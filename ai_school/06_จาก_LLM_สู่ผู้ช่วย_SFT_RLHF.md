# บทที่ 6: จากโมเดลที่ "เติมคำ" สู่ผู้ช่วยที่ "ทำตามคำสั่ง": SFT, RLHF, DPO, GRPO และคำว่า Instruct

> **เป้าหมายของบทนี้:**
> - อธิบายได้ว่าคำว่า `Instruct` ท้ายชื่อ `Qwen3-VL-8B-Instruct` ผ่านกระบวนการอะไรมาบ้าง และทำไม base model ถึง "ไม่ตอบ" แต่ "เขียนต่อ"
> - อ่านสมการของ SFT, RLHF (reward model + PPO), DPO และ GRPO แล้วบอกได้ว่าแต่ละตัวต้องการข้อมูลแบบไหน และทำไมเราใช้แค่ SFT ในโปรเจกต์
> - ตอบได้ว่าทำไม dataset ของเราต้องเป็นรูป `messages`, ทำไม loss ต้องคิดเฉพาะ assistant turn, ทำไม xgrammar บังคับ JSON ให้ปิดได้แต่ห้ามโมเดล "พูดยาว" ไม่ได้ และ hallucination คืออะไรในเชิงกลไก
>
> **ต้องอ่านบทไหนมาก่อน:** บทที่ 4 (loss, overfit, LoRA) และบทที่ 5 (next-token prediction, softmax, sampling, KV cache)
>
> **เวลาอ่านโดยประมาณ:** 90-120 นาที

---

## 6.0 คำถามเปิด (ผูกกับงานจริงของเรา)

บั๊กข้อ 4 ของโปรเจกต์: เราตั้ง `do_sample=False` (greedy) เพราะคิดว่า "งานถอดแบบต้องการคำตอบเดียวที่แน่นอน ไม่ควรสุ่ม" ผลคือโมเดลพ่น `"B2", "B2", "B2", ...` ไม่รู้จบ บางหน้าหลุดเป็นภาษาจีนกลางประโยค recall 0/34 ทั้งชุด พอเปลี่ยนตามที่ Qwen แนะนำ (temperature 0.7, top_p 0.8, top_k 20) บวก xgrammar บังคับ JSON และ repetition_penalty โมเดลกลับมาทำงานได้

มะขามถามว่า "ทำไมการ *สุ่ม* ถึงทำให้คำตอบ *ถูกกว่า* การเลือกค่าที่น่าจะเป็นที่สุด" คำถามนี้ตอบไม่ได้ถ้ามองโมเดลเป็นเครื่องตอบคำถาม แต่ตอบได้ทันทีถ้ามองว่ามันคือเครื่องเติมคำที่ถูก "ดัด" ให้ทำตามคำสั่ง บทนี้เล่าว่าการดัดนั้นทำอย่างไร และข้อจำกัดของมันอธิบายบั๊กของเราได้อย่างไร

---

## 6.1 Base model vs Instruct model: เขียนต่อ กับ ตอบคำถาม

### 6.1.1 base model ทำอะไรได้

จากบทที่ 5 โมเดลที่ pretrain เสร็จคือเครื่องประมาณ $p(x_{t+1} \mid x_1..x_t)$ บนข้อความอินเทอร์เน็ต ถ้าป้อน "ถอดรายการคานจากแบบหน้านี้" base model จะเขียนต่อสิ่งที่ *มักตามมา* ในคลังข้อความ ซึ่งอาจเป็น "…ให้ครบทุกตัว แล้วส่งภายในวันศุกร์" (เหมือนอีเมลสั่งงาน) หรือ "1. เปิดหน้าแบบ 2. …" (เหมือนคู่มือ) ไม่ใช่ JSON ที่เราต้องการ มันไม่ได้ "ไม่รู้" แต่ไม่มีเหตุผลอะไรให้เชื่อว่าสิ่งที่ตามมาคือคำตอบ

### 6.1.2 Instruct model คืออะไร

`Qwen3-VL-8B-Instruct` [15] คือ base model ตัวเดียวกันที่ผ่าน post-training ให้ "เมื่อเห็นข้อความในรูปแบบสนทนา ให้เขียนต่อเป็นคำตอบของผู้ช่วย" กระบวนการนี้มีสองถึงสามขั้นซึ่งบทนี้จะไล่ทีละขั้น

| ขั้น | ข้อมูลที่ใช้ | สอนอะไร |
|---|---|---|
| Pretraining (บทที่ 5) | ข้อความดิบหลายสิบ T token | ภาษา ความรู้ โครงสร้างโลก |
| SFT / instruction tuning | คู่ (คำสั่ง, คำตอบดี) หลักหมื่นถึงล้าน | รูปแบบการตอบ ทำตามคำสั่ง |
| Preference tuning (RLHF / DPO / GRPO) | คู่ (คำตอบดีกว่า, คำตอบแย่กว่า) หรือ reward | เลือกคำตอบที่คนชอบ / ถูกต้อง |

เทียบงานโยธา: pretraining คือเรียนจบวิศวะ (รู้กลศาสตร์ รู้มาตรฐาน) SFT คือช่วงฝึกงานที่รุ่นพี่ให้ดูตัวอย่างว่า "รายการถอดปริมาณของบริษัทเราหน้าตาแบบนี้" preference tuning คือช่วงที่หัวหน้าตรวจงานสองฉบับแล้วบอกว่าชอบฉบับไหนมากกว่า

🎨 **ภาพที่จะวาดใน HTML:** ช่องพิมพ์ prompt เดียวกัน แสดงผลลัพธ์สองคอลัมน์ "base" และ "instruct" (ใช้ตัวอย่างที่เตรียมไว้ 5 prompt รวม prompt ถอดคาน) เมื่อกด "generate" คอลัมน์ base จะพิมพ์ต่อประโยคแบบเอกสารสุ่ม ส่วน instruct พิมพ์คำตอบ มีแถบไทม์ไลน์ด้านบนสามช่วง (pretrain → SFT → preference) ที่คลิกแล้วไฮไลต์ว่าแต่ละช่วงใช้ข้อมูลกี่ token/ตัวอย่าง (log scale) และเปลี่ยนพารามิเตอร์ "กี่ %" (pretrain ~100%, SFT/LoRA <1%)

---

## 6.2 Supervised Fine-Tuning (SFT): สอนด้วยตัวอย่างคำตอบ

### 6.2.1 หลักการ: loss เดิม ข้อมูลใหม่

SFT ใช้ loss เดียวกับ pretraining ทุกประการ (next-token cross-entropy จากบทที่ 5) เปลี่ยนแค่ข้อมูล: จากข้อความดิบเป็นข้อความที่จัดรูปเป็น "คำสั่ง → คำตอบ"

$$\mathcal{L}_{\text{SFT}}(\theta) = -\sum_{t \in \text{assistant}} \log p_\theta(y_t \mid x, y_{<t})$$

$x$ คือ prompt (system + user + ภาพ), $y$ คือคำตอบ, θ คือพารามิเตอร์ (ในกรณี LoRA คือ B, A ของ adapter) สังเกตว่าผลรวมคิดเฉพาะ token ใน assistant turn (หัวข้อ 6.6)

### 6.2.2 FLAN 2021: สอนหลายงานพร้อมกันแล้วทำงานใหม่ได้

Wei และคณะ [1] เอาชุดข้อมูล NLP กว่า 60 งานมาแปลงเป็นรูปคำสั่งภาษาธรรมชาติ ("แปลประโยคนี้", "ประโยคนี้บวกหรือลบ") แล้ว fine-tune โมเดล 137B พบว่าโมเดลทำ **งานที่ไม่เคยเห็น** ได้ดีขึ้นมาก นี่คือหลักฐานว่า instruction tuning สอน "วิธีอ่านคำสั่ง" ไม่ใช่แค่ท่องงาน

### 6.2.3 LIMA 2023: ข้อมูลน้อยแต่ดีก็พอ

Zhou และคณะ [2] fine-tune LLaMA 65B ด้วยตัวอย่างที่คัดมาอย่างดีแค่ 1,000 ตัวอย่าง แล้วได้ผลเทียบเคียง GPT-4 ใน 43% ของกรณี ข้อสรุปคือ "ความรู้เกือบทั้งหมดมาจาก pretraining, SFT แค่สอนรูปแบบ" นี่คือความหวังของโปรเจกต์เรา (t05 มี ~1,000 ตัวอย่างต่อ fold) แต่ต้องระวัง: LIMA สอนรูปแบบสนทนาทั่วไปที่ base model รู้จักดี ส่วนเราสอนให้อ่านแบบก่อสร้างไทยซึ่ง base model แทบไม่เคยเห็น ข้อมูล 1,000 ตัวอย่างจึงต้องแบก "ความรู้ใหม่" ด้วย ไม่ใช่แค่รูปแบบ

