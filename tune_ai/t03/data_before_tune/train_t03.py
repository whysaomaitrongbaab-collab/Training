#!/usr/bin/env python3
"""
train_t03.py — fine-tune Qwen3.6-35B-A3B แบบ per-subtask (t03) ด้วย Unsloth + LoRA

เขียนใหม่ 2026-08-24 (มะขามสั่ง "เขียนใหม่ หาข้อมูลในเน็ตมาด้วย") — ไม่ใช่ copy ของ
t01/train_qwen36.py หรือ t02/train_qwen3vl.py แต่ทุกค่ามีที่มาระบุไว้ 2 ทาง:
  [W] = จากเอกสาร/งานวิจัยบนเน็ต (ค้น 2026-08-24):
        - Unsloth Qwen3.5 fine-tune docs (Qwen3.6-35B-A3B อยู่ตระกูลนี้ — log unsloth
          patch ขึ้นชื่อ "Qwen3_5_MoE"): bf16 LoRA 35B-A3B ~74GB VRAM, transformers v5
          บังคับ, MoE QLoRA 4-bit ไม่รองรับ (BitsandBytes), router layer ปิดเทรน
          by default "not a good idea to fine-tune the router"
        - Unsloth Vision docs: lora_dropout=0, bias="none", seed 3407,
          completion_only_loss "should always be True"
        - "LoRA Without Regret" (Thinking Machines, 2025): LoRA ต้องแปะทุก layer รวม
          MLP/MoE ("attention-only underperforms"), optimal LR ~ไม่ขึ้นกับ rank,
          LoRA แพ้ batch ใหญ่ → batch เล็กดี
  [t01] = บทเรียนที่พิสูจน์บนเครื่องจริงกับโมเดลตระกูลนี้เป๊ะๆ (t01_workflow.md):
        - lora_dropout ต้อง 0 — MoE ParamWrapper error จริงถ้าไม่ 0 (ตรงกับ [W])
        - r=64 OOM จริงบน 95GB ที่ MAX_LENGTH สูง → r=32 คือค่าที่รันผ่านจริง
        - paged_adamw_8bit (adamw_8bit ธรรมดา OOM ตอน optimizer step)
        - ip.size["longest_edge"] คือกลไกตั้ง max_pixels จริง (ip.max_pixels ไม่มีแล้ว
          บน transformers 5.x — AttributeError จริงบนเครื่องเช่า)
        - enable_thinking=False ตอน inference (ไม่งั้น CoT กิน token จนไม่ถึง JSON)
        - epilogue หลังเซฟ adapter ค้างได้ — SKIP_DEMO=1 ข้ามได้ adapter เซฟก่อนแล้ว
  [t02] = บทเรียน collator (rule_of_tune ข้อ 12 — บั๊ก 14x visual token):
        - UnslothVisionDataCollator ต้อง resize="max" (default "min" หา
          vision_config.image_size ไม่เจอ → ย่อ 512px เงียบๆ) + ส่ง max_seq_length
        - max_seq_length ต้องส่งตอน from_pretrained ด้วย (default 2048 ตัดกลาง image token)
  [t03] = วัดจากข้อมูลจริงรอบนี้ (2026-08-24):
        - MAX_LENGTH=32768: ตัวอย่างยาวสุดคือ gridline (4 ภาพ×5120 + prompt ~3.2k +
          gridmaster JSON ~3k) ≈ 26,791 tokens โดยประมาณ — 8 ตัวอย่างทะลุ 24576 ของ
          t01 เดิม (บั๊กคลาส t01 §0.4 จับได้ก่อนเทรนรอบนี้) 32768 = margin ~20%
          ⛔ ถ้า OOM: ลดจำนวนภาพ gridline 4→3 ใน build_dataset_t03.py แล้ว rebuild
             หรือลด lora_r — ห้ามลด MAX_LENGTH (จะตัด label gridmaster ทิ้งกลาง JSON)

dataset: train.jsonl (408) / val.jsonl (44) / images/ (353) — สร้างโดย build_dataset_t03.py
7 subtasks: section, schedule, notes, plan_beam, plan_footing, plan_slab, gridline

    TEST_STEPS=5 python3 train_t03.py     # ★ รันสั้นก่อนเสมอ (rule_of_tune ข้อ 4)
    python3 train_t03.py                   # รันเต็ม 3 epochs
    SKIP_DEMO=1 python3 train_t03.py       # ข้าม demo generation ท้ายรัน

⚠️ rule_of_tune ข้อ 2: ค่าในไฟล์นี้กำหนดว่าโมเดลเรียนอะไร/เห็นภาพละเอียดแค่ไหน —
   แก้แล้วผลเปลี่ยน ต้องเตือน/บันทึกก่อนแก้เสมอ
"""
import gc
import json
import os
import sys
from collections import Counter
from pathlib import Path

