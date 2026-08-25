# json_แก้ไขแล้ว

โฟลเดอร์นี้เป็น**สำเนาสำหรับตรวจสอบ/แก้ไขความถูกต้อง**ของ raw JSON แต่ละบ้าน (คัดลอกมาจาก `rawjson_ยังไม่ได้แก้ไขโดนคน/0N<house>/`) — ใช้แก้ไขได้อิสระโดยไม่ต้องขออนุญาตตามกฎข้อ 1 ของ `rule_of_tune.md` (เพราะ path นี้ไม่เข้าข่ายไฟล์ที่กฎคุ้มครอง) แต่ถ้าจะเอาผลที่แก้แล้วไปทับกลับ `rawjson_ยังไม่ได้แก้ไขโดนคน/` ต้องทำตามกฎข้อ 1-3 เต็มรูปแบบ (เตือนก่อน + log)

## Convention

- ค่าไหนที่มะขามสั่งแก้/ยืนยันเองโดยตรง (ไม่ใช่ Claude เดา) → ตั้ง `confidence_score: 1` เสมอ พร้อม flag อธิบายว่าแก้เพราะอะไร วันที่เท่าไหร่
- ทุกไฟล์ที่แก้ต้อง validate ผ่าน `JSON.parse` ก่อนถือว่าเสร็จ

## บันทึกการแก้ไข

### 01บ้าน_เล็ก_1ชั้น_01

