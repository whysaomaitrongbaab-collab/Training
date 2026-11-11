#!/usr/bin/env python3
"""
train_t07.py — t07 "Palfrey": fine-tune Qwen3.6-35B-A3B แบบ per-subtask ด้วย Unsloth + LoRA

[t07] คัดลอกจาก t05_Courser/train_t05_courser.py (สคริปต์ที่เทรน Courser_a/c/d ผ่านจริง 31 ส.ค.)
   แล้วแก้เฉพาะที่ t07 ตัดสินแล้ว (t07_workflow.md + D7/D9/D10/D11/D13) — บรรทัดที่แก้มีป้าย [t07]:
   - ข้อมูล: data/{train,val}_fold{FOLD}.jsonl ในโฟลเดอร์นี้ (ล้างแล้วโดย sanitize — data_raw/ ห้ามใช้เทรน)
   - ตรึงเวอร์ชันตาม PIN_SET: A = ชุด 3 ต.ค. ที่ผ่าน merge/verify A-B-C (ค่าเริ่มต้น) · t05 = ชุดเทรน Destrier
     ⚠️ UNTESTED · เวอร์ชันเพี้ยน = หยุด (ALLOW_VERSION_DRIFT=1 ยอมให้ผ่าน) + บันทึก training_env.txt ไปกับ adapter
   - UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert ตั้งก่อน import unsloth แล้วถาม zoo กลับว่าใช้จริง (Lesson 18,
     ต้นเหตุคลาสเดียวกับ destrier e229403) · ปฏิเสธ UNSLOTH_MOE_LORA_MERGED=1 (ทางนั้นส่ง LoRA ไป PEFT = rank_major)
   - hub: dacarokann/Palfrey_{a..d} private · hub_strategy 'end' (push เฉพาะ adapter สุดท้าย — checkpoint ทุก 25 step
     เก็บบนการ์ด 2 ตัว เพราะพื้นที่ private ของ HF ฟรีมีจำกัด) · ห้ามชี้ Courser_*/destrier* เด็ดขาด
   - EPOCHS ค่าเริ่ม 1 (D7) · RESUME=1 ต่อจาก checkpoint ล่าสุดที่สมบูรณ์ (D10) · SKIP_DEMO ค่าเริ่ม 1
   - รูปถอดรหัสทีละ step (LazyRows): t05 เปิดรูปทุกแถวล่วงหน้า — t07 มี ~4,000 รูปต่อ fold × ~37 MB (วัด 6,241 หน้า
     ใน image/: เฉลี่ย 9.26 Mpx × 4 ไบต์) ≈ 150 GB RAM เครื่อง ซึ่งเกิน RAM ของการ์ดหลายใบ (90-188 GB) · EAGER_IMAGES=1 = แบบ t05
   - SORT_LONGEST ใช้ sampler แบบเรียงลำดับ: t05 เรียงแถวแล้วแต่ Trainer ใช้ RandomSampler สุ่มทับ (transformers 5.5.0
     trainer.py:1003-1032) = probe ไม่เคยเห็นตัวยาวสุดจริง
   - เขียน DONE_fold{FOLD} หลัง save + push + sha256 บน HF ตรงกับไฟล์บนการ์ด (dry-run เขียน DRYRUN_DONE_ แทน
     กันไม่ให้ marker ค้างจาก gate 2 หลอก run_fold.sh/watch4.sh ว่า fold เสร็จแล้ว)

เขียนใหม่ 2026-08-24 (มะขามสั่ง "เขียนใหม่ หาข้อมูลในเน็ตมาด้วย") — ไม่ใช่ copy ของ
t01/train_qwen36.py หรือ t02/train_qwen3vl.py แต่ทุกค่ามีที่มาระบุไว้ 2 ทาง:
  [W] = จากเอกสาร/งานวิจัยบนเน็ต (ค้น 2026-08-24):
        - Unsloth Qwen3.5 fine-tune docs (Qwen3.6-35B-A3B อยู่ตระกูลนี้ — log unsloth
          patch ขึ้นชื่อ "Qwen3_5_MoE"): bf16 LoRA 35B-A3B ~74GB VRAM, transformers v5
          บังคับ, MoE QLoRA 4-bit ไม่รองรับ (BitsandBytes), router layer ปิดเทรน
          by default "not a good idea to fine-tune the router"
        - Unsloth Vision docs: lora_dropout=0, bias="none", seed 3407,
          completion_only_loss "should always be True"
        - "LoRA Without Regret" (Thinking Machines, 2025): LoRA ต้องแปะทุก layer รวม
          MLP/MoE ("attention-only underperforms"), optimal LR ~ไม่ขึ้นกับ rank,
          LoRA แพ้ batch ใหญ่ → batch เล็กดี
  [t01] = บทเรียนที่พิสูจน์บนเครื่องจริงกับโมเดลตระกูลนี้เป๊ะๆ (t01_workflow.md):
        - lora_dropout ต้อง 0 — MoE ParamWrapper error จริงถ้าไม่ 0 (ตรงกับ [W])
        - r=64 OOM จริงบน 95GB ที่ MAX_LENGTH สูง → r=32 คือค่าที่รันผ่านจริง
        - paged_adamw_8bit (adamw_8bit ธรรมดา OOM ตอน optimizer step)
        - ip.size["longest_edge"] คือกลไกตั้ง max_pixels จริง (ip.max_pixels ไม่มีแล้ว
          บน transformers 5.x — AttributeError จริงบนเครื่องเช่า)
        - enable_thinking=False ตอน inference (ไม่งั้น CoT กิน token จนไม่ถึง JSON)
        - epilogue หลังเซฟ adapter ค้างได้ — SKIP_DEMO=1 ข้ามได้ adapter เซฟก่อนแล้ว
  [t02] = บทเรียน collator (rule_of_tune ข้อ 12 — บั๊ก 14x visual token):
        - UnslothVisionDataCollator ต้อง resize="max" (default "min" หา
          vision_config.image_size ไม่เจอ → ย่อ 512px เงียบๆ) + ส่ง max_seq_length
        - max_seq_length ต้องส่งตอน from_pretrained ด้วย (default 2048 ตัดกลาง image token)
  [t03] = วัดจากข้อมูลจริงรอบนี้ (2026-08-24):
        ⛔ ถ้า OOM: ลดจำนวนภาพ gridline หรือลด lora_r — ห้ามลด MAX_LENGTH (จะตัด label กลาง JSON)

dataset [t07]: build_t07.py → data_raw/ → sanitize → data/{train,val}_fold{0..3}.jsonl (D13)
  5 group-fold (D8) เทรน fold 0-3 — บ้านของ fold 4 อยู่ใน train ของทุก adapter (เหมือน t05)
  path รูปในไฟล์เทียบ "รากรีโป Training" (image/<บ้าน>/<ไฟล์>.png)

    /venv/main/bin/python train_t07.py --selftest          # ตรวจตัวช่วย (ไม่ใช้ GPU/unsloth) รันบน PC ได้
    TEST_STEPS=10 FOLD=0 /venv/main/bin/python train_t07.py # ★ รันสั้นก่อนเสมอ — gate2_smoke.sh ทำให้ครบชุด
    bash run_fold.sh 0                                      # รันจริง (retry OOM + RESUME) → dacarokann/Palfrey_a

⚠️ rule_of_tune ข้อ 2: ค่าในไฟล์นี้กำหนดว่าโมเดลเรียนอะไร/เห็นภาพละเอียดแค่ไหน —
   แก้แล้วผลเปลี่ยน ต้องเตือน/บันทึกก่อนแก้เสมอ
"""
import gc
import hashlib
import json
import os
import platform
import re
import sys
import time
from collections import Counter
from importlib import metadata
from pathlib import Path

