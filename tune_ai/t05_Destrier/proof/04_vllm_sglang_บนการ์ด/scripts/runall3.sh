#!/bin/bash
# รอบสาม: CUDA_HOME = ชุด CUDA 13.0 ที่ nvcc ตรงกับ header ของ runtime (CCCL บังคับเลขตรงกัน)
cd /workspace/ft || exit 1
rm -rf /root/.cache/flashinfer
for f in FAIL_vllm_serve FAIL_sglang_serve; do [ -f $f ] && mv $f OLD_${f}_cuda134_vs_130; done
bash phaseB.sh vllm house > logs/phaseB_vllm.log 2>&1
bash phaseB.sh sglang house > logs/phaseB_sglang.log 2>&1
touch DONE_all3
