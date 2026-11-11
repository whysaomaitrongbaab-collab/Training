# t07 Palfrey: the prompt tree

Written 2026-11-11 (prep for training; nothing trained, nothing deployed). The worker and the t07
builder load these files with `PURSON_PROMPTS_DIR = tune_ai/t07_Palfrey`. The tree sits at
`tune_ai/<round>/` depth so worker.py's `ORGANIZE_PY` (`PROMPTS_DIR.parent/t03/...`) and
`CV_SCAN_PY` (`PROMPTS_DIR.parent.parent/tools/...`) still resolve. Both files exist; checked.

## What was copied (from `t04_Purson/`, CRLF → LF, text otherwise byte-identical before the edits)

- `_common.md`, `pass0/prompt.md`
- `pass2/<sub>/prompt_<sub>.md` for exactly the 7 trained subtasks: gridline, plan_footing,
  plan_beam, plan_slab, section, schedule, notes

Not copied, on purpose: plan_column, material_list, soil_boring_log. With no prompt file,
`subtask_prompt()` returns None and the worker skips those pages silently (it only warns about
untrained subtasks that do have a prompt). Also not copied: `pass2/plan.md` (the template; the three
plan prompts were edited by hand in lockstep), pass3_takeoff (t07 has no pass3), READMEs,
`pass0/output_example.json`.

The loaders' markers are unchanged: `## BLOCK START` / `## BLOCK END` and the GLOSSARY comments in
`_common.md`, `## PROMPT START` / `## PROMPT END` in every prompt. The t07 header notes sit outside
them, so the model never sees them.

## Changes inside the model-visible text, per file, and why

| file | change | why |
|---|---|---|
| `_common.md` | wrapper list loses `png`, `doc_page`, `source_image` | Provenance. The worker stamps the page (`_page`, `page_NN_<sub>.json`); no consumer reads these from the model (survey: worker L633/L957/L1071, drawing-purson.js `_page`). Asking for a value the image cannot show taught t05 to print training-file names. |
| `pass0/prompt.md` | `png`, `doc_page` gone from the example and the field list | The worker ignores both (`doc["_page"] = p["page"]`). |
| `section`, `schedule`, `notes` | `png`, `doc_page`, `source_image` gone from the example | Same reason. `notes{}` stays (see KEYS below). |
| `plan_footing` / `plan_beam` / `plan_slab` | `png`, `doc_page`, `source_image`, `grid_source` gone from the example; optional `"view_title": "<printed view title, verbatim>"` added after `building`, plus one sentence; `pattern` is now one fixed value (`footing_plan` / `beam_plan` / `etc_plan`) instead of "pick one of four"; the `roof_frame_plan` trap became a single `roof_plan` trap; footing example's `sheet_name` → `แปลนฐานราก` | D5: plan labels are normalized to the worker's `SUBTASK_PATTERN`, so a prompt still saying "a roof-framing sheet is `roof_frame_plan`" would contradict every label. Nothing is lost on the web side: `PLAN_PATTERNS` treats all plan patterns alike, and a roof-framing sheet is still told apart by `floor_level: "RF"`. `view_title` is read by the web for floor detection (`sheetFloorCount`, `floorFromSheet`) and 52–62% of plan labels already carry it. |
| `gridline` | rewritten around the slim D4 label (below) | see next section |

### gridline

Example is now the D4 label shape plus one optional key (see "2026-11-11 afternoon" below):
`{"pattern":"grid_master","grid":{"x_lines":[{id,pos_m,type}],"y_lines":[...],"z_levels":[{id,level_m,type}]?},"confidence_score","confidence_flags","warnings":[]}`.

Cut: `png`, `doc_page`, `source_pages`, per-entry `source_image`; `discipline` / `sheet_code` /
`sheet_name`; the `dimension_chains` and `unassigned_dimensions` sections and every
sentence that pointed at them; the full `z_levels` section (first cut removed it; a slim one is
back, see below); per-line `confidence_score` /
`confidence_flags`, `dummy_grid_rule_check`, `non_grid_dimensions_do_not_confuse`; every
instruction to write into `warnings[]`; "a line you cannot position keeps `pos_m: null`".

Why each cut: the labels drop all of it (D4: lines keep only `id`, `pos_m`, `type`; lines without
a numeric `pos_m` are dropped; `warnings` is always `[]`). A prompt that asks for something no
label ever shows is the same prompt/label mismatch t07 exists to remove. The per-line field cut
also matters at inference: the worker pastes the model's x/y line objects verbatim into every plan
prompt as the GRID MASTER tail, and the t07 plan rows are built from slim lines, so extra per-line
keys would make inference tails differ from training tails (Lesson 12).

Kept unchanged: the axis rules (x = top-edge markers, y = side-edge markers, origin = first named
line, negative `pos_m` before it, same line on several sheets = one entry), dummy naming
(direction, not nearest; primes in reading order), the beam-endpoint rule, and the two-step
measure-by-proportion rule with its worked example (a measured line is now written like any
other line).

