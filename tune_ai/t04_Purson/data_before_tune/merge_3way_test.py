#!/usr/bin/env python3
"""3-way merge smoke test: fold1-weights + fold3-weights + fold4-weights (equal weight linear soup)
มะขามเคาะ 2026-08-30: "รอfold4จบลองผสมของทั้ง3อันดูแบบ k factor" -> ผสมก่อนรอ fold2(instance fold1) เสร็จ
"""
import torch
from transformers import AutoModelForImageTextToText, BitsAndBytesConfig
from peft import PeftModel

BASE = "OpenGVLab/InternVL3-78B-hf"
ADAPTERS = {
    "f1": "Sicilian44/Purson-fold1-weights",
    "f3": "Sicilian44/Purson-fold3-weights",
    "f4": "Sicilian44/Purson-fold4-weights",
}
OUT_DIR = "/workspace/tune/merge_3way_test"

print("=== loading base model (4-bit) ===")
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
base = AutoModelForImageTextToText.from_pretrained(BASE, quantization_config=bnb, device_map="auto", trust_remote_code=True)

print("=== loading adapter f1 ===")
model = PeftModel.from_pretrained(base, ADAPTERS["f1"], adapter_name="f1")
print("=== loading adapter f3 ===")
model.load_adapter(ADAPTERS["f3"], adapter_name="f3")
print("=== loading adapter f4 ===")
model.load_adapter(ADAPTERS["f4"], adapter_name="f4")

print("=== merging (linear, equal weight 1/3 each) ===")
model.add_weighted_adapter(
    adapters=["f1", "f3", "f4"],
    weights=[1 / 3, 1 / 3, 1 / 3],
    adapter_name="soup3_test",
    combination_type="linear",
)
model.set_adapter("soup3_test")

print(f"=== saving merged adapter to {OUT_DIR} ===")
model.save_pretrained(OUT_DIR, selected_adapters=["soup3_test"])

print("=== DONE — 3-way merge test complete ===")
