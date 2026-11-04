#!/usr/bin/env python3
"""ก่อน/หลังรวม CV บนหน้า 20 ของ TEST-01: เฉลย (น้ำเงิน) vs คำตอบ (แดง) · ก่อน = โมเดลอย่างเดียว · หลัง = โมเดล+CV"""
import json, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
import overlay_t01 as O

fused = [(f["element_id"], f["grid_ref_start"], f["grid_ref_end"])
         for f in json.load(open(os.path.join(O.B, "out", "TEST-01", "fused.json"), encoding="utf-8")) if f["page"] == 20]
gtk = {(i, frozenset((a, b))) for i, a, b in O.gt20}
hit = sum(1 for i, a, b in fused if (i, frozenset((a, b))) in gtk)
pA, *_ = O.panel(20, (640, 250, 1450, 1240), "ก่อน: โมเดลอย่างเดียว", O.gt20, O.mod20, *O.O20,
                 [(f"น้ำเงิน = เฉลย {len(O.gt20)} ช่วง · แดง = โมเดลชี้ {len(O.mod20)} ช่วง", O.RED)])
pB, *_ = O.panel(20, (640, 250, 1450, 1240), "หลัง: โมเดล + CV + หัวกริด + ป้าย (OCR)", O.gt20, fused, *O.O20,
                 [(f"แดง = ช่วงคานที่ระบบชี้ {len(fused)} ช่วง · ตรงเฉลยทั้งรหัสและปลายช่วง {hit} ช่วง", O.RED)])
W = pA.width + pB.width + 20; H = max(pA.height, pB.height)
sheet = Image.new("RGB", (W, H + 120), "white"); sheet.paste(pA, (0, 0)); sheet.paste(pB, (pA.width + 20, 0))
d = ImageDraw.Draw(sheet)
d.text((30, H + 20), "ตำแหน่งเส้นวาดจากชื่อเส้นกริด (เฉลย/คำตอบ) วางด้วยมาตราส่วน 1:100 — แดงทับน้ำเงิน = ระบบชี้ถูกช่วง",
       fill=(60, 60, 60), font=O.font(36))
sheet.thumbnail((2600, 2600)); p = os.path.join(O.B, "overlay_fused_TEST-01_หน้า20.png"); sheet.save(p)
print("saved", p, sheet.size, "fused p20", len(fused), "hit", hit)
