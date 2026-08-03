#!/usr/bin/env python3
"""
export_gguf.py — merge LoRA + export to GGUF + push to HuggingFace, in one step.

Replaces the old manual pipeline from 2026-07-21 (merge_lora.py → convert_hf_to_gguf.py →
llama-quantize) that cost hours of debugging (q8_0-can't-requantize mistake, disk full
3x, llama.cpp CUDA build failing 3x) and, in the end, never got backed up before the
rented instance was destroyed. See No_touch_box/docs/rule_of_tune.md's Mark of Shame
section for the full story (standalone mark_of_shame.md doc was deleted 2026-07-24).

★ t02: ปรับจากของ t01 ให้เป็น Qwen3-VL-30B-A3B แล้ว (2026-07-28) — path/repo/ขนาดที่ตรวจ
ทั้งหมดผูกกับ MODEL_SIZE ตัวเดียวกับ train_qwen3vl.py จึงเลื่อนออกจากกันไม่ได้

Key insight that makes this version simpler and safer: our LoRA only ever trains
language/attention/MLP layers (finetune_vision_layers=False in train_qwen3vl.py — vision
is frozen). That means our fine-tuned model's vision encoder is BYTE-IDENTICAL to the
base model's. We do NOT need to extract/regenerate mmproj at all — we just reuse the
official mmproj-F16.gguf from the matching -GGUF repo. ยืนยันสดด้วย HF API 2026-07-28:
unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF มี mmproj-BF16 / mmproj-F16 (1.08 GB) / mmproj-F32
ครบ และมี Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf (18.6 GB) ไว้เทียบขนาดผลลัพธ์ของเรา
No llama.cpp vision-surgery script, no risk of it silently not supporting this architecture.

Unsloth's model.save_pretrained_gguf() does the convert + quantize in one call (no manual
llama.cpp CLI commands, no q8_0-vs-f16 requantize trap). It calls llama.cpp's own
conversion scripts internally.

⚠️ 2026-07-21 correction: an earlier version of this script called save_pretrained_gguf()
directly on the PeftModel (adapter attached, not merged) — checked against real GitHub
issue reports on unslothai/unsloth afterward and found this is a KNOWN silent-failure
mode: it can export the untrained BASE model with the adapter weights simply not applied,
with no error and no warning. The script would still "succeed," still upload, still pass
the HF-existence check below — and the GGUF would just be the untuned model. This script
now explicitly calls model.merge_and_unload() first (the documented-safe pattern) AND
runs a cheap post-merge sanity generation (see Step 0 below) to catch this class of
failure BEFORE spending 20-40 minutes on quantization + upload of a useless file.

Usage (run right after train_qwen3vl.py finishes, same instance, same MODEL_SIZE):
    MODEL_SIZE=30B-A3B HF_TOKEN=hf_xxx HF_REPO=Sicilian44/qwen3vl-30b-thai-rc python3 export_gguf.py

⛔ HF_REPO ห้ามชี้ไปที่ Sicilian44/qwen36-thai-rc (ของ t01) — Phase 7.5 ต้องใช้เทียบ ทับแล้วจบเลย

⚠️ rule_of_tune.md Mark of Shame rule #2: this script pushes to HuggingFace BEFORE
printing the "safe to destroy instance" message. Do not destroy the instance based on
this script merely exiting without error — wait for the final printed confirmation,
which only appears after the upload is verified via the HF API (file exists, size matches).
"""
import os, sys, json
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO = os.environ.get("HF_REPO")  # e.g. "Sicilian44/qwen3vl-30b-thai-rc"
if not HF_TOKEN or not HF_REPO:
    print("❌ Set HF_TOKEN and HF_REPO env vars first, e.g.:")
    print('   MODEL_SIZE=30B-A3B HF_TOKEN=hf_xxx HF_REPO=Sicilian44/qwen3vl-30b-thai-rc python3 export_gguf.py')
    sys.exit(1)
if HF_REPO.strip().lower().endswith("/qwen36-thai-rc"):
    # Phase 7.5 ต้องวัด adapter ของ t01 ซ้ำบนเครื่องเดียวกัน ถ้าทับ repo นั้นทิ้ง = A/B จบเห่
    print("⛔ HF_REPO ชี้ไปที่ repo ของ t01 — ห้ามทับ ต้องเก็บไว้เทียบใน Phase 7.5")
    sys.exit(1)

QUANT_METHOD = os.environ.get("QUANT_METHOD", "q4_k_m")  # ตรงกับเครื่องมะขาม (~18.6GB, 31GB RAM + 8GB VRAM)

