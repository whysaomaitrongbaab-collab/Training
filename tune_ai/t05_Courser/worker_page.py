#!/usr/bin/env python3
"""
worker_page.py — สร้าง output 1 หน้า/1 แถวต่อ 1 process แล้วจบ ให้ตัวคุมนอก (bash timeout) ฆ่าทิ้งได้
สะอาดถ้าเกิน 25 นาที โดยไม่ต้องเล่น thread/signal ตัดกลาง generate() ในโพรเซสเดียวกัน

มะขามสั่ง 2026-08-31: "ถ้าหน้าไหนเกิน 25 นาทีให้ใช้ xgrammar เลย" — ตัวคุม (run_queue.sh)
เรียกตัวนี้ผ่าน `timeout 1500`, ถ้า exit 124 (timeout) ก็เรียกซ้ำโดยเติม --xgrammar

ใช้ได้ 2 โหมด:
  --source val:<subtask>        อ่านจาก val_fold0.jsonl (สำหรับ smoke test)
  --source house:<page_num>     อ่านจาก test_house_new (สำหรับ pure-power test)
"""
import argparse
import json
import os
import re
import sys

import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

BASE = "unsloth/Qwen3.6-35B-A3B"
ADAPTER = "dacarokann/destrier"
MAX_PIXELS = 6912 * 1024
MAX_NEW = 4096
COURSER_DIR = "/workspace/Training/tune_ai/t05_Courser"
HOUSE_DIR = "/workspace/Training/tune_ai/t04_Purson/test_house_new/image_บ้านไทยพอเพียง3"
REPO_ROOT = "/workspace/Training"

PROMPT_CORE_PATH = os.path.join(os.path.dirname(__file__), "..", "t04_Purson",
                                 "test_house_new", "_prompt_core.txt")


def load_val_row(subtask):
    for l in open(os.path.join(COURSER_DIR, "val_fold0.jsonl")):
        r = json.loads(l)
        if r["subtask"] == subtask:
            return r
    raise SystemExit(f"⛔ ไม่พบ subtask {subtask} ใน val_fold0.jsonl")


def build_messages_val(row):
    user = [m for m in row["messages"] if m["role"] == "user"]
    for m in user:
        for p in m["content"]:
            if isinstance(p, dict) and p.get("type") == "image":
                p["image"] = os.path.join(REPO_ROOT, p["image"])
    return user, row["id"]


def build_messages_house(page_num):
    import glob
    hits = glob.glob(os.path.join(HOUSE_DIR, f"*_หน้า{int(page_num):02d}.png"))
    if not hits:
        raise SystemExit(f"⛔ ไม่พบหน้า {page_num} ใน {HOUSE_DIR}")
    prompt = open(PROMPT_CORE_PATH, encoding="utf-8").read()
    msgs = [{"role": "user", "content": [
        {"type": "image", "image": hits[0]},
        {"type": "text", "text": prompt},
    ]}]
    return msgs, os.path.basename(hits[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="val:<subtask> หรือ house:<page_num>")
    ap.add_argument("--xgrammar", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    kind, key = args.source.split(":", 1)
    if kind == "val":
        row = load_val_row(key)
        messages, label = build_messages_val(row)
    elif kind == "house":
        messages, label = build_messages_house(key)
    else:
        raise SystemExit(f"⛔ --source ต้องขึ้นต้นด้วย val: หรือ house: ได้ {args.source}")

    print(f"โหลด base {BASE} …", flush=True)
    model = AutoModelForImageTextToText.from_pretrained(BASE, dtype="auto", device_map="auto")
    processor = AutoProcessor.from_pretrained(BASE)
    ip = getattr(processor, "image_processor", None)
    if ip is not None and hasattr(ip, "max_pixels"):
        ip.max_pixels = MAX_PIXELS
    print(f"โหลด adapter {ADAPTER} …", flush=True)
    model = PeftModel.from_pretrained(model, ADAPTER)
    model.eval()

    gen_kwargs = dict(max_new_tokens=MAX_NEW, do_sample=False)
    if args.xgrammar:
        import xgrammar as xgr
        from xgrammar.contrib.hf import LogitsProcessor
        tok = getattr(processor, "tokenizer", processor)
        config = xgr.GrammarCompiler(
            xgr.TokenizerInfo.from_huggingface(tok, vocab_size=model.config.get_text_config().vocab_size))
        grammar = config.compile_builtin_json_grammar()  # bare JSON grammar — Lesson 13 addendum: safe default
        gen_kwargs["logits_processor"] = [LogitsProcessor(grammar)]
        print("   [xgrammar] เปิด builtin JSON grammar", flush=True)

    kw = dict(add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
    try:
        inputs = processor.apply_chat_template(messages, enable_thinking=False, **kw)
    except TypeError:
        inputs = processor.apply_chat_template(messages, **kw)
    inputs = inputs.to(model.device)
    n_in = inputs["input_ids"].shape[-1]
    print(f"=== {args.source} ({label}) — input {n_in} tokens · xgrammar={args.xgrammar} ===", flush=True)

    with torch.no_grad():
        g = model.generate(**inputs, **gen_kwargs)
    txt = processor.decode(g[0][n_in:], skip_special_tokens=True)
    txt = re.sub(r"^```(?:json)?|```$", "", txt.strip()).strip()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    open(args.out, "w", encoding="utf-8").write(txt)

    cleaned = re.sub(r",(\s*[}\]])", r"\1", txt)
    try:
        obj = json.loads(cleaned)
        jok, pattern = "valid", obj.get("pattern")
    except Exception as e:
        jok, pattern = f"เสีย ({e})", "?"
    print(f"   ยาว {len(txt)} ตัวอักษร · JSON {jok} · pattern={pattern}")
    print(f"   ตัวอย่าง 300 ตัวแรก: {txt[:300]}")
    print("DONE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
