#!/usr/bin/env python3
"""build_dataset_llamafactory.py — แปลง train.jsonl/val.jsonl (สาย Unsloth message-parts,
สร้างโดย build_dataset_t03.py) เป็นฟอร์แมต multimodal sharegpt ของ LLaMA-Factory

**ไม่แตะ GT/รูปเลย** — อ่านของที่ build_dataset_t03.py ทำไว้แล้วเท่านั้น แปลงแค่ "โครง" jsonl
(list-of-content-parts → string + <image> token + images[] แยก) ตามฟอร์แมตจริงที่ยืนยันจาก
data/mllm_demo.json + data/dataset_info.json ใน hiyouga/LLaMA-Factory repo (2026-08-30):
  {"messages": [{"role": "user", "content": "<image><image>...prompt text"},
                {"role": "assistant", "content": "<gt json string>"}],
   "images": ["images/xxx.png", ...]}
dataset_info.json entry: formatting sharegpt, columns {messages: messages, images: images},
tags {role_tag: role, content_tag: content, user_tag: user, assistant_tag: assistant}

ที่มาของ path รูป: train.jsonl เดิมเก็บ "images/<ชื่อไฟล์>.png" (สัมพัทธ์กับ data_before_tune/)
ซึ่งตรงกับ convention ของ LLaMA-Factory เป๊ะ (dataset_dir = data_before_tune/) ไม่ต้องแก้ path เลย

รัน:  python build_dataset_llamafactory.py    (อ่าน train.jsonl/val.jsonl ที่มีอยู่แล้ว
                                                เขียน train_lf.json/val_lf.json/dataset_info.json)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

DATASET_ENTRY = {
    "formatting": "sharegpt",
    "columns": {"messages": "messages", "images": "images"},
    "tags": {
        "role_tag": "role", "content_tag": "content",
        "user_tag": "user", "assistant_tag": "assistant",
    },
}


def convert_row(row):
    """messages[0].content = [image parts..., ONE text part] (ยืนยันโครงจริงจาก build_dataset_t03.py
    — image ทุกใบเรียงก่อน text เสมอ ไม่มีข้อยกเว้น) → "<image>"*n + prompt text"""
    user_content = row["messages"][0]["content"]
    images = [c["image"] for c in user_content if c["type"] == "image"]
    texts = [c["text"] for c in user_content if c["type"] == "text"]
    assert len(texts) == 1, f"{row['id']}: คาดว่ามี text part เดียว เจอ {len(texts)}"
    assert all(c["type"] in ("image", "text") for c in user_content), \
        f"{row['id']}: เจอ content type ที่ไม่รู้จัก"
    # ยืนยันลำดับจริง (ไม่ใช่แค่สมมติ) — image ต้องมาก่อน text ทั้งหมดเสมอ
    seen_text = False
    for c in user_content:
        if c["type"] == "text":
            seen_text = True
        elif seen_text:
            raise AssertionError(f"{row['id']}: เจอ image หลัง text — โครงเปลี่ยนไปจากที่คาด")

    assistant_content = row["messages"][1]["content"]
    gt_text = "".join(x.get("text", "") for x in assistant_content) \
        if isinstance(assistant_content, list) else assistant_content

    return {
        "messages": [
            {"role": "user", "content": "<image>" * len(images) + texts[0]},
            {"role": "assistant", "content": gt_text},
        ],
        "images": images,
    }


def convert_split(name):
    src = HERE / f"{name}.jsonl"
    rows = []
    with open(src, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(convert_row(json.loads(line)))
    dst = HERE / f"{name}_lf.json"
    dst.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{name}: {len(rows)} แถว → {dst.name}")
    return len(rows)


def main():
    n_train = convert_split("train")
    n_val = convert_split("val")

    info_path = HERE / "dataset_info.json"
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    info["t04_train"] = {"file_name": "train_lf.json", **DATASET_ENTRY}
    info["t04_val"] = {"file_name": "val_lf.json", **DATASET_ENTRY}
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"dataset_info.json: t04_train ({n_train}) + t04_val ({n_val}) ลงทะเบียนแล้ว")
    print(f"\nใช้ใน config yaml: dataset: t04_train  ·  eval_dataset: t04_val  ·  "
          f"dataset_dir: {HERE}")


if __name__ == "__main__":
    main()
