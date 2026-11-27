#!/usr/bin/env python3
"""
tools/pass1_sheet_classify.py — Pass 1 "Sheet classification" ตามแผนภาพ King (ประชุม 18->19 พ.ย. 2569)

แผนภาพ (ซ้ายไปขวา):
  1. Lightweight Title Block crop: หน้าตัวอย่างไม่กี่หน้า -> ลองโซน (แถบขวา / แถบล่าง) -> OCR หา "คำที่ title block ต้องมี"
     -> ให้คะแนนความมั่นใจด้วยกฎ (ไม่เรียกโมเดล; แผนภาพเขียน "AI (or rule base logic)") -> >= 80% พร้อมใช้ -> เขียน Title Block Zone log
  2. Run for full drawing.PDF: ไล่ทุกหน้า แยกทางตามชนิดหน้า
       vector logic = ข้อความฝังใน PDF ก่อน (เร็ว ไม่ OCR)   ·   png logic = render เป็นภาพ แล้ว OCR โซนที่ล็อกไว้
  3. Sheet classified data (.JSON): sheet_name, sheet_code ผูกกับเลขหน้า PDF ("fixed with page") -> ส่งต่อ Pass 2

ใช้ของที่มีอยู่แล้ว ไม่เขียนซ้ำ: titleblock_extract.py (อ่านรหัส/ชื่อ/ธง moved) และ run_part1_part3.py (ชนิดหน้า)
สิ่งที่ไฟล์นี้เพิ่ม: โพรบ+คะแนนโซน, zone log, ลำดับค้นหาที่เริ่มจากโซนที่ล็อก, ธง titleblock_outside_zone, JSON ตามแผนภาพ

คำที่ title block ต้องมี (5 กลุ่ม — ชุดที่ฉันเลือกเอง ไม่ใช่มาตรฐาน):
  code (รหัสแผ่น) · title (ป้ายชื่อแบบ) · scale (มาตราส่วน/1:100) · date (วันที่) · project (โครงการ/เจ้าของ/สถาปนิก/วิศวกร)
คะแนนโซน = จำนวนกลุ่มที่เจอ / 5 ต่อหน้าตัวอย่าง แล้วเอาคะแนนสูงสุดอันดับ 2 ของหน้าตัวอย่าง (ต้องมี 2 หน้าเห็นพ้อง); ล็อกเมื่อ >= READY (0.8 = เลขของ King)
ทิศหน้า (Pass 0, page_orient.py): ทุกหน้าถูกตรวจทิศก่อน; หน้าสแกนตะแคงถูกหมุนให้ตั้งตรงก่อนตัดโซน/OCR (ใช้ทั้งในโพรบและตอนอ่านรหัส/ชื่อ)
ข้อควรรู้: ข้อความไทยฝังใน PDF จาก CAD ส่วนใหญ่เพี้ยน -> โพรบ OCR เสมอ (รวมกับข้อความฝังของโซนเดียวกัน)

    python tools/pass1_sheet_classify.py <บ้าน>                     # เขียน ../logic_test_out/<บ้าน>/pass1_sheet_classified.json
    python tools/pass1_sheet_classify.py <บ้าน> --no-name           # ไม่อ่านชื่อแผ่น (เร็ว: ไม่ OCR ไทยทีละหน้า)
    python tools/pass1_sheet_classify.py <บ้าน> --pages 3-8 --out ผล.json
    python tools/pass1_sheet_classify.py --eval บ้าน1 บ้าน2 ...     # เทียบ sheet_code กับ json เฉลย + ดูคะแนนโซนทำนายได้ไหม
    python tools/pass1_sheet_classify.py --demo                     # self-check กฎคะแนน/เลือกโซน (ไม่ต้องมีไฟล์จริง)
ไม่แตะเฉลย ไม่เรียกโมเดล ไม่เก็บข้อความดิบของกรอบ (มีชื่อ/เลขใบอนุญาตวิศวกร)
"""
import argparse
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_part1_part3 as R          # noqa: E402  ชนิดหน้า (kind_of/page_info)
import titleblock_extract as T       # noqa: E402

