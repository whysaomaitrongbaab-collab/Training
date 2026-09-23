# บทที่ 7: Vision-Language Model (VLM) เกิดมาได้อย่างไร — ต่อ "ตา" เข้ากับ "สมองภาษา"

> **เป้าหมายของบทนี้:**
> - อธิบายได้ว่าภาพหนึ่งใบกลายเป็น "token" ที่ LLM กินได้อย่างไร และทำไมจำนวน token ต่อภาพถึงเป็นตัวแปรที่พลิกผลการทูนทั้งรอบ
> - แยกได้ว่า VLM สองแนวทางใหญ่ (ต่อ token เข้าลำดับ vs cross-attention) ต่างกันตรงไหน และ Qwen-VL / InternVL / Llama 3.2 Vision อยู่ค่ายไหน
> - คำนวณ token budget ของภาพแบบก่อสร้าง 3309×2339 px ที่ `max_pixels` ต่าง ๆ ได้เอง และอธิบายบั๊ก "512 px / 266 token" ด้วยตัวเลข
>
> **ต้องอ่านบทไหนมาก่อน:** บทที่ 4 (Transformer / attention), บทที่ 5 (LLM และ tokenizer), บทที่ 6 (ViT และการมองภาพเป็น patch)
>
> **เวลาอ่านโดยประมาณ:** 60-75 นาที (รวมลองรันโค้ด)

---

## 7.0 คำถามเปิด (ผูกกับงานจริงของเรา)

ตอนรอบ t02 เราตั้งใจจะเทียบ Qwen3.6-35B-A3B (t01) กับ Qwen3-VL-30B-A3B ให้ยุติธรรมที่สุด ทุกค่าคุมให้เท่ากันหมด เหลือตัวแปรเดียวคือ "ตระกูลโมเดล" แล้วผลออกมาแย่กว่าที่ควรจะเป็นมาก

สิ่งที่พบทีหลังคือ collator ของ Unsloth มีค่า default `resize="min"` ที่ไปหา `vision_config.image_size` ของโมเดล พอหาไม่เจอก็ย่อภาพเหลือ 512 px เงียบ ๆ ภาพแบบก่อสร้างหน้าละ 3309×2339 px เลยเหลือ visual token ราว 266 token ต่อภาพตอนเทรน แต่ตอนใช้จริงเราป้อนภาพเต็มที่ราว 3,796 token ต่อภาพ ต่างกัน 14 เท่า โมเดลไม่เคย "เห็น" ภาพละเอียดขนาดนั้นมาก่อนเลยตอนเรียน

คำถามที่บทนี้ต้องตอบให้ได้คือ

1. "visual token" คืออะไรกันแน่ ทำไมภาพใบเดียวถึงกลายเป็นตัวเลข 266 หรือ 3,796 ได้ และเลขนั้นคำนวณจากอะไร
2. ทำไมการย่อภาพถึงทำให้โมเดล "อ่านเหล็ก Ø12 เป็น DB23" ในเมื่อคนเราย่อรูปก็ยังพออ่านออก
3. ตอนเรา freeze vision tower แล้วทูนเฉพาะ LLM เรากำลังแตะส่วนไหนของเครื่องจักรนี้ และส่วนไหนที่ไม่แตะเลย

ถ้าเทียบกับงานวิศวกร: LLM คือวิศวกรที่อ่านได้แต่ "รายการคำนวณ" ที่พิมพ์เป็นตัวหนังสือ VLM คือการติดตั้ง "ตา" ให้เขา แล้วต่อสายประสาทจากตาเข้าสมองส่วนภาษาให้ได้ บทนี้คือประวัติของสายประสาทเส้นนั้น

---

## 7.1 ปัญหาต้นทาง: LLM รับได้แต่ token ข้อความ

จากบทที่ 5 เรารู้แล้วว่า LLM decoder รับ input เป็นลำดับของ embedding ขนาด $d$ มิติ (เช่น $d = 4096$) หนึ่งตัวต่อหนึ่ง token ข้อความ "คาน B1" อาจถูก tokenizer หั่นเป็น 3 token แล้วแต่ละ token ถูก lookup เป็นเวกเตอร์ 4096 มิติผ่านตาราง embedding

ภาพไม่มีตาราง lookup แบบนั้น ภาพคือกริดของตัวเลข (pixel) ขนาด $H \times W \times 3$ ภาพแบบก่อสร้างของเราคือ $2339 \times 3309 \times 3 \approx 23$ ล้านตัวเลข จะยัดเข้า LLM ตรง ๆ ไม่ได้ ต้องมีขั้นตอน "แปลงภาพให้เป็นลำดับเวกเตอร์ขนาด $d$ มิติ ที่อยู่ในภาษาเดียวกับ token ข้อความ"

นี่คือคำนิยามการทำงานของ VLM ทุกตัวในบทนี้: **หา function ที่รับภาพ แล้วคืนลำดับเวกเตอร์ที่ LLM อ่านรู้เรื่อง**

$$
\text{image} \xrightarrow{\ \text{vision encoder}\ } \{v_1, v_2, \dots, v_N\} \xrightarrow{\ \text{projector}\ } \{h_1, h_2, \dots, h_N\} \in \mathbb{R}^{N \times d}
$$

- $v_i$ = feature ของ patch ที่ $i$ จาก vision encoder (ขนาดของมัน เช่น 1024 หรือ 1152 มิติ ไม่จำเป็นต้องเท่ากับ $d$ ของ LLM)
- $h_i$ = เวกเตอร์ที่ถูกแปลงให้มีขนาด $d$ เท่า token ข้อความ
- $N$ = จำนวน visual token ตัวเลขนี้แหละที่เป็น 266 หรือ 3,796 ในบั๊กของเรา

จากบทที่ 6 เรารู้แล้วว่า ViT หั่นภาพเป็น patch สี่เหลี่ยมขนาดคงที่ ถ้า patch 14 px บนภาพ 336 px จะได้ $336/14 = 24$ patch ต่อด้าน รวม $24 \times 24 = 576$ patch นั่นคือ $N = 576$ นี่คือเลขกลม ๆ ที่โมเดลรุ่น LLaVA ใช้ [4]

🎨 **ภาพที่จะวาดใน HTML:** ภาพซ้ายเป็นแบบแปลนคาน (ใช้ภาพจริงจากโปรเจกต์ย่อขนาด) มีกริดซ้อนทับให้เห็น patch ขวาเป็นแถวของกล่องสี่เหลี่ยมเรียงยาว (token sequence) ที่ผสมกล่องข้อความ "ถอดรายการคานจากแบบนี้" กับกล่องภาพ $h_1 \dots h_N$ มีสไลเดอร์ "patch size" (14/16/28/32) เมื่อขยับ กริดบนภาพจะละเอียดขึ้น/หยาบลง และจำนวนกล่องภาพในแถว token จะเปลี่ยนตามพร้อมโชว์ตัวเลข $N$ ให้ผู้เรียนเห็นว่า patch เล็กลง 2 เท่า = token เพิ่ม 4 เท่า

---

## 7.2 CLIP (2021): สอนให้ "ตา" กับ "ภาษา" ใช้ไม้บรรทัดเดียวกัน

ก่อนจะต่อตาเข้ากับ LLM ต้องมีตาที่ "รู้ภาษา" ก่อน CLIP ของ Radford และคณะ (OpenAI, 2021) [1] คือจุดเริ่มต้นสำคัญ แนวคิดคือเอาคู่ (ภาพ, คำบรรยาย) จากอินเทอร์เน็ต 400 ล้านคู่ มาสอน encoder สองตัว (image encoder และ text encoder) ให้ส่งภาพและข้อความที่ "คู่กัน" ไปอยู่ใกล้กันในปริภูมิเวกเตอร์เดียวกัน และคู่ที่ไม่ใช่ให้อยู่ห่างกัน

วิธีนี้เรียกว่า contrastive learning ไม่ต้องมีคนมานั่งติดป้าย "นี่คือแมว" แค่ใช้ caption ที่มีอยู่แล้วบนเว็บเป็นครู

### 7.2.1 contrastive loss ด้วยตัวอย่าง 3 คู่

สมมติมี batch 3 คู่:

| # | ภาพ | ข้อความ |
|---|---|---|
| 1 | ผังคาน | "แบบแปลนคานชั้น 2" |
| 2 | รูปตัดเสา | "รูปตัดเสา C1 เหล็ก 8-DB16" |
| 3 | ตารางเหล็ก | "ตารางรายการเหล็กเสริม" |

