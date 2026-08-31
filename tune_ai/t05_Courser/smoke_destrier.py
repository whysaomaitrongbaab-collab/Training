#!/usr/bin/env python3
"""
smoke_destrier.py — พิสูจน์ว่า destrier (soup 3 fold) โหลดได้จริง + อ่านแบบได้จริง ก่อนคืนการ์ดใบสุดท้าย

ออกแบบตาม rule_of_tune Lesson 16 (probe ห้ามมีเฉลยในตัว):
  - พรอมต์ = ข้อความเดิมจาก val row เป๊ะ ไม่เติมตัวอย่าง mark ใด ๆ
  - ทดสอบ ≥2 หน้า **ต่างกัน** และ output ต้อง**ต่างกัน** (เหมือนกัน = ไม่ได้มองภาพ)
  - นับ hit จาก GT ของแถวนั้นเอง (marks ที่ปรากฏใน assistant turn) ไม่ใช่ list ที่คนเขียนเดา
  - มี control ง่าย 1 หน้า (gridline — แค่อ่านเส้นกริด)

ต้องรันด้วย /workspace/infer_env/bin/python (peft 0.20 — convention เดียวกับ destrier
ห้ามใช้ python ระบบซึ่งเป็น peft 0.18.1 คนละ convention ชั้น MoE = ขยะเงียบ ๆ)
"""
import json
import os
import re
import sys

import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

BASE = "unsloth/Qwen3.6-35B-A3B"
ADAPTER = "dacarokann/destrier"          # โหลดจาก HF = ตรวจไฟล์บน HF ไปในตัว
DATA_DIR = "/workspace/Training/tune_ai/t05_Courser"
REPO_ROOT = "/workspace/Training"        # path รูปใน jsonl เทียบรากรีโป (ดู train_t05_courser.py:48)
MAX_PIXELS = 6912 * 1024                 # ตรงกับตอนเทรน (หลังแก้ OOM)
MAX_NEW = 4096
# เลือก subtask ต่างชนิดกัน: control ง่าย (gridline) + งานจริง (plan_beam ถ้ามี)
WANT = ["gridline", "plan_beam", "notes"]


def pick_rows():
    rows = [json.loads(l) for l in open(os.path.join(DATA_DIR, "val_fold0.jsonl"))]
    picked = []
    for st in WANT:
        r = next((x for x in rows if x["subtask"] == st), None)
        if r:
            picked.append(r)
    return picked[:3]


def gt_text(row):
    for m in row["messages"]:
        if m["role"] == "assistant":
            c = m["content"]
            return c if isinstance(c, str) else " ".join(
                p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def gt_marks(gt):
    """ดึง mark จาก GT: ค่า string สั้น ๆ ของคีย์ mark/name ใน JSON GT"""
    marks = set()
    for m in re.finditer(r'"(?:mark|name|grid_ref)"\s*:\s*"([^"]{1,12})"', gt):
        marks.add(m.group(1))
    return marks


def main():
    print(f"โหลด base {BASE} …", flush=True)
    model = AutoModelForImageTextToText.from_pretrained(BASE, dtype="auto", device_map="auto")
    processor = AutoProcessor.from_pretrained(BASE)
    ip = getattr(processor, "image_processor", None)
    if ip is not None and hasattr(ip, "max_pixels"):
        ip.max_pixels = MAX_PIXELS  # ให้เห็นภาพละเอียดเท่าตอนเทรน (Lesson 15)
        print(f"   max_pixels = {ip.max_pixels}")
    print(f"โหลด adapter {ADAPTER} จาก HF …", flush=True)
    model = PeftModel.from_pretrained(model, ADAPTER)
    model.eval()

    outs = []
    for row in pick_rows():
        st = row["subtask"]
        user = [m for m in row["messages"] if m["role"] == "user"]
        # path รูปใน jsonl เป็น relative — เปลี่ยนเป็น absolute
        for m in user:
            for p in m["content"]:
                if isinstance(p, dict) and p.get("type") == "image":
                    p["image"] = os.path.join(REPO_ROOT, p["image"])
        kw = dict(add_generation_prompt=True, tokenize=True,
                  return_dict=True, return_tensors="pt")
        try:
            inputs = processor.apply_chat_template(user, enable_thinking=False, **kw)
        except TypeError:
            inputs = processor.apply_chat_template(user, **kw)
        inputs = inputs.to(model.device)
        n_in = inputs["input_ids"].shape[-1]
        print(f"\n=== {st} ({row['id'].split('::')[1]}) — input {n_in} tokens ===", flush=True)
        with torch.no_grad():
            g = model.generate(**inputs, max_new_tokens=MAX_NEW, do_sample=False)
        txt = processor.decode(g[0][n_in:], skip_special_tokens=True)
        txt = re.sub(r"^```(?:json)?|```$", "", txt.strip()).strip()
        outs.append((st, txt))

        gt = gt_text(row)
        marks = gt_marks(gt)
        hit = {m for m in marks if m in txt}
        try:
            json.loads(re.sub(r",(\s*[}\]])", r"\1", txt))
            jok = "valid"
        except Exception as e:
            jok = f"เสีย ({e})"
        print(f"   ยาว {len(txt)} ตัวอักษร · JSON {jok}")
        print(f"   GT marks {len(marks)} ตัว → เจอในคำตอบ {len(hit)}: {sorted(hit)[:15]}")
        print(f"   ตัวอย่างคำตอบ 300 ตัวแรก: {txt[:300]}")

    # Lesson 16 ข้อ 2: คำตอบทุกหน้าต้องต่างกัน
    texts = [t for _, t in outs]
    if len(texts) >= 2 and len(set(texts)) == 1:
        print("\n⛔ FAIL: ทุกหน้าตอบเหมือนกันเป๊ะ — โมเดลไม่ได้มองภาพ")
        return 1
    print(f"\n✅ คำตอบ {len(texts)} หน้าต่างกันจริง — สรุปผลด้านบนต่อหน้า")
    return 0


if __name__ == "__main__":
    sys.exit(main())
