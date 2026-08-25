#!/usr/bin/env python3
"""overlay_gt_vs_ai.py — วาดทับหน้าแบบจริง: ซ้าย = ground truth (เขียว), ขวา = AI (ส้ม)

ทั่วไปกว่า tune_ai/t02/overlay_gt_vs_ai_house09.py (ตัวนั้นล็อกบ้าน 09 ไว้ตายตัว):
บ้านไหนก็ได้ รอบโมเดลไหนก็ได้ และรับผล AI ได้ 2 ทรง โดยเดาเอง

  t02:  <ai>/<ชื่อบ้าน>_หน้าNN.json  ที่ห่อด้วย {ok, parsed, raw_text, grammar}
  t03:  <ai>/<house>__<gtstem>__<subtask>.txt  (ข้อความดิบจาก infer_house_t03.py)
        หนึ่งหน้ามีหลาย subtask -> รวม elements ของทุกไฟล์ในหน้านั้นเข้าด้วยกัน

วิธีหาพิกัด: HoughCircles หาวงกลมป้ายชื่อเส้นกริดบนหน้าสแกน -> จับคู่กับ pos_m ใน
grid master -> fit เส้นตรงต่อแกน -> grid_ref กลายเป็นพิกัด px
(ต่างจาก t02 ตรงที่ไม่ได้ crop ตำแหน่งวงกลมไว้ล่วงหน้า — สแกนทั้งหน้าแล้วคัดกลุ่มที่
fit เข้ากับ pos_m จริงเท่านั้น จึงย้ายบ้าน/ย้ายหน้าได้)

    python overlay_gt_vs_ai.py --house 08 \
        --ai "../../t02/ผล/08บ้าน_เล็ก_1ชั้น_03" --label "AI t02" --out ผล_overlay
"""
import argparse
import itertools
import json
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TRAIN = Path(__file__).resolve().parents[3]
GT_ROOT = TRAIN / "json_แก้ไขแล้ว"
IMG_ROOT = TRAIN / "image"

GREEN = (40, 200, 70)
ORANGE = (255, 140, 0)

_DIGIT = re.compile(r"\d")
_PAGE = re.compile(r"หน้า(\d+)")

# --- เกณฑ์คัดกลุ่มวงกลม (ปรับได้ถ้าเจอแบบที่สแกนคนละความละเอียด) ---
ALIGN_TOL_PX = 20        # วงกลมป้ายกริดบนเส้นเดียวกันเยื้องกันได้ไม่เกินนี้
MIN_SPAN_FRAC = 0.10     # กลุ่มต้องกินความกว้าง/สูงหน้าอย่างน้อยเท่านี้ (กันตราครุฑ)
MAX_RESID_FRAC = 0.02    # residual สูงสุดเทียบ span ถึงจะถือว่า fit กับ pos_m จริง
MAX_GROUP_EXTRA = 8      # กลุ่มที่มีวงกลมเกินจำนวนกริด +นี่ = ขยะ ข้ามไป
SCALE_TOL = 0.03         # สเกลสองแกนต้องใกล้กัน (แบบเขียนสเกลเดียว)


# ---------------------------------------------------------------- อ่านไฟล์ผล


def strip_fence(text):
    """ข้อความดิบจากโมเดล -> สตริง JSON (ตัด ```json fence + comma เกิน)"""
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    t = m.group(1).strip() if m else t
    return re.sub(r",(\s*[}\]])", r"\1", t)


def iter_elements(doc):
    """elements ทั้งหมด ไม่ว่าจะอยู่ใต้ elements[] หรือ views[].elements[]"""
    out = []
    if not isinstance(doc, dict):
        return out
    buckets = [doc.get("elements")]
    buckets += [v.get("elements") for v in (doc.get("views") or [])
                if isinstance(v, dict)]
    for b in buckets:
        if isinstance(b, list):
            out += [e for e in b if isinstance(e, dict)]
    return out