READY = 0.8                          # เลขของ King ในแผนภาพ: "80% is ready to send to tag"
SAMPLES = 6                          # หน้าตัวอย่างสูงสุดที่โพรบ (ค่าที่เลือกเอง); หยุดก่อนเมื่อ 2 หน้าถึง READY แล้ว (enough)
ZONES = {"right": T.RIGHT, "bottom": T.BOTTOM}
KEY_GROUPS = ("code", "title", "scale", "date", "project")
_RX = {
    "scale": re.compile(r"มาตรา|SCALE|\d\s*[:;]\s*\d{2,3}"),
    "date": re.compile(r"วันที่|เดือน|DATE|\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}"),
    "project": re.compile(r"โครงการ|PROJECT|เจ้าของ|OWNER|สถาปนิก|ARCHITECT|วิศวกร|ENGINEER"),
}


def evidence(texts):
    """ข้อความ/คำในโซน -> เซตของกลุ่มคำที่เจอ (pure)"""
    hit = set()
    for t in texts:
        k = T._norm_label(t)
        if any(T.is_code(tok) for tok in re.split(r"[\s,;:/()]+", t)):
            hit.add("code")
        if T._start_rest(t) is not None or re.search(r"DRAWING", k):
            hit.add("title")
        hit.update(g for g, rx in _RX.items() if rx.search(k))
    return hit


def coverage(hit):
    return len(hit & set(KEY_GROUPS)) / len(KEY_GROUPS)


def choose_zone(per_sample):
    """per_sample = [{"right": (hit, n_lines), "bottom": (hit, n_lines)}, ...] -> zone log (pure)
    คะแนนโซน = coverage สูงสุดอันดับ 2 ของหน้าตัวอย่าง (ต้องมี 2 หน้าเห็นพ้องกัน; หน้าเดียวอาจเป็นปก/ใบ BOQ ที่บังเอิญมีคำครบ
    และเล่มที่หน้ากลางเล่มเป็น BOQ ไม่ควรทำให้ล็อกพัง — 1ชั้น_06 ใช้มัธยฐานแล้วได้ 0.00 ทั้งที่อ่านรหัสถูก 42 หน้า)
    เท่ากัน -> โซนที่ OCR อ่านได้จำนวนบรรทัดมากกว่า (กรอบล่างเต็มหน้าก็ทับแถบขวาครึ่งล่าง คะแนนจึงเสมอกันได้ — บ้าน 174)"""
    stats = {}
    for z in ZONES:
        covs = [coverage(s[z][0]) for s in per_sample]
        lines = [s[z][1] for s in per_sample]
        second = sorted(covs, reverse=True)[1] if len(covs) > 1 else covs[0]
        stats[z] = dict(confidence=round(second, 3), per_sample=[round(c, 2) for c in covs],
                        mean_lines=round(statistics.mean(lines), 1),
                        groups=sorted(set().union(*(s[z][0] for s in per_sample)) & set(KEY_GROUPS)))
    best = max(stats, key=lambda z: (stats[z]["confidence"], stats[z]["mean_lines"]))
    return dict(zone=best, confidence=stats[best]["confidence"], ready=stats[best]["confidence"] >= READY,
                threshold=READY, per_zone=stats)


def enough(per_sample):
    """หยุดโพรบเมื่อมี 2 หน้าที่โซนใดโซนหนึ่งถึง READY แล้ว (เล่มปกติโพรบแค่ 2 หน้า; เล่มที่กลางเล่มเป็น BOQ ไล่ต่อถึง SAMPLES)"""
    return sum(max(coverage(s[z][0]) for z in ZONES) >= READY for s in per_sample) >= 2


def in_zone(pos, zone):
    """code_pos (สัดส่วนหน้า) อยู่ในสี่เหลี่ยมของโซนที่ล็อกไหม (มุมขวาล่างอยู่ในทั้งสองโซน)"""
    return bool(pos) and pos[0] >= ZONES[zone]["x0"] and pos[1] >= ZONES[zone]["y0"]


