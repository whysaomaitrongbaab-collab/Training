# บทที่ 8: Fine-tuning คืออะไรกันแน่ — Full FT, LoRA, QLoRA และตัวแปรทุกตัวใน train script ของเรา

> **เป้าหมายของบทนี้:**
> - คำนวณได้เองว่า full fine-tune โมเดล 8B ต้องใช้ VRAM เท่าไหร่ และทำไม LoRA ถึงลดลงได้เป็นสิบเท่า
> - อ่านสมการ $W' = W + BA$ แล้วอธิบายได้ว่า r, alpha, target_modules, dropout, merge_and_unload แต่ละตัวทำอะไรทางคณิตศาสตร์ และโยงกับบั๊ก "adapter ไม่ถูก merge เข้า GGUF" ได้
> - เปิด `train_t05_courser.py` แล้วอธิบายเหตุผลของค่าทุกตัว (lr 1e-4, epochs, batch 1 × grad_accum 8, cosine, warmup, max_length, freeze vision) รวมถึงบอกได้ว่าค่าไหนคือ "หลักการ" และค่าไหนคือ "ผลจากการชน OOM จริง"
>
> **ต้องอ่านบทไหนมาก่อน:** บทที่ 3 (gradient descent, loss), บทที่ 4-5 (Transformer, LLM), บทที่ 7 (VLM และ visual token)
>
> **เวลาอ่านโดยประมาณ:** 75-90 นาที (รวมลองรันโค้ด)

---

## 8.0 คำถามเปิด (ผูกกับงานจริงของเรา)

รอบ t01 เราทูน Qwen3.6-35B-A3B แล้วได้ element recall 28.2% สูงสุดของโปรเจกต์ รอบต่อมามีอยู่ช่วงหนึ่งที่ทีมเชื่อว่า "ทูนแล้ว 90%" แต่พอไล่ดูจริง ๆ พบว่า LoRA adapter อาจไม่ถูก merge เข้าไฟล์ GGUF ที่เอาไปวัด สิ่งที่วัดอยู่คือโมเดลเปล่า (บั๊กข้อ 2 ในรายการของเรา)

จะเข้าใจว่าบั๊กนี้เกิดได้อย่างไร ต้องเข้าใจก่อนว่า LoRA ไม่ได้ "แก้" น้ำหนักของโมเดล มันเก็บ "ส่วนต่าง" ไว้ในไฟล์แยก ถ้าไม่เอาส่วนต่างนั้นบวกกลับ (merge) ก่อน export โมเดลก็คือโมเดลเดิมทุกไบต์

คำถามที่บทนี้ต้องตอบ:

1. fine-tune ต่างจาก pretrain อย่างไร และทำไมเราไม่เทรน Qwen ใหม่ตั้งแต่ศูนย์ให้อ่านแบบก่อสร้าง
2. ทำไม full fine-tune 8B ต้องใช้การ์ด 128GB ทั้งที่ไฟล์โมเดลแค่ 16GB
3. LoRA ทำอะไรทางคณิตศาสตร์ ทำไม r=16 (t05) ถึงพอ และ alpha คืออะไร
4. ค่าทุกตัวใน `train_t05_courser.py` มาจากไหน อะไรเป็นทฤษฎี อะไรเป็นแผลจาก OOM
5. จะรู้ได้อย่างไรว่าทูน "ติด" จริง ไม่ใช่แค่เชื่อว่าติด

เทียบกับงานวิศวกร: pretrain คือการเรียนวิศวกรรมโยธา 4 ปี fine-tune คือการฝึกงาน 3 เดือนที่บริษัทเราให้อ่านแบบตามมาตรฐานเรา LoRA คือการ "เสริมแผ่นเหล็กบางบนคานเดิม" แทนที่จะทุบคานทิ้งแล้วหล่อใหม่ คานเดิม (base model) รับน้ำหนักได้อยู่แล้ว เราแค่เสริมให้รับ load case ใหม่

---

## 8.1 Pretrain กับ fine-tune: transfer learning

### 8.1.1 สองขั้นที่ต่างกันด้วยข้อมูลและเป้าหมาย

| | Pretrain | Fine-tune |
|---|---|---|
| ข้อมูล | ข้อความ/ภาพนับล้านล้าน token จากอินเทอร์เน็ต | ตัวอย่างของเราหลักร้อยถึงพัน |
| เป้าหมาย | ทำนาย token ถัดไปให้ได้ทุกเรื่อง | ทำงานเฉพาะให้ได้ในรูปแบบที่เราต้องการ |
| ใครทำ | Alibaba, Meta, OpenAI | เรา |
| ต้นทุน | ล้านดอลลาร์ | สิบดอลลาร์ (t03 จริง ≈ $5 เทรน 5 ชม.) |

หลักการเบื้องหลังคือ transfer learning: ความรู้ที่โมเดลได้จาก pretrain (ภาษาไทย, คำว่า "คาน", การนับ, การเขียน JSON, การมองเส้นในภาพ) ถูก "ถ่ายโอน" มาใช้กับงานใหม่ เราไม่ต้องสอนมันตั้งแต่ว่า JSON คืออะไร สอนแค่ว่า "แบบหน้านี้ควรออกมาเป็น JSON แบบนี้"

LIMA (Zhou และคณะ, 2023) [10] เป็นหลักฐานเชิงประจักษ์ที่ชัดที่สุด: โมเดล 65B ที่ fine-tune ด้วยตัวอย่างคัดสรรเพียง 1,000 ตัว ให้ผลใกล้เคียง GPT-4 ในการสนทนา ข้อสรุปของ paper คือ "ความรู้เกือบทั้งหมดถูกเรียนตอน pretrain ส่วน fine-tune แค่สอนรูปแบบและสไตล์"

### 8.1.2 กลไกทางคณิตศาสตร์เหมือนเดิมทุกประการ

fine-tune ไม่ได้ใช้เวทมนตร์อื่น มันคือ gradient descent จากบทที่ 3 บน loss เดียวกับ pretrain (cross-entropy ของ token ถัดไป) ต่างกันแค่ (ก) เริ่มจากน้ำหนักที่ดีอยู่แล้ว ไม่ใช่สุ่ม (ข) ข้อมูลน้อยและเฉพาะทาง (ค) learning rate เล็กกว่ามาก เพราะเราไม่อยากเดินไกลจากจุดที่ดีอยู่แล้ว

$$
\theta_{t+1} = \theta_t - \eta \nabla_\theta \mathcal{L}(\theta_t)
$$

- $\theta$ = พารามิเตอร์ทั้งหมด (Qwen3.6-35B-A3B มี 35 พันล้านตัว)
- $\eta$ = learning rate
- $\mathcal{L}$ = loss เฉลี่ยของ token ในคำตอบ (JSON) ที่โมเดลทำนายผิด

ใน SFT (supervised fine-tuning) ของเรา `completion_only_loss=True` หมายความว่า loss คิดเฉพาะ token ฝั่ง assistant (JSON) ไม่คิด token ของ prompt และภาพ เพราะเราไม่ได้อยากให้โมเดลเรียน "ทำนาย prompt" [22]

🎨 **ภาพที่จะวาดใน HTML:** ภูมิทัศน์ loss (contour 2 มิติ) มีจุด "สุ่ม" อยู่ไกลจากหุบเขา และจุด "pretrained" อยู่ในหุบเขาที่กว้าง ผู้เรียนเลือกจุดเริ่มแล้วกด "เทรน" เห็นลูกศร gradient descent เดิน จากจุดสุ่มต้องเดินหลายร้อยก้าวและอาจตกหุบเขาผิด จากจุด pretrained เดินไม่กี่ก้าวถึงก้นหุบเขาใหม่ (งานของเรา) สไลเดอร์ learning rate ใหญ่เกินจะทำให้กระโดดออกจากหุบเขาที่ดี

---

## 8.2 Full fine-tune ต้องใช้ VRAM เท่าไหร่ (และทำไม)

ไฟล์โมเดล 8B ใน bf16 มีขนาด $8 \times 10^9 \times 2\ \text{bytes} = 16$ GB ทำไมเทรนถึงต้องใช้มากกว่านั้นถึง 8 เท่า

เพราะตอนเทรนด้วย Adam (optimizer มาตรฐาน) ต้องเก็บของ 4 อย่างต่อพารามิเตอร์ 1 ตัว [12]:

| สิ่งที่เก็บ | ความละเอียด | bytes/param | ทำไมต้องมี |
|---|---|---|---|
| น้ำหนัก (สำเนาทำงาน) | bf16 | 2 | ใช้ forward/backward |
| น้ำหนัก (master copy) | fp32 | 4 | อัปเดตค่าเล็ก ๆ ได้แม่น bf16 ปัดทิ้ง |
| gradient | bf16 หรือ fp32 | 2-4 | ทิศทางที่ต้องเดิน |
| Adam momentum $m$ | fp32 | 4 | ค่าเฉลี่ยเคลื่อนที่ของ gradient |
| Adam variance $v$ | fp32 | 4 | ค่าเฉลี่ยเคลื่อนที่ของ gradient² |
| **รวม** | | **16-18** | |

$$
\text{VRAM}_{\text{full FT}} \approx 16\ \text{bytes} \times 8 \times 10^9 = 128\ \text{GB}
$$

และนี่ยังไม่รวม activation (ผลลัพธ์กลางทุกชั้นที่ต้องเก็บไว้คำนวณ backward) ซึ่งโตตามความยาว sequence เรามี sequence ยาว 24,576-47,104 token activation จึงใหญ่มาก จนต้องเปิด gradient checkpointing (หัวข้อ 8.7)

เทียบกับงานวิศวกร: น้ำหนักคือตัวอาคาร gradient คือแรงที่กระทำ ส่วน Adam states คือ "ประวัติแรง" ที่ต้องจำไว้เพื่อให้เดินนิ่ง (เหมือน damping) ของทั้งหมดนี้ต้องอยู่ในความจำพร้อมกัน

