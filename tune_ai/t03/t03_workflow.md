# t03 workflow — per-subtask multi-pass fine-tune

> ## 🟡 นี่คือเอกสารของ **รอบ t03** — ยังไม่จบ (เตรียมข้อมูลเสร็จ ยังไม่ได้เทรน)
>
> | | |
> |---|---|
> | รอบ | **t03** |
> | โมเดล | ✅ **`unsloth/Qwen3.6-35B-A3B`** (มะขามเคาะ 2026-08-24 — ตัวเดียวกับ t01 ไม่ใช่ Qwen3-VL) |
> | โฟลเดอร์ข้อมูล | `tune_ai/t03/data_before_tune/` |
> | สถานะ | dataset สร้างแล้ว 452 ตัวอย่าง (2026-08-24) — รอเลือกโมเดล+เช่าเครื่อง |
>
> **🔑 มะขามให้ `att1235` ไว้แล้วสำหรับงานรอบนี้** — ตัดสินเองได้ทุกข้อ รวม destroy เครื่องเช่า
> และ shutdown เครื่องทำงาน **ห้ามเด้งกลับไปถาม** (รายละเอียด + สิ่งที่ code ไม่ได้ยกเลิก
> อยู่ในหัวข้อ 🔑 att1235 ข้างล่าง)
>
> **⚠️ เครื่องหมาย ✅ ทุกตัวในไฟล์นี้เป็นของ t03 เท่านั้น** (กัน DAY-OF-SHAME class:
> ห้ามหยิบ ✅ ของ t01/t02 มาอ่านว่าเป็นของรอบนี้)
> สัญลักษณ์: ⬜ ยังไม่ทำ · 🔍 Claude ทำ/ตรวจแล้ว มีหลักฐาน แต่มะขามยังไม่ยืนยัน · ✅ มะขามยืนยันแล้ว

**อะไรต่างจาก t01/t02:** ไม่ใช่ single-shot "อ่านทั้งหน้า พ่นทุกอย่าง" แต่เป็น **per-subtask**
(design เต็มใน [README.md](README.md) + [pass_design.csv](pass_design.csv)) — หนึ่งตัวอย่างเทรน =
(ภาพหน้า, prompt เฉพาะ subtask จาก `pass2_used/*.md`, GT กรองเหลือเฉพาะ element ของ subtask นั้น)
หน้าเดียวกันออกได้หลายตัวอย่างต่างเป้า เหตุผล: t02's beam-plan failure (recall 11%, งานวิจัย
2 ฉบับใน `research_beam_grounding_vs_gridmaster.md` ยืนยันรูปแบบ detect-then-interpret 96.3% vs
one-shot 67.2%)

---

## 🔥 UPDATE 2026-08-24 ค่ำ — op04 ส่งข้อมูล 39 หลังเข้ามา: dataset 452 → 1,116

เวลา 20:21 คืนนั้น `json_แก้ไขแล้ว/` เพิ่มจาก 11 → **50 หลัง** (1,180 → 2,183 ไฟล์) จากรอบ
**op04** (`_scope.json` ในทุกหลังใหม่: `scope: pass2_only`, date 2026-08-23, agent 20 ตัวขนาน,
`tools/check_format.py` ผ่าน) — scope ตรงกับ 7 subtask ของ t03 พอดี ไม่มี index/material_list/
MEP ปน **และภาพครบทั้ง 50 หลังใน `image/`** → build ใหม่ได้ทันที

| subtask | 11 หลัง | **48 หลังที่ใช้ได้** |
|---|---|---|
| section | 223 | 484 |
| **plan_beam** (คอขวด) | 38 | **149** |
| schedule | 66 | 119 |
| notes | 55 | 117 |
| plan_footing | 35 | 111 |
| plan_slab | 23 | 86 |
| gridline | 12 | 50 |
| **รวม** | **452** | **1,116** |

**val split ใหม่ — มะขามสั่ง "4/1 ดีกว่า" (10:1 เดิมแย่เกินไป):**
`VAL_HOUSES` = บ้าน **01-05 ทั้งหมด = ทุกหลังที่คนรีวิวเนื้อหากับภาพต้นฉบับแล้ว**
→ **train 887 (43 หลัง op04) / val 229 (5 หลัง) = 3.87:1** ตรงเป้า
ผลพลอยได้ที่สำคัญกว่าอัตราส่วน: **val = GT รีวิวแล้ว 100% · train = op04 ล้วน** ไม้บรรทัด
สะอาดทั้งอัน · **plan_beam val 4 → 18** (วัด subtask คอขวดได้จริงเป็นครั้งแรก)
ข้อจำกัดที่รับ: val ไม่มีบ้าน 3 ชั้น/บ้านใหญ่ (อยู่ในกลุ่ม op04 ที่ยังไม่รีวิว) และ train
เสียบ้านคุณภาพสูงสุด 5 หลังไป — แลกเพื่อให้ตัววัดเชื่อถือได้

**3 เรื่องที่เจอตอน build ชุดใหม่ (บันทึกไว้ ไม่ได้เดาแก้):**
1. `31บ้าน_เล็ก_1ชั้น_11/…หน้า25_plan_footing.json` **ถูกตัดกลางไฟล์** (agent op04 โดน API
   session-limit ตัด ตามที่ `_scope.json` เขียนไว้เอง) — builder มี guard ข้ามพร้อมรายงานชื่อ
   **ไม่ซ่อมโดยเดาค่าที่หาย** (= ปลอม GT) ต้องสกัดหน้านั้นใหม่รอบหน้า
2. 8 หน้า plan ที่ไม่มี element ตรง subtask ถูกข้ามพร้อมรายงานชื่อครบใน `stats.json`
3. **1 ตัวอย่างประเมินแล้วเกิน MAX_LENGTH** (บ้าน 31 gridline: 4 ภาพ + GT 19,114 ตัวอักษร
   ≈ 34,854 est) — assert เดิมมองไม่เห็นเพราะเช็คเฉพาะ "ตัวที่ภาพเยอะสุด" ซึ่งไม่ใช่ตัวที่
   ยาวสุดจริง **แก้ assert ให้เช็ค 3 อันดับแรกตามการประมาณ ภาพ+prompt+GT** แทน

## Dataset เดิม (11 หลัง) — สร้าง 2026-08-24 บ่าย (Claude ภายใต้ att1235 ระหว่างมะขามไม่อยู่)

