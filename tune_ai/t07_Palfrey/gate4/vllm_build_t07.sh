#!/bin/bash
# vllm_build_t07.sh — ด่าน 4 ของ t07 Palfrey บนการ์ดเช่า: soup 4 fold → merge → ตรวจ A/B/C → tokenizer → vLLM → ด่าน D
# ⚠️ UNTESTED — ร่าง 11 พ.ย. 69 ยังไม่เคยรันบนการ์ดจริง · วิธีใช้ทั้งหมดอยู่ใน RUNBOOK_gate4.md (อ่านก่อน)
#
# ต้นแบบ: Constistant server/purson-worker/vllm_build.sh (สูตรที่ผ่าน A/B/C จริง 3 ต.ค. และ 8 พ.ย. 69) ต่างกัน:
#   · ไม่มีขั้นโหลด/ซ่อม destrier และไม่มี EXPECT_FIXED_SHA (t07 เทรนใหม่ ไม่มี adapter ที่ต้องซ่อม)
#   · soup: soup_safetensors.py --folds 0 1 2 3 --fold-repo dacarokann/Palfrey_{} --out-repo dacarokann/palfrey (ไม่ push)
#   · ด่าน C ใช้ soup เป็น adapter (4 fingerprint เหมือนเดิม)
#   · tokenizer (Lesson 20): sha256 ของ merged/tokenizer.json ต้องเท่ากับของ base ใน proof/06 และ id ภาษาไทยต้องเท่ากัน
#     ทั้งใน /venv/main (ชุดเทรน) และใน venv ของ vLLM (ชุดเสิร์ฟ) — gate4/tok_parity.py
#   · เปิด vLLM ด้วยคำสั่งที่ presentation.launch_cmd สร้าง (gate4/launch_vllm_palfrey.txt) แล้วทำด่าน D ต่อเลย
#     ด้วยเกณฑ์ที่ตัดสินแล้ว 11 พ.ย. (gate4/gate_d_t07.py)
# ⛔ ไม่ push อะไรขึ้น HF · fold repo เป็น private → มะขาม `hf auth login` บนการ์ดเองด้วย token อ่านอย่างเดียว (Lesson 22)
# รันซ้ำได้: ขั้นที่ผ่านมี DONE_<ขั้น> ข้าม · ล้มเขียน FAIL_<ขั้น> แล้วหยุด (ไม่ลบอะไร) · จบ = DONE_gate4_ready
set -u
FT=/workspace/ft; L=$FT/logs; G=$FT/gate4; T=$FT/tune; mkdir -p $L
PY=/venv/main/bin/python; VPY=/workspace/venv_vllm/bin/python
export HF_HUB_DISABLE_XET=1 UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# ⛔ ห้ามเอาออก (Lesson 19): torch CPU หลายสิบเธรดบนการ์ดเช่าให้ผลไม่ deterministic — จำกัดทุกขั้น soup/merge/ตรวจ
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4
export FOLD_REPO='dacarokann/Palfrey_{}'
SOUP_REPO=dacarokann/palfrey
SOUP=/workspace/palfrey_soup; MERGED=/workspace/palfrey_merged
BASE_TOK_SHA=87a7830d63fcf43bf241c3c5242e96e62dd3fdc29224ca26fed8ea333db72de4   # tokenizer.json ของ base — proof/06
PAT='[v]llm[.]entrypoints'

step(){ echo; echo "=== $(date '+%F %T') $1"; }
ok(){ touch $FT/DONE_$1; echo "--- DONE $1 $(date '+%T')"; }
fail(){ echo "!!! FAIL $1"; touch $FT/FAIL_$1; exit 1; }
have(){ [ -f $FT/DONE_$1 ]; }
rm -f $FT/FAIL_*      # รันซ้ำ = ล้างรอยล้มเก่า
[ "${UNSLOTH_MOE_LORA_MERGED:-0}" = 1 ] && fail moe_lora_merged_env   # zoo ส่งทางนี้ไป PEFT/rank_major