def sample_pages(kinds, k=SAMPLES):
    """หน้าตัวอย่างจากช่วงกลางเล่ม (ปก/สารบัญอยู่ต้น ใบ BOQ อยู่ท้าย) เว้นระยะเท่าๆ กัน; ไม่นับหน้าว่าง (pure)"""
    cand = [i for i, kd in enumerate(kinds) if kd != "empty"]
    lo = len(cand) // 4
    mid = cand[lo:max(len(cand) * 3 // 4, lo + 1)] or cand
    return mid[::max(1, len(mid) // k)][:k]


def zone_texts(page, zone, turns=0):
    """โซนของหน้า -> (ข้อความทั้งหมด, จำนวนบรรทัด OCR): OCR ไทยของ crop + คำฝังในโซนเดียวกัน (ไม่เก็บข้อความออกไป)
    turns = ทิศหน้าจาก Pass 0 (หน้าสแกนตะแคง): โซนอ้างอิงหน้าที่ตั้งตรงแล้ว; หน้าที่หมุนไม่ใช้คำฝัง (ตำแหน่งคำฝังเป็นของหน้าที่ตามองเห็น)"""
    import fitz
    spec = ZONES[zone]
    img, _, _ = T._strip_image(page, spec, turns)
    texts = []
    for r in T._reader_th().predict(img):
        texts += list(r.get("rec_texts", []))
    n = len(texts)
    if turns:
        return texts, n
    rm, W, H = page.rotation_matrix, page.rect.width, page.rect.height
    for w in page.get_text("words"):
        r = fitz.Rect(w[:4]) * rm
        if (r.x0 + r.x1) / 2 / W >= spec["x0"] and (r.y0 + r.y1) / 2 / H >= spec["y0"]:
            texts.append(w[4])
    return texts, n


def probe_zone(doc, idx, kinds, tmap=None):
    """ขั้น 1 ของแผนภาพ: โพรบหน้าตัวอย่าง (เลือกจากหน้าที่กำลังจะรัน idx) -> zone log
    tmap = {index หน้า: turns จาก Pass 0}; ไม่ส่ง = ไม่หมุนทุกหน้า"""
    t0, per, pages = time.time(), [], []
    for j in sample_pages(kinds):
        i = idx[j]
        row = {}
        for z in ZONES:
            texts, n = zone_texts(doc[i], z, (tmap or {}).get(i, 0))
            row[z] = (evidence(texts), n)
        per.append(row)
        pages.append(i)
        if enough(per):
            break
    if not per:
        return dict(zone=None, confidence=0.0, ready=False, threshold=READY, per_zone={}, samples=[], seconds=0.0)
    log = choose_zone(per)
    log.update(samples=[i + 1 for i in pages], seconds=round(time.time() - t0, 1), rect=ZONES[log["zone"]])
    return log


def page_turns(page, info, use_ocr):
    """Pass 0: ต้องหมุนหน้ากี่ครั้ง 90° ตามเข็มให้ตั้งตรง (ไม่แน่ใจ = 0 ไม่หมุน) — ตัวเดียวกับที่ run_part1_part3.py ใช้"""
    import page_orient as O
    d = O.decide(page, info["n_words"] >= 30, allow_ocr=use_ocr)
    return d["turns"] or 0, d["how"]


def find_code(page, zone_log, use_ocr, turns=0):
    """ขั้น 2: vector logic = ข้อความฝังก่อน; png logic = OCR เริ่มจากมุมขวาล่าง -> โซนที่ล็อก -> โซนอื่น (ถ้าไม่ล็อกใช้ลำดับเดิม)"""
    res = T.text_layer(page)
    res["pdf_page"] = page.number + 1
    if res["found"] or not use_ocr:
        return res
    z = zone_log.get("zone") if zone_log.get("ready") else None
    order = ["corner"] + ([z] + [o for o in ZONES if o != z] if z else [o for o in ZONES])
    for strip in order:
        best, _ = T.ocr_strip(page, strip, turns)
        if best:
            return dict(found=True, strip=strip, sheet_code=best[2], source="ocr", pdf_page=page.number + 1,
                        code_pos=(round(best[0], 3), round(best[1], 3)))
    return dict(found=False, strip=None, sheet_code=None, source="ocr", reason="no_code_in_strips", pdf_page=page.number + 1)


def classify(house, use_ocr=True, with_name=True, pages=None):
    import fitz
    t0 = time.time()
    doc = fitz.open(T.pdf_of(house))
    idx = list(T.parse_pages(pages, len(doc)))
    infos = [R.page_info(doc[i]) for i in idx]
    kinds = [R.kind_of(**inf) for inf in infos]
    # Pass 0 ก่อน: ทิศของทุกหน้า (หน้าสแกนตะแคงต้องหมุนก่อนตัดโซน/OCR ไม่งั้นอ่านรหัสผิดได้ เช่น A-05 แทน A-04)
    tmap, how = {}, {}
    for i, inf in zip(idx, infos):
        tmap[i], how[i] = page_turns(doc[i], inf, use_ocr)
    zone_log = probe_zone(doc, idx, kinds, tmap) if use_ocr \
        else dict(zone=None, confidence=0.0, ready=False, threshold=READY, per_zone={}, samples=[], note="no_ocr_no_probe")
    recs = []
    for i, inf, kd in zip(idx, infos, kinds):
        res = find_code(doc[i], zone_log, use_ocr, tmap[i])
        if with_name and res["found"]:
            res.update(T.extract_name(doc[i], res.get("strip"), use_ocr, tmap[i]))
        res["turns"], res["orient_how"] = tmap[i], how[i]
        # logic = ทางที่อ่านรหัสได้จริง: vector = ข้อความฝัง, png = OCR ภาพที่ render (หน้าเวกเตอร์ที่ตัวหนังสือเป็นเส้น เช่น 174 จึงเป็น png)
        res.update(kind=kd, logic=("vector" if res.get("source") == "text" else "png") if res["found"]
                   else ("vector" if kd == "vector" else "png"))
        recs.append(res)
    T.flag_moved(recs)
    z = zone_log.get("zone") if zone_log.get("ready") else None
    for r in recs:
        r["in_zone"] = in_zone(r.get("code_pos"), z) if z and r.get("code_pos") else None
        if r["in_zone"] is False and not r.get("flag"):
            r["flag"] = "titleblock_outside_zone"      # เจอรหัสแต่อยู่นอกโซนที่ล็อก: จัดการแยก (แผนภาพ: หน้าที่กรอบย้าย)
    out = [dict(pdf_page=r["pdf_page"], kind=r["kind"], logic=r["logic"], sheet_code=r.get("sheet_code"),
                sheet_name=r.get("sheet_name"), source=r.get("source"), strip=r.get("strip"), code_pos=r.get("code_pos"),
                in_zone=r["in_zone"], flag=r.get("flag"), turns=r["turns"], orient_how=r["orient_how"]) for r in recs]
    found = [r for r in out if r["sheet_code"]]
    codes = Counter(T.norm_code(r["sheet_code"]) for r in found)
    summary = dict(pages=len(out), found=len(found), flagged=sum(bool(r["flag"]) for r in out),
                   turned=sum(bool(r["turns"]) for r in out),
                   kinds=dict(Counter(r["kind"] for r in out)), duplicate_codes=sorted(c for c, n in codes.items() if n > 1))
    doc.close()
    return dict(house=house, zone_log=zone_log, pages=out, summary=summary, ocr=use_ocr, with_name=with_name,
                seconds=round(time.time() - t0, 1))


def evaluate(houses, use_ocr=True):
    """sheet_code ต่อหน้าเทียบ json เฉลย (เหมือน titleblock_extract.evaluate) + คะแนนโซนของแต่ละเล่ม"""
    tot = Counter()
    for h in houses:
        gt = T.load_gt(h)
        r = classify(h, use_ocr=use_ocr, with_name=False)
        c = Counter()
        for p in r["pages"]:
            g = gt.get(p["pdf_page"])
            if g is None:
                c["no_gt"] += 1
            elif not p["sheet_code"]:
                c["missed"] += 1
            elif T.norm_code(p["sheet_code"]) == g:
                c["correct"] += 1
            else:
                c["WRONG"] += 1
        z = r["zone_log"]
        print(f"{h:28s} โซน={z.get('zone')} คะแนน={z.get('confidence'):.2f} {'ล็อก' if z.get('ready') else 'ไม่ล็อก':6s} "
              f"หน้า={len(r['pages']):3d} ถูก={c['correct']:3d} ไม่เจอ={c['missed']:3d} ผิด={c['WRONG']:3d} "
              f"ธง={r['summary']['flagged']:3d} {r['seconds']:6.1f}s", flush=True)
        tot += c
        tot["locked" if z.get("ready") else "unlocked"] += 1
    j = tot["correct"] + tot["missed"] + tot["WRONG"]
    print(f"รวม: ตัดสินได้ {j} หน้า ถูก {tot['correct']} ({tot['correct'] / max(j, 1):.0%}) ไม่เจอ {tot['missed']} ผิด {tot['WRONG']}"
          f" | ล็อกโซน {tot['locked']} เล่ม ไม่ล็อก {tot['unlocked']} เล่ม")


def demo():
    full = ["A-05", "แสดงแบบ", "มาตราส่วน 1:100", "วันที่ 12/03/2565", "โครงการ บ้านพัก"]
    assert evidence(full) == set(KEY_GROUPS), evidence(full)
    assert evidence(["A-05", "1:100"]) == {"code", "scale"}
    assert evidence(["DB16", "RB9", "A3"]) == set()                    # ชื่อเหล็ก/ขนาดกระดาษไม่ใช่รหัสแผ่น
    assert evidence(["DRAWING TITLE", "SCALE NTS", "DATE", "PROJECT"]) == {"title", "scale", "date", "project"}
    assert evidence(["แสดงเบบ"]) == {"title"}                           # ป้าย OCR พลาด 1 ตัวอักษรยังนับ
    assert coverage(set(KEY_GROUPS)) == 1.0 and coverage({"code", "scale"}) == 0.4 and coverage({"x"}) == 0.0
    # เลือกโซน: ขวา 5/5 · ล่าง 2/5 -> ขวา ล็อก; ขวาและล่างเสมอ -> โซนที่ OCR อ่านบรรทัดมากกว่า (กรอบล่างเต็มหน้า)
    five, two = set(KEY_GROUPS), {"code", "date"}
    z = choose_zone([{"right": (five, 20), "bottom": (two, 6)}] * 3)
    assert z["zone"] == "right" and z["ready"] and z["confidence"] == 1.0
    z = choose_zone([{"right": (five, 21), "bottom": (five, 49)}] * 3)
    assert z["zone"] == "bottom" and z["ready"]
    # 3/5 = 0.6 < READY -> ไม่ล็อก (ผลยังออก แต่ใช้ลำดับค้นหาเดิม) ; มัธยฐานกันหน้าตัวอย่างพลาดหน้าเดียว
    z = choose_zone([{"right": ({"code", "title", "scale"}, 10), "bottom": (two, 5)}] * 3)
    assert not z["ready"] and z["confidence"] == 0.6
    bad = {"right": (set(), 3), "bottom": (set(), 3)}
    z = choose_zone([{"right": (five, 9), "bottom": (two, 5)}, {"right": (five, 9), "bottom": (two, 5)}, bad])
    assert z["zone"] == "right" and z["ready"]                          # BOQ 1 หน้าใน 3 ไม่ทำให้ล็อกพัง
    z = choose_zone([{"right": (set(), 9), "bottom": (set(), 5)}, {"right": (five, 9), "bottom": (two, 5)}, bad])
    assert z["confidence"] == 0.0 and not z["ready"]                    # ตัวอย่างเสีย 2 ใน 3 -> ไม่ล็อก
    assert 4 / 5 >= READY and 3 / 5 < READY                              # 4 ใน 5 กลุ่มขึ้นไปถึงล็อก
    # โซน
    assert in_zone((0.93, 0.95), "right") and in_zone((0.93, 0.95), "bottom")      # มุมขวาล่างอยู่ทั้งสองโซน
    assert not in_zone((0.5, 0.2), "right") and not in_zone(None, "right") and not in_zone((0.6, 0.9), "right")
    assert in_zone((0.6, 0.9), "bottom")
    assert not in_zone((0.9, 0.2), "right") and not in_zone((0.9, 0.5), "bottom")        # x ผ่านแต่ y ตก (ต้องดูทั้งสองแกน)
    # หน้าตัวอย่าง: ช่วงกลางเล่ม ไม่นับหน้าว่าง
    assert sample_pages(["vector"] * 29, 3) == [7, 11, 15] and sample_pages(["vector"] * 29) == [7, 9, 11, 13, 15, 17]
    # คะแนน = อันดับ 2: หน้าเดียวที่ครบไม่พอ (ปก/BOQ บังเอิญมีคำครบ); 2 หน้าเห็นพ้อง แม้หน้าอื่น (BOQ) ว่าง ก็ล็อก
    only1 = [{"right": (five, 9), "bottom": (two, 5)}] + [bad] * 4
    assert not choose_zone(only1)["ready"] and choose_zone(only1)["confidence"] == 0.0
    two_ok = [{"right": (five, 9), "bottom": (two, 5)}, bad, bad, bad, {"right": (five, 9), "bottom": (two, 5)}]
    assert choose_zone(two_ok)["ready"] and choose_zone(two_ok)["zone"] == "right"
    ok = {"right": (five, 9), "bottom": (two, 5)}
    assert not enough([ok]) and not enough([ok, bad, bad]) and enough([ok, bad, ok]) and enough([ok, ok])
    assert enough([{"right": (two, 9), "bottom": (five, 5)}, {"right": (two, 9), "bottom": (five, 5)}])   # โซนไหนถึงก็นับ
    assert sample_pages(["empty"] * 5) == [] and sample_pages(["vector"]) == [0]
    mixed = ["empty", "vector", "empty", "vector"] * 6
    assert sample_pages(mixed) and all(mixed[i] == "vector" for i in sample_pages(mixed))
    print("OK — self-check ผ่าน (กฎคะแนน/เลือกโซน/โซน/หน้าตัวอย่าง เท่านั้น ไม่ได้เทียบกับ PDF จริง ใช้ --eval)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("house", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--no-name", action="store_true", help="ไม่อ่านชื่อแผ่น (OCR ไทย ~5-9 วิ/หน้า)")
    ap.add_argument("--no-ocr", action="store_true", help="ข้อความฝังอย่างเดียว (ไม่มีโพรบโซน)")
    ap.add_argument("--pages")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not a.house:
        return ap.print_help()
    if a.eval:
        return evaluate(a.house, use_ocr=not a.no_ocr)
    for h in a.house:
        r = classify(h, use_ocr=not a.no_ocr, with_name=not a.no_name, pages=a.pages)
        out = Path(a.out) if a.out else R.DEFAULT_OUT / h / "pass1_sheet_classified.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        z = r["zone_log"]
        print(f"{h}: โซน={z.get('zone')} คะแนน={z.get('confidence')} {'ล็อก' if z.get('ready') else 'ไม่ล็อก'} "
              f"เจอรหัส {r['summary']['found']}/{r['summary']['pages']} ธง {r['summary']['flagged']} "
              f"{r['seconds']}s -> {out}")


if __name__ == "__main__":
    main()
