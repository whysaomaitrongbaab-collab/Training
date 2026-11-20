#!/usr/bin/env python3
"""
tools/gridlab_probe.py — โพรบ (ไม่ใช่ส่วนของ pipeline) ของ "grid lab" ส่วน 3 แขนแปลน บนไฟล์เวกเตอร์
ประชุม 18->19 พ.ย. 2569: ขั้นต่ำ = "วาดเส้นกริดบนแบบให้ตรงตำแหน่งจริง เริ่มจากไฟล์เวกเตอร์"

ไฟล์นี้ทำ 3 อย่าง และวัดแล้ว (ข้อ 3 = ขั้นต่ำของ King: วาดเส้นกริดลงบนภาพ ดู --draw):
  1. หาเส้นกริดจากเส้นเวกเตอร์: เส้นที่ตำแหน่งตั้งฉากเดียวกันมี "ท่อน" (dash-dot ถูกระเบิดเป็นท่อน) >= 10 ท่อน
     ยาว >= 25% ของด้านยาวหน้า แล้วเอากลุ่มที่ "ปลายเส้นเริ่มที่เดียวกัน" (±4 pt) มากสุด = ปลายที่วงกลมหัวกริด
  2. ผูกชื่อหัวกริด (ตัวอักษร/เลข 1 ตัวในข้อความฝัง) ที่อยู่ใกล้ปลายเส้น (<=30 pt) ตรงกับตำแหน่งเส้น (±14 pt)

  3. วาดเส้นที่จับได้ + ชื่อ ('?' = ผูกไม่ได้) ลงบนภาพหน้านั้น (--draw) — เปิดดูภาพจริง 3 บ้านแล้ว เส้นอยู่ตรงกริดจริง
     (1ชั้น_27, 1ชั้น_30, 174); ตรวจด้วยตา ไม่ได้วัดเป็นตัวเลข

2026-11-20: เพิ่มตัวกรอง "เส้นประจริง" (>=60% ของรอยต่อระหว่างท่อนต้องมีช่องว่าง > 0.3 pt) — เส้นทึบที่ถูกขีดมิติตัดเป็นท่อน
ไม่ถูกนับเป็นกริดอีก: --eval ตรงเฉลยยังเท่าเดิม 54 แกน (judged 189 จาก 192) และบ้าน 174 หน้า 10 เส้นนอนได้ A,C,D,E ถูก 4 จาก 5
(ขาด B; เดิมเลือกผิดกลุ่มทั้งหมด); ลองตัดสายท่อนที่ช่องว่าง > 40 pt แล้วตก 54 -> 46 จึงปิดไว้ (CHAIN_BREAK=1e9) ผลข้างเคียง:
เส้นตั้งบางเส้นของ 174 ลากยาวเกินลงไปถึงกรอบชื่อแบบ (draw_page ดึงกลับด้วย harmonize เฉพาะตอนวาด ไม่แก้ผลวัด)
ยังไม่ได้ทำ: ชื่อหัวกริดที่ถูกวาดเป็นเส้น (ต้อง OCR วงหัวกริด), หน้าที่มีสองแปลน (จับกลุ่มใหญ่สุดกลุ่มเดียว เห็นที่ 1ชั้น_27 หน้า 10),
pos_m (ยังต้องมาจาก grid master + vector_ruler.py)

ผลวัด 2026-11-19 (รันซ้ำได้ด้วย --eval: หน้าแปลน 2 หน้าแรกของแต่ละบ้านที่ 12 หน้าแรกมีข้อความฝัง และมีเฉลย
grid master — 192 แกนที่ตัดสินได้ ใช้เวลา ~50 วินาที):
  - ผูกชื่อได้ตรงชุดเฉลยเป๊ะ 54/192 แกน (28%) · บางส่วน 6 · ไม่ตรงเลย 132 (69%)
    (ตอนสำรวจก่อนรวมไฟล์ ใช้ชุดแคบกว่า = 53 บ้านที่มีรหัสแผ่นเป็นข้อความในแถบ: 126 แกน เป๊ะ 54 (43%) ไม่ตรงเลย 66 —
    ตัวหารต่างกัน ตัวตั้งเท่ากัน 54 แกน; ตัวเลขชุดแคบไม่ใช่ผลของ --eval)
  - สาเหตุที่ไม่ตรงเลย: ตัวอักษรหัวกริดไม่ได้เป็นข้อความฝัง (ถูกวาดเป็นเส้น เหมือนกรอบชื่อแบบบ้าน 174) หรือไม่มีเส้น
    ผู้สมัครเลย (เส้นกริดเป็นเส้นทึบ ไม่ใช่ dash-dot -> เกณฑ์ >=10 ท่อนตกหมด) หรือหน้าแปลนเป็นภาพในบ้านที่ปนกัน
  - จำนวนเส้นที่จับได้ == จำนวนเส้น named ใน grid master (วัดตอนสำรวจ ชุด 98 หน้า): แกน x 37 หน้า, แกน y 29 หน้า
  - บ้าน 174 (A1 CAD, หน้า 10): เส้นตั้ง 6/6 เส้นจริงอยู่ในผู้สมัคร และกลุ่มปลายเริ่ม y=187 เท่ากันพอดี 6 เส้น
    แต่ "กลุ่มปลายตรงกันใหญ่สุด" ของเส้นนอนเลือกผิดกลุ่ม (ได้ 5 เส้นที่ไม่ใช่กริด A-E; กริดจริง 4 เส้นอยู่ในกลุ่ม
    ปลายเริ่ม x=321) และชื่อหัวกริดอ่านไม่ได้ (ตัวอักษรเป็นเส้น) — กฎเลือกกลุ่มต้องฉลาดกว่า "ใหญ่สุด"
  ผลลบที่ต้องรู้ (ลองแล้ว ไม่ใช้ — วัดด้วยสคริปต์ชั่วคราวชุด 126 แกนข้างบน ไม่อยู่ในไฟล์นี้ รันซ้ำไม่ได้จากที่นี่):
  - หา pos_m จาก "มาตราส่วนที่พิมพ์" (1:75 ในข้อความฝัง) ถูกแค่ 14/126 แกน: มาตราส่วนจริงใน PDF ต่างจากที่พิมพ์
    (บ้าน 1ชั้น_27: ระยะเส้น 105 pt = 3.0 ม. ตรงเป๊ะทุกช่อง -> 35.0 pt/m แต่ 1:75 ควรได้ 37.8) ตรงกับที่
    server/purson-worker/vector_ruler.py เตือนไว้ ห้ามเชื่อโน้ตมาตราส่วน
  - หา pos_m จากตัวเลขมิติ (8.00 / 3.00) ที่อยู่ระหว่างเส้น: 0/126 แกน — ตัวเลขมิติไม่อยู่ในข้อความฝังของหน้าที่ลอง
    (ต้องอ่านจากภาพ/โมเดล) ส่วน "geometry อย่างเดียวบอกมาตราส่วนไม่ได้" เป็นข้อโต้แย้ง ไม่ใช่ตัวเลขที่วัด: มาตราส่วนที่ต่างกันเป็นเท่า
    (35 vs 17.5 pt/m) ให้ระยะที่ "ตัวเลขกลม" เหมือนกัน
  => ข้อสรุป: vector ให้ "ตำแหน่ง+ชื่อเส้น" ได้บนบางหน้า แต่ pos_m ต้องมาจาก grid master ที่โมเดลอ่าน/ตัวเลขมิติ
     แล้วใช้ vector_ruler.py ผูกเข้าด้วยกัน (งานแบ่งเดิมของ worker ไม่ต้องเปลี่ยน)

    python tools/gridlab_probe.py --page <บ้าน> <เลขหน้า>     # พิมพ์เส้น+ชื่อที่จับได้ของหน้านั้น
    python tools/gridlab_probe.py --draw <บ้าน> <เลขหน้า> <ไฟล์.png>   # วาดเส้น+ชื่อที่จับได้ลงภาพหน้านั้น
    python tools/gridlab_probe.py --eval                       # วัดเทียบ grid master (ใช้เวลา ~1 นาที)
    python tools/gridlab_probe.py --demo                       # self-check ไม่ต้องมีไฟล์จริง
"""
import argparse
import collections
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_PIECES = 10      # ตรงกับ vector_ruler.MIN_PIECES (ลายเส้นประของเส้น named >= 10 ท่อน)
MIN_SPAN_FRAC = 0.25  # ยาวอย่างน้อยเท่านี้ของด้านยาวหน้า (vector_ruler ใช้ 0.05 แต่ที่นี่ต้องกรองหนักกว่าเพราะไม่มี master)
PERP_TOL = 0.75      # pt: ท่อนที่ห่างกันไม่เกินนี้ = เส้นเดียวกัน
END_TOL = 4.0        # pt: ปลายเส้นเริ่มที่เดียวกัน = วงกลมหัวกริดแถวเดียวกัน
LABEL_RE = re.compile(r"^(?:[A-Z]|\d{1,2})$")


