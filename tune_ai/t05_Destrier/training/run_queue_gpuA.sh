#!/bin/bash
# run_queue_gpuA.sh — ทดสอบกำลังดิบบนบ้านแบบประหยัด1 (3 หน้า: 09 ฐานราก+เสา+คาน+พื้นรวมแผ่น,
# 10 โครงหลังคา, 12 รายละเอียดคาน) กติกาเดียวกับ gpu1: เกิน 25 นาที → xgrammar retry → ยังเกิน → ข้าม
set -u
cd /workspace
export LD_LIBRARY_PATH=/venv/main/lib:${LD_LIBRARY_PATH:-}
PY=/venv/main/bin/python
OUT=/workspace/queue_out
mkdir -p "$OUT"

run_one() {
  local src="$1"
  local label="$2"
  local outfile="$OUT/${label}.json"
  echo ">>> $label ($src)"
  timeout 1500 "$PY" worker_page_raw_pratyad.py --source "$src" --out "$outfile" > "$OUT/${label}.log" 2>&1
  rc=$?
  if [ $rc -eq 124 ]; then
    echo "!!! $label เกิน 25 นาที → xgrammar retry"
    pkill -9 -f worker_page_raw_pratyad.py 2>/dev/null; sleep 5
    timeout 1500 "$PY" worker_page_raw_pratyad.py --source "$src" --xgrammar --out "$outfile" > "$OUT/${label}_xgr.log" 2>&1
    rc=$?
    if [ $rc -eq 124 ]; then
      echo "!!! $label ยังเกิน 25 นาทีแม้ใช้ xgrammar — ข้าม"
      pkill -9 -f worker_page_raw_pratyad.py 2>/dev/null; sleep 5
    fi
  fi
  echo "<<< $label rc=$rc"
}

for n in 09 10 12; do
  run_one "house:$n" "gpuA_page$n"
done

echo "=== QUEUE_GPUA_DONE ==="
