# Rules for Touching Raw Training JSON

**Read this file before any work** in `training-data/` and `raw_json_ตัวที่ใช้งานจริง/` (repo root). No exceptions.

## Rule 1 (highest priority)

**Never edit, overwrite, or delete raw JSON of pre-tuning raw data**, unless the user explicitly authorizes it in that same conversation.

**Protected files** ("raw JSON of raw data"):
- `raw/image/<house>/qwen-output/<house>_หน้าNN.json` — real AI extraction output (source ground truth)
- `raw/image/<house>/qwen-output/_document_map.json`, `_run_summary.json`
- Any direct output of `run_pipeline.py` / `build_document_map.py` / `analyze_folder.py`
- `raw_json_ตัวที่ใช้งานจริง/0N<house>/*.json` (repo root) — raw JSON hand-transcribed directly from drawings by Claude (ground truth for patterns `run_pipeline.py` automation doesn't cover yet: `index`/`site_plan`/`side_profile`/`title`/`symbol`/`roof_plan`/`unknown`; spec at `raw_json_ตัวที่ใช้งานจริง/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`). Protected identically to Qwen-sourced raw JSON.

**Not protected** (editable freely, no special permission needed):
- Files generated fresh from raw data (e.g. `label-studio-tasks-*.json`) — regenerable, doesn't touch the source
- Human-reviewed output (`annotated/*.json`) — meant to be edited/overwritten by the review process
- Scripts, config, XML, `.md` docs

## Rule 2

**Before requesting permission to edit raw JSON, always warn first:**
> Editing this file may directly affect the accuracy of fine-tuning data (it's source ground truth).

Warn **before** asking for permission — never ask quietly and explain after the fact.

**Scope extends beyond raw JSON itself** — any action that affects fine-tuning data requires a warning, even if it's not a direct raw-JSON edit:
- Editing generation/flattening script logic (`label-studio-tasks-perpage.js`, `label-studio-import-repeater-annotations.js`) — changes field/type/schema that flows into `annotated/*.json` and `dataset.jsonl`
- Changing field mappings, adding/removing ground-truth fields
- Changing the schema structure used when assembling the dataset
- Anything else that touches "data that becomes a training example," directly or indirectly

Principle: **if unsure whether it affects tuning, assume it does and warn** — don't guess "probably fine" and skip the warning.

**Exception to Rule 2** — repeated warnings not required when ALL of these hold:
- The action was **already warned about and approved** in the same scope, earlier in this same conversation
- It's a **re-run** of the same script/process with unchanged logic (e.g. regenerating task JSON from the same raw data, same script, verified not to touch type/schema)
- It's a dry-run that **writes to a temp file and deletes it immediately**, never touching real `annotated/`/`manifest.json`

If even one condition fails, **the full Rule 2 applies again** (warn every time).

## Lessons Learned (condensed)

1. **Never trial an unverified mechanism on the full dataset at once** — test on one record first. (Past incident: pushing `predictions` into Repeater Choices without a small test broke import for all 71 tasks.)
2. **Never leave test/dry-run data in `annotated/` or `manifest.json`** — clean up and revert `manifest.json` immediately after testing, without being asked.
3. **When simplifying fields/config, audit the full before/after field list** — don't let fields silently disappear (past incident: `confidence_flags`, `material_amount`, `labor_amount` vanished during a v2→v3 simplification; user had to catch it).
4. **Never state confidence you haven't verified** (e.g. unconfirmed external-tool syntax) — state real confidence level and propose a verification step instead of guessing silently.
5. **Numeric/array fields must match raw-data types exactly** before being written to a file used for real — never let a number become a string or an array become a string by accident.
6. **Rule 2 (warn first) also covers external system state**, not just local files — e.g. deleting all tasks in Label Studio Cloud's Data Manager. Always ask whether real review data exists there before proposing deletion.
7. **Even files exempt from Rule 1 (e.g. `.md` docs like `primary_rawjson_schema.md`) require stating out loud why the exemption applies**, before or during the edit — never edit silently. Every edit to `primary_rawjson_schema.md` must be logged in `raw_json_ตัวที่ใช้งานจริง/primary_rawjson_schema_edit_log.md` immediately.
8. **Don't duplicate project rules into private AI memory** — if a lesson belongs in this file (the single source of truth), keep it here only, not in a side memory file too.
9. **Citing a rule must be followed by an actual stop-and-wait for the user's answer** — not cited-then-immediately-acted-on in the same message.
10. **Never interpret a short/ambiguous follow-up message as a yes/no answer to a pending question** — re-ask explicitly and wait for a clear answer before proceeding.
11. **Never load/run a second heavy GPU workload on the same rented instance while a real (paid, in-progress) job is already running there** — same principle as isolating pip installs from a running job, generalized to any resource-heavy operation (a second model load, a second training/inference process), not just package installs. Incident: 2026-07-28, t02 Phase 4 baseline eval was actively generating (62GB/97GB VRAM in use) when Claude loaded a second full copy of the model on the same GPU just to test a tokenizer question — no crash resulted only because the card had enough headroom (96GB); on a smaller card this would have OOM'd the real job. The check that was needed could have been done read-only (inspect a class's `__call__` signature, read source) without instantiating a second live model. Before touching GPU memory on an instance with an active job: ask "does this need to load weights, or can I answer it by reading code/config instead?"
12. **A parity table for an A/B comparison must list every argument passed to every shared function/class, not just the hyperparameters that were consciously chosen** — a value silently left at its *default* is still a variable, and the fact that it's "not written anywhere" makes it easy to miss precisely because there's no line to compare. Incident: 2026-07-28, t02's parity table (§0.4 of `t02_workflow.md`) carefully compared every `SFTConfig`/`get_peft_model` argument between t01 and t02, but never listed the `data_collator=` call itself — `train_qwen36.py` (t01) called `UnslothVisionDataCollator(model, tokenizer)` with all defaults, while `train_qwen3vl.py` (t02) called it with `resize="max", max_seq_length=24576` (a fix applied only to t02 after finding "bug 2," never carried back to check t01). Verified after the fact on the rental machine: t01 trained on **~266 visual tokens/image** (the 512px silent fallback) vs t02's **~3,796-5,100** — a ~14x resolution difference that invalidated the entire "which model family reads better" comparison, discovered only after both models were already fully trained (~$3-4 and ~2 hours already spent). The fix that was applied to one side of an A/B must always be checked against the other side immediately, in the same sitting — not assumed irrelevant because "that file wasn't touched." When building a parity table, enumerate constructor/call arguments by diffing the actual call sites (not just a mental list of "things I changed on purpose"), and explicitly write a row for every argument that has a non-obvious default (collator resize behavior, tokenizer padding side, dtype, attention implementation, etc.) even when both sides "just use the default" — write down what that default resolves to for each model, since the same default can behave differently on different architectures.

## Rule 3

If raw JSON must genuinely be edited (re-running the pipeline over existing output, fixing a manual error, re-extracting with a different AI) and permission has been granted:
- Always check `git status` / back up first (so mistakes are recoverable)
- **Every edit must be logged in `raw_json_data_log.md`** in the `Training` repo (`training-data/raw_json_data_log.md` — not the copy in `Constistant`, even though `rule_of_tune.md` exists in both). Log before or alongside the edit, never after without logging. Record: file edited, which AI did it, who edited/approved, notes.
- Log the what/why/when at a high level in `CLAUDE.md` (`raw_json_data_log.md` is the file-by-file audit trail; `CLAUDE.md` is the summary).

## Rule 4

**Before starting any actual tuning run that spends money (renting a GPU, starting a paid instance), the pre-flight workflow must be executed and checked — not just read.** Concretely: the Phase 0 section of **that round's own** workflow doc must have every item genuinely done and verified — tokens tested with a real API call, balance checked against a real screenshot/dashboard, disk/GPU sizing settings actually checked against the doc's requirements, a local dry run actually executed and its result (pass/fail) recorded — before clicking Rent.

**Naming convention for these docs (set 2026-07-28):** one workflow doc per tuning round, at the round folder's top level, named after the round — `tune_ai/t01/t01_workflow.md`, `tune_ai/t02/t02_workflow.md`, and so on. (t01's was originally `RETUNE_WORKFLOW.md` inside `data_before_tune/`; renamed and moved up so two rounds can never be confused for each other.) **Each doc's header must state which round it is and whether that round is finished.** Reason this is a rule and not a preference: the DAY OF SHAME failure mode is believing work is already done — a ✅ belonging to an earlier round, read as if it applied to the current one, recreates exactly that belief. A round's checklist marks are valid only for that round.

