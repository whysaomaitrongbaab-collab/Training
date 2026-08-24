# t03 — notes (2026-08-21)

## แผนผังโฟลเดอร์ — อ่านตามลำดับ pass

```
t03/
├── README.md                 ← ไฟล์นี้ (ทำไม/ตัดสินใจอะไรไว้บ้าง)
├── pass_design.csv           ← ตารางสรุปทุก pass/subtask หน้าเดียวจบ
├── dataset_sizing.md         ← ควรมีกี่หลัง + annotate อะไรบ้าง (นับของจริง 2026-08-22)
│                               ⚠️ plan_column มีแค่ 2 ไฟล์ใน 11 หลัง — subtask นี้เทรนไม่ได้
├── _common.md                ← กฎร่วม เอาไปแปะหัว prompt ของ pass 2 และ 3 ทุกตัว
│
├── pass0_classify/           ① AI ดูรูปแต่ละหน้า → บอกว่าหน้านี้คือ subtask อะไร
│   ├── prompt.md
│   └── output_example.json   ← สัญญาว่า pass 0 ต้องออกมาหน้าตาแบบนี้ (pass 1 กินต่อ)
│
├── pass1_organize/           ② ไม่ใช้ AI — ตัดรูปหน้าที่มีหลาย view + แยกเป็นโฟลเดอร์ต่อ subtask
│   └── organize.py
│
├── pass2_used/               ③ 10 subtask ที่ Constistant เอาไปใช้จริง
│   ├── gridline.md           ← ต้องรันก่อนเพื่อน ตัวอื่นรอ grid master อันนี้
│   ├── plan.md               ← ครอบ 4 subtask: footing/column/beam/slab (แทนค่า {{TARGET}})
│   ├── section.md
│   ├── schedule.md
│   ├── notes.md
│   ├── material_list.md
│   └── soil_boring_log.md
│
├── pass3_unused/             ④ 11 subtask ที่ยังไม่มีอะไรใน Constistant อ่าน แต่ถอดไว้ก่อน
│   └── extract.md            ← ไฟล์เดียวครอบทั้ง 11 (แทนค่า {{PATTERN}})
│
└── _old_2026-08-04_two_pass/ ⛔ ดีไซน์เก่า 2 pass เลิกใช้แล้ว เก็บไว้อ่านย้อนหลัง
```

**สถานะ: ยังไม่ได้รันอะไรเลยสักตัว** — ทั้ง prompt และ `organize.py`

> **อัปเดต 2026-08-24:** dataset สร้างแล้ว — `data_before_tune/` (452 ตัวอย่าง 7 subtasks จาก
> json_แก้ไขแล้ว ทั้ง 11 หลังที่ normalize แล้ววันเดียวกัน) + round doc `t03_workflow.md`
> (rule_of_tune ข้อ 4) — การตัดสินใจ 4 ข้อรอมะขามทบทวนก่อนเทรน อยู่ในนั้น
> ตัว prompt/organize.py ยังไม่เคยรันกับโมเดลจริงเหมือนเดิม

t03 replaces t01/t02's single-shot "read the whole page, output everything" extraction with a
multi-pass pipeline: Pass 0 classifies each page's rawjson `pattern`, **Pass 1 organizes files
into one folder per subtask** (no AI — each folder ends up holding everything that subtask
needs, e.g. the `plan` folder gets the plan-page images plus the grid master; not just an
ordering/queue, an actual physical grouping), **Pass 2 covers the 7 patterns
Constistant actually consumes**, **Pass 3 covers the remaining 8 patterns that still need
extracting but nothing in Constistant reads them yet** (split decided 2026-08-21, Makham).
`unknown` (the 16th pattern, catch-all) has no subtask in either pass. Full breakdown in
[`pass_design.csv`](pass_design.csv), referenced against the 16-pattern taxonomy in
`../../rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md` §1.

**Pass 2 (used in Constistant):** `gridline`, `plan`, `section`, `schedule`, `notes`,
`material_list`, `soil_boring_log`.
**Pass 3 (not used, extracted anyway):** `index`, `site_plan`, `side_profile`, `title`,
`symbol`, `roof_plan`, `misc`, `bbs_schedule`.

