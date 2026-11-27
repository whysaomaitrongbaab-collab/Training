#!/bin/bash
# stop_server.sh — ปิด vLLM แล้วพิสูจน์ว่าหายหมดจริงก่อนเปิดตัวใหม่ (rule_of_tune Lesson 24) · ⚠️ UNTESTED (ร่าง 11 พ.ย. 69)
# เช็คตัวแม่ (api_server) ตัวลูก (VLLM::*) งานคอมไพล์ kernel (nvcc/ninja/cicc/ptxas) และหน่วยความจำ GPU ว่างจริง
# ตอนสั่งปิดยังมีงานคอมไพล์ค้าง = cache ของ FlashInfer อาจครึ่งๆ กลางๆ → ย้ายไปข้างๆ ไม่ให้ตัวใหม่ใช้ร่วม
set -u
SRV='[v]llm[.]entrypoints|[V]LLM::'
JIT='[n]vcc|[n]inja|[c]icc|[p]txas'
pgrep -f "$JIT" > /dev/null && HALF=1 || HALF=0
pkill -f "$SRV"; sleep 15; pkill -9 -f "$SRV"; pkill -9 -f "$JIT"; sleep 5
LEFT=""; USED=""
for n in $(seq 1 24); do
  LEFT=$(pgrep -af "$SRV|$JIT" | head -5)
  USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -dc 0-9)
  if [ -z "$LEFT" ] && [ "${USED:-99999}" -lt 2000 ]; then
    if [ $HALF = 1 ] && [ -d /root/.cache/flashinfer ]; then
      mv /root/.cache/flashinfer /root/.cache/flashinfer.half_$(date +%s)
      echo "ย้าย cache FlashInfer ที่อาจคอมไพล์ไม่จบไว้ข้างๆ"
    fi
    echo "ปิดสะอาด: ไม่มี process ค้าง · GPU ใช้ ${USED} MiB"
    exit 0
  fi
  sleep 5
done
echo "⛔ ยังปิดไม่หมด — ห้ามเปิดตัวใหม่: ${LEFT:-ไม่มี process แต่ GPU ยังใช้ ${USED} MiB}"
nvidia-smi
exit 1
