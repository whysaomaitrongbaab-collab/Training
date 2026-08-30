#!/usr/bin/env python3
"""smoke_4pass.py — ตรวจ dataset 4 pass k-fold ก่อนเช่า GPU (รันบน CPU ฟรี)
บทเรียน t04: บั๊ก config/ข้อมูลที่เจอบนเครื่องเช่า = เสียเงินฟรี — ทุกอย่างที่ตรวจได้บน CPU ต้องตรวจที่นี่

ตรวจต่อ fold: โครง jsonl · รูปเปิดได้จริงทุกใบ · val ไม่ปน train · id ไม่ซ้ำ ·
             <image> token ตรงจำนวนรูปฝั่ง LF · ขนาดรูปจริง vs MAX_PIXELS · assistant JSON parse ได้
"""
import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
T44 = REPO / "tune_ai" / "t44_Voldemort"
MAX_PIXELS = 7680 * 1024
FOLDS = [0, 1]

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
    return cond


def bare(h):
    return re.sub(r"^\d{2}", "", h)


def read_jsonl(p):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


seen_img_global = {}

for k in FOLDS:
    print(f"\n{'=' * 20} fold{k} {'=' * 20}")
    print(f"=== Courser (Unsloth message-parts) ===")
    splits = {}
    for name in (f"train_fold{k}", f"val_fold{k}"):
        rows = read_jsonl(HERE / f"{name}.jsonl")
        splits[name] = rows
        print(f"  {name}: {len(rows)} แถว")
        for r in rows:
            check(isinstance(r["messages"][1]["content"], list),
                  f"fold{k}/{r['id']}: assistant ไม่ใช่ list-parts")
            gt = "".join(x.get("text", "") for x in r["messages"][1]["content"])
            try:
                json.loads(gt)
            except json.JSONDecodeError as e:
                fails.append(f"fold{k}/{r['id']}: assistant ไม่ใช่ JSON ที่ parse ได้ ({e})")
            texts = [c for c in r["messages"][0]["content"] if c["type"] == "text"]
            check(len(texts) >= 1, f"fold{k}/{r['id']}: ไม่มี text part")
            seen_text = False
            for c in r["messages"][0]["content"]:
                if c["type"] == "text":
                    seen_text = True
                elif seen_text:
                    fails.append(f"fold{k}/{r['id']}: image อยู่หลัง text (LF ต้องการ image ก่อน)")

    tr_h = {bare(r["house"]) for r in splits[f"train_fold{k}"]}
    va_h = {bare(r["house"]) for r in splits[f"val_fold{k}"]}
    check(not (tr_h & va_h), f"fold{k}: บ้าน val ปนใน train: {tr_h & va_h}")
    print(f"  บ้าน train {len(tr_h)} · val {len(va_h)} · ปนกัน {len(tr_h & va_h)}")

    all_ids = [r["id"] for rows in splits.values() for r in rows]
    check(len(all_ids) == len(set(all_ids)), f"fold{k}: id ซ้ำข้าม split")

    oversize, biggest = 0, (0, None)
    for rows in splits.values():
        for r in rows:
            for c in r["messages"][0]["content"]:
                if c["type"] != "image":
                    continue
                rel = c["image"]
                if rel in seen_img_global:
                    continue
                p = REPO / rel
                if not p.exists():
                    fails.append(f"ไม่พบรูป {rel}")
                    seen_img_global[rel] = None
                    continue
                try:
                    with Image.open(p) as im:
                        px = im.width * im.height
                    seen_img_global[rel] = px
                except Exception as e:                  # noqa: BLE001 — อ่านรูปพังต้องรู้ทุกกรณี
                    fails.append(f"เปิดรูปไม่ได้ {rel}: {e}")
                    seen_img_global[rel] = None

    print(f"\n=== Voldemort (LLaMA-Factory sharegpt) ===")
    for name in (f"train_fold{k}", f"val_fold{k}"):
        lf = json.loads((T44 / f"{name}_lf.json").read_text(encoding="utf-8"))
        print(f"  {name}_lf.json: {len(lf)} แถว")
        check(len(lf) == len(splits[name]), f"fold{k}/{name}: จำนวนแถว LF ไม่ตรงกับ jsonl")
        for i, r in enumerate(lf):
            n_tok = r["messages"][0]["content"].count("<image>")
            check(n_tok == len(r["images"]),
                  f"fold{k}/{name}[{i}]: <image> {n_tok} ตัว แต่ images {len(r['images'])} ใบ")
            check(r["messages"][0]["content"].startswith("<image>"),
                  f"fold{k}/{name}[{i}]: content ไม่ได้ขึ้นต้นด้วย <image>")
            try:
                json.loads(r["messages"][1]["content"])
            except json.JSONDecodeError:
                fails.append(f"fold{k}/{name}[{i}]: assistant LF ไม่ใช่ JSON")

ok_imgs = sorted(v for v in seen_img_global.values() if v)
oversize = sum(1 for v in ok_imgs if v > MAX_PIXELS)
print(f"\n=== รูปรวมทุก fold ===")
print(f"  รูปไม่ซ้ำ {len(seen_img_global)} ใบ · เปิดได้ {len(ok_imgs)} · เกิน MAX_PIXELS {oversize} "
      f"({oversize / max(1, len(ok_imgs)) * 100:.0f}%)")
if ok_imgs:
    print(f"  ใหญ่สุด {ok_imgs[-1] / 1e6:.2f} MP · median {ok_imgs[len(ok_imgs) // 2] / 1e6:.2f} MP")

info = json.loads((T44 / "dataset_info.json").read_text(encoding="utf-8"))
expected_keys = {f"t44_train_fold{k}" for k in FOLDS} | {f"t44_val_fold{k}" for k in FOLDS}
check(expected_keys <= set(info), f"dataset_info.json ขาด key: {expected_keys - set(info)}")
print(f"\ndataset_info.json: {sorted(info)}")

print()
if fails:
    print(f"❌ ไม่ผ่าน {len(fails)} ข้อ")
    for f in fails[:25]:
        print("   -", f)
    raise SystemExit(1)
print(f"✅ ผ่านทุกข้อ — dataset 4 pass (fold {FOLDS}) พร้อมสำหรับทั้งสองแขน")
