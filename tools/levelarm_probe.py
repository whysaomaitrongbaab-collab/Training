#!/usr/bin/env python3
"""levelarm_probe.py - level arm of the grid lab (part 3): can printed level labels be read straight from the PDF?

    python tools/levelarm_probe.py --eval            # text layer: recall against grid.z_levels of every GT house (fast)
    python tools/levelarm_probe.py --ocr-eval [N]    # OCR: same question on every N-th level page (~35 s/page on CPU)
    python tools/levelarm_probe.py <house> <page>    # the signed level labels on one page (text layer, no OCR)
    python tools/levelarm_probe.py --demo            # self-check of the two label parsers

King's question (meeting 2026-11-19): structure drawings rarely print levels, so read them from the architectural
sections / elevations. This tool does the cheapest possible first step and measures it: take the text layer of the
page a GT level was read from (`z_levels[].source_image`) and look for a number equal to that level.
It reads NUMBERS only. Which level a number is (ระดับหลังคาน / พื้นชั้น 2 / ...) needs the text next to it, and Thai text
embedded in these PDFs is mostly mojibake, so naming a level is NOT solved here - that stays an OCR/model job.

GT = human-corrected `grid.z_levels` (40 houses, 343 levels, each with the page it was read from), so recall is "of the
levels a person found on that page, how many does the reader also give". It says nothing about levels a person missed, and a
stray `+3.20` that is not a level (e.g. a dimension) can pass as a hit - precision is only bounded, see `evaluate_ocr`.

Measured 2026-11-20, text layer (`--eval`): of the 129 distinct pages the GT levels were read from, 56 have no text at all
and 70 hold only the page number (scans / outlined text); 3 carry real text with level labels. Levels found: 7 of 343 (2%).
=> the text layer cannot be the level route.
OCR (`--ocr-eval 3`, every 3rd page = 43 pages, 106 levels, 94 non-zero): GT level found 75/106 (71%), non-zero 64/94 (68%);
7 of 43 pages gave no signed label; 227 of 250 OCR labels (91%) equal some GT level of that house (lower bound of precision).
Signed labels only (+ - ±); not checked that a number is bound to the right level NAME; every-3rd sample, not random.
Which level is which floor is NOT solved here. Notes: docs/pipeline_5_ส่วน/การบ้าน_2026-11-20.md section 4.
"""
import glob
import json
import os
import re
import sys

import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(ROOT, "image")
GT = os.path.join(ROOT, "json_แก้ไขแล้ว")

# a printed level: optional sign (+ - ± ‑ –), 1-2 integer digits, 2 decimals ("+3.20", "±0.00", "-1.50", "0.15")
LEVEL_RE = re.compile(r"^([+\-−–±]?)(\d{1,2})\.(\d{2})$")
PAGE_RE = re.compile(r"หน้า(\d+)")
TOL = 0.005


def page_levels(page):
    """text layer -> [(value_m, signed, word)] for every word that looks like a printed level."""
    out = []
    for w in page.get_text("words"):
        m = LEVEL_RE.match(w[4].strip())
        if not m:
            continue
        sign, whole, frac = m.groups()
        v = float(f"{whole}.{frac}")
        if sign in ("-", "−", "–"):
            v = -v
        out.append((v, bool(sign), w[4]))
    return out


def house_pdf(gt_dir):
    house = re.sub(r"^\d+", "", os.path.basename(os.path.normpath(gt_dir)))
    return house, os.path.join(IMAGE, house, house + ".pdf")


