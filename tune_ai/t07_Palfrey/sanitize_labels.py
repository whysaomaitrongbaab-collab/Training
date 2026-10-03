#!/usr/bin/env python3
"""ล้างคำตอบที่ใช้สอน (assistant content) ก่อนเทรน t07 — ตัดของที่ "อ่านจากแบบไม่ได้"

ทำไมต้องมี (สิ่งที่ต้องแก้ ข้อ 68, ทดสอบ 3 ต.ค. 69 proof/04): คำตอบที่สอน Destrier มี path ไฟล์ที่มีชื่อบ้านเทรน
(source_image / source_pages / grid_source …) + ประวัติการแก้ข้อมูล (วันที่, "by_user", บันทึกสคริปต์ relabel)
โมเดลจำไปพ่นกับบ้านที่ไม่เคยเห็น — gridline วนนับหน้าของบ้านเทรนจนชนเพดาน 9,000 token
ไม่แตะไฟล์ GT ใน json_แก้ไขแล้ว (กฎข้อ 1) — ล้างที่ jsonl ที่ตัวสร้างชุดเทรนผลิตออกมาเท่านั้น

    python sanitize_labels.py <in.jsonl> [<in2.jsonl> ...] --out <โฟลเดอร์>   # เขียนไฟล์ชื่อเดิมลงโฟลเดอร์ใหม่
    python sanitize_labels.py <in.jsonl> ... --stats                          # นับอย่างเดียว ไม่เขียน
    python sanitize_labels.py --selftest

กติกา (ตัดสินแล้ว 3 ต.ค. — ปรับได้ แต่ต้องรัน --stats เทียบก่อน/หลังทุกครั้ง):
  1. คีย์ในชุด DROP_KEYS ถูกตัดทั้งคีย์ ทุกระดับความลึก
  2. รายการใน warnings / confidence_flags ที่เป็นประวัติการแก้ หรืออ้างบ้านอื่น ถูกตัดทีละรายการ
  3. ค่าข้อความอื่นใดที่อ้างชื่อบ้านเทรน (บ้าน_เล็ก_1ชั้น_17 / house #3) ถูกตัดทั้งคีย์/รายการ
  elements[] ไม่ถูกตัดทิ้งเป็นตัว — ตัดได้แค่คีย์ข้างในตามข้อ 1/3 (ตรวจใน selftest)
"""
import argparse
import json
import re
import sys
from pathlib import Path

DROP_KEYS = {
    "source_image", "source_pages", "grid_source", "spec_source", "same_as",
    "source_pages_used_for_this_manifest", "corresponding_sheet_in_other_variant",
    "last_updated_from_page", "last_updated_date", "schema_generation",
}
LIST_FILTER_KEYS = {"warnings", "confidence_flags"}
HOUSE = re.compile(r"บ้าน_(?:เล็ก|ใหญ่)_[12]ชั้น_\d+|\bhouse\s*#\s*\d+|\bhouses\s*#", re.I)
HISTORY = re.compile(
    r"\b20\d\d-\d\d-\d\d\b|by_user|added_by|pattern re-labelled|Nothing else in this file changed"
    r"|§\d+-upgrade|\bCORRECTED_|\bADDED_|\bin the dataset\b|previous house|this extraction session",
    re.I)


def _bad_text(s, history):
    return bool(HOUSE.search(s) or (history and HISTORY.search(s)))


