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

### 🔴 ระเบิดเวลา 17 ก.ย. 2026 — `pip install -U unsloth` ทำให้ผลเป็นขยะเงียบๆ

`unsloth-zoo` PR #1232/#1269 (merge 17 ก.ย. 2026) เปลี่ยนวิธีอ่าน `lora_B` ของชั้น MoE expert
จาก **grouped_by_expert** (expert ช้าสุด) ไปเป็น **rank_major** (expert เร็วสุด ตาม PEFT)

adapter ของเราทั้ง `t03` และ `destrier` อัปก่อนวันนั้น = **grouped_by_expert ทั้งคู่**
(ดูได้จากที่ `adapter_config.json` ไม่มีคีย์ `lora_B_layout`) แต่ `onstart_cmd` ใช้
`pip install -U unsloth` ไม่ pin เวอร์ชัน → **เครื่องที่เช่าหลัง 17 ก.ย. จะอ่าน adapter ผิดทันที
ไม่ error แต่ expert ทุกตัวจับคู่กับ rank คอลัมน์ผิด ผลลัพธ์เป็นขยะ**

แก้แล้ว (2026-09-20): `presentation.py` ส่ง `UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert`
ตอนสั่งรันเซิร์ฟเวอร์เสมอ — เวอร์ชันเก่าไม่รู้จักตัวแปรนี้ก็แค่เมินทิ้ง ปลอดภัยทั้งสองทาง
`python test_serve_presets.py` มีด่านตรวจข้อนี้ไว้แล้ว

**นี่คือคำอธิบายจริงของบั๊ก "merge แล้วได้ขยะ" ที่ฆ่า GGUF ของ t01/t02 เมื่อ ก.ค. 2026** —
ไม่ใช่เพราะ peft เวอร์ชันเก่าอย่างที่เคยเข้าใจ แต่เพราะ merge path เรียก PEFT `get_delta_weight`
ซึ่งอ่าน rank_major ขณะที่ตอนเทรน forward เป็น grouped_by_expert (ไดอารี่ 2026-07-28 ข้อ 7
วัดไว้เองว่า "ΔW รูปร่างถูก scaling ถูก แต่ค่าที่ใส่เข้าไปขนาดเล็กผิดปกติ" — ตรงกับอาการนี้เป๊ะ)

## เส้นทางเร็ว (2026-09-20) — merge เป็น dense แล้วเสิร์ฟด้วย vLLM/SGLang

วัดแล้วว่าความช้าตอนนี้ **97-98% เป็น software overhead ไม่ใช่การ์ดจอ**: ได้จริง ~6-8 token/วิ
ทั้งที่การ์ดควรทำได้ ~300 token/วิ (HF `.generate()` ไม่มี CUDA graph + ชั้น MoE ไม่ fuse)
→ ทางแก้ที่ได้ผลจริงคือเปลี่ยนตัวเสิร์ฟ ไม่ใช่เปลี่ยนการ์ด

เหตุผลที่เคยตัด vLLM ทิ้งเป็นปัญหาของ **runtime LoRA loading** ล้วนๆ — พอ merge เข้า base แล้ว
ไม่มี adapter เหลือให้ parse ผิด เช็คพอยต์กลายเป็น Qwen3.6-35B-A3B ธรรมดาที่เสิร์ฟได้ native

```bash
# 1) merge (ครั้งเดียว บนเครื่องเช่า ดิสก์ ≥250GB) — Training/tune_ai/
python merge_lora_to_base.py --inspect-only          # ฟรี ไม่ใช้ GPU ทำก่อนเสมอ
python merge_lora_to_base.py --push dacarokann/destrier-merged

# 2) ตรวจว่า merge ถูกจริง — ⛔ ห้ามข้าม "รันจบไม่ error" ไม่ได้แปลว่าถูก
python verify_merge.py --check-ab --base <hf-cache> --merged <dir> --adapter <dir>   # ฟรี
python verify_merge.py --fingerprint adapter --adapter <dir> --out ref.pt            # ใช้ GPU
python verify_merge.py --fingerprint merged  --merged <dir>  --out mrg.pt
python verify_merge.py --fingerprint base    --base-repo unsloth/Qwen3.6-35B-A3B --out base.pt
python verify_merge.py --compare ref.pt mrg.pt base.pt

# 3) เสิร์ฟ — worker.py ไม่ต้องแก้อะไรเลยสักบรรทัด
python presentation.py up --model destrier-sglang    # แนะนำ (prefix cache ช่วยงานเรามาก)
python presentation.py up --model destrier-vllm      # ทางเลือก
```

**ทำไม SGLang น่าจะดีกว่าสำหรับงานนี้:** `worker.py` ยิงทีละหน้าโดยใช้ instruction prompt
ก้อนเดิม (~1,000 token) ซ้ำทุกหน้า → RadixAttention cache prefix ข้าม request ได้
= ลด latency **ต่อคำขอเดี่ยว** ตรงๆ ไม่ใช่แค่ throughput รวม

