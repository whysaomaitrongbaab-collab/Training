# t03 prompt design — 2 passes, per-pattern extraction

> # ⛔ เลิกใช้แล้ว — เก็บไว้อ่านย้อนหลังเท่านั้น
> แบบนี้เป็นดีไซน์ 2 pass ของ **2026-08-04** ถูกแทนที่ด้วยดีไซน์ 4 pass (0/1/2/3) เมื่อ
> **2026-08-21** ของจริงอยู่ที่ [`../README.md`](../README.md) และโฟลเดอร์
> `pass0_classify/` `pass1_organize/` `pass2_used/` `pass3_unused/`
> **อย่าเอา prompt ในโฟลเดอร์นี้ไปใช้** — กฎบางข้อในนี้ขัดกับดีไซน์ปัจจุบัน

> **สถานะ: ออกแบบ ยังไม่ได้เขียน prompt จริง** — เอกสารนี้คือแบบร่างให้ตัดสินใจก่อนลงมือ
> เขียน 2026-08-04

## อำนาจสูงสุด = `primary_rawjson_schema.md`

ทุก prompt ในโฟลเดอร์นี้ต้อง**ผลิต output ที่ผ่าน `tools/check_format.py`** ซึ่งบังคับตาม
[`rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md`](../../../rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md)

**ห้าม prompt ตัวไหนสร้างกฎของตัวเอง** ถ้าเจอกรณีที่สเปคไม่ครอบคลุม → แก้สเปคก่อน (พร้อม log ตาม
`rule_of_tune.md` ข้อ 7) แล้วค่อยให้ prompt อ้างถึง ไม่ใช่เขียนกฎใหม่ลงใน prompt เงียบๆ

---

## ทำไม 2 pass ไม่ใช่ 5

production ปัจจุบัน (`js/drawing/drawing-index.js` → `qt_runRead()`) ใช้ 5 pass และ **ไม่ตรงกับ
training data เลย** — dataset ของ t01/t02 คือ "1 หน้า → JSON เต็มของหน้านั้น" ซึ่งไม่ใช่ shape
ของ pass ไหนเป๊ะๆ ผลคือโมเดลที่ทูนแล้วเสียบแทน production ไม่ได้จริง

2-pass ใหม่ออกแบบให้ **training shape = production shape** ตั้งแต่ต้น:

```
Pass 0  1 หน้า (ภาพ)                → wrapper §2 + รายการ view/pattern (§3)
Pass 1  1 หน้า (ภาพ) + pattern       → เนื้อหาตาม pattern นั้น (elements[] / grid{} / categories[])
merge   ไม่ใช้ AI                    → คำนวณ span จาก grid (§4), spec join (§7), merge point elements (§4)
```

ขั้น merge **ไม่มี prompt** — เป็นโค้ดล้วน จงใจ เพราะ §4 เขียนไว้ตรงๆ ว่า
*"Span: calculated by code from the grid only — never let the model estimate distance"*
(ข้อนี้คือสิ่งที่ production Pass 3 ปัจจุบันละเมิดอยู่ — สั่งโมเดลให้กะระยะเป็นเมตรจากภาพ)

---

## Pass 0 — จำแนกหน้า + wrapper

### output ที่ต้องได้ (§2 + §3)

§2 บังคับ 10 field บน wrapper: `png, doc_page, discipline, sheet_code, sheet_name, pattern,
source_image, confidence_score, confidence_flags, warnings`

ในนั้น **3 ตัวไม่ต้องใช้ AI** — เป็นข้อเท็จจริงของไฟล์ ไม่ใช่สิ่งที่อ่านจากภาพ:

| field | ที่มา |
|---|---|
| `png` | ชื่อไฟล์ |
| `doc_page` | ลำดับหน้า |
| `source_image` | path เต็ม |

**AI ต้องตอบแค่:** `discipline`, `sheet_code`, `sheet_name`, `pattern`, `confidence_score`,
`confidence_flags`, `warnings`

### ⚠️ ประเด็นออกแบบข้อ 1 — 1 หน้าอาจมีหลาย pattern (§3)

§3 เขียนไว้ว่า *"A page may contain multiple views/patterns — **inventory every view first with
`views[]`** (prevents losing one), then write each out as a separate file per view"*

