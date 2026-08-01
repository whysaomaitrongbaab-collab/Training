#!/usr/bin/env python3
"""
train_qwen3vl.py (t02) — fine-tune Qwen3-VL on Thai RC drawing pages (Unsloth + LoRA)

t02 มีเป้าหมายเดียว: **เทียบกับ t01 ให้ได้จริง**
t01 = Qwen3.6-35B-A3B (MoE, active 3B)  →  t02 = Qwen3-VL-30B-A3B-Instruct (MoE, active 3B)
ตัวแปรที่ต่างมีตัวเดียวคือ "ตระกูลโมเดล" ที่เหลือคุมให้เท่ากันหมด (dataset ก็อปมาแบบ byte-identical
ดู DATASET_PROVENANCE.md)

    MODEL_SIZE=30B-A3B python3 train_qwen3vl.py    # ← ตัวหลักของ t02 (default)
    MODEL_SIZE=8B      python3 train_qwen3vl.py    # ตัวเล็ก ไว้ทดสอบ/เทียบเพิ่ม (4090 24GB)
    MODEL_SIZE=32B     python3 train_qwen3vl.py    # dense 32B (ไม่ใช่ตัวเทียบ — active param ต่าง 10 เท่า)

    TEST_STEPS=5 MODEL_SIZE=30B-A3B python3 train_qwen3vl.py   # ★ รันสั้นก่อนเสมอ

โครงสร้างที่ต้องมีข้าง ๆ ไฟล์นี้:  train.jsonl  val.jsonl  images/

⚠️ rule_of_tune.md ข้อ 2: PRESET ด้านล่างกำหนดว่าโมเดลจะเรียนอะไร/เห็นภาพละเอียดแค่ไหน
   แก้แล้วผล fine-tune เปลี่ยน — ต้องเตือน/ขออนุญาตก่อนแก้เสมอ
"""
import json, os, gc, sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# PRESET — เลือกด้วย env var MODEL_SIZE (default 30B-A3B = ตัวเทียบของ t02)
# ─────────────────────────────────────────────────────────────
# Qwen3-VL นับ 1 visual token / 32x32 px (= 1024 px) — ยืนยันจาก preprocessor_config.json จริง
# (patch_size 16 x merge_size 2 = 32) ไม่ใช่ 28x28 แบบ Qwen2.5-VL — ก็อป config เก่ามาจะ OOM
#   5120 tok = 5,242,880 px  ← t01 ใช้ค่านี้เป๊ะ (MAX_PIXELS = 5120*1024) ห้ามเปลี่ยนถ้าจะเทียบกับ t01
#   7680 tok = 7,864,320 px  ← native 3309x2339 ไม่ย่อเลย ใช้ตอน VRAM เหลือ (คนละเงื่อนไขกับ t01)
#
# MAX_LENGTH: ตัวอย่าง gridmaster (1 ต่อบ้าน = 5 ตัว) มัดภาพ 2-4 ใบ ไม่ใช่ใบเดียว
#   4 ภาพ x 5120 tok + instruction 1,022 + output สูงสุด 2,818 = 24,320 → ต้อง >= ค่านี้
#   t01 เจอบั๊กนี้จริงและแก้ 9216 -> 24576 (t01_workflow.md 0.4) t02 ใช้เลขเดียวกัน
#   ⚠️ ค่าเดิมในไฟล์ต้นฉบับ (10240 สำหรับ 8B / 13312 สำหรับ 32B) ตัด gridmaster ทิ้งเหลือ 42%/39%
PRESETS = {
    # ★ ตัวหลักของ t02 — mirror ทุกค่าจาก t01/train_qwen36.py เพื่อให้ A/B มีความหมาย
    "30B-A3B": dict(
        model="unsloth/Qwen3-VL-30B-A3B-Instruct",
        load_in_4bit=False,          # ไม่มี repo bnb-4bit ของ MoE เลย + t01 ก็ใช้ bf16 (ตระกูล MoE
                                     # ไม่แนะนำ 4-bit: quantization difference สูงผิดปกติ)
        max_pixels=5120 * 1024,      # = t01 เป๊ะ (5,120 visual tokens/ภาพ)
        lora_r=32, lora_alpha=64,    # = t01 เป๊ะ
        batch=1, grad_accum=8,       # = t01 เป๊ะ
        max_length=24576,            # = t01 เป๊ะ
    ),
    "8B": dict(
        model="unsloth/Qwen3-VL-8B-Instruct-unsloth-bnb-4bit",
        load_in_4bit=True,
        max_pixels=5120 * 1024,
        lora_r=32, lora_alpha=64,
        batch=1, grad_accum=8,
        max_length=24576,            # แก้จาก 10240 — ค่าเดิมตัด gridmaster ทิ้งเหลือ 42%
    ),
    "32B": dict(
        model="unsloth/Qwen3-VL-32B-Instruct-unsloth-bnb-4bit",
        load_in_4bit=True,
        max_pixels=5120 * 1024,
        lora_r=32, lora_alpha=64,
        batch=1, grad_accum=8,
        max_length=24576,            # แก้จาก 13312 — ค่าเดิมตัด gridmaster ทิ้งเหลือ 39%
    ),
}
SIZE = os.environ.get("MODEL_SIZE", "30B-A3B").upper()
if SIZE not in PRESETS:
    sys.exit(f"❌ MODEL_SIZE={SIZE} ไม่มีใน PRESETS — เลือกจาก {list(PRESETS)}")
