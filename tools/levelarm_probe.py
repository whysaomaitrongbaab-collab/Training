#!/usr/bin/env python3
"""levelarm_probe.py - level arm of the grid lab (part 3): can printed level labels be read straight from the PDF?

    python tools/levelarm_probe.py --eval            # text layer: recall against grid.z_levels of every GT house (fast)
    python tools/levelarm_probe.py --ocr-eval [N]    # OCR: same question on every N-th level page (~35 s/page on CPU)
    python tools/levelarm_probe.py --name-eval [N] [cache.json] [--show]
                                                     # + bind each OCR number to the name printed next to it
                                                     #   (Thai reader too, ~1 min/page; cache.json resumes / re-scores)
    python tools/levelarm_probe.py <house> <page>    # the signed level labels on one page (text layer, no OCR)
    python tools/levelarm_probe.py --demo            # self-check: label parsers + name binding (no PDF needed)

King's question (meeting 2026-11-19): structure drawings rarely print levels, so read them from the architectural
sections / elevations. This tool does the cheapest possible first step and measures it: take the text layer of the
page a GT level was read from (`z_levels[].source_image`) and look for a number equal to that level.
NUMBERS: text layer, then OCR. NAMES (which level a number is: ระดับหลังคาน / พื้นชั้น 2 / ...): Thai text embedded in
these PDFs is mostly mojibake, so names come from the Thai OCR reader on the same page image (`bind_names`).

GT = human-corrected `grid.z_levels` (40 houses, 343 levels, each with the page it was read from), so recall is "of the
levels a person found on that page, how many does the reader also give". It says nothing about levels a person missed, and a
stray `+3.20` that is not a level (e.g. a dimension) can pass as a hit - precision is only bounded, see `evaluate_ocr`.

Measured 2026-11-20, text layer (`--eval`): of the 129 distinct pages the GT levels were read from, 56 have no text at all
and 70 hold only the page number (scans / outlined text); 3 carry real text with level labels. Levels found: 7 of 343 (2%).
=> the text layer cannot be the level route.
OCR (`--ocr-eval 3`, every 3rd page = 43 pages, 106 levels, 94 non-zero): GT level found 75/106 (71%), non-zero 64/94 (68%);
7 of 43 pages gave no signed label; 227 of 250 OCR labels (91%) equal some GT level of that house (lower bound of precision).
Signed labels only (+ - ±); every-3rd sample, not random. Notes: docs/pipeline_5_ส่วน/การบ้าน_2026-11-20.md section 4.

Names, measured 2026-11-21 (`--name-eval 3`, the same 43 pages; numbers = the Latin reading above, identical on all 43
pages; names = th_PP-OCRv5_mobile_rec on the same image - both readers share one detector, so they return the same boxes).
Of the 106 GT levels 30 have no printed Thai name to compare (id None 16, bare number 6, English / annotator slug 6, the
bare word 'ระดับ' 2); 76 do, and their number was found for 60. Of those 60: name_sim >= 0.8 to the GT id (name_key of
titleblock_extract) 48 (80%) · wrong name 11 · no name 1. 'core' (the shared 'ระดับ' in front and an annotator '(...)'
dropped) >= 0.8: 51 (85%), identical 41. The whole-name 0.8 bar is too kind where names share 'ระดับหลัง' (ระดับหลังคาน vs
ระดับหลังเสาบน = 0.82, core 0.71) and no 0.8 bar separates 'ชั้น 1' from 'ชั้น 2' - read 'identical' and the floor count.
Where the right name sat: in the number's own box 31 ('+3.75ระดับหลังคาน' - the detector joins them), same line left 11 /
right 3, just above 3 (room names over floor levels on plans).
The 11 wrong, read from the OCR text (only the bathroom page looked at by eye): 5 the GT id is not the printed text (GT
'พื้นห้องน้ำส่วนเปียก', the plan prints 'ห้องน้ำ'), 5 OCR misspelt the right label ('อะเส' -> 'อะเล'), 1 two levels at one
height (the number found is the bathroom's, not 'ชานระเบียง''s). None of the 11 took text from the wrong place.
Precision side: 100 bound (number, name) pairs at the height of a named GT level, 70 agree (core 74). Of the other 30: 9
room names on plans at a height GT names by floor, 9 printed names GT spells longer, 8 OCR misspellings, 3 notes bound by
mistake ('หลังคา ค.ส.ล' over +3.75, 'ดูแบบขยายหลังคา 3' left of +3.85), 1 unclear ('ถนนสาธารณะ' over ±0.00).
Floor (`floor_of`: ชั้น N / ชั้นล่าง / ชั้นบน / หลังคา -> FN / F1 / F2 / RF): 14 GT ids imply a floor, the bound names give
the same floor for 11, another 0, none 3 (OCR-garbled). Name against name only: no GT house has a level master
(`*หน้า00_level.json` of level_link.py exists for raw house 174 only), so the floor's height is not checked; ชั้นบน -> F2
assumes 2 storeys; most names (ระดับหลังคาน, ระดับหลังอะเส, ระดับดินเดิม) carry no floor word.
Limits: binder rules were adjusted while looking at these 43 pages (x-overlap for 'above', a lone 'ระดับ' is no name, slugs
skipped, the core metric) - as first written it scored 47 / core 48 here, so fitting moved 1-3 levels; no held-out pages.
Matching is by value, so two levels at one height can swap. ~56 s/page for both readers on CPU (43 pages ~40 min with other
jobs on the CPU). The cache keeps only what bind_names can reach and no people's names (title block): wider limits need
a fresh OCR run.
"""
import glob
import json
import os
import re
import sys

