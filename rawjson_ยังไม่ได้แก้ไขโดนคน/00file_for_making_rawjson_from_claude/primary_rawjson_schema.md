# Primary Raw JSON Schema

> Compiled 2026-07-10 from [`20260708draft of prime rawjson.md`](../../wait_for_ทิ้ง/No_touch_box/docs/20260708draft%20of%20prime%20rawjson.md) (original kept untouched, moved into `wait_for_ทิ้ง/` 2026-08-04 as historical — see `No_touch_box/docs/ARCHIVE.md`) — this is the spec actually used when prompting the model to extract raw JSON for other houses. History/rationale stripped out; only actionable rules remain.

## 0. FORMAT LOCK — read this before anything else (added 2026-08-02)

**Two files with the same `pattern` must have the same shape. House #1000 must come out looking exactly like house #1.** Everything below is mandatory, not a preference. It exists because houses 01-11 drifted apart badly and had to be repaired in bulk — the repair is described in `json_แก้ไขแล้ว/สิ่งที่ต้องแก้.md` items 59-62, and these rules are what stops it happening again.

### 0.1 The container — never invent an array name

Every file puts its content in **`elements[]`**. Three documented exceptions, and no others:

| pattern | container |
|---|---|
| `grid_master` | `grid{ x_lines[], y_lines[], z_levels[], dimension_chains[], unassigned_dimensions[] }` — **nested under `grid`**, never `x_lines` at the top level (the last three added 2026-08-21, see §4) |
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

### 0.2 Every element carries these four

```json
{ "element_id": "...", "element_type": "...", "confidence_score": 0.9, "confidence_flags": [] }
```
`confidence_score` is `null` when the sheet genuinely gave you nothing to judge by. **Never invent a number to fill the field** — a made-up confidence is worse than an honest `null`.

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

`beam` · `column` · `footing` · `pile` · `pile_cap` · `pedestal` · `slab` · `tie_beam` · `rafter` · `stair` · `room` · `room_cut` · `door` · `window` · `wall` · `dimension` · `dimension_chain` · `dimension_note` · `level` · `datum` · `note` · `symbol` · `symbol_legend_entry` · `sheet_index_entry` · `detail_view` · `section_view` · `plan_view` · `precast_plank_detail` · `sanitary_fixture` · `vent_pipe` · `fitting` · `accessory` · `furniture` · `gate_component` · `railing_component` · `electrical_outlet` · `ceiling_downlight_point` · `ceiling_fan` · `design_criterion` · `steel_member` · `connection_detail` · `installation_detail`

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
- Every point ref must resolve against that house's `หน้า00_gridline.json`. If it doesn't, the grid master is missing a line (§4 beam-endpoint rule) — fix the master, don't invent a ref.

### 0.9 `pattern` must be one of the 19 in §1

Never coin a new one. House 07 invented `detail`, `diagram` and `elevation` and needed 21 files remapped. A detail sheet is `section`; an elevation is `side_profile`; a schematic diagram is `side_profile`; a site plan is `site_plan`, not `plan`.

**The plan family is four values, not one** (`beam_plan` · `footing_plan` · `roof_frame_plan` · `etc_plan`, split 2026-08-28 — see §1). Check the first three in order; `etc_plan` is the residual for a plan sheet that is none of them (column plan, slab plan, architectural/MEP layout). **`plan` is a dead spelling** — it was renamed to `etc_plan` in the same pass, files included. Do not add a fifth by analogy.

