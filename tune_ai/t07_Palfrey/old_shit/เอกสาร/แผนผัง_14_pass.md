# แผนผังระบบ 14 pass (สร้างจาก `pass_ทำอะไร.csv` ฉบับแก้ 18 พ.ย. 69)

สี: **น้ำเงินเข้ม = โมเดล t07 (AI บนการ์ด)** · **เขียวน้ำทะเล = cv2** · **เทา = โค้ดธรรมดา (ไม่เดา)** · **เหลือง = t07 + โค้ดตรวจ** · **เทา ขอบน้ำเงินประ = โค้ด + t07 สำรอง (ยังไม่ตัดสิน)** · **เขียว = ฝั่งเว็บ**

เลข pass เดิม → ใหม่: 1→1 · 2→2 · 3→3 · 3.5→4 · 4→5 · 4b→6 · 5→7 · 5.5→8 · 5.6→9 · 6→10 · 7→11 · 8→12 · 9→13 · 10→14

## 1) ภาพรวมทั้ง 14 pass (เรียงตามลำดับทำงาน)

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Leelawadee UI, Tahoma, sans-serif","fontSize":"15px","lineColor":"#64748b","edgeLabelBackground":"#ffffff"},"flowchart":{"curve":"basis","nodeSpacing":36,"rankSpacing":36,"padding":14}}}%%
flowchart TD
  WEB0(["<b>เว็บเตรียมไฟล์</b><br/>PDF → PNG 200 dpi + vectors_v1.json"]):::web

  subgraph G1["① อ่านข้อความ จำแนก และตัดวิว"]
    direction TB
    P1["<b>pass 1 · ดึงข้อความ</b><br/>CAD อ่านจาก vectors_v1.json ไม่ต้อง OCR<br/>หน้าสแกนค่อย OCR กรอบชื่อแบบ<br/><i>ส่ง: ข้อความรายหน้า + มาร์คต่อหน้า + สารบัญ</i>"]:::code
    P2["<b>pass 2 · จำแนกรายวิว</b><br/>หน้าเดียวมีได้หลายวิว · ใหม่: column_plan / slab_plan (ติดด่าน)<br/><i>ส่ง: views[] (ตำแหน่ง · pattern · also_gridline · อาคาร)</i>"]:::ai
    P3["<b>pass 3 · ตัดวิว</b><br/>organize.py บน/ล่าง + ซ้าย/ขวา · หน้ารูปตัดตัดทีละรูป<br/><i>ส่ง: ครอปรายวิว + manifest</i>"]:::code
    P4["<b>pass 4 · คัดชนิดรูปตัด</b><br/>beam_section · footing_section<br/>column_section · section (ชนิดอื่น)<br/>โค้ดดูตัวนำหน้ามาร์ค · t07 เมื่อไม่มีมาร์ค (ยังไม่ตัดสิน)"]:::mix
    P1 --> P2 --> P3 --> P4
  end

  subgraph G2["② ผังกริดและระดับชั้น"]
    direction TB
    P5["<b>pass 5 · Grid master</b><br/>รายอาคาร · อ่านทีละหน้าแล้วโค้ดรวม · ตรวจ 4 ข้อ<br/><i>ส่ง: x/y lines + z_levels + ผลตรวจ</i>"]:::check
    P6["<b>pass 6 · Level master</b><br/>ชั้นไหนอยู่ระดับเท่าไร · ผูกวิวแปลนเข้ากับชั้น<br/><i>ส่ง: หน้า00_level.json + ธง (ความสูงชั้นไป pass 14)</i>"]:::code
    P5 --> P6
  end

  subgraph G3["③ ชี้เป้าบนภาพครอป"]
    direction TB
    P7["<b>pass 7 · cv2 หา element</b><br/>แปลน 4 ชนิด + column_plan (ไม่มีแม่แบบพื้น)<br/>ไม่เจอชิ้นเลย = ตัดผิด → ใช้เต็มหน้า<br/><i>ส่ง: #n + พิกัด + จำนวนต่อชนิด</i>"]:::cv
    P8["<b>pass 8 · หาเส้นกริดบนภาพ</b><br/>อย่างน้อย 3 มุม · cv2 + OCR + เวกเตอร์<br/><i>ส่ง: ตัวแปลงพิกเซล ↔ เมตร + ค่าคลาด</i>"]:::cv
    P9["<b>pass 9 · วาดเส้นกริด dummy</b><br/>วาดลงภาพครอปพร้อมชื่อเส้น (2', A'')<br/>วาดเฉพาะเมื่อ pass 8 คลาดน้อย"]:::cv
    P7 --> P8 --> P9
  end

  subgraph G4["④ อ่านชิ้นส่วน"]
    direction TB
    P10["<b>pass 10 · จัดระเบียบ</b><br/>รวมผล pass 3, 4, 5, 7 + ภาพเส้น dummy จาก pass 9<br/>แล้วแยกโฟลเดอร์ตาม pattern"]:::code
    P11["<b>pass 11 · t07 หา element</b><br/>prompt ต่างกันตาม pattern<br/>คานเขียนเป็น span [เริ่ม, จบ, ยาว]"]:::ai
    P12["<b>pass 12 · t07 + คำใบ้</b><br/>เฉพาะแปลน (ไม่รวม slab_plan)<br/>hint จาก pass 7"]:::ai
    P10 --> P11
    P10 --> P12
  end

  subgraph G5["⑤ วัดระยะและรวมผล"]
    direction TB
    P13["<b>pass 13 · วัดระยะ</b><br/>ไม้บรรทัดเวกเตอร์ก่อน · CV เป็นตัวสำรอง<br/>รายงานอย่างเดียว ไม่ทับผลที่อ่านมา"]:::code
    P14["<b>pass 14 · combine</b><br/>โค้ดล้วน ไม่ใช้โมเดล · ใช้ความสูงชั้นจาก pass 6<br/><i>ส่ง: raw JSON รายวิว + ธง + ที่มาต่อชิ้น</i>"]:::code
    P13 --> P14
  end

  WEB1(["<b>เว็บ</b><br/>ตรวจ → ยืนยันนำเข้า → BOQ"]):::web

  WEB0 --> G1
  G1 --> G2
  G2 --> G3
  G3 --> G4
  G4 --> G5
  G5 --> WEB1

  classDef ai fill:#17324d,stroke:#0b1b2b,color:#fff,stroke-width:2px;
  classDef cv fill:#0f766e,stroke:#0a4f4a,color:#fff,stroke-width:2px;
  classDef code fill:#e2e8f0,stroke:#64748b,color:#1b2430,stroke-width:2px;
  classDef check fill:#fde68a,stroke:#b45309,color:#1b2430,stroke-width:2px;
  classDef mix fill:#e2e8f0,stroke:#17324d,color:#1b2430,stroke-width:3px,stroke-dasharray:6 3;
  classDef web fill:#16a34a,stroke:#166534,color:#fff,stroke-width:2px;
  style G1 fill:#f8fafc,stroke:#cbd5e1,color:#334155
  style G2 fill:#f8fafc,stroke:#cbd5e1,color:#334155
  style G3 fill:#f8fafc,stroke:#cbd5e1,color:#334155
  style G4 fill:#f8fafc,stroke:#cbd5e1,color:#334155
  style G5 fill:#f8fafc,stroke:#cbd5e1,color:#334155
