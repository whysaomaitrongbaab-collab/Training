#!/usr/bin/env python3
"""build_t05_night.py — สร้าง dataset 3 ส่วนใหม่ของ t05 Courser (มะขามเคาะ 2026-08-31 ดึก:
"ไม่ทุกอย่างต้องทำคืนนี้ให้พร้อม ทำ dataset — pass0 บ้าน 5 หลัง 4/1 · pass2.4 บ้าน 10 หลัง 8/2 ·
pass3 บ้าน 10 หลัง 8/2")

ผลลัพธ์ (โฟลเดอร์นี้): pass0_train/val.jsonl · pass24_train/val.jsonl · pass3_train/val.jsonl
+ รายการคิวที่ derive อัตโนมัติไม่ได้ (พิมพ์ท้ายรัน — ไม่เดา ไม่มั่ว)

กติกา matcher ของ pass3 (จับคู่ cv_mark ↔ GT — จับคู่ผิด = สอนผิดทั้งชุด บั๊กคลาส slugify):
รับเฉพาะเคสที่พิสูจน์ได้เท่านั้น เรียงจากง่ายไปยาก —
  (ก) หน้ามีไฟล์ GT โครงสร้างไฟล์เดียว (multi-view ข้าม — เข้าคิว eyeball)
  (ข) ต่อ class: จำนวน CV box == จำนวน GT element ชนิดนั้น (นับหลัง expand count)
  (ค1) id เดียวทั้ง class → จับคู่ได้ทันที (ลำดับไหนก็ถูก)
  (ค2) id ปนกัน/ต้องแจก grid_refs → **spatial matching ผ่าน gridmaster (v2)**: แปลง grid_refs
      เป็น (x_m, y_m) จาก pos_m แล้วลองทั้ง 8 orientation (พลิกแกน×2, swap แกน) จับคู่แบบ
      row-major เทียบกับลำดับ CV box — รับเฉพาะเมื่อ (1) ลำดับ pixel กับลำดับ grid สอดคล้อง
      แบบ monotonic ทุกคู่ และ (2) ทุก orientation ที่ผ่านให้คำตอบ id ต่อ box ตรงกันหมด
      ไม่ผ่านเงื่อนไขใด = eyeball ไม่เดา
"""
import json
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent.parent
GT_ROOT = TRAINING / "json_แก้ไขแล้ว"
IMG_ROOT = TRAINING / "image"
T04 = TRAINING / "tune_ai" / "t04_Purson"
DATA_T04 = T04 / "data_before_tune"

TRAIN_HOUSES_10 = ["บ้าน_เล็ก_2ชั้น_04", "บ้าน_เล็ก_2ชั้น_19", "บ้าน_เล็ก_2ชั้น_01",
                   "บ้าน_เล็ก_2ชั้น_03", "บ้าน_เล็ก_1ชั้น_04", "บ้าน_เล็ก_1ชั้น_03",
                   "บ้าน_ใหญ่_2ชั้น_04", "บ้าน_ใหญ่_1ชั้น_01"]
VAL_HOUSES = ["บ้าน_เล็ก_2ชั้น_05", "บ้าน_ใหญ่_1ชั้น_02"]
PASS0_TRAIN = ["บ้าน_เล็ก_2ชั้น_04", "บ้าน_เล็ก_1ชั้น_04", "บ้าน_ใหญ่_2ชั้น_04", "บ้าน_ใหญ่_1ชั้น_01"]
PASS0_VAL = ["บ้าน_เล็ก_2ชั้น_05"]

CV_TO_GT_TYPES = {
    "column": {"column"},
    "footing": {"footing", "pile_cap"},
    "beam_h": {"beam", "tie_beam"},
    "beam_v": {"beam", "tie_beam"},
}
PLAN_PATTERNS = {"footing_plan", "beam_plan", "roof_frame_plan", "etc_plan", "plan"}


def bare(h):
    return re.sub(r"^\d{2}", "", h)


def read_jsonl(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def write_jsonl(p, rows):
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def house_of_id(rid):
    return bare(rid.split("::")[0])


def page_of_image(img_name):
    m = re.search(r"หน้า(\d+[ab]?)", img_name)
    return m.group(1) if m else None


# ── pass0 ────────────────────────────────────────────────────────────────
def prompt_pass0():
    txt = (T04 / "pass0" / "prompt.md").read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)\n## PROMPT END", txt, re.DOTALL)
    return m.group(1).strip()


