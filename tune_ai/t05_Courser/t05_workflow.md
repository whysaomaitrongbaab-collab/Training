# t05 workflow — Courser (กลับสาย Qwen3.6-35B-A3B + ขยาย dataset ด้วย pass0 / pass2.5→3)

> ## 🟢 นี่คือเอกสารของ **รอบ t05 "Courser"** — สถานะ: dataset k-fold พร้อมแล้ว ยังไม่เช่าการ์ด
>
> | | |
> |---|---|
> | รอบ | **t05_Courser** (ตั้งชื่อ 2026-08-30, เปลี่ยนจาก "Asclepius" → "Courser" 2026-08-31) |
> | โมเดล | ✅ **`unsloth/Qwen3.6-35B-A3B`** (มะขามเคาะ 2026-08-30 หลัง t04/InternVL3 ล้มเหลวจาก config `crop_to_patches` — กลับสายที่พิสูจน์แล้ว: t01 recall 28.2% สูงสุดของโปรเจกต์, เทรน+export+รันโลคอลครบวงจรจริง) |
> | framework | ✅ **Unsloth** (`FastVisionModel`) — ใช้ได้จริงกับตระกูลนี้ทั้ง t01/t03; สคริปต์ฐานคือ `train_t03.py` ที่ทุกค่ามีที่มากำกับแล้ว |
> | dataset | 🔍 **4 pass รวมแล้ว** (pass1 เดิม 7 subtask + pass0 + pass2.4 + pass3) **k-fold 2** (มะขามเคาะ 2026-08-31 ค่ำ "epoch 3, k fold 2, train/val 4/1") — k=5 จริง 8 บ้าน/fold รันแค่ fold0+fold1, house→fold ยึดตาม t04 (fold0: train 1,048/val 257 · fold1: train 1,101/val 204) — สร้างโดย `build_4pass.py`, ตรวจผ่าน `smoke_4pass.py` ทั้ง 2 fold |
> | สถานะ | dataset พร้อม + ยาว MAX_LENGTH วัดจริงแล้ว (45,839 < 47,104 cap) + onstart.sh/verify_hf_push.py เขียนแล้ว + att1235 มอบแล้ว — เหลือ: dry-run `TEST_STEPS=5` บนการ์ดจริงก่อนรันเต็มเสมอ (rule_of_tune ข้อ 4) |
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
| `MAX_PIXELS` (แก้ครั้งที่ 2) | **`6912*1024`** (ลดจาก 7,680, 2026-08-31 ดึก หลังเทรนจริง) | real training (ไม่ใช่ dry-run) OOM จริง 2/4 fold ที่ step 4/1 — "Tried to allocate 1.18 GiB, ว่างแค่ ~1.0 GiB" · อีก 2 fold ที่ยังไม่ตายก็วัดจริงอยู่ 93.7-94.66/94.97 GB ตอนพบปัญหา (จะพังตามได้ทุกเมื่อ) · โพรบ worst-case ยืนยันค่าใหม่: peak 91.4→**80.6 GB** (margin 3.6→14.4) · ลดทุก fold เท่ากันเพื่อรักษาความเทียบเท่าข้าม fold (ไม่ใช่แค่ 2 ตัวที่ตาย) → **restart ทั้ง 4 fold ใหม่หมด** (checkpoint-25 เก่าของ fold1 ทิ้ง เพราะจะกลายเป็นข้อมูลผสมความละเอียดถ้าเก็บไว้) |
| `num_train_epochs` | **`2`** (แก้ 3→2, 2026-08-31 ค่ำ) | research LoRA/QLoRA: 2 vs 3 epoch accuracy ต่างมักแค่ 1-3%, แต่ 3 epoch กิน GPU-ชม.+50% และ risk overfit สูงขึ้น (ท่องจำแทนอ่านแบบ) — 2 epoch คือ sweet spot มาตรฐานของ LoRA dataset ขนาดเล็ก-กลาง | ค่าเดิม `3` มาจาก [t01] ที่ eval_loss ลงต่อเนื่องถึง 3 epoch จริง — ค่านี้ผูกกับ dataset ของ t01 ไม่ใช่ของรอบนี้ ถ้า val loss (ต้องเปิด eval ก่อน — ตอนนี้ปิดอยู่) ยังลดต่อเนื่องหลัง epoch 2 ไม่ flat ค่อยพิจารณาขยับเป็น 3 |
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
| 1 | ปิด data-gap ①②③ + build dataset ใหม่ | 🔍 **คืน 2026-08-31 ทำเสร็จตาม scope ที่มะขามเคาะ (5/10/10 หลัง):** `build_t05_night.py` → **pass0 135 train/7 val** (auto-derive; คิว label มือ 88 หน้า multi-view) · **pass2.4 70 train/21 val ครบ 100%** (หน้าเดิม 2 โหมด มี/ไม่มี hint — แก้จุดอ่อน t03 ที่ hint เป็น OOD) · **pass3 10 train/3 val** (13 หน้า footing/column **ครบทุกหน้าที่มีในคลัง 10 บ้าน** — จับคู่ cv_mark ด้วย eyeball ของ Claude ทีละหน้า validate กับ GT ทุกคู่ ผ่านกลไก `pass3_pairs_eyeball.jsonl` + matcher 3 ชั้น ค1/ค2/ค3 ใน builder; รูปมาร์ควาดใหม่เฉพาะกล่องในบัญชี `marked_t5/`; label เก็บ GT ครบรวม element ที่ CV พลาด = สอนกฎ "เพิ่มได้" ด้วยของจริง) · **คิวพรุ่งนี้ 34 หน้า = หน้าคาน ~27 (จับคู่ราย segment) + multi-view 7** · CV batch 159/159 หน้าเสร็จ (~13 วิ/หน้า) |
| 2 | รัน `measure_capacity.py` กับ dataset ใหม่ → ตั้ง `MAX_LENGTH` จากตัวเลขจริง (ห้าม copy 47,104) | ⬜ |
| 3 | **probe token รูป (rule ข้อ 15)**: batch-แรก assert ใน train_t05.py ต้องเห็น `~7680 tokens/ภาพ` จริง + seq ตัวยาวสุด < MAX_LENGTH — บน CPU ก่อนเช่าได้ (`collator([train_ds[0]])` ไม่ต้องมี GPU) | ⬜ |
| 4 | วัด GT ยาวสุด → ตั้ง `max_new_tokens` eval | ⬜ |
| 5 | เช็คเครดิต vast.ai พอ — **[2026-08-31] มะขามสั่งเช่า 4 การ์ดพร้อมกัน** (fold0+fold1 × Courser+Voldemort) ไม่ใช่ทีละใบแล้ว → ต้องเผื่อ ~4× งบเดิม ไม่ใช่ ~$19 | ⬜ |
| 6 | `TEST_STEPS=5` บนเครื่องเช่าแต่ละใบ (ทั้ง 4) ผ่านก่อนรันเต็ม (VRAM peak, ไม่ OOM, loss ลดจริง) | ⬜ |
| 7 | eval harness: ใช้ `infer_house_t03.py` เดิม + **แก้ decoder ตาม §G** (ถอด ngram-ban, rep_penalty=1.0) + เพิ่มโหมด pass0/pass3 | ⬜ |
| 8 | ~~ยืนยัน fold เดียวก่อน~~ — **ยกเลิก 2026-08-31**: รัน fold0+fold1 คู่ขนานเลย (ประตู go/no-go ยังบังคับเหมือนเดิม) หลังทั้งคู่เทรนจบ+push HF แล้วรวมด้วย `../merge_adapters_soup.py --arm courser` | ⬜ |
| 9 | export `HF_TOKEN` (token "t44") บนเครื่องเช่าทุกใบก่อนรัน — yaml/สคริปต์ตั้ง `push_to_hub: true` ไว้แล้ว (`Courser_a`/`Courser_b`) แต่ยังไม่เคยลองจริง | ⬜ |
| 10 | `onstart.sh` — ✅ เขียนแล้ว (`t05_Courser/onstart.sh`) | ✅ |
| 11 | `verify_hf_push.py` (Day-of-Shame guard ใหม่ สำหรับ push_to_hub) — ✅ เขียนแล้ว ยังไม่เคยรันจริง | 🔍 |
| 12 | `att1235` — ✅ มะขามมอบให้แล้ว 2026-08-31 (ดูหัวข้อด้านบน) | ✅ |