```

**ยังไม่ตัดสิน:** pass 11 กับ pass 12 วาดเป็นทางคู่ขนาน (ต่างคนต่างรับโฟลเดอร์จาก pass 10) — จะให้ทำคู่กันหรือทำต่อกันเป็นลำดับ รอมะขามตัดสิน

## 2) ใครส่งอะไรให้ใคร (ทุกเส้นมาจากช่อง input ใน CSV)

เส้น: **เขียว = ภาพหน้า/เวกเตอร์จากเว็บ** · **ส้ม = grid master จาก pass 5** · **ประเทา = ข้อความ/มาร์คจาก pass 1** · **เทาทึบ = ข้อมูลอื่น (views, ภาพครอป, json, level master)**

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Leelawadee UI, Tahoma, sans-serif","fontSize":"15px","lineColor":"#64748b","edgeLabelBackground":"#ffffff"},"flowchart":{"curve":"basis","nodeSpacing":30,"rankSpacing":46,"padding":12}}}%%
flowchart TD
  W0(["<b>เว็บ</b> · PNG + vectors_v1.json"]):::web
  S1["<b>1</b> · ดึงข้อความ"]:::code
  S2["<b>2</b> · จำแนกรายวิว"]:::ai
  S3["<b>3</b> · ตัดวิว"]:::code
  S4["<b>4</b> · คัดชนิดรูปตัด"]:::mix
  S5["<b>5</b> · grid master"]:::check
  S6["<b>6</b> · level master"]:::code
  S7["<b>7</b> · cv2 หา element"]:::cv
  S8["<b>8</b> · หาเส้นกริดบนภาพ"]:::cv
  S9["<b>9</b> · วาดเส้น dummy"]:::cv
  S10["<b>10</b> · จัดระเบียบ"]:::code
  S11["<b>11</b> · t07 หา element"]:::ai
  S12["<b>12</b> · t07 + คำใบ้"]:::ai
  S13["<b>13</b> · วัดระยะ"]:::code
  S14["<b>14</b> · combine"]:::code
  W1(["<b>เว็บ</b> · ตรวจ → BOQ"]):::web

  W0 --> S1
  S1 -.-> S2
  S2 --> S3
  S3 --> S4
  S2 --> S5
  S5 --> S6
  S2 --> S6
  S3 --> S6
  S3 --> S7
  S7 --> S8
  S3 --> S8
  S8 --> S9
  S3 --> S9
  S3 --> S10
  S4 --> S10
  S7 --> S10
  S9 --> S10
  S10 --> S11
  S10 --> S12
  S7 --> S13
  S11 --> S13
  S12 --> S13
  S11 --> S14
  S12 --> S14
  S13 --> S14
  S6 --> S14
  S14 --> W1
  S5 --> S8
  S5 --> S9
  S5 --> S10
  S5 --> S13
  S5 --> S14
  S1 -.-> S3
  S1 -.-> S4
  S1 -.-> S5
  S1 -.-> S6
  S1 -.-> S8
  S1 -.-> S11
  S1 -.-> S12
  S1 -.-> S14
  W0 --> S2
  W0 --> S3
  W0 --> S5
  W0 --> S8
  W0 --> S13

  classDef ai fill:#17324d,stroke:#0b1b2b,color:#fff,stroke-width:2px;
  classDef cv fill:#0f766e,stroke:#0a4f4a,color:#fff,stroke-width:2px;
  classDef code fill:#e2e8f0,stroke:#64748b,color:#1b2430,stroke-width:2px;
  classDef check fill:#fde68a,stroke:#b45309,color:#1b2430,stroke-width:2px;
  classDef mix fill:#e2e8f0,stroke:#17324d,color:#1b2430,stroke-width:3px,stroke-dasharray:6 3;
  classDef web fill:#16a34a,stroke:#166534,color:#fff,stroke-width:2px;
  linkStyle 0,40,41,42,43,44 stroke:#16a34a,stroke-width:2px;
  linkStyle 1,32,33,34,35,36,37,38,39 stroke:#94a3b8,stroke-width:1.5px;
  linkStyle 5,27,28,29,30,31 stroke:#b45309,stroke-width:2.5px;
```

