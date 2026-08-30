# t05 workflow — Asclepius (กลับสาย Qwen3.6-35B-A3B + ขยาย dataset ด้วย pass0 / pass2.5→3)

> ## 🟡 นี่คือเอกสารของ **รอบ t05 "Asclepius"** — สถานะ: เตรียมการ (ยังไม่เช่าการ์ด ยังไม่ build dataset ใหม่)
>
> | | |
> |---|---|
> | รอบ | **t05_Asclepius** (มะขามตั้ง 2026-08-30 — Asclepius ผู้ใช้งูหาสมุนไพร: โมเดลใช้ CV/เครื่องมือช่วยอ่านแบบ เหมือนหมอใช้งู) |
> | โมเดล | ✅ **`unsloth/Qwen3.6-35B-A3B`** (มะขามเคาะ 2026-08-30 หลัง t04/InternVL3 ล้มเหลวจาก config `crop_to_patches` — กลับสายที่พิสูจน์แล้ว: t01 recall 28.2% สูงสุดของโปรเจกต์, เทรน+export+รันโลคอลครบวงจรจริง) |
> | framework | ✅ **Unsloth** (`FastVisionModel`) — ใช้ได้จริงกับตระกูลนี้ทั้ง t01/t03; สคริปต์ฐานคือ `train_t03.py` ที่ทุกค่ามีที่มากำกับแล้ว |
> | dataset | เดิม 7 subtasks (1,020 train / 229 val, 40 หลัง) **+ ใหม่: pass0 (จำแนกหน้า) + pass3 (takeoff จากรูปมาร์ค CV)** — มะขามสั่ง 2026-08-30 "รอบนี้เอา pass0 pass2.5 และ pass3 ใส่มา" |
> | สถานะ | ยังไม่เริ่ม build — ดู "งานที่ต้องทำก่อนเทรน" ข้างล่าง มี data-gap จริง 2 จุดที่ต้องปิดก่อน |
>
> **⚠️ เครื่องหมาย ✅ ทุกตัวในไฟล์นี้เป็นของ t05 เท่านั้น** (กัน DAY-OF-SHAME class)
> สัญลักษณ์: ⬜ ยังไม่ทำ · 🔍 Claude ทำ/ตรวจแล้ว มีหลักฐาน · ✅ มะขามยืนยันแล้ว

---

## 📖 ตัวแปรทุกตัว — แบบไม่มีข้อยกเว้น (rule_of_tune ข้อ 12 + 15)

มะขามสั่ง 2026-08-30: "เอาให้เข้าใจตัวแปรทุกตัวแบบไม่มีข้อยกเว้น" — ตารางนี้คือคำตอบ
ทุกค่ามี (ก) ค่าที่จะใช้ (ข) ที่มา (ค) **พังยังไงถ้าตั้งผิด — จากเหตุการณ์จริง ไม่ใช่ทฤษฎี**
ที่มา: `[W]` = เอกสาร/วิจัยบนเน็ต (re-check 2026-08-30: Unsloth docs ยังยืนยันค่าเดิม) ·
`[t01]/[t02]/[t03]/[t04]` = พิสูจน์บนเครื่องจริงรอบนั้น

### A. Environment (ก่อน import torch)

| ตัวแปร | ค่า | ที่มา | พังยังไงถ้าผิด |
|---|---|---|---|
| `PYTORCH_ALLOC_CONF` | `expandable_segments:True` | [t01] | OOM จาก fragmentation ทั้งที่ VRAM รวมพอ — เคยขาดแค่ ~100MB จาก 95GB (2026-07-21); ต้องตั้ง**ก่อน** import torch ไม่งั้นไม่มีผลเงียบ ๆ |

### B. โหลดโมเดล

