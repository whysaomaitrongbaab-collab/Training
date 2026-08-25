#!/bin/bash
# Vast.ai on-start script — t03: Qwen3.6-35B-A3B per-subtask fine-tune env
# (Blackwell: RTX PRO 6000 / RTX 50-series) — ดัดแปลงจาก t02/onstart.sh ที่รันผ่านจริง
# ⚠️ ไฟล์นี้ต้องเป็น LF เท่านั้น — CRLF ทำให้ set -euo pipefail พังทันที
#    ถ้าไม่แน่ใจ: tr -d '\r' < onstart.sh | ssh ... "bash -s"
set -euo pipefail

echo "=== Constistant fine-tune setup — t03 Qwen3.6-35B-A3B + Unsloth (Blackwell) ==="

# Blackwell (compute capability 12.0) ต้องตั้งก่อนติดตั้งอะไรที่ compile CUDA kernel
export TORCH_CUDA_ARCH_LIST="12.0"
echo 'export TORCH_CUDA_ARCH_LIST="12.0"' >> ~/.bashrc

# || true จำเป็น — pip จาก apt ถอนตัวเองไม่ได้ (RECORD file not found) พังจริง 2026-07-20
pip install --upgrade pip || true
pip install "triton>=3.3.1"
pip install unsloth trl peft accelerate bitsandbytes
pip install pillow
# xgrammar บังคับสำหรับ t03 — กติกาถาวรของมะขาม: หน้า plan_beam ต้องแนบ grammar เสมอ
pip install xgrammar

# ไม่ติดตั้ง xformers — Blackwell ต้อง compile เอง เสี่ยงพัง; Unsloth ใช้ SDPA แทนได้

mkdir -p /workspace/tune
cd /workspace/tune

cat <<'MSG'

=== Setup t03 เสร็จ ===

ขั้นต่อไป (ตามลำดับ ห้ามข้าม — t03_workflow.md Phase 1):

1) อัปโหลด data_before_tune/ เข้า /workspace/tune/
   (train.jsonl 408, val.jsonl 44, images/ 353 ไฟล์, train_t03.py)

2) hf auth login  ← มะขามพิมพ์ token บน session นี้เอง (ห้ามส่งผ่านแชท)

3) ★ ทดสอบสั้นก่อนเสมอ (rule_of_tune ข้อ 4):
     TEST_STEPS=5 SKIP_DEMO=1 python3 train_t03.py
   ต้องเห็น:
     - "✓ batch แรก: ~5100 visual tokens" (ถ้า ~205 = ย่อ 512px → หยุดทันที)
     - "✓ ตัวอย่าง multi-image ยาวสุด: seq=..." ต้อง < 32768
     - "peak VRAM: XX GB" ← ตัดสินว่าเทรนเต็มไหวไหม

4) เทรนเต็ม 3 epochs:
     SKIP_DEMO=1 python3 train_t03.py 2>&1 | tee train.log
   (demo ท้ายรันข้ามไว้ก่อน — รันแยกทีหลังได้ ค้างเมื่อไหร่ kill ได้ adapter เซฟแล้ว)

5) backup adapter ขึ้น HF ก่อนคิดเรื่อง destroy (Mark-of-Shame):
     hf upload Sicilian44/qwen36-thai-rc-t03 outputs_t03/lora
   ⛔ อย่าใช้ repo ของ t01/t02

⛔ ห้าม destroy instance จนกว่าไฟล์ verify ครบบนเครื่องเรา และมะขามสั่งเอง

MSG