P = PRESETS[SIZE]

MIN_PIXELS = 256 * 1024           # = t01 เป๊ะ
EPOCHS = 3                        # = t01
LR = 1e-4                         # = t01 (LoRA; ถ้าเปลี่ยนเป็น full fine-tune ต้องลดเหลือ 5e-6..1e-5)
OUT_DIR = f"outputs_{SIZE.lower().replace('-', '')}"

# freeze vision layers (ViT + merger) — เทรนเฉพาะ LLM ด้วย LoRA. เหมือน t01 เป๊ะ
#   เหตุผล: dataset 315 ตัวอย่าง = เล็ก การเทรน ViT บนชุดเล็กทำ visual features พัง
#   ปัญหา "Ø12→DB23" แก้ด้วยความละเอียดภาพ (max_pixels สูง) ไม่ใช่รื้อ encoder ใหม่
#   ⚠️ notebook ทางการของ Unsloth ตั้ง finetune_vision_layers=True แต่เราตั้ง False เพื่อให้ตรงกับ
#      t01 — ถ้าเปลี่ยนตรงนี้ ผลจะเทียบกับ t01 ไม่ได้อีกต่อไป (เก็บไว้เป็นการทดลองรอบถัดไป)
FINETUNE_VISION = os.environ.get("FINETUNE_VISION", "0") == "1"

# ทดสอบก่อนรันเต็มเสมอ: TEST_STEPS=5 python3 train_qwen3vl.py  (= t01)
TEST_STEPS = int(os.environ.get("TEST_STEPS", "0"))

# ข้ามการ generate ตัวอย่างหลังเทรน — t01 เจอว่า epilogue นี้ค้างกิน VRAM ~83GB ไม่ยอมจบ
# (t01_workflow.md Phase 6 bug #1) adapter เซฟเสร็จก่อนถึงตรงนี้แล้ว ปลอดภัยที่จะข้าม
SKIP_DEMO = os.environ.get("SKIP_DEMO", "0") == "1"
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
n_multi = sum(1 for r in train_ds
              if sum(1 for c in r["messages"][0]["content"] if c["type"] == "image") > 1)
print(f"[{SIZE}] train {len(train_ds)} | val {len(val_ds)} | "
      f"multi-image (gridmaster) {n_multi} | vision={'train' if FINETUNE_VISION else 'FROZEN'}")

model, tokenizer = FastVisionModel.from_pretrained(
    P["model"],
    load_in_4bit=P["load_in_4bit"],
    use_gradient_checkpointing="unsloth",
    # ★ ต้องส่งตรงนี้ด้วย ไม่ใช่แค่ใน SFTConfig — default ของ Unsloth คือ 2048 และ collator
    #   จะเอาค่านี้ไปตัด sequence ทิ้ง "กลาง image token" (ไม่มี guard เหมือนฝั่ง audio)
    max_seq_length=P["max_length"],
)

# ── pad_token: repo 4-bit ของ Unsloth ใส่ <|vision_pad|> มา ซึ่ง issue #4104 รายงานว่าทำให้
#    gradient ระเบิด/NaN เมื่อ batch > 1. เราใช้ batch=1 อยู่แล้วแต่เช็คไว้ให้เห็นชัด
pad = getattr(tokenizer, "pad_token", None) or getattr(
    getattr(tokenizer, "tokenizer", None), "pad_token", None)
print(f"pad_token = {pad!r}" + ("   ⚠️ <|vision_pad|> — ระวังถ้าเพิ่ม batch > 1"
                                if pad == "<|vision_pad|>" else ""))

