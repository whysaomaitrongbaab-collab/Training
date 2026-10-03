"""ลายนิ้วมือทุกหน้าของ PDF บ้านในเครื่อง (Training/image) — ใช้กันเอาบ้านที่เคยใช้เทรนมาทดสอบ
    python fp_index.py build                 → fp_train.json
    python fp_index.py check a.pdf b.pdf ... → บอกว่าซ้ำกับบ้านไหน (ภาพย่อ dHash + ข้อความในหน้า)
dHash 16x16 ของทั้งหน้า: แบบเดียวกันที่ export คนละครั้ง/คนละความละเอียด ห่างกันไม่กี่บิต · คนละแบบห่าง ~100+"""
import glob
import json
import os
import re
import sys

import fitz

ROOT = r"d:/00mk/steel project/training/Training/image"
INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp_train.json")


def dhash(page, n=16):
    pix = page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15), colorspace=fitz.csGRAY)
    from PIL import Image
    im = Image.frombytes("L", (pix.width, pix.height), pix.samples).resize((n + 1, n))
    px = list(im.getdata())
    bits = 0
    for r in range(n):
        for c in range(n):
            bits = (bits << 1) | (px[r * (n + 1) + c] > px[r * (n + 1) + c + 1])
    return bits


def words(page):
    t = page.get_text()
    return sorted({w for w in re.findall(r"[\u0E00-\u0E7FA-Za-z0-9.\-]{4,}", t)})


def fp(path):
    doc = fitz.open(path)
    return {"pages": len(doc), "hash": [dhash(p) for p in doc],
            "words": sorted({w for p in doc for w in words(p)})}


def main():
    if sys.argv[1] == "build":
        idx = {}
        for f in sorted(glob.glob(os.path.join(ROOT, "*", "*.pdf"))):
            idx[os.path.basename(os.path.dirname(f))] = fp(f)
            print(os.path.basename(f), idx[os.path.basename(os.path.dirname(f))]["pages"], flush=True)
        json.dump(idx, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False)
        return
    idx = json.load(open(INDEX, encoding="utf-8"))
    for f in sys.argv[2:]:
        c = fp(f)
        best = []
        for name, t in idx.items():
            near = sum(1 for h in c["hash"] if any(bin(h ^ x).count("1") <= 20 for x in t["hash"]))
            cw, tw = set(c["words"]), set(t["words"])
            jac = len(cw & tw) / len(cw | tw) if cw and tw else 0
            best.append((near, round(jac, 2), name))
        best.sort(reverse=True)
        print(f"{os.path.basename(f)} ({c['pages']} หน้า, คำ {len(c['words'])}) → ใกล้สุด {best[:3]}")


if __name__ == "__main__":
    main()
