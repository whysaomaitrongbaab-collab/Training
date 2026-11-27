#!/usr/bin/env python3
"""level_marks.py - Leveling, triangle first (meeting 2026-11-25): find the level marks (▽ + level number + name) that
elevations / sections print, read each one, and build the house's level master from them.

    python tools/level_marks.py <house> [--pages 5-20] [--no-ocr]   # one house: every vector page -> level master JSON
    python tools/level_marks.py <house> --page 8 [--show]            # one page: the marks and what was read (+ PNG)
    python tools/level_marks.py --pdf "path/to/any.pdf"               # any PDF (e.g. a STECON set), output folder = file name
    python tools/level_marks.py --plan-tags STRUCT.pdf --levels ../logic_test_out/<set>/level_marks.json
                                                     # '(+9.00)' slab tags on the structural plans -> floor per plan page
    python tools/level_marks.py --eval [N] [--cache f.json]           # GT pages of every Nth GT house (see evaluate)
    python tools/level_marks.py --demo                                # self-check (no PDF, no OCR)
    add --ocr both|openthai to any reading command (OpenThai OCR, see OCR engines below; run with the openthai venv)

Why triangles (King, 25 Nov): a printed level on an elevation / section always sits next to a ▽ on a level line.
Reading only around the ▽ keeps dimensions (also "d.dd") out, lets the crop be rendered at a much higher resolution than a
whole page (whole-page OCR is capped at ~3300 px, so text is ~14 px high), and gives the number and its name in one strip.

MARK (vector pages, `find_marks`, pure): three straight strokes that close into a triangle with
  - one horizontal edge on top and the apex below it (▽, empty or filled ▼), isosceles: apex within 0.2 base of the middle
    (a square with an X in it makes right / flat triangles: apex over a corner, or height = base / 2 - both rejected);
  - height / base 0.6-1.25 and base 2.5-15 pt;
  - nothing drawn inside (a ▽ with a digit in it is a finish / section tag; the triangles on walls in elevations are △ with
    a digit, they point up and carry one - "ระวังสามเหลี่ยมกำแพง", meeting 25 Nov).
  A level line is NOT required: measured on the GT pages, many real marks have the line under the text, not at the apex.
READ (`ocr_strip` = OCR, cacheable; `interpret` = pure): strip from 3 bases left of the ▽ to 30 bases right of it, 1.2
  base above the top edge to 0.8 below the apex, rendered at ~400 dpi; numbers from BOTH readers (the Latin one reads
  '±0.00' as '±O.00'), names from the Thai reader (levelarm_probe.bind_names). The number must sit on the ▽'s own row and
  start within 4 bases right of it (or end within 4 bases left), or within 4 bases past a 'ระดับ...' name that starts at
  the ▽ ('▽ ระดับพื้นชั้นบน +2.60'). A ▽ with neither a number nor a 'ระดับ...' name next to it is dropped (not a level
  mark). A name without a number is kept with level_m None (`name_without_number`); `fill_by_name` gives it the value
  that marks with the same name carry elsewhere in the house when those agree (`value_from_same_name`).
CIRCLE (`find_circle_marks`): STECON (and many plans) print a circle with two opposite quarters filled on the level line,
  name above it, value below ('ระดับพื้นชั้นที่ 5' / 'FFL.+19.50') - read with a taller strip, same rules otherwise.
LEVEL MASTER: z_levels register = pass3_grid.build_level_master (one vote per mark); floors = assemble_floors (spec
  codes B* F* F*M RF RF2, floor names with 'พื้น' first, tie = level_m None + candidates, never guessed) -> same JSON
  shape as pass3_grid's proj_grid level_master. level_link.py --level-master <this file> joins plan views to it.

Output: ../logic_test_out/<house>/level_marks.json (outside the repo). Reads PDFs and the GT only; calls no model.
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(ROOT, "image")
GT = os.path.join(ROOT, "json_แก้ไขแล้ว")
DEFAULT_OUT = os.path.join(os.path.dirname(ROOT), "logic_test_out")
PAGE_RE = re.compile(r"หน้า(\d+)")

SNAP = 0.35            # pt: two stroke ends closer than this are one corner
BASE_MIN, BASE_MAX = 2.5, 15.0
RATIO_MIN, RATIO_MAX = 0.6, 1.25
APEX_OFF = 0.2         # apex x within this share of the base from the middle
READ_DPI = 400
NUM_REACH = 4.0        # bases: how far from the ▽ the number may start / end
NAME_LEFT = 4.0        # bases: how far left of the ▽ a joined name box may start
# sign may follow a prefix like 'FFL.' (STECON: 'FFL.+19.50'), so only a digit (or digit + point) before it is refused
LEVEL_NUM = re.compile(r"(?<!\d)(?<!\d[.,])([+\-−–±]?)(\d{1,2})[.,](\d{2})\d?(?![\d.])")
CIRCLE_D_MIN, CIRCLE_D_MAX = 3.0, 14.0   # pt: diameter of the quartered datum circle (STECON 6.96)
LEVEL_WORD = re.compile(r"ระ[ดตคศ][ัิี]?บ")       # 'ระดับ' + reader slips: ระตับ ระคับ (Paddle), ระดีบ ระดิบ (OpenThai)
# the Latin reader reads '±0.00' as '±O.00' (measured): an O right after a sign, right before '.d', or in the decimals
OH_ZERO = re.compile(r"(?<=[+\-−–±])[Oo]|[Oo](?=[.,][\dOo])|(?<=[.,])[Oo]|(?<=[.,]\d)[Oo]")
PERSON = re.compile(r"^\W*(นาย|นาง|น\.ส\.)")              # never keep a person's name in a cache file


# ---------------- geometry (pure) ----------------

def _cluster(points, tol=SNAP):
    """points -> (node id per point, node coordinates); greedy, grid-bucketed"""
    nodes, grid, ids = [], defaultdict(list), []
    cell = 2 * tol
    for x, y in points:
        gx, gy = int(x // cell), int(y // cell)
        hit = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for k in grid[(gx + dx, gy + dy)]:
                    if abs(nodes[k][0] - x) <= tol and abs(nodes[k][1] - y) <= tol:
                        hit = k
                        break
                if hit is not None:
                    break
            if hit is not None:
                break
        if hit is None:
            nodes.append((x, y))
            hit = len(nodes) - 1
            grid[(gx, gy)].append(hit)
        ids.append(hit)
    return ids, nodes


def _inside(px, py, tri, shrink):
    """point strictly inside the triangle shrunk toward its centroid by `shrink` (share)"""
    (ax, ay), (bx, by), (cx, cy) = tri
    gx, gy = (ax + bx + cx) / 3, (ay + by + cy) / 3
    a = (gx + (ax - gx) * (1 - shrink), gy + (ay - gy) * (1 - shrink))
    b = (gx + (bx - gx) * (1 - shrink), gy + (by - gy) * (1 - shrink))
    c = (gx + (cx - gx) * (1 - shrink), gy + (cy - gy) * (1 - shrink))

    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2, d3 = side(a, b, (px, py)), side(b, c, (px, py)), side(c, a, (px, py))
    return (d1 > 0 and d2 > 0 and d3 > 0) or (d1 < 0 and d2 < 0 and d3 < 0)


def find_marks(segs, ink=()):
    """segs = [(x0, y0, x1, y1)] straight strokes in display coordinates (y down); ink = [(x, y)] every drawn point of the
    page (stroke ends, curve points) for the empty-inside test. -> [dict(x0, x1, top, apex_x, apex_y, base, height)]"""
    ends = []
    keep = []
    for s in segs:
        L = ((s[2] - s[0]) ** 2 + (s[3] - s[1]) ** 2) ** 0.5
        if 1.0 <= L <= BASE_MAX * 1.8:
            keep.append(s)
            ends += [(s[0], s[1]), (s[2], s[3])]
    ids, nodes = _cluster(ends)
    adj = defaultdict(set)
    edges = []
    for i, s in enumerate(keep):
        a, b = ids[2 * i], ids[2 * i + 1]
        if a != b:
            adj[a].add(b)
            adj[b].add(a)
            edges.append((a, b))
    ink_grid = defaultdict(list)
    for x, y in ink:
        ink_grid[(int(x // 4), int(y // 4))].append((x, y))
    seen, out = set(), []
    for a, b in edges:
        (ax, ay), (bx, by) = nodes[a], nodes[b]
        if abs(ay - by) > 0.25:
            continue
        base = abs(bx - ax)
        if not BASE_MIN <= base <= BASE_MAX:
            continue
        x0, x1, top = min(ax, bx), max(ax, bx), (ay + by) / 2
        for c in adj[a] & adj[b]:
            cx, cy = nodes[c]
            h = cy - top
            if h <= 0 or not RATIO_MIN <= h / base <= RATIO_MAX or abs(cx - (x0 + x1) / 2) > APEX_OFF * base:
                continue
            key = (round(x0, 1), round(top, 1), round(base, 1))
            if key in seen:
                continue
            seen.add(key)
            tri = ((x0, top), (x1, top), (cx, cy))
            busy = False
            for gx in range(int(x0 // 4) - 1, int(x1 // 4) + 2):
                for gy in range(int(top // 4) - 1, int(cy // 4) + 2):
                    for px, py in ink_grid.get((gx, gy), ()):
                        if _inside(px, py, tri, 0.15):   # shrunk 15%: the outline's own points never count
                            busy = True
                            break
                    if busy:
                        break
                if busy:
                    break
            if not busy:
                out.append(dict(kind="tri", x0=round(x0, 2), x1=round(x1, 2), top=round(top, 2), apex_x=round(cx, 2),
                                apex_y=round(cy, 2), base=round(base, 2), height=round(h, 2)))
    return _dedupe(out)


def find_circle_marks(circles, fills):
    """the other level symbol (STECON, and plans of many drafters): a circle with two opposite quarters filled, the
    level line through its centre. circles = [(cx, cy, d)] (gridlab_probe.circles); fills = [(x0, y0, x1, y1, [(x, y)])]
    dark filled paths with their vertices. A circle counts when a filled path lies inside it and has a vertex on its
    centre (a quarter wedge) - grid bubbles and plain circles have none. -> marks shaped like find_marks' (box = circle)"""
    out = []
    for cx, cy, d in circles:
        if not CIRCLE_D_MIN <= d <= CIRCLE_D_MAX:
            continue
        r = d / 2
        tol = max(0.6, 0.15 * d)
        wedge = any(fx0 >= cx - r - tol and fx1 <= cx + r + tol and fy0 >= cy - r - tol and fy1 <= cy + r + tol
                    and any(abs(x - cx) <= tol and abs(y - cy) <= tol for x, y in pts)
                    for fx0, fy0, fx1, fy1, pts in fills)
        if wedge:
            out.append(dict(kind="circle", x0=round(cx - r, 2), x1=round(cx + r, 2), top=round(cy - r, 2),
                            apex_x=round(cx, 2), apex_y=round(cy + r, 2), base=round(d, 2), height=round(d, 2)))
    return out


