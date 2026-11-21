#!/usr/bin/env python3
"""
tools/pass3_grid.py — Pass 3 "Grid Ref Detect" ตามแผนภาพของ King: ต่อกริดต่อหน้า + เลขระดับ เป็นฐานข้อมูลต่อบ้าน

    python tools/pass3_grid.py <บ้าน>                   # รันตัวรันส่วน 1+3 ถ้ายังไม่มี result.json แล้วสร้าง 3 ไฟล์
    python tools/pass3_grid.py <บ้าน> --max-level-pages 6 --no-levels
    python tools/pass3_grid.py --eval 174บ้าน...       # เทียบ grid master กับเฉลย (ดู evaluate)
    python tools/pass3_grid.py --demo                  # self-check ของส่วน pure

แผนภาพ (Grid Ref Detect (HW)) -> ที่ไฟล์นี้ทำ:
  Floor Plan : Set up logic (สเกล + vector/PNG) = gridlab_scale / run_part1_part3.kind_of (มีอยู่แล้ว)
               X/Y grid annotate = gridlab_probe.detect (มีอยู่แล้ว, ผลต่อหน้าใน result.json)
               -> **Grid Master DB** = merge_plans(): รวมแปลนทุกหน้าของบ้านเป็นเส้นชุดเดียว เรียงด้วยชื่อเส้นที่ซ้ำกัน
                  (ต่างแปลนต่างจุดเริ่ม 0 -> เลื่อนให้ชื่อที่ซ้ำตรงกัน; ชื่อซ้ำ >= 2 เส้นแต่ระยะไม่ตรงกัน = ทิ้งแปลนนั้นพร้อมเตือน
                  ไม่เฉลี่ยให้เนียน; ชื่อซ้ำเส้นเดียว = รับแต่ติดธง weak)
  Leveling   : Find ART = route_page(): รหัสแผ่นขึ้นต้น A (จาก Pass 1) จัดอันดับด้วยชื่อแผ่น/เลขระดับในข้อความฝัง
               (ไม่มีหน้า A เลย = ใช้หน้าที่ข้อความฝังมีเลขระดับ >= 3 ค่า พร้อมธง; เล่ม 174 ระดับอยู่หน้าแปลนโครงสร้าง)
               Match = levelarm_probe (OCR เลขระดับ + ชื่อไทย + floor_of) -> **LVL DB** = build_level_master():
               floors[] ตามสเปก level_master (floor_level, level_m, structure_level_m, printed_as) + ทะเบียนเลขระดับ z_levels
               (ชนะด้วยจำนวนเสียงต่อชั้น; เสมอ = level_m None + candidates ไม่เดา; level_m ต้องมีใน z_levels ตามสเปก)
  **Proj. Grid DB** = proj_grid.json: grid_master + z_levels + level_master + warnings + ที่ยังไม่ทำ

ไม่ได้ทำ (ตรงตามแผนภาพแต่ยังไม่มีวิธีที่วัดแล้ว): "Find Site area", ฝั่ง PNG/หน้าสแกนของ Floor Plan (หาวงหัวเส้นจากเวกเตอร์เท่านั้น)
ผลลัพธ์ลง ../logic_test_out/<บ้าน>/ (นอก repo) · ไม่แตะเฉลย · ไม่เรียกโมเดล
"""
import argparse
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT.parent / "logic_test_out"

ALIGN_TOL = 0.05          # ม. ระยะระหว่างเส้นเดียวกันที่ต่างแปลนต้องตรงกันภายในนี้ถึงรวมได้ (เลือกเอง: เฉลยตรงกัน 0.02 ม. ใน eval ของสเกล)
SAME_POS_TOL = 0.02       # ม. สองชื่อห่างกันน้อยกว่านี้ = ตำแหน่งเดียวกัน (เฉลยมีเส้นห่างกัน 0.05 ม. จึงไม่ชนกัน)
MIN_LINES = 2             # แปลนที่มีเส้นมีชื่อ+เมตรน้อยกว่านี้ไม่พอจัดแนว
ART_RE = re.compile(r"^A[R]?[-_ ]?\d", re.I)                       # รหัสแผ่นสถาปัตย์: A-04, A04, AR-01
NAME_HINT = re.compile(r"รูปตัด|รูปด้าน|ด้าน|section|elevation", re.I)
MIN_TEXT_LEVELS = 3       # ทางสำรองเมื่อไม่มีหน้า A: ข้อความฝังมีเลขระดับอย่างน้อยกี่ค่า


# ---------- Grid Master DB (pure) ----------

def plans_from_result(result):
    """result.json ของ run_part1_part3 -> [{page, plan, x:[(label,pos_m)], y:[...], scale_source}] เฉพาะเส้นที่มีชื่อและเมตร"""
    plans = []
    for rec in result.get("pages", []):
        g = rec.get("grid")
        if not g:
            continue
        by = defaultdict(lambda: {"v": [], "h": []})
        for ax in ("v", "h"):
            for ln in g["lines"].get(ax, []):
                if ln.get("label") and ln.get("pos_m") is not None:
                    by[ln.get("plan")][ax].append((str(ln["label"]), float(ln["pos_m"])))
        for pid, axes in by.items():
            plans.append(dict(page=rec["pdf_page"], plan=pid, x=axes["v"], y=axes["h"],
                              scale_source=(g.get("scales", {}).get(str(pid)) or {}).get("source")))
    return plans