def page_of(name):
    m = _PAGE.search(name)
    return m.group(1) if m else None


def load_ai_pages(ai_dir):
    """-> {page: (elements, note)} รองรับทั้งทรง t02 และ t03 โดยเดาจากไฟล์ในโฟลเดอร์"""
    txts = sorted(ai_dir.glob("*__*__*.txt"))
    pages = {}
    if txts:                                                   # ---- t03
        by_page = {}
        for f in txts:
            pg = page_of(f.stem)
            if pg:
                by_page.setdefault(pg, []).append(f)
        for pg, files in by_page.items():
            els, bad = [], 0
            for f in files:
                try:
                    els += iter_elements(json.loads(strip_fence(f.read_text(encoding="utf-8"))))
                except Exception:
                    bad += 1
            note = f"{len(files)} subtask" + (f", JSON เสีย {bad}" if bad else "")
            pages[pg] = (els, note)
        return pages, "t03"
    for f in sorted(ai_dir.glob("*_หน้า*.json")):               # ---- t02
        pg = page_of(f.stem)
        if not pg:
            continue
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pages[pg] = ([], "อ่านไฟล์ไม่ได้")
            continue
        parsed = doc.get("parsed") if isinstance(doc, dict) else None
        if parsed is None and isinstance(doc, dict) and ("elements" in doc or "views" in doc):
            parsed = doc                                        # ไม่มี wrapper ก็รับได้
        pages[pg] = (iter_elements(parsed), "" if doc.get("ok", True) else "ok=false")
    return pages, "t02"


