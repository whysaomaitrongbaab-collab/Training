# Pipeline ทุก pass ตั้งแต่ต้นจนจบ — 1 pass 1 แผนภาพ

สถานะ 27 พ.ย. 2569 · เรียงตามลำดับที่ไฟล์แบบวิ่งผ่านจริง · เลข pass ตามชุด `../mermaid_21พย2569/` (ชุดนั้นมีแผนภาพละเอียดหลายรูปของ Pass 1, 3, 4) · "ส่วน N" = 5 ส่วนของคิง (ประชุม 19 พ.ย.) · เจ้าของงานตามที่แบ่งในประชุม 25 พ.ย.
สี: 🟩 ทำแล้วและวัดแล้ว · 🟨 ทำบางส่วน / ยังไม่ได้วัดกับงานจริง · 🟥 ยังไม่ได้ทำ · 🟦 ข้อเสนอ หรือตั้งใจให้โมเดล t07 (ยังไม่เทรน)

| Pass | ทำอะไร | ส่วนของคิง | เจ้าของ | สถานะโดยรวม |
|---|---|---|---|---|
| 0 | เตรียมไฟล์: ชนิดหน้า + ทิศหน้า | ส่วน 1 | มะขาม | 🟩 หน้าเวกเตอร์ · 🟨 หน้าสแกน |
| 1 | กรอบชื่อแบบ → รหัสแผ่น / ชื่อแผ่นต่อหน้า (+ สารบัญ) | ส่วน 1 | มะขาม | 🟩 รหัสแผ่น · 🟨 สารบัญ |
| 2 | ประเภทงานก่อสร้าง | ส่วน 2 | ข้อเสนอของมะขาม รอทีมตัดสิน | 🟦 |
| 3 | เส้นกริด (แนวนอน) + ระดับ (แนวตั้ง) → Proj. Grid DB | ส่วน 3 | มะขาม | 🟩 หน้าเวกเตอร์ · 🟥 หน้าสแกน · 🟥 เส้น dummy |
| 4 | หา element: GT / SM / SS และ SP | ส่วน 4 | เมล + มะขาม (GT/SM/SS) · โซน + อิม (SP, overlay) | 🟨 |
| 5 | Matching: รวมทุกฐานข้อมูล → Constistant | ส่วน 5 | ยังไม่ได้แบ่ง | 🟥 ฝั่งรวม · 🟩 ฝั่ง Constistant ที่รับ |

---

## Pass 0 — เตรียมไฟล์: ชนิดหน้า + ทิศหน้า (ส่วน 1)

โค้ด: `tools/page_orient.py` · `tools/vector_raster_list.py` · ชนิดหน้า `page_info` (ตัวรันใน `tools/`)

```mermaid
flowchart TD
  IN["drawing.pdf ทั้งเล่ม"] --> PI["ต่อหน้า: ชนิดหน้า<br/>vector · raster · mixed · empty<br/>(ไฟล์เดียวปนกันได้)"]
  PI --> BK["สรุปทั้งเล่ม: เวกเตอร์ / ผสม / สแกน<br/>vector_raster_list.py<br/>175 เล่ม = เวกเตอร์ 90 · ผสม 21 · สแกน 64"]
  PI --> OR["ทิศหน้า page_orient.decide<br/>turns 0-3 = หมุนตามเข็มกี่ครั้งให้ตั้งตรง"]
  OR -->|"มีข้อความฝัง ≥ 30 คำ"| TX["ดูทิศของข้อความฝัง (≥ 70% ไปทางเดียวกัน)<br/>953 หน้าใน 35 เล่ม: หมุน 3 ครั้งทุกหน้า"]
  OR -->|"หน้าสแกนที่ตามองเห็นเป็นแนวตั้ง"| OC["OCR 3 ทิศ นับเฉพาะพยัญชนะไทย<br/>26 หน้า ตัดสินได้ 25"]
  OR -->|"หน้าสแกนแนวนอน"| NC["ไม่ตรวจ → turns 0<br/>(เนื้อหาตะแคงข้างในหน้ายังตรวจไม่ได้)"]
  PI --> PNG["ทุกหน้า → PNG 200 dpi<br/>ความละเอียดเดียวกับภาพที่ใช้เทรน<br/>(คลัง image/ มีครบ · เว็บทำตอนส่งงาน)"]
  TX --> OUT["ส่งต่อ Pass 1: หน้าตั้งตรง + ชนิดหน้า + PNG"]
  OC --> OUT
  NC --> OUT
  PNG --> OUT
  BK --> OUT
  classDef ok fill:#cfeede,stroke:#12906a,color:#14213d
  classDef part fill:#fff0b3,stroke:#b58900,color:#14213d
  classDef no fill:#f9d0d6,stroke:#d1405a,color:#14213d
  class IN,PI,BK,OR,TX,OC,PNG,OUT ok
  class NC no
```

