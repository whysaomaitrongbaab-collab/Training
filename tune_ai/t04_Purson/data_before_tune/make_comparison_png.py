#!/usr/bin/env python3
"""สร้างภาพ PNG เปรียบเทียบผลทูน จาก JSON ไฟล์เดียว (stdlib ล้วน ไม่ต้อง pip install อะไร)

วิธีใช้:
    python make_comparison_png.py
    python make_comparison_png.py --data comparison_data.json --out ../ชื่อไฟล์.png

เรนเดอร์ด้วย Microsoft Edge headless (มีติดเครื่องอยู่แล้ว) — ไม่ใช้ matplotlib/puppeteer
ค่า null ใน values = "ยังไม่ได้วัด" → แสดง n/a / — ไม่ใช่ 0%
"""
import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
WIDTH = 1200
PLOT_H = 420          # ความสูงพื้นที่กราฟ (px) — ต้องตรงกับ CSS
FONT = "'Sarabun','Noto Sans Thai','Leelawadee UI','Tahoma',sans-serif"


def esc(s):
    return html.escape(str(s if s is not None else ""))


def bold(s):
    """**ข้อความ** → <strong>ข้อความ</strong> (escape ก่อนเสมอ)"""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))


def nlines(text, chars_per_line):
    """เดาจำนวนบรรทัดหลัง word-wrap แบบหยาบๆ เอาไว้คำนวณความสูงหน้าต่าง"""
    if not text:
        return 0
    return max(1, math.ceil(len(str(text)) / float(chars_per_line)))


# ---------------------------------------------------------------- HTML pieces

def render_legend(series):
    out = []
    for s in series:
        out.append(
            '<span class="lg"><i style="background:%s"></i>%s</span>'
            % (esc(s.get("color", "#888")), esc(s.get("name", "")))
        )
    return "".join(out)


def fmt_pct(v):
    if v is None:
        return None
    return ("%.1f" % v).rstrip("0").rstrip(".") + "%"


def render_chart(data):
    series = data["series"]
    groups = []
    for m in data["metrics"]:
        bars = []
        for i, s in enumerate(series):
            v = m["values"][i] if i < len(m["values"]) else None
            if v is None:
                bars.append('<div class="bc"><div class="na">n/a</div></div>')
            else:
                h = max(0.0, min(100.0, float(v)))
                bars.append(
                    '<div class="bc"><div class="bar" style="height:%.2f%%;background:%s">'
                    '<span class="val">%s</span></div></div>'
                    % (h, esc(s.get("color", "#888")), esc(fmt_pct(v)))
                )
        groups.append('<div class="grp">%s</div>' % "".join(bars))

    xlabels = "".join('<div class="xl">%s</div>' % esc(m["label"]) for m in data["metrics"])
    gridlines = "".join('<i style="bottom:%d%%"></i>' % p for p in (0, 25, 50, 75, 100))
    yticks = "".join("<div>%d%%</div>" % p for p in (100, 75, 50, 25, 0))
    return """
  <div class="legend">%s</div>
  <div class="chart">
    <div class="yax">%s</div>
    <div class="plotwrap">
      <div class="plot"><div class="gridlines">%s</div>%s</div>
      <div class="xlabels">%s</div>
    </div>
  </div>""" % (render_legend(series), yticks, gridlines, "".join(groups), xlabels)


def render_table(data):
    series = data["series"]
    head = "".join("<th>%s</th>" % esc(s.get("name", "")) for s in series)
    rows = []
    for m in data["metrics"]:
        cells = []
        for i in range(len(series)):
            v = m["values"][i] if i < len(m["values"]) else None
            raw = (m.get("raw") or [])
            r = raw[i] if i < len(raw) else ""
            if v is None:
                cells.append('<td><span class="dash">—</span></td>')
            else:
                frac = ' <span class="frac">(%s)</span>' % esc(r) if r else ""
                cells.append('<td><b>%s</b>%s</td>' % (esc(fmt_pct(v)), frac))
        rows.append("<tr><td class=\"mlab\">%s</td>%s</tr>" % (esc(m["label"]), "".join(cells)))
    return '<table><thead><tr><th>ตัวชี้วัด</th>%s</tr></thead><tbody>%s</tbody></table>' % (
        head, "".join(rows))