แปลว่า Pass 0 **ห้ามตอบ pattern เดียวต่อหน้า** ต้องตอบเป็นรายการ:

```json
{
  "sheet_code": "S-04",
  "sheet_name": "แปลนฐานรากและแปลนคาน",
  "discipline": "structural",
  "views": [
    { "view_no": 1, "view_title": "แปลนฐานราก", "pattern": "plan", "confidence_score": 0.95 },
    { "view_no": 2, "view_title": "แปลนคาน",   "pattern": "plan", "confidence_score": 0.95 }
  ],
  "confidence_flags": [],
  "warnings": []
}
```

นี่คือบทเรียนข้อ 7 ใน `No_touch_box/CLAUDE.md` โดยตรง — *"เคยพลาดเพราะบังคับเลือก `pattern` เดียว
ต่อหน้า ทำให้ view ที่ 2 หายไปเงียบๆ ไม่มี warning"*

### ⚠️ ประเด็นออกแบบข้อ 2 — `pattern` มี 16 ค่า แต่ต้องเลือกจาก §1 เท่านั้น

§0.9: *"Never coin a new one"* — prompt ต้องพิมพ์รายการ 16 ค่าออกมาให้ครบใน instruction และ
บังคับให้เลือกจากในนั้น พร้อมเกณฑ์แยกที่ §0.9 ระบุไว้:

- detail sheet → `section` (ไม่ใช่ `detail`)
- elevation / schematic diagram → `side_profile` (ไม่ใช่ `elevation`)
- site plan → `site_plan` (ไม่ใช่ `plan`)
- ตารางสรุป member → `schedule` · ตารางตัดเหล็กรายเส้น → `bbs_schedule`
- รายงานเจาะสำรวจดิน → `soil_boring_log` (ไม่ใช่ `schedule`/`notes`)

**บ้าน 07 เคยประดิษฐ์ `detail`/`diagram`/`elevation` ขึ้นมาเองและต้อง remap 21 ไฟล์** — prompt
ต้องกันเรื่องนี้ตั้งแต่ต้น

### ไฟล์

```
pass0/
└── prompt.md          ← ตัวเดียว ไม่แยกตาม pattern (ยังไม่รู้ pattern ตอนนี้)
```

---

## Pass 1 — สกัดเนื้อหา แยก prompt ต่อ pattern

### input

```
ภาพหน้านั้น (1 ใบ) + pattern ที่ Pass 0 ตอบมา + view_title (ถ้ามีหลาย view)
```

### output

เนื้อหาตาม container ที่ §0.1 กำหนด — **3 แบบเท่านั้น ห้ามประดิษฐ์ชื่อ array ใหม่**

| pattern | container (§0.1) |
|---|---|
| `gridline` | `grid{ x_lines[], y_lines[] }` |
| `material_list` | `categories[].items[]` |
| ที่เหลือทั้งหมด | `elements[]` |

### กฎที่ทุก prompt ต้องมีเหมือนกัน (ใส่เป็น shared block ไม่ copy 15 รอบ)

| § | กฎ |
|---|---|
| §0.2 | ทุก element มี `element_id`, `element_type`, `confidence_score`, `confidence_flags` · `confidence_score: null` ได้ **ห้ามมั่วตัวเลข** |
| §0.3 | `element_id` = มาร์คที่พิมพ์บนแบบเท่านั้น ห้ามต่อท้ายตำแหน่ง/ชั้น/section |
| §0.4 | `element_type` เลือกจาก 40 ค่าที่มี ห้ามประดิษฐ์ (เคยบานเป็น 359 ค่า) |
| §0.5 | ขนาด member = mm จำนวนเต็ม (`width_mm`) · ระดับ/ระยะ/พิกัด = เมตร (`level_m`, `span_length_m`, `pos_m`) เป็นตัวเลข ไม่ใช่ string |
| §0.7 | ทุกค่าที่แปลงจากที่พิมพ์บนแบบ เก็บต้นฉบับไว้ใน `*_printed_as` |
| §0.8 | `grid_ref`: จุด = ไม่มีขีด (`C1`) · ช่วง = มีขีด (`D-C`) · 2 แกน = แนวตั้งก่อน (`D-C x 1-2`) · ห้ามมีคำว่า `grid`/`dummy` |
| §2a | ห้ามใส่ `phase_note` (ใช้เฉพาะ staged `op2` เท่านั้น) |

