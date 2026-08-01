#!/bin/bash
# Vast.ai on-start script — t02: Qwen3-VL-30B-A3B fine-tune env
# (Blackwell: RTX PRO 6000 / RTX 50-series / B100-B200)
# วาง script นี้ในช่อง "On-start script" ตอนสร้าง instance บน Vast.ai (ก่อนกด Rent)
set -euo pipefail

echo "=== Constistant fine-tune setup — t02 Qwen3-VL-30B-A3B + Unsloth (Blackwell) ==="

# t02: ทุกสคริปต์อ่าน MODEL_SIZE ตัวเดียวกัน ตั้งไว้ที่นี่ที่เดียวกันลืม
export MODEL_SIZE="30B-A3B"
echo 'export MODEL_SIZE="30B-A3B"' >> ~/.bashrc

# Blackwell (compute capability 12.0) ต้องตั้งค่านี้ก่อนติดตั้งอะไรที่ compile CUDA kernel
# ผูกเข้า .bashrc ด้วย ไม่งั้น env var จะหายตอนเปิด SSH/Jupyter terminal ใหม่
export TORCH_CUDA_ARCH_LIST="12.0"
echo 'export TORCH_CUDA_ARCH_LIST="12.0"' >> ~/.bashrc

# ⚠️ ไม่ใช้ set -e กับบรรทัดนี้ — pip 24.0 ที่มากับ base image ติดตั้งผ่าน apt/debian
# (ไม่ใช่ pip เอง) ทำให้ "pip install --upgrade pip" เจอ error "Cannot uninstall pip 24.0,
# RECORD file not found" เสมอ ถ้าไม่ใส่ || true ตรงนี้ set -euo pipefail ด้านบนจะฆ่า
# สคริปต์ทั้งไฟล์ทันที (พังจริงมาแล้ว 2026-07-20 — ทุกบรรทัดถัดจากนี้ไม่เคยรันเลย)
pip install --upgrade pip || true
pip install "triton>=3.3.1"          # Blackwell ต้องการเวอร์ชันนี้ขึ้นไปเท่านั้น
pip install unsloth trl peft accelerate bitsandbytes
pip install pillow

# ไม่ติดตั้ง xformers — บน Blackwell ต้อง compile จากซอร์ส (ช้า/เสี่ยงพังตอน build)
# Unsloth fallback ไปใช้ PyTorch native SDPA ให้อัตโนมัติถ้าไม่มี xformers

mkdir -p /workspace/tune
cd /workspace/tune

cat <<'MSG'

=== Setup ติดตั้งเสร็จ — MODEL_SIZE=30B-A3B ===

ขั้นต่อไป (ทำมือ ตามลำดับ ห้ามข้าม):

1) อัปโหลด data_before_tune/ ทั้งโฟลเดอร์เข้า /workspace/tune/
   (train.jsonl, val.jsonl, images/, train_qwen3vl.py, eval_fields.py,
    export_gguf.py, verify_env.py)

2) เช็คสภาพแวดล้อม — ตัวนี้เช็ค disk/RAM/transformers ให้ด้วย:
     python3 verify_env.py
   ต้องไม่มี ✗ เลย ถ้าเจอ "ดิสก์ทั้งก้อน < 280GB" = ตอนเช่าลืมลาก slider เป็น 300

3) วัด baseline ก่อนทูน (ตัวเลขนี้ต้องเก็บไว้เทียบ):
     python3 eval_fields.py --base --limit 20

4) ★ ทดสอบสั้นก่อนเสมอ — ห้ามข้าม:
     TEST_STEPS=5 SKIP_DEMO=1 python3 train_qwen3vl.py
   สิ่งที่ต้องเห็นก่อนไปต่อ:
     - บรรทัด "✓ ตรวจ batch แรก ... → ~5100 visual tokens"
       ถ้าได้ ~205 = collator ย่อภาพเป็น 512px → หยุด อย่าเทรนต่อ
     - "peak VRAM: XX GB" ← เอาเลขนี้ตัดสินว่าเทรนเต็มไหว/ไม่ไหว

5) เทรนเต็ม 3 epoch:
     SKIP_DEMO=1 python3 train_qwen3vl.py 2>&1 | tee train.log

6) วัดผลหลังเทรน (ไม้บรรทัดเดียวกับ baseline):
     python3 eval_fields.py --limit 20

7) export + อัปขึ้น HF (⛔ อย่าใช้ repo ของ t01):
     HF_TOKEN=hf_xxx HF_REPO=Sicilian44/qwen3vl-30b-thai-rc python3 export_gguf.py

⛔ ห้าม destroy instance จนกว่าจะโหลดไฟล์ลงเครื่องตัวเองเสร็จและมะขามสั่งเอง

MSG
