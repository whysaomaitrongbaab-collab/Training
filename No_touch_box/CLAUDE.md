# CLAUDE.md — No_touch_box/

Context สำหรับ AI agent ที่มาทำงานต่อในโฟลเดอร์นี้ (portable — อาจอยู่ใน repo แยกจาก Constistant หลัก)

> ## ⚠️ 2026-08-02 — Label Studio ถูกยกเลิกทั้งหมด (คำสั่งมะขาม)
> **ไม่เก็บข้อมูลผ่าน Label Studio อีกต่อไป และ `op1`/`op2` ห้ามสร้างไฟล์ task ของ Label Studio อีก** — ทุกไฟล์ที่เกี่ยวกับ Label Studio **ถูกลบจริงแล้ว 2026-08-02** (`label_studio_stuff/` ทั้งโฟลเดอร์ = generator + import scripts + XML + task JSON 10 บ้าน 21MB, mindmap PDF, `label-studio-config.xml`, `annotated/`, `upload-to-supabase-storage.js` — รวม 51 ไฟล์) กู้คืนได้จาก git history ถ้าจำเป็น
> **`manifest.json` กับ `review.html` ไม่ใช่ของ Label Studio** — เป็นของ pipeline รุ่น `pdf-processor.py`/`qwen-processor.js` ที่อ่านไฟล์นี้ตรงๆ เคยย้ายออกไปผิดแล้วเอากลับคืนแล้ว
> Ground truth ปัจจุบัน = raw JSON ใน `rawjson_ยังไม่ได้แก้ไขโดนคน/0N<house>/` ตรวจด้วย `tools/check_format.py` เท่านั้น
> **ทุก section ในไฟล์นี้ที่พูดถึง Label Studio review flow (3 sections ด้านล่าง) = ประวัติศาสตร์ อ่านเพื่อเข้าใจที่มาได้ แต่ห้ามทำตาม**

