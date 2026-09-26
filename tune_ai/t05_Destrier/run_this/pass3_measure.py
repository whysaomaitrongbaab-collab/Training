#!/usr/bin/env python3
"""pass3_measure.py — วัดระยะจริงจากพิกเซล โดยใช้ grid master เป็นไม้บรรทัด · **รายงานอย่างเดียว**

    pass1.5/2.5 (CV) ให้พิกัด pixel ของทุกจุดที่ตรวจเจอ
    pass2 (โมเดล)   ให้ grid_ref ของ element ที่มันอ่านออก
    grid master     ให้ pos_m ของทุกเส้นกริด (เมตรจริง)
    ─────────────────────────────────────────────────────────
    pass3 (ไฟล์นี้) เอา 3 อย่างนั้นมาต่อกัน → px ต่อเมตร → รายงานลง pass3_measure.json

⚠️ ตัดสินแล้ว 2026-09-26 (D3): pass3 **ไม่แก้ doc ของ pass2 เลย** — ไม่เติม grid_ref / span /
element ใหม่ / cv_measure / warnings (ตัวเติมเดิม merge_into_pass2 ถูกถอดออก) เพราะวัดจริงแล้ว
0/9 หน้า production วัดได้ ของที่เติมถูกเว็บทิ้งเกือบหมด และที่รอดคือ ref ที่ผิด (กระจก/เลขลำดับ)
ทุกอย่างที่วัดได้อยู่ใน report เท่านั้น ข้อความถึงคนไปที่ warnings ระดับงาน (summary_warnings)

วิธี (ไม่ต้องเทรน ไม่ต้อง detect เส้นกริดในภาพ):
  1. หา "หมุด" = คู่ (pixel, เมตร) ที่รู้ทั้งสองฝั่ง
       ทาง 1 cv_mark ที่โมเดล echo กลับ (ผ่านการตรวจแล้ว: ไม่ใช่เลขลำดับ 1..N, ชนิดกล่องตรงชนิด element)
       ทาง 2 จับคู่ด้วยรูปทรงการกระจายตัว ต่อคลาส (ฐานราก/เสา) — ลอง 4 ทิศแกน (D4)
  2. fit เส้นตรง 2 แกนแยกกัน  px = ax*mx + bx  ·  py = ay*my + by  (เครื่องหมาย a = ทิศแกน)
  3. ผ่านด่าน residual + isotropy → ใช้ได้ · ทิศแกนมากกว่าหนึ่งแบบผ่าน → "ทิศแกนกำกวม" ปฏิเสธ

กติกา "ไม่เดา": หมุดไม่พอ / residual เกิน / scale สองแกนไม่เท่ากัน / ทิศกำกวม → ok=False พร้อม
reason (ไทย) + reason_code · ถูกต้องสำคัญกว่าวัดได้เยอะ (ปฏิเสธเกินได้ ยอมรับผิดไม่ได้)

สัญญา grid ref ร่วมกับ js/drawing/raw-extraction-adapter.js อยู่ที่ tests/fixtures/grid-ref-vectors.json
(test_pass3.py โหลดไฟล์นั้นตรงๆ — สองฝั่งห้ามแยกทางกันอีก)

self-check:  python pass3_measure.py    ·   tests: python test_pass3.py
"""
import json
import math
import re
import sys

# ── เกณฑ์ตัดสิน (ตัวเลขเดียว เปลี่ยนที่นี่ที่เดียว) ──────────────────────────────
MIN_ANCHORS = 3          # 2 พอ fit ได้ แต่ 2 = residual 0 เสมอ วัดคุณภาพไม่ได้เลย
SNAP_TOL_M = 0.50        # ไกลกว่านี้จากจุดตัดกริด = ไม่ใช่จุดนั้น ไม่ snap ให้
MAX_RESIDUAL_M = 0.50    # หมุดเบี้ยวเกินนี้ = การ fit ใช้ไม่ได้ ปฏิเสธทั้งแผ่น
MAX_ANISOTROPY = 0.05    # px/m สองแกนต่างกันเกิน 5% = ไม่ใช่ orthographic (หรือ grid master ผิด)
# สัดส่วนกว้าง/สูงของกลุ่มจุด CV ในคลาสหนึ่ง เทียบกลุ่มจุดที่โมเดลตอบของคลาสเดียวกัน — px/m สองแกน
# เท่ากัน สองกลุ่มจึงต้องสัดส่วนเดียวกัน ต่างเกินนี้ = CV เห็นแค่บางส่วน (เช่น 267d1989: ฐานราก 2 ตัว
# แถวเดียว สูงต่างกัน 2 px ถูกยืดเป็น [0,1] แล้วลากทั้งหน้าพัง) → ข้ามคลาสนั้น ไม่เอามาปน
# ค่า 1.5 = ค่าที่ทีมตรวจทดสอบแล้ว 0 wrong accept บน 15 หน้าที่ดูด้วยตา (real_replay p3_aspect)
MAX_CLASS_ASPECT = 1.5
# ทิศแกนต้อง "ข้อมูลบอก" ไม่ใช่ "noise ตัดสิน": ตัวแปลงที่เลือกต้องอธิบายจุด CV ได้มากกว่าการอ่าน
# กลับด้านทุกแบบอย่างน้อยเท่านี้จุด — ไม่งั้นถือว่าทิศแกนกำกวม · วัดด้วย geometry fuzz (mixture
# 2×20000 หน้า, fix_worker/analyze_mirror.py): ไม่มีด่านนี้ ยอมรับผิด 449/6148 หน้า (7.3%) เพราะ
# noise ล้มคำตอบจริง แล้วกระจกผ่านอยู่ตัวเดียว · ด่าน ≥3 เหลือ 12/4907 (0.24%) ผังสะอาดไม่เสียเลย
# 3 = MIN_ANCHORS: ทิศที่เลือกต้องมีจุดสนับสนุนเกินกระจกอย่างน้อยเท่าหมุดขั้นต่ำ
MIN_ORIENTATION_MARGIN = 3
# ตัวแปลงที่เลือกต้องวางจุด CV (ฐานราก/เสา) อย่างน้อยครึ่งหนึ่งลงบน ref ที่ตอบไว้ — ตัวแปลงที่ถูกอธิบายได้
# ทุกจุดยกเว้น FP/ของที่ไม่ได้ตอบ (ความแม่นของ CV จริง 99%) · กันกรณี FP ไกลๆ ยืดกรอบแล้วได้ px/m ผิด
# 2-3 เท่า (residual หน่วยเมตรดูเล็กเพราะหารด้วย px/m ที่ใหญ่ผิด) · วัดแล้ว ตัดที่ยอมรับผิด 15 → 9 จาก
# 5378 หน้าที่ยอมรับ เสียหน้าที่ถูกแค่ 0.1% (fix_worker/analyze_explained.py)
MIN_EXPLAINED_SHARE = 0.5
# ด่านความแม่น "ทั้งผัง" (ไม่ใช่แค่ที่หมุด): residual วัดได้แค่ตรงหมุด — หมุด 3 ตัว/กระจุกมุมเดียว ผ่าน
# residual ได้ทั้งที่ตัวแปลงเพี้ยนเกินครึ่งเมตรที่ขอบผัง (fuzz รอบตรวจ: 65/1121 ของทาง cv_mark ผิดแบบนี้
# ทุกตัวหมุดถูกหมด) · ประมาณความคลาดที่เส้นกริดไกลสุดด้วยสูตรช่วงทำนายของ least squares
# (t × σ × √(1/n + (u−ū)²/Sxx)) σ จาก residual รวมสองแกน แต่ไม่ต่ำกว่า SIGMA_FLOOR_M (CV จริงคลาด ~3 px
# ≈ 0.05 ม. — residual ของหมุดน้อยตัวต่ำเพราะบังเอิญได้) · เกิน MAX_EDGE_ERROR_M = ปฏิเสธ
SIGMA_FLOOR_M = 0.05
MAX_EDGE_ERROR_M = SNAP_TOL_M
# ตัวแปลงอื่นที่ "ต่าง" จากตัวที่เลือกจริง = ชี้เส้นกริดบางเส้นห่างกันเกินนี้ (ใกล้กว่านี้คือ noise ของตัวเดียวกัน)
DISTINCT_TRANSFORM_M = 2 * SNAP_TOL_M

# ── grid ref grammar (ต้องตรงกับ grid-ref-vectors.json ทุกเคส) ────────────────────
# ref = จุด = ส่วนตัวอักษร (แถว) + ส่วนตัวเลข (คอลัมน์) สลับลำดับได้ มี/ไม่มีขีดก็ได้ ·
# ส่วนตัวอักษรคือแถวเสมอ ตัดสินจากชนิดตัวอักษร ไม่ใช่ตำแหน่ง (spec §0.8) · เลขเฉพาะ ASCII 0-9
_LET = r"[A-Za-zก-ฮ]{1,3}'*"
_DIG = r"[0-9]+'*"
_DASH = r"(?:\s*-\s*)?"
_REF = re.compile(rf"^(?:(?P<l1>{_LET}){_DASH}(?P<d1>{_DIG})|(?P<d2>{_DIG}){_DASH}(?P<l2>{_LET}))$")
_IS_LET = re.compile(rf"^{_LET}$")
_IS_DIG = re.compile(rf"^{_DIG}$")


