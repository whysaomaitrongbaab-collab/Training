# Primary Raw JSON Schema

> Compiled 2026-07-10 from [`20260708draft of prime rawjson.md`](../../training-data/docs/20260708draft%20of%20prime%20rawjson.md) (original kept untouched) — this is the spec actually used when prompting the model to extract raw JSON for other houses. History/rationale stripped out; only actionable rules remain.

## 1. Pattern taxonomy — 13 types

| # | pattern | description |
|---|---|---|
| 1 | `plan` | floor plan / layout, has `grid_ref` |
| 2 | `section` | detail section — rebar spec/dimensions for beam, column, footing |
| 3 | `schedule` | summary table of any element/material type (column, beam, door, window, fence, etc. — not limited to column/beam) |
| 4 | `notes` | project-level requirements/specs |
| 5 | `index` | drawing set table of contents |
| 6 | `material_list` | bill of quantities (BOQ) |
| 7 | `site_plan` | site layout |
| 8 | `side_profile` | non-top-down view, e.g. elevation/building section (not site/terrain info, no rebar) — formerly named `site_profile` |
| 9 | `gridline` | grid reference file (per-page companion + `หน้า00` master) |
| 10 | `title` | cover page *(draft — no field-set verified yet)* |
| 11 | `symbol` | symbol/legend page *(draft)* |
| 12 | `roof_plan` | roof plan, separated from `plan` because it has ridge/hip lines and eave overhangs *(draft)* |
| 13 | `unknown` | doesn't fit any of the 12 above |

**Automation scope:** `run_pipeline.py` currently only auto-extracts `plan` / `section` / `schedule` / `notes` / `gridline` / `material_list`. The other 7 patterns (`index`, `site_plan`, `side_profile`, `title`, `symbol`, `roof_plan`, `unknown`) are manual-extraction only for now — which is exactly what this workflow (Claude reading pages directly) is for.

## 2. Required fields on every file (wrapper level)

```
png, doc_page, discipline, sheet_code, sheet_name, pattern,
source_image, confidence_score, confidence_flags, warnings
```

**`source_image`** = full path of the source image, e.g. `"image/<house>/<house>_หน้า19.png"` — every file coming from the same page (e.g. `_view1_...`/`_view2_...`) must have the exact same value.
**Exception:** the grid-master file `<house>_หน้า00_gridline.json` uses `source_pages` (array of every `source_image` used to confirm the grid) instead.

## 3. Multi-view pages

A page may contain multiple views/patterns — **inventory every view first with `views[]`** (prevents losing one), then write each out as a separate file per view (`_view1_footing_plan.json`, `_view2_beam_plan.json`, etc.).

## 4. Grid

- **Axis:** `x_lines` = horizontal along the top edge (usually numbers 1,2,3...) · `y_lines` = vertical along the side edge (usually letters A,B,C...)
- **grid_ref format:** `"A-1/A-2"` (dash+slash) — point-type elements (footing/column) store position as an **array**, e.g. `grid_refs:["A-1","A-2"]`, never a comma-string
- **Axis order rule:** always read/write the **vertical axis (y_lines, row letters) first**, then the horizontal axis (x_lines, column numbers) — matches the existing `"A-1"` convention (row before column) and must also apply to any combined-range free-text `grid_ref` on `plan` elements, e.g. write `"D-C x 1-1'"` (row range first, `x`, then column range), not `"1-1' x D-C"` (บทเรียนจาก 2026-07-13: ตอนย่อ `grid_ref` ในบ้าน 1 หน้า06_floor_plan.json ให้สั้นลง เขียนแกน x ก่อนโดยไม่ตั้งใจ ต้องกลับมาแก้)
- **Span:** calculated by code from the grid only — never let the model estimate distance
- **`span_source` enum:** `grid_table` / `local_dimension` / `unresolved` / `n/a`

