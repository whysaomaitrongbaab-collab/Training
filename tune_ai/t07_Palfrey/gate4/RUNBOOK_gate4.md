# RUNBOOK ด่าน 4 — t07 Palfrey: รวม 4 fold → merge → เสิร์ฟ vLLM → วัดผล

**สถานะ: ร่าง · UNTESTED — ยังไม่เคยรันบนการ์ดจริง (เขียน 11 พ.ย. 69)**
ทำหลังด่าน 3 ผ่านครบเท่านั้น (4 fold อยู่บน HF และตรวจ hash แล้ว) · **ห้ามเช่าการ์ดโดยไม่ถามมะขามก่อน** (Rule 4)

สรุปภาษาง่าย: เช่าการ์ด 1 ใบ (ดิสก์ใหญ่) → รวมผลเทรน 4 ชุดเป็นตัวเดียว → อบเข้าโมเดลหลัก → ตรวจว่าอบถูก →
เปิดตัวเสิร์ฟแบบเร็ว (vLLM) → ให้อ่านบ้านทดสอบ 4 หลัง หลังละ 3 รอบ → ดึงผลกลับคอม → ให้คะแนนเทียบของเดิม → คืนการ์ด
เวลาการ์ดรวม ~3.5–4.5 ชม. ราว $4–8 (ประมาณจากราคา 11 พ.ย. $1.19–1.70/ชม. — ยังไม่เคยวัดจริง) · วัด Destrier ซ้ำบนการ์ดเดียวกัน +~2 ชม. +$2–3

คำสั่งบน PC ทั้งหมดรันใน Git Bash (Bash tool) จากราก Training (`D:/00mk/steel project/training/Training`) · path ของ scp
ต้องเขียนแบบ `/d/...` (ถ้าเขียน `D:\...` scp จะเข้าใจว่า `D` คือชื่อเครื่อง)

## 0. ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | ทำอะไร | ทดสอบแล้วแค่ไหน |
|---|---|---|
| `vllm_build_t07.sh` | การ์ด: soup 4 fold → merge → ตรวจ A/B/C → tokenizer → เปิด vLLM → ด่าน D | `bash -n` ผ่าน · CR = 0 · ไม่เคยรัน |
| `run_bench_t07.sh` | การ์ด: 83b8e52c ×3 · บ้านเน็ต 3 หลัง ×3 · micro ×4 (ทุกคำขอ `PURSON_CV_MERGE=0`) | `bash -n` ผ่าน · ไม่เคยรัน |
| `stop_server.sh` | การ์ด: ปิด vLLM แล้วพิสูจน์ว่าหายหมด ก่อนเปิดตัวใหม่ (Lesson 24) | `bash -n` ผ่าน |
| `dl_destrier_merged.sh` | การ์ด (ทางเลือก): โหลด destrier-merged + ตรวจ sha256 ตาม proof/06 | `bash -n` ผ่าน |
| `gate_d_t07.py` | ด่าน D ตามเกณฑ์ที่ตัดสินแล้ว (ข้อ 6) | `--selftest` 9 ข้อผ่าน ด้วยตัวเลขจริงของ proof/04 · ไม่เคยยิงตัวเสิร์ฟ |
| `tok_parity.py` | Lesson 20: id ภาษาไทยของ merged ต้องเท่ากับ base | ลองบน PC (วัดซ้ำ 11 พ.ย. 01:4x): ผ่านกับ destrier_fixed · จับ Qwen2Tokenizer ได้ (14 → 18 token) · `--ids-ref` ที่แก้ id 1 ตัว = ไม่ผ่าน · บน PC ต้องตั้ง `TORCHINDUCTOR_CACHE_DIR` ไปที่อื่น (ค่าเดิมชี้ `.unsloth\studio` ที่ลิงก์เสีย — เรื่องของ PC ไม่เกี่ยวกับการ์ด) |
| `launch_vllm_palfrey.txt` · `launch_vllm_destrier.txt` | คำสั่งเปิด vLLM — สร้างจาก `presentation.launch_cmd` ตัวจริง | flag ตรงกับ proof/04 `launch_prodvllm.txt` ทุกตัว (ต่างแค่ path venv/โมเดล) · กับ `launch_vllm.txt` ของรอบวัดคุณภาพต่างแค่ที่อยู่ CUDA_HOME |
| `make_bundle_t07.py` | PC: ห่อทุกอย่างเป็น `ft_t07.tar` + sha256 | ลองบน PC ด้วย prompt t07 ตัวจริง (11 พ.ย. 01:32): 123 ไฟล์ (prompt 21) 104.3 MB · แตกแล้ว `BUNDLE_OK` · CR = 0 · worker หา organize.py/cv_scan.py เจอ · ไม่มี worker_config.json |
| `dryrun_bench_stub.py` | PC: ซ้อม bench ฟรีบน bundle ที่แตกแล้ว — โมเดลปลอมตอบแบบ t07 (ไม่มี `png`/`doc_page`) | 11 พ.ย.: house + micro exit 0 · ตัวให้คะแนนอ่านผลได้ · GRID MASTER ที่ worker ต่อท้าย = สูตร D4 ทุกไบต์ · **วัดแค่ท่อ ไม่ได้วัดคุณภาพ** |
| `score_house.py` | ให้คะแนน 83b8e52c เทียบเฉลย | สำเนาตรงตัวของ proof/04 (sha256 เท่ากัน) |
| `analyze_houses.py` | สรุปทุกบ้าน + ตัดสินตามตารางข้อ 9 | สำเนาดัดแปลงของ proof/05 (regex ทุกจำนวนชั้น) · ลองกับผลฐาน proof/04/05 แล้ว |