# ── ทุกอย่างผูกกับ MODEL_SIZE ตัวเดียวกับ train_qwen3vl.py ห้ามฮาร์ดโค้ดแยก
#    (OUT_DIR ของ train คือ f"outputs_{SIZE.lower().replace('-','')}" — สูตรเดียวกันเป๊ะ)
TARGETS = {
    "30B-A3B": dict(model_id="unsloth/Qwen3-VL-30B-A3B-Instruct",
                    mmproj_repo="unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF",
                    gguf_gb=(14, 24)),   # อ้างอิง: Q4_K_M ทางการของ repo นี้ = 18.6 GB
    "8B":      dict(model_id="unsloth/Qwen3-VL-8B-Instruct",
                    mmproj_repo="unsloth/Qwen3-VL-8B-Instruct-GGUF",
                    gguf_gb=(3, 8)),
    "32B":     dict(model_id="unsloth/Qwen3-VL-32B-Instruct",
                    mmproj_repo="unsloth/Qwen3-VL-32B-Instruct-GGUF",
                    gguf_gb=(15, 26)),
}
SIZE = os.environ.get("MODEL_SIZE", "30B-A3B").upper()
if SIZE not in TARGETS:
    sys.exit(f"❌ MODEL_SIZE={SIZE} ไม่รู้จัก — เลือกจาก {list(TARGETS)}")
T = TARGETS[SIZE]

OUT_DIR = f"outputs_{SIZE.lower().replace('-', '')}"
ADAPTER_DIR = f"{OUT_DIR}/lora"
LOCAL_GGUF_DIR = f"{OUT_DIR}/gguf"
MODEL_ID = T["model_id"]
GGUF_MIN_GB, GGUF_MAX_GB = T["gguf_gb"]

# Official mmproj — reused as-is, NOT regenerated (see module docstring for why this is safe)
OFFICIAL_MMPROJ_REPO = T["mmproj_repo"]
OFFICIAL_MMPROJ_FILE = "mmproj-F16.gguf"  # 1.08 GB, ยืนยันสดผ่าน HF API tree 2026-07-28

if not Path(ADAPTER_DIR).is_dir():
    sys.exit(f"❌ ไม่มี {ADAPTER_DIR} — MODEL_SIZE ตรงกับตอนเทรนหรือเปล่า "
             f"(train_qwen3vl.py เขียนลง outputs_<size>/lora)")
print(f"[{SIZE}] adapter={ADAPTER_DIR}  base={MODEL_ID}  mmproj={OFFICIAL_MMPROJ_REPO}")

print(f"Loading base model + LoRA adapter from {ADAPTER_DIR} ...")
from unsloth import FastVisionModel
model, tokenizer = FastVisionModel.from_pretrained(MODEL_ID, load_in_4bit=False)

from peft import PeftModel
model = PeftModel.from_pretrained(model, ADAPTER_DIR)
print("✓ Adapter attached")

# ── Step 0: MERGE explicitly, then SANITY-CHECK the merge actually applied our tuning —
# do this BEFORE the 20-40 min quantization step, so a silent no-op merge is caught cheap.
print("Merging LoRA into base weights (merge_and_unload) ...")
model = model.merge_and_unload()
assert not hasattr(model, "peft_config"), "❌ Model still looks like a PeftModel after merge_and_unload() — merge did not complete. STOP, do not export."
print("✓ Merged — model is now a plain model, no adapter wrapper left")

print("Sanity-checking the merge actually changed behavior vs. the untuned base model ...")
import json as _json
FastVisionModel.for_inference(model)
with open(HERE_VAL := Path("val.jsonl"), encoding="utf-8") as f:
    _lines = f.readlines()
# val.jsonl's FIRST line is an index+material-list+signature-block page that the model
# tends to over-generate on (13,991 chars / 4096 tokens and still not done — a real
# over-prediction tendency of this tuning round, not a merge failure; see Phase 7's
# actual eval showing 78 over-predicted elements). Line 3 (a compact structural plan
# page, confirmed valid+fast in the real Phase 7 eval run) is a more representative
# quick sanity check. Fixed 2026-07-24.
_sample = _json.loads(_lines[2])
_msgs = [_sample["messages"][0]]
_text = tokenizer.apply_chat_template(_msgs, add_generation_prompt=True, enable_thinking=False)  # found 2026-07-24, see eval_fields.py note
from PIL import Image as _Image
_imgs = [_Image.open(c["image"]).convert("RGB") for c in _msgs[0]["content"] if c["type"] == "image"]
_inputs = tokenizer(_imgs, _text, add_special_tokens=False, return_tensors="pt").to("cuda")
_out = model.generate(**_inputs, max_new_tokens=1200, do_sample=False)  # only need the opening structure, not a full completion — see check below
_pred = tokenizer.decode(_out[0][_inputs["input_ids"].shape[1]:], skip_special_tokens=True)
# Checking full json.loads() success is too fragile here: this tuning round genuinely
# tends to over-generate on complex pages (confirmed in Phase 7's real eval — 78
# over-predicted elements across 20 examples), and tiny bf16 rounding differences between
# merge_and_unload()'s merged weights and the adapter-applied-at-runtime math used in
# eval_fields.py can make a long greedy generation diverge and run past any fixed token
# budget on some examples — none of that means the merge silently failed. What we
# actually need to rule out is the KNOWN failure mode: a silently-unmerged model reverts
# to the untuned base's behavior, which (confirmed via the Phase 0.3 dry run and the
# 2026-07-21 baseline) looks nothing like this — either a "Here's a thinking process"
# prose preamble, or generic non-schema text, not real schema JSON. So: check the START
# of the output looks like genuine tuned-schema JSON, not that the whole thing parses.
_looks_tuned = _pred.lstrip().startswith("{") and any(k in _pred[:400] for k in ('"png"', '"views"', '"pattern"', '"doc_page"'))
if _looks_tuned:
    print(f"✓ Sanity check passed — merged model opens with real schema JSON, not a reasoning preamble or generic text (matches tuned behavior, not the untuned baseline)")
