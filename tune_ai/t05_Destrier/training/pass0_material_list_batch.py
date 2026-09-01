#!/usr/bin/env python3
"""pass0_material_list_batch.py — เติม pass0 label ให้หน้า material_list ที่วาง 2 แผ่นข้างกัน
(เอกสาร ปร.4 หมุน 90° วางคู่) ซึ่ง pass0_derive.py derive อัตโนมัติไม่ได้เพราะไม่รู้ตำแหน่ง where

กติกา "ซ้าย/ขวา" ยืนยันด้วยตาจาก 5 หน้า 5 บ้านคนละเอกสาร (เลขน้อย=ขวา เลขมาก=ซ้าย):
  บ้าน_เล็ก_1ชั้น_04 หน้า50 · บ้าน_เล็ก_2ชั้น_04 หน้า67 (warning ของ GT เขียนบอกตรง ๆ) ·
  บ้าน_เล็ก_2ชั้น_02 หน้า75 · บ้าน_เล็ก_1ชั้น_05 หน้า52 · บ้าน_เล็ก_2ชั้น_08 หน้า36
ไม่มีข้อยกเว้นสักหน้า

**sheet_code/sheet_name ต้องไม่เป็น null** (แก้ 2026-08-31 หลังมะขามทักเรื่อง OCR):
pass0/prompt.md เขียนไว้ว่าสองฟิลด์นี้ "required … the title block is cropped away before the
extraction passes see the page, so this is the only chance to capture them" และอนุญาต null
เฉพาะตอน "unreadable" พร้อมเขียน warning เท่านั้น — ของเราอ่านได้ชัด (GT มีครบทั้งสองแผ่น)
เวอร์ชันแรกตั้ง null ทั้งคู่ = สอนโมเดลให้ข้ามข้อความที่อ่านออก และหน้านั้นเสียรหัสแบบถาวร
ตอนนี้: ฟิลด์บนสุดถือแผ่น "เลขน้อย" (ครึ่งขวา = แผ่นแรกของหน้า) ส่วนแผ่นที่สองไม่ถูกทิ้ง —
เก็บไว้ใน warnings[] แบบอ่านออก เพราะ schema ของ pass0 มี sheet_code ช่องเดียวต่อหน้า
⚠️ ช่องว่างเชิง schema ที่ยังไม่ปิด: หน้าที่มี 2 แผ่นจริง ๆ ควรมี sheet_code ต่อ view
   (ต้องแก้ prompt = เปลี่ยนสัญญาของ pass0 ทั้งชุด) — ยังไม่ทำ รอเคาะ

รันซ้ำได้ (idempotent): หาหน้าเป้าหมายจาก GT ตรง ๆ ไม่พึ่งคิว แล้วเขียนทับแถวเดิมของหน้านั้น
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent.parent
GT_ROOT = TRAINING / "json_แก้ไขแล้ว"
IMG_ROOT = TRAINING / "image"

SHEET_NUM_RX = re.compile(r"(\d+)\s*/\s*(\d+)")
MARK = "batch-derived"          # ป้ายบอกว่าแถวนี้มาจากสคริปต์นี้ ใช้หาแถวเก่ามาเขียนทับ


def bare(h):
    return re.sub(r"^\d{2}", "", h)


def page_key(fname):
    m = re.search(r"หน้า(\d+[ab]?)", fname)
    return m.group(1) if m else None


def read_jsonl(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()] if p.exists() else []


def write_jsonl(p, rows):
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def find_pages():
    """หา (house, page) ที่มีไฟล์ GT pattern=material_list พอดี 2 ไฟล์ และเป็นไฟล์ทั้งหมดของหน้านั้น
    (ถ้ามีไฟล์ pattern อื่นปนอยู่ด้วย = หน้าผสม ไม่ใช่เคส 2 แผ่นข้างกัน ต้อง label มือ)"""
    out = {}
    for hd in sorted(GT_ROOT.iterdir()):
        if not (hd.is_dir() and re.match(r"^\d{2}บ้าน", hd.name)):
            continue
        pages = {}
        for fp in sorted(hd.glob("*.json")):
            pk = page_key(fp.name)
            if pk is None:
                continue
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            pages.setdefault(pk, []).append((fp, d))
        for pk, items in pages.items():
            ml = [(fp, d) for fp, d in items if d.get("pattern") == "material_list"]
            if len(items) == 2 and len(ml) == 2:
                out[(hd.name, pk)] = ml
    return out


def build_label(page, ml):
    """คืน label หรือ None ถ้าเลขแผ่นอ่านไม่ได้/ซ้ำ (ไม่เดา — ปล่อยเข้าคิวมือ)"""
    parsed = []
    for fp, d in ml:
        m = SHEET_NUM_RX.search(d.get("sheet_code") or "")
        if not m:
            return None
        parsed.append((int(m.group(1)), d))
    if parsed[0][0] == parsed[1][0]:
        return None
    parsed.sort(key=lambda x: x[0])
    (n_lo, d_lo), (n_hi, d_hi) = parsed
    return {
        "png": str(d_lo.get("png") if d_lo.get("png") is not None else page),
        "doc_page": d_lo.get("doc_page"),
        # ฟิลด์บนสุด = แผ่นเลขน้อย (ครึ่งขวา) · แผ่นที่สองอยู่ใน warnings[] ไม่ถูกทิ้ง
        "sheet_code": d_lo.get("sheet_code"),
        "sheet_name": d_lo.get("sheet_name"),
        "discipline": d_lo.get("discipline") or "material_list",
        "building": "main",
        "views": [
            {"subtask": "material_list", "where": "right", "also_gridline": False},
            {"subtask": "material_list", "where": "left", "also_gridline": False},
        ],
        "confidence_score": 0.85,   # รูปแบบเอกสารยืนยัน 5/5 หน้า แต่ไม่ได้ตรวจด้วยตาทุกหน้า
        "warnings": [
            f"หน้านี้วางเอกสาร ปร.4 สองแผ่นข้างกัน (หมุน 90°) — ครึ่งขวาคือ "
            f"{d_lo.get('sheet_code')!r} ({d_lo.get('sheet_name')!r}) ซึ่งเป็นค่าในฟิลด์ "
            f"sheet_code/sheet_name ด้านบน · ครึ่งซ้ายคือ {d_hi.get('sheet_code')!r} "
            f"({d_hi.get('sheet_name')!r}) ซึ่ง schema ของ pass0 มีช่องเดียวต่อหน้าจึงเก็บไว้ตรงนี้",
            f"{MARK}: where ซ้าย/ขวา อนุมานจากรูปแบบเอกสาร (เลขแผ่นน้อย=ขวา) ยืนยันด้วยตา 5 หน้า "
            f"จาก 5 บ้าน — หน้านี้เองยังไม่ได้ตรวจด้วยตาทีละหน้า",
        ],
    }


def main():
    labels = read_jsonl(HERE / "pass0_labels.jsonl")
    queue = read_jsonl(HERE / "pass0_manual_queue.jsonl")
    targets = find_pages()

    new_rows, skipped = [], []
    for (house, page), ml in sorted(targets.items()):
        hb = bare(house)
        img = IMG_ROOT / hb / f"{hb}_หน้า{page}.png"
        if not img.exists():
            skipped.append(f"{hb} หน้า{page}: ไม่พบภาพ")
            continue
        label = build_label(page, ml)
        if label is None:
            skipped.append(f"{hb} หน้า{page}: เลขแผ่นอ่านไม่ได้/ซ้ำ — เข้าคิวมือ")
            continue
        new_rows.append({"house": house, "page": page,
                         "image": str(img.relative_to(TRAINING)).replace("\\", "/"),
                         "status": "auto", "gt_file": "+".join(fp.name for fp, _ in ml),
                         "label": label})

    done = {(r["house"], r["page"]) for r in new_rows}
    kept = [r for r in labels if (r["house"], r["page"]) not in done]   # เขียนทับแถวเดิมของหน้าเดียวกัน
    write_jsonl(HERE / "pass0_labels.jsonl", kept + new_rows)
    write_jsonl(HERE / "pass0_manual_queue.jsonl",
                [r for r in queue if (r["house"], r["page"]) not in done])

    n_named = sum(1 for r in new_rows if r["label"]["sheet_code"])
    print(f"pass0 material_list (2 แผ่นข้างกัน): {len(new_rows)} หน้า "
          f"(เขียนทับของเดิม {len(labels) - len(kept)} หน้า)")
    print(f"  มี sheet_code จากตารางชื่อจริง: {n_named}/{len(new_rows)} หน้า")
    print(f"  pass0_labels.jsonl รวม {len(kept) + len(new_rows)} หน้า · "
          f"คิวมือเหลือ {len([r for r in queue if (r['house'], r['page']) not in done])}")
    for s in skipped[:10]:
        print("   -", s)


if __name__ == "__main__":
    main()
