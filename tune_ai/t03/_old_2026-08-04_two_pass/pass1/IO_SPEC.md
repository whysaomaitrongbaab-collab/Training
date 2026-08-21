---
pass: 1
purpose: exact input/output contract per pattern, before writing the 15 prompt files themselves
status: DRAFT — I/O contracts only, no prompt text written yet (that's the next step, one file
  per pattern per the README's file tree)
authority: primary_rawjson_schema.md (../../../../rawjson_ยังไม่ได้แก้ไขโดนคน/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md)
---

> ⚠️ อ่าน [`rule_of_tune.md`](../../../../No_touch_box/docs/rule_of_tune.md) ก่อนแก้ไฟล์นี้ —
> เข้าข่ายกฎข้อ 2 เหมือนไฟล์อื่นใน `prompt/`

# Pass 1 — Input/Output contract, per pattern

15 pattern (16 ลบ `unknown` ซึ่งไม่มี Pass 1 โดยนิยาม) — แต่ละ pattern มี prompt ของตัวเอง
เอกสารนี้กำหนด **input จริง / output จริง** ของแต่ละตัว ก่อนไปเขียน prompt text จริง

## Input ที่ทุก pattern ใช้ร่วมกัน (ไม่ต้องเขียนซ้ำ 15 รอบ)

| ส่วนประกอบ | มาจากไหน | หมายเหตุ |
|---|---|---|
| **ภาพ** | 1 หน้า PNG เต็มหน้า (ความละเอียดเดียวกับที่ `op1` อ่านจริง) | **ไม่ crop เฉพาะ view** — ไม่มีพิกัด bounding box เก็บไว้ในสคีมาเลย (Pass 0 ให้แค่ `view_title`/`pattern` ไม่ให้พิกัด) ถ้าหน้านั้นมีหลาย view ต้องบอกโมเดลด้วยข้อความว่า **"สกัดเฉพาะ view ที่ชื่อ X เท่านั้น"** ให้โมเดลเล็งเอง |
| `sheet_code`, `sheet_name`, `discipline` | ผลจาก Pass 0 (รู้อยู่แล้ว ไม่ต้องให้โมเดลตอบซ้ำ) | ใส่เข้า wrapper ตอน merge ไม่ใช่ Pass 1 |
| `view_title` (ถ้ามีหลาย view) | ผลจาก Pass 0 | บอกโมเดลว่ากำลังสกัด view ไหนของหน้านั้น |
| `png`, `doc_page`, `source_image` | ข้อเท็จจริงของไฟล์ | ไม่ต้องให้ AI ตอบ (เหมือน Pass 0) |
| Confidence discipline | §0.2 | `confidence_score: null` ดีกว่าเลขมั่ว ทุก pattern ใช้กฎเดียวกัน |
| Thai notation guide | เหมือนที่ Constistant ใช้ (`QT_THAI_NOTATION_GUIDE`) | DB/RB/Ø/ค/พ/@/fc'/SD40 — ใช้ร่วมทุก pattern ที่มีเหล็ก |

**Auxiliary input พิเศษ (ไม่ใช่ทุก pattern ได้):**

| pattern | ต้องการ grid master เพิ่มไหม | เหตุผล |
|---|---|---|
| `plan`, `roof_plan` | ✅ ต้องการ — แนบ `หน้า00_gridline.json` ของบ้านนั้น (หรืออย่างน้อยรายชื่อ dummy grid ทั้งหมด) | ต้องเขียน `grid_ref` ให้ตรงกับชื่อ dummy grid ที่ประกาศไว้แล้ว (`1'`, `A''`) ไม่งั้นโมเดลจะประดิษฐ์ชื่อใหม่/เขียน `"?"` ทั้งที่จริงมีชื่อแล้ว |
| `section`, `schedule`, `notes`, `index`, `material_list`, `site_plan`, `side_profile`, `title`, `symbol`, `misc`, `bbs_schedule`, `soil_boring_log` | ❌ ไม่ต้องการ | ไม่มี `grid_ref` ในเนื้อหา (spec/ตาราง/ข้อความล้วน) |
| `gridline` | — (เป็นตัว grid master เอง) | ดูหัวข้อเฉพาะด้านล่าง — อาจต้องการ**หลายภาพ** ไม่ใช่ auxiliary text |

---

## ตารางสรุป 15 pattern

| # | pattern | container (§0.1) | ต้องการ grid master | ตัวอย่างเทรนจริง | สถานะ |
|---|---|---|---|---|---|
| 1 | `plan` | `elements[]` | ✅ | 192 | พร้อม |
| 2 | `section` | `elements[]` | ❌ | 243 | พร้อม |
| 3 | `schedule` | `elements[]` | ❌ | 71 | พร้อม |
| 4 | `notes` | `elements[]` หรือ `sections[]` (ข้อยกเว้น §0.1) | ❌ | 58 | พร้อม (บาง) |
| 5 | `index` | `sections[]` (ข้อยกเว้น §0.1) | ❌ | 42 | พร้อม (บาง) |
| 6 | `material_list` | `categories[].items[]` | ❌ | 435 | พร้อม |
| 7 | `site_plan` | `elements[]` | ❌ | 12 | ⚠️ น้อย + §13 element_type ยังไม่ standardize |
| 8 | `side_profile` | `elements[]` | ❌ | 94 | พร้อม |
| 9 | `gridline` | `grid{x_lines[],y_lines[]}` | (เป็นตัวเอง) | 13 | ⚠️ น้อยโดยธรรมชาติ (มติ 08-04: ไม่รวมกับ plan) |
| 10 | `title` | `elements[]` (draft) | ❌ | 5 | 🔴 น้อยเกิน + draft |
| 11 | `symbol` | `fixture_symbol_legend[]`-style (draft) | ❌ | 27 | ⚠️ draft |
| 12 | `roof_plan` | `elements[]` (draft) | ✅ | 23 | ⚠️ draft + บาง |
| 13 | `misc` | `series_price_table[]` หรือ `elements[]` | ❌ | 25 | ⚠️ บาง |
| 14 | `bbs_schedule` | `elements[]` (draft) | ❌ | **0** | ⛔ ไม่มีตัวอย่างเลย |
| 15 | `soil_boring_log` | `elements[]` + wrapper พิเศษ (draft) | ❌ | **0** | ⛔ ไม่มีตัวอย่างเลย |

---

## 1. `plan`

**Input:** ภาพหน้า (เต็มหน้า) + **grid master ของบ้านนั้น** (รายชื่อ `x_lines[]`/`y_lines[]` ทั้งหมด รวม dummy grid — ไม่ต้องส่งทั้งไฟล์ JSON เต็ม แค่รายชื่อ+`pos_m` พอ) + `view_title` ถ้ามีหลาย view บนหน้าเดียว

**Output** (`elements[]`, §4-§5, §10, §10a):

| field | type | บังคับ | หมายเหตุ |
|---|---|---|---|
| `element_id` | string | ✅ | มาร์คที่พิมพ์เท่านั้น (§0.3) |
| `element_type` | string | ✅ | จากรายการ 40 ค่า (§0.4) |
| `grid_ref_start` / `grid_ref_end` | string | span element (คาน) | จุด ไม่มีขีด (§0.8) |
| `grid_refs[]` | array of string | point element (footing/column) | array ไม่ใช่ comma-string (§4) — **merge เป็น 1 entry ต่อมาร์ค** |
| `span_length_m` | number\|null | span element | **โมเดลกรอกได้ แต่โค้ดจะทับใน merge เสมอ** (§4) — ห้ามพึ่งค่านี้เป็นค่าสุดท้าย |
| `span_source` | enum | span element | `grid_table`/`local_dimension`/`unresolved`/`n/a` |
| `count` | number | point element | หลัง merge (§4) |
| `confidence_score`/`confidence_flags[]` | — | ✅ | §0.2 |

**กฎพิเศษที่ prompt ต้องเน้น:** beam-endpoint rule (§4 "How to FIND dummy grids") — ปลายคานที่ไม่อยู่บนกริดที่มี **ห้ามทิ้งคาน ห้ามเขียนบรรยายแทน grid_ref** ต้องขอ dummy grid เพิ่ม (แต่ Pass 1 **แก้ grid master เองไม่ได้** — ทำได้แค่ flag `confidence_flags: ["needs_dummy_grid_at_<pos>"]` ให้ merge/มนุษย์จัดการ เพราะ gridline เป็นไฟล์แยก แก้พร้อมกันไม่ได้ในการเรียกเดียว)

**ลำดับ elements[]:** บนลงล่าง ซ้ายไปขวา แนวตั้งก่อนแนวนอนถ้าจุดเริ่มตรงกัน (§4 "Element ordering")

---

## 2. `section`

**Input:** ภาพหน้า (เต็มหน้า) เท่านั้น — ไม่มี auxiliary

**Output** (`elements[]`, §6, §6a, §7):

| field | type | หมายเหตุ |
|---|---|---|
| `element_id` | string | มาร์ค (§0.3) |
| `element_type` | string | §0.4 |
| `width_mm`/`height_mm`/`thickness_mm`/`depth_mm` | number | จำนวนเต็ม (§0.5) ห้าม packed string |
| `main_bar` | object | **แยก `top`/`bottom` เสมอแม้เท่ากัน** (§6) — column **ห้าม**แยก ใช้ `count` เดี่ยว |
| `main_bar.middle` | object | optional — มีเฉพาะเมื่อเห็นแถวเหล็กกลางจริง (§6) |
| `additional_bars[]` | array | เฉพาะเหล็กที่ไม่อยู่หน้าไหนเลย — **เช็ค leader line จริง ห้ามเชื่อ label เฉยๆ** (§7) |
| `stirrup` | object | `{count?, dia_mm, type, spacing_mm}` — ชื่อ `stirrup` เท่านั้น ห้าม `tie`/`tie_bar` (§0.6) |
| `steel_section` | object | ถ้าเป็นเหล็กรูปพรรณ แทน `main_bar`/`stirrup` (§6a) — **มีอย่างใดอย่างหนึ่งเท่านั้น ห้ามมีทั้งคู่** |
| `concrete_grade`/`steel_grade` | string | §7 |
| `confidence_score`/`confidence_flags[]` | — | §0.2 |

**กฎพิเศษ:** `Ø` = RB เสมอ ห้ามเดาจากขนาด (§6 ท้าย) · column ใช้ `count` เดี่ยว **ห้ามแยก top/bottom** (แยกแล้วนับเหล็กเป็น 2 เท่า) · ถ้ามาร์คเดียวกันปรากฏหลายจุดในหน้าเดียวและสเปคเหมือนกันทุกตัวอักษร — เขียนแค่ครั้งเดียวพอ ปล่อยให้ merge จัดการ join เข้า `specs{}` (§7)

---

## 3. `schedule`

**Input:** ภาพหน้า เท่านั้น

**Output** (`elements[]`, §6, §6a, §7, §8):

โครงสร้าง field เหมือน `section` ทุกประการ (ใช้ prompt block เดียวกันสำหรับ rebar/spec ได้) **ต่างแค่บริบท** — 1 แถว = 1 member ในตาราง ไม่ใช่หน้าตัดขยาย

**field เพิ่มเฉพาะ pattern นี้:**

| field | type | หมายเหตุ |
|---|---|---|
| `level` | string | multi-level schedule (§8) — **ห้ามยัดลง `element_id`** ต้องแยก field เสมอ เช่น `C1` @ `"roof frame"` vs `C1` @ `"ground floor, pedestal, footing"` |

**กฎพิเศษ:** มาร์คเดียวกันซ้ำได้ถ้า `level` ต่างกัน (ข้อยกเว้นเดียวของกฎ merge §4 — ตารางหลายชั้นห้าม merge เข้าด้วยกัน)

---

## 4. `notes`

**Input:** ภาพหน้า เท่านั้น

**Output:** **สอง container ที่ยอมรับได้ (§0.1 ข้อยกเว้น)** — เลือกตามรูปแบบจริงของหน้า:

| รูปแบบหน้า | container |
|---|---|
| ข้อความยาวไม่มีหัวข้อชัด | `elements[]` (`element_type: "note"`) |
| แบ่งเป็นหัวข้อลำดับเลข ("1. ข้อกำหนดทั่วไป", "2. ...") | `sections[{heading, items[]}]` — **นี่ไม่ใช่ drawing element ห้ามพับเข้า `elements[]`** |

**กฎพิเศษ:** เนื้อหาระดับโปรเจกต์ (fc', fy, cover, มาตรฐานอ้างอิง) — คัดลอกข้อความจริง ไม่สรุปย่อ (จะเสียความแม่นยำ)

---

## 5. `index`

**Input:** ภาพหน้า เท่านั้น

**Output** (`sections[]`, ข้อยกเว้น §0.1):

| field | type | หมายเหตุ |
|---|---|---|
| `title` | string | ชื่อหมวด เช่น `"แบบสถาปัตยกรรม"` |
| `sheet_range` | string | เช่น `"A-01 ถึง A-15"` |

**กฎพิเศษ:** นี่คือสารบัญเอกสาร — **ไม่ใช่ element ของแบบ** ห้ามพับเข้า `elements[]` แม้จะมี field คล้าย element

---

## 6. `material_list`

**Input:** ภาพหน้า — **⚠️ ก่อนส่งเข้า Pass 1 ต้องเช็คก่อนว่า 1 PNG เป็น 2 แผ่นจริงซ้อนกันไหม** (§11: หมุน 90° แล้วแยกซ้าย/ขวาเป็นคนละภาพ) — **นี่คือ pre-processing ก่อน Pass 1 ไม่ใช่สิ่งที่ขอให้โมเดลทำเอง** ถ้าตรวจพบว่าเป็น 2 แผ่น ต้องแยกไฟล์ก่อนแล้วเรียก Pass 1 สองครั้ง

**Output** (`categories[].items[]`):

| field | type | หมายเหตุ |
|---|---|---|
| `category` | string | ชื่อหมวดงาน |
| `items[].item_no` | string | เลขลำดับ |
| `items[].description` | string | รายการ |
| `items[].quantity` | number | — |
| `items[].unit` | string | หน่วยไทย (ลบ.ม./ตร.ม./กก. ฯลฯ) |

**กฎพิเศษ:** แถวต่อเนื่องที่ไม่มี item_no/qty ของตัวเอง **ต้องเป็นแถวแยก ห้ามรวมกับแถวบน** (§11) · `columns[]` ในหน้าตารางนี้ = หัวตาราง ไม่ใช่ element (§0.1)

---

## 7. `site_plan`

**Input:** ภาพหน้า เท่านั้น

**Output** (`elements[]`):

field พื้นฐานตาม §0.2/§0.5 ทั่วไป

**⚠️ กฎพิเศษที่สำคัญที่สุดของ pattern นี้ (§13):** `element_type` **ยังไม่ standardize** — พบ 10 ค่าซ้ำความหมายกันข้าม 5 บ้านเดิม (`building_footprint`/`building_outline`, `boundary_line`/`lot_boundary`, `grading_note`/`grading_note_or_slab`) **prompt ต้องล็อกชื่อให้เหลือชุดเดียวตั้งแต่ตอนเขียน** ไม่ปล่อยให้โมเดลเลือกเองเหมือนที่ผ่านมา ไม่งั้นจะ drift ต่อเข้า dataset ใหม่อีก — **ต้องตัดสินใจชื่อ canonical ก่อนเขียน prompt จริง** (ยังไม่ได้ตัดสินใจ ณ ตอนเขียนไฟล์นี้)

---

## 8. `side_profile`

**Input:** ภาพหน้า เท่านั้น

**Output** (`elements[]`):

รูปด้านหรือรูปตัดอาคาร (ไม่ใช่ terrain/site info) — field หลักคือ `level_m` (ระดับ), มิติความสูง, ป้ายกำกับชั้น ไม่มีเหล็ก ไม่มี `grid_ref`

**กฎพิเศษ:** ห้ามใช้ pattern นี้กับข้อมูลที่ตั้ง/ภูมิประเทศ (ชื่อเดิม `site_profile` เคยทำให้เข้าใจผิด — เปลี่ยนชื่อแล้วตั้งแต่ 07-08)

---

## 9. `gridline`

**Input:** **อาจมากกว่า 1 ภาพ** — ต่างจากทุก pattern อื่น เพราะ dummy grid บางเส้นต้อง cross-reference จากหลายหน้า (เช่น plan sheet ยืนยันตำแหน่งหนึ่ง, beam plan ยืนยันอีกตำแหน่ง) ตรงกับที่ §2 ให้ใช้ `source_pages[]` แทน `source_image` เดี่ยว

**Output** (`grid{x_lines[], y_lines[]}`):

```json
{
  "id": "1'",
  "pos_m": 7.6,
  "type": "dummy",
  "confidence_score": 1,
  "confidence_flags": []
}
```

**กฎพิเศษ (ยากสุดทั้งชุด, §4):**
- ตั้งชื่อ dummy grid ตามกริดที่**บน/ซ้าย** เสมอ (ไม่ใช่ใกล้สุด)
- ลำดับ prime ตามทิศการอ่าน (x: ซ้าย→ขวา, y: บน→ล่าง) — เจอตัวแรก 1 prime เจอตัวสอง 2 prime
- จุดกำเนิด (0,0) ต้องเป็นกริดหลักซ้ายสุด/บนสุดเสมอ — dummy grid ห้ามแย่งตำแหน่งนี้ ถ้าอยู่ก่อน origin ใช้ `pos_m` **ติดลบ**
- `pos_m` อ่านจากเส้นบอกระยะที่พิมพ์จริงเท่านั้น **ห้ามเดา**
- ต้องระบุด้วยว่าแบบชุดนี้ใช้ **drawing break line** หรือไม่ (สัญลักษณ์ซิกแซกกลางเส้น มักถูกมองข้าม — บทเรียนบ้าน 06 ที่ทำให้ grid master ต้องพลิกจาก 10 เส้นเป็น 11 เส้น)
- multi-building set (§11a): 1 grid master ต่อ 1 อาคาร ห้ามผสม coordinate space

---

## 10. `title`

**Input:** ภาพหน้า เท่านั้น

**Output:** **ยังไม่มี field-set ยืนยัน** (`(draft)`, §1 #10) — ตัวอย่างจริงมีแค่ 5 ไฟล์จาก 5 บ้าน ต้องสำรวจฟิลด์ที่ใช้จริงก่อนล็อก schema ให้แน่น

---

## 11. `symbol`

**Input:** ภาพหน้า เท่านั้น

**Output:** `(draft)` — แนวโน้มคือ `fixture_symbol_legend[]`/`fixture_install_height_standard[]` (§0.1 กล่าวถึงเป็นตาราง reference ที่ไม่พับเข้า `elements[]`) แต่ยังไม่ล็อก schema ชัดเจน

---

## 12. `roof_plan`

**Input:** ภาพหน้า + **grid master** (เหมือน `plan` — สันหลังคา/ตะเข้/ชายคาก็อ้างอิงกริดโครงสร้างเดียวกัน)

**Output:** `(draft)`, §1 #12 — คาดว่าจะมี field คล้าย `plan` แต่เพิ่มมิติชายคา/สันหลังคา `element_type` ที่มีอยู่ (`rafter`) อาจไม่พอ — ต้องสำรวจตัวอย่างจริง 23 ไฟล์ก่อนล็อก

---

## 13. `misc`

**Input:** ภาพหน้า เท่านั้น

**Output:** ถ้าเป็นตารางราคาซีรีส์ 10 แบบ → **`series_price_table[]` รูปเดียวเท่านั้น** (§0.1 — เคยเก็บ 5 แบบต่างกันใน 5 บ้านมาก่อน ห้ามประดิษฐ์แบบใหม่อีก):

| field | type |
|---|---|
| `design` | string |
| `name` | string |
| `size_sqm` | number |
| `price_pile_baht` | number |
| `price_spread_baht` | number |

ถ้าเป็นหน้าปกรวม/โปรโมชันอื่น → `elements[]` ทั่วไปพร้อม `element_type: "misc"` (ไม่มี schema เฉพาะ)

---

## 14. `bbs_schedule` — ⛔ ไม่มีตัวอย่างเทรนเลย

**Input:** ภาพหน้า เท่านั้น (ตามดีไซน์)

**Output** (`elements[]`, §1 #14, ยืมโครง field จาก `QT_PROMPT_BBS_EXTRACT` ของ Constistant เพราะเป็นแบบเดียวที่มีอยู่):

| field | type | หมายเหตุ |
|---|---|---|
| `element_id` | string | element ที่บาร์นี้เป็นของ (เช่น `"C1"`) |
| `bar_mark` | string | รหัสบาร์ (เช่น `"T1"`) |
| `dia_mm` | number | ขนาดเหล็ก |
| `shape_code` | string | BS8666 (00=ตรง, 11=งอ90°, 51=ปลอกปิด ฯลฯ) |
| `len_A`/`len_B`/`len_C` | number | มิติงอ เป็น**เมตร** (ต่างจาก `plan`/`section` ที่ mm — ต้องระวัง prompt สับสน) |
| `qty` | number | จำนวน |
| `grade` | string | SR24/SD30/SD40 |

**⛔ ต้องแก้ก่อนเขียน prompt จริง:** ไม่มีไฟล์ raw JSON ไหนใช้ pattern นี้เลยสักไฟล์ (0/1,240) — ต้องหาว่าบ้านไหนมีหน้า BBS จริงในแบบต้นฉบับก่อน ไม่งั้น prompt นี้เป็นแค่การเดา field จาก Constistant โดยไม่มีหลักฐานจริงรองรับ (ตามมติ 08-04 ข้อ 2)

---

## 15. `soil_boring_log` — ⛔ ไม่มีตัวอย่างเทรนเลย

**Input:** ภาพหน้า (PDF/รูปรายงานเจาะสำรวจดิน) เท่านั้น

**Output** (`elements[]` + wrapper พิเศษ, §1 #15, ยืมโครง field จาก `QT_PROMPT_SOIL_BORING_LOG` ของ Constistant):

| field | type | หมายเหตุ |
|---|---|---|
| `element_type` | string | `"soil_layer"` คงที่ |
| `depth_m` | string | เช่น `"0-1.5"` (ช่วง ไม่ใช่ตัวเลขเดี่ยว) |
| `soil_type` | string | ตามที่รายงานระบุ ไม่แปล |
| `spt_n` | string | blow count, `"R"`/`"Refusal"` ได้ |
| `moisture_content_pct`/`unit_weight_kn_m3`/`cohesion_kpa`/`friction_angle_deg`/`liquid_limit_pct`/`plastic_limit_pct`/`specific_gravity` | number\|null | ผลแล็บ — แปลงหน่วยตามที่ Constistant ทำอยู่ (t/m³→kN/m³ ×9.80665 ฯลฯ) |
| **wrapper:** `borehole_id` | string | ไม่ใช่ element |
| **wrapper:** `groundwater_level_m` | number | ค่าเดียวของทั้งหลุมเจาะ ไม่ใช่ต่อชั้นดิน |

**เรียงชั้นดินตื้น→ลึกเสมอ**

**⛔ ต้องแก้ก่อนเขียน prompt จริง:** เหมือน `bbs_schedule` — 0 ตัวอย่างจริง ต้องหาบ้านที่มีรายงานเจาะสำรวจดินก่อน (แบบก่อสร้างบ้านทั่วไปมักไม่แนบรายงานนี้ในชุดเดียวกัน อาจต้องหาจากแหล่งอื่น เช่น Site Investigation ของ Constistant ที่มีตัวอย่างจริงอยู่)

---

## สิ่งที่ยังไม่ได้ทำ (สถานะจริง)

- **ยังไม่ได้เขียน prompt text จริงสักไฟล์** — เอกสารนี้คือ I/O contract เตรียมไว้ก่อนเขียน prompt
- `site_plan`'s canonical `element_type` list — ยังไม่ตัดสินใจ (บล็อกก่อนเขียน prompt ของ pattern นี้)
- `title`/`symbol`/`roof_plan` — field-set ยัง draft ทั้งหมด ต้องสำรวจตัวอย่างจริงก่อนล็อก
- `bbs_schedule`/`soil_boring_log` — บล็อกด้วย "0 ตัวอย่าง" ตามมติ 08-04 ข้อ 2 (ต้องขยาย dataset จริง ไม่ใช่เขียน prompt เดาไปก่อน)
- **บล็อกอันดับ 1 ที่ยังไม่เริ่ม:** คานหายบ้าน 06-12 — ตามมติ 08-04 ข้อ 3 priority คือแก้ dataset ก่อน ไฟล์นี้เขียนเสร็จก่อนตามที่ขอ แต่ยังไม่ได้แปลว่า dataset พร้อมแล้ว