Self-Instruct [3] แสดงอีกทางว่าใช้โมเดลสร้างคำสั่งและคำตอบเองแล้วกรอง ก็ได้ข้อมูล SFT ที่ใช้ได้ ท่อข้อมูลของเรา (Qwen ถอด → คนแก้ใน review.html / Label Studio → dataset) คือ Self-Instruct แบบมีคนตรวจ

🎨 **ภาพที่จะวาดใน HTML:** กราฟแกน x = จำนวนตัวอย่าง SFT (log: 100 → 1M) แกน y = คุณภาพ (สมมติ) สองเส้น: "งานที่ base รู้จักแล้ว" (อิ่มตัวเร็วแบบ LIMA) กับ "งานที่ต้องการความรู้ใหม่" (ยังไต่ขึ้นเรื่อย ๆ) มีจุดของโปรเจกต์เราที่ ~1,000 และสไลเดอร์ "สัดส่วนความรู้ใหม่ในงาน" ที่ดันเส้นที่สองไปทางขวา

---

## 6.3 RLHF: จาก "เลียนแบบตัวอย่าง" เป็น "ทำให้คนพอใจ"

### 6.3.1 ปัญหาของ SFT อย่างเดียว

SFT สอนให้เลียนแบบคำตอบตัวอย่าง แต่ (1) คนเขียนตัวอย่างดี ๆ ได้ช้าและแพง (2) คำตอบที่ "ถูก" มีได้หลายแบบ SFT ลงโทษทุกแบบที่ไม่ตรงตัวอย่างเท่ากัน (3) คนตัดสิน "อันไหนดีกว่า" ง่ายกว่าเขียนเอง Ouyang และคณะ 2022 (InstructGPT) [4] จึงเสนอสามขั้น

### 6.3.2 สามขั้นของ InstructGPT

1. **SFT** จากตัวอย่างที่คนเขียน (หัวข้อ 6.2)
2. **Reward model (RM)**: ให้โมเดล SFT ตอบ prompt เดียวกันหลายแบบ ให้คนจัดอันดับ แล้วเทรนโมเดลอีกตัว $r_\phi(x, y)$ ให้คืนคะแนนสเกลาร์ที่สอดคล้องกับอันดับนั้น ใช้ Bradley-Terry loss:

$$\mathcal{L}_{RM} = -\log \sigma\big(r_\phi(x, y_w) - r_\phi(x, y_l)\big)$$

$y_w$ คือคำตอบที่ชนะ $y_l$ ที่แพ้ σ คือ sigmoid ถ้า RM ให้คะแนนผู้ชนะสูงกว่ามาก loss ต่ำ

3. **RL ด้วย PPO** [5]: ให้ policy $\pi_\theta$ (โมเดลภาษา) สร้างคำตอบ RM ให้คะแนน แล้วปรับ θ ให้คะแนนสูงขึ้น โดยมีโทษไม่ให้หนีจากโมเดล SFT ไกลเกิน:

$$J(\theta) = \mathbb{E}_{y \sim \pi_\theta}\big[r_\phi(x,y)\big] - \beta\, \mathbb{D}_{KL}\big(\pi_\theta(\cdot|x)\,\|\,\pi_{\text{ref}}(\cdot|x)\big)$$

$\pi_{\text{ref}}$ คือโมเดล SFT ที่ถูกแช่แข็ง β คือน้ำหนักโทษ KL divergence วัดว่าการแจกแจงสองอันต่างกันแค่ไหน ถ้าไม่มีเทอมนี้ policy จะหาช่องโหว่ของ RM (reward hacking) เช่น เขียนยาว ๆ ใส่คำสุภาพเยอะ ๆ เพราะ RM ให้คะแนนสูง ทั้งที่คนจริงไม่ชอบ

ผลของ InstructGPT: โมเดล 1.3B ที่ผ่าน RLHF ได้รับความชอบจากคนมากกว่า GPT-3 175B ที่ไม่ผ่าน [4] แปลว่า "ทำตามคำสั่งเป็น" มีค่ามากกว่าขนาด

### 6.3.3 PPO เบื้องต้น

PPO (Schulman 2017 [5]) เป็นวิธี policy gradient ที่จำกัดขนาดการเปลี่ยนแปลงต่อขั้นด้วยการ clip อัตราส่วน $\rho = \pi_\theta(y|x)/\pi_{\theta_{\text{old}}}(y|x)$ ให้อยู่ใน $[1-\epsilon, 1+\epsilon]$ (เช่น ε = 0.2) เหมือนการจำกัด step size ใน gradient descent ไม่ให้กระโดดจนหลุดจากบริเวณที่ประมาณค่าได้ดี ราคาที่ต้องจ่ายคือต้องมี 4 โมเดลในหน่วยความจำพร้อมกัน: policy, reference, reward model, และ value model (ตัวประมาณ baseline) นี่คือเหตุผลที่ RLHF แบบเต็มทำในโปรเจกต์ขนาดเราแทบไม่ได้ [16]

### 6.3.4 Constitutional AI / RLAIF แบบสั้น

Bai และคณะ 2022 [6] แทนคนจัดอันดับด้วย AI ที่ตัดสินตาม "รัฐธรรมนูญ" (รายการหลักการ) สองขั้น: ให้โมเดลวิจารณ์และแก้คำตอบตัวเอง แล้วเทรน RM จากการเปรียบเทียบที่ AI ทำ (RLAIF) แนวคิดนี้สำคัญกับเราตรงที่ "ตัวตัดสิน" ไม่จำเป็นต้องเป็นคนเสมอ ในงานถอดแบบ ตัวตัดสินอาจเป็นโค้ดที่เช็คว่า JSON parse ผ่าน จำนวนคานตรงกับ CV นับ หรือมิติอยู่ในช่วงสมเหตุสมผล (หัวข้อ 6.4.3)

🎨 **ภาพที่จะวาดใน HTML:** ผังไหลสามกล่อง (SFT → RM → PPO) ที่กดแต่ละกล่องแล้วเปิดแอนิเมชัน: กล่อง RM แสดงคำตอบ 4 แบบให้ผู้เรียนลากจัดอันดับเอง แล้วเห็น RM loss ลดลงเมื่อคะแนนเรียงตามอันดับ กล่อง PPO แสดงจุด policy บนระนาบ 2 มิติ (แกน = reward, ระยะ KL จาก ref) ที่เดินขึ้นตาม reward แต่ถูกสปริง (β) ดึงกลับ สไลเดอร์ β: ตั้ง 0 แล้วจุดวิ่งไปมุมที่ reward สูงแต่ข้อความเพี้ยน (แสดงตัวอย่าง reward hacking เป็นข้อความ)

```python
import numpy as np
# reward model แบบ Bradley-Terry: ปรับคะแนน r ของ 3 คำตอบให้ตรงอันดับ A > B > C
r = np.zeros(3); pairs = [(0,1),(1,2),(0,2)]; lr = 0.5
sig = lambda z: 1/(1+np.exp(-z))
for step in range(200):
    g = np.zeros(3)
    for w,l in pairs:                       # gradient ของ -log sigmoid(r_w - r_l)
        p = sig(r[w]-r[l]); g[w] += (1-p); g[l] -= (1-p)
    r += lr*g
    if step % 50 == 0:
        loss = sum(-np.log(sig(r[w]-r[l])) for w,l in pairs)
        print(f"step {step:3d} r={np.round(r,2)} loss={loss:.3f}")
```

---

## 6.4 DPO และ GRPO: ทำให้ preference tuning ถูกลง

### 6.4.1 DPO (Rafailov 2023): ตัด reward model และ RL ทิ้ง

Rafailov และคณะ [7] สังเกตว่าคำตอบ optimal ของสมการ RLHF (6.3.2) เขียนเป็นสูตรปิดได้ และเมื่อแทนกลับเข้า Bradley-Terry จะได้ loss ที่ขึ้นกับ policy โดยตรง ไม่ต้องมี RM แยก:

$$\mathcal{L}_{DPO} = -\log \sigma\!\left(\beta \log\frac{\pi_\theta(y_w|x)}{\pi_{\text{ref}}(y_w|x)} - \beta \log\frac{\pi_\theta(y_l|x)}{\pi_{\text{ref}}(y_l|x)}\right)$$

