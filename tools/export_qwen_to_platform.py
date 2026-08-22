#!/usr/bin/env python3
"""export_qwen_to_platform.py — แปลงผล inference ของ Qwen (t02) ให้ Constistant นำเข้าได้

ผลดิบจาก run_house_batch.py มีรูปเป็น {ok, parsed, raw_text, grammar} และตัว parsed
เก็บ pattern/elements ไว้ "ข้างใน views[]" แต่ adapter ฝั่งแพลตฟอร์ม
(js/drawing/raw-extraction-adapter.js) อ่าน f.pattern และ f.elements ที่ "ระดับไฟล์"
สคริปต์นี้แค่แบน views ออกมาเป็นไฟล์ละ view ตามธรรมเนียม _view1_/_view2_ ของ
ground truth แล้วเติม wrapper field ที่ §2 บังคับให้ครบ

หลักการเดียว: ไม่แต่งข้อมูล — เนื้อ element คัดลอกดิบทุกตัวอักษร ตัวที่ใช้ไม่ได้จะ
"รายงาน" ไม่ใช่ "ซ่อม" ค่าที่เติมเพิ่มมีแค่ wrapper field ที่ขาดและระบุที่มาไว้ใน
warnings ของไฟล์นั้นเสมอ

    python tools/export_qwen_to_platform.py "tune_ai/t02/ผล/09บ้าน_เล็ก_1ชั้น_04" \
        --grid-master "json_แก้ไขแล้ว/09บ้าน_เล็ก_1ชั้น_04/บ้าน_เล็ก_1ชั้น_04_หน้า00_gridline.json"
"""
import argparse
import json
import re
import shutil
from pathlib import Path

# pattern ที่ adapter ฝั่ง Constistant แปลงเป็น entity ได้จริง (ADAPTED_PATTERNS)
ADAPTED = {"plan", "section", "schedule", "notes", "gridline", "material_list"}
WRAPPER_DEFAULTS = {"discipline": None, "sheet_code": None, "sheet_name": None,
                    "confidence_score": None, "confidence_flags": [], "warnings": []}


def floor_from(title, sheet_name):
    """อ่านชั้นจากหัวแบบ — ไม่เจอคืน None (ห้ามเดาเป็น F1 ตามสเปก)"""
    text = f"{title or ''} {sheet_name or ''}"
    if re.search(r"หลังคา|roof", text, re.I):
        return "RF"
    m = re.search(r"ชั้น\s*(?:ที่\s*)?([๑-๙0-9]|หนึ่ง|สอง|ล่าง|บน)", text)
    if not m:
        return None
    tok = m.group(1)
    return {"๑": "F1", "1": "F1", "หนึ่ง": "F1", "ล่าง": "F1",
            "๒": "F2", "2": "F2", "สอง": "F2", "บน": "F2"}.get(tok)


