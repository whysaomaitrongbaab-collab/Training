#!/usr/bin/env python3
"""grid_incremental.py - the grid master built ONE PAGE AT A TIME (t07 Palfrey, pass2 gridline)

Why (Makham, 2026-11-11): the old gridline row showed the model up to 4 pages at once and asked for the whole
master in one answer - that is where Qwen hallucinates. Now every call shows ONE page plus the lines found on
the earlier pages ("GRID SO FAR") and asks only for what THIS page adds. Page order = beam plan first, footing
plan next, then the other plans, then sections / elevations (levels).

This file is the single source of truth for the rules both sides must share (training rows built by
build_t07.py, and the worker at inference - rule_of_tune Lesson 12: the tail the model is trained on and the
tail it is given must be identical):
  * MARK / tail()            the "GRID SO FAR" text appended to the prompt
  * merge_delta()            what the CODE does with the model's reply (the model never renames, never shifts)
  * derive_steps()           how a ground-truth master is cut into page-by-page rows (training side only)

The two things the model is spared, because the spec's rules for them are mechanical (primary_rawjson_schema
section 4) and would otherwise force it to rewrite lines it already gave:
  * origin   - the leftmost NAMED line is 0.0. A later page can reveal a named line further left; the model
               writes it with a negative pos_m and merge_delta() renumbers everything.
  * primes   - a dummy takes the id of the named line on its low-pos side + primes in reading order. A later
               page can insert a dummy between two earlier ones; merge_delta() re-primes. The model writes
               "<named line>'" for every new dummy and the primes are fixed afterwards.

Pure standard library. No file or network access.
"""
import json
from collections import defaultdict

MARK = "\n\nGRID SO FAR (lines read from earlier pages of this building)\n"
EPS = 0.0005                       # two positions closer than 0.5 mm are one point (spec: compare to the millimetre)
AXES = ("x_lines", "y_lines")

# order pages are shown in: plans first (the beam plan carries the full dimension chain), then levels pages.
# keys are GT page patterns AND the worker's pass0 subtask names, so training and inference rank the same way
PAGE_CLASS_RANK = {
    "beam_plan": 0, "plan_beam": 0,
    "footing_plan": 1, "plan_footing": 1,
    "roof_frame_plan": 2,
    "etc_plan": 3, "plan": 3, "plan_slab": 3,
    "section": 4, "side_profile": 4,
}
LAST_RANK = 9


def class_rank(pattern):
    return PAGE_CLASS_RANK.get(pattern, LAST_RANK)


def page_order(pages):
    """pages = [(class_pattern_or_None, page_key)] -> same items in step order (rank, then page number)"""
    return sorted(pages, key=lambda p: (class_rank(p[0]), p[1]))


def new_state():
    return {"x_lines": [], "y_lines": [], "z_levels": []}


def _r(v):
    return round(float(v) + 0.0, 3)


def reorigin(lines):
    """leftmost named line -> 0.0 (dummies before it go negative). No named line = unchanged."""
    named = [l["pos_m"] for l in lines if l["type"] == "named"]
    if not named:
        return [dict(l) for l in lines]
    m = min(named)
    if abs(m) <= EPS:
        return [dict(l) for l in lines]
    return [{**l, "pos_m": _r(l["pos_m"] - m)} for l in lines]


def reprime(lines):
    """spec s4 dummy naming: base = the named line with the greatest pos_m <= the dummy's (direction, not nearest);
    a dummy before the first named line shares that line's sequence; primes in reading order. Result sorted by pos_m."""
    named = sorted((l for l in lines if l["type"] == "named"), key=lambda l: l["pos_m"])
    out, groups = [], defaultdict(list)
    for l in lines:
        if l["type"] != "dummy" or not named:
            out.append(dict(l))
            continue
        base = named[0]
        for n in named:
            if n["pos_m"] <= l["pos_m"] + EPS:
                base = n
        groups[base["id"]].append(l)
    for bid, ls in groups.items():
        for i, l in enumerate(sorted(ls, key=lambda l: l["pos_m"]), 1):
            out.append({**l, "id": bid + "'" * i})
    return sorted(out, key=lambda l: (l["pos_m"], l["id"]))