MIN_DASHED = 0.6     # เส้นประจริงต้องมีช่องว่างระหว่างท่อน: >= สัดส่วนนี้ของรอยต่อต้องห่าง > GAP_MIN pt
GAP_MIN = 0.3        # เส้นทึบที่ถูกขีดมิติ/ลูกศรตัดเป็นท่อนจะชนกัน (ช่องว่าง ~0) -> ไม่ใช่เส้นกริด (เห็นที่บ้าน 174)
CHAIN_BREAK = 1e9    # pt: ตัดสายท่อนที่ช่องว่างใหญ่กว่านี้ — ปิดไว้ (1e9): วัดแล้วตัดที่ 40 pt ทำให้ผูกชื่อได้ตรงเฉลยตก 54 -> 46 แกน
                     # (ผลข้างเคียง: เส้นอาจลากยาวเกินไปถึงกรอบชื่อแบบเมื่อมีเส้นอื่นอยู่ตำแหน่งเดียวกัน เช่นบ้าน 174 เส้นที่ 4 และ 6)


def longest_chain(segs):
    """segs = [(lo, hi)] เรียงตาม lo -> สายท่อนที่ต่อกันเป็นเส้นเดียวที่ยาวที่สุด (ตัดที่ช่องว่าง > CHAIN_BREAK)"""
    best, cur = [], []
    for sg in segs:
        if cur and sg[0] - max(c[1] for c in cur) > CHAIN_BREAK:
            if (max(c[1] for c in cur) - cur[0][0]) > (max(c[1] for c in best) - best[0][0] if best else -1):
                best = cur
            cur = []
        cur.append(sg)
    if cur and (not best or (max(c[1] for c in cur) - cur[0][0]) > (max(c[1] for c in best) - best[0][0])):
        best = cur
    return best