## 1. ก่อนเช่า (ฟรี บน PC) — ทุกข้อต้องผ่าน

1. ด่าน 3 จบจริง: `Palfrey_a..d` มี adapter ตัวสุดท้าย · `verify_hf_push.py` ผ่าน · sha256 ของ LFS บน HF = `sha256sum` ของ adapter บนการ์ดเทรน (Lesson 23)
2. `python -B tune_ai/test_soup_layout.py` ผ่าน (soup ฉบับ t07 มี `--fold-repo` / `--out-repo` แล้ว — วัดซ้ำ 11 พ.ย. 01:40 exit 0
   รวมข้อ 7e K=4 → r64 / alpha128) · ตั้ง `TMP`/`TEMP` ไปโฟลเดอร์ชั่วคราวก่อน (มันเขียนไฟล์ทดสอบลง temp)
3. `python tune_ai/t07_Palfrey/gate4/gate_d_t07.py --selftest` → `selftest ผ่าน 9 ข้อ`
4. ห่อ bundle (ต้องมี prompt ของ t07 ครบ 7 subtask + pass0 + `_common.md` แล้ว ไม่งั้นมันหยุดเอง):
   `python tune_ai/t07_Palfrey/gate4/make_bundle_t07.py "D:/00mk/steel project/training/t07_bench/gate4_bundle"`
   → ต้องขึ้น ✅ · ถ้าขึ้น "launch_vllm_*.txt ไม่ตรง" = flag ของ production เปลี่ยนตั้งแต่ 11 พ.ย. → สร้างไฟล์ launch ใหม่แล้วถามมะขามก่อนใช้
   (อย่าตั้ง `T07_DIR` — ตัวนั้นไว้ลองบน PC เท่านั้น)
   ห่อใหม่ทุกครั้งก่อนเช่า: `worker.py` ในก้อนคือไฟล์บนดิสก์ตอนห่อ (11 พ.ย. Constistant มี worker.py ที่ยังไม่ commit
   และมีคนแก้อยู่) — sha ของมันอยู่ใน `ft/MANIFEST.sha256` + สถานะ git อยู่ใน `ft/BUNDLE_INFO.txt`
   ซ้อม bench ฟรีบน PC (โมเดลปลอม ~3.5 นาที — จับ worker ที่พัง/ต้องใช้เน็ตก่อนเสียค่าการ์ด):
   `B="/d/00mk/steel project/training/t07_bench/gate4_bundle"; mkdir -p "$B/x" && tar -xf "$B/ft_t07.tar" -C "$B/x"`
   `python -B tune_ai/t07_Palfrey/gate4/dryrun_bench_stub.py "D:/00mk/steel project/training/t07_bench/gate4_bundle/x/ft" <โฟลเดอร์ออก>`
   → ต้องขึ้น `exit 0` ทั้งสองบรรทัด แล้ว `analyze_houses.py <โฟลเดอร์ออก>/out t07` ต้องรันจบ (ตัวเลขต่ำ = ปกติ โมเดลปลอม)
   ด่าน 3 เทรนด้วย `PIN_SET=t05` ก็ยังใช้ชุด A ในด่านนี้ได้ (อนุมาน: soup วัด layout จากตัวเลขเองแล้วเขียน grouped —
   destrier_fixed ที่เทรนด้วยชุด t05 ผ่าน A/B/C ด้วยชุด A มาแล้ว 3 ต.ค. / 8 พ.ย. ตาม proof/06)
