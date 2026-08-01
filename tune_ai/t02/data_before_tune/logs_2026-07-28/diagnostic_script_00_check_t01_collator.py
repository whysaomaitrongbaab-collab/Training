#!/usr/bin/env python3
"""
ตรวจว่า train_qwen36.py จริง (collator แบบ default ไม่มี resize="max") ทำให้ภาพถูกย่อ
เหลือ 512px จริงไหม — reproduce สภาพแวดล้อมของ t01 ตอนเทรนจริงเป๊ะ (2026-07-21/24)
ไม่แตะ resize= เลย ให้เหมือน train_qwen36.py:164 เป๊ะ
"""
import json
from pathlib import Path
from PIL import Image

from unsloth import FastVisionModel

MODEL_ID = "unsloth/Qwen3.6-35B-A3B"
HERE = Path("/workspace/tune/data_before_tune")

model, tokenizer = FastVisionModel.from_pretrained(MODEL_ID, load_in_4bit=False)

# เช็คตรงว่า vision_config มี image_size ไหม (ตัวตัดสินว่า collator default จะ fallback 512px หรือไม่)
vc = model.config.vision_config.to_dict() if hasattr(model.config, "vision_config") else {}
print("has image_size in vision_config:", "image_size" in vc)

# ตั้งความละเอียดภาพแบบเดียวกับ train_qwen36.py ทุกบรรทัด (MAX_PIXELS=5120*1024, MIN_PIXELS=256*1024)
MAX_PIXELS = 5120 * 1024
MIN_PIXELS = 256 * 1024
ip = getattr(tokenizer, "image_processor", None)
if ip is not None:
    ip.size["longest_edge"] = MAX_PIXELS
    ip.size["shortest_edge"] = MIN_PIXELS
    print(f"image processor size set: {ip.size}")

# โหลดตัวอย่างจริงตัวเดียวกับที่ t02 เคยเช็ค (แถวแรกของ train.jsonl)
with open(HERE / "train.jsonl", encoding="utf-8") as f:
    row = json.loads(f.readline())
content = []
for c in row["messages"][0]["content"]:
    if c["type"] == "image":
        content.append({"type": "image", "image": Image.open(HERE / c["image"]).convert("RGB")})
    else:
        content.append({"type": "text", "text": c["text"]})
train_ds0 = {"messages": [{"role": "user", "content": content},
                           {"role": "assistant", "content": row["messages"][1]["content"]}]}

from unsloth.trainer import UnslothVisionDataCollator

print("\n=== collator แบบ DEFAULT เป๊ะ (เหมือน train_qwen36.py:164 — ไม่มี resize=) ===")
collator_default = UnslothVisionDataCollator(model, tokenizer)
print(f"  self.image_size ที่ collator ตั้งเอง: {collator_default.image_size!r}")
b = collator_default([train_ds0])
pv = b.get("pixel_values")
gt = b.get("image_grid_thw")
if gt is not None:
    tok = int((gt[:, 1] * gt[:, 2]).sum()) // 4
    print(f"  pixel_values {tuple(pv.shape)} | grid_thw {gt.tolist()} -> ~{tok} visual tokens")
else:
    print(f"  pixel_values shape: {tuple(pv.shape) if pv is not None else None}")

print("\n=== collator แบบ resize='max' (เหมือน train_qwen3vl.py ของ t02) เทียบผล ===")
collator_max = UnslothVisionDataCollator(model, tokenizer, resize="max", max_seq_length=24576)
b2 = collator_max([train_ds0])
gt2 = b2.get("image_grid_thw")
if gt2 is not None:
    tok2 = int((gt2[:, 1] * gt2[:, 2]).sum()) // 4
    print(f"  grid_thw {gt2.tolist()} -> ~{tok2} visual tokens")

print("\n=== สรุป ===")
print("ถ้า default ได้ ~205 token = t01 เทรนด้วยภาพเบลอ 512px จริง (ยืนยันบั๊กเดียวกับ Qwen3-VL)")
print("ถ้า default ได้ตัวเลขใกล้เคียง resize='max' = ไม่มีปัญหา ไม่เข้า fallback")
