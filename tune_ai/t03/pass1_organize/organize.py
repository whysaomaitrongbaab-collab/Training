#!/usr/bin/env python3
"""
pass1_organize/organize.py — t03 Pass 1: จัดระเบียบไฟล์ก่อนเข้า pass 2/3

ไม่ใช้ AI เลย อ่านผลจาก pass 0 (บอกว่าแต่ละหน้าเป็น subtask อะไร มีกี่ view อยู่ตรงไหน)
แล้ว (1) ตัดรูปหน้าที่มีหลาย view ออกเป็นรูปละ view (2) แตกลงโฟลเดอร์ตาม subtask
(3) เขียน manifest.json บอกว่าโฟลเดอร์นั้นต้องการอะไรบ้าง (เลข pass ตาม pass_design_v2.md)

ทำไมต้องตัดรูปจริง ไม่ใช่แค่สั่งโมเดลว่า "อ่านเฉพาะผังคาน":
visual token ล็อกไว้ที่ 5120/รูป (เท่าตอนเทรน ห้ามเปลี่ยน) — ส่งเต็มหน้า token กระจายทั้งแผ่น
ตัดครึ่งมา token เท่าเดิมกระจุกอยู่ครึ่งเดียว = ความละเอียดที่โมเดลเห็นเพิ่มเท่าตัว

กติกา "ไม่เดา" (เหมือนทั้งโปรเจกต์): ตัดแล้วได้จำนวนช่องไม่ตรงกับที่ pass 0 บอก
→ ส่งเต็มหน้าไปแทน + ติดธง ไม่ตัดมั่ว

    python3 pass1_organize/organize.py --pass0 pass0_08.json --images-root image/ --out work/
"""
import argparse, json, shutil, sys
from pathlib import Path

import cv2
import numpy as np

# subtask → pass ไหน (ตรงกับ pass_design.csv)
PASS_OF = {
    # pass 2 — Constistant ใช้จริง
    "gridline": 2, "plan_footing": 2, "plan_column": 2, "plan_beam": 2, "plan_slab": 2,
    "section": 2, "schedule": 2, "notes": 2, "material_list": 2, "soil_boring_log": 2,
    # pass 4 — หน้ารอง ถอดเก็บไว้ ยังไม่มีใครอ่าน (เลขเดิมคือ 3 — เปลี่ยนตาม
    # pass_design_v2.md 2026-08-26: เลข 3 ถูกใช้เป็น pass ถอดระยะตัวใหม่แล้ว)
    "plan_architectural": 4, "plan_electrical": 4, "plan_sanitary": 4, "roof_plan": 4,
    "site_plan": 4, "side_profile": 4, "index": 4, "title": 4, "symbol": 4,
    "misc": 4, "bbs_schedule": 4,
}

# subtask ที่ต้องใช้ grid master (pass2/gridline เป็นคนสร้าง — ตอน pass1 ยังไม่มี
# จึงชี้ไปที่ _shared/ ไม่ก็อปเข้าทุกโฟลเดอร์ ตัวรันเช็ค needs ว่ามีครบก่อนค่อยยิง)
NEEDS_GRID = {"plan_footing", "plan_column", "plan_beam", "plan_slab",
              "plan_architectural", "plan_electrical", "plan_sanitary",
              "roof_plan", "site_plan", "side_profile"}

# คำบอกตำแหน่ง view ที่ pass 0 ใช้ได้ → (แกนที่ตัด, ลำดับ)
ROW_WORDS = ["top", "middle", "bottom"]      # ตัดแนวนอน เรียงบน→ล่าง
COL_WORDS = ["left", "center", "right"]      # ตัดแนวตั้ง เรียงซ้าย→ขวา

PAD_FRAC = 0.02        # เผื่อขอบรอบ crop — กันเลขกริด ①②③ / ⒶⒷⒸ ที่อยู่ริมสุดหลุด
MIN_AREA_FRAC = 0.06   # crop ที่เล็กกว่านี้ถือว่าตัดพลาด ไม่ใช่ view จริง
RULE_FRAC = 0.55       # เส้นจะนับเป็น "เส้นแบ่ง" ต้องยาวเกินสัดส่วนนี้ของด้านนั้น
EDGE_SKIP = 0.10       # ข้ามเส้นที่อยู่ใกล้ขอบเกินไป (คือกรอบนอกของแผ่น ไม่ใช่เส้นแบ่ง)


def binarize(img_path):
    """อ่านรูปเป็นขาวดำ (255 = มีหมึก) — รองรับ path ภาษาไทยด้วย np.fromfile"""
    buf = np.fromfile(str(img_path), dtype=np.uint8)
    gray = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise IOError(f"อ่านรูปไม่ได้: {img_path}")
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]


