# Pass 3 — ถอดระยะ/เหล็ก จากบัญชี element ที่ยืนยันแล้ว

**สถานะ: เขียนเต็มแล้ว ยังไม่เคยรันจริงกับโมเดล** (ย้ายมาจาก `tune_ai/t03/pass3_takeoff/`
2026-08-28 — ที่อยู่ถาวรคือที่นี่ ใน t04 ไม่ใช่ t03 อีกต่อไป จะรันได้ต้องผ่านผลทดลอง
แขน 2 vs 2.4 ก่อน ดู [`../pass2.4_hint/`](../pass2.4_hint/))

**Input:** รูปมาร์คเลข (จาก [pass 1.5](../pass1.5_cv/)) + บัญชี element ฉบับสุดท้าย
(CV ∪ โมเดล จาก [pass 2.5](../pass2.5_harvest/)) + grid master + prompt นี้
(prepend `../../t03/_common.md` — glossary ไทยติดมาด้วย)

**กฎเหล็กของ pass นี้ — บังคับด้วยโค้ด ไม่ใช่แค่ prompt:**
[`tools/merge_guard.py::merge_no_delete()`](../../../tools/merge_guard.py) รันหลังโมเดลตอบเสมอ —
element ไหนในบัญชีที่โมเดลไม่ตอบ (ไม่มี `cv_mark` ตรงกัน) จะถูกใส่กลับเป็น stub + ธง
`dropped_by_pass3` ให้คนดู โมเดลจึง**ลบอะไรไม่ได้จริง** ต่อให้ prompt ล้มเหลว

