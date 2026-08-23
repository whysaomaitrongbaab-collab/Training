# วิจัย: ใช้ Qwen grounding (pixel/bbox) เทียบกับ gridmaster เพื่อตรวจสอบคาน

สืบเนื่องจากคำถาม 2026-08-22 "เป็นไปได้ไหมให้ Qwen นับ pixel" — คำตอบตอนนั้นบอกว่าไม่คุ้ม
เพราะอ้างอิงงาน FLOORPLANVLM (`No_touch_box/docs/FLOORPLANVLM.md`) ที่ต้องเทรนใหม่ด้วยข้อมูล
pixel-aligned 300K ตัวอย่าง + RL (GRPO) ถึงจะแม่น **ค้นเน็ตเพิ่มแล้วพบว่าข้อสรุปนั้นไม่ครบ** —
มีอีกเส้นทางที่ไม่ต้องเทรนใหม่เลย เพราะเป็นความสามารถที่ติดมากับโมเดลฐานอยู่แล้ว

## แก้ไขจากที่ตอบไปก่อนหน้า

FLOORPLANVLM คือกรณี "สอนโมเดลให้ **แทนที่** grid_ref ด้วยพิกัด" — อันนั้นแพงจริงตามที่ตอบไป
แต่สิ่งที่ค้นเจอใหม่คือ **Qwen3-VL (โมเดลฐานของ t02) มี 2D grounding ในตัวอยู่แล้ว** ไม่ใช่สิ่งที่ต้อง
ทูนเพิ่ม — เป็นความสามารถที่มากับ pretrained ปกติ (เหมือน Qwen2-VL รุ่นก่อนหน้าที่มี grounding
มาตั้งแต่ arXiv 2308.12966) เรื่องนี้เปลี่ยนคำตอบจาก "ไม่คุ้มเลย" เป็น **"ลองได้ฟรี ไม่ต้องเทรนใหม่
— แต่ใช้เป็นตัวช่วยตรวจสอบ (QA layer) ไม่ใช่ตัวแทนที่ grid_ref"**

## รูปแบบ output ของ Qwen3-VL grounding

- พิกัดเป็น**สเกลปกติ 0-1000** ไม่ใช่ pixel ตรงๆ (ทำให้ไม่ผูกกับความละเอียดภาพหนึ่งเดียว
  — แก้จุดที่กังวลไว้เดิมเรื่อง "pixel ผูกกับสแกนเดียว" ได้ระดับหนึ่ง เพราะแปลงกลับเป็น pixel จริง
  ด้วยการหาร 1000 คูณความกว้าง/สูงภาพทีหลังได้)
- แต่ละวัตถุออกมาเป็น `[x1, y1, x2, y2]` ในรูป JSON พร้อม label
- รองรับทั้งแบบ bounding box และแบบจุด (point)

## ปัญหาการนับที่เจอ (บ้าน09 หน้า26: 48 คานจริง เหลือ 2) ไม่ใช่เรื่องแปลก — มีงานวิจัยรองรับ

- แม้ VLM ระดับ SOTA ก็ยัง**นับผิดพลาดเป็นระบบ** ความแม่น 64.0-74.7% เท่านั้น ต่ำกว่างาน visual
  reasoning ประเภทอื่นชัดเจน
- รากของปัญหา: **cross-modal attention ไม่สมดุล** — decoder โน้มเอียงไปพึ่ง text prior
  (แพทเทิร์นภาษาที่เคยเห็น) มากกว่าใช้ visual token จริงตรงหน้า — อธิบายตรงกับที่เราเห็น: โมเดล
  "รู้" ว่าแปลนคานควรมีคานเยอะๆ เรียงเป็นแพทเทิร์น แต่ไม่ได้นับจากภาพจริงทีละเส้น
- Prompt-induced hallucination: ถ้า prompt สื่อนัยว่า "ควรมี" วัตถุจำนวนหนึ่ง โมเดลมีแนวโน้ม
  หลอนเติมให้ครบตามนัยนั้น — ยิ่งของจริงมี**มากกว่า 4 ชิ้น**ยิ่งเสี่ยง (หน้าคานเรามี 48 ชิ้น
  อยู่ในโซนเสี่ยงเต็มๆ)

## เทคนิคที่ตรงประเด็นที่สุด — GroundCount (ผสม detection model เข้ากับ VLM)

แนวคิด: **อย่าให้ VLM นับเอง** — ใช้โมเดล detection แบบคลาสสิก (เช่น YOLO) หาตำแหน่ง+จำนวนวัตถุ
ก่อน แล้วป้อนผลนั้นเข้าไปเป็นบริบทให้ VLM ใช้ตอนตอบ (ไม่ใช่ให้ VLM เดาเอง)

