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
