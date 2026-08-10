# Archive — historical / superseded / reference docs, one place to read

Every `.md` in `No_touch_box/` that isn't part of the **live** workflow, summarized here so you
don't have to open 6 files to remember what's what.

Written 2026-08-04, at Makham's request ("รวมไฟล์ md ขยะๆ ในนี้รวมไว้ที่เดียว"). **Updated same
day**: the 8 files below (everything except the external paper) were physically moved into
[`wait_for_ทิ้ง/No_touch_box/`](../../wait_for_ทิ้ง/No_touch_box/) (repo root) — same staging
convention this project already used for the Label Studio material (see
`workmen's_diary/2026-08-02.md` round 6). Recoverable from git history regardless; not deleted
for real yet. Every link below now points at the new location.

## Not touched — these are live, don't confuse them with the pile below

`CLAUDE.md` · `README.md` (root) · `SETUP.md` · `docs/rule_of_tune.md` ·
`docs/raw_json_data_log.md` · `Prompt/README.md` + `Prompt/stage-*/prompt.md`

## Index

| file (now in `wait_for_ทิ้ง/No_touch_box/`) | status | what it is |
|---|---|---|
| [QUICKSTART.md](../../wait_for_ทิ้ง/No_touch_box/QUICKSTART.md) | 🔴 **DEAD** | Guide for a pipeline generation that no longer runs |
| [vast-template/](../../wait_for_ทิ้ง/No_touch_box/vast-template/) | 🔴 **DEAD** | GPU template from before any real tuning happened |
| [raw/README.md](../../wait_for_ทิ้ง/No_touch_box/raw/README.md) | 🟡 stale | Points at the same dead pipeline as QUICKSTART |
| [docs/AGENTS.md](AGENTS.md) | ⚪ keep, not junk | 6-line stub — some tools look for this filename by convention, **not moved** |
| [merged_pattern_gen4_20260706.md](../../wait_for_ทิ้ง/No_touch_box/docs/merged_pattern_gen4_20260706.md) | 📜 historical | Gen 2 × Gen 3 schema merge record |
| [20260708draft of prime rawjson.md](../../wait_for_ทิ้ง/No_touch_box/docs/20260708draft%20of%20prime%20rawjson.md) | 📜 historical | Direct ancestor of the live spec — still linked from `primary_rawjson_schema.md`'s own header |
| [Makham's patter of rawjson20260705.md](../../wait_for_ทิ้ง/No_touch_box/docs/Makham's%20patter%20of%20rawjson20260705.md) | 📜 historical | Origin doc — dummy-grid + spec-join were designed here first |
| pilot docs ([`raw/image/.../claude_output_01/`](../../wait_for_ทิ้ง/No_touch_box/raw/image/บ้าน_เล็ก_1ชั้น_01/claude_output_01/)) | 📜 historical draft | First Claude-vs-Qwen comparison, never reviewed |
| [docs/FLOORPLANVLM.md](FLOORPLANVLM.md) | 📖 external reference | An academic paper (not project-authored), kept for citation, **not moved** — Makham: "เก็บดีๆ" |

**The schema lineage, in order:** `Makham's patter...` (Gen 3, design only) → `merged_pattern_gen4...`
(Gen 2×3 merged) → `20260708draft...` (13 patterns, current rebar structure) → **compiled into
`primary_rawjson_schema.md`** in the `Constistant` repo on 2026-07-10, which is the only one of
these five still authoritative. Reading the chain bottom-to-top from `primary_rawjson_schema.md`
is *why* a rule exists; nothing in the chain overrides it.

---

## 🔴 QUICKSTART.md — dead

Walks through `python pdf-processor.py` → `node qwen-processor.js` → `review.html` → drop the
corrected JSON into `annotated/`. **This is the older pipeline generation** — the 2026-08-02 diary
(round 8, `workmen's_diary/2026-08-02.md`) confirms `pdf-processor.py`/`qwen-processor.js`/
`review.html`/`manifest.json` were superseded by `run_pipeline.py` + `build_document_map.py`, and
kept only because two scripts still read `manifest.json` without owning it. The `annotated/` /
review-and-correct step it describes is also the pre-Label-Studio flow — Label Studio itself was
cancelled 2026-08-02 and its tooling deleted. Following this guide today runs real scripts against
a generation nothing else in the repo still treats as ground truth.

**Current equivalent:** `rawjson_ยังไม่ได้แก้ไขโดนคน/README.md` (`op1`/`op2`/`op3` commands).

## 🔴 vast-template/ — dead

`README.md` + `onstart.sh`, dated 2026-07-02. Picks an RTX 3090 24GB instance, defaults to
`Qwen3-VL-8B-Instruct`, and defers the real model choice to "King's sign-off" on
"`AGENTS.md` (main Constistant repo) section 16" — a decision-making process and a model
(Qwen2-VL-7B vs Qwen3-VL-8B) that don't match what actually happened. The real tuning rounds
(t01/t02, see `tune_ai/`) were run by Makham + Claude directly, landed on `Qwen3.6-35B-A3B`
(t01, the one that worked) and `Qwen3-VL-30B-A3B` (t02, MoE-merge failed), on a rented **RTX PRO
6000 96GB**, not a 3090. Nothing here reflects the actual pipeline.

**Current equivalent:** `tune_ai/t01/t01_workflow.md` (the proven Phase 0-11 process); `t03/` when
it starts.

## 🟡 raw/README.md — stale

Short (25 lines): tells a collaborator to drop PDFs in `raw/` and run `python pdf-processor.py`.
Same dead pipeline as QUICKSTART.md above, just the short version.

## ⚪ docs/AGENTS.md — not junk, leave it

