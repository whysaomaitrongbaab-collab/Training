#!/usr/bin/env python3
"""
train_qwen36.py — fine-tune Qwen3.6-35B-A3B on Thai RC drawing pages (Unsloth + bf16 LoRA)

ตัดสินใจ 2026-07-20: ใช้ Qwen3.6-35B-A3B แทน Qwen3-VL (train_qwen3vl.py เดิม) เพราะ:
  - MoE 35B รวม / 3B active — เบนช์ document (OmniDocBench 89.9) เทียบเท่า Qwen3.5-122B-A10B (89.8)
    ทั้งที่ 122B ต้องใช้ bf16 LoRA 256GB VRAM (multi-GPU) vs ตัวนี้ 74GB (การ์ดเดียวพอ)
  - งานวิจัย fine-tuning บน dataset เล็ก: โมเดลใหญ่ลืมความรู้เดิม (catastrophic forgetting) หนักกว่า
    ไม่ใช่เบากว่า + MoE ยิ่งมี expert เยอะยิ่งเสี่ยง routing กระจุกที่ expert ไม่กี่ตัวเมื่อ domain แคบ
    (dataset เราคือเอกสารก่อสร้างไทยล้วน 226 ตัวอย่าง — แคบมาก) 256 experts ของ 122B ส่วนใหญ่จะไม่ถูกใช้

รันบนเครื่องเช่า GPU (A100/H100 80GB ใบเดียว) หลังอัปโหลดโฟลเดอร์นี้ทั้งก้อน:
    python train_qwen36.py

โครงสร้างที่ต้องมีข้าง ๆ ไฟล์นี้:  train.jsonl  val.jsonl  images/

⚠️⚠️⚠️ ยังไม่เคยรันจริงสักครั้ง — มากกว่าปกติที่ต้องเตือน เพราะ:
  1. Qwen3.6 ใหม่กว่า Qwen3-VL มาก (เม.ย. 2026) Unsloth community/notebook น้อยกว่า
  2. "natively multimodal early-fusion" — สถาปัตยกรรมอาจต่างจาก Qwen3-VL's ViT+merger พอที่
     FastVisionModel wrapper (ใช้ในสคริปต์นี้) จะใช้ไม่ได้ตรง ๆ ต้องพร้อมสลับเป็น FastLanguageModel
     ถ้า import/load พัง — ดู try/except ด้านล่างที่ดักไว้แล้ว
  3. เอกสาร Unsloth บอกแค่ "Qwen3.6 can now be run and fine-tuned in Unsloth Studio" ไม่มีตัวอย่าง
     โค้ดสคริปต์ดิบให้อ้างอิงตรง ๆ (ต่างจาก Qwen3-VL ที่มี notebook อ้างอิงชัดเจน)
  4. ทดสอบ MAX_STEPS=5 ก่อนเสมอ (ดูท้ายไฟล์) ก่อนปล่อยรันเต็ม 3 epoch

⚠️ rule_of_tune.md ข้อ 2: ค่าใน CONFIG กำหนดว่าโมเดลจะเรียนอะไร/เห็นภาพละเอียดแค่ไหน
   แก้แล้วผล fine-tune เปลี่ยน — ต้องเตือน/ขออนุญาตก่อนแก้เสมอ
"""
import json, os, gc, sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────
MODEL_ID = "unsloth/Qwen3.6-35B-A3B"   # bare repo = bf16 full weights, ไม่ใช่ -GGUF/-NVFP4/-MLX (พวกนั้นรันได้ ไม่ใช่ทูนได้)

# 🔴 ห้าม 4-bit/QLoRA — Unsloth เตือนเองว่า Qwen3.5/3.6 (dense และ MoE) quantize แล้ว
#    คุณภาพตกผิดปกติ ("higher than normal quantization differences" / BitsandBytes limitation)
#    ต้องโหลด bf16 เต็ม ~74GB VRAM สำหรับ LoRA — ใบเดียวพอถ้าเป็น A100/H100 80GB
LOAD_IN_4BIT = False

