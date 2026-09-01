#!/usr/bin/env python3
"""pass3_measure.py — วัดระยะจริงจากพิกเซล โดยใช้ grid master เป็นไม้บรรทัด

    pass1.5/2.5 (CV) ให้พิกัด pixel ของทุกจุดที่ตรวจเจอ
    pass2 (โมเดล)   ให้ grid_ref ของ element ที่มันอ่านออก
    grid master     ให้ pos_m ของทุกเส้นกริด (เมตรจริง)
    ─────────────────────────────────────────────────────────
    pass3 (ไฟล์นี้) เอา 3 อย่างนั้นมาต่อกัน → px ต่อเมตร → วัดอะไรก็ได้บนแผ่นนั้น

วิธี (ไม่ต้องเทรน ไม่ต้อง detect เส้นกริดในภาพ):
  1. หา "หมุด" = element ที่มีทั้ง grid_ref (โมเดลอ่านได้) และ cv_position (CV เห็น)
     → คู่ (pixel, เมตร) ที่รู้ทั้งสองฝั่ง
  2. fit เส้นตรง 2 แกนแยกกัน  px = ax*mx + bx  ·  py = ay*my + by
     (แบบก่อสร้างเป็น orthographic ไม่หมุน — ถ้าหมุนจริง residual จะพุ่งแล้วเราปฏิเสธเอง)
  3. กลับด้าน: pixel ไหนก็แปลงเป็นเมตรได้ → snap เข้ากริดที่ใกล้สุด / วัดคานสู่คาน

ทำไมไม่ detect เส้นกริดเอง: ต้องเขียน Hough + จับคู่ลำดับเส้นกับ id ซึ่งพังง่ายเมื่อ
เส้นบางเส้นถูกบัง — วิธีหมุดใช้คำตอบที่ "อ่านออกแน่ ๆ" อยู่แล้วเป็นตัวตั้ง แล้ว residual
บอกเราเองว่าเชื่อได้แค่ไหน (fail loud ไม่ใช่ fail silent)

กติกา "ไม่เดา" เหมือนทั้งโปรเจกต์: หมุดไม่พอ / residual เกินเกณฑ์ / scale สองแกนไม่เท่ากัน
→ คืน None พร้อมเหตุผลเป็นภาษาไทย ไม่คืนตัวเลขมั่ว

self-check:  python pass3_measure.py
"""
import json
import re
import sys

# ── เกณฑ์ตัดสิน (ตัวเลขเดียว เปลี่ยนที่นี่ที่เดียว) ──────────────────────────────
MIN_ANCHORS = 3          # 2 พอ fit ได้ แต่ 2 = residual 0 เสมอ วัดคุณภาพไม่ได้เลย
SNAP_TOL_M = 0.50        # ไกลกว่านี้จากจุดตัดกริด = ไม่ใช่จุดนั้น ไม่ snap ให้
MAX_RESIDUAL_M = 0.50    # หมุดเบี้ยวเกินนี้ = การ fit ใช้ไม่ได้ ปฏิเสธทั้งแผ่น
MAX_ANISOTROPY = 0.05    # px/m สองแกนต่างกันเกิน 5% = ภาพยืด/หมุน ไม่ใช่แบบ orthographic

# รูปแบบ grid ref แบบไม่มีขีด ("C1", "E1'", "B'2") — พอร์ตจาก raw-extraction-adapter.js
# parseGridRef() ต้องตรงกันเป๊ะ ไม่งั้นสองฝั่งอ่าน ref เดียวกันได้คนละความหมาย
_NO_DASH = re.compile(r"^([A-Za-zก-ฮ]{1,3}'*)(\d+'*)$")


def parse_grid_ref(ref):
    """"D1" → {"row": "D", "col": "1"} · แถว = ตัวอักษร (y_lines) · คอลัมน์ = ตัวเลข (x_lines)
    คืน None ถ้าระบุตำแหน่งแน่นอนไม่ได้ (ว่าง / ขึ้นต้น "~" = โดยประมาณ / รูปแบบไม่ตรง)"""
    if not isinstance(ref, str):
        return None
    s = ref.strip()
    if not s or s.startswith("~"):
        return None
    parts = s.split("-")
    if len(parts) == 2:
        row, col = parts[0].strip(), parts[1].strip()
        return {"row": row, "col": col} if row and col else None
    m = _NO_DASH.match(s)
    return {"row": m.group(1), "col": m.group(2)} if m else None


def grid_pos(grid, axis, line_id):
    """เมตรของเส้นกริดเส้นนั้น — None ถ้าไม่รู้จัก หรือ pos_m เป็น null (ห้ามเดา)"""
    lines = (grid or {}).get("x_lines" if axis == "x" else "y_lines") or []
    for ln in lines:
        if ln.get("id") == line_id:
            p = ln.get("pos_m")
            return float(p) if isinstance(p, (int, float)) else None
    return None