def build_html(data):
    return """<!doctype html>
<html lang="th"><head><meta charset="utf-8"><title>comparison</title><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:%(font)s;background:#fff;color:#1f2933;width:%(w)dpx}
.hdr{background:linear-gradient(100deg,#0d3540 0%%,#155461 55%%,#1a6675 100%%);
     padding:38px 48px 34px;color:#fff}
.hdr h1{font-size:31px;font-weight:700;line-height:1.32;letter-spacing:-.2px}
.hdr p{margin-top:11px;font-size:15px;color:#bcd2d7;line-height:1.5}
.body{padding:26px 48px 34px}
.warn{border:1.6px solid #d94a4a;background:#fdeff0;border-radius:7px;
      padding:16px 20px;font-size:14.5px;line-height:1.75;color:#3a2b2b}
.warn strong{color:#a52020}
.sec{margin-top:30px;display:flex;align-items:center;gap:9px;
     font-size:14.5px;font-weight:700;color:#28323c}
.sec::before{content:"";width:4px;height:17px;background:#2b7fd4;border-radius:2px}
.legend{margin:16px 0 6px;display:flex;gap:26px;font-size:13px;color:#42505d}
.lg{display:flex;align-items:center;gap:8px}
.lg i{width:13px;height:13px;border-radius:2px;display:inline-block}
.chart{display:flex;margin-top:26px} /* เผื่อที่ให้ป้ายตัวเลขเหนือแท่งเต็มสเกล ไม่ทับ legend */
.yax{width:52px;height:%(ph)dpx;display:flex;flex-direction:column;
     justify-content:space-between;font-size:12px;color:#8d99a6;text-align:right;
     padding-right:10px}
.yax div{transform:translateY(-50%%)}
.yax div:first-child{transform:translateY(0)}
.yax div:last-child{transform:translateY(-100%%)}
.plotwrap{flex:1}
.plot{position:relative;height:%(ph)dpx;display:flex;
      border-bottom:1.5px solid #c6ced6}
.gridlines i{position:absolute;left:0;right:0;height:1px;background:#e8ecf0}
.gridlines i[style*="bottom:0%%"]{background:transparent}
.grp{flex:1;display:flex;align-items:flex-end;justify-content:center;gap:10px;
     position:relative;z-index:1}
.bc{width:40px;height:100%%;display:flex;align-items:flex-end;justify-content:center}
.bar{width:100%%;position:relative;border-radius:2px 2px 0 0;min-height:2px}
.val{position:absolute;bottom:100%%;left:50%%;transform:translateX(-50%%);
     margin-bottom:6px;font-size:13px;font-weight:700;color:#2c3742;white-space:nowrap}
.na{font-size:12.5px;color:#a9b3bd;font-style:italic;padding-bottom:5px;white-space:nowrap}
.xlabels{display:flex;margin-top:11px}
.xl{flex:1;text-align:center;font-size:12.5px;color:#4a5866;line-height:1.4;padding:0 4px}
table{width:100%%;border-collapse:collapse;margin-top:14px;font-size:14px}
thead th{background:#16232e;color:#fff;text-align:left;font-weight:600;
         padding:13px 16px;font-size:13.5px}
tbody td{padding:12px 16px;border-bottom:1px solid #eaeef2;color:#25303b}
tbody tr:last-child td{border-bottom:none}
.mlab{color:#3a4551}
.frac{font-size:12px;color:#8d99a6;font-weight:400}
.dash{color:#a9b3bd}
.foot{margin-top:26px;padding-top:16px;border-top:1px solid #e6eaee;
      font-size:12.5px;color:#8b96a1;line-height:1.65}
</style></head><body>
<div class="hdr"><h1>%(title)s</h1><p>%(sub)s</p></div>
<div class="body">
  <div class="warn">⚠️ %(warn)s</div>
  <div class="sec">ผลวัด</div>%(chart)s
  <div class="sec">ตัวเลขเต็ม</div>%(table)s
  <div class="foot">%(foot)s</div>
</div></body></html>""" % {
        "font": FONT, "w": WIDTH, "ph": PLOT_H,
        "title": esc(data.get("title", "")),
        "sub": esc(data.get("subtitle", "")),
        "warn": bold(data.get("warning", "")),
        "chart": render_chart(data),
        "table": render_table(data),
        "foot": esc(data.get("footer", "")),
    }


def estimate_height(data):
    """เดาความสูงหน้าเพื่อสั่ง --window-size ให้ไม่โดนตัด (เผื่อไว้เสมอ)"""
    h = 38 + nlines(data.get("title"), 60) * 41 + 11 + nlines(data.get("subtitle"), 130) * 23 + 34
    h += 26 + 36 + nlines(data.get("warning"), 128) * 26 + 4          # warning box
    h += 30 + 20 + 22 + 6 + 8 + PLOT_H + 11 + 40                      # section + legend + chart
    h += 30 + 20 + 14 + 45 + len(data["metrics"]) * 45                # section + table
    h += 26 + 16 + nlines(data.get("footer"), 155) * 21 + 34          # footer + padding
    return int(h) + 24