# Qwen3.6 vision: patch 16x16 + spatial-merge ×4 → H×W/(16×16×4) = H×W/1024 ต่อ token
# (บังเอิญสัดส่วนเดียวกับ Qwen3-VL's 32×32 patch — ทดสอบ crop จริงที่ทำไว้กับ Qwen3-VL
#  (5,120 tok ≈ 2723×1925 px ยังแยกจุดเหล็กบน/ล่างได้) จึงยังใช้เลขเดิมเป็นจุดเริ่ม
#  ⚠️ แต่ชื่อ attribute บน processor (max_pixels ฯลฯ) ยังไม่ยืนยันว่าตรงกับ Qwen3-VL
MAX_PIXELS = 5120 * 1024
MIN_PIXELS = 256 * 1024

EPOCHS = 3
LR = 1e-4              # LoRA (ไม่ใช่ full fine-tune ซึ่งต้องต่ำกว่านี้มาก 5e-6..1e-5)
BATCH = 1
GRAD_ACCUM = 8
MAX_LENGTH = 10240      # instruction ~1,020 + ภาพ 5,120 + output ยาวสุด ~2,750 + หัวท้าย
OUT_DIR = "outputs_qwen36"

# freeze vision — เหตุผลเดียวกับ train_qwen3vl.py: dataset เล็ก (226 ตัวอย่าง) เทรน vision
# encoder ทั้งก้อนเสี่ยงทำ visual features พัง ไปดันความละเอียดภาพ (MAX_PIXELS) แทน
# ทดลองเทียบได้: FINETUNE_VISION=1 python train_qwen36.py
FINETUNE_VISION = os.environ.get("FINETUNE_VISION", "0") == "1"

LORA_R, LORA_ALPHA = 64, 128   # MoE + งานยาก (อ่านเอกสารก่อสร้าง) — rank สูงกว่า preset 8B ของ Qwen3-VL
# ─────────────────────────────────────────────────────────────

import torch
from PIL import Image

# Qwen3.6 อาจไม่มี "vision encoder แยกจาก LLM" แบบ Qwen3-VL (early-fusion) —
# ลอง FastVisionModel ก่อน (ใช้กับ Qwen3-VL/Llama-Vision ทุกตัวที่ผ่านมา) ถ้าไม่มีคลาสนี้
# ใน unsloth เวอร์ชันที่ลงจริง ให้ fallback ไป FastModel (wrapper รวมของ Unsloth รุ่นใหม่)
try:
    from unsloth import FastVisionModel as UnslothModel
    MODEL_CLASS_USED = "FastVisionModel"
except ImportError:
    try:
        from unsloth import FastModel as UnslothModel
        MODEL_CLASS_USED = "FastModel"
    except ImportError:
        print("❌ ทั้ง FastVisionModel และ FastModel หาไม่เจอใน unsloth เวอร์ชันนี้ — "
              "เช็ค `pip show unsloth` และดู unsloth.ai/docs/models/qwen3.6 ว่าตอนนี้ใช้คลาสไหน")
        sys.exit(1)
print(f"ใช้ {MODEL_CLASS_USED} โหลดโมเดล (fallback อัตโนมัติถ้า FastVisionModel ไม่มี)")

HERE = Path(__file__).parent