**A summary table is `schedule`; a bar-bending (cut-list) table is `bbs_schedule`** — the test is whether a row describes a *member* or a single *bar* (§1 #17). A soil borehole log is `soil_boring_log`, never `schedule` or `notes` (§1 #18).

### 0.10 Before you call a house finished

**Run `python tools/check_format.py <house-folder>` — it checks every item below and exits non-zero on failure.** Do not hand-audit; a 1000-house set cannot be eyeballed.

- [ ] every file parses as JSON
- [ ] every file has the §2 wrapper fields
- [ ] `pattern` is one of the 19 (§1) — and the three gated plan-family values are not emitted until §1's consumer gate is lifted
- [ ] no file carries `phase_note` (§2a)
- [ ] no array named after a kind of drawing element (§0.1)
- [ ] grid master nests `x_lines`/`y_lines` under `grid{}` (§0.1)
- [ ] every sheet that prints a level contributed to `z_levels[]`, and every sheet that prints a dimension row contributed to `dimension_chains[]` (§4) — a sheet with printed numbers and no contribution is an unread sheet, not a clean one
- [ ] every printed number that landed in neither is in `unassigned_dimensions[]` (§4)
- [ ] a `notes` file uses only `sections[]` + `notes{}` — no `notes_sections`/`spec_notes`/`raw_text`/per-topic one-off key (§4a)
- [ ] `notes{}`'s four flat fields match the nested values they alias, and `cover` is in **mm** not metres (§4a, §0.5)
- [ ] no rebar left as a string (§0.6)
- [ ] no packed size string (§0.5)
- [ ] `grid_ref` notation: no dashed point, no `grid`/`dummy` word (§0.8)
- [ ] every point `grid_ref` resolves against `หน้า00_gridline.json` (§0.8)
- [ ] no `element_id` collides with a different member on the same sheet (§0.3)
- [ ] point elements merged to one entry per mark (§4), span elements left atomic (§4)

**The one allowed exception to the merge check:** two entries of the same point mark may stay separate when they carry genuinely different `confidence_score` or a different per-position `note` — merging would erase which positions were read off the drawing and which were inferred. The checker reports these; keep them, and say why in `warnings[]`. Anything else that trips the checker is a real defect.

## 1. Pattern taxonomy — 19 types

**The plan family sits first (#1-4) because it is where the money is** — every beam, footing and roof member that reaches a BOQ or a BBS arrives through one of these four. Everything from #5 down is either a spec source, a reference page, or not a drawing of the building at all.

| # | pattern | description |
|---|---|---|
| 1 | `beam_plan` | **structural beam plan** (แปลนคาน) — beams with marks, `grid_ref_start`/`grid_ref_end`, spans. Added 2026-08-28 *(draft — see the consumer gate below)* |
| 2 | `footing_plan` | **structural footing plan** (แปลนฐานราก) — footings/pile caps as point elements with `grid_refs[]` + `count`. A sheet drawing both a spread-footing and a pile-footing system is two views (§3), one file each. Added 2026-08-28 *(draft)* |
| 3 | `roof_frame_plan` | **structural roof-framing plan** (แปลนโครงหลังคา) — roof beams/purlins/trusses with marks and grid refs. **Not `roof_plan`** (#15), which is the architectural roof plan and carries no structural marks. Added 2026-08-28 *(draft)* |
| 4 | `etc_plan` | **any other top-down plan with `grid_ref` — the "none of the above three" bucket.** This is the value formerly spelled `plan`: **renamed 2026-08-28, same value, and every existing `plan` file was renamed with it.** `plan` is now a dead spelling — see the legacy note below |
| 5 | `section` | detail section — rebar spec/dimensions for beam, column, footing |
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
| 19 | `unknown` | doesn't fit any of the other 18 |

**`plan` is a dead spelling — it was renamed to `etc_plan` on 2026-08-28, files included (Makham's ruling).** All 899 existing plan files across both trees were rewritten in that pass, so `pattern: "plan"` should no longer appear anywhere in this repo. A consumer may keep accepting the old string defensively, but nothing produces it.

**What a legacy `etc_plan` does and does not tell you.** For a **newly extracted** file, `etc_plan` is a positive statement: the extractor checked #1, #2, #3 and none matched. For one of the **899 renamed** files it is only "an unclassified plan" — the old `plan` value carried no kind information at all, so the rename neither added nor destroyed any, but it also did not verify anything. Most of those files are in fact beam plans or footing plans.

Consequences, both directions:

- **Do not read `etc_plan` as "definitely not a beam plan"** while renamed files are still in the set. A pass that skips `etc_plan` while hunting for beams would skip real beam plans.
- **Re-labelling a renamed file to #1/#2/#3 is real work, not a regex** — read the sheet, apply the test table, pick one, one file at a time. That is a separate future pass; it is not what the rename did.
- There is no per-file marker separating the two cases. The boundary is this entry plus the `primary_rawjson_schema_edit_log.md` row and the git commit for that pass — deliberately, rather than stamping a mechanical note into 899 files' `warnings[]`, which is a channel for genuine reading ambiguity (§2a), not for bookkeeping.

### The plan family — `beam_plan` · `footing_plan` · `roof_frame_plan` · `etc_plan` (split 2026-08-28)

`plan` was one pattern doing four jobs, so a consumer could not tell a beam sheet from a footing sheet without reading `sheet_name` free text. #1-3 name the three that carry structural quantities; **#4 `etc_plan` is everything else, and is defined by exclusion, not by content.**

The test is what the sheet carries, exactly as in the `roof_plan` rule below:

| The sheet shows | pattern |
|---|---|
| Beams with marks + two grid endpoints each (แปลนคาน, แปลนคาน-พื้น) | `beam_plan` |
| Footings/pile caps as points with `grid_refs[]` (แปลนฐานราก) | `footing_plan` |
| Roof beams / purlins / trusses with marks (แปลนโครงหลังคา) | `roof_frame_plan` |
| A top-down plan with `grid_ref` that is **none of the three above** | `etc_plan` |
| Ridge/hip/eave/roofing material, no structural marks | `roof_plan` (#15) |
| Site/lot layout, not the building itself | `site_plan` (#10) |

**`etc_plan` in full — what it does and does not mean.** It means exactly one thing: *a plan sheet that is not a beam plan, not a footing plan, and not a roof-framing plan.* It is a residual bucket, so it is defined by what it excludes, and the exclusion test is the only test. Known members today:

- **Column plan** (แปลนเสา) — columns as point elements with `grid_refs[]`. `etc_plan`, **not** `column_plan`.
- **Slab / floor plan** (แปลนพื้น) — slab markers `SO`/`SI`/`SX`/`ST` (§10). `etc_plan`, **not** `slab_plan`.
- **Architectural floor plan / layout** — rooms, doors, windows, walls with grid refs.
- **Sanitary / electrical / mechanical layouts** drawn top-down over the same grid.
- **A mixed structural plan** whose views genuinely cannot be separated (rare — try §3 first: a sheet with a footing view *and* a beam view is two files, `footing_plan` + `beam_plan`, not one `etc_plan`).

Rules that follow from it being a residual:

- **Never invent a fifth specific value.** A column plan is `etc_plan`, not `column_plan`; a slab plan is `etc_plan`, not `slab_plan`; an electrical layout is `etc_plan`, not `electrical_plan`. If one of those earns its own pattern later it gets added to the table above, never coined inside a house file (§0.9).
- **`etc_plan` is a last resort, not a default.** Check #1, #2, #3 in that order first. Reaching for `etc_plan` because the sheet is crowded or hard to read is how a beam plan's beams stop reaching the BOQ — the same failure the `roof_plan` warning below records. When genuinely unsure, pick the specific one that matches the marks you can read and say so in `warnings[]`.
- **It is not a dumping ground for non-plans.** No `grid_ref` and not top-down → it is `side_profile`, `section`, `schedule`, `notes`, `misc` or `unknown`, never `etc_plan`.

**Four traps, all found the hard way on 2026-08-28 while re-labelling the 183 legacy `etc_plan` structural sheets in `json_แก้ไขแล้ว/`.** Each one silently produces a plausible-looking wrong answer, so they are recorded here rather than left to be rediscovered:

- **`แป` is a substring of `แปลน`.** `แป` alone means *purlin* (a roof member), but `แปลน` means *plan* and starts the title of essentially every plan sheet in the corpus — so matching a bare `แป` as a roof signal calls **every Thai plan sheet a roof-framing sheet**. Match the compound words only: `แปเหล็ก`, `แปหลังคา`, `โครงหลังคา`, `โครงสร้างหลังคา`, `จันทัน`, `อกไก่`.
- **`sheet_name` on a multi-view page names every view on it, not this one.** A page whose `sheet_name` is `"แปลนอะเส, แปลนโครงหลังคา"` produces two files (§3), and reading `sheet_name` on the first one labels the tie-beam view a roof-framing sheet. **`view_title` is the field that describes this view**; fall back to `sheet_name` only when there is no `view_title`.
- **A คานอะเส / ring-beam plan is a `beam_plan`, even when it is filed as `*_beam_roof` or `*_roof_beam`.** The อะเส sits at the top of the wall and carries the roof, so its sheet is often named for the roof — but the roof *frame* (จันทัน / แป / โครงหลังคา) is always a separate sheet, and that separate one is the `roof_frame_plan`. If a house has both, the อะเส sheet is the beam plan.
- **A `roof_frame_plan` can contain no beam-shaped element at all.** A steel roof frame is often typed `steel_member` throughout (or `truss`/`purlin`/`rafter`), so a classifier keyed only on `element_type` finds nothing and falls through to `etc_plan`. When the title says `โครงหลังคา`/`โครงสร้างหลังคา`, that is sufficient on its own.

Applies to all four equally:

- **A sheet carrying two of these is a multi-view page (§3)** — split it, one file per view, each with its own pattern. A single sheet showing footing plan + beam plan produces `_view1_footing_plan.json` (`footing_plan`) and `_view2_beam_plan.json` (`beam_plan`).
- **Element shapes do not change at all.** A `beam_plan` element is the same atomic-segment shape as before (§4), a `footing_plan` element is the same merged point shape (§4). Only the wrapper's `pattern` value is new — nothing inside `elements[]` moves.
- `floor_level`, `grid_source` and every other wrapper field apply unchanged to all four.

**✅ CONSUMER GATE — LIFTED 2026-08-28.** All four values are safe to emit. The gate existed because Constistant's `buildElements()` filtered on the literal string `'plan'` and `ADAPTED_PATTERNS` listed six values, so a file labelled `beam_plan` would have been stored raw with a warning and **every beam on it would have silently disappeared from BOQ and BBS** — the identical failure that cost 8 houses their roof beams (see the `roof_plan` warning immediately below). Closed in the same pass as the rename, in this order (consumer first, files last — the reverse order would have zeroed every house's BOQ in between):

1. `Constistant/js/drawing/raw-extraction-adapter.js` — `PLAN_PATTERNS` accepts all four plus the dead `plan`, used by both `buildElements()` and `ADAPTED_PATTERNS`
2. `tools/check_format.py` — `PATTERNS` set widened; the roof-framing check now accepts `roof_frame_plan`
3. the 899 legacy files renamed `plan` → `etc_plan`

Still open, and the reason a fresh extraction should keep producing `etc_plan` rather than guessing: **the t04 Pass 0 / Pass 2 prompts have not been taught the three specific values yet.** Until they are, a model run classifies every plan as `etc_plan` — correct under the residual rule, just not yet using the split.

### ⚠️ `roof_plan` vs `plan` — a real, live data-loss bug (found 2026-08-21)

**A roof-framing plan carries real structural beams and must be `pattern: "plan"`.** Audited across all 11 houses: all 12 roof-framing files are `discipline: "structural"`, but **4 were written as `pattern: "plan"` and 8 as `pattern: "roof_plan"`**. Downstream, Constistant's `buildElements()` reads **only** `pattern === 'plan'` — so **the roof beams in those 8 houses have never reached a BOQ at all**, silently.

The test is what the sheet carries, not what it is called:

| The sheet shows | pattern |
|---|---|
| Beams/purlins with element marks, grid refs, spans (แปลนโครงหลังคา, roof frame plan, roof beam plan) | `roof_frame_plan` (#3) |
| Ridge/hip lines, eave overhang, roofing material, slope arrows — no structural marks | `roof_plan` (#15) |

A sheet showing both is a multi-view page (§3): split it, one file each.

**The 2026-08-28 split does not change this rule, it names it.** A structural roof-framing sheet was `plan` and is now `roof_frame_plan` — what must never happen, before or after the split, is calling it `roof_plan`. Nor is it `etc_plan`: a roof-framing sheet has its own specific value now, so the residual bucket is the wrong answer for a freshly read one. (A renamed legacy file may well be sitting in `etc_plan` — see the legacy note above; fixing those is the separate re-labelling pass.) The 59 existing `roof_plan` files are **not** all wrong: audit each against the two rows above before touching anything.

**Automation scope:** `run_pipeline.py` auto-extracts the plan family plus `section` / `schedule` / `notes` / `grid_master` / `material_list`. The other 10 patterns (`index`, `site_plan`, `side_profile`, `title`, `symbol`, `roof_plan`, `misc`, `bbs_schedule`, `soil_boring_log`, `unknown`) are manual-extraction only for now — which is exactly what this workflow (Claude reading pages directly) is for.

## 2. Required fields on every file (wrapper level)

```
png, doc_page, discipline, sheet_code, sheet_name, pattern,
source_image, confidence_score, confidence_flags, warnings
```

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

#### 2. `dimension_chains[]` — every printed dimension row, on any axis

```json
"dimension_chains": [
  {
    "axis": "x",
    "source_image": "..._หน้า15.png",
    "segments": [
      {"from": "edge", "to": "1", "value_m": 1.30},
      {"from": "1", "to": "2", "value_m": 4.00},
      {"from": "2", "to": "3", "value_m": 3.00},
      {"from": "3", "to": "edge", "value_m": 0.60},
      {"from": "edge", "to": "edge", "value_m": 0.70}
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

- `axis` is `x`, `y`, or `z`.
- `from`/`to` reference a grid `id` (or a `z_levels[]` `id` on the z axis) when that end sits on one, or the literal `"edge"` when it's a building/slab edge with no grid — **never invent a grid id just to have something to put here.**
- Record **every** row actually printed, including the cumulative/total row (the `3.75` above, the `7.00` on the x chain). Redundant arithmetically, but printed — and a mismatch between the detail row and the total row is exactly the extraction error this array exists to catch.
- One entry per printed row per sheet; the same chain reprinted on three sheets gets three entries with three different `source_image` values. Do not deduplicate across sheets.

#### 3. `unassigned_dimensions[]` — the catch-all, so nothing is ever dropped

Every printed number that did **not** land in a chain or a level goes here, with whatever text was printed next to it:

```json
"unassigned_dimensions": [
  {"value_m": 0.10, "label": "บัวปูนปั้น กว้าง 0.10 ม", "source_image": "..._หน้า15.png", "note": "moulding width, not a grid or level"},
  {"value_m": 0.10, "label": "บัวปูนปั้น ลึก 0.10 ม",  "source_image": "..._หน้า15.png", "note": null}
]
```

- `label` is the printed text verbatim (Thai stays Thai). `note` is optional and only for a genuine observation — leave `null` rather than inventing an interpretation.
- **This array is the reason the rule holds.** If a number doesn't fit anywhere else, it goes here — it never gets skipped. A page with numbers and an empty `unassigned_dimensions[]` means every number found a home, not that the page wasn't read.
- These are *not* grid data and nothing downstream uses them for span calculation; they exist so a later reader can see the full picture without re-reading the sheet.

#### Relationship to the resolved axes

`x_lines`/`y_lines`/`z_levels` stay the **resolved, deduplicated** registry — that's what the pipeline consumes. The three arrays above are the **raw transcript** proving where each resolved value came from, and holding everything that has no resolved home. Both live in the same master file; neither replaces the other.

All three arrays are optional in the sense that a sheet printing no dimensions contributes nothing — but a sheet that *does* print dimensions and contributes an empty array is an extraction failure, not a clean file.

### Documenting genuine ambiguity in the grid master (optional, added 2026-08-09)

These three fields exist for the case where a grid master genuinely can't be read with full confidence — do **not** add them to a clean file just for consistency; a house whose chains close and whose dummies are unambiguous (e.g. house #04) needs none of them.

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

**Conversely — do NOT invent a dummy for a slab-only edge.** A dashed slab/room boundary, a roof-overhang line, or an eave edge with **no beam label and no columns at its corners** is not a structural line and gets no dummy grid (house #3's `E'` at the S0 bay-window box is exactly this case — slab edge only, no beam, so nothing was added). The trigger is a **beam endpoint**, not any line on the drawing.

### Master file
Create/update `<house>_หน้า00_gridline.json` **before** extracting any other page — it holds every main grid + dummy grid + every level (`z_levels[]`) + every printed dimension in the set (`dimension_chains[]`, `unassigned_dimensions[]`, §4) for the whole house in one place. Other plan/section pages reference it via the `grid_source` field instead of re-writing the grid. Keep this as a separate companion file — never re-embed the full grid inline inside every view.

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

## 6b. Footings and pile caps — same flat fields as everything else (added 2026-08-28)

A footing is the most common structural element in this corpus (**427 `footing` + 45 `pile_cap` across 50 houses**) and until now had no section of its own. Five houses independently invented five field vocabularies for it. This section closes that: **a footing carries exactly the same four load-bearing fields as a beam or a column** — no metre variants, no `cap_*` family, no mesh-specific rebar object.

```json
{
  "element_id": "F1",
  "element_type": "footing",
  "width_mm": 1000,
  "height_mm": 300,
  "main_bar": { "count": 12, "dia_mm": 9, "type": "RB", "count_printed_as": "6+6",
                "note": "6 เส้นต่อทิศทาง วางตาราง 2 ทาง" },
  "stirrup": { "count": 1, "dia_mm": 9, "type": "RB", "note": "1-Ø9มม. รัดรอบขอบฐานราก" },
  "pile_count": 5,
  "concrete_grade": "fc210",
  "steel_grade": "SR24",
  "confidence_score": 0.92,
  "confidence_flags": []
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

**The mat is `main_bar` with a single `count`, like a column — never `top`/`bottom`.** A two-way mat prints as `6+6` or `4+4`: `count` is the **sum** (12, 8) and the printed text goes in `count_printed_as`, exactly as §0.5 already requires. The two directions of a square cap are the same bar length, so one count carries the full steel weight with no loss. Never split a mat into `top`/`bottom` — that is the beam convention and it silently doubles the count (§6).

**`stirrup` on a footing is usually a fixed count, not a spacing.** An edge tie printed `1-Ø9มม. รัดรอบ` is one bar, not a repeating row:

```json
"stirrup": { "count": 1, "dia_mm": 9, "type": "RB", "note": "1-Ø9มม. รัดรอบขอบฐานราก" }
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

These describe what the footing sits on rather than the footing itself, are already consistent across houses, and stay exactly as they are: `pile_count`, `pile{}`, `lean_concrete{}`, `sand_bed_thickness_m`, `pedestal_height_m`, `pedestal_tie{}`, `ground_reference`, `base_fill`, `plan_layout`, `column_stub_mm`, `footing_type`. Add nothing new here without a `warnings[]` note (§0.4).

**A pedestal (ตอม่อ) detailed as its own member is its own element** — its own mark, its own section, `element_type: "pedestal"`, single `count` main bar per §6. But when the footing's detail sheet only prints the pedestal's height and its tie (the common case), those stay on the footing as `pedestal_height_m` / `pedestal_tie{}`: promoting them to a separate element would mean inventing a width and height nobody drew.

### Legacy files

The five houses carrying `cap_*` were extracted before this section existed and are **not being rewritten as part of this edit** — see the entry in `primary_rawjson_schema_edit_log.md`. Every new extraction (t04 included) emits the flat form only.

## 7. Spec join (plan + section/schedule)

A `plan` element (has `grid_ref`) + a `section` **or** `schedule` element (has width/height/main_bar/stirrup) for the same mark join together via `element_id` — **`section` and `schedule` are equally valid spec sources**, not limited to `section` only.

Fields joined in:
```
width_mm, height_mm, depth_mm, main_bar{}, stirrup{}, additional_bars[],
steel_section{}, material, spacing_mm, pile_count,
concrete_grade, steel_grade, spec_source, spec_confidence_score
```
(`steel_section{}`/`material` per §6a — a steel member joins exactly the same way, it just carries a section designation instead of rebar. `depth_mm`/`pile_count` per §6b — a footing joins the same way too, which is the point of it using the same field names.)

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
- **Footing flat-field rule (§6b) — written 2026-08-28 against the existing corpus, not yet exercised by a fresh extraction.** The rule matches what 253 footing elements already do, but no house has been extracted *under* it yet; t04's first real run is the test. Five houses (01/02/03/05/07 with `cap_*` as numbers, 04 with `cap_thickness_m` as an object) still carry the legacy form and have not been migrated
- **Non-square footings.** §6b defines `depth_mm` for a rectangular cap, but the Constistant pipeline currently squares `width_mm` for both plan sides and only flags the mismatch (`footing_cap_not_square_width_used_for_both_sides`). Emit `depth_mm` anyway — the data should be right before the consumer is

## 13. `site_plan` — `element_type` not standardized across houses

Checked all 5 houses' `site_plan` pattern files (2026-07-13). `element_type` values found: `boundary_line`, `building_footprint`, `building_outline`, `grading_note`, `grading_note_or_slab`, `lot_boundary`, `other`, `road`, `room`, `setback` — 10 distinct strings, but several pairs describe the same real-world thing under different names per house:

- `building_footprint` / `building_outline` — both mean the building's outline within the lot
- `boundary_line` / `lot_boundary` — both mean the property boundary line
- `grading_note` / `grading_note_or_slab` — both mean the ground-fill/grading annotation

No fixed enum has ever been given for `site_plan`'s `element_type` — each house's extraction picked its own naming independently. Not merged/standardized yet; flagged here so a future pass can decide on one canonical name per concept before this pattern is used for any downstream automation.
