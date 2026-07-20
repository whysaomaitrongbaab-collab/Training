#!/usr/bin/env python3
"""
verify_env.py — เช็คว่าเครื่องที่เช่าพร้อมจริงก่อนอัปโหลด dataset/รันเทรน

รันทันทีหลัง onstart.sh ติดตั้งเสร็จ:
    python verify_env.py

ไม่แตะ train.jsonl/val.jsonl/images/ เลย — เช็คแค่ตัวเครื่อง+library เท่านั้น
"""
import sys

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
    if vram and vram < 74:
        print(f"  ⚠️  VRAM {vram}GB < 74GB ที่ bf16 LoRA ของ Qwen3.6-35B-A3B ต้องการ — จะ OOM")
else:
    print("  ❌ ไม่เจอ GPU เลย — เช็คว่า container ขอ --gpus all / instance แนบ GPU จริงไหม")

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

print("\n=== 4) bitsandbytes (ใช้เป็น adamw_8bit optimizer เท่านั้น ไม่ใช่ quantize โมเดล) ===")
try:
    import bitsandbytes
    print(f"✓ bitsandbytes {bitsandbytes.__version__}")
except ImportError as e:
    print(f"✗ bitsandbytes import ไม่ได้ — {e}")
    ok = False

print("\n=== 5) ทดลองโหลด tokenizer จริง (ไม่โหลด weight เต็ม — เร็ว, เช็คว่า repo/auth ใช้ได้) ===")
try:
    from transformers import AutoTokenizer
    AutoTokenizer.from_pretrained("unsloth/Qwen3.6-35B-A3B")
    print("✓ โหลด tokenizer จาก unsloth/Qwen3.6-35B-A3B สำเร็จ (repo มีจริง เข้าถึงได้)")
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