def load_split(name):
    """อ่าน jsonl → สลับ path รูปเป็น PIL Image (Unsloth ต้องการ object ไม่ใช่ path)"""
    rows = []
    with open(HERE / f"{name}.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            content = []
            for c in r["messages"][0]["content"]:
                if c["type"] == "image":
                    content.append({"type": "image",
                                    "image": Image.open(HERE / c["image"]).convert("RGB")})
                else:
                    content.append({"type": "text", "text": c["text"]})
            rows.append({"messages": [
                {"role": "user", "content": content},
                {"role": "assistant", "content": r["messages"][1]["content"]},
            ]})
    return rows

train_ds = load_split("train")
val_ds = load_split("val")
print(f"train {len(train_ds)} | val {len(val_ds)} | vision={'train' if FINETUNE_VISION else 'FROZEN'}")

model, tokenizer = UnslothModel.from_pretrained(
    MODEL_ID,
    load_in_4bit=LOAD_IN_4BIT,          # False → bf16 เต็ม ~74GB
    use_gradient_checkpointing="unsloth",
    max_seq_length=MAX_LENGTH,
)

# บังคับความละเอียดภาพ — ชื่อ attribute อาจต่างจาก Qwen3-VL (ตรงนี้คือจุดเสี่ยง #2 ที่บอกไว้ข้างบน)
ip = getattr(tokenizer, "image_processor", None)
if ip is not None:
    ip.max_pixels = MAX_PIXELS
    ip.min_pixels = MIN_PIXELS
    if isinstance(getattr(ip, "size", None), dict):
        ip.size["longest_edge"] = MAX_PIXELS
        ip.size["shortest_edge"] = MIN_PIXELS
    print(f"image processor: max={ip.max_pixels} px (≈{ip.max_pixels // 1024} visual tokens/ภาพ)")
else:
    print("⚠️  tokenizer.image_processor ไม่มี — เช็คโครงสร้าง processor จริงด้วย "
          "print(tokenizer) / dir(tokenizer) ก่อนเทรนต่อ ความละเอียดภาพอาจไม่ถูกบังคับตามที่ตั้งใจ")

model = UnslothModel.get_peft_model(
    model,
    finetune_vision_layers=FINETUNE_VISION,
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.05,
    bias="none", random_state=3407, use_rslora=False, loftq_config=None,
)

from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig

UnslothModel.for_training(model)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    data_collator=UnslothVisionDataCollator(model, tokenizer),
    train_dataset=train_ds,
    eval_dataset=val_ds,
    args=SFTConfig(
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        warmup_ratio=0.05,
        num_train_epochs=EPOCHS,
        learning_rate=LR,
        logging_steps=5,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=3407,
        output_dir=OUT_DIR,
        report_to="none",
        save_strategy="epoch",
        eval_strategy="epoch",
        per_device_eval_batch_size=1,
        remove_unused_columns=False,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        max_length=MAX_LENGTH,
        bf16=True,          # ★ ไม่ใช้ fp16 — MoE ตระกูลนี้ Unsloth แนะนำ bf16 setup เท่านั้น
    ),
)

gpu = torch.cuda.get_device_properties(0)
print(f"GPU: {gpu.name} {gpu.total_memory/1024**3:.1f} GB")
if gpu.total_memory / 1024**3 < 74:
    print(f"⚠️  VRAM {gpu.total_memory/1024**3:.0f}GB < แนะนำ 74GB สำหรับ bf16 LoRA — เสี่ยง OOM")

print(trainer.train())

model.save_pretrained(f"{OUT_DIR}/lora")
tokenizer.save_pretrained(f"{OUT_DIR}/lora")
print(f"✓ เซฟ LoRA adapter ที่ {OUT_DIR}/lora")

# ── ยิง val 3 ตัวให้ดูผลจริงทันที (eval loss อย่างเดียวบอกไม่ได้ว่าอ่านเลขถูกไหม)
UnslothModel.for_inference(model)
for i, sample in enumerate(val_ds[:3]):
    msgs = [sample["messages"][0]]
    text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True)
    imgs = [c["image"] for c in msgs[0]["content"] if c["type"] == "image"]
    inputs = tokenizer(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
    out = model.generate(**inputs, max_new_tokens=3000, do_sample=False)
    pred = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    Path(f"{OUT_DIR}/sample_{i}.json").write_text(pred, encoding="utf-8")
    try:
        json.loads(pred); ok = "JSON valid"
    except Exception as e:
        ok = f"JSON เสีย — {e}"
    print(f"  ตัวอย่าง {i}: {ok} ({len(pred)} ตัวอักษร)")
    del inputs, out; gc.collect(); torch.cuda.empty_cache()

print(f"\nขั้นต่อไป: MODEL=qwen36 python eval_fields.py --adapter {OUT_DIR}/lora")

# ─────────────────────────────────────────────────────────────
# ก่อนรันเต็ม 3 epoch จริง แนะนำทดสอบ 5 step ก่อนเสมอ (โมเดล/สคริปต์นี้ยังไม่เคยรัน):
#   แก้ SFTConfig ชั่วคราวเพิ่ม max_steps=5 (ลบ num_train_epochs ออกชั่วคราว) แล้วดูว่า
#   ผ่าน step แรกได้ไหมก่อน ไม่งั้นถ้า OOM หรือ error ตอน step 200/663 จะเสียเวลา/เงินเปล่า
# ─────────────────────────────────────────────────────────────
