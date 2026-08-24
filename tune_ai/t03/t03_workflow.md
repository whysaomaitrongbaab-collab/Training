# t03 workflow — per-subtask multi-pass fine-tune

> ## 🟡 นี่คือเอกสารของ **รอบ t03** — ยังไม่จบ (เตรียมข้อมูลเสร็จ ยังไม่ได้เทรน)
>
> | | |
> |---|---|
> | รอบ | **t03** |
> | โมเดล | ⬜ **มะขามยังไม่เลือก** (ดู Phase 0 ข้อ 1 — default ที่เสนอ: `unsloth/Qwen3-VL-30B-A3B-Instruct` ตัวเดียวกับ t02 เพราะ infra พิสูจน์แล้ว) |
> | โฟลเดอร์ข้อมูล | `tune_ai/t03/data_before_tune/` |
> | สถานะ | dataset สร้างแล้ว 452 ตัวอย่าง (2026-08-24) — รอเลือกโมเดล+เช่าเครื่อง |
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

## Dataset — สร้างแล้ว 2026-08-24 (Claude ภายใต้ att1235 ระหว่างมะขามไม่อยู่)

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
| 1 | **เลือกโมเดล** — เสนอ `unsloth/Qwen3-VL-30B-A3B-Instruct` (t02 เดิม: infra/script/collator fix พิสูจน์แล้ว, แค่เปลี่ยน data) ทางเลือก: Qwen3.6-35B-A3B (t01) แต่ MoE ตัวนั้นเทรนช้ากว่าและ export GGUF เจ็บมาแล้ว | ⬜ **มะขามตัดสิน** |
| 2 | dataset พร้อม (452 ตัวอย่าง + ภาพ 353 + manifest) | 🔍 |
| 3 | สคริปต์เทรน — **ยังไม่ได้เขียน/แก้จาก t02** (`t02/data_before_tune/train_qwen3vl.py` เป็นฐาน: ต้องเช็ค MAX_LENGTH กับ prompt ใหม่ที่ยาว ~12k chars/ตัวอย่าง + gridmaster text + ภาพ 5120 tokens — ยาวกว่ารอบ t02 มาก **ต้องคำนวณ token จริงก่อนตั้ง MAX_LENGTH** อย่าเดา (บทเรียน t01 §0.4 MAX_LENGTH bug)) | ⬜ |
| 4 | Parity table ต่อจาก rule_of_tune ข้อ 12 — enumerate ทุก argument ของ collator/SFTConfig เทียบ t02 รวมค่า default (บทเรียน 14x visual-token bug) | ⬜ |
| 5 | HF token ใช้ได้ (เพิ่งใช้เช้านี้กับงาน t01-vs-base สำเร็จ — ต้องเช็คซ้ำวันเทรนจริง) | 🔍 |
| 6 | Vast.ai เครดิต — เช็ค dashboard จริงวันเทรน **และเช็คบิลของ instance เมื่อเช้าด้วย** (ราคาโชว์ $0.056/hr มีประวัติผิด 30 เท่า — diary 2026-08-20) | ⬜ |
| 7 | ทดสอบสั้น (`TEST_STEPS=5`) ก่อนรันเต็มเสมอ | ⬜ |

## Phase 1+ (หลัง Phase 0 ครบ — โครงตาม t02_workflow.md)

เช่าเครื่อง ≥80GB VRAM → upload `data_before_tune/` → verify env → short test → full train →
eval per-subtask (ต้องเขียน eval ใหม่: `eval_fields.py` เดิมเทียบทั้งหน้า แต่ t03 ต้องเทียบ
ต่อ subtask — ยังไม่ได้เขียน ⬜) → backup ขึ้น HF ก่อนคิดเรื่อง destroy (Mark-of-Shame)

## สิ่งที่ Makham ต้องตัดสินใจก่อนเริ่มเทรนคืนนี้

1. **โมเดล** (Phase 0 ข้อ 1)
2. **ยอมรับ/แก้การตัดสินใจ dataset ทั้ง 4 ข้อ** ข้างบน (โดยเฉพาะ plan_column ยุบ — ตรงกับที่
   `dataset_sizing.md` ชง แต่ยังไม่เคยเคาะ)
3. **gridline subtask แบบ multi-image** — open question ใน README (single AI call หลายภาพ →
   gridmaster ตรงๆ vs per-file แล้ว merge ด้วยโค้ด) dataset ตอนนี้เตรียมตามแบบแรก
4. รวมบ้าน 06-11 ที่ยังไม่รีวิวเนื้อหาใน train ต่อไหม (ตอนนี้รวมตามคำสั่ง "ทำบ้านทุกบ้าน")