def ref_to_metre(grid, ref):
    """grid ref → (mx, my) เมตร · None ถ้าเส้นใดเส้นหนึ่งไม่รู้ตำแหน่ง"""
    g = parse_grid_ref(ref)
    if not g:
        return None
    mx = grid_pos(grid, "x", g["col"])   # ตัวเลข = แกนนอน (x_lines)
    my = grid_pos(grid, "y", g["row"])   # ตัวอักษร = แกนตั้ง (y_lines)
    return None if mx is None or my is None else (mx, my)


def rect_center(box):
    """จุดศูนย์กลางจากมุมไปมุมของสี่เหลี่ยม — รับได้ทั้งแบบ {cx,cy} (cv_scan ให้มาแล้ว)
    และแบบ {x,y,w,h} (มุมซ้ายบน+ขนาด) · คืน (px, py) หรือ None ถ้าอ่านไม่ได้"""
    if not isinstance(box, dict):
        return None
    if isinstance(box.get("cx"), (int, float)) and isinstance(box.get("cy"), (int, float)):
        return (float(box["cx"]), float(box["cy"]))
    x, y, w, h = (box.get(k) for k in ("x", "y", "w", "h"))
    if all(isinstance(v, (int, float)) for v in (x, y, w, h)):
        return (x + w / 2.0, y + h / 2.0)   # มุมซ้ายบน → มุมขวาล่าง แล้วหารสอง
    return None


def _fit_line(pairs):
    """least squares  v = a*u + b  จาก [(u, v)] · None ถ้า u ไม่กระจาย (ทุกจุดอยู่เส้นเดียว)"""
    n = len(pairs)
    if n < 2:
        return None
    su = sum(u for u, _ in pairs)
    sv = sum(v for _, v in pairs)
    suu = sum(u * u for u, _ in pairs)
    suv = sum(u * v for u, v in pairs)
    denom = n * suu - su * su
    if abs(denom) < 1e-9:      # u ทุกตัวเท่ากัน = หมุดเรียงอยู่บนกริดเส้นเดียว fit ไม่ได้
        return None
    a = (n * suv - su * sv) / denom
    return (a, (sv - a * su) / n)


def build_transform(anchors, grid):
    """หมุด [(px, py, ref)] + grid master → ตัวแปลง pixel ↔ เมตร

    คืน (transform_dict, None) เมื่อใช้ได้ · (None, "เหตุผลไทย") เมื่อใช้ไม่ได้
    transform: ax,bx,ay,by (px = a*m + b), px_per_m_x/y, residual_max_m, rms_m, n_anchors"""
    pts = []
    for px, py, ref in anchors:
        m = ref_to_metre(grid, ref)
        if m is not None:
            pts.append((px, py, m[0], m[1]))
    if len(pts) < MIN_ANCHORS:
        return None, (f"หมุดไม่พอ: ได้ {len(pts)} ต้องการอย่างน้อย {MIN_ANCHORS} "
                      f"(element ที่มีทั้ง grid_ref ที่รู้ pos_m และพิกัด CV)")

    fx = _fit_line([(mx, px) for px, _, mx, _ in pts])
    fy = _fit_line([(my, py) for _, py, _, my in pts])
    if fx is None or fy is None:
        return None, "หมุดเรียงอยู่บนกริดเส้นเดียว (แกนใดแกนหนึ่งไม่กระจาย) — fit ไม่ได้"
    ax, bx = fx
    ay, by = fy
    if abs(ax) < 1e-9 or abs(ay) < 1e-9:
        return None, "scale ออกมาเป็นศูนย์ — ข้อมูลหมุดผิดปกติ"

    # residual วัดเป็น "เมตร" ไม่ใช่พิกเซล — คนอ่านเข้าใจทันทีว่าเบี้ยวแค่ไหนบนของจริง
    errs = []
    for px, py, mx, my in pts:
        errs.append(max(abs((px - (ax * mx + bx)) / ax), abs((py - (ay * my + by)) / ay)))
    residual_max = max(errs)
    rms = (sum(e * e for e in errs) / len(errs)) ** 0.5
    if residual_max > MAX_RESIDUAL_M:
        return None, (f"หมุดเบี้ยวเกินเกณฑ์: คลาดสูงสุด {residual_max:.2f} ม. "
                      f"(เกิน {MAX_RESIDUAL_M} ม.) — grid_ref บางตัวน่าจะผิด ไม่ใช้ผลนี้")

    pxm_x, pxm_y = abs(ax), abs(ay)
    aniso = abs(pxm_x - pxm_y) / ((pxm_x + pxm_y) / 2)
    if aniso > MAX_ANISOTROPY:
        return None, (f"px ต่อเมตรสองแกนไม่เท่ากัน ({pxm_x:.1f} vs {pxm_y:.1f}, ต่าง "
                      f"{aniso * 100:.1f}%) — ภาพน่าจะยืด/หมุน ไม่ใช่ orthographic ไม่ใช้ผลนี้")

    return {
        "ax": ax, "bx": bx, "ay": ay, "by": by,
        "px_per_m_x": round(pxm_x, 2), "px_per_m_y": round(pxm_y, 2),
        "residual_max_m": round(residual_max, 3), "rms_m": round(rms, 3),
        "n_anchors": len(pts),
    }, None