อ่านว่า: "เพิ่มความน่าจะเป็นของคำตอบชนะ ลดของคำตอบแพ้ เทียบกับ reference โดยมี β คุมความแรง" ทั้งหมดเป็น classification loss ธรรมดา ไม่ต้อง sample ระหว่างเทรน ไม่ต้องมี value model ใช้แค่ 2 โมเดล (policy + ref แช่แข็ง หรือ 1 โมเดลถ้าใช้ LoRA แล้วปิด adapter เป็น ref) TRL มี `DPOTrainer` ที่รับ dataset รูป `{prompt, chosen, rejected}` [17]

ตัวอย่างตัวเลข: β = 0.1, policy ให้ log-prob คำตอบชนะสูงกว่า ref 2.0 nat และคำตอบแพ้ต่ำกว่า ref 1.0 nat จะได้ margin = 0.1×(2.0 - (-1.0)) = 0.3 loss = -log σ(0.3) = 0.554 ถ้า margin เป็น 3.0 loss = 0.049

สำหรับงานเรา DPO น่าสนใจเพราะ **เรามีคู่ (chosen, rejected) ฟรี**: JSON ที่โมเดลถอดมา (rejected) กับ JSON ที่คนแก้แล้วใน review.html (chosen) จาก prompt เดียวกัน

### 6.4.2 GRPO (DeepSeek 2024-2025): RL ที่ไม่ต้องมี value model

Shao และคณะ (DeepSeekMath 2024) [8] เสนอ Group Relative Policy Optimization: สำหรับแต่ละ prompt สุ่มคำตอบ G ตัว ให้คะแนน $r_1..r_G$ แล้วใช้ค่าเทียบกันในกลุ่มเป็น advantage:

$$\hat{A}_i = \frac{r_i - \text{mean}(r)}{\text{std}(r)}$$

คำตอบที่ดีกว่าค่าเฉลี่ยของกลุ่มถูกดันขึ้น แย่กว่าถูกกดลง ไม่ต้องมี value model มาประมาณ baseline (ประหยัดหน่วยความจำไปหนึ่งโมเดล) [18] DeepSeek-R1 2025 [9] ใช้ GRPO กับ **reward ที่ตรวจได้ด้วยโค้ด** (คำตอบคณิตตรงเฉลย, โค้ดผ่านเทส) โดยไม่มี SFT นำ และพบว่าโมเดลเรียนรู้ที่จะ "คิดยาว" ตรวจทาน และย้อนกลับเอง แนวนี้เรียก RLVR (RL with verifiable rewards) DAPO 2025 [10] เปิดรายละเอียดเทคนิคที่ทำให้ RL ระดับใหญ่เสถียร

ตัวอย่าง G = 4 คำตอบ reward = (1, 0, 0, 1) mean 0.5 std 0.5 advantage = (+1, -1, -1, +1) คำตอบถูกสองตัวถูกดันขึ้นเท่ากัน

### 6.4.3 Reasoning / thinking model และเหตุผลที่ค่า sampling ต่างกัน

Qwen3 [11] รวมสองโหมดในโมเดลเดียว: **thinking** (เขียน `<think>...</think>` ก่อนตอบ) และ **non-thinking** (ตอบเลย) เอกสารทางการ [12] แนะนำค่าต่างกัน

| โหมด | temperature | top_p | top_k | หมายเหตุ |
|---|---|---|---|---|
| thinking | 0.6 | 0.95 | 20 | **ห้าม greedy** เพราะทำให้วนซ้ำและคุณภาพตก |
| non-thinking | 0.7 | 0.8 | 20 | |
| Qwen3-VL-8B-Instruct (งานภาพ) [15] | 0.7 | 0.8 | 20 | presence_penalty 1.5, repetition_penalty 1.0 |

ทำไมต่างกัน: โหมด thinking ถูกเทรนด้วย RL ที่ **สุ่ม** คำตอบหลายแบบ (GRPO) การแจกแจงของมันจึงถูกปรับให้ "ทำงานได้ดีเมื่อถูกสุ่ม" ไม่ใช่เมื่อเลือก argmax ตลอด top_p 0.95 เปิดกว้างให้สำรวจแนวคิดระหว่างคิด ส่วน non-thinking ต้องการคำตอบตรง จึงตัดหางการแจกแจงแน่นกว่า (top_p 0.8) และ temperature 0.7 กันไม่ให้แหลมจนวน ค่าเหล่านี้เป็นค่าที่ผู้ทำโมเดลวัดมา ไม่ใช่ทฤษฎีตายตัว (state of the art เปลี่ยนได้ทุกรุ่น; Qwen3.6-35B-A3B แนะนำ temperature 1.0/top_p 0.95 สำหรับ thinking ทั่วไป [13])

**นิยาม sampling ที่ควรอ่านออก**
- temperature T: หาร logits ด้วย T ก่อน softmax (โค้ดบทที่ 5) T→0 คือ greedy
- top_k: เหลือแค่ k token ที่น่าจะเป็นสูงสุด แล้ว renormalize
- top_p (nucleus, Holtzman 2019 [14]): เหลือ token ที่น่าจะเป็นสะสมถึง p แล้ว renormalize ปรับตัวตามความแหลมของการแจกแจง
- repetition / presence penalty: ลด logit ของ token ที่ปรากฏแล้ว

🎨 **ภาพที่จะวาดใน HTML:** แท่งกราฟการแจกแจง token ถัดไป 30 token (จากตัวอย่างจริง "หลัง B2 คือ") มีสไลเดอร์ T, top_k, top_p, repetition_penalty ที่เปลี่ยนความสูงแท่งและระบายสีเทาแท่งที่ถูกตัดทิ้ง ปุ่ม "greedy" เลือกแท่งสูงสุดแล้วต่อประโยคอัตโนมัติ 30 ครั้ง ให้เห็นการวนซ้ำ B2 B2 B2 (จำลองด้วย bigram ที่ P(B2|B2) สูงเล็กน้อย) กับปุ่ม "Qwen preset" ที่ต่อประโยคแล้วหลุดจากวงจร ด้านข้างเป็นแท็บ GRPO: กล่อง 4 คำตอบ ให้คลิกติ๊กถูก/ผิด แล้วแสดง advantage ต่อคำตอบและลูกศรดัน/กดบนแท่ง

```python
import numpy as np
rng = np.random.default_rng(1)
P = {"B2": {"B2": 0.36, ",": 0.35, "}": 0.29}, ",": {"B3": 1.0}, "B3": {"}": 1.0}, "}": {"<end>": 1.0}}
def gen(greedy, T=0.7, n=8):
    tok, out = "B2", ["B2"]
    for _ in range(n):
        nxt = list(P[tok]); p = np.array(list(P[tok].values()))
        p = p**(1/T); p /= p.sum()
        tok = nxt[int(np.argmax(p))] if greedy else rng.choice(nxt, p=p)
        out.append(tok)
        if tok == "<end>": break
    return " ".join(out)
print("greedy :", gen(True))     # ติดลูป B2 เพราะ P(B2|B2) สูงสุดแค่นิดเดียว
print("sample :", gen(False))    # หลุดจากลูปได้
```

---

## 6.5 Chat template: ทำไม dataset ต้องเป็น messages

### 6.5.1 โมเดลเห็นแค่ token ลำดับเดียว

จากบทที่ 5 decoder-only "เขียนต่อ" ลำดับ token เท่านั้น ไม่มีแนวคิด "ผู้ใช้" หรือ "ผู้ช่วย" ในตัว การสนทนาจึงต้องถูกแปลงเป็น token ลำดับเดียวด้วย **control token** พิเศษ Qwen ใช้รูปแบบ ChatML [19]:

```
<|im_start|>system
คุณคือผู้ช่วยถอดแบบ<|im_end|>
<|im_start|>user
ถอดคาน B2<|im_end|>
<|im_start|>assistant
<think>

</think>

{"beam_id":"B2"}<|im_end|>
```

ผลด้านบนมาจาก `tokenizer.apply_chat_template` ของ Qwen3-8B จริง ๆ `<|im_start|>` คือ token id 151644, `<|im_end|>` 151645, `</think>` 151668 (ข้อความจริงถูกหั่นเป็น token ปกติ แต่ control token เป็น token เดียวเสมอ ไม่ถูกหั่น) ใน non-thinking mode template ใส่ `<think>\n\n</think>` ว่างไว้ให้ เพื่อให้รูปแบบตรงกับที่โมเดลเคยเห็นตอนเทรน

