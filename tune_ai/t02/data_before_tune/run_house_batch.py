#!/usr/bin/env python3
"""
run_house_batch.py — รัน t02 (LoRA: Sicilian44/qwen3vl-30b-thai-rc) ทุกหน้าของบ้านที่ระบุ
เซฟผลแยกโฟลเดอร์ตามบ้าน ที่ tune_ai/t02/ผล/<house>/<page>.json

โหลดโมเดลครั้งเดียว (โมเดล 62GB บนการ์ดจอเช่า) แล้ววนสร้างทีละหน้า — ไม่ใช่ infer_t02.py
ทีละภาพ (โหลดโมเดลใหม่ทุกครั้ง = เสียเวลาบนนาฬิกาที่คิดเงินโดยไม่จำเป็น)

resume-safe: ข้ามหน้าที่มีไฟล์ผลลัพธ์อยู่แล้ว — ถ้า process ตายกลางทาง รันซ้ำได้โดยไม่เสียเวลา/เงิน
ที่ทำไปแล้ว (บทเรียนจาก DAY OF SHAME — งานที่ทำแล้วต้องไม่หายเมื่อมีปัญหากลางทาง)

2026-08-21: เพิ่ม grammar-constrained decoding (--grammar-backend auto|xgr|lmfe|none,
default auto = xgrammar ก่อน ตกมา lm-format-enforcer) + regex ลบ trailing comma ก่อน parse
- lmfe: พิสูจน์บนเครื่องเช่าแล้วผ่าน infer_t02_grammar.py / xgr: probe ผ่านบนเครื่อง local
  (compile grammar + LogitsProcessor init ด้วย tokenizer จริงของ Qwen) แต่ยังไม่เคยรันบน GPU
- **เส้นทาง batch นี้ทั้งเส้นยังไม่เคยรันบน GPU จริง** — รอบหน้าที่เช่า ให้ลอง --limit 2
  ก่อนปล่อยเต็มเสมอ (ธรรมเนียมเดิมของไฟล์นี้อยู่แล้ว) และถ้า xgr มีปัญหา:
  --grammar-backend lmfe คือตัวที่พิสูจน์แล้ว

    python3 run_house_batch.py --images-root /workspace/tune/image --out-root /workspace/tune/ผล
    python3 run_house_batch.py --houses 01 03          # รันแค่บางบ้าน
    python3 run_house_batch.py --limit 5                # ทดสอบสั้นก่อนรันเต็ม (แนะนำก่อนรันจริง)
"""
import argparse, json, os, time
from pathlib import Path

HERE = Path(__file__).parent

# ชื่อโฟลเดอร์ภาพต้นทาง (Training/image/<...>) → ชื่อโฟลเดอร์ผลลัพธ์ (ตรงกับ
# rawjson_ยังไม่ได้แก้ไขโดนคน/ และ json_แก้ไขแล้ว/ เพื่อเทียบ ground truth ได้ตรงชื่อ)
# บ้าน 08-11: ไม่อยู่ใน train.jsonl/val.jsonl ของ t02 เลย (ตรวจแล้ว 2026-08-20) = unseen จริง
# แผนลดขอบเขต 2026-08-20 (ราคาเช่าจริง $1.792/hr แพงกว่าที่คิด): บ้าน 08 ทำเต็ม, บ้าน 09
# ทำแค่หน้า plan โครงสร้าง+gridline — 10/11 ตัดออกจากรอบนี้ (ไฟล์ยังอยู่ ใช้ภายหลังได้)
HOUSES = {
    "08": ("บ้าน_เล็ก_1ชั้น_03", "08บ้าน_เล็ก_1ชั้น_03"),
    "09": ("บ้าน_เล็ก_1ชั้น_04", "09บ้าน_เล็ก_1ชั้น_04"),
}

# None = ทุกหน้าตามลำดับเลขหน้า, list = ลำดับ/ชุดหน้าที่ต้องการ (จับคู่จาก rawjson
# ground truth ของบ้านนั้น) — ถ้าให้ list จะ "เรียงตามลำดับที่ระบุ" ไม่ใช่แค่กรอง
# บ้าน 08: หลังหน้า 1-15 ให้ข้ามไปหน้า 20 (beam_plan) ก่อน แล้วค่อยกลับมาทำที่เหลือ
# (สั่ง 2026-08-20) รวมยังคง 25 หน้าเท่าเดิม แค่สลับลำดับ
# บ้าน 09: ไม่มีไฟล์ page00_gridline.png จริง (gridmaster ในเอกสาร t02 เป็น multi-image
# composite เฉพาะ 5 บ้านที่ใช้ทูน ไม่มีของบ้านนี้) ใช้หน้า plan โครงสร้างที่มีเส้นกริดพิมพ์
# อยู่ในแบบแทน: floor_plan(06) footing_plan(24) pile_footing_plan(25) beam_floor_plan(26)
# ring_beam_plan(27) roof_frame_plan(28) — ตัด MEP plan (lighting/outlet/ac/roof_drain) ออก
PAGE_FILTER = {
    "08": list(range(1, 16)) + [20] + list(range(16, 20)) + list(range(21, 26)),
    "09": [6, 24, 25, 26, 27, 28],
}

