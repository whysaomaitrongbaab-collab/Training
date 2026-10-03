#!/bin/bash
# รอบสอง: vLLM/SGLang หลังแก้ CUDA_HOME (nvcc 13 จาก venv) — รอ Unsloth micro ของ runall รอบแรกจบก่อน (GPU ใบเดียว)
cd /workspace/ft || exit 1
while [ ! -f DONE_all ]; do sleep 20; done
rm -f FAIL_vllm_serve FAIL_sglang_serve
bash phaseB.sh vllm house > logs/phaseB_vllm.log 2>&1
bash phaseB.sh sglang house > logs/phaseB_sglang.log 2>&1
touch DONE_all2