def build_pass0():
    p0 = prompt_pass0()
    rows_by_house = defaultdict(list)
    for r in read_jsonl(HERE / "pass0_labels.jsonl"):
        h = bare(r["house"])
        if h not in PASS0_TRAIN + PASS0_VAL:
            continue
        rows_by_house[h].append({
            "id": f"{r['house']}::หน้า{r['page']}::pass0",
            "house": r["house"], "subtask": "pass0",
            "messages": [
                {"role": "user", "content": [
                    {"type": "image", "image": r["image"].replace("\\", "/")},
                    {"type": "text", "text": p0},
                ]},
                {"role": "assistant", "content": json.dumps(r["label"], ensure_ascii=False)},
            ],
        })
    queue = [r for r in read_jsonl(HERE / "pass0_manual_queue.jsonl")
             if bare(r["house"]) in PASS0_TRAIN + PASS0_VAL]
    train = [x for h in PASS0_TRAIN for x in rows_by_house[h]]
    val = [x for h in PASS0_VAL for x in rows_by_house[h]]
    write_jsonl(HERE / "pass0_train.jsonl", train)
    write_jsonl(HERE / "pass0_val.jsonl", val)
    return len(train), len(val), queue


# ── pass2.4a (hint arm) ─────────────────────────────────────────────────
def build_pass24():
    plan_subs = {"plan_footing", "plan_beam", "plan_slab"}
    src = read_jsonl(DATA_T04 / "train.jsonl") + read_jsonl(DATA_T04 / "val.jsonl")
    train, val, no_hint = [], [], []
    seen = set()
    for r in src:
        if r.get("subtask") not in plan_subs or r["id"] in seen:
            continue
        seen.add(r["id"])
        h = house_of_id(r["id"])
        if h not in TRAIN_HOUSES_10 + VAL_HOUSES:
            continue
        imgs = [c["image"] for c in r["messages"][0]["content"] if c.get("type") == "image"]
        if len(imgs) != 1:
            continue
        name = Path(imgs[0]).name
        hint_p = IMG_ROOT / h / (Path(name).stem + "_hint25.txt")
        if not hint_p.exists():
            no_hint.append(r["id"])
            continue
        hint = hint_p.read_text(encoding="utf-8").strip()
        content = [dict(c) for c in r["messages"][0]["content"]]
        # แก้ path: ต้นทาง (t04 data_before_tune) ใช้ "images/<flat>.png" ชี้ไปโฟลเดอร์แบนที่มีแค่
        # ในเครื่องเทรน t04 เอง — ที่นี่ไม่มีโฟลเดอร์นั้น ทุกไฟล์อื่นของ t05 ใช้ "image/<house>/<flat>.png"
        # เทียบกับรากของ Training repo อยู่แล้ว (รูปเดียวกัน ไฟล์เดียวกัน แค่คนละ prefix) — ต้อง
        # rewrite ให้ตรงกัน ไม่งั้น path ค้างจากคนละที่ทำงาน หาไฟล์รูปไม่เจอตอนเทรนจริง
        for c in content:
            if c.get("type") == "image":
                c["image"] = f"image/{h}/{Path(c['image']).name}"
        # convention เดียวกับ apply_arm ของ infer: hint เป็น text ต่อท้าย
        content.append({"type": "text", "text": "\n\n" + hint})
        row = {**r, "id": r["id"] + "::arm24",
               "messages": [{"role": "user", "content": content}, r["messages"][1]]}
        (val if h in VAL_HOUSES else train).append(row)
    write_jsonl(HERE / "pass24_train.jsonl", train)
    write_jsonl(HERE / "pass24_val.jsonl", val)
    return len(train), len(val), no_hint


# ── pass3 ────────────────────────────────────────────────────────────────
MARKED_DIR = HERE / "marked_t5"
CLASS_RGB = {"footing": (255, 0, 0), "column": (0, 160, 0),
             "beam_h": (0, 80, 255), "beam_v": (0, 80, 255)}