### 6.5.2 ทำไมรูปแบบต้องตรงเป๊ะ

โมเดลถูก SFT ให้เห็นว่า "หลัง `<|im_start|>assistant\n` คือจุดที่ต้องเริ่มตอบ และ `<|im_end|>` คือจุดหยุด" ถ้าเราเทรนด้วยรูปแบบอื่น (เช่น "Q: ... A: ...") โมเดลต้องเรียนรู้ใหม่ว่าจุดเริ่ม-หยุดอยู่ตรงไหน สิ้นเปลืองข้อมูล และตอนใช้จริงกับ vLLM/llama.cpp ที่ใส่ template ของ Qwen ให้อัตโนมัติ จะไม่ตรงกับที่เทรน เอกสาร HF [20] เตือนชัดว่าใช้ control token ผิด "ประสิทธิภาพตกอย่างมาก" และการเติม `<bos>`/`<eos>` ซ้ำโดยไม่รู้ตัวก็เป็นบั๊กที่พบบ่อย

นี่คือเหตุผลที่ dataset ของเราต้องเป็นรูป

```json
{"messages": [
  {"role": "system", "content": "..."},
  {"role": "user", "content": [{"type": "image", "image": "page_012.png"}, {"type": "text", "text": "ถอดคานทั้งหมด"}]},
  {"role": "assistant", "content": "{\"beams\": [...]}"}
]}
```

แล้วให้ trainer (Unsloth / TRL SFTTrainer [16]) เรียก template ของโมเดลใส่ control token ให้ ภาพจะถูกแทนด้วย token พิเศษ `<|vision_start|>...<|vision_end|>` ที่มี visual token อยู่ข้างใน (ตรงนี้คือที่บั๊กข้อ 1 เกิด: จำนวน visual token ตอนเทรนกับตอนใช้ไม่เท่ากัน)

🎨 **ภาพที่จะวาดใน HTML:** ฟอร์ม messages (system / user / assistant) ที่พิมพ์ได้ ด้านขวาแสดงข้อความหลัง apply_chat_template แบบเรียลไทม์ โดย control token เป็นกล่องสีเด่น (ไม่ถูกหั่น) และข้อความปกติเป็น token สีสลับ มีสวิตช์ "enable_thinking" ที่ใส่/ถอด `<think></think>` และสวิตช์ "add_generation_prompt" ที่เติม `<|im_start|>assistant\n` ท้ายสุด พร้อมข้อความอธิบายว่าโมเดลจะเริ่มเขียนจากตรงไหน และปุ่ม "ใส่ template ผิด" (เช่น Llama format) ที่แสดงคำเตือนว่าโมเดลจะเขียนต่อ user แทนตอบ

---

## 6.6 Loss masking: สอนให้ตอบ ไม่ใช่สอนให้ถาม

ใน SFT ลำดับเดียวมีทั้ง prompt และคำตอบ ถ้าคิด loss ทุก token โมเดลจะเสียความจุไปกับการเรียน "ทำนาย prompt" (เช่น ทำนายว่าคำสั่งถอดคานเขียนว่าอะไร และภาพหน้าตาเป็นอย่างไร) ซึ่งไม่ใช่สิ่งที่เราต้องการ วิธีมาตรฐานคือใส่ label = -100 (ค่าที่ PyTorch cross-entropy ข้าม) ที่ทุก token นอก assistant turn [16]

| token | `<\|im_start\|>` | user | ถอด | คาน | `<\|im_end\|>` | `<\|im_start\|>` | assistant | `{"` | beam | ... | `<\|im_end\|>` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| label | -100 | -100 | -100 | -100 | -100 | -100 | -100 | `{"` | beam | ... | `<\|im_end\|>` |

สังเกตว่า `<|im_end|>` ท้ายคำตอบ **ต้องอยู่ใน loss** ไม่งั้นโมเดลไม่เคยเรียนว่าต้องหยุด และจะพ่นต่อไปเรื่อย ๆ (อาการหนึ่งของบั๊กข้อ 4)

ใน TRL ตั้ง `assistant_only_loss=True` (ต้องใช้ template ที่มี `{% generation %}` ซึ่ง TRL patch ให้ Qwen3 อัตโนมัติ) หรือใช้ prompt-completion dataset ที่ `completion_only_loss` เป็นค่าเริ่มต้น [16] ใน Unsloth ใช้ `train_on_responses_only` โดยระบุ `instruction_part` และ `response_part` เป็นสตริง `<|im_start|>user\n` และ `<|im_start|>assistant\n`

ข้อควรระวังจริง: มีรายงานว่า `assistant_only_loss=True` ถูกละเลยเงียบ ๆ เมื่อเปิด `use_liger_kernel=True` ใน TRL บางเวอร์ชัน [21] นี่คือบั๊กประเภทเดียวกับ บั๊กข้อ 5 ของเรา (ค่า default พลิกผลโดยไม่มี error) วิธีตรวจคือ decode `labels` ของ batch แรกออกมาดูว่าเหลือแต่ assistant จริง

🎨 **ภาพที่จะวาดใน HTML:** แถบ token ของตัวอย่างหนึ่งตัวอย่าง (system + user + ภาพย่อ + assistant JSON) ระบายสีตาม label: เทา = -100 (ไม่คิด loss) เขียว = คิด loss สวิตช์ "assistant_only_loss" เปิด/ปิด ให้เห็นสีเปลี่ยน และมิเตอร์ "สัดส่วน token ที่โมเดลเรียนจริง" (เช่น 1,800 / 6,100 = 30%) กับกล่องข้อความจำลอง log ของ trainer ที่บอกว่า `loss` เฉลี่ยจากกี่ token

```python
# ตรวจว่า mask ถูกต้อง: decode เฉพาะ label ที่ไม่ใช่ -100 ควรเห็นแต่ JSON คำตอบ
import numpy as np
input_ids = np.array([151644, 872, 198, 5001, 151645, 151644, 77091, 198, 4913, 22]) # สมมติ
labels    = np.array([-100, -100, -100, -100, -100, -100, -100, -100, 4913, 22])
kept = input_ids[labels != -100]
print("token ที่คิด loss:", kept, "| สัดส่วน", f"{len(kept)/len(input_ids):.0%}")
# ในงานจริง: print(tokenizer.decode(kept)) แล้วอ่านดูว่าเป็น JSON ล้วน ไม่มี prompt ปน
```

---

## 6.7 Prompt engineering vs Fine-tuning vs RAG: เลือกอะไรเมื่อไหร่

### 6.7.1 In-context learning / few-shot

GPT-3 [22] แสดงว่าโมเดลใหญ่ทำงานใหม่ได้จากตัวอย่างใน prompt (few-shot) โดยไม่แตะพารามิเตอร์ กลไกคือ attention ดึงรูปแบบจากตัวอย่างมาใช้กับคำถาม สำหรับเราการใส่ตัวอย่าง JSON 1-2 หน้าใน prompt ช่วยเรื่อง **รูปแบบ** ได้ แต่แลกกับ token (หน้าละหลายพัน) และไม่ได้เพิ่มความสามารถ "อ่านแบบไทย" ที่ base model ไม่มี

### 6.7.2 RAG

Lewis และคณะ 2020 [23] เสนอดึงเอกสารที่เกี่ยวข้องมาใส่ context ก่อนตอบ Ovadia และคณะ 2023 [24] พบว่าการใส่ "ความรู้ข้อเท็จจริงใหม่" ผ่าน RAG ได้ผลกว่า fine-tuning แบบ unsupervised แต่ RAG ตอบโจทย์ "ความรู้ที่ค้นได้เป็นข้อความ" (เช่น ตารางเหล็กมาตรฐาน, ข้อกำหนดโครงการ) ไม่ตอบโจทย์ "ทักษะการมองภาพเฉพาะทาง"

### 6.7.3 ตารางตัดสินใจ

