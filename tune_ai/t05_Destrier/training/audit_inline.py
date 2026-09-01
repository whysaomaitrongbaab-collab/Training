#!/usr/bin/env python3
"""audit_inline.py — ตรวจ jsonl integrity + cv_mark duplicate + element conservation
รันแทน subagent ที่โดน session limit บล็อก"""
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent.parent
GT_ROOT = TRAINING / "json_แก้ไขแล้ว"
IMG_ROOT = TRAINING / "image"

VAL_HOUSES = {"บ้าน_เล็ก_2ชั้น_05", "บ้าน_ใหญ่_1ชั้น_02"}


def bare(h):
    return re.sub(r"^\d{2}", "", h)


def load(name):
    p = HERE / name
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


print("=== 1. jsonl parse + shape integrity ===")
files = ["pass0_train.jsonl", "pass0_val.jsonl", "pass24_train.jsonl", "pass24_val.jsonl",
         "pass3_train.jsonl", "pass3_val.jsonl"]
rows_by_file = {}
for fn in files:
    rows = load(fn)
    rows_by_file[fn] = rows
    bad = 0
    for r in rows:
        try:
            assert "id" in r and "house" in r and "subtask" in r
            msgs = r["messages"]
            assert len(msgs) == 2
            assert msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant"
            imgs = [c for c in msgs[0]["content"] if c.get("type") == "image"]
            assert len(imgs) >= 1
            json.loads(msgs[1]["content"])
        except Exception as e:
            bad += 1
    print(f"  {fn}: {len(rows)} rows, {bad} malformed")

print("\n=== 2. image paths exist ===")
missing = []
for fn, rows in rows_by_file.items():
    for r in rows:
        for c in r["messages"][0]["content"]:
            if c.get("type") == "image":
                p = TRAINING / c["image"]
                if not p.exists():
                    missing.append((fn, r["id"], c["image"]))
print(f"  missing images: {len(missing)}")
for m in missing[:10]:
    print("   ", m)

print("\n=== 3. train/val house separation ===")
for base in ("pass0", "pass24", "pass3"):
    train_houses = {bare(r["house"]) for r in rows_by_file[f"{base}_train.jsonl"]}
    val_houses = {bare(r["house"]) for r in rows_by_file[f"{base}_val.jsonl"]}
    overlap = train_houses & val_houses
    print(f"  {base}: train houses={sorted(train_houses)} val houses={sorted(val_houses)} overlap={overlap}")

print("\n=== 4. id uniqueness ===")
for base in ("pass0", "pass24", "pass3"):
    ids = [r["id"] for r in rows_by_file[f"{base}_train.jsonl"] + rows_by_file[f"{base}_val.jsonl"]]
    dupes = [i for i in set(ids) if ids.count(i) > 1]
    print(f"  {base}: {len(ids)} ids, {len(dupes)} duplicated")

print("\n=== 5. pass3 cv_mark duplicate check (THE suspected bug) ===")
ACC_RX = re.compile(r"^(\d+)\)\s*(\S+)", re.MULTILINE)
total_dup_marks = 0
total_dup_elements = 0
rows_with_dupes = 0
for fn in ("pass3_train.jsonl", "pass3_val.jsonl"):
    for r in rows_by_file[fn]:
        user_text = next(c["text"] for c in r["messages"][0]["content"] if c.get("type") == "text")
        account_nums = {int(m.group(1)) for m in ACC_RX.finditer(user_text)}
        label = json.loads(r["messages"][1]["content"])
        marks = [e.get("cv_mark") for e in label["elements"] if e.get("cv_mark") is not None]
        mark_count = defaultdict(int)
        for m in marks:
            mark_count[m] += 1
        dupes = {m: c for m, c in mark_count.items() if c > 1}
        # account number sanity: every cv_mark must be in account_nums
        marks_not_in_account = set(mark_count) - account_nums
        if dupes:
            rows_with_dupes += 1
            total_dup_marks += len(dupes)
            total_dup_elements += sum(dupes.values())
            print(f"  {r['id']}: {len(dupes)} marks shared, elements involved={sum(dupes.values())}, "
                  f"detail={dupes}")
        if marks_not_in_account:
            print(f"  ⚠ {r['id']}: cv_mark not in account text: {marks_not_in_account}")
