#!/usr/bin/env python3
"""
tools/titleblock_extract.py — ส่วน 1 ของ pipeline King (ประชุม 18->19 พ.ย. 2569): หา title block ต่อหน้า
แล้วดึง sheet_code ออกมา พร้อมบอกว่าเจอที่แถบไหน (right/bottom) และอ่านมาจากไหน (text/ocr)

ขั้นต่ำที่ประชุมตั้ง: "หากรอบชื่อแบบให้เจอ แล้วดึงข้อมูลออกมา" — ไฟล์นี้ทำ sheet_code + pdf_page + sheet_name (--name)
และติดธงหน้าที่กรอบชื่อแบบไม่เจอ/ตำแหน่งต่างจากเล่ม (flag_moved)

ลำดับ (ตามที่ตกลงใน workmen's_diary/2026-11-18.md [22:33]):
  1. ข้อความฝังใน PDF (เร็ว ไม่ต้อง OCR): หาคำที่หน้าตาเป็นรหัสแผ่น (A-05, S-10) ในแถบขวา แล้วแถบล่าง
  2. ไม่เจอ -> render แถบนั้นแล้ว OCR (PaddleOCR) — ใช้เฉพาะ --ocr
  "เจอ" ต้องผ่านการทดสอบ ไม่ใช่เดา: คำที่อ่านได้ต้องเข้ารูปแบบรหัสแผ่น ไม่งั้นนับว่าไม่เจอ (found=false)

ผลวัด 2026-11-19 (เทียบ sheet_code ใน json เฉลย): สุ่มเว้นช่องทุก 5 บ้าน + 174 = 526 หน้า 33 บ้าน ~2 วิ/หน้า
  - หน้าที่เฉลยเป็นรหัสแผ่นแบบตัวอักษร+เลข: ถูก 475/475 (ข้อความฝัง 85 · OCR มุมขวาล่าง 364 · OCR แถบขวา 26)
  - ที่เหลือ 51 หน้าไม่ใช่รหัสแบบนั้น: ใบ BOQ/ปร.4 42 (ไม่เจอ 22, อ่าน 'SN-01' จากแถบผิด 20 — หน้าที่ไม่ใช่แผ่นแบบ
    ไม่ควรถูกส่งเข้าส่วนนี้), เฉลยว่าง 4, ป้าย "แผ่นที่ n/2" 2, เลขล้วน 1/2/3 3 (regex ต้องมีตัวอักษร -> ไม่รองรับ)
  - ข้อจำกัด: ยังไม่ทำ sheet_name · เฉลยเองผิดอย่างน้อย 4 หน้า (บ้าน 1ชั้น_30 หน้า 14-17 เฉลย S05..S08 แต่แบบพิมพ์ S-06..S-09)
  - วัดบางบ้านเท่านั้น ไม่ได้ครบ 175 บ้าน; ภาพสแกนคุณภาพต่ำ/กรอบชื่อแบบตำแหน่งแปลกยังไม่ได้ลองเป็นกลุ่ม

ชื่อแผ่น (sheet_name, --name) วัด 2026-11-20 เทียบ sheet_name ใน json เฉลย (ความคล้ายตัวอักษรหลังตัดช่องว่าง/สระบน-ล่าง/วรรณยุกต์ ตั้งแต่ 0.8):
  วิธี: OCR ไทย (th_PP-OCRv5_mobile_rec) แถบขวา x>=0.72,y>=0.40 แล้วแถบล่าง; ชื่อ = แถวระหว่างป้าย "แสดงแบบ/แบบแสดง/ชื่อแบบ"
  กับป้าย "มาตราส่วน/วัน/เดือน/เลขที่"; ป้ายที่ OCR พลาด 1 ตัวอักษรยังจับได้ ~5-9 วิ/หน้า บน CPU; ข้อความฝังไทยจริงอ่านชื่อได้ 0 หน้า
  (ไทยในข้อความฝังส่วนใหญ่เพี้ยน) -> ชื่อทุกตัวมาจาก OCR
  - ชุดที่ไม่เคยดู (บ้านที่ 4,10,16,... = hs[3::6]) 107 หน้า: เจอชื่อ 90 (84%) · ตรงเฉลย >=0.8 46 (43%) · ใกล้ 0.5-0.8 25 · ผิด <0.5 19 · ไม่เจอ 17
  - ชุดที่ใช้จูนกฎ (hs[0::6]) 96 หน้า: เจอ 67 (70%) · ตรง 39 · ใกล้ 18 · ผิด 10 · ไม่เจอ 29 (ก่อนจูนกฎ: เจอ 60 ตรง 31) — ตัวเลขชุดนี้ดีเกินจริง
  - "ผิด/ใกล้" ส่วนหนึ่งไม่ใช่ OCR พลาดแต่นิยามต่างกัน: กรอบชื่อแบบพิมพ์ชื่อทั่วไป ("แบบขยายโครงสร้าง คสล.") แต่เฉลยตั้งชื่อตามแต่ละ view
    ("ขยาย F1, F2") และหน้าสารบัญเฉลยเรียงต่างจากที่พิมพ์ — ยังไม่ได้แยกส่วนนี้ออกจากข้อผิดจริง
  - ที่ยังทำไม่ได้: กรอบที่ไม่มีป้าย (แบบมาตรฐาน สปช., ป้ายอังกฤษล้วน) -> ไม่เจอ (ไม่เดา); สแกนคุณภาพต่ำอ่านป้ายไม่ออก;
    OCR ยังสะกดผิดบ้าง ('ชึ้น' แทน 'ชั้น') — ถ้าจะใช้ต่อให้เทียบกับสารบัญแบบของเล่มเดียวกันเพื่อแก้คำ
ธง (flag_moved) วัดใหม่ 2026-11-21 — ผลเดิม "moved 16 หน้า = ใบ BOQ" สรุปกลับด้าน (ดูภาพแล้ว):
  - 16 หน้านั้นคือแผ่นแบบสุขาภิบาลจริง SN-01..SN-08 (1ชั้น_11 น.34-41, 1ชั้น_23 น.39-46) รหัสอยู่ที่ปกติ (0.872,0.924) แต่ค่ากลาง
    (โหมดข้อความฝัง) ถูกใบ BOQ 10 หน้า/เล่มที่มี 'SN-08' อ้างอิงในหัวใบที่ (0.923,0.716) ลากไป -> แก้: ค่ากลางคิดจากรหัสที่ไม่ซ้ำหน้าอื่น
    หลังแก้ ข้อความฝังทั้งคลัง: moved 20 หน้า = ใบ BOQ ทั้งหมด, แผ่นแบบ 0
  - หากรอบย้ายจริงทั้ง 175 เล่ม (ขนาด/แนว/rotation หน้า, ตำแหน่งรหัสในข้อความฝังทั้งหน้า, เส้นกรอบยาวต่อหน้า แล้วดูภาพย่อทุกเล่มที่มีหน้าต่าง):
    เจอแค่ (ก) หน้าสแกนตะแคง กรอบไปอยู่ขอบบน: ครอบครัวไทยเป็นสุข2 น.2-18 (รหัส A-xx), ใหญ่_3ชั้น_06 น.1-8; (ข) แผ่นครุภัณฑ์ไม่มีกรอบ
    ชื่ออยู่บน/ซ้าย: ใหญ่_1ชั้น_11 น.6, 13 น.5, 14 น.5, 15 น.5, เล็ก_1ชั้น_57 น.6 (เล่มรหัสเลขล้วน อ่านไม่ได้อยู่แล้ว) — ทุกกรณีอยู่นอกแถบ
    ขวา/ล่างที่ค้น จึงเป็น moved ไม่ได้ ได้แค่ not_found; ไม่เคยเจอกรอบแผ่นแบบที่ย้ายแต่ยังอยู่ในแถบ -> moved ยังไม่เคยจับกรอบย้ายจริงได้
  - เดิมเล่มที่เจอรหัสไม่ถึง 3 หน้าไม่มีธงเลย (OCR: ครอบครัวไทยเป็นสุข2 0/18, ใหญ่_3ชั้น_06 0/11) -> แก้: ไม่เจอ = ติดธงเสมอ (หลังแก้ 16/18,
    9/11); ที่ยังหลุดคือหน้าที่ OCR อ่านรหัสผิดจากในแบบ ('A-05' จากวงรูปตัดแทน A-04, 'A16N', 'G-1') เพราะไม่มีค่ากลางให้เทียบ
  - not_found แยกไม่ได้ว่า "กรอบย้ายออกนอกแถบ" หรือ "รหัสไม่ใช่รูปแบบที่รองรับ" (เล็ก_2ชั้น_17 ไม่เจอ 22/22) และ moved ติดกับรหัสที่อ่านผิด
    ได้ด้วย ('B16' จากคาน ใหญ่_2ชั้น_21 น.7,10 กรอบไม่ได้ย้าย)
  - เล่มปกติ OCR (1ชั้น_27, ใหญ่_2ชั้น_24, ใหญ่_2ชั้น_09, 1ชั้น_11): moved บนแผ่นแบบ 0, not_found เฉพาะปก/สารบัญ/หน้ารายการ;
    แผ่นปกติคลาดจากค่ากลาง <=0.007 (ข้อความฝัง 49 เล่ม 796 แผ่น <=0.006) แต่ข้อความฝัง (กลางคำ) กับ OCR (มุมขวาล่างกล่อง) ในเล่มเดียวกัน
    ห่างกันเป็นระบบ 0.022 (1ชั้น_11) — MOVED_TOL=0.06 ยังเป็นค่าที่เลือกเอง

กับดักที่เจอจริง (วัดจากคลังนี้ 2026-11-19 ไม่ใช่เดา):
- PDF จาก CAD มีข้อความฝังแค่ 1,928 จาก 6,267 หน้า และมีรหัสแผ่นในแถบแค่ 878 หน้า (37 บ้านเกือบทุกหน้า)
  บ้านอย่าง 174 กรอบชื่อแบบเป็นเส้น (outline) ไม่ใช่ข้อความ -> ต้อง OCR แม้ไฟล์เป็นเวกเตอร์
- ภาษาไทยในข้อความฝังของ PDF กลุ่ม siamplan เป็นรหัสเพี้ยน (ฟอนต์เก่า) อ่านชื่อแผ่นไทยตรงๆ ไม่ได้
  แต่ตัวละติน/ตัวเลข (รหัสแผ่น วันที่) อ่านถูก
- หน้าที่ rotation != 0: พิกัดคำเป็นพิกัดก่อนหมุน ต้องคูณ page.rotation_matrix ก่อนใช้ (ไม่งั้นแถบขวา
  กลายเป็นแถบอื่น)
- PaddleOCR ชน native crash ถ้าด้านยาวเกิน ~4,000 px บนเครื่องนี้ (ดู titleblock_ocr.py) และ CPU ช้า (บ้าน 174
  รอบแรก render 200 dpi + ตัดช่อง: 26 หน้ายังไม่จบใน 10 นาที) -> render ทั้งหน้าไม่เกิน 3,300 px ช่องเดียว

    python tools/titleblock_extract.py <บ้าน>                 # ข้อความฝังอย่างเดียว พิมพ์ JSON
    python tools/titleblock_extract.py <บ้าน> --ocr           # หน้าที่ข้อความฝังไม่เจอ -> OCR ต่อ
    python tools/titleblock_extract.py <บ้าน> --ocr --name    # + sheet_name (OCR ไทย ช้า ~5-9 วิ/หน้า)
    python tools/titleblock_extract.py <บ้าน> --pages 3-8 --out ผล.json
    python tools/titleblock_extract.py --eval บ้าน1 บ้าน2 ... # เทียบกับ sheet_code ใน json เฉลย
    python tools/titleblock_extract.py --eval --name บ้าน1 ... # วัดชื่อแผ่น (หมายเหตุ: ส่งชื่อบ้านไทยผ่านบรรทัดคำสั่งใน Git Bash บางครั้งเพี้ยน -> ใช้ PYTHONUTF8=1 หรือเรียกจาก python)
    python tools/titleblock_extract.py --demo                 # self-check ไม่ต้องมีไฟล์จริง
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = ROOT / "image"

# รหัสแผ่น: A-05, S-10, ST-01, A05, S-1, A-05A (ตัวอักษรใหญ่ 1-3 + ตัวเลข 1-3 + ตัวอักษรท้ายได้)
# ตัวใหญ่อย่างเดียว: OCR อ่านพลาดเป็นตัวเล็กบ่อย ('au100' จาก "1:100") ส่วนรหัสจริงในคลังนี้ใหญ่ทั้งหมด
CODE_RE = re.compile(r"^[A-Z]{1,3}-?\d{1,3}[A-Z]?$")
# ชื่อเหล็ก/มาร์คที่หน้าตาคล้ายรหัสแผ่น (DB16, RB9, SD40) — ตัดทิ้งเมื่อไม่มีขีด (SD-01 ยังเป็นรหัสแผ่นได้)
NOT_CODE_RE = re.compile(r"^(DB|RB|SD|SR|PC|PT)\d")

# แถบ (สัดส่วนของหน้าตามที่ตามองเห็น หลังหมุนแล้ว) — ขอบแคบกว่าหน้าจริงไม่ได้ เพราะบางชุดกรอบสูงถึง 45% ของหน้า
RIGHT = dict(x0=0.80, y0=0.50)    # แถบขวา: cx >= x0 และ cy >= y0
BOTTOM = dict(x0=0.50, y0=0.85)   # แถบล่าง: cy >= y0 และ cx >= x0
# OCR ช้า (CPU ~7 วิ/แถบ) จึงเริ่มจากมุมขวาล่างเล็กๆ — รหัสแผ่นอยู่มุมนี้ทั้งชุดแถบขวาและชุดแถบล่างที่เห็น
# (บ้าน 174: ช่องรหัสอยู่ท้ายสุดของกรอบล่าง) ไม่เจอค่อยขยายเป็นแถบเต็ม; 'corner' เป็นส่วนย่อยของทั้ง right/bottom
OCR_REGIONS = {"corner": dict(x0=0.80, y0=0.86), "right": RIGHT, "bottom": BOTTOM}
MAX_PAGE_PX = 3300               # ด้านยาวของ "ทั้งหน้า" ตอน render — ต้อง < ~4000 (paddle ล้ม) และทำให้แถบล่างเป็นช่องเดียว
                                  # ไม่ต้องตัดช่อง; รหัสแผ่นเป็นตัวใหญ่พอที่ ~100 dpi บน A1 (วัดจากบ้าน 174)


def is_code(s):
    s = s.strip()
    if not CODE_RE.match(s):
        return False
    if "-" in s:
        return True
    # ไม่มีขีด: ต้องมีเลขอย่างน้อย 2 หลัก (S10, A01) — 'A1'/'A3' คือขนาดกระดาษในช่องมาตราส่วน ไม่ใช่รหัสแผ่น
    return not NOT_CODE_RE.match(s) and sum(c.isdigit() for c in s) >= 2


def norm_code(s):
    """เทียบรหัสแบบไม่สนตัวพิมพ์/ขีด/ช่องว่าง: 'a-05' == 'A05'"""
    return re.sub(r"[\s\-_.]", "", s or "").upper()


def pick_cand(cands):
    """cands = [(cx, cy, text)] -> ตัวที่ชิดมุมขวาล่างที่สุด (รหัสแผ่นอยู่ล่างสุดของ title block เสมอ
    ในชุดที่เห็น; รหัสอ้างอิงแผ่นอื่นในหมายเหตุอยู่สูงกว่า) — ประเมินกับเฉลยใน --eval"""
    if not cands:
        return None
    return max(cands, key=lambda c: c[0] + c[1])


def pick_code(cands):
    c = pick_cand(cands)
    return c[2] if c else None


def text_layer(page):
    """คืน dict(found, strip, sheet_code, source) จากข้อความฝัง หรือ found=False"""
    words = page.get_text("words")
    if len(words) < 3:
        return dict(found=False, strip=None, sheet_code=None, source="text", reason="no_text_layer")
    rm = page.rotation_matrix
    W, H = page.rect.width, page.rect.height
    right, bottom = [], []
    import fitz  # หลัง check words เพราะหน้า 0 ข้อความเยอะที่สุด
    for w in words:
        if not is_code(w[4]):
            continue
        r = fitz.Rect(w[:4]) * rm
        cx, cy = (r.x0 + r.x1) / 2 / W, (r.y0 + r.y1) / 2 / H
        if cx >= RIGHT["x0"] and cy >= RIGHT["y0"]:
            right.append((cx, cy, w[4]))
        elif cy >= BOTTOM["y0"] and cx >= BOTTOM["x0"]:
            bottom.append((cx, cy, w[4]))
    for strip, cands in (("right", right), ("bottom", bottom)):
        best = pick_cand(cands)
        if best:
            return dict(found=True, strip=strip, sheet_code=best[2], source="text", n_candidates=len(cands),
                        code_pos=(round(best[0], 3), round(best[1], 3)))
    return dict(found=False, strip=None, sheet_code=None, source="text", reason="no_code_in_strips")


_READER = None


def _reader():
    global _READER
    if _READER is None:
        # ต้องตั้ง env cache ก่อน import paddleocr (กับดักเครื่องนี้ ดู titleblock_ocr.py) — reuse module นั้น
        sys.path.insert(0, str(Path(__file__).parent))
        import titleblock_ocr  # noqa: F401  (ตั้ง PADDLE_PDX_CACHE_HOME/HOME/USERPROFILE ตอน import)
        from paddleocr import PaddleOCR
        # ตัวตรวจจับรุ่น mobile ไม่ใช่ server: วัด 2026-11-19 เร็วกว่า ~2.5 เท่า (7 วิ vs 18 วิ ต่อแถบขวา บน CPU)
        # และอ่านรหัสแผ่นถูกเท่ากัน — เราต้องการแค่รหัสละติน ไม่ใช่ข้อความไทยทั้งกรอบ
        # สร้าง reader เอง ไม่แก้ titleblock_ocr.get_reader() เพราะ pass 0 hint ใช้ตัวนั้นอยู่
        # ล็อกชื่อโมเดลอ่านด้วย: ถ้าระบุแค่ det แล้วปล่อยให้ paddle เลือก rec เอง มันเลือก PP-OCRv6_medium_rec
        # (ไม่ใช่ th_PP-OCRv5_mobile_rec ที่ titleblock_ocr.py ใช้) — ผลวัดทุกตัวเลขในไฟล์นี้มาจากตัวนี้
        _READER = PaddleOCR(lang="th", text_detection_model_name="PP-OCRv5_mobile_det",
                            text_recognition_model_name="PP-OCRv6_medium_rec",
                            use_doc_orientation_classify=False, use_doc_unwarping=False,
                            use_textline_orientation=False, enable_mkldnn=False)  # ห้ามลบ mkldnn=False (กับดักเครื่องนี้)
    return _READER


def _strip_image(page, spec, turns=0):
    """render แถบตามสัดส่วนหน้า (ตามที่ตามองเห็น) -> ภาพ numpy RGB + (กว้าง, สูง) พิกเซล
    turns = จำนวนครั้ง 90° ตามเข็มที่ต้องหมุนหน้าให้ตั้งตรง (หน้าสแกนตะแคง ดู page_orient.py) — สัดส่วนของ spec
    อ้างอิงหน้าที่ตั้งตรงแล้ว; 0 = ไม่หมุน (พฤติกรรมเดิมทุกไบต์)"""
    import fitz
    import numpy as np
    W, H = page.rect.width, page.rect.height
    dpi = int(MAX_PAGE_PX / (max(W, H) / 72))   # PyMuPDF set_dpi ต้องเป็น int
    clip = None if turns else fitz.Rect(W * spec["x0"], H * spec["y0"], W, H)
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    if pix.n == 1:
        img = np.repeat(img, 3, axis=2)
    if turns:                                    # หมุนทั้งหน้าให้ตั้งตรงก่อน แล้วค่อยตัดแถบ
        img = np.rot90(img, -turns)
        h, w = img.shape[:2]
        img = img[int(h * spec["y0"]):, int(w * spec["x0"]):]
    return np.ascontiguousarray(img), img.shape[1], img.shape[0]


def ocr_strip(page, strip, turns=0):
    """render แถบ -> OCR -> คืน (ผู้สมัครรหัสที่ชิดมุมขวาล่างสุด (cx, cy, text) หรือ None, จำนวนบรรทัดที่ OCR อ่านได้)
    ไม่เก็บข้อความดิบออกไป: ใน title block มีชื่อ/เลขใบอนุญาตวิศวกร (ข้อมูลส่วนบุคคล ไม่เข้า label)"""
    spec = OCR_REGIONS[strip]
    img, pw, ph = _strip_image(page, spec, turns)
    cands, n_lines = [], 0
    for r in _reader().predict(img):
        for txt, box in zip(r.get("rec_texts", []), r.get("rec_boxes", [])):
            n_lines += 1
            for tok in re.split(r"[\s,;:/()]+", txt):
                if is_code(tok):
                    # ตำแหน่งในหน้า (สัดส่วน) ใช้เลือกตัวที่ชิดมุมขวาล่างเหมือนทางข้อความฝัง
                    cands.append((spec["x0"] + (1 - spec["x0"]) * float(box[2]) / pw,
                                  spec["y0"] + (1 - spec["y0"]) * float(box[3]) / ph, tok))
    return pick_cand(cands), n_lines


# ---------- ชื่อแผ่น (sheet_name) ----------
# ช่องชื่อแผ่นในกรอบชื่อแบบมีป้าย ("แสดงแบบ" / "แบบแสดง" / "ชื่อแบบ") ชื่ออยู่ใต้ป้ายจนถึงป้ายถัดไป (มาตราส่วน/วันที่/เลขที่แบบ)
# ไม่เจอป้าย = ไม่เจอชื่อ (ไม่เดา) -> กรอบชื่อแบบแบบอื่น (ชื่อภาพใหญ่ใต้รูป, ป้ายภาษาอังกฤษล้วน) ยังไม่รองรับ
NAME_START = re.compile(r"แสดงแบบ|แบบแสดง|ชื่อแบบ|ชื่อแผ่น|DRAWINGTITLE|SHEETTITLE|^TITLE")
NAME_END = re.compile(r"มาตรา|^SCALE|เดือน|วันที่|วันที|^DATE|เลขที่|แผ่นที่|จำนวนแผ่น|^NO\.?$|^DWG|^JOB|ผู้เขียน|ผู้ตรวจ")
NAME_REGIONS = {"right": dict(x0=0.72, y0=0.40), "bottom": dict(x0=0.50, y0=0.80)}
MAX_NAME_LINES = 4
_TH = re.compile(r"[ก-ฮ]")           # พยัญชนะไทย


def _norm_label(t):
    return re.sub(r"\s+", "", t).upper()


def group_rows(items):
    """items = [(yc, h, x, text)] -> ข้อความทีละแถว บนลงล่าง (คำ/ท่อนที่ y เกือบเท่ากันรวมเป็นแถวเดียว เรียงซ้ายไปขวา)"""
    rows = []   # [yc, h, [(x, text)]]
    for yc, h, x, t in sorted(items):
        if rows and abs(yc - rows[-1][0]) <= 0.5 * min(h, rows[-1][1]):
            rows[-1][2].append((x, t))
        else:
            rows.append([yc, h, [(x, t)]])
    return [" ".join(t for _, t in sorted(r[2])) for r in rows]


START_LABELS = ("แสดงแบบ", "แบบแสดง", "ชื่อแบบ", "ชื่อแผ่น")
END_LABEL = "มาตราส่วน"
FUZZY_MIN = 0.75     # OCR ไทยพลาดป้าย 1 ตัวอักษรบ่อย ('แสดงเบบ', 'แบบแลดง', 'มาคราล่วน' — เจอจริงในบ้านที่สแกน) -> ยอมพลาดได้ 1 ตัว
SCALE_RE = re.compile(r"\d\s*[:;]\s*\d{2,3}")   # '1:100' — มาตราส่วนที่ป้ายถูก OCR พัง ยังเป็นจุดจบของช่องชื่อ


def _fuzzy_head(k, label):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, name_key(k[:len(label)]), name_key(label)).ratio() >= FUZZY_MIN


def _start_rest(t):
    """แถวนี้เป็นป้ายเริ่มช่องชื่อไหม -> เศษข้อความหลังป้ายในแถวเดียวกัน ('' ถ้าไม่มี) หรือ None ถ้าไม่ใช่ป้ายเริ่ม"""
    k = _norm_label(t)
    m = NAME_START.search(k)
    if m:
        return k[m.end():]
    for lab in START_LABELS:
        if _fuzzy_head(k, lab):
            return k[len(lab):]
    return None


def _is_end(t):
    k = _norm_label(t)
    return bool(NAME_END.search(k) or SCALE_RE.search(k) or _fuzzy_head(k, END_LABEL))


def pick_name(rows):
    """rows = ข้อความทีละแถวบนลงล่าง -> ชื่อแผ่น หรือ None (ต้องเจอป้ายเริ่มก่อน)"""
    for i, t in enumerate(rows):
        rest = _start_rest(t)
        if rest is None:
            continue
        out = []
        if len(_TH.findall(rest)) >= 3:            # ชื่ออยู่แถวเดียวกับป้าย (บางชุด)
            out.append(rest)
        for t2 in rows[i + 1:]:
            if _is_end(t2) or len(out) >= MAX_NAME_LINES:
                break
            if len(_TH.findall(_norm_label(t2))) >= 2 and name_key(t2) not in name_key(" ".join(out)):
                out.append(t2.strip())             # เศษ OCR ('c', 'A3') และท่อนซ้ำ ('ลนฐานราก' ซ้ำ 'แปลนฐานราก') ถูกข้าม
        return " ".join(out) if out else None
    return None


_READER_TH = None


def _reader_th():
    """OCR ภาษาไทยจริง (th_PP-OCRv5_mobile_rec) — PP-OCRv6_medium_rec ของ _reader() อ่านไทยเป็นละตินเพี้ยน (วัดแล้ว)"""
    global _READER_TH
    if _READER_TH is None:
        sys.path.insert(0, str(Path(__file__).parent))
        import titleblock_ocr  # noqa: F401  (ตั้ง env cache)
        from paddleocr import PaddleOCR
        _READER_TH = PaddleOCR(lang="th", text_detection_model_name="PP-OCRv5_mobile_det",
                               text_recognition_model_name="th_PP-OCRv5_mobile_rec",
                               use_doc_orientation_classify=False, use_doc_unwarping=False,
                               use_textline_orientation=False, enable_mkldnn=False)
    return _READER_TH


def name_from_text(page, spec):
    """ข้อความฝังที่เป็นภาษาไทยจริงในแถบ -> ชื่อ หรือ None (ฟอนต์เก่าของ PDF CAD ส่วนใหญ่เพี้ยน -> None แล้วไป OCR)"""
    import fitz
    rm, W, H = page.rotation_matrix, page.rect.width, page.rect.height
    items = []
    for w in page.get_text("words"):
        r = fitz.Rect(w[:4]) * rm
        cx, cy = (r.x0 + r.x1) / 2 / W, (r.y0 + r.y1) / 2 / H
        if cx >= spec["x0"] and cy >= spec["y0"] and _TH.search(w[4]):
            items.append((cy, (r.y1 - r.y0) / H, cx, w[4]))
    return pick_name(group_rows(items)) if items else None


def name_from_ocr(page, spec, turns=0):
    img, pw, ph = _strip_image(page, spec, turns)
    items = []
    for r in _reader_th().predict(img):
        for txt, box in zip(r.get("rec_texts", []), r.get("rec_boxes", [])):
            y0, y1, x0 = float(box[1]) / ph, float(box[3]) / ph, float(box[0]) / pw
            items.append(((y0 + y1) / 2, y1 - y0, x0, txt))
    return pick_name(group_rows(items))


def extract_name(page, strip_hint=None, use_ocr=True, turns=0):
    """-> dict(sheet_name, name_source text|ocr, name_strip) หรือ sheet_name=None + reason
    ลองแถบที่รหัสแผ่นเจอก่อน แล้วอีกแถบ; ข้อความฝังก่อน OCR; ไม่เก็บข้อความดิบของแถบ (มีชื่อวิศวกร)"""
    order = ["bottom", "right"] if strip_hint == "bottom" else ["right", "bottom"]
    for strip in order:
        spec = NAME_REGIONS[strip]
        name = name_from_text(page, spec)
        if name:
            return dict(sheet_name=name, name_source="text", name_strip=strip)
        if use_ocr:
            name = name_from_ocr(page, spec, turns)
            if name:
                return dict(sheet_name=name, name_source="ocr", name_strip=strip)
    return dict(sheet_name=None, name_source=None, name_strip=None, name_reason="no_name_label_in_strips")


def extract_page(page, use_ocr=False, with_name=False, turns=0):
    res = extract_code(page, use_ocr, turns)
    if with_name:
        res.update(extract_name(page, res.get("strip"), use_ocr, turns))
    return res


def extract_code(page, use_ocr=False, turns=0):
    res = text_layer(page)
    res["pdf_page"] = page.number + 1
    if res["found"] or not use_ocr:
        return res
    for strip in OCR_REGIONS:           # corner -> right -> bottom (เล็ก/เร็วก่อน ขยายเมื่อไม่เจอ)
        best, n = ocr_strip(page, strip, turns)
        if best:
            return dict(found=True, strip=strip, sheet_code=best[2], source="ocr", pdf_page=page.number + 1,
                        code_pos=(round(best[0], 3), round(best[1], 3)))
    return dict(found=False, strip=None, sheet_code=None, source="ocr", reason="no_code_in_strips", pdf_page=page.number + 1)


def pdf_of(house):
    p = IMAGE_DIR / house / f"{house}.pdf"
    if not p.exists():
        sys.exit(f"ไม่พบ {p}")
    return p


def parse_pages(spec, n):
    if not spec:
        return range(n)
    a, _, b = spec.partition("-")
    return range(int(a) - 1, min(int(b or a), n))


MOVED_TOL = 0.06   # สัดส่วนหน้า: รหัสแผ่นห่างจากตำแหน่งกลางของทั้งเล่มเกินนี้ = กรอบชื่อแบบน่าจะย้ายที่ (ค่าที่เลือกเอง; แผ่นปกติคลาด <=0.007 วัด 21 พ.ย.)


def flag_moved(results, tol=MOVED_TOL):
    """ติดธงต่อหน้า (ไม่แก้ผลอื่น): titleblock_not_found = หน้านี้ไม่เจอ (ติดเสมอ ไม่ขึ้นกับว่าทั้งเล่มเจอกี่หน้า);
    titleblock_moved = เจอรหัสแต่ตำแหน่งห่างจากค่ากลางของเล่มเกิน tol — ค่ากลางคิดจากหน้าที่รหัสไม่ซ้ำหน้าอื่น (รหัสแผ่นจริงมีหน้าเดียว;
    รหัสที่ซ้ำหลายหน้าคือการอ้างอิง เช่น 'SN-08' ในหัวใบ BOQ) ไม่ถึง 3 หน้าใช้ทุกหน้าที่เจอ ยังไม่ถึง 3 = ไม่ตัดสิน moved
    หน้าที่ติดธงให้คนหรือขั้นอื่นจัดการแยก (ตามที่ประชุมสั่ง)"""
    for r in results:
        if not r["found"]:
            r["flag"] = "titleblock_not_found"
    found = [r for r in results if r.get("code_pos")]
    n = Counter(norm_code(r.get("sheet_code")) for r in found)
    pos = [r["code_pos"] for r in found if n[norm_code(r.get("sheet_code"))] == 1]
    if len(pos) < 3:
        pos = [r["code_pos"] for r in found]
    if len(pos) < 3:
        return results
    mx, my = sorted(p[0] for p in pos)[len(pos) // 2], sorted(p[1] for p in pos)[len(pos) // 2]
    for r in found:
        if abs(r["code_pos"][0] - mx) > tol or abs(r["code_pos"][1] - my) > tol:
            r["flag"] = "titleblock_moved"
    return results


def run_house(house, use_ocr=False, pages=None, with_name=False):
    import fitz
    doc = fitz.open(pdf_of(house))
    out = flag_moved([extract_page(doc[i], use_ocr, with_name) for i in parse_pages(pages, len(doc))])
    doc.close()
    return out


# ---------- เทียบกับเฉลย ----------

def load_gt(house):
    """{pdf_page: sheet_code ที่พบบ่อยสุดในไฟล์ json ของบ้านนั้น} จาก json_แก้ไขแล้ว + rawjson (ถ้ามี)
    ชื่อไฟล์ลงท้าย 'หน้าNN' = เลขหน้า PDF (ตรวจแล้วตรงกับ doc_page)"""
    per = {}
    for base in ("json_แก้ไขแล้ว", "rawjson_ยังไม่ได้แก้ไขโดนคน"):
        for d in (ROOT / base).glob(f"*{house}"):
            for f in d.glob("*.json"):
                m = re.search(r"หน้า(\d+)", f.name)
                if not m:
                    continue
                try:
                    j = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                code = j.get("sheet_code") if isinstance(j, dict) else None
                if code:
                    per.setdefault(int(m.group(1)), []).append(norm_code(code))
        if per:
            return {p: Counter(v).most_common(1)[0][0] for p, v in per.items()}  # เฉลยแก้แล้วชนะ rawjson
    return {}


def load_gt_names(house):
    """{pdf_page: [sheet_name ของแต่ละ view ในหน้านั้น]} เฉพาะไฟล์ที่มี sheet_code (= แผ่นแบบจริง ไม่ใช่ grid master)"""
    per = {}
    for base in ("json_แก้ไขแล้ว", "rawjson_ยังไม่ได้แก้ไขโดนคน"):
        for d in (ROOT / base).glob(f"*{house}"):
            for f in d.glob("*.json"):
                m = re.search(r"หน้า(\d+)", f.name)
                if not m or int(m.group(1)) == 0:
                    continue
                try:
                    j = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(j, dict) and j.get("sheet_code") and j.get("sheet_name"):
                    per.setdefault(int(m.group(1)), []).append(str(j["sheet_name"]))
        if per:
            return per
    return {}


_DROP = re.compile(r"[\s,\-./()ัิ-ฺ็-๎]")


def name_key(s):
    """เทียบชื่อแบบไม่สนช่องว่าง/เครื่องหมาย/สระบน-ล่าง/วรรณยุกต์ (OCR ไทยพลาดตรงนี้บ่อย: 'ชึ้น' แทน 'ชั้น')"""
    return _DROP.sub("", s or "")


def name_sim(got, gts):
    """ความคล้าย 0..1 กับชื่อเฉลยของหน้านั้น (เทียบรายชื่อแต่ละ view และชื่อที่ต่อกันทั้งหมด เอาค่าสูงสุด)"""
    from difflib import SequenceMatcher
    g = name_key(got)
    cands = [name_key(x) for x in gts] + [name_key("".join(gts))]
    return max(SequenceMatcher(None, g, c).ratio() for c in cands)


def evaluate_names(houses, per_house=4):
    """วัดเฉพาะชื่อแผ่น: หน้าแผ่นแบบที่เฉลยมีชื่อ (เลือกเว้นช่องเท่าๆ กัน per_house หน้า/บ้าน) -> OCR/ข้อความ -> เทียบเฉลย"""
    import fitz
    tot, shown = Counter(), 0
    for h in houses:
        gt = load_gt_names(h)
        pages = sorted(gt)
        if not pages:
            continue
        step = max(1, len(pages) // per_house)
        doc = fitz.open(pdf_of(h))
        for pn in pages[::step][:per_house]:
            if pn > len(doc):
                continue
            r = extract_name(doc[pn - 1])
            if not r["sheet_name"]:
                tot["not_found"] += 1
                print(f"   ไม่เจอ {h} หน้า {pn}: เฉลย {gt[pn]!r}")
                continue
            sim = name_sim(r["sheet_name"], gt[pn])
            k = "good(>=0.8)" if sim >= 0.8 else "close(0.5-0.8)" if sim >= 0.5 else "wrong(<0.5)"
            tot[k] += 1
            tot[r["name_source"]] += 1
            if sim < 0.8 and shown < 25:
                shown += 1
                print(f"   {k} {h} หน้า {pn} ({r['name_strip']}/{r['name_source']}): อ่านได้ {r['sheet_name']!r} เฉลย {gt[pn]!r}")
    n = sum(tot[k] for k in ("good(>=0.8)", "close(0.5-0.8)", "wrong(<0.5)", "not_found"))
    print(dict(tot), "รวม", n, "หน้า")


def evaluate(houses, use_ocr=False):
    tot = Counter()
    for h in houses:
        gt = load_gt(h)
        res = run_house(h, use_ocr)
        c = Counter()
        for r in res:
            g = gt.get(r["pdf_page"])
            if g is None:
                c["no_gt"] += 1
                continue
            if not r["found"]:
                c["missed"] += 1
            elif norm_code(r["sheet_code"]) == g:
                c["correct"] += 1
            else:
                c["WRONG"] += 1
                print(f"   ผิด {h} หน้า {r['pdf_page']}: อ่านได้ {r['sheet_code']!r} เฉลย {g!r} ({r['strip']}/{r['source']})")
        print(f"{h:28s} หน้า={len(res):3d} เฉลย={len(gt):3d}  ถูก={c['correct']:3d} พลาด(ไม่เจอ)={c['missed']:3d} ผิด={c['WRONG']:3d} ไม่มีเฉลย={c['no_gt']:3d}")
        tot += c
    judged = tot["correct"] + tot["missed"] + tot["WRONG"]
    if judged:
        print(f"รวม: ตัดสินได้ {judged} หน้า | ถูก {tot['correct']} ({tot['correct']/judged:.0%}) | "
              f"ไม่เจอ {tot['missed']} | ผิด {tot['WRONG']} ({tot['WRONG']/judged:.1%})")


def demo():
    assert is_code("A-05") and is_code("S10") and is_code("ST-01") and is_code("SD-01") and is_code("A-05A")
    assert not is_code("DB16") and not is_code("RB9") and not is_code("SD40") and not is_code("1:100")
    assert not is_code("Tel") and not is_code("A")
    assert not is_code("A1") and not is_code("A3") and not is_code("au100")   # ขนาดกระดาษ / OCR อ่านพลาดตัวเล็ก
    assert is_code("A-1")                                                     # มีขีด = รหัสแผ่น แม้เลขหลักเดียว
    assert norm_code("a-05") == norm_code("A05") == "A05"
    assert pick_code([(0.9, 0.5, "A-01"), (0.9, 0.95, "A-05")]) == "A-05"   # ชิดมุมขวาล่างชนะ
    assert pick_code([]) is None
    # ชื่อแผ่น: ชื่ออยู่ระหว่างป้าย 'แสดงแบบ' กับ 'มาตราส่วน'; ไม่มีป้าย = None (ไม่เดา)
    assert pick_name(["สถาปนิก", "แสดงแบบ", "แปลนพื้นชั้น 1", "c", "แปลนหลังคา", "มาตราส่วน", "ไม่ใช่ชื่อ"]) == "แปลนพื้นชั้น 1 แปลนหลังคา"
    assert pick_name(["แปลนฐานราก", "SCALE"]) is None
    assert pick_name(["สถาปนิก", "แสดงเบบ", "a", "รูปด้าน 3,4", "ขยายหลังคา", "มาตราส่วน 1:100"]) == "รูปด้าน 3,4 ขยายหลังคา"   # ป้าย OCR พลาด 1 ตัว
    assert pick_name(["แสดงแบบ", "แปลนฐานราก", "ลนฐานราก", "มาคราล่วน 1:75"]) == "แปลนฐานราก"                            # ท่อนซ้ำ + ป้ายจบพัง
    assert pick_name(["แบบขยายหลังคา 4", "มาตราส่วน"]) is None                                                            # 'แบบขยาย...' ไม่ใช่ป้ายเริ่ม
    assert pick_name(["แสดงแบบ แปลนฐานราก", "มาตราส่วน"]) == "แปลนฐานราก"
    rs = [dict(found=True, code_pos=(0.9, 0.95)) for _ in range(4)] + [dict(found=True, code_pos=(0.5, 0.2)), dict(found=False)]
    flag_moved(rs)
    assert [r.get("flag") for r in rs] == [None] * 4 + ["titleblock_moved", "titleblock_not_found"]
    # บ้าน_เล็ก_1ชั้น_11 (ข้อความฝัง): แผ่นแบบ SN-01..SN-08 ที่มุมขวาล่าง + ใบ BOQ 10 หน้ามี 'SN-08' อ้างอิงอีกจุด
    # ค่ากลางต้องมาจากรหัสที่ไม่ซ้ำ -> ธงตกที่ใบ BOQ ไม่ใช่แผ่นแบบ (ก่อนแก้กลับด้าน: แผ่นแบบ 8 หน้าโดนธง moved)
    rs = [dict(found=True, sheet_code=f"SN-0{i}", code_pos=(0.872, 0.924)) for i in range(1, 9)] \
        + [dict(found=True, sheet_code="SN-08", code_pos=(0.923, 0.716)) for _ in range(10)]
    flag_moved(rs)
    assert [r.get("flag") for r in rs] == [None] * 8 + ["titleblock_moved"] * 10
    # กรอบย้ายจริง (บ้านครอบครัวไทยเป็นสุข2: หน้าสแกนตะแคง กรอบไปอยู่ขอบบน นอกแถบที่ค้น): OCR อ่านรหัสผิดจากในแบบได้ 2 หน้า
    # ไม่พอทำค่ากลาง แต่หน้าที่ไม่เจอต้องติดธงเสมอ (ก่อนแก้: ทั้งเล่มไม่มีธงเลย)
    rs = [dict(found=True, sheet_code="A-05", code_pos=(0.93, 0.64)), dict(found=True, sheet_code="U214", code_pos=(0.767, 0.873))] \
        + [dict(found=False) for _ in range(3)]
    flag_moved(rs)
    assert [r.get("flag") for r in rs] == [None, None] + ["titleblock_not_found"] * 3
    assert group_rows([(0.5, 0.01, 0.9, "B"), (0.5, 0.01, 0.8, "A"), (0.6, 0.01, 0.8, "C")]) == ["A B", "C"]
    assert name_sim("แปลนพื้นชึ้น 1", ["แปลนพื้นชั้น 1", "แปลนหลังคา"]) >= 0.9   # OCR พลาดสระ ยังนับว่าตรง
    assert name_sim("รูปด้าน", ["แปลนหลังคา"]) < 0.5
    print("OK — self-check ผ่าน (ตรรกะ regex/เลือกรหัส เท่านั้น ไม่ได้เทียบกับ PDF จริง ใช้ --eval)")


# ponytail: sheet_name ใช้ป้ายนำ ("แสดงแบบ"...) ไม่เรียนรู้เลย์เอาต์ต่อชุด — ชุดที่ไม่มีป้ายได้ "ไม่เจอ" แทนการเดา;
# ทางที่แม่นกว่าคือ join รหัสแผ่นกับสารบัญแบบของเล่มเดียวกัน (sections[].sheet_range/title ใน json เฉลยมีโครงนี้อยู่แล้ว)
# แต่ต้อง OCR หน้าสารบัญที่เป็นตาราง — ยังไม่ได้ทำ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("house", nargs="*", help="ชื่อบ้านเหมือนโฟลเดอร์ใน image/")
    ap.add_argument("--ocr", action="store_true", help="หน้าที่ข้อความฝังไม่เจอ -> OCR แถบขวา/ล่าง")
    ap.add_argument("--pages", help="เช่น 3-8 (นับจาก 1)")
    ap.add_argument("--out", help="เขียน JSON ลงไฟล์ (ค่าเริ่มต้นพิมพ์ stdout)")
    ap.add_argument("--name", action="store_true", help="อ่าน sheet_name ด้วย (OCR ไทย ~5-9 วิ/หน้า)")
    ap.add_argument("--eval", action="store_true", help="เทียบกับ sheet_code ใน json เฉลย (รวม --name = วัดชื่อแผ่น)")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not a.house:
        ap.print_help()
        return
    if a.eval:
        return evaluate_names(a.house) if a.name else evaluate(a.house, a.ocr)
    res = {h: run_house(h, a.ocr, a.pages, a.name) for h in a.house}
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
        print("เขียน", a.out)
    else:
        print(txt)


if __name__ == "__main__":
    main()
