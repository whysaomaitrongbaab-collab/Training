---
stage: B1
model: qwen-vl-max
temperature: 0.2
max_tokens: 2048
response_format: json_object
input: 1 page image (single call per page, NOT batch)
input_requires: sheet_type from Stage A (floor_plan | section_detail | schedule_table)
output_schema: aligned with js/shared/schema.js → createBeamLibraryEntry() + createDrawingElement()
---

# Stage B1 — Element Extractor

## วัตถุประสงค์

ดึงรายละเอียดโครงสร้างจากหน้าที่ Stage A classify ว่าเป็น structural page
อ่านตัวเลข dimension, rebar notation, grid reference ให้แม่นยำ → JSON ที่ pipeline กินต่อได้เลย

## หลักการทำงานจริง

```
qwen-processor.js (script)
  │
  ├── หน้าละ 1 call (ไม่ batch — spatial reasoning ต้องการ context เต็ม)
  │     └── เลือก prompt ตาม sheet_type ที่ Stage A ให้มา:
  │            section_detail  → SECTION_PROMPT   (อ่าน spec เหล็ก/มิติหน้าตัด)
  │            schedule_table  → SCHEDULE_PROMPT  (อ่านตารางเป็นแถว)
  │            floor_plan      → FLOORPLAN_PROMPT (นับ instance + grid + span)
  │
  └── เซฟผลเป็น <ชื่อเดียวกับรูป>.json
```

**Script เป็นคนเลือก prompt จาก sheet_type — Qwen ไม่รู้ว่ามาจาก stage ไหน**

---

## ⚠️ บทเรียนจาก research (ต้องฝังใน prompt)

อ้างอิง [research/vision-ai/02-vision-language-engineering-drawings.md](../../research/vision-ai/02-vision-language-engineering-drawings.md):

1. **Instance counting คือจุดอ่อนสุดของ VLM** — AECV-Bench (2026) พบการนับประตู/หน้าต่างแม่นแค่ ~0.09–0.39 EM (MAPE 20–50%)
   → floor_plan ต้องให้ count มาพร้อม `confidence_flags:["count_uncertain"]` เสมอเมื่อไม่มั่นใจ ห้ามเดามั่ว
2. **Cross-sheet referencing เป็นจุดอ่อน** — อย่าให้โมเดลเดา spec ของ element จากหน้าอื่นที่มองไม่เห็น
   → ถ้าหน้าเป็น floor_plan (ไม่มี spec เหล็ก) ให้ปล่อย field เหล็กเป็น null ไม่ต้องเดา
3. **Thai DB/RB notation ต่างจาก Western** — "2DB16" = เหล็กข้ออ้อย 2 เส้น 16mm, "RB6" = เหล็กกลม 6mm
4. **Confidence scoring = จุด handoff ให้คน** — ทุก field ตัวเลขต้องมี confidence, ต่ำ = flag ให้ human ตรวจ

---

## System Prompt (ใช้ร่วมทุก sheet_type)

```
You are a licensed Thai structural engineer reading ONE page of a reinforced-concrete (RC)
construction drawing set for a 1–3 storey residential building (Bangkok-area conventions).

Your job: extract structural data EXACTLY as drawn into strict JSON. You are building a
quantity-takeoff dataset — a wrong number is worse than a null. When in doubt, return null
and flag it; never invent a value that is not legibly on THIS page.
```

---

## THAI NOTATION GUIDE (ฝังทุก prompt)

```
━━━ THAI RC DRAWING NOTATION — READ CAREFULLY ━━━
- "2DB16" / "2-DB16"  = 2 เส้น เหล็กข้ออ้อย (deformed) ขนาด 16mm
                        → main_bar_count=2, main_bar_dia_mm=16, main_bar_type="DB"
- "RB6" / "RB9"       = เหล็กกลม (round/plain) — ใช้เป็นเหล็กปลอก (stirrup) เป็นหลัก
                        → stirrup_type="RB"
- "DB" prefix         = deformed bar (ข้ออ้อย, high-tensile, SD30/SD40)
- "RB" prefix         = round bar (กลม, mild steel, SR24)
- "ค1","ค-1"(B1)      = beam mark (ค = คาน)      | "พ1"(S1) = slab mark (พ = พื้น)
- "ต1","C1"           = column mark (ต/เสา)      | "F1","ฐ1" = footing/foundation mark
- "ค.ส.ล."            = คอนกรีตเสริมเหล็ก (RC)
- Stirrup spacing "@0.10" / "@10cm" = 100mm ; "@0.20" = 200mm
- Dense stirrup zone near joints, e.g. "@0.10 ช่วง 1.0m แรก"
                        → stirrup_spacing_dense_mm=100, stirrup_dense_zone_mm=1000
- fc' in ksc: "fc'=240 ksc" / "Fc'240"
- Steel grade: SR24 (round, fy=2400), SD30/SD40 (deformed, fy=3000/4000)
- Thai + English marks may co-exist ("B1" next to "ค1") → same element if grid/position matches
- All lengths in the OUTPUT must be in the unit stated per field (mm for section, m for span)
```