print(f"  TOTAL: {rows_with_dupes} rows affected, {total_dup_marks} distinct marks reused, "
      f"{total_dup_elements} elements sharing a non-unique mark")

print("\n=== 6. pass3 element conservation vs GT (spot: all beam-plan rows) ===")


def elements_flat(d):
    els = list(d.get("elements") or [])
    for v in d.get("views") or []:
        if isinstance(v, dict):
            els += list(v.get("elements") or [])
    return [e for e in els if isinstance(e, dict)]


def expand_key(e):
    if e.get("grid_ref_start") is not None or e.get("grid_ref_end") is not None:
        return (e.get("element_id"), e.get("element_type"), e.get("grid_ref_start"), e.get("grid_ref_end"))
    return (e.get("element_id"), e.get("element_type"), tuple(e.get("grid_refs") or []))


mismatches = 0
for fn in ("pass3_train.jsonl", "pass3_val.jsonl"):
    for r in rows_by_file[fn]:
        parts = r["id"].split("::")
        house_dir_name = parts[0]
        gt_stem = parts[1]
        gt_dir = GT_ROOT / house_dir_name
        gt_file = gt_dir / f"{gt_stem}.json"
        if not gt_file.exists():
            print(f"  ⚠ GT file missing for {r['id']}: {gt_file}")
            mismatches += 1
            continue
        gt = json.loads(gt_file.read_text(encoding="utf-8"))
        gt_els = elements_flat(gt)
        # expand count-aggregated (only when expandable)
        gt_keys = []
        for e in gt_els:
            c = e.get("count") or 1
            refs = e.get("grid_refs") or []
            if c > 1 and len(refs) == c:
                for ref in refs:
                    e2 = dict(e)
                    e2["grid_refs"] = [ref]
                    gt_keys.append(expand_key(e2))
            else:
                gt_keys.append(expand_key(e))
        label = json.loads(r["messages"][1]["content"])
        lab_keys = [expand_key(e) for e in label["elements"]]
        gt_multiset = defaultdict(int)
        for k in gt_keys:
            gt_multiset[k] += 1
        lab_multiset = defaultdict(int)
        for k in lab_keys:
            lab_multiset[k] += 1
        if gt_multiset != lab_multiset:
            mismatches += 1
            missing_from_label = {k: gt_multiset[k] - lab_multiset.get(k, 0) for k in gt_multiset
                                   if gt_multiset[k] > lab_multiset.get(k, 0)}
            extra_in_label = {k: lab_multiset[k] - gt_multiset.get(k, 0) for k in lab_multiset
                               if lab_multiset[k] > gt_multiset.get(k, 0)}
            print(f"  ✗ {r['id']}: GT={len(gt_keys)} label={len(lab_keys)} "
                  f"missing_from_label={missing_from_label} extra_in_label={extra_in_label}")
print(f"  rows with element-set mismatch: {mismatches} / {len(rows_by_file['pass3_train.jsonl']) + len(rows_by_file['pass3_val.jsonl'])}")

print("\n=== 7. pass24 shape check ===")
for fn in ("pass24_train.jsonl", "pass24_val.jsonl"):
    bad = 0
    for r in rows_by_file[fn]:
        if not r["id"].endswith("::arm24"):
            bad += 1
            continue
        imgs = [c for c in r["messages"][0]["content"] if c.get("type") == "image"]
        texts = [c for c in r["messages"][0]["content"] if c.get("type") == "text"]
        if len(imgs) != 1 or len(texts) < 1:
            bad += 1
    print(f"  {fn}: {bad} malformed")

print("\ndone")