Added, because the labels already follow the current spec and the t04 text predates it
(`primary_rawjson_schema.md` §4, both 2026-09-27):
- rule 4 "every printed dimension tick is a line, even one nothing uses", stated for x/y only
  (reuse an existing line, otherwise a new dummy; count points, not numbers; one point = one
  line; which axis; element-internal dimensions are not ticks; a floating row adds no line);
- dummies before the first named line share its prime sequence (`1'` -0.60, `1''` 1.10, ...);
- the t04 sentence "do not invent a dummy for a slab-only edge ... the trigger is a beam
  endpoint, nothing else" contradicts rule 4 (the spec marks it superseded), so it now says what
  the spec says: a printed tick to an edge is a line; a line with neither a printed dimension nor
  a beam endpoint is still forbidden.

## Verification (2026-11-11, MEASURED)

The check pulled the loader functions verbatim out of their sources with `ast` and executed only
those defs (no module-level code, so no `worker_config.json` was read): worker.py
`load_common_block` / `load_prompt_file` / `subtask_prompt` / `SUBTASK_PATTERN`,
`build_dataset_t03.py` `load_prompt_block` (asserts the GLOSSARY markers) / `load_subtask_prompt` /
`prompt_for`, and `build_t05_night.py` `prompt_pass0` (needs `## PROMPT END`).

- all 9 files: 0 CR; pass2 holds exactly the 7 trained prompt files
- worker assembly == t04-builder assembly for all 7 subtasks, and == t05 pass0 loader for pass0
- `subtask_prompt("plan_column")` and `("material_list")` → None
- none of `source_image`, `source_pages`, `grid_source`, `"png"`, `doc_page`, `<house>`, `{{`
  in any model-visible text; also none of `dimension_chains`,
  `unassigned_dimensions`, `dummy_grid_rule_check`, `roof_frame_plan`, bare `png`, `image/`, `_หน้า`
  (and, until the 2026-11-11 afternoon change below, `z_levels`)
- every example parses as JSON (after `[ ... ]` → `[]`); each example's `pattern` equals the
  worker's `SUBTASK_PATTERN`
- tokens, `destrier_fixed/tokenizer.json` (Qwen3.6 base pre-tokenizer with `\p{M}`), with
  `no_truncation()` + `no_padding()` (a 60,000-digit string gives 60,000 ids). The t04 numbers
  reproduce the survey's exactly.

| prompt (assembled as the worker sends it) | t04 | t07 | Δ |
|---|---:|---:|---:|
| COMMON alone | 1,661 | 1,654 | −7 |
| gridline | 4,471 | 3,635 → 4,055 (after the z_levels change, MEASURED with the same tokenizer) | −836 → −416 |
| plan_footing | 4,949 | 4,607 | −342 |
| plan_beam | 4,969 | 4,663 | −306 |
| plan_slab | 4,945 | 4,605 | −340 |
| section | 3,954 | 3,910 | −44 |
| schedule | 3,305 | 3,261 | −44 |
| notes | 3,453 | 3,409 | −44 |
| pass0 (no COMMON) | 1,976 | 1,922 | −54 |

Plan rows add the GRID MASTER tail and, for pass2.4, the hint. Neither is counted here.

## `pass2/KEYS.json` (the builder's top-level label allowlist)

