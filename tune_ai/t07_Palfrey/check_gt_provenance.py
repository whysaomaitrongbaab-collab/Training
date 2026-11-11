#!/usr/bin/env python3
"""check_gt_provenance.py - how well can the ground-truth grid masters be cut into page-by-page rows? (read-only)

Written 2026-11-11 (t07 page-by-page gridline). It reproduces the numbers the workmen's diary and PROMPTS_t07.md quote
BEFORE the builder runs; the numbers AFTER the cut (rows, replay, renumbering) are in build_report.md.

    python check_gt_provenance.py

For every grid master (json_แก้ไขแล้ว/ first, else rawjson_ยังไม่ได้แก้ไขโดนคน/, same house set as build_t07.py):
  * masters with / without `dimension_chains`
  * chain arithmetic: |pos(to) - pos(from)| vs the printed value_m of every segment whose two ends are known lines
    (a mismatch above 0.011 m is counted) - does the printed dimension row really give the position?
  * provenance: a line is "justified" when some dimension row on a page that has an image names it as an end;
    the rest are counted as unjustified, split into dummy/named and "a plan element uses that id" (those are the lines
    the old prompt told the model to measure by proportion)
  * naming rule: does grid_incremental.reprime() reproduce the GT ids (spec section 4: primes in reading order)?
Read-only on json_แก้ไขแล้ว/, rawjson_ยังไม่ได้แก้ไขโดนคน/ and image/ (only existence of page images is checked).
"""
import json
import re
import sys
from collections import Counter

sys.dont_write_bytecode = True
import build_t07 as B  # noqa: E402
import grid_incremental as G  # noqa: E402


def plan_ref_tokens(doc):
    toks = set()
    for e in doc.get("elements") or []:
        if not isinstance(e, dict):
            continue
        refs = [e.get(k) for k in ("grid_ref_start", "grid_ref_end", "grid_ref")] + list(e.get("grid_refs") or [])
        for v in refs:
            if isinstance(v, str):
                toks.update(t for t in re.split(r"-", v) if t)
    return toks


def main():
    houses, _, _, _ = B.enumerate_houses(set())
    T = Counter()
    keyset = lambda ls: {(l["id"], round(l["pos_m"], 3), l["type"]) for l in ls}  # noqa: E731
    for bare, h in houses.items():
        docs = []
        for name in h["files"]:
            try:
                doc = json.loads((h["dir"] / name).read_text(encoding="utf-8"))
            except ValueError:
                T["files_not_json"] += 1
                continue
            if isinstance(doc, dict):
                docs.append((name, doc))
        plan_refs = set()
        for _, doc in docs:
            if doc.get("pattern") in B.PLAN_PATTERNS:
                plan_refs |= plan_ref_tokens(doc)
        for name, doc in docs:
            if doc.get("pattern") not in ("grid_master", "gridline"):
                continue
            T["masters"] += 1
            g = doc.get("grid") or {}
            lines = {ax: B.slim_lines(g.get(k), Counter()) for ax, k in (("x", "x_lines"), ("y", "y_lines"))}
            if all(keyset(G.reprime(lines[ax])) == keyset(lines[ax]) for ax in "xy"):
                T["masters_ids_follow_the_naming_rule"] += 1
            else:
                T["masters_ids_do_not_follow_the_naming_rule"] += 1
            chains = g.get("dimension_chains") if isinstance(g.get("dimension_chains"), list) else []
            if not chains:
                T["masters_without_dimension_chains"] += 1
                continue
            T["masters_with_dimension_chains"] += 1
            pos = {(ax, l["id"]): (l["pos_m"], l["type"]) for ax in "xy" for l in lines[ax]}
            named_on_a_page = set()
            for c in chains:
                ax = c.get("axis")
                src = c.get("source_image")
                pk = B.page_key(src) if isinstance(src, str) else None
                if ax not in ("x", "y"):
                    continue
                for s in c.get("segments") or []:
                    a, b, v = s.get("from"), s.get("to"), s.get("value_m")
                    if pk and (B.TR / B.page_png(bare, pk)).exists():
                        named_on_a_page.update((ax, e) for e in (a, b) if isinstance(e, str) and e != "edge")
                    if (ax, a) in pos and (ax, b) in pos and isinstance(v, (int, float)):
                        T["chain_segments_checkable"] += 1
                        if abs(abs(pos[(ax, b)][0] - pos[(ax, a)][0]) - abs(v)) > 0.011:
                            T["chain_segments_position_mismatch"] += 1
            for (ax, i), (p, t) in pos.items():
                if (ax, i) in named_on_a_page:
                    T["lines_justified_by_a_page"] += 1
                else:
                    T["lines_unjustified"] += 1
                    T["lines_unjustified_" + t] += 1
                    T["unjustified_but_a_plan_element_uses_the_id" if i in plan_refs else "unjustified_and_unused"] += 1
    for k, v in sorted(T.items()):
        print(f"{k:55s} {v}")


if __name__ == "__main__":
    main()
