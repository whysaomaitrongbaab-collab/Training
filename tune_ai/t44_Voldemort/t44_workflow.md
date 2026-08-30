# t44 "Voldemort" — InternVL3-78B แก้มือ, 4 pass

> **สโคป: InternVL3-78B เท่านั้น** — แขน Qwen3.6-35B-A3B อยู่ที่ [`../t05_Courser/`](../t05_Courser/)
> แยกกันเด็ดขาด กันข้อมูลสองโมเดลปนกัน (มะขามสั่งแยก 2026-08-31)

## ไฟล์ในโฟลเดอร์นี้
| ไฟล์ | คืออะไร |
|---|---|
| [`train_t44_internvl3_fold0.yaml`](train_t44_internvl3_fold0.yaml) | config เทรน fold0 — มี `crop_to_patches: true` (บรรทัดที่ฆ่า t04) |
| [`train_t44_internvl3_fold1.yaml`](train_t44_internvl3_fold1.yaml) | config เทรน fold1 — เหมือน fold0 ทุกอย่าง ต่างแค่ dataset/output_dir |
| `train_fold{0,1}_lf.json` / `val_fold{0,1}_lf.json` | dataset 4 pass รูปแบบ sharegpt ต่อ fold (สร้างโดย `../t05_Courser/build_4pass.py`) |
| `dataset_info.json` | ลงทะเบียน `t44_train_fold{0,1}` / `t44_val_fold{0,1}` ให้ LLaMA-Factory |
| [`internvl_arm_dossier.md`](internvl_arm_dossier.md) | dossier เต็ม: กลไก root cause t04, ทางเลือก, งบ, ประตู go/no-go |

## dataset (2026-08-31 ค่ำ) — k-fold 2, เนื้อเดียวกับแขน Courser เป๊ะทุก fold
**"k fold 2, train/val 4/1"** (มะขามสั่ง) = **k=5 folds จริง (8 บ้าน/fold จาก 40 บ้าน) รันแค่
fold0+fold1** (ประหยัดงบเหมือน t04) — แต่ละ fold train=32 บ้าน(4/5) val=8 บ้าน(1/5) = 4:1 พอดี
ไม่ใช่แบ่งครึ่ง (k=2 จริงจะเห็นข้อมูลแค่ 50%/โมเดล แย่กว่ามาก)

**house→fold ยึดตาม t04 เดิม** (ไม่ใช้ VAL_HOUSES คงที่ 2 บ้านเดิมอีกต่อไป) — เจอว่า fold0's val
ตรงกับ 2 บ้าน val เดิมของเราเป๊ะ แต่มี 1 บ้านชน (`บ้าน_ใหญ่_1ชั้น_01`) ที่เคยอยู่ train ฝั่งเราแต่เป็น
val ของ t04 fold0 — แก้โดยยึด house-to-split ของ t04 เป็นความจริงเดียวทุก pass (ไม่งั้นบ้านเดียวกัน
จะอยู่ train ของ pass0 พร้อมกับ val ของ pass1 ในโมเดลเดียวกัน = รั่วข้ามชนิดข้อมูล) — ผลพลอยได้:
เทียบตัวเลขกับ t04 เดิมได้ตรงบ้าน val เป๊ะ

| fold | train | val | หมายเหตุ |
|---|---|---|---|
| fold0 | 1,048 | 257 | val ตรงกับ t04 fold0 เป๊ะ — มี pass0/2.4/3 ใน val ด้วย (17/31/4 แถว) |
| fold1 | 1,101 | 204 | 8 บ้าน val ไม่ทับกับสโคป pass0/2.4/3 เลย — val มีแค่ pass1 (204) ล้วน pass0/2.4/3 ไปอยู่ train หมด |

**จงใจให้ข้อมูลตรงกันทั้งสองแขนทุก fold** — t04 เปลี่ยนทั้งโมเดลและ precision พร้อมกันจนแยกไม่ออก
ว่าอะไรทำให้ผลต่าง (confound) รอบนี้ตรึงข้อมูลเท่ากัน ผลต่างที่เห็นจึงมาจากโมเดลจริง ๆ

