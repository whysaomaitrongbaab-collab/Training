# _common.md — shared rule block

Prepend this block to **every** Pass 2 and Pass 3 extraction prompt. Pass 0 does not use it
(Pass 0 classifies, it does not extract).

Every rule here is taken from `primary_rawjson_schema.md`; the section numbers point back to it.
Do not add a rule here that is not in that spec, and do not restate a rule differently — if a
prompt and the spec disagree, the spec wins and the prompt is the bug.

---

## BLOCK START

You are extracting structured data from a Thai reinforced-concrete construction drawing.
Output **one JSON object and nothing else** — no prose before or after, no markdown fence.

### Output shape

Put drawing content in `elements[]`. Two exceptions only (§0.1):
- a grid file uses `grid{ ... }`
- a bill of quantities uses `categories[].items[]`

**Never name an array after the kind of element it holds.** `beams[]`, `columns[]`, `slabs[]`,
`footing_types[]`, `structural_elements[]` are forbidden — the kind belongs in `element_type`.

Every file carries these wrapper fields (§2):

```
png, doc_page, discipline, sheet_code, sheet_name, pattern,
source_image, confidence_score, confidence_flags, warnings
```

`discipline` is one of (§2): `structural` · `architectural` · `sanitary` · `electrical` ·
`mechanical` · `boq` · `material_list` · `general` · `front_matter` · `regulatory` · `misc`.
Write `architectural`, never `architecture`.

Never emit a `phase_note` field (§2a).

### Every element carries four fields (§0.2)

```json
{ "element_id": "...", "element_type": "...", "confidence_score": 0.9, "confidence_flags": [] }
```

`confidence_score` is `null` when the sheet gave you nothing to judge by. **Never invent a number
to fill it** — an honest `null` beats a made-up score.

### `element_id` is the mark printed on the drawing, nothing else (§0.3)

- Exactly as printed: `"B1"`, `"F1.30x1.30"`, `"C1A"`.
- No position suffix (position lives in `grid_refs`), no level suffix (use `level`), no
  section suffix (use `section_ref`).
- Unmarked thing → a descriptive id (`"ceiling_fan_นอน1"`). Never leave it absent.
- Two different members must never share an `element_id` on one sheet.

### `element_type` — reuse, do not invent (§0.4)

`beam` · `column` · `footing` · `pile` · `pile_cap` · `pedestal` · `slab` · `tie_beam` ·
`rafter` · `stair` · `room` · `room_cut` · `door` · `window` · `wall` · `dimension` ·
`dimension_chain` · `dimension_note` · `level` · `datum` · `note` · `symbol` ·
`symbol_legend_entry` · `sheet_index_entry` · `detail_view` · `section_view` · `plan_view` ·
`precast_plank_detail` · `sanitary_fixture` · `vent_pipe` · `fitting` · `accessory` ·
`furniture` · `gate_component` · `railing_component` · `electrical_outlet` ·
`ceiling_downlight_point` · `ceiling_fan` · `design_criterion` · `steel_member` ·
`connection_detail` · `installation_detail`

Only invent a value when none of these fits, and say so in `warnings[]` when you do.

### Numbers (§0.5)

- Member size → `width_mm`, `height_mm`, `thickness_mm`, `depth_mm` as **integer millimetres**.
- Never a packed string: `"0.20x0.40"` → `width_mm: 200, height_mm: 400`.
- Positions stay in **metres** as numbers: `level_m`, `span_length_m`, `pos_m`.
  `"+0.60"` → `level_m: 0.6`. `"±0.00"` → `level_m: 0.0`.
- Multi-span member → `spans_m[]`. `span_length_m` is always a single number.
- Printed `4+4` → `count` = the sum, printed text in `count_printed_as`.
- Printed `16+12` → `dia_mm` = first, `mixed_dia_mm` = the list, text in `dia_mm_printed_as`.
- Variable stirrup spacing → `spacing_mm` = the smallest, `variable_spacing: true`, detail in `note`.

### Rebar is always an object, never a string (§0.6)

Wrong: `"main_bar": "2-Ø16มม. top"`, `"stirrup": "Ø6มม.@0.20ม."`

- `stirrup` is the only name — `tie`, `tie_bar`, `stirrup_or_tie` are forbidden spellings.
- Spacing is `spacing_mm`, an integer.
- `Ø` → `type: "RB"`.
- `main_bar` / `stirrup` / `rebar` / `steel_section` are **single objects, never arrays**.
  Multi-layer reinforcement goes in `bar_layers[]`, each layer carrying its own `location`.

<!-- GLOSSARY START -->
### Thai → field glossary (not a rule — a lookup)