`data_before_tune/build_dataset_t03.py` → `train.jsonl` (408) + `val.jsonl` (44, บ้าน 03
ทั้งหลังตาม precedent t01/t02) + `images/` (353 ไฟล์) + `stats.json` + `images_manifest.txt`

| subtask | ตัวอย่าง | หมายเหตุ |
|---|---|---|
| section | 223 | ทุก discipline |
| schedule | 66 | รวม door/window schedule (หน้าที่ t02 ทำได้ดีสุด 86%) |
| notes | 55 | |
| plan_beam | 38 | รวมโครงหลังคา (หลังแก้ pattern roof_plan→plan 8 หลัง วันเดียวกัน) |
| plan_footing | 35 | รวมเสา (plan_column ยุบเข้านี่ — ดูการตัดสินใจข้างล่าง) |
| plan_slab | 23 | |
| gridline | 12 | multi-image จาก source_pages[] ของ gridmaster |
| **รวม** | **452** | material_list ตัดทิ้ง 435 ไฟล์ (op04 ruling), pass3 อีก 331 |

**Integrity ตรวจแล้ว 🔍:** ทุกแถว JSON parse ผ่าน, ภาพอ้างอิงครบ 0 missing, `{{TARGET}}`/
`{{ELEMENT_TYPES}}` แทนค่าแล้วจริง, ตัวอย่าง plan_* ฝัง grid master (x_lines/y_lines) ใน prompt
ตาม input spec ของ pass_design.csv

**การตัดสินใจที่ทำไปแล้ว (มะขามทบทวนได้ — ทั้งหมดอยู่ใน docstring ของ build_dataset_t03.py):**
1. **plan_column ยุบ** — มีหน้าแปลนเสาเดี่ยวๆ แค่ 2 ไฟล์ใน 11 หลัง (`dataset_sizing.md` เตือนไว้
   ว่าเทรนแยกไม่ได้) เสาเข้าชุดผ่าน plan_footing ซึ่งตาราง `pass2_used/plan.md` รวม column
   อยู่แล้ว — หน้า column+beam plan ออก 2 ตัวอย่าง (plan_footing เป้าเสา / plan_beam เป้าคาน)
2. **plan_* จำกัด structural** — แปลนสถาปัตย์/MEP เป็น pass3 ไม่เข้ารอบนี้; section/schedule/notes
   เอาทุก discipline (pattern-based)
3. **val = บ้าน 03 ทั้งหลัง** ตาม precedent
4. plan_beam จับ element_type แต่งเองของโครงหลังคาด้วย regex (`rafter|purlin|ridge|hip|valley|truss`)
   — ไม่งั้นหน้าโครงหลังคาบ้าน 07 (steel_rafter/steel_ridge/...) หลุดทั้งหน้า

**Ground truth ที่ใช้ผ่านการ normalize รอบใหญ่วันเดียวกัน (2026-08-24):** 267 จุด/246 ไฟล์ +
gridmaster ทั้ง 12 ได้ `z_levels[]` — ดู `json_แก้ไขแล้ว/README.md` บันทึกการแก้ไข 2026-08-24
สำหรับรายการเต็มและสิ่งที่จงใจไม่แตะ

**ข้อจำกัดของ GT ที่ต้องพูดตรงๆ ก่อนอ่านตัวเลข accuracy ที่จะได้:**
- บ้าน 06-11 **ยังไม่ผ่านรีวิวเนื้อหากับภาพต้นฉบับ** (แค่ format-normalize — README ของ
  json_แก้ไขแล้ว บอกชัด) มะขามสั่ง "ทำบ้านทุกบ้าน" จึงรวมทั้ง 11 — แต่ตัวเลข val ที่ได้จะสะอาด
  (บ้าน 03 อยู่กลุ่มรีวิวลึกแล้ว) ส่วน train มีสัญญาณรบกวนจาก 6 หลังที่ยังไม่รีวิว
- **beam plan ทุกหลังยังไม่เคยถูกตรวจว่าคานหายหรือเปล่า** (README item เดิม — บ้าน 01-05 ตอนตรวจ
  เจอคานหายทุกหลัง) plan_beam คือ subtask ที่แบกความหวังรอบนี้ แต่ GT ของมันคือส่วนที่ตรวจน้อยสุด
- โครงหลังคาบ้าน 09 (หน้า28) ไม่มี positional elements ใน GT เลย (มีแค่ specs{}) — ถูกข้ามจาก
  dataset โดยตั้งใจ (สอนโมเดลด้วย GT ว่างบนหน้าที่เต็มไปด้วยคาน = สอนโรค under-extraction)
- prompt ทั้ง 7 ไฟล์ใน `pass2_used/` **ยังไม่เคยถูกยิงกับโมเดลจริงสักครั้ง**

---

## Phase 0 — Pre-flight (rule_of_tune ข้อ 4: ทำจริง+ตรวจจริง ก่อนเสียเงินเช่า)

