# Gemini Overlay Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 3-script Python prototype that sends `image/บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า19.png` to Gemini, resolves the returned column `grid_refs` to real (x,y) meter coordinates using the existing gridline master JSON, and renders a self-contained HTML overlay + element summary table that diffs the result against the existing human-corrected ground truth for that page.

**Architecture:** `extract_gemini.py` calls the Gemini API and writes an elements JSON matching the existing Qwen training schema. `resolve_grid.py` is a pure-function module (no I/O side effects beyond loading its input file) that turns a grid_ref like `"C2"` into meters using `pos_m` values already present in `หน้า00_gridline.json`. `render_overlay.py` loads the Gemini output + ground truth + resolved coordinates, computes a 3-way diff (matched / missed / hallucinated), and writes one static HTML file (inline SVG + inline JS) with both the overlay diagram and a plain summary table.

**Tech Stack:** Python 3, `google-genai` SDK (Gemini API client), stdlib `json`/`argparse`/`pathlib` only otherwise — no web framework, no build step, no pytest (this is a throwaway logic-testing prototype per the spec, see Global Constraints).

## Global Constraints

- Reference spec: `docs/superpowers/specs/2026-08-01-gemini-overlay-prototype-design.md` — every task below implements one section of it.
- API key comes from env var `GEMINI_API_KEY` only. Never hardcode a key, never prompt for one interactively, fail with a clear error message if unset.
- No pixel bounding boxes anywhere in this prototype — all element positions come from `grid.x_lines[].pos_m` / `grid.y_lines[].pos_m` in the gridline master JSON.
- No automated test suite (pytest or otherwise) — this is a throwaway prototype per the spec's "Testing" section. Each pure-logic module instead gets a `if __name__ == "__main__":` self-check block using plain `assert` statements, runnable directly (`python resolve_grid.py`) with no extra dependency. This still gives each task an independently-runnable verification step, per the "Task Right-Sizing" rule, without adding pytest to a repo that doesn't already use it.
- No persistence of user clicks in the HTML viewer — clicking a missed-element marker only toggles its on-screen color and logs to the browser console.
- Single house + single page per run (`--house`, `--page` CLI args) — no batch mode.
- Follow the existing per-page JSON convention already used in this repo (`training-data/CLAUDE.md`): element schema is `{"elements": [{"element_id", "element_type", "count", "grid_refs"}]}`, point-type elements (footing/column) use a flat list of individual grid_ref strings, never `start-end` ranges.
- This prototype does not touch any file under `training-data/raw/` or any existing ground-truth JSON — it only reads them. `training-data/rule_of_tune.md`'s warning-before-editing-raw-JSON rule does not apply here since nothing existing is modified, only new files are created under `tools/gemini_overlay_prototype/`.

---

### Task 1: Project scaffold + grid resolution module

**Files:**
- Create: `tools/gemini_overlay_prototype/__init__.py` (empty — makes the folder importable)
- Create: `tools/gemini_overlay_prototype/resolve_grid.py`
- Modify: `training-data/requirements.txt` (add `google-genai>=0.3.0`)

**Interfaces:**
- Produces: `load_gridline_master(path: str) -> dict` — parses a `หน้า00_gridline.json` file into `{"x": {id: pos_m}, "y": {id: pos_m}}`.
- Produces: `resolve(grid_ref: str, grid: dict) -> tuple[float, float] | None` — splits `grid_ref` (e.g. `"C2"`) into its y-line id and x-line id, looks both up in `grid`, returns `(x_m, y_m)`, or `None` if either id is missing.

- [ ] **Step 1: Create the package folder and empty `__init__.py`**

```bash
mkdir -p tools/gemini_overlay_prototype
```

