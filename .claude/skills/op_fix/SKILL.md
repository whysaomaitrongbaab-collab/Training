---
name: op_fix
description: Retrofit one already-finished house's grid master to spec §4 as it stands since 2026-09-27 — the full dimension sweep (`z_levels[]` / `dimension_chains[]` / `unassigned_dimensions[]`) plus rule 4 (every printed x/y dimension tick is a line — reuse the existing line, otherwise a new dummy — even when nothing uses it). Triggers on "op_fix <house>" / "opfix <house>" / "op_fix 01-05" (a range of `json_แก้ไขแล้ว/` folder numbers). Works directly in `json_แก้ไขแล้ว/` (Makham's standing authorization, 2026-09-29) and decides every judgement call itself, att1235-style — never stops to ask. The mechanical half (dummy naming, prime re-sequencing, house-wide rename of grid refs, chain arithmetic checks) is `tools/gridfix.py`, never done by hand. This file is the source of truth for op_fix; the READMEs only point here.
---

# op_fix — bring an old house up to §4 rule 4

Argument: a house (`บ้าน_เล็ก_1ชั้น_01`) or a range of `json_แก้ไขแล้ว/` folder numbers (`01-05`).
All paths are relative to the **Training repo root**.

## Why this exists

Rule 4 (spec §4, added 2026-09-27, Makham: *"gridmaster จดจำระยะทุก ๆ ระยะ ในทุกหน้า แม้ระยะเหล่านั้นจะไม่ได้ใช้ก็ตาม"*)
came after most houses were finished. So every older master is wrong in one of two ways:

- **never swept** — no `dimension_chains[]` / `unassigned_dimensions[]` at all (houses 01–19 of
  `json_แก้ไขแล้ว/` on 2026-09-29: 20 master files);
- **swept, but ticks left as `"edge"`** — the chain was transcribed, but a tick that hangs off a known
  line was written `"edge"` instead of becoming a dummy line (houses 20–40: 25 chains in 12 houses —
  all fixed by the first run, 2026-09-29, via `chain_fixes`; a swept house can still hide missed rows,
  so the 40-house pass re-sweeps them too).

`check_format.py` reports both as NOTEs. op_fix is how they get cleared.

## Standing order — decide, don't ask

- **Target tree: `json_แก้ไขแล้ว/` only** (the 40-house set training is built from). Makham authorized
  editing it directly (2026-09-29, att1235). **Never touch `rawjson_ยังไม่ได้แก้ไขโดนคน/`** — it is
  Rule-1 protected raw ground truth; syncing a fix back there is a separate decision.
- Authority is `rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`
  §4 — read "Dummy grid", "The grid master records EVERY printed dimension" (arrays 1–4) and the
  beam-endpoint rule **every run**, don't work from memory.
- Every judgement call goes into the master's `warnings[]`: what was ambiguous, what was taken, why.
- The only thing never allowed: inventing a value that is printed on no sheet.
- **Older Makham rulings in the master** (`CORRECTED/CLOSED/RULED BY MAKHAM …`) are read before touching
  anything. Rule 4 is his own later rule and wins where they collide (typical case: a printed roofline or
  eave tick he once parked in `unassigned_dimensions`) — but every such collision is named in the README
  log entry as "ขัดกับคำตัดสินเดิม" so he can reverse it. A value he ruled (a centreline `pos_m`) is never
  moved; at most its line's *name* shifts when primes are re-sequenced.
- Scope is the grid master. The house's other files change **only** when a dummy rename forces their
  grid refs to follow (gridfix does that, and proves it).

## Steps

1. **Read** spec §4, the house's master (`<house>_หน้า00*gridline*.json` — a house can have more than
   one, e.g. a separate toilet block), and `tools/gridfix.py --help`.
2. **Pick the pages.** Every page that prints a dimension row along the building grid: site plan, every
   `*_plan` (footing, beam, roof frame, etc_plan floor plans), `roof_plan`, every `side_profile`, and the
   building `section`s (รูปตัด). Use each page JSON's `pattern`/`sheet_name` to find them fast — but **read
   the image**; the page JSONs don't carry the printed chains. Member-detail sections (a beam/column/
   footing cross-section) print only element-internal sizes → not axis ticks (§4 rule 4) → list them as
   skipped with that reason. Structural sheets first (they own grid geometry, op01 precedence), then
   elevations (the only source of z), then architectural plans.
3. **Transcribe each page image** (Read tool on `image/<house>/<file>.png`):
   - every printed x/y dimension row → one `dimension_chains[]` entry **per printed row per sheet**
     (the detail row and the total row are separate entries): `{axis, source_image, segments:[{from,to,value_m}]}`;
   - a chain end that sits on a known line → that line's `id` (compare `pos_m` to the millimetre);
   - a chain end that sits on **no** known line → the placeholder **`"@<pos_m>"`** where
     `pos_m` = the anchor line ± the printed segments between them (`"@-1.3"`, `"@8.3"`). gridfix turns
     every placeholder into a named dummy line. Count points, not numbers (§4 rule 4 count example);
   - `"edge"` stays legal for one case only: a chain that touches no known line anywhere;
   - z rows → `axis:"z"`, ends are `z_levels[]` ids. A level not yet in the master goes into
     `z_levels_add` (label verbatim; `type:"dummy"` and `id` = the printed level text when no label is printed);
   - every other printed number → `unassigned_dimensions[]` (`value_m`, verbatim `label`, `source_image`, `note`).