| # | รายการ | สถานะ |
|---|---|---|
| 1 | **เลือกโมเดล** | ✅ มะขามเคาะ 2026-08-24: **Qwen3.6-35B-A3B** (ตัว t01 — ข้อดี: ทั้ง tuned/base ถูกวัดบนบ้าน 11 ไปเช้านี้ = มี baseline ตรงรุ่น + เส้นทาง export GGUF+mmproj ของ t01 ใช้ซ้ำได้ถ้า freeze vision เหมือนเดิม) |
| 2 | dataset พร้อม (452 ตัวอย่าง + ภาพ 353 + manifest) | 🔍 |
| 3 | สคริปต์เทรน — **เขียนใหม่แล้ว: `data_before_tune/train_t03.py`** (มะขามสั่งเขียนใหม่+อ้างอิงเน็ต 2026-08-24) ทุกค่ามีที่มากำกับ [W]=เว็บ/[t01]/[t02]/[t03]=วัดจริง — สำคัญสุด: **MAX_LENGTH=32768 คำนวณจากข้อมูลจริง** (8 ตัวอย่าง gridline ทะลุ 24576 เดิม สูงสุด ~26,791 est. — บั๊กคลาส t01 §0.4 จับได้ก่อนเทรน) + assert ตรวจ batch แรกทั้ง visual-token (กัน 512px silent) และ seq ยาวสุด (กันตัด label) syntax check ผ่าน **ยังไม่เคยรันบน GPU** | 🔍 |
| 4 | Parity table — 🔍 ทำแล้ว 2026-08-24 (ดู section "Parity table" ข้างล่าง) เจอจริง 2 จุด: `PYTORCH_ALLOC_CONF` หาย + `FINETUNE_VISION` โดน hardcode — แก้ใน train_t03.py แล้วทั้งคู่ (syntax re-check ผ่าน) | 🔍 |
| 5 | HF token ใช้ได้ (เพิ่งใช้เช้านี้กับงาน t01-vs-base สำเร็จ — ต้องเช็คซ้ำวันเทรนจริง) | 🔍 |
| 6 | Vast.ai เครดิต+บิล — ✅ เช็คผ่าน vastai CLI (API key "t02", 2026-08-24 เย็น): บิลเช้า $5.43 — **GPU จริง $1.1067/hr, ตัว $0.056 ที่หน้าเว็บโชว์คือเรท storage** (ไขปริศนา 30x-misread แล้ว) เครดิตเหลือ **$8.91** พอสำหรับคืนนี้ (~$3-6) กติกาใหม่: เช็คราคาผ่าน `vastai search offers` (dph_total) เท่านั้น + Claude คุม เช่า/destroy จาก CLI ได้เองแล้ว | ✅ |
| 7 | ทดสอบสั้น `TEST_STEPS=5` — ✅ รันจริง 2026-08-24 22:00 บน instance 48567519 **ผ่าน 5 step ไม่ OOM ไม่ error** · visual token **3,778/ภาพ** (ภาพจริง 2339×1654 ต่ำกว่า cap 5,120 อยู่แล้ว = ไม่ย่อเลย ตรงข้ามกับบั๊ก t01 ที่เหลือ 266) · seq multi-image ยาวสุด **21,445** < 32,768 · **~55 วิ/step** (step แรก 152 วิ รวม warmup) · loss 1.86 @ step5 — **แต่ตายตอน eval ดูด้านล่าง** | ✅ |

## ⛔ บทเรียนใหม่ 2026-08-24 — eval ต่อ epoch OOM ทั้งที่การเทรนไม่ OOM

`TEST_STEPS=5` ผ่านการเทรน 5 step สบายๆ แล้ว **ตายทันทีตอนเข้า evaluate**:
`evaluate → evaluation_loop → unsloth_prediction_step → compute_loss → forward →`
**`accelerate/utils/operations.py: convert_to_fp32`** → `OutOfMemory: ขอ 24.72 GiB`
(ใช้ไปแล้ว 88.78/94.97 GiB, fragmentation ไม่ใช่สาเหตุ — unallocated เหลือแค่ 245 MiB)

**สาเหตุจริง:** accelerate ห่อ `model.forward` ด้วย wrapper ที่ upcast **output ทั้งก้อน**
เป็น fp32 → logits ขนาด seq 21,445 × vocab 152k × 4 B ≈ **13 GB** (+ต้นทาง bf16 6.5 GB)
ตอน**เทรน**ไม่เจอเพราะ Unsloth ใช้ fused/chunked loss ไม่ materialize logits เลย

**ทำไมเพิ่งเจอที่ t03:** t01 เป็น 35B เหมือนกันแต่ภาพโดนย่อ 512px (seq ~2-3k → logits fp32
แค่ ~1.8 GB) · t02 ความละเอียดเต็มแต่โมเดล 30B เหลือ headroom มากกว่า · **t03 คือรอบแรกที่
35B + ความละเอียดเต็มพร้อมกัน**

**แก้:** `eval_strategy="no"` (คงไว้ `save_strategy="epoch"` → มี checkpoint ทั้ง 3 epoch
ให้ย้อนวัดได้) — เสีย eval_loss ต่อ epoch ซึ่งเทียบกับ t01/t02 ไม่ได้อยู่แล้ว (คนละ prompt/GT)
ตัววัดจริงของ t03 คือ eval แบบ generate ต่อ subtask ที่ยังต้องเขียน

## 💥 บทเรียนใหม่ 2026-08-24 22:45 — CUDA illegal memory access ที่ step 42/321

รอบเทรนที่ 2 พังหลังวิ่งมา 40 นาที (loss ลงถึง **0.2183** แล้ว) — **ไม่มี checkpoint เลย**
เพราะ `save_strategy="epoch"` และ epoch 1 อยู่ที่ step 107

```
bitsandbytes/optim/optimizer.py:335 step → bitsandbytes/utils.py:206 sync_gpu
  → torch.cuda.synchronize() → AcceleratorError: CUDA error: an illegal memory access
```

**ตัวเลขที่อธิบายทุกอย่าง — `Trainable parameters = 1,890,448,640 (5.11%)`**
Unsloth ตรวจเจอ MoE แล้ว**เปิด LoRA บน expert layers ทั้ง 256 ตัว**
(`mlp.experts.gate_up_proj`, `mlp.experts.down_proj`) → LoRA ก้อนใหญ่ผิดปกติ ทำให้ log ขึ้นเองว่า
`Will smartly offload gradients to save VRAM!` + `Double buffering enabled (parallel H2D + compute)`
= มีการคัดลอก host↔device แบบ async ตลอดเวลา ซ้อนกับ `paged_adamw_8bit` ที่จองผ่าน
**unified memory (cudaMallocManaged)** อีกชั้น — แหล่ง illegal-address คลาสสิกเมื่อความดัน
หน่วยความจำสูง (น้ำหนัก 74GB + LoRA 3.8GB + grads 3.8GB + states 3.8GB บนการ์ด 95GB)

**พิสูจน์ว่าไม่ใช่การ์ดเสีย:** หลังพัง `nvidia-smi` = 50 MiB / 53°C, ไม่มี Xid, และ 41 step แรก
วิ่งปกติ · error เป็น **async** (`stacktrace อาจไม่ตรงจุดจริง`) จึงยืนยันได้แค่ว่ามัน*โผล่*ที่ bnb sync

**แก้ 2 จุด (ตัดสินภายใต้ att1235):**
1. `paged_adamw_8bit` → **`adamw_8bit`** — VRAM เท่าเดิม (states 8-bit ~3.8GB) แต่ตัด
   unified-memory paging ทิ้ง = ตัดกลไกที่ traceback ชี้ตรง
   *ความเสี่ยงที่รับ:* non-paged อาจ OOM ตอน optimizer step — แต่จะพังที่ step 1 (รู้ใน 2 นาที)
   ไม่ใช่ 40 นาที
