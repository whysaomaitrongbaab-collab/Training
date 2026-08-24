# ทดลองถอดแบบบ้าน 11 ด้วย t01 — เช่า GPU, ใช้ตัว not-gguf (transformers/PEFT)

> **แก้ไข 2026-08-24 (2): ลด scope จาก 3 บ้าน (08/09/10) เหลือ บ้าน 11 เดียว** (มะขามสั่ง
> เปลี่ยนใจ) — **ชื่อไฟล์ยังเป็น `_08_09_10_` ไม่ได้ rename ตาม** (ไฟล์เปิดอยู่ใน IDE ของ
> มะขามตอนสั่ง เปลี่ยนชื่อไฟล์ตอนนี้จะทำให้ tab เดิมหลุด) เนื้อหาข้างล่างคือของบ้าน 11 ทั้งหมด
>
> **แก้ไข 2026-08-24 (1): ยกเลิกแนวทาง local GGUF ในเอกสารเดิม** (`ทดลองถอดแบบ_08_09_10_local_workflow.md`)
> — มะขามสั่งเปลี่ยน: **รอบนี้เช่า GPU และใช้โมเดลตัวที่ไม่ใช่ GGUF** (bf16 เต็ม ผ่าน
> transformers/PEFT บนการ์ดจอเช่า, เหมือนวิธีที่ `eval_fields.py`/Phase 7 ของ t01 เคยวัดผล
> 90% JSON valid ไว้) แทนที่จะใช้ GGUF Q4_K_M ผ่าน llama-server บนเครื่องเอง — เลี่ยง
> quantization loss ของ GGUF เอกสารเก่ายังอยู่ (ตัวเลข classify จริงที่วัดได้ยังใช้อ้างอิงได้)
> แต่ **ให้ใช้เอกสารนี้แทนสำหรับการรันจริง**
>
> สัญลักษณ์: ⬜ ยังไม่ทำ · 🔍 Claude ตรวจ/รันแล้ว มีหลักฐาน แต่ยังไม่นับว่าผ่าน · ✅ มะขามยืนยันแล้วเท่านั้น

**เป้าหมาย:** อ่านบ้าน 11 (= `บ้าน_เล็ก_1ชั้น_06`) ด้วย 2 variant บน GPU เช่า
(≥80GB VRAM, bf16 เต็ม ไม่ใช่ GGUF) — เลือกบ้านเดียวก่อนเพื่อวัดเวลา/ราคาจริงจากของจริง (137 หน้า)
แทนที่จะคอมมิต 3 บ้าน 211 หน้าตั้งแต่แรก:

1. **`--variant tuned`** — t01: LoRA adapter `Sicilian44/qwen36-thai-rc/lora-adapter` บน
   base `unsloth/Qwen3.6-35B-A3B`
2. **`--variant base`** — `unsloth/Qwen3.6-35B-A3B` **untuned เพียวๆ** ไม่มี adapter (base
   model ตัวเดียวกับที่ t01 เอาไปทูน ไม่ใช่คนละ quant อย่างที่ local-GGUF เคยติดปัญหา — รอบนี้
   ทั้งสอง variant เป็น bf16 เท่ากันเป๊ะ ต่างกันแค่มี/ไม่มี adapter → apples-to-apples จริง)

สคริปต์ใหม่: **`data_before_tune/run_house_batch_t01.py`** — โครงสร้างเดียวกับ t02's
`run_house_batch.py` (โหลดโมเดลครั้งเดียว วนทุกหน้า, resume-safe) แต่พารามิเตอร์ทั้งหมด
(MAX_PIXELS/MIN_PIXELS, enable_thinking, max_new_tokens, ไม่มี repetition_penalty/grammar)
ก็อปมาจาก **t01 เองเป๊ะๆ** (`eval_fields.py`/`train_qwen36.py`) ไม่ใช่ยืมค่าจาก t02 (คนละโมเดล
คนละ hyperparameter — `unsloth/Qwen3.6-35B-A3B` vs `unsloth/Qwen3-VL-30B-A3B-Instruct`)

