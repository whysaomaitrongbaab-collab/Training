#!/bin/bash
# op04_gpu_setup.sh — ติดตั้ง serve_purson.py บนเครื่องเช่า (สูตร GPU-B ที่พิสูจน์แล้ว 2026-08-31:
# template vastai/pytorch:cuda-12.8.1-auto → /venv/main มี torch 2.11.0+cu128 ตรงกับระบบ = เร็ว ~20x)
# รัน: tr -d '\r' < op04_gpu_setup.sh | ssh -p <PORT> root@<HOST> "bash -s"
set -euo pipefail
cd /workspace
export TORCH_CUDA_ARCH_LIST="12.0"
pip install unsloth xgrammar fastapi uvicorn requests pillow 2>&1 | tail -3
# transformers v5 หน้าต่าง [5.2.0, 5.5.0] — บทเรียน onstart.sh t05 (unsloth ดึง 4.57.6 แล้วตายถ้าไม่ pin)
pip install "transformers>=5.2.0,<=5.5.0" 2>&1 | tail -2
python -c "import torch, transformers, unsloth; print('torch', torch.__version__, '| transformers', transformers.__version__)"
echo SETUP_DONE
