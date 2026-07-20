#!/usr/bin/env python3
"""
eval_fields.py — วัดผลจริงระดับ field ไม่ใช่แค่ eval loss

eval loss ต่ำไม่ได้แปลว่าอ่านเลขเหล็กถูก — บทเรียนข้อ 3 ใน training-data/CLAUDE.md
บอกไว้แล้วว่า confidence/loss ของโมเดลใช้ตัดสินเดี่ยว ๆ ไม่ได้ ต้องนับ field ที่ตรงจริง

    python eval_fields.py [--adapter outputs/lora] [--limit N]
"""
import argparse, json, gc, os
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--adapter", default="outputs/lora")
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--base", action="store_true", help="วัดโมเดลตั้งต้นก่อนทูน (baseline เทียบ)")
args = ap.parse_args()

import torch
from PIL import Image

# ต้องตรงกับ preset ในสคริปต์เทรนที่ใช้จริง — max_pixels/quantization ตอน eval ต้องเท่าตอนเทรน
# MODEL_SIZE=qwen36 = ตัวที่ตัดสินใจใช้จริง (2026-07-20) — 8B/32B เก็บไว้เผื่อกลับมาเทียบ
PRESETS = {
    "8B":     dict(model="unsloth/Qwen3-VL-8B-Instruct-unsloth-bnb-4bit",  max_pixels=5120 * 32 * 32, load_in_4bit=True),
    "32B":    dict(model="unsloth/Qwen3-VL-32B-Instruct-unsloth-bnb-4bit", max_pixels=7680 * 32 * 32, load_in_4bit=True),
    "QWEN36": dict(model="unsloth/Qwen3.6-35B-A3B", max_pixels=5120 * 1024, load_in_4bit=False),  # bf16 — ตระกูลนี้ไม่แนะนำ 4-bit
}
SIZE = os.environ.get("MODEL_SIZE", "QWEN36").upper()
P = PRESETS[SIZE]
src = P["model"] if args.base else args.adapter

try:
    from unsloth import FastVisionModel as UnslothModel
except ImportError:
    from unsloth import FastModel as UnslothModel

model, tokenizer = UnslothModel.from_pretrained(src, load_in_4bit=P["load_in_4bit"])
ip = getattr(tokenizer, "image_processor", None)
if ip is not None:
    ip.max_pixels = P["max_pixels"]
    ip.min_pixels = 256 * 1024
else:
    print("⚠️  tokenizer.image_processor ไม่มี — ความละเอียดภาพอาจไม่ถูกบังคับตามที่ตั้งใจ")
UnslothModel.for_inference(model)

rows = [json.loads(l) for l in open(HERE / "val.jsonl", encoding="utf-8") if l.strip()]
if args.limit:
    rows = rows[: args.limit]

# field ที่สนใจจริง — ตรงกับจุดที่ VLM พลาดบ่อยตามบทเรียนข้อ 2 (CLAUDE.md)
KEY_FIELDS = ["element_id", "element_type", "grid_ref_start", "grid_ref_end",
              "span_length_m", "width_mm", "height_mm", "count"]

def elements_of(obj):
    """ดึง element ทุกตัวจากทุก view พร้อม pattern กำกับ"""
    out = []
    for v in obj.get("views", []) if isinstance(obj, dict) else []:
        for e in (v.get("elements") or v.get("element") or []):
            if isinstance(e, dict):
                out.append(e)
    return out

def key_of(e):
    return (str(e.get("element_id")), str(e.get("grid_ref_start")), str(e.get("grid_ref_end")))

n_valid = 0
agg = defaultdict(lambda: {"hit": 0, "total": 0})
elem_recall = {"found": 0, "expected": 0, "extra": 0}
view_exact = 0

for i, r in enumerate(rows):
    msgs = [{"role": "user", "content": [
        ({"type": "image", "image": Image.open(HERE / c["image"]).convert("RGB")}
         if c["type"] == "image" else {"type": "text", "text": c["text"]})
        for c in r["messages"][0]["content"]]}]
    text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True)
    imgs = [c["image"] for c in msgs[0]["content"] if c["type"] == "image"]
    inputs = tokenizer(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
    out = model.generate(**inputs, max_new_tokens=3000, do_sample=False)
    pred_txt = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    del inputs, out
    gc.collect(); torch.cuda.empty_cache()

    gold = json.loads(r["messages"][1]["content"][0]["text"])
    try:
        pred = json.loads(pred_txt)
        n_valid += 1
    except Exception:
        print(f"  [{i+1}/{len(rows)}] {r['id'].split('::')[-1]}: JSON เสีย")
        elem_recall["expected"] += len(elements_of(gold))
        continue

    if len(pred.get("views", [])) == len(gold.get("views", [])):
        view_exact += 1

    ge, pe = elements_of(gold), elements_of(pred)
    pmap = {key_of(e): e for e in pe}
    elem_recall["expected"] += len(ge)
    elem_recall["extra"] += max(0, len(pe) - len(ge))
    for g in ge:
        p = pmap.get(key_of(g))
        if p is None:
            continue
        elem_recall["found"] += 1
        for f in KEY_FIELDS:
            if f in g:
                agg[f]["total"] += 1
                if g.get(f) == p.get(f):
                    agg[f]["hit"] += 1
    print(f"  [{i+1}/{len(rows)}] {r['id'].split('::')[-1]}: "
          f"element {len(pe)}/{len(ge)} | view {len(pred.get('views',[]))}/{len(gold.get('views',[]))}")

n = len(rows)
print("\n" + "=" * 58)
print(f"โมเดล: {'BASE (ก่อนทูน)' if args.base else src}")
print(f"JSON valid           : {n_valid}/{n}  ({100*n_valid/n:.1f}%)")
print(f"จำนวน view ตรงเป๊ะ    : {view_exact}/{n}  ({100*view_exact/n:.1f}%)")
er = elem_recall
print(f"element หาเจอ        : {er['found']}/{er['expected']}  "
      f"({100*er['found']/max(1,er['expected']):.1f}%)   เกินมา {er['extra']} ตัว")
print("\nfield exact-match (นับเฉพาะ element ที่จับคู่ได้):")
for f in KEY_FIELDS:
    a = agg[f]
    if a["total"]:
        print(f"  {f:<18} {a['hit']:>4}/{a['total']:<4} {100*a['hit']/a['total']:>5.1f}%")
print("=" * 58)
print("อ่านผลยังไง: element recall ต่ำ = โมเดลมองข้ามของ (ปัญหาที่เจอบ่อยสุดในชุดนี้)")
print("             span_length_m ผิด = อ่าน grid ไม่ตรง | width/height ผิด = อ่านเลขเล็กไม่ออก")
