#!/bin/bash
# ลง vLLM / SGLang คนละ venv (ไม่แตะ /venv/main ที่ merge กำลังใช้ — กติกา isolate pip installs)
# + deps ของ worker (requests/opencv) แยกที่ /workspace/wdeps แบบเดียวกับแผน A
set -u
FT=/workspace/ft; L=$FT/logs; mkdir -p $L
export PATH=$HOME/.local/bin:$PATH
command -v uv > /dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh > $L/uv_install.log 2>&1
export PATH=$HOME/.local/bin:$PATH
uv --version > $L/uv.version 2>&1 || { touch $FT/FAIL_uv; exit 1; }

(
  for E in vllm sglang; do
    if [ $E = vllm ]; then PKG="vllm==0.30.0"; else PKG="sglang[all]==0.5.21"; fi
    { uv venv /workspace/venv_$E --python 3.12 && \
      uv pip install --python /workspace/venv_$E/bin/python "$PKG"; } > $L/venv_$E.log 2>&1 \
      && touch $FT/DONE_venv_$E || touch $FT/FAIL_venv_$E
    /workspace/venv_$E/bin/python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)" >> $L/venv_$E.log 2>&1
    uv pip list --python /workspace/venv_$E/bin/python 2>/dev/null | grep -iE "^(vllm|sglang|torch|transformers|flashinfer|xgrammar|sglang-kernel) " >> $L/venv_$E.log
  done
) &

# deps ของ worker — รอ pip ของ onstart จบก่อน (pip สองตัวบน interpreter เดียวกันพร้อมกัน = เสี่ยง)
while pgrep -f '[v]env/main/bin/python -m pip install -U' > /dev/null; do sleep 10; done
/venv/main/bin/python -m pip install --target /workspace/wdeps requests opencv-python-headless \
  > $L/wdeps.log 2>&1 && touch $FT/DONE_wdeps || touch $FT/FAIL_wdeps
wait
