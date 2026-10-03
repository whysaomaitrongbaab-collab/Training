#!/bin/bash
# ต่อคิวหลัง runT: greedy (T=0) ชนะ micro (ผลนิ่ง + มาร์คดีสุด) แต่ greedy เสี่ยงวนซ้ำกับบ้านที่ไม่เคยเห็น
# → อ่านทั้งหลังที่ T=0: 83b8e52c + บ้านเน็ต 3 หลัง (13250 เพิ่งอัปโหลด)
set -u
FT=/workspace/ft; L=$FT/logs; OUT=$FT/out; PY=/venv/main/bin/python; PAT='[v]llm[.]entrypoints'
step(){ echo; echo "=== $(date '+%F %T') $1"; }
ok(){ touch $FT/DONE_$1; echo "--- DONE $1 $(date '+%T')"; }
until [ -f $FT/DONE_runT ] || ls $FT/FAIL_* > /dev/null 2>&1; do sleep 20; done
PYTHONPATH=/workspace/wdeps $PY $FT/render_jobs.py $FT/webpdf2 $FT/bench/web > $L/render2.log 2>&1
cat $L/render2.log
step "เปิด vLLM ใหม่ (cache kernel มีแล้ว)"
T0=$(date +%s)
setsid --fork nohup bash -c "$(sed 's#mv /root/.cache/flashinfer#true /root/.cache/flashinfer#' $FT/launch_prodvllm.txt)" > $L/serve_prodvllm2.log 2>&1 < /dev/null &
sleep 20
until curl -sf -m 5 localhost:8000/v1/models > /dev/null; do
  pgrep -f "$PAT" > /dev/null || { tail -30 $L/serve_prodvllm2.log; touch $FT/FAIL_serve2; exit 1; }
  sleep 15
done
echo "พร้อมใน $(( $(date +%s) - T0 )) วิ"
W="env PYTHONPATH=/workspace/wdeps PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 PURSON_QUIET=1 $PY"
PR=$FT/wk/training/tune_ai/t04_Purson
cd $FT/wk/worker
step "ทั้งบ้าน 83b8e52c T=0"
$W bench_house.py house --job $FT/bench/job_83b8e52c.json --images $FT/bench/img83 --out $OUT \
   --label house_T0.0 --prompts $PR --temperature 0 > $L/bench_house_T0.0.log 2>&1 && ok house_T0.0
for N in dpt13226_1fl dpt13244_1fl dpt13250_2fl; do
  step "บ้านเน็ต $N T=0"
  $W bench_house.py house --job $FT/bench/web/job_$N.json --images $FT/bench/web/img_$N --out $OUT \
     --label ${N}_T0.0 --prompts $PR --temperature 0 > $L/bench_${N}_T0.0.log 2>&1 && ok ${N}_T0.0
done
pkill -f "$PAT"; sleep 15; pkill -9 -f "$PAT"
ok runT2
