# 🚨 คู่มือฉุกเฉิน Purson — ใช้ตอนคุยกับ Claude ไม่ได้

สร้าง 2026-08-30 ตอนเทรน k-fold 4 folds คู่ขนาน
**ใช้เมื่อ:** ติด usage limit / Claude ล่ม / ดึกเกินไม่อยากรอ — ทำเองได้ทุกข้อ

---

## 📍 เครื่องทั้ง 4 ใบ

| fold | instance id | SSH | ราคา/ชม. |
|---|---|---|---|
| fold0 | 49160184 | `ssh -p 26367 root@170.64.243.132` | $1.105 |
| fold1 | 49171206 | `ssh -p 25212 root@84.249.79.112` | $1.096 |
| fold2 | 49172547 | `ssh -p 28080 root@170.64.254.80` | $0.916 |
| fold3 | **49175439** | `ssh -p 40516 root@87.236.196.76` | $1.134 |

**รวม ~$4.25/ชม. = ~$102/วัน** ← สำคัญ อย่าลืมปิด

> ⚠️ ใบ fold3 เดิม (49172551, Virginia US) **หลุด offline หลังเช่า 26 นาที** — destroy ทิ้งแล้ว
> เช่าใบ Czechia แทน (reliability 0.997, net 8496Mbps) ถ้าใบไหนขึ้น `offline` ใน `vastai show instances`
> ให้ทำแบบเดียวกัน: `echo "y" | vastai destroy instance <ID>` แล้วเช่าใหม่ (อย่าฝืนรอ host ที่มีอาการ)

ทุกเครื่อง: งานอยู่ที่ `/workspace/tune/` · tmux session ชื่อเดียวกับ fold

---

## 1️⃣ เช็คว่าเทรนถึงไหนแล้ว

```bash
# เข้าเครื่องแล้วรัน (แทน foldN ด้วยชื่อจริง เช่น fold0)
tail -c 500 /workspace/tune/fold0.log | tr '\r' '\n' | tail -5
```
จะเห็นแบบ `45/306 [1:23:45<7:12:30, 175s/it]` = ทำไป 45 จาก 306 steps

**เข้าไปดูสด ๆ:**
```bash
tmux attach -t fold0      # ออกโดยไม่ปิดงาน: กด Ctrl+b แล้วปล่อย แล้วกด d
```

**เช็ค GPU:**
```bash
nvidia-smi
```
ปกติต้องเห็น utilization ~100% และ memory ~85-87GB / 97.9GB

---

## 2️⃣ ถ้าเทรนพัง (OOM / error)

**ดู error จริง:**
```bash
grep -iE "error|traceback|out of memory|killed" /workspace/tune/fold0.log | tail -20
```

**checkpoint ล่าสุดที่เซฟไว้ (เซฟทุก 25 steps):**
```bash
ls -la /workspace/tune/outputs_t04/fold0/
```
ถ้ามี `checkpoint-XXX` = ยังกู้ได้ ไม่ต้องเริ่มใหม่หมด

**เทรนต่อจาก checkpoint:**
```bash
cd /workspace/tune
tmux kill-session -t fold0 2>/dev/null
tmux new-session -d -s fold0 'llamafactory-cli train train_t04_fold0.yaml \
  resume_from_checkpoint=outputs_t04/fold0/checkpoint-XXX 2>&1 | tee -a fold0.log'
```
(แทน XXX ด้วยเลข checkpoint ล่าสุด)

**ถ้า OOM ซ้ำ ๆ** — ลดภาระลง:
```bash
tmux new-session -d -s fold0 'llamafactory-cli train train_t04_fold0.yaml \
  cutoff_len=16384 2>&1 | tee -a fold0.log'
```

---

## 3️⃣ เทรนเสร็จแล้ว — ต้องทำอะไร (⚠️ สำคัญที่สุด)

เสร็จจะเห็นในไฟล์ log: `Training completed.` และมีโฟลเดอร์ `outputs_t04/foldN/` พร้อม
`adapter_model.safetensors`

### ⛔ ห้าม destroy ก่อนทำ 2 ข้อนี้ (บทเรียน Mark of Shame — เคยเสีย adapter มาแล้ว)