# [t01] ต้องตั้งก่อน import torch — ลด CUDA fragmentation (OOM จริงบนเครื่องเช่า
# 2026-07-21 ขาด ~100MB จาก 95GB; t03 ใช้ MAX_LENGTH สูงกว่า t01 อีก ยิ่งจำเป็น)
# เจอว่าหายไปตอนทำ parity table (rule_of_tune ข้อ 12) 2026-08-24
os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")

# ─────────────────────────────────────────────────────────────
# ค่าหลัก — ที่มากำกับทุกตัว (ดู docstring)
# ─────────────────────────────────────────────────────────────
MODEL = "unsloth/Qwen3.6-35B-A3B"   # ✅ มะขามเคาะ 2026-08-24: ใช้ Qwen3.6 (ตัว t01) ไม่ใช่ Qwen3-VL
LOAD_IN_4BIT = False                # [W] MoE QLoRA 4-bit ไม่รองรับ — bf16 เท่านั้น (~74GB)
MAX_PIXELS = 5120 * 1024            # [t01] 5,120 visual tokens/ภาพ — เท่าตอน t01 เทรน/วัดผล
MIN_PIXELS = 256 * 1024             # [t01]
MAX_LENGTH = 32768                  # [t03] วัดจากข้อมูลจริง — ดู docstring ห้ามลด
# [t03] ลด 32→16 หลัง OOM จริง 2026-08-24 23:00 (ใช้ 93.07 จาก 94.97 GiB เหลือ 470 MiB)
#   Unsloth เปิด LoRA บน MoE experts ทั้ง 256 ตัว → r=32 ให้ trainable 1.89B params
#   ซึ่งกิน LoRA 3.78GB + gradient 3.78GB + optimizer states 8-bit 3.78GB บนการ์ดที่มี
#   น้ำหนักโมเดล 74GB อยู่แล้ว → เหลือให้ activation ไม่พอสำหรับ sequence 30k token
#   r=16 คืน ~5.7GB (ทั้งสามก้อนลดครึ่ง) ขาดอยู่จริงแค่ ~1-2GB จึงเหลือ margin ~4GB
#   alpha ลดตามให้อัตราส่วน alpha/r = 2 เท่าเดิม (เท่า t01) — scaling ที่โมเดลเห็นไม่เปลี่ยน
#   [W] LWR: จำนวน layer ที่แปะสำคัญกว่า rank — เรายังแปะครบทุก layer รวม MoE เหมือนเดิม
#   854 ตัวอย่างใช้ capacity ของ r=16 ไม่หมดอยู่แล้ว
LORA_R, LORA_ALPHA = 16, 32
EPOCHS = 3                          # [t01] เท่ารอบที่พิสูจน์ eval_loss ลงต่อเนื่อง 3 epoch
LR = 1e-4                           # [t01] พิสูจน์ converge; [W] LWR: LoRA LR ~10x FullFT
                                    #   และ ~ไม่ขึ้นกับ rank — 1e-4 อยู่ในช่วงมาตรฐาน LoRA
