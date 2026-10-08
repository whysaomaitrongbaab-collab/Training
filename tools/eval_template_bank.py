#!/usr/bin/env python3
"""eval_template_bank.py — วัดคลัง template ทั้งคลังด้วยทางเดียวกับ production (analyze())

ทุกหน้าที่มีจำนวนคาดหวัง: GT (json_แก้ไขแล้ว/, คนแก้แล้ว) + rawjson (ยังไม่มีคนตรวจ — ติดป้าย raw)
บ้านที่มีใน GT ใช้ GT เท่านั้น · จำนวนต่อหน้า = รวมทุกไฟล์ plan ของหน้านั้น (หน้าเดียวมีหลาย view)
  footing: ขาด < 70% · เกิน > 160% · หน้าผังคานที่ไม่มีผังฐานรากเลย = ฐานรากที่เจอทั้งหมดคือ FP
  column : เกณฑ์เดียวกัน (จำนวนเสามักบันทึกไว้ไฟล์เดียวต่อบ้าน — หน้าที่ไม่มีเลขเสาไม่นับ)

    python tools/eval_template_bank.py                       # baseline → pattern_out/eval_bank.txt
    python tools/eval_template_bank.py --add-footing a.png   # ลอง candidate โดยยังไม่ promote
    python tools/eval_template_bank.py --tag after --only 54 55   # กรองบ้าน (เลขโฟลเดอร์/ชื่อ)

อ่านอย่างเดียว เขียนแค่ tools/pattern_out/
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from pattern_recognition import imread_thai, load_templates, analyze  # noqa: E402

TRAINING = HERE.parent
ROOTS = (("gt", TRAINING / "json_แก้ไขแล้ว"), ("raw", TRAINING / "rawjson_ยังไม่ได้แก้ไขโดนคน"))
IMG_ROOT = TRAINING / "image"
OUT = HERE / "pattern_out"


def _els(d):
    els = list(d.get("elements") or [])
    for v in d.get("views") or []:
        if isinstance(v, dict):
            els += v.get("elements") or []
    return [e for e in els if isinstance(e, dict)]


def _count(els, types):
    n = 0
    for e in els:
        if (e.get("element_type") or "") in types:
            c = e.get("count")
            if not isinstance(c, (int, float)) or not c:
                c = len(e.get("grid_refs") or []) or 1
            n += c
    return int(n)


def expected_pages():
    """{(house, page): {"src", "footing", "column", "beam", "has_fplan", "has_bplan"}}"""
    pages = {}
    gt_houses = {re.sub(r"^\d+", "", p.name) for p in ROOTS[0][1].iterdir() if p.is_dir()}
    for src, root in ROOTS:
        for f in sorted(root.glob("*/*.json")):
            house = re.sub(r"^\d+", "", f.parent.name)
            if src == "raw" and house in gt_houses:
                continue
            m = re.search(r"หน้า(\d+)", f.name)
            lb = f.name.lower()
            fplan = "plan" in lb and "footing" in lb
            bplan = "beam" in lb and "plan" in lb
            if not m or not (fplan or bplan):
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            els = _els(d)
            p = pages.setdefault((house, m.group(1)), {"src": src, "footing": 0, "column": 0,
                                                       "beam": 0, "has_fplan": False,
                                                       "has_bplan": False})
            if fplan:
                p["has_fplan"] = True
                p["footing"] += _count(els, ("footing", "pile_cap"))
            if bplan:
                p["has_bplan"] = True
                p["beam"] += _count(els, ("beam", "tie_beam"))
            p["column"] += _count(els, ("column", "pedestal"))
    return pages


_T = None


def _init(extra_f, extra_c):
    global _T
    _T = load_templates()
    _T["footing"] += [imread_thai(p) for p in extra_f]
    _T["column"] += [imread_thai(p) for p in extra_c]


def _scan(key):
    house, page = key
    img = IMG_ROOT / house / f"{house}_หน้า{page}.png"
    if not img.exists():
        return key, None
    det = analyze(imread_thai(img), _T["footing"], _T["column"])
    return key, {k: [list(map(float, b)) for b in v] for k, v in det.items()}


def grade(exp, n):
    if exp <= 0:
        return None
    if n > exp * 1.6:
        return "over"
    return "ok" if n >= exp * 0.7 else "short"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--add-footing", nargs="*", default=[])
    ap.add_argument("--add-column", nargs="*", default=[])
    ap.add_argument("--only", nargs="*", help="กรองบ้าน: ส่วนหนึ่งของชื่อบ้าน")
    ap.add_argument("--tag", default="bank")
    a = ap.parse_args()

    pages = expected_pages()
    keys = [k for k in sorted(pages) if not a.only or any(o in k[0] for o in a.only)]
    with Pool(20, _init, (a.add_footing, a.add_column)) as pool:
        res = dict(pool.map(_scan, keys))

    lines = [f"{'บ้าน':<26}{'หน้า':>5} src  {'F exp':>5}{'F got':>6}  F     "
             f"{'C exp':>5}{'C got':>6}  C     {'B exp':>5}{'runs':>5}"]
    tot = {"footing": defaultdict(int), "column": defaultdict(int)}
    fp_pages, fp_total = 0, 0
    for k in keys:
        e, det = pages[k], res[k]
        if det is None:
            lines.append(f"{k[0]:<26}{k[1]:>5} {e['src']:<4} ไม่มีภาพ")
            continue
        nf, nc = len(det["footing"]), len(det["column"])
        nb = len(det["beam_h"]) + len(det["beam_v"])
        gf = grade(e["footing"], nf) if e["has_fplan"] else None
        gc = grade(e["column"], nc)
        if gf:
            tot["footing"][gf] += 1
        if gc:
            tot["column"][gc] += 1
        fpm = ""
        if e["has_bplan"] and not e["has_fplan"] and nf:
            fp_pages += 1
            fp_total += nf
            fpm = f"  FPฐานราก {nf}"
        lines.append(f"{k[0]:<26}{k[1]:>5} {e['src']:<4} {e['footing']:>5}{nf:>6}  "
                     f"{(gf or '-'):<6}{e['column']:>5}{nc:>6}  {(gc or '-'):<6}"
                     f"{e['beam']:>5}{nb:>5}{fpm}")
    for cls in ("footing", "column"):
        t = tot[cls]
        lines.append(f"\n{cls}: ok {t['ok']} | short {t['short']} | over {t['over']}")
    lines.append(f"FP ฐานรากบนหน้าผังคานล้วน: {fp_pages} หน้า รวม {fp_total} จุด")
    lines.append(f"extra footing={a.add_footing} column={a.add_column}")
    OUT.mkdir(exist_ok=True)
    report = "\n".join(lines)
    (OUT / f"eval_{a.tag}.txt").write_text(report, encoding="utf-8")
    (OUT / f"eval_{a.tag}_det.json").write_text(
        json.dumps({f"{h}|{p}": v for (h, p), v in res.items()}, ensure_ascii=False),
        encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