**2 phase แยกกัน (ประหยัดเวลา/เงินเช่า):**
- `--phase classify` — จัดหมวด pattern ทุกหน้า **รันครั้งเดียว ใช้ variant tuned เสมอ** (ผลลัพธ์
  ไม่ขึ้นกับว่า variant ไหนจะมาอ่านต่อ ไม่ต้องเสียเวลา/เงินจัดหมวดซ้ำ 2 รอบ)
- `--phase extract --variant tuned|base` — extract เต็มเฉพาะหน้าที่ pattern อยู่ใน t03 Pass 2
  (`gridline, plan, section, schedule, notes, material_list, soil_boring_log`) — รันแยก 2 รอบ
  ต่อ variant โดยใช้ผล classify เดียวกัน

---

## ทำไมเป็นการทดสอบที่ยุติธรรม + ข้อควรระวัง (เหมือนเอกสารเดิม ยังจริงอยู่)

🔍 ตรวจแล้ว (grep `train.jsonl`/`val.jsonl` ของ t01 จริง 2026-08-24): บ้าน 11
(`บ้าน_เล็ก_1ชั้น_06`) **ไม่ปรากฏในชุดทูนเลย** — t01 เทรนด้วย `เล็ก_1ชั้น_01/02`,
`เล็ก_2ชั้น_02/03` (train), `เล็ก_2ชั้น_01` (val) เท่านั้น → generalization test จริง

⚠️ `json_แก้ไขแล้ว/11บ้าน_เล็ก_1ชั้น_06/` **ยังไม่ผ่านรีวิวเนื้อหา** (README หัวข้อ "06-11":
เพิ่งเข้ามา 2026-08-02 ทำแค่ปรับรูปแบบ ยังไม่เช็คกับภาพต้นฉบับสักหน้าเดียว) — ถ้าจะใช้เทียบ
accuracy วันนี้ ตัวเลขจะปนความคลาดเคลื่อนของ ground truth เองด้วย

## ตัวกรองหน้า — t03 Pass 2 (เหมือนเดิม)

```
gridline, plan, section, schedule, notes, material_list, soil_boring_log
```
(`roof_plan`/`side_profile` เป็น Pass 3 — Constistant ยังไม่อ่าน ไม่ extract รอบนี้) พร้อม
CLASSIFY_PROMPT ที่แก้แล้วให้มีตัวเลือกครบ 16 pattern จริง (ของเดิมขาด `soil_boring_log`/
`bbs_schedule`)

**ขอบเขตที่ยังไม่ทำ:** ใช้ prompt เดียว (`PROMPT_SHORT` เต็มหน้า) ไม่ใช่ per-subtask prompt ของ
t03 (7 ไฟล์ `pass2_used/*.md` ยังไม่เคยถูกรันเลยสักตัว — เป็นงานคนละขนาดกัน)

## ขนาดงานจริง

| บ้าน | โฟลเดอร์ภาพ | จำนวนหน้า |
|---|---|---|
| 11บ้าน_เล็ก_1ชั้น_06 | `บ้าน_เล็ก_1ชั้น_06` | **137** (นับจาก `ls *.png` จริง 2026-08-24) |

บ้านนี้ยาวกว่า 08/09/10 แต่ละบ้านเกือบเท่าตัว (137 vs 63-75) — เป็นบ้านที่ยาวสุดในกลุ่ม 06-11
ตามที่ t02's เอกสารเดิมเคยตั้งข้อสังเกตไว้เหมือนกัน (`t02/ทดลองถอดแบบ_08_09_10_11_workflow.md`)

