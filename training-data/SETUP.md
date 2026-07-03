# training-data/ — Portable Setup

> ⚠️ อ่าน [rule_of_tune.md](rule_of_tune.md) ก่อนเริ่มงานทุกครั้ง — ไม่มีข้อยกเว้น

โฟลเดอร์นี้ **self-contained** — copy ทั้งโฟลเดอร์ไปวางใน repo ไหนก็รันได้ทันที
ไม่ต้องพึ่งไฟล์ใดๆ นอกโฟลเดอร์นี้ (schema.js, supabase.js ของ repo หลัก ฯลฯ ไม่เกี่ยวข้อง)

## Setup ครั้งแรก (repo ใหม่)

```bash
cd training-data
pip install -r requirements.txt

cp .env.local.example .env.local
# แก้ .env.local ใส่ QWEN_API_KEY + QWEN_API_HOST จริง (ดู Model Studio console)
# ⚠️ .env.local ไม่ถูก commit (อยู่ใน .gitignore) — ต้องสร้างเองทุก repo/เครื่องใหม่
```

## โครงสร้างที่ต้องมีคู่กันเสมอ

```
training-data/
├── .env.local.example      ← template (commit ได้)
├── .env.local               ← key จริง (สร้างเอง, gitignored, ห้าม commit)
├── requirements.txt
├── run_pipeline.py           ← entry point หลัก (Stage 0 → route → Stage B)
├── build_document_map.py     ← Stage 0: อ่านสารบัญ → document map
├── analyze_folder.py         ← per-page fallback (ไม่ผ่านสารบัญ, ใช้ตอนไม่มี TOC)
├── Prompt/                   ← prompt เนื้อหาเต็ม (reference — executable source of truth อยู่ใน .py)
│   ├── stage-a/prompt.md
│   ├── stage-b1/prompt.md
│   └── stage-b2/prompt.md
└── raw/image/<ชื่อบ้าน>/
    ├── <ชื่อบ้าน>.pdf              ← PDF ต้นฉบับ (ต้องมี — ใช้เช็ค text layer)
    └── <ชื่อบ้าน>_หน้าNN.png       ← รูปแต่ละหน้า (rasterized)
```

## วิธีใช้งาน

```bash
# 1 บ้าน ทั้งโฟลเดอร์ (auto: หาสารบัญที่หน้า 02, ใช้ anchor หน้า 20+40 หา offset)
python run_pipeline.py "raw/image/<ชื่อบ้าน>" --toc 02 --anchors 20,40

# ทดสอบหน้าเดียวก่อน (แนะนำก่อนรันทั้งชุด)
python run_pipeline.py "raw/image/<ชื่อบ้าน>" --only 20
```

**Output:** `raw/image/<ชื่อบ้าน>/qwen-output/`
- `_document_map.json` — routing ทั้งเอกสาร (Stage 0)
- `_run_summary.json` — สรุปผลรัน (extract/skip กี่หน้า, token รวม)
- `<ชื่อบ้าน>_หน้าNN.json` — ผล extraction ต่อหน้า (เฉพาะหน้า structural, ชื่อตรงรูป 1:1)

## ค่า config ที่ต้องปรับต่อชุดแบบ (ถ้าไม่ตรงตัวอย่าง)

- `--toc` — เลข PNG ของหน้าสารบัญ (ถ้าไม่ใช่หน้า 02)
- `--anchors` — เลขหน้าที่ใช้ตรวจ offset ระหว่างเลขหน้าสารบัญ กับไฟล์ PNG จริง (ต้องเป็นหน้าที่มี sheet code ชัดเจน)
- `PREFIX_DISCIPLINE` / `DISCIPLINE_ALIASES` ใน `build_document_map.py` — เพิ่ม sheet-code prefix ใหม่ได้ (extensible ตามที่ต่างบริษัทใช้รหัสต่างกัน)

## ความปลอดภัย

- **ห้าม commit `.env.local`** (มี API key จริง) — เช็คว่า `.gitignore` มี `.env.local` ก่อน push เสมอ
- ก่อน copy โฟลเดอร์นี้ไป repo อื่น **ลบ/ห้ามรวม `.env.local` ตัวจริงไปด้วย** ใช้ `.env.local.example` แทนเสมอ
