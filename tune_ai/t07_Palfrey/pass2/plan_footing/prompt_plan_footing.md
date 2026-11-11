# pass2_plan_footing.md - footing / pile-cap plan

Rendered 2026-08-29 from `../plan.md`'s shared template - one concrete file per subtask now, not a template, per Makham's call to split them. The old one-file-four-subtasks design's own warning about copy drift (`../plan.md` still documents it) is still true - if a rule below needs to change for every plan subtask at once, edit `../plan.md` and re-render all four, do not patch this file alone and let it drift from its siblings.

**Input:** one `plan_footing` sheet image plus the building's grid master (`x_lines`/`y_lines` only, extracted from `<house>_หน้า00_gridline.json`).
**Output:** one JSON file, `pattern` decided from what the sheet draws (see the prompt body).

Prepend `../../_common.md`. Requires `_shared/gridmaster.json` - the manifest's `needs` gate blocks this subtask until it exists.

**t07 (Palfrey) copy, 2026-11-11.** Copied from `tune_ai/t04_Purson/pass2/plan_footing/`. `plan.md`
(the template) was not copied: the three t07 plan prompts (footing/beam/slab) were edited by hand
in lockstep and differ only in the title, the first prompt line, the `pattern` paragraph and the
example values. Changes inside the prompt: (1) `png`, `doc_page`, `source_image` and
`grid_source` are gone from the example (provenance the worker stamps itself; the labels drop
them, allowlist in `../KEYS.json`); (2) the example gains an optional `view_title` (the web reads
it for floor detection, about half the labels already carry it); (3) `pattern` is no longer
chosen from four values: it is the worker's fixed `SUBTASK_PATTERN` value for this subtask
(`footing_plan`), the value the t07 labels are normalized to (the web treats every plan pattern
alike, `PLAN_PATTERNS` in raw-extraction-adapter.js); the example's `sheet_name` became a
footing-plan title to match. The "Output" line above is t04 history. Why: `../../PROMPTS_t07.md`.

---

## PROMPT START

You are reading a structural plan sheet Extract footings (ฐานราก) and the columns marked with them

You are also given the building's grid master Use it - the spans you report come from it, not
from the image

Output one JSON object and nothing else

Thai to field glossary (not a rule - a lookup)

The drawing is Thai, this prompt and every value you emit are English These are the
Thai words that actually appear on our sheets and what each one controls Use it to
read, never to rewrite the rule directly below still holds - a printed label stays
Thai, verbatim (this pass is position and count only - no rebar fields, so the rebar
words are left out)

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

Words that decide a dimension field

- ขนาด → `width_mm` and `height_mm`
- กว้าง → `width_mm`
- ยาว, ช่วง → `span_length_m`
- หนา → `thickness_mm`
- สูง → `height_mm`
- ลึก → `depth_mm`
- ระดับ → `level_m`
- จำนวน, ต้น → `count`

Units and abbreviations

`มม` = mm · `ซม` = cm (×10 → mm) · `ม`, `เมตร` = m · `นิ้ว` = inch ·
`ตรม` = m² · `ลบม` = m³ · `กก` = kg · `คสล` = reinforced concrete ·
`มอก` = TIS standard number · `ชั้นล่าง` = ground floor · `ชั้นบน` = upper floor

A Thai word not in this list is not permission to invent an `element_type` - pick the
closest value from §0.4 and say so in `warnings[]`

`pattern` - fixed by the subtask

`pattern` is always `"footing_plan"` in this file, whatever the sheet's title says - the subtask
decides it

```json
{
  "discipline": "structural",
  "sheet_code": "S-03",
  "sheet_name": "แปลนฐานราก",
  "pattern": "footing_plan",
  "floor_level": "F1",
  "building": "main",
  "view_title": "<printed view title, verbatim>",
  "elements": [ ... ],
  "confidence_score": 0.86,
  "confidence_flags": [],
  "warnings": []
}
```

A trap that has cost real data before

Never write `roof_plan` That value exists and means the architectural roof plan - ridge lines,
eaves, roofing material, no structural marks A roof-framing sheet filed under it is not read at
all and its beams never reach a BOQ This happened to 8 houses out of 11

`floor_level`

Read it from the sheet title (`แปลนคาน ชั้นล่าง` → `"F1"`, `ชั้นสอง` → `"F2"`, a roof framing
sheet → `"RF"`) If the title does not say, use `null` and note it in `warnings[]` - do not assume
`F1`

`view_title` is optional - the title printed with this view, verbatim, Thai stays Thai
(`แปลนฐานราก`, `แปลนคาน ชั้นล่าง`) Leave the key out when the view prints no title of its own

Line elements vs point elements (§4)

A beam is a line It gets one entry per span between two grid points - one atomic segment,
never merged across a whole gridline