Six lines, entirely a pointer: *"ดู CLAUDE.md ... ชื่อไฟล์ต่างกันเพราะ tool ต่างกันมองหาคนละชื่อ"*.
Some agent tooling looks for `AGENTS.md` specifically by filename convention — this stub exists so
that lookup doesn't come up empty. Nothing to consolidate; it has no content of its own.

## 📜 docs/merged_pattern_gen4_20260706.md — historical

2026-07-06. Merges two schema lines that evolved independently — Claude's Gen 2 (`views[]`
inventory-first, code-computed span, atomic beam segments) and Makham's Gen 3.1-3.3 (dummy grid +
prime notation, per-house grid master file, spec join by `element_id`). Explicit merge rule: never
drop a feature from either side without saying what was chosen and why. Result: 10-pattern
taxonomy, `views[]` wins over Makham's no-inventory approach, `grid_ref` format keeps Gen 2's
dashed style (`"A-1/A-2"`) over Makham's packed style (`"{D1D2,4}"`) since it matches what
`run_pipeline.py` already expected. Superseded the same week by the 07-08 draft below.

## 📜 docs/20260708draft of prime rawjson.md — historical, direct ancestor of the live spec

2026-07-08, copied whole from the Gen 4 merge above and revised per 3 of Makham's instructions:
dummy-grid ordering + origin rules, pattern taxonomy cleanup (13 types, `site_profile` renamed to
`side_profile`, added `title`/`symbol`/`roof_plan`), and made `source_image` mandatory on every
file. 12 sections cover: taxonomy, multi-view, grid (incl. the dummy-grid-master-file convention),
beam segment splitting, the rebar restructure to nested `top`/`bottom` objects, `additional_bars`,
`Ø`=RB always, spec join, multi-level `level` field, `precast_plank_detail`, footing-as-array,
slab markers, BOQ dual-sheet handling. **`primary_rawjson_schema.md` in the `Constistant` repo was
compiled from this file on 2026-07-10** — read that one for what's actually enforced today; this
is the "why" behind it, not a second source of truth.

## 📜 docs/Makham's patter of rawjson20260705.md — historical, the origin document

2026-07-05/06, 439 lines. Where the ideas that later became core spec rules were first designed:
- **Generation 1** — the flat pattern that actually shipped in `qwen-output/` at the time
- **Generation 2** — Claude's `views[]` inventory-first fix for multi-view pages
- **Generation 3 / 3.1 / 3.2 / 3.3** — Makham's pattern: `grid_ref` rules keyed by `element_type`,
  **dummy grid + prime notation** (`1'`, `A''`) and the per-house `หน้า00_gridline.json` master
  file, and **spec join** (a `plan` element's position joined to a `section`/`schedule` element's
  spec via shared `element_id`) — both still load-bearing rules in the live spec today
- A real test run (บ้าน_เล็ก_1ชั้น_01, pages 02/18/19/20/21/38) that found the schema's biggest
  early gap: a flat 4-field element had nowhere to put a real `section`/`schedule` spec at all

If you ever need to know *why* dummy-grid-prime-notation or spec-join work the way they do, this
is the doc that has the original reasoning — everything downstream just inherited the decision.

## 📜 Pilot comparison docs — historical draft, never reviewed

`raw/image/บ้าน_เล็ก_1ชั้น_01/claude_output_01/_inventory_pass_pilot.md` (94 lines) and
`_pilot_comparison_summary.md` (38 lines), both 2026-07-02. The first real Claude-vs-Qwen
side-by-side on 4 real pages (19 plan, 21 section, 24 section detail, 40 BOQ). Explicitly flagged
in its own header: *"draft ที่ยังไม่ผ่านคนตรวจ — ห้ามใช้เป็น ground truth โดยตรง"*. What it found,
condensed:
- Qwen missed 3 real footings entirely on page 19 (recall gap — the same failure mode t01/t02
  measured months later as `element recall`)
- **`main_bar_type` misread systematically DB→RB across an entire page**, while the *same symbol*
  used for stirrups on the *same page* was read correctly — this exact finding is now lesson #6 in
  `No_touch_box/CLAUDE.md`
- A flat beam/column schema didn't fit a slab-detail page at all — early evidence for the spec
  restructuring that followed in the two docs above

## 📖 docs/FLOORPLANVLM.md — external reference, not project content

A published paper ("FLOORPLANVLM: A Vision-Language Model for Floorplan Vectorization", Beike
team), 364 lines. Not authored by anyone on this project — kept as background reading on VLM
floorplan extraction generally. Left where it is; not summarized here since it isn't part of this
project's own history.

---

## Status as of 2026-08-04: staged, not deleted

All 8 files above (everything except `docs/AGENTS.md` and the external `FLOORPLANVLM.md` paper)
now live under `wait_for_ทิ้ง/No_touch_box/` (repo root), mirroring their original relative paths.
Every link in `No_touch_box/CLAUDE.md`, `primary_rawjson_schema.md` (in `rawjson_ยังไม่ได้แก้ไขโดนคน/`),
and `rawjson_ยังไม่ได้แก้ไขโดนคน/README.md` that pointed at the old location was updated to the new
one in the same session — see `primary_rawjson_schema_edit_log.md` for the schema-doc edit
specifically (rule 7 applies there, not to this file).

**Not deleted for real yet** — same staging discipline this project used for the Label Studio
material (`workmen's_diary/2026-08-02.md` round 6, later actually deleted in round 8). Recoverable
from git history regardless either way. Retroactive archival notes were added to the
`workmen's_diary/` entry for each file's own creation/content date (2026-07-01, -02, -05, -06,
-08), not just to today's — see those files if you want the full record of which day each doc
came from.