def render_marked(src_img, boxes, out_path):
    """วาดกรอบ+เลขเฉพาะกล่องในบัญชี (PIL — path ไทยบน Windows ใช้ได้ ต่างจาก cv2.imread)
    สไตล์เดียวกับ pattern_recognition.draw_marks: กรอบสี + เลขมุมบนซ้าย"""
    from PIL import Image, ImageDraw
    MARKED_DIR.mkdir(exist_ok=True)
    im = Image.open(src_img).convert("RGB")
    dr = ImageDraw.Draw(im)
    for b in boxes:
        color = CLASS_RGB.get(b["class"], (128, 0, 128))
        x0, y0 = b["cx"] - b["w"] // 2, b["cy"] - b["h"] // 2
        x1, y1 = b["cx"] + b["w"] // 2, b["cy"] + b["h"] // 2
        dr.rectangle([x0, y0, x1, y1], outline=color, width=4)
        txt = str(b["n"])
        tw = 14 * len(txt) + 8
        dr.rectangle([x0, y0 - 26, x0 + tw, y0], fill=color)
        dr.text((x0 + 4, y0 - 24), txt, fill=(255, 255, 255))
    im.save(out_path)


def prompt_pass3():
    common = (T04 / "_common.md").read_text(encoding="utf-8")
    txt = (T04 / "pass3_takeoff" / "prompt.md").read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)\n## PROMPT END", txt, re.DOTALL)
    return common + "\n\n" + m.group(1).strip()


# ── spatial matcher v2 (ค2) ─────────────────────────────────────────────
REF_RX = re.compile(r"([A-Za-z]+)\s*-?\s*(\d+)")


def load_gridmaster(gt_dir, d):
    """เลือก gridmaster ตาม grid_source ของไฟล์ GT (บ้านที่มีอาคารรองมีกริดแยก)"""
    src = (d.get("grid_source") or "")
    cand = None
    for fp in gt_dir.glob("*gridline*.json"):
        if src and Path(src).name == fp.name:
            cand = fp
            break
        if cand is None:
            cand = fp
    if cand is None:
        return None
    try:
        g = json.loads(cand.read_text(encoding="utf-8")).get("grid") or {}
    except json.JSONDecodeError:
        return None
    pos = {}
    for axis in ("x_lines", "y_lines"):
        for ln in g.get(axis) or []:
            if ln.get("pos_m") is not None:
                pos[str(ln.get("id")).strip().upper()] = (axis, float(ln["pos_m"]))
    return pos or None


def ref_to_xy(ref, gridpos):
    m = REF_RX.search(str(ref))
    if not m:
        return None
    a, b = m.group(1).upper(), m.group(2)
    pa, pb = gridpos.get(a), gridpos.get(b)
    if not pa or not pb or pa[0] == pb[0]:
        return None
    x = pa[1] if pa[0] == "x_lines" else pb[1]
    y = pb[1] if pa[0] == "x_lines" else pa[1]
    return (x, y)


def expand_pool(pool):
    """GT รวม count → รายชิ้น: ทำได้เฉพาะเมื่อ len(grid_refs) == count (แต่ละชิ้นได้ ref ตัวเอง)
    คืน None ถ้า expand ไม่ได้อย่างปลอดภัย"""
    out = []
    for e in pool:
        c = e.get("count") or 1
        if c == 1:
            out.append(e)
            continue
        refs = e.get("grid_refs") or []
        if len(refs) != c:
            return None
        for r in refs:
            inst = json.loads(json.dumps(e, ensure_ascii=False))
            inst["count"] = 1
            inst["grid_refs"] = [r]
            out.append(inst)
    return out


