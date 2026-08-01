# raw_json_ตัวที่ใช้งานจริง

This folder holds **actual finished raw JSON extractions** (not test rounds) — one set per house, plus the spec file used to prompt the extraction.

> ⚠️ **Read [`training-data/docs/rule_of_tune.md`](../training-data/docs/rule_of_tune.md) before touching anything in here.** Every `0N<house>/*.json` file in this folder is protected ground-truth data under that rule — no exceptions. It covers what counts as raw JSON, when you must warn before editing, and the required audit-log entry for any real change.

## Folder structure + naming convention

```
raw_json_ตัวที่ใช้งานจริง/
├── 00file_for_making_rawjson_from_claude/   ← spec/prompt reference (not house data)
│   └── primary_rawjson_schema.md
├── 01บ้าน_เล็ก_1ชั้น_01/                     ← house #1 extraction output (101 files)
├── 02<house #2 name>/                        ← next house (doesn't exist yet — add as needed)
├── 03<house #3 name>/
└── ...
```

- **`00`** = always fixed, holds spec/reference docs only — never house data
- **`01`, `02`, `03`, ...** = one folder per house, in the order they were done. Folder name = 2-digit number glued directly onto the house name (matching the source image filenames in `image/<house>/`)

## Quick command: `op1 <house_name>`

If the user (Makham) types **`op1 <house_name>`** (e.g. `op1 บ้านเอกมัย`), treat it as shorthand for running the *entire* workflow below in one go, without asking them to re-explain each step:

