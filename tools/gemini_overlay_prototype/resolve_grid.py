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
