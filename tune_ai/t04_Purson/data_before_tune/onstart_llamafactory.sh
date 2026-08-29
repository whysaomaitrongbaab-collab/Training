#!/bin/bash
# Vast.ai on-start script — t04: InternVL3-78B QLoRA 4-bit via LLaMA-Factory
# (การ์ดใบเดียว 96GB, quantization_bit=4/bnb — มะขามเคาะ 2026-08-30, ดู t04_workflow.md)
# ⚠️ ไฟล์นี้ต้องเป็น LF เท่านั้น — CRLF ทำให้ set -euo pipefail พังทันที
#    ถ้าไม่แน่ใจ: tr -d '\r' < onstart_llamafactory.sh | ssh ... "bash -s"
#
# ⚠️ ต้องเช่าด้วย image ที่มี PyTorch >= 2.7.0 + CUDA 12.8 เท่านั้น (ยืนยันจาก search 2026-08-30):
#   RTX PRO 6000 = Blackwell (sm_120) — PyTorch < 2.7.0 ไม่รู้จัก sm_120 เลย จะพังตอนรัน ไม่ใช่แค่ compile
#   image ที่ใช้: pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel (มีจริงบน Docker Hub, ยืนยันแล้ว)
set -euo pipefail

echo "=== Constistant fine-tune setup — t04 InternVL3-78B QLoRA + LLaMA-Factory ==="

# Blackwell (compute capability 12.0, เช่น RTX PRO 6000) ต้องตั้งก่อนติดตั้งอะไรที่ compile CUDA
# kernel เสมอ (บทเรียนเดิมจาก onstart.sh ยุค t03 — bitsandbytes ก็ compile kernel เหมือนกัน)
export TORCH_CUDA_ARCH_LIST="12.0"
echo 'export TORCH_CUDA_ARCH_LIST="12.0"' >> ~/.bashrc

pip install --upgrade pip || true
pip install "transformers>=4.51.0" accelerate bitsandbytes
pip install git+https://github.com/hiyouga/LLaMA-Factory.git
# xgrammar ยังต้องใช้ตอน infer (มะขามสั่ง "ใส่ xgrammar ทุก pass") — probe tokenizer InternVL3
# ก่อนเชื่อว่าต่อกันได้ (rule_of_tune ข้อ 13 — ห้าม assume ตามตัวอย่าง lm-format-enforcer เดิม)
pip install xgrammar

mkdir -p /workspace/tune
cd /workspace/tune

cat <<'MSG'

=== Setup t04 (InternVL3-78B / LLaMA-Factory) เสร็จ ===

ขั้นต่อไป (ตามลำดับ ห้ามข้าม — t04_workflow.md Phase 0 ข้อ 6):

1) อัปโหลด data_before_tune/ เข้า /workspace/tune/
   ต้องมี: train_lf.json, val_lf.json, dataset_info.json, images/, train_t04_internvl3_qlora.yaml
   (ถ้ายังไม่แปลง: python build_dataset_llamafactory.py ก่อนอัป)

2) hf auth login  ← มะขามพิมพ์ token บน session นี้เอง (ห้ามส่งผ่านแชท)

3) ★ ทดสอบสั้นก่อนเสมอ (rule_of_tune ข้อ 4) — ยังไม่มี TEST_STEPS แบบ t03 ใน LLaMA-Factory
   ใช้ max_steps ชั่วคราวแทน (แก้ในไฟล์ yaml หรือ override ทาง CLI):
     llamafactory-cli train train_t04_internvl3_qlora.yaml --max_steps 5 --save_steps 5
   ต้องดู: VRAM peak (nvidia-smi ระหว่างรัน), ไม่ OOM, loss ลดลงจริง
   ⚠️ cutoff_len/image_max_pixels/lora_rank ในไฟล์ yaml เป็นค่าเริ่มต้นที่ยังไม่ verify —
   ดู log ว่ามี sample ไหนโดนตัด (truncated) หรือภาพโดนย่อผิดปกติไหมก่อนเทรนเต็ม

4) เทรนเต็ม 3 epochs:
     llamafactory-cli train train_t04_internvl3_qlora.yaml 2>&1 | tee train.log

5) backup adapter ขึ้น HF ก่อนคิดเรื่อง destroy (Mark-of-Shame):
     hf upload Sicilian44/Purson-weights outputs_t04/lora
   ⛔ อย่าใช้ repo ของ t01/t02/t03 · ชื่อ "Purson" = ชื่อจริงของรอบ t04 (มะขามย้ำ 2026-08-30)
   GGUF+mmproj (ถ้า verify ผ่านตาม t04_workflow.md Phase 0 ข้อ 14) ไปที่ repo แยก:
     hf upload Sicilian44/Purson-gguf <path-to-gguf>
   อย่าอัป Purson-gguf ถ้ายังไม่ verify ว่า merge+convert ผ่านจริง

⛔ ห้าม destroy instance จนกว่าไฟล์ verify ครบบนเครื่องเรา และมะขามสั่งเอง

MSG
