# t04 workflow — Purson (InternVL3-78B fine-tune on t04 dataset + hint arm 2 vs 2.4a)

> ## 🟡 นี่คือเอกสารของ **รอบ t04 (Purson)** — ยังไม่จบ (dataset/prompt พร้อม · สคริปต์เทรน/ infer ต้องสร้างใหม่สำหรับ InternVL3 · ยังไม่เคยเช่า GPU สักครั้ง)
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
| 3 | **สคริปต์เทรนใหม่** — `train_t04_internvl3_qlora.yaml` (LLaMA-Factory config) | 🔍 เขียนแล้ว 2026-08-30 ตาม official example จริงจาก repo hiyouga/LLaMA-Factory (`examples/train_qlora/qwen3_lora_sft_otfq.yaml` + `examples/train_lora/qwen3vl_lora_sft.yaml`, ไม่ได้เดา) `template: intern_vl` ยืนยันจาก constants.py, `model_name_or_path: OpenGVLab/InternVL3-78B-hf` (ต้องเป็นตัว **-hf** เท่านั้น) yaml parse ผ่าน · **⚠️ 3 ค่ายังไม่ verify: `cutoff_len`/`image_max_pixels`/`lora_rank`** — ยกมาจาก Qwen ไม่ได้ ต้อง dry-run วัดจริง (ข้อ 10) ก่อนเทรนเต็ม |
| 4 | **แปลง dataset** — train/val.jsonl → ฟอร์แมต LLaMA-Factory sharegpt | ✅ `build_dataset_llamafactory.py` เขียน+รันจริงแล้ว 2026-08-30: **1020 train / 229 val แปลงผ่านหมด**, assert ยืนยันลำดับ image-ก่อน-text ทุกแถวจริง (ไม่ใช่แค่สมมติ), sanity-check `<image>` token count = `images[]` length ทุกแถว, **0 ไฟล์รูปหาย** (เช็คจริงว่าทุก path resolve) → `train_lf.json`/`val_lf.json`/`dataset_info.json` พร้อมใช้ |
| 5 | **GPU sizing** | ✅ มะขามเคาะ 2026-08-30: **QLoRA 4-bit บนการ์ดใบเดียว 96GB** (ไม่เอา bf16 multi-GPU, ไม่เอาลดขนาดโมเดลลง InternVL3-38B — คง 78B) เหตุผล: InternVL3-78B เป็น dense รองรับ 4-bit จริง (ต่างจาก Qwen3.6/Qwen3.5-122B ที่เป็น MoE แล้ว bitsandbytes 4-bit ใช้ไม่ได้ — เช็คแล้วทั้งคู่) weights 4-bit (NF4) ~39GB (78B×0.5B) เหลือพื้นที่ให้ LoRA+activation+KV cache บนการ์ด 96GB ตามทฤษฎี **แต่ตัวเลขจริงยังไม่ verify กับ LLaMA-Factory จริง** — ต้องทดสอบบนการ์ดถูกก่อนเสมอ (กติกาเดิม) |
| 6 | dataset (ฝั่ง GT/รูป) พร้อม — train 1020 / val 229 / 40 หลัง / images 780 ไฟล์, สแกน 1249 text block ผ่าน 0 อักขระต้องห้าม | ✅ build 2026-08-29 (เนื้อหาใช้ต่อได้ รอแค่แปลงโครงตามข้อ 4) |
| 7 | sidecar CV (`cv_val/`) สำหรับ arm 2.4a | ✅ 23 `_hint.txt` (pass 1.5 → arm 2.4a) + 23 `_hint25.txt` (pass 2.5 → pass 3, คนละชุด อย่าสับสน) — hint เป็นข้อความล้วน ใช้กับโมเดลไหนก็ได้ |
| 8 | self-check เครื่องมือ CV | ✅ `cv_scan.py --demo` + `merge_guard.py` ผ่าน (รันจริง 2026-08-29) — เครื่องมือฝั่ง CV ไม่ผูกกับโมเดล ไม่กระทบจากการเปลี่ยน |
| 9 | **สคริปต์ infer/eval ใหม่** — `infer_house_t04.py` | 🔍 เขียนแล้ว 2026-08-30 — port `score_ids()`/`element_ids()`/`strip_fence()`/`apply_arm()`/`hide_grid_lines()` จาก `infer_house_t03.py` ตรงๆ (logic ล้วน ไม่ผูก Unsloth) + เขียนใหม่ส่วนโหลดโมเดล/generate ด้วย `transformers`+`bitsandbytes`(4-bit)+`peft` · `py_compile` ผ่าน + **`--selftest` ผ่านทุกข้อ** (เช็ค 5 ฟังก์ชันด้วยข้อมูลจำลอง ไม่ต้องมี GPU) · **⚠️ ส่วนโหลดโมเดล/generate ยังไม่เคยรันจริงบน GPU** — 3 จุดเสี่ยงระบุไว้ในหัวไฟล์ (chat template จริงของ InternVL3-78B-hf / tokenizer attribute จริงสำหรับ xgrammar / bitsandbytes โหลดโมเดลได้จริง) ต้อง probe ก่อนเชื่อ (rule_of_tune ข้อ 13) |
| 10 | onstart.sh ใหม่ (ตัวเดิมติดตั้ง unsloth — ผิด stack, framework เคาะแล้ว = LLaMA-Factory) | 🔍 `onstart_llamafactory.sh` เขียนแล้ว 2026-08-30, `bash -n` ผ่าน — ยังไม่เคยรันจริงบนเครื่องเช่า |
| 11 | **HF repo — ตั้งชื่อตาม "Purson" (ชื่อจริงของ t04 — มะขามย้ำ 2026-08-30)** | 🔍 เคาะชื่อชั่วคราว **2 repo แยกกัน**: `Sicilian44/Purson-weights` (LoRA adapter จาก LLaMA-Factory) และ `Sicilian44/Purson-gguf` (ไฟล์ GGUF+mmproj — อัปเฉพาะถ้าข้อ 14 ผ่านเท่านั้น อย่าอัป repo เปล่าไว้ก่อน) — **ชื่อยังไม่ยืนยันจากมะขามเป็นทางการ** |
| 12 | Vast.ai เครดิต+บิล — เช็คผ่าน `vastai search offers` (dph_total) เท่านั้น (บทเรียน 30x-misread) | ⬜ ยังไม่เช็ครอบนี้ |
| 13 | dry run สั้นบน**การ์ดถูก**ก่อนเสมอ (เทียบเท่า TEST_STEPS=5 ของรอบก่อน — ชื่อ flag ตาม framework ที่เลือก) | ⬜ |
| 14 | **GGUF+mmproj export — verify รอยต่อ checkpoint ก่อนเชื่อว่าทำได้** (มะขามสั่งเพิ่ม 2026-08-30) | ⬜ **ความเสี่ยงจริง พบ 2026-08-30:** `convert_hf_to_gguf.py` ของ llama.cpp รองรับ InternVL3 เฉพาะ checkpoint **"non-hf" (ดั้งเดิม)** เท่านั้น — เอกสารระบุชัดว่า `InternVL3-*-hf` **ใช้ไม่ได้** แต่ pipeline ทั้งรอบนี้ (LLaMA-Factory/transformers/peft) บังคับเทรนบนตัว `-hf` เพราะ LLaMA-Factory ลงทะเบียนไว้แบบนั้น → เทรน LoRA บน `-hf` → merge → **ยังไม่มีใครยืนยันว่าป้อน `convert_hf_to_gguf.py --mmproj` (ตัว non-hf) แล้วอ่านออกจริงไหม** (คนละ checkpoint format — อาจแค่ config/class ต่างแต่ tensor เดียวกันเลยแปลงได้ หรืออาจ state_dict ต่างจริงเลยแปลงไม่ได้ ไม่มีใครทดสอบไว้ให้เช็ค) **นี่คือความเสี่ยงคลาสเดียวกับ Day of Shame ของ t01** (mmproj export พังเพราะสถาปัตยกรรมใหม่เกินไป ค้นพบหลังเทรนเต็มไปแล้ว) **ห้ามรอจนเทรน 78B เต็มรอบแล้วค่อยพิสูจน์** — ต้องทดสอบขั้นนี้ด้วย InternVL3 ตัวเล็ก (2B/8B ที่มีคนทำ "-with-mmproj" สำเร็จแล้วบน HF เป็นตัวอย่าง) ตอน dry-run ราคาถูก (ข้อ 13): เทรน LoRA จิ๋วบนตัวเล็กสุด (หรือแม้แต่ 0 step แค่โหลด+merge) → merge_and_unload() → ลอง `convert_hf_to_gguf.py --mmproj` → เห็นผลจริงว่าผ่านหรือพัง ก่อนตัดสินใจว่า Purson-gguf จะมีจริงหรือมีแค่ Purson-weights |

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
| 1 | เช่าการ์ดถูก ทดสอบสคริปต์จบ 1 หน้า/5 step ก่อน แล้วค่อยขยับการ์ดจริง (venv แยกเสมอ) | ⬜ |
| 2 | อัป `data_before_tune/` (dataset แปลงแล้ว + `cv_val/` + `images/`) | ⬜ |
| 3 | dry run สั้น — ยืนยัน VRAM/seq ไม่โดนตัด ก่อนเทรนเต็ม | ⬜ |
| 4 | เทรนเต็ม → เซฟ adapter (โฟลเดอร์ output ใหม่ของ t04) | ⬜ |
| 5 | Day of Shame: ดึง adapter + เทียบ sha256 ทีละไฟล์บนเครื่องเรา ก่อนแตะ destroy | ⬜ |
| 6 | อัปขึ้น HF: **`Sicilian44/Purson-weights`** (adapter — ทำเสมอ, ก่อน destroy) | ⬜ |
| 7 | ยิง infer บ้าน val (arm 2 ตัวคุม) ด้วยสคริปต์ใหม่ | ⬜ |
| 8 | ยิงซ้ำ arm 2.4a (`--cv-dir cv_val`) — ตัดสิน hint ช่วยไหมด้วย `recall_printed` + จำนวนหลอน | ⬜ |
| 9 | *(อ้างอิง)* เทียบผลกับ t03 (Qwen) บนชุดงานเดียวกัน — กำกับชัดว่าเป็นการเทียบข้ามสถาปัตยกรรม | ⬜ |
| 10 | **ทดสอบจริงบ้าน 2 ชั้นที่ไม่เคยทำมาก่อนสักหลัง** (มะขามสั่งเพิ่ม 2026-08-30) | ⬜ **ต้องเป็นบ้านนอกคลัง 40 หลังทั้งหมด** (ไม่อยู่ใน `image/` หรือ `json_แก้ไขแล้ว/` เลย — ไม่ใช่แค่นอก train/val split เพราะทั้ง 40 หลังถูกใช้ในรอบใดรอบหนึ่งของ dataset ไปแล้ว) หา/op0x บ้าน 2 ชั้นใหม่มา 1 หลัง แล้วเดินผ่าน**สายพานเต็ม 7 ด่านจริง** (pass 0→3, ไม่ใช่แค่ยิง `infer_house_t04.py` วัด recall บนหน้าเดียว) — พิสูจน์ว่าใช้งานจริงได้ทั้งบ้าน ไม่ใช่แค่ตัวเลขบนตัวอย่างที่คัดมาแล้ว |
| 11 | GGUF+mmproj export (เฉพาะถ้า Phase 0 ข้อ 14 verify ผ่านแล้วว่าทำได้จริง — ทำบนเครื่องเช่าต่อ หรือดึง adapter จากข้อ 6 มาทำภายหลังก็ได้ ไม่บังคับต้องเสร็จก่อน destroy) | ⬜ |
| 12 | อัปขึ้น HF: **`Sicilian44/Purson-gguf`** (เฉพาะถ้าข้อ 11 ผ่านจริง — **อย่าอัป repo เปล่า/พังไว้ล่วงหน้า**) | ⬜ |
| 13 | **คืนการ์ดจอทุกใบที่เช่าไว้รอบนี้** (หลังข้อ 5-6 ผ่านเท่านั้น — ข้อ 11-12 ทำทีหลังได้ไม่ต้องรอ) | ⬜ `vastai destroy instance <ID>` **ทีละใบ ไล่ให้ครบทุก instance ที่เช่าตอนคืนนี้** (การ์ดถูกสำหรับ dry-run ข้อ 3 + การ์ดจริงสำหรับเทรนเต็ม ข้อ 4 — คนละใบกัน อย่าคืนแค่ใบหลังแล้วลืมใบถูก) **destroy ≠ stop** (stop = ยังเสียค่า storage ต่อ, destroy = ลบถาวรกู้ไม่ได้ — บทเรียนเดิม 2026-08-24) **หลัง destroy ต้องเช็ค `vastai show instances` ยืนยันเหลือ 0 instances จริง** ไม่ใช่แค่เชื่อว่าคำสั่งรันผ่าน (ทดสอบแล้ว 2026-08-24 ว่า destroy จริงคืน 0 ได้ แต่รอบนั้นมีแค่ 1 instance — รอบนี้อาจมีหลายใบพร้อมกัน ต้องเช็คทุกใบ) |
| 14 | log ผลลง `workmen's_diary/` + commit | ⬜ |

