#!/bin/bash
# Vast.ai on-start script — t05 "Courser": Qwen3.6-35B-A3B + Unsloth, 4 pass, k-fold 2
# (มะขามเคาะ 2026-08-30/31 — ดู t05_workflow.md) เช่า 4 การ์ดพร้อมกันคืนนี้ (fold0+fold1 ×
# Courser+Voldemort) — สคริปต์นี้ใช้กับเครื่อง Courser ทั้งสองใบ (fold0/fold1) เหมือนกัน
# ต่างกันแค่ตอนรัน export FOLD=0 หรือ FOLD=1
#
# ⚠️ ไฟล์นี้ต้องเป็น LF เท่านั้น — CRLF ทำให้ `set -euo pipefail` พังทันที
#    ถ้าแก้บน Windows แล้วไม่แน่ใจ: tr -d '\r' < onstart.sh | ssh ... "bash -s"
set -euo pipefail

echo "=== Constistant fine-tune setup — t05 Courser (Qwen3.6-35B-A3B, Unsloth) ==="

pip install --upgrade pip || true
pip install unsloth trl peft accelerate bitsandbytes
pip install pillow
# xgrammar บังคับทุก subtask/pass (มะขามสั่ง 2026-08-24/29) — ไม่ใช่แค่ตอน infer
pip install xgrammar
# push_to_hub อัตโนมัติตอนเทรน (train_t05_courser.py ตั้งไว้แล้ว) ต้องมี hub ตัวนี้
pip install "huggingface_hub>=0.24"

mkdir -p /workspace/tune
cd /workspace/tune

cat <<'MSG'

=== Setup t05 Courser เสร็จ ===

ขั้นต่อไป (ตามลำดับ ห้ามข้าม — t05_workflow.md Phase 0):

1) อัปโหลดทั้งโฟลเดอร์ t05_Courser/ เข้า /workspace/tune/
   ต้องมี: train_fold{0,1}.jsonl, val_fold{0,1}.jsonl, train_t05_courser.py
   + รูปที่ path อ้างถึง (image/<บ้าน>/…, marked_t5/…) — เทียบรากรีโป Training ทั้งหมด

2) export HF_TOKEN=hf_...XCRE   (token ชื่อ "t44", FINEGRAINED — พิมพ์เองบน session นี้
   ห้ามส่งผ่านแชท) — huggingface_hub อ่าน env นี้เองอัตโนมัติ ไม่ต้อง hf auth login แยก

3) ★ ทดสอบสั้นก่อนเสมอ (rule_of_tune ข้อ 4) — ห้ามข้าม:
     TEST_STEPS=5 FOLD=0 python3 train_t05_courser.py    # เครื่องนี้ทำ fold0
     TEST_STEPS=5 FOLD=1 python3 train_t05_courser.py    # อีกเครื่องทำ fold1
   ต้องเห็นก่อนไปต่อ:
     - assert "~7680 tokens/ภาพ" ผ่าน (ไม่ใช่ ~200 — กัน 512px silent resize)
     - seq ยาวสุด < MAX_LENGTH (45,839 วัดจริงแล้ว < cap 47,104)
     - ไม่ OOM, loss ลดจริง

4) เทรนเต็ม 2 epochs (แก้ 3→2, 2026-08-31 — ดู t05_workflow.md §F):
     FOLD=0 python3 train_t05_courser.py 2>&1 | tee train_fold0.log
     FOLD=1 python3 train_t05_courser.py 2>&1 | tee train_fold1.log
   push_to_hub อัตโนมัติทุก save_steps (25) → dacarokann/Courser_a (fold0) / Courser_b (fold1)

5) ⛔ verify-after-push ก่อน destroy ทุกครั้ง (Day-of-Shame guard ใหม่ — push_to_hub อัปเงียบๆ
   ได้ถ้าเน็ตหลุดกลางทาง ต้องเช็คจริงว่าไฟล์ขึ้น HF ครบไม่ใช่แค่สคริปต์จบแบบไม่ error):
     python3 ../verify_hf_push.py --repo dacarokann/Courser_a --local-dir outputs_t05_fold0
     python3 ../verify_hf_push.py --repo dacarokann/Courser_b --local-dir outputs_t05_fold1
   ต้องเห็น "✅ PASS" เท่านั้นก่อน destroy instance นั้น

⛔ ห้าม destroy instance จนกว่า verify-after-push ผ่าน (ข้อ 5) — ไม่ต้องปิดคอมทำงาน
   (เครื่อง มะขาม) หลังจบ ปล่อยไว้ได้ตามปกติ

MSG