## เช่าการ์ด (2026-08-31 มะขามสั่ง) — 4 การ์ดพร้อมกัน ไม่ใช่ทีละใบ
เช่า 4 เครื่องคู่ขนาน: Voldemort fold0, Voldemort fold1, Courser fold0, Courser fold1 — ยกเลิกกฎเดิม
"เทรน fold เดียวก่อนพิสูจน์แล้วค่อยรัน fold ถัดไป" (ยังต้องผ่านประตู go/no-go ด้านล่างก่อนเสมอ
แค่ทำครั้งเดียวใช้ได้ทั้ง 2 fold ของ Voldemort) หลังทั้ง 2 fold เทรนจบและ push HF แล้ว รวมเป็น
adapter เดียวด้วย PEFT model soup (`../merge_adapters_soup.py --arm voldemort`,
`add_weighted_adapter` linear 0.5/0.5) — ไม่ deploy แยก 2 adapter

## เก็บผลใน Hugging Face (token ใหม่ "t44", FINEGRAINED, export HF_TOKEN ก่อนรัน)
- `dacarokann/Voldemort_a` = adapter fold0
- `dacarokann/Voldemort_b` = adapter fold1
- (คู่กัน) `dacarokann/Courser_a`/`Courser_b` = adapter fold0/fold1 ของแขน Courser
- หลัง soup: `dacarokann/Voldemort_soup` / `dacarokann/Courser_soup` (ตัวใช้งานจริง)
- yaml ทั้งสอง fold ตั้ง `push_to_hub: true` ไว้แล้ว — push อัตโนมัติตอนเทรนจบ ไม่ต้องทำมือ
- ก่อน destroy instance ทุกครั้ง **ต้องรัน `../verify_hf_push.py --repo ... --local-dir ...`
  ให้เห็น `✅ PASS` ก่อนเสมอ** (Day-of-Shame guard ใหม่ — push_to_hub อัปเงียบๆ ล้มเหลวได้ถ้า
  เน็ตหลุด/token หมดอายุ) **ไม่ต้องปิดคอมทำงานของมะขามหลังจบ** (ตัดขั้น shutdown ออกจากลำดับ
  ปิดงานรอบนี้ ต่างจาก t03/t04) — `att1235` มอบให้ Claude แล้ว 2026-08-31 ตัดสิน/destroy เองได้
  ไม่ต้องเด้งถาม (Day-of-Shame verify ยังบังคับเหมือนเดิม, ยังต้อง log ทุกก้าว)

## ⛔ ก่อนเทรนเต็ม ต้องผ่านประตู go/no-go ~$2 ก่อนเสมอ
โหลด base 4-bit + tiling เต็ม **ไม่มี adapter** แล้วให้อ่านแบบจริง 3-5 หน้า
- อ่าน mark ออก (ตอบ B2/C1/F1 ตรง) = ตา InternViT รอด 4-bit → เดินต่อ
- เพ้อ/ตอบเป็นบ้านคนละหลัง = **หยุด** เสียแค่ ~$2 ไม่ใช่ทั้งคืน

เหตุผล: เอกสารทางการ InternVL เตือนตรง ๆ ว่า BNB 4-bit บน InternViT-6B *"produce nonsensical
outputs and fail to understand images"* และ LLaMA-Factory quantize ทั้งก้อนไม่เว้น ViT
(verify จาก `quantization.py` บน main 2026-08-31: ไม่มี `modules_to_not_convert`)

## ⚠️ เพดานความละเอียด — ต้องรู้ก่อนเทียบผลกับ Courser
tiling เต็ม 12+1 tile = ภาพถูกย่อเหลือราว **12 × 448² ≈ 2.4 ล้านพิกเซล** ก่อนอ่าน
ขณะที่ Courser (Qwen) อ่านได้ถึง **7.86 ล้านพิกเซล**

→ **InternVL เห็นรายละเอียดน้อยกว่าราว 3.3 เท่าโดยสถาปัตยกรรม** ไม่ใช่เพราะตั้งค่าผิด
งานเราคือมาร์ค/ตัวเลขเล็กบนแบบ และงานวิจัย (2026-08-31) ชี้ว่าความละเอียดยิ่งสูงยิ่งดีสำหรับ
ข้อความเล็ก **โดยยังไม่อิ่มตัวแม้ที่ 6MP** (InternLM-XComposer2-4KHD: DocVQA 79→89%,
InfographicVQA 50→69% เมื่อไต่จาก 1MP ไป 6.2MP)