def load_gt_pages(gt_dir):
    pages = {}
    for f in sorted(gt_dir.glob("*_หน้า*.json")):
        if "หน้า00_gridline" in f.stem:
            continue
        pg = page_of(f.stem)
        if not pg:
            continue
        try:
            els = iter_elements(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            els = []
        pages.setdefault(pg, []).extend(els)
    return pages


# ---------------------------------------------------------- กริด -> พิกัด px


class Grid:
    def __init__(self, grid_json):
        g = json.loads(grid_json.read_text(encoding="utf-8"))["grid"]
        self.x_m = {l["id"]: l["pos_m"] for l in g["x_lines"]}
        self.y_m = {l["id"]: l["pos_m"] for l in g["y_lines"]}
        self.named_x = [l["pos_m"] for l in g["x_lines"] if l.get("type") != "dummy"]
        self.named_y = [l["pos_m"] for l in g["y_lines"] if l.get("type") != "dummy"]

    def point(self, ref):
        """'D1' -> (x_m, y_m); None ถ้าแยกไม่ออกหรือไม่รู้จัก id"""
        m = _DIGIT.search(ref)
        if not m:
            return None
        y_id, x_id = ref[: m.start()], ref[m.start():]
        if x_id in self.x_m and y_id in self.y_m:
            return self.x_m[x_id], self.y_m[y_id]
        return None

    def zone(self, ref):
        """'F-E x 1'-2'' -> ((y0,y1),(x0,x1)) เป็นเมตร; None ถ้าแยกไม่ออก"""
        if "x" not in ref:
            return None
        left, _, right = ref.partition("x")
        ys = [s.strip() for s in left.strip().split("-")]
        xs = [s.strip() for s in right.strip().split("-")]
        if len(ys) != 2 or len(xs) != 2:
            return None
        if not all(y in self.y_m for y in ys) or not all(x in self.x_m for x in xs):
            return None
        return ((self.y_m[ys[0]], self.y_m[ys[1]]),
                (self.x_m[xs[0]], self.x_m[xs[1]]))


def _line_groups(circles, key, tol=ALIGN_TOL_PX):
    """จัดวงกลมเป็นกลุ่มที่ค่าแกน key ใกล้กัน (= อยู่บนเส้นเดียวกัน)

    ใช้หน้าต่างรอบวงกลมแต่ละวง ไม่ใช่ chaining แบบต่อกันไปเรื่อย — เพราะวงกลมขยะใน
    ตราครุฑ/ตารางชื่อแบบทำหน้าที่เป็นสะพานเชื่อมทุกกลุ่มเข้าด้วยกันจนเหลือกลุ่มเดียว
    (เจอจริงบนหน้า21 ที่มีสองแปลนวางคู่กัน)
    """
    # ponytail: O(n²) แต่ n ≈ 50 วง/หน้า — ไม่คุ้มทำ interval tree
    seen, groups = set(), []
    for a in circles:
        member = frozenset(i for i, c in enumerate(circles)
                           if abs(c[key] - a[key]) <= tol)
        if member not in seen:
            seen.add(member)
            groups.append([circles[i] for i in member])
    return groups


def _fit_group(group, pos_m, idx, dim):
    """subset ของ group ทุกชุดที่ fit กับ pos_m ได้ -> [(resid, slope, offset, anchor), ...]
    anchor = พิกัดอีกแกนของวงกลมที่ใช้ (ป้ายคอลัมน์อยู่แถว y ไหน / ป้ายแถวอยู่คอลัมน์ x ไหน)

    คืนทุกชุดไม่ใช่ชุดที่ดีที่สุด เพราะหน้าเดียวมักมีสองแปลนวางคู่กัน (เช่นหน้า19
    ฐานรากแผ่ + ฐานรากตอกเข็ม) ป้ายคอลัมน์ของทั้งสองแปลนอยู่แถวเดียวกัน = กลุ่มเดียวกัน
    ถ้าเอาแต่ resid ต่ำสุดจะได้แปลนใดแปลนหนึ่งแบบเงียบๆ โดยไม่รู้ว่ามีอีกอัน
    """
    n = len(pos_m)
    if len(group) < n or len(group) > n + MAX_GROUP_EXTRA:
        return []
    med_r = float(np.median([c[2] for c in group]))
    keep = sorted((c for c in group if 0.65 * med_r <= c[2] <= 1.35 * med_r),
                  key=lambda c: c[idx])
    if len(keep) < n:
        return []
    fits = {}
    for combo in itertools.combinations(keep, n):
        px = [c[idx] for c in combo]
        span = px[-1] - px[0]
        if span < MIN_SPAN_FRAC * dim:
            continue
        for pos in (pos_m, pos_m[::-1]):        # เผื่อแบบกลับด้าน
            s, o = np.polyfit(pos, px, 1)
            resid = max(abs(p - (m * s + o)) for p, m in zip(px, pos))
            if resid > MAX_RESID_FRAC * span:
                continue
            key = (round(s, 1), round(o / 10))
            if key not in fits or resid < fits[key][0]:
                fits[key] = (resid, s, o, float(np.median([c[1 - idx] for c in combo])))
    return list(fits.values())


def grid_instances(img_path, grid):
    """-> (instances, msg). instances = [(resid, sx, ox, sy, oy)] เรียงซ้าย->ขวา, บน->ล่าง"""
    gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return [], "เปิดภาพไม่ได้"
    h, w = gray.shape
    found = cv2.HoughCircles(cv2.medianBlur(gray, 5), cv2.HOUGH_GRADIENT, dp=1,
                             minDist=40, param1=80, param2=22,
                             minRadius=15, maxRadius=55)
    if found is None or len(found[0]) < len(grid.named_x) + len(grid.named_y):
        n = 0 if found is None else len(found[0])
        return [], f"เจอวงกลมแค่ {n} วง"
    circles = [tuple(map(float, c)) for c in found[0]]

    # ป้ายคอลัมน์ = เรียงกันตาม y (ต่างกันที่ x) / ป้ายแถว = เรียงกันตาม x
    col = [f for gp in _line_groups(circles, 1) for f in _fit_group(gp, grid.named_x, 0, w)]
    row = [f for gp in _line_groups(circles, 0) for f in _fit_group(gp, grid.named_y, 1, h)]
    if not col or not row:
        return [], (f"fit ไม่ผ่าน (คอลัมน์ {len(col)} ชุด / แถว {len(row)} ชุด; "
                    f"ต้องการวงกลม {len(grid.named_x)}+{len(grid.named_y)} วงที่เรียงตรงกับ pos_m)")

    def near(v, lo, hi):
        """ป้ายต้องอยู่ติดแปลนที่มันกำกับ — ห่างออกนอกกรอบกริดได้ไม่เกิน 1 ช่วงกริด
        (กันการจับป้ายแถวของแปลนซ้ายไปคู่กับป้ายคอลัมน์ของแปลนขวา และกันวงกลมในตารางชื่อแบบ)"""
        return lo - (hi - lo) <= v <= hi + (hi - lo)

    inst = {}
    for rx, sx, ox, y_c in col:
        x_lo, x_hi = sorted((grid.named_x[0] * sx + ox, grid.named_x[-1] * sx + ox))
        for ry, sy, oy, x_r in row:
            if abs(abs(sx) - abs(sy)) / max(abs(sx), abs(sy)) > SCALE_TOL:
                continue
            y_lo, y_hi = sorted((grid.named_y[0] * sy + oy, grid.named_y[-1] * sy + oy))
            if not (near(x_r, x_lo, x_hi) and near(y_c, y_lo, y_hi)):
                continue
            key = (round(ox / 10), round(oy / 10))      # แปลนเดียวกัน = จุดกำเนิดเดียวกัน
            if key not in inst or rx + ry < inst[key][0]:
                inst[key] = (rx + ry, sx, ox, sy, oy)
    if not inst:
        return [], "สเกลสองแกนไม่ตรงกัน — ไม่เชื่อว่าเป็นวงกลมกริดจริง"

    # แบบสถาปัตย์แน่นๆ (หน้า06) มีวงกลมป้ายประตู/หน้าต่าง/บับเบิลรูปตัดเต็มไปหมด จึงเกิด
    # ชุดที่ "fit ได้" โดยบังเอิญเป็นสิบ — คัดด้วย residual เทียบชุดที่ดีที่สุด แล้วยุบชุดที่
    # จุดกำเนิดใกล้กันให้เหลืออันเดียว (= แปลนเดียวกัน คนละ subset ของวงกลม)
    cand = sorted(inst.values())
    span = abs(grid.named_x[-1] - grid.named_x[0]) * abs(cand[0][1])
    keep = []
    for c in cand:
        if c[0] > cand[0][0] * 3 + 2:
            break
        if all(np.hypot(c[2] - k[2], c[4] - k[4]) > 0.5 * span for k in keep):
            keep.append(c)
    return sorted(keep, key=lambda t: (t[2], t[4])), ""


# ------------------------------------------------------------------- วาดทับ


def draw_element(draw, to_px, grid, e, color, font):
    """-> (drawn, fail_kind, fail_sample)"""
    eid = str(e.get("element_id") or e.get("mark") or e.get("element_type") or "?")
    line_fill, text_fill, rect_fill = color + (150,), color + (255,), color + (45,)

    def label(x, y):
        draw.text((x + 8, y - 38), eid, fill=text_fill, font=font)

    s, t = e.get("grid_ref_start"), e.get("grid_ref_end")
    if isinstance(s, str) and isinstance(t, str):
        ps, pt = grid.point(s.strip()), grid.point(t.strip())
        if ps and pt:
            x0, y0 = to_px(*ps)
            x1, y1 = to_px(*pt)
            draw.line([(x0, y0), (x1, y1)], fill=line_fill, width=12)
            label((x0 + x1) / 2, (y0 + y1) / 2)
            return True, None, None
        return False, "คู่ปลายคาน", f"{s} -> {t}"

    refs = e.get("grid_refs") or e.get("grid_ref") or []
    if isinstance(refs, str):
        refs = [r.strip() for r in refs.split(",")]
    if not refs:
        return False, "ไม่มี grid_ref", eid
    drawn, bad = False, None
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            continue
        ref = ref.strip()
        z = grid.zone(ref)
        if z:
            (ya, yb), (xa, xb) = z
            x0, y0 = to_px(xa, ya)
            x1, y1 = to_px(xb, yb)
            if abs(y0 - y1) < 2 or abs(x0 - x1) < 2:
                draw.line([(x0, y0), (x1, y1)], fill=line_fill, width=12)
            else:
                draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)],
                               fill=rect_fill, outline=line_fill, width=6)
            label((x0 + x1) / 2, (y0 + y1) / 2)
            drawn = True
            continue
        p = grid.point(ref)
        if p:
            x, y = to_px(*p)
            draw.ellipse([x - 22, y - 22, x + 22, y + 22], outline=line_fill, width=8)
            label(x, y)
            drawn = True
        elif bad is None:
            bad = ("โซน" if "x" in ref else "จุด", ref)
    if drawn:
        return True, None, None
    return (False,) + (bad or ("grid_ref ว่าง", eid))