| ตัวแปร | ค่า | ที่มา | พังยังไงถ้าผิด |
|---|---|---|---|
| `MODEL` | `unsloth/Qwen3.6-35B-A3B` | ✅ มะขาม 2026-08-30 | ตัว bare repo เท่านั้น (bf16 เต็ม) — `-GGUF`/`-NVFP4`/`-MLX` รันได้แต่**ทูนไม่ได้** |
| สถาปัตยกรรม | MoE 35B รวม / 3B active, vision native (patch 16×16 + merge ×4) | [W] | visual tokens = H×W/1024 ต่อภาพ — สูตรนี้ใช้คำนวณ MAX_LENGTH ทุกครั้ง |
| `LOAD_IN_4BIT` | `False` (บังคับ) | [W] re-check 2026-08-30 | Unsloth เตือนเอง: Qwen3.5/3.6 MoE quantize แล้วคุณภาพตกผิดปกติ + BitsandBytes import 4-bit MoE พัง — **bf16 เท่านั้น ~74GB VRAM**; NVFP4 ที่ออกใหม่ ก.ค. 2026 เป็น inference-only (ต้อง Blackwell) ไม่เกี่ยวกับการเทรน |
| `use_gradient_checkpointing` | `"unsloth"` | [W] | ไม่ตั้ง = activation ระเบิดที่ seq ยาว |
| `max_seq_length` (ตอน `from_pretrained`) | = MAX_LENGTH | [t02] | **default 2048 — ตัดกลาง image token เงียบ ๆ** ต้องส่งตรงนี้ด้วย ไม่ใช่แค่ใน SFTConfig |
| คลาสโหลด | `FastVisionModel` | [t01][t03] | ใช้ได้จริงกับตระกูลนี้ (มี fallback `FastModel` เผื่อ Unsloth เปลี่ยน API) |

### C. ภาพ — โซนที่ฆ่า t01/t02/t04 มาแล้ว 3 รอบ (rule_of_tune ข้อ 15)

| ตัวแปร | ค่า | ที่มา | พังยังไงถ้าผิด |
|---|---|---|---|
| `MAX_PIXELS` | `7680 * 1024` | [t03b] วัดด้วย `measure_capacity.py` | ที่ 5,120: ภาพเทรนโดนย่อ 100% (973/973 ใบ) ตัวใหญ่สุดเสียรายละเอียด 67% · ที่ 7,680: เหลือโดนย่อ 30% ภาพหลัก 3309×2339 ได้ครบ · **ห้ามขึ้น 16,384 บนการ์ด 96GB** (peak คำนวณแล้ว 97.8GB = เกิน) |
| `MIN_PIXELS` | `256 * 1024` | [t01] | — |
| กลไกตั้งค่าจริง | `ip.size["longest_edge"] / ["shortest_edge"]` | [t01] | `ip.max_pixels` **ไม่มีแล้ว**บน transformers 5.x (AttributeError จริง) · `ip.size` เป็น SizeDict — `isinstance(dict)` เป็น False เสมอ ห้ามเช็คก่อน assign |
| collator | `UnslothVisionDataCollator(model, tokenizer, resize="max", max_seq_length=MAX_LENGTH)` | [t02] | **default `resize="min"` หา vision_config.image_size ไม่เจอ → ย่อ 512px เงียบ ๆ = ~266 token/ภาพ** — บั๊กที่ทำ A/B t01-vs-t02 พังทั้งรอบ (แพงที่สุดในประวัติโปรเจกต์ก่อน t04) |
| ยามหน้า batch แรก | assert `_tok_per_img > 1000` + เทียบ cap + เช็ค 3 ตัวอย่างยาวสุด `seq < MAX_LENGTH` | [t03] | มีในสคริปต์แล้ว (`train_t03.py` บรรทัด 252-298) — จับทั้งคลาส "ภาพโดนย่อเงียบ" และ "label โดนตัดกลาง JSON" ก่อนเผาเงิน **นี่คือ probe ตาม rule ข้อ 15 ของสาย Unsloth** (เทียบเท่า `probe_img_tokens.py` ของสาย LLaMA-Factory) |

### D. ความยาว sequence

| ตัวแปร | ค่า | ที่มา | พังยังไงถ้าผิด |
|---|---|---|---|
| `MAX_LENGTH` | **ต้องวัดใหม่** (เดิม t03 = 47,104) | [t03b] + ⚠️ t05 | เดิมวัดจาก gridline 4 ภาพ = 44,607 tokens · **t05 มี pass3 เพิ่ม: รูปมาร์ค (≤7,680) + บัญชี element + gridmaster JSON + prompt ยาว — ต้องรัน `measure_capacity.py` กับ dataset ใหม่ก่อนตั้งค่า ห้ามใช้ 47,104 ตามเดิมโดยไม่วัด** · ห้ามลด MAX_LENGTH เดี่ยว ๆ เพื่อแก้ OOM (จะตัด label กลาง JSON = บั๊กคลาส t01 §0.4) — ลดภาพ/ลด r แทน |