> 🔍 **พบจากอ่านโค้ดจริง (2026-08-24):** `run_house_batch_t01.py` มี `PAGE_FILTER["11"]`
> hardcode ไว้ 34 หน้า (`4, 6, 11-33, 35-40, 42-44` — เว้น 34, 41) ตัดมาจาก
> `json_แก้ไขแล้ว/11บ้าน_เล็ก_1ชั้น_06/` ที่รีวิว pattern จริงแล้ว (ครอบแค่หน้า 00-66,
> หน้า 67-137 ไม่มีข้อมูล) เพื่อ **ข้าม classify phase ไปเลยสำหรับบ้าน 11** (ประหยัดเวลา/เงิน)
> ดังนั้นตัวเลข 137 หน้าในตารางข้างบนคือหน้าดิบทั้งหมด **ไม่ใช่ขอบเขต extract จริง** — extract
> จริงมีแค่ 34 หน้า ไม่ต้องรัน `--phase classify` เลยสำหรับบ้านนี้

## ตัวเลขอ้างอิง (จาก local GGUF บ้าน 08, ไม่ใช่ของรอบนี้ — ใช้แค่กะสัดส่วนหน้าที่น่าจะผ่านกรอง)

จาก smoke-test บน local GGUF (เอกสารเดิม, บ้าน 08 ไม่ใช่บ้าน 11): classify 162-201s/หน้า
(แต่นั่นคือความเร็วบน laptop 8GB VRAM แบบ CPU offload บางส่วน — **บน GPU เช่า ≥80GB คาดว่าเร็ว
กว่ามาก ไม่รู้ตัวเลขจริงจนกว่าจะทดสอบ**) หน้า 1-3 ของบ้าน 08: title+site_plan / index /
schedule → มีแค่ 1/3 ผ่านกรอง — ให้ภาพคร่าวๆ ว่าสัดส่วนหน้าที่ผ่านกรองอาจไม่สูงมาก แต่ **ห้ามเดา
เวลารวมจากตัวเลข local หรือจากบ้านอื่น** เพราะฮาร์ดแวร์/ความเร็ว generate ต่างกันมาก และหน้าคละ
pattern ของบ้าน 11 ก็ไม่รู้จนกว่าจะ classify จริง — ต้องวัดใหม่บน GPU เช่าจริงกับบ้าน 11 เอง

---

## Phase 0 — Pre-flight (rule_of_tune ข้อ 4 — ต้องทำและตรวจจริงก่อนกดเช่า)

