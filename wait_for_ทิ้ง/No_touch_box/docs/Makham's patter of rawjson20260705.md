# Makham's Pattern of Raw JSON — 2026-07-05 (แก้ไขล่าสุด 2026-07-06)

สรุป pattern การจัดเก็บ raw JSON ที่มีอยู่จริงในโปรเจกต์นี้ — เริ่มเขียน ณ วันที่ 5 ก.ค. 2026 (เช็คจากไฟล์จริง ไม่ใช่แค่เอกสาร เพราะ `rule_of_tune.md` เดิมมีตัวอย่างแค่ generation เก่า ยังไม่ครอบคลุม generation ใหม่ที่ King/Claude ทดลองไว้ในวันที่ 3 ก.ค.) — อัปเดตต่อเนื่องวันที่ 6 ก.ค. 2026 หลังทดสอบ fresh extraction จริง 2 รอบ (`mk_test/t1`, `mk_test/t2`) ดูหัวข้อ "Generation 3.1"/"Generation 3.2" ท้ายไฟล์สำหรับการแก้ไขล่าสุด

**สถานะ ณ ตอนนี้: มี 2 schema generation อยู่คู่ขนานกันในระบบจริง**

---

## Generation 1 — Flat pattern (เดิม, **ยัง live อยู่ใน `qwen-output/` ทุกไฟล์ตอนนี้**)

ใช้จริงใน `raw/image/<house>/qwen-output/<house>_หน้าNN.json` ของทั้ง 5 บ้านที่ extract แล้ว — **นี่คือ ground truth ตัวจริงที่ Label Studio/`label-studio-tasks-perpage.js` อ่านอยู่ตอนนี้**

### โครงไฟล์เต็ม

```json
{
  "png": "19",
  "doc_page": 17,
  "discipline": "structural",
  "extract": true,
  "extraction": {
    "sheet_code": "S-02",
    "sheet_name": "แปลนฐานรากและฐานรากเสาเข็ม",
    "pattern": "plan",
    "plan": [
      {
        "element_id": "F1,C1",
        "element_type": "footing",
        "count": 11,
        "grid_refs": ["A-1", "A-2", "...", "D-3"],
        "span_length_m": 4.0,
        "confidence_score": 0.85,
        "confidence_flags": ["claude_reviewed"]
      }
    ],
    "schedule": [],
    "section": [],
    "notes": {},
    "warnings": ["..."]
  }
}
```

### จุดสำคัญ
- **1 หน้า = เลือก `pattern` เดียว** (`plan` | `schedule` | `section` | `notes`) แล้วข้อมูลอยู่ใน array/object ที่ตรงกับ pattern นั้น อีก 3 ที่เหลือเป็น `[]`/`{}` ว่างเปล่า
- `notes` pattern เป็น **object เดี่ยว** (ไม่ใช่ list) — เก็บ spec ระดับโปรเจกต์ (`concrete_strength_ksc`, `steel_main`, `cover_mm`, `lap_rule`) ไม่ใช่รายการ element
- `section`/`schedule` pattern มี field ชุดเดียวกัน (`width_mm`, `height_mm`, `main_bar_count`, `main_bar_dia_mm`, `main_bar_type`, `stirrup_dia_mm`, `stirrup_type`, `stirrup_spacing_mm`, `concrete_grade`, `steel_grade`)
- `confidence_flags` เป็น **array ของคำสั้นๆ** (เช่น `"count_uncertain"`, `"inferred_from_layout"`, `"claude_reviewed"`)
- **ข้อจำกัดที่รู้แล้ว**: ถ้า 1 หน้ามีหลาย view (เช่นหน้า 19 มีทั้ง "แปลนฐานราก" + "แปลนคาน") บังคับเลือก pattern เดียวทำให้ view ที่ 2 หายไปเงียบๆ — เหตุผลที่ generation 2 เกิดขึ้น

---

## Generation 2 — `views[]` (ใหม่, **ทดลองอยู่ใน `claude_output_01/02/03/` เท่านั้น ยังไม่เข้า `qwen-output/`**)

ทดลองโดย King + Claude session อื่น วันที่ 2-3 ก.ค. — เก็บใน `raw/image/<house>/claude_output_0N/` แยกจาก `qwen-output/` เดิมสนิท (ไม่เขียนทับ)

### โครงไฟล์เต็ม (ตัวอย่างจริงจาก `claude_output_03/บ้าน_เล็ก_1ชั้น_01_หน้า19.json`)

```json
{
  "png": "19",
  "source_image": "image/บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า19.png",
  "read_by": "Claude — direct independent read (round 3, ...)",
  "grid_source": "บ้าน_เล็ก_1ชั้น_01_Gridline.json",
  "schema_note": "grid ไม่ฝังอยู่ในไฟล์นี้แล้ว — ให้ไปอ่านจาก grid_source แทน",
  "extraction": {
    "sheet_code": "S-02",
    "sheet_name": "แปลนฐานรากแผ่ ,ฐานรากเสาเข็ม / แปลนคาน ,พื้นชั้นล่าง",
    "views": [
      {
        "view_title": "แปลนฐานรากแผ่ และฐานรากเสาเข็ม",
        "pattern": "plan",
        "elements": [
          {
            "element_id": "F1,C1", "element_type": "footing", "count": 11,
            "grid_refs": ["A-1", "...", "D-3"],
            "span_length_m": null, "span_source": null,
            "confidence_score": 0.95, "confidence_flags": []
          }
        ]
      },
      {
        "view_title": "แปลนคาน, พื้นชั้นล่าง",
        "pattern": "plan",
        "elements": [
          {
            "element_id": "B2", "element_type": "beam", "count": 1,
            "grid_refs": ["D-1/D-2"],
            "span_length_m": 4.0, "span_source": "grid_table",
            "confidence_score": 0.75, "confidence_flags": []
          },
          {
            "element_id": "B2", "element_type": "beam", "count": 1,
            "grid_refs": ["?/?"],
            "span_length_m": null, "span_source": "unresolved",
            "confidence_score": 0.35,
            "confidence_flags": ["intermediate_horizontal_divider_inside_D_C_band_right_side", "bears_on_beam:B5(left_end)", "..."]
          }
        ]
      }
    ],
    "warnings": ["..."]
  }
}
```

### Companion file — Gridline.json (แยกต่างหาก ต่อรอบ)