## 3) แต่ละชนิดหน้าแบบ (pattern) ไปทางไหน

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Leelawadee UI, Tahoma, sans-serif","fontSize":"15px","lineColor":"#64748b","edgeLabelBackground":"#ffffff"},"flowchart":{"curve":"basis","nodeSpacing":36,"rankSpacing":36,"padding":14}}}%%
flowchart TD
  R(["<b>pass 3 · ครอปรายวิว</b><br/>pattern จาก pass 2"]):::code

  PL["<b>แปลน 5 ชนิด</b><br/>beam_plan · footing_plan<br/>roof_frame_plan · etc_plan<br/>column_plan (ใหม่ · ติดด่าน)"]:::grp
  SL["<b>slab_plan</b><br/>(ใหม่ · ติดด่าน)<br/>cv2 ไม่มีแม่แบบพื้น"]:::grp
  SEC["<b>รูปตัด 4 ชนิด</b><br/>section · beam_section<br/>footing_section · column_section"]:::grp
  SN["<b>ตาราง · ข้อกำหนด</b><br/>schedule · notes"]:::grp
  GR["<b>กริด และ ระดับ</b><br/>grid_master · side_profile"]:::grp
  KP["<b>เก็บไว้ ยังไม่อ่านชิ้นส่วน</b>"]:::grp

  A5["<b>pass 5</b><br/>ใช้ถ้าติด also_gridline"]:::check
  A6["<b>pass 6</b><br/>ระดับของชั้นที่วิวนี้อยู่"]:::code
  A7["<b>pass 7</b> · cv2<br/>หาชิ้น + เช็คครอป"]:::cv
  A8["<b>pass 8</b><br/>พิกเซลเส้นกริด ↔ เมตร"]:::cv
  A9["<b>pass 9</b><br/>วาดเส้น dummy (เมื่อ pass 8 ผ่าน)"]:::cv
  B4["<b>pass 4</b><br/>คัดชนิดต่อครอป"]:::mix
  P10(["<b>pass 10</b><br/>แยกโฟลเดอร์ตาม pattern"]):::code
  A11["<b>pass 11</b> · t07<br/>ภาพ + grid master"]:::ai
  A12["<b>pass 12</b> · t07<br/>ภาพ + grid master + json pass 7"]:::ai
  A13["<b>pass 13</b><br/>วัดระยะ"]:::code
  B11["<b>pass 11</b> · t07<br/>ภาพอย่างเดียว<br/>ไม่ต้องมีกริด/คำใบ้"]:::ai
  P14(["<b>pass 14</b><br/>combine"]):::code

  N1["<b>grid_master</b> อ่านที่ pass 5 แล้ว ไม่ต้องเข้า pass 11<br/><b>side_profile</b> ใช้อ่านระดับ z_levels ใน pass 5<br/><b>level_master</b> = ไฟล์ผลของ pass 6 ไม่ใช่หน้าในแบบ"]:::note
  N2["<b>ใช้ทีหลัง:</b> material_list · bbs_schedule · title · symbol<br/><b>ตรวจไฟล์ขาดหน้า:</b> index (สารบัญจาก pass 1)<br/><b>ไม่อ่าน:</b> site_plan · roof_plan · misc · unknown<br/><b>เว็บอ่านเอง:</b> soil_boring_log (หน้า Site Investigate)"]:::note

  R --> PL
  R --> SL
  R --> SEC
  R --> SN
  R --> GR
  R --> KP
  PL --> A5
  SL --> A5
  A5 --> A6
  A6 -->|แปลน 5 ชนิด| A7
  A6 -->|slab_plan ข้าม pass 7| A8
  A7 --> A8 --> A9 --> P10
  SEC --> B4 --> P10
  SN --> P10
  P10 -->|แปลนทั้ง 6 ชนิด| A11
  P10 -->|แปลน 5 ชนิด · ไม่มี slab_plan| A12
  A11 --> A13
  A12 --> A13
  A13 --> P14
  P10 -->|รูปตัด · ตาราง · ข้อกำหนด| B11 --> P14
  GR --> N1
  KP --> N2

  classDef ai fill:#17324d,stroke:#0b1b2b,color:#fff,stroke-width:2px;
  classDef cv fill:#0f766e,stroke:#0a4f4a,color:#fff,stroke-width:2px;
  classDef code fill:#e2e8f0,stroke:#64748b,color:#1b2430,stroke-width:2px;
  classDef check fill:#fde68a,stroke:#b45309,color:#1b2430,stroke-width:2px;
  classDef mix fill:#e2e8f0,stroke:#17324d,color:#1b2430,stroke-width:3px,stroke-dasharray:6 3;
  classDef grp fill:#fef3c7,stroke:#b45309,color:#1b2430,stroke-width:2px;
  classDef note fill:#f8fafc,stroke:#94a3b8,color:#334155,stroke-dasharray:4 3;
