# บทที่ 4: จาก kernel ที่คนออกแบบ สู่ kernel ที่เครื่องเรียนเอง: CNN และ Vision Transformer

> **เป้าหมายของบทนี้:**
> - อธิบายได้ว่า convolution layer คือ Sobel ที่ "ปล่อยให้ตัวเลขใน kernel เป็นตัวแปร" แล้วให้ gradient descent หาค่าเอง และเหตุใดการซ้อนหลายชั้นจึงได้ลำดับชั้น edge → texture → part → object
> - เล่าเส้นทาง LeNet (1998) → AlexNet (2012) → VGG → ResNet (2015) ได้พร้อมเหตุผลว่าแต่ละก้าวแก้ปัญหาอะไร และอธิบาย transfer learning ที่ทำให้เราไม่ต้องเทรนจากศูนย์
> - คำนวณได้ว่าภาพหน้าแบบ 3309×2339 px กลายเป็น visual token กี่ตัวใน Vision Transformer แบบ Qwen-VL และทำไมตัวเลขนี้คือหัวใจของบั๊ก 14 เท่า และของ VRAM/เวลาที่เราจ่าย
>
> **ต้องอ่านบทไหนมาก่อน:** บทที่ 2 (gradient descent, loss) และบทที่ 3 (convolution, Sobel, ภาพ = เมทริกซ์)
> **เวลาอ่านโดยประมาณ:** 70-90 นาที

---

## 4.0 คำถามเปิด (ผูกกับงานจริงของเรา)

บั๊กที่แพงที่สุดของโปรเจกต์ไม่ใช่โค้ดผิด แต่คือตัวเลขสองตัวที่ไม่เท่ากัน: ตอนเทรน collator ย่อภาพเหลือ 512 px ทำให้หนึ่งหน้าแบบกลายเป็น visual token ประมาณ 266 ตัว แต่ตอนใช้จริงเราป้อนหน้าแบบที่ให้ token ประมาณ 3,796 ตัว ต่างกัน 14 เท่า โมเดลที่ทูนมาไม่เคยเห็น "ภาพแบบนี้" ตอนเทรนเลย

คำถามคือ ทำไมภาพถึงกลายเป็น "token" ได้ 266 ตัวหรือ 3,796 ตัว ตัวเลขพวกนี้มาจากไหน ทำไมไม่ใช่ 7.7 ล้าน (จำนวนพิกเซล) และทำไมโมเดลจึงแคร์จำนวน token มากขนาดที่ recall ตกจากที่ควรได้

ตอบได้ต้องเข้าใจสองสิ่ง: (1) CNN ซึ่งเป็นวิธี "ย่อภาพให้เป็นความหมาย" ยุคแรก และ (2) Vision Transformer ซึ่งตัดภาพเป็น patch แล้วปฏิบัติกับมันเหมือนคำในประโยค ทั้งสองสืบทอดโดยตรงจาก Sobel ในบทที่ 3 และบทนี้จะเชื่อมเส้นนั้นให้เห็น พร้อมคำนวณเลข 3,796 ให้ดูด้วยมือ

---

## 4.1 Convolution layer = filter ที่เรียนรู้ได้

### ขั้นที่ 1: Sobel มีตัวเลข 9 ตัวที่คนกำหนด

ในบทที่ 3 kernel Sobel-x คือ

$$K_x = \begin{bmatrix} -1 & 0 & 1 \\ -2 & 0 & 2 \\ -1 & 0 & 1 \end{bmatrix}$$

Irwin Sobel คิดตัวเลข 9 ตัวนี้ในปี 1968 จากเหตุผลทางคณิตศาสตร์ (ความชันที่ค่อนข้าง isotropic) มันหา "ขอบแนวตั้ง" ได้ดี แต่ถ้าอยากหา "ไอคอนฐานรากแบบจัตุรัสซ้อน" ล่ะ จะออกแบบตัวเลขยังไง ไม่มีใครรู้

### ขั้นที่ 2: เปลี่ยนตัวเลขให้เป็นตัวแปร

Convolution layer ทำสิ่งเดียวกับ `cv2.filter2D` ทุกประการ คือคูณ-บวกแบบเลื่อนหน้าต่าง แต่ตัวเลขใน kernel ไม่ได้ถูกกำหนด มันคือ **พารามิเตอร์** $w_{ij}$ ที่เริ่มจากค่าสุ่ม แล้วให้ gradient descent (บทที่ 2) ปรับจน loss ต่ำ

$$O[y,x] = b + \sum_{i}\sum_{j} w_{ij}\; I[y+i, x+j]$$

$b$ คือ bias หนึ่งตัวต่อ kernel ถ้า layer มี 64 kernel ขนาด 3×3 ก็มีพารามิเตอร์ $64 \times (9 + 1) = 640$ ตัว น้อยมากเมื่อเทียบกับ fully-connected layer ที่เชื่อมทุกพิกเซลกับทุกนิวรอน (ภาพ 224×224 เข้า 64 นิวรอน = 3.2 ล้านพารามิเตอร์)

เทียบกับงานโยธา: Sobel คือสูตรจากมาตรฐาน convolution layer คือ "สูตรที่มีสัมประสิทธิ์ว่าง" แล้วเราถอยสัมประสิทธิ์จากผลทดสอบจริง เหมือนหาสมการกำลังอัดคอนกรีตกับอายุจากข้อมูลทดสอบของโรงงานเอง

สิ่งที่น่าทึ่งที่ Yosinski et al. (2014) [11] และ Zeiler & Fergus (2013) [5] พบคือ **ชั้นแรกของ CNN ที่เทรนบนภาพธรรมชาติเรียนรู้ได้ตัวกรองที่หน้าตาเหมือน Sobel/Gabor เอง** คือตัวหาขอบทุกทิศทางและตัวหาจุดสี โดยไม่มีใครบอก แปลว่า "ขอบ" คือสิ่งที่ข้อมูลภาพบังคับให้ต้องหาอยู่แล้ว Sobel แค่เดาถูกก่อนเครื่อง 45 ปี

### ขั้นที่ 3: feature map, stride, padding

ผลลัพธ์ของหนึ่ง kernel คือหนึ่ง **feature map** (ภาพคะแนน "ตรงนี้มีลวดลายที่ kernel ชอบแค่ไหน" ตรงกับแผนที่ $R$ ของ matchTemplate ในบทที่ 3) layer ที่มี 64 kernel ให้ 64 feature map ซ้อนกันเป็นเทนเซอร์ $64 \times H' \times W'$ ซึ่งเป็น "ภาพ" ที่มี 64 ช่องสีแทน 3 ช่อง แล้วชั้นถัดไปก็ convolve บนมันต่อได้ (kernel ชั้นถัดไปจึงมีขนาด $3 \times 3 \times 64$)

- **stride** = ก้าวเลื่อน stride 2 ทำให้ feature map เล็กลงครึ่ง
- **padding** = เติมศูนย์รอบขอบ เพื่อให้ขนาดเอาต์พุตเท่าอินพุต

```python
import torch, torch.nn as nn, numpy as np
img = torch.zeros(1, 1, 7, 7); img[:, :, :, :4] = 1.0        # กระดาษซ้าย หมึกขวา (ปรับ 0-1)
conv = nn.Conv2d(1, 1, kernel_size=3, bias=False)
sobel = torch.tensor([[[[-1., 0, 1], [-2, 0, 2], [-1, 0, 1]]]])
with torch.no_grad():
    conv.weight.copy_(sobel)                                  # ใส่ Sobel เป็นค่าเริ่มต้น
print("เอาต์พุตแถวกลาง (Sobel ตายตัว):", conv(img)[0, 0, 3].numpy().round(1))
conv2 = nn.Conv2d(1, 1, kernel_size=3, bias=False)           # ค่าสุ่ม = kernel ที่ยังไม่รู้อะไร
print("เอาต์พุตแถวกลาง (สุ่ม):        ", conv2(img)[0, 0, 3].detach().numpy().round(2))
print("จำนวนพารามิเตอร์ต่อ kernel:", conv.weight.numel())   # 9 ตัว
```