```json
{
  "house": "บ้าน_เล็ก_1ชั้น_01",
  "purpose": "Grid line coordinate table กลาง ใช้ร่วมกันทุกหน้าที่มี grid เดียวกัน 'ภายในรอบการอ่านนี้'",
  "source_sheet_code": "S-02",
  "source_png": "19",
  "grid": {
    "x_lines": [{"id": "A", "pos_m": 0.0}, {"id": "B", "pos_m": 3.5}, {"id": "C", "pos_m": 5.5}, {"id": "D", "pos_m": 9.5}],
    "y_lines": [{"id": "1", "pos_m": 0.0}, {"id": "2", "pos_m": 4.0}, {"id": "3", "pos_m": 7.0}]
  },
  "unnamed_extensions": [
    {"description": "...", "attached_to": "y_line 3", "offset_m": 1.5, "seen_on_png": ["19"]}
  ],
  "confidence_score": 0.9,
  "confidence_flags": ["..."],
  "last_updated_from_page": "19",
  "last_updated_date": "2026-07-03"
}
```

### จุดสำคัญที่ต่างจาก Generation 1

| จุด | Gen 1 (เดิม) | Gen 2 (ใหม่) |
|---|---|---|
| หลาย view ต่อหน้า | ❌ เลือก pattern เดียว view ที่ 2 หาย | ✅ `views[]` array เก็บได้ทุก view |
| grid dimension | ไม่มีเก็บแยก | แยกไฟล์ `<house>_Gridline.json` ต่างหาก **เก็บต่อรอบ ไม่ share ข้ามรอบ** (`claude_output_01`/`02`/`03` มี Gridline.json ของตัวเอง) |
| span คำนวณยังไง | AI กะเอง (`span_length_m` ตรงๆ) | คำนวณจาก grid table ด้วยโค้ด (`apply_grid_spans()`) — มี `span_source` บอกที่มา: `grid_table` (คำนวณ, โค้ดทับเสมอ) / `local_dimension` (อ่านเลขที่พิมพ์ไว้ใกล้ๆ, โค้ดไม่ทับ) / `unresolved` (หาไม่เจอ) |
| beam segment | 1 element = 1 entry รวม grid_refs หลายจุด | **atomic segment** — คาน 1 เส้นตัดเป็นหลาย segment ตาม (element_id, span, span_source) แยกกัน แล้ว group ทีหลัง |
| confidence_flags | คำสั้นๆ (`count_uncertain`) | **ข้อความอธิบายยาวเต็มประโยค** (`"bears_on_beam:B5(left_end)"`, `"not_a_column_split_this_is_a_beam-on-beam_split"`) — ให้บริบทละเอียดกว่ามาก |
| wrapper level fields | `png, doc_page, discipline, extract` | `png, source_image, read_by, grid_source, schema_note` (คนละชุด field เลย ไม่ใช่แค่เพิ่ม) |
| ปลาย grid ที่ resolve ไม่ได้ | ไม่มีระบุ | เขียนเป็น `"?"` แทน grid id (เช่น `"D-3/?"`) |

---

## สรุปสั้นสำหรับงานจัดข้อมูลใหม่ที่จะทำต่อ

1. **`qwen-output/` = ของจริงที่ระบบใช้อยู่ตอนนี้** ยังเป็น Gen 1 (flat pattern) ทั้งหมด 100% — 5 บ้านที่ extract แล้ว
2. **`claude_output_01/02/03/` = การทดลอง Gen 2** ยังเป็น draft ไม่ผ่านคนตรวจ ("draft ที่ยังไม่ผ่านคนตรวจ — ห้ามใช้เป็น ground truth โดยตรง" ตาม `_pilot_comparison_summary.md`) และมีแค่ 4 หน้าตัวอย่าง (19, 21, 24, 40) ของบ้านเดียว (บ้าน_เล็ก_1ชั้น_01)
3. **ทั้ง 2 generation ยังไม่เคยถูกรวมเป็นมาตรฐานเดียว** — ถ้าจะจัดข้อมูลใหม่ ต้องตัดสินใจก่อนว่าจะยึด Gen 1 (ของเดิม, ครบ 5 บ้าน) หรือย้ายไป Gen 2 (ละเอียดกว่า, แม่นกว่าตาม pilot, แต่มีแค่ 4 หน้า ต้อง extract ใหม่ทั้งหมดถ้าจะย้าย)
4. `label-studio-tasks-perpage.js` ที่เราเขียนไว้ **รองรับแค่ Gen 1** ถ้าเลือกย้ายไป Gen 2 ต้องเขียนใหม่ทั้ง flatten logic (จาก `views[].elements` แทน `plan[]/section[]/schedule[]`) และ import script กลับก็ต้อง regroup กลับเป็น `views[]` ไม่ใช่ `plan/section/schedule`

---

## Generation 3 — Makham's Pattern (2026-07-05, **design เท่านั้น — ยังไม่ apply กับ raw JSON จริงที่ไหนเลย**)

⚠️ **สถานะ: อยู่ในไฟล์นี้เท่านั้น ตามคำสั่ง "แก้ใน Makham's patter of rawjson20260705.md เท่านั้น ห้ามแตะ raw json ใน training เลย"** — เป็น spec ที่ออกแบบไว้ก่อน ยังไม่ implement เป็นโค้ด ไม่มีไฟล์ raw JSON ไหนใช้ schema นี้จริง

### โครงสร้างลำดับ field (บนลงล่างตามที่สั่ง)

```
1. sheet_code
2. sheet_name
3. pattern              ← ประเภทหน้า ขยายจาก 4 เป็น 9 ชนิด
   3.1 plan
   3.2 section
   3.3 schedule
   3.4 notes
   3.5 index               (สารบัญ)
   3.6 material_list        (รายการวัสดุ)
   3.7 site_plan
   3.8 site_profile
   3.9 gridline             (ใหม่ — สร้างเองโดยอ้างอิงจากข้อมูลในแปลน ไม่ใช่อ่านจากหน้าตรงๆ)
4. element[]
   4.1 element_id
   4.2 element_type
   4.3 count
   4.4 grid_ref          ← format ต่างกันตาม element_type (ดูตารางด้านล่าง)
```

### กติกา `grid_ref` ตาม `element_type` (ส่วนสำคัญที่สุดของ pattern ใหม่นี้)

