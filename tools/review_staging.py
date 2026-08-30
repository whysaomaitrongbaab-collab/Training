#!/usr/bin/env python3
"""review_staging.py — สร้างหน้าเว็บดู candidate ใน templates/staging/ ทีเดียวทั้งหมด

ปัญหาที่แก้: harvest_templates.py ทิ้ง candidate ไว้ 147 ไฟล์ให้คนตรวจ (ห้าม auto-promote
โดยตั้งใจ — บทเรียน F1/F2 "รูปทรงที่เดาว่าเหมือน อาจเป็นคนละของ") แต่การเปิดดูทีละไฟล์
ใน explorer แล้วจำว่าอันไหนผ่านไม่ผ่าน = คอขวดจริงของการขยายคลัง

    python tools/review_staging.py            # → tools/staging_review.html เปิดด้วยเบราว์เซอร์
    python tools/review_staging.py --open     # สร้างแล้วเปิดให้เลย

หน้าเว็บ: ภาพทุกใบเรียงตามบ้าน · ติ๊กอันที่ใช้ได้ + เลือกชนิด (ฐานราก/เสา) → กดปุ่มได้คำสั่ง
`harvest_templates.py --promote ...` ไปวางใน terminal · ไม่มีการย้ายไฟล์จากหน้าเว็บเอง
(คนยังเป็นคนกดคำสั่งเสมอ — หน้านี้แค่ช่วยดู ไม่ได้ตัดสินใจแทน)

self-contained (ฝัง base64) เปิดจากไฟล์ตรงๆ ได้ ไม่ต้องรันเซิร์ฟเวอร์
"""
import argparse
import base64
import html
import re
import webbrowser
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
STAGING = HERE / "templates" / "staging"
OUT = HERE / "staging_review.html"


def house_of(name):
    """ชื่อไฟล์: cand_<kind>__<บ้าน>__g0_n18.png → คืนชื่อบ้าน หรือ '?' ถ้าอ่านไม่ออก"""
    m = re.search(r"__(.+?)__", name)
    return m.group(1) if m else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true", help="เปิดเบราว์เซอร์ให้เลย")
    a = ap.parse_args()

    files = sorted(STAGING.glob("*.png"))
    if not files:
        raise SystemExit(f"ไม่มีไฟล์ใน {STAGING}")

    by_house = defaultdict(list)
    for f in files:
        by_house[house_of(f.name)].append(f)

    cards = []
    for house in sorted(by_house):
        cards.append(f'<h2>{html.escape(house)} '
                     f'<span class="n">{len(by_house[house])} รูป</span></h2><div class="grid">')
        for f in by_house[house]:
            b64 = base64.b64encode(f.read_bytes()).decode("ascii")
            n = html.escape(f.name)
            # n จาก glob ของโฟลเดอร์เรา ไม่ใช่ input ผู้ใช้ แต่ escape ไว้เป็นนิสัย
            cards.append(f'''<label class="card">
      <img src="data:image/png;base64,{b64}" alt="{n}">
      <div class="row"><input type="checkbox" data-name="{n}"><span class="fn">{n}</span></div>
      <select data-kind-for="{n}"><option value="footing">ฐานราก</option>
        <option value="column">เสา</option></select>
    </label>''')
        cards.append("</div>")

    page = f"""<!doctype html><meta charset="utf-8"><title>ตรวจ candidate CV ({len(files)} รูป)</title>
<style>
 body{{font-family:system-ui,'Segoe UI',sans-serif;margin:24px;background:#f6f7f9;color:#111}}
 h1{{margin:0 0 4px}} .sub{{color:#666;margin-bottom:20px}}
 h2{{margin:28px 0 8px;font-size:15px}} .n{{color:#888;font-weight:400}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}}
 .card{{background:#fff;border:1px solid #e2e5ea;border-radius:8px;padding:8px;cursor:pointer;display:block}}
 .card:has(input:checked){{border-color:#2066DF;box-shadow:0 0 0 2px #2066df33}}
 .card img{{width:100%;height:150px;object-fit:contain;background:#fafbfc;border-radius:4px}}
 .row{{display:flex;gap:6px;align-items:center;margin:6px 0 4px}}
 .fn{{font-size:10px;color:#666;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
 select{{width:100%;font-size:12px;padding:2px}}
 .bar{{position:sticky;top:0;background:#fff;border:1px solid #e2e5ea;border-radius:8px;
   padding:12px;margin-bottom:16px;z-index:9}}
 button{{background:#2066DF;color:#fff;border:0;border-radius:6px;padding:8px 14px;
   font-size:13px;cursor:pointer}}
 pre{{background:#111;color:#b7f;padding:10px;border-radius:6px;overflow:auto;font-size:12px;
   white-space:pre-wrap;margin:10px 0 0}}
</style>
<h1>ตรวจ candidate ก่อนเข้าคลัง CV</h1>
<div class="sub">{len(files)} รูปจาก {len(by_house)} บ้าน — ติ๊กเฉพาะรูปที่<b>เป็นสัญลักษณ์จริง</b>
 (ไอคอนฐานราก/เสาที่ซ้ำหลายจุดบนแบบ) · วงกลมกริด A/B/C ตัวเลข ตัวอักษร = <b>ห้ามติ๊ก</b>
 ชื่อไฟล์ <code>cand_fromFootingPage__</code> แปลว่า "เก็บมาจากหน้าผังฐานราก" ไม่ใช่ "นี่คือฐานราก"</div>
<div class="bar">
  <button onclick="gen()">สร้างคำสั่ง promote</button>
  <span id="count" style="margin-left:10px;color:#666">ยังไม่ได้เลือก</span>
  <pre id="out" style="display:none"></pre>
</div>
{''.join(cards)}
<script>
function gen() {{
  const byKind = {{}};
  document.querySelectorAll('input[type=checkbox]:checked').forEach(cb => {{
    const name = cb.dataset.name;
    const kind = document.querySelector(`[data-kind-for="${{name}}"]`).value;
    (byKind[kind] = byKind[kind] || []).push(name);
  }});
  const lines = Object.entries(byKind).map(([kind, names]) =>
    `python tools/harvest_templates.py --promote ${{names.join(' ')}} --kind ${{kind}}`);
  const total = Object.values(byKind).flat().length;
  document.getElementById('count').textContent = total ? `เลือก ${{total}} รูป` : 'ยังไม่ได้เลือก';
  const out = document.getElementById('out');
  out.style.display = lines.length ? 'block' : 'none';
  out.textContent = lines.join('\\n\\n') +
    '\\n\\n# หลัง promote: python tools/harvest_templates.py   (รันซ้ำดู coverage ที่ดีขึ้น)';
}}
</script>"""
    OUT.write_text(page, encoding="utf-8")
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"เขียน {OUT} ({size_mb:.1f} MB, {len(files)} รูป จาก {len(by_house)} บ้าน)")
    if a.open:
        webbrowser.open(OUT.as_uri())


if __name__ == "__main__":
    main()