5. มะขามตัดสิน **ก่อนเปิดดูผล** (ข้อ 9 และ 10): สถิติ 83b8e52c ใช้ **mean หรือ min** ของ 3 รอบ (ยังไม่ได้ตัดสิน) ·
   จะ push soup/merged ไหม public หรือ private · จะวัด Destrier ซ้ำบนการ์ดเดียวกันไหม (+$2–3)
6. token: มะขามสร้าง token **อ่านอย่างเดียว** ที่เห็นแค่ `Palfrey_a..d` (+ `destrier-merged` ถ้าจะวัดซ้ำ) · token เขียนแยกอีกตัว
   เฉพาะตอน push · ห้ามเอา token t44 ของ PC (เขียนได้ทุก repo) ขึ้นการ์ด (Lesson 22) · ห้ามวาง token ในแชต
7. เครดิต vast ≥ ~$10 (+$3 ถ้าวัดซ้ำ) — เครดิตหมด vast หยุดการ์ดทันที (billing credit-only)
8. ถ้าจะปล่อยข้ามคืน: ปิด sleep/hibernate ของคอมตอนเสียบไฟ (ตอนนี้ตั้งไว้ 3 ชม.) — `powercfg /change standby-timeout-ac 0` และ `powercfg /change hibernate-timeout-ac 0`
9. Unsloth: ด่านนี้ใช้ Unsloth แค่ตอน merge/ทำ fingerprint (เหมือนที่ทำ 8 พ.ย.) **ไม่ได้ใช้เป็นตัวเสิร์ฟ** — ถ้ามะขามหมายถึงห้ามใช้ทุกขั้นต้องบอกก่อนเช่า

## 2. สเปกการ์ด + เช่า

- RTX PRO 6000 96 GB (sm120) ตัวเดียวที่ทั้งสูตรผ่านมา · **ดิสก์ ≥ 400 GB** (base 72 + fold 15 + soup 15 + merged 67 + vLLM ~15 + destrier 72 ถ้าวัดซ้ำ)
- image `vastai/pytorch:cuda-12.8.1-auto` (torch 2.11.0+cu128 มากับ image ใน `/venv/main` — ไม่มี `python` บน PATH)
- หา offer: `python tune_ai/t07_Palfrey/offers_t07.py --n 1 --disk 400` (ตัวกรองเดียวกับ build_vllm_card + บัญชีดำ)
- เช่า (หลังมะขามอนุญาต):

```
vastai create instance <OFFER> --image vastai/pytorch:cuda-12.8.1-auto --disk 400 --ssh --direct --label t07-gate4 --raw --onstart-cmd "mkdir -p /workspace && export TORCH_CUDA_ARCH_LIST=12.0 && /venv/main/bin/python -m pip install -U unsloth==2026.9.14 unsloth_zoo==2026.9.9 peft==0.21.2 trl==0.24.0 transformers==5.5.0 accelerate==1.15.0 bitsandbytes==0.50.2 xgrammar==0.2.8 huggingface_hub==1.30.0 tokenizers==0.22.2 safetensors==0.8.0 datasets==4.3.0 xformers==0.0.35 triton==3.6.0 cut_cross_entropy==25.1.1 torchao==0.18.0 hf_xet==1.6.0 pillow==12.3.0 > /workspace/pip.log 2>&1"
```

  ชุดนี้ = ชุด A (D9, `freeze_venv_main.txt` ของ 3 ต.ค.) เดียวกับ `PIN_SETS["A"]` ใน `train_t07.py` · ขั้น deps ของ
  `vllm_build_t07.sh` ตรวจซ้ำทั้ง 20 ตัว (รวม torch/torchvision ที่มากับ image) ไม่ตรง = `FAIL_deps` ไม่ merge ต่อ ·
  pillow ต้องอยู่ในบรรทัด pip: 3 ต.ค. ได้ 12.3.0 จาก `-U pillow` ใน onstart ไม่ใช่จาก image (รุ่นใน image ไม่เคยวัด)
