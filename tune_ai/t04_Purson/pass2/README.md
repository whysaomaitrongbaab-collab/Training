# Pass 2 — Qwen อ่านแบบจริง (แขนตัวคุม)

นี่คือแขน "2" (ไม่มี hint) ในการทดลอง A/B ของ [`pass2.4_hint/`](../pass2.4_hint/)

**ย้ายมาจาก `t03/pass2_used/` ครบทั้ง 10 subtask แล้ว (2026-08-29)** — แต่ละ subtask แยกโฟลเดอร์
ของตัวเอง มี `prompt_<subtask>.md` เต็มอยู่ข้างในทุกตัว (ชื่อไฟล์บอกเลยว่าเป็น prompt ของอะไร
กันสับสนตอนเปิดหลายแท็บ) ไม่มีไฟล์แบนแล้ว:

| โฟลเดอร์ | pattern จริง | ตัวอย่าง | สถานะ |
|---|---|---|---|
| [`gridline/`](gridline/) | `grid_master` | 40 | รอยิง GPU |
| [`plan_footing/`](plan_footing/) | `footing_plan`/`beam_plan`/`roof_frame_plan` | 100 | รอยิง GPU |
| [`plan_beam/`](plan_beam/) | `beam_plan`/`roof_frame_plan`/`footing_plan` | 125 | รอยิง GPU |
| [`plan_slab/`](plan_slab/) | `beam_plan` | 70 | รอยิง GPU |
| [`plan_column/`](plan_column/) | — | 0 | ตัน (ไม่มี config เทรน) |
| [`section/`](section/) | `section` | 438 | รอยิง GPU |
| [`schedule/`](schedule/) | `schedule` | 111 | รอยิง GPU |
| [`notes/`](notes/) | `notes` | 105 | รอยิง GPU |
| [`material_list/`](material_list/) | `material_list` | 0 | ยิงไม่ได้ (prompt ไม่ถูกโหลดเข้าชุดเทรน) |
| [`soil_boring_log/`](soil_boring_log/) | `soil_boring_log` | 0 | ยิงไม่ได้ (ไม่มีไฟล์ GT เลยสักหลัง) |

`plan_footing`/`plan_beam`/`plan_slab`/`plan_column` เคยเป็นไฟล์เดียว (`plan.md`, ตัดสินใจไว้
ว่า "หนึ่งไฟล์ ไม่ใช่สี่ก็อปปี้ที่ดริฟท์ได้") — ย้ายมาแตกเป็น 4 ไฟล์จริงแล้ว 2026-08-29
ตามมะขามสั่ง แต่ `plan.md` ยังอยู่ที่นี่เป็น **template ต้นฉบับ** สำหรับ re-render ใหม่ถ้ากฎ
ที่ใช้ร่วมกันต้องเปลี่ยน (ทุกไฟล์ลูกมีคอมเมนต์บอกไว้ว่าต้อง re-render จาก `plan.md` ไม่ใช่แก้ตรง)

`_common.md` ยังอยู่ที่ [`tune_ai/t03/_common.md`](../../t03/_common.md) (glossary ไทย, prepend
ทุก prompt) — ยังไม่ย้าย

รันโดย `tune_ai/t03/data_before_tune/infer_house_t03.py --arm 2` (ค่าปริยาย)