🎨 **ภาพที่จะวาดใน HTML:** ซ้ายเป็นภาพ crop ฐานราก 32×32 ขวาเป็น kernel 3×3 ที่มีสไลเดอร์ 9 ตัว (−2 ถึง 2) ค่าเริ่มต้นสุ่ม ตรงกลางเป็น feature map แบบเรียลไทม์ มีปุ่ม "ตั้งเป็น Sobel-x" "Sobel-y" และปุ่ม "ให้ gradient descent หาเอง 50 ก้าว" ที่ animate ตัวเลขใน kernel ค่อย ๆ ขยับ พร้อมกราฟ loss ลดลง (loss = ผลต่างกับ feature map เป้าหมายที่ผู้ออกแบบซ่อนไว้ เช่น "หาขอบซ้ายของไอคอน") ให้เห็นว่า kernel ที่เรียนได้ออกมาคล้าย Sobel

---

## 4.2 Pooling และ receptive field: ทำไมชั้นลึกจึง "เห็นกว้าง"

### Pooling

Max pooling 2×2 แทนทุกช่อง 2×2 ด้วยค่าสูงสุด feature map เล็กลง 4 เท่า ผลสองอย่าง: (1) ประหยัดการคำนวณ (2) ทนการเลื่อนเล็กน้อย เพราะถ้าขอบเลื่อนไป 1 px ค่าสูงสุดในช่อง 2×2 ยังเท่าเดิม นี่คือคำตอบเชิงโครงสร้างของปัญหา "เลื่อน 1 px ก็ยังเหมือน" ที่ NMS ในบทที่ 3 ต้องมาแก้ทีหลัง

### Receptive field

นิวรอนในชั้นแรกที่ kernel 3×3 "เห็น" พิกเซล 3×3 ชั้นที่สองที่ convolve บนชั้นแรก แต่ละช่องของชั้นแรกเห็น 3×3 ของภาพ และชั้นสองรวม 3×3 ช่องของชั้นแรก จึงเห็นภาพ 5×5 ชั้นที่สามเห็น 7×7 สูตรทั่วไปสำหรับ kernel 3×3 stride 1 ซ้อน $L$ ชั้นคือ $1 + 2L$ [10] ถ้ามี pooling 2 เท่าคั่น receptive field จะโตเป็นทวีคูณ

นี่คือเหตุผลที่ VGG (2014) [3] ใช้ kernel 3×3 ล้วน 16-19 ชั้น: สาม 3×3 ซ้อนกันเห็นเท่า 7×7 ชั้นเดียว แต่ใช้พารามิเตอร์ $3 \times 9 = 27$ แทน $49$ และมี nonlinearity คั่นสามครั้ง

เทียบกับงานเรา: ไอคอนฐานราก 56 px ต้องการ receptive field อย่างน้อย 56 px ถึงจะมีนิวรอนที่ "เห็นทั้งไอคอน" ได้ ส่วนการเชื่อม "คานพาดจากกริด A ถึง C" ต้องการ receptive field หลายร้อยพิกเซล CNN ตื้น ๆ ทำไม่ได้ นี่คือแรงจูงใจหนึ่งของ attention ที่เห็นทั้งภาพตั้งแต่ชั้นแรก (หัวข้อ 4.6)

🎨 **ภาพที่จะวาดใน HTML:** ตารางภาพ 16×16 ซ้อนด้วย feature map ชั้น 1, 2, 3 (แต่ละชั้นเล็กลง) เมื่อคลิกนิวรอนหนึ่งตัวในชั้นใด ให้ไฮไลต์ย้อนกลับลงมาว่าครอบพิกเซลกี่ช่องในภาพต้นทาง (3×3 → 5×5 → 7×7) สวิตช์ "ใส่ max-pool 2×2 หลังชั้น 1" ที่ทำให้ receptive field ชั้น 2 กระโดดเป็น 8×8 และตัวเลขสูตร $1+2L$ แสดงคู่กัน

---

## 4.3 ประวัติย่อ: LeNet → AlexNet → VGG → ResNet

### LeNet-5 (LeCun, Bottou, Bengio, Haffner 1998) [1]

เครือข่ายอ่านตัวเลขบนเช็คและรหัสไปรษณีย์ รับภาพ 32×32 ผ่าน conv 5×5 (6 feature map) → subsampling → conv 5×5 (16 map) → subsampling → fully-connected → 10 คลาส เป็นครั้งแรกที่แสดงว่า convolution + gradient descent แบบ end-to-end ใช้ได้จริงในระดับอุตสาหกรรม แต่ยุคนั้นไม่มีข้อมูลใหญ่และไม่มี GPU จึงหยุดอยู่ที่ตัวเลขลายมือ

### AlexNet (Krizhevsky, Sutskever, Hinton 2012) [2]

จุดเปลี่ยนของทั้งวงการ: 5 conv + 3 FC รวม 60 ล้านพารามิเตอร์ เทรนบน ImageNet 1.2 ล้านภาพ 1,000 คลาส ด้วย GPU สองใบ ชนะ ILSVRC 2012 ด้วย top-5 error 15.3% ทิ้งอันดับสองที่ 26.2% ห่างกว่า 10 จุด สิ่งที่ทำให้ได้คือ ReLU (เทรนเร็วกว่า sigmoid) dropout (กัน overfit) และ **GPU** ซึ่งเป็นตัวแปรเดียวกับที่ทำให้เราต้องเช่า Vast.ai ในปี 2026

### VGG (Simonyan & Zisserman 2014) [3]

พิสูจน์ว่า "ลึกขึ้นด้วย kernel เล็ก 3×3 ล้วน" ดีกว่า kernel ใหญ่ (หัวข้อ 4.2) แต่พอลึกเกิน 20 ชั้น กลับเทรนยากขึ้น ความแม่นยำ **ลดลง** ทั้งบน train set ซึ่งไม่ใช่ overfit แต่คือ optimization ล้มเหลว: gradient ที่ไหลย้อนผ่านหลายสิบชั้นถูกคูณด้วยค่าน้อย ๆ ซ้ำจนเหลือเกือบศูนย์ (vanishing gradient)

### ResNet (He, Zhang, Ren, Sun 2015) [4]

ทางแก้ที่เรียบง่ายจนน่าตกใจ: **skip connection**

$$y = F(x) + x$$

แทนที่จะให้ชั้น $F$ เรียนรู้เอาต์พุตทั้งหมด ให้เรียนแค่ "ส่วนต่าง" (residual) จาก $x$ ถ้าชั้นนั้นไม่มีประโยชน์ก็ตั้ง $F(x) = 0$ แล้วส่ง $x$ ผ่านไปเฉย ๆ ทำให้เพิ่มชั้นแล้วอย่างน้อยไม่แย่ลง และ gradient มีทางลัดไหลย้อนผ่าน $+x$ โดยไม่ถูกคูณ ผลคือเทรนได้ 152 ชั้น ชนะ ILSVRC 2015 ด้วย top-5 error 3.57%

เทียบกับงานโยธา: skip connection คือ "ส่งแรงตรงลงเสาผ่านทางลัด" แทนที่จะให้แรงทั้งหมดต้องเดินผ่านคานทุกตัวก่อนถึงฐานราก ทางลัดทำให้ระบบไม่ล้มแม้คานบางตัวรับแรงไม่ได้ และแนวคิดนี้ก็คือ residual stream ใน Transformer ทุกตัวรวมถึง Qwen (บทที่ 5)

```python
import torch, torch.nn as nn
def deep(n, skip):
    layers = [nn.Linear(16, 16) for _ in range(n)]
    x = torch.randn(1, 16, requires_grad=True); h = x
    for L in layers:
        h = torch.tanh(L(h)) + (h if skip else 0)             # + h คือ skip connection
    h.sum().backward()
    return x.grad.abs().mean().item()
for n in (5, 20, 50):
    print(f"{n:2d} ชั้น | ไม่มี skip: {deep(n, False):.2e} | มี skip: {deep(n, True):.2e}")
# คาดผล: ไม่มี skip → gradient ที่อินพุตหดจนเกือบศูนย์เมื่อ 50 ชั้น มี skip → ยังมีขนาด
```

