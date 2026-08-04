# สรุป: Repo `Training` คืออะไร และ Match กับงานหลัก Constistant แค่ไหน

## Repo นี้ (`Training`) ทำอะไร

เป็น **workspace สร้าง fine-tuning dataset** ให้โมเดล vision (Qwen-VL) อ่านแบบก่อสร้าง RC (คอนกรีตเสริมเหล็ก) ของไทยได้แม่นขึ้น — ไม่ใช่ตัวแอปโปรดักชัน แต่เป็น "โรงงานเตรียมข้อมูล" ที่ป้อนผลลัพธ์กลับไปหนุนฟีเจอร์ Drawing Intelligence ของ Constistant

Pipeline หลัก: **PDF แบบบ้าน → rasterize เป็น PNG ต่อหน้า → Qwen-VL อ่าน/สกัดข้อมูล → มนุษย์ตรวจ/แก้ผ่าน Label Studio → dataset พร้อม fine-tune**

โฟลเดอร์สำคัญ:
| โฟลเดอร์ | หน้าที่ |
|---|---|
| `training-data/` | โค้ด pipeline หลัก (`run_pipeline.py`, `build_document_map.py`) + doc ละเอียด (`CLAUDE.md`, `README.md`) |
| `image/`, `raw_json_ตัวที่ใช้งานจริง/` | รูปแบบบ้านที่ rasterize แล้ว + ผลลัพธ์ JSON ดิบจาก Qwen ต่อบ้าน/ต่อหน้า |
| `json_แก้ไขแล้ว/` | JSON ที่ผ่านการแก้ไข/ตรวจแล้ว พร้อมใช้เป็น ground truth |
| `tune_ai/` | ข้อมูลที่จัดชุดพร้อม fine-tune จริง |
| `workmen's_diary/` | log รายวันแบบมนุษย์อ่าน ครอบคลุมงานทั้งฝั่ง `Training` และ `Constistant` (ย้ายมารวมที่นี่เพราะ entry ส่วนใหญ่ข้ามสองรีโปกัน) |
| `Contistant work/` | สำเนา `CLAUDE.md`/`AGENTS.md` ของรีโปหลัก Constistant ไว้อ้างอิง (ไม่ใช่โค้ดจริง) |

สถานะปัจจุบัน (ตาม `training-data/CLAUDE.md`, อัปเดตล่าสุด 2026-07-06 ถึง 07-07):
- Extraction เสร็จแล้ว 5/9 บ้าน (กลุ่ม "บ้านเล็ก" ทั้งหมด), เหลือ "บ้านใหญ่" 4 หลัง
- Scope ล็อกเฉพาะ **structural elements** เท่านั้น (ยังไม่แตะ architectural/sanitary/electrical)
- Review flow ผ่าน Label Studio Cloud มี 3 รุ่นขนานกัน (whole-JSON ต่อบ้าน, per-page Repeater, "Makham's Pattern" Gen 3) — ยังไม่มีรุ่นไหน publish ให้คนจริงตรวจ
- Fine-tuning dataset export (JSONL รวม image+prompt+ground-truth) — ยังไม่มีสคริปต์

## งานหลัก Constistant คืออะไร (จาก `Contistant work/CLAUDE.md`)

**"Constistant" (Steel Calc)** — เว็บแอป static ไม่มี build step สำหรับทีมก่อสร้างไทย ทำ 3 อย่างหลัก:
1. **Rebar cut-list optimization (CSP)** — BBS (Bar Bending Schedule)
2. **AI-driven drawing/quantity-takeoff scanning** — "Drawing Intelligence" อ่านแบบก่อสร้างแล้วสกัด BOQ/rebar อัตโนมัติ ผ่าน **Qwen-VL-Max** (server-side ผ่าน Supabase Edge Function)
3. **Project save/load** ผ่าน Supabase

โมดูลอื่นที่ต่อยอด: Planner (Gantt/EVM/critical path), Resource Hub, Readiness Check, BOQ export, Material pricing — ทำงานบน pipeline เดียว `runPipeline()`: BOQ → BBS → schedule → resources → readiness

## จุด Match