# [t01] ต้องตั้งก่อน import torch — ลด CUDA fragmentation (OOM จริงบนเครื่องเช่า
# 2026-07-21 ขาด ~100MB จาก 95GB; t03 ใช้ MAX_LENGTH สูงกว่า t01 อีก ยิ่งจำเป็น)
os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
# [2026-08-31] ตั้งชื่อเก่าด้วย — torch 2.11 ยังพิมพ์ชื่อนี้ในข้อความ OOM ของตัวเอง
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
# [t07] ต้องตั้งก่อน `import unsloth` — zoo ≥ 2026.9.6 ค่าเริ่มคือ rank_major และอ่านค่านี้ใหม่ทุก forward/backward
# ("process-wide mode ... set it before the process does any MoE work and leave it set" — zoo 2026.9.9 moe_utils.py:1369)
os.environ.setdefault("UNSLOTH_MOE_LORA_B_LAYOUT", "grouped_by_expert")
GROUPED = "grouped_by_expert"
# [review 11 พ.ย.] ปิด Xet ก่อน import huggingface_hub: Xet พังกลางการโหลดโมเดล 72 GB จริง (สาธิต 23 ก.ย. — presentation.py SERVE_ENV)
# และ upload_folder ของ adapter ท้ายไฟล์ + เช็ค sha256 ของ LFS ต้องไปทาง LFS ปกติ (ทางเดียวกับที่ verify_hf_push.py --sha คาดหวัง)
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from PIL import Image  # noqa: E402  [t07] ใช้อ่านขนาดรูป (header เท่านั้น) ก่อน import unsloth

# ─────────────────────────────────────────────────────────────
# ค่าหลัก — ที่มากำกับทุกตัว (ดู docstring)
# ─────────────────────────────────────────────────────────────
MODEL = "unsloth/Qwen3.6-35B-A3B"   # ✅ มะขามเคาะ 2026-08-24: ใช้ Qwen3.6 (ตัว t01) ไม่ใช่ Qwen3-VL
LOAD_IN_4BIT = False                # [W] MoE QLoRA 4-bit ไม่รองรับ — bf16 เท่านั้น (~74GB)
# [2026-08-31 att1235] 7680 → 6912 หลัง real training OOM 2/4 fold — ต้องเท่ากันทุก fold และเท่ากับ
# merge_lora_to_base.py / verify_merge.py / preset ตัวเสิร์ฟ (6912*1024) · ⛔ ห้ามขึ้นถึง 16,384 บนการ์ด 96GB
MAX_PIXELS = 6912 * 1024            # = 6,912 visual tokens/ภาพ (patch 16 × merge 2 = 1024 px/token)
MIN_PIXELS = 256 * 1024             # [t01]
# [t03b] 47104 วัดจากข้อมูลจริง — ห้ามลดเดี่ยวๆ (ตัด label กลาง JSON = บั๊กคลาส t01 §0.4)
#   [t07] survey 11 พ.ย.: gridline แบบ slim ทำให้แถวยาวสุด ~38,456 token (margin ~18%) — preflight ด้านล่างวัดจริงทุกแถว
#   ถ้า OOM: (1) ลดภาพ gridline (2) ลด MAX_PIXELS ทุก fold พร้อมกัน — ห้ามลด MAX_LENGTH เฉยๆ
MAX_LENGTH = 47104
# [t03] r=16 หลัง OOM จริง — Unsloth เปิด LoRA บน MoE experts ทั้ง 256 ตัว · alpha/r = 2 เท่าเดิม
#   soup_safetensors.py ต้องการ r/alpha/target เท่ากันทุก fold (SAME_CFG) — ห้ามต่างกันระหว่าง fold
LORA_R, LORA_ALPHA = 16, 32
# [t07] D7: ค่าเริ่ม 1 epoch — t05 loss ท้าย epoch 1 = 0.10-0.16 เทียบท้ายรอบ 0.09-0.14 (2 epoch) และ t07 มีแถว ~3 เท่า
#   (t05 เคาะ 3→2 เพราะ epoch ที่ 3 กิน GPU-ชม. +50% เสี่ยง overfit) · EPOCHS=2 ตั้งผ่าน env ได้ ไม่ต้องแก้ไฟล์
#   ⚠️ RESUME ต้องใช้ EPOCHS เดิม (ตรวจด้วย run_args.json ด้านล่าง)
EPOCHS = float(os.environ.get("EPOCHS", "1"))
LR = 1e-4                           # [t01] พิสูจน์ converge; [W] LWR: LoRA LR ~10x FullFT
BATCH, GRAD_ACCUM = 1, 8            # [t01]; [W] LWR: LoRA แพ้ batch ใหญ่ — 1 ดีอยู่แล้ว
SEED = 3407                         # [W] docs
# [t01] จงใจ freeze vision encoder — default 0 = freeze เท่าเดิมเป๊ะ (A/B: FINETUNE_VISION=1)
FINETUNE_VISION = os.environ.get("FINETUNE_VISION", "0") == "1"
HOUSE_RE = re.compile(r"บ้าน_(?:เล็ก|ใหญ่)_\d+ชั้น_\d+")   # [t07] D5 — ทุกจำนวนชั้น (ตัวเดิมเห็นแค่ 1-2 ชั้น)

# [t07] D9 — ชุดเวอร์ชันที่ตรึง (ต้องตรงกับ onstart_t07.sh) · None = ต้องไม่มีแพ็กเกจนี้
#   A  = freeze_venv_main.txt ของ 3 ต.ค. (t05_Destrier/proof/04_…/logs) — ชุดที่ merge/verify A-B-C/serve ผ่าน
#        ยังไม่เคยเทรนโมเดลนี้ → gate 2 ต้องพิสูจน์
#   t05 = ชุดที่เทรน Courser (unsloth 2026.8.22 / peft 0.20.0) + zoo 2026.9.5 = รุ่นสุดท้ายก่อนมีตัวเลือก layout
#        (grouped ตายตัวในโค้ด) — ⚠️ UNTESTED ทั้งชุด (t05 จริงใช้ torch cu130 บน image conda และ zoo ไม่เคยบันทึก)
_COMMON = {"torch": "2.11.0+cu128", "torchvision": "0.26.0+cu128", "trl": "0.24.0", "transformers": "5.5.0",
           "accelerate": "1.15.0", "bitsandbytes": "0.50.2", "xgrammar": "0.2.8", "huggingface_hub": "1.30.0",
           "tokenizers": "0.22.2", "safetensors": "0.8.0", "datasets": "4.3.0", "xformers": "0.0.35",
           "triton": "3.6.0", "cut_cross_entropy": "25.1.1", "pillow": "12.3.0", "hf_xet": "1.6.0"}