🎨 **ภาพที่จะวาดใน HTML:** กราฟ ILSVRC top-5 error ตามปี (2010: ~28%, 2011: ~26%, 2012 AlexNet 15.3%, 2014 VGG/GoogLeNet ~7%, 2015 ResNet 3.57%, เส้นประระดับมนุษย์ ~5%) แกน x เป็นปี แกน y เป็น error คลิกแต่ละจุดเปิดการ์ดสถาปัตยกรรม (จำนวนชั้น พารามิเตอร์ นวัตกรรมหลัก) ด้านล่างเป็นการจำลอง vanishing gradient: สไลเดอร์จำนวนชั้น 1-60 สวิตช์ skip on/off แสดงแท่งขนาด gradient ที่แต่ละชั้นแบบ log scale

---

## 4.4 Feature hierarchy: edge → texture → part → object

Zeiler & Fergus (2013) [5] ใช้ "deconvnet" ฉายกลับว่านิวรอนในแต่ละชั้นของ AlexNet ตอบสนองต่ออะไรในภาพจริง และ Olah, Mordvintsev, Schubert (2017) [6] ใช้ optimization สร้างภาพที่ทำให้นิวรอนแต่ละตัวยิงแรงที่สุด ทั้งสองงานเห็นภาพเดียวกัน:

| ชั้น | สิ่งที่ตรวจจับ | เทียบกับแบบก่อสร้าง |
|---|---|---|
| 1 | ขอบทุกทิศ จุดสี (เหมือน Sobel/Gabor) | เส้นหมึกบนกระดาษ |
| 2 | มุม เส้นคู่ขนาน ลายจุด | เส้นคู่คาน มุมกล่องเสา |
| 3 | ลวดลาย (texture) รูปทรงพื้นฐาน | จัตุรัสซ้อน (ไอคอน F1) วงกลมกริด |
| 4 | ชิ้นส่วนของวัตถุ | "กล่องเสาที่จุดตัดเส้นคู่" |
| 5+ | วัตถุทั้งตัว ในบริบท | "ผังคานชั้น 2 ที่มีคาน B1-B4" |

ความหมายเชิงลึกคือ CNN สร้าง "template" ของตัวเองเป็นลำดับชั้น: ชั้นต้นคือ template เล็ก ๆ ทั่วไป ชั้นลึกคือ template ของ template ซึ่งทน scale/rotation/สำนักวาดได้มากกว่า template พิกเซลของเราในบทที่ 3 เพราะมัน "ประกอบ" จากชิ้นส่วน ไม่ได้เทียบพิกเซลตรง ๆ นี่คือคำตอบเชิงหลักการว่าทำไม YOLO ใน SkeySpot จับสัญลักษณ์ที่วาดต่างสำนักได้ ในขณะที่ template bank ของเราต้องเก็บ F1 กับ F2 แยกกัน

🎨 **ภาพที่จะวาดใน HTML:** แถบแนวตั้ง 5 ชั้น แต่ละชั้นมีตารางเล็ก ๆ 8 ช่องแสดง "ภาพที่กระตุ้นนิวรอนนี้แรงที่สุด" (สร้างด้วย SVG เป็นภาพสังเคราะห์: ชั้น 1 เส้นเฉียง ชั้น 2 เส้นคู่/มุม ชั้น 3 จัตุรัสซ้อน ชั้น 5 ผังจำลอง) เมื่อวางเมาส์บนช่องหนึ่งของชั้น $n$ ให้ลากเส้นไปยังช่องของชั้น $n-1$ ที่มันประกอบมา และเมื่ออัปโหลด/เลือกภาพ crop ฐานราก ให้ไฮไลต์ว่าชั้นไหนยิงแรงตรงไหน (จำลองด้วย filter สังเคราะห์)

---

## 4.5 Transfer learning: ทำไมไม่ต้องเทรนจากศูนย์

Yosinski et al. (2014) [11] วัดอย่างเป็นระบบว่า feature ชั้นต้น ๆ **ทั่วไป** (ใช้ได้กับทุกงาน) ส่วนชั้นท้าย **เฉพาะงาน** ผลที่ตามมาคือสูตรมาตรฐานของวงการ:

1. **Pretrain** บน dataset ใหญ่ (ImageNet 1.2M ภาพ) ให้ได้ตัวกรอง edge/texture/part ที่ดี
2. **Fine-tune** บนงานเราด้วยข้อมูลน้อย: ล็อกชั้นต้น (freeze) ปรับเฉพาะชั้นท้าย หรือปรับทั้งหมดด้วย learning rate ต่ำ

เทียบกับงานโยธา: ไม่มีใครฝึกวิศวกรใหม่จากการสอนว่า "เส้นตรงคืออะไร" ทุกคนมาพร้อมความสามารถอ่านรูปทรงอยู่แล้ว เราแค่สอนสัญลักษณ์เฉพาะสำนัก

ในโปรเจกต์เรา แนวคิดนี้ปรากฏตรงที่ t02 **freeze vision tower** ทั้งหมด ปรับเฉพาะส่วนภาษาด้วย LoRA (บทที่ 8 จะลงรายละเอียด) เหตุผลคือ vision encoder ของ Qwen3-VL ถูก pretrain มาบนภาพหลายร้อยล้านภาพแล้ว ความสามารถ "เห็นเส้น เห็นตัวหนังสือ" ทั่วไปพอ ปัญหาของเราอยู่ที่ "แปลสิ่งที่เห็นเป็น JSON ตามสคีมา" ซึ่งเป็นงานฝั่งภาษา แต่ก็มีคำถามค้างว่า ถ้าแบบก่อสร้างต่างจากภาพธรรมชาติมาก (ลายเส้นบาง ขาวดำ ความละเอียดสูง) การ freeze อาจทิ้งโอกาสไว้ ซึ่งเป็นประเด็นวิจัยในหัวข้อ 4.9

🎨 **ภาพที่จะวาดใน HTML:** แผนภาพเครือข่าย 8 บล็อกเรียงซ้าย→ขวา (conv1…conv5, FC, head) แต่ละบล็อกมีสวิตช์ "freeze/train" และแถบสีแสดง "ความทั่วไป → ความเฉพาะงาน" (จาก Yosinski) สไลเดอร์ "จำนวนตัวอย่างของเรา" 50 → 5,000 ที่เปลี่ยนคำแนะนำ: ข้อมูลน้อย → freeze เกือบหมด ข้อมูลมาก → train ได้ลึกขึ้น พร้อมกราฟจำลอง accuracy เทียบระหว่าง "จากศูนย์" กับ "pretrain แล้ว fine-tune"

---

## 4.6 Object detection และ segmentation แบบย่อ

ในบทที่ 3 เราหา "กล่อง" ด้วย template + NMS วงการ deep learning เดินเส้นทางเดียวกันแต่ให้เครือข่ายทำทุกขั้น:

- **R-CNN (Girshick et al. 2013)** [7] เสนอ region proposal (~2,000 กล่องที่น่าจะมีวัตถุ) แล้วเอา CNN จำแนกทีละกล่อง ช้าแต่แม่น (mAP 53.3% บน VOC 2012) ต่อมาเป็น Fast/Faster R-CNN ที่ให้เครือข่ายเสนอกล่องเอง [12]
- **YOLO (Redmon et al. 2015)** [8] มองทั้งภาพครั้งเดียว แบ่งเป็นกริด ทำนายกล่อง+คลาสทุกช่องพร้อมกันเป็น regression ได้ 45 fps และยังต้องใช้ NMS แบบเดียวกับเราปิดท้าย YOLOv8 คือรุ่นที่ SkeySpot ใช้กับแบบไฟฟ้า
- **DETR (Carion et al. 2020)** [9] ใช้ Transformer ทำนาย "เซต" ของกล่องโดยตรง จับคู่กับเฉลยด้วย Hungarian matching จึง **ไม่ต้องมี NMS และไม่ต้องมี anchor** เป็นครั้งแรกที่ตัดสูตรจาก CV ดั้งเดิมออกหมด

Segmentation คือการระบายทุกพิกเซลว่าเป็นอะไร:

- **U-Net (Ronneberger et al. 2015)** [13] เข้ารหัสภาพให้เล็กลง (contracting) แล้วขยายกลับ (expanding) โดยมี skip connection ข้ามจากฝั่งย่อไปฝั่งขยายที่ความละเอียดเดียวกัน ทำให้ขอบแม่นแม้ข้อมูลน้อย เกิดในวงการแพทย์แต่ใช้ทุกที่
- **SAM (Kirillov et al. 2023)** [14] โมเดล "แบ่งอะไรก็ได้" เทรนบน 1.1 พันล้าน mask จาก 11 ล้านภาพ รับ prompt เป็นจุดหรือกล่องแล้วคืน mask แบบ zero-shot

สำหรับงานเรา ถ้าวันหนึ่งต้องการ "กล่องฐานรากทุกสำนักวาด" โดยไม่ต้องดูแล template bank ทางเลือกคือ fine-tune YOLO ด้วยกล่องที่ template bank + คนคัดสร้างไว้ให้ (bootstrap) และถ้าต้องการ "พื้นที่ของแต่ละคาน" เพื่อวัดความยาวจริง segmentation คือเครื่องมือ

🎨 **ภาพที่จะวาดใน HTML:** แท็บสามใบ: R-CNN (แสดง proposal 2,000 กล่องค่อย ๆ ถูกจำแนก), YOLO (กริด 7×7 ทาบบนผังจำลอง แต่ละช่องมีลูกศรทำนายกล่อง จบด้วย NMS แบบเดียวกับบทที่ 3), DETR (query 10 ตัวจับคู่กับวัตถุจริงด้วยเส้น matching ไม่มี NMS) และแท็บที่สี่ segmentation: คลิกจุดบนคานแล้วระบายพื้นที่คานเป็นสี (จำลอง SAM)

---

## 4.7 Vision Transformer: ตัดภาพเป็น patch แล้วปฏิบัติเหมือนคำ

### ขั้นที่ 1: patch → flatten → linear projection → token

Dosovitskiy et al. (2020) [15] ถามคำถามที่ตรงไปตรงมา: Transformer ที่ทำงานกับลำดับของ token (คำ) ในภาษา ถ้าเราแปลงภาพเป็น "ลำดับของ token" ได้ จะใช้ Transformer เปล่า ๆ โดยไม่มี convolution เลยได้ไหม

วิธีแปลง (ViT-Base/16):

1. ภาพ 224×224×3 ตัดเป็น patch ขนาด 16×16 ได้ $(224/16)^2 = 14 \times 14 = 196$ patch
2. แต่ละ patch มี $16 \times 16 \times 3 = 768$ ตัวเลข **flatten** เป็นเวกเตอร์ยาว 768
3. คูณด้วยเมทริกซ์ $E$ ขนาด $768 \times D$ (**linear projection**, เรียนรู้ได้) ได้เวกเตอร์ขนาด $D$ (ViT-Base ใช้ $D = 768$)
4. บวก position embedding (เพื่อบอกว่า patch นี้อยู่ตรงไหน เพราะ attention ไม่รู้ลำดับเอง)
5. ได้ token 196 ตัว + [CLS] 1 ตัว ป้อนเข้า Transformer encoder แบบเดียวกับ BERT ทุกประการ

ตัวอย่างเล็ก: ภาพ grayscale 4×4 patch 2×2 → 4 patch แต่ละ patch flatten เป็น 4 ตัวเลข ถ้า $D = 2$ เมทริกซ์ $E$ ขนาด $4 \times 2$

$$\text{patch}_1 = [255, 255, 0, 0], \quad E = \begin{bmatrix} 0.01 & 0 \\ 0.01 & 0 \\ 0 & 0.01 \\ 0 & 0.01 \end{bmatrix} \Rightarrow \text{token}_1 = [5.1,\; 0]$$

token นี้บอกว่า "แถวบนสว่าง แถวล่างมืด" ซึ่งก็คือ Sobel-y แบบหยาบ ๆ อีกครั้ง **linear projection ของ patch คือ convolution ที่ kernel = patch size และ stride = patch size** ทางคณิตศาสตร์เหมือนกันเป๊ะ (โค้ดจริงของ ViT ก็ใช้ `nn.Conv2d(3, D, kernel_size=16, stride=16)`) ViT จึงไม่ได้ "ไม่มี convolution" มันมี convolution ชั้นเดียวแล้วส่งต่อให้ attention

```python
import torch, torch.nn as nn
img = torch.randn(1, 3, 224, 224)
patchify = nn.Conv2d(3, 768, kernel_size=16, stride=16)      # = ตัด patch + flatten + linear
tokens = patchify(img)                                        # (1, 768, 14, 14)
tokens = tokens.flatten(2).transpose(1, 2)                    # (1, 196, 768) = 196 token ยาว 768
print("จำนวน token:", tokens.shape[1], "| มิติต่อ token:", tokens.shape[2])
print("พารามิเตอร์ของ patch embedding:", sum(p.numel() for p in patchify.parameters()))
# 3*16*16*768 + 768 = 590,592
```

### ขั้นที่ 2: inductive bias: CNN vs ViT

**Inductive bias** คือ "สมมติฐานที่ฝังในโครงสร้าง" ก่อนเห็นข้อมูล CNN ฝังสองอย่าง: (1) **locality** พิกเซลใกล้กันเกี่ยวข้องกัน (2) **translation equivariance** ไอคอนที่มุมซ้ายกับมุมขวาควรถูกจับด้วย kernel เดียวกัน ทั้งสองข้อ "จริง" สำหรับภาพ CNN จึงเรียนได้จากข้อมูลไม่มาก

ViT แทบไม่ฝังอะไร attention ให้ทุก patch มองทุก patch ตั้งแต่ชั้นแรก ต้อง **เรียน** ว่า patch ข้าง ๆ สำคัญกว่า patch ไกล ๆ เอง ผลคือ (ตามที่ paper รายงาน) เมื่อเทรนบน ImageNet อย่างเดียว ViT แพ้ ResNet แต่เมื่อ pretrain บน JFT-300M (300 ล้านภาพ) ViT ชนะ เหตุผลคือด้วยข้อมูลมากพอ bias ที่เรียนเองจะดีกว่า bias ที่คนกำหนด Raghu et al. (2021) [16] ยืนยันว่า ViT รวมข้อมูลระดับทั้งภาพตั้งแต่ชั้นต้น ในขณะที่ CNN ค่อย ๆ ขยาย receptive field และ DeiT (2020) [17] แสดงว่าด้วย augmentation และ distillation ที่ดี ViT เทรนบน ImageNet อย่างเดียวก็สู้ได้

| | CNN | ViT |
|---|---|---|
| Inductive bias | locality + translation equivariance (คนกำหนด) | น้อยมาก (เรียนเอง) |
| ข้อมูลที่ต้องการ | น้อยกว่า | มากกว่า (หรือต้องมี trick แบบ DeiT) |
| Receptive field ชั้นแรก | 3×3 | ทั้งภาพ |
| ค่าใช้จ่ายตามขนาดภาพ | เชิงเส้นกับจำนวนพิกเซล | attention เป็น $O(N^2)$ กับจำนวน token $N$ |

ข้อสุดท้ายคือหัวใจของหัวข้อ 4.8

### ขั้นที่ 3: CLIP: เชื่อมภาพกับภาษา (ปูทางบทที่ 7)

Radford et al. (2021) [18] เทรน image encoder (ViT หรือ ResNet) กับ text encoder พร้อมกันบน 400 ล้านคู่ (ภาพ, คำบรรยาย) จากอินเทอร์เน็ต ด้วย contrastive loss: ในชุด $N$ คู่ ให้เวกเตอร์ของภาพที่ $i$ ใกล้เวกเตอร์ข้อความที่ $i$ และไกลจากอีก $N-1$ ข้อความ ผลคือ **ภาพและข้อความอยู่ในปริภูมิเวกเตอร์เดียวกัน** ถามว่า "ภาพนี้คือ 'ผังฐานราก' หรือ 'ผังคาน'" ได้โดยไม่ต้องเทรนตัวจำแนก (zero-shot) เท่ากับ ResNet-50 บน ImageNet โดยไม่เห็นตัวอย่าง 1.28 ล้านภาพเลย