### E. LoRA

| ตัวแปร | ค่า | ที่มา | พังยังไงถ้าผิด |
|---|---|---|---|
| `r / alpha` | `16 / 32` (อัตรา 2 คงที่) | [t03] | r=32 OOM จริง (93.07/94.97GB เหลือ 470MB) — Unsloth แปะ LoRA ทั้ง 256 experts → r=32 = trainable 1.89B params กิน 11.3GB (LoRA+grad+optimizer) · r=16 คืน ~5.7GB · [W] LWR: จำนวน layer สำคัญกว่า rank |
| `lora_dropout` | `0` (บังคับ) | [W]+[t01] | MoE ParamWrapper **error จริง**ถ้า ≠0 |
| `bias` | `"none"` | [W] | — |
| `random_state` / `seed` | `3407` | [W] | ต้องเท่ากันทุก fold ถ้าจะ soup (LoRA-A init เดียวกัน) |
| `use_rslora` / `loftq_config` | `False` / `None` | [W] | — |
| `finetune_vision_layers` | `False` (freeze) | [t01] | **หัวใจ GGUF strategy**: vision encoder byte-identical กับ base → ใช้ mmproj official ตอน export ได้เลย เปลี่ยนเมื่อไหร่เส้นทาง GGUF พัง · unfreeze เป็นการทดลองรอบอนาคต (env `FINETUNE_VISION=1` มีไว้แล้ว) |
| `finetune_language/attention/mlp` | `True` ทั้งหมด | [W] LWR | attention-only underperforms — ต้องแปะครบรวม MoE experts |
| router/gate ของ MoE | frozen (Unsloth ทำให้เอง) | [W] | "not a good idea to fine-tune the router" |

### F. Trainer (SFTConfig)

| ตัวแปร | ค่า | ที่มา | พังยังไงถ้าผิด |
|---|---|---|---|
| `per_device_train_batch_size` | `1` | [t01]; [W] LWR: LoRA แพ้ batch ใหญ่ | — |
| `gradient_accumulation_steps` | `8` | [t01] | — |
| `learning_rate` | `1e-4` | [t01] converge จริง; [W] LWR: LoRA LR ~10× FullFT, ~ไม่ขึ้นกับ rank | — |
| `warmup_ratio` | `0.05` | [t01] | — |
| `num_train_epochs` | `3` | [t01] eval_loss ลงต่อเนื่อง 3 epoch | — |
| `optim` | `adamw_8bit` (**ไม่ใช่ paged**) | [t03] | `paged_adamw_8bit` พังจริง step 42: CUDA illegal memory access ใน bitsandbytes ตอนความดันหน่วยความจำสูง (unified memory paging) — non-paged ถ้าจะ OOM จะ OOM ที่ step 1 ให้รู้ใน 2 นาที |
| `weight_decay` / `lr_scheduler_type` | `0.01` / `cosine` | [t01] | — |
| `save_strategy/steps/total_limit` | `steps / 25 / 2` | [t03] | เดิม save ต่อ epoch → พังก่อนถึง epoch แรก = ไม่มี checkpoint เลย เสีย 40 นาทีฟรี |
| `eval_strategy` | `"no"` (บังคับปิด) | [t03] | **OOM จริง**: accelerate ห่อ forward ด้วย convert_to_fp32 → upcast logits seq 21k × vocab 152k × 4B ≈ 13GB ตาย · ตอนเทรนไม่เจอเพราะ Unsloth ใช้ fused/chunked loss ไม่ materialize logits · วัดผลจริงใช้ generate-eval แยกต่างหากหลังเทรน |
| `remove_unused_columns` | `False` | [W] | บังคับสำหรับ vision |
| `dataset_text_field` / `dataset_kwargs` | `""` / `{"skip_prepare_dataset": True}` | [W] | — |
| `completion_only_loss` | (default `True` — เขียนไว้ให้เห็น) | [W] docs "should always be True" | ค่า default ที่ไม่เขียนคือตัวแปรที่หายจาก parity table (rule ข้อ 12) |
| `bf16` | `True` | [W] | MoE ตระกูลนี้ = bf16 setup เท่านั้น (fp16 ไม่รองรับ) |

