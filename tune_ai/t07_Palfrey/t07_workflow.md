# t07 workflow — Palfrey

รอบทูนถัดจาก Destrier (t05) · เขียน 3 ต.ค. 69 หลังทดสอบตัวเสิร์ฟเร็ว (`t05_Destrier/proof/04_vllm_sglang_บนการ์ด.md`)
คำสั่งมะขาม (att1235): "ทำเลย แต่แค่สร้าง op_t07" → ไฟล์นี้ + `sanitize_labels.py` + skill `op_t07` · **ยังไม่เทรน ยังไม่เช่าการ์ดเทรน**
เรียกใช้ด้วย `op_t07` (skill อยู่ `.claude/skills/op_t07/SKILL.md`) — รันตามลำดับข้างล่าง ทุกด่านมีเกณฑ์ผ่าน/ไม่ผ่านชัด

## ทำไมต้องมี t07 — ปัญหาที่วัดได้จริง ไม่ใช่ความรู้สึก

| # | ปัญหา | หลักฐาน | แก้ที่ |
|---|---|---|---|
| 1 | โมเดลจำชื่อไฟล์บ้านเทรน → บ้านที่ไม่เคยเห็นวนพ่นจนชนเพดาน 9,000 token (gridline ไล่นับ `บ้าน_เล็ก_1ชั้น_17_หน้า315/316/317`) | proof/04 · สิ่งที่ต้องแก้ ข้อ 68 · fold0 938/1034 แถวมีชื่อบ้าน | `sanitize_labels.py` (ทำแล้ว) |
| 2 | ประวัติการแก้ข้อมูลอยู่ในคำตอบที่สอน (วันที่, `added_…_by_user`, บันทึก relabel 28 ส.ค. 183 ไฟล์) → โมเดลแต่ง "Nothing else in this file changed" | ข้อ 68 · fold0 335/1034 | `sanitize_labels.py` (ทำแล้ว) |
| 3 | grid master หลัง op_fix ใหญ่ขึ้น 6–13 เท่า (บ้าน 05: 10k → 122k ตัวอักษร) → ตัวอย่าง gridline เกิน MAX_LENGTH แน่ | ไดอารี่ 29 ก.ย. · json_แก้ไขแล้ว/README | วิธีสร้างตัวอย่าง gridline (ยังไม่ทำ) |
| 4 | prompt ขอ `source_image` เอง ทั้งระดับไฟล์และใน z_levels — โมเดลถูกบังคับให้เติมสิ่งที่มองไม่เห็นในภาพ | prompt ใน `t04_Purson/` | ตัดออกจาก prompt ตอนก็อป (ยังไม่ทำ) |
| 5 | ผลแกว่งมาก: plan_beam หน้าเดียวยิงซ้ำ 3 รอบได้ 56 / 51 / 22 ชิ้น | proof/04 `repeat_variance.txt` | ~~temperature~~ วัดแล้วแก้ไม่ได้ (proof/05 — ลดแล้วทั้งบ้านแย่ลง) → ข้อ 1–2 + อ่านหลายรอบโหวต |
| 6 | ฐานรากใน GT ใช้ field มิติ 3 ธรรมเนียมที่ขัดกัน + ส่วนใหญ่ไม่มีความหนา | ข้อ 67 | คนแก้ GT (Claude ไม่แตะ GT) — ไม่บล็อก t07 |

## ลำดับ (ห้ามสลับ — ด่านก่อนหน้าไม่ผ่าน ห้ามไปต่อ)

### ด่าน 0 — ก่อนแตะการ์ด (ฟรี)
- [ ] `onstart.sh` ของ t07 ตรึงเวอร์ชัน torch / unsloth / unsloth_zoo / peft / trl / transformers (Lesson 18 — t05 ไม่ได้ตรึง)
- [ ] ตั้ง `UNSLOTH_MOE_LORA_B_LAYOUT` ชัดทั้งตอนเทรนและตอนเสิร์ฟ — unsloth_zoo ≥ 2026.9.6 เทรนเป็น `rank_major` แต่ SERVE_ENV บังคับ `grouped_by_expert` (ต้นเหตุคลาสเดียวกับ e229403 ที่ปนผิด) · soup ต้องผ่าน `test_soup_layout.py`
- [ ] แก้ปัญหา 3: สร้างตัวอย่าง gridline ใหม่ (เสนอ: label เหลือ `x_lines/y_lines/z_levels` + ตัด chain/unassigned ออกจาก label หรือแยกเป็นตัวอย่างรายหน้า) แล้ว**วัด token ของตัวอย่างที่ยาวสุดจริง** — ห้ามลด MAX_LENGTH (ตัด JSON กลางทาง)
- [ ] ก็อป prompt จาก `t04_Purson/` มา `t07_Palfrey/prompts/` ตอนนี้เท่านั้น แล้วตัด `source_image` / `source_pages` ออกจาก schema ใน prompt (ปัญหา 4) — prompt กับ label ต้องตรงกัน