| # | รายการ | สถานะ |
|---|---|---|
| 1 | HF token มีสิทธิ์อ่าน `Sicilian44/qwen36-thai-rc` (private repo) — ทดสอบด้วย `curl -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/whoami-v2` **ก่อน**เช่าเครื่องจริง | 🔍 **ผ่านโดยพฤตินัย** — ไม่ได้รัน whoami-v2 แยก แต่ extract test จริง (2026-08-24 05:19-05:44) โหลด adapter `Sicilian44/qwen36-thai-rc/lora-adapter` สำเร็จ ("Fetching 7 files: 100%") แล้วรันจนจบ → สิทธิ์อ่านใช้ได้จริง |
| 2 | Vast.ai เครดิตพอ | 🔍 **เครื่องเช่าอยู่แล้วจริง** (instance C.48529261, 122.183.61.67) กำลังรันงานอยู่ — แปลว่ามีเครดิตพออย่างน้อยถึงตอนนี้ ยังไม่มีตัวเลขยอดคงเหลือที่แน่ชัด |
| 3 | Instance sizing — ใช้สเปกเดียวกับตอนทูน t01 (`t01_workflow.md` §0.5): **≥80GB VRAM** (RTX PRO 6000 96GB / A100 / H100 80GB), bf16 เต็ม ~74GB สำหรับโหลดโมเดล — inference อย่างเดียวไม่ต้องเผื่อ optimizer state เหมือนตอนเทรน แต่ยังไม่เคยวัด VRAM จริงตอน inference; disk **~150GB พอ** (ไม่มี GGUF/checkpoint กลางทางเหมือนตอน export, มีแค่โมเดล 70GB + adapter 7.5GB + ภาพ) | 🔍 ยืนยันแล้ว: instance จริงคือ RTX PRO 6000 Blackwell 96GB (nvidia-smi: 97887 MiB total) โหลดโมเดลได้ ไม่ OOM ระหว่าง extract 3 หน้า |
| 4 | สคริปต์ `run_house_batch_t01.py` เขียนแล้ว (พารามิเตอร์ตรงกับ `eval_fields.py`/`train_qwen36.py` ของ t01 เป๊ะ), syntax check ผ่าน (`python -m py_compile`) | 🔍 **รันบน GPU จริงแล้ว** — `--phase extract --variant tuned --houses 11 --limit 3` (2026-08-24 05:19-05:44): **3/3 หน้า JSON valid** (หน้า 4: 912s, หน้า 6: 486s, หน้า 11: 485s) ทดสอบสั้นผ่าน พร้อมปล่อยเต็ม |
| 5 | Scope: กี่บ้าน / รัน variant ไหนก่อน | ✅ **มะขามยืนยันแล้ว 2026-08-24: บ้าน 11 เดียว** (เปลี่ยนจาก 08/09/10 เดิม) รัน tuned+base ทั้งคู่ |
| 6 | เวลา/ค่าเช่ารวมจริง — ห้ามเดา ต้องวัดจาก `--limit` เล็กๆ ก่อนคูณเต็ม | 🔍 **วัดได้แล้วจากของจริง**: tuned variant เฉลี่ย **628s/หน้า (~10.5 นาที/หน้า)** จาก 3 ตัวอย่าง (912+486+485)/3 — แต่หน้าแรก (912s) รวมเวลาโหลดโมเดลด้วย ตัวเลขเฉลี่ยจริงน่าจะต่ำกว่านี้เมื่อรันยาว ⚠️ **PAGE_FILTER ของบ้าน 11 คือ 34 หน้า ไม่ใช่ 137** (ดูหมายเหตุด้านล่าง) → extract เต็ม 1 variant ≈ 34×~9-10 นาที ≈ **5-6 ชม.**, 2 variant (tuned+base) ≈ **10-12 ชม. รวม** — ไม่ต้องรัน classify แยกเลย (ข้ามไปตาม PAGE_FILTER) |

**ที่ผมทำต่อเองไม่ได้ในสองข้อนี้ (1, 2) เพราะเป็นของมะขามโดยตรง (token/2FA) — บอกผลมาแล้วผมรันต่อได้เลย**

---

## ✅ สรุปผลสุดท้าย (2026-08-24, จบรอบนี้)

**Scope จริงที่ทำสำเร็จทั้ง 2 variant: 6 หน้า** `[6, 20, 21, 22, 23, 24]` — pattern plan (06,20,21,22,37 ไม่ทัน) + section footing/beam detail บางส่วน (23,24)

**เหตุผลที่ scope เล็กกว่าที่วางแผนไว้ (12 หน้า):** หน้า25 (section, footing detail) **ค้างจริงทั้ง 2 รอบ** แม้เพิ่ม xgrammar + repetition_penalty แล้ว (รอบแรกไม่มี timeout ค้างเกิน 45 นาทีต้อง kill มือ; ใส่ `PAGE_TIMEOUT_S=25*60` (`_TimeLimit` StoppingCriteria) แล้วลองใหม่ ยังใกล้ชน timeout อีกรอบ) — มะขามสั่งตัดหน้าที่ t01 (tuned) ทำไม่สำเร็จออกจาก scope ทั้งคู่ ให้เทียบเฉพาะหน้าที่ทั้งสอง variant ทำสำเร็จจริงเท่านั้น (fair comparison)

**บทเรียนสำคัญ: grammar-constrained decoding แก้ "JSON ปิดไม่ได้" แต่ไม่แก้ "generate ยาวเกิน"** — หน้า section detail (รายละเอียดเหล็กเสริม/มิติเยอะ) ยังเสี่ยงกิน token ใกล้เพดาน `max_new_tokens=9000` ได้แม้มี grammar ต้องมี wall-clock timeout กันไว้ต่างหาก (เพิ่มแล้วในสคริปต์ `PAGE_TIMEOUT_S`)