ap = argparse.ArgumentParser()
ap.add_argument("--images-root", required=True, help="โฟลเดอร์ที่มี <house_image_folder>/*.png")
ap.add_argument("--out-root", required=True, help="โฟลเดอร์ผลลัพธ์ (สร้างซับโฟลเดอร์ตามบ้านให้เอง)")
ap.add_argument("--houses", nargs="+", default=list(HOUSES.keys()), choices=list(HOUSES.keys()))
ap.add_argument("--adapter", default="Sicilian44/qwen3vl-30b-thai-rc")
ap.add_argument("--subfolder", default="lora-adapter",
                help="adapter files ไม่ได้อยู่ที่ root ของ repo — ตรวจแล้ว 2026-08-20 ว่าอยู่ใต้ lora-adapter/")
ap.add_argument("--prompt-file", default=None, help="default: ดึงจาก val.jsonl แถวแรก")
ap.add_argument("--max-new-tokens", type=int, default=3000)
ap.add_argument("--limit", type=int, default=0, help="จำกัดจำนวนหน้า/บ้าน (0 = ทุกหน้า)")
ap.add_argument("--grammar-backend", choices=["auto", "xgr", "lmfe", "none"], default="auto",
                help="auto = ลอง xgrammar ก่อน (ดีสุด — trailing comma เป็นไปไม่ได้ที่ระดับ grammar) "
                     "ตกมา lm-format-enforcer (พิสูจน์บน GPU แล้ว) ตกมารันปกติ; "
                     "บังคับตัวใดตัวหนึ่งได้เพื่อ A/B")
ap.add_argument("--no-grammar", action="store_true",
                help="(ทางลัดเดิม) เท่ากับ --grammar-backend none")
args = ap.parse_args()
if args.no_grammar:
    args.grammar_backend = "none"

import torch
from PIL import Image

try:
    from unsloth import FastVisionModel as UnslothModel
except ImportError:
    from unsloth import FastModel as UnslothModel

print("=== โหลดโมเดล + adapter (ครั้งเดียว) ===")
# Unsloth's from_pretrained ไม่ forward kwarg `subfolder` ไปยัง AutoConfig/PeftConfig
# ภายใน (ตรวจ source แล้ว 2026-08-20 — hardcode แค่ token/revision/trust_remote_code/
# local_files_only) จึงต้องโหลดไฟล์ลง local ก่อนแล้วชี้ path ตรง ไม่ใช้ subfolder kwarg
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
else:
    print("⚠️  tokenizer.image_processor ไม่มี — ความละเอียดภาพอาจไม่ถูกบังคับตามที่ตั้งใจ")
UnslothModel.for_inference(model)

# grammar-constrained decoding (สรุปผลสืบ 2026-08-21, ดู rule_of_tune.md ข้อ 13):
#   xgr  = xgrammar: trailing comma เป็นไปไม่ได้ที่ระดับ grammar, มี LogitsProcessor สำเร็จรูป
#          — ดีสุดแต่ยังไม่เคยรันบน GPU จริง (probe บนเครื่อง local ผ่าน)
#   lmfe = lm-format-enforcer: พิสูจน์บน GPU แล้ว แต่ยอม trailing comma (regex ด้านล่างเก็บ)
#          และใช้ได้แค่ schema {"type":"object"} เปล่า (ปิด key set ถ้าประกาศ properties)
# ทั้งคู่: tokenizer จริงต้องแกะจาก processor wrapper (.tokenizer)
# grammar_setup() → dict ของ kwargs ที่จะรวมเข้า generate (สร้างใหม่ต่อหน้า — state ต่อ sequence)
grammar_setup = None
grammar_name = "none"

if args.grammar_backend in ("auto", "xgr"):
    try:
        import xgrammar as xgr
        cfg = model.config
        _vocab = getattr(cfg, "vocab_size", None) or cfg.text_config.vocab_size
        _tok_info = xgr.TokenizerInfo.from_huggingface(tokenizer.tokenizer, vocab_size=_vocab)
        _compiled = xgr.GrammarCompiler(_tok_info).compile_builtin_json_grammar()
        def grammar_setup():
            # LogitsProcessor ของ xgrammar เป็น stateful — ตัวใหม่ทุก generate
            return {"logits_processor": [xgr.contrib.hf.LogitsProcessor(_compiled)]}
        grammar_name = "xgrammar"
    except Exception as e:
        print(f"⚠️  xgrammar ใช้ไม่ได้ ({e})" + (" — ลอง lm-format-enforcer" if args.grammar_backend == "auto" else ""))
        if args.grammar_backend == "xgr":
            raise      # ผู้ใช้บังคับ xgr เอง — พังดังๆ ดีกว่ารันผิดตัวเงียบๆ

