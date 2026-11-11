#!/bin/bash
# t07 Palfrey — เทรน 1 fold บนการ์ด (D10) · ⚠️ ไฟล์ต้อง LF เท่านั้น
#   cd /workspace/Training/tune_ai/t07_Palfrey
#   setsid nohup bash run_fold.sh 0 > train_fold0.log 2>&1 < /dev/null &
# ลองสูงสุด 3 ครั้ง: ครั้งแรกตาม RESUME ที่ส่งมา (ค่าเริ่ม 0) · ครั้งที่ 2-3 = RESUME=1 (ต่อจาก checkpoint ล่าสุด)
#   ลองใหม่เฉพาะ CUDA OOM — ล้มแบบอื่น (config ผิด / push ล้ม / เวอร์ชันเพี้ยน) ลองซ้ำก็ล้มซ้ำ = เขียน FAIL ทันที
# ผล: DONE_fold$N (train_t07.py เขียนหลัง push + sha256 บน HF ตรง) → exit 0 · ไม่งั้น FAIL_fold$N → exit 1
# ⚠️ OOM ที่เกิดจากแถวยาวแถวเดียวอาจเกิดซ้ำที่ step เดิม (ลำดับข้อมูลเหมือนเดิมเป๊ะหลัง resume) — ครบ 3 = ให้คนตัดสิน
set -uo pipefail
N=${1:?ใส่เลข fold 0-3}
cd "$(dirname "$0")"
PY=${PY:-/venv/main/bin/python}
case $N in 0|1|2|3) ;; *) echo "⛔ fold ต้องเป็น 0-3 (ได้ $N)"; exit 1 ;; esac
if [ -n "${TEST_STEPS:-}" ] && [ "$TEST_STEPS" != 0 ]; then
  echo "⛔ run_fold.sh ใช้กับการเทรนจริงเท่านั้น — dry-run ใช้ gate2_smoke.sh"; exit 1
fi
# [review 11 พ.ย.] HF_HUB_DISABLE_XET=1 (Xet โหลดล้มกลางทางจริง 23 ก.ย.) · PYTHONUNBUFFERED=1 (print ของ python ผ่าน | tee ถูก
# buffer 8 KB — บรรทัด preflight/loss ไม่ขึ้น log จน buffer เต็ม ทำให้ watch4.sh อ่าน LOSS ไม่ได้และรอบแรกดูเหมือนเงียบ)
export FOLD=$N UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HUB_DISABLE_XET=1 PYTHONUNBUFFERED=1
fail() { echo "$(date '+%F %T') fold $N: $*" | tee "FAIL_fold$N"; exit 1; }
if [ -f "DONE_fold$N" ]; then echo "DONE_fold$N มีอยู่แล้ว: $(cat "DONE_fold$N")"; exit 0; fi
rm -f "FAIL_fold$N"
LETTER=$(echo abcd | cut -c$((N + 1)))
# ด่านก่อนเทรน 10+ ชม.: token เขียน repo ของ fold นี้ได้จริง และไม่ใช่ token กว้างของ PC (Lesson 22)
"$PY" gate2_hf_write.py --repo "dacarokann/Palfrey_$LETTER" || fail "ทดสอบเขียน HF ไม่ผ่าน (dacarokann/Palfrey_$LETTER)"
for A in 1 2 3; do
  LOG="attempt${A}_fold$N.log"
  R=${RESUME:-0}
  if [ "$A" -gt 1 ]; then R=1; fi
  echo "=== $(date '+%F %T') fold $N attempt $A/3 RESUME=$R ==="
  RESUME=$R "$PY" train_t07.py 2>&1 | tee "$LOG"
  RC=${PIPESTATUS[0]}
  if [ -f "DONE_fold$N" ]; then echo "✓ fold $N เสร็จ (attempt $A): $(cat "DONE_fold$N")"; exit 0; fi
  if grep -qE 'OutOfMemoryError|CUDA out of memory|CUDA error: out of memory' "$LOG"; then
    [ "$A" -lt 3 ] || break
    echo "⚠️ $(date '+%F %T') CUDA OOM (attempt $A/3, rc=$RC) — รอ 30 วิแล้วต่อด้วย RESUME=1"
    sleep 30
    continue
  fi
  fail "ล้มแบบไม่ใช่ OOM (attempt $A, rc=$RC) — ดู $LOG"
done
fail "CUDA OOM ครบ 3 ครั้ง — ต้องให้คนตัดสิน (ลดภาพ gridline / การ์ด VRAM ใหญ่กว่า) ดู attempt*_fold$N.log"
