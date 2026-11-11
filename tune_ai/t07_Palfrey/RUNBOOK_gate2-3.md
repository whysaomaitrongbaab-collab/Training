# RUNBOOK — t07 Palfrey ด่าน 2 (Phase 0) และด่าน 3 (เทรน 4 fold)

เขียน 11 พ.ย. 69 · ⚠️ **ยังไม่เคยรันจริงบนการ์ด** — ทุกสคริปต์ผ่านแค่ทดสอบบน PC (ไม่มี GPU) · ด่านไหนไม่ผ่าน ห้ามไปด่านถัดไป

> ⛔ **`vastai destroy` ลบถาวรทันที กู้ไม่ได้** (ไม่เหมือน stop) — ห้ามคืนการ์ดใบไหนจนกว่าของบนใบนั้นปลอดภัยตามเช็คลิสต์ Day of Shame ท้ายไฟล์ (2026-07-21 เสีย adapter + merged + GGUF ทั้งหมดเพราะข้อนี้)

> ⛔ **ห้ามเอา token ของ PC ขึ้นการ์ด** (t44 เขียนได้ทุก repo รวม destrier/destrier-merged — Lesson 22) · บนการ์ดใช้ token จำกัดสิทธิ์ที่มะขามพิมพ์เองเท่านั้น

> 💸 **เช่าการ์ดทุกใบต้องถามมะขามก่อน** (op_t07) · ด่าน 2 ≈ $2-3 · ด่าน 3 ≈ $55-100

ตัวแปรที่ใช้ข้างล่าง (git-bash บน PC):
```bash
T07="/d/00mk/steel project/training/Training/tune_ai/t07_Palfrey"     # PC
C=/workspace/Training/tune_ai/t07_Palfrey                             # บนการ์ด (รากรีโป = /workspace/Training)
```