3 วิธีที่งานวิจัยลอง:
1. **Prompt augmentation** — เอาผล detection มาเขียนเป็นข้อความแทรกใน prompt (ได้ 81.3% แม่นขึ้น)
2. **Architectural fusion** — ผสม feature ของ detection เข้าตัวโมเดลตรงๆ (ต้องแก้สถาปัตยกรรม
   ไม่เหมาะกับ LoRA fine-tune ของเรา)
3. **Combined** — ทำทั้งสองอย่าง

วิธีที่ 1 ใช้ได้กับงานเราทันทีโดยไม่ต้องแก้โมเดล — คล้ายกับที่เราทำอยู่แล้วสำหรับ grid circles
(`overlay_gt_vs_ai_house09.py` ใช้ `cv2.HoughCircles` หาวงกลม label ก่อน ไม่ได้ให้ AI นับวงกลมเอง)
**ส่วนที่ยังไม่ได้ทำคือขยายแนวคิดเดียวกันไปที่ตัวเส้นคาน** — ใช้ line detection (Hough line
transform) หาว่าบนภาพมีเส้นตรงกี่เส้นในโซนที่ควรเป็นคาน แล้วป้อนจำนวนนั้นเป็น hint ใน prompt
("ภาพนี้ตรวจพบเส้นตรงที่น่าจะเป็นคานประมาณ N เส้น อ่านให้ครบ")

## งานวิจัยในโดเมนแบบก่อสร้าง/วิศวกรรมโดยตรง — ยืนยันทิศทาง t03 ว่าถูกทาง

พบ 2 งานที่ทำ pipeline เดียวกับที่ t03 กำลังออกแบบอยู่ (multi-pass, detection ก่อน VLM ทีหลัง):

- **arXiv 2510.21862** — 3 stage: YOLOv11-det หา layout (view/title block/notes) →
  YOLOv11-obb หา annotation ทีละจุด (ขนาด, GD&T) → VLM (Donut-based) อ่านความหมาย
  ผลลัพธ์: Numerical VLM แม่น 96.3% (F1) เมื่อรับ input ที่ detection ตัดมาให้แล้ว
  เทียบ Alphabetical VLM ที่แม่นแค่ 67.2% (งานที่ยังต้องตีความเปิดกว้างกว่า)
- **arXiv 2506.17374** ("From Drawings to Decisions") — hybrid vision-language framework
  แบบเดียวกัน สำหรับ manufacturing drawing

**นัยสำหรับเรา:** ตัวเลข 96.3% vs 67.2% ในงานเดียวกันบอกชัดว่า **งานที่ detection ทำให้ก่อนแล้ว
VLM แค่ "อ่านความหมาย" แม่นกว่างานที่ VLM ต้อง "หา+นับ+อ่าน" เองทั้งหมดมาก** — ตรงกับที่
`plan_beam` subtask ของเราพัง (ต้องทำทั้งหาเส้น + นับ + จับคู่ grid + อ่านสเปกในทีเดียว)
สนับสนุนแนวทาง Pass 1 ที่วางไว้แล้ว (`pass1_organize.py` ตัด multi-view ก่อนส่งเข้า VLM) และ
เสนอเพิ่มอีกชั้น: **ให้ classical CV ตรวจนับเส้นก่อน ไม่ใช่แค่ตัด crop**

## เทคนิคเสริมอีกอัน — Two-stage: อธิบายเป็นภาษาก่อน ค่อยแปลงเป็น JSON

หลายงาน (LookPlanGraph, MinerU2.5) พบว่าการบังคับให้ VLM ตอบ JSON โครงสร้างซับซ้อนในช็อตเดียว
เพิ่มการหลอน — แยกเป็น 2 ขั้น (1) ให้อธิบายสิ่งที่เห็นเป็นข้อความธรรมชาติก่อน (2) ค่อยแปลงข้อความ
นั้นเป็น JSON ในอีกรอบ ลด syntax error และการหลอนความสามารถที่ไม่มีจริง — MinerU2.5 เรียกว่า
"decouple layout analysis จาก content recognition"

ตรงกับสิ่งที่ `pass2_used/plan.md` เขียนไว้แล้วบางส่วน (คำสั่ง "หยุดพิมพ์ทันทีถ้าเห็นตัวเองวนซ้ำ")
แต่ยังไม่ได้แยกเป็น 2 pass จริง — น่าจะลองในรอบทดสอบ prompt ของ t03

## ข้อเสนอที่ใช้ได้จริงกับสิ่งที่มะขามต้องการ — "ดูบีมเทียบ gridmaster"

