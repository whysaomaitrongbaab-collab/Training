#!/usr/bin/env python3
"""build_4pass.py — รวม 4 pass เป็น dataset เดียว จ่ายให้ทั้งสองแขน (มะขามสั่ง 2026-08-31
"Voldemort and Courser เทรนทูนครบ 4 pass ไปเลย" ตามด้วย "epoch 3, k fold 2, train/val 4/1")

  pass1  = ชุดสกัด element เดิมของ t04 (7 subtask: section/plan_*/schedule/notes/gridline)
  pass0  = จำแนกหน้า (t05 สร้างคืน 2026-08-31)
  pass2.4 = สกัด element + hint จาก CV (หน้าเดียวกับ pass1 บาง subtask แต่มี hint ต่อท้าย —
            ตั้งใจให้ซ้ำหน้า เพื่อสอนโมเดลทั้งโหมดมี/ไม่มี hint ดู t05_workflow.md)
  pass3  = ถอดระยะจากบัญชี CV + รูปมาร์คเลข

k-fold (2026-08-31 ตอนดึก — convention เดียวกับ build_folds_llamafactory.py ของ t04 เป๊ะ):
  "k fold 2, train/val 4/1" = **k=5 folds จริง (8 บ้าน/fold จาก 40 บ้าน) แต่รันแค่ fold0+fold1**
  (ประหยัดงบ เหมือน t04) แต่ละ fold train=32 บ้าน(4/5) val=8 บ้าน(1/5) = อัตราส่วน 4:1 พอดี
  ไม่ใช่แบ่งครึ่ง k=2 จริง (นั่นจะเห็นข้อมูลแค่ 50% ต่อโมเดล แย่กว่ามาก)

  **ใช้ house→fold assignment ของ t04 เป็นตัวตัดสิน ไม่ใช้ VAL_HOUSES คงที่เดิมอีกต่อไป** — เจอ
  ตอนเช็ค: fold0 val ตรงกับ 2 บ้าน val เดิมของเราเป๊ะ (บ้าน_เล็ก_2ชั้น_05, บ้าน_ใหญ่_1ชั้น_02) แต่มี
  1 บ้านชน (บ้าน_ใหญ่_1ชั้น_01 อยู่ train ของเราเดิม แต่เป็น val ของ fold0 ตาม t04) — ถ้ายังใช้
  VAL_HOUSES คงที่ บ้านนี้จะอยู่ train ของ pass0 พร้อมกับอยู่ val ของ pass1 ในโมเดลเดียวกัน = รั่ว
  ข้ามชนิดข้อมูล แก้โดยยึด house-to-split ของ t04 ต่อ fold เป็นความจริงหนึ่งเดียวทุก pass —
  ผลพลอยได้: เทียบตัวเลขกับ t04 เดิมได้ตรงกันด้วย (บ้าน val ชุดเดียวกันเป๊ะ)

ผลลัพธ์ (ต่อ fold):
  t05_Courser/train_fold{k}.jsonl · val_fold{k}.jsonl              (สาย Unsloth message-parts)
  t44_Voldemort/train_fold{k}_lf.json · val_fold{k}_lf.json · dataset_info.json  (สาย LF sharegpt)
**เนื้อข้อมูลเหมือนกันเป๊ะทั้งสองแขนทุก fold** — ต่างแค่รูปแบบ serialize เท่านั้น จงใจ: t04
เปลี่ยนทั้งโมเดลและ precision พร้อมกันจนแยกไม่ออกว่าอะไรทำให้ผลต่าง (confound) รอบนี้ข้อมูล
ตรึงเท่ากัน ผลต่างที่เห็นจึงมาจากโมเดลจริง ๆ

สามเรื่องที่ต้องแก้ตอนรวม (เจอจาก audit 2026-08-31 ทั้งหมด ไม่ใช่การเดา):
1. **path รูป**: pass1 เดิมเก็บ "images/<ไฟล์>.png" ชี้โฟลเดอร์แบนที่มีแค่ในเครื่องเทรน t04
   → เขียนใหม่เป็น "image/<บ้าน>/<ไฟล์>.png" เทียบรากรีโป (แบบเดียวกับ pass0/24/3)
2. **assistant content 2 รูปแบบ**: pass1/pass24 เป็น list ([{type:text,text:...}]) ส่วน
   pass0/pass3 เป็น string — normalize เป็น list ทั้งหมด (รูปแบบที่ t01→t03→t04 เทรนผ่านจริง)
3. **val ปน**: t04 val.jsonl เดิมเป็น subset ของ train.jsonl ทั้งก้อน (บั๊กเดิม) — ตอนนี้ไม่ใช้
   train.jsonl/val.jsonl ของ t04 อีกแล้ว ใช้ train_fold{k}/val_fold{k} ที่แยกสะอาดจริงแทน

รัน:  python build_4pass.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent.parent
T44 = TRAINING / "tune_ai" / "t44_Voldemort"
DATA_T04 = TRAINING / "tune_ai" / "t04_Purson" / "data_before_tune"
IMG_ROOT = TRAINING / "image"

FOLDS = [0, 1]     # รันแค่ 2 จาก 5 fold ที่มีจริง (งบ) — ดู docstring ด้านบน

# pass0 มี label auto ครบทั้ง 40 บ้าน (939 หน้า) แต่สโคปคุมงบเดิมของมะขามคือ 5 บ้าน
# True = ใช้ทุกบ้าน (ข้อมูลฟรีที่ derive ไว้แล้ว แต่ +~775 แถว = ค่าเทรนเพิ่ม)
PASS0_ALL_HOUSES = False
PASS0_SCOPE_5 = {"บ้าน_เล็ก_2ชั้น_04", "บ้าน_เล็ก_1ชั้น_04", "บ้าน_ใหญ่_2ชั้น_04",
                 "บ้าน_ใหญ่_1ชั้น_01", "บ้าน_เล็ก_2ชั้น_05"}

LF_ENTRY = {
    "formatting": "sharegpt",
    "columns": {"messages": "messages", "images": "images"},
    "tags": {"role_tag": "role", "content_tag": "content",
             "user_tag": "user", "assistant_tag": "assistant"},
}


def bare(h):
    return re.sub(r"^\d{2}", "", h)


def read_jsonl(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def house_of_image(fname):
    """'บ้าน_เล็ก_2ชั้น_01_หน้า31.png' → 'บ้าน_เล็ก_2ชั้น_01' (ตัดที่ _หน้า)"""
    m = re.match(r"^(.*?)_หน้า", Path(fname).name)
    return m.group(1) if m else None


def as_text_parts(content):
    """normalize assistant content → list-of-parts (รูปแบบที่พิสูจน์แล้วว่าเทรนผ่าน)"""
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content


def fix_pass1_paths(row, problems):
    """pass1: images/<ไฟล์>.png → image/<บ้าน>/<ไฟล์>.png + ตรวจว่าไฟล์มีจริง"""
    content = []
    for c in row["messages"][0]["content"]:
        if c.get("type") != "image":
            content.append(dict(c))
            continue
        name = Path(c["image"]).name
        h = house_of_image(name)
        if h is None:
            problems.append(f"{row['id']}: แยกชื่อบ้านจาก '{name}' ไม่ได้")
            return None
        p = IMG_ROOT / h / name
        if not p.exists():
            problems.append(f"{row['id']}: ไม่พบรูป {p.relative_to(TRAINING)}")
            return None
        content.append({"type": "image", "image": f"image/{h}/{name}"})
    return content


def normalize_pass1(rows, problems):
    out = []
    seen = set()
    for r in rows:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        content = fix_pass1_paths(r, problems)
        if content is None:
            continue
        out.append({"id": r["id"], "house": r["house"], "subtask": r["subtask"], "pass": "pass1",
                   "messages": [{"role": "user", "content": content},
                                {"role": "assistant",
                                 "content": as_text_parts(r["messages"][1]["content"])}]})
    return out


def collect_pass024(problems):
    """pass0/pass2.4/pass3 — รวม train+val เดิมของ t05 เข้าเป็นกองเดียว (ไม่ใช้ split เดิม
    เพราะรอบนี้แบ่งใหม่ตาม fold house assignment ของ t04 แทน)"""
    rows = []
    for pass_name, files in (("pass0", ("pass0_train.jsonl", "pass0_val.jsonl")),
                             ("pass2.4", ("pass24_train.jsonl", "pass24_val.jsonl")),
                             ("pass3", ("pass3_train.jsonl", "pass3_val.jsonl"))):
        for fn in files:
            for r in read_jsonl(HERE / fn):
                if pass_name == "pass0" and not PASS0_ALL_HOUSES \
                        and bare(r["house"]) not in PASS0_SCOPE_5:
                    continue
                for c in r["messages"][0]["content"]:
                    if c.get("type") == "image" and not (TRAINING / c["image"]).exists():
                        problems.append(f"{r['id']}: ไม่พบรูป {c['image']}")
                rows.append({"id": r["id"], "house": r["house"], "subtask": r["subtask"],
                             "pass": pass_name,
                             "messages": [r["messages"][0],
                                          {"role": "assistant",
                                           "content": as_text_parts(r["messages"][1]["content"])}]})
    return rows


def to_lf(row):
    """message-parts → sharegpt ของ LLaMA-Factory (ลอจิกเดียวกับ build_dataset_llamafactory.py)"""
    uc = row["messages"][0]["content"]
    images = [c["image"] for c in uc if c["type"] == "image"]
    texts = [c["text"] for c in uc if c["type"] == "text"]
    seen_text = False
    for c in uc:
        if c["type"] == "text":
            seen_text = True
        elif seen_text:
            raise AssertionError(f"{row['id']}: เจอ image หลัง text — LF ต้องการ image ก่อนเสมอ")
    gt = "".join(x.get("text", "") for x in row["messages"][1]["content"])
    return {"messages": [{"role": "user", "content": "<image>" * len(images) + "".join(texts)},
                         {"role": "assistant", "content": gt}],
            "images": images}


def write_split(name, split):
    (HERE / f"{name}.jsonl").write_text(
        "".join(json.dumps({k: v for k, v in r.items() if k != "pass"},
                           ensure_ascii=False) + "\n" for r in split), encoding="utf-8")
    T44.mkdir(exist_ok=True)
    (T44 / f"{name}_lf.json").write_text(
        json.dumps([to_lf(r) for r in split], ensure_ascii=False, indent=2), encoding="utf-8")


def bypass(split):
    return dict(Counter(r["pass"] for r in split))


def main():
    problems = []
    pass024 = collect_pass024(problems)
    info = {}

    for k in FOLDS:
        val_houses_k = {bare(r["house"]) for r in read_jsonl(DATA_T04 / f"val_fold{k}.jsonl")}
        p1_train = normalize_pass1(read_jsonl(DATA_T04 / f"train_fold{k}.jsonl"), problems)
        p1_val = normalize_pass1(read_jsonl(DATA_T04 / f"val_fold{k}.jsonl"), problems)
        p024_train = [r for r in pass024 if bare(r["house"]) not in val_houses_k]
        p024_val = [r for r in pass024 if bare(r["house"]) in val_houses_k]

        train = p1_train + p024_train
        val = p1_val + p024_val

        th = {bare(r["house"]) for r in train}
        vh = {bare(r["house"]) for r in val}
        if th & vh:
            problems.append(f"fold{k}: บ้าน val ปนใน train: {th & vh}")
        ids = [r["id"] for r in train + val]
        if len(ids) != len(set(ids)):
            problems.append(f"fold{k}: id ซ้ำ")

        if problems:
            continue     # เก็บปัญหาของทุก fold ไว้รายงานทีเดียว ไม่เขียนไฟล์ถ้ามีปัญหา

        write_split(f"train_fold{k}", train)
        write_split(f"val_fold{k}", val)
        info[f"t44_train_fold{k}"] = {"file_name": f"train_fold{k}_lf.json", **LF_ENTRY}
        info[f"t44_val_fold{k}"] = {"file_name": f"val_fold{k}_lf.json", **LF_ENTRY}

        print(f"fold{k}: train {len(train)} / val {len(val)}  (บ้าน val: {len(vh)} — {sorted(vh)[:3]}...)")
        print(f"  train ราย pass: {bypass(train)}")
        print(f"  val   ราย pass: {bypass(val)}")

    if problems:
        print(f"\n❌ พบปัญหา {len(problems)} รายการ — ไม่เขียนไฟล์ (ห้ามเทรนด้วยข้อมูลที่รูปหาย/ปนกัน)")
        for p in problems[:20]:
            print("   -", p)
        sys.exit(1)

    (T44 / "dataset_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    print(f"\n→ Courser: {HERE}/train_fold{{0,1}}.jsonl · val_fold{{0,1}}.jsonl")
    print(f"→ Voldemort: {T44}/train_fold{{0,1}}_lf.json · val_fold{{0,1}}_lf.json · dataset_info.json")
    if not PASS0_ALL_HOUSES:
        print("\nℹ pass0 ใช้สโคป 5 บ้านตามที่เคาะไว้ — ตั้ง PASS0_ALL_HOUSES=True "
              "เพื่อใช้ label ที่ derive ไว้แล้วครบทั้ง 40 บ้าน")


if __name__ == "__main__":
    main()