BATCH, GRAD_ACCUM = 1, 8            # [t01]; [W] LWR: LoRA แพ้ batch ใหญ่ — 1 ดีอยู่แล้ว
# env var เหมือน t01/t02 (parity table 2026-08-24) — default 0 = freeze เท่าเดิมเป๊ะ
# การทดลอง A/B รอบหน้า: FINETUNE_VISION=1 python3 train_t03.py (ไม่ต้องแก้ไฟล์)
FINETUNE_VISION = os.environ.get("FINETUNE_VISION", "0") == "1"
                                    # [t01] จงใจ freeze — vision encoder byte-identical กับ
                                    #   base → ใช้ mmproj official ตอน export GGUF ได้เลย
                                    #   (หัวใจของ t01 export strategy — เปลี่ยนเมื่อไหร่
                                    #   เส้นทาง GGUF+mmproj พังทันที) [W] docs บอกว่า unfreeze
                                    #   อาจแม่นขึ้น — เป็นการทดลองของรอบหน้า ไม่ใช่รอบนี้
OUT_DIR = "outputs_t03"

TEST_STEPS = int(os.environ.get("TEST_STEPS", "0"))
SKIP_DEMO = os.environ.get("SKIP_DEMO", "0") == "1"
# ─────────────────────────────────────────────────────────────

from unsloth import FastVisionModel
import torch
from PIL import Image

HERE = Path(__file__).parent


