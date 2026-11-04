#!/usr/bin/env python3
"""overlay TEST-01 (บ้าน_เล็ก_1ชั้น_03): เฉลย (น้ำเงิน) vs สิ่งที่ Destrier ชี้ (แดง) บนแปลนคาน หน้า 20 และ 21
ตำแหน่ง: เฉลยไม่มีพิกเซล มีแต่ชื่อเส้นกริด → แปลงด้วย pos_m ของ grid master (หน้า 00) + มาตราส่วน 1:100 + จุดอ้างอิงที่วัดจากภาพ"""
import json, re, glob, os
from PIL import Image, ImageDraw, ImageFont

B = r"D:\Temp\claude\3049db1b73f5b7d5\c641593e-2919-41af-bebc-66157c3c1ea4\scratchpad\bench5"
GT = r"D:\00mk\steel project\training\Training\json_แก้ไขแล้ว\08บ้าน_เล็ก_1ชั้น_03"
PX_PER_M = 28.3465 * 200 / 72          # 1:100 บน A3 · 200 dpi
K = 3309 / 2296                         # พิกัดที่อ่านจากภาพย่อ → พิกเซลจริง
FONT = r"C:\Windows\Fonts\tahoma.ttf"; FONTB = r"C:\Windows\Fonts\tahomabd.ttf"
def font(n, b=False):
    try: return ImageFont.truetype(FONTB if b else FONT, n)
    except Exception: return ImageFont.load_default()

grid = json.load(open(os.path.join(GT, "บ้าน_เล็ก_1ชั้น_03_หน้า00_gridline.json"), encoding="utf-8"))["grid"]
XP = {l["id"]: l["pos_m"] for l in grid["x_lines"]}; YP = {l["id"]: l["pos_m"] for l in grid["y_lines"]}
REF = re.compile(r"^([A-Za-z]'*)(\d+'*)$")

def locate(ref, ox, oy):
    """ref เช่น C3 / D'''2 → (x,y) พิกเซล · ox = พิกเซล x ของเส้น 1 · oy = พิกเซล y ของเส้น D"""
    m = REF.match((ref or "").strip())
    if not m or m.group(2) not in XP or m.group(1) not in YP: return None
    return ox + XP[m.group(2)] * PX_PER_M, oy + YP[m.group(1)] * PX_PER_M

def beams(path, types=("beam",)):
    d = json.load(open(path, encoding="utf-8"))
    return [(e["element_id"], e.get("grid_ref_start"), e.get("grid_ref_end")) for e in d.get("elements") or []
            if isinstance(e, dict) and e.get("element_type") in types and e.get("element_id")]

def draw_beams(img, items, ox, oy, rgb, w, label_dx, tag_font):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    n_ok = 0; skipped = []
    for eid, a, b in items:
        pa, pb = locate(a, ox, oy), locate(b, ox, oy)
        if not (pa and pb): skipped.append((eid, a, b)); continue
        d.line([pa, pb], fill=rgb + (150,), width=w); n_ok += 1
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        horiz = abs(pa[1] - pb[1]) < abs(pa[0] - pb[0])
        tx, ty = (mx - 18, my + label_dx) if horiz else (mx + label_dx, my - 18)
        d.text((tx, ty), eid, fill=rgb + (255,), font=tag_font, stroke_width=3, stroke_fill=(255, 255, 255, 255))
    img.alpha_composite(lay); return n_ok, skipped

def panel(page, crop, title, blue, red, ox, oy, note_lines):
    im = Image.open(os.path.join(B, "TEST-01", "img", f"page_{page:02d}.png")).convert("RGBA")
    n1 = n2 = 0; sk = []
    if blue: n1, sk = draw_beams(im, blue, ox, oy, (20, 70, 220), 16, 24, font(40, True))
    if red: n2, _ = draw_beams(im, red, ox, oy, (230, 20, 20), 10, -62, font(40, True))
    x0, y0, x1, y1 = [int(v * K) for v in crop]
    c = im.crop((x0, y0, x1, y1)).convert("RGB")
    top = 150 + 52 * len(note_lines)
    out = Image.new("RGB", (c.width, c.height + top), "white"); out.paste(c, (0, top))
    d = ImageDraw.Draw(out); d.text((20, 14), title, fill=(0, 0, 0), font=font(46, True))
    for i, (txt, col) in enumerate(note_lines): d.text((20, 86 + 52 * i), txt.replace("{n1}", str(n1)), fill=col, font=font(38))
    return out, n1, n2, sk

