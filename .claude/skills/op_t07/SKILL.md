---
name: op_t07
description: Run the t07_Palfrey fine-tune round — the Destrier successor that removes training-file names and edit history from the training labels (the cause of looping on unseen houses, measured 2026-10-03). Triggers on "op_t07" or "opt07" (Makham's shorthand). Walks the gates in tune_ai/t07_Palfrey/t07_workflow.md in order (free prep → dataset + sanitize → cheap-card Phase 0 → paid training → merge/serve/measure) and stops at the first failing gate. Never rents a training card without asking Makham first — that step costs real money. Source of truth is t07_workflow.md; keep this file in sync with it.
---

# op_t07 — tune round t07 (Palfrey)

All paths are relative to the **Training repo root**. Read these before doing anything:
1. `tune_ai/t07_Palfrey/t07_workflow.md` — the gates, pass criteria, and why each exists
2. `No_touch_box/docs/rule_of_tune.md` — standing tuning rules (cheap card first, pin versions, back up before destroy)
3. `tune_ai/t05_Destrier/proof/04_vllm_sglang_บนการ์ด.md` — the baseline numbers t07 must beat, and the bench tooling

## Standing order
- Decide judgement calls yourself (att1235 style) and record them as "ตัดสินแล้ว ✅ + เหตุผล + ความเสี่ยงที่รับ".
- **Stop and ask Makham before renting a training card (gate 3).** Gates 0–2 are free or near-free; gate 3 is the expensive one.
- Never edit files in `json_แก้ไขแล้ว/` (rule 1) — cleaning happens on the built jsonl via `sanitize_labels.py`.
- A gate that fails stops the run. Write what failed and the measured numbers; do not "fix forward" past it.

## Steps (summary — details and checklists live in t07_workflow.md)
0. **Free prep:** pin versions in t07 `onstart.sh`; set `UNSLOTH_MOE_LORA_B_LAYOUT` explicitly for train and serve; rebuild gridline examples so the longest one fits MAX_LENGTH (measure, never lower MAX_LENGTH); copy prompts from `t04_Purson/` into `t07_Palfrey/prompts/` and drop `source_image`/`source_pages` from their schemas.
1. **Dataset:** `build_t07.py` (copy of `build_t05_night.py`, same folds) → `python tune_ai/t07_Palfrey/sanitize_labels.py <all jsonl> --out tune_ai/t07_Palfrey/data/`. Pass = every file reports house names 0, audit notes 0, source_* 0, not-JSON 0.
2. **Phase 0 on a cheap card:** load, 10 steps, save, reload, one inference; expert-LoRA check must say grouped_by_expert for all 80.
3. **Ask Makham**, then train 4 folds and soup with the fixed soup script + `test_soup_layout.py`.
4. **Merge → verify A/B/C → serve vLLM → gate D → bench** (83b8e52c + the 3 web houses ×3 runs + `micro --repeat 4`). Compare against the pass table in t07_workflow.md.
5. Write a proof doc (`tune_ai/t07_Palfrey/proof/01_…md`), diary entry, and Constistant CLAUDE.md log; deploy steps are listed at the end of t07_workflow.md.

## Check before claiming done
- `python tune_ai/t07_Palfrey/sanitize_labels.py --selftest` passes.
- The pass table is filled with measured numbers, not estimates.
- Card destroyed and 0 instances confirmed after outputs are downloaded.
