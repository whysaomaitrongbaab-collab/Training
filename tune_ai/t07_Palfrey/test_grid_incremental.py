#!/usr/bin/env python3
"""hand-checked tests for grid_incremental.py (run: python test_grid_incremental.py; also run by build_t07.py --selftest)"""
import json
import sys

sys.dont_write_bytecode = True
import grid_incremental as G  # noqa: E402


def L(i, p, t="named"):
    return {"id": i, "pos_m": p, "type": t}


def run():
    # ── reprime: the spec's own example (1' -0.60, 1'' 1.10, 1''' 2.30 are ONE sequence on line 1) + direction rule
    got = G.reprime([L("1", 0.0), L("2", 5.0), L("3", 8.5), L("x", -0.6, "dummy"), L("y", 1.1, "dummy"),
                     L("z", 2.3, "dummy"), L("q", 5.2, "dummy")])
    assert [(l["id"], l["pos_m"]) for l in got] == [("1'", -0.6), ("1", 0.0), ("1''", 1.1), ("1'''", 2.3), ("2", 5.0),
                                                     ("2'", 5.2), ("3", 8.5)], got
    # direction, not nearest: 8.0 sits next to 3 (8.5) but belongs to 2
    got = G.reprime([L("2", 5.0), L("3", 8.5), L("d", 8.0, "dummy")])
    assert [l["id"] for l in got] == ["2", "2'", "3"], got
    # no named line -> dummies untouched
    assert G.reprime([L("a", 1.0, "dummy")]) == [L("a", 1.0, "dummy")]

    # ── reorigin: a named line further left becomes 0.0, dummies before it go negative
    got = G.reorigin([L("2", 0.0), L("3", 3.0), L("2'", 1.5, "dummy"), L("1", -4.0)])
    assert {(l["id"], l["pos_m"]) for l in got} == {("2", 4.0), ("3", 7.0), ("2'", 5.5), ("1", 0.0)}, got
    assert G.reorigin([L("a", 2.0, "dummy")]) == [L("a", 2.0, "dummy")]

    # ── merge_delta: out-of-order reveal renumbers everything and still lands on the final master
    s0 = G.new_state()
    s1, c1 = G.merge_delta(s0, {"x_lines": [L("2", 0.0), L("3", 3.0)], "y_lines": []})
    assert s1["x_lines"] == [L("2", 0.0), L("3", 3.0)] and c1 == {"added_named": 2}, (s1, c1)
    s2, c2 = G.merge_delta(s1, {"x_lines": [L("1", -4.0)], "y_lines": []})
    assert s2["x_lines"] == [L("1", 0.0), L("2", 4.0), L("3", 7.0)], s2
    assert c2["known_lines_renumbered"] == 2, c2                       # 2 and 3 moved

    # ── merge_delta: a dummy inserted between two known dummies re-primes the later one
    st = {"x_lines": [L("1", 0.0), L("1'", 1.0, "dummy"), L("2", 4.0)], "y_lines": [], "z_levels": []}
    got, c = G.merge_delta(st, {"x_lines": [L("1'", 0.5, "dummy")], "y_lines": []})
    assert got["x_lines"] == [L("1", 0.0), L("1'", 0.5, "dummy"), L("1''", 1.0, "dummy"), L("2", 4.0)], got
    assert c["known_lines_renumbered"] == 1, c

    # ── merge_delta: first sheet wins by id, one point = one line, junk is skipped and counted (never repaired)
    got, c = G.merge_delta(st, {"x_lines": [L("2", 9.0), L("9", 4.0), L("5", 1.0004, "dummy"), {"id": "7"},
                                           {"id": "", "pos_m": 1}, L("8", float("nan")), "x"],
                                "y_lines": "nope"})
    assert got["x_lines"] == st["x_lines"], got
    assert c == {"skipped_named_id_known": 1, "skipped_same_point": 2, "skipped_malformed": 4}, c
    assert G.merge_delta(st, None)[0] == st and G.merge_delta(st, {})[0] == st
    # levels: unknown type -> dummy, a level already known (same id and number) is skipped
    zs, c = G.merge_delta(G.new_state(), {"z_levels": [{"id": "ระดับ", "level_m": 3.75, "type": "named"},
                                                       {"id": None, "level_m": 0, "type": "floor"},
                                                       {"id": "ระดับ", "level_m": 3.75, "type": "named"},
                                                       {"id": "x", "level_m": "1"}]})
    assert zs["z_levels"] == [{"id": "ระดับ", "level_m": 3.75, "type": "named"},
                              {"id": None, "level_m": 0.0, "type": "dummy"}], zs
    assert c == {"added_level": 2, "skipped_level_known": 1, "skipped_malformed": 1}, c

    # ── tail(): exact text the worker must reproduce (z_levels only when there are some)
    assert G.tail(G.new_state()) == G.MARK + '{"grid": {"x_lines": [], "y_lines": []}}'
    assert G.tail({"x_lines": [L("1", 0.0)], "y_lines": [], "z_levels": [{"id": None, "level_m": 0.0, "type": "datum"}]}) == \
        G.MARK + '{"grid": {"x_lines": [{"id": "1", "pos_m": 0.0, "type": "named"}], "y_lines": [], ' \
                 '"z_levels": [{"id": null, "level_m": 0.0, "type": "datum"}]}}'

    # ── page order: plans first (beam, footing, roof, other), then sections/elevations, unknown last; ties by page
    pages = [("section", (5, "")), ("footing_plan", (9, "")), (None, (1, "")), ("beam_plan", (20, "")), ("beam_plan", (12, "")),
             ("plan_footing", (3, "")), ("side_profile", (2, ""))]
    assert [p[1] for p in G.page_order(pages)] == [(12, ""), (20, ""), (3, ""), (9, ""), (2, ""), (5, ""), (1, "")], G.page_order(pages)

    # ── derive_steps on a hand-made master (GT frame: leftmost named = 0)
    gt = {"x": [L("1", 0.0), L("2", 4.0), L("3", 7.0), L("3'", 7.6, "dummy"), L("9", 20.0)],
          "y": [L("D", 0.0), L("C", 4.0)]}
    steps_in = [
        {"page": "p1", "chains": [{"axis": "x", "segments": [("2", "3")]}, {"axis": "y", "segments": [("D", "C")]}]},
        {"page": "p2", "chains": [{"axis": "x", "segments": [("1", "2")]}, {"axis": "x", "segments": [("3", "3'")]}]},
        {"page": "p3", "chains": [{"axis": "x", "segments": [("9", "edge")]}]},          # touches nothing known -> adds nothing
        {"page": "p4", "chains": []},
    ]
    steps, left = G.derive_steps(steps_in, gt, {"p4": [{"id": "ระดับ", "level_m": 3.0, "type": "named"}]})
    d1, d2, d3, d4 = (s["delta"] for s in steps)
    assert d1 == {"x_lines": [L("2", 0.0), L("3", 3.0)], "y_lines": [L("D", 0.0), L("C", 4.0)], "z_levels": []}, d1
    assert d2["y_lines"] == [] and d2["z_levels"] == [], d2
    assert d2["x_lines"][0] == L("1", -4.0), d2                                         # named line left of the origin: negative
    assert d2["x_lines"][1]["id"] == "3'" and d2["x_lines"][1]["type"] == "dummy", d2   # one prime, code renumbers
    assert d2["x_lines"][1]["pos_m"] == 3.6, d2                                         # 7.6 in the OLD frame (origin was line 2 = 4.0)
    assert d3 == {"x_lines": [], "y_lines": [], "z_levels": []}, d3
    assert d4["z_levels"] == [{"id": "ระดับ", "level_m": 3.0, "type": "named"}], d4
    assert left == {"x": ["9"], "y": []}, left
    final = steps[-1]["state_after"]
    assert final["x_lines"] == [L("1", 0.0), L("2", 4.0), L("3", 7.0), L("3'", 7.6, "dummy")], final       # == GT minus line 9
    assert final["y_lines"] == [L("D", 0.0), L("C", 4.0)] and final["z_levels"] == d4["z_levels"]
    # replay with the plain merge function gives the same states (what the worker does)
    st = G.new_state()
    for s in steps:
        assert G.state_json(st) == G.state_json(s["state_before"])
        st, _ = G.merge_delta(st, s["delta"])
    assert G.state_json(st) == G.state_json(final)
    # a dummy cannot be added before its axis has a named line
    only_d = G.derive_steps([{"page": "a", "chains": [{"axis": "x", "segments": [("3'", "3''")]}]}],
                            {"x": [L("3'", 1.0, "dummy"), L("3''", 2.0, "dummy")], "y": []}, {})
    assert only_d[0][0]["delta"]["x_lines"] == [] and only_d[1]["x"] == ["3'", "3''"], only_d
    print("test_grid_incremental ok")


if __name__ == "__main__":
    run()