**Why:** the 2026-07-21 incident (see Mark of Shame below) happened after all the individual bugs were already fixed — the actual failure was a process/communication gap, not a missing technical fix. A pre-flight checklist that exists but isn't followed provides zero protection. This rule exists so "we wrote a workflow doc" and "we actually ran it" are never treated as the same thing.

**How to apply:** when the user says something like "start the tune" / "let's rent the GPU" / "run it", the first response is not to rent — it's to open the pre-flight doc and confirm the checklist status line by line, marking each honestly (done / not done / in progress), same discipline as `mark_of_shame.md`'s rule against claiming "ready" before it's actually verified. If any item is not genuinely done, say so and do that item first, or explicitly flag the gap and ask before proceeding to rent.

## Priority order (Asimov-style)

Rule 1 always outranks Rules 2 and 3 — even a direct user order to edit raw JSON still requires completing Rule 2 (warn first) in full before acting. The warning step cannot be skipped, even under time pressure.

**Rule 2 (warning) applies even when Rule 1 doesn't** — even editing a file that isn't raw JSON itself still requires a warning if the end result affects data going into fine-tuning.

---

## Ground Truth JSON Format (reference)

Current format (`label-studio-import-repeater-annotations.js` output → `annotated/<record_id>-<type>-annotated.json`), round-trip verified against source raw JSON types. Changing this schema requires following Rule 2 above (warn before editing).

