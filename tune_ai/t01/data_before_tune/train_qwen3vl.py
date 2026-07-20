#!/usr/bin/env python3
"""
train_qwen3vl.py — fine-tune Qwen3-VL-8B-Instruct on Thai RC drawing pages (Unsloth + LoRA)

รันบนเครื่องเช่า GPU หลังอัปโหลดโฟลเดอร์นี้ทั้งก้อน:
    python train_qwen3vl.py

โครงสร้างที่ต้องมีข้าง ๆ ไฟล์นี้:
    train.jsonl  val.jsonl  images/

⚠️ rule_of_tune.md ข้อ 2: ค่าใน CONFIG ด้านล่างกำหนดว่าโมเดลจะเรียนอะไร/เห็นภาพละเอียดแค่ไหน
   แก้แล้วผลลัพธ์ fine-tune เปลี่ยน — ต้องเตือน/ขออนุญาตก่อนแก้เสมอ
"""
import json, os, gc
from pathlib import Path

# ─────────────────────────────────────────────────────────────
MODEL_ID = "unsloth/Qwen3-VL-8B-Instruct-unsloth-bnb-4bit"

# Qwen3-VL นับ 1 visual token ต่อ 32x32 px (ไม่ใช่ 28x28 แบบ Qwen2.5-VL — ก็อป config เก่ามาจะ OOM)
# 5120 tok = ภาพเต็มหน้า ~2723x1925 px  ← ทดสอบแล้วว่าจุดเหล็กบน/ล่างยังแยกออก
#            ที่ 2560 tok จุดเหล็ก 2 จุดรวมเป็นก้อนเดียว อ่านไม่ออก (ดู README หัวข้อ "ทำไม 5120")
MAX_PIXELS = 5120 * 32 * 32
MIN_PIXELS = 256 * 32 * 32

EPOCHS = 3
LR = 1e-4
BATCH = 1              # 24GB พอแค่ 1 ที่ความละเอียดนี้
GRAD_ACCUM = 8         # effective batch = 8
MAX_LENGTH = 10240     # 5120 (ภาพ) + ~290 (instruction) + ~2800 (output ยาวสุด) + หัวท้าย
OUT_DIR = "outputs"
# ─────────────────────────────────────────────────────────────

from unsloth import FastVisionModel
import torch
from PIL import Image

HERE = Path(__file__).parent

def load_split(name):
    """อ่าน jsonl แล้วสลับ path รูป → PIL Image (Unsloth ต้องการ object ไม่ใช่ path)"""
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
print(f"train {len(train_ds)} examples | val {len(val_ds)} examples")

model, tokenizer = FastVisionModel.from_pretrained(
    MODEL_ID,
    load_in_4bit=True,
    use_gradient_checkpointing="unsloth",   # จำเป็นที่ความยาว seq ระดับนี้
    max_seq_length=MAX_LENGTH,
)

# ── บังคับความละเอียดภาพ ต้องตั้งก่อนเทรน ไม่งั้น processor ย่อลง ~1.3MP ตาม default
#    แล้วตัวอักษรเหล็กหายตั้งแต่ input โมเดลไม่มีทางเรียนถูก
ip = tokenizer.image_processor
ip.max_pixels = MAX_PIXELS
ip.min_pixels = MIN_PIXELS
if getattr(ip, "size", None) is not None and isinstance(ip.size, dict):
    ip.size["longest_edge"] = MAX_PIXELS
    ip.size["shortest_edge"] = MIN_PIXELS
print(f"image processor: min={ip.min_pixels} max={ip.max_pixels} px "
      f"(≈{ip.max_pixels // 1024} visual tokens ต่อภาพ)")

model = FastVisionModel.get_peft_model(
    model,
    finetune_vision_layers=True,     # ★ ต้อง True — งานนี้คือ "อ่านตัวเลขเล็กในภาพ" ไม่ใช่แค่จัด format
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=32, lora_alpha=32, lora_dropout=0.05,
    bias="none", random_state=3407, use_rslora=False, loftq_config=None,
)

from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig

FastVisionModel.for_training(model)

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
        # บังคับสำหรับ vision fine-tuning
        remove_unused_columns=False,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        max_length=MAX_LENGTH,
    ),
)

gpu = torch.cuda.get_device_properties(0)
print(f"GPU: {gpu.name} {gpu.total_memory/1024**3:.1f} GB")
stats = trainer.train()
print(stats)

model.save_pretrained(f"{OUT_DIR}/lora")
tokenizer.save_pretrained(f"{OUT_DIR}/lora")
print(f"✓ เซฟ LoRA adapter ที่ {OUT_DIR}/lora")

# ── ลองยิง val 3 ตัวให้ดูผลจริงทันที (eval loss อย่างเดียวบอกไม่ได้ว่าอ่านเลขถูกไหม)
FastVisionModel.for_inference(model)
for i, sample in enumerate(val_ds[:3]):
    msgs = [sample["messages"][0]]
    text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True)
    imgs = [c["image"] for c in msgs[0]["content"] if c["type"] == "image"]
    inputs = tokenizer(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
    out = model.generate(**inputs, max_new_tokens=3000, temperature=0.1, do_sample=False)
    pred = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    Path(f"{OUT_DIR}/sample_{i}.json").write_text(pred, encoding="utf-8")
    ok = True
    try:
        json.loads(pred)
    except Exception as e:
        ok = False
        print(f"  ตัวอย่าง {i}: JSON เสีย — {e}")
    print(f"  ตัวอย่าง {i}: {'JSON valid' if ok else 'JSON เสีย'} ({len(pred)} ตัวอักษร)")
    del inputs, out
    gc.collect(); torch.cuda.empty_cache()

print("\nขั้นต่อไป: python eval_fields.py   (วัด field-level exact match ทั้ง val set)")