**Match ตรงจุดสำคัญที่สุดคือ: โมเดลตัวเดียวกัน — Qwen-VL** ที่ `Training` กำลัง fine-tune คือโมเดลเดียวกับที่ `js/ai/qwenVision.js` + `supabase/functions/qwen-vision/` ใน Constistant เรียกใช้จริงตอนสแกนแบบก่อสร้าง (Drawing Intelligence)

| มิติ | Training | Constistant |
|---|---|---|
| เป้าหมาย | เตรียม dataset ป้อน fine-tune | ใช้โมเดล (ที่ fine-tune แล้ว) สแกนแบบจริงหน้างาน |
| Input | PDF แบบบ้านตัวอย่าง | PDF/รูปที่ลูกทีมอัปโหลดจริง |
| Output | JSON ที่ผ่านมนุษย์ตรวจ (ground truth) | JSON ที่ AI สกัด → ใส่ BOQ/BBS ทันที |
| Element type ที่ครอบคลุม | structural เท่านั้น (footing/column/beam/slab + rebar spec) | ต้องการ structural + BOQ (บางส่วนถึง architectural ในอนาคต) |
| Schema | มี "Makham's Pattern" ของตัวเอง แต่ `training-data/CLAUDE.md` ระบุชัดว่า **field ผูกกับ `js/shared/schema.js`** (`createBeamLibraryEntry`/`createDrawingElement`) เพื่อ "เผื่อย้อนกลับไป wire เข้า pipeline หลักภายหลัง" | `js/shared/schema.js` เป็น single source of truth ของทุก entity |

**สรุป: Match สูงในระดับเป้าหมาย/โมเดล/schema** — `Training` repo ถูกออกแบบมาโดยตั้งใจให้เป็นสายพานป้อนคุณภาพให้ Drawing Intelligence ของ Constistant โดยเฉพาะ ไม่ใช่โปรเจกต์คู่ขนานที่แยกทิศทางกัน

## จุดที่ยังไม่ Match / ยังไม่เชื่อมกันจริง

1. **ยังไม่มี wiring จริง** — ไม่มีสคริปต์ export dataset เป็น JSONL, ไม่มี fine-tuning job รันจริง, โมเดลที่ Constistant เรียกใช้ตอนนี้ยัง**ไม่ใช่**เวอร์ชัน fine-tuned จาก dataset นี้ (คำว่า "Next Steps (Fine-tuning)" ใน `training-data/README.md` ยังเป็นแผน ไม่ใช่ของที่ทำแล้ว)
2. **Scope แคบกว่า** — Training ล็อก structural เท่านั้น แต่ Constistant ต้องการ BOQ/quantity-takeoff ที่กว้างกว่านั้น (มี BOQ pattern อยู่ใน schema เก่าแต่ scope ปัจจุบันไม่ทำ)
3. **Schema drift เสี่ยง** — Gen 3 "Makham's Pattern" ปรับ schema เองหลายรอบ (`views[]`, `span_source`, ฯลฯ) โดยยังไม่ยืนยันว่าตรงกับ `createDrawingElement` ของ Constistant เป๊ะ — ต้องเช็ค sync ก่อนเอาไป wire จริง
4. **Human review ยังไม่เดินหน้า** — 3 Label Studio flow ทำไว้แต่ยังไม่ publish/เชิญคนตรวจจริง คอขวดอยู่ตรงนี้ก่อนจะมี ground truth พอ fine-tune

## ข้อสังเกตเพิ่ม

- `Contistant work/AGENTS.md` ในรีโปนี้เป็นแนวทางสไตล์โค้ด ("Ponytail, lazy senior dev mode" — YAGNI, ไม่สร้าง abstraction เกินจำเป็น) ไม่ใช่เอกสารสถาปัตยกรรมของโปรเจกต์ — ส่วนที่ match/ไม่ match ด้านบนอิงจาก `CLAUDE.md` เท่านั้น
- ทั้งสอง repo แชร์ `workmen's_diary/` ร่วมกัน (ย้ายมาไว้ที่ `Training` เพราะ entry ส่วนใหญ่ข้ามสองฝั่ง) — เป็นสัญญาณว่าทีมมองสองรีโปเป็นงานเดียวกันในทางปฏิบัติ แม้ code แยกกันคนละที่