ตัดสินในประชุม 25 พ.ย.: ทำเล่มเวกเตอร์ก่อน (บอก STECON ด้วย) · STECON ดอยคำ: เล่ม 05 (รายการคำนวณ) เป็นสแกน ที่เหลือเวกเตอร์ · รายชื่อทุกเล่มพร้อมเลขหน้าที่เป็นสแกน: `docs/pipeline_5_ส่วน/เล่มแบบ_เวกเตอร์_สแกน.csv`
ยังไม่ได้ทำ: ตัวจำแนกทิศสำเร็จรูป (PP-LCNet) ผิดราว 94% บนหน้าแนวนอน จึงไม่ใช้ · หน้าสแกนแนวนอนที่เนื้อหาข้างในตะแคงยังไม่มีวิธีตรวจ

---

## Pass 1 — กรอบชื่อแบบ → รหัสแผ่น / ชื่อแผ่นต่อหน้า (ส่วน 1)

โค้ด: `tools/pass1_sheet_classify.py` · `tools/titleblock_extract.py` · `tools/pass1_toc.py` (ตรรกะสารบัญ)

```mermaid
flowchart TD
  IN["หน้าตั้งตรง + ชนิดหน้า (Pass 0)"] --> PR["โพรบโซนกรอบชื่อแบบ<br/>ครอปโซนขวา / โซนล่าง ของหน้ากลางเล่ม ≤ 6 หน้า<br/>นับคำ 5 กลุ่ม: รหัส · ชื่อ · มาตราส่วน · วันที่ · โครงการ"]
  PR -->|"2 หน้าได้ ≥ 0.8"| LK["ล็อกโซน (zone log ready)"]
  PR -->|"ไม่ถึง"| UL["ไม่ล็อก ใช้ลำดับค้นเดิม (ผลยังออก ไม่หยุด)"]
  LK --> RD["อ่านทุกหน้าของเล่ม"]
  UL --> RD
  RD -->|"หน้าเวกเตอร์"| VT["ข้อความฝังในแถบขวา/ล่าง<br/>เลือกรหัสที่ชิดมุมขวาล่างสุด"]
  RD -->|"ไม่เจอ หรือหน้าสแกน"| OC["OCR ตามลำดับ: มุมขวาล่าง → โซนที่ล็อก → โซนอื่น"]
  VT --> NM["ชื่อแผ่น: ข้อความฝังก่อน แล้ว OCR ไทย<br/>หยุดที่คำจบ (มาตราส่วน วันที่ เลขที่)"]
  OC --> NM
  NM --> FL["ธง: titleblock_not_found · titleblock_moved<br/>titleblock_outside_zone"]
  FL --> OUT["pass1_sheet_classified.json<br/>ต่อหน้า: pdf_page · sheet_code · sheet_name<br/>ชนิดหน้า · turns · ธง"]
  TOC["สารบัญ: หาหน้า + OCR เป็นแถว"] --> JN["ผูกแถวสารบัญกับหน้าด้วยรหัสแผ่น<br/>(ตรรกะ + self-check)"]
  OUT --> JN
  T07["t07 pass0 จำแนกประเภทหน้า"] --> RC["เทียบสารบัญกับ t07 ต่อหน้า<br/>ตรง = ใช้ · ขัด = รวมทั้งสอง + เตือน<br/>ไม่มีทั้งคู่ = ห้ามเดาประเภท"]
  JN --> RC
  RC --> NX["ส่งต่อ: รหัส/ชื่อแผ่นต่อหน้า<br/>→ Pass 3 เลือกหน้าแปลน/รูปตัด · Pass 4 แยก GT/SP/SM/SS<br/>(ยังไม่ได้ต่อสาย)"]
  OUT --> NX
  classDef ok fill:#cfeede,stroke:#12906a,color:#14213d
  classDef part fill:#fff0b3,stroke:#b58900,color:#14213d
  classDef no fill:#f9d0d6,stroke:#d1405a,color:#14213d
  classDef plan fill:#dbe7ff,stroke:#2457d6,color:#14213d
  class IN,PR,LK,RD,VT,OC,NM,OUT ok
  class UL,FL,JN,RC part
  class TOC,NX no
  class T07 plan
```

