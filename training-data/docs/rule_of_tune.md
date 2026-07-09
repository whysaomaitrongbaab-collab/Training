# กฎการแตะต้อง Raw JSON ของ Training Data

**ต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง** ในโฟลเดอร์ `training-data/` และ `raw_json_ตัวที่ใช้งานจริง/` (repo root) — ไม่มีข้อยกเว้น

## กฎข้อที่ 1 (สำคัญสูงสุด)

**ห้ามแก้ไข/เขียนทับ/ลบ raw JSON ของ raw data ก่อน tune เด็ดขาด** เว้นแต่จะได้รับอนุญาตจากผู้ใช้อย่างชัดเจนในบทสนทนานั้นๆ

**ขอบเขตของ "raw JSON ของ raw data"** (ไฟล์ที่กฎนี้คุ้มครอง):
- `raw/image/<house>/qwen-output/<house>_หน้าNN.json` — ผล extraction จริงจาก AI (ground truth ต้นทาง)
- `raw/image/<house>/qwen-output/_document_map.json`, `_run_summary.json`
- ไฟล์ใดๆ ที่เป็นผลลัพธ์ตรงจาก `run_pipeline.py` / `build_document_map.py` / `analyze_folder.py`
- **`raw_json_ตัวที่ใช้งานจริง/0N<house>/*.json`** (repo root, เพิ่ม 2026-07-10) — raw JSON ที่ Claude ถอดแบบเองโดยตรงจากภาพ (ground truth ต้นทางสำหรับ pattern ที่ automation ของ `run_pipeline.py` ยังไม่รองรับ เช่น `index`/`site_plan`/`side_profile`/`title`/`symbol`/`roof_plan`/`unknown` — ดูสเปคที่ `raw_json_ตัวที่ใช้งานจริง/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`) ได้รับการคุ้มครองเท่ากับ raw JSON จาก Qwen ทุกประการ แม้จะมาจากคนละกระบวนการ (Claude อ่านเองเทียบกับ Qwen-VL automated) ก็ตาม

**ไฟล์ที่ไม่เข้าข่ายกฎนี้** (แก้ไขได้ตามปกติ ไม่ต้องขออนุญาตพิเศษ):
- ไฟล์ที่ generate ขึ้นมาใหม่จาก raw data (เช่น `label-studio-tasks-*.json`) — เพราะรันซ้ำได้ ไม่กระทบต้นฉบับ
- ไฟล์ผลตรวจจากคน (`annotated/*.json`) — เป็นข้อมูลที่ตั้งใจให้แก้ไข/เขียนทับตามกระบวนการรีวิว
- Script, config, XML, เอกสาร .md

## กฎข้อที่ 2

**ก่อนจะขออนุญาตแก้ raw JSON ทุกครั้ง ต้องเตือนผู้ใช้ก่อนเสมอว่า:**
> การแก้ไฟล์นี้อาจส่งผลต่อความถูกต้องของข้อมูลที่จะใช้ fine-tuning โดยตรง (เป็น ground truth ต้นทาง)

ต้องเตือนแบบนี้ **ก่อน** ขออนุญาต ไม่ใช่ขอเงียบๆ แล้วค่อยบอกทีหลัง

**ขยายผล — ไม่ใช่แค่ raw JSON เท่านั้น: การกระทำใดๆ ที่ส่งผลต่อการทูนนิ่ง ต้องมีการเตือนเสมอ** แม้จะไม่ได้แก้ raw JSON โดยตรงก็ตาม เช่น:
- แก้ logic ของ script ที่ generate/flatten ข้อมูล (`label-studio-tasks-perpage.js`, `label-studio-import-repeater-annotations.js`) — เพราะเปลี่ยน field/type/schema ที่จะไหลเข้า `annotated/*.json` และ `dataset.jsonl` ในที่สุด
- เปลี่ยน field mapping, ตัด/เพิ่ม field ที่เก็บเป็น ground truth
- เปลี่ยนโครงสร้าง schema ที่ใช้ตอนประกอบ dataset
- การกระทำอื่นใดที่กระทบ "ข้อมูลที่จะกลายเป็นตัวอย่าง training" ไม่ว่าทางตรงหรือทางอ้อม

