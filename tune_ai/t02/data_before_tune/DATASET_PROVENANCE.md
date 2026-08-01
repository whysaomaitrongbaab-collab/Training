# t02 dataset provenance — byte-identical copy of t01, deliberately NOT rebuilt

**Written 2026-07-28, when t02 was set up.**

t02 exists to answer one question: **is Qwen3-VL better or worse than Qwen3.6-35B-A3B at this task?**
That is an A/B test, and an A/B test is only worth running if exactly one thing differs between the
two arms. Here the one thing is **the model**. Everything else — every training example, every image,
every byte of the instruction prompt, the train/val split — is held identical.

## What was done

The dataset was **copied byte-for-byte from `t01/data_before_tune/`**. It was *not* regenerated with
`build_dataset.js`.

```
t01/data_before_tune/train.jsonl   ->  t02/data_before_tune/train.jsonl    (315 examples)
t01/data_before_tune/val.jsonl     ->  t02/data_before_tune/val.jsonl      ( 88 examples)
t01/data_before_tune/stats.json    ->  t02/data_before_tune/stats.json
t01/data_before_tune/images/       ->  t02/data_before_tune/images/        (398 files)
t01/data_before_tune/build_dataset.js -> t02/data_before_tune/build_dataset.js  (reference only — do not run, see below)
```

## Verification (run 2026-07-28, all passed)

SHA-256 per file, plus a rollup hash over all 398 images hashed in sorted filename order:

| item | result | sha256 (first 16) |
|---|---|---|
| `train.jsonl` | **MATCH** | `6de30e6a349dcf56` |
| `val.jsonl` | **MATCH** | `9fa935d632bc6a03` |
| `stats.json` | **MATCH** | `8ad654e65ea06018` |
| `build_dataset.js` | **MATCH** | `99060affdb1d6368` |
| `images/` filename list (398) | **MATCH** | — |
| `images/` content rollup | **MATCH** | `a16d7cbd2d8bde20429e3736c125d073` |

Also checked: **every image path referenced by `train.jsonl`/`val.jsonl` resolves to a real file
inside `t02/data_before_tune/images/` — 0 missing.**

## ⚠️ Do NOT re-run `build_dataset.js` for t02

`build_dataset.js` reads its source JSON from:

```
D:\00mk\steel project\training\Training\json_แก้ไขแล้ว
```

**That source has changed since t01's dataset was built**, so re-running the builder today would
silently produce a *different* dataset and destroy the comparison.

`stats.json` records the build time as **`2026-07-24T11:18:17.050Z`**. Files in the source tree
modified *after* that timestamp:

| modified | file (in `05บ้าน_เล็ก_2ชั้น_03/`) |
|---|---|
| 2026-07-24 16:24 | `..._หน้า30_spread_footing_plan.json` |
| 2026-07-24 16:24 | `..._หน้า31_pile_footing_plan.json` |
| 2026-07-24 16:49 | `..._หน้า36_beam_sections.json` |
| 2026-07-24 18:06 | `..._หน้า32_beam_plan_floor1.json` |
| 2026-07-24 18:07 | `..._หน้า00_gridline.json` |
| 2026-07-24 18:18 | `..._หน้า34_tie_beam_plan.json` |
| 2026-07-25 01:49 | `..._หน้า33_beam_plan_floor2.json` |

Seven files, including the **grid master** — which per the schema spec is the single most
error-prone and highest-value training signal in the set. A rebuild would change those labels,
and any accuracy difference measured afterwards could no longer be attributed to the model.

The copy is kept here as reference so the build parameters are visible without going back to t01,
and so a *future* round (t03+) that legitimately wants fresher labels can see exactly what it is
changing.

## The dataset being used (from the inherited `stats.json`)

| | |
|---|---|
| built at | 2026-07-24T11:18:17.050Z |
| prompt mode | `short` (the instruction text in `ai_output_.../_prompt_short.txt`, ~1,022 tokens) |
| val split | `03บ้าน_เล็ก_2ชั้น_01` held out whole |
| train | 315 examples / 324 images — output tokens: median 1,248, p95 2,319, max 2,818 |
| val | 88 examples / 91 images — output tokens: median 1,017, p95 2,385, max 2,641 |
| houses | 01 (62), 02 (71), 03 (88, val), 04 (93), 05 (89) |
| flags | `STRIP_WORKLOG: true`, `DROP_CROSS_PAGE_SPECS: true`, `COPY_IMAGES: true` |

**Note on the 5 grid-master examples**: one per house, and they bundle 2–4 images each rather than
one. In t01 this was the thing that forced `MAX_LENGTH` up from 9,216 to 24,576 — at 5,120 visual
tokens per image, a 4-image grid-master example runs to ~22,000 tokens and gets its JSON label
truncated away by the trainer otherwise. **The same arithmetic has to be redone for whatever
`max_pixels` t02's presets use** — it is not inherited automatically, because the token count
depends on the image resolution the processor is configured for. See the t02 workflow doc.

## Rule compliance

Per `rule_of_tune.md`, the contents of this folder are real project data. Nothing here was
generated, guessed, or edited — it is a verified copy, and the verification above is the record.
