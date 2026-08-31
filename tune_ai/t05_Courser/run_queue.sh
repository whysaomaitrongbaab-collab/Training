#!/bin/bash
# run_queue.sh — เดิน smoke (3 หน้า val) แล้ว pure-power (8 หน้าบ้านไทยพอเพียง3) ทีละหน้า
# กติกามะขาม 2026-08-31: หน้าไหนเกิน 25 นาที (1500s) → ฆ่าทิ้ง รันซ้ำหน้านั้นด้วย --xgrammar
set -u
cd /workspace/Training/tune_ai/t05_Courser
: "${HF_TOKEN:?set HF_TOKEN before running (export HF_TOKEN=...)}"
export LD_LIBRARY_PATH=/opt/conda/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}
PY=/workspace/infer_env/bin/python
OUT=/workspace/queue_out
mkdir -p "$OUT"

run_one() {  # $1 = source (val:xxx หรือ house:NN), $2 = out label
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

run_one "val:gridline"  "smoke_gridline"
run_one "val:plan_beam" "smoke_plan_beam"
run_one "val:notes"     "smoke_notes"

for n in 03 10 19 28 36 46 55 62; do
  run_one "house:$n" "pure_power_page$n"
done

echo "=== QUEUE_ALL_DONE ==="