def _dedupe(marks):
    """one ▽ drawn twice (fill + stroke, or an inner and outer outline) -> keep the larger"""
    marks = sorted(marks, key=lambda m: -m["base"])
    out = []
    for m in marks:
        cx, cy = (m["x0"] + m["x1"]) / 2, (m["top"] + m["apex_y"]) / 2
        if any(abs(cx - (o["x0"] + o["x1"]) / 2) <= o["base"] / 2 and abs(cy - (o["top"] + o["apex_y"]) / 2) <= o["height"] / 2
               for o in out):
            continue
        out.append(m)
    return sorted(out, key=lambda m: (m["top"], m["x0"]))


def clean_ocr(text):
    """reader quirks, before parsing: spaces inside a number ('+ 0.20', '0 .60') joined; '±' read as a sign pair ('-+0.00',
    '+-0.60', OpenThai) -> '±'; the ▽ glyph read as a leading '7' / 'Y' / 'V' glued to the sign ('7+3.75') dropped;
    a letter O inside a number -> 0 (Paddle's Latin reader: '±O.00'). Spaces elsewhere are kept, so '7 +3.75' (▽, then
    the level) does not turn into the digit run '7+3.75'."""
    t = re.sub(r"\+\s*[-−–]|[-−–]\s*\+", "±", text)
    t = re.sub(r"(?:^|(?<=\s))[7YVv∇▽]\s*(?=[+\-−–±]\s*[\dOoIl])", "", t)
    # after a sign, letters that look like digits are digits and spaces inside the number go: '+O. IO' -> '+0.10'
    t = re.sub(r"([+\-−–±])\s*([\dOoIl][\dOoIl ]{0,3}[.,] ?[\dOoIl]{2}\d?)",
               lambda m: m.group(1) + m.group(2).translate(str.maketrans("OoIl", "0011", " ")), t)
    t = re.sub(r"(?<=\d)\s*([.,])\s*(?=\d)", r"\1", t)
    return OH_ZERO.sub("0", t)


def parse_number(text):
    """OCR text -> [value_m] of level-looking numbers ('+3.75', '±0.00', '-1.50', '0.00'); unsigned only for 0.00 (a datum
    the reader often prints without its ±) - an unsigned 3.20 next to a ▽ is too often a dimension of the same row.
    '±' with a non-zero value counts as + (only 0.00 is printed with ±; a sign pair before +0.60 is reader noise)."""
    out = []
    for sign, whole, frac in LEVEL_NUM.findall(clean_ocr(text)):
        v = float(f"{whole}.{frac}")
        if not sign and v != 0:
            continue
        out.append(-v if sign and sign in "-−–" else v)
    return out


def pick_number(mark, nums, scale, name_boxes=()):
    """nums = [(value_m, box px)] in the strip (box relative to the strip; strip px = (pt - strip origin) x scale) ->
    the number on the ▽'s row nearest to it within NUM_REACH bases, or None. strip origin is passed in mark['_o'].
    Layout '▽ ระดับพื้นชั้นบน +2.60' (name between the mark and its number, ~15-20 bases away - 2ชั้น_08, ใหญ่_2ชั้น_01):
    a 'ระดับ...' box (name_boxes) on the row that starts within 6 bases of the ▽ extends the reach to NUM_REACH bases
    past its own right end."""
    ox, oy = mark["_o"]
    b = mark["base"] * scale
    tx0, tx1 = (mark["x0"] - ox) * scale, (mark["x1"] - ox) * scale
    ty0, ty1 = (mark["top"] - oy) * scale, (mark["apex_y"] - oy) * scale

    def on_row(y0, y1):
        return ty0 - 0.6 * b <= (y0 + y1) / 2 <= ty1 + 0.6 * b
    reach_end = tx1
    for x0, y0, x1, y1 in name_boxes:
        # the detector often joins the ▽ glyph, and OpenThai even the dashed level line left of it ('1– V ระดับ...'),
        # to the name: the name box may start up to NAME_LEFT bases left of the ▽
        if on_row(y0, y1) and tx0 - NAME_LEFT * b <= x0 <= tx1 + 6 * b:
            reach_end = max(reach_end, x1)
    best = None
    for v, (x0, y0, x1, y1) in nums:
        if not on_row(y0, y1):
            continue
        gap = x0 - tx1 if x0 >= tx0 else tx0 - x1
        if gap > NUM_REACH * b and not (x0 >= tx0 and x0 - reach_end <= NUM_REACH * b):
            continue
        if best is None or gap < best[0]:
            best = (gap, v)
    return None if best is None else best[1]


# ---------------- PDF / OCR (impure) ----------------

def page_geometry(page):
    """display-space straight strokes + every drawn point (for the empty-inside test) + circles + dark filled paths"""
    import gridlab_probe as G
    rm = page.rotation_matrix
    drawings = page.get_drawings()
    segs, ink, fills = [], [], []
    for d in drawings:
        f = d.get("fill")
        if f and sum(f) / len(f) < 0.5:
            pts = []
            for it in d["items"]:
                pts += [(q * rm) for q in it[1:] if hasattr(q, "x")]
            if pts:
                xs, ys = [p.x for p in pts], [p.y for p in pts]
                fills.append((min(xs), min(ys), max(xs), max(ys), [(p.x, p.y) for p in pts]))
        for it in d["items"]:
            op = it[0]
            if op == "l":
                a, b = it[1] * rm, it[2] * rm
                segs.append((a.x, a.y, b.x, b.y))
                ink += [(a.x, a.y), (b.x, b.y), ((a.x + b.x) / 2, (a.y + b.y) / 2)]
            elif op == "c":
                ink += [(p.x, p.y) for p in (q * rm for q in it[1:5])]
            elif op == "re":
                r = it[1] * rm
                r.normalize()
                segs += [(r.x0, r.y0, r.x1, r.y0), (r.x1, r.y0, r.x1, r.y1), (r.x1, r.y1, r.x0, r.y1), (r.x0, r.y1, r.x0, r.y0)]
                ink += [(r.x0, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x1, r.y0)]
            elif op == "qu":
                q = it[1]
                ink += [(p.x, p.y) for p in (q.ul * rm, q.ur * rm, q.ll * rm, q.lr * rm)]
    return segs, ink, G.circles(page, drawings), fills


def strip_of(page, mark):
    """▽: text on the mark's own row. Circle: name above the level line and the value below it (STECON) -> taller strip"""
    import fitz
    b = mark["base"]
    up, down = (1.2 * b, 0.8 * b) if mark.get("kind", "tri") == "tri" else (1.4 * b, 1.4 * b)
    r = fitz.Rect(mark["x0"] - 3 * b, mark["top"] - up, mark["x1"] + 30 * b, mark["apex_y"] + down) & page.rect
    return r


