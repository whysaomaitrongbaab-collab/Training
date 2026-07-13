# Primary Raw JSON Schema — Edit Log

บันทึกทุกครั้งที่มีการแก้ไข [`00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`](00file_for_making_rawjson_from_claude/primary_rawjson_schema.md) — คู่กับ [`training-data/docs/raw_json_data_log.md`](../training-data/docs/raw_json_data_log.md) ที่บันทึกการแก้ไข raw JSON ข้อมูลบ้านแต่ละหลัง (ไฟล์นี้บันทึกเฉพาะการแก้ตัวสเปคเอง)

ตาม `rule_of_tune.md` กฎข้อ 7 — `primary_rawjson_schema.md` เป็นเอกสาร .md ไม่เข้าข่ายกฎข้อ 1 (แก้ได้โดยไม่ต้องขออนุญาต) แต่ทุกการแก้ต้องอ้างอิงกฎนี้และจดไว้ที่นี่เสมอ ห้ามแก้แล้วไม่บันทึก

## รายการแก้ไข

| วันที่ | หัวข้อที่แก้ | AI ที่ใช้ทำ | ผู้แก้ไข/อนุมัติ | หมายเหตุ |
|---|---|---|---|---|
| 2026-07-13 | เพิ่ม section 13 "`site_plan` — `element_type` not standardized across houses" | Claude (Sonnet 5, Claude Code) — สำรวจไฟล์ site_plan ทั้ง 5 บ้านใน `raw_json_ตัวที่ใช้งานจริง/` | มะขาม (สั่งให้เพิ่มหลังถามว่า element_type มีกี่ประเภท) | รวบรวม element_type 10 ค่าที่ใช้จริงข้าม 5 บ้าน ชี้คู่ที่ความหมายซ้ำกันแต่ตั้งชื่อคนละคำ (building_footprint/building_outline, boundary_line/lot_boundary, grading_note/grading_note_or_slab) — ยังไม่ได้ตัดสินใจรวมชื่อให้เป็นมาตรฐาน แค่บันทึกไว้ |
| 2026-07-13 | เพิ่มกฎ "Axis order rule" ใน section 4 (Grid) — แกนตั้ง (y_lines, แถวตัวอักษร) ต้องมาก่อนแกนนอน (x_lines, คอลัมน์ตัวเลข) เสมอในทุก `grid_ref` แบบ free-text | Claude (Sonnet 5, Claude Code) | มะขาม (สั่งหลังเจอว่า `grid_ref` ที่ย่อไว้ในบ้าน 1 หน้า06 เขียนแกนนอนก่อนโดยไม่ตั้งใจ) | ตรงกับ convention เดิมของ `"A-1"` (row ก่อน column) อยู่แล้ว แค่ทำให้ชัดเจนเป็นกฎลายลักษณ์อักษร แก้ไฟล์ `json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า06_floor_plan.json` ให้ตรงกันด้วย |
| 2026-07-14 | เพิ่ม section 10a "Stairs (`element_type: \"stair\"`) — `grid_ref`" | Claude (Sonnet 5, Claude Code) | มะขาม (สั่งให้บันได `grid_ref` ใส่แค่กริดที่ใกล้ที่สุดแบบประมาณ ไม่ต้องอธิบายยาว) | ตัดข้อความ "between X/Y — see A-11" ทิ้ง เหลือแค่ `"~A-1"` style — footprint จริงของบันไดอยู่ใน detail sheet (A-11) อยู่แล้ว ไม่ต้องซ้ำใน grid_ref ระดับแปลนพื้น แก้ไฟล์ `json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า06_floor_plan.json` (บันได_ST1/ST2) ให้ตรงกันด้วย |
| 2026-07-14 | เพิ่ม "Element ordering within `elements[]`" ใน section 4 (Grid) — เรียงลำดับ elements ตามการอ่านแบบ: บนลงล่าง, ซ้ายไปขวา, แนวนอนก่อนแนวตั้งถ้าจุดเริ่มตรงกัน | Claude (Sonnet 5, Claude Code) | มะขาม (สั่งให้เน้นลำดับการเขียน/อ่านแบบนี้ ยืนยัน yes ให้เพิ่มเข้าสเปคหลังถามก่อนตามกฎข้อ 9) | ก่อนหน้านี้ elements[] เรียงตาม element_id/mark (กลุ่ม B2 ทั้งหมดก่อน กลุ่ม B4 ทั้งหมด ฯลฯ) ไม่ใช่ตำแหน่งจริงบนแบบ — เปลี่ยนเป็นเรียงตามตำแหน่งเพื่อให้อ่านสอดคล้องกับแบบจริง แก้ไฟล์ `json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า19_view2_beam_plan.json` เป็นตัวอย่างแรกที่ทำ (20 elements เรียงใหม่ครบ ไม่มีข้อมูลหาย) |
| 2026-07-14 | เพิ่มกฎ "Don't inline the joined spec into every atomic segment" ใน section 7 (Spec join) — เก็บ spec ที่ join แล้วไว้ครั้งเดียวต่อมาร์คใน object ใหม่ `specs{}` keyed by `element_id` แทนการพิมพ์ซ้ำในทุก atomic segment | Claude (Sonnet 5, Claude Code) | มะขาม (สั่งแยก spec ซ้ำออกจากไฟล์ หน้า19 beam plan เพราะ "จะได้ไม่ซ้ำซากจนกลายเป็น god object" แล้วสั่ง "แก้ใน primary rawjson ด้วย" ยืนยันให้เพิ่มเป็นกฎทั่วไป) | ทำในไฟล์ `json_แก้ไขแล้ว/01บ้าน_เล็ก_1ชั้น_01/บ้าน_เล็ก_1ชั้น_01_หน้า19_view2_beam_plan.json` ก่อนเป็นตัวอย่างแรก (verify ทุกมาร์คมี spec เหมือนกันเป๊ะทุก occurrence ก่อนแยก: B2 x2, B4 x3, B5 x3, B3 x3, B4X x2) — เพิ่มข้อแยกด้วยว่า spec-level flag (เช่น ASYMMETRIC main_bar) ควรอยู่ใน specs entry ไม่ใช่ซ้ำทุก occurrence แต่ occurrence-specific flag (เช่น arrow symbol ที่จุดเดียว) ยังอยู่ที่ elements[] entry เดิม |

## วิธีเพิ่มแถวใหม่

ก่อนแก้ `primary_rawjson_schema.md` ทุกครั้ง (อ้างอิง `rule_of_tune.md` กฎข้อ 7 ก่อนเสมอ) ให้เพิ่มแถวใหม่ทันที:

- **วันที่** — วันที่แก้จริง (ISO format `YYYY-MM-DD`)
- **หัวข้อที่แก้** — section/บรรทัดที่แก้ในสเปค สรุปสั้นๆ ว่าเพิ่ม/เปลี่ยนอะไร
- **AI ที่ใช้ทำ** — ชื่อ/รุ่นโมเดลที่ใช้แก้
- **ผู้แก้ไข/อนุมัติ** — คนที่สั่ง/อนุมัติการแก้ในบทสนทนานั้น
- **หมายเหตุ** — เหตุผล/บริบท ทำไมถึงแก้
