#!/usr/bin/env python3
"""
verify_env.py — เช็คว่าเครื่องที่เช่าพร้อมจริงก่อนอัปโหลด dataset/รันเทรน

รันทันทีหลัง onstart.sh ติดตั้งเสร็จ:
    python verify_env.py

ไม่แตะ train.jsonl/val.jsonl/images/ เลย — เช็คแค่ตัวเครื่อง+library เท่านั้น
"""
import os, sys

# t02: เช็คตามโมเดลที่จะเทรนจริง (MODEL_SIZE เดียวกับ train_qwen3vl.py / eval_fields.py)
TARGETS = {
    "30B-A3B": dict(repo="unsloth/Qwen3-VL-30B-A3B-Instruct", vram_min=74,
                    why="bf16 LoRA ของ MoE 30B (ไม่มี repo bnb-4bit ให้ทำ QLoRA)"),
    "8B":      dict(repo="unsloth/Qwen3-VL-8B-Instruct-unsloth-bnb-4bit", vram_min=24,
                    why="QLoRA 4-bit 8B ที่ 5,120 visual tokens/ภาพ, seq 24K"),
    "32B":     dict(repo="unsloth/Qwen3-VL-32B-Instruct-unsloth-bnb-4bit", vram_min=48,
                    why="QLoRA 4-bit 32B (repo unsloth-dynamic หนัก 32.3GB เฉพาะ weight)"),
    "QWEN36":  dict(repo="unsloth/Qwen3.6-35B-A3B", vram_min=74,
                    why="bf16 LoRA ของ Qwen3.6-35B-A3B (t01)"),
}
SIZE = os.environ.get("MODEL_SIZE", "30B-A3B").upper()
if SIZE not in TARGETS:
    raise SystemExit(f"❌ MODEL_SIZE={SIZE} ไม่รู้จัก — เลือกจาก {list(TARGETS)}")
T = TARGETS[SIZE]
print(f"=== ตรวจเครื่องสำหรับ MODEL_SIZE={SIZE} ({T['repo']}) ===\n")

ok = True

def check(name, fn):
    global ok
    try:
        result = fn()
        print(f"✓ {name}: {result}")
        return result
    except Exception as e:
        print(f"✗ {name}: FAILED — {e}")
        ok = False
        return None

print("=== 1) GPU / CUDA ===")
import torch
check("torch version", lambda: torch.__version__)
check("CUDA available", lambda: torch.cuda.is_available())
if torch.cuda.is_available():
    name = check("GPU name", lambda: torch.cuda.get_device_name(0))
    cc = check("compute capability", lambda: torch.cuda.get_device_capability(0))
    vram = check("VRAM total (GB)", lambda: round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1))
    if cc and cc[0] < 12:
        print(f"  ⚠️  compute capability {cc} < 12.0 — ไม่ใช่ Blackwell, ตรวจว่าเช่าเครื่องถูกรุ่นไหม")
    if vram and vram < T["vram_min"]:
        print(f"  ⚠️  VRAM {vram}GB < {T['vram_min']}GB ที่ {T['why']} ต้องการ — เสี่ยง OOM")
else:
    print("  ❌ ไม่เจอ GPU เลย — เช็คว่า container ขอ --gpus all / instance แนบ GPU จริงไหม")

print("\n=== 1b) ดิสก์ + RAM (สองอย่างที่ t01 พังจริงและ nvidia-smi ไม่บอก) ===")
import shutil
_du = shutil.disk_usage("/")
_free = _du.free / 1024**3
print(f"{'✓' if _free >= 250 else '✗'} disk ว่าง {_free:.0f} GB / ทั้งหมด {_du.total/1024**3:.0f} GB")
if _du.total / 1024**3 < 280:
    print("  ❌ ดิสก์ทั้งก้อน < 280GB — แปลว่า slider ตอนเช่ายังเป็น default 150GB")
    print("     t01 เจอ disk เต็มกลาง export มาแล้ว (ต้องการ ~265GB ตอน retry) → หยุด เช่าใหม่ให้ได้ 300GB")
    ok = False
elif _free < 250:
    print(f"  ⚠️  ว่างแค่ {_free:.0f}GB — โมเดล 62GB + merged ~60GB + gguf f16 + q4 ต้องการเยอะกว่านี้")
    print("     ล้าง ~/.cache/huggingface และ outputs_*/gguf ของรอบก่อนก่อนเริ่ม")