- `success:false` = เครื่องไม่ว่างจริง → `vastai destroy instance <id> -y` แล้วเอา offer ถัดไป · ใช้ endpoint direct (`public_ipaddr:direct_port_start`)
- ตั้งคืนอัตโนมัติทันทีที่ ssh ได้ (5 ชม. · 7.5 ชม. ถ้าจะวัด Destrier ซ้ำ) ด้วยไฟล์ state แยก ไม่แตะ state ของ production:

```
PURSON_QUIET=1 python -B -c "import sys; sys.dont_write_bytecode=True; sys.path.insert(0, 'D:/00mk/steel project/งานสมบูรณ์/Constistant/server/purson-worker'); import presentation as P; from pathlib import Path; P.STATE_FILE=Path('D:/00mk/steel project/training/t07_bench/state_gate4.json'); st={'instance_id': <ID>, 'ssh_host': '<IP>', 'ssh_port': <PORT>}; P.save_state(st); print(P.arm_autodown(st, 5))"
```

  ต้องขึ้น `⏰ ตั้งเวลาคืนการ์ดอัตโนมัติแล้ว` · ขึ้น ⚠️ = ไม่มีตัวคืนอัตโนมัติ ต้องคืนเองด้วยมือ (บอกมะขามทันที)

## 3. ส่ง bundle ขึ้นการ์ด

```
ssh -p <PORT> root@<IP> "mkdir -p /workspace"
scp -P <PORT> "/d/00mk/steel project/training/t07_bench/gate4_bundle/ft_t07.tar" "/d/00mk/steel project/training/t07_bench/gate4_bundle/ft_t07.tar.sha256" root@<IP>:/workspace/
ssh -p <PORT> root@<IP> "cd /workspace && sha256sum -c ft_t07.tar.sha256 && tar -xf ft_t07.tar && sha256sum -c --quiet ft/MANIFEST.sha256 && echo BUNDLE_OK && head -3 ft/BUNDLE_INFO.txt"
```

ต้องเห็น `BUNDLE_OK` (t05 เคย scp ค้างที่ 83% แล้วไฟล์ไม่ครบแบบเงียบๆ — manifest จับได้)

ในก้อน (`/workspace/ft/`): `tune/` (soup/merge/verify + test_soup_layout + fix_destrier_layout ให้ test import ได้) ·
`gate4/` (สคริปต์ + launch + `destrier_mrg.pt` + `destrier_merged.sha256`) · `vllm_engines.sh` · `render_jobs.py` ·
`webpdf/` (PDF บ้านเน็ต 3 เล่ม + sha256) · `bench/` (83b8e52c: job + 29 ภาพ + SHA256SUMS) ·
`wk/worker/` (worker.py + โมดูลที่มันเปิด + bench_house.py — **ไม่มี worker_config.json**) ·
`wk/training/tune_ai/{t07_Palfrey,t04_Purson}/` (prompt วางระดับ tune_ai) · `wk/training/tune_ai/t03/pass1_organize/organize.py` ·
`wk/training/tools/` (cv_scan.py + pattern_recognition.py + เทมเพลต) · `MANIFEST.sha256` · `BUNDLE_INFO.txt` (commit ของทั้งสอง repo)

## 4. token บนการ์ด (มะขามทำเอง)

มะขาม ssh เข้าการ์ดแล้วพิมพ์ (วาง token อ่านอย่างเดียวตอนมันถาม — ตัวอักษรไม่ขึ้นจอ):

```
/venv/main/bin/hf auth login
```

(ถ้าไม่มีคำสั่ง `hf`: `/venv/main/bin/python -c "from huggingface_hub import login; login()"`) · Claude ไม่เห็นและไม่พิมพ์ token

## 5. build (ครั้งเดียวจบ รันซ้ำได้)

```
ssh -p <PORT> root@<IP> "cd /workspace/ft && mkdir -p logs && setsid --fork nohup bash gate4/vllm_build_t07.sh >> logs/build.log 2>&1 < /dev/null &"
ssh -p <PORT> root@<IP> "ls /workspace/ft | grep -E '^(DONE|FAIL)_' | tr '\n' ' '; echo; tail -n 3 /workspace/ft/logs/build.log"
```

