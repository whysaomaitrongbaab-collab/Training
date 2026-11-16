#!/usr/bin/env python3
"""export_floor_z.py - per house: the floors its structural plans name + the printed levels of its grid master (read-only)

Feeds Constistant's `dev/floor-levels/report-gt.mjs`, which runs the web's own matching (`js/shared/floor-levels.js`) and
writes the review table `docs/research/2026-11-11-floor-levels-from-z-review.md`. Same house set as build_t07.py.

    python export_floor_z.py <out.json>
"""
import json
import re
import sys

sys.dont_write_bytecode = True
import build_t07 as B  # noqa: E402

ROOF = {"roof": "RF", "R": "RF", "ROOF": "RF"}


def main(out_path):
    houses, _, _, _ = B.enumerate_houses(set())
    out = []
    for bare, h in houses.items():
        floors, z, masters = set(), [], 0
        for name in h["files"]:
            try:
                d = json.loads((h["dir"] / name).read_text(encoding="utf-8"))
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            if d.get("pattern") in B.PLAN_PATTERNS and d.get("discipline") == "structural":
                f = d.get("floor_level")
                if isinstance(f, str):
                    f = ROOF.get(f, f)
                    if re.fullmatch(r"F\d+|RF", f):
                        floors.add(f)
            if d.get("pattern") in ("grid_master", "gridline"):
                masters += 1
                for e in (d.get("grid") or {}).get("z_levels") or []:
                    if isinstance(e, dict):
                        z.append({"id": e.get("id"), "level_m": e.get("level_m"), "type": e.get("type")})
        out.append({"house": bare, "tree": h["tree"], "floors": sorted(floors), "z_levels": z, "masters": masters})
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print(f"houses {len(out)} · with plan floors {sum(1 for o in out if o['floors'])} · with z {sum(1 for o in out if o['z_levels'])}")


if __name__ == "__main__":
    main(sys.argv[1])
