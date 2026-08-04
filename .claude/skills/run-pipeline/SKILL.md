---
name: run-pipeline
description: Run the training-data extraction pipeline (run_pipeline.py) on a house's rasterized PDF pages to generate structural-element JSON. User-invoked only — makes real Qwen-VL API calls and writes raw output.
disable-model-invocation: true
---

# Run Pipeline

Runs the current-generation extraction pipeline in `training-data/` (see `training-data/CLAUDE.md` "Generation ปัจจุบัน") against a house's PNG pages, producing structured JSON per structural page.

## Before running — read first

- `training-data/docs/rule_of_tune.md` — pipeline output lands in the protected `raw/image/<house>/qwen-output/` tree. Re-running against an existing house **overwrites prior raw JSON**, which requires the same warn-then-confirm flow as any other raw JSON edit.
- `training-data/SETUP.md` — one-time setup (`.env.local` with `QWEN_API_KEY`/`QWEN_API_HOST`, `pip install -r requirements.txt`).

## Steps

1. Confirm the target house folder exists: `training-data/raw/image/<house>/` with the source PDF and rasterized `<house>_หน้าNN.png` pages.
2. Confirm `training-data/.env.local` exists and has valid `QWEN_API_KEY` / `QWEN_API_HOST`. If missing, copy `.env.local.example` and ask the user for real values — never invent or guess a key.
3. **Test on one page first** (per rule_of_tune.md lesson #1 — never trial unverified changes on a full dataset):
   ```bash
   cd training-data
   python run_pipeline.py "raw/image/<house>" --only 20
   ```
4. If that looks right, run the full folder:
   ```bash
   python run_pipeline.py "raw/image/<house>" --toc 02 --anchors 20,40
   ```
   Adjust `--toc` (TOC page number) and `--anchors` (two page numbers with unambiguous sheet codes, used to resolve the PNG-to-TOC page offset) if the defaults don't match this house's document.
5. Output lands in `raw/image/<house>/qwen-output/`:
   - `_document_map.json` — Stage 0 routing table
   - `_run_summary.json` — run stats (pages extracted/skipped, token totals)
   - `<house>_หน้าNN.json` — per-page extraction (structural pages only)
6. If this run overwrote existing files in that folder, log it in `training-data/raw_json_data_log.md` per rule_of_tune.md Rule 3 (file, AI used, who approved, notes).

## Known failure modes to watch for

See `training-data/CLAUDE.md` "บทเรียนสำคัญ" before trusting output blindly — rebar spacing/size on fine text is unreliable, `main_bar_type` can flip DB/RB inconsistently on the same page, and `confidence_score` alone can't be trusted. Flag these for human review rather than accepting them as ground truth.