หลักการ: **ถ้าไม่แน่ใจว่ากระทบทูนนิ่งหรือไม่ ให้ถือว่ากระทบไว้ก่อน แล้วเตือน** ดีกว่าเดาว่าไม่กระทบแล้วไม่เตือน

**ข้อยกเว้นของกฎข้อ 2 — แหกได้ตามความเหมาะสม:** ไม่ต้องเตือนซ้ำทุกครั้งถ้าเข้าเงื่อนไขทั้งหมดนี้:
- เป็นการกระทำที่**เคยเตือนและได้รับอนุญาตแล้ว**ใน scope เดียวกันมาก่อนในบทสนทนานั้น (ไม่ต้องเตือนซ้ำทุกรอบที่ทำตามที่ตกลงไว้แล้ว)
- เป็นการ**รันซ้ำ** script/กระบวนการเดิมที่ไม่เปลี่ยน logic (เช่น regenerate task JSON จาก raw data ตัวเดิม โดย script เดิมที่ verify แล้วว่าไม่กระทบ type/schema)
- เป็น dry-run / รันแบบทดสอบที่**เขียนลงไฟล์ทดสอบชั่วคราวแล้วลบทิ้งทันที** ไม่ปล่อยให้ปนกับ `annotated/`/`manifest.json` จริง

ถ้าไม่เข้าเงื่อนไขข้างบนแม้แต่ข้อเดียว **กลับไปใช้กฎข้อ 2 เต็มรูปแบบ** (เตือนก่อนเสมอ)

## พฤติกรรมที่ควรเลี่ยง (บทเรียนจากงานจริงในโปรเจกต์นี้)

1. **อย่าลองกลไกที่ไม่เคย verify กับข้อมูลจริงทั้งชุดทีเดียว** — ทดสอบกับตัวอย่างเล็กๆ (1 task/1 record) ก่อนเสมอ (บทเรียนจาก: ลองใส่ `predictions` ให้ Choices ใน Repeater โดยไม่ทดสอบเล็กก่อน ผลคือ import พังทั้ง 71 task รวด)

2. **อย่าทิ้งข้อมูลทดสอบ (fake/dry-run data) ไว้ใน `annotated/` หรือ `manifest.json`** โดยไม่ล้างทันทีหลังทดสอบเสร็จ — ต้องลบไฟล์ทดสอบและ revert `manifest.json` กลับสภาพเดิมก่อนจบงานเสมอ ห้ามปล่อยให้ผู้ใช้ต้องมาเตือนเอง

3. **เวลาลดความซับซ้อนของ field/config (simplify) ต้อง audit รายการ field ก่อน-หลังให้ครบ** ห้ามให้ field หายไปเงียบๆ ระหว่างทำ (บทเรียนจาก: ตัด `confidence_flags`, `material_amount`, `labor_amount` หายไปจากหน้าจอตอนย่อ v2→v3 โดยไม่ได้ตั้งใจ ผู้ใช้ต้องเช็คจับได้เอง)

4. **ห้ามพูดมั่นใจเกินจริงในสิ่งที่ยังไม่ได้ verify** (เช่น syntax ของเครื่องมือภายนอกที่ดึงเอกสารมาเช็คไม่สำเร็จ) — ต้องบอกระดับความมั่นใจตามจริง และเสนอวิธี verify (เช่น ทดสอบใน Preview ก่อน) แทนการเดาแล้วนิ่งเงียบ

5. **field ที่เป็นตัวเลข/array ต้องเช็ค type ให้ตรงกับ raw data เสมอ** ก่อนเขียนเป็นไฟล์ที่จะใช้จริง (ดูตาราง type ด้านล่าง) — ห้ามปล่อยให้ number กลายเป็น string หรือ array กลายเป็น string โดยไม่ตั้งใจ