def load_split(name):
    """jsonl → PIL Image objects (Unsloth ต้องการ object ไม่ใช่ path)
    คืน subtask_list แยกต่างหาก — ห้ามยัด key เพิ่มใน rows (collator อาจสะดุด)"""
    rows, subtasks, subtask_list = [], Counter(), []
    with open(HERE / f"{name}.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            subtasks[r.get("subtask", "?")] += 1
            subtask_list.append(r.get("subtask", "?"))
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
    return rows, subtasks, subtask_list


train_ds, train_sub, _ = load_split("train")
val_ds, val_sub, val_subtasks = load_split("val")
n_multi = sum(1 for r in train_ds
              if sum(1 for c in r["messages"][0]["content"] if c["type"] == "image") > 1)
print(f"train {len(train_ds)} | val {len(val_ds)} | multi-image {n_multi}")
print(f"train per-subtask: {dict(train_sub)}")
print(f"val   per-subtask: {dict(val_sub)}")

model, tokenizer = FastVisionModel.from_pretrained(
    MODEL,
    load_in_4bit=LOAD_IN_4BIT,
    use_gradient_checkpointing="unsloth",   # [W] docs: ลด VRAM + ยืด context
    max_seq_length=MAX_LENGTH,              # [t02] ต้องส่งตรงนี้ — default 2048 ตัดกลาง image token
)

# [t01] ip.size[...] คือกลไกจริงบน transformers 5.x (ip.max_pixels ไม่มีแล้ว)
# ip.size เป็น SizeDict — ห้ามเช็ค isinstance(dict) ก่อน (เป็น False เสมอ)
ip = tokenizer.image_processor
ip.size["longest_edge"] = MAX_PIXELS
ip.size["shortest_edge"] = MIN_PIXELS
print(f"image processor: max={ip.size['longest_edge']} px "
      f"(= {ip.size['longest_edge'] // 1024} visual tokens/ภาพ)")

model = FastVisionModel.get_peft_model(
    model,
    # [W] LWR: แปะทุก layer รวม MLP/MoE — attention-only underperforms
    # (router/gate ของ MoE: unsloth ปิดเทรนให้เอง by default — [W] "not a good idea")
    finetune_vision_layers=FINETUNE_VISION,
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=LORA_R, lora_alpha=LORA_ALPHA,
    lora_dropout=0,                 # [W]+[t01] MoE ParamWrapper ไม่รองรับ dropout!=0 — error จริง
    bias="none", random_state=3407, use_rslora=False, loftq_config=None,
)

from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig

FastVisionModel.for_training(model)

# [t02] resize="max" บังคับ — default "min" หา vision_config.image_size ของตระกูลนี้ไม่เจอ
# → ย่อ 512px เงียบๆ = เสียความละเอียด ~25 เท่า (บั๊กที่ทำ A/B t01-vs-t02 รอบแรกพังทั้งรอบ)
# completion_only_loss=True: [W] docs "should always be True" — เขียนไว้ชัดตาม rule_of_tune
# ข้อ 12 (ค่า default ที่ไม่เขียนคือตัวแปรที่หายจาก parity table)
collator = UnslothVisionDataCollator(model, tokenizer, resize="max",
                                     max_seq_length=MAX_LENGTH)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    data_collator=collator,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    args=SFTConfig(
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        warmup_ratio=0.05,
        num_train_epochs=EPOCHS,
        **({"max_steps": TEST_STEPS} if TEST_STEPS else {}),
        learning_rate=LR,
        logging_steps=5,
        # [t03] เปลี่ยนจาก paged_adamw_8bit → adamw_8bit หลังพัง 2026-08-24 22:45
        # step 42/321: CUDA illegal memory access โผล่ใน bitsandbytes sync_gpu ตอน optimizer step
        # บริบท: trainable 1.89B params (Unsloth เปิด LoRA บน MoE experts ทั้ง 256 ตัว) +
        # "smartly offload gradients" + "double buffering (parallel H2D)" = ความดันหน่วยความจำสูงมาก
        # paged = จองผ่าน unified memory (cudaMallocManaged) ซึ่งสปิลไป host ได้ — เป็นกลไกที่
        # traceback ชี้ตรงและเป็นแหล่ง illegal-address คลาสสิก. non-paged ใช้ VRAM เท่าเดิม (states
        # 8-bit ~3.8GB) แค่ไม่ paging → ถ้าจะ OOM จะ OOM ที่ step 1 ให้รู้ทันทีใน 2 นาที
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=3407,                  # [W] docs
        output_dir=OUT_DIR,
        report_to="none",
        # [t03] เดิม save_strategy="epoch" → พังที่ step 42 ก่อนถึง epoch 1 (step 107)
        # = ไม่มี checkpoint เลย เสียไป 40 นาที. ทุก 25 step เสียมากสุด ~23 นาที
        # adapter 1.89B params bf16 ≈ 3.8GB/ครั้ง × เก็บ 2 = ~8GB (ดิสก์ว่าง 74GB)
        save_strategy="steps",
        save_steps=25,
        save_total_limit=2,
        # [t03] ⛔ eval ต่อ epoch ปิดไว้ — OOM จริง 2026-08-24 (TEST_STEPS=5 ผ่าน 5 step
        # แล้วตายตอน evaluate): accelerate ห่อ model.forward ด้วย convert_to_fp32 ซึ่ง
        # upcast logits ทั้งก้อนเป็น fp32 = seq 21,445 × vocab 152k × 4B ≈ 13GB (+ต้นทาง
        # bf16 6.5GB) → ขอ 24.72GB ไม่ได้ ตอนเทรนไม่เจอเพราะ Unsloth ใช้ fused/chunked loss
        # ไม่ materialize logits เลย. t01 ไม่เจอเพราะภาพโดนย่อ 512px (seq สั้น), t02 ไม่เจอ
        # เพราะโมเดลเล็กกว่า (30B) เหลือ headroom มากกว่า — t03 คือรอบแรกที่ 35B + ความ
        # ละเอียดเต็มพร้อมกัน. save_strategy="epoch" ยังอยู่ → มี checkpoint ทั้ง 3 epoch
        # ให้ย้อนวัดได้ด้วย eval แบบ generate (ตัววัดจริงของ t03 อยู่แล้ว)
        eval_strategy="no",
        per_device_eval_batch_size=1,
        remove_unused_columns=False,          # บังคับสำหรับ vision fine-tuning
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        max_length=MAX_LENGTH,
        bf16=True,                  # [W] MoE ตระกูลนี้ = bf16 setup เท่านั้น
    ),
)

