#!/usr/bin/env python3
"""
tools/titleblock_ocr.py — OCR hint for pass 0 (page classification)

ไม่ได้แทน pass 0 ทั้งดุ้น — pass 0 ยังต้องเป็น VLM (Qwen) เหมือนเดิม เพราะครึ่งงานที่แพงที่สุด
ของ pass 0 คือ views[] (หน้านี้กี่รูป ตัดตรงไหน also_gridline ไหม) ซึ่งเป็นการตัดสิน layout
ไม่ใช่ text OCR อ่านให้ไม่ได้ (พิสูจน์แล้วจากการทดลอง 2026-08-29: OCR อ่าน sheet_code เองก็พัง
0/4 หน้าตอนแรก จนกว่าจะปรับ engine/crop)

สิ่งที่ไฟล์นี้ทำ: crop มุมกรอบชื่อแบบ (title block) แล้ว OCR เฉพาะ sheet_code/sheet_name เป็น
ข้อความ "คำใบ้" แปะเสริมเข้า pass0 prompt (โครงเดียวกับ cv_hint_text() ใน cv_scan.py ที่ช่วย
pass 2 แขน 2.4a) — โมเดลยังต้องอ่านภาพจริงเอง คำใบ้อาจผิด บอกไว้ตรงๆ ในข้อความ

engine: PaddleOCR PP-OCRv5 (lang=th) รันในเครื่อง ไม่ต้องมี API key — ทดลองแล้วแม่นกว่า
easyocr เยอะ (2026-08-29: อ่าน "สารบัญแบบ, สัญลักษณ์ประกอบแบบ" ตรงเป๊ะ, "A-02" ตรงเป๊ะ)

กับดักเรื่อง environment (เจอจริงบนเครื่องนี้ ไม่ใช่บั๊ก paddle):
- ~/.cache และ ~/.unsloth เป็น symlink ไปที่ path /tmp/... ที่ python บน Windows ตามไม่เจอ
  → ตั้ง PADDLE_PDX_CACHE_HOME ให้ชี้เข้า tools/.cache_local/ เอง ก่อน import paddleocr
- PP-OCRv5 CPU ชน bug oneDNN บนเครื่องนี้ (ConvertPirAttribute2RuntimeAttribute) → ต้องปิด
  enable_mkldnn=False เสมอ

    python tools/titleblock_ocr.py <ภาพ.png>          # 1 ไฟล์ → sidecar _titleblock_hint.txt
    python tools/titleblock_ocr.py --dir image/<บ้าน>/  # ทั้งโฟลเดอร์ (เฉพาะ _หน้าNN.png)
    python tools/titleblock_ocr.py --demo               # self-check ไม่ต้องมีรูปจริง
"""
import argparse
import os
import sys
from pathlib import Path

# ต้องตั้งก่อน import paddleocr/paddle เสมอ — ดู docstring ด้านบน
# os.path.expanduser('~') บน Windows อ่าน USERPROFILE ไม่ใช่ HOME — ต้องตั้งทั้งคู่
# ไม่ใช้ setdefault เพราะ USERPROFILE ของเครื่องนี้ตั้งไว้แล้วแต่ symlink พัง (ดู docstring)
_CACHE = Path(__file__).parent / ".cache_local"
_CACHE.mkdir(exist_ok=True)
os.environ["PADDLE_PDX_CACHE_HOME"] = str(_CACHE)
os.environ["HOME"] = str(_CACHE)
os.environ["USERPROFILE"] = str(_CACHE)

MIN_HINT_CHARS = 6  # ผลสั้นกว่านี้ = OCR ไม่เจออะไรจริง ไม่คุ้มแปะเข้า prompt

# crop เฉพาะกล่อง sheet_name/sheet_code — วัดจากภาพจริงบ้าน_ใหญ่_2ชั้น_02 หน้า 3 (2026-08-29)
# รอบแรกใช้ 0.80/0.70 (จากสัดส่วนหน้า PDF native ที่ต่างกับ PNG ที่ organize ไว้แล้ว) แล้วจับผิด
# กล่อง — ไปโดนกล่องลายเซ็นอธิบดี (ด้านบนกล่อง sheet_name) แทน ทำให้ hint ทุกหน้าเป็นชื่อคนซ้ำกัน
# ไม่ใช่ sheet_code/sheet_name เลย ค่านี้แคบกว่าและเลื่อนลงกว่าเดิมมาก — 90-100% ของกรอบชื่อแบบ
# ทั้งแถบคือแค่ริมขวาสุดจริง ไม่ใช่ 20% กว้างเหมือนที่คิดตอนแรก
# ตำแหน่งอาจต่างกันได้ตาม orientation/scale ของแต่ละหลัง เป็นค่าประมาณ ไม่ใช่ค่าตายตัว —
# ถ้า hint ว่างเยอะผิดปกติหรือขึ้นชื่อคนซ้ำๆ ให้สงสัยค่านี้ก่อน ไม่ใช่ตัว OCR
CROP_RIGHT_FRAC = 0.84
CROP_TOP_FRAC = 0.73
CROP_BOTTOM_FRAC = 0.98
# เป้าหมายด้านยาวสุดหลัง resize, ไม่ใช่ upscale คูณตรงๆ — รูปต้นฉบับในคลังนี้ขนาดต่างกันมาก
# (พบ 2339x1654 ถึง 6498x4595) คูณคงที่เคยทำให้ crop ใหญ่เกิน max_side_limit ของ PP-OCRv5 (4000px)
# แล้ว resize ภายในของ paddle เจอ native crash (segfault) บนเครื่องนี้ — ต้องคุมขนาดเอง
TARGET_LONG_SIDE = 1600


