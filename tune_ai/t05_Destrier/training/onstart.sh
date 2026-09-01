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

# Blackwell (compute capability 12.0, RTX PRO 6000 = การ์ดที่เช่ารอบนี้) ต้องตั้งก่อนติดตั้ง
# อะไรที่ compile CUDA kernel (bitsandbytes เป็นตัวหลักที่ compile) — [t02] บทเรียนเดิม, ไฟล์นี้
# ตกหล่นไปตอนเขียนรอบแรก 2026-08-31 พบระหว่างเช่าจริงคืนนี้ (ยังไม่ได้ยืนยันว่าถ้าไม่มีแล้วพังจริง
# แต่ t02 เจอมาแล้วครั้งหนึ่ง ไม่คุ้มเสี่ยงซ้ำ)
export TORCH_CUDA_ARCH_LIST="12.0"
echo 'export TORCH_CUDA_ARCH_LIST="12.0"' >> ~/.bashrc

pip install --upgrade pip || true
pip install unsloth trl peft accelerate bitsandbytes
pip install pillow
# ★ บังคับ transformers v5 — t05_workflow.md §B บันทึกไว้ตั้งแต่ต้นว่า "transformers v5 บังคับ"
# แต่ onstart รอบแรก (2026-08-31) ลืม pin → unsloth ดึง 4.57.6 มา แล้ว dry-run ตายด้วย
# `ImportError: Your transformers version of 4.57.6 does not support Qwen3.5. The minimum
# required version is 5.2.0` (KeyError: 'qwen3_5_moe' ใน CONFIG_MAPPING) — เจอจริงบนเครื่องเช่า
# ต้องติดตั้ง**หลัง** unsloth เสมอ ไม่งั้นโดน unsloth ดึงกลับไปเวอร์ชันเก่า
# ⚠️ ต้อง pin ให้อยู่ในหน้าต่าง [5.2.0, 5.5.0] เท่านั้น — ปลายทั้งสองข้างมีของจริงบังคับ:
#   ล่าง 5.2.0 = unsloth ปฏิเสธต่ำกว่านี้ ("does not support Qwen3.5")
#   บน  5.5.0 = unsloth 2026.8.22 ประกาศ `transformers<=5.5.0` (ลอง `>=5.2.0` เฉย ๆ แล้ว
#               pip ให้ 5.16.1 มา = ขัดกับ unsloth ทันที) — เจอจริงบนเครื่องเช่า 2026-08-31
pip install "transformers==5.5.0"
# ★ ถอด torchao ทิ้ง — เราเทรน bf16 LoRA ไม่แตะ torchao เลย แต่ peft 0.18.1 มี dispatcher
# ที่เรียก `from torchao.quantization import LinearActivationQuantizedTensor` ตอนสร้าง LoRA
# ซึ่ง torchao 0.18.0 ถอด symbol นั้นออกไปแล้ว → `get_peft_model()` ตายทันที (เจอจริง
# 2026-08-31 dry-run รอบ 2) · `dispatch_torchao` เช็ค `is_torchao_available()` ก่อน import
# ดังนั้น "ไม่มี torchao เลย" = ข้ามไปเงียบ ๆ ปลอดภัยกว่าไปไล่หาเวอร์ชันที่เข้ากันได้
pip uninstall -y torchao || true

# ★ unsloth ดึง torch cu130 มาลงบน image ที่เป็น CUDA 12.8 → ตอน JIT compile kernel
# (jiterator, เช่น reduction_prod_kernel) nvrtc หา `libnvrtc-builtins.so.13.0` ไม่เจอแล้วตาย
# กลางการเทรน — **ไฟล์มีอยู่จริง** แค่ไม่อยู่ใน library path (มากับ pip pkg `nvidia-cuda-nvrtc` 13.x)
# เจอจริง 2026-08-31 dry-run รอบ 4 · แก้ด้วยการชี้ LD_LIBRARY_PATH ไปที่นั่น ไม่ต้อง downgrade torch
CU13_LIB=$(python -c "import site,os;p=[os.path.join(s,'nvidia/cu13/lib') for s in site.getsitepackages()];print(next((x for x in p if os.path.isdir(x)),''))" 2>/dev/null)
if [ -n "$CU13_LIB" ]; then
  export LD_LIBRARY_PATH="$CU13_LIB:${LD_LIBRARY_PATH:-}"
  echo "export LD_LIBRARY_PATH=\"$CU13_LIB:\${LD_LIBRARY_PATH:-}\"" >> ~/.bashrc
  echo "cu13 nvrtc libs: $CU13_LIB"
fi
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

5) ⛔ verify-after-push — ต้องผ่านทุก fold (push_to_hub อัปเงียบ ๆ ล้มเหลวได้ถ้าเน็ตหลุด/
   token หมดอายุ แล้วสคริปต์ยัง exit 0 → "สคริปต์จบ" ไม่เท่ากับ "ไฟล์อยู่บน HF"):
     python3 ../verify_hf_push.py --repo dacarokann/Courser_a --local-dir outputs_t05_fold0
     (a=fold0 · b=fold1 · c=fold2 · d=fold3 — ทำครบทั้ง 4 ไม่ใช่แค่ตัวที่ดีที่สุด)
   ต้องเห็น "✅ PASS" เท่านั้น

6) รวมทุก fold เป็น "destrier" ตามสมการ k-fold (Σ (1/k) × adapter_i, k=4 → นน. 0.25 เท่ากัน):
     python3 ../merge_adapters_soup.py --push        # → dacarokann/destrier
   ทำหลังข้อ 5 ผ่านครบทุก fold เท่านั้น (ต้องมี adapter ครบก่อนถึงจะรวมได้)

7) ตรวจ Day of Shame ให้ครบทุกข้อ (เช็คลิสต์ใน t05_workflow.md §ลำดับปิดงาน)

⛔⛔ ห้าม `vastai destroy` จนกว่าข้อ 5-7 ผ่านครบ — destroy บน vast.ai **ลบถาวรทันที กู้ไม่ได้**
   (ต่างจาก stop ที่เก็บไฟล์ไว้) นี่คือสิ่งที่ทำให้เสีย adapter 7.5GB + merged 66GB + GGUF 21.2GB
   ไปทั้งหมดเมื่อ 2026-07-21 — ดู rule_of_tune §Mark of Shame
   ไม่ต้องปิดคอมทำงานของมะขามหลังจบ (ตัดขั้นนั้นออกจากรอบนี้)

MSG