### Dummy grid
- A structural line not on a named/printed main grid → name it with a **prime** appended to the nearest main grid, e.g. `1'`, `A'`
- **Prime ordering when more than one dummy line falls in the same gap:** scan in standard reading direction — x-axis left→right, y-axis top→bottom. First line found = 1 prime (`A'`), next one = 2 primes (`A''`), and so on (`A'` must always sit left of/above `A''`)
- **Origin (0,0)** must always be the leftmost/topmost main grid (`type:"named"`) — a dummy grid must never take over the origin position. If a dummy grid falls before the origin (further left/up than the first main grid), use a **negative** `pos_m` instead, e.g. `{"id":"1'","pos_m":-0.80,"type":"dummy"}`
- `pos_m` is always read from an actually-printed dimension line — never guessed

### Master file
Create/update `<house>_หน้า00_gridline.json` **before** extracting any other page — it holds every main grid + dummy grid for the whole house in one place. Other plan/section pages reference it via the `grid_source` field instead of re-writing the grid. Keep this as a separate companion file — never re-embed the full grid inline inside every view.

### Atomic segments
Report each beam span as **one atomic entry per grid-to-grid segment** — don't pre-group multiple spans of the same mark into a single `count`. Grouping identical segments into `count` + list, keyed by `(element_id, span, span_source)`, is handled automatically downstream — sending atomic data in keeps that grouping accurate.