# ลง vLLM ขนาน (venv แยก /workspace/venv_vllm) — ไม่เปิดซ้ำถ้ากำลังรันอยู่หรือเสร็จแล้ว
if ! have venv_vllm && ! pgrep -f '[v]llm_engines[.]sh' > /dev/null; then
  setsid --fork nohup bash $FT/vllm_engines.sh > $L/engines.log 2>&1 < /dev/null &
fi

step "รอ pip ของ onstart แล้วตรวจชุด A (D9) · layout env · การ์ด"
while pgrep -f '[v]env/main/bin/python -m pip install' > /dev/null; do sleep 10; done
tail -3 /workspace/pip.log 2>/dev/null
$PY - <<'EOF' || fail deps
# ชุด A = freeze_venv_main.txt ของ 3 ต.ค. — ต้องตรงกับ PIN_SETS["A"] ใน t07_Palfrey/train_t07.py (ห้ามมีสองชุด)
import torch
from importlib import metadata as m
pins = {"torch": "2.11.0+cu128", "torchvision": "0.26.0+cu128", "unsloth": "2026.9.14", "unsloth_zoo": "2026.9.9",
        "peft": "0.21.2", "trl": "0.24.0", "transformers": "5.5.0", "accelerate": "1.15.0", "bitsandbytes": "0.50.2",
        "xgrammar": "0.2.8", "huggingface_hub": "1.30.0", "tokenizers": "0.22.2", "safetensors": "0.8.0",
        "datasets": "4.3.0", "xformers": "0.0.35", "triton": "3.6.0", "cut_cross_entropy": "25.1.1",
        "pillow": "12.3.0", "hf_xet": "1.6.0", "torchao": "0.18.0"}


def installed(dist):
    for n in dict.fromkeys((dist, dist.replace("_", "-"), dist.lower())):
        try:
            return m.version(n)
        except m.PackageNotFoundError:
            pass
    return None


bad = {k: (installed(k), v) for k, v in pins.items() if installed(k) != v}
print(" · ".join(f"{k} {installed(k)}" for k in pins), "| cuda", torch.version.cuda)
if bad:
    raise SystemExit(f"เวอร์ชันไม่ตรงชุด A (ได้, ต้อง): {bad}")
EOF
$PY -c "import unsloth; from unsloth_zoo.temporary_patches.moe_utils import moe_lora_b_layout as f; v = f(); print('moe_lora_b_layout', v); assert v == 'grouped_by_expert', v" > $L/layout_env.log 2>&1 \
  || { tail -5 $L/layout_env.log; fail layout_env; }
tail -1 $L/layout_env.log
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -dc 0-9)
[ "${MEM:-0}" -ge 90000 ] || fail gpu_small
df -h /workspace | tail -1

if ! have download; then
  AVAIL=$(df --output=avail -BG /workspace | tail -1 | tr -dc 0-9)
  [ "${AVAIL:-0}" -ge 300 ] || fail disk_small     # base 72 + fold 15 + soup 15 + merged 67 + vLLM ~15 GB + เผื่อ destrier 72
  step "โหลด base (unsloth/Qwen3.6-35B-A3B ~72GB)"
  for n in 1 2 3 4 5 6; do
    $PY - <<'EOF' && break
import time
from huggingface_hub import snapshot_download
t = time.time()
b = snapshot_download("unsloth/Qwen3.6-35B-A3B", max_workers=8)
open("/workspace/ft/base_path", "w").write(b)
print("BASE", b, f"{time.time()-t:.0f}s", flush=True)
EOF
    echo "โหลดสะดุดรอบที่ $n — รอ 20 วิแล้วลองต่อ"; sleep 20
    [ $n = 6 ] && fail download
  done
  ok download
fi
BASE=$(cat $FT/base_path)

if ! have soup; then
  step "สิทธิ์อ่าน fold repo (private — token อ่านอย่างเดียว · Lesson 22) + ตัว soup ต้องเป็นฉบับ t07"
  $PY - <<'EOF' || fail hf_access
import os
import sys
from huggingface_hub import HfApi, get_token
print("มี token บนการ์ด:", bool(get_token()))      # ห้ามพิมพ์ตัว token
bad = []
for c in "abcd":
    r = os.environ["FOLD_REPO"].format(c)
    try:
        names = {s.rfilename for s in HfApi().model_info(r).siblings}
        miss = {"adapter_model.safetensors", "adapter_config.json"} - names
        print(r, "OK" if not miss else f"ขาด {sorted(miss)}")
        bad += [r] if miss else []
    except Exception as e:
        print(r, f"อ่านไม่ได้ ({type(e).__name__}) — private หรือไม่มีจริง บอกไม่ได้ (Lesson 22)")
        bad.append(r)
