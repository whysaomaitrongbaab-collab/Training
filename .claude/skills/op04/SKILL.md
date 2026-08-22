---
name: op04
description: Extract one house into raw JSON covering ONLY the Pass 2 subtasks — the pages Constistant actually consumes — instead of all ~107 pages. Triggers on "op04 <house_name>" or "op4 <house_name>" (Makham's shorthand), e.g. "op04 บ้านเอกมัย". Same standing order and same authority as op01 ("produce the finished extraction, decide don't ask"); the only difference is scope. Cuts ~107 pages/house to ~38 (about 65% less work per house) so the dataset can grow in houses rather than in pages — the fix for the measured problem that t02 saw only ~13 beam-plan examples and scored 11% element recall on them. Writes a `_scope.json` marker so a partial house can never be mistaken for a complete one. Source of truth is `rawjson_ยังไม่ได้แก้ไขโดนคน/README.md`'s `op4` section — keep this file in sync with it whenever that section changes.
---

# op04 — extract one house, Pass 2 subtasks only

Argument: `<house_name>` (e.g. `บ้านเอกมัย`). All paths are relative to the **Training repo root**.

`op04` is `op01` with one change: **scope**. Everything else — the authority, the conflict
precedence, "decide don't ask", `warnings[]` discipline, the output folder, `check_format.py`,
the log row — is `op01`'s, unchanged. Read `.claude/skills/op01/SKILL.md` and follow it; this
file only states where `op04` differs.

## Why this exists — the measured reason, not a preference

Counted 2026-08-22 across the 11 annotated houses (`tune_ai/t03/dataset_sizing.md`):

| what t02 saw during training | pages | result |
|---|---|---|
| door/window schedule | ~24 | reads it at **86%** |
| material_list | ~158 | fine |
| **beam plans** | **~13** | **11% element recall** |

The failure tracks example count, not page difficulty. Beam plans are simultaneously the
hardest page type (≈25 elements each, every one needing two correct grid endpoints) and the
one the model saw least of.

Meanwhile **`material_list` alone accounts for 435 of the 1,180 annotated files — 37% of every
hour spent annotating so far — and yields `elements: []`.** It is a table of quantities; it
carries no member positions.

So the dataset does not need more pages per house. It needs **more houses**, and the way to
afford them is to stop annotating the pages nothing reads.

## Scope — what op04 extracts

Do these in order. The order is a dependency chain, not a preference.

| # | subtask | pages/house | notes |
|---|---|---|---|
| 1 | **`gridline`** | ~1 | **First, always.** Every span on every later sheet is computed from it. A wrong `pos_m` here is a wrong concrete volume and a wrong steel weight everywhere downstream, with nothing able to detect it. |
| 2 | `plan_footing` | ~1.8 | footings, piles, pile caps, pedestals + the columns marked with them |
| 3 | `plan_column` | ~0.2 | see the warning below — usually there is no such sheet |
| 4 | **`plan_beam`** | ~3.2 | **the point of this whole skill** — ground beams, floor beams, ring beams, roof framing |
| 5 | `plan_slab` | ~1 | floor slabs, precast plank fields |
| 6 | `section` | ~20 | the rebar spec for each mark; joins to the plans by `element_id` |
| 7 | `schedule` | ~6 | door/window and column schedules |
| 8 | `notes` | ~5 | project-wide concrete/steel spec (§4a) |
| 9 | `soil_boring_log` | 0-1 | only if the house has one; most do not |

**≈38 pages/house** versus ~107 for a full `op01`.

### Deliberately skipped

- **`material_list`** — the 435-file finding above. Skip by default. If Makham explicitly asks
  for it (`op04 <house> +material_list`), do it **last**, after everything above is finished
  and checked.
- **All of Pass 3** — `index`, `site_plan`, `side_profile`, `title`, `symbol`, `roof_plan`,
  `misc`, `bbs_schedule`. Nothing in Constistant reads them today.

⚠️ `roof_plan` is a trap here: **structural roof framing is `pattern: "plan"` and belongs to
`plan_beam` (do extract it)**; only the architectural roof sheet is Pass 3 (skip). Getting this
backwards silently drops a house's roof beams from the BOQ — the exact live bug found on
2026-08-21 in 8 of 11 existing houses.

⚠️ `plan_column` barely exists as a sheet — 2 files across 11 houses. Columns normally appear as
markers inside the beam/footing plans and as a column table. **Do not go hunting for a column
plan that isn't there, and do not invent one.** If the house has no column sheet, record nothing
for subtask 3 and note it in `_scope.json`. This is expected, not a miss.

## The one extra step op01 does not have — `_scope.json`

A folder holding 38 of a house's 107 pages looks exactly like a finished house to anyone
opening it later, including a future Claude session. **Write the marker before running
`check_format.py`**, at `rawjson_ยังไม่ได้แก้ไขโดนคน/0N<house_name>/_scope.json`:

```json
{
  "scope": "pass2_only",
  "op": "op04",
  "date": "2026-08-22",
  "subtasks_done": ["gridline", "plan_footing", "plan_beam", "plan_slab",
                    "section", "schedule", "notes"],
  "subtasks_absent_from_this_house": ["plan_column", "soil_boring_log"],
  "deliberately_skipped": ["material_list", "index", "site_plan", "side_profile",
                           "title", "symbol", "roof_plan", "misc", "bbs_schedule"],
  "pages_extracted": 38,
  "pages_in_house": 107,
  "note": "Pass 2 subtasks only — this house is NOT fully extracted. Skipped pages were skipped on purpose (tune_ai/t03/dataset_sizing.md), not missed."
}
```

`check_format.py` skips any filename starting with `_`, so this file is inert to it — verified,
not assumed (`tools/check_format.py`, `check_house()`).

Distinguish the two absence reasons honestly: `subtasks_absent_from_this_house` means the
drawing set has no such sheet; `deliberately_skipped` means it exists and we chose not to
extract it. Collapsing them loses the only signal that tells a later reader whether a page is
missing or merely unwanted.

## Finishing — same gate as op01, one addition

1. Every file written and parses as JSON.
2. `_scope.json` written.
3. `python tools/check_format.py 0N<house_name>` → **ALL CHECKS PASS**.
4. Report: files created, pages extracted vs pages in house, per-subtask counts, low-confidence
   flags, open questions.
5. Add the row to `No_touch_box/docs/raw_json_data_log.md` — and the row **must say
   `op04 / pass2-only`**. A partial house logged as if it were complete is worse than an
   unlogged one: it makes the dataset look bigger than it is, and the next person sizing a
   training run will believe it.

## When to use op01 instead

- The house is meant to be a **complete reference set** (a demo house, or one used to check the
  spec end to end).
- Someone is going to compare AI output against this house across *all* patterns — a partial
  ground truth would score the missing pages as failures.

`op04` is for growing the training set cheaply. `op01` is for a house that has to be whole.