ผลที่วัด: รหัสแผ่นถูก 475/475 บนหน้าที่เฉลยเป็นรหัสตัวอักษร+เลข (33 เล่ม) · โพรบ 15 เล่มบ้านเล็ก: เจอ 183/205 **ผิด 0** (ที่ไม่เจอ 22 หน้าอยู่ในเล่มเดียว `1ชั้น_06` ซึ่งหน้ากลางเล่มเป็น BOQ เลยไม่ล็อกโซน)
ยังไม่พิสูจน์: `titleblock_moved` ยังไม่เคยเจอกรอบที่ย้ายจริงในคลัง 175 เล่ม · การหาหน้าสารบัญและ OCR สารบัญเป็นแถวยังไม่ได้ทำ · t07 ยังไม่เทรน · Pass 3 และ 4 ยังไม่ได้ใช้รหัสแผ่นจาก pass นี้ (Pass 3 เลือกหน้าด้วยรูปทรง)

---

## Pass 2 — ประเภทงานก่อสร้าง (ส่วน 2) · ข้อเสนอ รอทีมตัดสิน

ที่มา: `docs/pipeline_5_ส่วน/การบ้าน_2026-11-20.md` ข้อ 1 · ไม่มีโค้ด

```mermaid
flowchart TD
  K["แนวคิดของคิง: จัดประเภทงาน<br/>บ้าน / อาคารใหญ่ / อื่นๆ (ถนน โรงงาน โรงไฟฟ้า)<br/>เพื่อคาดสเกลและเลือก prompt ตามประเภท"] --> Q["การบ้าน: ควรเป็นขั้นที่เรียกโมเดลไหม"]
  Q --> P["ข้อเสนอของมะขาม: ไม่เรียกโมเดล<br/>เก็บเป็นข้อเท็จจริงของไฟล์ที่ pass อื่นได้มาฟรี"]
  P --> F1["ขนาดกระดาษจาก PDF (Pass 0)<br/>บ้านเล็ก A3 106/118 เล่ม (90%)<br/>บ้านใหญ่ A3 24/56 (43%)"]
  P --> F2["จำนวนหน้า: มัธยฐาน 21 กับ 28<br/>(ช่วงทับกัน 2-137 กับ 5-108)"]
  P --> F3["จำนวนชั้นจาก level master (Pass 3)"]
  P --> F4["มาตราส่วนที่พิมพ์ในกรอบชื่อแบบ (Pass 1)<br/>ยังไม่ได้ดึง"]
  F1 --> X["คาดสเกลของงาน<br/>ยังไม่ได้วัดว่าพอไหม"]
  F2 --> X
  F3 --> X
  F4 --> X
  P --> PR["prompt เลือกตามชนิดแผ่นใน Pass 4 (GT/SP/SM/SS)<br/>ไม่ใช่ตามประเภทงาน"]
  P --> OOS["ไม่เจอสารบัญหรือกรอบกริดเลย<br/>→ ธง นอกขอบเขต ให้คนตรวจ (ไม่เดาประเภท)"]
  classDef ok fill:#cfeede,stroke:#12906a,color:#14213d
  classDef part fill:#fff0b3,stroke:#b58900,color:#14213d
  classDef no fill:#f9d0d6,stroke:#d1405a,color:#14213d
  classDef plan fill:#dbe7ff,stroke:#2457d6,color:#14213d
  class K,Q,P,PR,OOS plan
  class F1,F2 ok
  class F3 part
  class F4,X no
```

