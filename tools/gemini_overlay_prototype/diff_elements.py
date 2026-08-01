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