def scrub(obj, st, key=None):
    """คืนสำเนาที่ล้างแล้ว · st นับสิ่งที่ตัด (ไม่แก้ obj ของผู้เรียก)"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in DROP_KEYS:
                st["drop_key"] += 1
                continue
            if isinstance(v, str) and _bad_text(v, history=False):
                st["drop_text"] += 1
                continue
            out[k] = scrub(v, st, k)
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            if isinstance(v, str) and _bad_text(v, history=key in LIST_FILTER_KEYS):
                st["drop_item"] += 1
                continue
            out.append(scrub(v, st, key))
        return out
    return obj


def _text_of(content):
    if isinstance(content, str):
        return content, None
    for i, part in enumerate(content):
        if isinstance(part, dict) and part.get("type") == "text":
            return part["text"], i
    return None, None


def sanitize_row(row, st):
    msg = row["messages"][-1]
    txt, idx = _text_of(msg["content"])
    if txt is None:
        return row
    try:
        doc = json.loads(txt)
    except Exception:
        st["not_json"] += 1
        return row
    n_el = len(doc.get("elements") or []) if isinstance(doc, dict) else None
    clean = scrub(doc, st)
    if isinstance(clean, dict) and n_el is not None:
        assert len(clean.get("elements") or []) == n_el, "ห้ามตัด element ทิ้งทั้งตัว"
    new = json.dumps(clean, ensure_ascii=False)
    st["chars_before"] += len(txt)
    st["chars_after"] += len(new)
    row = json.loads(json.dumps(row, ensure_ascii=False))
    if idx is None:
        row["messages"][-1]["content"] = new
    else:
        row["messages"][-1]["content"][idx]["text"] = new
    return row


def leak_counts(rows):
    c = {"rows": 0, "house": 0, "audit": 0, "source_key": 0}
    for r in rows:
        t, _ = _text_of(r["messages"][-1]["content"])
        t = t or ""
        c["rows"] += 1
        c["house"] += bool(HOUSE.search(t))
        c["audit"] += "Nothing else in this file changed" in t or "pattern re-labelled" in t
        c["source_key"] += '"source_image"' in t or '"source_pages"' in t
    return c


def new_stats():
    return dict.fromkeys(("drop_key", "drop_text", "drop_item", "not_json", "chars_before", "chars_after"), 0)


def selftest():
    row = {"messages": [{"role": "user", "content": "x"}, {"role": "assistant", "content": [{"type": "text", "text": json.dumps({
        "pattern": "gridline", "source_pages": ["image/บ้าน_เล็ก_1ชั้น_02/a.png"],
        "note": "unlike house #1 which had overhang", "last_updated_date": "2026-07-19",
        "grid": {"x_lines": [{"id": "1", "pos_m": 0, "source_image": "image/บ้าน_เล็ก_1ชั้น_02/b.png",
                              "confidence_flags": ["added_2026-07-16_by_user_from_page12", "edge_read_twice"]}]},
        "elements": [{"mark": "B1", "source_image": "p.png"}, {"mark": "B2"}],
        "warnings": ["pattern re-labelled 'etc_plan' -> 'beam_plan'. Nothing else in this file changed.",
                     "ระยะ 3.20 บนแบบเบลอ อ่านจากผลรวม"],
    }, ensure_ascii=False)}]}]}
    st = new_stats()
    out = sanitize_row(row, st)
    doc = json.loads(out["messages"][-1]["content"][0]["text"])
    assert "source_pages" not in doc and "last_updated_date" not in doc and "note" not in doc
    assert "source_image" not in doc["grid"]["x_lines"][0]
    assert doc["grid"]["x_lines"][0]["confidence_flags"] == ["edge_read_twice"]
    assert [e["mark"] for e in doc["elements"]] == ["B1", "B2"] and "source_image" not in doc["elements"][0]
    assert doc["warnings"] == ["ระยะ 3.20 บนแบบเบลอ อ่านจากผลรวม"], doc["warnings"]
    assert "บ้าน_เล็ก" in row["messages"][-1]["content"][0]["text"], "ต้องไม่แก้ object ของผู้เรียก"
    assert leak_counts([out]) == {"rows": 1, "house": 0, "audit": 0, "source_key": 0}
    print("selftest ok", st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.inputs or not (a.out or a.stats):
        sys.exit("ต้องใส่ไฟล์ jsonl และ --out หรือ --stats")
    for f in a.inputs:
        rows = [json.loads(line) for line in open(f, encoding="utf-8") if line.strip()]
        st = new_stats()
        clean = [sanitize_row(r, st) for r in rows]
        before, after = leak_counts(rows), leak_counts(clean)
        shrink = 1 - st["chars_after"] / st["chars_before"] if st["chars_before"] else 0
        print(f"{Path(f).name}: แถว {before['rows']} · มีชื่อบ้านเทรน {before['house']} → {after['house']} · "
              f"บันทึกสคริปต์ {before['audit']} → {after['audit']} · source_* {before['source_key']} → "
              f"{after['source_key']} · ตัดคีย์ {st['drop_key']} ข้อความ {st['drop_text']} รายการ {st['drop_item']} · "
              f"คำตอบสั้นลง {shrink:.1%} · ไม่ใช่ JSON {st['not_json']}")
        if a.out:
            Path(a.out).mkdir(parents=True, exist_ok=True)
            with open(Path(a.out) / Path(f).name, "w", encoding="utf-8") as w:
                for r in clean:
                    w.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