Create `tools/gemini_overlay_prototype/__init__.py` with empty content (just makes the directory a package so later scripts can `from resolve_grid import ...` when run as `python -m tools.gemini_overlay_prototype.render_overlay` — but see Step 2's docstring for the simpler direct-run convention actually used).

- [ ] **Step 2: Write `resolve_grid.py` with `load_gridline_master` and `resolve`**

Grid line ids in the real data are **1-2 uppercase Thai/Latin letters for rows** (`y_lines`, e.g. `"D"`, `"A'"`) and **1-2 digit numbers with optional trailing primes for columns** (`x_lines`, e.g. `"1"`, `"3'"`, `"3''"`). A `grid_ref` like `"C2"` or `"A'3''"` is always `<y_line_id><x_line_id>` concatenated with no separator, and the boundary is always right after the last letter/prime-on-a-letter character before the first digit. Splitting rule: everything up to (and not including) the first digit character is the y-line id; everything from the first digit character onward is the x-line id.

```python
"""Resolve a construction-drawing grid_ref (e.g. "C2") to real-world
(x_m, y_m) meters, using the pos_m values already recorded in a house's
gridline master JSON. No pixel/bbox data is used anywhere in this module.
"""
import json
import re

# First digit in the ref marks the start of the x-line id (columns are
# numeric: "1", "2", "3'", "3''"...). Everything before it is the y-line id
# (rows are lettered: "A", "B", "D'"...).
_X_START = re.compile(r"\d")


def load_gridline_master(path):
    """Load a `<house>_หน้า00_gridline.json` file into a flat lookup dict:
    {"x": {"1": 0.0, "2": 4.0, "3'": 7.6, ...}, "y": {"D": 0.0, "C": 4.0, ...}}
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    grid = data["grid"]
    return {
        "x": {line["id"]: line["pos_m"] for line in grid["x_lines"]},
        "y": {line["id"]: line["pos_m"] for line in grid["y_lines"]},
    }


def resolve(grid_ref, grid):
    """Split a point grid_ref like "C2" or "A'3''" into (y_id, x_id) and
    look both up in `grid`. Returns (x_m, y_m) in meters, or None if either
    id isn't present in the gridline master (caller should flag this as an
    unresolved ref rather than crash).
    """
    match = _X_START.search(grid_ref)
    if not match:
        return None
    y_id, x_id = grid_ref[: match.start()], grid_ref[match.start() :]
    if x_id not in grid["x"] or y_id not in grid["y"]:
        return None
    return (grid["x"][x_id], grid["y"][y_id])


if __name__ == "__main__":
    # Self-check against the real gridline master for บ้าน_เล็ก_1ชั้น_01,
    # using values read directly from
    # json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json
    grid = load_gridline_master(
        "../../json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json"
    )
    assert grid["x"]["1"] == 0.0
    assert grid["x"]["2"] == 4.0
    assert grid["y"]["D"] == 0.0
    assert grid["y"]["A"] == 9.5
    assert resolve("D1", grid) == (0.0, 0.0)
    assert resolve("C2", grid) == (4.0, 4.0)
    assert resolve("A3", grid) == (7.0, 9.5)
    assert resolve("Z9", grid) is None  # unknown ids -> None, not a crash
    print("resolve_grid.py self-check: all assertions passed")
```

- [ ] **Step 3: Run the self-check**

Run: `cd tools/gemini_overlay_prototype && python resolve_grid.py`
Expected output: `resolve_grid.py self-check: all assertions passed`

- [ ] **Step 4: Add the `google-genai` dependency**

Add this line to `training-data/requirements.txt` (which already lists other pipeline deps):

```
google-genai>=0.3.0  # Gemini API client — used by tools/gemini_overlay_prototype/extract_gemini.py
```

- [ ] **Step 5: Commit**

```bash
git add tools/gemini_overlay_prototype/__init__.py tools/gemini_overlay_prototype/resolve_grid.py training-data/requirements.txt
git commit -m "Add grid_ref resolution module for overlay prototype"
```

---

### Task 2: Gemini extraction script

**Files:**
- Create: `tools/gemini_overlay_prototype/extract_gemini.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (this script only produces the raw elements JSON; grid resolution happens in Task 3).
- Produces: writes `tools/gemini_overlay_prototype/output/<house>_หน้า<page>_gemini.json` with the shape `{"elements": [{"element_id": str, "element_type": str, "count": int, "grid_refs": [str, ...]}]}`. This exact shape and these exact keys are what Task 3's diff logic consumes.

- [ ] **Step 1: Write the extraction prompt as a module-level constant**

This is a trimmed version of the extraction prompt already used for Qwen fine-tuning (`tune_ai/t01/data_before_tune/train.jsonl`, `training-data/Prompt/stage-a/prompt.md`), scoped to only footing/column point-type elements — no rebar, no beams, no other view types.

```python
"""Send one construction-drawing page image to Gemini and extract
footing/column elements using the same grid_ref schema already used for
Qwen fine-tuning in this repo. Writes output/<house>_หน้า<page>_gemini.json.
"""
import argparse
import json
import os
from pathlib import Path

from google import genai

EXTRACTION_PROMPT = """You are reading one page of a Thai reinforced-concrete (RC) \
construction drawing set. This page shows a footing/column plan (แปลนฐานราก).

Find every footing (ฐานราก) and every column (เสา) mark on this page. Each mark has:
- element_id: the label printed in the drawing (e.g. "F1" for a footing type, "C1" for \
a column type). Footings and columns are often printed as a combined label at the same \
point (e.g. "F1,C1") — still record them as separate elements, one entry for the footing \
mark and one for the column mark, both pointing at that same grid position.
- element_type: exactly "footing" or "column".
- count: how many points on the page carry this exact mark.
- grid_refs: the list of grid positions where this mark appears, read from the grid \
lines printed on the page (row letter first, then column number — e.g. "C2", never "2C"). \
A grid line not on a named/printed grid still needs a name: append a prime to the \
nearest named grid ("1'", "A'"). Point-type elements (footing/column) always use a flat \
list of individual grid_ref strings, never a "start-end" range.

Return ONLY valid JSON, no explanation, in exactly this shape:

{"elements": [
  {"element_id": "F1", "element_type": "footing", "count": 11, "grid_refs": ["D1", "D2", ...]},
  {"element_id": "C1", "element_type": "column", "count": 12, "grid_refs": ["D1", "D2", ...]}
]}
"""


def extract(image_path, model="gemini-2.5-flash"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a key from https://aistudio.google.com/ "
            "and export it: export GEMINI_API_KEY=your-key-here"
        )
    client = genai.Client(api_key=api_key)
    image_bytes = Path(image_path).read_bytes()
    response = client.models.generate_content(
        model=model,
        contents=[
            {"text": EXTRACTION_PROMPT},
            {"inline_data": {"mime_type": "image/png", "data": image_bytes}},
        ],
        config={"response_mime_type": "application/json"},
    )
    return json.loads(response.text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--house", required=True, help='e.g. "บ้าน_เล็ก_1ชั้น_01"')
    parser.add_argument("--page", required=True, help='page number, e.g. "19"')
    args = parser.parse_args()

    page_padded = args.page.zfill(2)
    image_path = Path("image") / args.house / f"{args.house}_หน้า{page_padded}.png"
    if not image_path.exists():
        raise FileNotFoundError(f"Page image not found: {image_path}")

    result = extract(image_path)

    output_dir = Path("tools/gemini_overlay_prototype/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.house}_หน้า{page_padded}_gemini.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script runs against the real test case**

Run (from repo root, with `GEMINI_API_KEY` exported in your shell):
```bash
python tools/gemini_overlay_prototype/extract_gemini.py --house บ้าน_เล็ก_1ชั้น_01 --page 19
```
Expected: prints a JSON object with an `"elements"` array containing at least one `element_type: "column"` entry, and writes `tools/gemini_overlay_prototype/output/บ้าน_เล็ก_1ชั้น_01_หน้า19_gemini.json`. Inspect the printed JSON by eye — confirm `grid_refs` look like `["D1", "D2", ...]` (letter-then-number, no dashes).

- [ ] **Step 3: Commit**

```bash
git add tools/gemini_overlay_prototype/extract_gemini.py
git commit -m "Add Gemini extraction script for overlay prototype"
```

(Do not commit the `output/` JSON from Step 2 yet — Task 4 will commit a full end-to-end output set together.)

---

### Task 3: Diff logic (Gemini output vs ground truth)

**Files:**
- Create: `tools/gemini_overlay_prototype/diff_elements.py`

**Interfaces:**
- Consumes: `resolve_grid.load_gridline_master` / `resolve_grid.resolve` from Task 1.
- Produces: `diff_columns(gemini_elements: list[dict], ground_truth_elements: list[dict], grid: dict) -> dict` returning
  ```python
  {
    "matched": [{"grid_ref": str, "xy": (float, float)}],
    "missed": [{"grid_ref": str, "xy": (float, float) | None}],       # in ground truth only
    "hallucinated": [{"grid_ref": str, "xy": (float, float) | None}], # in Gemini output only
    "unresolved": [str, ...],  # grid_refs (from either side) not found in the gridline master
  }
  ```
  This exact return shape is what Task 4's `render_overlay.py` consumes directly for both the SVG markers and the summary table rows.

- [ ] **Step 1: Write `diff_elements.py`**

```python
"""Diff a Gemini-extracted column list against ground truth, by grid_ref.
Positions come from resolve_grid (pos_m-based), never from pixel data.
"""
from resolve_grid import resolve


def _column_grid_refs(elements):
    """Flatten every element with element_type == "column" into one set of
    grid_refs. Real files sometimes carry the same grid position on more
    than one element_id entry (rare, but grid_refs is the unit of truth
    here, not element_id) -- a set naturally dedupes that.
    """
    refs = set()
    for el in elements:
        if el.get("element_type") == "column":
            refs.update(el.get("grid_refs", []))
    return refs


def diff_columns(gemini_elements, ground_truth_elements, grid):
    gemini_refs = _column_grid_refs(gemini_elements)
    truth_refs = _column_grid_refs(ground_truth_elements)

    matched_refs = gemini_refs & truth_refs
    missed_refs = truth_refs - gemini_refs
    hallucinated_refs = gemini_refs - truth_refs

    all_refs = gemini_refs | truth_refs
    unresolved = sorted(ref for ref in all_refs if resolve(ref, grid) is None)

    def _entries(refs):
        return [{"grid_ref": ref, "xy": resolve(ref, grid)} for ref in sorted(refs)]

    return {
        "matched": _entries(matched_refs),
        "missed": _entries(missed_refs),
        "hallucinated": _entries(hallucinated_refs),
        "unresolved": unresolved,
    }


if __name__ == "__main__":
    from resolve_grid import load_gridline_master

    grid = load_gridline_master(
        "../../json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json"
    )
    # Simulated Gemini output missing one column (C2) vs the real 12-column
    # ground truth read from
    # json_แก้ไขแล้ว/.../บ้าน_เล็ก_1ชั้น_01_หน้า19_view1_footing_plan.json
    gemini_elements = [
        {"element_type": "column", "grid_refs": [
            "D1", "D2", "D3", "C1", "C3", "B1", "B2", "B3", "A1", "A2", "A3"
        ]}
    ]
    truth_elements = [
        {"element_type": "column", "grid_refs": [
            "D1", "D2", "D3", "C1", "C2", "C3", "B1", "B2", "B3", "A1", "A2", "A3"
        ]}
    ]
    result = diff_columns(gemini_elements, truth_elements, grid)
    assert len(result["matched"]) == 11
    assert result["missed"] == [{"grid_ref": "C2", "xy": (4.0, 4.0)}]
    assert result["hallucinated"] == []
    assert result["unresolved"] == []
    print("diff_elements.py self-check: all assertions passed")
```

- [ ] **Step 2: Run the self-check**

Run: `cd tools/gemini_overlay_prototype && python diff_elements.py`
Expected output: `diff_elements.py self-check: all assertions passed`

- [ ] **Step 3: Commit**

```bash
git add tools/gemini_overlay_prototype/diff_elements.py
git commit -m "Add ground-truth diff logic for overlay prototype"
```

---

### Task 4: Overlay + summary table renderer

**Files:**
- Create: `tools/gemini_overlay_prototype/render_overlay.py`

**Interfaces:**
- Consumes: `resolve_grid.load_gridline_master`, `resolve_grid.resolve` (Task 1); `diff_elements.diff_columns` (Task 3); the JSON file written by `extract_gemini.py` (Task 2).
- Produces: `tools/gemini_overlay_prototype/output/<house>_หน้า<page>_overlay.html` — a single static file, no external requests, openable by double-click.

- [ ] **Step 1: Write `render_overlay.py`**

```python
"""Render a to-scale SVG overlay + element summary table comparing a
Gemini extraction against ground truth, using grid pos_m for all
positions (no pixel/bbox data anywhere in this file).
"""
import argparse
import json
from pathlib import Path

from diff_elements import diff_columns
from resolve_grid import load_gridline_master

SCALE_PX_PER_M = 40  # fixed scale factor: 1 meter of drawing = 40px on screen
MARGIN_PX = 40


def _to_px(x_m, y_m, min_x, min_y):
    return (MARGIN_PX + (x_m - min_x) * SCALE_PX_PER_M,
            MARGIN_PX + (y_m - min_y) * SCALE_PX_PER_M)


def _grid_svg(grid, min_x, max_x, min_y, max_y):
    lines = []
    width_px = MARGIN_PX * 2 + (max_x - min_x) * SCALE_PX_PER_M
    height_px = MARGIN_PX * 2 + (max_y - min_y) * SCALE_PX_PER_M
    for x_id, x_m in grid["x"].items():
        x_px, _ = _to_px(x_m, min_y, min_x, min_y)
        lines.append(
            f'<line x1="{x_px}" y1="{MARGIN_PX}" x2="{x_px}" y2="{height_px - MARGIN_PX}" '
            f'stroke="#ccc" stroke-width="1"/>'
            f'<text x="{x_px}" y="{MARGIN_PX - 10}" font-size="12" text-anchor="middle">{x_id}</text>'
        )
    for y_id, y_m in grid["y"].items():
        _, y_px = _to_px(min_x, y_m, min_x, min_y)
        lines.append(
            f'<line x1="{MARGIN_PX}" y1="{y_px}" x2="{width_px - MARGIN_PX}" y2="{y_px}" '
            f'stroke="#ccc" stroke-width="1"/>'
            f'<text x="{MARGIN_PX - 20}" y="{y_px + 4}" font-size="12" text-anchor="middle">{y_id}</text>'
        )
    return "\n".join(lines), width_px, height_px


def _marker_svg(entry, min_x, min_y, color, dashed, label_suffix=""):
    if entry["xy"] is None:
        return ""
    x_px, y_px = _to_px(entry["xy"][0], entry["xy"][1], min_x, min_y)
    dash_attr = ' stroke-dasharray="4,3"' if dashed else ""
    fill = "none" if dashed else color
    return (
        f'<g class="marker" data-ref="{entry["grid_ref"]}">'
        f'<circle cx="{x_px}" cy="{y_px}" r="10" fill="{fill}" stroke="{color}" '
        f'stroke-width="2"{dash_attr} onclick="toggleMarker(this)"/>'
        f'<text x="{x_px}" y="{y_px - 14}" font-size="11" text-anchor="middle">'
        f'{entry["grid_ref"]}{label_suffix}</text>'
        f"</g>"
    )


def _summary_table_html(diff):
    rows = []
    for entry in diff["matched"]:
        rows.append(f'<tr><td>{entry["grid_ref"]}</td><td>matched</td></tr>')
    for entry in diff["missed"]:
        rows.append(f'<tr><td>{entry["grid_ref"]}</td><td class="missed">missing (in ground truth, not detected)</td></tr>')
    for entry in diff["hallucinated"]:
        rows.append(f'<tr><td>{entry["grid_ref"]}</td><td class="hallucinated">extra (detected, not in ground truth)</td></tr>')
    for ref in diff["unresolved"]:
        rows.append(f'<tr><td>{ref}</td><td class="unresolved">unresolved grid ref (not in gridline master)</td></tr>')
    total_truth = len(diff["matched"]) + len(diff["missed"])
    return (
        f'<p>{len(diff["matched"])}/{total_truth} columns matched ground truth.</p>'
        f'<table border="1" cellpadding="4"><tr><th>grid_ref</th><th>status</th></tr>'
        f'{"".join(rows)}</table>'
    )


def render(house, page):
    page_padded = page.zfill(2)
    base = Path(__file__).parent.parent.parent  # repo root, from tools/gemini_overlay_prototype/render_overlay.py

    gemini_path = Path(__file__).parent / "output" / f"{house}_หน้า{page_padded}_gemini.json"
    gemini_data = json.loads(gemini_path.read_text(encoding="utf-8"))

    truth_path = (
        base / "json_แก้ไขแล้ว" / f"01{house}" / f"{house}_หน้า{page_padded}_view1_footing_plan.json"
    )
    truth_data = json.loads(truth_path.read_text(encoding="utf-8"))

    grid_path = base / "json_แก้ไขแล้ว" / f"01{house}" / f"{house}_หน้า00_gridline.json"
    grid = load_gridline_master(grid_path)

    diff = diff_columns(gemini_data["elements"], truth_data["elements"], grid)

    all_x = list(grid["x"].values())
    all_y = list(grid["y"].values())
    min_x, max_x, min_y, max_y = min(all_x), max(all_x), min(all_y), max(all_y)

    grid_svg, width_px, height_px = _grid_svg(grid, min_x, max_x, min_y, max_y)
    markers_svg = "\n".join(
        [_marker_svg(e, min_x, min_y, "#2ecc71", dashed=False) for e in diff["matched"]]
        + [_marker_svg(e, min_x, min_y, "#e74c3c", dashed=True) for e in diff["missed"]]
        + [_marker_svg(e, min_x, min_y, "#e67e22", dashed=False) for e in diff["hallucinated"]]
    )

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{house} หน้า{page_padded} overlay</title>
<style>
  .missed {{ color: #e74c3c; }}
  .hallucinated {{ color: #e67e22; }}
  .unresolved {{ color: #999; }}
  .marker circle {{ cursor: pointer; }}
</style></head>
<body>
<h1>{house} หน้า{page_padded} — column overlay</h1>
<svg width="{width_px}" height="{height_px}">
{grid_svg}
{markers_svg}
</svg>
{_summary_table_html(diff)}
<script>
function toggleMarker(circle) {{
  const isGreen = circle.getAttribute('fill') === '#2ecc71';
  circle.setAttribute('fill', isGreen ? 'none' : '#2ecc71');
  circle.setAttribute('stroke', '#2ecc71');
  console.log('toggled', circle.parentElement.dataset.ref);
}}
</script>
</body></html>"""

    output_path = Path(__file__).parent / "output" / f"{house}_หน้า{page_padded}_overlay.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"Wrote {output_path}")
    return diff


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--house", required=True)
    parser.add_argument("--page", required=True)
    args = parser.parse_args()
    render(args.house, args.page)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it end-to-end against the real test case**

Prerequisite: Task 2's `extract_gemini.py` must already have been run for `--house บ้าน_เล็ก_1ชั้น_01 --page 19`, producing `output/บ้าน_เล็ก_1ชั้น_01_หน้า19_gemini.json`.

Run:
```bash
cd tools/gemini_overlay_prototype
python render_overlay.py --house บ้าน_เล็ก_1ชั้น_01 --page 19
```
Expected: prints `Wrote .../บ้าน_เล็ก_1ชั้น_01_หน้า19_overlay.html`, no traceback.

- [ ] **Step 3: Open the HTML file and visually verify**

Open `tools/gemini_overlay_prototype/output/บ้าน_เล็ก_1ชั้น_01_หน้า19_overlay.html` in a browser (double-click it). Confirm:
- A grid of labeled lines (D/C/B/A rows, 1/2/3 columns) renders.
- Green dots appear at grid intersections Gemini and ground truth agree on.
- Any grid intersection ground truth has but Gemini missed shows as a red dashed circle; clicking it turns it solid green and logs `toggled <ref>` to the browser console (open DevTools to confirm).
- The summary table below lists every grid_ref with its match status, and the count line (e.g. "11/12 columns matched") matches what's visible in the diagram.

- [ ] **Step 4: Commit**

```bash
git add tools/gemini_overlay_prototype/render_overlay.py tools/gemini_overlay_prototype/output/
git commit -m "Add overlay + summary table renderer for Gemini extraction prototype"
```
