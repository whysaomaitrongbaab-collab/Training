#!/usr/bin/env python3
"""cv_scan.py — ตา CV ของสายพาน t03: Pass 1.5 (crop ผังราย view) และ Pass 2.5 (self-harvest)

เลข pass ตาม tune_ai/t03/pass_design_v2.md (2026-08-26):

  Pass 1.5 — รันกับ crop ที่ pass 1 (organize.py) ตัดแล้ว เฉพาะ 4 subtask ผังโครงสร้าง
             (plan_footing/plan_column/plan_beam/plan_slab) → ได้ 3 ของต่อภาพ:
               (1) JSON บัญชี element รายชิ้น มีเลขกำกับ #n คงที่ + พิกัด pixel
               (2) ภาพมาร์คเลข (Set-of-Mark, arXiv 2310.11441) — เดิมไว้ป้อน pass 2.4b
                   ซึ่งยกเลิกแล้ว (2026-08-29) ตอนนี้ใช้ให้คนตรวจด้วยตาเท่านั้น
               (3) บล็อกข้อความ hint (+กฎกันหลอน 4 ข้อ) ไว้แปะ prompt pass 2.4
  Pass 2.5 — self-harvest: เอา detection ของหน้านั้นเอง (ผ่านคลังกลางมาแล้ว) เป็น template
             แล้วกวาดซ้ำแบบเข้ม (0.90 — ไอคอนพิมพ์เดียวกันหน้าเดียวกัน match เกือบ 1.0)
             หา element ที่คลังกลางจับข้ามซีรีส์ไม่ติด
             (ทางแก้บ้าน 19 หลังที่คลังยังขาด — บ้านที่ CV หาไม่เจอเลยสักตัวยังช่วยไม่ได้ ติดธงไว้)

เลขกำกับ #n เรียง: column → footing → beam_h → beam_v, ในชนิดเรียงแถวบน→ล่าง ซ้าย→ขวา
— ต้องคงที่ข้ามรอบรัน ไม่งั้นเทียบผลระหว่างแขนทดลอง (pass 2 vs 2.4a) ไม่ได้

    python tools/cv_scan.py <ภาพ.png>              # 1 ไฟล์ → sidecar _cv.json + _marked.png + _hint.txt
    python tools/cv_scan.py <โฟลเดอร์>             # ทุก .png ในโฟลเดอร์
    python tools/cv_scan.py --manifest <workroot>  # pass 1.5 จริง: เดิน pass2/{4 ผัง}/images → เขียนลง cv/
    python tools/cv_scan.py <ภาพ> --pass25         # + self-harvest → *_cv25.json / *_marked25.png
    python tools/cv_scan.py --demo                 # self-check กับบ้าน 17

อ่านภาพอย่างเดียว ไม่แตะ GT/raw — ผลเขียนเป็นไฟล์ใหม่ข้างภาพ (หรือใน cv/) เท่านั้น
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from pattern_recognition import (imread_thai, imwrite_thai, load_templates,  # noqa: E402
                                 analyze)

# 4 subtask ที่ pass 1.5 กวาด (โฟลเดอร์จาก organize.py อยู่ใต้ pass2/ — Qwen อ่านที่ pass 2/2.4)
PLAN_SUBTASKS = ("plan_footing", "plan_column", "plan_beam", "plan_slab")
# self-harvest: seed "หลวม" (ทุก detection ที่ผ่านคลังกลางมาแล้ว — ข้ามซีรีส์ได้แค่ ~0.72-0.80
# วัดจริง 3 บ้าน 2026-08-26 ไม่มีทางถึง 0.85) แต่การกวาดซ้ำต้อง "เข้ม" 0.90 — ไอคอนพิมพ์
# เดียวกันในหน้าเดียวกัน match กันเกือบ 1.0 (วัดตอนทำ harvest_templates: 0.87-1.00)
# ห้ามกลับข้างเป็น seed เข้ม + match หลวม: นั่นคือคลาสบั๊ก HARVEST_THRESH 0.55 ที่เคยทำ
# รายงาน "44/44 ✅" ปลอมมาแล้ว
HARVEST_THRESH = 0.90
MIN_SEED_PX = 28       # กฎเดียวกับ load_templates — template เล็กกว่านี้จับมั่วแน่นอน
CLASS_ORDER = ("column", "footing", "beam_h", "beam_v")
CLASS_TH = {"column": "เสา", "footing": "ฐานราก", "beam_h": "คานแนวนอน", "beam_v": "คานแนวตั้ง"}
# สีเดียวกับ pattern_recognition.draw_marks: ฐานราก=แดง เสา=เขียว คาน=น้ำเงิน (BGR)
CLASS_BGR = {"footing": (0, 0, 255), "column": (0, 160, 0),
             "beam_h": (255, 80, 0), "beam_v": (255, 80, 0)}


# ---------- เลขกำกับคงที่ ----------

def number_elements(det):
    """[(cx,cy,w,h,score)] ราย class → [{"n","class","row","cx","cy","w","h","score"}]
    เรียง: CLASS_ORDER แล้วในชนิดจัดแถว (tolerance = 0.6 x median สูงกล่อง) บน→ล่าง ซ้าย→ขวา"""
    elements, n = [], 0
    for cls in CLASS_ORDER:
        items = det.get(cls, [])
        if cls.startswith("beam"):
            boxes = [(x + w / 2, y + h / 2, w, h, None) for x, y, w, h in items]
        else:
            boxes = [tuple(b) for b in items]
        if not boxes:
            continue
        tol = max(20, int(np.median([b[3] for b in boxes]) * 0.6))
        rows = []  # [ค่าเฉลี่ย cy, [กล่อง]]
        for b in sorted(boxes, key=lambda b: b[1]):
            for r in rows:
                if abs(b[1] - r[0]) <= tol:
                    r[1].append(b)
                    r[0] = sum(x[1] for x in r[1]) / len(r[1])
                    break
            else:
                rows.append([b[1], [b]])
        for ri, (_, rb) in enumerate(rows, 1):
            for b in sorted(rb, key=lambda b: b[0]):
                n += 1
                el = {"n": n, "class": cls, "row": ri,
                      "cx": int(b[0]), "cy": int(b[1]), "w": int(b[2]), "h": int(b[3])}
                if b[4] is not None:
                    el["score"] = round(b[4], 3)
                elements.append(el)
    return elements


# ---------- ภาพมาร์คเลข (Set-of-Mark) ----------

def draw_som_marks(gray, elements):
    """วาดกรอบ+เลข #n ลงภาพ — เลขต้องอ่านง่ายบนแบบลายเส้น: พื้นขาวหลังตัวเลขเสมอ"""
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    fs = max(0.9, gray.shape[1] / 2600)  # หน้า 3300px → ~1.27
    th_px = max(2, int(fs * 2))
    for el in elements:
        c = CLASS_BGR[el["class"]]
        x, y = el["cx"] - el["w"] // 2, el["cy"] - el["h"] // 2
        cv2.rectangle(img, (x, y), (x + el["w"], y + el["h"]), c, th_px)
        label = "#%d" % el["n"]
        (tw, tht), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, th_px)
        # ตำแหน่งป้ายเลือกให้ (1) สองป้ายที่จุดเดียวกันไม่ทับกัน (2) ไม่ทับมาร์คที่พิมพ์
        # บนแบบ — มาร์ค (เช่น F1) มักพิมพ์ "ซ้ายบน" ของไอคอน ป้ายเราจึงห้ามอยู่ซ้ายบน
        # (ทั้งสองข้อเจอจริงด้วยตา 2026-08-26: เลขเสาโดนทับ / เลข "1" ของ F1 โดนบัง)
        if el["class"] == "column":
            lx = max(0, min(x, img.shape[1] - tw - 4))
            ly = min(img.shape[0] - base - 2, y + el["h"] + tht + 6)   # ใต้กล่อง
        else:
            lx = max(0, min(x + el["w"] + 4, img.shape[1] - tw - 4))  # ขวาของกล่อง
            ly = max(tht + 4, y + tht // 2)
        cv2.rectangle(img, (lx - 2, ly - tht - 4), (lx + tw + 2, ly + base),
                      (255, 255, 255), -1)
        cv2.putText(img, label, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, fs, c, th_px,
                    cv2.LINE_AA)
    return img


# ---------- hint text สำหรับ pass 2.4 ----------

HINT_RULES_TH = """กฎการใช้ hint (สำคัญกว่าความครบ) มีดังนี้
1) hint คือสิ่งที่เครื่องเห็น ไม่ใช่คำตอบ จุดไหนอ่านป้ายบนแบบไม่ออก ใช้ชื่อบรรยาย + ติดธงใน confidence_flags ห้ามแต่งชื่อมาร์คขึ้นเอง
2) hint ไม่ใช่เพดาน เห็น element มากกว่าที่ hint บอก ให้ตอบตามที่เห็น
3) hint ไม่ใช่พื้น อ่านได้จริงน้อยกว่าที่ hint ชี้ ให้ตอบเท่าที่อ่านได้ แล้วบอกใน warnings[] ห้ามเติมให้ครบ
4) จุดที่มีกรอบแต่ไม่มีของจริง ให้บอกใน warnings[] (เครื่องตรวจภาพจับผิดได้)
ทุก element ที่ตรงกับกรอบหมายเลขไหน ให้ใส่ฟิลด์ cv_mark เป็นค่าเท่ากับเลขนั้นด้วย เช่นตรงกับกรอบหมายเลข 7 ให้ใส่ cv_mark เท่ากับ 7 (จับคู่ไม่ได้ก็ไม่ต้องใส่)"""


def _row_counts(elements, cls):
    rows = {}
    for el in elements:
        if el["class"] == cls:
            rows[el["row"]] = rows.get(el["row"], 0) + 1
    return [rows[k] for k in sorted(rows)]


def cv_hint_text(scan):
    """แปลง scan → บล็อกข้อความแปะท้าย prompt pass 2.4 (แขน 2.4a ข้อความล้วน — 2.4b ยกเลิกแล้ว)
    ไม่มีระยะ/ความยาวเด็ดขาด — ขัดกฎ 'ห้ามเดาระยะจากรูปร่างที่เห็น' (ดู pass_design_v2.md)"""
    els = scan["elements"]
    if not els:
        return ""
    lines = ["สิ่งที่เครื่องตรวจภาพ (CV) เห็นบนแผ่นนี้ hint ไม่ใช่คำตอบ",
             "บนภาพมีกรอบหมายเลขกำกับตรงจุดที่เครื่องเห็น เรียงบน→ล่าง ซ้าย→ขวา ดังนี้"]
    for cls in CLASS_ORDER:
        sub = [e for e in els if e["class"] == cls]
        if not sub:
            continue
        lo, hi = sub[0]["n"], sub[-1]["n"]
        rng = "%d" % lo if lo == hi else "%d ถึง %d" % (lo, hi)
        rc = _row_counts(els, cls)
        row_txt = " แถวละ %s" % rc if len(rc) > 1 and not cls.startswith("beam") else ""
        lines.append("- %s (%s) จำนวน %d จุด หมายเลข %s%s" % (CLASS_TH[cls], cls, len(sub), rng, row_txt))
    lines.append(HINT_RULES_TH)
    return "\n".join(lines)


# ---------- pass 2.5: self-harvest ----------

def self_harvest(gray, det):
    """เอา detection ของหน้านี้เอง (ทุกตัวที่ผ่านคลังกลาง) เป็น template กวาดซ้ำเข้ม 0.90
    → (det ใหม่, จำนวนที่เพิ่ม, warnings)
    ไม่มี seed (บ้านที่คลังกลางหาไม่เจอเลย) → คืนของเดิม + ติดธง — ช่วยไม่ได้ ไม่เดา"""
    seeds = {"footing": [], "column": []}
    for cls in seeds:
        for cx, cy, w, h, sc in det.get(cls, []):
            if min(w, h) < MIN_SEED_PX:
                continue
            x, y = cx - w // 2, cy - h // 2
            crop = gray[max(0, y):y + h, max(0, x):x + w]
            if crop.size:
                seeds[cls].append(crop)
    if not seeds["footing"] and not seeds["column"]:
        return det, 0, ["self_harvest: ไม่มี seed (คลังกลางหาไม่เจอเลยในหน้านี้ — ช่วยไม่ได้)"], []
    har = analyze(gray, seeds["footing"], seeds["column"],
                  footing_thresh=HARVEST_THRESH, column_thresh=HARVEST_THRESH)
    out, added, added_pts = dict(det), 0, []
    for cls in ("footing", "column"):
        cur = list(det.get(cls, []))
        for cand in har.get(cls, []):
            cx, cy, w, h, sc = cand
            if all(abs(cx - ox) > 0.7 * max(w, ow) or abs(cy - oy) > 0.7 * max(h, oh)
                   for ox, oy, ow, oh, _ in cur):
                cur.append(cand)
                added += 1
                added_pts.append({"class": cls, "cx": int(cx), "cy": int(cy),
                                  "score": round(sc, 3)})
        out[cls] = cur
    return out, added, [], added_pts


# ---------- scan หลัก ----------

def page_hint(counts):
    """ลายนิ้วมือหยาบๆ จากจำนวนที่เจอ — ไว้เช็คขวางป้าย pass0 ไม่ใช่แทนที่มัน"""
    f, c, b = counts["footing"], counts["column"], counts["beam"]
    if f >= 4 and b == 0:
        return "foundation_plan-like"
    if b >= 4 and f <= 2:
        return "beam_plan-like"
    if f == 0 and c == 0 and b == 0:
        return "no_structural_symbols"
    return "mixed_or_unknown"


def scan_image(path, tpls, pass25=False):
    gray = imread_thai(path)
    det = analyze(gray, tpls.get("footing", []), tpls.get("column", []))
    warnings, added, added_pts = [], 0, []
    if pass25:
        det, added, warnings, added_pts = self_harvest(gray, det)
    elements = number_elements(det)
    counts = {"footing": len(det["footing"]), "column": len(det["column"]),
              "beam": len(det["beam_h"]) + len(det["beam_v"])}
    scan = {
        "file": str(path),
        "pass": "2.5" if pass25 else "1.5",
        "counts": counts,
        "hint": page_hint(counts),
        "elements": elements,
        "self_harvest_added": added,
        "self_harvest_points": added_pts,
        "warnings": warnings,
    }
    return scan, gray


def write_outputs(scan, gray, out_dir, stem, pass25=False):
    sfx = "25" if pass25 else ""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ("%s_cv%s.json" % (stem, sfx))).write_text(
        json.dumps(scan, ensure_ascii=False, indent=1), encoding="utf-8")
    if scan["elements"]:
        imwrite_thai(out_dir / ("%s_marked%s.png" % (stem, sfx)),
                     draw_som_marks(gray, scan["elements"]))
        (out_dir / ("%s_hint%s.txt" % (stem, sfx))).write_text(
            cv_hint_text(scan), encoding="utf-8")


