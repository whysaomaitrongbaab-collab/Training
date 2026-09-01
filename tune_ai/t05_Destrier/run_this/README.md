# Purson worker — ต่อโมเดลของเราเข้า Constistant

Purson = โมเดลถอดแบบก่อสร้างที่เทรนเอง (t03: Qwen3.6-35B-A3B + LoRA `Sicilian44/t03` ·
t04: InternVL3-78B + soup `Sicilian44/Purson-weights`) ระบบนี้ทำให้เว็บ Constistant
สั่งถอดแบบผ่าน Purson ได้ โดยผ่านคิวบน Supabase:

```
Constistant (browser)                       Supabase                    เครื่องที่รัน worker.py
 pursonVision.js ── upload หน้า PNG ──▶  storage: purson-jobs
                 ── insert job ───────▶  table: purson_jobs  ◀── poll ── worker.py
                 ◀─── poll ผล ────────                                      │ ยิง OpenAI API
                                                                            ▼
                                                    GPU endpoint (serve_purson.py + Purson)
```

## โหมด A vs B — ต่างกันแค่ "worker.py รันที่ไหน" โค้ดชุดเดียวกันทุกไฟล์

| | B: PC มะขาม + เช่า GPU รายชั่วโมง (vast.ai) | A: เช่า server ถาวร |
|---|---|---|
| worker.py รันที่ | PC มะขาม | บน server เดียวกับโมเดล |
| `PURSON_GPU_URL` | `http://<vast-ip>:<port>` (แก้ทุกรอบเช่า ที่นี่ที่เดียว) | `http://localhost:8000` |
| เว็บต้องรู้อะไรเพิ่ม | ไม่ต้อง — คุยกับ Supabase อย่างเดียว | ไม่ต้อง — เหมือนกันเป๊ะ |

(Edge Function `purson-vision` มีโหมด direct สำหรับยิงทีละ call เมื่อมี URL ถาวร —
ตั้ง secret `PURSON_ENDPOINT_URL` — แต่งานถอดทั้งหลังใช้คิวเสมอ เพราะกินเวลาเป็นชั่วโมง)

## ติดตั้ง (เครื่องที่จะรัน worker)

1. `pip install requests`
2. สร้าง `worker_config.json` ข้างไฟล์นี้ (หรือตั้ง env ชื่อเดียวกัน):
```json
{
  "SUPABASE_URL": "https://vhcfcbogydxsukqedwdp.supabase.co",
  "SUPABASE_SERVICE_KEY": "<service role key — ห้าม commit>",
  "PURSON_GPU_URL": "http://<ip>:<port>",
  "PURSON_GPU_KEY": "",
  "PURSON_MODEL": "purson",
  "PURSON_PROMPTS_DIR": "d:\\00mk\\steel project\\training\\Training\\tune_ai\\t04_Purson"
}
```
   `PURSON_PROMPTS_DIR` ชี้ที่โฟลเดอร์ t04_Purson (ต้องมี `_common.md`, `pass0/prompt.md`,
   `pass2/<subtask>/prompt_<subtask>.md`) — บน server เช่า (โหมด A) clone Training repo
   หรือ copy เฉพาะโฟลเดอร์นี้ขึ้นไป **prompt ต้องตรงกับที่ใช้เทรนเสมอ** worker ประกอบ
   prompt แบบเดียวกับ build_dataset_t03.py เป๊ะ (COMMON − glossary + PROMPT block +
   GRID MASTER ต่อท้ายเฉพาะ plan_*)
3. apply migration `supabase/migrations/20260830000001_purson_jobs.sql` (ครั้งเดียว)
4. `python test_worker.py` ต้องขึ้น OK
5. `python worker.py`

## เปิด GPU endpoint (บนเครื่องเช่า) — `serve_purson.py`

`presentation.py up` ทำให้อัตโนมัติทั้งหมด (scp ขึ้นไป + สั่งรัน) ไม่ต้องพิมพ์เอง
สั่งมือเมื่อจะดีบั๊ก:

```bash
pip install unsloth xgrammar fastapi uvicorn pillow
python serve_purson.py --adapter Sicilian44/t03 --port 8000
python serve_purson.py --base            # ไม่ใส่ adapter (เทียบ untuned)
```

### ⚠️ ทำไมไม่ใช้ vLLM (ตรวจจริง 2026-08-30 — ก่อนเช่าการ์ด)