| element_type | รูปแบบ `grid_ref` | ความหมาย | ตัวอย่าง |
|---|---|---|---|
| `footing` | หมายเลข grid เดี่ยวๆ | จุดที่ footing ตั้งอยู่ (1 จุด) | `"A1"` |
| `beam` | `{<grid หัว><grid ท้าย>,<span>}` | grid 2 จุด (หัว-ท้าย) ตามด้วย comma แล้ว span length | `"{A1B1,5}"` (จาก A1 ถึง B1 ยาว 5 ม.) |
| `slab` | `{<4 จุด grid ไล่ตามเข็มนาฬิกา>,<ความสูงแกน Y>,<ความสูงแกน X>}` | มุมพื้น 4 จุดวนตามเข็มนาฬิกา ตามด้วยขนาด 2 แกน | `"{D1D2C2C1,5,5}"` |

### ตัวอย่างเต็ม (draft ตามโครงสร้างใหม่)

```json
{
  "sheet_code": "S-02",
  "sheet_name": "แปลนฐานรากและฐานรากเสาเข็ม",
  "pattern": "plan",
  "element": [
    {
      "element_id": "F1,C1",
      "element_type": "footing",
      "count": 11,
      "grid_ref": "A1"
    },
    {
      "element_id": "B2",
      "element_type": "beam",
      "count": 1,
      "grid_ref": "{A1B1,5}"
    },
    {
      "element_id": "S1",
      "element_type": "slab",
      "count": 1,
      "grid_ref": "{D1D2C2C1,5,5}"
    }
  ]
}
```

### กติกาของ pattern `section`/`schedule` — เก็บสเปคจริง (แก้ปัญหาที่เจอจากการทดสอบ 2026-07-05)

**หลักการ:** `section` (และ `schedule`) คือ **source of truth ของสเปค** ต่อ 1 mark (เช่น B1, B2, C1) ส่วน `plan` มีหน้าที่แค่บอก**ตำแหน่ง** (`grid_ref`) ของ mark นั้นๆ — **ไม่ต้องมีฟิลด์สเปคซ้ำอยู่ใน `plan`** ให้ดึง/จับคู่ข้อมูลจาก `section` มาด้วย `element_id` แทน

`element[]` ของ pattern `section`/`schedule` ใช้ field ชุดอื่น (ไม่ใช่ `count`+`grid_ref` แบบ `plan`):

```
element[] (เมื่อ pattern = "section" หรือ "schedule")
  4.1 element_id        ← mark เดียวกับที่ plan ใช้อ้างถึง (เช่น "B2")
  4.2 element_type
  4.5 width_mm
  4.6 height_mm
  4.7 main_bar           { count, dia_mm, type }
  4.8 stirrup             { dia_mm, type, spacing_mm }
  4.9 concrete_grade
  4.10 steel_grade
```

### ตัวอย่าง — ไฟล์ `plan` (ตำแหน่ง) + ไฟล์ `section` (สเปค) แยกกัน แล้วจับคู่ด้วย `element_id`

**ไฟล์ plan (หน้า 19, S-02):**
```json
{
  "sheet_code": "S-02",
  "pattern": "plan",
  "element": [
    { "element_id": "B2", "element_type": "beam", "count": 1, "grid_ref": "{D1D2,4}" }
  ]
}
```

**ไฟล์ section (หน้า 21, S-04) — สเปคของ mark "B2":**
```json
{
  "sheet_code": "S-04",
  "pattern": "section",
  "element": [
    {
      "element_id": "B2",
      "element_type": "beam",
      "width_mm": 200,
      "height_mm": 400,
      "main_bar": { "count": 2, "dia_mm": 12, "type": "RB" },
      "stirrup": { "dia_mm": 6, "type": "RB", "spacing_mm": 150 },
      "concrete_grade": "fc210",
      "steel_grade": "SR-24 / SD-40"
    }
  ]
}
```

**ตอนประกอบข้อมูลจริง (join step)** — เอา `element_id: "B2"` จากไฟล์ plan ไปหาใน element[] ของไฟล์ section ที่มี `element_id` ตรงกัน แล้วรวมเป็น record เดียว:
```json
{
  "element_id": "B2", "element_type": "beam",
  "count": 1, "grid_ref": "{D1D2,4}",
  "width_mm": 200, "height_mm": 400,
  "main_bar": { "count": 2, "dia_mm": 12, "type": "RB" },
  "stirrup": { "dia_mm": 6, "type": "RB", "spacing_mm": 150 },
  "concrete_grade": "fc210", "steel_grade": "SR-24 / SD-40"
}
```

**ข้อดี:** ไม่ต้องเขียนสเปคซ้ำทุกจุดที่ element ปรากฏใน plan (เช่น B2 มี 6 ตำแหน่งในหน้า 19 ก็ join กับ section ได้ทั้ง 6 จุดจาก entry เดียว) — ตรงกับที่แบบก่อสร้างจริงก็ทำงานแบบนี้ (ดู mark ในผัง แล้วไปเปิดตาราง/section หาสเปค)

**⚠️ ยังต้องตัดสินใจ:** ถ้า `element_id` เดียวกันปรากฏใน `section` มากกว่า 1 sheet (เช่น B2 มีรายละเอียดอยู่ทั้ง S-04 และ S-05) จะ join จากไฟล์ไหนก่อน/เกิด conflict ยังไง — ยังไม่ได้ทดสอบเคสนี้

### ❓ จุดที่ต้องเช็คกับมะขามก่อน implement จริง (สถานะล่าสุด 2026-07-06 — ส่วนที่ตอบแล้วทำเครื่องหมาย ✅)