LoRA paper [4] รายงานว่าบน GPT-3 175B LoRA ลดพารามิเตอร์ที่ต้องเทรน 10,000 เท่า และลด VRAM 3 เท่า ตัวเลข 3 เท่า (ไม่ใช่ 10,000 เท่า) เพราะน้ำหนัก base ยังต้องอยู่ใน VRAM และ activation ยังต้องเก็บ สิ่งที่หายไปคือ master copy + gradient + Adam states ของพารามิเตอร์ที่แช่แข็ง

🎨 **ภาพที่จะวาดใน HTML:** แท่งกราฟซ้อน (stacked bar) แสดง VRAM ต่อพารามิเตอร์ แยกสี: น้ำหนัก / master / gradient / Adam m / Adam v / activation สไลเดอร์ "ขนาดโมเดล (B)" 1-70 และสวิตช์ "Full FT / LoRA r=16 / QLoRA 4-bit" เมื่อสลับเป็น LoRA แท่ง master+grad+Adam ของ base หดหายเหลือเส้นบาง ๆ (เฉพาะ adapter) เมื่อสลับเป็น QLoRA แท่งน้ำหนัก base หดจาก 2 เหลือ 0.5 byte เส้นแนวนอนบอกขนาดการ์ด 24 / 48 / 80 / 96 GB

---

## 8.3 PEFT: ประวัติของการ "ไม่แตะโมเดลทั้งก้อน"

Parameter-Efficient Fine-Tuning (PEFT) คือชื่อรวมของวิธีที่เทรนพารามิเตอร์ส่วนน้อยแทนทั้งหมด สามรุ่นก่อน LoRA:

1. **Adapter** (Houlsby และคณะ, 2019) [1] แทรกชั้น bottleneck เล็ก ๆ (ลดมิติแล้วขยายกลับ) ต่อท้ายทุก sublayer ของ Transformer เทรนเฉพาะชั้นแทรก ได้ผลใกล้ full FT บน BERT ด้วยพารามิเตอร์เพิ่มแค่ 3.6% ต่องาน ข้อเสีย: ชั้นแทรกอยู่ในเส้นทาง forward ตลอด inference ช้าลง
2. **Prefix tuning** (Li & Liang, 2021) [2] แช่แข็งโมเดลทั้งหมด แล้วเรียนรู้ "เวกเตอร์นำหน้า" ที่ถูกเติมเข้าไปเป็น key/value ในทุกชั้น attention เหมือน prompt ที่ไม่ใช่คำจริง
3. **Prompt tuning** (Lester และคณะ, 2021) [3] ง่ายกว่านั้นอีก: เรียนรู้แค่ soft prompt ที่ชั้น input ผลคือยิ่งโมเดลใหญ่ยิ่งได้ผลใกล้ full FT

สามวิธีนี้พิสูจน์แนวคิดว่า "ไม่ต้องแตะทั้งก้อน" แต่แต่ละวิธีมีราคา: adapter เพิ่ม latency, prefix/prompt tuning กิน context และทูนยาก LoRA แก้ทั้งสองข้อในคราวเดียว

🎨 **ภาพที่จะวาดใน HTML:** แผนภาพ Transformer block เดียว มีปุ่มเลือก Adapter / Prefix / Prompt / LoRA เมื่อเลือก ส่วนที่ถูกเทรน (สีส้ม) จะเปลี่ยนตำแหน่ง: adapter = กล่องแทรกหลัง attention และ FFN, prefix = แถว K/V เพิ่มด้านซ้าย, prompt = token เพิ่มที่ input, LoRA = กิ่งขนานข้างเมทริกซ์ $W$ พร้อมตัวเลข "latency เพิ่มตอน inference" (adapter: ใช่, LoRA หลัง merge: ไม่)

---

## 8.4 LoRA (Hu และคณะ, 2021): $W' = W + BA$

### 8.4.1 แนวคิด

LoRA [4] ตั้งสมมติฐานว่า "การเปลี่ยนแปลงน้ำหนัก" $\Delta W$ ที่ fine-tune ต้องการ มี rank ต่ำ นั่นคือเขียนเป็นผลคูณของเมทริกซ์ผอม ๆ สองตัวได้

$$
W' = W + \Delta W = W + BA, \qquad W \in \mathbb{R}^{d \times k},\ B \in \mathbb{R}^{d \times r},\ A \in \mathbb{R}^{r \times k},\ r \ll \min(d,k)
$$

- $W$ = น้ำหนักเดิม (แช่แข็ง ไม่มี gradient)
- $A, B$ = เมทริกซ์ใหม่ที่เทรน
- $r$ = rank ยิ่งเล็กยิ่งประหยัด
- ตอนเริ่ม $B = 0$ และ $A$ สุ่ม ดังนั้น $BA = 0$ โมเดลเริ่มจากพฤติกรรมเดิมเป๊ะ (นี่คือเหตุผลที่ `random_state=3407` กำหนดค่าเริ่มของ $A$ และ t05 ระบุว่าต้องเท่ากันทุก fold ถ้าจะเอา adapter มารวมกัน)

ตอน forward: $y = Wx + BAx$ คำนวณ $Ax$ ก่อน (ได้เวกเตอร์ยาว $r$) แล้วค่อยคูณ $B$ ไม่ต้องสร้าง $BA$ เต็ม ๆ

### 8.4.2 ตัวอย่างตัวเลข: $W$ ขนาด $4 \times 4$, $r = 1$

$W$ มี $4 \times 4 = 16$ พารามิเตอร์ ถ้า full FT ต้องเทรน 16 ตัว
LoRA $r=1$: $B$ ขนาด $4 \times 1$ (4 ตัว) และ $A$ ขนาด $1 \times 4$ (4 ตัว) รวม **8 ตัว** ลดลงครึ่งหนึ่ง

ให้ $B = \begin{bmatrix}1\\0\\2\\0\end{bmatrix}$, $A = \begin{bmatrix}0.5 & 0 & 0 & 1\end{bmatrix}$ ดังนั้น

$$
BA = \begin{bmatrix} 0.5 & 0 & 0 & 1 \\ 0 & 0 & 0 & 0 \\ 1 & 0 & 0 & 2 \\ 0 & 0 & 0 & 0 \end{bmatrix}
$$

เมทริกซ์ $4 \times 4$ นี้มี rank 1 (แถวที่ 3 = 2 × แถวที่ 1) ทุกคอลัมน์เป็นตัวคูณของ $B$ นั่นคือข้อจำกัด: LoRA เขียน $\Delta W$ ได้เฉพาะแบบที่ "ทุกแถวเป็นตัวคูณกัน" ถ้า $r=2$ จะได้ผลบวกของสองแบบนั้น ยิ่ง $r$ สูง ยิ่งเขียน $\Delta W$ ได้อิสระขึ้น จนที่ $r = 4$ เขียนได้ทุกแบบ (เท่า full FT) แต่พารามิเตอร์ก็กลับมาเป็น $4 \times 4 + 4 \times 4 = 32$ ซึ่งแพงกว่า full FT เสียอีก

ในโมเดลจริง $d = k = 4096$: $W$ มี 16.8 ล้านตัว LoRA $r = 16$ มี $4096 \times 16 \times 2 = 131{,}072$ ตัว = 0.78% ของเดิม นี่คือที่มาของ "ลดพันเท่า"

```python
import numpy as np
np.random.seed(3407)
d, k, r = 4, 4, 1
W = np.random.randn(d, k)                      # น้ำหนักเดิม (แช่แข็ง)
B = np.array([[1.], [0.], [2.], [0.]])         # d x r
A = np.array([[0.5, 0., 0., 1.]])              # r x k
dW = B @ A
print("BA =\n", dW)
print("rank(BA) =", np.linalg.matrix_rank(dW))
print("params: full =", W.size, "| LoRA =", B.size + A.size)
x = np.array([1., 2., 3., 4.])
print("Wx + BAx =", W @ x + B @ (A @ x))        # คำนวณแบบไม่สร้าง BA เต็ม
print("(W+BA)x  =", (W + dW) @ x)               # ผลเท่ากัน = สิ่งที่ merge ทำ
```

🎨 **ภาพที่จะวาดใน HTML:** เมทริกซ์ $W$ 8×8 เป็น heatmap ทางซ้าย ตรงกลางเป็น $B$ (8×r) และ $A$ (r×8) ทางขวาเป็น $BA$ สไลเดอร์ $r$ จาก 1 ถึง 8 เมื่อขยับ ตัวเลข "พารามิเตอร์ที่เทรน" ($2 \cdot 8 \cdot r$) และ "เทียบ full FT (64)" อัปเดต และ heatmap $BA$ แสดงรูปแบบ rank ต่ำ (ที่ $r=1$ ทุกแถวเป็นเงาของกันและกัน) มีปุ่ม "สุ่ม $\Delta W$ เป้าหมาย" แล้วแสดงว่า $BA$ ที่ rank $r$ ประมาณมันได้ใกล้แค่ไหน (error ลดลงเมื่อ $r$ เพิ่ม)

### 8.4.3 ทำไม rank ต่ำถึงพอ: intrinsic dimension

Aghajanyan และคณะ (2020) [5] ทดลองบังคับให้ fine-tune เดินได้เฉพาะในปริภูมิย่อยสุ่มขนาด $d_{\text{int}}$ มิติ แล้ววัดว่าต้องกี่มิติถึงได้ 90% ของ full FT ผลที่โด่งดังคือ RoBERTa บนงาน MRPC ใช้แค่ **200 พารามิเตอร์** ก็ได้ 90% แล้ว และยิ่งโมเดลใหญ่ intrinsic dimension ยิ่ง **ต่ำลง**