2. `save_strategy="steps", save_steps=25, save_total_limit=2` — เสียมากสุด 23 นาที ไม่ใช่ทั้งรอบ
   (adapter 1.89B bf16 ≈ 3.8GB/ครั้ง × 2 = 8GB, ดิสก์ว่าง 74GB)

**ผลของการแก้ (รอบ 3, 23:00) — OOM ที่ step 3 และนั่นคือข้อมูลที่ต้องการ:**
`OutOfMemory: ขอ 846 MiB · ใช้ไป 93.07 จาก 94.97 GiB · เหลือว่าง 470 MiB`
→ **หน่วยความจำตึงจริง ไม่ใช่แค่บั๊ก paging** — paged มีไว้เลี่ยง OOM นี้ พอเอา paging ออกก็ OOM ทันที
พังภายใน 3 นาทีตามที่ประกาศความเสี่ยงไว้ (ไม่ใช่ 40 นาที) = การแลกที่คุ้ม ได้ข้อสรุปเร็ว

**รอบ 4 (23:05) — ลดการใช้จริง ไม่ใช่ย้ายที่เก็บ: `lora_r` 32 → 16, `lora_alpha` 64 → 32**
บัญชีหน่วยความจำ: น้ำหนัก 74GB (ตายตัว) + LoRA 3.78 + gradient 3.78 + optimizer 8-bit 3.78
= 85.3GB เหลือ activation ไม่ถึง 10GB ซึ่งไม่พอสำหรับ sequence 30,368 token
r=16 ลดทั้งสามก้อนครึ่งหนึ่ง = **คืน ~5.7GB** ขาดจริงแค่ ~1-2GB → เหลือ margin ~4GB
คง `adamw_8bit` (non-paged) ไว้ = **ตัดกลไกที่พังทั้งสองตัวพร้อมกัน** (ไม่มี unified memory →
ไม่มี illegal access · มี headroom → ไม่ OOM) · alpha/r = 2 เท่าเดิม scaling ไม่เปลี่ยน
[W] LWR: จำนวน layer สำคัญกว่า rank — ยังแปะครบทุก layer รวม MoE experts เหมือนเดิม

**ถ้ารอบ 4 ยัง OOM → แผนสำรองที่ตรวจราคาไว้แล้ว:** เช่า **H200 NVL 140GB $3.601/hr**
(มี 10 ตัวเลือก ≥130GB, ถูกสุด $3.601, B200 179GB $5.314) กลับไปใช้ r=32 + paged ได้เลย
เพราะ headroom 46GB — 5.3 ชม. ≈ $19 จากเครดิต $33.30 ยังไหว **แต่ลองของถูก 3.6 เท่าก่อน**

**สิ่งที่ยังไม่รู้ (พูดตรงๆ):** ยังไม่ได้พิสูจน์ว่า paged คือสาเหตุของ illegal access — error แบบ
async ชี้จุดตายไม่ได้ สิ่งที่พิสูจน์แล้วคือ **ความดันหน่วยความจำสูงจริงจนเหลือ 470 MiB** ซึ่งเป็น
เงื่อนไขที่ทำให้ทั้ง paging thrash และ illegal access เกิดได้ทั้งคู่

## Phase 1+ (หลัง Phase 0 ครบ — โครงตาม t02_workflow.md)

**เช่าแล้ว 2026-08-24 ค่ำ: instance 48567519 — RTX PRO 6000 WS 96GB, $1.002/hr จริงจาก API**
(offer 47725426, rel 0.995, ~800Mbps, disk 150GB, image `vastai/pytorch:cuda-12.8.1-auto`,
onstart = `data_before_tune/onstart.sh` ใหม่ — ดัดแปลงจาก t02 + xgrammar บังคับ)

เช่าเครื่อง ≥80GB VRAM → upload `data_before_tune/` → verify env → short test → full train →
eval per-subtask (ต้องเขียน eval ใหม่: `eval_fields.py` เดิมเทียบทั้งหน้า แต่ t03 ต้องเทียบ
ต่อ subtask — ยังไม่ได้เขียน ⬜) → backup ขึ้น HF ก่อนคิดเรื่อง destroy (Mark-of-Shame)

**📌 กติกา inference ถาวรของ t03 (มะขามสั่ง 2026-08-24): หน้า beam plan (subtask
`plan_beam`) ต้องแนบ xgrammar ตอนส่งทุกครั้ง** — หน้าคลาสนี้คือตัววนซ้ำ/JSON ไม่ปิด
(บ้าน08 หน้า20, บ้าน09 หน้า26 48→2 collapse; xgrammar พิสูจน์แล้ว 96.8% vs 57.9%,
rule_of_tune ข้อ 13) ใส่แล้วใน demo generation ของ `train_t03.py` (`setup_grammar()` —
เลือก demo ให้มี plan_beam อย่างน้อย 1 ตัวเสมอ) — **inference runner จริงของ t03 (ยังไม่
เขียน ⬜) ต้องทำตามกติกานี้ด้วย** (`pip install xgrammar` ต้องอยู่ใน onstart ของเครื่องเช่า)

## 📌 กติกาถาวรเพิ่ม (มะขามสั่ง 2026-08-24 ค่ำ) — off-grid elements + gridmaster ครบทุกระยะ

1. **Element ที่ไม่อยู่บนกริดของกระดาษ (plan_beam หรือ pass2 ใดๆ): ใช้ bbox นับ pixel
   แล้วเทียบตำแหน่งกับ gridmaster — ยึดค่าใน gridmaster เป็นหลักเสมอ** (pixel เป็นแค่ตัว
   interpolate หาว่าอยู่ระหว่างกริดไหน ระยะจริงมาจาก pos_m ของ gridmaster ไม่ใช่จากการวัด pixel)
2. **Prompt ของ gridmaster ต้องเน้นย้ำ: บันทึกระยะ "ทุกๆ อย่าง" ที่พบใน side profile และ
   หน้าที่กำหนด** — ไม่ใช่แค่กริดหลัก

