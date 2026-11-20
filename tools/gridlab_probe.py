#!/usr/bin/env python3
"""
tools/gridlab_probe.py — "grid lab" ส่วน 3 แขนแปลน บนไฟล์เวกเตอร์ (ยังเป็นโพรบ ไม่ใช่ส่วนของ worker)
ประชุม 18->19 พ.ย. 2569: ขั้นต่ำ = "วาดเส้นกริดบนแบบให้ตรงตำแหน่งจริง เริ่มจากไฟล์เวกเตอร์"
สเกลต่อหน้า + pos_m (เมตร) อยู่ที่ tools/gridlab_scale.py; รันทั้งเล่มคู่กับ title block ที่ tools/run_part1_part3.py

วิธี (2026-11-21, detect()): เริ่มจากวงหัวกริด ไม่ใช่จากเส้นประ
  1. วงกลมจากเวกเตอร์ (circles): ท่อน 'l'/'c' ที่ต่อกันจนปิด ระยะจุดบนเส้นถึงศูนย์กลางเท่ากัน ±10% เส้นผ่านศูนย์กลาง 6-45 pt
  2. หัวกริด (bubble_lines): เส้นตรงผ่านศูนย์กลางวง (±1 pt) แตะวงฝั่งเดียว — 'long' = เส้นกริดยาวพุ่งออก, 'stem' = ก้านสั้น
     (หลายแบบไม่วาดเส้นกริดทะลุแปลน) — ต้องมีวงขนาดเท่ากันก้านทิศเดียวกันอยู่แถวเดียวกันอย่างน้อยอีกวง (กันป้ายเดี่ยว)
     ตัดทิ้ง: วงที่มีเส้นพาดกลาง (วงอ้างอิงรูปตัด/แผ่น), เส้นเริ่มที่ศูนย์กลาง (จุดมุมกรอบ), เส้นแตะสองฝั่ง (เสาเข็ม/ป้ายพื้น
     ที่มีลูกศรสองข้าง/กากบาทโคมไฟ), เส้นยาวที่เริ่มห่างวงเกินครึ่งวง (ขีดตัวอักษรต่อกันเป็นสาย)
     รับเพิ่ม: วงที่ถูกยกพ้นแถวเพราะเส้นชิดกันไม่ถึง 1 วง (1'), วงเดี่ยวในแกนที่ไม่มีแถว (แปลนขยายที่มีกริดแกนนั้นเส้นเดียว)
  3. ชื่อ (bubble_labels): ข้อความฝังในวงก่อน ไม่มีค่อย OCR ข้างในวง (ทาขาวนอก 0.45d) — แถวที่ไม่มีชื่อเลยสักวงทิ้ง (confirmed)
  4. แกนเดียวกันในหน้าใช้ชื่อชนิดเดียวกัน (ตัวอักษร/ตัวเลข — consistent_labels) แล้วจับคู่แถววงแนวตั้งกับคอลัมน์วงแนวนอน
     เป็นแปลน (extend_to_plan: เลขแปลน 'plan' + ความยาวเส้นตอนวาด) — หน้าที่มีสองแปลนแยกกันเอง
  5. แกนที่ไม่มีวงเลย: ถอยไปวิธีเส้นประเดิม (candidates/aligned/label_lines) เฉพาะเส้นที่มีชื่อ
  ตำแหน่ง pos/lo/hi = pt ตามที่ตามองเห็น (หมุนหน้าแล้ว) -> พิกเซลของภาพที่ render = pt x dpi/72

ผลวัด 2026-11-21 (--eval: หน้าแปลน 2 หน้าแรกของบ้านที่มีเฉลย grid master และ 12 หน้าแรกมีข้อความฝัง, 276 แกน, ~3 นาที CPU):
  - ชุดชื่อหัวกริดตรงเฉลยเป๊ะ 251/276 (91%) [วิธีเส้นประเดิม 54] · เกินเฉลย 0 · ไม่ตรงเลย 0 · บางส่วน 6 · หาไม่เจอ 19
  - บางส่วน 6 แกน = ไม่ใช่บั๊กทั้งหมด (agent ไล่ทีละหน้า): หน้าแสดงกริดไม่ครบชุดของบ้าน (1ชั้น_03 น.11 แปลนขยายห้องน้ำ,
    1ชั้น_61 น.12 แปลนโครงหลังคา, 2ชั้น_28 น.42-43 แผ่นโครงสร้างไม่มีวง C) และเฉลยผิด (2ชั้น_04 น.5-6: C', C'', C''' ในเฉลยเป็น
    'named' แต่เป็นขีดบอกระยะ ไม่มีวงในแบบสักหน้าจาก 94 หน้า — ควรเป็น dummy)
  - หาไม่เจอ 19 = หน้าภาพสแกนล้วน 16 (1ชั้น_07/13/14, 2ชั้น_10 น.20-21) + 2ชั้น_22 น.14 (ภาพ 11 ชิ้น) + 1ชั้น_03 น.11 แกน x
    (ได้เส้น 1 ถูก แต่เฉลยบ้านมี 1,2,3) — หน้าภาพยังไม่รองรับตามขั้นต่ำ "เริ่มจากเวกเตอร์"
  - ตำแหน่งตรงจริง: แต่ละแปลนเทียบ pos(pt) กับ pos_m ของเฉลยด้วยเส้นตรงเส้นเดียว แกนที่มี >= 3 เส้น 282/283 คลาดไม่เกิน 2 ซม.
    (ตัวถัดไป 5 มม.); สเกลแกน x กับ y ของแปลนเดียวกันตรงกันภายใน 2% ใน 153/154 แปลน — ตัวที่ไม่ตรงคือ 2ชั้น_07 น.5 ที่แบบวาด
    วงหัวกริด 3 คลาดจากขีดบอกระยะ ~0.5 ม. เอง (เส้นตามที่วาดถูก)
  - ตรวจภาพแบบหักล้าง (agent 5 คู่ตรวจ+ตรวจซ้ำ บน 37 หน้าที่ไม่อยู่ในชุดวัด 21 พ.ย. ก่อนแก้รอบนี้): ผ่าน 20 เล็กน้อย 3 ผิด 14 หน้า
    ยืนยันข้อผิด 168 (เส้นเกิน 140 = ทางถอยเส้นประบนหน้าไม่มีกริด, เส้นหาย 28) — แก้ครบทุกสาเหตุในรอบนี้ (ดูคอมเมนต์ในโค้ด)
  - ข้อจำกัด: หัวกริดหกเหลี่ยม/สี่เหลี่ยมยังไม่รองรับ; ชื่อไทย (ก ข ค) อ่านได้จากข้อความฝังเท่านั้น (OCR ใช้ตัวอ่านละติน — บ้านที่ใช้
    ชื่อไทยในคลังเป็นสแกนทั้งหมด); หน้า detail/legend ที่มีวงเลขเรียงกัน (ลูกนอนบันได, สัญลักษณ์) ยังหลุดเป็นเส้นได้; ยังไม่ได้วัดบน
    หน้าที่ไม่มีเฉลยเป็นตัวเลข (ดูภาพด้วยตาเท่านั้น)

ผลเดิม 2026-11-19/20 (วิธีเส้นประ — ยังอยู่เป็นทางถอย): ตรง 54/192 แกน; สาเหตุหลักคือชื่อหัวกริดถูกวาดเป็นเส้น (121 แกน หน้านั้นมีคำ
< 40 คำ) และเลือกเส้นผิดกลุ่ม; หา pos_m จากโน้ตมาตราส่วน 1:75 ถูกแค่ 14/126 แกน (มาตราส่วนจริงใน PDF ต่างจากที่พิมพ์ — 1ชั้น_27
35.0 pt/m แต่ 1:75 ควรได้ 37.8) ห้ามเชื่อโน้ตมาตราส่วน — gridlab_scale.py จึงใช้ตัวเลขบอกระยะแทน

    python tools/gridlab_probe.py --page <บ้าน> <เลขหน้า> [--no-ocr]        # พิมพ์เส้น+ชื่อ+แปลนของหน้านั้น
    python tools/gridlab_probe.py --draw <บ้าน> <เลขหน้า> <ไฟล์.png>          # วาดเส้น+ชื่อลงภาพหน้านั้น (ขั้นต่ำของ King)
    python tools/gridlab_probe.py --eval [--dump ผล.json]                     # วัดเทียบ grid master (~3 นาที CPU)
    python tools/gridlab_probe.py --demo                                      # self-check ไม่ต้องมีไฟล์จริง
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


def candidates(page, drawings=None):
    """คืน ({'v': [...], 'h': [...]}, (W, H)) พิกัดตามที่ตามองเห็น (คูณ rotation_matrix แล้ว)"""
    rm, W, H = page.rotation_matrix, page.rect.width, page.rect.height
    runs = {"v": collections.defaultdict(list), "h": collections.defaultdict(list)}
    for d in (page.get_drawings() if drawings is None else drawings):
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


# ---------- วิธีที่ 2 (2026-11-21): เริ่มจากวงหัวกริด ----------
# วิธีเดิม (เส้นประ -> ชื่อ) พลาด 129/132 แกนเพราะตัวอักษรหัวกริดถูกวาดเป็นเส้น ไม่มีข้อความฝัง (121 แกน หน้านั้นมีคำ < 40 คำ)
# และเลือกเส้นผิดกลุ่มได้ง่าย: ที่นี่หาวงกลมก่อน (เส้นโค้ง 'c' ที่ปิดกลับจุดเริ่ม กรอบเกือบจัตุรัส) -> วงขนาดเท่ากันเรียงแถว/คอลัมน์
# -> แต่ละวงต้องมีเส้นตั้งฉากยาวพุ่งออกไป "ทางเดียว" (วงเสาเข็มที่เส้นกริดผ่านกลางจะมีเส้นสองทาง จึงตก)
# ชื่อ: ข้อความฝังที่อยู่ในวงก่อน ไม่มีค่อย OCR ข้างในวง (ตัวอ่านเดียวกับ titleblock_extract)
# clip ของ get_pixmap ใน PyMuPDF 1.28 ใช้พิกัดตามที่ตามองเห็น (ทดสอบบนหน้าหมุน 180 องศา: แปลงกลับแล้วได้ภาพขาว)
BUB_MIN, BUB_MAX = 6.0, 45.0      # pt เส้นผ่านศูนย์กลางวงหัวกริด
ALIGN_TOL = 2.0                   # pt วงในแถวเดียวกัน — หรือ ALIGN_FRAC เท่าของเส้นผ่านศูนย์กลาง ถ้ามากกว่า (_align_tol)
ALIGN_FRAC = 0.3                  # วงเยื้องจากแถวที่เจอจริง: 1ชั้น_49 หน้า 11-12 วง 3 เยื้อง 2.4-3.1 pt (0.22d), 1ชั้น_01 หน้า 19
                                  # วง A เยื้อง 4.0 pt (0.28d); วงต่างแถวที่ใกล้กันที่สุดในชุด --eval ห่าง 0.40d (รีวิว 21 พ.ย.)
TOUCH_MIN = 0.2                   # ก้านที่แตะวงต้องยาว >= 0.2d: ก้านสั้นสุดที่เจอ 5.92 pt ของวง 19.8 pt (0.299d) เคยตกเกณฑ์ 0.3d
                                  # (1ชั้น_04 หน้า 48, 1ชั้น_05 หน้า 50, 2ชั้น_02 หน้า 64 — ผู้ตรวจภาพยืนยัน 21 พ.ย.)
LINE_TOL = 1.0                    # pt เส้นต้องผ่านศูนย์กลางวง
LABEL_RE2 = re.compile(r"^(?:[A-Z]|\d{1,2}|[ก-ฮ])'{0,3}$")
OCR_MIN_SCORE = 0.5
OCR_MASK = 0.45                   # ทาสีขาวนอกรัศมีนี้ (x d) ก่อน OCR: มุมกรอบ 0.39d อยู่ห่างศูนย์กลาง 0.55d เลยขอบวง (0.5d)
                                  # ขอบวงถูกอ่านเป็น '1','7','/' แข่งกับชื่อจริง (56/508 ภาพ) — รีวิว 21 พ.ย.; 0.42d ทำให้ A' เป็น A`


def _align_tol(d):
    return max(ALIGN_TOL, ALIGN_FRAC * d)


def _row_tol(a, b):
    """ระยะเยื้องที่ยอมให้วงสองวงอยู่แถวเดียวกัน: เส้นยาวทั้งคู่ (หลักฐานแข็ง) ได้ 0.5d — แปลนขยายห้องน้ำวาดวง D กับ E
    เยื้องกัน 6.8 pt = 0.34d (1ชั้น_04 หน้า 13, 1ชั้น_05 หน้า 14 — ตรวจรอบสอง 21 พ.ย.); ก้านสั้นคงเกณฑ์เดิม"""
    d = a["bubble"][2]
    return 0.5 * d if a.get("kind") == "long" and b.get("kind") == "long" else _align_tol(d)


def _on_curve(it):
    """จุดที่อยู่บนเส้นจริงของท่อน 'l'/'c' (จุดควบคุม Bezier ยื่นออกนอกวง ใช้ทำกรอบไม่ได้ — 1ชั้น_03 หน้า 6)
    เส้นตรงให้จุดกลางด้วย: สี่เหลี่ยมมุมมน/ตัดมุม (สัญลักษณ์เสา) มีจุดยอดห่างศูนย์กลางเท่ากันแต่กลางขอบไม่เท่า จึงไม่ผ่านเป็นวง"""
    if it[0] == "l":
        return [it[1], (it[1] + it[2]) * 0.5, it[2]]
    p0, p1, p2, p3 = it[1:5]
    return [p0, (p0 + p1 * 3 + p2 * 3 + p3) * 0.125, p3]


def ring_circle(pts):
    """จุดบนเส้นของ path ที่ปิด -> (cx, cy, d) ถ้าเป็นวงกลม (ระยะจากศูนย์กลางเท่ากัน ±10%) ไม่งั้น None (pure)"""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if not (BUB_MIN <= w <= BUB_MAX) or abs(w - h) > 0.15 * w:
        return None
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    rs = [((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in pts]
    r = sum(rs) / len(rs)
    return (cx, cy, (w + h) / 2) if r > 0 and max(abs(q - r) for q in rs) <= 0.1 * r else None


def circles(page, drawings=None):
    """วงกลมจากเวกเตอร์ -> [(cx, cy, d)] พิกัดตามที่ตามองเห็น (ไม่ซ้ำ)
    วง = ท่อน 'l'/'c' ที่ต่อกันจนปิดกลับจุดเริ่ม และมีเส้นโค้งอย่างน้อย 1 ท่อน หรือเส้นตรง >= 8 ท่อน (วงหลายเหลี่ยม)
    เจอทั้งโค้ง 4 ท่อนล้วน (siamplan) และโค้ง 2 ท่อนสลับเส้นตรงสั้น (แบบภาครัฐ 1ชั้น_03)
    ยังไม่รองรับ: วงที่วาดต่อจากก้านใน path เดียวกัน (ปิดกลับที่ท่อนกลาง ไม่ใช่ท่อนแรก) และหัวกริดหกเหลี่ยม"""
    rm, out = page.rotation_matrix, []
    for dr in (page.get_drawings() if drawings is None else drawings):
        fill = dr.get("fill")
        if fill and sum(fill) / len(fill) < 0.5:
            continue     # จุดทึบสีเข้ม ไม่ใช่หัวกริด (กันไว้ก่อน — วงหัวกริดที่เติมสีขาวยังผ่าน)
        run = []
        for it in dr["items"]:
            if it[0] not in ("l", "c"):
                run = []
                continue
            if run and (abs(it[1].x - run[-1][-1].x) > 0.5 or abs(it[1].y - run[-1][-1].y) > 0.5):
                run = []         # ไม่ต่อกับท่อนก่อน -> เริ่มนับใหม่
            run.append(it if it[0] == "c" else (it[0], it[1], it[2]))
            s, e = run[0][1], run[-1][-1]
            if len(run) >= 2 and abs(e.x - s.x) < 0.5 and abs(e.y - s.y) < 0.5:
                if any(x[0] == "c" for x in run) or len(run) >= 8:
                    c = ring_circle([((p * rm).x, (p * rm).y) for x in run for p in _on_curve(x)])
                    if c and not any(abs(c[0] - o[0]) < 0.5 and abs(c[1] - o[1]) < 0.5 for o in out):
                        out.append(c)
                run = []
    return out


def segments(page, drawings=None):
    """เส้นตรงทุกเส้น (เส้นทึบด้วย ไม่ใช่แค่เส้นประ) -> {'v': [(x, y0, y1)], 'h': [(y, x0, x1)]}"""
    rm, segs = page.rotation_matrix, {"v": [], "h": []}
    for d in (page.get_drawings() if drawings is None else drawings):
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1] * rm, it[2] * rm
            if abs(a.x - b.x) < 0.3 and abs(a.y - b.y) > 0.5:
                segs["v"].append(((a.x + b.x) / 2, min(a.y, b.y), max(a.y, b.y)))
            elif abs(a.y - b.y) < 0.3 and abs(a.x - b.x) > 0.5:
                segs["h"].append(((a.y + b.y) / 2, min(a.x, b.x), max(a.x, b.x)))
    return segs


def _reach(start, spans, gap):
    """เดินออกจาก start ไปทาง + ตามท่อน (a0, a1) ที่ต่อกันโดยช่องว่าง <= gap -> ปลายสุดที่ไปถึง"""
    cur = start
    for a0, a1 in sorted(spans):
        if a1 <= start:
            continue
        if a0 > cur + gap:
            break
        cur = max(cur, a1)
    return cur


def _along(ln, ax):
    """พิกัดของวงตามแนวเส้น (เส้นตั้ง = y ของวง, เส้นนอน = x ของวง)"""
    return ln["bubble"][1] if ax == "v" else ln["bubble"][0]


def _rank(ln):
    """ชื่อไหนน่าเชื่อกว่า: มีชื่อ > ข้อความฝัง > คะแนน OCR"""
    return (ln.get("label") is not None, ln.get("src") == "text", ln.get("score", 0.0))


def _merge(lines):
    """วงหัวกริดสองปลายของเส้นเดียวกัน -> เส้นเดียว (ตำแหน่งเดียวกัน ช่วงซ้อนกัน วงขนาดใกล้กัน)"""
    merged = []
    for ln in sorted(lines, key=lambda l: (l["pos"], l["lo"])):
        # ช่วงต้องซ้อนกันจริง: ปลายแค่ชนกัน = เส้นของสองแปลนที่อยู่ระดับเดียวกัน (1ชั้น_03 หน้า 6) ไม่รวม
        # วงต้องขนาดใกล้กัน: โคมไฟดาวน์ไลท์ d 9.5 ที่บังเอิญอยู่บนเส้นกริด 3 (วง d 19.8) เคยเอาชื่อ OCR '2' มาทับ '3'
        # (1ชั้น_06 หน้า 44 — รีวิว 21 พ.ย.); เทียบกับทุกเส้นที่รวมแล้ว ไม่ใช่แค่เส้นสุดท้าย
        m = next((m for m in reversed(merged) if abs(m["pos"] - ln["pos"]) <= LINE_TOL and ln["lo"] < m["hi"] - 1
                  and m["lo"] < ln["hi"] - 1 and abs(m["bubble"][2] - ln["bubble"][2]) <= 0.12 * m["bubble"][2]), None)
        if m:
            m["lo"], m["hi"] = min(m["lo"], ln["lo"]), max(m["hi"], ln["hi"])
            if "vlo" in m and "vlo" in ln:
                m["vlo"], m["vhi"] = min(m["vlo"], ln["vlo"]), max(m["vhi"], ln["vhi"])
            m["kind"] = "long" if "long" in (m["kind"], ln["kind"]) else m["kind"]
            m.setdefault("more", []).extend([ln["bubble"]] + ln.get("more", []))
            if _rank(ln) > _rank(m):
                m["label"], m["src"], m["score"] = ln.get("label"), ln.get("src"), ln.get("score", 0.0)
        else:
            merged.append(ln)
    return merged


def divided(c, segs):
    """วงที่มีเส้นตรงพาดผ่านศูนย์กลาง ยาวเกือบเท่าวง (0.9d..1.2d, ห่างศูนย์กลาง <= 0.1d) = วงอ้างอิงรูปตัด/แผ่น
    (เลขบน / A-05 ล่าง) ไม่ใช่หัวกริด (1ชั้น_03 หน้า 6: ยาว 1.00d)
    เกณฑ์เดิม 0.6d..1.2d ห่างได้ 0.3d ไปโดนขาของตัวอักษรที่วาดเป็นเส้น (1/B/D/E/F ยาว 0.64-0.77d ห่าง 0.04-0.27d) — ทิ้งวงหัวกริด
    จริง 279 วงใน 73 หน้า 21 บ้าน (รีวิว 21 พ.ย.; 2ชั้น_36 หน้า 12 เสีย B,D,E,1); เกณฑ์ใหม่ยังจับวงอ้างอิงได้ 120/156 วง"""
    cx, cy, d = c
    for ax, (p0, q0) in (("h", (cy, cx)), ("v", (cx, cy))):
        for p, a0, a1 in segs[ax]:
            if abs(p - p0) <= 0.1 * d and a0 <= q0 - 0.3 * d and a1 >= q0 + 0.3 * d and 0.9 * d <= a1 - a0 <= 1.2 * d:
                return True
    return False


def bubble_lines(circs, segs, W, H):
    """วง + เส้น -> {'v': [dict(pos, lo, hi, bubble, dir, kind)], 'h': [...]} (pure: ทดสอบได้ใน demo)
    'v' = เส้นตั้ง (แกน x ใน grid master) วงเรียงเป็นแถวนอน; 'h' = เส้นนอน วงเรียงเป็นคอลัมน์
    kind='long' = มีเส้นกริดยาวพุ่งออกจากวง; kind='stem' = มีแค่ก้านสั้น (แบบหลายบ้านไม่วาดเส้นกริดทะลุแปลน —
    1ชั้น_30 หน้า 11, 2ชั้น_37 หน้า 13) -> bubble_labels ต้องอ่านชื่อได้ ไม่งั้นถูกทิ้ง"""
    out = {"v": [], "h": []}
    min_len = 0.08 * max(W, H)
    circs = [c for c in circs if not divided(c, segs)]
    for ax in ("v", "h"):
        across_i, along_i = (0, 1) if ax == "v" else (1, 0)
        for ci, (cx, cy, d) in enumerate(circs):
            c = (cx, cy)
            pos, mid = c[across_i], c[along_i]
            spans = [(a0, a1) for p, a0, a1 in segs[ax] if abs(p - pos) <= LINE_TOL]
            if not spans:
                continue
            if any((abs(a0 - mid) <= 0.35 * d and a1 > mid + d / 2) or (abs(a1 - mid) <= 0.35 * d and a0 < mid - d / 2)
                   for a0, a1 in spans):
                continue     # เส้นเริ่มที่ศูนย์กลางวงแล้วพุ่งออก = วงที่มุมกรอบ/จุดอ้างอิง ไม่ใช่หัวกริด (ก้านหัวกริดเริ่มที่ขอบวง)
                             # — ใหญ่_1ชั้น_02 หน้า 27 วงเล็กสี่มุมกรอบ OCR เป็น '5','H'
            neg = [(-a1, -a0) for a0, a1 in spans]
            ef, eb = mid + d / 2 - 1, -(mid - d / 2 + 1)     # ขอบวงสองฝั่ง (เผื่อ 1 pt ให้ก้านที่เริ่มชิดขอบ)
            gap = max(6 * d, 60.0)   # ก้านวง -> เส้นกริดจริงมีช่องว่างได้ ~70 pt ตรงเส้นบอกระยะ (1ชั้น_29 วง B,C)
            fwd, back = _reach(ef, spans, gap) - ef, _reach(eb, neg, gap) - eb
            tg = 0.25 * d + 1.0          # "แตะวง" = ช่องว่างไม่เกินนี้
            tf, tb = _reach(ef, spans, tg) - ef, _reach(eb, neg, tg) - eb
            t = TOUCH_MIN * d
            if tf >= t and tb <= 0.5 * d and tf - tb >= t:
                s = 1                    # ก้าน/เส้นแตะวงฝั่งเดียว — ตัดสินทิศจากเส้นที่แตะ ไม่ใช่เส้นไกล
            elif tb >= t and tf <= 0.5 * d and tb - tf >= t:
                s = -1                   # (เส้นกริดของแปลนข้างๆ ที่ลากมาจ่อวงห่าง ~30 pt ไม่ถือว่าทะลุ — 1ชั้น_03 หน้า 6)
                                         # ต้องไม่สมมาตร: กากบาทของโคมไฟ (ยื่นสองฝั่งเท่ากัน) เคยผ่านเป็นก้าน (ใหญ่_2ชั้น_01 หน้า 64)
            elif tf < t and tb < t and max(fwd, back) >= max(4 * d, min_len) and min(fwd, back) <= 2 * d:
                s = 1 if fwd >= back else -1   # ไม่มีอะไรแตะวง แต่มีเส้นยาวเริ่มห่างจากวงเล็กน้อย
                e = ef if s > 0 else eb
                if min(a0 for a0, a1 in (spans if s > 0 else neg) if a1 > e) - e > 0.5 * d:
                    continue     # เส้นยาวที่เริ่มห่างวงเกินครึ่งวง = ขีดตัวอักษร/ลูกศรของป้ายพื้นที่ต่อกันเป็นสาย ไม่ใช่เส้นกริด
                                 # (หัวกริดจริงที่ผ่านทางนี้ ท่อนแรกห่างขอบ ~1 pt; ของปลอมห่าง 15-65 pt — รีวิว 21 พ.ย.)
            else:
                continue         # ไม่มีเส้น หรือเส้นแตะวงทั้งสองฝั่ง (วงเสาเข็ม/ป้ายพื้น PS ที่มีลูกศรสองข้าง ไม่ใช่หัวกริด)
            length = fwd if s > 0 else back
            kind = "long" if length >= max(4 * d, min_len) else "stem"
            lo, hi = (mid - d / 2, mid + d / 2 + length) if s > 0 else (mid - d / 2 - length, mid + d / 2)
            for cj, c2 in enumerate(circs):   # หยุดที่วงอื่นบนเส้นเดียวกัน (วงปลายอีกด้าน หรือวงของแปลนข้างๆ — 2ชั้น_37 หน้า 13)
                if cj != ci and abs(c2[across_i] - pos) <= LINE_TOL and lo < c2[along_i] < hi and abs(c2[along_i] - mid) > d:
                    if s > 0:
                        hi = min(hi, c2[along_i] - c2[2] / 2)
                    else:
                        lo = max(lo, c2[along_i] + c2[2] / 2)
            out[ax].append(dict(pos=round(pos, 1), lo=round(lo), hi=round(hi), vlo=round(lo), vhi=round(hi),
                                bubble=(cx, cy, d), dir=s, kind=kind))
    raw = {}
    for ax in out:   # แถว/คอลัมน์ของวงต้องมีอย่างน้อย 2 วงขนาดเท่ากัน ก้านชี้ทางเดียวกัน (วงเดี่ยว = ป้ายอื่น)
        keep = [ln for ln in out[ax] if any(_mate(m, ln) and abs(_along(m, ax) - _along(ln, ax)) <= _row_tol(ln, m)
                                            for m in out[ax])]
        # วงเยื้อง: เส้นชิดเส้นของแถวไม่ถึง 2 วง วงจึงถูกยกพ้นแถว (1' ห่าง 1 = 0.20 ม. = 0.5 วง — 1ชั้น_52 หน้า 11, 12;
        # 2' ห่าง 3 = 1.31 วง ยกขึ้น 1.56 วง — 1ชั้น_36 หน้า 15; C' ห่าง D 1.31 วง — 1ชั้น_67 หน้า 14, ตรวจรอบสอง 21 พ.ย.)
        for ln in out[ax]:
            if all(ln is not k for k in keep) and any(
                    _mate(m, ln) and abs(m["pos"] - ln["pos"]) < 2 * ln["bubble"][2]
                    and abs(_along(m, ax) - _along(ln, ax)) <= 3 * ln["bubble"][2] for m in keep):
                ln["lone"] = True
                keep.append(ln)
        # วงที่ไม่มีก้านเลย แต่อยู่ในแถวที่ยืนยันแล้ว >= 2 วงขนาดเท่ากัน (วง 6 ของ 1ชั้น_38 หน้า 14: เส้นบอกระยะเริ่มห่างวง 21 pt)
        # รับเป็นก้าน — ต้องอ่านชื่อได้ถึงจะรอด (confirmed); วงที่มีเส้นแตะ/ทะลุอยู่แล้วถูกตัดสินไปแล้ว ไม่กู้
        across_i, along_i = (0, 1) if ax == "v" else (1, 0)
        used = [ln["bubble"] for ln in out[ax]]
        for c in circs:
            if c in used:
                continue
            pos, mid, d = c[across_i], c[along_i], c[2]
            if any(abs(p - pos) <= LINE_TOL and a0 < mid + d / 2 + 1 and a1 > mid - d / 2 - 1 for p, a0, a1 in segs[ax]):
                continue
            row = [k for k in keep if abs(k["bubble"][2] - d) <= 0.12 * d and abs(_along(k, ax) - mid) <= _align_tol(d)]
            if len(row) >= 2 and not any(abs(k["pos"] - pos) <= d for k in keep):
                s = 1 if sum(k["dir"] for k in row) >= 0 else -1
                keep.append(dict(pos=round(pos, 1), lo=round(mid - d / 2), hi=round(mid + d / 2), vlo=round(mid - d / 2),
                                 vhi=round(mid + d / 2), bubble=c, dir=s, kind="stem", stemless=True))
        raw[ax], out[ax] = out[ax], _merge(keep)
    for ax, other in (("v", "h"), ("h", "v")):
        # แกนที่ไม่มีแถววงเลย (แปลนขยายแสดงกริดแกนนั้นเส้นเดียว — 1ชั้น_03 หน้า 11 แปลนห้องน้ำ วง 1 เดี่ยว): รับวงเดี่ยวที่อยู่
        # นอกกริดของอีกแกน (เส้นอีกแกนที่ผ่านตำแหน่งนี้อยู่ฝั่งที่ก้านชี้ไปทั้งหมด) และเส้นยาวตัดเส้นที่วงขนาดเท่ากันได้ >= 2 เส้น
        # ป้ายพื้นที่อยู่ในแปลน (ใหญ่_1ชั้น_03 หน้า 28) ไม่ผ่าน
        if out[ax]:
            continue
        lone = []
        for ln in raw[ax]:
            ms = [m for m in out[other] if m["lo"] <= ln["pos"] <= m["hi"]]
            if ln["kind"] == "long" and all(ln["dir"] * (m["pos"] - _along(ln, ax)) > 0 for m in ms) and sum(
                    ln["lo"] <= m["pos"] <= ln["hi"] and abs(m["bubble"][2] - ln["bubble"][2]) <= 0.12 * ln["bubble"][2]
                    for m in ms) >= 2:
                ln["lone"] = True
                lone.append(ln)
        out[ax] = _merge(lone)
    return out


def _mate(m, ln):
    """วงอีกวงขนาดเท่ากัน (±12%) ก้านชี้ทางเดียวกัน"""
    return m is not ln and m["dir"] == ln["dir"] and abs(m["bubble"][2] - ln["bubble"][2]) <= 0.12 * ln["bubble"][2]


def _rows(lines_ax, ax):
    """จัดเส้นของแกนเดียวกันเป็นแถววง: วงอยู่แนวเดียวกัน (ALIGN_TOL หรือ ALIGN_FRAC*d) และก้านชี้ทางเดียวกัน"""
    gs = []
    for ln in sorted(lines_ax, key=lambda l: _along(l, ax)):
        g = next((g for g in gs if abs(_along(g[0], ax) - _along(ln, ax)) <= _row_tol(g[0], ln)
                  and g[0]["dir"] == ln["dir"]), None)
        (g.append(ln) if g else gs.append([ln]))
    return gs


def consistent_labels(lines):
    """ชื่อหัวกริดในแกนเดียวกันของหน้าเป็นชนิดเดียวกัน (ตัวอักษร หรือ ตัวเลข): ทิ้งแถววงที่ชื่อส่วนใหญ่เป็นอีกชนิด
    — ป้ายพื้น SP/S1 ที่มีลูกศรข้างเดียวอยู่ในแปลน OCR เป็น '7','1' ในแกนที่เป็น A-E (ใหญ่_1ชั้น_03 หน้า 28)
    แถวที่ไม่มีชื่อเลยไม่แตะ (ไม่เดาทิ้ง)"""
    kind = lambda t: "digit" if t[0].isdigit() else "alpha"
    for ax in lines:
        votes = collections.Counter(kind(l["label"]) for l in lines[ax] if l["label"])
        top = votes.most_common()
        if not top or (len(top) > 1 and top[0][1] == top[1][1]):
            continue     # เสมอกัน = ไม่ทิ้งอะไร (เดิมเลือกตามลำดับเส้น — 2ชั้น_03 หน้า 20 รูปตัดสองทิศ 1,2 กับ A,B เคยเสีย A,B)
        major = top[0][0]
        keep = []
        for g in _rows(lines[ax], ax):
            gv = collections.Counter(kind(l["label"]) for l in g if l["label"])
            if not gv or gv[major] >= sum(gv.values()) - gv[major]:
                keep.extend(g)
        lines[ax] = keep
    return lines


def _reaches(g, s, targets, d):
    """เส้นจริง (vlo/vhi ก่อนยืด) ของแถว g ที่ก้านชี้ทาง s ลากถึงตำแหน่ง targets ใกล้สุดภายใน 3 วงไหม"""
    if s > 0:
        return max(l.get("vhi", l["hi"]) for l in g) >= min(targets) - 3 * d
    return min(l.get("vlo", l["lo"]) for l in g) <= max(targets) + 3 * d


def extend_to_plan(lines):
    """ความยาวเส้นตอนวาด: จับคู่แต่ละแถววง (แกนหนึ่ง) กับกลุ่มวงของอีกแกนที่อยู่ฝั่งที่ก้านชี้ไปและใกล้สุด
    แล้วให้เส้นเริ่มที่วงและจบที่เส้นสุดท้ายของกลุ่มนั้น +1 วง (แทนระยะที่ลากตามเวกเตอร์ ซึ่งทะลุไปแปลนข้างๆ/กรอบชื่อแบบได้)
    จับคู่ไม่ได้ = คงระยะเดิม; ไม่แตะตำแหน่งเส้น (pos); หน้าที่มีสองแปลนจับคู่แยกกันเอง"""
    raw = {ax: _rows(lines[ax], ax) for ax in ("v", "h")}
    groups = {}
    for ax, other in (("v", "h"), ("h", "v")):
        # แถววงของสองแปลนที่อยู่ระดับเดียวกันต้องแยก: ตัดแถวตรงที่มีคอลัมน์วงของอีกแกนคั่นกลาง และช่องนั้นกว้างกว่า
        # 1.5 เท่าของระยะปกติในแถว (2ชั้น_37 หน้า 13: ช่องคั่นแปลน 275 pt vs ปกติ 113) — ไม่งั้นแถววงของแปลนอื่นที่
        # บังเอิญอยู่ระหว่างเส้น D-E จะตัดคอลัมน์ขาด (1ชั้น_27 หน้า 10: ช่อง 52 pt = ระยะปกติ)
        # ตัวแบ่งแปลนใช้เฉพาะแถววงที่มีชื่อ: แถวป้ายพื้น S1/S2 เคยตัดคอลัมน์จริงขาด (2ชั้น_02 หน้า 33 — รีวิว 21 พ.ย.)
        seps = [_along(g[0], other) for g in raw[other] if any(l.get("label") for l in g)]
        groups[ax] = []
        for g in raw[ax]:
            g = sorted(g, key=lambda l: l["pos"])
            gaps = sorted(b["pos"] - a["pos"] for a, b in zip(g, g[1:]))
            med = gaps[len(gaps) // 2] if gaps else 0
            cur = [g[0]]
            for a, b in zip(g, g[1:]):
                # ชื่อซ้ำในแถว = แปลนที่สอง (ชื่อกริดในแกนเดียวกันของแปลนเดียวไม่ซ้ำ): แปลนไฟฟ้า/เต้ารับคู่กัน แปลนขวาไม่มีคอลัมน์วง
                # ของตัวเอง แถวบน 1,2,3,1,2,3 เลยไม่ถูกตัด แล้วเมตรของแปลนขวาเพี้ยน (1ชั้น_06 หน้า 44 — ตรวจรอบสอง 21 พ.ย.)
                rep = b.get("label") and b["label"] in {x.get("label") for x in cur}
                if rep or (b["pos"] - a["pos"] > 1.5 * med and any(a["pos"] < s < b["pos"] for s in seps)):
                    groups[ax].append(cur)
                    cur = []
                cur.append(b)
            groups[ax].append(cur)
    parent = {}      # union-find: แถววงที่จับคู่กันได้ = แปลนเดียวกัน -> ln["plan"]

    def root(k):
        while parent.setdefault(k, k) != k:
            k = parent[k]
        return k
    # ชื่อในแต่ละแปลน: {root: {(แกน, ชื่อ): [ตำแหน่ง]}} — ห้ามรวมสองกลุ่มเป็นแปลนเดียวถ้าชื่อเดียวกันจะไปอยู่คนละตำแหน่ง
    # (แปลนขวาไม่มีคอลัมน์วงของตัวเองจึงจับคอลัมน์ของแปลนซ้าย — 1ชั้น_06 หน้า 44); ชื่อเดียวกันตำแหน่งเดียวกัน = เส้นเดียว
    # ที่มีวงสองปลาย รวมได้
    names = {}
    for ax in groups:
        for gi, g in enumerate(groups[ax]):
            nm = names.setdefault(root((ax, gi)), collections.defaultdict(list))
            for ln in g:
                if ln.get("label"):
                    nm[(ax, ln["label"])].append(ln["pos"])

    def clash(r1, r2):
        a, b = names.get(r1, {}), names.get(r2, {})
        return r1 != r2 and any(abs(x - y) > 2 * LINE_TOL for k in a if k in b for x in a[k] for y in b[k])
    for ax, other in (("v", "h"), ("h", "v")):
        for gi, g in enumerate(groups[ax]):
            at, s, dg = _along(g[0], ax), g[0]["dir"], g[0]["bubble"][2]
            span = (min(l["pos"] for l in g), max(l["pos"] for l in g))
            labelled = any(l.get("label") for l in g)
            longrow = 2 * sum(l["kind"] == "long" for l in g) > len(g)
            best = None
            for pj, p in enumerate(groups[other]):
                ps = [l["pos"] for l in p]
                pa = _along(p[0], other)
                if not all(s * (x - at) > 0 for x in ps) or not all(p[0]["dir"] * (x - pa) > 0 for x in span):
                    continue     # ต้องชี้เข้าหากันทั้งสองทาง: ไม่งั้นแปลนซ้ายจับคอลัมน์วงของแปลนขวาที่อยู่ใกล้กว่า (2ชั้น_37 หน้า 13)
                if labelled and not any(l.get("label") for l in p):
                    continue     # แถวไม่มีชื่อ (ป้ายพื้น) ห้ามชนะคู่ของแถวที่มีชื่อ (ใหญ่_1ชั้น_02 หน้า 28 เคยทำเส้น 1-3 ขาดก่อนถึง A)
                if longrow and not _reaches(g, s, ps, dg) and _reaches(p, p[0]["dir"], span, p[0]["bubble"][2]):
                    continue     # อีกแกนลากเส้นถึงแถวนี้ แต่แถวนี้ลากไม่ถึงอีกแกน = รูปด้าน/รูปตัดในแผ่นเดียวกับแปลน (2ชั้น_02 หน้า 25
                                 # เคยถูกจับเป็นแปลนเดียวกันจนชื่อซ้ำในแปลน — รีวิว 21 พ.ย.); ถ้าไม่ถึงกันทั้งคู่ = แปลนที่วาดแค่หัวกริด
                                 # กับเส้นบอกระยะ จับคู่ได้ (2ชั้น_09 หน้า 25 เคยแยกเป็นสองแปลน — ตรวจรอบสอง 21 พ.ย.)
                if clash(root((ax, gi)), root((other, pj))):
                    continue
                score = max(span[0] - pa, pa - span[1], 0) + min(abs(x - at) for x in ps)
                if best is None or score < best[0]:
                    best = (score, ps, pj)
            if best:
                r1, r2 = root((ax, gi)), root((other, best[2]))
                if r1 != r2:
                    parent[r1] = r2
                    for k, v in names.pop(r1, {}).items():
                        names.setdefault(r2, collections.defaultdict(list))[k].extend(v)
                for ln in g:
                    bc, d = _along(ln, ax), ln["bubble"][2]
                    if s > 0:
                        ln["lo"], ln["hi"] = round(bc - d / 2), round(max(best[1]) + d)
                    else:
                        ln["lo"], ln["hi"] = round(min(best[1]) - d), round(bc + d / 2)
                    for b in ln.get("more", []):     # วงอีกปลายของเส้นเดียวกัน: ยืดให้ถึง
                        ba = b[1] if ax == "v" else b[0]
                        ln["lo"], ln["hi"] = min(ln["lo"], round(ba - b[2] / 2)), max(ln["hi"], round(ba + b[2] / 2))
    ids = {}
    for ax in groups:
        for gi, g in enumerate(groups[ax]):
            pid = ids.setdefault(root((ax, gi)), len(ids))
            for ln in g:
                ln["plan"] = pid
    for ax in lines:
        lines[ax] = _merge(lines[ax])
    return lines


def norm_ocr_label(t):
    """'1)' -> '1', ' a ' -> 'A'; ไม่ใช่ชื่อหัวกริด -> None"""
    t = re.sub(r"[\s()\[\]{}|.,:;_\-]+", "", t).upper().replace("’", "'").replace("`", "'")
    return t if LABEL_RE2.match(t) else None


def bubble_labels(page, lines, ocr=True):
    """ใส่ label/src ให้แต่ละเส้น: ข้อความฝังที่อยู่ในวง > OCR ข้างในวง (batch ทีเดียวต่อหน้า)"""
    import fitz
    rm = page.rotation_matrix
    words = []
    for w in page.get_text("words"):
        t = w[4].strip()
        if LABEL_RE2.match(t.upper()):
            r = fitz.Rect(w[:4]) * rm
            words.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, t.upper()))
    todo = []
    for ax in lines:
        for ln in lines[ax]:
            ln["label"], ln["src"], ln["score"] = None, None, 0.0
            for cx, cy, d in [ln["bubble"]] + ln.get("more", []):
                hit = [t for x, y, t in words if (x - cx) ** 2 + (y - cy) ** 2 <= (d / 2) ** 2]
                if hit:
                    ln["label"], ln["src"], ln["score"] = hit[0], "text", 1.0
                    break
            if ln["label"] is None and ocr:
                todo.append(ln)
    if not todo:
        return lines
    import numpy as np
    sys.path.insert(0, str(Path(__file__).parent))
    import titleblock_extract as T
    imgs, owners = [], []
    for ln in todo:
        for cx, cy, d in [ln["bubble"]] + ln.get("more", []):
            hw = 0.39 * d    # ข้างในวง (ขอบวงทำให้ตัวตรวจจับมองไม่เห็นตัวเลข — วัดบน 1ชั้น_27)
            dpi = max(72, int(96 / (2 * hw / 72)))
            pix = page.get_pixmap(dpi=dpi, clip=fitz.Rect(cx - hw, cy - hw, cx + hw, cy + hw))
            a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            a = (a[:, :, :3] if pix.n >= 3 else np.repeat(a, 3, axis=2)).copy()
            yy, xx = np.ogrid[:a.shape[0], :a.shape[1]]   # มุมกรอบยื่นเลยขอบวง: ทาขาวนอก OCR_MASK*d (ดูค่าคงที่)
            a[(yy - a.shape[0] / 2) ** 2 + (xx - a.shape[1] / 2) ** 2 > (OCR_MASK * d * dpi / 72) ** 2] = 255
            imgs.append(np.ascontiguousarray(np.pad(a, ((40, 40), (40, 40), (0, 0)), constant_values=255)))
            owners.append(ln)
    for ln, r in zip(owners, T._reader().predict(imgs)):
        for txt, sc in zip(r.get("rec_texts", []), r.get("rec_scores", [])):
            lab = norm_ocr_label(txt)
            if lab and float(sc) >= OCR_MIN_SCORE and (ln["src"] != "ocr" or float(sc) > ln["score"]):
                ln["label"], ln["src"], ln["score"] = lab, "ocr", float(sc)
    return lines


def confirmed(lines):
    """หลังอ่านชื่อ: แถววงที่ไม่มีชื่อเลยสักวงทิ้งทั้งแถว (เส้นไม่มีชื่อ 6 เส้นในชุด --eval เป็นป้ายพื้นทั้งหมด — รีวิว 21 พ.ย.);
    ในแถวที่มีชื่อ วงที่มีแค่ก้านต้องมีชื่อ (เส้นยาวไม่มีชื่อเก็บไว้เป็น '?'); แล้วตรวจคู่แถวซ้ำ — วงที่รอดเพราะคู่ที่เพิ่งถูกทิ้ง
    ต้องหลุดด้วย (เว้นวงเดี่ยวที่กฎวงเยื้อง/แกนว่างรับไว้เอง)"""
    for ax in lines:
        keep = []
        for g in _rows(lines[ax], ax):
            if any(l["label"] for l in g):
                keep += [l for l in g if l["kind"] == "long" or l["label"]]
        lines[ax] = [l for l in keep if l.get("lone") or any(
            _mate(m, l) and abs(_along(m, ax) - _along(l, ax)) <= _row_tol(l, m) for m in keep)]
    return lines


def detect(page, ocr=True):
    """เส้นกริดของหน้า -> {'v': [dict(pos, lo, hi, label, src, method, kind, plan)], 'h': [...]}
    วิธีวงหัวกริดก่อน; แกนไหนหาวงไม่เจอ ถอยไปวิธีเส้นประเดิม (method='dash') เฉพาะเส้นที่มีชื่อ — เส้นประไม่มีชื่อ
    ไม่เคยถูกในชุด --eval และบนหน้าไม่มีกริดมันหยิบขีดตราประทับ/ลายเซ็นในกรอบชื่อแบบ แนวเขตที่ดิน แนวหลังคามาเป็น
    'เส้นกริด' (ผู้ตรวจภาพยืนยัน 140 เส้นเกินใน 7 หน้า เช่น ใหญ่_2ชั้น_01 หน้า 105 ได้ 107 เส้น — 21 พ.ย.)"""
    W, H = page.rect.width, page.rect.height
    drawings = page.get_drawings()     # อ่านครั้งเดียวต่อหน้า (หน้า A1 44k paths ~1-2 วิ ต่อครั้ง)
    lines = bubble_labels(page, bubble_lines(circles(page, drawings), segments(page, drawings), W, H), ocr=ocr)
    lines = extend_to_plan(consistent_labels(confirmed(lines)))
    for ax in lines:
        for ln in lines[ax]:
            ln["method"] = "bubble"
    c = None
    for ax in ("v", "h"):
        if lines[ax]:
            continue
        if c is None:
            c, _ = candidates(page, drawings)
        al = sorted(aligned(c[ax]))
        lines[ax] = [dict(pos=p, lo=lo, hi=hi, label=lab, src="text", method="dash")
                     for (p, _, lo, hi), (_, lab) in zip(al, label_lines(page, al, ax)) if lab]
    return lines


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


def show_page(house, pn, ocr=True):
    import fitz
    page = fitz.open(pdf_of(house))[pn - 1]
    print(f"{house} หน้า {pn} ขนาด {page.rect.width:.0f}x{page.rect.height:.0f} pt")
    lines = detect(page, ocr=ocr)
    for ax, name in (("v", "เส้นตั้ง (x)"), ("h", "เส้นนอน (y)")):
        print(f"{name}: {len(lines[ax])} เส้น")
        for ln in lines[ax]:
            print(f"   {ln['pos']:8.1f} pt  {ln['lo']}..{ln['hi']}  ชื่อ={ln['label']} ({ln['src']}, {ln['method']}, แปลน {ln.get('plan')})")


def harmonize(lines):
    """เส้นกริดแถวเดียวกันควรยาวเท่ากัน: เส้นที่ปลายสุดเกิน/ขาดจากค่ากลางของกลุ่มมาก (ท่อนของเส้นอื่นที่อยู่ตำแหน่งเดียวกัน
    เช่นในกรอบชื่อแบบ) ถูกดึงกลับมาที่ค่ากลาง — ใช้ตอนวาดเท่านั้น ไม่แก้ผลที่ตรวจวัด"""
    if len(lines) < 3:
        return lines
    his = sorted(l[3] for l in lines)
    med = his[len(his) // 2]
    return [(pos, n, lo, hi if abs(hi - med) <= 0.1 * med else med) for pos, n, lo, hi in lines]


def draw_page(house, pn, out, dpi=110, ocr=True, page=None, lines=None):
    """วาดเส้นกริดที่จับได้ลงบนภาพหน้านั้นแล้วบันทึกเป็น PNG — ขั้นต่ำของ King: 'วาดเส้นกริดบนแบบให้ตรงตำแหน่งจริง'
    เส้นตั้ง (แกน x) สีแดง เส้นนอน (แกน y) สีน้ำเงิน ป้ายชื่อหัวกริดที่ผูกได้ (ไม่ได้ = '?') วงหัวกริดที่ใช้ = วงสีเขียว
    พิกัดเส้นเป็นพิกัดตามที่ตามองเห็น จึงตรงกับพิกเซลของภาพที่ render ด้วยสเกล dpi/72 โดยตรง
    lines = ผลของ detect() ที่มีอยู่แล้ว (ไม่ต้อง OCR ซ้ำ); คืน (จำนวนเส้นตั้ง, จำนวนเส้นนอน, ผูกชื่อได้กี่เส้น)"""
    import fitz
    from PIL import Image, ImageDraw, ImageFont
    if page is None:
        page = fitz.open(pdf_of(house))[pn - 1]
    if lines is None:
        lines = detect(page, ocr=ocr)
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGB")
    d, k = ImageDraw.Draw(img), dpi / 72.0
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    n, named = {"v": 0, "h": 0}, 0
    for ax, color in (("v", (220, 30, 30)), ("h", (30, 60, 220))):
        dash = [ln for ln in lines[ax] if ln["method"] == "dash"]   # เส้นจากวิธีเดิม: ดึงปลายที่เกินกลับ (เฉพาะตอนวาด)
        fix = {ln["pos"]: h for ln, (_, _, _, h) in zip(dash, harmonize([(l["pos"], 0, l["lo"], l["hi"]) for l in dash]))}
        for ln in lines[ax]:
            pos, lo, hi = ln["pos"], ln["lo"], fix.get(ln["pos"], ln["hi"]) if ln["method"] == "dash" else ln["hi"]
            a, b = ((pos * k, lo * k), (pos * k, hi * k)) if ax == "v" else ((lo * k, pos * k), (hi * k, pos * k))
            d.line([a, b], fill=color, width=3)
            for cx, cy, dd in [ln["bubble"]] + ln.get("more", []) if "bubble" in ln else []:
                r = dd / 2 * k
                d.ellipse([cx * k - r, cy * k - r, cx * k + r, cy * k + r], outline=(20, 160, 60), width=3)
            tx, ty = (a[0] + 6, a[1] + 4) if ax == "v" else (a[0] + 4, a[1] - 26)
            d.text((tx, ty), ln["label"] or "?", fill=color, font=font)
            n[ax] += 1
            named += ln["label"] is not None
    img.save(out)
    return n["v"], n["h"], named


def evaluate(ocr=True, dump=None):
    """ชุดหน้าเดิม (หน้าแปลน 2 หน้าแรกของแต่ละบ้านที่มีเฉลย grid master และ 12 หน้าแรกมีข้อความฝัง)
    ตัวหารคงที่ = ทุกแกนที่เฉลยมี >= 2 เส้น named (หาเส้นไม่เจอ = 'no_lines' ไม่ถูกตัดทิ้ง)"""
    import fitz
    res, bad, how, rec = collections.Counter(), [], collections.Counter(), []
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
            lines = detect(doc[pn - 1], ocr=ocr)
            rec.append(dict(house=h, page=pn, lines={ax: [{k: v for k, v in ln.items() if k in
                                                               ("pos", "lo", "hi", "label", "src", "method", "kind", "plan")}
                                                              for ln in lines[ax]] for ax in lines}))
            for ax, gt in (("v", ids[0]), ("h", ids[1])):
                if len(gt) < 2:
                    continue
                res["axes"] += 1
                if not lines[ax]:      # เส้นเดียวยังตัดสินด้วยชื่อ (แปลนขยายพิมพ์กริดแกนนั้นเส้นเดียวได้ — 1ชั้น_03 หน้า 11)
                    res["no_lines"] += 1
                    bad.append(("no_lines", h, pn, ax, [], sorted(gt)))
                    continue
                for ln in lines[ax]:
                    how[(ln["method"], ln["src"])] += 1
                found = {ln["label"] for ln in lines[ax] if ln["label"]}
                k = ("exact_label_set" if found == gt else "superset" if gt <= found else
                     "partial" if found & gt else "none_match")
                res[k] += 1
                if k != "exact_label_set":
                    bad.append((k, h, pn, ax, sorted(found), sorted(gt)))
    print(dict(res))
    print("เส้นตามวิธี/ที่มาของชื่อ:", dict(how))
    for b in sorted(bad):
        print("  ", *b)
    if dump:
        Path(dump).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print("เขียนผลรายหน้าไว้ที่", dump)


def demo():
    c = [(100.0, 30, 91, 751), (200.0, 30, 91, 751), (300.0, 28, 91, 751), (400.0, 12, 300, 700)]
    assert [x[0] for x in aligned(c)] == [100.0, 200.0, 300.0]       # เส้นที่ปลายเริ่มต่างออกไปถูกคัดทิ้ง
    assert aligned([]) == []
    assert LABEL_RE.match("A") and LABEL_RE.match("12") and not LABEL_RE.match("A-1") and not LABEL_RE.match("123")

    # วงกลมจากจุดบนเส้น: 8 จุดบนวงรัศมี 7 -> d=14; สี่เหลี่ยม (มุมห่างกว่าขอบ) ไม่ใช่วง
    import math
    ring = [(50 + 7 * math.cos(t * math.pi / 4), 60 + 7 * math.sin(t * math.pi / 4)) for t in range(8)]
    cx, cy, d = ring_circle(ring)
    assert abs(cx - 50) < 0.01 and abs(cy - 60) < 0.01 and abs(d - 14) < 0.01
    assert ring_circle([(0, 0), (14, 0), (14, 14), (0, 14), (7, 0), (14, 7), (7, 14), (0, 7)]) is None

    # หัวกริดจริง 3 วง (แถว y=50 ก้านยาวลงล่าง) + สิ่งที่ต้องไม่ถูกนับ
    circs = [(100, 50, 14), (200, 50, 14), (300, 50, 14),
             (500, 300, 14), (550, 300, 14),   # วงเสาเข็มคู่ (แถวเดียวกัน): เส้นกริดทะลุทั้งสองฝั่ง
             (600, 50, 14),      # วงอ้างอิงรูปตัด: มีเส้นแบ่งกลางวง (แม้มีก้านยาว และอยู่แถวเดียวกัน)
             (700, 50, 14),      # จุดมุมกรอบ: เส้นเริ่มที่ศูนย์กลางวง
             (800, 400, 14)]     # วงเดี่ยว ไม่มีวงคู่ในแถว
    segs = {"v": [(100, 57, 600), (200, 57, 600), (300, 57, 600), (500, 100, 700), (550, 100, 700), (600, 57, 600),
                  (700, 50, 600), (800, 407, 700)],
            "h": [(50, 593, 607)]}
    got = bubble_lines(circs, segs, 1000, 800)
    assert [ln["pos"] for ln in got["v"]] == [100, 200, 300], got["v"]
    assert all(ln["kind"] == "long" and ln["dir"] == 1 for ln in got["v"]) and got["h"] == []
    # วงเยื้องจากแถว 3 pt (0.21d) ยังเป็นแถวเดียวกัน (1ชั้น_49 หน้า 11: วง 3 ต่ำกว่า 1,2 อยู่ 2.4-3.1 pt)
    got = bubble_lines([(100, 50, 14), (200, 53, 14), (300, 50, 14)],      # ก้านสั้น -> ใช้เกณฑ์ _align_tol (0.3d)
                       {"v": [(100, 57, 70), (200, 60, 73), (300, 57, 70)], "h": []}, 1000, 800)
    assert [(ln["pos"], ln["kind"]) for ln in got["v"]] == [(100, "stem"), (200, "stem"), (300, "stem")], got["v"]
    # ขาตัว B/1 ที่วาดเป็นเส้น (0.76d เยื้องกลาง 0.2d) ไม่ใช่เส้นแบ่งวง (2ชั้น_36 หน้า 12)
    assert not divided((100, 50, 14), {"v": [(97.2, 44.7, 55.3)], "h": []})
    # กากบาทโคมไฟ (ยื่นสองฝั่งเท่ากัน) ไม่ใช่ก้าน; เส้นยาวที่เริ่มห่างวง 16 pt (> 0.5d) ไม่ใช่ เริ่มห่าง 6 pt ยังเป็น
    # (วงที่เส้นเริ่มไกลอยู่คนละแถวกับวงจริง — ถ้าอยู่แถวเดียวกับหัวกริดที่ยืนยันแล้ว กฎ "วงไม่มีก้านในแถว" จะรับไว้ ตั้งใจ)
    got = bubble_lines([(150, 500, 10), (250, 500, 10), (100, 450, 14), (200, 450, 14), (300, 400, 14), (400, 400, 14)],
                       {"v": [(150, 492, 508), (250, 492, 508), (100, 472, 750), (200, 472, 750),
                              (300, 412, 750), (400, 412, 750)], "h": []}, 1000, 800)
    assert [ln["pos"] for ln in got["v"]] == [300, 400], got["v"]
    # วงเยื้อง (เส้น 108 ห่างเส้น 100 ไม่ถึง 1 วง วงยกขึ้นไป y=22) ถูกเก็บ; วงเดี่ยวที่เยื้องแต่ไกลจากทุกเส้นของแถวยังถูกทิ้ง
    got = bubble_lines(circs[:3] + [(108, 22, 14), (400, 30, 14)],
                       dict(segs, v=segs["v"][:3] + [(108, 29, 37), (400, 37, 45)]), 1000, 800)
    assert [ln["pos"] for ln in got["v"]] == [100, 108, 200, 300], got["v"]
    # แกนที่ไม่มีแถววง: วงเดี่ยวนอกกริดที่เส้นยาวตัดเส้นอีกแกน >= 2 เส้น = หัวกริด; วงเดี่ยวที่อยู่ระหว่างเส้นอีกแกน (ป้ายพื้น) ไม่ใช่
    got = bubble_lines([(50, 150, 14), (50, 250, 14), (300, 60, 14), (400, 200, 14)],
                       {"h": [(150, 57, 600), (250, 57, 600)], "v": [(300, 67, 400), (400, 40, 193)]}, 1000, 800)
    assert [ln["pos"] for ln in got["v"]] == [300] and [ln["pos"] for ln in got["h"]] == [150, 250], got
    # รวมเส้นซ้ำ: ชื่อที่น่าเชื่อกว่าชนะ (ไม่ใช่เส้นที่เรียงก่อน); วงคนละขนาด (โคมไฟบนเส้นกริด) ไม่รวม
    a = dict(pos=100, lo=0, hi=200, bubble=(100, 0, 20), kind="long", label="2", src="ocr", score=0.77)
    b = dict(pos=100.2, lo=50, hi=250, bubble=(100, 250, 20), kind="long", label="3", src="ocr", score=0.86)
    c2 = dict(pos=100.1, lo=60, hi=240, bubble=(100, 150, 9.5), kind="stem", label="2", src="ocr", score=0.9)
    m = _merge([a, b, c2])
    assert len(m) == 2 and {x["label"] for x in m} == {"3", "2"} and [x for x in m if x["bubble"][2] == 20][0]["label"] == "3", m

    def mk(ax, pos, along, label, d=14, s=1):
        b = (pos, along, d) if ax == "v" else (along, pos, d)
        return dict(pos=pos, lo=along - d / 2, hi=along + d / 2 + 20, bubble=b, dir=s, kind="stem", label=label)

    # ชื่อผิดชนิดในแกน (ป้ายพื้นที่ OCR เป็นตัวเลขในแกน A-E) ถูกทิ้งทั้งแถว; แถวไม่มีชื่อไม่แตะ
    L = consistent_labels({"v": [], "h": [mk("h", 150, 50, "A"), mk("h", 250, 50, "B"), mk("h", 350, 50, "C"),
                                           mk("h", 180, 400, "7"), mk("h", 280, 400, "1"),
                                           mk("h", 500, 900, None), mk("h", 600, 900, None)]})
    assert [ln["label"] for ln in L["h"]] == ["A", "B", "C", None, None]
    # เสมอกัน (2 ต่อ 2) ไม่ทิ้งอะไร — รูปตัดสองทิศในหน้าเดียว (2ชั้น_03 หน้า 20)
    L = consistent_labels({"v": [mk("v", 100, 50, "7"), mk("v", 200, 50, "1"), mk("v", 500, 600, "A"), mk("v", 600, 600, "B")],
                           "h": []})
    assert sorted(ln["label"] for ln in L["v"]) == ["1", "7", "A", "B"]
    # แถวไม่มีชื่อเลยทิ้งทั้งแถว; เส้นยาวไม่มีชื่อในแถวที่มีชื่อเก็บไว้ ('?'); วงที่เหลือคู่เดียวคือก้านไม่มีชื่อ -> หลุดด้วย
    lab = mk("v", 100, 50, "1") | dict(kind="long")
    q = mk("v", 200, 50, None) | dict(kind="long")
    nolab = [mk("v", x, 300, None) | dict(kind="long") for x in (150, 250)]
    alone = mk("v", 700, 500, "2") | dict(kind="long")
    stem_mate = mk("v", 800, 500, None)
    L = confirmed({"v": [lab, q] + nolab + [alone, stem_mate], "h": []})
    assert [(ln["pos"], ln["label"]) for ln in L["v"]] == [(100, "1"), (200, None)], L["v"]

    # สองแปลนวางคู่กันระดับเดียวกัน: แถววงบนต้องแยกที่คอลัมน์วงของแปลนขวา และจับคู่แปลนถูกฝั่ง
    v = [mk("v", x, 50, str(i % 3 + 1)) for i, x in enumerate((100, 200, 300, 700, 800, 900))]
    h = [mk("h", y, 50, ch) for y, ch in ((150, "A"), (300, "B"), (450, "C"))] + \
        [mk("h", y, 600, ch) for y, ch in ((150, "A"), (300, "B"), (450, "C"))]
    L = extend_to_plan({"v": v, "h": h})
    pv = {ln["pos"]: ln["plan"] for ln in L["v"]}
    assert pv[100] == pv[300] != pv[700] == pv[900], pv
    left_h = [ln for ln in L["h"] if ln["bubble"][0] == 50]
    assert all(ln["plan"] == pv[100] and ln["hi"] == 300 + 14 for ln in left_h), left_h   # จบที่เส้น 3 ของแปลนตัวเอง
    assert all(ln["hi"] == 450 + 14 for ln in L["v"])                                      # เส้นตั้งจบที่ C +1 วง

    # ตรวจรอบสอง 21 พ.ย.: (1) เส้นยาวทั้งคู่เยื้อง 0.34d ยังเป็นแถวเดียวกัน (แปลนขยายห้องน้ำ 1ชั้น_04 หน้า 13)
    got = bubble_lines([(100, 50, 14), (200, 54.8, 14)], {"v": [(100, 57, 600), (200, 61.8, 600)], "h": []}, 1000, 800)
    assert [ln["pos"] for ln in got["v"]] == [100, 200], got["v"]
    # (2) วงยกพ้นแถว ห่างเส้นข้างเคียง 1.3 วง (2' ของ 1ชั้น_36 หน้า 15) ถูกกู้
    got = bubble_lines(circs[:3] + [(118, 28, 14)], dict(segs, v=segs["v"][:3] + [(118, 35, 43)]), 1000, 800)
    assert [ln["pos"] for ln in got["v"]] == [100, 118, 200, 300], got["v"]
    # (3) วงไม่มีก้านในแถวที่ยืนยันแล้ว (วง 6 ของ 1ชั้น_38 หน้า 14) รับเป็นก้าน; วงไม่มีก้านนอกแถวไม่รับ
    got = bubble_lines(circs[:3] + [(400, 50, 14), (500, 200, 14)], dict(segs, v=segs["v"][:3]), 1000, 800)
    assert [(ln["pos"], ln["kind"]) for ln in got["v"]] == [(100, "long"), (200, "long"), (300, "long"), (400, "stem")], got["v"]
    # (4) ชื่อซ้ำในแถวเดียว = สองแปลน แม้ไม่มีคอลัมน์วงคั่น (แปลนไฟฟ้า/เต้ารับคู่กัน 1ชั้น_06 หน้า 44)
    v = [mk("v", x, 50, ch) for x, ch in ((100, "1"), (200, "2"), (300, "3"), (420, "1"), (520, "2"), (620, "3"))]
    L = extend_to_plan({"v": v, "h": [mk("h", y, 50, ch) for y, ch in ((150, "A"), (300, "B"))]})
    pv = {ln["pos"]: ln["plan"] for ln in L["v"]}
    assert pv[100] == pv[300] != pv[420] == pv[620], pv
    # (5) รูปด้านใต้แปลน (แถววงล่าง ก้านชี้ขึ้น เส้นยาวไม่ถึงแปลน แต่เส้นนอนของแปลนลากผ่าน) ไม่ใช่แปลนเดียวกัน;
    #     แปลนที่วาดแค่หัวกริด (ไม่ถึงกันทั้งสองแกน 2ชั้น_09 หน้า 25) ยังจับคู่ได้
    def lg(ax, pos, along, label, s, vlo, vhi):
        return mk(ax, pos, along, label, s=s) | dict(kind="long", vlo=vlo, vhi=vhi, lo=vlo, hi=vhi)
    top = [lg("v", x, 50, ch, 1, 43, 420) for x, ch in ((200, "1"), (300, "2"), (400, "3"))]
    elev = [lg("v", x, 700, ch, -1, 500, 707) for x, ch in ((200, "1"), (300, "2"), (400, "3"))]
    col = [lg("h", y, 40, ch, 1, 33, 600) for y, ch in ((100, "A"), (200, "B"), (300, "C"))]
    L = extend_to_plan({"v": top + elev, "h": col})
    pl = {(ln["pos"], _along(ln, "v")): ln["plan"] for ln in L["v"]}
    assert pl[(200, 50)] == L["h"][0]["plan"] != pl[(200, 700)], (pl, L["h"][0]["plan"])
    stub_v = [lg("v", x, 50, ch, 1, 43, 120) for x, ch in ((200, "1"), (300, "2"))]
    stub_h = [lg("h", y, 40, ch, 1, 33, 150) for y, ch in ((300, "A"), (400, "B"))]
    L = extend_to_plan({"v": stub_v, "h": stub_h})
    assert len({ln["plan"] for ax in L for ln in L[ax]}) == 1, L
    assert norm_ocr_label("1)") == "1" and norm_ocr_label(" a ") == "A" and norm_ocr_label("PS") is None
    print("OK — self-check ผ่าน (ตรรกะวงหัวกริด/คัดทิ้ง/จับคู่แปลน/regex — ไม่ได้เทียบกับ PDF จริง ใช้ --eval)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", nargs=2, metavar=("บ้าน", "หน้า"))
    ap.add_argument("--draw", nargs=3, metavar=("บ้าน", "หน้า", "ไฟล์.png"), help="วาดเส้นกริดที่จับได้ลงภาพหน้านั้น")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--no-ocr", action="store_true", help="ไม่ OCR วงหัวกริด (เร็ว ใช้ข้อความฝังอย่างเดียว)")
    ap.add_argument("--dump", metavar="ไฟล์.json", help="กับ --eval: เขียนเส้นที่จับได้รายหน้าลงไฟล์ (ไว้วัดตำแหน่งเทียบ pos_m)")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if a.draw:
        print("เส้นตั้ง, เส้นนอน, ผูกชื่อได้:", draw_page(a.draw[0], int(a.draw[1]), a.draw[2], ocr=not a.no_ocr))
        return
    if a.page:
        return show_page(a.page[0], int(a.page[1]), ocr=not a.no_ocr)
    if a.eval:
        return evaluate(ocr=not a.no_ocr, dump=a.dump)
    ap.print_help()


if __name__ == "__main__":
    main()
