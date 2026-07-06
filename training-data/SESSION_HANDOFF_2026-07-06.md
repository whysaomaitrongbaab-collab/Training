# Session Handoff — 2026-07-06

เขียนไว้ให้ Claude session ใหม่ (หรือมะขามเอง) อ่านต่อได้ทันทีโดยไม่ต้องไล่ chat history เก่า — เขียนขึ้นระหว่างเซสชันตามคำสั่งมะขาม ("หาก usage ของ Claude ใกล้หมดให้ตั้งเป็นไฟล์ md ทดไว้เตรียมทำงานต่อ") เผื่อ session ถูกตัดกลางคัน

> ⚠️ **อ่าน [rule_of_tune.md](rule_of_tune.md) ก่อนทำอะไรทั้งนั้น** — ไม่มีข้อยกเว้น
>
> ⚠️ **เอกสารสคีมาเต็ม (Makham's Pattern Gen 3, ทุกเวอร์ชัน 3.1/3.2/3.3) อยู่คนละ repo:**
> `C:\00mk\steel project\งานสมบูรณ์\Constistant\mk's stuff\Makham's patter of rawjson20260705.md`
> (ย้ายมาจาก repo Training ตั้งแต่ 5 ก.ค. — path เดิมใน repo Training **ไม่มีไฟล์นี้แล้ว**)
>
> ⚠️ **บันทึกงานละเอียดเป็นรายชั่วโมงอยู่ที่ workmen's_diary ของ repo Constistant** (คนละ repo กับ Training):
> `C:\00mk\steel project\งานสมบูรณ์\Constistant\workmen's_diary\2026-07-05.md` และ `2026-07-06.md`
> ไฟล์นี้ (SESSION_HANDOFF) เป็นแค่สรุปภาพรวมสั้นๆ ให้เริ่มงานเร็ว — รายละเอียดจริงทุกจุดอยู่ใน workmen's_diary

## ภาพรวมโปรเจกต์

Pipeline สร้าง fine-tuning dataset ให้ Qwen-VL อ่านแบบก่อสร้าง RC (คอนกรีตเสริมเหล็ก) ของไทยแม่นขึ้น มี 2 repo:
- **Constistant** (`c:\00mk\steel project\งานสมบูรณ์\Constistant`) — แอปหลัก (SteelCalc), มี `mk's stuff/` เก็บเอกสาร schema design และ `workmen's_diary/` เก็บ log งานละเอียด
- **Training** (`c:\00mk\steel project\training\Training`, github.com/whysaomaitrongbaab-collab/Training) — repo ที่ทำงานจริง มี `training-data/` เก็บ script/config/ผลลัพธ์ extraction ทั้งหมด

## สถานะ schema (Makham's Pattern) — ล่าสุดคือ Generation 3.3

- **Gen 1** (เดิม, `qwen-output/`) — flat pattern, ยังเป็น ground truth ของจริงที่ 5 บ้านแรกใช้อยู่
- **Gen 2** (`claude_output_03/`, draft ของ King, ไม่ใช่ ground truth) — `views[]`, atomic beam segment, `span_source` — **แหล่งอ้างอิงสำคัญที่ Gen 3 เอามาปรับใช้เยอะ**
- **Gen 3** (Makham's Pattern, ออกแบบ 5 ก.ค., ทดสอบจริง 6 ก.ค.) — 9+1 pattern type (plan/section/schedule/notes/index/material_list/site_plan/site_profile/gridline/unknown), 1 ไฟล์ = 1 pattern/view เสมอ (แยกไฟล์ตั้งแต่ extract)
  - **3.1** (6 ก.ค. เช้า): เพิ่ม `span_source`, atomic beam segment, `slab` element_type ครอบคลุม SO/SI/SX/ST, บทเรียน Ø=RB เสมอ (ห้ามอนุมานจากขนาดเส้นผ่านศูนย์กลาง), เปิดคำถาม 4 ข้อที่ยังไม่ตัดสินใจ (ดูด้านล่าง)
  - **3.2** (6 ก.ค. บ่าย): Dummy grid convention (prime notation `1'`,`A'`,`A''`) + ไฟล์กริดกลาง "หน้า 0" (`<house>_หน้า00_gridline.json`)
  - **3.3** (6 ก.ค. เย็น): Join สเปคหน้าตัดคาน (`width_mm/height_mm/main_bar{}/stirrup{}/additional_bars[]`) เข้า `plan` beam element โดยตรงจาก `section` ด้วย `element_id` — ไม่รอ join ตอน assembly time อีกต่อไป

### ❓ 4 คำถามเปิดจาก Gen 3.1 — ยังไม่ได้ถามมะขามโดยตรง ยังค้างอยู่
1. เหล็กบน-ล่างไม่เท่ากัน (asymmetric main_bar เช่น B5 = 2บน+3ล่าง) — จะแยก `main_bar.top{}`/`main_bar.bottom{}` ไหม หรือเก็บรวมแบบปัจจุบัน
2. `additional_bars[]` (เหล็กหยุดกลางคาน L/8) ที่ออกแบบเองดีกว่า Gen 2 — ยังไม่ได้ยืนยันเป็นทางการว่ารับเข้า spec ถาวร
3. ตารางเสาหลายระดับ (เช่น C1 มี 2 สเปคตามชั้น) — ใช้ field `level` แยก (แนวทางที่ใช้อยู่) หรือฝัง level ใน element_id แบบ Gen 2
4. Precast plank detail ต้องการ field เฉพาะ (`dowel_bar{}`/`topping_mesh{}`/`topping_thickness_min_mm`/`level_step_mm`) แทนการยืม main_bar/stirrup — เสนอไว้แล้วแต่ยังไม่ยืนยัน

## สถานะ mk_test/ (ผลลัพธ์ extraction จริงของ บ้าน_เล็ก_1ชั้น_01)

`training-data/mk_test/` ตอนนี้แบ่งเป็น 2 รอบทดสอบ (มะขามจัดเข้าโฟลเดอร์เองแล้ว):
- **`t1/`** — รอบแรก fresh-extraction หน้า 1-60 (ยกเว้น 41-47 BOQ ที่ยังไม่เสร็จ) ใช้ Gen 3 ดั้งเดิม (ก่อน 3.1)
- **`t2/`** — รอบสอง fresh-extraction หน้า 1-37 เท่านั้น (**ไม่รวม BOQ 38-47/48-60**) ใช้ Gen 3.1+3.2+3.3 ล่าสุด — **นี่คือชุดข้อมูลที่ควรใช้อ้างอิงต่อไป** (t1 เป็นแค่ baseline เปรียบเทียบ)
  - ไฟล์กริดกลาง: `t2/บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json`
  - หน้า 19 (view2 beam plan) และหน้า 20 (view1 tie beam plan) — join สเปคคานเข้าแล้วตาม Gen 3.3

### ⚠️ ปัญหาที่ยังไม่ได้ชี้ขาด
1. **concrete_grade ขัดแย้ง 210 vs 240 ksc** — อ่านสดจากหน้า 18 (S-01 notes) ได้ 210 ksc ชัดเจน แต่ Gen 1 เดิมบันทึกไว้ 240 ksc — ยังไม่ได้ตรวจสอบว่าอันไหนถูก (`concrete_grade` ใน beam element ทุกตัวเลยเป็น `null` ไปก่อน ไม่เดา)
2. **grid_ref บนหน้า MEP (29/35/36/37) ขัดแย้งกันเอง** — agent รอบ t1 บอกว่าเป็น free text ทั่วไป, agent รอบ t2 (อ่านอิสระ) บอกว่าตรงกับกริดโครงสร้างจริงของบ้าน (รวม dummy grid ที่ page00 master สร้างไว้) เป๊ะ — แนวโน้มเชื่อ t2 มากกว่า แต่ยังไม่ฟันธง
3. **หน้า 41-47 (BOQ ฐานรากแผ่)** ยังไม่ได้ extract เลยทั้ง t1 (ทำได้แค่ 38-40) และ t2 (ไม่อยู่ใน scope รอบนี้)
4. **Slab marker (SO/SI/ST/SX) ยังไม่ join สเปคจากหน้า 23** — ทำแค่คานตาม Gen 3.3 (มะขามสั่งเฉพาะคาน)
5. ไฟล์เปล่า 0 ไบต์ที่ path เดิมใน repo Training (`training-data/Makham's patter of rawjson20260705.md`) — เกิดจาก IDE สร้างขึ้นเองตอนเปิด path ที่ไม่มีไฟล์แล้ว ยังไม่ได้รับคำยืนยันจากมะขามว่าจะลบไหม

## สถานะ Label Studio (Gen 3 flow ใหม่ — คนละชุดกับ flow Gen 1 เดิม)

ไฟล์ทั้งหมดอยู่ที่ `training-data/` root:
- **Generator:** `label-studio-tasks-makham.js` — `node label-studio-tasks-makham.js <house> [subfolder=t2] [discipline]`
  - รองรับทั้ง `element`/`elements` key (schema drift ระหว่าง agent), sort items ตาม `element_id` (จัดกลุ่ม mark เดียวกันติดกัน), format `grid_ref_display` ให้อ่านง่าย (`"{D1D2,4}"` → `"D1 → D2 (ยาว 4 ม.)"`)
- **Config (3 pattern group x 2 freeze direction = ยังไม่ครบทุก combo):**
  - `label-studio-makham-elements.xml` (freeze-left, default) / `-elements-freezeR.xml` (freeze-right)
  - `label-studio-makham-material_list.xml` (sticky-top เดิม ยังไม่ได้ทำ freeze — ไม่จำเป็นสำหรับ scope structural)
  - `label-studio-makham-single.xml` (freeze-left) / `-single-freezeR.xml` (freeze-right)
- **Task JSON ที่ generate ไว้แล้ว (scope structural, ล่าสุดหลัง Gen 3.3 join):**
  - `label-studio-tasks-makham-elements-structural.json` (10 tasks: หน้า 19,20,21,22,23,24,25)
  - `label-studio-tasks-makham-single-structural.json` (2 tasks: หน้า18 notes+index)
  - (material_list-structural มี 0 task — ไม่ต้องใช้)
- **⚠️ บั๊กสำคัญที่แก้แล้ว (6 ก.ค. ค่ำ) — อย่าพลาดซ้ำเป็นครั้งที่ 3:** ห้ามยัดตัวแปร `$field` มากกว่า 1 ตัวไว้ใน `value=` ของ `<Text>`/`<Header>` เดียวกันเด็ดขาด (เคยพลาดมาแล้วรอบหนึ่งกับ Repeater item ตอน 2 ก.ค. — คราวนี้พลาดซ้ำกับ top-level field ตอน 6 ก.ค. ทำให้ Label Studio import task ทั้งชุดล้มเหลวด้วย error `"..." key is expected in task data`) — แก้แล้วทั้ง 5 ไฟล์ XML (แยกเป็นคนละ `<Text>` ต่อ 1 ตัวแปร) ดูรายละเอียดเต็มที่ `training-data/CLAUDE.md` หัวข้อ "บทเรียนสำคัญ" ข้อ 8 — **ถ้าจะแก้/เพิ่ม field ใน XML config เหล่านี้ต่อ ต้องเช็คกฎนี้ทุกครั้ง**
- **ยังไม่ได้ทำ:** สร้าง project จริงใน Label Studio Cloud (มะขามสร้างไว้แล้ว 1 อัน "structural Review t2" แต่ยัง import ไม่ผ่านเพราะบั๊กข้างต้น — ต้อง paste XML ที่แก้แล้วเข้า Labeling Interface ก่อน แล้วค่อย import ใหม่), ทดสอบ UI, publish, เขียน `label-studio-import-*.js` ฝั่งรับผล export กลับ (แปลงเป็น `annotated/*.json`)

## ทำต่อยังไงใน 3 ชม. ข้างหน้า (ลำดับที่แนะนำ)

1. ถ้ามะขามยังไม่ได้ทดสอบ layout ใหม่ (freeze-left, grid_ref_display, grouping) ใน Label Studio Cloud จริง — ให้ทดสอบก่อน แล้วแจ้งปัญหาถ้ามี
2. ตัดสินใจ 4 คำถามเปิดของ Gen 3.1 (ดูหัวข้อด้านบน) จะช่วยให้ schema นิ่งพอจะ scale ไปบ้านอื่น
3. ตรวจสอบ concrete_grade 210 vs 240 ksc ให้ชัวร์ (ดูภาพหน้า 18 อีกรอบ หรือถามคนมีแบบต้นฉบับ)
4. ตัดสินใจข้อขัดแย้ง grid_ref บนหน้า MEP (t1 vs t2)
5. Extract หน้า 41-47 (BOQ ฐานรากแผ่) ให้ครบ (ยังไม่ได้ทำเลยทั้ง 2 รอบ)
6. ถ้า schema นิ่งแล้ว: สร้าง Label Studio project จริง + import + publish + เชิญเพื่อน
7. เขียน import script ฝั่งรับผลกลับจาก Label Studio Gen 3 (คู่กับ `label-studio-tasks-makham.js`)
