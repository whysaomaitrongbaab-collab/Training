# proof 04 — destrier-vllm / destrier-sglang บนการ์ดจริง (3 ต.ค. 69)

คำสั่งมะขาม (att1235): เช่าการ์ดทดสอบ GO.bat ข้อ 2/3 · จดละเอียด · คืนการ์ด
การ์ด: vast 53971544 RTX PRO 6000 (sm120, 96 GB) ฮ่องกง $1.268/ชม. · 12:36–15:03 · ใช้ไป ~$3.81
ข้อมูลดิบทั้งหมดอยู่ในโฟลเดอร์ `04_vllm_sglang_บนการ์ด/` (out/ logs/ scripts/ fingerprint/)

## คำตอบ 3 ข้อ

**1. เปิดได้จริงไหม — เปิดได้ทั้งคู่ หลังแก้ชุด CUDA · แต่ GO.bat ยังใช้วันจริงไม่ได้ เพราะโมเดล merged ไม่อยู่บน HF**
- image ของ vast (cuda-12.8.1) มี nvcc 12.8 · FlashInfer/DeepGEMM คอมไพล์ kernel ของ sm120 ตอนเปิด ต้อง ≥12.9 →
  vLLM: "No supported CUDA architectures found for major versions [12]" · SGLang: "NVCC version must be at least 12.9"
- ชี้ไป nvcc ของ venv (13.4.92) ไม่ได้ เพราะ torch 2.13 ตรึง runtime header 13.0.96 และ CCCL บังคับ major.minor ตรงกัน
- ทางที่ผ่าน: ตรึง `nvidia-cuda-nvcc/crt/nvvm==13.0.88` + `nvidia-cuda-cccl==13.0.85` + symlink `lib*.so` และ `lib64`
  → ใส่ใน Constistant `presentation.py` แล้ว (`CUDA13_TOOLKIT_PINS` / `SERVE_ONSTART_FIX` / `launch_cmd` ตั้ง CUDA_HOME)
- **พิสูจน์ทางแก้ production แล้ว:** venv ใหม่ที่ลงแบบเดียวกับ onstart + คำสั่งที่ `presentation.launch_cmd()` สร้าง
  (เปลี่ยนแค่ path โมเดล/venv) + ย้าย cache FlashInfer ออกให้คอมไพล์ใหม่ทั้งหมด → พร้อมใน 576 วิ · ด่าน D ผ่าน
- เวลาเปิดถึงพร้อม: vLLM 170 วิ (มี cache) / 576 วิ (cache ว่าง) · SGLang 65 วิ (+คำขอแรก 44 วิ คอมไพล์ sampling)
- ⛔ `dacarokann/destrier-merged` ไม่มีบน HF (ไม่มี write token) → ต้อง merge + push ก่อนใช้ข้อ 2/3 จริง

**2. เร็วขึ้นกี่เท่า**

| | บ้าน 83b8e52c ทั้งหลัง (29 หน้า) | pass0 ต่อหน้า | section หน้า 22 |
|---|---|---|---|
| Unsloth production (adapter เดิม) | 16,964 วิ (4 ชม. 43 นาที) | 88 วิ | — |
| Unsloth บนการ์ดนี้ (adapter ซ่อม) | ไม่วัด | 16–25 วิ | 170 วิ · 20 ตัวอักษร/วิ |
| **vLLM** | **298.6 วิ (~57×)** | 1.6 วิ | 3–9 วิ · ~430 ตัวอักษร/วิ |
| **SGLang** | **382.1 วิ (~44×)** | 2.7 วิ | 8.7 วิ |

- เทียบบนการ์ดเดียวกันต่อคำขอ: pass0 ~10× · section ~20× · ตัวเลข 57× รวมโชคการ์ด/torch ของรอบ production ด้วย
  (pass0 production 88 วิ vs Unsloth การ์ดนี้ 18.5 วิ = ต่างกันเอง 4.7×)
- ถอดรหัส ~120–165 token/วิ ทั้งสองตัว · vLLM เร็วกว่า SGLang ~20% ทั้งบ้าน (prefill ภาพเร็วกว่า)
- **prefix cache ไม่ช่วยงานเรา:** SGLang โดน cache แค่ 6/292 prefill — prompt ขึ้นต้นด้วยภาพ (ลำดับตอนเทรน)
  ภาพทุกหน้าต่างกัน prefix จึงไม่ซ้ำ · เหตุผลที่ README เคยแนะนำ SGLang (RadixAttention) ใช้ไม่ได้กับ pipeline นี้

**3. ผลอ่านเท่าเดิมไหม — ไม่แย่กว่าเดิม · precision ดีขึ้นชัด**
- ด่าน A: expert เปลี่ยน 80/82 (2 = mtp ไม่อยู่ใน adapter) · B: merge ตรง `round_bf16(W+ΔW)` เป๊ะ (0.0000)
  — คลาด 0.1194 เทียบ W+ΔW คือราคาของ bf16 ไม่ใช่ merge ผิด · C: 0.9956 vs ค่าพื้นฐาน Unsloth↔transformers 0.9945 → ผ่าน