1. ✅ **`footing` ที่มีหลายตำแหน่ง** — **ตัดสินใจแล้ว (2026-07-05):** entry เดียว, `grid_ref` เก็บหลายจุดเป็น string คั่น comma (เช่น `"A1,A2,A3,B1,B2,B3,C1,C3,D1,D2,D3"`) ไม่แยก entry ทีละจุด — ใช้จริงแล้วใน `mk_test/บ้าน_เล็ก_1ชั้น_01_หน้า19_view1_footing_plan.json`
2. ✅ **Pattern 9 ชนิดใหม่** — **ตัดสินใจแล้ว (2026-07-05):** ขยาย scope ทำทุก pattern ที่เจอจริงในหน้า (ไม่ล็อกแค่ structural อีกต่อไปสำหรับรอบ extraction นี้) — ดูหัวข้อ "Generation 3.1" ด้านล่างสำหรับ pattern ที่ 10 (`unknown`) ที่เพิ่มเข้ามาระหว่างทดสอบจริง
3. ⚠️ **`gridline`** — ยังไม่ได้ตัดสินใจอย่างเป็นทางการ แต่ระหว่าง extraction จริง (`mk_test/`) เลือกทำแบบ **ไฟล์ companion แยกต่างหากต่อหน้า plan** (เช่น `_หน้า19_gridline.json` คู่กับ `_หน้า19_view1_footing_plan.json`) ไม่ได้รวมเป็น pattern ในไฟล์เดียวกัน — ใกล้เคียงแนวทาง Gen 2 มากกว่า ไม่ใช่ pattern 3.9 ตามที่ระบุไว้เดิม ควรยืนยันกับมะขามอีกครั้งว่าจะยึดแนวนี้ถาวรไหม
4. ✅ **field เดิมจาก Gen 1/2** — **ตัดสินใจแล้ว (2026-07-05):** เก็บไว้ทั้งหมด (`confidence_score`, `confidence_flags`, `doc_page`, `discipline`) เพิ่มจาก 4 field หลัก — `span_source` ยังไม่ได้ใส่ในรอบ extraction แรก แต่ควรเพิ่มตาม Generation 3.1 ด้านล่าง (พบว่าจำเป็นมากสำหรับ beam segment)

---

## ผลทดสอบจริง (2026-07-05) — บ้าน_เล็ก_1ชั้น_01 หน้า 02, 18, 19, 20, 21, 38

ทดสอบ Makham's Pattern กับตัวแทนแต่ละ pattern type (ไม่ใช่แค่ `plan` ซ้ำ) — ไฟล์ทดสอบอยู่ที่ `mk_test/` (ไม่แตะ raw JSON จริงเลยตามคำสั่ง) **เจอปัญหาใหม่ที่ร้ายแรงกว่า 4 ข้อเดิม:**

### ⚠️ ปัญหาใหญ่ที่สุด: schema 4-field ไม่มีที่เก็บสเปคจริงของ `section`/`schedule`/`material_list`

ทดสอบหน้า 21 (S-04, ขยายคาน B1-B6 + ตารางเสา C1) พบว่า **schema ปัจจุบันมีแค่ `element_id`, `element_type`, `count`, `grid_ref` — ไม่มีฟิลด์ไหนเก็บ width/height/จำนวนเหล็ก/ขนาดเหล็ก/ระยะปลอก/กำลังคอนกรีตเลยสักตัว** ลองยัดข้อมูลจริงลง schema นี้แล้วข้อมูลหายหมด (ดู `mk_test/บ้าน_เล็ก_1ชั้น_01_หน้า21.json` — ต้องแอบเก็บ spec จริงไว้ใน field พิเศษ `_actual_spec_data_that_has_nowhere_to_go` เพื่อไม่ให้ข้อมูลหายไปเฉยๆ)

เช่นเดียวกับ `material_list` (ทดสอบหน้า 38, BOQ) — ไม่มีฟิลด์ `unit` (หน่วย: ตร.ม./กก./ต้น/ผืน) และไม่มีฟิลด์ราคาเลย ทั้งที่เป็นข้อมูลสำคัญที่สุดของรายการวัสดุ

**สรุป:** `grid_ref` (4.4) ใช้ได้ดีกับ pattern `plan` เท่านั้น (ที่ต้องการแค่ "อยู่ตรงไหน") แต่ `section`/`schedule`/`material_list` ต้องการ "สเปค/ตัวเลข" ไม่ใช่ "ตำแหน่ง" — **น่าจะต้องมี field ชุดที่ 2 สำหรับสเปค แยกจาก `grid_ref` โดยเฉพาะ** (ไม่งั้น pattern เหล่านี้ใช้งานไม่ได้เลยจริงๆ)

### ปัญหาอื่นที่เจอเพิ่ม

5. **1 หน้ามักมีหลาย pattern ปนกัน** (ปัญหาเดิมที่ Gen 2 เคยแก้ด้วย `views[]`) — หน้า 18 มีทั้ง `notes` (สเปคโครงการ) + `index` (ตารางรายชื่อแผ่น S-01 ถึง S-08) ปนกัน, หน้า 21 มีทั้ง `section` (คาน) + `schedule` (ตารางเสา) ปนกัน — Makham's Pattern (Gen 3) ยังไม่มีกลไกรองรับ (ไม่มี `views[]` แบบ Gen 2 แล้ว)
6. **pattern `index` (3.5) ไม่มี element ก่อสร้างเลย** — เป็นรายการหมวดแบบ+เลขหน้า ไม่เข้ากับโครง `element[]` (element_id/element_type/count/grid_ref) เลยสักฟิลด์ ต้องออกแบบโครงสร้างแยกต่างหาก (ทดสอบเป็น `sections[]` ไปก่อนใน `mk_test/บ้าน_เล็ก_1ชั้น_01_หน้า02.json`)
7. **roof truss plan (แปเหล็ก/จันทันเหล็กรูปพรรณ) ในหน้า 20 ไม่มี `element_type` ที่เหมาะ** — ไม่ใช่ footing/beam/slab แบบ คสล. เป็นเหล็กรูปพรรณคนละระบบ (purlin/rafter) ยังไม่มีในสเปค

### ไฟล์ทดสอบทั้งหมด (`mk_test/`)
`บ้าน_เล็ก_1ชั้น_01_หน้า02.json` (index), `_หน้า18.json` (notes+index ปน), `_หน้า19.json` + `_หน้า19_gridline.json` (plan+gridline), `_หน้า20.json` (plan, พลาด roof truss), `_หน้า21.json` (section+schedule ปน, โชว์ปัญหา spec หาย), `_หน้า38.json` (material_list, โชว์ปัญหา unit หาย)

---

## Generation 3.1 — ปรับปรุงจากการเทียบกับ `claude_output_03` (Gen 2 pilot, อ่านซ้ำ 3 รอบ) + fresh extraction เต็ม 60 หน้า (2026-07-06)

หลังตัดสินใจ 4 คำถามเปิดหลักแล้ว (ดูเครื่องหมาย ✅ ด้านบน) มะขามสั่งให้ทำ **fresh extraction จริงหน้า 1-60 ของ `บ้าน_เล็ก_1ชั้น_01`** ลง `mk_test/` (อ่านภาพใหม่ทั้งหมด ไม่ใช้ Gen 1 เดิม) แล้วเทียบผลกับ `claude_output_03` (Gen 2 pilot ที่ทำไว้ก่อนหน้าและผ่านการอ่านซ้ำอิสระ 3 รอบจนมั่นใจสูงในหน้า 19/21/24/40) — พบจุดที่ Gen 3 ควรปรับปรุงจริงหลายจุด:

### 1. ✅ นำ `span_source` กลับมาใช้ (ยืมจาก Gen 2) — จำเป็นจริง ไม่ใช่แค่ nice-to-have

ตอน fresh-extract หน้า 19 (แปลนคาน) ด้วยตัวเอง โดยไม่มี `span_source` ในสเปค ผลคือต้องให้ `confidence_score` ต่ำมาก (~0.4) กับทั้งหน้าเพราะแยกไม่ออกว่า span ไหน "คำนวณได้จาก grid table" (มั่นใจสูง) กับ span ไหน "เดา/อ่านจากตัวเลขที่พิมพ์ไว้ใกล้ๆ" (มั่นใจต่ำกว่า) — Gen 2 (ผ่านการ verify 3 รอบ) พิสูจน์แล้วว่า field นี้แก้ปัญหานี้ได้จริง ให้เพิ่มเข้า field set ของ `plan`/`beam` element:

```
element[] (เมื่อ pattern = "plan" และ element_type = "beam")
  ... (element_id, element_type, count, grid_ref ตามเดิม)
  + span_source: "grid_table" | "local_dimension" | "unresolved"
```
- `grid_table` = คำนวณจาก `gridline` companion file (มั่นใจสูง)
- `local_dimension` = อ่านจากตัวเลขมิติที่พิมพ์กำกับไว้ใกล้ element โดยตรง (ไม่ได้มาจากกริดหลัก)
- `unresolved` = หาที่มาไม่ได้ ต้องซูมภาพเพิ่ม — **ห้าม**ใส่ span_length_m แบบเดามั่ว ถ้า source เป็น `unresolved` ให้ span เป็น `null`

### 2. ✅ Atomic beam segment — คานยาว 1 มาร์คต้องแยกเป็นหลาย entry ตามช่วง grid จริง ไม่ใช่นับรวมเป็น `count`

การ fresh-extract หน้า 19 (view คาน) ด้วยตัวเอง ใช้วิธี "นับจำนวนครั้งที่เจอ mark + อธิบาย grid คร่าวๆ" (เช่น `B4: count 5, grid_ref: "แนวแกน 1 ตลอดแนว D-C-B-A..."`) ได้ confidence ต่ำมากเพราะข้อมูลไม่ atomic พอ — Gen 2 (3 รอบ, ตรงกัน 100%) พิสูจน์แนวทางที่ดีกว่า: **1 คานมาร์คเดียวกันที่ปรากฏหลายช่วง (span ต่างกัน) ต้องแยกเป็นคนละ entry** โดย group ตาม `(element_id, span_length_m, span_source)` แต่ละ entry มี `grid_ref` เป็นคู่ grid เดียว (1 ช่วง) ไม่ใช่ list รวมทุกช่วง เช่น B4 4 ช่วงคนละ span จะเป็น 4 entries แยกกัน (ไม่ใช่ 1 entry `count:5`)

**ปรับกติกา `grid_ref` ของ `beam`:** ยังเป็น `"{หัวกริด+ท้ายกริด,span}"` เหมือนเดิม แต่ **1 entry = 1 segment เท่านั้น** ถ้า resolve หัว/ท้ายไม่ได้ ให้ใช้ `"?"` แทน (เช่น `"{D3?,null}"`) ตามแบบ Gen 2 แทนการเขียนคำอธิบายภาษาไทยยาวๆ ลงใน `grid_ref`

### 3. ✅ `slab` element_type ครอบคลุมสัญลักษณ์ marker พื้นแบบ SO/SI/SX/ST ด้วย (ไม่ใช่ "unknown_symbol")

ตอน fresh-extract หน้า 19 เจอสัญลักษณ์วงกลม SO/SI/ST กระจายอยู่ในผัง แต่ไม่รู้ความหมายเลยใส่ `element_type: "unknown_symbol"` ไปก่อน (confidence 0.3) — Gen 2 ยืนยันแล้วว่านี่คือ **`element_type: "slab"`** (marker บอกชนิดพื้นที่จุดนั้น ไม่ใช่คาน) และตรงกับที่หน้า 23 (S-06 "ขยายพื้น SO,SI,SX,ST") มีสเปคของแต่ละชนิดพื้นจริง — **cross-reference ข้ามหน้าใช้ได้:** plan (หน้า 19) บอกตำแหน่ง/จำนวนจุดที่ใช้พื้นชนิดนั้น, section (หน้า 23) บอกสเปค เหมือนกับ beam ที่ join ด้วย `element_id`

**⚠️ พบจุดที่ต้องแก้:** ไฟล์ `mk_test/บ้าน_เล็ก_1ชั้น_01_หน้า23.json` ที่ทำไว้ใช้ `element_id: "S1"` แต่ Gen 2 (อ่านซ้ำ 3 รอบ เพื่อยืนยันจุดนี้โดยเฉพาะ) สรุปว่าที่จริงคือ **`"SI"`** (ตัว I ไม่ใช่เลข 1) — สัญลักษณ์ชุดนี้เป็น suffix ตัวอักษรทั้งหมด (S-**O**/S-**I**/S-**X** + T) ไม่ใช่ S ตามด้วยเลข — ต้องแก้ `mk_test/บ้าน_เล็ก_1ชั้น_01_หน้า23.json` (เปลี่ยน `"S1"` → `"SI"`) ก่อนใช้เป็น ground truth จริง

### 4. ⚠️ Ø (สัญลักษณ์กลม) = RB เสมอ ไม่ใช่ DB — อย่าเดาจากขนาดเส้นผ่านศูนย์กลาง

