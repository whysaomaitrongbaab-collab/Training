"""Render a to-scale SVG overlay + element summary table comparing a
Gemini extraction against ground truth, using grid pos_m for all
positions (no pixel/bbox data anywhere in this file).
"""
import argparse
import json
import os
import sys
from pathlib import Path

from diff_elements import diff_elements
from resolve_grid import load_gridline_master

SCALE_PX_PER_M = 40  # fixed scale factor: 1 meter of drawing = 40px on screen
MARGIN_PX = 40

ELEMENT_TYPES = ("footing", "column")


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


def _marker_svg(entry, to_px, color, dashed, label_suffix=""):
    if entry["xy"] is None:
        return ""
    x_px, y_px = to_px(entry["xy"][0], entry["xy"][1])
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


def _wrong_id_marker_svg(entry, to_px):
    label_suffix = f": expected {entry['expected_id']}, got {entry['got_id']}"
    return _marker_svg(entry, to_px, "#9b59b6", dashed=False, label_suffix=label_suffix)


def _markers_svg(to_px, all_matched, all_wrong_id, all_missed, all_hallucinated):
    return "\n".join(
        [_marker_svg(e, to_px, "#2ecc71", dashed=False) for e in all_matched]
        + [_wrong_id_marker_svg(e, to_px) for e in all_wrong_id]
        + [_marker_svg(e, to_px, "#e74c3c", dashed=True) for e in all_missed]
        + [_marker_svg(e, to_px, "#e67e22", dashed=False) for e in all_hallucinated]
    )


def _merge_element_refs(gemini_elements, truth_elements, element_type):
    """Union grid_refs per element_id for one element_type, combining the
    Gemini and ground-truth versions of that element_id so the summary
    table shows every ref either side reports for it, even when they
    disagree. Returns (ordered element_ids, {element_id: set(grid_refs)}).
    """
    refs_by_id = {}
    order = []
    for elements in (truth_elements, gemini_elements):
        for el in elements:
            if el.get("element_type") != element_type:
                continue
            eid = el.get("element_id")
            if eid not in refs_by_id:
                refs_by_id[eid] = set()
                order.append(eid)
            refs_by_id[eid].update(el.get("grid_refs", []))
    return order, refs_by_id


def _ref_status_map(diff):
    """Flatten one element_type's diff_elements() result into a single
    {grid_ref: (status, detail_text)} lookup, so table rows and markers are
    always built from the same diff result.
    """
    status = {}
    for e in diff["matched"]:
        status[e["grid_ref"]] = ("matched", e["element_id"])
    for e in diff["wrong_id"]:
        status[e["grid_ref"]] = (
            "wrong_id", f'expected {e["expected_id"]}, got {e["got_id"]}'
        )
    for e in diff["missed"]:
        status[e["grid_ref"]] = ("missed", f'missing (ground truth: {e["element_id"]})')
    for e in diff["hallucinated"]:
        status[e["grid_ref"]] = ("hallucinated", f'extra (Gemini only: {e["element_id"]})')
    return status


def _element_rows_html(gemini_elements, truth_elements, diff, element_type):
    """Build <tr> rows for the summary table for one element_type, iterating
    the actual elements lists (not the flattened diff buckets) so `count`
    and `grid_refs` reflect what each element record actually said -- but
    color/flag each row's match status using the diff computed for the same
    element_type, so the table and the SVG overlay never disagree.
    """
    order, refs_by_id = _merge_element_refs(gemini_elements, truth_elements, element_type)
    status_map = _ref_status_map(diff)
    rows = []
    for eid in order:
        refs = sorted(refs_by_id[eid])
        matched_count = 0
        detail_notes = []
        for ref in refs:
            status, detail = status_map.get(ref, ("unresolved", "unresolved grid ref"))
            if status == "matched":
                matched_count += 1
            else:
                detail_notes.append(f"{ref}: {detail}")
        total = len(refs)
        summary = f"{matched_count}/{total} matched"
        if detail_notes:
            summary += " (" + "; ".join(detail_notes) + ")"
        row_class = "matched" if matched_count == total else "mismatch"
        rows.append(
            f'<tr class="{row_class}"><td>{eid}</td><td>{element_type}</td>'
            f'<td>{total}</td><td>{", ".join(refs)}</td><td>{summary}</td></tr>'
        )
    return rows


