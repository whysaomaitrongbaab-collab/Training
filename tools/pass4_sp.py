#!/usr/bin/env python3
"""
tools/pass4_sp.py — Pass 4 · SP (Structural Plans): "Analyze SP" + "HW pixel lock with element" ตามแผนภาพ King

แผนภาพ: STR classified -> 2. Structural Plans (SP) -> Analyze SP
        ลูกศรเข้า = "Input Grid line Coordinate ทำให้อ้างอิงเส้นที่อ่าน element ได้ง่ายขึ้น" · ป้ายการบ้าน = "pixel lock with element"

สิ่งที่ไฟล์นี้ทำ (ไม่เรียกโมเดล — ตอนนี้ยังไม่มีโมเดลอ่านแปลนที่เทรนแล้ว จึงใช้ element ใน json เฉลยเป็นตัวแทนผลที่โมเดลอ่าน):
  1. Input grid line coordinate: ตารางเส้นกริดต่อแปลนบนหน้า = ชื่อ · พิกเซลที่ 200 dpi · เมตรจาก grid master  (ส่วนที่ส่งให้ "Analyze SP")
       เส้นบนหน้ามาจาก grid lab (gridlab_probe.detect) จับคู่ชื่อกับ grid master -> เส้นตรง pt = a*เมตร + b ต่อแกนต่อแปลน
  2. Pixel lock: element ที่มี grid_ref -> ตำแหน่งพิกเซล: คาน = เส้นตรงจากจุดต้นถึงจุดปลาย; ฐานราก/เสา = จุดที่จุดตัดเส้นกริด
       ref ที่แยกเป็น (เส้นตั้ง, เส้นนอน) ตาม id ใน grid master ไม่ได้ หรือกำกวม = ไม่ล็อก (ไม่เดา — กติกาเดียวกับ D2 ของ grid ref)
  3. ตรวจว่าล็อกลงบนของที่วาดจริง (หน้าเวกเตอร์): จุด = มีรูปปิดขนาดฐานราก/เสาครอบจุด · คาน = มีเส้นทึบขนานห่างจากแกนกริดในช่วงครึ่งความกว้างคาน
       เทียบกับ "ตัวควบคุม" = จุดตัดกริดที่ไม่มี element / ช่วงกริดที่ไม่มีคาน — ถ้าอัตรา element สูงกว่าตัวควบคุมชัด ถึงเชื่อได้ว่าล็อกถูกที่
  4. view หลายแปลนในหน้าเดียว (บ้าน 1ชั้น_27 หน้า 10 มีแปลนฐานรากกับแปลนคาน): เลือกแปลนที่ล็อกแล้ววาดตรงมากสุด; คะแนนต่ำ = ติดธง weak

    python tools/pass4_sp.py <บ้าน> <หน้า> [--no-ocr]    # เขียน ../logic_test_out/<บ้าน>/pass4_sp_pNN.json + .png
    python tools/pass4_sp.py --eval [บ้าน ...]            # วัด lock rate + ตรวจบนภาพวาดจริง (ค่าเริ่มต้น: บ้านเวกเตอร์ที่มีเฉลย)
    python tools/pass4_sp.py --demo                       # self-check กฎล้วน
ข้อจำกัด: หน้าภาพสแกนยังไม่รองรับ (grid lab เริ่มจากเวกเตอร์ตามที่ King สั่ง) · พิกัด = ตามที่ตามองเห็น (หมุนหน้าแล้ว) ตรงกับภาพที่ render
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "logic_test_out"
DPI = 200                          # เดียวกับภาพเทรน
FIT_TOL_PT = 3.0                   # เส้นที่ชื่อตรง master แต่ห่างเส้นตรงเกินนี้ = ชื่อผิด -> ไม่ใช้แปลนนี้ (ค่าเลือกเอง; 3 pt ~ 8 ซม. ที่ 1:75)
POINT_MAX_M = 2.5                  # รูปปิดที่ใหญ่กว่านี้ไม่ใช่ฐานราก/เสา
POINT_MIN_PT = 2.5                 # ด้านสั้นสุดของรูป — ท่อนเส้นประของกริดบางกว่านี้ จึงไม่นับ
BEAM_BAND_M = 0.4                  # เส้นขอบคานอยู่ห่างแกนกริดไม่เกินนี้ (ค่าเลือกเอง)
BEAM_COVER_OK = 0.6                # คานที่ตรวจผ่านเมื่อ >= สัดส่วนนี้ของจุดตัวอย่างมีเส้นขนาน
ANGLE_TOL = math.radians(3)
CONTROL_MAX = 60                   # ตัวควบคุมต่อแปลนไม่เกินนี้ (หน้าที่มีเส้นกริดหลายสิบเส้นจะช้า)
PLAN_FAMILY = {"beam_plan", "footing_plan", "roof_frame_plan", "column_plan", "slab_plan", "etc_plan", "plan"}


# ---------- กฎล้วน (ทดสอบใน --demo) ----------
def split_ref(ref, xs, ys):
    """'A1' / '1-A' / "A'1" -> (id เส้นตั้ง x, id เส้นนอน y) ตาม id ใน grid master หรือ None (ไม่รู้จัก/กำกวม)"""
    s = re.sub(r"[\s,]", "", str(ref or ""))
    found = set()
    for k in range(1, len(s)):
        left, right = s[:k].rstrip("-"), s[k:].lstrip("-")
        if left in ys and right in xs:
            found.add((right, left))
        if left in xs and right in ys:
            found.add((left, right))
    return found.pop() if len(found) == 1 else None


REGION_RE = re.compile(r"^\s*([^\s\-xX×]+)\s*-\s*([^\s\-xX×]+)\s*[xX×]\s*([^\s\-xX×]+)\s*-\s*([^\s\-xX×]+)\s*$")


def split_region(ref, xs, ys):
    """แผงพื้น 'A-B x 1-2' (แถว A-B คูณ คอลัมน์ 1-2) -> ((x1, x2), (y1, y2)) ตาม id ใน master หรือ None; สลับลำดับได้ ('1-2 x A-B')"""
    m = REGION_RE.match(str(ref or ""))
    if not m:
        return None
    a, b, c, d = m.groups()
    if a in ys and b in ys and c in xs and d in xs:
        return (c, d), (a, b)
    if a in xs and b in xs and c in ys and d in ys:
        return (a, b), (c, d)
    return None


def fit_axis(pairs):
    """pairs [(เมตรใน master, pt บนหน้า)] -> (a, b, n, residual สูงสุด pt) ของ pt = a*เมตร + b หรือ None
    ต้องมี >= 2 ค่าเมตรที่ต่างกัน และทุกเส้นห่างเส้นตรงไม่เกิน FIT_TOL_PT"""
    pairs = list(pairs)
    if len({round(m, 4) for m, _ in pairs}) < 2:
        return None
    n = len(pairs)
    mm, mp = sum(m for m, _ in pairs) / n, sum(p for _, p in pairs) / n
    sxx = sum((m - mm) ** 2 for m, _ in pairs)
    a = sum((m - mm) * (p - mp) for m, p in pairs) / sxx
    b = mp - a * mm
    res = max(abs(a * m + b - p) for m, p in pairs)
    return (a, b, n, res) if res <= FIT_TOL_PT and abs(a) > 1e-6 else None


def bays(ids_sorted, start, end):
    """id เรียงตามเมตร + id ต้น/ปลายของคาน -> รายการช่วงกริดติดกันที่คานคลุม [(id1, id2)]"""
    if start not in ids_sorted or end not in ids_sorted:
        return []
    i, j = sorted((ids_sorted.index(start), ids_sorted.index(end)))
    return [(ids_sorted[k], ids_sorted[k + 1]) for k in range(i, j)]


def cover_fraction(p0, p1, pieces, band, n=9):
    """สัดส่วนจุดตัวอย่างบนช่วง p0-p1 (ตัดปลาย 10%) ที่มีท่อนเส้นทึบขนานห่าง 1..band pt และคลุมตำแหน่งนั้น
    pieces = [(x0, y0, x1, y1)]"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return 0.0
    ux, uy = dx / L, dy / L
    lo_x, hi_x = min(p0[0], p1[0]) - band - 1, max(p0[0], p1[0]) + band + 1
    lo_y, hi_y = min(p0[1], p1[1]) - band - 1, max(p0[1], p1[1]) + band + 1
    pieces = [q for q in pieces if max(q[0], q[2]) >= lo_x and min(q[0], q[2]) <= hi_x
              and max(q[1], q[3]) >= lo_y and min(q[1], q[3]) <= hi_y]      # ตัดท่อนที่ไกลทิ้งก่อน (หน้า A1 มีหลายหมื่นท่อน)
    hit = 0
    for k in range(n):
        t = 0.1 + 0.8 * k / (n - 1)
        sx, sy = p0[0] + dx * t, p0[1] + dy * t
        for x0, y0, x1, y1 in pieces:
            vx, vy = x1 - x0, y1 - y0
            ln = math.hypot(vx, vy)
            if ln < 1e-6 or abs(vx * uy - vy * ux) / ln > math.sin(ANGLE_TOL):
                continue
            along0, along1 = sorted(((x0 - sx) * ux + (y0 - sy) * uy, (x1 - sx) * ux + (y1 - sy) * uy))
            perp = abs((x0 - sx) * uy - (y0 - sy) * ux)
            if along0 - 0.5 <= 0 <= along1 + 0.5 and 1.0 <= perp <= band:
                hit += 1
                break
    return hit / n