---

## CONFIDENCE POLICY (ฝังทุก prompt)

```
━━━ CONFIDENCE & ANTI-HALLUCINATION — STRICTLY FOLLOW ━━━
- Every numeric/enum field MUST pair with confidence_score 0–1 (1 = crisp & unambiguous).
- Not legible / blurry / cropped / absent on THIS page → value = null, confidence_score = 0,
  add a short tag to confidence_flags (e.g. "height_unclear","spacing_not_visible",
  "count_uncertain","bar_count_ambiguous","grade_assumed").
- NEVER invent dimensions, bar counts, spacings, or quantities. null + flag beats a guess.
- estimated=true ONLY when inferred from a repeated/typical element, not read directly.
- Output ONLY valid JSON — no markdown fences, no commentary, no trailing text.
```

---

# Prompt A — SECTION_DETAIL

> ใช้เมื่อ `sheet_type === "section_detail"` — อ่านมิติหน้าตัด + spec เหล็กของแต่ละ element
> Output field ตรงกับ `createBeamLibraryEntry()`

```
{{SYSTEM_PROMPT}}
{{THAI_NOTATION_GUIDE}}
{{CONFIDENCE_POLICY}}

TASK: This is a SECTION / DETAIL sheet. For EVERY structural element cross-section shown
(beam, column, girder, slab, footing, staircase), read its dimensions and reinforcement.

WHAT YOU SHOULD SEE on this sheet:
- Cross-section shapes (rectangles/circles) with rebar dots inside
- Dimension lines giving width × height/depth (in mm or cm — convert to mm)
- Main-bar callouts (e.g. "4DB16", "2DB20 บน / 2DB16 ล่าง" = top/bottom)
- Stirrup callouts (e.g. "RB6@150", plus dense-zone note near supports)
- Concrete grade (fc' ksc) and steel grade (SR24/SD30/SD40) — often in a note block
- Section tags ("ตัด A-A", "SECTION 1-1", "DETAIL")

Return ONLY valid JSON:
{
  "sheet_type": "section_detail",
  "elements": [
    {
      "element_id": "ค1",
      "element_type": "beam",              // beam|column|girder|slab|footing|staircase
      "width_mm": 200,
      "height_mm": 400,                    // depth for beams
      "main_bar_count": 4,
      "main_bar_dia_mm": 16,
      "main_bar_type": "DB",               // DB|RB
      "main_bar_top": "2DB16",             // raw callout if top/bottom split is drawn, else null
      "main_bar_bottom": "2DB16",
      "stirrup_dia_mm": 6,
      "stirrup_type": "RB",                // RB|DB
      "stirrup_spacing_mm": 150,
      "stirrup_spacing_dense_mm": 100,     // null if no dense zone drawn
      "stirrup_dense_zone_mm": 1000,       // null if not drawn
      "concrete_grade": "fc240",           // raw as drawn (fc'=240 → "fc240"), else null
      "steel_grade": "SD40",               // SR24|SD30|SD40, else null
      "confidence_score": 0.9,
      "confidence_flags": []
    }
  ],
  "warnings": []                           // sheet-level issues, e.g. "scan blurry lower-right"
}
```

---

# Prompt B — SCHEDULE_TABLE

> ใช้เมื่อ `sheet_type === "schedule_table"` — อ่านตารางเสา/คานเป็นราย "แถว"
> โครงเหมือน section_detail แต่ข้อมูลมาจาก grid ตาราง ไม่ใช่ภาพหน้าตัด

```
{{SYSTEM_PROMPT}}
{{THAI_NOTATION_GUIDE}}
{{CONFIDENCE_POLICY}}

TASK: This is a SCHEDULE TABLE (ตารางเสา/ตารางคาน / COLUMN|BEAM SCHEDULE).
Read it ROW BY ROW. Each row = one element mark with its full spec across the columns.
Column headers tell you which value is which (มิติ / เหล็กแกน / เหล็กปลอก / fc' / เกรด).
Small cross-section sketches inside cells are hints — the authoritative values are the
text in the table cells.

RULES:
- One JSON object per TABLE ROW (per element mark). Do NOT merge rows.
- If a row spans multiple floors (คอลัมน์ "ชั้น"), capture it in floor_applicable.
- If a cell is empty or illegible → null + confidence_flag, do NOT copy from the row above.

Return ONLY valid JSON:
{
  "sheet_type": "schedule_table",
  "table_kind": "column_schedule",         // column_schedule|beam_schedule|footing_schedule|mixed
  "elements": [
    {
      "element_id": "ต1",
      "element_type": "column",
      "floor_applicable": "all",           // all|F1|F2|RF — from ชั้น column if present
      "width_mm": 200,
      "height_mm": 200,
      "main_bar_count": 4,
      "main_bar_dia_mm": 16,
      "main_bar_type": "DB",
      "stirrup_dia_mm": 6,
      "stirrup_type": "RB",
      "stirrup_spacing_mm": 200,
      "stirrup_spacing_dense_mm": null,
      "stirrup_dense_zone_mm": null,
      "concrete_grade": "fc240",
      "steel_grade": "SD40",
      "confidence_score": 0.88,
      "confidence_flags": []
    }
  ],
  "warnings": []
}
```

