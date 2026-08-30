# t04 workflow — Purson (InternVL3-78B fine-tune on t04 dataset + hint arm 2 vs 2.4a)

> ## 🔴 รอบ t04 **จบแล้ว 2026-08-30 ค่ำ — เทรนครบ 4 folds, adapter ทั้ง 4 อัป HF + verify ครบ, การ์ดคืนครบ 4 ใบ (0 instances, เครดิตเหลือ $16.66) — แต่ eval recall ≈0-8.8%: โมเดล "อ่านแบบไม่ได้จริง" และหา root cause เจอครบแล้ว** (ดู section 🔬 ผลสอบสวนด้านล่าง — config ขาด `crop_to_patches: true` ทำให้ตอนเทรนทุกรูปเหลือ 1 tile 448px = 256 tokens อ่านชื่อคานไม่ออก โมเดลจึงเรียนได้แค่ schema+จำคำตอบ) · **มะขามขอคิดก่อนว่าจะไปทางไหนต่อ** (เทรน InternVL ใหม่พร้อม fix / กลับ Qwen3-VL / พอแค่นี้เพราะงานจริงมี CV ช่วย) — ห้ามเริ่มเช่าการ์ดใหม่จนกว่าจะเคาะ
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
| 4 | เทรนเต็ม → เซฟ adapter | ✅ **ครบ k-fold 4 folds คู่ขนาน 4 การ์ด** (มะขามเคาะ 2026-08-30 ดึก "ทำเป็น 4 fold เลย ... อย่าสนงบ ผมจ่ายเอง" — หลังพบ val เดิมปนเปื้อน 100%): instance `49160184`(AU)→fold0, `49171206`(FI)→fold1, `49172547`(AU)→fold2, `49175439`(CZ)→fold3 (ใบแรก `49172551` offline หลังเช่า 26 นาที destroy แล้วเช่าใหม่เป็น `49175439`) — 3 epochs/fold, 306 steps/fold, ~16.5-18ชม./fold · train_runtime: fold0/2 ไม่บันทึกเวลารวมไว้ตรงนี้, fold3(→fold4-weights) 16:30:52, fold1(→fold2-weights) 18:00:29 |
| 5 | Day of Shame: ดึง adapter + เทียบ sha256 ทีละไฟล์บนเครื่องเรา ก่อนแตะ destroy | ✅ **ครบ 4/4** — fold0→fold1-weights, fold2→fold3-weights, fold3(CZ)→fold4-weights, fold1→fold2-weights ทุกตัว sha256 ตรงเป๊ะระหว่างเครื่องเช่ากับเครื่องเรา ก่อน destroy ทุกครั้ง (ไม่มีใบไหน destroy ก่อน verify) |
| 6 | อัปขึ้น HF: `Purson-fold1..4-weights` (4 adapter) — **ทำก่อน destroy เสมอ** (Mark of Shame) | ✅ **ครบ 4/4** — ⚠️ **บั๊กจริงพบระหว่างอัป**: `hf upload <repo> <folder> --exclude 'pattern'` เงียบไม่อัปไฟล์เลย ("Processing Files 0/0") ทั้งที่ไฟล์มีครบ — **วิธีแก้ที่ได้ผล: copy เฉพาะไฟล์ top-level (ไม่รวม checkpoint-*/) ไปโฟลเดอร์ staging แยก แล้วอัปโฟลเดอร์นั้นโดยไม่ใช้ `--exclude` เลย** — ใช้วิธีนี้กับทั้ง 4 ตัว |
| 6.5 | **3-way merge smoke test** (มะขามสั่ง "รอ fold4 จบลองผสมของทั้ง 3 อันดู") | ✅ ทำบนใบ Czechia: โหลด base + fold1/fold3/fold4-weights, PEFT `add_weighted_adapter` linear (1/3 เท่ากัน) → save สำเร็จ ไม่ OOM/error, ได้ adapter 842MB — **พิสูจน์แค่ pipeline merge รันได้จริง ไม่ได้บอกว่าคุณภาพดี** (ดูข้อ 🔬 root cause ด้านล่าง ทำไมถึงไม่มีความหมายทางคุณภาพ) |
| 7 | ยิง infer บ้าน val (arm 2 ตัวคุม) ด้วยสคริปต์ใหม่ | ✅ **ครบทั้ง 4 fold** — eval สุ่ม 24 ตัวอย่าง/fold (`make_eval_samples.py`, stratified, seed=42, ครอบคลุม 8/8 หลังทุก fold) · **ผลสรุป: fold1-weights 8.8% recall (JSON valid 96%) / fold2,3,4-weights ≈0% recall** — ดู section 🔬 root cause ด้านล่างว่าทำไมต่ำขนาดนี้ · แก้บั๊ก `--all-val` อ่าน `val.jsonl` เดิม (ปนเปื้อน) ไม่รู้จัก fold โดยอัป `val_fold{k}_sample.jsonl` ทับ |
| 7.5 | **สอบสวนสาเหตุ recall ต่ำ** (มะขามสั่ง "หาสาเหตุก่อน มันไม่ควรแย่ขนาดนั้น") | ✅ **เจอ root cause ครบ 3 ชั้น — ดู section 🔬 ด้านล่าง** สรุปสั้น: config เทรนไม่มี `crop_to_patches: true` → ทุกรูปเทรนเหลือ 1 tile 448px (256 tokens) อ่านชื่อคาน/ขนาดจากแบบไม่ได้จริง |
| 8 | ยิงซ้ำ arm 2.4a (`--cv-dir cv_val`) — ตัดสิน hint ช่วยไหมด้วย `recall_printed` + จำนวนหลอน | ⬜ **พักไว้** — รอเคาะทิศทางหลัง root cause ก่อน (ยิง arm 2.4a บนโมเดลที่มองไม่เห็นรูปชัดไม่มีประโยชน์) |
| 9 | *(อ้างอิง)* เทียบผลกับ t03 (Qwen) บนชุดงานเดียวกัน — กำกับชัดว่าเป็นการเทียบข้ามสถาปัตยกรรม | ⬜ พักไว้เช่นกัน |
| 10 | **ทดสอบจริงบ้าน 2 ชั้นที่ไม่เคยทำมาก่อนสักหลัง** (มะขามสั่งเพิ่ม 2026-08-30) | 🔍 **บ้านทดสอบเตรียมพร้อมแล้ว** `test_house_new/บ้านไทยพอเพียง3.pdf` (65 หน้า, ยืนยันไม่อยู่ใน fold_manifest.json 40 หลังคลัง) แต่ **ยังไม่รัน** — รอเคาะทิศทางก่อน (รันตอนนี้กับ adapter ที่อ่านแบบไม่ได้ไม่มีประโยชน์) |
| 11 | ~~GGUF+mmproj export~~ | ❌ **ยกเลิก** — มะขามเคาะ 2026-08-30: เอาแต่ adapter พอ (ดู Phase 0 ข้อ 14) |
| 12 | ~~อัปขึ้น HF: `Purson-gguf`~~ | ❌ **ยกเลิก** — ไม่มี repo นี้ |
| 13 | 🔴 คืนการ์ดจอ — รอบนี้เช่า 4 ใบพร้อมกัน | ✅ **คืนครบ 4/4 ใบ 2026-08-30 ค่ำ** — `vastai show instances` ยืนยันเหลือ 0 instances, เครดิตคงเหลือ $16.66 ทุกใบ verify adapter (ข้อ 5) ก่อน destroy ครบทุกใบ ไม่มีใบไหนหลุดกฎ Mark-of-Shame · *(ใบเดิม 49172551 Virginia US หลุด offline คืนก่อนหน้า destroy ไปแล้วตั้งแต่ต้น ไม่เข้าข่ายนี้)* |
| 14 | log ผลลง `workmen's_diary/` + commit | 🔍 diary เขียนแล้ว (ดู 2026-08-30.md) — commit ยังไม่ทำ (มะขามยังไม่สั่ง) |