def pixel_to_metre(t, px, py):
    """pixel → เมตรบนระบบพิกัดของ grid master"""
    return ((px - t["bx"]) / t["ax"], (py - t["by"]) / t["ay"])


def metre_distance(t, p1, p2):
    """ระยะจริงเป็นเมตรระหว่างสองจุด pixel (เช่น คานสู่คาน / เสาสู่เสา)"""
    (x1, y1), (x2, y2) = pixel_to_metre(t, *p1), pixel_to_metre(t, *p2)
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def nearest_grid_ref(grid, mx, my, tol_m=SNAP_TOL_M):
    """จุดเมตร → grid ref ที่ใกล้สุด · คืน (ref, ระยะห่าง) หรือ (None, ระยะ) ถ้าไกลเกิน tol
    ไกลเกิน = ไม่ยัดให้ (ของจริงนั่งบนจุดตัดกริด ถ้าไม่ใกล้แปลว่าไม่ใช่จุดนั้น)"""
    xs = [(l["id"], l["pos_m"]) for l in (grid or {}).get("x_lines") or []
          if isinstance(l.get("pos_m"), (int, float))]
    ys = [(l["id"], l["pos_m"]) for l in (grid or {}).get("y_lines") or []
          if isinstance(l.get("pos_m"), (int, float))]
    if not xs or not ys:
        return None, None
    col, dx = min(((i, abs(p - mx)) for i, p in xs), key=lambda t: t[1])
    row, dy = min(((i, abs(p - my)) for i, p in ys), key=lambda t: t[1])
    d = (dx * dx + dy * dy) ** 0.5
    return (f"{row}{col}" if d <= tol_m else None), round(d, 3)


def _element_refs(el):
    """ref ทั้งหมดของ element นี้ — จุด (grid_refs[]) และเส้น (start/end)"""
    refs = [r for r in (el.get("grid_refs") or []) if isinstance(r, str)]
    for k in ("grid_ref_start", "grid_ref_end"):
        if isinstance(el.get(k), str):
            refs.append(el[k])
    return refs


POINT_CLASSES = ("footing", "column")


