#!/usr/bin/env python3
"""
infer_t02_xgrammar.py — twin ของ infer_t02_grammar.py แต่ใช้ xgrammar เป็น backend
(โหลดโมเดล/ตั้งค่าภาพ/prompt เหมือนกันเป๊ะ — ห้ามเปลี่ยน ดู infer_t02.py)

ทำไมต้องมี twin (สรุปผลสืบ 2026-08-21, รายละเอียด rule_of_tune.md ข้อ 13):
- lm-format-enforcer 0.11.3: ยอม trailing comma (ต้อง regex เก็บ) + ปิด key set ถ้าประกาศ
  properties → ใช้ schema เข้มไม่ได้
- xgrammar 0.2.3 (probe จริง): grammar ผลิต trailing comma ไม่ได้เลย, รองรับ
  additionalProperties จริง (เปิด key อิสระ + กัน key ซ้ำให้ด้วย), มี LogitsProcessor
  สำเร็จรูป (xgr.contrib.hf) — ดีกว่าทุกข้อ **แต่ยังไม่เคยรันบน GPU จริง**
  → ไฟล์นี้คือตัวทดลองสำหรับรอบเช่าหน้า, ตัวที่พิสูจน์แล้วคือ infer_t02_grammar.py

⚠️ กับดักของ xgrammar ที่ probe เจอ: key ใน `properties` ถูกบังคับ "ลำดับตาม schema"
และห้ามโผล่ซ้ำในโซน additionalProperties — ถ้า schema เรียง key ไม่ตรงกับลำดับที่โมเดล
พิมพ์จริง จะ deadlock กลาง generate. default จึงใช้ builtin JSON grammar (ไม่มี schema,
ปลอดภัย 100%); จะทดลอง schema ให้ส่ง --schema-file และรับความเสี่ยงเอง

    python3 infer_t02_xgrammar.py --image page.png
    python3 infer_t02_xgrammar.py --image page.png --schema-file rawjson_infer_schema.json
"""
import argparse, json, os, re
from pathlib import Path

HERE = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True)
ap.add_argument("--adapter", default="Sicilian44/qwen3vl-30b-thai-rc")
ap.add_argument("--subfolder", default="lora-adapter")
ap.add_argument("--prompt-file", default=None)
ap.add_argument("--max-new-tokens", type=int, default=3000)
ap.add_argument("--schema-file", default=None,
                help="JSON schema (เสี่ยง deadlock ถ้าลำดับ key ไม่ตรงโมเดล — อ่านหัวไฟล์)")
args = ap.parse_args()

import torch
from PIL import Image

try:
    from unsloth import FastVisionModel as UnslothModel
except ImportError:
    from unsloth import FastModel as UnslothModel

adapter_path = args.adapter
if not os.path.isdir(args.adapter):
    from huggingface_hub import snapshot_download
    local_dir = snapshot_download(repo_id=args.adapter, allow_patterns=[f"{args.subfolder}/*"])
    adapter_path = os.path.join(local_dir, args.subfolder)
model, tokenizer = UnslothModel.from_pretrained(adapter_path, load_in_4bit=False)

ip = getattr(tokenizer, "image_processor", None)
if ip is not None:
    ip.size["longest_edge"] = 5120 * 1024
    ip.size["shortest_edge"] = 256 * 1024
    print(f"image processor: {ip.size['longest_edge'] // 1024} visual tokens/ภาพ (ต้องเท่าตอนเทรน)")
UnslothModel.for_inference(model)

import xgrammar as xgr

# vocab_size ต้องเป็นของโมเดล (รวม padding) ไม่ใช่ len(tokenizer) — กับดักที่ xgrammar docs เตือนเอง
cfg = model.config
vocab_size = getattr(cfg, "vocab_size", None)
if vocab_size is None and hasattr(cfg, "text_config"):
    vocab_size = cfg.text_config.vocab_size
print(f"vocab_size จาก config: {vocab_size}")

# tokenizer จริงอยู่ใต้ processor wrapper (บทเรียนเดียวกับ infer_t02_grammar.py)
tok_info = xgr.TokenizerInfo.from_huggingface(tokenizer.tokenizer, vocab_size=vocab_size)
compiler = xgr.GrammarCompiler(tok_info)
if args.schema_file:
    compiled = compiler.compile_json_schema(Path(args.schema_file).read_text(encoding="utf-8"))
    print(f"grammar: schema {args.schema_file}")
else:
    compiled = compiler.compile_builtin_json_grammar()
    print("grammar: builtin JSON (ไม่มี schema)")

if args.prompt_file:
    prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
else:
    first_row = json.loads(next(open(HERE / "val.jsonl", encoding="utf-8")))
    prompt_text = next(c["text"] for c in first_row["messages"][0]["content"] if c["type"] == "text")

img = Image.open(args.image).convert("RGB")
msgs = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": prompt_text}]}]

text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
inputs = tokenizer([img], text, add_special_tokens=False, return_tensors="pt").to("cuda")

# LogitsProcessor ของ xgrammar เป็น stateful — สร้างใหม่ทุกครั้งที่ generate
proc = xgr.contrib.hf.LogitsProcessor(compiled)
out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                      repetition_penalty=1.15, no_repeat_ngram_size=8,
                      logits_processor=[proc])
pred_txt = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

print("\n" + "=" * 58)
# builtin JSON grammar ผลิต trailing comma ไม่ได้อยู่แล้ว — คง regex ไว้เป็นเข็มขัดนิรภัย
# เผื่อสลับ backend/grammar (1 บรรทัด ไม่มีต้นทุน)
pred_txt = re.sub(r",(\s*[}\]])", r"\1", pred_txt)
try:
    parsed = json.loads(pred_txt)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
except Exception:
    print("⚠️  ผลลัพธ์ไม่ใช่ JSON ที่ parse ได้ — พิมพ์ดิบ:")
    print(pred_txt)
