# Primary Raw JSON Schema

> Compiled 2026-07-10 from [`20260708draft of prime rawjson.md`](../../training-data/docs/20260708draft%20of%20prime%20rawjson.md) (original kept untouched) — this is the spec actually used when prompting the model to extract raw JSON for other houses. History/rationale stripped out; only actionable rules remain.

## 0. FORMAT LOCK — read this before anything else (added 2026-08-02)

**Two files with the same `pattern` must have the same shape. House #1000 must come out looking exactly like house #1.** Everything below is mandatory, not a preference. It exists because houses 01-11 drifted apart badly and had to be repaired in bulk — the repair is described in `json_แก้ไขแล้ว/สิ่งที่ต้องแก้.md` items 59-62, and these rules are what stops it happening again.

### 0.1 The container — never invent an array name

Every file puts its content in **`elements[]`**. Three documented exceptions, and no others:

| pattern | container |
|---|---|
| `gridline` | `grid{ x_lines[], y_lines[] }` — **nested under `grid`**, never `x_lines` at the top level |
| `material_list` (BOQ) | `categories[].items[]` |
| everything else | **`elements[]`** |

❌ **Never name an array after the kind of drawing element it holds.** `beams[]`, `columns[]`, `slabs[]`, `footing_types[]`, `column_sections[]`, `structural_elements[]`, and `details[]`/`sections[]` *when they hold drawing elements*, are all forbidden. Houses 10 and 11 did this and needed 30 files rebuilt. The kind belongs in `element_type`, not in the array name.

**The test is what the array holds, not what it is called.** These are legitimate and must NOT be folded into `elements[]`:

| array | where | holds |
|---|---|---|
| `sections[]` | `index` | document sections — `{title: "แบบสถาปัตยกรรม", sheet_range: "A-01 ถึง A-15"}` |
| `sections[]` | `notes` | numbered note headings — `{heading: "1. ข้อกำหนดทั่วไป", items: [...]}` |
| `columns[]` | `schedule`, `material_list` | table column headers — plain strings like `"ลำดับที่"` |
| `fixture_symbol_legend[]`, `fixture_install_height_standard[]` | any | pure reference tables |

If the entries have (or should have) an `element_id` and an `element_type`, it is drawing content → it belongs in `elements[]`. If they are document structure, table headers, or a reference table, leave them where they are.

### 0.2 Every element carries these four

```json
{ "element_id": "...", "element_type": "...", "confidence_score": 0.9, "confidence_flags": [] }
```
`confidence_score` is `null` when the sheet genuinely gave you nothing to judge by. **Never invent a number to fill the field** — a made-up confidence is worse than an honest `null`.

### 0.3 `element_id` = the mark printed on the drawing, nothing else

- `"B1"`, `"F1.30x1.30"`, `"C1A"` — exactly as printed.
- ❌ **No position suffix**: `"F1.30x1.30_E1"` is wrong, position lives in `grid_refs`. Embedding it breaks every cross-page spec join.
- ❌ **No level suffix**: see §8 — the level goes in its own `level` field.
- ❌ **No detail/section suffix**: `"B0_section_0-0"` → `"B0"`, put the cut label in `section_ref`.
- If the drawing never marked the thing, a descriptive id is fine (`"ครีบ_คสล_รอบอาคาร"`) — just don't dress it up to look like a mark.
- **Two different members must never end up with the same `element_id` on one sheet.** A landing beam and an ordinary beam of the same mark, a stair and its steps, three eave materials at one R-mark — these are genuinely different and keep whatever suffix distinguishes them. When shortening an id would collide, don't shorten it.

### 0.4 `element_type` — reuse, don't invent

Across houses 01-11 this field grew to **359 distinct values over 4,507 elements**. That is drift, not richness. Use one of these established values whenever it fits:

`beam` · `column` · `footing` · `pile` · `pile_cap` · `pedestal` · `slab` · `tie_beam` · `rafter` · `stair` · `room` · `room_cut` · `door` · `window` · `wall` · `dimension` · `dimension_chain` · `dimension_note` · `level` · `datum` · `note` · `symbol` · `symbol_legend_entry` · `sheet_index_entry` · `detail_view` · `section_view` · `plan_view` · `precast_plank_detail` · `sanitary_fixture` · `vent_pipe` · `fitting` · `accessory` · `furniture` · `gate_component` · `railing_component` · `electrical_outlet` · `ceiling_downlight_point` · `ceiling_fan` · `design_criterion` · `steel_member` · `connection_detail` · `installation_detail`

Only add a new value when **none** of the above genuinely fits, and when you do, say so in `warnings[]` so the next house can reuse it instead of inventing a third spelling of the same idea.

### 0.5 Dimensions are integer millimetres

- Member size → **`width_mm`, `height_mm`, `thickness_mm`, `depth_mm`** as numbers.
- ❌ Never a packed string: `"size_m": "0.20x0.40"` is wrong → `width_mm: 200, height_mm: 400`.
- ❌ Never a metre variant of a member dimension (`width_m`, `height_m`, `depth_m`, `section_mm: "200x200"`).
- Levels, spans, grid positions and site distances stay in metres (`level_m`, `span_length_m`, `pos_m`) — those are *positions*, not member sizes.
- When the drawing prints metres, convert **and** keep the printed text (§0.7).

### 0.6 Rebar is always an object, never a string

❌ `"main_bar": "2-Ø16มม. top + 2-Ø16มม. bottom"` · ❌ `"stirrup": "Ø6มม.@0.20ม."`

✅ the §6 object form. Also:
- **`stirrup` is the only name** — `tie`, `tie_bar`, `stirrup_or_tie`, `tie_or_mesh` are all forbidden spellings of it.
- Spacing is `spacing_mm` (an integer), not `@0.20ม.` inside a string.
- `Ø` → `type: "RB"` always (§6).

### 0.7 `printed_as` — keep the drawing's own words

Whenever you convert something the drawing printed (a size string, a rebar callout, a section designation), keep the original verbatim in a sibling `*_printed_as` / `printed_as` field. It costs nothing, it is the audit trail back to the sheet, and it is what lets a later pass re-check a parse without reopening the drawing.

### 0.8 `grid_ref` notation — one way only

| meaning | write it | never |
|---|---|---|
| a point (footing, column, beam end) | `"C1"`, `"ค1"`, `"E'1"`, `"C3''"` | `"C-1"`, `"c-1"`, `"1-C"` |
| a range on one axis | `"D-C"`, `"1-2"` | — |
| a 2-axis area, **vertical first** | `"D-C x 1-2"` | `"1-2 x D-C"` |
| approximate | `"~A1"` | `"near grid A1"` |

- **The word `grid`/`dummy` never appears inside a `grid_ref` value.** Write `"D-C"`, not `"gridD-gridC"`; `"beyond 3"`, not `"beyond grid 3"`.
- Row letters keep the drawing's own alphabet — Thai `ก`/`ข`/`ค` stays Thai, it is what is printed.
- Every point ref must resolve against that house's `หน้า00_gridline.json`. If it doesn't, the grid master is missing a line (§4 beam-endpoint rule) — fix the master, don't invent a ref.

### 0.9 `pattern` must be one of the 14 in §1

Never coin a new one. House 07 invented `detail`, `diagram` and `elevation` and needed 21 files remapped. A detail sheet is `section`; an elevation is `side_profile`; a schematic diagram is `side_profile`; a site plan is `site_plan`, not `plan`.

### 0.10 Before you call a house finished

**Run `python tools/check_format.py <house-folder>` — it checks every item below and exits non-zero on failure.** Do not hand-audit; a 1000-house set cannot be eyeballed.