def dashed_fraction(chain):
    """สัดส่วนรอยต่อระหว่างท่อนติดกันที่มีช่องว่างจริง (เส้นประ) — 1.0 = ประล้วน, 0 = ทึบที่ถูกตัด"""
    gaps = [chain[i + 1][0] - chain[i][1] for i in range(len(chain) - 1)]
    return sum(g > GAP_MIN for g in gaps) / len(gaps) if gaps else 0.0


def aligned(cands, tol=END_TOL):
    """cands = [(pos, pieces, lo, hi)] -> กลุ่มที่ lo (ปลายเริ่ม) ตรงกันมากสุด"""
    best = []
    for c in cands:
        g = [d for d in cands if abs(d[2] - c[2]) <= tol]
        if len(g) > len(best):
            best = g
    return best


def candidates(page):
    """คืน ({'v': [...], 'h': [...]}, (W, H)) พิกัดตามที่ตามองเห็น (คูณ rotation_matrix แล้ว)"""
    rm, W, H = page.rotation_matrix, page.rect.width, page.rect.height
    runs = {"v": collections.defaultdict(list), "h": collections.defaultdict(list)}
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1] * rm, it[2] * rm
            if abs(a.x - b.x) < 0.3 and abs(a.y - b.y) > 1.0:
                runs["v"][round(a.x / PERP_TOL)].append((min(a.y, b.y), max(a.y, b.y)))
            elif abs(a.y - b.y) < 0.3 and abs(a.x - b.x) > 1.0:
                runs["h"][round(a.y / PERP_TOL)].append((min(a.x, b.x), max(a.x, b.x)))
    out = {"v": [], "h": []}
    for ax in out:
        for k, segs in runs[ax].items():
            chain = longest_chain(sorted(segs))
            lo, hi = chain[0][0], max(c[1] for c in chain)
            if len(chain) >= MIN_PIECES and hi - lo >= MIN_SPAN_FRAC * max(W, H) and dashed_fraction(chain) >= MIN_DASHED:
                out[ax].append((round(k * PERP_TOL, 1), len(chain), round(lo), round(hi)))
        out[ax].sort()
    return out, (W, H)