**การทดลอง hint (arm 2 vs 2.4a) วัดบน adapter InternVL3-78B ของ t04 เอง** — ตัดสินทิศทาง pass 3
จากผลนี้ตาม [RUNBOOK.md](RUNBOOK.md) ข้อ 4 (RUNBOOK เขียนสมัย Qwen — คำสั่ง `infer_house_t03.py`
ในนั้นจะถูกแทนด้วยสคริปต์ใหม่ ชื่อ flag `--arm/--cv-dir` จะคงเดิมเพื่อให้เอกสารเก่ายังอ่านรู้เรื่อง)

## 🔬 ผลสอบสวน: ทำไม recall ต่ำมาก (สอบสวน 2026-08-30 ค่ำ หลังมะขามสั่ง "หาสาเหตุก่อน มันไม่ควรแย่ขนาดนั้น")

**สรุป 1 บรรทัด:** `train_t04_internvl3_qlora.yaml` (และ fold0-3.yaml ที่สืบมา) ไม่มี `crop_to_patches: true`
→ ทุกรูปตอนเทรนถูกยุบเหลือ 1 tile 448×448 = 256 image tokens เสมอ (ไม่ว่าต้นฉบับกี่ MP) → โมเดล
**ไม่เคยเห็นแบบชัดพอจะอ่านชื่อคาน/มิติ/เหล็กเสริมเลยสักครั้งตลอด 16.5-18 ชม./fold ที่เทรน**