def evaluate():
    tot = dict(levels=0, nonzero=0, blank_page=0, no_text=0,hit_any=0, hit_signed=0, hit_nonzero_any=0, hit_nonzero_signed=0)
    houses_zero_text = []
    for gd in sorted(glob.glob(os.path.join(GT, "*"))):
        gf = glob.glob(os.path.join(gd, "*gridline.json"))
        house, pdf = house_pdf(gd)
        if not gf or not os.path.exists(pdf):
            continue
        z = (json.load(open(gf[0], encoding="utf-8")).get("grid") or {}).get("z_levels") or []
        doc = fitz.open(pdf)
        cache = {}
        h = dict(levels=0, hit=0, no_text=0)
        for e in z:
            m = PAGE_RE.search(str(e.get("source_image") or ""))
            lv = e.get("level_m")
            if not m or not isinstance(lv, (int, float)) or not (1 <= int(m.group(1)) <= len(doc)):
                continue
            pn = int(m.group(1))
            if pn not in cache:
                cache[pn] = (page_levels(doc[pn - 1]), len(doc[pn - 1].get_text("words")))
            labels, n_words = cache[pn]
            tot["levels"] += 1
            h["levels"] += 1
            nz = abs(lv) > TOL
            tot["nonzero"] += nz
            tot["blank_page"] += n_words == 0
            if not labels:
                tot["no_text"] += 1
                h["no_text"] += 1
                continue
            any_hit = any(abs(v - lv) < TOL or abs(abs(v) - abs(lv)) < TOL and v == 0 for v, s, _ in labels)
            sg_hit = any(abs(v - lv) < TOL for v, s, _ in labels if s)
            tot["hit_any"] += any_hit
            tot["hit_signed"] += sg_hit
            tot["hit_nonzero_any"] += any_hit and nz
            tot["hit_nonzero_signed"] += sg_hit and nz
            h["hit"] += any_hit
        if h["levels"] and h["no_text"] == h["levels"]:
            houses_zero_text.append(house)
    return tot, houses_zero_text


OCR_LEVEL = re.compile(r"([+\-−±])\s?(\d{1,2})[.,](\d{2})(?!\d)")


def ocr_levels(page):
    """scan/outlined page -> signed level labels read by OCR: [(value_m, text)]. Same CPU reader as titleblock_extract
    (Latin/code model - reads digits well, Thai as garbage, which is fine here). Full page <= 3300 px on the long side."""
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import titleblock_extract as T
    W, H = page.rect.width, page.rect.height
    pix = page.get_pixmap(dpi=int(T.MAX_PAGE_PX / (max(W, H) / 72)))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    img = np.ascontiguousarray(img[:, :, :3] if pix.n >= 3 else np.repeat(img, 3, axis=2))
    out = []
    for r in T._reader().predict(img):
        for txt in r.get("rec_texts", []):
            for sign, whole, frac in OCR_LEVEL.findall(txt):
                v = float(f"{whole}.{frac}")
                out.append((-v if sign in ("-", "−") else v, txt))
    return out


def evaluate_ocr(stride=1, cache=None):
    """OCR the distinct pages a GT level was read from, every `stride`-th one in house order (CPU ~35 s/page, so the full
    129 pages is over an hour; a stride keeps the sample spread over all houses instead of the first few).
    recall = GT level of that page seen among the OCR labels; labels_in_gt = share of OCR labels equal to ANY GT level of
    the house (precision proxy: GT may miss real levels, so the true precision is >= this). `cache` = json file, resumable."""
    cp = cache
    cache = json.load(open(cp, encoding="utf-8")) if cp and os.path.exists(cp) else {}
    t = dict(pages=0, levels=0, nonzero=0, hit=0, hit_nonzero=0, labels=0, labels_in_gt=0, pages_zero_labels=0)
    done = seen = 0
    for gd in sorted(glob.glob(os.path.join(GT, "*"))):
        gf = glob.glob(os.path.join(gd, "*gridline.json"))
        house, pdf = house_pdf(gd)
        if not gf or not os.path.exists(pdf):
            continue
        z = (json.load(open(gf[0], encoding="utf-8")).get("grid") or {}).get("z_levels") or []
        doc = fitz.open(pdf)
        house_levels = [e["level_m"] for e in z if isinstance(e.get("level_m"), (int, float))]
        by_page = {}
        for e in z:
            m = PAGE_RE.search(str(e.get("source_image") or ""))
            if m and isinstance(e.get("level_m"), (int, float)) and 1 <= int(m.group(1)) <= len(doc):
                by_page.setdefault(int(m.group(1)), []).append(e["level_m"])
        for pn, gts in sorted(by_page.items()):
            seen += 1
            if seen % stride:
                continue
            key = f"{house}|{pn}"
            if key not in cache:
                cache[key] = [v for v, _ in ocr_levels(doc[pn - 1])]
                done += 1
                if cp and done % 3 == 0:
                    json.dump(cache, open(cp, "w"))
            vals = cache[key]
            t["pages"] += 1
            t["pages_zero_labels"] += not vals
            t["labels"] += len(vals)
            t["labels_in_gt"] += sum(any(abs(v - g) < TOL for g in house_levels) for v in vals)
            for g in gts:
                t["levels"] += 1
                t["nonzero"] += abs(g) > TOL
                h = any(abs(v - g) < TOL for v in vals)
                t["hit"] += h
                t["hit_nonzero"] += h and abs(g) > TOL
    return t, cache