def point_hit(pt, boxes, max_pt):
    """มีรูปปิดขนาดฐานราก/เสาครอบจุด (กล่องขยาย 2 pt) หรือไม่; boxes = [(x0, y0, x1, y1)]"""
    for x0, y0, x1, y1 in boxes:
        w, h = x1 - x0, y1 - y0
        if min(w, h) >= POINT_MIN_PT and max(w, h) <= max_pt and x0 - 2 <= pt[0] <= x1 + 2 and y0 - 2 <= pt[1] <= y1 + 2:
            return True
    return False


def box_around(pt, pieces, half_max):
    """จุดอยู่ในกล่องที่ประกอบจากเส้นทึบแยกท่อน: มีเส้นแนวนอนเหนือและใต้จุด + เส้นแนวตั้งซ้ายและขวาจุด (ห่าง 2..half_max pt,
    คลุมตำแหน่งจุด) — CAD บางไฟล์วาดฐานรากเป็นเส้นทีละด้าน ไม่ใช่รูปปิด (2ชั้น_43) ใช้เฉพาะแปลนฐานราก: แปลนคานมีเส้นขอบคานล้อมทุกจุดตัดอยู่แล้ว"""
    x, y = pt
    up = dn = lf = rt = False
    for x0, y0, x1, y1 in pieces:
        if abs(y1 - y0) <= 0.5 and abs(x1 - x0) >= 3 and min(x0, x1) - 1 <= x <= max(x0, x1) + 1:
            dy = (y0 + y1) / 2 - y
            dn = dn or 2 <= dy <= half_max
            up = up or -half_max <= dy <= -2
        elif abs(x1 - x0) <= 0.5 and abs(y1 - y0) >= 3 and min(y0, y1) - 1 <= y <= max(y0, y1) + 1:
            dx = (x0 + x1) / 2 - x
            rt = rt or 2 <= dx <= half_max
            lf = lf or -half_max <= dx <= -2
        if up and dn and lf and rt:
            return True
    return False


