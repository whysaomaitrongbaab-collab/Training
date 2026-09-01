# t05 Courser (Destrier) — แผนที่โฟลเดอร์นี้

ไฟล์ .py/.sh/.jsonl ในนี้ **ไม่ย้ายเข้าโฟลเดอร์ย่อย** เพราะสคริปต์ทุกตัวอ้างชื่อไฟล์ตรงๆ
(ผ่านตัวแปร `HERE`/`COURSER_DIR`/`DATA_DIR`) และ `onstart.sh` สั่งอัปโหลด "ทั้งโฟลเดอร์"
ขึ้นการ์ดจอเช่าตรงๆ — ย้ายแล้วเสี่ยงพังตอนรันจริงบนเครื่องเช่า (เสียเงินจริงถ้าพลาด)
เอกสารนี้จึงทำหน้าที่เป็น "แผนที่" อ่านแทน — ไล่ตามลำดับที่งานจริงไหลผ่าน

## ลำดับสายงาน (pass0 → เทรนจริง)

1. **`pass0_derive.py`** → อ่านข้อมูลดิบ สร้าง `pass0_labels.jsonl` (auto) + `pass0_manual_queue.jsonl` (ต้อง label มือ)
2. **`pass0_material_list_batch.py`** → ประมวลผลคิว label มือ อัปเดตกลับเข้า `pass0_labels.jsonl`
3. **`build_t05_night.py`** → รวม labels เป็น split เทรน/val ของแต่ละ pass:
   - `pass0_train.jsonl` / `pass0_val.jsonl`
   - `pass24_train.jsonl` / `pass24_val.jsonl` (pass 2.4)
   - `pass3_train.jsonl` / `pass3_val.jsonl` (ใช้ `pass3_pairs_eyeball.jsonl` — คู่ที่คนตรวจแล้ว)
4. **`build_4pass.py`** → รวม 4 pass เป็นชุดสุดท้าย **k-fold 4 ส่วน** (ไฟล์ใหญ่สุดในนี้):
   - `train_fold0-3.jsonl` / `val_fold0-3.jsonl` ← **นี่คือข้อมูลเทรนจริง**
5. **`smoke_4pass.py`** → เช็ค fold ไม่รั่ว/ไม่ซ้ำ ก่อนเสียเงินเช่าการ์ดจอ
6. **`train_t05_courser.py`** → เทรนจริงบนการ์ดจอเช่า (รันทีละ fold ผ่าน `onstart.sh`) → push ขึ้น HF
7. **`audit_inline.py`** → ตรวจคุณภาพ/ความสอดคล้องของ pass0/pass24/pass3 jsonl ย้อนหลัง

## สคริปต์ที่รันบนเครื่องเช่า (remote เท่านั้น — path ฝัง `/workspace/...` ตรงๆ)

- `worker_page.py`, `worker_page_raw_pratyad.py` — ยิงทดสอบทีละหน้าบนโมเดลที่เพิ่งเทรน
- `smoke_destrier.py` — smoke test เร็วๆ ก่อนเชื่อมเข้า worker จริง
- `run_queue.sh` / `run_queue_elements.sh` / `run_queue_gpuA.sh` — ตัวรันคิวงานจริงบน GPU

## เครื่องมือช่วยตรวจ (ใช้มือ ไม่ใช่ pipeline)

- **`gtq.py`** — ดูคำตอบจริง (ground truth) + ผล CV ของบ้าน/หน้าไหนก็ได้: `python gtq.py <ชื่อบ้าน> <เลขหน้า>`
- `run_cv_batch.py` — รัน CV pre-scan เป็นชุด (log อยู่ที่ `logs_final/cv_prescan_batch.log`)

## โฟลเดอร์ผลลัพธ์ที่จัดไว้แล้ว

- `logs_final/` — log การเทรนจริงทุก fold + push ขึ้น HF + CV pre-scan
- `marked_t5/` — รูปที่มาร์กไว้ (23 ไฟล์) สำหรับตรวจ pass 1.5 ด้วยตา
- `destrier_test_house/results/` — ผลทดสอบ Destrier ทุกรอบ จัดเรียงลำดับ + มี README ของตัวเอง

## เอกสารตัวเต็ม

- `t05_workflow.md` — บันทึกละเอียดทุกขั้นตอน/บั๊ก/การตัดสินใจของงาน t05 ทั้งหมด (ไฟล์นี้เป็นแค่แผนที่ย่อ ไม่ใช่ตัวแทน)
