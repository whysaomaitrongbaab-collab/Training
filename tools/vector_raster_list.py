#!/usr/bin/env python3
"""vector_raster_list.py - which house books are vector (CAD export) and which are scans (meeting 2026-11-25:
"เอาแค่เวกเตอร์ไปเลย แยกไปเลยว่าเล่มไหนเวกเตอร์ เล่มไหนรูป ไม่งั้นจะเสียเวลา").

    python tools/vector_raster_list.py                 # every image/<house>/<house>.pdf -> CSV (default path below)
    python tools/vector_raster_list.py --out f.csv
    python tools/vector_raster_list.py --demo          # self-check of the per-book rule (no PDF needed)

Per page: run_part1_part3.kind_of (the rule the pipeline already uses: >= 200 vector lines = vector, or mixed when the
page also holds an image; no lines but an image = raster). Lines are counted with get_cdrawings (same items, faster).
Per book: share of drawing pages (vector + mixed + raster) that are raster:
    <= 10% -> vector · >= 90% -> raster · else mixed (list the raster pages in the CSV so they can be skipped)
A mixed page (vector lines plus an image) counts as vector: its lines are there to read.
Writes one CSV row per book; reads only the PDFs, touches nothing else.
"""
import argparse
import csv
import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_part1_part3 import kind_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(ROOT, "image")
GT = os.path.join(ROOT, "json_แก้ไขแล้ว")
RAW = os.path.join(ROOT, "rawjson_ยังไม่ได้แก้ไขโดนคน")
DEFAULT_OUT = os.path.join(ROOT, "docs", "pipeline_5_ส่วน", "เล่มแบบ_เวกเตอร์_สแกน.csv")
VECTOR_MAX_RASTER = 0.10
RASTER_MIN_RASTER = 0.90


def book_kind(kinds):
    """page kinds -> (book kind, raster share of drawing pages or None when the book has no drawing page)"""
    drawn = [k for k in kinds if k in ("vector", "mixed", "raster")]
    if not drawn:
        return "empty", None
    share = sum(k == "raster" for k in drawn) / len(drawn)
    if share <= VECTOR_MAX_RASTER:
        return "vector", share
    if share >= RASTER_MIN_RASTER:
        return "raster", share
    return "mixed", share


def page_kind(page):
    n_lines = sum(it[0] == "l" for d in page.get_cdrawings() for it in d.get("items", ()))
    return kind_of(n_lines, len(page.get_images()), len(page.get_text("words")))


def compress(pages):
    """[3, 4, 5, 9] -> '3-5,9'"""
    out, start, prev = [], None, None
    for p in pages + [None]:
        if start is None:
            start = prev = p
        elif p is not None and p == prev + 1:
            prev = p
        else:
            out.append(f"{start}" if start == prev else f"{start}-{prev}")
            start = prev = p
    return ",".join(out)


def labelled(house):
    gt = sorted(os.path.basename(d) for d in glob.glob(os.path.join(GT, "*" + house)) if os.path.isdir(d))
    raw = sorted(os.path.basename(d) for d in glob.glob(os.path.join(RAW, "*" + house)) if os.path.isdir(d))
    return gt[0] if gt else "", raw[0] if raw else ""


def run(out):
    import fitz
    rows = []
    books = sorted(glob.glob(os.path.join(IMAGE, "*", "*.pdf")))
    t0 = time.time()
    for i, pdf in enumerate(books, 1):
        house = os.path.splitext(os.path.basename(pdf))[0]
        try:
            doc = fitz.open(pdf)
            kinds = [page_kind(p) for p in doc]
        except Exception as e:  # a broken PDF is listed, not skipped
            rows.append(dict(house=house, book_kind="error", note=str(e)[:120]))
            continue
        kind, share = book_kind(kinds)
        gt, raw = labelled(house)
        rows.append(dict(house=house, book_kind=kind, pages=len(kinds),
                         vector=kinds.count("vector"), mixed=kinds.count("mixed"), raster=kinds.count("raster"),
                         empty=kinds.count("empty"),
                         raster_share="" if share is None else f"{share:.2f}",
                         raster_pages=compress([n + 1 for n, k in enumerate(kinds) if k == "raster"]),
                         gt_folder=gt, raw_folder=raw, note=""))
        print(f"[{i}/{len(books)}] {house}: {kind} ({time.time() - t0:.0f} s)", flush=True)
    cols = ["house", "book_kind", "pages", "vector", "mixed", "raster", "empty", "raster_share", "raster_pages",
            "gt_folder", "raw_folder", "note"]
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\r\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    tally = {}
    for r in rows:
        tally[r["book_kind"]] = tally.get(r["book_kind"], 0) + 1
    print("books:", len(rows), tally, "->", out)


def demo():
    assert book_kind([]) == ("empty", None)
    assert book_kind(["empty", "empty"]) == ("empty", None)
    assert book_kind(["vector"] * 9 + ["raster"])[0] == "vector"          # 10% raster = still a vector book
    assert book_kind(["vector"] * 8 + ["raster"] * 2)[0] == "mixed"
    assert book_kind(["raster"] * 9 + ["mixed"])[0] == "raster"           # mixed page counts on the vector side
    assert book_kind(["raster"] * 8 + ["vector"] * 2)[0] == "mixed"
    assert book_kind(["empty", "raster"])[0] == "raster"                   # empty pages are not drawing pages
    assert compress([]) == "" and compress([3]) == "3" and compress([3, 4, 5, 9, 11, 12]) == "3-5,9,11-12"
    assert kind_of(250, 0, 0) == "vector" and kind_of(0, 1, 0) == "raster" and kind_of(250, 1, 0) == "mixed"
    print("demo ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    demo() if a.demo else run(a.out)