Vision encoder ของ VLM ยุคปัจจุบัน (รวม Qwen ที่ใช้ SigLIP-2 ใน Qwen3-VL [20]) สืบทอดจากตระกูลนี้ เหตุผลที่ VLM "รู้ว่ากำลังดูอะไร" คือ encoder ถูกเทรนให้ตรงกับภาษาตั้งแต่ต้น บทที่ 7 จะต่อจากตรงนี้

🎨 **ภาพที่จะวาดใน HTML:** ภาพหน้าแบบจำลองที่มีเส้นกริดตัดเป็น patch สไลเดอร์ patch size 8/14/16/32 เปลี่ยนจำนวนช่องและตัวเลข "จำนวน token" แบบเรียลไทม์ คลิก patch ใดจะเห็น (1) พิกเซลของมันขยายใหญ่ (2) เวกเตอร์ flatten (แสดง 16 ค่าแรก) (3) เวกเตอร์หลัง projection เป็นแถบสี และ (4) heatmap attention จำลองว่า patch นี้ "มอง" patch ไหนบ้าง (ตอนเริ่ม = สม่ำเสมอทั้งภาพ เพื่อสื่อว่า ViT ไม่มี locality bias)

---

## 4.8 คำนวณ visual token ของหน้าแบบเรา: หัวใจของบั๊ก 14 เท่า

### ขั้นที่ 1: กติกาของ Qwen2-VL / Qwen2.5-VL / Qwen3-VL

Qwen2-VL [19] เปลี่ยนจาก ViT ที่รับภาพขนาดตายตัว (224×224) เป็น **naive dynamic resolution**: รับภาพขนาดไหนก็ได้ ตัดเป็น patch **14×14** แล้วมี MLP รวม **2×2 patch ที่ติดกันเป็น 1 token** ก่อนส่งเข้า LLM ดังนั้น 1 visual token = 28×28 พิกเซล paper ให้ตัวอย่างว่าภาพ 224×224 กลายเป็น 66 token (= $16 \times 16 = 256$ patch → $8 \times 8 = 64$ token + `<vision_start>` + `<vision_end>`) ตัวประมวลผลภาพใน HuggingFace จึงมีฟังก์ชัน `smart_resize(height, width, factor=28, min_pixels=56*56, max_pixels=28*28*1280)` ที่ปัดขนาดภาพให้หารด้วย 28 ลงตัว [21] Qwen3-VL (และ Qwen3.6 ที่ t01/t05 ใช้) เปลี่ยน encoder เป็น SigLIP-2 ที่ใช้ patch **16×16** แต่ยังคง merge 2×2 ดังนั้น 1 visual token = **32×32** พิกเซล [20] (บทที่ 7 ตรวจจาก `preprocessor_config.json` ของ Qwen3.6 แล้ว: `patch_size: 16, merge_size: 2`) ตัวเลขในหัวข้อ 4.8 ด้านล่างคำนวณด้วยกติกา 28 px ของ Qwen2-VL เพื่อให้ตรงกับ paper ที่อ้าง ถ้าเป็น Qwen3 ให้แทน 28 ด้วย 32 หลักการเหมือนกันทุกประการ

สูตรจึงเป็น

$$N_{\text{token}} = \left\lceil \frac{H}{28} \right\rfloor \times \left\lceil \frac{W}{28} \right\rfloor \quad (\text{ปัดเป็นจำนวนเต็มใกล้ที่สุด ภายใต้ min/max\_pixels})$$

### ขั้นที่ 2: หน้าแบบเต็มความละเอียด 3309×2339

- $3309 / 28 = 118.18 \to 118$ ช่อง (กว้าง 3304 px)
- $2339 / 28 = 83.54 \to 84$ ช่อง (สูง 2352 px)
- patch 14 px: $236 \times 168 = 39{,}648$ patch
- หลัง merge 2×2: $118 \times 84 = \mathbf{9{,}912}$ visual token

แต่ภาพนี้มี $3304 \times 2352 \approx 7.77$ ล้านพิกเซล เกิน `max_pixels` ปริยาย (1,003,520 px ≈ 1,280 token) processor จะย่อลงให้พอดี max_pixels ที่ตั้ง ดังนั้นจำนวน token จริงขึ้นกับค่า **default ที่ไม่ได้ตั้ง** ซึ่งเป็นบั๊กข้อ 5 ของเราพอดี

### ขั้นที่ 3: ย้อนหาว่าเลข 3,796 และ 266 มาจากไหน

$3{,}796 = 73 \times 52$ ตรงกับภาพ $73 \times 28 = 2044$ px × $52 \times 28 = 1456$ px (อัตราส่วน 1.404 ใกล้ 3309/2339 = 1.415) ≈ 2.98 ล้านพิกเซล แปลว่าตอน inference มี max_pixels ราว 3 ล้านพิกเซลทำงานอยู่ ภาพถูกย่อจากเต็ม ~62% แล้วแต่ยังใหญ่ (ถ้าล็อกนั้นมาจากโมเดลตระกูล Qwen3 ที่ใช้ 32 px ต่อ token ภาพจริงคือ $73 \times 32 = 2336$ × $52 \times 32 = 1664$ px ≈ 3.9 ล้านพิกเซล ข้อสรุปเรื่องอัตราส่วน 14 เท่าไม่เปลี่ยน)

ส่วน collator ตอนเทรนย่อด้านยาวเหลือ 512 px: $512 \times (2339/3309) \approx 512 \times 362$ → $18 \times 13 = 234$ token หรือถ้าปัดขึ้นเป็น $19 \times 14 = 266$ (ตัวเลขที่วัดได้จริงในรีโป) ไม่ว่าจะ 234 หรือ 266 ก็ต่างจาก 3,796 ราว **14-16 เท่า**

ที่ 512 px เส้นคู่คานที่ห่าง 21 px กลายเป็น 3 px ตัวหนังสือ "B1 0.20×0.40" สูง 20 px กลายเป็น 3 px คือ **อ่านไม่ออกทางกายภาพ** โมเดลจึงเรียนรู้ที่จะเดาจากรูปทรงหยาบ ๆ ของหน้า แล้วพอเจอภาพ 3,796 token ตอนใช้จริงซึ่งเป็นการกระจายตัวของอินพุตที่ไม่เคยเห็น (train/inference distribution mismatch) ก็ไม่รู้จะทำอย่างไรกับรายละเอียดที่โผล่มา นี่ยังอธิบายคำเตือนที่ถูกมองข้ามในบั๊กข้อ 6 ด้วย: Qwen-VL แนะนำ ≥ 1,024 image token เพราะต่ำกว่านั้นภาพเอกสารอ่านไม่ได้

```python
def qwen_tokens(w, h, factor=28, max_pixels=28*28*1280, min_pixels=56*56):
    import math
    hb, wb = round(h/factor)*factor, round(w/factor)*factor
    if hb*wb > max_pixels:                        # ย่อให้พอดีเพดาน (ตามแนวคิด smart_resize)
        s = math.sqrt(max_pixels/(h*w)); hb, wb = (math.floor(h*s/factor)*factor,
                                                   math.floor(w*s/factor)*factor)
    elif hb*wb < min_pixels:
        s = math.sqrt(min_pixels/(h*w)); hb, wb = (math.ceil(h*s/factor)*factor,
                                                   math.ceil(w*s/factor)*factor)
    return (hb//factor)*(wb//factor), (wb, hb)
for name, w, h, mp in [("เต็ม ไม่มีเพดาน", 3309, 2339, 10**9),
                       ("เต็ม เพดาน default", 3309, 2339, 28*28*1280),
                       ("inference ของเรา (~3M px)", 3309, 2339, 2_980_000),
                       ("collator 512px", 512, 362, 10**9)]:
    n, wh = qwen_tokens(w, h, max_pixels=mp); print(f"{name:28s} → {wh} = {n:,} token")
```

### ขั้นที่ 4: ทำไม visual token = VRAM = เวลา

ทุก visual token ถูกปฏิบัติเหมือน token คำใน LLM ค่าใช้จ่ายมีสามก้อน:

1. **Attention เป็นกำลังสอง** ทุก token มองทุก token: $3{,}796^2 \approx 14.4$ ล้านคู่ เทียบ $266^2 \approx 70{,}800$ คู่ ต่างกัน **~200 เท่า** (ต่อชั้น ต่อ head) นี่คือรายการที่โตเร็วที่สุดเมื่อภาพใหญ่ขึ้น
2. **KV cache เป็นเชิงเส้น** ทุกชั้นต้องเก็บเวกเตอร์ Key และ Value ของทุก token ไว้ตลอดการ generate ขนาดต่อ token คือ $2 \times L \times n_{kv} \times d_{head} \times \text{bytes}$ ($L$ = จำนวนชั้น, $n_{kv}$ = จำนวน KV head, $d_{head}$ = มิติต่อ head) ตัวอย่างสมมติ $L = 36$, $n_{kv} = 8$, $d_{head} = 128$, bf16 (2 ไบต์) → 147 KB ต่อ token → 3,796 token ≈ 560 MB และ 9,912 token ≈ 1.4 GB **ต่อหนึ่งภาพ ต่อหนึ่งตัวอย่างใน batch** ก่อนจะนับพารามิเตอร์ของโมเดลและ activation ตอน backprop ซึ่งใหญ่กว่านี้หลายเท่า
3. **Prefill เป็นเชิงเส้น** ทุก token ต้องผ่านทุกชั้นของ LLM หนึ่งรอบก่อนเริ่มตอบ 3,796 token คือคำนวณ 14 เท่าของ 266

ผลรวมคือ **ภาพใหญ่ขึ้น 2 เท่า (ด้านละ) → token 4 เท่า → attention 16 เท่า → VRAM และเวลาโตแบบไม่เป็นเส้นตรง** นี่คือเหตุผลที่ (ก) collator ของคนเขียน library ตั้งค่าย่อภาพเป็น default เพื่อไม่ให้ OOM (ข) เราเจอ CUDA OOM กับ MoE บน Vast.ai (บั๊กข้อ 7) เมื่อป้อนภาพเต็ม (ค) max_length 10k-13k token ของ t02 ถูกกินไปโดยภาพเกือบ 4k token ก่อนจะถึง JSON ที่ต้องตอบ และ (ง) ทำไมการให้ cv2 crop เฉพาะบริเวณคานแล้วส่งให้ VLM (บทที่ 3 ข้อสรุป hybrid) จึงคุ้ม: ตัดครึ่งหน้าทิ้งได้ = token ลดครึ่ง = attention ลด 4 เท่า

🎨 **ภาพที่จะวาดใน HTML:** เครื่องคิดเลข token: ช่องใส่กว้าง×สูงของภาพ (ค่าเริ่มต้น 3309×2339), สไลเดอร์ max_pixels (0.25M → 8M, มีขีดที่ "default 1.0M" และ "ของเรา ~3M"), patch size 14 และ merge 2×2 แสดงเป็นกริดทาบภาพจริง ผลลัพธ์แสดงแบบเรียลไทม์: ขนาดหลัง resize, จำนวน token, จำนวนคู่ attention ($N^2$), KV cache (MB) ตามพารามิเตอร์ $L, n_{kv}, d_{head}$ ที่แก้ได้ และแท่งเทียบสองสถานการณ์ "train (512px)" กับ "inference" ที่ยาวต่างกัน 14 เท่า พร้อมภาพ crop ของป้าย "B1" ที่ความละเอียดทั้งสองแบบให้เห็นว่าอ่านออก/ไม่ออก

---

## 4.9 เชื่อมกับงานของเรา

- **บั๊กข้อ 1 (14 เท่า)** = หัวข้อ 4.8 ทั้งหัวข้อ สาเหตุลึกคือ ViT แบบ dynamic resolution ทำให้ "จำนวน token" เป็นฟังก์ชันของขนาดภาพ ซึ่งต่างจาก CNN/ViT ยุคก่อนที่ resize ทุกภาพเป็น 224 ตายตัว ความยืดหยุ่นนี้ดีมาก แต่ทำให้ค่าที่ไม่ได้ตั้ง (บั๊กข้อ 5) ในสองที่ (collator กับ processor ตอน inference) สร้าง distribution สองแบบได้โดยไม่มีใครเห็น
- **บั๊กข้อ 6 (คำเตือน ≥ 1,024 image token)** = ขีดจำกัดทางกายภาพของ patch 14-16 px: ถ้าหน้าแบบทั้งหน้าถูกย่อจนเหลือ 266 token ตัวหนังสือสูง 3 px ไม่มี encoder ไหนอ่านออก ไม่ใช่เรื่องความฉลาดของโมเดล
- **บั๊กข้อ 7 (MoE + OOM)** = ค้ากำลังสองของ attention และ KV cache ที่โตตาม token ในหัวข้อ 4.8 ขั้นที่ 4 การใช้ Qwen3.6-35B-A3B ที่ active แค่ 3B ช่วยเรื่อง FLOPs ของ FFN แต่ **ไม่ช่วย** เรื่อง KV cache ซึ่งขึ้นกับจำนวนชั้นและ token ไม่ใช่จำนวน expert
- **t04 Purson (InternVL3 ล้มจาก crop_to_patches)** = อีกรูปแบบของ dynamic resolution: InternVL ตัดภาพใหญ่เป็นหลาย tile ขนาดคงที่ (crop to patches) แทนที่จะรับภาพยาวต่อเนื่องแบบ Qwen config ที่ผิดจึงเปลี่ยนจำนวน tile และจำนวน token ต่อภาพ เป็นบทเรียนว่าแต่ละตระกูล VLM มี "กติกาแปลงภาพเป็น token" ไม่เหมือนกัน ต้องอ่าน preprocessor ก่อนเทรนเสมอ
- **t02 freeze vision tower** = transfer learning (4.5): เชื่อว่า SigLIP/ViT ที่ pretrain มาแล้ว "เห็น" พอ ปรับเฉพาะภาษา สมมติฐานนี้สมเหตุสมผลเมื่อภาพเข้าถูกต้อง แต่ถ้าภาพถูกย่อจนอ่านไม่ออก การ freeze หรือไม่ก็ไม่ต่างกัน ต้องแก้ 4.8 ก่อน
- **cv2 ใน pattern_recognition.py** = feature ชั้น 1-3 ของ CNN ที่ทำด้วยมือ (edge, เส้นคู่, ไอคอนซ้ำ) และ template bank = "ชั้น 4" ที่ต้องเก็บทุกสำนักวาดเพราะไม่มีการประกอบจากชิ้นส่วน (4.4) นี่คือคำอธิบายทางทฤษฎีว่าทำไม bank ต้องโตเรื่อย ๆ และทำไม dedup ด้วย NCC จึงหลอกได้
- **pass0 classify หน้าใน t03** = งานที่ CLIP-style encoder ทำได้ดีที่สุด (จำแนกทั้งภาพ) ต่างจาก pass2 ที่ต้องอ่านรายละเอียด token ต่อ token ทั้งสองงานควรได้จำนวน token ต่างกัน: classify ใช้ภาพย่อได้ ถอดรายการต้องภาพใหญ่ การแยก pass จึงเป็นการแยกงบ token ไปในตัว

---

## 4.10 ระดับนักวิจัย: คำถามที่ยังเปิดอยู่