**ทำไมยังเข้าเทรนคืนนี้ไม่ได้ (บันทึกไว้ตรงๆ):** GT ปัจจุบันไม่มีข้อมูลรองรับทั้งคู่ —
gridmaster ทั้ง 12 ยังไม่มี `dimension_chains[]`/`unassigned_dimensions[]` (image sweep ยังไม่ทำ)
และ plan GT ไม่มี bbox ให้เรียน ถ้าแก้ prompt ให้เรียกร้องสิ่งที่ label ไม่มี = สอนโรค
under-extraction (เหตุผลเดียวกับที่ข้ามหน้าโครงหลังคาบ้าน 09) จัดลง phase จริง:

| ข้อ | ไปอยู่ที่ไหน | เมื่อไหร่ |
|---|---|---|
| 1 (bbox↔gridmaster) | **t03 inference runner** (⬜ ยังไม่เขียน) — logic หลังได้ JSON: element off-grid → interpolate จาก bbox → snap เข้า pos_m ของ gridmaster | เขียน runner หลังเทรนคืนนี้ |
| 1 (prerequisite) | **grounding bbox probe** (~$0.1 บนเครื่องเช่าคืนนี้) — พิสูจน์ก่อนว่าโมเดลให้ bbox แม่นพอไหม | คืนนี้ หลังเทรนเสร็จ |
| 2 (prompt gridmaster) | **op04 รอบข้อมูลหน้า**: ทำ dimension_chains image sweep ให้ GT ครบก่อน → แก้ prompt `pass2_used/gridline.md` พร้อมกัน → เข้าเทรน t04 | รอบหน้า — ห้ามแก้ prompt ก่อน GT พร้อม |

## 🔑 `att1235` — มะขามให้ไว้แล้วสำหรับงานคืนนี้ทั้งชุด (2026-08-24)

**อนุมัติล่วงหน้าแล้ว ห้ามเด้งกลับไปถาม** — ทุกอย่างในลำดับปิดงานข้างล่างทำได้เลย รวมถึง
`vastai destroy instance` (ลบถาวร กู้ไม่ได้) และ `shutdown` เครื่องทำงาน ตลอดจนการตัดสินใจ
ระหว่างทาง (เลือก checkpoint, ตัดงานที่เวลาไม่พอ, แก้ค่าที่ต้องแก้)

**สิ่งที่ code นี้ไม่ได้ยกเลิก** (ตาม rule_of_tune §att1235):
- **ยังต้องพูดความเสี่ยงหนึ่งบรรทัดตอนลงมือ** สำหรับสิ่งที่ย้อนไม่ได้ — "อนุมัติแล้ว" ไม่ใช่ "ห้ามบอก"
- **ยังต้อง log** — บันทึกลง workflow นี้ + workmen's diary เหมือนเดิม
- **Day of Shame ยังต้องเช็คก่อน destroy เสมอ** (ข้อ 1 ข้างล่าง) — att1235 ไม่ได้อนุญาตให้ข้ามการ verify
  ไฟล์ก่อนลบเครื่อง นั่นคือบทเรียนที่ทำให้เสียงานทั้งคืนไปแล้วครั้งหนึ่ง

เขียนผลลัพธ์เป็น "ตัดสินแล้ว ✅ + เหตุผล + ความเสี่ยงที่รับ" เสมอ ไม่ใช่ "รอมะขามเคาะ"

## 🌙 ลำดับปิดงานคืนนี้ (มะขามสั่ง 2026-08-24, `code=att1235`) — ทำตามลำดับ ห้ามสลับ

| # | ขั้น | รายละเอียด | สถานะ |
|---|---|---|---|
| 1 | **check Day of Shame** | `python3 pull_and_verify_t03.py` → scp adapter ลงเครื่องเรา แล้วเทียบ **ชื่อไฟล์ + ขนาด + sha256 ทีละไฟล์** remote-vs-local · ต้องเห็น **✅ PASS** เท่านั้น (สคริปต์บังคับ: ไม่มีไฟล์ = FAIL, ไม่มี `.safetensors`/`adapter_config.json` = FAIL, `--fast` ไม่มีวันให้ไฟเขียว) · แล้ว **อัปขึ้น HF จากเครื่องเรา** (ข้อ 1b) *ก่อน* destroy | ⬜ |
| 1b | **อัป adapter ขึ้น HuggingFace** | `hf upload Sicilian44/t03 <local lora dir> .` · **repo พร้อมแล้ว: https://huggingface.co/Sicilian44/t03 — สาธารณะ (มะขามสั่ง 2026-08-24 23:25) มี model card ไทยแล้ว** · ทดสอบเขียนสำเร็จจริง (commit `51ba9d6`, `1ef6b0a`) · `user=Sicilian44`, token fine-grained ชื่อ `t03` มะขามพิมพ์เองใน PowerShell เก็บที่ `~/.cache/huggingface/token` **บนเครื่องมะขาม ไม่เคยผ่านแชทและไม่เคยไปอยู่บนเครื่องเช่า** (ตั้งใจ: token เขียนได้ไม่ควรอยู่บนเครื่องที่เช่าคนอื่นมา) · อัปจากเครื่องเราหลัง verify ผ่าน → มีสำเนา 2 ที่ก่อน destroy · **หมายเหตุ STECON: repo สาธารณะ = ทีมคู่แข่งโหลด adapter ไปใช้ได้ ถ้าไม่ต้องการ เปลี่ยนเป็น private ได้ทุกเมื่อด้วย `update_repo_settings(private=True)` แต่ของที่ถูกโหลดไปแล้วเรียกคืนไม่ได้** | ⬜ |
### เครื่องมือ overlay ภาพเทียบตำแหน่ง (มะขามส่งภาพตัวอย่างมา 2026-08-24 ดึก, สร้างเสร็จ+ทดสอบแล้ว)

**`data_before_tune/overlay_gt_vs_ai.py`** — GT เขียว vs AI ส้ม วางทับหน้าแบบจริง (HoughCircles หา
วงกลมป้ายกริด → fit เส้นต่อแกน → แปลง `grid_ref`+`pos_m` เป็นพิกเซล) ต่างจาก `t02/overlay_gt_vs_ai_house09.py`
เดิมตรงไม่ผูกกับบ้าน/ชุดผลตายตัว — รับ `--house`/`--ai`/`--label`/`--pages`/`--grid-instance`,
อ่านได้ทั้งผล t02 (`views[].elements[]`) และ t03 (`infer_house_t03.py`'s `.txt` ต่อ subtask, union
ต่อหน้า), นับ**อย่างซื่อสัตย์**(ref แปลงพิกัดไม่ได้ยังอยู่ในตัวหาร ไม่หายเงียบๆ), ข้ามหน้าที่หา
กริดไม่เจอแทนวาดผิด (`--selftest` มี assert คุมการ parse ref ทั้ง 3 รูปแบบ + การ fit กริด)

