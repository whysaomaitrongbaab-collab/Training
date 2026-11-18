#!/usr/bin/env python3
"""rawjson_format_catalog.py — รูปแบบ JSON ของแต่ละประเภทหน้า (pattern) ในระบบ primary rawjson เป็น PDF สั้นๆ

    python tools/rawjson_format_catalog.py --date 2026-11-16
    → docs/primary_rawjson_formats/รูปแบบJSON_primary_rawjson_<date>.pdf

อ่านอย่างเดียว. บ้านละหนึ่งฉบับ (บ้านที่อยู่ใน json_แก้ไขแล้ว/ ใช้ฉบับคนแก้แล้ว ที่เหลือใช้ rawjson_ยังไม่ได้แก้ไขโดนคน/).
ต่อประเภทหน้าหนึ่งหน้า: โครง JSON ที่สร้างจากไฟล์จริง เอาเฉพาะฟิลด์ที่มีใน ≥30% ของ object แม่
ค่าในโครง = ค่าที่พบบ่อยสุด (string) หรือค่าตัวอย่าง · "// มีใน 59%" = ฟิลด์นี้มีอยู่ใน 59% ของ object (ไม่ใช่ความถี่ของค่า)

2026-11-18: ก่อนนับ ไฟล์ทุกไฟล์ถูกแปลงเป็นรูปแบบตามสเปก §0.0 (to_spec) — ตัดฟิลด์ที่เลิกใช้ (confidence_*, note ...),
แปลงช่วงคานเป็น "span": [start, end, length] และกำกับฟิลด์หัวไฟล์ว่าใครเติม (code / OCR). ไฟล์จริงไม่ถูกแก้.
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
from check_format import SECTION_KINDS  # noqa: E402  (ชนิดย่อยของ section ชุดเดียวกับตัวตรวจ)

# section แยกย่อยตามสเปก §1 #5 (2026-11-18) — pass 0 คัดทีละ view
SECTION_SUBS = [("5.1", "beam", "รูปตัดคาน — pattern `beam_section` (#22)"),
                ("5.2", "footing", "รูปตัดฐานราก — pattern `footing_section` (#23)"),
                ("5.3", "column", "รูปตัดเสา — pattern `column_section` (#24)"),
                ("5.4", "other", "รูปตัดอื่นๆ (พื้น บันได รอยต่อ ฯลฯ) — pattern `section` (#5) เดิม")]


def section_kind_of(element_type):
    return next((k for k, ts in SECTION_KINDS.items() if ts and element_type in ts), "other")

EDITED = TR / "json_แก้ไขแล้ว"
UNEDITED = TR / "rawjson_ยังไม่ได้แก้ไขโดนคน"
OUT_DIR = TR / "docs" / "primary_rawjson_formats"
KEEP = 0.30                         # ฟิลด์ที่มีใน ≥30% ของ object แม่ถึงจะอยู่ในโครง
SEP = "\x1f"                        # ตัวคั่น path ภายใน — key จริงมีจุดได้ (เช่น "F1.30x1.30") จึงใช้ "." ไม่ได้
FIELD_RE = re.compile(r"^[a-z_][A-Za-z0-9_]*$")
WILD = "‹ชื่อเป็นข้อมูล›"            # key ที่เป็นค่าข้อมูล (B1, "1", ข้อความไทย) ไม่ใช่ชื่อฟิลด์ — รวบเป็นตัวเดียว

# ลำดับและชื่อไทยตามสเปก §1 (25 pattern; #20 column_plan และ #25 slab_plan ยังติดด่านเขียนลงไฟล์; #21 level_master; #22-24 รูปตัดแยกชนิด)
PATTERNS = [
    ("beam_plan", "แปลนคาน"), ("footing_plan", "แปลนฐานราก"), ("roof_frame_plan", "แปลนโครงหลังคา"),
    ("etc_plan", "แปลนอื่นๆ (สถาปัตย์ งานระบบ · ไฟล์เก่ายังมีเสา/พื้นปนอยู่)"), ("section", "แบบขยาย / รูปตัด (ขนาดและเหล็กเสริม)"),
    ("schedule", "ตาราง (เสา คาน ประตู หน้าต่าง ฯลฯ)"), ("notes", "ข้อกำหนดทั่วไป"), ("index", "สารบัญแบบ"),
    ("material_list", "ใบ BOQ"), ("site_plan", "ผังบริเวณ"), ("side_profile", "รูปด้าน / รูปตัดอาคาร"),
    ("grid_master", "กริดหลักของบ้าน (ไฟล์หน้า00)"), ("title", "หน้าปก"), ("symbol", "หน้าสัญลักษณ์"),
    ("roof_plan", "แปลนหลังคา (สถาปัตย์)"), ("misc", "เบ็ดเตล็ด"), ("bbs_schedule", "ตารางตัดเหล็ก"),
    ("soil_boring_log", "ผลเจาะสำรวจดิน"), ("unknown", "ไม่เข้าพวกไหน"),
    ("column_plan", "แปลนเสา (เสาจากทุกแปลน — ไฟล์เก่ายังปนอยู่ในแปลนอื่น)"),
    ("level_master", "level master (ชั้น → ระดับ ไฟล์หน้า00_level)"),
    ("beam_section", "รูปตัดคาน (ยังไม่มีไฟล์ — ดู 5.1)"),
    ("footing_section", "รูปตัดฐานราก (ยังไม่มีไฟล์ — ดู 5.2)"),
    ("column_section", "รูปตัดเสา (ยังไม่มีไฟล์ — ดู 5.3)"),
    ("slab_plan", "แปลนพื้น (พื้นจากทุกแปลน — ไฟล์เก่ายังปนอยู่ในแปลนอื่น)"),
]
PLAN_FAMILY = {"beam_plan", "footing_plan", "roof_frame_plan", "etc_plan"}
SLAB_TYPES = {"slab", "precast_plank_detail", "precast_plank_placement_detail"}   # = t07 plan_slab
# ส่วนที่สเปกเพิ่ม 2026-11-18 แต่ไฟล์จริงยังไม่มี — โครงด้านบนสร้างจากไฟล์จริงจึงไม่เห็น ต้องแปะตัวอย่างเอง
EXTRA = {
    "grid_master": [
        "**วิธีสร้างกริด master (สเปก §4 ท้ายหัวข้อ Master file, 2026-11-18):** อ่านทีละหน้า หนึ่งหน้าต่อหนึ่งครั้งที่เรียกโมเดล "
        "บ้านที่มี 25 หน้าให้อ่าน = เรียก 25 ครั้ง · แต่ละครั้งตอบเฉพาะสิ่งที่หน้านั้นเพิ่ม (หน้าที่ไม่เพิ่มอะไรตอบว่าง) "
        "· โค้ดรวมทุกคำตอบเป็น master เดียวที่เดียว แล้วจัดเลขเส้นและจุดกำเนิดใหม่ · ระดับต่อชั้นอยู่ในไฟล์ `level_master` (หน้า 21) เขียนหลังรวมครบทุกหน้า",
        "",
    ],
}
EXTRA["level_master"] = [
    "**ไฟล์ระดับของบ้าน (สเปก §4b, 2026-11-18):** หนึ่งบ้านหนึ่งไฟล์ `<บ้าน>_หน้า00_level.json` เรียงชั้นจากล่างขึ้นบน · "
    "`floor_level` ใช้รหัสเดียวกับหัวไฟล์ · ทุก `level_m` ต้องตรงกับค่าใน `z_levels[]` ของกริด master · "
    "ชั้นที่แบบไม่พิมพ์ระดับไม่ใส่ · ไม่เขียนความสูงชั้น โค้ดคิดจากผลต่าง · ตอนนี้มีไฟล์จริงแค่บ้าน 174 "
    "(หน้านี้จึงสร้างจากไฟล์เดียว) บ้านอื่นยังไม่มี"]
SECTION_NOTES = {
    "footing": [
        "**ฐานรากบนแบบจริงมีอะไรบ้าง (สเปก §6b, 2026-11-18):** B/L → `width_mm`/`depth_mm` · ความหนา → `height_mm` · "
        "ตะแกรงล่างสองทิศ → `main_bar` (`count` = ผลรวม, แยกทิศใน `count_printed_as` เช่น `\"10 + 7\"`) · "
        "**ตะแกรงบน → `top_bar`** (รูปแบบเดียวกับ `main_bar` ใส่เฉพาะเมื่อแบบพิมพ์ไว้) · เหล็กรัดรอบขอบ → `stirrup` · "
        "เหล็กเดือย → `dowel_bar` · ระยะหุ้ม → `cover_mm` (เฉพาะที่แบบพิมพ์) · คอนกรีตหยาบ → `lean_concrete` · "
        "เสาเข็ม → `pile_count`/`pile`",
        "", "**ไม่ดึง:** เส้นทางถ่ายแรง แรงต้านดิน ข้อความอธิบายการออกแบบ (มีในรูปอ้างอิง แต่แบบโครงสร้างไทยไม่พิมพ์)",
        "", "**สะกดแปลกที่เจอในไฟล์เก่า — ห้ามใช้:** `bars_by_direction` (25) `bar_layers` (21) `rebar` (15) `main_bar.top/bottom` (13) "
        "`thickness_mm` ระดับบน (120) `dowel_bar.length_m` (7) `pile_length_m` (22)"],
}
SECTION_INTRO = [
    "**แยกย่อยตามชนิดชิ้นส่วน เป็น pattern ของตัวเอง (สเปก §1 #5 และ #22-24, 2026-11-18):** pass 0 คัดทีละ view เป็น "
    "`beam_section` / `footing_section` / `column_section` · `section` เดิมเก็บรูปตัดชนิดอื่นกับไฟล์เก่า · "
    "หน้าที่ปนหลายชนิดแยกเป็นหลาย view · ตารางตัดเหล็กเป็น `bbs_schedule`",
    "", "ยังไม่มีไฟล์ที่ใช้ pattern ใหม่สามตัว (ไฟล์ section เก่า 1,218 ไฟล์ปนหลายชนิดและไม่ได้ติดป้าย) "
    "โครงด้านล่างจึงสร้างจาก `element_type` ของแต่ละชิ้นในไฟล์เก่า (ไฟล์หนึ่งนับได้ในหลายชนิด)"]
POINT_REFS = '["A2", "A3"]'   # ตัวอย่างแบบรวม — ค่าที่พบบ่อยสุดคือจุดเดียว ไม่สอนการรวม (2026-11-18)
# สเปก §0.0 (2026-11-18): ฟิลด์ที่เลิกใช้ทุกระดับ และฟิลด์หัวไฟล์ที่โค้ด/OCR เติม (โมเดลไม่เขียน)
RETIRED = {"confidence_score", "confidence_flags", "note", "offset_note", "spec_confidence_score",
           "spec_confidence_flags", "dummy_grid_rule_check", "non_grid_dimensions_do_not_confuse", "phase_note"}
WHO = {
    "png": "code", "doc_page": "code", "source_image": "code", "source_pages": "code", "grid_source": "code",
    "pattern": "code: pass 0 ต่อ view", "discipline": "code: pass 0", "views": "code: pass 0",
    "sheet_code": "OCR กรอบชื่อแบบ", "sheet_name": "OCR กรอบชื่อแบบ", "view_title": "OCR ใต้ view",
    "scale": "OCR + regex", "floor_level": "code: กฎจาก view_title, ไม่ตรง = null",
    "confidence_score": "code: null เสมอ", "confidence_flags": "code: [] เสมอ", "warnings": "code: [] เสมอ",
}
SPAN_EXAMPLE = '["A1", "A2", null]'


def to_spec(node, top=True):
    """แปลงไฟล์จริงเป็นรูปแบบตามสเปก §0.0 — ใช้แสดงผลเท่านั้น"""
    if isinstance(node, list):
        return [to_spec(x, False) for x in node]
    if not isinstance(node, dict):
        return node
    out = {k: to_spec(v, False) for k, v in node.items()
           if k not in RETIRED and not (top and k in ("warnings", "views"))}
    if not top and isinstance(out.get("source_image"), str):   # path ชั้นใน (z_levels, chains) ก็ซ่อนชื่อบ้าน
        out["source_image"] = "image/‹บ้าน›/‹บ้าน›_หน้า‹NN›.png"
    if "grid_ref_start" in out and "grid_ref_end" in out:
        src, length = out.pop("span_source", None), out.pop("span_length_m", None)
        third = (length if src == "local_dimension" else f"~{length}" if src == "scaled_from_grid" else None)
        out["span"] = [out.pop("grid_ref_start"), out.pop("grid_ref_end"), third]
    if top:
        out["confidence_score"], out["confidence_flags"], out["warnings"] = None, [], []
        # ค่าตัวอย่างของ path แต่ละช่องมาจากคนละไฟล์ — เคยทำให้อ่านว่าโมเดลใส่ชื่อบ้านปนกัน (2026-11-18) จึงไม่แสดงชื่อจริง
        for k, ph in (("source_image", "image/‹บ้าน›/‹บ้าน›_หน้า‹NN›.png"),
                      ("grid_source", "‹บ้าน›_หน้า00_gridline.json")):
            if k in out:
                out[k] = ph
        if "source_pages" in out:
            out["source_pages"] = ["image/‹บ้าน›/‹บ้าน›_หน้า‹NN›.png"]
    return out


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
        note = [WHO[name]] if path == "" and name in WHO else []
        if path.endswith("elements[]") and name == "element_id":
            note.append("model: ต้องอยู่ในรายการ OCR ของหน้า ไม่งั้น null")
        if name == "span":
            note.append("length เฉพาะปลายที่ไม่อยู่บนเส้นกริด: ตัวเลข=พิมพ์ · \"~N\"=วัดสเกล · null=โค้ดคิดจากกริด")
        point = path.endswith("elements[]") and f"{path}{SEP}grid_refs" in km.get(path, [])
        if point and name == "grid_refs":
            note.append("element_id เดียวกันรวมเป็นแถวเดียวต่อไฟล์ (§4)")
        if point and name == "count":
            note.append("= จำนวน grid_refs")
        if pct < 90:
            note.append(f"มีใน {pct}%")
        if name == WILD:
            note.append("ชื่อจริง เช่น " + ", ".join(n for n, _ in st[p].names.most_common(4)))
        val = ([SPAN_EXAMPLE] if name == "span" else [POINT_REFS] if point and name == "grid_refs"
               else ["2"] if point and name == "count" else value_lines(st, km, p, ind))
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
    col_src = collections.Counter()                       # แปลนเสา: เสามาจากแปลนแบบไหน
    slab_src = collections.Counter()                      # แปลนพื้น: พื้นมาจากแปลนแบบไหน
    for name in sorted(set(edited) | set(unedited)):
        for f in (edited.get(name) or unedited[name]).glob("*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            g = d.get("pattern") if isinstance(d, dict) else None
            if not g:                                   # _scope.json / manifest.json — ไม่ใช่หน้าแบบ
                continue
            files[g] += 1
            houses[g].add(name)
            walk(to_spec(d), "", stats[g])
            cols = [e for e in d.get("elements") or []
                    if isinstance(e, dict) and e.get("element_type") in ("column", "pedestal")]
            if g in PLAN_FAMILY and cols:            # เสาบนแปลนทุกแบบ = view แปลนเสา (สเปก §1 #20)
                files["column_plan"] += 1
                houses["column_plan"].add(name)
                col_src[g] += 1
                walk(to_spec(dict(d, pattern="column_plan", elements=cols)), "", stats["column_plan"])
            slabs = [e for e in d.get("elements") or []
                     if isinstance(e, dict) and e.get("element_type") in SLAB_TYPES]
            if g in PLAN_FAMILY and slabs:           # พื้นบนแปลนทุกแบบ = view แปลนพื้น (สเปก §1 #25)
                files["slab_plan"] += 1
                houses["slab_plan"].add(name)
                slab_src[g] += 1
                walk(to_spec(dict(d, pattern="slab_plan", elements=slabs)), "", stats["slab_plan"])
            if g == "section":
                by_kind = collections.defaultdict(list)
                for e in d.get("elements") or []:
                    if isinstance(e, dict):
                        by_kind[section_kind_of(e.get("element_type"))].append(e)
                for kind, els in by_kind.items():
                    sub = dict(d, elements=els)
                    sub = {"section_kind": kind, **sub}
                    files["section/" + kind] += 1
                    houses["section/" + kind].add(name)
                    walk(to_spec(sub), "", stats["section/" + kind])

    L = [CSS, "", "# รูปแบบ JSON แต่ละประเภทหน้า — primary rawjson",
         f"สร้าง {a.date} จากไฟล์จริง {sum(files.values()):,} ไฟล์ · {len(set().union(*houses.values()))} บ้าน "
         f"({len(set().union(*houses.values()) & set(edited))} บ้านใช้ฉบับคนแก้แล้ว)", "",
         "**แสดงตามสเปกใหม่ §0.0 (2026-11-18)** — ไฟล์เก่ายังเป็นรูปแบบเดิม ตัวสร้างชุดข้อมูลแปลงให้ตอนเทรน",
         "", "- **ตัดออกทุกระดับ:** `confidence_score`, `confidence_flags`, `note`, `offset_note`, "
         "`spec_confidence_*` และฟิลด์อธิบายผังกริดด้วยคำของผู้สกัด",
         "- **ช่วงคาน/คานคอดิน/จันทัน/แป/ผนัง:** เขียนเป็น `\"span\": [จุดเริ่ม, จุดจบ, ความยาว]` "
         "โค้ดแปลงกลับเป็น `grid_ref_start`, `grid_ref_end`, `span_length_m`, `span_source` ตอนบันทึก",
         "- **คอมเมนต์หลัง `//`:** `code` / `OCR` = ใครเติมฟิลด์นั้น (โมเดลไม่ต้องเขียน) · "
         "`มีใน 59%` = ฟิลด์นี้มีอยู่ใน 59% ของ object **ไม่ใช่**ความถี่ของค่าที่แสดง · ค่าที่แสดงคือค่าที่พบบ่อยสุด · "
         "แสดงเฉพาะฟิลด์ที่มีใน ≥30%",
         "- **โครงแต่ละหน้าไม่ใช่ไฟล์จริงไฟล์เดียว:** แต่ละช่องคือค่าที่พบบ่อยที่สุดของช่องนั้น มาจากคนละไฟล์ได้ "
         "(ชื่อบ้านใน path จึงแทนด้วย `‹บ้าน›`)",
         "- **ก๊อปข้อความไทยออกจาก PDF นี้** สระ/วรรณยุกต์อาจซ้ำ (เช่น \"โครงสร้ ร้ าง\") เป็นเรื่องของการก๊อป ไม่ได้อยู่ในไฟล์ JSON",
         "- **เพิ่ม 2026-11-18:** `column_plan` (#20) = เสาจากทุกแปลนแยกเป็น view ของตัวเอง (ดูหน้า 20) · "
         "`section` แยกเป็น 5.1-5.4 (pattern #22-24 + section เดิม) · `level_master` (#21) ไฟล์ระดับของบ้าน (ดูหน้า 21)",
         "",
         "| # | ประเภทหน้า | pattern | ไฟล์ | บ้าน |", "|---|---|---|---|---|"]
    L += [f"| {i} | {th} | `{p}` | {files[p]:,} | {len(houses[p])} |" for i, (p, th) in enumerate(PATTERNS, 1)]
    extra = sorted(set(files) - {p for p, _ in PATTERNS} - {k for k in files if "/" in k})
    L += [f"| — | (นอกสเปก) | `{p}` | {files[p]:,} | {len(houses[p])} |" for p in extra]

    def skeleton(st):
        km = collections.defaultdict(list)
        for q in st:
            if q and not q.endswith("[]"):
                km[q.rsplit(SEP, 1)[0] if SEP in q else ""].append(q)
        return ["```json", "{"] + obj_lines(st, km, "", 1) + ["}", "```"]

    for i, (p, th) in enumerate(PATTERNS + [(e, "นอกสเปก") for e in extra], 1):
        if not files[p]:
            continue                                     # มีในสเปกแต่ยังไม่มีไฟล์จริง — อยู่ในตารางหน้าแรกแล้ว
        L += ['<div style="page-break-before: always"></div>', "",
              f"## {i}. {th} — `{p}`", f"{files[p]:,} ไฟล์ · {len(houses[p])} บ้าน", ""]
        if p == "column_plan":
            L += ["**แยกเสาออกเป็น view ของตัวเอง (สเปก §1 #20, 2026-11-18):** pass 0 ส่งทุกแปลนที่มีมาร์คเสา "
                  "เข้างานเสาอีก view หนึ่ง หน้าเดียวจึงได้ทั้ง `footing_plan` และ `column_plan` · ไฟล์เก่ายังไม่มี "
                  "`column_plan` หน้านี้จึงดึงเฉพาะเสา (`column`, `pedestal`) ออกมาจากแปลนเหล่านี้: "
                  + " · ".join(f"`{g}` {n:,} ไฟล์" for g, n in col_src.most_common()),
                  "", "**ยังติดด่าน:** ห้ามเขียน `column_plan` ลงไฟล์จนกว่า Constistant กับ `check_format.py` "
                  "จะรู้จัก ไม่งั้นเสาหายจาก BOQ ระหว่างนี้เสายังอยู่ในแปลนที่อ่านมา", ""]
        if p == "slab_plan":
            L += ["**แยกพื้นออกเป็น view ของตัวเอง (สเปก §1 #25, 2026-11-18):** ป้ายพื้น SO/SI/SX/ST และแผนผังแผ่นพื้นสำเร็จ "
                  "จากทุกแปลน · ไฟล์เก่ายังไม่มี `slab_plan` หน้านี้จึงดึงเฉพาะพื้นออกมาจากแปลนเหล่านี้: "
                  + " · ".join(f"`{g}` {n:,} ไฟล์" for g, n in slab_src.most_common()),
                  "", "**ยังติดด่าน** แบบเดียวกับ `column_plan`: ห้ามเขียนลงไฟล์จนกว่า Constistant จะรู้จัก", ""]
        if p != "section":
            L += [*skeleton(stats[p]), "", *EXTRA.get(p, []), ""]
            continue
        L += [*SECTION_INTRO, ""]
        for n, (num, kind, kth) in enumerate(SECTION_SUBS):
            k = "section/" + kind
            if not files[k]:
                continue
            L += (['<div style="page-break-before: always"></div>', ""] if n else []) + [
                f"### {num} {kth}",
                f"{files[k]:,} ไฟล์ · {len(houses[k])} บ้าน · element_type: "
                + (", ".join(f"`{t}`" for t in sorted(SECTION_KINDS[kind])) if SECTION_KINDS[kind] else "อื่นทั้งหมด"),
                "", *skeleton(stats[k]), "", *SECTION_NOTES.get(kind, []), ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        md = Path(td) / "catalog.md"
        md.write_text("\n".join(L) + "\n", encoding="utf-8")
        pdf = md_to_pdf(md, OUT_DIR / f"รูปแบบJSON_primary_rawjson_{a.date}.pdf")
    from pypdf import PdfReader
    print(f"pdf {pdf}  ({len(PdfReader(str(pdf)).pages)} หน้า)")


if __name__ == "__main__":
    main()