```

## หมายเหตุสั้นๆ (จากคอลัมน์ "แก้อะไร / ทำไม")

- **pass 1:** 22 จาก 53 เล่มเป็น PDF จาก CAD มีข้อความฝังอยู่แล้ว · OCR ไทยต้อง ≥ 180 dpi ไม่งั้นสระหลุด · OCR ทำด้วย Python ไม่ให้โมเดลอ่านเอง (t05 เคยหลอนชื่อบ้านเทรน) · ภาพชุดเทรนต้องทำ OCR ก่อนเทรน
- **pass 2:** หน้าเดียวมีหลายวิว (บ้าน 83b8e52c หน้า 20 มีแปลน 2 ชั้นในแผ่นเดียว เคยอ่านเป็น F1 หมด) · ข้อความจาก pass 1 เข้า prompt ได้เมื่อ t07 เทรนด้วยรูปแบบนี้ · หน้ารูปตัดส่งเป็น section แล้วไปคัดชนิดที่ pass 4
- **pass 3:** หน้ารูปตัดมีคาน เสา ฐานรากปนกัน ต้องตัดเป็นรูปย่อยก่อนถึงคัดชนิดได้ · จุดอ่อน: ตัดผ่ากลางรูปใหญ่ · ตารางรวมเป็นก้อนเดียว · มาร์คใต้รูปหลุด
- **pass 4:** กติกาที่เสนอ B/GB → คาน · F/PC → ฐานราก · C → เสา · แยกเป็นขั้นของตัวเองเพื่อวัดความแม่นการคัดแยกจากการตัด
- **pass 5:** กริดผิดตัวเดียว BOQ เกิน 30.8% (อ่านได้ 0/6/12 แทน 3+3) จึงต้องตรวจก่อนแนบเข้า prompt · รูปด้านเป็นที่เดียวที่พิมพ์ระดับ
- **pass 6:** ระดับชั้นเคยเป็น 3.00 ม. ทุกชั้น (บ้าน 174 สูงจริง 2.90–3.60) · วิวแปลนที่ไม่มีระดับต้องเห็นเป็นธง ไม่ใช่เงียบ
- **pass 7:** cv2 มีแม่แบบเสา/ฐานราก/คาน ไม่มีพื้น → slab_plan ข้าม pass 7 และไม่เข้า pass 12
- **pass 8:** 3 มุมคือขั้นต่ำ · ฟิตด้วยทุกเส้นที่หาเจอทนกว่าและได้ค่าคลาดไว้ตรวจ · แผ่นที่มีสองแปลนต้องทำทีละครอป
- **pass 9:** ปลายคานที่ไม่อยู่บนเส้นที่มีชื่อต้องใช้ชื่อเส้น dummy · ให้โมเดลเห็นเส้นบนภาพแทนการเดา · ภาพชุดเทรนต้องวาดแบบเดียวกัน
- **pass 12:** รูปแบบคำใบ้ต้องมีในชุดเทรน t07 ไม่งั้นห้ามส่ง
- **pass 13:** วัดจาก CV อย่างเดียวเคยได้ 0/9 หน้าในงานจริง · เวกเตอร์วัดได้ 68/98 หน้า CAD (แปลนคาน 38/47) · ห้ามเอาค่าที่วัดไปทับผลอ่าน
- **pass 14:** กติกาอยู่ชีต "pass10 combine" (ชื่อชีตเดิม)
