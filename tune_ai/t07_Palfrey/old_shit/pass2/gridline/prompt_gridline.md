# pass2_gridline.md - the grid master, ONE PAGE AT A TIME

**Input (per call):** ONE page image + the text `GRID SO FAR` (the lines and levels read from the earlier pages of
this building, same shape as the answer; empty on the first page). Pages come in this order: beam plan, footing plan,
roof framing, any other plan, then sections / elevations (levels).
**Output:** only what THIS page adds - the new lines and levels, as a `grid{}` object per `primary_rawjson_schema.md` §4.
The caller merges every reply into the master and renumbers (origin, primes); the worker repeats the call page by page.

Runs **first** in Pass 2. Every plan subtask blocks on the merged result: spans are computed from it and from nothing else.

Prepend `../../_common.md`. No embedded glossary here (2026-08-29 review) - this sheet
never touches `element_type` or rebar, and every position it reports is already a decimal metre
read straight off a printed dimension chain, so none of the Thai-field lookup applies.

**t07 (Palfrey) copy, 2026-11-11. Rewritten twice that day.**

*First cut (morning)* - copied from `tune_ai/t04_Purson/pass2/gridline/`, then cut down to the slim label t07 trains on:
`{pattern, grid: {x_lines, y_lines: [{id, pos_m, type}], z_levels?: [{id, level_m, type}]},
confidence_score, confidence_flags, warnings: []}`. Why (numbers from the 2026-11-11 survey, details in
`../../PROMPTS_t07.md`): the full master (z_levels, dimension_chains, unassigned_dimensions, per-line notes and
sources) made 22 of 215 gridline rows longer than MAX_LENGTH 47,104; nothing downstream reads more than x/y
`id` / `pos_m` / `type`; the worker pastes the model's x/y line objects verbatim into the plan prompts as the GRID
MASTER tail, so a line must carry exactly `id` / `pos_m` / `type` (rule_of_tune Lesson 12). `z_levels` came back the
same day as an optional slim list. Cut from the prompt: `png`, `doc_page`, `source_pages`, `source_image`;
`discipline` / `sheet_code` / `sheet_name`; the `dimension_chains` and `unassigned_dimensions` sections; the per-line
confidence fields; every instruction to write into `warnings[]`.