# บังคับความละเอียดภาพ ต้องตั้งก่อนเทรน ไม่งั้น processor ใช้ default (สูงสุด 16,384 tok/ภาพ)
# ซึ่งทำให้ sequence ยาวเกินจำเป็นมหาศาล — และต้องเท่ากับ t01 ถึงจะเทียบกันได้
#
# ⚠️ พังจริงบนเครื่องเช่า 2026-07-28: `ip.max_pixels = ...` ที่นี่เคยเป็นวิธีตั้งค่า แต่บน
# transformers 5.5.0 (เวอร์ชันจริงที่ pip ดึงมา) ip ไม่มี attribute max_pixels/min_pixels
# แล้ว (ไม่ใช่แค่ readonly — hasattr เป็น False เลย) → AttributeError ทันทีตอน Phase 4
# baseline อ่าน source จริงของ Qwen2VLImageProcessor (ใช้เป็น image_processor ของ Qwen3-VL
# ด้วย) แล้วพบว่า preprocess() อ่าน min/max pixels จาก self.size["shortest_edge"]/
# ["longest_edge"] เป็นค่า default เสมอเมื่อไม่ได้ส่ง min_pixels/max_pixels เป็น kwargs ตรงๆ
# ตอน call — ฉะนั้น ip.size[...] ด้านล่างคือกลไกจริงที่มีผล ไม่ต้องพึ่ง ip.max_pixels เลย
ip = tokenizer.image_processor
# ip.size เป็น SizeDict ไม่ใช่ dict subclass จริง (isinstance(..., dict) เป็น False เสมอ)
# แต่รองรับ ip.size["key"]=value ตรง ๆ — ห้ามเช็ค isinstance ก่อน (ยืนยันบนเครื่องเช่า 2026-07-21)
ip.size["longest_edge"] = P["max_pixels"]
ip.size["shortest_edge"] = MIN_PIXELS
print(f"image processor: max={ip.size['longest_edge']} px "
      f"(= {ip.size['longest_edge'] // 1024} visual tokens/ภาพ), "
      f"min={ip.size['shortest_edge']} px (= {ip.size['shortest_edge'] // 1024} tokens)")

model = FastVisionModel.get_peft_model(
    model,
    finetune_vision_layers=FINETUNE_VISION,
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    # lora_dropout=0 บังคับ — t01 เจอ error จริง: MoE ParamWrapper ไม่รองรับ dropout!=0
    # Qwen3-VL-30B-A3B ก็เป็น MoE เหมือนกัน ค่า 0.05 เดิมในไฟล์นี้เขียนไว้ก่อน t01 จะรันจริง
    # (และมันเป็นตัวแปรที่ไม่ได้คุมด้วย ต้องเท่า t01 อยู่แล้ว)
    r=P["lora_r"], lora_alpha=P["lora_alpha"], lora_dropout=0,
    bias="none", random_state=3407, use_rslora=False, loftq_config=None,
)

from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig

FastVisionModel.for_training(model)

# ★★ resize="max" คือของบังคับ ★★
# default ของ UnslothVisionDataCollator คือ resize="min" ซึ่งจะไปอ่าน
# model.config.vision_config.image_size — แต่ Qwen3-VL "ไม่มี key นี้" เลย fallback
# ไปที่ 512 px เงียบ ๆ (พิมพ์เตือนบรรทัดเดียว) แบบ 2560px จะเหลือ ~205 visual token
# แทนที่จะเป็น 5,120 = เสียความละเอียด 25 เท่า และ VRAM จะดู "สบาย" อย่างหลอก ๆ
# resize="max" = ไม่ย่อภาพเลย ปล่อยให้ image_processor ข้างบนคุม max_pixels แทน
collator = UnslothVisionDataCollator(model, tokenizer, resize="max",
                                     max_seq_length=P["max_length"])

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    data_collator=collator,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    args=SFTConfig(
        per_device_train_batch_size=P["batch"],
        gradient_accumulation_steps=P["grad_accum"],
        warmup_ratio=0.05,
        num_train_epochs=EPOCHS,
        **({"max_steps": TEST_STEPS} if TEST_STEPS else {}),
        learning_rate=LR,
        logging_steps=5,
        optim="paged_adamw_8bit",   # = t01 — paged กัน memory spike ตอน optimizer step
                                    # ค่าเดิมในไฟล์นี้คือ adamw_8bit ซึ่งเป็นตัวที่ t01 เจอ OOM จริงแล้วเปลี่ยนหนี
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
        bf16=True,          # ★ = t01 — ไม่ใช้ fp16 — MoE ตระกูลนี้ Unsloth แนะนำ bf16 setup เท่านั้น
                            # ไฟล์นี้เดิมไม่มีบรรทัดนี้เลย → Trainer จะไม่ตั้ง mixed precision ให้
                            # กลายเป็นตัวแปรที่ไม่ได้คุมอีกตัว
    ),
)