| สิ่งที่ต้องการเปลี่ยน | Prompt / few-shot | RAG | Fine-tune (LoRA) |
|---|---|---|---|
| รูปแบบ output (JSON schema) | ได้ระดับหนึ่ง | ไม่เกี่ยว | **ดีที่สุด** เสถียร ไม่กิน token |
| ความรู้ข้อเท็จจริงที่เปลี่ยนบ่อย (ราคาวัสดุ, สเปกโครงการ) | ได้ถ้าสั้น | **ดีที่สุด** | แย่ (ต้องเทรนใหม่, ลืมง่าย) |
| ทักษะรับรู้ใหม่ (อ่านสัญลักษณ์แบบไทย, ผูกคานกับกริด) | แทบไม่ได้ | ไม่ได้ | **ทางเดียว** |
| ลดต้นทุน token ต่อคำขอ | แย่ (prompt ยาว) | กลาง | ดี (prompt สั้นได้) |
| ต้นทุนเริ่มต้น | ต่ำสุด | กลาง (ต้องมี index) | สูง (GPU, data, บั๊ก 7 ข้อ) |
| ความเสี่ยงลืมของเดิม | ไม่มี | ไม่มี | มี (หัวข้อ 6.9) |

งานของเรา = โครงสร้าง output เฉพาะทาง **บวก** ภาพเฉพาะทางที่ base model ไม่เคยเห็น จึงตกช่องขวาสุดสองแถว: fine-tune เป็นทางเลือกหลัก โดยใช้ prompt คุมรูปแบบเสริม และ RAG อาจเข้ามาภายหลังสำหรับ "มาตรฐานของโครงการนี้"

🎨 **ภาพที่จะวาดใน HTML:** แบบสอบถามตัดสินใจ 4 คำถาม (ต้องการเปลี่ยนรูปแบบ? ความรู้เปลี่ยนบ่อย? เป็นทักษะรับรู้ใหม่? งบ GPU?) ที่แต่ละคำตอบเลื่อนตัวชี้บนสามเหลี่ยม Prompt / RAG / Fine-tune พร้อมคำอธิบายสั้น และปุ่ม "โปรเจกต์ Constistant" ที่กรอกคำตอบให้แล้วตัวชี้ตกที่ Fine-tune + Prompt

---

## 6.8 Structured output และ constrained decoding: บังคับ JSON ได้แค่ไหน

### 6.8.1 กลไก

constrained decoding ทำงานที่ขั้น sampling: ก่อนเลือก token ถัดไป ให้ตัวตรวจไวยากรณ์ (grammar) ดูว่าตอนนี้อยู่ตรงไหนของ JSON แล้ว **ตั้ง logit ของ token ที่ผิดไวยากรณ์เป็น -∞** โมเดลจึงเลือกได้เฉพาะ token ที่ทำให้ JSON ยังถูก XGrammar (Dong 2024 [25]) ทำให้ขั้นนี้เร็วขึ้นถึง 100 เท่าโดยแบ่ง token ในพจนานุกรมเป็นกลุ่มที่ตรวจล่วงหน้าได้กับกลุ่มที่ต้องตรวจตอนรัน และ vLLM ใช้ xgrammar เป็น backend ให้ระบุ JSON schema, regex หรือ grammar ได้ [26]

ตัวอย่าง: หลัง `{"beam_id": "B2", "width_m": ` grammar อนุญาตเฉพาะตัวเลข เครื่องหมายลบ หรือ `null` token "B2" ภาษาจีน หรือคำพูดใด ๆ ถูกตัดทิ้งหมด **นี่คือเหตุผลที่ xgrammar แก้อาการ "หลุดภาษาจีน" ได้ทันที**

### 6.8.2 สิ่งที่ grammar ทำไม่ได้ (บั๊กจริงของเรา)

grammar รับประกัน **รูปแบบ** ไม่ใช่ **เนื้อหา** และไม่ใช่ **ความยาว**:

- ถ้า schema เป็น `{"beams": [ {...}, {...}, ... ]}` grammar อนุญาตให้ array ยาวเท่าไรก็ได้ โมเดลที่อยากพ่น B2 ซ้ำ ก็ยังพ่น `{"beam_id":"B2"}, {"beam_id":"B2"}, ...` ได้ถูกไวยากรณ์ทุกตัว
- grammar บังคับได้ว่า "ต้องปิดวงเล็บก่อนจบ" แต่บังคับไม่ได้ว่า "ต้องอยากจบ" การจบเกิดเมื่อโมเดลเลือก `]` แล้ว `}` แล้ว `<|im_end|>` ซึ่งขึ้นกับการแจกแจงของโมเดล
- ดังนั้นเราต้องใช้สามอย่างร่วมกัน: xgrammar (รูปแบบ) + repetition_penalty (ลด logit ของ token ที่ซ้ำ) + timeout / max_new_tokens (เพดานความยาว) แต่ละตัวอุดรูคนละรู

Tam และคณะ 2024 [27] ยังเตือนอีกด้าน: การบังคับรูปแบบเข้มเกินไปทำให้ความสามารถ reasoning ลดลง เพราะโมเดลไม่มีที่ให้ "คิดก่อนตอบ" ทางออกที่นิยมคือให้คิดเป็นข้อความอิสระก่อน แล้วค่อยบังคับ JSON เฉพาะส่วนสุดท้าย (vLLM รองรับ structural tag สำหรับกรณีนี้ [26])

🎨 **ภาพที่จะวาดใน HTML:** ตัวพิมพ์ JSON ทีละ token: ด้านซ้ายแสดง JSON ที่พ่นมาแล้ว ด้านขวาแสดงแท่งการแจกแจง 15 token ถัดไปโดยแท่งที่ grammar ตัดทิ้งเป็นสีแดงจาง (logit = -∞) แท่งที่เหลือเป็นสีเขียว สวิตช์ "xgrammar" เปิด/ปิด ให้เห็นว่า token ภาษาจีนหายไปเมื่อเปิด และสไลเดอร์ repetition_penalty ที่กดแท่ง `"B2"` ลงเมื่อมันปรากฏซ้ำ พร้อมตัวนับความยาวที่เดินไปเรื่อย ๆ จนชนเส้น max_new_tokens

```python
import numpy as np
vocab = ['"B2"', '"B3"', '0.2', '中', ']', '}', 'the']
logits = np.array([2.0, 1.5, 1.0, 1.8, 0.5, 0.2, 0.9])
allowed_after_number_key = {'0.2'}                 # grammar: หลัง "width_m": ต้องเป็นตัวเลข
masked = np.where([v in allowed_after_number_key for v in vocab], logits, -np.inf)
p = np.exp(masked - masked.max()); p /= p.sum()
for v, pi in zip(vocab, p): print(f"{v:>6}: {pi:.2f}")
# แต่ถ้า grammar อนุญาต '"B2"' และ ']' ทั้งคู่ (ใน array) โมเดลก็ยังเลือก "B2" ซ้ำได้
```

---

## 6.9 Hallucination และ catastrophic forgetting: สองอาการที่มาจากกลไก

### 6.9.1 Hallucination ในเชิงกลไก

โมเดลไม่มีฐานข้อมูล "ข้อเท็จจริง" ที่จะเปิดเช็ค มันมีแค่การแจกแจง $p(\text{token ถัดไป} \mid \text{บริบท})$ ที่เรียนจากข้อความ เมื่อถูกถามสิ่งที่ไม่มีในบริบทและไม่แน่ใจ การแจกแจงก็ยังต้องรวมเป็น 1 อยู่ดี sampling จึงเลือก *อะไรสักอย่าง* ที่ดู "คล้ายคำตอบ" ออกมาด้วยความมั่นใจเท่า ๆ กับตอนที่รู้จริง

Kalai และคณะ 2025 [28] วิเคราะห์เชิงสถิติว่า hallucination เกิดจากแรงกดดันธรรมชาติของการเทรน (ข้อเท็จจริงที่ปรากฏครั้งเดียวในคลังแยกไม่ออกจากข้อมูลผิด) และถูกซ้ำเติมด้วยการประเมินที่ให้คะแนน "เดา" มากกว่า "บอกว่าไม่รู้" Xu และคณะ 2024 [29] พิสูจน์ในกรอบทฤษฎีการเรียนรู้ว่ากำจัดให้หมดไม่ได้ ส่วน Huang และคณะ 2023 [30] จัดหมวดชนิดของ hallucination และวิธีตรวจจับ

ในงานเรา hallucination หน้าตาเป็น "คาน B7 ขนาด 0.20×0.50 ที่ไม่มีในแบบ" มันไม่ใช่โมเดลโกหก แต่คือการแจกแจงหลัง `{"beam_id": "` ให้ "B7" ความน่าจะเป็นพอสมควรเพราะแบบส่วนใหญ่มี B7 นี่คือเหตุผลที่ต้องมี CV (cv2.matchTemplate ใน tools/pattern_recognition.py) มา cross-check จำนวน เพราะ CV นับจากพิกเซลจริง ไม่ได้นับจากการแจกแจง