**หลักฐาน 3 ชั้น (ไล่จากอ่อนไปแข็ง):**
1. Dump จริงจาก training log (`fold0.log`, sample แรก): 3 รูป → `input_ids` มี image token (`<IMG_CONTEXT>`,
   id 151667) นับได้ **768 ตัว = 256×3 เป๊ะ** — ยืนยันด้วยสคริปต์ `probe_img_tokens.py` (เก็บไว้ใน
   `data_before_tune/`) รันบน CPU ล้วนเทียบ (ก) token จาก log เทรนจริง กับ (ข) token ที่ AutoProcessor
   สร้างตอน infer จริง (ได้ 9984 tokens = 13 tiles/รูป — ต่างกัน 13 เท่า เป็นปัญหาเสริมข้อ 2)
2. ไล่ source `llamafactory/data/mm_plugin.py` (`InternVLPlugin._get_mm_inputs`, บรรทัด ~1190):
   tiling (`crop_to_patches`/`max_patches: 12`) เปิดเฉพาะเมื่อ `getattr(processor, "crop_to_patches", False)`
   เป็น true — yaml ของเราไม่เคยตั้งค่านี้เลย ดีฟอลต์คือ false เสมอ
3. **ทดสอบตาเปล่า**: ย่อรูปแปลนคาน `บ้าน_ใหญ่_1ชั้น_01_หน้า15.png` (ต้นฉบับ 4631×3473) เหลือ 448×448
   (ขนาดที่โมเดลเห็นจริงตอนเทรน) แล้วเปิดดู — **อ่านชื่อคาน B1/B2, ขนาดหน้าตัด, ระยะเหล็กเสริม ไม่ออก
   สักตัวเดียว** เห็นแค่โครงเส้นราง ๆ

**ทำไมทุก subtask ยกเว้น plan_slab ได้ recall ~0%:** โมเดลตอบผิด pattern/element ทั้งชุด (เช่น
ป้อนแปลนฐานราก ตอบเป็นแปลนหลังคาของบ้านคนละหลัง) — ไม่ใช่ตอบใกล้เคียงแต่ id เพี้ยน คือ**ไม่รู้เลยว่ากำลัง
ดูอะไรอยู่** แล้วดึงความจำจาก training data (32 บ้านที่เห็นตอนเทรน) มาตอบแทน ยิ่ง element ต่อหน้าเยอะ
(plan_beam มี 9-46 ตัว) ยิ่งพัง เพราะจำได้แค่คร่าว ๆ; plan_slab element น้อย (1-4 ตัว) เดาถูกได้ง่ายกว่า
โดยบังเอิญ — ไม่ใช่เพราะอ่านรูปได้ดีกว่า