- [ ] every file parses as JSON
- [ ] every file has the §2 wrapper fields
- [ ] `pattern` is one of the 14 (§1)
- [ ] no file carries `phase_note` (§2a)
- [ ] no array named after a kind of drawing element (§0.1)
- [ ] grid master nests `x_lines`/`y_lines` under `grid{}` (§0.1)
- [ ] no rebar left as a string (§0.6)
- [ ] no packed size string (§0.5)
- [ ] `grid_ref` notation: no dashed point, no `grid`/`dummy` word (§0.8)
- [ ] every point `grid_ref` resolves against `หน้า00_gridline.json` (§0.8)
- [ ] no `element_id` collides with a different member on the same sheet (§0.3)
- [ ] point elements merged to one entry per mark (§4), span elements left atomic (§4)

**The one allowed exception to the merge check:** two entries of the same point mark may stay separate when they carry genuinely different `confidence_score` or a different per-position `note` — merging would erase which positions were read off the drawing and which were inferred. The checker reports these; keep them, and say why in `warnings[]`. Anything else that trips the checker is a real defect.

## 1. Pattern taxonomy — 14 types

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
| 13 | `misc` | เบ็ดเตล็ด — whole-series catalog/promotional/reference pages that aren't about this house's own construction (e.g. a back-cover price-comparison table across all 10 designs in the series, or a cover collage of every design's render) — added 2026-07-14, previously misclassified as `title` |
| 14 | `unknown` | doesn't fit any of the 13 above |

**Automation scope:** `run_pipeline.py` currently only auto-extracts `plan` / `section` / `schedule` / `notes` / `gridline` / `material_list`. The other 8 patterns (`index`, `site_plan`, `side_profile`, `title`, `symbol`, `roof_plan`, `misc`, `unknown`) are manual-extraction only for now — which is exactly what this workflow (Claude reading pages directly) is for.

## 2. Required fields on every file (wrapper level)

```
png, doc_page, discipline, sheet_code, sheet_name, pattern,
source_image, confidence_score, confidence_flags, warnings
```

**`source_image`** = full path of the source image, e.g. `"image/<house>/<house>_หน้า19.png"` — every file coming from the same page (e.g. `_view1_...`/`_view2_...`) must have the exact same value.
**Exception:** the grid-master file `<house>_หน้า00_gridline.json` uses `source_pages` (array of every `source_image` used to confirm the grid) instead.

## 2a. `phase_note` — staged-extraction scratch field (added 2026-07-27)

Optional wrapper-level field, **only** used by a staged `op2` run (see the README). It is orchestration scratch, **not training data**.

```json
"phase_note": [
  "Stage 2: A-07 confirms the S-06 roof ridge position traced from line weights. Stage 3 please cross-check and fold into warnings[].",
  "Stage 2: จันทัน section on this sheet differs from S-05's. Not resolvable without both sheets side by side."
]
```

Purpose: let a stage that **cannot** resolve something — because it does not hold the sheet that settles it, or because it is forbidden to touch the grid — hand the question forward without polluting `warnings[]`.

Hard rules:

- **`warnings[]` is append-or-rewrite only. NEVER delete a warning.** When a later stage overturns an earlier reading, **rewrite** the warning so it records the reversal: what was believed, what overturned it, and how many sheets agreed. That reversal narrative is the single most valuable training signal in the file (precedent: the house-06 grid reversal, and house-07's `F16` vs `F18`, where three marks on the drawing beat one in the title block).
- **`phase_note` must be ABSENT from every finished file.** Stage 3 folds each note into `warnings[]` (or discards it as resolved) and then deletes the field. A file still carrying a `phase_note` is by definition unfinished.
- A `phase_note` is never a substitute for a decision. If the stage that holds the evidence *can* decide, it decides and writes a `warnings[]` entry — same standing order as `op1`.
- Never put a `phase_note` on the grid master. A grid problem is escalated by re-running Stage 1, not annotated (see the README's `op2` escalation rule).

## 3. Multi-view pages

A page may contain multiple views/patterns — **inventory every view first with `views[]`** (prevents losing one), then write each out as a separate file per view (`_view1_footing_plan.json`, `_view2_beam_plan.json`, etc.).

## 4. Grid

- **Axis:** `x_lines` = horizontal along the top edge (usually numbers 1,2,3...) · `y_lines` = vertical along the side edge (usually letters A,B,C...)
- **grid_ref format — a dash means a RANGE, never a point** (confirmed project-wide 2026-07-13, applied to houses 01-05):
  - **Point** (a footing, a column, one end of a beam) = row letter + column number with **no dash**: `"C2"`, `"E'1"`, `"C3''"`. A prime on either part stays attached (`C1'`, `A''3`).
  - **Range/line/area** = dash between the two positions **on the same axis**: `"D-C"` (row range), `"1-2"` (column range). Two axes combine with `x`, vertical axis first: `"D-C x 1-2"`.
  - Point-type elements (footing/column) store position as an **array**, e.g. `grid_refs:["A1","A2"]`, never a comma-string.
  - Makham's reasoning: "it's just a point, not a line — only a line or area needs a dash." A beam's own line is already expressed by having separate `grid_ref_start`/`grid_ref_end`, so each endpoint is a point and takes no dash.
  - ⚠️ **After any bulk regex that strips these dashes, re-check `sheet_code`** — a value like `"S-04"` matches the same letter-dash-digit shape and gets corrupted to `"S04"`. This has happened on three separate houses (สิ่งที่ต้องแก้ items 26, 31).
- **Axis order rule:** always read/write the **vertical axis (y_lines, row letters) first**, then the horizontal axis (x_lines, column numbers) — the same row-before-column order a point ref uses (`"A1"`), and it must also apply to any combined-range free-text `grid_ref` on `plan` elements, e.g. write `"D-C x 1-1'"` (row range first, `x`, then column range), not `"1-1' x D-C"` (บทเรียนจาก 2026-07-13: ตอนย่อ `grid_ref` ในบ้าน 1 หน้า06_floor_plan.json ให้สั้นลง เขียนแกน x ก่อนโดยไม่ตั้งใจ ต้องกลับมาแก้)
- **Span:** calculated by code from the grid only — never let the model estimate distance
- **`span_source` enum:** `grid_table` / `local_dimension` / `unresolved` / `n/a`

### Dummy grid
- A structural line not on a named/printed main grid → name it with a **prime** appended to the main grid **above it (y-axis) / to its left (x-axis)** — **not** the nearest one (corrected by Makham 2026-07-24, สิ่งที่ต้องแก้ item 51; the earlier wording here said "nearest" and was wrong). E.g. a line at 5.2 between named `2`(5.0) and `3`(8.5) is `2'`, even though it is far closer to `2` than to `3` — the rule is direction, not distance, so it stays stable when a grid is later re-based.
- **Exception — a label the user supplies by hand is recorded exactly as given, never normalized.** House #04's master carries `A'`(1.6) and `E'''`(4.2) both sitting in the E-to-C range, matching neither the above/left rule nor the nearest rule. They are kept verbatim and flagged, on the standing "record as given, don't guess" rule — do not silently rename a user-supplied label to satisfy this section.
- **Prime ordering when more than one dummy line falls in the same gap:** scan in standard reading direction — x-axis left→right, y-axis top→bottom. First line found = 1 prime (`A'`), next one = 2 primes (`A''`), and so on (`A'` must always sit left of/above `A''`)
- **Origin (0,0)** must always be the leftmost/topmost main grid (`type:"named"`) — a dummy grid must never take over the origin position. If a dummy grid falls before the origin (further left/up than the first main grid), use a **negative** `pos_m` instead, e.g. `{"id":"1'","pos_m":-0.80,"type":"dummy"}`
- `pos_m` is always read from an actually-printed dimension line — never guessed

#### 🔎 How to FIND dummy grids: the beam-endpoint rule (Makham, 2026-07-19)

**If a beam's start or end point does not sit on any grid line in the drawing, that point needs a dummy grid.** A beam always lands on something — if the extraction has nowhere to name that landing point, the grid master is incomplete, not the beam.

Work the plan sheet this way:
1. Trace **every** beam segment on the sheet, including short stubs and the ones in dense stair/closet clusters.
2. For each endpoint, ask: is there a named or already-known dummy line there? If yes, use it.
3. If not → **a dummy grid belongs at that point.** Read its `pos_m` off the printed dimension chain (per the rule above — never estimate), add it to `หน้า00_gridline.json`, then record the beam against it.

**Never do these instead** (all three are real failure modes seen in houses #3/#4, and each one silently loses a real beam):
- ❌ dropping the beam because it "isn't on the grid"
- ❌ recording it with a prose `description` and no `grid_ref_start`/`grid_ref_end` (e.g. `"small beam marker near col1, exact segment uncertain"`)
- ❌ setting `grid_ref_start` = `grid_ref_end` with a `null` span

Real cases: house #04's S-04 (หน้า33) was missing **8** beams and had 2 position-less placeholder entries; its S-05 (หน้า34) was missing **12** more, including a whole bay window recorded only as `"1.75m wide, not clearly grid-aligned"`. Every one of them sat on a line the grid master didn't have yet (`1'`, `1''`, `1'''`, `1''''`, `3'`, `E''`). Once those dummy lines existed, all 20 beams had exact grid refs.

**Conversely — do NOT invent a dummy for a slab-only edge.** A dashed slab/room boundary, a roof-overhang line, or an eave edge with **no beam label and no columns at its corners** is not a structural line and gets no dummy grid (house #3's `E'` at the S0 bay-window box is exactly this case — slab edge only, no beam, so nothing was added). The trigger is a **beam endpoint**, not any line on the drawing.

### Master file
Create/update `<house>_หน้า00_gridline.json` **before** extracting any other page — it holds every main grid + dummy grid for the whole house in one place. Other plan/section pages reference it via the `grid_source` field instead of re-writing the grid. Keep this as a separate companion file — never re-embed the full grid inline inside every view.

### Atomic segments (span elements) vs merged entries (point elements)

These are two opposite rules and the dividing line is **whether the element has a span or a position**:

**Beams and other span elements → atomic, one entry per grid-to-grid segment.** Don't pre-group multiple spans of the same mark into a single `count`. Grouping identical segments into `count` + list, keyed by `(element_id, span, span_source)`, is handled automatically downstream — sending atomic data in keeps that grouping accurate.

**Footings, columns and other point elements → the opposite: one `element_id` appears exactly ONCE per file**, merged into a single entry carrying `count` + a `grid_refs` array (Makham, 2026-07-20, สิ่งที่ต้องแก้ item 48):
```json
// ❌ wrong — same mark split across 2 entries
{ "element_id": "F0.60x0.60", "count": 2, "grid_refs": ["E'1", "E'2"] },
{ "element_id": "F0.60x0.60", "count": 2, "grid_refs": ["A2", "A3"] }

// ✅ right — one entry
{ "element_id": "F0.60x0.60", "count": 4, "grid_refs": ["E'1", "E'2", "A2", "A3"] }
```
This holds **even when the adjacent column marks differ** — a point element carries position only (its spec lives in `specs{}`), so a neighbouring column's mark is not a reason to split the footing entry.

**⚠️ Merging vs de-duplicating — check `grid_refs` overlap before you touch anything:**
- grid_refs **do not overlap** → genuine merge, add the counts.
- grid_refs **overlap** (the same point appears in both entries) → that is a real double-count bug: **delete** the duplicate, the count must NOT increase.

**⚠️ Exception — multi-level schedule tables.** This merge rule applies only to elements with a **position on a plan**. A column schedule listing the same mark once per level (§8) **must** repeat `element_id`, one entry per `level` — never merge those.

### Element ordering within `elements[]`
Order grid-positioned elements (beams, footings, columns, etc.) in **reading order**, not grouped by `element_id`/mark:
1. **Top to bottom** (row order: first main grid row → last, e.g. D → C → B → A)
2. **Left to right** within each row (column order: first main grid column → last, e.g. 1 → 1' → 2 → 3 → 3'')
3. **Vertical before horizontal** when two elements share the same starting point (e.g. at D1, a beam running D1→C1 vertically is listed before a beam running D1→D2 horizontally) — corrected 2026-07-14, was stated backwards originally

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

**⚠️ Columns are the exception — a column NEVER uses `top`/`bottom`, only a single `count`** (confirmed project-wide by Makham, สิ่งที่ต้องแก้ items 21/46):
```json
"main_bar": { "count": 4, "dia_mm": 12, "type": "RB", "note": "main rebar around the 4 column corners" }
```
A column has no beam-style top face and bottom face — it has bars around its corners, printed as a single figure (`4-Ø12มม.`). Recording it as `top:4/bottom:4` silently doubles the real count to 8. This has been swept across the whole project and every `element_type: "column"` now uses a single `count`; do not reintroduce the split. Applies to structural columns, pedestals (ตอม่อ), short columns (`C0`/`CN`) and fence columns alike.

The `top`/`bottom` split rule above is for **beams** (and any member genuinely detailed with two longitudinal faces).

**`middle` — third main_bar face (added 2026-07-20 by Makham).** When a section drawing shows a **clearly distinct mid-depth bar row** — its own leader line, its own dot row sitting between the top and bottom clusters, typically on a deep beam — record it as a third `main_bar` face, **not** as `additional_bars`:
```json
"main_bar": {
  "top":    { "count": 2, "dia_mm": 16, "type": "RB" },
  "middle": { "count": 2, "dia_mm": 9,  "type": "RB" },
  "bottom": { "count": 4, "dia_mm": 16, "type": "RB", "note": "2 เส้นเต็มความยาว + 2 เส้นหยุดที่ L/8" }
}
```
Real case: house #04's B4A/B4X (200x700 deep beams) print `2Ø9มม.` on a leader pointing to a distinct dot row at mid-depth, between the `2-Ø16มม.` top row and the `2-Ø16มม.` + `2-Ø16มม.(หยุดที่ L/8)` bottom rows. These are skin/waist bars — real longitudinal main reinforcement on their own face, so they belong in `main_bar.middle`.

`middle` is **optional** — emit it only when such a row genuinely exists; most beams have only `top`/`bottom`. Do not invent a `middle` by splitting a top or bottom cluster, and do not use it for a bar that is merely *drawn* between the two clusters but whose leader ties it to the top or bottom face (that case still merges into `top`/`bottom` per §7).

```json
"additional_bars": [
  { "count": 1, "dia_mm": 16, "position": "on top of beam, cut off at L/8 from column face", "note": "..." }
]
```
With `middle` available, `additional_bars` is now only for bars that belong to **no** longitudinal face at all (e.g. a standalone tie/dowel). A mid-depth longitudinal row is `main_bar.middle`, not an additional bar.

**Ø (circle symbol) always = RB** — never infer from bar diameter; go by the printed symbol only (deformed bar with visible ribs = DB).

## 6a. Steel members — `steel_section` (added 2026-07-25)

Not every house is reinforced concrete. When a member is **structural steel** (hot-rolled section), it has no `main_bar`/`stirrup` at all — record its printed section designation instead:

```json
"steel_section": {
  "designation": "WF",
  "d_mm": 400, "b_mm": 200, "tw_mm": 8, "tf_mm": 13,
  "printed_as": "WF 400x200x8x13 มม."
}
```

- **`designation`** = the printed profile family exactly as drawn — `WF` (wide flange), `C` (channel/light-lip channel), `L`, `RHS`, `SHS`, `Pipe`. Don't translate or normalize to a foreign standard (no `H-beam`, no `W14x…`).
- **Dimension keys follow the printed order of that family.** For the two seen so far:
  - `WF d×b×tw×tf` → `d_mm` (depth), `b_mm` (flange width), `tw_mm` (web thickness), `tf_mm` (flange thickness)
  - `C d×b×tw×tf` → same four keys (e.g. `C 125x65x6x8`)
  - A lipped channel printed with five numbers (e.g. `C100x50x20x3.2`) adds `lip_mm` before the thickness.
- **`printed_as`** always keeps the raw printed string verbatim, including the Thai unit — it's the audit trail when the key mapping above is ambiguous for a family not yet seen.
- **`element_type` stays semantic** (`beam` / `column` / `purlin` / `truss`), not `steel_beam` — the material is carried by `steel_section` being present instead of `main_bar`.
- Add `"material": "steel"` on the spec entry so a consumer never has to infer material from which key exists.
- Spacing-based repeated members (purlins/joists, e.g. `C100x50x20x3.2 มม. @0.40 ม.`) put the spacing in `spacing_mm` (400), same field name the rebar side uses.

**A member has either `main_bar`/`stirrup` or `steel_section` — never both.** A hybrid building (steel superstructure on RC footings/pedestals, as in `บ้าน_ใหญ่_1ชั้น_01`) is normal: the RC footings/pedestals/slabs keep the rebar fields, the steel frame above uses `steel_section`, and both live in the same `specs{}` object keyed by `element_id`.

## 7. Spec join (plan + section/schedule)

A `plan` element (has `grid_ref`) + a `section` **or** `schedule` element (has width/height/main_bar/stirrup) for the same mark join together via `element_id` — **`section` and `schedule` are equally valid spec sources**, not limited to `section` only.

Fields joined in:
```
width_mm, height_mm, main_bar{}, stirrup{}, additional_bars[],
steel_section{}, material, spacing_mm,
concrete_grade, steel_grade, spec_source, spec_confidence_score
```
(`steel_section{}`/`material` per §6a — a steel member joins exactly the same way, it just carries a section designation instead of rebar.)

**Conflict rule:** if the same `element_id` has mismatched specs in both `section` and `schedule` → **`section` always wins**, and must be flagged with `confidence_flag: "spec_conflict_section_vs_schedule"` every time — never silently pick one without recording it. *(Not yet tested against real data.)*

**Don't inline the joined spec into every atomic segment.** Once a mark's spec is confirmed identical across all its occurrences (verify this first — don't assume), store it **once** in a top-level `specs` object keyed by `element_id`, e.g. `specs.B4 = {width_mm, height_mm, main_bar, stirrup, additional_bars, concrete_grade, steel_grade, spec_source, spec_confidence_score}`. Each entry in `elements[]` then only carries position (`grid_ref_start`/`grid_ref_end`, `span_length_m`, `span_source`) and its own per-occurrence `confidence_score`/`confidence_flags` — never repeat the full spec block on every segment (บทเรียนจาก 2026-07-14: บ้าน 1 หน้า19 beam plan เคยพิมพ์ spec ซ้ำทุกช่วงของคานมาร์คเดียวกัน กลายเป็น god-object-in-a-row-per-mark ทั้งที่ spec เหมือนกันทุกตัวอักษร). A spec-level observation that applies to every occurrence of a mark (e.g. an asymmetric top/bottom rebar count) belongs in that mark's `specs` entry as `spec_confidence_flags`, not repeated on each `elements[]` occurrence — but a note about something specific to one particular occurrence (e.g. a stray arrow symbol printed only near one segment) stays on that occurrence's own `confidence_flags`.

**Verify `additional_bars[].position` against the actual leader line in the section drawing — never trust the printed label text alone, and never assume top vs. bottom from how a similar-looking mark resolved.** Two real cases from the same house, same-looking label pattern, opposite answers:
- **B2/B4/B5/B3**: label read "บนคาน" (top) but the leader line actually pointed to a bottom-corner bar (curtailed at L/8, alongside the other bottom main bars) → merged into `main_bar.bottom.count` (e.g. `count: 2` + 1 curtailed bar → `count: 3`).
- **B3X**: a bar labeled "ล้วงเข้า B3 1.5 ม." (lap-splices into the adjacent beam B3) — sounds like it should be a separate cross-beam detail, but per B3X's own section the label order top-to-bottom was *top-continuing / lap-splice bar / stirrup / bottom-continuing*, meaning the lap-splice bar is actually B3X's own **top** reinforcement (anchored by extending into B3), not a bottom bar and not something to leave out — merged into `main_bar.top.count` (`count: 2` → `4`) instead.

So: **"lap-splices into an adjacent beam" is not on its own a reason to keep a bar in `additional_bars`** — it can still belong to that mark's own `main_bar.top` or `.bottom`, exactly like a same-beam curtailed bar. Check the printed label *order* (top-to-bottom in the section) or the leader line position for **every mark independently** — don't reuse the previous mark's answer. Always add a `note` on the affected `main_bar` side (e.g. "2 เส้นต่อเนื่องจาก B3 + 2 เส้นล้วงเข้า B3 1.5 ม.") so the splice/curtailment detail isn't lost after merging. Only keep a bar in `additional_bars` when it genuinely isn't part of any main_bar face at all — and note that a **mid-depth longitudinal row now has its own face, `main_bar.middle` (§6)**, so "it's not top and not bottom" is no longer a reason to leave it in `additional_bars`.

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

## 11a. Multi-building drawing sets (added 2026-07-25)

A single drawing set can cover **more than one physically separate building** (e.g. `บ้าน_ใหญ่_1ชั้น_01` = the main row building + a detached shared-toilet block, `อาคารสุขารวม`). Both buildings reuse the same grid names (`ก`/`ข`/`ค`, `1`/`2`) at **different spacings** — so a single grid master cannot hold them.

- **One grid-master file per building.** Main building keeps `<house>_หน้า00_gridline.json`; each additional building gets `<house>_หน้า00<letter>_gridline_<building>.json`, e.g. `..._หน้า00b_gridline_สุขา.json`.
- Each building's grid has **its own origin** — never offset one building's grid into the other's coordinate space.
- Every page/view file points at the one it uses via `grid_source` (the filename), so a `grid_ref` is only ever read against the right grid.
- When a single sheet draws both buildings (S-01/S-02 here do), split it into one view file per building rather than mixing two coordinate systems in one `elements[]`.
- Record the building name on the wrapper as `building` (e.g. `"อาคารหลัก"` / `"อาคารสุขารวม"`) so downstream consumers don't have to infer it from the filename.

## 12. Rules still in draft / not yet verified against real data

- `title` / `symbol` / `roof_plan` — no confirmed field-set from real extraction yet
- `steel_section` (§6a) — key mapping confirmed only for `WF` and `C` so far; other families (`L`, `RHS`, `Pipe`) unseen
- Multi-building grid masters (§11a) — first use is `บ้าน_ใหญ่_1ชั้น_01`; no second example yet
- ~~Dummy grid prime ordering + negative `pos_m` (section 4) — no real case yet with ≥2 dummy lines in the same gap, or one before the origin~~ **CONFIRMED against real data 2026-08-02** — house #04's master carries four dummies in the single grid-1-to-grid-2 gap (`1'`/`1''`/`1'''`/`1''''`, ordered left→right exactly as the rule requires) and a negative `pos_m` before the origin (`1'` at -0.6); house #05 has the same negative case (`1'` at -0.6). Both halves of the rule now have real precedent
- `source_image` field — older files in `mk_test/t1-t3` don't have it
- "section wins over schedule" conflict rule (section 7) — not yet tested against real data
- Same `element_id` appearing in more than one `section` file (e.g. B2 in both S-04 and S-05) — no resolved precedence rule yet; open question

## 13. `site_plan` — `element_type` not standardized across houses

Checked all 5 houses' `site_plan` pattern files (2026-07-13). `element_type` values found: `boundary_line`, `building_footprint`, `building_outline`, `grading_note`, `grading_note_or_slab`, `lot_boundary`, `other`, `road`, `room`, `setback` — 10 distinct strings, but several pairs describe the same real-world thing under different names per house:

- `building_footprint` / `building_outline` — both mean the building's outline within the lot
- `boundary_line` / `lot_boundary` — both mean the property boundary line
- `grading_note` / `grading_note_or_slab` — both mean the ground-fill/grading annotation

No fixed enum has ever been given for `site_plan`'s `element_type` — each house's extraction picked its own naming independently. Not merged/standardized yet; flagged here so a future pass can decide on one canonical name per concept before this pattern is used for any downstream automation.