ตอน fresh-extract หน้า 21 (ขยายคาน) ด้วยตัวเอง ใส่ `main_bar.type: "DB"` ให้กับเหล็กหลักทุกเส้น (สมมติว่าเส้นผ่านศูนย์กลาง ≥12mm = DB ตามธรรมเนียมทั่วไป) และมี confidence_flags บอกว่า "inferred_not_printed" — Gen 2 (ซึ่งมีบันทึกประวัติของโปรเจกต์นี้ว่า Qwen เคยอ่าน Ø ผิดเป็น DB มาก่อน) ยืนยันชัดว่า **สัญลักษณ์บนหน้า S-04 ทั้งแผ่นเป็น "Ø" (กลม) ล้วน = RB (SR24) ทั้งหมด ไม่มี DB เลยสักเส้น** แม้เส้นผ่านศูนย์กลางจะใหญ่ถึง 16mm ก็ตาม — **บทเรียน: ต้องดูสัญลักษณ์ที่พิมพ์จริง (Ø กลม = RB, เส้นข้ออ้อยมีรอยหยัก = DB) ห้ามอนุมานจากขนาดเส้นผ่านศูนย์กลางเด็ดขาด** ต้องแก้ `mk_test/บ้าน_เล็ก_1ชั้น_01_หน้า21_view1_section.json` (เปลี่ยน `main_bar.type`/`stirrup.type` จาก `"DB"` เป็น `"RB"` ทุก element) ก่อนใช้เป็น ground truth จริง

### 5. ❓ เปิดคำถามใหม่: เหล็กบน-ล่างไม่เท่ากัน (asymmetric main bar) — ยังไม่มี field รองรับ

ทั้ง Gen 2 และการ fresh-extract ของผมเองเจอปัญหาเดียวกันอิสระต่อกัน: มาร์ค B5/B5X มีเหล็กบน 2 เส้น + ล่าง 3 เส้น (ไม่ใช่ 2+2) ตอนนี้ schema มีแค่ `main_bar.count` เดี่ยว (รวมเป็น 5) ทำให้ข้อมูล "บนกี่เส้น ล่างกี่เส้น" หายไป — **ต้องตัดสินใจ:** จะแยกเป็น `main_bar: {top: {count,dia_mm,type}, bottom: {count,dia_mm,type}}` แทน `main_bar: {count,dia_mm,type}` เดี่ยวไหม? (Breaking change กับตัวอย่างเดิมในเอกสารนี้ทุกจุด)

### 6. ❓ เปิดคำถามใหม่: เหล็กเสริมพิเศษที่หยุดกลางคาน (stop bar / curtailment ที่ L/8) — mk_test แก้ปัญหานี้ไว้แล้ว แต่ยังไม่ยืนยันเป็นทางการ

Gen 2 ไม่มี field รองรับ เลยเก็บเป็นคำอธิบายยาวใน `confidence_flags` แทน (เช่น `"extra_top_bar_1-Ø12mm_stopped_at_L/8..."`) — ตอน fresh-extract หน้า 21 ผมออกแบบ field ใหม่ `additional_bars: [{count, dia_mm, position, note}]` แยกจาก `main_bar` หลัก ซึ่ง**ดีกว่าวิธีของ Gen 2** (เป็นข้อมูลโครงสร้างที่ query ได้ ไม่ใช่แค่ข้อความอธิบาย) — เสนอให้รับ field นี้เข้าสเปคถาวร แต่ยังไม่ได้ยืนยันกับมะขามอย่างเป็นทางการ

### 7. ❓ เปิดคำถามใหม่: ตารางเสาหลายระดับ (เช่น C1 มีสเปคต่างกันตามชั้น) — 2 วิธีที่เป็นไปได้ ยังไม่ตัดสินใจว่าจะยึดแบบไหน

- **แบบที่ผมใช้ใน mk_test:** เก็บ `element_id: "C1"` ซ้ำ 2 entry เท่ากับจำนวนระดับ แยกด้วย field ใหม่ `level: "โครงหลังคา" | "พื้นชั้น1, ตอม่อ, ฐานราก"`
- **แบบที่ Gen 2 ใช้:** ฝัง level ไว้ใน `element_id` เอง (เช่น `"C1_โครงหลังคา"`, `"C1_ตอม่อฐานราก"`)

ข้อดี-เสีย: แบบแรก `element_id` สะอาด (ตรงกับ mark จริงในแบบ) แต่ต้อง de-dupe ด้วย 2 field ร่วมกัน (`element_id`+`level`); แบบหลัง `element_id` unique ในตัวเองแต่ไม่ตรงกับ mark ที่พิมพ์จริงในแบบ (ตรงกับ mark จริง+level ที่ประดิษฐ์ขึ้น) — เสนอให้ใช้แบบแรก (แยก field `level`) เพราะ `element_id` ควรตรงกับที่พิมพ์ในแบบเป๊ะเพื่อให้ join ข้ามหน้าได้ตรงไปตรงมา

**หมายเหตุคุณภาพข้อมูล Gen 1 เดิม:** Gen 2 ยืนยันว่าแถว "C1 ระดับตอม่อ/ฐานราก" **หายไปทั้งแถวจาก Gen 1 เดิม** (Qwen พลาดไม่ดึงมาเลยตอน automated pass ครั้งแรก) — เป็นตัวอย่างจริงว่า Gen 1 มีช่องโหว่ ไม่ใช่แค่ปัญหาเรื่อง schema

### 8. ❓ เปิดคำถามใหม่: รายละเอียดการติดตั้งพื้นสำเร็จรูป (precast plank / SP) ต้องการ field เฉพาะ ไม่ใช่ยืม main_bar/stirrup

หน้า 24-25 (S-07/S-08) เป็น typical detail การวางพื้นสำเร็จรูป ไม่ใช่ rebar schedule ของคาน/เสา ทั้ง Gen 2 และผมเองเจอปัญหาเดียวกัน: field `main_bar`/`stirrup` ถูก "ยืมความหมาย" มาใช้ผิดๆ (เช่น `main_bar` จริงๆ คือเหล็กหนีบ/หมุด hook `1+1Ø9มม.`, `stirrup` จริงๆ คือตะแกรงเหล็กเสริม topping ไม่ใช่ปลอกคาน) Gen 2 เสนอ field ใหม่เฉพาะไว้ (ยังไม่ implement) — เห็นด้วยกับแนวทางนี้ เสนอ field set ใหม่สำหรับ `element_type: "precast_plank_detail"`:
```
{
  element_id, element_type: "precast_plank_detail",
  description,
  dowel_bar: { count, dia_mm, type },       // เหล็กหนีบ/หมุด (แทนที่ main_bar เดิม)
  topping_mesh: { dia_mm, spacing_mm },      // ตะแกรงเสริม topping (แทนที่ stirrup เดิม)
  topping_thickness_min_mm,
  level_step_mm,                              // ระดับต่างจากพื้นปกติ (ถ้ามี เช่นพื้นห้องน้ำลด 0.10ม.)
  confidence_score, confidence_flags
}
```