### กฎเฉพาะแต่ละ pattern

| # | pattern | § ที่บังคับ | จุดยากที่ prompt ต้องเน้น |
|---|---|---|---|
| 1 | `plan` | §4, §5, §10, §10a | **beam-endpoint rule** (ปลายคานไม่อยู่บนกริด = ต้องมี dummy grid ไม่ใช่ทิ้งคาน) · atomic ต่อ segment สำหรับคาน แต่ merge เป็นหนึ่งเดียวสำหรับ footing/column · ลำดับ element (บนลงล่าง ซ้ายไปขวา แนวตั้งก่อนแนวนอน) · `SI` vs `S1` |
| 2 | `section` | §6, §6a, §7 | **`main_bar` แยก top/middle/bottom เสมอ** แต่ **column ใช้ `count` เดี่ยว ห้ามแยก** (แยกแล้วนับเหล็กเป็น 2 เท่า) · `Ø` = RB เสมอ ห้ามเดาจากขนาด · `additional_bars` ต้องดู leader line จริง ไม่เชื่อ label |
| 3 | `schedule` | §6, §6a, §7, §8 | `level` เป็น field แยก ห้ามยัดลง `element_id` · ตารางหลายชั้นซ้ำมาร์คได้ (ข้อยกเว้นของกฎ merge §4) |
| 4 | `notes` | §0.1 ข้อยกเว้น | `sections[{heading, items[]}]` = หัวข้อโน้ต **ไม่ใช่** drawing element ห้ามพับเข้า `elements[]` |
| 5 | `index` | §0.1 ข้อยกเว้น | `sections[{title, sheet_range}]` = สารบัญเอกสาร ไม่ใช่ element |
| 6 | `material_list` | §11 | 1 PNG อาจเป็น 2 แผ่นจริง (หมุน 90° แล้วผ่าซ้าย/ขวา) · แถวต่อเนื่องที่ไม่มี item_no ต้องเป็นแถวแยก ห้ามรวมกับแถวบน · `columns[]` = หัวตาราง ไม่ใช่ element |
| 7 | `site_plan` | §13 | ⚠️ **`element_type` ยังไม่ standardize** (10 ค่าข้าม 5 บ้าน ซ้ำความหมายกัน) — prompt ต้องล็อกชื่อให้เหลือชุดเดียวก่อน ไม่งั้นจะ drift ต่อ |
| 8 | `side_profile` | §1 #8 | รูปด้าน/รูปตัดอาคาร ไม่มีเหล็ก ไม่ใช่ข้อมูลภูมิประเทศ |
| 9 | `gridline` | §4, §11a | **ยากสุดทั้งชุด** — dummy grid ตั้งชื่อตามกริดบน/ซ้าย (ไม่ใช่ใกล้สุด) · prime ordering · `pos_m` ติดลบได้ถ้าอยู่ก่อน origin · `pos_m` อ่านจากเส้นบอกระยะที่พิมพ์จริง **ห้ามเดา** · หลายอาคาร = grid master แยกไฟล์ |
| 10 | `title` | §1 #10 *(draft)* | ยังไม่มี field-set ยืนยัน |
| 11 | `symbol` | §1 #11 *(draft)* | `fixture_symbol_legend[]` เป็นตาราง reference ไม่พับเข้า `elements[]` |
| 12 | `roof_plan` | §1 #12 *(draft)* | สันหลังคา/ตะเข้/ชายคา |
| 13 | `misc` | §1 #13 | ตารางราคาซีรีส์ = `series_price_table[]` รูปเดียวเท่านั้น (เคยเก็บ 5 แบบใน 5 บ้าน) |
| 14 | `bbs_schedule` | §1 #14 *(draft)* | **ยังไม่มีข้อมูลเทรนเลย 0 ไฟล์** |
| 15 | `soil_boring_log` | §1 #15 *(draft)* | **ยังไม่มีข้อมูลเทรนเลย 0 ไฟล์** |
| — | `unknown` | — | ไม่มี prompt โดยนิยาม |

### ไฟล์