`soil_boring_log` is the one judgment call: `raw-extraction-adapter.js`'s `ADAPTED_PATTERNS`
(the raw-JSON-import path) never touches it, but Constistant *does* consume it through a
separate door — `QT_PROMPT_SOIL_BORING_LOG` → `site-index.js` → Foundation Design's
bearing-capacity calc. Put it in Pass 2 on the "used anywhere in Constistant" reading of
Makham's split. If the intended criterion is narrower (only the raw-JSON-import path counts),
move it to Pass 3 — flagged in the CSV's note column, not yet confirmed.

**Status: design only.** Nothing in this folder has been run yet. Makham described the pass
structure this session; the full t03 spec (which model, prompt content per subtask, training
data shape) has not been described yet — do not assume `pass_design.csv` is final.

## Why per-pattern passes (not one big prompt)

t02 (single prompt reads a whole page and emits every element type at once) is the thing that
produced the beam-plan failure documented in `../t02/ผล/08บ้าน_เล็ก_1ชั้น_03/` — see the
2026-08-21 workmen's diary entry. Splitting into one subtask per pattern makes each individual
generation shorter and more constrained, which should reduce (not eliminate — see below) the
model's tendency to loop when it's uncertain.

## Prompts — written 2026-08-21

Ten files, all English, **sourced from `primary_rawjson_schema.md` only** — no rule in them comes
from anywhere else. If a prompt and the spec disagree, the spec wins and the prompt is the bug.
**None has been run**, not against the model, not against a real page.

### Why one prompt covers several subtasks

`pass2_used/plan.md` covers four subtasks and `pass3_unused/extract.md` covers eleven, both
parameterized by substitution rather than copied per subtask. Four or eleven near-identical files
drift apart — and drift between same-shaped files is the exact failure `primary_rawjson_schema.md`
§0 exists to stop. Change a rule once, and every subtask that shares it changes together.

### The anti-loop wording is deliberate

`pass2_used/plan.md` and `pass3_unused/extract.md` both carry an explicit instruction to stop and
close the JSON on noticing repetition. That is aimed at a specific observed failure: on 2026-08-20
t02 hit house 08's beam plan, fell into emitting the same `B2` beam across every grid cell, and ran
to the token cap without ever closing the JSON — so the whole page, including the real elements read
at the start, was lost to a parse error.

The prompt wording is a second line of defence, not the fix. The real fixes live in the runner
(`repetition_penalty` / `no_repeat_ngram_size`, and the grammar-constrained decoding added to
`run_house_batch.py`).

### Before running any of these

- `pass0_classify/prompt.md` is the highest-stakes prompt in the pipeline — everything routes on it,
  and it is the only chance to capture `sheet_code`/`sheet_name` before the title block is cropped
  away. Check its output by hand on a full house before trusting Pass 1's folder tree.
- `pass2_used/gridline.md` blocks every plan subtask. A wrong `pos_m` here is a wrong span, a wrong
  concrete volume and a wrong steel weight, everywhere, with nothing downstream able to detect it.
- Run one house end to end and read the output before spending GPU time on eleven.

### Two spec gaps found while writing them — one now closed

