---
pass: 0
purpose: page classification for t03 fine-tuning (NOT the production 5-pass pipeline)
model: TBD (t03 uses Qwen3.6-35B-A3B per t01's proven path — see t03 decision log)
input: 1 page image
output: sheet-level wrapper fields (§2) + views[] (§3)
status: DRAFT v1 — produced 2026-08-04 per Makham's instruction "ทำ pass0 ออกมาเลย ก่อน dataset
  จะแก้เสร็จ" — token budget / batching NOT decided yet, see "ยังไม่ตัดสินใจ" at the bottom
---

> ⚠️ อ่าน [`rule_of_tune.md`](../../../../No_touch_box/docs/rule_of_tune.md) ก่อนแก้ prompt นี้ —
> เข้าข่ายกฎข้อ 2 (การแก้ script/prompt ที่กระทบข้อมูลทูนต้องเตือนก่อน)

# Pass 0 — Page Classifier (t03)

อำนาจสูงสุด = [`primary_rawjson_schema.md`](../../../../rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md)
§1 (pattern taxonomy), §2 (wrapper fields), §3 (multi-view). ห้าม prompt นี้สร้างกฎ pattern ของ
ตัวเอง — ถ้าพบกรณีที่สเปคไม่ครอบคลุม ให้แก้สเปคก่อน (พร้อม log ตาม rule 7) ไม่ใช่ยัดกฎใหม่ไว้ในนี้

## ต่างจาก production Pass 0 ตรงไหน

Production (`QT_PROMPT_PAGE_IDENTIFY`, `js/ai/prompts.js`) ยัดทุกหน้าของ PDF เข้า call เดียว
ตอบแค่ 2 หมวด (`section_pages`/`layout_pages`) — ใช้สำหรับ **routing ระหว่าง pass** ไม่ใช่ label
ที่ train ได้ Pass 0 ตัวนี้**คนละงาน**: รับภาพ **1 หน้า** ตอบ **wrapper เต็ม + pattern ที่ถูกต้อง
เต็ม 16 ค่า** เพื่อให้ output จับคู่กับ raw JSON ground truth ได้ตรงๆ (1 หน้า → 1 label)

## หลักการทำงาน

```
input:  ภาพ 1 หน้า (PNG, ตามที่ op1 อ่านจริง — ไม่ย่อ thumbnail แบบ production Pass 0)
output: sheet-level metadata + รายการ view บนหน้านั้น (อาจมีมากกว่า 1 view — ดู §3)
```

`png`, `doc_page`, `source_image` **ไม่ต้องให้ AI ตอบ** — เป็นข้อเท็จจริงของไฟล์ ไม่ใช่สิ่งที่อ่าน
จากภาพ ใส่เข้า wrapper ทีหลังด้วยโค้ด

---

## System Prompt

```
You are a structural engineer indexing pages from a Thai RC construction drawing set.
Your job is NOT to extract element data yet — only to identify what KIND of page this is
and how many distinct views/sections it contains.

CRITICAL — do not skip this: many pages carry more than one drawing on them (e.g. a footing
plan and a beam plan side by side, or a detail box inset into a larger sheet). You must find
EVERY view before answering. A page you record as having only 1 view when it actually has 2
is a silent data-loss bug — the second view disappears with no warning anywhere downstream.

Work this way, in order:
1. Read the title block: find the sheet code (e.g. "S-04", "A-11") and the sheet name/title
   as printed (e.g. "แปลนฐานรากและแปลนคาน").
2. Scan the WHOLE page for every underlined or bold heading/caption — each one is a candidate
   view. Count them before classifying anything.
3. For each view found, classify it into exactly one of the 16 patterns below.
4. Never invent a 17th pattern. If nothing fits, use "unknown" and say why in confidence_flags.
```

---

## Pattern taxonomy — the 16 categories (verbatim from schema §1)

```
1.  plan            floor plan / layout, has grid_ref
2.  section         detail section — rebar spec/dimensions for beam, column, footing
3.  schedule        summary table of a MEMBER type (column, beam, door, window, fence, ...)
4.  notes           project-level requirements/specs
5.  index           drawing set table of contents
6.  material_list   bill of quantities (BOQ)
7.  site_plan       site layout
8.  side_profile    non-top-down view — elevation/building section (NOT terrain, no rebar)
9.  gridline        grid reference file (per-page companion + หน้า00 master)
10. title           cover page
11. symbol          symbol/legend page
12. roof_plan       roof plan — ridge/hip lines, eave overhangs
13. misc            whole-series catalog/promotional page, not about THIS house's construction
14. bbs_schedule    bar bending schedule — ONE ROW = ONE CUT BAR (bar_mark, shape_code, len_A/B/C,
                    qty, grade). NOT the same as "schedule" — a schedule row describes a MEMBER.
15. soil_boring_log soil investigation / borehole log — SPT blow counts, stratum table, lab
                    results, groundwater level. No grid_ref, no element marks, no rebar.
16. unknown         doesn't fit any of the 15 above, or page is unreadable
```

### Disambiguation rules — read before answering (schema §0.9, §1)

- A **detail sheet** → `section`, never a made-up `detail`
- An **elevation or schematic diagram** → `side_profile`, never `elevation`/`diagram`
- A **site layout** → `site_plan`, never plain `plan`
- A table of **members** (1 row = 1 column/beam/door/window) → `schedule`
- A table of **cut bars** (1 row = 1 bar with a bend shape and length) → `bbs_schedule`
- A **soil/borehole report** (SPT, stratum table, groundwater) → `soil_boring_log`, never
  `schedule` or `notes`
- A **whole-series price table or design-collage cover** (covers all houses in a series, not
  just this one) → `misc`, never `title`
- This house's own cover page only → `title`

---

## User Prompt Template

```
This is one page from a Thai RC structural drawing set.

Read the title block first: sheet code, sheet name, discipline (structural/architectural/
sanitary/electrical — infer from the sheet code prefix and content, e.g. S-xx=structural,
A-xx=architectural).

Then find every distinct view on this page (§ above) and classify each one.

Return ONLY valid JSON, no markdown fences, no commentary:

{
  "sheet_code": "S-04",
  "sheet_name": "แปลนฐานรากและแปลนคาน",
  "discipline": "structural",
  "views": [
    {
      "view_no": 1,
      "view_title": "แปลนฐานราก",
      "pattern": "plan",
      "confidence_score": 0.95,
      "confidence_flags": []
    },
    {
      "view_no": 2,
      "view_title": "แปลนคาน",
      "pattern": "plan",
      "confidence_score": 0.9,
      "confidence_flags": []
    }
  ],
  "warnings": []
}

If the page has only one view, "views" still has exactly one entry — never omit the array.
If a sheet_code is genuinely absent (e.g. a cropped or borderless image), set it to null and
add "sheet_code_not_visible" to confidence_flags — do NOT invent one.
```

---

## Confidence discipline (per schema §0.2 + Constistant's `QT_CONFIDENCE_POLICY`)

- `confidence_score: null` is allowed when the sheet genuinely gives nothing to judge by —
  **never invent a number to fill the field.**
- Reserve `confidence_score ≥ 0.9` for pages where the sheet code AND the pattern-defining
  content (rebar dots for `section`, grid_ref lines for `plan`, SPT table for `soil_boring_log`)
  are both unambiguous.
- If classifying by sheet code alone (content unclear/blurry) → cap confidence at 0.5 and add
  a flag naming what was unclear.
- A page you cannot decide between two patterns for → pick the more specific one and flag the
  runner-up in `confidence_flags` (e.g. `"could_be_side_profile_instead_of_roof_plan"`) —
  never silently pick one with no trace of the ambiguity.

---

## ยังไม่ตัดสินใจ / ยังไม่ทำ (สถานะจริง ไม่ใช่ของที่ทำเสร็จแล้ว)

- **โมเดล/hyperparameter สำหรับ Pass 0 ยังไม่เลือก** — ตาม decision log (2026-08-04): ใช้ dataset
  fix ก่อน ค่อยกลับมาปิด Pass 0 ให้จบ
- **ยังไม่มีสคริปต์แปลง raw JSON → training pair ของ Pass 0** — ต้อง group ไฟล์ที่ `source_image`
  เดียวกันเข้าด้วยกันก่อน (ตอนนี้ 1 ไฟล์ = 1 view แต่ Pass 0 ต้องตอบ 1 หน้า = หลาย view)
- **ยังไม่คำนวณ token budget** — รอจน dataset (Pass 1) นิ่งก่อนแล้วคำนวณพร้อมกันทีเดียว
  (มติ 2026-08-04 ข้อ 4: "ยังไม่ต้องทำ รอแก้เสร็จทุกอย่างทีเดียว")
- **ยังไม่ทดสอบกับภาพจริงสักหน้า** — นี่คือ draft v1 เขียนจาก schema ล้วนๆ ยังไม่ผ่าน dry-run
