#!/bin/bash
# Vast.ai on-start script — t44 "Voldemort": InternVL3-78B QLoRA 4-bit via LLaMA-Factory
# (มะขามเคาะ 2026-08-31 — ดู t44_workflow.md) เช่า 4 การ์ดพร้อมกันคืนนี้ (fold0+fold1 ×
# Courser+Voldemort) — สคริปต์นี้ใช้กับเครื่อง Voldemort ทั้งสองใบ (fold0/fold1) เหมือนกัน
# ต่างกันแค่ยาม train_t44_internvl3_fold0.yaml หรือ fold1.yaml
#
# ⚠️ ไฟล์นี้ต้องเป็น LF เท่านั้น — CRLF ทำให้ set -euo pipefail พังทันที
#    ถ้าไม่แน่ใจ: tr -d '\r' < onstart.sh | ssh ... "bash -s"
#
# ⚠️ ต้องเช่าด้วย image ที่มี PyTorch >= 2.7.0 + CUDA 12.8 เท่านั้น (บทเรียน t04):
#   RTX PRO 6000 = Blackwell (sm_120) — PyTorch < 2.7.0 ไม่รู้จัก sm_120 พังตอนรัน ไม่ใช่แค่ compile
#   image ที่ใช้: pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel
set -euo pipefail

echo "=== Constistant fine-tune setup — t44 Voldemort (InternVL3-78B QLoRA, LLaMA-Factory) ==="

export TORCH_CUDA_ARCH_LIST="12.0"
echo 'export TORCH_CUDA_ARCH_LIST="12.0"' >> ~/.bashrc

pip install --upgrade pip || true
pip install "transformers>=4.51.0" accelerate bitsandbytes
# ต้อง LLaMA-Factory >= 0.9.3 (crop_to_patches รองรับตั้งแต่ PR #7817 — ดู yaml comment)
pip install "llamafactory[torch]>=0.9.3" || pip install git+https://github.com/hiyouga/LLaMA-Factory.git
pip install xgrammar
pip install "huggingface_hub>=0.24"

mkdir -p /workspace/tune
cd /workspace/tune

cat <<'MSG'

=== Setup t44 Voldemort เสร็จ ===

ขั้นต่อไป (ตามลำดับ ห้ามข้าม — t44_workflow.md):

1) อัปโหลดทั้งโฟลเดอร์ t44_Voldemort/ **และ** t05_Courser/ เข้า /workspace/tune/ ในโครงเดิม
   (media_dir: ../.. ใน yaml ชี้กลับไปที่ root ของ Training repo — image/<บ้าน>/…,
   tune_ai/t05_Courser/marked_t5/… ต้องอยู่ที่เดิมเทียบกับ t44_Voldemort/)
   ต้องมี: train_fold{0,1}_lf.json, val_fold{0,1}_lf.json, dataset_info.json,
   train_t44_internvl3_fold{0,1}.yaml

2) export HF_TOKEN=hf_...XCRE   (token ชื่อ "t44", FINEGRAINED — พิมพ์เองบน session นี้
   ห้ามส่งผ่านแชท) — llamafactory-cli อ่าน env นี้เองอัตโนมัติ ไม่ต้อง hf auth login แยก

3) ⛔ ประตู go/no-go ~$2 ก่อนเทรนเต็มเสมอ (internvl_arm_dossier.md §4 ทาง ก — ทำครั้งเดียว
   ใช้ได้ทั้ง 2 fold ไม่ต้องทำซ้ำสองเครื่อง): โหลด base 4-bit + tiling เต็ม ไม่มี adapter
   แล้วให้อ่านแบบจริง 3-5 หน้า — อ่าน mark ออก (B2/C1/F1) = ไปต่อ, เพ้อ/ตอบบ้านผิดหลัง = หยุด

4) ★ ทดสอบสั้นก่อนเสมอ (rule_of_tune ข้อ 4) — เพิ่ม `max_steps: 5` ชั่วคราวในบรรทัดสุดท้าย
   ของ yaml (มี comment คั่นไว้แล้ว) แล้วรัน:
     llamafactory-cli train train_t44_internvl3_fold0.yaml   # เครื่องนี้ทำ fold0
     llamafactory-cli train train_t44_internvl3_fold1.yaml   # อีกเครื่องทำ fold1
   ต้องดู: VRAM peak ไม่ OOM, loss ลดจริง, token/ภาพ ~2,300-3,328 (ไม่ใช่ 256 — รัน
   ../t04_Purson/data_before_tune/probe_img_tokens.py ถ้าอยากยืนยันแยกก่อนก็ได้) — ลบ
   max_steps ออกก่อนรันเต็ม

5) เทรนเต็ม 2 epochs (แก้ 3→2, 2026-08-31):
     llamafactory-cli train train_t44_internvl3_fold0.yaml 2>&1 | tee train_fold0.log
     llamafactory-cli train train_t44_internvl3_fold1.yaml 2>&1 | tee train_fold1.log
   push_to_hub อัตโนมัติทุก save_steps (25) → dacarokann/Voldemort_a (fold0) / _b (fold1)

6) ⛔ verify-after-push ก่อน destroy ทุกครั้ง (Day-of-Shame guard ใหม่):
     python3 ../verify_hf_push.py --repo dacarokann/Voldemort_a --local-dir outputs_t44_fold0/lora
     python3 ../verify_hf_push.py --repo dacarokann/Voldemort_b --local-dir outputs_t44_fold1/lora
   ต้องเห็น "✅ PASS" เท่านั้นก่อน destroy instance นั้น

⛔ ห้าม destroy instance จนกว่า verify-after-push ผ่าน (ข้อ 6) — ไม่ต้องปิดคอมทำงาน
   (เครื่อง มะขาม) หลังจบ ปล่อยไว้ได้ตามปกติ

MSG
