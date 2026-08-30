# InternVL3-78B — dossier ฉบับเต็มสำหรับแขนขนาน (arm B) ของ t05

*ค้น 2026-08-31 (workflow 4 agents, ทุกข้อ verify จาก primary source — raw source code จริง/model card จริง
ไม่ใช่ blog) + ข้อเท็จจริง empirical จาก t04 ที่วัดเองกับมือ · จุดประสงค์: เทรน InternVL3-78B
รอบแก้มือขนานกับ Courser (Qwen3.6) ตามคำสั่งมะขาม "เทรน 2 ตัวขนานกันแบบเมื่อคืน"*

---

## 1. สถาปัตยกรรม (ยืนยันจาก config.json + paper arXiv 2504.10479)

- **ViT-MLP-LLM**: ตา = InternViT-6B-448px-V2_5 (~5.9B, hidden 3200, 45 layers) + MLP 2 ชั้น +
  สมอง = **Qwen2.5-72B (dense — ไม่ใช่ MoE)** รวม ~78.4B
- context 32,768 (V2PE — visual token ใช้ position increment เล็กกว่า text), dynamic RoPE ×2
- **การมองภาพ**: ตัด tile 448×448 · tile ละ 1024 patches (14px) → pixel-unshuffle ×0.25 →
  **256 tokens/tile** · เกิน 1 tile จะแถม thumbnail ทั้งภาพอีก 1 tile เสมอ (`use_thumbnail=True`
  **hardcode ใน transformers ไม่มี config ปิด**) → ภาพใหญ่ = 12+1 = **13 tiles = 3,328 tokens**
