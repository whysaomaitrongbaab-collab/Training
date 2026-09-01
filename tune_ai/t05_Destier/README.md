# t05_Destier — ทุกอย่างที่ "ใช้จริง" ของ Destrier รวมไว้ที่เดียว

โฟลเดอร์นี้คือชุด **สำเนา** (copy ไม่ใช่ move) ของทุกไฟล์ที่ยังใช้งานจริงในระบบ Destrier
ทั้งฝั่งเทรนโมเดล (repo `Training`) และฝั่งต่อเข้าเว็บ (repo `Constistant`) — รวบมาไว้ที่เดียว
เพื่อให้เห็นภาพรวมทั้งระบบโดยไม่ต้องไล่ 2 repo

⚠️ **ไฟล์ต้นฉบับทุกไฟล์ยังอยู่ที่เดิม ไม่ได้ย้าย/ลบ** — `worker.py` ตัวที่รันจริงคือตัวใน
`Constistant/server/purson-worker/`, ข้อมูลเทรนจริงคือตัวใน `tune_ai/t05_Courser/`
ที่นี่คือสำเนาไว้ดูภาพรวม **ถ้าจะแก้โค้ด ให้แก้ที่ต้นฉบับ แล้วค่อยก็อปมาทับที่นี่ใหม่**
(เหตุผล: ต้นฉบับมีสคริปต์อื่นอ้าง path ตรงๆ อยู่ ย้ายแล้วเสี่ยงพังตอนรันจริงบนเครื่องเช่า)

## โครงสร้าง

```
run_this/            ← ฝั่ง Constistant: ตัวรันจริงวันพรีเซนต์
  GO.bat, go.py         เมนูเดียวจบ (ดับเบิลคลิก GO.bat)
  presentation.py       เช่า GPU + เปิดโมเดล + ต่อ tunnel + smoke test + destroy
  serve_purson.py       เปิดโมเดลเป็น HTTP endpoint บนเครื่องเช่า (ไม่ใช้ vLLM เพราะ LoRA MoE shape ไม่ตรง)
  worker.py             ตัวคุยกับ Supabase queue จริง (poll job → เรียกโมเดล → เขียนผลกลับ)
  pass3_measure.py      วัดตำแหน่งจริงจากพิกเซลเทียบ grid master (import โดย worker.py)
  test_worker.py        self-check ของ worker (รัน `python test_worker.py`)
  worker_config.example.json   ตัวอย่างค่าตั้ง (ของจริงมี service key ห้าม commit — ไม่อยู่ในนี้)
  README.md, คู่มือวันพรีเซนต์.md   คู่มือฉบับเต็ม

prompts/              ← จาก t04_Purson: prompt ตัวจริงที่ worker.py โหลดตอนรัน (ยืนยันจาก grep worker.py)
  _common.md             กฎร่วมทุก pass
  pass0/prompt.md        prompt คัดแยกประเภทหน้า
  pass2/<subtask>/prompt_<subtask>.md   prompt แยกตาม subtask (gridline/plan_beam/…) 9 ไฟล์
  หมายเหตุ: แม้โมเดล t04 จะเลิกใช้ไปแล้ว แต่ "prompt" ชุดนี้ยังเป็นของจริงที่ worker.py
  อ่านอยู่ทุกครั้งที่รัน (PURSON_PROMPTS_DIR ชี้ไปที่ tune_ai/t04_Purson ตัวจริง)

training/             ← จาก t05_Courser: สายการเทรนจริงที่ผลิต Destrier (pass0_derive → build_4pass → train)
  train_fold0-3.jsonl / val_fold0-3.jsonl   ★ ข้อมูลเทรนจริงที่ใช้ผลิตโมเดล

merge_model/          ← รวม 4 fold (LoRA) เป็น Destrier ตัวเดียว (model soup)
  merge_adapters_soup.py, soup_safetensors.py, verify_hf_push.py

proof/                ← หลักฐานว่า Destrier อ่านแบบได้จริง (ไม่ใช่แค่เทรนเสร็จ)
  op04_run.py, op04_score.py, op04_gpu_setup.sh
  01_op04_sampling_ผ่าน/   ผลวัด recall จริง: strict 11.8% · ให้อภัยชื่อ 88.2% · รายตำแหน่ง 43.5%

web_integration/       ← ฝั่งเว็บ Constistant คุยกับระบบนี้ยังไง
  pursonVision.js          ฝั่ง browser: อัปโหลดหน้า PNG + insert job ลงคิว
  drawing-purson.js        UI หน้ารอ/แสดงผลใน Drawing Intelligence
  supabase_functions_purson-vision/index.ts   Edge Function โหมด direct call (secret คีย์ฝั่ง server)
```

## สิ่งที่ **ไม่** เอามาใส่ (ตัดใจแล้ว ไม่ใช่ลืม)

- **t04_Purson (โมเดล) / t44_Voldemort ทั้งคู่** — โมเดลพังทั้งคู่ เก็บเป็นบทเรียนไว้ที่เดิม
  (ดู `INVENTORY.csv` หมวด 12/13) — เอามาเฉพาะ "prompt" ของ t04 ที่ worker.py ยังใช้จริง
- **ผลทดสอบที่พัง/ซ้ำซ้อน** จาก `destrier_test_house/results/` (02 greedy พัง, 03/04 log เช่า GPU,
  05 e2e dry-run, 06/07 smoke ก่อนมีระบบ pass) — ของจริงมีครบที่ `t05_Courser/destrier_test_house/results/`
  ถ้าอยากดูประวัติทั้งหมด
- **สคริปต์ dev/debug ใน `server/purson-worker/`** ที่ไม่ได้รันตอนใช้งานจริง เช่น
  `sim_house_run.py`, `sim_house01.py`, `test_e2e_*.py`, `validate_pass3_real.py`, `presentation.py`
  (❌ ผิด — presentation.py เอามาแล้วอยู่ใน run_this/) — ไฟล์ทดสอบ/จำลองที่เหลือยังอยู่ต้นฉบับ
- **น้ำหนักโมเดล (adapter_model.safetensors)** — อยู่บน HuggingFace แล้ว (push_to_hub อัตโนมัติ
  ตอนเทรน) ไม่ต้องมีสำเนาไฟล์ใหญ่ๆ ซ้ำในนี้
- **worker_config.json ตัวจริง** — มี service role key ห้าม commit/ก็อปที่ไหนทั้งนั้น

## ถ้าจะรันจริงจากที่นี่

อย่ารันจากที่นี่ — path ภายในของแต่ละสคริปต์ (`HERE`, `PROMPTS_DIR` ใน `worker_config.json`)
ยังอ้างอิงตำแหน่งเดิม (`t05_Courser/`, `t04_Purson/`) ไม่ใช่ที่นี่ ที่นี่ไว้ **อ่าน/อ้างอิง** เท่านั้น