encoder แต่ละฝั่งให้เวกเตอร์ที่ normalize แล้ว (ความยาว 1) เราคำนวณ cosine similarity ของทุกคู่ (ภาพ $i$, ข้อความ $j$) ได้เมทริกซ์ $3 \times 3$ คูณด้วย temperature scale แล้วสมมติได้

$$
S = \begin{bmatrix} 2.0 & 0.5 & 0.1 \\ 0.3 & 1.8 & 0.2 \\ 0.0 & 0.4 & 1.5 \end{bmatrix}
$$

แถวคือภาพ คอลัมน์คือข้อความ เส้นทแยงคือคู่ที่ถูกต้อง loss ของ CLIP คือ cross-entropy ที่บังคับให้เส้นทแยงชนะในทุกแถว (ภาพ→ข้อความ) และทุกคอลัมน์ (ข้อความ→ภาพ)

สำหรับแถวที่ 1 (ภาพผังคาน) softmax ให้ความน่าจะเป็นของข้อความที่ถูก:

$$
p_{1} = \frac{e^{2.0}}{e^{2.0}+e^{0.5}+e^{0.1}} = \frac{7.389}{7.389+1.649+1.105} = 0.729
$$

loss แถวนี้ = $-\ln 0.729 = 0.317$ ทำแบบเดียวกันแถว 2 ได้ $0.354$ แถว 3 ได้ $0.442$ เฉลี่ยฝั่งภาพ→ข้อความ = $0.371$ แล้วทำซ้ำในแนวคอลัมน์ เอาสองฝั่งมาเฉลี่ยกันอีกที

สังเกตว่าแถว 3 loss สูงสุด เพราะ "ตารางเหล็ก" ยังถูกจับคู่กับ "รูปตัดเสา C1 เหล็ก 8-DB16" ค่อนข้างมาก (0.4) ซึ่งสมเหตุสมผล ทั้งคู่มีคำว่าเหล็ก gradient จะดัน encoder ให้แยกสองอย่างนี้ออกจากกันมากขึ้น

เทียบกับงานวิศวกร: เหมือนสอนคนใหม่ให้จับคู่ "แผ่นแบบ" กับ "ชื่อแผ่นในสารบัญ" โดยไม่ต้องอธิบายอะไรเลย ให้ดูคู่ที่ถูกเป็นแสน ๆ คู่ แล้วลงโทษทุกครั้งที่จับคู่ผิด สุดท้ายเขาจะรู้เองว่า "เส้นขนานหนาสองเส้นที่มีตัวหนังสือ B กำกับ" คือคาน

```python
import numpy as np
S = np.array([[2.0, 0.5, 0.1],
              [0.3, 1.8, 0.2],
              [0.0, 0.4, 1.5]])          # similarity ภาพ(แถว) x ข้อความ(คอลัมน์)
def ce_rows(M):                            # cross-entropy ที่เส้นทแยงต้องชนะในแต่ละแถว
    P = np.exp(M) / np.exp(M).sum(axis=1, keepdims=True)
    return -np.log(np.diag(P))
l_i2t = ce_rows(S)        # ภาพ -> ข้อความ
l_t2i = ce_rows(S.T)      # ข้อความ -> ภาพ
print("loss ต่อแถว (i2t):", l_i2t.round(3))
print("loss ต่อคอลัมน์ (t2i):", l_t2i.round(3))
print("CLIP loss =", ((l_i2t.mean() + l_t2i.mean()) / 2).round(3))
```

ผลที่ควรได้: `[0.317 0.354 0.442]` ในแถว และ CLIP loss ราว 0.37

🎨 **ภาพที่จะวาดใน HTML:** เมทริกซ์ 3×3 เป็น heatmap แต่ละช่องคลิกลากปรับค่าได้ ด้านขวาแสดง softmax ของแถวที่เลือกเป็นแท่งกราฟ 3 แท่ง และตัวเลข loss ของแถวนั้น มีปุ่ม "ทำ 1 gradient step" ที่ดันค่าเส้นทแยงขึ้นและนอกทแยงลงเล็กน้อยแล้วอัปเดต loss ให้เห็นว่ามันลดลง เพิ่มสไลเดอร์ temperature ($\tau$) ให้เห็นว่า scale ใหญ่ทำให้ softmax "แหลม" ขึ้น

### 7.2.2 ทำไม CLIP ถึงสำคัญกับ VLM

ผลพลอยได้ที่สำคัญกว่าตัว CLIP เอง คือ image encoder ของมัน (ViT) ออกมาเป็น encoder ที่ feature "มีความหมายเชิงภาษา" อยู่แล้ว VLM รุ่นแรก ๆ เกือบทั้งหมด (Flamingo, BLIP-2, LLaVA, Qwen-VL รุ่นแรก) หยิบ ViT จาก CLIP หรือญาติของมัน (เช่น SigLIP ที่ PaliGemma ใช้ [12]) มาเป็น "ตา" โดยไม่ต้องสอนตาใหม่ตั้งแต่ศูนย์

---

## 7.3 สามวิธีต่อสาย: Flamingo, BLIP-2, LLaVA

พอมีตาที่ดีแล้ว คำถามคือจะต่อสายเข้าสมองภาษาอย่างไร ระหว่างปี 2022-2023 มีสามคำตอบที่ต่างกันชัดเจน Lilian Weng สรุปแนวทางทั้งหมดไว้เป็นหมวดหมู่ที่อ่านง่าย [21]

### 7.3.1 Flamingo (2022): เจาะ cross-attention เข้าไปกลาง LLM

Flamingo ของ DeepMind [2] แช่แข็งทั้ง vision encoder และ LLM แล้ว "แทรก" ชั้น cross-attention ใหม่เข้าไประหว่างชั้นเดิมของ LLM ชั้นที่แทรกนี้ให้ token ข้อความมองไปที่ visual feature ได้ (query มาจากข้อความ, key/value มาจากภาพ) โดยที่ visual feature ไม่ได้ถูกยัดเข้าไปในลำดับ token เลย

ข้อดี: ลำดับ token ข้อความไม่ยาวขึ้น ภาพจะใหญ่แค่ไหนก็ไม่ไปกิน context ของ LLM
ข้อเสีย: ต้องเพิ่มพารามิเตอร์ใหม่จำนวนมาก (cross-attention ทุก ๆ สองสามชั้น) และสถาปัตยกรรม LLM ถูกแก้ ทำให้เครื่องมือ inference มาตรฐาน (เช่น llama.cpp) รองรับยากกว่า

### 7.3.2 BLIP-2 (2023): Q-Former "บีบ" ภาพให้เหลือ token จำนวนคงที่

BLIP-2 ของ Li และคณะ [3] เสนอ Querying Transformer (Q-Former) ตัวเล็กที่มี "query token" ที่เรียนรู้ได้จำนวนคงที่ (เช่น 32 ตัว) query เหล่านี้ไปทำ cross-attention กับ feature ของ ViT แล้วสรุปภาพทั้งใบเป็นเวกเตอร์ 32 ตัว จากนั้นค่อยฉายเข้า LLM

ข้อดี: ประหยัด token มาก (32 token ต่อภาพ)
ข้อเสีย: ภาพแบบก่อสร้างมีข้อมูลเป็นพันจุด (ตัวเลขเหล็ก ระยะกริด) การบีบเหลือ 32 เวกเตอร์คือการโยนรายละเอียดทิ้งโดยโครงสร้าง ต่อให้ทูนอย่างไรก็กู้คืนไม่ได้ นี่คือเหตุผลที่ Q-Former หายไปจากโมเดลที่เน้น OCR/document

### 7.3.3 LLaVA (2023): projector เชิงเส้นตัวเดียว แล้วต่อ token เข้าลำดับตรง ๆ

LLaVA ของ Liu และคณะ [4] เลือกทางที่ง่ายที่สุด: เอา feature ทุก patch จาก ViT ผ่าน projector (ตอนแรกเป็นเมทริกซ์ $W$ ตัวเดียว รุ่นต่อมาเป็น MLP 2 ชั้น) แล้วเรียงต่อเข้าไปในลำดับ token ข้างหน้าข้อความ LLM มองภาพเหมือนเป็น "คำ" 576 คำที่มาก่อนคำถาม

