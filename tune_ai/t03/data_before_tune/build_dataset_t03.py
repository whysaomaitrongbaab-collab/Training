#!/usr/bin/env python3
"""build_dataset_t03.py — สร้าง train.jsonl/val.jsonl สำหรับรอบ t03 (per-subtask multi-pass)
จาก ground truth ที่คนรีวิว/normalize แล้วใน json_แก้ไขแล้ว/ ทั้ง 11 หลัง

ต่างจาก t01/t02 (single-shot อ่านทั้งหน้า): หนึ่งตัวอย่าง = (ภาพหน้า, prompt เฉพาะ subtask,
GT ที่กรองเหลือเฉพาะ element ของ subtask นั้น) — หน้าเดียวกันจึงออกได้หลายตัวอย่างต่างเป้า
ตาม design ใน ../pass_design.csv + ../README.md

การตัดสินใจที่ฝังในไฟล์นี้ (2026-08-24, Claude ภายใต้ att1235 — ทบทวนได้ก่อนเทรนจริง):
 - plan_column ยุบ: ไม่มี subtask แยก (มีหน้าแปลนเสาเดี่ยวๆ แค่ 2 ไฟล์ใน 11 หลัง — dataset_sizing.md)
   เสาเข้าชุดผ่าน plan_footing (ตาราง plan.md เดิมก็รวม column อยู่แล้ว) — หน้า column+beam plan
   จะออก 2 ตัวอย่าง (plan_footing เป้าเสา + plan_beam เป้าคาน)
 - plan_* จำกัด discipline=structural (แปลนสถาปัตย์/ไฟฟ้า/สุขาภิบาลเป็น pass3 ไม่เข้ารอบนี้)
   section/schedule/notes เอาทุก discipline (pattern-based ตาม pass_design.csv — door/window
   schedule คือหน้าที่ t02 ทำได้ดีสุด 86% อยู่ใน schedule/architectural)
 - material_list ตัดทิ้งทั้งหมด (op04 ruling: 37% ของงาน annotate, elements=0 เสมอ)
 - soil_boring_log: ไม่มีไฟล์จริงใน 11 หลัง (นับแล้ว 0) — subtask ว่าง บันทึกไว้
 - gridline: ตัวอย่าง multi-image จาก source_pages[] ของ gridmaster (ตามที่ pass_design.csv
   สมมติ — open question ใน README ยังไม่ปิด แต่ dataset เตรียมตามสมมตินั้น)
 - val split = บ้าน 03 (บ้าน_เล็ก_2ชั้น_01) ตาม precedent t01/t02
 - prompt = _common.md BLOCK + prompt ของ subtask (แทน {{TARGET}}/{{ELEMENT_TYPES}}) —
   ไฟล์ prompt พวกนี้ยังไม่เคยถูกรันจริงกับโมเดลเลย (บันทึกใน t03/README.md)

รัน:  python build_dataset_t03.py            (เขียน train.jsonl, val.jsonl, stats.json,
                                              images_manifest.txt และ copy ภาพเข้า images/)
"""
import json
import glob
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
T03 = HERE.parent
TRAINING = T03.parent.parent           # .../Training
GT_ROOT = TRAINING / "json_แก้ไขแล้ว"


def strip_assigned(obj):
    """ตัด element_name_assigned ออกจาก training target (2026-08-25, มะขามอนุมัติ att1235)

    convention ใหม่ของ section: element ที่ไม่มี mark พิมพ์บนแบบ → element_id: null และชื่อที่
    คนจดตั้งเอง (gate_front ฯลฯ) ย้ายไป element_name_assigned ซึ่งเป็น metadata สำหรับมนุษย์ —
    **ห้ามรั่วเข้า target** ไม่งั้นโมเดลถูกสอนให้เดาชื่อที่ไม่มีบนกระดาษ (ปัญหาเดิม 66% ของ
    ตัวอย่าง section) ตัดแบบ deep เพราะ element อยู่ได้ทั้ง elements[] และ views[].elements[]
    """
    if isinstance(obj, dict):
        return {k: strip_assigned(v) for k, v in obj.items() if k != "element_name_assigned"}
    if isinstance(obj, list):
        return [strip_assigned(x) for x in obj]
    return obj

IMG_ROOT = TRAINING / "image"
OUT_IMAGES = HERE / "images"

