#!/usr/bin/env python3
"""harvest_templates.py — สร้าง stock ภาพ element (template bank) จากบ้านที่มีเฉลยอยู่แล้ว

มะขามสั่ง 2026-08-25: "stock ยังไม่มี ณ ตอนนี้ — เริ่มลงมือทำเลย" (แผน pass 0.5 / 1.5)
หลักการ: ชื่อไฟล์ GT ใน json_แก้ไขแล้ว/ บอกอยู่แล้วว่าบ้านไหนหน้าไหนคือผังฐานราก/ผังคาน
→ ไม่ต้องรอ pass0 เอาหน้าเหล่านั้นมาให้ template bank ปัจจุบันลองจับ แล้ว:

  - บ้านที่ bank จับได้ดี   → ไม่ต้องทำอะไร (สัญลักษณ์ซ้ำกับที่มีใน stock แล้ว)
  - บ้านที่ bank จับได้น้อย → คือบ้านที่วาดสัญลักษณ์คนละแบบ = ของใหม่ที่ stock ต้องการ
    ใช้ contour หา "ไอคอนซ้ำๆ ขนาดเท่ากัน" บนหน้านั้น crop ลง staging/ ให้คนดูก่อน
    ⚠️ ชื่อไฟล์ `cand_fromFootingPage__` = "เก็บมาจากหน้าผังฐานราก" ไม่ใช่ "นี่คือฐานราก"
       ตัวหาไม่รู้จักฐานราก มันหาแค่ไอคอนที่ซ้ำหลายจุด → วงกลมกริด A/B/C ก็ติดมาด้วยเป็นปกติ
    **ไม่ auto-promote เข้า bank เด็ดขาด** — ต้องผ่านตาก่อนเสมอ (บทเรียน F1/F2 วันนี้:
    รูปทรงที่เดาว่าเหมือน อาจเป็นคนละของ)

    python tools/harvest_templates.py                # สแกนทุกบ้าน สรุป coverage + เติม staging
    python tools/harvest_templates.py --houses 06 07 # เฉพาะบางบ้าน
    python tools/harvest_templates.py --promote a b  # ย้ายไฟล์จาก staging เข้า bank จริง
    python tools/harvest_templates.py --kind column  # เก็บ candidate เสา (จากหน้าผังคาน —
                                                     #  เสาอยู่ที่จุดตัดคาน ไม่มีหน้าผังเสาแยก)
    python tools/harvest_templates.py --promote a --kind column   # เข้า bank เป็น tpl_column*.png
    python tools/harvest_templates.py --measure-beam-gap          # วัดระยะเส้นคู่คานจริงต่อบ้าน
                                                     #  (คานไม่ใช้ template จากคลัง — ใช้เส้นคู่
                                                     #   สังเคราะห์จาก BEAM_GAP ดู pattern_recognition.py)

อ่าน image/ อย่างเดียว ไม่แตะ GT · ผลเขียนลง tools/templates/staging/ กับ harvest_report.txt
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from pattern_recognition import (imread_thai, imwrite_thai, load_templates,  # noqa: E402
                                 match_bank, FOOTING_THRESH)

TRAINING = HERE.parent
GT_ROOT = TRAINING / "json_แก้ไขแล้ว"
IMG_ROOT = TRAINING / "image"
STAGING = HERE / "templates" / "staging"
# [แก้ 2026-08-25 รอบสอง] เดิม 0.55 "จับหลวมๆ พอเห็นเค้า" — ใช้ได้ตอน bank 3 ตัว แต่พอ bank
# 11 ตัว ขยะท่วม (บ้าน 27: GT 20 จับ 293) แล้วเกณฑ์ "≥70% ของ GT" ผ่านหมดแบบไร้ความหมาย
# → ใช้เกณฑ์เดียวกับตอนใช้จริง และวัดสองด้าน (ขาดก็แย่ เกินก็แย่)
HARVEST_THRESH = FOOTING_THRESH


def house_pages():
    """{'06บ้าน_ใหญ่_1ชั้น_01': {'footing': ('หมายเลขหน้า', gt_count), 'beam': (...),
    'column': (...)}} จากชื่อ+เนื้อไฟล์ GT

    'column' ไม่มีหน้าของตัวเอง — เสาถูกวาดเป็นกล่องที่จุดตัดคานบนผังคาน (ที่มาของ
    tpl_column.png ตัวแรก: บ้าน 17 หน้า16 ซึ่งเป็นผังคาน) จึงนับ element ชนิดเสาจาก
    หน้าผังคาน/ผังฐานรากหน้าเดียวกันนั้น หน้าไหนนับได้มากสุดเป็นตัวแทนของบ้าน"""
    out = defaultdict(dict)
    col_best = {}
    for f in sorted(GT_ROOT.glob("*/*.json")):
        m = re.search(r"หน้า(\d+)", f.name)
        if not m:
            continue
        lb = f.name.lower()
        kind = None
        if "plan" in lb and "footing" in lb:
            kind = "footing"
        elif "plan_beam" in lb or ("beam" in lb and "plan" in lb):
            kind = "beam"
        if not kind:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        els = d.get("elements") or []
        for v in d.get("views") or []:
            if isinstance(v, dict):
                els += v.get("elements") or []

        def count(pred):
            n = 0
            for e in els:
                if isinstance(e, dict) and pred(e.get("element_type") or ""):
                    c = e.get("count")
                    if not isinstance(c, (int, float)) or not c:
                        c = len(e.get("grid_refs") or []) or 1
                    n += c
            return int(n)

        house = f.parent.name
        if kind not in out[house]:
            out[house][kind] = (m.group(1), count(
                (lambda t: t in ("footing", "pile", "pile_cap")) if kind == "footing"
                else (lambda t: "beam" in t)))
        # เสา: ดูทุกหน้า plan เอาหน้าที่มีเสามากสุด
        nc = count(lambda t: t in ("column", "pedestal"))
        if nc > col_best.get(house, (None, -1))[1]:
            col_best[house] = (m.group(1), nc)
    for house, (page, n) in col_best.items():
        if n > 0:
            out[house]["column"] = (page, n)
    return out


def image_of(house_dir, page):
    base = re.sub(r"^\d+", "", house_dir)          # '06บ้าน_...' → 'บ้าน_...'
    p = IMG_ROOT / base / f"{base}_หน้า{page}.png"
    return p if p.exists() else None


def repeated_icon_candidates(gray, min_rep=3):
    """หาไอคอนที่ซ้ำกันหลายจุดบนหน้า — สำหรับบ้านที่ bank ปัจจุบันจับไม่ได้
    วิธี: contour ทุกระดับ → กรองก้อนเกือบจัตุรัสขนาดไอคอน → จัดกลุ่มตามขนาด
    → เอากลุ่มที่ซ้ำ ≥ min_rep (สัญลักษณ์ element ซ้ำตามจำนวนตัวจริง ต่างจาก
    ตัวหนังสือ/กรอบที่ขนาดสะเปะสะปะ)"""
    _, bw = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    H, W = gray.shape
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if not (14 < w < 120 and 14 < h < 120):
            continue
        if not (0.6 < w / h < 1.7):
            continue
        if x > W * 0.8:                            # ตัด title block
            continue
        boxes.append((x, y, w, h))
    groups = defaultdict(list)
    for b in boxes:
        groups[(b[2] // 8, b[3] // 8)].append(b)   # bucket ขนาดหยาบ 8px
    cands = []
    for _, bs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(bs) < min_rep:
            continue
        # ตัดกล่องซ้อนกันเอง (ไอคอนซ้อน = contour ชั้นนอก/ในของตัวเดียวกัน)
        keep = []
        for x, y, w, h in bs:
            cx, cy = x + w // 2, y + h // 2
            if all(abs(cx - (kx + kw // 2)) > kw or abs(cy - (ky + kh // 2)) > kh
                   for kx, ky, kw, kh in keep):
                keep.append((x, y, w, h))
        if len(keep) >= min_rep:
            cands.append(keep)
        if len(cands) >= 3:                        # เอาแค่ 3 กลุ่มแรกพอ กันขยะท่วม staging
            break
    return cands


def harvest(houses_filter=None, kind="footing"):
    from pattern_recognition import COLUMN_THRESH
    tpls = load_templates()
    bank_f = tpls.get(kind, [])
    if not isinstance(bank_f, list):
        bank_f = [bank_f]
    # เกณฑ์/สเกลเดียวกับตอนใช้จริงใน analyze() — วัดคนละเกณฑ์กับ production = ตัวเลขโกหก
    thresh = HARVEST_THRESH if kind == "footing" else COLUMN_THRESH
    scales = None if kind == "footing" else (1.0,)
    STAGING.mkdir(parents=True, exist_ok=True)
    tag = kind.capitalize()
    rows = []
    for house, kinds in sorted(house_pages().items()):
        if houses_filter and not any(house.startswith(hf) for hf in houses_filter):
            continue
        if kind not in kinds:
            continue
        page, gt_n = kinds[kind]
        img_p = image_of(house, page)
        if img_p is None:
            rows.append((house, page, gt_n, None, "ไม่มีไฟล์ภาพ"))
            continue
        g = imread_thai(img_p)
        if scales:
            hits = match_bank(g, bank_f, thresh, scales=scales)
        else:
            hits = match_bank(g, bank_f, thresh)
        note = ""
        # bank เห็นน้อยกว่าเฉลยมาก = สัญลักษณ์แบบใหม่ → เก็บ candidate ลง staging
        if gt_n > 0 and len(hits) < gt_n * 0.7:
            n_saved = 0
            # เสาเป็นไอคอนเล็ก (กล่อง ~30-60px) — จำกัดช่วงขนาดให้แคบกว่า footing
            min_rep = 3
            for gi, grp in enumerate(repeated_icon_candidates(g, min_rep=min_rep)):
                x, y, w, h = grp[0]                # ตัวแทนกลุ่มละ 1 crop พอ
                pad = 6
                crop = g[max(y - pad, 0):y + h + pad, max(x - pad, 0):x + w + pad]
                out = STAGING / f"cand_from{tag}Page__{house}__g{gi}_n{len(grp)}.png"
                imwrite_thai(out, crop)
                n_saved += 1
            note = f"→ staging {n_saved} กลุ่ม" if n_saved else "→ contour ก็ไม่เจอ (ดูเองทั้งหน้า)"
        rows.append((house, page, gt_n, len(hits), note))

    lines = [f"{'บ้าน':<28}{'หน้า':>5}{'GT':>5}{'bank จับได้':>12}   หมายเหตุ"]
    lines.append("-" * 78)
    ok = short = over = 0
    for house, page, gt_n, nh, note in rows:
        if nh is None:
            lines.append(f"{house:<28}{page:>5}{gt_n:>5}{'-':>12}   {note}")
            continue
        # สองด้าน: ต่ำกว่า 70% = template ขาด / เกิน 160% = ขยะท่วม (เผื่อ inset บนหน้า)
        # บทเรียนรอบแรก: เช็คด้านเดียว "≥70%" พอ bank ใหญ่ ขยะดันตัวเลขผ่านหมดแบบไร้ความหมาย
        if gt_n > 0 and nh > gt_n * 1.6:
            over += 1
            mark = "🔺 เกิน (FP)"
        elif gt_n > 0 and nh >= gt_n * 0.7:
            ok += 1
            mark = "✅"
        else:
            short += 1
            mark = "🔶"
        lines.append(f"{house:<28}{page:>5}{gt_n:>5}{nh:>12}   {mark} {note}")
    lines.append(f"\nพอดี {ok} | ขาด (template ไม่ครบ) {short} | เกิน (ขยะ) {over}"
                 f" | bank {len(bank_f)} template ({kind}) @thresh {thresh}")
    report = "\n".join(lines)
    (HERE / f"harvest_report_{kind}.txt").write_text(report, encoding="utf-8")
    print(report)


def review(kind="footing"):
    """จัดอันดับ candidate ในกอง staging แล้วทำ montage ให้คนดูเรียงตามความน่าจะเป็นของจริง

    สัญญาณจัดอันดับ = |จำนวนซ้ำ − เฉลยของบ้านนั้น| (มีข้อมูลอยู่แล้ว ไม่ต้องหาใหม่)
    พิสูจน์จากรอบแรก: ตัวที่ promote แล้วรอด n17/เฉลย17 · n17/เฉลย17 (ตรงเป๊ะ)
    ตัวที่ต้องถอดทีหลัง n31/เฉลย9 · n88/เฉลย11 (ห่างลิบ = เป็นตัวหนังสือ/กริด)
    **ยังต้องใช้ตาคัดอยู่ดี** — นี่แค่เรียงให้ของน่าจะใช่ขึ้นก่อน ไม่ใช่ตัดสินแทน
    """
    gt = {h: v[kind][1] for h, v in house_pages().items() if kind in v}
    tag = kind.capitalize()
    cands = []
    for f in sorted(STAGING.glob(f"cand_from{tag}Page__*.png")):
        m = re.match(rf"cand_from{tag}Page__(.+?)__g\d+_n(\d+)\.png", f.name)
        if not m:
            continue
        house, n = m.group(1), int(m.group(2))
        g = gt.get(house)
        if not g:
            continue
        cands.append((abs(n - g) / g, f, house, n, g))
    cands.sort(key=lambda c: c[0])

    CELL, LBL, cols = 170, 30, 6
    rows_n = (len(cands) + cols - 1) // cols
    canvas = np.full((rows_n * (CELL + LBL), cols * CELL), 255, np.uint8)
    for i, (err, f, house, n, g) in enumerate(cands):
        im = imread_thai(f)
        s = min((CELL - 12) / im.shape[1], (CELL - 12) / im.shape[0], 3.0)
        im2 = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
        r, c = divmod(i, cols)
        y0, x0 = r * (CELL + LBL), c * CELL
        canvas[y0 + 6:y0 + 6 + im2.shape[0], x0 + 6:x0 + 6 + im2.shape[1]] = im2
        hno = re.match(r"(\d+)", house).group(1)
        cv2.putText(canvas, f"{hno} n{n}/gt{g}", (x0 + 4, y0 + CELL + LBL - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1, cv2.LINE_AA)
    out = HERE / "pattern_out" / f"review_ranked_{kind}.png"
    out.parent.mkdir(exist_ok=True)
    imwrite_thai(out, cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR))
    print(f"เรียงแล้ว {len(cands)} candidate → {out}")
    print("  (ซ้าย-บน = จำนวนซ้ำใกล้เฉลยที่สุด = น่าจะใช่ที่สุด)\n")
    for err, f, house, n, g in cands[:20]:
        print(f"  ต่าง {err*100:>4.0f}%  n{n:<4}/gt{g:<3}  {f.name}")
    return cands


def promote(names, kind="footing"):
    for n in names:
        src = STAGING / n if (STAGING / n).exists() else next(STAGING.glob(f"*{n}*"), None)
        if not src:
            print(f"ไม่เจอ {n} ใน staging")
            continue
        seq = len(list((HERE / "templates").glob(f"tpl_{kind}*.png"))) + 1
        dst = HERE / "templates" / f"tpl_{kind}{seq}.png"
        shutil.move(str(src), str(dst))
        print(f"✅ {src.name} → {dst.name}")


def measure_beam_gaps(houses_filter=None):
    """วัดระยะเส้นคู่ขนานของคาน (px) จริงต่อบ้าน จากหน้าผังคานที่ GT ชี้

    คานบนผังคือเส้นดำยาวขนาน 2 เส้น — BEAM_GAP ปัจจุบัน (21px) วัดจากบ้าน 17 บ้านเดียว
    บ้านที่สแกนคนละ DPI/มาตราส่วนระยะนี้ต่างออกไป เครื่องเลยมองไม่เห็นคานทั้งหน้า
    วิธีวัด: สกัดเส้นนอนยาวด้วย morphology → เก็บ y-กึ่งกลางของแต่ละเส้น → คู่เส้นที่
    ทับช่วง x กันและห่างกัน 8-45px คือคู่หน้าคาน → histogram แล้วรายงานค่า mode ต่อบ้าน"""
    rows = []
    for house, kinds in sorted(house_pages().items()):
        if houses_filter and not any(house.startswith(hf) for hf in houses_filter):
            continue
        if "beam" not in kinds:
            continue
        page, gt_n = kinds["beam"]
        img_p = image_of(house, page)
        if img_p is None:
            continue
        g = imread_thai(img_p)
        _, bw = cv2.threshold(g, 128, 255, cv2.THRESH_BINARY_INV)
        # เส้นนอนยาว: เปิดด้วย kernel นอนยาว 80px — ตัวหนังสือ/ไอคอนสั้นกว่านั้นหายหมด
        horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((1, 80), np.uint8))
        cnts, _ = cv2.findContours(horiz, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        segs = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w >= 100 and h <= 8:
                segs.append((x, x + w, y + h // 2))
        gaps = Counter()
        segs.sort(key=lambda s: s[2])
        for i, (x0, x1, y) in enumerate(segs):
            for x0b, x1b, yb in segs[i + 1:]:
                d = yb - y
                if d > 45:
                    break
                if d >= 8 and min(x1, x1b) - max(x0, x0b) > 80:
                    gaps[d] += 1
        top = gaps.most_common(3)
        rows.append((house, page, gt_n, len(segs), top))
    print(f"{'บ้าน':<28}{'หน้า':>5}{'GT คาน':>7}{'เส้นยาว':>8}   gap ที่พบบ่อย (px: ครั้ง)")
    print("-" * 84)
    all_modes = Counter()
    for house, page, gt_n, nseg, top in rows:
        t = " ".join(f"{d}px:{c}" for d, c in top) or "-"
        print(f"{house:<28}{page:>5}{gt_n:>7}{nseg:>8}   {t}")
        if top:
            all_modes[top[0][0]] += 1
    print("\nmode ต่อบ้าน รวมทั้งคลัง:", dict(sorted(all_modes.items())))
    print("→ เอาค่าที่ครอบคลุมบ้านมากสุดไปใส่ BEAM_GAPS ใน pattern_recognition.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--houses", nargs="*", help="กรองเฉพาะบ้านที่ขึ้นต้นด้วยเลขพวกนี้")
    ap.add_argument("--promote", nargs="*", help="ชื่อไฟล์ใน staging ที่ผ่านตาแล้ว ย้ายเข้า bank")
    ap.add_argument("--review", action="store_true", help="จัดอันดับ candidate + ทำ montage ให้คนดู")
    ap.add_argument("--kind", default="footing", choices=("footing", "column"),
                    help="ชนิด template ที่เก็บ/รีวิว/promote (คานไม่ใช้คลัง — ดู --measure-beam-gap)")
    ap.add_argument("--measure-beam-gap", action="store_true",
                    help="วัดระยะเส้นคู่คานจริงต่อบ้าน สำหรับตั้ง BEAM_GAPS")
    a = ap.parse_args()
    if a.measure_beam_gap:
        measure_beam_gaps(a.houses)
    elif a.review:
        review(a.kind)
    elif a.promote:
        promote(a.promote, a.kind)
    else:
        harvest(a.houses, a.kind)