1. Read [`00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`](00file_for_making_rawjson_from_claude/primary_rawjson_schema.md) in full (every time — don't rely on memory of a past session).
2. Determine the next sequence number `N` (2 digits) by checking the highest existing `0N<house>/` folder in this directory and incrementing — don't ask the user to supply it.
3. Actually read every page image in `image/<house_name>/*.png` (never guess, never copy another house's data) and extract per the spec — grid master first (`<house>_หน้า00_gridline.json`), then page-by-page/view-by-view. This is real vision extraction work done in-session; there is no script that does this part automatically.
4. Save every file into the new `0N<house_name>/` folder.
5. Run `node label-studio-tasks-makham.js <house_name>` (from `training-data/label_studio_stuff/`) to generate the 3 Label Studio task files, now namespaced per house (see Step 2 below) so this is always safe to re-run for any house without overwriting another house's output.
6. Report back: files created, page count, any low-confidence flags or open questions (e.g. duplicate `element_id` across sections) — then remind the user that the 3 task files still need to be **manually uploaded** into their matching Label Studio projects (this step is never automatic).
7. Add a row to `training-data/docs/raw_json_data_log.md` per `rule_of_tune.md` rule #3 — every new house extraction is a real-data event that must be logged.

### `op1` is a standing order — decide, don't ask

**`op1` means "produce the finished extraction, no matter what." Claude must make every judgement call itself and keep going to the end. Do not stop mid-run to ask the user which reading is right.**

- **The authority is [`00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`](00file_for_making_rawjson_from_claude/primary_rawjson_schema.md).** When two sheets disagree, when a field has no obvious home, when a new pattern appears — resolve it against that spec and the precedent already set by houses `01`–`05`, then move on.
- **Precedence when sheets conflict** (extends spec §7's "section wins over schedule"):
  1. **Grid geometry** → the STRUCTURAL footing/column plans win (S-sheets). The grid master has always been derived from them (spec §4, and every existing house's `view_title`). An architectural site plan or a sheet that self-declares "เพื่อประมาณราคา/ตัวอย่าง" never overrides them.
  2. **Member spec** → the detail/section sheet wins over the plan; `section` wins over `schedule` (spec §7).
  3. **More sheets agreeing beats fewer.** Count them, and say so in the warning.
- **Every decision must be written down where the data lives** — a `warnings[]` entry that states what conflicted, which reading was taken, and why. Lower `confidence_score` and add a flag when the losing reading is genuinely plausible. The user reviews decisions after the fact; they do not arbitrate during the run.
- **Never leave a field blank because a choice was hard.** Blank is only for "the drawing genuinely does not say" (e.g. an undimensioned gap, per spec §4's rule against guessing a `pos_m`) — never for "two sheets said different things."
- Asking mid-run is only correct if continuing would require **inventing data that appears on no sheet at all**.

This command does **not** skip any `rule_of_tune.md` protections — the output in `0N<house_name>/*.json` is ground-truth raw data the moment it's saved, protected the same as everything else in this folder.

## Quick command: `op2 <house_name>` — staged run with automatic model switching

**`op2` produces exactly the same finished output as `op1`, under exactly the same standing order** ("produce the finished extraction, no matter what — decide, don't ask"). The only difference is that the work is split into 4 stages and **each stage runs on a different model**, so the expensive model is spent only where it earns its keep.

Everything in the `op1` standing-order section above — the authority of `primary_rawjson_schema.md`, the conflict-precedence list, "every decision written into `warnings[]`", "never leave a field blank because a choice was hard" — applies unchanged to every stage of `op2`. Do not re-derive those rules; they are one ruleset, not two.

### Why stage it at all — the measured split

From house 07 (`บ้าน_ใหญ่_2ชั้น_01`), after 48 of 108 pages:

| `pattern` | files | needs real geometric reasoning? |
|---|---:|---|
| `gridline` | 1 | ✅ hardest page in the set |
| `plan` | 9 | ✅ hard |
| `section` | 17 | ❌ transcription |
| `detail` | 8 | ❌ |
| `elevation` | 4 | ❌ |
| `index` / `notes` / `schedule` | 9 | ❌ |

**~20% of files carry ~60% of the difficulty**, and they are all `gridline` + `plan`. The BOQ block alone (34 pages in house 07) is pure table transcription with nothing to decide.

### The invariant that fixes the stage order

**Grid before plan. Plan before everything else.** This is a data dependency, not a preference:

```python
XP = {"1": 0.0, "2": 4.00, "3": 9.00, "4": 13.00}   # from the grid master
"span_length_m": round(XP[b] - XP[a], 2)            # every plan element
```

Move one grid line and **every `span_length_m` in every `plan` file is wrong**. This already happened once for real: on house 06 a drawing break line was misread as a building expansion joint, the grid master had to be reversed from 10 lines to 11, and three finished plan files had to be re-derived behind it. A staging order that reads plans first and fixes the grid afterwards guarantees repeating that.

### The 4 stages

| Stage | Model | Does | Reads images? |
|---|---|---|---|
| **0** | `sonnet` | สารบัญ + page offset + build `_stage0_manifest.json`: which PNG is which sheet, which are `pattern: plan`, which sheet carries the full grid dimension chain, how many buildings (§11a) | yes, a few pages |
| **1** | `fable` | Grid master(s) + **every** `pattern: plan` file. One coupled unit. | yes, heavily zoomed |
| **2** | `opus` / `sonnet` | Everything else — section, detail, elevation, schedule, notes, index, BOQ. Grid master is **read-only**. Parallelisable by discipline. | yes |
| **3** | `opus` | Cross-sheet contradictions, from the JSON only — no images. Rewrites `warnings[]`, clears every `phase_note`. | no |

Switch models with the `Agent` tool's `model` parameter (`sonnet` / `opus` / `fable` / `haiku`) — one subagent per stage, launched in order. Stage 2 may launch several agents at once (e.g. architectural / structural-details / SN-EE-M / BOQ) since each writes only its own PNGs.

### Handoff contract between stages

- **Stage 0 → 1.** Output is `0N<house>/_stage0_manifest.json`. The leading `_` matters: `label-studio-tasks-makham.js` filters with `f.startsWith(house)`, so a file named this way is never picked up as a training task. It is orchestration metadata, not house data.
- **Stage 1 → 2.** The grid master must be complete: every `x_lines`/`y_lines` entry carries `pos_m` (or an explicit `null` for a dummy grid whose position the drawing genuinely does not give), and **both dimension chains must be shown to close against the printed overall dimension** in a `warnings[]` entry. Stage 1 must also state explicitly whether the set uses **drawing break lines** — checking for them is mandatory, not optional (house-06 lesson: zooming to 6× was not enough; the zigzag symbol sits mid-line and needs ~4.5× on a tight crop of the middle of the double line).
- **Stage 2 → 3.** Stage 2 **never edits the grid master or any `plan` file.** If it finds evidence bearing on the grid — e.g. house 07's A-07 architectural roof plan independently confirming the S-06 ridge position that had to be traced from line weights — it writes a `phase_note` and moves on.
- **Stage 3.** Folds every `phase_note` into `warnings[]`, then deletes the field. Per spec §2a, a finished file has no `phase_note`.

### Escalation rule

If Stage 2 or 3 concludes the **grid itself** is wrong, **re-run Stage 1 for that house** — do not hand-patch the grid master and do not patch plan files individually. A grid change invalidates every plan file downstream of it, and patching by hand is how the two files silently drift out of agreement.

### Stage 3 contradiction checklist

Grounded in what house 07 actually turned up. Run all six:

1. **Same mark, two values.** `F16` on the S-02 plan vs `F18` in the S-01 index and title block — three independent marks on the drawing (title, `16-16` section arrows, "จำนวน 16 ต้น") beat one in the title block.
2. **Same member name, different section on different sheets.** `จันทันเหล็ก C-150x75` is `x9x12.5` (24 kg/m) on S-04 but `x25x3.2` (8.27 kg/m) on S-05 — three times the thickness under one name. Anything keying a section off the member *name* alone will get it wrong; key off the sheet too.
3. **A deferral whose target must be checked.** S-14 replaced every stair dimension with "ระยะลูกนอน/ลูกตั้งตามแบบสถาปัตยกรรม" — confirm A-16 actually carries them (it does: 10 ลูกตั้ง @0.15, 9 ลูกนอน @0.275, and 20 × 0.15 = 3.00 m closes exactly against the elevations' floor-to-floor).
4. **The same minimum stated twice, differently.** Ceiling insulation is "ไม่น้อยกว่า 2\"" on A-01 and "ไม่น้อยกว่า 3\"" on A-02. Both are minima so 3″ satisfies both, but neither sheet supersedes the other — record both as printed and flag.
5. **Dangling callouts.** Every `detail_callout` must resolve. House 07's six `DETAIL 1/2/3` callouts on S-04 named no target sheet at all until S-15 turned up.
6. **Mark used but not scheduled, or scheduled but not used.** Cross the plan marks against the schedules both ways — this is what showed that doors run 1–5 and windows 1–6, so any circled `6` on a plan is necessarily a window.

### When to use `op1` instead

Use plain `op1` when a single model is doing the whole house anyway, or when the remaining pages are all transcription. **Do not switch mid-house once the grid master and `plan` files are already finished** — the expensive stage is already paid for; spend the premium quota on the *next* house from Stage 1.

## Step 1 — Extract a new house into raw JSON

1. Read [`00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`](00file_for_making_rawjson_from_claude/primary_rawjson_schema.md) in full before starting — it's the only spec needed (13 patterns, grid/dummy-grid rules, `main_bar` top/bottom shape, spec join, etc). The full original with history/rationale lives at `training-data/docs/20260708draft of prime rawjson.md` if you need more context.
2. Actually read every page image of that house (`image/<house>/*.png`) — **never guess, never copy from another house** even if it looks similar (see `rule_of_tune.md`).
3. Build the grid master before anything else: `<house>_หน้า00_gridline.json` (all main grids + dummy grids for the whole house).
4. Extract page by page / view by view per the spec — a page with multiple views gets a separate file per view (`_view1_...`, `_view2_...`).
5. Every file needs `source_image` (full path of the source image) except the `หน้า00` file, which uses `source_pages` instead.
6. Save everything into a new folder `0N<house_name>/` (next number after the last house).

## Step 2 — Prepare data for Label Studio (3 files: element / material_list / single)

Label Studio needs 3 separate task JSON files by data shape (see `training-data/label_studio_stuff/` for why) — one generator script produces all 3:

```bash
cd training-data/label_studio_stuff
node label-studio-tasks-makham.js <house>
# e.g.: node label-studio-tasks-makham.js บ้าน_เล็ก_1ชั้น_01
```

This auto-finds `raw_json_ตัวที่ใช้งานจริง/<NN><house>/` — no need to pass a folder number. (Pass an old `mk_test` round name, e.g. `t2`, as a second argument to force reading that instead.)

Output is written into per-project subfolders automatically, filenames namespaced by house so running this for a new house never overwrites an earlier house's files:
```
label_studio_stuff/element/label-studio-tasks-makham-<house>-elements.json
label_studio_stuff/material_list/label-studio-tasks-makham-<house>-material_list.json
label_studio_stuff/single/label-studio-tasks-makham-<house>-single.json
```

Then **Upload Files** each one into its matching Label Studio project (Elements / Material List / Single — separate projects, never combined; see `label_studio_stuff/` for why, re: Label Studio's `visibleWhen` bug). Always finish **Labeling Setup → Code** (paste the matching `.xml`) before **Data Import**.

## Full workflow summary

```
1. Read the spec (00file_for_making_rawjson_from_claude/)
        ↓
2. Extract from real images → save into 0N<house_name>/
        ↓
3. Run label-studio-tasks-makham.js → get 3 task JSON files
        ↓
4. Import into 3 Label Studio projects (Elements / Material List / Single)
        ↓
5. Review/correct in Label Studio → export back as ground truth for fine-tuning
```
