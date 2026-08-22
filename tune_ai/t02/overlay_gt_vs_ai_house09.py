"""Overlay house09 (บ้าน_เล็ก_1ชั้น_04) — GREEN = ground-truth elements,
ORANGE = AI (t02) elements — onto the real scanned page. Same method as the
2026-08-20 house01 render: HoughCircles on the printed grid-label circles
-> linear fit per axis -> grid_ref + grid master pos_m -> px.

Ref notations handled:
  point    "E1"                       -> dot
  segment  start/end pair "F1"->"E1"  -> line
  zone     "F-E x 1'-2'" (row-range x col-range) -> line if one side is
           degenerate (F-F), translucent rect otherwise; AI uses this
           notation heavily, GT uses it for slabs

    python overlay_house09.py 26 27
"""
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TRAIN = Path(r"D:\00mk\steel project\training\Training")
IMG_DIR = TRAIN / "image" / "บ้าน_เล็ก_1ชั้น_04"
RESULT_DIR = TRAIN / "tune_ai" / "t02" / "ผล" / "09บ้าน_เล็ก_1ชั้น_04"
GT_DIR = TRAIN / "json_แก้ไขแล้ว" / "09บ้าน_เล็ก_1ชั้น_04"
GRID_JSON = GT_DIR / "บ้าน_เล็ก_1ชั้น_04_หน้า00_gridline.json"

g = json.loads(GRID_JSON.read_text(encoding="utf-8"))["grid"]
GRID_X_M = {l["id"]: l["pos_m"] for l in g["x_lines"]}
GRID_Y_M = {l["id"]: l["pos_m"] for l in g["y_lines"]}
NAMED_X = [l for l in g["x_lines"] if l.get("type") != "dummy"]
NAMED_Y = [l for l in g["y_lines"] if l.get("type") != "dummy"]

_DIGIT = re.compile(r"\d")

GREEN = (40, 200, 70)
ORANGE = (255, 140, 0)


def split_point(ref):
    """'E1' -> ('E','1'); None if ids unknown."""
    m = _DIGIT.search(ref)
    if not m:
        return None
    y_id, x_id = ref[: m.start()], ref[m.start():]
    if x_id in GRID_X_M and y_id in GRID_Y_M:
        return y_id, x_id
    return None


def parse_zone(ref):
    """'F-E x 1'-2'' -> ((y0,y1),(x0,x1)) in metres; None if unparsable."""
    if "x" not in ref:
        return None
    left, _, right = ref.partition("x")
    ys = [s.strip() for s in left.strip().split("-")]
    xs = [s.strip() for s in right.strip().split("-")]
    if len(ys) != 2 or len(xs) != 2:
        return None
    if not all(y in GRID_Y_M for y in ys) or not all(x in GRID_X_M for x in xs):
        return None
    return (GRID_Y_M[ys[0]], GRID_Y_M[ys[1]]), (GRID_X_M[xs[0]], GRID_X_M[xs[1]])


def draw_element(draw, to_px, e, color, font):
    """Returns True if anything was drawn for element e."""
    eid = str(e.get("element_id") or e.get("mark") or e.get("element_type") or "?")
    line_fill = color + (150,)
    text_fill = color + (255,)
    rect_fill = color + (45,)

    def label(x, y):
        draw.text((x + 8, y - 38), eid, fill=text_fill, font=font)

    # 1) endpoint pair
    s, t = e.get("grid_ref_start"), e.get("grid_ref_end")
    if isinstance(s, str) and isinstance(t, str):
        ps, pt = split_point(s.strip()), split_point(t.strip())
        if ps and pt:
            x0, y0 = to_px(GRID_X_M[ps[1]], GRID_Y_M[ps[0]])
            x1, y1 = to_px(GRID_X_M[pt[1]], GRID_Y_M[pt[0]])
            draw.line([(x0, y0), (x1, y1)], fill=line_fill, width=12)
            label((x0 + x1) / 2, (y0 + y1) / 2)
            return True

    # 2) grid_ref / grid_refs — points or zones (AI packs zone lists in one string)
    refs = e.get("grid_refs") or e.get("grid_ref") or []
    if isinstance(refs, str):
        refs = [r.strip() for r in refs.split(",")]
    drawn = False
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            continue
        ref = ref.strip()
        z = parse_zone(ref)
        if z:
            (ya, yb), (xa, xb) = z
            x0, y0 = to_px(xa, ya)
            x1, y1 = to_px(xb, yb)
            if abs(y0 - y1) < 2 or abs(x0 - x1) < 2:  # degenerate -> segment
                draw.line([(x0, y0), (x1, y1)], fill=line_fill, width=12)
            else:
                box = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
                draw.rectangle(box, fill=rect_fill, outline=line_fill, width=6)
            label((x0 + x1) / 2, (y0 + y1) / 2)
            drawn = True
            continue
        p = split_point(ref)
        if p:
            x, y = to_px(GRID_X_M[p[1]], GRID_Y_M[p[0]])
            draw.ellipse([x - 22, y - 22, x + 22, y + 22],
                         outline=line_fill, width=8)
            label(x, y)
            drawn = True
    return drawn


