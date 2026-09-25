#!/usr/bin/env python3
"""merge_lora_to_base.py — รวม LoRA เข้า base ให้เป็นโมเดล dense ตัวเดียว (เอาไปเสิร์ฟด้วย vLLM)

ทำไปทำไม: dense = ไม่มี LoRA ติดมา → vLLM/SGLang เสิร์ฟได้ตรงๆ ได้ fused MoE kernel +
CUDA graph (ตัวที่ทำให้เร็วขึ้นจริง — วัดแล้วว่าตอนนี้ overhead กิน 97-98% ของเวลา)
และปลดล็อกทาง GGUF ที่ค้างมาตั้งแต่ ก.ค. ไปด้วย

════════════════════════════════════════════════════════════════════════════
🔴 เรื่องที่ต้องเข้าใจก่อนรัน ไม่งั้นจะได้โมเดลขยะแบบเงียบๆ (เคยเกิดมาแล้ว 2 รอบ)
════════════════════════════════════════════════════════════════════════════
LoRA ของชั้น MoE expert เก็บ lora_B เป็นเมทริกซ์แบน (out, E*r) ซึ่ง "อ่านได้ 2 แบบ":
  · grouped_by_expert — expert ช้าสุด  [e0:r0..r47 | e1:r0..r47 | …]  ← Unsloth เดิมใช้แบบนี้
  · rank_major        — expert เร็วสุด  [r0:e0..e255 | r1:e0..e255 | …] ← PEFT/vLLM ใช้แบบนี้
รูปร่างเทนเซอร์ **เท่ากันเป๊ะทั้งสองแบบ** → อ่านผิดแบบก็ไม่มี error มีแต่ผลลัพธ์เพี้ยน

`dacarokann/destrier` อัปเมื่อ ~31 ส.ค. 2026 ไม่มีคีย์ `lora_B_layout` ใน adapter_config
= **legacy grouped_by_expert** (unsloth-zoo PR #1232/#1269 merge 17 ก.ย. 2026 เป็นตัวเปลี่ยน
default ไป rank_major + เพิ่มคีย์นั้น) ⇒ ไฟล์นี้ตั้ง env `UNSLOTH_MOE_LORA_B_LAYOUT=
grouped_by_expert` **ก่อน import unsloth** ห้ามลบบรรทัดนั้น ห้ามย้ายลงไปใต้ import

นี่คือคำอธิบายจริงของบั๊ก "merge แล้วได้ขยะ" ที่ฆ่า GGUF ของ t01/t02 เมื่อ ก.ค. 2026
(ไดอารี่ 2026-07-28 ข้อ 7: ΔW ที่ peft คำนวณ "รูปร่างถูก" scaling "ถูก" แต่ค่าที่ใส่เข้าไป
ขนาดเล็กผิดปกติ) — ไม่ใช่เพราะ peft เวอร์ชันเก่าอย่างที่เคยเข้าใจ แต่เพราะ **merge path
เรียก PEFT get_delta_weight ซึ่งอ่าน rank_major ขณะที่ตอนเทรน forward เป็น grouped_by_expert**

⛔ ห้ามเชื่อว่า "รันแล้วไม่ error = merge สำเร็จ" — จบแล้วต้องรัน `verify_merge.py` เสมอ

รัน (บนเครื่องเช่า · ดิสก์ต้องว่าง ≥250GB · ดู README ของ t05_Destrier):
    python merge_lora_to_base.py --inspect-only        # อ่านสเปก adapter อย่างเดียว ฟรี ไม่ใช้ GPU
    python merge_lora_to_base.py --out ./destrier_merged
    python merge_lora_to_base.py --push dacarokann/destrier-merged
"""
import argparse
import json
import os
import sys

# ⛔ ต้องอยู่ก่อน import unsloth/peft ทุกกรณี — resolver อ่าน env ตอน forward/merge ทุกครั้ง
os.environ.setdefault("UNSLOTH_MOE_LORA_B_LAYOUT", "grouped_by_expert")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

BASE = "unsloth/Qwen3.6-35B-A3B"
ADAPTER = "dacarokann/destrier"
NUM_EXPERTS = 256                    # base config.json: num_experts
# ต้องตรงกับตอนเทรน (train_t05_courser.py) — เสิร์ฟคนละค่ากับที่เทรนคือบั๊กคลาสที่ฆ่า t01/t04
# อบลง preprocessor_config.json ของ repo ที่ merge แล้ว → engine ไหนโหลดก็ได้ค่าถูกเอง
MAX_PIXELS = 6912 * 1024             # 7,077,888
MIN_PIXELS = 256 * 1024              # 262,144


