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
# 2026-08-29 late: this whole file moved tune_ai/t03/data_before_tune -> t04_Purson/data_before_tune
# (มะขามสั่ง "เลิกอ่าน t03 เราไม่ใช้แล้ว") - t03 is legacy/reference only now, t04_Purson is home.
T04 = HERE.parent
TRAINING = T04.parent.parent           # .../Training
# every pass-2 subtask prompt (gridline/section/schedule/notes/plan_*) lives under
# T04_PASS2/<subtask>/prompt_<subtask>.md as of 2026-08-29 (see load_subtask_prompt)
T04_PASS2 = T04 / "pass2"
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

# บ้านทดสอบ — เคยกันบ้าน 08 ไว้นอก train/val ทั้งคู่ (มะขามสั่ง 2026-08-24 ดึก:
# "เอาบ้าน 08 ออกจาก dataset") เพราะเป็น cross-round benchmark กับ t02 (t02 ไม่เคยเทรนบ้านนี้
# — ถ้า t03/t04 เทรนมัน ตัวเลขจะสูงเพราะจำได้ ไม่ใช่เพราะอ่านเป็น เทียบข้ามรอบไม่ได้อีก)
# **กลับคำ 2026-08-29 ค่ำ (มะขามสั่ง "เอาบ้าน 08 เข้ามาด้วย จะได้ครบ 40 หลัง")** —
# ยอมรับการเสีย cross-round benchmark กับ t02 อย่างเปิดเผย เพื่อให้ dataset สมบูรณ์ 40/40 หลัง
# TEST_HOUSES ว่างเปล่าถาวรจากนี้ (ไม่ลบ set/logic ทิ้ง เผื่อรอบหน้าอยากกันบ้านอื่นออกอีก)
TEST_HOUSES = set()
# แก้ 2026-08-24 ค่ำ รอบ 2 — หลัง op04 ส่ง 39 หลังใหม่เข้ามา (452 → 1,116 ตัวอย่าง)
# val = บ้าน 01-05 ทั้งหมด = "ทุกหลังที่คนรีวิวเนื้อหากับภาพต้นฉบับแล้ว" (229 ตัวอย่าง)
#   → train 887 / val 229 = 3.9:1 ตรงเป้า 4:1 ที่มะขามสั่ง
#   → ผลพลอยได้ที่สำคัญกว่าอัตราส่วน: val = GT รีวิวแล้ว 100% / train = op04 ล้วน
#     ไม้บรรทัดจึงสะอาดทั้งอัน ไม่มีข้อมูลที่ยังไม่ตรวจปนในตัววัด
#   → plan_beam val 4 → 18 (subtask คอขวด วัดได้จริงเป็นครั้งแรก)
# ข้อจำกัดที่ยอมรับ: val ไม่มีบ้าน 3 ชั้น/บ้านใหญ่เลย (อยู่ในกลุ่ม op04 ที่ยังไม่รีวิว)
# และ train เสียบ้านคุณภาพสูงสุด 5 หลังไป — ยอมแลกเพื่อให้ตัววัดเชื่อถือได้

# ---- subtask definitions -------------------------------------------------
# "target"/{{TARGET}} substitution retired 2026-08-29 - each plan subtask now has its own
# rendered prompt.md (see load_subtask_prompt); these dicts now only drive GT element filtering.
PLAN_SUBTASKS = {
    "plan_footing": {
        "types": {"footing", "pile", "pile_cap", "pedestal", "column"},
    },
    "plan_beam": {
        "types": {"beam", "tie_beam", "steel_member"},
        # โครงหลังคาใช้ชื่อแต่งหลากหลาย (rafter/hip_rafter/steel_rafter/steel_ridge/purlin/...)
        "type_regex": r"(rafter|purlin|ridge|hip|valley|truss)",
    },
    "plan_slab": {
        "types": {"slab", "precast_plank_detail", "precast_plank_placement_detail"},
    },
}