6. **กฎข้อ 2 (ต้องเตือนก่อน) ครอบคลุมไปถึง state ในระบบภายนอกด้วย ไม่ใช่แค่ไฟล์ในเครื่อง** — เช่น task/annotation ที่เก็บอยู่ใน Label Studio Cloud (คนละระบบกับไฟล์ raw JSON ใน repo แต่ก็ยังเป็น "ข้อมูล" ที่อาจมีของจริงอยู่ข้างใน) บทเรียนจาก: เสนอ "ลบ task ทั้งหมดใน Data Manager" เป็นขั้นตอนแก้ error โดยไม่เตือนก่อนว่าอาจมีข้อมูลรีวิวจริงอยู่ข้างใน — ต้องเตือนและถามก่อนเสมอว่ามีของจริงอยู่ในนั้นไหม ก่อนเสนอให้ลบ

## กฎข้อที่ 3

ถ้าจำเป็นต้องแก้ raw JSON จริง (เช่น รัน pipeline ใหม่ทับของเดิม, แก้ค่าที่ผิดมือ, extract ใหม่ด้วย AI ตัวอื่นทับของเดิม) และได้รับอนุญาตแล้ว:
- สำรอง/เช็ค git status ก่อนแก้เสมอ (ให้กู้คืนได้ถ้าพลาด)
- **ทุกการแก้ไข ต้องบันทึกใน `raw_json_data_log.md` ของ repo `Training` เท่านั้น** (`training-data/raw_json_data_log.md` ใน repo `Training` — ไม่ใช่สำเนาใน repo `Constistant` แม้จะมี `rule_of_tune.md` อยู่ทั้ง 2 ที่ก็ตาม) เพิ่มแถวก่อนหรือพร้อมกับการแก้ทุกครั้ง ห้ามแก้แล้วไม่บันทึก (บันทึก: ไฟล์ที่แก้, AI ที่ใช้ทำ, ผู้แก้ไข/ผู้อนุมัติ, หมายเหตุ)
- บันทึกใน `CLAUDE.md` ว่าแก้อะไร ทำไม เมื่อไหร่ (สรุประดับภาพรวม — ส่วน `raw_json_data_log.md` คือ audit trail ระดับไฟล์ต่อไฟล์)

## ลำดับความสำคัญ (แบบกฎอาซิมอฟ)

กฎข้อ 1 มาก่อนข้อ 2 และ 3 เสมอ — ต่อให้ผู้ใช้สั่งให้แก้ raw JSON ตรงๆ ก็ต้องทำตามข้อ 2 (เตือนก่อน) ให้ครบก่อนจะลงมือ จะข้ามขั้นตอนเตือนไปเลยไม่ได้ แม้ผู้ใช้จะรีบก็ตาม

**กฎข้อ 2 (การเตือน) ใช้แม้ในกรณีที่ไม่เข้าข่ายกฎข้อ 1** — คือแม้ไฟล์ที่จะแก้ "ไม่ใช่" raw JSON ต้นทาง (เช่น แก้ script generate task) แต่ถ้าผลลัพธ์สุดท้ายกระทบข้อมูลที่จะเข้า fine-tuning ก็ต้องเตือนอยู่ดี

---

## บันทึก: Format JSON ที่ใช้ทูนจริง (ground truth schema)

นี่คือ format ล่าสุด (2026-07-02) ที่ `label-studio-import-repeater-annotations.js` เขียนออกมาเป็น `annotated/<record_id>-<type>-annotated.json` — **ผ่านการทดสอบ round-trip แล้วว่า type ถูกต้องตรงกับ raw JSON ต้นทาง** (ดูหัวข้อ "Label Studio Cloud — King's per-page Repeater review flow" ใน `CLAUDE.md` สำหรับที่มา) ถ้าจะแก้ schema นี้ ต้องทำตามกฎข้อ 2 ด้านบนก่อน (เตือนก่อนแก้)

### Structural (`plan`/`section`/`schedule`)