เปิด `adapter_model.safetensors` ดูจริงแล้วพบว่า LoRA ของ MoE expert เก็บเป็น

```
...mlp.experts.lora_A.weight   shape=[4096, 2048]   # 4096 = 256 experts × rank 16
```

= รูปแบบของ Unsloth เอง **ไม่ตรงกับที่ vLLM รับทั้งสองแบบ** (3D fused ต้องเป็น
`experts.gate_up_proj.lora_A`, 2D megatron ต้องเป็น `experts.0.gate_proj.lora_A`)
และ `is_3d_lora_weight` ประกาศผิด vLLM **ไม่ error แต่ให้ผลขยะเงียบๆ** —
ถ้าไม่ตรวจก่อน จะรู้ตัวหลังโหลดโมเดลไปแล้ว 45 นาที หรือแย่กว่านั้นคือไม่รู้ตัวเลย

`serve_purson.py` จึงโหลดด้วย Unsloth ตรงๆ ยกโค้ดโหลด/generate มาจาก
`infer_house_t03.py` ที่รันผ่านจริงแล้ว 33 งาน — พูดภาษา OpenAI เหมือนเดิมทุกอย่าง
worker ไม่รู้ความต่าง ถ้าวันหนึ่งแปลง adapter เป็นรูปแบบที่ vLLM รับได้ ก็สลับกลับได้ทันที

**t04 (InternVL3-78B) ยังใช้ไม่ได้** — เทรนด้วย LLaMA-Factory ไม่ใช่ Unsloth
`presentation.py up --model t04` จะปฏิเสธพร้อมบอกเหตุผล ต้อง port ตัวโหลดจาก
`infer_house_t04.py` (transformers+peft) เข้ามาใน serve_purson.py ก่อน

## วันพรีเซนต์ (เปิด GPU เฉพาะตอนใช้) — `presentation.py`

เครื่องเช่าเปิดแค่ช่วงพรีเซนต์ ที่เหลือ destroy ทิ้ง สคริปต์เดียวจัดการครบ:

```bash
# ล่วงหน้า ~1 ชม. ก่อนพรีเซนต์ (ลง deps + โหลดโมเดล ~70GB กินเวลา 15-45 นาที)
python presentation.py up              # เช่าการ์ด → ส่ง+เปิด serve_purson.py → tunnel → รอพร้อม
python presentation.py smoke           # ยิงทดสอบ ต้องได้ JSON กลับ
python worker.py                       # (terminal ที่ 2) เริ่มรับงานจากเว็บ

# ระหว่างวัน
python presentation.py status          # เครื่อง/tunnel/เครดิต
python presentation.py tunnel          # ต่อ tunnel ใหม่ถ้าหลุด

# จบวัน — ห้ามลืม ไม่งั้นเผาเงินทั้งคืน
python presentation.py down            # destroy + ปิด tunnel + ยืนยันคืนครบ
```

ทำไม `PURSON_GPU_URL` ใน worker_config.json ตั้งเป็น `http://localhost:8000` แล้วไม่ต้องแก้อีกเลย:
tunnel (`ssh -N -L 8000:localhost:8000`) แปลงให้ทุกรอบเช่า — IP เครื่องเช่าเปลี่ยนก็กระทบแค่
คำสั่ง ssh ที่ presentation.py สร้างเองจาก `vastai show instances` ไม่แตะ config ไหนทั้งนั้น
และไม่ต้องเปิดพอร์ตสาธารณะบนเครื่องเช่า (ทางที่ vast.ai แนะนำเอง)

`--model t03` (default) = Qwen3.6-35B + `Sicilian44/t03` บนการ์ด 96GB ใบเดียว — **เส้นทางที่
พิสูจน์แล้วฝั่งโมเดล** (แต่ตัว serve_purson.py เองยังไม่เคยรันบน GPU จริง ต้องซ้อม 1 รอบ
ก่อนวันงาน) · `--model t04` **ถูกปฏิเสธโดยตั้งใจ** จนกว่าจะ port ตัวโหลด InternVL3 เข้ามา

## ความปลอดภัย
- service role key อยู่ในเครื่องที่รัน worker เท่านั้น ไม่เคยเข้า browser/repo
- browser เขียนได้แค่ job ของตัวเอง (RLS) และห้าม update สถานะ (worker เท่านั้น)
- bucket `purson-jobs` เป็น private, path ขึ้นต้นด้วย uid เจ้าของ