else:
    print(f"❌ SANITY CHECK FAILED — merged model's output does NOT look like tuned schema JSON:")
    print(f"   output length: {len(_pred)} chars, {_out.shape[1] - _inputs['input_ids'].shape[1]} tokens generated")
    print(f"   first 400: {_pred[:400]}")
    print("🔴 This matches the known silent-merge-failure pattern (adapter not actually")
    print("   applied). STOP. Do not spend time quantizing/uploading this. Investigate")
    print("   before continuing — check merge_and_unload() output and adapter path.")
    sys.exit(1)
del _inputs, _out
import torch as _torch, gc as _gc
_gc.collect(); _torch.cuda.empty_cache()

# ── Step 1: convert + quantize (Unsloth calls llama.cpp's conversion internally)
print(f"Exporting merged model to GGUF ({QUANT_METHOD}) — this can take 20-40 min, be patient, do NOT interrupt ...")
print("(If disk space runs low mid-export: safe to delete is the HF hub cache — ~/.cache/huggingface —")
print(f" since the model is already loaded in GPU memory. Do NOT delete anything in {OUT_DIR}/.)")
Path(LOCAL_GGUF_DIR).mkdir(parents=True, exist_ok=True)
# ★ t02 note (2026-07-28): เหตุผลของ patch นี้ "เปลี่ยนไปครึ่งหนึ่ง" แต่ยังต้องเก็บไว้
#   ของ t01 patch เพราะ llama.cpp แปลง vision ของ Qwen3.6 ไม่ได้เลย — ส่วน Qwen3-VL
#   llama.cpp รองรับแล้วจริง (ตรวจไบนารีที่เครื่องมะขาม b10105: llama.dll มี qwen3vl/
#   qwen3vlmoe, mtmd.dll มี qwen3vl) ฉะนั้น auto-export อาจ "ทำงานได้" รอบนี้
#   แต่เรายัง**ไม่ต้องการ**มันอยู่ดี: เราใช้ mmproj ทางการที่ vision ถูก freeze ไว้แล้ว
#   ปล่อยให้ auto-export ทำงาน = เพิ่มเวลา + เพิ่มความเสี่ยงโดยไม่ได้อะไรกลับมา
#   (unsloth issue #3899 เคยรายงาน GGUF ของ Qwen3-VL-2B ออกมาเพี้ยน) → คง patch ไว้
#
# Found 2026-07-24: Unsloth auto-detects this as a VLM (model.config has vision_config)
# and, as PART OF THE SAME call, also tries to auto-export a vision-projector GGUF —
# which fails hard on this architecture (llama.cpp's converter can't find the vision
# tensors: "no tensors were written... Check that the safetensors filenames are
# discoverable") and takes down the WHOLE export (including the already-working text/LLM
# conversion) with it. We deliberately don't want Unsloth's auto-mmproj export anyway —
# the whole point of this script (see module docstring) is reusing the official
# pre-built mmproj-F16.gguf instead, since vision layers were frozen during training.
#
# FIRST ATTEMPT (reverted): deleting model.config.vision_config to fake is_vlm=False.
# This broke the MAIN text save too — inspecting the resulting safetensors afterward
# showed triple-nested tensor names (`model.language_model.language_model.language_model.
# ...`), because is_vlm also changes how unsloth_save_pretrained_gguf unwraps/saves the
# model itself, not just the GGUF conversion step. Confirmed corrupt: that's WHY the
# "no tensors were written" error persisted even after the mmproj skip.
#
# REAL FIX: unsloth_zoo.llama_cpp.convert_to_gguf already has a graceful fallback for
# exactly this situation — `if is_vlm and supported_vision_archs is not None: if arch not
# in supported_vision_archs: is_vlm = False` (converts as text-only, no crash). It just
# never fires here because save_to_gguf() calls convert_to_gguf() without passing
# supported_vision_archs at all (stays None), so the check that would set is_vlm=False
# never activates for an architecture nobody's added to that list yet. Monkey-patch
# `unsloth.save.convert_to_gguf` (the name as imported into unsloth.save's own namespace —
# patching unsloth_zoo.llama_cpp's copy wouldn't affect the already-bound import) so the
# call always supplies supported_vision_archs=set(), triggering Unsloth's own intended
# safe path instead of inventing a new one. Leaves model.save_pretrained() completely
# untouched — only affects the GGUF conversion step.
import unsloth.save as _unsloth_save_mod
_orig_convert_to_gguf = _unsloth_save_mod.convert_to_gguf
def _convert_to_gguf_text_only(*_args, **_kwargs):
    # save_to_gguf() calls convert_to_gguf(..., supported_vision_archs=supported_vision_archs, ...)
    # EXPLICITLY (confirmed by reading its source) — the key is always present in kwargs,
    # even when its value is None, so .setdefault() (tried first, silently did nothing) never
    # takes effect. Must force-overwrite the value directly, not just supply a default.
    _kwargs["supported_vision_archs"] = set()
    return _orig_convert_to_gguf(*_args, **_kwargs)