### 9. ⚠️ Grid axis convention — ต้องนิยามให้ชัดว่า `x_lines`/`y_lines` หมายถึงแกนไหน (พบว่าสับสนได้จริง)

เทียบ gridline ของหน้า 19 ระหว่างของผม (fresh extract) กับ Gen 2 พบว่า**ตำแหน่งตัวเลขตรงกัน 100%** (cross-validate ผ่าน) แต่**ชื่อ field สลับกัน**: ผมเรียกกริดตัวเลข (1,2,3 แนวนอนบนสุด) ว่า `x_lines` และกริดตัวอักษร (D,C,B,A แนวตั้งด้านข้าง) ว่า `y_lines`; Gen 2 เรียกกลับกัน (ตัวอักษร=`x_lines`, ตัวเลข=`y_lines`) — **ข้อมูลตรงกัน แค่ label สลับ** แต่ถ้าไม่ตกลงกันให้ชัดจะทำให้ dataset ไม่สม่ำเสมอข้ามรอบ extraction เสนอกติกา: **`x_lines` = กริดที่วิ่งแนวนอนตามขอบบนของแผ่น (มักเป็นตัวเลข 1,2,3...) และ `y_lines` = กริดที่วิ่งแนวตั้งตามขอบข้างของแผ่น (มักเป็นตัวอักษร A,B,C...)** ยึดตามที่ผมใช้ใน `mk_test/` (ยังไม่ได้ยืนยันกับมะขามอย่างเป็นทางการ)

### 10. ✅ ยืนยันแล้ว: 1 ไฟล์ PNG ของ BOQ อาจมี 2 แผ่นจริงซ้อนกัน (ต้องหมุน 90° + แยกซ้าย-ขวา)

ทั้ง Gen 2 (หน้า 40) และ agent ที่ทำ `mk_test/` หน้า 48-57 อิสระต่อกัน เจอปัญหาเดียวกันและแก้ด้วยวิธีเดียวกัน: PNG ต้นฉบับเป็น portrait 2 แผ่นเรียงในภาพเดียวแบบ landscape (ต้องหมุน 90° แล้วแยกครึ่งซ้าย-ขวาเป็นคนละแผ่น/คนละ `sheet_no`) — ยืนยันว่านี่คือกติกาที่ถูกต้องสำหรับหน้า BOQ ของบ้านหลังนี้ (และน่าจะบ้านอื่นในชุดเดียวกันด้วย) ให้แยกเป็นไฟล์ `_1.json`/`_2.json` เสมอเมื่อเจอ 1 PNG มี 2 sheet_no

### สรุปไฟล์ mk_test ที่ต้องแก้ไขก่อนใช้เป็น ground truth จริง (พบจากการเทียบนี้)

| ไฟล์ | ต้องแก้ | เหตุผล |
|---|---|---|
| `บ้าน_เล็ก_1ชั้น_01_หน้า23.json` | `element_id: "S1"` → `"SI"` | Gen 2 ยืนยันด้วยการอ่านซ้ำ 3 รอบเฉพาะจุดนี้ |
| `บ้าน_เล็ก_1ชั้น_01_หน้า21_view1_section.json` | `main_bar.type`/`stirrup.type`: `"DB"` → `"RB"` ทุก element | สัญลักษณ์บนแผ่นเป็น Ø (กลม) ล้วน ไม่มี DB เลย — เคยมีประวัติอ่านผิดจุดนี้มาก่อนในโปรเจกต์ |
| `บ้าน_เล็ก_1ชั้น_01_หน้า19_view2_beam_plan.json` | ควร extract ใหม่ทั้งหมดด้วยวิธี atomic segment + `span_source` (ข้อ 1-2 ด้านบน) แทนของเดิมที่ confidence ต่ำ (~0.4) | schema เดิมตอนทำไม่มี `span_source` จึงแยก segment ไม่ได้แม่นพอ |

**สถานะ mk_test ณ วันนี้ (2026-07-06):** หน้า 1-40 และ 48-60 extract แล้ว (บางไฟล์ต้องแก้ตามตารางข้างบน), **หน้า 41-47 (BOQ ฐานรากแผ่) ยังไม่ได้ extract** (งานค้าง ดู `workmen's_diary/2026-07-05.md`)

---

## Generation 3.2 — Dummy Grid convention + "หน้า 0" grid master file (2026-07-06)

มะขามพบระหว่างดูหน้า 06 (A-04 แปลนพื้นชั้น 1) ว่า**มีเส้นผนัง/แนวคานที่วิ่งเต็มความสูงอาคาร (จากแนว D ถึงใต้แนว A) แต่ไม่มีวงกลมกำกับกริดใดๆ เลยในแบบต้นฉบับ** (อยู่ที่ระยะ 2.55 ม. จากกริด "1" หรือ 1.45 ม. ก่อนถึงกริด "2") — ตรงกับตำแหน่งของคาน B1 ที่เคยพบปัญหาเดียวกันมาก่อนแล้วทั้งในการ fresh-extract หน้า 19 ของผมเอง และใน `claude_output_03` (Gen 2, บันทึกไว้ว่า "interior position between grid 1 and 2, not legible")

### กติกาใหม่ที่ตกลงกัน