```
pass1/
├── _common/
│   ├── notation.md        ← สัญกรณ์แบบก่อสร้างไทย (DB/RB/Ø/ค1/พ1/@0.20/fc'/SD40)
│   ├── confidence.md      ← §0.2 ห้ามเดา null + flag ดีกว่าเลขมั่ว
│   └── format_lock.md     ← §0.2-§0.8 กฎที่ทุก pattern ใช้ร่วมกัน
├── plan.md
├── section.md
├── schedule.md
├── notes.md
├── index.md
├── material_list.md
├── site_plan.md
├── side_profile.md
├── gridline.md
├── title.md
├── symbol.md
├── roof_plan.md
├── misc.md
├── bbs_schedule.md
└── soil_boring_log.md
```

**15 ไฟล์ ไม่ใช่ 13** — สเปคเพิ่ม `bbs_schedule` + `soil_boring_log` เมื่อ 2026-08-04 (16 pattern
ลบ `unknown` = 15) เลข 13 คือของเดิมก่อนวันนั้น

---

## ⚠️ ปัญหาใหญ่สุดของดีไซน์นี้ — ข้อมูลเทรนต่อ pattern ไม่เท่ากันอย่างรุนแรง

นับจริงจาก `rawjson_ยังไม่ได้แก้ไขโดนคน/` ทั้ง **12 บ้าน** (2026-08-04, รวม **1,240 ไฟล์**):

| pattern | ไฟล์ | บ้าน | เทรนแยกไหวไหม |
|---|---:|---:|---|
| `material_list` | 435 | 10 | ✅ |
| `section` | 243 | 12 | ✅ |
| `plan` | 192 | 12 | ✅ |
| `side_profile` | 94 | 12 | ✅ |
| `schedule` | 71 | 12 | ✅ |
| `notes` | 58 | 12 | 🟡 บาง |
| `index` | 42 | 12 | 🟡 บาง |
| `symbol` | 27 | 9 | 🟡 บาง |
| `misc` | 25 | 9 | 🟡 บาง |
| `roof_plan` | 23 | 12 | 🟡 บาง |
| **`gridline`** | **13** | 12 | 🔴 **น้อยเกิน** |
| `site_plan` | 12 | 12 | 🔴 น้อยเกิน |
| `title` | 5 | 5 | 🔴 น้อยเกิน |
| `bbs_schedule` | **0** | 0 | ⛔ ไม่มีเลย |
| `soil_boring_log` | **0** | 0 | ⛔ ไม่มีเลย |

**`gridline` คือปัญหาที่ต้องแก้ก่อนอย่างอื่น:**
- มีแค่ **13 ไฟล์** (1 ต่อบ้าน) เพราะโดยนิยามมันเป็น master 1 ตัวต่อบ้าน
- แต่มันคือ pattern ที่**ยากที่สุด** และ**ทุกอย่างขึ้นกับมัน** — README ของ `op2` เขียนไว้ตรงๆ:
  *"Move one grid line and **every `span_length_m` in every `plan` file is wrong**"*
- t01/t02 เจอปัญหาเดียวกันมาแล้ว: gridmaster 5 ตัวจาก 403 ตัวอย่าง และเป็นตัวที่บังคับให้
  ต้องดัน `MAX_LENGTH` จาก 9,216 → 24,576 เพราะมัดภาพ 2-4 ใบต่อตัวอย่าง

---

## ตัดสินใจแล้ว (มะขาม, 2026-08-04) — 4 ข้อ

### 1. `gridline` — ใช้หน้า 00 ของทุกบ้านตรงๆ ✅ ตัดสินใจแล้ว

**ไม่รวมกับ `plan`** — `gridline` แยก prompt ของตัวเองต่อไป dataset = ไฟล์ `<house>_หน้า00_
gridline.json` ของทุกบ้าน (13 ไฟล์ = 13 บ้าน ณ ตอนนับ, 1 ไฟล์ต่อบ้านโดยนิยาม) ยอมรับว่าจำนวน
ตัวอย่างน้อยเพราะเป็นธรรมชาติของ pattern นี้ (master ไฟล์เดียวต่อบ้าน ไม่ใช่ต่อหน้า) ไม่ใช่ปัญหา
ที่ต้องแก้ด้วยการรวม pattern — ถ้าจะเพิ่มตัวอย่างต้องมาจากการเพิ่มจำนวนบ้าน ไม่ใช่เปลี่ยนนิยาม

