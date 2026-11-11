#!/bin/bash
# t07 Palfrey — gate 2 (Phase 0) ทั้งลำดับบนการ์ดใบเดียว · ⚠️ ไฟล์ต้อง LF เท่านั้น
#   cd /workspace/Training/tune_ai/t07_Palfrey && bash gate2_smoke.sh 2>&1 | tee /workspace/gate2_smoke.log
# 1) TEST_STEPS=10 FOLD=0 → adapter เซฟ · 2) adapter_config r16 α32 lora_B_layout grouped_by_expert
# 3) RESUME=1 TEST_STEPS=12 ต่อจาก checkpoint-10 (D10 — กลไกนี้ยังไม่เคยรันกับโมเดลนี้)
# 4) SORT_LONGEST=1 TEST_STEPS=3 บน fold ที่มีแถวยาวสุด → peak VRAM
# 5) โหลด adapter ข้อ 1 ใน process ใหม่ (env grouped) → LoRA expert ครบ 80 ตัว grouped_by_expert + อนุมาน 1 แถว val
#    ⚠️ ข้อนี้เปิดโมเดลผ่าน Unsloth (ตรวจอย่างเดียว ไม่ใช่เสิร์ฟ) — บอกมะขามก่อนรัน (กฎ 7 พ.ย.)
# 6) เขียน HF ได้จริง (ต้องมี HF_TOKEN แบบจำกัดสิทธิ์ใน env) → ตาราง PASS/FAIL ท้ายไฟล์ · exit 0 = ไม่มี FAIL
set -uo pipefail
cd "$(dirname "$0")"
PY=${PY:-/venv/main/bin/python}
G=${GATE2_DIR:-/workspace/gate2}
mkdir -p "$G"
: > "$G/results.tsv"
export UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True SKIP_DEMO=1
export HF_HUB_DISABLE_XET=1 PYTHONUNBUFFERED=1     # [review 11 พ.ย.] Xet โหลดล้มจริง 23 ก.ย. · log ไม่ถูก buffer (เหมือน run_fold.sh)
unset RESUME SORT_LONGEST TEST_STEPS FOLD EPOCHS
rec() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" | tee -a "$G/results.tsv"; }
run() {
  local name=$1; shift
  echo "=== $(date '+%T') $name: $*"
  env "$@" "$PY" train_t07.py > "$G/$name.log" 2>&1
  local rc=$?
  tail -4 "$G/$name.log"
  return $rc
}
aside() { [ -d "$1" ] && mv "$1" "$G/$2_$(date +%s)"; return 0; }
if pgrep -f '[t]rain_t07' >/dev/null; then echo "⛔ มี train_t07 รันอยู่ — gate 2 ห้ามแย่ง GPU (Lesson 11)"; exit 1; fi

# 1 ─ เทรนสั้น
aside outputs_t07_fold0 prev_fold0
if run s1_train10 TEST_STEPS=10 FOLD=0 && [ -f outputs_t07_fold0/lora/adapter_model.safetensors ]; then
  rm -rf "$G/adapter_s10" && cp -a outputs_t07_fold0/lora "$G/adapter_s10"
  LOSS=$(grep -oE "'loss': '?[0-9.]+" "$G/s1_train10.log" | grep -oE '[0-9.]+$' | tr '\n' ' ')
  TREND=$(awk '{ if (NF < 2) print "WARN"; else if ($NF < $1) print "PASS"; else print "WARN" }' <<<"$LOSS")
  rec "1 เทรน 10 step fold0" "$TREND" "loss: $LOSS· $(grep -m1 -oE '~[0-9]+ visual tokens/ภาพ' "$G/s1_train10.log") · $(grep -m1 -oE 'preflight train: seq ยาวสุด [0-9,]+ token' "$G/s1_train10.log") · $(grep -oE 'peak VRAM: [0-9.]+ GB' "$G/s1_train10.log" | tail -1)"
else
  rec "1 เทรน 10 step fold0" FAIL "ดู $G/s1_train10.log"
fi

# 2 ─ adapter_config
if [ -d "$G/adapter_s10" ] && "$PY" gate2_check.py config "$G/adapter_s10" > "$G/s2_config.log" 2>&1; then
  rec "2 adapter_config" PASS "$(grep -m1 'r=' "$G/s2_config.log")"
else
  rec "2 adapter_config" FAIL "ดู $G/s2_config.log"
fi

# 3 ─ RESUME
if [ -d outputs_t07_fold0 ] && run s3_resume12 RESUME=1 TEST_STEPS=12 FOLD=0 \
   && grep -q 'ต่อจาก .*checkpoint-10' "$G/s3_resume12.log" && grep -q 'global_step=12' "$G/s3_resume12.log"; then
  rec "3 RESUME จาก checkpoint-10" PASS "global_step=12"