def safetensors_header(repo, filename="adapter_model.safetensors"):
    """อ่าน **เฉพาะ header** ของ safetensors ผ่าน HTTP Range — ได้ shape/dtype ครบทุกเทนเซอร์
    โดยไม่ต้องโหลดไฟล์จริง (adapter ตัวนี้ 11.3GB · header ไม่กี่ร้อย KB)

    รูปแบบไฟล์: 8 ไบต์แรก = ความยาว header (u64 little-endian) ตามด้วย JSON
    คืน None ถ้าอ่านแบบนี้ไม่ได้ (เซิร์ฟเวอร์ไม่รองรับ Range ฯลฯ) ให้ผู้เรียกถอยไปโหลดเต็ม"""
    import struct
    import requests
    from huggingface_hub import hf_hub_url
    url = hf_hub_url(repo, filename)
    try:
        h = requests.get(url, headers={"Range": "bytes=0-7"}, timeout=60)
        if len(h.content) < 8:
            return None
        n = struct.unpack("<Q", h.content[:8])[0]
        if not 0 < n < 200_000_000:
            return None
        b = requests.get(url, headers={"Range": f"bytes=8-{8 + n - 1}"}, timeout=180)
        return json.loads(b.content[:n])
    except Exception as e:
        print(f"   (อ่าน header แบบ Range ไม่ได้: {type(e).__name__} — จะถอยไปโหลดเต็ม)")
        return None