def _summary_table_html(gemini_elements, truth_elements, footing_diff, column_diff):
    rows = (
        _element_rows_html(gemini_elements, truth_elements, footing_diff, "footing")
        + _element_rows_html(gemini_elements, truth_elements, column_diff, "column")
    )
    all_matched = len(footing_diff["matched"]) + len(column_diff["matched"])
    all_wrong_id = len(footing_diff["wrong_id"]) + len(column_diff["wrong_id"])
    all_missed = len(footing_diff["missed"]) + len(column_diff["missed"])
    total_truth = all_matched + all_wrong_id + all_missed
    return (
        f'<p>{all_matched}/{total_truth} elements matched ground truth '
        f'({all_wrong_id} wrong id, {all_missed} missed).</p>'
        f'<table border="1" cellpadding="4">'
        f'<tr><th>element_id</th><th>type</th><th>count</th><th>grid_refs</th>'
        f'<th>match vs ground truth</th></tr>'
        f'{"".join(rows)}</table>'
    )


def render(house, page):
    page_padded = page.zfill(2)
    gemini_data, truth_data, grid, footing_diff, column_diff = _load_diff_inputs(house, page_padded)

    all_matched = footing_diff["matched"] + column_diff["matched"]
    all_wrong_id = footing_diff["wrong_id"] + column_diff["wrong_id"]
    all_missed = footing_diff["missed"] + column_diff["missed"]
    all_hallucinated = footing_diff["hallucinated"] + column_diff["hallucinated"]

    all_x = list(grid["x"].values())
    all_y = list(grid["y"].values())
    min_x, max_x, min_y, max_y = min(all_x), max(all_x), min(all_y), max(all_y)

    grid_svg, width_px, height_px = _grid_svg(grid, min_x, max_x, min_y, max_y)
    to_px = lambda x_m, y_m: _to_px(x_m, y_m, min_x, min_y)
    markers_svg = _markers_svg(to_px, all_matched, all_wrong_id, all_missed, all_hallucinated)

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{house} หน้า{page_padded} overlay</title>
<style>
  .missed {{ color: #e74c3c; }}
  .hallucinated {{ color: #e67e22; }}
  .unresolved {{ color: #999; }}
  .mismatch {{ background: #fdf2ff; }}
  .marker circle {{ cursor: pointer; }}
</style></head>
<body>
<h1>{house} หน้า{page_padded} — footing/column overlay</h1>
<svg width="{width_px}" height="{height_px}">
{grid_svg}
{markers_svg}
</svg>
{_summary_table_html(gemini_data["elements"], truth_data["elements"], footing_diff, column_diff)}
<script>
function toggleMarker(circle) {{
  const isGreen = circle.getAttribute('fill') === '#2ecc71';
  circle.setAttribute('fill', isGreen ? 'none' : '#2ecc71');
  circle.setAttribute('stroke', '#2ecc71');
  console.log('toggled', circle.parentElement.dataset.ref);
}}
</script>
</body></html>"""

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{house}_หน้า{page_padded}_overlay.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"Wrote {output_path}")
    return {
        "footing": footing_diff,
        "column": column_diff,
    }


def _load_diff_inputs(house, page_padded):
    """Shared by render() and render_on_image(): loads the Gemini output,
    ground truth, and gridline master, and computes both element-type
    diffs. Returns (gemini_data, truth_data, grid, footing_diff, column_diff).
    """
    base = Path(__file__).parent.parent.parent  # repo root

    gemini_path = Path(__file__).parent / "output" / f"{house}_หน้า{page_padded}_gemini.json"
    gemini_data = json.loads(gemini_path.read_text(encoding="utf-8"))

    truth_path = (
        base / "json_แก้ไขแล้ว" / f"01{house}" / f"{house}_หน้า{page_padded}_view1_footing_plan.json"
    )
    truth_data = json.loads(truth_path.read_text(encoding="utf-8"))

    grid_path = base / "json_แก้ไขแล้ว" / f"01{house}" / f"{house}_หน้า00_gridline.json"
    grid = load_gridline_master(grid_path)

    footing_diff = diff_elements(gemini_data["elements"], truth_data["elements"], grid, "footing")
    column_diff = diff_elements(gemini_data["elements"], truth_data["elements"], grid, "column")
    return gemini_data, truth_data, grid, footing_diff, column_diff


def render_on_image(house, page, refs=None, model="models/gemini-2.5-flash", calibration_attempts=3):
    """Same diff as render(), but drawn on top of the actual scanned page
    PNG instead of a schematic grid diagram. Positions still come entirely
    from grid pos_m -- the only new input is a one-time pixel calibration
    (Gemini-read reference points, each read `calibration_attempts` times
    and median-combined since single-call reads have been observed to
    vary, then averaged by least squares across points -- see
    pixel_calibration.py) used to convert those meter positions to pixel
    positions on this one image.
    """
    from PIL import Image
    from pixel_calibration import DEFAULT_CALIBRATION_REFS, calibrate, meter_to_pixel

    refs = refs or DEFAULT_CALIBRATION_REFS
    page_padded = page.zfill(2)
    base = Path(__file__).parent.parent.parent
    gemini_data, truth_data, grid, footing_diff, column_diff = _load_diff_inputs(house, page_padded)

    image_path = base / "image" / house / f"{house}_หน้า{page_padded}.png"
    with Image.open(image_path) as im:
        img_w, img_h = im.size

    transform = calibrate(image_path, img_w, img_h, grid, refs=refs, model=model, attempts=calibration_attempts)
    to_px = lambda x_m, y_m: meter_to_pixel(x_m, y_m, transform)

    all_matched = footing_diff["matched"] + column_diff["matched"]
    all_wrong_id = footing_diff["wrong_id"] + column_diff["wrong_id"]
    all_missed = footing_diff["missed"] + column_diff["missed"]
    all_hallucinated = footing_diff["hallucinated"] + column_diff["hallucinated"]
    markers_svg = _markers_svg(to_px, all_matched, all_wrong_id, all_missed, all_hallucinated)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{house}_หน้า{page_padded}_overlay_on_image.html"
    image_href = os.path.relpath(image_path, output_dir).replace(os.sep, "/")

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{house} หน้า{page_padded} overlay on image</title>
<style>
  .missed {{ color: #e74c3c; }}
  .hallucinated {{ color: #e67e22; }}
  .unresolved {{ color: #999; }}
  .mismatch {{ background: #fdf2ff; }}
  .marker circle {{ cursor: pointer; }}
</style></head>
<body>
<h1>{house} หน้า{page_padded} — footing/column overlay on real drawing</h1>
<p>Calibrated from {", ".join(refs)} (model: {model}).</p>
<svg width="{img_w}" height="{img_h}">
<image href="{image_href}" x="0" y="0" width="{img_w}" height="{img_h}"/>
{markers_svg}
</svg>
{_summary_table_html(gemini_data["elements"], truth_data["elements"], footing_diff, column_diff)}
<script>
function toggleMarker(circle) {{
  const isGreen = circle.getAttribute('fill') === '#2ecc71';
  circle.setAttribute('fill', isGreen ? 'none' : '#2ecc71');
  circle.setAttribute('stroke', '#2ecc71');
  console.log('toggled', circle.parentElement.dataset.ref);
}}
</script>
</body></html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"Wrote {output_path}")
    return {"footing": footing_diff, "column": column_diff, "transform": transform}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--house", required=True)
    parser.add_argument("--page", required=True)
    parser.add_argument(
        "--on-image", action="store_true",
        help="Draw markers on the real scanned page PNG instead of a schematic grid diagram",
    )
    parser.add_argument(
        "--refs", default=None,
        help='Comma-separated pixel-calibration grid_refs, e.g. "D1,D3,A1,A3" (--on-image only; default: 4 grid corners)',
    )
    parser.add_argument("--model", default="models/gemini-2.5-flash", help="Gemini model for pixel calibration (--on-image only)")
    args = parser.parse_args()
    if args.on_image:
        refs = args.refs.split(",") if args.refs else None
        render_on_image(args.house, args.page, refs=refs, model=args.model)
    else:
        render(args.house, args.page)


def _self_check():
    # Inline synthetic grid + gemini/ground-truth elements covering all 5
    # diff_elements() categories, exercised directly against the internal
    # rendering helpers (not render()/main(), which need real files on disk).
    grid = {
        "x": {"1": 0.0, "2": 4.0, "3": 7.0},
        "y": {"D": 0.0, "C": 4.0, "B": 6.0},
    }
    truth_elements = [
        {"element_id": "F1", "element_type": "footing", "grid_refs": ["D1", "D2", "C1"]},
        {"element_id": "F2", "element_type": "footing", "grid_refs": ["C2"]},
        {"element_id": "C1", "element_type": "column", "grid_refs": ["D1", "D2", "C1", "C2"]},
    ]
    gemini_elements = [
        # D1 matched, D2 missed (Gemini didn't report it), C1 wrong_id
        # (reported as "F2" instead of "F1"), plus a hallucinated extra
        # ref "B1" (resolves against the inline grid above, but isn't in
        # ground truth at all).
        {"element_id": "F1", "element_type": "footing", "grid_refs": ["D1"]},
        {"element_id": "F2", "element_type": "footing", "grid_refs": ["C1", "C2", "B1"]},
        {"element_id": "C1", "element_type": "column", "grid_refs": ["D1", "D2", "C1", "C2"]},
    ]

    footing_diff = diff_elements(gemini_elements, truth_elements, grid, "footing")
    column_diff = diff_elements(gemini_elements, truth_elements, grid, "column")

    assert footing_diff["matched"] == [
        {"grid_ref": "C2", "xy": (4.0, 4.0), "element_id": "F2"},
        {"grid_ref": "D1", "xy": (0.0, 0.0), "element_id": "F1"},
    ]
    assert footing_diff["wrong_id"] == [
        {"grid_ref": "C1", "xy": (0.0, 4.0), "expected_id": "F1", "got_id": "F2"}
    ]
    assert footing_diff["missed"] == [{"grid_ref": "D2", "xy": (4.0, 0.0), "element_id": "F1"}]
    assert footing_diff["hallucinated"] == [
        {"grid_ref": "B1", "xy": (0.0, 6.0), "element_id": "F2"}
    ]
    assert footing_diff["unresolved"] == []
    assert len(column_diff["matched"]) == 4

    all_matched = footing_diff["matched"] + column_diff["matched"]
    all_wrong_id = footing_diff["wrong_id"] + column_diff["wrong_id"]
    all_missed = footing_diff["missed"] + column_diff["missed"]
    all_hallucinated = footing_diff["hallucinated"] + column_diff["hallucinated"]

    identity_to_px = lambda x_m, y_m: (x_m, y_m)
    markers_svg = _markers_svg(identity_to_px, all_matched, all_wrong_id, all_missed, all_hallucinated)
    table_html = _summary_table_html(gemini_elements, truth_elements, footing_diff, column_diff)
    html = f"<html><body><svg>{markers_svg}</svg>{table_html}</body></html>"

    assert 'fill="#2ecc71"' in html  # matched marker
    assert 'stroke="#e74c3c"' in html and 'stroke-dasharray="4,3"' in html  # missed marker
    assert 'fill="#e67e22"' in html  # hallucinated marker
    assert 'fill="#9b59b6"' in html  # wrong_id marker
    assert "expected F1, got F2" in html  # wrong_id label on the marker
    assert "<th>element_id</th>" in html
    assert "<th>type</th>" in html
    assert "<th>count</th>" in html
    assert "<th>grid_refs</th>" in html
    assert "<th>match vs ground truth</th>" in html
    assert "<td>footing</td>" in html
    assert "<td>column</td>" in html
    print("render_overlay.py self-check: all assertions passed")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        _self_check()