1. **`notes` had no defined value fields, so the notes → Constistant path produced nothing.**
   `raw-extraction-adapter.js` reads `notes.fc_ksc` / `fy_main_ksc` / `fy_stirrup_ksc` /
   `cover_mm` to build `extractedNotes`, but `primary_rawjson_schema.md` had **never defined that
   shape**. `fc_ksc` appeared in exactly **1 of 55** real notes files, and that file put it at top
   level under `concrete_strength` rather than under `notes` — so the value reached the consumer
   for **no house at all**, and the project-wide concrete and steel specification has never
   entered the pipeline.

   **Closed 2026-08-21 on Makham's decision ("define the fields in the spec"):** new
   `primary_rawjson_schema.md` **§4a**. Two layers, following the precedent already used for
   `BeamLibraryEntry`'s flat `main_bar_*` aliases — a nested half that records what the drawing
   actually prints, and four flat one-way copies so the existing consumer needs no change:

   - `concrete{ grade_label, fc_ksc, curing_days, printed_as }`
   - `steel{ round_bar{}, deformed_bar{} }` — **split by bar notation (RB/DB), not by role.** Thai
     notes sheets specify "RB = SR-24 = 2400, DB = SD-40 = 4000"; they never say "main bars are X,
     stirrups are Y". The `fy_main_ksc` / `fy_stirrup_ksc` split the consumer wants is an
     interpretation, so it lives in the derived layer with the convention stated and overridable.
   - `cover{ default_mm, by_condition[] }` — **millimetres**, since cover is a member dimension
     (§0.5). Four existing files carry `rebar_cover_m` in metres, which is a §0.5 violation.
   - flat: `fc_ksc`, `fy_main_ksc`, `fy_stirrup_ksc`, `cover_mm`, each a copy of a nested value,
     `null` when its source is absent — never a convention-based default.

2. **`notes` is the worst-drifted pattern in the data set** — still open. Measured across the 11
   houses: 55 notes files carry the same content under **six different container keys** — `notes`
   (22), `notes_sections` (9), `sections` (8), `spec_notes` (3), `notes_text` (1), `raw_text` (1)
   — plus one-offs like `reference_standard`, `concrete_strength`, `precast_plank_spec`,
   `bangkok_additional_requirements`. §4a now pins `sections[]` + `notes{}` as the only two
   allowed names, but **the 55 existing files have not been migrated.**

This is the same class of problem as the `roof_frame_plan` bug below, and larger.

## Pass 1 — built 2026-08-21 (`pass1_organize/organize.py`)

**⚠️ Written but never run.** Makham asked for it without a test pass. Nothing in it has touched
a real image yet — run it on one house with a hand-written `pass0.json` before trusting any of
the cropping.

What it does: reads pass 0's output, cuts multi-view pages into one image per view with OpenCV,
scatters everything into `pass2/<subtask>/images/` + `pass3/<subtask>/images/`, and writes a
`manifest.json` per folder listing what that subtask needs.

**Why crop at all** — visual tokens are pinned at 5120/image (must match training). A full page
spreads those 5120 across the whole sheet; a half-page crop spends the same budget on half the
area, doubling effective resolution on the thing being read. That's an accuracy win, not just a
token saving, and it matters most on exactly the sheets t02 failed on.

**Scale of the problem, measured:** 62 of ~1,100 pages across the 11 houses carry more than one
view (~6%) — but they include the highest-value structural sheets (`footing_plan + beam_plan` on
one page, `tie_beam_plan + roof_frame_plan` on another), and some carry three views.

Design decisions worth not re-litigating:

- **Grid master is not copied into each folder.** It doesn't exist yet when Pass 1 runs (Pass 2's
  `gridline` subtask produces it). It lives at `_shared/gridmaster.json` and each manifest's
  `needs` points at it; the runner checks `needs` exist before firing a subtask. That's the
  dependency gate — no graph needed.
- **Title block is stripped from every crop, so `sheet_code`/`sheet_name` travel as text.** They
  are §2-required wrapper fields but sit in the right-edge title block, outside every view. Pass 0
  already read them; Pass 1 puts them in the manifest. Do not expect the model to find them in a
  crop.
- **Cropping never guesses.** If the detected cell count doesn't match the view count Pass 0
  reported, it sends the full page instead and writes the reason to `_shared/pass1_flags.json`.
- **Crops are padded ~2%** specifically so the grid markers (①②③ / ⒶⒷⒸ), which sit at the very
  edge of a view, don't get clipped — losing them kills span calculation for the whole sheet.
- Only 1-D splits (rows or columns) are supported. No 4-up grid case appeared in the data; a
  mixed `where` vocabulary is rejected rather than guessed.

`pass0_classify/output_example.json` is the contract Pass 1 expects — **Pass 0's prompt has to produce
exactly that shape**, including `subtask` as the final fine-grained label (not a 16-taxonomy
`pattern`), `where`, `also_gridline`, and `building`.