ตีความแบบวิศวกร: โมเดลที่ pretrain มาดีแล้วเหมือนอาคารที่ออกแบบเผื่อ load หลายแบบไว้แล้ว การปรับให้รับ load ใหม่ต้องการ "ขันน็อตไม่กี่ตัว" ไม่ใช่ย้ายเสาทุกต้น LoRA คือการจำกัดให้ขันน็อตได้แค่ $r$ ทิศทาง ซึ่งพอ เพราะทิศทางที่ต้องการมีน้อยอยู่แล้ว

"LoRA Without Regret" (Schulman และคณะ, Thinking Machines, 2025) [11] ยืนยันในสเกลใหม่: บน dataset ขนาดที่ post-training ทั่วไปใช้ LoRA ให้ผลเท่า full FT ถ้าตั้งค่าถูก และเสนอมุมมองว่า adapter มีความจุราว 2 bits ต่อพารามิเตอร์ ถ้า dataset มี "ข้อมูล" มากกว่าความจุนั้น LoRA จะเริ่มแพ้ full FT

### 8.4.4 alpha และ scaling $\alpha / r$

ในโค้ดจริง LoRA ไม่ได้บวก $BA$ ตรง ๆ แต่คูณตัวคูณคงที่ก่อน

$$
W' = W + \frac{\alpha}{r} BA
$$

- $\alpha$ (`lora_alpha`) = ตัวเลขที่เราตั้ง
- $\alpha / r$ = ตัวคูณจริงที่ใช้

ทำไมต้องมี: ถ้าเพิ่ม $r$ แล้ว $BA$ เป็นผลบวกของหลายเทอมมากขึ้น ขนาดของมันจะโตตาม $r$ การหารด้วย $r$ ทำให้ขนาดของ update "ประมาณเท่าเดิม" เมื่อเปลี่ยน $r$ ทำให้ learning rate ที่จูนไว้ยังใช้ได้ [11]

ตัวอย่างค่าที่เราเคยใช้ใน t02:

| r | alpha | $\alpha/r$ | ความหมาย |
|---|---|---|---|
| 32 | 32 | 1.0 | update ถูกใช้เต็มขนาด |
| 64 | 128 | 2.0 | update ถูกขยาย 2 เท่า ก่อนบวกเข้า $W$ |
| 32 | 64 (ไฟล์ t02 ปัจจุบัน) | 2.0 | เท่ากับแถวบนเชิงตัวคูณ แต่ rank ต่ำกว่า |
| 16 | 32 (t05) | 2.0 | อัตรา 2 คงที่ตามที่ท่อของเราเลือก |

สังเกตว่า r=64/alpha=128 กับ r=32/alpha=64 มีตัวคูณเท่ากัน (2.0) ต่างกันแค่ "ความอิสระ" ของ $\Delta W$ ส่วน r=32/alpha=32 มีตัวคูณ 1.0 ซึ่งในทางปฏิบัติคล้ายการลด learning rate ของ adapter ลงครึ่งหนึ่ง เพราะ gradient ที่ไหลเข้า $A, B$ ก็ถูกคูณด้วย $\alpha/r$ เช่นกัน

Raschka [13] จากการทดลองหลายร้อยรอบสรุป heuristic ว่า $\alpha = 2r$ ใช้ได้ดีโดยทั่วไป Unsloth แนะนำ $\alpha = r$ หรือ $2r$ [14] ท่อของเราเลือก 2 คงที่

### 8.4.5 rsLoRA: หารด้วย $\sqrt{r}$ แทน

Kalajdzievski (2023) [6] ชี้ว่าการหารด้วย $r$ ทำให้ที่ $r$ สูง ๆ gradient ของ adapter เล็กลงจนเรียนรู้ช้า (rank สูงกลับไม่ช่วย) และเสนอให้หารด้วย $\sqrt{r}$ แทน (rank-stabilized LoRA) ใน PEFT เปิดด้วย `use_rslora=True` [15] สคริปต์ของเราตั้ง `use_rslora=False` เพราะ $r$ ที่เราใช้ (16-32) ยังต่ำ และเราต้องการคงค่าเท่ากับ t01 เพื่อเทียบกันได้

🎨 **ภาพที่จะวาดใน HTML:** กราฟแกน x = $r$ (1-256, log) แกน y = ตัวคูณ scaling สองเส้น: $\alpha/r$ (LoRA เดิม, ลดลงเรื่อย ๆ) และ $\alpha/\sqrt{r}$ (rsLoRA, ลดช้ากว่า) สไลเดอร์ $\alpha$ ขยับทั้งสองเส้น จุดมาร์กแสดง (32,32), (64,128), (32,64), (16,32) ของโปรเจกต์เราบนเส้น

### 8.4.6 target_modules: แปะ LoRA ที่ไหน

LoRA paper ทดลองเฉพาะ attention (q, v) QLoRA paper [7] พบว่าแปะ **ทุก linear layer** (q, k, v, o ของ attention และ gate, up, down ของ MLP) ให้ผลใกล้ full FT กว่ามาก และ "LoRA Without Regret" ย้ำอีกครั้งว่า attention-only underperform แม้จะเพิ่ม r ให้พารามิเตอร์เท่ากัน โดยเฉพาะ MLP/MoE layers สำคัญที่สุด [11] เหตุผลเชิงสัญชาตญาณ: MLP คือส่วนที่เก็บ "ความรู้" (บทที่ 4) ส่วน attention คือส่วนที่เก็บ "การจัดเส้นทางข้อมูล" งานถอดรายการต้องเปลี่ยนความรู้ (Ø12 ไม่ใช่ DB23) ไม่ใช่แค่เส้นทาง

ในสคริปต์ของเรา Unsloth ทำผ่าน `finetune_attention_modules=True, finetune_mlp_modules=True` ซึ่งแปะครบทั้ง 7 ชื่อ และบน MoE ยังแปะไปทุก expert (256 ตัว) ผลคือ r=32 บน Qwen3.6-35B-A3B มี trainable params ถึง 1.89B กิน 11.3GB (LoRA + grad + optimizer) นี่คือเหตุผลที่ t05 ต้องลด r เหลือ 16 หลัง OOM ที่ 93/95 GB ส่วน router (gate ของ MoE) Unsloth แช่แข็งให้เอง เพราะการทูน router ด้วยข้อมูลน้อยทำให้การเลือก expert เสียสมดุล

### 8.4.7 lora_dropout

dropout สุ่มปิดบางค่าของ input ก่อนเข้า $A$ เพื่อกัน overfit Unsloth ระบุว่างานวิจัยช่วงหลังพบว่า dropout สำหรับการเทรนสั้น ๆ เป็น regularizer ที่ไม่น่าเชื่อถือ และแนะนำ 0 [14] ของเรา `lora_dropout=0` ด้วยเหตุผลที่แข็งกว่านั้น: MoE ParamWrapper ของ Unsloth error จริงถ้าไม่ใช่ 0 (t01)

### 8.4.8 adapter คือไฟล์แยก: merge_and_unload และบั๊ก GGUF

หลังเทรน สิ่งที่ `model.save_pretrained(f"{OUT_DIR}/lora")` เซฟคือ **เฉพาะ $A, B$ ของทุกชั้น** (ไฟล์ `adapter_model.safetensors` ขนาดหลักร้อย MB) ไม่มี $W$ อยู่ในนั้น จะใช้งานต้องมี 2 ทาง:

1. โหลด base + adapter แยกกัน ทุก forward คำนวณ $Wx + \frac{\alpha}{r}B(Ax)$ (ช้ากว่านิดหน่อย)
2. **merge**: คำนวณ $W' = W + \frac{\alpha}{r}BA$ ครั้งเดียว เขียนทับ $W$ แล้วทิ้ง $A, B$ ได้โมเดลปกติที่มีน้ำหนักใหม่ PEFT เรียกว่า `merge_and_unload()` [15]

llama.cpp/GGUF รับโมเดลแบบที่ 2 เท่านั้น ถ้าขั้น merge ถูกข้าม หรือ merge แล้วแต่ไฟล์ที่ถูกแปลงเป็น GGUF คือโฟลเดอร์ base เดิม ผลคือ GGUF = $W$ ล้วน ๆ ทุกไบต์เหมือนโมเดลเปล่า นี่คือบั๊กข้อ 2 ของเรา และมันเงียบสนิท เพราะโมเดลเปล่าก็ตอบ JSON ได้ (แค่แย่กว่า)

วิธีตรวจที่คณิตศาสตร์บอกเรา: เอาน้ำหนักชั้นใดชั้นหนึ่งจาก GGUF ที่ merge แล้ว มาลบกับน้ำหนักชั้นเดียวกันของ base ถ้าผลต่างเป็นศูนย์ทุกตัว = ไม่ได้ merge ถ้าผลต่างมี rank ≤ r = merge แล้ว

```python
import numpy as np
np.random.seed(0)
d, r, alpha = 6, 2, 4
W = np.random.randn(d, d); A = np.random.randn(r, d); B = np.random.randn(d, r)
W_merged = W + (alpha / r) * (B @ A)             # สิ่งที่ merge_and_unload ทำ
W_gguf_bug = W.copy()                             # GGUF ที่ลืม merge
for name, M in [("merged", W_merged), ("bug", W_gguf_bug)]:
    diff = M - W
    print(f"{name:>6}: max|diff| = {np.abs(diff).max():.3f}  rank(diff) = {np.linalg.matrix_rank(diff)}")
```

ผลควรเป็น `merged: max|diff| > 0, rank 2` และ `bug: max|diff| = 0, rank 0` การเทียบ base vs tuned บน val ชุดเดียวกัน (หัวข้อ 8.9) คือเวอร์ชัน "ปลายทาง" ของการตรวจนี้