### 6.9.2 Catastrophic forgetting

McCloskey และ Cohen ระบุปัญหานี้ตั้งแต่ปี 1989: เทรนเครือข่ายด้วยงานใหม่แล้วงานเก่าหายไป เพราะ gradient ของงานใหม่เขียนทับน้ำหนักที่งานเก่าใช้ Kirkpatrick และคณะ 2017 (EWC) [31] เสนอลงโทษการเปลี่ยนน้ำหนักที่สำคัญกับงานเก่า (วัดด้วย Fisher information) เทียบโยธา: เสริมกำลังคานเดิมโดยไม่แตะเหล็กหลักที่รับโมเมนต์อยู่

สำหรับ LLM ที่ fine-tune ด้วยข้อมูลแคบ (JSON ถอดแบบล้วน) อาการคือโมเดลอาจตอบภาษาธรรมดาแย่ลง หรือลืมวิธีอ่านตารางแบบอื่น Biderman และคณะ 2024 [32] วัดว่า LoRA "เรียนได้น้อยกว่า full fine-tune แต่ลืมน้อยกว่า" ซึ่งเป็นข้อแลกเปลี่ยนที่โปรเจกต์เราเลือกอยู่แล้ว (LoRA r = 32/64) วิธีลดผลกระทบอื่น: ผสมข้อมูลทั่วไปเข้าไปสัก 5-10%, ใช้ lr ต่ำ, epoch น้อย, และ freeze vision tower (ที่ t02 ทำ) เพื่อไม่ให้ตัวรับรู้ภาพถูกเขียนทับด้วยภาพ 512px ที่ย่อผิด

🎨 **ภาพที่จะวาดใน HTML:** สองแท็บ แท็บ hallucination: แท่งการแจกแจงหลัง `"beam_id": "` สองกรณี (มี B7 ในภาพ / ไม่มี) ที่หน้าตาเกือบเหมือนกัน พร้อมค่า entropy และเส้น "ความมั่นใจของโมเดล" ที่ไม่ต่างกัน ให้ผู้เรียนเห็นว่าไม่มีสัญญาณภายในบอกว่าอันไหนจริง แล้วมีกล่อง "CV นับได้ 6 คาน" ที่ขีดฆ่า B7 ออก แท็บ forgetting: ระนาบน้ำหนัก 2 มิติ มีวงรี "บริเวณที่งานเก่าทำได้ดี" และ "งานใหม่" จุดน้ำหนักเดินตาม gradient ของงานใหม่ออกจากวงรีเก่า สไลเดอร์ "โทษ EWC / rank LoRA" ที่ดึงเส้นทางให้อยู่ในส่วนซ้อนทับ

---

## 6.10 การประเมิน LLM: benchmark, LLM-as-judge, human eval และข้อจำกัด

- **Benchmark มาตรฐาน** (MMLU, GSM8K, MMMU สำหรับภาพ) วัดความสามารถทั่วไป เปรียบเทียบข้ามโมเดลได้ แต่ (1) ข้อสอบรั่วเข้าคลังเทรน (contamination) (2) ไม่สะท้อนงานเฉพาะทางเลย โมเดลที่ MMMU สูงอาจอ่านแบบไทยไม่ได้
- **LLM-as-a-judge** (Zheng 2023 [33]; survey Gu 2024 [34]): ให้โมเดลแข็ง ๆ ให้คะแนนคำตอบ ตรงกับคนราว 80% ในงานสนทนา แต่มีอคติ: ชอบคำตอบยาว ชอบตำแหน่งแรก ชอบสไตล์ตัวเอง และ **ตรวจข้อเท็จจริงที่ต้องดูภาพไม่ได้** ถ้าตัวตัดสินก็ hallucinate
- **Human eval**: แม่นสุดแต่แพงและช้า (ท่อ review.html ของเราคือ human eval แบบต่อเนื่อง)
- **Task metric ที่ตรวจด้วยโค้ด**: element recall, leave-one-out, GT vs AI overlay ของเรา เป็น "verifiable reward" ในภาษาของ 6.4.2 นี่คือจุดแข็งของงานเรา เพราะเมื่อมี metric ที่โค้ดตรวจได้ ก็เปิดทางไปสู่ DPO/GRPO ได้โดยไม่ต้องจ้างคนจัดอันดับ

ข้อจำกัดที่ต้องจำ: recall บอกว่า "หาเจอกี่ตัว" แต่ไม่บอกว่า "ตัวที่หาเจอ ขนาดถูกไหม" ควรมี precision, mismatch ของมิติ และอัตรา JSON parse ผ่าน ควบคู่ และเมื่อใช้ leave-one-out กับ dataset เล็ก ความแปรปรวนของตัวเลขสูง ควรรายงานช่วง ไม่ใช่ตัวเลขเดียว

🎨 **ภาพที่จะวาดใน HTML:** ตารางเปรียบเทียบวิธีประเมิน 4 วิธี × 5 เกณฑ์ (ค่าใช้จ่าย, ความเร็ว, ความแม่น, อคติ, ใช้กับงานภาพเฉพาะทางได้) เป็น heatmap ที่คลิกช่องแล้วอ่านคำอธิบาย และกราฟ "recall ต่อ fold" ของ k-fold 2 ที่แสดง error bar เมื่อผู้เรียนลด/เพิ่มจำนวนตัวอย่างต่อ fold (จำลอง) ให้เห็นว่าที่ ~1,000 ตัวอย่าง ช่วงความเชื่อมั่นกว้างแค่ไหน

---

## 6.11 เชื่อมกับงานของเรา

| แนวคิดในบทนี้ | ปรากฏตรงไหนในโปรเจกต์ |
|---|---|
| Instruct model | ทุกรอบทูนเริ่มจาก `-Instruct` (Qwen3-VL-8B/32B-Instruct, Qwen3.6-35B-A3B) เพราะเราต้องการต่อยอดจากโมเดลที่ "รู้จัก messages และ JSON แล้ว" ไม่ใช่สอนใหม่จาก base |
| SFT loss = cross-entropy บน assistant | t02: LoRA r=32/64, lr=1e-4, 3 epoch, cosine คือ SFT ล้วน ไม่มี preference stage; ค่า lr 1e-4 ตรงกับที่ TRL แนะนำสำหรับ adapter [16] |
| Chat template / messages | dataset ทุก pass ของ t03 และ t05 อยู่ในรูป messages เพื่อให้ Unsloth/TRL ใส่ ChatML ให้ตรงกับที่ Qwen เคยเห็น |
| Loss masking | ถ้า mask ผิด โมเดลจะใช้ความจุไปเรียน "ทำนาย prompt" และไม่เรียนว่าต้องหยุดที่ `<\|im_end\|>` เป็นสาเหตุที่เป็นไปได้หนึ่งของการพ่นไม่หยุดใน บั๊กข้อ 4 ควรตรวจ labels ของ batch แรกทุกครั้ง |
| Sampling / greedy | บั๊กข้อ 4 ตรง ๆ: greedy บนการแจกแจงที่ P(B2\|B2) สูงกว่าคู่แข่งนิดเดียวทำให้วนไม่รู้จบ และ argmax ที่ตกลงบน token จีน (Qwen เทรนสองภาษาหนัก) แล้วดึงบริบทไปทางนั้น ค่า 0.7/0.8/20 คือค่าที่ผู้ทำโมเดลวัดมา [12][15] |
| Constrained decoding | xgrammar แก้รูปแบบ (JSON ปิด, ไม่มีภาษาจีน) แต่แก้ความยาวไม่ได้ ต้องบวก repetition_penalty และ timeout ตามที่ทำจริง |
| Default พลิกผล | บั๊กข้อ 5 และรายงาน `assistant_only_loss` ถูกละเลยเมื่อเปิด liger [21] เป็นเรื่องเดียวกัน: พารามิเตอร์ที่ไม่ได้ตั้งหรือถูก override เงียบ ๆ |
| Hallucination | คาน/เสาที่ไม่มีในแบบ และ "นับผิด/ไม่นิ่ง" ที่ทำให้ต้องมี cv2.matchTemplate (threshold footing 0.60 / column 0.65 / beam 0.70) เป็น deterministic cross-check |
| Forgetting | freeze vision tower ที่ t02 และ LoRA แทน full fine-tune คือมาตรการกันลืมที่ใช้อยู่ |
| Verifiable reward | element recall / GT overlay คือ reward ที่โค้ดตรวจได้ เปิดทางให้รอบต่อไปลอง DPO จากคู่ (JSON ที่ AI ถอด, JSON ที่คนแก้) |
| Train/inference mismatch | บั๊กข้อ 1 ในภาษาของบทนี้: SFT สอนการแจกแจงบนบริบทที่มี visual token ~266 ตัว แต่ตอนใช้ป้อน 3,796 ตัว โมเดลจึงอยู่นอกการแจกแจงที่ถูกดัดมา |