- ผล OCR/เอกสาร (paper): OCRBench 906 · DocVQA 95.4 · ChartQA 89.7 · OmniDocBench 80.33
- repo `-hf` = weights เดียวกับตัว OpenGVLab แปลงเป็น native transformers
  (`InternVLForConditionalGeneration` + `AutoProcessor`) — **transformers ≥ 4.52.0 เท่านั้น**
  (คลาสบั๊ก "Processor was not found" ใน LF issues #7959/#8799/#8855 = transformers เก่าไป)

## 2. ไขปริศนา t04 ครบทุกข้อ (ตอนนี้รู้กลไกจริงแล้ว ไม่ใช่แค่อาการ)

**ทำไมตอนเทรนได้ 1 tile:** LLaMA-Factory `mm_plugin.py` เปิด tiling เฉพาะเมื่อ
`getattr(processor, "crop_to_patches", False)` เป็นจริง — และ `preprocessor_config.json`
ของโมเดล**ตั้ง `crop_to_patches: false` มาจากโรงงาน** yaml เราไม่ได้ override → 1 tile ตลอด

**ทำไมตอน infer ได้ 13 tiles ทั้งที่ config โมเดลบอก false:** `InternVLProcessorKwargs._defaults`
ใน transformers (`processing_internvl.py` บรรทัด 34) **hardcode `crop_to_patches: True`
เป็น call-time kwarg ทุกครั้ง** — ค่าใน preprocessor_config เป็นแค่ fallback ที่ไม่เคยถูกใช้
(`_merge_kwargs` ไม่อ่าน config ของ image processor เลย) → inference tile เสมอ ปิดได้ต้องส่ง
`crop_to_patches=False` ตอนเรียกเท่านั้น — **train กับ infer จึง mismatch โดยดีไซน์ของสองไลบรารี
ที่ default คนละทาง ไม่ใช่ความซวยเฉพาะเรา**

**วิธีเปิด tiling ตอนเทรน (ยืนยันจาก source 3 ไฟล์):** เพิ่ม **`crop_to_patches: true`** ใน yaml —
LF ≥ v0.9.3 รองรับเป็น ProcessorArguments จริง (PR #7817, `patcher.py` setattr ลง processor)
⚠️ `max_patches: 12` / `min_patches: 1` **hardcode ใน plugin** ปรับผ่าน yaml ไม่ได้ —
คุมจำนวน tile ทางอ้อมด้วย `image_max_pixels` (ภาพถูกย่อก่อนตัด: ~1MP→~4-5 tiles, ~2MP→~8-9,
≥2.4MP→เต็ม 12+thumbnail)

## 3. 🔴 การค้นพบใหม่ — อาจเป็น "สาเหตุที่สอง" ของคืนที่แล้ว ซ้อนอยู่ใต้เรื่อง tile

**เอกสารทางการ InternVL เตือนตรง ๆ (quick_start, verbatim):** *"Due to significant quantization
errors with BNB 4-bit quantization on InternViT-6B, the model may produce nonsensical outputs
and fail to understand images. Therefore, please avoid using BNB 4-bit quantization."*
— ใช้กับรุ่น 38B/78B ที่ตาเป็น InternViT-6B (รุ่นเล็กใช้ InternViT-300M ไม่โดน)

**และ LF `quantization_bit: 4` quantize ทั้งก้อนไม่เว้นอะไรเลย** (`quantization.py` ไม่มี
`modules_to_not_convert` — verify จาก source) → **t04 เทรนโดย ViT ถูกบีบ 4-bit ที่ทางการบอกว่า
"ทำให้มองภาพไม่รู้เรื่อง" มาตลอด** สอดคล้องกับอาการที่เห็นเป๊ะ (ตอบเป็นบ้านคนละหลัง)
ถึงแก้ tile แล้ว ถ้ายัง 4-bit แบบเดิม **อาจตาบอดต่อ**

ไม่มีรายงานบวกของ QLoRA-4bit บน InternVL3-38B/78B ที่ไหนเลย (หาแล้ว) — มีแต่ negative
(ms-swift #1724 crash บน InternVL2-8B)

## 4. ทางเลือกของแขน InternVL (เรียงตามความเสี่ยง×ราคา)

| ทาง | VRAM/การ์ด | ราคา | ความเสี่ยง |
|---|---|---|---|
| **(ก) 78B QLoRA-4bit + crop_to_patches:true + ประตู go/no-go** | 96GB ใบเดียว (แบบเดิม) | gate ~$2 → เต็ม ~$25-40 | ⚠️ ฝืนคำเตือนทางการเรื่อง ViT-4bit — **แต่มีประตูตรวจถูก ๆ ก่อน**: โหลด base (ไม่มี adapter) แบบ 4-bit + tiling เต็ม แล้วให้อ่านแบบจริง 3-5 หน้า — ถ้า base อ่าน mark ได้ = ViT รอด 4-bit เดินต่อ / ถ้าเพ้อ = หยุดทันที เสียแค่ ~$2 ไม่ใช่ทั้งคืน |
| (ข) 78B **8-bit** LoRA | ~78GB weights → ต้อง H200 140GB (~$3.3-3.6/ชม.) | ~$60-90 | ทางการใช้ 8-bit ใน inference ได้จริง (2×80GB) แต่เทรน 8-bit บนการ์ดเดียว+seq 30k ไม่เคยมีใครยืนยัน |
| (ค) InternVL3.5-38B-hf (dense, LF รองรับแล้ว ~2025-08) | 4-bit บน 96GB สบาย / bf16 บน H200 | ~$15-25 | ตาเป็น InternViT-6B ตัวเดียวกัน → คำเตือน 4-bit โดนเหมือนกัน ต้องผ่านประตูเดียวกัน · paper อ้างดีกว่า 3.0 แต่ยังไม่มีเลขต่อ benchmark เทียบ 78B ตรง ๆ |
| (ง) bf16 LoRA 78B เต็มรูป | ~156GB weights → B200 179GB $5.3/ชม. ตึงมาก หรือ multi-GPU | $100+ | แพงเกินโปรเจกต์ตอนนี้ |

**คำแนะนำ (ตัดสินได้เลยถ้ามะขามไม่ค้าน): ทาง (ก)** — การ์ดใบเดียวเท่าเดิม แต่**บังคับผ่านประตู
go/no-go ก่อนเทรนเต็มเสมอ** (บทเรียน "ทดสอบถูกก่อนแพง" + rule ข้อ 15) ประตูนี้ตอบทั้งสองคำถาม
ในครั้งเดียว: ViT รอด 4-bit ไหม และ tiling ทำให้อ่าน mark ออกจริงไหม

## 5. YAML แก้มือ (ต่างจาก t04 สามบรรทัด + ข้อควรระวัง)

```yaml
# เหมือน train_t04_internvl3_qlora.yaml เดิมทุกอย่าง ยกเว้น:
crop_to_patches: true          # ← บรรทัดที่ฆ่าเราเมื่อคืน (LF ≥ 0.9.3)
image_max_pixels: 2359296      # 1536×1536 ≈ 9-10 tiles/ภาพ (~2,560 tokens) — จุดกลางระหว่าง
                               # รายละเอียด กับ VRAM/เวลา; เต็ม 12+1 tiles ใช้ 4194304 (2048²)
cutoff_len: 32768              # ต้องวัดใหม่หลังรู้ tile จริง — seq จะโตจาก ~9-17k เป็น ~15-30k
```
- **เวลา/step จะช้าลง**: t04 = 175-235s/step ที่ 256 tok/ภาพ → คาด ~250-400s/step → 306 steps
  ≈ 21-34 ชม. (ถ้า OOM: ลด image_max_pixels ก่อน อย่าลด cutoff_len เดี่ยว ๆ)
- **infer ต้อง match เทรน**: ส่ง `crop_to_patches=True, max_patches=12` (ค่าเดียวกับ LF hardcode)
  + `image_max_pixels` เดียวกัน — ห้ามใช้ AutoProcessor default ดิบ ๆ อีก (มัน tile เต็มเสมอ
  ไม่สน config) · decoder: ถอด `no_repeat_ngram_size`, `repetition_penalty=1.0` (บทเรียน t04)
- probe ก่อนเทรน: `probe_img_tokens.py` มีอยู่แล้ว — คราวนี้ค่าเทรนต้องเห็น **~2,300-3,328
  tokens/ภาพ** ไม่ใช่ 256 (รัน CPU ฟรี ก่อนกดเช่า)

## 6. งบรวม 2 แขนขนาน

| แขน | การ์ด | ประมาณ |
|---|---|---|
| A: Courser (Qwen3.6, scope คุมงบ) | RTX PRO 6000 96GB ×1 | ~$13-15 |
| B: InternVL3-78B แก้มือ (ทาง ก) | RTX PRO 6000 96GB ×1 | gate $2 + เต็ม $25-40 |
| **รวม** | 2 ใบขนาน | **~$40-57** |

**⛔ เครดิต $16.66 ไม่พอแน่นอนสำหรับ 2 แขน — ต้องเติมก่อนเช่า (ขั้นต่ำแนะนำ +$50)**

---
*แหล่งหลัก: [LF model_args.py](https://raw.githubusercontent.com/hiyouga/LLaMA-Factory/main/src/llamafactory/hparams/model_args.py) · [LF PR #7817](https://github.com/hiyouga/LLaMA-Factory/pull/7817) · [transformers processing_internvl.py](https://raw.githubusercontent.com/huggingface/transformers/main/src/transformers/models/internvl/processing_internvl.py) · [InternVL3-78B model card](https://huggingface.co/OpenGVLab/InternVL3-78B) · [InternVL3 paper](https://arxiv.org/html/2504.10479v1) · [คำเตือน BNB-4bit ViT (quick_start ทางการ)](https://internvl.readthedocs.io/en/latest/internvl3.0/quick_start.html) · [InternVL3 finetune ทางการ](https://internvl.readthedocs.io/en/latest/internvl3.0/finetune.html) · [InternVL3.5-38B](https://huggingface.co/OpenGVLab/InternVL3_5-38B)*
