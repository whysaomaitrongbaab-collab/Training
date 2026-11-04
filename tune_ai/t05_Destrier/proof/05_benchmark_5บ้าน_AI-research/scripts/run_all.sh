#!/bin/bash
# รันทั้ง 5 บ้านต่อกันผ่าน worker ตัวจริง (bench_house.py) บนการ์ด vLLM ผ่าน tunnel · จดเวลาทุกคำขอ
B="D:/Temp/claude/3049db1b73f5b7d5/c641593e-2919-41af-bebc-66157c3c1ea4/scratchpad/bench5"
WD="d:/00mk/steel project/งานสมบูรณ์/Constistant/server/purson-worker"
PR="d:/00mk/steel project/training/Training/tune_ai/t04_Purson"
cd "$WD" || exit 1
for T in TEST-01 TEST-02 TEST-03 TEST-04 TEST-05; do
  echo "=== $T เริ่ม $(date +%H:%M:%S)"
  s=$(date +%s)
  PYTHONIOENCODING=utf-8 python -u bench_house.py house --job "$B/$T/job.json" --images "$B/$T/img" --out "$B/out/$T" --label vllm --prompts "$PR" > "$B/$T.log" 2>&1
  echo "=== $T จบ exit=$? ใช้ $(( $(date +%s) - s )) วิ ($(date +%H:%M:%S))"
done
echo "=== ALL_DONE $(date +%H:%M:%S)"
