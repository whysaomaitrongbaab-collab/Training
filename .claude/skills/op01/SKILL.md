---
name: op01
description: Extract one house's construction drawings into ground-truth raw JSON for the Training repo's rawjson dataset. Triggers on "op01 <house_name>" or "op1 <house_name>" (Makham's shorthand), e.g. "op01 บ้านเอกมัย" — treat it as running this whole flow in one go without asking the user to re-explain each step. Standing order: produce the finished extraction no matter what, deciding every judgement call instead of stopping to ask. Source of truth is `rawjson_ยังไม่ได้แก้ไขโดนคน/README.md`'s `op1` section — keep this file in sync with it whenever that section changes.
---

# op01 — extract one house into raw JSON

Argument: `<house_name>` (e.g. `บ้านเอกมัย`). All paths below are relative to the **Training repo root**.

## Standing order — decide, don't ask

**Produce the finished extraction, no matter what.** Make every judgement call yourself and keep going to the end. Do not stop mid-run to ask which reading is right.

- **Authority:** `rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`. When two sheets disagree, when a field has no obvious home, when a new pattern appears — resolve it against that spec and the precedent already set by the existing houses, then move on.
- **Precedence when sheets conflict** (extends spec §7's "section wins over schedule"):
  1. **Grid geometry** → the STRUCTURAL footing/column plans win (S-sheets). An architectural site plan, or a sheet self-declared "เพื่อประมาณราคา/ตัวอย่าง", never overrides them.
  2. **Member spec** → the detail/section sheet wins over the plan; `section` wins over `schedule`.
  3. **More sheets agreeing beats fewer** — count them, and say so in the warning.
- **Every decision gets written down where the data lives** — a `warnings[]` entry stating what conflicted, which reading was taken, and why. Lower `confidence_score` and flag when the losing reading was genuinely plausible.
- **Never leave a field blank because a choice was hard.** Blank is only for "the drawing genuinely does not say" — never for "two sheets said different things."
- Asking mid-run is only correct if continuing would require **inventing data that appears on no sheet at all**.
- Label Studio is cancelled (2026-08-02) — never generate Label Studio task files, regardless of what an older transcript suggests.

## Steps

1. Read `rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md` in full — **every time**, don't rely on memory of a past session.
2. **Check for a duplicate first:** does any existing `rawjson_ยังไม่ได้แก้ไขโดนคน/0N<house_name>/` folder already match `<house_name>`? If so, **stop and report it** — don't silently re-extract a house that's already done, that only burns a full vision-extraction pass for a duplicate. Otherwise, determine the next sequence number `N` (2 digits): highest existing `0N<house>/` folder + 1. Don't ask the user to supply it.
3. Actually read every page image in `image/<house_name>/*.png` and extract per the spec — grid master first (`<house>_หน้า00_gridline.json`), then page-by-page/view-by-view. Never guess, never copy another house's data. This is real vision extraction work done in-session; no script does this part.
4. Save every file into the new `rawjson_ยังไม่ได้แก้ไขโดนคน/0N<house_name>/` folder.
5. Run `python tools/check_format.py 0N<house_name>` — every check must **PASS** before the house counts as finished.
6. Report back: files created, page count, any low-confidence flags or open questions (e.g. duplicate `element_id` across sections).
7. Add a row to `No_touch_box/docs/raw_json_data_log.md` per `rule_of_tune.md` rule #3 — every new house extraction is a real-data event that must be logged.

This does **not** skip any `rule_of_tune.md` protections — the output is ground-truth raw data the moment it's saved, protected the same as everything else in that folder.