def scan_paths(imgs, tpls, out_dir_of, pass25=False):
    results = []
    for img in imgs:
        scan, gray = scan_image(img, tpls, pass25=pass25)
        results.append(scan)
        c = scan["counts"]
        extra = " (+self-harvest %d)" % scan["self_harvest_added"] if pass25 else ""
        print("%s: ฐานราก %d เสา %d คาน %d  → %s%s"
              % (img.name, c["footing"], c["column"], c["beam"], scan["hint"], extra))
        write_outputs(scan, gray, out_dir_of(img), img.stem, pass25=pass25)
    return results


def run_manifest(workroot, tpls, pass25=False):
    """pass 1.5 จริง: เดินเฉพาะโฟลเดอร์ผังโครงสร้างที่ organize.py จัดไว้ → เขียนลง cv/ ข้าง images/"""
    root = Path(workroot)
    total = 0
    for sub in PLAN_SUBTASKS:
        img_dir = root / "pass2" / sub / "images"
        if not img_dir.is_dir():
            continue
        imgs = sorted(p for p in img_dir.glob("*.png") if "_marked" not in p.stem)
        if not imgs:
            continue
        print("[%s] %d รูป" % (sub, len(imgs)))
        scan_paths(imgs, tpls, lambda _: img_dir.parent / "cv", pass25=pass25)
        total += len(imgs)
    if total == 0:
        print("ไม่พบรูปใต้ %s/pass2/{%s}/images — รัน organize.py ก่อน"
              % (root, ",".join(PLAN_SUBTASKS)))
    return total