$$
h_i = W \, v_i \quad (W \in \mathbb{R}^{d \times d_v})
$$

ถ้า $d_v = 1024$ (ViT) และ $d = 4096$ (LLM) projector มีพารามิเตอร์แค่ $4096 \times 1024 \approx 4.2$ ล้าน เทียบกับ LLM 7 พันล้าน คือเล็กจิ๋ว

**visual instruction tuning สองขั้น** ของ LLaVA คือสูตรที่แทบทุกโมเดลรุ่นหลังลอกไป:

| ขั้น | อะไรถูกเทรน | ข้อมูล | จุดประสงค์ |
|---|---|---|---|
| 1. pretrain projector | เฉพาะ $W$ (ViT และ LLM แช่แข็ง) | คู่ภาพ-caption | สอน "ล่าม" ให้แปลภาษาตาเป็นภาษาสมอง |
| 2. fine-tune | $W$ + LLM (ViT มักยังแช่แข็ง) | คำสั่ง-คำตอบที่ GPT-4 ช่วยสร้าง | สอนให้ตอบคำถามเกี่ยวกับภาพ |

ข้อดี: เรียบง่าย ใช้เครื่องมือ LLM ปกติได้หมด LoRA ทำได้เหมือน LLM ธรรมดา
ข้อเสีย: ภาพกิน context เท่ากับจำนวน patch ภาพละเอียด = token เยอะ = แพง นี่คือต้นตอของเรื่อง `max_pixels` ทั้งหมดในหัวข้อถัดไป

🎨 **ภาพที่จะวาดใน HTML:** แผนภาพสามคอลัมน์เปรียบเทียบ Flamingo / BLIP-2 / LLaVA แต่ละคอลัมน์มี ViT (กล่องเขียว), ตัวเชื่อม (กล่องเหลือง: cross-attn / Q-Former / projector), LLM (กล่องน้ำเงิน) เมื่อผู้เรียนเลื่อนสไลเดอร์ "ความละเอียดภาพ" จำนวนกล่อง token ที่ไหลเข้า LLM ในคอลัมน์ LLaVA จะเพิ่มขึ้นตาม ในคอลัมน์ BLIP-2 คงที่ที่ 32 และในคอลัมน์ Flamingo ลำดับ token ไม่เปลี่ยนแต่ลูกศร cross-attention หนาขึ้น ให้เห็นข้อแลกเปลี่ยนสามแบบพร้อมกัน

---

## 7.4 สถาปัตยกรรม 3 ส่วน และ "freeze vision tower" หมายถึงอะไรทางกายภาพ

VLM ค่าย LLaVA/Qwen ทุกตัวประกอบด้วยสามก้อน

1. **Vision encoder (ViT)** พารามิเตอร์หลายร้อยล้านถึงหลายพันล้าน รับ pixel คืน feature ต่อ patch
2. **Projector / merger** ชั้นเล็ก ๆ ที่ (ก) รวม patch ข้างเคียงให้เหลือน้อยลง และ (ข) เปลี่ยนมิติให้เท่า $d$ ของ LLM
3. **LLM decoder** ก้อนใหญ่สุด รับลำดับ [visual token ... text token ...] แล้ว generate ข้อความ

ตอนเราตั้ง `finetune_vision_layers=False` ในสคริปต์ t02 และ t05 หมายความว่า gradient จะ **ไม่ไหลเข้า** ก้อนที่ 1 และ 2 เลย น้ำหนักของ ViT และ merger หลังเทรนเสร็จเป็น byte เดียวกันกับตอนโหลดมา สิ่งที่เปลี่ยนคือ LoRA adapter ที่แปะบน linear layer ของก้อนที่ 3 เท่านั้น (บทที่ 8 จะลงลึก)

พูดเป็นภาษาวิศวกร: เราไม่ได้เปลี่ยนเลนส์กล้อง ไม่ได้เปลี่ยนเซ็นเซอร์ เราสอนแค่ "คนอ่านภาพ" ให้ตีความ feature ชุดเดิมเป็น JSON ให้ดีขึ้น

ผลตามมาสองอย่างที่โปรเจกต์เราใช้ประโยชน์จริง:

- **ข้อดี:** vision encoder ที่ไม่ถูกแตะ ทำให้ตอน export เป็น GGUF ใช้ไฟล์ mmproj (ส่วน vision) ของทางการได้เลย ไม่ต้องแปลงเอง นี่คือเหตุผลที่ t05 เขียนไว้ว่ามันคือ "หัวใจ GGUF strategy" และการเทรน ViT บน dataset เล็ก (t02 มี 315 ตัวอย่าง) เสี่ยงทำ visual feature พัง
- **ข้อเสีย:** ถ้าปัญหาอยู่ที่ "ตามองไม่เห็น" (เช่น เส้นบางเกินไปสำหรับ feature ที่ ViT เรียนมาจากภาพถ่าย) การทูนเฉพาะ LLM แก้ไม่ได้ ต้องแก้ด้วยความละเอียดภาพ (max_pixels) หรือยอมปลด freeze ในรอบทดลอง

🎨 **ภาพที่จะวาดใน HTML:** แผนภาพสามก้อนเรียงจากซ้ายไปขวา (ViT → merger → LLM) มีสวิตช์ "freeze vision" เมื่อเปิด ก้อน ViT และ merger จะเป็นสีเทาและมีไอคอนแม่กุญแจ ลูกศร gradient (สีแดง ไหลจากขวาไปซ้าย) จะหยุดที่ขอบ LLM เมื่อปิด ลูกศรจะไหลทะลุถึง ViT และตัวเลข "พารามิเตอร์ที่เทรน" ด้านล่างเพิ่มขึ้น มีคำอธิบายข้าง ๆ ว่าไฟล์ mmproj ยังใช้ของเดิมได้หรือไม่

---

## 7.5 สาย Qwen-VL: จากภาพขนาดคงที่สู่ dynamic resolution

### 7.5.1 Qwen-VL (2023)

Qwen-VL รุ่นแรก [5] ใช้ ViT + cross-attention resampler แบบ Q-Former ย่อภาพให้เหลือ token จำนวนคงที่ (ภาพถูก resize เป็นขนาดตายตัวก่อน) จุดเด่นคือถูกสอนให้ทำ text reading และ localization (ให้ bbox กลับ) ตั้งแต่ pretrain

### 7.5.2 Qwen2-VL (2024): naive dynamic resolution และ M-RoPE

Qwen2-VL ของ Wang และคณะ [6] เปลี่ยนเกม ด้วยสองอย่าง

**(ก) Naive Dynamic Resolution** ไม่ resize ภาพเป็นขนาดตายตัวอีกต่อไป ภาพขนาดไหนก็หั่นเป็น patch 14 px ตามจริง แล้ว merger รวม patch ข้างเคียง $2 \times 2$ เป็น 1 token ดังนั้น

$$
\text{1 visual token} = (14 \times 2) \times (14 \times 2) = 28 \times 28 = 784\ \text{px}^2
$$

จำนวน token ต่อภาพ $= \dfrac{H' \times W'}{784}$ เมื่อ $H', W'$ คือขนาดหลังปัดให้หาร 28 ลงตัว

ค่านี้ตรงกับ `preprocessor_config.json` ของ Qwen2-VL-7B จริง (`patch_size: 14, merge_size: 2, min_pixels: 3136, max_pixels: 12845056`) [22] สังเกตว่า `min_pixels = 3136 = 56 \times 56` คือ 4 token พอดี

**(ข) `min_pixels` / `max_pixels`** คือคันเร่งและเบรกของ token budget ถ้าภาพมีพิกเซลเกิน `max_pixels` processor จะย่อลง (รักษาสัดส่วน) จนพิกเซลไม่เกินเพดาน ถ้าน้อยกว่า `min_pixels` จะขยายขึ้น ตัวแปรสองตัวนี้คือสิ่งที่สคริปต์ t02/t05 ของเราตั้งผ่าน `ip.size["longest_edge"]` / `["shortest_edge"]`

