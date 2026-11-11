#!/bin/bash
# t07 Palfrey — vast.ai onstart สำหรับ image vastai/pytorch:cuda-12.8.1-auto  (⚠️ ไฟล์ต้อง LF เท่านั้น)
# ใช้ /venv/main/bin/python ตรงๆ (image นี้ไม่มี python บน PATH) · รันซ้ำได้
#   PIN_SET=A   (ค่าเริ่ม) ชุด 3 ต.ค. ที่ merge/verify A-B-C ผ่าน — ต้องตรงกับ PIN_SETS ใน train_t07.py
#   PIN_SET=t05 ชุดเทรน Destrier (unsloth 2026.8.22 / zoo 2026.9.5 / peft 0.20.0) ⚠️ UNTESTED
#   FREEZE_FILE=<path> ลงตาม pip freeze ของการ์ดใบแรกเป๊ะแทนรายการ pin (Lesson 18a)
# ผล: /workspace/ONSTART_DONE หรือ /workspace/ONSTART_FAIL · log /workspace/onstart_t07.log
# ⛔ ห้ามใส่ token ในไฟล์นี้ — HF_TOKEN มะขามพิมพ์เองบนการ์ด (RUNBOOK_gate2-3.md)
set -euo pipefail
PY=/venv/main/bin/python
W=/workspace
mkdir -p $W
rm -f $W/ONSTART_DONE $W/ONSTART_FAIL
exec > >(tee -a $W/onstart_t07.log) 2>&1
trap 'echo "⛔ onstart_t07 ล้มที่บรรทัด $LINENO" | tee $W/ONSTART_FAIL' ERR
PIN_SET=${PIN_SET:-A}
echo "=== onstart_t07 $(date '+%F %T') PIN_SET=$PIN_SET FREEZE_FILE=${FREEZE_FILE:-} ==="
[ -x $PY ] || { echo "⛔ ไม่มี $PY — image ต้องเป็น vastai/pytorch:cuda-12.8.1-auto"; false; }

# Blackwell sm120 (RTX PRO 6000) — ต้องตั้งก่อนลงอะไรที่ compile CUDA kernel [t02]
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-12.0}
CAP=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 || true)
[ "$CAP" = "$TORCH_CUDA_ARCH_LIST" ] || echo "⚠️ compute_cap=$CAP ≠ TORCH_CUDA_ARCH_LIST=$TORCH_CUDA_ARCH_LIST (ชุดนี้ทดสอบบน sm120 เท่านั้น)"
# [review 11 พ.ย.] HF_HUB_DISABLE_XET=1 — Xet พังจริงกลางการโหลดฐาน 72 GB ตอนสาธิต 23 ก.ย. (โหลดไป 9.1 GB แล้วโยน
# "Background writer channel closed" · presentation.py SERVE_ENV / vllm_build_t07.sh ปิดไว้แล้ว) · ปิดแล้วอัป adapter ก็ไปทาง LFS
# ตามที่ sha256 ที่ train_t07.py ตรวจเทียบกับ HF คาดหวัง · ต้องตั้งก่อน prefetch ข้างล่าง (nohup ลูกสืบทอด env นี้)
export UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HUB_DISABLE_XET=1
rc() { grep -qxF "$1" ~/.bashrc 2>/dev/null || echo "$1" >> ~/.bashrc; }
rc "export TORCH_CUDA_ARCH_LIST=$TORCH_CUDA_ARCH_LIST"
rc "export UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert"
rc "export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
rc "export HF_HUB_DISABLE_XET=1"
rc "export PIN_SET=$PIN_SET"

# torch ต้องเป็นตัว cu128 ที่ image ติดมา — ไม่มี/ผิดรุ่นค่อยลงจาก index cu128 (PyPI ให้ cu130)
TV="2.11.0+cu128 0.26.0+cu128"
tv() { $PY -c 'import torch,torchvision;print(torch.__version__,torchvision.__version__)' 2>/dev/null || echo none; }
if [ "$(tv)" != "$TV" ]; then
  echo "torch/torchvision = $(tv) → ลง 2.11.0/0.26.0 จาก cu128"
  $PY -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