def render_layer(base, to_px, grid, elements, color, caption, font, thfont):
    img = base.copy()
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov)
    drawn, fails = 0, {}
    for e in elements:
        ok, kind, sample = draw_element(draw, to_px, grid, e, color, font)
        if ok:
            drawn += 1
        else:
            fails.setdefault(kind, sample)
    out = Image.alpha_composite(img, ov)
    d2 = ImageDraw.Draw(out)
    text = f"{caption} — วางตำแหน่งได้ {drawn}/{len(elements)}"
    box = d2.textbbox((140, 42), text, font=thfont)
    d2.rectangle([120, 30, box[2] + 20, max(box[3] + 12, 120)], fill=(255, 255, 255, 235))
    d2.text((140, 42), text, fill=color + (255,), font=thfont)
    return out, drawn, fails


def fail_note(fails, total, drawn):
    if drawn >= total:
        return ""
    bits = "; ".join(f"{k}: {v!r}" for k, v in fails.items())
    return f" [วางไม่ได้ {total - drawn} — {bits}]"


# ---------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--house", required=True, help="เลขนำหน้าโฟลเดอร์ เช่น 08")
    ap.add_argument("--ai", required=True, help="โฟลเดอร์ผล AI (ทรง t02 หรือ t03)")
    ap.add_argument("--label", default="AI", help="ข้อความบนแผงขวา")
    ap.add_argument("--out", required=True, help="โฟลเดอร์ปลายทาง")
    ap.add_argument("--pages", nargs="*", help="เลขหน้า เช่น 20 21 (ว่าง = ทุกหน้าที่มีทั้ง GT และผล AI)")
    ap.add_argument("--grid-instance", type=int, default=1,
                    help="หน้าที่มีหลายแปลนใช้กริดเดียวกัน: เลือกแปลนที่ N (1 = ซ้ายสุด/บนสุด)")
    ap.add_argument("--quality", type=int, default=85)
    a = ap.parse_args()

    gt_dirs = sorted(d for d in GT_ROOT.iterdir()
                     if d.is_dir() and d.name.startswith(a.house))
    if len(gt_dirs) != 1:
        raise SystemExit(f"หา GT ของบ้าน {a.house} ไม่เจอ/เจอหลายอัน: "
                         f"{[d.name for d in gt_dirs]}")
    gt_dir = gt_dirs[0]
    house_name = gt_dir.name[len(a.house):]
    img_dir = IMG_ROOT / house_name
    if not img_dir.is_dir():
        raise SystemExit(f"ไม่มีโฟลเดอร์ภาพ {img_dir}")
    grid_files = list(gt_dir.glob("*หน้า00_gridline.json"))
    if len(grid_files) != 1:
        raise SystemExit(f"ต้องมี grid master 1 ไฟล์ใน {gt_dir}, เจอ {len(grid_files)}")
    grid = Grid(grid_files[0])

    ai_dir = Path(a.ai)
    if not ai_dir.is_dir():
        raise SystemExit(f"ไม่มีโฟลเดอร์ผล AI {ai_dir}")
    ai_pages, style = load_ai_pages(ai_dir)
    gt_pages = load_gt_pages(gt_dir)

    pages = a.pages or sorted(set(gt_pages) & set(ai_pages))
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"บ้าน {gt_dir.name} | ผล AI ทรง {style} ({len(ai_pages)} หน้า) | "
          f"GT {len(gt_pages)} หน้า | จะวาด {len(pages)} หน้า")
    print(f"กริด: named {len(grid.named_x)} x {len(grid.named_y)} เส้น -> {out_dir}\n")

    try:
        font = ImageFont.truetype("arial.ttf", 30)
        thfont = ImageFont.truetype(r"C:\Windows\Fonts\LeelawUI.ttf", 56)
    except OSError:
        font = thfont = ImageFont.load_default()

    done = skipped = 0
    for pg in pages:
        img_path = img_dir / f"{house_name}_หน้า{pg}.png"
        if not img_path.exists():
            print(f"หน้า{pg}: ข้าม — ไม่มีภาพ {img_path.name}")
            skipped += 1
            continue
        gt_els = gt_pages.get(pg, [])
        ai_els, ai_note = ai_pages.get(pg, ([], "ไม่มีผล AI"))
        if not gt_els and not ai_els:
            print(f"หน้า{pg}: ข้าม — ไม่มี element ทั้งสองฝั่ง")
            skipped += 1
            continue

        inst, msg = grid_instances(img_path, grid)
        if not inst:
            print(f"หน้า{pg}: ข้าม — {msg} (GT {len(gt_els)} / AI {len(ai_els)} element)")
            skipped += 1
            continue
        k = min(a.grid_instance, len(inst)) - 1
        _, sx, ox, sy, oy = inst[k]
        def to_px(xm, ym, sx=sx, ox=ox, sy=sy, oy=oy):
            return xm * sx + ox, ym * sy + oy
        msg = f"สเกล {abs(sx):.1f} px/m"
        tail = ""
        if len(inst) > 1:
            # หน้าเดียวมีหลายแปลนที่ใช้กริดชุดเดียวกัน — วาดได้ทีละแปลน เลือกด้วย --grid-instance
            tail = f" (กริดชุดที่ {k + 1}/{len(inst)} บนหน้านี้)"
            msg += f" | พบกริด {len(inst)} ชุด ใช้ชุดที่ {k + 1} (x≈{ox:.0f}) — เปลี่ยนด้วย --grid-instance"

        base = Image.open(img_path).convert("RGBA")
        gt_img, gt_n, gt_f = render_layer(base, to_px, grid, gt_els, GREEN,
                                          "ground truth (คนตรวจแล้ว)" + tail, font, thfont)
        ai_img, ai_n, ai_f = render_layer(base, to_px, grid, ai_els, ORANGE,
                                          a.label + tail, font, thfont)
        print(f"หน้า{pg}: {msg} | GT {gt_n}/{len(gt_els)}{fail_note(gt_f, len(gt_els), gt_n)}")
        print(f"        {' ' * len(msg)} | {a.label} {ai_n}/{len(ai_els)}"
              f"{' (' + ai_note + ')' if ai_note else ''}"
              f"{fail_note(ai_f, len(ai_els), ai_n)}")
        if gt_n == 0 and ai_n == 0:
            # ไม่มีอะไรวางได้เลย = ภาพจะเป็นหน้าเปล่าซ้ำสองแผง ไม่มีประโยชน์ และหน้าที่ไม่ใช่
            # แปลน (สารบัญ/รูปด้าน) บางทีก็ fit วงกลมมั่วได้ — ไม่เขียนไฟล์ดีกว่า
            print("        -> ไม่เขียนไฟล์ (วางไม่ได้สักตัวทั้งสองฝั่ง)")
            skipped += 1
            continue

        combo = Image.new("RGB", (base.width * 2 + 20, base.height), (60, 60, 60))
        combo.paste(gt_img.convert("RGB"), (0, 0))
        combo.paste(ai_img.convert("RGB"), (base.width + 20, 0))
        out_path = out_dir / f"{gt_dir.name}_หน้า{pg}_overlay.jpg"
        combo.save(out_path, "JPEG", quality=a.quality)
        done += 1

    print(f"\nวาดได้ {done} หน้า, ข้าม {skipped} หน้า -> {out_dir}")