def load_prompt_block():
    """คืน block ของ _common.md (กฎร่วม - output shape, honesty rules) โดยตัด glossary
    ทิ้งเสมอ (ไม่มี {{GLOSSARY}} ให้เติมอีกต่อไป)

    2026-08-29 (มะขามสั่ง "ใส่ dictionary เข้าไปในทุก prompt ใน t04 เลย"): glossary ไทย→field
    ย้ายจาก "ก้อนเดียวใช้ร่วมกันทุก subtask" ไปเป็น "ฝังตรงในไฟล์ prompt ของแต่ละ subtask เอง
    ปรับให้ตรงกับงานจริงของ subtask นั้น" (เช่น plan family ตัดคำศัพท์เหล็กเสริมออกเพราะ pass
    นี้ไม่แตะสเปกเหล็ก, notes/material_list ได้แค่ศัพท์ที่ตรงกับสิ่งที่หน้านั้นสกัดจริง) —
    ทำที่ tune_ai/t04_Purson/pass2/<subtask>/prompt_<subtask>.md ทุกไฟล์แล้ว (plan family
    render มาจาก pass2/plan.md ซึ่งพก glossary ของตัวเองอยู่แล้ว re-render ใหม่ไม่หาย)
    ฟังก์ชันนี้จึงไม่ต้องเจาะช่อง {{GLOSSARY}} อีกต่อไป - เอา glossary block ออกจาก COMMON
    เฉยๆ กัน COMMON ลากตัวเปล่าติดมาซ้ำกับที่ฝังในแต่ละไฟล์แล้ว
    """
    txt = (T04 / "_common.md").read_text(encoding="utf-8")
    m = re.search(r"## BLOCK START\n(.*?)\n## BLOCK END", txt, re.DOTALL)
    body = m.group(1).strip()
    g = re.search(r"<!-- GLOSSARY START -->\n(.*?)\n<!-- GLOSSARY END -->\n", body, re.DOTALL)
    assert g, "_common.md ไม่มี marker GLOSSARY START/END"
    return body.replace(g.group(0), "").strip()