- เฝ้าทุก ~10 นาที · **อ่านรอบแรกเองว่ามีค่าจริง** และ ssh ไม่ตอบ 3 ครั้งติด = ต้องปลุกคนดู ไม่ใช่วนต่อเงียบๆ (Lesson 17)
- ลำดับ DONE: `download` → `soup` → `merge` → `verifyAB` → `verifyC` → `tokenizer` → `venv_vllm` → `tokenizer_vllm` → `gateD` → `merged_sha` → `gate4_ready`
- ล้มที่ไหน (`FAIL_<ขั้น>`) หยุดตรงนั้น ไม่ลบอะไร · แก้แล้วสั่งบรรทัดเดิมซ้ำ ขั้นที่ผ่านแล้วข้ามเอง
  - `FAIL_deps` เวอร์ชันไม่ตรงชุด A · `FAIL_layout_env` env ของ layout ไม่ติด · `FAIL_gpu_small` / `FAIL_disk_small` การ์ดผิดสเปก
  - `FAIL_hf_access` อ่าน fold repo ไม่ได้ — 401/403 แปลว่า "private หรือไม่มีจริง บอกไม่ได้" ไม่ใช่ "ไม่มี" (Lesson 22) → เช็ค token ข้อ 4
  - `FAIL_soup_cfg` soup ไม่ใช่ r64 / alpha128 / grouped_by_expert · `FAIL_soup` ด่านตรวจใน soup ไม่ผ่าน (ไม่เดา หยุด)
  - `FAIL_verifyC_ref` อาจเป็น OOM: soup r64 + base บน GPU ≈ 87 จาก 95 GB (ประมาณ — r64 ยังไม่เคยลอง · r48 ของ Destrier ผ่าน)
  - `FAIL_tokenizer_sha` tokenizer.json ของ merged ไม่ใช่ของ base (ดู `logs/tokenizer_sha.txt` + ผล tok_parity) — ถ้า id เท่ากันหมดและ
    ต่างแค่ padding/truncation: ก็อป `tokenizer.json` ของ base snapshot ทับใน `/workspace/palfrey_merged/` แล้วรันซ้ำ (Lesson 20: ส่ง tokenizer ของ base ไม่แตะ) — **บอกมะขามก่อน**
  - `FAIL_base_tokenizer_changed` base บน HF ไม่ใช่ตัวที่ตรวจไว้ใน proof/06 → หยุด ห้ามไปต่อ ให้คนดู
  - `FAIL_gateD` ดู `logs/probeD_palfrey.log` (เกณฑ์ข้อ 6)

## 6. ด่าน D — เกณฑ์ที่ตัดสินแล้ว (11 พ.ย. 69)

