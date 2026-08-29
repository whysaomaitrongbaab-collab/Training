# Pass 0 — คัดหน้า

ของจริงอยู่ที่นี่: [`prompt.md`](prompt.md) (`output_example.json` ข้างกัน) — ย้ายมาจาก
`tune_ai/t03/pass0_classify/` 2026-08-29 ไม่ใช่แค่แนวนอนแล้ว t03 ไม่ใช่บ้านของสายพานนี้อีกต่อไป
(`pass3_takeoff/` ย้ายไปแล้วเมื่อ 2026-08-28, `pass2/plan.md` ย้ายพร้อมกันวันนี้)

**สถานะ: ไม่มี runner** — ทำมือหรือให้ Claude ป้อน prompt + รูปทีละหน้าไปก่อน
**ถ้า/เมื่อเขียน runner: ต้องเปิด xgrammar (builtin JSON) เสมอ** (มะขามสั่ง 2026-08-29
"ใส่ xgrammar ทุก pass") — pass นี้เป็นด่านอันตรายสุดของสายพาน หน้าที่ JSON พังจน parse
ไม่ได้ = หน้านั้นหลุดจากการ route ทั้งใบ ดูวิธี setup ที่ `infer_house_t03.py::setup_grammar()`

**ตัวเลือกเสริม (ไม่บังคับ):** `tools/titleblock_ocr.py --dir image/<house>/` ก่อนเรียก VLM
ช่วยอ่าน sheet_code/sheet_name เป็นคำใบ้ (`{{TITLEBLOCK_OCR}}` ใน prompt.md) — ไม่ช่วย `views[]`