def strip_title_block(ink):
    """
    ตัดแถบ title block ทางขวาออก (ชุดแบบราชการมีทุกแผ่น) — หาเส้นตั้งเข้มในโซนขวา
    ที่ตัดแล้วยังเหลือเนื้อที่ซ้าย > 55% ถ้าไม่เจอก็คืนความกว้างเต็ม (ไม่เดา)
    คืน x ที่จะตัด
    """
    h, w = ink.shape
    col_ink = (ink > 0).sum(axis=0)
    for x in range(w - 1, int(w * 0.55), -1):
        if col_ink[x] > h * RULE_FRAC:
            return x
    return w


def find_dividers(ink, axis, n_parts, lo, hi):
    """
    หาเส้นแบ่ง n_parts-1 เส้นในช่วง [lo, hi) ตามแกนที่ระบุ
    axis 0 = แบ่งตามแนวนอน (หาเส้นนอน), axis 1 = แบ่งตามแนวตั้ง
    คืน list ตำแหน่ง หรือ None ถ้าหาไม่ครบ (ห้ามเดา)
    """
    if n_parts < 2:
        return []
    span = ink.shape[1] if axis == 0 else ink.shape[0]
    profile = (ink > 0).sum(axis=1 - axis)

    # ตำแหน่งที่หมึกยาวพอจะเป็นเส้นกรอบ/เส้นแบ่ง
    is_rule = profile > span * RULE_FRAC
    margin = int((hi - lo) * EDGE_SKIP)
    lo_ok, hi_ok = lo + margin, hi - margin

    # ยุบเส้นหนาหลาย pixel ให้เหลือตำแหน่งเดียว (จุดกึ่งกลางของแต่ละกลุ่ม)
    groups, start = [], None
    for i in range(lo_ok, hi_ok):
        if is_rule[i] and start is None:
            start = i
        elif not is_rule[i] and start is not None:
            groups.append((start + i - 1) // 2)
            start = None
    if start is not None:
        groups.append((start + hi_ok - 1) // 2)

    if len(groups) < n_parts - 1:
        return None

    # เลือกเส้นที่แบ่งได้ "ใกล้เคียงเท่า ๆ กัน" ที่สุด — view บนแผ่นแบบมักกินพื้นที่พอกัน
    # (ไม่ได้แปลว่าต้องเท่ากันเป๊ะ แค่ใช้เป็นตัวตัดสินเวลามีเส้นให้เลือกหลายเส้น)
    targets = [lo + (hi - lo) * k / n_parts for k in range(1, n_parts)]
    chosen = []
    pool = list(groups)
    for t in targets:
        best = min(pool, key=lambda g: abs(g - t))
        chosen.append(best)
        pool.remove(best)
    chosen.sort()

    # เส้นที่เลือกต้องเรียงและห่างกันจริง ไม่ใช่เส้นชิดกันสองเส้นในกลุ่มเดียว
    bounds = [lo] + chosen + [hi]
    if any(bounds[i + 1] - bounds[i] < (hi - lo) * MIN_AREA_FRAC for i in range(len(bounds) - 1)):
        return None
    return chosen


def cut_views(img_path, wheres):
    """
    ตัดหน้าเป็นรูปละ view ตามคำบอกตำแหน่งจาก pass 0
    คืน (list ของ box (x0,y0,x1,y1) เรียงตรงกับ wheres, เหตุผลถ้าตัดไม่ได้)
    """
    ink = binarize(img_path)
    h, w = ink.shape
    x_end = strip_title_block(ink)

    if len(wheres) == 1:
        return [(0, 0, x_end, h)], None

    lowered = [str(s).lower() for s in wheres]
    if all(s in ROW_WORDS for s in lowered):
        axis, order = 0, ROW_WORDS
    elif all(s in COL_WORDS for s in lowered):
        axis, order = 1, COL_WORDS
    else:
        return None, f"คำบอกตำแหน่งปนกันหรือไม่รู้จัก: {wheres} — รองรับแค่แบ่งแถวหรือแบ่งคอลัมน์อย่างเดียว"

    n = len(wheres)
    dividers = find_dividers(ink, axis, n, 0, h if axis == 0 else x_end)
    if dividers is None:
        return None, f"หาเส้นแบ่ง {n - 1} เส้นไม่เจอ (pass 0 บอกว่ามี {n} view)"

    edges = [0] + dividers + [h if axis == 0 else x_end]
    cells = []
    for i in range(n):
        a, b = edges[i], edges[i + 1]
        cells.append((0, a, x_end, b) if axis == 0 else (a, 0, b, h))

    # เรียง cell ตามลำดับที่ pass 0 บอก (top→bottom / left→right)
    rank = {s: order.index(s) for s in lowered}
    boxes = [None] * n
    for cell, slot in zip(cells, sorted(range(n), key=lambda i: rank[lowered[i]])):
        boxes[slot] = cell

    # เผื่อขอบกันเลขกริดหลุด
    pad = int(min(h, w) * PAD_FRAC)
    padded = []
    for (x0, y0, x1, y1) in boxes:
        padded.append((max(0, x0 - pad), max(0, y0 - pad),
                       min(x_end, x1 + pad), min(h, y1 + pad)))

    page_area = h * w
    if any((b[2] - b[0]) * (b[3] - b[1]) < page_area * MIN_AREA_FRAC for b in padded):
        return None, "มี crop เล็กผิดปกติ — น่าจะตัดผิดเส้น"
    return padded, None


def save_crop(img_path, box, dst):
    buf = np.fromfile(str(img_path), dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    x0, y0, x1, y1 = box
    ok, enc = cv2.imencode(".png", img[y0:y1, x0:x1])
    if not ok:
        raise IOError(f"encode crop ไม่สำเร็จ: {dst}")
    enc.tofile(str(dst))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass0", required=True, help="ไฟล์ผลลัพธ์ pass 0 (.json)")
    ap.add_argument("--images-root", required=True, help="โฟลเดอร์ที่มีรูปหน้าแบบ")
    ap.add_argument("--out", required=True, help="โฟลเดอร์ปลายทาง (สร้าง <out>/<house>/ ให้)")
    args = ap.parse_args()

    p0 = json.loads(Path(args.pass0).read_text(encoding="utf-8"))
    house = p0["house"]
    images_root = Path(args.images_root)
    root = Path(args.out) / house

    shared = root / "_shared"
    shared.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.pass0, shared / "pass0.json")

    buckets = {}   # subtask -> list ของ entry
    flags = []

    for page in p0["pages"]:
        img_path = images_root / page["image"]
        if not img_path.exists():
            flags.append(f"หน้า {page['png']}: ไม่พบไฟล์รูป {page['image']} — ข้ามทั้งหน้า")
            continue

        views = page["views"]
        wheres = [v.get("where", "full") for v in views]
        boxes, why = cut_views(img_path, wheres) if len(views) > 1 else ([None], None)

        if boxes is None:
            # ไม่เดา: ส่งเต็มหน้าให้ทุก view แล้วติดธงไว้ให้คนมาดู
            flags.append(f"หน้า {page['png']}: ตัดไม่สำเร็จ ({why}) — ส่งเต็มหน้าแทน")
            boxes = [None] * len(views)

        for i, (view, box) in enumerate(zip(views, boxes), start=1):
            subtask = view["subtask"]
            if subtask not in PASS_OF:
                flags.append(f"หน้า {page['png']} view {i}: ไม่รู้จัก subtask '{subtask}' — ข้าม")
                continue

            dst_dir = root / f"pass{PASS_OF[subtask]}" / subtask / "images"
            dst_dir.mkdir(parents=True, exist_ok=True)
            stem = Path(page["image"]).stem
            name = f"{stem}.png" if box is None and len(views) == 1 else f"{stem}_view{i}.png"
            dst = dst_dir / name

            if box is None:
                shutil.copy2(img_path, dst)
            else:
                save_crop(img_path, box, dst)

            entry = {
                "image": f"images/{name}",
                "png": page["png"],
                # title block อยู่นอกทุก view — crop จึงไม่มีข้อมูลนี้ ต้องส่งเป็นข้อความไปด้วย
                # (pass 0 อ่านมาแล้ว) ไม่ใช่หวังให้โมเดลหาเจอในรูปที่ตัดมา
                "sheet_code": page.get("sheet_code"),
                "sheet_name": page.get("sheet_name"),
                "building": page.get("building", "main"),
                "cropped": box is not None,
            }
            buckets.setdefault(subtask, []).append(entry)

            # view นี้มีเส้นกริดพิมพ์อยู่ด้วย → ส่งเข้า gridline เป็นแหล่งสำรอง
            # (บ้านที่ไม่มีหน้า gridline เฉพาะ ต้องอ่านกริดจากผัง/รูปด้านแทน)
            if view.get("also_gridline"):
                gdir = root / "pass2" / "gridline" / "images"
                gdir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, gdir / name)
                buckets.setdefault("gridline", []).append({**entry, "image": f"images/{name}"})

    for subtask, entries in sorted(buckets.items()):
        d = root / f"pass{PASS_OF[subtask]}" / subtask
        manifest = {
            "subtask": subtask,
            "pass": PASS_OF[subtask],
            "house": house,
            "buildings": sorted({e["building"] for e in entries}),
            "needs": ["_shared/gridmaster.json"] if subtask in NEEDS_GRID else [],
            "sources": entries,
        }
        (d / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {subtask:22s} {len(entries):3d} รูป  → pass{PASS_OF[subtask]}/")

    if flags:
        (shared / "pass1_flags.json").write_text(
            json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n⚠️  {len(flags)} เรื่องต้องดูด้วยตา — {shared / 'pass1_flags.json'}")
        for f in flags:
            print(f"   - {f}")

    print(f"\nเสร็จ → {root}")


if __name__ == "__main__":
    sys.exit(main())