**ทดสอบจริงกับบ้าน 08 (GT vs t02) แล้ว 2026-08-24 ดึก — ยืนยันด้วยภาพ ตรงกับตัวเลข id-recall
ที่ agent ก่อนหน้าถอดไว้เป๊ะ:**

| หน้า | GT | AI t02 | ยืนยันด้วยภาพ |
|---|---|---|---|
| 06 (floor plan, 2 กริด) | 9/17 | 1/3 | |
| 19 (ฐานราก, 2 กริด) | 4/4 | 2/4 | วงกลมลงตรง F5/F9 จริง |
| **20 (แปลนคาน)** | **27/31** | **0/6** | **ภาพยืนยัน 0 กรอบส้มจริง** — output จริงคือ `"1'D'C'B'A x D C B A"` ยัดกริดทั้งแถวไว้ในสตริงเดียว แปลงพิกัดไม่ได้เลยสักตัว |
| 21 (คานอะเส, 2 กริด) | 24/32 | 0/4 | |

**2 บั๊กที่การทำให้ทั่วไปจับได้ (ไม่ใช่แค่ย้ายโค้ดบ้าน 09 มาใช้บ้าน 08):** (1) single-linkage
chaining มัดวงกลม title-block เข้าเป็นกลุ่มเดียวกับกริด — หน้า 21 พังทั้งหน้าเพราะเรื่องนี้ แก้เป็น
windowed grouping (2) เลือก fit ที่ residual ต่ำสุดไม่พอ — หน้าที่มี 2 แผนผังใช้แถวเสาร่วมกัน (19)
เอา fit ผิดแผนผังมาวาดเงียบๆ ต้อง enumerate ทุก fit แล้วให้ผู้ใช้เลือกด้วย `--grid-instance`

**หมายเหตุ t03 path:** ยังไม่มีผล inference จริง (โมเดลยังเทรนไม่เสร็จ) — ทดสอบ path การอ่านไฟล์
ด้วยชุด synthetic เท่านั้น (union 4 subtask ไฟล์ของหน้า 20 ได้ 27/31 ตรง GT เป๊ะ, ไฟล์เสีย 1 ไฟล์
รายงาน "JSON เสีย" โดยไม่ทำหน้าอื่นพัง) — **path การยิงโมเดลจริงยังไม่เคยพิสูจน์**

| 2 | **ให้ AI ที่เพิ่งเทรนถอดแบบ บ้าน 08** (`08บ้าน_เล็ก_1ชั้น_03`) — *เปลี่ยนจากบ้าน 32 ตามคำสั่งมะขาม 2026-08-24 ดึก* | เหตุผล: **บ้าน 08 มีผลของ t02 และ Qwen เพียวๆ อยู่แล้ว** (`tune_ai/t02/ผล/08บ้าน_เล็ก_1ชั้น_03/` 25 หน้า) → เทียบข้ามรอบได้ · ทำเฉพาะงาน pass2 = **33 งาน** (section 13, notes 5, schedule 5, plan_footing 4, plan_beam 3, plan_slab 2, gridline 1) · `python3 infer_house_t03.py --house 08 --adapter outputs_t03/lora` · **plan_beam แนบ xgrammar อัตโนมัติ** (กติกาถาวร) | ⬜ |
| 2b | **ยิง Qwen3.6 เพียวๆ (untuned) บนบ้าน 08 ด้วย prompt ของ t03** | `python3 infer_house_t03.py --house 08 --base` — **ผล base ของบ้าน 08 ไม่เคยมีมาก่อน** (ที่มีคือบ้าน 11 จากเช้า 2026-08-24) จึงต้องสร้างเอง · บ้านเดียวกัน prompt เดียวกัน ตัววัดเดียวกัน **ต่างกันแค่ adapter** = การเทียบที่ตัดตัวแปรกวนทั้ง 6 ข้อออก ต่างจากเลข t02 ที่เป็นบริบทประวัติศาสตร์เท่านั้น (~50 นาที รวมโหลดโมเดล ~$0.9) | ⬜ |
| 2c | *(ถ้าเวลาพอ)* plan_beam ของ val ทุกหลัง | `--all-val --subtask plan_beam` = **18 งาน 5 หลัง** แทนที่จะเป็น 3 งานของบ้าน 08 เดี่ยวๆ — subtask ที่แบกความหวังทั้งรอบ (t02 = 0%) ต้องมี n มากพอถึงจะเชื่อตัวเลขได้ (~20 นาที) | ⬜ |
| 2d | **ทำภาพเปรียบเทียบ** (มะขามสั่ง 2026-08-24 — แบบเดียวกับ `เปรียบเทียบผลทูน_t01_vs_t02_2026-07-29.png`) | เติมตัวเลข t03/base ลง `data_before_tune/comparison_data.json` แล้ว `python make_comparison_png.py` → `tune_ai/t03/เปรียบเทียบผลทูน_t03_2026-08-25.png` · **สร้างและทดสอบแล้ว 2026-08-24 23:20** (คอลัมน์ t02 ของจริงครบ, t03/base ขึ้น `n/a` รอเติม) · เครื่องนี้ไม่มี puppeteer/matplotlib จึง render ด้วย **Edge headless** (บั๊ก `Access is denied` เกิดจาก `--screenshot=` เป็น path สัมพัทธ์ — ต้องใช้ absolute + `--user-data-dir` ชั่วคราว + เขียนลง path ASCII ก่อนแล้วค่อย move ไปชื่อไทย) · **`n/a` ต้องไม่กลายเป็น 0%** — "ยังไม่วัด" กับ "วัดแล้วได้ศูนย์" ต้องแยกให้เห็น | ⬜ |
| 3 | **คืนการ์ดจอ** | `vastai destroy instance 48567519` — ทำหลังข้อ 1 **และ 1b** ผ่านเท่านั้น | ⬜ |
| 4 | **ปิดเครื่องทำงาน** | `shutdown //s //t 60` (Bash, double-slash) — อนุมัติแล้วด้วย `att1235` | ⬜ |

