#!/usr/bin/env python3
"""
tools/run_part1_part3.py — รันส่วน 1 (title block) + ส่วน 3 (grid lab) ของ pipeline King บนบ้านเดียว
สำหรับทดสอบตรรกะ (ประชุม 19 พ.ย. 2569: เสาร์ 21 พ.ย. 22:00 "แต่ละส่วนลองตรรกะ ดูผลเบื้องต้น")

    python tools/run_part1_part3.py <บ้าน>                    # เขียนผลที่ ../logic_test_out/<บ้าน>/
    python tools/run_part1_part3.py <บ้าน> --name             # + ชื่อแผ่นจาก OCR ไทย (ช้า ~5-9 วิ/หน้า)
    python tools/run_part1_part3.py <บ้าน> --fast             # ไม่ OCR เลย (ข้อความฝังอย่างเดียว — ชื่อหัวกริดที่เป็นเส้นจะหาย)
    python tools/run_part1_part3.py <บ้าน> --pages 5-20 --out D:/somewhere
    python tools/run_part1_part3.py <บ้าน> --png              # + หน้าภาพ/ปนบันทึกเป็น PNG 200 dpi (ส่วน 1 "หน้าภาพแปลงเป็น PNG")
    python tools/run_part1_part3.py --demo                   # self-check ของกฎแยกชนิดหน้า

ผลต่อบ้าน: result.json (ทุกหน้า), report.md (สรุปภาษาไทย), overlay_pNN.png (หน้าที่มีกริด)
ขั้นต่อหน้า:
  1. ชนิดหน้า vector / raster / mixed / empty  (นับเส้นเวกเตอร์ ภาพ คำในข้อความฝัง — "ไลบรารีชนิดไฟล์" ของส่วน 1)
  2. title block: titleblock_extract.extract_page ทุกหน้า แล้ว flag_moved ทั้งเล่ม -> สารบัญ (หน้า PDF, รหัสแผ่น, ชื่อแผ่น, ธง)
  3. grid lab: หน้าที่มีแถววงหัวกริดอย่างน้อย 2 วงทั้งสองแกน (เรขาคณิตล้วน ไม่ OCR — คัดเร็ว) -> gridlab_probe.detect()
     แล้ววาด overlay; หน้าภาพ (raster) ยังไม่รองรับ (King: เริ่มจากเวกเตอร์) จึงถูกข้ามและบอกไว้ในรายงาน
ไม่แตะเฉลย ไม่เรียกโมเดล ไม่เขียนอะไรลง repo
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT.parent / "logic_test_out"


def kind_of(n_lines, n_images, n_words):
    """ชนิดหน้าจากจำนวนเส้นเวกเตอร์/ภาพ/คำ (pure) — แบบสแกนในเล่ม CAD มีภาพ 1 ภาพ เส้นแทบไม่มี"""
    if n_lines >= 200:
        return "vector" if n_images == 0 else "mixed"
    if n_images:
        return "raster"
    return "vector" if n_lines or n_words else "empty"


def page_info(page):
    n_lines = sum(it[0] == "l" for d in page.get_drawings() for it in d["items"])
    return dict(n_lines=n_lines, n_images=len(page.get_images()), n_words=len(page.get_text("words")))


def is_grid_candidate(page):
    """มีแถววงหัวกริด (>= 2 วงที่มีก้าน/เส้น) ทั้งแกนตั้งและแกนนอน — ยังไม่อ่านชื่อ (ไม่ OCR)"""
    import gridlab_probe as G
    W, H = page.rect.width, page.rect.height
    bl = G.bubble_lines(G.circles(page), G.segments(page), W, H)
    return len(bl["v"]) >= 2 and len(bl["h"]) >= 2


def parse_pages(spec, n):
    if not spec:
        return range(n)
    a, _, b = spec.partition("-")
    return range(int(a) - 1, min(int(b or a), n))


def run(house, out_dir, ocr=True, with_name=False, pages=None, png=False):
    import fitz
    import gridlab_probe as G
    import gridlab_scale as S
    import titleblock_extract as T
    out = Path(out_dir) / house
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(T.pdf_of(house))
    t0, recs, tbs = time.time(), [], []
    for i in parse_pages(pages, len(doc)):
        page = doc[i]
        info = page_info(page)
        rec = dict(pdf_page=i + 1, kind=kind_of(**info), **info)
        if png and rec["kind"] in ("raster", "mixed"):    # ส่วน 1: "หน้าภาพแปลงเป็น PNG" (200 dpi = เดียวกับภาพเทรน)
            rec["png"] = str(out / f"page_p{i + 1:02d}.png")
            page.get_pixmap(dpi=200).save(rec["png"])
        tb = T.extract_page(page, use_ocr=ocr, with_name=with_name)
        tbs.append(tb)
        rec["title"] = tb
        rec["grid"] = None
        if rec["kind"] in ("vector", "mixed") and is_grid_candidate(page):
            lines = G.detect(page, ocr=ocr)
            scales = S.plan_scales(page, lines, ocr=ocr)     # ตั้งสเกลต่อแปลน -> ใส่ pos_m ลงในเส้น
            png = out / f"overlay_p{i + 1:02d}.png"
            G.draw_page(house, i + 1, str(png), page=page, lines=lines)
            rec["grid"] = dict(overlay=str(png), plans=len({ln.get("plan") for ax in lines for ln in lines[ax]}),
                               scales={str(k): dict(scale_pt_per_m=v["scale"], source=v["source"]) for k, v in scales.items()},
                               lines={ax: [{k: v for k, v in ln.items() if k in
                                            ("pos", "pos_m", "lo", "hi", "label", "src", "method", "kind", "plan")}
                                           for ln in lines[ax]] for ax in lines})
        recs.append(rec)
        print(f"  หน้า {i + 1}: {rec['kind']} รหัส={tb.get('sheet_code')}"
              + (f" กริด {len(rec['grid']['lines']['v'])}x{len(rec['grid']['lines']['h'])}" if rec["grid"] else ""), flush=True)
    T.flag_moved(tbs)    # ใส่ "flag" ลงใน dict เดียวกับ rec["title"]
    result = dict(house=house, pages=recs, seconds=round(time.time() - t0, 1), ocr=ocr, with_name=with_name)
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (out / "report.md").write_text(report(result), encoding="utf-8")
    return out


def report(r):
    pages = r["pages"]
    kinds = {}
    for p in pages:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    found = [p for p in pages if p["title"].get("found")]
    flagged = [p for p in pages if p["title"].get("flag")]
    grid = [p for p in pages if p["grid"]]
    L = [f"# {r['house']} — ส่วน 1 (title block) + ส่วน 3 (grid lab)", "",
         f"รัน {len(pages)} หน้า ใน {r['seconds']} วินาที · OCR={'เปิด' if r['ocr'] else 'ปิด'} · ชื่อแผ่น={'อ่าน' if r['with_name'] else 'ไม่อ่าน'}", "",
         "## ส่วน 1 — ชนิดหน้าและสารบัญจาก title block", "",
         "ชนิดหน้า: " + " · ".join(f"{k} {v}" for k, v in sorted(kinds.items())), "",
         f"หารหัสแผ่นเจอ {len(found)}/{len(pages)} หน้า · ติดธง {len(flagged)} หน้า", "",
         "| หน้า PDF | ชนิด | รหัสแผ่น | ที่มา | ชื่อแผ่น | ธง |", "|---|---|---|---|---|---|"]
    for p in pages:
        t = p["title"]
        L.append(f"| {p['pdf_page']} | {p['kind']} | {t.get('sheet_code') or '—'} | {t.get('source') or '—'} | "
                 f"{t.get('sheet_name') or '—'} | {t.get('flag') or ''} |")
    L += ["", "## ส่วน 3 — grid lab (หน้าเวกเตอร์ที่มีวงหัวกริดทั้งสองแกน)", "",
          f"หน้าที่มีกริด {len(grid)} หน้า (หน้าภาพ {kinds.get('raster', 0)} หน้ายังไม่รองรับ — เริ่มจากเวกเตอร์ตามที่ King สั่ง)", "",
          "| หน้า PDF | รหัสแผ่น | แปลน | สเกล (pt/m) | เส้นตั้ง (x) ชื่อ@เมตร | เส้นนอน (y) ชื่อ@เมตร | ภาพ |",
          "|---|---|---|---|---|---|---|"]
    for p in grid:
        g = p["grid"]
        for pid in sorted(g["scales"], key=int) or ["-"]:
            sc = g["scales"].get(pid, {})

            def lab(ax):
                ls = sorted((ln for ln in g["lines"][ax] if pid == "-" or str(ln.get("plan")) == pid), key=lambda l: l["pos"])
                return ", ".join(f"{ln['label'] or '?'}@{ln['pos_m']}" if ln.get("pos_m") is not None else (ln["label"] or "?")
                                 for ln in ls) or "—"
            L.append(f"| {p['pdf_page']} | {p['title'].get('sheet_code') or '—'} | {pid} | "
                     f"{sc.get('scale_pt_per_m') or '—'} ({sc.get('source') or 'ไม่มีตัวเลขระยะที่ยืนยันได้'}) | "
                     f"{lab('v')} | {lab('h')} | {Path(g['overlay']).name} |")
    L += ["", "ภาพ overlay: เส้นแดง = เส้นตั้ง (แกน x), น้ำเงิน = เส้นนอน (แกน y), วงเขียว = วงหัวกริดที่ใช้, '?' = อ่านชื่อไม่ได้",
          "เมตร (pos_m) = ระยะจากเส้นแรกของแปลน (ซ้ายสุด/บนสุด) ตามสเกลที่อ่านจากตัวเลขบอกระยะบนแบบ (gridlab_scale.py)"
          " — ไม่มีตัวเลขที่ยืนยันได้ = ไม่ให้เมตร (ไม่เดาจากโน้ตมาตราส่วน)", ""]
    return "\n".join(L)


def demo():
    assert kind_of(5000, 0, 300) == "vector"
    assert kind_of(0, 1, 1) == "raster"          # หน้าสแกนในเล่ม CAD (1ชั้น_07 หน้า 20: เส้น 0 ภาพ 1)
    assert kind_of(23, 11, 244) == "raster"      # ภาพหลายชิ้น + ข้อความฝัง แต่ไม่มีเส้นแบบ (2ชั้น_22 หน้า 14)
    assert kind_of(900, 2, 50) == "mixed"
    assert kind_of(0, 0, 0) == "empty" and kind_of(0, 0, 12) == "vector"
    assert list(parse_pages("3-5", 10)) == [2, 3, 4] and list(parse_pages(None, 2)) == [0, 1]
    print("OK — self-check ผ่าน (กฎแยกชนิดหน้า/ช่วงหน้า)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("house", nargs="?")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--fast", action="store_true", help="ไม่ OCR (ข้อความฝังอย่างเดียว)")
    ap.add_argument("--name", action="store_true", help="อ่านชื่อแผ่นด้วย OCR ไทย")
    ap.add_argument("--pages")
    ap.add_argument("--png", action="store_true", help="บันทึกหน้าภาพ/ปนเป็น PNG 200 dpi")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not a.house:
        ap.print_help()
        return
    out = run(a.house, a.out, ocr=not a.fast, with_name=a.name, pages=a.pages, png=a.png)
    print("เขียนผลไว้ที่", out)


if __name__ == "__main__":
    main()