ผ่าน ถ้า **(ก)** token อันดับ 1 ของตัวเสิร์ฟตรงกับ merged และ top-5 ซ้อนกัน ≥ 4/5 (เกณฑ์เดิม) **หรือ (ข)** อันดับ 1 สลับกันระหว่าง
```` ``` ```` กับ `{"` เท่านั้น **และ** top-5 ซ้อนกันครบ 5/5 **และ** |Δlogprob| สูงสุดใน top-5 **< 0.7** · นอกนั้นไม่ผ่าน
ที่มา: proof/04 และ proof/05 vLLM สลับคู่นี้ที่ Δ 0.678 ทั้งสองรอบ ทั้งที่ merged ถูก — เกณฑ์เดิม (`verify_merge.py`) ตัดทิ้ง

## 7. วัดผล t07 (เริ่มเมื่อเห็น `DONE_gate4_ready`)

```
ssh -p <PORT> root@<IP> "cd /workspace/ft && setsid --fork nohup bash gate4/run_bench_t07.sh t07 >> logs/bench_t07.log 2>&1 < /dev/null &"
ssh -p <PORT> root@<IP> "ls /workspace/ft | grep -E '^(DONE|FAIL)_(bench|wdeps|render)' | tr '\n' ' '; echo; tail -n 3 /workspace/ft/logs/bench_t07.log"
```

- 83b8e52c (มีเฉลย หน้า 19–25) ×3 → `out/t07_house_r1..r3`
- บ้านเน็ต 3 หลัง (แบบบ้านเพื่อประชาชน กรมโยธาฯ ไม่มีเฉลย) ×3 → `out/t07_dpt13226_1fl_r1..3` · `dpt13244_1fl` · `dpt13250_2fl`
  — PDF ตรวจ sha256 กับ proof/04 ก่อนเรนเดอร์ (dpt13226 `775f620d…` 14 หน้า · dpt13244 `486da2a0…` 18 หน้า · dpt13250 `e4e3829e…` 25 หน้า)
  แล้วเรนเดอร์ใหม่ด้วย pymupdf 1.28.2 dpi 200 (`render_jobs.py`) เหมือนรอบฐาน
- micro: pass0 หน้า 1,19 + `22:section,20:plan_beam,19:plan_footing` ยิงซ้ำ 4 รอบ → `out/t07_micro` (ห้ามตัดสินคุณภาพจาก micro — proof/05)
- ทุกคำขอ `PURSON_CV_MERGE=0` (worker ได้ขั้นรวม CV 5 พ.ย. ซึ่งแก้ doc ของแปลน — ฐาน 3 ต.ค. ไม่มี) · `--prompts` =
  `/workspace/ft/wk/training/tune_ai/t07_Palfrey` (ระดับ tune_ai ไม่งั้น worker ไม่มีครอป/CV hint แบบเงียบๆ — สคริปต์เช็คให้)
- deps ของ worker ตรึงตามรอบฐาน: opencv-python-headless 5.0.0.93 · pymupdf 1.28.2 · numpy 2.5.3 · requests 2.34.2 (ลง `/workspace/wdeps`)
- ใช้เวลา ~85 นาที (ประมาณจากรอบฐาน: 299 + 218 + 530 + 557 วิ ต่อรอบ × 3 + micro) · รันวนเป็นรอบ (รอบ 1 ครบทุกบ้านก่อน)

## 8. (ทางเลือก) วัด Destrier ซ้ำบนการ์ดเดียวกัน

ฐาน 3 ต.ค. เป็น n=1 และ worker เปลี่ยนไปแล้ว — วัด Destrier ด้วย worker/การ์ดเดียวกันได้ตัวเทียบที่ยุติธรรมกว่า (+~2 ชม. +$2–3)

```
ssh ... "bash /workspace/ft/gate4/stop_server.sh"                       # ต้องขึ้น 'ปิดสะอาด' — ไม่ขึ้น = ห้ามเปิดตัวใหม่
ssh ... "bash /workspace/ft/gate4/dl_destrier_merged.sh"                # 71.9 GB private · ตรวจ sha 27 ไฟล์ตาม proof/06
ssh ... "cd /workspace/ft && setsid --fork nohup bash -c \"\$(cat gate4/launch_vllm_destrier.txt)\" > logs/serve_destrier.log 2>&1 < /dev/null &"
ssh ... "until curl -sf -m 5 localhost:8000/v1/models > /dev/null; do sleep 15; done; echo UP"
ssh ... "cd /workspace/ft && /venv/main/bin/python gate4/gate_d_t07.py --ref gate4/destrier_mrg.pt --merged /workspace/destrier_merged --tune tune"
ssh ... "cd /workspace/ft && setsid --fork nohup bash gate4/run_bench_t07.sh destrier /workspace/ft/wk/training/tune_ai/t04_Purson >> logs/bench_destrier.log 2>&1 < /dev/null &"
```

`destrier_mrg.pt` = fingerprint ของ merged รอบ 3 ต.ค. (proof/04) — น้ำหนัก destrier-merged บน HF ตรงกับ build ที่ตรวจแล้ว 26/26 shard (proof/06)
จึงใช้เป็นตัวอ้างอิงได้ (อนุมาน — ยังไม่เคยยิงคู่นี้) · Destrier ใช้ prompt ชุด t04_Purson (ที่มันเทรนมา) ไม่ใช่ของ t07

## 9. ดึงผล + ให้คะแนน (PC)

```
mkdir -p "/d/00mk/steel project/training/t07_bench/gate4_out"
scp -P <PORT> -r root@<IP>:/workspace/ft/out root@<IP>:/workspace/ft/logs "/d/00mk/steel project/training/t07_bench/gate4_out/"
scp -P <PORT> root@<IP>:/workspace/ft/ref.pt root@<IP>:/workspace/ft/mrg.pt root@<IP>:/workspace/ft/base.pt root@<IP>:/workspace/ft/base_u.pt "/d/00mk/steel project/training/t07_bench/gate4_out/"
python tune_ai/t07_Palfrey/gate4/analyze_houses.py "D:/00mk/steel project/training/t07_bench/gate4_out/out" t07 destrier
O="D:/00mk/steel project/training/t07_bench/gate4_out/out"
python tune_ai/t07_Palfrey/gate4/score_house.py t07_r1="$O/t07_house_r1/result.json" t07_r2="$O/t07_house_r2/result.json" t07_r3="$O/t07_house_r3/result.json"
```

เกณฑ์ผ่าน t07 (จาก `t07_workflow.md` · ฐาน = Destrier ตัวซ่อมบน vLLM proof/04 — ไม่ใช่ตัวที่ปนผิด):

| วัด | ฐาน (proof/04) | t07 ต้อง |
|---|---|---|
| 83b8e52c recall / precision (มาร์ค หน้า 19–25) | 0.79–0.83 / 0.83–0.85 | ≥ 0.79 / ≥ 0.83 |
| บ้านเน็ต: gridline ชนเพดาน 9,000 token | 3 ครั้งใน 6 รอบ (2 ตัวเสิร์ฟ × 3 หลัง) | **0 ครั้ง** ใน 3 หลัง × 3 รอบ |
| ชื่อบ้านเทรนในผลอ่านใดๆ (regex `บ้าน_(?:เล็ก\|ใหญ่)_\d+ชั้น_\d+`) | มี | **0** |
| ตัวอักษรจีน (`cjk` ใน calls.jsonl) | 0 | 0 |
| plan_beam หน้า 20 ยิงซ้ำ 4 รอบ (เฉลย 59) | 22–56 | ช่วงแคบลง + ค่าต่ำสุด ≥ 45 |

- `analyze_houses.py` พิมพ์ทั้ง mean และ min ของ 3 รอบ — **ใช้ตัวไหนยังไม่ได้ตัดสิน ต้องเลือกก่อนเปิดดู** (ข้อ 1.5)
- ตีความเกณฑ์ recall/precision แบบปัด 2 ตำแหน่ง (ฐานจริง 41/52 = 0.788 พิมพ์เป็น 0.79 — เทียบตรงตัวฐานเองจะตก) — ⚠️ รอมะขามยืนยัน
- ฐาน micro ของ plan_beam ใน proof/05 (T 0.7 × 4) คือ 13 / 30 / 74 / 25 — แกว่งกว่าตัวเลขในตาราง
- regex ชื่อบ้านเดิม (`[12]ชั้น`) มองไม่เห็นบ้าน 3–4 ชั้น 10 หลัง — สำเนาในโฟลเดอร์นี้แก้แล้ว
- temperature คง 0.7 ตาม worker (ไม่ทับ) · ห้ามตัดสินค่า sampling จาก micro

## 10. push ขึ้น HF (เฉพาะเมื่อมะขามตัดสินแล้ว) — ⚠️ พื้นที่ private ของบัญชีฟรี

ตอนนี้ private ที่ใช้อยู่: destrier-merged **71.9 GB** · ถ้า fold repo private 4 × ~3.8 GB ≈ 15 GB · soup r64 ≈ 15 GB · palfrey-merged ≈ **67 GB**
(+ palfrey-data ถ้ายังไม่ลบ) → รวม ≈ 170 GB — **น่าจะเกินโควตา private ของบัญชีฟรี** (ตัวเลขโควตาจริงยังไม่ได้เช็ค — ดูหน้า storage ของบัญชีก่อน)
push เกินโควตาอาจล้มกลางทาง · ทางเลือกให้มะขามเลือก: (ก) palfrey-merged เป็น public (ติดเรื่อง siamplan ห้ามใช้เชิงพาณิชย์ — 57 บ้านในชุดเทรน
ยังไม่ได้ตัดสิน) (ข) push แค่ soup แล้ว merge ใหม่เมื่อจะใช้ (~1.5 ชม. บนการ์ด) (ค) ลบ/ย้าย destrier-merged (ง) อัปเกรดบัญชี

ทำเมื่อเลือกแล้ว (มะขาม `hf auth login` ด้วย token เขียนที่เห็นแค่ repo ปลายทาง — ไม่ใช่ t44):

```
/venv/main/bin/python -c "from huggingface_hub import HfApi; HfApi().upload_folder(folder_path='/workspace/palfrey_soup', repo_id='dacarokann/palfrey', repo_type='model')"
/venv/main/bin/python -c "from huggingface_hub import HfApi; HfApi().upload_large_folder(repo_id='dacarokann/palfrey-merged', folder_path='/workspace/palfrey_merged', repo_type='model', private=True)"
```

(signature ตรวจกับ huggingface_hub 1.28.0 บน PC แล้ว · บนการ์ดเป็น 1.30.0) · `upload_folder` **ไม่สร้าง repo ให้** (ไม่มีอาร์กิวเมนต์
`private`) → repo ต้องมีอยู่ก่อน (`hf_setup.py --apply` สร้างไว้เป็น private) · ถ้าเลือก public ให้เปลี่ยนที่ Settings ก่อน push · หลัง push เทียบ sha256 ของ LFS บน HF กับ
`logs/merged_sha256.txt` ทุกไฟล์ (`HfApi().model_info(repo, files_metadata=True).siblings[i].lfs.sha256`) ต้องตรง 100% (Lesson 23)
แล้วเก็บ `merged_sha256.txt` + `soup.sha256` เข้า repo (proof ของ t07) ไว้เป็นด่านของการ build ครั้งต่อไป

## 11. t07 ไม่มี `png` / `doc_page` ในคำตอบแล้ว — เครื่องมือวัดพังไหม (ตรวจ 11 พ.ย. ด้วย grep + อ่านโค้ด)

- **ไม่พัง ไม่ต้องแก้:** `bench_house.py` · `score_house.py` · `analyze_houses.py` (และ `analyze_micro.py`) ไม่อ่าน `png`/`doc_page` เลย
  — เลขหน้ามาจากฝั่งเราทั้งหมด: worker ตั้ง `doc["_page"]` จาก payload ของงาน แล้วตั้งชื่อไฟล์ `page_NN_<subtask>.json` เอง
  (score_house จับเลขจากชื่อไฟล์นี้) · micro ใช้เลขหน้าจาก `--tasks` · เฉลยจับเลขหน้าจากชื่อไฟล์ `_หน้าNN_`
- worker.py เองก็ไม่อ่าน `png` ของโมเดล (`png` ใน manifest ของ organize.py คือเลขหน้าที่ worker เขียนเอง)
- **วัดจริงแล้ว (11 พ.ย. `dryrun_bench_stub.py`)**: bundle ที่แตกแล้ว + worker.py ปัจจุบัน + prompt t07 + โมเดลปลอมที่ตอบแบบ t07
  (ไม่มี `png`/`doc_page`/`source_*` · element ใช้คีย์ `element_id`/`mark`) → house + micro exit 0 · ได้ `page_19_plan_footing.json`
  `page_20_plan_beam.json` `page_22_section.json` `grid_master.json` · `score_house.py` / `analyze_houses.py` อ่านได้ครบ ·
  GRID MASTER ที่ worker ต่อท้าย plan_* ตรงกับสูตร D4 ทุกไบต์ (2/2 คำขอ) · ทุกคำขอ `response_format json_object` · temperature 0.7
- ทางแก้ขั้นต่ำถ้าวันหลังเครื่องมือไหนต้องการเลขหน้า: ใช้ชื่อไฟล์ `page_NN_<subtask>.json` หรือ `doc["_page"]` ที่ worker เขียนเอง
  ห้ามพึ่งคีย์ที่โมเดลตอบ
- ที่ต้องแก้จริงและแก้ในสำเนาแล้ว: regex ชื่อบ้าน `[12]ชั้น` → `\d+ชั้น` · path ที่ผูกกับ proof/04/05 · import `score_house` จาก `bench`
- นอกด่าน 4 (ตอน deploy — มีใน t07_workflow แล้ว): เว็บ `raw-extraction-import.js` บรรทัด 522 (เดิมจด 516) หา grid master ด้วย
  `pattern === 'gridline' && source_pages` · `raw-extraction-adapter.js` ใช้ `png`/`doc_page` แค่เป็นป้ายในข้อความเตือน (มีตัวสำรอง)

## 12. คืนการ์ด — หลังดาวน์โหลดครบเท่านั้น

1. ผลวัดทั้งหมดอยู่บนการ์ดที่เดียว → ข้อ 9 ต้องเสร็จ และเปิดดูบน PC ได้จริง (`analyze_houses.py` รันผ่าน)
2. `logs/merged_sha256.txt` · `logs/soup.sha256` · `logs/probeD_*.log` · fingerprint 4 ไฟล์ อยู่บน PC แล้ว
3. ถ้าตัดสินให้ push: push เสร็จ + ตรวจ hash ข้อ 10 ผ่าน · ถ้าไม่ push: บอกมะขามตรงๆ ว่า soup/merged จะหายพร้อมการ์ด
   (สร้างใหม่ได้จาก fold บน HF ~2 ชม. ~$3–4 — fold repo คือของจริง ห้ามลบ)
4. `vastai destroy instance <id> -y` → `vastai show instances --raw` ต้องไม่มี id นี้แล้ว (ใบอื่นถ้ามีห้ามแตะ)
5. ลบ/ยกเลิก token อ่านอย่างเดียวที่ใช้บนการ์ด (ถ้าตั้งใจใช้ครั้งเดียว)