def crop_titleblock(img):
    """img: PIL.Image หน้าเต็ม -> PIL.Image ครอปมุมกรอบชื่อแบบ ขยาย+ปรับ contrast แล้ว"""
    from PIL import ImageOps, ImageEnhance

    W, H = img.size
    box = (int(W * CROP_RIGHT_FRAC), int(H * CROP_TOP_FRAC), W, int(H * CROP_BOTTOM_FRAC))
    crop = img.crop(box)
    scale = TARGET_LONG_SIDE / max(crop.width, crop.height)
    crop = crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))))
    crop = crop.convert("L")
    crop = ImageOps.autocontrast(crop, cutoff=1)
    crop = ImageEnhance.Sharpness(crop).enhance(2.0)
    return crop


_READER = None


def get_reader():
    global _READER
    if _READER is None:
        from paddleocr import PaddleOCR

        _READER = PaddleOCR(
            lang="th",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,  # ดูกับดักใน docstring — ห้ามลบบรรทัดนี้
        )
    return _READER


def ocr_titleblock(image_path):
    """คืน (hint_text, raw_lines) — hint_text ว่างถ้า OCR ไม่เจออะไรจริงจัง"""
    from PIL import Image

    img = Image.open(image_path)
    crop = crop_titleblock(img)
    # เขียนไฟล์ชั่วคราวใน _CACHE ไม่ใช่ข้างไฟล์ต้นฉบับ — เคยเขียนข้างไฟล์ต้นฉบับแล้วโดน crash
    # (segfault ของ paddle บนรูปใหญ่เกิน ก่อนแก้ TARGET_LONG_SIDE) กลาง finally ไม่ทันลบ
    # ทิ้งไฟล์ .titleblock_tmp.png ค้างไว้ให้ --dir กวาดเจอเป็น "หน้า" ปลอมในรอบถัดไป
    tmp = str(_CACHE / f"_tmp_{os.getpid()}.png")
    crop.save(tmp)
    try:
        result = get_reader().predict(tmp)
        lines = []
        for r in result:
            lines.extend(r.get("rec_texts", []) if isinstance(r, dict) else [])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    text = " / ".join(l.strip() for l in lines if l.strip())
    if len(text) < MIN_HINT_CHARS:
        return "", lines

    hint = (
        "OCR อ่านมุมกรอบชื่อแบบได้ (อาจผิด ยืนยันกับภาพจริงก่อนใช้ โดยเฉพาะ sheet_code/sheet_name) "
        + text
    )
    return hint, lines


def write_hint(image_path):
    hint, lines = ocr_titleblock(image_path)
    stem = Path(image_path).stem
    out = Path(image_path).parent / f"{stem}_titleblock_hint.txt"
    if hint:
        out.write_text(hint, encoding="utf-8")
        return out
    if out.exists():
        out.unlink()  # ผลรอบนี้ว่าง แต่มีไฟล์เก่าค้าง — ลบทิ้ง อย่าปล่อยคำใบ้ผิดยุคค้างไว้
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", help="ไฟล์ภาพ 1 หน้า")
    ap.add_argument("--dir", help="โฟลเดอร์ที่มี <บ้าน>_หน้าNN.png หลายไฟล์")
    ap.add_argument("--demo", action="store_true", help="self-check ไม่ต้องมีรูปจริง")
    args = ap.parse_args()

    if args.demo:
        from PIL import Image, ImageDraw

        demo_path = _CACHE / "_demo_page.png"
        img = Image.new("RGB", (2339, 1654), "white")
        d = ImageDraw.Draw(img)
        # จำลองกรอบชื่อแบบมุมขวาล่าง ตัวหนังสือใหญ่พอให้ OCR อ่านได้จริง
        d.rectangle([2000, 1230, 2330, 1600], outline="black", width=3)
        d.text((2030, 1450), "A-09", fill="black")
        img.save(demo_path)
        hint, lines = ocr_titleblock(demo_path)
        print("demo lines:", lines)
        assert isinstance(hint, str), "hint ต้องเป็น str เสมอ"
        print("OK — self-check ผ่าน (เห็นบรรทัดจาก OCR จริง ไม่ได้เช็คความแม่นตรงนี้)")
        return

    if args.dir:
        pages = sorted(
            p for p in Path(args.dir).glob("*.png")
            if "_marked" not in p.stem
            and "_titleblock_hint" not in p.stem
            and "_tmp" not in p.stem
        )
        if not pages:
            print(f"ไม่พบรูปใต้ {args.dir}")
            return
        n_hint = 0
        for p in pages:
            out = write_hint(p)
            print(f"  {p.name:40s} {'-> ' + out.name if out else '(ไม่มี hint)'}")
            if out:
                n_hint += 1
        print(f"รวม {len(pages)} หน้า, ได้ hint {n_hint} หน้า")
        return

    if args.image:
        out = write_hint(args.image)
        print(out if out else "(ไม่มี hint — OCR ไม่เจออะไรจริงจัง)")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
