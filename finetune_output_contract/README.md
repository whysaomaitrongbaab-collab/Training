# finetune_output_contract — what the fine-tune model must output for Constistant

One folder, one contract. `templates/` is the shape the model must emit per pattern;
`examples/` is a real, human-corrected set (house 01, `json_แก้ไขแล้ว`) that forms a
coherent importable mini-house. If the model's output matches these files, every field
Constistant can consume will flow through; anything outside this contract is either
stored raw (invisible to BOQ/BBS) or dropped.

Full extraction rules live in
[`rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`](../rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md).
This README does not replace it — it adds the **consumer's view**: which fields
Constistant's import path actually reads, verified against
`Constistant/js/drawing/raw-extraction-adapter.js` + `raw-extraction-import.js`
(2026-08-28).

## How Constistant consumes these files

Import path: **นำเข้าไฟล์สกัดข้อมูล (JSON)** → `qt_importRawExtractionFiles()` →
`adaptRawExtraction()` → `buildEntitiesFromAdapted()` → `DrawingElement[]` /
`BeamLibraryEntry[]` / `GridReference` → `runPipeline()` (BOQ/BBS/Schedule/Resources).

Only **9 of the 19 patterns** are adapted: the whole plan family (`beam_plan`,
`footing_plan`, `roof_frame_plan`, `etc_plan` — split from the single `plan` value
2026-08-28, schema §1; the dead `plan` spelling is still accepted defensively), plus
`section`, `schedule`, `notes`, `gridline`, `material_list`. The other 10 (`index`,
`site_plan`, `side_profile`, `title`, `symbol`, `roof_plan`, `misc`, `bbs_schedule`,
`soil_boring_log`, `unknown`) are stored verbatim in the raw-extraction store with a
warning — they never reach a number the user sees.

## Field flow per pattern

### `gridline` (one master file per building, `หน้า00`)

| field | Constistant |
|---|---|
| `grid.x_lines[] / grid.y_lines[]` (`id`, `pos_m`, `type`) | ✅ consumed — the ONLY source of every beam span. Adapter accepts both nested `grid{}` and legacy top-level `x_lines`/`y_lines` |
| `source_pages[]` | ✅ consumed (provenance) |
| `grid.z_levels[]`, `grid.dimension_chains[]`, `grid.unassigned_dimensions[]` | ⚠️ stored raw, not read by any code yet — still REQUIRED by the schema (audit trail) |
| per-line `source`, `confidence_*` | ⚠️ stored raw only |

Every point `grid_ref` and every beam endpoint in every plan-family file must resolve
against this master — an unresolvable ref becomes `span_source: "unresolved"` and that
beam's concrete/steel is silently 0 in the BOQ.

### the plan family — `beam_plan` / `footing_plan` / `roof_frame_plan` / `etc_plan`

Wrapper: `floor_level` ✅ (missing → defaults to `F1` + warning — never omit on a real
sheet), `pattern` must be one of the four (schema §1). All four adapt **identically** —
the value tells a human and a future consumer what kind of sheet it is, and changes
nothing about how `elements[]` is read today. A structural roof-framing sheet is
`roof_frame_plan`; `roof_plan` files are NOT read at all and their beams vanish.

Per element:

| field | Constistant |
|---|---|
| `element_id`, `element_type` | ✅ consumed (join key + type) |
| `grid_ref_start` / `grid_ref_end` (line elements) | ✅ consumed — span recomputed from grid master; model-supplied `span_length_m` is ignored |
| `grid_refs[]` + implied `count` (point elements; duplicates deduped with warning) | ✅ consumed |
| `confidence_score`, `confidence_flags[]` | ✅ consumed |
| top-level `specs{}` object on the plan file | ❌ **NOT read.** Constistant builds specs ONLY from `section`/`schedule` files' `elements[]`. Keep emitting `specs{}` per schema §7 (audit trail), but every spec must ALSO exist as a `section` or `schedule` element or it is invisible |
| `count` on a schedule-style plan row, `description`, `section_ref`, `level_m`, `*_printed_as` | ⚠️ stored raw only |

### `section` and `schedule` (spec sources — equal priority, `section` wins conflicts)

Per element, the adapter whitelist (`SPEC_FIELDS`) passes exactly:

| field | Constistant |
|---|---|
| `element_id` | ✅ join key |
| `element_type`, `width_mm`, `height_mm`, `level` | ✅ consumed |
| `main_bar{}` (beam: `top`/`middle`/`bottom`; column: single `count` — never top/bottom) | ✅ consumed |
| `stirrup{}` → `dia_mm`, `type`, `spacing_mm`, `spacing_dense_mm`, `dense_zone_mm` | ✅ consumed (the last two are optional Constistant extensions for variable spacing — emit when the drawing prints a dense end zone) |
| `additional_bars[]`, `concrete_grade`, `steel_grade` | ✅ consumed |
| `confidence_score`, `confidence_flags[]` | ✅ consumed (per-spec) |
| `thickness_mm`, `depth_mm`, `steel_section{}`, `material`, `spacing_mm` (member spacing), `bar_layers[]`, `spans_m[]`, `*_printed_as` | ❌ **dropped by SPEC_FIELDS today** — keep emitting per schema; see Known gaps |

### `notes`

