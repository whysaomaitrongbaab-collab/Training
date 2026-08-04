"""
merge_raw_json_for_import.py — รวมไฟล์ raw JSON รายหน้า (101 ไฟล์ต่อบ้าน) เป็น 1 ไฟล์เดียว
สำหรับอัปโหลดเข้า Constistant ผ่านปุ่ม "นำเข้าไฟล์สกัดข้อมูล (JSON)"
(js/drawing/raw-extraction-import.js ในนั้นรองรับไฟล์เดียวที่เนื้อหาเป็น JSON array
ของหลาย page object อยู่แล้ว — ดู qt_importRawExtractionFiles(): "ไฟล์เดียวอาจเป็น
array ของหลาย view ก็ได้" — สคริปต์นี้แค่รวมไฟล์ ไม่แปลง schema เพราะ
raw-extraction-adapter.js ฝั่ง Constistant เป็นคนแปลง/join spec/grid เอง)

READ-ONLY ต่อไฟล์ต้นทาง — ไม่แก้/ไม่เขียนทับอะไรใน json_แก้ไขแล้ว/ หรือ
raw_json_ตัวที่ใช้งานจริง/ เด็ดขาด เขียนผลลัพธ์ไปที่ output dir แยกเท่านั้น
(ตาม rule_of_tune.md ข้อ 1 — raw JSON ของ raw data ห้ามแตะโดยไม่ได้รับอนุญาต
การรวมไฟล์เป็น import bundle ไม่ใช่การแก้ raw JSON ตัวจริง จึงเขียนเป็นไฟล์ใหม่แยกไว้เสมอ)

Usage:
    python tools/import_merge/merge_raw_json_for_import.py <source_dir> [--out <output_dir>]

Example:
    python tools/import_merge/merge_raw_json_for_import.py \
        "json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01"
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter

REQUIRED_WRAPPER_FIELDS = [
    "png", "doc_page", "discipline", "sheet_code", "sheet_name", "pattern",
    "confidence_score", "confidence_flags", "warnings",
]

ADAPTED_PATTERNS = {"plan", "section", "schedule", "notes", "gridline", "material_list"}


def merge_folder(source_dir, output_dir):
    if not os.path.isdir(source_dir):
        print(f"ERROR: source dir ไม่มีอยู่จริง: {source_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(glob.glob(os.path.join(source_dir, "*.json")))
    if not files:
        print(f"ERROR: ไม่พบไฟล์ .json ใน {source_dir}", file=sys.stderr)
        sys.exit(1)

    merged = []
    pattern_counts = Counter()
    problems = []
    gridline_master_count = 0
    seen_source_images = set()

    for path in files:
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                parsed = json.load(f)
        except json.JSONDecodeError as e:
            problems.append(f"{name}: invalid JSON — {e} (ข้ามไฟล์นี้)")
            continue

        # ไฟล์หนึ่งอาจเป็น object เดียว หรือ array ของหลาย view — เก็บทั้งสองแบบ
        entries = parsed if isinstance(parsed, list) else [parsed]

        for entry in entries:
            if not isinstance(entry, dict):
                problems.append(f"{name}: entry ไม่ใช่ object ({type(entry).__name__}) — ข้าม")
                continue

            missing = [k for k in REQUIRED_WRAPPER_FIELDS if k not in entry]
            if missing:
                problems.append(f"{name}: ขาด required field(s): {', '.join(missing)}")

            pattern = entry.get("pattern", "?")
            pattern_counts[pattern] += 1
            if pattern not in ADAPTED_PATTERNS:
                problems.append(
                    f"{name}: pattern '{pattern}' ไม่อยู่ใน ADAPTED_PATTERNS ของ Constistant "
                    f"(plan/section/schedule/notes/gridline/material_list) — จะถูกนำเข้าเป็น raw "
                    f"เก็บไว้เฉยๆ ไม่ถูกแปลงเป็น beam_library/drawing_element อัตโนมัติ"
                )

            if pattern == "gridline" and entry.get("source_pages"):
                gridline_master_count += 1

            si = entry.get("source_image")
            if si:
                seen_source_images.add(si)

            merged.append(entry)

    if gridline_master_count == 0:
        problems.append("ไม่พบไฟล์ grid master (pattern=gridline พร้อม source_pages) — Constistant จะไม่มี grid_references")
    elif gridline_master_count > 1:
        problems.append(f"พบไฟล์ grid master {gridline_master_count} ไฟล์ (ควรมีแค่ 1) — ตัวแรกที่เจอจะถูกใช้ ตัวอื่นถูกละไว้เฉยๆ โดยฝั่ง Constistant")

    os.makedirs(output_dir, exist_ok=True)
    house_name = os.path.basename(os.path.normpath(source_dir))
    out_path = os.path.join(output_dir, f"{house_name}_merged_for_import.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"รวมแล้ว {len(merged)} entries จาก {len(files)} ไฟล์ -> {out_path}")
    print("pattern counts:", dict(pattern_counts))
    print(f"source_image ที่ต่างกัน: {len(seen_source_images)} ค่า")
    if problems:
        print(f"\n⚠️  {len(problems)} คำเตือน:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("\nไม่มีคำเตือน — ไฟล์ครบตามที่ Constistant adapter คาดหวัง")

    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source_dir", help="โฟลเดอร์ต้นทางที่มีไฟล์ raw JSON ต่อหน้า (อ่านอย่างเดียว ไม่แก้)")
    parser.add_argument("--out", default="merged_for_import", help="โฟลเดอร์ปลายทางสำหรับไฟล์รวม (default: merged_for_import/)")
    args = parser.parse_args()
    merge_folder(args.source_dir, args.out)