**การแบ่งข้อมูลสุดท้าย (มะขามสั่ง "เอาบ้าน 08 ออกจาก dataset" 2026-08-24 ดึก) — 3 ส่วนแยกขาด:**

| split | จำนวน | บ้าน | บทบาท |
|---|---|---|---|
| train | **854** | 42 หลัง (op04 + 06,07,09,10,11) รวมบ้าน 32 | เทรน |
| val | **229** | 01-05 (รีวิวเนื้อหาแล้วทั้งหมด) | ไม้บรรทัดคุณภาพ GT · **3.73:1** |
| **test** | **33** | **08 เท่านั้น** | benchmark ข้ามรอบ — อยู่นอก train และ val |

`build_dataset_t03.py` เขียน `test.jsonl` แยกออกมา (`TEST_HOUSES`) · **ยืนยันแล้วว่า `train.jsonl`
md5 ไม่เปลี่ยนจากตอนเริ่มเทรน** — การเปลี่ยนครั้งนี้จึงไม่กระทบรอบที่กำลังวิ่ง (และ `eval_strategy="no"`
แปลว่าการเทรนไม่เคยแตะ val/test อยู่แล้ว) · บ้าน 32 อยู่ใน train ตามปกติ ไม่เคยถูกกันออก

### เบสไลน์บ้าน 08 ที่มีอยู่จริง (ตรวจแล้ว 2026-08-24 ดึก — แก้ความเข้าใจ 1 จุด)

**❗ "Qwen เพียวๆ" ของบ้าน 08 ไม่มีอยู่จริง** — ผล base/untuned ที่มีคือ **บ้าน 11** (รันเช้า 2026-08-24)
บ้าน 08 มีแค่ t02 · t01 รันบ้าน 08 ได้หน้าเดียว (หน้า03 = title/material_list ไม่มี element) ใช้ไม่ได้

**t02 บนบ้าน 08** (25 หน้า, xgrammar, `_batch_summary.json`: 1991.4 วิ = 79.7 วิ/หน้า):

| ตัวชี้วัด | t02 |
|---|---|
| JSON valid | 24/25 (96%) — หน้า07 พังจาก degeneration loop ใน string |
| **element-id recall (15 หน้าที่ทับกับ GT)** | **2/57 = 3.5%** |
| plan_beam | **0.0%** (0/15) · plan_slab 0% · section 0% · schedule 0% |
| plan_footing | 33.3% (เจอแค่ F5, F9 หน้า19) |

อาการจริง: JSON ผ่านแต่ข้างในไม่มี `element_id` — หน้า20 คานทั้งหน้ายุบเหลือ 6 element เป็น zone
notation (`grid_ref: "B2-B2-B2… x D-D-C-C…"`, mark ซ่อนใน `sub_elements[].mark`), หน้า21 แต่ง id
เอง (`tie_rAfter_set_2`, `"tie_r After_set_3"`) **คือโรคที่ prompt ของ t03 เขียนมาห้ามโดยตรง**

**ข้อจำกัดของการเทียบ (agent ตรวจแล้ว — 3 ข้อแรกทำให้เทียบตรงๆ ไม่ได้ ไม่ใช่แค่ noise):**
(1) หน่วยงานต่างกัน — t02 = 1 คำถาม/หน้าทั้งหน้า, t03 = 1 คำถาม/(หน้า×subtask) หน้า20 ของ t03 = 3 คำถาม
(2) ตัวหารต่างกัน — t02 ตอบหน้า pass3 ด้วย (site_plan/side_profile) และ **ขาด 10 หน้าที่ GT มี**
    (เครื่องเช่ารอบนั้นมีภาพแค่ 25 หน้า) ตัวเลขทั้งหลังจึงหารด้วยหน้าที่ t02 ไม่เคยเห็น
(3) prompt+schema ต่างกัน — t03 บังคับ `element_id` ห้ามขาด + vocab ปิด (t02 ไม่มีข้อนี้)
    → ส่วนที่ดีขึ้นบางส่วนมาจาก prompt ไม่ใช่การทูน
(4) t02 รันแบบ xgrammar → ตัวเลข JSON-valid เทียบกับ t03 ที่ไม่ constrain ไม่ได้
(5) คนละ inference stack (t01 = GGUF/llama.cpp 1375 วิ/หน้า vs t02 = transformers 79.7 วิ/หน้า)
(6) หน่วยนับ: GT หน้า20 มี 31 element แต่ **12 distinct element_id** — ต่างกัน 2.6 เท่า
    **ทุกตัวเลขข้างบนใช้ distinct `element_id` เป็นหน่วย** `infer_house_t03.py` วัดหน่วยเดียวกัน

**→ ทางเทียบที่สะอาดจริง (ทำหลังเทรนเสร็จ): ยิง `--base` บนบ้าน 08 ด้วย prompt ของ t03 เอง**
`python3 infer_house_t03.py --house 08 --base` — Qwen3.6 untuned, บ้านเดียวกัน, prompt เดียวกัน,
ตัววัดเดียวกัน **ต่างกันแค่ adapter** = การเทียบที่ตัดข้อ (1)(2)(3)(4)(5) ออกหมด
(+~$1, ~1 ชม.) ส่วนเลข t02 3.5% เก็บไว้เป็นบริบทประวัติศาสตร์ ไม่ใช่ตัวเทียบหลัก

**หมายเหตุบ้าน 11:** มีผล t01-tuned + base จากเช้านี้ แต่บ้าน 11 **อยู่ใน train ของ t03**
(ไม่ได้ย้ายออกเพราะจะต้องเทรนใหม่รอบที่ 3) → ถ้ายิงบ้าน 11 ต้องกำกับว่า "เคยเห็นตอนเทรน"
ตัวเลขเป็นเพดานบน ไม่ใช่ generalization

## Parity table (rule_of_tune ข้อ 12) — diff call-site จริง 2026-08-24

เทียบ `train_t03.py` กับ t01 (`train_qwen36.py` — โมเดลตระกูลเดียวกัน) และ t02
(`train_qwen3vl.py` preset 30B-A3B — เจ้าของบทเรียน collator) **ทุก argument รวมค่าที่ไม่ได้เขียน**

