# t01 workflow — Qwen3.6-35B-A3B → Local GGUF, No Ongoing GPU Rental

> ## 🔵 นี่คือเอกสารของ **รอบ t01** — จบแล้ว (Phase 0-10 ✅ / Phase 11 ยังไม่ทำ)
>
> | | |
> |---|---|
> | รอบ | **t01** |
> | โมเดล | `unsloth/Qwen3.6-35B-A3B` (MoE, active 3B) |
> | โฟลเดอร์ข้อมูล | `tune_ai/t01/data_before_tune/` |
> | สถานะ | เทรน+export+backup+รันโลคอลเสร็จแล้ว — ผล: JSON valid 90%, element recall 28.2% |
> | เครื่องที่เช่า | instance `m:130161` (RTX PRO 6000 WS 95.6GB, ฮ่องกง, $0.111/hr) |
>
> **⚠️ ถ้ากำลังจะรันรอบใหม่ อย่าใช้ไฟล์นี้** — ไปที่ [`tune_ai/t02/t02_workflow.md`](../t02/t02_workflow.md)
> การหยิบสถานะ ✅ ของรอบเก่ามาใช้กับรอบใหม่ คือรูปแบบความผิดพลาดที่ทำให้เกิด DAY OF SHAME
> (เชื่อว่างานเสร็จแล้วทั้งที่ยังไม่ได้ backup) เครื่องหมาย ✅ ทุกตัวในไฟล์นี้เป็นของ **t01 เท่านั้น**
>
> *เปลี่ยนชื่อ 2026-07-28: เดิมคือ `RETUNE_WORKFLOW.md` และเคยอยู่ใน `data_before_tune/`
> ย้ายขึ้นมาไว้ระดับโฟลเดอร์รอบ และตั้งชื่อให้บอกรอบชัดเจน เพื่อให้ t01/t02 ไม่ปนกัน
> เอกสารเก่าที่อ้างถึง `RETUNE_WORKFLOW.md` (diary 07-24, 07-25) หมายถึงไฟล์นี้*

Written 2026-07-21, after the previous attempt lost all output files (LoRA adapter, merged
model, GGUF) because the rented instance was destroyed before backup. Full incident:
`No_touch_box/docs/rule_of_tune.md`'s Mark of Shame section (the standalone
`mark_of_shame.md` narrative doc was deleted 2026-07-24 by the user).

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

### 0.1 — HuggingFace account + token ✅ DONE (2026-07-24)
Token tested and confirmed working: `curl .../api/whoami-v2` returned user `Sicilian44`
(Chaichana Juisiri), token name `constistant-tune_t1`, scope `fineGrained` with
`repo.write` — sufficient for the upload in Phase 9.

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

### 0.2 — Vast.ai account ✅ DONE (2026-07-24)
1. Balance confirmed via dashboard screenshot: **$12.29 credit** — covers the $5-10 budget
   estimate (Phase 9), though with less margin than the low end if the run overruns.
2. SSH key: **already done, reusable forever** — you generated `~/.ssh/id_ed25519` on
   2026-07-21 and added the public key to vast.ai/manage-keys/. Nothing to redo here.