def label_lines(page, lines, axis, reach=30.0, side=14.0):
    """ผูกตัวอักษร/เลข 1 ตัวที่ใกล้ปลายเส้น -> [(pos, label|None)]"""
    import fitz
    rm = page.rotation_matrix
    words = []
    for w in page.get_text("words"):
        if LABEL_RE.match(w[4]):
            r = fitz.Rect(w[:4]) * rm
            words.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, w[4]))
    out = []
    for pos, _, lo, hi in lines:
        best = None
        for cx, cy, t in words:
            across, along = (abs(cx - pos), min(abs(cy - lo), abs(cy - hi))) if axis == "v" \
                else (abs(cy - pos), min(abs(cx - lo), abs(cx - hi)))
            if across <= side and along <= reach and (best is None or along < best[0]):
                best = (along, t)
        out.append((pos, best[1] if best else None))
    return out


def pdf_of(house):
    p = ROOT / "image" / house / f"{house}.pdf"
    if not p.exists():
        sys.exit(f"ไม่พบ {p}")
    return p


def gt_ids(house):
    """({id named แกน x}, {id named แกน y}) จาก *_gridline.json — เฉลยแก้แล้วชนะ rawjson"""
    for base in ("json_แก้ไขแล้ว", "rawjson_ยังไม่ได้แก้ไขโดนคน"):
        for d in (ROOT / base).glob(f"*{house}"):
            for f in d.glob("*gridline*.json"):
                g = json.loads(f.read_text(encoding="utf-8")).get("grid", {})
                return ({str(l["id"]) for l in g.get("x_lines", []) if l.get("type") != "dummy"},
                        {str(l["id"]) for l in g.get("y_lines", []) if l.get("type") != "dummy"})
    return None


def plan_pages(house):
    pages = set()
    for base in ("json_แก้ไขแล้ว", "rawjson_ยังไม่ได้แก้ไขโดนคน"):
        for d in (ROOT / base).glob(f"*{house}"):
            for f in d.glob("*plan*.json"):
                m = re.search(r"หน้า(\d+)", f.name)
                if m:
                    pages.add(int(m.group(1)))
        if pages:
            break
    return sorted(pages)


def show_page(house, pn):
    import fitz
    page = fitz.open(pdf_of(house))[pn - 1]
    c, (W, H) = candidates(page)
    print(f"{house} หน้า {pn} ขนาด {W:.0f}x{H:.0f} pt")
    for ax, name in (("v", "เส้นตั้ง (x)"), ("h", "เส้นนอน (y)")):
        lines = aligned(c[ax])
        print(f"{name}: ผู้สมัคร {len(c[ax])} ปลายตรงกัน {len(lines)}")
        for pos, label in label_lines(page, sorted(lines), ax):
            print(f"   {pos:8.1f} pt  ชื่อ={label}")


