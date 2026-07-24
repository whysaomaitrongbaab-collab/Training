# Retune Workflow — Qwen3.6-35B-A3B → Local GGUF, No Ongoing GPU Rental

Written 2026-07-21, after the previous attempt lost all output files (LoRA adapter, merged
model, GGUF) because the rented instance was destroyed before backup. Full incident:
`training-data/docs/mark_of_shame.md`. Rules extracted from that incident: `training-data/docs/rule_of_tune.md`.

**Goal:** end this run with a vision-capable GGUF file running on your own PC (RTX 5060,
8GB VRAM + 31GB RAM), reading Thai construction drawings, with zero ongoing GPU rental —
and a verified backup on HuggingFace before the rented instance is ever destroyed.

**What changed since the last attempt** (why this run should be faster and safer):
1. All script bugs from the last run are already fixed (`train_qwen36.py` — image
   processor config, LoRA/MoE dropout, OOM from LoRA rank). No debugging expected this time.
2. The old manual pipeline (`merge_lora.py` → `convert_hf_to_gguf.py` → `llama-quantize`,
   3+ failure points) is replaced by `export_gguf.py`, which does merge + convert + quantize
   in one Unsloth call.
3. **The vision problem (mmproj) is solved without ever extracting anything.**
   `train_qwen36.py` freezes the vision encoder (`finetune_vision_layers=False`, the
   default) — our LoRA only touches language/attention/MLP layers. That means our
   fine-tuned model's vision encoder is byte-identical to the base model's. We just reuse
   the official `mmproj-F16.gguf` (899MB) already published at
   `unsloth/Qwen3.6-35B-A3B-GGUF` — confirmed to exist via the HuggingFace API on
   2026-07-21 (tree listing showed `mmproj-BF16.gguf` / `mmproj-F16.gguf` / `mmproj-F32.gguf`
   all present). No llama.cpp vision-surgery script, no architecture-support gamble.
4. `export_gguf.py` verifies the HuggingFace upload landed (checks file existence via the
   API, not just "the command didn't error") before printing anything resembling
   "safe to destroy the instance."
5. **A second silent-failure risk was found and closed while reviewing this plan (2026-07-21,
   same day, before ever renting):** the first draft of `export_gguf.py` called
   `save_pretrained_gguf()` directly on the adapter-attached model without an explicit
   merge step. Real GitHub issue reports on `unslothai/unsloth` show this can silently
   export the untuned BASE model — no error, no warning, upload "succeeds," verification
   passes, and the file is just wrong. Fixed by adding an explicit `merge_and_unload()`
   call plus a cheap post-merge sanity generation (checks the merged model actually
   produces valid JSON on a val example, i.e. behaves like the tuned model, not the ~0%
   baseline) — this runs BEFORE the 20-40 min quantization step, so a bad merge is caught
   in seconds, not after wasting rental time on a useless export.

---

## Phase 0 — Prep on your own PC, before renting anything ($0, do this first)

This phase exists because last time, things that could have been checked for free
beforehand turned into paid debugging time on the rented clock. Everything here runs on
your own PC or is a free account signup — no GPU needed.

### 0.1 — HuggingFace account + token
1. Sign up (free) at https://huggingface.co/join if you don't have an account.
2. Go to https://huggingface.co/settings/tokens → **New token** → type **Write** →
   name it e.g. `constistant-tune`.
3. Copy the token (starts `hf_...`) and save it somewhere you can paste from later
   (password manager, or a local text file that is NOT committed to git).
4. **Cost: $0.** Free tier = 100GB private storage (confirmed via HuggingFace's own
   pricing page, 2026). Our total upload this round is ~30GB (LoRA adapter 7.5GB + GGUF
   ~22GB + mmproj copy 0.9GB) — well under the free limit. You do not need PRO ($9/mo).
5. Test the token works, from your own PC, before renting anything:
   ```bash
   curl -s -H "Authorization: Bearer hf_YOUR_TOKEN" https://huggingface.co/api/whoami-v2
   ```
   Should return your username as JSON. If it returns an error, the token is wrong —
   fix this now, not mid-rental.

### 0.2 — Vast.ai account
1. Confirm your Vast.ai account has enough balance for one training run. Budget:
   **$5-10** (see cost estimate in Phase 9). Top up now if needed.
