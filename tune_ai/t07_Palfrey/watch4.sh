#!/bin/bash
# t07 Palfrey — เฝ้าการ์ดเทรนหลายใบจาก PC (git-bash) · ⚠️ ไฟล์ต้อง LF เท่านั้น
#   bash watch4.sh 'H0:P0 H1:P1 H2:P2 H3:P3' 900        # (นาทีสูงสุด) — รันผ่าน Claude Bash run_in_background ได้
# ทุก INTERVAL วิ (ค่าเริ่ม 600) ต่อการ์ด: MARKERS (DONE/FAIL) · PROC train/runner ALIVE/DEAD · OOM · step/loss ล่าสุด · GPU mem
# รอบแรกพิมพ์ทันที — อ่านรอบแรกด้วยตาเสมอว่ามีตัวเลขจริง (Lesson 17)
# exit 0 = ทุกใบ DONE · 1 = มี FAIL / DEAD โดยไม่มี DONE / โฟลเดอร์งานหาย · 2 = ssh ไม่ติด 3 รอบติดกัน (ใบใดใบหนึ่ง) · 3 = หมดเวลา
# ไม่มีทางไหนวนต่อเงียบๆ — ssh ล้ม / ผลว่าง / ไม่มี END_REPORT นับเป็น SSHFAIL ทุกครั้ง (Lesson 17 ข้อ 2-3)
set -u
HOSTS=${1:?"ใส่ 'host:port host:port ...'"}
MAXMIN=${2:?"ใส่นาทีสูงสุด"}
INTERVAL=${INTERVAL:-600}
RDIR=${REMOTE_DIR:-/workspace/Training/tune_ai/t07_Palfrey}
SSH=${SSH:-ssh}
read -r -d '' REMOTE <<'EOF'
cd "$RDIR" 2>/dev/null || { echo "DIR: missing $RDIR"; echo END_REPORT; exit 0; }
echo "MARKERS: $(ls DONE_fold* FAIL_fold* 2>/dev/null | tr '\n' ' ')"
for f in DONE_fold* FAIL_fold*; do [ -f "$f" ] && echo "  $f: $(head -c 300 "$f")"; done
T=$(pgrep -f '[t]rain_t07' >/dev/null 2>&1 && echo ALIVE || echo DEAD)
R=$(pgrep -f '[r]un_fold.sh' >/dev/null 2>&1 && echo ALIVE || echo DEAD)
echo "PROC: train=$T runner=$R"
echo "OOM: $(cat attempt*_fold*.log 2>/dev/null | grep -cE 'OutOfMemoryError|CUDA out of memory')"
L=$(ls -t train_fold*.log 2>/dev/null | head -1)
if [ -z "$L" ]; then echo "LOG: missing train_fold*.log"; else
  echo "STEP: $(tail -c 50000 "$L" | tr '\r' '\n' | grep -E '[0-9]+/[0-9]+ \[' | tail -1 | cut -c1-160)"
  echo "LOSS: $(tail -c 50000 "$L" | tr '\r' '\n' | grep -E "'loss'" | tail -1 | cut -c1-160)"
  echo "LAST: $(tail -c 50000 "$L" | tr '\r' '\n' | grep -v '^\s*$' | tail -1 | cut -c1-200)"
fi
echo "GPU: $(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader 2>&1 | head -1)"
echo END_REPORT
EOF
declare -A FAILS
T0=$(date +%s)
CYCLE=0
NH=$(wc -w <<<"$HOSTS")
while :; do
  CYCLE=$((CYCLE + 1))
  DONE=0; BAD=0; SSHX3=0
  echo "========== cycle $CYCLE · $(date '+%F %T') · $(( ($(date +%s) - T0) / 60 )) นาที =========="
  for HP in $HOSTS; do
    H=${HP%:*}; P=${HP##*:}
    OUT=$($SSH -p "$P" -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new \
          -o ServerAliveInterval=15 -o ServerAliveCountMax=4 "root@$H" "RDIR='$RDIR' bash -s" <<<"$REMOTE" 2>&1)
    RC=$?
    echo "--- $HP (rc=$RC)"
    if [ $RC -ne 0 ] || ! grep -q '^END_REPORT' <<<"$OUT"; then
      FAILS[$HP]=$(( ${FAILS[$HP]:-0} + 1 ))
      echo "  SSHFAIL ${FAILS[$HP]}/3: $(tail -3 <<<"$OUT" | tr '\n' ' ' | cut -c1-300)"
      [ "${FAILS[$HP]}" -ge 3 ] && SSHX3=1
      continue
    fi
    FAILS[$HP]=0
    grep -vE 'Welcome to vast|Have fun|^END_REPORT' <<<"$OUT" | sed 's/^/  /'
    MK=$(grep '^MARKERS:' <<<"$OUT")
    if grep -q 'FAIL_fold' <<<"$MK"; then echo "  ⛔ FAIL marker"; BAD=1
    elif grep -q 'DONE_fold' <<<"$MK"; then DONE=$((DONE + 1))
    elif grep -q '^DIR: missing' <<<"$OUT"; then echo "  ⛔ ไม่เห็นโฟลเดอร์งาน — REMOTE_DIR ผิด หรือ bundle ยังไม่แตก"; BAD=1
    elif grep -q 'PROC: train=DEAD runner=DEAD' <<<"$OUT"; then echo "  ⛔ DEAD โดยไม่มี DONE"; BAD=1
    fi
  done
  echo "SUMMARY: done=$DONE/$NH bad=$BAD ssh_fail_x3=$SSHX3"
  [ $BAD -eq 1 ] && { echo "WATCH: FAIL/DEAD — ปลุกคน"; exit 1; }
  [ $SSHX3 -eq 1 ] && { echo "WATCH: SSH_FAIL x3 — ปลุกคน (การ์ดอาจดับ/เครดิตหมด)"; exit 2; }
  [ $DONE -eq "$NH" ] && { echo "WATCH: ALL_DONE ($NH ใบ)"; exit 0; }
  [ $(( $(date +%s) - T0 )) -ge $((MAXMIN * 60)) ] && { echo "WATCH: timeout ${MAXMIN} นาที"; exit 3; }
  sleep "$INTERVAL"
done
