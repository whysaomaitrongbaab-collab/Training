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

This command does **not** skip any `rule_of_tune.md` protections — the output in `0N<house_name>/*.json` is ground-truth raw data the moment it's saved, protected the same as everything else in this folder.

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
