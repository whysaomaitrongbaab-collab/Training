#!/usr/bin/env python3
"""empty_warnings.py — ล้าง warnings[] ระดับ wrapper ของ pattern หนึ่งให้เป็น [] (ทั้งสองโฟลเดอร์)

    python tools/empty_warnings.py beam_plan            # ดูว่าจะแก้กี่ไฟล์ ไม่เขียน
    python tools/empty_warnings.py beam_plan --apply    # เขียนจริง

แก้ที่ข้อความตรงๆ เฉพาะค่าของ key "warnings" ชั้นบนสุด — การจัดหน้า/CRLF/บรรทัดอื่นไม่ขยับ
แล้วตรวจว่า parse กลับได้เท่ากับของเดิมทุกอย่างยกเว้น warnings ก่อนเขียน
key ยังอยู่ (เป็น []) เพราะสเปก §2 / check_format / prompt t07 ต้องมี key นี้
"""
import argparse
import json
from pathlib import Path

TR = Path(__file__).resolve().parent.parent
ROOTS = [TR / "json_แก้ไขแล้ว", TR / "rawjson_ยังไม่ได้แก้ไขโดนคน"]


def top_level_value_span(text, key):
    """(start, end) ของค่าของ key ชั้นบนสุด หรือ None"""
    depth, i, n = 0, 0, len(text)
    dec = json.JSONDecoder()
    while i < n:
        c = text[i]
        if c == '"':
            s, j = dec.raw_decode(text, i)          # ข้ามทั้ง string (รองรับ escape)
            if depth == 1 and s == key:
                k = j
                while text[k] in " \t\r\n":
                    k += 1
                if text[k] == ":":
                    k += 1
                    while text[k] in " \t\r\n":
                        k += 1
                    _, end = dec.raw_decode(text, k)
                    return k, end
            i = j
            continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        i += 1
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    changed = skipped = 0
    for root in ROOTS:
        for f in sorted(root.glob("*/*.json")):
            if f.parent.name.startswith("00"):
                continue
            text = f.read_bytes().decode("utf-8")
            d = json.loads(text)
            if not isinstance(d, dict) or d.get("pattern") != a.pattern or d.get("warnings") in ([], None):
                continue
            span = top_level_value_span(text, "warnings")
            if not span:
                skipped += 1
                print("ไม่เจอ warnings ชั้นบนสุด:", f)
                continue
            new = text[:span[0]] + "[]" + text[span[1]:]
            want = dict(d, warnings=[])
            got = json.loads(new)
            assert got == want and list(got) == list(want), f
            changed += 1
            if a.apply:
                f.write_bytes(new.encode("utf-8"))
    print(f"{a.pattern}: {'แก้แล้ว' if a.apply else 'จะแก้'} {changed} ไฟล์ · ข้าม {skipped}")


if __name__ == "__main__":
    main()