- **2026-07-13** — `หน้า00_gridline.json`: dummy grid `3'` แก้จาก 8.5 → **7.6** (ขอบผนังจริง ตามหน้า05/A-03 ผังบริเวณ) และเพิ่ม `3''` = **8.5** กลับเข้ามาเป็นกริดที่สองในช่องเดียวกัน (คานยื่นเลยผนังไปรับชายคา, ตามหน้า19 คาน B4X) — เดิมเข้าใจผิดว่ามีแค่เส้นเดียว
- **2026-07-13** — `หน้า19_view2_beam_plan.json`: คาน B4X (C-3/B-3 → C-3''/B-3'') span_length_m กลับไปเป็น 1.5 (อ้างอิง 3'' ไม่ใช่ 3')
- **2026-07-13** — `หน้า05.json`: `boundary_line_right.dimension_m` null → **14.6** (มิเรอร์จากฝั่งซ้ายที่พิมพ์ไว้ 14.60 ม. เพราะที่ดินเป็นรูปสี่เหลี่ยม)

---

### 02บ้าน_เล็ก_1ชั้น_02

**⚠️ ยังไม่เสร็จ** — เริ่มรีวิว 2026-07-15/16 (apply convention จากบ้าน 1 + รีเช็ค pattern=plan ทั้ง 15 ไฟล์ + เพิ่ม dummy grid 6 เส้น) แต่ยังเหลือไฟล์ส่วนใหญ่ของบ้านนี้ (หน้า03-05, 08-09, 11, 13, 15, 18-22, 30-38, 41-45, 49-70) ที่ยังไม่ได้ไล่ตรวจ/แก้ตาม convention เลย และยังไม่ได้ sync กลับ `rawjson_ยังไม่ได้แก้ไขโดนคน/02บ้าน_เล็ก_1ชั้น_02/` — ดูรายละเอียดเต็มใน `สิ่งที่ต้องแก้.md` หัวข้อ "02บ้าน_เล็ก_1ชั้น_02" (ข้อ 18-23)

---

### 03บ้าน_เล็ก_2ชั้น_01 และ 04บ้าน_เล็ก_2ชั้น_02

**⚠️ ยังไม่เสร็จ** — เริ่มรีวิว 2026-07-16 (แรกที่เป็นบ้าน 2 ชั้น) ทำ full depth ทั้งกริดมาสเตอร์ + ไฟล์โครงสร้าง (footing/beam/tie-beam/roof-frame/column schedule) + ไฟล์ pattern=plan ส่วนใหญ่ + misc-pattern check เจอบั๊ก additional_bars position ซ้ำแบบเดียวกับบ้าน 1/2 ในทั้ง 2 หลัง (แก้แล้ว) และเจอ cross-house price-table digit errors 3 จุด (แก้แล้วทั้งบ้าน 2/3/4) แต่ไฟล์ที่เหลือส่วนใหญ่ (elevations, sections, schedules, details, BOQ) ยังไม่ได้ไล่ตรวจ และยังไม่ได้ sync กลับ rawjson_ยังไม่ได้แก้ไขโดนคน/ ทั้งคู่ — ดูรายละเอียดเต็มใน `สิ่งที่ต้องแก้.md` หัวข้อ "03บ้าน_เล็ก_2ชั้น_01" (ข้อ 24-28) และ "04บ้าน_เล็ก_2ชั้น_02" (ข้อ 29-33)

---

### 05บ้าน_เล็ก_2ชั้น_03

**⚠️ ยังไม่เสร็จ** — เริ่มรีวิวรอบแรก 2026-07-19 ตามคำสั่งมะขาม (เฉพาะหน้า00 + pattern=plan): copy โฟลเดอร์จาก raw มาใหม่, normalize convention เชิงกลไกทั้ง 30 ไฟล์ plan (`grid2-gridF`→`F2`, `gridAprime`→`A'`), สร้างกริดมาสเตอร์ใหม่ (nested `grid{}` + dummy ตามกฎ beam-endpoint ของมะขาม: `F'`(14.40), `4'`(9.6), `3'`(8.35 ขอบชานพัก), `D'`(6.60 คานแบ่ง lane บันได) + แก้การอ่านผิด "notch F-E" → ส่วนต่อขยาย F-F' ในหน้า32/33), specs{} + zoom นับจุด S-08 แล้ว (B2X/B3X/B4/B5 แก้ครบ), หน้า88-90 → misc, ตารางราคาตรวจ 5 สำเนาแล้ว (ข้อ 37) แต่**ยังไม่ได้ทำ**: แกน y ใช้ origin ที่แถว A (ต่างจากบ้าน 02-04 — รอมะขามตัดสินใจ flip), ผนัง SOA/BX1 y-extent ยังรอ zoom, ไฟล์อื่นนอก pattern=plan (elevations/sections/schedules/BOQ), sync กลับ raw — ดู `สิ่งที่ต้องแก้.md` ข้อ 34-37

---

### 06-11 (บ้าน_ใหญ่_1ชั้น_01, บ้าน_ใหญ่_2ชั้น_01, บ้าน_เล็ก_1ชั้น_03/04/05/06)

**⚠️ เพิ่งเข้ามา 2026-08-02 — ยังไม่ได้รีวิวเนื้อหา** copy สดจาก `rawjson_ยังไม่ได้แก้ไขโดนคน/` (571 ไฟล์) แล้วทำ **เฉพาะการปรับรูปแบบให้ตรงกับบ้าน 01-05** ยังไม่มีการตรวจกับภาพแบบต้นฉบับสักหน้าเดียว:

- **pattern นอกสเปค** (บ้าน 07 เท่านั้น, 21 ไฟล์): `detail`→`section`, `elevation`/`diagram`→`side_profile`, `plan`→`site_plan`/`roof_plan`
- **grid master** (7 ไฟล์): ย้าย `x_lines`/`y_lines` เข้าไปซ้อนใน `grid{}` ตามแบบบ้าน 01-05
- **footing** (11 ไฟล์): ใช้กฎ item 48 (1 entry ต่อ mark + `count` + `grid_refs[]`) + strip ขีด point-ref — เหลือ 3 ไฟล์ที่**ตั้งใจไม่รวม** เพราะ entry ต่างกันที่ confidence/note จริง (บ้าน 06 `F2`, 07 `F1`, 09 `F0.8x0.8`)
- **rebar** (บ้าน 10/11, 65 ค่า): `main_bar`/`stirrup` ที่เก็บเป็น string ล้วน → object ตามสเปค §6 โดยเก็บสตริงเดิมไว้ใน `printed_as` ทุกตัว

**ยังไม่ทำทั้งหมด** ดูรายการเต็มใน `สิ่งที่ต้องแก้.md` ข้อ 60 — ที่ใหญ่ที่สุด: บ้าน 10/11 ไฟล์ `pattern=section` ไม่มี `elements[]` เลย (ตั้งชื่อ array เองรายไฟล์), `specs{}` ยังไม่ทั่วถึง, และ **beam plan ทุกหลังยังไม่ได้ตรวจว่าคานหายหรือเปล่า** (บ้าน 01-05 ตอนตรวจเจอคานหายทุกหลัง)

---

### 2026-08-24 — schema-normalize ทุกหลัง (Claude, ภายใต้ att1235 ระหว่างมะขามออกไปข้างนอก)

ปรับทั้ง 11 หลังให้ตรง `primary_rawjson_schema.md` ปัจจุบัน (**267 จุด / 246 ไฟล์** + gridmaster
12 ไฟล์) — validate `json.loads` ผ่านครบ 1,180 ไฟล์หลังแก้ สคริปต์+log เต็มอยู่ใน session
scratchpad (`fix_schema_phaseA.py`/`fix_gridmaster_phaseB2.py`):

- **discipline** `architecture`→`architectural` (157 ไฟล์ บ้าน 02-05), ค่านอก vocab 6 ไฟล์
  (`site_regulations`→`regulatory`; `credits`/`administrative`/`reference`/`cover`→`misc`)
- **pattern roof_frame** `roof_plan`→`plan` 8 หลัง (บ้าน 01-05, 08, 09, 11) — ปิดบั๊ก data-loss
  ที่ t03/README บันทึกไว้ (Constistant `buildElements()` อ่านเฉพาะ `plan` → คานโครงหลังคา 8 หลัง
  ไม่เคยถึง BOQ) พร้อม warning ในไฟล์
- **container §0.1**: `element`→`elements` (15), `steel_members`→elements/`steel_member` (4),
  `void_bays`→elements/`note` (1), `stair_details`→`stair` + `other_details`→`beam`+flag (1),
  `reinforcement`+`footing_bearing_notes`→`design_criterion` (4), `sheet_index`+
  `sheet_list_structural`→`sheet_index_entry` (5)
- **notes §4a**: `notes_sections`/`spec_notes`→`sections[]` (17), `raw_text`/`notes_text`
  (string)→`sections[]` entry (~20 ไฟล์ รวม elevation/side_profile ที่มี raw_text ด้วย —
  เกิน scope §4a ที่พูดถึง pattern notes เท่านั้น แต่เลือกให้ container เดียวกันแทนที่จะปล่อย
  raw_text ที่ไม่มีใน spec เลย)
- **rebar**: `stirrup_or_tie`→`stirrup` (3), `rebar_cover_m`→`cover_mm` int มม. + printed_as (2)
- **gridmaster §4 (2026-08-21 revision)**: เพิ่ม `grid.z_levels[]` ทั้ง 12 ไฟล์ — **harvest จาก
  ข้อมูล level ที่คนรีวิวแล้วในไฟล์ต่อหน้าของบ้านตัวเอง** (4 รูปแบบที่พบจริง: ป้าย Thai เป็น key,
  prose "ระดับ... +X.XX", `level_labels_as_printed`, `levels_m` dict — แบบสุดท้าย key อังกฤษของ
  reviewer ติด flag `label_is_reviewer_key_not_printed_text`) **ไม่ใช่การกวาดรูปใหม่** —
  `dimension_chains[]`/`unassigned_dimensions[]` **จงใจไม่เพิ่ม** (ต้องกวาดรูปทีละหน้า ยังไม่ทำ;
  การคำนวณย้อนจาก pos_m คือปลอม provenance) — warning ในทุก gridmaster บอกทั้งสองข้อ

**จงใจไม่แตะ (บันทึกไว้ ไม่ใช่ลืม):** container drift ในไฟล์ MEP/สถาปัตย์/index/symbol
(`rows`/`circuits`/`equipment`/`rooms_shown`/`symbol_entries`/`index_rows`/ฯลฯ ~132 จุด) —
เป็น pass-3 subtasks ที่ไม่เข้า dataset โครงสร้างคืนนี้; และ `element_type` ที่ reviewer แต่งเอง
(truss/purlin/roof_overhang/ฯลฯ) — §0.4 อนุญาตการแต่งพร้อม warn, การ remap ของที่คนตัดสินแล้ว
เสี่ยงกว่าปล่อย

---

### 2026-08-25 — normalize ทั้ง 2 tree ให้ตรงสเปกปัจจุบัน + อัปเกรด checker (Claude, att1235)

ทำกับ **ทั้ง `json_แก้ไขแล้ว/` และ `rawjson_ยังไม่ได้แก้ไขโดนคน/` ทั้ง 49 หลัง** (รอบ 2026-08-24
ทำแค่ 11 หลัง) — **485 จุด / 430 ไฟล์** validate `json.loads` ผ่านครบหลังแก้:

- **discipline** `architecture`→`architectural` (345), `site`/`administrative`/`credits`/
  `reference`/`cover`→`misc` หรือ `regulatory` ตามเนื้อหา (11), `null` บนหน้าสารบัญ→`front_matter` (4)
- **`roof_plan`→`plan`** อีก 7 ไฟล์ที่รอบก่อนไม่ได้แตะ (บ้านนอก 11 หลังแรก)
- **notes §4a**: `notes_sections`/`spec_notes`/`notes_text`/`raw_text`/`notes_general`→`sections[]` (22),
  ดูดคีย์เฉพาะกิจ (`concrete_strength`→`concrete`, `steel_grade`→`steel`, ฯลฯ) เข้า `notes{}` (20)
- **`notes{}` flat fields** — parse `fc_ksc`/`fy_main_ksc`/`fy_stirrup_ksc` จาก `sections[]` ของ
  ไฟล์ตัวเอง 62 ค่า/26 ไฟล์ เก็บข้อความที่พิมพ์ไว้ใน `notes.parsed_as` ทุกตัว **นี่คือครั้งแรกที่ค่า
  พวกนี้ถึง consumer จริง** (§4a บอกเองว่าไม่เคยถึงสักหลัง) — ไฟล์ที่พิมพ์ค่าขัดกัน (SD-40 กับ SD-50
  ในหน้าเดียว) **จงใจปล่อยว่าง** ไม่เลือกให้เอง
- **ไฟล์ truncated** `31.../หน้า25_plan_footing.json` (พังทั้ง 2 tree) — ปิดให้ parse ได้ เก็บ `F5`
  ที่ครบ ทิ้งเศษ `F10` ที่ขาด **ไม่เดาค่าที่หาย** + warning บอกว่าหายอะไรไป
- **`tools/check_format.py`** เพิ่มกฎ 2026-08-21 ที่ checker เดิมไม่มี (discipline vocab,
  `source_image`, notes one-off key, structural roof-framing ต้องเป็น `plan`, gridmaster ขาด 3 array)
  — สาเหตุรากที่ drift หลุดมาได้คือ checker ตามสเปกไม่ทัน

**เหลือค้าง (ต้องกวาดรูปใหม่ ทำแทนไม่ได้):** gridmaster 25 ไฟล์ยังไม่มี `dimension_chains[]`/
`unassigned_dimensions[]` (+ z_levels บางไฟล์) — เติม array ว่างคือโกหกว่า "อ่านแล้วไม่เจอ" ตาม §4;
และ `notes{}` ของอีก ~76 ไฟล์ที่ไม่มี `sections[]` ให้ parse

`สิ่งที่ต้องแก้.md` **ย้ายออกไป** `wait_for_ทิ้ง/stale_value_logs/` (คำสั่งมะขาม) — เป็นบันทึก
ค่าเก่า→ค่าใหม่รายบ้าน 1,220 บรรทัดที่นั่งอยู่ในโฟลเดอร์ training data = ช่องปนเปื้อนข้ามหลัง

---

สงสัย ให้ถามมะขาม