sys.exit(1 if bad else 0)
EOF
  HELP=$($PY $T/soup_safetensors.py --help 2>&1)
  for f in --fold-repo --out-repo; do
    echo "$HELP" | grep -q -- "$f" || { echo "soup_safetensors.py ยังไม่มี $f (ต้องเป็นฉบับ t07 — D11)"; fail soup_cli; }
  done
  $PY $T/test_soup_layout.py > $L/test_soup_layout.log 2>&1 || { tail -20 $L/test_soup_layout.log; fail soup_selftest; }
  tail -1 $L/test_soup_layout.log
  step "soup 4 fold → $SOUP (ไม่ push)"
  W=/workspace/soupwork; rm -rf $W $SOUP; mkdir -p $W
  OUTDIR=""; echo "$HELP" | grep -q -- '--out-dir' && OUTDIR="--out-dir $SOUP"
  ( cd $W && $PY $T/soup_safetensors.py --folds 0 1 2 3 --fold-repo "$FOLD_REPO" --out-repo $SOUP_REPO $OUTDIR ) 2>&1 | tee $L/soup.log
  [ ${PIPESTATUS[0]} = 0 ] || fail soup
  if [ ! -f $SOUP/adapter_model.safetensors ]; then    # ตัว soup ไม่มี --out-dir → หาโฟลเดอร์ที่มันเซฟไว้ใต้ $W
    F=$(find $W -maxdepth 2 -name adapter_model.safetensors | head -1)
    [ -n "$F" ] || fail soup_outdir
    mv "$(dirname "$F")" $SOUP
  fi
  $PY - "$SOUP" <<'EOF' || fail soup_cfg
import json
import sys
c = json.load(open(sys.argv[1] + "/adapter_config.json", encoding="utf-8"))
print("soup r", c.get("r"), "alpha", c.get("lora_alpha"), "lora_B_layout", c.get("lora_B_layout"))
assert c.get("r") == 64 and c.get("lora_alpha") == 128 and c.get("lora_B_layout") == "grouped_by_expert", \
    "ต้องเป็น r64 / alpha128 / grouped_by_expert (4 fold × r16/alpha32)"
EOF
  sha256sum $SOUP/adapter_model.safetensors | tee $L/soup.sha256
  ok soup
fi

if ! have merge; then
  step "merge (merge_lora_to_base.py --adapter $SOUP --out $MERGED)"
  rm -rf $MERGED
  $PY $T/merge_lora_to_base.py --adapter $SOUP --out $MERGED || fail merge
  du -sh $MERGED; ls $MERGED | head -40
  ok merge
fi

if ! have verifyAB; then
  step "ตรวจ A+B (ไม่ใช้ GPU)"
  $PY $T/verify_merge.py --check-ab --base "$BASE" --merged $MERGED --adapter $SOUP --experts 16 || fail verifyAB
  ok verifyAB
fi

if ! have verifyC; then
  step "ตรวจ C (fingerprint adapter / merged / base / base-unsloth แล้วเทียบ)"
  $PY $T/verify_merge.py --fingerprint adapter --adapter $SOUP --out $FT/ref.pt || fail verifyC_ref
  $PY $T/verify_merge.py --fingerprint merged --merged $MERGED --out $FT/mrg.pt || fail verifyC_mrg
  $PY $T/verify_merge.py --fingerprint base --base-repo "$BASE" --out $FT/base.pt || fail verifyC_base
  $PY $T/verify_merge.py --fingerprint base-unsloth --base-repo "$BASE" --out $FT/base_u.pt || fail verifyC_base_unsloth
  $PY $T/verify_merge.py --compare $FT/ref.pt $FT/mrg.pt $FT/base.pt $FT/base_u.pt || fail verifyC
  ok verifyC
fi

