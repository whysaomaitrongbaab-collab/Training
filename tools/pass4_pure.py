#!/usr/bin/env python3
"""
tools/pass4_pure.py — overlay ของ Pass 4 แบบ "code เพียว": ไม่ใช้ไฟล์เฉลยเลย (ไม่มีรายการ element, ไม่มี grid master)

pass4_sp.py ใช้เฉลย 2 อย่าง: element + grid master (ชื่อเส้น/เมตร) — ที่นี่ไม่ใช้ทั้งคู่ ทุกอย่างมาจากหน้า PDF เอง:
  1. เส้นกริดบนหน้า        = gridlab_probe.detect()  (logic + OCR ในวงหัวกริดเมื่อไม่มีข้อความฝัง)
  2. สเกล pt/เมตร          = gridlab_scale.plan_scales() (OCR ตัวเลขระยะ) — ใช้แค่ตั้งขนาดกรอบเสา/ระยะขอบคาน
  3. ลองทุกจุดตัดกริดของแปลน  -> มีรูปปิดขนาดเสา/ฐานราก (pass4_sp.point_hit) = จุดผู้สมัคร (สีม่วงแดง)
  4. ลองทุกช่วงกริดติดกัน    -> มีเส้นทึบขนานแกนครอบคลุม >= 60% (pass4_sp.cover_fraction) = คานผู้สมัคร (สีเขียว)
  5. ชื่อ (ไม่บังคับ)        = ข้อความฝังของหน้าที่รูปแบบเหมือนรหัส (F1, C1, B2(+0.15)) ที่ใกล้ที่สุด — ขึ้นต้นด้วย "~" = "ข้อความใกล้ๆ"
                              ไม่ได้ตรวจว่าถูก (เดา)
ข้อจำกัดที่ต้องรู้ (ไม่ซ่อน):
  - ผู้สมัครไม่ใช่ element: จุดตัดที่ไม่มีเสาก็มีรูปปิดขนาดพอดีเสาอยู่ราว 17% (ตัวควบคุมของ pass4_sp.py) จึงมีของเกินแน่นอน
    ใช้ --vs-gt วัดบนหน้านั้น (อ่านเฉลยเพื่อ "นับคะแนน" เท่านั้น ไม่ได้ใช้สร้างภาพ)
  - ใช้ได้เฉพาะหน้าเวกเตอร์ที่ detect() หาเส้นกริดเจอ · หน้าสแกนจะว่าง
  - ไม่รู้ชนิด (เสา/ฐานราก) ไม่รู้ว่าแปลนนี้เป็นแปลนฐานรากหรือคาน (box_around ของฐานรากแยกท่อน ไม่ใช้ เปิดด้วย --box)
  - จุดตัดที่ไม่ใช่คู่เส้นของแปลนเดียวกัน ไม่ถูกลอง

    python tools/pass4_pure.py <บ้าน> <หน้า> [--no-ocr] [--no-labels] [--show-miss] [--box] [--vs-gt]
    python tools/pass4_pure.py --demo
ผลลง ../logic_test_out/<บ้าน>/pass4_pure_pNN.png + .json
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pass4_sp as P4  # noqa: E402

OUT = P4.OUT
MARK_RE = re.compile(r"^[A-Za-zก-ฮ]{1,3}\d{1,2}[A-Za-z]?(\([+\-]?\d*\.?\d+\))?$")
BEAM_MARK_RE = re.compile(r"^(GB|RB|TB|B|ค|ก)\d")
POINT_LABEL_M = 0.8        # ข้อความที่นับว่า "ใกล้จุด" ภายในกี่เมตร (ค่าที่เลือกเอง)
BEAM_LABEL_M = 0.6         # ข้อความที่นับว่า "ใกล้คาน": ห่างแนวคานไม่เกินนี้ (ค่าที่เลือกเอง)
MATCH_PT = 4.0             # --vs-gt: ผู้สมัครกับ GT ถือว่าเป็นที่เดียวกันเมื่อห่างไม่เกินนี้ (หรือชื่อเส้นเดียวกัน)


# ---------- กฎล้วน (ทดสอบใน --demo) ----------
def plan_grids(lines, scales):
    """lines = detect() {'v': [...], 'h': [...]} · scales = {plan: {'scale': pt/m}} -> {plan: dict(v, h, scale)} (เรียงตามตำแหน่ง)
    แปลนที่ไม่มีสเกล หรือไม่มีเส้นครบสองแกน = ไม่ลอง (ใส่ใน skipped พร้อมเหตุผล)"""
    plans = {ln.get("plan") for ax in ("v", "h") for ln in lines.get(ax, [])}
    out, skipped = {}, {}
    for p in sorted(plans, key=lambda v: (v is None, v)):
        v = sorted((ln for ln in lines.get("v", []) if ln.get("plan") == p and ln.get("label") is not None), key=lambda l: l["pos"])
        h = sorted((ln for ln in lines.get("h", []) if ln.get("plan") == p and ln.get("label") is not None), key=lambda l: l["pos"])
        sc = (scales.get(p) or {}).get("scale")
        if not sc:
            skipped[p] = "no_scale"
        elif len(v) < 2 or len(h) < 2:
            skipped[p] = "fewer_than_2_lines_on_an_axis"
        else:
            out[p] = dict(v=v, h=h, scale=float(sc))
    return out, skipped


def candidates(grids, pieces, boxes, use_box=False):
    """ลองทุกจุดตัดและทุกช่วงกริดของแต่ละแปลน -> (points, beams) พร้อมผล hit/ok"""
    pts, beams = [], []
    for p, g in grids.items():
        a = g["scale"]
        max_pt, band = P4.POINT_MAX_M * a, P4.BEAM_BAND_M * a
        for vl in g["v"]:
            for hl in g["h"]:
                pt = (vl["pos"], hl["pos"])
                hit = P4.point_hit(pt, boxes, max_pt) or (use_box and P4.box_around(pt, P4.near(pieces, pt, max_pt), max_pt / 2))
                pts.append(dict(plan=p, x=vl["label"], y=hl["label"], pt=pt, hit=bool(hit)))
        for hl in g["h"]:                                  # ช่วงตามแนวนอน (บนเส้นนอน hl ระหว่างเส้นตั้งติดกัน)
            for v0, v1 in zip(g["v"], g["v"][1:]):
                p0, p1 = (v0["pos"], hl["pos"]), (v1["pos"], hl["pos"])
                c = P4.cover_fraction(p0, p1, pieces, band)
                beams.append(dict(plan=p, axis="x", line=hl["label"], a=v0["label"], b=v1["label"], p0=p0, p1=p1,
                                  cover=round(c, 2), ok=c >= P4.BEAM_COVER_OK))
        for vl in g["v"]:                                  # ช่วงตามแนวตั้ง
            for h0, h1 in zip(g["h"], g["h"][1:]):
                p0, p1 = (vl["pos"], h0["pos"]), (vl["pos"], h1["pos"])
                c = P4.cover_fraction(p0, p1, pieces, band)
                beams.append(dict(plan=p, axis="y", line=vl["label"], a=h0["label"], b=h1["label"], p0=p0, p1=p1,
                                  cover=round(c, 2), ok=c >= P4.BEAM_COVER_OK))
    return pts, beams


def dist_to_segment(q, p0, p1):
    """(ระยะตั้งฉาก, ตำแหน่งตามแนว 0..1 ถ้าอยู่ในช่วง ไม่งั้น None)"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return math.hypot(q[0] - p0[0], q[1] - p0[1]), None
    t = ((q[0] - p0[0]) * dx + (q[1] - p0[1]) * dy) / L2
    perp = abs((q[0] - p0[0]) * dy - (q[1] - p0[1]) * dx) / math.sqrt(L2)
    return perp, (t if 0.0 <= t <= 1.0 else None)


