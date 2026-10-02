# Graph Report - Training  (2026-09-02)

## Corpus Check
- 5305 files · ~203,151,602 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2855 nodes · 3208 edges · 292 communities (252 shown, 40 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e2ee287c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CV Scan Detection Pipeline
- Harvest Report - Template Match QA
- T01 Batch House Extraction (GPU-Rental)
- T01 House 08-11 Local vs GPU Workflow
- T02 Dataset Provenance & Training Bugs
- T03 GT-vs-AI Overlay Renderer
- T02 House09 Export & Inference Runs
- T01 Dataset Builder (build_dataset.js)
- T02 Dataset Builder (build_dataset.js)
- T03 Comparison PNG Report Builder
- T03 Gridline/Plan Prompt Passes
- T03 Dataset Builder (build_dataset_t03.py)
- T01 Single-House Local Extraction Script
- T01 Multi-House Local Extraction Script
- T03 Common Rules Header
- T03 Pass1 Page Organizer
- T03 Notes/Soil-Boring Passes & Schema Drift
- T03 Pass3/Pass4 Takeoff Prompts
- T02 House09 Overlay Renderer
- T03 Pass0 Classifier (current vs superseded)
- T03 Dataset Pull & Verify Script
- Markdown-to-PDF Book Builder
- T03 Visual Token Capacity Measurement
- Merge Guard Safety Layer
- T03 Training Script (train_t03.py)
- T03 Dataset Sizing Analysis
- Format Validation Gate
- Qwen Export Converter
- T03 ID Ceiling Measurement
- T01 Eval Fields Script
- T02 Eval Fields Script
- T02 GPU Rental Onstart Script
- T03 Beam Grounding Research
- T01 GPU Rental Onstart Script
- T01 Training Script (train_qwen36.py)
- T01 Training Script (train_qwen3vl.py)
- T02 Training Script (train_qwen3vl.py)
- T03 GPU Rental Onstart Script
- T01 GGUF Export Script
- T01 Environment Verification
- T02 GGUF Export Script
- T02 Merge Diagnostic Script
- T02 Environment Verification
- T02 Inference Script (infer_t02.py)
- T02 Grammar-Constrained Inference
- T02 XGrammar Inference
- T02 Collator Diagnostic Script
- T02 Merge Fix Script
- T02 Merge Coverage Check Script
- T02 Inference Schema Test
- Makham (working together with Claude Code — continuing from the July 9 session, see `2026-07-09.md`)
- 2026-08-29
- ตอนที่ 4 (2026-07-29) — คืนนี้เจอว่า "ของที่เราภูมิใจที่สุด" อาจไม่เคยถูกทูนเลย
- finetune_output_contract — what the fine-tune model must output for Constistant
- Rules for Touching Raw Training JSON
- t01 — dataset + สคริปต์เทรน (พร้อมใช้)
- 0.4 — re-check สคริปต์บรรทัดต่อบรรทัด ✅ ผ่าน (เจอ+แก้บั๊ก 8 ข้อ, มะขามสั่งทำ+ติ๊ก 2026-07-28)
- ทีละด่าน
- Merged Pattern — Generation 4 (Claude Gen 2 × Makham Gen 3, merged 2026-07-06)
- 2026-07-06.md
- Archive — historical / superseded / reference docs, one place to read
- Stage B1 — Element Extractor
- extract_house01_local.py
- drawing-purson.js
- 🚀 Quick Start — 5 Minutes to First Annotation
- [Afternoon/evening] Makham (working together with Claude Code — moved to starting house #2 instead of #6)
- บันทึกการแก้ไข
- manifest.json
- qwen-processor.js
- extract_houses_local.py
- WORKFLOW สำหรับ intern — เดินบ้าน 1 หลังผ่านสายพาน t04 Purson
- 2026-08-02
- ตอนที่ 2 (2026-07-24) — วันนี้ทำอะไร "ก่อน" เช่าการ์ดจอ ทำไมต้องทำขนาดนี้
- pdf-processor.py
- Stage A — Page Classifier
- 0. FORMAT LOCK — read this before anything else (added 2026-08-02)
- organize.py
- PROMPT START
- วิจัย: ใช้ Qwen grounding (pixel/bbox) เทียบกับ gridmaster เพื่อตรวจสอบคาน
- 🚨 คู่มือฉุกเฉิน Purson — ใช้ตอนคุยกับ Claude ไม่ได้
- t04_Purson/README.md
- destrier_test_house/op04_score.py
- proof/op04_score.py
- 03บ้าน_เล็ก_2ชั้น_01 (รอบตรวจภาพต้นฉบับ 2026-07-20)
- 64. ตรวจอิสระรอบ fable — "ทุกอย่างเป็น pattern เดียวกันไหม?" คำตอบตอนเริ่ม: ยัง / คำตอบตอนจบ: ใช่ (2026-08-02)
- [Morning] Makham (working together with Claude Code — continuing house #2's review, see `2026-07-15.md`)
- Claude — continuing from the entry above: rented a real GPU + full training + full export cycle, this round finished successfully (Phase 1-10)
- [morning–afternoon] Claude — session with Makham
- Supported Models
- ARCHIVE.md
- check_house
- ทดลองถอดแบบบ้าน 01/03/04 ด้วย t02 (LoRA adapter, ไม่ใช่ tuning round ใหม่)
- ทดลองถอดแบบบ้าน 08/09/10/11 ด้วย t02 (LoRA adapter, ไม่ใช่ tuning round ใหม่)
- t05_Courser/pass0_material_list_batch.py
- go.py
- serve_purson.py
- training/pass0_material_list_batch.py
- [Continuing from the July 7 session] Makham (working together with Claude Code — same session, crossing midnight)
- [Morning-afternoon] Makham (working together with Claude Code — continuing from the July 12 session, see `2026-07-12.md`)
- [00:30–03:30] Claude — session with Makham (continuing from the night of the 28th)
- ตอนที่ 3 (2026-07-28) — วันนี้ t02 ลงมือเช่าจริง เกิดอะไรขึ้นบ้าง
- Stage B2 — Spec / Notes Reader
- t02 dataset provenance — byte-identical copy of t01, deliberately NOT rebuilt
- Pass 0 — Page Classifier (t03)
- PROMPT START
- PROMPT START
- RUNBOOK — ยิง t04 Purson จริงครั้งแรก (เขียน 2026-08-28 สำหรับคืนนี้)
- 05บ้าน_เล็ก_2ชั้น_03 (รอบ F=0 re-origin + item 48, 2026-07-24)
- [17:13] Makham (working together with Claude Code — continuing from the July 10 session, see `2026-07-10.md`)
- [Continuing all day] Makham (working together with Claude Code — continuing house #1's review/fixes started on 2026-07-13, see `2026-07-13.md`)
- สอนมะขาม_รวม.md
- op04 — extract one house, Pass 2 subtasks only
- qwen-api-helper.js
- Primary Raw JSON Schema — Edit Log
- ocr_titleblock
- tune_ai/soup_safetensors.py
- Phase 0 — เตรียมบนเครื่องตัวเอง ก่อนเช่าอะไรทั้งนั้น ($0)
- pull_and_verify_t03.py
- Pass 2.4 - prompt ประกอบเสร็จ ของจริง ทั้ง 3 แขน (อ่านไฟล์นี้ไฟล์เดียวเข้าใจทั้ง pass)
- t05_Courser/pass0_derive.py
- t05_Courser/train_t05_courser.py
- merge_model/soup_safetensors.py
- training/pass0_derive.py
- training/train_t05_courser.py
- Things To Fix
- Claude — re-verified the entire workflow + prepared to shut down the instance + tried running the tuned model on a new house (repo Constistant)
- 2026-08-21
- Raw JSON Data Log
- package.json
- 4. Grid
- md_to_book_pdf.py
- ผล Qwen t02 บ้าน 09 — ไฟล์สำหรับนำเข้า Constistant
- Dataset sizing — ควรมีกี่หลัง และ annotate อะไรบ้าง
- convert_split
- measure_capacity.py
- t05 Courser (Destrier) — แผนที่โฟลเดอร์นี้
- Inventory-first pass — pilot 4 หน้า (บ้าน_เล็ก_1ชั้น_01)
- 02บ้าน_เล็ก_1ชั้น_02
- 60. บ้าน 01-11: ตรวจ+ทำ pattern=plan / footing plan / grid master / section ให้เป็นรูปแบบเดียวกัน (2026-08-02)
- 61. Apply สิ่งที่ต้องแก้.md ให้ครบบ้าน 01-11 — รอบที่ 2 (2026-08-02)
- 2026-08-24
- 2026-08-26.md
- 9. เรื่องใหญ่ที่สุดของวัน — ผลทั้งวันพลิกเพราะ "ค่าที่ไม่ได้ตั้ง" ไม่ใช่ "ค่าที่ตั้งผิด"
- op03 — op01, then shut the laptop down
- merge_no_delete
- Phase 0 — Prep on your own PC, before renting anything ($0, do this first)
- _common.md - shared rule block
- train_t03.py
- t04_Purson/pass0/prompt.md
- Pass 2.4 - Qwen อ่านแบบจริง + hint จาก CV (แขนทดลอง)
- t04 workflow — Purson (InternVL3-78B fine-tune on t04 dataset + hint arm 2 vs 2.4a)
- t05_Courser/smoke_destrier.py
- anchors_by_shape
- training/smoke_destrier.py
- pursonVision.js
- Pilot comparison: Claude vs Qwen — บ้าน_เล็ก_1ชั้น_01 (4 หน้า)
- Vast.ai template — Constistant fine-tune (Qwen3-VL-8B + Unsloth)
- 03บ้าน_เล็ก_2ชั้น_01
- 04บ้าน_เล็ก_2ชั้น_02
- [Afternoon-evening] Makham (working together with Claude Code — continuing from the July 11 session, see `2026-07-11.md`)
- 2026-07-20.md
- 2026-09-01
- Workmen's Diary
- 4. 0.3 — "ซ้อมของจริง" บนคอมตัวเองก่อน (local dry run)
- Prompt Library — Thai RC Drawing Pipeline
- The grid master records EVERY printed dimension in the whole set (added 2026-08-21, Makham)
- 4a. `notes` pattern — the `notes{}` object (added 2026-08-21)
- 6b. Footings and pile caps — same flat fields as everything else (added 2026-08-28)
- convert
- t05_Courser/worker_page.py
- worker_page_raw_pratyad.py
- t05_Destier — ทุกอย่างที่ "ใช้จริง" ของ Destrier รวมไว้ที่เดียว
- training/worker_page.py
- index.ts
- 5. Rebar spec — รวมโครงสร้างใหม่ (breaking change จากทั้ง 2 ฝั่งเดิม แต่มีเหตุผลจากหลักฐานจริง)
- stale_value_logs — ย้ายออกจาก training data 2026-08-25
- 05บ้าน_เล็ก_2ชั้น_03
- 63. ล็อกรูปแบบในสเปค + ทำ checker อัตโนมัติ — เตรียมรับ op1 บ้าน 1000 หลัง (2026-08-02)
- 2026-08-18
- 2026-08-27
- 11. พรุ่งนี้ทำอะไรต่อ — เรียงตามลำดับ
- 2. เจอบั๊กใหม่ที่ไม่เคยเจอในรอบ t01 — เพราะ "เวอร์ชันไลบรารีขยับ"
- 4. 🔑 หลักฐานที่ทำให้สงสัยว่า LoRA ไม่ได้อยู่ใน GGUF
- op01 — extract one house into raw JSON
- house_of
- t01/data_before_tune/eval_fields.py
- t02/data_before_tune/eval_fields.py
- t02/data_before_tune/onstart.sh
- t02 inference results — beam plan pages, ad-hoc read (ไม่ใช่ eval รอบเป็นทางการ)
- pass2_gridline.md - the grid master
- pass2_material_list.md - bill of quantities (BOQ)
- pass2_notes.md - project-level specifications
- pass2_plan.md - structural plans
- pass2_plan_beam.md - beam plan (floor beams and roof framing)
- pass2_plan_column.md - column plan (not wired into training - see note)
- pass2_plan_footing.md - footing / pile-cap plan
- pass2_plan_slab.md - floor slab plan
- pass2_schedule.md - summary tables
- pass2_section.md - detail sections (rebar specs)
- pass2_soil_boring_log.md - soil investigation / borehole log
- pure_power_read.py
- t05_Courser/run_cv_batch.py
- t05_Courser/run_queue.sh
- t05_Courser/run_queue_elements.sh
- t05_Courser/run_queue_gpuA.sh
- _common.md - shared rule block
- Pass 0 - page classification
- pass2_gridline.md - the grid master
- pass2_material_list.md - bill of quantities (BOQ)
- pass2_notes.md - project-level specifications
- pass2_plan_beam.md - beam plan (floor beams and roof framing)
- pass2_plan_column.md - column plan (not wired into training - see note)
- pass2_plan_footing.md - footing / pile-cap plan
- pass2_plan_slab.md - floor slab plan
- pass2_schedule.md - summary tables
- pass2_section.md - detail sections (rebar specs)
- pass2_soil_boring_log.md - soil investigation / borehole log
- training/run_cv_batch.py
- training/run_queue.sh
- training/run_queue_elements.sh
- training/run_queue_gpuA.sh
- 2026-07-05.md
- 2026-07-07.md
- 2026-08-20
- 3. 🔑 เบาะแสสำคัญ: "พังในแบบที่ผิดธรรมชาติของโมเดลที่ทูนมาแล้ว"
- แคตตาล็อก AI — ทางเลือกโมเดล Vision ขนาด 100-200B (นอกจาก Qwen)
- json_แก้ไขแล้ว/สิ่งที่ต้องแก้.md
- 1. Pattern taxonomy — 19 types
- t01/data_before_tune/onstart.sh
- load_split
- load_split
- load_split
- 0.0 ตารางคุมตัวแปร — หัวใจของรอบนี้
- t04_Purson/data_before_tune/onstart.sh
- onstart_llamafactory.sh
- destrier_test_house/op04_gpu_setup.sh
- destrier_test_house/op04_run.py
- t05_Courser/onstart.sh
- proof/op04_gpu_setup.sh
- proof/op04_run.py
- training/onstart.sh
- t44_Voldemort/onstart.sh
- 2026-07-01
- 2026-07-02
- 2026-07-30
- 2026-07-31
- 2026-08-01
- 2026-08-04
- 2026-08-05
- 2026-08-07
- 2026-08-08
- 2026-08-09
- 2026-08-10
- 2026-08-14
- 2026-08-16
- 2026-08-22
- 2026-08-28
- 7. ทำไมมันช้า — เลขจริงและเหตุผล
- CLAUDE.md
- README.md
- compare_eval.mjs
- pass1.5_cv/README.md
- pass1/README.md
- pass2.5_harvest/README.md
- results/README.md
- vast-template/onstart.sh
- 2026-07-19.md

## God Nodes (most connected - your core abstractions)
1. `2026-08-30` - 26 edges
2. `Performance & Quantization` - 23 edges
3. `Primary Raw JSON Schema` - 21 edges
4. `Primary Raw JSON Schema` - 20 edges
5. `t02 workflow — Qwen3-VL-30B-A3B vs Qwen3.6-35B-A3B (A/B ตัวต่อตัว)` - 20 edges
6. `Pass 1 — Input/Output contract, per pattern` - 19 edges
7. `t01 workflow — Qwen3.6-35B-A3B → Local GGUF, No Ongoing GPU Rental` - 18 edges
8. `01บ้าน_เล็ก_1ชั้น_01` - 18 edges
9. `เช่า 4 การ์ดพร้อมกัน — เริ่มรอบเทรนจริง (att1235 มอบแล้ว 2026-08-31 ดึก)` - 18 edges
10. `t03 workflow — per-subtask multi-pass fine-tune` - 17 edges

## Surprising Connections (you probably didn't know these)
- `check_house()` --indirect_call--> `scan()`  [INFERRED]
  tools/check_format.py → tune_ai/t04_Purson/data_before_tune/measure_id_ceiling.py
- `generate()` --calls--> `grammar_setup()`  [INFERRED]
  tune_ai/t04_Purson/data_before_tune/infer_house_t04.py → tune_ai/t02/data_before_tune/run_house_batch.py
- `main()` --calls--> `log_action()`  [EXTRACTED]
  No_touch_box/log_claude_analysis.py → No_touch_box/log_utils.py
- `generate()` --calls--> `grammar_setup()`  [INFERRED]
  tune_ai/t01/data_before_tune/run_house_batch_t01.py → tune_ai/t02/data_before_tune/run_house_batch.py
- `generate()` --calls--> `grammar_setup()`  [INFERRED]
  tune_ai/t04_Purson/data_before_tune/infer_house_t03.py → tune_ai/t02/data_before_tune/run_house_batch.py

## Import Cycles
- None detected.

## Communities (292 total, 40 thin omitted)

### Community 0 - "CV Scan Detection Pipeline"
Cohesion: 0.06
Nodes (65): cv_hint_text(), demo(), draw_som_marks(), number_elements(), page_hint(), แปลง scan → บล็อกข้อความแปะท้าย prompt pass 2.4 (แขน 2.4a ข้อความล้วน — 2.4b ยกเ, เอา detection ของหน้านี้เอง (ทุกตัวที่ผ่านคลังกลาง) เป็น template กวาดซ้ำเข้ม 0., ลายนิ้วมือหยาบๆ จากจำนวนที่เจอ — ไว้เช็คขวางป้าย pass0 ไม่ใช่แทนที่มัน (+57 more)

### Community 1 - "Harvest Report - Template Match QA"
Cohesion: 0.04
Nodes (46): Before running any of these, Corrections made to the first draft (record so they don't get re-litigated), Pass 1 — built 2026-08-21 (`pass1_organize/organize.py`), Prompts — written 2026-08-21, Schema change #1 (earlier same session), Schema change #2 — the grid master now records every printed dimension in the set, Speed, separate from the pass split, Splitting `plan` into sub-subtasks (2026-08-21, Makham) (+38 more)

### Community 2 - "T01 Batch House Extraction (GPU-Rental)"
Cohesion: 0.04
Nodes (46): 0.10 Before you call a house finished, 0.1 The container — never invent an array name, 0.2 Every element carries these four, 0.3 `element_id` = the mark printed on the drawing, nothing else, 0.4 `element_type` — reuse, don't invent, 0.5 Dimensions are integer millimetres, 0.6 Rebar is always an object, never a string, 0.7 `printed_as` — keep the drawing's own words (+38 more)

### Community 3 - "T01 House 08-11 Local vs GPU Workflow"
Cohesion: 0.07
Nodes (39): call_qwen(), extract_pdf_text(), find_pdf(), grounding_block(), main(), page_index_from_filename(), process_page(), prompt variant B — แนบ text layer ที่ดึงมาแล้วเป็น ground truth (+31 more)

### Community 4 - "T02 Dataset Provenance & Training Bugs"
Cohesion: 0.04
Nodes (46): 10. ลองเองได้เลย — คำสั่งทั้งหมด, 11. สรุปแบบสั้นที่สุด, 12.1 ตัวที่เก่งแต่ใช้ไม่ได้ — Pixtral-Large, 12.2 ทำไมตัวอื่นก็ตกรอบเหมือนกัน, 12.3 อัปเดต — เช็คซ้ำอีก 2 ตัวที่เหลือค้าง, 12.4 ตามหาตัวแทน NVLM-D-72B ต่อ — ยังไม่เจอตัวที่แทนได้เป๊ะ, 12. ภาคผนวก — ลองหาโมเดล AI ตัวอื่นนอกจาก Qwen, 1.1 t03 เทรนเสร็จแล้ว แต่ยังไม่ชนะ (+38 more)

### Community 5 - "T03 GT-vs-AI Overlay Renderer"
Cohesion: 0.08
Nodes (33): discover_pages(), generate(), load_model(), log(), main(), variant='tuned' -> base+adapter (PEFT); variant='base' -> base เพียวๆ ไม่มี adap, xgrammar builtin JSON grammar — เหมือน t02's run_house_batch.py (rule_of_tune.md, StoppingCriteria แบบ duck-typed (import transformers.StoppingCriteria ตรงๆ ในฟัง (+25 more)

### Community 6 - "T02 House09 Export & Inference Runs"
Cohesion: 0.05
Nodes (39): 🔴 A serious bug: a parallel pip install broke the training job's environment, Actual measured baseline results (before tuning), Actual quality measurement of the tuned model (`eval_fields.py --adapter`, compared against baseline), Added a testing tool before running the full job (to prevent wasting money again), Calculating the time/cost for the full run, Claude — continuing from the entry above: the first 3 OOM fixes didn't work, had to genuinely reduce LoRA rank (Makham's own decision), Claude — continuing from the top entry: the "GPU out of memory" problem (CUDA out of memory) — explained in great detail, as Makham requested, Claude — detailed log, continuing from the entry above (Makham asked for this to be recorded in as much detail as possible, "because I don't know anything, you'll have to walk me through it, I want to actually learn") (+31 more)

### Community 7 - "T01 Dataset Builder (build_dataset.js)"
Cohesion: 0.05
Nodes (38): Activation Offloading (Small-VRAM Large-Batch), Advanced Save Formats (v0.53.0), Assistant-only loss masking, Batch size vs gradient accumulation, BitNet 1.58-Bit Fine-Tuning (BETA, live in v0.71.20), Chat-template hardening, Correctness First (v0.36.0), Cross-Document Attention Masking (+30 more)

### Community 8 - "T02 Dataset Builder (build_dataset.js)"
Cohesion: 0.05
Nodes (37): 05:46 — 3/4 fold จบ · fold1 OOM · ตัดสินใจ merge k=3, 08:16 — watcher หลุด SSH กลางทาง, GPU ว่างไปสั้นๆ, กู้กลับมารันต่อแล้ว, 10:00–11:40 — เช่า 2 การ์ด (A=กำลังดิบ / B=ระบบ pass) · ซ้อมใช้งานจริงผ่านคิว Supabase สำเร็จ · เจอสาเหตุ GPU-A ช้า, 12:00–14:30 — op04: วัด recall จริงครั้งแรกของ destrier + เจอตัวการ "หลุดภาษาจีน" คือ greedy decoding, 12:45–13:30 — merge สำเร็จ · destrier ขึ้น HF · คืนการ์ด 3 ใบ · smoke test กำลังรัน, 13:30–ปัจจุบัน — smoke test destrier + คิว pure-power อ่านบ้านนอกคลัง, 15:52 — มะขามจับได้ว่าผล destrier ไปเก็บผิดที่ (ใต้ t04_Purson แทน t05_Courser), 2026-08-31 (+29 more)

### Community 9 - "T03 Comparison PNG Report Builder"
Cohesion: 0.09
Nodes (32): draw_element(), parse_zone(), Overlay house09 (บ้าน_เล็ก_1ชั้น_04) — GREEN = ground-truth elements, ORANGE =, E1' -> ('E','1'); None if ids unknown., F-E x 1'-2'' -> ((y0,y1),(x0,x1)) in metres; None if unparsable., Returns True if anything was drawn for element e., render_page(), split_point() (+24 more)

### Community 10 - "T03 Gridline/Plan Prompt Passes"
Cohesion: 0.05
Nodes (36): 10. ✅ ยืนยันแล้ว: 1 ไฟล์ PNG ของ BOQ อาจมี 2 แผ่นจริงซ้อนกัน (ต้องหมุน 90° + แยกซ้าย-ขวา), 1. ✅ นำ `span_source` กลับมาใช้ (ยืมจาก Gen 2) — จำเป็นจริง ไม่ใช่แค่ nice-to-have, 2. ✅ Atomic beam segment — คานยาว 1 มาร์คต้องแยกเป็นหลาย entry ตามช่วง grid จริง ไม่ใช่นับรวมเป็น `count`, 3. ✅ `slab` element_type ครอบคลุมสัญลักษณ์ marker พื้นแบบ SO/SI/SX/ST ด้วย (ไม่ใช่ "unknown_symbol"), 4. ⚠️ Ø (สัญลักษณ์กลม) = RB เสมอ ไม่ใช่ DB — อย่าเดาจากขนาดเส้นผ่านศูนย์กลาง, 5. ❓ เปิดคำถามใหม่: เหล็กบน-ล่างไม่เท่ากัน (asymmetric main bar) — ยังไม่มี field รองรับ, 6. ❓ เปิดคำถามใหม่: เหล็กเสริมพิเศษที่หยุดกลางคาน (stop bar / curtailment ที่ L/8) — mk_test แก้ปัญหานี้ไว้แล้ว แต่ยังไม่ยืนยันเป็นทางการ, 7. ❓ เปิดคำถามใหม่: ตารางเสาหลายระดับ (เช่น C1 มีสเปคต่างกันตามชั้น) — 2 วิธีที่เป็นไปได้ ยังไม่ตัดสินใจว่าจะยึดแบบไหน (+28 more)

### Community 11 - "T03 Dataset Builder (build_dataset_t03.py)"
Cohesion: 0.06
Nodes (33): 10. Tonight's lessons — 6 things worth remembering, 11. What to do tomorrow — in order, 12. Questions still without answers, 1. What happened tonight — in chronological order, 2. How is it "awful" — but let's be fair first, 3. 🔑 The key clue: "broken in a way that is unnatural for a model that has actually been tuned", 4. 🔑 The evidence that raises the suspicion that the LoRA is not in the GGUF, 5.1 Training and inference see the image at resolutions 14× apart (+25 more)

### Community 12 - "T01 Single-House Local Extraction Script"
Cohesion: 0.11
Nodes (30): _beam_span_m(), build_transform(), collect_anchors(), _cv_only_points(), demo(), _element_refs(), _fit_line(), grid_pos() (+22 more)

### Community 13 - "T01 Multi-House Local Extraction Script"
Cohesion: 0.13
Nodes (29): bare(), build_pass0(), build_pass24(), build_pass3(), cluster1d(), elements_flat(), expand_pool(), fit_axis() (+21 more)

### Community 14 - "T03 Common Rules Header"
Cohesion: 0.13
Nodes (29): bare(), build_pass0(), build_pass24(), build_pass3(), cluster1d(), elements_flat(), expand_pool(), fit_axis() (+21 more)

### Community 15 - "T03 Pass1 Page Organizer"
Cohesion: 0.07
Nodes (25): Phase 0 — Pre-flight (ทำก่อนรันเต็ม, $0 แต่เสียเวลาเครื่องจริงหลักชั่วโมง/วัน), Phase 1 — ทดสอบสั้นก่อนเสมอ (ทำไปแล้ว 2 รอบ, ยืนยันด้วยตัวเลขจริง), Phase 2 — รันเต็ม (ยังไม่ทำ — รอ Phase 0 ข้อ 4-6 ก่อน), Phase 3 — (ทางเลือก, ยังไม่ทำ) เทียบกับ ground truth, ข้อจำกัดที่รู้อยู่แล้ว บอกตรงๆ, ขนาดงานจริง (นับแล้ว ไม่ใช่ประมาณ), ตัวกรองหน้า — ใช้ t03 Pass 2 แทนตัวกรองเดิมของ t01, ตัวเลขเวลาจริงที่วัดแล้ว (smoke-test บ้าน 08, โมเดล tuned) (+17 more)

### Community 16 - "T03 Notes/Soil-Boring Passes & Schema Drift"
Cohesion: 0.07
Nodes (26): 2026-08-30, Claude (att1235 — มะขามไปทำมาม่า, ตัดสินใจเองต่อ), Claude (audit ตามคำสั่งมะขาม: เช็ค workflow + diary + rule_of_tune Mark of Shame), Claude (fold0 เทรนเสร็จตัวแรก — อัป HF + Day of Shame), Claude (fold2 เทรนเสร็จตัวที่ 2 + บั๊กจริงเรื่อง hf upload folder + เริ่ม eval), Claude (คิวบน Supabase ทำงานจริงแล้ว — เหลือแค่ GPU), Claude (ตอบคำถามคลัง CV + เครื่องมือตรวจ staging), Claude (ทดลองใช้จริง: จำลองผู้ใช้อัปบ้าน 01 เข้าเว็บ → เจอบั๊กเก่าที่ไม่มีใครรู้) (+18 more)

### Community 17 - "T03 Pass3/Pass4 Takeoff Prompts"
Cohesion: 0.07
Nodes (26): ⚠️ กับดักที่เกือบหลอกเราสำเร็จ, ตอนที่ 0 — ปูพื้นก่อน: เราสอนโมเดลยังไง, ตอนที่ 1 — Purson (t04) พัง เพราะ "แว่นตาผิดอัน", ตอนที่ 2 — Voldemort (t44) พัง คนละสาเหตุกันเลย, ตอนที่ 3 — สรุปเทียบสองตัว, ตอนที่ 4 — สมการรวมโมเดล (ที่ Claude เอาของมารวมกัน), ตอนที่ 5 — เรื่องที่มะขามจับได้เอง (และถูกด้วย), ตอนที่ 6 — สรุปบทเรียนทั้งหมดใน 6 บรรทัด (+18 more)

### Community 18 - "T02 House09 Overlay Renderer"
Cohesion: 0.08
Nodes (24): 2026-08-02 — sync `json_แก้ไขแล้ว/` กลับเข้า raw ครั้งแรกของโปรเจกต์ (362 ไฟล์), 2026-08-09 (2) — สาเหตุจริงของ pattern ไม่ตรงกัน: `check_format.py` เช็คลมเงียบๆ เมื่อได้ path ผิด (แก้แล้ว), 2026-08-09 — แก้ `png`/`doc_page` สลับขั้วในกริดมาสเตอร์บ้าน 14-18 (5 ไฟล์), Activity log อัตโนมัติ (เพิ่ม 2026-07-03) — `pipeline_activity_log.json`, Architecture — 2 generation ของ logic (สำคัญ: ใช้ generation ล่าสุด), CLAUDE.md — No_touch_box/, Convention, Generation ปัจจุบัน (ใช้จริง) — `run_pipeline.py` + `build_document_map.py` (+16 more)

### Community 19 - "T03 Pass0 Classifier (current vs superseded)"
Cohesion: 0.08
Nodes (24): Purson worker — ต่อโมเดลของเราเข้า Constistant, ความปลอดภัย, ติดตั้ง (เครื่องที่จะรัน worker), ⚠️ ทำไมไม่ใช้ vLLM (ตรวจจริง 2026-08-30 — ก่อนเช่าการ์ด), วันพรีเซนต์ (เปิด GPU เฉพาะตอนใช้) — `presentation.py`, เปิด GPU endpoint (บนเครื่องเช่า) — `serve_purson.py`, โหมด A vs B — ต่างกันแค่ "worker.py รันที่ไหน" โค้ดชุดเดียวกันทุกไฟล์, 1. ยิงพร้อมกัน 2 งาน → เซิร์ฟเวอร์ค้างทั้งระบบ (+16 more)

### Community 20 - "T03 Dataset Pull & Verify Script"
Cohesion: 0.08
Nodes (25): Arm the dead-man's switch first — before step 1, Escalation rule, Folder structure + naming convention, Full workflow summary, Handoff contract between stages, `op1` is a standing order — decide, don't ask, Quick command: `op1 <house_name>`, Quick command: `op2 <house_name>` — staged run with automatic model switching (+17 more)

### Community 21 - "Markdown-to-PDF Book Builder"
Cohesion: 0.12
Nodes (18): call_purson(), claim_next_job(), download_image(), _element_is_garbage(), load_prompt_file(), main(), now_iso(), คืน prompt เต็มของ subtask หรือ None ถ้าไม่มีไฟล์ prompt (= ยังไม่รองรับ)     d (+10 more)

### Community 22 - "T03 Visual Token Capacity Measurement"
Cohesion: 0.08
Nodes (24): 10. สรุปบทเรียนคืนนี้, 1. อาการ — "ตอบไม่จบประโยค" หน้าตาเป็นยังไง, 2. ทำไม AI ถึงวนพูดไม่จบ, 3. ความพยายามที่ 1 — ปรับพารามิเตอร์ (ช่วยได้ แต่ไม่พอ), 4. ความพยายามที่ 2 — Grammar-constrained decoding (ตัวที่แก้จบ), 5. บทเรียนที่แพงที่สุดของคืนนี้ — ผมวินิจฉัยผิด แล้วเขียนลงเอกสารไปแล้ว, 6. ผลลัพธ์จริง — วัดได้เป็นตัวเลข, 7. บั๊กที่ grammar แก้ไม่ได้ (มี 1 ตัว เจอจริง) (+16 more)

### Community 23 - "Merge Guard Safety Layer"
Cohesion: 0.08
Nodes (23): 10. How to read the results during training/evaluation — what these numbers mean, 11. Glossary at the end (quick reference), 12. The confusing incident of "why doesn't the log file I ordered exist" — a lesson about terminal command queuing, 13. The incident "training finished, then it broke anyway" — a lesson about a "shared environment", 14. Real quality measurement results — did the tuning work (answer: yes, clearly), 15. Why "converting to GGUF" has so many steps + what problems were hit, 16. Tonight's final lesson — destroying the instance before backing the files up, 1. Overview: what's being done today (the whole journey) (+15 more)

### Community 24 - "T03 Training Script (train_t03.py)"
Cohesion: 0.09
Nodes (22): Annotated Dataset Format, Contact, Folder Structure, JSON parse errors in review.html, JSON Structure Reference, Next Steps (Fine-tuning), PDFPlumber/pdf2image errors, Poppler not found (+14 more)

### Community 25 - "T03 Dataset Sizing Analysis"
Cohesion: 0.09
Nodes (22): 1. Recap: what question does t02 answer, 2. A new bug never seen in the t01 round — because "the library version drifted", 3. Reading the loss curve during training — what is loss, what does it tell us, 4. VRAM going up and down during training — why, 5. Why Qwen3-VL is 2.9x slower than Qwen3.6, with all settings identical, 6. The real Phase 7 results — t02 loses to t01 on every metric, 7. Why Phase 7.5 has to load the whole model again — what a LoRA adapter really is, 8. New vocabulary today (continuing from the glossary at the end of the 07-24 file) (+14 more)

### Community 26 - "Format Validation Gate"
Cohesion: 0.09
Nodes (23): 10. วิธีอ่านผลลัพธ์ตอนเทรน/วัดผล — ตัวเลขพวกนี้แปลว่าอะไร, 11. สรุปคำศัพท์ท้ายเล่ม (เปิดดูเร็วๆ ได้), 12. เหตุการณ์สับสน "ทำไม log ไฟล์ที่สั่งไว้ถึงไม่มี" — บทเรียนเรื่อง terminal คิวคำสั่ง, 13. เหตุการณ์ "เทรนเสร็จแล้วดันพัง" — บทเรียนเรื่อง "environment ใช้ร่วมกัน", 14. ผลวัดคุณภาพจริง — การทูนได้ผลไหม (คำตอบ: ได้ผลชัดเจน), 15. ทำไม "แปลงเป็น GGUF" ถึงมีหลายขั้นตอน + เจอปัญหาอะไรบ้าง, 16. บทเรียนสุดท้ายของคืนนี้ — ทำลาย instance ก่อนสำรองไฟล์ออกมา, 1. ภาพรวม: วันนี้ทำอะไรอยู่ (เส้นทางเดินทั้งหมด) (+15 more)

### Community 27 - "Qwen Export Converter"
Cohesion: 0.10
Nodes (18): CFG, clean(), DROP_KEYS, est(), examples, fs, HARD_LEAK_RE, houses (+10 more)

### Community 28 - "T03 ID Ceiling Measurement"
Cohesion: 0.10
Nodes (18): CFG, clean(), DROP_KEYS, est(), examples, fs, HARD_LEAK_RE, houses (+10 more)

### Community 29 - "T01 Eval Fields Script"
Cohesion: 0.10
Nodes (21): 1. `gridline` — ใช้หน้า 00 ของทุกบ้านตรงๆ ✅ ตัดสินใจแล้ว, 2. `title` / `site_plan` / `bbs_schedule` / `soil_boring_log` — แก้ที่ dataset ตรงๆ ✅ ตัดสินใจแล้ว, 3. Pass 0 — เขียนออกมาก่อน แม้ยังไม่จบ ✅ เขียนแล้ว (draft v1), 4. Token budget — ยังไม่ทำ รอทุกอย่างนิ่งก่อน ✅ ตัดสินใจแล้ว, input, output, output ที่ต้องได้ (§2 + §3), Pass 0 — จำแนกหน้า + wrapper (+13 more)

### Community 30 - "T02 Eval Fields Script"
Cohesion: 0.17
Nodes (18): apply_arm(), element_ids(), generate(), hide_grid_lines(), load_model(), main(), norm_id(), eval เท่านั้น — สืบมาจาก infer_house_t03.py ตรงๆ ห้ามใช้กับงานสกัดจริง (+10 more)

### Community 31 - "T02 GPU Rental Onstart Script"
Cohesion: 0.10
Nodes (21): merge_into_pass2(), เติมของที่ขาดใน doc ของ pass2 จากผล pass3 — คืนสรุปว่าเติมอะไรไปบ้าง      เติม, collect_pass15_files(), collect_pass25_files(), crop_for_task(), _crop_image_path(), cv_mark_lookup(), cv_scan_for_task() (+13 more)

### Community 32 - "T03 Beam Grounding Research"
Cohesion: 0.24
Nodes (20): cmd_down(), cmd_smoke(), cmd_status(), cmd_tunnel(), cmd_up(), healthy(), load_state(), main() (+12 more)

### Community 33 - "T01 GPU Rental Onstart Script"
Cohesion: 0.10
Nodes (20): 10. Slab marker (SO/SI/SX/ST) — ยืนยันร่วมกันแล้ว, 11. BOQ — 1 PNG อาจมี 2 แผ่นจริงซ้อนกัน (ยืนยันร่วมกันแล้ว, ต้อง implement ใน `run_pipeline.py`), 12. `source_image` — ทุกไฟล์ต้องระบุไฟล์รูปต้นทางที่อ่านมา (เพิ่มเข้ามา 2026-07-08), 1. Pattern taxonomy — ขยายเป็น 13 ชนิด (อัปเดต 2026-07-08: เพิ่มคำอธิบายต่อชนิด + เปลี่ยนชื่อ 1 ชนิด + เพิ่ม 3 ชนิดใหม่), 20260708draft of prime rawjson, 2. Multi-view ต่อหน้า — ใช้ `views[]` inventory-first ของ Gen 2 เป็นกลไกหลัก, 3.1 คำสั่งสร้างไฟล์ "หน้า 0" grid master (อ้างอิงตรงจาก Makham's Pattern of Raw JSON — 2026-07-05, หัวข้อ "Generation 3.2"), 3. Grid — รวม 3 ฟีเจอร์เข้าด้วยกัน (ไม่มีใครเสีย) (+12 more)

### Community 34 - "T01 Training Script (train_qwen36.py)"
Cohesion: 0.10
Nodes (20): [15:00-15:25] Claude — session with Makham: teaching PDF for today's work (ตอนที่ 4), [15:30-16:00] Claude — session with Makham: item 3 (max token) followed through — 2 real findings, 1 bug fixed, [16:00-16:20] Claude — session with Makham: "เพิ่ม VRAM" → measured first, raised resolution without changing cards, [16:20-17:00] Claude — session with Makham: "section 0% — can pattern recognition fix it?" → diagnosed first, answer is no (and why matters), [17:00-17:25] Claude — teaching PDF (ตอนที่ 4) brought up to date; one stale claim corrected, [18:30-18:50] Claude — session with Makham: metric fix applied ("ไปหาในเน็ตและแก้มาซะ"), [19:00] Claude — ปิดวัน: สรุปงานค้างทั้งหมด (มะขามสั่งจด), [19:20-19:50] Claude — มะขามอนุมัติ att1235 ข้อ 1: แก้ convention element_id ของ section แล้วจริง (+12 more)

### Community 35 - "T01 Training Script (train_qwen3vl.py)"
Cohesion: 0.10
Nodes (19): 3 ข้อที่ต้องเคาะก่อนเริ่ม, ~~grid ref ใน hint~~ — แก้เป็นแถว/ช่องเชิงลำดับ (พบตอนลงมือ 2026-08-26), § hint design — pass 2.4 ป้อนอะไรให้ Qwen, t03 pass design v2 — 2026-08-26 (มะขามสั่ง reset การนับ pass), กฎกันหลอน 4 ข้อ ที่ต้องอยู่ในบล็อก hint, การทดลอง: 3 แขน ไม่ใช่ 2, ของที่มีอยู่แล้ว ไม่ต้องเริ่มจาก 0, งานที่ต้องทำ เรียงตามลำดับ (+11 more)

### Community 36 - "T02 Training Script (train_qwen3vl.py)"
Cohesion: 0.10
Nodes (19): A. Environment (ก่อน import torch), 🔑 `att1235` — มะขามมอบให้ Claude สำหรับรอบนี้ (2026-08-31, ก่อนไปนอน), B. โหลดโมเดล, C. ภาพ — โซนที่ฆ่า t01/t02/t04 มาแล้ว 3 รอบ (rule_of_tune ข้อ 15), D. ความยาว sequence, Data-gap ที่ต้องปิดก่อน build (เรียงตามลำดับทำ), 📦 Dataset t05 — ของเดิม + 3 pass ใหม่ (มะขามสั่ง "เอา pass0 pass2.5 และ pass3 ใส่มา"), E. LoRA (+11 more)

### Community 37 - "T03 GPU Rental Onstart Script"
Cohesion: 0.11
Nodes (19): Phase 10 — โหลดลงเครื่องตัวเอง + รันจริง ⛔ ข้าม — ไม่มี GGUF ให้โหลด (ดู Phase 8), Phase 11 — ⛔ HARD BLOCK ห้ามทำลาย instance โดยไม่มีคำสั่งชัดเจน ⬜, Phase 1 — เช่า + ต่อ SSH ✅ (RTX PRO 6000 96GB, RAM 188GB, disk 300GB, 2026-07-28), Phase 2 — อัปโหลด dataset + สคริปต์ ✅ (315/88/398 ครบ, hash ตรง §0.3, 2026-07-28), Phase 3 — ตรวจเครื่อง ก่อนแตะ dataset ✅ ผ่านครบทุกข้อ ไม่มี ✗ เลย (2026-07-28), Phase 4 — baseline ก่อนทูน ✅ (0/20 JSON valid, 0/170 element — ตรงกับ t01, 2026-07-28), Phase 5 — รันสั้นก่อน (ประกันราคาถูก ทำทุกครั้ง) ✅ ผ่านครบ 4 ข้อ (2026-07-28), Phase 6 — เทรนเต็ม ✅ 120/120 step ผ่านครบ ไม่มี error (eval_loss 0.2076, 2026-07-28) (+11 more)

### Community 38 - "T01 GGUF Export Script"
Cohesion: 0.11
Nodes (19): 10. `title`, 11. `symbol`, 12. `roof_plan`, 13. `misc`, 14. `bbs_schedule` — ⛔ ไม่มีตัวอย่างเทรนเลย, 15. `soil_boring_log` — ⛔ ไม่มีตัวอย่างเทรนเลย, 1. `plan`, 2. `section` (+11 more)

### Community 39 - "T01 Environment Verification"
Cohesion: 0.16
Nodes (17): build_folds(), filter_elements(), find_image(), gather_all_rows(), gt_for_plan_subtask(), load_prompt_block(), main(), prompt_for() (+9 more)

### Community 40 - "T02 GGUF Export Script"
Cohesion: 0.23
Nodes (18): bold(), build_html(), esc(), estimate_height(), fmt_pct(), main(), measure_height(), nlines() (+10 more)

### Community 41 - "T02 Merge Diagnostic Script"
Cohesion: 0.19
Nodes (18): as_text_parts(), bare(), build_house_folds(), bypass(), collect_pass024(), fix_pass1_paths(), house_of_image(), main() (+10 more)

### Community 42 - "T02 Environment Verification"
Cohesion: 0.19
Nodes (18): as_text_parts(), bare(), build_house_folds(), bypass(), collect_pass024(), fix_pass1_paths(), house_of_image(), main() (+10 more)

### Community 43 - "T02 Inference Script (infer_t02.py)"
Cohesion: 0.11
Nodes (18): 1. Why we had to spend so much time checking today, when nothing has been rented yet, 2. 0.1 — testing the HuggingFace key before relying on it, 3. 0.2 — checking the Vast.ai account balance + a point we nearly missed again, 4. 0.3 — a "dress rehearsal" on your own computer first (local dry run), 5. 0.4 — re-reading the scripts seriously, and finding a bug nobody knew about, 6. 0.5 — picking a real rental machine from a listing that really exists, 6.5. What exactly is llama.cpp — and why not use Unsloth to run it in real use, 7. Summary: Phase 0 is done — are we ready to rent for real? (+10 more)

### Community 44 - "T02 Grammar-Constrained Inference"
Cohesion: 0.11
Nodes (18): apply_arm() — ตัวสลับแขนทดลอง (อยู่ใน infer_house_t03.py ไม่ใช่ไฟล์แยก), pass0/README.md → ชี้ไป tune_ai/t03/pass0_classify/, pass1.5_cv/README.md → ชี้ไป tools/cv_scan.py, pass1/README.md → ชี้ไป tune_ai/t03/pass1_organize/organize.py, pass2.4_hint/assembled_example.md, pass2.4_hint/prompt.md, pass2.5_harvest/README.md → ชี้ไป tools/cv_scan.py (--pass25), pass2/README.md → ชี้ไป tune_ai/t03/pass2_used/ (prompt 7 ตัว) (+10 more)

### Community 45 - "T02 XGrammar Inference"
Cohesion: 0.11
Nodes (16): 1. สถาปัตยกรรม (ยืนยันจาก config.json + paper arXiv 2504.10479), 2. ไขปริศนา t04 ครบทุกข้อ (ตอนนี้รู้กลไกจริงแล้ว ไม่ใช่แค่อาการ), 3. 🔴 การค้นพบใหม่ — อาจเป็น "สาเหตุที่สอง" ของคืนที่แล้ว ซ้อนอยู่ใต้เรื่อง tile, 4. ทางเลือกของแขน InternVL (เรียงตามความเสี่ยง×ราคา), 5. YAML แก้มือ (ต่างจาก t04 สามบรรทัด + ข้อควรระวัง), 6. งบรวม 2 แขนขนาน, InternVL3-78B — dossier ฉบับเต็มสำหรับแขนขนาน (arm B) ของ t05, dataset (2026-08-31 ค่ำ) — k-fold 2, เนื้อเดียวกับแขน Courser เป๊ะทุก fold (+8 more)

### Community 46 - "T02 Collator Diagnostic Script"
Cohesion: 0.11
Nodes (18): 01บ้าน_เล็ก_1ชั้น_01, 10. `หน้า19_view2_beam_plan.json` — fixed a wrongly-labeled additional-rebar position (top of beam → bottom of beam), merged into a single bottom-rebar count, 11. `หน้า19_view2_beam_plan.json` — B3X: lap-splice bar merges into the top rebar (not bottom), 12. `หน้า19_view2_beam_plan.json` — B5X: identical to B3X in every respect (Claude found the image itself from page21), 13. Added new pattern `misc` — page60/61, 14. Element ordering direction reversed: vertical before horizontal (not horizontal-first as originally written), 15. `หน้า19_view2_beam_plan.json` — added 7 missing beams (from a clearer new full-page image) + fixed B4X's 3'/3'' back correctly, 16. Synced the fix between page19 ↔ page20/21 (files sharing the same spec/mark) (+10 more)

### Community 47 - "T02 Merge Fix Script"
Cohesion: 0.12
Nodes (17): Cost estimate for this whole round, Phase 10 — Local run (this is "done" — no more GPU rental from here), Phase 11 — ⚠️ HARD BLOCK — destroy the rented instance ONLY on explicit user go-ahead, Phase 1 — Rent + connect ✅ DONE (2026-07-24), Phase 2 — Upload dataset + scripts ✅ DONE (2026-07-24), Phase 3 — Verify environment (before touching the dataset) ✅ DONE (2026-07-24) — ALL GREEN, Phase 4 — Baseline measurement ⏭️ SKIPPED (2026-07-24, deliberately), Phase 5 — Short test run (always do this — cheap insurance) ✅ DONE (2026-07-24) — PASSED (+9 more)

### Community 48 - "T02 Merge Coverage Check Script"
Cohesion: 0.12
Nodes (16): 10. Slab marker, 10a. Stairs (`element_type: "stair"`) — `grid_ref`, 11. BOQ, 11a. Multi-building drawing sets (added 2026-07-25), 12. Rules still in draft / not yet verified against real data, 13. `site_plan` — `element_type` not standardized across houses, 2. Required fields on every file (wrapper level), 2a. `phase_note` — staged-extraction scratch field (added 2026-07-27) (+8 more)

### Community 49 - "T02 Inference Schema Test"
Cohesion: 0.12
Nodes (15): 10. Cleaned up old files out of the main folder, 1. One final recheck of everything before continuing, 2. Explained/planned setting up the 3 Label Studio projects, 3. Created a mindmap PDF explaining the work structure in simple terms, 4. Makham started creating the real projects in Label Studio Cloud — hit a real scroll bug, 5. Removed/reverted the browser "no style information" fix because it made things worse, 6. Made Material List's image sticky-left like Elements, 7. Moved header fields out of the image column, into the data side instead (+7 more)

### Community 50 - "Makham (working together with Claude Code — continuing from the July 9 session, see `2026-07-09.md`)"
Cohesion: 0.12
Nodes (15): 10. Backed up the whole project to `E:\constitant\20260710\`, 11. Checked readiness for the "name a house → get complete raw JSON + Label Studio" workflow, 12. Added a record in `raw_json_data_log.md` (the log Makham+King had previously kept), [19:13] Makham (working together with Claude Code — same day's work, continuing from the entry above), 1. Created `primary_rawjson_schema` — 2 rounds of trial and error, [20:12] Makham (working together with Claude Code — same day's work, continuing from the entry above), 2. Set up the new structure `rawjson_ยังไม่ได้แก้ไขโดนคน/` (production raw JSON) (repo root), 3. Wired `label-studio-tasks-makham.js` to automatically read from `rawjson_ยังไม่ได้แก้ไขโดนคน/` (+7 more)

### Community 51 - "2026-08-29"
Cohesion: 0.12
Nodes (15): 2026-08-29, Claude (op04 บ้านเล็ก 1 ชั้น ×2 หลังใหม่ — ไทยพอเพียง 1+2), Claude กะดึก (มะขามไปนอน สั่ง att1235 ตัดสินใจเองทั้งหมด), Claude (คำสั่งมะขาม: ยกเลิก pass 4 · ล้าง prompt · ยกเลิกแขน 2.4b · workflow intern), Claude (บ้าน 51/52 → GT เป็น 39/40 · ย้าย t03→t04_Purson · บ้าน 08 เข้า dataset · k-fold infra), Claude (มะขามเคาะ: t04 เปลี่ยนโมเดลเป็น InternVL3-78B), xgrammar เปิดทุก pass (มะขามสั่ง "ใส่ x gramma ทุก pass ตามความเหมาะสม"), กฎใหม่: วัดสัดส่วนเทียบ gridmaster (มะขามสั่ง — "นั่นคือจุดประสงค์ของการมีอยู่ของ gridmaster") (+7 more)

### Community 52 - "ตอนที่ 4 (2026-07-29) — คืนนี้เจอว่า "ของที่เราภูมิใจที่สุด" อาจไม่เคยถูกทูนเลย"
Cohesion: 0.12
Nodes (16): 10. สรุปบทเรียนคืนนี้ — 6 ข้อที่ควรจำ, 12. คำถามที่ยังไม่มีคำตอบ, 1. เกิดอะไรขึ้นคืนนี้ — เรียงตามเวลา, 2. "ห่วย" ห่วยยังไง — แต่ต้องพูดให้แฟร์ก่อน, 5.1 เทรนกับตอนใช้ เห็นภาพคนละความละเอียด 14 เท่า, 5.2 การบีบอัด (quantization) ที่เจ้าของโมเดลเตือนเองว่าอย่าทำ, 5. สาเหตุรองอีก 2 ข้อ (จริงทั้งคู่ แต่ไม่ใช่ตัวหลัก), 6. บทเรียนเรื่อง "ตัวเลข 90% ที่เราเชื่อมาตลอด" (+8 more)

### Community 53 - "finetune_output_contract — what the fine-tune model must output for Constistant"
Cohesion: 0.14
Nodes (13): Acceptance checklist for a model-output house, Field flow per pattern, finetune_output_contract — what the fine-tune model must output for Constistant, Fixed 2026-08-28 — no longer gaps, Folder contents, `grid_master` (one file per building, `หน้า00`) — renamed from `gridline` 2026-08-28, How Constistant consumes these files, How to check your own output against this contract (+5 more)

### Community 54 - "Rules for Touching Raw Training JSON"
Cohesion: 0.14
Nodes (14): 2026-07-21 — "DAY OF SHAME" — Tuned model files (LoRA/GGUF) permanently lost from not warning before instance destroy, BOQ (`categories[].items[]`), Ground Truth JSON Format (reference), Lessons Learned (condensed), Mark of Shame, Override code — `att1235`, Priority order (Asimov-style), Rule 1 (highest priority) (+6 more)

### Community 55 - "t01 — dataset + สคริปต์เทรน (พร้อมใช้)"
Cohesion: 0.14
Nodes (13): 1 ภาพ = 1 example, รวมทุก view, ① ใช้ Qwen ไหม? ตัวไหน?, ② เช่าเครื่องไหน, ③ ต้องทำยังไง (ทำตามนี้ทีละข้อ), ④ มีอะไรในโฟลเดอร์นี้, instruction ~1,020 tok — ความยาวถ่วงน้ำหนักตามความถี่ที่เคยผิดจริง, t01 — dataset + สคริปต์เทรน (พร้อมใช้), การตัดสินใจที่ฝังอยู่ในชุดนี้ (มะขามสั่งเปลี่ยนได้ทุกข้อ) (+5 more)

### Community 56 - "0.4 — re-check สคริปต์บรรทัดต่อบรรทัด ✅ ผ่าน (เจอ+แก้บั๊ก 8 ข้อ, มะขามสั่งทำ+ติ๊ก 2026-07-28)"
Cohesion: 0.14
Nodes (14): 0.4 — re-check สคริปต์บรรทัดต่อบรรทัด ✅ ผ่าน (เจอ+แก้บั๊ก 8 ข้อ, มะขามสั่งทำ+ติ๊ก 2026-07-28), ตารางยืนยัน parity ทั้งหมด (ไล่ทีละบรรทัดกับ `train_qwen36.py` เมื่อ 2026-07-28), บั๊ก 1 🔴 `max_length` ตัดตัวอย่าง gridmaster ทิ้งเกินครึ่ง, บั๊ก 2 🔴 collator ย่อภาพเหลือกว้าง 512 px แบบเงียบ ๆ, บั๊ก 3 🔴 `max_seq_length` default 2048 ตัดกลาง image token, บั๊ก 4 🔴 `enable_thinking=False` หายไป, บั๊ก 5 🟡 epilogue หลังเทรนค้างกิน VRAM, บั๊ก 6 🔴 `lora_dropout=0.05` — MoE ไม่รองรับ (t01 เจอ error จริงมาแล้ว) (+6 more)

### Community 57 - "ทีละด่าน"
Cohesion: 0.14
Nodes (14): Pass 0 — คัดหน้า (Qwen, ไม่แตะ), Pass 1.5 — ตา CV ตรวจของที่ตัดแล้ว 🆕, Pass 1 — จัดของ (โค้ดล้วน ไม่ใช้ AI), Pass 2 / 2.4 — Qwen อ่านแบบจริง (การทดลอง A/B), Pass 2.5 — self-harvest 🆕, Pass 3 — ถอดระยะ/เหล็ก 🆕 (ยังไม่เคยรัน), Pass 4 — หน้ารอง — ❌ ยกเลิกแล้ว (2026-08-29), t04 Purson — สายพาน t03 ฉบับ v2 (+6 more)

### Community 58 - "Merged Pattern — Generation 4 (Claude Gen 2 × Makham Gen 3, merged 2026-07-06)"
Cohesion: 0.14
Nodes (14): 10. Slab marker (SO/SI/SX/ST) — ยืนยันร่วมกันแล้ว, 11. BOQ — 1 PNG อาจมี 2 แผ่นจริงซ้อนกัน (ยืนยันร่วมกันแล้ว, ต้อง implement ใน `run_pipeline.py`), 1. Pattern taxonomy — ใช้ชุด 10 ของ Makham (ขยายจาก 4 ของ Gen 2), 2. Multi-view ต่อหน้า — ใช้ `views[]` inventory-first ของ Gen 2 เป็นกลไกหลัก, 3.1 คำสั่งสร้างไฟล์ "หน้า 0" grid master (อ้างอิงตรงจาก Makham's Pattern of Raw JSON — 2026-07-05, หัวข้อ "Generation 3.2"), 3. Grid — รวม 3 ฟีเจอร์เข้าด้วยกัน (ไม่มีใครเสีย), 4. Beam segment splitting — กติกา 3 แบบของ support point (Gen 2 ทั้งหมด, Makham ยังไม่เคยมี), 6. Spec join (ตำแหน่งใน plan + สเปคจาก section/schedule รวมกัน) — รับของ Makham (Gen 3.3) เต็ม (+6 more)

### Community 59 - "2026-07-06.md"
Cohesion: 0.14
Nodes (13): [~16:00–16:20] Makham (working together with Claude — session continuing from last night), [~16:20–17:00] Makham (working together with Claude — same session, continuing from the previous entry), [~17:00–17:20] Makham (working together with Claude — same session, continuing from the previous entry), [~17:20–17:50] Makham (working together with Claude — same session, continuing from the previous entry), [~17:50–18:10] Makham (working together with Claude — same session, continuing from the previous entry), [~18:15] Makham (working together with Claude — same session, continuing from the previous entry), [~18:20–18:45] Makham (working together with Claude — same session, continuing from the previous entry), [~19:00] Makham (working together with Claude — same session, continuing from the previous entry) (+5 more)

### Community 60 - "Archive — historical / superseded / reference docs, one place to read"
Cohesion: 0.15
Nodes (13): Archive — historical / superseded / reference docs, one place to read, 📜 docs/20260708draft of prime rawjson.md — historical, direct ancestor of the live spec, ⚪ docs/AGENTS.md — not junk, leave it, 📖 docs/FLOORPLANVLM.md — external reference, not project content, 📜 docs/Makham's patter of rawjson20260705.md — historical, the origin document, 📜 docs/merged_pattern_gen4_20260706.md — historical, Index, Not touched — these are live, don't confuse them with the pile below (+5 more)

### Community 61 - "Stage B1 — Element Extractor"
Cohesion: 0.15
Nodes (12): CONFIDENCE POLICY (ฝังทุก prompt), Field mapping → schema.js (สำหรับคน wire pipeline), Prompt A — SECTION_DETAIL, Prompt B — SCHEDULE_TABLE, Prompt C — FLOOR_PLAN, Stage B1 — Element Extractor, System Prompt (ใช้ร่วมทุก sheet_type), THAI NOTATION GUIDE (ฝังทุก prompt) (+4 more)

### Community 62 - "extract_house01_local.py"
Cohesion: 0.35
Nodes (12): call_model(), classify_page(), extract_page(), image_data_uri(), load_classify(), log(), main(), patterns_from_existing_extract() (+4 more)

### Community 63 - "drawing-purson.js"
Cohesion: 0.31
Nodes (12): ensureProgressCss(), estimateRemainingSec(), fmtDuration(), notifyDone(), pass3Stats(), PURSON_STEPS, qt_runPurson(), renderPagesToPngBlobs() (+4 more)

### Community 64 - "🚀 Quick Start — 5 Minutes to First Annotation"
Cohesion: 0.15
Nodes (13): Check Your Work, File Organization, Full Example, Next: Batch Processing, 🚀 Quick Start — 5 Minutes to First Annotation, Step 0: Prerequisites, Step 1: Get PDFs Ready, Step 2: Rasterize (1 minute) (+5 more)

### Community 65 - "[Afternoon/evening] Makham (working together with Claude Code — moved to starting house #2 instead of #6)"
Cohesion: 0.15
Nodes (12): 1. Element ordering direction reversed: **vertical before horizontal** (had been written the wrong direction the first time), 1. Went through and fixed the grid_ref format convention in 12 files, 2. Added 7 more missing beams + fixed B4X 3'/3'' back to correct, 2. Found the same additional_bars wrong-side bug again (exactly like house 1) — pages 25/28, 3. Found a real mislabel in หน้า26_tie_beam_plan.json (RB1A that's actually RB1), 3. Synced page20 + page21 to match page19 (same mark/spec), 4. Page22 — rejected incorrect advice from an external AI, 4. Page29_column_schedule — confirmed the column rule uses a single main_bar.count (answering the open question from house 1) (+4 more)

### Community 66 - "บันทึกการแก้ไข"
Cohesion: 0.17
Nodes (11): 01บ้าน_เล็ก_1ชั้น_01, 02บ้าน_เล็ก_1ชั้น_02, 03บ้าน_เล็ก_2ชั้น_01 และ 04บ้าน_เล็ก_2ชั้น_02, 05บ้าน_เล็ก_2ชั้น_03, 06-11 (บ้าน_ใหญ่_1ชั้น_01, บ้าน_ใหญ่_2ชั้น_01, บ้าน_เล็ก_1ชั้น_03/04/05/06), 2026-08-24 — schema-normalize ทุกหลัง (Claude, ภายใต้ att1235 ระหว่างมะขามออกไปข้างนอก), 2026-08-25 — normalize ทั้ง 2 tree ให้ตรงสเปกปัจจุบัน + อัปเกรด checker (Claude, att1235), Convention (+3 more)

### Community 67 - "manifest.json"
Cohesion: 0.17
Nodes (11): datasets, focus, phase, processing_log, project, scope, stats, annotated_datasets (+3 more)

### Community 68 - "qwen-processor.js"
Cohesion: 0.24
Nodes (11): buildQwenPayload(), callQwenAPI(), fs, listPendingRecords(), main(), MANIFEST_FILE, path, PROCESSING_DIR (+3 more)

### Community 69 - "extract_houses_local.py"
Cohesion: 0.36
Nodes (11): call_model(), classify_page(), discover_pages(), extract_page(), image_data_uri(), log(), main(), หมายเลขหน้าจริงจากชื่อไฟล์ png (กัน gap ในลำดับ ไม่เดาว่าต่อเนื่อง 1..N). (+3 more)

### Community 70 - "WORKFLOW สำหรับ intern — เดินบ้าน 1 หลังผ่านสายพาน t04 Purson"
Cohesion: 0.17
Nodes (12): WORKFLOW สำหรับ intern — เดินบ้าน 1 หลังผ่านสายพาน t04 Purson, ⛔ กฎเหล็กก่อนแตะอะไร (อ่าน 1 นาที ประหยัดหายนะ 1 คืน), ข้อ 1 — Pass 0: คัดหน้า (VLM + OCR ช่วย, ยังไม่มีสคริปต์ยิงจริง), ข้อ 2 — Pass 1: จัดของ (โค้ดล้วน CPU), ข้อ 3 — Pass 1.5: ตา CV (CPU), ข้อ 4 — Pass 2/2.4: ยิงโมเดล (GPU — ตาม RUNBOOK เท่านั้น), ข้อ 5 — Pass 2.5: self-harvest (CPU), ข้อ 6.5 — Fine-tune จริง (train_t03.py) + k-fold CV (+4 more)

### Community 71 - "2026-08-02"
Cohesion: 0.17
Nodes (11): 2026-08-02, Claude — session with Makham (afternoon, round 2), Claude — session with Makham (afternoon, round 3), Claude — session with Makham (evening, round 4), Claude — session with Makham (evening, round 5 — independent fable audit), Claude — session with Makham (midday), Claude — session with Makham (night, round 6 — Label Studio cancelled), Claude — session with Makham (night, round 7 — folder rename) (+3 more)

### Community 72 - "ตอนที่ 2 (2026-07-24) — วันนี้ทำอะไร "ก่อน" เช่าการ์ดจอ ทำไมต้องทำขนาดนี้"
Cohesion: 0.17
Nodes (12): 1. ทำไมวันนี้ต้องเสียเวลาเช็คตั้งเยอะ ทั้งที่ยังไม่ได้เช่าอะไรเลย, 2. 0.1 — ทดสอบกุญแจ HuggingFace ก่อนใช้จริง, 3. 0.2 — เช็คเงินในบัญชี Vast.ai + จุดที่เกือบพลาดอีกรอบ, 5. 0.4 — อ่านสคริปต์ซ้ำจริงจัง เจอบั๊กที่ไม่เคยรู้มาก่อน, 6. 0.5 — เลือกเครื่องเช่าจริงจากรายการที่มีอยู่จริง, 6.5. llama.cpp คืออะไรกันแน่ — ทำไมไม่ใช้ Unsloth รันตอนใช้งานจริง, 7. สรุป: ทำครบ Phase 0 แล้ว พร้อมเช่าจริงหรือยัง, 8. คำศัพท์ใหม่วันนี้ (ต่อจากท้ายเล่มในตอนที่ 1) (+4 more)

### Community 73 - "pdf-processor.py"
Cohesion: 0.25
Nodes (10): analyze_pdf_content(), list_uploaded_pdfs(), process_batch(), process_pdf(), rasterize_pdf(), Main processing pipeline for a single PDF, List all PDFs in raw/ folder, Process all unprocessed PDFs in raw/ folder (+2 more)

### Community 74 - "Stage A — Page Classifier"
Cohesion: 0.18
Nodes (10): Batch Size Guide, Script: Build Payload (Node.js), Script: Convert to Label Studio Tasks (Node.js), Script: Match Stage B output → filename (Node.js), Script: Route Pages After Validation (Node.js), Script: Validate Output (Node.js), Stage A — Page Classifier, System Prompt (+2 more)

### Community 75 - "0. FORMAT LOCK — read this before anything else (added 2026-08-02)"
Cohesion: 0.18
Nodes (11): 0.10 Before you call a house finished, 0.1 The container — never invent an array name, 0.2 Every element carries these four, 0.3 `element_id` = the mark printed on the drawing, nothing else, 0.4 `element_type` — reuse, don't invent, 0.5 Dimensions are integer millimetres, 0.6 Rebar is always an object, never a string, 0.7 `printed_as` — keep the drawing's own words (+3 more)

### Community 76 - "organize.py"
Cohesion: 0.27
Nodes (10): binarize(), cut_views(), find_dividers(), main(), ตัดหน้าเป็นรูปละ view ตามคำบอกตำแหน่งจาก pass 0     คืน (list ของ box (x0,y0,x1, อ่านรูปเป็นขาวดำ (255 = มีหมึก) — รองรับ path ภาษาไทยด้วย np.fromfile, ตัดแถบ title block ทางขวาออก (ชุดแบบราชการมีทุกแผ่น) — หาเส้นตั้งเข้มในโซนขวา, หาเส้นแบ่ง n_parts-1 เส้นในช่วง [lo, hi) ตามแกนที่ระบุ     axis 0 = แบ่งตามแนวน (+2 more)

### Community 77 - "PROMPT START"
Cohesion: 0.18
Nodes (9): `bbs_schedule` specifically, Elements, pass4 extract.md — the patterns nothing reads yet (เดิมเรียก pass 3 — renumbered 2026-08-26, ดู pass_design_v2.md), PROMPT END, PROMPT START, `side_profile` specifically, `site_plan` specifically, The rules that matter most here (+1 more)

### Community 78 - "วิจัย: ใช้ Qwen grounding (pixel/bbox) เทียบกับ gridmaster เพื่อตรวจสอบคาน"
Cohesion: 0.18
Nodes (10): Sources, ข้อเสนอที่ใช้ได้จริงกับสิ่งที่มะขามต้องการ — "ดูบีมเทียบ gridmaster", งานวิจัยในโดเมนแบบก่อสร้าง/วิศวกรรมโดยตรง — ยืนยันทิศทาง t03 ว่าถูกทาง, ปัญหาการนับที่เจอ (บ้าน09 หน้า26: 48 คานจริง เหลือ 2) ไม่ใช่เรื่องแปลก — มีงานวิจัยรองรับ, รูปแบบ output ของ Qwen3-VL grounding, วิจัย: ใช้ Qwen grounding (pixel/bbox) เทียบกับ gridmaster เพื่อตรวจสอบคาน, สิ่งที่ยังไม่ยืนยัน — ต้องทดสอบจริงก่อนเชื่อ, เทคนิคที่ตรงประเด็นที่สุด — GroundCount (ผสม detection model เข้ากับ VLM) (+2 more)

### Community 79 - "🚨 คู่มือฉุกเฉิน Purson — ใช้ตอนคุยกับ Claude ไม่ได้"
Cohesion: 0.18
Nodes (10): 1️⃣ เช็คว่าเทรนถึงไหนแล้ว, 2️⃣ ถ้าเทรนพัง (OOM / error), 3️⃣ เทรนเสร็จแล้ว — ต้องทำอะไร (⚠️ สำคัญที่สุด), 4️⃣ 💰 คืนการ์ด (ทำเมื่อมั่นใจว่าไฟล์ปลอดภัยแล้วเท่านั้น), 5️⃣ เช็คเงิน, 6️⃣ ค่าที่ใช้อยู่ (ไว้อ้างอิงตอนต้องตัดสินใจ), 7️⃣ ขั้นถัดไปหลังได้ adapter ครบ 4 ตัว (ไม่ต้องรีบ ทำทีหลังได้), 🚨 คู่มือฉุกเฉิน Purson — ใช้ตอนคุยกับ Claude ไม่ได้ (+2 more)

### Community 80 - "t04_Purson/README.md"
Cohesion: 0.25
Nodes (4): `{{ELEMENT_ACCOUNT}}` — รูปแบบบัญชีที่ป้อนเข้า prompt, Pass 3 — ถอดระยะ/เหล็ก จากบัญชี element ที่ยืนยันแล้ว, PROMPT END, PROMPT START

### Community 81 - "destrier_test_house/op04_score.py"
Cohesion: 0.35
Nodes (10): elements_of(), main(), mark_base(), norm_id(), norm_ref(), F4,C1" → "f4" — mark ในแบบพิมพ์ติดกันเป็นคู่ (ฐานราก,เสา) แต่ธรรมเนียม GT     แ, 1-A" / "A-1" / "A1" / "a 1" → ("A","1") — ตัวอักษรขึ้นก่อนเสมอ, score_page() (+2 more)

### Community 82 - "proof/op04_score.py"
Cohesion: 0.35
Nodes (10): elements_of(), main(), mark_base(), norm_id(), norm_ref(), F4,C1" → "f4" — mark ในแบบพิมพ์ติดกันเป็นคู่ (ฐานราก,เสา) แต่ธรรมเนียม GT     แ, 1-A" / "A-1" / "A1" / "a 1" → ("A","1") — ตัวอักษรขึ้นก่อนเสมอ, score_page() (+2 more)

### Community 83 - "03บ้าน_เล็ก_2ชั้น_01 (รอบตรวจภาพต้นฉบับ 2026-07-20)"
Cohesion: 0.18
Nodes (11): 03บ้าน_เล็ก_2ชั้น_01 (รอบตรวจภาพต้นฉบับ 2026-07-20), 38. ⚠️ ต้องให้มะขามตัดสิน: คานตะวันออกช่องบันได ชั้น1 กับ ชั้น2 ไม่ตรงกัน 0.29 m, 39. ถอนคำ: ค่าที่วัดได้เรื่อง `2'` เมื่อ 2026-07-19 ผิดเอง, 40. หน้า31 + หน้า32 ตรวจภาพต้นฉบับเต็มแผ่น — เจอของหายและ label ผิดเพียบ, 41. ค้าง (ยังไม่แตะ), 42. บ้าน3 หน้าอื่นที่รับผลจากการแก้ B'(10.2→10.1): หน้า00 + หน้า32 ปรับตามแล้ว, 43. หน้า31: ลบ 2 element ตามคำสั่งมะขาม (ส่วนต่อขยายแถว E ฝั่งตะวันตก/ตะวันออก), 44. หน้า33 (S-06 คานอะเส) ตรวจภาพต้นฉบับเต็มแผ่นแบบเดียวกับหน้า31/32 — 17→23 element (+3 more)

### Community 84 - "64. ตรวจอิสระรอบ fable — "ทุกอย่างเป็น pattern เดียวกันไหม?" คำตอบตอนเริ่ม: ยัง / คำตอบตอนจบ: ใช่ (2026-08-02)"
Cohesion: 0.18
Nodes (11): 59. บ้าน 41 (บ้าน_เล็ก_2ชั้น_17) — แถว dummy แกน y ผิดทั้งชุด: `A'` ย้าย 1.60 → **-1.10** + เพิ่ม `A''`=0.80, `A'''`=2.00, 60. บ้าน 42 (บ้าน_เล็ก_2ชั้น_18) — ตรวจคาน: ยืนยัน "ไม่มีผังคาน" จริง + หน้า18 ผิด 2 กลุ่ม (คานหาย 4, ผูกช่วงผิด 2), 61. บ้าน 43 (บ้าน_เล็ก_2ชั้น_19) — ผังคาน 2 แผ่น: เพิ่ม dummy 7 เส้น, คานหาย 6, ผูกแถวผิด 4, 62. บ้าน 44 (บ้าน_เล็ก_2ชั้น_20) — หน้า18 คานชั้นล่าง: เพิ่ม dummy x 2 เส้น, ปลด `~` ได้ 3 ตัว, ลบคานที่ไม่มีจริง 1, 63. บ้าน 45 (บ้าน_ใหญ่_1ชั้น_02) หน้า28 ผังคาน — เจอความผิดพลาดเชิงระบบ 2 เรื่อง + คานหาย 4, 64. ตรวจอิสระรอบ fable — "ทุกอย่างเป็น pattern เดียวกันไหม?" คำตอบตอนเริ่ม: ยัง / คำตอบตอนจบ: ใช่ (2026-08-02), ของที่เจอและแก้ (เก็บของเดิมใน `*_printed_as`/flag ทุกจุด), ผลจบ (+3 more)

### Community 85 - "[Morning] Makham (working together with Claude Code — continuing house #2's review, see `2026-07-15.md`)"
Cohesion: 0.18
Nodes (10): 1. Added 6 dummy grids to house 2's grid master (`หน้า00_gridline.json`), 2. Cascaded fixes to related pages (checked against the image before every fix), 3. Found an unrelated pre-existing issue — not fixed, just flagged, 4. Points decided "not to cascade" due to insufficient evidence, 5. Translated the entire `สิ่งที่ต้องแก้.md` file into English, [Afternoon-evening] Makham (working together with Claude Code — starting houses #3 and #4 in full), [Evening] Makham — going back to catch up on house 2: cascading the new dummy grids into pages 05/06/07, House 3 (บ้าน_เล็ก_2ชั้น_01) (+2 more)

### Community 86 - "Claude — continuing from the entry above: rented a real GPU + full training + full export cycle, this round finished successfully (Phase 1-10)"
Cohesion: 0.18
Nodes (10): AI retune — Phase 0 (`tune_ai/t01/data_before_tune/`, see `RETUNE_WORKFLOW.md` + `2026-07-24(teach mk).md` for detail/explanation), Claude — continuing from the entry above: rented a real GPU + full training + full export cycle, this round finished successfully (Phase 1-10), Claude — house05 grid/beam plan continuing from 2026-07-21.md, then on to AI retune Phase 0 (repo Constistant), House05 (`json_แก้ไขแล้ว/05บ้าน_เล็ก_2ชั้น_03/`), Phase 10: downloaded to Makham's computer + real run test — hit near-full RAM, Phase 1-4: rent+connect+upload+verify — all passed, no problems, Phase 5-6: full 3-epoch training succeeded — found a new "process hangs holding VRAM" bug, Phase 7: real measurement — much better than the previous round (after fixing the reasoning-mode bug) (+2 more)

### Community 87 - "[morning–afternoon] Claude — session with Makham"
Cohesion: 0.18
Nodes (10): 1. Checked house 07's grid master + all plans (Fable, opening the real images and zooming on every point), 2026-07-28, 2. Tried the tuned t01 model on house 01 → `tune_ai/t01/ผล/`, 3. Set up t02 — comparing Qwen3-VL against Qwen3.6 (Makham's instruction), 4. t02's Phase 0 — checked for real (afternoon), 5. Phase 0 fully closed, 0.1-0.6 (evening — Makham said "finish it and tick it off"), 6. Rented the real machine, ran Phase 1-7.5 in full + found a bug that reinterprets the whole day's results, 7. Phase 8 (export GGUF) — failed at the sanity check, diagnosed down to tensor level and confirmed to be a genuine tooling bug (+2 more)

### Community 88 - "Supported Models"
Cohesion: 0.20
Nodes (9): ASR Models (`task: asr`, Whisper — v0.71.32), Optional Extras, Quick Size Guide, Quoting the extra, Recommended Models, Supported Models, Supported Models & Optional Extras, The extras table (+1 more)

### Community 89 - "ARCHIVE.md"
Cohesion: 0.20
Nodes (5): AGENTS.md — No_touch_box/, File naming (recommended), How to use, Note, 📥 Raw PDF Upload Folder

### Community 90 - "check_house"
Cohesion: 0.29
Nodes (7): check_house(), load_grid(), main(), walk(), gt_of(), คืน {subtask: (total_ids, printed_ids, [ตัวอย่างที่คนตั้งเอง])}, scan()

### Community 91 - "ทดลองถอดแบบบ้าน 01/03/04 ด้วย t02 (LoRA adapter, ไม่ใช่ tuning round ใหม่)"
Cohesion: 0.20
Nodes (9): Phase 0 — Pre-flight (ทำก่อนเช่าอะไรทั้งนั้น, $0), Phase 1 — เช่าเครื่อง, Phase 2 — ทดสอบสั้นก่อนเสมอ (ห้ามข้าม — เป็นด่านเดียวที่กันเสียเงินทั้งก้อนถ้าอะไรพัง), Phase 3 — รันเต็ม 3 บ้าน, Phase 4 — ดาวน์โหลดผลลัพธ์ + ⛔ คำเตือนก่อน destroy, Phase 5 — (ทางเลือก, ไม่ทำตอนนี้) เทียบผลกับ ground truth ที่แก้แล้ว, ทดลองถอดแบบบ้าน 01/03/04 ด้วย t02 (LoRA adapter, ไม่ใช่ tuning round ใหม่), ⚠️ สิ่งที่ต้องรู้ก่อนอ่านผล — คำเตือนสำคัญที่สุดของเอกสารนี้ (+1 more)

### Community 92 - "ทดลองถอดแบบบ้าน 08/09/10/11 ด้วย t02 (LoRA adapter, ไม่ใช่ tuning round ใหม่)"
Cohesion: 0.20
Nodes (9): Phase 0 — Pre-flight (ทำก่อนเช่าอะไรทั้งนั้น, $0), Phase 1 — เช่าเครื่อง, Phase 2 — ทดสอบสั้นก่อนเสมอ (ห้ามข้าม — ด่านเดียวที่กันเสียเงินทั้งก้อนถ้าอะไรพัง), Phase 3 — รันเต็ม, Phase 4 — ดาวน์โหลดผลลัพธ์ + ⛔ คำเตือนก่อน destroy, Phase 5 — (ทางเลือก, ไม่ทำตอนนี้) เทียบผลกับ ground truth ที่แก้แล้ว, ✅ ทำไมรอบนี้เป็นการทดสอบที่ยุติธรรมกว่ารอบ 01/03/04, ทดลองถอดแบบบ้าน 08/09/10/11 ด้วย t02 (LoRA adapter, ไม่ใช่ tuning round ใหม่) (+1 more)

### Community 93 - "t05_Courser/pass0_material_list_batch.py"
Cohesion: 0.33
Nodes (9): bare(), build_label(), find_pages(), main(), page_key(), หา (house, page) ที่มีไฟล์ GT pattern=material_list พอดี 2 ไฟล์ และเป็นไฟล์ทั้งห, คืน label หรือ None ถ้าเลขแผ่นอ่านไม่ได้/ซ้ำ (ไม่เดา — ปล่อยเข้าคิวมือ), read_jsonl() (+1 more)

### Community 94 - "go.py"
Cohesion: 0.42
Nodes (9): current_instance(), do_start(), do_stop(), main(), pick_model(), เรียก presentation.py — cwd ล็อกที่โฟลเดอร์นี้เสมอ ไม่ว่าจะถูกเรียกจากไหน, id ของการ์ดที่เปิดอยู่ **จริง** (None ถ้าไม่มี)      เช็คกับ vast.ai เสมอ ไม่เ, เลือกรุ่นโมเดล — destrier เป็นค่าเริ่มต้น (รุ่นที่ทีมใช้อยู่จริงตอนนี้)      เ (+1 more)

### Community 95 - "serve_purson.py"
Cohesion: 0.29
Nodes (7): build_grammar(), _Deadline, generate(), load(), main(), make_app(), xgrammar builtin JSON — คืน factory (LogitsProcessor มี state ต้องสร้างใหม่ทุกคร

### Community 96 - "training/pass0_material_list_batch.py"
Cohesion: 0.33
Nodes (9): bare(), build_label(), find_pages(), main(), page_key(), หา (house, page) ที่มีไฟล์ GT pattern=material_list พอดี 2 ไฟล์ และเป็นไฟล์ทั้งห, คืน label หรือ None ถ้าเลขแผ่นอ่านไม่ได้/ซ้ำ (ไม่เดา — ปล่อยเข้าคิวมือ), read_jsonl() (+1 more)

### Community 97 - "[Continuing from the July 7 session] Makham (working together with Claude Code — same session, crossing midnight)"
Cohesion: 0.20
Nodes (9): 1. Diagnosed the "issue loading URL from $image value" problem, 2. Answered knowledge questions about all the patterns, 3. Created a new draft file `20260708draft of prime rawjson.md`, 4. Attempted a token-cheap "migration" first → cancelled, 5. Full fresh re-extraction (a genuine fresh extraction this time) → t4, 6. Prepared Label Studio to work with the t4 data → found a real, long-hidden bug (also affecting t3), 7. Verified that image filenames in the raw JSON match what's actually shown in the UI, [Continuing from the July 7 session] Makham (working together with Claude Code — same session, crossing midnight) (+1 more)

### Community 98 - "[Morning-afternoon] Makham (working together with Claude Code — continuing from the July 12 session, see `2026-07-12.md`)"
Cohesion: 0.20
Nodes (9): 1. Confirmed scope: `json_แก้ไขแล้ว\` doesn't fall under `rule_of_tune.md` rule 1, 1. Surveyed pages + created the grid master + personally read the structural section S-01 through S-19 (pages 29-47, 20 files including the grid master), 2. Dispatched 5 background agents for the remaining sections (architectural, sanitary, electrical+mechanical, spread-footing BOQ, pile-foundation BOQ+back-of-book references), 2. Reviewed and fixed dummy grid `3'` for house #1 (บ้าน_เล็ก_1ชั้น_01) — found an error inherited all the way from the t3/t4 rounds, 3. Repaired the 4 agents' unfinished work personally (instead of re-dispatching) — continued across a compaction with the command "Continue from where you left off" / "keep going", 3. Self-correction on rule 2, 4. Validated + ran the label-studio script, [Evening] Makham (continuing from this same morning-afternoon — new task: starting to use the `json_แก้ไขแล้ว\` (json_corrected\) folder for reviewing/fixing house #1) (+1 more)

### Community 99 - "[00:30–03:30] Claude — session with Makham (continuing from the night of the 28th)"
Cohesion: 0.20
Nodes (9): [00:30–03:30] Claude — session with Makham (continuing from the night of the 28th), 1. Continued the house 01 extraction run — got 4 new pages, then stopped as ordered, 2026-07-29, 2. ⛔ The results really are unusable — all 6 pages checked against ground truth, 3. ★★ The most likely cause — **the LoRA may not be in t01's GGUF at all**, 4. Two secondary causes (real, but not the main one), 5. ⚠️ Caveats when interpreting tonight's results, 6. Real speed numbers (measured from the log) (+1 more)

### Community 100 - "ตอนที่ 3 (2026-07-28) — วันนี้ t02 ลงมือเช่าจริง เกิดอะไรขึ้นบ้าง"
Cohesion: 0.20
Nodes (10): 1. ทบทวน: t02 ตอบคำถามอะไร, 3. อ่านกราฟ loss ตอนเทรน — loss คืออะไร บอกอะไรเรา, 4. VRAM ขึ้นๆ ลงๆ ระหว่างเทรน — ทำไม, 5. ทำไม Qwen3-VL ช้ากว่า Qwen3.6 ถึง 2.9 เท่า ทั้งที่ตั้งค่าเหมือนกันหมด, 6. ผลจริงของ Phase 7 — t02 แพ้ t01 ทุกตัวชี้วัด, 7. ทำไม Phase 7.5 ต้องโหลดโมเดลใหม่ทั้งก้อน — LoRA adapter คืออะไรกันแน่, 8. คำศัพท์ใหม่วันนี้ (ต่อจากท้ายเล่มในตอนที่ 2), ตอนที่ 3 (2026-07-28) — วันนี้ t02 ลงมือเช่าจริง เกิดอะไรขึ้นบ้าง (+2 more)

### Community 101 - "Stage B2 — Spec / Notes Reader"
Cohesion: 0.22
Nodes (8): Stage B2 — Spec / Notes Reader, System Prompt, User Prompt (NOTES_PROMPT), การใช้ผลลัพธ์ (สำหรับคน wire pipeline), ⚠️ บทเรียนจาก research, วัตถุประสงค์, สถานะ, หลักการทำงานจริง

### Community 102 - "t02 dataset provenance — byte-identical copy of t01, deliberately NOT rebuilt"
Cohesion: 0.22
Nodes (6): ⚠️ Do NOT re-run `build_dataset.js` for t02, Rule compliance, t02 dataset provenance — byte-identical copy of t01, deliberately NOT rebuilt, The dataset being used (from the inherited `stats.json`), Verification (run 2026-07-28, all passed), What was done

### Community 103 - "Pass 0 — Page Classifier (t03)"
Cohesion: 0.22
Nodes (9): Confidence discipline (per schema §0.2 + Constistant's `QT_CONFIDENCE_POLICY`), Disambiguation rules — read before answering (schema §0.9, §1), Pass 0 — Page Classifier (t03), Pattern taxonomy — the 16 categories (verbatim from schema §1), System Prompt, User Prompt Template, ต่างจาก production Pass 0 ตรงไหน, ยังไม่ตัดสินใจ / ยังไม่ทำ (สถานะจริง ไม่ใช่ของที่ทำเสร็จแล้ว) (+1 more)

### Community 104 - "PROMPT START"
Cohesion: 0.22
Nodes (8): Choosing `subtask`, Fields, Pass 0 — page classification, PROMPT END, PROMPT START, Rules, Two traps that have already cost real data, `views[]` — the unit of work is a view, not a page

### Community 105 - "PROMPT START"
Cohesion: 0.22
Nodes (8): `bbs_schedule` specifically, Elements, pass3.md — the patterns nothing reads yet, PROMPT END, PROMPT START, `side_profile` specifically, `site_plan` specifically, The rules that matter most here

### Community 106 - "RUNBOOK — ยิง t04 Purson จริงครั้งแรก (เขียน 2026-08-28 สำหรับคืนนี้)"
Cohesion: 0.22
Nodes (9): RUNBOOK — ยิง t04 Purson จริงครั้งแรก (เขียน 2026-08-28 สำหรับคืนนี้), ข้อ 1 — Pass 1.5: CV สแกนหน้า plan ของ 5 บ้าน val (CPU, ไม่ใช้ GPU), ข้อ 2 — เช่า GPU (Vast) — กติกาเดิมที่เคยตกลงกัน, ข้อ 3 — การทดลอง 3 แขน (GPU) — หัวใจของคืนนี้, ข้อ 4 — อ่านผล ตัดสินด้วยเลข, ข้อ 5 — Pass 3 (ทำต่อเมื่อข้อ 4 ได้ผู้ชนะแล้วเท่านั้น), งานคลัง template ที่เหลือ (อัปเดตหลังรอบเติม 2026-08-28 ค่ำ), ถ้าคืนนี้มีเวลาแค่ครึ่งเดียว (+1 more)

### Community 107 - "05บ้าน_เล็ก_2ชั้น_03 (รอบ F=0 re-origin + item 48, 2026-07-24)"
Cohesion: 0.22
Nodes (9): 05บ้าน_เล็ก_2ชั้น_03 (รอบ F=0 re-origin + item 48, 2026-07-24), 51. Grid master — ตัดสิน axis-origin: re-base เป็น F=0 (ปิด flag ข้อ 35) + เพิ่ม dummy 7 เส้น, 52. Cascade F=0 + Aprime→A' เข้า หน้า32/33 (beam plan ชั้น1/ชั้น2), 53. item 48 (merge duplicate element_id) — apply กับ footing plan หน้า30/31, 54. ค้าง (ยังไม่ทำสำหรับบ้าน 05), 55. ⚠️ พบว่า item 34-37 ที่บันทึกไว้ **ไม่ได้อยู่ในไฟล์จริง** — ต้องทำใหม่, 56. หน้า36 (S-08) แก้ additional_bars 4 จุด — **ยืนยันจากภาพต้นฉบับ ไม่ได้เชื่อ doc อย่างเดียว**, 57. หน้า32/33 — apply format บ้าน04 ครบทั้ง 4 อนุสัญญา (item 9/14/19/25/30) (+1 more)

### Community 108 - "[17:13] Makham (working together with Claude Code — continuing from the July 10 session, see `2026-07-10.md`)"
Cohesion: 0.22
Nodes (8): [17:13] Makham (working together with Claude Code — continuing from the July 10 session, see `2026-07-10.md`), [17:29] Makham (working together with Claude Code — continuing the same day, closing out pending item 1 above), 1. Surveyed house #3's document structure, 2. Created the grid master — found real dummy grids for the first time since starting op1, 3. Personally read the entire structural section S-01 through S-18 (pages 28-45, 18 sheets + grid master = 19 files), 4. Released 5 background agents simultaneously for the remaining sections, 5. Repaired the unfinished work personally (instead of re-dispatching a new agent, which would hit the same session limit), 6. Validated + ran the label-studio script

### Community 109 - "[Continuing all day] Makham (working together with Claude Code — continuing house #1's review/fixes started on 2026-07-13, see `2026-07-13.md`)"
Cohesion: 0.22
Nodes (8): 1. Added dummy grids that had been missed before, 2. New convention: vertical axis (row) comes before horizontal axis (column) in range-type `grid_ref`, 3. New convention: point-type `grid_ref` doesn't use a dash — dashes are reserved for line/area ranges only, 4. Removed an irrelevant element + removed a duplicated grid, 5. Recorded the lesson "citing a rule but not actually stopping to ask" into `rule_of_tune.md` (new rule 9), 6. Checked whether architecture-level data (finishing materials, door/window schedule) extracted so far is used anywhere in the Constistant app, 7. `หน้า19_view2_beam_plan.json` — reordered elements[] to match reading order + split the duplicated spec out into `specs{}`, [Continuing all day] Makham (working together with Claude Code — continuing house #1's review/fixes started on 2026-07-13, see `2026-07-13.md`)

### Community 110 - "สอนมะขาม_รวม.md"
Cohesion: 0.22
Nodes (8): A.1 เอกสารประจำรอบ (ระดับโฟลเดอร์ `t01/`), A.2 `data_before_tune/` — ชุดข้อมูลเทรน + สคริปต์เทรนบนเครื่องเช่า, A.3 `ผล/` — ผลลัพธ์การถอดแบบบ้าน_เล็ก_1ชั้น_01 จริง (จาก `extract_house01_local.py`), A.4 `ai_output_บ้าน_ใหญ่_1ชั้น_01/` — ผลทดสอบ smoketest แยกต่างหาก, B.1 Phase A — `CLASSIFY_PROMPT` (สแกนไว ถามแค่ pattern ของแต่ละ view), B.2 Phase B — `PROMPT_SHORT` (ถอดเต็ม — ตัวเดียวกับที่ใช้สอนตอนเทรน), ภาคผนวก A — ไฟล์ทุกไฟล์ใน `tune_ai/t01/` ทำหน้าที่อะไรบ้าง, ภาคผนวก B — prompt จริงที่ส่งไปหา Qwen (t01)

### Community 111 - "op04 — extract one house, Pass 2 subtasks only"
Cohesion: 0.25
Nodes (7): Deliberately skipped, Finishing — same gate as op01, one addition, op04 — extract one house, Pass 2 subtasks only, Scope — what op04 extracts, The one extra step op01 does not have — `_scope.json`, When to use op01 instead, Why this exists — the measured reason, not a preference

### Community 113 - "qwen-api-helper.js"
Cohesion: 0.32
Nodes (6): callQwenAPINative(), callQwenDirect(), callQwenViaSupabase(), fs, https, path

### Community 114 - "Primary Raw JSON Schema — Edit Log"
Cohesion: 0.25
Nodes (8): 2026-08-25 — §0.2: unmarked elements now take `element_id: null` + `element_name_assigned`, 2026-08-28 (6) — §1 plan family: four classification traps recorded, 2026-08-28 (7) — §0.4 / §6a element_type contradiction closed: purlin/truss added, 2026-08-29 — §1 stale claim corrected: pass 2 prompt already teaches the plan-family split, 2026-08-29 — §4 span rule amended + `scaled_from_grid` added to `span_source` (Makham's order), Primary Raw JSON Schema — Edit Log, รายการแก้ไข, วิธีเพิ่มแถวใหม่

### Community 115 - "ocr_titleblock"
Cohesion: 0.43
Nodes (7): crop_titleblock(), get_reader(), main(), ocr_titleblock(), img: PIL.Image หน้าเต็ม -> PIL.Image ครอปมุมกรอบชื่อแบบ ขยาย+ปรับ contrast แล้ว, คืน (hint_text, raw_lines) — hint_text ว่างถ้า OCR ไม่เจออะไรจริงจัง, write_hint()

### Community 116 - "tune_ai/soup_safetensors.py"
Cohesion: 0.39
Nodes (7): convert_expert_pair(), diagnose(), expert_delta_e0(), main(), ΔW ของ expert ตัวแรก ตาม peft ParamWrapper.get_delta_weight        A (E·r, X) →, สลับข้างการแยกตัวประกอบของชั้น MoE ให้ตรงอีก convention หนึ่งของ peft — **ไม่เสี, เช็คว่าพจน์ไขว้ไม่ได้กลบของจริง: ‖ΔW_รวม‖ ควรใกล้ ‖ค่าเฉลี่ย ΔW‖        ตรวจทั้

### Community 117 - "Phase 0 — เตรียมบนเครื่องตัวเอง ก่อนเช่าอะไรทั้งนั้น ($0)"
Cohesion: 0.25
Nodes (8): 0.1 — HuggingFace token ✅ ผ่าน (มะขามยืนยัน 2026-07-28), 0.2 — Vast.ai ✅ เครดิตผ่าน (มะขามยืนยัน 2026-07-28) — ข้อ 3/4 ยังต้องทำตอนกด Rent, 0.3 — dataset ต้องตรงกับ t01 ทุก byte ✅ ผ่าน (ตรวจ 2 รอบ, มะขามสั่งตรวจ 2026-07-28), 0.5 — ยืนยันว่าของที่จะใช้มีอยู่จริง ✅ ผ่าน (ตรวจสดถึงระดับไบนารี+config, มะขามสั่งทำ+ติ๊ก 2026-07-28), 0.6 — ขนาดเครื่องที่จะเช่า ✅ ตัดสินแล้ว (มะขามสั่งทำ+ติ๊ก 2026-07-28), Phase 0 — เตรียมบนเครื่องตัวเอง ก่อนเช่าอะไรทั้งนั้น ($0), คำตัดสิน 0.6, ตรวจซ้ำรอบสอง 2026-07-28 — ยืนยันถึงระดับไบนารีและ config จริง

### Community 118 - "pull_and_verify_t03.py"
Cohesion: 0.46
Nodes (7): local_sha(), main(), คืน {relative_path: size} ของไฟล์ทั้งหมดใต้ d (ว่าง = ไม่มีโฟลเดอร์นั้น), sha256 ของทุกไฟล์ใต้ d — ขนาดตรงกันยังพลาดได้ (ไฟล์เสียระหว่างโอนโดยขนาดเท่าเดิม, remote_listing(), remote_sha(), sh()

### Community 119 - "Pass 2.4 - prompt ประกอบเสร็จ ของจริง ทั้ง 3 แขน (อ่านไฟล์นี้ไฟล์เดียวเข้าใจทั้ง pass)"
Cohesion: 0.25
Nodes (8): Pass 2.4 - prompt ประกอบเสร็จ ของจริง ทั้ง 3 แขน (อ่านไฟล์นี้ไฟล์เดียวเข้าใจทั้ง pass), จะรู้ได้ไงว่าแขนไหนชนะ (ตัดสินด้วยเลข ไม่ใช่ความรู้สึก), ผลลัพธ์ที่เพิ่มจากเดิม: ฟิลด์ `cv_mark`, พาร์ทที่ 1 - ภาพ, พาร์ทที่ 2 - prompt pass 2 เดิม (ไม่แตะเลย), พาร์ทที่ 3 - hint ข้อความ (เฉพาะแขน 2.4a, โค้ดแปะต่อท้ายเอง), ภาพรวม 10 วินาที, สิ่งที่โค้ดรับประกันให้ (ไม่ต้องกลัวพัง)

### Community 120 - "t05_Courser/pass0_derive.py"
Cohesion: 0.46
Nodes (7): building_of(), elements_of(), has_grid_refs(), main(), page_key(), คืน list ของ view dict หรือ None ถ้า derive ไม่ได้ (เข้าคิวมือ), views_for()

### Community 121 - "t05_Courser/train_t05_courser.py"
Cohesion: 0.25
Nodes (4): load_split(), jsonl → PIL Image objects (Unsloth ต้องการ object ไม่ใช่ path)     คืน subtask_, xgrammar builtin JSON grammar — มะขามสั่ง 2026-08-24: หน้า beam plan ต้องแนบ xgr, setup_grammar()

### Community 122 - "merge_model/soup_safetensors.py"
Cohesion: 0.39
Nodes (7): convert_expert_pair(), diagnose(), expert_delta_e0(), main(), ΔW ของ expert ตัวแรก ตาม peft ParamWrapper.get_delta_weight        A (E·r, X) →, สลับข้างการแยกตัวประกอบของชั้น MoE ให้ตรงอีก convention หนึ่งของ peft — **ไม่เสี, เช็คว่าพจน์ไขว้ไม่ได้กลบของจริง: ‖ΔW_รวม‖ ควรใกล้ ‖ค่าเฉลี่ย ΔW‖        ตรวจทั้

### Community 123 - "training/pass0_derive.py"
Cohesion: 0.46
Nodes (7): building_of(), elements_of(), has_grid_refs(), main(), page_key(), คืน list ของ view dict หรือ None ถ้า derive ไม่ได้ (เข้าคิวมือ), views_for()

### Community 124 - "training/train_t05_courser.py"
Cohesion: 0.25
Nodes (4): load_split(), jsonl → PIL Image objects (Unsloth ต้องการ object ไม่ใช่ path)     คืน subtask_, xgrammar builtin JSON grammar — มะขามสั่ง 2026-08-24: หน้า beam plan ต้องแนบ xgr, setup_grammar()

### Community 125 - "Things To Fix"
Cohesion: 0.25
Nodes (7): 48. ⚠️ กฎ: element_id เดียวกันในแผ่นเดียวกัน = **1 entry เท่านั้น** (รวม count + grid_refs), 49. บ้าน04 หน้า31/32 — merge ตามกฎข้อ 48 (4 มาร์คต่อไฟล์), 50. ⚠️ กฎใหม่: เหล็กกลางที่เด่นชัด → `main_bar.middle` (ไม่ใช่ `additional_bars`), 59. ⚠️ ตรวจสอบความสอดคล้อง `primary_rawjson_schema.md` ↔ ไฟล์นี้ — เจอสเปคค้างหลังการตัดสินใจ 4 จุด แก้ครบแล้ว (2026-08-02), 62. สัญกรณ์ `grid_ref` ให้เหมือนกันทุกบ้าน — ปิดเรื่อง "เดี๋ยว C1 เดี๋ยว c-1" (2026-08-02), Things To Fix, กฎทั่วไป (ใช้ทุกบ้าน)

### Community 126 - "Claude — re-verified the entire workflow + prepared to shut down the instance + tried running the tuned model on a new house (repo Constistant)"
Cohesion: 0.25
Nodes (7): 1. Re-verify RETUNE_WORKFLOW Phase 0–10 (Makham ordered: "check everything from the start, tick them all off except 11"), 2. Preparing to shut down the instance — final hard-block check (Makham ordered: "check the net + Mark of shame one last time"), 3. Question: taking the tuned AI to do `บ้าน_ใหญ่_1ชั้น_01` into the raw json actually in use — "that'll work, right?", 4. A real local run on the big house (25 pages) — setup + smoke test + the same RAM problem as Phase 10, 5. Design: "split into 5 calls like Constistant but with primary_rawjson content" — trade-off analysis, 6. Question: in real use on the web (with no Claude), how does it tell which page is which file type?, Claude — re-verified the entire workflow + prepared to shut down the instance + tried running the tuned model on a new house (repo Constistant)

### Community 127 - "2026-08-21"
Cohesion: 0.25
Nodes (7): 2026-08-21, [after midnight, final task before shutdown] Claude — session with Makham, [afternoon] Claude — session with Makham, [continued] Claude — Qwen output exported into the platform, two live platform bugs found, Dataset sizing — ตอบคำถาม "ควรมีกี่หลัง" (ต่อจากด้านบน, ยังเซสชันเดียวกัน), Late addition — t03 folder reorganized (after midnight, still this session), [คืน → เช้า 2026-08-22] Claude — session with Makham

### Community 128 - "Raw JSON Data Log"
Cohesion: 0.29
Nodes (7): 2026-07-28 — บ้าน 07: Fable re-verification pass (grid master + pattern:plan ทั้ง 19 ไฟล์), 2026-08-25 — batch: section element_id convention (json_แก้ไขแล้ว/, 343 files), 2026-08-28 (2) — `json_แก้ไขแล้ว/` house folders renumbered 01–38 (contiguous), 2026-08-28 — batch: `json_แก้ไขแล้ว/` brought to full `primary_rawjson_schema.md` conformance (z axis + plan family + 4 hard fails), Raw JSON Data Log, รายการแก้ไข, วิธีเพิ่มแถวใหม่

### Community 129 - "package.json"
Cohesion: 0.29
Nodes (6): dependencies, @supabase/supabase-js, name, private, type, @supabase/supabase-js

### Community 130 - "4. Grid"
Cohesion: 0.29
Nodes (7): 4. Grid, Atomic segments (span elements) vs merged entries (point elements), Documenting genuine ambiguity in the grid master (optional, added 2026-08-09), Dummy grid, Element ordering within `elements[]`, 🔎 How to FIND dummy grids: the beam-endpoint rule (Makham, 2026-07-19), Master file

### Community 131 - "md_to_book_pdf.py"
Cohesion: 0.52
Nodes (6): absolutize_images(), append_to_book(), find_browser(), md_to_pdf(), Path, แปลง src ของรูปที่เขียนเป็น path สัมพัทธ์ ให้เป็น file:// เต็ม      จำเป็นเพรา

### Community 132 - "ผล Qwen t02 บ้าน 09 — ไฟล์สำหรับนำเข้า Constistant"
Cohesion: 0.29
Nodes (6): ข้อจำกัดที่เหลือ ระบุตรงๆ, ผล Qwen t02 บ้าน 09 — ไฟล์สำหรับนำเข้า Constistant, ผลจริงตอนนำเข้า (รันผ่าน adapter จริงแล้ว ไม่ใช่คาดเดา), วิธีใช้, สร้างใหม่ยังไง, ไฟล์มาจากไหน — อ่านก่อนใช้

### Community 133 - "Dataset sizing — ควรมีกี่หลัง และ annotate อะไรบ้าง"
Cohesion: 0.29
Nodes (6): Dataset sizing — ควรมีกี่หลัง และ annotate อะไรบ้าง, ตัวเลขที่ตอบว่าทำไมหน้า beam ถึงพัง, ⚠️ ปัญหาที่ต้องตัดสินใจก่อนวาง t03, วิธีนับซ้ำ, ⚠️ อย่า annotate ทุก pattern เท่ากัน — จุดที่ประหยัดได้จริง, เป้า

### Community 134 - "convert_split"
Cohesion: 0.48
Nodes (5): convert_row(), convert_split(), main(), messages[0].content = [image parts..., ONE text part] (ยืนยันโครงจริงจาก build_d, main()

### Community 135 - "measure_capacity.py"
Cohesion: 0.43
Nodes (6): load(), measure(), จำนวน visual token ของภาพ 1 ใบ หลังโดน cap (Qwen ย่อภาพให้พอดี cap โดยรักษาสัดส่, คืน (รายตัวอย่าง, สถิติภาพ) — ทุกตัวเลขคำนวณจากไฟล์ภาพจริง ไม่ได้ประมาณ, report(), visual_tokens()

### Community 136 - "t05 Courser (Destrier) — แผนที่โฟลเดอร์นี้"
Cohesion: 0.29
Nodes (6): t05 Courser (Destrier) — แผนที่โฟลเดอร์นี้, ลำดับสายงาน (pass0 → เทรนจริง), สคริปต์ที่รันบนเครื่องเช่า (remote เท่านั้น — path ฝัง `/workspace/...` ตรงๆ), เครื่องมือช่วยตรวจ (ใช้มือ ไม่ใช่ pipeline), เอกสารตัวเต็ม, โฟลเดอร์ผลลัพธ์ที่จัดไว้แล้ว

### Community 137 - "Inventory-first pass — pilot 4 หน้า (บ้าน_เล็ก_1ชั้น_01)"
Cohesion: 0.29
Nodes (6): Inventory-first pass — pilot 4 หน้า (บ้าน_เล็ก_1ชั้น_01), สรุปรวม 4 หน้า — มุมมอง completeness, หน้า 19 (S-02), หน้า 21 (S-04), หน้า 24 (S-07), หน้า 40 (BOQ)

### Community 138 - "02บ้าน_เล็ก_1ชั้น_02"
Cohesion: 0.29
Nodes (7): 02บ้าน_เล็ก_1ชั้น_02, 18. Grid_ref format convention (items 5 and 8) — applied across house 2, 19. `หน้า25_beam_plan.json` — found the additional_bars wrong-side-position bug (exactly like house 1 items 10-12), 20. `หน้า26_tie_beam_plan.json` — found a genuine mislabel (what was recorded as RB1A is actually RB1), 21. `หน้า29_column_schedule_stair_fin.json` — columns use a single main_bar.count (the rule left unconfirmed in house 1 item 16 → now confirmed this round), 22. Added `misc` pattern (item 13) — page71/72, 23. Grid master — added 6 more dummy grid lines (1', 1'', 3', 4', F', F'') + cascaded into pattern=plan pages

### Community 139 - "60. บ้าน 01-11: ตรวจ+ทำ pattern=plan / footing plan / grid master / section ให้เป็นรูปแบบเดียวกัน (2026-08-02)"
Cohesion: 0.29
Nodes (7): 60. บ้าน 01-11: ตรวจ+ทำ pattern=plan / footing plan / grid master / section ให้เป็นรูปแบบเดียวกัน (2026-08-02), (ก) pattern นอกสเปค — บ้าน 07 เป็นบ้านเดียวที่ผิด (21 ไฟล์), (ข) grid master ซ้อนไม่เหมือนกัน — แก้ 7 ไฟล์, (ค) footing: กฎ item 48 ไปไม่ถึงบ้าน 06-11 — แก้ 11 ไฟล์, (ง) ⚠️ บ้าน 10/11 เก็บ `main_bar`/`stirrup` เป็น **string ล้วน** — แก้ 65 ค่า, ⚠️ ที่ยังไม่ได้แก้ (ตั้งใจ ไม่ใช่ลืม — ต้องอ่านแบบจริง ห้ามให้สคริปต์เดา), ผลลัพธ์รวม — scorecard ทั้ง 11 บ้าน

### Community 140 - "61. Apply สิ่งที่ต้องแก้.md ให้ครบบ้าน 01-11 — รอบที่ 2 (2026-08-02)"
Cohesion: 0.29
Nodes (7): 61. Apply สิ่งที่ต้องแก้.md ให้ครบบ้าน 01-11 — รอบที่ 2 (2026-08-02), Scorecard สุดท้าย — ทั้ง 11 บ้าน, (ก) บ้าน 10/11: พับ array เฉพาะกิจเข้า `elements[]` — 30 ไฟล์, (ข) บ้าน 05: `levels[]` ซ้อน → แถวแบนตาม §8 (20 แถว), (ค) phase_note → warnings[] แล้วลบ field (5 ไฟล์ 7 note), (ง) ⚠️ element_id ตัด underscore — ทำแล้ว **แต่ต้องย้อน 37 จุด เพราะจะทำข้อมูลหาย**, ⚠️ ยังเหลือ — ต้องเปิดแบบจริง สคริปต์ทำแทนไม่ได้

### Community 141 - "2026-08-24"
Cohesion: 0.29
Nodes (6): 2026-08-24, [afternoon, Makham out — standing order under att1235] Claude solo, [evening] Claude — session with Makham (continued), [morning → afternoon] Claude — session with Makham, [ค่ำ-ดึก] Claude — เช่าเครื่องจริง + op04 มาถึงกลางคัน + เทรน t03 รอบเต็ม, [ตี 4 - เช้า 2026-08-25] Claude — เทรนจบ, verify, อัป HF, พบบั๊ก 3 ชนิด, ยกเลิก base เพราะเวลาไม่พอ

### Community 142 - "2026-08-26.md"
Cohesion: 0.29
Nodes (6): [00:20–21:22] makham — GT corrections across multiple houses (reconstructed from git log, not a live session), [afternoon] Claude — session with Makham (format-fix incident affecting Ark's checked houses, verification, apology sent), [Claude] Dictionary ไทย→อังกฤษ แทรกใน prompt (DIP) — ข้อ 1 ของอาจารย์, [Claude] สายพาน v2 ลงมือรอบแรก (มะขามสั่ง GO) — pass 0/1 เดิม, 1.5/2.4/2.5/3 ใหม่, pass3เก่า→pass4, [late night, carried into early morning] Claude — session with Makham (GPU/model research wrap-up: scheduled shutdown, teaching PDF), [morning] Claude — session with Makham (merge conflict resolution)

### Community 143 - "9. เรื่องใหญ่ที่สุดของวัน — ผลทั้งวันพลิกเพราะ "ค่าที่ไม่ได้ตั้ง" ไม่ใช่ "ค่าที่ตั้งผิด""
Cohesion: 0.29
Nodes (7): 9. เรื่องใหญ่ที่สุดของวัน — ผลทั้งวันพลิกเพราะ "ค่าที่ไม่ได้ตั้ง" ไม่ใช่ "ค่าที่ตั้งผิด", ค้นพบอะไร, ทำไมถึงเกิดขึ้นได้ทั้งที่เช็คละเอียดมากแล้ว, ทำไมเรื่องนี้ถึงพลิกทุกอย่างที่สรุปไปก่อนหน้า, ทางเลือกที่เสนอ + สิ่งที่มะขามเลือก, บทเรียนที่บันทึกไว้ถาวร, ยืนยันด้วยการวัดจริง ไม่ใช่แค่อ่านโค้ดแล้วเดา

### Community 144 - "op03 — op01, then shut the laptop down"
Cohesion: 0.33
Nodes (5): op03 — op01, then shut the laptop down, Step 0 — arm the dead-man's switch, before anything else, The shutdown is the last step, and it is gated, Then: run op01 to completion, Two checks first — before arming anything

### Community 145 - "merge_no_delete"
Cohesion: 0.47
Nodes (5): cv_stub(), merge_no_delete(), สร้าง element ตัวแทนของกรอบ CV ที่โมเดลทำหาย — ทุกอย่างที่ CV ไม่รู้จริงเป็น nul, (บัญชี CV จาก pass 2.5, elements ที่โมเดลตอบใน pass 3) → (merged, warnings), _selfcheck()

### Community 146 - "Phase 0 — Prep on your own PC, before renting anything ($0, do this first)"
Cohesion: 0.33
Nodes (6): 0.1 — HuggingFace account + token ✅ DONE (2026-07-24), 0.2 — Vast.ai account ✅ DONE (2026-07-24), 0.3 — Local dry run: prove your PC can run the FINAL result, before spending anything, 0.4 — Re-check the scripts one more time ✅ DONE (2026-07-24) — found a real problem, RESOLVED (MAX_LENGTH→24576, verified in file on 2026-07-25), 0.5 — Instance sizing checklist (decide before clicking Rent) ✅ DONE (2026-07-24), Phase 0 — Prep on your own PC, before renting anything ($0, do this first)

### Community 147 - "_common.md - shared rule block"
Cohesion: 0.33
Nodes (4): BLOCK END, BLOCK START, _common.md - shared rule block, Pass 2 — Qwen อ่านแบบจริง (แขนตัวคุม)

### Community 148 - "train_t03.py"
Cohesion: 0.33
Nodes (4): load_split(), jsonl → PIL Image objects (Unsloth ต้องการ object ไม่ใช่ path)     คืน subtask_, xgrammar builtin JSON grammar — มะขามสั่ง 2026-08-24: หน้า beam plan ต้องแนบ xgr, setup_grammar()

### Community 149 - "t04_Purson/pass0/prompt.md"
Cohesion: 0.33
Nodes (4): Pass 0 - page classification, PROMPT END, PROMPT START, Pass 0 — คัดหน้า

### Community 150 - "Pass 2.4 - Qwen อ่านแบบจริง + hint จาก CV (แขนทดลอง)"
Cohesion: 0.33
Nodes (6): grid ref ใน hint - ยังไม่ทำ (บันทึกไว้กันคิดว่าลืม), Pass 2.4 - Qwen อ่านแบบจริง + hint จาก CV (แขนทดลอง), การทดลอง 2 แขน (2.4b ยกเลิก 2026-08-29), วัดผลอะไร, สัญญาของ hint block (สิ่งที่ต้องมี ไม่ว่าโค้ดจะแก้ถ้อยคำยังไง), ~~แขน 2.4b: ภาพมาร์คเลขแทนภาพเปล่า~~ — ยกเลิก 2026-08-29

### Community 151 - "t04 workflow — Purson (InternVL3-78B fine-tune on t04 dataset + hint arm 2 vs 2.4a)"
Cohesion: 0.33
Nodes (6): Phase 0 — Pre-flight (rule_of_tune ข้อ 4: ทำจริง+ตรวจจริง ก่อนเสียเงินเช่า), t04 workflow — Purson (InternVL3-78B fine-tune on t04 dataset + hint arm 2 vs 2.4a), ⚠️ ช่องว่างที่ต้องปิดก่อนกดเช่าจริง (เรียงตามลำดับที่ต้องทำ), บันทึกการแก้ที่ทำไปแล้วรอบนี้ (2026-08-29), 🔬 ผลสอบสวน: ทำไม recall ต่ำมาก (สอบสวน 2026-08-30 ค่ำ หลังมะขามสั่ง "หาสาเหตุก่อน มันไม่ควรแย่ขนาดนั้น"), ลำดับงานเมื่อพร้อมเช่าจริง (โครงตามรอบก่อน ปรับเป็น InternVL3)

### Community 152 - "t05_Courser/smoke_destrier.py"
Cohesion: 0.53
Nodes (5): gt_marks(), gt_text(), main(), pick_rows(), ดึง mark จาก GT: ค่า string สั้น ๆ ของคีย์ mark/name ใน JSON GT

### Community 153 - "anchors_by_shape"
Cohesion: 0.33
Nodes (6): anchors_by_shape(), _mutual_nearest(), _normalize(), ย่อชุดจุดลงกรอบ [0,1] ของตัวเอง — เทียบรูปทรงการกระจายตัวข้ามหน่วย (เมตร vs พิกเ, คู่ที่ "ต่างฝ่ายต่างเห็นกันเป็นเพื่อนบ้านใกล้สุด" เท่านั้น → [(i, j)]      ใช้, ทางสำรองเมื่อโมเดลไม่ตอบ cv_mark (ซึ่งเป็นกรณีปกติ — destrier เห็น cv_mark

### Community 154 - "training/smoke_destrier.py"
Cohesion: 0.53
Nodes (5): gt_marks(), gt_text(), main(), pick_rows(), ดึง mark จาก GT: ค่า string สั้น ๆ ของคีย์ mark/name ใน JSON GT

### Community 155 - "pursonVision.js"
Cohesion: 0.60
Nodes (5): getSupabaseClient(), purson_analyzeSingle(), purson_getJob(), purson_submitHouseExtract(), purson_waitForJob()

### Community 156 - "Pilot comparison: Claude vs Qwen — บ้าน_เล็ก_1ชั้น_01 (4 หน้า)"
Cohesion: 0.33
Nodes (5): Pilot comparison: Claude vs Qwen — บ้าน_เล็ก_1ชั้น_01 (4 หน้า), ข้อค้นพบที่สำคัญที่สุด, ข้อจำกัดที่ต้องบอกตรงๆ (สำคัญพอๆ กับข้อค้นพบ), ข้อเสนอขั้นต่อไป, สรุปสั้น

### Community 157 - "Vast.ai template — Constistant fine-tune (Qwen3-VL-8B + Unsloth)"
Cohesion: 0.33
Nodes (5): Create the Vast.ai template, Model decision status, Vast.ai template — Constistant fine-tune (Qwen3-VL-8B + Unsloth), What it does NOT do (still manual), What onstart.sh does

### Community 158 - "03บ้าน_เล็ก_2ชั้น_01"
Cohesion: 0.33
Nodes (6): 03บ้าน_เล็ก_2ชั้น_01, 24. Grid master — this house has *genuine* structural dummy grids (1'/3'), confirmed against the architecture floor plan, 25. Beam spec sheet (`หน้า35_column_beam_sections.json`, S-08) — found the same additional_bars position bug twice (B3X, B4), 26. Point-ref dash stripping — mechanical, but caught a real footgun, 27. Misc pattern — 3 whole-series pages found and fixed, 28. Cross-house data bug found and fixed: house #2's price table had 2 wrong digits for house #10's row

### Community 159 - "04บ้าน_เล็ก_2ชั้น_02"
Cohesion: 0.33
Nodes (6): 04บ้าน_เล็ก_2ชั้น_02, 29. Grid master — dummy grid E' cross-confirmed on a 3rd independent structural sheet, 30. Beam spec sheet (`หน้า37_beam_slab_sections.json`, S-08) — same additional_bars bug found on 4 marks (B4, B4A, B4X, B5), 31. Point-ref dash-stripping — repeated the sheet_code footgun from house #3, same fix, 32. Misc pattern — 3 whole-series pages, same as house #3's pattern, 33. Cross-house price-table check, round 2 — found 2 more digit errors, all now resolved with 2-3 way agreement

### Community 160 - "[Afternoon-evening] Makham (working together with Claude Code — continuing from the July 11 session, see `2026-07-11.md`)"
Cohesion: 0.33
Nodes (5): 1. Personally read the remaining structural section S-09 through S-19 (pages 38-48, 11 sheets), 2. Dispatched 5 background agents for the remaining sections (architectural, sanitary, electrical+mechanical, spread-footing BOQ, pile-foundation BOQ+back-of-book references), 3. Repaired the 3 agents' unfinished work personally (instead of re-dispatching), 4. Validated + ran the label-studio script, [Afternoon-evening] Makham (working together with Claude Code — continuing from the July 11 session, see `2026-07-11.md`)

### Community 161 - "2026-07-20.md"
Cohesion: 0.33
Nodes (5): Afternoon round — cascading B'/E' turned into a full-sheet image check for pages 31+32, Claude — Qwen3.6-35B-A3B fine-tune session (Constistant repo, `tune_ai/t01/data_before_tune/`), Evening round — B' correction, deleting elements per instruction, full-sheet check of page33, Late-night round — sweeping every pattern=plan file in house3 against the gridline master, Makham + Claude Code — house 3 dummy grids continued + footing dedup + answering fine-tune questions (continuing from 2026-07-19.md)

### Community 162 - "2026-09-01"
Cohesion: 0.33
Nodes (5): 2026-09-01, Claude (session with Makham — live demo debugging + pass1/1.5/2.5 wiring), Claude (session with Makham — pass3 วัดระยะจากผังกริด + เชื่อมเข้าเว็บ), Claude (session with Makham — จำลองรันบ้านจริงทั้งหลังโดยไม่เช่าการ์ด + เอกสารสอนมะขาม), Claude (session with Makham — แก้ 2 บั๊กค้าง + พิสูจน์ pass3 กับแบบจริง)

### Community 163 - "Workmen's Diary"
Cohesion: 0.33
Nodes (5): Template for a new entry, Usage example, Why this diary exists, Workmen's Diary, Writing rules

### Community 164 - "4. 0.3 — "ซ้อมของจริง" บนคอมตัวเองก่อน (local dry run)"
Cohesion: 0.33
Nodes (6): 4. 0.3 — "ซ้อมของจริง" บนคอมตัวเองก่อน (local dry run), GGUF คืออะไร, llama.cpp คืออะไร, mmproj คืออะไร — ทำไมเป็นปัญหาใหญ่วันที่ 21, Quantization (การบีบอัด) คืออะไร, สิ่งที่ทำจริงวันนี้ (ซ้อมทั้งกระบวนการ ก่อนเสียเงินเช่า)

### Community 165 - "Prompt Library — Thai RC Drawing Pipeline"
Cohesion: 0.40
Nodes (4): Prompt Library — Thai RC Drawing Pipeline, การใช้งาน Label Studio, โครงสร้าง Pipeline, ไฟล์

### Community 166 - "The grid master records EVERY printed dimension in the whole set (added 2026-08-21, Makham)"
Cohesion: 0.40
Nodes (5): 1. `z_levels[]` — the vertical axis, same role as `x_lines`/`y_lines`, 2. `dimension_chains[]` — every printed dimension row, on any axis, 3. `unassigned_dimensions[]` — the catch-all, so nothing is ever dropped, Relationship to the resolved axes, The grid master records EVERY printed dimension in the whole set (added 2026-08-21, Makham)

### Community 167 - "4a. `notes` pattern — the `notes{}` object (added 2026-08-21)"
Cohesion: 0.40
Nodes (5): 4a. `notes` pattern — the `notes{}` object (added 2026-08-21), Rules, Shape, The flat half is a derived alias, never a second reading, The nested half is what the drawing says

### Community 168 - "6b. Footings and pile caps — same flat fields as everything else (added 2026-08-28)"
Cohesion: 0.40
Nodes (5): 6b. Footings and pile caps — same flat fields as everything else (added 2026-08-28), Context fields — keep, don't re-spell, Forbidden spellings — write the right-hand column, Legacy files, The four load-bearing fields

### Community 169 - "convert"
Cohesion: 0.50
Nodes (4): convert(), floor_from(), Path, อ่านชั้นจากหัวแบบ — ไม่เจอคืน None (ห้ามเดาเป็น F1 ตามสเปก)

### Community 171 - "t05_Courser/worker_page.py"
Cohesion: 0.70
Nodes (4): build_messages_house(), build_messages_val(), load_val_row(), main()

### Community 172 - "worker_page_raw_pratyad.py"
Cohesion: 0.70
Nodes (4): build_messages_house(), build_messages_val(), load_val_row(), main()

### Community 173 - "t05_Destier — ทุกอย่างที่ "ใช้จริง" ของ Destrier รวมไว้ที่เดียว"
Cohesion: 0.40
Nodes (4): t05_Destier — ทุกอย่างที่ "ใช้จริง" ของ Destrier รวมไว้ที่เดียว, ถ้าจะรันจริงจากที่นี่, สิ่งที่ **ไม่** เอามาใส่ (ตัดใจแล้ว ไม่ใช่ลืม), โครงสร้าง

### Community 175 - "training/worker_page.py"
Cohesion: 0.70
Nodes (4): build_messages_house(), build_messages_val(), load_val_row(), main()

### Community 176 - "index.ts"
Cohesion: 0.40
Nodes (3): corsHeaders, endpointKey, endpointUrl

### Community 177 - "5. Rebar spec — รวมโครงสร้างใหม่ (breaking change จากทั้ง 2 ฝั่งเดิม แต่มีเหตุผลจากหลักฐานจริง)"
Cohesion: 0.40
Nodes (5): 5.1 เปลี่ยนจาก flat field เป็น nested object (ตาม Makham), 5.2 แก้ปัญหาเหล็กบน-ล่างไม่เท่ากัน (คำถามเปิดข้อ 5 ของ Makham — **ตัดสินใจแล้ว**), 5.3 `additional_bars[]` (เหล็กเสริมพิเศษหยุดที่ L/8) — รับเข้ามาตามที่ Makham เสนอ, 5.4 `Ø` (กลม) = RB เสมอ ไม่ใช่ DB — ยืนยันร่วมกันแล้ว (ทั้งคู่เจอ bug เดียวกันอิสระ), 5. Rebar spec — รวมโครงสร้างใหม่ (breaking change จากทั้ง 2 ฝั่งเดิม แต่มีเหตุผลจากหลักฐานจริง)

### Community 178 - "stale_value_logs — ย้ายออกจาก training data 2026-08-25"
Cohesion: 0.40
Nodes (4): stale_value_logs — ย้ายออกจาก training data 2026-08-25, ตัวชี้ที่ค้างอยู่, ทำไมย้าย, ไฟล์

### Community 179 - "05บ้าน_เล็ก_2ชั้น_03"
Cohesion: 0.40
Nodes (5): 05บ้าน_เล็ก_2ชั้น_03, 34. Mechanical convention normalization (30 pattern=plan files), 35. Grid master rebuilt + 2 new dummy grids found by Makham's beam-endpoint rule (F', 4'), 36. House 05 follow-up (2026-07-19, autonomous continuation per Makham's "keep working" instruction), 37. ⚠️ MAJOR: series price-table 8x re-verification — REVERSES the 2026-07-16 house-#10 corrections + 4 more digit fixes (all 4 copies agree)

### Community 180 - "63. ล็อกรูปแบบในสเปค + ทำ checker อัตโนมัติ — เตรียมรับ op1 บ้าน 1000 หลัง (2026-08-02)"
Cohesion: 0.40
Nodes (5): ⚠️ §0.1 ฉบับแรกของผมกว้างเกินไป ต้องแก้เอง, 63. ล็อกรูปแบบในสเปค + ทำ checker อัตโนมัติ — เตรียมรับ op1 บ้าน 1000 หลัง (2026-08-02), ทำ `tools/check_format.py` — รันเช็ค 14 ข้ออัตโนมัติ, ผล, เพิ่ม §0 FORMAT LOCK ไว้หัวสเปค (10 หัวข้อย่อย)

### Community 181 - "2026-08-18"
Cohesion: 0.40
Nodes (4): [00:09] Claude — session with Makham, 2026-08-18, [afternoon] Claude — session with Makham, [evening] Claude — session with Makham

### Community 182 - "2026-08-27"
Cohesion: 0.40
Nodes (4): [00:02] makham — house 37 GT correction (reconstructed from git log, not a live session), [12:18–13:00] Claude Opus 5 (1M context) — graphify knowledge-graph setup, [18:58] makham — house 50 milestone (reconstructed from git log, not a live session), 2026-08-27

### Community 183 - "11. พรุ่งนี้ทำอะไรต่อ — เรียงตามลำดับ"
Cohesion: 0.40
Nodes (5): 11. พรุ่งนี้ทำอะไรต่อ — เรียงตามลำดับ, ⛔ สิ่งที่ยังไม่ควรทำ, 🔴 อันดับ 1 (ฟรี, ~20 นาที) — พิสูจน์ว่า LoRA อยู่ใน GGUF ไหม, 🟠 อันดับ 2 (ฟรี, ไม่กี่นาที) — แก้ด่านตรวจใน `export_gguf.py`, 🟡 อันดับ 3 — ค่อยเลือกทางแก้ ตามผลของอันดับ 1

### Community 184 - "2. เจอบั๊กใหม่ที่ไม่เคยเจอในรอบ t01 — เพราะ "เวอร์ชันไลบรารีขยับ""
Cohesion: 0.40
Nodes (5): 2. เจอบั๊กใหม่ที่ไม่เคยเจอในรอบ t01 — เพราะ "เวอร์ชันไลบรารีขยับ", ทำไมไม่มีใครรู้ล่วงหน้า, ปัญหา, วิธีแก้จริง, อธิบายง่ายๆ ว่าเกิดอะไรขึ้น

### Community 185 - "4. 🔑 หลักฐานที่ทำให้สงสัยว่า LoRA ไม่ได้อยู่ใน GGUF"
Cohesion: 0.40
Nodes (5): 4. 🔑 หลักฐานที่ทำให้สงสัยว่า LoRA ไม่ได้อยู่ใน GGUF, ทำไม t02 ถึงถูกจับได้ แต่ t01 หลุด, 🧪 วิธีพิสูจน์ — ถูกและเร็ว ทำพรุ่งนี้ได้เลย, หลักฐาน A — t01 ใช้กลไก LoRA แบบเดียวกับที่ทำ t02 พัง, หลักฐาน B — ด่านตรวจของ t01 อ่อนจนโมเดลเปล่าก็ผ่าน

### Community 186 - "op01 — extract one house into raw JSON"
Cohesion: 0.50
Nodes (3): op01 — extract one house into raw JSON, Standing order — decide, don't ask, Steps

### Community 187 - "house_of"
Cohesion: 0.67
Nodes (3): house_of(), main(), ชื่อไฟล์: cand_<kind>__<บ้าน>__g0_n18.png → คืนชื่อบ้าน หรือ '?' ถ้าอ่านไม่ออก

### Community 190 - "t02/data_before_tune/onstart.sh"
Cohesion: 0.50
Nodes (3): MODEL_SIZE, onstart.sh script, TORCH_CUDA_ARCH_LIST

### Community 191 - "t02 inference results — beam plan pages, ad-hoc read (ไม่ใช่ eval รอบเป็นทางการ)"
Cohesion: 0.50
Nodes (3): t02 inference results — beam plan pages, ad-hoc read (ไม่ใช่ eval รอบเป็นทางการ), รอบเช่า 2026-08-21/22 กลางคืน — xgrammar พิสูจน์บน GPU จริงแล้ว ✅, สรุป

### Community 192 - "pass2_gridline.md - the grid master"
Cohesion: 0.50
Nodes (3): pass2_gridline.md - the grid master, PROMPT END, PROMPT START

### Community 193 - "pass2_material_list.md - bill of quantities (BOQ)"
Cohesion: 0.50
Nodes (3): pass2_material_list.md - bill of quantities (BOQ), PROMPT END, PROMPT START

### Community 194 - "pass2_notes.md - project-level specifications"
Cohesion: 0.50
Nodes (3): pass2_notes.md - project-level specifications, PROMPT END, PROMPT START

### Community 195 - "pass2_plan.md - structural plans"
Cohesion: 0.50
Nodes (3): pass2_plan.md - structural plans, PROMPT END, PROMPT START

### Community 196 - "pass2_plan_beam.md - beam plan (floor beams and roof framing)"
Cohesion: 0.50
Nodes (3): pass2_plan_beam.md - beam plan (floor beams and roof framing), PROMPT END, PROMPT START

### Community 197 - "pass2_plan_column.md - column plan (not wired into training - see note)"
Cohesion: 0.50
Nodes (3): pass2_plan_column.md - column plan (not wired into training - see note), PROMPT END, PROMPT START

### Community 198 - "pass2_plan_footing.md - footing / pile-cap plan"
Cohesion: 0.50
Nodes (3): pass2_plan_footing.md - footing / pile-cap plan, PROMPT END, PROMPT START

### Community 199 - "pass2_plan_slab.md - floor slab plan"
Cohesion: 0.50
Nodes (3): pass2_plan_slab.md - floor slab plan, PROMPT END, PROMPT START

### Community 200 - "pass2_schedule.md - summary tables"
Cohesion: 0.50
Nodes (3): pass2_schedule.md - summary tables, PROMPT END, PROMPT START

### Community 201 - "pass2_section.md - detail sections (rebar specs)"
Cohesion: 0.50
Nodes (3): pass2_section.md - detail sections (rebar specs), PROMPT END, PROMPT START

### Community 202 - "pass2_soil_boring_log.md - soil investigation / borehole log"
Cohesion: 0.50
Nodes (3): pass2_soil_boring_log.md - soil investigation / borehole log, PROMPT END, PROMPT START

### Community 203 - "pure_power_read.py"
Cohesion: 0.83
Nodes (3): load(), main(), page_path()

### Community 204 - "t05_Courser/run_cv_batch.py"
Cohesion: 0.83
Nodes (3): collect_targets(), house_of(), main()

### Community 205 - "t05_Courser/run_queue.sh"
Cohesion: 0.67
Nodes (3): LD_LIBRARY_PATH, run_one(), run_queue.sh script

### Community 206 - "t05_Courser/run_queue_elements.sh"
Cohesion: 0.67
Nodes (3): LD_LIBRARY_PATH, run_one(), run_queue_elements.sh script

### Community 207 - "t05_Courser/run_queue_gpuA.sh"
Cohesion: 0.67
Nodes (3): LD_LIBRARY_PATH, run_one(), run_queue_gpuA.sh script

### Community 209 - "_common.md - shared rule block"
Cohesion: 0.50
Nodes (3): BLOCK END, BLOCK START, _common.md - shared rule block

### Community 210 - "Pass 0 - page classification"
Cohesion: 0.50
Nodes (3): Pass 0 - page classification, PROMPT END, PROMPT START

### Community 211 - "pass2_gridline.md - the grid master"
Cohesion: 0.50
Nodes (3): pass2_gridline.md - the grid master, PROMPT END, PROMPT START

### Community 212 - "pass2_material_list.md - bill of quantities (BOQ)"
Cohesion: 0.50
Nodes (3): pass2_material_list.md - bill of quantities (BOQ), PROMPT END, PROMPT START

### Community 213 - "pass2_notes.md - project-level specifications"
Cohesion: 0.50
Nodes (3): pass2_notes.md - project-level specifications, PROMPT END, PROMPT START

### Community 214 - "pass2_plan_beam.md - beam plan (floor beams and roof framing)"
Cohesion: 0.50
Nodes (3): pass2_plan_beam.md - beam plan (floor beams and roof framing), PROMPT END, PROMPT START

### Community 215 - "pass2_plan_column.md - column plan (not wired into training - see note)"
Cohesion: 0.50
Nodes (3): pass2_plan_column.md - column plan (not wired into training - see note), PROMPT END, PROMPT START

### Community 216 - "pass2_plan_footing.md - footing / pile-cap plan"
Cohesion: 0.50
Nodes (3): pass2_plan_footing.md - footing / pile-cap plan, PROMPT END, PROMPT START

### Community 217 - "pass2_plan_slab.md - floor slab plan"
Cohesion: 0.50
Nodes (3): pass2_plan_slab.md - floor slab plan, PROMPT END, PROMPT START

### Community 218 - "pass2_schedule.md - summary tables"
Cohesion: 0.50
Nodes (3): pass2_schedule.md - summary tables, PROMPT END, PROMPT START

### Community 219 - "pass2_section.md - detail sections (rebar specs)"
Cohesion: 0.50
Nodes (3): pass2_section.md - detail sections (rebar specs), PROMPT END, PROMPT START

### Community 220 - "pass2_soil_boring_log.md - soil investigation / borehole log"
Cohesion: 0.50
Nodes (3): pass2_soil_boring_log.md - soil investigation / borehole log, PROMPT END, PROMPT START

### Community 221 - "training/run_cv_batch.py"
Cohesion: 0.83
Nodes (3): collect_targets(), house_of(), main()

### Community 222 - "training/run_queue.sh"
Cohesion: 0.67
Nodes (3): LD_LIBRARY_PATH, run_one(), run_queue.sh script

### Community 223 - "training/run_queue_elements.sh"
Cohesion: 0.67
Nodes (3): LD_LIBRARY_PATH, run_one(), run_queue_elements.sh script

### Community 224 - "training/run_queue_gpuA.sh"
Cohesion: 0.67
Nodes (3): LD_LIBRARY_PATH, run_one(), run_queue_gpuA.sh script

### Community 225 - "2026-07-05.md"
Cohesion: 0.50
Nodes (3): [Early morning ~00:00–02:40] Makham (working together with Claude — this session), Entry — Data Schema review + Phase A reorganization (Claude Code + taddy), [retroactive note, added 2026-08-04] Claude — archival record for a file dated this day

### Community 226 - "2026-07-07.md"
Cohesion: 0.50
Nodes (3): [~18:00] Makham (working together with Claude Code — new session), [~18:15] Makham (working together with Claude Code — same session, continuing from the previous entry), [~19:00–23:33] Makham (working together with Claude Code — same session, continuing from the previous entry) — Gen 4 full extraction round "t3" + Label Studio setup

### Community 227 - "2026-08-20"
Cohesion: 0.50
Nodes (3): 2026-08-20, [evening] Claude — session with Makham, [late night → early 2026-08-21] Claude — session with Makham

### Community 228 - "3. 🔑 เบาะแสสำคัญ: "พังในแบบที่ผิดธรรมชาติของโมเดลที่ทูนมาแล้ว""
Cohesion: 0.50
Nodes (4): 3. 🔑 เบาะแสสำคัญ: "พังในแบบที่ผิดธรรมชาติของโมเดลที่ทูนมาแล้ว", ข้อเท็จจริงที่ทำให้ทุกอย่างเปลี่ยน, สิ่งที่ผลลัพธ์แบบนี้เหมือนที่สุดคือ..., แล้วทำไมถึงแปลก

### Community 229 - "แคตตาล็อก AI — ทางเลือกโมเดล Vision ขนาด 100-200B (นอกจาก Qwen)"
Cohesion: 0.50
Nodes (3): ตารางสรุปทั้งหมด, ผลชี้ขาด, แคตตาล็อก AI — ทางเลือกโมเดล Vision ขนาด 100-200B (นอกจาก Qwen)

### Community 231 - "1. Pattern taxonomy — 19 types"
Cohesion: 0.67
Nodes (3): 1. Pattern taxonomy — 19 types, ⚠️ `roof_plan` vs `plan` — a real, live data-loss bug (found 2026-08-21), The plan family — `beam_plan` · `footing_plan` · `roof_frame_plan` · `etc_plan` (split 2026-08-28)

### Community 236 - "0.0 ตารางคุมตัวแปร — หัวใจของรอบนี้"
Cohesion: 0.67
Nodes (3): 0.0 ตารางคุมตัวแปร — หัวใจของรอบนี้, ทำไม 30B-A3B ไม่ใช่ 8B หรือ 32B, เกณฑ์ตัดสิน — ตัวเลขที่ต้องเอาชนะ

### Community 261 - "7. ทำไมมันช้า — เลขจริงและเหตุผล"
Cohesion: 0.67
Nodes (3): 7. ทำไมมันช้า — เลขจริงและเหตุผล, ทำไม classify เร็วกว่าถอดเต็ม 7 เท่า ทั้งที่ดูภาพเดียวกัน, เหตุผล — เลขคณิตง่าย ๆ

## Knowledge Gaps
- **1530 isolated node(s):** `project`, `phase`, `scope`, `focus`, `datasets` (+1525 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t03 prompt design — 2 passes, per-pattern extraction` connect `T01 Eval Fields Script` to `rule_of_tune.md`?**
  _High betweenness centrality (0.003) - this node is a cross-community bridge._
- **Why does `Rules for Touching Raw Training JSON` connect `Rules for Touching Raw Training JSON` to `rule_of_tune.md`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Why does `rawjson_ยังไม่ได้แก้ไขโดนคน` connect `T03 Dataset Pull & Verify Script` to `rule_of_tune.md`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **What connects `project`, `phase`, `scope` to the rest of the system?**
  _1530 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CV Scan Detection Pipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.058385093167701865 - nodes in this community are weakly interconnected._
- **Should `Harvest Report - Template Match QA` be split into smaller, more focused modules?**
  _Cohesion score 0.041666666666666664 - nodes in this community are weakly interconnected._
- **Should `T01 Batch House Extraction (GPU-Rental)` be split into smaller, more focused modules?**
  _Cohesion score 0.0425531914893617 - nodes in this community are weakly interconnected._