def demo():
    """self-check, no PDF needed: the two level-label parsers on the shapes seen in real drawings"""
    def txt(s):
        m = LEVEL_RE.match(s)
        return None if not m else (-1 if m.group(1) in "-−–" and m.group(1) else 1) * float(f"{m.group(2)}.{m.group(3)}")
    assert txt("+3.75") == 3.75 and txt("-1.50") == -1.5 and txt("±0.00") == 0.0 and txt("0.15") == 0.15
    assert txt("3.7") is None and txt("Ø4\"SW") is None and txt("1:100") is None and txt("0.20ม.") is None
    got = [(("-" if s == "-" else "+") + w + "." + f) for s, w, f in OCR_LEVEL.findall("FL +3.75 ระดับ -0.50 ที่ ±0.00 และ 3.00 +12,30")]
    assert got == ["+3.75", "-0.50", "+0.00", "+12.30"], got   # "3.00" has no sign -> not a level; "," read as "."
    print("levelarm_probe demo OK")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--demo"]:
        demo()
    elif sys.argv[1:2] == ["--ocr-eval"]:
        cp = os.environ.get("LEVEL_OCR_CACHE", "level_ocr_cache.json")
        t, c = evaluate_ocr(int(sys.argv[2]) if len(sys.argv) > 2 else 1, cp)
        json.dump(c, open(cp, "w"))
        n, nz = t["levels"], t["nonzero"]
        print(f"pages OCRed: {t['pages']} · GT levels on them: {n} (non-zero {nz})")
        print(f"OCR found the GT level: {t['hit']}/{n} ({t['hit'] / max(n, 1):.0%}) · non-zero {t['hit_nonzero']}/{nz} ({t['hit_nonzero'] / max(nz, 1):.0%})")
        print(f"pages where OCR read no signed label at all: {t['pages_zero_labels']}")
        print(f"OCR labels: {t['labels']} · equal to a GT level of that house: {t['labels_in_gt']} ({t['labels_in_gt'] / max(t['labels'], 1):.0%}, lower bound of precision)")
    elif sys.argv[1:2] == ["--eval"]:
        t, zero = evaluate()
        n, nz = t["levels"], t["nonzero"]
        print(f"GT levels checked: {n} (non-zero {nz})")
        print(f"source page has no text at all (scan / outlined): {t['blank_page']} ({t['blank_page'] / n:.0%})")
        print(f"source page has no level-like word (incl. the above): {t['no_text']} ({t['no_text'] / n:.0%})")
        print(f"level found in text layer (any number form): {t['hit_any']} ({t['hit_any'] / n:.0%})")
        print(f"level found as a SIGNED label (+ - ±):      {t['hit_signed']} ({t['hit_signed'] / n:.0%})")
        print(f"non-zero levels only: any {t['hit_nonzero_any']}/{nz} ({t['hit_nonzero_any'] / max(nz, 1):.0%})"
              f" signed {t['hit_nonzero_signed']}/{nz} ({t['hit_nonzero_signed'] / max(nz, 1):.0%})")
        print(f"houses where NONE of the level pages has text: {len(zero)}")
    elif len(sys.argv) == 3:
        house, pdf = sys.argv[1], os.path.join(IMAGE, sys.argv[1], sys.argv[1] + ".pdf")
        for v, s, w in page_levels(fitz.open(pdf)[int(sys.argv[2]) - 1]):
            print(f"{v:+.2f}  {'signed' if s else 'plain '}  {w!r}")
    else:
        print(__doc__)
