---
name: op03
description: Run op01's full house extraction, then shut the laptop down automatically once — and only once — the house is genuinely finished and safe. Triggers on "op03 <house_name>" or "op3 <house_name>" (Makham's shorthand), e.g. "op03 บ้านเอกมัย". Arms a 90-minute dead-man's-switch shutdown at the very start so the laptop shuts down even if the session runs out of tokens mid-run and nobody is left to finish the gate. Use when Makham wants to start a house and walk away. Source of truth is `rawjson_ยังไม่ได้แก้ไขโดนคน/README.md`'s `op3` section — keep this file in sync with it whenever that section changes.
---

# op03 — op01, then shut the laptop down

Argument: `<house_name>`. `op03` is `op01` with two additions: an unconditional 90-minute dead-man's-switch shutdown armed the moment the run starts, and — when the house is genuinely finished before that — a clean shutdown instead of just stopping.

**Don't use this if anything else on the machine is still running** (a training job, an upload, another agent) — the dead-man's switch arms unconditionally on its own 90-minute clock, with no awareness of what else is running, and will kill that other work too.

## Step 0 — arm the dead-man's switch, before anything else

Before doing anything else — before even reading the spec — run:

```bash
shutdown /s /t 5400 /c "op3 dead-man's switch <house_name> - no finish in 90 min, shutting down"
```

(5400s = 90 minutes.) This is Windows' own scheduler, independent of this session staying alive. If tokens run out mid-run and nobody is left to cancel it, it fires on its own at the 90-minute mark — that's the intended fallback, not a bug. It only ever discards uncommitted progress from the current run; nothing already finished is at risk (see the gate below — nothing counts as finished until it's committed).

90 minutes is a fixed ceiling for one house, not a per-house estimate. Don't leave `op03` unwatched on a house genuinely expected to run long.

## Then: run op01 to completion

Invoke the `op01` skill for `<house_name>` and follow it through all 7 steps. Everything in `op01`'s standing order applies unchanged — same authority, same conflict precedence, same "decide, don't ask."

## The shutdown is the last step, and it is gated

**Never shut down on "the run ended". Shut down only on "the work is finished and safe."** All six must be true, in this order — the first three are just `op01`'s own steps, restated as a checklist:

1. Every file for the house is written and parses as JSON. (`op01` step 4)
2. `python tools/check_format.py 0N<house_name>` → **ALL CHECKS PASS**. (`op01` step 5)
3. The row is added to `No_touch_box/docs/raw_json_data_log.md`. (`op01` step 7)
4. **`git add -A && git commit`** — commit before the machine goes down. A finished house that exists only in an unsaved working tree is one bad wake-up away from gone.
5. The full summary is printed to the user **first** (this is `op01` step 6, already done by this point) — file count, page count, open questions, low-confidence flags. The screen is about to go dark; the report has to already be in the transcript.
6. Cancel the dead-man's switch, then shut down for real:
   ```bash
   shutdown /a
   shutdown /s /t 120 /c "op3 finished <house_name> - shutting down. Run: shutdown /a  to cancel"
   ```
   **120 seconds, never `/t 0`** — that window is the only chance to stop it. Say `shutdown /a` cancels it, in the same message.

**If any of 1-5 fails, do not shut down.** Report what is unfinished and stop. A house that failed `check_format.py` is not finished, and shutting down on it buries the failure until the next session.

**Why the gate is written out like this:** on 2026-07-21 a tuned model (7.5 GB LoRA + 21 GB GGUF) was lost because a machine was shut down while the work was only *apparently* done and nothing had been pushed. See the Mark of Shame in `No_touch_box/docs/rule_of_tune.md`. `op03` exists to automate the ending — not to automate skipping the save.