if ! have tokenizer; then
  step "tokenizer (Lesson 20): sha ของ merged = base (proof/06) + id ภาษาไทยเท่ากัน ใน /venv/main (ชุดเทรน)"
  BSHA=$(sha256sum "$BASE/tokenizer.json" | awk '{print $1}')
  MSHA=$(sha256sum $MERGED/tokenizer.json | awk '{print $1}')
  echo "tokenizer.json · proof/06 $BASE_TOK_SHA · base snapshot $BSHA · merged $MSHA" | tee $L/tokenizer_sha.txt
  [ "$BSHA" = "$BASE_TOK_SHA" ] || fail base_tokenizer_changed   # base บน HF ไม่ใช่ตัวที่ตรวจไว้ = หยุดให้คนดู
  $PY $G/tok_parity.py --base "$BASE" --merged $MERGED --ids-out $L/thai_ids.json || fail tok_parity_main
  [ "$MSHA" = "$BASE_TOK_SHA" ] || fail tokenizer_sha
  ok tokenizer
fi

step "รอ venv ของ vLLM (vllm_engines.sh ลงขนานอยู่)"
while ! have venv_vllm; do
  [ -f $FT/FAIL_venv_vllm ] && { tail -20 $L/venv_vllm.log 2>/dev/null; fail venv_vllm; }
  sleep 20
done

if ! have tokenizer_vllm; then
  step "tokenizer ใน venv ของ vLLM (transformers 5.18.0 = ตัวที่เสิร์ฟจริง) เทียบ id ของชุดเทรน"
  $VPY $G/tok_parity.py --base "$BASE" --merged $MERGED --ids-ref $L/thai_ids.json || fail tok_parity_vllm
  ok tokenizer_vllm
fi

if ! have gateD; then
  if ! curl -sf -m 5 localhost:8000/v1/models > /dev/null; then
    if pgrep -f "$PAT" > /dev/null; then
      echo "มีตัวเสิร์ฟรันอยู่แล้ว — รอให้พร้อม ไม่เปิดซ้อน (จะเปลี่ยนโมเดลต้องรัน gate4/stop_server.sh ก่อน)"
    else
      step "เปิด vLLM จาก $MERGED (คำสั่งจาก presentation.launch_cmd — gate4/launch_vllm_palfrey.txt)"
      setsid --fork nohup bash -c "$(cat $G/launch_vllm_palfrey.txt)" > $L/serve_palfrey.log 2>&1 < /dev/null &
      sleep 20
    fi
    T0=$(date +%s)
    while ! curl -sf -m 5 localhost:8000/v1/models > /dev/null; do
      pgrep -f "$PAT" > /dev/null || { tail -40 $L/serve_palfrey.log; fail serve; }
      [ $(( $(date +%s) - T0 )) -gt 3600 ] && { tail -40 $L/serve_palfrey.log; fail serve_timeout; }
      sleep 15
    done
    echo "vLLM พร้อม (รอ $(( $(date +%s) - T0 + 20 )) วิ)" | tee $L/ready_s_palfrey
  fi
  step "ด่าน D (gate_d_t07.py — เกณฑ์ที่ตัดสินแล้ว 11 พ.ย.)"
  $PY $G/gate_d_t07.py --url http://localhost:8000 --ref $FT/mrg.pt --merged $MERGED --tune $T > $L/probeD_palfrey.log 2>&1
  RC=$?
  cat $L/probeD_palfrey.log
  [ $RC = 0 ] || fail gateD
  ok gateD
fi

if ! have merged_sha; then
  step "sha256 ทุกไฟล์ของ merged (Lesson 23 — ทำหลังด่าน tokenizer เผื่อมีการแก้ไฟล์เล็ก · ไว้เทียบกับ HF หลัง push)"
  ( cd $MERGED && find . -maxdepth 1 -type f -printf '%f\n' | sort | xargs sha256sum ) > $L/merged_sha256.txt || fail merged_sha
  echo "$(wc -l < $L/merged_sha256.txt) ไฟล์ → $L/merged_sha256.txt"
  ok merged_sha
fi
ok gate4_ready
step "พร้อมวัด — ต่อด้วย: bash $G/run_bench_t07.sh t07   (ดู RUNBOOK_gate4.md)"