2. SSH key: **already done, reusable forever** — you generated `~/.ssh/id_ed25519` on
   2026-07-21 and added the public key to vast.ai/manage-keys/. Nothing to redo here.

### 0.3 — Local dry run: prove your PC can run the FINAL result, before spending anything
This is the step that would have caught the mmproj problem for free, before ever renting
a GPU. Do this now:

1. Download a **small** quant of the same base model + the official mmproj (no fine-tune
   needed yet, just proving the runtime works). Storage location:
   **`D:\00mk\ai-models\qwen36-thai-rc\`** (created now, kept outside every git repo —
   `Training` has no `.gitignore`, so a repo folder is the wrong place for multi-GB
   binaries — this is also where the real fine-tuned files land later in Phase 9):
   ```bash
   cd "D:\00mk\ai-models\qwen36-thai-rc"
   curl -L -o mmproj-F16.gguf "https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/mmproj-F16.gguf"
   curl -L -o test-model.gguf "https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf"
   ```
   (IQ2_XXS is ~10.8GB — smaller/faster than what we'll actually use, this is only to
   test that the *pipeline* works, not to judge quality.)
2. Get llama.cpp. On Windows, skip building from source — download the prebuilt CUDA
   release directly from https://github.com/ggml-org/llama.cpp/releases (look for a
   `win-cuda-*.zip` asset matching your CUDA version).
3. Run a vision test with a real drawing image from this project (e.g. anything in
   `tune_ai/t01/data_before_tune/images/`):
   ```bash
   llama-cli --model test-model.gguf --mmproj mmproj-F16.gguf --image images/<any_page>.png -p "Describe this drawing."
   ```
4. **If this works** (model produces a coherent description referencing the drawing),
   you've proven: llama.cpp runs on your PC, mmproj loads correctly, your VRAM/RAM can
   host this architecture. When the real fine-tuned GGUF comes back from the rental,
   you're only swapping one file — no new unknowns.
5. **If this fails**, you now know *before* spending any rental money, and can debug the
   local runtime for free instead of on the paid clock. Delete `test-model.gguf`
   afterward (10.8GB, no longer needed) — keep `mmproj-F16.gguf`, you'll reuse it later.

### 0.4 — Re-check the scripts one more time
- `train_qwen36.py` — already fixed from last run (image processor, LoRA dropout, LORA_R=32
  for the OOM fix). No changes needed unless you want to intentionally change something
  (if so, per `rule_of_tune.md` — that requires a warning before proceeding).
- `export_gguf.py` — new this round, replaces `merge_lora.py`. Read it once before
  renting so the commands in Phase 6 below aren't a surprise.
- `eval_fields.py` — unchanged, used for baseline + post-tune measurement.

### 0.5 — Instance sizing checklist (decide before clicking Rent)
| Setting | Value | Why |
|---|---|---|
| GPU | RTX PRO 6000 96GB (Blackwell) or A100/H100 80GB | Confirmed working 2026-07-21. VRAM ≥80GB required for bf16 LoRA (~74GB). |
| Disk | **≥300GB** (raised twice now — 150GB last time, then 200GB, now corrected after actually doing the math) | Last run hit 100%-full disk multiple times even after cleanup. Realistic peak this round, all potentially coexisting at once: base model HF cache (~70GB, already on disk from training) + merged 16-bit intermediate Unsloth writes internally (~66GB) + GGUF f16 intermediate before quantizing (~66GB) + final Q4_K_M (~22GB) ≈ **~225GB just for those**, before any breathing room. 200GB would likely repeat the disk-full saga; 300GB gives actual margin. If you see disk filling up mid-`export_gguf.py` anyway: the safe thing to delete is the HF hub cache (`~/.cache/huggingface`, already loaded into GPU memory by then) — never delete anything under `outputs_qwen36/`. |
| Template | Plain PyTorch + CUDA | NOT "Unsloth Studio" — we run our own scripts via SSH, not their UI. |
| On-start script | Paste `onstart.sh` contents into the instance creation form | Installs Unsloth/Triton/Blackwell env vars automatically on boot. |
| Reliability | ≥95% | Check before renting — avoid flaky hosts. |

---

## Phase 1 — Rent + connect

```bash
# From your PC:
ssh -p <port> root@<ip>          # port/ip from the Vast.ai instance's "Connect" button
```
You land in a `tmux` session automatically (Vast.ai default).

## Phase 2 — Upload dataset + scripts

```bash
# From your PC (a second terminal, don't reuse the SSH session for this):
scp -P <port> -r "d:\00mk\steel project\training\Training\tune_ai\t01\data_before_tune" root@<ip>:/workspace/tune/
```
This uploads: `train.jsonl`, `val.jsonl`, `images/`, `train_qwen36.py`, `export_gguf.py`,
`eval_fields.py`, `verify_env.py`, `stats.json`.

## Phase 3 — Verify environment (before touching the dataset)

```bash
cd /workspace/tune/data_before_tune
python3 verify_env.py
```
Must show ✓ on every line (GPU compute capability, VRAM ≥74GB, Unsloth/Triton load,
tokenizer download). If anything shows ✗, fix it before proceeding — do not skip ahead.

## Phase 4 — Baseline measurement (optional re-check, already have this number from last run)

```bash
python3 eval_fields.py --base --limit 20
```
Expected: ~0% JSON valid (this is normal — the base model has never seen this task).
Skip this step if you want to save ~10-15 min and just trust last run's baseline (0/20,
0/170) — nothing about the base model changed.

## Phase 5 — Short test run (always do this — cheap insurance)

```bash
TEST_STEPS=5 python3 train_qwen36.py 2>&1 | tee test_run.log
```
Takes a few minutes. Confirms: no OOM, no import errors, LoRA attaches cleanly, a
checkpoint saves. **Wait for the shell prompt to return before typing the next command**
(lesson from 2026-07-21: typing ahead while a script is still finishing its post-training
demo step queues the command instead of running it, and looks confusing).

If this fails for any reason, STOP — do not proceed to full training. Something
regressed since 2026-07-21 (unlikely, but check).

## Phase 6 — Full training

```bash
python3 train_qwen36.py 2>&1 | tee full_train.log
```
Expected duration: ~50-60 minutes (measured last run: 226 examples ÷ 8 grad-accum × 3
epochs ≈ 85 steps × 37.4s/step). Expected cost at $1.056/hr: **under $1.10**.

Watch for: `✓ เซฟ LoRA adapter ที่ outputs_qwen36/lora` — this is the point where the
valuable output first exists on disk. Loss should fall from ~2.0 toward ~0.1-0.2 by the
end (matches last run: 2.02 → 0.79 → 0.49 → 0.29 → 0.17 → 0.14).

**Do not open a second terminal and run `pip install` for anything else while this is
running** (the exact mistake from 2026-07-21 that broke `transformers`/`torch` mid-run
by sharing one Python environment across two concurrent tasks).

## Phase 7 — Post-training measurement

```bash
python3 eval_fields.py --adapter outputs_qwen36/lora --limit 20
```
Compare against baseline. Last run's numbers to beat: JSON valid 90%, view match 60%,
element recall 9.4%. Element recall is the known weak spot — if this round doesn't
improve it, that's expected (same dataset), not a new bug.

## Phase 8 — Export: merge + GGUF + quantize + upload, all in one script

```bash
export HF_TOKEN=hf_YOUR_TOKEN_FROM_PHASE_0
export HF_REPO=yourusername/qwen36-thai-rc
python3 export_gguf.py 2>&1 | tee export.log
```

This single script (see file for full comments):
1. Loads base model + your LoRA adapter
2. Calls `model.merge_and_unload()` explicitly, then runs a cheap sanity generation on a
   val example to confirm the merge actually applied the tuning (catches a known
   silent-failure mode where calling `save_pretrained_gguf` directly on an unmerged
   adapter can silently export the untuned base model instead — found while reviewing
   this plan, fixed before ever renting)
3. Calls `model.save_pretrained_gguf(..., quantization_method="q4_k_m")` — GGUF convert +
   quantize in one Unsloth call (no manual `llama-quantize` CLI, no
   q8_0-then-can't-requantize trap from last time)
4. Checks the resulting GGUF file size is in the expected ~20-24GB range (catches a
   truncated/crashed write — e.g. disk filled mid-export — that would otherwise still
   leave a file on disk looking "done")
5. Downloads the official `mmproj-F16.gguf` from `unsloth/Qwen3.6-35B-A3B-GGUF` (899MB,
   unchanged by our LoRA — see the "what changed" section above for why this is valid)
6. Uploads the LLM GGUF (~22GB) + mmproj (0.9GB) + LoRA adapter backup (7.5GB) to your
   HuggingFace repo
7. **Verifies the upload via the HF API** (checks the files actually exist remotely) and
   only then prints a success banner

Expect this to take 20-40 minutes total (export + upload, depends on your instance's
upload bandwidth). Do not interrupt it mid-run.

## Phase 9 — ⚠️ HARD STOP — verify before you even think about destroying the instance

Do NOT trust `export_gguf.py`'s own printed success message alone. Open a browser (not
the terminal) and check:
```
https://huggingface.co/yourusername/qwen36-thai-rc
```
Confirm you can see and the file sizes look right:
- A `.gguf` file around 22GB (the fine-tuned LLM)
- `mmproj-F16.gguf` around 0.9GB
- `lora-adapter/` folder

**Only after seeing this in the browser**, download the two files you need to your own PC.
**Storage location: `D:\00mk\ai-models\qwen36-thai-rc\`** (already created, sits outside
every git repo on purpose — the `Training` repo has no `.gitignore` at all, so a 22GB
file dropped inside a repo folder risks accidentally being `git add`-ed and bogging down
git locally, even though the push itself would fail on GitHub's file-size limit anyway):
```bash
# From your PC:
cd "D:\00mk\ai-models\qwen36-thai-rc"
curl -L -H "Authorization: Bearer hf_YOUR_TOKEN" \
  -o qwen36-thai-rc-Q4_K_M.gguf \
  "https://huggingface.co/yourusername/qwen36-thai-rc/resolve/main/<exact-filename>.gguf"