def merge_axis(entries, tol=ALIGN_TOL):
    """entries = [(page, plan, [(label, pos_m)])] -> (lines, warnings)
    แปลนอ้างอิง = แปลนที่มีเส้นมากสุด (เท่ากัน = หน้าน้อยกว่า); แปลนอื่นเลื่อนให้ชื่อที่ซ้ำกับ master ตรงกัน"""
    warns, usable = [], []
    for page, plan, ls in entries:
        labels = [l for l, _ in ls]
        if len(set(labels)) != len(labels):
            warns.append(f"plan p{page}#{plan}: duplicate label inside the plan - skipped")
        elif len(ls) < MIN_LINES:
            warns.append(f"plan p{page}#{plan}: {len(ls)} named+scaled line(s) - too few to align, skipped")
        else:
            usable.append((page, plan, dict(ls)))
    if not usable:
        return [], warns
    usable.sort(key=lambda e: (-len(e[2]), e[0], e[1] if e[1] is not None else -1))
    ref = usable[0]
    pos = {l: [p] for l, p in ref[2].items()}          # label -> aligned positions
    pages = {l: {ref[0]} for l in ref[2]}
    weak = set()
    for page, plan, d in usable[1:]:
        shared = [l for l in d if l in pos]
        if not shared:
            warns.append(f"plan p{page}#{plan}: shares no label with the master - not aligned, skipped")
            continue
        offs = [statistics.median(pos[l]) - d[l] for l in shared]
        if len(shared) >= 2 and max(offs) - min(offs) > tol:
            warns.append(f"plan p{page}#{plan}: shared labels {shared} disagree on distances "
                         f"(offsets {[round(o, 2) for o in offs]}) - skipped, not averaged")
            continue
        off = statistics.median(offs)
        for l, p in d.items():
            if l not in pos:
                pos[l], pages[l] = [], set()
                if len(shared) == 1:
                    weak.add(l)
            pos[l].append(p + off)
            pages[l].add(page)
    lines = []
    for l, ps in pos.items():
        e = dict(id=l, pos_m=round(statistics.median(ps), 2), votes=len(ps), pages=sorted(pages[l]))
        if max(ps) - min(ps) > tol:
            e["spread_m"] = round(max(ps) - min(ps), 2)
        if l in weak:
            e["weak"] = True
        lines.append(e)
    lines.sort(key=lambda e: e["pos_m"])
    base = lines[0]["pos_m"]
    for e in lines:
        e["pos_m"] = round(e["pos_m"] - base, 2)       # จุดเริ่ม 0 = เส้นแรกของ master (ไม่ใช่เส้นอ้างอิงของเฉลย)
    lines, w = resolve_same_position(lines)
    return lines, warns + w


def resolve_same_position(lines):
    """สองชื่อที่ตำแหน่งเดียวกัน (< SAME_POS_TOL) = เส้นกริดสองเส้นซ้อนกันไม่ได้ (เช่น OCR อ่าน '1' เป็น '7' ในแปลนเดียว):
    เก็บชื่อที่เสียงมากกว่า ทิ้งชื่อน้อย + เตือน · เสียงเท่ากัน = เก็บทั้งคู่ + เตือน ไม่เดา
    (กติกานี้เกิดหลังเห็น 2 เส้นเกินในชุดวัด 10 บ้าน — ตัวเลขหลังมีกติกาเป็น in-sample)"""
    out, warns, i = [], [], 0
    while i < len(lines):
        j = i + 1
        while j < len(lines) and lines[j]["pos_m"] - lines[j - 1]["pos_m"] < SAME_POS_TOL:
            j += 1
        grp = lines[i:j]
        if len(grp) == 1:
            out.append(grp[0])
        else:
            top = max(e["votes"] for e in grp)
            winners = [e for e in grp if e["votes"] == top]
            names = ", ".join(f"{e['id']} ({e['votes']})" for e in grp)
            if len(winners) == 1:
                out.append(winners[0])
                warns.append(f"label conflict at {winners[0]['pos_m']} m: {names} - kept {winners[0]['id']}")
            else:
                out += grp
                warns.append(f"label conflict at {grp[0]['pos_m']} m: {names} - same votes, all kept")
        i = j
    return out, warns


def merge_plans(plans):
    """-> grid master (x_lines = เส้นตั้ง, y_lines = เส้นนอน) + warnings"""
    out, warns = {}, []
    for key in ("x", "y"):
        lines, w = merge_axis([(p["page"], p["plan"], p[key]) for p in plans], ALIGN_TOL)
        out[key + "_lines"] = lines
        warns += [f"{key}: {m}" for m in w]
    out["plans_used"] = len(plans)
    return out, warns


