#!/usr/bin/env python3
"""overlay: สิ่งที่ CV (cv2 template-match, pass 1.5/2.5) จับได้บนแปลนคาน หน้า 20 ของ TEST-01 + เฉลยคานเป็นเส้นน้ำเงินจาง"""
import json, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
import overlay_t01 as O   # ใช้ฟังก์ชัน locate/beams/font + ค่าคงที่เดิม (รันสคริปต์นั้นซ้ำ 1 รอบตอน import — ไม่เป็นไร)

B = O.B
res = json.load(open(os.path.join(B, "out", "TEST-01", "vllm", "result.json"), encoding="utf-8"))
F = {f["name"]: f["json"] for f in res["files"]}
c15 = F["cv15_plan_beam_page_20_cv.json"]; c25 = F["cv25_plan_beam_page_20_cv25.json"]
print("cv15 หน้า20:", c15["counts"], "| cv25:", c25["counts"], "| self-harvest:", len(c25.get("self_harvest_points") or []))
print("ตัวอย่าง self_harvest:", json.dumps((c25.get("self_harvest_points") or [None])[:2], ensure_ascii=False))

im = Image.open(os.path.join(B, "TEST-01", "img", "page_20.png")).convert("RGBA")
lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
# เฉลย (จาง)
for eid, a, b in O.gt20:
    pa, pb = O.locate(a, *O.O20), O.locate(b, *O.O20)
    if pa and pb: d.line([pa, pb], fill=(20, 70, 220, 70), width=16)
# CV (pass 1.5) = กล่องทึบอ่อน/เส้นขอบเข้ม
for e in c15.get("elements") or []:
    cx, cy, w, h = e["cx"], e["cy"], e["w"], e["h"]; box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    col = (0, 160, 60) if e["class"] == "column" else (255, 140, 0)
    d.rectangle(box, outline=col + (255,), width=8, fill=col + (60,))
# pass 2.5 self-harvest = จุดม่วง
for e in c25.get("self_harvest_points") or []:
    cx, cy = e.get("cx"), e.get("cy")
    if cx is not None: d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], outline=(160, 0, 200, 255), width=8)
im.alpha_composite(lay)
x0, y0, x1, y1 = [int(v * O.K) for v in (640, 250, 1450, 1240)]
c = im.crop((x0, y0, x1, y1)).convert("RGB")
top = 240; out = Image.new("RGB", (c.width, c.height + top), "white"); out.paste(c, (0, top)); dd = ImageDraw.Draw(out)
dd.text((20, 14), "CV (cv2) จับได้อะไรบนแปลนคาน หน้า 20", fill=(0, 0, 0), font=O.font(46, True))
dd.text((20, 80), f"เขียว = เสา {c15['counts']['column']} ต้น · ส้ม = ท่อนคาน {c15['counts']['beam']} ท่อน", fill=(30, 30, 30), font=O.font(36))
dd.text((20, 130), "ม่วง = เสาที่รอบ 2.5 เพิ่มให้ 3 จุด · น้ำเงินจาง = คานตามเฉลย", fill=(20, 70, 220), font=O.font(32))
dd.text((20, 180), "CV รู้แค่ตำแหน่งพิกเซล ไม่รู้ชื่อมาร์ค/ช่วงกริด", fill=(160, 20, 20), font=O.font(32))
out.thumbnail((1800, 2200)); p = os.path.join(B, "overlay_cv_TEST-01_หน้า20.png"); out.save(p); print("saved", p, out.size)