def _selftest():
    """python overlay_gt_vs_ai.py --selftest — เช็คตัวแยก ref + ตัว fit กริด"""
    import tempfile
    gj = {"grid": {"x_lines": [{"id": "1", "pos_m": 0.0}, {"id": "2", "pos_m": 4.0},
                               {"id": "3", "pos_m": 7.0},
                               {"id": "3'", "pos_m": 7.6, "type": "dummy"}],
                   "y_lines": [{"id": "D", "pos_m": 0.0}, {"id": "C", "pos_m": 4.0},
                               {"id": "A", "pos_m": 9.5}]}}
    p = Path(tempfile.mkdtemp()) / "g.json"
    p.write_text(json.dumps(gj), encoding="utf-8")
    g = Grid(p)
    assert g.point("D1") == (0.0, 0.0)
    assert g.point("A3'") == (7.6, 9.5)          # dummy ใช้อ้างอิงได้ แค่ไม่ใช้ fit
    assert g.point("Z9") is None
    assert g.point("ไม่มีเลข") is None
    assert g.zone("D-C x 1-3") == ((0.0, 4.0), (0.0, 7.0))
    assert g.zone("B2-B2 x D-D") is None          # ทรงที่ AI มักหลอน -> ต้องตกเป็น fail
    assert g.named_x == [0.0, 4.0, 7.0] and len(g.named_y) == 3

    # fit: วงกลมจริง 3 คอลัมน์ + ขยะปนกลุ่ม, สเกล 80 px/m, offset 100
    circles = [(100.0, 400.0, 28.0), (420.0, 400.0, 28.0), (660.0, 400.0, 28.0),
               (500.0, 405.0, 9.0)]
    fits = _fit_group(circles, g.named_x, 0, 2000)
    assert len(fits) == 1 and abs(fits[0][1] - 80.0) < 1e-6, fits

    assert _fit_group(circles[:2], g.named_x, 0, 2000) == []         # วงไม่พอ
    assert _fit_group([(0.0, 0.0, 28.0), (10.0, 0.0, 28.0), (20.0, 0.0, 28.0)],
                      g.named_x, 0, 2000) == []                      # span เล็กเกิน

    # สองแปลนวางคู่กัน ป้ายคอลัมน์อยู่แถวเดียวกัน -> ต้องเจอทั้งสองชุด ไม่ใช่ชุดเดียว
    # (ชุดข้าม-แปลนก็หลุด residual มาได้เพราะกริด 3 เส้น fit ได้ง่าย — ตัวคัดจริงคือ
    #  การเทียบสเกลสองแกนใน grid_instances ซึ่งเหลือแต่ slope ที่ตรงกันจริง)
    two = circles[:3] + [(1100.0, 400.0, 28.0), (1420.0, 400.0, 28.0), (1660.0, 400.0, 28.0)]
    real = [f for f in _fit_group(two, g.named_x, 0, 2000) if abs(f[1] - 80.0) < 0.5]
    assert sorted(round(f[2]) for f in real) == [100, 1100], real
    assert len(_line_groups(two + [(900.0, 900.0, 28.0)], 1)) == 2
    assert strip_fence('```json\n{"a":[1,2,],}\n```') == '{"a":[1,2]}'
    assert len(iter_elements({"views": [{"elements": [{}, {}]}], "elements": [{}]})) == 3
    assert page_of("บ้าน_x_หน้า20_beam_plan") == "20"
    print("selftest ok")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