import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import titleblock_extract as T  # noqa: E402  (readers, name_key/name_sim, MAX_PAGE_PX; paddle loads only on first OCR)

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


def _page_img(page):
    """whole page as RGB numpy, long side <= titleblock_extract.MAX_PAGE_PX (PaddleOCR crashes above ~4000 px here)"""
    import numpy as np
    W, H = page.rect.width, page.rect.height
    pix = page.get_pixmap(dpi=int(T.MAX_PAGE_PX / (max(W, H) / 72)))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return np.ascontiguousarray(img[:, :, :3] if pix.n >= 3 else np.repeat(img, 3, axis=2))


def _ocr(img, reader):
    """-> [(text, [x0, y0, x1, y1])] in image pixels. Both readers share the detector (PP-OCRv5_mobile_det), so the same
    image gives the same boxes from both (checked on 1ชั้น_01 p8: 100/100 identical) - a box joins the two readings."""
    return [(t, [int(v) for v in b]) for r in reader.predict(img) for t, b in zip(r.get("rec_texts", []), r.get("rec_boxes", []))]


def level_numbers(lines):
    """OCR lines -> [(value_m, text, box)] for every signed level label in them"""
    out = []
    for txt, box in lines:
        for sign, whole, frac in OCR_LEVEL.findall(txt):
            v = float(f"{whole}.{frac}")
            out.append((-v if sign in ("-", "−") else v, txt, box))
    return out


def ocr_levels(page):
    """scan/outlined page -> signed level labels read by OCR: [(value_m, text)]. Same CPU reader as titleblock_extract
    (Latin/code model - reads digits well, Thai as garbage, which is fine here). Full page <= 3300 px on the long side."""
    return [(v, t) for v, t, _ in level_numbers(_ocr(_page_img(page), T._reader()))]


def gt_level_pages(stride=1):
    """(house, doc, page_no, GT z_levels read from that page, numeric level_m of the whole house) for every distinct page
    a GT level was read from, every `stride`-th one in house order (shared by --ocr-eval and --name-eval: same sample)"""
    seen = 0
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
                by_page.setdefault(int(m.group(1)), []).append(e)
        for pn, es in sorted(by_page.items()):
            seen += 1
            if seen % stride == 0:
                yield house, doc, pn, es, house_levels


def evaluate_ocr(stride=1, cache=None):
    """OCR the distinct pages a GT level was read from, every `stride`-th one in house order (CPU ~35 s/page, so the full
    129 pages is over an hour; a stride keeps the sample spread over all houses instead of the first few).
    recall = GT level of that page seen among the OCR labels; labels_in_gt = share of OCR labels equal to ANY GT level of
    the house (precision proxy: GT may miss real levels, so the true precision is >= this). `cache` = json file, resumable."""
    cp = cache
    cache = json.load(open(cp, encoding="utf-8")) if cp and os.path.exists(cp) else {}
    t = dict(pages=0, levels=0, nonzero=0, hit=0, hit_nonzero=0, labels=0, labels_in_gt=0, pages_zero_labels=0)
    done = 0
    for house, doc, pn, es, house_levels in gt_level_pages(stride):
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
        for g in (e["level_m"] for e in es):
            t["levels"] += 1
            t["nonzero"] += abs(g) > TOL
            h = any(abs(v - g) < TOL for v in vals)
            t["hit"] += h
            t["hit_nonzero"] += h and abs(g) > TOL
    return t, cache


