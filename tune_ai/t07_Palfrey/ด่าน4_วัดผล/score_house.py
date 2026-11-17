"""ให้คะแนนผลอ่านบ้าน 83b8e52c เทียบเฉลย (tests/fixtures/real-house-truth/83b8e52c) ต่อหน้า
มาร์คที่ต่างกัน (distinct) → recall/precision · จำนวนชิ้น (element) เทียบเฉลย
    python score_house.py <ชื่อ>=<result.json หรือ job json> ...
หยาบโดยตั้งใจ: ไม่ดูสเปก/ขนาด/ตำแหน่ง — ใช้ตอบคำถามเดียวว่า "ตัวเสิร์ฟใหม่อ่านได้ระดับเดียวกับเดิมไหม"
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

TRUTH = r"d:/00mk/steel project/งานสมบูรณ์/Constistant/tests/fixtures/real-house-truth/83b8e52c"
PAGES = (19, 20, 21, 22, 23, 24, 25)


def norm(m):
    return re.sub(r"\s+", "", str(m)).upper() if m else None


def mark_of(e):
    return e.get("mark") or e.get("element_id")


def truth():
    marks, counts = defaultdict(set), defaultdict(int)
    for f in glob.glob(os.path.join(TRUTH, "*.json")):
        m = re.search(r"_หน้า(\d+)_", os.path.basename(f))
        pg = int(m.group(1))
        if pg not in PAGES:
            continue
        for e in json.load(open(f, encoding="utf-8")).get("elements") or []:
            if norm(mark_of(e)):
                marks[pg].add(norm(mark_of(e)))
                counts[pg] += 1
    return marks, counts


def model(path):
    d = json.load(open(path, encoding="utf-8"))
    files = (d.get("result") or d)["files"]
    marks, counts, ok, total = defaultdict(set), defaultdict(int), 0, 0
    for f in files:
        m = re.match(r"page_(\d+)_(\w+?)(\.raw)?\.(json|txt)$", f["name"])
        if not m:
            continue
        total += 1
        if m.group(3):
            continue
        ok += 1
        pg = int(m.group(1))
        if pg not in PAGES:
            continue
        for e in f["json"].get("elements") or []:
            if isinstance(e, dict) and norm(mark_of(e)):
                marks[pg].add(norm(mark_of(e)))
                counts[pg] += 1
    return marks, counts, ok, total


def main():
    tm, tc = truth()
    rows = []
    for arg in sys.argv[1:]:
        name, path = arg.split("=", 1)
        mm, mc, ok, total = model(path)
        hit = sum(len(tm[p] & mm[p]) for p in PAGES)
        want = sum(len(tm[p]) for p in PAGES)
        got = sum(len(mm[p]) for p in PAGES)
        rows.append((name, ok, total, hit, want, got, mm, mc))
    print(f"{'ชุด':<16} {'JSON ผ่าน':>10} {'มาร์คเจอ/เฉลย':>14} {'recall':>7} {'precision':>9}  ชิ้นต่อหน้า (เฉลย " +
          " ".join(f"{p}:{tc[p]}" for p in PAGES) + ")")
    for name, ok, total, hit, want, got, mm, mc in rows:
        print(f"{name:<16} {ok:>4}/{total:<5} {hit:>6}/{want:<7} {hit / want:7.2f} {hit / got if got else 0:9.2f}  "
              + " ".join(f"{p}:{mc[p]}" for p in PAGES))
    print("\nมาร์คต่อหน้า (✓ = ตรงเฉลย · ✗ = ขาด · + = เกินมา)")
    for p in PAGES:
        print(f"  หน้า {p} เฉลย {sorted(tm[p])}")
        for name, *_, mm, mc in rows:
            print(f"     {name:<14} ✓{len(tm[p] & mm[p])} ✗{sorted(tm[p] - mm[p])} +{sorted(mm[p] - tm[p])}")


if __name__ == "__main__":
    main()
