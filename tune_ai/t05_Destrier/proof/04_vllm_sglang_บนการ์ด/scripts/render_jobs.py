"""PDF → page_NN.png (PyMuPDF dpi=200 = ตอนเทรน Destrier + เว็บ RENDER_SCALE 200/72) + job JSON แบบที่เว็บส่ง
    python render_jobs.py <โฟลเดอร์ pdf> <โฟลเดอร์ออก>"""
import json
import os
import sys

import fitz

src, out = sys.argv[1], sys.argv[2]
for f in sorted(os.listdir(src)):
    if not f.endswith(".pdf"):
        continue
    name = f[:-4]
    d = os.path.join(out, f"img_{name}")
    os.makedirs(d, exist_ok=True)
    doc = fitz.open(os.path.join(src, f))
    pages = []
    for i, p in enumerate(doc, 1):
        pix = p.get_pixmap(dpi=200)
        fn = f"page_{i:02d}.png"
        pix.save(os.path.join(d, fn))
        pages.append({"page": i, "path": f"bench/{name}/{fn}"})
    json.dump({"id": f"web-{name}", "payload": {"pages": pages}},
              open(os.path.join(out, f"job_{name}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(name, len(pages), "หน้า", f"{pix.width}x{pix.height}", flush=True)