### Element ordering within `elements[]`
Order grid-positioned elements (beams, footings, columns, etc.) in **reading order**, not grouped by `element_id`/mark:
1. **Top to bottom** (row order: first main grid row → last, e.g. D → C → B → A)
2. **Left to right** within each row (column order: first main grid column → last, e.g. 1 → 1' → 2 → 3 → 3'')
3. **Horizontal before vertical** when two elements share the same starting point (e.g. at D1, a beam running D1→D2 horizontally is listed before a beam running D1→C1 vertically)

Elements with no `grid_ref` (marker-only symbols like slab tags `SO`/`SI`/`ST`) can't be positionally sorted — leave them at the end of the array, unordered.

## 5. Beam segment splitting

One beam = between two adjacent supports only. Split immediately when:
1. A column/grid intersection sits in between
2. The beam bears on another beam (not a column) → add `confidence_flags: ["bears_on_beam:<mark>(<end>)"]`
3. The beam changes direction/turns a corner

## 6. Rebar

```json
"main_bar": {
  "top":    { "count": 2, "dia_mm": 16, "type": "RB" },
  "bottom": { "count": 3, "dia_mm": 16, "type": "RB" }
}
```
**Always split `top`/`bottom`, even when equal (symmetric case)** — never collapse into one count. Genuine top≠bottom cases have been found (e.g. top 2, bottom 3); merging loses real data.

```json
"additional_bars": [
  { "count": 1, "dia_mm": 16, "position": "on top of beam, cut off at L/8 from column face", "note": "..." }
]
```

**Ø (circle symbol) always = RB** — never infer from bar diameter; go by the printed symbol only (deformed bar with visible ribs = DB).

## 7. Spec join (plan + section/schedule)

A `plan` element (has `grid_ref`) + a `section` **or** `schedule` element (has width/height/main_bar/stirrup) for the same mark join together via `element_id` — **`section` and `schedule` are equally valid spec sources**, not limited to `section` only.

Fields joined in:
```
width_mm, height_mm, main_bar{}, stirrup{}, additional_bars[],
concrete_grade, steel_grade, spec_source, spec_confidence_score
```

**Conflict rule:** if the same `element_id` has mismatched specs in both `section` and `schedule` → **`section` always wins**, and must be flagged with `confidence_flag: "spec_conflict_section_vs_schedule"` every time — never silently pick one without recording it. *(Not yet tested against real data.)*

**Don't inline the joined spec into every atomic segment.** Once a mark's spec is confirmed identical across all its occurrences (verify this first — don't assume), store it **once** in a top-level `specs` object keyed by `element_id`, e.g. `specs.B4 = {width_mm, height_mm, main_bar, stirrup, additional_bars, concrete_grade, steel_grade, spec_source, spec_confidence_score}`. Each entry in `elements[]` then only carries position (`grid_ref_start`/`grid_ref_end`, `span_length_m`, `span_source`) and its own per-occurrence `confidence_score`/`confidence_flags` — never repeat the full spec block on every segment (บทเรียนจาก 2026-07-14: บ้าน 1 หน้า19 beam plan เคยพิมพ์ spec ซ้ำทุกช่วงของคานมาร์คเดียวกัน กลายเป็น god-object-in-a-row-per-mark ทั้งที่ spec เหมือนกันทุกตัวอักษร). A spec-level observation that applies to every occurrence of a mark (e.g. an asymmetric top/bottom rebar count) belongs in that mark's `specs` entry as `spec_confidence_flags`, not repeated on each `elements[]` occurrence — but a note about something specific to one particular occurrence (e.g. a stray arrow symbol printed only near one segment) stays on that occurrence's own `confidence_flags`.

## 8. `level` field (multi-level schedules)

When a schedule has multiple levels (e.g. same column mark with different specs per floor), use a separate `level` field — **never embed the level into `element_id`**. `element_id` must match the printed mark exactly so cross-page joins stay reliable.
```json
{ "element_id": "C1", "level": "roof frame", "width_mm": 150, ... }
{ "element_id": "C1", "level": "ground floor, pedestal, footing", "width_mm": 200, ... }
```

## 9. `precast_plank_detail` (precast plank detail page)

```json
{
  "element_id": "SP_interior", "element_type": "precast_plank_detail",
  "description": "interior SP slab-laying detail",
  "dowel_bar": { "count": 2, "dia_mm": 9, "type": "RB" },
  "topping_mesh": { "dia_mm": 6, "spacing_mm": 200 },
  "topping_thickness_min_mm": 50,
  "level_step_mm": null,
  "confidence_score": 0.7, "confidence_flags": []
}
```
`level_step_mm` is used when the floor level differs from the norm (e.g. bathroom floor stepped down).

## 10. Slab marker

`SO`/`SI`/`SX`/`ST` → `element_type: "slab"` (not `"unknown_symbol"`) — cross-references across pages the same way as beams. **Watch for `"SI"` (letter I) vs `"S1"` (digit 1) confusion** — double-check this specific point every time.

## 10a. Stairs (`element_type: "stair"`) — `grid_ref`

Don't describe a stair's position with verbose free text (which rooms it sits between, cross-references to a detail sheet, etc.) — just give the **single nearest grid point, approximate**, e.g. `"~A-1"`. A stair's exact footprint is already fully documented on its own detail sheet (`A-11` or equivalent); `grid_ref` on the floor-plan-level element only needs to be enough to locate it roughly on the main grid.

## 11. BOQ

- **One PNG may contain 2 real sheets** (2 portrait pages laid out as one landscape image) → rotate 90° then split left/right halves into separate files (`_1.json`/`_2.json`)
- **Continuation rows** with no item_no/qty of their own must still be a separate item, never merged into the previous row's description

## 12. Rules still in draft / not yet verified against real data

- `title` / `symbol` / `roof_plan` — no confirmed field-set from real extraction yet
- Dummy grid prime ordering + negative `pos_m` (section 4) — no real case yet with ≥2 dummy lines in the same gap, or one before the origin
- `source_image` field — older files in `mk_test/t1-t3` don't have it
- "section wins over schedule" conflict rule (section 7) — not yet tested against real data
- Same `element_id` appearing in more than one `section` file (e.g. B2 in both S-04 and S-05) — no resolved precedence rule yet; open question

## 13. `site_plan` — `element_type` not standardized across houses

Checked all 5 houses' `site_plan` pattern files (2026-07-13). `element_type` values found: `boundary_line`, `building_footprint`, `building_outline`, `grading_note`, `grading_note_or_slab`, `lot_boundary`, `other`, `road`, `room`, `setback` — 10 distinct strings, but several pairs describe the same real-world thing under different names per house:

- `building_footprint` / `building_outline` — both mean the building's outline within the lot
- `boundary_line` / `lot_boundary` — both mean the property boundary line
- `grading_note` / `grading_note_or_slab` — both mean the ground-fill/grading annotation

No fixed enum has ever been given for `site_plan`'s `element_type` — each house's extraction picked its own naming independently. Not merged/standardized yet; flagged here so a future pass can decide on one canonical name per concept before this pattern is used for any downstream automation.