> 📋 **Session ใหม่เริ่มจากอ่าน [SESSION_HANDOFF_2026-07-06.md](SESSION_HANDOFF_2026-07-06.md) ก่อน** — สรุปงานล่าสุดทั้งหมด (Label Studio, Makham's Pattern schema Gen 3.1-3.3, คำถามเปิดที่ค้างอยู่) ไม่ต้องไล่ chat history เก่า (schema doc เต็ม [`Makham's patter of rawjson20260705.md`](../wait_for_ทิ้ง/No_touch_box/docs/Makham's%20patter%20of%20rawjson20260705.md) ย้ายไปอยู่ repo Constistant ชั่วคราวตั้งแต่ 5 ก.ค. แล้วย้ายกลับมาที่นี่ (`No_touch_box/`) วันที่ 7 ก.ค. — ดู `workmen's_diary/` ที่ root repo Training สำหรับประวัติการย้ายเต็ม — **เอกสารนี้ถูกย้ายเข้า `wait_for_ทิ้ง/` เมื่อ 2026-08-04** เป็นประวัติศาสตร์ ไม่ใช่สเปคที่ใช้จริงอีกต่อไป ดู `docs/ARCHIVE.md`)

> ⚠️ **อ่าน [rule_of_tune.md](rule_of_tune.md) ก่อนเริ่มงานทุกครั้ง — ไม่มีข้อยกเว้น**
> กฎห้ามแตะ raw JSON ของ raw data ก่อนได้รับอนุญาต + **การกระทำใดๆ ที่ส่งผลต่อการทูนนิ่งต้องมีการเตือนเสมอ** (ไม่ใช่แค่แก้ raw JSON ตรงๆ — รวมถึงแก้ script/schema ที่กระทบข้อมูลปลายทาง) + บันทึก format JSON ที่ใช้ทูนจริงไว้อ้างอิง
> ทุกครั้งที่แก้ raw JSON จริง (ได้รับอนุญาตแล้ว) ต้องบันทึกใน [raw_json_data_log.md](raw_json_data_log.md) ด้วยเสมอ (ไฟล์ที่แก้ / AI ที่ใช้ / ผู้แก้ไข)

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
  → เขียนลง raw/image/<house>/qwen-output/_document_map.json

Step 2 (run_pipeline.py) — ไล่ทุกหน้าตาม map:
  discipline == structural  → Stage B (unified extractor, 1 call/หน้า, model=qwen-vl-max)
                               อ่าน title-block sheet_name เอง → INVENTORY ทุก view บนหน้านั้นก่อน (ดูหัวข้อ
                               "Multi-view extraction" ด้านล่าง) → เลือก pattern ต่อ view → extract แต่ละ view
  discipline อื่น            → skip (ตอนนี้ scope = structural only)
```

### Multi-view extraction + grid-based span (เพิ่ม 2026-07-03)

**เปลี่ยน schema จาก flat `pattern`+`plan[]/schedule[]/section[]/notes` เดี่ยวต่อหน้า → `views[]` array**
เหตุผล: 1 หน้า S-series มักมีหลาย view ปนกัน (เช่น "แปลนฐานราก" + "แปลนคาน" คนละกล่องบนหน้าเดียวกัน หรือ detail box แยกต่อคาน 1 ตัว) — ของเดิมบังคับเลือก pattern เดียวต่อหน้าทำให้ view ที่ 2 เป็นต้นไปหายไปเงียบๆ ตอนนี้ prompt สั่งให้ **inventory ทุก heading/caption ที่ underline/bold ก่อน** แล้วค่อย extract ทีละ view เข้า `views: [{view_title, pattern, elements/notes, grid?}, ...]`

**Span length คำนวณด้วยโค้ด ไม่ใช้ตัวเลขที่โมเดลกะเอง** (`apply_grid_spans()` ใน `run_pipeline.py`):
- โมเดลอ่าน grid dimension chain ที่พิมพ์จริงบนหน้า (ระยะห่างระหว่างเส้น grid) เข้า `view.grid.{x_lines,y_lines}` (list ของ `{id, pos_m}`) — อ่านครั้งเดียวต่อหน้า ใช้ร่วมกันได้ทุก plan view บนหน้านั้น
- `element.grid_refs` เป็น segment string (เช่น `"A-1/A-2"`) → หลัง extract โค้ด Python คำนวณระยะจริงจากตาราง grid เติม/ทับ `span_length_m` ให้ (ไม่ใช้ค่าที่โมเดลกะสายตา)
- `span_source` บอกที่มา: `"grid_table"` (คำนวณจาก grid — ค่าเริ่มต้น, ถูกทับด้วยโค้ดเสมอ), `"local_dimension"` (ปลายไม่ใช่ grid intersection แต่มีตัวเลขพิมพ์กำกับไว้ใกล้ๆ — โมเดลอ่านเลขนั้นมาตรง ๆ, โค้ด**ไม่ทับ**ค่านี้), `"unresolved"` (หาตัวเลขไม่เจอเลย — `span_length_m:null`)
- ปลายที่ resolve เป็น grid point ไม่ได้ (cantilever/มิติ mid-bay) เขียนเป็น `"?"` แทน grid id (เช่น `"C-2/?"`)
- ถ้า segment หลายอันของ element เดียวกัน resolve ได้ไม่ตรงกัน (ต่างเกิน 15 ซม.) → ไม่เขียนทับ ใส่ flag `grid_segments_inconsistent_span` ให้คนตรวจแทน
- POINT-type element (footing/column ที่ทำเครื่องหมายซ้ำในผัง) ไม่มี span — `span_length_m:null` เสมอ, `grid_refs` แค่ list ตำแหน่งที่พบ

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

6. **`main_bar_type` ผิดทั้งหน้าได้แบบเป็นระบบ แม้ symbol เดียวกันที่จุดอื่นอ่านถูก** — pilot เทียบ Claude vs Qwen 4 หน้า (`wait_for_ทิ้ง/No_touch_box/raw/image/บ้าน_เล็ก_1ชั้น_01/claude_output_01/_pilot_comparison_summary.md`, 2026-07-02, draft ยังไม่ผ่านคนตรวจ, ย้ายเข้า `wait_for_ทิ้ง/` เมื่อ 2026-08-04) พบหน้า 21: Qwen จัดทุก main bar เป็น "DB" หมดทั้งที่สัญลักษณ์เป็นวงกลมเปล่า (RB) — แต่ **stirrup ที่ใช้สัญลักษณ์เดียวกัน Qwen อ่านเป็น RB ถูกทุกจุดในหน้าเดียวกัน** แปลว่าไม่ใช่ปัญหาอ่าน symbol ไม่ออก แต่เป็น bug เฉพาะจุดตรงตำแหน่ง mapping field `main_bar_type` — เป็นหลักฐานเพิ่มเติมว่า field เดียวกันอาจหลอนไม่เท่ากันในหน้าเดียวกัน ต้องเช็ค cross-consistency ในหน้าเดียวกันด้วย ไม่ใช่แค่ข้ามหน้า
7. **หน้าเดียวมีหลาย view ปนกันบ่อย** — เคยพลาดเพราะบังคับเลือก `pattern` เดียวต่อหน้า ทำให้ view ที่ 2 (เช่น "แปลนฐานราก" คนละกล่องกับ "แปลนคาน" บนหน้าเดียวกัน) หายไปเงียบๆ ไม่มี warning → แก้เป็น inventory ทุก heading ก่อนเสมอ (ดูหัวข้อ "Multi-view extraction" ด้านบน)

8. **⚠️ ห้ามยัดตัวแปร `$field` มากกว่า 1 ตัวไว้ใน `value=` ของ Text/Header tag เดียวกันใน Label Studio config — พลาดซ้ำมาแล้ว 2 ครั้ง:**
   - ครั้งที่ 1 (2 ก.ค., ใน Repeater `$items[{{idx}}].field`): อาการคือค่าตัวที่สองขึ้นเป็น "undefined" ตอน runtime — แก้โดยแยกเป็นคนละ `<Text>` ต่อตัวแปร (ดูหัวข้อ "Label Studio Cloud — King's per-page Repeater review flow" ด้านล่าง)
   - ครั้งที่ 2 (6 ก.ค., top-level task data ไม่ใช่ Repeater): อาการเปลี่ยนเป็น **import ทั้งชุดล้มเหลวทันที** ด้วย error `"<ข้อความในกล่อง>" key is expected in task data` — เกิดเพราะ value เริ่มต้นด้วย `$` แล้วมีตัวแปร/ข้อความอื่นตามมาอีก ทำให้ตัว validator ของ Label Studio เข้าใจผิดว่าทั้งสตริง (รวม `$` ตัวถัดๆ ไป) คือชื่อ field เดียวที่ต้องหาในข้อมูล
   - **กติกาที่ต้องทำตามเสมอ:** 1 tag (`<Text>`/`<Header>`) = ไม่เกิน 1 ตัวแปร `$xxx` เท่านั้น จะมีข้อความ literal ผสมได้ (เช่น `value="หน้า $png"` ใช้ได้) แต่ห้ามมี `$var1 ... $var2` สองตัวขึ้นไปในกล่องเดียวเด็ดขาด ไม่ว่าจะเป็น top-level field หรือ Repeater item field

## Activity log อัตโนมัติ (เพิ่ม 2026-07-03) — `pipeline_activity_log.json`

แยกจาก [raw_json_data_log.md](raw_json_data_log.md) (ซึ่งยังต้องเขียนมือทุกครั้งที่แก้ raw JSON ตาม rule_of_tune.md ข้อ 1 เหมือนเดิม ไม่เปลี่ยน) — อันนี้คือ log อัตโนมัติที่บันทึก**ทุกครั้งที่ script เขียนไฟล์ผลลัพธ์ใหม่** (extract/document_map) และ**ทุกครั้งที่ Claude วิเคราะห์ไฟล์ JSON ด้วยมือ**นอก pipeline

- `log_utils.py` — `log_action(file, ai_model, action, house=None, **extra)` เขียน entry ใหม่ไว้บนสุดของ `pipeline_activity_log.json` (newest-first) ถูกเรียกจาก `run_pipeline.py`/`analyze_folder.py`/`build_document_map.py` อัตโนมัติทุกครั้งที่เขียนไฟล์ output — username มาจาก env var `TRAINING_USER` หรือ OS login name
- `log_claude_analysis.py` — CLI สำหรับ Claude เรียกเองหลังวิเคราะห์ไฟล์ JSON ด้วยมือ (เช่น เทียบภาพจริงกับผล extraction แล้วแก้) `python log_claude_analysis.py <path.json> --model claude-sonnet-5 --note "..."` → บันทึก `action:"claude_manual_analysis"` ลง log เดียวกัน
- **ยังต้องเขียน [raw_json_data_log.md](raw_json_data_log.md) มือเหมือนเดิม** ถ้าการแก้นั้นเป็นการแก้ไข raw JSON ของ raw data จริง (log นี้เป็นแค่ activity trail เสริม ไม่ใช่ตัวแทนกฎ rule_of_tune.md)

## 2026-08-02 — sync `json_แก้ไขแล้ว/` กลับเข้า raw ครั้งแรกของโปรเจกต์ (362 ไฟล์)

**ทำอะไร:** เขียนทับ `rawjson_ยังไม่ได้แก้ไขโดนคน/0N<house>/*.json` **362 ไฟล์ ครบทั้ง 11 บ้าน** ด้วยเนื้อหาจาก `json_แก้ไขแล้ว/` (อีก 821 ไฟล์เหมือนเดิม ไม่ถูกแตะ) — งานนี้ค้างมาตั้งแต่บ้าน 1 ทุก entry ใน `สิ่งที่ต้องแก้.md` เคยเขียนว่า "sync ยังไม่เริ่ม"

**ทำไม:** มะขามสั่งให้บ้าน 01-11 มี format JSON เดียวกัน ("ไม่เอาเดี๋ยว C1 เดี๋ยว c-1") — งานรีวิว/ปรับรูปแบบทั้งหมดอยู่ใน `json_แก้ไขแล้ว/` ซึ่งเป็นสำเนา ถ้าไม่ sync กลับ ตัว ground truth ที่เอาไปเทรนจริงก็ยังเป็นของเดิม

**สิ่งที่ไหลกลับเข้า raw:** งานรีวิวสะสมของบ้าน 01-05 ที่เทียบภาพแบบจริงแล้ว (คานที่หาย, `additional_bars` ผิดหน้า, ตารางราคาซีรีส์ 5 สำเนา, dummy grid) + งานปรับรูปแบบทั้ง 11 บ้านของวันนั้น (pattern นอกสเปคบ้าน 07, grid master nest เข้า `grid{}`, footing merge ตามข้อ 48, บ้าน 10/11 พับ array เฉพาะกิจเข้า `elements[]` + rebar string→object, บ้าน 05 แตก `levels[]` ตาม §8, `phase_note`→`warnings[]`, **`grid_ref` สัญกรณ์เดียวกันทุกบ้าน 1,075 ค่า**)

**กระบวนการตามกฎ:** เตือน Rule 2 เต็มรูปแบบแล้ว**หยุดรอ**ก่อน มะขามอนุญาตชัดเจน · git commit `0029264` ไว้ก่อน sync (revert ได้) · เทียบรายชื่อไฟล์ก่อนเขียน (1,183 = 1,183 ไม่มีเกิน/ขาด) · สคริปต์ `json.loads()` ทุกไฟล์ก่อน copy · หลัง sync: raw parse ผ่าน **1,183/1,183**, ต่างจาก fix **0 ไฟล์**, point ref **2,007 ตัว resolve กับ grid master ครบ dangling 0** · log เต็มใน `No_touch_box/docs/raw_json_data_log.md`

**⚠️ ข้อจำกัดที่ต้องรู้ก่อนเอาไปเทรน:** บ้าน 06-11 ที่ sync เข้าไป**ผ่านเฉพาะการปรับรูปแบบ ยังไม่เคยตรวจกับภาพแบบต้นฉบับสักหน้า** — ที่ยังค้าง: `specs{}` มีแค่ 24/1,183 ไฟล์, **คานที่อาจหายในบ้าน 06-11** (บ้าน 01-05 ตอนตรวจเจอคานหายทุกหลัง 20→27/22→36/30→38/5→21), เหล็ก `หยุดที่ L/8` ในบ้าน 10/11 ที่ยังไม่ merge เข้า face ตาม §7 · รายละเอียดเต็ม `json_แก้ไขแล้ว/สิ่งที่ต้องแก้.md` ข้อ 59-62

## 2026-08-09 — แก้ `png`/`doc_page` สลับขั้วในกริดมาสเตอร์บ้าน 14-18 (5 ไฟล์)

**ทำอะไร:** แก้ 2 คีย์ `png`/`doc_page` ใน `<house>_หน้า00_gridline.json` ของบ้าน 14/15/16/17/18 จาก `png:null, doc_page:0` เป็น `png:"00", doc_page:null` — ไม่แตะ `grid{}`/`warnings[]`/field อื่นเลย

**ทำไม:** มะขามถามเปรียบเทียบบ้าน09 vs บ้าน18 ว่าทำไมรูปแบบหน้า00 ต่างกัน ตรวจทั้ง 19 ไฟล์กริดมาสเตอร์ในโปรเจกต์พบว่าบ้าน 01-13 ทั้งหมดใช้ `png:"00", doc_page:null` ตรงกัน (ตรงกับบ้าน01 ไฟล์ต้นฉบับสุดจาก 2026-07-10) แต่บ้าน 14-18 ใช้ค่าสลับขั้วกันทั้ง batch — ไม่มีใครผิดกฎเดิม เพราะ `primary_rawjson_schema.md` §2/§0.10 และ `tools/check_format.py`'s `WRAPPER` list เช็คแค่ว่าคีย์มีอยู่ ไม่เคยเช็คค่า จึงผ่าน ALL CHECKS ทั้งที่ขัดกันเอง

**ทำพร้อมกัน:** ปักค่า canonical ไว้ใน `primary_rawjson_schema.md` §2 (ย่อหน้าใหม่ "Grid-master `png`/`doc_page` convention") กันบ้านหลังถัดไป drift ซ้ำ — log ใน `primary_rawjson_schema_edit_log.md` และ `raw_json_data_log.md` (แถว 2026-08-09 (2)/(3)) ตามกฎข้อ 3/7

**กระบวนการตามกฎ:** เตือน Rule 2 ก่อนถามมะขาม (บอกผลกระทบ fine-tuning) → มะขามอนุมัติ "แก้เลย แต่ให้ยึดรูปแบบตามบ้าน01เป็นหลักได้ไหม" → เช็ค `git status` ก่อนแก้ไม่มีงานค้างอื่น → แก้ 5 ไฟล์ + ปักสเปค + log ครบ 3 จุด

**ตามด้วยรอบที่ 2 วันเดียวกัน — บ้าน 01-05 เปลี่ยน `note`→`view_title` + เพิ่ม `building:null`:** มะขามสั่งให้ตรวจบ้าน 01-11 ทั้งชุดให้ "รูปแบบเดียวกัน" ต่อ — พบว่า `png`/`doc_page` ตรงกันอยู่แล้ว (ไม่ต้องแก้) แต่บ้าน 01-05 ยังใช้คีย์ `note` (ไม่มี `building`) ขณะที่บ้าน 06-11 ใช้ `view_title` + มี `building` — **ต่างจากเคส png/doc_page ตรงที่นี่คือวิวัฒนาการสเปคจริงตามเวลา** (`building` เพิ่มเข้าสเปคจริงวันที่ 2026-07-25 รองรับบ้าน06 ที่มี 2 อาคาร บ้าน 01-05 ทำก่อนหน้านั้นจึงไม่มี field นี้โดยธรรมชาติ ไม่ใช่ทำตกหล่น) — หยุดถามมะขามก่อนแก้ด้วย `AskUserQuestion` แทนที่จะเดาเอง เพราะเปลี่ยนแล้วเท่ากับเขียนประวัติศาสตร์ไฟล์เก่าให้ดูเหมือนทำด้วยสเปคที่ตอนนั้นยังไม่มีจริง — มะขามเลือกให้เปลี่ยนตาม (consistency เหนือ historical accuracy สำหรับ 2 field นี้) ขอบเขตจำกัดเฉพาะ `note`→`view_title` + `building:null` เท่านั้น ไม่แตะ `sheet_name`/`schema_generation`/`dummy_grid_rule_check_2026-07-08` ที่ยังต่างกันอยู่ · `python tools/check_format.py` ทั้ง 5 บ้าน = ALL CHECKS PASS · log เต็มใน `raw_json_data_log.md` แถว 2026-08-09 (4)

## 2026-08-09 (2) — สาเหตุจริงของ pattern ไม่ตรงกัน: `check_format.py` เช็คลมเงียบๆ เมื่อได้ path ผิด (แก้แล้ว)

**อาการที่พบ:** `python tools/check_format.py` (สแกนทั้งโปรเจกต์) เจอ 13 จุดที่ผิดสเปคจริง — บ้าน 15 มี `pattern: "detail_view"` 7 ไฟล์ (หน้า11-16, 18 — ควรเป็น `section` ตาม §0.9 "a detail sheet is section") + `tie_bar` (ควรเป็น `stirrup`) 2 ไฟล์ (หน้า19, 23); บ้าน 18 มี `pattern: "elevation"` 4 ไฟล์ (หน้า09-12 — ควรเป็น `side_profile`) แต่ log ของทั้ง 2 บ้านตอนทำเสร็จกลับบันทึกไว้ว่า "ALL CHECKS PASS" ทั้งคู่

**สาเหตุจริง (สืบจนเจอ ไม่ใช่เดา):** `tools/check_format.py`'s `main()` รับ path จาก `argv[1:]` ตรงๆ ไม่เช็คว่า path นั้นมีอยู่จริงหรือมีไฟล์ `.json` อยู่ข้างในไหม — log ของบ้าน 12/13/14/15/16/17/18 **ทุกบ้านบันทึกคำสั่งแบบเดียวกัน**: `python tools/check_format.py 15บ้าน_ใหญ่_2ชั้น_03` (ชื่อโฟลเดอร์เปล่าๆ ไม่มี prefix `rawjson_ยังไม่ได้แก้ไขโดนคน/`) — path นี้ไม่มีอยู่จริงจาก repo root, `glob.glob()` จึงคืน list ว่าง, loop ไม่ทำงานเลย, ไม่มี fail ไหนถูกบันทึก → พิมพ์ "ALL CHECKS PASS" ทั้งที่**ไม่ได้เช็คไฟล์แม้แต่ไฟล์เดียว** — reproduce ได้จริง (`python tools/check_format.py 15บ้าน_ใหญ่_2ชั้น_03` จาก repo root ให้ "checked 1 house folder(s)" + "ALL CHECKS PASS" แม้โฟลเดอร์นั้นไม่มีอยู่จริงที่ path นั้น) เทียบกับรันด้วย path เต็มที่ถูกต้องซึ่งเจอ 9 จุดผิดในบ้าน 15 ทันที **`pattern:'elevation'` คือความผิดพลาดเดิมที่บ้าน 07 เคยทำมาก่อนแล้ว** (สเปค §0.9 บันทึกไว้เป็นตัวอย่างเตือนอยู่แล้ว: "House 07 invented detail, diagram and elevation and needed 21 files remapped") — เกิดซ้ำเพราะตัวเช็คที่ควรจับได้ไม่เคยรันจริง ไม่ใช่เพราะสเปคไม่ได้เตือน

**แก้แล้ว (root-cause fix ที่ตัว checker ไม่ใช่แค่สอนคนพิมพ์ path ให้ถูก):** `main()` ตอนนี้เช็คว่าทุก target ที่รับมาจาก argv มีอยู่จริงและมีไฟล์ `.json` อยู่ข้างในก่อนเริ่มเช็ค — ถ้าไม่ใช่ พิมพ์ error ชัดเจนพร้อมคำใบ้เรื่อง prefix ที่ขาด แล้ว exit 1 ทันที (ไม่ใช่ exit 0 เงียบๆ) verify แล้วว่า reproduce บั๊กเดิมไม่ได้อีกต่อไป (คำสั่งเดียวกับที่เคยให้ false pass ตอนนี้ error ชัดเจน) และคำสั่งที่ถูกต้อง (มี prefix / ไม่ใส่ argument เลย) ยังทำงานปกติเหมือนเดิม

**ยังไม่ได้แก้ (แยกเป็นคนละงาน เพราะเป็นการแก้ raw JSON จริง ต้องขออนุญาตตามกฎข้อ 1 ก่อน):** 13 จุดที่ผิดจริงในบ้าน 15/18 (11 pattern + 2 tie_bar) ยังคงอยู่ในไฟล์ ยังไม่ถูกแก้

## สิ่งที่ยังไม่ได้ทำ (ทำต่อได้)

- **Label Studio review flow** — มี 2 แบบขนานกันตอนนี้ (ดูหัวข้อ "Label Studio Cloud" ด้านล่าง): (1) whole-JSON ต่อบ้าน project "Constistant01" (2) per-page Repeater ต่อรายการ project "Structural Review"/"BOQ Review" ตามแผน King — ทั้งคู่ยังไม่ publish/เชิญคนจริง
- **Extraction ยังไม่ครบทุกบ้าน** — 5/9 บ้าน (บ้าน_เล็ก ทั้งหมด) มี qwen-output แล้ว รวม BOQ ด้วย, เหลือ 4 บ้าน_ใหญ่ ยังไม่ได้รัน `run_pipeline.py`
- **Confidence/trust scoring 3 ชั้น** (ออกแบบไว้ในบทสนทนา ยังไม่ implement เป็นโค้ด):
  - ชั้น 1: model confidence (ไม่น่าเชื่อถือเดี่ยวๆ ตามข้อ 3 ด้านบน)
  - ชั้น 2: human confidence จาก Label Studio — เก็บ `reviewer_level` (junior/mid/senior/expert) + `human_confidence` (sure/fairly/unsure)
  - ชั้น 3: trust weight รวม (expert+sure = gold/1.0 ... junior+unsure = escalate ให้ senior ตรวจซ้ำ, ไม่เอาเข้า training ตรงๆ)
- **Fine-tuning dataset export** (JSONL รวม image+prompt+ground-truth) — ยังไม่มีสคริปต์ประกอบจาก `raw/image/<house>/qwen-output/` + reviewed data
- **Architectural extraction** — ตอนนี้ scope ล็อกเฉพาะ structural (ตามที่ตกลงกันไว้) ถ้าต้องการ floor_area จาก arch plan ต้องเพิ่ม pattern ใหม่

## Key files

| ไฟล์ | หน้าที่ |
|---|---|
| `run_pipeline.py` | **entry point หลัก** — Stage 0 → route → extract ทั้งโฟลเดอร์ |
| `build_document_map.py` | Stage 0 — อ่านสารบัญ, หา offset, สร้าง document map |
| `analyze_folder.py` | fallback per-page classify (ใช้เมื่อไม่มีสารบัญ) |
| `Prompt/stage-*/prompt.md` | เอกสารอ้างอิง prompt (source of truth จริงคือ string ในไฟล์ `.py`) |
| `raw/image/<house>/qwen-output/` | ผลลัพธ์ — `_document_map.json`, `_run_summary.json`, `<house>_หน้าNN.json` (อยู่ใต้โฟลเดอร์รูปของบ้านนั้นๆ เลย ดึงไป assign Label Studio ต่อบ้านได้ง่าย) |
| `SETUP.md` | วิธี setup ครั้งแรกใน repo ใหม่ |
| `log_utils.py` / `log_claude_analysis.py` / `pipeline_activity_log.json` | Activity log อัตโนมัติ (ดูหัวข้อ "Activity log อัตโนมัติ" ด้านบน) — แยกจาก `raw_json_data_log.md` |

## Label Studio Cloud — review flow (เริ่มใช้จริง 2026-07-02)

**Hosting:** ใช้ **Label Studio Cloud** (`app.heartex.com`, Starter Cloud trial) ไม่ใช่ self-host — เพื่อนทีมเข้าออนไลน์ได้ทันทีไม่ต้อง tunnel/deploy เอง

**Image hosting:** repo `Training` (github.com/whysaomaitrongbaab-collab/Training) เป็น **public** → ใช้ **`raw.githubusercontent.com` URL ตรงๆ** เป็น image source ของ Label Studio ได้เลย ไม่ต้องอัปโหลดรูปเข้า Supabase Storage หรือที่อื่น (ทดสอบแล้ว: URL ที่ generate resolve ได้ HTTP 200 จริง) — รูปอยู่ที่ root-level `image/<house>/*.png` (ไม่ใช่ `No_touch_box/raw/image/` ซึ่งมีแค่ 1 บ้านและเป็น path เก่าที่ scripts รุ่นก่อนอ้างผิด)

**Task/config ที่ใช้จริง:**
- `node label-studio-tasks-github.js` → อ่านทุกโฟลเดอร์ใน root `image/` → 1 task ต่อ 1 บ้าน, `data.images` = list ของ GitHub raw URL (encode ชื่อไทย/เว้นวรรคให้ถูกต้องแล้ว), แนบ `predictions` จาก `qwen-output/<house>-qwen.json` ถ้ามีไฟล์นั้นอยู่ (ตอนนี้ยังไม่มีเลยสักบ้าน → ทุก task ยังไม่มี pre-annotation)
- ผลลัพธ์: `label-studio-tasks-github.json` — import เข้า Label Studio ผ่าน Data Import → Upload Files (รองรับ JSON ตรงๆ)
- Labeling Interface ใช้ `label-studio-config-review.xml`: `<Image name="page" value="$images" valueType="list">` (โชว์ทุกหน้าของบ้านเป็น gallery) + `<TextArea name="corrected_json" toName="page">` (ให้พิมพ์/แก้ JSON ที่ถูกต้อง) + `<TextArea name="reviewer_note" toName="page">`

**สถานะปัจจุบัน:** สร้าง project "Constistant01" บน Label Studio Cloud สำเร็จ, import ครบ 9 tasks (9 บ้าน) แล้ว, สถานะ "Ready to Publish" — **ยังไม่ได้กด Publish และยังไม่ได้เชิญสมาชิก**

**ข้อมูลไม่ sync กลับอัตโนมัติ** — ตอนเพื่อน submit annotation ใน Label Studio Cloud ข้อมูลอยู่ในฐานข้อมูลของ Label Studio เท่านั้น ต้อง**ทำมือ**ทุกครั้ง:
1. Export จาก Label Studio (Project → Export → JSON)
2. `node label-studio-import-annotations.js <path-to-export.json>` → ได้ `annotated/*.json` + `manifest.json` อัปเดต
3. commit/push เข้า repo เอง

(ยังไม่ได้ตั้ง webhook ให้ sync อัตโนมัติ — ถ้าจะทำต้องมี server รับ webhook ก่อน)

**สิ่งที่ยังไม่ได้ทำต่อ:**
- Publish project + เชิญเพื่อนเข้า project "Constistant01" (ไม่ใช่แค่ invite เข้า organization)
- `label-studio-tasks-github.js` ยังหา `qwen-output/<house>-qwen.json` (ไฟล์รวมทั้งบ้าน) ไม่เจอเลย เพราะข้อมูลจริงที่มีตอนนี้เป็นไฟล์ **ต่อหน้า** ไม่ใช่ไฟล์รวม — ถ้าจะใช้ flow นี้ต่อ (whole-JSON ต่อบ้าน) ต้องเขียน merge script ก่อน; **แนะนำใช้ flow per-page Repeater ด้านล่างแทน** เพราะอ่านไฟล์ต่อหน้าที่มีจริงได้ตรงๆ ไม่ต้อง merge

## Label Studio Cloud — King's per-page Repeater review flow (2026-07-02, รอบ 2)

**ต่างจาก flow ด้านบนตรงไหน:** ด้านบนคือ 1 task = 1 บ้าน (ทุกหน้า) + กล่อง JSON เต็มก้อนให้พิมพ์ทับ — อันนี้คือ **1 task = 1 หน้า** + field แยกทีละรายการให้แก้ (ตามแผนที่ King ร่างไว้แต่เดิม, ปรับมาใช้ hosting เดียวกัน: Label Studio Cloud + GitHub raw URL จาก repo `Training` เท่านั้น ไม่ใช้ Supabase Storage ตามที่ King เสนอไว้ตอนแรก)

**Pipeline สร้าง task:**
```
node label-studio-tasks-perpage.js
  → อ่าน raw/image/<house>/qwen-output/<house>_หน้าNN.json ของทุกบ้านที่มี extraction แล้ว (5/9 บ้านตอนนี้)
  → discipline structural (pattern plan/section/schedule, ข้าม notes) → flatten เป็น items[] → label-studio-tasks-structural.json
  → discipline boq (categories[].items[])                              → flatten เป็น items[] → label-studio-tasks-boq.json
```

**Field ที่แก้ได้จริงใน UI (v3 — ลดลงจากตอนแรก):**
- Structural: `element_id, element_type, count, grid_refs, span_length_m, main_bar_dia_mm, stirrup_dia_mm, stirrup_spacing_mm` (8 ช่อง — เลือกเฉพาะจุดที่บทเรียนข้อ 2 ด้านบนบอกว่า AI มักพลาด) ส่วน `width_mm/height_mm/main_bar_count/main_bar_type/stirrup_type/concrete_grade/steel_grade` โชว์เป็นบรรทัดอ่านอย่างเดียว ไม่มีกล่องแก้ (แต่ยัง carry-over ค่าจาก AI เข้า output เสมอ ไม่ได้หายไป)
- BOQ: `item_no, description, quantity, unit` (4 ช่อง) ส่วนราคาต่างๆ (ยังเป็น null เกือบทุกแถวเพราะ extraction รอบนี้ไม่มีข้อมูลราคา) โชว์อ่านอย่างเดียว
- ทุกรายการมี checkbox "❌ ลบรายการนี้ (AI มโน)" แทนการลบจริง — ตอน import จะกรองแถวที่ติ๊กออกทิ้ง
- ไม่มีปุ่ม "+เพิ่มรายการ" (Label Studio Repeater ไม่รองรับ add/remove แถวจาก UI จริง — เช็คจากเอกสารทางการแล้ว) แทนที่ด้วยกล่อง `reviewer_note` ท้าย task ให้พิมพ์อธิบายเป็นคำพูดธรรมดาว่าขาดอะไร แล้วไปแก้ไฟล์ JSON ต้นทางเองทีหลัง

**⚠️ ความไม่แน่นอนที่ยังไม่ได้ verify กับเอกสารทางการ:** ตอนเขียน `label-studio-structural.xml`/`label-studio-boq.xml` ดึงเอกสาร Repeater tag ของ Label Studio มาเช็คไม่สำเร็จ (เว็บ error ซ้ำๆ) ใช้ syntax `on="$items"` + `{{idx}}` + `$items[{{idx}}].field` จากความรู้เดิม ทดสอบจริงใน Label Studio Cloud แล้วพบว่า**ใช้งานได้จริง** (เห็นค่าจริงในกล่องถูกต้อง) แต่เจอบั๊กเล็ก: ยัดหลายตัวแปรในกล่อง `<Text>` เดียวกันทำให้ตัวที่สองขึ้นคำว่า "undefined" — แก้แล้วโดยแยกเป็นคนละ `<Text>` ต่อตัวแปร

**สถานะปัจจุบัน:** สร้าง project "Structural Review" + "BOQ Review" บน Label Studio Cloud แล้ว, import task JSON แล้ว, ผ่านการทดสอบ Repeater รอบแรก (v1 ไม่มี label กำกับ → v2 เพิ่ม label → v3 ลดจำนวนช่องแก้) — **รอ user ทดสอบ v3 ล่าสุดในเบราว์เซอร์อีกรอบ** ก่อน publish/เชิญเพื่อน

## Label Studio Cloud — Makham's Pattern (Gen 3) review flow (2026-07-06)

**ต่างจาก 2 flow ด้านบน:** ทั้งคู่ยังอิง Gen 1 schema (`plan[]/section[]/schedule[]` flat, หรือ `categories[].items[]`) อ่านจาก `raw/image/<house>/qwen-output/`. Flow นี้อิง **Gen 3 ("Makham's Pattern", เอกสารเต็มอยู่ที่ [`Makham's patter of rawjson20260705.md`](../wait_for_ทิ้ง/No_touch_box/docs/Makham's%20patter%20of%20rawjson20260705.md), ย้ายเข้า `wait_for_ทิ้ง/` เมื่อ 2026-08-04)** อ่านจาก `No_touch_box/mk_test/<subfolder>/*.json` — ผลลัพธ์ fresh-extraction ทดสอบจริงของบ้าน_เล็ก_1ชั้น_01 หน้า 1-40+48-60 (`mk_test/t1/` = รอบแรก) และหน้า 1-37 (`mk_test/t2/` = รอบสอง หลังปรับ schema)

**จุดต่างสำคัญจาก Gen 1:** หน้าที่มีหลาย pattern ปนกันถูกแยกเป็นคนละไฟล์ตั้งแต่ตอน extract แล้ว (ไม่ต้องรวม `plan+section+schedule` ในหน้าเดียวแบบเดิม) — 1 ไฟล์ = 1 pattern/view เสมอ ทำให้ task generator ง่ายขึ้น (ไม่ต้อง merge หลาย array ต่อหน้า)

**Task generator:** `node label-studio-tasks-makham.js <house> [subfolder=t2]`
- จัดกลุ่มไฟล์เป็น 3 กลุ่มตาม**โครงสร้างจริง** (ไม่ใช่แค่ field `pattern`) เพราะพบว่า agent ต่างตัวเขียน field ไม่ตรงกันเป๊ะ (เช่น `บ้าน_เล็ก_1ชั้น_01_หน้า29_floor_plan.json` ใน `t2/` ใช้ key `elements` พหูพจน์ ทั้งที่ spec เดิมใช้ `element` เอกพจน์) — script เช็คทั้ง `element`/`elements` เป็น fallback:
  - **elements** (มี array `element`/`elements`) → `label-studio-tasks-makham-elements.json` (ใช้กับ pattern plan/section/schedule/site_plan/site_profile)
  - **material_list** (มี `categories[].items[]`) → `label-studio-tasks-makham-material_list.json`
  - **single** (ที่เหลือ: notes/gridline/unknown/index) → `label-studio-tasks-makham-single.json` (รีวิวเป็น JSON block เดียว ไม่ใช่ Repeater เพราะเป็น object เดี่ยวหรือ list สั้นๆ)
- ไฟล์ grid master (`png:"00"`, เช่น `_หน้า00_gridline.json`) ถูกข้าม (skip) จาก flow นี้เสมอ — รีวิวแยกด้วยตาเพราะเป็นไฟล์สังเคราะห์ข้ามหน้า ไม่ใช่หน้าจริง
- field ที่หายไปนอกเหนือจาก core fields (เช่น `pile{}` ของ footing, `dowel_bar{}`/`topping_mesh{}` ของ precast_plank_detail, `additional_bars[]`, `level`) ถูกเก็บรวมเป็น `other_fields_json` (อ่านอย่างเดียว) ไม่ให้หายไปเงียบๆ ตามกฎ rule_of_tune ข้อ 3

**Labeling Interface:**
- `label-studio-makham-elements.xml` — Repeater, มี field ใหม่ `span_source` (Choices: grid_table/local_dimension/unresolved/n/a) ที่ schema เดิมไม่มี, field เสี่ยงผิด (main_bar/stirrup แยก count/dia/type ทั้งคู่) แก้ได้, field อื่นๆ โชว์เป็น `other_fields_json` อ่านอย่างเดียว
- `label-studio-makham-material_list.xml` — Repeater เดิมสไตล์เดียวกับ `label-studio-boq.xml` เก่า
- `label-studio-makham-single.xml` — ไม่ใช้ Repeater, โชว์ JSON เต็มก้อนใน `TextArea` แก้ทับได้ (แบบเดียวกับ flow "Constistant01" เดิม) + `Choices` สถานะ approved/corrected/reject

**สถานะปัจจุบัน:** สร้าง script + 3 XML config แล้ว, รันกับ `mk_test/t2/` ของ บ้าน_เล็ก_1ชั้น_01 สำเร็จ (33 elements task, 1 material_list task, 22 single task) — **ยังไม่ได้ import เข้า Label Studio Cloud จริง/สร้าง project ใหม่/publish**

## Convention

- ชื่อ output JSON = ชื่อไฟล์รูป 1:1 (แค่เปลี่ยนนามสกุล) — เปิดคู่กันได้ทันทีไม่ต้องพึ่ง manifest
- Field ของ element ผูกกับ schema ของ repo หลัก (`js/shared/schema.js` → `createBeamLibraryEntry`/`createDrawingElement`) เผื่อย้อนกลับไป wire เข้า pipeline หลักภายหลัง — ชื่อ field ควรตรงกันไว้แม้ repo นี้จะแยกออกมา