# ---------- ข้อมูลบ้าน ----------
def house_dir(house, base_order=("json_แก้ไขแล้ว", "rawjson_ยังไม่ได้แก้ไขโดนคน")):
    for base in base_order:
        for d in (ROOT / base).glob(f"*{house}"):
            if any(d.glob("*gridline*.json")):
                return d
    return None


def load_master(d):
    f = sorted(d.glob("*gridline*.json"))[0]
    g = json.loads(f.read_text(encoding="utf-8")).get("grid", {})
    out = {"x": {}, "y": {}, "dummy": set()}
    for key, arr in (("x", "x_lines"), ("y", "y_lines")):
        for ln in g.get(arr, []):
            if ln.get("id") is not None and isinstance(ln.get("pos_m"), (int, float)):
                out[key][str(ln["id"])] = float(ln["pos_m"])
                if ln.get("type") == "dummy":
                    out["dummy"].add(str(ln["id"]))
    return out


def element_files(d, pn):
    res = []
    for f in sorted(d.glob("*.json")):
        m = re.search(r"หน้า(\d+)", f.name)
        if not m or int(m.group(1)) != pn:
            continue
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(j, dict) and j.get("pattern") in PLAN_FAMILY and isinstance(j.get("elements"), list):
            res.append((f.name, j))
    return res


# ---------- ขั้น 1: input grid line coordinate ----------
def plan_transforms(lines, master):
    """lines = gridlab_probe.detect() -> {แปลน: {'x': fit, 'y': fit, 'lines': [...]}} เฉพาะแปลนที่ fit ได้ทั้งสองแกน"""
    out = {}
    for p in sorted({ln.get("plan") for ax in lines for ln in lines[ax]}, key=lambda v: (v is None, v)):
        tf = {}
        for ax, key in (("v", "x"), ("h", "y")):
            pairs = [(master[key][ln["label"]], ln["pos"]) for ln in lines[ax]
                     if ln.get("plan") == p and ln.get("label") in master[key]]
            f = fit_axis(pairs)
            if f:
                tf[key] = f
        if len(tf) == 2:
            out[p] = tf
    return out


def to_pt(tf, xid, yid, master):
    ax, bx = tf["x"][0], tf["x"][1]
    ay, by = tf["y"][0], tf["y"][1]
    return (ax * master["x"][xid] + bx, ay * master["y"][yid] + by)


def grid_input(tf, master):
    """ตารางเส้นกริดของแปลน (ส่งให้ Analyze SP): ทุกเส้นใน master ที่คำนวณตำแหน่งบนหน้าได้ -> pt · พิกเซล 200 dpi · เมตร"""
    k = DPI / 72.0
    rows = []
    for key, name in (("x", "vertical"), ("y", "horizontal")):
        a, b = tf[key][0], tf[key][1]
        for i, m in sorted(master[key].items(), key=lambda kv: kv[1]):
            pt = a * m + b
            rows.append(dict(id=i, axis=key, kind="dummy" if i in master["dummy"] else "named", pos_m=m,
                             pos_pt=round(pt, 2), pos_px=round(pt * k, 1)))
    return rows