*Evening (Makham: "send it one page at a time, beam plan first, then footing, adding as you go, so Qwen does not
hallucinate")* - the row shows ONE page + `GRID SO FAR` and the answer is only the DELTA. Mechanics and the rules both
sides must share: `../../grid_incremental.py` (`merge_delta`, `tail`, `derive_steps`) - the training rows and the worker
use the same functions. What changed in the model-visible text:
- the task is "what does THIS page add"; an empty answer (`x_lines: []`, `y_lines: []`) is a normal answer;
- origin and primes are not the model's job any more: a named line left of the known origin is written with a negative
  `pos_m`, every new dummy is written as `<named line it sits right of>'` (one prime) - the code renumbers;
- **the whole "measure a dummy by proportion" section is gone** (two-step pixel P / U arithmetic). It was the most
  hallucination-prone paragraph of the prompt, and in the ground truth only about 1% of lines (39 of 3,869, all dummies
  that a beam endpoint needs and no dimension row prints) could not be justified by a printed dimension. A line no
  printed dimension reaches is simply not added; the beam that lands on it is reported unresolved by its own plan sheet;
- the beam-endpoint rule is kept only as "a beam end is not a reason to add a line unless a dimension row prints it".

**z_levels** keep their t04 rules (one set per building; `id` = printed label verbatim or `null`; `level_m` signed metres
from the datum; `type` datum / named / dummy). The training labels carry a level only on the page that prints it
(`build_t07.py` `slim_levels` + `grid_incremental.derive_steps`), so the model is never asked to write a level it cannot
see. The GRID MASTER tail the worker pastes into the plan prompts stays x/y only.

---

## PROMPT START

You are reading ONE sheet of a building's drawing set - a page that shows a column grid or a dimension chain You are also
given GRID SO FAR - the lines and levels that were already read from the earlier pages of this same building (empty on
the first page) Give only what THIS page adds Never repeat a line that is already in GRID SO FAR

Output one JSON object and nothing else

```json
{
  "pattern": "grid_master",
  "grid": {
    "x_lines": [
      { "id": "1", "pos_m": -4.0, "type": "named" },
      { "id": "3'", "pos_m": 3.6, "type": "dummy" }
    ],
    "y_lines": [],
    "z_levels": [
      { "id": "ระดับอ้างอิง", "level_m": 0.0, "type": "datum" }
    ]
  },
  "confidence_score": 0.9,
  "confidence_flags": [],
  "warnings": []
}
```

This file carries only `pattern`, `grid`, `confidence_score`, `confidence_flags` and `warnings` - no `discipline`,
`sheet_code` or `sheet_name` `grid` holds `x_lines` and `y_lines` (both always present, an empty list when this page adds
nothing on that axis), plus `z_levels` when this page prints level marks that GRID SO FAR does not have yet - omit it
otherwise Every line carries exactly `id`, `pos_m` and `type` - `type` is `named` for a line with its own printed marker,
`dummy` for every other line Every level carries exactly `id`, `level_m` and `type` `warnings` stays an empty list

What GRID SO FAR is

- The text after `GRID SO FAR` is a JSON object shaped like your answer - the lines and levels known so far, with their
  positions in metres from its own origin (the leftmost `named` line is `0.0`)
- Your new `pos_m` values are written in that same frame - never in a frame of your own

When nothing is known yet (the first page)

- Origin `0.0` is the leftmost `named` line you can read on this page, on each axis separately
- Positions come from the printed dimension rows of this page, added up from that line

The rule that governs this page

Look at every printed dimension row of this page - plan, elevation, section or roof, whichever sheet it is Every point that
a printed x or y dimension marks is a line, even when nothing on the sheet uses it

- For each printed segment of an x or y dimension row, look at both of its ends If an end sits on a line that is already in
  GRID SO FAR (or one you are adding in this same answer), reuse that line Otherwise that end is a new line
- Its `pos_m` is the known line it hangs off plus or minus the printed segments between them, added up That is arithmetic
  on printed numbers, so it still counts as read off the drawing
- Count points, not numbers A gap between `A` and `B` printed as 10 segments has 9 ticks inside it, so 9 new dummy lines
  Ten distances all measured from `A` mark 10 different points, so 10 new dummy lines
- One point is one line A tick at the same `pos_m` as a line you already know, to the millimetre, is that line - do not add
  it, even when this page prints it too Two ticks with different `pos_m` are two lines, even a few centimetres apart
- A dimension row belongs to the axis whose grid markers it runs between - numbers (`1`, `2`, `3`) are x, letters (`A`,
  `B`, `ก`, `ข`) are y Check the markers, not the sheet title
- Not an axis tick - a dimension inside one element's own detail, such as a section's width or depth, a pile cap's pile
  spacing or a rebar spacing
- A dimension row that touches no known line - and, on the first page, no `named` marker you can read - cannot be
  positioned, so it adds nothing Leave it out, a later page may connect it
- Every `pos_m` is a printed number or a sum of printed numbers Never estimate a position, never measure one on the
  image, never read one from where a line looks to be A beam that ends somewhere is not a reason to add a line unless a
  printed dimension row gives that point a position

`x_lines` / `y_lines` - the plan axes (§4)

- `x_lines` = the horizontal axis, markers along the top edge (usually `1`, `2`, `3`…)
  `y_lines` = the vertical axis, markers along the side edge (usually `A`, `B`, `C`… - Thai
  `ก`/`ข`/`ค` stays Thai)
- A `named` line is one that has its own printed marker, its `id` is that marker, verbatim A line further to the left (x)
  or higher (y) than every known `named` line gets a negative `pos_m` in your answer - the caller moves the origin
- If two sheets print different positions for a line that is already known, keep the known one - do not add it again

Dummy lines

A dummy line is any line that has no printed marker of its own Write its `id` as the `named` line it sits to the right of (x)
or below (y) plus ONE prime - `3'` for a dummy after line `3` Direction, not nearest A dummy at 5.2 between `2`(5.0) and
`3`(8.5) is `2'`, even though `2` is far closer A dummy before the first `named` line takes the first `named` line's id plus
one prime Do not try to count the primes among several dummies - when you add several in the same gap write the same
`id` for each, they are renumbered in reading order afterwards, so only `pos_m` has to be right Never rewrite or rename a
line that is already known

`z_levels` - the vertical axis (optional)

Levels are printed on elevations, sections and side profiles, and almost nowhere else Add only levels this page prints
that GRID SO FAR does not have yet If this page prints no new level mark, leave `z_levels` out of `grid`

- `id` is the printed level label, verbatim - `"ระดับหลังคาน"`, not a translation, not `"F1"` A
  level printed with only a number and no label gets `id: null`
- `level_m` is a number in metres, signed relative to the datum, as printed - `"±0.00"` becomes
  `0.0`, `"+3.75"` becomes `3.75`, a level below the datum is negative
- `type` is `datum` for the `±0.00` reference, `named` for a labelled level, `dummy` for a level
  the dimension chain implies but never labels
- A level whose number is not printed on this page is left out - an elevation gives you no second axis to measure against,
  so a level is never scaled or guessed

Rules

- Every `pos_m` and every `level_m` traces to a printed number, read directly or added up along a printed dimension row
- One grid master per building If the sheet shows more than one building, take the main building only
- A page that adds nothing is a normal answer - return both lists empty

## PROMPT END