# ---------- Leveling (pure) ----------

def route_page(rec):
    """หน้าหนึ่งของ result.json -> dict(floor_plan, art): floor_plan = มีวงหัวเส้นทั้งสองแกน, art = รหัสแผ่นขึ้นต้น A"""
    code = ((rec.get("title") or {}).get("sheet_code") or "").strip()
    return dict(floor_plan=bool(rec.get("grid")), art=bool(ART_RE.match(code)))


def rank_level_pages(cands, max_pages):
    """cands = [dict(page, art, n_text_levels, name_hint)] -> (pages, note)
    ลำดับ: หน้า A ก่อน -> ชื่อแผ่นเป็นรูปตัด/รูปด้าน -> เลขระดับในข้อความฝังมาก -> หน้าน้อย
    ไม่มีหน้า A เลย: ใช้หน้าที่ข้อความฝังมีเลขระดับ >= MIN_TEXT_LEVELS ค่า (note บอกไว้)"""
    pool = [c for c in cands if c["art"]]
    note = None
    if not pool:
        pool = [c for c in cands if c["n_text_levels"] >= MIN_TEXT_LEVELS]
        note = "no_art_pages_used_text_layer_level_pages" if pool else "no_art_pages_and_no_text_layer_levels"
    pool.sort(key=lambda c: (-int(c["name_hint"]), -c["n_text_levels"], c["page"]))
    return [c["page"] for c in pool[:max_pages]], note


SCAN_MIN_LEVELS = 3       # สแกนหยาบ: หน้าที่เจอเลขระดับน้อยกว่านี้ไม่ถือเป็นหน้าระดับ (เลือกเอง)


def drawing_like_pages(recs):
    """ไม่มีรหัส A ให้ใช้: หน้าที่เป็นแบบ (เวกเตอร์ >= 200 เส้น หรือภาพสแกน) ตัดหน้าฟอร์ม/ว่างออก -> [เลขหน้า]"""
    return [r["pdf_page"] for r in recs if r.get("kind") in ("vector", "mixed") and r.get("n_lines", 0) >= 200
            or r.get("kind") == "raster"]


def pick_by_scan(counts, max_pages, min_levels=SCAN_MIN_LEVELS):
    """counts = {หน้า: จำนวนเลขระดับที่สแกนหยาบเจอ} -> หน้าที่ต้องอ่านเต็ม (มากไปน้อย; เท่ากัน = หน้าน้อยก่อน)"""
    ok = [(n, p) for p, n in counts.items() if n >= min_levels]
    ok.sort(key=lambda t: (-t[0], t[1]))
    return [p for _, p in ok[:max_pages]]


def scan_level_counts(doc, pages, turns_by_page=None, px=1600):
    """สแกนหยาบ: OCR ตัวอ่านละตินอย่างเดียวที่ด้านยาว px พิกเซล นับเลขระดับต่อหน้า (ไม่อ่านชื่อไทย = เร็ว)"""
    import numpy as np
    import levelarm_probe as L
    import titleblock_extract as T
    out = {}
    for pn in pages:
        page = doc[pn - 1]
        W, H = page.rect.width, page.rect.height
        pix = page.get_pixmap(dpi=max(20, int(px / (max(W, H) / 72))))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        img = img[:, :, :3] if pix.n >= 3 else np.repeat(img, 3, axis=2)
        t = (turns_by_page or {}).get(pn) or 0
        out[pn] = len(L.level_numbers(L._ocr(np.ascontiguousarray(np.rot90(img, -t) if t else img), T._reader())))
    return out


def floor_code(name):
    import levelarm_probe as L
    return L.floor_of(name)


def build_level_master(readings):
    """readings = [dict(page, value_m, name)] -> (z_levels, floors, warnings)
    z_levels = ทะเบียนเลขระดับที่อ่านได้ทุกค่า (id = ชื่อที่ผูกได้ ไม่งั้น None); floors = ชั้นที่ชื่อบอก (ชนะด้วยเสียงมากสุด)"""
    warns = []
    reg = {}
    for r in readings:
        e = reg.setdefault(round(r["value_m"], 2), dict(level_m=round(r["value_m"], 2), names=Counter(), pages=set(), votes=0))
        e["votes"] += 1
        e["pages"].add(r["page"])
        if r.get("name"):
            e["names"][r["name"]] += 1
    z_levels = [dict(id=(e["names"].most_common(1)[0][0] if e["names"] else None), level_m=e["level_m"],
                     votes=e["votes"], source_pages=sorted(e["pages"])) for _, e in sorted(reg.items())]
    by_floor = defaultdict(Counter)
    names = defaultdict(Counter)
    pages = defaultdict(set)
    for r in readings:
        f = floor_code(r.get("name"))
        if f:
            by_floor[f][round(r["value_m"], 2)] += 1
            names[f][r["name"]] += 1
            pages[f].add(r["page"])
    floors = []
    for f, votes in by_floor.items():
        top = votes.most_common()
        tie = len(top) > 1 and top[0][1] == top[1][1]
        e = dict(floor_level=f, level_m=None if tie else top[0][0], structure_level_m=None,
                 printed_as=names[f].most_common(1)[0][0], votes=top[0][1] if not tie else 0, pages=sorted(pages[f]))
        if len(top) > 1:
            e["candidates"] = [dict(level_m=v, votes=n) for v, n in top]
            warns.append(f"floor {f}: more than one level read {[v for v, _ in top]}" + (" - tie, level_m left empty" if tie else ""))
        floors.append(e)
    floors.sort(key=lambda e: (e["level_m"] is None, e["level_m"] if e["level_m"] is not None else 0))
    warns += check_level_master(floors, z_levels)
    return z_levels, floors, warns


