#!/usr/bin/env python3
"""
infer_t02_grammar.py — เหมือน infer_t02.py ทุกอย่าง (โหลด/ตั้งค่า/prompt เดียวกัน
เป๊ะ ห้ามเปลี่ยน ดูคอมเมนต์ในไฟล์นั้น) ต่างแค่บังคับ output ด้วย
grammar-constrained decoding (lm-format-enforcer) ให้เป็น JSON ที่ syntax ถูกเสมอ
— แก้ปัญหา key ซ้ำ/string ไม่ปิด/comma ขาดที่เจอจาก infer_t02.py ธรรมดา

บังคับแค่ "เป็น JSON object ที่ valid" (schema: {"type":"object"}) ไม่ผูกกับ
primary_rawjson_schema เต็มรูปแบบ — เพราะ schema จริงซับซ้อนมาก (nested,
optional fields หลายแบบ) ผูกเข้าไปเสี่ยงบีบให้โมเดล generate ผิดทิศทางกว่าเดิม
ถ้า generic JSON ได้ผลดีค่อยลองผูก schema เต็มทีหลัง

    python3 infer_t02_grammar.py --image /path/to/drawing.png
"""
import argparse, json, os
from pathlib import Path

HERE = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True)
ap.add_argument("--adapter", default="Sicilian44/qwen3vl-30b-thai-rc")
ap.add_argument("--subfolder", default="lora-adapter")
ap.add_argument("--prompt-file", default=None)
ap.add_argument("--max-new-tokens", type=int, default=3000)
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

if args.prompt_file:
    prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
else:
    first_row = json.loads(next(open(HERE / "val.jsonl", encoding="utf-8")))
    prompt_text = next(c["text"] for c in first_row["messages"][0]["content"] if c["type"] == "text")

img = Image.open(args.image).convert("RGB")
msgs = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": prompt_text}]}]

text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
inputs = tokenizer([img], text, add_special_tokens=False, return_tensors="pt").to("cuda")

# grammar constraint — บังคับแค่ "valid JSON object" ไม่ผูก schema เต็ม (ดูเหตุผลหัวไฟล์)
# lm-format-enforcer 0.11.3 ยัง import `PreTrainedTokenizerBase` จาก
# transformers.tokenization_utils ซึ่งย้ายไปแล้วใน transformers 5.x — shim path เดิมไว้ก่อน import
import transformers.tokenization_utils as _tu
if not hasattr(_tu, "PreTrainedTokenizerBase"):
    import transformers as _tf
    _tu.PreTrainedTokenizerBase = _tf.PreTrainedTokenizerBase
from lmformatenforcer import JsonSchemaParser
from lmformatenforcer.integrations.transformers import build_transformers_prefix_allowed_tokens_fn
# จงใจใช้ {"type":"object"} เปล่า — lm-format-enforcer 0.11.3 ปิด key set ทันทีที่ schema
# ประกาศ properties (ไม่เคารพ additionalProperties ทุกรูปแบบ — probe จริง 2026-08-21) ทำให้
# schema เข้มอย่าง rawjson_infer_schema.json ใช้ไม่ได้กับไลบรารีนี้; ไฟล์นั้นเก็บรอไลบรารี
# ที่รองรับ, ตัวเช็คสถานะอยู่ที่ test_infer_schema.py (canary)
parser = JsonSchemaParser({"type": "object"})
# tokenizer ที่ UnslothModel.from_pretrained คืนมาคือ Qwen3VLProcessor (multimodal
# wrapper) ไม่ใช่ tokenizer ตรงๆ — lm-format-enforcer ต้องการ PreTrainedTokenizerBase
# จริง ต้องแกะ .tokenizer (Qwen2Tokenizer) ออกมาก่อน
prefix_fn = build_transformers_prefix_allowed_tokens_fn(tokenizer.tokenizer, parser)

out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                      repetition_penalty=1.15, no_repeat_ngram_size=8,
                      prefix_allowed_tokens_fn=prefix_fn)
pred_txt = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

print("\n" + "=" * 58)
# lm-format-enforcer อนุญาต trailing comma ก่อน } โดย design (ObjectParsingStage.PARSING_KEY_OR_END:
# หลัง ',' จะยอม '}' เสมอเมื่อ schema ไม่มี required keys — ยืนยันจาก source 2026-08-21) แต่
# json.loads เข้มกว่า — ลบทิ้งก่อน parse
# ponytail: regex ธรรมดา ไม่รู้จัก string boundary — ",}" ที่อยู่ในเนื้อ string โดนลบด้วย (โอกาสน้อยมาก);
# ถ้าเจอจริงค่อยเปลี่ยนเป็น json5/tolerant parser
import re
pred_txt = re.sub(r",(\s*[}\]])", r"\1", pred_txt)
try:
    parsed = json.loads(pred_txt)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
except Exception:
    print("⚠️  ผลลัพธ์ไม่ใช่ JSON ที่ parse ได้ — พิมพ์ดิบ:")
    print(pred_txt)