# ── ตรวจ batch แรกก่อนเผาเวลาเทรน: (1) ภาพไม่โดนย่อเงียบๆ (2) seq ยาวสุดไม่โดนตัด
try:
    # ตัวอย่างแรก (ภาพเดียว)
    _b = collator([train_ds[0]])
    _gt = _b.get("image_grid_thw")
    if _gt is not None:
        _tok = int((_gt[:, 1] * _gt[:, 2]).sum()) // 4
        print(f"✓ batch แรก: ~{_tok} visual tokens, seq={_b['input_ids'].shape[-1]}")
        assert _tok > 1000, f"visual tokens = {_tok} ต่ำผิดปกติ — resize='max' ไม่มีผล?"
    # ตัวอย่างที่ "น่าจะยาวสุด" — ต้องประเมินจากภาพ+prompt+GT ไม่ใช่จำนวนภาพอย่างเดียว
    # (2026-08-24: ชุด op04 มี gridline GT ยาวถึง 19,114 ตัวอักษร — ตัวที่ภาพเยอะสุด
    #  ไม่ใช่ตัวที่ยาวสุดเสมอไป assert เดิมจึงมองไม่เห็นตัวที่เสี่ยงจริง)
    def _est(row):
        vis = sum(min(c["image"].size[0] * c["image"].size[1], MAX_PIXELS) // 1024
                  for c in row["messages"][0]["content"] if c["type"] == "image")
        txt = sum(len(c["text"]) for c in row["messages"][0]["content"] if c["type"] == "text")
        a = row["messages"][1]["content"]
        gt = "".join(x.get("text", "") for x in a) if isinstance(a, list) else a
        return vis + (txt + len(gt)) / 2.2
    _top = sorted(range(len(train_ds)), key=lambda i: _est(train_ds[i]), reverse=True)[:3]
    for _rank, _gi in enumerate(_top, 1):
        _b2 = collator([train_ds[_gi]])
        _seq = _b2["input_ids"].shape[-1]
        print(f"✓ ตัวอย่างยาวอันดับ {_rank}: seq={_seq} (est {_est(train_ds[_gi]):.0f}, "
              f"MAX_LENGTH={MAX_LENGTH})")
        assert _seq < MAX_LENGTH, (f"seq {_seq} >= MAX_LENGTH {MAX_LENGTH} — โดนตัด! "
                                   f"label จะขาดกลาง JSON (บั๊กคลาส t01 §0.4) "
                                   f"— ตัดตัวอย่างนี้ทิ้งหรือลดจำนวนภาพ gridline ห้ามลด MAX_LENGTH")
        del _b2
    del _b, _b2, _gt
    gc.collect(); torch.cuda.empty_cache()
except AssertionError:
    raise
except Exception as e:
    print(f"⚠️  ตรวจ batch แรกไม่สำเร็จ ({e}) — ดู VRAM/loss ตอนเทรนให้ดี")

gpu = torch.cuda.get_device_properties(0)
print(f"GPU: {gpu.name} {gpu.total_memory / 1024**3:.1f} GB")
if not LOAD_IN_4BIT and gpu.total_memory / 1024**3 < 74:
    print("⚠️  VRAM < 74GB สำหรับ bf16 LoRA 35B-A3B — เสี่ยง OOM สูง")
print(trainer.train())
print(f"peak VRAM: {torch.cuda.max_memory_allocated() / 1024**3:.1f} GB")

model.save_pretrained(f"{OUT_DIR}/lora")
tokenizer.save_pretrained(f"{OUT_DIR}/lora")
print(f"✓ เซฟ LoRA adapter ที่ {OUT_DIR}/lora")