| call site / arg | t01 (รันจริงแล้ว) | t02 (รันจริงแล้ว) | t03 | verdict |
|---|---|---|---|---|
| `PYTORCH_ALLOC_CONF=expandable_segments:True` (ก่อน import torch) | ✅ มี (ใส่หลัง OOM จริงขาด ~100MB) | ❌ ไม่มี | ❌ **ไม่มี → แก้แล้ว** | 🔴 t03 ใช้ MAX_LENGTH สูงกว่า t01 อีก (32768>24576) ยิ่งต้องมี |
| MODEL | Qwen3.6-35B-A3B | Qwen3-VL-30B-A3B | Qwen3.6-35B-A3B | ✅ = t01 |
| `from_pretrained(load_in_4bit)` | False | False | False | ✅ |
| `from_pretrained(use_gradient_checkpointing)` | "unsloth" | "unsloth" | "unsloth" | ✅ |
| `from_pretrained(max_seq_length)` | 24576 | 24576 | **32768** | ✅ จงใจ — วัดจากข้อมูลจริง (gridline ~26.8k) |
| args อื่นของ from_pretrained (dtype ฯลฯ) | default | default | default | ✅ default เหมือนกันทุกฝั่ง |
| model-class import | try FastVisionModel→FastModel | FastVisionModel ตรง | FastVisionModel ตรง | ✅ t01 พิสูจน์แล้วว่า FastVisionModel ใช้กับตระกูลนี้ได้จริง |
| `ip.size["longest_edge"/"shortest_edge"]` | 5120\*1024 / 256\*1024 (มี getattr guard) | เท่ากัน | เท่ากัน (ไม่มี guard — ตระกูลพิสูจน์แล้วว่ามี ip) | ✅ |
| `get_peft_model` ทั้ง 11 args (vision F/lang T/attn T/mlp T, r32, α64, dropout 0, bias none, seed 3407, rslora F, loftq None) | ตรงกันทั้ง 3 ไฟล์ทุกตัว | | | ✅ |
| `FINETUNE_VISION` toggle | env var (default 0) | env var (default 0) | **hardcode False → แก้เป็น env var แล้ว** | 🟡 ค่า default เท่าเดิมเป๊ะ แต่ A/B รอบหน้า (FINETUNE_VISION=1) ต้องรันได้โดยไม่แก้ไฟล์ |
| `UnslothVisionDataCollator` | **(model, tokenizer) เปล่า = บั๊ก 14x (266 visual tok)** | resize="max", max_seq_length | resize="max", max_seq_length | ✅ t03 ตาม t02 (fix) — จงใจไม่ตาม t01 (t01 คือฝั่งที่พัง) |
| pad_token check (`<|vision_pad|>` issue #4104) | ไม่มี | มี (print เตือน) | ไม่มี | 🟢 inert ที่ batch=1 (ทั้ง 3 ใช้ batch=1) — บันทึกไว้ว่ารู้ |
| SFTConfig: batch/grad_accum/warmup/epochs/LR/logging/optim/wd/scheduler/seed/report_to/save/eval/eval_batch/remove_unused_columns/dataset_text_field/dataset_kwargs/bf16 | 1/8/0.05/3/1e-4/5/paged_adamw_8bit/0.01/cosine/3407/none/epoch/epoch/1/False/""/skip_prepare/True | เท่ากันทุกตัว | เท่ากันทุกตัว | ✅ enumerate ครบ 18 ตัว |
| SFTConfig: `max_steps` (TEST_STEPS) | `if >0 else -1` | dict-spread | dict-spread | ✅ พฤติกรรมเท่ากัน (ไม่ส่ง = default -1) |
| SFTConfig: `max_length` | 24576 | 24576 | 32768 | ✅ จงใจ (คู่กับ from_pretrained) |
| first-batch check | ไม่มี | visual-token assert | visual-token + longest-seq assert | ✅ t03 เข้มสุด |
| demo: max_new_tokens/do_sample/enable_thinking/add_special_tokens | 3000/False/False/False | เท่ากัน | เท่ากัน **+ xgrammar เฉพาะ plan_beam** | ✅ ส่วนเพิ่มคือกติกาถาวรของมะขาม |
| SKIP_DEMO | ไม่มี | มี | มี | ✅ |

**ผลจาก table → แก้ train_t03.py 2 จุด (2026-08-24):** เพิ่ม `PYTORCH_ALLOC_CONF` ก่อน
import torch, คืน `FINETUNE_VISION` เป็น env var (default 0 เท่าเดิม) — นอกนั้นไม่มี
ตัวแปรหลุดคุม

## การตัดสินใจทั้งหมด — ตัดสินแล้วภายใต้ att1235 (2026-08-24) ✅

ทุกข้อ**ตัดสินและลงมือแล้ว** ตามคำสั่ง "มีอะไรตัดสินใจให้เองเลย" — ไม่มีอะไรค้างรอ
มะขามแก้ทีหลังได้เสมอ (rebuild dataset ใช้เวลา <1 นาที) แต่ค่า default ที่จะเทรนคืนนี้คือชุดนี้:

1. **โมเดล = Qwen3.6-35B-A3B** — ✅ มะขามเคาะเองระหว่างวัน (แก้จากที่ Claude เสนอ Qwen3-VL)
2. **plan_column ยุบเข้า plan_footing** — ✅ ตัดสินตามหลักฐาน `dataset_sizing.md` (2 ไฟล์/11 หลัง
   เทรนแยกไม่ได้) ตาราง `pass2_used/plan.md` รวม column ใน plan_footing อยู่แล้ว
3. **gridline = multi-image → gridmaster ตรงๆ** — ✅ ตัดสินตามที่ `pass_design.csv` สมมติไว้
   (ปิด open question ของ README สำหรับรอบนี้) ความเสี่ยงที่รับ: ตัวอย่างยาวสุด ~26.8k tokens
   → MAX_LENGTH 32768 รองรับแล้ว
4. **บ้าน 06-11 (ยังไม่รีวิวเนื้อหา) อยู่ใน train** — ✅ ตามคำสั่งตรง "ทำบ้านทุกบ้านที่มีใน
   json แก้ไขโดยคน" ความเสี่ยงที่รับ: train มีสัญญาณรบกวนจาก 6 หลัง แต่ val (บ้าน 03)
   อยู่กลุ่มรีวิวลึก — ตัวเลขวัดผลยังเชื่อได้