def check_level_master(floors, z_levels):
    """สเปก level_master: level_m ของทุกชั้นต้องเท่ากับค่าใน z_levels (ปฏิเสธระดับที่แต่งขึ้น) · ลำดับชั้นต้องสูงขึ้น (F1<F2<…<RF)"""
    warns = []
    vals = {e["level_m"] for e in z_levels}
    for f in floors:
        if f["level_m"] is not None and f["level_m"] not in vals:
            warns.append(f"floor {f['floor_level']}: level_m {f['level_m']} is not in z_levels - rejected")
    def key(f):
        c = f["floor_level"]
        m = re.fullmatch(r"F(\d+)", c)
        return int(m.group(1)) if m else (1000 if c == "RF" else None)
    seq = sorted((f for f in floors if f["level_m"] is not None and key(f) is not None), key=key)
    for a, b in zip(seq, seq[1:]):
        if b["level_m"] <= a["level_m"]:
            warns.append(f"floor order: {a['floor_level']} {a['level_m']} m is not below {b['floor_level']} {b['level_m']} m")
    return warns


def build_proj(house, grid, warns_grid, z_levels, floors, warns_level, notes):
    return dict(house=house,
                grid_master=dict(x_lines=grid["x_lines"], y_lines=grid["y_lines"], z_levels=z_levels, plans_used=grid["plans_used"]),
                level_master=dict(pattern="level_master", level=dict(floors=[{k: f[k] for k in
                                  ("floor_level", "level_m", "structure_level_m", "printed_as")} for f in floors]),
                                  detail=floors),
                warnings=warns_grid + warns_level, notes=notes,
                not_done=["find_site_area", "floor_plan_on_png_scanned_pages"])


# ---------- ต่อกับของจริง (impure) ----------

def read_page_levels(page, turns=0):
    """OCR หน้าเดียว -> [dict(value_m, name, where)] ผ่าน levelarm_probe (เลขละติน + ชื่อไทย ผูกด้วยกล่อง); ไม่เก็บข้อความดิบ"""
    import levelarm_probe as L
    rec = L.ocr_page_lines(page, turns)
    nums = [(v, box) for v, _, box in L.level_numbers([(t, b) for t, b in rec["lat"]])]
    return [dict(value_m=v, name=n, where=w) for v, n, w in L.bind_names(nums, [(t, b) for t, b in rec["th"]])]


def level_candidates(doc, recs):
    """ทุกหน้าของบ้าน -> cands สำหรับ rank_level_pages (ข้อความฝังเท่านั้น = เร็ว; หน้าสแกนไม่มีข้อความฝัง n_text_levels=0)"""
    import levelarm_probe as L
    out = []
    for rec in recs:
        n = rec["pdf_page"]
        r = route_page(rec)
        out.append(dict(page=n, art=r["art"], name_hint=bool(NAME_HINT.search((rec.get("title") or {}).get("sheet_name") or "")),
                        n_text_levels=len(L.page_levels(doc[n - 1]))))
    return out


def result_direct(house, ocr=True):
    """โหมด direct (ใช้ตอนวัด grid master ไม่ต้องอ่านกรอบชื่อแบบ): คัดหน้าที่มีวงหัวเส้นทั้งสองแกนด้วยเรขาคณิต -> detect -> สเกล
    -> โครงเดียวกับ result.json ของตัวรัน (plans_from_result อ่านต่อได้ = ตัวรวมตัวเดียวกัน)"""
    import fitz
    import gridlab_probe as G
    import gridlab_scale as S
    import run_part1_part3 as R
    import titleblock_extract as T
    pages = []
    for i, page in enumerate(fitz.open(T.pdf_of(house))):
        if not R.is_grid_candidate(page):
            continue
        lines = G.detect(page, ocr=ocr)
        sc = S.plan_scales(page, lines, ocr=ocr)
        pages.append(dict(pdf_page=i + 1, title={}, grid=dict(
            scales={str(k): dict(scale_pt_per_m=v["scale"], source=v["source"]) for k, v in sc.items()},
            lines={ax: [{k: v for k, v in ln.items() if k in ("pos", "pos_m", "label", "plan")} for ln in lines[ax]] for ax in lines})))
    return dict(house=house, pages=pages, direct=True)