fi
[ "$(tv)" = "$TV" ] || { echo "⛔ torch/torchvision = $(tv) ไม่ใช่ $TV"; false; }

COMMON="trl==0.24.0 transformers==5.5.0 accelerate==1.15.0 bitsandbytes==0.50.2 xgrammar==0.2.8 huggingface_hub==1.30.0 tokenizers==0.22.2 safetensors==0.8.0 datasets==4.3.0 xformers==0.0.35 triton==3.6.0 cut-cross-entropy==25.1.1 pillow==12.3.0 hf-xet==1.6.0"
case $PIN_SET in
  A)   PINS="unsloth==2026.9.14 unsloth_zoo==2026.9.9 peft==0.21.2 torchao==0.18.0 $COMMON" ;;
  t05) PINS="unsloth==2026.8.22 unsloth_zoo==2026.9.5 peft==0.20.0 $COMMON"; echo "⚠️ PIN_SET=t05 = UNTESTED" ;;
  *)   echo "⛔ PIN_SET ต้องเป็น A หรือ t05"; false ;;
esac
if [ -n "${FREEZE_FILE:-}" ]; then
  grep -v ' @ file://' "$FREEZE_FILE" > /tmp/freeze_clean.txt
  $PY -m pip install -r /tmp/freeze_clean.txt --extra-index-url https://download.pytorch.org/whl/cu128
else
  # ★ pip ครั้งเดียว ทุกตัว == (Lesson 18) · torch/torchvision ใส่กันไม่ให้ pip สลับตัว cu128 ที่ตรวจแล้ว
  $PY -m pip install $PINS torch==2.11.0 torchvision==0.26.0
fi
# peft รุ่นเก่า import symbol ที่ torchao ถอดไปแล้ว (t05 onstart ถอดทิ้ง)
if [ "$PIN_SET" = t05 ]; then $PY -m pip uninstall -y torchao || true; fi
[ "$(tv)" = "$TV" ] || { echo "⛔ pip เปลี่ยน torch เป็น $(tv)"; false; }
$PY - $PINS "torch==2.11.0+cu128" "torchvision==0.26.0+cu128" <<'EOF'
import sys
from importlib import metadata as m
bad = []
for a in sys.argv[1:]:
    n, v = a.split("==")
    try:
        got = m.version(n)
    except m.PackageNotFoundError:
        got = None
    if got != v:
        bad.append(f"  {n}: ต้องการ {v} ได้ {got}")
print("⛔ เวอร์ชันไม่ตรง:\n" + "\n".join(bad) if bad else "✓ เวอร์ชันตรงชุดที่ตรึงทุกตัว")
sys.exit(1 if bad else 0)
EOF
$PY -m pip freeze > $W/freeze_train.txt
echo "pip freeze → $W/freeze_train.txt ($(wc -l < $W/freeze_train.txt) บรรทัด)"

# โหลดฐานโมเดล 72 GB เบื้องหลังระหว่างส่ง bundle (public — ไม่ต้องใช้ token)
if ! pgrep -f '[s]napshot_download' >/dev/null; then
  nohup $PY -c "
from huggingface_hub import snapshot_download as s
for i in range(3):
    try:
        s('unsloth/Qwen3.6-35B-A3B'); print('PREFETCH_OK'); break
    except Exception as e:
        print('retry', i + 1, type(e).__name__, e)
" > $W/prefetch_base.log 2>&1 < /dev/null &
fi
date '+%F %T' > $W/ONSTART_DONE
cat <<MSG
=== onstart_t07 เสร็จ (PIN_SET=$PIN_SET) ===
ต่อไป: tune_ai/t07_Palfrey/RUNBOOK_gate2-3.md — โหลด bundle → sha256sum -c → แตก tar → พิมพ์ HF_TOKEN แบบจำกัดสิทธิ์
ฐานโมเดลกำลังโหลด: tail -f $W/prefetch_base.log (รอ PREFETCH_OK)
⛔ ห้าม vastai destroy จนกว่า adapter อยู่บน HF + verify_hf_push.py --sha ผ่าน (Day of Shame)
MSG
