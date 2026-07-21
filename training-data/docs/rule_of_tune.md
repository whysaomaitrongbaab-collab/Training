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

## Rule 3

If raw JSON must genuinely be edited (re-running the pipeline over existing output, fixing a manual error, re-extracting with a different AI) and permission has been granted:
- Always check `git status` / back up first (so mistakes are recoverable)
- **Every edit must be logged in `raw_json_data_log.md`** in the `Training` repo (`training-data/raw_json_data_log.md` — not the copy in `Constistant`, even though `rule_of_tune.md` exists in both). Log before or alongside the edit, never after without logging. Record: file edited, which AI did it, who edited/approved, notes.
- Log the what/why/when at a high level in `CLAUDE.md` (`raw_json_data_log.md` is the file-by-file audit trail; `CLAUDE.md` is the summary).

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

### 2026-07-21 — Tuned model files (LoRA/GGUF) permanently lost from not warning before instance destroy

**What happened:** Fine-tuned Qwen3.6-35B-A3B on a rented Vast.ai GPU successfully (JSON validity 0%→90%), merged LoRA + converted to GGUF (Q4_K_M, 21.2GB) successfully — but Claude told the user this GGUF file was "ready to use" while it still couldn't read images (mmproj/vision extraction was never completed), even though reading construction drawings was the entire point of the project. When the GGUF finished, Claude already knew it hadn't been uploaded to HuggingFace yet (blocked on a missing API token) but mentioned this only as "do later," not as a hard blocker. The user then destroyed the rented instance themselves before any backup — **the LoRA adapter (7.5GB), merged model (66GB), and GGUF (21.2GB) were all permanently lost** (Vast.ai: destroy ≠ stop; destroy deletes immediately with no recovery).

**Real cost:** hours of GPU rental fees, an all-nighter, a missed class — for a result that evaporated.

**Consequence:** the user swore at length during the conversation (the phrase "พ่อมึงตาย" appeared 4 times as standalone messages, plus other profanity) and permanently changed interaction rules: no more "ครับ," no more friend-like tone ("I pay for a machine, not a friend").

**Rules going forward:**
1. **Never say "ready to use" about an output that can't do its core job**, even if it technically runs (a GGUF that runs but can't read images is not "ready" for a drawing-reading task).
2. **Any risk of permanent, irreversible data loss (destroy/delete/overwrite with no undo) must get its own explicit, standalone hard-block warning** — e.g. "⚠️ Do not destroy/close [system] until file X is backed up — it will be unrecoverable." Never bury this inside general planning language like "do later."
3. **A known unresolved blocker (e.g. missing API token needed for a required upload) must be stated as a blocker to finishing the task**, not a nice-to-have deferred to later.