## Splitting `plan` into sub-subtasks (2026-08-21, Makham)

`plan` was one subtask; it is now split by **what structural element the sheet carries**, since
that's what decides which BOQ lines come out of it: `plan_footing`, `plan_column`, `plan_beam`,
`plan_slab` in Pass 2, and `plan_architectural` / `plan_electrical` / `plan_sanitary` in Pass 3.

**Floor level and building stay FIELDS, never subtasks.** The real files show heavy naming drift
that would tempt you to split further — `beam_plan` / `beam_plan_floor1` / `beam_plan_floor2` /
`beam_floor_plan` / `beam_plan_สุขา` are all the same extraction job. `floor_level` and `building`
already exist in the schema for exactly this; splitting them into separate subtasks would
multiply the subtask count per house for no gain.

### Three real problems found in the existing data while doing this split

Counted across all 11 houses in `json_แก้ไขแล้ว/`:

1. **`roof_frame_plan` is classified under two different patterns — and 8 of 11 houses are
   invisible to Constistant because of it.** All 12 roof-framing files are
   `discipline: "structural"` (they carry real roof beams), but 4 say `pattern: "plan"` and 8 say
   `pattern: "roof_plan"`. Constistant's `buildElements()` only reads `pattern === 'plan'`, so
   **the roof framing beams in those 8 houses never reach the BOQ at all.** This is a live data
   bug, not a t03 design question. The fix is to reclassify structural roof framing as `plan`
   (leaving `roof_plan` for the architectural ridge/eave sheet), which is what the CSV assumes:
   `plan_beam` owns roof framing, Pass 3's `roof_plan` owns the architectural one.

2. **`discipline` has two spellings of the same value** — `"architectural"` (182 files) and
   `"architecture"` (157 files). Nothing consumes `discipline` today so nothing is broken yet,
   but any future filter on it silently drops half the files. Needs one canonical spelling.

3. **Precast plank layout sheets are `pattern: "section"`** (18 files), despite being named
   `*_plank_layout*`. Probably correct as-is (they are detail sheets), but it means `plan_slab`
   should not expect to find them by filename — flagged so nobody "fixes" the pattern later
   without checking what actually reads it.

None of the three were introduced by t03; recording them here because the split is what surfaced
them, and #1 in particular should be fixed in the data before t03's output gets compared against
this ground truth.

## Corrections made to the first draft (record so they don't get re-litigated)