_unsloth_save_mod.convert_to_gguf = _convert_to_gguf_text_only

model.save_pretrained_gguf(LOCAL_GGUF_DIR, tokenizer, quantization_method=QUANT_METHOD)
print(f"✓ GGUF export done — check {LOCAL_GGUF_DIR}/ for the .gguf file")

# ── Step 2: fetch the official (unchanged) mmproj file alongside our fine-tuned LLM gguf
from huggingface_hub import hf_hub_download, HfApi, upload_file

print(f"Downloading official mmproj ({OFFICIAL_MMPROJ_FILE}, ~1.08GB, vision encoder — unchanged by our LoRA) ...")
mmproj_path = hf_hub_download(repo_id=OFFICIAL_MMPROJ_REPO, filename=OFFICIAL_MMPROJ_FILE)
print(f"✓ mmproj ready at {mmproj_path}")

# ── Step 3: find the produced GGUF file
# Found 2026-07-24: Unsloth's save_pretrained_gguf() writes the actual final .gguf files
# to "{LOCAL_GGUF_DIR}_gguf/" (note the appended "_gguf" suffix on the directory name) —
# LOCAL_GGUF_DIR itself only ever holds the intermediate merged HF-format safetensors.
# The original glob on LOCAL_GGUF_DIR always found nothing, incorrectly reporting the
# whole export as failed even when the GGUF was sitting right there one directory over.
gguf_files = list(Path(f"{LOCAL_GGUF_DIR}_gguf").glob("*.gguf"))
if not gguf_files:
    print(f"❌ No .gguf file found in {LOCAL_GGUF_DIR}_gguf/ — export_gguf step above may have failed silently. STOP. Do not destroy the instance. Investigate first.")
    sys.exit(1)
llm_gguf = gguf_files[0]
llm_gguf_size_gb = llm_gguf.stat().st_size / 1e9
print(f"Found LLM GGUF: {llm_gguf} ({llm_gguf_size_gb:.1f} GB)")

# Sanity check on size — เทียบกับ Q4_K_M ทางการของรุ่นเดียวกัน (30B-A3B = 18.6 GB ยืนยันสด
# ผ่าน HF API 2026-07-28) ดักเคสเขียนไฟล์ค้างกลางทาง (disk เต็ม) ที่ยังทิ้งไฟล์ไว้บนดิสก์
# จนดู "เสร็จแล้ว" เพราะไฟล์มีอยู่จริง
if llm_gguf_size_gb < GGUF_MIN_GB or llm_gguf_size_gb > GGUF_MAX_GB:
    print(f"❌ GGUF size ({llm_gguf_size_gb:.1f} GB) อยู่นอกช่วงที่คาด "
          f"{GGUF_MIN_GB}-{GGUF_MAX_GB} GB สำหรับ {SIZE} q4_k_m")
    print("🔴 This suggests a truncated/incomplete write (disk full mid-export?) or wrong quant method.")
    print("   STOP. Do not upload or destroy the instance. Check disk space (df -h) and re-run export.")
    sys.exit(1)

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
print(f"   - mmproj-F16.gguf (1.08 GB)")
print(f"   - lora-adapter/ (backup)")
print()
print("It is now safe to download these to your own PC and, only after that")
print("succeeds too, destroy the rented instance.")
print("=" * 70)
