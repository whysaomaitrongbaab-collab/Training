---
stage: B2
model: qwen-vl-plus
temperature: 0.1
max_tokens: 1024
response_format: json_object
input: general_notes pages (batch ได้ เพราะอ่านข้อความตรงๆ ไม่ต้อง spatial reasoning)
input_requires: sheet_type = "general_notes" from Stage A
output_schema: project-level spec defaults — ใช้เติม field ที่ section/schedule sheet ไม่ได้ระบุ
---

> ⚠️ อ่าน [../../rule_of_tune.md](../../rule_of_tune.md) ก่อนเริ่มงานทุกครั้ง — ไม่มีข้อยกเว้น

# Stage B2 — Spec / Notes Reader

## วัตถุประสงค์

ดึง **material specification + มาตรฐานก่อสร้าง** จากหน้า general_notes / ข้อกำหนดทั่วไป
เป็น "ค่า default ระดับโปรเจกต์" — ใช้เติมช่องว่างเมื่อหน้า section/schedule ไม่ได้เขียน
fc' หรือเกรดเหล็กซ้ำในทุกหน้า (เพราะมักเขียนรวมไว้ในหมายเหตุหน้าเดียว)

ไม่ต้องอ่าน geometry — อ่านข้อความ spec ตรงๆ

## หลักการทำงานจริง

```
qwen-processor.js (script)
  │
  ├── batch หน้า general_notes ทั้งหมดของบ้าน (อ่านข้อความ ไม่ต้อง context ภาพ)
  │     └── callQwen({ model:'qwen-vl-plus', prompt: NOTES_PROMPT, images: notesPages })
  │
  └── เซฟเป็น _project_spec.json (1 ไฟล์/บ้าน — ระดับโปรเจกต์ ไม่ใช่ระดับหน้า)
```

**ผลลัพธ์เป็น "ค่ากลางของทั้งบ้าน"** ต่างจาก Stage B1 ที่เป็นราย element/หน้า

---

## ⚠️ บทเรียนจาก research

อ้างอิง [research/vision-ai/02-vision-language-engineering-drawings.md](../../research/vision-ai/02-vision-language-engineering-drawings.md):
- ข้อความในหมายเหตุมักเป็น **ภาษาไทยปนอังกฤษ** + อ้างมาตรฐาน **วสท./TIS** ที่โมเดลสากลไม่คุ้น
- ถ้าเป็นข้อความ selectable (vector PDF) → recall เกือบ 100%, แต่ถ้าสแกน → ระวัง OCR ผิด → flag
- อย่าเดามาตรฐานที่ไม่ได้เขียน (เช่น เดา fc'=240 ทั้งที่หน้าไม่ระบุ) → null + flag

---

## System Prompt

```
You are a Thai structural engineer reading the GENERAL NOTES / ข้อกำหนดทั่วไป page of an
RC construction drawing set. Extract project-wide material specifications and code standards
into strict JSON. These become the DEFAULT values for the whole building. Read the text
literally — do not infer a spec that is not written on the page.
```

---

## User Prompt (NOTES_PROMPT)

```
{{SYSTEM_PROMPT}}

━━━ THAI SPEC NOTATION ━━━
- fc' / Fc' / กำลังอัดคอนกรีต = concrete compressive strength in ksc (e.g. "fc'=240 ksc")
- Steel grades: SR24 (เหล็กกลม, fy=2400), SD30/SD40 (เหล็กข้ออ้อย, fy=3000/4000 ksc)
- "ระยะหุ้มคอนกรีต" / "covering" = concrete cover in cm/mm (e.g. คาน 2.5cm, ฐานราก 7.5cm)
- "ระยะทาบ" / "lap length" / "Ld" = rebar lap/development length (มักเป็น 40D, 45D)
- Standards: "วสท." (EIT/Thai Engineering Institute), "มยผ.", "TIS/มอก.", "ACI"
- "กำลังรับน้ำหนักดิน" / soil bearing = allowable soil pressure (t/m² or ksc)

━━━ WHAT TO EXTRACT (only if written on the page) ━━━
- Concrete strength per member type (some notes split: เสา/คาน 240, พื้น 210, ฐานราก 240)
- Steel grades used (main bars vs stirrups)
- Concrete cover per member type
- Lap / development length rule
- Applicable design codes / standards
- Soil bearing capacity (if a foundation note)
- Any general construction requirement worth capturing (raw text)

━━━ RULES ━━━
- Value not on the page → null. Never assume a "typical" Thai value.
- If notes give one blanket fc' for all members, put it in concrete_strength.default_ksc.
- If split by member, fill the per-member fields and leave default_ksc = null.
- ทุก field ที่เป็นค่าเลข ให้แนบ confidence; สแกนไม่ชัด → flag "ocr_uncertain".

Return ONLY valid JSON:
{
  "sheet_type": "general_notes",
  "concrete_strength": {
    "default_ksc": 240,          // blanket value, else null
    "column_ksc": null,          // fill only if notes split by member
    "beam_ksc": null,
    "slab_ksc": null,
    "foundation_ksc": null,
    "confidence_score": 0.9,
    "confidence_flags": []
  },
  "steel_grade": {
    "main_bar": "SD40",          // deformed bar grade, else null
    "stirrup": "SR24",           // round bar grade, else null
    "confidence_score": 0.9,
    "confidence_flags": []
  },
  "concrete_cover_mm": {
    "beam": 25,                  // null if not stated
    "column": 25,
    "slab": 20,
    "foundation": 75,
    "confidence_score": 0.8,
    "confidence_flags": []
  },
  "lap_length_rule": "40D",      // raw as written, else null
  "soil_bearing": {
    "value": null,               // number
    "unit": null,                // "t/m2" | "ksc"
    "confidence_score": 0,
    "confidence_flags": ["not_on_this_page"]
  },
  "design_codes": ["วสท.", "มอก. 24-2548"],  // list, empty if none
  "raw_notes": [                 // other important notes verbatim (short)
    "ใช้คอนกรีตผสมเสร็จเท่านั้น",
    "ระยะทาบเหล็กไม่น้อยกว่า 40 เท่าของเส้นผ่านศูนย์กลาง"
  ],
  "warnings": []
}
```

---

## การใช้ผลลัพธ์ (สำหรับคน wire pipeline)

`_project_spec.json` เป็น **fallback ค่ากลาง** — เมื่อ merge ผล Stage B1:
- element ไหนที่ `concrete_grade === null` (section sheet ไม่เขียน) → เติมจาก `concrete_strength`
  (เลือก per-member ก่อน ถ้าไม่มีค่อยใช้ `default_ksc`)
- element ไหนที่ `steel_grade === null` → เติมจาก `steel_grade.main_bar`
- เก็บ `unit_price_source`/trace ว่าค่านี้มาจาก notes ไม่ใช่จาก section เอง (เผื่อ audit)

> ⚠️ อย่าให้ B2 override ค่าที่ B1 อ่านมาได้จริง — B2 เติมเฉพาะช่องที่ B1 เป็น null เท่านั้น
> (section sheet เขียนเฉพาะเจาะจงกว่า general notes เสมอ)

---

## สถานะ

✅ พร้อมทดสอบ — ยิงหน้า general_notes ของบ้าน 01 (ปกติหน้าแรกๆ ของชุดแบบ) 1 หน้าก่อน
🔜 ปรับ raw_notes ให้ยาว/สั้นตามที่ทีมอยากเก็บ — ตอนนี้ตั้งให้เก็บเฉพาะข้อสำคัญสั้นๆ