เหตุผลของข้อเสนอ: คลัง 175 เล่มเป็นบ้านหรืออาคารล้วน ไม่มีงาน "อื่นๆ" ให้สอบ ตัวจัดประเภทที่ตอบ "อื่นๆ" จึงพิสูจน์ไม่ได้ · ทุกขั้นที่เพิ่ม = จุดพัง เวลารัน และหน่วยความจำที่เพิ่มขึ้น
ความเสี่ยงที่รับ: ถ้างานจริงของ STECON ต้องการ prompt คนละแบบกับบ้าน จะรู้ก็ต่อเมื่อเห็นผลพัง · กลับมาพิจารณาเมื่อ prompt เดียวกันพังซ้ำกับอาคารใหญ่และ prompt เฉพาะประเภทแก้ได้

---

## Pass 3 — เส้นกริด (แนวนอน) + ระดับ (แนวตั้ง) → Proj. Grid DB (ส่วน 3)

โค้ด: `tools/gridlab_probe.py` · `tools/gridlab_scale.py` · `tools/pass3_grid.py` · `tools/level_marks.py` · `tools/level_link.py`

```mermaid
flowchart TD
  subgraph G[" "]
    GH["แขนแปลน: เส้นกริด x / y"] --> GA
    GA["หาวงหัวกริด + ก้านของวง<br/>gridlab_probe.detect()"] --> GB["ชื่อในวง: ข้อความฝัง หรือ OCR ในวง<br/>ชื่อสอดคล้องทั้งแถว · จับคู่เป็นแปลน"]
    GB --> GC["สเกล: OCR ตัวเลขระยะระหว่างวงกับตัวอาคาร<br/>โหวต pt ต่อเมตร → pos_m ทุกเส้น"]
    GC --> GD["รวมทุกแปลนเป็นของทั้งบ้าน<br/>จัดแนวด้วยชื่อที่ซ้ำ ≥ 2 ตัว · ขัดกัน = ทิ้งแปลน"]
  end
  subgraph L[" "]
    LH["แขนระดับ: ความสูง (วิธีใหม่ 25-26 พ.ย.)"] --> LA
    LA["หาสัญลักษณ์ระดับ ▽ และวงกลมระดับแบบ STECON<br/>ในรูปด้าน/รูปตัด (ไม่เรียกโมเดล)"] --> LB["OCR แถบข้างสัญลักษณ์ ~400 dpi<br/>Paddle / OpenThai / both"]
    LB --> LC["เลขระดับ + ชื่อชั้น → ตารางชั้น<br/>B1 · F1 · F1M · F2 … RF · RF2<br/>เสมอกัน = ว่าง + ตัวเลือก ไม่เดา"]
    LT["ป้าย (+9.00) ใต้ชื่อพื้นในแปลนโครงสร้าง<br/>→ แปลนหน้าไหนอยู่ชั้นไหน"]
  end
  IN["หน้าเวกเตอร์ (Pass 0)<br/>เลือกหน้าด้วยรูปทรง"] --> GH
  IN --> LH
  GD --> GM[("grid_master.json<br/>เส้น named")]
  DM["เส้น dummy: มีแต่ขีดระยะ ไม่มีวง (~64% ของเฉลย)<br/>ตั้งใจให้ t07 อ่าน · ข้อเสนอ: เก็บเป็นตำแหน่งรอ<br/>เลื่อนเป็น dummy เมื่อมี element มาเกาะ"] -.-> GM
  LC --> LM[("level_marks.json<br/>level master")]
  LM --> LT
  LM --> LL["level_link.py --level-master<br/>แปลนทุกหน้า → ชั้น + ความสูงชั้น"]
  GM --> PG[("Proj. Grid DB proj_grid.json<br/>grid master + z_levels + level master")]
  LM -.->|"ยังไม่ได้ต่อสาย<br/>proj_grid ยังใช้ระดับวิธีเก่า"| PG
  GM --> DV["วาดทับแบบใน Developer mode<br/>(โหลด result.json / level_marks.json)"]
  LM --> DV
  PG --> NX["→ Pass 4 (ตารางกริดของ SP) · Pass 5<br/>(ยังไม่ได้ต่อสาย)"]
  SC["หน้าสแกน: หาวงหัวกริด / สัญลักษณ์ระดับไม่ได้"] -.-> IN
  SA["Find Site area"] -.-> PG
  classDef ok fill:#cfeede,stroke:#12906a,color:#14213d
  classDef part fill:#fff0b3,stroke:#b58900,color:#14213d
  classDef no fill:#f9d0d6,stroke:#d1405a,color:#14213d
  classDef plan fill:#dbe7ff,stroke:#2457d6,color:#14213d
  classDef head fill:#ffffff,stroke:#ffffff,color:#2457d6,font-weight:bold
  class IN,GA,GB,GC,GD,GM,LA,LB,LC,LM,LT,LL,DV ok
  class PG part
  class SC,SA,NX no
  class DM plan
  class GH,LH head
```

