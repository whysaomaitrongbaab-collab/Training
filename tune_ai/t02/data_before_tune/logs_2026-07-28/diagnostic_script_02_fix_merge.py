#!/usr/bin/env python3
"""
peft's ParamWrapper.get_delta_weight() guesses tensor orientation via a heuristic
(`is_transposed` attribute lookup on the base layer, defaulting False) — for Qwen3-VL-MoE
this default may be wrong, silently producing a wrong-shaped/wrong-orientation delta that
still "adds" without error (broadcastable) but corrupts the weights.

Plan: check param.shape vs both possible einsum output shapes directly — shape itself proves
which orientation is structurally correct (no guessing). Apply the correct one manually,
verify generation output matches the known-good pre-merge output.
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
print("adapter attached")

# หา ParamWrapper module ตัวแรก มาตรวจ shape จริง (ไม่กรองชื่อ path — parameter_name อยู่ข้างใน object)
from peft.tuners.lora.layer import ParamWrapper
pw = None
pw_name = None
all_pw_names = []
for name, mod in model.named_modules():
    if isinstance(mod, ParamWrapper):
        all_pw_names.append((name, getattr(mod, "parameter_name", "?")))
        if pw is None:
            pw = mod
            pw_name = name
print(f"เจอ ParamWrapper ทั้งหมด {len(all_pw_names)} ตัว ตัวอย่าง 5 แรก:")
for n, p in all_pw_names[:5]:
    print(f"  module={n}  parameter_name={p}")
assert pw is not None, "หา ParamWrapper ไม่เจอเลยแม้แต่ตัวเดียว — โครงสร้าง PeftModel อาจเปลี่ยนไป"
print(f"\nตรวจ module: {pw_name}")
print("_did_swap_in_out_features:", pw._did_swap_in_out_features)
print("in_features/out_features (หลัง swap แล้วถ้ามี):", pw.in_features, pw.out_features)

param = pw.get_param()
print("param.shape จริง:", tuple(param.shape))
print("num_experts:", pw.num_experts)

adapter_name = list(pw.lora_A.keys())[0]
weight_A = pw.lora_A[adapter_name].weight
weight_B = pw.lora_B[adapter_name].weight
print("weight_A.shape:", tuple(weight_A.shape), " weight_B.shape:", tuple(weight_B.shape))

wA = weight_A.reshape(pw.num_experts, -1, weight_A.shape[-1])
wB = weight_B.reshape(weight_B.shape[0], -1, pw.num_experts)
print("wA (reshaped):", tuple(wA.shape), " wB (reshaped):", tuple(wB.shape))

delta_a = torch.einsum("o r e, e r i -> e i o", wB, wA)  # 'not swapped' orientation
delta_b = torch.einsum("o r e, e r i -> e o i", wB, wA)  # 'swapped' orientation
print("\norientation A (e i o) shape:", tuple(delta_a.shape))
print("orientation B (e o i) shape:", tuple(delta_b.shape))
print("param.shape                :", tuple(param.shape))
print("orientation A matches param.shape:", tuple(delta_a.shape) == tuple(param.shape))
print("orientation B matches param.shape:", tuple(delta_b.shape) == tuple(param.shape))