1. **`gridline` is the real pattern name, not "gridmaster".** "Gridmaster" is the *merged
   result* (what Constistant's `parseGridMaster()` produces from one or more `gridline` files),
   not a rawjson pattern. Renamed the subtask.

2. **`site_plan`/`side_profile` ARE valid grid sources — do not exclude them.** First draft of
   this design excluded them, reasoning that `side_profile` (elevation, not top-down) has no
   plan-view grid axis to read. **This was wrong** and Makham corrected it with real evidence: a
   spec-A-05 elevation sheet ("รูปด้าน 1"/"รูปด้าน 2") prints grid markers `①②③` and
   `Ⓓ Ⓒ Ⓑ Ⓐ` along the bottom edge with full dimension chains (`1.30/4.00/3.00/0.60/0.70` and
   `1.50/4.00/2.00/3.50/1.50`), exactly like a `plan` sheet's grid row. **Rule going forward:
   don't assume a pattern can't carry grid data because of its general description — check the
   actual sheet.** `plan`, `site_plan`, `side_profile`, `roof_plan` are all legitimate `gridline`
   sources when the sheet in question actually prints one; `gridline` itself (dedicated pages)
   stays primary when present.

3. **`roof_plan`'s own extraction subtask needs `gridmaster` as input too**, same as
   `plan`/`site_plan`/`side_profile` — missing from the first draft table, added for consistency
   (roof framing commonly references the same column grid).

## Schema change #2 — the grid master now records every printed dimension in the set

Makham's rule, 2026-08-21: **sweep every page, record every printed number, nothing gets dropped
for not fitting a category.** Three new arrays under `grid{}` (spec §4):

- **`z_levels[]`** — the vertical axis, previously missing entirely. `+3.75 ระดับหลังคาน`,
  `+0.60 ระดับพื้นชั้น 1`, `±0.00 ระดับอ้างอิง` are printed on every elevation and section in the
  set and there was **no field anywhere to put them** — `x_lines`/`y_lines` are plan axes only.
  `id` keeps the printed Thai label verbatim (no normalizing to `F1`).
- **`dimension_chains[]`** — every printed dimension row, now on `x`/`y`/**`z`**, including the
  redundant cumulative/total row (a mismatch between detail row and total row is the extraction
  error this catches).
- **`unassigned_dimensions[]`** — the catch-all. Any printed number that lands in neither of the
  above goes here with its printed label verbatim. This is what makes "nothing gets dropped"
  actually hold; a page with numbers and an empty array means an unread page, not a clean one.

Checklist items added to §0 so the format checker enforces it.

**Why the Z axis matters for t03 specifically:** elevations and sections are the *only* place
levels are printed, so a pipeline that treats `side_profile` as low-value (which the first draft
of `pass_design.csv` did) loses the entire vertical dimension of the building. This is the second
time that assumption bit — see correction #2 below.

## Schema change #1 (earlier same session)

Added a **Dimension chain** subsection to `primary_rawjson_schema.md` §4 (right after the
`pos_m` rule, before "Documenting genuine ambiguity"). Motivation: `x_lines[]`/`y_lines[]` only
record the *resolved* position of a named/dummy grid line, and a dummy grid only gets created
when a beam endpoint needs one (the beam-endpoint rule). Real sheets print more than that — e.g.
the `1.30` offset from a building edge to the first grid line in the A-05 elevation above — and
nothing sits on those points to trigger a dummy grid, so they were being silently dropped even
though they're real printed numbers.

New optional field: `grid.dimension_chains[]`, one entry per printed dimension row on a sheet
(a sheet can print more than one row — detail chain + a cumulative/total row above it). Each
segment is `{from, to, value_m}` where `from`/`to` are a grid `id` or the literal `"edge"`.
Purely additive — doesn't change `x_lines`/`y_lines`' existing contract, so nothing downstream
in Constistant needs to change to tolerate it.

**Open question, not yet decided:** should Pass 2's `gridline` subtask be a single AI call that
reads multiple images (gridline page + any plan/site_plan/side_profile/roof_plan fallback pages)
and emits the merged gridmaster directly? That's what `pass_design.csv` currently assumes
(`prompt=y`). Constistant's own `parseGridMaster()` today is pure JS math over already-extracted
per-file `gridline` JSON, not an AI call — t03 doing it as one AI call over multiple images would
be a different division of labor than what exists today. Confirm with Makham before building.

## Speed, separate from the pass split

Also fixed (unrelated to the pass redesign, found while investigating the beam-plan failure):
`run_house_batch.py`/`infer_t02.py` used pure greedy decoding with no repetition guard —
`repetition_penalty=1.15, no_repeat_ngram_size=8` added to both. **Not GPU-tested yet.**

Other speed levers discussed, not yet applied, roughly in order of effort:
1. Per-pattern pass split itself (this design) — shorter, more constrained generations.
2. Tune `max_new_tokens` per pattern instead of one flat 3000 for every page type.
3. 4-bit quantization at inference (`load_in_4bit=True`).
4. vLLM / TensorRT-LLM serving instead of raw `transformers.generate()` — biggest throughput win,
   biggest setup cost.
5. Grammar/JSON-constrained decoding (`outlines`/`xgrammar`) — the most robust fix for the
   looping failure mode specifically (structurally can't emit invalid/repeating JSON), heaviest
   to add.

## Still needed before t03 training (per Makham, planned tonight 19:00)

- Makham's full t03 design beyond the pass table — model choice, per-subtask prompt content,
  training data shape.
- Re-run the repetition-penalty fix against house 08's beam-plan page on a real GPU to confirm
  it actually closes valid JSON now (the fix is untested).
