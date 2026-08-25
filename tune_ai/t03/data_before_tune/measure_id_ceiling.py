#!/usr/bin/env python3
"""measure_id_ceiling.py — วัด "เพดาน" ของ id-recall แต่ละ subtask

มะขามถาม 2026-08-25: "section ได้ 0 เลย ทำไงดี ใช้ pattern recognition ได้ไหม"
ไล่ดูก่อนแล้วพบว่า **ส่วนหนึ่งของเลข 0% ไม่ได้แปลว่าโมเดลอ่านไม่ออก แต่แปลว่าโจทย์วัดสิ่งที่เป็นไปไม่ได้**

`infer_house_t03.py` วัด id-recall ด้วย `set(gt_ids) & set(pred_ids)` = **เทียบสตริงตรงเป๊ะ**
แต่ element_id ใน GT มี 2 พันธุ์ปนกัน:
  (ก) ชื่อที่ **พิมพ์อยู่บนแบบจริง** — `B1` `C1` `F1A` `RB1'` → โมเดลอ่านออกได้
  (ข) ชื่อที่ **คนจดตั้งขึ้นเอง** เพื่อแยกรายละเอียดย่อย — `gate_front` `SP_at_bathroom`
      `purlin_rafter_connection` `door_lock_detail` → **ไม่มีตัวหนังสือแบบนี้อยู่บนกระดาษเลย**
      ไม่มีทางที่โมเดล (หรือคน) จะเดาถูกจากการดูรูป

สคริปต์นี้แยกสองพันธุ์ด้วย regex แล้วรายงานสัดส่วน = เพดานสูงสุดที่โมเดลทำได้แม้อ่านถูกหมด

**อ่านอย่างเดียว ไม่แก้ไฟล์ใดๆ ไม่ใช้ GPU**

    python measure_id_ceiling.py                      # อ่าน train+val+test
    python measure_id_ceiling.py --splits test        # เฉพาะชุดที่ใช้วัดผล
    python measure_id_ceiling.py --show section       # ดูตัวอย่าง id ที่ถูกจัดว่า "คนตั้งเอง"

# ponytail: PRINTED_ID เป็น heuristic ไม่ใช่ความจริงสัมบูรณ์ — ปรับ regex ได้ถ้าเจอ
# convention ใหม่ ตัวเลขที่ได้จึงเป็น "ประมาณการเพดาน" ไม่ใช่ค่าที่พิสูจน์แล้ว
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent

# ชื่อที่พิมพ์บนแบบมักสั้น: ตัวอักษรนำ 1-4 ตัว + เลข 0-3 หลัก + ท้าย A/X/' ได้
# เช่น B1 · B3X · C1 · F1A · RB1' · CN · S1 · ค1
PRINTED_ID = re.compile(r"^[A-Za-zก-๙]{1,4}[0-9]{0,3}[A-Za-z']{0,3}$")

# ตัวเลขผลจริงของ t03 บนบ้าน 08 (comparison_data.json) — เอาไว้วางข้างเพดานให้เห็นช่องว่าง
T03_ACTUAL = {"plan_beam": "0%", "plan_footing": "33.3%", "plan_slab": "20%",
              "section": "0%", "schedule": "21.9%"}


def gt_of(row):
    a = row["messages"][1]["content"]
    txt = "".join(x.get("text", "") for x in a) if isinstance(a, list) else a
    return json.loads(txt)


def scan(splits):
    """คืน {subtask: (total_ids, printed_ids, [ตัวอย่างที่คนตั้งเอง])}"""
    agg = defaultdict(lambda: [0, 0, []])
    for split in splits:
        p = HERE / f"{split}.jsonl"
        if not p.exists():
            print(f"⚠️  ไม่มี {split}.jsonl ข้ามไป")
            continue
        for line in p.open(encoding="utf-8"):
            if not line.strip():
                continue
            row = json.loads(line)
            sub = row.get("subtask", "?")
            try:
                gt = gt_of(row)
            except Exception:
                continue
            for e in gt.get("elements", []) or []:
                eid = e.get("element_id")
                if not isinstance(eid, str) or not eid:
                    continue
                agg[sub][0] += 1
                if PRINTED_ID.match(eid):
                    agg[sub][1] += 1
                elif len(agg[sub][2]) < 40:
                    agg[sub][2].append(eid)
    return agg


def report(agg, show=None):
    print("\nเพดาน id-recall = สัดส่วน element_id ที่ 'พิมพ์อยู่บนแบบจริง'")
    print("(id ที่คนจดตั้งชื่อเอง โมเดลไม่มีทางเดาถูก จึงกินโควตาตัวหารฟรีๆ)\n")
    print(f"{'subtask':<16}{'id ทั้งหมด':>11}{'อ่านได้จากแบบ':>15}{'เพดาน':>9}   {'t03 ทำได้จริง'}")
    print("-" * 70)
    for sub, (tot, ok, _) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
        if not tot:
            continue
        print(f"{sub:<16}{tot:>11}{ok:>15}{ok/tot*100:>8.0f}%   {T03_ACTUAL.get(sub, '-')}")

    print("\nอ่านตารางนี้ยังไง:")
    print("  เพดานสูง + ผลจริงต่ำ  → โมเดลอ่านไม่ออกจริง (แก้ที่โมเดล/prompt/pattern recognition)")
    print("  เพดานต่ำ              → ตัววัดเองมีปัญหา (แก้ที่ convention การตั้ง element_id)")

    if show:
        _, _, ex = agg.get(show, (0, 0, []))
        print(f"\nตัวอย่าง element_id ของ '{show}' ที่ถูกจัดว่าคนตั้งเอง ({len(ex)} ตัวแรก):")
        for i in range(0, len(ex), 3):
            print("   " + "  ·  ".join(ex[i:i+3]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    ap.add_argument("--show", help="พิมพ์ตัวอย่าง id ที่คนตั้งเองของ subtask นี้")
    a = ap.parse_args()
    report(scan(a.splits), a.show)