def _normalize(pts):
    """ย่อชุดจุดลงกรอบ [0,1] ของตัวเอง — เทียบรูปทรงการกระจายตัวข้ามหน่วย (เมตร vs พิกเซล)
    คืน None ถ้าจุดทั้งหมดกองอยู่ที่เดียว (กรอบกว้าง 0 หารไม่ได้)"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if w <= 0 or h <= 0:
        return None
    return [((x - min(xs)) / w, (y - min(ys)) / h) for x, y in pts]


def _mutual_nearest(a, b):
    """คู่ที่ "ต่างฝ่ายต่างเห็นกันเป็นเพื่อนบ้านใกล้สุด" เท่านั้น → [(i, j)]

    ใช้ mutual (ไม่ใช่ nearest ทางเดียว) เพราะจำนวนสองฝั่งไม่เท่ากันเป็นเรื่องปกติ —
    CV จับไม่ครบ / โมเดลตอบเกิน · one-way nearest จะยัดคู่ให้ทุกตัวรวมทั้งตัวที่ไม่มีคู่จริง
    mutual ตัดพวกนั้นทิ้งเอง โดยไม่ต้องรู้ล่วงหน้าว่าใครขาด"""
    d = lambda p, q: (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
    best_a = [min(range(len(b)), key=lambda j: d(a[i], b[j])) for i in range(len(a))]
    best_b = [min(range(len(a)), key=lambda i: d(a[i], b[j])) for j in range(len(b))]
    return [(i, j) for i, j in enumerate(best_a) if best_b[j] == i]


def anchors_by_shape(elements, cv_scan, grid):
    """ทางสำรองเมื่อโมเดลไม่ตอบ cv_mark (ซึ่งเป็นกรณีปกติ — destrier เห็น cv_mark
    ตอนเทรนแค่ ~9% ของตัวอย่าง) จับคู่ "จุดที่โมเดลบอก grid_ref" กับ "จุดที่ CV เห็น"
    ด้วยรูปทรงการกระจายตัวแทน แล้วปล่อยให้ residual เป็นคนตรวจว่าจับคู่ถูกไหม

    ปลอดภัยเพราะ: จับคู่ผิด → หมุดเพี้ยน → residual พุ่ง → build_transform ปฏิเสธเอง
    (ไม่ต้องเชื่อการจับคู่นี้ล่วงหน้า มีตัวจับผิดอยู่ปลายทางแล้ว)
    เฉพาะฐานราก/เสาเท่านั้น — คานใช้เป็นหมุดไม่ได้อยู่แล้ว (จุดกึ่งกลางไม่อยู่ที่ ref)"""
    if not isinstance(cv_scan, dict):
        return [], set()
    out, used_xy = [], set()
    for cls in POINT_CLASSES:
        cv_raw = [e for e in cv_scan.get("elements") or []
                  if e.get("class") == cls and isinstance(e.get("cx"), (int, float))]
        cv_pts = [(e["cx"], e["cy"]) for e in cv_raw]
        model = []
        for el in elements or []:
            if el.get("element_type") != cls:
                continue
            # ⚠️ 1 record อาจแทนของหลายชิ้น — สเปกบอกว่า grid_refs เป็น "อาร์เรย์ของจุด"
            # และ count คือจำนวนชิ้นจริง เช่น {"element_id":"F1","count":11,"grid_refs":[11 จุด]}
            # เดิมบังคับ len(refs)==1 เลยมองข้ามทั้งหมด → หมุด 0 ทั้งที่ CV เจอ 12 จุดตรงเป๊ะ
            # (เจอ 2026-09-01 จากการจำลองบ้าน01 ด้วยเฉลยจริง — การจำลองบ้านก่อนหน้าที่
            #  Claude เขียนคำตอบเองแบบ 1 ref/element ปิดบังบั๊กนี้ไว้สนิท)
            refs = [r for r in (el.get("grid_refs") or []) if isinstance(r, str)]
            if not refs and isinstance(el.get("grid_ref_start"), str):
                refs = [el["grid_ref_start"]]      # จุดเดี่ยวที่เขียนเป็น start
            single = len(refs) == 1
            for r in refs:
                m = ref_to_metre(grid, r)
                if m:
                    model.append((m, r, el if single else None))
        if len(cv_pts) < 2 or len(model) < 2:
            continue
        na = _normalize([m for m, _, _ in model])
        nb = _normalize(cv_pts)
        if na is None or nb is None:
            continue
        for i, j in _mutual_nearest(na, nb):
            out.append((cv_pts[j][0], cv_pts[j][1], model[i][1]))
            used_xy.add((round(cv_pts[j][0]), round(cv_pts[j][1])))
            # แนบพิกัดกลับให้ element ที่จับคู่ได้ — ไม่งั้นขั้นวัดต่อไปมองไม่เห็นมัน
            # (เติมเฉพาะตอนที่ยังว่าง ตามกฎ เติมได้ ห้ามทับ) · element ที่แทนของหลายชิ้น
            # (count>1) แนบไม่ได้ เพราะ cv_position เก็บได้จุดเดียว — ใช้เป็นหมุดอย่างเดียว
            el = model[i][2]
            if el is not None and not el.get("cv_position"):
                src = cv_raw[j]
                el["cv_position"] = {"cx": src["cx"], "cy": src["cy"],
                                     "w": src.get("w"), "h": src.get("h"), "class": cls}
                el.setdefault("confidence_flags", []).append("cv_matched_by_shape")
    return out, used_xy


def collect_anchors(elements):
    """element ที่มี cv_position + ref จุดเดียวชัดเจน = หมุดที่ใช้ได้

    ตัดคานออกเสมอ แม้จะมี ref เดียว — ฐานราก/เสา "นั่งบนจุดตัดกริดพอดี" จุดกึ่งกลางไอคอน
    จึงเป็นตำแหน่งของ ref จริง แต่คานพาดจากจุดหนึ่งไปอีกจุด **จุดกึ่งกลางกล่องคานไม่ได้อยู่ที่
    ref ใดเลย** เอามาเป็นหมุดเมื่อไหร่ = ป้อนพิกัดผิดเข้าไปใน fit ทั้งแผ่นพัง
    (เจอตอนเขียนเทส: คาน B9 ref A1 แต่กล่องอยู่กลางช่วง → residual 2 ม. ปฏิเสธทั้งหน้า)"""
    out = []
    for el in elements or []:
        cv = el.get("cv_position") or {}
        if str(cv.get("class", "")).startswith("beam"):
            continue
        c = rect_center(cv)
        refs = _element_refs(el)
        if c and len(refs) == 1:
            out.append((c[0], c[1], refs[0]))
    return out


def measure_page(doc, grid, cv_scan=None):
    """เติมผลวัดลง doc (แก้ในที่) + คืนรายงานสรุปของแผ่นนี้

    doc      = ผล pass2 ของหน้านั้น (ผ่าน merge_cv_marks มาแล้ว = element มี cv_position)
    grid     = grid master ({"x_lines": [...], "y_lines": [...]})
    cv_scan  = ผล pass1.5/2.5 ของหน้านั้น (ใช้จุดที่ CV เห็นแต่โมเดลไม่ได้ตอบ)
    """
    els = doc.get("elements") if isinstance(doc.get("elements"), list) else []
    report = {"ok": False, "reason": None, "transform": None, "anchor_source": None,
              "measured": 0, "grid_check": [], "cv_only": []}

    # ทาง 1: cv_mark ที่โมเดล echo กลับมา (แม่นสุด แต่โมเดลมักไม่ตอบ)
    anchors = collect_anchors(els)
    report["anchor_source"] = "cv_mark"
    anchored_xy = set()
    if len(anchors) < MIN_ANCHORS:
        # ทาง 2: จับคู่ด้วยรูปทรง — residual ปลายทางเป็นคนตรวจว่าถูกไหม
        shaped, used_xy = anchors_by_shape(els, cv_scan, grid)
        if len(shaped) > len(anchors):
            anchors, report["anchor_source"] = shaped, "shape_match"
            anchored_xy = used_xy

    t, why = build_transform(anchors, grid)
    if t is None:
        report["reason"] = why
        doc.setdefault("warnings", []).append(f"pass3 วัดระยะไม่ได้: {why}")
        return report
    report["ok"] = True
    report["transform"] = t

    for el in els:
        c = rect_center(el.get("cv_position"))
        if not c:
            continue
        mx, my = pixel_to_metre(t, *c)
        info = {"center_px": [round(c[0], 1), round(c[1], 1)],
                "pos_m": [round(mx, 3), round(my, 3)]}
        span = _beam_span_m(el.get("cv_position") or {}, t)
        if span:
            info["span_m_cv"] = span
        refs = _element_refs(el)
        if len(refs) == 1:
            # โมเดลตอบ ref มาแล้ว → เราไม่ทับ แต่บอกว่าห่างจากจุดนั้นจริงกี่เมตร (ตัวจับผิด)
            nominal = ref_to_metre(grid, refs[0])
            if nominal:
                d = ((mx - nominal[0]) ** 2 + (my - nominal[1]) ** 2) ** 0.5
                info["grid_ref_check_m"] = round(d, 3)
                if d > SNAP_TOL_M:
                    report["grid_check"].append({"ref": refs[0], "off_by_m": round(d, 3),
                                                 "id": el.get("element_id") or el.get("id")})
        elif not refs:
            # โมเดลไม่ได้ให้ตำแหน่ง → นี่คือที่ pass3 เติมให้จริง
            ref, d = nearest_grid_ref(grid, mx, my)
            info["grid_ref_cv"] = ref
            info["snap_dist_m"] = d
        el["cv_measure"] = info
        report["measured"] += 1

    # จุดที่ CV เห็น (รวม self-harvest ของ pass2.5) แต่โมเดลไม่เคยพูดถึงเลย
    for pt in _cv_only_points(cv_scan, els, anchored_xy):
        mx, my = pixel_to_metre(t, pt["cx"], pt["cy"])
        ref, d = nearest_grid_ref(grid, mx, my)
        entry = {"class": pt.get("class"), "n": pt.get("n"),
                 "center_px": [pt["cx"], pt["cy"]],
                 "pos_m": [round(mx, 3), round(my, 3)],
                 "grid_ref_cv": ref, "snap_dist_m": d,
                 "source": pt.get("source", "pass1.5")}
        span = _beam_span_m(pt, t)
        if span:
            entry["span_m_cv"] = span
        report["cv_only"].append(entry)
    if report["cv_only"]:
        doc.setdefault("warnings", []).append(
            f"pass3: CV เห็น {len(report['cv_only'])} จุดที่โมเดลไม่ได้ตอบ "
            f"(ดู pass3 report — ยังไม่เติมเป็น element ให้ ต้องคนตัดสิน)")
    return report


def _cv_only_points(cv_scan, elements, anchored_xy=()):
    """จุดจาก cv_scan ที่ไม่มี element ไหนอ้างถึงเลย — รวม self_harvest_points (pass2.5)

    ⚠️ ต้องเช็คทั้ง cv_mark **และพิกัดของ cv_position** (แก้ 2026-09-01 หลังเจอในการจำลอง
    บ้านจริง): ตอนจับคู่ด้วยรูปทรง element ไม่มี cv_mark เลย ถ้าดูแต่ cv_mark จะเห็นว่า
    "ไม่มีใครใช้" ทุกจุด แล้วเพิ่มฐานรากตัวเดิมซ้ำเป็น element ใหม่อีกรอบ = นับซ้ำเข้า BOQ
    (เจอจริง: 15 ฐานรากที่จับคู่แล้ว ถูกเพิ่มซ้ำจนกลายเป็น 48 element ใหม่)"""
    if not isinstance(cv_scan, dict):
        return []
    used = {el.get("cv_mark") for el in elements or [] if el.get("cv_mark") is not None}
    used_xy = {(round(p["cx"]), round(p["cy"])) for p in
               (el.get("cv_position") for el in elements or [])
               if isinstance(p, dict) and isinstance(p.get("cx"), (int, float))}
    # จุดที่ถูกใช้เป็นหมุด = โมเดลตอบถึงมันแล้ว (แค่ตอบรวมเป็น record เดียวที่มี count)
    # ไม่นับเป็น "CV เห็นแต่โมเดลไม่ตอบ" ไม่งั้นฐานรากตัวเดิมถูกเพิ่มซ้ำเข้า BOQ
    used_xy |= set(anchored_xy or ())
    out = [dict(e, source="pass1.5") for e in cv_scan.get("elements") or []
           if e.get("n") not in used and isinstance(e.get("cx"), (int, float))
           and (round(e["cx"]), round(e["cy"])) not in used_xy]
    # self-harvest ไม่มีเลข n (มันคือของที่คลังกลางจับไม่ติด แล้วเจอทีหลัง)
    out += [dict(p, source="pass2.5") for p in cv_scan.get("self_harvest_points") or []
            if isinstance(p.get("cx"), (int, float))]
    return out


# ── รวมผล pass3 กลับเข้า pass2 ────────────────────────────────────────────────
# กฎเดียวจากมะขาม (2026-09-01): "ถ้าข้อมูลใน pass2 ขาดไปก็เติมให้ครบ เติมได้แต่ห้ามเอาออก"
# → additive อย่างเดียว ไม่ทับค่าที่โมเดลตอบมา ไม่ลบ element ไหนทิ้ง
# ค่าที่โมเดลตอบชนกับที่เราวัดได้ = ของโมเดลชนะเสมอ เราแค่ติดธงไว้ให้คนดู
CV_CLASS_TO_ELEMENT_TYPE = {"footing": "footing", "column": "column",
                            "beam_h": "beam", "beam_v": "beam"}


def _beam_span_m(el_cv, t):
    """ความยาวคานจากกล่อง CV → เมตร · beam_h วัดด้านกว้าง, beam_v วัดด้านสูง
    None ถ้าไม่ใช่คานหรือขนาดอ่านไม่ได้ (ไม่เดา)"""
    cls = el_cv.get("class")
    if cls not in ("beam_h", "beam_v"):
        return None
    px = el_cv.get("w") if cls == "beam_h" else el_cv.get("h")
    if not isinstance(px, (int, float)) or px <= 0:
        return None
    per_m = t["px_per_m_x"] if cls == "beam_h" else t["px_per_m_y"]
    return round(px / per_m, 3) if per_m else None


# CV เห็นทุกอย่างบนแผ่นเดียว แต่ pass2 แบ่งงานเป็น subtask — จุดที่ CV เจอจึงต้องเข้า
# subtask ที่ "รับผิดชอบของชนิดนั้น" เท่านั้น ไม่งั้นคานบนแผ่นฐานรากจะถูกเพิ่มเป็น element
# ซ้ำกับที่โมเดลตอบไว้ในไฟล์ plan_beam แล้ว = นับซ้ำเข้า BOQ (เจอในการจำลองบ้านจริง)
SUBTASK_CV_CLASSES = {
    "plan_footing": ("footing", "column"),   # เสาอยู่บนแผ่นฐานรากเสมอในแบบไทย
    "plan_beam": ("beam_h", "beam_v"),
    "plan_column": ("column",),
    "plan_slab": (),                          # CV ไม่มี template ของพื้น
}


def merge_into_pass2(doc, report, grid, subtask=None):
    """เติมของที่ขาดใน doc ของ pass2 จากผล pass3 — คืนสรุปว่าเติมอะไรไปบ้าง

    เติม 3 อย่าง (ทั้งหมด "เฉพาะตอนที่ของเดิมว่าง" เท่านั้น):
      1. grid_refs ที่ว่าง → ใส่ ref ที่วัดได้
      2. span_length_m ที่ว่างของคาน → ใส่ความยาวที่วัดจากกล่อง CV
      3. จุดที่ CV เห็น (pass1.5 + pass2.5) แต่โมเดลไม่ตอบเลย → เพิ่มเป็น element ใหม่
         โดย element_id เป็น null เสมอ — เรารู้ตำแหน่ง ไม่รู้ว่ามันชื่ออะไร ห้ามแต่งชื่อ
    """
    added = {"grid_refs": 0, "span": 0, "elements": 0}
    if not report.get("ok"):
        return added
    els = doc.get("elements")
    if not isinstance(els, list):
        return added

    for el in els:
        m = el.get("cv_measure") or {}
        # 1. ref ที่ขาด — เฉพาะตอนที่ไม่มีเลย (ว่าง/ไม่มีคีย์) ไม่ทับของโมเดลเด็ดขาด
        if m.get("grid_ref_cv") and not (el.get("grid_refs") or el.get("grid_ref_start")):
            el["grid_refs"] = [m["grid_ref_cv"]]
            el.setdefault("confidence_flags", []).append("grid_ref_added_by_cv_pass3")
            added["grid_refs"] += 1
        # 2. ความยาวคานที่ขาด — pass3 วัดจากกล่องจริง ไม่ต้องพึ่งว่า ref อยู่ในกริดไหม
        if m.get("span_m_cv") and el.get("span_length_m") in (None, 0):
            el["span_length_m"] = m["span_m_cv"]
            el["span_source"] = "cv_measured"
            el.setdefault("confidence_flags", []).append("span_measured_by_cv_pass3")
            added["span"] += 1

    # 3. จุดที่โมเดลไม่เคยพูดถึง (รวม self-harvest ของ pass2.5) → เพิ่มเป็น element
    allowed = SUBTASK_CV_CLASSES.get(subtask) if subtask else None
    for pt in report.get("cv_only") or []:
        if allowed is not None and pt.get("class") not in allowed:
            continue          # ของชนิดนี้เป็นงานของ subtask อื่น ปล่อยให้เขาเพิ่มเอง
        els.append({
            "element_id": None,          # ไม่รู้มาร์ค ห้ามแต่ง — คนกรอกตอนตรวจ
            "element_type": CV_CLASS_TO_ELEMENT_TYPE.get(pt.get("class")),
            "grid_refs": [pt["grid_ref_cv"]] if pt.get("grid_ref_cv") else [],
            "span_length_m": pt.get("span_m_cv"),
            "span_source": "cv_measured" if pt.get("span_m_cv") else None,
            "cv_measure": {"center_px": pt.get("center_px"), "pos_m": pt.get("pos_m"),
                           "source": pt.get("source")},
            "confidence_score": 0.5,     # เครื่องเห็น คนยังไม่ยืนยัน
            "confidence_flags": ["element_added_by_cv_pass3", f"cv_{pt.get('source', '')}"],
        })
        added["elements"] += 1

    if any(added.values()):
        doc.setdefault("warnings", []).append(
            f"pass3 เติมข้อมูลที่ขาด: grid_ref {added['grid_refs']} · ความยาวคาน {added['span']} "
            f"· element ใหม่จาก CV {added['elements']} (ทั้งหมดติดธง cv_pass3 ตรวจก่อนใช้)")
    return added


def demo():
    """self-check: กริด 3x3 ระยะจริงรู้อยู่แล้ว → fit ต้องได้ px/m ตรงเป๊ะ และต้องปฏิเสธของเสีย"""
    grid = {"x_lines": [{"id": "1", "pos_m": 0.0}, {"id": "2", "pos_m": 4.0},
                        {"id": "3", "pos_m": 7.0}],
            "y_lines": [{"id": "A", "pos_m": 0.0}, {"id": "B", "pos_m": 3.0},
                        {"id": "C", "pos_m": 8.0}]}
    # ภาพสมมติ 50 px/m, origin ที่ (100, 80)
    to_px = lambda mx, my: (100 + 50 * mx, 80 + 50 * my)

    assert parse_grid_ref("D1") == {"row": "D", "col": "1"}
    assert parse_grid_ref("A-1") == {"row": "A", "col": "1"}
    assert parse_grid_ref("~B2") is None and parse_grid_ref("") is None
    assert rect_center({"x": 10, "y": 20, "w": 10, "h": 20}) == (15.0, 30.0)
    assert rect_center({"cx": 5, "cy": 6, "w": 2, "h": 2}) == (5.0, 6.0)

    anchors = [(*to_px(0, 0), "A1"), (*to_px(4, 0), "A2"), (*to_px(0, 3), "B1"),
               (*to_px(7, 8), "C3")]
    t, why = build_transform(anchors, grid)
    assert t and why is None, why
    assert abs(t["px_per_m_x"] - 50) < 0.01 and abs(t["px_per_m_y"] - 50) < 0.01
    assert t["residual_max_m"] < 1e-6, t

    # แปลงกลับต้องได้เมตรเดิม และวัดระยะคานสู่คานต้องตรง (A1→A2 = 4.00 ม.)
    mx, my = pixel_to_metre(t, *to_px(4, 3))
    assert abs(mx - 4) < 1e-6 and abs(my - 3) < 1e-6
    assert abs(metre_distance(t, to_px(0, 0), to_px(4, 0)) - 4.0) < 1e-6

    # snap: ตรงจุดตัด = ได้ ref · ห่าง 2 ม. = ไม่ยัดให้
    assert nearest_grid_ref(grid, 4.0, 3.0)[0] == "B2"
    assert nearest_grid_ref(grid, 5.9, 1.4)[0] is None

    # หมุดน้อยไป / เรียงเส้นเดียว / เบี้ยว → ต้องปฏิเสธพร้อมเหตุผล ไม่คืนตัวเลขมั่ว
    assert build_transform(anchors[:2], grid)[0] is None
    assert build_transform([(*to_px(0, 0), "A1"), (*to_px(0, 3), "B1"),
                            (*to_px(0, 8), "C1")], grid)[0] is None
    bad = list(anchors) + [(to_px(0, 0)[0] + 400, to_px(0, 0)[1], "A3")]
    t_bad, why_bad = build_transform(bad, grid)
    assert t_bad is None and "เบี้ยว" in why_bad, why_bad

    # ทั้งหน้า: element 1 ตัวไม่มี ref → pass3 ต้องเติม grid_ref_cv ให้
    doc = {"elements": [
        {"element_id": "F1", "grid_refs": ["A1"], "cv_position": dict(zip(("cx", "cy"), to_px(0, 0)))},
        {"element_id": "F2", "grid_refs": ["A2"], "cv_position": dict(zip(("cx", "cy"), to_px(4, 0)))},
        {"element_id": "F3", "grid_refs": ["B1"], "cv_position": dict(zip(("cx", "cy"), to_px(0, 3)))},
        {"element_id": "F4", "grid_refs": [], "cv_position": dict(zip(("cx", "cy"), to_px(4, 3)))},
    ]}
    cv = {"elements": [{"n": 9, "cx": to_px(7, 8)[0], "cy": to_px(7, 8)[1], "class": "footing"}],
          "self_harvest_points": [{"cx": to_px(0, 8)[0], "cy": to_px(0, 8)[1], "class": "column"}]}
    rep = measure_page(doc, grid, cv)
    assert rep["ok"] and rep["measured"] == 4, rep
    assert doc["elements"][3]["cv_measure"]["grid_ref_cv"] == "B2"
    assert doc["elements"][0]["cv_measure"]["grid_ref_check_m"] < 1e-6
    assert len(rep["cv_only"]) == 2, rep["cv_only"]
    assert {c["grid_ref_cv"] for c in rep["cv_only"]} == {"C3", "C1"}
    assert {c["source"] for c in rep["cv_only"]} == {"pass1.5", "pass2.5"}

    # ── merge_into_pass2: กฎ "เติมได้ ห้ามเอาออก" ──────────────────────────────
    import copy
    doc2 = {"elements": [
        # โมเดลตอบครบ → ห้ามแตะ
        {"element_id": "F1", "grid_refs": ["A1"], "span_length_m": 3.0,
         "cv_position": dict(zip(("cx", "cy"), to_px(0, 0)))},
        {"element_id": "F2", "grid_refs": ["A2"], "cv_position": dict(zip(("cx", "cy"), to_px(4, 0)))},
        {"element_id": "F3", "grid_refs": ["B1"], "cv_position": dict(zip(("cx", "cy"), to_px(0, 3)))},
        # ref ขาด → ต้องเติม
        {"element_id": "F4", "grid_refs": [], "cv_position": dict(zip(("cx", "cy"), to_px(4, 3)))},
        # คานที่ span ขาด แต่ CV เห็นกล่องกว้าง 200px = 4.00 ม. → ต้องเติม
        {"element_id": "B9", "grid_refs": ["A1"], "span_length_m": None,
         "cv_position": {**dict(zip(("cx", "cy"), to_px(2, 0))), "w": 200, "h": 20,
                         "class": "beam_h"}},
    ]}
    before = copy.deepcopy(doc2)
    cv2 = {"elements": [{"n": 9, "cx": to_px(7, 8)[0], "cy": to_px(7, 8)[1], "class": "footing"}],
           "self_harvest_points": [{"cx": to_px(0, 8)[0], "cy": to_px(0, 8)[1], "class": "column"}]}
    rep2 = measure_page(doc2, grid, cv2)
    got = merge_into_pass2(doc2, rep2, grid)

    assert got["grid_refs"] == 1, got          # F4 เท่านั้น
    assert got["span"] == 1, got               # B9 เท่านั้น
    assert got["elements"] == 2, got           # pass1.5 หนึ่ง + pass2.5 หนึ่ง
    assert doc2["elements"][3]["grid_refs"] == ["B2"]
    assert abs(doc2["elements"][4]["span_length_m"] - 4.0) < 0.01
    assert doc2["elements"][4]["span_source"] == "cv_measured"

    # **กฎเหล็ก: ห้ามเอาออก** — ทุก element เดิมต้องยังอยู่ และทุกค่าที่เคยมีต้องไม่เปลี่ยน
    assert len(doc2["elements"]) == len(before["elements"]) + 2, "element เดิมหายไป!"
    for i, old in enumerate(before["elements"]):
        new = doc2["elements"][i]
        for k, v in old.items():
            if v not in (None, [], ""):        # ค่าที่ "มีจริง" ห้ามถูกทับ
                assert new[k] == v, f"ค่าเดิมถูกทับ: {old.get('element_id')}.{k} {v} -> {new[k]}"
    # element ที่ CV เพิ่มให้ ต้องไม่แต่งชื่อมาร์คขึ้นเอง
    for el in doc2["elements"][len(before["elements"]):]:
        assert el["element_id"] is None, "ห้ามแต่ง element_id — เรารู้แค่ตำแหน่ง"
        assert "element_added_by_cv_pass3" in el["confidence_flags"]

    # เรียกซ้ำต้องไม่เติมซ้ำ (idempotent) — ของเดิมเต็มแล้วก็ไม่มีอะไรให้เติม
    rep3 = measure_page(doc2, grid, {"elements": [], "self_harvest_points": []})
    again = merge_into_pass2(doc2, rep3, grid)
    assert again["grid_refs"] == 0 and again["span"] == 0 and again["elements"] == 0, again

    # กริดพัง (pos_m เป็น null ทุกเส้น) → ปฏิเสธ ไม่ crash
    dead = {"x_lines": [{"id": "1", "pos_m": None}], "y_lines": [{"id": "A", "pos_m": None}]}
    d2 = {"elements": [dict(e) for e in doc["elements"]]}
    assert measure_page(d2, dead)["ok"] is False
    assert any("pass3 วัดระยะไม่ได้" in w for w in d2["warnings"])

    print("OK — pass3_measure self-check ผ่านทุกข้อ")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--demo":
        print(json.dumps(measure_page(json.loads(open(sys.argv[1], encoding="utf-8").read()),
                                      json.loads(open(sys.argv[2], encoding="utf-8").read())),
                         ensure_ascii=False, indent=1))
    else:
        demo()