curl -L -H "Authorization: Bearer hf_YOUR_TOKEN" \
  -o mmproj-F16.gguf \
  "https://huggingface.co/yourusername/qwen36-thai-rc/resolve/main/mmproj-F16.gguf"
```
(You likely already have `mmproj-F16.gguf` from Phase 0.3's dry run — move that copy
into this same folder instead of redownloading, it's the identical file.)

Confirm both files exist in `D:\00mk\ai-models\qwen36-thai-rc\` and match the expected
sizes **before** going to Vast.ai's dashboard.

## Phase 10 — Local run (this is "done" — no more GPU rental from here)

```bash
cd "D:\00mk\ai-models\qwen36-thai-rc"
llama-cli --model qwen36-thai-rc-Q4_K_M.gguf --mmproj mmproj-F16.gguf \
  --image "path/to/a/real/drawing.png" -p "<the exact instruction prompt from build_dataset.js's PROMPT_SHORT>"
```
Confirm it produces a JSON response, ideally on a drawing page NOT in the training set.
This is the real "is it ready to use" test — not just "did the file get created."

## Phase 11 — Only now: destroy the rented instance

Everything that matters is confirmed on HuggingFace (Phase 9, browser-verified) AND
running locally (Phase 10). Go to the Vast.ai dashboard and destroy the instance.

---

## Cost estimate for this whole round

| Item | Estimate |
|---|---|
| GPU rental (env verify + test + train + export/upload) | ~2-2.5 hours × $1.056/hr ≈ **$2-3** |
| HuggingFace | **$0** (free tier, well under 100GB) |
| Total | **~$2-3**, down from the ~$19 spent last round (most of which was debugging time now already fixed) |

## What "ready to use" honestly means here

Per `rule_of_tune.md`'s Mark of Shame rule #1: don't call something "ready" if it can't
do its core job. To be precise about what finishing this workflow actually gets you:

- ✅ **Technically functional**: runs entirely on your own PC, no GPU rental, reads an
  image, produces JSON. This is the part that was missing last time (mmproj).
- ⚠️ **Not yet highly accurate**: last run's element recall was only 9.4% — meaning it
  still misses most individual rebar/beam/column entries even though it gets the JSON
  *shape* right 90% of the time. That's a data/training-round problem (more reviewed
  examples, more epochs, or dataset changes), not something this export workflow fixes.
  Don't expect production-grade extraction accuracy from this round — expect a working,
  correctly-shaped, locally-runnable model that's measurably better than the untuned
  base, with accuracy as the next thing to improve.
