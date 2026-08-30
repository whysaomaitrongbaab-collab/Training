# t04 workflow — Purson (InternVL3-78B fine-tune on t04 dataset + hint arm 2 vs 2.4a)

> ## 🟢 นี่คือเอกสารของ **รอบ t04 (Purson)** — อัปเดตล่าสุด 2026-08-30 กลางดึก: เทรนจริงแบบ k-fold **4 folds** (ไม่ใช่ 2 อย่างที่เคยเขียนไว้) คู่ขนาน 4 การ์ด — **fold1 (จาก instance fold0) และ fold3 (จาก instance fold2) เทรนเสร็จแล้ว + อัป HF + Day-of-Shame verify ผ่านทั้งคู่** — fold2/fold4 (instance fold1/fold3) ยังเทรนอยู่ 90%+ · eval แบบสุ่ม 24/fold (ไม่ใช่เต็ม 205 — ประหยัดเวลา) กำลังรันบน fold1/fold3 ที่เสร็จแล้ว
>
> | | |
> |---|---|
> | รอบ | **t04_Purson** |
> | โมเดล | ✅ **`OpenGVLab/InternVL3-78B`** (มะขามเคาะ 2026-08-29) — dense 78B, สมองข้างในคือ Qwen2.5-72B-Instruct + ตา InternViT-6B, ไลเซนส์ Apache-สืบทอด ใช้เชิงพาณิชย์ได้, ขึ้น OmniDocBench 83.76 (ตัวเดียวใน 10 ตัวที่เช็คที่ขึ้น leaderboard จริง — ดู `แคตตาล็อก_AI_ทางเลือก_2026-08-26.md`) |
> | framework เทรน | ✅ **LLaMA-Factory** (มะขามเคาะ 2026-08-29 — Unsloth ใช้กับ InternVL3 ไม่ได้, issue #3401/#2341) → `train_t03.py`/`infer_house_t03.py` เดิม (Unsloth) **ใช้กับรอบนี้ไม่ได้ ต้องเขียนใหม่** — เก็บไว้เป็น reference ยุค Qwen พร้อม header เตือนแล้ว |
> | adapter ที่จะได้ | ใหม่ทั้งอัน — LoRA บน InternVL3-78B (ชื่อโฟลเดอร์/HF repo ยังไม่ตั้ง — ห้ามใช้ `outputs_t03`/`Sicilian44/t03` ของเดิม) |
> | โฟลเดอร์ข้อมูล | `tune_ai/t04_Purson/data_before_tune/` |
> | สถานะ | dataset build ล่าสุด: train 1020 / val 229 ตัวอย่าง จาก 40 หลัง — **แต่ jsonl อยู่ในฟอร์แมต messages ของสาย Unsloth/Qwen ต้องแปลงเป็นฟอร์แมตของ framework ใหม่ก่อน** · prompt ทุก pass (0/2/2.4/2.5/3) เขียนเสร็จ (prompt เป็นข้อความล้วน ใช้ต่อได้ทุกโมเดล ไม่ต้องแก้) · sidecar CV 5 บ้าน val พร้อม |
>
> **⚠️ เครื่องหมาย ✅ ทุกตัวในไฟล์นี้เป็นของ t04 เท่านั้น** — ห้ามหยิบ ✅ ของ t01/t02/t03 มาอ่านว่าเป็นของรอบนี้ (DAY-OF-SHAME class)
> สัญลักษณ์: ⬜ ยังไม่ทำ · 🔍 Claude ทำ/ตรวจแล้ว มีหลักฐาน แต่มะขามยังไม่ยืนยัน · ✅ มะขามยืนยันแล้ว

**อะไรต่างจาก t03 (2 แกนพร้อมกัน — ต้องรู้ตอนอ่านผล):**
1. **โมเดลเปลี่ยนตระกูล** — Qwen3.6-35B-A3B (MoE, active 3B) → InternVL3-78B (dense 78B) คนละสถาปัตยกรรม
   คนละ framework → ตัวเลขที่ได้เทียบกับ t03 เป็นการเทียบข้ามสถาปัตยกรรม ไม่ใช่ controlled A/B
2. **dataset/prompt คนละชุด** — 7 pass ใหม่ (plan แยก 4 subtask จริง, ล้าง markdown noise, กฎวัดสัดส่วน
   เทียบ gridmaster, dictionary ฝังทุก prompt) + การทดลอง hint arm 2 vs 2.4a
รายละเอียดสายพานเต็มอยู่ [README.md](README.md) · เหตุผลเลือก/ตกรอบโมเดลอยู่
`workmen's_diary/แคตตาล็อก_AI_ทางเลือก_2026-08-26.md` (InternVL3-78B เดิมตกรอบเพราะ "สมองเป็น Qwen อยู่ดี" —
มะขามรับเงื่อนไขนั้นแล้ว เคาะใช้ 2026-08-29)

---

## Phase 0 — Pre-flight (rule_of_tune ข้อ 4: ทำจริง+ตรวจจริง ก่อนเสียเงินเช่า)

| # | รายการ | สถานะ |
|---|---|---|
| 1 | **เลือกโมเดล** | ✅ มะขามเคาะ 2026-08-29: **InternVL3-78B** |
| 2 | **เลือก framework เทรน** — LLaMA-Factory vs ms-swift (Unsloth ตกรอบ: ใช้กับ InternVL3 ไม่ได้) | ✅ มะขามเคาะ 2026-08-29: **LLaMA-Factory** (มีคนยืนยันเทรน InternVL3-78B LoRA จริง — diary 2026-08-25; ms-swift พักไว้เป็นทางเลือกสำรอง ยังไม่ยืนยันกับ 78B โดยเฉพาะ) |
| 3 | **สคริปต์เทรนใหม่** — `train_t04_internvl3_qlora.yaml` (LLaMA-Factory config) | ✅ dry-run จริงบนการ์ดเช่าผ่านแล้ว 2026-08-30 (5 steps, `max_steps=5 save_steps=5` — **syntax ถูกคือ `key=value` ไม่มี `--` นำหน้า**, ลองแบบมี `--` ก่อนแล้ว parser พัง แก้แล้ว): loss 1.297 (ปกติ), grad_norm 0.24, **VRAM peak 54.6GB/97.9GB** (เหลือ headroom ~43GB สบาย), **ไม่มี truncation warning** (แต่สุ่มแค่ 40/1020 แถว ไม่ครอบคลุม 100%), checkpoint เซฟสำเร็จครบ · `cutoff_len`/`image_max_pixels`/`lora_rank` ผ่านการทดสอบเบื้องต้นแล้ว ถือว่าใช้ได้ · **`num_train_epochs` เปลี่ยนหลายรอบคืนนี้: 3.0 → 5.0 → 4.0 → กลับมา 3.0 (ค่าสุดท้ายที่ใช้เทรนจริงทั้ง 4 folds)** เหตุผลค่าสุดท้าย: ให้ k-fold 4 folds อยู่ในงบ ไม่ใช่ค่าที่วัด converge จริง — loss ทั้ง 4 folds ลดต่อเนื่องปกติถึง epoch 3 ไม่มีสัญญาณ overfit · **⚠️ พบตอน eval: `Token indices sequence length ... (17773 > 8192)` — sequence ยาวเกิน tokenizer model_max_length จริง (inference ยัง generate ได้ปกติ แต่ไม่ยืนยันว่าตอนเทรนตัด label หรือเปล่า — คำถามเปิด)** |
| 4 | **แปลง dataset** — train/val.jsonl → ฟอร์แมต LLaMA-Factory sharegpt | ✅ `build_dataset_llamafactory.py` เขียน+รันจริงแล้ว 2026-08-30: **1020 train / 229 val แปลงผ่านหมด**, assert ยืนยันลำดับ image-ก่อน-text ทุกแถวจริง (ไม่ใช่แค่สมมติ), sanity-check `<image>` token count = `images[]` length ทุกแถว, **0 ไฟล์รูปหาย** (เช็คจริงว่าทุก path resolve) → `train_lf.json`/`val_lf.json`/`dataset_info.json` พร้อมใช้ |
| 5 | **GPU sizing** | ✅ มะขามเคาะ 2026-08-30: **QLoRA 4-bit บนการ์ดใบเดียว 96GB** — **ยืนยันด้วยตัวเลขจริงแล้ว 2026-08-30** (ไม่ใช่แค่ทฤษฎี): VRAM peak จริง **54.6GB/97.9GB** ระหว่าง dry-run บน RTX PRO 6000 Max-Q (เหลือ headroom ~43GB) ไม่ OOM ยืนยันการ์ดใบเดียว 96GB พอจริงสำหรับ InternVL3-78B QLoRA 4-bit ทั้ง dry-run และเทรนเต็ม (**ใช้การ์ดใบเดียวกันตลอด ไม่ต้องเปลี่ยนการ์ดระหว่าง dry-run → เทรนเต็ม**) |
| 6 | dataset (ฝั่ง GT/รูป) พร้อม — train 1020 / val 229 / 40 หลัง / images 780 ไฟล์, สแกน 1249 text block ผ่าน 0 อักขระต้องห้าม | ✅ build 2026-08-29 (เนื้อหาใช้ต่อได้ รอแค่แปลงโครงตามข้อ 4) |
| 7 | sidecar CV (`cv_val/`) สำหรับ arm 2.4a | ✅ 23 `_hint.txt` (pass 1.5 → arm 2.4a) + 23 `_hint25.txt` (pass 2.5 → pass 3, คนละชุด อย่าสับสน) — hint เป็นข้อความล้วน ใช้กับโมเดลไหนก็ได้ |
| 8 | self-check เครื่องมือ CV | ✅ `cv_scan.py --demo` + `merge_guard.py` ผ่าน (รันจริง 2026-08-29) — เครื่องมือฝั่ง CV ไม่ผูกกับโมเดล ไม่กระทบจากการเปลี่ยน |
| 9 | **สคริปต์ infer/eval ใหม่** — `infer_house_t04.py` | 🔍 เขียนแล้ว 2026-08-30 — port `score_ids()`/`element_ids()`/`strip_fence()`/`apply_arm()`/`hide_grid_lines()` จาก `infer_house_t03.py` ตรงๆ (logic ล้วน ไม่ผูก Unsloth) + เขียนใหม่ส่วนโหลดโมเดล/generate ด้วย `transformers`+`bitsandbytes`(4-bit)+`peft` · `py_compile` ผ่าน + **`--selftest` ผ่านทุกข้อ** (เช็ค 5 ฟังก์ชันด้วยข้อมูลจำลอง ไม่ต้องมี GPU) · **⚠️ ส่วนโหลดโมเดล/generate ยังไม่เคยรันจริงบน GPU** — 3 จุดเสี่ยงระบุไว้ในหัวไฟล์ (chat template จริงของ InternVL3-78B-hf / tokenizer attribute จริงสำหรับ xgrammar / bitsandbytes โหลดโมเดลได้จริง) ต้อง probe ก่อนเชื่อ (rule_of_tune ข้อ 13) |
| 10 | onstart.sh ใหม่ (ตัวเดิมติดตั้ง unsloth — ผิด stack, framework เคาะแล้ว = LLaMA-Factory) | ✅ รันจริงบนเครื่องเช่าแล้ว 2026-08-30 ไม่มี error: transformers ลงตัวที่ **4.57.6** (ลง 5.16.1 ก่อน แล้ว xgrammar บังคับ `<5` pip downgrade ให้เอง — พฤติกรรมถูกต้อง), torch 2.8.0+cu128, bitsandbytes 0.50.2, llamafactory-cli 0.9.6.dev0 ยืนยัน `image: pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel` (ต้อง >=2.7.0 เท่านั้นสำหรับ Blackwell sm_120 — เช็คจริงก่อนเช่า) ใช้งานได้จริง |
| 11 | **HF repo — ตั้งชื่อตาม "Purson" (ชื่อจริงของ t04)** | ✅ มะขามเคาะ 2026-08-30: **5 repo แยกกัน แต่ละ fold มีของตัวเอง** — `Sicilian44/Purson-fold1-weights` · `-fold2-` · `-fold3-` · `-fold4-` (adapter ของแต่ละ fold; เลข fold ฝั่ง HF นับจาก 1 ตามที่มะขามเรียก ส่วนโฟลเดอร์ในเครื่อง `outputs_t04/fold0..3` นับจาก 0) + `Sicilian44/Purson-weights` (soup ตัวจริง, ป้าย unbenchmarked) · **ไม่มี `Purson-gguf` แล้ว** (ข้อ 14 ยกเลิก) · **โควตาเช็คแล้วพอสบาย**: adapter ละ ~840 MB (210.5M params fp32) × 5 = **~4.2 GB** จาก public quota 8.7 TB (ใช้ไป 0.03 TB) = 0.05% — ไม่ต้องเก็บลง drive D ตามที่เคยสำรองไว้ |
| 12 | Vast.ai เครดิต+บิล — เช็คผ่าน `vastai search offers` (dph_total) เท่านั้น (บทเรียน 30x-misread) | ✅ เติมเครดิตเป็น **$52.46** (2026-08-30) ก่อนเช่า — เช็คด้วย `vastai show user --raw` (`credit` field) จริง |
| 13 | dry run สั้นบน**การ์ดถูก**ก่อนเสมอ (เทียบเท่า TEST_STEPS=5 ของรอบก่อน — ชื่อ flag ตาม framework ที่เลือก) | ✅ ผ่าน 2026-08-30 (ดูรายละเอียดเต็มในข้อ 3) — **ใช้การ์ดเดียวกับที่เทรนเต็มต่อเลย ไม่ได้แยก "การ์ดถูก" กับ "การ์ดจริง" คนละใบแบบรอบก่อนๆ** |
| 14 | ~~**GGUF+mmproj export**~~ | ❌ **ยกเลิก — มะขามเคาะ 2026-08-30 คืนนี้: "เรื่องแปลง gguf ไม่ต้องก็ได้ เอาแต่ adapter พอ"** รอบนี้ส่งมอบเป็น **LoRA adapter อย่างเดียว** ไม่ทำ GGUF/mmproj และไม่มี repo `Purson-gguf` · เหตุผลเบื้องหลังที่ยังเก็บไว้เผื่อรอบหน้าอยากทำ: **ความเสี่ยงจริง พบ 2026-08-30:** `convert_hf_to_gguf.py` ของ llama.cpp รองรับ InternVL3 เฉพาะ checkpoint **"non-hf" (ดั้งเดิม)** เท่านั้น — เอกสารระบุชัดว่า `InternVL3-*-hf` **ใช้ไม่ได้** แต่ pipeline ทั้งรอบนี้ (LLaMA-Factory/transformers/peft) บังคับเทรนบนตัว `-hf` เพราะ LLaMA-Factory ลงทะเบียนไว้แบบนั้น → เทรน LoRA บน `-hf` → merge → **ยังไม่มีใครยืนยันว่าป้อน `convert_hf_to_gguf.py --mmproj` (ตัว non-hf) แล้วอ่านออกจริงไหม** (คนละ checkpoint format — อาจแค่ config/class ต่างแต่ tensor เดียวกันเลยแปลงได้ หรืออาจ state_dict ต่างจริงเลยแปลงไม่ได้ ไม่มีใครทดสอบไว้ให้เช็ค) **นี่คือความเสี่ยงคลาสเดียวกับ Day of Shame ของ t01** (mmproj export พังเพราะสถาปัตยกรรมใหม่เกินไป ค้นพบหลังเทรนเต็มไปแล้ว) **ห้ามรอจนเทรน 78B เต็มรอบแล้วค่อยพิสูจน์** — ต้องทดสอบขั้นนี้ด้วย InternVL3 ตัวเล็ก (2B/8B ที่มีคนทำ "-with-mmproj" สำเร็จแล้วบน HF เป็นตัวอย่าง) ตอน dry-run ราคาถูก (ข้อ 13): เทรน LoRA จิ๋วบนตัวเล็กสุด (หรือแม้แต่ 0 step แค่โหลด+merge) → merge_and_unload() → ลอง `convert_hf_to_gguf.py --mmproj` → เห็นผลจริงว่าผ่านหรือพัง ก่อนตัดสินใจว่า Purson-gguf จะมีจริงหรือมีแค่ Purson-weights |

## ⚠️ ช่องว่างที่ต้องปิดก่อนกดเช่าจริง (เรียงตามลำดับที่ต้องทำ)

1. ~~เลือก framework~~ ✅ **LLaMA-Factory** (มะขามเคาะ 2026-08-29)
2. ~~เคาะ GPU strategy~~ ✅ **QLoRA 4-bit การ์ดใบเดียว 96GB, คง InternVL3-78B ไม่ลดขนาด** (มะขามเคาะ 2026-08-30)
3. ~~เขียน converter dataset~~ ✅ `build_dataset_llamafactory.py` (2026-08-30, verify แล้ว)
4. ~~เขียนสคริปต์เทรน + onstart~~ 🔍 `train_t04_internvl3_qlora.yaml` + `onstart_llamafactory.sh`
   (2026-08-30, syntax ผ่าน — ยังไม่เคยรันจริงบน GPU)
5. ~~เขียนสคริปต์ infer ใหม่~~ 🔍 `infer_house_t04.py` (2026-08-30, `--selftest` ผ่าน — ส่วนโมเดล/
   generate ยังไม่เคยรันจริงบน GPU) + ยังต้อง probe xgrammar กับ tokenizer InternVL3 จริง
6. **ทดสอบ QLoRA 4-bit จริงบนการ์ดถูกก่อน** — ยืนยัน `cutoff_len`/`image_max_pixels`/`lora_rank`
   ที่ยังเป็นค่าเริ่มต้นในข้อ 4 (VRAM ทฤษฎี ~39GB weights + LoRA/activation/KV บนการ์ด 96GB)
7. เช็คเครดิต Vast → แล้วค่อยเช่าจริงเต็มรอบ

## ลำดับงานเมื่อพร้อมเช่าจริง (โครงตามรอบก่อน ปรับเป็น InternVL3)

| # | ขั้น | สถานะ |
|---|---|---|
| 1 | เช่าการ์ด **ใบเดียว** RTX PRO 6000 96GB — ใบเดียวกันใช้ทั้ง dry-run และเทรนเต็ม (ไม่แยกการ์ดถูก/การ์ดจริงแบบรอบก่อน เพราะ QLoRA 4-bit ใบเดียวพอทั้งกระบวนการ — ยืนยันด้วย VRAM peak จริง 54.6/97.9GB) | ✅ instance id `49160184`, $1.1048/hr, image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel` |
| 2 | อัป `data_before_tune/` (train_lf.json/val_lf.json/dataset_info.json/yaml/images/) | ✅ 894/894 รูปตรง, 1020/1020 image path resolve ครบ 0 missing |
| 3 | dry run สั้น — ยืนยัน VRAM/seq ไม่โดนตัด ก่อนเทรนเต็ม | ✅ ผ่าน (ดูข้อ 3 ใน Phase 0) |
| 4 | เทรนเต็ม → เซฟ adapter | 🔍 **ขยายเป็น k-fold 4 folds คู่ขนาน 4 การ์ด** (มะขามเคาะ 2026-08-30 ดึก "ทำเป็น 4 fold เลย ... อย่าสนงบ ผมจ่ายเอง" — หลังพบ val เดิมปนเปื้อน 100%): instance `49160184`(AU)→fold0, `49171206`(FI)→fold1, `49172547`(AU)→fold2, `49175439`(CZ)→fold3 (ใบแรก `49172551` offline หลังเช่า 26 นาที destroy แล้วเช่าใหม่เป็น `49175439`) — 3 epochs/fold, 306 steps/fold · **สถานะจริง ณ ล่าสุด: fold0+fold2 เทรนเสร็จแล้ว (train_loss 0.5503/0.5589) fold1+fold3 ยังเทรนอยู่ ~90%+** · **แผนรวม:** merge **4** adapters เป็น "Purson-soup" ผ่าน PEFT `add_weighted_adapter` linear 0.25×4 (เงื่อนไข Model Soup ครบ: seed 3407 เท่ากันทุก fold) — **ระหว่างรอ fold ตัวสุดท้าย จะทดลอง merge แค่ 3 ตัวที่เสร็จก่อนดูเป็น smoke test** (ไม่ใช่ soup ตัวจริง) → **soup ตัวจริง (4-way) ไม่วัด benchmark** ตามที่มะขามสั่ง "อย่าวัดผล soup" (train ของ 4 folds รวมกันครบ 40 หลัง ไม่เหลือ val สะอาด) อัปเป็น `Sicilian44/Purson-weights` ติดป้าย unbenchmarked |
| 5 | Day of Shame: ดึง adapter + เทียบ sha256 ทีละไฟล์บนเครื่องเรา ก่อนแตะ destroy | 🔍 **fold0→fold1-weights ✅ ผ่าน** (sha256 `8bc8c1c6...fa7a5ef` ตรงเป๊ะ) · **fold2→fold3-weights ✅ ผ่าน** (sha256 `3e43dd02...11d301e4` ตรงเป๊ะ) · fold1, fold3 ยังรอ (ยังไม่เทรนเสร็จ) |
| 6 | อัปขึ้น HF: **5 repo** — `Purson-fold1-weights` ← `outputs_t04/fold0` (49160184) · `Purson-fold2-weights` ← `fold1` (49171206) · `Purson-fold3-weights` ← `fold2` (49172547) · `Purson-fold4-weights` ← `fold3` (49175439) · `Purson-weights` ← soup — **ทำก่อน destroy เสมอ** (Mark of Shame) | 🔍 **2/5 อัปแล้ว**: `Purson-fold1-weights` (858MB) + `Purson-fold3-weights` (858MB) — ⚠️ **บั๊กจริงพบระหว่างอัป**: `hf upload <repo> <folder> --exclude 'pattern'` เงียบไม่อัปไฟล์เลย ("Processing Files 0/0") ทั้งที่ไฟล์มีครบ — **วิธีแก้ที่ได้ผล: copy เฉพาะไฟล์ top-level (ไม่รวม checkpoint-*/) ไปโฟลเดอร์ staging แยก แล้วอัปโฟลเดอร์นั้นโดยไม่ใช้ `--exclude` เลย** ใช้กับ fold2/fold4 ต่อด้วย |
| 7 | ยิง infer บ้าน val (arm 2 ตัวคุม) ด้วยสคริปต์ใหม่ | 🔍 **สมอกเทสต์ 2 ตัวอย่างผ่าน 2026-08-30 — ปลดล็อก 3 ความเสี่ยงเดิม** (bitsandbytes โหลดโมเดล/xgrammar/chat-template ทำงานจริงบน GPU) · เต็ม val ช้าเกิน (~2-2.5 นาที/ตัวอย่าง × 205 = 7-8ชม./fold) **มะขามเคาะ: eval สุ่ม 24 ตัวอย่าง/fold แทน** (สร้างด้วย `make_eval_samples.py`, stratified กระจายครบ 8/8 หลังทุก fold, seed=42) · **⚠️ พบว่า `--all-val` เดิมอ่านจาก `val.jsonl` ต้นฉบับ (ปนเปื้อน) ไม่รู้จัก fold — แก้โดยอัป `val_fold{k}_sample.jsonl` ทับชื่อ `val.jsonl` บนเครื่องเช่าแต่ละใบ** · **กำลังรัน eval บน fold0(→fold1-weights) และ fold2(→fold3-weights)** |
| 8 | ยิงซ้ำ arm 2.4a (`--cv-dir cv_val`) — ตัดสิน hint ช่วยไหมด้วย `recall_printed` + จำนวนหลอน | ⬜ ยังไม่ทำ (ทำหลัง arm 2 เสร็จ) |
| 9 | *(อ้างอิง)* เทียบผลกับ t03 (Qwen) บนชุดงานเดียวกัน — กำกับชัดว่าเป็นการเทียบข้ามสถาปัตยกรรม | ⬜ |
| 10 | **ทดสอบจริงบ้าน 2 ชั้นที่ไม่เคยทำมาก่อนสักหลัง** (มะขามสั่งเพิ่ม 2026-08-30) | ⬜ **ต้องเป็นบ้านนอกคลัง 40 หลังทั้งหมด** (ไม่อยู่ใน `image/` หรือ `json_แก้ไขแล้ว/` เลย — ไม่ใช่แค่นอก train/val split เพราะทั้ง 40 หลังถูกใช้ในรอบใดรอบหนึ่งของ dataset ไปแล้ว) หา/op0x บ้าน 2 ชั้นใหม่มา 1 หลัง แล้วเดินผ่าน**สายพานเต็ม 7 ด่านจริง** (pass 0→3, ไม่ใช่แค่ยิง `infer_house_t04.py` วัด recall บนหน้าเดียว) — พิสูจน์ว่าใช้งานจริงได้ทั้งบ้าน ไม่ใช่แค่ตัวเลขบนตัวอย่างที่คัดมาแล้ว |
| 11 | ~~GGUF+mmproj export~~ | ❌ **ยกเลิก** — มะขามเคาะ 2026-08-30: เอาแต่ adapter พอ (ดู Phase 0 ข้อ 14) |
| 12 | ~~อัปขึ้น HF: `Purson-gguf`~~ | ❌ **ยกเลิก** — ไม่มี repo นี้ |
| 13 | 🔴 **คืนการ์ดจอ — รอบนี้เช่า 4 ใบพร้อมกัน ต้อง destroy ให้ครบทั้ง 4 ใบ** (มะขามย้ำ 2026-08-30) ทำหลังข้อ 5-6 ผ่านเท่านั้น | ⬜ **เผารวม ~$4.29/ชม. = ~$103/วัน — ลืมใบเดียวก็เสียเงินเปล่าทั้งวัน**<br>`echo "y" \| vastai destroy instance 49160184`  ← fold0 (AU, $1.105)<br>`echo "y" \| vastai destroy instance 49171206`  ← fold1 (FI, $1.096)<br>`echo "y" \| vastai destroy instance 49172547`  ← fold2 (AU, $0.916)<br>`echo "y" \| vastai destroy instance 49175439`  ← fold3 (CZ, $1.171)<br>**⚠️ ต้อง `echo "y" \|` เสมอ** — CLI ถาม y/N แบบ interactive ถ้าไม่ป้อนจะ **abort เงียบ ๆ** แล้วนึกว่า destroy ไปแล้ว (เจอจริง 2026-08-30)<br>**⚠️ destroy ≠ stop** — stop ยังเสียค่า storage ต่อ, destroy ลบถาวรกู้ไม่ได้ (บทเรียน 2026-08-24)<br>**✅ ปิดท้ายต้องรัน `vastai show instances` ยืนยันเหลือ 0 instances จริง** ไม่ใช่แค่เชื่อว่าคำสั่งผ่าน — รอบนี้ 4 ใบ พลาดง่ายกว่ารอบก่อนที่มีใบเดียว<br>*(หมายเหตุ: ใบเดิม 49172551 (Virginia US) หลุด offline ตั้งแต่คืนวันที่ 30 และ destroy ไปแล้ว — ไม่ต้องคืนซ้ำ)* |
| 14 | log ผลลง `workmen's_diary/` + commit | ⬜ |

**การทดลอง hint (arm 2 vs 2.4a) วัดบน adapter InternVL3-78B ของ t04 เอง** — ตัดสินทิศทาง pass 3
จากผลนี้ตาม [RUNBOOK.md](RUNBOOK.md) ข้อ 4 (RUNBOOK เขียนสมัย Qwen — คำสั่ง `infer_house_t03.py`
ในนั้นจะถูกแทนด้วยสคริปต์ใหม่ ชื่อ flag `--arm/--cv-dir` จะคงเดิมเพื่อให้เอกสารเก่ายังอ่านรู้เรื่อง)

## บันทึกการแก้ที่ทำไปแล้วรอบนี้ (2026-08-29)

- แก้ `infer_house_t03.py` MAX_PIXELS 5120→7680 และ `OUT_DIR`/`--out-root` เป็น t04 — **ทำก่อนรู้ว่า
  เปลี่ยนโมเดล** ตอนนี้ไฟล์คู่นี้มีสถานะ "reference ยุค Qwen" (header เตือนหัวไฟล์) การแก้พวกนั้น
  ไม่เสียเปล่า: ถ้าอนาคตกลับมาใช้ Qwen ไฟล์พร้อมใช้ และ logic วัดผลใน infer จะถูก port ไปสคริปต์ใหม่
- สร้างไฟล์ workflow นี้ + ตรวจ Phase 0 เดิม → พบและปิดช่องว่าง MAX_PIXELS/OUT_DIR ไปแล้วก่อนเปลี่ยนโมเดล
