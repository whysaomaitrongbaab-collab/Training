# CLAUDE.md — training-data/

Context สำหรับ AI agent ที่มาทำงานต่อในโฟลเดอร์นี้ (portable — อาจอยู่ใน repo แยกจาก Constistant หลัก)

## นี่คืออะไร

Pipeline สร้าง **fine-tuning dataset** สำหรับโมเดล Qwen-VL ให้อ่านแบบก่อสร้าง RC (คอนกรีตเสริมเหล็ก) ของไทยได้แม่นขึ้น
Input: PDF แบบบ้าน (rasterize เป็น PNG ต่อหน้าไว้แล้ว) → Output: JSON structured data ต่อหน้า (element/dimension/rebar spec)
เป้าหมายปลายทาง: เก็บพอแล้วเอาไป fine-tune (ตอนนี้ยังอยู่ขั้น pre-labeling/dataset generation ไม่ใช่ training)

**Setup ก่อนรัน:** ดู [SETUP.md](SETUP.md) — ต้องมี `.env.local` (QWEN_API_KEY/HOST) และ `pip install -r requirements.txt`

## Architecture — 2 generation ของ logic (สำคัญ: ใช้ generation ล่าสุด)

### Generation ปัจจุบัน (ใช้จริง) — `run_pipeline.py` + `build_document_map.py`

```
Stage 0 (build_document_map.py) — อ่านหน้าสารบัญ (TOC) 1 ครั้ง
  → ได้ตาราง: sheet-code range (S-01..08, A-01..15, ...) + เลขหน้าใน doc ต่อ discipline
  → หา offset ระหว่าง "เลขหน้าที่สารบัญบอก" กับ "ไฟล์ PNG จริง" โดยอ่าน sheet_code จาก anchor page 1-2 หน้า
  → LOCK เป็น document map: ทุกหน้า PNG → discipline (structural/architectural/sanitary/electrical/...)
  → เขียนลง qwen-output/<house>/_document_map.json

Step 2 (run_pipeline.py) — ไล่ทุกหน้าตาม map:
  discipline == structural  → Stage B (unified extractor, 1 call/หน้า, model=qwen-vl-max)
                               อ่าน title-block sheet_name เอง → เลือก pattern (plan/schedule/section/notes)
                               → extract ตาม pattern นั้น
  discipline อื่น            → skip (ตอนนี้ scope = structural only)
```

**ทำไมต้อง Stage 0 ก่อน (อย่ากลับไป per-page classify ทุกหน้า):**
เคยลองให้ VLM classify ทีละหน้าจาก geometry (dimension line/hatching) — **หลอนหนัก** เช่น หน้าแบบขยายบันได (architectural ล้วน) VLM ยืนยัน "เห็น rebar dots" (มั่ว) แล้วจัดเป็น `section_detail` conf 0.95 — **confidence ของโมเดลใช้คัดกรองไม่ได้เลย** (ติดเพดาน ~0.95 ทั้งตอนถูกและผิด)

**สิ่งที่พิสูจน์แล้วว่าเชื่อถือได้แม้ตอน VLM หลอน:** มันอ่าน **sheet_code** จาก title block ถูกเสมอ (เช่น "A-11") แม้จะหลอนเรื่อง geometry ข้างๆ กัน → เปลี่ยนมาใช้ **สารบัญ + sheet-code เป็นตัวกำหนด discipline แบบ deterministic** แทนการให้ VLM เดา geometry เอง แก้ hallucination ได้เกือบหมด และประหยัด token กว่ามาก (2-3 call routing ทั้งเอกสาร แทน 61 call classify)

### Generation เก่ากว่า (fallback, ใช้เมื่อไม่มีสารบัญ) — `analyze_folder.py`
Per-page classify (Stage A) → route → extract (Stage B1/B2 แยกตาม sheet_type) เป็น pattern เดิมก่อนจะรู้ว่า sheet-code routing ดีกว่า **ยังอยู่ในโค้ดเผื่อเอกสารที่ไม่มีสารบัญ** แต่ควรใช้ `run_pipeline.py` เป็นค่าเริ่มต้นเสมอถ้ามีสารบัญ

## Layer สำรอง: PDF text layer (ยังไม่เคยเจอไฟล์ที่มีจริง)

ทั้ง 2 สคริปต์เช็ค PDF text layer ก่อน (ผ่าน PyMuPDF/`fitz`) — ถ้ามี text จะฉีดเป็น "grounding block" เข้า prompt (บอกโมเดลว่าตัวอักษร/รหัสให้เชื่อ text ไม่ต้องอ่านจากภาพ) แต่ **PDF ทุกไฟล์ที่เจอในโปรเจกต์นี้เป็น vector-outline (ตัวอักษรถูกวาดเป็นเส้น) → 0 text เสมอ** ดังนั้นกิ่งนี้ยัง**ไม่เคยถูกทดสอบจริง** ถ้าเจอ PDF ที่มี text layer จริง ให้ทดสอบกิ่งนี้ก่อนเชื่อผล