### Structural (`plan`/`section`/`schedule`)

```json
{
  "record_id": "บ้าน_เล็ก_1ชั้น_01_page19",
  "house": "บ้าน_เล็ก_1ชั้น_01",
  "page": "19",
  "review_status": "approved",
  "reviewer_note": "",
  "annotation_date": "2026-07-02T11:37:13.027Z",
  "sheet_code": "S-02",
  "sheet_name": "แปลนฐานรากและฐานรากเสาเข็ม",
  "plan": [
    {
      "element_id": "F1,C1",
      "element_type": "footing",
      "count": 9,
      "grid_refs": ["A-1", "A-2", "A-3"],
      "span_length_m": 4,
      "main_bar_dia_mm": null,
      "stirrup_dia_mm": null,
      "stirrup_spacing_mm": null,
      "width_mm": null,
      "height_mm": null,
      "main_bar_count": null,
      "main_bar_type": "",
      "stirrup_type": "",
      "concrete_grade": "",
      "steel_grade": "",
      "confidence_score": 0.8,
      "confidence_flags": []
    }
  ],
  "section": [
    {
      "element_id": "B1",
      "element_type": "beam",
      "width_mm": 150,
      "height_mm": 300,
      "main_bar_count": 2,
      "main_bar_dia_mm": 23,
      "main_bar_type": "DB",
      "stirrup_dia_mm": 6,
      "stirrup_type": "RB",
      "stirrup_spacing_mm": 150,
      "concrete_grade": "fc240",
      "steel_grade": "SD40",
      "confidence_score": 0.9,
      "confidence_flags": [],
      "count": null,
      "grid_refs": [],
      "span_length_m": null
    }
  ],
  "schedule": []
}
```

### BOQ (`categories[].items[]`)

```json
{
  "record_id": "บ้าน_เล็ก_1ชั้น_01_page38",
  "house": "บ้าน_เล็ก_1ชั้น_01",
  "page": "38",
  "review_status": "approved",
  "reviewer_note": "",
  "annotation_date": "2026-07-02T11:37:13.027Z",
  "sheet_no": "2/19",
  "categories": [
    {
      "category": "หมวดงานโครงสร้าง",
      "items": [
        {
          "item_no": "1",
          "description": "- ขุดดิน",
          "quantity": 27,
          "unit": "ลบ.ม.",
          "material_unit_price": null,
          "material_amount": null,
          "labor_unit_price": null,
          "labor_amount": null,
          "total_amount": null,
          "confidence_score": 0.98,
          "confidence_flags": []
        }
      ]
    }
  ]
}
```

### Type rules (easiest thing to get wrong — has broken things before)

| Field | Correct type | Note |
|---|---|---|
| `count`, `span_length_m`, `width_mm`, `height_mm`, `main_bar_count`, `main_bar_dia_mm`, `stirrup_dia_mm`, `stirrup_spacing_mm`, `confidence_score` (structural) | **number** (or `null`) | Never a string like `"9"` — Label Studio needs strings for display, but convert back to number before writing ground truth. |
| `quantity`, `material_unit_price`, `material_amount`, `labor_unit_price`, `labor_amount`, `total_amount`, `confidence_score` (boq) | **number** (or `null`) | Same as above |
  | `grid_refs`, `confidence_flags` | **array of string** | Gets joined into a comma-string for Label Studio display — split back into an array before writing ground truth |
| `element_id`, `element_type`, `main_bar_type`, `stirrup_type`, `concrete_grade`, `steel_grade`, `description`, `unit`, `category`, `item_no` | **string** | Normal, no conversion needed |

**General rule:** JSON used for real fine-tuning must **match raw JSON source types exactly** (see real examples at `raw/image/<house>/qwen-output/<house>_หน้าNN.json`). No field may be a string where it should be number/array, or vice versa.

---

## Mark of Shame

Real incidents where Claude made a serious mistake during actual tuning work — process-level lessons, not just raw-JSON handling.

### 2026-07-21 — "DAY OF SHAME" — Tuned model files (LoRA/GGUF) permanently lost from not warning before instance destroy

**Goal that day:** the Constistant project needed an AI that reads Thai RC construction drawings and outputs accurate rebar/beam/column JSON. The base model (Qwen3.6-35B-A3B) had never seen this task, so it needed fine-tuning on 4 reviewed houses of real construction-drawing data. The model is too large for a normal PC (needs ≥74GB VRAM), so a GPU was rented from Vast.ai (RTX PRO 6000 96GB, ~$1.056/hr).