# ---------- ขั้น 2: pixel lock ----------
def lock_elements(elements, tf, master):
    """element -> ตำแหน่งบนหน้า; คาน = segment, ที่เหลือที่มี ref = points; ไม่มี ref/ref ไม่ resolve = ไม่ล็อก พร้อมเหตุผล"""
    xs, ys = set(master["x"]), set(master["y"])
    out = []
    for e in elements:
        base = dict(element_id=e.get("element_id"), element_type=e.get("element_type"))
        s, t = e.get("grid_ref_start"), e.get("grid_ref_end")
        refs = [r for r in (e.get("grid_refs") if isinstance(e.get("grid_refs"), list) else [e.get("grid_ref")]) if r]
        if s and t:
            a, b = split_ref(s, xs, ys), split_ref(t, xs, ys)
            if a and b:
                out.append(dict(base, kind="segment", refs=[s, t], ids=[a, b], pts=[to_pt(tf, *a, master), to_pt(tf, *b, master)]))
            else:
                out.append(dict(base, kind="segment", refs=[s, t], status="unresolved_ref"))
        elif refs:
            for r in refs:
                a, reg = split_ref(r, xs, ys), split_region(r, xs, ys)
                if a:
                    out.append(dict(base, kind="point", refs=[r], ids=[a], pts=[to_pt(tf, *a, master)]))
                elif reg:      # แผงพื้น: มุมซ้ายบน-ขวาล่างของสี่เหลี่ยมระหว่างเส้นกริด (ยังไม่มีตัวตรวจบนภาพวาด)
                    (x1, x2), (y1, y2) = reg
                    out.append(dict(base, kind="region", refs=[r], ids=[reg], pts=[to_pt(tf, x1, y1, master), to_pt(tf, x2, y2, master)]))
                else:
                    out.append(dict(base, kind="point", refs=[r], status="unresolved_ref"))
        else:
            out.append(dict(base, kind=None, refs=[], status="no_grid_ref"))
    return out


# ---------- ขั้น 3: ตรวจบนภาพวาดจริง ----------
def drawn_things(page):
    """(ท่อนเส้นทึบยาว >= 3 pt, กล่องรูปที่วาด) จาก get_drawings — เส้นกริดแบบเส้นประ (dashes) ไม่นับเป็นเส้นทึบ
    พิกัดคูณ page.rotation_matrix ให้เป็นพิกัดที่ตามองเห็น (หน้า /Rotate 90 = 3,507 จาก 6,267 หน้า; ก่อนแก้ 1ชั้น_25 น.24 ล็อกถูกที่
    แต่ตรวจเทียบภาพวาดไม่เจอเลยเพราะ get_drawings ให้พิกัดก่อนหมุน) · รูปสี่เหลี่ยม (re) นับทั้งเป็นกล่องและเป็นเส้นขอบ 4 ด้าน"""
    import fitz
    rm = page.rotation_matrix
    pieces, boxes = [], []
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"]) * rm
        boxes.append((r.x0, r.y0, r.x1, r.y1))
        solid = d.get("dashes") in (None, "", "[] 0")
        for it in d["items"]:
            if it[0] == "re":
                rr = fitz.Rect(it[1]) * rm
                boxes.append((rr.x0, rr.y0, rr.x1, rr.y1))
                if solid:
                    pieces += [(rr.x0, rr.y0, rr.x1, rr.y0), (rr.x0, rr.y1, rr.x1, rr.y1),
                               (rr.x0, rr.y0, rr.x0, rr.y1), (rr.x1, rr.y0, rr.x1, rr.y1)]
            elif it[0] == "l" and solid:
                a, b = it[1] * rm, it[2] * rm
                if math.hypot(b.x - a.x, b.y - a.y) >= 3:
                    pieces.append((a.x, a.y, b.x, b.y))
    return pieces, boxes


def near(pieces, pt, r):
    """ท่อนที่อยู่ในช่องสี่เหลี่ยมรัศมี r รอบจุด (ตัดทิ้งก่อน box_around เพราะหน้า A1 มีหลายหมื่นท่อน)"""
    return [q for q in pieces if max(q[0], q[2]) >= pt[0] - r and min(q[0], q[2]) <= pt[0] + r
            and max(q[1], q[3]) >= pt[1] - r and min(q[1], q[3]) <= pt[1] + r]