**ตัวเลขเวลาจริงต่อหน้า (grammar+repetition_penalty เปิด, หลังหน้า22):**

| หน้า | tuned | base |
|---|---|---|
| 06 | 486s (ก่อน grammar) | 407s |
| 20 | 265s (ก่อน grammar) | 270s |
| 21 | 410s (ก่อน grammar) | 121s |
| 22 | 321s | 253s |
| 23 | 476s | 238s |
| 24 | 530s | 396s |

**สังเกต: base (untuned) เร็วกว่า tuned พอสมควรในหลายหน้า** (โดยเฉพาะหน้า21: 410s vs 121s) — คาดว่าเพราะ base ไม่ได้เขียนละเอียด/verbose (confidence_flags ยาวๆ, description อธิบายเหตุผล) แบบที่ t01 ถูกทูนให้ทำ ไม่ใช่ base "คิดเร็วกว่า" ในทางเทคนิค

**คุณภาพเนื้อหา (ตัวอย่างหน้า22 เทียบรูปจริง):** ทั้งคู่ผ่าน JSON valid แต่ **recall ต่ำมาก** — รูปจริงมีคานอย่างน้อย ~13 จุด + เสาหลายจุด (ชื่อแผ่น "แปลนเสา คาน พื้น" มีคำว่าเสาตรงๆ) ฝั่ง tuned หาเจอแค่ 5 รายการทั้งหมดเป็นคาน ไม่มีเสาเลย — ตรงกับปัญหา VLM counting hallucination ที่ไดอารี่ 22/8 บันทึกไว้ ยังไม่ได้เทียบ base อย่างละเอียด (ทำต่อได้)

**ไฟล์ผลลัพธ์ (ดึงกลับมาเครื่องตัวเองครบแล้ว, ตรวจ remote vs local ไฟล์ต่อไฟล์ 2026-08-24):**
- `tune_ai/t01/ผล_11/ผล/tuned/11บ้าน_เล็ก_1ชั้น_06/` — 8 ไฟล์ (04,06,11 จาก Phase 2 smoke-test + 20,21,22,23,24)
- `tune_ai/t01/ผล_11/ผล/base/11บ้าน_เล็ก_1ชั้น_06/` — 6 ไฟล์ (06,20,21,22,23,24)

**✅ Instance ปลอดภัยที่จะ destroy ได้** (Mark-of-Shame checklist ผ่านครบ: ยืนยัน remote vs local ไฟล์ตรงกันทุกไฟล์แล้ว ไม่มีผลลัพธ์ตกหล่น)

## Phase 1 — เช่าเครื่อง (ยังไม่ทำ)

สเปกเดียวกับ `t01_workflow.md` §0.5 / §1: GPU ≥80GB VRAM, disk ~150GB, template PyTorch+CUDA
ธรรมดา, ติดตั้ง unsloth/transformers/peft/accelerate/bitsandbytes/pillow ผ่าน onstart script

## Phase 2 — ทดสอบสั้นก่อนเสมอ (ยังไม่ทำ — ด่านเดียวที่กันเสียเงินทั้งก้อนถ้าอะไรพัง)

```bash
huggingface-cli login          # พิมพ์ token ตรงบน SSH session ห้ามส่งผ่านแชท
cd /workspace/tune
python3 run_house_batch_t01.py --phase classify --images-root /workspace/tune/image \
    --out-root /workspace/tune/ผล --houses 11 --limit 5
```
ดูให้ผ่านก่อนไปต่อ:
- `image processor: max=5242880 px (≈5120 visual tokens/ภาพ)` (ต้องเท่านี้ ตรงกับตอนเทรน)
- classify ออกมาเป็น pattern ที่สมเหตุสมผล ไม่ error
- จดเวลาเฉลี่ย/หน้า → คูณ 211 = เวลา classify รวมจริง → คูณราคา/ชม. เช่า = ค่าเช่า classify จริง