# ---------- binding a level number to the level NAME printed next to it ----------
# Layouts in the 43-page sample (right names, of 48): number + name in ONE detector box "▽+3.75 ระดับหลังคาน" (31), the
# name on the same line, mostly left "ระดับดินเดิม  ±0.00" (14), a room name just above a floor level on plans (3).
_THC = re.compile(r"[ก-ฮ]")            # Thai consonant
SAME_LINE_GAP = 15                     # max horizontal gap to a same-line name, in heights of the number's box (set before
ABOVE_GAP = 1.5                        # measuring; correct names in the sample sat <= 4.6 and <= 0.7) / just above, same unit
PERSON = re.compile(r"^\W*(นาย|นาง|น\.ส\.)")   # a person's name (title block) is never kept, even when next to a level


def level_name(txt):
    """Thai OCR text of one box -> the name in it, number/sign/leader junk cut off ('+3.75ระดับหลังคาน' -> 'ระดับหลังคาน');
    None when fewer than 2 Thai consonants are left or all that is left is the word 'ระดับ' itself (also as OCR misreads
    it, 'จะดับ'): 'ระดับ +0.25' under a room name names nothing, the room name above does"""
    m = re.search(r"[ก-ฮ].*", OCR_LEVEL.sub(" ", txt))
    name = re.sub(r"[^ก-๙0-9A-Za-z)]+$", "", m.group(0)).strip() if m else ""
    generic = len(T.name_key(name)) <= len(T.name_key("ระดับ")) and T.name_sim(name, ["ระดับ"]) >= 0.75
    return name if len(_THC.findall(name)) >= 2 and not generic else None


def bind_names(nums, th_lines):
    """nums = [(value_m, box)] from the Latin reader; th_lines = [(text, box)] from the Thai reader on the SAME image.
    -> [(value_m, name or None, where)], where = same (name inside the number's own box, always wins) | right | left
    (same text line, gap <= SAME_LINE_GAP) | above (stacked over the number and overlapping it by half a width, gap <=
    ABOVE_GAP); among those the smallest gap in box heights wins. A Thai box that holds another level number belongs
    to that label and is never borrowed, and a name of the row above that starts right of the number does not overlap
    it in x, so stacked labels ('+0.60 ระดับพื้นชั้น 1' over '±0.00 ...') keep their own names."""
    owned = [b for _, b in nums]
    out = []
    for v, nb in nums:
        best = None   # (gap in box heights, name, where)
        for txt, b in th_lines:
            name = level_name(txt)
            r = _reach(nb, b) if name else None
            if not r or r[1] != "same" and (b in owned or OCR_LEVEL.search(txt)):
                continue
            if r[1] == "same":
                best = (r[0], name, "same")
                break
            if best is None or (r[0], name, r[1]) < best:
                best = (r[0], name, r[1])
        out.append((v, best[1], best[2]) if best else (v, None, None))
    return out


def _reach(nb, b):
    """can the Thai box b name the number in box nb? -> (gap in nb's heights, same|right|left|above) or None"""
    if b == nb:
        return -1, "same"
    x0, y0, x1, y1 = nb
    bx0, by0, bx1, by1 = b
    h = max(y1 - y0, 1)
    if min(y1, by1) - max(y0, by0) >= 0.5 * min(h, by1 - by0):
        gap = max(bx0 - x1, x0 - bx1, 0) / h
        return (gap, "right" if bx0 >= x0 else "left") if gap <= SAME_LINE_GAP else None
    if by0 < y0 and by1 <= y0 + h / 2 and min(x1, bx1) - max(x0, bx0) >= 0.5 * min(x1 - x0, bx1 - bx0):
        gap = max(y0 - by1, 0) / h
        return (gap, "above") if gap <= ABOVE_GAP else None
    return None