**(ค) M-RoPE** จากบทที่ 4 เรารู้ว่า RoPE ใส่ตำแหน่งให้ token ด้วยการหมุนเวกเตอร์ตามดัชนีตำแหน่ง 1 มิติ แต่ภาพมี 2 มิติ (สูง, กว้าง) และวิดีโอมี 3 (เวลา, สูง, กว้าง) Qwen2-VL แบ่งมิติของ embedding ออกเป็นสามส่วน แล้วให้แต่ละส่วนหมุนตามดัชนี (time, height, width) แยกกัน token ข้อความใช้ดัชนีเดียวกันทั้งสามส่วน (จึงลดรูปเป็น RoPE ปกติ) ผลคือโมเดลรู้ว่า visual token สองตัวอยู่ "แถวเดียวกันแต่คนละคอลัมน์" ซึ่งสำคัญมากกับการอ่านตารางเหล็กหรือผังกริด

### 7.5.3 Qwen2.5-VL (2025)

Qwen2.5-VL [7] ฝึก ViT ใหม่ตั้งแต่ต้นแบบ native dynamic resolution และใส่ window attention ในชั้นส่วนใหญ่ของ ViT เพื่อลดค่าใช้จ่ายเมื่อภาพใหญ่ (attention เต็มทุก patch มี cost $O(N^2)$ ภาพ 7,000 token จะแพงมาก) และปรับ M-RoPE ในแกนเวลาให้ผูกกับ "เวลาจริง" (absolute time) โมเดลรุ่นนี้ถูกเน้นเรื่อง document parsing และ grounding ให้ bbox กลับเป็นพิกัดพิกเซลจริง

### 7.5.4 Qwen3-VL (2025)

Qwen3-VL technical report [8] ระบุการเปลี่ยนแปลงหลักสามอย่าง: (1) interleaved-MRoPE ที่สลับความถี่ของสามแกนให้กระจายทั่ว embedding แทนการแบ่งเป็นช่วง ๆ (2) DeepStack เอา feature จาก ViT **หลายชั้น** (ไม่ใช่แค่ชั้นสุดท้าย) ฉีดเข้า LLM หลายชั้น เพื่อรักษารายละเอียดระดับต่ำ (เส้น ขอบ ตัวอักษรเล็ก) ที่มักหายไปตอนไปถึงชั้นบนของ ViT (3) text-timestamp alignment สำหรับวิดีโอ

ที่สำคัญกับเราคือ **patch ของ Qwen3-VL เปลี่ยนเป็น 16 px** เมื่อรวม merge $2 \times 2$ ได้ 1 token ต่อ $32 \times 32 = 1024$ px² ยืนยันจาก `preprocessor_config.json` ของ Qwen3-VL-8B (`patch_size: 16, merge_size: 2`) [23] ไม่ใช่ 28 px แบบ Qwen2.5-VL สคริปต์ t02 ของเราจึงเขียนกำกับไว้ว่า "ก็อป config เก่ามาจะ OOM" เพราะ token ต่อภาพต่างกัน $1024/784 \approx 1.3$ เท่า

### 7.5.5 Qwen3.5 / Qwen3.6 มี native vision จริงไหม (ตรวจสอบแล้ว)

brief ของหลักสูตรระบุว่า t01/t05 ใช้ Qwen3.6-35B-A3B เป็น VLM โดยตรง ผมตรวจสอบเมื่อ 2026-09-08 พบว่า

- Qwen3.5 (ออก 2026-02-16) ประกาศตัวเป็น "native vision-language model" model card ของ Qwen3.5-35B-A3B ระบุ "Unified Vision-Language Foundation" ที่ทำ "early fusion training on multimodal tokens" สถาปัตยกรรมเป็น hybrid Gated DeltaNet + attention แบบ MoE 256 experts (8 routed + 1 shared) รับภาพและวิดีโอได้ [9]
- Qwen3.6-35B-A3B (ออก 2026-04-16) model card ระบุ type เป็น "Causal Language Model with Vision Encoder" 35B รวม / 3B active, 256 experts, 9 active ต่อ token มีตัวอย่างรับ `image_url` และ `video_url` และมีตาราง benchmark หมวด Vision Language [10]
- `preprocessor_config.json` ของ Qwen3.6-35B-A3B ใช้ `Qwen3VLProcessor`, `patch_size: 16, merge_size: 2` เหมือน Qwen3-VL ทุกประการ [24] ดังนั้นสูตร 1 token = 1024 px² ที่ t05 ใช้คำนวณ MAX_LENGTH ถูกต้อง

สรุป: **ยืนยันได้** ว่า Qwen3.5/3.6 รับภาพได้โดยตรง (native) ไม่ใช่ LLM ล้วนที่ต้องต่อ vision แยก และตัวประมวลผลภาพเป็นตระกูลเดียวกับ Qwen3-VL สิ่งที่ยัง **ไม่พบเอกสารยืนยัน** คือรายละเอียดภายในว่า "early fusion" ของ Qwen3.5 ต่างจาก Qwen3-VL ตรงไหนในระดับสถาปัตยกรรม (report ของ Qwen3.5-Omni [11] กล่าวถึงข้อมูล text-vision แต่ไม่ลงรายละเอียด encoder) ผู้เรียนควรถือว่านี่คือส่วน state of the art ที่เปลี่ยนเร็ว

🎨 **ภาพที่จะวาดใน HTML:** ไทม์ไลน์แนวนอน Qwen-VL (2023) → Qwen2-VL (2024) → Qwen2.5-VL (2025) → Qwen3-VL (2025) → Qwen3.5/3.6 (2026) แต่ละจุดมีการ์ดแสดง "px ต่อ token" (คงที่ / 28 / 28 / 32 / 32) และฟีเจอร์เด่น ด้านล่างมีภาพแบบก่อสร้างใบเดียวกันวางไว้ เมื่อคลิกรุ่นไหน กริด token บนภาพจะเปลี่ยนความหยาบและตัวเลข token ต่อภาพจะอัปเดต

---

## 7.6 InternVL: ViT ยักษ์ + dynamic tiling (และทำไม t04 พัง)

InternVL [13][14] เลือกคนละทางกับ Qwen ตรง "ตา": แทนที่จะใช้ ViT ขนาด 300-600M มันเทรน InternViT-6B (6 พันล้านพารามิเตอร์) ตาที่ใหญ่มากพอจะเรียนรู้ feature ละเอียดได้เอง

ส่วนเรื่องภาพใหญ่ InternVL 1.5 ขึ้นไปใช้ **dynamic tiling**: ตัดภาพเป็นกระเบื้อง (tile) ขนาด $448 \times 448$ px ตามสัดส่วนภาพ สูงสุด 40 tile สำหรับภาพ 4K [13] แต่ละ tile ผ่าน ViT แยกกัน แล้ว pixel-shuffle ลดจำนวน token ต่อ tile จาก 1024 เหลือ 256 บวก thumbnail ของภาพทั้งใบอีก 1 tile เพื่อให้เห็นภาพรวม

ภาพ 3309×2339 ของเรา ถ้าตัดเป็น tile 448 จะได้ราว $7.4 \times 5.2$ ปัดเป็นตาราง เช่น $7 \times 5 = 35$ tile ($+1$ thumbnail) $= 36 \times 256 \approx 9{,}216$ token ใกล้เคียงกับ Qwen3-VL แบบไม่ย่อ

**t04 พังตรงไหน:** config ที่ใช้ตอนเทรนขาดตัวเปิด `crop_to_patches` ผลคือไม่มีการตัด tile เลย ทั้งภาพถูกย่อเหลือ tile เดียว 448×448 = 256 token ตลอดการเทรน (ตามที่ docstring ของ `train_t05_courser.py` บันทึกไว้) นี่คือบั๊กคลาสเดียวกับ 512px ของ t02 ต่างแค่กลไก: t02 ถูก collator ย่อ t04 ถูก tiling ที่ไม่ทำงานย่อ ทั้งสองครั้งโมเดลเห็นภาพ "หยาบกว่าที่ใช้จริง 15-30 เท่า" และไม่มีทางอ่านตัวเลขเหล็กได้

บทเรียนระดับหลักการ: **ทุก VLM มีตัวควบคุมจำนวน token ต่อภาพ ชื่อต่างกัน (max_pixels / crop_to_patches / max_num tiles) และค่า default มักไม่ใช่ค่าที่เราต้องการ** ต้องวัด token ต่อภาพจาก batch แรกเสมอ นี่คือที่มาของ assert `_tok > 1000` ใน train script ของเรา

