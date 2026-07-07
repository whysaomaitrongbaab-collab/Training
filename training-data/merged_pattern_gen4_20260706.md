# Merged Pattern — Generation 4 (Claude Gen 2 × Makham Gen 3, merged 2026-07-06)

รวม 2 สาย schema ที่วิวัฒนาการคู่ขนานกันอย่างอิสระเข้าเป็นสเปคเดียว:
- **Gen 2** — Claude (บทสนทนานี้), `raw/image/บ้าน_เล็ก_1ชั้น_01/claude_output_01/02/03/`, ซูมภาพจริงทุกรอบ, 4 หน้าตัวอย่าง (19,21,24,40)
- **Gen 3.1-3.3 (Makham's Pattern)** — มะขาม, `training-data/mk_test/t1/t2/`, เอกสารต้นทาง [`Makham's patter of rawjson20260705.md`](../Constistant/mk's%20stuff/Makham's%20patter%20of%20rawjson20260705.md) (repo `Constistant`), ครอบคลุมหน้า 1-60 ทุก discipline

**กติกาการ merge:** ห้ามตัดฟีเจอร์ของฝั่งใดทิ้ง — ทุกจุดที่ทั้งสองฝั่งต่างกันจะแก้ไว้ชัดว่า **เลือกอะไร + ทำไม + อีกฝั่งเสียอะไรไปไหม** (ถ้าไม่เสีย ให้บอกว่า "แค่คนละ serialization ข้อมูลเดียวกัน")

---

## 1. Pattern taxonomy — ใช้ชุด 10 ของ Makham (ขยายจาก 4 ของ Gen 2)

`plan | section | schedule | notes | index | material_list | site_plan | site_profile | gridline | unknown`

Gen 2 มีแค่ 4 ตัวแรก (scope ล็อก structural+boq) — **ไม่เสียอะไร**: 4 ตัวนั้นยังทำงานเหมือนเดิมทุกอย่าง แค่เพิ่มอีก 6 ตัวไว้รองรับ scope ที่กว้างกว่า (ที่ mk_test ทำอยู่) `run_pipeline.py` (อัตโนมัติ) **ยังคง action แค่ pattern ที่ตรงกับ scope structural+boq เดิม** (plan/section/schedule/notes/gridline + material_list สำหรับ boq) — pattern อีก 4 ตัว (index/site_plan/site_profile/unknown) เอกสารไว้เผื่อขยาย scope ในอนาคต ยังไม่ auto-extract

## 2. Multi-view ต่อหน้า — ใช้ `views[]` inventory-first ของ Gen 2 เป็นกลไกหลัก

Gen 3 ไม่มีกลไกนี้ (เจอปัญหานี้ซ้ำเองระหว่างทดสอบ หน้า 18/21 — ดูข้อ 5 ใน doc ต้นทาง) → **Gen 2 ชนะเคลียร์ ใช้ `views[]`** เก็บทุก pattern/view ที่อยู่ในหน้าเดียวกันไว้ครบ ไม่มีอะไรหาย

ส่วนไฟล์แยกต่อ view ของ Makham (`_view1_footing_plan.json`, `_view2_beam_plan.json`) **เป็นแค่ physical file layout** (1 ไฟล์ = 1 view) ไม่ใช่กลไกคนละแบบกับ `views[]` — **เก็บไว้ทั้งคู่**: ตอน extract ให้ inventory ทุก view ก่อนแบบ Gen 2 (ป้องกัน view ที่ 2 หาย) แล้วค่อยเขียนออกเป็นไฟล์แยกต่อ view แบบ Makham (ง่ายต่อ Label Studio task-gen ที่มะขามต่อ pipeline ไว้แล้ว — `label-studio-tasks-makham.js`)

## 3. Grid — รวม 3 ฟีเจอร์เข้าด้วยกัน (ไม่มีใครเสีย)

| ฟีเจอร์ | มาจากฝั่งไหน | คงไว้ |
|---|---|---|
| คำนวณ span ด้วยโค้ด ไม่ให้โมเดลกะ (`apply_grid_spans()`) | Gen 2 | ✅ คงไว้ทั้งหมด |
| `span_source`: `grid_table`/`local_dimension`/`unresolved` | Gen 2 (Makham ยืมกลับไปใช้ "Generation 3.1 ข้อ 1" — ยืนยันว่าจำเป็นจริง) | ✅ |
| Atomic segment (1 entry = 1 ช่วง grid) group ทีหลังด้วย `(element_id, span, span_source)` | Gen 2 | ✅ คงไว้ — Makham เขียนแบบ atomic แต่ยังไม่ group เป็น `count`; Gen 4 ให้โมเดลส่ง atomic (แบบ Makham) **แล้วโค้ด group เป็น `count`+list ให้อัตโนมัติ** (แบบ Gen 2) — ได้ของทั้งคู่ ไม่มีใครเสีย |
| Dummy grid + prime notation (`1'`, `A'`, `A''`) + ไฟล์ `<house>_หน้า00_gridline.json` เป็น master ข้ามหน้า | **Makham (Gen 3.2)** — Gen 2 ไม่มี ปล่อยเป็น `"?"` เฉยๆ | ✅ ใหม่ทั้งหมด รับเข้ามาเต็ม — เป็นฟีเจอร์ที่ resolve จุดที่ Gen 2 เคยทิ้งไว้เป็น unresolved ได้จริง (พิสูจน์แล้วกับ B1/B3X/B5X หน้า 19) |
| Companion gridline ไฟล์แยกต่างหาก ไม่ฝังซ้ำในทุก view | ทั้งคู่คิดแบบเดียวกันอิสระ (Gen 2: ต่อรอบ, Gen 3.2: ต่อบ้านข้ามหน้า) | ✅ ใช้แบบ Makham (ต่อบ้าน กว้างกว่า ครอบคลุมกว่า) |

**Grid axis convention (ข้อ 9 ที่ Makham เปิดคำถามไว้ — ตัดสินใจแล้วใน Gen 4):**
`x_lines` = กริดแนวนอนตามขอบบนแผ่น (ปกติเป็นตัวเลข 1,2,3...), `y_lines` = กริดแนวตั้งตามขอบข้างแผ่น (ปกติเป็นตัวอักษร A,B,C...) — **ยึดตาม Makham** (ตรงกับธรรมเนียม Cartesian ทั่วไปกว่า) ไฟล์เก่าของ Gen 2 (`claude_output_03`) ใช้สลับกัน (x=ตัวอักษร,y=ตัวเลข) — **ไม่ต้องแก้ย้อนหลัง** (ตัวเลขตำแหน่งถูกต้องเป๊ะ แค่ label แกนสลับ) แค่บันทึกไว้ว่าไฟล์เก่าอ่านสลับแกน ถ้าจะเทียบ x/y ข้ามรุ่นต้องรู้จุดนี้

**Grid_ref string format:** ใช้ format ของ Gen 2 (`"A-1/A-2"` มีขีด+สแลชคั่นชัดเจน) เป็นมาตรฐานไปข้างหน้า แทน format อัดแน่นของ Makham (`"{D1D2,4}"`) — **ข้อมูลเหมือนกันทุกประการ แค่ serialize คนละแบบ ไม่มีอะไรหาย** เหตุผลที่เลือกของ Gen 2: อ่านง่ายกว่าด้วยตา, ตรงกับที่ `run_pipeline.py`/`CLAUDE.md`/`rule_of_tune.md` อ้างอิงไว้แล้ว เปลี่ยนน้อยที่สุด

### 3.1 คำสั่งสร้างไฟล์ "หน้า 0" grid master (อ้างอิงตรงจาก Makham's Pattern of Raw JSON — 2026-07-05, หัวข้อ "Generation 3.2")

Gen 4 รับกติกานี้เข้ามาเต็มตามที่เอกสารต้นทางระบุไว้ **คำต่อคำ**:

1. **Dummy grid naming** — เมื่อพบเส้นโครงสร้าง (คาน/ผนังรับน้ำหนัก) ที่ไม่อยู่บนกริดหลักที่มีชื่อพิมพ์จริงในแบบ ให้ตั้งชื่อกริดเสมือนด้วย **prime notation** ต่อท้ายกริดหลักที่ใกล้ที่สุด (`1'`, `A'`, `3'`; ถ้ามีมากกว่า 1 เส้นในช่วงเดียวกัน ไล่เป็น `A''`, `A'''`) ระบุ `pos_m` จากเส้นบอกระยะที่พิมพ์จริงเสมอ (ห้ามเดา) และเก็บ `"type":"dummy"` แยกจาก `"type":"named"` ของกริดหลัก — ข้อนี้อยู่ใน prompt จริงของ `run_pipeline.py` แล้ว (ดูหัวข้อ 3 ด้านบน)
2. **สั่งสร้าง/อัปเดตไฟล์ `<house>_หน้า00_gridline.json` ก่อนเริ่ม extract หน้าอื่น** — `"png":"00"` เป็น convention หมายถึง "ไม่ใช่หน้าจริงในเอกสาร แต่เป็นไฟล์สังเคราะห์กริดกลางของทั้งบ้าน" รวมทั้งกริดหลัก (`type:"named"`) และ dummy grid ทั้งหมดที่พบไว้ในที่เดียว — ทุกหน้า plan/section ที่อ้างตำแหน่งของบ้านนี้ต้องชี้กลับมาที่ไฟล์นี้ผ่าน field `grid_source` แทนการเขียน grid ซ้ำหรือบรรยายเป็นข้อความอิสระต่อไฟล์
3. **ไฟล์ gridline ต่อหน้าเดิม (ถ้ามี) ให้เก็บไว้ไม่ลบ** เพื่อ traceability (สืบย้อนได้ว่ากริดแต่ละเส้นยืนยันจากหน้าไหน) แต่ไฟล์ `หน้า00` คือตัวที่ใช้อ้างอิงจริงต่อไปเสมอ

**สถานะ implementation (สำคัญ — ตามสไตล์เดียวกับหัวข้อ 6/11 ด้านล่าง):** กติกานี้ยืนยันแล้วจากการทดสอบจริงใน `mk_test/t1`/`t2` (มะขามยืนยัน dummy grid `1'` ได้จริงจากหน้า 06 ตรงกับตำแหน่งคาน B1 ในหน้า 19 อิสระ 2 ทาง) **แต่ `run_pipeline.py`/`build_document_map.py` ยังไม่มี stage ไหนสร้างไฟล์ `หน้า00_gridline.json` นี้โดยอัตโนมัติเลย** (grep ทั้ง 2 ไฟล์หา "หน้า00" ไม่เจอ) — prompt ปัจจุบันสั่งให้โมเดลอ่าน `grid{x_lines,y_lines}` (รวม dummy grid) **ต่อหน้า/ต่อ view เท่านั้น** ไม่มี stage รวมข้ามหน้าเป็นไฟล์กลางของบ้าน ต้องเพิ่ม stage ใหม่หลัง extract ทุกหน้าของบ้านเสร็จ (อ่าน `grid` object จากทุกไฟล์ผลลัพธ์ของบ้านเดียวกัน → merge + dedupe ตำแหน่งกริดเดียวกันที่อาจอ่านได้ไม่ตรงกันเป๊ะข้ามหน้า → เขียนเป็น `หน้า00_gridline.json`) — บันทึกเป็นงานที่ควรทำต่อ ไม่ใช่ตัด scope ทิ้ง (ดูรายการ "ยังไม่ได้ทำ" ท้ายเอกสาร)

## 4. Beam segment splitting — กติกา 3 แบบของ support point (Gen 2 ทั้งหมด, Makham ยังไม่เคยมี)

คานหนึ่งตัว = ระหว่าง 2 support ที่ติดกันเท่านั้น ต้องแยกทันทีถ้า:
1. มีเสา/grid intersection คั่นกลาง
2. คานวางพาดอยู่บนคานอีกตัว (ไม่ใช่เสา) — ใส่ `confidence_flags: ["bears_on_beam:<mark>(<end>)"]`
3. คานหักมุม/เปลี่ยนทิศทาง

**คงไว้ทั้งหมด** — Makham ไม่มีกติกานี้เลย (ดูจาก mk_test/t1 ที่บรรยาย grid_ref เป็นข้อความรวมยาวๆ) Gen 4 ใช้ของ Gen 2 เต็มๆ

## 5. Rebar spec — รวมโครงสร้างใหม่ (breaking change จากทั้ง 2 ฝั่งเดิม แต่มีเหตุผลจากหลักฐานจริง)

### 5.1 เปลี่ยนจาก flat field เป็น nested object (ตาม Makham)
`main_bar_count/main_bar_dia_mm/main_bar_type` (Gen 2 เดิม, flat) → `main_bar: {count, dia_mm, type}` (Makham) — เหตุผล: ข้อ 5.2 ทำให้ต้อง nest อยู่ดี เอาแบบ Makham ไปเลยตั้งแต่ต้น

### 5.2 แก้ปัญหาเหล็กบน-ล่างไม่เท่ากัน (คำถามเปิดข้อ 5 ของ Makham — **ตัดสินใจแล้ว**)
พบหลักฐานตรงกันอิสระ 2 ทาง (Gen 2 อ่านหน้า 21 เอง + Makham fresh-extract เอง) ว่า B5/B5X มีเหล็กบน 2 เส้น + ล่าง 3 เส้นจริง ไม่ใช่ 2+2 — เก็บด้วย count เดียวรวมกัน (=5) ทำข้อมูลสำคัญหายไป

**Gen 4 decision:** แยก `main_bar` เป็น `top`/`bottom` เสมอ:
```json
"main_bar": {
  "top":    { "count": 2, "dia_mm": 16, "type": "RB" },
  "bottom": { "count": 3, "dia_mm": 16, "type": "RB" }
}
```
กรณีสมมาตร (ส่วนใหญ่) `top` กับ `bottom` จะมีค่าเท่ากัน — ไม่เสียอะไร ยังรวมยอดได้ง่าย (`top.count + bottom.count`)

### 5.3 `additional_bars[]` (เหล็กเสริมพิเศษหยุดที่ L/8) — รับเข้ามาตามที่ Makham เสนอ
```json
"additional_bars": [{ "count": 1, "dia_mm": 16, "position": "บนคาน หยุดที่ L/8 จากหน้าเสา", "note": "..." }]
```
Gen 2 เดิมเก็บเป็นข้อความยาวใน `confidence_flags` — Makham ออกแบบ field แยกที่ query ได้จริง ดีกว่า **รับเข้ามาแทนของ Gen 2**

### 5.4 `Ø` (กลม) = RB เสมอ ไม่ใช่ DB — ยืนยันร่วมกันแล้ว (ทั้งคู่เจอ bug เดียวกันอิสระ)
ห้ามอนุมานจากขนาดเส้นผ่านศูนย์กลาง ต้องดูสัญลักษณ์ที่พิมพ์จริงเท่านั้น (Ø=กลม=RB, เส้นข้ออ้อยมีรอยหยัก=DB) — บันทึกเป็นกติกาถาวรใน prompt

## 6. Spec join (ตำแหน่งใน plan + สเปคจาก section/schedule รวมกัน) — รับของ Makham (Gen 3.3) เต็ม

`plan` element (ตำแหน่ง/grid_ref) + `section` **หรือ** `schedule` element (width/height/main_bar/stirrup ของ mark เดียวกัน) join ด้วย `element_id` เข้าด้วยกัน ให้รีวิว 1 หน้าเห็นครบ

**⚠️ ระบุให้ชัด (แก้ความคลุมเครือของรุ่นก่อนหน้าของไฟล์นี้ ที่พิมพ์แคบเหลือแค่ "section element"):** หน้าตัดคาน/เสา (`width_mm`/`height_mm`) และเหล็กข้างใน (`main_bar`/`stirrup`) **ไม่ได้ถูกบังคับว่าต้องมาจาก pattern `section` เท่านั้น** — `section` และ `schedule` ถือเป็น**แหล่งสเปคที่เท่ากัน** ทั้งคู่ ด้วยเหตุผล 2 ข้อ:
1. สเปคดั้งเดิมของ Makham's Pattern of Raw JSON — 2026-07-05 (หัวข้อ "กติกาของ pattern `section`/`schedule`") เขียนไว้ตรงๆ ว่า **"`section` (และ `schedule`) คือ source of truth ของสเปค"** — ไม่เคยจำกัดไว้แค่ section ตั้งแต่ต้น
2. `STEP 6` ของ prompt จริงที่ยิงเข้าโมเดลใน `run_pipeline.py` ตอนนี้เขียนว่า **"for `schedule`/`section` views (rebar spec of a beam/column mark)"** — ปฏิบัติกับทั้งสอง pattern เหมือนกันทุกประการตอนสกัดข้อมูล ไม่มีการแยกพิเศษ

```
width_mm, height_mm, main_bar{...}, stirrup{...}, additional_bars[], concrete_grade, steel_grade,
spec_source            <- ไฟล์ section/schedule ที่ join สเปคมา (ระบุด้วยว่ามาจาก pattern ไหน ไม่ใช่แค่ path)
spec_confidence_score  <- ความมั่นใจสเปค แยกจาก confidence_score (ตำแหน่ง) หลัก
```

**กติกา conflict ระหว่าง section กับ schedule (ใหม่ในรอบนี้ — เอกสารก่อนหน้าไม่เคยตอบคำถามนี้):** ถ้า `element_id` เดียวกันมีสเปคปรากฏอยู่ทั้งไฟล์ pattern `section` **และ** `schedule` ของบ้านเดียวกัน แล้วค่าไม่ตรงกัน ให้ **`section` ชนะเสมอ** (เหตุผล: section เป็นรายละเอียดเจาะจงต่อ 1 mark โดยตรง ส่วน schedule มักเป็นตารางสรุปรวมหลาย mark ในแถวเดียว มีโอกาสพิมพ์/อ่านผิดพลาดจากการเรียงแถวมากกว่า) ทุกครั้งที่เกิด conflict แบบนี้ต้องเขียน confidence_flag `"spec_conflict_section_vs_schedule"` กำกับไว้ที่ element นั้นเสมอ ห้าม silently เลือกโดยไม่บันทึกร่องรอย — **หมายเหตุความเสี่ยง:** กติกา "section ชนะ" นี้เป็นการตัดสินใจใหม่ที่เพิ่งเพิ่มเข้ามาตอนนี้ (2026-07-07) ยังไม่เคยผ่านการทดสอบกับข้อมูลจริง ต่างจากกติกาอื่นในเอกสารนี้ที่ผ่านการยืนยันจาก `mk_test/`/`claude_output_0N` มาแล้ว — ถ้าเจอเคสจริงที่กติกานี้ให้ผลผิด ต้องกลับมาทบทวน ส่วนกรณี `element_id` เดียวกันปรากฏใน `section` มากกว่า 1 ไฟล์ (เช่น B2 มีทั้งใน S-04 และ S-05) ยังเป็นคำถามเปิดเดิมจาก Makham's Pattern ที่ยังไม่ได้ตอบเช่นกัน (ยังไม่เจอเคสทดสอบจริง)

**สถานะ implementation:** design พร้อมใช้ (ผ่านการทดสอบจริงใน `mk_test/t2` แล้ว — เฉพาะส่วน join กับ section, ส่วนกติกา conflict/schedule ยังไม่ผ่านการทดสอบตามที่ระบุข้างบน) — **`run_pipeline.py` (อัตโนมัติ) ยังไม่ได้ implement การ join ข้ามหน้านี้** เพราะ pipeline ปัจจุบันประมวลผลทีละหน้า ไม่ cross-reference หน้าอื่น ต้องเพิ่ม stage ใหม่ (อ่าน plan แล้วไปหา section/schedule ที่มี element_id ตรงกันจากหน้าอื่นของบ้านเดียวกัน พร้อม apply กติกา conflict ข้างบน) — บันทึกเป็นงานที่ควรทำต่อ ไม่ใช่ตัด scope ทิ้ง

## 7. `level` field สำหรับ schedule หลายระดับ (เช่น เสา C1 คนละสเปคตามชั้น)

**Gen 4 decision (ตามที่ Makham เสนอและให้เหตุผล):** ใช้ `level` field แยก ไม่ฝัง level ลงใน `element_id`
```json
{ "element_id": "C1", "level": "โครงหลังคา", "width_mm": 150, ... }
{ "element_id": "C1", "level": "พื้นชั้น 1, ตอม่อ, ฐานราก", "width_mm": 200, ... }
```
เหตุผล: `element_id` ควรตรงกับ mark ที่พิมพ์จริงเป๊ะเพื่อ join ข้ามหน้าได้ตรงไปตรงมา (Gen 2 เดิมฝัง level ใน element_id เช่น `"C1_โครงหลังคา"` — **เปลี่ยนมาใช้แบบ Makham**, ไม่เสียข้อมูลอะไร แค่ normalize ให้ join ง่ายขึ้น)

## 8. `precast_plank_detail` — element_type ใหม่สำหรับหน้ารายละเอียดวางพื้นสำเร็จรูป (รับของ Makham เต็ม)

ทั้ง Gen 2 (หน้า 24, ใส่ SCHEMA_MISMATCH_WARNING เพราะ field คาน/เสาไม่เข้ากับเนื้อหา) และ Makham (Gen 3.1 ข้อ 8) เจอปัญหาเดียวกันอิสระ — **Makham เสนอ element_type ใหม่ที่ Gen 2 เห็นด้วยว่าดีกว่า**:
```json
{
  "element_id": "SP_interior", "element_type": "precast_plank_detail",
  "description": "ลักษณะการวางพื้น SP ภายใน",
  "dowel_bar": { "count": 2, "dia_mm": 9, "type": "RB" },
  "topping_mesh": { "dia_mm": 6, "spacing_mm": 200 },
  "topping_thickness_min_mm": 50,
  "level_step_mm": null,
  "confidence_score": 0.7, "confidence_flags": []
}
```
`level_step_mm` ใช้กับกรณีระดับพื้นต่างจากปกติ (เช่นพื้นห้องน้ำ Gen 2 เจอ step ลง 0.10ม. ที่ Makham ยังไม่เจอในรอบทดสอบของตัวเอง — จุดนี้ Gen 2 มีข้อมูลเสริมให้ Makham)

## 9. Footing/point-type element — เก็บตำแหน่งเป็น array (ของ Gen 2) ไม่ใช่ comma-string (ของ Makham)

ข้อมูลเดียวกัน แค่ serialize ต่างกัน: Gen 2 `"grid_refs": ["A-1","A-2",...]` vs Makham `"grid_ref": "A1,A2,..."` — **เลือก array** เพราะ parse ง่ายกว่า (ไม่ต้อง split string เอง) ไม่มีอะไรหาย

## 10. Slab marker (SO/SI/SX/ST) — ยืนยันร่วมกันแล้ว

`element_type: "slab"` (ไม่ใช่ `"unknown_symbol"`) — cross-reference ข้ามหน้าได้เหมือน beam (plan บอกตำแหน่ง/จำนวนจุด, section หน้า S-06 บอกสเปคแต่ละชนิดพื้น join ด้วย element_id) **หมายเหตุจาก Gen 2 ให้ Makham:** ตรวจให้แน่ใจว่าเป็น `"SI"` (ตัว I) ไม่ใช่ `"S1"` (เลข 1) — ยืนยันจากการอ่านซ้ำเฉพาะจุดนี้ 3 รอบอิสระ

## 11. BOQ — 1 PNG อาจมี 2 แผ่นจริงซ้อนกัน (ยืนยันร่วมกันแล้ว, ต้อง implement ใน `run_pipeline.py`)

ทั้ง Gen 2 (หน้า 40) และ Makham (หน้า 48-57, อิสระต่อกัน) เจอกติกาเดียวกัน: PNG ต้นฉบับ = 2 แผ่น portrait เรียงกันแบบ landscape → ต้องหมุน 90° แล้วแยกครึ่งซ้าย-ขวาเป็นคนละ sheet_no คนละไฟล์ (`_1.json`/`_2.json`)

**สถานะ implementation:** `run_pipeline.py` เดิม (`extract_boq()`) หมุนทั้งภาพ 90° แต่ **ยังไม่แยกครึ่งซ้าย-ขวาเป็น 2 sheet** — ต้องแก้โค้ด (ดูหัวข้อถัดไป)

**เพิ่มเติมจาก Gen 2 (การทดสอบหน้า 40):** แถวที่เป็นบรรทัดต่อท้ายไม่มี item_no/qty ของตัวเอง (เช่น "โครงเคร่าเหล็กชุบสังกะสี...") ต้องแยกเป็น item คนละแถว ห้ามรวมเข้ากับ description ของแถวก่อนหน้า — ยืนยันด้วยการอ่าน crop จัดตำแหน่งแถวแล้วจาก Makham เช่นกัน (Gen 3.1 ไม่ได้พูดชัดเจนเท่า Gen 2 ในจุดนี้ แต่ผลลัพธ์ตรงกัน)

---

## สรุปฟีเจอร์ทั้งหมด — เช็คลิสต์ว่าไม่มีอะไรหาย

| ฟีเจอร์ | ที่มา | สถานะใน Gen 4 |
|---|---|---|
| `views[]` inventory-first | Gen 2 | ✅ คงไว้ |
| ไฟล์แยกต่อ view | Makham | ✅ คงไว้ (physical layout, ใช้คู่กับ views[]) |
| Grid คำนวณด้วยโค้ด + `span_source` | Gen 2 | ✅ คงไว้ |
| Atomic segment → group เป็น count | Gen 2 (atomic) + Gen 2 (group) | ✅ คงไว้ทั้งคู่ |
| Dummy grid + page00 master | Makham | ✅ รับเข้าเต็ม (สเปค — ดูหัวข้อ 3.1), ⚠️ ยังไม่ auto-implement |
| Beam-on-beam / corner-change split + bears_on_beam | Gen 2 | ✅ คงไว้ |
| main_bar top/bottom split | หลักฐานร่วม, decision ใหม่ | ✅ ตัดสินใจใหม่ |
| additional_bars[] | Makham | ✅ รับเข้าเต็ม |
| Ø=RB ไม่ใช่ DB | หลักฐานร่วม | ✅ ยืนยันร่วม |
| Spec join (plan+section) | Makham | ✅ รับ design เต็ม, ⚠️ ยังไม่ auto-implement |
| `level` field (schedule หลายระดับ) | Makham | ✅ รับเข้า แทน compound element_id ของ Gen 2 |
| `precast_plank_detail` + dowel_bar/topping_mesh/level_step_mm | Makham | ✅ รับเข้าเต็ม |
| footing position เป็น array | Gen 2 | ✅ คงไว้ (แทน comma-string) |
| slab marker = element_type "slab" | หลักฐานร่วม | ✅ ยืนยันร่วม |
| BOQ 2-sheet split | หลักฐานร่วม | ✅ ตัดสินใจร่วม, ⚠️ ต้อง implement โค้ด |
| BOQ continuation row แยก item | Gen 2 (+ สอดคล้อง Makham) | ✅ คงไว้ |
| Pattern taxonomy 10 ชนิด | Makham | ✅ รับเข้า (แต่ automated scope ยังล็อก structural+boq เดิม) |

**ไม่มีฟีเจอร์ไหนถูกตัดทิ้ง** — ทุกจุดที่ format ต่างกัน (grid_ref string, footing position, main_bar flat-vs-nested) เป็นการเลือก serialization เดียวเพื่อความสม่ำเสมอเท่านั้น ข้อมูลเดิมแปลงกลับ-ไปกลับมาได้ครบ ไม่มีการสูญเสียเชิงความหมาย

## ยังไม่ได้ทำ (บันทึกไว้ ไม่ใช่ตัด scope)

1. Cross-page spec join อัตโนมัติใน `run_pipeline.py` (ข้อ 6) — ต้องมี stage ใหม่หลัง extract ทุกหน้าเสร็จ
2. `precast_plank_detail`/`slab` cross-page join กับหน้าสเปค (S-06/S-07) — ยังทำแค่ manual
3. Pattern 4 ชนิดนอก scope structural (index/site_plan/site_profile/unknown) — ยังไม่ auto-extract
4. Dummy grid `3'`/`A'`/`A''` ยัง tentative (confidence 0.5-0.6) — ต้อง zoom หน้า 19/20 ยืนยันตำแหน่งคานจริงอีกรอบ
5. Automated `<house>_หน้า00_gridline.json` master-file generation (ข้อ 3.1) — prompt อ่าน grid ของแต่ละหน้าแยกกันอยู่ ไม่มี stage รวมข้ามหน้าเป็นไฟล์กลางของบ้านเลย
6. กติกา conflict "section ชนะ schedule" (ข้อ 6) — ตัดสินใจใหม่ยังไม่ผ่านการทดสอบกับข้อมูลจริง, และกรณี element_id ซ้ำข้าม section หลายไฟล์ยังไม่มีคำตอบ