# RAM — merge_and_unload() ของ bf16 30B กาง ~60GB ใน RAM ธรรมดา ไม่ใช่ VRAM
# ถ้าไม่พอจะโดน OOM killer เงียบ ๆ (process หายไปเฉย ๆ ไม่มี traceback) หลงไปไล่ที่ GPU ผิดที่
try:
    with open("/proc/meminfo") as _f:
        _mem = {l.split(":")[0]: int(l.split()[1]) for l in _f if ":" in l}
    _total_gb = _mem["MemTotal"] / 1024**2
    _avail_gb = _mem.get("MemAvailable", _mem["MemFree"]) / 1024**2
    _swap_gb = _mem.get("SwapTotal", 0) / 1024**2
    print(f"{'✓' if _total_gb >= 80 else '⚠️ '} RAM {_total_gb:.0f} GB (ว่าง {_avail_gb:.0f} GB, swap {_swap_gb:.0f} GB)")
    if _total_gb < 80:
        print(f"  ⚠️  RAM {_total_gb:.0f}GB < 80GB — Phase 8 (merge_and_unload ของ bf16 30B) กาง ~60GB")
        print("     ถ้า export ตายแบบ 'Killed' เฉย ๆ ไม่มี traceback = OOM ของ RAM ไม่ใช่ VRAM")
except Exception as e:
    print(f"  (อ่าน /proc/meminfo ไม่ได้ — {e})")

print("\n=== 2) Unsloth ===")
try:
    from unsloth import FastVisionModel
    print("✓ FastVisionModel import สำเร็จ")
except ImportError as e:
    print(f"  FastVisionModel ไม่มี ({e}) — ลอง FastModel แทน (Qwen3.6 อาจไม่ใช้ wrapper vision แยก)")
    try:
        from unsloth import FastModel
        print("✓ FastModel import สำเร็จ (ตัวสำรอง)")
    except ImportError as e2:
        print(f"✗ FastModel ก็ไม่มี — {e2}")
        ok = False

print("\n=== 3) Triton (Blackwell ต้องการ >=3.3.1) ===")
try:
    import triton
    v = triton.__version__
    print(f"✓ triton {v}")
    major_minor_patch = tuple(int(x) for x in v.split(".")[:3])
    if major_minor_patch < (3, 3, 1):
        print(f"  ⚠️  triton {v} < 3.3.1 — Blackwell ต้องการเวอร์ชันนี้ขึ้นไป: pip install -U triton")
except ImportError as e:
    print(f"✗ triton import ไม่ได้ — {e}")
    ok = False

print("\n=== 4) bitsandbytes (ใช้เป็น paged_adamw_8bit optimizer เท่านั้น ไม่ใช่ quantize โมเดล) ===")
try:
    import bitsandbytes
    print(f"✓ bitsandbytes {bitsandbytes.__version__}")
except ImportError as e:
    print(f"✗ bitsandbytes import ไม่ได้ — {e}")
    ok = False

print("\n=== 5) transformers รู้จักสถาปัตยกรรมนี้ไหม ===")
# config.json ของ Qwen3-VL-30B-A3B ระบุ architectures = Qwen3VLMoeForConditionalGeneration
# ซึ่งเพิ่งเข้า transformers ช่วง 4.57 ถ้า unsloth ดึงตัวเก่ากว่ามา จะพังตอน from_pretrained
# ด้วย KeyError ที่อ่านไม่รู้เรื่อง — เช็คตรงนี้ก่อนเสียเวลาโหลด weight 62GB
try:
    import transformers
    print(f"✓ transformers {transformers.__version__}")
    _need = {"30B-A3B": "Qwen3VLMoeForConditionalGeneration",
             "8B": "Qwen3VLForConditionalGeneration",
             "32B": "Qwen3VLForConditionalGeneration"}.get(SIZE)
    if _need:
        if hasattr(transformers, _need):
            print(f"✓ transformers รู้จัก {_need}")
        else:
            print(f"✗ transformers เวอร์ชันนี้ไม่มี {_need} — ต้อง >=4.57")
            print("  แก้: pip install -U 'transformers>=4.57'  (แล้วเช็คว่า unsloth ยัง import ผ่าน)")
            ok = False
except Exception as e:
    print(f"✗ import transformers ไม่ได้ — {e}")
    ok = False

print("\n=== 6) ทดลองโหลด tokenizer จริง (ไม่โหลด weight เต็ม — เร็ว, เช็คว่า repo/auth ใช้ได้) ===")
try:
    from transformers import AutoTokenizer
    AutoTokenizer.from_pretrained(T["repo"])
    print(f"✓ โหลด tokenizer จาก {T['repo']} สำเร็จ (repo มีจริง เข้าถึงได้)")
except Exception as e:
    print(f"✗ โหลด tokenizer ไม่ได้ — {e}")
    print("  เช็คว่าชื่อ repo เปลี่ยนไปหรือยัง, หรือต้อง huggingface-cli login ก่อนไหม")
    ok = False

print("\n" + "=" * 50)
if ok:
    print("✓ พร้อมแล้ว — อัปโหลด data_before_tune/ ที่เหลือแล้วรัน eval_fields.py --base ต่อได้")
else:
    print("✗ มีจุดพัง — แก้ตามที่ ✗ แจ้งไว้ก่อนอัปโหลด dataset")
    sys.exit(1)