def floor_of(name):
    """level name -> floor code it implies: ชั้น N / ชั้นที่ N -> FN, ชั้นล่าง -> F1, ชั้นบน -> F2 (2-storey houses only),
    หลังคา -> RF ('หลังคาน' = top of beam is NOT a roof), else None. Works on name_key, so OCR vowel/tone slips and the
    ช/ซ confusion of the Thai reader ('ซั้น') do not matter."""
    k = T.name_key(name or "")
    m = re.search(r"[ชซ]น(?:ท)?(\d+)", k)
    if m:
        return "F" + m.group(1)
    if re.search(r"[ชซ]นลาง", k):
        return "F1"
    if re.search(r"[ชซ]นบน", k):
        return "F2"
    return "RF" if re.search(r"หลงคา(?!น)", k) else None


def gt_skip(e):
    """why a GT z_level id is not a printed Thai name ('none' | 'number' '+0.20' '@3.30' | 'slug' 'roof_ridge',
    'ห้องนอน_main_floor' | 'generic' = the bare word 'ระดับ', which names nothing) or None when it is one"""
    s = e.get("id")
    if not isinstance(s, str):
        return "none"
    if len(_THC.findall(s)) < 2:
        return "slug" if re.search(r"[A-Za-z]", s) else "number"
    if re.search(r"[A-Za-z]{3,}_|_[A-Za-z]{3,}", s):
        return "slug"
    return "generic" if T.name_key(s) == T.name_key("ระดับ") else None


def gt_name(e):
    return None if gt_skip(e) else e["id"]


def name_sim(got, gt):
    """the task's metric: titleblock_extract.name_sim (name_key: spaces, punctuation, upper/lower vowels, tone marks dropped)"""
    return T.name_sim(got, [gt])


def core(s):
    """what tells levels apart, as a name_key: the shared word 'ระดับ' ("level", also as OCR reads it: 'ระตับ' 'ระคับ'
    'ระศับ') in front, an annotator note '(...)' at the end and '_' dropped. 'ระดับ ดินถม' and the printed 'ดินถม' are one
    name; 'ระดับหลังคาน' / 'ระดับหลังเสาบน' stop looking alike."""
    return re.sub(r"^ระ[ดตคศ]บ", "", T.name_key(re.sub(r"\s*\(.*$|_", "", s or "")))


def core_sim(got, gt):
    return T.name_sim(core(got), [core(gt)])


def ocr_page_lines(page):
    """both readers on one page -> cache record: Latin lines holding a level number + the Thai lines bind_names could use
    for one (_reach), minus people's names. Kept that narrow on purpose: the title block holds engineer names and
    licence numbers, which must not end up in a file (rebinding with wider limits needs a fresh OCR run)."""
    img = _page_img(page)
    lat = [[t, b] for t, b in _ocr(img, T._reader()) if OCR_LEVEL.search(t)]
    th = _ocr(img, T._reader_th()) if lat else []
    return {"lat": lat, "th": [[t, b] for t, b in th if _THC.search(t) and not PERSON.search(t)
                               and any(_reach(nb, b) for _, nb in lat)]}