3. **⚠️ CATCH — fix before renting:** the search page's default **Container Size (disk)
   is 150GB**, not the **≥300GB** this workflow requires (§0.5 below). If you click Rent
   without changing this slider first, you will hit the exact 100%-full-disk failure from
   the 2026-07-21 run again. Move the "Disk Space" slider to 300 before renting anything.
   Also note: the listed GPUs need filtering to ≥80GB VRAM (RTX PRO 6000 96GB qualifies,
   e.g. m:67820 $0.975/hr or m:137288 $1.431/hr in the Asia region shown; RTX 5090 32GB /
   RTX 5060 Ti 16GB do NOT qualify — don't rent those for this job).

### 0.3 — Local dry run: prove your PC can run the FINAL result, before spending anything
✅ **DONE (2026-07-24) — PASSED.**
Environment confirmed: RTX 5060 Laptop (8GB VRAM, driver 592.01, compute capability 12.0
Blackwell), 31.4GB system RAM. `mmproj-F16.gguf` + `test-model.gguf` (IQ2_XXS) + llama.cpp
`win-cuda-13.3-x64` prebuilt release downloaded to `D:\00mk\ai-models\qwen36-thai-rc\`.
Ran `llama-cli --model test-model.gguf --mmproj mmproj-F16.gguf --image <real house01 หน้า19
drawing> -p "Describe this drawing."` — produced a coherent, on-topic description: correctly
read the Thai title block text ("แผนลุนฐานรากแผ่ และฐานรากเสาเข็ม" / spread + pile-cap
foundation plan, scale 1:100), identified the grid (1/2/3 x A/B/C/D), footing labels (F1,C1
etc.), and was mid-way through reading dimension figures when generation ended (this is the
UNTUNED base model at IQ2_XXS — output quality itself doesn't matter here, only that the
pipeline works end to end). Confirms: llama.cpp runs on this PC, mmproj loads and reads
images correctly, VRAM+RAM can host this architecture (partial GPU offload, ~25 t/s prompt /
~4.4 t/s generation on IQ2_XXS). `test-model.gguf` (10GB) deleted after the test per step 5
below; `mmproj-F16.gguf` kept for reuse in Phase 6-9.
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

### 0.4 — Re-check the scripts one more time ✅ DONE (2026-07-24) — found a real problem, RESOLVED (MAX_LENGTH→24576, verified in file on 2026-07-25)
Actually re-read all three scripts line by line (not just skimmed) against the CURRENT
`stats.json` (rebuilt today after adding house 05 — 315 train / 88 val examples now).

- `train_qwen36.py` — LORA_R=32, dropout=0, bf16, image-processor patch, TEST_STEPS support:
  all still consistent with the 2026-07-21 fixes. **BUT** found a sizing bug that predates
  this session (not introduced by adding house 05, just never caught before):
  **`MAX_LENGTH=9216`'s comment only accounts for ONE image (1,022 instruction + 5,120
  image + ≤2,748 output + buffer). It never accounted for the 5 grid-master examples
  (one per house), which bundle 2-4 images each.** Real numbers, computed just now:

  | Example | Images | Est. total tokens | vs MAX_LENGTH 9216 |
  |---|---|---|---|
  | house01 gridmaster | 3 | ~16,981 | ⚠️ 1.8× over |
  | house02 gridmaster | 4 | ~21,896 | ⚠️ 2.4× over |
  | house03 gridmaster (in **val** split) | 4 | ~22,067 | ⚠️ 2.4× over |
  | house04 gridmaster | 2 | ~11,883 | ⚠️ 1.3× over |
  | house05 gridmaster | 4 | ~21,944 | ⚠️ 2.4× over |

  (Each image gets downscaled to ≤5,120 visual tokens by `MAX_PIXELS`; real drawing scans
  here are 3309×2339 or larger, so they land at or near that cap — this isn't a worst-case
  estimate, it's the expected case.) All 5 grid-master examples — the ONLY training signal
  for whole-house dummy-grid extraction, explicitly the most error-prone part of this task
  per the dataset's own prompt — will get truncated by the trainer if this isn't fixed
  first. Truncation on a chat-formatted example cuts from the end, i.e. it would corrupt
  the JSON label those examples are trying to teach, not just crop unused padding.
  **RESOLVED 2026-07-24 (user's decision):** raise `MAX_LENGTH` to cover the worst case
  rather than downscale images or drop grid-master data. Changed `train_qwen36.py`:
  `MAX_LENGTH = 9216` → **`24576`** (comfortably above the ~22,067-token worst case, with
  margin for the char→token estimate's imprecision). Accepted trade-off: this raises OOM
  risk specifically on the 5 grid-master forward passes (last run had only ~100MiB to
  spare at 95GB with the old 9216 cap) — if OOM hits, the fallback is to cut `LORA_R`
  further or cap `MAX_PIXELS` for grid-master images specifically, NOT to lower
  `MAX_LENGTH` back down (that would re-truncate the grid-master labels).
- `export_gguf.py` — re-read in full. Merge-then-sanity-check-then-quantize-then-verify-
  upload sequence is intact, GGUF size guard (15-30GB) matches this doc's Phase 0.5 numbers.
  One minor fragility (not blocking): line ~78 opens `val.jsonl` as a bare relative path
  instead of `Path(__file__).parent / "val.jsonl"` like every other script here does — fine
  as long as you `cd` into `data_before_tune/` before running it (Phase 6 already says to).
- `eval_fields.py` — re-read in full, unchanged, consistent with `train_qwen36.py`'s presets
  and image-processor handling. No issues found.

### 0.5 — Instance sizing checklist (decide before clicking Rent) ✅ DONE (2026-07-24)
Matched against the real Vast.ai search page (screenshot, Asia region filter, "PyTorch
(Vast)" template, credit $12.29):

| Setting | Value | Why |
|---|---|---|
| GPU | RTX PRO 6000 96GB (Blackwell) or A100/H100 80GB | Confirmed working 2026-07-21. VRAM ≥80GB required for bf16 LoRA (~74GB). **Pick from the real listing:** `m:67820`, $0.975/hr, 99.76% reliability, Japan — best cost+reliability combo of the qualifying options shown. (`m:137288` $1.431/hr 97.9% is a fallback if 67820 is gone; do NOT pick the RTX 5090 32GB or RTX 5060 Ti 16GB rows shown in the same list — both under the 80GB floor.) |
| Disk | **≥300GB** (raised twice now — 150GB last time, then 200GB, now corrected after actually doing the math) | Last run hit 100%-full disk multiple times even after cleanup. Realistic peak this round, all potentially coexisting at once: base model HF cache (~70GB, already on disk from training) + merged 16-bit intermediate Unsloth writes internally (~66GB) + GGUF f16 intermediate before quantizing (~66GB) + final Q4_K_M (~22GB) ≈ **~225GB just for those**, before any breathing room. 200GB would likely repeat the disk-full saga; 300GB gives actual margin. **The search page's Container Size slider defaults to 150GB — you must drag it to 300 before renting**, confirmed still true on today's screenshot. If you see disk filling up mid-`export_gguf.py` anyway: the safe thing to delete is the HF hub cache (`~/.cache/huggingface`, already loaded into GPU memory by then) — never delete anything under `outputs_qwen36/`. |
| Template | Plain PyTorch + CUDA | NOT "Unsloth Studio" — we run our own scripts via SSH, not their UI. Today's screenshot shows "PyTorch (Vast)" selected, which is the right family — just confirm it's the plain image, not a Studio/notebook variant, when you actually click Rent. |
| On-start script | Paste `onstart.sh` contents into the instance creation form | Installs Unsloth/Triton/Blackwell env vars automatically on boot. |
| Reliability | ≥95% | `m:67820` (99.76%) and `m:137288` (97.9%) both clear this. |
| Budget | $12.29 credit confirmed (2026-07-24) vs. $5-10 estimated cost | Enough, but with less margin than the low end of the estimate if the run overruns — don't leave the instance running idle after Phase 9 finishes. |

---

## Phase 1 — Rent + connect ✅ DONE (2026-07-24)
Instance `m:130161` (RTX PRO 6000 WS, 95.6GB VRAM, Hong Kong, $0.111/hr — cheaper than the
0.5 pick since Vast.ai's market moved). Disk confirmed **300GB** on the instance itself
(`df -h /` → `300G`), so the 0.2/0.5 disk-slider warning was applied correctly.
Direct SSH works: `ssh -p 30055 root@94.190.219.147` (proxy route via ssh4.vast.ai also
available as fallback, not needed so far).

```bash
# From your PC:
ssh -p <port> root@<ip>          # port/ip from the Vast.ai instance's "Connect" button
```
You land in a `tmux` session automatically (Vast.ai default) **only on interactive login**
— a non-interactive `ssh ... "command"` (what's being used to drive this run) does NOT
go through tmux by itself. Noted as a real gap for Phase 6 below (the long one).

## Phase 2 — Upload dataset + scripts ✅ DONE (2026-07-24)
Uploaded and verified on the remote: `train.jsonl` (315 lines), `val.jsonl` (88 lines),
`images/` (398 files), plus all scripts. Sizes match what was built locally after adding
house 05.

```bash
# From your PC (a second terminal, don't reuse the SSH session for this):
scp -P <port> -r "d:\00mk\steel project\training\Training\tune_ai\t01\data_before_tune" root@<ip>:/workspace/tune/
```
This uploads: `train.jsonl`, `val.jsonl`, `images/`, `train_qwen36.py`, `export_gguf.py`,
`eval_fields.py`, `verify_env.py`, `stats.json`.

## Phase 3 — Verify environment (before touching the dataset) ✅ DONE (2026-07-24) — ALL GREEN
`onstart.sh` had already installed Unsloth 2026.7.5 / Triton 3.6.0 / bitsandbytes 0.49.2 on
boot. `verify_env.py` output: torch 2.11.0+cu130, CUDA available, compute capability (12,0),
VRAM 95.0GB, FastVisionModel imports, tokenizer downloads from `unsloth/Qwen3.6-35B-A3B` —
every line ✓.

```bash
cd /workspace/tune/data_before_tune
python3 verify_env.py
```
Must show ✓ on every line (GPU compute capability, VRAM ≥74GB, Unsloth/Triton load,
tokenizer download). If anything shows ✗, fix it before proceeding — do not skip ahead.

## Phase 4 — Baseline measurement ⏭️ SKIPPED (2026-07-24, deliberately)
Per this doc's own note below: nothing about the base model changed since 2026-07-21's
measured baseline (0/20 JSON valid, 0/170 elements) — trusting that number instead of
re-spending ~10-15 min re-measuring it.

```bash
python3 eval_fields.py --base --limit 20
```
Expected: ~0% JSON valid (this is normal — the base model has never seen this task).
Skip this step if you want to save ~10-15 min and just trust last run's baseline (0/20,
0/170) — nothing about the base model changed.

## Phase 5 — Short test run (always do this — cheap insurance) ✅ DONE (2026-07-24) — PASSED
Trainable params 1,890,448,640 / 36,997,630,576 (5.11%, LORA_R=32 as expected). Ran all 5
steps clean: **no OOM**, no import errors, loss 1.801→eval_loss 1.213 (expected range for
step 0), `✓ เซฟ LoRA adapter ที่ outputs_qwen36/lora` printed — checkpoint saved.
⚠️ Caveat worth naming honestly: with `TEST_STEPS=5` × grad_accum 8 = 40 samples seen out
of 315, this may or may not have included one of the 4 in-train grid-master examples (the
ones the 0.4 `MAX_LENGTH` fix specifically targets) — no way to confirm from this log
alone. Not blocking (nothing failed), but the *real* test of that fix is Phase 6's full
3-epoch run, which touches every example including all grid-masters. Watching for OOM
specifically during those steps.

```bash
TEST_STEPS=5 python3 train_qwen36.py 2>&1 | tee test_run.log
```
Takes a few minutes. Confirms: no OOM, no import errors, LoRA attaches cleanly, a
checkpoint saves. **Wait for the shell prompt to return before typing the next command**
(lesson from 2026-07-21: typing ahead while a script is still finishing its post-training
demo step queues the command instead of running it, and looks confusing).

If this fails for any reason, STOP — do not proceed to full training. Something
regressed since 2026-07-21 (unlikely, but check).

## Phase 6 — Full training ✅ DONE (2026-07-24)
Completed clean: 120 steps (315 examples ÷ 8 grad-accum × 3 epochs), 29:23 train_runtime.
Loss 1.80→0.22→0.12→0.08 (noisy but trending down); eval_loss per epoch 0.2668→0.1983→0.1936
(steady improvement each epoch, better trajectory than the 2026-07-21 run at the same
points). `✓ เซฟ LoRA adapter ที่ outputs_qwen36/lora` confirmed on disk (7.56GB
`adapter_model.safetensors`). No OOM despite the higher `MAX_LENGTH=24576` — the 0.4 fix
held up under the real full run touching every grid-master example.

**⚠️ Two new process-hygiene bugs found and worked around this round (both about the
Python process not exiting on its own, not about training correctness):**
1. **`train_qwen36.py` hangs in its own post-training epilogue** (the "generate 3 val
   samples to show a quick result" loop after the LoRA save) — confirmed on BOTH the
   Phase 5 short test and this Phase 6 full run: the log stops cleanly right after
   `✓ เซฟ LoRA adapter...`, but the process stays alive holding ~83GB VRAM indefinitely
   (checked minutes later, no further log lines, no crash). The adapter itself is fully
   and correctly saved by that point — this hang is isolated to the epilogue's demo
   generation, not the actual training or save. **Workaround used:** once
   `✓ เซฟ LoRA adapter` appears in the log, `kill -9` the process tree — don't wait for it
   to exit on its own, and don't treat a hang here as a training failure.
   **Not yet root-caused** (candidate suspects: `FastVisionModel.for_inference(model)`
   mode switch, or `max_new_tokens=3000` unbatched generation just being very slow rather
   than truly hung — not distinguished yet since killing it was faster/safer than waiting
   to find out). Future round: consider removing/guarding that epilogue block entirely
   since Phase 7's `eval_fields.py` is the real measurement anyway.
2. **This is why the harness's own "background command completed" signal can't be fully
   trusted for this script** — Phase 5's SSH command was still reported as running (not
   exited) many minutes after the training itself had genuinely finished, because the
   underlying process was stuck in bug #1 above holding the SSH channel open. Confirmed by
   checking `ps aux` / `nvidia-smi` directly on the remote rather than trusting silence.

## Phase 6 — Full training (original doc text)

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

## Phase 7 — Post-training measurement ✅ DONE (2026-07-24) — 🔴 CRITICAL BUG FOUND AND FIXED, then re-run with real improved numbers
First run (`--limit 20`) showed **0/3 JSON valid** before being stopped for investigation —
a severe regression from the 2026-07-21 run's 90%. Root-caused by pulling the raw
(untruncated) model output directly: the model was emitting a full chain-of-thought
preamble ("Here's a thinking process: 1. Analyze... 2. Scan...") before ever reaching the
JSON, burning most of the `max_new_tokens=3000` budget on reasoning text instead of the
answer — this is also why Phase 6's post-training demo loop and this eval both appeared to
"hang": they weren't stuck, just extremely slow due to unbounded reasoning generation.

**Root cause (confirmed empirically, not guessed):** `apply_chat_template(msgs,
add_generation_prompt=True)` — used in `eval_fields.py`, `export_gguf.py`'s sanity check,
and `train_qwen36.py`'s own post-training demo loop — omits `enable_thinking=False`. The
chat template's default behavior (when this flag isn't set) inserts a bare, unclosed
`<think>\n` tag at the generation position, and this reasoning-native base model responds
by writing genuine chain-of-thought there. **Training itself was never affected** — the
data collator calls the same template with `add_generation_prompt=False` (full
conversation already includes the assistant's JSON, so no generation-prompt tag is ever
inserted) — this is purely an inference-time prompt mismatch, confirmed by testing
`enable_thinking=False` on the actual trained adapter: the model immediately produced pure
JSON with zero reasoning preamble, no retraining required.

**Fixed in all three files** (`eval_fields.py`, `train_qwen36.py`, `export_gguf.py`) by
adding `enable_thinking=False` to every `apply_chat_template(..., add_generation_prompt=True, ...)`
call.

✅ **Re-run completed (2026-07-24) — real numbers, `--limit 20`:**

| Metric | 2026-07-21 | 2026-07-24 (this round) |
|---|---|---|
| JSON valid | 90% (18/20) | **90% (18/20)** — same |
| View exact match | 60% | **70% (14/20)** ⬆️ |
| Element recall | 9.4% (16/170) | **28.2% (48/170)** ⬆️ — 3× better |
| element_id exact-match | — | 100% (48/48) |
| element_type exact-match | — | 87.5% (42/48) |
| count exact-match | — | 100% (12/12) |
| Over-predicted (extra) elements | 61 | 78 |

Adding house 05 + the extra training data (315 vs 226 examples) plus the `MAX_LENGTH` fix
appears to have genuinely helped element recall, not just fixed the inference bug (JSON
validity is unchanged at 90%, so the recall/view-match gains are real training
improvements, not an artifact of the `enable_thinking` fix). Remaining weak spot: the model
over-predicts (78 extra elements not in gold) — a real thing to address in a future round,
not blocking this one.

**Open question, not yet resolved:** why didn't this affect the 2026-07-21 run (measured
90% JSON valid with the same `eval_fields.py` logic, unpatched)? Leading theory: the
upstream `unsloth/Qwen3.6-35B-A3B` repo's chat template may have been updated between
2026-07-21 and 2026-07-24 to add hybrid-reasoning defaults — plausible for an actively
developed model repo, not yet independently confirmed. Not blocking (the fix works
regardless of why the default changed), but worth knowing if this recurs on a future
re-download.

## Phase 7 — Post-training measurement (original doc text)

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

**⚠️ Bug found and fixed (2026-07-24) — took 4 attempts to get right, real lesson in
sanity-check design:**
1. First run: `max_new_tokens=500` — truncated mid-string, false "SANITY CHECK FAILED".
   Raised to 3000 (matching `eval_fields.py`).
2. Second run: STILL failed — this exact sanity-check example (`val.jsonl` line 1, a
   large index+material-list+signature-block page) generated 10,497 chars / hit the full
   3000-token cap and was still mid-string. Raised to 4096.
3. Third run: STILL failed at 4096 tokens (13,991 chars, still incomplete) — this specific
   page turns out to be a genuine over-generation case (the model enumerates far more
   signature/approval entries than really exist — the same over-prediction tendency Phase
   7 already measured as 78 extra elements across 20 examples). No fixed token budget was
   going to "solve" this — it's not a truncation bug, it's real (if imperfect) model
   behavior on an unlucky fixed example.
4. **Root fix:** the check itself was the wrong shape. Requiring full `json.loads()` on an
   arbitrarily long generation is fragile against two things that are both expected and
   harmless: (a) this round's real over-generation tendency on complex pages, and (b) tiny
   bf16 rounding differences between `merge_and_unload()`'s merged weights and the
   adapter-applied-at-runtime math `eval_fields.py` uses, which can make a long greedy
   decode diverge after enough tokens. Neither means the merge silently failed — that
   specific failure mode (confirmed via the 2026-07-21 baseline and the Phase 0.3 dry run)
   looks like a reasoning preamble or generic non-schema text, not real schema JSON that
   just runs long. **Rewrote the check** to generate only 1200 tokens and verify the
   output *starts* with real schema JSON (`{` plus a `"png"`/`"views"`/`"pattern"`/
   `"doc_page"` marker in the first 400 chars) rather than requiring a full valid parse.
   Also switched the fixed test example from `val.jsonl` line 1 (the problematic one) to
   line 3 (a compact page, already confirmed valid+fast in Phase 7's real run). Passed
   after this fix.

**Lesson for next time:** a "does the output fully parse" check is the wrong tool when the
model being tested is known to sometimes run long — check for the *presence of expected
tuned behavior* near the start instead of *absence of any imperfection* over the whole
output. The script's fail-safe design (stop before expensive quantization on any doubt)
worked exactly as intended throughout — it just needed a better-shaped check, not removal.

**Second bug, after the sanity check finally passed:** `model.save_pretrained_gguf()`
itself failed — but not on the text/LLM conversion (that part succeeded: "Writing model
shards: 100%"). Unsloth auto-detects this model as a VLM (`hasattr(model.config,
"vision_config")` is true) and, as part of the SAME call, automatically also attempts to
export a vision-projector GGUF — which fails hard on this architecture ("no tensors were
written... check safetensors filenames are discoverable") and takes the whole export down
with it, including the already-successful text conversion. This is exactly the same
architecture-support gap that caused the mmproj problem on 2026-07-21 — except this round
we never asked Unsloth to attempt it at all (the whole design here is reusing the official
pre-built `mmproj-F16.gguf` instead, see the "What changed" section at the top of this
doc), yet its auto-detection tries anyway and fatally errors when it can't.
**Fix:** temporarily `del model.config.vision_config` right before
`save_pretrained_gguf()` (restored in a `finally` block) so Unsloth's `is_vlm` check sees
a text-only model for this one call and skips the failing auto-mmproj attempt — the
correct outcome for our design either way, since we bring our own mmproj file afterward.

**Third issue (2026-07-24): disk filled up mid-save** — `No space left on device` during
`model.save_pretrained_gguf()`'s shard-writing step, even though disk was correctly set to
300GB. Cause: this phase got re-run 6+ times while chasing the bugs above, and nothing
cleaned up between attempts — 3 old training checkpoints (`checkpoint-5/40/80`, 11GB each
= 33GB, all superseded by the final `outputs_qwen36/lora/` save), the final checkpoint
(`checkpoint-120`, another 11GB, also redundant with `lora/`), and a stale partial
`outputs_qwen36/gguf/` dir (66GB) from an earlier failed attempt, together with the normal
67GB HF cache, had eaten 265GB of the 300GB before the export's own peak usage (merged
safetensors + GGUF f16 intermediate + quantized output, ~154GB per the 0.5 estimate) could
even start. **Fix:** deleted the 3 redundant checkpoints + stale `gguf/` dir + pip cache
(58GB freed, safe — none of it is the actual save output, which lives in `outputs_qwen36/
lora/` untouched throughout), recovering 133GB→147GB free. **Lesson:** the 300GB estimate
in §0.5 assumed one clean run; it doesn't have headroom for re-running this phase multiple
times without cleanup in between — if debugging requires several attempts, clean
`outputs_qwen36/gguf/` (regenerated fresh each run anyway) and old non-final checkpoints
before each retry, don't just re-run blind.

**Fourth issue — the `del model.config.vision_config` fix itself was wrong.** After
freeing disk space, the re-run still failed with the identical "no tensors were written"
error, but this time llama.cpp's converter had successfully *found and indexed* both
safetensors shards first — so the shards existed, but contained nothing the converter
recognized. Inspecting the saved tensor names directly showed why:
`model.language_model.language_model.language_model.embed_tokens.weight` — **triple-
nested**, not the normal single-level name. Deleting `vision_config` doesn't just change
the GGUF-conversion branch, it also changes how `unsloth_save_pretrained_gguf` unwraps/
saves the model itself, and that unwrap logic doesn't compose cleanly with this
architecture's own nested `language_model.language_model` submodule structure — producing
genuinely corrupt output, not just a skipped step. That's the real reason the error
persisted even after "fixing" it.

**Real fix:** traced into `unsloth_zoo.llama_cpp.convert_to_gguf`'s source directly.
It already has a graceful fallback built in for exactly this case:
```python
if is_vlm and supported_vision_archs is not None:
    if arch not in supported_vision_archs:
        is_vlm = False
        print(f"Unsloth: {arch} is not supported for MMPROJ conversion. Converting as text-only model.")
```
It just never fires here, because `save_to_gguf()` calls `convert_to_gguf()` without ever
passing `supported_vision_archs` (stays `None`), so the architecture-support check that
would flip `is_vlm` to `False` never runs for an architecture nobody's added to that list
yet. Fix: monkey-patch `unsloth.save.convert_to_gguf` (the name as bound inside
`unsloth.save`'s own namespace via its `from ... import`, not `unsloth_zoo.llama_cpp`'s
copy — patching the latter wouldn't affect the already-resolved import) so every call
supplies `supported_vision_archs=set()`, triggering Unsloth's own intended safe path
instead of inventing a workaround. Crucially, this **leaves `model.save_pretrained()`
completely untouched** — it only changes what the GGUF-conversion step does, so the
tensor-naming corruption from the `vision_config` approach can't recur.

**First attempt at the real fix had one more bug:** used `_kwargs.setdefault
("supported_vision_archs", set())`, which silently did nothing — `save_to_gguf()` calls
`convert_to_gguf()` with `supported_vision_archs` always explicitly present as a keyword
(confirmed by reading its source), even when the value is `None`, so `setdefault` never
overrides an already-present key. Fixed by force-assigning
`_kwargs["supported_vision_archs"] = set()` unconditionally instead. **Confirmed working**
— log now shows the intended Unsloth message: `Unsloth: Qwen3_5MoeForConditionalGeneration
is not supported for MMPROJ conversion. Converting as text-only model.` — exactly
Unsloth's own built-in safe path, finally triggered correctly.

**Fifth (last) bug: script looked in the wrong directory for its own output.** GGUF
conversion + quantization actually succeeded — log showed "All GGUF conversions completed
successfully!" — but `export_gguf.py`'s Step 3 glob checked `LOCAL_GGUF_DIR` itself, while
Unsloth's `save_pretrained_gguf()` writes the real final `.gguf` files to
`"{LOCAL_GGUF_DIR}_gguf/"` (an auto-appended `_gguf` suffix on the directory name —
`LOCAL_GGUF_DIR` only ever holds the intermediate merged safetensors). The script
incorrectly reported total failure ("No .gguf file found... may have failed silently")
even though the file was sitting right there, one directory over, complete and correctly
sized (21.2GB). Fixed the glob path in `export_gguf.py`. Rather than re-run the entire
(already-successful, ~15 min) merge+convert+quantize from scratch, wrote a small resume
script (`resume_upload.py`, not part of the permanent pipeline) that picks up from the
already-generated GGUF + already-cached mmproj and does just Step 4 (upload) + Step 5
(verify) — saves real time/cost on a mistake that was purely about a wrong file path, not
a bad artifact.

✅ **Phase 8 DONE (2026-07-24) — VERIFIED on HuggingFace, real banner, real API check:**
```
✅ VERIFIED on HuggingFace: https://huggingface.co/Sicilian44/qwen36-thai-rc
   - Qwen3.6-35B-A3B.Q4_K_M.gguf (21.2 GB)
   - mmproj-F16.gguf (0.9 GB)
   - lora-adapter/ (backup)
```
Five real bugs found and fixed end-to-end this phase (sanity-check token budget × 2,
sanity-check design itself, mmproj auto-export crash × 2 attempts, disk-full from
uncleaned retries, wrong output directory) — none were data/training problems, all were
export-pipeline plumbing. The actual tuned model (confirmed by Phase 7's real numbers) was
never in question.

**⚠️ Per Rule 4 / Mark of Shame: this does NOT mean it's safe to destroy the instance yet.**
Phase 9 (browser-verify) and Phase 10 (local download + local run confirmed) still come
first — the whole point of this backup step existing is so 2026-07-21 can't repeat, and
that only holds if the hard stop below is actually respected, not skipped because the
upload already printed success.

✅ **Phase 9 DONE (2026-07-24)** — browser check hit a 404 at first (expected: the repo is
`private:true`, and HF returns 404 rather than 403 to non-owners to avoid leaking
existence — the browser just wasn't logged into the `Sicilian44` account yet). Confirmed
the repo was genuinely real in the meantime via a direct API call (not just trusting the
export script): `"private":true, "gguf":{"architecture":"qwen35moe","total":34660610688}`
— HF had already parsed the GGUF's own metadata correctly. After logging in, the browser
confirmed the same: 35B params, qwen35moe architecture, Q4_K_M 21.2GB. Real, independent,
human-eyes verification — not just re-trusting the same script's own success message.

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

**Phase 10 bugs found on the local PC (2026-07-24), separate from the rented-instance
bugs above:**
1. **No `--ctx-size` set** — this model's max context is 262,144 tokens; without an
   explicit cap, `llama-cli` reserved KV-cache sized toward that default and drove system
   RAM to ~0.1GB free (out of 31.4GB) — confirmed via `Get-Process`'s `PrivateMemorySize64`
   showing ~35GB committed, more than physical RAM. Fixed: added `--ctx-size 8192` (plenty
   for one page + response).
(For the record: this laptop — a Lenovo Legion — was running in **High Performance** power
mode throughout Phase 10 testing, not Balanced/Power Saver. Noted in case results differ
on a future run under a different power profile.)

2. **Same `enable_thinking` issue as Phase 7, different tool.** Output was an endless
   stream of empty `> ` prompt lines instead of a real answer — `llama-cli` applies the
   GGUF's own baked-in chat template by default, same as the Python side, and without
   disabling reasoning mode the model tries to emit chain-of-thought first. Fixed with
   `--chat-template-kwargs '{"enable_thinking":false}'` (the CLI equivalent of the Python
   `enable_thinking=False` fix from Phase 7) plus `-st`/`--single-turn` to guarantee one
   completion and exit. Confirmed working: real structured JSON output, no preamble.

✅ **Phase 10 DONE (2026-07-25) — confirmed on a real local run, process exited cleanly
(exit code 0), full log captured:**
```
llama-cli.exe --model Qwen3.6-35B-A3B.Q4_K_M.gguf --mmproj mmproj-F16.gguf \
  --image ".../บ้าน_เล็ก_2ชั้น_01_หน้า08.png" \
  -p "$PROMPT_TEXT" --n-gpu-layers 999 --ctx-size 8192 -st \
  --chat-template-kwargs '{"enable_thinking":false}' --temp 0
```
Output was real, correctly-shaped JSON — no reasoning preamble, no `> ` hang. Model
inventoried all 6 views on the page (roof plan + 5 section/detail views), emitted grid
lines, 9 columns with `grid_refs`, 12 beams, 8 slabs with rebar, and roof truss/purlin
specs per section — matching the schema shape used in training. Speed:
`28.4 t/s prompt / 3.2 t/s generation` on CPU+GPU split (`--n-gpu-layers 999` but this
GPU can't hold all 35B params in VRAM, so part runs on CPU — expected for a laptop, not a
bug). Output was still mid-sentence on the last view when it hit the response length used
for this test run — the JSON *structure and content so far* is genuinely good evidence,
but this was not a full unbounded generation to a natural stop, so don't read this as
"proven complete to end of output," just "proven working, correct format, no hang."

## Phase 10 — Local run (this is "done" — no more GPU rental from here)

```bash
cd "D:\00mk\ai-models\qwen36-thai-rc"
llama-cli --model qwen36-thai-rc-Q4_K_M.gguf --mmproj mmproj-F16.gguf \
  --image "path/to/a/real/drawing.png" -p "<the exact instruction prompt from build_dataset.js's PROMPT_SHORT>"
```
Confirm it produces a JSON response, ideally on a drawing page NOT in the training set.
This is the real "is it ready to use" test — not just "did the file get created."

---

## ✅ RE-VERIFICATION PASS (2026-07-25) — all of Phase 0–10 re-checked against real state, not just trusting the doc

Done at the user's request ("ตรวจสอบทุกอย่างตั้งแต่แรก") before authorizing Phase 11. Each
item below was confirmed against actual files/logs on this date, not re-read from the doc:

| Phase | Status | Real evidence re-confirmed 2026-07-25 |
|---|---|---|
| 0.1 HF token | ✅ | (from 2026-07-24 `whoami-v2` — not re-run; token not stored in repo) |
| 0.2 Vast.ai acct | ✅ | (from 2026-07-24 dashboard) |
| 0.3 local dry run | ✅ | mmproj-F16.gguf present on disk (0.9GB) — same file reused through Phase 10 |
| 0.4 script re-check | ✅ | `MAX_LENGTH = 24576` confirmed in `train_qwen36.py` |
| 0.5 instance sizing | ✅ | (from 2026-07-24) |
| 1 rent+connect | ✅ | (from 2026-07-24) |
| 2 upload dataset | ✅ | `train.jsonl` 315 lines / `val.jsonl` 88 lines confirmed locally (matches what was uploaded) |
| 3 verify env | ✅ | (from 2026-07-24, all green) |
| 4 baseline | ⏭️ | deliberately skipped (base model unchanged) |
| 5 short test | ✅ | (from 2026-07-24, passed) |
| 6 full train | ✅ | (from 2026-07-24, LoRA adapter saved 7.56GB) |
| 7 measurement | ✅ | `enable_thinking=False` fix confirmed in all 3 scripts (train=2, eval=2, export=1 occurrences); real numbers recorded (element recall 28.2%) |
| 8 export+upload | ✅ | (from 2026-07-24, HF API + browser verified) |
| 9 browser-verify | ✅ | (from 2026-07-24, human-eyes) |
| 10 local run | ✅ | `Qwen3.6-35B-A3B.Q4_K_M.gguf` present on disk (21.17GB); local `llama-cli` run exited code 0 with real 6-view JSON, no reasoning preamble, no hang |

**Conclusion: Phase 0–10 are all genuinely done and re-verified. Phase 11 is the only
remaining step, and it is deliberately NOT auto-executed — see the hard block below.**

## Phase 11 — ⚠️ HARD BLOCK — destroy the rented instance ONLY on explicit user go-ahead

**⚠️ DO NOT destroy the Vast.ai instance without the user explicitly saying so in that same
message.** This is the exact step that caused the 2026-07-21 DAY OF SHAME (see
`rule_of_tune.md` Mark of Shame): destroy is permanent and unrecoverable, completely
different from stop. The whole Phase 8–10 backup chain exists so this step is safe — and it
is only safe if this block is respected, not skipped because "everything looks done."

The technical preconditions are now met (backup on HuggingFace, browser-verified Phase 9;
files downloaded and running locally, Phase 10). But "preconditions met" ≠ "go ahead and
destroy." The user destroys it themselves from the dashboard, OR explicitly authorizes
Claude to — one clear, unambiguous instruction, this session. Anything short of that, the
instance stays running.

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
