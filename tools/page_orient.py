"""Pass 0 — ทิศหน้ากระดาษ (แนวตั้ง/แนวนอน/หน้าตะแคง) ก่อนส่งให้ส่วน 1-3

ปัญหา (sticky note ของ King บนแผนภาพ Pass 0: "ยังขาด logic แปลงแบบ เช่น แนวตั้ง แนวนอน"):
  สำรวจทั้งคลัง 175 เล่ม 6,267 หน้า (page.rect = ขนาดที่ตามองเห็นแล้ว):
    - /Rotate 90/270/180 = 3,507 หน้า — ผู้ชมหมุนให้เอง ตัวตรวจกริด/กรอบชื่อแบบคูณ rotation_matrix อยู่แล้ว (ไม่ต้องทำอะไร)
    - หน้าที่ตามองเห็นเป็นแนวตั้ง = 26 หน้า ใน 2 เล่ม (บ้านครอบครัวไทยเป็นสุข2 18, บ้าน_ใหญ่_3ชั้น_06 8)
      ดูภาพแล้ว = แบบแนวนอนที่สแกนมาตะแคง (ไม่ใช่แบบแนวตั้งจริง) -> OCR/ตัวตรวจกรอบชื่อแบบอ่านไม่ได้ทั้งที่แบบดีมาก
    - หน้าเวกเตอร์ที่ข้อความฝังตะแคงตามที่ตามองเห็น = 953 หน้า ใน 35 เล่ม (ทุกหน้าต้องหมุนตามเข็ม 3 ครั้ง ไม่มีทิศอื่นปน)
      ตรวจ 70 หน้าที่เส้นเยอะด้วยตัวตรวจวงหัวกริดของส่วน 3: 0 หน้ามีวงหัวกริด = แบบฟอร์มเอกสาร (ตาราง BOQ) ไม่กระทบส่วน 3
    - หน้าสแกนแนวนอนที่เนื้อหาตะแคงข้างใน: ไม่มีวิธีที่ตัดสินได้ (ดู "ที่วัดแล้วใช้ไม่ได้") — ยังไม่ตรวจ ไม่แกล้งบอกว่าตรวจ

วิธี:
  1. orientation_info(page): rotation, ขนาด, แนวที่ตามองเห็น (ตรง ๆ จาก PDF ไม่ต้อง OCR)
  2. หน้ามีข้อความฝัง: text_turns(page) = ทิศที่ข้อความส่วนใหญ่วิ่ง (คูณ rotation_matrix)
  3. หน้าสแกนที่ตามองเห็นเป็นแนวตั้ง: upright_turns(img) — OCR ไทยลองหมุน 3 ทิศ (0, 2, แล้ว 1) นับพยัญชนะไทยของคำที่มั่นใจ
     หลัก: PaddleOCR หมุนครอปบรรทัดที่สูงกว่ากว้างมาก 90° ก่อนอ่านเอง -> ข้อความตะแคงด้านหนึ่งอ่านออก อีกด้านอ่านไม่ออกเลย
     ดังนั้นคะแนนต่อทิศมีรูป "คู่ติดกันแรง อีกคู่ ~0" เสมอ: ถ้าหน้าต้องหมุนตามเข็ม u ครั้ง ทิศ u และ u+1 แรง
     (วัดจริง: หน้า 5 = [0,204,134,0] · หน้า 10 = [0,838,642,0] ความจริง u=1 ทั้งคู่) ตัดสินจากคู่ ไม่ใช่จากทิศที่ชนะกี่เท่า
     (ทิศ u+1 ได้ 134-642 ใกล้ทิศ u มาก เกณฑ์ "ชนะ k เท่า" ใช้ไม่ได้) — ไม่แน่ชัดตอบ None (ไม่เดา)
  turns = จำนวนครั้ง 90° ตามเข็มนาฬิกาที่ต้องหมุนภาพที่ตามองเห็น ให้ตัวหนังสืออ่านตั้งตรง (0 = ตั้งอยู่แล้ว)

ที่วัดแล้วใช้ไม่ได้ (อย่าเอากลับมา):
  - ตัวจำแนกทิศสำเร็จรูป PP-LCNet_x1_0_doc_ori: หน้า 10 ตอบ "270" ที่ 0.91 ความจริงคือ 1 ครั้ง (กลับหัว) และกับ 16 หน้าแนวนอน
    ที่มันมั่นใจ >= 0.9 ว่าตะแคง 15 หน้าตั้งตรงอยู่แล้ว (ตรวจด้วยตา) -> ผิด ~94% ใช้หมุนอัตโนมัติไม่ได้
  - นับ "ตัวอักษรมั่นใจ" รวมตัวเลข/ละติน: ตัวเลขอ่านกลับหัวก็ยังได้คะแนน ทั้ง 4 ทิศได้ 140-240 ใกล้กันหมด

ผลที่วัดได้ (21 พ.ย. 2569) บนทั้ง 26 หน้าแนวตั้ง: ตัดสินได้ 25 หน้า ทุกหน้า = หมุนตามเข็ม 1 ครั้ง · None 1 หน้า (เป็นสุข2 หน้า 1 = ภาพแบนเนอร์ปก ไม่มีไทยพอ ถูกแล้ว)
  - 8 หน้าของ 3ชั้น_06 (แผ่น 6,249x11,731 px): ที่ 1,400 px ตัดสินได้ 4 หน้า อีก 4 หน้าตัวไทยน้อยกว่า MIN_LETTERS -> ลองซ้ำที่ 2,800 px (how=ocr_pair_2x) ได้ครบ
    (หน้า 6 เฉียดขอบ: ทิศ 0 ได้ 20 เทียบ 112 ขอบ WEAK = 22.4)
  - ตรวจด้วยตา (หมุนแล้วดูภาพ) เพียง 3 หน้า: เป็นสุข2 หน้า 5 (หมุน 1 ตั้งตรง), หน้า 10 (หมุน 3 = กลับหัว -> ความจริง 1), 3ชั้น_06 หน้า 1 (หมุน 1 ตั้งตรง)
    อีก 22 หน้ามีแค่ความสอดคล้อง (ทุกหน้าได้ 1) เป็นหลักฐาน ไม่ได้ดูทีละหน้า
  - ผลต่อกรอบชื่อแบบ (เป็นสุข2 หน้า 5): ก่อนหมุนอ่านรหัสได้ "A-05" ซึ่งผิด (มาจากสัญลักษณ์อ้างอิงแปลนในวงกลม) ไม่มีชื่อแผ่น
    หลังหมุน = "A-04" (ถูก) + ชื่อ "แปลนพื้น, แปลนหลังคา" (ถูก) — วัดหน้าเดียว
ข้อจำกัด: ต้องมีพยัญชนะไทยพอ (MIN_LETTERS) — แบบอังกฤษล้วนจะตอบ None · เวลา ~25-60 วินาที/รอบ OCR (3 รอบ/หน้า, CPU; แผ่นใหญ่ + ลองซ้ำ 75-190 วินาที/หน้า)
ไม่ได้ตรวจ: หน้าสแกนแนวนอนที่เนื้อหาตะแคงข้างใน (เช่น 1ชั้น_05 หน้า 17 แผ่นข้อความ) และหน้าสแกนตะแคงที่ตามองเห็นเป็นแนวนอน — ไม่มีวิธีที่วัดแล้วว่าใช้ได้

ใช้ที่: run_part1_part3.py (แต่ละหน้า: ข้อมูลทิศ + หน้าสแกนแนวตั้งหมุนให้ตั้งก่อนอ่านกรอบชื่อแบบ + --png บันทึกภาพที่ตั้งแล้ว)
CLI: python tools/page_orient.py --demo | --scan บ้านครอบครัวไทยเป็นสุข2 [หน้า,หน้า...] | --survey
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

MAX_PX = 1400            # ด้านยาวของภาพที่ส่ง OCR (ย่อ: ทิศตัดสินได้ไม่ต้องละเอียด)
MIN_CONF = 0.7           # คำที่ OCR มั่นใจกว่านี้ถึงนับ
MIN_LETTERS = 40         # พยัญชนะไทยอย่างน้อยเท่านี้ในทิศที่แรงสุด ไม่งั้นถือว่าข้อความน้อยไป (เลือกเอง วัด 2 หน้า = 134-838)
WEAK = 0.2               # ทิศที่ได้ <= 0.2 ของทิศแรงสุดถือว่า "อ่านไม่ออก" (วัดจริง: ทิศอ่านไม่ออก = 0 พอดี)
TEXT_MIN_SPANS = 8       # ข้อความฝังน้อยกว่านี้ = ไม่ตัดสินจากข้อความฝัง
_THAI = re.compile(r"[ก-ฮ]")


def orientation_info(page):
    """ข้อมูลทิศจาก PDF ตรง ๆ (ไม่ OCR) — page.rect เป็นขนาดที่ตามองเห็นแล้ว"""
    r = page.rect
    return dict(rotation=page.rotation, width_pt=round(r.width, 1), height_pt=round(r.height, 1),
                orientation="landscape" if r.width >= r.height else "portrait")


def turns_from_dir(dx, dy):
    """ทิศที่ข้อความวิ่ง (ตามที่ตามองเห็น, y ลง) -> กี่ครั้งตามเข็มที่ต้องหมุนให้เป็น (1,0)
    (1,0) ตั้งอยู่ = 0 · (0,-1) วิ่งขึ้น (หัวตัวอักษรชี้ซ้าย) = 1 · (-1,0) กลับหัว = 2 · (0,1) วิ่งลง (หัวชี้ขวา) = 3"""
    ang = math.degrees(math.atan2(dy, dx)) % 360        # (1,0)=0, (0,1)=90, (-1,0)=180, (0,-1)=270
    return int(round(((-ang) % 360) / 90.0)) % 4


def text_turns(page):
    """หน้ามีข้อความฝัง: ทิศส่วนใหญ่ของบรรทัด (ถ่วงด้วยจำนวนตัวอักษร) -> turns หรือ None (ข้อความน้อย/ทิศปนกัน)"""
    rm = page.rotation_matrix
    votes = [0, 0, 0, 0]
    n = 0
    for b in page.get_text("dict").get("blocks", []):
        for ln in b.get("lines", []):
            nch = sum(len(s.get("text", "").strip()) for s in ln.get("spans", []))
            if nch < 2:
                continue
            dx, dy = ln["dir"]
            # เวกเตอร์ทิศ -> พิกัดที่ตามองเห็น (แค่ส่วนหมุน ไม่เอาการเลื่อน)
            vx, vy = dx * rm.a + dy * rm.c, dx * rm.b + dy * rm.d
            votes[turns_from_dir(vx, vy)] += nch
            n += 1
    if n < TEXT_MIN_SPANS:
        return None
    top = max(range(4), key=lambda k: votes[k])
    if votes[top] < 0.7 * sum(votes):
        return None
    return top


def pick_turns(s0, s2, s1_fn):
    """ตัดสินทิศจากคะแนนพยัญชนะไทยของทิศ 0, 2 (ส่งมาเป็นตัวเลข) และทิศ 1 (เรียกเมื่อจำเป็น) — pure, ไม่แตะ OCR
    ถ้าหน้าต้องหมุน u ครั้ง ทิศ u และ u+1 แรง ส่วน u+2, u+3 อ่านไม่ออก (~0) ทิศ 0 กับ 2 ไม่มีวันอยู่ในคู่ "อ่านไม่ออก" พร้อมกัน
    -> ทิศ 0 แรง/2 อ่านไม่ออก: u ∈ {0, 3} · ทิศ 0 อ่านไม่ออก/2 แรง: u ∈ {1, 2} · แล้วทิศ 1 ชี้ขาด"""
    m = max(s0, s2)
    if m < MIN_LETTERS:
        return None
    weak0, weak2 = s0 <= WEAK * m, s2 <= WEAK * m
    if weak0 == weak2:            # แรงทั้งคู่ (ข้อความสองทิศปนกัน) หรืออ่อนทั้งคู่ — ไม่ใช่รูปคู่ติดกัน ไม่เดา
        return None
    s1 = s1_fn()
    weak1 = s1 <= WEAK * max(m, s1)
    if weak2:                     # ทิศ 0 แรง: u=0 -> แรง {0,1} · u=3 -> แรง {3,0}
        return 3 if weak1 else 0
    return 2 if weak1 else 1      # ทิศ 2 แรง: u=2 -> แรง {2,3} · u=1 -> แรง {1,2}


def thai_letters(res):
    """จำนวนพยัญชนะไทยของคำที่ OCR มั่นใจ >= MIN_CONF (ไม่นับตัวเลข/ละติน: อ่านกลับหัวก็ยังได้คะแนน)"""
    return sum(len(_THAI.findall(txt)) for r in res
               for txt, conf in zip(r.get("rec_texts", []), r.get("rec_scores", [])) if conf >= MIN_CONF)


def upright_turns(img, reader=None, max_px=MAX_PX):
    """img = numpy RGB ของหน้าที่ตามองเห็น -> (turns หรือ None, {ทิศ: คะแนน} ที่วัดจริง) — OCR สูงสุด 3 รอบ"""
    import numpy as np
    if reader is None:
        import titleblock_extract as T
        reader = T._reader_th()
    h, w = img.shape[:2]
    if max(h, w) > max_px:                               # ย่อด้วยการเว้นพิกเซล (ไม่ต้องพึ่ง cv2/PIL)
        step = int(math.ceil(max(h, w) / max_px))
        img = img[::step, ::step]
    scores = {}

    def score(t):
        # np.rot90(k) หมุนทวนเข็ม k ครั้ง -> หมุนตามเข็ม t ครั้ง = rot90(-t)
        if t not in scores:
            scores[t] = thai_letters(reader.predict(np.ascontiguousarray(np.rot90(img, -t))))
        return scores[t]

    return pick_turns(score(0), score(2), lambda: score(1)), scores


def page_img(page, dpi=100):
    """ภาพ numpy RGB ของหน้าตามที่ตามองเห็น"""
    import numpy as np
    pix = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    if pix.n == 1:
        img = np.repeat(img, 3, axis=2)
    return np.ascontiguousarray(img)


def decide(page, has_text_layer, reader=None, allow_ocr=True):
    """รวมวิธี -> dict(turns, how, checked, [scores]) — turns None = ตรวจแล้วแต่ไม่แน่ใจ (ปล่อยไว้ตามเดิม + ติดธง)
    checked=False = ไม่ได้ตรวจ (หน้าสแกนแนวนอน: ไม่มีวิธีที่วัดแล้วว่าใช้ได้ · หรือ allow_ocr=False) turns=0 ตามเดิม"""
    if has_text_layer:
        t = text_turns(page)
        if t is not None:
            return dict(turns=t, how="text_layer", checked=True)
    r = page.rect
    if r.width < r.height and not allow_ocr:
        return dict(turns=0, how="skipped_no_ocr", checked=False)
    if r.width < r.height:        # หน้าสแกนที่ตามองเห็นเป็นแนวตั้ง = แบบแนวนอนที่สแกนมาตะแคง (26/26 ในคลัง)
        dpi = max(20, int(MAX_PX / (max(r.width, r.height) / 72)))
        t, scores = upright_turns(page_img(page, dpi), reader)
        if t is None and max(scores.get(0, 0), scores.get(2, 0)) < MIN_LETTERS:
            # ตัวไทยเล็กเกินไปเมื่อย่อ (แผ่นสแกนใหญ่ เช่น 3ชั้น_06 6,249x11,731 px ย่อเหลือ 1,400 ได้ 3-36 ตัว) -> ลองอีกครั้งที่สองเท่า
            t, scores = upright_turns(page_img(page, dpi * 2), reader, max_px=2 * MAX_PX)
            return dict(turns=t, how="ocr_pair_2x", checked=True, scores=scores)
        return dict(turns=t, how="ocr_pair", checked=True, scores=scores)
    return dict(turns=0, how="not_checked", checked=False)


def save_upright_png(page, turns, path, dpi=200):
    """บันทึก PNG ของหน้าที่หมุนตั้งตรงแล้ว (turns ตามเข็ม)"""
    import numpy as np
    from PIL import Image
    Image.fromarray(np.ascontiguousarray(np.rot90(page_img(page, dpi), -(turns or 0)))).save(str(path))


# ---------- demo / ตรวจ ----------
def _demo():
    # ทิศข้อความ: (1,0) ตั้ง · (0,-1) วิ่งขึ้น · (-1,0) กลับหัว · (0,1) วิ่งลง
    assert turns_from_dir(1, 0) == 0
    assert turns_from_dir(0, -1) == 1, turns_from_dir(0, -1)
    assert turns_from_dir(-1, 0) == 2
    assert turns_from_dir(0, 1) == 3
    assert turns_from_dir(0.99, -0.05) == 0           # เอียงนิดเดียว = ยังตั้ง
    # ตัดสินจากคู่ — ตัวเลขจริงที่วัดได้ (เป็นสุข2 หน้า 5 และ 10, ความจริง u=1 ตรวจด้วยตา)
    assert pick_turns(0, 134, lambda: 204) == 1
    assert pick_turns(0, 642, lambda: 838) == 1
    # รูปแบบของทุก u ที่สร้างตามหลัก "u, u+1 แรง ที่เหลือ 0" ต้องได้ u กลับมา
    for u in range(4):
        s = [900 if t in (u, (u + 1) % 4) else 0 for t in range(4)]
        assert pick_turns(s[0], s[2], lambda: s[1]) == u, (u, s)
    # ไม่เดา: ข้อความน้อย / แรงทั้งสองทิศ (ปนกัน) / อ่านไม่ออกทั้งสองทิศ
    assert pick_turns(5, 12, lambda: 900) is None
    assert pick_turns(500, 480, lambda: 10) is None
    assert pick_turns(0, 0, lambda: 900) is None
    # ทิศ 1 ถูกเรียกเฉพาะเมื่อจำเป็น (ข้อมูลไม่ครบรูปคู่ = ไม่ต้องเสีย OCR รอบที่ 3)
    called = []
    pick_turns(500, 480, lambda: called.append(1) or 0)
    assert not called
    # พยัญชนะไทย: ไม่นับเลข/ละติน และต่ำกว่า MIN_CONF
    assert thai_letters([dict(rec_texts=["แปลน 3.50 ABC", "กขค"], rec_scores=[0.9, 0.5])]) == 3     # ป ล น (แ เป็นสระ)
    # ข้อความฝังจริงใน PDF ที่สร้างเอง: เขียนตะแคง 4 แบบ -> ต้องได้ turns ที่ถูก
    # insert_text(rotate=r) หมุนข้อความทวนเข็ม r องศา: 90 = วิ่งขึ้น (ต้องหมุนตามเข็ม 1 ครั้ง) · 180 = กลับหัว (2) · 270 = วิ่งลง (3)
    import fitz
    for rot, want in ((0, 0), (90, 1), (180, 2), (270, 3)):
        doc = fitz.open()
        pg = doc.new_page(width=842, height=595)
        for i in range(12):
            x, y = {0: (50, 60 + 30 * i), 90: (100 + 30 * i, 500), 180: (700, 60 + 30 * i), 270: (100 + 30 * i, 100)}[rot]
            pg.insert_text((x, y), f"hello grid line {i}", fontsize=14, rotate=rot)
        got = text_turns(pg)
        assert got == want, (rot, got, want)
    # หน้าที่มี /Rotate: ข้อความที่ผู้ชมเห็นตั้งอยู่แล้วต้องได้ 0 (คูณ rotation_matrix แล้ว)
    doc = fitz.open()
    pg = doc.new_page(width=842, height=595)
    for i in range(12):
        pg.insert_text((50, 60 + 30 * i), f"hello grid line {i}", fontsize=14)
    pg.set_rotation(90)                               # ผู้ชมเห็นข้อความหมุน 90 ตามเข็ม -> ต้องหมุนกลับ 3
    assert text_turns(pg) == 3, text_turns(pg)
    # ข้อความน้อย = ไม่ตัดสิน
    doc = fitz.open()
    pg = doc.new_page()
    pg.insert_text((50, 60), "one line", fontsize=14)
    assert text_turns(pg) is None
    # ทิศปน: แผ่นแบบมีตัวเลขบอกระยะแนวตั้งปนอยู่เสมอ -> ส่วนน้อยต้องไม่ล้มทิศหลัก (3 บรรทัดตะแคงต่อ 12 บรรทัดตั้ง = ยังตั้ง)
    # แต่ครึ่งต่อครึ่ง (ไม่มีทิศไหนถึง 70%) ต้องตอบ None ไม่ใช่เดา
    for n_side, want in ((3, 0), (12, None)):
        doc = fitz.open()
        pg = doc.new_page(width=842, height=595)
        for i in range(12):
            pg.insert_text((50, 60 + 30 * i), f"hello grid line {i}", fontsize=14)
        for i in range(n_side):
            pg.insert_text((600 + 30 * i, 500), f"hello grid line {i}", fontsize=14, rotate=90)
        assert text_turns(pg) == want, (n_side, text_turns(pg), want)
    # decide: หน้าแนวนอนไม่มีข้อความฝัง = ไม่ตรวจ (ไม่แกล้งตรวจ) · หน้าแนวตั้งต้องเข้าทาง OCR (ใส่ reader ปลอมที่คืนทิศ 1 แรง)
    doc = fitz.open()
    land = doc.new_page(width=842, height=595)
    assert decide(land, False) == dict(turns=0, how="not_checked", checked=False)

    class FakeReader:                                  # คืนพยัญชนะไทยเฉพาะตอนภาพถูกหมุนตามเข็ม 1 หรือ 2 ครั้ง (u=1)
        def __init__(self):
            self.calls = 0

        def predict(self, im):
            self.calls += 1
            return [dict(rec_texts=["ก" * 100], rec_scores=[0.9])] if self.calls in (2, 3) else [dict(rec_texts=["x"], rec_scores=[0.9])]
    port = doc.new_page(width=612, height=792)
    fr = FakeReader()
    got = decide(port, False, fr)
    # ลำดับเรียก: ทิศ 0 (call1: ไม่มีไทย) -> ทิศ 2 (call2: แรง) -> ทิศ 1 (call3: แรง) => u=1, OCR 3 รอบพอดี
    assert got["turns"] == 1 and got["how"] == "ocr_pair" and fr.calls == 3, (got, fr.calls)

    class SmallTextReader:                             # ย่อแล้วตัวไทยน้อย (10 ตัว < MIN_LETTERS) · สองเท่าแล้วอ่านออก (u=1)
        def __init__(self):
            self.calls = 0

        def predict(self, im):
            self.calls += 1
            n = {2: 10, 4: 100, 5: 100}.get(self.calls, 0)       # รอบแรก: call1=ทิศ0, call2=ทิศ2 -> None · รอบสอง: call3=ทิศ0, call4=ทิศ2, call5=ทิศ1
            return [dict(rec_texts=["ก" * n], rec_scores=[0.9])]
    sr = SmallTextReader()
    got = decide(port, False, sr)
    assert got["turns"] == 1 and got["how"] == "ocr_pair_2x" and sr.calls == 5, (got, sr.calls)
    print("page_orient demo ok")


def _scan(house, pages=None):
    import fitz
    import titleblock_extract as T
    doc = fitz.open(T.pdf_of(house))
    for i in (pages or range(1, len(doc) + 1)):
        pg = doc[i - 1]
        d = decide(pg, len(pg.get_text("words")) >= 30)
        print(house, i, orientation_info(pg)["orientation"], d, flush=True)


def _survey():
    """หน้าเวกเตอร์ที่มีข้อความฝังทั้งคลัง: มีหน้าไหนที่ข้อความตะแคง/กลับหัวตามที่ตามองเห็นไหม (เร็ว ไม่ OCR)"""
    import collections
    import fitz
    import titleblock_extract as T
    c = collections.Counter()
    off = []
    for d in sorted(T.IMAGE_DIR.iterdir()):
        p = d / f"{d.name}.pdf"
        if not p.exists():
            continue
        for i, pg in enumerate(fitz.open(p)):
            t = text_turns(pg)
            c["none" if t is None else t] += 1
            if t not in (None, 0):
                off.append((d.name, i + 1, t))
                print("OFF", d.name, i + 1, t, flush=True)
        print("done", d.name, dict(c), flush=True)
    print("TOTAL", dict(c), "off-pages", len(off))


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--demo" in a:
        _demo()
    elif "--survey" in a:
        _survey()
    elif "--scan" in a:
        i = a.index("--scan")
        _scan(a[i + 1], [int(x) for x in a[i + 2].split(",")] if len(a) > i + 2 else None)
    else:
        print(__doc__)