🎨 **ภาพที่จะวาดใน HTML:** ภาพแบบก่อสร้างมีเส้นกริดสีส้มตัดเป็น tile 448 px สไลเดอร์ "max tiles" (1 ถึง 40) เมื่อเลื่อนลงถึง 1 ภาพจะถูกย่อทั้งใบใส่กรอบ 448 เดียว (จำลอง t04) ตัวเลขเหล็ก "DB12" บนภาพจะเบลอจนอ่านไม่ออก ด้านข้างแสดง token = tiles × 256 + 256

---

## 7.7 Llama 3.2 Vision: กลับไปทาง Flamingo

Llama 3.2 Vision (11B/90B) ใช้แนวทาง compositional ตามที่ Llama 3 paper อธิบาย [15] model card ระบุตรง ๆ ว่า "vision adapter ประกอบด้วยชุดของ cross-attention layers ที่ป้อน representation จาก image encoder เข้าสู่ LLM หลัก" โดย LLM ฐาน (Llama 3.1) ถูกแช่แข็งไว้ [16]

เปรียบเทียบสองแนวทางให้ชัด:

| | token concatenation (LLaVA, Qwen-VL, InternVL) | cross-attention (Flamingo, Llama 3.2 Vision) |
|---|---|---|
| ภาพเข้า LLM อย่างไร | เป็น token ในลำดับเดียวกับข้อความ | ผ่านชั้น cross-attention ที่แทรกเพิ่ม |
| context ที่ภาพกิน | เท่าจำนวน visual token (พันถึงหมื่น) | ไม่กิน context ข้อความ |
| พารามิเตอร์ใหม่ | projector เล็ก | cross-attention หลายชั้น (หลายพันล้าน) |
| ความสามารถข้อความเดิม | อาจถูกกระทบตอนทูนทั้งก้อน | รักษาไว้ได้ดี (LLM ไม่ถูกแตะ) |
| เครื่องมือ (LoRA, GGUF, vLLM) | รองรับกว้าง | รองรับช้ากว่า |
| หลายภาพ / ภาพใหญ่มาก | context ระเบิดง่าย | รับได้สบายกว่า |

สำหรับงานเรา ข้อได้เปรียบเรื่อง context ของ cross-attention น่าสนใจ (gridmaster ของเรามัด 2-4 ภาพต่อตัวอย่าง จน MAX_LENGTH ต้องขึ้นไป 24,576-47,104 token) แต่ความพร้อมของเครื่องมือฝั่ง Qwen สูงกว่ามาก และประวัติการทูนสำเร็จของเราอยู่ฝั่ง Qwen ทั้งหมด

🎨 **ภาพที่จะวาดใน HTML:** สองแผงเทียบกัน ซ้าย token concat: แถบลำดับ token ที่ยาวขึ้นเมื่อเพิ่มภาพ (ปุ่ม "+ภาพ") พร้อมมิเตอร์ context ที่วิ่งเข้าใกล้ MAX_LENGTH ขวา cross-attention: ลำดับ token ยาวเท่าเดิม แต่มีกล่องภาพลอยอยู่ข้าง ๆ พร้อมลูกศรเข้าชั้นที่ 4, 8, 12 ของ LLM มิเตอร์ "พารามิเตอร์ใหม่" ของฝั่งขวาสูงกว่า

---

## 7.8 ทำไม VLM อ่านแบบก่อสร้างยากกว่าอ่านรูปแมว

### 7.8.1 ธรรมชาติของภาพ

ภาพถ่ายทั่วไป: วัตถุใหญ่ สีต่างกัน ข้อมูลกระจายทั่วภาพ ย่อเหลือ 336 px ก็ยังรู้ว่าเป็นแมว
แบบก่อสร้าง: พื้นขาว เส้นดำบาง 1-2 px ตัวหนังสือสูง 8-12 px ตัวเลขนับร้อย ข้อมูลอยู่ที่ "เส้นบางกับตัวเลขเล็ก" ทั้งนั้น ย่อ 2 เท่า ตัวเลขก็หาย ย่อ 6 เท่า (3309→512) เหลือแต่ผังคร่าว ๆ

feature ของ ViT ที่เรียนมาจากภาพเว็บ ถูกสอนให้ "ทน" ต่อการย่อขยายและ noise เพราะแมวย่อแล้วยังเป็นแมว แต่ความทนนี้เป็นศัตรูกับเราเมื่อ Ø12 กับ DB23 ต่างกันแค่ตัวอักษรเดียว

### 7.8.2 resolution vs token budget

ถ้ายอมให้ภาพละเอียดพอ token ก็พุ่ง ค่าใช้จ่ายทั้ง VRAM ตอนเทรน (activation ยาวตาม sequence) และเวลา inference โตตาม $N$ และ attention โตตาม $N^2$ ถ้ารัดเข็มขัด token ก็อ่านตัวเลขไม่ออก นี่คือข้อแลกเปลี่ยนหลักของบทนี้ และคือเหตุผลที่ t03/t05 ต้องใช้ `measure_capacity.py` วัดว่า max_pixels เท่าไหร่ภาพถึงจะไม่โดนย่อ (ที่ 5,120 token ภาพเทรนโดนย่อ 100% ที่ 7,680 เหลือ 30%) แล้วยังต้องลดลง 6,912 เพราะ OOM จริงบนการ์ด 96GB

### 7.8.3 การนับและ hallucination

VLM ไม่ได้ "นับ" ด้วยกลไกที่รับประกันผล มันทำนาย token ถัดไปที่น่าจะเป็น ถ้าคานตัวเดียวกันควรปรากฏ 10 ครั้ง (B2 × 10) โมเดลอาจตอบ 8 หรือ 13 หรือวนซ้ำไม่จบ (บั๊ก greedy decoding ของเรา) benchmark AECV-Bench (2026) ที่ทดสอบโมเดลชั้นนำกับแบบสถาปัตย์จริงพบว่า OCR ทำได้ถึง 0.95 แต่ "การนับสัญลักษณ์ เช่น ประตู หน้าต่าง ยังไม่ถูกแก้ (0.40-0.55)" และสรุปว่าโมเดลปัจจุบัน "ขาด drawing literacy" [17] ตรงกับประสบการณ์เราทุกข้อ และเป็นเหตุผลที่ท่อของเราให้ CV (`cv2.matchTemplate`) เป็นคนนับ แล้วให้ VLM เป็นคนอ่านความหมาย

🎨 **ภาพที่จะวาดใน HTML:** ภาพแบบก่อสร้างจริงย่อขนาด มีสไลเดอร์ "max_pixels" ที่มีจุดหมาย 512px-collator, 5120 tok, 6912 tok, 7680 tok, native เมื่อเลื่อน ภาพจะถูก downsample จริง (canvas) และแว่นขยายบนตัวเลข "DB12" แสดงว่าอ่านออกหรือไม่ ใต้ภาพเป็นแท่งกราฟสองแท่ง: token ต่อภาพ และ VRAM โดยประมาณ (สเกลเชิงเส้นและกำลังสอง) ให้เห็นว่าจุดที่ "อ่านออก" กับจุดที่ "การ์ดรับไหว" มันชนกันตรงไหน

---

## 7.9 งานวิจัย document understanding และแบบก่อสร้าง

### 7.9.1 สาย document (พื้นฐานที่ไม่เปลี่ยน)

- **Donut** (Kim และคณะ, 2021/2022) [18] พิสูจน์ว่าไม่ต้องมี OCR แยก โมเดล encoder-decoder อ่านภาพเอกสารแล้วพ่น JSON ได้ตรง ๆ นี่คือรูปแบบงานเดียวกับเรา (ภาพ → JSON) ก่อนยุค LLM
- **Pix2Struct** (Lee และคณะ, 2022) [19] pretrain ด้วยการ "แปลง screenshot เว็บเป็น HTML" ทำให้โมเดลเก่งโครงสร้างเชิงพื้นที่ (ตาราง แผนภูมิ)
- **DocVQA** (Mathew และคณะ, 2020) [20] และ **ChartQA** (Masry และคณะ, 2022) [25] คือ benchmark มาตรฐานที่ทุก VLM รายงาน ถ้าเห็น model card บอก DocVQA 95+ แปลว่าอ่านฟอร์ม/ตารางได้ดี แต่ไม่ได้แปลว่าอ่านแบบก่อสร้างได้
- **Florence-2** (Xiao และคณะ, 2023) [26] และ **PaliGemma** (Beyer และคณะ, 2024) [12] เป็น VLM ขนาดเล็กที่ออกแบบให้ทำ detection/grounding ผ่านข้อความ เหมาะกับการเป็น "เครื่องมือ" ตัวที่สองมากกว่าเป็นสมองหลัก