# ── ข้อมูล ──
gt20 = beams(os.path.join(GT, "บ้าน_เล็ก_1ชั้น_03_หน้า20_beam_plan.json"))
gt21 = beams(os.path.join(GT, "บ้าน_เล็ก_1ชั้น_03_หน้า21_view1_ring_beam_plan.json"))
res = json.load(open(os.path.join(B, "out", "TEST-01", "vllm", "result.json"), encoding="utf-8"))
F = {f["name"]: f.get("json") for f in res["files"]}
mod20 = beams_ = [(e.get("element_id"), e.get("grid_ref_start"), e.get("grid_ref_end")) for e in (F.get("page_20_plan_beam.json") or {}).get("elements", []) if e.get("element_type") == "beam"]
mod21 = [(e.get("element_id"), e.get("grid_ref_start"), e.get("grid_ref_end")) for e in (F.get("page_21_plan_beam.json") or {}).get("elements", []) if e.get("element_type") == "beam"]
slabs20 = [(e.get("element_id"), e.get("count")) for e in (F.get("page_20_plan_beam.json") or {}).get("elements", []) if e.get("element_type") == "slab"]
print("เฉลยหน้า20", len(gt20), "| โมเดลหน้า20 คาน", len(mod20), "พื้น", slabs20, "| เฉลยหน้า21", len(gt21), "| โมเดลหน้า21", mod21)

# จุดอ้างอิง (พิกเซลจริง) = ที่อ่านจากภาพย่อ × K: หน้า 20 เส้น 1 x=944, เส้น D y=509 · หน้า 21 (ผังซ้าย) เส้น 1 x=400, เส้น D y=440
O20 = (944 * K, 509 * K); O21 = (400 * K, 440 * K)
BLUE, RED, GREY = (20, 70, 220), (200, 20, 20), (70, 70, 70)

pA, a1, a2, sk20 = panel(20, (640, 250, 1450, 1240), "(1) หน้า 20 แปลนคาน — คานตามเฉลย (น้ำเงิน)", gt20, [], *O20,
    [(f"เฉลยมีคาน {len(gt20)} ช่วง วาดได้ {{n1}} ช่วง (ที่เหลือวางตำแหน่งไม่ได้)", BLUE)])
pB, b1, b2, _ = panel(20, (640, 250, 1450, 1240), "(2) หน้าเดียวกัน — ที่ Destrier ชี้ (แดง)", [], mod20, *O20,
    [(f"โมเดลตอบหน้านี้ว่า: คาน {len(mod20)} เส้น · แผ่นพื้น " + ", ".join(f"{i}×{c}" for i, c in slabs20), RED),
     ("(ไม่มีเส้นแดงเลย = ยังไม่เจอคานสักเส้นบนแปลนนี้)", RED)])
pC, c1, c2, sk21 = panel(21, (120, 190, 880, 1050), "(3) หน้า 21 แปลนอะเส — เฉลย/โมเดล", gt21, mod21, *O21,
    [(f"เฉลย {len(gt21)} ช่วง · โมเดลชี้ {len(mod21)} ช่วง", GREY),
     ("แดง = B1, B2 ที่ช่วง C3–B3 (ช่วงเดียวกัน ป้ายซ้อนกัน)", RED)])

H = max(p.height for p in (pA, pB, pC)); W = pA.width + pB.width + pC.width + 40
foot = 230; sheet = Image.new("RGB", (W, H + foot), "white")
x = 0
for p in (pA, pB, pC): sheet.paste(p, (x, 0)); x += p.width + 20
d = ImageDraw.Draw(sheet)
d.rectangle([0, H + 10, W, H + foot], fill=(245, 245, 245))
d.text((30, H + 24), "ทำไม 'มาร์คคานตรง 100%' ไม่ได้แปลว่าเจอคาน", fill=(0, 0, 0), font=font(50, True))
d.text((30, H + 92), "ตัวเลข 100% นับแค่รหัสคาน (B1, B2, B3, B4, B5, B3X, B4X, B5X) ที่โมเดลพิมพ์ออกมาครบเท่ารหัสในเฉลยทั้งบ้าน", fill=(30, 30, 30), font=font(40))
d.text((30, H + 142), "รหัสเหล่านั้นมาจากหน้า 24 (ตารางหน้าตัด) ซึ่งไม่มีตำแหน่ง — ส่วนแปลนคานจริง (หน้า 20) โมเดลไม่ได้ชี้คานเลย", fill=(30, 30, 30), font=font(40))
d.text((30, H + 188), "หมายเหตุ: เส้นสีวางจากชื่อเส้นกริด + มาตราส่วน 1:100 (ไม่ใช่ตำแหน่งที่โมเดลให้มา — โมเดลไม่ส่งพิกเซล) จึงคลาดได้เล็กน้อย", fill=(90, 90, 90), font=font(34))
sheet.thumbnail((3000, 3000))
out = os.path.join(B, "overlay_TEST-01.png"); sheet.save(out)
print("saved", out, sheet.size, "| ข้าม(เฉลย20):", sk20[:6], "| ข้าม(เฉลย21):", sk21[:6])