def name_candidates(pts, beams, marks, grids):
    """ข้อความฝังที่รูปแบบเหมือนรหัส ใกล้ที่สุดของแต่ละผู้สมัคร (เฉพาะที่ hit/ok) — เดา ไม่ตรวจ
    marks = [(x, y, text)] · จุด: รหัสที่ไม่ขึ้นต้นแบบคาน ภายใน POINT_LABEL_M · คาน: รหัสแบบคาน ห่างแนวไม่เกิน BEAM_LABEL_M และอยู่ในช่วง"""
    for c in pts:
        if not c["hit"]:
            continue
        a, best = grids[c["plan"]]["scale"], None
        for x, y, t in marks:
            if BEAM_MARK_RE.match(t):
                continue
            d = math.hypot(x - c["pt"][0], y - c["pt"][1])
            if d <= POINT_LABEL_M * a and (best is None or d < best[0]):
                best = (d, t)
        c["name_near"] = best[1] if best else None
    for c in beams:
        if not c["ok"]:
            continue
        a, best = grids[c["plan"]]["scale"], None
        for x, y, t in marks:
            if not BEAM_MARK_RE.match(t):
                continue
            perp, along = dist_to_segment((x, y), c["p0"], c["p1"])
            if along is not None and perp <= BEAM_LABEL_M * a and (best is None or perp < best[0]):
                best = (perp, t)
        c["name_near"] = best[1] if best else None


