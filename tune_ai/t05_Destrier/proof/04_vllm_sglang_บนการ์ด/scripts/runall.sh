#!/bin/bash
# รอ phase A จบ แล้วไล่ทดสอบตัวเสิร์ฟต่อกันเอง (การ์ดไม่ต้องนั่งว่างรอคนสั่ง)
# phase A ล้ม = หยุด ไม่ทดสอบต่อ (โมเดลที่ merge ไม่ผ่านด่าน → ตัวเลขคุณภาพเชื่อไม่ได้ ต้องให้คนดูก่อน)
cd /workspace/ft || exit 1
while [ ! -f DONE_phaseA ]; do
  ls FAIL_deps FAIL_download FAIL_fix FAIL_merge FAIL_verifyAB FAIL_verifyC* > /dev/null 2>&1 && { echo "phase A ล้ม — หยุด"; exit 1; }
  sleep 30
done
waitvenv(){ while [ ! -f DONE_venv_$1 ] && [ ! -f FAIL_venv_$1 ]; do sleep 30; done; [ -f DONE_venv_$1 ]; }
waitvenv vllm && bash phaseB.sh vllm house > logs/phaseB_vllm.log 2>&1
waitvenv sglang && bash phaseB.sh sglang house > logs/phaseB_sglang.log 2>&1
bash phaseB.sh unsloth > logs/phaseB_unsloth.log 2>&1
touch DONE_all