### ด่าน 1 — สร้าง dataset (ฟรี)
1. รันตัวสร้าง (ก็อป `t05_Destrier/training/build_t05_night.py` → `t07_Palfrey/build_t07.py` ชี้ prompt ใหม่ · fold/split เดิม)
2. ล้าง: `python t07_Palfrey/sanitize_labels.py <jsonl ทุกไฟล์> --out t07_Palfrey/data/`
3. **เกณฑ์ผ่าน:** ทุกไฟล์ `มีชื่อบ้านเทรน → 0 · บันทึกสคริปต์ → 0 · source_* → 0 · ไม่ใช่ JSON 0` และจำนวน element ไม่ลด (มี assert ในตัว)
   - ค่าอ้างอิงจากชุด t05 (3 ต.ค.): fold0 938→0 / 335→0 / 917→0 คำตอบสั้นลง 16.9% · pass24 สั้นลง 25.8%
4. วัด token ของตัวอย่างยาวสุดหลังล้าง (ภาพ + prompt + label) < MAX_LENGTH พร้อมเผื่อ

### ด่าน 2 — Phase 0 บนการ์ดถูก (rule_of_tune: ทดสอบบนการ์ดถูกก่อนเสมอ)
- โหลด + เทรน 10 step + บันทึก adapter + โหลดกลับ + ยิง 1 ภาพ · ดู `check_expert_lora` ขึ้น "✅ ทั้ง 80 ตัว grouped_by_expert"

### ด่าน 3 — เทรนจริง (เสียเงิน — ถามมะขามก่อนเช่า)
- 4 fold แบบ t05 · soup ด้วย `merge_adapters_soup.py` ตัวที่แก้แล้ว + `test_soup_layout.py`

### ด่าน 4 — merge + เสิร์ฟ + วัด (ใช้ชุดเครื่องมือของ proof/04)
- merge: `merge_lora_to_base.py` → `verify_merge.py` A/B/C → เสิร์ฟ vLLM ตาม preset `destrier-vllm` → ด่าน D
- วัด: `bench_house.py` บ้าน 83b8e52c + บ้านเน็ต 3 หลัง (PDF + sha256 ใน proof/04) + `micro --repeat 4`

## เกณฑ์ผ่าน t07 (ฐาน = Destrier ตัวซ่อมบน vLLM, proof/04 — ไม่ใช่ตัวที่ปนผิด)

| วัด | ฐาน (proof/04) | t07 ต้อง |
|---|---|---|
| 83b8e52c recall / precision (มาร์ค หน้า 19–25) | 0.79–0.83 / 0.83–0.85 | ≥ 0.79 / ≥ 0.83 |
| บ้านเน็ต: gridline ชนเพดาน 9,000 token | 3 ครั้งใน 6 รอบ (2 ตัวเสิร์ฟ × 3 หลัง) | **0 ครั้ง** ใน 3 หลัง × 3 รอบ |
| ชื่อบ้านเทรนในผลอ่านใดๆ (regex เดียวกับ `sanitize_labels.HOUSE`) | มี | **0** |
| ตัวอักษรจีน (`cjk` ใน calls.jsonl) | 0 | 0 |
| plan_beam หน้า 20 ยิงซ้ำ 4 รอบ (เฉลย 59) | 22–56 | ช่วงแคบลง + ค่าต่ำสุด ≥ 45 |

## ตอน deploy (หลังผ่าน)
- `Constistant/js/drawing/raw-extraction-import.js:516` หา grid master ด้วย `f?.source_pages` — t07 ไม่ส่งฟิลด์นี้แล้ว → เปลี่ยนเป็นหาจาก `pattern === 'gridline'` อย่างเดียว
- push merged ขึ้น HF (ต้องมี HF write token) แล้วชี้ preset `destrier-vllm` ไปที่ repo ใหม่
- temperature ใน `worker.py` ตามผลวัด (ดูหัวข้อถัดไป)

## temperature — ผลวัด 3 ต.ค. เย็น (`t05_Destrier/proof/05_temperature_บนการ์ด.md`)
- **คง 0.7** — ทั้งบ้าน 83b8e52c: 0.7 → recall 0.79 · 0.4 → 0.73 · 0.2 → 0.63 · 0 → 0.38 (gridline วนทุกบ้าน)
- ยิงทีละหน้า greedy ดูดีสุด (นิ่ง + มาร์คดี) แต่ทั้งบ้านแย่สุด → ปัญหา 5 (ผลแกว่ง) แก้ด้วย temperature ไม่ได้
  ทางที่เหลือ: t07 (ปัญหา 1–2 ทำให้ gridline วนอยู่) + อ่านหลายรอบโหวต (Constistant docs/research 2026-10-03)
- t07 ต้องวัด sampling ใหม่หลังเทรน (โมเดลใหม่ ค่าที่ดีสุดอาจย้าย) — วัดทั้งบ้านเสมอ ห้ามตัดสินจาก micro
