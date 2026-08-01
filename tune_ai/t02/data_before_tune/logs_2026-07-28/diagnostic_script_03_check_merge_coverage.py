#!/usr/bin/env python3
"""
orientation ที่ peft คำนวณจริง (ยืนยันจาก shape check รอบก่อน) ถูกต้องอยู่แล้ว —
ตัดสมมติฐาน "ทิศทาง tensor ผิด" ทิ้งไป ตอนนี้เช็คตรงๆ ว่าค่าตัวเลขจริงเปลี่ยนไปหลัง merge ไหม
เทียบ param เดิม (path เดียวกัน) ก่อน/หลัง merge_and_unload() แบบจับคู่ตรงตัว
"""
from peft.tuners.lora.layer import ParamWrapper

MODEL_ID = "unsloth/Qwen3-VL-30B-A3B-Instruct"
ADAPTER_DIR = "outputs_30ba3b/lora"

from unsloth import FastVisionModel
model, tokenizer = FastVisionModel.from_pretrained(MODEL_ID, load_in_4bit=False)
from peft import PeftModel
model = PeftModel.from_pretrained(model, ADAPTER_DIR)

pw_list = [(n, m) for n, m in model.named_modules() if isinstance(m, ParamWrapper)]
print(f"ParamWrapper ทั้งหมดก่อน merge: {len(pw_list)}")
print("merged flag ก่อน merge (ควรเป็น False ทุกตัว):", set(m.merged for _, m in pw_list))

# จับค่า param จริงก่อน merge (ผ่าน get_param() ของ ParamWrapper เอง — วิธีเดียวกับที่ shape check ใช้)
target_pw = None
for n, m in pw_list:
    if n.endswith("layers.0.mlp.experts") and getattr(m, "parameter_name", "") == "down_proj":
        target_pw = m
        target_name = n
        break
if target_pw is None:
    print("หาแบบเงื่อนไขเดิมไม่เจอ พิมพ์ชื่อทั้งหมดดู:")
    for n, m in pw_list[:10]:
        print(f"  {n!r}  param={getattr(m,'parameter_name','?')}")
assert target_pw is not None
before_full = target_pw.get_param().detach().float().cpu().clone()  # tensor เต็ม ไม่ใช่แค่ 5 ตัว
before_val = before_full.flatten()[:5]
print(f"\nค่าจริงก่อน merge ({target_name}, param={target_pw.parameter_name}): {before_val.tolist()}")
print(f"scaling factor ของ adapter นี้: {target_pw.scaling}")
print(f"lora_alpha: {target_pw.lora_alpha}  r: {target_pw.r}")

model = model.merge_and_unload()
print("\nหลัง merge_and_unload():")
print("hasattr peft_config:", hasattr(model, "peft_config"))

pw_after = [(n, m) for n, m in model.named_modules() if isinstance(m, ParamWrapper)]
print(f"ParamWrapper ที่เหลือหลัง merge_and_unload (ควรเป็น 0): {len(pw_after)}")

found = False
for n, p in model.named_parameters():
    if n.endswith("layers.0.mlp.experts.down_proj") or ("layers.0.mlp.experts" in n and "down_proj" in n):
        after_full = p.detach().float().cpu()
        after_val = after_full.flatten()[:5]
        print(f"\nพบ param หลัง merge: {n}  shape={tuple(p.shape)}")
        print(f"ค่าจริงหลัง merge: {after_val.tolist()}")
        print(f"เท่ากับก่อน merge เป๊ะไหม (5 ตัวแรก): {(before_val == after_val).all().item()}")

        diff = (after_full - before_full).abs()
        print(f"\n=== สถิติผลต่างทั้ง tensor ({diff.numel():,} ค่า) ===")
        print(f"mean |diff|: {diff.mean().item():.6f}")
        print(f"max  |diff|: {diff.max().item():.6f}")
        print(f"% ของค่าที่เปลี่ยนไม่เท่ากับ 0 เป๊ะ: {(diff > 0).float().mean().item()*100:.2f}%")
        print(f"mean |before| (สำหรับเทียบสัดส่วน): {before_full.abs().mean().item():.6f}")
        print(f"อัตราส่วน mean|diff| / mean|before|: {(diff.mean() / before_full.abs().mean()).item():.4f}")
        found = True
        break
if not found:
    print("\n⚠️ ไม่เจอ param down_proj ของ layer 0 เลยหลัง merge — ชื่อ path เปลี่ยนไปตอน unload")