def evaluate_names(stride=1, cache=None, show=False):
    """--name-eval: same page sample as --ocr-eval. Per GT level with a printed Thai name (gt_skip) whose number the Latin
    reader found on that page; the number may occur several times on the page, the best-named occurrence counts:
      good  = name_sim >= 0.8 to the GT id (the task's bar) · wrong = named, < 0.8 · no_name = no occurrence got a name
      core  = core_sim >= 0.8 / core key identical (stricter where names share 'ระดับ', fairer where GT added it)
      floor = GT ids that imply a floor (floor_of) vs the floors implied by the bound names
      pairs = every (number, name) the binder made at the height of a named GT level of the page; name agrees >= 0.8 in
              how many (lower bound of precision: GT can hold two names at one height, or miss a printed one)."""
    from collections import Counter
    cp = cache
    cache = json.load(open(cp, encoding="utf-8")) if cp and os.path.exists(cp) else {}
    t, where = Counter(), Counter()
    for house, doc, pn, es, _ in gt_level_pages(stride):
        key = f"{house}|{pn}"
        if key not in cache:
            cache[key] = ocr_page_lines(doc[pn - 1])
            if cp:
                json.dump(cache, open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        rec = cache[key]
        bound = bind_names([(v, b) for v, _, b in level_numbers(rec["lat"])], [tuple(x) for x in rec["th"]])
        t["pages"] += 1
        named = [(e["level_m"], gt_name(e)) for e in es if gt_name(e)]
        for v, name, w in bound:
            if name and any(abs(v - g) < TOL for g, _ in named):
                ok = any(abs(v - g) < TOL and name_sim(name, n) >= 0.8 for g, n in named)
                t["pairs"] += 1
                t["pairs_ok"] += ok
                t["pairs_core_ok"] += any(abs(v - g) < TOL and core_sim(name, n) >= 0.8 for g, n in named)
                if show and not ok:
                    print(f"  pair-off       {key} {v:+.2f} bound {name!r} ({w}) GT {[n for g, n in named if abs(v - g) < TOL]}")
        for e in es:
            t["levels"] += 1
            n = gt_name(e)
            if not n:
                t["skip_" + gt_skip(e)] += 1
                continue
            t["named"] += 1
            occ = [(name, w) for v, name, w in bound if abs(v - e["level_m"]) < TOL]
            got = [(name_sim(name, n), name, w) for name, w in occ if name]
            k = "number_missing" if not occ else "no_name" if not got else "good" if max(got)[0] >= 0.8 else "wrong"
            t[k] += 1
            if show:
                print(f"  {k:14s} {key} {e['level_m']:+.2f} GT {n!r} <- {sorted(set((x, w) for _, x, w in got))}")
            if not got:
                continue
            where[f"{k}:{max(got)[2]}"] += 1
            cs = max(core_sim(x, n) for _, x, _ in got)
            t["core_good"] += cs >= 0.8
            t["core_exact"] += cs == 1.0
            f = floor_of(n)
            if f:
                t["floor_gt"] += 1
                fl = {floor_of(x) for _, x, _ in got} - {None}
                t["floor_ok" if f in fl else "floor_wrong" if fl else "floor_none"] += 1
    t["number_found"] = t["good"] + t["wrong"] + t["no_name"]
    return t, where, cache


def demo():
    """self-check, no PDF needed: the two level-label parsers and the name binding on the shapes seen in real drawings"""
    def txt(s):
        m = LEVEL_RE.match(s)
        return None if not m else (-1 if m.group(1) in "-−–" and m.group(1) else 1) * float(f"{m.group(2)}.{m.group(3)}")
    assert txt("+3.75") == 3.75 and txt("-1.50") == -1.5 and txt("±0.00") == 0.0 and txt("0.15") == 0.15
    assert txt("3.7") is None and txt("Ø4\"SW") is None and txt("1:100") is None and txt("0.20ม.") is None
    got = [(("-" if s == "-" else "+") + w + "." + f) for s, w, f in OCR_LEVEL.findall("FL +3.75 ระดับ -0.50 ที่ ±0.00 และ 3.00 +12,30")]
    assert got == ["+3.75", "-0.50", "+0.00", "+12.30"], got   # "3.00" has no sign -> not a level; "," read as "."
    # name binding (pure, no OCR): number+name in one box / name on the same line / room name just above /
    # a stacked label above is someone else's / Thai text far away on the same line is not a name
    assert level_name("+3.75ระดับหลังคาน") == "ระดับหลังคาน" and level_name("±0.00_ระดับอ้างอิง") == "ระดับอ้างอิง"
    assert level_name("ระดับพื้นชั้น 2 +3.20") == "ระดับพื้นชั้น 2" and level_name("+0.60") is None and level_name("SLE") is None
    assert level_name("ระดับ +0.25") is None and level_name("จะดับ +0.25") is None and level_name("ระเบียง") == "ระเบียง"
    assert level_name("ระดับดิน ±0.00") == "ระดับดิน" and level_name("ระดับพื้น +0.60") == "ระดับพื้น"   # short real names
    nums = [(3.75, [100, 100, 300, 120]), (0.6, [100, 200, 160, 220]), (0.15, [100, 300, 160, 320]),
            (0.0, [100, 400, 160, 420]), (2.5, [900, 600, 960, 620]),
            (0.6, [100, 478, 160, 498]), (0.0, [100, 500, 160, 520]), (0.0, [600, 700, 680, 733])]
    th = [("+3.75ระดับหลังคาน", [100, 100, 300, 120]), ("ระดับพื้นชั้น 1", [200, 202, 330, 220]), ("ห้องน้ำ", [95, 275, 170, 296]),
          ("±0.00", [100, 400, 160, 420]), ("+0.60 ระดับพื้นชั้น 1", [100, 378, 300, 398]), ("หมายเหตุ", [100, 600, 200, 620]),
          ("ระดับพื้นชั้น 1", [170, 478, 300, 498]), ("ระดับอ้างอิง", [175, 502, 300, 520]),   # stacked rows, split boxes
          ("ดินถม", [597, 659, 682, 702]), ("ซักล้าง", [200, 700, 300, 733])]             # name on top beats a far one
    got = bind_names(nums, th)
    assert got == [(3.75, "ระดับหลังคาน", "same"), (0.6, "ระดับพื้นชั้น 1", "right"), (0.15, "ห้องน้ำ", "above"),
                   (0.0, None, None), (2.5, None, None), (0.6, "ระดับพื้นชั้น 1", "right"), (0.0, "ระดับอ้างอิง", "right"),
                   (0.0, "ดินถม", "above")], got
    assert [floor_of(s) for s in ("ระดับพื้นชั้น 1", "ระดับพื้นซั้น 2", "ระดับพื้นชั้นล่าง", "ระดับพื้นชั้นบน", "ระดับหลังคาน",
                                  "ระดับหลังคานหลังคา", "ระดับคานหลังคา", "ระดับอ้างอิง")] == ["F1", "F2", "F1", "F2", None, "RF", "RF", None]
    assert gt_name({"id": "ระดับหลังคาน"}) and gt_name({"id": "ห้องน้ำ WC.1"}) and not gt_name({"id": "+0.20"})
    assert not gt_name({"id": None}) and not gt_name({"id": "roof_ridge"}) and not gt_name({"id": "ห้องนอน_main_floor"})
    assert not gt_name({"id": "ระดับ"})                                    # the bare word "level" names nothing
    assert name_sim("ระดับพื้นซั้น 1", "ระดับพื้นชั้น 1") >= 0.8 and core_sim("ดินถม", "ระดับ ดินถม") == 1.0
    assert name_sim("ระดับหลังคาน", "ระดับหลังเสาบน") >= 0.8 > core_sim("ระดับหลังคาน", "ระดับหลังเสาบน")  # shared 'ระดับหลัง'
    assert core_sim("ระดับพื้นชั้น 1", "ระดับพื้นชั้น 2") >= 0.8   # no 0.8 bar tells floors apart -> 'identical' + floor counts
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
    elif sys.argv[1:2] == ["--name-eval"]:
        sys.stdout.reconfigure(encoding="utf-8")
        args = [a for a in sys.argv[2:] if a != "--show"]
        cp = args[1] if len(args) > 1 else os.environ.get("LEVEL_NAME_CACHE", "level_name_cache.json")
        t, where, c = evaluate_names(int(args[0]) if args else 1, cp, "--show" in sys.argv)
        json.dump(c, open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        f = t["number_found"]
        print(f"pages: {t['pages']} · GT levels on them: {t['levels']} · skipped: id None {t['skip_none']}, bare number "
              f"{t['skip_number']}, English/annotator slug {t['skip_slug']}, bare 'ระดับ' {t['skip_generic']} · printed Thai "
              f"name: {t['named']}")
        print(f"number found by OCR: {f}/{t['named']} · of those: name >= 0.8 {t['good']} ({t['good'] / max(f, 1):.0%}) · "
              f"wrong name {t['wrong']} · no name {t['no_name']}")
        print(f"core name ('ระดับ' and '(...)' dropped): >= 0.8 {t['core_good']} ({t['core_good'] / max(f, 1):.0%}) · "
              f"identical {t['core_exact']}")
        print(f"where the best name sat: {dict(sorted(where.items()))}")
        print(f"floor implied by the GT id: {t['floor_gt']} · bound names give the same floor {t['floor_ok']}, only another "
              f"{t['floor_wrong']}, none {t['floor_none']}")
        print(f"bound pairs at a named GT height: {t['pairs']} · name agrees >= 0.8: {t['pairs_ok']} "
              f"({t['pairs_ok'] / max(t['pairs'], 1):.0%}), core {t['pairs_core_ok']} "
              f"({t['pairs_core_ok'] / max(t['pairs'], 1):.0%}) - lower bounds of precision")
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