PIN_SETS = {
    "A": {**_COMMON, "unsloth": "2026.9.14", "unsloth_zoo": "2026.9.9", "peft": "0.21.2", "torchao": "0.18.0"},
    "t05": {**_COMMON, "unsloth": "2026.8.22", "unsloth_zoo": "2026.9.5", "peft": "0.20.0", "torchao": None},
}


# ─────────────────────────────────────────────────────────────
# [t07] ตัวช่วย — ไม่แตะ GPU/unsloth จึงตรวจด้วย --selftest บน PC ได้
# ─────────────────────────────────────────────────────────────
def installed(dist):
    """เวอร์ชันที่ติดตั้งอยู่ หรือ None — ลองทั้ง _ / - (metadata ของแต่ละแพ็กเกจสะกดชื่อไม่เหมือนกัน)"""
    for n in dict.fromkeys((dist, dist.replace("_", "-"), dist.replace("-", "_"), dist.lower())):
        try:
            return metadata.version(n)
        except metadata.PackageNotFoundError:
            pass
    return None


def version_drift(pins):
    """[(แพ็กเกจ, ต้องการ, ที่มีจริง)] ที่ไม่ตรง"""
    return [(k, want, installed(k)) for k, want in pins.items() if installed(k) != want]


def newest_checkpoint(out_dir):
    """checkpoint-N ที่ N สูงสุดและเซฟครบ (trainer_state.json เขียนเป็นไฟล์สุดท้ายของ _save_checkpoint)
    ตัวที่เขียนไม่จบ (โดน kill/OOM กลางเซฟ) ข้ามพร้อมบอก — resume จากตัวขาด = ล้มซ้ำแบบไม่ใช่ OOM"""
    d = Path(out_dir)
    if not d.is_dir():
        return None
    cks = sorted((p for p in d.glob("checkpoint-*") if p.is_dir() and p.name.split("-")[-1].isdigit()),
                 key=lambda p: int(p.name.split("-")[-1]), reverse=True)
    for p in cks:
        if (p / "trainer_state.json").is_file() and (p / "adapter_model.safetensors").is_file():
            return str(p)
        print(f"⚠️  ข้าม {p.name}: เซฟไม่ครบ (ไม่มี trainer_state.json/adapter)")
    return None


class _Img:
    """รูปที่ยังไม่ถอดรหัส — มีแค่ path + size (ตัวตรวจทุกตัวข้างล่างใช้แค่ .size เหมือน PIL)"""
    __slots__ = ("path", "size")

    def __init__(self, path, size):
        self.path, self.size = path, size


def load_split(name, data_dir, root):
    """jsonl → แถว metadata (รูปเป็น _Img) — คืน subtask_list แยกต่างหาก ห้ามยัด key เพิ่มใน rows (collator อาจสะดุด)
    [t07] เปิดแค่ header ของรูป (ขนาด) ไม่ถอดรหัสพิกเซล — ถอดจริงใน LazyRows ทีละ step"""
    rows, subtasks, subtask_list, sizes = [], Counter(), [], {}
    with open(Path(data_dir) / f"{name}.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            subtasks[r.get("subtask", "?")] += 1
            subtask_list.append(r.get("subtask", "?"))
            content = []
            for c in r["messages"][0]["content"]:
                if c["type"] == "image":
                    p = c["image"]
                    if p not in sizes:
                        with Image.open(Path(root) / p) as im:
                            sizes[p] = im.size
                    content.append({"type": "image", "image": _Img(p, sizes[p])})
                else:
                    content.append({"type": "text", "text": c["text"]})
            rows.append({"messages": [
                {"role": "user", "content": content},
                {"role": "assistant", "content": r["messages"][1]["content"]},
            ]})
    return rows, subtasks, subtask_list


def materialize(row, root):
    """แถว metadata → แถวที่ collator รับ (PIL RGB) — รูปแบบเดียวกับ t05 load_split เป๊ะ"""
    user = []
    for c in row["messages"][0]["content"]:
        if c["type"] == "image":
            with Image.open(Path(root) / c["image"].path) as im:
                user.append({"type": "image", "image": im.convert("RGB")})
        else:
            user.append(c)
    return {"messages": [{"role": "user", "content": user}, row["messages"][1]]}


class LazyRows:
    """dataset แบบ map-style: ถอดรหัสรูปตอน DataLoader ขอแถว แล้วทิ้ง (RAM ต่อ step ≈ รูปใน batch เท่านั้น)
    ไม่มี __iter__ โดยตั้งใจ — iter() ของ Python วน __getitem__ 0,1,2… จน IndexError (TRL อ่าน next(iter(ds)))"""

    def __init__(self, rows, root):
        self.rows, self.root = rows, root

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        return materialize(self.rows[i], self.root)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def check_run_args(out_dir, current, resuming):
    """ค่าที่เปลี่ยนกลางทางแล้ว resume = schedule/ข้อมูลเพี้ยนเงียบๆ — เทรนใหม่: เขียนทับ · resume: ต้องตรงทุกค่า"""
    p = Path(out_dir) / "run_args.json"
    if resuming and p.is_file():
        old = json.loads(p.read_text(encoding="utf-8"))
        diff = {k: (old.get(k), v) for k, v in current.items() if old.get(k) != v}
        if diff:
            raise SystemExit(f"⛔ RESUME ด้วยค่าที่ต่างจากรอบเดิม: {diff} — ใช้ค่าเดิม หรือเทรนใหม่ใน OUT_DIR ใหม่")
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(current, indent=1, ensure_ascii=False), encoding="utf-8")