def render_page(page):
    img_path = IMG_DIR / f"บ้าน_เล็ก_1ชั้น_04_หน้า{page}.png"
    ai_path = RESULT_DIR / f"บ้าน_เล็ก_1ชั้น_04_หน้า{page}.json"
    gt_matches = sorted(GT_DIR.glob(f"บ้าน_เล็ก_1ชั้น_04_หน้า{page}_*.json"))
    out_path = RESULT_DIR / f"_overlay_gt_vs_ai_หน้า{page}.png"

    gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    assert gray is not None, img_path

    def find_circles(x0, y0, x1, y1):
        crop = cv2.medianBlur(gray[y0:y1, x0:x1], 5)
        c = cv2.HoughCircles(crop, cv2.HOUGH_GRADIENT, dp=1, minDist=60,
                             param1=80, param2=22, minRadius=18, maxRadius=45)
        return [] if c is None else [(x + x0, y + y0, r) for x, y, r in c[0]]

    col_c = sorted(find_circles(1150, 200, 2150, 400), key=lambda c: c[0])
    row_c = sorted(find_circles(880, 450, 1090, 1900), key=lambda c: c[1])
    if len(col_c) != len(NAMED_X) or len(row_c) != len(NAMED_Y):
        print(f"หน้า{page}: SKIP — circles {len(col_c)}/{len(NAMED_X)} cols, "
              f"{len(row_c)}/{len(NAMED_Y)} rows (sheet layout differs)")
        return
    sx, ox = np.polyfit([l["pos_m"] for l in NAMED_X], [c[0] for c in col_c], 1)
    sy, oy = np.polyfit([l["pos_m"] for l in NAMED_Y], [c[1] for c in row_c], 1)
    assert abs(sx - sy) / sx < 0.02, f"axis scale mismatch {sx:.2f} vs {sy:.2f}"

    def to_px(x_m, y_m):
        return x_m * sx + ox, y_m * sy + oy

    base = Image.open(img_path).convert("RGBA")
    try:
        font = ImageFont.truetype("arial.ttf", 30)
        thfont = ImageFont.truetype(r"C:\Windows\Fonts\LeelawUI.ttf", 56)
    except OSError:
        font = thfont = ImageFont.load_default()

    def render_layer(elements, color, caption):
        img = base.copy()
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)
        drawn = sum(bool(draw_element(draw, to_px, e, color, font))
                    for e in elements)
        out = Image.alpha_composite(img, ov)
        d2 = ImageDraw.Draw(out)
        d2.rectangle([120, 30, 1700, 120], fill=(255, 255, 255, 235))
        d2.text((140, 42), f"{caption} — วางตำแหน่งได้ {drawn}/{len(elements)}",
                fill=color + (255,), font=thfont)
        return out, drawn

    gt_els = [e for f in gt_matches
              for e in json.loads(f.read_text(encoding="utf-8")).get("elements", [])
              if isinstance(e, dict)]
    ai_els = [e for v in (json.loads(ai_path.read_text(encoding="utf-8"))
                          .get("parsed") or {}).get("views", [])
              if isinstance(v, dict)
              for e in v.get("elements", []) if isinstance(e, dict)]

    gt_img, gt_drawn = render_layer(gt_els, GREEN, "ground truth (คนตรวจแล้ว)")
    ai_img, ai_drawn = render_layer(ai_els, ORANGE, "AI t02")

    combo = Image.new("RGB", (base.width * 2 + 20, base.height), (60, 60, 60))
    combo.paste(gt_img.convert("RGB"), (0, 0))
    combo.paste(ai_img.convert("RGB"), (base.width + 20, 0))
    combo.save(out_path, "PNG")
    print(f"หน้า{page}: GT {gt_drawn}/{len(gt_els)} | AI {ai_drawn}/{len(ai_els)} -> {out_path.name}")


for page in (sys.argv[1:] or ["26", "27"]):
    render_page(page)