**การทดลอง hint (arm 2 vs 2.4a) วัดบน adapter InternVL3-78B ของ t04 เอง** — ตัดสินทิศทาง pass 3
จากผลนี้ตาม [RUNBOOK.md](RUNBOOK.md) ข้อ 4 (RUNBOOK เขียนสมัย Qwen — คำสั่ง `infer_house_t03.py`
ในนั้นจะถูกแทนด้วยสคริปต์ใหม่ ชื่อ flag `--arm/--cv-dir` จะคงเดิมเพื่อให้เอกสารเก่ายังอ่านรู้เรื่อง)

## บันทึกการแก้ที่ทำไปแล้วรอบนี้ (2026-08-29)

- แก้ `infer_house_t03.py` MAX_PIXELS 5120→7680 และ `OUT_DIR`/`--out-root` เป็น t04 — **ทำก่อนรู้ว่า
  เปลี่ยนโมเดล** ตอนนี้ไฟล์คู่นี้มีสถานะ "reference ยุค Qwen" (header เตือนหัวไฟล์) การแก้พวกนั้น
  ไม่เสียเปล่า: ถ้าอนาคตกลับมาใช้ Qwen ไฟล์พร้อมใช้ และ logic วัดผลใน infer จะถูก port ไปสคริปต์ใหม่
- สร้างไฟล์ workflow นี้ + ตรวจ Phase 0 เดิม → พบและปิดช่องว่าง MAX_PIXELS/OUT_DIR ไปแล้วก่อนเปลี่ยนโมเดล