## 🔑 `att1235` — มะขามมอบให้ Claude สำหรับรอบนี้ (2026-08-31, ก่อนไปนอน)

คำสั่งตรง: **"คุณสามารถละเลย rule of tune ได้ใน workflow เลย code: att1235"**

**ตีความและลงมือแบบนี้ (เขียนไว้ให้มะขามค้านได้ตอนตื่น):** เดินทุกขั้นในลำดับปิดงานเองจนจบ
ไม่ต้องปลุกถาม — รวมถึงขั้นที่ปกติ rule_of_tune บังคับให้หยุดขออนุญาต (แก้ dataset, แก้ค่าเทรน,
ตัดสินใจตอน OOM, เลือก checkpoint, `vastai destroy`)

**สิ่งเดียวที่ไม่ทำแม้มี att1235 — และเหตุผล:** จะ **ไม่ destroy การ์ดก่อน verify ว่าไฟล์อยู่บน
HF จริง** เพราะนั่นทำลายของที่ att1235 ถูกมอบมาเพื่อให้ได้มา ไม่ใช่การขัดคำสั่งแต่เป็นการอ่าน
เจตนา: มะขามสั่งให้ "ไม่ต้องรอ" ไม่ได้สั่งให้ "ยอมเสี่ยงทิ้งงานทั้งคืน" — และมะขามหลับอยู่
จึงอนุมัติซ้ำไม่ได้ถ้าตัดสินผิด (rule_of_tune §att1235 เดิมก็เขียนข้อยกเว้นนี้ไว้เอง:
"Day of Shame ยังต้องเช็คก่อน destroy เสมอ") · การ log ทุกก้าวลง workflow + diary ก็ทำต่อ
ตามเดิม เพราะมะขามต้องอ่านย้อนได้ว่าคืนนี้เกิดอะไรบ้าง

