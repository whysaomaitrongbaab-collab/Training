# pattern ไหนเชื่อมกับอันไหน — primary rawjson

นับจากไฟล์จริง 16 พ.ย. 69 (194 บ้าน บ้านละหนึ่งฉบับ)

```mermaid
flowchart LR
  subgraph PLAN["แปลน — มีตำแหน่งบนกริด"]
    BP["beam_plan<br/>แปลนคาน"]
    FP["footing_plan<br/>แปลนฐานราก"]
    RFP["roof_frame_plan<br/>แปลนโครงหลังคา"]
    EP["etc_plan<br/>แปลนอื่นๆ"]
  end

  subgraph SPEC["ที่มาของสเปก — ขนาดและเหล็ก"]
    SEC["section<br/>แบบขยาย / รูปตัด"]
    SCH["schedule<br/>ตาราง"]
    SEC -.-|"ขัดกัน: section ชนะ"| SCH
  end

  subgraph VIEW["หน้าที่ให้ระดับและระยะ"]
    SIDE["side_profile<br/>รูปด้าน / รูปตัดอาคาร"]
    SITE["site_plan<br/>ผังบริเวณ"]
    ROOF["roof_plan<br/>แปลนหลังคา (สถาปัตย์)"]
  end

  GM[("grid_master<br/>กริดหลักของบ้าน<br/>(ไฟล์หน้า00)")]
  NOTES["notes<br/>ข้อกำหนดทั่วไป"]
  BOQ["material_list<br/>ใบ BOQ"]
  WEB[["Constistant<br/>ตัวแปลงข้อมูล → BOQ / BBS"]]

  PLAN ==>|"มาร์คเดียวกัน → ต่อสเปก"| SPEC
  PLAN -->|"grid_source 88–100%"| GM
  SPEC -->|"17–48%"| GM
  VIEW -->|"49–83% · ระดับ z_levels"| GM

  GM -->|"ตำแหน่ง + ระยะช่วง"| WEB
  PLAN -->|"ชิ้นส่วน + จำนวน"| WEB
  SPEC -->|"ขนาด + เหล็ก"| WEB
  NOTES -->|"fc · fy · ระยะหุ้ม"| WEB
  BOQ -.->|"เก็บไว้ ยังไม่เข้า BOQ"| WEB

  subgraph ALONE["ไม่เชื่อมกับหน้าอื่น"]
    IDX["index<br/>สารบัญ"]
    TTL["title<br/>หน้าปก"]
    SYM["symbol<br/>สัญลักษณ์"]
    MISC["misc<br/>เบ็ดเตล็ด"]
    UNK["unknown"]
  end

  subgraph EMPTY["มีในสเปก ยังไม่มีไฟล์"]
    BBS["bbs_schedule<br/>ตารางตัดเหล็ก"]
    SOIL["soil_boring_log<br/>ผลเจาะดิน"]
  end
```

## ตัวเลขแยกราย pattern

**ต่อสเปก** (`element_id` เดียวกันโผล่ทั้งในแปลนและหน้าสเปกของบ้านเดียวกัน — สเปก §7) · จำนวนมาร์คที่ตรงกัน / จำนวนบ้าน

| แปลน | → section | → schedule |
|---|---|---|
| beam_plan | 1,680 / 145 | 49 / 17 |
| footing_plan | 641 / 155 | 97 / 36 |
| etc_plan | 506 / 48 | 85 / 19 |
| roof_frame_plan | 310 / 72 | 0 |

**`grid_source`** (ไฟล์ระบุชื่อไฟล์กริดหลัก) — beam_plan, footing_plan, roof_frame_plan 100% · etc_plan 88% · roof_plan 83% · site_plan 53% · side_profile 49% · section 48% · schedule 17% · notes 1% · ที่เหลือ 0%

## หมายเหตุ
- ทุกหน้าที่พิมพ์ระยะหรือระดับ ต้องส่งตัวเลขเข้า `grid_master` (สเปก §4) — ในรูปวาดเฉพาะกลุ่มที่มี `grid_source`
- Constistant อ่าน 9 ประเภท: แปลน 4 แบบ, `section`, `schedule`, `notes`, `grid_master`, `material_list` · ที่เหลือเก็บดิบพร้อมคำเตือน