## 0. ก่อนเช่า (PC ฟรี) — ทำครั้งเดียว ใช้ทั้งด่าน 2 และ 3
1. dataset ผ่านด่าน 1 แล้ว: `data/{train,val}_fold{0..3}.jsonl` + `manifest.json` อยู่ใน `$T07` และ sanitize ไม่มีอะไรค้าง
2. สร้าง bundle (นอกรีโป): `cd "$T07" && python make_bundle.py` → `D:\00mk\steel project\training\t07_bundle\` (tar + `.sha256` + manifest) · หยุดเองถ้ารูปหาย/มีข้อความหน้าตาเหมือน token
3. HF (ใช้ token ของ PC — รันบน PC เท่านั้น): `python hf_setup.py` (dry-run ดูก่อน) → มะขามเคาะ → `python hf_setup.py --apply`
   ต้องจบด้วย `✅ PASS — sha256 บน HF ตรงกับในเครื่อง` · repo ทั้ง 7 เป็น private ·
   ⚠️ เช็คพื้นที่ private ของบัญชีฟรีก่อน (destrier-merged กินไป 71.9 GB) ที่หน้า Settings ของ HF
4. **มะขามสร้าง token ใหม่ที่หน้าเว็บ HF** (Settings → Access Tokens → Fine-grained) ชื่อ `t07-card`:
   Repositories: `dacarokann/Palfrey_a` `_b` `_c` `_d` = **Read + Write** · `dacarokann/palfrey-data` = **Read** · ไม่ติ๊กสิทธิ์ระดับ user
   (repo ต้องถูกสร้างจากข้อ 3 ก่อน — token แบบนี้สร้าง repo เองไม่ได้) · ลบ token นี้ทิ้งหลังจบด่าน 3
5. เครดิต: `vastai show user --raw | python -c "import json,sys;print('credit', json.load(sys.stdin)['credit'])"`
6. หา offer (ตัวกรองชุดเดียวกับ Constistant build_vllm_card.py: gpu_ram≥90, num_gpus=1, reliability>0.99, inet_down>500,
   verified, direct port, disk≥200, ชื่อการ์ด "RTX PRO 6000", ตัดเครื่องใน blacklist.json, ประเทศ US/CA/GB/AU/NZ/IE ก่อน
   ไม่พอค่อยเติม any-geo): `python offers_t07.py` (ด่าน 2) · `python offers_t07.py --n 4` (ด่าน 3) — อ่านอย่างเดียว ไม่เช่า

## เช่า + เตรียมการ์ด 1 ใบ (ใช้ซ้ำทั้งด่าน 2 และ 3)
```bash
# PC
vastai create instance <OFFER> --image vastai/pytorch:cuda-12.8.1-auto --disk 200 --ssh --direct --label t07-<ชื่อ> --raw
#   ได้ success:false → vastai destroy instance <ID> -y แล้วเอา offer ถัดไป
vastai show instances --raw | python -c "import json,sys;[print(i['id'], i.get('label'), i.get('actual_status'), i.get('public_ipaddr'), i.get('direct_port_start')) for i in json.load(sys.stdin)]"   # รอ running
vastai ssh-url <ID>                                     # → ssh://root@<H>:<P> (ทางตรง) · ต่อไม่ติด 15 นาที = คืนแล้วเช่าใหม่
# ส่ง onstart เอง (ไม่พึ่งช่อง onstart ของ vast) — tr ตัด CR กันไฟล์โดน autocrlf
tr -d '\r' < "$T07/onstart_t07.sh" | ssh -p <P> -o StrictHostKeyChecking=accept-new root@<H> 'cat > /workspace/onstart_t07.sh'
ssh -p <P> root@<H> 'setsid nohup bash /workspace/onstart_t07.sh > /dev/null 2>&1 < /dev/null &'
```
```bash
# บนการ์ด: ssh -p <P> root@<H>
C=/workspace/Training/tune_ai/t07_Palfrey    # ⚠️ ตัวแปรนี้ต้องตั้งในเชลล์บนการ์ดด้วย (ไม่ใช่แค่บน PC) — ไม่ตั้ง `cd $C` จะพาไป home แล้วทุกคำสั่งข้างล่างล้ม
export HF_HUB_DISABLE_XET=1                  # Xet พังกลางการโหลดโมเดลใหญ่จริง (23 ก.ย.) — onstart ใส่ ~/.bashrc ให้แล้ว แต่ใส่ซ้ำกันเชลล์ที่ไม่อ่าน .bashrc
ls /workspace/ONSTART_DONE /workspace/ONSTART_FAIL 2>/dev/null; tail -3 /workspace/onstart_t07.log   # ~10 นาที
#   ต้องเห็น "✓ เวอร์ชันตรงชุดที่ตรึงทุกตัว" · ONSTART_FAIL = อ่าน log แล้วหยุด
read -rs HF_TOKEN && export HF_TOKEN        # ← มะขามพิมพ์ token t07-card เอง (ไม่ขึ้นจอ ไม่ลงไฟล์)
/venv/main/bin/python -c "from huggingface_hub import snapshot_download as s; s('dacarokann/palfrey-data', repo_type='dataset', local_dir='/workspace/dl')"
cd /workspace/dl && sha256sum -c t07_bundle.tar.sha256                     # ต้อง OK
mkdir -p /workspace/Training && tar -xf /workspace/dl/t07_bundle.tar -C /workspace/Training
cd /workspace/Training && sha256sum -c --quiet tune_ai/t07_Palfrey/BUNDLE_MANIFEST.sha256 && echo MANIFEST_OK
cd $C && /venv/main/bin/python gate2_hf_write.py --repo dacarokann/Palfrey_a   # ✅ PASS = token ถูกตัว (token กว้าง = FAIL เอง)
grep PREFETCH_OK /workspace/prefetch_base.log                              # ฐานโมเดล 72 GB โหลดเสร็จ
```
ทางสำรองถ้าโหลดจาก HF ไม่ได้: `scp -P <P> t07_bundle.tar t07_bundle.tar.sha256 root@<H>:/workspace/dl/` (จาก `t07_bundle\` บน PC) แล้ว `sha256sum -c` เหมือนเดิม

## ด่าน 2 — Phase 0 บนการ์ด 1 ใบ (เกณฑ์ผ่าน = ตาราง gate 2 ไม่มี FAIL)
⚠️ ข้อ 5 ของ gate2_smoke เปิด adapter ผ่าน Unsloth เพื่อตรวจ (ไม่ใช่เสิร์ฟ) — **บอกมะขามก่อนรัน** (กฎ 7 พ.ย.)
```bash
cd $C && setsid nohup bash gate2_smoke.sh > /workspace/gate2_smoke.log 2>&1 < /dev/null &
tail -f /workspace/gate2_smoke.log        # ~1-1.5 ชม. · ท้ายไฟล์คือตาราง PASS/WARN/FAIL
```
ทำอะไรบ้าง: (1) เทรน 10 step fold0 (2) adapter_config r16 α32 `lora_B_layout=grouped_by_expert` (3) RESUME จาก checkpoint-10 ถึง step 12
(4) SORT_LONGEST=1 3 step บน fold ที่มีแถวยาวสุด → peak VRAM (t05: probe 80.6 แต่เทรนจริงขึ้น 92.0 GB — ตารางบวก 11.4 ให้ดู)
(5) process ใหม่ env grouped → `✅ LoRA ของ expert ทั้ง 80 ตัว อ่านแบบ grouped_by_expert` + อนุมาน 1 แถว val ต้องเป็น JSON และไม่มีชื่อบ้านเทรน (6) เขียน HF ได้
- WARN/SKIP/INFO ต้องอ่านเองแล้วตัดสิน · ข้อ 6 ต้อง PASS ก่อนด่าน 3 (SKIP ไม่พอ)
- จดจาก log ไว้คำนวณด่าน 3: วินาทีต่อ step (ข้อ 1) และ peak VRAM (ข้อ 4)
```bash
# PC — เอาเฉพาะ log/ผล/freeze กลับ (ไม่เอา adapter ทดสอบ 3.8 GB)
mkdir -p "$T07/logs_gate2"
ssh -p <P> root@<H> 'cd /workspace && tar -cf - gate2/results.tsv gate2/*.log gate2/infer gate2_smoke.log onstart_t07.log freeze_train.txt' | tar -xf - -C "$T07/logs_gate2"
cp "$T07/logs_gate2/freeze_train.txt" "$T07/freeze_train.txt"            # Lesson 18a: การ์ดด่าน 3 ลงตามนี้เป๊ะ
cd "$T07" && python make_bundle.py && python hf_setup.py --apply           # bundle ใหม่มี freeze_train.txt
vastai destroy instance <ID> -y && vastai show instances                    # ใบนี้ไม่มีของที่หาใหม่ไม่ได้ เมื่อ log อยู่บน PC แล้ว
```

## ด่าน 3 — เทรนจริง 4 fold (fold0→Palfrey_a … fold3→Palfrey_d)
ก่อนเช่า: ด่าน 2 ไม่มี FAIL · มะขามอนุมัติ · เครดิตพอ (4 ใบ × ราคา/ชม. × ชม.ต่อ fold + 20%; ชม.ต่อ fold ≈ ceil(แถว train/8) × EPOCHS × วินาทีต่อ step จากด่าน 2 + ~1 ชม. setup · แถว train อยู่ใน manifest.json) · bundle ล่าสุดมี freeze_train.txt
⚡ **ไฟ PC (PowerShell) — กันเครื่องหลับระหว่างเฝ้า** (ค่าเดิม 3 ชม.): `powercfg /change standby-timeout-ac 0` · `powercfg /change hibernate-timeout-ac 0` · เสียบสายชาร์จไว้ · จบแล้วคืนค่า `... standby-timeout-ac 180` · `... hibernate-timeout-ac 180`
```bash
# PC: offer 4 ใบ แล้วเช่า + เตรียมทีละใบตามหัวข้อ "เช่า + เตรียมการ์ด" (label t07-fold0 … t07-fold3) — จดคู่ <ID> <H>:<P> ของแต่ละ fold
python "$T07/offers_t07.py" --n 4
```
```bash
# บนการ์ด fold <N> (session เดียวกับที่ export HF_TOKEN ไว้)
cd $C && FREEZE_FILE=$C/freeze_train.txt bash /workspace/onstart_t07.sh      # ลงตาม freeze ของการ์ดด่าน 2 → ต้องเห็น ✓ เวอร์ชันตรง
diff <(grep -v ' @ ' freeze_train.txt | sort) <(grep -v ' @ ' /workspace/freeze_train.txt | sort) && echo FREEZE_SAME   # Lesson 18a
setsid nohup bash run_fold.sh <N> > train_fold<N>.log 2>&1 < /dev/null &     # EPOCHS=1 (D7) · อยาก 2: EPOCHS=2 setsid nohup …
sleep 90; tail -5 train_fold<N>.log      # ต้องเห็น ✅ PASS ของ gate2_hf_write และ "attempt 1/3"
```
run_fold.sh: OOM → รอ 30 วิแล้ว RESUME=1 ต่อจาก checkpoint ล่าสุด (สูงสุด 3 ครั้ง) · ล้มแบบอื่น → `FAIL_fold<N>` · เสร็จ = `DONE_fold<N>`
(train_t07.py เขียน DONE หลัง push + sha256 บน HF ตรงกับบนการ์ดแล้วเท่านั้น · checkpoint ทุก 25 step อยู่บนการ์ด ไม่ขึ้น HF)

**เฝ้าจาก PC** — ผ่าน Claude Bash `run_in_background` หรือหน้าต่าง git-bash แยก:
```bash
bash "$T07/watch4.sh" '<H0>:<P0> <H1>:<P1> <H2>:<P2> <H3>:<P3>' 960 > "$T07/watch_gate3.log" 2>&1; echo "watch exit=$?"
```
(ไม่ต่อ `| tee` — exit code จะกลายเป็นของ tee แล้วเงื่อนไขปลุกหาย)
- **อ่านรอบแรกด้วยตาทันที** (Lesson 17): `head -40 "$T07/watch_gate3.log"` — ทุกใบต้องมีบรรทัด `PROC:` `STEP:`/`LAST:` `GPU:` ที่เป็นตัวเลขจริง ไม่ใช่ `SSHFAIL`
- exit 0 = DONE ครบ → ไปตรวจ · 1 = FAIL/DEAD → ssh ไปอ่าน `cat FAIL_fold<N>; tail -50 attempt*_fold<N>.log` แก้แล้ว `RESUME=1 setsid nohup bash run_fold.sh <N> >> train_fold<N>.log 2>&1 < /dev/null &`
  · 2 = ssh ไม่ติด 3 รอบ → `vastai show instances` + เครดิต (vast หยุดการ์ดเมื่อเครดิตหมด) · 3 = หมดเวลา → ดูความคืบหน้าแล้วเปิดใหม่
- แก้อะไรแล้ว **เปิด watcher ใหม่ทุกครั้ง** · ห้ามรัน soup/merge/โหลดโมเดลที่สองบนการ์ดที่ยังเทรนอยู่ (Lesson 11)

**ตรวจหลังเสร็จ (ทุก fold — verify-after-push):**
```bash
# บนการ์ด fold <N>  (<L> = a b c d ตาม fold 0 1 2 3)
cd $C && /venv/main/bin/python ../verify_hf_push.py --repo dacarokann/Palfrey_<L> --local-dir outputs_t07_fold<N> --sha   # ต้อง ✅ PASS
cat DONE_fold<N>                                                             # มี sha256=…
# PC — เทียบ sha บน HF กับใน DONE แบบไม่พึ่งการ์ด + ดู config ที่ขึ้นไปจริง
python -c "from huggingface_hub import HfApi; a=HfApi(); [print(c, a.get_paths_info(f'dacarokann/Palfrey_{c}', ['adapter_model.safetensors'], expand=True)[0].lfs.sha256) for c in 'abcd']"
python -c "import json; from huggingface_hub import hf_hub_download as d; [print(c, {k: json.load(open(d(f'dacarokann/Palfrey_{c}', 'adapter_config.json'), encoding='utf-8')).get(k) for k in ('r', 'lora_alpha', 'lora_B_layout', 'peft_version')}) for c in 'abcd']"
mkdir -p "$T07/logs_gate3/fold<N>"
ssh -p <P> root@<H> "cd $C && tar -cf - train_fold<N>.log attempt*_fold<N>.log DONE_fold<N> outputs_t07_fold<N>/run_args.json outputs_t07_fold<N>/lora/training_env.txt" | tar -xf - -C "$T07/logs_gate3/fold<N>"
```

## เช็คลิสต์ Day of Shame — ทุกข้อของการ์ดใบนั้นต้อง ✅ ก่อน `vastai destroy` (ไม่ใช่ "น่าจะโอเค")
- [ ] `DONE_fold<N>` มีจริง และ `verify_hf_push.py --sha` บนการ์ดใบนั้น **✅ PASS**
- [ ] sha256 ที่ PC อ่านจาก HF **ตรงกับ** sha256 ใน `DONE_fold<N>` (สำเนาที่ 2 อยู่บน HF จริง ไม่ใช่ "push ไม่ error")
- [ ] config บน HF: r 16 · lora_alpha 32 · lora_B_layout `grouped_by_expert` · มี `training_env.txt` ใน repo
- [ ] log + run_args + training_env อยู่ใน `$T07/logs_gate3/fold<N>/` บน PC แล้ว
- [ ] ไม่มีงานค้างที่ยังไม่ได้พูด — ถ้ามี ต้องเป็นคำเตือนบรรทัดเดี่ยวก่อนแตะ destroy
- [ ] ไม่เรียกว่า "พร้อมใช้" — คุณภาพตัดสินที่ด่าน 4 (soup + merge + bench: `gate4/RUNBOOK_gate4.md`)
- [ ] มะขามตอบชัดๆ ว่าคืนใบนี้ได้ → `vastai destroy instance <ID> -y` → `vastai show instances` ไม่เหลือใบที่ตั้งใจคืน

หลังคืนครบ 4 ใบ: คืนค่าไฟ PC · ลบ token `t07-card` ที่หน้าเว็บ HF · (ถ้าพื้นที่ private ตึง) ลบ dataset `palfrey-data` ได้ — สร้างใหม่จาก `t07_bundle\` บน PC ได้เสมอ
