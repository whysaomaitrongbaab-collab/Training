#!/usr/bin/env python3
"""pattern_recognition.py — ไฮไลต์ เสา/คาน/ฐานราก บนแบบก่อสร้างด้วย cv2 template matching

มะขามสั่ง 2026-08-25 (จากประชุมอาจารย์): ไม่เอาแค่นับ — ให้ mark ตำแหน่งลงบนภาพเลย
เป็นเครื่องมือ standalone อ่านภาพอย่างเดียว ไม่แตะ raw JSON / fine-tuning data ใดๆ
(ผลลัพธ์เขียนลง tools/pattern_out/ เท่านั้น — ไม่เขียนอะไรลงโฟลเดอร์ image/ ต้นทาง)

วิธีใช้:
    python tools/pattern_recognition.py <ภาพ.png>                 # เขียน <ชื่อ>_marked.png ลง tools/pattern_out/
    python tools/pattern_recognition.py <ภาพ.png> -o out.png      # เลือกที่เซฟเอง
    python tools/pattern_recognition.py --demo                    # self-check กับบ้าน 17 (ฐานรากต้องได้ 14)

สี:  ฐานราก = แดง   เสา = เขียว   คาน = น้ำเงิน (แถบโปร่ง)

ที่มาของ template (บ้าน_เล็ก_2ชั้น_17, สแกน 3309x2339, มาตราส่วน 1:75):
  - footing: ไอคอนสี่เหลี่ยมซ้อน F1A/C1 ตัดจากหน้า14 ที่ (1240,766) — ยืนยันด้วยตาแล้ว
  - column : กล่องเสา C1 ที่จุดตัดคาน ตัดจากหน้า16 ที่ (1068-1096, 754-788)
  - beam   : สังเคราะห์ — เส้นขนานดำ 2 เส้น หนา 3px ห่าง 21px (วัดจากหน้า16 y=758-760/777-779)

# ponytail: ค่า BEAM_GAP/BEAM_THICK ผูกกับ DPI+มาตราส่วนของชุดสแกนนี้ — บ้านที่สแกนต่าง
# DPI ต้องปรับ --beam-gap เอง (ไม่มี auto-scale จนกว่าจะเจอบ้านที่ต้องใช้จริง)
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
TEMPLATE_DIR = HERE / "templates"
OUT_DIR = HERE / "pattern_out"

# threshold ต่อ class — จูนกับบ้าน 17: footing นิ่งมาก (14/14 ตั้งแต่ 0.5-0.8), column ต้องสูงกว่า
# 0.60 → 0.72 (2026-08-25 หลังขยาย bank 3→12): bank ใหญ่ = โอกาสขยะช่วง 0.6-0.65 คูณตาม
# จำนวน template (เทสต์จริง: หน้า16 บ้าน 17 ซึ่งไม่มีฐานรากเลย ขึ้น 607 จุดที่เกณฑ์เดิม)
# บ้าน 17 ของแท้ให้คะแนน 0.82-1.00 จึงยังห่างเกณฑ์ใหม่พอสมควร
FOOTING_THRESH = 0.72
COLUMN_THRESH = 0.65
BEAM_THRESH = 0.70
BEAM_MIN_LEN = 100   # แถบคานสั้นกว่านี้ (px) ตัดทิ้ง — กัน false positive จากตัวหนังสือ/ขอบตาราง
BEAM_GAP = 21        # ระยะหน้าคานบน-ล่าง (px) — วัดจากบ้าน 17
BEAM_THICK = 3


def imread_thai(path):
    """cv2.imread พังกับ path ภาษาไทยบน Windows — อ้อมผ่าน np.fromfile"""
    buf = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)
    return img


def imwrite_thai(path, img):
    cv2.imencode(Path(path).suffix, img)[1].tofile(str(path))


def beam_template(gap=BEAM_GAP, thick=BEAM_THICK, length=60, vertical=False):
    """เส้นขนานดำ 2 เส้น = หน้าตัดคานบนผังโครงสร้าง"""
    pad = 6
    h = gap + thick + 2 * pad
    tpl = np.full((h, length), 255, np.uint8)
    tpl[pad:pad + thick, :] = 0
    tpl[pad + gap:pad + gap + thick, :] = 0
    return tpl.T.copy() if vertical else tpl


# ไอคอนเดียวกันถูกวาดคนละขนาดตามชนิดจริง (บ้าน 12: F1 เล็กกว่า F2 — เจอวันแรกที่ทดสอบข้ามบ้าน)
# จึง match หลาย scale แล้วเอาคะแนนสูงสุดต่อตำแหน่ง — คือคำตอบมาตรฐานของข้อจำกัด scale variance
SCALES = (0.7, 0.8, 0.9, 1.0, 1.1, 1.2)


def match_points(gray, tpl, thresh, scales=SCALES, _nms=True):
    """คืน [(cx, cy, w, h, score)] (จุดกึ่งกลาง+ขนาดกล่อง) ทุก scale รวมกัน หลัง NMS แบบ greedy"""
    cands = []
    for s in scales:
        st = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        th, tw = st.shape
        if th >= gray.shape[0] or tw >= gray.shape[1]:
            continue
        res = cv2.matchTemplate(gray, st, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= thresh)
        for x, y in zip(xs, ys):
            cands.append((int(x) + tw // 2, int(y) + th // 2, tw, th, float(res[y, x])))
    return _nms_greedy(cands) if _nms else cands


def _nms(cands):
    return _nms_greedy(cands)


def _nms_greedy(cands):
    keep = []
    for cx, cy, w, h, sc in sorted(cands, key=lambda c: -c[4]):
        # NMS ด้วยระยะจุดกึ่งกลาง ~ ขนาดกล่อง — กันกล่องซ้อน/กล่องเบิ้ลข้าม scale/ข้าม template
        if all(abs(cx - kx) > 0.7 * max(w, kw) or abs(cy - ky) > 0.7 * max(h, kh)
               for kx, ky, kw, kh, _ in keep):
            keep.append((cx, cy, w, h, sc))
    return keep


def match_beam_runs(gray, tpl, thresh, min_len, vertical=False):
    """match คานแล้วรวมจุดต่อเนื่องเป็นแถบยาว คืน [(x, y, w, h)]"""
    res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
    th, tw = tpl.shape
    mask = np.zeros(gray.shape, np.uint8)
    ys, xs = np.where(res >= thresh)
    for x, y in zip(xs, ys):
        mask[y:y + th, x:x + tw] = 255
    # ปิดช่องว่างเล็กๆ ตามแนวคาน (ข้าม label/เสาที่คั่นกลาง)
    k = (1, 25) if vertical else (25, 1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones(k[::-1], np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    runs = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if (h if vertical else w) >= min_len:
            runs.append((x, y, w, h))
    return runs


def match_bank(gray, tpls, thresh, scales=SCALES):
    """match ทุก template ในลิสต์ (ต่างชนิดไอคอน เช่น F1 จัตุรัสซ้อน / F2 ผืนผ้า+จุดเข็ม)
    รวม candidate ทุกตัวก่อนแล้วค่อย NMS ทีเดียว — กันกล่อง F1/F2 เบิ้ลทับตำแหน่งเดียวกัน"""
    cands = []
    for tpl in tpls:
        cands += match_points(gray, tpl, thresh, scales=scales, _nms=False)
    return _nms(cands)


def analyze(gray, tpls_footing=(), tpls_column=(),
            footing_thresh=FOOTING_THRESH, column_thresh=COLUMN_THRESH,
            beam_thresh=BEAM_THRESH, beam_gap=BEAM_GAP):
    """คืน dict ผลตรวจทุก class (template ไหนไม่มีก็ข้าม class นั้น)"""
    out = {"footing": [], "column": [], "beam_h": [], "beam_v": []}
    out["footing"] = match_bank(gray, tpls_footing, footing_thresh)
    # เสา: single-scale พอ — C1 บนผังคานขนาดคงที่ในบ้านเดียวกัน และ template เล็กมาก
    # ย่อ scale แล้วเริ่มจับ noise (เทสต์บ้าน 17: multi-scale ทำให้ 14 กลายเป็น 21)
    out["column"] = match_bank(gray, tpls_column, column_thresh, scales=(1.0,))
    out["beam_h"] = match_beam_runs(gray, beam_template(beam_gap), beam_thresh, BEAM_MIN_LEN)
    out["beam_v"] = match_beam_runs(gray, beam_template(beam_gap, vertical=True),
                                    beam_thresh, BEAM_MIN_LEN, vertical=True)
    # ไอคอนฐานราก F2 (ผืนผ้าแนวตั้ง) หน้าตาคล้าย "คานตั้งวิ่งผ่านกล่องเสา" — บนผังคานจึง
    # จับมั่ว (เจอจริงบ้าน 12 หน้า22) แก้โดยตัดฐานรากที่จุดกึ่งกลางตกในแถบคานทิ้ง:
    # ผังฐานรากจริงไม่มีคานให้ detect อยู่แล้ว กฎนี้จึงไม่มีทางตัดฐานรากจริง
    beams = out["beam_h"] + out["beam_v"]
    M = 10  # ขยายแถบคานเผื่อขอบ — กล่อง run แน่นเป๊ะ ขยะที่เกาะขอบคาน (ห่าง 4px ก็เจอจริง) หนีได้
    out["footing"] = [f for f in out["footing"]
                      if not any(bx - M <= f[0] <= bx + bw + M and by - M <= f[1] <= by + bh + M
                                 for bx, by, bw, bh in beams)]
    return out


def draw_marks(gray, det):
    """วาด overlay: ฐานราก=แดง เสา=เขียว คาน=น้ำเงินโปร่ง + ป้ายจำนวนมุมภาพ"""
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    overlay = img.copy()
    for x, y, w, h in det["beam_h"] + det["beam_v"]:
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (255, 80, 0), -1)
    img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)
    for cx, cy, w, h, s in det["footing"]:
        cv2.rectangle(img, (cx - w // 2 - 4, cy - h // 2 - 4),
                      (cx + w // 2 + 4, cy + h // 2 + 4), (0, 0, 255), 3)
    for cx, cy, w, h, s in det["column"]:
        cv2.rectangle(img, (cx - w // 2 - 4, cy - h // 2 - 4),
                      (cx + w // 2 + 4, cy + h // 2 + 4), (0, 180, 0), 3)
    n_beam = len(det["beam_h"]) + len(det["beam_v"])
    label = f"footing:{len(det['footing'])}  column:{len(det['column'])}  beam:{n_beam}"
    cv2.putText(img, label, (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
    return img


def load_templates():
    """template bank: tpl_footing*.png / tpl_column*.png ทุกไฟล์ใน tools/templates/"""
    tpls = {"footing": [], "column": []}
    for name in tpls:
        for p in sorted(TEMPLATE_DIR.glob(f"tpl_{name}*.png")):
            t = imread_thai(p)
            # template จิ๋วเกิน = จับทุกอย่างที่คล้ายเส้นตัดกัน (บทเรียนจริง 2026-08-25:
            # เครื่องหมาย + ขนาด 22px จากบ้าน 11 ทำ footing บวม 636 จุดในหน้าที่ไม่มีฐานราก)
            if min(t.shape) < 28:
                print(f"⚠️ ข้าม {p.name} — เล็กกว่า 28px จับมั่วแน่นอน (ย้ายออกจาก templates/)")
                continue
            tpls[name].append(t)
    return tpls


def run(image_path, out_path=None, beam_gap=BEAM_GAP):
    gray = imread_thai(image_path)
    tpls = load_templates()
    det = analyze(gray, tpls["footing"], tpls["column"], beam_gap=beam_gap)
    marked = draw_marks(gray, det)
    if out_path is None:
        OUT_DIR.mkdir(exist_ok=True)
        out_path = OUT_DIR / (Path(image_path).stem + "_marked.png")
    imwrite_thai(out_path, marked)
    n_beam = len(det["beam_h"]) + len(det["beam_v"])
    print(f"{Path(image_path).name}: ฐานราก {len(det['footing'])} | เสา {len(det['column'])} "
          f"| แถบคาน {n_beam} -> {out_path}")
    return det


def demo():
    """self-check กับบ้าน 17 — ฐานรากหน้า14 ต้องเจอครบ 14 (ground truth นับจากแบบจริง)"""
    house = HERE.parent / "image" / "บ้าน_เล็ก_2ชั้น_17"
    det14 = run(house / "บ้าน_เล็ก_2ชั้น_17_หน้า14.png")
    assert len(det14["footing"]) == 14, f"ฐานรากหน้า14 ต้องได้ 14 ได้ {len(det14['footing'])}"
    det16 = run(house / "บ้าน_เล็ก_2ชั้น_17_หน้า16.png")
    assert len(det16["beam_h"]) + len(det16["beam_v"]) >= 8, "หน้า16 ต้องเจอแถบคานอย่างน้อย 8"
    print("OK — self-check ผ่าน")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image", nargs="?", help="ภาพหน้าแบบ (.png)")
    ap.add_argument("-o", "--out", help="path ภาพผลลัพธ์")
    ap.add_argument("--beam-gap", type=int, default=BEAM_GAP,
                    help=f"ระยะหน้าคานบน-ล่าง px (default {BEAM_GAP} จากบ้าน 17)")
    ap.add_argument("--demo", action="store_true", help="รัน self-check บ้าน 17")
    a = ap.parse_args()
    if a.demo:
        demo()
    elif a.image:
        run(a.image, a.out, a.beam_gap)
    else:
        ap.print_help()
        sys.exit(1)
