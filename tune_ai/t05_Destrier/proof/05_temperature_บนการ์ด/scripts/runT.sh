#!/bin/bash
# รอบวัด temperature (3 ต.ค. เย็น · มะขามสั่งข้อ 4): merge ใหม่ → vLLM แบบ production → ด่าน D เทียบ mrg.pt รอบเช้า
# → micro 4 ค่า T × 4 รอบ → ทั้งบ้าน (83b8e52c + บ้านเน็ตที่เคยวน) ที่ T ต่ำ
# ห้าม temperature 0 แบบลวกๆ: เคยทำให้พ่นภาษาจีน แต่รอบนั้นถอด repetition_penalty พร้อมกัน แยกต้นเหตุไม่ได้ → วัดซ้ำที่นี่
set -u
FT=/workspace/ft; L=$FT/logs; OUT=$FT/out; mkdir -p $L $OUT
PY=/venv/main/bin/python
PAT='[v]llm[.]entrypoints'
step(){ echo; echo "=== $(date '+%F %T') $1"; }
ok(){ touch $FT/DONE_$1; echo "--- DONE $1 $(date '+%T')"; }
fail(){ echo "!!! FAIL $1"; touch $FT/FAIL_$1; pkill -f "$PAT"; exit 1; }

step "venv vLLM แบบ production (uv, คนละ venv กับ /venv/main) — ขนานกับ phase A"
export PATH=$HOME/.local/bin:$PATH
command -v uv > /dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh > $L/uv_install.log 2>&1
export PATH=$HOME/.local/bin:$PATH
( { uv venv /workspace/venv_prodvllm --python 3.12 && \
    uv pip install --python /workspace/venv_prodvllm/bin/python vllm==0.30.0 \
      nvidia-cuda-nvcc==13.0.88 nvidia-cuda-crt==13.0.88 nvidia-nvvm==13.0.88 nvidia-cuda-cccl==13.0.85; } \
    > $L/venv_prodvllm.log 2>&1 && touch $FT/DONE_venv_prodvllm || touch $FT/FAIL_venv_prodvllm ) &
VPID=$!

step "deps ของ worker + เรนเดอร์บ้านเน็ต (หลัง pip ของ onstart จบ)"
while pgrep -f '[v]env/main/bin/python -m pip install -U' > /dev/null; do sleep 10; done
$PY -m pip install --target /workspace/wdeps requests opencv-python-headless pymupdf > $L/wdeps.log 2>&1 || fail wdeps
mkdir -p $FT/bench/web
PYTHONPATH=/workspace/wdeps $PY $FT/render_jobs.py $FT/webpdf $FT/bench/web > $L/render.log 2>&1 || fail render
cat $L/render.log

step "phase A (โหลด → ซ่อม → merge → ตรวจ A+B) — ข้าม C เพราะด่าน D เทียบ mrg.pt รอบเช้าแทน"
touch $FT/DONE_verifyC
bash $FT/phaseA.sh > $L/phaseA.log 2>&1 || { tail -30 $L/phaseA.log; fail phaseA; }
tail -12 $L/phaseA.log
wait $VPID
[ -f $FT/DONE_venv_prodvllm ] || { tail -20 $L/venv_prodvllm.log; fail venv_prodvllm; }

step "เปิด vLLM (คำสั่งจาก presentation.launch_cmd ตัวจริง)"
T0=$(date +%s)
setsid --fork nohup bash -c "$(cat $FT/launch_prodvllm.txt)" > $L/serve_prodvllm.log 2>&1 < /dev/null &
sleep 20
while :; do
  curl -sf -m 5 localhost:8000/v1/models > /dev/null && break
  pgrep -f "$PAT" > /dev/null || { tail -40 $L/serve_prodvllm.log; fail serve; }
  [ $(( $(date +%s) - T0 )) -gt 3600 ] && { tail -40 $L/serve_prodvllm.log; fail serve_timeout; }
  sleep 15
done
echo "พร้อมใน $(( $(date +%s) - T0 )) วิ" | tee $L/ready_s

step "ด่าน D เทียบ fingerprint ของ merged รอบเช้า (ผ่าน = merge ซ้ำได้โมเดลเดิม + ตัวเสิร์ฟคำนวณถูก)"
$PY $FT/tune/verify_merge.py --probe-server http://localhost:8000 --ref $FT/mrg.pt \
    --merged /workspace/destrier_merged 2>&1 | tee $L/probeD.log

W="env PYTHONPATH=/workspace/wdeps PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 PURSON_QUIET=1 $PY"
PR=$FT/wk/training/tune_ai/t04_Purson
cd $FT/wk/worker || fail cd
for T in 0.7 0.4 0.2 0.0; do
  step "micro T=$T (section 22 · plan_beam 20 · plan_footing 19 × 4 รอบ)"
  $W bench_house.py micro --job $FT/bench/job_83b8e52c.json --images $FT/bench/img83 --out $OUT \
     --label micro_T$T --prompts $PR --pages 1,19 --tasks 22:section,20:plan_beam,19:plan_footing \
     --repeat 4 --temperature $T > $L/bench_micro_T$T.log 2>&1 && ok micro_T$T || echo "micro T=$T ล้ม"
  tail -3 $L/bench_micro_T$T.log
done

for T in 0.2 0.4; do
  step "ทั้งบ้าน 83b8e52c T=$T"
  $W bench_house.py house --job $FT/bench/job_83b8e52c.json --images $FT/bench/img83 --out $OUT \
     --label house_T$T --prompts $PR --temperature $T > $L/bench_house_T$T.log 2>&1 && ok house_T$T
  for N in dpt13226_1fl dpt13244_1fl; do
    step "บ้านเน็ต $N T=$T"
    $W bench_house.py house --job $FT/bench/web/job_$N.json --images $FT/bench/web/img_$N --out $OUT \
       --label ${N}_T$T --prompts $PR --temperature $T > $L/bench_${N}_T$T.log 2>&1 && ok ${N}_T$T
  done
done

step "ปิดตัวเสิร์ฟ"
pkill -f "$PAT"; sleep 15; pkill -9 -f "$PAT"
ok runT