# ── demo 3 ตัวจาก val — [t01] บล็อกนี้เคยค้างกิน VRAM ไม่ยอมจบ; adapter เซฟไปแล้ว
#    ค้างเมื่อไหร่ kill -9 ได้เลย ไม่ถือว่าเทรนพัง หรือ SKIP_DEMO=1 ข้ามแต่แรก
def setup_grammar():
    """xgrammar builtin JSON grammar — มะขามสั่ง 2026-08-24: หน้า beam plan ต้องแนบ xgrammar
    ตอนส่งเสมอ (หน้าคลาสนี้คือตัววนซ้ำ/JSON ไม่ปิด: บ้าน08 หน้า20 48→2 collapse, ดู
    rule_of_tune ข้อ 13 — xgrammar พิสูจน์บน GPU แล้ว 96.8% vs 57.9%)
    tokenizer จริงต้องแกะจาก processor wrapper (.tokenizer) — คืน None ถ้าใช้ไม่ได้"""
    try:
        import xgrammar as xgr
        cfg = model.config
        vocab = getattr(cfg, "vocab_size", None) or cfg.text_config.vocab_size
        tok_info = xgr.TokenizerInfo.from_huggingface(tokenizer.tokenizer, vocab_size=vocab)
        compiled = xgr.GrammarCompiler(tok_info).compile_builtin_json_grammar()
        return lambda: {"logits_processor": [xgr.contrib.hf.LogitsProcessor(compiled)]}
    except Exception as e:
        print(f"⚠️  xgrammar ใช้ไม่ได้ ({e}) — demo หน้า beam จะรันแบบไม่ constrain")
        return None


if SKIP_DEMO:
    print("ข้าม demo generation (SKIP_DEMO=1)")
else:
    FastVisionModel.for_inference(model)
    grammar = setup_grammar()
    # เลือก demo ให้มี plan_beam อย่างน้อย 1 ตัวเสมอ (subtask ที่แบกความหวังรอบนี้)
    beam_idx = [i for i, s in enumerate(val_subtasks) if s == "plan_beam"]
    other_idx = [i for i in range(len(val_ds)) if i not in beam_idx]
    demo_idx = (beam_idx[:1] + other_idx)[:3]
    print(f"demo generation {len(demo_idx)} ตัว ({[val_subtasks[i] for i in demo_idx]}) "
          f"— ค้างเกิน ~10 นาที kill ได้เลย adapter เซฟแล้ว")
    for i in demo_idx:
        sample = val_ds[i]
        sub = val_subtasks[i]
        msgs = [sample["messages"][0]]
        # [t01] enable_thinking=False จำเป็น — ไม่งั้นโมเดล reasoning-native เขียน CoT
        # จนหมด token budget ก่อนถึง JSON (เทรนไม่กระทบ เป็นปัญหาเฉพาะ inference)
        text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True,
                                             enable_thinking=False)
        imgs = [c["image"] for c in msgs[0]["content"] if c["type"] == "image"]
        inputs = tokenizer(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
        gen_kwargs = dict(max_new_tokens=3000, do_sample=False)
        if sub == "plan_beam" and grammar is not None:
            gen_kwargs.update(grammar())   # LogitsProcessor เป็น stateful — ตัวใหม่ต่อ generate
        out = model.generate(**inputs, **gen_kwargs)
        pred = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        Path(f"{OUT_DIR}/sample_{sub}_{i}.json").write_text(pred, encoding="utf-8")
        try:
            json.loads(pred)
            ok = "JSON valid"
        except Exception as e:
            ok = f"JSON เสีย — {e}"
        gtag = " [xgrammar]" if (sub == "plan_beam" and grammar is not None) else ""
        print(f"  [{sub}]{gtag} ตัวอย่าง {i}: {ok} ({len(pred)} ตัวอักษร)")
        del inputs, out
        gc.collect(); torch.cuda.empty_cache()

print("\nขั้นต่อไป: วัดผลต่อ subtask (eval script ของ t03 ยังไม่มี — งานค้างใน t03_workflow.md)")