**Runner ของ pass นี้ต้องเปิด xgrammar (builtin JSON) เสมอ** (มะขามสั่ง 2026-08-29 "ใส่ xgrammar
ทุก pass") — pass นี้ยิ่งจำเป็นกว่าเพื่อน: merge_guard ทำงานได้ก็ต่อเมื่อคำตอบ parse เป็น JSON ได้
ก่อน คำตอบที่ JSON พังเท่ากับ element ทั้งบัญชีกลายเป็น stub หมดทั้งหน้า ดูวิธี setup ที่
`infer_house_t03.py::setup_grammar()` (เปิดทุก subtask เป็นค่าปริยายแล้วที่นั่น)

---

## `{{ELEMENT_ACCOUNT}}` — รูปแบบบัญชีที่ป้อนเข้า prompt

Runner ดึง `elements[]` จาก sidecar ของ pass 2.5 (`<stem>_cv25.json`) มาเรียงเป็นบรรทัดข้อความ
หนึ่งบรรทัดต่อหนึ่ง element ตามลำดับ `n` เดิม (ห้ามเรียงใหม่ — เลขต้องตรงกับที่มาร์คบนภาพเป๊ะ)
รูปแบบ `เลข) class` — ไม่ใช้ `#` (กติกาห้ามอักขระ markdown ใน prompt, 2026-08-29):

```
1) column
2) column
...
15) footing
16) footing
...
29) beam_h
```

ชื่อ class (`column`/`footing`/`beam_h`/`beam_v`) เป็นแค่ป้ายบอกว่ากรอบนั้นเป็นไอคอนหน้าตาแบบไหน
**ไม่ใช่คำตอบสุดท้าย** — โมเดลยังต้องอ่านมาร์คจริงบนแบบ (เช่น F1 vs F2, C1 vs C1A) เอง ตาม
`_common.md` §0.4/§0.3

---

## PROMPT START

You are given (1) a Thai construction drawing image with numbered boxes marking elements a
computer-vision pass already found, and (2) the list below telling you what shape each numbered
box looks like (its coarse class, not its real mark)

{{ELEMENT_ACCOUNT}}

Your job - for every numbered box, find it on the image, read its real mark and dimensions, and
extract its full spec - size, span (for beams), and reinforcement

Output one JSON object and nothing else

Thai to field glossary (not a rule - a lookup)

The drawing is Thai, this prompt and every value you emit are English These are the
Thai words that actually appear on our sheets and what each one controls Use it to
read, never to rewrite the rule directly below still holds - a printed label stays
Thai, verbatim

Words that decide `element_type`

- คาน → `beam`
- คานคอดิน → `tie_beam`
- อะเส, ทับหลัง, ตง → `beam`
- เสา → `column`
- เสาเอ็น, เอ็น → `column`
- จันทัน → `rafter`
- บันได → `stair`
- ประตู → `door`
- ห้อง… (ห้องนอน, ห้องน้ำ, ครัว, โถง, เฉลียง, ระเบียง, ซักล้าง, จอดรถ) → `room`
- รูปตัด → `section_view`
- ผัง, แปลน → `plan_view`
- ฐานราก, ฐานรากแผ่ → `footing`
- ฐานรากเสาเข็ม, ฐานรากเข็มตอก → `pile_cap`
- เสาเข็ม, เข็ม → `pile`
- ตอม่อ → `pedestal`
- พื้น → `slab`
- แผ่นพื้นสำเร็จรูป → `precast_plank_detail`
- ผนัง → `wall`
- หน้าต่าง → `window`
- หมายเหตุ → `note`
- แบบขยาย → `detail_view`
- ระดับ (เป็นตัวเลขบนแบบ) → `level`

Words that decide a field

- ขนาด → `width_mm` and `height_mm`
- กว้าง → `width_mm`
- ยาว, ช่วง → `span_length_m`
- หนา → `thickness_mm`
- สูง → `height_mm`
- ลึก → `depth_mm`
- ระดับ → `level_m`
- จำนวน, ต้น → `count`
- ตะแกรง → `bar_layers[]`
- กลม, Ø → `type: "RB"`
- เหล็กเสริม, เหล็กหลัก → `main_bar`
- เหล็กบน / เหล็กล่าง → `location: "top"` / `"bottom"`
- ปลอก, เหล็กปลอก, รัดรอบ, ป. → `stirrup`
- @ , ระยะ (ตามด้วยเลข) → `spacing_mm`
- ระยะหุ้ม → `cover_mm`
- ข้ออ้อย, DB → `type: "DB"`
- ตลอด → ต่อเนื่องทั้งช่วง ใส่ใน `note`
- งอ, ขอ, ทาบ → รายละเอียดปลาย/ทาบ ใส่ใน `note`

Units and abbreviations

`มม` = mm · `ซม` = cm (×10 → mm) · `ม`, `เมตร` = m · `นิ้ว` = inch ·
`ตรม` = m² · `ลบม` = m³ · `กก` = kg · `คสล` = reinforced concrete ·
`มอก` = TIS standard number · `ชั้นล่าง` = ground floor · `ชั้นบน` = upper floor

A Thai word not in this list is not permission to invent an `element_type` - pick the closest value from §0.4 and say so in `warnings[]`

```json
{
  "png": "14",
  "doc_page": 14,
  "discipline": "structural",
  "pattern": "section",
  "source_image": "image/<house>/<house>_หน้า14.png",
  "grid_source": "<house>_หน้า00_gridline.json",
  "elements": [ ... ],
  "confidence_score": 0.9,
  "confidence_flags": [],
  "warnings": []
}
```

Every element you output carries `cv_mark` when it corresponds to a numbered box

```json
{
  "element_id": "F1",
  "element_type": "footing",
  "cv_mark": 15,
  "width_mm": 1000,
  "height_mm": 300,
  "grid_refs": ["A1"],
  "main_bar": { "count": 12, "dia_mm": 9, "type": "RB" },
  "stirrup": { "count": 1, "dia_mm": 9, "type": "RB" },
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

A fixed number of edge ties (for example `1-Ø9มม. รัดรอบขอบฐานราก`) goes in `stirrup.count` with
`spacing_mm` omitted - never a top-level `stirrup_tie_count`, which schema §6b forbids
(Constistant reads `stirrup.count` only when `spacing_mm` is absent, a repeating stirrup keeps
`spacing_mm` as usual)

A beam uses `span_length_m`/`grid_ref_start`/`grid_ref_end` from the grid master exactly as in
the beam plan prompt A footing or column uses `width_mm`/`height_mm`/`main_bar`/`stirrup`
exactly as in the section prompt This prompt does not redefine those field shapes - it only adds
`cv_mark` on top of them

Rules, in priority order

1) Never remove a numbered box from your output Every number in the list above appears in your
   output with that `cv_mark` If you cannot read anything about it (blurred, obstructed, or the
   box is a false positive with nothing there), output it anyway with all measurement fields
   `null` and a `confidence_flags` entry saying why - that is a correct answer, not a failure
   A guard program enforces this even if you get it wrong, but get it right anyway - a stub with
   no real data is worse than your own honest read
2) You may add elements the list missed - a real member the CV pass did not detect An added
   element has no `cv_mark`
3) Never invent a `cv_mark` Only use a number that appears in the list above Guessing a
   number that is not there is worse than leaving `cv_mark` off - the guard treats an unknown
   `cv_mark` as a warning-worthy anomaly, not a silent match
4) Two elements never claim the same `cv_mark` If two real members genuinely sit at one
   marked point (rare - a column-on-footing box drawn once for both), pick the element type the
   coarse class in the account most closely matches and note the other in `warnings[]`
5) Spans come from the printed grid dimensions via the grid master - never from how long a line
   looks alone (honesty rule 1) When a span is printed nowhere, recover it by proportion in two
   separate steps, never in one leap First find the pixels - P = the on-image separation of two
   same-axis grid lines with known `pos_m` (the pair furthest apart), U = the on-image length of
   the span itself Then convert - R = the difference of those two `pos_m` in metres, and the
   span is U divided by P, multiplied by R A printed value always wins, an x span uses the
   x-axis scale only and a y span the y-axis scale only, a diagonal stays `unresolved` Label
   the result `span_source` `scaled_from_grid` with a lower `confidence_score` and a
   `confidence_flags` entry carrying the two reference lines and both pixel numbers
   (`scaled_between:1,3 P:380 U:142`) - a human must be able to redo the arithmetic from the
   flag alone, and if you cannot state P and U you did not measure, so the span stays
   `unresolved` It is a derived number, not a read one, and whoever reads the file must be
   able to tell those apart
6) All the shared rules apply unchanged (element shape, units, rebar-as-object, honesty rules,
   Thai glossary)

## PROMPT END