- ด่าน D (logprobs ตัวเสิร์ฟ vs merged): vLLM top-5 5/5 แต่ top-1 สลับ (`{"` กับ ```` ``` ````) Δ 0.678 ·
  SGLang top-1 ตรง Δ 0.429 · vLLM venv production top-1 ตรง Δ 0.192 — ใต้ JSON grammar ไม่มีผล
- เทียบเฉลย 83b8e52c (`score_83b8e52c.txt`, หน้า 19–25):

| | JSON ผ่าน | มาร์คเจอ/เฉลย | recall | precision |
|---|---|---|---|---|
| production (Unsloth + adapter เดิมที่ปนผิด) | 16/16 | 42/52 | 0.81 | 0.63 |
| vLLM | 16/16 | 41/52 | 0.79 | 0.85 |
| SGLang | 18/18 | 43/52 | 0.83 | 0.83 |

- ⚠️ เปลี่ยนสองตัวแปรพร้อมกัน (adapter ซ่อมแล้ว + ตัวเสิร์ฟ/merge bf16) แยกไม่ได้ว่าดีขึ้นเพราะอะไร · adapter ซ่อมยังไม่ผ่าน Stage 1
- **sampling แกว่งมาก** (`repeat_variance.txt`, เซิร์ฟเวอร์เดียว ภาพเดียว 3 รอบ): plan_beam หน้า 20 ได้ 56 / 51 / 22 ชิ้น
  (เฉลย 59) · section หน้า 22 มาร์คตรง 6/6, 4/6, 4/6 · plan_footing นิ่ง 8/10 ทุกรอบ → ความต่างรายหน้าระหว่าง
  vLLM กับ SGLang อยู่ในช่วงแกว่งของ temperature 0.7 · บ้านจากเน็ต: มาร์คตรงกันข้ามตัวเสิร์ฟ Jaccard 0.45–0.57

## บ้านจากเน็ต 3 หลัง (ไม่อยู่ใน json_แก้ไขแล้ว — ยืนยันด้วย dHash เทียบ PDF 53 หลังใน image/)
แบบบ้านเพื่อประชาชน กรมโยธาฯ (office.dpt.go.th/construction/th/house01) · sha256 ใน `webpdf_sha256.txt`
· ตัดทิ้ง: ไทยเป็นสุข 5 = บ้าน_ใหญ่_2ชั้น_02 (27/27 หน้า) · ไทยเป็นสุข 1 = บ้าน_เล็ก_1ชั้น_15 (12/12)

| บ้าน | vLLM | SGLang |
|---|---|---|
| 13226 แบบประหยัด 1 · 1 ชั้น 14 หน้า | 218 วิ · JSON 21/22 · gridline วน | 192 วิ · 21/21 |
| 13244 แบบประหยัด 2 · 1 ชั้นยกใต้ถุน 18 หน้า | 530 วิ · 31/32 · gridline วน | 282 วิ · 29/30 · gridline วน |
| 13250 ไทยเป็นสุข 4 · 2 ชั้น 25 หน้า | 557 วิ · 40/41 · ชนเพดาน 3 ตัว | 469 วิ · 41/41 · ชนเพดาน 1 ตัว |

**ปัญหาเด่นของรอบนี้ — ชนเพดาน 9,000 token บนบ้านที่ไม่เคยเห็น:** gridline เขียน ~18,470 ตัวอักษร ท้ายวน
`…บ้าน_เล็ก_1ชั้น_17/บ้าน_เล็ก_1ชั้น_` → ไม่มี grid master → pass3 ข้ามทั้งบ้าน · section (vLLM บ้าน 2 ชั้น) 27,895 ตัวอักษร
ท้ายวน `view505_sanitary_plan (_view505_sanitary_plan.json)` · เกิดแบบสุ่ม (SGLang ที่ 13226 ไม่วน) บนทั้งสองตัวเสิร์ฟ
**ต้นเหตุอยู่ที่ข้อมูลเทรน** → `json_แก้ไขแล้ว/สิ่งที่ต้องแก้.md` ข้อ 68: คำตอบที่สอน 938/1034 แถว (fold0) มีชื่อบ้านเทรน
ผ่าน `source_image`/`source_pages`/`grid_source` · 335/1034 มีบันทึกสคริปต์ relabel 28 ส.ค. ใน warnings

## สิ่งที่ฉันพลาดระหว่างทาง (บทเรียน)
- ตัวเฝ้ารุ่นแรกใช้ `head -1` ได้ banner ของ vast → มองไม่เห็น FAIL_download · แก้เป็นบรรทัด `MARKERS:`
- `pgrep -f "bash phaseA.sh"` เจอ shell ของ ssh ตัวเอง → kill ตัวเองกลางคำสั่ง
- เปิด runall ซ้อนตัวที่สองขณะตัวแรกยังรอ → kill ทิ้ง
- verify B ข้ามเงียบ (แกน expert กลับด้าน) แต่ขึ้น "A+B ผ่าน" → แก้ verify ให้หาไม่เจอ = ไม่ผ่าน
- จด "9000 token ได้แค่ 378 ตัวอักษร" — 378 คือความยาวข้อความเตือนที่ worker ใส่แทน raw ตอนชนเพดาน
  (`calls.jsonl` ช่อง chars ของคำขอที่ล้มจึงไม่ใช่ความยาวจริง — ความยาวจริงอยู่ในข้อความเตือนใน result.json)

## สร้างซ้ำ
- `scripts/phaseA.sh` (โหลด → ซ่อม `fix_destrier_layout.py` → merge → verify A/B/C) · `scripts/phaseB.sh <engine> [house]`
- `scripts/launch_*.txt` สร้างจาก `presentation.launch_cmd()` ตัวจริง · เวอร์ชันครบใน `logs/freeze_*.txt`
- `fingerprint/mrg.pt` = fingerprint ของ merged รอบนี้ (adapter ซ่อม sha256 7e57a635…37ea) · merge ซ้ำแล้วจะใช้เป็น ref
  ของด่าน D ได้ก็ต่อเมื่อ `--compare` ใหม่กับมันผ่าน — ยังไม่ได้พิสูจน์ว่า merge ซ้ำได้ไฟล์เดิมทุก byte
