#!/usr/bin/env python3
"""overlay ก่อน/หลังรวม CV ทุกหน้าแปลนคานที่ fusion หาเส้นกริดได้ + หน้า held-out (CV/หัวกริดที่เห็น)
ตำแหน่งเส้น: วางด้วยเส้นกริดที่ระบบหาเอง (fused_debug X/Y) — เฉลยที่อ้างเส้นที่ระบบไม่เห็นจะวาดไม่ได้ (นับแยก)
คะแนนรายหน้า: เกณฑ์เดียวกับ King (ชนิด+รหัส+ปลายช่วง) แต่เทียบเฉพาะหน้านั้น"""
import glob, json, os, re
import cv2
from PIL import Image, ImageDraw, ImageFont

B = r"D:\Temp\claude\3049db1b73f5b7d5\c641593e-2919-41af-bebc-66157c3c1ea4\scratchpad\bench5"
GT = r"D:\00mk\steel project\training\Training\json_แก้ไขแล้ว"
OUT = os.path.join(B, "overlays"); os.makedirs(OUT, exist_ok=True)
H = {"TEST-01": "08บ้าน_เล็ก_1ชั้น_03", "TEST-02": "11บ้าน_เล็ก_1ชั้น_06", "TEST-03": "03บ้าน_เล็ก_2ชั้น_01",
     "TEST-04": "27บ้าน_เล็ก_2ชั้น_06", "TEST-05": "34บ้าน_ใหญ่_1ชั้น_02"}
BLUE, RED, GREEN, ORANGE = (20, 70, 220), (220, 20, 20), (0, 150, 60), (255, 140, 0)
def font(n, b=False):
    return ImageFont.truetype(r"C:\Windows\Fonts\tahomabd.ttf" if b else r"C:\Windows\Fonts\tahoma.ttf", n)
REF = re.compile(r"^([A-Z]'*)(\d+'*)$")
key = lambda i, a, b: ((i or "").strip().upper(), frozenset(((a or "").strip().upper(), (b or "").strip().upper())))

def gt_page(folder, page):
    out = []
    for f in glob.glob(os.path.join(GT, folder, f"*_หน้า{page:02d}_*.json")):
        d = json.load(open(f, encoding="utf-8"))
        out += [(e["element_id"], e.get("grid_ref_start"), e.get("grid_ref_end")) for e in d.get("elements") or []
                if isinstance(e, dict) and e.get("element_type") == "beam" and e.get("element_id")]
    return out

def locate(ref, X, Y):
    m = REF.match((ref or "").strip().upper())
    if not m: return None
    L, N = m.group(1), m.group(2)
    if L in Y and N in X: return X[N], Y[L]
    if L in X and N in Y: return X[L], Y[N]
    return None

def draw(img, items, X, Y, rgb, w, dy):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); n = 0
    for i, a, b in items:
        pa, pb = locate(a, X, Y), locate(b, X, Y)
        if not (pa and pb): continue
        n += 1; d.line([pa, pb], fill=rgb + (150,), width=w)
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        horiz = abs(pa[1] - pb[1]) < abs(pa[0] - pb[0])
        d.text((mx - 20, my + dy) if horiz else (mx + dy, my - 20), i, fill=rgb + (255,), font=font(34, True),
               stroke_width=3, stroke_fill=(255, 255, 255, 255))
    img.alpha_composite(lay); return n

def score(gt, pr):
    g = {key(*x) for x in gt}; p = {key(*x) for x in pr}
    tp = len(g & p); P = tp / len(p) * 100 if p else 0; R = tp / len(g) * 100 if g else 0
    return tp, len(p), len(g), P, R

def panel(page_img, crop, title, lines):
    c = page_img.crop(crop).convert("RGB")
    top = 70 + 46 * len(lines); out = Image.new("RGB", (c.width, c.height + top), "white"); out.paste(c, (0, top))
    d = ImageDraw.Draw(out); d.text((16, 10), title, fill=(0, 0, 0), font=font(42, True))
    for k, (t, col) in enumerate(lines): d.text((16, 66 + 46 * k), t, fill=col, font=font(32))
    return out