🎨 **ภาพที่จะวาดใน HTML:** ท่อ export: [base W] + [adapter A,B] → ปุ่ม "merge" → [W'] → ปุ่ม "convert GGUF" → [ไฟล์ .gguf] มีสวิตช์ "ข้าม merge" เมื่อเปิด ลูกศรจาก adapter จะขาด และไฟล์ .gguf จะแสดง "= base 100%" สีแดง ด้านล่างมี heatmap ผลต่าง $W' - W$ ที่เป็นศูนย์ทั้งแผ่นเมื่อข้าม merge

---

## 8.5 QLoRA (Dettmers และคณะ, 2023): base 4-bit + adapter bf16

### 8.5.1 สามกลไก

QLoRA [7] ทำให้ทูนโมเดล 65B บนการ์ด 48GB ใบเดียวได้ ด้วย

1. **NF4 (4-bit NormalFloat)** น้ำหนักโมเดลมีการแจกแจงใกล้ปกติ (ค่าส่วนใหญ่กระจุกใกล้ศูนย์) NF4 วางระดับ quantization 16 ระดับตาม quantile ของการแจกแจงปกติ แทนที่จะแบ่งเท่า ๆ กัน ทำให้ 4 bit เก็บข้อมูลได้ดีกว่า int4 ธรรมดา
2. **Double quantization** ค่า scale ของแต่ละ block (ที่ปกติเก็บเป็น fp32) ถูก quantize อีกชั้น ประหยัดอีก ~0.4 bit/param
3. **Paged optimizer** ใช้ unified memory ของ NVIDIA ย้าย optimizer state ไป RAM ชั่วคราวเมื่อ VRAM พุ่ง (spike) กัน OOM ตอน optimizer step

### 8.5.2 ทำไม 4-bit base + bf16 LoRA เทรนได้

$W$ ถูกเก็บ 4-bit แต่ตอน forward มันถูก de-quantize กลับเป็น bf16 ทีละ block เพื่อคูณกับ $x$ แล้วทิ้ง ส่วน $A, B$ อยู่ใน bf16 เต็ม gradient ไหลผ่าน $W$ (แค่ผ่าน ไม่ได้อัปเดต $W$) ไปถึง $A, B$ ได้ตามปกติ เพราะ $\partial (Wx)/\partial x = W^\top$ ใช้แค่ค่าของ $W$ ไม่ต้องการให้ $W$ ปรับได้

$$
\text{VRAM}_{\text{base}} \approx 0.5\ \text{byte} \times N_{\text{params}} \quad (\text{เทียบ } 2\ \text{byte ใน bf16})
$$

Qwen3-VL-8B: bf16 = 16GB, NF4 ≈ 4-5GB จึงลงการ์ด 24GB ได้พร้อม activation ของ sequence ยาว นี่คือ preset "8B" ใน `train_qwen3vl.py` (`load_in_4bit=True`, repo `unsloth-bnb-4bit`)

### 8.5.3 ข้อแลกเปลี่ยน

- ช้ากว่า เพราะต้อง de-quantize ทุก forward Raschka วัดได้ประหยัด VRAM 33% แต่ช้าลง 39% [13]
- quantization error ของ base ทำให้ผลต่างจาก bf16 LoRA เล็กน้อย (QLoRA paper อ้างว่าใกล้เคียง 16-bit)
- **MoE เป็นข้อยกเว้น**: สคริปต์ t02 (preset 30B-A3B) และ t05 ตั้ง `load_in_4bit=False` เพราะ Unsloth เตือนว่า Qwen3.5/3.6 MoE quantize แล้วคุณภาพตกผิดปกติ และ bitsandbytes โหลด MoE 4-bit พัง ดังนั้น "QLoRA" ในโปรเจกต์นี้ใช้จริงเฉพาะ Qwen3-VL-8B/32B dense; ตัวหลัก (35B-A3B) เป็น bf16 LoRA ที่ต้องเช่าการ์ด ~74-96GB

### 8.5.4 DoRA และ LoRA+ (สั้น ๆ)

- **DoRA** (Liu และคณะ, 2024) [8] แยก $W$ เป็น "ขนาด" (magnitude) กับ "ทิศทาง" (direction) แล้วใช้ LoRA ปรับเฉพาะทิศทาง เทรนขนาดแยก ผลดีกว่า LoRA ที่ r ต่ำ แต่ overhead สูงกว่า PEFT แนะนำ merge ก่อน inference [15]
- **LoRA+** (Hayou และคณะ, 2024) [9] ใช้ learning rate ต่างกันสำหรับ $A$ กับ $B$ (B สูงกว่าหลายเท่า) อ้างว่าเร็วขึ้นถึง 2 เท่าและดีขึ้น 1-2%

ทั้งสองยังไม่ได้ใช้ในรีโป เป็นตัวเลือกสำหรับรอบทดลองเมื่อ pipeline พื้นฐานนิ่งแล้ว

🎨 **ภาพที่จะวาดใน HTML:** histogram ของน้ำหนักชั้นหนึ่ง (การแจกแจงระฆังคว่ำ) มีเส้นแนวตั้ง 16 เส้นแสดงระดับ quantization สวิตช์ int4 (เส้นห่างเท่ากัน) / NF4 (เส้นถี่ตรงกลาง ห่างที่หาง) แสดงตัวเลข "error เฉลี่ย" ที่ NF4 ต่ำกว่า ด้านล่างมีแผนภาพ forward: $W_{4bit}$ → de-quantize → bf16 → คูณ $x$ กับกิ่ง $B(Ax)$ ที่ bf16 ตลอด ลูกศร gradient สีแดงไหลกลับผ่าน $W$ ไปหยุดที่ $A,B$

---

## 8.6 Hyperparameter ของเราทีละตัว

ค่าจริงจาก `train_t05_courser.py` (และ t02 ในวงเล็บเมื่อต่างกัน) พร้อมเหตุผลว่าเป็น "หลักการ" หรือ "แผล"

| ตัวแปร | ค่า t05 | ประเภทเหตุผล | ที่มา |
|---|---|---|---|
| `LR` | 1e-4 | หลักการ | LoRA ใช้ LR สูงกว่า full FT ~10 เท่า [11][14]; full FT ต้องลดเหลือ 5e-6..1e-5 |
| `EPOCHS` | 2 (t01/t02 = 3) | หลักการ + งบ | 2 vs 3 ต่างกัน 1-3% แต่กิน GPU +50% และเสี่ยง overfit; Raschka พบ multi-epoch ทำผลตก [13] |
| `BATCH × GRAD_ACCUM` | 1 × 8 | หลักการ + VRAM | LoRA แพ้ batch ใหญ่ [11]; sequence 47k token ใส่ได้ทีละ 1 |
| `lr_scheduler_type` | cosine | หลักการ | ลด LR แบบนุ่มจนถึงศูนย์ที่ปลาย |
| `warmup_ratio` | 0.05 | หลักการ | 5-10% ของ steps [14] |
| `MAX_LENGTH` | 47,104 (t02 = 24,576) | วัดจริง | gridmaster 4 ภาพ × 7,519 token + prompt + JSON = 44,607 |
| `use_gradient_checkpointing` | "unsloth" | VRAM | activation ยาว 47k ไม่มีทางพอ |
| `finetune_vision_layers` | False | หลักการ + GGUF | ดู 8.6.8 |
| `LORA_R / ALPHA` | 16 / 32 (t02 = 32/64) | แผล OOM | r=32 บน MoE 256 experts = 1.89B trainable |
| `optim` | adamw_8bit (t02 = paged_adamw_8bit) | แผล | paged พัง step 42 (illegal memory access); non-paged ถ้าจะ OOM จะ OOM ที่ step 1 |
| `random_state / seed` | 3407 | reproducibility | init ของ $A$ เท่ากันทุก fold |
| `MAX_PIXELS` | 6912×1024 (t02 = 5120×1024) | วัดจริง + แผล | 7,680 ไม่ย่อภาพหลัก แต่ OOM จริง 2/4 fold |
| `eval_strategy` | "no" (t02 = epoch) | แผล | accelerate upcast logits 21k × 152k × 4B ≈ 13GB ตาย |

### 8.6.1 learning rate 1e-4: ทำไม LoRA ใช้สูงกว่า full FT

ใน full FT gradient เดินบนพารามิเตอร์ทั้ง 35B ที่ "ดีอยู่แล้ว" ก้าวใหญ่ = ทำลายความรู้เดิม (catastrophic forgetting, หัวข้อ 8.10) จึงใช้ 5e-6 ถึง 1e-5

ใน LoRA พารามิเตอร์ที่เดินคือ $A, B$ ที่เริ่มจาก $B=0$ ก้าวใหญ่ไม่ทำลายอะไร เพราะ $W$ ไม่ถูกแตะ และ update จริงยังถูกคูณ $\alpha/r$ อีกชั้น "LoRA Without Regret" วัดว่า optimal LR ของ LoRA สูงกว่า full FT ราว 10 เท่าอย่างสม่ำเสมอ และในช่วงต้นการเทรน optimal LR แทบไม่ขึ้นกับ $r$ (เพราะตัวคูณ $1/r$) [11] Unsloth แนะนำเริ่มที่ 2e-4 [14] ของเรา 1e-4 คือค่าที่ t01 พิสูจน์ว่า converge

### 8.6.2 epochs 2-3

1 epoch = โมเดลเห็นทุกตัวอย่าง 1 รอบ t01 เห็น eval loss ลงต่อเนื่องถึง epoch 3 จึงใช้ 3 แต่ t05 ลดเหลือ 2 ด้วยเหตุผลงบและ overfit ข้อควรระวัง: ค่านี้ผูกกับ dataset เมื่อ dataset โต 1.5-2 เท่า จำนวน step ต่อ epoch ก็โต การใช้ epoch เท่าเดิมคือการเทรน "นานขึ้น" ในหน่วย step

### 8.6.3 batch 1 × grad_accum 8

`per_device_train_batch_size=1` เพราะ sequence 47k token ใส่พร้อมกันหลายตัวไม่ไหว `gradient_accumulation_steps=8` สะสม gradient 8 ตัวอย่างก่อนอัปเดตครั้งเดียว ได้ effective batch 8 ทางคณิตศาสตร์เท่ากับ batch 8 (gradient เฉลี่ย) แต่ใช้ VRAM เท่า batch 1 ข้อสังเกตจาก [11]: LoRA แพ้ full FT เมื่อ batch ใหญ่ ดังนั้น 8 ไม่ใช่ข้อเสีย

### 8.6.4 cosine schedule และ warmup

LR ไม่คงที่: 5% แรกไต่จาก 0 ขึ้น 1e-4 (warmup กัน gradient ช่วงแรกที่ยังมั่ว) จากนั้นลดตามเส้นโค้ง cosine ลงถึง ~0 ที่ step สุดท้าย

$$
\eta(t) = \eta_{\max} \cdot \tfrac{1}{2}\left(1 + \cos\left(\pi \cdot \tfrac{t - t_w}{T - t_w}\right)\right), \quad t \ge t_w
$$

- $t$ = step ปัจจุบัน, $t_w$ = step สิ้นสุด warmup, $T$ = step ทั้งหมด

ตัวอย่าง: T = 321 steps (t03: 854 ตัวอย่าง × 3 epoch / 8) → $t_w = 16$ ที่ step 168 (กึ่งกลาง) LR ≈ 0.5e-4 ที่ step 300 LR ≈ 0.01e-4

```python
import math
T, tw, lr_max = 321, 16, 1e-4
def lr(t):
    if t < tw: return lr_max * t / tw
    return lr_max * 0.5 * (1 + math.cos(math.pi * (t - tw) / (T - tw)))
for t in [0, 8, 16, 80, 168, 250, 300, 320]:
    print(f"step {t:3d}: lr = {lr(t):.2e}")
```

🎨 **ภาพที่จะวาดใน HTML:** กราฟ LR ต่อ step มีสไลเดอร์ warmup_ratio (0-0.2), total steps, และปุ่มเลือก linear/cosine/constant มีเส้นแนวตั้งบอกขอบ epoch เมื่อเปลี่ยนจำนวน epoch หรือ dataset size กราฟยืด/หด และแสดง "LR เฉลี่ยตลอดการเทรน"

### 8.6.5 max_length และการตัดกลาง JSON

`max_seq_length` ต้องส่งทั้งตอน `from_pretrained` และ SFTConfig (default 2048 ของ Unsloth จะตัด sequence "กลาง image token" เงียบ ๆ) ค่าที่เล็กเกินไปคือการโยน label ทิ้ง: t02 เดิมตั้ง 10,240 ทำให้ตัวอย่าง gridmaster ถูกตัดเหลือ 42% ของ JSON โมเดลเรียนรู้ว่า "JSON ไม่ต้องปิด" นี่คือบั๊กที่ loss ดูดีแต่ output ใช้ไม่ได้

### 8.6.6 gradient checkpointing

ปกติ forward เก็บ activation ทุกชั้นไว้เพื่อ backward ความจำโตตาม (ชั้น × sequence × hidden) checkpointing เก็บเฉพาะบางจุด แล้วคำนวณช่วงระหว่างใหม่ตอน backward แลกเวลา ~20-30% กับ VRAM ที่ลดหลายเท่า `"unsloth"` คือเวอร์ชันของ Unsloth ที่ offload ไป CPU บางส่วน

### 8.6.7 random_state 3407

seed คุมการสุ่ม init ของ $A$, ลำดับ shuffle ข้อมูล, dropout ผลจริงสำหรับเรา: ทำให้ fold0/fold1 เริ่มจาก $A$ เดียวกัน เทียบกันได้ และ Raschka รายงานว่า LoRA ให้ผล "สม่ำเสมออย่างน่าทึ่ง" ข้าม seed [13] ดังนั้นความต่างระหว่างรอบมักมาจาก config ไม่ใช่โชค

### 8.6.8 freeze vision tower (finetune_vision_layers=False)

จากบทที่ 7: LoRA แปะเฉพาะ linear layer ใน LLM ViT และ merger ไม่ถูกแตะ

| ข้อดี | ข้อเสีย |
|---|---|
| dataset เล็ก (315-1,100 ตัวอย่าง) ไม่พอสอน ViT ใหม่ เสี่ยงทำ visual feature พัง | ถ้า ViT "มองไม่เห็น" เส้นบาง การทูน LLM แก้ไม่ได้ |
| VRAM ลด (ไม่ต้องเก็บ activation gradient ของ ViT ที่รับ 7,519 token) | อาจเสีย recall ที่ได้จากการปรับ feature ให้เข้ากับแบบก่อสร้าง |
| vision encoder byte-identical กับ base → ใช้ mmproj ทางการตอน export GGUF | notebook ทางการของ Unsloth ตั้ง True เราต่างจากมาตรฐาน |
| เทียบกับ t01 ได้ (ตัวแปรคุม) | |

ตัวแปร env `FINETUNE_VISION=1` มีไว้แล้วสำหรับรอบทดลอง เงื่อนไขที่ควรลอง: เมื่อบั๊กระดับ pipeline (token, merge, decoding) หมดแล้ว และยังเห็นความผิดพลาดแบบ "อ่านตัวเลขผิด" ไม่ใช่ "จัดโครงสร้างผิด"

🎨 **ภาพที่จะวาดใน HTML:** ตารางตัวแปรแบบ interactive: คลิกแต่ละแถวเปิดการ์ดอธิบาย + กราฟย่อย (เช่น คลิก LR เห็นกราฟ loss ที่ LR 1e-5 / 1e-4 / 1e-3 จำลอง: ช้าเกิน / พอดี / แกว่งระเบิด) มีป้ายสีบอกประเภทเหตุผล: เขียว = หลักการ, เหลือง = วัดจริง, แดง = แผลจาก OOM

---

## 8.7 dataset ต้อง "เหมือนตอนใช้จริง": train/inference mismatch

โมเดลเรียนการแจกแจง $p_{\text{train}}(\text{input})$ แล้วถูกใช้กับ $p_{\text{infer}}(\text{input})$ ถ้าสองอย่างต่างกัน เรียกว่า distribution shift และประสิทธิภาพที่วัดบน val (ซึ่งมาจาก $p_{\text{train}}$) จะไม่บอกอะไรเกี่ยวกับตอนใช้จริง

บั๊ก 14 เท่าของเราคือ shift ที่ "เราสร้างเอง": เทรนบนภาพ 266 token ใช้จริง 3,796 token ในสายตาโมเดล ภาพตอนใช้จริงคือ input ที่ยาวกว่า 14 เท่า ตำแหน่ง M-RoPE ของ visual token กว้างกว่าที่เคยเห็น รายละเอียดที่ LLM ไม่เคยถูกสอนให้ใช้ ผลคือโมเดลที่ val loss สวยแต่ recall จริงต่ำ

หลักการเดียวกันใช้กับทุกมิติของ input ไม่ใช่แค่ resolution:

- **prompt** ตอนเทรนกับตอนใช้ต้องเป็นข้อความเดียวกัน (t05 pass2.4 เทรน 2 โหมด มี/ไม่มี hint เพราะตอนใช้จริงมีทั้งสองแบบ)
- **chat template / enable_thinking** t01 เจอว่าตอนเทรนไม่มี `<think>` แต่ตอน inference template ใส่ให้ โมเดลเลยเขียน chain-of-thought จนหมด token ก่อนถึง JSON
- **ภาพมาร์ค** pass3 เทรนบนภาพที่ CV วาดเลขมาร์คแล้ว เพราะ production ป้อนภาพแบบนั้น ไม่ใช่ภาพเปล่า
- **decoding** เทรนไม่เกี่ยวกับ decoding แต่ถ้า eval ใช้ greedy แล้ววนซ้ำ (บั๊ก 4) ตัวเลขที่วัดก็ไม่สะท้อนโมเดล

🎨 **ภาพที่จะวาดใน HTML:** histogram สองอันซ้อนกัน แกน x = visual token ต่อภาพ (log) สีฟ้า = ตอนเทรน สีแดง = ตอนใช้จริง สไลเดอร์ "max_pixels ตอนเทรน" และ "ตอนใช้จริง" แยกกัน เมื่อสองยอดซ้อนกัน มิเตอร์ "distribution overlap" เขียว เมื่อห่างกัน 14 เท่า มิเตอร์แดงและข้อความ "โมเดลไม่เคยเห็น input แบบนี้"

---

## 8.8 dataset ขนาดเท่าไหร่ถึงพอ

LIMA [10] บอกว่า 1,000 ตัวอย่างพอ **สำหรับการสอนสไตล์** (alignment) ที่ความรู้มีอยู่แล้ว งานเราต่างออกไปสองข้อ:

1. ความรู้ "แบบโครงสร้าง คสล. ไทย → JSON ตามหลักถอดปริมาณ" แทบไม่มีใน pretrain โมเดลต้องเรียนความรู้ใหม่ ไม่ใช่แค่สไตล์
2. output ยาวและมีโครงสร้างละเอียด (JSON หลายพัน token) แต่ละตัวอย่างมี "bits" ของข้อมูลเยอะ

มุมมองความจุจาก [11]: LoRA เก็บได้ราว 2 bits/param ถ้า r=16 บน Qwen3.6-35B-A3B มี trainable ~0.95B params (ครึ่งของ 1.89B ที่ r=32) ความจุ ≈ 1.9 Gbit ซึ่งมากกว่าข้อมูลใน 1,000 ตัวอย่าง × JSON 3k token มาก ดังนั้นความจุ adapter ไม่ใช่คอขวด คอขวดคือ (ก) จำนวนตัวอย่างต่อ subtask (t02 เห็น beam-plan แค่ ~13 ตัวอย่าง recall 11%) และ (ข) ความสม่ำเสมอของ label

~1,000 ตัวอย่างต่อ fold ของ t05 อยู่ในโซน "พอสำหรับสไตล์ ยังน้อยสำหรับ subtask ที่หายาก" การแยก pass (t03/t05) คือการทำให้แต่ละ subtask มีตัวอย่างพอ และ op04 (ลดหน้าต่อบ้าน 107 → 38) คือการเอางบ label ไปเพิ่ม "จำนวนบ้าน" แทน "จำนวนหน้า" เพื่อกระจาย distribution

🎨 **ภาพที่จะวาดใน HTML:** กราฟ learning curve จำลอง แกน x = จำนวนตัวอย่าง (log 10-10,000) แกน y = recall สองเส้น: งานสไตล์ (อิ่มตัวเร็วที่ ~1k) และงานความรู้ใหม่ (ยังไต่อยู่ที่ 1k) มีจุดมาร์ก t02 (315), t03 (854), t05 (~1,000/fold) และแถบแยกสีตาม subtask แสดงว่า beam-plan มีแค่ 13 ตัวอย่างใน t02

---

## 8.9 Unsloth และ HF stack

**Hugging Face stack** ที่ทุกอย่างวางอยู่บน:
- `transformers` โหลดโมเดล/processor (t05 ต้องใช้ v5 สำหรับ Qwen3.6)
- `peft` LoRA/QLoRA/rsLoRA/DoRA, `merge_and_unload` [15]
- `trl` `SFTTrainer` และ `SFTConfig` (completion_only_loss, max_length, packing)
- `bitsandbytes` NF4 4-bit และ 8-bit optimizer (`adamw_8bit` = Adam states 2 bytes/param แทน 8 [12])
- `accelerate` mixed precision / device placement (และเป็นตัวที่ upcast logits จน eval OOM ใน t03)

**Unsloth** ห่อ stack นี้ด้วย `FastVisionModel` และอ้างว่าเทรนเร็ว 2 เท่า ใช้ VRAM น้อยลง 70% โดยไม่เสียความแม่นยำ [16] กลไกหลักที่ README ระบุ: kernel ที่เขียนใน Triton (ภาษาเขียน GPU kernel ของ OpenAI) สำหรับ RoPE, MLP และ loss แบบ fused/chunked (ไม่ materialize logits ทั้ง vocab × sequence) บวก padding-free และ packing [17] ผลจริงกับเราคือ ตอนเทรน loss ถูกคำนวณแบบ chunk จึงไม่ OOM แต่พอเปิด eval ผ่าน accelerate ที่ไม่ใช้ kernel นี้ logits 21k × 152k × 4 bytes ≈ 13GB ก็ตาย นี่คือเหตุผลที่ท่อของเราปิด eval ตอนเทรน แล้ววัดด้วย generate-eval แยก

ข้อควรระวัง: ความสะดวกของ Unsloth มาพร้อม default ที่มองไม่เห็น (`resize="min"`, `max_seq_length=2048`, pad_token `<|vision_pad|>`) ทุกตัวเคยกัดเรามาแล้ว บั๊กข้อ 5 ("ค่าที่ไม่ได้ตั้งพลิกผลทั้งวัน") คือคำเตือนถาวรของหัวข้อนี้

🎨 **ภาพที่จะวาดใน HTML:** แผนภาพชั้น: ล่างสุด CUDA/Triton kernels, ถัดมา torch, bitsandbytes, transformers, peft, trl, accelerate, บนสุด Unsloth FastVisionModel และ train_t05.py ของเรา คลิกแต่ละชั้นแสดง "ค่า default ที่ซ่อนอยู่" ที่เคยกัดเรา พร้อมบรรทัดในสคริปต์ที่ override

---

## 8.10 อ่าน loss และพิสูจน์ว่าทูน "ติด"

### 8.10.1 loss คืออะไรตอนทูน

train loss = cross-entropy เฉลี่ยต่อ token ของ JSON ที่โมเดลทำนาย $e^{\text{loss}}$ คือ perplexity t03 จบที่ train_loss 0.2249 → perplexity ≈ 1.25 แปลว่าเฉลี่ยแล้วโมเดล "ลังเลระหว่าง 1.25 ตัวเลือก" ต่อ token ซึ่งต่ำมาก เพราะ JSON ส่วนใหญ่คือโครงสร้างที่เดาได้ (วงเล็บ ชื่อ key) token ที่ยาก (เลขเหล็ก จำนวนคาน) ถูกเฉลี่ยจนมองไม่เห็น

นี่คือข้อจำกัดสำคัญ: **loss ต่ำไม่ได้แปลว่าอ่านเลขเหล็กถูก** สคริปต์ t02 เขียนไว้ตรง ๆ ว่า "eval loss อย่างเดียวบอกไม่ได้ว่าอ่านเลขเหล็กถูกไหม" จึงต้อง generate จริงแล้ววัด element recall

### 8.10.2 รูปร่าง loss curve ที่ควรเห็น

- ช่วง warmup ลงเร็ว (โมเดลเรียน format JSON)
- จากนั้นลงช้า ๆ (เรียนเนื้อหา)
- ถ้า train loss ลงแต่ val loss ขึ้น = overfit (ท่องข้อสอบเก่า) ลด epoch
- ถ้าทั้งคู่ไม่ลงเลย = LR ต่ำเกิน, label ผิด, หรือ input ถูกตัด/ย่อจนไม่มีข้อมูลให้เรียน (บั๊ก 1 จะโชว์เป็น loss ที่ยัง "ลง" ได้ เพราะโมเดลเรียนเดา JSON จากภาพเบลอ)
- loss กระโดดเป็น NaN = LR สูงเกิน, fp16 overflow (เราใช้ bf16), หรือ pad_token ผิด (issue `<|vision_pad|>` ที่ batch > 1)

### 8.10.3 การพิสูจน์ที่เราเคยละเลย: base vs tuned บนชุดเดียวกัน

หลักฐานว่าทูน "ติด" มีแบบเดียว: รัน **base model** และ **tuned model** บน val ชุดเดียวกัน decoding config เดียวกัน วัด metric เดียวกัน (element recall) แล้วดูส่วนต่าง ถ้าส่วนต่างเป็นศูนย์ มีสามความเป็นไปได้: adapter ไม่ถูกโหลด/merge (บั๊ก 2), เทรนบน input ที่ไม่มีข้อมูล (บั๊ก 1), หรือ decoding พังทั้งคู่ (บั๊ก 4) และทั้งสามอย่างเคยเกิดกับเราจริง

รอบที่เชื่อว่า "ทูนแล้ว 90%" ขาดการเทียบนี้ จึงไม่มีทางรู้ว่ากำลังวัดโมเดลเปล่า การเทียบ base vs tuned จึงเป็น "การทดสอบยอมรับ" (acceptance test) ของทุกรอบทูน ไม่ใช่ตัวเลือก

```python
# โครงของการพิสูจน์ (pseudo-code ที่ใช้ได้กับ eval_fields.py)
import json
def recall(pred, gt):                     # element recall แบบง่าย: ชื่อ element ที่ GT มี และ pred เจอ
    g = {e["name"] for e in gt["elements"]}; p = {e["name"] for e in pred["elements"]}
    return len(g & p) / max(1, len(g))
gt   = {"elements": [{"name": n} for n in ["B1","B2","B2","C1","F1"]]}
base = {"elements": [{"name": n} for n in ["B1","C1"]]}
tune = {"elements": [{"name": n} for n in ["B1","B2","C1","F1"]]}
print("base recall =", recall(base, gt), "| tuned recall =", recall(tune, gt))
print("ส่วนต่าง =", recall(tune, gt) - recall(base, gt), "→ ถ้าเป็น 0 ให้สงสัย merge/token/decoding ก่อนสงสัยโมเดล")
```

🎨 **ภาพที่จะวาดใน HTML:** กราฟ loss curve จำลอง มีปุ่มสถานการณ์: ปกติ / overfit / LR สูงเกิน (NaN) / ภาพถูกย่อ (loss ลงแต่ต่ำกว่า) ด้านขวาเป็นแท่งกราฟ recall คู่ base vs tuned ต่อ subtask เมื่อเลือกสถานการณ์ "ลืม merge" แท่ง tuned จะเท่ากับ base ทุกแท่งพร้อมข้อความเตือน

---

## 8.11 catastrophic forgetting และวิธีกัน

เมื่อทูนงานใหม่ โมเดลอาจสูญเสียความสามารถเดิม Luo และคณะ (2023) [18] ศึกษาเชิงประจักษ์บนโมเดล 1B-7B ระหว่าง continual instruction tuning พบว่า forgetting เกิดจริงทั่วไป และที่น่าแปลกคือโมเดลใหญ่ในช่วงนี้ลืมมากกว่า (เพราะมีมากกว่าให้ลืม)

สำหรับเรา ความสามารถที่ห้ามลืม: อ่านภาษาไทย, เขียน JSON ถูกไวยากรณ์, นับเลข, ตอบเป็นภาษาที่ถูกต้อง (อาการ "หลุดภาษาจีน" ในบั๊ก 4 อาจมีส่วนจาก forgetting ผสมกับ greedy decoding)

วิธีกันที่ใช้กันทั่วไปและอยู่ในมือเรา:

| วิธี | กลไก | สถานะในรีโป |
|---|---|---|
| LoRA เอง | $W$ ไม่ถูกแตะ ลบ adapter ก็กลับเป็นเดิม; ความจุจำกัด = ลืมได้จำกัด | ใช้อยู่ |
| lower LR | ก้าวเล็ก = ไปไม่ไกลจากจุดเดิม | 1e-4 (ไม่ใช่ 2e-4) |
| fewer epochs | เห็นข้อมูลน้อยรอบ = ท่องน้อยลง | 3 → 2 ใน t05 |
| mix general data | ปน instruction ทั่วไป 5-20% ให้โมเดล "ทบทวน" ของเดิม | ยังไม่ทำ (ตัวเลือกรอบหน้า) |
| freeze ส่วนที่ไม่เกี่ยว | ViT/merger/router แช่แข็ง | ใช้อยู่ |
| วัด general benchmark ก่อน-หลัง | จับ forgetting ให้เห็น | ยังไม่ทำ |

🎨 **ภาพที่จะวาดใน HTML:** radar chart ความสามารถ 5 แกน (ไทย, JSON, นับ, อ่านแบบ, ภาษาถูก) เส้น base กับเส้น tuned สไลเดอร์ LR, epochs, สัดส่วน general data เมื่อดัน LR/epochs สูง แกน "อ่านแบบ" โตแต่แกนอื่นหดจำลอง เมื่อเพิ่ม general data แกนอื่นกลับมา

---

## 8.12 การเลือก base model

| เกณฑ์ | คำถาม | ประสบการณ์เรา |
|---|---|---|
| ขนาด vs VRAM | bf16 LoRA ต้อง ~2 bytes × params + activation; QLoRA ~0.5 bytes | 8B 4-bit ลง 24GB; 35B-A3B bf16 ต้อง 74-96GB เช่า |
| ความสามารถ vision | รับ resolution สูงได้ไหม, patch/merge เท่าไหร่, document benchmark | Qwen3-VL/3.6 ใช้ 32 px/token, InternVL3 tiling 448 |
| MoE vs dense | MoE: params รวมเยอะ (ความรู้) แต่ active น้อย (inference เร็ว); ราคาคือ VRAM ต้องเก็บทุก expert, LoRA แปะทุก expert → trainable บวม, 4-bit ไม่รองรับ, dropout ต้อง 0, router ห้ามทูน | t01/t05 (35B-A3B MoE) recall สูงสุด; t02 8B dense ลงการ์ดเล็กได้ |
| ecosystem | Unsloth รองรับไหม, GGUF/llama.cpp แปลงได้ไหม, vLLM + xgrammar ใช้ได้ไหม | Qwen ครบทุกข้อ; InternVL3 พังที่ config |
| การเทียบข้ามรอบ | เปลี่ยน base = เปลี่ยนตัวแปรทุกตัว ต้องคุมที่เหลือให้เท่า | t02 เทียบ t01 ด้วยการ mirror ทุกค่า |

กฎง่าย ๆ ที่ได้จาก 5 รอบ: **เปลี่ยน base model ครั้งละหนึ่งตัวแปร และห้ามเปลี่ยนก่อนพิสูจน์ว่า pipeline (token/merge/decoding) ไม่มีบั๊ก** ไม่งั้นจะสรุปว่า "โมเดล B แย่กว่า A" ทั้งที่จริงคือ collator ย่อภาพ

🎨 **ภาพที่จะวาดใน HTML:** ตารางเลือกโมเดล interactive: เลือกการ์ด (24/48/80/96 GB), เลือกโหมด (bf16 LoRA / QLoRA), เลือกโมเดล (8B dense, 32B dense, 30B-A3B MoE, 35B-A3B MoE) ระบบคำนวณ VRAM ประมาณ (weights + LoRA + activation ที่ MAX_LENGTH ที่กรอก) และขึ้นสีเขียว/แดง พร้อมหมายเหตุ "MoE: 4-bit ไม่รองรับ"

---

## 8.13 เชื่อมกับงานของเรา

| แนวคิดในบทนี้ | ปรากฏที่ไหน | บั๊ก/เหตุการณ์ที่อธิบายได้ |
|---|---|---|
| adapter = ไฟล์แยก, ต้อง merge $W + \frac{\alpha}{r}BA$ | `model.save_pretrained(f"{OUT_DIR}/lora")` แล้วขั้น export GGUF แยกต่างหาก | บั๊ก 2 (adapter ไม่ถูก merge → วัดโมเดลเปล่า) |
| LoRA ใช้ LR ~10× full FT | `LR = 1e-4` + คอมเมนต์ "ถ้า full FT ต้องลดเหลือ 5e-6..1e-5" ใน t02 | หลักการ [11] |
| แปะทุก linear รวม MLP/MoE | `finetune_attention_modules=True, finetune_mlp_modules=True` | r=32 → 1.89B trainable → OOM → r=16 |
| $\alpha/r$ | t02: 32/64, t05: 16/32 (อัตรา 2) | ตัวคูณเท่ากันข้ามรอบ เทียบกันได้ |
| lora_dropout=0 | บังคับบน MoE | error จริงใน t01 |
| QLoRA (NF4) | preset 8B/32B ของ t02 `load_in_4bit=True`; MoE ห้าม | ทำไมตัวหลักต้องเช่าการ์ด 96GB |
| paged optimizer | t02 `paged_adamw_8bit` → t05 `adamw_8bit` | paged พัง step 42 (illegal memory access) |
| freeze vision | `finetune_vision_layers=False` | ใช้ mmproj ทางการได้; ข้อจำกัดเมื่อ ViT มองไม่เห็น |
| distribution shift | `resize="max"` + assert `_tok > 1000` | บั๊ก 1 (14 เท่า), t04 (tile เดียว) |
| max_length ตัด label | 10,240 → 24,576 → 47,104 | gridmaster เหลือ 42% |
| base vs tuned | `eval_fields.py --adapter` | การพิสูจน์ที่รอบ "90%" ละเลย |
| decoding ≠ training | greedy วน B2, `enable_thinking=False`, xgrammar | บั๊ก 4 |
| default ที่มองไม่เห็น | `max_seq_length` 2048, `resize="min"`, `completion_only_loss` เขียนไว้ชัด | บั๊ก 5 |

---

## 8.14 ระดับนักวิจัย: คำถามที่ยังเปิดอยู่

1. **LoRA เท่า full FT จริงไหม และเมื่อไหร่ไม่เท่า:** LoRA Without Regret [11] ให้ขอบเขต (dataset ไม่เกินความจุ ~2 bits/param, ไม่ใช้ batch ใหญ่, แปะทุกชั้น) แต่ยังไม่มีคำตอบสำหรับงานที่ต้อง "เรียนความรู้ใหม่จำนวนมาก" อย่างสัญลักษณ์แบบก่อสร้างไทย ซึ่งอาจต้อง full FT บางชั้นหรือ continued pretraining
2. **rank และ scaling บน MoE:** rsLoRA [6] และ LoRA+ [9] ทดลองบน dense เป็นหลัก การแปะ LoRA ทุก expert (256 ตัว) ที่ส่วนใหญ่แทบไม่ถูกเรียกในโดเมนแคบ ๆ ของเรา เป็นการใช้พารามิเตอร์ที่สิ้นเปลืองหรือไม่ และควรแปะเฉพาะ expert ที่ router เลือกบ่อยหรือไม่ ยังเป็นคำถามเปิด
3. **การทูน ViT ด้วยข้อมูลน้อย:** ควร freeze หรือไม่ ไม่มีคำตอบทั่วไป งานสาย document (Qwen2.5-VL [19]) ทูน ViT ด้วยข้อมูลมหาศาล แต่กรณี 1,000 ตัวอย่างไม่มีใครรายงานผลอย่างเป็นระบบ
4. **quantization หลังทูน:** QLoRA quantize base ก่อนทูน (ทูนชดเชย error ได้) แต่เรา quantize Q4_K_M **หลัง** ทูน (บั๊ก 3) ซึ่ง error ไม่ถูกชดเชย ผลกระทบต่อ adapter ที่ merge แล้วเป็นเรื่องที่ควรวัดทุกครั้ง ไม่มีทฤษฎีรับประกัน
5. **สัญญาณของ forgetting ในโมเดล vision:** งานของ Luo [18] วัดบนข้อความ ยังไม่มีมาตรฐานว่า VLM ที่ทูนอ่านแบบแล้ว "ลืม" การมองภาพทั่วไปไปแค่ไหน และมันสำคัญกับเราหรือไม่

---

## 8.15 แบบฝึกหัด

**ข้อ 1 (คำนวณ):** Qwen3-VL-32B dense, full fine-tune ด้วย AdamW mixed precision ต้อง VRAM เท่าไหร่ (ไม่รวม activation) และถ้าเป็น QLoRA r=16 บน linear layer ที่รวมกันมี 30B params ใน 64 ชั้น สมมติทุก linear เป็น 5120×5120 โดยประมาณ ประมาณพารามิเตอร์ที่เทรน

<details><summary>เฉลย</summary>
Full FT: 32B × 16-18 bytes ≈ 512-576 GB (ต้องหลายการ์ด) · QLoRA: base 32B × 0.5 byte ≈ 16GB + adapter: linear 5120×5120 มี 26.2M params/ตัว → 30B/26.2M ≈ 1,145 เมทริกซ์ × (5120×16×2 = 163,840) ≈ 188M params × ~16 bytes ≈ 3GB รวมราว 19GB + activation จึงลง 24GB ได้แบบหวุดหวิดที่ sequence ไม่ยาวมาก
</details>

**ข้อ 2 (คิด):** r=32 alpha=32 กับ r=16 alpha=32 ต่างกันอย่างไรทั้งในเชิง "ความอิสระ" และ "ตัวคูณ" ถ้าอยากเทียบสองค่านี้ให้ยุติธรรมควรปรับ LR ไหม

<details><summary>เฉลย</summary>
r=32/α=32: ตัวคูณ 1.0, rank 32 · r=16/α=32: ตัวคูณ 2.0, rank 16 ต่างทั้งสองมิติพร้อมกัน ไม่ยุติธรรม ควรคง α/r เท่ากัน (เช่น 32/64 vs 16/32) แล้วเทียบเฉพาะ rank หรือใช้ rsLoRA ที่ตัวคูณขึ้นกับ √r ตาม [11] ในช่วงต้น optimal LR ไม่ขึ้นกับ r มากนักถ้าใช้ 1/r scaling จึงไม่ต้องปรับ LR
</details>

**ข้อ 3 (รันโค้ด):** ต่อยอดโค้ดใน 8.4.8: สร้าง $W$ ขนาด 64×64, adapter r=4, merge แล้ว quantize $W'$ เป็น 4-bit แบบง่าย (ปัดเป็น 16 ระดับเท่า ๆ กันในช่วง min-max) แล้ววัด $\|W'_{q} - W'\|$ เทียบกับ $\|\frac{\alpha}{r}BA\|$ ขนาดของ adapter เทียบกับ error ของ quantization เป็นเท่าไหร่

<details><summary>เฉลย</summary>
โค้ดแนว: `levels = np.linspace(Wm.min(), Wm.max(), 16); Wq = levels[np.abs(Wm[...,None]-levels).argmin(-1)]` ผลทั่วไป: quantization error (Frobenius) มักมีขนาดเทียบเท่าหรือใหญ่กว่า adapter update เมื่อ r เล็กและ α/r = 1 นี่คือทำไม Q4_K_M หลังทูน (บั๊ก 3) อาจ "กลบ" สิ่งที่ทูนไป ต้องวัดซ้ำเสมอ
</details>

**ข้อ 4 (คิด):** t05 ปิด eval ระหว่างเทรน ให้เสนอวิธีตรวจ overfit โดยไม่เปิด eval_strategy

<details><summary>เฉลย</summary>
เซฟ checkpoint ทุก 25 step (มีอยู่แล้ว) แล้วรัน generate-eval แยกบน val subset เล็ก (เช่น 20 ตัวอย่าง) กับ checkpoint หลายจุด พล็อต recall ต่อ step ถ้า recall ตกหลัง epoch 1-2 = overfit เลือก checkpoint ที่ดีที่สุดแทน checkpoint สุดท้าย
</details>

**ข้อ 5 (คิด):** ออกแบบ "acceptance test" 3 ข้อที่ต้องผ่านก่อนประกาศว่ารอบทูนสำเร็จ

<details><summary>เฉลย</summary>
(1) batch แรก: visual token/ภาพ ≥ 1,000 และ seq ยาวสุด < MAX_LENGTH (2) หลัง merge: ผลต่าง $W' - W$ ของอย่างน้อย 1 ชั้นไม่เป็นศูนย์ (หรือ hash ไฟล์ GGUF ต่างจาก base) (3) base vs tuned บน val เดียวกัน decoding เดียวกัน: recall ของ tuned สูงกว่าอย่างมีนัย และ JSON valid rate ไม่ต่ำกว่า base
</details>

---

## สรุปบทนี้ใน 5 บรรทัด

1. fine-tune = gradient descent ต่อจากจุดที่ pretrain ทิ้งไว้ ด้วยข้อมูลน้อยและ LR เล็ก ความรู้ส่วนใหญ่มาจาก pretrain (LIMA) เราสอนรูปแบบและความรู้เฉพาะทางเพิ่ม
2. full FT ต้อง ~16-18 bytes/param (น้ำหนัก + master + gradient + Adam m,v) → 8B = 128GB; LoRA แช่แข็ง $W$ เทรนเฉพาะ $BA$ rank ต่ำ ลด trainable เป็นพันเท่าและ VRAM ราว 3 เท่า; QLoRA เก็บ base เป็น NF4 อีก 4 เท่า (แต่ MoE ของเราใช้ไม่ได้)
3. $W' = W + \frac{\alpha}{r}BA$: r คือความอิสระ, $\alpha/r$ คือตัวคูณ (เราใช้ 2), แปะทุก linear รวม MLP/MoE, dropout 0, LR ~10× full FT, adapter เป็นไฟล์แยกที่ต้อง merge ก่อน GGUF (บั๊ก 2)
4. ค่าใน train script ของเราแบ่งเป็นหลักการ (lr, cosine, warmup, batch 1×8, freeze vision), วัดจริง (MAX_LENGTH, MAX_PIXELS) และแผลจาก OOM (r 32→16, paged→non-paged, eval ปิด) ต้องรู้ว่าอันไหนเป็นอันไหนก่อนเปลี่ยน
5. loss ต่ำไม่พิสูจน์อะไร การพิสูจน์ว่าทูนติดคือ base vs tuned บน val เดียวกัน decoding เดียวกัน และการเทรนต้องเห็น input แบบเดียวกับตอนใช้จริง (distribution shift 14 เท่า = บั๊ก 1)

---

## ที่มาและอ่านต่อ

| # | แหล่ง | ประเภท | ทำไมควรอ่าน | URL |
|---|---|---|---|---|
| 1 | Houlsby et al. (2019) "Parameter-Efficient Transfer Learning for NLP" | paper | adapter รุ่นแรก 3.6% params/งาน | https://arxiv.org/abs/1902.00751 |
| 2 | Li & Liang (2021) "Prefix-Tuning: Optimizing Continuous Prompts for Generation" | paper | เทรนเวกเตอร์นำหน้า โมเดลแช่แข็ง | https://arxiv.org/abs/2101.00190 |
| 3 | Lester et al. (2021) "The Power of Scale for Parameter-Efficient Prompt Tuning" | paper | soft prompt ยิ่งโมเดลใหญ่ยิ่งพอ | https://arxiv.org/abs/2104.08691 |
| 4 | Hu et al. (2021) "LoRA: Low-Rank Adaptation of Large Language Models" | paper | ต้นฉบับ $W + BA$, ลด params 10,000×, VRAM 3× | https://arxiv.org/abs/2106.09685 |
| 5 | Aghajanyan et al. (2020) "Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning" | paper | ทำไม rank ต่ำพอ (200 params ได้ 90%) | https://arxiv.org/abs/2012.13255 |
| 6 | Kalajdzievski (2023) "A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA" (rsLoRA) | paper | หารด้วย √r แทน r | https://arxiv.org/abs/2312.03732 |
| 7 | Dettmers et al. (2023) "QLoRA: Efficient Finetuning of Quantized LLMs" | paper | NF4, double quantization, paged optimizer, แปะทุก linear | https://arxiv.org/abs/2305.14314 |
| 8 | Liu et al. (2024) "DoRA: Weight-Decomposed Low-Rank Adaptation" | paper | แยก magnitude/direction | https://arxiv.org/abs/2402.09353 |
| 9 | Hayou et al. (2024) "LoRA+: Efficient Low Rank Adaptation of Large Models" | paper | LR ต่างกันสำหรับ A และ B | https://arxiv.org/abs/2402.12354 |
| 10 | Zhou et al. (2023) "LIMA: Less Is More for Alignment" | paper | 1,000 ตัวอย่างพอสำหรับสไตล์ | https://arxiv.org/abs/2305.11206 |
| 11 | Schulman et al. / Thinking Machines (2025) "LoRA Without Regret" | blog (research) | LR 10×, แปะทุกชั้นรวม MoE, batch เล็ก, ความจุ 2 bits/param | https://thinkingmachines.ai/blog/lora/ |
| 12 | Hugging Face transformers docs "GPU memory usage / model memory anatomy" | docs | bytes/param ของ weights, Adam, gradient, activation | https://huggingface.co/docs/transformers/model_memory_anatomy |
| 13 | Sebastian Raschka (2023) "Practical Tips for Finetuning LLMs Using LoRA" | blog | α=2r, QLoRA -33% VRAM +39% เวลา, multi-epoch ทำผลตก, แปะทุกชั้น | https://magazine.sebastianraschka.com/p/practical-tips-for-finetuning-llms |
| 14 | Unsloth docs "LoRA Hyperparameters Guide" | docs | ค่าแนะนำ LR/epochs/r/α/dropout/target_modules/warmup | https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide |
| 15 | Hugging Face PEFT docs "LoRA" | docs | merge_and_unload, use_rslora, use_dora | https://huggingface.co/docs/peft/main/en/developer_guides/lora |
| 16 | Unsloth docs (หน้าแรก) | docs | อ้าง 2× faster, 70% less VRAM | https://unsloth.ai/docs |
| 17 | Unsloth GitHub README | docs | Triton kernels สำหรับ RoPE/MLP, padding-free, packing | https://github.com/unslothai/unsloth |
| 18 | Luo et al. (2023) "An Empirical Study of Catastrophic Forgetting in Large Language Models During Continual Fine-tuning" | paper | forgetting เกิดจริง 1B-7B | https://arxiv.org/abs/2308.08747 |
| 19 | Qwen Team (2025) "Qwen2.5-VL Technical Report" | paper | ตัวอย่างการทูน ViT ด้วยข้อมูลมหาศาล (เทียบกับกรณีเรา) | https://arxiv.org/abs/2502.13923 |
| 20 | Rajbhandari et al. (2019) "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models" | paper | ที่มาของการวิเคราะห์ memory ของ optimizer states ในการเทรนขนาดใหญ่ | https://arxiv.org/abs/1910.02054 |
| 21 | Hugging Face (2024) "Vision Language Models Explained" | blog | ตัวอย่าง fine-tune VLM ด้วย TRL SFTTrainer | https://huggingface.co/blog/vlms |
| 22 | Hugging Face TRL docs "LoRA Without Regret" | docs | สรุปข้อแนะนำ [11] ในรูปแบบ config ของ TRL | https://huggingface.co/docs/trl/lora_without_regret |
