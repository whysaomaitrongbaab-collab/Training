# Primary Raw JSON Schema

> Compiled 2026-07-10 from [`20260708draft of prime rawjson.md`](../../wait_for_ทิ้ง/No_touch_box/docs/20260708draft%20of%20prime%20rawjson.md) (original kept untouched, moved into `wait_for_ทิ้ง/` 2026-08-04 as historical — see `No_touch_box/docs/ARCHIVE.md`) — this is the spec actually used when prompting the model to extract raw JSON for other houses. History/rationale stripped out; only actionable rules remain.

## 0. FORMAT LOCK — read this before anything else (added 2026-08-02)

**Two files with the same `pattern` must have the same shape. House #1000 must come out looking exactly like house #1.** Everything below is mandatory, not a preference. It exists because houses 01-11 drifted apart badly and had to be repaired in bulk — the repair is described in `json_แก้ไขแล้ว/สิ่งที่ต้องแก้.md` items 59-62, and these rules are what stops it happening again.

### 0.0 Who writes each field — the model, code, or OCR (added 2026-11-18, Makham)

**Rule: the model writes only what is printed on the sheet and can be read off the image. Everything else is stamped by code, read by OCR, or gone.** Asking the model for a value the image cannot show is how t05 learned to emit training-file names (measured 2026-10-03: on houses outside the training set its gridline pass looped on training-house file names until the 9,000-token cap; see `tune_ai/t07_Palfrey/_common.md`). Free text and self-assessed scores have no rule a reader can check. Measured on the 32 human-corrected beam plans in `json_แก้ไขแล้ว/`: `confidence_score` + `confidence_flags` + `note` + `warnings` were **39% of the characters** (112,116 of 286,513).

Two layers, so that no reader has to change:

- **Model output** — what the model (or a hand extractor) decides. Compact, defined by the tables below.
- **Stored file** — what sits in `rawjson_ยังไม่ได้แก้ไขโดนคน/` and `json_แก้ไขแล้ว/` and what every consumer reads (Constistant, `check_format.py`, the dataset builders). Code builds it from the model output plus the stamps below. Its keys are the ones the rest of this spec describes.

**Table 1 — wrapper fields, all 25 patterns**

| field | filled by | from |
|---|---|---|
| `png`, `doc_page` | code | the job's page number |
| `source_image` / `source_pages` | code | the page image path |
| `grid_source` | code | the house's grid-master filename |
| `pattern` | code | pass 0, **per view** — one page can hold several patterns (§3) |
| `discipline` | code | pass 0's subtask; every Pass 2 subtask is `structural` |
| `views[]` | code | pass 0 / the `_viewN` file split; the model no longer lists views |
| `sheet_code`, `sheet_name` | OCR | the title block (`tools/titleblock_ocr.py` exists; quality on these fields not yet measured) |
| `view_title` | OCR | the title printed under the view; on a multi-view page, cropped per view |
| `scale` | OCR + regex `1:\d+` | the scale printed under the view title |
| `floor_level` | code rule on `view_title` | `ชั้นที่ N` / `ชั้น N` → `FN`, `ชั้นล่าง` → `F1`, `ชั้นลอย` → `F<N>M`, `ใต้ดิน` → `B1`, `หลังคา` → `RF`, a second roof level above `RF` (a roof frame standing on an RC roof slab) → `RF2`; no match → `null`, never guessed |
| `confidence_score` | code, always `null` | key kept only so old readers and `check_format.py` keep working |
| `confidence_flags`, `warnings` | code, always `[]` | same |

**Table 2 — element fields**

| field | filled by | rule |
|---|---|---|
| `element_id` | model, checked against OCR | the page's OCR text is sent with the prompt; the model picks the printed mark from it; code keeps the id only if that string is in the OCR list, otherwise `null` + `element_name_assigned` (§0.2). Applies to every pattern that carries marks. The model only uses an OCR list it was trained with, so the training prompts must carry it too |
| `element_type` | model | unchanged (§0.4) |
| span position | model, as `span` (below) | code expands it |
| `confidence_score`, `confidence_flags` on elements | gone | no key at all on elements (Constistant reads them as `?? null`) |
| `note`, `offset_note` — at every level, including inside `main_bar` / `stirrup` / `additional_bars` | gone | printed words go verbatim into `*_printed_as` (§0.7); nothing in the extractor's own words |

**The `span` form — every span element of the plan family** (`beam_plan`, `footing_plan`, `roof_frame_plan`, `etc_plan`: beam, tie_beam, rafter, purlin, steel_member run, atomic wall segment):

```json
{ "element_id": "B1", "element_type": "beam", "span": ["A1", "A2", null] }
```

- `span[0]`, `span[1]` = start and end point, written as in §0.8.
- `span[2]` = length in metres, given **only when an end is not on a named or dummy line**: a number = a printed dimension (`local_dimension`); a string `"~3.20"` = measured by proportion against the grid (`scaled_from_grid`, §4 Span; `~` = approximate, as in §0.8); `null` = not given.
- Code expands it into the stored keys `grid_ref_start`, `grid_ref_end`, `span_length_m`, `span_source`: both ends resolve against the grid master and the beam is axis-aligned → length from the grid, `grid_table`; `null` and not computable (diagonal, or a ref the master lacks) → `unresolved`, never a guess; otherwise from `span[2]` as above.
- Why: on 302 beam plans (11,076 beams) **94% of spans are `grid_table`** — grid arithmetic the model no longer has to do.
- Point elements (footing, column, pile, pedestal, slab tag) keep `count` + `grid_refs[]` (§4) — already compact, and merged: one `element_id` once per file, e.g. `"grid_refs": ["A2", "A3"], "count": 2`. Tendons keep their own band form (§0.4).

**Retired with the free text (no replacement field):** `bears_on_beam:<mark>(<end>)` (§5 — the split rule stays, nothing read the flag) · `spec_conflict_section_vs_schedule` in raw files (§7 — code detects it at join time) · the §0.10 merge exception for point marks (it relied on per-entry `confidence_score` / `note`) · the grid master's per-line confidence, `dummy_grid_rule_check` and `non_grid_dimensions_do_not_confuse` (§4).

**Status, 2026-11-18: spec only.** Still to do, in one batch: the t07 dataset builder, `pass2/KEYS.json` and prompts (drop the retired keys, `span` arrays, OCR list in the prompt), the worker (stamps, OCR, expansion back to stored keys). `check_format.py` needs no change for new files (the kept wrapper keys are present, `null` / `[]`). **Existing files are legacy and are not rewritten** — the builder strips and converts them. **Hand extraction (op01/op04) from now on** writes the stored form directly (keyed spans, wrapper filled from the page in hand), but with `confidence_score: null`, `confidence_flags: []`, no element-level confidence keys and no `note`.

### 0.1 The container — never invent an array name

Every file puts its content in **`elements[]`**. Four documented exceptions, and no others:

| pattern | container |
|---|---|
| `grid_master` | `grid{ x_lines[], y_lines[], z_levels[], dimension_chains[], unassigned_dimensions[] }` — **nested under `grid`**, never `x_lines` at the top level (the last three added 2026-08-21, see §4) |
| `level_master` | `level{ floors[] }` — nested under `level`, same idea as `grid{}` (added 2026-11-18, see §4b) |
| `material_list` (BOQ) | `categories[].items[]` |
| everything else | **`elements[]`** |

❌ **Never name an array after the kind of drawing element it holds.** `beams[]`, `columns[]`, `slabs[]`, `footing_types[]`, `column_sections[]`, `structural_elements[]`, and `details[]`/`sections[]` *when they hold drawing elements*, are all forbidden. Houses 10 and 11 did this and needed 30 files rebuilt. The kind belongs in `element_type`, not in the array name.

**The test is what the array holds, not what it is called.** These are legitimate and must NOT be folded into `elements[]`:

| array | where | holds |
|---|---|---|
| `sections[]` | `index` | document sections — `{title: "แบบสถาปัตยกรรม", sheet_range: "A-01 ถึง A-15"}` |
| `sections[]` | `notes` | numbered note headings — `{heading: "1. ข้อกำหนดทั่วไป", items: [...]}`. A `notes` file also carries a **`notes{}`** object of parsed specification values (§4a) — those two names are the only two allowed on this pattern |
| `columns[]` | `schedule`, `material_list` | table column headers — plain strings like `"ลำดับที่"` |
| `fixture_symbol_legend[]`, `fixture_install_height_standard[]` | any | pure reference tables |

If the entries have (or should have) an `element_id` and an `element_type`, it is drawing content → it belongs in `elements[]`. If they are document structure, table headers, or a reference table, leave them where they are.

Also forbidden as separate arrays (found and repaired 2026-08-02): `slab_markers[]` (§10 already says SO/SI/SX/ST are `element_type: "slab"` in `elements[]`), `reference_markers[]` (→ `element_type: "symbol"`), `door_window_schedule[]` (→ `elements[]` with `element_id` `D1`/`W1`, `element_type` door/window, `opening_type`, `leaf_material` — the field names houses 01-05 use).

**The 10-design series price table** (printed identically in every house of the series) is a reference table and always uses the same shape: `series_price_table[]` with `{design, name, size_sqm, price_pile_baht, price_spread_baht}` under `pattern: misc`. It was once stored five different ways (`house_catalog`/`house_series`/`elements` rows/`material_list` categories/raw text) — never invent a new shape for it.

### 0.2 Every element carries these two

```json
{ "element_id": "...", "element_type": "..." }
```
**Changed 2026-11-18 (§0.0):** elements no longer carry `confidence_score` / `confidence_flags`. They were self-assessed with no rule behind them, and a made-up confidence is worse than none. Older files still have them; the dataset builder strips them.