def _selftest():
    import tempfile
    t = Path(tempfile.mkdtemp(prefix="t07_selftest_"))
    (t / "image" / "h").mkdir(parents=True)
    (t / "data").mkdir()
    Image.new("RGB", (64, 48), (200, 10, 10)).save(t / "image/h/a.png")
    Image.new("L", (32, 32), 128).save(t / "image/h/b.png")          # ไม่ใช่ RGB → ต้องได้ RGB
    row = lambda sub, imgs: {"subtask": sub, "messages": [            # noqa: E731
        {"role": "user", "content": [{"type": "image", "image": f"image/h/{i}"} for i in imgs]
         + [{"type": "text", "text": "prompt"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "{}"}]}]}
    with open(t / "data/train_fold0.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in (row("plan_beam", ["a.png"]), row("gridline", ["a.png", "b.png"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.write("\n")
    rows, subs, sl = load_split("train_fold0", t / "data", t)
    assert len(rows) == 2 and subs == Counter(plan_beam=1, gridline=1) and sl == ["plan_beam", "gridline"]
    assert rows[1]["messages"][0]["content"][1]["image"].size == (32, 32)
    assert rows[0]["messages"][1]["content"] == [{"type": "text", "text": "{}"}]
    ds = LazyRows(rows, t)
    m = ds[1]
    ims = [c["image"] for c in m["messages"][0]["content"] if c["type"] == "image"]
    assert [im.mode for im in ims] == ["RGB", "RGB"] and ims[1].size == (32, 32)
    assert len(ds) == 2 and isinstance(next(iter(ds)), dict)
    try:
        ds[2]
        raise AssertionError("ds[2] ต้อง IndexError")
    except IndexError:
        pass
    o = t / "out"
    assert newest_checkpoint(o) is None
    for n, full in ((25, True), (50, False)):
        (o / f"checkpoint-{n}").mkdir(parents=True)
        if full:
            (o / f"checkpoint-{n}/trainer_state.json").write_text("{}")
            (o / f"checkpoint-{n}/adapter_model.safetensors").write_text("x")
    assert newest_checkpoint(o).endswith("checkpoint-25"), "ตัวที่เซฟไม่ครบต้องถูกข้าม"
    (o / "checkpoint-50/trainer_state.json").write_text("{}")
    (o / "checkpoint-50/adapter_model.safetensors").write_text("x")
    assert newest_checkpoint(o).endswith("checkpoint-50")
    assert version_drift({"pillow": installed("pillow")}) == []
    assert [d[0] for d in version_drift({"t07-no-such-pkg": "1"})] == ["t07-no-such-pkg"]
    check_run_args(o, {"EPOCHS": 1.0}, resuming=False)
    check_run_args(o, {"EPOCHS": 1.0}, resuming=True)
    try:
        check_run_args(o, {"EPOCHS": 2.0}, resuming=True)
        raise AssertionError("EPOCHS เปลี่ยนตอน resume ต้องหยุด")
    except SystemExit:
        pass
    assert HOUSE_RE.search('x "บ้าน_ใหญ่_3ชั้น_09_หน้า12" y') and not HOUSE_RE.search("บ้าน 2 ชั้น")
    print(f"selftest ok — {t}")


if __name__ == "__main__" and "--selftest" in sys.argv:
    _selftest()
    sys.exit(0)

# ─────────────────────────────────────────────────────────────
# ค่าที่มาจาก env + ด่านกันพลาดก่อนแตะ GPU
# ─────────────────────────────────────────────────────────────
FOLD = os.environ.get("FOLD", "0")
if FOLD not in ("0", "1", "2", "3"):   # [t07] 'abcd' = 4 fold เท่านั้น (fold 4 ไม่เทรนแยก — D8)
    raise SystemExit(f"⛔ FOLD={FOLD!r} — t07 เทรน fold 0-3 เท่านั้น")
HERE = Path(__file__).resolve().parent                     # [t07] resolve(): run_fold.sh เรียกด้วย path สัมพัทธ์
# [t05] path รูปใน jsonl เทียบ "รากรีโป Training" ไม่ใช่โฟลเดอร์สคริปต์ — บนการ์ดต้องเป็น /workspace/Training/{image,tune_ai/t07_Palfrey}
REPO_ROOT = HERE.parent.parent
DATA_DIR = HERE / "data"                                   # [t07] D13 — ไม่ใช่ HERE/*.jsonl แบบ t05
TRAIN_SPLIT = f"train_fold{FOLD}"
VAL_SPLIT = f"val_fold{FOLD}"
OUT_DIR = str(HERE / f"outputs_t07_fold{FOLD}")            # [t07] แยกจาก outputs_t05_* — ห้ามทับ adapter รอบเก่า
LORA_DIR = Path(OUT_DIR) / "lora"
HUB_MODEL_ID = f"dacarokann/Palfrey_{'abcd'[int(FOLD)]}"   # [t07] D11 fold0→a … fold3→d (private)
if re.search(r"courser|destrier", HUB_MODEL_ID, re.I):     # [t07] D11 — t07 ห้ามลงทับ repo ของ t05 เด็ดขาด
    raise SystemExit(f"⛔ HUB_MODEL_ID={HUB_MODEL_ID} ชี้ repo ของ t05 — ห้าม")
DONE_MARK = HERE / f"DONE_fold{FOLD}"

TEST_STEPS = int(os.environ.get("TEST_STEPS", "0"))
SORT_LONGEST = os.environ.get("SORT_LONGEST") == "1"
RESUME = os.environ.get("RESUME", "0") == "1"              # [t07] D10
SKIP_DEMO = os.environ.get("SKIP_DEMO", "1") == "1"        # [t07] ค่าเริ่ม 1 (t05 = 0) — demo เคยค้าง และ gate2_check ทำหน้าที่นี้แทน
EAGER_IMAGES = os.environ.get("EAGER_IMAGES", "0") == "1"  # [t07] ทางหนีไฟ: โหลดรูปล่วงหน้าแบบ t05 (ต้องมี RAM ~150 GB)
PIN_SET = os.environ.get("PIN_SET", "A")
if PIN_SET not in PIN_SETS:
    raise SystemExit(f"⛔ PIN_SET={PIN_SET!r} — ต้องเป็น {sorted(PIN_SETS)}")

# [t07] layout ของ LoRA ตัวที่สอง: ค่าที่ผิดต้องหยุดก่อนโหลดโมเดล (setdefault ด้านบนไม่ทับค่าที่ export ผิดมา)
if os.environ["UNSLOTH_MOE_LORA_B_LAYOUT"] != GROUPED:
    raise SystemExit(f"⛔ UNSLOTH_MOE_LORA_B_LAYOUT={os.environ['UNSLOTH_MOE_LORA_B_LAYOUT']!r} — t07 ต้อง {GROUPED}")
if os.environ.get("UNSLOTH_MOE_LORA_MERGED") == "1":      # zoo moe_utils.py:1962-1964: ทางนี้ยกให้ PEFT = rank_major
    raise SystemExit("⛔ UNSLOTH_MOE_LORA_MERGED=1 — ทางนี้อ่าน expert LoRA แบบ rank_major ห้ามใช้ตอนเทรน t07")

# [2026-08-31] `push_to_hub=True` ทำให้ Trainer เรียก `init_hf_repo()` ตั้งแต่ `__init__`
# **ไม่ใช่ตอน save_steps** — dry-run จึงตายด้วย 401 ทั้งที่ยังไม่ถึง step ที่จะเซฟ (เจอจริง)
#   - dry-run (TEST_STEPS>0): ปิด push ไปเลย ไม่มีอะไรควรอัปอยู่แล้ว
#   - รันจริง: **บังคับต้องมี HF_TOKEN แล้วตายทันทีถ้าไม่มี** — ห้ามปล่อยให้เทรน 10+ ชม.
#     แล้วค่อยไปพังตอน push (นั่นคือคลาส Day of Shame: งานเสร็จแต่ไม่มีที่เก็บ)
PUSH_TO_HUB = TEST_STEPS == 0
if PUSH_TO_HUB and not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")):
    raise SystemExit(
        "⛔ ไม่พบ HF_TOKEN — รันจริงต้อง push adapter ขึ้น HF (Day-of-Shame guard)\n"
        "   แก้: พิมพ์ token แบบจำกัดสิทธิ์ (repo ของ t07 เท่านั้น — ห้าม token ของ PC, Lesson 22):\n"
        "        read -rs HF_TOKEN && export HF_TOKEN   แล้วรันใหม่\n"
        "   (ถ้าตั้งใจ dry-run ให้ใส่ TEST_STEPS=10 ซึ่งปิด push ให้อัตโนมัติ)")
if SORT_LONGEST and TEST_STEPS == 0:
    raise SystemExit("⛔ SORT_LONGEST ใช้ได้เฉพาะ dry-run (ต้องมี TEST_STEPS>0) — "
                     "เปิดตอนเทรนจริงจะทำให้ลำดับข้อมูลไม่สุ่ม")
# [t07] เริ่มใหม่ทั้งที่มี checkpoint ค้าง: rotation เก็บเลขสูงสุดไว้ (เช่น checkpoint-2 ของรอบทดสอบ) แล้ว RESUME ครั้งหน้า
# หยิบของคนละรอบไปต่อเงียบๆ — หยุดตั้งแต่ก่อนโหลดโมเดล ให้คนย้ายออกหรือสั่ง RESUME=1 เอง
if not RESUME and any(Path(OUT_DIR).glob("checkpoint-*")):
    raise SystemExit(f"⛔ {OUT_DIR} มี checkpoint ค้างอยู่แต่ RESUME=0 — ย้ายโฟลเดอร์ออกก่อน หรือใช้ RESUME=1")

# [t07] Lesson 18 — เวอร์ชันที่เขียนไฟล์ adapter ต้องตรงชุดที่ตรึงทุกการ์ด (t05: peft 0.18.1 vs 0.20.0 ห่างกัน 2 ชม.)
_pins = PIN_SETS[PIN_SET]
_drift = version_drift(_pins)
print(f"PIN_SET={PIN_SET}{' (⚠️ UNTESTED)' if PIN_SET == 't05' else ''}: "
      + " · ".join(f"{k} {installed(k) or '-'}" for k in _pins))
if _drift:
    _msg = "\n".join(f"   {k}: ต้องการ {w or '<ไม่ติดตั้ง>'} · มีจริง {h or '<ไม่ติดตั้ง>'}" for k, w, h in _drift)
    if os.environ.get("ALLOW_VERSION_DRIFT") != "1":
        raise SystemExit(f"⛔ เวอร์ชันไม่ตรงชุด {PIN_SET} ({len(_drift)} ตัว):\n{_msg}\n"
                         "   แก้: bash onstart_t07.sh (หรือ FREEZE_FILE=…) · ตั้งใจจริงค่อยใส่ ALLOW_VERSION_DRIFT=1")
    print(f"⚠️  ALLOW_VERSION_DRIFT=1 — เทรนต่อทั้งที่เวอร์ชันเพี้ยน (บันทึกลง training_env.txt):\n{_msg}")
# ─────────────────────────────────────────────────────────────

from unsloth import FastVisionModel  # noqa: E402
import torch  # noqa: E402

# [t07] ถาม zoo กลับว่าจะอ่าน/เขียน lora_B แบบไหนจริง — env ถูกแต่ zoo ไม่รับ = ผลเพี้ยนเงียบๆ แบบ e229403
try:
    from unsloth_zoo.temporary_patches.moe_utils import moe_lora_b_layout
except ImportError:
    moe_lora_b_layout = None
if moe_lora_b_layout is None:
    if PIN_SET != "t05":
        raise SystemExit("⛔ unsloth_zoo รุ่นนี้ไม่มี moe_lora_b_layout() — ไม่ใช่ชุด A (2026.9.9) ห้ามเทรน")
    print("⚠️  PIN_SET=t05: zoo ≤ 2026.9.5 ไม่มีตัวเลือก layout — grouped_by_expert ตายตัวในโค้ด "
          "(adapter_config จะไม่มีคีย์ lora_B_layout; soup วัดจากตัวเลขเอง)")
else:
    _lay = moe_lora_b_layout()
    if _lay != GROUPED:
        raise SystemExit(f"⛔ unsloth_zoo moe_lora_b_layout() = {_lay!r} ไม่ใช่ {GROUPED} — หยุดก่อนเทรน")
    print(f"✓ unsloth_zoo moe_lora_b_layout() = {_lay}")

train_meta, train_sub, _ = load_split(TRAIN_SPLIT, DATA_DIR, REPO_ROOT)


def _len_est(r):
    vis = sum(min(c["image"].size[0] * c["image"].size[1], MAX_PIXELS) // 1024
              for c in r["messages"][0]["content"] if c["type"] == "image")
    txt = sum(len(c["text"]) for c in r["messages"][0]["content"] if c["type"] == "text")
    a = r["messages"][1]["content"]
    gt = "".join(x.get("text", "") for x in a) if isinstance(a, list) else a
    return vis + (txt + len(gt)) / 2.2


# [2026-08-31] SORT_LONGEST=1 — เรียงตัวอย่างยาวสุดขึ้นก่อน **สำหรับ dry-run เท่านั้น** (worst-case VRAM probe)
# ⛔ ห้ามเปิดตอนเทรนจริง — ลำดับข้อมูลจะไม่สุ่ม (curriculum โดยไม่ตั้งใจ) — ด่านอยู่ด้านบนแล้ว
# [t07] คู่กับ train_sampling_strategy="sequential" ใน SFTConfig — ไม่งั้น RandomSampler สุ่มทับการเรียง (บั๊กของ t05)
if SORT_LONGEST:
    train_meta = sorted(train_meta, key=_len_est, reverse=True)
    print(f"⚠️  SORT_LONGEST=1 — เรียงยาวสุดขึ้นก่อน + sampler แบบเรียงลำดับ (worst-case VRAM probe) "
          f"ตัวยาวสุด est {_len_est(train_meta[0]):.0f} token")
val_meta, val_sub, val_subtasks = load_split(VAL_SPLIT, DATA_DIR, REPO_ROOT)
if EAGER_IMAGES:
    print("⚠️  EAGER_IMAGES=1 — ถอดรหัสรูปทั้งหมดล่วงหน้าแบบ t05 (RAM เครื่อง ~37 MB ต่อรูป)")
    train_ds = [materialize(r, REPO_ROOT) for r in train_meta]
    val_ds = [materialize(r, REPO_ROOT) for r in val_meta]
else:
    train_ds, val_ds = LazyRows(train_meta, REPO_ROOT), LazyRows(val_meta, REPO_ROOT)
n_multi = sum(1 for r in train_meta
              if sum(1 for c in r["messages"][0]["content"] if c["type"] == "image") > 1)
print(f"train {len(train_ds)} | val {len(val_ds)} | multi-image {n_multi}")
print(f"train per-subtask: {dict(train_sub)}")
print(f"val   per-subtask: {dict(val_sub)}")

model, tokenizer = FastVisionModel.from_pretrained(
    MODEL,
    load_in_4bit=LOAD_IN_4BIT,
    use_gradient_checkpointing="unsloth",   # [W] docs: ลด VRAM + ยืด context
    max_seq_length=MAX_LENGTH,              # [t02] ต้องส่งตรงนี้ — default 2048 ตัดกลาง image token
)

# [t01] ip.size[...] คือกลไกจริงบน transformers 5.x (ip.max_pixels ไม่มีแล้ว)
# ip.size เป็น SizeDict — ห้ามเช็ค isinstance(dict) ก่อน (เป็น False เสมอ)
ip = tokenizer.image_processor
ip.size["longest_edge"] = MAX_PIXELS
ip.size["shortest_edge"] = MIN_PIXELS
print(f"image processor: max={ip.size['longest_edge']} px "
      f"(= {ip.size['longest_edge'] // 1024} visual tokens/ภาพ)")


# ── ด่านกันตัด label กลาง JSON (บั๊กคลาส t01 §0.4) ────────────────────────────
# visual token คำนวณตรงจากขนาดภาพ (แม่นยำ) + text token จาก tokenizer จริง (ไม่ต้องประมวลผลภาพ = เร็วไม่กี่วินาที)
# ถ้าเกิน = หยุดทันทีก่อนเสียค่าเช่า GPU ดีกว่าเทรนจบแล้วพบว่า label โดนตัดเงียบ ๆ
# [t07] วิ่งบน train_meta/val_meta (ขนาดรูปจาก header) — ไม่ถอดรหัสรูปทั้ง fold
def preflight_seq_lengths(ds, name):
    px_per_token = 1024                      # patch 16 × merge 2 (processor_config จริง)
    cap = MAX_PIXELS // px_per_token
    worst, over = (0, None), []
    for i, r in enumerate(ds):
        vis, txt = 0, 0
        for c in r["messages"][0]["content"]:
            if c["type"] == "image":
                w, h = c["image"].size
                vis += min(w * h // px_per_token, cap)
            else:
                txt += len(tokenizer.tokenizer(c["text"], add_special_tokens=False)["input_ids"])
        a = r["messages"][1]["content"]
        gt = "".join(x.get("text", "") for x in a) if isinstance(a, list) else a
        txt += len(tokenizer.tokenizer(gt, add_special_tokens=False)["input_ids"])
        total = vis + txt
        if total > worst[0]:
            worst = (total, i)
        if total > MAX_LENGTH:
            over.append((total, i))
    print(f"preflight {name}: seq ยาวสุด {worst[0]:,} token (แถว {worst[1]}) "
          f"| MAX_LENGTH {MAX_LENGTH:,} | margin {(MAX_LENGTH - worst[0]) / MAX_LENGTH * 100:.1f}%")
    if over:
        raise SystemExit(
            f"⛔ {len(over)} แถวใน {name} ยาวเกิน MAX_LENGTH ({max(o[0] for o in over):,} > "
            f"{MAX_LENGTH:,}) — label จะโดนตัดกลาง JSON\n"
            f"   แก้ตามลำดับ: (1) ลดภาพ gridline (2) ลด MAX_PIXELS "
            f"(3) เพิ่ม MAX_LENGTH ถ้า VRAM ไหว — ห้ามปล่อยผ่าน")
    return worst[0]


_longest_train = preflight_seq_lengths(train_meta, "train")
preflight_seq_lengths(val_meta, "val")
# ─────────────────────────────────────────────────────────────────────────────

model = FastVisionModel.get_peft_model(
    model,
    # [W] LWR: แปะทุก layer รวม MLP/MoE — attention-only underperforms
    # (router/gate ของ MoE: unsloth ปิดเทรนให้เอง by default — [W] "not a good idea")
    finetune_vision_layers=FINETUNE_VISION,
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=LORA_R, lora_alpha=LORA_ALPHA,
    lora_dropout=0,                 # [W]+[t01] MoE ParamWrapper ไม่รองรับ dropout!=0 — error จริง
    bias="none", random_state=SEED, use_rslora=False, loftq_config=None,
)

from unsloth.trainer import UnslothVisionDataCollator  # noqa: E402
from trl import SFTTrainer, SFTConfig  # noqa: E402

FastVisionModel.for_training(model)

# [t02] resize="max" บังคับ — default "min" หา vision_config.image_size ของตระกูลนี้ไม่เจอ
# → ย่อ 512px เงียบๆ = เสียความละเอียด ~25 เท่า (บั๊กที่ทำ A/B t01-vs-t02 รอบแรกพังทั้งรอบ)
# completion_only_loss=True: [W] docs "should always be True" — เขียนไว้ชัดตาม rule_of_tune ข้อ 12
collator = UnslothVisionDataCollator(model, tokenizer, resize="max",
                                     max_seq_length=MAX_LENGTH)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    data_collator=collator,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    args=SFTConfig(
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        warmup_ratio=0.05,
        num_train_epochs=EPOCHS,
        **({"max_steps": TEST_STEPS} if TEST_STEPS else {}),
        # [t07] SORT_LONGEST ต้องได้ลำดับที่เรียงไว้จริง (transformers 5.5.0 ค่าเริ่ม = "random")
        train_sampling_strategy="sequential" if SORT_LONGEST else "random",
        learning_rate=LR,
        logging_steps=5,
        # [t03] adamw_8bit ไม่ใช่ paged_adamw_8bit — paged พังด้วย CUDA illegal memory access ที่ step 42
        # (unified memory สปิลไป host) · non-paged ใช้ VRAM เท่าเดิม ถ้าจะ OOM จะ OOM ที่ step 1 ให้รู้ทันที
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=SEED,
        output_dir=OUT_DIR,
        report_to="none",
        # [t03] ทุก 25 step เสียมากสุด ~25-35 นาทีถ้าล้ม · เก็บ 2 ตัว (adapter 3.8GB + optimizer 1.9GB ต่อตัว)
        # [t07] checkpoint อยู่บนการ์ดเท่านั้น (hub_strategy 'end') — RESUME=1 ต่อจากตัวล่าสุด
        save_strategy="steps",
        save_steps=25,
        save_total_limit=2,
        push_to_hub=PUSH_TO_HUB,
        # [t07] D11: 'end' = Trainer ไม่ push checkpoint เลย (trainer.py:4076) — push adapter สุดท้ายเองท้ายไฟล์
        # push_to_hub=True ยังมีไว้ให้ init_hf_repo() สร้าง repo private/ตรวจ token ตั้งแต่ __init__ (ล้มเร็ว)
        **({"hub_model_id": HUB_MODEL_ID, "hub_strategy": "end", "hub_private_repo": True}
           if PUSH_TO_HUB else {}),
        # [t03] ⛔ eval ปิดไว้ — accelerate upcast logits ทั้งก้อนเป็น fp32 ≈ 13-25GB → OOM ตอน evaluate จริง
        eval_strategy="no",
        per_device_eval_batch_size=1,
        remove_unused_columns=False,          # บังคับสำหรับ vision fine-tuning
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        max_length=MAX_LENGTH,
        bf16=True,                  # [W] MoE ตระกูลนี้ = bf16 setup เท่านั้น
    ),
)
# [t07] Unsloth กรอง kwargs ที่ config ไม่รับทิ้งพร้อมแค่พิมพ์บอก (rl_config_compat.filter_config_init_kwargs)
# ค่าเหล่านี้หายเงียบ = probe ไม่เรียง / push ทุก checkpoint จนพื้นที่ HF เต็ม / repo สาธารณะ — ตรวจค่าที่ Trainer ถือจริง
_want_args = {"train_sampling_strategy": "sequential" if SORT_LONGEST else "random", "save_steps": 25,
              "save_total_limit": 2, "num_train_epochs": EPOCHS}
if PUSH_TO_HUB:
    _want_args.update(hub_strategy="end", hub_private_repo=True, hub_model_id=HUB_MODEL_ID)
_lost = {k: (v, getattr(trainer.args, k, None)) for k, v in _want_args.items() if getattr(trainer.args, k, None) != v}
if _lost:
    raise SystemExit(f"⛔ ค่าใน SFTConfig หาย/ถูกเปลี่ยน (ต้องการ, ที่ Trainer ถือ): {_lost}")

# ── ตรวจ batch แรกก่อนเผาเวลาเทรน: (1) ภาพไม่โดนย่อเงียบๆ (2) seq ยาวสุดไม่โดนตัด
try:
    # [แก้ 2026-08-25] หาร n_img ให้เป็น "ต่อภาพ" จริง (แถว gridline มีหลายภาพ — เกณฑ์รวมจะหลวมลงตามจำนวนภาพ)
    _b = collator([train_ds[0]])
    _gt = _b.get("image_grid_thw")
    if _gt is not None:
        _n_img = int(_gt.shape[0])
        _tok_per_img = int((_gt[:, 1] * _gt[:, 2]).sum()) // 4 // max(_n_img, 1)
        _cap = MAX_PIXELS // 1024
        print(f"✓ batch แรก: {_n_img} ภาพ, ~{_tok_per_img} visual tokens/ภาพ "
              f"(cap ที่ตั้งไว้ {_cap}), seq={_b['input_ids'].shape[-1]}")
        assert _tok_per_img > 1000, (
            f"visual tokens = {_tok_per_img}/ภาพ ต่ำผิดปกติ — resize='max' ไม่มีผล? "
            f"(บั๊กคลาส t01 §0.4: ภาพโดนย่อ 512px เงียบๆ เหลือ ~266)")
        # [แก้ 2026-08-31] เทียบกับเพดานที่แถวนี้ควรได้จริง = min(พิกเซลจริง, MAX_PIXELS)/1024 (ไม่ใช่เพดานรวม)
        _row0_imgs = [c["image"] for c in train_meta[0]["messages"][0]["content"] if c["type"] == "image"]
        _expect = (sum(min(im.size[0] * im.size[1], MAX_PIXELS) // 1024 for im in _row0_imgs)
                   // max(len(_row0_imgs), 1)) if _row0_imgs else _cap
        if _tok_per_img < _expect * 0.75:
            print(f"⚠️  ได้ {_tok_per_img}/ภาพ แต่ขนาดภาพจริงควรได้ ~{_expect} (cap {_cap}) "
                  f"— ต่ำเกิน 25% จากที่ควรเป็น = มีอะไรย่อภาพเงียบ ๆ ตรวจก่อนเทรนต่อ")
        else:
            print(f"   (ภาพแถวนี้ควรได้ ~{_expect} token/ภาพ ตามขนาดจริง — ตรงกัน ไม่โดนย่อ)")
    # ตัวอย่างที่ "น่าจะยาวสุด" — ประเมินจากภาพ+prompt+GT ไม่ใช่จำนวนภาพอย่างเดียว
    _top = sorted(range(len(train_meta)), key=lambda i: _len_est(train_meta[i]), reverse=True)[:3]
    for _rank, _gi in enumerate(_top, 1):
        _b2 = collator([train_ds[_gi]])
        _seq = _b2["input_ids"].shape[-1]
        print(f"✓ ตัวอย่างยาวอันดับ {_rank}: seq={_seq} (est {_len_est(train_meta[_gi]):.0f}, "
              f"MAX_LENGTH={MAX_LENGTH})")
        assert _seq < MAX_LENGTH, (f"seq {_seq} >= MAX_LENGTH {MAX_LENGTH} — โดนตัด! "
                                   f"label จะขาดกลาง JSON (บั๊กคลาส t01 §0.4) "
                                   f"— ตัดตัวอย่างนี้ทิ้งหรือลดจำนวนภาพ gridline ห้ามลด MAX_LENGTH")
        del _b2
    # [2026-08-31] `_b2` ถูก del ในลูปแล้ว — del ซ้ำ = NameError ที่ทำให้ยามดูเหมือนล้มทั้งที่ผ่าน
    del _b, _gt
    gc.collect(); torch.cuda.empty_cache()
except AssertionError:
    raise
except Exception as e:
    print(f"⚠️  ตรวจ batch แรกไม่สำเร็จ ({e}) — ดู VRAM/loss ตอนเทรนให้ดี")

gpu = torch.cuda.get_device_properties(0)
print(f"GPU: {gpu.name} {gpu.total_memory / 1024**3:.1f} GB")
if not LOAD_IN_4BIT and gpu.total_memory / 1024**3 < 74:
    print("⚠️  VRAM < 74GB สำหรับ bf16 LoRA 35B-A3B — เสี่ยง OOM สูง")

# [t07] D10 — RESUME=1: ต่อจาก checkpoint ล่าสุดที่เซฟครบใน OUT_DIR (optimizer/scheduler/rng กลับมาครบ)
_resume_from = newest_checkpoint(OUT_DIR) if RESUME else None
if RESUME:
    print(f"▶ RESUME=1: {'ต่อจาก ' + _resume_from if _resume_from else 'ไม่มี checkpoint ที่เซฟครบ — เริ่มใหม่'}")
_run_args = {"EPOCHS": EPOCHS, "MAX_LENGTH": MAX_LENGTH, "MAX_PIXELS": MAX_PIXELS, "LORA_R": LORA_R,
             "LORA_ALPHA": LORA_ALPHA, "LR": LR, "BATCH": BATCH, "GRAD_ACCUM": GRAD_ACCUM, "SEED": SEED,
             "PIN_SET": PIN_SET, "FINETUNE_VISION": FINETUNE_VISION, "n_train": len(train_meta),
             "train_sha256": sha256_file(DATA_DIR / f"{TRAIN_SPLIT}.jsonl")}
check_run_args(OUT_DIR, _run_args, resuming=bool(_resume_from))
_t0 = time.time()
_out = trainer.train(resume_from_checkpoint=_resume_from)
print(_out)
_peak = torch.cuda.max_memory_allocated() / 1024**3
print(f"peak VRAM: {_peak:.1f} GB (reserved {torch.cuda.max_memory_reserved() / 1024**3:.1f} GB)")

model.save_pretrained(str(LORA_DIR))
tokenizer.save_pretrained(str(LORA_DIR))
print(f"✓ เซฟ LoRA adapter ที่ {LORA_DIR}")

# [t07] adapter ที่เซฟต้องประกาศ layout ที่ตั้งใจ (zoo 2026.9.9 เขียนคีย์ lora_B_layout ทุก save_pretrained)
_cfg = json.loads((LORA_DIR / "adapter_config.json").read_text(encoding="utf-8"))
_lay_saved = _cfg.get("lora_B_layout")
_cfg_ok = (_cfg.get("r"), _cfg.get("lora_alpha")) == (LORA_R, LORA_ALPHA) and (
    _lay_saved == GROUPED if PIN_SET == "A" else _lay_saved in (None, GROUPED))
print(f"{'✓' if _cfg_ok else '⛔'} adapter_config: r={_cfg.get('r')} alpha={_cfg.get('lora_alpha')} "
      f"lora_B_layout={_lay_saved!r} peft={_cfg.get('peft_version')}")

# [t07] Lesson 18d — บันทึกเวอร์ชัน/ค่าที่ใช้จริงไว้ข้าง adapter (อัปขึ้น HF ไปพร้อมกัน)
_env = {
    "round": "t07 Palfrey", "fold": FOLD, "hub_model_id": HUB_MODEL_ID, "pin_set": PIN_SET,
    "pins_drift": [list(d) for d in _drift], "allow_version_drift": os.environ.get("ALLOW_VERSION_DRIFT") == "1",
    "python": platform.python_version(), "torch_cuda": torch.version.cuda, "gpu": gpu.name,
    "gpu_total_gb": round(gpu.total_memory / 1024**3, 2), "peak_vram_alloc_gb": round(_peak, 2),
    "peak_vram_reserved_gb": round(torch.cuda.max_memory_reserved() / 1024**3, 2),
    "env": {k: os.environ.get(k) for k in ("UNSLOTH_MOE_LORA_B_LAYOUT", "PYTORCH_CUDA_ALLOC_CONF",
                                           "TORCH_CUDA_ARCH_LIST", "EPOCHS", "TEST_STEPS", "RESUME")},
    "resumed_from": _resume_from, "train_output": str(_out), "train_wall_s": round(time.time() - _t0),
    "longest_train_tokens": _longest_train, **_run_args,
    "val_sha256": sha256_file(DATA_DIR / f"{VAL_SPLIT}.jsonl"),
    "saved_adapter_config": {k: _cfg.get(k) for k in ("r", "lora_alpha", "lora_B_layout", "peft_version")},
    "installed": sorted(f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions()
                        if d.metadata["Name"]),
}
(LORA_DIR / "training_env.txt").write_text(json.dumps(_env, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"✓ เขียน {LORA_DIR / 'training_env.txt'}")

_local_sha = sha256_file(LORA_DIR / "adapter_model.safetensors")
_step = getattr(trainer.state, "global_step", "?")
if PUSH_TO_HUB:
    from huggingface_hub import HfApi
    _api = HfApi()
    for _attempt in range(1, 4):
        try:
            _api.upload_folder(folder_path=str(LORA_DIR), repo_id=HUB_MODEL_ID, repo_type="model",
                               commit_message=f"t07 fold{FOLD} final adapter (step {_step})")
            break
        except Exception as e:
            if _attempt == 3:
                raise SystemExit(f"⛔ push ขึ้น {HUB_MODEL_ID} ล้มครบ 3 ครั้ง ({type(e).__name__}: {e}) — "
                                 f"adapter อยู่ที่ {LORA_DIR} บนการ์ดนี้เท่านั้น ⛔ ห้าม destroy การ์ด")
            print(f"⚠️  push ล้มครั้งที่ {_attempt}/3 ({type(e).__name__}: {e}) — รอ 60 วิ")
            time.sleep(60)
    # Lesson 23: "สคริปต์จบ" ≠ "ไฟล์อยู่บน HF" — เทียบ sha256 ของ LFS (metadata ฟรี) กับไฟล์บนการ์ด
    _info = _api.get_paths_info(HUB_MODEL_ID, ["adapter_model.safetensors"], expand=True)
    _rsha = _info[0].lfs.sha256 if _info and getattr(_info[0], "lfs", None) else None
    if _rsha != _local_sha:
        raise SystemExit(f"⛔ sha256 บน HF ({_rsha}) ≠ บนการ์ด ({_local_sha}) — ⛔ ห้าม destroy การ์ด")
    print(f"✓ push {HUB_MODEL_ID} แล้ว · sha256 ตรงกัน {_local_sha}")
if not _cfg_ok:
    raise SystemExit("⛔ adapter_config ไม่ตรงที่ตั้งใจ (ดูบรรทัด ⛔ ด้านบน) — ไม่เขียน DONE ให้คนตัดสิน "
                     f"({'push แล้ว' if PUSH_TO_HUB else 'dry-run'})")
_mark = DONE_MARK if PUSH_TO_HUB else HERE / f"DRYRUN_DONE_fold{FOLD}"
_mark.write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} step={_step} peak_alloc_gb={_peak:.1f} "
                 f"sha256={_local_sha} lora_B_layout={_lay_saved} repo={HUB_MODEL_ID if PUSH_TO_HUB else '-'}\n",
                 encoding="utf-8")
print(f"✓ เขียน {_mark.name}")


# ── demo 3 ตัวจาก val — [t01] บล็อกนี้เคยค้างกิน VRAM ไม่ยอมจบ; adapter เซฟ+push ไปแล้ว
#    ค้างเมื่อไหร่ kill -9 ได้เลย ไม่ถือว่าเทรนพัง · [t07] ค่าเริ่มข้าม (SKIP_DEMO=1) — gate2_check.py ทำแทน
def setup_grammar():
    """xgrammar builtin JSON grammar — มะขามสั่ง 2026-08-24: หน้า beam plan ต้องแนบ xgrammar
    ตอนส่งเสมอ (rule_of_tune ข้อ 13 — xgrammar พิสูจน์บน GPU แล้ว 96.8% vs 57.9%)
    tokenizer จริงต้องแกะจาก processor wrapper (.tokenizer) — คืน None ถ้าใช้ไม่ได้"""
    try:
        import xgrammar as xgr
        cfg = model.config
        vocab = getattr(cfg, "vocab_size", None) or cfg.text_config.vocab_size
        tok_info = xgr.TokenizerInfo.from_huggingface(tokenizer.tokenizer, vocab_size=vocab)
        compiled = xgr.GrammarCompiler(tok_info).compile_builtin_json_grammar()
        return lambda: {"logits_processor": [xgr.contrib.hf.LogitsProcessor(compiled)]}
    except Exception as e:
        print(f"⚠️  xgrammar ใช้ไม่ได้ ({e}) — demo หน้า beam จะรันแบบไม่ constrain")
        return None


if SKIP_DEMO:
    print("ข้าม demo generation (SKIP_DEMO=1)")
else:
    FastVisionModel.for_inference(model)
    grammar = setup_grammar()
    beam_idx = [i for i, s in enumerate(val_subtasks) if s == "plan_beam"]
    other_idx = [i for i in range(len(val_ds)) if i not in beam_idx]
    demo_idx = (beam_idx[:1] + other_idx)[:3]
    print(f"demo generation {len(demo_idx)} ตัว ({[val_subtasks[i] for i in demo_idx]}) "
          f"— ค้างเกิน ~10 นาที kill ได้เลย adapter เซฟแล้ว")
    for i in demo_idx:
        sample = val_ds[i]
        sub = val_subtasks[i]
        msgs = [sample["messages"][0]]
        # [t01] enable_thinking=False จำเป็น — ไม่งั้นโมเดล reasoning-native เขียน CoT จนหมด token budget
        text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
        imgs = [c["image"] for c in msgs[0]["content"] if c["type"] == "image"]
        inputs = tokenizer(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
        gen_kwargs = dict(max_new_tokens=3000, do_sample=False)
        if sub == "plan_beam" and grammar is not None:
            gen_kwargs.update(grammar())   # LogitsProcessor เป็น stateful — ตัวใหม่ต่อ generate
        out = model.generate(**inputs, **gen_kwargs)
        pred = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        Path(f"{OUT_DIR}/sample_{sub}_{i}.json").write_text(pred, encoding="utf-8")
        try:
            json.loads(pred)
            ok = "JSON valid"
        except Exception as e:
            ok = f"JSON เสีย — {e}"
        leak = " · ⚠️ มีชื่อบ้านเทรน" if HOUSE_RE.search(pred) else ""
        print(f"  [{sub}] ตัวอย่าง {i}: {ok} ({len(pred)} ตัวอักษร){leak}")
        del inputs, out
        gc.collect(); torch.cuda.empty_cache()

print("\nขั้นต่อไป: verify_hf_push.py --sha (ทุก fold) → Day-of-Shame → soup_safetensors.py --folds 0 1 2 3 "
      "--fold-repo 'dacarokann/Palfrey_{}' --out-repo dacarokann/palfrey (RUNBOOK_gate2-3.md)")