1. **Dummy grid** — เมื่อพบเส้นโครงสร้าง (คาน/ผนังรับน้ำหนัก) ที่ไม่อยู่บนกริดหลักที่มีชื่อในแบบ (ตัวเลข/ตัวอักษรที่พิมพ์มากับแบบจริง) ให้ **ตั้งชื่อกริดเสมือนขึ้นเอง** ด้วย **prime notation** ต่อท้ายกริดหลักที่ใกล้ที่สุด เช่น `1'`, `A'`, `3'` (ถ้ามีมากกว่า 1 เส้นในช่วงเดียวกัน ใช้ `A''`, `A'''` ไล่ไป) — ให้ระบุตำแหน่ง (`pos_m`) จากเส้นบอกระยะที่พิมพ์จริงในแบบเสมอ (ไม่เดา) และเก็บ `type: "dummy"` แยกจาก `type: "named"` เพื่อความโปร่งใสว่าอันไหนเป็นกริดจริง อันไหนเป็นกริดที่สร้างขึ้นเอง
2. **ไฟล์ "หน้า 0" (`<house>_หน้า00_gridline.json`)** — ก่อนจะเริ่ม extract หน้า plan/section อื่นๆ ของบ้านหนึ่งๆ ให้สร้าง/อัปเดตไฟล์กริดกลางนี้ก่อนเสมอ (`png: "00"` เป็น convention หมายถึง "ไม่ใช่หน้าจริงในเอกสาร แต่เป็นไฟล์สังเคราะห์กริดกลางของทั้งบ้าน") รวมทั้งกริดหลัก (`type: "named"`) และ dummy grid ทั้งหมดที่พบ (`type: "dummy"`) ไว้ในที่เดียว แล้วให้ทุกหน้าที่ต้องอ้างอิงกริดของบ้านนี้ (plan, section ที่มีการอ้างตำแหน่ง) ชี้มาที่ไฟล์นี้แทนการเขียน grid ซ้ำหรือบรรยายเป็นข้อความอิสระต่อไฟล์ — ตัวอย่างจริง: `mk_test/บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json`
3. ไฟล์ gridline เดิมที่เคยสร้างต่อหน้า (เช่น `_หน้า19_gridline.json`, `_หน้า06_gridline.json`) **ยังเก็บไว้ไม่ลบ** เพื่อ traceability (ที่มาว่ากริดแต่ละเส้นยืนยันจากหน้าไหน) แต่ให้ถือว่า **ไฟล์ "หน้า 0" คือตัวที่ใช้อ้างอิงจริงต่อไป**

### ตัวอย่างพบจริง (บ้าน_เล็ก_1ชั้น_01)

| Dummy grid | ตำแหน่ง | หลักฐาน | ความมั่นใจ |
|---|---|---|---|
| `1'` | 2.55 ม. จากกริด 1 (แกน x) | เส้นผนัง/คานเต็มความสูงอาคารในหน้า 06 (A-04) ตรงกับคาน B1 ที่หน้า 19/Gen 2 | สูง (0.85) — เห็นเส้นชัดเจนเต็มความสูง |
| `3'` | 8.5 ม. (ขอบนอกส่วนต่อขยาย 1.5ม. เลยกริด 3) | ตรงกับ "unnamed_extension" ที่ Gen 2 Gridline.json บันทึกไว้ + คาน B4X | ปานกลาง (0.6) — ยังไม่ยืนยันว่าคานอยู่ตรงขอบนอกหรือที่เส้นย่อย +0.60 |
| `A'` / `A''` | 11.0 ม. / 12.5 ม. (ส่วนต่อขยายใต้กริด A แบ่ง 1.5+1.5) | ตรงกับ "unnamed_extension" ใต้กริด A ที่ Gen 2 บันทึกไว้ + คาน B3X/B5X | ปานกลาง-ต่ำ (0.5-0.55) — ยังไม่ยืนยัน 100% |

**ค้างไว้:** ตอน redo หน้า 19 view2 (beam plan) และหน้า 20 (แปลนอะเส/โครงหลังคา) ด้วยวิธี atomic segment (ดู Generation 3.1 ข้อ 1-2) ให้ reference กริด (รวม dummy) จากไฟล์ `หน้า00_gridline.json` นี้ แล้วยืนยัน/ปรับความมั่นใจของ `3'`/`A'`/`A''` ให้แม่นขึ้นตอนนั้น

---

## Generation 3.3 — Join สเปคหน้าตัดคานเข้า plan โดยตรงตอน extract (2026-07-06)

**เปลี่ยนจากที่ Generation 3 ออกแบบไว้เดิม:** ตอนแรก (ดูหัวข้อ "กติกาของ pattern `section`/`schedule`") ออกแบบไว้ว่า `plan` มีหน้าที่แค่บอกตำแหน่ง (`grid_ref`) ส่วน `section` เป็น source of truth ของสเปค แล้ว**ค่อย join กันตอนประกอบ dataset** (assembly time, คนละขั้นตอนจาก extraction) — มะขามสั่งให้เปลี่ยนมา **join สเปคเข้า `plan` element โดยตรงตั้งแต่ตอน extract/แก้ไฟล์เลย** เพื่อให้รีวิว 1 หน้าเห็นครบทั้งตำแหน่งและสเปค ไม่ต้องเปิด 2 ไฟล์เทียบกันเอง

**Field ใหม่ที่เพิ่มเข้า `plan` beam element หลัง join:**
```
width_mm, height_mm, main_bar{count,dia_mm,type}, stirrup{dia_mm,type,spacing_mm},
additional_bars[], concrete_grade, steel_grade,
spec_source        <- ไฟล์ section ที่ join สเปคมา (เช่น "หน้า21_view1_section.json (S-04)")
spec_confidence_score  <- ความมั่นใจของสเปค (จากไฟล์ section) แยกจาก confidence_score หลัก
```
**หลักการ:** `confidence_score` เดิมของ element ยังหมายถึงความมั่นใจเรื่อง**ตำแหน่ง** (grid_ref/span) เหมือนเดิม — ไม่ปนกับความมั่นใจเรื่องสเปคที่ join เข้ามาใหม่ (เก็บแยกไว้ที่ `spec_confidence_score`) เพื่อไม่ให้ทั้งสองเรื่องกลบกันจนดูไม่ออกว่าอันไหนไม่ชัวร์เพราะอะไร

**Element ที่ไม่ใช่คาน (เช่น slab marker SO/SI/SX/ST) ไม่ join สเปคจากไฟล์ section คาน** — สเปคของ marker เหล่านี้อยู่คนละไฟล์ (`หน้า23.json`, S-06 "ขยายพื้น SO,SI,SX,ST") ยังไม่ได้ join ในรอบนี้ (ทำแค่คานตามที่สั่ง) แต่ใส่ flag `not_a_beam_no_section_spec_joined_here_see_หน้า23.json_for_slab_edge_spec` กำกับไว้เป็น pointer ให้ทำต่อได้ถ้าต้องการ

**ใช้แล้วจริงกับ:** `mk_test/t2/บ้าน_เล็ก_1ชั้น_01_หน้า19_view2_beam_plan.json` (join จาก `หน้า21_view1_section.json`) และ `..._หน้า20_view1_tie_beam_plan.json` (B2/B6 join จากไฟล์เดียวกัน)

**ข้อควรระวังที่ยกมาด้วย:** `concrete_grade` ยังใส่เป็น `null` ทุก element เพราะค่าจริง (210 vs 240 ksc) ยังไม่ยืนยัน — ไม่ join ค่าที่ยังขัดแย้งกันอยู่เข้าไปโดยไม่เตือน
