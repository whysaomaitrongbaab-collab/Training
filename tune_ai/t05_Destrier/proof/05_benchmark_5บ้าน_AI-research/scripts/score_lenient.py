#!/usr/bin/env python3
"""เกณฑ์ผ่อน 'แบบ 3 ต.ค.' (score_house.py ของ proof/04) บนบ้านทดสอบ 5 หลัง
นับเฉพาะ: ต่อหน้า · มาร์คที่ต่างกัน (distinct) · ไม่ดูชนิด/ตำแหน่ง/จำนวน · เฉพาะหน้าโครงสร้าง (ฐานราก/แปลนคาน/โครงหลังคา/รูปตัด)
recall = มาร์คเฉลยที่โมเดลพิมพ์มาในหน้าเดียวกัน ÷ มาร์คเฉลยทั้งหมด · precision = มาร์คที่โมเดลพิมพ์ที่ตรงเฉลย ÷ มาร์คที่โมเดลพิมพ์"""
import glob, json, os, re
from collections import defaultdict
B = r"D:\Temp\claude\3049db1b73f5b7d5\c641593e-2919-41af-bebc-66157c3c1ea4\scratchpad\bench5"
GT = r"D:\00mk\steel project\training\Training\json_แก้ไขแล้ว"
H = {"TEST-01": "08บ้าน_เล็ก_1ชั้น_03", "TEST-02": "11บ้าน_เล็ก_1ชั้น_06", "TEST-03": "03บ้าน_เล็ก_2ชั้น_01",
     "TEST-04": "27บ้าน_เล็ก_2ชั้น_06", "TEST-05": "34บ้าน_ใหญ่_1ชั้น_02"}
PAT = {"footing_plan", "beam_plan", "roof_frame_plan", "section"}

def norm(m):
    return re.sub(r"\s+", "", str(m)).upper() if m else None

def main():
    tot = [0, 0, 0]
    print(f"{'บ้าน':<8}{'หน้าโครงสร้าง':>14}{'มาร์คเฉลย':>10}{'โมเดลพิมพ์':>11}{'ตรง':>5}{'recall%':>9}{'precision%':>12}")
    for tid, folder in H.items():
        rp = os.path.join(B, "out", tid, "vllm", "result.json")
        if not os.path.exists(rp): print(tid, "— ยังไม่มีผล"); continue
        g = defaultdict(set)
        for f in glob.glob(os.path.join(GT, folder, "*.json")):
            m = re.search(r"_หน้า(\d+)", os.path.basename(f))
            try: d = json.load(open(f, encoding="utf-8"))
            except Exception: continue
            if not (m and isinstance(d, dict) and d.get("pattern") in PAT): continue
            for e in d.get("elements") or []:
                if isinstance(e, dict) and norm(e.get("element_id")): g[int(m.group(1))].add(norm(e["element_id"]))
        res = json.load(open(rp, encoding="utf-8")); p = defaultdict(set)
        for f in res["files"]:
            m = re.match(r"page_(\d+)_", f["name"])
            if not m or f["name"].endswith((".raw.json", ".txt")) or not isinstance(f.get("json"), dict): continue
            for e in f["json"].get("elements") or []:
                if isinstance(e, dict) and norm(e.get("element_id")): p[int(m.group(1))].add(norm(e["element_id"]))
        pages = sorted(g)
        want = sum(len(g[x]) for x in pages); got = sum(len(p[x]) for x in pages); hit = sum(len(g[x] & p[x]) for x in pages)
        tot[0] += hit; tot[1] += want; tot[2] += got
        print(f"{tid:<8}{len(pages):>14}{want:>10}{got:>11}{hit:>5}{hit/want*100 if want else 0:>9.1f}{hit/got*100 if got else 0:>12.1f}")
    if tot[1]: print(f"{'รวม':<8}{'':>14}{tot[1]:>10}{tot[2]:>11}{tot[0]:>5}{tot[0]/tot[1]*100:>9.1f}{tot[0]/tot[2]*100 if tot[2] else 0:>12.1f}")

if __name__ == "__main__": main()
