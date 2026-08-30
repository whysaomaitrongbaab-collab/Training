#!/usr/bin/env python3
"""probe_img_tokens.py — เทียบจำนวน token (โดยเฉพาะ token รูป) ของ sample เดียวกัน
ระหว่าง (ก) ตอนเทรนจริงด้วย LLaMA-Factory (dump ใน fold0.log บรรทัด input_ids)
กับ (ข) path ตอน infer (AutoProcessor.apply_chat_template แบบ infer_house_t04.py)
ถ้าไม่เท่ากัน = โมเดลเห็นรูปคนละความละเอียดกับตอนเทรน — CPU ล้วน ไม่แตะ GPU
"""
import json
import re
from pathlib import Path

from PIL import Image
from transformers import AutoProcessor

HERE = Path("/workspace/tune")
p = AutoProcessor.from_pretrained("OpenGVLab/InternVL3-78B-hf", trust_remote_code=True)
tok = p.tokenizer
img_id = tok.convert_tokens_to_ids("<IMG_CONTEXT>")
print("IMG_CONTEXT id:", img_id)

# (ก) training-side: line 404 (1-indexed) ของ fold0.log คือ input_ids ของ sample แรก
lines = (HERE / "fold0.log").read_text(encoding="utf-8", errors="replace").split("\n")
train_ids = None
for i, l in enumerate(lines):
    if l.strip() == "input_ids:":
        train_ids = [int(x) for x in re.findall(r"-?\d+", lines[i + 1])]
        break
print(f"(ก) เทรนจริง:  input_ids = {len(train_ids)} tokens | token รูป = {sum(1 for t in train_ids if t == img_id)}")

# (ข) inference-side: สร้าง msgs แบบเดียวกับ infer_house_t04.generate() เป๊ะ
row = json.loads((HERE / "probe_row.json").read_text(encoding="utf-8"))
parts = []
for c in row["messages"][0]["content"]:
    if c["type"] == "image":
        parts.append({"type": "image", "image": Image.open(HERE / c["image"]).convert("RGB")})
    else:
        parts.append({"type": "text", "text": c["text"]})
msgs = [{"role": "user", "content": parts}]
inputs = p.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True,
                               return_dict=True, return_tensors="pt")
ids = inputs["input_ids"][0].tolist()
print(f"(ข) ตอน infer: input_ids = {len(ids)} tokens | token รูป = {sum(1 for t in ids if t == img_id)}")

# ขนาดรูปดิบ ประกอบการอ่านผล
for c in row["messages"][0]["content"]:
    if c["type"] == "image":
        im = Image.open(HERE / c["image"])
        print(f"    {c['image']}: {im.size[0]}x{im.size[1]} = {im.size[0]*im.size[1]/1e6:.2f} MP")