summary = []
for tid, folder in H.items():
    R = json.load(open(os.path.join(B, "out", tid, "vllm", "result.json"), encoding="utf-8"))
    F = {f["name"]: f.get("json") for f in R["files"]}
    fused = json.load(open(os.path.join(B, "out", tid, "fused.json"), encoding="utf-8"))
    dbg = json.load(open(os.path.join(B, "out", tid, "fused_debug.json"), encoding="utf-8"))
    for pg in dbg["pages"]:
        page, X, Y = pg["page"], pg.get("X") or {}, pg.get("Y") or {}
        img = Image.open(os.path.join(B, tid, "img", f"page_{page:02d}.png")).convert("RGBA")
        gt = gt_page(folder, page)
        model = []
        for name, j in F.items():
            if name.startswith(f"page_{page:02d}_plan_beam") and isinstance(j, dict):
                model += [(e.get("element_id"), e.get("grid_ref_start"), e.get("grid_ref_end")) for e in j.get("elements") or []
                          if isinstance(e, dict) and e.get("element_type") == "beam" and e.get("element_id")]
        fz = [(f["element_id"], f["grid_ref_start"], f["grid_ref_end"]) for f in fused if f["page"] == page]
        fz = fz or model          # กติกา "แทนที่": หน้าที่ fusion ไม่ได้อะไร ระบบสุดท้ายยังใช้คำตอบของโมเดล
        if len(X) >= 2 and len(Y) >= 2:
            xs, ys = list(X.values()), list(Y.values())
            crop = (max(0, int(min(xs) - 330)), max(0, int(min(ys) - 300)), min(img.width, int(max(xs) + 330)), min(img.height, int(max(ys) + 260)))
            a = img.copy(); ng = draw(a, gt, X, Y, BLUE, 16, 22); draw(a, model, X, Y, RED, 9, -58)
            b = img.copy(); draw(b, gt, X, Y, BLUE, 16, 22); draw(b, fz, X, Y, RED, 9, -58)
            s0, s1 = score(gt, model), score(gt, fz)
            note = (f"เฉลยหน้านี้ {len(gt)} ช่วง (วาดได้ {ng} — ที่เหลืออ้างเส้นกริดที่ระบบไม่เห็น)", (90, 90, 90))
            pa = panel(a, crop, f"{tid} หน้า {page} — ก่อน: Destrier อย่างเดียว",
                       [note, (f"ตอบ {s0[1]} ช่วง · ตรง {s0[0]} · precision {s0[3]:.0f}% · recall {s0[4]:.0f}%", RED)])
            pb = panel(b, crop, f"{tid} หน้า {page} — หลัง: + CV + หัวกริด + OCR",
                       [note, (f"ตอบ {s1[1]} ช่วง · ตรง {s1[0]} · precision {s1[3]:.0f}% · recall {s1[4]:.0f}%", RED)])
            summary.append((tid, page, len(gt), s0, s1))
        else:
            # held-out / หัวกริดไม่พอ: แสดงสิ่งที่ CV + ตัวหาหัวกริดเห็น
            wr = dbg.get("workroot")
            cvf = os.path.join(wr, "pass2", "plan_beam", "cv", pg["stem"] + "_cv.json")
            els = json.load(open(cvf, encoding="utf-8")).get("elements", []) if os.path.exists(cvf) else []
            off = pg.get("offset") or (0, 0)
            a = img.copy(); lay = Image.new("RGBA", a.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            for e in els:
                cx, cy, w, h = e["cx"] + off[0], e["cy"] + off[1], e["w"], e["h"]
                col = GREEN if e["class"] == "column" else ORANGE
                d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=col + (255,), width=7, fill=col + (50,))
            for k, v in X.items(): d.line([(v, 0), (v, a.height)], fill=(160, 0, 200, 120), width=5); d.text((v + 6, 40), k, fill=(160, 0, 200, 255), font=font(40, True))
            for k, v in Y.items(): d.line([(0, v), (a.width, v)], fill=(160, 0, 200, 120), width=5); d.text((40, v + 6), k, fill=(160, 0, 200, 255), font=font(40, True))
            a.alpha_composite(lay)
            pa = panel(a, (0, 0, a.width, a.height), f"{tid} หน้า {page} — ทำไมรวมไม่ได้",
                       [(f"ส้ม = ท่อนคานที่ CV เห็น {sum(1 for e in els if e['class'].startswith('beam'))} · เขียว = เสา · ม่วง = เส้นกริดที่หาเจอ x={list(X)} y={list(Y)}", (60, 60, 60)),
                        (f"เหตุผล: {pg.get('skip') or 'ได้ช่วง 0'} · เฉลยหน้านี้ {len(gt)} ช่วง", RED)])
            pb = None; summary.append((tid, page, len(gt), None, None))
        W = pa.width + (pb.width + 24 if pb else 0); Hh = max(pa.height, pb.height if pb else 0)
        sheet = Image.new("RGB", (W, Hh), "white"); sheet.paste(pa, (0, 0))
        if pb: sheet.paste(pb, (pa.width + 24, 0))
        sheet.thumbnail((2600, 2600)); p = os.path.join(OUT, f"{tid}_{pg['stem'].replace('page_', 'หน้า')}.png"); sheet.save(p); print("saved", p)

print("\nรายหน้า (เกณฑ์ King เทียบเฉพาะหน้านั้น): บ้าน หน้า เฉลย | ก่อน ตรง/ตอบ P R | หลัง ตรง/ตอบ P R")
for tid, page, ng, s0, s1 in summary:
    if s0: print(f"{tid} {page:>3} {ng:>4} | {s0[0]:>3}/{s0[1]:<3} {s0[3]:5.0f} {s0[4]:5.0f} | {s1[0]:>3}/{s1[1]:<3} {s1[3]:5.0f} {s1[4]:5.0f}")
    else: print(f"{tid} {page:>3} {ng:>4} | รวมไม่ได้")