```json
{
  "element_id": "B2",
  "element_type": "beam",
  "grid_ref_start": "D1",
  "grid_ref_end": "D2",
  "span_length_m": 4.0,
  "span_source": "grid_table",
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

A footing or column is a point All positions of one mark merge into one entry with an
array of refs and a count

```json
{
  "element_id": "F1",
  "element_type": "footing",
  "grid_refs": ["A1", "A2", "B1"],
  "count": 3,
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

`grid_refs` is an array of strings, never a comma-joined string Each ref is a point with no dash
(`"C1"`, not `"C-1"`) - §0.8

A slab marker with no resolvable position (a circled `SO`/`SI`/`ST` tag sitting inside a bay) is
`element_type: "slab"` with `grid_refs: []`, `confidence_flags: ["marker_only_not_a_line_element"]`,
and the bays it covers described in `description`

`span_length_m` comes from the grid, never from the image (§4)

Look up both endpoints in the grid master and subtract

- Both endpoints known, same row or same column → `span_source: "grid_table"`
- The distance is printed locally on this sheet and you used that → `span_source: "local_dimension"`
- Nothing printed anywhere, but you measured it against the grid by proportion, as described
  below → `span_source: "scaled_from_grid"`
- You could not resolve it even by proportion → `span_length_m: null`,
  `span_source: "unresolved"`, and name the missing line in `warnings[]`
- The element is a point, not a line → `span_source: "n/a"`

Never estimate a span by how long the line looks alone A wrong span silently becomes a wrong
concrete volume and a wrong steel weight downstream

Measuring against the grid by proportion - what the grid master is for

The grid master is a ruler printed on this same image Two grid lines whose `pos_m` you already
know tell you the scale of the drawing, so a span with no printed dimension can still be
recovered by proportion instead of being thrown away That is measuring against a printed
reference, not guessing

Work in two separate steps, always in this order - find every pixel number first, convert to
metres second A metres figure produced in one leap, without its pixel numbers committed first,
is a guess dressed as a measurement

Step 1 - find the pixels (no metres yet)

- Pick two grid lines on the same axis as the span you are measuring, both with a known `pos_m`
  Take the pair furthest apart - a long baseline makes the error small
- Measure those two lines' separation on the image Call it P pixels
- Measure the unknown span on the image along that same axis Call it U pixels
- Step 1 ends with exactly two pixel numbers, P and U, and no arithmetic done on them yet

Step 2 - convert the pixels to real length

- The two reference lines' true separation is the difference of their `pos_m` Call it R metres
- The span is U divided by P, multiplied by R, in metres
- Look at the printed dimension chain If your answer lands within about 0.05 m of a value the
  chain actually prints, use the printed value instead - the chain is the truth and your
  measurement only found which entry of it applies

A worked example - the shape your work must take

Grid lines `2` and `5` have `pos_m` 4.00 and 12.00 On the image they are 400 pixels apart, so
P is 400 The unknown span, measured along that same axis, is 150 pixels, so U is 150 That ends
Step 1 Now convert - R is 12.00 minus 4.00, which is 8.00 The span is 150 divided by 400,
times 8.00, which is 3.00 m The chain prints no 3.00 anywhere, so the element records
`span_length_m: 3.0` with `span_source: "scaled_from_grid"`, the flag
`scaled_between:2,5 P:400 U:150`, and a lower `confidence_score`

Rules that keep this honest

- A printed value always wins Never scale something the drawing states outright This applies
  only to a span that would otherwise be `unresolved`
- Use the x axis scale for a horizontal span and the y axis scale for a vertical one, never one
  for the other A scan that was cropped or resized does not stretch both axes equally, and
  borrowing one axis to measure the other produces a wrong number that looks right
- A diagonal span cannot be measured this way Leave it `unresolved`
- `span_source` is `scaled_from_grid`, never `grid_table` `grid_table` means you read the number
  off the grid, `scaled_from_grid` means you derived it Whoever reads this file has to be able
  to tell those apart
- Round to 2 decimal places A drawing does not carry more precision than that, and a value like
  3.9847 reads as a measurement when it is an estimate
- Record the whole measurement in `confidence_flags` - the two reference lines and both pixel
  numbers, for example `scaled_between:1,3 P:380 U:142` A human must be able to redo your
  arithmetic from the flag alone If you cannot state P and U, you did not measure - the span
  is `unresolved`, not `scaled_from_grid` A scaled value with no pixel numbers behind it is
  the guess this rule exists to prevent
- Give a scaled span a lower `confidence_score` than a read one It is a real number, but it is
  not a number you read
- `unresolved` after attempting Step 1 and failing is a correct answer - you could not find two
  same-axis lines with known `pos_m`, or could not put a pixel number on both endpoints
  `unresolved` without attempting Step 1 is not

Every beam endpoint must land on a named line - the beam-endpoint rule (§4)

Trace every beam segment on the sheet, including short stubs and the crowded ones in stair and
closet clusters For each endpoint, find its line in the grid master

If an endpoint sits on no known line, the grid master is missing a dummy grid Record the beam
with `span_source: "unresolved"` and say exactly which point could not be named in `warnings[]`,
so the grid master can be fixed

Three things you must never do instead - each one silently loses a real beam

- Drop the beam because it "isn't on the grid"
- Write a prose description with no `grid_ref_start` / `grid_ref_end`
- Set `grid_ref_start` equal to `grid_ref_end` with a `null` span

A beam bearing on another beam rather than a column is normal - record it against the dummy grid
and add a flag like `"bears_on_beam:B4(start)"`

Read the sheet, do not pattern-fill it

Extract what is actually drawn A plan has a specific, finite set of members in specific places -
it is never a grid with the same beam in every cell

If you notice yourself emitting the same `element_id` repeatedly with only the grid reference
advancing (`1-2`, `2-3`, `3-4`, `4-5`…) in a way you are not reading off the drawing, stop and
close the JSON immediately A short honest file that ends properly is correct and usable A long
repetitive one that never closes is worthless - it cannot even be parsed, so every element in it,
including the real ones you read at the start, is lost

Twenty-five accurate beams beat two hundred invented ones

Rules

- `element_id` exactly as printed `B4X` is not `B4` - an X variant is a different mark (§0.3)
- Two different members never share an `element_id` on one sheet (§0.3)
- No rebar specs here This sheet gives position and count, the section and schedule sheets give
  the spec, joined later by `element_id` (§7)
- Anything ambiguous, blurred, or judged goes in `warnings[]`

## PROMPT END
