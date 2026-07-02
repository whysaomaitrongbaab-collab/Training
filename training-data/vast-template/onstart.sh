#!/bin/bash
# Vast.ai on-start script — Constistant fine-tune env (Qwen3-VL-8B + Unsloth)
# Tuned for the offer picked 2026-07-02: Type #35961802, RTX 3090 24GB, PCIe 4.0 x16,
# AMD EPYC 7532 32-core, NVMe, ~$0.152/hr.
#
# NOTE: base model is Qwen3-VL-8B here as a working default for this template.
# Per AGENTS.md ("16. Drawing AI — Fine-tuning Architecture"), the officially agreed
# Primary Model is still Qwen2-VL-7B pending King's sign-off — swap MODEL_ID below if
# the decision lands on the original plan instead.

set -euo pipefail

echo "=== Constistant fine-tune setup — Qwen3-VL-8B + Unsloth (RTX 3090 24GB) ==="

pip install --upgrade pip

# Simple path works on most current Linux/CUDA images; fall back to the explicit
# Ampere build tag (RTX 3090 = Ampere) if the plain install fails.
# Docs: https://unsloth.ai/docs/get-started/install/pip-install
pip install unsloth || \
  pip install "unsloth[cu121-ampere-torch230] @ git+https://github.com/unslothai/unsloth.git"

pip install --no-deps trl peft accelerate bitsandbytes xformers
pip install qwen-vl-utils pillow

mkdir -p /workspace/constistant-finetune/data
mkdir -p /workspace/constistant-finetune/checkpoints
mkdir -p /workspace/constistant-finetune/logs
cd /workspace/constistant-finetune

cat <<'MSG'

=== Setup done ===

Next steps (manual, not automated by this script):
1. Upload dataset.jsonl into ./data
   (assembled from training-data/annotated/*.json — see docs/FINETUNING_FLOW.md step 5
   in the main Constistant repo for the exact format)
2. Confirm the base model repo id on the Unsloth / Hugging Face model hub before
   downloading (search "Qwen3-VL-8B" under the unsloth org) — do not hardcode a guess.
3. Use the Unsloth Qwen3-VL vision fine-tuning notebook as the training script template:
   https://unsloth.ai/docs/models/qwen3-vl-how-to-run-and-fine-tune
4. VRAM budget on this GPU (24GB) is tight for an 8B vision model fine-tune — keep
   batch size small (1-2) with gradient accumulation, and use 4-bit loading.

MSG
