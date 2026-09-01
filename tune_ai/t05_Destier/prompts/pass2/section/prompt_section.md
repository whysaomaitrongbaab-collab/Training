# pass2_section.md - detail sections (rebar specs)

**Input:** one section-sheet image (a detail cut through a member).
**Output:** one `pattern: "section"` file.

Does **not** need the grid master - a section is a cut through a member, it has no plan axes.

This is where the numbers that become steel weight come from. A wrong bar count here is wrong
everywhere downstream, and unlike a missing element it will not look wrong.

Prepend `../../_common.md`.

---

## PROMPT START

You are reading a detail-section sheet Extract the size and reinforcement of every member
detailed on it

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
  "png": "24",
  "doc_page": 24,
  "discipline": "structural",
  "sheet_code": "S-07",
  "sheet_name": "รายละเอียดคานและเสา",
  "pattern": "section",
  "source_image": "image/<house>/<house>_หน้า24.png",
  "elements": [ ... ],
  "confidence_score": 0.9,
  "confidence_flags": [],
  "warnings": []
}
```

A reinforced-concrete member

```json
{
  "element_id": "B1",
  "element_type": "beam",
  "width_mm": 150,
  "height_mm": 300,
  "main_bar": {
    "top":    { "count": 2, "dia_mm": 16, "type": "DB" },
    "bottom": { "count": 3, "dia_mm": 16, "type": "DB" }
  },
  "stirrup": { "dia_mm": 6, "type": "RB", "spacing_mm": 150 },
  "additional_bars": [],
  "concrete_grade": "fc240",
  "steel_grade": "SD40",
  "main_bar_printed_as": "2-DB16 บน, 3-DB16 ล่าง",
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

`element_id` = the mark printed on the drawing, or `null` - never an invented name
A cross-section labelled `B1` or `C1` takes that mark verbatim A detail with no printed mark
at all (a gate detail, a pipe sleeve, a generic wall section) takes `element_id: null` - do NOT
invent a descriptive name for it, the rest of the fields (`element_type`, dimensions,
reinforcement) still describe it fully

Rebar rules (§6) - the ones that have been got wrong before

Beams split `top` / `bottom` always, even when the two are equal Never collapse a symmetric
beam into one count Genuine top and bottom differ in real cases and merging destroys them

A column NEVER uses `top`/`bottom` - a single `count` only

```json
"main_bar": { "count": 4, "dia_mm": 12, "type": "RB" }
```

A column has bars around its corners, printed as one figure (`4-Ø12มม.`) Writing it as
top 4 bottom 4 silently doubles the real count to 8 This applies to structural columns,
pedestals (ตอม่อ), short columns (`C0`/`CN`) and fence columns alike

`middle` - only for a genuinely distinct mid-depth row A deep beam sometimes shows a third
bar row at mid-depth with its own leader line and its own row of dots between the top and bottom
clusters (skin/waist bars) That is `main_bar.middle` Do not invent one by splitting a top or
bottom cluster, and do not use it for a bar that is merely drawn between the clusters but whose
leader ties it to the top or bottom face

`additional_bars[]` is only for bars belonging to no longitudinal face at all - a standalone
tie or dowel A mid-depth longitudinal row is `main_bar.middle`, not an additional bar

Read `position` off the actual leader line, never off the label text alone, and never by analogy
to how a similar-looking mark resolved elsewhere Two same-looking labels on the same sheet have
been found to mean opposite faces

`Ø` always means `type: "RB"` Never infer bar type from diameter A deformed bar with visible
ribs is `DB`

`stirrup` is the only name for it - `tie`, `tie_bar`, `stirrup_or_tie` are forbidden spellings
Spacing is `spacing_mm` as an integer, `@0.20ม.` is not a value

Variable stirrup spacing (`@0.10` at the ends, `@0.25` mid-span) means `spacing_mm` = the
smallest, `variable_spacing: true`, and the detail in `note`

A structural steel member (§6a)

A steel member has no `main_bar` or `stirrup` at all

```json
{
  "element_id": "GB1",
  "element_type": "beam",
  "material": "steel",
  "steel_section": {
    "designation": "WF",
    "d_mm": 400, "b_mm": 200, "tw_mm": 8, "tf_mm": 13,
    "printed_as": "WF 400x200x8x13 มม."
  },
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

- `designation` is the printed family verbatim - `WF`, `C`, `L`, `RHS`, `SHS`, `Pipe` Never
  translate to a foreign standard (no H-beam, no W14x)
- `WF`/`C` print four numbers in the order depth, flange width, web thickness, flange thickness
  A lipped channel with five numbers adds `lip_mm` before the thickness
- `element_type` stays semantic (`beam`, `column`, `purlin`) - the material is carried by
  `steel_section` being present
- Repeated members at a spacing (purlins at `@0.40 ม.`) put it in `spacing_mm`, the same field
  name the rebar side uses

A member has either rebar or `steel_section`, never both A hybrid building - steel frame on
RC footings - is normal, the RC parts keep rebar fields, the steel frame above uses
`steel_section`

Dimensions

Member sizes are integer millimetres `width_mm`, `height_mm`, `thickness_mm`, `depth_mm`
Never a packed string (`"0.20x0.40"` becomes `width_mm: 200, height_mm: 400`), never a metre
variant of a member dimension Keep the printed text in a `*_printed_as` sibling

Rules

- `element_id` exactly as printed, with no suffix for the cut label - put that in `section_ref`
  (§0.3)
- One entry per member detailed on the sheet The same mark detailed twice on one sheet, showing
  genuinely different things, keeps whatever suffix distinguishes them
- A dimension that is not printed is `null` Do not scale it off the drawing A section is
  drawn to a scale you cannot verify from the image, and an estimated bar count or member depth is
  worse than an honest gap
- No positions or counts of instances here - those come from the plan sheets and join by
  `element_id` later (§7)

## PROMPT END
