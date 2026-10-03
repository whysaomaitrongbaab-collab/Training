#!/bin/bash
# รอคิว SGLang (runall4) จบ → พิสูจน์ทางแก้ production: vLLM จาก venv_prodvllm ด้วยคำสั่งที่ presentation.py สร้าง
# + ยิงซ้ำ 3 รอบ แยก sampling แกว่งออกจากคุณภาพตกจริง
FT=/workspace/ft
until [ -f $FT/DONE_all4 ]; do sleep 30; done
PAGES=1,19 TASKS=22:section,20:plan_beam,19:plan_footing REPEAT=3 bash $FT/phaseB2.sh prodvllm > $FT/logs/phaseB_prodvllm.log 2>&1
touch $FT/DONE_all5
