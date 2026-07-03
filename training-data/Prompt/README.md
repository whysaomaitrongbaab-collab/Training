# Prompt Library — Thai RC Drawing Pipeline

> ⚠️ อ่าน [../rule_of_tune.md](../rule_of_tune.md) ก่อนเริ่มงานทุกครั้ง — ไม่มีข้อยกเว้น

โฟลเดอร์นี้เก็บ prompt ทั้งหมดสำหรับ multi-model pipeline อ่านแบบโครงสร้าง RC ไทย

## โครงสร้าง Pipeline

```
PDF pages
    │
    ▼
[stage-a]  qwen-vl-plus   — จำแนกประเภทหน้า (router)
    │
    ├── floor_plan / section_detail / schedule_table ──▶ [stage-b1]  qwen-vl-max
    ├── general_notes ──────────────────────────────────▶ [stage-b2]  qwen-vl-plus
    └── table_of_contents / architectural / unknown ────▶ skip
```

## ไฟล์

| โฟลเดอร์ | Model | งาน | Prompt | Label Studio |
|---|---|---|---|---|
| `stage-a/` | qwen-vl-plus | จำแนกประเภทหน้า (router) | ✅ | ✅ พร้อม |
| `stage-b1/` | qwen-vl-max | ดึง element (section/schedule/floor_plan) | ✅ | 🔜 |
| `stage-b2/` | qwen-vl-plus | ดึง spec (วัสดุ/มาตรฐาน) จาก general_notes | ✅ | 🔜 |

> **Field ของ Stage B1/B2 ผูกกับ [js/shared/schema.js](../js/shared/schema.js)** (`createBeamLibraryEntry` + `createDrawingElement`) เพื่อให้ pipeline (BOQ/BBS) กินต่อได้ทันที

## การใช้งาน Label Studio

1. ใช้ `stage-a/label-studio-config.xml` เป็น Labeling Interface ใน Label Studio project
2. หลัง Qwen รัน Stage A → แปลง output เป็น tasks ด้วย script (ดู `stage-a/prompt.md`)
3. Import tasks JSON เข้า Label Studio → human ตรวจและแก้ไข
4. Export corrections → ใช้เป็น training data หรือ few-shot examples
