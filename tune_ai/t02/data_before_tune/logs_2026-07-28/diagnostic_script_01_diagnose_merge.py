#!/usr/bin/env python3
"""
วินิจฉัยว่า merge_and_unload() ทำลาย LoRA ที่แปะบน MoE experts (target_parameters) จริงไหม
เทียบ output ก่อน-หลัง merge บนตัวอย่างเดียวกัน ไม่ต้องเดา
"""
import json, gc
from pathlib import Path
from PIL import Image
import torch

MODEL_ID = "unsloth/Qwen3-VL-30B-A3B-Instruct"
ADAPTER_DIR = "outputs_30ba3b/lora"
HERE = Path("/workspace/tune/data_before_tune")

from unsloth import FastVisionModel
model, tokenizer = FastVisionModel.from_pretrained(MODEL_ID, load_in_4bit=False)

from peft import PeftModel
model = PeftModel.from_pretrained(model, ADAPTER_DIR)
print("adapter attached via peft.PeftModel.from_pretrained")

# ดึงตัวอย่างเดียวกับที่ export_gguf.py ใช้ (val.jsonl index 2)
with open(HERE / "val.jsonl", encoding="utf-8") as f:
    lines = f.readlines()
sample = json.loads(lines[2])
msgs = [sample["messages"][0]]
text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
imgs = [Image.open(HERE / c["image"]).convert("RGB") for c in msgs[0]["content"] if c["type"] == "image"]

def gen(label):
    FastVisionModel.for_inference(model)
    inputs = tokenizer(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
    out = model.generate(**inputs, max_new_tokens=400, do_sample=False)
    pred = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"\n=== {label} ===")
    print(pred[:400])
    del inputs, out
    gc.collect(); torch.cuda.empty_cache()
    return pred

pred_before = gen("ก่อน merge (PeftModel adapter attached)")

# หา expert weight tensor ตัวหนึ่งมาเทียบค่าจริงก่อน/หลัง merge (ไม่เดา วัดตรงๆ)
sample_param_name = None
for name, _ in model.named_parameters():
    if "experts.gate_up_proj" in name:
        sample_param_name = name
        break
print(f"\nตรวจ tensor: {sample_param_name}")
before_val = dict(model.named_parameters())[sample_param_name].detach().float().cpu().flatten()[:5].clone()
print(f"ค่า 5 ตัวแรกก่อน merge: {before_val.tolist()}")

print("\nกำลัง merge_and_unload() ...")
model = model.merge_and_unload()
assert not hasattr(model, "peft_config"), "merge ไม่สำเร็จ"
print("✓ merge_and_unload() เสร็จ ไม่มี peft_config เหลือ")

# หา tensor ชื่อเดียวกัน (หรือใกล้เคียง) หลัง merge มาเทียบ
after_name_candidates = [n for n, _ in model.named_parameters() if "experts.gate_up_proj" in n]
if after_name_candidates:
    after_name = after_name_candidates[0]
    after_val = dict(model.named_parameters())[after_name].detach().float().cpu().flatten()[:5].clone()
    print(f"ตรวจ tensor หลัง merge: {after_name}")
    print(f"ค่า 5 ตัวแรกหลัง merge: {after_val.tolist()}")
    print(f"เท่ากับก่อน merge เป๊ะไหม (ถ้าเท่ากัน = merge ไม่ได้เปลี่ยนอะไรเลย = พังแน่นอน): {torch.allclose(before_val, after_val)}")
else:
    print("ไม่เจอ expert param ชื่อเดิมหลัง merge — โครงสร้างเปลี่ยนไปเป็นปกติของการ merge")

pred_after = gen("หลัง merge (merge_and_unload)")

print("\n=== สรุป ===")
print("before startswith gold-like keys (png/views/doc_page):", any(k in pred_before[:400] for k in ('"png"', '"views"', '"pattern"', '"doc_page"')))
print("after  startswith gold-like keys (png/views/doc_page):", any(k in pred_after[:400] for k in ('"png"', '"views"', '"pattern"', '"doc_page"')))