---

## 6.12 ระดับนักวิจัย: คำถามที่ยังเปิดอยู่

1. **RL สร้างความสามารถใหม่ หรือแค่ดึงของเดิมออกมา?** Yue และคณะ 2025 [35] วัด pass@k แล้วพบว่าเมื่อ k ใหญ่พอ base model ตามทัน (และแซง) โมเดลที่ผ่าน RLVR ในทุกตระกูล สรุปว่า RL "บีบการแจกแจง" ไปทางคำตอบที่ได้ reward แต่ไม่ขยายขอบเขต ต่างจาก distillation ที่ใส่ความรู้ใหม่ได้ สำหรับเราแปลว่า: ถ้า base มองแบบไทยไม่ออกเลย DPO/GRPO ช่วยได้จำกัด ต้องพึ่ง SFT ที่มีข้อมูลจริงก่อน
2. **SFT กับ RL อันไหนควรมาก่อน และสัดส่วนเท่าไร?** DeepSeek-R1 [9] ทำ RL ล้วนแล้วค่อยเติม SFT ในภายหลัง ส่วน DAPO [10] เปิดสูตรทั้งหมด งานปี 2025-2026 ยังเถียงเรื่อง "SFT ทำให้ท่องจำ RL ทำให้ generalize" ซึ่งไม่มีคำตอบเดียวสำหรับงานเฉพาะทางที่ข้อมูลน้อย
3. **Structured output ทำร้าย reasoning แค่ไหน และแก้อย่างไร?** [27] แสดงว่ายิ่งบังคับยิ่งแย่ในงานคิดวิเคราะห์ คำถามเปิดคือควรให้โมเดล "คิดอิสระ" ก่อนแล้วบังคับ JSON เฉพาะตอนท้าย (structural tag) หรือ fine-tune ให้ JSON เป็นภาษาแม่ไปเลย งานเราที่มี pass แยก (classify → organize → extract) คือการทดลองในเรื่องนี้โดยปริยาย
4. **Hallucination แก้ที่การประเมินหรือที่โมเดล?** [28] เสนอว่าต้องแก้ที่ระบบให้คะแนน (ให้เครดิตกับ "ไม่แน่ใจ") ส่วน [29] บอกว่ากำจัดไม่ได้ในหลักการ สำหรับงานเราคำถามที่ปฏิบัติได้คือ ควรให้ schema มี `confidence` หรือ `null` และให้ reward กับการเว้นว่างเมื่อไม่แน่ใจ แทนที่จะให้ recall อย่างเดียวซึ่งจูงใจให้เดา
5. **LoRA ลืมน้อยกว่าจริง แต่เรียนได้น้อยกว่าด้วย** [32] คำถามคือสำหรับทักษะรับรู้ใหม่ (อ่านแบบไทย) rank เท่าไรจึงพอ และควรแปะ LoRA บน vision tower ด้วยหรือไม่ เมื่อ t02 freeze ไว้ทั้งหมด นี่เป็นการทดลองที่ยังไม่ได้ทำ

---

## 6.13 แบบฝึกหัด

**ข้อ 1 (คิด)** ทำไมโมเดลชื่อ `-Instruct` ยังพ่น "B2" ซ้ำไม่รู้จบได้ ทั้งที่ผ่าน SFT/preference tuning มาแล้ว

<details><summary>เฉลย</summary>
post-training ดัดการแจกแจงให้ "คำตอบแบบผู้ช่วย" มีความน่าจะเป็นสูง แต่ไม่ได้เปลี่ยนกลไก: โมเดลยังเป็นเครื่องสุ่มจากการแจกแจง ในบริบทแปลก (visual token ที่ไม่เคยเห็น 14 เท่า, JSON ยาว) การแจกแจงอาจมีจุดที่ P(B2|…B2) สูงสุดเพียงเล็กน้อย greedy เลือกมันทุกครั้ง จึงวน การเทรนของ Qwen ยังทำบน sampling ไม่ใช่ greedy จึงแนะนำห้าม greedy ตรง ๆ [12]
</details>

**ข้อ 2 (คำนวณ)** DPO β = 0.1 policy ให้ log-prob คำตอบชนะ -20.0 (ref -22.0) และคำตอบแพ้ -18.0 (ref -17.0) คำนวณ loss ถ้า β = 0.5 loss เป็นเท่าไร

<details><summary>เฉลย</summary>
margin = β[(−20+22) − (−18+17)] = β(2 − (−1)) = 3β; β=0.1 → 0.3, loss = −log σ(0.3) = 0.554; β=0.5 → 1.5, loss = −log σ(1.5) = 0.201 β สูงทำให้ loss ตอบสนองแรงขึ้นต่อ margin เดียวกัน (ดันออกจาก ref แรงขึ้น)
</details>

**ข้อ 3 (คำนวณ)** GRPO กลุ่ม G = 5 reward = (1, 1, 0, 0, 0) หา advantage ของแต่ละคำตอบ และถ้า reward เป็น (1,1,1,1,1) จะเกิดอะไรขึ้น

<details><summary>เฉลย</summary>
mean 0.4, std (population) = √(0.24) = 0.49 advantage = (+1.22, +1.22, −0.82, −0.82, −0.82) ถ้าทุกตัวได้ 1 std = 0 advantage นิยามไม่ได้ (หารศูนย์) และไม่มีสัญญาณเรียนรู้ นี่คือเหตุผลที่ DAPO [10] เสนอ dynamic sampling ทิ้ง prompt ที่ทุกคำตอบถูกหรือผิดหมด
</details>

**ข้อ 4 (รันโค้ด)** แก้โค้ด 6.4.3 ให้ P(B2|B2) = 0.30 และ P(","|B2) = 0.41 แล้วรัน greedy อีกครั้ง อธิบายว่าทำไมผลเปลี่ยน และทำไมเราจึงไม่ควรพึ่ง "หวังว่า argmax จะพอดี"

<details><summary>เฉลย</summary>
greedy จะเลือก "," แล้วไปต่อ B3 } end ไม่วน เพราะ argmax เปลี่ยนตัว แสดงว่าพฤติกรรม greedy พลิกได้จากส่วนต่างความน่าจะเป็นเล็กน้อย (0.36 vs 0.35) ซึ่งเราควบคุมไม่ได้และเปลี่ยนตามบริบท/quantization sampling + penalty + grammar ทำให้ระบบทนต่อความไม่แน่นอนนี้
</details>

**ข้อ 5 (คิด)** ออกแบบ dataset DPO จากท่อข้อมูลปัจจุบันของเรา: chosen และ rejected มาจากไหน มีความเสี่ยงอะไรถ้า rejected คือ JSON ที่ AI ถอดแล้วคน "แก้เล็กน้อย"

<details><summary>เฉลย</summary>
prompt = ภาพ + คำสั่งเดิม; rejected = JSON ดิบจาก Qwen; chosen = JSON หลังคนแก้ใน review.html ความเสี่ยง: ถ้าสองฉบับต่างกันแค่ 1-2 ค่า margin ใน DPO จะเล็กและสัญญาณอ่อน อีกทั้ง DPO ดันความน่าจะเป็นของ rejected ลงทั้งลำดับ รวมส่วนที่ถูกอยู่แล้ว 95% ควรกรองเฉพาะคู่ที่ต่างกันมีนัย หรือใช้ token-level/segment-level preference
</details>

---

## สรุปบทนี้ใน 5 บรรทัด