Parsed from the first ```json block of each edited prompt, in example order. It matches D5 for
gridline, plan_*, section, schedule and pass0. **It differs for notes:** the notes example
carries `notes{}` (schema §4a, the parsed spec values), so KEYS has `notes` and D5's expected list
does not. Kept on purpose. The web reads it (`raw-extraction-adapter.js`
`files.filter(f => f.pattern === 'notes' && f.notes)` → `fc_ksc`, `fy_main_ksc`,
`fy_stirrup_ksc`, `cover_mm`), and 220 of 402 notes labels carry it (survey key audit). Dropping
it would teach the model to stop emitting the only concrete/steel spec values the web takes from
a drawing.

## 2026-11-11 afternoon: two decided changes the first build had not applied

Both measured by `build_t07.py` (numbers in `build_report.md`, section "2026-11-11 afternoon").

**1. `grid.z_levels` is back in the gridline task, slim.** The 11-pass design's grid master pass
outputs x/y lines plus z levels; D4 had dropped z. Prompt (`pass2/gridline/prompt_gridline.md`):
the example grid gets an optional `"z_levels": [{id, level_m, type}]`; a short section adapted from
t04 (one set per building; `id` = printed label verbatim or `null`; `level_m` = signed metres from
the datum; `type` datum / named / dummy; read from elevations, sections and side profiles; "omit
`z_levels` when none of the provided pages print level marks"; a level whose number is not printed
is left out, never scaled). The t04 per-entry `source_image`, notes, confidence fields and `null`
levels stay cut. The tail the worker pastes into plan prompts is unchanged: x_lines + y_lines only
(`grid_tail()` ignores z).

Labels (`build_t07.py` `slim_levels`): entries keep exactly `{id, level_m, type}` in that order.
An entry is written only if (a) `level_m` is a number, (b) the level's own GT source page is
among that row's images (first 4 pages by page number, same rule as before), (c) the id passes the
leak gate. A row with no surviving entry has no `z_levels` key at all. Normalisations, all counted
in the report: `type` outside datum/named/dummy (old GT: beam_top, floor, landing, ridge) becomes
`named` when the level has an id, else `dummy`; an id that is only the printed number ("+0.40",
"@2.05", "±0.00") or a lower-case snake slug ("roof_ridge", "reference") becomes `null` (the prompt
says number-only means `null`; a slug is not a printed label); `named` with no id becomes `dummy`
(the prompt: named = a labelled level). This is a decision of mine, not of the brief: without it
about one entry in five would have contradicted the prompt. The per-entry visibility filter is
conservative: a level printed on a shown page but credited in the GT to another page is not written.

**2. pass0 learns the sheet list.** The prompt text is unchanged (so rows without a list equal what
the worker sends today). About half of the pass0 rows of houses with a usable index page get
`"\n\nSHEET LIST (from this drawing set's index page)\n" + json.dumps([{title, sheet_range}...])`
in the same text part. Format, source and the worker requirement: `SHEET_LIST_format.md`.

**KEYS.json** gained dotted entries for the nested allowlists: `gridline.grid` (x_lines, y_lines,
z_levels), `gridline.grid.x_lines` / `.y_lines` (id, pos_m, type) and `gridline.grid.z_levels`
(id, level_m, type). The top-level lists are unchanged; the builder asserts the z entries on load,
and `sanitize_labels.py` `schema_info` reports any nested key outside them.

## Open points for the builder (not prompt changes)

- 120 of 402 notes labels carry a top-level `elements` (survey key audit). Neither the prompt nor
  KEYS names it, so the allowlist drops it. If the sanitize step asserts element counts per row,
  those rows will trip it. Decide whether that is meant before the build.
- `view_title` is in KEYS only for plan_*. Section (1,039/1,511), schedule (252/373) and notes
  (229/402) labels carry it and will lose it. That is per D5.
- Gridline `building` (25 rows) is dropped. The 3 outbuilding masters (`หน้า00b`: บ้าน_ใหญ่_1ชั้น_01
  สุขา, บ้าน_เล็ก_2ชั้น_19 โรงรถ, บ้าน_ใหญ่_2ชั้น_21 ส่วนต่อเติม) become ordinary gridline rows. The
  prompt's "extract the main building only" holds if their images show only that building.
  Not checked.
- Raw-tree gridline labels made before rule 4 probably have fewer tick-dummies than the prompt
  asks for (INFERRED: op_fix only ever ran on `json_แก้ไขแล้ว/`, and the survey found `"edge"`
  chain ends in 20–26% of masters). That is label quality, not a prompt bug.

## 2026-11-11 evening: gridline is page-by-page (Makham's order)

`pass2/gridline/prompt_gridline.md` rewritten. One page image + the `GRID SO FAR` tail in, only what THIS page adds out.
The rules both the training rows and the worker must share live in `grid_incremental.py` (`MARK`, `tail`, `merge_delta`,
`page_order`, `derive_steps`); `test_grid_incremental.py` checks them by hand-computed cases and runs inside
`build_t07.py --selftest`.

What the model-visible text lost and gained:
- **gone:** the whole "measure a dummy by proportion" section (the P / U two-step pixel arithmetic and its worked example);
  the "one grid master for the whole building from every page at once" framing; origin and prime-sequence rules as
  the model's job (it now writes a negative `pos_m` for a named line left of the known origin and `<named line>'` with one
  prime for every new dummy - the code renumbers); the sentence "if two sheets print different positions keep the first"
  is now "keep the known one".
- **new:** the GRID SO FAR section (positions in the known frame; first page = origin at its leftmost `named` line); "a page
  that adds nothing is a normal answer"; "never repeat a known line"; "a beam end is not a reason to add a line unless a
  printed dimension row gives that point a position".
- tokens (assembled as the worker sends it, same tokenizer as the table above): gridline **3,350** (was 4,055 after the z_levels
  change). The user text adds the tail: empty grid on the first page, the accumulated lines after that.

Labels (`build_t07.py` `incremental_rows`): see `build_report.md` section "2026-11-11 evening" for every number. Short version: a
line is added at the first page whose printed dimension rows connect it to what is known (the GT `dimension_chains` carry the
page of each row; chain arithmetic matches the GT positions on 15,951 of 15,995 segments); masters without chains or whose ids do
not follow the spec's mechanical naming get no gridline rows; empty pages keep at most 2 rows per master; `confidence_flags` is
`[]` on page rows; plan rows still carry the full GT master as their GRID MASTER tail (the model that wrote the grid may have
missed about 5% of those lines - a known train/inference gap).

Worker side (NOT done): the page loop, the stop rule and the merge. Spec in `t07_workflow.md`, section "ตอน deploy".

The numbers about the ground truth quoted in this section (15,995 checkable chain segments, 44 mismatches, 3,869 justified / 225 unjustified lines, 39 of them used by a plan element, 161 / 10 masters following / breaking the naming rule) come from `check_gt_provenance.py` (read-only, rerunnable).