def harmonize(lines):
    """เส้นกริดแถวเดียวกันควรยาวเท่ากัน: เส้นที่ปลายสุดเกิน/ขาดจากค่ากลางของกลุ่มมาก (ท่อนของเส้นอื่นที่อยู่ตำแหน่งเดียวกัน
    เช่นในกรอบชื่อแบบ) ถูกดึงกลับมาที่ค่ากลาง — ใช้ตอนวาดเท่านั้น ไม่แก้ผลที่ตรวจวัด"""
    if len(lines) < 3:
        return lines
    his = sorted(l[3] for l in lines)
    med = his[len(his) // 2]
    return [(pos, n, lo, hi if abs(hi - med) <= 0.1 * med else med) for pos, n, lo, hi in lines]


def draw_page(house, pn, out, dpi=110):
    """วาดเส้นกริดที่จับได้ลงบนภาพหน้านั้นแล้วบันทึกเป็น PNG — ขั้นต่ำของ King: 'วาดเส้นกริดบนแบบให้ตรงตำแหน่งจริง'
    เส้นตั้ง (แกน x) สีแดง เส้นนอน (แกน y) สีน้ำเงิน ป้ายชื่อหัวกริดที่ผูกได้ (ไม่ได้ = '?') พิกัดเส้นเป็นพิกัดตามที่ตามองเห็น
    จึงตรงกับพิกเซลของภาพที่ render ด้วยสเกล dpi/72 โดยตรง; คืน (จำนวนเส้นตั้ง, จำนวนเส้นนอน, ผูกชื่อได้กี่เส้น)"""
    import fitz
    from PIL import Image, ImageDraw, ImageFont
    page = fitz.open(pdf_of(house))[pn - 1]
    c, _ = candidates(page)
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGB")
    d, k = ImageDraw.Draw(img), dpi / 72.0
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    n, named = {"v": 0, "h": 0}, 0
    for ax, color in (("v", (220, 30, 30)), ("h", (30, 60, 220))):
        lines = sorted(aligned(c[ax]))
        for (pos, lo, hi), (_, label) in zip([(l[0], l[2], l[3]) for l in harmonize(lines)], label_lines(page, lines, ax)):
            a, b = ((pos * k, lo * k), (pos * k, hi * k)) if ax == "v" else ((lo * k, pos * k), (hi * k, pos * k))
            d.line([a, b], fill=color, width=3)
            tx, ty = (a[0] + 6, a[1] + 4) if ax == "v" else (a[0] + 4, a[1] - 26)
            d.text((tx, ty), label or "?", fill=color, font=font)
            n[ax] += 1
            named += label is not None
    img.save(out)
    return n["v"], n["h"], named


def evaluate():
    import fitz
    res, bad = collections.Counter(), []
    sv = [h.name for h in (ROOT / "image").iterdir() if h.is_dir()]
    for h in sorted(sv):
        ids = gt_ids(h)
        pp = plan_pages(h)[:2]
        if not ids or not pp:
            continue
        doc = fitz.open(pdf_of(h))
        if not any(len(p.get_text("words")) > 8 for p in list(doc)[:12]):
            continue  # ไม่มีข้อความฝัง (ภาพสแกน) — เกณฑ์นี้ใช้ไม่ได้
        for pn in pp:
            if pn > len(doc):
                continue
            page = doc[pn - 1]
            c, _ = candidates(page)
            for ax, gt in (("v", ids[0]), ("h", ids[1])):
                lines = aligned(c[ax])
                if len(lines) < 2 or len(gt) < 2:
                    res["skip"] += 1
                    continue
                found = {t for _, t in label_lines(page, sorted(lines), ax) if t}
                res["judged"] += 1
                if found == gt:
                    res["exact_label_set"] += 1
                elif gt <= found:
                    res["superset"] += 1
                elif found & gt:
                    res["partial"] += 1
                else:
                    res["none_match"] += 1
                    bad.append((h, pn, ax))
    print(dict(res))
    print("ไม่ตรงเลย (ตัวอย่าง):", bad[:6])


def demo():
    c = [(100.0, 30, 91, 751), (200.0, 30, 91, 751), (300.0, 28, 91, 751), (400.0, 12, 300, 700)]
    assert [x[0] for x in aligned(c)] == [100.0, 200.0, 300.0]       # เส้นที่ปลายเริ่มต่างออกไปถูกคัดทิ้ง
    assert aligned([]) == []
    assert LABEL_RE.match("A") and LABEL_RE.match("12") and not LABEL_RE.match("A-1") and not LABEL_RE.match("123")
    print("OK — self-check ผ่าน (ตรรกะคัดกลุ่ม/regex เท่านั้น ไม่ได้เทียบกับ PDF จริง ใช้ --eval)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", nargs=2, metavar=("บ้าน", "หน้า"))
    ap.add_argument("--draw", nargs=3, metavar=("บ้าน", "หน้า", "ไฟล์.png"), help="วาดเส้นกริดที่จับได้ลงภาพหน้านั้น")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if a.draw:
        print("เส้นตั้ง, เส้นนอน, ผูกชื่อได้:", draw_page(a.draw[0], int(a.draw[1]), a.draw[2]))
        return
    if a.page:
        return show_page(a.page[0], int(a.page[1]))
    if a.eval:
        return evaluate()
    ap.print_help()


if __name__ == "__main__":
    main()