def compare_with_gt(pts, beams, gt_locks_by_plan, grids):
    """นับคะแนนเทียบเฉลย (เฉลยไม่ได้ใช้สร้างผู้สมัคร) · gt_locks_by_plan = {plan: [lock...]} จาก pass4_sp.run_page
    จุด: เทียบด้วย (plan, ชื่อเส้นตั้ง, ชื่อเส้นนอน) · คาน: เทียบทีละช่วงกริด (เฉลยคานยาวแตกเป็นช่วงติดกัน)"""
    gt_pts, gt_bays = set(), set()
    for p, locks in gt_locks_by_plan.items():
        if p not in grids:
            continue
        xs, ys = [l["label"] for l in grids[p]["v"]], [l["label"] for l in grids[p]["h"]]
        for lk in locks:
            if "pts" not in lk or lk.get("kind") == "region":
                continue
            if lk["kind"] == "point":
                gt_pts.add((p,) + tuple(lk["ids"][0]))
            else:
                (x1, y1), (x2, y2) = lk["ids"]
                if x1 == x2:
                    gt_bays |= {(p, "y", x1, a, b) for a, b in P4.bays(ys, y1, y2)}
                elif y1 == y2:
                    gt_bays |= {(p, "x", y1, a, b) for a, b in P4.bays(xs, x1, x2)}
    cand_pts = {(c["plan"], c["x"], c["y"]) for c in pts if c["hit"]}
    cand_bays = {(c["plan"], c["axis"], c["line"], c["a"], c["b"]) for c in beams if c["ok"]}
    # เฉลยที่เส้นของมันไม่ได้ถูก detect ในแปลนนั้น ลองไม่ได้ ไม่นับเป็นพลาด
    tried_pts = {(c["plan"], c["x"], c["y"]) for c in pts}
    tried_bays = {(c["plan"], c["axis"], c["line"], c["a"], c["b"]) for c in beams}

    def score(gt, cand, tried):
        gt_t = gt & tried
        tp = len(gt_t & cand)
        return dict(gt_total=len(gt), gt_testable=len(gt_t), candidates=len(cand), matched=tp,
                    recall=round(tp / len(gt_t), 3) if gt_t else None,
                    precision=round(tp / len(cand), 3) if cand else None,
                    extra_vs_gt=len(cand - gt), missed_vs_gt=len(gt_t - cand))
    return dict(points=score(gt_pts, cand_pts, tried_pts), beams=score(gt_bays, cand_bays, tried_bays))


# ---------- รันหน้าเดียว ----------
def page_marks(page):
    import fitz
    rm, out = page.rotation_matrix, []
    for w in page.get_text("words"):
        t = w[4].strip().rstrip(",;")
        if MARK_RE.match(t):
            r = fitz.Rect(w[:4]) * rm
            out.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, t))
    return out


