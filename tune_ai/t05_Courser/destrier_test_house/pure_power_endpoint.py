#!/usr/bin/env python3
"""pure_power_endpoint.py — วัด "กำลังดิบ" ของ destrier: ยิงภาพ + prompt แกนกลางเข้า
serve_purson.py ตรงๆ โดย **ไม่มี** pass0 บอกว่าหน้านี้เป็น subtask อะไร และ **ไม่มี**
GRID MASTER แนบ — ต่างจาก worker.py (ระบบ pass) ที่มีทั้งสองอย่าง

เทียบกับผลของระบบ pass บนหน้าเดียวกัน → ตอบว่า "ระบบ pass ช่วยจริงไหม"

เดิมทดสอบบน GPU แยก (worker_page_raw_pratyad.py) แต่โหลดแบบ vanilla PeftModel บน
MoE LoRA ช้าเกิน 25 นาที/หน้า และไม่มี repetition_penalty เลยหลุดวนจนหมด max_tokens —
ยิงผ่าน endpoint ที่เปิดอยู่แล้วได้ผลเดียวกันในเวลา ~1 นาที/หน้า

    python pure_power_endpoint.py 09 10 12
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"d:\00mk\steel project\งานสมบูรณ์\Constistant\server\purson-worker")
import worker  # noqa: E402

HOUSE = Path(r"D:\00mk\steel project\training\Training\tune_ai\t04_Purson"
             r"\test_house_new\image_บ้านแบบประหยัด1")
PROMPT = (Path(__file__).parent / "_prompt_core.txt").read_text(encoding="utf-8")
OUT = Path(__file__).parent / "results" / "pure_power_endpoint"


def main():
    pages = sys.argv[1:] or ["09", "10", "12"]
    OUT.mkdir(parents=True, exist_ok=True)
    for p in pages:
        hits = list(HOUSE.glob(f"*_หน้า{int(p):02d}.png"))
        if not hits:
            print(f"⛔ ไม่พบหน้า {p}")
            continue
        t0 = time.time()
        obj, raw = worker.call_purson([hits[0].read_bytes()], PROMPT)
        dt = time.time() - t0
        (OUT / f"page{int(p):02d}.json").write_text(raw, encoding="utf-8")
        if obj is None:
            print(f"หน้า {p}: {dt:.0f}s · JSON เสีย · ยาว {len(raw)} ตัวอักษร")
            continue
        els = obj.get("elements")
        n = len(els) if isinstance(els, list) else "-"
        print(f"หน้า {p}: {dt:.0f}s · pattern={obj.get('pattern')} · elements={n}"
              f" · sheet={obj.get('sheet_name')}")


if __name__ == "__main__":
    main()