The drawing is Thai; this prompt and every value you emit are English. These are the Thai words
that actually appear on our sheets and what each one controls. Use it to *read*, never to
*rewrite*: the rule directly below still holds — a printed label stays Thai, verbatim.

**Words that decide `element_type`**

| printed | `element_type` | | printed | `element_type` |
|---|---|---|---|---|
| คาน | `beam` | | ฐานราก, ฐานรากแผ่ | `footing` |
| คานคอดิน | `tie_beam` | | ฐานรากเสาเข็ม, ฐานรากเข็มตอก | `pile_cap` |
| อะเส, ทับหลัง, ตง | `beam` | | เสาเข็ม, เข็ม | `pile` |
| เสา | `column` | | ตอม่อ | `pedestal` |
| เสาเอ็น, เอ็น | `column` | | พื้น | `slab` |
| จันทัน | `rafter` | | แผ่นพื้นสำเร็จรูป | `precast_plank_detail` |
| บันได | `stair` | | ผนัง | `wall` |
| ประตู | `door` | | หน้าต่าง | `window` |
| ห้อง… (ห้องนอน, ห้องน้ำ, ครัว, โถง, เฉลียง, ระเบียง, ซักล้าง, จอดรถ) | `room` | | หมายเหตุ | `note` |
| รูปตัด | `section_view` | | แบบขยาย | `detail_view` |
| ผัง, แปลน | `plan_view` | | ระดับ (เป็นตัวเลขบนแบบ) | `level` |

A Thai word not in this table is not permission to invent an `element_type` — pick the closest
value from §0.4 and say so in `warnings[]`.

**Words that decide a field**

| printed | field | | printed | field |
|---|---|---|---|---|
| ขนาด | `width_mm` × `height_mm` | | ระดับ | `level_m` |
| กว้าง | `width_mm` | | จำนวน, ต้น | `count` |
| ยาว, ช่วง | `span_length_m` | | เหล็กเสริม, เหล็กหลัก | `main_bar` |
| หนา | `thickness_mm` | | เหล็กบน / เหล็กล่าง | `location: "top"` / `"bottom"` |
| สูง | `height_mm` | | ปลอก, เหล็กปลอก, รัดรอบ | `stirrup` |
| ลึก | `depth_mm` | | @ , ระยะ (ตามด้วยเลข) | `spacing_mm` |
| ตะแกรง | `bar_layers[]` | | ระยะหุ้ม | `cover_mm` |
| กลม, Ø | `type: "RB"` | | ข้ออ้อย, DB | `type: "DB"` |
| ตลอด | ต่อเนื่องทั้งช่วง — ใส่ใน `note` | | งอ, ขอ, ทาบ | รายละเอียดปลาย/ทาบ — `note` |

**Units and abbreviations**

`มม.` = mm · `ซม.` = cm (×10 → mm) · `ม.`, `เมตร` = m · `นิ้ว` = inch ·
`ตร.ม.` = m² · `ลบ.ม.` = m³ · `กก.` = kg · `คสล.` = reinforced concrete ·
`มอก.` = TIS standard number · `ชั้นล่าง` = ground floor · `ชั้นบน` = upper floor

<!-- GLOSSARY END -->
### Keep the drawing's own words (§0.7)

Whenever you convert something printed — a size string, a rebar callout, a level — keep the
original verbatim in a sibling `*_printed_as` field. Thai stays Thai. Never translate a printed
label.

### `grid_ref` notation — one way only (§0.8)

| meaning | write | never |
|---|---|---|
| a point (footing, column, beam end) | `"C1"`, `"ค1"`, `"E'1"`, `"C3''"` | `"C-1"`, `"1-C"` |
| a range on one axis | `"D-C"`, `"1-2"` | — |
| a 2-axis area, **vertical axis first** | `"D-C x 1-2"` | `"1-2 x D-C"` |
| approximate | `"~A1"` | `"near grid A1"` |

The words `grid` and `dummy` never appear inside a `grid_ref` value. Row letters keep the
drawing's own alphabet — Thai `ก`/`ข`/`ค` stays Thai.

### The honesty rules — these outrank being complete

1. **Never guess a measurement.** If a dimension is not printed, do not estimate it from how the
   drawing looks. Leave the field `null` and say why in `warnings[]`.
2. **Never drop something you could not read.** An element you can see but cannot fully resolve
   still gets an entry, with the unreadable fields `null` and a `confidence_flags` entry saying
   what was unreadable.
3. **Never repeat an entry to fill space.** If you find yourself emitting the same element over
   and over with only the grid reference changing, stop and close the JSON — a short honest
   answer is correct, a long repetitive one is not.
4. `warnings[]` is where you talk to the human. Use it for anything blurred, ambiguous,
   contradictory between sheets, or that you had to make a judgment call on.

## BLOCK END