### 7.9.2 สายแบบก่อสร้าง / CAD (state of the art เปลี่ยนเร็ว)

- **CubiCasa5K** (Kalervo และคณะ, 2019) [27] dataset แปลนบ้าน 5,000 ใบพร้อม annotation ห้อง/ผนัง/ไอคอน เป็น dataset แปลนที่ถูกใช้มากที่สุด แต่เป็นแปลนสถาปัตย์ ไม่ใช่แบบโครงสร้าง คสล.
- **AECV-Bench** (Kondratenko และคณะ, 2026) [17] benchmark แรก ๆ ที่วัด VLM กับแบบ AEC จริง ด้วยงานนับวัตถุบนแปลน 120 ใบและ QA 192 ข้อ
- **FloorplanVLM** (Liu และคณะ, 2026) [28] จัดรูปแบบ "vectorize แปลน" เป็น image-conditioned sequence modeling ให้ VLM พ่น JSON ของ topology อาคารออกมา แนวคิดเดียวกับท่อของเราเป๊ะ
- **ArchPlanVQA** (Journal of Computing in Civil Engineering, 2026) benchmark VQA บนแปลน CAD สถาปัตย์ (พบจากการค้น แต่เข้าถึงเนื้อหาเต็มไม่ได้ในการตรวจสอบครั้งนี้)

สิ่งที่ยังไม่มีในวรรณกรรมเท่าที่ค้นพบ: dataset สาธารณะของ **แบบโครงสร้าง คสล. ระดับรายละเอียดเหล็กเสริม** ที่ label เป็น JSON ตามหลักถอดปริมาณ นั่นคือช่องว่างที่ dataset ของโปรเจกต์นี้กำลังเติม

### 7.9.3 visual grounding: ทำไมต้องขอ bbox กลับ

grounding คือการให้โมเดลตอบ "สิ่งนี้อยู่ตรงไหนในภาพ" เป็นพิกัด $(x_1, y_1, x_2, y_2)$ Qwen-VL ตั้งแต่รุ่นแรกถูกสอนเรื่องนี้ [5] และ Qwen2.5-VL คืนเป็นพิกเซลจริง [7]

กับงานตรวจสอบของเรา bbox มีค่ามหาศาลสามทาง: (1) คนตรวจใน review.html เห็นได้ทันทีว่าโมเดลอ่าน "B2" จากตรงไหน ไม่ต้องไล่หาเอง (2) เอา bbox ของ VLM ไปเทียบกับกล่องจาก `cv2.matchTemplate` ได้ ถ้าไม่ซ้อนกันเลยแปลว่ามีฝ่ายหนึ่ง hallucinate (3) ใน pass3 ของ t05 เราทำกลับด้าน: ให้ CV วาดเลขมาร์คลงบนภาพก่อน แล้วให้ VLM อ่าน spec ตามเลขมาร์ค ซึ่งคือการ "บังคับ grounding" ด้วยภาพ input แทนที่จะหวังให้โมเดลคืนพิกัดเอง

🎨 **ภาพที่จะวาดใน HTML:** ภาพแบบแปลนคาน มีเลเยอร์เปิด-ปิดสามชั้น: กล่องจาก CV (สีน้ำเงิน), กล่องจาก VLM grounding (สีแดง), และป้ายเลขมาร์คแบบ pass3 (สีเขียว) เมื่อเปิดสองชั้นแรกพร้อมกัน ระบบคำนวณ IoU ของแต่ละคู่และไฮไลต์คู่ที่ IoU < 0.3 ว่า "ต้องให้คนดู"

---

## 7.10 คำนวณ token budget ของภาพ 3309×2339 ให้ดู

ใช้สูตรของ Qwen3-VL / Qwen3.6: 1 token ต่อ $32 \times 32$ px หลังปัดขนาดให้หาร 32 ลงตัว และถ้าพิกเซลรวมเกิน `max_pixels` ย่อด้วยสเกล $s = \sqrt{\text{max\_pixels} / (H \times W)}$

ภาพต้นฉบับ $3309 \times 2339 = 7{,}739{,}751$ px

| ตั้งค่า | max_pixels (px) | สเกล $s$ | ขนาดหลังปัด | token ≈ | ใช้ที่ไหน |
|---|---|---|---|---|---|
| native (ไม่ย่อ) | ≥ 7,739,751 | 1.00 | 3296×2336 | 103×73 = **7,519** | เพดาน 7,680 ของ t03b ครอบพอดี |
| 7680 tok | 7,864,320 | 1.00 | 3296×2336 | **7,519** | t03b/t05 ตั้งต้น |
| 6912 tok | 7,077,888 | 0.956 | 3136×2208 | 98×69 = **6,762** | t05 หลัง OOM |
| 5120 tok | 5,242,880 | 0.823 | 2720×1920 | 85×60 = **5,100** | t01/t02 |
| collator 512 px | ด้านยาว 512 | 0.155 | 512×352 | 16×11 = **176** (วัดจริงในรอบนั้น ~266 เพราะ rounding/aspect ต่างกัน) | บั๊ก t02 |
| inference จริง | (ค่า default ของ pipeline) | | | **~3,796** | ตามที่วัดตอนใช้จริง |

อัตราส่วน $3{,}796 / 266 \approx 14$ เท่า คือตัวเลข "14 เท่า" ในบันทึกบั๊กของเรา และแม้เราแก้ให้เทรนที่ 7,519 แล้ว ก็ยังต้องไปตั้ง inference ให้เท่ากัน ไม่งั้นก็จะ mismatch ในทิศตรงข้าม (เทรนละเอียด ใช้จริงหยาบ)

```python
import math
H, W = 2339, 3309
def qwen3_tokens(max_pixels, unit=32):
    s = min(1.0, math.sqrt(max_pixels / (H * W)))
    h = int(H * s) // unit * unit          # ปัดลงให้หาร 32 ลงตัว (ประมาณ smart_resize)
    w = int(W * s) // unit * unit
    return (h, w), (h // unit) * (w // unit)
for name, mp in [("native", H*W), ("7680", 7680*1024), ("6912", 6912*1024),
                 ("5120", 5120*1024), ("512px-longest", 512*int(512*H/W))]:
    size, tok = qwen3_tokens(mp)
    print(f"{name:>14}: max_pixels={mp:>10,} -> {size} -> {tok:,} tokens")
```

ลองเปลี่ยน `unit=28` เพื่อดูสูตรของ Qwen2.5-VL แล้วเทียบว่า token ต่างกันกี่เปอร์เซ็นต์

🎨 **ภาพที่จะวาดใน HTML:** เครื่องคิดเลข token: ช่องกรอก H, W, สไลเดอร์ max_pixels (log scale 0.1M ถึง 16M), ปุ่มเลือก unit (28 = Qwen2.5-VL / 32 = Qwen3-VL) แสดงผลเป็นภาพย่อที่ปรับขนาดจริงพร้อมกริด และตัวเลขใหญ่ "token ต่อภาพ" มีเส้นแนวตั้งบนสไลเดอร์บอกตำแหน่ง 266 (บั๊ก) และ 3,796 (inference) พร้อมป้าย "×14"

---

## 7.11 เชื่อมกับงานของเรา