1. **CNN ตายแล้วจริงหรือ** ConvNeXt (Liu et al. 2022) [22] แสดงว่าถ้าเอา trick การเทรนของ ViT (AdamW, augmentation, LayerNorm, kernel ใหญ่ 7×7) มาใส่ ResNet ธรรมดา จะได้ผลเทียบเท่า Swin Transformer บน ImageNet และดีกว่าใน detection/segmentation คำถามที่ยังเถียงกันคือ ความได้เปรียบของ ViT มาจาก attention จริง ๆ หรือมาจากวิธีเทรนที่ดีกว่า ซึ่งกระทบการเลือก vision encoder ของ VLM สำหรับเอกสารความละเอียดสูง
2. **Visual token ซ้ำซ้อนแค่ไหน** FastV (Chen et al. 2024) [23] พบว่าใน LLaVA ตัด visual token ครึ่งหนึ่งทิ้งหลังชั้นที่ 2 โดยดู attention แทบไม่เสียความแม่น และ survey ของ Shao et al. (2025, TMLR 2026) [24] รวมวิธีบีบ token หลายสิบวิธี (ตัดตามความสำคัญ รวมตามความคล้าย ตัดตาม query) ประเด็นสำหรับเราคือหน้าแบบก่อสร้างมีพื้นที่ขาว 80% (token ที่แทบไม่มีข้อมูล) แต่ 20% ที่เหลือคือตัวหนังสือเล็กที่ตัดไม่ได้เลย งานพวกนี้ทดสอบบนภาพธรรมชาติเป็นหลัก ยังไม่มีใครตอบชัดว่าใช้กับแบบวิศวกรรมได้ไหม
3. **Patch 14 px คือขีดจำกัดของเอกสาร** Qwen3-VL [20] แนะนำ DeepStack ที่ส่ง feature จากหลายชั้นของ ViT เข้าหลายชั้นของ LLM เพื่อรักษารายละเอียดโดยไม่เพิ่ม token คำถามเปิดคือสำหรับตัวหนังสือสูง 20 px บนแบบ (ประมาณ 1.4 patch) เราต้องการ token มากขึ้น หรือ feature ที่ละเอียดขึ้นต่อ token
4. **Inductive bias กลับมาในรูปใหม่** Raghu et al. [16] พบว่า ViT ที่ข้อมูลน้อยเรียน local attention ไม่ได้ดี งาน 2025-2026 หลายชิ้น (เช่น ViT-5 ที่ปรับ ViT สำหรับกลางทศวรรษ 2020) พยายามใส่ bias กลับแบบเบา ๆ สำหรับ dataset ขนาด ~1,000 ตัวอย่างต่อ fold แบบ t05 ของเรา คำถามคือควร freeze encoder (เชื่อ bias จาก pretrain) หรือ fine-tune encoder ด้วย LoRA เล็ก ๆ บนแบบก่อสร้างโดยเฉพาะ ยังไม่มีคำตอบทั่วไป ต้องวัดด้วย leave-one-out ของเราเอง

---

## 4.11 แบบฝึกหัด

**ข้อ 1 (คำนวณ)** ภาพ 3309×2339 ถ้าใช้ max_pixels ปริยาย (28×28×1280) จะได้ token ประมาณกี่ตัว และภาพจะถูกย่อเหลือประมาณกี่พิกเซลด้านยาว

<details><summary>เฉลย</summary>

สัดส่วนย่อ $s = \sqrt{1{,}003{,}520 / 7{,}739{,}751} \approx 0.36$ → ประมาณ $1191 \times 842$ → ปัดลงเป็นพหุคูณ 28: $1176 \times 840$ → $42 \times 30 = 1{,}260$ token ด้านยาวเหลือราว 1,176 px เส้นคู่คาน 21 px จะเหลือ ~7.5 px ตัวหนังสือ 20 px เหลือ ~7 px อยู่ในเขต "อ่านออกบ้าง"

</details>

**ข้อ 2 (คิด)** ถ้าจะให้ train และ inference มี distribution เดียวกัน ควรแก้ที่ collator (เพิ่มเป็น 3,796) หรือแก้ที่ inference (ลดเป็น 266) ให้เหตุผลทั้งสองด้านและตอบว่าจะเลือกอะไร

<details><summary>เฉลย</summary>

ลด inference เป็น 266 = สม่ำเสมอแต่อ่านตัวหนังสือไม่ออก (ผิดทั้งคู่อย่างสม่ำเสมอ) เพิ่ม collator เป็น ~3,800 = ถูกต้องแต่ VRAM ตอนเทรนโตมาก (attention ~200 เท่า KV cache 14 เท่า) ต้องลด batch/ใช้ gradient checkpointing/ตัด max_length คำตอบที่สมเหตุสมผลคือเพิ่ม collator ให้ ≥ 1,024 token ตามคำเตือนของ Qwen และตั้ง max_pixels **ค่าเดียวกัน** ในทั้งสองที่อย่างชัดแจ้ง (ไม่ปล่อย default) แล้ววัด recall ซ้ำ

</details>

**ข้อ 3 (รันโค้ด)** ดัดแปลง `qwen_tokens()` ในหัวข้อ 4.8 ให้พิมพ์จำนวน token ของภาพครึ่งหน้า (1655×2339) และหนึ่งในสี่หน้า (1655×1170) ที่ max_pixels 3M แล้วเทียบว่าถ้า cv2 crop เฉพาะบริเวณคานที่ใช้พื้นที่ 1/4 ของหน้า จะประหยัด attention กี่เท่า

<details><summary>เฉลย</summary>

ครึ่งหน้า ≈ 1652×2324 → 59×83 = 4,897 token (ยังต่ำกว่าเพดาน 3M px จึงไม่ถูกย่อ) หนึ่งในสี่ ≈ 1652×1176 → 59×42 = 2,478 token เทียบกับเต็มหน้าที่ถูกย่อเหลือ 3,796: crop 1/4 ได้ 2,478 token แต่ **ความละเอียดเต็ม** (ไม่ถูกย่อ) attention ลด $(3796/2478)^2 \approx 2.3$ เท่า และตัวหนังสือคมกว่าเดิม 1.6 เท่า นี่คือเหตุผลเชิงตัวเลขของ hybrid

</details>

**ข้อ 4 (คำนวณ)** ViT-Base/16 บนภาพ 384×384 ได้ token กี่ตัว และ attention matrix ต่อ head ใหญ่กว่าที่ 224×224 กี่เท่า

<details><summary>เฉลย</summary>

$(384/16)^2 = 576$ token (+1 CLS) เทียบ 196 ที่ 224 → attention $(577/197)^2 \approx 8.6$ เท่า ทั้งที่พิกเซลเพิ่มแค่ 2.9 เท่า

</details>

**ข้อ 5 (คิด)** ทำไม skip connection ของ ResNet และ residual stream ของ Transformer ถึงเป็นแนวคิดเดียวกัน และมันเกี่ยวอะไรกับการที่ LoRA (บทที่ 8) "เสริมแผ่นเหล็กบางบนคานเดิม" ได้

<details><summary>เฉลย</summary>

ทั้งสองคือ $y = x + F(x)$: ทุกชั้นบวก "ส่วนต่าง" ลงบนสัญญาณเดิม ไม่ได้แทนที่ LoRA ทำแบบเดียวกันในระดับพารามิเตอร์: $W' = W + BA$ บวกส่วนต่างอันดับต่ำลงบนน้ำหนักเดิมโดยไม่แตะ $W$ โครงสร้างที่ "บวกทับ" นี้คือสิ่งที่ทำให้เพิ่มความสามารถได้โดยไม่ทำลายของเดิม เหมือนเสริมแผ่นเหล็กแทนหล่อคานใหม่

</details>

---

## สรุปบทนี้ใน 5 บรรทัด

1. Convolution layer คือ Sobel ที่ตัวเลข 9 ตัวเป็นตัวแปรให้ gradient descent หา และเมื่อเทรนบนภาพจริง ชั้นแรกก็เรียนได้ตัวหาขอบเหมือน Sobel เอง
2. ซ้อนหลายชั้น + pooling ทำให้ receptive field โตและได้ลำดับชั้น edge → texture → part → object ซึ่งเป็น "template ของ template" ที่ทน scale/สำนักวาดกว่า template พิกเซลของ cv2
3. LeNet (1998) → AlexNet (2012, GPU + ImageNet) → VGG (3×3 ลึก) → ResNet (2015, skip connection แก้ vanishing gradient) และ transfer learning ทำให้เราไม่ต้องเทรนจากศูนย์ (t02 freeze vision tower)
4. ViT ตัดภาพเป็น patch (16 หรือ 14 px) → flatten → linear projection (= convolution ชั้นเดียว) → token ป้อน Transformer มี inductive bias น้อยจึงต้องการข้อมูลมาก CLIP เชื่อมภาพกับภาษาและเป็นต้นตระกูลของ encoder ใน VLM
5. Qwen2-VL: patch 14 + merge 2×2 = 28 px ต่อ token (Qwen3-VL/3.6: patch 16 → 32 px) หน้าแบบเต็ม 3309×2339 = 9,912 token, inference ของเรา 3,796 (73×52), collator 512 px ≈ 266 ต่างกัน 14 เท่า และ token คือ VRAM (KV cache เชิงเส้น) และเวลา (attention กำลังสอง)

