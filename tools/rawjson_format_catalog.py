#!/usr/bin/env python3
"""rawjson_format_catalog.py — รูปแบบ JSON ของแต่ละประเภทหน้า (pattern) ในระบบ primary rawjson เป็น PDF สั้นๆ

    python tools/rawjson_format_catalog.py --date 2026-11-16
    → docs/primary_rawjson_formats/รูปแบบJSON_primary_rawjson_<date>.pdf

อ่านอย่างเดียว. บ้านละหนึ่งฉบับ (บ้านที่อยู่ใน json_แก้ไขแล้ว/ ใช้ฉบับคนแก้แล้ว ที่เหลือใช้ rawjson_ยังไม่ได้แก้ไขโดนคน/).
ต่อประเภทหน้าหนึ่งหน้า: โครง JSON ที่สร้างจากไฟล์จริง เอาเฉพาะฟิลด์ที่มีใน ≥30% ของ object แม่
ค่าในโครง = ค่าที่พบบ่อยสุด (string) หรือค่าตัวอย่าง · "// 59%" = ฟิลด์นี้มีแค่ 59% (ไม่มีคอมเมนต์ = มี ≥90%)
"""
import argparse
import collections
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TR = HERE.parent
sys.path.insert(0, str(HERE))
from md_to_book_pdf import md_to_pdf  # noqa: E402  (เครื่องมือเดิมของ repo — Edge headless, ภาษาไทยไม่ลอย)

EDITED = TR / "json_แก้ไขแล้ว"
UNEDITED = TR / "rawjson_ยังไม่ได้แก้ไขโดนคน"
OUT_DIR = TR / "docs" / "primary_rawjson_formats"
KEEP = 0.30                         # ฟิลด์ที่มีใน ≥30% ของ object แม่ถึงจะอยู่ในโครง
SEP = "\x1f"                        # ตัวคั่น path ภายใน — key จริงมีจุดได้ (เช่น "F1.30x1.30") จึงใช้ "." ไม่ได้
FIELD_RE = re.compile(r"^[a-z_][A-Za-z0-9_]*$")
WILD = "‹ชื่อเป็นข้อมูล›"            # key ที่เป็นค่าข้อมูล (B1, "1", ข้อความไทย) ไม่ใช่ชื่อฟิลด์ — รวบเป็นตัวเดียว

# ลำดับและชื่อไทยตามสเปก §1 (19 pattern)
PATTERNS = [
    ("beam_plan", "แปลนคาน"), ("footing_plan", "แปลนฐานราก"), ("roof_frame_plan", "แปลนโครงหลังคา"),
    ("etc_plan", "แปลนอื่นๆ (เสา พื้น สถาปัตย์ งานระบบ)"), ("section", "แบบขยาย / รูปตัด (ขนาดและเหล็กเสริม)"),
    ("schedule", "ตาราง (เสา คาน ประตู หน้าต่าง ฯลฯ)"), ("notes", "ข้อกำหนดทั่วไป"), ("index", "สารบัญแบบ"),
    ("material_list", "ใบ BOQ"), ("site_plan", "ผังบริเวณ"), ("side_profile", "รูปด้าน / รูปตัดอาคาร"),
    ("grid_master", "กริดหลักของบ้าน (ไฟล์หน้า00)"), ("title", "หน้าปก"), ("symbol", "หน้าสัญลักษณ์"),
    ("roof_plan", "แปลนหลังคา (สถาปัตย์)"), ("misc", "เบ็ดเตล็ด"), ("bbs_schedule", "ตารางตัดเหล็ก"),
    ("soil_boring_log", "ผลเจาะสำรวจดิน"), ("unknown", "ไม่เข้าพวกไหน"),
]
CSS = """<style>
pre { white-space: pre-wrap; word-break: break-all; page-break-inside: auto; }
pre code { font-size: 8pt; line-height: 1.35; }
table { font-size: 9pt; } th, td { padding: 3px 8px; }
</style>"""


class Stat:
    __slots__ = ("present", "objs", "types", "values", "names")

    def __init__(self):
        self.present = self.objs = 0
        self.types = collections.Counter()
        self.values = collections.Counter()
        self.names = collections.Counter()


def typ(v):
    return {dict: "obj", list: "arr", str: "str", bool: "bool", type(None): "null"}.get(type(v), "num")


def walk(node, path, st):
    if isinstance(node, dict):
        st[path].objs += 1
        wild_seen = False
        for k, v in node.items():
            name = k if FIELD_RE.match(k) else WILD
            p = f"{path}{SEP}{name}" if path else name
            if name == WILD:
                st[p].names[k] += 1
            observe(v, p, st, count=not (name == WILD and wild_seen))
            wild_seen |= name == WILD
    elif isinstance(node, list):
        for it in node:
            observe(it, path + "[]", st, count=False)


def observe(v, p, st, count=True):
    s = st[p]
    s.present += count
    s.types[typ(v)] += 1
    if isinstance(v, (str, int, float, bool)) and (v in s.values or len(s.values) < 400):
        s.values[v] += 1                        # ค่าในโครง = ค่าที่พบบ่อยสุด (ตัวเลขด้วย ไม่งั้นได้ DB คู่กับ 9)
    if isinstance(v, (dict, list)):
        walk(v, p, st)


