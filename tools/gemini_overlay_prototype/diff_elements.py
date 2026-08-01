"""Diff a Gemini-extracted element list against ground truth, by grid_ref
AND element_id label, for one element_type at a time. Positions come from
resolve_grid (pos_m-based), never from pixel data.
"""
from resolve_grid import resolve


def _grid_ref_to_element_id(elements, element_type):
    """Flatten every element with element_type == `element_type` into a
    {grid_ref: element_id} lookup. Real files sometimes carry the same grid
    position on more than one element_id entry (rare, but grid_refs is the
    unit of truth here, not element_id) -- if that happens within one side,
    last-write-wins (whichever element comes later in the list).
    """
    lookup = {}
    for el in elements:
        if el.get("element_type") == element_type:
            element_id = el.get("element_id")
            for ref in el.get("grid_refs", []):
                lookup[ref] = element_id
    return lookup


def diff_elements(gemini_elements, ground_truth_elements, grid, element_type):
    """Diff one element_type's grid positions AND element_id labels between
    a Gemini extraction and ground truth. Returns 5 categories instead of 3:
    matched (same element_id at the same grid_ref in both), wrong_id (an
    element_id is present at the same grid_ref in both, but they disagree),
    missed (ground truth has this ref, Gemini has nothing there), hallucinated
    (Gemini has this ref, ground truth has nothing there), unresolved (either
    side's grid_ref isn't in the gridline master).
    """
    gemini_lookup = _grid_ref_to_element_id(gemini_elements, element_type)
    truth_lookup = _grid_ref_to_element_id(ground_truth_elements, element_type)

    gemini_refs = set(gemini_lookup)
    truth_refs = set(truth_lookup)

    common_refs = gemini_refs & truth_refs
    matched_refs = {ref for ref in common_refs if gemini_lookup[ref] == truth_lookup[ref]}
    wrong_id_refs = common_refs - matched_refs
    missed_refs = truth_refs - gemini_refs
    hallucinated_refs = gemini_refs - truth_refs

    all_refs = gemini_refs | truth_refs
    unresolved = sorted(ref for ref in all_refs if resolve(ref, grid) is None)

    def _entries(refs, lookup):
        return [
            {"grid_ref": ref, "xy": resolve(ref, grid), "element_id": lookup[ref]}
            for ref in sorted(refs)
        ]

    return {
        "matched": _entries(matched_refs, truth_lookup),
        "wrong_id": [
            {
                "grid_ref": ref,
                "xy": resolve(ref, grid),
                "expected_id": truth_lookup[ref],
                "got_id": gemini_lookup[ref],
            }
            for ref in sorted(wrong_id_refs)
        ],
        "missed": _entries(missed_refs, truth_lookup),
        "hallucinated": _entries(hallucinated_refs, gemini_lookup),
        "unresolved": unresolved,
    }


if __name__ == "__main__":
    from resolve_grid import load_gridline_master

    grid = load_gridline_master(
        "../../json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json"
    )
    # Real ground truth read from
    # json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า19_view1_footing_plan.json:
    # F1 (footing) has every grid point except C2; F2 (footing) has just C2;
    # C1 (column) has all 12 points.
    truth_elements = [
        {
            "element_id": "F1", "element_type": "footing",
            "grid_refs": [
                "D1", "D2", "D3", "C1", "C3", "B1", "B2", "B3", "A1", "A2", "A3"
            ],
        },
        {
            "element_id": "F2", "element_type": "footing",
            "grid_refs": ["C2"],
        },
        {
            "element_id": "C1", "element_type": "column",
            "grid_refs": [
                "D1", "D2", "D3", "C1", "C2", "C3", "B1", "B2", "B3", "A1", "A2", "A3"
            ],
        },
    ]
    # Synthetic Gemini output exercising all 5 categories:
    # - column C1: exactly right (all 12 refs) -> 12 matched
    # - footing F1: right everywhere except it reports C2 as "F1" instead of
    #   the correct "F2" (no separate F2 entry at all) -> 10 matched, 1 wrong_id
    # - "B1'" is a hallucinated extra footing ref: it resolves against this
    #   house's gridline master (y-line "B" and dummy x-line "1'" both
    #   exist), but is genuinely absent from ground truth, so it correctly
    #   lands in "hallucinated" rather than "unresolved" -- same trap Task 4's
    #   implementer hit using "E1" (which does NOT resolve, no "E" y-line on
    #   this house), per task-4-report.md.
    gemini_elements = [
        {
            "element_id": "F1", "element_type": "footing",
            "grid_refs": [
                "D1", "D2", "D3", "C1", "C2", "C3", "B1", "B2", "B3", "A1", "A2",
                "A3", "B1'",
            ],
        },
        {
            "element_id": "C1", "element_type": "column",
            "grid_refs": [
                "D1", "D2", "D3", "C1", "C2", "C3", "B1", "B2", "B3", "A1", "A2", "A3"
            ],
        },
    ]

    footing_diff = diff_elements(gemini_elements, truth_elements, grid, "footing")
    assert len(footing_diff["matched"]) == 11
    assert footing_diff["wrong_id"] == [
        {"grid_ref": "C2", "xy": (4.0, 4.0), "expected_id": "F2", "got_id": "F1"}
    ]
    assert footing_diff["missed"] == []
    assert footing_diff["hallucinated"] == [
        {"grid_ref": "B1'", "xy": (2.55, 6.0), "element_id": "F1"}
    ]
    assert footing_diff["unresolved"] == []

    column_diff = diff_elements(gemini_elements, truth_elements, grid, "column")
    assert len(column_diff["matched"]) == 12
    assert column_diff["wrong_id"] == []
    assert column_diff["missed"] == []
    assert column_diff["hallucinated"] == []
    assert column_diff["unresolved"] == []

    print("diff_elements.py self-check: all assertions passed")