def _clean_line(l):
    if not isinstance(l, dict):
        return None
    pos = l.get("pos_m")
    if isinstance(pos, bool) or not isinstance(pos, (int, float)) or pos != pos or abs(pos) == float("inf"):
        return None
    lid = l.get("id")
    if not isinstance(lid, str) or not lid.strip():
        return None
    return {"id": lid, "pos_m": _r(pos), "type": "named" if l.get("type") == "named" else "dummy"}


def merge_delta(state, delta):
    """state: {"x_lines","y_lines","z_levels"} in the display frame; delta: the model's grid object (only additions).
    Returns (new_state, counters). Rules, all from the spec: a line already known by id keeps its first value; a point
    already on a line is that line; a named line left of the origin is accepted and the whole axis is renumbered;
    dummies are re-primed. Malformed entries are skipped and counted, never repaired."""
    c = defaultdict(int)
    out = {"x_lines": [], "y_lines": [], "z_levels": [dict(z) for z in state.get("z_levels", [])]}
    delta = delta if isinstance(delta, dict) else {}
    for ax in AXES:
        cur = [dict(l) for l in state.get(ax, [])]
        for raw in delta.get(ax) if isinstance(delta.get(ax), list) else []:
            l = _clean_line(raw)
            if l is None:
                c["skipped_malformed"] += 1
                continue
            if l["type"] == "named" and any(k["type"] == "named" and k["id"] == l["id"] for k in cur):
                c["skipped_named_id_known"] += 1                    # first sheet wins (spec s4)
                continue
            if any(abs(k["pos_m"] - l["pos_m"]) <= EPS for k in cur):
                c["skipped_same_point"] += 1                        # one point = one line
                continue
            cur.append(l)
            c["added_" + l["type"]] += 1
        merged = reprime(reorigin(cur))
        now = {(k["id"], k["pos_m"]) for k in merged}
        moved = sum(1 for k in state.get(ax, []) if (k["id"], k["pos_m"]) not in now)
        if moved:
            c["known_lines_renumbered"] += moved
        out[ax] = merged
    for z in delta.get("z_levels") if isinstance(delta.get("z_levels"), list) else []:
        if not (isinstance(z, dict) and isinstance(z.get("level_m"), (int, float)) and not isinstance(z.get("level_m"), bool)):
            c["skipped_malformed"] += 1
            continue
        ent = {"id": z.get("id") if isinstance(z.get("id"), str) and z.get("id").strip() else None,
               "level_m": _r(z["level_m"]), "type": z.get("type") if z.get("type") in ("datum", "named", "dummy") else "dummy"}
        if any(k["id"] == ent["id"] and abs(k["level_m"] - ent["level_m"]) <= EPS for k in out["z_levels"]):
            c["skipped_level_known"] += 1
            continue
        out["z_levels"].append(ent)
        c["added_level"] += 1
    return out, dict(c)


def state_json(state):
    """the object shown after the MARK: z_levels only when there are some (same convention as the labels)"""
    grid = {"x_lines": state["x_lines"], "y_lines": state["y_lines"]}
    if state.get("z_levels"):
        grid["z_levels"] = state["z_levels"]
    return {"grid": grid}


def tail(state):
    return MARK + json.dumps(state_json(state), ensure_ascii=False)


# ── training side: cut a ground-truth master into steps ─────────────────────────────────────────────────────
def _components(nodes, edges):
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    seen, comps = set(), []
    for n in sorted(nodes):
        if n in seen:
            continue
        comp, stack = set(), [n]
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            stack.extend(adj[u] - comp)
        seen |= comp
        comps.append(comp)
    return comps


