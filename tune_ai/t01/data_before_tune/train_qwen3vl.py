#!/usr/bin/env python3
"""
train_qwen3vl.py — fine-tune Qwen3-VL on Thai RC drawing pages (Unsloth + QLoRA)

รันบนเครื่องเช่า GPU หลังอัปโหลดโฟลเดอร์นี้ทั้งก้อน:
    MODEL_SIZE=8B  python train_qwen3vl.py     # 4090 24GB — เริ่มจากตัวนี้ก่อน
    MODEL_SIZE=32B python train_qwen3vl.py     # A100 80GB — คุณภาพสูงสุด

โครงสร้างที่ต้องมีข้าง ๆ ไฟล์นี้:  train.jsonl  val.jsonl  images/

⚠️ rule_of_tune.md ข้อ 2: PRESET ด้านล่างกำหนดว่าโมเดลจะเรียนอะไร/เห็นภาพละเอียดแค่ไหน
   แก้แล้วผล fine-tune เปลี่ยน — ต้องเตือน/ขออนุญาตก่อนแก้เสมอ
"""
import json, os, gc
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# PRESET — เลือกด้วย env var MODEL_SIZE (default 8B)
# ─────────────────────────────────────────────────────────────
# Qwen3-VL นับ 1 visual token / 32x32 px (ไม่ใช่ 28x28 แบบ Qwen2.5-VL — ก็อป config เก่ามา OOM)
#   5120 tok ≈ 2723x1925 px  ← ทดสอบแล้ว จุดเหล็กบน/ล่างยังแยกออก (ที่ 2560 รวมเป็นก้อน อ่านไม่ออก)
#   7680 tok ≈ native 3309x2339  ← ไม่ย่อภาพเลย ใช้ตอนมี VRAM เหลือ
PRESETS = {
    "8B": dict(
        model="unsloth/Qwen3-VL-8B-Instruct-unsloth-bnb-4bit",
        max_pixels=5120 * 32 * 32,   # 4090 24GB พอ
        lora_r=32, lora_alpha=32,
        batch=1, grad_accum=8, max_length=10240,
    ),
    "32B": dict(
        model="unsloth/Qwen3-VL-32B-Instruct-unsloth-bnb-4bit",
        max_pixels=7680 * 32 * 32,   # native — A100 80GB รับไหว
        lora_r=64, lora_alpha=128,   # dataset ยาก + VRAM เหลือ → rank สูงขึ้น
        batch=1, grad_accum=8, max_length=13312,
    ),
}
SIZE = os.environ.get("MODEL_SIZE", "8B").upper()
P = PRESETS[SIZE]

MIN_PIXELS = 256 * 32 * 32
EPOCHS = 3
LR = 1e-4                 # LoRA (ถ้าเปลี่ยนเป็น full fine-tune ต้องลดเหลือ 5e-6..1e-5)
OUT_DIR = f"outputs_{SIZE.lower()}"

# ★ freeze vision layers (ViT + merger) — เทรนเฉพาะ LLM ด้วย LoRA
#   เหตุผล: dataset แค่ 221 ตัว = เล็ก การเทรน ViT บนชุดเล็กทำ visual features พัง
#   (Fadaeinejad Qwen3-VL guide: "freeze ViT unless you have a large, high-quality dataset")
#   ปัญหา "Ø12→DB23" แก้ด้วย "ความละเอียดภาพ" (max_pixels สูง) ไม่ใช่รื้อ encoder ใหม่
#   ตั้ง True เพื่อ "ทดลองเทียบ" ว่าการเทรน vision ช่วยไหม (เสี่ยง — ทำหลัง baseline frozen แล้ว)
FINETUNE_VISION = os.environ.get("FINETUNE_VISION", "0") == "1"
# ─────────────────────────────────────────────────────────────

from unsloth import FastVisionModel
import torch
from PIL import Image

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
print(f"[{SIZE}] train {len(train_ds)} | val {len(val_ds)} | vision={'train' if FINETUNE_VISION else 'FROZEN'}")

model, tokenizer = FastVisionModel.from_pretrained(
    P["model"],
    load_in_4bit=True,
    use_gradient_checkpointing="unsloth",
    max_seq_length=P["max_length"],
)

# บังคับความละเอียดภาพ ต้องตั้งก่อนเทรน ไม่งั้น processor ย่อลง ~1.3MP ตาม default
# แล้วตัวอักษรเหล็กหายตั้งแต่ input โมเดลไม่มีทางเรียนถูก
ip = tokenizer.image_processor
ip.max_pixels = P["max_pixels"]
ip.min_pixels = MIN_PIXELS
if isinstance(getattr(ip, "size", None), dict):
    ip.size["longest_edge"] = P["max_pixels"]
    ip.size["shortest_edge"] = MIN_PIXELS
print(f"image processor: max={ip.max_pixels} px (≈{ip.max_pixels // 1024} visual tokens/ภาพ)")

model = FastVisionModel.get_peft_model(
    model,
    finetune_vision_layers=FINETUNE_VISION,   # ★ default False — ดูเหตุผลข้างบน
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=P["lora_r"], lora_alpha=P["lora_alpha"], lora_dropout=0.05,
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
        per_device_train_batch_size=P["batch"],
        gradient_accumulation_steps=P["grad_accum"],
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
        remove_unused_columns=False,      # บังคับสำหรับ vision fine-tuning
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        max_length=P["max_length"],
    ),
)

gpu = torch.cuda.get_device_properties(0)
print(f"GPU: {gpu.name} {gpu.total_memory/1024**3:.1f} GB")
print(trainer.train())

model.save_pretrained(f"{OUT_DIR}/lora")
tokenizer.save_pretrained(f"{OUT_DIR}/lora")
print(f"✓ เซฟ LoRA adapter ที่ {OUT_DIR}/lora")

# ── ยิง val 3 ตัวให้ดูผลจริงทันที (eval loss อย่างเดียวบอกไม่ได้ว่าอ่านเลขถูกไหม)
FastVisionModel.for_inference(model)
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

print(f"\nขั้นต่อไป: python eval_fields.py --adapter {OUT_DIR}/lora")