def run_page(house, pn, ocr=True, labels=True, use_box=False, vs_gt=False, write=True, show_miss=False):
    import fitz
    import gridlab_probe as G
    import gridlab_scale as S
    doc = fitz.open(G.pdf_of(house))
    page = doc[pn - 1]
    lines = G.detect(page, ocr=ocr)
    scales = S.plan_scales(page, lines, ocr=ocr)
    grids, skipped = plan_grids(lines, scales)
    pieces, boxes = P4.drawn_things(page)
    pts, beams = candidates(grids, pieces, boxes, use_box=use_box)
    if labels:
        name_candidates(pts, beams, page_marks(page), grids)
    res = dict(house=house, page=pn, source="page only (no ground truth used to build the overlay)",
               plans={str(p): dict(scale_pt_per_m=round(g["scale"], 2), vlines=[l["label"] for l in g["v"]], hlines=[l["label"] for l in g["h"]])
                      for p, g in grids.items()},
               skipped_plans={str(k): v for k, v in skipped.items()},
               points=dict(tried=len(pts), hit=sum(c["hit"] for c in pts)),
               beams=dict(tried=len(beams), ok=sum(c["ok"] for c in beams)),
               candidates=dict(points=[c for c in pts if c["hit"]], beams=[c for c in beams if c["ok"]]))
    if not grids:
        res["error"] = "no_plan_with_grid_and_scale"
        res["why"] = dict(lines_v=len(lines.get("v", [])), lines_h=len(lines.get("h", [])), page_kind=P4.kind_of_page(page))
    if vs_gt:
        gt = P4.run_page(house, pn, ocr=ocr, write=False)          # อ่านเฉลยเพื่อนับคะแนนเท่านั้น
        by_plan = {}
        for f in gt.get("files", []):
            if f.get("plan") is not None or "locks" in f:
                by_plan.setdefault(f.get("plan"), []).extend(f.get("locks", []))
        res["vs_ground_truth"] = compare_with_gt(pts, beams, by_plan, grids) if "error" not in gt or by_plan else dict(error=gt.get("error"))
    if write:
        out = OUT / house
        out.mkdir(parents=True, exist_ok=True)
        (out / f"pass4_pure_p{pn:02d}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        draw(page, lines, grids, pts, beams, out / f"pass4_pure_p{pn:02d}.png", show_miss=show_miss)
    return res


def draw(page, lines, grids, pts, beams, path, dpi=110, show_miss=False):
    from PIL import Image, ImageDraw, ImageFont
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGB")
    dr, k = ImageDraw.Draw(img), dpi / 72.0
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    H, W = page.rect.height, page.rect.width
    for p, g in grids.items():                            # เส้นกริดที่ code หาเจอ (ฟ้า) + ชื่อ
        for ax, key in (("v", "v"), ("h", "h")):
            for ln in g[key]:
                lo, hi = ln.get("lo"), ln.get("hi")
                if ax == "v":
                    a, b = (ln["pos"] * k, (lo if lo is not None else 0) * k), (ln["pos"] * k, (hi if hi is not None else H) * k)
                else:
                    a, b = ((lo if lo is not None else 0) * k, ln["pos"] * k), ((hi if hi is not None else W) * k, ln["pos"] * k)
                dr.line([a, b], fill=(70, 160, 220), width=1)
                dr.text((a[0] + 3, a[1] + 2), str(ln["label"]), fill=(30, 110, 180), font=font)
    for c in beams:
        a, b = (c["p0"][0] * k, c["p0"][1] * k), (c["p1"][0] * k, c["p1"][1] * k)
        if c["ok"]:
            dr.line([a, b], fill=(20, 160, 60), width=4)
            if c.get("name_near"):
                dr.text(((a[0] + b[0]) / 2 + 3, (a[1] + b[1]) / 2 - 18), "~" + c["name_near"], fill=(20, 130, 50), font=font)
        elif show_miss:
            dr.line([a, b], fill=(240, 130, 20), width=2)
    for c in pts:
        x, y = c["pt"][0] * k, c["pt"][1] * k
        if c["hit"]:
            dr.rectangle([x - 7, y - 7, x + 7, y + 7], outline=(200, 30, 160), width=3)
            if c.get("name_near"):
                dr.text((x + 9, y - 20), "~" + c["name_near"], fill=(200, 30, 160), font=font)
        elif show_miss:
            dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(150, 150, 150))
    img.save(path)