### G. Inference/eval (สำคัญไม่แพ้ตอนเทรน — t04 พิสูจน์แล้วว่า decoder ผิดตัวเดียวทำตัวเลขพังทั้งชุด)

| ตัวแปร | ค่า t05 | ที่มา | เหตุผล |
|---|---|---|---|
| `enable_thinking` | `False` เสมอ | [t01] | โมเดล reasoning-native เขียน CoT จนหมด token budget ก่อนถึง JSON — อาการคือ "เหมือนค้าง" |
| xgrammar | เปิด **ทุก subtask/ทุก pass** (builtin JSON) | ✅ มะขาม 2026-08-24/29 | พิสูจน์ 96.8% vs 57.9% valid · pass0/pass3 ยิ่งจำเป็น (JSON พัง = หน้าหลุด route / element กลายเป็น stub ทั้งบัญชี) |
| `no_repeat_ngram_size` | **เอาออก** (เดิม 8) | [t04] 🔴 เปลี่ยนจาก t03 | **ห้ามลำดับ 8 token ซ้ำ แต่คำตอบที่ถูกต้องของงานนี้ซ้ำโดยธรรมชาติ** (B2×10, RB1×24) — t04 พิสูจน์: ปลดแล้ว element โผล่ 0→10 ทันที · เหตุที่ t03 เคยใส่ (กัน loop ในสตริง) ใช้ timeout+regenerate แทน |
| `repetition_penalty` | **1.0** (เดิม 1.15) | [t04] 🔴 | เหตุผลเดียวกัน — ลงโทษการซ้ำที่ GT ต้องมี |
| `do_sample` | `False` | [t01] | deterministic — เทียบข้ามรอบได้ |
| `max_new_tokens` | วัดจาก GT ยาวสุดของ dataset ใหม่ (t03 ใช้ 3000, t04 ใช้ 6000) | ⚠️ วัดใหม่ | pass3 ตอบทั้งบัญชี element — สั้นไป = JSON ไม่ปิด |
| `PAGE_TIMEOUT_S` | 25 นาที/หน้า | [t03] | กัน string-loop (คลาสที่ grammar คุมไม่ได้) — เจอ JSON เสีย ให้ regenerate ไม่ใช่ไปเพิ่ม ngram-ban กลับ |
| tokenizer สำหรับ xgrammar | `tokenizer.tokenizer` (แกะจาก processor wrapper) | [t02] rule ข้อ 13 | ส่ง wrapper ตรง ๆ = AttributeError |

### H. งบ/เวลา (ประมาณจากรอบจริง)

- t03 จริง: 854 ตัวอย่าง × 3 epochs = 321 steps ≈ 5 ชม.เทรน บน RTX PRO 6000 WS 96GB $1.002/ชม., peak VRAM 87.5GB, train_loss 0.2249
- t05 คาด: dataset โต ~1.5-2.2× (แล้วแต่ scope pass0) → **เทรน ~8-12 ชม. ≈ $9-14** + eval ~2-3 ชม. + setup ~1 ชม. → **รวม ~$13-19 ต่อรอบ การ์ดใบเดียว**
- เครดิตคงเหลือ ณ 2026-08-30: **$16.66** — พอ 1 รอบพอดี ถ้า scope ไม่บาน (เผื่อใจ: เติมก่อนถ้าจะทำ k-fold)
- ⚠️ ตามบทเรียน t04: **เทรน fold เดียวก่อน พิสูจน์ว่าอ่านแบบได้จริง แล้วค่อยคิดเรื่อง k-fold** — k-fold เป็นตัวคูณความมั่นใจ ไม่ใช่ตัวตรวจว่าของพัง

---

## 📦 Dataset t05 — ของเดิม + 3 pass ใหม่ (มะขามสั่ง "เอา pass0 pass2.5 และ pass3 ใส่มา")

