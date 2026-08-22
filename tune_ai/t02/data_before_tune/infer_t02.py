#!/usr/bin/env python3
"""
infer_t02.py — รัน t02 (LoRA adapter บน HF: Sicilian44/qwen3vl-30b-thai-rc)
บนภาพแบบใหม่ที่ไม่ได้อยู่ใน val.jsonl (production use, ไม่ใช่ eval)

โหลด base+adapter ผ่าน transformers/PEFT (ไม่ใช่ GGUF — t02 export GGUF ไม่ได้ ดู
t02_workflow.md หัวเอกสาร) วิธีโหลด/ตั้งค่าภาพ/enable_thinking=False ก็อปมาจาก
eval_fields.py ตรงๆ เพื่อให้พฤติกรรมตรงกับตอนวัดผล (ห้ามเปลี่ยน — ไม่งั้นผลไม่ตรงกับที่วัดไว้)

prompt ดึงจาก val.jsonl แถวแรกเพื่อไม่ให้พิมพ์ผิดเพี้ยนจากตอนเทรน (ทุกแถวใช้ prompt เดียวกัน)

    python3 infer_t02.py --image /path/to/drawing.png
    python3 infer_t02.py --image page.png --prompt-file custom_prompt.txt
"""
import argparse, json, os
from pathlib import Path

HERE = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True, help="path รูปแบบก่อสร้างที่จะอ่าน")
ap.add_argument("--adapter", default="Sicilian44/qwen3vl-30b-thai-rc",
                help="HF repo หรือ path local ของ adapter (default = t02 บน HF)")
ap.add_argument("--subfolder", default="lora-adapter",
                help="adapter files ไม่ได้อยู่ที่ root ของ repo — ตรวจแล้ว 2026-08-20 ว่าอยู่ใต้ lora-adapter/")
ap.add_argument("--prompt-file", default=None,
                help="ไฟล์ .txt ของ instruction prompt (default: ดึงจาก val.jsonl แถวแรก)")
ap.add_argument("--max-new-tokens", type=int, default=3000)
args = ap.parse_args()

import torch
from PIL import Image

try:
    from unsloth import FastVisionModel as UnslothModel
except ImportError:
    from unsloth import FastModel as UnslothModel

# Unsloth's from_pretrained ไม่ forward kwarg `subfolder` ไปยัง AutoConfig/PeftConfig
# ภายใน — โหลดไฟล์ลง local ก่อนแล้วชี้ path ตรง (ดู run_house_batch.py คอมเมนต์เดียวกัน)
adapter_path = args.adapter
if not os.path.isdir(args.adapter):
    from huggingface_hub import snapshot_download
    local_dir = snapshot_download(repo_id=args.adapter, allow_patterns=[f"{args.subfolder}/*"])
    adapter_path = os.path.join(local_dir, args.subfolder)
model, tokenizer = UnslothModel.from_pretrained(adapter_path, load_in_4bit=False)

# ต้องตั้งเท่าตอนเทรน/eval เป๊ะ (5120 tokens/ภาพ) — ดู bug 2 ใน t02_workflow.md §0.4
ip = getattr(tokenizer, "image_processor", None)
if ip is not None:
    ip.size["longest_edge"] = 5120 * 1024
    ip.size["shortest_edge"] = 256 * 1024
    print(f"image processor: {ip.size['longest_edge'] // 1024} visual tokens/ภาพ (ต้องเท่าตอนเทรน)")
else:
    print("⚠️  tokenizer.image_processor ไม่มี — ความละเอียดภาพอาจไม่ถูกบังคับตามที่ตั้งใจ")
UnslothModel.for_inference(model)

if args.prompt_file:
    prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
else:
    first_row = json.loads(next(open(HERE / "val.jsonl", encoding="utf-8")))
    prompt_text = next(c["text"] for c in first_row["messages"][0]["content"] if c["type"] == "text")

img = Image.open(args.image).convert("RGB")
msgs = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": prompt_text}]}]

# enable_thinking=False required — ดู eval_fields.py บรรทัดเดียวกัน ไม่งั้นโมเดลเขียน
# chain-of-thought ยาวจนหมด token budget ก่อนถึง JSON (bug 4, t02_workflow.md §0.4)
text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
inputs = tokenizer([img], text, add_special_tokens=False, return_tensors="pt").to("cuda")
out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                      repetition_penalty=1.15, no_repeat_ngram_size=8)
pred_txt = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

print("\n" + "=" * 58)
try:
    parsed = json.loads(pred_txt)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
except Exception:
    print("⚠️  ผลลัพธ์ไม่ใช่ JSON ที่ parse ได้ — พิมพ์ดิบ:")
    print(pred_txt)