if grammar_setup is None and args.grammar_backend in ("auto", "lmfe"):
    try:
        import transformers.tokenization_utils as _tu
        if not hasattr(_tu, "PreTrainedTokenizerBase"):   # transformers 5.x ย้าย class นี้
            import transformers as _tf
            _tu.PreTrainedTokenizerBase = _tf.PreTrainedTokenizerBase
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import (
            build_token_enforcer_tokenizer_data, build_transformers_prefix_allowed_tokens_fn)
        _tok_data = build_token_enforcer_tokenizer_data(tokenizer.tokenizer)
        def grammar_setup():
            return {"prefix_allowed_tokens_fn":
                    build_transformers_prefix_allowed_tokens_fn(_tok_data, JsonSchemaParser({"type": "object"}))}
        grammar_name = "lm-format-enforcer"
    except Exception as e:
        print(f"⚠️  lm-format-enforcer ใช้ไม่ได้ ({e}) — รันต่อแบบไม่ constrain")
        if args.grammar_backend == "lmfe":
            raise

print(f"grammar-constrained: {grammar_name}")

if args.prompt_file:
    prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
else:
    first_row = json.loads(next(open(HERE / "val.jsonl", encoding="utf-8")))
    prompt_text = next(c["text"] for c in first_row["messages"][0]["content"] if c["type"] == "text")

images_root = Path(args.images_root)
out_root = Path(args.out_root)

def run_one(img_path: Path):
    img = Image.open(img_path).convert("RGB")
    msgs = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": prompt_text}]}]
    text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer([img], text, add_special_tokens=False, return_tensors="pt").to("cuda")
    gen_kwargs = dict(max_new_tokens=args.max_new_tokens, do_sample=False,
                      repetition_penalty=1.15, no_repeat_ngram_size=8)
    if grammar_setup is not None:
        gen_kwargs.update(grammar_setup())      # ตัวใหม่ต่อหน้า — state ไม่ปนกัน
    out = model.generate(**inputs, **gen_kwargs)
    pred_txt = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    del inputs, out
    import gc; gc.collect(); torch.cuda.empty_cache()
    # enforcer ยอม trailing comma โดย design แต่ json.loads ไม่ยอม — ลบก่อน parse
    # (ponytail: regex ไม่รู้จัก string boundary, ",}" ในเนื้อ string โดนด้วย — โอกาสน้อยมาก)
    import re
    cleaned = re.sub(r",(\s*[}\]])", r"\1", pred_txt)
    try:
        return {"ok": True, "parsed": json.loads(cleaned), "raw_text": pred_txt,
                "grammar": grammar_name}
    except Exception:
        return {"ok": False, "parsed": None, "raw_text": pred_txt,
                "grammar": grammar_name}

for code in args.houses:
    img_folder, out_folder = HOUSES[code]
    src_dir = images_root / img_folder
    dst_dir = out_root / out_folder
    dst_dir.mkdir(parents=True, exist_ok=True)

    all_pages = sorted(src_dir.glob("*.png"))
    page_filter = PAGE_FILTER.get(code)
    if page_filter is not None:
        # เรียงตามลำดับที่ระบุใน page_filter ไม่ใช่แค่กรอง (รองรับการสลับลำดับ)
        order = {f"หน้า{n:02d}": i for i, n in enumerate(page_filter)}
        matched = [p for p in all_pages if any(k in p.stem for k in order)]
        pages = sorted(matched, key=lambda p: next(i for k, i in order.items() if k in p.stem))
    else:
        pages = all_pages
    if args.limit:
        pages = pages[: args.limit]
    print(f"\n=== บ้าน {code} ({img_folder}) — {len(pages)} หน้า → {dst_dir} ===")

    n_valid, t0 = 0, time.time()
    for i, page in enumerate(pages):
        out_file = dst_dir / f"{page.stem}.json"
        if out_file.exists():
            print(f"  [{i+1}/{len(pages)}] {page.name}: ข้าม (มีผลอยู่แล้ว)")
            n_valid += 1
            continue
        result = run_one(page)
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        n_valid += int(result["ok"])
        status = "OK" if result["ok"] else "JSON เสีย"
        print(f"  [{i+1}/{len(pages)}] {page.name}: {status}")

    elapsed = time.time() - t0
    summary = {"house": out_folder, "pages": len(pages), "json_valid": n_valid,
               "elapsed_sec": round(elapsed, 1)}
    (dst_dir / "_batch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  สรุป: {n_valid}/{len(pages)} JSON valid, ใช้เวลา {elapsed/60:.1f} นาที")

print("\n=== เสร็จทุกบ้าน ===")
