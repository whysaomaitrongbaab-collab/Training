---
name: tuning-data-guardrails
description: Background knowledge for any work touching training-data/ raw JSON or fine-tuning pipeline logic — encodes rule_of_tune.md's warn-then-confirm rule and the raw_json_data_log.md logging requirement. Auto-loads for Claude; not user-invoked.
user-invocable: false
---

# Tuning Data Guardrails

Source of truth: `training-data/docs/rule_of_tune.md` — read it in full before any work in `training-data/` or `raw_json_ตัวที่ใช้งานจริง/`. This skill is a summary reminder, not a replacement; if this summary and the doc ever disagree, the doc wins.

## Rule 1 — never edit raw JSON silently

Never edit, overwrite, or delete raw JSON of pre-tuning raw data unless the user explicitly authorizes it in that same conversation. Protected:
- `raw/image/<house>/qwen-output/<house>_หน้าNN.json`, `_document_map.json`, `_run_summary.json` — direct output of `run_pipeline.py` / `build_document_map.py` / `analyze_folder.py`
- `raw_json_ตัวที่ใช้งานจริง/0N<house>/*.json` (repo root) — hand-transcribed ground truth

Not protected: regenerable derived files (`label-studio-tasks-*.json`), human-reviewed `annotated/*.json`, scripts/config/docs.

The two hook scripts (`.claude/hooks/block-raw-json-edit.js`, `.claude/hooks/block-env-edit.js`) enforce a confirmation prompt on these paths mechanically — but the hook can't judge whether a given file is genuinely "raw" vs. derived, or whether a script change indirectly affects tuning data. That judgment call is this skill's job.

## Rule 2 — warn before asking, and warn broadly

Before requesting permission to edit raw JSON, state the warning first (never ask quietly and explain after):
> Editing this file may directly affect the accuracy of fine-tuning data (it's source ground truth).

This extends beyond direct raw-JSON edits — also warn before:
- Editing generation/flattening script logic that feeds `annotated/*.json` or `dataset.jsonl`
- Changing field mappings or the schema structure used to assemble the dataset
- Anything else that touches "data that becomes a training example," directly or indirectly

Principle: if unsure whether an action affects tuning, assume it does and warn.

**Narrow exception** (skip re-warning only when ALL hold): already warned + approved earlier in this same conversation, in the same scope; it's a re-run of the same unchanged script/process; or it's a dry-run writing to a temp file deleted immediately. If any condition fails, warn again.

After citing this rule, actually stop and wait for the user's answer — don't act in the same message, and don't treat a short/ambiguous follow-up as a yes.

## Rule 3 — if approved, back up and log

If raw JSON editing is genuinely approved: check `git status` / back up first, then log every edit in `training-data/raw_json_data_log.md` (the Training repo copy, not the Constistant one) — file edited, which AI did it, who approved, notes. Log before or alongside the edit, never after without logging.