ผลที่วัด (หน้าเวกเตอร์เท่านั้น): ชื่อเส้นต่อหน้าตรงทั้งชุด 251/276 แกน (91%) · สเกลเจอ 154/155 แปลน ช่องระหว่างเส้นคลาด ≤ 2 ซม. 841/842 · grid master เส้น named 72/72 บน 10 บ้าน ช่อง 52/52 · บ้าน 174 11/11
ระดับ: เล่มเวกเตอร์ในเฉลย ชั้นถูก 28/28 ผิด 0 · ค่าที่อ่านได้เป็นระดับจริง 98% · โหมด both อ่านได้ 113/180 ระดับ · STECON ดอยคำครบ 9 ชั้น · ป้าย (+9.00) ในแปลนโครงสร้าง STECON ลงชั้นถูก 16/17 ผิด 0 · เล่ม 174: แปลน 18 หน้าลง 9 ชั้น ไม่มีธง
ยังไม่ได้ทำ: หน้าสแกนทั้งสองแขน · เส้น dummy · ต่อ level_marks.json เข้า proj_grid · Find Site area · Pass 4 ยังใช้ grid master จากเฉลย ไม่ใช่ของ pass นี้

---

## Pass 4 — หา element: GT / SM / SS และ SP (ส่วน 4)

โค้ด: SP = `tools/pass4_sp.py` · `tools/pass4_pure.py` · อ่านครอป = Constistant `js/dev/dev-mode.js` (งาน `single_call` → `worker.py run_single_call`) · prompt = `tune_ai/t04_Purson/pass2/`

