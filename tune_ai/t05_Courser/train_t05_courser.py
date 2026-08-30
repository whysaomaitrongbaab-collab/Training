#!/usr/bin/env python3
"""
train_t05.py — fine-tune Qwen3.6-35B-A3B แบบ per-subtask (t05) ด้วย Unsloth + LoRA

🟡 รอบ t05 (2026-08-30): กลับสาย Qwen3.6 หลัง t04/InternVL3 ล้มเหลว (config `crop_to_patches`
   ขาด — โมเดลเห็นรูป 1 tile 256 tokens ตลอดการเทรน, ดู rule_of_tune ข้อ 15) — ไฟล์นี้ clone
   จาก train_t03.py (สคริปต์ที่รันผ่านจริง 854 ตัวอย่าง peak 87.5GB) แล้วปรับเป็น t05
   ตัวแปรทุกตัว + ที่มา + วิธีพังถ้าตั้งผิด: ดู t05_workflow.md §ตัวแปรทุกตัว

⚠️ ก่อนรันจริง (Phase 0 ใน t05_workflow.md): MAX_LENGTH ต้อง**วัดใหม่**กับ dataset t05
   (มี pass0/pass3 เพิ่ม — ห้าม copy 47,104 ของ t03 โดยไม่วัด) + batch-แรก assert ต้องเห็น
   ~7,680 tokens/ภาพจริง (probe ตาม rule ข้อ 15)

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

dataset: train_fold{0,1}.jsonl / val_fold{0,1}.jsonl — สร้างโดย build_4pass.py (รวม 4 pass,
  k-fold 2 ตาม house assignment ของ t04: fold0 = 1048/257, fold1 = 1101/204, 4:1 บ้านต่อ fold)
  pass1 (7 subtask) + pass0 + pass2.4 + pass3 — สัดส่วนต่อ fold ดู build_4pass.py ตอนรัน
  path รูปในไฟล์เทียบ "รากรีโป Training" (image/<บ้าน>/… , tune_ai/…/marked_t5/…)
  บ้าน val ต่อ fold ยึดตาม t04 (เทียบผลข้ามรอบได้ตรงบ้าน) — กฎเดียวกับแขน Voldemort เป๊ะ

    TEST_STEPS=5 python3 train_t05_courser.py   # ★ รันสั้นก่อนเสมอ (rule_of_tune ข้อ 4)
    python3 train_t05_courser.py                 # รันเต็ม 3 epochs (fold0 = default)
    FOLD=1 python3 train_t05_courser.py          # รัน fold1 (หลัง fold0 พิสูจน์แล้วว่าอ่านแบบได้)
    SKIP_DEMO=1 python3 train_t05_courser.py     # ข้าม demo generation ท้ายรัน

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
# [t03b 2026-08-25] 5120 → 7680 ตามคำสั่งมะขาม "เพิ่ม" หลังวัดด้วย measure_capacity.py:
#   ที่ 5,120 ภาพในชุดเทรน **973/973 ใบ (100%) โดนย่อ** — ตัวเล็กสุด 3307x2339 = 7,554 token
#   ก็ยังเกิน cap; ตัวใหญ่สุด 4631x3473 = 15,707 token เสียรายละเอียดไป 67%
#   ที่ 7,680: เหลือโดนย่อ 292/973 (30%) = ภาพ 3309x2339 (615 ใบ ส่วนใหญ่ของชุด) ได้ครบไม่ย่อ
#   ⛔ ห้ามขึ้นถึง 16,384 (ไม่ย่อเลย) บนการ์ด 96GB — คำนวณแล้ว peak 97.8 GB = เกินการ์ด
#      ต้อง H200 140GB ($3.29/ชม. = $17.45/รอบ เทียบการ์ดเดิม $5.87) ยังไม่ได้เช่า เครดิตไม่พอ
MAX_PIXELS = 7680 * 1024            # [t03b] 7,680 visual tokens/ภาพ (เดิม 5,120 = ย่อทุกใบ)
MIN_PIXELS = 256 * 1024             # [t01]
# [t03b] 32768 → 47104 บังคับตามข้อบน: seq ยาวสุดที่ 7,680 = 44,607 (ประมาณ) + margin 5%
#   ตัวที่ดันเพดานคือ gridline ล้วนๆ (36 ใน 37 ตัวที่ยาวเกิน ใช้ 4 ภาพ) subtask อื่นไม่แตะ
#   VRAM: activation โตเชิงเส้นกับ seq (flash attention) จากจุดวัดจริง 7.8GB @ 32,768
#   → 11.3GB @ 47,104 → peak ≈ 90.9 GB บนการ์ด 94.97 GB = เหลือ ~4.0 GB (เดิมเหลือ 7.5)
#   ⚠️ margin แคบลงจริง **ต้องรัน TEST_STEPS=5 ยืนยันก่อนรันเต็มเสมอ** (rule_of_tune ข้อ 4)
#   ถ้า OOM: ทางแก้ตามลำดับ (1) ลดภาพ gridline 4→3 ใน build_dataset_t03.py แล้ว rebuild
#   → seq ยาวสุดเหลือ 37,049 ตั้ง MAX_LENGTH 39,936 peak ≈ 89.2 GB  (2) ลด MAX_PIXELS กลับ 5,120
#   ห้ามลด MAX_LENGTH เฉยๆ โดยไม่ลด MAX_PIXELS (จะตัด label กลาง JSON — บั๊กคลาส t01 §0.4)
MAX_LENGTH = 47104                  # [t03b] วัดจากข้อมูลจริง — ดู docstring ห้ามลดเดี่ยวๆ
# [t03] ลด 32→16 หลัง OOM จริง 2026-08-24 23:00 (ใช้ 93.07 จาก 94.97 GiB เหลือ 470 MiB)
#   Unsloth เปิด LoRA บน MoE experts ทั้ง 256 ตัว → r=32 ให้ trainable 1.89B params
#   ซึ่งกิน LoRA 3.78GB + gradient 3.78GB + optimizer states 8-bit 3.78GB บนการ์ดที่มี
#   น้ำหนักโมเดล 74GB อยู่แล้ว → เหลือให้ activation ไม่พอสำหรับ sequence 30k token
#   r=16 คืน ~5.7GB (ทั้งสามก้อนลดครึ่ง) ขาดอยู่จริงแค่ ~1-2GB จึงเหลือ margin ~4GB
#   alpha ลดตามให้อัตราส่วน alpha/r = 2 เท่าเดิม (เท่า t01) — scaling ที่โมเดลเห็นไม่เปลี่ยน
#   [W] LWR: จำนวน layer ที่แปะสำคัญกว่า rank — เรายังแปะครบทุก layer รวม MoE เหมือนเดิม
#   854 ตัวอย่างใช้ capacity ของ r=16 ไม่หมดอยู่แล้ว
LORA_R, LORA_ALPHA = 16, 32
EPOCHS = 2                          # [2026-08-31 ค่ำ] มะขามเคาะ 3→2 หลัง research LoRA/QLoRA:
                                     # ผล accuracy/recall ต่าง 2 vs 3 epoch มักแค่ 1-3%, แต่ 3 epoch
                                     # กิน GPU-ชม.เพิ่ม 50% และ risk overfit สูงขึ้น (เริ่มท่องจำแทน
                                     # อ่านแบบ) — 2 epoch คือ sweet spot สำหรับ dataset ขนาดเล็ก-กลาง
                                     # ทาง LoRA ตามหลักทั่วไป · ถ้า val loss ยังลดต่อเนื่องไม่ flat
                                     # หลัง epoch 2 ค่อยพิจารณาต่อเป็น 3 (ดู eval_strategy หมายเหตุ
                                     # ด้านล่าง — ตอนนี้ปิด eval อยู่ ต้องเปิดถ้าจะใช้เกณฑ์นี้จริง)
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
OUT_DIR = "outputs_t05"  # [t05] แยกจาก outputs_t03/t04 — ห้ามทับ adapter รอบเก่า

# k-fold 2 (มะขามเคาะ 2026-08-31 ค่ำ: "epoch 3, k fold 2, train/val 4/1") — convention เดียวกับ
# t04: k=5 folds จริง (8 บ้าน/fold) รันแค่ fold0+fold1 → train 32 บ้าน / val 8 บ้าน = 4:1 ต่อ fold
# build_4pass.py เขียน train_fold{0,1}.jsonl / val_fold{0,1}.jsonl แล้ว (ไม่มี train.jsonl รวม
# อีกต่อไป — default จึงเป็น fold0 ไม่ใช่ "train" ที่ไม่มีไฟล์แล้ว):
#   FOLD=0 python3 train_t05_courser.py   (default)  ·  FOLD=1 python3 train_t05_courser.py
FOLD = os.environ.get("FOLD", "0")
TRAIN_SPLIT = f"train_fold{FOLD}"
VAL_SPLIT = f"val_fold{FOLD}"
OUT_DIR = f"outputs_t05_fold{FOLD}"
# [2026-08-31] มะขามสั่งเช่า 4 การ์ดพร้อมกัน: fold0+fold1 × Courser+Voldemort คู่ขนาน
# (แทนที่กฎเดิม "ห้ามรันหลาย fold คู่ขนาน" — ยกเลิกเพราะรอบนี้ dry-run ผ่านทั้งคู่แล้วก่อนรันเต็ม
# ต่างจาก t04 ที่พังตอน fold เดียวยังไม่พิสูจน์) หลังเทรนครบ รวม fold0+fold1 เป็น adapter เดียว
# ด้วย PEFT model soup (ดู ../merge_adapters_soup.py) ก่อนใช้งานจริง — ไม่ได้ deploy แยก 2 adapter
HUB_MODEL_ID = f"dacarokann/Courser_{'a' if FOLD == '0' else 'b'}"  # a=fold0, b=fold1
# push ขึ้น HF ด้วย token ใหม่ "t44" (FINEGRAINED) — export HF_TOKEN=hf_...XCRE ก่อนรัน
# (huggingface_hub อ่าน env HF_TOKEN เองอัตโนมัติ ไม่ต้องเรียก login() เพิ่ม)

TEST_STEPS = int(os.environ.get("TEST_STEPS", "0"))
SKIP_DEMO = os.environ.get("SKIP_DEMO", "0") == "1"
# ─────────────────────────────────────────────────────────────

from unsloth import FastVisionModel
import torch
from PIL import Image

HERE = Path(__file__).parent
# [t05] path รูปใน train.jsonl เทียบ "รากรีโป Training" ไม่ใช่โฟลเดอร์สคริปต์ — เพราะรูปกระจาย
# อยู่ 2 ที่ (image/<บ้าน>/ ของหน้าแบบ กับ tune_ai/t05_Courser/marked_t5/ ของ pass3) และแขน
# Voldemort ต้องใช้ path ชุดเดียวกันเป๊ะผ่าน media_dir ของ LLaMA-Factory
REPO_ROOT = HERE.parent.parent


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
                                    "image": Image.open(REPO_ROOT / c["image"]).convert("RGB")})
                else:
                    content.append({"type": "text", "text": c["text"]})
            rows.append({"messages": [
                {"role": "user", "content": content},
                {"role": "assistant", "content": r["messages"][1]["content"]},
            ]})
    return rows, subtasks, subtask_list


train_ds, train_sub, _ = load_split(TRAIN_SPLIT)
val_ds, val_sub, val_subtasks = load_split(VAL_SPLIT)
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


# ── ด่านกันตัด label กลาง JSON (บั๊กคลาส t01 §0.4) ────────────────────────────
# audit 2026-08-31 ชี้ว่า MAX_LENGTH มีแต่คอมเมนต์เตือน ไม่มีด่านจริง — ตัวเลขจาก
# measure_capacity.py เป็น "ประมาณ" (ข้อความหาร 2.2) ตรงนี้วัดจริง: visual token คำนวณตรง
# จากขนาดภาพ (แม่นยำ) + text token จาก tokenizer จริง (ไม่ต้องประมวลผลภาพ = เร็วไม่กี่วินาที)
# ถ้าเกิน = หยุดทันทีก่อนเสียค่าเช่า GPU ดีกว่าเทรนจบแล้วพบว่า label โดนตัดเงียบ ๆ
def preflight_seq_lengths(ds, name):
    px_per_token = 1024                      # patch 16 × merge 2 (processor_config จริง)
    cap = MAX_PIXELS // px_per_token
    worst, over = (0, None), []
    for i, r in enumerate(ds):
        vis, txt = 0, 0
        for c in r["messages"][0]["content"]:
            if c["type"] == "image":
                w, h = c["image"].size
                vis += min(w * h // px_per_token, cap)
            else:
                txt += len(tokenizer.tokenizer(c["text"], add_special_tokens=False)["input_ids"])
        a = r["messages"][1]["content"]
        gt = "".join(x.get("text", "") for x in a) if isinstance(a, list) else a
        txt += len(tokenizer.tokenizer(gt, add_special_tokens=False)["input_ids"])
        total = vis + txt
        if total > worst[0]:
            worst = (total, i)
        if total > MAX_LENGTH:
            over.append((total, i))
    print(f"preflight {name}: seq ยาวสุด {worst[0]:,} token (แถว {worst[1]}) "
          f"| MAX_LENGTH {MAX_LENGTH:,} | margin {(MAX_LENGTH - worst[0]) / MAX_LENGTH * 100:.1f}%")
    if over:
        raise SystemExit(
            f"⛔ {len(over)} แถวใน {name} ยาวเกิน MAX_LENGTH ({max(o[0] for o in over):,} > "
            f"{MAX_LENGTH:,}) — label จะโดนตัดกลาง JSON\n"
            f"   แก้ตามลำดับ: (1) ลดภาพ gridline 4→3 (2) ลด MAX_PIXELS "
            f"(3) เพิ่ม MAX_LENGTH ถ้า VRAM ไหว — ห้ามปล่อยผ่าน")


preflight_seq_lengths(train_ds, "train")
preflight_seq_lengths(val_ds, "val")
# ─────────────────────────────────────────────────────────────────────────────

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
        push_to_hub=True,
        hub_model_id=HUB_MODEL_ID,
        hub_strategy="checkpoint",
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
    # [แก้ 2026-08-25] เดิมคอมเมนต์ว่า "ตัวอย่างแรก (ภาพเดียว)" และเทียบ .sum() ของทุกภาพ
    # กับเกณฑ์ 1000 ของภาพเดียว — แต่ train_ds[0] ของชุด op04 มี 4 ภาพ ทำให้เกณฑ์หลวมลง 4 เท่า
    # ระดับหายนะแบบ t01 (266 token/ภาพ) x 4 ภาพ = 1,064 > 1000 → assert ผ่าน = จับไม่ได้
    # จึงหาร n_img ให้เป็น "ต่อภาพ" จริง และเทียบกับ cap ที่เราตั้งไว้เองด้วย
    _b = collator([train_ds[0]])
    _gt = _b.get("image_grid_thw")
    if _gt is not None:
        _n_img = int(_gt.shape[0])
        _tok_per_img = int((_gt[:, 1] * _gt[:, 2]).sum()) // 4 // max(_n_img, 1)
        _cap = MAX_PIXELS // 1024
        print(f"✓ batch แรก: {_n_img} ภาพ, ~{_tok_per_img} visual tokens/ภาพ "
              f"(cap ที่ตั้งไว้ {_cap}), seq={_b['input_ids'].shape[-1]}")
        assert _tok_per_img > 1000, (
            f"visual tokens = {_tok_per_img}/ภาพ ต่ำผิดปกติ — resize='max' ไม่มีผล? "
            f"(บั๊กคลาส t01 §0.4: ภาพโดนย่อ 512px เงียบๆ เหลือ ~266)")
        # เตือน (ไม่ abort) ถ้าได้ต่ำกว่า cap มาก — แปลว่ามีอะไรย่อภาพก่อนถึง cap ของเรา
        if _tok_per_img < _cap * 0.75:
            print(f"⚠️  ได้ {_tok_per_img}/ภาพ ต่ำกว่า cap {_cap} เกิน 25% — collator อาจย่อภาพ"
                  f" เองเพื่อให้พอดี max_seq_length ตรวจก่อนเชื่อว่าได้ความละเอียดเต็ม")
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