| แนวคิดในบทนี้ | ปรากฏที่ไหนในรีโป | บั๊กที่อธิบายได้ |
|---|---|---|
| visual token = พิกเซล / (patch × merge)² | `train_qwen3vl.py` คอมเมนต์ "1 visual token / 32x32 px" และสูตร H×W/1024 ใน `t05_workflow.md` §B | บั๊ก 1 (512px/266 token) และบั๊ก 6 (คำเตือน ≥1024 image token ถูกมองข้าม) |
| min_pixels / max_pixels ควบคุมย่อ-ขยาย | `ip.size["longest_edge"] = P["max_pixels"]` ใน t02, `MAX_PIXELS = 6912*1024` ใน t05 | บั๊ก 5: ค่า default (16,777,216 px = 16,384 token) ที่ไม่ได้ตั้ง ทำ sequence ยาวเกินและ OOM (บั๊ก 7) |
| collator เป็นอีกจุดที่ย่อภาพได้ | `UnslothVisionDataCollator(..., resize="max")` + assert `_tok > 1000` | บั๊ก 1 ตรง ๆ |
| dynamic tiling ของ InternVL | t04 Purson ล้มเหลว (`crop_to_patches` ขาด → 1 tile 256 token) | คลาสเดียวกับบั๊ก 1 |
| freeze vision tower | `finetune_vision_layers=False` ทั้ง t02 และ t05 | ทำให้ใช้ mmproj ทางการตอน export GGUF ได้ และเป็นเหตุผลที่ LoRA แตะเฉพาะ LLM (บทที่ 8) |
| train/inference token ต้องเท่ากัน | ~3,796 token ตอนใช้จริง vs ตอนเทรน | บั๊ก 1 ในมุม distribution shift (ขยายในบทที่ 8) |
| VLM นับไม่แม่น | `tools/cv_scan.py`, `pattern_recognition.py` ทำหน้าที่นับ; VLM อ่านความหมาย | บั๊ก 4 (วน B2 ไม่จบ) เป็นอาการของโมเดลที่ไม่มีกลไกนับ |
| grounding | pass3 ของ t05 ให้ CV มาร์คเลขบนภาพก่อน | ลด hallucination ตำแหน่ง |

ประโยคเดียวที่สรุปทั้งบท: **บั๊กที่แพงที่สุดสองรอบของโปรเจกต์ (t02, t04) ไม่ใช่บั๊กของโมเดล แต่เป็นบั๊กของ "จำนวน visual token" ที่เราไม่ได้วัด** และวิธีป้องกันคือ assert ตัวเดียวที่ batch แรก

---

## 7.12 ระดับนักวิจัย: คำถามที่ยังเปิดอยู่

1. **native multimodal (early fusion) vs ต่อ encoder ทีหลัง:** InternVL3 [14] และ Qwen3.5 [9] ต่างอ้างว่าการเทรนภาพ-ข้อความร่วมกันตั้งแต่ pretrain ให้ผลดีกว่าการต่อ ViT เข้ากับ LLM ที่เทรนเสร็จแล้ว แต่ต้นทุนคือต้อง pretrain ใหม่ทั้งก้อน คำถามที่ยังไม่มีคำตอบชัดคือ ผลได้นี้ยังอยู่ไหมเมื่อ domain เป็นภาพเชิงเทคนิค (แบบก่อสร้าง) ที่แทบไม่มีใน pretrain data
2. **visual token ควรเป็นกี่ตัว:** ฝั่งหนึ่งเพิ่ม resolution (Qwen dynamic resolution, InternVL tiling) อีกฝั่งบีบ token (Q-Former, token pruning/merging) Qwen3-VL ตอบด้วย DeepStack (ส่ง feature หลายชั้นแทนเพิ่มจำนวน token) [8] ยังไม่มีฉันทามติว่าสำหรับงาน OCR-หนักแบบเรา แนวทางไหนให้ "ความละเอียดต่อ token" ดีที่สุด
3. **counting และ symbol literacy:** AECV-Bench [17] ชี้ว่าการนับสัญลักษณ์บนแบบยังแก้ไม่ตก คำถามคือควรแก้ที่โมเดล (เทรนให้นับ) หรือที่ระบบ (ให้ CV นับ, ให้ VLM ตรวจ) แนวทางของเรา (pass2.5 CV + pass3 VLM) คือฝั่งหลัง
4. **cross-attention จะกลับมาไหม:** Llama 3.2 Vision [16] เลือก cross-attention เพื่อไม่ให้ภาพกิน context เมื่อ context ยาว 256K กลายเป็นมาตรฐาน (Qwen3-VL) ข้อได้เปรียบนี้อาจหมดความหมาย หรืออาจกลับมาสำคัญเมื่อต้องอ่านแบบทั้งชุด 100 หน้าในครั้งเดียว
5. **grounding ที่ตรวจสอบได้:** FloorplanVLM [28] และงานสาย document ให้โมเดลพ่นโครงสร้าง JSON ที่ผูกพิกัด แต่ยังไม่มีมาตรฐานว่า bbox ที่โมเดลคืนมา "เชื่อได้แค่ไหน" การใช้ CV เป็นตัวสอบทาน (แบบที่เราทำ) เป็นวิธีปฏิบัติ ไม่ใช่ทฤษฎี

---

## 7.13 แบบฝึกหัด

**ข้อ 1 (คำนวณ):** ภาพหน้ารายละเอียดเสาถูกสแกนที่ 2480×3508 px (A4 300 dpi แนวตั้ง) ถ้าใช้ Qwen3-VL ที่ max_pixels = 5120×1024 จะได้ visual token ประมาณกี่ตัว และถ้าเป็น Qwen2.5-VL (unit 28) ล่ะ

<details><summary>เฉลย</summary>
พิกเซล = 8,700,000 > 5,242,880 → s = √(5,242,880/8,700,000) ≈ 0.776 → 1925×2723 → ปัด 32: 1920×2720 → 60×85 = 5,100 token (เท่าภาพแนวนอนเพราะพิกเซลรวมเท่ากัน) ส่วน unit 28: 1904×2716 → 68×97 = 6,596 token มากกว่าราว 29%
</details>

**ข้อ 2 (คิด):** ถ้าเราปลด freeze ให้เทรน ViT ด้วยใน t05 (dataset ~1,000 ตัวอย่างต่อ fold) ให้ระบุความเสี่ยง 2 ข้อ และผลกระทบต่อขั้นตอน export GGUF

<details><summary>เฉลย</summary>
(1) ViT ถูกเทรนด้วยข้อมูลน้อยมากเทียบกับ pretrain (400M คู่) feature ทั่วไปอาจพัง (catastrophic forgetting ของฝั่งภาพ) (2) VRAM และเวลาเพิ่มเพราะ gradient ต้องไหลผ่าน ViT ทั้งก้อนที่รับ 7,000 token ต่อภาพ ส่วน export: mmproj ทางการใช้ไม่ได้อีก ต้องแปลง vision encoder ที่ทูนแล้วเอง ซึ่งเป็นเส้นทางที่ยังไม่เคยพิสูจน์ในรีโป
</details>

**ข้อ 3 (รันโค้ด):** แก้โค้ดใน 7.10 ให้รับภาพหลายใบ (เช่น gridmaster 4 ใบ) แล้วรวม token ทั้งหมด บวก instruction 1,022 และ output 2,818 token ตรวจว่าเกิน MAX_LENGTH 24,576 ของ t02 หรือไม่ ที่ max_pixels 5120 และ 7680

<details><summary>เฉลย</summary>
5120: 4×5,100 + 1,022 + 2,818 = 24,240 < 24,576 ผ่านหวุดหวิด · 7680: 4×7,519 + 3,840 = 33,916 > 24,576 ต้องเพิ่ม MAX_LENGTH (t03 วัดได้ 44,607 จากภาพ 4 ใบจริงและตั้ง 47,104)
</details>

**ข้อ 4 (คิด):** ทำไม Q-Former แบบ BLIP-2 ถึงไม่เหมาะกับงานถอดรายการเหล็ก แม้จะประหยัด token กว่า LLaVA ถึง 18 เท่า

<details><summary>เฉลย</summary>
query 32 ตัวเป็น bottleneck ที่ตายตัว ข้อมูลในแบบ (ตัวเลขนับร้อยจุด) ถูกบีบก่อนถึง LLM ไม่ว่าจะทูนอย่างไร LLM ก็ไม่เคยได้เห็นรายละเอียดที่ถูกทิ้ง ต่างจาก LLaVA/Qwen ที่ทุก patch ยังอยู่ให้ attention เลือกได้
</details>

**ข้อ 5 (คิด):** ให้ออกแบบ "การทดสอบ 1 นาที" ที่จับบั๊กคลาส t02/t04 ได้ทั้งคู่ โดยไม่ต้องเช่า GPU

<details><summary>เฉลย</summary>
รัน collator/processor กับตัวอย่างแรกบน CPU แล้วพิมพ์จำนวน visual token ต่อภาพ (จาก `image_grid_thw` หรือ `pixel_values.shape`) เทียบกับค่าที่คาดจากสูตร H×W/1024 ถ้าต่ำกว่า 1,000 ให้หยุด นี่คือ assert ที่มีอยู่แล้วใน train script ของเรา และ Phase 0 ข้อ 3 ของ t05
</details>

