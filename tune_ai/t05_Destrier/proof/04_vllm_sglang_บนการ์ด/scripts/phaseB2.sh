#!/bin/bash
# phase B บนการ์ด: เปิดตัวเสิร์ฟ 1 ตัว (vllm | sglang | unsloth) → ด่าน D → วัด micro → วัดทั้งบ้าน → ปิด
#   bash phaseB.sh vllm|sglang|unsloth [house]   (ไม่ใส่ house = วัดแค่ micro)
# คำสั่งเปิดตัวเสิร์ฟมาจาก launch_<engine>.txt ที่สร้างบนคอมด้วย presentation.launch_cmd() ตัวจริง
# (เปลี่ยนแค่ path โมเดล + python ของ venv) → ทดสอบ flag ชุดเดียวกับที่ GO.bat ข้อ 2/3 ใช้
set -u
E=$1; HOUSE=${2:-}
FT=/workspace/ft; L=$FT/logs; OUT=$FT/out
PY=/venv/main/bin/python
W="env PYTHONPATH=/workspace/wdeps PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 PURSON_QUIET=1 $PY"
PAT='[s]erve_purson[.]py|[v]llm[.]entrypoints|[s]glang[.]launch_server'
step(){ echo; echo "=== $(date '+%F %T') [$E] $1"; }
ok(){ touch $FT/DONE_$1; echo "--- DONE $1 $(date '+%T')"; }
fail(){ echo "!!! FAIL $1"; touch $FT/FAIL_$1; pkill -f "$PAT"; exit 1; }
cd $FT/wk/worker || exit 1

if pgrep -f "$PAT" > /dev/null; then fail ${E}_busy; fi
step "เปิดตัวเสิร์ฟ"
nvidia-smi --query-gpu=memory.used --format=csv,noheader
T0=$(date +%s)
setsid --fork nohup bash -c "$(cat $FT/launch_$E.txt)" > $L/serve_$E.log 2>&1 < /dev/null &
sleep 20
while :; do
  if curl -sf -m 5 localhost:8000/v1/models > /dev/null; then break; fi
  if ! pgrep -f "$PAT" > /dev/null; then echo "ตัวเสิร์ฟตาย:"; tail -40 $L/serve_$E.log; fail ${E}_serve; fi
  if [ $(( $(date +%s) - T0 )) -gt 3600 ]; then tail -40 $L/serve_$E.log; fail ${E}_serve_timeout; fi
  sleep 15
done
echo "พร้อมใน $(( $(date +%s) - T0 )) วิ"; echo "$(( $(date +%s) - T0 ))" > $L/ready_s_$E
nvidia-smi --query-gpu=memory.used --format=csv,noheader

if [ "$E" != unsloth ]; then
  step "ด่าน D (logprobs เทียบ merged)"
  $PY $FT/tune/verify_merge.py --probe-server http://localhost:8000 --ref $FT/mrg.pt \
      --merged /workspace/destrier_merged 2>&1 | tee $L/probeD_$E.log
fi

step "วัด micro (pass0 5 หน้า + section 1 หน้า)"
$W bench_house.py micro --job $FT/bench/job_83b8e52c.json --images $FT/bench/img83 --out $OUT \
   --label ${E}_micro --prompts $FT/wk/training/tune_ai/t04_Purson --pages ${PAGES:-1,19,20,22,25} --tasks ${TASKS:-22:section} --repeat ${REPEAT:-1} \
   > $L/bench_${E}_micro.log 2>&1 && ok ${E}_micro || echo "micro ล้ม (ดู log) — ไปต่อ"
tail -25 $L/bench_${E}_micro.log

if [ "$HOUSE" = house ]; then
  step "วัดทั้งบ้าน 83b8e52c (29 หน้า, worker ตัวจริง)"
  $W bench_house.py house --job $FT/bench/job_83b8e52c.json --images $FT/bench/img83 --out $OUT \
     --label ${E}_house --prompts $FT/wk/training/tune_ai/t04_Purson \
     > $L/bench_${E}_house.log 2>&1 && ok ${E}_house || echo "house ล้ม (ดู log)"
  tail -40 $L/bench_${E}_house.log
  # บ้านจากเน็ต 3 หลัง (แบบบ้านเพื่อประชาชน กรมโยธาฯ — ไม่เคยอยู่ใน json_แก้ไขแล้ว) ไม่มีเฉลย
  for J in $FT/bench/web/job_*.json; do
    [ -f "$J" ] || continue
    N=$(basename $J .json); N=${N#job_}
    step "วัดบ้านจากเน็ต $N"
    $W bench_house.py house --job $J --images $FT/bench/web/img_$N --out $OUT \
       --label ${E}_$N --prompts $FT/wk/training/tune_ai/t04_Purson \
       > $L/bench_${E}_$N.log 2>&1 && ok ${E}_$N || echo "$N ล้ม (ดู log)"
    tail -12 $L/bench_${E}_$N.log
  done
fi

step "ปิดตัวเสิร์ฟ"
pkill -f "$PAT"; sleep 15; pkill -9 -f "$PAT"; sleep 5
nvidia-smi --query-gpu=memory.used --format=csv,noheader
ok phaseB_$E