def inspect(adapter):
    """อ่านสเปกจริงจากไฟล์ ไม่เชื่อ adapter_config.json อย่างเดียว — ฟรี ไม่ใช้ GPU

    ทำไมต้องอ่าน shape เอง: r ที่ config บอกกับ r ที่อยู่ในไฟล์จริงไม่ตรงกันได้ (สคริปต์
    รวม fold เขียน r ใหม่) และ **r ผิด = สูตรแกะ expert ผิดทั้งหมด**"""
    from huggingface_hub import hf_hub_download
    cfg_path = hf_hub_download(adapter, "adapter_config.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    layout = cfg.get("lora_B_layout", "<<ไม่มีคีย์ → legacy grouped_by_expert>>")
    print(f"adapter: {adapter}")
    print(f"   r={cfg.get('r')} alpha={cfg.get('lora_alpha')} layout={layout}")
    print(f"   target_parameters={cfg.get('target_parameters')}")

    hdr = safetensors_header(adapter)
    d = None
    if hdr is None:                       # ถอยไปโหลดเต็ม (บนเครื่องเช่าที่ cache อยู่แล้วก็ไม่ช้า)
        from huggingface_hub import snapshot_download
        from safetensors import safe_open
        d = snapshot_download(adapter, allow_patterns=["*.json", "*.safetensors"])
        with safe_open(os.path.join(d, "adapter_model.safetensors"), framework="pt") as f:
            hdr = {k: {"shape": f.get_slice(k).get_shape(),
                       "dtype": f.get_slice(k).get_dtype()} for k in f.keys()}
    keys = [k for k in hdr if k != "__metadata__"]
    ek = sorted(k for k in keys if "experts" in k and k.endswith("lora_A.weight"))
    if not ek:
        sys.exit("⛔ ไม่เจอ lora_A ของชั้น experts เลย — adapter ผิดตัว?")
    shape, dtype = hdr[ek[0]]["shape"], hdr[ek[0]]["dtype"]
    r_file = shape[0] // NUM_EXPERTS
    n_exp = sum(1 for k in keys if "experts" in k)
    print(f"   ไฟล์จริง {ek[0].split('language_model.')[-1]} {shape} {dtype}")
    print(f"   → r ที่คำนวณจาก shape = {r_file} (E={NUM_EXPERTS})")
    if r_file != cfg.get("r"):
        print(f"   ⚠️  ไม่ตรงกับ config (r={cfg.get('r')}) — **ยึดค่าจากไฟล์** {r_file}")
    print(f"   เทนเซอร์ของชั้น expert {n_exp} ตัว · ทั้งหมด {len(keys)} ตัว")

    # ขนาดที่ควรเป็น vs ที่เป็นจริง — ต่างกันมาก = เก็บ fp32 หรือ r ไม่ใช่อย่างที่คิด
    nbytes = {"F32": 4, "BF16": 2, "F16": 2}.get(dtype, 2)
    total = sum(
        nbytes * (lambda s: s[0] * (s[1] if len(s) > 1 else 1))(hdr[k]["shape"]) for k in keys)
    print(f"   ขนาดรวมที่คำนวณจาก header ≈ {total / 1e9:.1f} GB (dtype {dtype})")

    if cfg.get("lora_B_layout") is None:
        print("\n🔴 ไม่มีคีย์ lora_B_layout = adapter อัปก่อน 17 ก.ย. 2026 → legacy grouped_by_expert")
        print(f"   สคริปต์นี้ตั้ง UNSLOTH_MOE_LORA_B_LAYOUT="
              f"{os.environ['UNSLOTH_MOE_LORA_B_LAYOUT']} ให้แล้ว")
    else:
        print(f"\n✅ adapter ประกาศ layout เอง: {cfg['lora_B_layout']}")
    return d, cfg, r_file


def check_versions():
    """เตือนเรื่องเวอร์ชัน — ไม่บังคับ เพราะ env var ข้างบนกันไว้ทั้งสองทางแล้ว"""
    try:
        import unsloth_zoo
        print(f"unsloth_zoo {getattr(unsloth_zoo, '__version__', '?')}")
    except ImportError:
        sys.exit("⛔ ไม่มี unsloth_zoo — ลง: pip install unsloth unsloth_zoo")
    import peft
    print(f"peft {peft.__version__}")


def merge(adapter_dir, out, push, max_mem):
    import torch
    from unsloth import FastVisionModel
    print(f"\nโหลด base+adapter (base ~72GB ครั้งแรกรอนาน) …", flush=True)
    model, tok = FastVisionModel.from_pretrained(
        model_name=adapter_dir, load_in_4bit=False, dtype=torch.bfloat16)
    ip = getattr(tok, "image_processor", None)
    if ip is not None:
        ip.size["longest_edge"] = MAX_PIXELS
        ip.size["shortest_edge"] = MIN_PIXELS
        print(f"อบความละเอียดภาพลง processor: longest={MAX_PIXELS} shortest={MIN_PIXELS}")
    target = push or out
    print(f"\nmerge + เซฟ → {target} (ทีละ shard ไม่โหลดทั้งโมเดลเข้า RAM) …", flush=True)
    if push:
        model.push_to_hub_merged(push, tok, save_method="merged_16bit",
                                 maximum_memory_usage=max_mem)
    else:
        model.save_pretrained_merged(out, tok, save_method="merged_16bit",
                                     maximum_memory_usage=max_mem)
    return target


def bake_image_config(out):
    """เขียนค่าความละเอียดลง preprocessor_config.json ของ repo ที่ merge แล้ว

    ทำไมสำคัญ: ถ้าไม่อบไว้ ทุกคนที่เสิร์ฟต้องจำส่ง --mm-processor-kwargs เองทุกครั้ง
    ลืมเมื่อไหร่ = เสิร์ฟคนละความละเอียดกับที่เทรน = บั๊กเงียบคลาสเดิม (ฆ่า t01/t04 มาแล้ว)"""
    p = os.path.join(out, "preprocessor_config.json")
    if not os.path.exists(p):
        print(f"⚠️  ไม่เจอ {p} — ข้ามการอบค่า (ต้องส่ง --mm-processor-kwargs ตอนเสิร์ฟเอง)")
        return
    cfg = json.load(open(p, encoding="utf-8"))
    cfg.setdefault("size", {})
    cfg["size"]["longest_edge"] = MAX_PIXELS
    cfg["size"]["shortest_edge"] = MIN_PIXELS
    json.dump(cfg, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"✅ อบ size.longest_edge={MAX_PIXELS} / shortest_edge={MIN_PIXELS} ลง {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", default=ADAPTER)
    ap.add_argument("--out", default="./destrier_merged")
    ap.add_argument("--push", help="repo บน HF (ต้อง export HF_TOKEN)")
    ap.add_argument("--inspect-only", action="store_true",
                    help="อ่านสเปก adapter อย่างเดียว ฟรี ไม่ใช้ GPU — ทำก่อนเสมอ")
    ap.add_argument("--max-mem", type=float, default=0.5,
                    help="maximum_memory_usage ของ unsloth (0.5 กัน OOM ตอน merge โมเดลใหญ่)")
    a = ap.parse_args()

    if a.push and not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")):
        sys.exit("⛔ --push ต้องมี HF_TOKEN")

    adapter_dir, cfg, r_file = inspect(a.adapter)
    if a.inspect_only:
        return 0
    check_versions()
    target = merge(adapter_dir, a.out, a.push, a.max_mem)
    if not a.push:
        bake_image_config(a.out)

    print(f"""
{'=' * 74}
merge เสร็จ → {target}
{'=' * 74}
⛔ ยังเชื่อไม่ได้ — "รันจบไม่ error" ไม่ได้พิสูจน์ว่า merge ถูก (กฎของทีมเอง)
   ต้องรันด่านตรวจต่อ ตามลำดับนี้ (2 ข้อแรกฟรี ไม่ใช้ GPU):

   1. python verify_merge.py --check-ab --base <path base ใน HF cache> --merged {a.out} \\
          --adapter {adapter_dir}
      → ชั้น experts ต้องเปลี่ยนทุกตัว (ไม่เปลี่ยน = merge ไม่ติด) และ packing ต้องตรงแบบเดียว

   2. เทียบพฤติกรรมกับ production path (ต้องใช้ GPU แต่คุ้ม — ตัวชี้ขาดจริง):
      python verify_merge.py --fingerprint adapter --adapter {adapter_dir} --out ref.pt
      python verify_merge.py --fingerprint merged  --merged {a.out}       --out mrg.pt
      python verify_merge.py --fingerprint base    --base-repo {a.base}   --out base.pt
      python verify_merge.py --compare ref.pt mrg.pt base.pt
      → mrg ต้องเหมือน ref (top-1 ตรง ~100%) และต้อง **ต่างจาก base ชัดเจน**
        (ถ้า mrg เหมือน base มากกว่า ref = merge ไม่ติด ได้โมเดลที่ไม่เคย fine-tune)
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