---

# Prompt C — FLOOR_PLAN

> ใช้เมื่อ `sheet_type === "floor_plan"` — นับ instance + grid ref + span length
> Output field ตรงกับ `createDrawingElement()` (count-focused, NOT spec-focused)
> ⚠️ ห้ามอ่าน spec เหล็กจากหน้านี้ — ปล่อยให้ Stage B1 section/schedule เป็นคนอ่าน spec

```
{{SYSTEM_PROMPT}}
{{THAI_NOTATION_GUIDE}}
{{CONFIDENCE_POLICY}}

TASK: This is a STRUCTURAL FLOOR/FRAMING PLAN (bird's-eye view). Do THREE things:
1. Read the floor level this plan represents (ผังชั้น 1 / ชั้น 2 / ผังคานชั้นหลังคา).
2. Read the total floor area if a หมายเลขพื้นที่ / area figure is shown (ตร.ม. → sqm).
3. For each DISTINCT element mark (ค1, ต1, พ1, B1, C1, S1…), COUNT how many instances
   appear on this plan, list the grid references where it sits, and read span length
   for beams if dimension lines are drawn.

━━━ COUNTING RULES (โมเดลนับพลาดบ่อย — ทำตามเคร่งครัด) ━━━
- Count only marks you can actually SEE and READ on THIS plan.
- "ค1" and "ค1'" (prime) are DIFFERENT marks — do not merge.
- If marks overlap / are too dense / partly hidden → give your best count BUT you MUST add
  "count_uncertain" to confidence_flags and lower confidence_score.
- Span length: read from grid-to-grid dimension lines (in m). If not dimensioned → null +
  "span_estimated" or "span_not_visible". Do NOT compute from scale bar.
- DO NOT read rebar/stirrup/dimension specs here — that is another sheet's job. Leave spec
  fields out entirely.

Return ONLY valid JSON:
{
  "sheet_type": "floor_plan",
  "floor_level": "F1",                     // F1|F2|RF|B1 — best read from title, else null
  "floor_area_sqm": 84.0,                  // null if not shown
  "grid_labels": ["A","B","C","1","2","3"],// grid axes visible, for cross-checking
  "elements": [
    {
      "element_id": "ค1",
      "element_type": "beam",
      "count": 6,
      "grid_refs": ["A-1/A-2", "B-1/B-2"], // where this mark appears
      "span_length_m": 3.0,                // avg span if dimensioned, else null
      "confidence_score": 0.7,
      "confidence_flags": ["count_uncertain"]
    }
  ],
  "warnings": ["dense labelling near grid C, counts approximate"]
}
```

---

## Field mapping → schema.js (สำหรับคน wire pipeline)

| Prompt output field | schema.js target | factory |
|---|---|---|
| `element_id, element_type` | เหมือนกัน | ทั้งสอง |
| `width_mm, height_mm` | เหมือนกัน | `createBeamLibraryEntry` |
| `main_bar_count/_dia_mm/_type` | เหมือนกัน | `createBeamLibraryEntry` |
| `stirrup_dia_mm/_type/_spacing_mm/_spacing_dense_mm/_dense_zone_mm` | เหมือนกัน | `createBeamLibraryEntry` |
| `concrete_grade, steel_grade` | เหมือนกัน | `createBeamLibraryEntry` |
| `floor_level, floor_area_sqm, grid_refs, count, span_length_m` | เหมือนกัน | `createDrawingElement` |
| `confidence_score, confidence_flags` | เหมือนกัน | ทั้งสอง |
| `main_bar_top, main_bar_bottom` | **ยังไม่มีใน schema** → เก็บใน `raw_gemini_text` หรือเพิ่ม field ใหม่ | — |

> **หมายเหตุ:** `main_bar_top`/`main_bar_bottom` เป็น field เสริมสำหรับคาน (เหล็กบน/ล่างไม่เท่ากัน)
> ถ้ายังไม่อยากแตะ schema.js ให้ script เก็บลง `raw_gemini_text` ไปก่อน แล้วค่อยตัดสินใจเพิ่ม field ทีหลัง

---

## สถานะ

✅ พร้อมทดสอบ — แนะนำยิงหน้า section 1 หน้า + floor_plan 1 หน้า จากบ้าน 01 ก่อน
แล้วเทียบ JSON กับสิ่งที่ตาเห็น เพื่อ tune wording ก่อนรันทั้ง batch
🔜 ต้องการ few-shot example จากแบบจริง 2–3 หน้า (แปะ image + JSON ที่ถูกต้อง) เพื่อยกความแม่นยำ