# ---------- self-check ----------
def demo():
    # แปลนสังเคราะห์: เส้นตั้ง 1,2,3 ที่ x = 100,200,300 · เส้นนอน A,B ที่ y = 100,200 · สเกล 50 pt/m
    lines = {"v": [dict(pos=x, label=l, plan=0) for x, l in ((100, "1"), (200, "2"), (300, "3"))],
             "h": [dict(pos=y, label=l, plan=0) for y, l in ((100, "A"), (200, "B"))]}
    grids, skipped = plan_grids(lines, {0: {"scale": 50.0}})
    assert not skipped and list(grids) == [0] and [l["label"] for l in grids[0]["v"]] == ["1", "2", "3"]
    # ไม่มีสเกล / แกนเดียว = ไม่ลอง พร้อมเหตุผล
    assert plan_grids(lines, {})[1] == {0: "no_scale"}
    one_axis = {"v": lines["v"], "h": lines["h"][:1]}
    assert plan_grids(one_axis, {0: {"scale": 50.0}})[1] == {0: "fewer_than_2_lines_on_an_axis"}
    # บนหน้า: กรอบเสา 14x14 pt ที่ (1,A) และ (2,B) · เส้นทึบขนานสองเส้นห่างแกน 8 pt ตลอดช่วง 1-2 บนแนวนอน A (คาน) · ไม่มีอะไรที่อื่น
    boxes = [(93, 93, 107, 107), (193, 193, 207, 207)]
    pieces = [(100, 92, 200, 92), (100, 108, 200, 108)]
    pts, beams = candidates(grids, pieces, boxes)
    hit = {(c["x"], c["y"]) for c in pts if c["hit"]}
    assert len(pts) == 6 and hit == {("1", "A"), ("2", "B")}, hit
    ok = {(c["axis"], c["line"], c["a"], c["b"]) for c in beams if c["ok"]}
    assert len(beams) == 7 and ok == {("x", "A", "1", "2")}, ok          # 2 ช่วง x 2 เส้นนอน + 1 ช่วง x 3 เส้นตั้ง = 7
    # กรอบใหญ่เกิน 2.5 ม. (125 pt) ไม่ใช่เสา · กรอบบางเกิน (ด้านสั้น < 2.5 pt) ไม่นับ
    pts2, _ = candidates(grids, [], [(0, 0, 400, 400), (99, 90, 101, 110)])
    assert not any(c["hit"] for c in pts2)
    # ชื่อ: ไม่ได้เดาข้ามไกล · คานใช้รหัสแบบคานเท่านั้น · จุดไม่ใช้รหัสแบบคาน
    marks = [(112, 90, "F1"), (150, 96, "B2(+0.15)"), (300, 300, "C9"), (110, 100, "B1")]
    name_candidates(pts, beams, marks, grids)
    nm = {(c["x"], c["y"]): c["name_near"] for c in pts if c["hit"]}
    assert nm[("1", "A")] == "F1" and nm[("2", "B")] is None, nm            # B1 ใกล้กว่าแต่เป็นรหัสคาน จึงไม่ใช่ชื่อจุด
    assert [c["name_near"] for c in beams if c["ok"]] == ["B1"]              # B1 อยู่บนแนวคาน (ห่าง 0) ใกล้กว่า B2(+0.15) (ห่าง 4 pt)
    for c in beams + pts:
        c.pop("name_near", None)
    name_candidates(pts, beams, [(150, 96, "B2(+0.15)"), (250, 100, "B7"), (150, 190, "B8")], grids)   # B7 พ้นปลายช่วง, B8 ห่างแนวเกิน 0.6 ม. (30 pt)
    assert [c["name_near"] for c in beams if c["ok"]] == ["B2(+0.15)"]
    # เทียบเฉลย: เฉลยมี (1,A) กับ (3,B) และคาน 1-2 บนเส้น A — ผู้สมัคร (1,A),(2,B) + คาน 1-2
    gt = {0: [dict(kind="point", ids=[("1", "A")], pts=[(100, 100)]), dict(kind="point", ids=[("3", "B")], pts=[(300, 200)]),
              dict(kind="segment", ids=[("1", "A"), ("2", "A")], pts=[(100, 100), (200, 100)])]}
    cmp_ = compare_with_gt(pts, beams, gt, grids)
    assert cmp_["points"]["gt_testable"] == 2 and cmp_["points"]["matched"] == 1 and cmp_["points"]["recall"] == 0.5
    assert cmp_["points"]["precision"] == 0.5 and cmp_["points"]["extra_vs_gt"] == 1 and cmp_["points"]["missed_vs_gt"] == 1
    assert cmp_["beams"]["matched"] == 1 and cmp_["beams"]["recall"] == 1.0 and cmp_["beams"]["precision"] == 1.0
    # เฉลยที่เส้นไม่ได้ถูก detect ในแปลน ลองไม่ได้ ไม่นับเป็นพลาด
    gt2 = {0: [dict(kind="point", ids=[("9", "A")], pts=[(1, 1)])]}
    assert compare_with_gt(pts, beams, gt2, grids)["points"]["gt_testable"] == 0
    print("OK — self-check ผ่าน (กฎสร้างผู้สมัคร/ชื่อ/นับคะแนน เท่านั้น ยังไม่ได้ทดสอบกับ PDF จริง ใช้รันหน้าจริงแล้วดู overlay)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("house", nargs="?")
    ap.add_argument("page", nargs="?", type=int)
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--no-labels", action="store_true")
    ap.add_argument("--show-miss", action="store_true")
    ap.add_argument("--box", action="store_true", help="ใช้ box_around (เส้นสี่ด้านล้อมจุด) ด้วย")
    ap.add_argument("--vs-gt", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not a.house or not a.page:
        return ap.print_help()
    r = run_page(a.house, a.page, ocr=not a.no_ocr, labels=not a.no_labels, use_box=a.box, vs_gt=a.vs_gt, show_miss=a.show_miss)
    print(json.dumps({k: v for k, v in r.items() if k != "candidates"}, ensure_ascii=False, indent=1, default=str))
    print("->", OUT / a.house / f"pass4_pure_p{a.page:02d}.png")


if __name__ == "__main__":
    main()