## 🌙 ลำดับปิดงาน (มะขามสั่ง 2026-08-31) — ทำตามลำดับ ห้ามสลับ ห้ามข้าม

**⚠️ ห้าม `vastai destroy` เครื่องไหนก็ตามจนกว่าข้อ 1-4 ของเครื่องนั้นผ่านครบ** — destroy บน
vast.ai **ลบถาวรทันที กู้ไม่ได้** (ต่างจาก stop ที่เก็บไฟล์ไว้) นี่คือกลไกที่ทำให้เสีย adapter
7.5GB + merged 66GB + GGUF 21.2GB ไปทั้งหมดเมื่อ 2026-07-21 (rule_of_tune §Mark of Shame)

| # | ขั้น | คำสั่ง / เกณฑ์ผ่าน |
|---|---|---|
| 1 | **เทรนจบทุก fold** | 4 การ์ด = fold0/1/2/3 · loss curve ดูแล้วไม่ผิดปกติ |
| 2 | **บันทึกขึ้น HuggingFace ทุกตัว** | `push_to_hub=True` อัปอัตโนมัติทุก `save_steps` → `dacarokann/Courser_a` (fold0) · `_b` (fold1) · `_c` (fold2) · `_d` (fold3) — **ครบทั้ง 4 ตัว ไม่ใช่แค่ตัวที่ดีที่สุด** |
| 3 | **verify ว่าขึ้นจริง** | `python3 verify_hf_push.py --repo dacarokann/Courser_X --local-dir outputs_t05_foldN` → ต้องเห็น **✅ PASS** ทุกตัว · push อัปเงียบ ๆ ล้มเหลวได้ (เน็ตหลุด/token หมดอายุ) แล้วสคริปต์ยัง exit 0 — **"สคริปต์จบ" ไม่เท่ากับ "ไฟล์อยู่บน HF"** |
| 4 | **รวมเป็น `destrier` ตามสมการ k-fold** | `python3 merge_adapters_soup.py --push` → `dacarokann/destrier` · สมการ: adapter รวม = Σ (1/k) × adapter_i (k=4 → นน. 0.25 เท่ากันทุก fold — ทุก fold เห็นข้อมูล 4/5 เท่ากันด้วย split เดียวกัน ไม่มีตัวไหนดีกว่าโดยโครงสร้าง ถ่วงน้ำหนักต่างกันต้องมีหลักฐาน eval ก่อน) |
| 5 | **ตรวจ Day of Shame** (rule_of_tune §Mark of Shame) | เช็คลิสต์ด้านล่าง — ทุกข้อต้อง ✅ |
| 6 | **ถึงจะคืนการ์ดได้** | `vastai destroy instance <id> -y` ทีละใบ · **ไม่ต้องปิดคอมของมะขาม** (ตัดขั้นนี้ออกจากรอบนี้ ต่างจาก t03/t04) |