**ถ้า Voldemort แพ้ Courser อย่าเพิ่งสรุปว่าโมเดลแย่กว่า** — อาจเป็นเพดานความละเอียดล้วน ๆ

## สถานะ (2026-08-31 ค่ำ)
- [x] dataset 4 pass k-fold พร้อม (ตรวจผ่าน `../t05_Courser/smoke_4pass.py` ทั้ง fold0/fold1:
  รูปไม่ซ้ำ 884 ใบ เปิดได้ครบ 0 หาย, บ้าน val ไม่ปน train ทั้ง 2 fold)
- [x] yaml เขียนแล้ว 2 ไฟล์ (fold0/fold1) มี `crop_to_patches: true` + `media_dir`
  (verify path resolve ถูกครบทุกไฟล์ ทั้งสอง fold — 1,416 image ref/fold, missing 0)
- [ ] **ประตู go/no-go $2** (ยังไม่ทำ — บังคับก่อนเทรนเต็ม ทำครั้งเดียวใช้ได้ทั้ง 2 fold)
- [ ] dry-run `max_steps: 5` บนการ์ดจริง (ทั้ง fold0 และ fold1)
- [ ] probe ยืนยัน token/ภาพ ต้องเห็น ~2,300-3,328 ไม่ใช่ 256 (`../t04_Purson/data_before_tune/probe_img_tokens.py`)
- [ ] เครดิตยังไม่พอเช่า (ดู dossier §6) — ตอนนี้ต้องเผื่อ **4 การ์ดพร้อมกัน** ไม่ใช่ใบเดียว
- [ ] export HF_TOKEN (token "t44") บนเครื่องเช่าทุกใบก่อนรัน — ยังไม่เคยลอง push_to_hub จริง
- [ ] merge_adapters_soup.py ยังไม่เคยรันจริง — รอ Voldemort_a/_b เทรนจบทั้งคู่ก่อน
- [x] `onstart.sh` — เขียนแล้ว (`t44_Voldemort/onstart.sh`, LLaMA-Factory flavor)
- [ ] `../verify_hf_push.py` (Day-of-Shame guard สำหรับ push_to_hub) — เขียนแล้ว ยังไม่เคยรันจริง
- [x] `att1235` — มะขามมอบให้ Claude สำหรับรอบนี้แล้ว 2026-08-31 (ตัดสิน/destroy เองได้ ไม่ต้อง
  เด้งถาม — Day-of-Shame verify-after-push ยังบังคับก่อน destroy เสมอ, ยังต้อง log ทุกก้าว)

## ค่าที่ยังไม่ได้ verify (อย่าเชื่อโดยไม่วัด)
- `lora_rank: 16` — ยกมาจาก t03 ที่จูนเพื่อ MoE, dense+QLoRA headroom ต่างกัน
- `num_train_epochs: 2.0` (แก้ 3→2, 2026-08-31 ค่ำ ตาม research LoRA/QLoRA: 2 vs 3 epoch accuracy
  ต่างมักแค่ 1-3% แต่ 3 epoch กิน GPU-ชม.+50% + risk overfit สูงขึ้น) — ไม่ใช่ค่าที่วัด converge
  จริงของรอบนี้ ยังต้องดู loss curve เอง
- eval ปิดอยู่ — 2026-08-31 พบว่ามีทางเลี่ยง OOM ที่ยังไม่ได้ลอง (`fp16_full_eval` +
  `eval_accumulation_steps`) ถ้าอยากได้ eval_loss curve จริง ให้ทดสอบตอน dry-run ไม่ใช่ตอนรันเต็ม
- infer script ยังไม่เคยเจอ GPU จริง — และตอน infer ต้องส่ง `crop_to_patches=True, max_patches=12`
  + `image_max_pixels` เดียวกับตอนเทรน ห้ามใช้ AutoProcessor default ดิบ (มัน tile เต็มเสมอ ไม่สน config)