| field | Constistant |
|---|---|
| `notes.fc_ksc`, `notes.fy_main_ksc`, `notes.fy_stirrup_ksc`, `notes.cover_mm` (the four FLAT aliases) | ✅ consumed → `DrawingUpload.extracted_notes`. **These flat fields are the only thing read — a house whose notes file has only the nested objects delivers nothing.** Never omit them; `null` when the sheet doesn't specify |
| `sections[]`, nested `concrete{}`/`steel{}`/`cover{}` | ⚠️ stored raw only (audit trail — still required) |
| more than one `notes` file | first file wins, warning raised — put the four flat values in the structural notes file (`S-01`), not a sanitary one |

### `material_list`

| field | Constistant |
|---|---|
| `items[]` (flat, top-level) → `item_no`, `description`, `unit`, `quantity` | ✅ consumed → `boqSeed` |
| `categories[].items[]` (the shape the schema §0.1 mandates and every real house uses) | ❌ **NOT read — known adapter gap.** Until fixed, every real house's BOQ seed imports empty. See Known gaps |
| price columns (`material_unit_price` …), `confidence_*` per item | ⚠️ stored raw only |

## Known gaps — data the model emits correctly that Constistant does not see yet

These are **Constistant-side fixes**, not reasons to change the model's output. The
model keeps emitting per `primary_rawjson_schema.md`; this list is the work queue for
the pipeline side (the reason this folder exists).

1. **`material_list` container mismatch** — schema mandates `categories[].items[]`;
   `adaptRawExtraction()` reads only flat `f.items[]`. Result: `boqSeed` is empty for
   every schema-compliant house. Fix: adapter reads both.
2. **`steel_section{}` / `material` / member `spacing_mm` not in `SPEC_FIELDS`** — a
   steel-framed house (e.g. `บ้าน_ใหญ่_1ชั้น_01`) imports with no member specs at all.
   Schema §7 says these join; the whitelist predates §6a.
3. **Slab quantities are always 0** — `computeBOQ()` needs `floor_area_sqm`, but no
   raw-JSON field produces it (slab markers `SO`/`SI`/`ST` carry no boundary). Needs a
   decision: either the pipeline derives area from grid bays, or the schema grows a
   field. Today the import warns and the BOQ shows ฿0.00 rows.
4. **10 patterns stored raw only** — most importantly `bbs_schedule` and
   `soil_boring_log` (Constistant's Foundation Design reads soil data on the live-AI
   path but not on this import path), and `side_profile` (only source of Z levels).
5. **`grid.z_levels[]` / `dimension_chains[]` / `unassigned_dimensions[]` unused** —
   collected at real cost, consumed by nothing yet.
6. **Plan-file `specs{}` unread** — by design (specs come from section/schedule), but
   it means a spec that exists ONLY on a plan sheet must still be duplicated into that
   sheet's section/schedule extraction or it never reaches `BeamLibraryEntry`.
7. **`thickness_mm`/`depth_mm` dropped** — a slab or footing detailed with thickness
   instead of width×height loses its dimension (the pile-cap field miss fixed
   2026-08-25 was this class of bug).

## Acceptance checklist for a model-output house

1. Every file parses as standalone JSON — one object, nothing else (no markdown fence,
   no trailing prose). A truncated/unclosed file loses ALL its elements.
2. `python tools/check_format.py <house-folder>` exits 0.
3. Wrapper fields present on every file: `png`, `doc_page`, `discipline`,
   `sheet_code`, `sheet_name`, `pattern`, `source_image` (grid master:
   `source_pages`), `confidence_score`, `confidence_flags`, `warnings`.
4. Grid master exists and every point `grid_ref` / beam endpoint resolves against it.
5. Rebar is always the object form; columns single-`count`; dimensions integer mm;
   `element_id` exactly as printed (no position/level/section suffix).
6. `notes` file carries the four flat aliases.
7. Never invent values — `null` + `warnings[]` beats a guess. `confidence_score: null`
   when there is nothing to judge by.

## Folder contents

```
templates/                          minimal valid shape per pattern (placeholder values)
  gridline.template.json
  plan_line_element.template.json   beams — atomic segments, grid_ref_start/end
  plan_point_element.template.json  footings/columns — merged grid_refs[] + count
  section.template.json             beam + column spec elements
  schedule.template.json            multi-level column schedule (level field)
  notes.template.json               sections[] + notes{} with the four flat aliases
  material_list.template.json       categories[].items[] incl. continuation-row rule
examples/                           real, human-corrected files from house 01 —
                                    together they form an importable mini-house
  ..._หน้า00_gridline.json           grid master (named + dummy lines, full audit trail)
  ..._หน้า18_notes.json              structural notes with flat aliases
  ..._หน้า19_view1_footing_plan.json point elements
  ..._หน้า19_view2_beam_plan.json    line elements + specs{} + heavy warnings[] history
  ..._หน้า21_view1_section.json      beam sections (the spec source that actually joins)
  ..._หน้า21_view2_schedule.json     column schedule with per-level rows
  ..._หน้า38_1.json                  material_list (categories[].items[])
```

Note the examples carry `schema_generation`, `schema_note`, `view_title` and long
correction-history `warnings[]` — that is the human-correction audit trail. The model
is not expected to produce those meta fields (extra fields are harmless; the wrapper
and `elements[]` shapes are what must match). The `warnings[]` array itself IS
expected: it is where the model reports anything ambiguous, blurred, or judged.