def spatial_match(boxes, pool, gridpos):
    """คืน list GT-instance เรียงตาม boxes (จับคู่แล้ว) หรือ None ถ้าพิสูจน์ไม่ได้
    boxes เรียงตาม n อยู่แล้ว (row-major บน→ล่าง ซ้าย→ขวา จาก cv_scan)"""
    pts = []
    for e in pool:
        refs = e.get("grid_refs") or []
        xy = ref_to_xy(refs[0], gridpos) if len(refs) == 1 else None
        if xy is None:
            return None
        pts.append(xy)
    if len({p for p in pts}) < 3:
        return None  # จุดน้อย/ซ้ำ — แยก orientation ไม่ออก
    tol_px = max(20, int(sum(b["w"] for b in boxes) / len(boxes) / 2))
    assignments = []
    for swap in (False, True):
        for sx in (1, -1):
            for sy in (1, -1):
                uv = [((x if not swap else y) * sx, (y if not swap else x) * sy) for x, y in pts]
                order = sorted(range(len(pool)), key=lambda i: (round(uv[i][1], 3), uv[i][0]))
                # ตรวจ monotonic ทุกคู่: pixel ↔ grid ต้องเรียงทางเดียวกัน
                okc = True
                for ai in range(len(boxes)):
                    for bi in range(len(boxes)):
                        if ai == bi:
                            continue
                        ba, bb = boxes[ai], boxes[bi]
                        ua, ub = uv[order[ai]], uv[order[bi]]
                        if ba["cy"] < bb["cy"] - tol_px and ua[1] > ub[1] + 1e-6:
                            okc = False
                            break
                        if abs(ba["cy"] - bb["cy"]) <= tol_px and ba["cx"] < bb["cx"] - tol_px \
                                and ua[1] == ub[1] and ua[0] > ub[0] + 1e-6:
                            okc = False
                            break
                    if not okc:
                        break
                if okc:
                    # เก็บ "เนื้อหา" ที่จับคู่ (id + refs) — id ตรงกันเฉย ๆ ไม่พอ เพราะ instance
                    # id เดียวกันอาจถือ grid_refs คนละตัว → label ต่างกันจริง
                    assignments.append(tuple(
                        (pool[i].get("element_id"), tuple(pool[i].get("grid_refs") or []))
                        for i in order))
                    good_order = order
    if not assignments:
        return None
    first = assignments[0]
    if any(a != first for a in assignments[1:]):
        return None  # orientation กำกวมและให้คำตอบต่างกัน — ไม่เดา
    return [pool[i] for i in good_order]


# ── geometric beam matcher (คาน — ไม่ผ่าน eyeball) ─────────────────────────
# เหตุผล: กล่อง column ของ CV นั่งอยู่บนเส้นกริดพอดี → ใช้ pixel ของมันคำนวณ
# "กริด(เมตร) → พิกเซล" ได้ตรง ๆ (fit เชิงเส้นจาก grid ชื่อจริงเท่านั้น ไม่ใช้ dummy)
# แล้วจับคู่กล่องคาน (beam_h/beam_v) ด้วยระยะพิกเซลจริง — ไม่ใช่การเดา ไม่ใช่ eyeball
def cluster1d(vals, tol=25):
    vs = sorted(vals)
    out = []
    for v in vs:
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(c) / len(c) for c in out]


def _lstsq_fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None, None
    b = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / den
    a = my - b * mx
    resid = max(abs(ys[i] - (a + b * xs[i])) for i in range(n))
    return (a, b), resid


def fit_axis(named_ids_sorted, pos_of, px_clusters_sorted, max_resid=40):
    """fit เชิงเส้น เมตร→พิกเซล จากเสาที่มีชื่อ (ชื่อกริดจริง ไม่ใช่ dummy) — เผื่อบางชั้น/บ้าน
    เสาบางต้นไม่โดน CV เจอ หรือมีจุดตรวจจับเกิน (จริงจากภาพ): ลองทุก subsequence ที่ยาวเท่ากับ
    ค่าน้อยกว่า เลือกอันที่ fit ตรงที่สุด รับเฉพาะเมื่อ residual ต่ำพอ (ไม่งั้นคือ combo ผิด)"""
    n_named, n_px = len(named_ids_sorted), len(px_clusters_sorted)
    if n_named < 2 or n_px < 2:
        return None
    if abs(n_named - n_px) > 3:
        return None  # ต่างกันเยอะเกิน — ไม่ใช่แค่จุดหาย/เกินไม่กี่จุด อย่าเดา
    if n_named == n_px:
        combos_named = [named_ids_sorted]
        combos_px = [px_clusters_sorted]
    elif n_named > n_px:
        combos_named = [list(c) for c in combinations(named_ids_sorted, n_px)]
        combos_px = [px_clusters_sorted]
    else:
        combos_named = [named_ids_sorted]
        combos_px = [list(c) for c in combinations(px_clusters_sorted, n_named)]
    best, best_resid = None, max_resid
    for nm in combos_named:
        for px in combos_px:
            fit, resid = _lstsq_fit([pos_of[i] for i in nm], px)
            if fit is not None and resid < best_resid:
                best, best_resid = fit, resid
    return best