4. **Write the staging file** `wait_for_ทิ้ง/opfix_staging/<NN><house>__<master file stem>.json` —
   **never** inside a house folder (every `*.json` there becomes training data):

   ```json
   {
     "house_dir": "json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01",
     "master": "บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json",
     "pages_swept": ["..._หน้า19.png"],
     "pages_skipped": [{"page": "..._หน้า40.png", "why": "member detail sections only"}],
     "z_levels_add": [],
     "dimension_chains": [],
     "unassigned_dimensions": [],
     "chain_fixes": [{"index": 3, "segments": [{"from": "@-1.0", "to": "1", "value_m": 1.0}]}],
     "warnings": []
   }
   ```

   `chain_fixes` replaces the segments of an **existing** chain (by its index in the master) — that's how
   an old `"edge"` becomes a placeholder without re-transcribing the page.
5. **Dry-run:** `python tools/gridfix.py wait_for_ทิ้ง/opfix_staging/<file>.json` — prints the new dummies,
   every rename, and **every segment whose printed value disagrees with the line positions**. A mismatch is
   a misread digit or a wrong anchor: go back to the image and fix the staging. Don't apply over a mismatch
   you can't explain; if one is genuinely printed that way (the drawing itself doesn't close), keep it and
   say so in `warnings`.
6. **Apply:** same command with `--apply`. Then `python tools/check_format.py json_แก้ไขแล้ว/<NN><house>` —
   every check PASS, and the house's "not dimension-swept"/"edge" NOTEs gone.
7. **Log:** one entry under "บันทึกการแก้ไข" in `json_แก้ไขแล้ว/README.md` (pages swept/skipped, lines added,
   renames, open doubts) and one terse line in the day's workmen's diary.

**Out of time?** Don't apply a half sweep — an applied sweep claims the set was read. Leave the staging
with `pages_swept` as far as you got; the next run continues from it.

**Several houses at once** (one sub-agent per house, the parent applies): give every agent its own scratch
folder from the start and a crop script with the house path hard-coded. On 2026-09-29 five agents shared one
`crop.py` and overwrote each other's house path; every reading had to be re-verified. Agents write staging
only — the parent runs `--apply`, the checks, and the log, one house at a time.

**What the sweep does to training:** a swept master grows 6–13× (house 05: 10k → 122k characters). The old
"whole master as one gridline label" example no longer fits `MAX_LENGTH`; the dataset builder has to change
before the next round trains on swept houses.

## What gridfix.py does (so nobody does it by hand)

- **Naming** (spec § Dummy grid): every run leaves the whole axis canonical — each dummy primed off the main
  grid to its left (x) / above it (y), before the origin in the first main grid's sequence, primes 1, 2, 3… in
  reading order. That includes labels Makham gave or confirmed (`confidence_score: 1`) and labels filed under
  the wrong base (Makham, 2026-09-29: "เรียงให้เลย"). `1'`(1.2) becomes `1''` when a new line at -1.0 takes `1'`.
  A staging with no chains is a pure re-sequence run.
- **Printed grid names never move:** when a rule name would equal a grid name printed on the drawing (house 12's
  `ง'`/`ค'` bubbles are named lines), that base keeps its names and a warning says so.
- **`merge_lines`** (`[{"axis": "x", "id": "2'", "into_pos": 4.7}]`): removes a wrong line and moves every ref
  that used it to the line at `into_pos` — the only case where a ref is allowed to change position
  (house 03's `2'`, Makham 2026-09-29).
- **Absent stays absent:** a run never creates an empty `dimension_chains`/`z_levels` on an unswept master —
  empty would claim "swept, found nothing".
- **Rename propagation:** every rename is applied to every grid ref in every file of the house
  (`grid_ref`, `grid_ref_start`, `grid_ref_end`, `grid_refs`, and the per-page `grid_columns`/`grid_rows`
  lists; point, range and prose-ish forms like `~bay 1''-2`) and to chain ends — then it re-resolves every
  ref before/after and aborts unless each one still points at the same position. Any *other* field whose
  value equals a renamed id stops the apply ("CHECK BY HAND") until someone decides what it is. `element_id`
  marks like `B1'` are printed member names, not grid ids — never renamed. A quoted label inside a prose-ish
  ref (`labels '1'/'2'`, `box '3 +0.50 3'`) and an English apostrophe (`see view1's warnings`) are not primes
  and are left alone (houses 02, 03, 13 — 2026-09-29).
- **After every apply, read the prose-ish refs by eye** — the independent check can't parse them, so it lists
  them for a human; the one real slip of the first run was hiding there.
- **Writes keep the file's own format** (number literals like `4.00`, one-line objects, CRLF) and re-type
  only the values that changed, so `git diff` shows the fix and nothing else. Verify with `git diff --numstat`.
- Prose inside old `warnings[]` is **not** rewritten; the master gets one warning listing the renames.
