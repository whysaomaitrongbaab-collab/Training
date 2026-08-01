# Gemini overlay-visualization prototype — design

## Goal

Prototype a single pipeline, runnable from this repo, that:

1. Sends one drawing page image to Gemini (Google AI Studio API) and asks it to
   extract column/footing elements using the same grid_ref schema already used
   for Qwen fine-tuning.
2. Resolves each element's `grid_refs` to real (x, y) coordinates in meters,
   using the existing gridline master JSON (`pos_m` per grid line) — no pixel
   bounding boxes required.
3. Renders a to-scale overlay diagram, diffs it against the existing
   human-corrected ground truth for that page, and shows a summary table of
   everything Gemini read.

Target test case: `image/บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า19.png`
(แปลนฐานรากแผ่และฐานรากเสาเข็ม), compared against
`json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า19_view1_footing_plan.json`.

This is a logic-testing prototype, not a production feature — no persistence
of user edits, no multi-page batch mode.

## Architecture

Three Python scripts, no server, chained via one output JSON per stage:

```
tools/gemini_overlay_prototype/
  extract_gemini.py    # Gemini API call -> elements JSON (grid_ref schema)
  resolve_grid.py       # gridline master (pos_m) -> (x_m, y_m) per grid_ref
  render_overlay.py     # elements + resolved coords + ground truth -> overlay.html
```

Run order:

```
python extract_gemini.py --house 01บ้าน_เล็ก_1ชั้น_01 --page 19
  -> output/หน้า19_gemini.json

python render_overlay.py --house 01บ้าน_เล็ก_1ชั้น_01 --page 19
  -> output/หน้า19_overlay.html   (opens directly in a browser)
```

`render_overlay.py` calls `resolve_grid.py`'s functions internally; it isn't
meant to be run standalone (kept as a separate module for clarity/testability,
not a separate CLI step).

## 1. Gemini extraction (`extract_gemini.py`)

- Reads the API key from env var `GEMINI_API_KEY`. Missing key -> clear error
  message and exit; never hardcoded, never prompted for at runtime.
- Uses the `google-genai` SDK (added to `training-data/requirements.txt`).
- Prompt is a trimmed version of the extraction prompt already used for Qwen
  fine-tuning (see `training-data/Prompt/stage-a/prompt.md` and the prompt
  embedded in `tune_ai/t01/data_before_tune/train.jsonl`), scoped down to just
  footing/column elements and the grid_ref rules — rebar/beam/other view types
  are out of scope for this prototype.
- Output schema matches the existing training schema exactly:
  ```json
  {"elements": [
    {"element_id": "C1", "element_type": "column", "count": 12,
     "grid_refs": ["D1", "D2", ...]}
  ]}
  ```
- Script writes this JSON to `output/<page>_gemini.json` and also prints it,
  so it can be inspected without opening the overlay.

## 2. Grid resolution (`resolve_grid.py`)

- Loads the house's `หน้า00_gridline.json` (`grid.x_lines` / `grid.y_lines`,
  each with `id` and `pos_m`).
- Exposes `resolve(grid_ref: str) -> (x_m, y_m)`, splitting a ref like `"C2"`
  into its y-line id (`"C"`) and x-line id (`"2"`) and looking up `pos_m` on
  each. Point-type elements (footing/column) always use single grid_refs, not
  ranges — matches the existing schema convention.
- Unknown grid_ref (not present in the master) -> the element is still listed
  in the summary table with a flagged "unresolved grid ref" note, but is
  skipped on the visual overlay (can't be plotted without a coordinate).

## 3. Overlay + diff (`render_overlay.py`)

- Draws grid lines to scale (meters -> px, single scale factor, computed to
  fit a fixed canvas size).
- Loads the ground-truth JSON for the same page/view and compares grid_refs
  for `element_type == "column"`:
  - In both Gemini output and ground truth -> green dot + label.
  - In ground truth only (Gemini missed it) -> red dashed circle + label.
    Clicking it toggles it to "confirmed added" (visual state change only —
    logged to the browser console, not persisted anywhere).
  - In Gemini output only (hallucinated) -> orange dot + label, marked
    distinctly from a true miss.
- Output is a single self-contained HTML file (inline SVG + inline JS, no
  build step, no external requests) — opens directly by double-clicking.

## 4. Element summary table

Above (or beside) the overlay diagram, the same HTML file includes a plain
table listing every element Gemini returned:

| element_id | type | count | grid_refs | match vs ground truth |
|---|---|---|---|---|
| C1 | column | 12 | D1, D2, ... | 11/12 matched, missing: C2 |

This is generated from the same diff used for the overlay coloring, so the
table and the picture never disagree. It's the plain-text fallback for
anything the visual overlay can't show clearly (e.g. an unresolved grid_ref
that got skipped on the diagram still shows up here).

## Out of scope (YAGNI)

- No persistence of clicked/added markers (console log only).
- No multi-page or multi-house batch mode (CLI takes one house + one page;
  re-run per page).
- No comparison against the existing Qwen output in this round (the data
  exists in `raw_json_ตัวที่ใช้งานจริง/` if this is extended later).
- No pixel-coordinate/bounding-box extraction from Gemini — positions come
  entirely from the gridline master's `pos_m` values.

## Testing

- Manual: run the two scripts against the `หน้า19` test case, open the
  resulting HTML, visually confirm the 12 known columns render, and that the
  intentionally-known easy-to-miss one (if any) is flagged correctly against
  ground truth.
- No automated test suite for this prototype — it's a throwaway/logic-testing
  tool, not shipped code.