def scalar(s, t):
    if t == "null":
        return "null"
    v = next((x for x, _ in s.values.most_common() if typ(x) == t), "")
    if isinstance(v, str) and len(v) > 40:
        v = v[:40] + "…"
    return json.dumps(v, ensure_ascii=False)


def value_lines(st, km, p, ind):
    """บรรทัดของค่าที่ path p — บรรทัดแรกต่อท้าย key"""
    s = st[p]
    t = s.types.most_common(1)[0][0]
    if t == "obj":
        body = obj_lines(st, km, p, ind + 1)
        return ["{"] + body + [" " * ind + "}"] if body else ["{}"]
    if t == "arr":
        if p + "[]" not in st:
            return ["[]"]
        inner = value_lines(st, km, p + "[]", ind)
        return [f"[{inner[0]}"] + inner[1:-1] + [inner[-1] + "]"] if len(inner) > 1 else [f"[{inner[0]}]"]
    return [scalar(s, t)]


def obj_lines(st, km, path, ind):
    objs = st[path].objs
    kids = [p for p in sorted(km.get(path, []), key=lambda p: -st[p].present) if st[p].present / objs >= KEEP]
    out = []
    for i, p in enumerate(kids):
        name = p.rsplit(SEP, 1)[-1]
        pct = st[p].present * 100 // objs
        note = [f"{pct}%"] if pct < 90 else []
        if name == WILD:
            note.append("ชื่อจริง เช่น " + ", ".join(n for n, _ in st[p].names.most_common(4)))
        val = value_lines(st, km, p, ind)
        comma = "," if i < len(kids) - 1 else ""
        first = " " * ind + json.dumps(name, ensure_ascii=False) + ": " + val[0]
        rest = val[1:]
        if rest:
            rest[-1] += comma
        else:
            first += comma
        out.append(first + (f"   // {' · '.join(note)}" if note else ""))
        out += rest
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="วันที่บนหน้าแรกและชื่อไฟล์ เช่น 2026-11-16")
    a = ap.parse_args()

    edited = {p.name: p for p in EDITED.iterdir() if p.is_dir() and not p.name.startswith("00")}
    unedited = {p.name: p for p in UNEDITED.iterdir() if p.is_dir() and not p.name.startswith("00")}
    stats = collections.defaultdict(lambda: collections.defaultdict(Stat))
    files, houses = collections.Counter(), collections.defaultdict(set)
    for name in sorted(set(edited) | set(unedited)):
        for f in (edited.get(name) or unedited[name]).glob("*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            g = d.get("pattern") if isinstance(d, dict) else None
            if not g:                                   # _scope.json / manifest.json — ไม่ใช่หน้าแบบ
                continue
            files[g] += 1
            houses[g].add(name)
            walk(d, "", stats[g])

    L = [CSS, "", "# รูปแบบ JSON แต่ละประเภทหน้า — primary rawjson",
         f"สร้าง {a.date} จากไฟล์จริง {sum(files.values()):,} ไฟล์ · {len(set().union(*houses.values()))} บ้าน "
         f"({len(set().union(*houses.values()) & set(edited))} บ้านใช้ฉบับคนแก้แล้ว) · โครงแสดงเฉพาะฟิลด์ที่มีใน ≥30% · `// 59%` = มีแค่ 59% "
         "(ไม่มีคอมเมนต์ = มีเกือบทุกไฟล์) · ค่าในโครงคือค่าที่พบบ่อยสุด", "",
         "| # | ประเภทหน้า | pattern | ไฟล์ | บ้าน |", "|---|---|---|---|---|"]
    L += [f"| {i} | {th} | `{p}` | {files[p]:,} | {len(houses[p])} |" for i, (p, th) in enumerate(PATTERNS, 1)]
    extra = sorted(set(files) - {p for p, _ in PATTERNS})
    L += [f"| — | (นอกสเปก) | `{p}` | {files[p]:,} | {len(houses[p])} |" for p in extra]

    for i, (p, th) in enumerate(PATTERNS + [(e, "นอกสเปก") for e in extra], 1):
        if not files[p]:
            continue                                     # มีในสเปกแต่ยังไม่มีไฟล์จริง — อยู่ในตารางหน้าแรกแล้ว
        st = stats[p]
        km = collections.defaultdict(list)
        for q in st:
            if q and not q.endswith("[]"):
                km[q.rsplit(SEP, 1)[0] if SEP in q else ""].append(q)
        body = ["{"] + obj_lines(st, km, "", 1) + ["}"]
        L += ['<div style="page-break-before: always"></div>', "",
              f"## {i}. {th} — `{p}`", f"{files[p]:,} ไฟล์ · {len(houses[p])} บ้าน", "",
              "```json", *body, "```", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        md = Path(td) / "catalog.md"
        md.write_text("\n".join(L) + "\n", encoding="utf-8")
        pdf = md_to_pdf(md, OUT_DIR / f"รูปแบบJSON_primary_rawjson_{a.date}.pdf")
    from pypdf import PdfReader
    print(f"pdf {pdf}  ({len(PdfReader(str(pdf)).pages)} หน้า)")


if __name__ == "__main__":
    main()