def run_house(house, out_dir=DEFAULT_OUT, ocr=True, levels=True, max_level_pages=6, reuse=True, direct=False,
              level_pages=None, scan=True, scan_cap=40):
    import fitz
    import run_part1_part3 as R
    import titleblock_extract as T
    out = Path(out_dir) / house
    out.mkdir(parents=True, exist_ok=True)
    rj = out / "result.json"
    if direct:                                  # เก็บผลต่อแปลนไว้ (ไฟล์แยกจาก result.json ของตัวรัน) รวมใหม่ได้โดยไม่ OCR ซ้ำ
        rd = out / "result_direct.json"
        if reuse and rd.exists():
            result = json.loads(rd.read_text(encoding="utf-8"))
        else:
            result = result_direct(house, ocr)
            rd.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    else:
        if not (reuse and rj.exists()):
            R.run(house, out_dir, ocr=ocr)
        result = json.loads(rj.read_text(encoding="utf-8"))
    t0 = time.time()
    grid, wg = merge_plans(plans_from_result(result))
    z_levels, floors, wl, notes = [], [], [], []
    if levels:
        doc = fitz.open(T.pdf_of(house))
        recs = result["pages"]
        pages, note = rank_level_pages(level_candidates(doc, recs), max_level_pages)
        notes.append(note) if note else None
        if level_pages or (scan and not pages):
            if level_pages:
                pages = [p for p in level_pages if 1 <= p <= len(doc)]
                notes.append("level_pages_given_by_user")
            else:                                  # ไม่มีหน้า A / ไม่มีเลขระดับในข้อความฝัง: สแกนหยาบทั้งเล่ม (วัดแล้วว่าไม่มีทางอื่น)
                pool = drawing_like_pages(recs)[:scan_cap]
                turns = {r["pdf_page"]: (r.get("orient") or {}).get("turns") or 0 for r in recs}
                counts = scan_level_counts(doc, pool, turns)
                pages = pick_by_scan(counts, max_level_pages)
                notes.append(f"coarse_scan pages={len(pool)} with_levels={sorted(p for p, n in counts.items() if n >= SCAN_MIN_LEVELS)}")
        readings = []
        for pn in pages:
            turns = (recs[pn - 1].get("orient") or {}).get("turns") or 0
            for r in read_page_levels(doc[pn - 1], turns):
                readings.append(dict(r, page=pn))
        z_levels, floors, wl = build_level_master(readings)
        notes.append(f"level_pages_read={pages}")
    proj = build_proj(house, grid, wg, z_levels, floors, wl, notes)
    (out / "grid_master.json").write_text(json.dumps(dict(x_lines=grid["x_lines"], y_lines=grid["y_lines"],
                                                           plans_used=grid["plans_used"], warnings=wg), ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "level_master.json").write_text(json.dumps(dict(pattern="level_master", level=proj["level_master"]["level"],
                                                            z_levels=z_levels, detail=floors, warnings=wl), ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "proj_grid.json").write_text(json.dumps(proj, ensure_ascii=False, indent=1), encoding="utf-8")
    proj["seconds_pass3"] = round(time.time() - t0, 1)
    return proj


# ---------- เทียบเฉลย ----------

def gt_grid(house):
    """เส้นมีชื่อ (type != dummy) ของเฉลย: ({id: pos_m} แกน x, {id: pos_m} แกน y) — json_แก้ไขแล้วชนะ raw"""
    for base in ("json_แก้ไขแล้ว", "rawjson_ยังไม่ได้แก้ไขโดนคน"):
        for d in (ROOT / base).glob(f"*{house}"):
            for f in d.glob("*gridline*.json"):
                g = json.loads(f.read_text(encoding="utf-8")).get("grid", {})
                pick = lambda k: {str(l["id"]): l.get("pos_m") for l in g.get(k, []) if l.get("type") != "dummy"}
                return pick("x_lines"), pick("y_lines"), base
    return None


def compare_axis(master_lines, gt):
    """-> dict(found, missing, extra, gaps, gaps_ok): found = ชื่อของ master ที่อยู่ในเฉลย; gaps = ช่องระหว่างเส้นติดกัน (ชื่อมีในเฉลย)"""
    ml = [l for l in master_lines]
    found = [l["id"] for l in ml if l["id"] in gt]
    ml_gt = [l for l in ml if l["id"] in gt and isinstance(gt[l["id"]], (int, float))]
    gaps = ok = 0
    for a, b in zip(ml_gt, ml_gt[1:]):
        gaps += 1
        ok += abs(abs(b["pos_m"] - a["pos_m"]) - abs(gt[b["id"]] - gt[a["id"]])) <= 0.02
    return dict(found=len(found), master=len(ml), gt=len(gt), missing=sorted(set(gt) - {l["id"] for l in ml}),
                extra=sorted({l["id"] for l in ml} - set(gt)), gaps=gaps, gaps_ok=ok)


def gt_level_master(house):
    for d in (ROOT / "rawjson_ยังไม่ได้แก้ไขโดนคน").glob(f"*{house}"):
        for f in d.glob("*หน้า00_level.json"):
            return {e["floor_level"]: e["level_m"] for e in json.loads(f.read_text(encoding="utf-8"))["level"]["floors"]}
    return None


def evaluate(houses, out_dir=DEFAULT_OUT, ocr=True, levels=False, max_level_pages=6):
    tot = Counter()
    for h in houses:
        gt = gt_grid(h)
        t0 = time.time()
        proj = run_house(h, out_dir, ocr=ocr, levels=levels, max_level_pages=max_level_pages, direct=not levels)
        row = dict(house=h, seconds=round(time.time() - t0), plans=proj["grid_master"]["plans_used"])
        if gt:
            for key, g in (("x", gt[0]), ("y", gt[1])):
                c = compare_axis(proj["grid_master"][key + "_lines"], g)
                row[key] = c
                for k in ("found", "master", "gt", "gaps", "gaps_ok"):
                    tot[k] += c[k]
                tot["missing"] += len(c["missing"])
                tot["extra"] += len(c["extra"])
        if levels:
            gl = gt_level_master(h)
            got = {f["floor_level"]: f["level_m"] for f in proj["level_master"]["detail"]}
            row["floors"] = got
            if gl:
                row["gt_floors"] = gl
                for k, v in gl.items():
                    tot["gt_floors"] += 1
                    tot["floor_found"] += k in got
                    tot["floor_level_ok"] += k in got and got[k] is not None and abs(got[k] - v) <= 0.05
        print(json.dumps(row, ensure_ascii=False), flush=True)
    print("TOTAL", dict(tot), flush=True)


# ---------- self-check ----------

def demo():
    L = lambda *p: list(p)
    # 1. สองแปลน คนละจุดเริ่ม: แปลนเล็กเริ่ม C=0 ต้องเลื่อนเข้า master, E เป็นเส้นใหม่
    a = (1, 0, [("A", 0.0), ("B", 3.0), ("C", 6.0), ("D", 9.0)])
    b = (2, 0, [("C", 0.0), ("D", 3.0), ("E", 6.5)])
    lines, w = merge_axis([b, a])
    assert [(l["id"], l["pos_m"]) for l in lines] == [("A", 0.0), ("B", 3.0), ("C", 6.0), ("D", 9.0), ("E", 12.5)], lines
    assert not w and next(l for l in lines if l["id"] == "C")["votes"] == 2
    # 2. ชื่อซ้ำ >= 2 เส้นแต่ระยะไม่ตรง (สเกลผิด) = ทิ้งทั้งแปลนพร้อมเตือน ไม่เฉลี่ย
    bad = (3, 0, [("A", 0.0), ("B", 4.0), ("C", 8.0)])
    lines, w = merge_axis([a, bad])
    assert [l["pos_m"] for l in lines] == [0.0, 3.0, 6.0, 9.0] and any("disagree" in m for m in w), (lines, w)
    # 3. ชื่อซ้ำเส้นเดียว = รับแต่ติดธง weak เฉพาะเส้นใหม่ · ไม่มีชื่อซ้ำเลย = ทิ้ง
    one = (4, 0, [("D", 0.0), ("F", 2.0)])
    lines, w = merge_axis([a, one])
    assert next(l for l in lines if l["id"] == "F") == dict(id="F", pos_m=11.0, votes=1, pages=[4], weak=True)
    assert "weak" not in next(l for l in lines if l["id"] == "D")
    lines, w = merge_axis([a, (5, 0, [("X", 0.0), ("Y", 1.0)])])
    assert len(lines) == 4 and any("shares no label" in m for m in w)
    # 4. ชื่อซ้ำในแปลนเดียว / เส้นน้อยเกิน = ข้าม
    lines, w = merge_axis([a, (6, 0, [("A", 0.0), ("A", 1.0)]), (7, 0, [("B", 0.0)])])
    assert len(lines) == 4 and len(w) == 2
    # 5. แปลนอ้างอิง = เส้นมากสุด ไม่ใช่หน้าแรก (แปลนขยายหน้าน้อยเลขมีเส้นน้อยต้องไม่เป็นฐาน) · จุดเริ่ม master เป็น 0 แม้เลื่อนไปติดลบ
    small_first = (1, 0, [("B", 0.0), ("C", 3.0)])
    big_later = (9, 0, [("A", 0.0), ("B", 3.0), ("C", 6.0), ("D", 9.0)])
    lines, _ = merge_axis([small_first, big_later])
    assert [(l["id"], l["pos_m"]) for l in lines] == [("A", 0.0), ("B", 3.0), ("C", 6.0), ("D", 9.0)], lines
    lines, _ = merge_axis([(1, 0, [("B", 0.0), ("C", 3.0), ("D", 6.0)]), (2, 0, [("A", 0.0), ("B", 2.5)])])
    assert lines[0]["id"] == "A" and lines[0]["pos_m"] == 0.0 and lines[-1]["pos_m"] == 8.5, lines
    # 6. plans_from_result: เฉพาะเส้นที่มีชื่อและเมตร, แยกตาม plan id
    res = dict(pages=[dict(pdf_page=3, grid=dict(scales={"0": dict(source="dimension_numbers")},
        lines=dict(v=[dict(label="1", pos_m=0.0, plan=0), dict(label=None, pos_m=2.0, plan=0), dict(label="2", pos_m=3.5, plan=0)],
                   h=[dict(label="A", pos_m=None, plan=0)])))])
    pl = plans_from_result(res)
    assert len(pl) == 1 and pl[0]["x"] == [("1", 0.0), ("2", 3.5)] and pl[0]["y"] == [] and pl[0]["scale_source"] == "dimension_numbers"
    # 7. route_page
    assert route_page(dict(grid=None, title=dict(sheet_code="A-04"))) == dict(floor_plan=False, art=True)
    assert route_page(dict(grid={"x": 1}, title=dict(sheet_code="S-01"))) == dict(floor_plan=True, art=False)
    assert route_page(dict(grid=None, title=dict(sheet_code="AR-12")))["art"] and route_page(dict(title={}))["art"] is False
    assert not route_page(dict(title=dict(sheet_code="ARCH")))["art"] and not route_page(dict(title=dict(sheet_code="EE-05")))["art"]
    # 8. rank_level_pages: A ก่อน > ชื่อรูปตัด > เลขระดับในข้อความ > หน้าน้อย · ไม่มี A = ทางสำรองจากข้อความฝัง + note
    c = [dict(page=5, art=True, n_text_levels=0, name_hint=False), dict(page=9, art=True, n_text_levels=8, name_hint=False),
         dict(page=7, art=True, n_text_levels=1, name_hint=True), dict(page=2, art=False, n_text_levels=20, name_hint=True)]
    assert rank_level_pages(c, 3) == ([7, 9, 5], None)
    p, note = rank_level_pages([dict(page=4, art=False, n_text_levels=2, name_hint=False), dict(page=8, art=False, n_text_levels=5, name_hint=False),
                                dict(page=6, art=False, n_text_levels=3, name_hint=False)], 5)
    assert p == [8, 6] and note == "no_art_pages_used_text_layer_level_pages"
    assert rank_level_pages([dict(page=1, art=False, n_text_levels=0, name_hint=True)], 5) == ([], "no_art_pages_and_no_text_layer_levels")
    # 9. build_level_master: เสียงมากสุดชนะ · เสมอ = level_m None + candidates + เตือน · ลำดับชั้นต้องสูงขึ้น · z_levels ครบ
    rd = lambda pg, v, n: dict(page=pg, value_m=v, name=n)
    z, fl, w = build_level_master([rd(8, 0.0, "ระดับพื้นชั้น 1"), rd(9, 0.0, "ระดับพื้นชั้น 1"), rd(9, 0.2, "ระดับพื้นชั้น 1"),
                                   rd(8, 3.2, "ระดับพื้นชั้น 2"), rd(8, 6.4, "ระดับหลังคา"), rd(8, 1.5, None)])
    by = {f["floor_level"]: f for f in fl}
    assert by["F1"]["level_m"] == 0.0 and by["F2"]["level_m"] == 3.2 and by["RF"]["level_m"] == 6.4, by
    assert [e["level_m"] for e in z] == [0.0, 0.2, 1.5, 3.2, 6.4] and next(e for e in z if e["level_m"] == 1.5)["id"] is None
    assert not w or all("floor order" not in m for m in w)
    z, fl, w = build_level_master([rd(1, 3.0, "ระดับพื้นชั้น 2"), rd(2, 3.5, "ระดับพื้นชั้น 2")])
    assert fl[0]["level_m"] is None and fl[0]["votes"] == 0 and len(fl[0]["candidates"]) == 2 and any("tie" in m for m in w), (fl, w)
    z, fl, w = build_level_master([rd(1, 5.0, "ระดับพื้นชั้น 1"), rd(1, 3.0, "ระดับพื้นชั้น 2")])
    assert any("floor order" in m for m in w), w                                  # F1 สูงกว่า F2 = ผิดลำดับ
    # 10. check_level_master: level_m ที่ไม่มีใน z_levels ถูกปฏิเสธ
    w = check_level_master([dict(floor_level="F1", level_m=1.23)], [dict(level_m=0.0)])
    assert any("not in z_levels" in m for m in w), w
    assert check_level_master([dict(floor_level="F1", level_m=None)], []) == []
    # 11. compare_axis: ช่องวัดด้วยระยะต่างสัมบูรณ์ (ไม่ขึ้นกับทิศ/จุดเริ่ม) · เส้นนอกเฉลยนับเป็น extra
    c = compare_axis([dict(id="A", pos_m=0.0), dict(id="B", pos_m=3.0), dict(id="Z", pos_m=7.0), dict(id="C", pos_m=9.5)],
                     {"A": 10.0, "B": 7.0, "C": 1.0, "D": 0.0})
    # A-B: |3-0|=3 ต่อเฉลย |7-10|=3 ตรง (ทิศกลับกันก็ตรง) · B-C: 6.5 ต่อ 6.0 ไม่ตรง · Z ไม่อยู่ในเฉลย = extra และไม่ถูกนับเป็นช่อง
    assert c["found"] == 3 and c["extra"] == ["Z"] and c["missing"] == ["D"] and c["gaps"] == 2 and c["gaps_ok"] == 1, c
    # 11b. ชื่อสองชื่อตำแหน่งเดียวกัน: เสียงมากชนะ (OCR อ่าน 1 เป็น 7 ในแปลนเดียว) · เท่ากัน = เก็บทั้งคู่ · ห่าง 0.05 ม. ไม่ใช่ตำแหน่งเดียวกัน
    p1 = [(i, 0, [("1", 0.0), ("2", 4.0), ("3", 7.0)]) for i in range(1, 6)]
    lines, w = merge_axis(p1 + [(9, 0, [("7", 0.0), ("2", 4.0)])])
    assert [(l["id"], l["pos_m"]) for l in lines] == [("1", 0.0), ("2", 4.0), ("3", 7.0)] and any("kept 1" in m for m in w), (lines, w)
    lines, w = merge_axis([(1, 0, [("A", 0.0), ("B", 3.0), ("C", 6.0)]), (2, 0, [("B", 0.0), ("X", 3.0)]), (3, 0, [("B", 0.0), ("Y", 3.0)])])
    assert sorted(l["id"] for l in lines if l["pos_m"] == 6.0) == ["C", "X", "Y"], lines      # เสียงเท่ากัน (1,1,1) = เก็บทั้งสาม
    assert sum("same votes" in m for m in w) == 1, w
    lines, w = merge_axis([(1, 0, [("A", 0.0), ("B", 3.5), ("C", 3.55), ("D", 7.0)])])
    assert [l["id"] for l in lines] == ["A", "B", "C", "D"] and not w, (lines, w)
    # 12. drawing_like_pages: แบบเวกเตอร์เส้นมาก + ภาพสแกน; ตัดฟอร์ม (เส้นน้อย) / หน้าว่าง
    recs = [dict(pdf_page=1, kind="raster", n_lines=0), dict(pdf_page=2, kind="vector", n_lines=5000), dict(pdf_page=3, kind="vector", n_lines=40),
            dict(pdf_page=4, kind="empty", n_lines=0), dict(pdf_page=5, kind="mixed", n_lines=900), dict(pdf_page=6, kind="mixed", n_lines=100)]
    assert drawing_like_pages(recs) == [1, 2, 5]
    # 13. pick_by_scan: ต่ำกว่าเกณฑ์ไม่เอา · มากไปน้อย · เท่ากันหน้าน้อยก่อน · จำกัดจำนวน
    assert pick_by_scan({3: 2, 5: 9, 7: 9, 8: 4, 9: 3}, 3) == [5, 7, 8] and pick_by_scan({1: 2, 2: 1}, 5) == []
    assert pick_by_scan({1: 3}, 5) == [1] and pick_by_scan({1: 3}, 5, min_levels=4) == []
    print("OK - self-check ผ่าน (pass3_grid: merge/route/rank/level/compare/scan)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("house", nargs="?")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--no-levels", action="store_true")
    ap.add_argument("--max-level-pages", type=int, default=6)
    ap.add_argument("--level-pages", help="เลขหน้าที่ให้อ่านเลขระดับ คั่นด้วยจุลภาค (ข้ามการหา ART/สแกนหยาบ) เช่น 5,8,10")
    ap.add_argument("--no-scan", action="store_true", help="ไม่สแกนหยาบเมื่อไม่มีหน้า A (ไม่อ่านระดับถ้าหาหน้าไม่เจอ)")
    ap.add_argument("--scan-cap", type=int, default=40, help="สแกนหยาบสูงสุดกี่หน้า (หน้าแบบแรก ๆ ตามลำดับ)")
    ap.add_argument("--eval", nargs="+", metavar="บ้าน")
    ap.add_argument("--eval-levels", action="store_true", help="--eval ด้วย: อ่านเลขระดับและเทียบ level master (ช้า)")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if a.eval:
        return evaluate(a.eval, a.out, ocr=not a.no_ocr, levels=a.eval_levels, max_level_pages=a.max_level_pages)
    if not a.house:
        ap.print_help()
        return
    proj = run_house(a.house, a.out, ocr=not a.no_ocr, levels=not a.no_levels, max_level_pages=a.max_level_pages,
                     level_pages=[int(x) for x in a.level_pages.split(",")] if a.level_pages else None,
                     scan=not a.no_scan, scan_cap=a.scan_cap)
    g = proj["grid_master"]
    print(f"{a.house}: grid x {len(g['x_lines'])} เส้น y {len(g['y_lines'])} เส้น จาก {g['plans_used']} แปลน · "
          f"ระดับ {len(g['z_levels'])} ค่า ชั้น {len(proj['level_master']['detail'])} · เตือน {len(proj['warnings'])} · ลง {Path(a.out) / a.house}")
    for m in proj["warnings"][:10]:
        print("  เตือน:", m)


if __name__ == "__main__":
    main()