**ปัญหาเสริม 2 ข้อที่ซ้อนทับ (ไม่ใช่ตัวการหลัก แต่ทำให้ตัวเลขแย่ลงอีก และบางอาการที่นึกว่าโมเดลพัง
จริง ๆ มาจากตรงนี้):**
- **decoder ตอน infer มี `no_repeat_ngram_size=8` + `repetition_penalty=1.15`** (มรดกจาก
  `infer_house_t03.py`/t03-Qwen) — ห้ามลำดับ 8 token ซ้ำ แต่คำตอบที่ถูกต้องของงานนี้ต้องซ้ำโดยธรรมชาติ
  (เช่น `"B2"` ซ้ำ 10 ครั้ง, `"RB1"` ซ้ำ 24 ครั้ง) → โมเดลถูกบังคับให้ตอบผิดทางแม้จะ "จำ" ถูกก็ตาม, บางครั้ง
  วนหาทางออกจนชนเวลา 25 นาที/หน้า (`JSON เสีย`, เจอ 2 ครั้งใน eval fold0/fold2)
  **พิสูจน์แยกแล้วด้วย fixtest**: ปลด `no_repeat_ngram_size`/`repetition_penalty` ออก → จำนวน element
  ที่ตอบเพิ่มขึ้นจริง (0→10 element) **แต่ recall ยังคง 0%** — ยืนยันว่านี่เป็นปัญหาซ้อนทับ ไม่ใช่ตัวการหลัก
- **AutoProcessor ตอน infer (default 13 tiles/รูป) เห็นรูปคนละความละเอียดกับตอนเทรน (1 tile)** — แม้จะ
  ไม่ใช่ต้นเหตุที่โมเดล "ไม่รู้จัก" อะไร (เพราะ weight ถูกเทรนมาบนความละเอียดต่ำ) แต่ทำให้ผลตอน infer
  ยิ่งไม่สอดคล้องกับสิ่งที่โมเดลถูกเทรนมาให้คุ้นเคย

**สรุปผลกระทบ:** adapter ทั้ง 4 fold (และ 3-way soup smoke test) เรียนรู้ schema JSON ได้ดีจริง
(JSON valid 96-100%) แต่**ไม่ได้เรียนรู้การอ่านแบบเลย** — data/k-fold split/pipeline/upload
ระเบียบต่าง ๆ ยังดีทั้งหมด ปัญหาอยู่ที่ config 1 บรรทัดที่ขาดไป ไม่ใช่ตัว dataset หรือ InternVL3
ตัวโมเดลเอง

**ทางที่ยังไม่เคาะ (รอมะขามคิด):** (ก) เทรนใหม่พร้อมเปิด `crop_to_patches: true` — seq length จะยาวขึ้น
มาก ต้อง smoke-test 5 steps ก่อนเทรนเต็มเสมอ (เสี่ยง OOM บน 96GB) (ข) กลับไปใช้ Qwen3-VL/Qwen2.5-VL
(native dynamic resolution เป็นดีฟอลต์ ไม่ต้องตั้ง flag เพิ่ม — เหตุผลที่ t03 อ่านแบบได้โดยไม่ต้องรู้เรื่อง
tiling เลย) (ค) พอแค่นี้ เพราะงานจริงมี Python CV ช่วยถอด element อยู่แล้ว โมเดลรับหน้าที่แค่ schema

## บันทึกการแก้ที่ทำไปแล้วรอบนี้ (2026-08-29)

- แก้ `infer_house_t03.py` MAX_PIXELS 5120→7680 และ `OUT_DIR`/`--out-root` เป็น t04 — **ทำก่อนรู้ว่า
  เปลี่ยนโมเดล** ตอนนี้ไฟล์คู่นี้มีสถานะ "reference ยุค Qwen" (header เตือนหัวไฟล์) การแก้พวกนั้น
  ไม่เสียเปล่า: ถ้าอนาคตกลับมาใช้ Qwen ไฟล์พร้อมใช้ และ logic วัดผลใน infer จะถูก port ไปสคริปต์ใหม่
- สร้างไฟล์ workflow นี้ + ตรวจ Phase 0 เดิม → พบและปิดช่องว่าง MAX_PIXELS/OUT_DIR ไปแล้วก่อนเปลี่ยนโมเดล
