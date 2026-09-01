#!/usr/bin/env python3
"""op04_run.py — รัน destrier ผ่านเส้นทาง production จริง (worker.py's subtask_prompt +
call_purson) บนหน้า 26 (plan_footing) + 27 (plan_beam) ของบ้านไทยพอเพียง3

ลำดับเหมือน run_house_extract เป๊ะ: gridline ก่อน (หน้า 26+27 เป็น grid pages) →
GRID MASTER slim → ต่อท้าย prompt ของ plan_* ทุกตัว — production-faithful:
ใช้ grid master ที่โมเดลสร้างเอง ไม่ใช่เฉลย (error ของ gridline เป็นส่วนหนึ่งของระบบที่วัด)

ต้องมี tunnel: ssh -p <PORT> root@<HOST> -L 8000:localhost:8000 -N
    python op04_run.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"d:\00mk\steel project\งานสมบูรณ์\Constistant\server\purson-worker")
import worker  # noqa: E402

HOUSE = Path(r"D:\00mk\steel project\training\Training\tune_ai\t04_Purson"
             r"\test_house_new\image_บ้านไทยพอเพียง3")
OUT = Path(__file__).parent / "results" / "op04"
TASKS = [(26, "plan_footing"), (27, "plan_beam")]
GRID_PAGES = [26, 27]  # ทั้งคู่มีกริด 1-4/A-C — worker ส่ง grid pages สูงสุด 4 หน้าเป็นภาพชุดเดียว


def png(n):
    return (HOUSE / f"บ้านไทยพอเพียง3_หน้า{n:02d}.png").read_bytes()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    timings = {}

    # gridline pass — ลำดับ/รูปแบบเดียวกับ worker.run_house_extract
    t0 = time.time()
    gm_text = None
    doc, raw = worker.call_purson([png(p) for p in GRID_PAGES], worker.subtask_prompt("gridline"))
    timings["gridline_s"] = round(time.time() - t0, 1)
    (OUT / "grid_master.raw.txt").write_text(raw, encoding="utf-8")
    if doc is None:
        print(f"gridline: JSON เสีย ({timings['gridline_s']}s) — plan_* จะไม่มี GRID MASTER แนบ (degrade แบบเดียวกับ production)")
    else:
        (OUT / "grid_master.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        grid = doc.get("grid")
        if isinstance(grid, dict):
            slim = {"grid": {k: grid.get(k) for k in ("x_lines", "y_lines") if k in grid}}
            gm_text = ("\n\nGRID MASTER (resolved axes for this building)\n"
                       + json.dumps(slim, ensure_ascii=False))
        print(f"gridline: OK {timings['gridline_s']}s · gm_text={'แนบ' if gm_text else 'ไม่มี grid dict'}")

    for page, sub in TASKS:
        prompt = worker.subtask_prompt(sub)
        if gm_text:
            prompt += gm_text  # ทั้งคู่เป็น plan_*
        t0 = time.time()
        doc, raw = worker.call_purson([png(page)], prompt)
        dt = round(time.time() - t0, 1)
        timings[f"page{page}_{sub}_s"] = dt
        (OUT / f"page_{page}_{sub}.raw.txt").write_text(raw, encoding="utf-8")
        if doc is None:
            print(f"หน้า {page} {sub}: JSON เสีย ({dt}s, ยาว {len(raw)})")
        else:
            (OUT / f"page_{page}_{sub}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
            els = doc.get("elements")
            print(f"หน้า {page} {sub}: OK {dt}s · elements={len(els) if isinstance(els, list) else '-'}")

    (OUT / "timings.json").write_text(json.dumps(timings, indent=1), encoding="utf-8")
    print("เสร็จ →", OUT)


if __name__ == "__main__":
    main()