def demo():
    """self-check บ้าน 17: hint ถูกข้าง, เลขกำกับคงที่ข้ามรอบ, marked/hint ครบ, harvest ไม่ทำของหาย"""
    house = HERE.parent / "image" / "บ้าน_เล็ก_2ชั้น_17"
    tpls = load_templates()
    s14, g14 = scan_image(house / "บ้าน_เล็ก_2ชั้น_17_หน้า14.png", tpls)
    s16, _ = scan_image(house / "บ้าน_เล็ก_2ชั้น_17_หน้า16.png", tpls)
    print("หน้า14:", s14["counts"], "→", s14["hint"])
    print("หน้า16:", s16["counts"], "→", s16["hint"])
    assert s14["counts"]["footing"] >= 10 and s14["hint"] == "foundation_plan-like", s14["counts"]
    assert s16["counts"]["beam"] >= 8 and s16["hint"] == "beam_plan-like", s16["counts"]

    # เลขกำกับคงที่: รันซ้ำต้องได้ลิสต์เดิมเป๊ะ
    s14b, _ = scan_image(house / "บ้าน_เล็ก_2ชั้น_17_หน้า14.png", tpls)
    assert s14["elements"] == s14b["elements"], "เลขกำกับไม่คงที่ข้ามรอบรัน!"
    ns = [e["n"] for e in s14["elements"]]
    assert ns == list(range(1, len(ns) + 1)), "เลขไม่ต่อเนื่อง"

    # hint text มีชนิด+กฎครบ + มีคำสั่ง cv_mark + ไม่มีตัวเลขระยะ
    h = cv_hint_text(s14)
    assert "ไม่ใช่คำตอบ" in h and "cv_mark" in h and "\n4)" in h
    assert "เมตร" not in h and "span" not in h, "hint ห้ามมีระยะ"

    # marked image วาดได้จริง ขนาดเท่าภาพเดิม
    img = draw_som_marks(g14, s14["elements"])
    assert img.shape[:2] == g14.shape, "marked ขนาดเพี้ยน"

    # self-harvest ห้ามทำของเดิมหาย (เพิ่มได้อย่างเดียว)
    s25, _ = scan_image(house / "บ้าน_เล็ก_2ชั้น_17_หน้า14.png", tpls, pass25=True)
    for cls in ("footing", "column"):
        n_base = sum(1 for e in s14["elements"] if e["class"] == cls)
        n_25 = sum(1 for e in s25["elements"] if e["class"] == cls)
        assert n_25 >= n_base, "self-harvest ทำ %s หาย: %d → %d" % (cls, n_base, n_25)
    print("self-harvest หน้า14: +%d" % s25["self_harvest_added"])
    print("OK — self-check ผ่านทุกข้อ")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", help="ภาพหรือโฟลเดอร์")
    ap.add_argument("--manifest", help="workroot จาก organize.py — เดิน pass2/{ผัง}/images")
    ap.add_argument("--pass25", action="store_true", help="ต่อ self-harvest (pass 2.5)")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo()
    elif a.manifest:
        run_manifest(a.manifest, load_templates(), pass25=a.pass25)
    elif a.target:
        p = Path(a.target)
        imgs = (sorted(x for x in p.glob("*.png") if "_marked" not in x.stem)
                if p.is_dir() else [p])
        scan_paths(imgs, load_templates(), lambda i: i.parent, pass25=a.pass25)
    else:
        ap.print_help()