```json
{
  "record_id": "บ้าน_เล็ก_1ชั้น_01_page19",
  "house": "บ้าน_เล็ก_1ชั้น_01",
  "page": "19",
  "review_status": "approved",
  "reviewer_note": "",
  "annotation_date": "2026-07-02T11:37:13.027Z",
  "sheet_code": "S-02",
  "sheet_name": "แปลนฐานรากและฐานรากเสาเข็ม",
  "plan": [
    {
      "element_id": "F1,C1",
      "element_type": "footing",
      "count": 9,
      "grid_refs": ["A-1", "A-2", "A-3"],
      "span_length_m": 4,
      "main_bar_dia_mm": null,
      "stirrup_dia_mm": null,
      "stirrup_spacing_mm": null,
      "width_mm": null,
      "height_mm": null,
      "main_bar_count": null,
      "main_bar_type": "",
      "stirrup_type": "",
      "concrete_grade": "",
      "steel_grade": "",
      "confidence_score": 0.8,
      "confidence_flags": []
    }
  ],
  "section": [
    {
      "element_id": "B1",
      "element_type": "beam",
      "width_mm": 150,
      "height_mm": 300,
      "main_bar_count": 2,
      "main_bar_dia_mm": 23,
      "main_bar_type": "DB",
      "stirrup_dia_mm": 6,
      "stirrup_type": "RB",
      "stirrup_spacing_mm": 150,
      "concrete_grade": "fc240",
      "steel_grade": "SD40",
      "confidence_score": 0.9,
      "confidence_flags": [],
      "count": null,
      "grid_refs": [],
      "span_length_m": null
    }
  ],
  "schedule": []
}
```

### BOQ (`categories[].items[]`)

```json
{
  "record_id": "บ้าน_เล็ก_1ชั้น_01_page38",
  "house": "บ้าน_เล็ก_1ชั้น_01",
  "page": "38",
  "review_status": "approved",
  "reviewer_note": "",
  "annotation_date": "2026-07-02T11:37:13.027Z",
  "sheet_no": "2/19",
  "categories": [
    {
      "category": "หมวดงานโครงสร้าง",
      "items": [
        {
          "item_no": "1",
          "description": "- ขุดดิน",
          "quantity": 27,
          "unit": "ลบ.ม.",
          "material_unit_price": null,
          "material_amount": null,
          "labor_unit_price": null,
          "labor_amount": null,
          "total_amount": null,
          "confidence_score": 0.98,
          "confidence_flags": []
        }
      ]
    }
  ]
}
```

### กฎเรื่อง type (ผิดพลาดง่ายสุด — เคยพังมาแล้วรอบหนึ่ง)

| Field | Type ที่ถูกต้อง | หมายเหตุ |
|---|---|---|
| `count`, `span_length_m`, `width_mm`, `height_mm`, `main_bar_count`, `main_bar_dia_mm`, `stirrup_dia_mm`, `stirrup_spacing_mm`, `confidence_score` (structural) | **number** (หรือ `null` ถ้าไม่มีข้อมูล) | ห้ามเป็น string เช่น `"9"` — เคยเกิดบั๊กเพราะ Label Studio ต้องการ string ตอนแสดงผล แต่ก่อนเขียนเป็น ground truth ต้องแปลงกลับเป็น number เสมอ |
| `quantity`, `material_unit_price`, `material_amount`, `labor_unit_price`, `labor_amount`, `total_amount`, `confidence_score` (boq) | **number** (หรือ `null`) | เหมือนข้างบน |
| `grid_refs`, `confidence_flags` | **array of string** | เคยถูก join เป็น comma-string ตอนแสดงผลใน Label Studio ต้อง split กลับเป็น array ก่อนเขียนเป็น ground truth |
| `element_id`, `element_type`, `main_bar_type`, `stirrup_type`, `concrete_grade`, `steel_grade`, `description`, `unit`, `category`, `item_no` | **string** | ปกติ ไม่ต้องแปลง |

**หลักการทั่วไป:** JSON ที่จะใช้ทูนจริงต้อง**ตรง type กับ raw JSON ต้นทางเป๊ะ** (ดูตัวอย่างจริงได้ที่ `raw/image/<house>/qwen-output/<house>_หน้าNN.json`) ห้ามมี field ไหนเป็น string ทั้งที่ควรเป็น number/array หรือกลับกัน
