#!/bin/bash
# phase A บนการ์ด: โหลด → ซ่อม destrier → merge → ตรวจ A+B → ตรวจ C
# รันซ้ำได้ — ขั้นที่ผ่านแล้วมีไฟล์ DONE_<ขั้น> จะข้าม · ล้มขั้นไหนเขียน FAIL_<ขั้น> แล้วหยุด
set -u
FT=/workspace/ft; L=$FT/logs; mkdir -p $L
PY=/venv/main/bin/python
export HF_HUB_DISABLE_XET=1 UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FIXED=/workspace/destrier_fixed; MERGED=/workspace/destrier_merged
step(){ echo; echo "=== $(date '+%F %T') $1"; }
ok(){ touch $FT/DONE_$1; echo "--- DONE $1 $(date '+%T')"; }
fail(){ echo "!!! FAIL $1"; touch $FT/FAIL_$1; exit 1; }
have(){ [ -f $FT/DONE_$1 ]; }
cd $FT/tune || exit 1

step "รอ pip ของ onstart"
# รอเฉพาะ pip ของ onstart (/venv/main) — ไม่รอ uv ที่กำลังลง vLLM/SGLang คนละ venv อยู่ขนานกัน
while pgrep -f '[v]env/main/bin/python -m pip install -U' > /dev/null; do sleep 10; done
tail -3 /workspace/pip.log 2>/dev/null
$PY -c "import torch,transformers,peft,unsloth,unsloth_zoo; from importlib import metadata as m
print('torch',torch.__version__,'cuda',torch.version.cuda,'| transformers',transformers.__version__,'| peft',peft.__version__,'| unsloth',m.version('unsloth'),'| zoo',m.version('unsloth_zoo'))" || fail deps
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
df -h /workspace | tail -1

if ! have download; then
  step "โหลด base + destrier"
  # เน็ตเครื่องนี้ไป HF สะดุดเป็นพักๆ (SSL handshake timeout ที่ 48/72 GB) — ลองซ้ำ ของที่โหลดแล้วอยู่ใน cache
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

if ! have fix; then
  step "โหลด destrier e229403 (16 ช่วงขนาน + ตรวจ sha256)"
  if [ ! -f $FT/DONE_dl_destrier ]; then bash $FT/dl_destrier.sh || fail dl_destrier; touch $FT/DONE_dl_destrier; fi
  step "ซ่อม destrier (fix_destrier_layout.py)"
  $PY fix_destrier_layout.py --src /workspace/destrier_src --out $FIXED || fail fix
  sha256sum $FIXED/adapter_model.safetensors | tee $L/fixed.sha256
  ok fix
fi

if ! have merge; then
  step "merge (merge_lora_to_base.py)"
  rm -rf $MERGED
  $PY merge_lora_to_base.py --adapter $FIXED --out $MERGED || fail merge
  du -sh $MERGED; ls $MERGED
  ok merge
fi

if ! have verifyAB; then
  step "ตรวจ A+B (ฟรี ไม่ใช้ GPU)"
  $PY verify_merge.py --check-ab --base "$BASE" --merged $MERGED --adapter $FIXED --experts 16 || fail verifyAB
  ok verifyAB
fi

if ! have verifyC; then
  step "ตรวจ C (fingerprint adapter / merged / base)"
  $PY verify_merge.py --fingerprint adapter --adapter $FIXED --out $FT/ref.pt || fail verifyC_ref
  $PY verify_merge.py --fingerprint merged --merged $MERGED --out $FT/mrg.pt || fail verifyC_mrg
  $PY verify_merge.py --fingerprint base --base-repo "$BASE" --out $FT/base.pt || fail verifyC_base
  $PY verify_merge.py --compare $FT/ref.pt $FT/mrg.pt $FT/base.pt || fail verifyC
  ok verifyC
fi
step "phase A จบ"
touch $FT/DONE_phaseA