---

## ที่มาและอ่านต่อ

| # | แหล่ง | ประเภท | ทำไมควรอ่าน | URL |
|---|---|---|---|---|
| 1 | LeCun, Y., Bottou, L., Bengio, Y., Haffner, P. (1998). "Gradient-Based Learning Applied to Document Recognition." Proc. IEEE 86(11): 2278-2324 | paper | LeNet-5 ต้นฉบับ CNN ที่เทรน end-to-end บนเอกสาร (งานใกล้เรามาก) | https://gwern.net/doc/ai/nn/cnn/1998-lecun.pdf |
| 2 | Krizhevsky, A., Sutskever, I., Hinton, G.E. (2012). "ImageNet Classification with Deep Convolutional Neural Networks." NeurIPS 25 | paper | AlexNet: GPU + ImageNet + ReLU + dropout จุดเริ่มยุค deep learning | https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks |
| 3 | Simonyan, K., Zisserman, A. (2014). "Very Deep Convolutional Networks for Large-Scale Image Recognition" | paper (arXiv 1409.1556) | ทำไม 3×3 ซ้อนลึกดีกว่า kernel ใหญ่ | https://arxiv.org/abs/1409.1556 |
| 4 | He, K., Zhang, X., Ren, S., Sun, J. (2015). "Deep Residual Learning for Image Recognition" | paper (arXiv 1512.03385) | skip connection, 152 ชั้น, top-5 3.57% | https://arxiv.org/abs/1512.03385 |
| 5 | Zeiler, M.D., Fergus, R. (2013). "Visualizing and Understanding Convolutional Networks" | paper (arXiv 1311.2901) | ภาพจริงของ feature hierarchy ในแต่ละชั้น | https://arxiv.org/abs/1311.2901 |
| 6 | Olah, C., Mordvintsev, A., Schubert, L. (2017). "Feature Visualization." Distill | article (interactive) | ภาพ interactive ของ edge → texture → part → object | https://distill.pub/2017/feature-visualization/ |
| 7 | Girshick, R., Donahue, J., Darrell, T., Malik, J. (2013). "Rich feature hierarchies for accurate object detection and semantic segmentation" | paper (arXiv 1311.2524) | R-CNN ต้นตระกูล two-stage detector | https://arxiv.org/abs/1311.2524 |
| 8 | Redmon, J., Divvala, S., Girshick, R., Farhadi, A. (2015). "You Only Look Once: Unified, Real-Time Object Detection" | paper (arXiv 1506.02640) | YOLO: detection เป็น regression ครั้งเดียว 45 fps | https://arxiv.org/abs/1506.02640 |
| 9 | Carion, N. et al. (2020). "End-to-End Object Detection with Transformers" | paper (arXiv 2005.12872) | DETR: set prediction ไม่ต้องมี NMS/anchor | https://arxiv.org/abs/2005.12872 |
| 10 | Stanford CS231n, "Convolutional Neural Networks" course notes | docs/course | receptive field, stride, padding, สูตร 1+2L อธิบายละเอียดพร้อมภาพ | https://cs231n.github.io/convolutional-networks/ |
| 11 | Yosinski, J., Clune, J., Bengio, Y., Lipson, H. (2014). "How transferable are features in deep neural networks?" NeurIPS | paper (arXiv 1411.1792) | หลักฐานว่าชั้นต้นทั่วไป ชั้นท้ายเฉพาะงาน = รากของ freeze/fine-tune | https://arxiv.org/abs/1411.1792 |
| 12 | Weng, L. (2017-2018). "Object Detection for Dummies" Part 1-4. Lil'Log | blog | ไล่จาก HOG ถึง R-CNN family ถึง YOLO/SSD แบบเข้าใจง่าย | https://lilianweng.github.io/posts/2018-12-27-object-recognition-part-4/ |
| 13 | Ronneberger, O., Fischer, P., Brox, T. (2015). "U-Net: Convolutional Networks for Biomedical Image Segmentation" | paper (arXiv 1505.04597) | encoder-decoder + skip ที่ทำ segmentation ได้จากข้อมูลน้อย | https://arxiv.org/abs/1505.04597 |
| 14 | Kirillov, A. et al. (2023). "Segment Anything" | paper (arXiv 2304.02643) | SAM: 1.1B mask, 11M ภาพ, promptable zero-shot segmentation | https://arxiv.org/abs/2304.02643 |
| 15 | Dosovitskiy, A. et al. (2020). "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale" | paper (arXiv 2010.11929) | ViT ต้นฉบับ: patch 16×16, ต้องการข้อมูลมาก, inductive bias | https://arxiv.org/abs/2010.11929 |
| 16 | Raghu, M., Unterthiner, T., Kornblith, S., Zhang, C., Dosovitskiy, A. (2021). "Do Vision Transformers See Like Convolutional Neural Networks?" | paper (arXiv 2108.08810) | ViT รวมข้อมูล global ตั้งแต่ชั้นต้น ต่างจาก CNN | https://arxiv.org/abs/2108.08810 |
| 17 | Touvron, H. et al. (2020). "Training data-efficient image transformers & distillation through attention" ICML 2021 | paper (arXiv 2012.12877) | DeiT: ViT เทรนบน ImageNet อย่างเดียวได้ด้วย distillation | https://arxiv.org/abs/2012.12877 |
| 18 | Radford, A. et al. (2021). "Learning Transferable Visual Models From Natural Language Supervision" | paper (arXiv 2103.00020) | CLIP: contrastive บน 400M คู่ภาพ-ข้อความ, zero-shot | https://arxiv.org/abs/2103.00020 |
| 19 | Wang, P., Bai, S., Tan, S. et al. (2024). "Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution" | paper (arXiv 2409.12191) | naive dynamic resolution, patch 14, MLP merge 2×2, ตัวอย่าง 224×224 → 66 token | https://arxiv.org/abs/2409.12191 |
| 20 | Qwen Team (Bai, S. et al.) (2025). "Qwen3-VL Technical Report" | paper (arXiv 2511.21631) | SigLIP-2 encoder, DeepStack, interleaved-MRoPE, รุ่น dense/MoE ที่เราใช้ | https://arxiv.org/abs/2511.21631 |
| 21 | HuggingFace transformers, `image_processing_qwen2_vl.py` (`smart_resize`, min_pixels/max_pixels) | docs/code | โค้ดจริงที่ตัดสินจำนวน token: factor=28, max_pixels=28×28×1280 | https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen2_vl/image_processing_qwen2_vl.py |
| 22 | Liu, Z. et al. (2022). "A ConvNet for the 2020s" | paper (arXiv 2201.03545) | ConvNeXt: CNN ที่เทรนแบบใหม่สู้ Swin ได้ | https://arxiv.org/abs/2201.03545 |
| 23 | Chen, L., Zhao, H. et al. (2024). "An Image is Worth 1/2 Tokens After Layer 2: Plug-and-Play Inference Acceleration for Large Vision-Language Models." ECCV 2024 | paper (arXiv 2403.06764) | FastV: ตัด visual token ครึ่งหนึ่งหลังชั้น 2 โดยแทบไม่เสียความแม่น | https://arxiv.org/abs/2403.06764 |
| 24 | Shao, K. et al. (2025). "A Survey of Token Compression for Efficient Multimodal Large Language Models." TMLR 2026 | survey (arXiv 2507.20198) | แผนที่วิธีบีบ visual token ทั้งหมด ณ 2026 | https://arxiv.org/abs/2507.20198 |
| 25 | 3Blue1Brown (2022). "But what is a convolution?" | video | ภาพเคลื่อนไหวของ convolution สำหรับทบทวนก่อนอ่าน 4.1 | https://www.youtube.com/watch?v=KuXjwB4LzSA |