---

## สรุปบทนี้ใน 5 บรรทัด

1. VLM = vision encoder (ViT) + projector/merger + LLM decoder ภาพถูกแปลงเป็น "visual token" ที่นั่งในลำดับเดียวกับข้อความ (LLaVA/Qwen/InternVL) หรือถูกมองผ่าน cross-attention (Flamingo/Llama 3.2 Vision)
2. CLIP สอนตากับภาษาให้ใช้ไม้บรรทัดเดียวกันด้วย contrastive loss บนคู่ภาพ-ข้อความ 400 ล้านคู่ ViT จาก CLIP/SigLIP กลายเป็นตาของ VLM ยุคแรกทั้งหมด
3. จำนวน visual token = พิกเซล / (patch × merge)² ; Qwen2/2.5-VL ใช้ 28 px ต่อ token, Qwen3-VL และ Qwen3.5/3.6 ใช้ 32 px ; `min_pixels`/`max_pixels` (หรือ tiling ของ InternVL) คือคันเร่งและเบรก
4. แบบก่อสร้างต้องการความละเอียดสูง (7,519 token ต่อหน้าแบบไม่ย่อ) ทุกจุดที่ย่อภาพเงียบ ๆ (collator 512 px, tile เดียว 256 token) = บั๊กที่แพงที่สุดของโปรเจกต์ ต้องวัด token จาก batch แรกเสมอ
5. VLM อ่านความหมายได้แต่นับไม่แม่นและ hallucinate ได้ (AECV-Bench: การนับสัญลักษณ์ยังไม่ถูกแก้) จึงต้องมี CV เป็นคู่หูนับและสอบทานตำแหน่ง (grounding)

---

## ที่มาและอ่านต่อ

| # | แหล่ง | ประเภท | ทำไมควรอ่าน | URL |
|---|---|---|---|---|
| 1 | Radford et al. (2021) "Learning Transferable Visual Models From Natural Language Supervision" (CLIP) | paper | ต้นกำเนิด contrastive image-text, 400M คู่ | https://arxiv.org/abs/2103.00020 |
| 2 | Alayrac et al. (2022) "Flamingo: a Visual Language Model for Few-Shot Learning" | paper | แนวทาง cross-attention แทรกใน LLM แช่แข็ง | https://arxiv.org/abs/2204.14198 |
| 3 | Li et al. (2023) "BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models" | paper | Q-Former และการเชื่อม encoder แช่แข็งกับ LLM แช่แข็ง | https://arxiv.org/abs/2301.12597 |
| 4 | Liu et al. (2023) "Visual Instruction Tuning" (LLaVA) | paper | projector + visual instruction tuning 2 ขั้น สูตรที่ทุกคนลอก | https://arxiv.org/abs/2304.08485 |
| 5 | Bai et al. (2023) "Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond" | paper | จุดเริ่มสาย Qwen-VL เน้น OCR และ grounding | https://arxiv.org/abs/2308.12966 |
| 6 | Wang et al. (2024) "Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution" | paper | naive dynamic resolution, M-RoPE, min/max_pixels | https://arxiv.org/abs/2409.12191 |
| 7 | Qwen Team (2025) "Qwen2.5-VL Technical Report" | paper | window attention, absolute time, document parsing, grounding พิกเซลจริง | https://arxiv.org/abs/2502.13923 |
| 8 | Bai et al. (2025) "Qwen3-VL Technical Report" | paper | DeepStack, interleaved-MRoPE, text-timestamp, 256K context | https://arxiv.org/abs/2511.21631 |
| 9 | Qwen (2026) Qwen3.5-35B-A3B model card | docs | ยืนยัน native vision, early fusion, hybrid Gated DeltaNet + MoE | https://huggingface.co/Qwen/Qwen3.5-35B-A3B |
| 10 | Unsloth/Qwen (2026) Qwen3.6-35B-A3B model card | docs | โมเดลของ t01/t05: "Causal Language Model with Vision Encoder" 35B/3B active | https://huggingface.co/unsloth/Qwen3.6-35B-A3B |
| 11 | Qwen Team (2026) "Qwen3.5-Omni Technical Report" | paper | เอกสารทางเทคนิคใกล้เคียงที่สุดของตระกูล 3.5 (ยังไม่ลงรายละเอียด vision encoder) | https://arxiv.org/abs/2604.15804 |
| 12 | Beyer et al. (2024) "PaliGemma: A versatile 3B VLM for transfer" | paper | SigLIP + LLM เล็ก ออกแบบเพื่อ transfer/fine-tune | https://arxiv.org/abs/2407.07726 |
| 13 | Chen et al. (2024) "How Far Are We to GPT-4V?" (InternVL 1.5) | paper | InternViT-6B, dynamic tiling 448 px สูงสุด 40 tile | https://arxiv.org/abs/2404.16821 |
| 14 | Zhu et al. (2025) "InternVL3: Exploring Advanced Training and Test-Time Recipes for Open-Source Multimodal Models" | paper | native multimodal pretraining, โมเดลของ t04 | https://arxiv.org/abs/2504.10479 |
| 15 | Meta (2024) "The Llama 3 Herd of Models" | paper | compositional approach สำหรับภาพ/วิดีโอ/เสียง | https://arxiv.org/abs/2407.21783 |
| 16 | Meta (2024) Llama-3.2-11B-Vision-Instruct model card | docs | ระบุชัดว่า adapter คือ cross-attention layers ป้อน image encoder เข้า LLM | https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct |
| 17 | Kondratenko et al. (2026) "AECV-Bench: Benchmarking Multimodal Models on Architectural and Engineering Drawings Understanding" | paper | หลักฐานว่าการนับสัญลักษณ์บนแบบยังไม่ถูกแก้ (0.40-0.55) | https://arxiv.org/abs/2601.04819 |
| 18 | Kim et al. (2021) "OCR-free Document Understanding Transformer" (Donut) | paper | ภาพเอกสาร → JSON ไม่ต้องมี OCR | https://arxiv.org/abs/2111.15664 |
| 19 | Lee et al. (2022) "Pix2Struct: Screenshot Parsing as Pretraining for Visual Language Understanding" | paper | pretrain ด้วยโครงสร้างหน้าจอ | https://arxiv.org/abs/2210.03347 |
| 20 | Mathew et al. (2020) "DocVQA: A Dataset for VQA on Document Images" | paper | benchmark มาตรฐานเอกสาร 50k คำถาม | https://arxiv.org/abs/2007.00398 |
| 21 | Lilian Weng (2022) "Generalized Visual Language Models" | blog | จัดหมวด VLM 4 แบบ อ่านง่ายที่สุด | https://lilianweng.github.io/posts/2022-06-09-vlm/ |
| 22 | Qwen2-VL-7B-Instruct preprocessor_config.json | docs | patch 14, merge 2, min/max_pixels จริง | https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct/blob/main/preprocessor_config.json |
| 23 | Qwen3-VL-8B-Instruct preprocessor_config.json | docs | patch 16, merge 2, longest_edge 16,777,216 | https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct/blob/main/preprocessor_config.json |
| 24 | Qwen3.6-35B-A3B preprocessor_config.json | docs | ยืนยัน Qwen3.6 ใช้ Qwen3VLProcessor patch 16 merge 2 | https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/main/preprocessor_config.json |
| 25 | Masry et al. (2022) "ChartQA" | paper | benchmark แผนภูมิ 32.7k คำถาม | https://arxiv.org/abs/2203.10244 |
| 26 | Xiao et al. (2023) "Florence-2: Advancing a Unified Representation for a Variety of Vision Tasks" | paper | detection/grounding ผ่าน prompt ข้อความ | https://arxiv.org/abs/2311.06242 |
| 27 | Kalervo et al. (2019) "CubiCasa5K" | paper | dataset แปลนบ้าน 5,000 ใบ | https://arxiv.org/abs/1904.01920 |
| 28 | Liu et al. (2026) "FloorplanVLM: A Vision-Language Model for Floorplan Vectorization" | paper | แปลน → JSON ด้วย VLM แนวเดียวกับท่อของเรา | https://arxiv.org/abs/2602.06507 |
| 29 | Hugging Face (2024) "Vision Language Models Explained" | blog | ภาพรวมสถาปัตยกรรม + โค้ด fine-tune ด้วย TRL | https://huggingface.co/blog/vlms |
