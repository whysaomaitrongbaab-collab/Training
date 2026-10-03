#!/bin/bash
# เฝ้าการ์ด — จบ (ปลุก Claude) เมื่อ: เจอ marker ที่รอ / เจอ FAIL_ ใหม่ / ssh ไม่ติด 3 รอบติด / เกินเวลา
#   bash watch.sh <marker ที่รอ เช่น DONE_phaseA> <นาทีสูงสุด> [log ที่จะ tail]
# บรรทัด marker ขึ้นต้นด้วย MARKERS: เสมอ — เดิมใช้ head -1 แล้วได้ข้อความต้อนรับของ vast แทน
# จึงมองไม่เห็น FAIL_download (12:44 วันที่ 3 ต.ค.) = ตัวเฝ้าที่ไม่เฝ้า (rule of tune บทเรียนข้อ 17)
WANT=$1; MAXMIN=${2:-120}; LOG=${3:-logs/phaseA.log}
S="ssh -p 11210 -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=15 root@103.112.1.36"
T0=$(date +%s); FAILS=0
while :; do
  OUT=$($S "cd /workspace/ft && echo MARKERS: \$(ls DONE_* FAIL_* 2>/dev/null | tr '\n' ' '); tail -4 $LOG 2>/dev/null; df -h /workspace | tail -1; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader" < /dev/null 2>&1)
  RC=$?
  MK=$(echo "$OUT" | grep '^MARKERS:')
  echo "[$(date '+%H:%M:%S')] rc=$RC"; echo "$OUT" | grep -v -E "Welcome to vast|Have fun"; echo
  if [ $RC -ne 0 ] || [ -z "$MK" ]; then FAILS=$((FAILS+1)); [ $FAILS -ge 3 ] && { echo "WATCH: SSH_FAIL x3"; exit 2; }
  else FAILS=0
    echo "$MK" | grep -q "FAIL_" && { echo "WATCH: FAIL marker"; exit 1; }
    echo "$MK" | grep -q "$WANT" && { echo "WATCH: got $WANT"; exit 0; }
  fi
  [ $(( $(date +%s) - T0 )) -gt $((MAXMIN*60)) ] && { echo "WATCH: timeout ${MAXMIN}m"; exit 3; }
  sleep 120
done