```mermaid
flowchart TD
  subgraph A[" "]
    AH["GT / SM / SS — เมล + มะขาม (ใช้ logic เดียวกัน)"] --> CR
    CR["ครอปทีละ detail<br/>Voronoi + Set-of-Mark agent · ตัดแกน x/y<br/>(เมลกำลังเลือกวิธีที่ดีที่สุดจากที่ลองแล้ว)"] --> RD["AI อ่านทีละครอป<br/>prompt t04: section = SM · notes = GT · schedule<br/>ส่งผ่าน Developer mode ผลขึ้นเป็นตาราง"]
    RD --> PC["ตรวจกติกาของ prompt (คอลัมน์ตรวจ)<br/>คานแยกบน/ล่าง · เสาเป็นจำนวนเดียว · มีปลอก มีขนาด"]
    PC --> EL["Engineering logic check เทียบมาตรฐาน<br/>ACI / วสท. / มยผ. · ครอปใหม่ ≤ 3 รอบ<br/>ไม่ผ่าน = ใช้ค่ามาตรฐาน + เตือนวิศวกร"]
    EL --> DB1[("GT / SM / SS DB<br/>SM ผูกรูปตัดเข้ากับ element ที่อ้างถึง")]
    JS["ข้อเสนอ: JSON หนึ่งแม่แบบต่อ element_type<br/>footing กับ column ก่อน · ล็อกชื่อคีย์"] -.-> RD
  end
  subgraph B[" "]
    BH["SP แปลนโครงสร้าง — โซน + อิม (overlay)<br/>ตัวล็อกตำแหน่งของมะขาม"] --> GT0
    GT0["ตารางกริดต่อแปลน: pt = a × เมตร + b<br/>(ใช้ grid master จากเฉลย ยังไม่ใช่ของ Pass 3)"] --> FE["element + grid_ref<br/>ตอนนี้จากไฟล์เฉลย<br/>ตั้งใจให้ t07 plan_beam / plan_footing / plan_slab"]
    FE --> PL["pixel lock: grid_ref → ตำแหน่งบนภาพ<br/>เสา/ฐานราก = จุด · คาน = ท่อน · พื้น = กรอบ<br/>กำกวม = ไม่ล็อก ไม่เดา"]
    PL --> VF["ตรวจว่ามีของวาดอยู่จริง (หน้าเวกเตอร์)<br/>จุด 99.5% เทียบตัวควบคุม 16.8%<br/>คาน 92.7% เทียบตัวควบคุม 16.5%"]
    PU["pass4_pure.py: ไม่ใช้เฉลย ลองทุกจุดตัด / ช่วงกริด<br/>ได้ผู้สมัคร (มีของเกิน · แผ่นสถาปัตย์ต้องกรองด้วยรหัสแผ่น)"] -.-> VF
    VF --> OV["overlay บนเว็บ: คานก่อน แล้วพื้น = พื้นที่ในกรอบคาน<br/>ช่องเปิดลบด้วยมือ · dynamic field แก้แล้ว BOQ/BBS เปลี่ยน"]
    OV --> DB2[("ตำแหน่ง element ต่อแปลน<br/>pass4_sp_pNN.json")]
  end
  IN["รหัส/ชื่อแผ่นต่อหน้า (Pass 1)"] --> KD["แยกชนิดหน้า: GT ทั่วไป/หมายเหตุ · SM ตาราง/รูปตัดชิ้นส่วน<br/>SS รูปตัดพิเศษ (บันได โครงหลังคา) · SP แปลนโครงสร้าง<br/>หน้าเดียวมีสองชนิดได้ · วิธีแยกยังเปิดอยู่"]
  KD -->|"GT · SM · SS"| AH
  KD -->|"SP"| BH
  GRID["Proj. Grid DB (Pass 3)"] -.-> GT0
  DB1 --> NX["→ Pass 5: รวมเป็น structural DB"]
  DB2 --> NX
  classDef ok fill:#cfeede,stroke:#12906a,color:#14213d
  classDef part fill:#fff0b3,stroke:#b58900,color:#14213d
  classDef no fill:#f9d0d6,stroke:#d1405a,color:#14213d
  classDef plan fill:#dbe7ff,stroke:#2457d6,color:#14213d
  classDef head fill:#ffffff,stroke:#ffffff,color:#2457d6,font-weight:bold
  class IN,PC,PL,VF,DB2 ok
  class KD,CR,RD,GT0,FE,PU,OV,GRID part
  class EL,DB1,NX no
  class JS plan
  class AH,BH head
```

