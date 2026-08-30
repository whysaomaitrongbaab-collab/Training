#!/usr/bin/env python3
"""build_folds_llamafactory.py — แปลง train_fold{k}.jsonl / val_fold{k}.jsonl เป็นฟอร์แมต
LLaMA-Factory sharegpt แล้วลงทะเบียนใน dataset_info.json

มะขามเคาะ 2026-08-30: รอบ Purson ทำ k-fold **2 folds จาก k=5 ที่มีอยู่** (fold 0 + fold 1)
เหตุผลที่ไม่ทำ k=2 จริง (แบ่งครึ่ง): k=2 แต่ละโมเดลเห็นข้อมูลแค่ 50% (20 หลัง) ส่วน fold ของ
k=5 เห็น 80% (32 หลัง) → คุณภาพใกล้เคียงเทรนเต็มกว่ามาก และไฟล์ fold มีอยู่แล้วไม่ต้องแบ่งใหม่

เหตุผลที่ต้องใช้ fold แทน split เดิม (สำคัญ — พบ 2026-08-30):
  val.jsonl เดิม = 5 หลังที่ review แล้ว ซึ่ง **อยู่ใน train.jsonl ทั้ง 5 หลัง** (ปนเปื้อน 100%)
  → วัด generalization ไม่ได้เลย ตัวเลขสูงเกินจริง
  ส่วน fold: 8 หลัง val ไม่อยู่ใน 32 หลัง train เลย = สะอาดจริง อัตราส่วน 4:1 พอดี

ใช้ convert_row/convert_split ตัวเดิมจาก build_dataset_llamafactory.py (ไม่ copy logic ซ้ำ)

รัน:  python build_folds_llamafactory.py
"""
import json
from pathlib import Path

from build_dataset_llamafactory import DATASET_ENTRY, convert_split

HERE = Path(__file__).resolve().parent
FOLDS = [0, 1, 2, 3]  # มะขามเคาะ 2026-08-30 ดึก: ขยายจาก 2 → 4 folds (จ่ายเอง ไม่จำกัดงบ)


def main():
    info_path = HERE / "dataset_info.json"
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}

    for k in FOLDS:
        for split in ("train", "val"):
            name = f"{split}_fold{k}"
            n = convert_split(name)
            key = f"t04_fold{k}_{split}"
            info[key] = {"file_name": f"{name}_lf.json", **DATASET_ENTRY}
            print(f"  → ลงทะเบียน {key} ({n} แถว)")

    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ndataset_info.json อัปเดตแล้ว — keys: {sorted(info.keys())}")


if __name__ == "__main__":
    main()
