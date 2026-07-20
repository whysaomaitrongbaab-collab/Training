#!/bin/bash
# Vast.ai on-start script — Qwen3.6-35B-A3B fine-tune env (Blackwell: RTX PRO 6000 / RTX 50-series / B100-B200)
# วาง script นี้ในช่อง "On-start script" ตอนสร้าง instance บน Vast.ai (ก่อนกด Rent)
set -euo pipefail

echo "=== Constistant fine-tune setup — Qwen3.6-35B-A3B + Unsloth (Blackwell) ==="

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

=== Setup ติดตั้งเสร็จ ===

ขั้นต่อไป (ทำมือ):

1) เช็คสภาพแวดล้อมก่อน (สำคัญ — ทำก่อนอัปโหลดอะไรทั้งนั้น):
     python verify_env.py

2) อัปโหลด data_before_tune/ ทั้งโฟลเดอร์ (train.jsonl, val.jsonl, images/,
   train_qwen36.py, eval_fields.py) เข้า /workspace/tune/

3) วัด baseline ก่อนทูน:
     python eval_fields.py --base --limit 20

4) ทดสอบ 5 steps ก่อนรันเต็ม (train_qwen36.py ยังไม่เคยรันจริง):
   แก้ SFTConfig ชั่วคราวใส่ max_steps=5 (คอมเมนต์ num_train_epochs ออก) แล้ว
     python train_qwen36.py
   ผ่าน step แรกไหมก่อนค่อยเอา max_steps=5 ออกแล้วรันเต็ม 3 epoch

5) วัดผลหลังเทรน:
     python eval_fields.py --adapter outputs_qwen36/lora

MSG