def _norm_ref(s):
    """prime แบบพิมพ์ (′) → ' · double prime (″ หรือ ") → '' · ตัดช่องว่างหัวท้าย"""
    return s.strip().replace("″", "''").replace('"', "''").replace("′", "'")


def parse_grid_ref(ref):
    """"D1" / "1D" / "D-1" / "1-D" → {"row": "D", "col": "1"} · None ถ้าไม่ใช่ "จุด" ที่ระบุได้แน่นอน
    (ว่าง / ขึ้นต้น "~" = โดยประมาณ / ขีดระหว่างอักษรกับอักษรหรือเลขกับเลข = ช่วง ไม่ใช่จุด)"""
    if not isinstance(ref, str):
        return None
    s = _norm_ref(ref)
    if not s or s.startswith("~"):
        return None
    m = _REF.match(s)
    if not m:
        return None
    return {"row": m.group("l1") or m.group("l2"), "col": m.group("d1") or m.group("d2")}


def _id_kind(i):
    return "L" if _IS_LET.match(i) else "D" if _IS_DIG.match(i) else None


def _lines(grid, axis):
    lines = grid.get("x_lines" if axis == "x" else "y_lines") if isinstance(grid, dict) else None
    # gridline ตอบ x_lines เป็นเลข/true ได้ (โมเดลตอบผิดรูป) — ไม่ใช่ list = ไม่มีเส้น ห้าม crash
    return [ln for ln in lines if isinstance(ln, dict)] if isinstance(lines, list) else []


def _line_id(ln):
    """id ของเส้น ผ่าน prime-normalise ตัวเดียวกับ ref (เส้นชื่อ '1"' ต้องเจอด้วย ref "A1''")"""
    i = ln.get("id")
    if isinstance(i, bool) or not isinstance(i, (str, int)):
        return None
    i = _norm_ref(str(i))
    return i or None


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _grid_index(grid):
    """{axis: {id: [pos_m, ...]}} — เก็บทุกเส้นรวมเส้นชื่อซ้ำ (ให้ตัวเรียกรู้ว่ากำกวม)"""
    idx = {"x": {}, "y": {}}
    for axis in ("x", "y"):
        for ln in _lines(grid, axis):
            i = _line_id(ln)
            if i is not None:
                idx[axis].setdefault(i, []).append(ln.get("pos_m"))
    return idx


def _unique_pos(idx, axis, line_id):
    """เมตรของเส้นนั้น — None ถ้าไม่รู้จัก / pos_m ไม่ใช่ตัวเลข / ชื่อซ้ำหลายเส้นคนละตำแหน่ง (ห้ามเดาเส้นแรก)
    ชื่อซ้ำที่ตำแหน่งเดียวกัน = เส้นเดียวกันเขียนซ้ำ ไม่กำกวม (ตรงกับฝั่งเว็บ)"""
    ps = {float(p) if _num(p) else None for p in idx[axis].get(line_id) or []}
    return ps.pop() if len(ps) == 1 and None not in ps else None


def ref_to_metre(grid, ref):
    """grid ref → (mx, my) เมตร · ค้นแต่ละส่วนในแกนที่มี id นั้นจริง (ไม่ผูกตายว่าเลข=x อักษร=y)
    None เมื่อ: ส่วนใดอยู่ 0 หรือ 2 แกน / สองส่วนตกแกนเดียวกัน / ref ทั้งคำเป็นชื่อเส้นเอง (เส้น
    dummy เช่น "3A" = ชื่อเส้น ไม่ใช่จุด) / เส้นไม่รู้ตำแหน่งหรือชื่อซ้ำ — ไม่เดาทุกกรณี"""
    g = parse_grid_ref(ref)
    if not g:
        return None
    idx = _grid_index(grid)
    literal = _norm_ref(ref)
    if literal in idx["x"] or literal in idx["y"]:
        return None
    axis_of = {}
    for part in (g["row"], g["col"]):
        axes = [a for a in ("x", "y") if part in idx[a]]
        if len(axes) != 1:
            return None
        axis_of[part] = axes[0]
    if axis_of[g["row"]] == axis_of[g["col"]]:
        return None
    x_part = g["row"] if axis_of[g["row"]] == "x" else g["col"]
    y_part = g["col"] if x_part == g["row"] else g["row"]
    mx, my = _unique_pos(idx, "x", x_part), _unique_pos(idx, "y", y_part)
    return None if mx is None or my is None else (mx, my)


def nearest_grid_ref(grid, mx, my, tol_m=SNAP_TOL_M):
    """จุดเมตร → grid ref ที่ใกล้สุด · คืน (ref, ระยะห่าง) หรือ (None, ระยะ) ถ้าไกลเกิน tol
    ref ที่ออกไปต้องแปลงกลับ (ref_to_metre) มาจุดเดิมเป๊ะเท่านั้น — ชื่อเส้นซ้ำ / id อยู่สองแกน /
    สองแกนเป็นชนิดเดียวกัน → None ไม่ปล่อย ref กำกวมออกไปเด็ดขาด"""
    near = {}
    for axis, v in (("x", mx), ("y", my)):
        cands = [(_line_id(ln), float(ln["pos_m"])) for ln in _lines(grid, axis)
                 if _line_id(ln) is not None and _num(ln.get("pos_m"))]
        if not cands:
            return None, None
        near[axis] = min(cands, key=lambda c: abs(c[1] - v))
    d = round(math.hypot(near["x"][1] - mx, near["y"][1] - my), 3)
    if d > tol_m:
        return None, d
    parts = {_id_kind(near["x"][0]): near["x"][0], _id_kind(near["y"][0]): near["y"][0]}
    if set(parts) != {"L", "D"}:
        return None, d
    ref = parts["L"] + parts["D"]
    return (ref if ref_to_metre(grid, ref) == (near["x"][1], near["y"][1]) else None), d


def rect_center(box):
    """จุดศูนย์กลางจากมุมไปมุมของสี่เหลี่ยม — รับได้ทั้งแบบ {cx,cy} (cv_scan ให้มาแล้ว)
    และแบบ {x,y,w,h} (มุมซ้ายบน+ขนาด) · คืน (px, py) หรือ None ถ้าอ่านไม่ได้"""
    if not isinstance(box, dict):
        return None
    if _num(box.get("cx")) and _num(box.get("cy")):
        return (float(box["cx"]), float(box["cy"]))
    x, y, w, h = (box.get(k) for k in ("x", "y", "w", "h"))
    if all(_num(v) for v in (x, y, w, h)):
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