def render(page, rect, dpi=READ_DPI):
    import numpy as np
    pix = page.get_pixmap(clip=rect, dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    img = img[:, :, :3] if pix.n >= 3 else np.repeat(img, 3, axis=2)
    return np.ascontiguousarray(img), pix.width / max(rect.width, 1e-6)


# ---- OCR engines: paddle (default; titleblock_extract's two PaddleOCR readers) | openthai | both ----
# OpenThai = iApp OpenThai2.1-OCR-Text v2.1.4 (Apache-2.0, ONNX, CPU; downloaded to OPENTHAI_DIR, not in the repo).
# It needs onnxruntime, installed only in the venv next to it: run this file with
#   "D:\00mk\steel project\training\openthai_ocr\venv\Scripts\python.exe" tools/level_marks.py ... --ocr both
# Measured 2026-11-26 on the 324 marks of the GT eval (same strips, same rules): Paddle 109/180 printed levels on
# vector pages, 98% of read values real, 30 floors right; OpenThai 108/180, 96%, 32 floors, 57 ms per strip (~100x
# faster); both (OpenThai first, Paddle where OpenThai has no number or a number read only once in the house)
# 113/180, 98%, 32 floors, 0 wrong. OpenThai reads scans badly (whole pages: vector 79%, scans 22%).
OPENTHAI_DIR = os.environ.get("OPENTHAI_OCR_DIR", os.path.join(os.path.dirname(ROOT), "openthai_ocr", "model_v2.1.4"))
_OT = {}


def openthai(px_limit=1280):
    """the OpenThai reader for one detector size (cached); nothing dropped by its own confidence filter"""
    if px_limit not in _OT:
        if OPENTHAI_DIR not in sys.path:
            sys.path.insert(0, OPENTHAI_DIR)
        try:
            from runtime.line_engine import LineOCR
            _OT[px_limit] = LineOCR(OPENTHAI_DIR, threads=int(os.environ.get("OPENTHAI_THREADS", "4")),
                                    det={"limit": px_limit}, rec={"drop_below": 0.0, "junk_below": 0.0, "min_chars": 1})
        except ImportError as e:
            raise SystemExit(f"OpenThai OCR not available ({e}). Model folder: {OPENTHAI_DIR}; run with the venv python "
                             "that has onnxruntime: D:\\00mk\\steel project\\training\\openthai_ocr\\venv\\Scripts\\python.exe")
    return _OT[px_limit]


def ot_lines(img_rgb, px_limit=1280):
    """RGB image -> [[text, [x0, y0, x1, y1]]] read by OpenThai (its 4-corner boxes made axis-aligned)"""
    import numpy as np
    r = openthai(px_limit).read(np.ascontiguousarray(img_rgb[:, :, ::-1]))
    out = []
    for ln in r["lines"] + r.get("dropped", []):
        xs, ys = [p[0] for p in ln["box"]], [p[1] for p in ln["box"]]
        if ln["text"] and not PERSON.search(ln["text"]):
            out.append([ln["text"], [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]])
    return out


def ocr_strip(page, mark, engine="paddle"):
    """OCR the strip of one ▽ -> rec (cacheable: strip origin, px per pt, the two line lists). Paddle: Latin reader for
    numbers + Thai reader for names; OpenThai: one reader, its lines fill both slots. Thai lines that look like a
    person's name are dropped here, so a cache never holds one. (engine 'both' is decided per house in run_house.)"""
    rect = strip_of(page, mark)
    if rect.is_empty or rect.width < 2 or rect.height < 2:
        return dict(o=None, scale=0, lat=[], th=[])
    img, scale = render(page, rect)
    if engine == "openthai":
        lines = ot_lines(img)
        return dict(o=[rect.x0, rect.y0], scale=scale, lat=lines, th=lines, engine="openthai")
    import levelarm_probe as L
    import titleblock_extract as T
    lat = [[t, b] for t, b in L._ocr(img, T._reader())]
    th = [[t, b] for t, b in L._ocr(img, T._reader_th()) if not PERSON.search(t)]
    return dict(o=[rect.x0, rect.y0], scale=scale, lat=lat, th=th)


def interpret(mark, rec):
    """mark + its OCR rec -> mark with value_m / name / flags, or None when the ▽ has neither a level number nor a
    'ระดับ...' name next to it (pure: re-scoring a cache needs no OCR). Numbers come from BOTH readers - the Latin one
    reads '±0.00' as '±O.00' and the Thai one often gets it right (measured on 1ชั้น_01 p22)."""
    import levelarm_probe as L
    if not rec.get("o"):
        return None
    m = dict(mark, _o=tuple(rec["o"]))
    scale = rec["scale"]
    nums = []
    for t, b in rec["lat"] + rec["th"]:
        for v in parse_number(t):
            if (v, tuple(b)) not in nums:
                nums.append((v, tuple(b)))
    name_boxes = [tuple(b) for t, b in rec["th"] if LEVEL_WORD.search(t)]
    value = pick_number(m, nums, scale, name_boxes)
    th = [(t, list(b)) for t, b in rec["th"]]
    flags, name = [], None
    if value is not None:
        box = next(list(b) for v, b in nums if v == value)
        hits = L.bind_names([(value, box)], th)
        name = hits[0][1] if hits else None
        if name and not LEVEL_WORD.search(name) and not L.floor_of(name):
            alt = row_name(m, th, scale)
            if alt:
                name = alt
            else:
                flags.append("name_unsure")
    if name is None:
        name = row_name(m, th, scale)
    if value is None and name is None:
        return None
    if value is None:
        flags.append("name_without_number")
    out = {k: v for k, v in m.items() if k != "_o"}
    out.update(value_m=value, name=name, flags=flags)
    return out


def row_name(mark, th, scale):
    """a 'ระดับ...' name on the ▽'s own row right of it (name-only marks, or when the bound name is not a level name)"""
    import levelarm_probe as L
    ox, oy = mark["_o"]
    b = mark["base"] * scale
    ty0, ty1, tx1 = (mark["top"] - oy) * scale, (mark["apex_y"] - oy) * scale, (mark["x1"] - ox) * scale
    tx0 = (mark["x0"] - ox) * scale
    for txt, (x0, y0, x1, y1) in sorted(th, key=lambda t: t[1][0]):
        if x0 < tx0 - NAME_LEFT * b or x0 > tx1 + 6 * b or not ty0 - 0.6 * b <= (y0 + y1) / 2 <= ty1 + 0.6 * b:
            continue
        nm = L.level_name(txt)
        if nm and LEVEL_WORD.search(txt):
            return nm
    return None


def page_marks(page, ocr=True, keep_ocr=False, engine="paddle"):
    """-> read marks (or bare geometry when ocr=False). keep_ocr=True returns [(mark, rec)] for a cache instead.
    engine 'both' reads with OpenThai here; run_house re-reads the doubtful marks with Paddle."""
    segs, ink, circles, fills = page_geometry(page)
    marks = find_marks(segs, ink) + find_circle_marks(circles, fills)
    if not ocr:
        return marks
    pairs = [(m, ocr_strip(page, m, "openthai" if engine == "both" else engine)) for m in marks]
    if keep_ocr:
        return pairs
    return [r for r in (interpret(m, rec) for m, rec in pairs) if r]


LEVEL_LIKE = re.compile(r"\d\s*[.,]\s*\d|[OoIl]\s*[.,]\s*\d")


def level_like(rec):
    """does the OCR of a strip hold anything a level could come from (a decimal number, or the word 'ระดับ')?"""
    txt = " ".join(t for t, _ in rec.get("lat", []))
    return bool(LEVEL_LIKE.search(txt) or LEVEL_WORD.search(txt))


def doubtful(reads, recs=None):
    """'both': which OpenThai reads Paddle should redo -> indexes: no number at all, or a number read only once in the
    whole house (OpenThai misreads '±0.00' as '-10.00' or '+0.60' as '+90.60' - such a value is never repeated, while a
    real level is printed on several elevations). With recs: a mark whose strip OpenThai read nothing level-like from is
    not a level mark and is skipped (GT eval: Paddle on 33% of marks instead of 39%, same 113/180, 98%, 32 floors)."""
    from collections import Counter
    n = Counter(round(r["value_m"], 2) for r in reads if r and r.get("value_m") is not None)
    out = [i for i, r in enumerate(reads) if not r or r.get("value_m") is None or n[round(r["value_m"], 2)] == 1]
    return [i for i in out if recs is None or level_like(recs[i])]


def floor_votes(readings):
    """readings [dict(value_m, name, page)] -> {code: Counter(value)} + {code: Counter(name)} with the spec's codes
    (level_master: B*, F*, F*M, RF, RF2): ชั้น N / ชั้นล่าง / ชั้นบน -> FN / F1 / F2 (levelarm_probe.floor_of);
    roof slab ('หลังคา', not 'หลังคาน' = top of beam) -> RF, a second, higher roof value -> RF2 ...; mezzanine 'ชั้นลอย'
    -> F{n}M over the numbered floor below it; 'ใต้ดิน' / 'จอดรถ' below F1 -> B1, B2 ... downward.
    A floor's level prefers names with 'พื้น' (floor): 'ระดับหลังคานชั้น 2' is the beam top of floor 2, not the floor;
    other names only count when a code has no 'พื้น' reading at all. Street / ground names ('ระดับพื้นถนน', 'ระดับดินเดิม')
    carry none of these words, so they never become a floor."""
    import titleblock_extract as T
    import levelarm_probe as L
    from collections import Counter
    floor_v, floor_n, other_v, other_n = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    roof, mezz, base = Counter(), [], []
    for r in readings:
        nm, v = r.get("name"), r.get("value_m")
        if not nm or v is None:
            continue
        k = T.name_key(nm)          # name_key drops vowels / tone marks: 'พื้น' -> 'พน', 'ใต้ดิน' -> 'ใตดน'
        code = L.floor_of(nm)
        if code == "RF":
            if "พน" in k:
                roof[v] += 1
                floor_n["RF"][nm] += 1
            else:
                other_v["RF"][v] += 1
                other_n["RF"][nm] += 1
            continue
        if code:
            (floor_v if "พน" in k else other_v)[code][v] += 1
            (floor_n if "พน" in k else other_n)[code][nm] += 1
            continue
        if re.search(r"[ชซ]นลอย", k):
            mezz.append((v, nm))
        elif re.search(r"ใตดน|จอดรถ", k):
            base.append((v, nm))
    votes = {c: floor_v[c] for c in floor_v}
    names = {c: floor_n[c] for c in floor_n}
    for c in other_v:
        if c not in votes and c != "RF":
            votes[c], names[c] = other_v[c], other_n[c]
    # a roof sits above every numbered floor: a 'roof' value at or below the top floor is a mislabel (2ชั้น_01 p49, a
    # sanitary riser diagram, prints 'ระดับพื้นชั้นหลังคา' at ±0.00) - dropped with a note; then the non-slab roof names
    # ('ระดับคานหลังคา') are used if the slab names left nothing
    tops = [Counter(vs).most_common(1)[0][0] for c, vs in votes.items() if re.fullmatch(r"F\d+", c)]
    top = max(tops) if tops else None
    notes = []
    for src in (roof, other_v.get("RF", Counter())):
        low = [v for v in src if top is not None and v <= top]
        if low:
            notes.append(f"roof value(s) {sorted(low)} at or below the top floor {top} - dropped")
    roof_ok = Counter({v: n for v, n in roof.items() if top is None or v > top})
    other_ok = Counter({v: n for v, n in other_v.get("RF", Counter()).items() if top is None or v > top})
    src = roof_ok or other_ok
    for i, v in enumerate(sorted(src)):
        c = "RF" if i == 0 else f"RF{i + 1}"
        votes[c] = Counter({v: src[v]})
        names[c] = floor_n.get("RF") if roof_ok else other_n.get("RF")
    numbered = sorted((Counter(vs).most_common(1)[0][0], c) for c, vs in votes.items() if re.fullmatch(r"F\d+", c))
    for v, nm in mezz:
        below = [c for lv, c in numbered if lv < v]
        c = (below[-1] if below else "F1") + "M"
        votes.setdefault(c, Counter())[v] += 1
        names.setdefault(c, Counter())[nm] += 1
    f1 = Counter(votes.get("F1", {})).most_common(1)
    f1v = f1[0][0] if f1 else None
    for i, v in enumerate(sorted({v for v, _ in base if f1v is None or v < f1v}, reverse=True)):
        c = f"B{i + 1}"
        votes[c] = Counter({v: sum(1 for b, _ in base if b == v)})
        names[c] = Counter(nm for b, nm in base if b == v)
    return votes, names, notes


def code_rank(c):
    """spec floor code -> order from the bottom: B2 < B1 < F1 < F1M < F2 < ... < RF < RF2 (None = unknown code)"""
    m = re.fullmatch(r"B(\d+)", c)
    if m:
        return -int(m.group(1))
    m = re.fullmatch(r"F(\d+)(M?)", c)
    if m:
        return int(m.group(1)) + (0.5 if m.group(2) else 0)
    m = re.fullmatch(r"RF(\d*)", c)
    return 1000 + int(m.group(1) or 1) if m else None


def assemble_floors(readings):
    """-> (floors sorted by level, warnings): level_m = the most voted value; a tie leaves level_m None with the
    candidates listed (never guessed). Order check (each floor above the one before) via pass3_grid.check_level_master."""
    import pass3_grid as P
    votes, names, notes = floor_votes(readings)
    floors, warns = [], list(notes)
    for c, vs in votes.items():
        top = vs.most_common()
        tie = len(top) > 1 and top[0][1] == top[1][1]
        f = dict(floor_level=c, level_m=None if tie else top[0][0], structure_level_m=None,
                 printed_as=names[c].most_common(1)[0][0] if names.get(c) else None, votes=0 if tie else top[0][1])
        if len(top) > 1:
            f["candidates"] = [dict(level_m=v, votes=n) for v, n in top]
            warns.append(f"floor {c}: more than one level read {[v for v, _ in top]}" + (" - tie, level_m left empty" if tie else ""))
        floors.append(f)
    # out of order (a floor at or below the one under it): the side with fewer votes is the misreading - its level_m
    # is emptied and kept in candidates; equal votes = both kept, reported below (never decided by guess)
    while True:
        seq = sorted((f for f in floors if f["level_m"] is not None and code_rank(f["floor_level"]) is not None),
                     key=lambda f: code_rank(f["floor_level"]))
        bad = next(((a, b) for a, b in zip(seq, seq[1:]) if b["level_m"] <= a["level_m"] and a["votes"] != b["votes"]), None)
        if not bad:
            break
        loser = min(bad, key=lambda f: f["votes"])
        winner = bad[0] if loser is bad[1] else bad[1]
        warns.append(f"floor {loser['floor_level']} {loser['level_m']} m out of order with {winner['floor_level']} "
                     f"{winner['level_m']} m - dropped ({loser['votes']} vs {winner['votes']} votes)")
        loser.setdefault("candidates", [dict(level_m=loser["level_m"], votes=loser["votes"])])
        loser["level_m"], loser["votes"], loser["dropped"] = None, 0, "out_of_order"
    floors.sort(key=lambda f: (f["level_m"] is None, f["level_m"] if f["level_m"] is not None else 0))
    z = [dict(level_m=f["level_m"]) for f in floors if f["level_m"] is not None]
    warns += P.check_level_master(floors, z)
    return floors, warns


PAREN_LEVEL = re.compile(r"\(\s*([+\-−–±])\s?(\d{1,2})[.,](\d{2})\s*\)")
LINK_TOL = 0.15        # m: a structural slab tag may sit this far under the architectural FFL of its floor (174: 1.90/2.00)


def paren_levels(text):
    """'(+9.00)' -> [9.0]: the slab-level tag structural plans print under the slab label (STECON / house 174)"""
    return [(-1 if s in "-−–" else 1) * float(f"{a}.{b}") for s, a, b in PAREN_LEVEL.findall(OH_ZERO.sub("0", text))]


def link_plan_levels(page_tags, floors, tol=LINK_TOL):
    """page_tags {page: Counter(value)} + floors (assemble_floors) -> (links [dict(page, level, floor_level, delta)],
    floors with structure_level_m set). Only tags within tol of a floor's level_m vote (the slab sits at or a little
    under the finished floor); the most voted of those gives the page its floor. A basement plan carries ramp / pit
    tags too (STECON p8: -1.00 x2 beside +1.00 x3, -0.80, 0.00), so a plain majority would pick a ramp. No tag near any
    floor = floor_level None, reported with the page's most frequent tag - never forced onto the nearest floor."""
    from collections import Counter
    links, struct = [], defaultdict(Counter)
    known = [f for f in floors if f.get("level_m") is not None]

    def nearest(v):
        return min(known, key=lambda f: abs(f["level_m"] - v), default=None)
    for pg, tags in sorted(page_tags.items()):
        if not tags:
            continue
        tags = Counter(tags)
        near = [(n, v) for v, n in tags.items() if nearest(v) and abs(nearest(v)["level_m"] - v) <= tol + 1e-9]
        if near:
            n, lv = max(near, key=lambda t: (t[0], -abs(nearest(t[1])["level_m"] - t[1])))
            best = nearest(lv)
            links.append(dict(page=pg, level=lv, floor_level=best["floor_level"], delta=round(lv - best["level_m"], 3)))
            struct[best["floor_level"]][lv] += 1
        else:
            lv = tags.most_common(1)[0][0]
            best = nearest(lv)
            links.append(dict(page=pg, level=lv, floor_level=None, delta=round(lv - best["level_m"], 3) if best else None))
    out = []
    for f in floors:
        f = dict(f)
        if struct.get(f["floor_level"]):
            f["structure_level_m"] = struct[f["floor_level"]].most_common(1)[0][0]
        out.append(f)
    return links, out


def plan_tags(page, tiles=2, engine="paddle"):
    """OCR a plan page -> Counter of '(+d.dd)' slab tags. Paddle: tiles x tiles pieces at 3300 px (Paddle fails above ~4000
    px; A1 at ~2.8 px/pt as a whole page reads 7 px text), Latin reader only (the tag is digits), ~90-150 s/page.
    OpenThai: the whole page at 6000 px in one read, ~4.4 s/page (STECON Doi Kham structure, 19 plan pages)."""
    import fitz
    from collections import Counter
    if engine == "openthai":
        W = max(page.rect.width, page.rect.height)
        img, _ = render(page, page.rect, dpi=int(6000 / (W / 72)))
        return Counter(v for t, _b in ot_lines(img, px_limit=6000) for v in paren_levels(t))
    import levelarm_probe as L
    import titleblock_extract as T
    W, H = page.rect.width, page.rect.height
    found = Counter()
    for i in range(tiles):
        for j in range(tiles):
            r = fitz.Rect(W * i / tiles - 20, H * j / tiles - 20, W * (i + 1) / tiles + 20, H * (j + 1) / tiles + 20) & page.rect
            img, _ = render(page, r, dpi=int(T.MAX_PAGE_PX / (max(r.width, r.height) / 72)))
            for t, _b in L._ocr(img, T._reader()):
                for v in paren_levels(t):
                    found[v] += 1
    return found


def run_plan_tags(pdf, levels_json, out=None, engine="paddle"):
    """structural PDF + level_marks.json of the architectural set -> level master with structure_level_m + plan links.
    engine 'both': OpenThai on every plan page, then Paddle (tiles) only on the pages left without a floor, tags added
    together (STECON Doi Kham: OpenThai alone 14/17 pages, Paddle alone 15/17, both 16/17, 0 wrong in each)."""
    import fitz
    import run_part1_part3 as R
    from collections import Counter
    doc = fitz.open(pdf)
    floors = json.load(open(levels_json, encoding="utf-8"))["level_master"]["detail"]
    suffix = "" if engine == "paddle" else f"_{engine}"
    tag_cache = os.path.join(DEFAULT_OUT, os.path.splitext(os.path.basename(pdf))[0], f"plan_tags{suffix}.json")
    if os.path.exists(tag_cache):     # OCR is the slow part: re-linking against a new floors table needs none
        page_tags = {int(k): Counter({float(v): n for v, n in d.items()})
                     for k, d in json.load(open(tag_cache, encoding="utf-8")).items()}
        print(f"  plan tags from {tag_cache}", flush=True)
    else:
        page_tags = {}
        t0 = time.time()
        first = "openthai" if engine == "both" else engine
        for n, page in enumerate(doc, 1):
            if not is_vector(page) or not R.is_grid_candidate(page):
                continue
            page_tags[n] = plan_tags(page, engine=first)
            print(f"  plan page {n}: {dict(page_tags[n])} ({time.time() - t0:.0f} s)", flush=True)
        if engine == "both":
            links, _ = link_plan_levels(page_tags, floors)
            linked = {l["page"] for l in links if l["floor_level"]}
            for n in [n for n in page_tags if n not in linked]:
                page_tags[n] = page_tags[n] + plan_tags(doc[n - 1], engine="paddle")
                print(f"  plan page {n} + Paddle: {dict(page_tags[n])} ({time.time() - t0:.0f} s)", flush=True)
        os.makedirs(os.path.dirname(tag_cache), exist_ok=True)
        json.dump({str(k): {str(v): n for v, n in c.items()} for k, c in page_tags.items()},
                  open(tag_cache, "w", encoding="utf-8"))
    links, floors2 = link_plan_levels(page_tags, floors)
    res = dict(pdf=os.path.basename(pdf), levels_from=os.path.basename(os.path.dirname(levels_json)),
               plan_tags={str(k): dict(v) for k, v in page_tags.items()}, plan_links=links,
               level_master=dict(pattern="level_master", level=dict(floors=[
                   {k: f[k] for k in ("floor_level", "level_m", "structure_level_m", "printed_as")} for f in floors2]),
                   detail=floors2),
               warnings=[f"plan page {l['page']}: slab tag {l['level']:+.2f} matches no floor within {LINK_TOL} m"
                         for l in links if l["floor_level"] is None])
    out = out or os.path.join(os.path.dirname(levels_json), "level_master_with_plans.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return res, out


def fill_by_name(marks):
    """name-only marks take the value that marks with the same name (levelarm_probe.core) carry elsewhere in the house -
    only when those agree on one value; flagged value_from_same_name. Returns the same list (mutated)."""
    import levelarm_probe as L
    vals = defaultdict(set)
    for m in marks:
        if m.get("value_m") is not None and m.get("name"):
            vals[L.core(m["name"])].add(m["value_m"])
    for m in marks:
        if m.get("value_m") is None and m.get("name"):
            vs = vals.get(L.core(m["name"]))
            if vs and len(vs) == 1:
                m["value_m"] = next(iter(vs))
                m["flags"] = [f for f in m.get("flags", []) if f != "name_without_number"] + ["value_from_same_name"]
    return marks


def house_pdf(house):
    return os.path.join(IMAGE, house, house + ".pdf")


def is_vector(page):
    return sum(1 for d in page.get_cdrawings() for it in d.get("items", ()) if it[0] == "l") >= 200


def level_master_of(per_page):
    """{page: [read marks]} -> (z_levels, level_master dict, warnings) - shared by run_house and reassemble"""
    import pass3_grid as P
    readings = [dict(page=int(n), value_m=m["value_m"], name=m.get("name"))
                for n, ms in per_page.items() for m in ms if m.get("value_m") is not None]
    z, _, warns = P.build_level_master(readings)     # z_levels register only; floors come from assemble_floors
    floors, fwarns = assemble_floors(readings)
    warns = [w for w in warns if not w.startswith("floor")] + fwarns
    # a floor emptied by the order rule (a lone misread like 'ชั้น 4' at +0.60 in a 2-storey house) stays in detail
    # only; a tie stays in the spec list with level_m None - that floor exists, its height is undecided
    lm = dict(pattern="level_master", level=dict(floors=[
        {k: f[k] for k in ("floor_level", "level_m", "structure_level_m", "printed_as")} for f in floors
        if not f.get("dropped")]), detail=floors)
    return z, lm, warns


def reassemble(path):
    res = json.load(open(path, encoding="utf-8"))
    z, lm, warns = level_master_of(res["marks"])
    res.update(z_levels=z, level_master=lm, warnings=warns)
    json.dump(res, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return res


def run_house(house, pages=None, ocr=True, out_dir=DEFAULT_OUT, pdf=None, engine="paddle"):
    import fitz
    doc = fitz.open(pdf or house_pdf(house))
    todo = [n for n in (pages or range(1, len(doc) + 1)) if 1 <= n <= len(doc)]
    per_page, skipped, pairs_by_page = {}, [], {}
    t0 = time.time()
    for n in todo:
        page = doc[n - 1]
        if not is_vector(page):
            skipped.append(n)
            continue
        if ocr and engine == "both":
            pairs_by_page[n] = page_marks(page, keep_ocr=True, engine="both")
            ms = [m for m, _ in pairs_by_page[n]]
        else:
            ms = page_marks(page, ocr=ocr, engine=engine)
            if ms:
                per_page[n] = ms
        print(f"  page {n}: {len(ms)} marks ({time.time() - t0:.0f} s)", flush=True)
    redone = 0
    if ocr and engine == "both":
        flat = [(n, i, m, rec) for n, ps in pairs_by_page.items() for i, (m, rec) in enumerate(ps)]
        reads = [interpret(m, rec) for _, _, m, rec in flat]
        for k in doubtful(reads, [rec for _, _, _, rec in flat]):
            n, i, m, _ = flat[k]
            rp = interpret(m, ocr_strip(doc[n - 1], m, "paddle"))
            redone += 1
            if rp and (rp.get("value_m") is not None or not reads[k]):
                reads[k] = dict(rp, flags=rp.get("flags", []) + ["read_by_paddle"])
        for (n, _, _, _), r in zip(flat, reads):
            if r:
                per_page.setdefault(n, []).append(r)
        print(f"  both: Paddle re-read {redone} of {len(flat)} marks ({time.time() - t0:.0f} s)", flush=True)
    if ocr:
        fill_by_name([m for ms in per_page.values() for m in ms])
    res = dict(house=house, pages_read=list(todo), raster_pages_skipped=skipped, ocr=engine if ocr else None,
               marks={str(k): v for k, v in per_page.items()})
    if ocr:
        z, lm, warns = level_master_of(per_page)
        res.update(z_levels=z, level_master=lm, warnings=warns)
    out = os.path.join(out_dir, house)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "level_marks.json")
    json.dump(res, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return res, path


# ---------------- evaluation ----------------

def gt_house(gd):
    gf = glob.glob(os.path.join(gd, "*gridline.json"))
    if not gf:
        return None
    return (json.load(open(gf[0], encoding="utf-8")).get("grid") or {}).get("z_levels") or []


def evaluate(stride=1, cache=None):
    """GT pages (the pages a person read z_levels from) of every `stride`-th GT house.
    recall_printed = GT levels of type named/datum on that page that a read mark gives (value within 0.005 m);
    '@' and dummy GT levels are annotator heights / room tags, not ▽ marks - counted apart. precision = read values equal
    to ANY GT level of the house (lower bound: GT may miss levels). Floors: GT floor = floor_of(GT id) for ids that name
    one; compared with build_level_master's floors on the marks of the same pages."""
    import fitz
    import levelarm_probe as L
    import pass3_grid as P
    done = json.load(open(cache, encoding="utf-8")) if cache and os.path.exists(cache) else {}
    tot = defaultdict(int)
    floor_rows = []
    for hi, gd in enumerate(sorted(d for d in glob.glob(os.path.join(GT, "*")) if os.path.isdir(d))):
        if hi % stride:
            continue
        z = gt_house(gd)
        house = re.sub(r"^\d+", "", os.path.basename(gd))
        pdf = house_pdf(house)
        if z is None or not os.path.exists(pdf):
            continue
        doc = fitz.open(pdf)
        by_page = defaultdict(list)
        for e in z:
            m = PAGE_RE.search(str(e.get("source_image") or ""))
            if m and isinstance(e.get("level_m"), (int, float)) and 1 <= int(m.group(1)) <= len(doc):
                by_page[int(m.group(1))].append(e)
        house_vals = [e["level_m"] for e in z if isinstance(e.get("level_m"), (int, float))]
        readings = []
        page_reads = {}
        for pn in sorted(by_page):
            key = f"{house}|{pn}"
            if key not in done:
                page = doc[pn - 1]
                vec = is_vector(page)
                done[key] = dict(v=2, vector=vec, pairs=[[m, r] for m, r in page_marks(page, keep_ocr=True)] if vec else [])
                if cache:
                    json.dump(done, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
            elif done[key].get("v") != 2:
                # cache written before circle marks existed: add (and OCR) only the circles, keep the ▽ reads as they are
                if done[key]["vector"]:
                    page = doc[pn - 1]
                    _, _, circles, fills = page_geometry(page)
                    done[key]["pairs"] += [[m, ocr_strip(page, m)] for m in find_circle_marks(circles, fills)]
                done[key]["v"] = 2
                if cache:
                    json.dump(done, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
            page_reads[pn] = [r for r in (interpret(m, rec) for m, rec in done[key]["pairs"]) if r]
        fill_by_name([m for ms in page_reads.values() for m in ms])
        for pn in sorted(by_page):
            rec = dict(vector=done[f"{house}|{pn}"]["vector"], marks=page_reads[pn])
            vals = [m["value_m"] for m in rec["marks"] if m.get("value_m") is not None]
            for m in rec["marks"]:
                if m.get("value_m") is not None:
                    readings.append(dict(page=pn, value_m=m["value_m"], name=m.get("name")))
            for e in by_page[pn]:
                printed = e.get("type") in ("named", "datum") and not str(e.get("id")).startswith("@")
                k = "printed" if printed else "other"
                tot[f"gt_{k}"] += 1
                tot[f"gt_{k}_{'vector' if rec['vector'] else 'raster'}"] += 1
                if any(abs(v - e["level_m"]) < 0.005 for v in vals):
                    tot[f"hit_{k}"] += 1
                    tot[f"hit_{k}_{'vector' if rec['vector'] else 'raster'}"] += 1
            for v in vals:
                tot["read"] += 1
                tot["read_in_gt"] += any(abs(v - g) < 0.005 for g in house_vals)
            tot["marks_name_only"] += sum(1 for m in rec["marks"] if m.get("value_m") is None)
            tot["pages"] += 1
            tot["pages_vector"] += rec["vector"]
        gt_floor = {}
        for e in z:
            f = L.floor_of(e.get("id")) if isinstance(e.get("id"), str) else None
            if f and isinstance(e.get("level_m"), (int, float)):
                gt_floor.setdefault(f, set()).add(round(e["level_m"], 2))
        floors, _ = assemble_floors(readings)
        got = {f["floor_level"]: f["level_m"] for f in floors}
        for f, vals in sorted(gt_floor.items()):
            g = got.get(f)
            floor_rows.append((house, f, sorted(vals), g, g is not None and round(g, 2) in vals))
        print(f"{house}: {sum(len(v) for v in by_page.values())} GT levels on {len(by_page)} pages", flush=True)
    return dict(tot), floor_rows


def report(tot, floor_rows):
    def pct(a, b):
        return f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0"
    print("pages", tot.get("pages", 0), "vector", tot.get("pages_vector", 0))
    print("printed GT levels (named/datum) found:", pct(tot.get("hit_printed", 0), tot.get("gt_printed", 0)),
          "| on vector pages:", pct(tot.get("hit_printed_vector", 0), tot.get("gt_printed_vector", 0)),
          "| on raster pages:", pct(tot.get("hit_printed_raster", 0), tot.get("gt_printed_raster", 0)))
    print("other GT levels (@ / dummy) found:", pct(tot.get("hit_other", 0), tot.get("gt_other", 0)))
    print("read values equal to some GT level of the house:", pct(tot.get("read_in_gt", 0), tot.get("read", 0)),
          "| marks with a name and no number:", tot.get("marks_name_only", 0))
    ok = sum(r[4] for r in floor_rows)
    print("floors named in GT:", len(floor_rows), "| level master gives the GT level:", ok,
          "| wrong:", sum(1 for r in floor_rows if r[3] is not None and not r[4]),
          "| missing:", sum(1 for r in floor_rows if r[3] is None))
    for r in floor_rows:
        if not r[4]:
            print("   ", r)


# ---------------- self-check ----------------

def _tri(x, y, b, h, down=True):
    """three strokes of a triangle with its horizontal edge at y"""
    ay = y + h if down else y - h
    return [(x, y, x + b, y), (x + b, y, x + b / 2, ay), (x + b / 2, ay, x, y)]


def demo():
    # a plain ▽ is found, with its numbers
    m = find_marks(_tri(100, 50, 6, 5.2))
    assert len(m) == 1 and m[0]["base"] == 6 and m[0]["apex_y"] == 55.2, m
    # △ (apex up, a wall tag) is not a level mark
    assert find_marks(_tri(100, 50, 6, 5.2, down=False)) == []
    # a square with an X: flat (h = b/2) and right triangles only -> nothing
    sq = [(0, 0, 6, 0), (6, 0, 6, 6), (6, 6, 0, 6), (0, 6, 0, 0), (0, 0, 6, 6), (6, 0, 0, 6)]
    assert find_marks(sq) == []
    # a ▽ with a digit drawn inside is a tag, not a level
    assert find_marks(_tri(100, 50, 6, 5.2), ink=[(103, 51.8), (103, 53.2)]) == []
    # points ON an edge (its own stroke ends / mid points) do not count as inside
    assert len(find_marks(_tri(100, 50, 6, 5.2), ink=[(100, 50), (106, 50), (103, 55.2), (103, 50)])) == 1
    # too small / too big / too flat / too tall
    assert find_marks(_tri(0, 0, 2.0, 1.7)) == [] and find_marks(_tri(0, 0, 16, 14)) == []
    assert find_marks(_tri(0, 0, 6, 3.2)) == [] and find_marks(_tri(0, 0, 6, 8)) == []
    # the same ▽ drawn twice (filled + outlined, slightly shifted) is one mark; two marks in a column stay two
    assert len(find_marks(_tri(100, 50, 6, 5.2) + _tri(100.1, 50.1, 5.8, 5.0))) == 1
    inner = find_marks(_tri(100, 50, 6, 5.2) + _tri(100.7, 50.5, 4.6, 4.0))      # inner outline, corners > SNAP apart
    assert len(inner) == 1 and inner[0]["base"] == 6, inner
    assert len(find_marks(_tri(100, 50, 6, 5.2) + _tri(100, 70, 6, 5.2))) == 2
    # strokes that meet within SNAP close the triangle; a gap bigger than SNAP does not
    t = _tri(100, 50, 6, 5.2)
    t[1] = (106.2, 50.2, 103, 55.2)
    assert len(find_marks(t)) == 1
    t[1] = (107, 51, 103, 55.2)
    assert find_marks(t) == []
    # numbers: signed levels, ± datum, unsigned 0.00 kept, unsigned 3.20 dropped, 3 decimals kept
    assert parse_number("+3.75") == [3.75] and parse_number("±0.00") == [0.0] and parse_number("-1.50") == [-1.5]
    # a 3rd decimal is dropped: OCR adds stray digits ('+0.601' for +0.60, seen on 2ชั้น_01 p22) and no GT house prints a
    # 3-decimal level (one annotator height 7.789 only) - a real '+0.175' would read 0.17 (5 mm off), accepted
    assert parse_number("0.00") == [0.0] and parse_number("3.20") == [] and parse_number("+ 0.175") == [0.17]
    assert parse_number("ระดับหลังคาน+3.75") == [3.75] and parse_number("1.2.30") == []
    assert parse_number("S0AUAHAl±O.00") == [0.0]          # real Latin-reader output, letter O for zero
    assert parse_number("+0.601") == [0.6] and parse_number("+O.60") == [0.6]
    assert parse_number("BOX.12") == []                     # an O not in a number stays a letter
    assert parse_number("FFL.+19.50") == [19.5] and parse_number("FFL.-1.00") == [-1.0]   # STECON prefix
    # OpenThai quirks (real readings of 1ชั้น_01 p8): ▽ as '7'/'Y', ± as a sign pair, ± as ':'
    assert parse_number("7 +3.75 ระดับหลังคาน") == [3.75] and parse_number("7+3.75") == [3.75]
    assert parse_number("Y7 -+0.00 ระดับอ้างอิง") == [0.0] and parse_number("Y :0.00 ระดับอ้างอิง") == [0.0]
    assert parse_number("7-+0.60 ระดับพื้นชั้น") == [0.6] and parse_number("Y7 +-0.60") == [0.6]
    assert parse_number("0 .60") == [] and parse_number("+0 .60") == [0.6]        # unsigned stays refused once joined
    assert parse_number("17+3.75") == [] and parse_number("3.00+3.00") == []        # a real digit run is not a ▽
    assert parse_number("+O.20") == [0.2] and parse_number("+O. IO") == [0.1] and parse_number("+O. 40") == [0.4]
    assert parse_number("175 7+2.35 ระดับพื้นชานพัก") == [2.35] and parse_number("ฬ +6.65") == [6.65]
    assert parse_number("+-6.65") == [6.65] and parse_number("V ระดับพื้นชื้นล่าง +-0.31") == [0.31]
    assert parse_number("NO.12") == [] and parse_number("+ 0.3021") == []           # garbage stays garbage
    assert parse_number("Y :O.00 ระดับอ้างอิง") == [0.0]       # ± read as ':' and 0 as O, no sign left: OH_ZERO's job
    assert LEVEL_WORD.search("งระดีบพินชั้นลาง") and LEVEL_WORD.search("จระดิบพินภายใน")
    # circle level mark (STECON page 26, real numbers): circle d 6.96 + a filled quarter wedge with a vertex on the centre
    wedge = (170.27, 437.63, 173.63, 440.99, [(173.63, 440.99), (171.47, 437.87), (170.27, 437.63), (170.27, 440.99)])
    cm = find_circle_marks([(170.15, 441.11, 6.96)], [wedge])
    assert len(cm) == 1 and cm[0]["kind"] == "circle" and cm[0]["base"] == 6.96, cm
    assert find_circle_marks([(170.15, 441.11, 6.96)], []) == []                 # plain circle (grid bubble) -> none
    assert find_circle_marks([(170.15, 441.11, 20.0)], [wedge]) == []            # too big for a level symbol
    far = (180.0, 437.0, 183.0, 440.0, [(180.0, 437.0), (183.0, 440.0)])          # a fill elsewhere does not count
    assert find_circle_marks([(170.15, 441.11, 6.96)], [far]) == []
    # circle: name above the line, value below it (both right of the circle) -> both read
    cmk = dict(cm[0])
    crec = dict(o=[cmk["x0"] - 21, cmk["top"] - 9.7], scale=1.0,
                lat=[["FFL.+19.50", [24.5, 13.0, 60.0, 18.5]]], th=[["ระดับพื้นชั้นที่ 5", [24.5, 3.0, 70.0, 9.5]]])
    cr = interpret(cmk, crec)
    assert cr and cr["value_m"] == 19.5 and cr["name"] == "ระดับพื้นชั้นที่ 5", cr
    # interpret: number from the Thai reader when the Latin one garbled it; name bound from the same box
    mk = dict(x0=10, x1=16, top=10, apex_y=15.2, base=6)
    rec = dict(o=[0, 0], scale=1.0, lat=[["S0AUAHAl±O.0O", [18, 9, 60, 16]]], th=[["ระดับดินเดิม±0.00", [18, 9, 60, 16]]])
    r = interpret(mk, rec)
    assert r and r["value_m"] == 0.0 and r["name"] == "ระดับดินเดิม" and r["flags"] == [], r
    rec_th_only = dict(rec, lat=[["S0AUAHAl", [18, 9, 60, 16]]])                 # Latin pass got no number at all
    assert interpret(mk, rec_th_only)["value_m"] == 0.0
    # a ▽ with only unrelated text next to it is not a level mark
    assert interpret(mk, dict(o=[0, 0], scale=1.0, lat=[["A-06", [18, 9, 40, 16]]], th=[["แบบ", [18, 9, 40, 16]]])) is None
    # name only -> kept, flagged; fill_by_name gives it the value another mark with the same name carries
    r2 = interpret(mk, dict(o=[0, 0], scale=1.0, lat=[], th=[["ระดับหลังคาน", [18, 9, 60, 16]]]))
    assert r2["value_m"] is None and r2["flags"] == ["name_without_number"]
    other = dict(value_m=3.75, name="ระดับหลังคาน", flags=[])
    fill_by_name([r2, other])
    assert r2["value_m"] == 3.75 and r2["flags"] == ["value_from_same_name"]
    # two different values for one name -> no fill (never guess)
    r3 = dict(value_m=None, name="ระดับพื้นชั้น 1", flags=["name_without_number"])
    fill_by_name([r3, dict(value_m=0.6, name="ระดับพื้นชั้น 1"), dict(value_m=0.5, name="ระดับพื้นชั้น 1")])
    assert r3["value_m"] is None
    # pick_number: the number on the ▽'s row right next to it wins; a number on another row or far away does not
    mk = dict(x0=10, x1=16, top=10, apex_y=15.2, base=6, _o=(0, 0))
    s = 1.0
    assert pick_number(mk, [(3.75, (18, 9, 40, 16))], s) == 3.75
    assert pick_number(mk, [(3.75, (18, 30, 40, 37))], s) is None              # row below
    assert pick_number(mk, [(3.75, (18 + 4 * 6 + 1, 9, 80, 16))], s) is None    # starts too far right
    assert pick_number(mk, [(0.0, (-30, 9, 9, 16)), (2.0, (40, 9, 60, 16))], s) == 0.0   # left side, nearer
    # '▽ ระดับพื้นชั้นบน +2.60': the number past the name is reached through the name box; without it, it is too far
    far_num = [(2.6, (110, 9, 135, 16))]
    assert pick_number(mk, far_num, s) is None
    assert pick_number(mk, far_num, s, name_boxes=[(18, 8, 95, 17)]) == 2.6
    assert pick_number(mk, far_num, s, name_boxes=[(9, 8, 95, 17)]) == 2.6      # box joined with the ▽ glyph
    assert pick_number(mk, far_num, s, name_boxes=[(-10, 8, 95, 17)]) == 2.6    # box joined with the level line too
    assert pick_number(mk, far_num, s, name_boxes=[(-20, 8, 95, 17)]) is None   # starts too far left
    assert pick_number(mk, far_num, s, name_boxes=[(60, 8, 95, 17)]) is None      # name starts too far from the ▽
    assert pick_number(mk, far_num, s, name_boxes=[(18, 30, 95, 39)]) is None     # name on another row
    # floors: the STECON page 26 readings (real) -> the codes house 174's level master uses
    st = [(-1.0, "ระดับพื้นชั้นที่จอดรถ"), (0.0, "ระดับพื้นถนนหน้าอาคาร"), (2.0, "ระดับพื้นชั้นที่ 1"), (5.5, "ระดับพื้นชั้นลอย"),
          (9.0, "ระดับพื้นชั้นที่ 2"), (12.5, "ระดับพื้นชั้นที่ 3"), (16.0, "ระดับพื้นชั้นที่ 4"), (19.5, "ระดับพื้นชั้นที่ 5"),
          (22.9, "ระดับพื้นหลังคา คสล"), (25.65, "ระดับพื้นหลังคา คสล"), (27.35, "ระดับหลังอกไก่"), (6.05, "ระดับหลังคาน")]
    fl, w = assemble_floors([dict(page=26, value_m=v, name=n) for v, n in st * 2])
    got = {f["floor_level"]: f["level_m"] for f in fl}
    assert got == {"B1": -1.0, "F1": 2.0, "F1M": 5.5, "F2": 9.0, "F3": 12.5, "F4": 16.0, "F5": 19.5, "RF": 22.9,
                   "RF2": 25.65}, got
    assert [f["floor_level"] for f in fl] == ["B1", "F1", "F1M", "F2", "F3", "F4", "F5", "RF", "RF2"] and not w, (fl, w)
    # mezzanine over floor 2 -> F2M; a basement named without 'ชั้น' ('ใต้ดิน' holds 'ดิน') is still B1
    fl, _ = assemble_floors([dict(value_m=v, name=n) for v, n in [(0.5, "ระดับพื้นชั้น 1"), (3.5, "ระดับพื้นชั้น 2"),
                                                                    (5.0, "ระดับพื้นชั้นลอย"), (-2.5, "ระดับพื้นใต้ดิน")]])
    assert {f["floor_level"]: f["level_m"] for f in fl} == {"B1": -2.5, "F1": 0.5, "F2": 3.5, "F2M": 5.0}, fl
    # 'พื้น' names win over other names of the same floor; a 1-1 tie between two floor values is left empty
    fl, _ = assemble_floors([dict(value_m=3.75, name="ระดับพื้นชั้น 2"), dict(value_m=6.75, name="ระดับหลังคานชั้น 2")])
    assert {f["floor_level"]: f["level_m"] for f in fl} == {"F2": 3.75}
    fl, w = assemble_floors([dict(value_m=0.6, name="ระดับพื้นชั้น 1"), dict(value_m=0.5, name="ระดับพื้นชั้น 1")])
    assert fl[0]["level_m"] is None and len(fl[0]["candidates"]) == 2 and w
    # a floor above the next one with EQUAL votes is reported, not fixed
    _, w = assemble_floors([dict(value_m=3.0, name="ระดับพื้นชั้น 1"), dict(value_m=0.6, name="ระดับพื้นชั้น 2")])
    assert any("floor order" in x for x in w), w
    # 2ชั้น_01 as read (whole book): the riser diagram's 'roof' at ±0.00 is dropped, the roof beam name gives RF
    h = ([(0.6, "ระดับพื้นชั้น 1")] * 8 + [(3.75, "ระดับพื้นชั้น 2")] * 8 + [(3.75, "ระดับพื้นชั้นล่าง")]
         + [(0.0, "ระดับพื้นชั้นหลังคา")] + [(6.65, "ระดับคานหลังคา")] * 4)
    fl, w = assemble_floors([dict(value_m=v, name=n) for v, n in h])
    assert {f["floor_level"]: f["level_m"] for f in fl} == {"F1": 0.6, "F2": 3.75, "RF": 6.65}, (fl, w)
    assert any("roof value(s) [0.0]" in x for x in w), w
    # out of order with unequal votes: the weaker side is emptied, kept as a candidate
    fl, w = assemble_floors([dict(value_m=3.5, name="ระดับพื้นชั้น 2")] * 5 + [dict(value_m=4.0, name="ระดับพื้นชั้น 3")])
    assert {f["floor_level"]: f["level_m"] for f in fl} == {"F2": 3.5, "F3": 4.0} and not w, (fl, w)   # in order: kept
    fl, w = assemble_floors([dict(value_m=3.5, name="ระดับพื้นชั้น 2")] * 5 + [dict(value_m=2.0, name="ระดับพื้นชั้น 3")])
    fl3 = next(f for f in fl if f["floor_level"] == "F3")
    assert fl3["level_m"] is None and fl3["candidates"] == [dict(level_m=2.0, votes=1)], fl3
    _, lm3, _ = level_master_of({1: [dict(value_m=3.5, name="ระดับพื้นชั้น 2")] * 5 + [dict(value_m=2.0, name="ระดับพื้นชั้น 3")]})
    assert [f["floor_level"] for f in lm3["level"]["floors"]] == ["F2"], lm3      # dropped F3 not in the spec list
    assert any("out of order" in x for x in w) and not any("floor order" in x for x in w), w
    # 'both': Paddle redoes marks without a number and numbers read only once in the house (OpenThai's '±0.00' -> '-10.00')
    rd = [dict(value_m=0.6), dict(value_m=0.6), None, dict(value_m=None, name="ระดับหลังคาน"), dict(value_m=-10.0),
          dict(value_m=3.75), dict(value_m=3.75)]
    assert doubtful(rd) == [2, 3, 4], doubtful(rd)
    blank, lv = dict(lat=[["A-06", [0, 0, 9, 9]]]), dict(lat=[["Y7.40.00 ระดับอ้างิง", [0, 0, 9, 9]]])
    assert doubtful(rd, [lv, lv, blank, dict(lat=[["V ระดีบหลังคาน", [0, 0, 9, 9]]]), lv, lv, lv]) == [3, 4]
    # plan slab tags: '(+9.00)' read, joined to the floor within 0.15 m; F1 slab 1.90 under FFL 2.00 -> F1, structural
    assert paren_levels("(+9.00)") == [9.0] and paren_levels("( +1.9O )") == [1.9] and paren_levels("+9.00") == []
    assert paren_levels("(-1.00)") == [-1.0]
    from collections import Counter
    fl, _ = assemble_floors([dict(page=26, value_m=v, name=n) for v, n in st])
    links, fl2 = link_plan_levels({9: Counter({1.9: 2}), 13: Counter({9.0: 3, 6.05: 1}), 30: Counter({4.4: 1}),
                                   # STECON p8 as read: the ramp's +1.00 is the most frequent tag, B1's -1.00 the floor
                                   8: Counter({1.0: 3, -0.8: 2, 0.0: 2, 0.3: 1, -0.85: 1, -1.0: 2})}, fl)
    by = {l["page"]: l for l in links}
    assert by[9]["floor_level"] == "F1" and by[13]["floor_level"] == "F2" and by[30]["floor_level"] is None, links
    assert by[8]["floor_level"] == "B1" and by[8]["level"] == -1.0, by[8]
    f2 = {f["floor_level"]: f for f in fl2}
    assert f2["F1"]["structure_level_m"] == 1.9 and f2["F1"]["level_m"] == 2.0 and f2["F3"]["structure_level_m"] is None
    print("demo ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("house", nargs="?")
    ap.add_argument("--page", type=int)
    ap.add_argument("--pages")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--eval", nargs="?", const=1, type=int)
    ap.add_argument("--cache")
    ap.add_argument("--pdf", help="any PDF instead of image/<house>/<house>.pdf (house name = output folder)")
    ap.add_argument("--plan-tags", metavar="STRUCT_PDF", help="read '(+9.00)' slab tags on the plans of this structural "
                    "PDF and join them to the floors of --levels")
    ap.add_argument("--levels", metavar="LEVEL_MARKS_JSON", help="level_marks.json of the architectural set")
    ap.add_argument("--reassemble", metavar="LEVEL_MARKS_JSON", help="rebuild z_levels / floors of a saved result from "
                    "its marks (after a rule change; no OCR)")
    ap.add_argument("--ocr", choices=("paddle", "openthai", "both"), default="paddle",
                    help="reader: paddle (default), openthai (iApp OpenThai, needs the openthai_ocr venv), or both "
                         "(OpenThai first, Paddle on doubtful marks / unlinked plan pages; best measured)")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if a.reassemble:
        res = reassemble(a.reassemble)
        print(json.dumps(res["level_master"]["level"], ensure_ascii=False, indent=1), "\nwarnings:", res["warnings"])
        return
    if a.plan_tags:
        if not a.levels:
            ap.error("--plan-tags needs --levels <level_marks.json of the architectural set>")
        res, path = run_plan_tags(a.plan_tags, a.levels, engine=a.ocr)
        print(json.dumps(res["level_master"]["level"], ensure_ascii=False, indent=1))
        for l in res["plan_links"]:
            print(l)
        print("warnings:", res["warnings"], "\n->", path)
        return
    if a.pdf and not a.house:
        a.house = os.path.splitext(os.path.basename(a.pdf))[0]
    if a.eval:
        tot, rows = evaluate(a.eval, a.cache)
        return report(tot, rows)
    if a.house and a.page:
        import fitz
        page = fitz.open(a.pdf or house_pdf(a.house))[a.page - 1]
        ms = page_marks(page, ocr=not a.no_ocr, engine="openthai" if a.ocr == "both" else a.ocr)
        for m in ms:
            print(m)
        if a.show:
            show(page, ms, os.path.join(DEFAULT_OUT, a.house, f"level_marks_p{a.page:02d}.png"))
        return
    if a.house:
        pages = None
        if a.pages:
            lo, _, hi = a.pages.partition("-")
            pages = range(int(lo), int(hi or lo) + 1)
        res, path = run_house(a.house, pages, ocr=not a.no_ocr, pdf=a.pdf, engine=a.ocr)
        print(json.dumps(res.get("level_master", {}), ensure_ascii=False, indent=1))
        print("->", path)
        return
    ap.print_help()


def show(page, marks, path):
    from PIL import Image, ImageDraw, ImageFont
    pix = page.get_pixmap(dpi=100)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("tahoma.ttf", 13)      # a font with Thai glyphs (Windows); default font has none
    except OSError:
        font = ImageFont.load_default()
    s = 100 / 72
    for m in marks:
        d.rectangle([m["x0"] * s - 2, m["top"] * s - 2, m["x1"] * s + 2, m["apex_y"] * s + 2], outline=(255, 0, 0), width=2)
        d.text((m["x1"] * s + 3, m["apex_y"] * s + 2), f"{m.get('value_m')} {m.get('name') or ''}"[:40], fill=(200, 0, 0),
               font=font)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    print("->", path)


if __name__ == "__main__":
    main()
