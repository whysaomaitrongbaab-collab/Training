#!/bin/bash
# run_bench_t07.sh — ด่าน 4: วัดผลกับตัวเสิร์ฟที่เปิดอยู่ที่ localhost:8000 (ไม่เปิด/ปิดตัวเสิร์ฟเอง)
# ⚠️ UNTESTED — ร่าง 11 พ.ย. 69 ยังไม่เคยรันบนการ์ดจริง · ดู RUNBOOK_gate4.md
#
#   bash run_bench_t07.sh <ชุด> [prompts] [รอบ]
#     t07       prompts ค่าเริ่มต้น /workspace/ft/wk/training/tune_ai/t07_Palfrey · 3 รอบ
#     destrier  ใส่ /workspace/ft/wk/training/tune_ai/t04_Purson (prompt ชุดที่ Destrier เทรนมา = production)
# ทุกคำขอ PURSON_CV_MERGE=0 (ฐาน 3 ต.ค. ไม่มีขั้นรวม CV) · temperature ตาม worker (0.7) ไม่ทับ
# prompt ต้องอยู่ระดับ tune_ai/<x>/ ไม่งั้น worker หา organize.py / cv_scan.py ไม่เจอแล้วส่งเต็มหน้าเงียบๆ (เช็คให้แล้ว)
# ผล: /workspace/ft/out/<ชุด>_house_r<N> · <ชุด>_<บ้านเน็ต>_r<N> · <ชุด>_micro  (รันซ้ำได้: ชุดที่มี DONE_bench_ ข้าม)
set -u
NAME=${1:?"ใส่ชื่อชุด เช่น t07 หรือ destrier"}
FT=/workspace/ft; L=$FT/logs; OUT=$FT/out; mkdir -p $L $OUT
PR=${2:-$FT/wk/training/tune_ai/t07_Palfrey}; RUNS=${3:-3}
PY=/venv/main/bin/python; WD=/workspace/wdeps
W="env PYTHONPATH=$WD PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 PURSON_QUIET=1 PURSON_CV_MERGE=0 $PY"
step(){ echo; echo "=== $(date '+%F %T') [$NAME] $1"; }
ok(){ touch $FT/DONE_$1; echo "--- DONE $1 $(date '+%T')"; }
fail(){ echo "!!! FAIL $1"; touch $FT/FAIL_$1; exit 1; }
have(){ [ -f $FT/DONE_$1 ]; }

curl -sf -m 5 localhost:8000/v1/models > /dev/null || fail bench_noserver
for f in _common.md pass0/prompt.md; do [ -f "$PR/$f" ] || { echo "ไม่มี $PR/$f"; fail bench_prompts; }; done
for s in gridline plan_footing plan_beam plan_slab section schedule notes; do
  [ -f "$PR/pass2/$s/prompt_$s.md" ] || { echo "ไม่มี $PR/pass2/$s/prompt_$s.md"; fail bench_prompts; }
done
{ [ -f "$PR/../t03/pass1_organize/organize.py" ] && [ -f "$PR/../../tools/cv_scan.py" ]; } || fail bench_prompt_depth

if ! have wdeps; then
  step "deps ของ worker (ตรึงตามรอบฐาน 3 ต.ค.: opencv 5.0.0.93 · pymupdf 1.28.2)"
  while pgrep -f '[v]env/main/bin/python -m pip install' > /dev/null; do sleep 10; done
  $PY -m pip install --target $WD requests==2.34.2 numpy==2.5.3 opencv-python-headless==5.0.0.93 pymupdf==1.28.2 \
    > $L/wdeps.log 2>&1 || { tail -20 $L/wdeps.log; fail wdeps; }
  env PYTHONPATH=$WD $PY -c "import cv2, pymupdf, requests; print('cv2', cv2.__version__, '| pymupdf', pymupdf.__version__)" \
    | tee -a $L/wdeps.log
  [ ${PIPESTATUS[0]} = 0 ] || fail wdeps
  ok wdeps
fi

if ! have render_web; then
  step "บ้านเน็ต 3 หลัง: ตรวจ sha256 ของ PDF (proof/04) แล้วเรนเดอร์ dpi 200 (pymupdf 1.28.2)"
  ( cd $FT/webpdf && sha256sum -c webpdf.sha256 ) || fail webpdf_sha
  mkdir -p $FT/bench/web
  env PYTHONPATH=$WD $PY $FT/render_jobs.py $FT/webpdf $FT/bench/web > $L/render.log 2>&1 || { cat $L/render.log; fail render; }
  cat $L/render.log
  ( cd $FT/bench/web && sha256sum img_*/page_*.png ) > $L/web_render_sha256.txt
  ok render_web
fi
( cd $FT/bench && sha256sum -c --quiet SHA256SUMS ) || fail bench83_sha

run(){   # run <ป้าย> <job> <โฟลเดอร์ภาพ>
  have bench_$1 && { echo "ข้าม $1 (เสร็จแล้ว)"; return 0; }
  rm -f $FT/FAIL_bench_$1
  step "วัด $1"
  ( cd $FT/wk/worker && $W bench_house.py house --job $2 --images $3 --out $OUT --label $1 --prompts $PR ) \
    > $L/bench_$1.log 2>&1 && ok bench_$1 || { touch $FT/FAIL_bench_$1; echo "⚠️ $1 ล้ม (ดู $L/bench_$1.log) — ไปต่อ"; }
  tail -4 $L/bench_$1.log
}
# วนเป็นรอบ (รอบ 1 ครบทุกบ้านก่อนรอบ 2) — เวลาหมดกลางทางยังได้ชุดที่เทียบกันได้ครบ
for r in $(seq 1 $RUNS); do
  run ${NAME}_house_r$r $FT/bench/job_83b8e52c.json $FT/bench/img83
  for N in dpt13226_1fl dpt13244_1fl dpt13250_2fl; do
    run ${NAME}_${N}_r$r $FT/bench/web/job_$N.json $FT/bench/web/img_$N
  done
done

if ! have bench_${NAME}_micro; then
  rm -f $FT/FAIL_bench_${NAME}_micro
  step "micro: pass0 หน้า 1,19 + section 22 · plan_beam 20 · plan_footing 19 ยิงซ้ำ 4 รอบ (ห้ามตัดสินคุณภาพจาก micro)"
  ( cd $FT/wk/worker && $W bench_house.py micro --job $FT/bench/job_83b8e52c.json --images $FT/bench/img83 --out $OUT \
      --label ${NAME}_micro --prompts $PR --pages 1,19 --tasks 22:section,20:plan_beam,19:plan_footing --repeat 4 ) \
    > $L/bench_${NAME}_micro.log 2>&1 && ok bench_${NAME}_micro || { touch $FT/FAIL_bench_${NAME}_micro; echo "⚠️ micro ล้ม"; }
fi
step "จบ — ผลอยู่ $OUT/${NAME}_* · ดึงกลับ PC แล้วให้คะแนนด้วย gate4/analyze_houses.py"
ls $FT | grep -E "^(DONE|FAIL)_bench_${NAME}_" | tr '\n' ' '; echo
ls $FT | grep -q -E "^FAIL_bench_${NAME}_" && exit 1 || exit 0