### 2. `title` / `site_plan` / `bbs_schedule` / `soil_boring_log` — แก้ที่ dataset ตรงๆ ✅ ตัดสินใจแล้ว

**ไม่ตัดออกจาก training set** — แนวทางคือ**ขยาย dataset จริง** (เพิ่มบ้าน/เพิ่มหน้าที่มี pattern
พวกนี้จริงในแบบ) ไม่ใช่เขียน prompt ทิ้งไว้เฉยๆ แล้วข้ามการเทรน `bbs_schedule`/`soil_boring_log`
ยังมี **0 ตัวอย่าง** อยู่ — ต้องหาว่าบ้านไหนมีหน้าประเภทนี้จริงในแบบต้นฉบับก่อนถึงจะสร้าง label ได้
(ยังไม่ได้ทำ — ดูหัวข้อ "ค้าง" ท้ายไฟล์)

### 3. Pass 0 — เขียนออกมาก่อน แม้ยังไม่จบ ✅ เขียนแล้ว (draft v1)

มติ: **priority หลักคือแก้ dataset** (โดยเฉพาะคานหายบ้าน 06-12) ส่วน Pass 0 "เดี๋ยวมาต่อ" —
ยังเขียน prompt ออกมาก่อนตามที่สั่ง → [`pass0/prompt.md`](pass0/prompt.md) เขียนแล้ว (16 pattern
เต็ม, wrapper + `views[]` ตาม §2/§3) **แต่ยังเป็น draft v1** — 3 อย่างยังไม่ทำ: (1) ยังไม่มีสคริปต์
แปลง raw JSON → training pair จริง (ต้อง group ไฟล์ `source_image` เดียวกัน), (2) ยังไม่เลือก
โมเดล/hyperparameter, (3) ยังไม่ทดสอบกับภาพจริงสักหน้า

### 4. Token budget — ยังไม่ทำ รอทุกอย่างนิ่งก่อน ✅ ตัดสินใจแล้ว

**ไม่คำนวณตอนนี้** — รอจน dataset (โดยเฉพาะ Pass 1 ต่อ pattern) นิ่งก่อน แล้วคำนวณทั้งชุดทีเดียว
ครั้งเดียว ไม่ทยอยคำนวณทีละ pattern (กัน error สะสมแบบ t02 บั๊ก 1)

---

## ที่ยังไม่ได้ทำ (สถานะจริง หลังมติ 2026-08-04)

**Priority ตอนนี้ = แก้ dataset ก่อน** (มติข้อ 3) — ไม่ใช่เขียน prompt ให้ครบ 15 ไฟล์ก่อน

- ⛔ **บล็อกอันดับ 1: คานหายในบ้าน 06-12 ยังไม่เคยตรวจ** (บ้าน 01-05 หายทุกหลังตอนตรวจ:
  20→27, 22→36, 30→38, 5→21) — เทรนด้วย label ที่คานหาย = สอนให้ under-predict ตรงๆ
- ⛔ **`bbs_schedule`/`soil_boring_log` มี 0 ตัวอย่าง** — ต้องหาว่าบ้านไหนมีหน้าประเภทนี้จริงก่อน
  (มติข้อ 2: แก้ด้วยการขยาย dataset ไม่ใช่ตัดออกจากแผนเทรน)
- ✅ `pass0/prompt.md` เขียนแล้ว (draft v1) — ยังไม่มีสคริปต์แปลงข้อมูล, ยังไม่ทดสอบจริง
- ✅ [`pass1/IO_SPEC.md`](pass1/IO_SPEC.md) เขียนแล้ว — input/output contract ละเอียดต่อ pattern
  ครบ 15 ตัว (ภาพที่ต้องการ, auxiliary input เช่น grid master, container, field list ทุกตัวอ้าง §
  ของสคีมา) **แต่ยังไม่ใช่ prompt text จริง** — เป็นสเปคเตรียมก่อนเขียน prompt แต่ละไฟล์
- ⬜ `pass1/plan.md`, `section.md`, ... (prompt text จริง 15 ไฟล์) — ยังไม่เขียนสักไฟล์ รอ dataset
  นิ่งตามลำดับ priority ข้างบน
- ⬜ ยังไม่ได้เขียนสคริปต์แปลง raw JSON → training pair (ทั้ง Pass 0 และ Pass 1)
