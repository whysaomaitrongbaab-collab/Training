import json, glob, sys
from pathlib import Path
TRAINING = Path(__file__).resolve().parent.parent.parent
h, pk = sys.argv[1], sys.argv[2]
gtd = next(p for p in (TRAINING / "json_แก้ไขแล้ว").iterdir() if p.name.endswith(h))
for fp in sorted(gtd.glob(f"*หน้า{pk}_*.json")) + sorted(gtd.glob(f"*หน้า{pk}.json")):
    d = json.load(open(fp, encoding="utf-8"))
    els = list(d.get("elements") or [])
    for v in d.get("views") or []:
        els += v.get("elements") or []
    print(f"== {fp.name} pattern={d.get('pattern')}")
    for e in els:
        ex = f" | {e.get('grid_ref_start')}->{e.get('grid_ref_end')}" if e.get("grid_ref_start") else ""
        print(f"  {e.get('element_id')} | {e.get('element_type')} | count {e.get('count') or 1} | refs {e.get('grid_refs')}{ex}")
cvp = TRAINING / "image" / h / f"{h}_หน้า{pk}_cv25.json"
if cvp.exists():
    d = json.load(open(cvp, encoding="utf-8"))
    print("== CV:", " ".join(f"{b['n']}){b['class']}" for b in d["elements"]))