แล้วค่อยทดสอบ extract สั้นๆ ก่อนปล่อยเต็ม:
```bash
python3 run_house_batch_t01.py --phase extract --variant tuned \
    --images-root /workspace/tune/image --out-root /workspace/tune/ผล --houses 11 --limit 3
```

## Phase 3 — รันเต็ม (ยังไม่ทำ, resume-safe)

```bash
python3 run_house_batch_t01.py --phase classify --images-root /workspace/tune/image \
    --out-root /workspace/tune/ผล --houses 11
python3 run_house_batch_t01.py --phase extract --variant tuned \
    --images-root /workspace/tune/image --out-root /workspace/tune/ผล --houses 11
python3 run_house_batch_t01.py --phase extract --variant base \
    --images-root /workspace/tune/image --out-root /workspace/tune/ผล --houses 11
```

## Phase 4 — ดาวน์โหลดผลลัพธ์ + ⛔ คำเตือนก่อน destroy

```bash
# บนเครื่องตัวเอง
scp -r -P <port> root@<host>:/workspace/tune/ผล/ \
    "D:\00mk\steel project\training\Training\tune_ai\t01\ผล_11\"
```
ตรวจว่าจำนวนไฟล์ `.json` ในแต่ละโฟลเดอร์ + `_batch_summary.json` ครบบ้าน 11 × 2 variant
**ก่อน** destroy instance

> **⛔ ห้าม destroy instance จนกว่าจะยืนยันว่าไฟล์ผลลัพธ์ทั้งหมดอยู่บนเครื่องตัวเองแล้วจริง**
> — กฎเดียวกับที่ทำให้เกิด DAY OF SHAME (2026-07-21, ดู `rule_of_tune.md` § Mark of Shame)
> destroy ≠ stop, destroy ลบถาวรกู้คืนไม่ได้

## Phase 5 — (ทางเลือก) เทียบกับ ground truth

`json_แก้ไขแล้ว/0N<house>/` มีให้เทียบ แต่ **ยังไม่ผ่านรีวิวเนื้อหาสำหรับบ้าน 08/09/10** (ย้ำ) —
ยังไม่มีสคริปต์เทียบระดับ field ครบทุกหน้า (ต่างจาก `eval_fields.py` ที่เทียบแค่ 20 ตัวอย่างจาก
val.jsonl) รอสั่งถ้าต้องการ

---

## Scope — ตัดสินใจแล้ว 2026-08-24

**บ้าน 11 (`บ้าน_เล็ก_1ชั้น_06`, 137 หน้า) เดียว รัน tuned+base ทั้งคู่** — ไม่ใช่ 3 บ้าน 08/09/10
เดิมอีกแล้ว ยังต้องผ่าน Phase 2 (`--limit` เล็กๆ) ก่อนปล่อยเต็ม 137 หน้าเหมือนเดิม ตามหลัก
rule_of_tune ข้อ 4 — บ้านเดียวไม่ได้แปลว่าข้ามการวัดเวลาก่อนได้

---

## สรุปสิ่งที่เตรียมไว้แล้ว

- `data_before_tune/run_house_batch_t01.py` — เขียนแล้ว, syntax check ผ่าน, **ยังไม่เคยรันบน GPU**
- เอกสารนี้ — pre-flight ตาม rule_of_tune ข้อ 4
- เอกสารเดิม (`_local_workflow.md`) — เก็บไว้อ้างอิง (สถานะ superseded ไม่ใช่ path ที่ใช้แล้ว)

**บล็อกอยู่ตอนนี้ (รอมะขาม):** HF token ยืนยันสิทธิ์ (มะขามมี token แล้ว — รอผลทดสอบ
`whoami-v2` จากมะขาม), Vast.ai 2FA login เพื่อดูยอดเครดิต — scope ตัดสินใจแล้ว (บ้าน 11
เดียว) ครบสองข้อบนแล้วเช่าเครื่องได้เลย
