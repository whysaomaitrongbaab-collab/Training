# Vast.ai template — Constistant fine-tune (Qwen3-VL-8B + Unsloth)

Instance picked (2026-07-02): **Type #35961802** — RTX 3090, 24GB VRAM, PCIe 4.0 x16,
AMD EPYC 7532 32-core (16/64 CPU alloc), 32/129 GB RAM alloc, NVMe, verified host,
~$0.152/hr + bandwidth, 99.32% reliability, max duration 5 mon.

## Model decision status

This template defaults to **Qwen3-VL-8B-Instruct**. That is *not* yet the final
decision — see `AGENTS.md` (main Constistant repo) section 16, which still lists
Qwen2-VL-7B as the agreed Primary Model pending King's sign-off. Update
`onstart.sh` if the decision changes.

## Create the Vast.ai template

In the Vast.ai console (Templates → New Template):

1. **Image**: pick a CUDA-enabled PyTorch image (e.g. an official `pytorch/pytorch`
   CUDA 12.1 runtime tag, or Vast.ai's built-in "PyTorch (cuDNN Runtime)" template as
   a base) — must support Ampere (RTX 3090).
2. **Disk space**: at least **60-80 GB** (model weights ~16GB bf16 + checkpoints +
   dataset images + Unsloth/deps ~5-10GB — leave headroom).
3. **On-start script**: paste the contents of [onstart.sh](onstart.sh).
4. **Ports**: expose Jupyter (8888) or SSH depending on how you plan to drive
   training interactively vs. as a batch job.
5. Launch against the RTX 3090 offer above (or any equivalent 24GB Ampere card if
   that one is gone by the time you launch).

## What onstart.sh does

- Installs Unsloth (with the Ampere-tagged fallback if the plain `pip install unsloth`
  doesn't resolve correctly for the image's CUDA/torch combo)
- Installs `trl`, `peft`, `accelerate`, `bitsandbytes`, `xformers`, `qwen-vl-utils`, `pillow`
- Creates `/workspace/constistant-finetune/{data,checkpoints,logs}`

## What it does NOT do (still manual)

- Does not download the base model or dataset — no `dataset.jsonl` exists yet
  (see `training-data/CLAUDE.md` "สิ่งที่ยังไม่ได้ทำ" — extraction is only done for
  1 of 9 houses, no annotated pairs exist yet, no assembly script has been run)
- Does not run the actual training loop — that's the Unsloth Qwen3-VL fine-tuning
  notebook (linked in onstart.sh's output), adapted once real data exists
- Does not pick between Qwen2-VL-7B / Qwen3-VL-8B / Qwen3-VL-30B-A3B — that's King's
  call per AGENTS.md