# val = 2 หลัง (มะขามสั่ง 2026-08-24: 10:1 แย่เกินไป เอา ~4:1)
# เลือก 02+03 จาก 5 หลังที่รีวิวเนื้อหาแล้ว (val ต้องเป็น GT สะอาดเท่านั้น):
#   - ครอบคลุมทั้ง 1 ชั้น (02) และ 2 ชั้น (03) — คู่ 03+04/03+05 เป็น 2 ชั้นล้วน
#     จะวัดบ้านชั้นเดียวไม่ได้เลยทั้งที่เป็น 7 ใน 11 หลังของชุดข้อมูล
#   - เสีย train น้อยสุด (35 ตัวอย่าง) — 04/05 เป็นบ้าน section เยอะ (36-37) เสีย 60
#   - ผล: train 373 / val 79 = 4.7:1 (val 17.5%) · plan_beam val 4→7 · gridline val 1→2
VAL_HOUSES = {
    "01บ้าน_เล็ก_1ชั้น_01", "02บ้าน_เล็ก_1ชั้น_02", "03บ้าน_เล็ก_2ชั้น_01",
    "04บ้าน_เล็ก_2ชั้น_02", "05บ้าน_เล็ก_2ชั้น_03",
}

# บ้านทดสอบ — **อยู่นอก dataset ทั้ง train และ val** (มะขามสั่ง 2026-08-24 ดึก:
# "เอาบ้าน 08 ออกจาก dataset") เขียนออกเป็น test.jsonl ต่างหาก
# ทำไมต้องอยู่นอกทั้งคู่: บ้าน 08 คือ benchmark ข้ามรอบ — t02 มีผลของบ้านนี้อยู่แล้ว
# (`tune_ai/t02/ผล/08.../` 25 หน้า, id-recall 3.5%, plan_beam 0%) และ **t02 ไม่เคยเทรนบ้าน 08**
# ถ้า t03 เทรนมัน ตัวเลขจะสูงเพราะจำได้ ไม่ใช่เพราะอ่านเป็น → เทียบกันไม่ได้เลย
# อยู่ใน val ก็ยังสื่อผิด (val = ไม้บรรทัดคุณภาพ GT ซึ่งบ้าน 08 ยังไม่ผ่านรีวิวเนื้อหา)
# แยกเป็น test จึงตรงความจริงที่สุด: train / val (01-05 รีวิวแล้ว) / test (08 benchmark)
# บ้าน 32 อยู่ใน train ตามปกติอยู่แล้ว (ไม่เคยถูกกันออก)
TEST_HOUSES = {"08บ้าน_เล็ก_1ชั้น_03"}
# แก้ 2026-08-24 ค่ำ รอบ 2 — หลัง op04 ส่ง 39 หลังใหม่เข้ามา (452 → 1,116 ตัวอย่าง)
# val = บ้าน 01-05 ทั้งหมด = "ทุกหลังที่คนรีวิวเนื้อหากับภาพต้นฉบับแล้ว" (229 ตัวอย่าง)
#   → train 887 / val 229 = 3.9:1 ตรงเป้า 4:1 ที่มะขามสั่ง
#   → ผลพลอยได้ที่สำคัญกว่าอัตราส่วน: val = GT รีวิวแล้ว 100% / train = op04 ล้วน
#     ไม้บรรทัดจึงสะอาดทั้งอัน ไม่มีข้อมูลที่ยังไม่ตรวจปนในตัววัด
#   → plan_beam val 4 → 18 (subtask คอขวด วัดได้จริงเป็นครั้งแรก)
# ข้อจำกัดที่ยอมรับ: val ไม่มีบ้าน 3 ชั้น/บ้านใหญ่เลย (อยู่ในกลุ่ม op04 ที่ยังไม่รีวิว)
# และ train เสียบ้านคุณภาพสูงสุด 5 หลังไป — ยอมแลกเพื่อให้ตัววัดเชื่อถือได้

# ---- subtask definitions -------------------------------------------------
PLAN_SUBTASKS = {
    "plan_footing": {
        "target": "footings (ฐานราก) and the columns marked with them",
        "types": {"footing", "pile", "pile_cap", "pedestal", "column"},
    },
    "plan_beam": {
        "target": ("beams at every level, ground beams (คานคอดิน), floor beams, ring beams "
                   "(คานอะเส), roof framing (โครงหลังคา)"),
        "types": {"beam", "tie_beam", "steel_member"},
        # โครงหลังคาใช้ชื่อแต่งหลากหลาย (rafter/hip_rafter/steel_rafter/steel_ridge/purlin/...)
        "type_regex": r"(rafter|purlin|ridge|hip|valley|truss)",
    },
    "plan_slab": {
        "target": "floor slabs and precast plank fields",
        "types": {"slab", "precast_plank_detail", "precast_plank_placement_detail"},
    },
}

