#!/bin/bash
# run_queue_elements.sh — ต่อจากคิวเดิม แต่ตัด notes/gridline ทิ้ง (มะขามสั่ง 2026-08-31
# "ทดสอบเน้นหน้าหา element พอ") เหลือเฉพาะหน้าที่มี elements[] จริง: plan_beam (smoke)
# + 8 หน้าบ้านไทยพอเพียง3 (เป็นหน้าแปลน/รูปตัดเกือบทั้งหมด น่าจะมี element)
set -u
cd /workspace/Training/tune_ai/t05_Courser
: "${HF_TOKEN:?set HF_TOKEN before running (export HF_TOKEN=...)}"
export LD_LIBRARY_PATH=/opt/conda/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}
PY=/workspace/infer_env/bin/python
OUT=/workspace/queue_out

run_one() {
  local src="$1"
  local label="$2"
  local outfile="$OUT/${label}.json"
  echo ">>> $label ($src)"
  timeout 1500 "$PY" worker_page.py --source "$src" --out "$outfile" > "$OUT/${label}.log" 2>&1
  rc=$?
  if [ $rc -eq 124 ]; then
    echo "!!! $label เกิน 25 นาที → xgrammar retry"
    pkill -9 -f worker_page.py 2>/dev/null; sleep 5
    timeout 1500 "$PY" worker_page.py --source "$src" --xgrammar --out "$outfile" > "$OUT/${label}_xgr.log" 2>&1
    rc=$?
    if [ $rc -eq 124 ]; then
      echo "!!! $label ยังเกิน 25 นาทีแม้ใช้ xgrammar — ข้าม"
      pkill -9 -f worker_page.py 2>/dev/null; sleep 5
    fi
  fi
  echo "<<< $label rc=$rc"
}

if [ ! -f "$OUT/smoke_plan_beam.json" ]; then
  run_one "val:plan_beam" "smoke_plan_beam"
fi

for n in 03 10 19 28 36 46 55 62; do
  f="$OUT/pure_power_page$n.json"
  [ -f "$f" ] && { echo "--- pure_power_page$n มีผลแล้ว ข้าม ---"; continue; }
  run_one "house:$n" "pure_power_page$n"
done

echo "=== QUEUE_ELEMENTS_DONE ==="