This applies to **top-level `elements[]` entries**. A cross-reference sub-list nested *inside* an element (e.g. a section-callout element listing its cut marks as `sections[{mark: "A-A", sheet: "A-12"}]`) is exempt — those are attributes of the element, not elements themselves. An entry with no printed mark takes `element_id: null` with the descriptive name moved to `element_name_assigned` (**convention changed 2026-08-25, Makham's approval via att1235** — the old rule of inventing a descriptive id like `ceiling_fan_นอน1` taught the tuned model to guess names that exist nowhere on the paper; 66% of section training examples carried such ids and capped section id-recall at 4% on the test house). `element_name_assigned` is human-facing metadata: dataset builders must strip it from training targets (build_dataset_t03.py `strip_assigned()`), and never leave the `element_id` key absent — null, not missing.

### 0.3 `element_id` = the mark printed on the drawing, nothing else

- `"B1"`, `"F1.30x1.30"`, `"C1A"` — exactly as printed.
- ❌ **No position suffix**: `"F1.30x1.30_E1"` is wrong, position lives in `grid_refs`. Embedding it breaks every cross-page spec join.
- ❌ **No level suffix**: see §8 — the level goes in its own `level` field.
- ❌ **No detail/section suffix**: `"B0_section_0-0"` → `"B0"`, put the cut label in `section_ref`.
- If the drawing never marked the thing, a descriptive id is fine (`"ครีบ_คสล_รอบอาคาร"`) — just don't dress it up to look like a mark.
- **Two different members must never end up with the same `element_id` on one sheet.** A landing beam and an ordinary beam of the same mark, a stair and its steps, three eave materials at one R-mark — these are genuinely different and keep whatever suffix distinguishes them. When shortening an id would collide, don't shorten it.

### 0.4 `element_type` — reuse, don't invent

Across houses 01-11 this field grew to **359 distinct values over 4,507 elements**. That is drift, not richness. Use one of these established values whenever it fits:

`beam` · `column` · `footing` · `pile` · `pile_cap` · `pedestal` · `slab` · `tie_beam` · `rafter` · `purlin` · `truss` · `stair` · `room` · `room_cut` · `door` · `window` · `wall` · `dimension` · `dimension_chain` · `dimension_note` · `level` · `datum` · `note` · `symbol` · `symbol_legend_entry` · `sheet_index_entry` · `detail_view` · `section_view` · `plan_view` · `precast_plank_detail` · `sanitary_fixture` · `vent_pipe` · `fitting` · `accessory` · `furniture` · `gate_component` · `railing_component` · `electrical_outlet` · `ceiling_downlight_point` · `ceiling_fan` · `design_criterion` · `steel_member` · `connection_detail` · `installation_detail` · `tendon`

`purlin` and `truss` were added 2026-08-28 to close a self-contradiction: §6a already names them as the correct semantic `element_type` for a steel roof frame's individual members (distinct from generic `steel_member`), but this list never carried them, so no real file has used them yet — this is a pure vocabulary fix, not a migration.

`tendon` was added 2026-11-18 (house 174, the first post-tensioned building in the set). One element per band of parallel tendon lines that share an end symbol and a run: `{element_id: null, element_name_assigned, element_type: "tendon", direction: "x"|"y", grid_ref: "<y part> x <x part>", tendon_lines_drawn, positions_y_m (x-direction) | positions_x_m (y-direction), end_symbol: "circle"|"triangle"|"square"|"diamond"|null, strands_per_tendon}`. Strands per tendon come from the set's own symbol legend; positions are the lines' perpendicular positions in metres.

Only add a new value when **none** of the above genuinely fits, and when you do, say so in `warnings[]` so the next house can reuse it instead of inventing a third spelling of the same idea.

**A detail sheet does not get its own `element_type`.** `pile_cap_detail` and `spread_footing_detail` are the same members as `pile_cap` and `footing`, drawn at a bigger scale — the sheet's `pattern` (`section`) already carries "this is a detail". Writing the sheet type into `element_type` splits one mark across two vocabularies and breaks the §7 spec join. See §6b.

### 0.5 Dimensions are integer millimetres

- Member size → **`width_mm`, `height_mm`, `thickness_mm`, `depth_mm`** as numbers.
- ❌ Never a packed string: `"size_m": "0.20x0.40"` is wrong → `width_mm: 200, height_mm: 400`.
- ❌ Never a metre variant of a member dimension (`width_m`, `height_m`, `depth_m`, `cap_width_m`, `cap_length_m`, `cap_thickness_m`, `section_mm: "200x200"`). This applies to footings and pile caps exactly like beams and columns — see §6b.
- Levels, spans, grid positions and site distances stay in metres (`level_m`, `span_length_m`, `pos_m`) — those are *positions*, not member sizes.
- **Metre fields are numbers, never strings.** `"+0.60"`/`"±0.00"` → `level_m: 0.6`/`0.0`; an annotated value (`"0.50 (sub-area at +0.40)"`) → the leading number, full text in `level_m_printed_as`.
- A **multi-span member** puts its list in `spans_m[]` (plural); `span_m`/`span_length_m` is always a single number.
- A printed **two-way count** (`4+4` on a footing mat) → `count` = the sum, printed text in `count_printed_as`. **Mixed diameters** (`16+12`) → `dia_mm` = first, `mixed_dia_mm` = the list, printed text in `dia_mm_printed_as`. Variable stirrup spacing (`@0.10 ends, @0.25 mid`) → `spacing_mm` = the smallest + `variable_spacing: true`, detail in `note`.
- When the drawing prints metres, convert **and** keep the printed text (§0.7).

### 0.6 Rebar is always an object, never a string

❌ `"main_bar": "2-Ø16มม. top + 2-Ø16มม. bottom"` · ❌ `"stirrup": "Ø6มม.@0.20ม."`

✅ the §6 object form. Also:
- **`stirrup` is the only name** — `tie`, `tie_bar`, `stirrup_or_tie`, `tie_or_mesh` are all forbidden spellings of it.
- Spacing is `spacing_mm` (an integer), not `@0.20ม.` inside a string.
- `Ø` → `type: "RB"` always (§6).
- **`main_bar`/`stirrup`/`rebar`/`steel_section` are always single objects, never arrays.** Multi-layer reinforcement (a stair waist slab's main + distribution layers) goes in **`bar_layers[]`** — an array of layer objects each carrying its own `location` — so the object keys stay type-pure.

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
- Every point ref must resolve against that house's `หน้า00_gridline.json`. If it doesn't, the grid master is missing a line (§4 beam-endpoint rule / rule 4) — fix the master, don't invent a ref.

### 0.9 `pattern` must be one of the 25 in §1

Never coin a new one. House 07 invented `detail`, `diagram` and `elevation` and needed 21 files remapped. A detail sheet is `section`; an elevation is `side_profile`; a schematic diagram is `side_profile`; a site plan is `site_plan`, not `plan`.

**The plan family is six values, not one** (`beam_plan` · `footing_plan` · `roof_frame_plan` · `column_plan` · `slab_plan` · `etc_plan`; split 2026-08-28, `column_plan` and `slab_plan` added 2026-11-18 by Makham — see §1). Check the five specific ones first; `etc_plan` is the residual for a plan sheet that is none of them (architectural/MEP layout). **`plan` is a dead spelling** — it was renamed to `etc_plan` in the same pass, files included. Do not add a seventh by analogy. **`column_plan` and `slab_plan` are gated (§1): until the gate is lifted, columns and slabs stay in the file of the plan they were read from (a column-only or slab-only plan is `etc_plan`).**

**A summary table is `schedule`; a bar-bending (cut-list) table is `bbs_schedule`** — the test is whether a row describes a *member* or a single *bar* (§1 #17). A soil borehole log is `soil_boring_log`, never `schedule` or `notes` (§1 #18).

### 0.10 Before you call a house finished

**Run `python tools/check_format.py <house-folder>` — it checks every item below and exits non-zero on failure.** Do not hand-audit; a 1000-house set cannot be eyeballed.

- [ ] every file parses as JSON
- [ ] every file has the §2 wrapper fields
- [ ] `pattern` is one of the 25 in §1 — and `column_plan` (#20) and `slab_plan` (#25) are not emitted until §1's gate is lifted
- [ ] no file carries `phase_note` (§2a)
- [ ] a `beam_section` / `footing_section` / `column_section` file holds only that kind's element types (§1 #22-24, 2026-11-18)
- [ ] wrapper `confidence_score` is `null` and `confidence_flags` is `[]`; no element carries `confidence_score` / `confidence_flags`; no `note` / `offset_note` anywhere (§0.0, from 2026-11-18 — legacy files excepted)
- [ ] no array named after a kind of drawing element (§0.1)
- [ ] grid master nests `x_lines`/`y_lines` under `grid{}` (§0.1)
- [ ] every sheet that prints a level contributed to `z_levels[]`, and every sheet that prints a dimension row contributed to `dimension_chains[]` (§4) — a sheet with printed numbers and no contribution is an unread sheet, not a clean one
- [ ] every printed number that landed in neither is in `unassigned_dimensions[]` (§4)
- [ ] a `level_master` file (§4b, 2026-11-18): floor codes unique and bottom to top, every `level_m` / `structure_level_m` equal to a `z_levels[]` value of the same house's grid master — checked when the file exists; houses finished before 2026-11-18 have none
- [ ] every tick of an x/y chain that touches a known line is a line in `x_lines[]`/`y_lines[]`, and `"edge"` is left only on chains that touch none (§4 rule 4, 2026-09-27)
- [ ] a `notes` file uses only `sections[]` + `notes{}` — no `notes_sections`/`spec_notes`/`raw_text`/per-topic one-off key (§4a)
- [ ] `notes{}`'s four flat fields match the nested values they alias, and `cover` is in **mm** not metres (§4a, §0.5)
- [ ] no rebar left as a string (§0.6)
- [ ] no packed size string (§0.5)
- [ ] `grid_ref` notation: no dashed point, no `grid`/`dummy` word (§0.8)
- [ ] every point `grid_ref` resolves against `หน้า00_gridline.json` (§0.8)
- [ ] no `element_id` collides with a different member on the same sheet (§0.3)
- [ ] point elements merged to one entry per mark (§4), span elements left atomic (§4)

**~~The one allowed exception to the merge check~~ — retired 2026-11-18 (§0.0).** It let two entries of the same point mark stay separate when they differed in `confidence_score` or `note`. Both fields are gone, so the same mark always merges into one entry. Legacy files may still carry such pairs; `check_format.py` reports them as notes. Anything else that trips the checker is a real defect.

## 1. Pattern taxonomy — 25 types

**The plan family sits first (#1-4, plus #20 `column_plan` and #25 `slab_plan`) because it is where the money is** — every beam, footing, column, slab and roof member that reaches a BOQ or a BBS arrives through one of these six. `column_plan` (#20) and `slab_plan` (#25) were appended on 2026-11-18 instead of being inserted next to #2, so that every existing "#N" reference in this spec and in the tools stays valid. Everything from #5 to #19, and #21-24, is either a spec source, a reference page, a companion file, or not a drawing of the building at all.

| # | pattern | description |
|---|---|---|
| 1 | `beam_plan` | **structural beam plan** (แปลนคาน) — beams with marks, `grid_ref_start`/`grid_ref_end`, spans. Added 2026-08-28 *(draft — see the consumer gate below)* |
| 2 | `footing_plan` | **structural footing plan** (แปลนฐานราก) — footings/pile caps as point elements with `grid_refs[]` + `count`. A sheet drawing both a spread-footing and a pile-footing system is two views (§3), one file each. Added 2026-08-28 *(draft)* |
| 3 | `roof_frame_plan` | **structural roof-framing plan** (แปลนโครงหลังคา) — roof beams/purlins/trusses with marks and grid refs. **Not `roof_plan`** (#15), which is the architectural roof plan and carries no structural marks. Added 2026-08-28 *(draft)* |
| 4 | `etc_plan` | **any other top-down plan with `grid_ref` — the "none of the above three" bucket.** This is the value formerly spelled `plan`: **renamed 2026-08-28, same value, and every existing `plan` file was renamed with it.** `plan` is now a dead spelling — see the legacy note below |
| 5 | `section` | detail section — rebar spec/dimensions. **Since 2026-11-18 the three common kinds have patterns of their own (#22 `beam_section`, #23 `footing_section`, #24 `column_section`, Makham: so the model cannot drift between kinds); `section` stays for every other detail section (slab, stair, joint…) and for the 1,218 legacy files until they are relabelled one sheet at a time.** A section page is first cut into single sections, then each cut is sorted into one of the four (t07 pass table, numbering of 2026-11-18: pass 3 cuts, pass 4 sorts by the mark's prefix, the model only when there is no usable mark); a sheet that mixes kinds therefore becomes one view per section (§3). A bar-cutting table is `bbs_schedule` (#17), not a section |
| 6 | `schedule` | summary table of any element/material type (column, beam, door, window, fence, etc. — not limited to column/beam) |
| 7 | `notes` | project-level requirements/specs |
| 8 | `index` | drawing set table of contents |
| 9 | `material_list` | bill of quantities (BOQ) |
| 10 | `site_plan` | site layout |
| 11 | `side_profile` | non-top-down view, e.g. elevation/building section (not site/terrain info, no rebar) — formerly named `site_profile` |
| 12 | `grid_master` | the house's one grid reference file (`หน้า00`) — main + dummy grids, `z_levels[]`, and every printed dimension (§4). **Renamed from `gridline` 2026-08-28, files included**; the old name claimed to also cover a "per-page companion" file, and an audit of all 93 gridline files found **every one is a `หน้า00` master — the companion never existed.** `gridline` is a dead spelling. Note this renames the *pattern value only*: the **filename stays `<house>_หน้า00_gridline.json`**, because every other file points at it by name through `grid_source` |
| 13 | `title` | cover page *(draft — no field-set verified yet)* |
| 14 | `symbol` | symbol/legend page *(draft)* |
| 15 | `roof_plan` | **architectural** roof plan only — ridge/hip lines, eave overhangs, roofing material. **A structural roof-framing plan (แปลนโครงหลังคา — beams/purlins with marks and grid refs) is `roof_frame_plan` (#3), NOT `roof_plan`** (pinned 2026-08-21, see the warning under this table) *(draft)* |
| 16 | `misc` | เบ็ดเตล็ด — whole-series catalog/promotional/reference pages that aren't about this house's own construction (e.g. a back-cover price-comparison table across all 10 designs in the series, or a cover collage of every design's render) — added 2026-07-14, previously misclassified as `title` |
| 17 | `bbs_schedule` | **bar bending schedule (ตารางตัดเหล็ก)** — one row per individual BAR, not per element: `bar_mark`, `shape_code`, bend dimensions `len_A`/`len_B`/`len_C`, `qty`, `grade`. **Split from `schedule` 2026-08-04 because the granularity is genuinely different** — a `schedule` row describes one member (`C1`: 200×200, 4-Ø12), a `bbs_schedule` row describes one cut bar (`C1`/`T1`: Ø12, shape 00, 4.5 m, ×2). Putting both under `schedule` forced two incompatible row shapes into one pattern *(draft — no field-set verified against a real extraction yet)* |
| 18 | `soil_boring_log` | **soil investigation / borehole log (รายงานเจาะสำรวจดิน)** — SPT blow counts, stratum table, lab results, groundwater level. Not a drawing of the building at all: it carries no `grid_ref`, no element marks, no rebar. Container is `elements[]` per §0.1 with `element_type: "soil_layer"`, plus wrapper-level `borehole_id` and `groundwater_level_m`. Added 2026-08-04 — Constistant already reads these live (`QT_PROMPT_SOIL_BORING_LOG` → `js/site/site-index.js`, feeding Foundation Design's bearing-capacity calc) and had no pattern to record them under *(draft — no field-set verified against a real extraction yet)* |
| 19 | `unknown` | doesn't fit any of the other 20 |
| 20 | `column_plan` | **the column view of any structural plan** (แปลนเสา / ผังเสา, and the column marks on a footing or beam plan) — columns and pedestals as point elements with `grid_refs[]` + `count`, the same merged point shape as `footing_plan` (§4: one `element_id` once per file). Added 2026-11-18 (Makham) to take columns out of the footing and beam tasks: pass 0 sends every plan that shows column marks to the column task as its own view (one page, several patterns, §3; t07 pass 0 already has a `plan_column` subtask). Measured 2026-11-18: columns sit today inside 112 footing plans, 147 beam plans, 53 `etc_plan` and 28 roof-frame plans (183 houses). **Gated** — until the gate under the plan family is lifted, columns stay in the file of the plan they were read from |
| 21 | `level_master` | **the house's one level file** (`<house>_หน้า00_level.json`, companion of the grid master) — which printed level is which floor: `floor_level` code → `level_m`, so storey heights stop being guessed. Added 2026-11-18 (Makham). Container `level{ floors[] }`; see §4b |
| 22 | `beam_section` | **beam detail section** — `beam`, `tie_beam`, `girder` with width, depth, `main_bar` top/bottom/middle, `stirrup` (§6). Added 2026-11-18 (Makham) |
| 23 | `footing_section` | **footing / pile-cap detail** — `footing`, `pile_cap`, `pile`: size, bottom mat `main_bar`, `top_bar`, `dowel_bar`, cover, lean concrete (§6b). Added 2026-11-18 (Makham) |
| 24 | `column_section` | **column detail section** — `column`, `pedestal`: size, `main_bar` (one count), `stirrup` (§6). Added 2026-11-18 (Makham) |
| 25 | `slab_plan` | **the slab view of any structural plan** (แปลนพื้น, and the slab tags `SO`/`SI`/`SX`/`ST` and precast-plank layouts on a beam or other plan) — `slab`, `precast_plank_detail`, `precast_plank_placement_detail` (§9, §10). Added 2026-11-18 (Makham: "we forgot slab plans"); pass 0 already has a `plan_slab` subtask. Measured 2026-11-18: slab elements sit today inside 223 beam plans, 86 `etc_plan`, 5 footing plans and 4 roof-frame plans (318 files, 186 houses). **Gated** like `column_plan` — until lifted, slabs stay in the file of the plan they were read from |

**`plan` is a dead spelling — it was renamed to `etc_plan` on 2026-08-28, files included (Makham's ruling).** All 899 existing plan files across both trees were rewritten in that pass, so `pattern: "plan"` should no longer appear anywhere in this repo. A consumer may keep accepting the old string defensively, but nothing produces it.

**What a legacy `etc_plan` does and does not tell you.** For a **newly extracted** file, `etc_plan` is a positive statement: the extractor checked #1, #2, #3, #20 and #25 and none matched. For one of the **899 renamed** files it is only "an unclassified plan" — the old `plan` value carried no kind information at all, so the rename neither added nor destroyed any, but it also did not verify anything. Most of those files are in fact beam plans or footing plans.

Consequences, both directions:

- **Do not read `etc_plan` as "definitely not a beam plan"** while renamed files are still in the set. A pass that skips `etc_plan` while hunting for beams would skip real beam plans.
- **Re-labelling a renamed file to #1/#2/#3 is real work, not a regex** — read the sheet, apply the test table, pick one, one file at a time. That is a separate future pass; it is not what the rename did.
- There is no per-file marker separating the two cases. The boundary is this entry plus the `primary_rawjson_schema_edit_log.md` row and the git commit for that pass — deliberately, rather than stamping a mechanical note into 899 files' `warnings[]`, which is a channel for genuine reading ambiguity (§2a), not for bookkeeping.

### The plan family — `beam_plan` · `footing_plan` · `roof_frame_plan` · `column_plan` · `slab_plan` · `etc_plan` (split 2026-08-28; `column_plan` and `slab_plan` added 2026-11-18)

`plan` was one pattern doing four jobs, so a consumer could not tell a beam sheet from a footing sheet without reading `sheet_name` free text. #1-3, #20 and #25 name the five that carry structural quantities; **#4 `etc_plan` is everything else, and is defined by exclusion, not by content.**

The test is what the sheet carries, exactly as in the `roof_plan` rule below:

| The sheet shows | pattern |
|---|---|
| Beams with marks + two grid endpoints each (แปลนคาน, แปลนคาน-พื้น) | `beam_plan` |
| Footings/pile caps as points with `grid_refs[]` (แปลนฐานราก) | `footing_plan` |
| Roof beams / purlins / trusses with marks (แปลนโครงหลังคา) | `roof_frame_plan` |
| Column marks as points with `grid_refs[]` — on a column plan, or on a footing/beam plan as a second view | `column_plan` (**gated** — until lifted, columns stay in the plan they were read from) |
| Slab tags (`SO`/`SI`/`SX`/`ST`) and precast-plank layouts — on a slab plan, or on a beam plan as a second view | `slab_plan` (**gated** — until lifted, slabs stay in the plan they were read from) |
| A top-down plan with `grid_ref` that is **none of the five above** | `etc_plan` |
| Ridge/hip/eave/roofing material, no structural marks | `roof_plan` (#15) |
| Site/lot layout, not the building itself | `site_plan` (#10) |

**`etc_plan` in full — what it does and does not mean.** It means exactly one thing: *a plan sheet that is not a beam plan, not a footing plan, not a roof-framing plan, not a column plan, and not a slab plan.* It is a residual bucket, so it is defined by what it excludes, and the exclusion test is the only test. Known members today:

- **Column plan** (แปลนเสา) — columns as point elements with `grid_refs[]`. **`column_plan` (#20) since 2026-11-18, but gated:** until the column-plan gate below is lifted, a column-only plan is still `etc_plan` and columns on a footing/beam plan stay in that file; never write `column_plan` early.
- **Slab / floor plan** (แปลนพื้น) — slab markers `SO`/`SI`/`SX`/`ST` (§10). **`slab_plan` (#25) since 2026-11-18, but gated:** until the gate below is lifted, a slab-only plan is still `etc_plan` and slab tags on a beam plan stay in that file.
- **Architectural floor plan / layout** — rooms, doors, windows, walls with grid refs.
- **Sanitary / electrical / mechanical layouts** drawn top-down over the same grid.
- **Post-tension TENDON LAYOUT sheets** — tendons only (`element_type: "tendon"`, §0.4). The beams and slab tags that show through from the MILD STEEL sheet of the same floor are not extracted a second time (added 2026-11-18, house 174).
- **A mixed structural plan** whose views genuinely cannot be separated (rare — try §3 first: a sheet with a footing view *and* a beam view is two files, `footing_plan` + `beam_plan`, not one `etc_plan`).

Rules that follow from it being a residual:

- **Never invent a seventh specific value.** An electrical layout is `etc_plan`, not `electrical_plan`. If one earns its own pattern later it gets added to the table above, never coined inside a house file (§0.9) — that is exactly how `column_plan` and `slab_plan` arrived (2026-11-18: Makham's decision, a table row, a gate).
- **`etc_plan` is a last resort, not a default.** Check #1, #2, #3, #20 and #25 first. Reaching for `etc_plan` because the sheet is crowded or hard to read is how a beam plan's beams stop reaching the BOQ — the same failure the `roof_plan` warning below records. When genuinely unsure, pick the specific one that matches the marks you can read and say so in `warnings[]`.
- **It is not a dumping ground for non-plans.** No `grid_ref` and not top-down → it is `side_profile`, `section`, `schedule`, `notes`, `misc` or `unknown`, never `etc_plan`.

**Four traps, all found the hard way on 2026-08-28 while re-labelling the 183 legacy `etc_plan` structural sheets in `json_แก้ไขแล้ว/`.** Each one silently produces a plausible-looking wrong answer, so they are recorded here rather than left to be rediscovered:

- **`แป` is a substring of `แปลน`.** `แป` alone means *purlin* (a roof member), but `แปลน` means *plan* and starts the title of essentially every plan sheet in the corpus — so matching a bare `แป` as a roof signal calls **every Thai plan sheet a roof-framing sheet**. Match the compound words only: `แปเหล็ก`, `แปหลังคา`, `โครงหลังคา`, `โครงสร้างหลังคา`, `จันทัน`, `อกไก่`.
- **`sheet_name` on a multi-view page names every view on it, not this one.** A page whose `sheet_name` is `"แปลนอะเส, แปลนโครงหลังคา"` produces two files (§3), and reading `sheet_name` on the first one labels the tie-beam view a roof-framing sheet. **`view_title` is the field that describes this view**; fall back to `sheet_name` only when there is no `view_title`.
- **A คานอะเส / ring-beam plan is a `beam_plan`, even when it is filed as `*_beam_roof` or `*_roof_beam`.** The อะเส sits at the top of the wall and carries the roof, so its sheet is often named for the roof — but the roof *frame* (จันทัน / แป / โครงหลังคา) is always a separate sheet, and that separate one is the `roof_frame_plan`. If a house has both, the อะเส sheet is the beam plan.
- **A `roof_frame_plan` can contain no beam-shaped element at all.** A steel roof frame is often typed `steel_member` throughout (or `truss`/`purlin`/`rafter`), so a classifier keyed only on `element_type` finds nothing and falls through to `etc_plan`. When the title says `โครงหลังคา`/`โครงสร้างหลังคา`, that is sufficient on its own.

Applies to all six equally:

- **A sheet carrying two of these is a multi-view page (§3)** — split it, one file per view, each with its own pattern. A single sheet showing footing plan + beam plan produces `_view1_footing_plan.json` (`footing_plan`) and `_view2_beam_plan.json` (`beam_plan`).
- **Element shapes do not change at all.** A `beam_plan` element is the same atomic-segment shape as before (§4), a `footing_plan` or `column_plan` element is the same merged point shape (§4). Only the wrapper's `pattern` value is new — nothing inside `elements[]` moves.
- `floor_level`, `grid_source` and every other wrapper field apply unchanged to all six.

**✅ CONSUMER GATE — LIFTED 2026-08-28.** All four values are safe to emit. The gate existed because Constistant's `buildElements()` filtered on the literal string `'plan'` and `ADAPTED_PATTERNS` listed six values, so a file labelled `beam_plan` would have been stored raw with a warning and **every beam on it would have silently disappeared from BOQ and BBS** — the identical failure that cost 8 houses their roof beams (see the `roof_plan` warning immediately below). Closed in the same pass as the rename, in this order (consumer first, files last — the reverse order would have zeroed every house's BOQ in between):

1. `Constistant/js/drawing/raw-extraction-adapter.js` — `PLAN_PATTERNS` accepts all four plus the dead `plan`, used by both `buildElements()` and `ADAPTED_PATTERNS`
2. `tools/check_format.py` — `PATTERNS` set widened; the roof-framing check now accepts `roof_frame_plan`
3. the 899 legacy files renamed `plan` → `etc_plan`

**The three section-kind patterns (#22-24) need no gate.** Constistant already treats any pattern name containing `section` as `section` (with a vocabulary warning), so a `beam_section` file loses nothing even on the deployed app; the 2026-11-18 adapter change makes it silent.

**⛔ COLUMN-PLAN / SLAB-PLAN GATE — OPEN (2026-11-18).** `column_plan` and `slab_plan` are defined above but **must not be written into any file yet.** Everything below says `column_plan`; it holds word for word for `slab_plan` (slabs instead of columns; adapter, checker and table steps were done for both together). Same lesson as the gate above, same failure if skipped: Constistant's `PLAN_PATTERNS` does not know the value, so a `column_plan` file would be stored raw with a warning and **every column on it would drop out of BOQ and BBS**, and `check_format.py` would reject the file. Until all three steps are done, columns stay where they are read today (a column-only plan is `etc_plan`; columns on a footing/beam plan stay in that file) — in hand extraction (op01 / op03 / op04) too. Order matters, consumer first:

1. `Constistant/js/drawing/raw-extraction-adapter.js` — add `column_plan` to `PLAN_PATTERNS` (used by `buildElements()` and `ADAPTED_PATTERNS`). **Written and tested 2026-11-18 (`tests/raw-extraction-patterns-2026-11-18.test.js`, whole suite 2708/2708), NOT yet merged or deployed — the gate stays open until it is.** The same change makes the adapter read `level_master` and the `"span": [start, end, length]` form.
2. `tools/check_format.py` — add it to `PLAN_FAMILY`. **Done 2026-11-18.**
3. the Pass 2 prompt and the t07 builder (`pass2/KEYS.json`) — a `plan_column` task (Pass 0 already sorts views to `plan_column`), and the builder moving columns out of the footing/beam targets into the column view. **Not done.**

Only then move the existing columns into `column_plan` views (340 files in the protected folders, count of 2026-11-18): one sheet at a time, not a regex, same as the re-labelling note under the plan-family table.

**✅ Pass 2 prompt taught the split — done 2026-08-29.** `tune_ai/t03/pass2_used/plan.md` carries the full sheet-content → pattern decision table (all four values, the `plan_beam`-splits-into-two trap, the `roof_plan` trap) and `gridline.md` already emits `pattern: "grid_master"`. A model run through pass 2 now picks the specific value instead of defaulting to `etc_plan`. Pass 0 (page classification, before pattern is even decided) does not need this — it only sorts pages into subtask folders (`plan_footing`/`plan_beam`/etc., §1 table in `pass_design.csv`), not into the four output pattern values.

### ⚠️ `roof_plan` vs `plan` — a real, live data-loss bug (found 2026-08-21)

**A roof-framing plan carries real structural beams and must be `pattern: "plan"`.** Audited across all 11 houses: all 12 roof-framing files are `discipline: "structural"`, but **4 were written as `pattern: "plan"` and 8 as `pattern: "roof_plan"`**. Downstream, Constistant's `buildElements()` reads **only** `pattern === 'plan'` — so **the roof beams in those 8 houses have never reached a BOQ at all**, silently.

The test is what the sheet carries, not what it is called:

| The sheet shows | pattern |
|---|---|
| Beams/purlins with element marks, grid refs, spans (แปลนโครงหลังคา, roof frame plan, roof beam plan) | `roof_frame_plan` (#3) |
| Ridge/hip lines, eave overhang, roofing material, slope arrows — no structural marks | `roof_plan` (#15) |

A sheet showing both is a multi-view page (§3): split it, one file each.

**The 2026-08-28 split does not change this rule, it names it.** A structural roof-framing sheet was `plan` and is now `roof_frame_plan` — what must never happen, before or after the split, is calling it `roof_plan`. Nor is it `etc_plan`: a roof-framing sheet has its own specific value now, so the residual bucket is the wrong answer for a freshly read one. (A renamed legacy file may well be sitting in `etc_plan` — see the legacy note above; fixing those is the separate re-labelling pass.) The 59 existing `roof_plan` files are **not** all wrong: audit each against the two rows above before touching anything.

**Automation scope:** `run_pipeline.py` auto-extracts the plan family plus `section` / `schedule` / `notes` / `grid_master` / `material_list`. The other 16 patterns (`index`, `site_plan`, `side_profile`, `title`, `symbol`, `roof_plan`, `misc`, `bbs_schedule`, `soil_boring_log`, `unknown`, `level_master`, `beam_section`, `footing_section`, `column_section`, and `column_plan` / `slab_plan` once their gate is lifted) are manual-extraction only for now — which is exactly what this workflow (Claude reading pages directly) is for.

## 2. Required fields on every file (wrapper level)

```
png, doc_page, discipline, sheet_code, sheet_name, pattern,
source_image, confidence_score, confidence_flags, warnings
```

**Who fills each of these: §0.0 (2026-11-18).** All are stamped by code or read by OCR; `confidence_score` is always `null`, `confidence_flags` and `warnings` always `[]`. They stay in the stored file so readers keep working.

**`warnings` is always `[]`, in every pattern (2026-11-16).** All 5,336 files that had warnings were emptied by `tools/empty_warnings.py` (beam_plan first, then the rest): the text mixed edit history ("CORRECTED 2026-08-24 …") with real notes, and the model learned to copy it. Keep the key and leave it empty. **Wherever this spec says "say so in `warnings[]`" or "flag it in `warnings[]`", write nothing there** — decide and move on. (Until 2026-11-18 this said to lower `confidence_score` / add a `confidence_flags` entry instead; both are retired too, §0.0.) `check_format.py` fails any file with a non-empty list. The old text is in git history (commit f1a1dd5 and earlier).

**`discipline` — closed vocabulary (pinned 2026-08-21 after an audit found two spellings of one value):** `structural` · `architectural` · `sanitary` · `electrical` · `mechanical` · `boq` · `material_list` · `general` · `front_matter` · `regulatory` · `misc`. **`architecture` is wrong — the canonical spelling is `architectural`.** The audit counted 182 files spelling it one way and 157 the other, across the same 11 houses. Nothing consumes `discipline` today so nothing is broken yet, but the first code that filters on it would silently drop roughly half the set. Anything genuinely outside this list goes to `misc`, not to a newly-invented word.

**`source_image`** = full path of the source image, e.g. `"image/<house>/<house>_หน้า19.png"` — every file coming from the same page (e.g. `_view1_...`/`_view2_...`) must have the exact same value.
**Exception:** the grid-master file `<house>_หน้า00_gridline.json` uses `source_pages` (array of every `source_image` used to confirm the grid) instead.

**Grid-master `png`/`doc_page` convention (pinned 2026-08-09 after houses 14-18 drifted to the opposite encoding):** `png: "00"` (or `"00b"`, `"00c"`… for additional buildings per §11a), `doc_page: null` — never the reverse (`png: null, doc_page: 0`). It is a synthesized file with no real printed page, so `doc_page` (which means "position in the real document") stays `null`; `"00"` is just the file's own conventional tag, matching how every other page's `png` field already holds its page-number string.

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

- **`warnings[]` is append-or-rewrite only. NEVER delete a warning** — **void since 2026-11-16: `warnings[]` is always `[]` (§2).** When a later stage overturns an earlier reading, **rewrite** the warning so it records the reversal: what was believed, what overturned it, and how many sheets agreed. That reversal narrative is the single most valuable training signal in the file (precedent: the house-06 grid reversal, and house-07's `F16` vs `F18`, where three marks on the drawing beat one in the title block).
- **`phase_note` must be ABSENT from every finished file.** Stage 3 resolves each note (nothing goes into `warnings[]` — §2) and then deletes the field. A file still carrying a `phase_note` is by definition unfinished.
- A `phase_note` is never a substitute for a decision. If the stage that holds the evidence *can* decide, it decides and writes a `warnings[]` entry — same standing order as `op1`.
- Never put a `phase_note` on the grid master. A grid problem is escalated by re-running Stage 1, not annotated (see the README's `op2` escalation rule).

## 3. Multi-view pages

A page may contain multiple views/patterns — **inventory every view first** (prevents losing one), then write each out as a separate file per view (`_view1_footing_plan.json`, `_view2_beam_plan.json`, etc.).

**Since 2026-11-18 (§0.0) the inventory is pass 0's job and `views[]` is stamped by code. `pattern` is assigned per view, never per page,** so one page can feed several subtasks: a sheet with a footing plan and a beam plan goes to both.

## 4. Grid

- **Axis:** `x_lines` = horizontal along the top edge (usually numbers 1,2,3...) · `y_lines` = vertical along the side edge (usually letters A,B,C...)
- **grid_ref format — a dash means a RANGE, never a point** (confirmed project-wide 2026-07-13, applied to houses 01-05):
  - **Point** (a footing, a column, one end of a beam) = row letter + column number with **no dash**: `"C2"`, `"E'1"`, `"C3''"`. A prime on either part stays attached (`C1'`, `A''3`).
  - **Range/line/area** = dash between the two positions **on the same axis**: `"D-C"` (row range), `"1-2"` (column range). Two axes combine with `x`, vertical axis first: `"D-C x 1-2"`.
  - Point-type elements (footing/column) store position as an **array**, e.g. `grid_refs:["A1","A2"]`, never a comma-string.
  - Makham's reasoning: "it's just a point, not a line — only a line or area needs a dash." A beam's own line is already expressed by having separate `grid_ref_start`/`grid_ref_end`, so each endpoint is a point and takes no dash.
  - ⚠️ **After any bulk regex that strips these dashes, re-check `sheet_code`** — a value like `"S-04"` matches the same letter-dash-digit shape and gets corrupted to `"S04"`. This has happened on three separate houses (สิ่งที่ต้องแก้ items 26, 31).
- **Axis order rule:** always read/write the **vertical axis (y_lines, row letters) first**, then the horizontal axis (x_lines, column numbers) — the same row-before-column order a point ref uses (`"A1"`), and it must also apply to any combined-range free-text `grid_ref` on `plan` elements, e.g. write `"D-C x 1-1'"` (row range first, `x`, then column range), not `"1-1' x D-C"` (บทเรียนจาก 2026-07-13: ตอนย่อ `grid_ref` ในบ้าน 1 หน้า06_floor_plan.json ให้สั้นลง เขียนแกน x ก่อนโดยไม่ตั้งใจ ต้องกลับมาแก้)
- **Span:** read from the grid, never eyeballed off the drawing. **Amended 2026-08-29 (Makham's order):** when a span is printed nowhere, the model *may* recover it by proportion against two grid lines whose `pos_m` it already knows — that is measuring against a ruler printed on the same image, which is what the grid master exists for, and it replaces a `null` that used to be thrown away. It is a derived value, never a read one, so it carries its own `span_source` (below) — written as the string `"~N.NN"` in `span[2]` since 2026-11-18 (§0.0). A printed value always wins; the x-axis scale measures x spans and the y-axis scale measures y spans (a cropped/rescaled scan does not stretch both axes equally); a diagonal span stays `unresolved`. Same rule extends to a dummy grid line whose position the dimension chain never prints. Does **not** apply to a sheet with no grid to calibrate against, e.g. `section` — there, an unprinted dimension is still `null`.
- **`span_source` enum:** `grid_table` / `local_dimension` / `scaled_from_grid` / `unresolved` / `n/a`
  - **Filled by code since 2026-11-18** from the `span` array (§0.0); the model no longer writes it. Only these five values exist. `printed_dim`, `printed_dimension`, `user_confirmed`, `measured_pixel` were found on 5 legacy beams (count of 2026-11-18) and are not values.
  - `scaled_from_grid` added 2026-08-29 — measured by proportion against the grid, per the amendment above. Kept distinct from `grid_table` deliberately: `grid_table` means the number was read off the grid, `scaled_from_grid` means it was derived from it, and a consumer must be able to tell those apart.

### Dummy grid
- A line not on a named/printed main grid (structural, or any dimension tick per the 2026-09-27 rule below) → name it with a **prime** appended to the main grid **above it (y-axis) / to its left (x-axis)** — **not** the nearest one (corrected by Makham 2026-07-24, สิ่งที่ต้องแก้ item 51; the earlier wording here said "nearest" and was wrong). E.g. a line at 5.2 between named `2`(5.0) and `3`(8.5) is `2'`, even though it is far closer to `2` than to `3` — the rule is direction, not distance, so it stays stable when a grid is later re-based.
- **Dummy labels are always renamed into this rule — including ones Makham gave or confirmed himself** (Makham, 2026-09-29, reversing the old "a hand-supplied label is never normalized" exception). A dummy name is a position label, not something printed, so when a line is added inside a run, or a label breaks the rule (house #04's `A'`(1.6)/`E'''`(4.2) in the E-to-C range), the whole axis is re-sequenced and **every grid ref in every page of the house is renamed with it** — done by `tools/gridfix.py` (op_fix), which refuses to write unless each ref still resolves to the same position.
- **The one thing never renamed is a grid name printed on the drawing.** House #12 prints `ง'` and `ค'` in their own bubbles — they are named lines, not dummies. A dummy whose rule name would collide with a printed name keeps its current name, flagged in `warnings[]`.
- **Prime ordering when more than one dummy line falls in the same gap:** scan in standard reading direction — x-axis left→right, y-axis top→bottom. First line found = 1 prime (`A'`), next one = 2 primes (`A''`), and so on (`A'` must always sit left of/above `A''`)
- **Origin (0,0)** must always be the leftmost/topmost main grid (`type:"named"`) — a dummy grid must never take over the origin position. If a dummy grid falls before the origin (further left/up than the first main grid), use a **negative** `pos_m` instead, e.g. `{"id":"1'","pos_m":-0.80,"type":"dummy"}`
- **Before-origin dummies share the first main grid's prime sequence** (written down 2026-09-27 from what houses 04/05/17/22/33/39/40 already do): dummies before the first main grid and dummies in the gap after it are *one* sequence, primed in reading order. So `1'` = -0.60, `1''` = 1.10, `1'''` = 2.30 — never a second `1'` on the far side. House 17's x axis runs `1'` through `1'''''''` (7 dummies) this way.
- `pos_m` is always read from an actually-printed dimension line — never guessed

### The grid master records EVERY printed dimension in the whole set (added 2026-08-21, Makham)

**The rule: sweep every page in the drawing set, and record every printed dimension value you find. Nothing gets dropped for not fitting a category.**

Before this section the grid master held only `x_lines[]`/`y_lines[]` — the **resolved** position of a named or dummy grid line, and a dummy line only gets created when a beam endpoint needs one (§ beam-endpoint rule above). That threw away most of the real numbers on a sheet:

- Offsets from a building/slab **edge** to the first or last grid (`1.30` before grid `1` on the A-05 elevation) — nothing sits on them, so no dummy grid, so they vanished.
- **Vertical levels entirely.** `+3.75 ระดับหลังคาน`, `+0.60 ระดับพื้นชั้น 1`, `±0.00 ระดับอ้างอิง` are printed on every elevation and section in the set, and there was **no field anywhere to put them** — `x_lines`/`y_lines` are plan axes only. Elements carry a `level_m`, but nothing registered which levels the building actually has.
- Anything else with a number next to it: a `0.60` stub past the last grid, `บัวปูนปั้น กว้าง 0.10 ม ลึก 0.10 ม`, an eave overhang.

**Elevations (`side_profile`) and sections are first-class sources, not afterthoughts.** They reprint the column-grid markers (`1`,`2`,`3`… / `A`,`B`,`C`…) along the bottom edge with a full dimension chain exactly like a plan sheet, **and** they are the only place the Z axis is printed at all. Never assume a non-top-down view has no grid data — check the sheet.

`grid` gains three optional sibling arrays. All three are **transcription, not derivation** — write down what is printed, do not compute, collapse, deduplicate, or "tidy" anything.

#### 1. `z_levels[]` — the vertical axis, same role as `x_lines`/`y_lines`

```json
"z_levels": [
  {"id": "ระดับอ้างอิง",   "level_m":  0.00, "type": "datum",  "source_image": "..._หน้า15.png"},
  {"id": "ระดับพื้นชั้น 1", "level_m":  0.60, "type": "named",  "source_image": "..._หน้า15.png"},
  {"id": "ระดับหลังคาน",   "level_m":  3.75, "type": "named",  "source_image": "..._หน้า15.png"}
]
```

- `id` is the **printed Thai label, verbatim** — do not translate, do not normalize to `F1`/`FL1`. If a level is printed with only a number and no label, use `null` and let `level_m` carry it.
- `type`: `datum` for the ±0.00 reference, `named` for a labelled level, `dummy` for a level implied by a dimension chain but never labelled.
- `level_m` is signed and relative to the datum, exactly as printed (`-0.30` for a below-datum level).
- One `z_levels[]` for the whole building, merged across every sheet that prints levels — same "one master per building" rule as the plan axes (§ Master file below).

#### 1a. Which level is which floor → `level_master` (§4b)

`z_levels[]` records every printed vertical tick but cannot say which tick is a floor: house 174's holds `id: null`, `"FLAT SLAB 0.35 M. THK."` as an id, and `GS` twice (0.00 and 0.30). The join from the floor codes (`F1`, `F2`, `RF`) to those ticks is a file of its own, §4b — it is not a field of the grid master.

#### 2. `dimension_chains[]` — every printed dimension row, on any axis

```json
"dimension_chains": [
  {
    "axis": "x",
    "source_image": "..._หน้า15.png",
    "segments": [
      {"from": "1'", "to": "1", "value_m": 1.30},
      {"from": "1", "to": "2", "value_m": 4.00},
      {"from": "2", "to": "3", "value_m": 3.00},
      {"from": "3", "to": "3'", "value_m": 0.60},
      {"from": "3'", "to": "3''", "value_m": 0.70}
    ]
  },
  {
    "axis": "z",
    "source_image": "..._หน้า15.png",
    "segments": [
      {"from": "ระดับอ้างอิง", "to": "ระดับพื้นชั้น 1", "value_m": 0.60},
      {"from": "ระดับพื้นชั้น 1", "to": "ระดับหลังคาน", "value_m": 3.15},
      {"from": "ระดับอ้างอิง", "to": "ระดับหลังคาน", "value_m": 3.75}
    ]
  }
]
```

- The x chain above uses house #01's figures (1.30 before grid `1`, then 0.60 + 0.70 past grid `3`). Under rule 4 below, its three non-grid ends are lines: `1'` at -1.30, `3'` at 7.60 and `3''` at 8.30. Before 2026-09-27 this example wrote them as `"edge"`, which is how those points got lost.
- `axis` is `x`, `y`, or `z`.
- `from`/`to` reference a grid `id` (or a `z_levels[]` `id` on the z axis). On the x/y axes every end of a chain that hangs off a known line is itself a line (the 2026-09-27 rule below), so it has an `id` — use it. The literal `"edge"` is left for one case only: a chain that touches **no** known line anywhere, so none of its ends can be given a position. **Never invent an id for a point you could not position.**
- Record **every** row actually printed, including the cumulative/total row (the `3.75` above, the `7.00` on the x chain). Redundant arithmetically, but printed — and a mismatch between the detail row and the total row is exactly the extraction error this array exists to catch.
- One entry per printed row per sheet; the same chain reprinted on three sheets gets three entries with three different `source_image` values. Do not deduplicate across sheets.

#### 3. `unassigned_dimensions[]` — the catch-all, so nothing is ever dropped

Every printed number that did **not** land in a chain or a level goes here, with whatever text was printed next to it:

```json
"unassigned_dimensions": [
  {"value_m": 0.10, "label": "บัวปูนปั้น กว้าง 0.10 ม", "source_image": "..._หน้า15.png"},
  {"value_m": 0.10, "label": "บัวปูนปั้น ลึก 0.10 ม",  "source_image": "..._หน้า15.png"}
]
```

- `label` is the printed text verbatim (Thai stays Thai) and is the only text on the entry — `note` was retired 2026-11-18 (§0.0).
- **This array is the reason the rule holds.** If a number doesn't fit anywhere else, it goes here — it never gets skipped. A page with numbers and an empty `unassigned_dimensions[]` means every number found a home, not that the page wasn't read.
- These are *not* grid data and nothing downstream uses them for span calculation; they exist so a later reader can see the full picture without re-reading the sheet.

#### 4. Every dimension tick is a line — even one nothing uses (added 2026-09-27, Makham)

**The rule: every point a printed x/y dimension marks gets a line in `x_lines[]`/`y_lines[]`.** It doesn't matter whether any element sits on it, or which kind of sheet printed it — plan, `side_profile`, section, roof. Makham's words: *"gridmaster จดจำระยะทุก ๆ ระยะ ในทุกหน้า แม้ระยะเหล่านั้นจะไม่ได้ใช้ก็ตาม"*.

- For each printed segment on the x or y axis, look at both of its ends. If an end sits on a line the master already has, reuse that line. Otherwise that end becomes a **new dummy line**.
- Its `pos_m` = the known line it hangs off ± the printed segments between them, added up. That is arithmetic on printed numbers, so it still counts as "read off a printed dimension line" (above). Before the origin, `pos_m` goes negative, same as any dummy.
- **Count example:** a `side_profile` prints the A–B gap split into 10 segments. The two outer ends are `A` and `B`, which already exist, so the 9 ticks inside become 9 dummies. They're primed off whichever of `A`/`B` is the upper line, e.g. `A'` … `A'''''''''`. If the 10 numbers are instead 10 separate distances measured from `A`, they mark 10 different points, so that's 10 dummies. The rule is one dummy per distinct point — count the points, not the numbers.
- **Which axis:** a chain belongs to the axis whose grid markers it runs between. Numbers (`1`,`2`,`3`) → x. Letters (`A`,`B` / `ก`,`ข`) → y. A front elevation usually carries x and a side elevation usually carries y — check the markers, not the sheet title.
- **One point = one line.** A tick at the same `pos_m` as an existing line (compare to the millimetre — some sets print 3 decimals, e.g. 1.725) *is* that line, even when another sheet printed it too. Two ticks with different `pos_m` are two lines. If two are within 0.05 m and look like the same edge printed twice, keep both and say so in `warnings[]` — don't pick one. `dimension_chains[]` still keeps every sheet's row separately (above) — that's where the per-sheet evidence lives, not here.
- **Not an axis tick:** a dimension inside one element's own detail. That means a section's width/depth, a pile cap's pile spacing (§6b) or a rebar spacing. It stays on the element as it always has. Rule 4 is about dimension rows that run along the building's grid axes.
- Naming, prime order and the before-origin rule are unchanged (§ Dummy grid). What this rule changes is how many dummies there are, not how they're written. With a lot of them, count the primes carefully — `check_format.py` flags a sequence whose primes are out of order along the axis.
- A chain that touches no known line at all (a floating detail dimension) can't be positioned, so it makes no line. Its row stays in `dimension_chains[]` with `"edge"` ends.
- **z axis:** same idea, already covered by `z_levels[]` — every tick on a z chain is a level. Use `type: "dummy"` when the drawing prints no label for it.
- **Why keep lines nothing uses:** a beam or footing read later — by a person or by the model on another sheet — can land on any of these points, and until now those were exactly the points the master had thrown away (house #04's 20 missing beams all sat on lines the master didn't have yet). A consumer that wants only structural lines can still derive them: they are the lines some element's `grid_ref` actually points at.

#### Relationship to the resolved axes

`x_lines`/`y_lines`/`z_levels` stay the **resolved, deduplicated** registry — that's what the pipeline consumes — and since 2026-09-27 they hold **every positioned point**, not only structural lines (rule 4 above). The three arrays above are the **raw transcript** proving where each resolved value came from, and holding everything that has no resolved home. Both live in the same master file; neither replaces the other.

All three arrays are optional in the sense that a sheet printing no dimensions contributes nothing — but a sheet that *does* print dimensions and contributes an empty array is an extraction failure, not a clean file.

### ~~Documenting genuine ambiguity in the grid master~~ — retired 2026-11-18 (§0.0)

**Do not write these three fields any more.** They were the extractor's own words about its reading, the same class as `note` and `confidence_*`. A line whose `pos_m` was scaled rather than printed stays identifiable without them: no `dimension_chains[]` tick lands on it. The text below only explains legacy files:

- **Per-line `confidence_score` / `confidence_flags`** on an individual `x_lines[]`/`y_lines[]` entry (same meaning as the element-level fields in §0.2) — use when one specific line is less certain than the rest of the file, instead of dragging the whole file's top-level `confidence_score` down uniformly. Precedent: house #06's `A'`/`D'` dummy lines (carry unidentified superstructure) and its `B` line (ambiguous printed digit, `3.00` vs `3.03`) each got their own score while the other, unambiguous lines stayed unscored.
- **`dummy_grid_rule_check`** (wrapper-level object, sibling of `grid`) — when applying the naming/prime-ordering/negative-`pos_m` rules above was non-trivial, record which rule fired and why in one short sentence per rule, e.g. `{"prime_ordering": "...", "negative_pos_m": "..."}`. Skip entirely when no rule above needed a judgment call.
- **`non_grid_dimensions_do_not_confuse`** (wrapper-level array of `{location, value_m, meaning}`) — when a dimension elsewhere in the set (another sheet, a costing-example site plan, a non-structural chain) coincidentally matches a grid value or could be mistaken for one, record it so a later reader doesn't re-derive the same false lead. `value_m` is `null` when the entry documents a non-numeric mix-up (e.g. a whole ramp/landing chain), not a single coincidental figure.

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

**A slab edge, overhang or eave line — superseded 2026-09-27.** This paragraph used to say such a line never gets a dummy (house #3's `E'` at the S0 bay-window box was left out that way). Under rule 4 above, **if a dimension is printed to it, it gets a dummy** like any other tick — whether it's structural no longer matters. Several houses (28, 39, 40: roof eaves, gable overhangs) already had these before the rule was written. What's still forbidden: making up a line that has **neither** a printed dimension **nor** a beam endpoint on it. There is nothing to take its `pos_m` from, so it can't be traced.

The beam-endpoint rule above is still how you find the dummies a dimension chain never prints (measured by proportion, §4 Span amendment). Rule 4 is how you find the ones it does print. Use both.

### Master file
Create/update `<house>_หน้า00_gridline.json` **before** extracting any other page — it holds every main grid + dummy grid + every level (`z_levels[]`) + every printed dimension in the set (`dimension_chains[]`, `unassigned_dimensions[]`, §4) for the whole house in one place. Other plan/section pages reference it via the `grid_source` field instead of re-writing the grid. Keep this as a separate companion file — never re-embed the full grid inline inside every view.

### How the grid master is built — one page per call, merged once (Makham, 2026-11-18)

- **One call reads one page.** Never two pages in one call. A house whose grid pass reads 25 pages makes 25 calls — the same pass, 25 times.
- **Which pages the pass reads:** every page that prints a grid or a level: the grid page itself, every plan with `also_gridline`, every elevation / section (the only place levels are printed, §4 rule 1). Nothing else.
- **Each call returns only what its page adds** — lines, levels, dimension rows, leftover numbers, all in the `grid{}` shape above. A page that adds nothing returns empty arrays; that is a normal answer, not a failure.
- **The merge happens once, in code, in one place** (the master file): every reply is combined into the house's single master, a point with the same `pos_m` to the mm is one line (§4 rule 4), and the origin and the prime numbering are redone by code in reading order (§ Dummy grid). The model never renumbers and never reconciles pages itself.
- **The level master (§4b) is written after the merge,** from the merged `z_levels[]` — it needs every page, so it is not part of any single page's answer.
- **Why one page at a time:** a model asked to hold a whole set at once drifts. The measured case: house 83b8e52c's master read `0 / 6 / 12` where the drawing prints `3 + 3`, and one wrong grid line pushed its BOQ 30.8% over (`tune_ai/t07_Palfrey/เอกสาร/pass_ทำอะไร.csv`). One page is one image at full resolution, and the merge step is plain code that can be checked.
- **Today's pipeline (t07):** each call is also shown the merged master so far as text (`GRID SO FAR`), so a later page can see what is already known; the training rows and the worker share one merge function (`tune_ai/t07_Palfrey/สร้างชุดข้อมูล/grid_incremental.py`). Whether a call should see the master so far or read blind is a pipeline choice, not a format rule; the format above holds either way.
- **Hand extraction (op01 / op03 / op04) works the same way:** read the pages one by one, add what each contributes to the one master file, and tidy (dedupe, prime order) in that one file at the end.

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

## 4a. `notes` pattern — the `notes{}` object (added 2026-08-21)

A `notes` file carries **two things, both required when the sheet prints them**:

1. **`sections[]`** — the verbatim transcript of the printed headings and lines (§0.1). Unchanged
   from before; this is the audit trail and it is never summarised or translated.
2. **`notes{}`** — the project-level specification values parsed out of that transcript, defined
   below.

**Why this section exists.** `notes{}` was being read by a downstream consumer (Constistant's
`raw-extraction-adapter.js` builds `extractedNotes` from `notes.fc_ksc` / `notes.fy_main_ksc` /
`notes.fy_stirrup_ksc` / `notes.cover_mm`) while this spec had never defined it. Audited
2026-08-21: `fc_ksc` appeared in **1 of 55** real notes files, and that one file put it at
top level under `concrete_strength`, not under `notes` — so the value never reached the consumer
for **any** house, and the project-wide concrete and steel specification has never entered the
pipeline. This section closes that.

The same audit found `notes` to be the worst-drifted pattern in the set: 55 files carrying the
same content under six container keys (`notes` 22, `notes_sections` 9, `sections` 8, `spec_notes`
3, `notes_text` 1, `raw_text` 1) plus a long tail of one-offs (`reference_standard`,
`concrete_strength`, `precast_plank_spec`, `general_requirements`, …). **The two names above are
the only two. Every one-off key is a defect.**

### Shape

```json
"notes": {
  "reference_standard": "มยผ. 1101-52 ถึง 1106-52",

  "concrete": {
    "grade_label": "ค.3",
    "fc_ksc": 210,
    "curing_days": 28,
    "printed_as": "คอนกรีต ค.3 กำลังอัด 210 กก./ตร.ซม. ที่ 28 วัน"
  },

  "steel": {
    "round_bar":    { "notation": "RB", "grade": "SR-24", "fy_ksc": 2400, "applies_to_dia_mm": [6, 9] },
    "deformed_bar": { "notation": "DB", "grade": "SD-40", "fy_ksc": 4000, "applies_to_dia_mm": ">=12" }
  },

  "cover": {
    "default_mm": 25,
    "by_condition": [
      { "condition": "หล่อติดดิน",                "cover_mm": 75 },
      { "condition": "สัมผัสดินหรือดินฟ้าอากาศ",  "cover_mm": 50 }
    ]
  },

  "fc_ksc": 210,
  "fy_main_ksc": 4000,
  "fy_stirrup_ksc": 2400,
  "cover_mm": 25
}
```

### The nested half is what the drawing says

- **`concrete`** — `fc_ksc` is an integer in ksc. A grade printed as a Thai label (`ค.3`) keeps
  the label in `grade_label`; the label is not a substitute for the number.
- **`steel` splits by bar notation, not by role.** Thai notes sheets specify steel as
  "RB = SR-24 = 2400 ksc, DB = SD-40 = 4000 ksc" — **by bar type**. They do not say "main bars are
  X and stirrups are Y". Record what is printed. `applies_to_dia_mm` is an array of diameters or a
  printed threshold string (`">=12"`), whichever the sheet gives.
- **`cover` is in millimetres** — it is a member dimension, so §0.5 applies. ❌ `rebar_cover_m` is
  wrong and appears in 4 existing files. `by_condition[]` exists because a notes sheet usually
  prints several covers (cast against earth, exposed to weather, interior); `default_mm` is the
  unqualified one. A sheet printing only one cover gets `default_mm` and an empty `by_condition`.

### The flat half is a derived alias, never a second reading

`fc_ksc`, `fy_main_ksc`, `fy_stirrup_ksc` and `cover_mm` at the top of `notes{}` are **one-way
copies** of values already recorded above them, kept flat so existing consumers need no change —
the same alias pattern `BeamLibraryEntry`'s flat `main_bar_*` fields already use.

Derivation, in order:

| flat field | copy of |
|---|---|
| `fc_ksc` | `concrete.fc_ksc` |
| `fy_main_ksc` | `steel.deformed_bar.fy_ksc` — main bars are deformed unless the sheet says otherwise |
| `fy_stirrup_ksc` | `steel.round_bar.fy_ksc` — stirrups are round bar unless the sheet says otherwise |
| `cover_mm` | `cover.default_mm` |

**If the sheet actually states a different pairing, follow the sheet and flag it in `warnings[]`.**
The two "unless" rules above are the Thai convention, not a law — a house detailing DB stirrups is
unusual but real, and the flat field must reflect what that house's drawing says, not the
convention.

A flat field whose source is absent is **`null`**, never a convention-based default. A missing
value is a real signal that this house's notes sheet did not specify it.

### Rules

- Every value in `notes{}` traces to a line in `sections[]`. **If it is not in the transcript, it
  does not go in the object** — never carry a value in from another sheet, another house, or a
  standard you know.
- The whole `notes{}` object is omitted when the sheet is not a specification sheet (a notes page
  that is purely procedural, e.g. site-safety requirements, has a `sections[]` transcript and no
  `notes{}`).
- Extraction of these values belongs to the `notes` sheet **only**. A section or schedule sheet
  reprinting `fc = 210` records it as that member's `concrete_grade` per §6, not here.

## 4b. `level_master` — which printed level is which floor (pattern #21, added 2026-11-18, Makham)

One file per house, `<house>_หน้า00_level.json`: the companion of the grid master (§4) in the same `หน้า00` slot. It maps the floor codes a view carries in `floor_level` (§0.0 Table 1) to the levels the drawings print, so a consumer can compute storey heights instead of assuming 3.00 m.

```json
{
  "png": "00", "doc_page": null, "discipline": "structural", "sheet_code": null, "sheet_name": "level master",
  "pattern": "level_master", "source_pages": ["image/‹บ้าน›/‹บ้าน›_หน้า09.png", "image/‹บ้าน›/‹บ้าน›_หน้า21.png"],
  "confidence_score": null, "confidence_flags": [], "warnings": [],
  "level": {
    "floors": [
      {"floor_level": "F1", "level_m": 0.60, "structure_level_m": null, "printed_as": "ระดับพื้นชั้น 1"},
      {"floor_level": "RF", "level_m": 3.75, "structure_level_m": null, "printed_as": "ระดับหลังคาน"}
    ]
  }
}
```

- **Wrapper:** the same fields, stamped the same way, as the grid master (§0.0); `source_pages` lists the pages the levels were read from. The content sits under `level{ floors[] }` (§0.1), never in `elements[]`, and there is no `grid_source`.
- **One entry per floor the drawings give a level for, bottom to top.** `floor_level` uses exactly the wrapper codes: `B1`, `F1`, `F<N>M`, `F2` …, `RF`.
- **`level_m`** = the finished floor level as printed, signed, same datum as the grid master's `z_levels[]`. **It must equal a `level_m` in that house's `z_levels[]`:** a level printed only beside a plan title (house 174: `(+12.50)` under the floor-3 plan) goes into `z_levels[]` first, because every printed level lands there (§4 rule 1). A floor with no printed level is left out, never estimated. House 174 prints one for every floor, including the basement parking slab (`(-1.00)` on the beam/slab plan) and the roof frame (`+25.65` on its members), so all nine are in its file.
- **`structure_level_m`** = the structural (top of slab) level when a sheet prints one separately for that floor, else `null`. Same rule: equal to a `z_levels[]` value.
- **`printed_as`** = the label printed with the level, verbatim (§0.7); `null` for a bare number such as `(+12.50)`.
- **`RF`** = the roof the structural sheets name (หลังคา / หลังคาน / ROOF). A roof frame standing on it is not a floor.
- **Not written:** storey height. Code derives it as the next entry's `level_m` minus this one's; the top entry has none.
- **Written after the grid master is complete** (all pages merged, §4 "How the grid master is built"), from the merged `z_levels[]` and the levels printed beside the plan titles. It needs every page, so it is one write per house, not one per page.
- **No printed floor level anywhere → no file.** An empty `floors: []` would claim the set was read and holds none, the same false claim §4 rule 4 forbids for an empty `dimension_chains[]`.
- **`check_format.py`** accepts the pattern and checks `floors[]` when the file exists: codes unique and bottom to top, every level equal to a `z_levels[]` value of the same house.
- **Consumers (2026-11-18):** Constistant stores a `level_master` file raw and warns that the pattern is not adapted; no BOQ line depends on it, so nothing is lost while it waits. Reading `floors[]` to replace `DEFAULT_FLOOR_HEIGHT_M` (3.00 m) is future code (branch `makham/floor-levels-from-z`).
- **Hand extraction (op01 / op03 / op04):** write it right after the grid master is complete.

## 5. Beam segment splitting

One beam = between two adjacent supports only. Split immediately when:
1. A column/grid intersection sits in between
2. The beam bears on another beam (not a column) — split there. No flag: `bears_on_beam` was retired 2026-11-18 (§0.0); nothing read it.
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
"main_bar": { "count": 4, "dia_mm": 12, "type": "RB", "printed_as": "4-Ø12มม." }
```
A column has no beam-style top face and bottom face — it has bars around its corners, printed as a single figure (`4-Ø12มม.`). Recording it as `top:4/bottom:4` silently doubles the real count to 8. This has been swept across the whole project and every `element_type: "column"` now uses a single `count`; do not reintroduce the split. Applies to structural columns, pedestals (ตอม่อ), short columns (`C0`/`CN`) and fence columns alike.

The `top`/`bottom` split rule above is for **beams** (and any member genuinely detailed with two longitudinal faces).

**`middle` — third main_bar face (added 2026-07-20 by Makham).** When a section drawing shows a **clearly distinct mid-depth bar row** — its own leader line, its own dot row sitting between the top and bottom clusters, typically on a deep beam — record it as a third `main_bar` face, **not** as `additional_bars`:
```json
"main_bar": {
  "top":    { "count": 2, "dia_mm": 16, "type": "RB" },
  "middle": { "count": 2, "dia_mm": 9,  "type": "RB" },
  "bottom": { "count": 4, "dia_mm": 16, "type": "RB", "printed_as": "2-Ø16มม. + 2-Ø16มม.(หยุดที่ L/8)" }
}
```
Real case: house #04's B4A/B4X (200x700 deep beams) print `2Ø9มม.` on a leader pointing to a distinct dot row at mid-depth, between the `2-Ø16มม.` top row and the `2-Ø16มม.` + `2-Ø16มม.(หยุดที่ L/8)` bottom rows. These are skin/waist bars — real longitudinal main reinforcement on their own face, so they belong in `main_bar.middle`.

`middle` is **optional** — emit it only when such a row genuinely exists; most beams have only `top`/`bottom`. Do not invent a `middle` by splitting a top or bottom cluster, and do not use it for a bar that is merely *drawn* between the two clusters but whose leader ties it to the top or bottom face (that case still merges into `top`/`bottom` per §7).

```json
"additional_bars": [
  { "count": 1, "dia_mm": 16, "position": "on top of beam, cut off at L/8 from column face", "printed_as": "..." }
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

## 6b. Footings and pile caps — same flat fields as everything else (added 2026-08-28)

A footing is the most common structural element in this corpus (**427 `footing` + 45 `pile_cap` across 50 houses**) and until now had no section of its own. Five houses independently invented five field vocabularies for it. This section closes that: **a footing carries exactly the same four load-bearing fields as a beam or a column** — no metre variants, no `cap_*` family, no mesh-specific rebar object.

```json
{
  "element_id": "F1",
  "element_type": "footing",
  "width_mm": 1000,
  "height_mm": 300,
  "main_bar": { "count": 12, "dia_mm": 9, "type": "RB", "count_printed_as": "6+6" },
  "stirrup": { "count": 1, "dia_mm": 9, "type": "RB", "printed_as": "1-Ø9มม. รัดรอบ" },
  "pile_count": 5,
  "concrete_grade": "fc210",
  "steel_grade": "SR24"
}
```

### The four load-bearing fields

| field | meaning on a footing |
|---|---|
| `width_mm` | plan dimension, integer mm. A **square** cap (the normal case) needs only this one. |
| `depth_mm` | the **other** plan dimension — emit it **only when the cap is genuinely not square**. |
| `height_mm` | the cap's / footing's own **structural thickness**, nothing else (see below). |
| `main_bar` | the mat, as **one flat object** with a single `count`. |

**`height_mm` is the concrete member only.** Lean concrete, sand bed, cover and pedestal height are *not* part of it and must never be summed into it — each keeps its own field (`lean_concrete`, `sand_bed_thickness_m`, `pedestal_height_m`). A cap drawn `0.20 cap / 0.05 cover / 0.10 lean / 0.05 sand` is `height_mm: 200`, full stop.

**The bottom mat is `main_bar` with a single `count`, like a column — never `top`/`bottom` keys inside it.** A two-way mat prints as `6+6` or `4+4`: `count` is the **sum** (12, 8) and the printed text goes in `count_printed_as`, exactly as §0.5 already requires. The two directions of a square cap are the same bar length, so one count carries the full steel weight with no loss. Never split a mat into `top`/`bottom` keys inside `main_bar` — that is the beam convention and it silently doubles the count (§6). **A top mat is its own field, `top_bar`** (field map below).

**`stirrup` on a footing is usually a fixed count, not a spacing.** An edge tie printed `1-Ø9มม. รัดรอบ` is one bar, not a repeating row:

```json
"stirrup": { "count": 1, "dia_mm": 9, "type": "RB", "printed_as": "1-Ø9มม. รัดรอบ" }
```

Emit `count` and **omit `spacing_mm` entirely** — do not invent a spacing to fill the field. A consumer that sees a spacing where none was printed computes `ceil(1/0.20)+1 = 6` bars from a number nobody drew; this exact substitution was found live and had been inflating footing tie steel sixfold. A footing that genuinely *does* print a repeating spacing (`Ø9@0.20`) uses `spacing_mm` as normal and omits `count` — the two are mutually exclusive.

### Forbidden spellings — write the right-hand column

| ❌ never | ✅ write instead |
|---|---|
| `cap_width_m: 1.0` | `width_mm: 1000` |
| `cap_length_m: 1.2` | `depth_mm: 1200` (omit when square) |
| `cap_thickness_m: 0.3` | `height_mm: 300` |
| `cap_thickness_m: {cap, cover, lean_concrete, sand_fill}` | `height_mm` = the `cap` value only; the rest keep their own fields |
| `cap_plan_dims_m: {width_total, depth_total, sub_dims[]}` | `width_mm` / `depth_mm` from the totals; the sub-dimension chain goes in `width_mm_printed_as` / `depth_mm_printed_as` (§0.7) — see the note below |
| `main_bar_mesh: {total_bars, dia_mm, type}` | `main_bar: {count, dia_mm, type}` |
| `stirrup_tie_count: 1` (element top level) | `stirrup: { count: 1, ... }` |
| `element_type: "pile_cap_detail"` / `"spread_footing_detail"` | `"pile_cap"` or `"footing"` (§0.4) |

**Where a cap's sub-dimension chain goes — corrected 2026-08-28 after reading the real data.** This rule first said the chain belonged in the grid master's `dimension_chains[]`; **that was wrong.** A real chain reads `{width_total: 0.85, sub_dims: [0.20, 0.225, 0.225, 0.20]}` — edge distance and pile spacing *inside one footing*, on no grid axis at all. `dimension_chains[]` records the building's printed grid dimensions (§4); putting per-element detail dimensions there would pollute the one file every span in the house is computed from. Keep the chain on the element, in the `*_printed_as` sibling §0.7 already provides:

```json
"width_mm": 850,
"width_mm_printed_as": "0.20+0.225+0.225+0.20 = 0.85",
```

**`pedestal_tie` is allowed — it was wrongly listed as forbidden above until 2026-08-28.** Real data reads `{count: 1, dia_mm: 9, type: "RB", note: "1Ø9มม. รัดรอบ — wraps around pedestal"}`: a tie on the **pedestal (ตอม่อ)**, a different member from the footing it sits on. Neither correction offered before was right — splitting out an `element_type: "pedestal"` element means inventing that pedestal's width and height (the sheet gives only `pedestal_height_m`), and folding it into `stirrup` would file a pedestal bar as the footing's own edge tie, which a consumer reads as `stirrup.count`. So it stays its own named field. Do not merge it, do not delete it, and do not rename it.

**Why not just bless `cap_*`:** it violates §0.5 (no metre variant of a member dimension) — so the schema would contradict itself — and it is the minority form by a wide margin: `width_mm` appears on **253** footing elements, `cap_width_m` on **2**. The `cap_thickness_m` name is worse than unused, it is actively ambiguous: **15 elements across houses 01/02/03/05/07 write it as a plain number and 4 elements in house 04 write it as an object** with four sub-thicknesses. A downstream consumer converting metres to millimetres gets `NaN` on the object form and cannot tell that it failed. One field, two incompatible types, silent corruption — that is the whole case against it.

### Context fields — keep, don't re-spell

These describe what the footing sits on rather than the footing itself, are already consistent across houses, and stay exactly as they are: `pile_count`, `pile{}`, `dowel_bar{}` (§6b below), `cover_mm`, `cover_printed_as`, `lean_concrete{}`, `sand_bed_thickness_m`, `pedestal_height_m`, `pedestal_tie{}`, `ground_reference`, `base_fill`, `plan_layout`, `column_stub_mm`, `footing_type`. Add nothing new here without a `warnings[]` note (§0.4).

**A pedestal (ตอม่อ) detailed as its own member is its own element** — its own mark, its own section, `element_type: "pedestal"`, single `count` main bar per §6. But when the footing's detail sheet only prints the pedestal's height and its tie (the common case), those stay on the footing as `pedestal_height_m` / `pedestal_tie{}`: promoting them to a separate element would mean inventing a width and height nobody drew.

### What a footing detail sheet prints — field map (added 2026-11-18, Makham)

Checked three ways: Makham's reference picture (components of a reinforced concrete footing), ACI 318 summaries found online ([STRUCTURE magazine, Part 5: Foundations](https://structuremag.org/?p=15006); [ACI 318 spread-footing reinforcement](https://www.ideastatica.com/es/support-center/aci-spread-footing-reinforcement)), and the 820 `footing` / `pile_cap` / `pile` elements already in the `section` files. The online sources are summaries, not code text; the Thai standards (มยผ.) could not be found online for dowels or lean concrete, so nothing below is cited to them.

| the drawing shows | field |
|---|---|
| footing width B, length L | `width_mm`, `depth_mm` (omit when square) |
| thickness H | `height_mm` |
| bottom mesh = the main (tension) steel, bar size, spacing, **both directions** ("transverse" bars are the second direction) | `main_bar` — `count` (sum of both directions), `dia_mm`, `type`, `count_printed_as`; a printed spacing `@0.15` is `spacing_mm` with no `count`, as for a stirrup |
| **top bars** (the upper mat, distribution bars) | **`top_bar`** — same shape as `main_bar` (`count` = sum of both directions, `dia_mm`, `type`, `count_printed_as`, `printed_as`, or `spacing_mm`) |
| side / edge tie bars wrapping the footing (`รัดรอบ`) | `stirrup` (§6b above: a fixed `count`, no `spacing_mm`) |
| starter bars from the column | `dowel_bar` (below) — the column's own ties and main bars belong to the column's section, not here |
| dowel bars (เหล็กเดือย) tying the column to the footing | `dowel_bar: { count, dia_mm, type, length_mm, printed_as }` — `length_mm` = the bar's total length as printed; hook, embedment depth and projection stay in `printed_as` (the sheet prints them as words, e.g. `1ø12 ยาว 1.00 ม / กรอกคอนกรีตลึก 0.50 ม`) |
| minimum concrete cover | `cover_mm` + `cover_printed_as` — **only when the sheet prints it**; never fill in the standard's value (the standard is `standards-config`'s job, not the drawing's) |
| lean concrete, sand bed | `lean_concrete{}`, `sand_bed_thickness_m` (context fields, unchanged) |
| column stub, pedestal | `column_stub_mm`, `pedestal_*` (context fields, unchanged) |
| piles under a cap | `pile_count`, `pile{}` (context fields, unchanged) |
| concrete / steel grade | `concrete_grade`, `steel_grade` |

**Not extracted:** load paths, soil bearing pressure, "governed by punching shear", compression arrows, corrosion-protection icons. The picture explains design; a Thai structural sheet does not print them. A soil value printed in a note belongs to `notes`.

**A non-square footing prints a different bar count per direction** (real example: `10-DB12, 7-DB12` on a 1.20 × 0.75 m footing; ACI 318 §13.3.3.3 likewise treats the long and short directions differently). `main_bar.count` stays the sum (17), and **the split is kept in `count_printed_as` in printed order (`"10 + 7"`)** — that text is the only place the two directions survive, so never drop it. A consumer must not assume both directions are the same length when it prices a non-square mat (Constistant does today; known approximation).

**A footing can print a top mat as well as a bottom mat** (Makham's strip-footing reference picture shows both; real files: 40 of 789 footing / pile-cap elements already print one, e.g. บ้าน_ใหญ่_2ชั้น_01 page 40 F3 and บ้าน_เล็ก_2ชั้น_03 pages 43-45). The bottom mat is `main_bar`, the top mat is **`top_bar`**:

```json
"main_bar": { "count": 8, "dia_mm": 12, "type": "DB", "count_printed_as": "4+4" },
"top_bar":  { "count": 8, "dia_mm": 12, "type": "DB", "count_printed_as": "4+4" }
```

- Write `top_bar` **only when the sheet prints a top mat.** Most spread footings print one mat; then there is no `top_bar` at all, and a top mat is never copied from the bottom one or assumed from a standard.
- A combined callout is split between the two fields, keeping the printed words on both: `3-Ø9 บน + 3-Ø9 ล่าง` is `top_bar: {count: 3, ...}` + `main_bar: {count: 3, ...}`.
- **Consumer gap:** Constistant's footing steel reads `main_bar` only, so a `top_bar` is **not priced until it reads the field** (legacy files that folded the top bars into one summed `count` were priced). Same gate logic as `column_plan`: the reader first, then files that rely on it.

**Stray spellings found in the same 820 elements — write the right-hand column** (counts are footing/pile-cap elements, 2026-11-18):

| ❌ never | ✅ write instead |
|---|---|
| `bars_by_direction: { "along_0.75": "10-DB12", ... }` (25) | `main_bar` + `count_printed_as: "10 + 7"` |
| `bar_layers: [ ... ]` (21) | `main_bar` (bottom mat), `top_bar` (top mat) |
| `main_bar: { top: {...}, bottom: {...} }` on a footing (13) | `top_bar` and `main_bar` |
| the words `บน` / `ล่าง` inside one `main_bar` or `rebar` callout (21) | split into `top_bar` and `main_bar`, printed words kept on both |
| `rebar: { count, dia_mm, ... }` (15) | `main_bar` |
| `thickness_mm: 300` at the top level (120; 70 of them also carry `height_mm`) | `height_mm: 300` for the footing's own thickness; lean concrete and sand keep their own fields |
| `dowel_bar.length_m: 1.0` (7) | `dowel_bar.length_mm: 1000` |
| `pile_length_m` (22) | `pile.length_m` |

Legacy files keep these spellings; the dataset builder maps them, no file is rewritten.

### Legacy files

The five houses carrying `cap_*` were extracted before this section existed and are **not being rewritten as part of this edit** — see the entry in `primary_rawjson_schema_edit_log.md`. Every new extraction (t04 included) emits the flat form only.

## 7. Spec join (plan + section/schedule)

A `plan` element (has `grid_ref`) + a `section` **or** `schedule` element (has width/height/main_bar/stirrup) for the same mark join together via `element_id` — **`section` and `schedule` are equally valid spec sources**, not limited to `section` only.

Fields joined in:
```
width_mm, height_mm, depth_mm, main_bar{}, stirrup{}, additional_bars[],
steel_section{}, material, spacing_mm, pile_count,
concrete_grade, steel_grade, spec_source
```
(`spec_confidence_score` dropped 2026-11-18 with element confidence, §0.0; Constistant already reads it as `null` when absent.)
(`steel_section{}`/`material` per §6a — a steel member joins exactly the same way, it just carries a section designation instead of rebar. `depth_mm`/`pile_count` per §6b — a footing joins the same way too, which is the point of it using the same field names.)

**Conflict rule:** if the same `element_id` has mismatched specs in both `section` and `schedule` → **`section` always wins**. Both files keep what they print; the conflict is detected and flagged by code at join time (Constistant's adapter writes `spec_conflict_section_vs_schedule` on its own entity). Since 2026-11-18 the raw files carry no flag (§0.0). *(Not yet tested against real data.)*

**Don't inline the joined spec into every atomic segment.** Once a mark's spec is confirmed identical across all its occurrences (verify this first — don't assume), store it **once** in a top-level `specs` object keyed by `element_id`, e.g. `specs.B4 = {width_mm, height_mm, main_bar, stirrup, additional_bars, concrete_grade, steel_grade, spec_source}`. Each entry in `elements[]` then only carries position (the `span` array, §0.0 — stored as `grid_ref_start`/`grid_ref_end`, `span_length_m`, `span_source`) — never repeat the full spec block on every segment (บทเรียนจาก 2026-07-14: บ้าน 1 หน้า19 beam plan เคยพิมพ์ spec ซ้ำทุกช่วงของคานมาร์คเดียวกัน กลายเป็น god-object-in-a-row-per-mark ทั้งที่ spec เหมือนกันทุกตัวอักษร). (Until 2026-11-18 spec-level observations went into `spec_confidence_flags` and per-occurrence ones into `confidence_flags`; both are retired, §0.0 — an asymmetric top/bottom count is already visible in the `main_bar` numbers themselves.)

**Verify `additional_bars[].position` against the actual leader line in the section drawing — never trust the printed label text alone, and never assume top vs. bottom from how a similar-looking mark resolved.** Two real cases from the same house, same-looking label pattern, opposite answers:
- **B2/B4/B5/B3**: label read "บนคาน" (top) but the leader line actually pointed to a bottom-corner bar (curtailed at L/8, alongside the other bottom main bars) → merged into `main_bar.bottom.count` (e.g. `count: 2` + 1 curtailed bar → `count: 3`).
- **B3X**: a bar labeled "ล้วงเข้า B3 1.5 ม." (lap-splices into the adjacent beam B3) — sounds like it should be a separate cross-beam detail, but per B3X's own section the label order top-to-bottom was *top-continuing / lap-splice bar / stirrup / bottom-continuing*, meaning the lap-splice bar is actually B3X's own **top** reinforcement (anchored by extending into B3), not a bottom bar and not something to leave out — merged into `main_bar.top.count` (`count: 2` → `4`) instead.

So: **"lap-splices into an adjacent beam" is not on its own a reason to keep a bar in `additional_bars`** — it can still belong to that mark's own `main_bar.top` or `.bottom`, exactly like a same-beam curtailed bar. Check the printed label *order* (top-to-bottom in the section) or the leader line position for **every mark independently** — don't reuse the previous mark's answer. Always keep the printed callouts verbatim in that side's `printed_as` (e.g. "2 เส้นต่อเนื่องจาก B3 + 2 เส้นล้วงเข้า B3 1.5 ม.") so the splice/curtailment detail isn't lost after merging. Only keep a bar in `additional_bars` when it genuinely isn't part of any main_bar face at all — and note that a **mid-depth longitudinal row now has its own face, `main_bar.middle` (§6)**, so "it's not top and not bottom" is no longer a reason to leave it in `additional_bars`.

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
  "level_step_mm": null
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
- **Footing flat-field rule (§6b) — written 2026-08-28 against the existing corpus, not yet exercised by a fresh extraction.** The rule matches what 253 footing elements already do, but no house has been extracted *under* it yet; t04's first real run is the test. Five houses (01/02/03/05/07 with `cap_*` as numbers, 04 with `cap_thickness_m` as an object) still carry the legacy form and have not been migrated
- **Non-square footings.** §6b defines `depth_mm` for a rectangular cap, but the Constistant pipeline currently squares `width_mm` for both plan sides and only flags the mismatch (`footing_cap_not_square_width_used_for_both_sides`). Emit `depth_mm` anyway — the data should be right before the consumer is

## 13. `site_plan` — `element_type` not standardized across houses

Checked all 5 houses' `site_plan` pattern files (2026-07-13). `element_type` values found: `boundary_line`, `building_footprint`, `building_outline`, `grading_note`, `grading_note_or_slab`, `lot_boundary`, `other`, `road`, `room`, `setback` — 10 distinct strings, but several pairs describe the same real-world thing under different names per house:

- `building_footprint` / `building_outline` — both mean the building's outline within the lot
- `boundary_line` / `lot_boundary` — both mean the property boundary line
- `grading_note` / `grading_note_or_slab` — both mean the ground-fill/grading annotation

No fixed enum has ever been given for `site_plan`'s `element_type` — each house's extraction picked its own naming independently. Not merged/standardized yet; flagged here so a future pass can decide on one canonical name per concept before this pattern is used for any downstream automation.