def load_subtask_prompt(name):
    # 2026-08-29: every pass-2 subtask now has its own concrete prompt.md folder under
    # T04_PASS2/<subtask>/ - the plan family (footing/beam/slab/column) used to share one
    # templated file (plan.md, {{TARGET}}/{{ELEMENT_TYPES}} substitution); it is now four
    # separate rendered files, same rendering plan.md itself still documents for re-rendering.
    # Each file also carries its own tailored Thai-glossary block near the top (see
    # load_prompt_block's docstring) - the shared _common.md glossary is retired.
    txt = (T04_PASS2 / name / f"prompt_{name}.md").read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)(?:\n## PROMPT END|\Z)", txt, re.DOTALL)
    return m.group(1).strip()

COMMON = load_prompt_block()
PROMPTS = {n: load_subtask_prompt(n) for n in
           ("gridline", "plan_footing", "plan_beam", "plan_slab", "section", "schedule", "notes")}

def prompt_for(subtask):
    return COMMON + "\n\n" + PROMPTS[subtask]

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
def gather_all_rows():
    """เดินทุกบ้านทุกไฟล์ครั้งเดียว คืน rows ทั้งหมด (ไม่ตัดสิน train/val/test ที่นี่ -
    การแบ่ง split เป็นขั้นแยกใน main()/build_folds() ที่กรอง all_rows ตาม row['house']
    ทำให้ path เดียวใช้ได้ทั้ง default single-split และ k-fold โดยไม่พิมพ์ logic ซ้ำ"""
    broken_files = []
    stats = Counter()
    per_subtask = Counter()
    skipped = defaultdict(list)
    needed_images = set()
    all_rows = []

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
                all_rows.append(row)
                per_subtask[sub] += 1
                stats["examples"] += 1

    return all_rows, broken_files, per_subtask, stats, skipped, needed_images


def write_jsonl(name, rows):
    with open(HERE / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def build_folds(all_rows, k):
    """k-fold แบบ house-level (ห้ามหั่นตัวอย่างข้ามบ้านเดียวกันไปคนละ fold - จะรั่วความจำ
    รูปทรง/สไตล์การเขียนแบบของบ้านนั้นข้าม fold เหมือนบั๊กเดิมที่กันบ้าน 08 ไว้นอก dataset)
    fold assignment = greedy balance by จำนวนตัวอย่างต่อบ้าน (ไม่ใช่ random - reproducible)
    เขียน train_fold{i}.jsonl/val_fold{i}.jsonl ทุก fold + fold_manifest.json

    หมายเหตุคุณภาพข้อมูล (2026-08-29 ค่ำ, มะขามสั่งทำแม้ไม่คุ้ม GPU-hours - งานต้องดี):
    5 หลังที่คนรีวิวเนื้อหาแล้ว (VAL_HOUSES เดิม 01-05) ตอนนี้ปนกับบ้าน op04 ที่ยังไม่รีวิว
    ในทุก fold เท่าๆ กันไม่ได้การันตี - fold_manifest.json ระบุ reviewed_houses_in_fold
    ต่อ fold ไว้ให้เห็นตรงๆ ว่า fold ไหนได้ GT สะอาดกี่หลัง อย่าเชื่อว่าทุก fold คุณภาพเท่ากัน"""
    house_rows = defaultdict(list)
    for r in all_rows:
        house_rows[r["house"]].append(r)
    house_count = {h: len(rows) for h, rows in house_rows.items()}
    houses_sorted = sorted(house_count, key=lambda h: (-house_count[h], h))

    fold_totals = [0] * k
    fold_members = [[] for _ in range(k)]
    for h in houses_sorted:
        idx = min(range(k), key=lambda i: (fold_totals[i], i))
        fold_members[idx].append(h)
        fold_totals[idx] += house_count[h]

    fold_sizes = []
    for i in range(k):
        val_houses_i = set(fold_members[i])
        train_rows = [r for r in all_rows if r["house"] not in val_houses_i]
        val_rows = [r for r in all_rows if r["house"] in val_houses_i]
        write_jsonl(f"train_fold{i}", train_rows)
        write_jsonl(f"val_fold{i}", val_rows)
        fold_sizes.append({
            "fold": i,
            "houses": sorted(fold_members[i]),
            "val_examples": len(val_rows),
            "train_examples": len(train_rows),
            "reviewed_houses_in_fold": sorted(h for h in fold_members[i] if h in VAL_HOUSES),
        })

    manifest = {
        "folds": k,
        "assignment": {h: i for i, hs in enumerate(fold_members) for h in hs},
        "fold_sizes": fold_sizes,
    }
    (HERE / "fold_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n--folds {k}: เขียน train_fold0..{k-1}.jsonl / val_fold0..{k-1}.jsonl + fold_manifest.json")
    for fs in fold_sizes:
        print(f"  fold {fs['fold']}: {len(fs['houses'])} หลัง, val {fs['val_examples']} ตัวอย่าง, "
              f"reviewed {len(fs['reviewed_houses_in_fold'])}/{len(fs['houses'])}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=0,
                     help="เปิด k-fold CV เพิ่ม (house-level, greedy-balanced) เช่น --folds 5 "
                          "- ไม่กระทบ train.jsonl/val.jsonl/test.jsonl เดิม เขียนเพิ่มเป็นไฟล์ใหม่")
    args = ap.parse_args()

    OUT_IMAGES.mkdir(exist_ok=True)
    all_rows, broken_files, per_subtask, stats, skipped, needed_images = gather_all_rows()

    # copy images (flat, filenames unique — house name is in the filename)
    for img in sorted(needed_images):
        dst = OUT_IMAGES / img.name
        if not dst.exists():
            shutil.copy2(img, dst)

    rows_test = [r for r in all_rows if r["house"] in TEST_HOUSES]
    rows_val = [r for r in all_rows if r["house"] in VAL_HOUSES]
    # 2026-08-29 มะขามสั่ง: val houses (01-05) go in train too
    rows_train = [r for r in all_rows if r["house"] not in TEST_HOUSES]

    write_jsonl("train", rows_train)
    write_jsonl("val", rows_val)
    write_jsonl("test", rows_test)
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

    if args.folds:
        build_folds(all_rows, args.folds)

if __name__ == "__main__":
    sys.exit(main())