else
  rec "3 RESUME จาก checkpoint-10" FAIL "ดู $G/s3_resume12.log"
fi
aside outputs_t07_fold0 run_fold0

# 4 ─ worst-case VRAM
LINE=$("$PY" gate2_check.py longest 2>&1 | tail -1)
LF=$(sed -n 's/^FOLD=\([0-3]\) .*/\1/p' <<<"$LINE")
if [ -z "$LF" ]; then
  rec "4 peak VRAM (แถวยาวสุด)" FAIL "หา fold ที่ยาวสุดไม่ได้: $LINE"
else
  aside "outputs_t07_fold$LF" "prev_fold$LF"
  if run s4_longest SORT_LONGEST=1 TEST_STEPS=3 FOLD="$LF"; then
    PK=$(grep -oE 'peak VRAM: [0-9.]+' "$G/s4_longest.log" | tail -1 | grep -oE '[0-9.]+$')
    TOT=$(grep -m1 -oE '^GPU: .* [0-9.]+ GB' "$G/s4_longest.log" | grep -oE '[0-9.]+ GB$' | grep -oE '[0-9.]+')
    # t05: probe 80.6 GB แต่เทรนจริงขึ้นถึง 92.0 GB (+11.4 — หน่วยความจำค่อยๆ ขึ้นระหว่างรอบ) = ค่าคาดแบบหยาบ ไม่ใช่วัด
    rec "4 peak VRAM (แถวยาวสุด fold$LF)" "$(awk -v p="$PK" -v t="$TOT" 'BEGIN{print (p + 11.4 > t - 1) ? "WARN" : "PASS"}')" \
        "probe ${PK} GB / การ์ด ${TOT} GB · ${LINE} · คาดจริง ≈ $(awk -v p="$PK" 'BEGIN{printf "%.1f", p + 11.4}') GB (t05 +11.4)"
  else
    rec "4 peak VRAM (แถวยาวสุด fold$LF)" FAIL "$(grep -m1 -oE 'OutOfMemoryError|CUDA out of memory' "$G/s4_longest.log" || echo ล้ม) — ดู $G/s4_longest.log"
  fi
  aside "outputs_t07_fold$LF" "run_longest"
fi

# 5 ─ โหลดใหม่ + LoRA expert + อนุมาน 1 แถว
if [ -d "$G/adapter_s10" ]; then
  "$PY" gate2_check.py reload --adapter "$G/adapter_s10" --val data/val_fold0.jsonl \
        --out "$G/infer" --results "$G/results.tsv" > "$G/s5_reload.log" 2>&1 \
    || echo "(s5 ไม่ผ่านบางข้อ — ดู $G/s5_reload.log)"
  grep -q '^5a' "$G/results.tsv" || rec "5 โหลดใหม่ + อนุมาน" FAIL "ไม่ได้ผลเลย — ดู $G/s5_reload.log"
else
  rec "5 โหลดใหม่ + อนุมาน" FAIL "ไม่มี adapter จากข้อ 1"
fi

# 6 ─ เขียน HF
if [ -n "${HF_TOKEN:-}" ]; then
  # --lfs-mb 16: อัปไฟล์ LFS จริง + เช็ค lfs.sha256 ทางเดียวกับที่ train_t07.py ใช้ยืนยัน adapter ท้ายรอบ (ไม่ให้เพิ่งรู้ตอนจบ 8 ชม.)
  if "$PY" gate2_hf_write.py --repo dacarokann/Palfrey_a --lfs-mb 16 > "$G/s6_hfwrite.log" 2>&1; then
    rec "6 เขียน HF (Palfrey_a)" PASS "$(grep -m1 '^token' "$G/s6_hfwrite.log")"
  else
    rec "6 เขียน HF (Palfrey_a)" FAIL "$(tail -1 "$G/s6_hfwrite.log")"
  fi
else
  rec "6 เขียน HF (Palfrey_a)" SKIP "ไม่มี HF_TOKEN — ต้องผ่านข้อนี้ก่อน gate 3"
fi

cp -f /workspace/freeze_train.txt "$G/" 2>/dev/null || true
rm -f DRYRUN_DONE_fold*
echo
echo "================ gate 2 สรุป ($(date '+%F %T')) ================"
awk -F'\t' '{ printf "%-5s %-34s %s\n", $2, $1, $3 }' "$G/results.tsv"
if awk -F'\t' '$2 == "FAIL" { f = 1 } END { exit !f }' "$G/results.tsv"; then
  echo "❌ gate 2 ไม่ผ่าน — ห้ามไป gate 3"; exit 1
fi
echo "✅ ไม่มี FAIL (WARN/SKIP ต้องอ่านและตัดสินก่อนไป gate 3) · ผล+log: $G · scp $G กลับ PC ก่อนคืนการ์ด"