def derive_steps(page_steps, gt_lines, levels_by_page):
    """Cut one ground-truth master into page-by-page steps.

    page_steps : [{"page": <any>, "chains": [{"axis": "x"|"y", "segments": [(from_id, to_id), ...]}]}] in STEP ORDER
    gt_lines   : {"x": [{"id","pos_m","type"}], "y": [...]}  final master, ground-truth frame (leftmost named = 0)
    levels_by_page : {page: [{"id","level_m","type"}]}  already slimmed (build_t07.slim_levels), one list per page

    A line is added at the first step whose chains connect it to what is already known (or, on an axis with nothing
    known yet, to the component holding that page's leftmost named line). That is exactly what a reader of the page
    can do: a printed dimension row that touches no known line cannot be positioned, so it adds nothing yet.
    A dummy is only added once its axis has a named line to hang off.

    Returns (steps, left_over) - each step {"page","delta","state_before","state_after"} in the DISPLAY frame
    (origin and primes as merge_delta() will produce them); left_over = {"x": [...ids], "y": [...ids]} GT lines no page added.
    """
    gt = {ax: {l["id"]: l for l in gt_lines[ax]} for ax in ("x", "y")}
    known = {"x": set(), "y": set()}
    z_known, steps = [], []
    state = new_state()
    for ps in page_steps:
        delta = {"x_lines": [], "y_lines": [], "z_levels": []}
        for ax, key in (("x", "x_lines"), ("y", "y_lines")):
            edges, nodes = [], set()
            for ch in ps["chains"]:
                if ch["axis"] != ax:
                    continue
                for a, b in ch["segments"]:
                    ok = [e for e in (a, b) if e in gt[ax]]
                    nodes.update(ok)
                    if len(ok) == 2:
                        edges.append((a, b))
            if not nodes:
                continue
            comps = _components(nodes, edges)
            if known[ax]:
                reach = set().union(*[c for c in comps if c & known[ax]]) if any(c & known[ax] for c in comps) else set()
            else:
                named = [n for n in nodes if gt[ax][n]["type"] == "named"]
                if not named:
                    continue
                anchor = min(named, key=lambda n: (gt[ax][n]["pos_m"], n))
                reach = next(c for c in comps if anchor in c)
            new_ids = sorted(reach - known[ax], key=lambda n: (gt[ax][n]["pos_m"], n))
            all_after = known[ax] | set(new_ids)
            named_after = sorted((gt[ax][i]["pos_m"], i) for i in all_after if gt[ax][i]["type"] == "named")
            if not named_after:
                continue                                           # dummies only: no named line to hang them off yet
            if known[ax]:
                kn = [gt[ax][i]["pos_m"] for i in known[ax] if gt[ax][i]["type"] == "named"]
                base = min(kn) if kn else None
            else:
                base = None
            if base is None:                                       # first named line(s) on this axis: origin = leftmost named
                base = named_after[0][0]
            for i in new_ids:
                l = gt[ax][i]
                if l["type"] == "dummy":
                    # the id this dummy would get among the lines known after this step (reading order primes are
                    # fixed by merge_delta afterwards, so the model writes one prime and the code renumbers)
                    host = named_after[0][1]
                    for p, n in named_after:
                        if p <= l["pos_m"] + EPS:
                            host = n
                    lid = gt[ax][host]["id"] + "'"
                else:
                    lid = l["id"]
                delta[key].append({"id": lid, "pos_m": _r(l["pos_m"] - base), "type": l["type"]})
            known[ax] |= set(new_ids)
        for z in levels_by_page.get(ps["page"], []):
            if not any(k["id"] == z["id"] and abs(k["level_m"] - z["level_m"]) <= EPS for k in z_known):
                z_known.append(z)
                delta["z_levels"].append(dict(z))
        before = state
        state, _ = merge_delta(before, delta)
        steps.append({"page": ps["page"], "delta": delta, "state_before": before, "state_after": state})
    left = {ax: [i for i in gt[ax] if i not in known[ax]] for ax in ("x", "y")}
    return steps, left