def verify(locks, tf, master, pieces, boxes, use_box=False):
    """ใส่ verified/cover ให้ล็อกแต่ละตัว + ตัวควบคุมของแปลนนี้ -> สถิติ"""
    a = abs(tf["x"][0])                                   # pt ต่อเมตร (สเกลแกน x)
    max_pt, band = POINT_MAX_M * a, BEAM_BAND_M * a
    xs_sorted = sorted(master["x"], key=master["x"].get)
    ys_sorted = sorted(master["y"], key=master["y"].get)
    used_pts, used_bays = set(), set()
    for lk in locks:
        if "pts" not in lk or lk["kind"] == "region":
            continue
        if lk["kind"] == "point":
            lk["verified"] = point_hit(lk["pts"][0], boxes, max_pt) or (use_box and box_around(lk["pts"][0], near(pieces, lk["pts"][0], max_pt), max_pt / 2))
            used_pts.add(lk["ids"][0])
        else:
            lk["cover"] = round(cover_fraction(lk["pts"][0], lk["pts"][1], pieces, band), 2)
            lk["verified"] = lk["cover"] >= BEAM_COVER_OK
            (x1, y1), (x2, y2) = lk["ids"]
            if x1 == x2:
                used_bays |= {("y", x1, p, q) for p, q in bays(ys_sorted, y1, y2)}
            elif y1 == y2:
                used_bays |= {("x", y1, p, q) for p, q in bays(xs_sorted, x1, x2)}
    ctl_pts = [(xi, yi) for xi in master["x"] for yi in master["y"] if (xi, yi) not in used_pts]
    ctl_pts = ctl_pts[::max(1, len(ctl_pts) // CONTROL_MAX)]            # ตัวควบคุมเว้นระยะเท่าๆ กัน ไม่เกิน CONTROL_MAX
    ctl_pt_hits = []
    for xi, yi in ctl_pts:
        c = to_pt(tf, xi, yi, master)
        ctl_pt_hits.append(point_hit(c, boxes, max_pt) or (use_box and box_around(c, near(pieces, c, max_pt), max_pt / 2)))
    ctl_beam = []
    for yi in master["y"]:                                # ช่วงตามแกน x (เส้นนอน yi): ระหว่าง x ติดกัน
        for p, q in zip(xs_sorted, xs_sorted[1:]):
            if ("x", yi, p, q) not in used_bays:
                ctl_beam.append(cover_fraction(to_pt(tf, p, yi, master), to_pt(tf, q, yi, master), pieces, band))
    for xi in master["x"]:
        for p, q in zip(ys_sorted, ys_sorted[1:]):
            if ("y", xi, p, q) not in used_bays:
                ctl_beam.append(cover_fraction(to_pt(tf, xi, p, master), to_pt(tf, xi, q, master), pieces, band))
    ctl_beam = ctl_beam[::max(1, len(ctl_beam) // CONTROL_MAX)]
    pts = [lk for lk in locks if lk.get("kind") == "point" and "pts" in lk]
    bms = [lk for lk in locks if lk.get("kind") == "segment" and "pts" in lk]
    rate = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
    return dict(points=len(pts), points_hit=rate([lk["verified"] for lk in pts]),
                control_points=len(ctl_pts), control_points_hit=rate(ctl_pt_hits),
                beams=len(bms), beams_ok=rate([lk["verified"] for lk in bms]), beams_cover_mean=rate([lk["cover"] for lk in bms]),
                control_bays=len(ctl_beam), control_bays_ok=rate([c >= BEAM_COVER_OK for c in ctl_beam]),
                control_bays_cover_mean=rate(ctl_beam))


def score(v):
    """แปลนไหนเหมาะกับ view นี้: อัตราที่ล็อกลงบนของที่วาดจริง (จุดและคานถ่วงตามจำนวน)"""
    n = (v["points"] or 0) + (v["beams"] or 0)
    if not n:
        return 0.0
    return ((v["points_hit"] or 0) * (v["points"] or 0) + (v["beams_ok"] or 0) * (v["beams"] or 0)) / n


def kind_of_page(page):
    import run_part1_part3 as R
    return R.kind_of(**R.page_info(page))


# ---------- รันหน้าเดียว ----------
def run_page(house, pn, ocr=True, write=True):
    import fitz
    import gridlab_probe as G
    d = house_dir(house)
    if d is None:
        return dict(house=house, page=pn, error="no_grid_master")
    master = load_master(d)
    doc = fitz.open(G.pdf_of(house))
    page = doc[pn - 1]
    files = element_files(d, pn)
    lines = G.detect(page, ocr=ocr)
    tfs = plan_transforms(lines, master)
    pieces, boxes = drawn_things(page)
    res = dict(house=house, page=pn, plans={}, files=[])
    for p, tf in tfs.items():
        res["plans"][str(p)] = dict(scale_pt_per_m=round(abs(tf["x"][0]), 2), fit_x=dict(n=tf["x"][2], res_pt=round(tf["x"][3], 2)),
                                    fit_y=dict(n=tf["y"][2], res_pt=round(tf["y"][3], 2)), grid_input=grid_input(tf, master))
    if not tfs:
        res["error"] = "no_plan_fits_master"
        # เหตุผล: ไม่เจอเส้นเลย (หน้าภาพสแกน) / เจอแต่ชื่อไม่ตรง master / ตรงแต่ fit ไม่ผ่าน / ได้แกนเดียว
        res["why"] = dict(lines_v=len(lines["v"]), lines_h=len(lines["h"]),
                          matched_v=sum(ln.get("label") in master["x"] for ln in lines["v"]),
                          matched_h=sum(ln.get("label") in master["y"] for ln in lines["h"]), page_kind=kind_of_page(page))
    for fname, j in files:
        best = None
        for p, tf in tfs.items():
            locks = lock_elements(j["elements"], tf, master)
            v = verify(locks, tf, master, pieces, boxes, use_box=j.get("pattern") == "footing_plan")
            if best is None or score(v) > best[0]:
                best = (score(v), p, locks, v)
        entry = dict(file=fname, pattern=j.get("pattern"), view_title=j.get("view_title"), elements=len(j["elements"]))
        if best:
            sc, p, locks, v = best
            entry.update(plan=p, score=round(sc, 3), weak=sc < 0.3 and len(tfs) > 1 or sc < 0.15, verify=v, locks=locks,
                         locked=sum("pts" in lk for lk in locks), unresolved=sum(lk.get("status") == "unresolved_ref" for lk in locks),
                         no_ref=sum(lk.get("status") == "no_grid_ref" for lk in locks))
        res["files"].append(entry)
    if write:
        out = OUT / house
        out.mkdir(parents=True, exist_ok=True)
        (out / f"pass4_sp_p{pn:02d}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        draw(page, res, out / f"pass4_sp_p{pn:02d}.png")
    doc.close()
    return res


def draw(page, res, path, dpi=110):
    from PIL import Image, ImageDraw, ImageFont
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGB")
    dr, k = ImageDraw.Draw(img), dpi / 72.0
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    for f in res["files"]:
        for lk in f.get("locks", []):
            if "pts" not in lk:
                continue
            col = (20, 160, 60) if lk.get("verified") else (240, 130, 20)
            p = [(x * k, y * k) for x, y in lk["pts"]]
            if lk["kind"] == "region":
                dr.rectangle([min(p[0][0], p[1][0]), min(p[0][1], p[1][1]), max(p[0][0], p[1][0]), max(p[0][1], p[1][1])],
                             outline=(40, 90, 220), width=3)
                dr.text((min(p[0][0], p[1][0]) + 6, min(p[0][1], p[1][1]) + 4), str(lk["element_id"]), fill=(40, 90, 220), font=font)
                continue
            if lk["kind"] == "segment":
                dr.line(p, fill=col, width=4)
                dr.text(((p[0][0] + p[1][0]) / 2 + 3, (p[0][1] + p[1][1]) / 2 - 18), str(lk["element_id"]), fill=col, font=font)
            else:
                x, y = p[0]
                dr.rectangle([x - 7, y - 7, x + 7, y + 7], outline=(200, 30, 160), width=3)
                dr.text((x + 9, y - 20), str(lk["element_id"]), fill=(200, 30, 160), font=font)
    img.save(path)


# ---------- วัด ----------
def vector_houses():
    import gridlab_probe as G
    out = []
    for d in sorted((ROOT / "image").iterdir()):
        if (d / f"{d.name}.pdf").exists() and house_dir(d.name) and G.plan_pages(d.name):
            out.append(d.name)
    return out


def evaluate(houses=None, per_house=2, ocr=True):
    import fitz
    import gridlab_probe as G
    houses = houses or vector_houses()[::6]
    tot = collections.Counter()
    sums = collections.defaultdict(list)
    for h in houses:
        d = house_dir(h)
        pages = [pn for pn in G.plan_pages(h) if element_files(d, pn)][:per_house]
        for pn in pages:
            r = run_page(h, pn, ocr=ocr, write=False)
            if r.get("error"):
                tot["pages_" + r["error"]] += 1
                print(f"{h:26s} p{pn:<3d} {r['error']} {r.get('why')}", flush=True)
                continue
            tot["pages_ok"] += 1
            for f in r["files"]:
                if "verify" not in f:
                    continue
                v = f["verify"]
                tot["elements"] += f["elements"]
                tot["locked"] += f["locked"]
                tot["unresolved"] += f["unresolved"]
                tot["no_ref"] += f["no_ref"]
                tot["regions"] += sum(lk.get("kind") == "region" and "pts" in lk for lk in f["locks"])
                tot["weak_files"] += bool(f["weak"])
                tot["files"] += 1
                for key, n_key in (("points_hit", "points"), ("beams_ok", "beams"), ("control_points_hit", "control_points"),
                                   ("control_bays_ok", "control_bays")):
                    if v[key] is not None:
                        sums[key].append((v[key], v[n_key]))
                print(f"{h:26s} p{pn:<3d} {f['pattern']:13s} plan={f['plan']} score={f['score']:.2f}{' WEAK' if f['weak'] else ''} "
                      f"elem={f['elements']:3d} ล็อก={f['locked']:3d} ไม่resolve={f['unresolved']} ไม่มีref={f['no_ref']} "
                      f"จุด {v['points_hit']}/{v['points']} (คุม {v['control_points_hit']}/{v['control_points']}) "
                      f"คาน {v['beams_ok']}/{v['beams']} (คุม {v['control_bays_ok']}/{v['control_bays']})", flush=True)
    w = lambda k: (sum(r * n for r, n in sums[k]) / max(sum(n for _, n in sums[k]), 1)) if sums[k] else None
    print("รวม:", dict(tot))
    for k in ("points_hit", "control_points_hit", "beams_ok", "control_bays_ok"):
        print(f"  {k}: {w(k) if w(k) is None else round(w(k), 3)} (n={sum(n for _, n in sums[k])})")


def demo():
    xs, ys = {"1", "2", "3", "4", "1'"}, {"A", "B", "C", "A'"}
    assert split_ref("A1", xs, ys) == ("1", "A") and split_ref("1-A", xs, ys) == ("1", "A")
    assert split_ref("B 3", xs, ys) == ("3", "B") and split_ref("A'1", xs, ys) == ("1", "A'")
    assert split_ref("A1'", xs, ys) == ("1'", "A") and split_ref("Z9", xs, ys) is None and split_ref("A", xs, ys) is None
    assert split_ref("", xs, ys) is None and split_ref(None, xs, ys) is None
    assert split_ref("A11", xs | {"11"}, ys) == ("11", "A")                               # ไม่สับสนกับ A1 + 1
    assert split_ref("A11", {"1", "11"}, {"A", "A1"}) is None                          # A+11 หรือ A1+1: กำกวม = ไม่เดา
    f = fit_axis([(0.0, 207.9), (3.0, 313.2), (6.0, 418.3), (9.0, 523.4)])
    assert f and abs(f[0] - 35.1) < 0.05 and abs(f[1] - 207.9) < 0.1 and f[2] == 4
    assert fit_axis([(0.0, 500.0), (2.0, 430.0), (4.0, 360.0)])[0] < 0                    # แกนกลับด้านได้
    assert fit_axis([(0.0, 10.0), (0.0, 12.0)]) is None and fit_axis([(1.0, 5.0)]) is None
    assert fit_axis([(0.0, 0.0), (3.0, 105.0), (6.0, 210.0), (9.0, 400.0)]) is None       # ชื่อผิดหนึ่งเส้น = ทิ้งทั้งแปลน
    ids = ["1", "2", "3", "4"]
    assert bays(ids, "1", "3") == [("1", "2"), ("2", "3")] and bays(ids, "4", "3") == [("3", "4")] and bays(ids, "1", "9") == []
    # คาน: เส้นขอบ 2 เส้นห่างแกน 8 pt ทั้งสองข้าง -> คลุมทั้งช่วง; ไม่มีเส้น = 0; เส้นบนแกนเอง (ระยะ 0 = เส้นกริด) ไม่นับ; เส้นห่างเกิน band ไม่นับ
    p0, p1 = (100.0, 200.0), (300.0, 200.0)
    edges = [(90.0, 192.0, 310.0, 192.0), (90.0, 208.0, 310.0, 208.0)]
    assert cover_fraction(p0, p1, edges, 14) == 1.0 and cover_fraction(p0, p1, [], 14) == 0.0
    assert cover_fraction(p0, p1, [(90.0, 200.0, 310.0, 200.0)], 14) == 0.0
    assert cover_fraction(p0, p1, [(90.0, 150.0, 310.0, 150.0)], 14) == 0.0
    assert cover_fraction(p0, p1, [(90.0, 192.0, 200.0, 192.0)], 14) == 0.5 or 0.4 < cover_fraction(p0, p1, [(90.0, 192.0, 200.0, 192.0)], 14) < 0.7
    assert cover_fraction(p0, p1, [(150.0, 150.0, 150.0, 250.0)], 14) == 0.0              # ตั้งฉากไม่นับ
    assert cover_fraction(p0, p1, [(90.0, 192.0, 310.0, 208.0)], 14) == 0.0               # เฉียงเกิน 3° ไม่นับ (ขนานเท่านั้น)
    assert cover_fraction(p0, p1, [(90.0, 192.0, 310.0, 192.0)], 14) == 1.0 and cover_fraction(p0, p1, [(90.0, 215.0, 310.0, 215.0)], 14) == 0.0   # ห่างเกิน band ไม่นับ (14 pt)
    assert cover_fraction(p0, p1, [(90.0, 215.0, 310.0, 215.0)], 20) == 1.0               # band กว้างขึ้นจึงนับ
    # จุด: รูปปิดขนาดพอดีครอบจุด; ท่อนเส้นประบาง (ด้านสั้น < 2.5 pt) ไม่นับ; รูปใหญ่เกินไม่นับ
    assert point_hit((50, 50), [(40, 40, 62, 60)], 90) and not point_hit((50, 50), [(48, 49, 70, 50.5)], 90)
    assert not point_hit((50, 50), [(0, 0, 400, 300)], 90) and not point_hit((200, 200), [(40, 40, 62, 60)], 90)
    # box_around: เส้นแยกท่อนครบ 4 ด้านล้อมจุด = อยู่ในกล่อง; ขาดด้านเดียว/เส้นกริดผ่านจุด/ไกลเกิน = ไม่ใช่
    sq = [(40.0, 40.0, 60.0, 40.0), (40.0, 60.0, 60.0, 60.0), (40.0, 40.0, 40.0, 60.0), (60.0, 40.0, 60.0, 60.0)]
    assert box_around((50.0, 50.0), sq, 40) and not box_around((50.0, 50.0), sq[:3], 40) and not box_around((50.0, 50.0), sq[1:], 40)
    assert not box_around((50.0, 50.0), [(0.0, 50.0, 100.0, 50.0), (50.0, 0.0, 50.0, 100.0)], 40)       # เส้นกริดผ่านจุดเองไม่ใช่ขอบกล่อง
    assert not box_around((50.0, 50.0), [sq[0], sq[2], sq[3], (0.0, 50.0, 100.0, 50.0)], 40)           # ด้านล่างขาด แต่มีเส้นกริดผ่านจุด: ห้ามนับแทนขอบ
    assert not box_around((50.0, 50.0), sq, 8) and not box_around((200.0, 200.0), sq, 400)                 # ขอบไกลเกิน half_max / จุดอยู่นอกกล่อง
    assert not box_around((70.0, 50.0), sq, 40)                                                            # จุดอยู่นอกกล่อง (เกินด้านขวา)
    assert near([(0, 0, 10, 0), (500, 500, 510, 500)], (5, 5), 20) == [(0, 0, 10, 0)]
    # หน้า /Rotate: get_drawings ให้พิกัดก่อนหมุน ต้องแปลงเป็นพิกัดที่ตามองเห็น (ก่อนแก้ ตรวจบนภาพวาดพลาดทุกหน้าหมุน)
    import fitz
    doc = fitz.open()
    pg = doc.new_page(width=842, height=595)
    pg.draw_rect(fitz.Rect(100, 50, 200, 150), color=(0, 0, 0))
    pg.draw_line((300, 400), (500, 400), color=(0, 0, 0))
    pg.set_rotation(90)
    pcs, bxs = drawn_things(pg)
    want = fitz.Rect(100, 50, 200, 150) * pg.rotation_matrix
    assert any(abs(b[0] - want.x0) < 0.01 and abs(b[1] - want.y0) < 0.01 and abs(b[2] - want.x1) < 0.01 and abs(b[3] - want.y1) < 0.01 for b in bxs), (bxs, want)
    assert all(0 <= b[0] <= pg.rect.width + 0.01 and 0 <= b[3] <= pg.rect.height + 0.01 for b in bxs)
    vis = fitz.Point(300, 400) * pg.rotation_matrix
    assert any(abs(q[0] - vis.x) < 0.01 and abs(q[1] - vis.y) < 0.01 or abs(q[2] - vis.x) < 0.01 and abs(q[3] - vis.y) < 0.01 for q in pcs)
    assert len([q for q in pcs if q[2] - q[0] == 100 or q[3] - q[1] == 100]) >= 2       # ขอบสี่เหลี่ยมถูกนับเป็นท่อนเส้นด้วย
    # lock: คาน/จุด/ref เสีย/ไม่มี ref
    assert split_region("A-B x 1-2", xs, ys) == (("1", "2"), ("A", "B")) and split_region("1-2 x A-B", xs, ys) == (("1", "2"), ("A", "B"))
    assert split_region("A-Z x 1-2", xs, ys) is None and split_region("A1", xs, ys) is None and split_region(None, xs, ys) is None
    assert split_region("A-C × 2-4", xs, ys) == (("2", "4"), ("A", "C"))
    master = {"x": {"1": 0.0, "2": 3.0}, "y": {"A": 0.0, "B": 2.0}, "dummy": set()}
    tf = {"x": (35.0, 100.0, 2, 0.0), "y": (35.0, 50.0, 2, 0.0)}
    ls = lock_elements([dict(element_id="B1", element_type="beam", grid_ref_start="A1", grid_ref_end="A2"),
                        dict(element_id="F1", element_type="footing", grid_refs=["A1", "B2", "Q9"]),
                        dict(element_id="S1", element_type="slab"), dict(element_id="B9", grid_ref_start="A1", grid_ref_end="Z9")],
                       tf, master)
    assert ls[0]["pts"] == [(100.0, 50.0), (205.0, 50.0)] and ls[1]["pts"] == [(100.0, 50.0)] and ls[2]["pts"] == [(205.0, 120.0)]
    assert ls[3].get("status") == "unresolved_ref" and ls[4]["status"] == "no_grid_ref" and ls[5]["status"] == "unresolved_ref"
    rg = lock_elements([dict(element_id="S1", element_type="slab", grid_refs=["A-B x 1-2", "A-Z x 1-2"])], tf, master)
    assert rg[0]["kind"] == "region" and rg[0]["pts"] == [(100.0, 50.0), (205.0, 120.0)] and rg[1]["status"] == "unresolved_ref"
    gi = grid_input(tf, master)
    assert [r["id"] for r in gi] == ["1", "2", "A", "B"] and gi[1]["pos_pt"] == 205.0 and gi[1]["pos_px"] == round(205.0 * 200 / 72, 1)
    assert score(dict(points=3, points_hit=1.0, beams=1, beams_ok=0.0)) == 0.75 and score(dict(points=0, beams=0)) == 0.0
    assert score(dict(points=0, points_hit=None, beams=2, beams_ok=1.0)) == 1.0 and score(dict(points=1, points_hit=0.0, beams=3, beams_ok=1.0)) == 0.75
    # แกน y ใช้สเกลของตัวเอง ไม่ใช่ของแกน x (สองแกนสเกลต่างกันได้เมื่อ fit จากเส้นต่างกัน) และ y กลับด้านได้
    tf2 = {"x": (35.0, 100.0, 2, 0.0), "y": (-20.0, 300.0, 2, 0.0)}
    assert to_pt(tf2, "2", "B", master) == (205.0, 260.0) and to_pt(tf2, "1", "A", master) == (100.0, 300.0)
    print("OK — self-check ผ่าน (กฎ split_ref/fit/bays/cover/point/lock เท่านั้น ไม่ได้เทียบกับ PDF จริง ใช้ --eval)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("args", nargs="*")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if a.eval:
        return evaluate(a.args or None, ocr=not a.no_ocr)
    if len(a.args) != 2:
        return ap.print_help()
    r = run_page(a.args[0], int(a.args[1]), ocr=not a.no_ocr)
    print(json.dumps({k: v for k, v in r.items() if k != "files"} | {"files": [
        {k: v for k, v in f.items() if k != "locks"} for f in r["files"]]}, ensure_ascii=False, indent=1, default=str)[:3500])


if __name__ == "__main__":
    main()