def load_gridmaster_typed(gt_dir, d):
    src = d.get("grid_source") or ""
    cand = None
    for fp in gt_dir.glob("*gridline*.json"):
        if src and Path(src).name == fp.name:
            cand = fp
            break
        if cand is None:
            cand = fp
    if cand is None:
        return None
    try:
        g = json.loads(cand.read_text(encoding="utf-8")).get("grid") or {}
    except json.JSONDecodeError:
        return None
    out = {}
    for axis, key in (("x", "x_lines"), ("y", "y_lines")):
        pos, named = {}, []
        for ln in g.get(key) or []:
            i, p = str(ln.get("id")).strip(), ln.get("pos_m")
            if p is None:
                continue
            pos[i] = float(p)
            if ln.get("type") == "named":
                named.append(i)
        out[axis] = {"pos": pos, "named": sorted(named, key=lambda i: pos[i])}
    return out


def parse_ref_axes(ref, y_ids, x_ids):
    ref = str(ref).strip()
    for yid in sorted(y_ids, key=len, reverse=True):
        if ref.startswith(yid) and ref[len(yid):] in x_ids:
            return yid, ref[len(yid):]
    for xid in sorted(x_ids, key=len, reverse=True):
        if xid and ref.endswith(xid) and ref[:-len(xid)] in y_ids:
            return ref[:-len(xid)], xid
    return None


def geo_match_beams(boxes, pool, gm):
    """boxes: กล่อง CV class beam_h/beam_v (cx,cy,n) · pool: GT beam element (grid_ref_start/end)
    คืน (matched_pairs [(box,gt)], leftover_gt [gt ไม่มีกล่อง]) หรือ None ถ้า fit ไม่ได้ (bail → eyeball)"""
    if gm is None:
        return None
    y_ids, x_ids = set(gm["y"]["pos"]), set(gm["x"]["pos"])
    parsed = []
    for e in pool:
        r = parse_ref_axes(e.get("grid_ref_start"), y_ids, x_ids)
        r2 = parse_ref_axes(e.get("grid_ref_end"), y_ids, x_ids)
        if r is None or r2 is None:
            return None
        parsed.append((e, r, r2))

    col_boxes = [b for b in boxes if b["class"] == "column"]
    if len(col_boxes) < 2:
        return None
    xcl = cluster1d([b["cx"] for b in col_boxes])
    ycl = cluster1d([b["cy"] for b in col_boxes])
    fx = fit_axis(gm["x"]["named"], gm["x"]["pos"], xcl)
    fy = fit_axis(gm["y"]["named"], gm["y"]["pos"], ycl)
    if fx is None or fy is None:
        return None
    px_of_x = lambda i: fx[0] + fx[1] * gm["x"]["pos"][i]
    px_of_y = lambda i: fy[0] + fy[1] * gm["y"]["pos"][i]

    TOL = 60
    beam_h_boxes = sorted([b for b in boxes if b["class"] == "beam_h"], key=lambda b: b["cy"])
    beam_v_boxes = [b for b in boxes if b["class"] == "beam_v"]

    matched, leftover = [], []
    # แนวนอน: กลุ่มตามแถว (row_id เดียวกันทั้งสองปลาย) → กล่องเดียวคุมทั้งแถว (กล่อง CV กว้างครอบ
    # ทั้งแถว — ยืนยันจาก width จริงที่ตรงกับ span เต็มแถว ไม่ใช่การเดา)
    rows = defaultdict(list)
    for e, r, r2 in parsed:
        if r[0] != r2[0]:
            continue  # ไม่ใช่แนวนอนแท้ (แถวต่างกัน) — ข้าม ไปจับที่แนวตั้ง
        rows[r[0]].append(e)
    used_h = set()
    for row_id, els in rows.items():
        exp_cy = px_of_y(row_id)
        best, bd = None, TOL
        for b in beam_h_boxes:
            if id(b) in used_h:
                continue
            d = abs(b["cy"] - exp_cy)
            if d < bd:
                best, bd = b, d
        if best is None:
            leftover += els
            continue
        used_h.add(id(best))
        for e in els:
            matched.append((best, e))

    # แนวตั้ง: จับคู่ 1-1 ตามระยะพิกเซลจริง (ใกล้สุดที่ยังไม่มีเจ้าของ)
    verts = []
    for e, r, r2 in parsed:
        if r[1] != r2[1]:
            continue  # ไม่ใช่แนวตั้งแท้ (คอลัมน์ต่างกัน)
        if r[0] == r2[0]:
            continue  # เคยนับเป็นแนวนอนไปแล้ว
        exp_cx = px_of_x(r[1])
        exp_cy = (px_of_y(r[0]) + px_of_y(r2[0])) / 2
        verts.append((e, exp_cx, exp_cy))
    used_v = set()
    for e, ecx, ecy in verts:
        best, bd = None, None
        for b in beam_v_boxes:
            if id(b) in used_v:
                continue
            d = ((b["cx"] - ecx) ** 2 + (b["cy"] - ecy) ** 2) ** 0.5
            if bd is None or d < bd:
                best, bd = b, d
        if best is not None and bd <= 90:
            used_v.add(id(best))
            matched.append((best, e))
        else:
            leftover.append(e)

    if len(matched) + len(leftover) != len(pool):
        return None  # element ที่ parse ไม่ผ่านทั้งแนวนอน/แนวตั้ง — bail อย่าเดา
    return matched, leftover