**หลักคิด:** สอนโมเดลด้วย input แบบเดียวกับที่ production ใช้จริง — pipeline จริงมี Python CV
(pass1.5/2.5) ช่วยมาร์ค element อยู่แล้ว โมเดลจึงควรถูก**เทรน**บนรูปมาร์ค+บัญชี ไม่ใช่รูปเปล่า

| ส่วน | บทบาทโมเดล | ตัวอย่าง (ประมาณ) | สถานะข้อมูล |
|---|---|---|---|
| 7 subtasks เดิม (gridline/section/plan_beam/plan_slab/plan_footing/notes/schedule) | อ่านรูปเปล่า → JSON | 1,020 train / 229 val — **พร้อมแล้ว** (ของ t04 ฟอร์แมต messages ใช้กับ Unsloth ได้เลย ตัว builder เดียวกัน) | ✅ มีครบ |
| **pass0 — จำแนกหน้า** | 1 หน้า → `{sheet_code, sheet_name, discipline, building, views[], ...}` (prompt: `t04_Purson/pass0/prompt.md`) | โครงสร้าง: derive จาก GT ได้ ~1,249 view · non-structural: ดู data-gap ① | ⚠️ data-gap ① |
| **pass2.5 — CV self-harvest** | **ไม่มีบทบาทโมเดล — ไม่ใช้ AI** (`cv_scan.py --pass25`) ผลของมันคือ **input ของ pass3** (`_marked25.png` + `_cv25.json` + `_hint25.txt`) | — | ⚠️ มีแค่ 10 หน้า ต้องรัน batch ทั้งคลัง (data-gap ②) |
| **pass3 — takeoff จากรูปมาร์ค** | รูปมาร์คเลข + บัญชี element + gridmaster → spec เต็มทุก element พร้อม `cv_mark` (prompt: `t04_Purson/pass3_takeoff/prompt.md`) | ~300 หน้าผังโครงสร้าง | ⚠️ data-gap ② + ③ |

### Data-gap ที่ต้องปิดก่อน build (เรียงตามลำดับทำ)

**① pass0 labels** — `pass0.json` GT **ไม่มีอยู่เลยสักบ้าน** (ตรวจแล้ว 2026-08-30) แต่:
- หน้าโครงสร้าง+notes+schedule: **derive ได้จาก GT rawjson ที่มีอยู่** (ชื่อไฟล์บอก หน้า/view/pattern
  → map pattern→subtask ด้วยตาราง lookup ใน pass0/prompt.md; `sheet_code/sheet_name/discipline`
  อยู่ใน rawjson แล้ว) — เขียน script derive ได้เลย ไม่ต้องดูรูป
- หน้า non-structural (arch/elec/sanitary/title/index — ส่วนใหญ่ของ 2,990 หน้าในคลัง): **ไม่มี GT**
  ทางเลือก: (ก) ให้ Claude label ผ่าน pass0 prompt แล้วมะขาม spot-check (งาน classify ง่าย เสี่ยงต่ำ)
  (ข) เทรนรอบนี้เฉพาะหน้าที่ derive ได้ก่อน แล้วเพิ่ม non-structural รอบหน้า — **รอมะขามเคาะ**
**② CV batch run** — รัน `python tools/cv_scan.py <โฟลเดอร์> --pass25` กับหน้าผังโครงสร้างทั้ง 40 หลัง
  (CPU ล้วน ทำบนเครื่องนี้ ไม่ต้องเช่าการ์ด) → ได้ `_marked25.png`/`_cv25.json` ครบคลัง
  ⚠️ เพดานที่รู้อยู่แล้ว: บ้านที่คลัง template จับไม่ติดเลย pass2.5 ช่วยไม่ได้ (บ้านพวกนั้นจะไม่มีตัวอย่าง pass3)
**③ จับคู่ `cv_mark` ↔ GT element** — GT ไม่มี bbox, CV ไม่รู้ mark จริง → ต้องออกแบบตัวจับคู่
  (แนวทาง: ตำแหน่ง CV box → interpolate เข้า grid → เทียบ `grid_refs` ของ GT element; ชนิดต้อง
  ตรงกัน; เหลือกำกวมให้คน eyeball) — **นี่คืองาน design ชิ้นเดียวที่ยังไม่มีคำตอบสำเร็จรูป ห้ามมั่ว:
  จับคู่ผิด = สอนโมเดลอ่านผิดตำแหน่งทั้ง dataset (บั๊กคลาสเดียวกับ slugify ของ Constistant)**