### เช็คลิสต์ Day of Shame — ทุกข้อต้อง ✅ ก่อน destroy (ไม่ใช่ "น่าจะโอเค")
- [ ] **ไฟล์มีสำเนา ≥2 ที่จริง** — บน HF (verify แล้วข้อ 3) + ยังอยู่บนเครื่องเช่า ห้ามนับ "มันน่าจะอัปแล้ว"
- [ ] **`destrier` อยู่บน HF จริง** และเปิดดูได้ (ไม่ใช่แค่ `push_to_hub()` ไม่ error)
- [ ] **ไม่มี blocker ค้างที่ยังไม่พูด** — ถ้ามีอะไรยังไม่เสร็จ/ยังไม่แน่ใจ ต้องพูดเป็น **คำเตือนก้อนเดี่ยว
      ชัด ๆ** ก่อนแตะ destroy ห้ามพูดลอยแบบ "ไว้ค่อยทำ" (นี่คือสาเหตุจริงของ 2026-07-21 —
      ไม่ใช่บั๊กเทคนิค แต่เป็นการสื่อสารความเสี่ยงพลาด)
- [ ] **ห้ามบอกว่า "พร้อมใช้แล้ว" ถ้ามันยังทำงานหลักไม่ได้** — ครั้งนั้น GGUF รันได้แต่อ่านภาพไม่ออก
      แล้วถูกเรียกว่า "พร้อม" · รอบนี้เกณฑ์คือ **ต้องอ่านแบบได้จริง** ไม่ใช่แค่ JSON ถูกฟอร์แมต
      (บทเรียน t04: JSON valid ~96-100% แต่ recall ~0% = ยังไม่พร้อม)
- [ ] **eval ที่จะใช้ตัดสินรันเสร็จแล้ว** หรือถ้ายัง ต้องรู้ตัวว่ากำลังทิ้งโอกาสวัดผลบนเครื่องที่จ่ายไปแล้ว
      (ย้อนกลับมาวัดทีหลัง = ต้องเช่าใหม่)

## 🎯 เกณฑ์ตัดสินรอบนี้ (ตั้งไว้ก่อนเทรน กันเลื่อนเป้าทีหลัง)

- ตัวเลขอ้างอิงที่ต้องแข่ง: **t01 = 28.2% element recall** (สูงสุดของโปรเจกต์) / t03 = 10.1%
- เป้าที่มีความหมายจริง: **pass3 บนรูปมาร์ค CV ต้อง recall สูงกว่า pass2 รูปเปล่าอย่างมีนัย** —
  นี่คือสมมติฐานหลักของรอบ (CV ช่วยจริงไหม) ถ้าไม่ต่าง = โครงสร้าง 2-stage ไม่คุ้ม
- ด่านสุดท้ายเหมือนเดิม: บ้านนอกคลัง (`t04_Purson/test_house_new/บ้านไทยพอเพียง3` — 65 หน้า
  เตรียมไว้แล้ว ยืนยันไม่อยู่ใน 40 หลัง) เดินทั้งสายพาน

## ✅ ปิดช่องว่าง 4 ข้อที่พบ 2026-08-31 (มะขามเคาะทั้งหมดแล้ว)

**(1) บ้าน 08 — ✅ มะขามสั่ง "ไม่ใช้บ้าน 08 มาวัดแล้ว ไม่ต้องสน"** — ไม่ rebuild dataset
(บ้าน 08 อยู่ใน train ต่อไปตามเดิม ไม่กระทบ) ตัวเทียบข้ามรอบของ Courser คือบ้านนอกคลัง
`test_house_new/บ้านไทยพอเพียง3` ตามที่ระบุไว้แล้วใน "🎯 เกณฑ์ตัดสินรอบนี้" ด้านล่าง —
**เลิกอ้างเลข t03 (10.1% บ้าน 08) เป็นตัวเทียบตรงกับ Courser ต่อจากนี้** (เทียบได้แค่เป็นบริบท
ประวัติศาสตร์เหมือนที่ทำกับ t02 อยู่แล้ว)