**A. อัปขึ้น HuggingFace (ทำก่อนเสมอ):**
```bash
cd /workspace/tune
hf upload Sicilian44/Purson-fold1-weights outputs_t04/fold0    # fold0 → repo ชื่อ fold1
```
| เครื่อง | คำสั่ง |
|---|---|
| fold0 | `hf upload Sicilian44/Purson-fold1-weights outputs_t04/fold0` |
| fold1 | `hf upload Sicilian44/Purson-fold2-weights outputs_t04/fold1` |
| fold2 | `hf upload Sicilian44/Purson-fold3-weights outputs_t04/fold2` |
| fold3 | `hf upload Sicilian44/Purson-fold4-weights outputs_t04/fold3` |

(ชื่อ repo นับจาก 1 ตามที่ตกลงไว้ ส่วนโฟลเดอร์ในเครื่องนับจาก 0)

**B. ดึงกลับมาเก็บที่เครื่องตัวเอง (รันบนเครื่อง Windows ไม่ใช่บนเครื่องเช่า):**
```bash
scp -P 26367 -r root@170.64.243.132:/workspace/tune/outputs_t04/fold0 ./
```

**เช็คว่าไฟล์ครบจริงก่อนใจชื้น:**
```bash
ls -la fold0/          # ต้องมี adapter_model.safetensors ขนาดหลายร้อย MB ไม่ใช่ 0 byte
```

---

## 4️⃣ 💰 คืนการ์ด (ทำเมื่อมั่นใจว่าไฟล์ปลอดภัยแล้วเท่านั้น)

```bash
# รันบนเครื่อง Windows — ต้อง echo "y" | เพราะ CLI ถาม y/N แบบ interactive (ไม่งั้น abort เงียบ)
echo "y" | vastai destroy instance 49160184
echo "y" | vastai destroy instance 49171206
echo "y" | vastai destroy instance 49172547
echo "y" | vastai destroy instance 49175439

# ยืนยันว่าคืนครบจริง — ต้องได้ 0 instances
vastai show instances
```

⚠️ **destroy ≠ stop** — stop ยังเสียค่า storage ต่อ, destroy คือลบถาวรกู้ไม่ได้
⚠️ ถ้าอยากหยุดเผาเงินด่วนแต่ยังไม่พร้อมลบ ให้ destroy ไปเลยหลังดึงไฟล์ครบ — อย่า stop ทิ้งไว้

---

## 5️⃣ เช็คเงิน

```bash
vastai show user --raw | python -c "import json,sys; print('$', json.load(sys.stdin)['credit'])"
```

**ถ้าเครดิตจะหมด** — เติมที่ https://cloud.vast.ai/billing/
เครดิตหมด = instance ถูกหยุดอัตโนมัติ **แต่ checkpoint ที่เซฟไว้แล้วยังอยู่** (ถ้ายังไม่ถูก destroy)

---

## 6️⃣ ค่าที่ใช้อยู่ (ไว้อ้างอิงตอนต้องตัดสินใจ)

- โมเดล: `OpenGVLab/InternVL3-78B-hf` · QLoRA 4-bit (bnb NF4)
- LoRA: rank 16, alpha 32, target all · seed 3407 (ทุก fold เหมือนกัน — จำเป็นสำหรับ soup)
- 3 epochs · 306 steps/fold · batch 1 × grad accum 8
- VRAM ที่วัดได้จริง: ~87GB / 97.9GB
- แต่ละ fold: train 32 หลัง (~816 ตัวอย่าง) / val 8 หลัง (~204) — **ไม่ปนกันเลย** ตรวจแล้ว

---

## 7️⃣ ขั้นถัดไปหลังได้ adapter ครบ 4 ตัว (ไม่ต้องรีบ ทำทีหลังได้)

1. วัดผลแต่ละ fold บน val สะอาดของตัวเอง (`infer_house_t04.py`)
2. merge เป็น soup: PEFT `add_weighted_adapter(["f0","f1","f2","f3"], [0.25]*4, combination_type="linear")`
   → อัป `Sicilian44/Purson-weights` (ติดป้าย unbenchmarked ตามที่ตกลง — ไม่วัด soup)
3. ทดสอบบ้าน 2 ชั้นใหม่ที่ไม่เคยอยู่ในคลัง 40 หลัง (ด่านตัดสินจริงด่านเดียว)

❌ **GGUF ยกเลิกแล้ว** (มะขามเคาะ 2026-08-30: "เอาแต่ adapter พอ") — ไม่ต้องทำ ไม่มี repo Purson-gguf

รายละเอียดเต็ม: `t04_workflow.md`
