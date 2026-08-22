#!/usr/bin/env python3
"""md_to_book_pdf.py — แปลง .md เป็นหน้า PDF แล้วต่อท้ายหนังสือเล่มเดิม

ใช้ Edge/Chrome headless เป็นตัวเรนเดอร์ (ไม่ใช่ reportlab) เพราะภาษาไทยต้องการ
text shaping ที่ถูกต้อง — สระบน/ล่างและวรรณยุกต์ต้องซ้อนตำแหน่งให้ถูก ซึ่ง
เบราว์เซอร์ทำได้ ส่วน reportlab วางเรียงกันเป็นตัวๆ แล้วสระลอย

    python tools/md_to_book_pdf.py "workmen's_diary/2026-08-21(teach mk).md" \
        --append-to "workmen's_diary/สอน_AI_อ่านแบบบ้าน_รวม_21-24กค.pdf"

ไม่ใส่ --append-to = ได้ PDF เดี่ยวข้างๆ ไฟล์ .md
ของเดิมถูกสำรองเป็น <ชื่อไฟล์>.bak.pdf ก่อนเขียนทับเสมอ
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader, PdfWriter

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

# Tahoma = ฟอนต์เดียวกับเล่มเดิม (ตรวจจาก /BaseFont ในไฟล์ PDF ต้นฉบับ)
CSS = """
@page { size: A4; margin: 18mm 16mm 16mm 16mm; }
body { font-family: Tahoma, "Leelawadee UI", "Sarabun", sans-serif;
       font-size: 10.5pt; line-height: 1.75; color: #1a1a1a; }
h1 { font-size: 19pt; border-bottom: 3px solid #2066DF; padding-bottom: 8px;
     margin: 0 0 18px; color: #10315e; }
h2 { font-size: 14pt; margin: 26px 0 10px; color: #10315e;
     border-left: 5px solid #2066DF; padding-left: 10px; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 18px 0 6px; color: #333; page-break-after: avoid; }
p, li { orphans: 2; widows: 2; }
blockquote { background: #eef4ff; border-left: 4px solid #2066DF; margin: 14px 0;
             padding: 10px 14px; page-break-inside: avoid; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 9.5pt;
        page-break-inside: avoid; }
th, td { border: 1px solid #c4c4c4; padding: 6px 9px; text-align: left;
         vertical-align: top; }
th { background: #e8eef8; }
code { font-family: Consolas, monospace; background: #f2f2f2; padding: 1px 4px;
       border-radius: 3px; font-size: 9pt; }
pre { background: #f7f7f7; border: 1px solid #ddd; border-radius: 4px;
      padding: 10px 12px; overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.5pt; line-height: 1.5; }
hr { border: 0; border-top: 1px solid #ddd; margin: 22px 0; }
strong { color: #10315e; }
"""


def find_browser():
    for b in BROWSERS:
        if Path(b).is_file():
            return b
    sys.exit("หาเบราว์เซอร์ไม่เจอ — ต้องมี Edge หรือ Chrome")


def md_to_pdf(md_path: Path, out_pdf: Path):
    html_body = markdown.markdown(
        md_path.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    html = (f'<!doctype html><html lang="th"><head><meta charset="utf-8">'
            f"<style>{CSS}</style></head><body>{html_body}</body></html>")

    # เขียน html ลง temp dir — ชื่อไฟล์ต้องไม่มีอักษรไทย/ช่องว่าง เพราะ
    # --print-to-pdf ของ Chromium จัดการ path แบบนั้นได้ไม่ดีบน Windows
    with tempfile.TemporaryDirectory() as td:
        tmp_html = Path(td) / "page.html"
        tmp_pdf = Path(td) / "page.pdf"
        tmp_html.write_text(html, encoding="utf-8")
        subprocess.run(
            [find_browser(), "--headless", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={tmp_pdf}", "--no-pdf-header-footer",
             tmp_html.as_uri()],
            check=True, capture_output=True, timeout=180,
        )
        if not tmp_pdf.is_file():
            sys.exit("เบราว์เซอร์ไม่ได้สร้างไฟล์ PDF ออกมา")
        out_pdf.write_bytes(tmp_pdf.read_bytes())
    return out_pdf


def append_to_book(new_pdf: Path, book: Path):
    backup = book.with_suffix(".bak.pdf")
    backup.write_bytes(book.read_bytes())          # สำรองก่อนเสมอ
    w = PdfWriter()
    for src in (book, new_pdf):
        for page in PdfReader(str(src)).pages:
            w.add_page(page)
    with open(book, "wb") as fh:
        w.write(fh)
    return backup, len(PdfReader(str(book)).pages)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--append-to", default=None)
    a = ap.parse_args()

    md = Path(a.md)
    made = md_to_pdf(md, md.with_suffix(".pdf"))
    print(f"สร้าง {made.name} — {len(PdfReader(str(made)).pages)} หน้า")

    if a.append_to:
        book = Path(a.append_to)
        before = len(PdfReader(str(book)).pages)
        bak, after = append_to_book(made, book)
        print(f"ต่อท้าย {book.name}: {before} → {after} หน้า (สำรองไว้ที่ {bak.name})")
