#!/usr/bin/env python3
"""cv_scan_footing_survey.py — รัน cv_scan (pass 1.5 CV) กับหน้า footing_plan ของทุกบ้านใน
json_แก้ไขแล้ว/ (ไม่ต้องผ่าน organize.py ก่อน — cv_scan.scan_image() ใช้ได้กับภาพดิบตรงๆ)

จุดประสงค์: เช็คว่า "CV หาจุดในหน้าฐานรากไม่เจอเลย (0 จุด)" ที่เจอกับบ้านครอบครัวไทยเป็นสุข๒
หน้า 12 เป็นเคสเดียวหรือเกิดบ่อย — เอาไปตอบคำถาม "เชื่อ pipeline นี้ได้แค่ไหน"

    python cv_scan_footing_survey.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent
GT_ROOT = TRAINING / "json_แก้ไขแล้ว"
IMG_ROOT = TRAINING / "image"

sys.path.insert(0, str(HERE))
from cv_scan import scan_image, load_templates  # noqa: E402


def find_image(house_dir, d, fname):
    src = d.get("source_image")
    cands = []
    if isinstance(src, str):
        cands.append(TRAINING / src)
        cands.append(IMG_ROOT / Path(src).name)
    m = re.match(r"(.+?_หน้า\d+)", Path(fname).stem)
    if m:
        img_house = house_dir[2:] if house_dir[:2].isdigit() else house_dir
        cands.append(IMG_ROOT / img_house / f"{m.group(1)}.png")
    for c in cands:
        if c.exists():
            return c
    return None


def main():
    tpls = load_templates()
    houses = sorted(p.name for p in GT_ROOT.iterdir() if p.is_dir())
    rows = []
    for house in houses:
        for fp in sorted((GT_ROOT / house).glob("*.json")):
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            if d.get("pattern") != "footing_plan":
                continue
            img = find_image(house, d, fp.name)
            if not img:
                rows.append((house, fp.name, None, None))
                continue
            scan, _ = scan_image(img, tpls)
            c = scan["counts"]
            rows.append((house, fp.name, c, scan["hint"]))

    print(f"หน้า footing_plan ทั้งหมดที่เจอ: {len(rows)} หน้า จาก {len(houses)} บ้าน\n")

    no_image = [r for r in rows if r[2] is None]
    zero_both = [r for r in rows if r[2] and r[2]["footing"] == 0 and r[2]["column"] == 0]
    has_something = [r for r in rows if r[2] and (r[2]["footing"] > 0 or r[2]["column"] > 0)]

    print(f"หาไฟล์ภาพไม่เจอ: {len(no_image)} หน้า")
    print(f"CV หาไม่เจอเลยสักจุด (footing=0, column=0): {len(zero_both)} หน้า "
          f"({100 * len(zero_both) / max(1, len(rows) - len(no_image)):.0f}% ของหน้าที่สแกนได้)")
    print(f"CV หาเจออย่างน้อย 1 จุด: {len(has_something)} หน้า\n")

    if zero_both:
        print("หน้าที่ CV หาไม่เจอเลย:")
        for house, fname, c, hint in zero_both:
            print(f"  · {house}/{fname}")

    if has_something:
        totals = [r[2]["footing"] + r[2]["column"] for r in has_something]
        totals.sort()
        mid = totals[len(totals) // 2]
        print(f"\nในหน้าที่เจอ: จุดเฉลี่ย/หน้า = {sum(totals) / len(totals):.1f}, "
              f"มัธยฐาน = {mid}, ต่ำสุด = {min(totals)}, สูงสุด = {max(totals)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