⚠️ ทั้งสองทางยังไม่เคยรันจริงบนการ์ด — ตัวเลข `--max-model-len 40960` / `--mem-fraction-static
0.78` คำนวณจากงานหนักสุด (gridline 4 ภาพ) แต่ยังไม่ได้วัด VRAM จริง ถ้า OOM ตอนเปิด
**ให้ลด `--gpu-memory-utilization` ก่อน อย่าลด context** (จะพังเฉพาะงานหนักซึ่ง smoke test มองไม่เห็น)

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

### แผน A (2026-09-27) — worker.py รันบนการ์ดเช่าเอง ไม่ใช่บนคอมเรา

เมนู GO.bat ข้อ 1/3 เปิดตัวรับงาน**บนการ์ด**ให้เองแล้ว (`presentation.py worker-up`) — ยิงโมเดลที่
localhost ของการ์ด คุยกับ Supabase ด้วยเน็ตของการ์ด คอมเราแค่สั่งเปิด **เน็ตคอมหลุดกลางงานก็ไม่สะดุด**
ส่งขึ้นไปก้อนเดียว ~0.14 MB: worker + prompt จาก `PURSON_PROMPTS_DIR` ชุดเดียวกับที่คอมนี้ใช้ +
organize.py/cv_scan.py/แม่แบบ CV (วางโครงเลียน Training repo) + config ที่เปลี่ยนแค่ GPU URL/path

```bash
python presentation.py worker-up     # ส่ง+เปิด (กดซ้ำได้ ไม่เปิดซ้อน) — dependency ลงแยกที่ /workspace/wdeps
python presentation.py worker-log    # ไม่มีหน้าต่างให้ดู ดู log ตรงนี้ (เมนู 9 → 8)
python presentation.py worker-down   # หยุดตัวบนการ์ด (คืนการ์ดไม่ต้องสั่งก่อน เครื่องหายทั้งก้อนอยู่แล้ว)
```

- เปิดบนการ์ดไม่สำเร็จ → เมนูสั่ง `worker-down` แล้วถอยไปเปิดหน้าต่างบนคอมแบบเดิมเอง
- มีหน้าต่างรับงานบนคอมเปิดค้างอยู่แล้ว → ใช้ตัวนั้น ไม่เปิดบนการ์ดซ้อน — **ตัวรับงานสองตัวยิง
  Unsloth พร้อมกัน = ค้าง** (ตัวเสิร์ฟรับทีละคำขอ)
- ไม่มีเสียงตอนงานเสร็จ (ตัวรับงานไม่ได้อยู่บนคอมเรา) — ดูความคืบหน้าที่หน้าเว็บ
- ตรวจแล้วแบบไม่ต้องเช่าการ์ด: `python test_worker_remote.py` (import worker จาก bundle จริง,
  pgrep ไม่เจอตัวเอง, setsid --fork) · **ยังไม่เคยรันบนการ์ดจริง**

ทำไม `PURSON_GPU_URL` ใน worker_config.json ตั้งเป็น `http://localhost:8000` แล้วไม่ต้องแก้อีกเลย:
tunnel (`ssh -N -L 8000:localhost:8000`) แปลงให้ทุกรอบเช่า — IP เครื่องเช่าเปลี่ยนก็กระทบแค่
คำสั่ง ssh ที่ presentation.py สร้างเองจาก `vastai show instances` ไม่แตะ config ไหนทั้งนั้น
และไม่ต้องเปิดพอร์ตสาธารณะบนเครื่องเช่า (ทางที่ vast.ai แนะนำเอง)

`--model t03` (default) = Qwen3.6-35B + `Sicilian44/t03` บนการ์ด 96GB ใบเดียว — **เส้นทางที่
พิสูจน์แล้วฝั่งโมเดล** (แต่ตัว serve_purson.py เองยังไม่เคยรันบน GPU จริง ต้องซ้อม 1 รอบ
ก่อนวันงาน) · `--model t04` **ถูกปฏิเสธโดยตั้งใจ** จนกว่าจะ port ตัวโหลด InternVL3 เข้ามา

## ความปลอดภัย
- service role key อยู่ในเครื่องที่รัน worker เท่านั้น ไม่เคยเข้า browser/repo
- ⚠️ แผน A = key ขึ้นไปอยู่บนเครื่องของโฮสต์เช่าด้วย (ไฟล์ chmod 600) — คืนการ์ดแบบ destroy
  ดิสก์หายทั้งก้อน แต่ระหว่างเช่าโฮสต์เข้าถึงดิสก์ได้ในทางเทคนิค · ไม่อยากรับความเสี่ยงนี้กับงานไหน
  ให้ใช้หน้าต่างรับงานบนคอมแทน (`python worker.py`)
- browser เขียนได้แค่ job ของตัวเอง (RLS) และห้าม update สถานะ (worker เท่านั้น)
- bucket `purson-jobs` เป็น private, path ขึ้นต้นด้วย uid เจ้าของ