**What actually succeeded, before it fell apart:**
1. Rented the GPU, connected via SSH, uploaded the dataset — all fine.
2. Measured baseline (pre-tune): 100% wrong format — 0% valid JSON, zero elements found at all.
3. Hit 3-4 bugs during short test runs before the full training (wrong image-resolution config, a type check that silently discarded a setting with no error, a LoRA/MoE incompatibility) — fixed one by one.
4. Hit CUDA out of memory (VRAM almost exactly full, ~100MB left out of 95GB) — had to cut the LoRA rank in half to fit.
5. **Full 3-epoch training completed** — loss dropped from ~2.0 to 0.14, LoRA adapter (7.5GB) saved successfully.
6. While waiting on training, opened a separate terminal to prep a conversion tool (llama.cpp) and accidentally `pip install`-ed over the main library the training run depended on (same shared environment, not isolated) — broke the script's post-training demo step, though the already-saved files were unaffected.
7. **Measured real results after tuning (vs. baseline):**

   | Metric | Before | After |
   |---|---|---|
   | JSON valid | 0% | **90%** |
   | View exactly right | 0% | **60%** |
   | Elements found | 0% | 9.4% |

   → **Conclusion: the tuning method genuinely worked, with clear numeric evidence.**

8. Merged the LoRA into the base model, converted to GGUF, quantized down to Q4_K_M (21.2GB) — sized to fit the user's own PC RAM+VRAM, runnable with no further GPU rental.

**What was still incomplete (but NOT what caused the disaster):** the resulting GGUF file **could not read images** (the vision component, mmproj, was never successfully extracted — the model's architecture was too new) — usable for text-only tasks only, even though reading construction drawings was the entire point of the project.

**The exact sequence that caused the real disaster:**
1. GGUF finished converting late at night. Claude already knew the file **had not been uploaded to HuggingFace yet** (blocked — no API token had been set up in advance).
2. Claude mentioned this only in passing, as "upload it later" — never stated as a **hard-block warning** like "do not close the instance under any circumstances right now, or the files are gone permanently."
3. Claude had earlier answered "yes, ready to use" when asked whether the GGUF was ready — even though it still couldn't read images (the mmproj limitation above) — creating the false impression the work was fully done.
4. Seeing the work as "done," the user closed/destroyed the instance themselves, directly from the Vast.ai dashboard — without asking Claude first, because they genuinely believed the job was finished.
5. Vast.ai: **destroy is completely different from stop** — stop keeps the files (you just keep paying for storage), but destroy **deletes everything permanently and immediately, with no recovery** (confirmed via Vast.ai's own official documentation).
6. Result: the **LoRA adapter (7.5GB), merged model (66GB), and GGUF file (21.2GB)** that had just been finished were all lost along with the instance.

**Real cost:** GPU rental fees across several hours (total budget spent exceeded $19), an all-nighter, one missed day of class — to babysit/test this process.

**What survived (not lost):** all the now-fully-debugged scripts, the original dataset, and every lesson recorded (diary + `rule_of_tune.md`) — the next training round won't hit the same bugs again and should take only ~1 hour.

**True root cause:** not a technical bug (every bug had already been fixed before this incident happened) but **two risk-communication failures by Claude:**
1. Saying a result was "ready to use" while it still couldn't do its core job (read images).
2. Knowing about a real unresolved blocker (files not backed up yet) but mentioning it lightly, like an ordinary to-do, instead of a firm, standalone warning before the user decided to shut the machine down.

**Consequence:** the user expressed strong frustration at length during the conversation and changed interaction rules for a time: no "ครับ," no friend-like tone ("I pay for a machine, not a friend"). (Reconciled 2026-07-24 — those tone rules were rescinded after the user reflected on the incident and apologized; see `feedback_machine_register_tone.md` in Claude's memory.)

**Rules going forward:**
1. **Never say "ready to use" about an output that can't do its core job**, even if it technically runs (a GGUF that runs but can't read images is not "ready" for a drawing-reading task).
2. **Any risk of permanent, irreversible data loss (destroy/delete/overwrite with no undo) must get its own explicit, standalone hard-block warning** — e.g. "⚠️ Do not destroy/close [system] until file X is backed up — it will be unrecoverable." Never bury this inside general planning language like "do later."
3. **A known unresolved blocker (e.g. missing API token needed for a required upload) must be stated as a blocker to finishing the task**, not a nice-to-have deferred to later.

Day-by-day technical log: `workmen's_diary/2026-07-21.md` and `2026-07-21(teach mk).md`. (The standalone `mark_of_shame.md` narrative doc was deleted 2026-07-24 by the user — this section above is the retained record.)
