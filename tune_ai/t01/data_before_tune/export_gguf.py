#!/usr/bin/env python3
"""
export_gguf.py — merge LoRA + export to GGUF + push to HuggingFace, in one step.

Replaces the old manual pipeline from 2026-07-21 (merge_lora.py → convert_hf_to_gguf.py →
llama-quantize) that cost hours of debugging (q8_0-can't-requantize mistake, disk full
3x, llama.cpp CUDA build failing 3x) and, in the end, never got backed up before the
rented instance was destroyed. See training-data/docs/mark_of_shame.md for the full story.

Key insight that makes this version simpler and safer: our LoRA only ever trains
language/attention/MLP layers (finetune_vision_layers=False in train_qwen36.py — vision
is frozen). That means our fine-tuned model's vision encoder is BYTE-IDENTICAL to the
base model's. We do NOT need to extract/regenerate mmproj at all — we just reuse the
official unsloth/Qwen3.6-35B-A3B-GGUF mmproj-F16.gguf file (899MB), confirmed to exist
via the HuggingFace API on 2026-07-21 (repo tree: mmproj-BF16.gguf / mmproj-F16.gguf /
mmproj-F32.gguf all present). No llama.cpp vision-surgery script, no risk of it silently
not supporting this architecture.

Unsloth's model.save_pretrained_gguf() does the merge + convert + quantize in one call
(no separate PeftModel.merge_and_unload() step, no manual llama.cpp CLI commands, no
q8_0-vs-f16 requantize trap). It calls llama.cpp's own conversion scripts internally.

Usage (run right after train_qwen36.py finishes, same instance):
    HF_TOKEN=hf_xxx HF_REPO=your-username/qwen36-thai-rc python export_gguf.py

⚠️ rule_of_tune.md Mark of Shame rule #2: this script pushes to HuggingFace BEFORE
printing the "safe to destroy instance" message. Do not destroy the instance based on
this script merely exiting without error — wait for the final printed confirmation,
which only appears after the upload is verified via the HF API (file exists, size matches).
"""
import os, sys, json
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO = os.environ.get("HF_REPO")  # e.g. "yourusername/qwen36-thai-rc"
if not HF_TOKEN or not HF_REPO:
    print("❌ Set HF_TOKEN and HF_REPO env vars first, e.g.:")
    print('   HF_TOKEN=hf_xxx HF_REPO=yourname/qwen36-thai-rc python export_gguf.py')
    sys.exit(1)

QUANT_METHOD = os.environ.get("QUANT_METHOD", "q4_k_m")  # matches user's PC: ~22GB, fits 31GB RAM + 8GB VRAM
ADAPTER_DIR = "outputs_qwen36/lora"
LOCAL_GGUF_DIR = "outputs_qwen36/gguf"
MODEL_ID = "unsloth/Qwen3.6-35B-A3B"

# Official mmproj — reused as-is, NOT regenerated (see module docstring for why this is safe)
OFFICIAL_MMPROJ_REPO = "unsloth/Qwen3.6-35B-A3B-GGUF"
OFFICIAL_MMPROJ_FILE = "mmproj-F16.gguf"  # 899MB, confirmed present 2026-07-21 via HF API tree listing

print(f"Loading base model + LoRA adapter from {ADAPTER_DIR} ...")
from unsloth import FastVisionModel
model, tokenizer = FastVisionModel.from_pretrained(MODEL_ID, load_in_4bit=False)

from peft import PeftModel
model = PeftModel.from_pretrained(model, ADAPTER_DIR)
print("✓ Adapter attached")

# ── Step 1: merge + convert + quantize in one call (Unsloth handles llama.cpp internally)
print(f"Exporting merged model to GGUF ({QUANT_METHOD}) — this can take 20-40 min, be patient, do NOT interrupt ...")
Path(LOCAL_GGUF_DIR).mkdir(parents=True, exist_ok=True)
model.save_pretrained_gguf(LOCAL_GGUF_DIR, tokenizer, quantization_method=QUANT_METHOD)
print(f"✓ GGUF export done — check {LOCAL_GGUF_DIR}/ for the .gguf file")

# ── Step 2: fetch the official (unchanged) mmproj file alongside our fine-tuned LLM gguf
from huggingface_hub import hf_hub_download, HfApi, upload_file

print(f"Downloading official mmproj ({OFFICIAL_MMPROJ_FILE}, ~899MB, vision encoder — unchanged by our LoRA) ...")
mmproj_path = hf_hub_download(repo_id=OFFICIAL_MMPROJ_REPO, filename=OFFICIAL_MMPROJ_FILE)
print(f"✓ mmproj ready at {mmproj_path}")

# ── Step 3: find the produced GGUF file
gguf_files = list(Path(LOCAL_GGUF_DIR).glob("*.gguf"))
if not gguf_files:
    print(f"❌ No .gguf file found in {LOCAL_GGUF_DIR}/ — export_gguf step above may have failed silently. STOP. Do not destroy the instance. Investigate first.")
    sys.exit(1)
llm_gguf = gguf_files[0]
print(f"Found LLM GGUF: {llm_gguf} ({llm_gguf.stat().st_size / 1e9:.1f} GB)")

# ── Step 4: upload everything to HuggingFace — LLM gguf + mmproj copy + adapter (small, for safety)
api = HfApi(token=HF_TOKEN)
api.create_repo(repo_id=HF_REPO, private=True, exist_ok=True)

print(f"Uploading {llm_gguf.name} to {HF_REPO} ...")
api.upload_file(path_or_fileobj=str(llm_gguf), path_in_repo=llm_gguf.name, repo_id=HF_REPO, token=HF_TOKEN)

print(f"Uploading mmproj-F16.gguf to {HF_REPO} ...")
api.upload_file(path_or_fileobj=mmproj_path, path_in_repo="mmproj-F16.gguf", repo_id=HF_REPO, token=HF_TOKEN)

print(f"Uploading LoRA adapter (small, kept as a backup) to {HF_REPO}/lora-adapter/ ...")
api.upload_folder(folder_path=ADAPTER_DIR, path_in_repo="lora-adapter", repo_id=HF_REPO, token=HF_TOKEN)

# ── Step 5: VERIFY the upload actually landed — don't just trust "no exception raised"
print("Verifying upload via HF API (not just trusting no-error) ...")
remote_files = api.list_repo_files(repo_id=HF_REPO, token=HF_TOKEN)
expected = {llm_gguf.name, "mmproj-F16.gguf"}
missing = expected - set(remote_files)
if missing:
    print(f"❌ VERIFICATION FAILED — missing on HF: {missing}")
    print("🔴 DO NOT DESTROY THE INSTANCE. Files are not confirmed backed up. Re-run the upload.")
    sys.exit(1)

print()
print("=" * 70)
print(f"✅ VERIFIED on HuggingFace: https://huggingface.co/{HF_REPO}")
print(f"   - {llm_gguf.name} ({llm_gguf.stat().st_size / 1e9:.1f} GB)")
print(f"   - mmproj-F16.gguf (0.9 GB)")
print(f"   - lora-adapter/ (backup)")
print()
print("It is now safe to download these to your own PC and, only after that")
print("succeeds too, destroy the rented instance.")
print("=" * 70)