def _fit(anchors, grid):
    """หมุด [(px, py, ref)] → {"ok","reason","reason_code","transform","fit","scale","n"}
    fit = ตัวเลขที่ fit ได้แม้ไม่ผ่านด่าน (ไว้รายงานเป็นหลักฐาน) · transform = เฉพาะตอนผ่านด่าน"""
    pts = []
    for px, py, ref in anchors:
        m = ref_to_metre(grid, ref)
        if m is not None:
            pts.append((px, py, m[0], m[1]))
    out = {"ok": False, "reason": None, "reason_code": None, "transform": None, "fit": None,
           "scale": None, "n": len(pts)}

    def fail(code, why):
        out.update(reason_code=code, reason=why)
        return out

    if len(pts) < MIN_ANCHORS:
        return fail("too_few_anchors", f"หมุดไม่พอ: ได้ {len(pts)} ต้องการอย่างน้อย {MIN_ANCHORS} "
                                       f"(element ที่มีทั้ง grid_ref ที่รู้ pos_m และพิกัด CV)")
    fx = _fit_line([(mx, px) for px, _, mx, _ in pts])
    fy = _fit_line([(my, py) for _, py, _, my in pts])
    if fx is None or fy is None:
        return fail("collinear", "หมุดเรียงอยู่บนกริดเส้นเดียว (แกนใดแกนหนึ่งไม่กระจาย) — fit ไม่ได้")
    ax, bx = fx
    ay, by = fy
    if abs(ax) < 1e-9 or abs(ay) < 1e-9:
        return fail("zero_scale", "scale ออกมาเป็นศูนย์ — ข้อมูลหมุดผิดปกติ")

    # residual วัดเป็น "เมตร" ไม่ใช่พิกเซล — คนอ่านเข้าใจทันทีว่าเบี้ยวแค่ไหนบนของจริง
    errs = [max(abs((px - (ax * mx + bx)) / ax), abs((py - (ay * my + by)) / ay))
            for px, py, mx, my in pts]
    residual_max = max(errs)
    rms = (sum(e * e for e in errs) / len(errs)) ** 0.5
    pxm_x, pxm_y = abs(ax), abs(ay)
    out["fit"] = {"ax": ax, "bx": bx, "ay": ay, "by": by,
                  "px_per_m_x": round(pxm_x, 2), "px_per_m_y": round(pxm_y, 2),
                  "residual_max_m": round(residual_max, 3), "rms_m": round(rms, 3),
                  "n_anchors": len(pts)}
    if residual_max > MAX_RESIDUAL_M:
        return fail("residual", f"หมุดเบี้ยวเกินเกณฑ์: คลาดสูงสุด {residual_max:.2f} ม. "
                                f"(เกิน {MAX_RESIDUAL_M} ม.) — grid_ref บางตัวน่าจะผิด ไม่ใช้ผลนี้")
    aniso = abs(pxm_x - pxm_y) / ((pxm_x + pxm_y) / 2)
    if aniso > MAX_ANISOTROPY:
        # ไม่มีขั้นไหนในท่อ resize ภาพ (วัดแล้ว real anisotropy 0.1–2.8%) — อัตราส่วนใกล้จำนวนเต็ม
        # พอดี (เช่น 2.00 ของ 83b8e52c ที่อ่าน x เป็น 0/6/12 แทน 0/3/6) = grid master อ่านระยะผิด
        # แกนที่ px/m ต่ำกว่า = pos_m ใหญ่เกินจริง (ทางที่เจอจริง) · อาจเป็นอีกแกนก็ได้ ข้อความบอกตรงๆ
        ratio = max(pxm_x, pxm_y) / min(pxm_x, pxm_y)
        k = round(ratio)
        if k >= 2 and abs(ratio / k - 1) <= MAX_ANISOTROPY:
            axis = "x" if pxm_x < pxm_y else "y"
            out["scale"] = {"ratio": round(ratio, 3), "suspect_axis": axis, "k": k}
            return fail("grid_scale_suspect",
                        f"grid master แกน {axis} น่าจะผิด (อัตราส่วน {ratio:.2f}) — px ต่อเมตรแกน x "
                        f"{pxm_x:.1f} vs แกน y {pxm_y:.1f} ต่างกันเกือบ {k} เท่าพอดี ซึ่งภาพไม่ได้ถูกยืด "
                        f"ระยะ pos_m แกน {axis} น่าจะอ่านมาผิด (หรืออีกแกนผิดในทางกลับกัน) ไม่ใช้ผลนี้")
        return fail("anisotropy", f"px ต่อเมตรสองแกนไม่เท่ากัน ({pxm_x:.1f} vs {pxm_y:.1f}, ต่าง "
                                  f"{aniso * 100:.1f}%) — ภาพน่าจะยืด/หมุน ไม่ใช่ orthographic ไม่ใช้ผลนี้")
    edge = _edge_error_m(pts, ax, bx, ay, by, grid)
    out["fit"]["edge_error_m"] = round(edge, 3)
    if edge > MAX_EDGE_ERROR_M:
        return fail("underdetermined", f"หมุดน้อยหรือกระจุกเกินไปสำหรับทั้งผัง ({len(pts)} ตัว): ตรงหมุดเบี้ยวแค่ "
                                       f"{residual_max:.2f} ม. แต่ที่เส้นกริดไกลสุดอาจคลาดได้ถึง ~{edge:.2f} ม. "
                                       f"(เกิน {MAX_EDGE_ERROR_M} ม.) — ไม่ใช้ผลนี้")
    out.update(ok=True, transform=dict(out["fit"]))
    return out


# t-quantile 97.5% (สองข้าง 95%) ตาม dof — ตารางมาตรฐาน · ไม่มีในตาราง = ใช้แถวที่ dof ต่ำกว่าถัดไป (เข้มกว่า)
_T975 = ((1, 12.71), (2, 4.30), (3, 3.18), (4, 2.78), (5, 2.57), (6, 2.45), (7, 2.36), (8, 2.31),
         (9, 2.26), (10, 2.23), (12, 2.18), (15, 2.13), (20, 2.09), (30, 2.04), (60, 2.00))


def _t975(dof):
    return next((t for d, t in reversed(_T975) if dof >= d), _T975[0][1])


def _edge_error_m(pts, ax, bx, ay, by, grid):
    """ความคลาด (เมตร) ที่คาดได้ ณ เส้นกริดที่ไกลจากหมุดที่สุด — ช่วงทำนาย 95% ของ least squares
    ต่อแกน แล้วรวมสองแกนเป็นระยะทแยง · σ = residual รวมสองแกน (dof 2n−4) ไม่ต่ำกว่า SIGMA_FLOOR_M"""
    n = len(pts)
    ssr = sum(((px - (ax * mx + bx)) / ax) ** 2 + ((py - (ay * my + by)) / ay) ** 2 for px, py, mx, my in pts)
    dof = 2 * n - 4
    sigma = max((ssr / dof) ** 0.5 if dof > 0 else float("inf"), SIGMA_FLOOR_M)
    t = _t975(max(dof, 1))
    per_axis = []
    for k, axis in ((2, "x"), (3, "y")):
        us = [p[k] for p in pts]
        mean = sum(us) / n
        sxx = sum((u - mean) ** 2 for u in us)
        far = max((g - mean) ** 2 for g in _grid_positions(grid, axis) + us)
        per_axis.append(t * sigma * (1.0 / n + far / sxx) ** 0.5)
    return math.hypot(*per_axis)


def build_transform(anchors, grid):
    """หมุด [(px, py, ref)] + grid master → (transform, None, None) เมื่อใช้ได้ ·
    (None, "เหตุผลไทย", reason_code) เมื่อใช้ไม่ได้
    transform: ax,bx,ay,by (px = a*m + b), px_per_m_x/y, residual_max_m, rms_m, n_anchors"""
    f = _fit(anchors, grid)
    return (f["transform"], None, None) if f["ok"] else (None, f["reason"], f["reason_code"])


def pixel_to_metre(t, px, py):
    """pixel → เมตรบนระบบพิกัดของ grid master"""
    return ((px - t["bx"]) / t["ax"], (py - t["by"]) / t["ay"])


def metre_distance(t, p1, p2):
    """ระยะจริงเป็นเมตรระหว่างสองจุด pixel (เช่น คานสู่คาน / เสาสู่เสา)"""
    (x1, y1), (x2, y2) = pixel_to_metre(t, *p1), pixel_to_metre(t, *p2)
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


ORIENT_TH = {"identity": "ปกติ", "flipped_x": "แกน x กลับด้าน", "flipped_y": "แกน y กลับด้าน",
             "flipped_both": "กลับทั้งสองแกน"}
FLIPPED_AXES = {"flipped_x": ("x",), "flipped_y": ("y",), "flipped_both": ("x", "y")}


def orientation_of(t):
    """ทิศแกนจากเครื่องหมาย slope: + = pos_m โตไปทางขวา/ลงล่าง (origin ซ้ายบนตาม prompt gridline)"""
    return {(False, False): "identity", (True, False): "flipped_x",
            (False, True): "flipped_y", (True, True): "flipped_both"}[(t["ax"] < 0, t["ay"] < 0)]


# ── cv_mark: เชื่อได้เมื่อไหร่ (ใช้ร่วมกับ worker.merge_cv_marks) ──────────────────────
# ชนิด element → คลาสกล่อง CV ที่เข้ากันได้ · ฐานราก↔เสาข้ามกันได้เพราะแบบไทยวางเสากลางฐานราก
# (ทีมตรวจวัด: ศูนย์กลางตรงกันภายใน 3 px บน 5/9 หน้า) · ชนิดอื่น (detail_view, dimension_chain ...)
# ไม่มีกล่อง CV ที่ถูกต้องเลย → cv_mark ของมันไม่ถูกผูกพิกัด
_POINT = ("footing", "column")
_BEAM = ("beam_h", "beam_v")
CV_CLASSES_FOR_TYPE = {"footing": _POINT, "column": _POINT, "pile_cap": _POINT, "pedestal": _POINT,
                       "beam": _BEAM, "girder": _BEAM, "tie_beam": _BEAM}


def cv_class_fits(element_type, cv_class):
    # rev_worker major: element_type/cv_class ที่ไม่ hashable (list/dict — generation หลุดกลางคัน)
    # ทำให้ .get()/`in` โยน TypeError กลาง pass2 loop ที่ไม่มี try — ต้องเป็น str เท่านั้นถึงเชื่อ
    if not isinstance(element_type, str) or not isinstance(cv_class, str):
        return False
    return cv_class in CV_CLASSES_FOR_TYPE.get(element_type, ())


def _mark(el):
    v = el.get("cv_mark") if isinstance(el, dict) else None
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def marks_look_enumerated(elements):
    """cv_mark ที่เป็นแค่ "เลขลำดับรายการ" ไม่ใช่เลขกล่อง CV — เจอ 5/5 หน้าจริงใน production
    (hint บอกว่ามีเลขบนภาพ แต่ภาพที่ส่งไม่มีเลข โมเดลเลยนับ 1..N ตามที่ตอบ)
    True เมื่อมี mark ≥ 2 ตัว และ (ทุกตัว = ลำดับรายการ+1) หรือ (อ่านตามลำดับแล้วได้ 1,2,…,k)
    mark ตัวเดียวบอกไม่ได้ → False (ตัวเดียว fit ไม่ได้อยู่แล้ว)"""
    marked = [(i, _mark(el)) for i, el in enumerate(elements or []) if _mark(el) is not None]
    if len(marked) < 2:
        return False
    marks = [m for _, m in marked]
    return all(m == i + 1 for i, m in marked) or marks == list(range(1, len(marks) + 1))