1. base model เขียนต่อ, instruct model ตอบคำสั่ง ต่างกันที่ post-training ไม่ใช่สถาปัตยกรรม และ `-Instruct` คือสิ่งที่เราต่อยอดทุกรอบทูน
2. SFT ใช้ cross-entropy เดิมบนข้อมูล (คำสั่ง, คำตอบ) โดยคิด loss เฉพาะ assistant turn และต้องใส่ chat template ให้ตรงกับที่โมเดลเคยเห็น จึงเป็นเหตุผลของ dataset รูป messages
3. RLHF = SFT → reward model → PPO (4 โมเดล แพง) DPO ยุบเหลือ classification loss บนคู่ chosen/rejected ส่วน GRPO ใช้ advantage เทียบในกลุ่มกับ reward ที่โค้ดตรวจได้ และให้กำเนิด thinking model ที่ต้องใช้ sampling ไม่ใช่ greedy
4. โมเดลคือเครื่องสุ่มจากการแจกแจง จึง hallucinate ได้อย่างมั่นใจ, greedy วนซ้ำได้, grammar บังคับได้แค่รูปแบบไม่ใช่ความยาว และ fine-tune ทำให้ลืมของเดิมได้ ทุกบั๊กของเราอธิบายด้วยประโยคนี้
5. งานที่ต้องการทั้ง output เฉพาะทางและการรับรู้ภาพเฉพาะทางเลือก fine-tune เป็นหลัก ประเมินด้วย metric ที่โค้ดตรวจได้ และ metric นั้นเองคือ reward สำหรับขั้นต่อไป

---

## ที่มาและอ่านต่อ

| # | แหล่ง | ประเภท | ทำไมควรอ่าน | URL |
|---|---|---|---|---|
| 1 | Wei et al. (2021). Finetuned Language Models Are Zero-Shot Learners (FLAN) | paper | instruction tuning สอน "อ่านคำสั่ง" | https://arxiv.org/abs/2109.01652 |
| 2 | Zhou et al. (2023). LIMA: Less Is More for Alignment | paper | 1,000 ตัวอย่างพอ ถ้าความรู้มีแล้ว | https://arxiv.org/abs/2305.11206 |
| 3 | Wang et al. (2022). Self-Instruct | paper | สร้างข้อมูล SFT ด้วยโมเดลเอง | https://arxiv.org/abs/2212.10560 |
| 4 | Ouyang et al. (2022). Training language models to follow instructions with human feedback (InstructGPT) | paper | สามขั้น SFT → RM → PPO ต้นฉบับ | https://arxiv.org/abs/2203.02155 |
| 5 | Schulman et al. (2017). Proximal Policy Optimization Algorithms | paper | PPO | https://arxiv.org/abs/1707.06347 |
| 6 | Bai et al. (2022). Constitutional AI: Harmlessness from AI Feedback | paper | RLAIF, ตัวตัดสินไม่ต้องเป็นคน | https://arxiv.org/abs/2212.08073 |
| 7 | Rafailov et al. (2023). Direct Preference Optimization | paper | DPO และที่มาของสูตร | https://arxiv.org/abs/2305.18290 |
| 8 | Shao et al. (2024). DeepSeekMath | paper | ต้นฉบับ GRPO | https://arxiv.org/abs/2402.03300 |
| 9 | DeepSeek-AI (2025). DeepSeek-R1 | paper | RL ล้วนสร้าง reasoning, RLVR | https://arxiv.org/abs/2501.12948 |
| 10 | Yu et al. (2025). DAPO: An Open-Source LLM RL System at Scale | paper | รายละเอียดที่ทำให้ RL ใหญ่เสถียร | https://arxiv.org/abs/2503.14476 |
| 11 | Qwen Team (2025). Qwen3 Technical Report | paper | thinking / non-thinking ในโมเดลเดียว | https://arxiv.org/abs/2505.09388 |
| 12 | Qwen3-8B model card | docs | ค่า sampling แนะนำสองโหมด และคำเตือนห้าม greedy | https://huggingface.co/Qwen/Qwen3-8B |
| 13 | Qwen3.6-35B-A3B model card | docs | ค่า sampling รุ่นล่าสุด (เปลี่ยนตามรุ่น) | https://huggingface.co/Qwen/Qwen3.6-35B-A3B |
| 14 | Holtzman et al. (2019). The Curious Case of Neural Text Degeneration | paper | nucleus sampling, ทำไม greedy ทำให้ซ้ำ | https://arxiv.org/abs/1904.09751 |
| 15 | Qwen3-VL-8B-Instruct model card | docs | ค่า sampling สำหรับงานภาพ (0.7/0.8/20, presence 1.5) | https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct |
| 16 | HF TRL docs: SFT Trainer | docs | loss, `assistant_only_loss`, `completion_only_loss`, lr สำหรับ adapter | https://huggingface.co/docs/trl/sft_trainer |
| 17 | HF TRL docs: DPO Trainer | docs | รูป dataset chosen/rejected และสูตร loss | https://huggingface.co/docs/trl/dpo_trainer |
| 18 | HF TRL docs: GRPO Trainer | docs | สูตร advantage เทียบกลุ่ม | https://huggingface.co/docs/trl/grpo_trainer |
| 19 | Qwen docs: Key Concepts (ChatML) | docs | `<\|im_start\|>` / `<\|im_end\|>` และ role | https://qwen.readthedocs.io/en/latest/getting_started/concepts.html |
| 20 | HF Transformers docs: Chat templates | docs | apply_chat_template, add_generation_prompt, คำเตือน special token ซ้ำ | https://huggingface.co/docs/transformers/chat_templating |
| 21 | TRL issue #3781: assistant_only_loss ถูกละเลยเมื่อใช้ liger kernel | docs | ตัวอย่างจริงของ default ที่พลิกผลเงียบ ๆ | https://github.com/huggingface/trl/issues/3781 |
| 22 | Brown et al. (2020). Language Models are Few-Shot Learners | paper | in-context learning | https://arxiv.org/abs/2005.14165 |
| 23 | Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | paper | RAG ต้นฉบับ | https://arxiv.org/abs/2005.11401 |
| 24 | Ovadia et al. (2023). Fine-Tuning or Retrieval? | paper | ความรู้ข้อเท็จจริงใหม่ควรใช้ RAG | https://arxiv.org/abs/2312.05934 |
| 25 | Dong et al. (2024). XGrammar | paper | constrained decoding เร็ว 100 เท่า | https://arxiv.org/abs/2411.15100 |
| 26 | vLLM docs: Structured Outputs | docs | json / regex / grammar / structural tag กับ xgrammar backend | https://docs.vllm.ai/en/latest/features/structured_outputs.html |
| 27 | Tam et al. (2024). Let Me Speak Freely? | paper | บังคับรูปแบบทำให้ reasoning แย่ลง | https://arxiv.org/abs/2408.02442 |
| 28 | Kalai et al. (2025). Why Language Models Hallucinate | paper | สาเหตุเชิงสถิติและการประเมินที่จูงใจให้เดา | https://arxiv.org/abs/2509.04664 |
| 29 | Xu et al. (2024). Hallucination is Inevitable | paper | พิสูจน์ว่ากำจัดไม่ได้ในหลักการ | https://arxiv.org/abs/2401.11817 |
| 30 | Huang et al. (2023). A Survey on Hallucination in LLMs | paper | อนุกรมวิธานและวิธีตรวจจับ | https://arxiv.org/abs/2311.05232 |
| 31 | Kirkpatrick et al. (2017). Overcoming catastrophic forgetting in neural networks (EWC) | paper | นิยามและวิธีแก้แบบคลาสสิก | https://arxiv.org/abs/1612.00796 |
| 32 | Biderman et al. (2024). LoRA Learns Less and Forgets Less | paper | ข้อแลกเปลี่ยนของ LoRA ที่เราใช้ | https://arxiv.org/abs/2405.09673 |
| 33 | Zheng et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | paper | LLM-as-judge และอคติของมัน | https://arxiv.org/abs/2306.05685 |
| 34 | Gu et al. (2024). A Survey on LLM-as-a-Judge | paper | ภาพรวมและข้อจำกัด | https://arxiv.org/abs/2411.15594 |
| 35 | Yue et al. (2025). Does RL Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model? | paper | RL บีบการแจกแจง ไม่ขยายขอบเขต | https://arxiv.org/abs/2504.13837 |
| 36 | Zhang et al. (2023). Instruction Tuning for LLMs: A Survey | paper | ภาพรวม SFT ทั้งสาย | https://arxiv.org/abs/2308.10792 |
| 37 | Lambert et al. (2022). Illustrating RLHF (HF blog) | blog | ภาพประกอบสามขั้น RLHF | https://huggingface.co/blog/rlhf |
| 38 | Raschka (2023). LLM Training: RLHF and Its Alternatives | blog | เปรียบเทียบ RLHF, DPO, RLAIF, ReST | https://magazine.sebastianraschka.com/p/llm-training-rlhf-and-its-alternatives |
| 39 | Karpathy (2023). Let's build GPT: from scratch, in code, spelled out | video | เห็น next-token → chat ในโค้ดจริง | https://www.youtube.com/watch?v=kCc8FmEb1nY |