**อย่าใช้ grounding แทนที่ grid_ref ในสเปก rawjson** (เหตุผลเดิมยังยืนยัน: derived value,
ผูกกับสแกนหนึ่งเดียว, grid_ref เองพิสูจน์แล้วว่าวาง overlay ถูกต้อง 45/48-52/53 ตัว)

**แต่ใช้ grounding เป็นชั้นตรวจสอบแยกต่างหาก (QA cross-check), ไม่ใช่ข้อมูลหลัก:**

1. รันภาพเดียวกัน 2 รอบ (คนละ prompt): รอบปกติได้ `grid_ref_start`/`grid_ref_end` ตามเดิม +
   รอบที่สองถาม grounding ตรงๆ ("ระบุ bounding box ของเส้นคานทุกเส้นที่เห็นในภาพ") ได้ `[x1,y1,x2,y2]`
2. แปลง `grid_ref_start`/`end` เป็นพิกเซลผ่าน gridmaster (สคริปต์ `overlay_gt_vs_ai_house09.py`
   ทำอยู่แล้ว) แล้ววาดทับกับ bbox จาก grounding
3. **เส้นที่ grid_ref บอกตำแหน่งหนึ่ง แต่ bbox จาก grounding อยู่คนละที่ (หรือไม่มี bbox
   ตรงนั้นเลย) = สัญญาณเตือนว่า grid_ref นั้นน่าจะหลอน** แม้ JSON จะ parse ผ่านสมบูรณ์ก็ตาม
4. **จำนวน bbox ที่นับได้จาก grounding เทียบกับจำนวน element ใน `elements[]`** เป็นตัวเช็คนับ
   ที่ตรงไปตรงมาที่สุด — ถ้า grounding นับได้ 40 เส้น แต่ `elements[]` มีแค่ 2 แถว (แบบที่เกิดขึ้น
   จริงกับหน้า26) นี่คือหลักฐานเชิงปริมาณของการยุบข้อมูล ไม่ต้องรอคนตรวจด้วยตา

## สิ่งที่ยังไม่ยืนยัน — ต้องทดสอบจริงก่อนเชื่อ

- **ยังไม่รู้ว่า adapter ของ t02 (LoRA ที่ทูนให้พิมพ์ JSON schema เฉพาะ) ยังรักษาความสามารถ
  grounding ของโมเดลฐานไว้ได้แค่ไหน** — การทูนหนักๆ ไปทาง output format หนึ่ง มีโอกาส "ลืม"
  ความสามารถอื่นบางส่วน (catastrophic forgetting) ไม่ได้เดา ต้องพิสูจน์
- ยังไม่เคยลองจริงว่า prompt ที่ขอ grounding ("ระบุ bounding box ของคาน") จะได้ output รูปแบบ
  `[x1,y1,x2,y2]` จริงจากโมเดลตัวนี้ผ่าน Unsloth หรือไม่ — รูปแบบพิเศษนี้อาจต้องใช้ special
  token บางตัว (เช่น `<|box_start|>`) ที่ chat template ของเราไม่ได้ตั้งไว้
- **ขั้นทดสอบที่ถูกที่สุดก่อนลงทุนอะไรเพิ่ม:** รอบเช่า GPU ครั้งหน้า ลองยิง prompt grounding
  ตรงๆ กับภาพเดียว (`หน้า26` บ้าน09 ที่มีอยู่แล้ว) ดูว่าได้ output รูปแบบไหนกลับมา ก่อนตัดสินใจ
  ว่าจะสร้าง pipeline 2 pass จริงหรือไม่

## Sources

- [Spatial Understanding and 2D Grounding | QwenLM/Qwen3-VL | DeepWiki](https://deepwiki.com/QwenLM/Qwen3-VL/5.2-spatial-understanding-and-2d-grounding)
- [Qwen3-VL Technical Report](https://arxiv.org/pdf/2511.21631)
- [Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond](https://arxiv.org/pdf/2308.12966)
- [GroundCount: Grounding Vision-Language Models with Object Detection for Mitigating Counting Hallucinations](https://arxiv.org/pdf/2603.10978)
- [Can Vision-Language Models Count? A Synthetic Benchmark and Analysis of Attention-Based Interventions](https://arxiv.org/html/2511.17722v1)
- [A Multi-Stage Hybrid Framework for Automated Interpretation of Multi-View Engineering Drawings Using Vision Language Model (arXiv 2510.21862)](https://arxiv.org/abs/2510.21862)
- [From Drawings to Decisions: A Hybrid Vision-Language Framework for Parsing 2D Engineering Drawings into Structured Manufacturing Knowledge (arXiv 2506.17374)](https://arxiv.org/abs/2506.17374)
- [MinerU2.5: A Decoupled Vision-Language Model for Efficient High-Resolution Document Parsing](https://arxiv.org/pdf/2509.22186)