def _element_refs(el):
    """ref ทั้งหมดของ element นี้ — จุด (grid_refs[]) และเส้น (start/end)"""
    gr = el.get("grid_refs")
    refs = [r for r in gr if isinstance(r, str)] if isinstance(gr, list) else []
    for k in ("grid_ref_start", "grid_ref_end"):
        if isinstance(el.get(k), str):
            refs.append(el[k])
    return refs


def _flags(el):
    fl = el.get("confidence_flags") if isinstance(el, dict) else None
    return fl if isinstance(fl, list) else []


def _trusted_cv_positions(elements):
    """[(index, cv_position)] ที่เชื่อได้: หน้าไม่ได้ตอบ cv_mark แบบเลขลำดับ + ชนิดกล่องตรงชนิด element
    + element มี cv_mark จริง (ไม่ใช่แค่มี cv_position ค้างอยู่) + ไม่ได้ติดธงว่าผูกด้วยการจับคู่รูปทรง
    (rev_worker minor: doc จาก checkpoint pass3 รุ่นเก่าผูก cv_position ไว้แล้วจากทางรูปทรง (D4 —
    อาจเป็นกระจก) โดยไม่มี cv_mark คุมเลย resume แล้วห้ามเชื่อพิกัดนั้นเป็นหมุดซ้ำอีกรอบ — กันไว้ที่นี่
    ด้วย ไม่พึ่ง merge_cv_marks อย่างเดียว)"""
    if marks_look_enumerated(elements):
        return []
    return [(i, el["cv_position"]) for i, el in enumerate(elements or [])
            if isinstance(el, dict) and isinstance(el.get("cv_position"), dict)
            and _mark(el) is not None
            and "cv_matched_by_shape" not in _flags(el)
            and cv_class_fits(el.get("element_type"), el["cv_position"].get("class"))]


def collect_anchors(elements):
    """ทาง 1: element ที่มี cv_position ที่เชื่อได้ + ref จุดเดียวชัดเจน = หมุด → [(px, py, ref, index)]

    ตัดคานออกเสมอ แม้จะมี ref เดียว — ฐานราก/เสา "นั่งบนจุดตัดกริดพอดี" จุดกึ่งกลางไอคอน
    จึงเป็นตำแหน่งของ ref จริง แต่คานพาดจากจุดหนึ่งไปอีกจุด **จุดกึ่งกลางกล่องคานไม่ได้อยู่ที่
    ref ใดเลย** เอามาเป็นหมุดเมื่อไหร่ = ป้อนพิกัดผิดเข้าไปใน fit ทั้งแผ่นพัง"""
    out = []
    for i, cv in _trusted_cv_positions(elements):
        if cv.get("class") not in _POINT:
            continue
        c = rect_center(cv)
        refs = _element_refs(elements[i])
        if c and len(refs) == 1:
            out.append((c[0], c[1], refs[0], i))
    return out


# ── ทาง 2: จับคู่ด้วยรูปทรง + ทดลองทิศแกน 4 แบบ (D4) ──────────────────────────────────
POINT_CLASSES = _POINT
HYPOTHESES = (("identity", 1, 1), ("flipped_x", -1, 1), ("flipped_y", 1, -1), ("flipped_both", -1, -1))