## บทเรียนสำคัญ (อย่าพลาดซ้ำ)

1. **VLM หลอน geometry แบบมั่นใจสูง** — dimension line + hatching อย่างเดียวไม่ใช่หลักฐานว่าเป็น structural (ดูหัวข้อ Architecture ด้านบน) ใช้ sheet-code/สารบัญตัดสิน ไม่ใช้ VLM geometry classify เป็นหลัก

2. **ตัวเลขเหล็กเส้นเล็กๆ อ่านผิดบ่อย** — ทดสอบจริงพบ Ø12 ถูกอ่านเป็น "DB23" (ไม่มีขนาดนี้ในมาตรฐานจริง — สัญญาณเตือนว่าเป็นค่าหลอน), stirrup Ø9 อ่านเป็น Ø6, dense stirrup zone (`@0.10 ช่วง 1.0m แรก`) มักถูกมองข้าม → **element_id/มิติหน้าตัด/จำนวนเหล็กหลัก มักถูก แต่ค่า spacing/ขนาดเหล็กปลอกละเอียดต้องให้คนตรวจก่อนเชื่อ**

3. **`confidence_score` จากโมเดลใช้ตัดสินเดี่ยวๆ ไม่ได้** — ต้องมี cross-check (sheet-code ตรงกับ TOC ไหม, self-consistency ถ้ายิงซ้ำ) หรือรอ human review เท่านั้น

4. **BOQ/schedule table ที่ไม่ใช่ rebar schedule ก็ยังมีตาราง** — เคยเจอหน้า BOQ (บัญชีปริมาณงาน) ถูกยัดเป็น `schedule_table` เพราะ VLM เห็นว่ามันเป็นตาราง ทั้งที่ไม่เกี่ยวกับโครงสร้างเลย → เหตุผลอีกข้อที่ต้อง route จากสารบัญ ไม่ใช่ให้ VLM เดาจาก geometry ของตาราง

5. **Model เลือกตาม task**: `qwen-vl-plus` ถูกกว่า ใช้กับ classify/สารบัญ/notes (ข้อความล้วน); `qwen-vl-max` แม่นกว่า ใช้เฉพาะ extraction ที่ต้องอ่าน geometry/ตัวเลขละเอียด (structural elements)

## สิ่งที่ยังไม่ได้ทำ (ทำต่อได้)

- **Label Studio review flow** — ยังไม่ได้ wire task/config จริง (มี draft prompt ไว้ที่ `Prompt/stage-a/label-studio-config.xml` แต่ยังอ้าง path รูปแบบเก่า ต้องเช็คก่อนใช้)
- **Confidence/trust scoring 3 ชั้น** (ออกแบบไว้ในบทสนทนา ยังไม่ implement เป็นโค้ด):
  - ชั้น 1: model confidence (ไม่น่าเชื่อถือเดี่ยวๆ ตามข้อ 3 ด้านบน)
  - ชั้น 2: human confidence จาก Label Studio — เก็บ `reviewer_level` (junior/mid/senior/expert) + `human_confidence` (sure/fairly/unsure)
  - ชั้น 3: trust weight รวม (expert+sure = gold/1.0 ... junior+unsure = escalate ให้ senior ตรวจซ้ำ, ไม่เอาเข้า training ตรงๆ)
- **Fine-tuning dataset export** (JSONL รวม image+prompt+ground-truth) — ยังไม่มีสคริปต์ประกอบจาก `qwen-output/` + reviewed data
- **Architectural extraction** — ตอนนี้ scope ล็อกเฉพาะ structural (ตามที่ตกลงกันไว้) ถ้าต้องการ floor_area จาก arch plan ต้องเพิ่ม pattern ใหม่

## Key files

| ไฟล์ | หน้าที่ |
|---|---|
| `run_pipeline.py` | **entry point หลัก** — Stage 0 → route → extract ทั้งโฟลเดอร์ |
| `build_document_map.py` | Stage 0 — อ่านสารบัญ, หา offset, สร้าง document map |
| `analyze_folder.py` | fallback per-page classify (ใช้เมื่อไม่มีสารบัญ) |
| `Prompt/stage-*/prompt.md` | เอกสารอ้างอิง prompt (source of truth จริงคือ string ในไฟล์ `.py`) |
| `qwen-output/<house>/` | ผลลัพธ์ — `_document_map.json`, `_run_summary.json`, `<house>_หน้าNN.json` |
| `SETUP.md` | วิธี setup ครั้งแรกใน repo ใหม่ |

## Convention

- ชื่อ output JSON = ชื่อไฟล์รูป 1:1 (แค่เปลี่ยนนามสกุล) — เปิดคู่กันได้ทันทีไม่ต้องพึ่ง manifest
- Field ของ element ผูกกับ schema ของ repo หลัก (`js/shared/schema.js` → `createBeamLibraryEntry`/`createDrawingElement`) เผื่อย้อนกลับไป wire เข้า pipeline หลักภายหลัง — ชื่อ field ควรตรงกันไว้แม้ repo นี้จะแยกออกมา