def elements_flat(d):
    els = list(d.get("elements") or [])
    for v in d.get("views") or []:
        if isinstance(v, dict):
            els += list(v.get("elements") or [])
    return [e for e in els if isinstance(e, dict)]


def build_pass3():
    p3 = prompt_pass3()
    gt_dirs = {bare(p.name): p for p in GT_ROOT.iterdir()
               if p.is_dir() and re.match(r"^\d{2}บ้าน", p.name)}
    # index GT plan files ต่อ (บ้าน, หน้า)
    gt_by_page = defaultdict(list)
    for h in TRAIN_HOUSES_10 + VAL_HOUSES:
        for fp in sorted(gt_dirs[h].glob("*.json")):
            if fp.name.startswith("_"):
                continue
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if d.get("pattern") in PLAN_PATTERNS and d.get("discipline") == "structural":
                pk = page_of_image(fp.name)
                if pk:
                    gt_by_page[(h, pk)].append((fp.name, d))

    # pairing จาก eyeball ของ Claude (พิสูจน์ด้วยตาจริงทีละหน้า cross-check กับ GT):
    # {"house","page","class","pairs":{"<n>":{"element_id","grid_refs"}}, "cv_fp":[n,...]}
    eyeball_pairs = {}
    ep = HERE / "pass3_pairs_eyeball.jsonl"
    if ep.exists():
        for r in read_jsonl(ep):
            eyeball_pairs[(r["house"], r["page"], r["class"])] = r

    train, val, eyeball = [], [], []
    for (h, pk), items in sorted(gt_by_page.items()):
        img = IMG_ROOT / h / f"{h}_หน้า{pk}.png"
        cv_p = img.with_name(img.stem + "_cv25.json")
        marked = img.with_name(img.stem + "_marked25.png")
        if not (cv_p.exists() and marked.exists()):
            continue  # CV ไม่มี — หน้าอยู่นอก batch (ไม่ใช่คิว)
        if len(items) > 1:
            eyeball.append((h, pk, "multi_view_gt"))
            continue
        fn, d = items[0]
        cv = json.loads(cv_p.read_text(encoding="utf-8"))
        boxes = cv.get("elements") or []
        gt_els = elements_flat(d)

        # จัดกลุ่ม + กรอง class ที่ "ไม่เกี่ยวกับหน้านี้" ออกจากบัญชี (เช่น CV เห็นสัญลักษณ์เสา
        # บนแปลนคาน — เสาพิมพ์อยู่จริงที่จุดตัดกริด แต่ GT หน้าคานบันทึกเฉพาะคาน ไม่ใช่ CV ผิด)
        # กล่องที่ถูกกรองจะไม่อยู่ทั้งในบัญชีและใน "รูปมาร์คใหม่" ที่วาดเอง — เลขบนภาพตรงบัญชีเป๊ะ
        by_class = defaultdict(list)
        for b in boxes:
            by_class[b.get("class")].append(b)
        # รวม beam_h+beam_v เป็น pool เดียว
        if "beam_v" in by_class or "beam_h" in by_class:
            by_class["beam_h"] = by_class.pop("beam_h", []) + by_class.pop("beam_v", [])
        matched_pairs = []   # (box, gt_instance)
        kept_boxes = []
        matched_types = set()
        leftover_instances = []   # instance ที่ CV พลาด (จาก eyeball) — เข้า label ไม่มี cv_mark
        ok = True
        reasons = []
        gridpos = None
        gridpos_typed = None
        for cls, bs in by_class.items():
            gt_types = CV_TO_GT_TYPES.get(cls) or (CV_TO_GT_TYPES["beam_h"] if cls == "beam_h" else None)
            if not gt_types:
                continue  # class แปลก — ทิ้งจากบัญชี
            pool = [e for e in gt_els if e.get("element_type") in gt_types]
            if not pool:
                continue  # หน้านี้ไม่มีชนิดนี้ใน GT → class ไม่เกี่ยว กรองออก
            bs_sorted = sorted(bs, key=lambda x: x["n"])

            # (ค4) คาน: จับคู่เชิงเรขาคณิตจริง — ใช้ pixel ของกล่องเสา (นั่งบนเส้นกริดพอดี) fit
            # เมตร→พิกเซล แล้วจับคู่กล่องคาน ไม่ต้อง eyeball ต่อหน้า (พิสูจน์แม่นบนหน้า31 ก่อนใช้จริง)
            if cls == "beam_h":
                if gridpos_typed is None:
                    gridpos_typed = load_gridmaster_typed(gt_dirs[h], d)
                geo = geo_match_beams(boxes, pool, gridpos_typed)
                if geo is not None:
                    pairing, leftover = geo
                    matched_pairs += pairing
                    kept_boxes += [b for b, _e in pairing]
                    matched_types |= gt_types
                    leftover_instances += leftover
                    continue

            pool2 = expand_pool(pool)

            # (ค3) eyeball pairing จากไฟล์ — ทางหลักของคืนนี้ (validate กับ GT ก่อนเชื่อเสมอ)
            key = (h, pk, "beam_h" if cls in ("beam_h", "beam_v") else cls)
            eb = eyeball_pairs.get(key)
            if eb is not None:
                pairs, fps = eb.get("pairs") or {}, set(eb.get("cv_fp") or [])
                avail = list(pool2 if pool2 is not None else pool)
                pairing, bad = [], None
                for b in bs_sorted:
                    if b["n"] in fps:
                        continue
                    spec = pairs.get(str(b["n"]))
                    if spec is None:
                        bad = f"eyeball_missing_n:{b['n']}"
                        break
                    hit = next((e for e in avail
                                if e.get("element_id") == spec["element_id"]
                                and (e.get("grid_refs") or []) == spec.get("grid_refs")), None)
                    if hit is None:
                        bad = f"eyeball_pair_not_in_gt:n{b['n']}:{spec['element_id']}"
                        break
                    avail.remove(hit)
                    pairing.append((b, hit))
                if bad:
                    ok, _ = False, reasons.append(bad)
                    break
                # instance ที่ CV พลาด (avail เหลือ) จะเข้า label แบบไม่มี cv_mark ผ่าน
                # เส้นทาง unmatched ด้านล่าง — สอนกฎ "เพิ่ม element ที่บัญชีพลาดได้" ด้วยของจริง
                matched_pairs += pairing
                kept_boxes += [b for b, _e in pairing]
                matched_types |= gt_types
                for e in avail:
                    leftover_instances.append(e)
                continue

            # column บนแปลนคาน = สัญลักษณ์รอง (CV เห็นทุกจุดตัดกริด, GT บันทึกเฉพาะบางต้น) —
            # จับคู่ไม่ได้ไม่ถือว่าหน้าพัง แค่ข้าม class นี้ไปเงียบ ๆ (element จริงยังอยู่ใน label
            # ผ่านทาง matched_types ที่ไม่ครอบคลุม → ตกไปที่ก้อน "ชนิดอื่นคงเดิม" ท้ายฟังก์ชัน)
            secondary_column = cls == "column" and "beam_h" in by_class
            if pool2 is None:
                if secondary_column:
                    continue
                ok, _ = False, reasons.append(f"aggregated_refs_mismatch:{cls}")
                break
            if len(bs) != len(pool2):
                if secondary_column:
                    continue
                ok, _ = False, reasons.append(f"count_mismatch:{cls} cv={len(bs)} gt={len(pool2)}")
                break
            ids = {e.get("element_id") for e in pool2}
            refsets = {tuple(e.get("grid_refs") or []) for e in pool2}
            if len(ids) == 1 and len(refsets) == 1:
                pairing = list(zip(bs_sorted, pool2))       # (ค1) เนื้อหาเหมือนกันหมด ลำดับไหนก็ถูก
            else:
                if gridpos is None:
                    gridpos = load_gridmaster(gt_dirs[h], d)
                ordered = spatial_match(bs_sorted, pool2, gridpos) if gridpos else None
                if ordered is None:
                    if secondary_column:
                        continue
                    ok, _ = False, reasons.append(f"spatial_unprovable:{cls}")
                    break
                pairing = list(zip(bs_sorted, ordered))     # (ค2) พิสูจน์ผ่าน orientation แล้ว
            matched_pairs += pairing
            kept_boxes += bs_sorted
            matched_types |= gt_types
        if not ok:
            eyeball.append((h, pk, ";".join(reasons)))
            continue
        if not matched_pairs:
            eyeball.append((h, pk, "no_relevant_boxes"))
            continue

        # ประกอบ label ระดับ instance: element ที่จับคู่ = instance + cv_mark ·
        # element ชนิดอื่น (เช่น slab บนหน้าคาน) คงไว้ตามเดิมไม่มี cv_mark
        label = {k: v for k, v in d.items() if k not in ("elements", "views")}
        new_els = []
        for b, e in sorted(matched_pairs, key=lambda p: p[0]["n"]):
            inst = json.loads(json.dumps(e, ensure_ascii=False))
            inst["cv_mark"] = b["n"]
            new_els.append(inst)
        for e in leftover_instances:   # CV พลาด — อยู่ใน label โดยไม่มี cv_mark (กฎ "เพิ่มได้")
            new_els.append(json.loads(json.dumps(e, ensure_ascii=False)))
        for e in gt_els:
            if e.get("element_type") not in matched_types:
                new_els.append(json.loads(json.dumps(e, ensure_ascii=False)))
        label["elements"] = new_els

        # วาดรูปมาร์คใหม่ "เฉพาะกล่องในบัญชี" — เลขบนภาพต้องตรงบัญชีเป๊ะ (รูป _marked25 เดิม
        # มีกล่อง class ที่ถูกกรองออกด้วย ใช้ไม่ได้ จะสับสน) เลข n คงเดิมจาก _cv25.json
        out_img = MARKED_DIR / f"{img.stem}_markedT5.png"
        render_marked(img, kept_boxes, out_img)

        account = "\n".join(f"{b['n']}) {b['class'].replace('beam_v', 'beam_h')}"
                            for b in sorted(kept_boxes, key=lambda x: x["n"]))
        ptext = p3.replace("{{ELEMENT_ACCOUNT}}", account)
        row = {
            "id": f"{gt_dirs[h].name}::{Path(fn).stem}::pass3",
            "house": gt_dirs[h].name, "subtask": "pass3",
            "messages": [
                {"role": "user", "content": [
                    {"type": "image", "image": str(out_img.relative_to(TRAINING)).replace("\\", "/")},
                    {"type": "text", "text": ptext},
                ]},
                {"role": "assistant", "content": json.dumps(label, ensure_ascii=False)},
            ],
        }
        (val if h in VAL_HOUSES else train).append(row)

    write_jsonl(HERE / "pass3_train.jsonl", train)
    write_jsonl(HERE / "pass3_val.jsonl", val)
    return len(train), len(val), eyeball


def main():
    t0, v0, q0 = build_pass0()
    print(f"pass0:  train {t0} / val {v0}  (5 หลัง) | คิว label มือในบ้านชุดนี้: {len(q0)} หน้า")
    t24, v24, nh = build_pass24()
    print(f"pass2.4: train {t24} / val {v24} (10 หลัง) | หน้าที่ไม่มี hint: {len(nh)}")
    t3, v3, eye = build_pass3()
    print(f"pass3:  train {t3} / val {v3}  (10 หลัง, auto-match เข้มเท่านั้น)")
    print(f"        คิว eyeball พรุ่งนี้: {len(eye)} หน้า")
    for h, pk, why in eye:
        print(f"          - {h} หน้า{pk}: {why}")
    if q0:
        print("pass0 คิว label มือ:")
        for r in q0[:20]:
            print(f"          - {bare(r['house'])} หน้า{r['page']}: {r['reason']}")


if __name__ == "__main__":
    main()