def _normalize(pts):
    """ย่อชุดจุดลงกรอบ [0,1] ของตัวเอง — เทียบรูปทรงการกระจายตัวข้ามหน่วย (เมตร vs พิกเซล)
    คืน None ถ้าจุดทั้งหมดกองอยู่ที่เดียว (กรอบกว้าง 0 หารไม่ได้)"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if w <= 0 or h <= 0:
        return None
    return [((x - min(xs)) / w, (y - min(ys)) / h) for x, y in pts]


def _aspect(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    return w / h if w > 0 and h > 0 else None


def _mutual_nearest(a, b):
    """คู่ที่ "ต่างฝ่ายต่างเห็นกันเป็นเพื่อนบ้านใกล้สุด" เท่านั้น → [(i, j)]
    จำนวนสองฝั่งไม่เท่ากันเป็นเรื่องปกติ (CV จับไม่ครบ / โมเดลตอบเกิน) mutual ตัดตัวที่ไม่มีคู่จริงทิ้งเอง"""
    d = lambda p, q: (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
    best_a = [min(range(len(b)), key=lambda j: d(a[i], b[j])) for i in range(len(a))]
    best_b = [min(range(len(a)), key=lambda i: d(a[i], b[j])) for j in range(len(b))]
    return [(i, j) for i, j in enumerate(best_a) if best_b[j] == i]


def _extent(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


def _class_sets(elements, cv_scan, grid):
    """ต่อคลาส (ฐานราก/เสา): จุดที่โมเดลตอบ (ไม่ซ้ำตำแหน่ง) + จุดที่ CV เห็น · ผ่านด่านสัดส่วนก่อน
    คืน ([(cls, model, cv)], skipped) — model = [{"m": (mx,my), "ref", "ids": [index element]}]
    skipped[i] อาจมี "scale_suspect": {axis, ratio, k} เมื่อสัดส่วนที่ต่างกันเป็นจำนวนเต็มพอดี — สัญญาณว่า
    grid master แกนนั้นน่าจะอ่านผิด ไม่ใช่แค่คนละมุมมอง (rev_worker major: เดิมด่านนี้ตัดคลาสทิ้งเงียบๆ
    ก่อนถึง _fit เลย ทำให้ scale_check ไม่มีวันขึ้น 'suspect' บนทางรูปทรง — ทางเดียวที่รอดคือ cv_mark
    ซึ่ง production แทบไม่เชื่อ (เลขลำดับ) จึงไม่เคยแจ้งเตือน 83b8e52c ทั้งที่แกน x ยาวผิด 2 เท่าจริง)"""
    sets, skipped = [], []
    for cls in POINT_CLASSES:
        cv = [e for e in cv_scan.get("elements") or []
              if isinstance(e, dict) and e.get("class") == cls and _num(e.get("cx")) and _num(e.get("cy"))]
        model, seen = [], {}
        for i, el in enumerate(elements or []):
            if not isinstance(el, dict) or el.get("element_type") != cls:
                continue
            gr = el.get("grid_refs")
            # ⚠️ 1 record แทนของหลายชิ้นได้ (count>1, grid_refs = อาร์เรย์ของจุด) — ใช้ทุกจุด
            refs = [r for r in gr if isinstance(r, str)] if isinstance(gr, list) else []
            if not refs and isinstance(el.get("grid_ref_start"), str):
                refs = [el["grid_ref_start"]]      # จุดเดี่ยวที่เขียนเป็น start
            for r in refs:
                m = ref_to_metre(grid, r)
                if m is None:
                    continue
                key = (round(m[0], 6), round(m[1], 6))
                if key in seen:
                    seen[key]["ids"].append(i)
                    continue
                seen[key] = {"m": m, "ref": r, "ids": [i]}
                model.append(seen[key])
        if len(cv) < 2 or len(model) < 2:
            continue
        am, ac = _aspect([p["m"] for p in model]), _aspect([(e["cx"], e["cy"]) for e in cv])
        factor = max(am / ac, ac / am) if am and ac else None
        if factor is None or factor > MAX_CLASS_ASPECT:
            entry = {"class": cls, "aspect_factor": None if factor is None else round(factor, 2),
                     "n_cv": len(cv), "n_model": len(model)}
            # เดียวกับด่าน anisotropy ใน _fit: สัดส่วนที่ต่างเกือบจำนวนเต็ม k≥2 พอดี = แกนหนึ่งยาวผิด
            # เป็นทวีคูณ ไม่ใช่แค่มุมมอง/สัดส่วนภาพต่าง — mw/cw (เมตรโมเดลต่อ px CV) แกนไหนมากกว่า
            # คือแกนที่ pos_m ใหญ่เกินจริง (สอดคล้องข้อความ "แกน{axis}น่าจะผิด" ของ _fit)
            mw, mh = _extent([p["m"] for p in model])
            cw, ch = _extent([(e["cx"], e["cy"]) for e in cv])
            # ต้องมีจุดพอ (≥4) และจำนวนสองฝั่งใกล้เคียงกัน (≥80% ของฝั่งที่มากกว่า) ก่อนเชื่อ extent
            # ratio นี้เป็นสัญญาณสเกล — extent จากจุดจำนวนต่างกันมาก (CV เห็นเยอะกว่าโมเดลตอบเยอะ)
            # ผันผวนได้จากตัวที่หายไป ไม่ใช่จากสเกลจริง (fuzz จับได้จริง: n_cv 10 vs n_model 6 ให้
            # ratio ปลอมใกล้ 3 เท่าพอดี บนกริดที่ถูกอยู่แล้ว — no_false_scale_suspect_on_noisy_pages)
            n_lo, n_hi = min(len(cv), len(model)), max(len(cv), len(model))
            if mw > 0 and mh > 0 and cw > 0 and ch > 0 and n_lo >= 4 and n_lo >= 0.8 * n_hi:
                rx, ry = mw / cw, mh / ch
                ratio = max(rx, ry) / min(rx, ry)
                k = round(ratio)
                if k >= 2 and abs(ratio / k - 1) <= MAX_ANISOTROPY:
                    # คีย์เดียวกับ scale dict ของ _fit ("suspect_axis") — รวมกับของทาง cv_mark ได้
                    # ในโค้ดเดียว ไม่ต้องแปลงชื่อฟิลด์ตอนใช้
                    entry["scale_suspect"] = {"suspect_axis": "x" if rx > ry else "y", "ratio": round(ratio, 3), "k": k}
            skipped.append(entry)
            continue
        sets.append((cls, model, cv))
    return sets, skipped


def _shape_pairs(sets, sx, sy):
    """ทิศแกนสมมติ (sx, sy): กลับเครื่องหมายเมตรของโมเดลก่อนย่อ [0,1] → คู่ที่ mutual nearest"""
    pairs = []
    for cls, model, cv in sets:
        na = _normalize([(sx * p["m"][0], sy * p["m"][1]) for p in model])
        nb = _normalize([(e["cx"], e["cy"]) for e in cv])
        if na is None or nb is None:
            continue
        for i, j in _mutual_nearest(na, nb):
            pairs.append({"cls": cls, "ref": model[i]["ref"], "ids": model[i]["ids"], "cv": cv[j]})
    return pairs


def _grid_positions(grid, axis):
    return [float(ln["pos_m"]) for ln in _lines(grid, axis) if _num(ln.get("pos_m"))]


def _same_transform(t1, t2, grid, tol_m=SNAP_TOL_M):
    """สองตัวแปลงชี้ทุกเส้นกริดไปพิกเซลเดียวกัน (ต่างไม่เกิน tol_m) = คำตอบเดียวกัน"""
    for axis, a, b in (("x", "ax", "bx"), ("y", "ay", "by")):
        s = (abs(t1[a]) + abs(t2[a])) / 2
        for m in _grid_positions(grid, axis) or [0.0]:
            if abs((t1[a] * m + t1[b]) - (t2[a] * m + t2[b])) / s > tol_m:
                return False
    return True


def _support_points(elements, cv_scan, grid):
    """(จุดเมตรที่โมเดลตอบของฐานราก/เสา ไม่ซ้ำ, จุดพิกเซลที่ CV เห็นของฐานราก/เสา ไม่ซ้ำ)"""
    model = set()
    for el in elements or []:
        if isinstance(el, dict) and el.get("element_type") in POINT_CLASSES:
            for r in _element_refs(el):
                m = ref_to_metre(grid, r)
                if m:
                    model.add(m)
    boxes = list((cv_scan or {}).get("elements") or [])
    # cv_position ที่เชื่อได้ = สำเนากล่องจากบัญชี pass1.5 — นับเป็นจุดที่ CV เห็นด้วย (doc จาก checkpoint
    # อาจมี cv_position โดยไม่มี cv_scan ของหน้านั้น)
    boxes += [cv for _, cv in _trusted_cv_positions(elements)]
    pts = {(float(e["cx"]), float(e["cy"])) for e in boxes
           if isinstance(e, dict) and e.get("class") in POINT_CLASSES and _num(e.get("cx")) and _num(e.get("cy"))}
    return sorted(model), sorted(pts)


def _hits(model_cells, pts, t):
    """จำนวนจุด CV ที่ตัวแปลง t วางห่างจุดที่โมเดลตอบ ≤ SNAP_TOL_M"""
    n = 0
    for px, py in pts:
        mx, my = pixel_to_metre(t, px, py)
        cx, cy = math.floor(mx / SNAP_TOL_M), math.floor(my / SNAP_TOL_M)
        if any(math.hypot(mx - m[0], my - m[1]) <= SNAP_TOL_M
               for i in (-1, 0, 1) for j in (-1, 0, 1) for m in model_cells.get((cx + i, cy + j), ())):
            n += 1
    return n


def _support(elements, cv_scan, grid, t):
    """(hit, n_cv, margin) — hit = จุด CV (ฐานราก/เสา) ที่ตัวแปลง t อธิบายได้ · margin = hit ลบ จุดที่
    "ตัวแปลงอื่นที่ดีที่สุด" อธิบายได้ — ตัวแปลงอื่น = scale เท่ากัน ทิศแกนใดก็ได้ 4 แบบ และเลื่อนไปวางตรงไหนก็ได้
    ที่ห่างจาก t เกิน DISTINCT_TRANSFORM_M (หาด้วยการโหวต: ทุกคู่ (จุด CV, จุดที่ตอบ) เสนอการเลื่อนหนึ่งค่า)
    ครอบทั้งกระจก (ทิศผิด) และการเลื่อนไปหนึ่งช่องกริด (ผังระยะเท่า) — ทีมตรวจพบว่าตัวแทนแบบเดิม (สะท้อน
    รอบกึ่งกลางกลุ่มจุด) ไม่ใช่ทางเลือกจริง: ref บนเส้น dummy ยืดกรอบ แล้วกระจกผ่านด่านได้"""
    model, pts = _support_points(elements, cv_scan, grid)
    if not model or not pts:
        return 0, len(pts), 0
    cells = {}
    for m in model:
        cells.setdefault((math.floor(m[0] / SNAP_TOL_M), math.floor(m[1] / SNAP_TOL_M)), []).append(m)
    base = _hits(cells, pts, t)
    sxa, sya = abs(t["ax"]), abs(t["ay"])
    alt = 0
    # swap = แผ่นถูกหมุน 90° (เส้นเลขวิ่งแนวตั้ง) — นอกสมมติฐานทิศทั้ง 4 แต่เกิดได้ (fuzz: หน้าหมุนผ่านด่าน
    # แบบไม่หมุนได้บังเอิญ ผิด 19 ม.) · ทดสอบโดยสลับแกนพิกัดจุด CV แล้วใช้กลไกเดียวกัน — เป็นทางเลือกเสมอ
    for swap in (False, True):
        cvp = [(py, px) for px, py in pts] if swap else pts
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            ax, ay = sx * sxa, sy * sya
            votes = {}
            for px, py in cvp:
                for mx, my in model:
                    # การเลื่อน (หน่วยเมตร) ที่ทำให้จุด CV นี้ตกบนจุดที่ตอบนี้พอดี
                    k = (round((px - ax * mx) / sxa / SNAP_TOL_M), round((py - ay * my) / sya / SNAP_TOL_M))
                    votes[k] = votes.get(k, 0) + 1
            near = {k: sum(votes.get((k[0] + i, k[1] + j), 0) for i in (-1, 0, 1) for j in (-1, 0, 1))
                    for k in votes}
            for k in sorted(near, key=lambda k: -near[k])[:8]:
                cand = {"ax": ax, "bx": k[0] * SNAP_TOL_M * sxa, "ay": ay, "by": k[1] * SNAP_TOL_M * sya}
                if near[k] <= alt or (not swap and _same_transform(cand, t, grid, DISTINCT_TRANSFORM_M)):
                    continue
                # ขยับละเอียดรอบเซลล์ (noise แบ่งโหวตข้ามเซลล์) — เอาค่าที่อธิบายได้มากสุด
                best = max(_hits(cells, cvp, dict(cand, bx=cand["bx"] + dx * sxa, by=cand["by"] + dy * sya))
                           for dx in (-0.25, 0, 0.25) for dy in (-0.25, 0, 0.25))
                alt = max(alt, best)
    return base, len(pts), base - alt


def _support_gate(elements, cv_scan, grid, t, res):
    """ด่านหลักฐานจากภาพ (ใช้ทั้งทาง cv_mark และทางรูปทรง) · ผ่าน = None · ไม่ผ่าน = เติม reason ลง res"""
    hit, n_cv, margin = _support(elements, cv_scan, grid, t)
    res["orientation_margin"] = margin
    res["support"] = {"hit": hit, "n_cv": n_cv}
    if not n_cv:
        return ("no_cv", "ไม่มีจุด CV (ฐานราก/เสา) ของหน้านี้ให้ตรวจตัวแปลงเทียบ — ไม่ใช้ผลนี้")
    if hit < MIN_EXPLAINED_SHARE * n_cv:
        return ("weak_support",
                f"ตัวแปลงที่ fit ได้วางจุดที่ CV เห็นลงบน ref ที่ตอบไว้ได้แค่ {hit}/{n_cv} จุด (ต่ำกว่า "
                f"{MIN_EXPLAINED_SHARE:.0%}) — น่าจะจับคู่ผิดหรือ px/m ผิด (เช่น จุด CV นอกผังยืดกรอบ) ไม่ใช้ผลนี้")
    if margin < MIN_ORIENTATION_MARGIN:
        return ("orientation_ambiguous",
                f"ทิศแกน/ตำแหน่งกำกวม: ตัวแปลงที่เลือก ({ORIENT_TH[orientation_of(t)]}) อธิบายจุดที่ CV เห็นได้ "
                f"{hit} จุด แต่มีการอ่านแบบอื่น (กลับด้าน หรือเลื่อนไปช่องกริดอื่น) อธิบายได้แทบเท่ากัน (ต่างกัน "
                f"{margin} จุด ต้องการ ≥ {MIN_ORIENTATION_MARGIN}) — ไม่เดา ไม่ใช้ผลนี้")
    return None


def _shape_match(elements, cv_scan, grid):
    """ลองทั้ง 4 ทิศแกน · ยอมรับเฉพาะเมื่อมีคำตอบเดียวที่ผ่านด่าน (ซ้ำกันเองนับเป็นหนึ่ง) **และ**
    คำตอบนั้นอธิบายจุด CV ได้ดีกว่าการอ่านกลับด้านชัดเจน (MIN_ORIENTATION_MARGIN) — "ผ่านตัวเดียว"
    อย่างเดียวไม่พอ: noise ล้มคำตอบจริงได้ แล้วกระจกผ่านอยู่ตัวเดียว (วัดแล้ว 7.3% ของที่ยอมรับ)
    ห้ามเลือก "residual ต่ำสุด" — ทีมตรวจวัดแล้ว คำตอบกระจกได้ residual ต่ำกว่าคำตอบจริงบน 3/15 หน้า"""
    sets, skipped = _class_sets(elements, cv_scan, grid)
    cands = []
    for name, sx, sy in HYPOTHESES:
        pairs = _shape_pairs(sets, sx, sy)
        cands.append({"orientation": name, "pairs": pairs,
                      "fit": _fit([(p["cv"]["cx"], p["cv"]["cy"], p["ref"]) for p in pairs], grid)})
    distinct = []
    for c in cands:
        if c["fit"]["ok"] and not any(_same_transform(c["fit"]["transform"], d["fit"]["transform"], grid)
                                      for d in distinct):
            distinct.append(c)
    res = {"cands": cands, "skipped": skipped, "chosen": None, "ok": False,
           "reason": None, "reason_code": None, "scale": None}
    if len(distinct) == 1:
        bad = _support_gate(elements, cv_scan, grid, distinct[0]["fit"]["transform"], res)
        if bad:
            res.update(reason_code=bad[0], reason=bad[1])
            return res
        res.update(ok=True, chosen=distinct[0])
        return res
    if len(distinct) > 1:
        names = ", ".join(ORIENT_TH[orientation_of(c["fit"]["transform"])] for c in distinct)
        res.update(reason_code="orientation_ambiguous",
                   reason=f"ทิศแกนกำกวม: จับคู่ได้ {len(distinct)} แบบ ({names}) — ผังสมมาตรหรือจุดที่ CV "
                          f"เห็นไม่พอบอกว่าเส้นกริดเริ่มนับจากฝั่งไหน ไม่เดาทิศ ไม่ใช้ผลนี้")
        return res
    scale = [c["fit"] for c in cands if c["fit"]["reason_code"] == "grid_scale_suspect"]
    if scale and len({(f["scale"]["suspect_axis"], f["scale"]["k"]) for f in scale}) == 1:
        res.update(reason=scale[0]["reason"], reason_code="grid_scale_suspect", scale=scale[0]["scale"])
        return res
    # rev_worker major: ด่านสัดส่วนต่อคลาสใน _class_sets ตัดคลาสทิ้งก่อนถึง _fit เสมอเมื่อแกนยาวผิด
    # เป็นทวีคูณ (k≥2) — เส้นทาง cands ด้านบนจึงไม่มีวันเห็น grid_scale_suspect เลยในกรณีนี้ (ทุก
    # ทิศแกนได้ too_few_anchors จากคลาสที่ถูกข้ามหมด) ต้องเช็ค skipped ด้วยแยกต่างหาก
    class_scale = [s["scale_suspect"] for s in skipped if s.get("scale_suspect")]
    if class_scale and len({(s["suspect_axis"], s["k"]) for s in class_scale}) == 1:
        s = class_scale[0]
        cls_names = ", ".join(sk["class"] for sk in skipped if sk.get("scale_suspect"))
        res.update(reason_code="grid_scale_suspect", scale=s,
                   reason=f"grid master แกน {s['suspect_axis']} น่าจะผิด (อัตราส่วน {s['ratio']:.2f}) — "
                          f"สัดส่วนกว้าง/สูงของจุด CV คลาส {cls_names} ต่างจากตำแหน่งที่โมเดลตอบเกือบ "
                          f"{s['k']} เท่าพอดี ซึ่งไม่ใช่แค่มุมมองต่าง — grid master pos_m แกนนี้น่าจะอ่านมาผิด ไม่ใช้ผลนี้")
        return res
    ident = cands[0]["fit"]
    why = ident["reason"]
    if skipped:
        why += " · ข้ามคลาส " + ", ".join(
            f"{s['class']} (จุดที่ CV เห็นกระจายตัวไม่เข้ากับตำแหน่งที่ตอบ"
            + (f" ต่าง {s['aspect_factor']} เท่า)" if s["aspect_factor"] else ")") for s in skipped)
    res.update(reason=why, reason_code=ident["reason_code"])
    return res


# CV เห็นทุกอย่างบนแผ่นเดียว แต่ pass2 แบ่งงานเป็น subtask — จุด CV-only ที่รายงานต้องเป็นของชนิดที่
# subtask นั้นรับผิดชอบ ไม่งั้นคานบนแผ่นฐานรากถูกรายงานว่า "CV เห็นแต่ไม่มีใครตอบ" ทั้งที่อยู่อีกไฟล์
SUBTASK_CV_CLASSES = {"plan_footing": _POINT, "plan_beam": _BEAM, "plan_column": ("column",),
                      "plan_slab": ()}                  # CV ไม่มี template ของพื้น


def _new_report():
    return {"ok": False, "reason": None, "reason_code": None, "orientation": None,
            "anchor_source": None, "transform": None, "measured": 0, "cv_only_count": 0,
            "grid_check": [], "cv_only": [], "candidates": [], "classes_skipped": []}


def _eid(el):
    return (el.get("element_id") or el.get("id")) if isinstance(el, dict) else None


def measure_page(doc, grid, cv_scan=None, subtask=None):
    """รายงานผลวัดของแผ่นนี้ — **ไม่แก้ doc / grid / cv_scan ที่รับมาเลย** (D3)

    doc      = ผล pass2 ของหน้านั้น (อาจมี cv_position จาก worker.merge_cv_marks)
    grid     = grid master ({"x_lines": [...], "y_lines": [...]})
    cv_scan  = ผล pass1.5 ("elements") + pass2.5 ("self_harvest_points") ของหน้านั้น หรือ None
    subtask  = plan_footing / plan_beam / ... (กรองชนิดจุด CV-only ที่รายงาน) หรือ None = ทุกชนิด

    คืน report: ok, reason, reason_code, orientation, anchor_source, transform, measured
    (= จำนวน element ที่ตัวแปลงหาตำแหน่งได้), cv_only_count, grid_check, cv_only (จุดที่ CV เห็น
    แต่ไม่ได้จับคู่), candidates (ผลทั้ง 4 ทิศ — หลักฐานตอนปฏิเสธ), classes_skipped (ด่านสัดส่วน)"""
    els = doc.get("elements") if isinstance(doc, dict) and isinstance(doc.get("elements"), list) else []
    rep = _new_report()
    anchors = collect_anchors(els)
    if len(anchors) >= MIN_ANCHORS:
        # ทาง 1: cv_mark ที่ผ่านการตรวจ — กล่องระบุตัวตน ทิศแกนจึงมาจากข้อมูลเอง ไม่ต้องทดลองทิศ
        # แต่ยังต้องผ่านด่านหลักฐานจากภาพชุดเดียวกับทางรูปทรง (_support_gate ด้านล่าง) — cv_mark ที่ผ่าน
        # การตรวจแล้วก็ยังเป็นคำอ้างของโมเดล ทีมตรวจเจอยอมรับผิด 5.8% ของทางนี้เมื่อไม่มีด่านนี้
        rep["anchor_source"] = "cv_mark"
        fit = _fit([a[:3] for a in anchors], grid)
        pairs = [{"ref": a[2], "ids": [a[3]], "cv": {"cx": a[0], "cy": a[1]}} for a in anchors]
        chosen_fit, scale = fit, fit["scale"]
        if fit["ok"]:
            gate = {}
            bad = _support_gate(els, cv_scan, grid, fit["transform"], gate)
            rep.update(orientation_margin=gate["orientation_margin"], support=gate["support"])
            if bad:
                rep.update(reason_code=bad[0], reason=bad[1])
                return rep
    elif not isinstance(cv_scan, dict):
        rep.update(reason_code="no_cv", reason="ไม่มีผล CV ของหน้านี้ (ครอปไม่ชัดเจน/CV ไม่ได้รัน) "
                                               "และไม่มี cv_mark ที่เชื่อได้ — ไม่มีหมุดให้วัด")
        return rep
    else:
        rep["anchor_source"] = "shape_match"
        sm = _shape_match(els, cv_scan, grid)
        rep["classes_skipped"] = sm["skipped"]
        for k in ("orientation_margin", "support"):
            if k in sm:
                rep[k] = sm[k]
        rep["candidates"] = [{"orientation": c["orientation"], "ok": c["fit"]["ok"],
                              "reason_code": c["fit"]["reason_code"], "n_anchors": c["fit"]["n"],
                              **{k: (c["fit"]["fit"] or {}).get(k)
                                 for k in ("px_per_m_x", "px_per_m_y", "residual_max_m")}}
                             for c in sm["cands"]]
        if not sm["ok"]:
            rep.update(reason=sm["reason"], reason_code=sm["reason_code"])
            if sm["scale"]:
                rep["scale"] = sm["scale"]
            return rep
        pairs, chosen_fit, scale = sm["chosen"]["pairs"], sm["chosen"]["fit"], None
    if not chosen_fit["ok"]:
        rep.update(reason=chosen_fit["reason"], reason_code=chosen_fit["reason_code"])
        if scale:
            rep["scale"] = scale
        return rep

    t = chosen_fit["transform"]
    rep.update(ok=True, transform=t, orientation=orientation_of(t))
    located, used_xy = set(), set()
    for p in pairs:
        located.update(p["ids"])
        used_xy.add((round(p["cv"]["cx"]), round(p["cv"]["cy"])))
        mx, my = pixel_to_metre(t, p["cv"]["cx"], p["cv"]["cy"])
        nominal = ref_to_metre(grid, p["ref"])
        if nominal:
            d = math.hypot(mx - nominal[0], my - nominal[1])
            if d > SNAP_TOL_M:     # ตัวจับผิด: ref ที่ตอบห่างจากที่ภาพบอกเกินเกณฑ์
                rep["grid_check"].append({"ref": p["ref"], "off_by_m": round(d, 3),
                                          "id": _eid(els[p["ids"][0]])})
    rep["measured"] = len(located)

    # จุดที่ CV เห็น (รวม self-harvest ของ pass2.5) แต่ไม่ได้เป็นหมุด และไม่มี element ไหนชี้ถึง
    # (cv_position ที่เชื่อได้) — รายงานเฉยๆ ไม่เพิ่มเป็น element (D3) · ยังไม่ได้ตรวจว่าซ้ำกับ ref
    # ที่ตอบไว้แล้วหรือไม่ (ทีมตรวจพบว่าส่วนใหญ่ซ้ำ) ข้อความถึงคนจึงห้ามอ้างว่า "โมเดลพลาด"
    used_xy |= {(round(c[0]), round(c[1])) for c in
                (rect_center(cv) for _, cv in _trusted_cv_positions(els)) if c}
    allowed = SUBTASK_CV_CLASSES.get(subtask) if subtask else None
    if isinstance(cv_scan, dict):
        pts = [(e, "pass1.5") for e in cv_scan.get("elements") or [] if isinstance(e, dict)]
        pts += [(e, "pass2.5") for e in cv_scan.get("self_harvest_points") or [] if isinstance(e, dict)]
        for e, src in pts:
            if not (_num(e.get("cx")) and _num(e.get("cy"))):
                continue
            if allowed is not None and e.get("class") not in allowed:
                continue
            if (round(e["cx"]), round(e["cy"])) in used_xy:
                continue
            mx, my = pixel_to_metre(t, e["cx"], e["cy"])
            ref, d = nearest_grid_ref(grid, mx, my)
            rep["cv_only"].append({"class": e.get("class"), "n": e.get("n"),
                                   "center_px": [e["cx"], e["cy"]],
                                   "pos_m": [round(mx, 3), round(my, 3)],
                                   "grid_ref_cv": ref, "snap_dist_m": d, "source": src})
    rep["cv_only_count"] = len(rep["cv_only"])
    return rep


# ── C2: ตรวจ grid master + สรุปทั้งบ้าน (เขียนลง grid_master.json "validation") ──────────
def validate_grid(grid):
    """ปัญหาของ grid master ที่เห็นได้จากตัวไฟล์เอง (ไม่ต้องดูภาพ) → [issue]
    issue = {"code", "axis", "detail_th", ...} · code: duplicate_id / mixed_axis / id_on_both_axes"""
    issues, ids = [], {}
    for axis in ("x", "y"):
        seen = {}
        for ln in _lines(grid, axis):
            i = _line_id(ln)
            if i is not None:
                seen.setdefault(i, []).append(ln.get("pos_m"))
        for i, ps in seen.items():
            if len({float(p) if _num(p) else repr(p) for p in ps}) > 1:
                issues.append({"code": "duplicate_id", "axis": axis, "id": i, "pos_m": ps,
                               "detail_th": f"grid master: แกน {axis} มีเส้นชื่อ {i} ซ้ำ {len(ps)} เส้น "
                                            f"(pos_m {ps}) — ref ที่อ้างเส้น {i} ระบุตำแหน่งไม่ได้ "
                                            f"ไม่เดาว่าเป็นเส้นไหน"})
        kinds = {i: _id_kind(i) for i in seen}
        if {"L", "D"} <= set(kinds.values()):
            letters = [i for i, k in kinds.items() if k == "L"]
            digits = [i for i, k in kinds.items() if k == "D"]
            issues.append({"code": "mixed_axis", "axis": axis, "letters": letters, "digits": digits,
                           "detail_th": f"grid master: แกน {axis} มีทั้งเส้นชื่อตัวอักษร ({', '.join(letters)}) "
                                        f"และตัวเลข ({', '.join(digits)}) ปนกัน — น่าจะอ่านสองแกนมารวมกัน"})
        ids[axis] = set(seen)
    both = sorted(ids["x"] & ids["y"])
    if both:
        issues.append({"code": "id_on_both_axes", "axis": None, "ids": both,
                       "detail_th": f"grid master: เส้นชื่อ {', '.join(both)} อยู่ทั้งแกน x และแกน y — "
                                    f"ref ที่มีชื่อเหล่านี้ระบุตำแหน่งไม่ได้"})
    return issues


def grid_validation(grid, reports):
    """validation ของ grid master ทั้งบ้าน = ปัญหาจากตัวไฟล์ + สิ่งที่ pass3 เห็นจากภาพ
    reports = {page_key: report ของ measure_page} (ว่างได้ = ยังไม่ได้วัด)
    scale_check: suspect (หน้าไหนเจอ px/m ต่างกันเกือบจำนวนเต็มเท่า) > ok (มีหน้าที่วัดผ่าน) > unknown"""
    issues = validate_grid(grid)
    reports = reports or {}
    flipped = {}
    for key, r in reports.items():
        if r.get("ok"):
            for axis in FLIPPED_AXES.get(r.get("orientation"), ()):
                flipped.setdefault(axis, []).append(key)
    for axis, pages in sorted(flipped.items()):
        way = "ล่างขึ้นบน" if axis == "y" else "ขวาไปซ้าย"
        issues.append({"code": "origin_not_top_left", "axis": axis, "pages": pages,
                       "detail_th": f"grid master: pos_m แกน {axis} เริ่มนับจาก{way} (ไม่ใช่จากซ้ายบนตามที่ "
                                    f"prompt gridline กำหนด) — ผลวัด {', '.join(pages)} ใช้ทิศนี้แล้ว "
                                    f"แต่ควรตรวจว่า grid master อ่านทิศถูก"})
    suspects = [(k, r["scale"]) for k, r in reports.items()
                if r.get("reason_code") == "grid_scale_suspect" and r.get("scale")]
    accepted = [(k, r["transform"]) for k, r in reports.items() if r.get("ok") and r.get("transform")]
    if suspects:
        axes = {s["suspect_axis"] for _, s in suspects}
        axis = axes.pop() if len(axes) == 1 else None
        ratio = suspects[0][1]["ratio"]
        pages = [k for k, _ in suspects]
        scale = {"status": "suspect", "suspect_axis": axis, "ratio": ratio, "source": "pass3 " + ", ".join(pages)}
        issues.append({"code": "scale_suspect", "axis": axis, "ratio": ratio, "pages": pages,
                       "detail_th": f"grid master แกน {axis or 'x/y'} น่าจะผิด (อัตราส่วน {ratio:.2f}) — "
                                    f"px ต่อเมตรสองแกนต่างกันเกือบจำนวนเต็มเท่าพอดีบน {', '.join(pages)} "
                                    f"ระยะที่คำนวณจากแกนนี้ควรตรวจก่อนใช้"})
    elif accepted:
        k, t = accepted[0]
        scale = {"status": "ok", "suspect_axis": None,
                 "ratio": round(max(t["px_per_m_x"], t["px_per_m_y"]) / min(t["px_per_m_x"], t["px_per_m_y"]), 3),
                 "source": "pass3 " + ", ".join(k for k, _ in accepted)}
    else:
        scale = {"status": "unknown", "suspect_axis": None, "ratio": None,
                 "source": "pass3 ไม่มีหน้าที่วัดได้" if reports else "pass3 ไม่ได้รัน"}
    return {"issues": issues, "scale_check": scale}


def pass3_file(reports, validation, grid_master_used=True):
    """เนื้อไฟล์ pass3_measure.json รุ่น 2 (C1) — เว็บยังอ่านรุ่น 1 เก่าได้ (ไม่มี version)"""
    return {"version": 2, "mode": "report_only", "grid_master_used": bool(grid_master_used),
            "grid_validation": validation, "pages": reports}


REASON_SHORT_TH = {"too_few_anchors": "หมุดไม่พอ", "collinear": "หมุดเรียงเส้นเดียว",
                   "zero_scale": "scale เป็นศูนย์", "residual": "หมุดเบี้ยวเกินเกณฑ์",
                   "anisotropy": "px/m สองแกนไม่เท่ากัน", "grid_scale_suspect": "grid master น่าจะผิด",
                   "orientation_ambiguous": "ทิศแกนกำกวม", "weak_support": "จุด CV ไม่เข้ากับตัวแปลง",
                   "no_cv": "ไม่มีผล CV"}


def summary_warnings(reports, validation):
    """ข้อความถึงคน (warnings ระดับงาน ไม่ใช่ doc.warnings ที่แปลว่าโมเดลพูด) — บอกสิ่งที่วัดได้/ไม่ได้
    ไม่อ้างว่าแก้หรือเพิ่มอะไรให้ผลอ่านแบบ เพราะ pass3 ไม่แก้อะไรเลย"""
    lines = []
    if reports:
        ok = sum(1 for r in reports.values() if r.get("ok"))
        why = {}
        for r in reports.values():
            if not r.get("ok"):
                k = REASON_SHORT_TH.get(r.get("reason_code"), r.get("reason_code") or "?")
                why[k] = why.get(k, 0) + 1
        s = (f"pass3 (วัดระยะเทียบผังกริด · รายงานอย่างเดียว ไม่แก้ผลอ่านแบบ): วัดได้ {ok}/{len(reports)} หน้า")
        if why:
            s += " · วัดไม่ได้: " + ", ".join(f"{k} {v}" for k, v in why.items())
        n_off = sum(len(r.get("grid_check") or []) for r in reports.values())
        if n_off:
            s += f" · ref ที่ห่างจากตำแหน่งในภาพเกิน {SNAP_TOL_M} ม. {n_off} จุด"
        n_cv = sum(r.get("cv_only_count") or 0 for r in reports.values())
        if n_cv:
            s += (f" · CV เห็นอีก {n_cv} จุดที่ไม่ได้จับคู่ (ยังไม่ได้ตรวจว่าซ้ำกับที่อ่านได้ไหม "
                  f"ไม่ได้นำเข้าผล ดู pass3_measure.json)")
        lines.append(s)
    lines += [i["detail_th"] for i in (validation or {}).get("issues") or []]
    return lines


def demo():
    """self-check: กริดที่รู้ระยะจริง → fit ต้องได้ px/m ตรงเป๊ะ ต้องปฏิเสธของเสีย และต้องไม่แก้ doc"""
    import copy
    grid = {"x_lines": [{"id": "1", "pos_m": 0.0}, {"id": "2", "pos_m": 4.0},
                        {"id": "3", "pos_m": 7.0}],
            "y_lines": [{"id": "A", "pos_m": 0.0}, {"id": "B", "pos_m": 3.0},
                        {"id": "C", "pos_m": 8.0}]}
    # ภาพสมมติ 50 px/m, origin ที่ (100, 80)
    to_px = lambda mx, my: (100 + 50 * mx, 80 + 50 * my)

    assert parse_grid_ref("D1") == {"row": "D", "col": "1"}
    assert parse_grid_ref("A-1") == parse_grid_ref("1A") == parse_grid_ref("1-A") == {"row": "A", "col": "1"}
    assert parse_grid_ref("~B2") is None and parse_grid_ref("") is None and parse_grid_ref("1-3") is None
    assert ref_to_metre(grid, "2B") == ref_to_metre(grid, "B2") == (4.0, 3.0)
    assert rect_center({"x": 10, "y": 20, "w": 10, "h": 20}) == (15.0, 30.0)
    assert rect_center({"cx": 5, "cy": 6, "w": 2, "h": 2}) == (5.0, 6.0)

    anchors = [(*to_px(0, 0), "A1"), (*to_px(4, 0), "A2"), (*to_px(0, 3), "B1"),
               (*to_px(7, 8), "C3")]
    t, why, code = build_transform(anchors, grid)
    assert t and why is None and code is None, why
    assert abs(t["px_per_m_x"] - 50) < 0.01 and abs(t["px_per_m_y"] - 50) < 0.01
    assert t["residual_max_m"] < 1e-6, t
    assert orientation_of(t) == "identity"

    # แปลงกลับต้องได้เมตรเดิม และวัดระยะคานสู่คานต้องตรง (A1→A2 = 4.00 ม.)
    mx, my = pixel_to_metre(t, *to_px(4, 3))
    assert abs(mx - 4) < 1e-6 and abs(my - 3) < 1e-6
    assert abs(metre_distance(t, to_px(0, 0), to_px(4, 0)) - 4.0) < 1e-6

    # snap: ตรงจุดตัด = ได้ ref · ห่าง 2 ม. = ไม่ยัดให้
    assert nearest_grid_ref(grid, 4.0, 3.0)[0] == "B2"
    assert nearest_grid_ref(grid, 5.9, 1.4)[0] is None

    # หมุดน้อยไป / เรียงเส้นเดียว / เบี้ยว → ต้องปฏิเสธพร้อมเหตุผล ไม่คืนตัวเลขมั่ว
    assert build_transform(anchors[:2], grid)[2] == "too_few_anchors"
    assert build_transform([(*to_px(0, 0), "A1"), (*to_px(0, 3), "B1"),
                            (*to_px(0, 8), "C1")], grid)[2] == "collinear"
    bad = list(anchors) + [(to_px(0, 0)[0] + 400, to_px(0, 0)[1], "A3")]
    t_bad, why_bad, code_bad = build_transform(bad, grid)
    assert t_bad is None and "เบี้ยว" in why_bad and code_bad == "residual", why_bad

    # ทั้งหน้า (ทาง cv_mark ที่ไม่ใช่เลขลำดับ): วัดได้ + จุด CV-only ถูกรายงาน + doc ไม่ถูกแตะ
    # (รอบแก้ 2026-09-26: ทาง cv_mark ต้องชนะการอ่านแบบอื่นทุกแบบ ≥ MIN_ORIENTATION_MARGIN จุด —
    # 10 หมุด + 1 จุด CV-only บนกริด 6×5 ช่อง เว้นระยะไม่เท่ากันสองแกน (3.0 ม./3.5 ม.) กันไม่ให้ผัง
    # เล็กเกินไปจนสมมาตรพอที่การอ่านกลับด้าน/เลื่อนช่องจะอธิบายจุดได้ใกล้เคียงกัน — เดิมใช้แค่ 6 หมุด
    # บนกริด 3×3 สมมาตร (0/4/7 × 0/3/8) ซึ่งพบว่าการกลับแกน x ยังอธิบายได้ 4/6 จุดพอดี (margin เหลือ 2
    # ไม่ถึง 3) หลังเพิ่มด่านนี้ให้ทาง cv_mark ด้วย — ไม่ใช่บั๊กของด่าน แค่ผังตัวอย่างเล็ก/สมมาตรเกินไป)
    grid = {"x_lines": [{"id": str(i), "pos_m": 3.0 * i} for i in range(1, 7)],
            "y_lines": [{"id": c, "pos_m": 3.5 * j} for j, c in enumerate(["A", "B", "C", "D", "E"])]}
    box = lambda mx, my: {"cx": to_px(mx, my)[0], "cy": to_px(mx, my)[1], "w": 20, "h": 20, "class": "footing"}
    placed = (("4E", 2, (12.0, 14.0)), ("3E", 7, (9.0, 14.0)), ("3A", 9, (9.0, 0.0)), ("6B", 10, (18.0, 3.5)),
              ("5C", 8, (15.0, 7.0)), ("2B", 4, (6.0, 3.5)), ("2A", 6, (6.0, 0.0)), ("3C", 3, (9.0, 7.0)),
              ("3B", 1, (9.0, 3.5)), ("4A", 5, (12.0, 0.0)))
    doc = {"elements": [{"element_id": f"F{i}", "element_type": "footing", "grid_refs": [ref], "cv_mark": mark,
                         "cv_position": box(*m)} for i, (ref, mark, m) in enumerate(placed, 1)]}
    cv = {"elements": [dict(box(*m), n=mark) for _, mark, m in placed]
          + [{"n": 11, "cx": to_px(6.0, 14.0)[0], "cy": to_px(6.0, 14.0)[1], "class": "footing"}],
          "self_harvest_points": [{"cx": to_px(15.0, 3.5)[0], "cy": to_px(15.0, 3.5)[1], "class": "column"}]}
    before = copy.deepcopy(doc)
    rep = measure_page(doc, grid, cv, "plan_footing")
    assert doc == before, "pass3 ต้องไม่แก้ doc"
    assert rep["ok"] and rep["anchor_source"] == "cv_mark" and rep["measured"] == 10, rep
    assert {c["grid_ref_cv"] for c in rep["cv_only"]} == {"E2", "B5"}, rep["cv_only"]
    assert {c["source"] for c in rep["cv_only"]} == {"pass1.5", "pass2.5"}

    # กริดพัง (pos_m เป็น null ทุกเส้น) → ปฏิเสธ ไม่ crash
    dead = {"x_lines": [{"id": "1", "pos_m": None}], "y_lines": [{"id": "A", "pos_m": None}]}
    assert measure_page(doc, dead, cv)["ok"] is False
    assert measure_page({"elements": []}, grid, None)["reason_code"] == "no_cv"

    print("OK — pass3_measure self-check ผ่านทุกข้อ")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--demo":
        print(json.dumps(measure_page(json.loads(open(sys.argv[1], encoding="utf-8").read()),
                                      json.loads(open(sys.argv[2], encoding="utf-8").read())),
                         ensure_ascii=False, indent=1))
    else:
        demo()