ผลที่วัด (SP, `pass4_sp.py --eval` ทุกเล่มที่ 6 ที่มี grid master, 53 หน้า): ล็อกได้ 26 หน้า 466 element · ล็อกไม่ได้ 27 หน้า (25 เป็นหน้าสแกน) · `pass4_pure.py` บน `1ชั้น_27` หน้า 10: จุด 32/32 คาน 28/28 ไม่เกิน · แต่แผ่นสถาปัตย์ (A-03, A-04) ก็ได้คาน 16-27 ช่วง จึงต้องกรองด้วยรหัสแผ่นจาก Pass 1 ก่อน
GT/SM/SS: ทางส่งครอปให้ AI อ่าน (Developer mode) ทำแล้ว ทดสอบในเบราว์เซอร์กับ Supabase จำลอง แต่**ยังไม่เคยส่งผ่านการ์ดจริง** · คอลัมน์ตรวจเช็คแค่กติกาที่ prompt เขียนไว้ ไม่ใช่ engineering logic
ที่ตัวเลข SP ไม่ได้บอก: "เจอของที่วาด" ไม่ได้แปลว่า mark ถูก (สลับ C1 กับ C2 ที่ตำแหน่งถูกต้องจับไม่ได้) · ตัวควบคุมราว 17% ไม่ใช่ศูนย์ ต้องอ่านคู่กันเสมอ
ยังไม่ได้ทำ: engineering logic check · ฐานข้อมูล GT/SM/SS · ผูกรูปตัดกับ element · ให้โมเดลหา element บนแปลนเอง (ต้อง t07 ที่เทรนแล้ว) · หน้าสแกน · ต่อ grid master จาก Pass 3

---

## Pass 5 — Matching: รวมทุกฐานข้อมูล → Constistant (ส่วน 5)

ฝั่งที่รับมีอยู่แล้วใน Constistant: `js/drawing/raw-extraction-adapter.js` · `js/shared/pipeline.js` · `js/shared/standards-config.js` · `js/shared/price-config.js` · Input Hub

```mermaid
flowchart TD
  PG[("Proj. Grid DB (Pass 3)<br/>เส้นกริด + เมตร + ระดับชั้น")] --> LK
  SD[("structural DB (Pass 4)<br/>รายละเอียดจาก GT/SM/SS<br/>+ ตำแหน่งจาก SP")] --> LK
  MD[("main DB: มีก่อนเห็นแบบ<br/>มาตรฐาน มยผ. / วสท. / ACI = standards-config.js<br/>ราคา CGD / TPSO = price-config.js")] --> LK
  UI["ข้อมูลที่ผู้ใช้กรอก<br/>Input Hub ของ Constistant"] --> LK
  LK["ผูกต่อ element เป็นกราฟ (แบบ graphify)<br/>ตำแหน่ง (SP) + หน้าตัด/เหล็ก (SM) + กติกาทั่วไป (GT)<br/>+ ระดับชั้น + ความมั่นใจของแต่ละช่อง"] --> RJ["ส่งเข้า Constistant ในรูปแบบที่ adapter อ่านได้<br/>ตอนนี้ = raw JSON ตาม primary_rawjson_schema<br/>(รูปแบบของส่วน 5 ยังไม่ตัดสิน)"]
  RJ --> AD["raw-extraction adapter<br/>ค่าที่ไม่มี = ติดธง ไม่เดา"]
  AD --> PP["runPipeline: BOQ → BBS → แผนงาน<br/>→ ทรัพยากร → ความพร้อม"]
  PP --> OV["overlay ให้ผู้ใช้ดู: ตำแหน่ง · หน้าตัด · ความมั่นใจ<br/>แก้ค่าแล้วคำนวณใหม่"]
  OV -.->|"ผู้ใช้แก้ค่า"| UI
  classDef ok fill:#cfeede,stroke:#12906a,color:#14213d
  classDef part fill:#fff0b3,stroke:#b58900,color:#14213d
  classDef no fill:#f9d0d6,stroke:#d1405a,color:#14213d
  class MD,UI,AD,PP ok
  class PG,RJ,OV part
  class SD,LK no
```

ตอนนี้ทางที่วิ่งครบจริงคือทางเก่า: Destrier อ่านทั้งเล่ม → raw JSON → adapter → BOQ · ส่วน 5 ของไปป์ไลน์ใหม่ (ผูกเป็นกราฟ) ยังไม่ได้เริ่ม และยังไม่ได้แบ่งเจ้าของ
ต้องตัดสิน: รูปแบบที่ส่วน 5 ส่งให้ Constistant (ใช้ raw JSON เดิมต่อ หรือรูปแบบใหม่) · ใครเป็นเจ้าของ dynamic field ฝั่ง overlay (ประชุม 25 พ.ย. ยังไม่ตกลงว่าอิมหรือแทน)
