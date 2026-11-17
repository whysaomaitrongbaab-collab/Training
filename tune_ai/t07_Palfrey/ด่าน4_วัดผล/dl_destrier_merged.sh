#!/bin/bash
# dl_destrier_merged.sh — (ทางเลือก) โหลด dacarokann/destrier-merged มาวัดเทียบบนการ์ดใบเดียวกัน · ⚠️ UNTESTED (ร่าง 11 พ.ย. 69)
# repo เป็น private (71.9 GB) → ต้อง hf auth login ด้วย token อ่านอย่างเดียวที่เห็น repo นี้ก่อน (Lesson 22)
# ตรวจทุกไฟล์ด้วย sha256 ที่ตรวจแล้ว 8 พ.ย. (proof/06 → gate4/destrier_merged.sha256) — ไม่ตรง = ห้ามใช้วัด
set -u
FT=/workspace/ft; L=$FT/logs; D=/workspace/destrier_merged; PY=/venv/main/bin/python
export HF_HUB_DISABLE_XET=1
[ -f $FT/DONE_destrier_dl ] && { echo "โหลด+ตรวจแล้ว"; exit 0; }
for n in 1 2 3 4 5 6; do
  $PY -c "from huggingface_hub import snapshot_download as s; s('dacarokann/destrier-merged', local_dir='$D', max_workers=8)" \
    >> $L/destrier_dl.log 2>&1 && break
  echo "โหลดสะดุดรอบที่ $n — รอ 20 วิแล้วลองต่อ"; sleep 20
  [ $n = 6 ] && { tail -5 $L/destrier_dl.log; touch $FT/FAIL_destrier_dl; exit 1; }
done
( cd $D && sha256sum -c $FT/gate4/destrier_merged.sha256 ) > $L/destrier_sha.log 2>&1 \
  || { grep -v ': OK$' $L/destrier_sha.log | head; touch $FT/FAIL_destrier_sha; exit 1; }
echo "ตรงกับ proof/06: $(grep -c ': OK$' $L/destrier_sha.log) ไฟล์"
touch $FT/DONE_destrier_dl