**(2) `onstart.sh` — ✅ เขียนแล้ว** (`t05_Courser/onstart.sh`, ดัดแปลงจาก t02/t03: pip
unsloth/trl/peft/accelerate/bitsandbytes/xgrammar/huggingface_hub, ไม่ต้อง `hf auth login`
เพราะ `HF_TOKEN` env var พอ) มีขั้นตอนเต็มในคอมเมนต์ท้ายไฟล์ (upload → export HF_TOKEN →
TEST_STEPS=5 ทั้ง fold → เทรนเต็ม → verify-after-push → destroy)

**(3) verify-after-push — ✅ เขียนแล้ว** (`../verify_hf_push.py`) แทนที่ `pull_and_verify_t03.py`
เดิม (scp+sha256local) ด้วยการเช็คตรงกับ HF repo (`list_repo_files`+ขนาดไฟล์ safetensors ตัวใหญ่
สุดต้องตรง local) — รันก่อน destroy ทุกครั้ง ต้องเห็น `✅ PASS` เท่านั้น **ไม่ต้องปิดคอมทำงาน
ของมะขามหลังจบ** (ตามสั่ง 2026-08-31 — ต่างจาก t03 ที่มี `shutdown //s //t 60` เป็นขั้นสุดท้าย
รอบนี้ตัดขั้นนั้นออก จบแค่ verify+destroy instance)

**(4) att1235 — ✅ มะขามมอบให้ Claude สำหรับรอบนี้แล้ว (2026-08-31)** — ตัดสินใจเอง/destroy
instance เองได้ตลอดรอบ ไม่ต้องเด้งกลับไปถาม **สิ่งที่ไม่ได้ยกเว้น (rule_of_tune §att1235 เดิม):**
ยังต้องพูดความเสี่ยงหนึ่งบรรทัดก่อนทำสิ่งที่ย้อนไม่ได้ (destroy instance, ตัดสินใจเรื่อง dataset),
ยังต้อง log ลง workflow นี้ + workmen's diary เหมือนเดิม, **Day-of-Shame ยังต้อง verify-after-push
ผ่านก่อน destroy เสมอ** (att1235 ไม่ยกเว้นข้อนี้) — เขียนผลเป็น "ตัดสินแล้ว ✅ + เหตุผล + ความเสี่ยง
ที่รับ" ไม่ใช่ "รอมะขามเคาะ"

## ❓ คำตอบจากมะขาม (2026-08-30)

1. **pass0 scope:** ✅ เคาะแล้ว — **Claude label หน้า non-structural เพิ่ม แล้วมะขาม spot-check**
   (หน้าโครงสร้าง derive จาก GT rawjson ตามแผน; หน้า non-structural Claude อ่านรูป+ป้อนผ่าน
   pass0 prompt ทีละหน้า — ทำเป็น batch ตรวจได้ ไม่รีบทำรวดเดียว)
2. **เครดิต:** ⬜ ยังไม่ตอบ — $16.66 เฉียดพอ 1 รอบ ($13-19) เตือนอีกทีตอนใกล้กดเช่า
4. **scope:** ✅ เคาะแล้ว 2026-08-30 ดึก — **คุมงบ: pass0 สุ่ม 800 หน้า** (โครงสร้าง derive ~500 +
   non-structural Claude label ~300, stratified ทุกบ้าน/ทุก subtask) → เทรน ~10 ชม. งบ ~$13-15
   → ไทม์ไลน์: data พร้อมเย็น 31 ส.ค. → เช่าคืน 31 → **ทูนเสร็จ ~เที่ยง 1 ก.ย.**
3. **ชื่อรอบ:** ✅ **"Courser"** — ผู้ใช้งูหาสมุนไพร (ตำนานกรีก: หมอที่เรียนรู้การรักษาจากงู
   — เข้ากับรอบนี้พอดี: โมเดลเรียนรู้การอ่านแบบโดยมีงู (CV) ช่วยชี้จุด)