# ── พิสูจน์ว่า resize/max_pixels มีผลจริง ก่อนเผาเวลาเทรน (เช็คถูกที่สุดที่ทำได้)
#    ถ้า collator แอบย่อภาพเป็น 512 px ตัวเลขนี้จะต่ำกว่าที่ตั้งไว้หลายเท่า
try:
    _b = collator([train_ds[0]])
    _pv = _b.get("pixel_values")
    _gt = _b.get("image_grid_thw")
    if _gt is not None:
        _tok = int((_gt[:, 1] * _gt[:, 2]).sum()) // 4   # spatial_merge_size**2 = 4
        print(f"✓ ตรวจ batch แรก: pixel_values {tuple(_pv.shape)} | grid_thw {_gt.tolist()} "
              f"→ ~{_tok} visual tokens")
        assert _tok > 1000, (f"visual tokens = {_tok} ต่ำผิดปกติ — collator น่าจะย่อภาพเป็น 512px "
                             f"(เช็คว่า resize='max' ถูกส่งจริงไหม)")
    else:
        print(f"✓ ตรวจ batch แรก: pixel_values {tuple(_pv.shape)}")
    print(f"  seq len = {_b['input_ids'].shape[-1]} (max_length={P['max_length']})")
    del _b, _pv, _gt
    gc.collect(); torch.cuda.empty_cache()
except AssertionError:
    raise
except Exception as e:
    print(f"⚠️  ตรวจ batch แรกไม่สำเร็จ ({e}) — ไม่ใช่ตัวบล็อก แต่ควรดู log ตอนเทรนว่า VRAM สมเหตุผลไหม")

gpu = torch.cuda.get_device_properties(0)
print(f"GPU: {gpu.name} {gpu.total_memory/1024**3:.1f} GB")
# = t01 — เตือนไว้ก่อนเริ่ม ไม่ใช่ให้ไปเจอ OOM ที่ step 200/663
if not P["load_in_4bit"] and gpu.total_memory / 1024**3 < 74:
    print(f"⚠️  VRAM {gpu.total_memory/1024**3:.0f}GB < แนะนำ 74GB สำหรับ bf16 LoRA — เสี่ยง OOM")
    print("    ถ้า OOM: ลด max_pixels เฉพาะภาพ gridmaster → ลด lora_r → เช่าการ์ดใหญ่กว่า")
    print("    ⛔ ห้ามลด max_length กลับ (จะตัด JSON label ทิ้ง และทำลาย A/B กับ t01)")
print(trainer.train())
print(f"peak VRAM: {torch.cuda.max_memory_allocated()/1024**3:.1f} GB")

model.save_pretrained(f"{OUT_DIR}/lora")
tokenizer.save_pretrained(f"{OUT_DIR}/lora")
print(f"✓ เซฟ LoRA adapter ที่ {OUT_DIR}/lora")

# ── ยิง val 3 ตัวให้ดูผลจริงทันที (eval loss อย่างเดียวบอกไม่ได้ว่าอ่านเลขเหล็กถูกไหม)
#    ⚠️ t01 เจอว่าบล็อกนี้ค้าง ไม่ยอมจบ กิน VRAM ~83GB ค้างไว้ (Phase 6 bug #1)
#       adapter เซฟเสร็จไปแล้วข้างบน ถ้าค้างให้ kill -9 ได้เลย ไม่ถือว่าเทรนพัง
#       หรือรันด้วย SKIP_DEMO=1 เพื่อข้ามไปเลย แล้วไปวัดจริงด้วย eval_fields.py แทน
if SKIP_DEMO:
    print("ข้าม demo generation (SKIP_DEMO=1)")
else:
    print("กำลัง generate ตัวอย่าง 3 ตัว — ถ้าค้างเกิน ~10 นาที kill ได้เลย adapter เซฟแล้ว")
    FastVisionModel.for_inference(model)
    for i, sample in enumerate(val_ds[:3]):
        msgs = [sample["messages"][0]]
        # enable_thinking=False จำเป็น: template default จะทิ้ง <think>\n ที่เปิดค้างไว้หลัง
        # add_generation_prompt=True แล้วโมเดลตระกูลนี้จะเขียน chain-of-thought ยาวแทนที่จะตอบ JSON
        # (t01 เจอ 2026-07-24: ตอนเทรนไม่กระทบ เพราะ add_generation_prompt=False ไม่ใส่ tag นี้
        #  เป็นปัญหาเฉพาะตอน inference — ทำให้วัดผลได้ 0% ทั้งที่โมเดลดี)
        text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True,
                                             enable_thinking=False)
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

print(f"\nขั้นต่อไป: MODEL_SIZE={SIZE} python3 eval_fields.py --adapter {OUT_DIR}/lora --limit 20")