def convert(src_dir: Path, out_dir: Path, grid_master: Path | None, fix_roof: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"files_written": [], "elements_kept": 0, "elements_dropped": 0,
              "notes": [], "not_adapted": []}

    for src in sorted(src_dir.glob("*.json")):
        if src.name.startswith("_"):
            continue
        doc = json.loads(src.read_text(encoding="utf-8"))
        if not doc.get("ok"):
            report["notes"].append(f"{src.name}: ok=false (JSON พังตั้งแต่ตอน infer) — ข้าม")
            continue
        parsed = doc.get("parsed")
        if not isinstance(parsed, dict):
            report["notes"].append(f"{src.name}: parsed ไม่ใช่ object — ข้าม")
            continue

        views = parsed.get("views")
        views = views if isinstance(views, list) else [parsed]
        multi = len(views) > 1

        for i, view in enumerate(views, 1):
            if not isinstance(view, dict):
                report["notes"].append(f"{src.name}: view #{i} ไม่ใช่ object — ข้าม")
                continue

            out = {k: v for k, v in parsed.items() if k != "views"}
            gen_warn = []

            pattern = view.get("pattern") or parsed.get("pattern")
            if fix_roof and pattern == "roof_plan" and \
                    re.search(r"โครงหลังคา|truss|frame", str(view.get("view_title") or ""), re.I):
                gen_warn.append("pattern เดิมจากโมเดลคือ roof_plan — เปลี่ยนเป็น plan ด้วย "
                                "--fix-roof-pattern เพราะเป็นโครงหลังคาเชิงโครงสร้าง")
                pattern = "plan"
            out["pattern"] = pattern

            for k, default in WRAPPER_DEFAULTS.items():
                if k not in out or out[k] is None:
                    if k in ("confidence_flags", "warnings"):
                        out[k] = list(default)
                    elif k == "confidence_score":
                        out[k] = view.get("confidence_score")
                    else:
                        out.setdefault(k, default)
            out["view_title"] = view.get("view_title")

            if out.get("floor_level") is None:
                fl = floor_from(view.get("view_title"), parsed.get("sheet_name"))
                out["floor_level"] = fl
                if fl:
                    gen_warn.append(f"floor_level ไม่มีในผลโมเดล — อ่านจากหัวแบบได้ '{fl}'")

            # elements: คัดลอกดิบ ตัวที่ไม่ใช่ object หรือไม่มี element_id = ใช้ไม่ได้
            kept, dropped = [], []
            for el in (view.get("elements") or []):
                if isinstance(el, dict) and el.get("element_id"):
                    kept.append(el)
                else:
                    dropped.append(el if isinstance(el, str) else type(el).__name__)
            out["elements"] = kept
            report["elements_kept"] += len(kept)
            report["elements_dropped"] += len(dropped)
            if dropped:
                gen_warn.append(f"โมเดลส่ง element ที่ใช้ไม่ได้ {len(dropped)} ตัว "
                                f"(ไม่ใช่ object หรือไม่มี element_id): {dropped[:6]}")

            for extra in ("element_count_summary", "raw_text_content", "title_block"):
                if extra in view:
                    out[extra] = view[extra]

            existing = out.get("warnings")
            out["warnings"] = (existing if isinstance(existing, list) else []) + gen_warn
            out["_provenance"] = {
                "source": "qwen t02 inference (Sicilian44/qwen3vl-30b-thai-rc)",
                "source_file": src.name,
                "human_reviewed": False,
                "note": "ผลดิบจากโมเดล ยังไม่ผ่านคนตรวจ — ห้ามใช้เป็น ground truth",
            }

            stem = src.stem + (f"_view{i}" if multi else "")
            dst = out_dir / f"{stem}.json"
            dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            report["files_written"].append(dst.name)
            if pattern not in ADAPTED:
                report["not_adapted"].append(f"{dst.name} (pattern={pattern})")

    if grid_master:
        dst = out_dir / grid_master.name
        shutil.copy2(grid_master, dst)
        report["files_written"].append(dst.name)
        report["notes"].append(
            f"grid master {grid_master.name} = ของคนทำ ไม่ใช่ผลโมเดล "
            "(รอบนี้ไม่ได้รันหน้า gridline ผ่าน Qwen) — ถ้าไม่มีไฟล์นี้ span ทุกเส้นจะ unresolved")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default=None)
    ap.add_argument("--grid-master", default=None)
    ap.add_argument("--fix-roof-pattern", action="store_true",
                    help="เปลี่ยน roof_plan ที่เป็นโครงหลังคาเชิงโครงสร้างเป็น plan (บันทึกใน warnings)")
    a = ap.parse_args()

    src = Path(a.src)
    out = Path(a.out) if a.out else src.parent.parent / "export_platform" / src.name
    r = convert(src, out, Path(a.grid_master) if a.grid_master else None, a.fix_roof_pattern)

    print(f"เขียน {len(r['files_written'])} ไฟล์ → {out}")
    print(f"elements ใช้ได้ {r['elements_kept']} · ทิ้ง {r['elements_dropped']}")
    for n in r["notes"]:
        print("  •", n)
    if r["not_adapted"]:
        print("  ⚠ แพลตฟอร์มจะไม่อ่าน (pattern นอก ADAPTED_PATTERNS):")
        for n in r["not_adapted"]:
            print("     -", n)