---

## ✈️ Phase 0 — Pre-flight (rule_of_tune ข้อ 4 — ทุกข้อต้องทำจริงก่อนกดเช่า)

| # | รายการ | สถานะ |
|---|---|---|
| 1 | ปิด data-gap ①②③ + build dataset ใหม่ (`build_dataset_t05.py` ต่อยอดจาก `build_dataset_t03.py`) | ⬜ |
| 2 | รัน `measure_capacity.py` กับ dataset ใหม่ → ตั้ง `MAX_LENGTH` จากตัวเลขจริง (ห้าม copy 47,104) | ⬜ |
| 3 | **probe token รูป (rule ข้อ 15)**: batch-แรก assert ใน train_t05.py ต้องเห็น `~7680 tokens/ภาพ` จริง + seq ตัวยาวสุด < MAX_LENGTH — บน CPU ก่อนเช่าได้ (`collator([train_ds[0]])` ไม่ต้องมี GPU) | ⬜ |
| 4 | วัด GT ยาวสุด → ตั้ง `max_new_tokens` eval | ⬜ |
| 5 | เช็คเครดิต vast.ai พอ (~$19 + margin) — ตอนนี้ $16.66 **ไม่พอถ้ามี buffer** พิจารณาเติม | ⬜ |
| 6 | `TEST_STEPS=5` บนเครื่องเช่า ผ่านก่อนรันเต็ม (VRAM peak, ไม่ OOM, loss ลดจริง) | ⬜ |
| 7 | eval harness: ใช้ `infer_house_t03.py` เดิม + **แก้ decoder ตาม §G** (ถอด ngram-ban, rep_penalty=1.0) + เพิ่มโหมด pass0/pass3 | ⬜ |
| 8 | ยืนยัน fold เดียวก่อน — k-fold เป็นการตัดสินใจหลังเห็นผล ไม่ใช่ค่าเริ่มต้น (บทเรียน t04) | ⬜ |

## 🎯 เกณฑ์ตัดสินรอบนี้ (ตั้งไว้ก่อนเทรน กันเลื่อนเป้าทีหลัง)

- ตัวเลขอ้างอิงที่ต้องแข่ง: **t01 = 28.2% element recall** (สูงสุดของโปรเจกต์) / t03 = 10.1%
- เป้าที่มีความหมายจริง: **pass3 บนรูปมาร์ค CV ต้อง recall สูงกว่า pass2 รูปเปล่าอย่างมีนัย** —
  นี่คือสมมติฐานหลักของรอบ (CV ช่วยจริงไหม) ถ้าไม่ต่าง = โครงสร้าง 2-stage ไม่คุ้ม
- ด่านสุดท้ายเหมือนเดิม: บ้านนอกคลัง (`t04_Purson/test_house_new/บ้านไทยพอเพียง3` — 65 หน้า
  เตรียมไว้แล้ว ยืนยันไม่อยู่ใน 40 หลัง) เดินทั้งสายพาน

## ❓ คำตอบจากมะขาม (2026-08-30)

1. **pass0 scope:** ✅ เคาะแล้ว — **Claude label หน้า non-structural เพิ่ม แล้วมะขาม spot-check**
   (หน้าโครงสร้าง derive จาก GT rawjson ตามแผน; หน้า non-structural Claude อ่านรูป+ป้อนผ่าน
   pass0 prompt ทีละหน้า — ทำเป็น batch ตรวจได้ ไม่รีบทำรวดเดียว)
2. **เครดิต:** ⬜ ยังไม่ตอบ — $16.66 เฉียดพอ 1 รอบ ($13-19) เตือนอีกทีตอนใกล้กดเช่า
3. **ชื่อรอบ:** ✅ **"Asclepius"** — ผู้ใช้งูหาสมุนไพร (ตำนานกรีก: หมอที่เรียนรู้การรักษาจากงู
   — เข้ากับรอบนี้พอดี: โมเดลเรียนรู้การอ่านแบบโดยมีงู (CV) ช่วยชี้จุด)
