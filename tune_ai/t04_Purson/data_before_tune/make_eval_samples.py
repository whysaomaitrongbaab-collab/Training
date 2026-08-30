#!/usr/bin/env python3
"""make_eval_samples.py — สุ่มตัวอย่าง val ของแต่ละ fold ~25-28 ตัวอย่าง กระจายทุกหลัง
(ไม่ใช่แค่ N แถวแรก ที่อาจตกบ้านเดียวถ้า jsonl เรียงตามหลัง) ใช้สำหรับ eval แบบสุ่มเทียบ fold
มะขามเคาะ 2026-08-30: eval สุ่ม 20-30/fold แทนเต็ม 205/fold (ประหยัดเวลา 7-8ชม. -> ~1-1.5ชม./fold)
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
random.seed(42)

for k in range(4):
    rows = [json.loads(l) for l in open(HERE / f"val_fold{k}.jsonl", encoding="utf-8") if l.strip()]
    houses = sorted({r["house"] for r in rows})
    by_house = {h: [r for r in rows if r["house"] == h] for h in houses}
    sample = []
    per_house = max(1, 28 // len(houses))
    for h in houses:
        pool = by_house[h][:]
        random.shuffle(pool)
        sample.extend(pool[:per_house])
    random.shuffle(sample)
    out = HERE / f"val_fold{k}_sample.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in sample:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    sample_houses = sorted({r["house"] for r in sample})
    print(f"fold{k}: สุ่ม {len(sample)}/{len(rows)} ตัวอย่าง จาก {len(sample_houses)}/{len(houses)} หลัง")