def load_prompt_block():
    """คืน (block ที่เจาะช่อง {{GLOSSARY}} ไว้, ตัว glossary)

    glossary ไทย→field (DIP — แทรกศัพท์ ไม่แปลทั้ง prompt) คั่นด้วย HTML comment ใน
    _common.md เพื่อให้ตัดออกราย subtask ได้: gridline หาแต่เส้นกริด ไม่แตะตาราง
    element_type/เหล็กเลย และเป็น subtask ที่ seq ยาวสุด "ทุกตัว" (~45.6k) — ใส่ไปก็
    เปลืองเปล่าแล้วดัน MAX_LENGTH ทะลุ 47,104 (= ต้องขยับ VRAM ตาม)
    """
    txt = (T03 / "_common.md").read_text(encoding="utf-8")
    m = re.search(r"## BLOCK START\n(.*?)\n## BLOCK END", txt, re.DOTALL)
    body = m.group(1).strip()
    g = re.search(r"<!-- GLOSSARY START -->\n(.*?)\n<!-- GLOSSARY END -->\n", body, re.DOTALL)
    assert g, "_common.md ไม่มี marker GLOSSARY START/END"
    return body.replace(g.group(0), "{{GLOSSARY}}"), g.group(1).strip()

def load_subtask_prompt(name):
    txt = (T03 / "pass2_used" / f"{name}.md").read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)(?:\n## PROMPT END|\Z)", txt, re.DOTALL)
    return m.group(1).strip()

COMMON, GLOSSARY = load_prompt_block()
PROMPTS = {n: load_subtask_prompt(n) for n in
           ("gridline", "plan", "section", "schedule", "notes")}

def prompt_for(subtask):
    if subtask.startswith("plan_"):
        cfg = PLAN_SUBTASKS[subtask]
        body = (PROMPTS["plan"]
                .replace("{{TARGET}}", cfg["target"])
                .replace("{{ELEMENT_TYPES}}", ", ".join(sorted(cfg["types"]))))
    else:
        body = PROMPTS[subtask]
    gloss = "" if subtask == "gridline" else GLOSSARY
    return COMMON.replace("{{GLOSSARY}}", gloss) + "\n\n" + body

# ---- element filtering ---------------------------------------------------
def type_matches(t, cfg):
    if not isinstance(t, str):
        return False
    if t in cfg["types"]:
        return True
    rx = cfg.get("type_regex")
    return bool(rx and re.search(rx, t))

def filter_elements(elements, cfg):
    out = []
    for e in elements or []:
        if not isinstance(e, dict):
            continue
        if type_matches(e.get("element_type"), cfg):
            out.append(e)
    return out

def gt_for_plan_subtask(d, cfg):
    """GT = wrapper + elements filtered to this subtask's types (views preserved)."""
    g = {k: v for k, v in d.items() if k not in ("views", "elements")}
    n = 0
    if isinstance(d.get("views"), list):
        vs = []
        for view in d["views"]:
            if not isinstance(view, dict):
                continue
            v2 = {k: v for k, v in view.items() if k != "elements"}
            fe = filter_elements(view.get("elements"), cfg)
            v2["elements"] = fe
            n += len(fe)
            vs.append(v2)
        g["views"] = vs
    else:
        fe = filter_elements(d.get("elements"), cfg)
        g["elements"] = fe
        n = len(fe)
    return g, n

# ---- image resolution ----------------------------------------------------
def find_image(house_dir, d, fname):
    """resolve the page image for a GT file"""
    src = d.get("source_image")
    cands = []
    if isinstance(src, str):
        cands.append(TRAINING / src)
        cands.append(IMG_ROOT / Path(src).name)
    m = re.match(r"(.+?_หน้า\d+)", Path(fname).stem)
    if m:
        img_house = house_dir[2:]  # strip 2-digit prefix -> image folder name
        cands.append(IMG_ROOT / img_house / f"{m.group(1)}.png")
    for c in cands:
        if c.exists():
            return c
    return None

# ---- build ---------------------------------------------------------------
def main():
    OUT_IMAGES.mkdir(exist_ok=True)
    rows_train, rows_val, rows_test = [], [], []
    broken_files = []
    stats = Counter()
    per_subtask = Counter()
    skipped = defaultdict(list)
    needed_images = set()

    houses = sorted(d.name for d in GT_ROOT.iterdir() if d.is_dir())
    for house in houses:
        gridmaster = None
        gm_file = sorted((GT_ROOT / house).glob("*หน้า00_gridline.json"))
        if gm_file:
            gridmaster = json.loads(gm_file[0].read_text(encoding="utf-8"))

        for fp in sorted((GT_ROOT / house).glob("*.json")):
            if "_stage0_manifest" in fp.name or fp.name == "_scope.json":
                continue
            # op04 batch (2026-08-23) มี agent โดน API session-limit ตัดกลางเขียนไฟล์ →
            # ไฟล์ truncated. ข้ามพร้อมรายงานชื่อ ห้ามเดาค่าที่ขาดหาย (= ปลอม GT)
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                broken_files.append(f"{fp.relative_to(GT_ROOT)} — {e}")
                continue
            pat = d.get("pattern")
            disc = d.get("discipline")

            examples = []  # (subtask, gt_dict, images[list of Path], extra_text)

            if pat in ("grid_master", "gridline"):
                srcs = d.get("source_pages") or []
                imgs = [TRAINING / s for s in srcs if (TRAINING / s).exists()]
                if not imgs:
                    skipped["gridline_no_source_images"].append(f"{house}/{fp.name}")
                    continue
                if len(imgs) > 4:
                    imgs = imgs[:4]  # เพดานเดียวกับ t01 gridmaster examples
                examples.append(("gridline", d, imgs, None))

            elif pat in ("beam_plan", "footing_plan", "roof_frame_plan", "etc_plan", "plan") and disc == "structural":
                img = find_image(house, d, fp.name)
                if not img:
                    skipped["no_image"].append(f"{house}/{fp.name}")
                    continue
                gm_text = None
                if gridmaster and isinstance(gridmaster.get("grid"), dict):
                    slim = {"grid": {k: gridmaster["grid"].get(k)
                                     for k in ("x_lines", "y_lines") if k in gridmaster["grid"]}}
                    gm_text = ("\n\nGRID MASTER (resolved axes for this building)\n"
                               + json.dumps(slim, ensure_ascii=False))
                for sub, cfg in PLAN_SUBTASKS.items():
                    gt, n = gt_for_plan_subtask(d, cfg)
                    if n == 0:
                        continue
                    examples.append((sub, gt, [img], gm_text))
                if not examples:
                    skipped["plan_no_matching_elements"].append(f"{house}/{fp.name}")
                    continue

            elif pat in ("section", "schedule", "notes"):
                img = find_image(house, d, fp.name)
                if not img:
                    skipped["no_image"].append(f"{house}/{fp.name}")
                    continue
                examples.append((pat, d, [img], None))

            elif pat == "material_list":
                stats["excluded_material_list"] += 1
                continue
            else:
                stats["excluded_pass3_or_other"] += 1
                continue

            for sub, gt, imgs, extra in examples:
                content = []
                for img in imgs:
                    needed_images.add(img)
                    content.append({"type": "image", "image": f"images/{img.name}"})
                ptext = prompt_for(sub)
                if extra:
                    ptext += extra
                content.append({"type": "text", "text": ptext})
                row = {
                    "id": f"{house}::{fp.stem}::{sub}",
                    "house": house,
                    "subtask": sub,
                    "messages": [
                        {"role": "user", "content": content},
                        {"role": "assistant",
                         "content": [{"type": "text",
                                      "text": json.dumps(strip_assigned(gt),
                                                         ensure_ascii=False)}]},
                    ],
                }
                (rows_test if house in TEST_HOUSES
                 else rows_val if house in VAL_HOUSES else rows_train).append(row)
                per_subtask[sub] += 1
                stats["examples"] += 1

    # copy images (flat, filenames unique — house name is in the filename)
    for img in sorted(needed_images):
        dst = OUT_IMAGES / img.name
        if not dst.exists():
            shutil.copy2(img, dst)

    with open(HERE / "train.jsonl", "w", encoding="utf-8") as f:
        for r in rows_train:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(HERE / "val.jsonl", "w", encoding="utf-8") as f:
        for r in rows_val:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(HERE / "test.jsonl", "w", encoding="utf-8") as f:
        for r in rows_test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(HERE / "images_manifest.txt", "w", encoding="utf-8") as f:
        for img in sorted(needed_images):
            f.write(str(img.relative_to(TRAINING)) + "\n")

    summary = {
        "built": "2026-08-24",
        "train_examples": len(rows_train),
        "val_examples": len(rows_val),
        "test_examples": len(rows_test),
        "val_houses": sorted(VAL_HOUSES),
        "test_houses": sorted(TEST_HOUSES),
        "per_subtask": dict(per_subtask),
        "images": len(needed_images),
        "stats": dict(stats),
        "skipped": {k: len(v) for k, v in skipped.items()},
        "skipped_detail": {k: v[:20] for k, v in skipped.items()},
    }
    (HERE / "stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    sys.exit(main())