def measure_height(html_text, tmp):
    """วัดความสูงจริงของหน้าด้วย Edge รอบแรก (--dump-dom)

    JS ใช้แค่ "บอกความสูงกลับมา" เท่านั้น ตัวกราฟยัง layout ด้วย CSS ล้วน
    ถ้ารอบวัดล้มเหลวจะคืน None แล้วไปใช้ estimate_height() แทน
    """
    src = os.path.join(tmp, "measure.html")
    with open(src, "w", encoding="utf-8") as f:
        f.write(html_text.replace(
            "</body>",
            '<script>document.title="PGH="+document.documentElement.scrollHeight</script></body>'))
    try:
        r = subprocess.run(
            [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--window-size=%d,900" % WIDTH, "--virtual-time-budget=2000",
             "--user-data-dir=" + os.path.join(tmp, "prof_m"), "--dump-dom",
             "file:///" + src.replace("\\", "/")],
            capture_output=True, timeout=120)
    except Exception:
        return None
    m = re.search(rb"PGH=(\d+)", r.stdout or b"")
    return int(m.group(1)) if m else None


def shoot(html_text, out_png, height, fallback=1400):
    """เรนเดอร์ HTML → PNG ด้วย Edge headless

    หมายเหตุ: --screenshot ต้องเป็น *absolute path* เสมอ ไม่งั้นจะได้
    'Failed to write file ...: Access is denied. (0x5)' เพราะ Edge resolve
    path สัมพัทธ์เทียบ cwd ที่มันเขียนไม่ได้ และต้องมี --user-data-dir ของตัวเอง
    กันชนกับ Edge ที่เปิดอยู่ ส่วนปลายทางเซฟลง temp (ชื่อ ASCII) ก่อนแล้วค่อย
    ย้าย เพื่อเลี่ยงปัญหา path ภาษาไทย
    """
    tmp = tempfile.mkdtemp(prefix="cmp_png_")
    try:
        src = os.path.join(tmp, "page.html")
        shot = os.path.join(tmp, "shot.png")
        with open(src, "w", encoding="utf-8") as f:
            f.write(html_text)
        if not height:
            height = (measure_height(html_text, tmp) or fallback) + 8
        cmd = [
            EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--force-device-scale-factor=1",
            "--window-size=%d,%d" % (WIDTH, height),
            "--virtual-time-budget=3000",
            "--user-data-dir=" + os.path.join(tmp, "prof"),
            "--screenshot=" + shot,
            "file:///" + src.replace("\\", "/"),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if not os.path.exists(shot):
            sys.exit("เรนเดอร์ไม่สำเร็จ (exit %s)\n%s\n%s" % (r.returncode, r.stdout, r.stderr))
        os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
        shutil.move(shot, out_png)
        return os.path.getsize(out_png)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def selfcheck():
    d = {"title": "t", "subtitle": "s", "warning": "w", "footer": "f",
         "series": [{"name": "A", "color": "#111"}, {"name": "B", "color": "#222"}],
         "metrics": [{"label": "m", "values": [None, 96.0], "raw": ["", "24/25"]}]}
    c, t = render_chart(d), render_table(d)
    assert 'class="na">n/a' in c, "null ต้องเป็น n/a"
    assert c.count('class="bar"') == 1, "2 ซีรีส์ null 1 → ต้องมีแท่งเดียว"
    assert "height:0" not in c, "null ห้ามกลายเป็นแท่ง 0%"
    assert "96%" in c and "height:96.00%" in c
    assert "—" in t and "(24/25)" in t and "<b>96%</b>" in t
    assert "<strong>x</strong>" in bold("**x**") and "&lt;" in bold("<")   # escape ก่อน bold
    assert estimate_height(d) < estimate_height(dict(d, warning="ก" * 800))
    print("selfcheck OK")


def main():
    p = argparse.ArgumentParser(description="สร้าง PNG เปรียบเทียบผลทูนจาก JSON")
    p.add_argument("--data", default=os.path.join(HERE, "comparison_data.json"))
    p.add_argument("--out", default=os.path.join(HERE, "..", "เปรียบเทียบผลทูน_t03_2026-08-25.png"))
    p.add_argument("--height", type=int, default=0, help="บังคับความสูงหน้าต่าง (ปกติคำนวณเอง)")
    p.add_argument("--keep-html", default="", help="เซฟ HTML ไว้ดูด้วย (path)")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return selfcheck()

    with open(a.data, encoding="utf-8") as f:
        data = json.load(f)
    doc = build_html(data)
    if a.keep_html:
        with open(a.keep_html, "w", encoding="utf-8") as f:
            f.write(doc)
    out = os.path.abspath(a.out)
    size = shoot(doc, out, a.height, fallback=estimate_height(data))
    print("เขียนแล้ว: %s (%.1f KB)" % (out, size / 1024.0))


if __name__ == "__main__":
    main()
