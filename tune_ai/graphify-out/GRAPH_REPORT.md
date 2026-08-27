# Graph Report - tune_ai  (2026-08-27)

## Corpus Check
- Large corpus: 974 files · ~14,527,363 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 420 nodes · 583 edges · 45 communities (38 shown, 7 thin omitted)
- Extraction: 92% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 43 edges (avg confidence: 0.75)
- Token cost: 483,397 input · 0 output

## Community Hubs (Navigation)
- T01 House 08-11 GPU-Rental Workflow
- T02 Dataset Provenance & Training Bugs
- T03 GT-vs-AI Overlay Renderer
- T02 House09 Export & Inference Runs
- T02/T03 Batch Inference Runners
- T01 Dataset Builder (build_dataset.js)
- T02 Dataset Builder (build_dataset.js)
- T03 Comparison PNG Report Builder
- T01 Batch House Extraction Runner
- T03 Gridline/Plan Prompt Passes
- T03 Dataset Builder (build_dataset_t03.py)
- T01 Single-House Local Extraction Script
- T01 Multi-House Local Extraction Script
- T03 Common Rules + Schedule Pass
- T03 Pass1 Page Organizer
- T03 Notes Pass & Schema Drift
- T03 Pass3/Pass4 Takeoff Prompts
- T02 House09 Overlay Renderer
- T03 Pass0 Classifier (current vs superseded)
- T03 Dataset Pull & Verify Script
- T03 Visual Token Capacity Measurement
- T03 Training Script (train_t03.py)
- T03 Dataset Sizing Analysis
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

## God Nodes (most connected - your core abstractions)
1. `t03 README` - 19 edges
2. `_common.md Shared Rule Block` - 17 edges
3. `plan Pass (footing/column/beam/slab)` - 12 edges
4. `_selftest()` - 11 edges
5. `t02 Workflow (Qwen3-VL-30B-A3B vs Qwen3.6-35B-A3B A/B)` - 11 edges
6. `t03 Workflow Log` - 11 edges
7. `train_qwen3vl.py Training Script` - 10 edges
8. `main()` - 9 edges
9. `t01 Dataset + Training README` - 9 edges
10. `Pass Design v2 (2026-08-26 renumbering + hint pipeline)` - 9 edges

## Surprising Connections (you probably didn't know these)
- `t01 Prompt Explained (PDF)` --conceptually_related_to--> `t01 PROMPT_SHORT (inference instruction)`  [AMBIGUOUS]
  t01/t01_prompt_อธิบาย.pdf → t01/ai_output_บ้าน_ใหญ่_1ชั้น_01/_prompt_short.txt
- `generate()` --calls--> `grammar_setup()`  [INFERRED]
  t01/data_before_tune/run_house_batch_t01.py → t02/data_before_tune/run_house_batch.py
- `render_page()` --calls--> `render_layer()`  [INFERRED]
  t02/overlay_gt_vs_ai_house09.py → t03/data_before_tune/overlay_gt_vs_ai.py
- `Two-Pass Design README (superseded)` --conceptually_related_to--> `t03 Prompt Design PDF (2026-08-04)`  [INFERRED]
  t03/_old_2026-08-04_two_pass/README.md → t03/_old_2026-08-04_two_pass/t03_prompt_design_2026-08-04.pdf
- `generate()` --calls--> `grammar_setup()`  [INFERRED]
  t03/data_before_tune/infer_house_t03.py → t02/data_before_tune/run_house_batch.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **t01 fine-tuning + GGUF export pipeline** — t01_t01_workflow_qwen36_35b_a3b_model, t01_data_before_tune_readme_train_qwen36_script, t01_t01_workflow_export_gguf_script, t01_t01_workflow_hf_repo_qwen36_thai_rc, t01_t01_workflow_vision_encoder_freeze_mmproj_reuse [INFERRED 0.85]
- **House 11 tuned-vs-base fair comparison experiment** — t01_08_09_10_workflow, t01_result_house11_base_variant_run, t01_result_house11_tuned_variant_run, t01_08_09_10_workflow_fair_comparison_scope_cut [EXTRACTED 1.00]
- **t01 dataset curation decisions** — t01_data_before_tune_readme, t01_data_before_tune_readme_drop_cross_page_specs, t01_data_before_tune_readme_strip_worklog, t01_data_before_tune_readme_instruction_weighting, t01_data_before_tune_readme_val_split_by_house, t01_data_before_tune_readme_visual_token_budget [INFERRED 0.85]
- **Grammar-Constrained Decoding Debugging Arc (lmfe -> trailing comma root cause -> xgrammar adoption)** — t02_infer_results_summary_lm_format_enforcer_run, t02_infer_results_summary_trailing_comma_root_cause, t02_infer_results_summary_strict_schema_parked, t02_infer_results_summary_xgrammar_run, t02_infer_results_summary_gpu_proof_night_run [EXTRACTED 1.00]
- **train_qwen3vl.py Bug-Fix Set (bugs 1-9 achieving hyperparameter parity with t01)** — t02_t02_workflow_train_qwen3vl_script, t02_t02_workflow_bug1_max_length_gridmaster_truncation, t02_t02_workflow_bug2_collator_512px_silent_downscale, t02_t02_workflow_bug6_lora_dropout_moe_unsupported, t02_t02_workflow_bug7_optim_oom_regression, t02_t02_workflow_bug8_missing_bf16_true, t02_t02_workflow_bug9_ip_max_pixels_no_setter_crash [EXTRACTED 1.00]
- **House 09 Element-Recall Failure Evidence Chain (export README + inference run + overlay visualization)** — t02_export_platform_09_readme_span_recall_gap_finding, t02_infer_results_house09_p26_beamplan_raw_infer_house09_p26, t02_infer_results_summary_overlay_gt_vs_ai_house09 [INFERRED 0.85]
- **The Current Production Prompt Set (pass2_used + _common)** — t03__common, t03_pass2_used_gridline, t03_pass2_used_plan, t03_pass2_used_section, t03_pass2_used_schedule, t03_pass2_used_notes, t03_pass2_used_material_list, t03_pass2_used_soil_boring_log [EXTRACTED 1.00]
- **Superseded Two-Pass Legacy Design (2026-08-04)** — t03__old_2026_08_04_two_pass_readme, t03__old_2026_08_04_two_pass_pass0_prompt, t03__old_2026_08_04_two_pass_pass1_io_spec, t03__old_2026_08_04_two_pass_t03_prompt_design_2026_08_04 [EXTRACTED 1.00]
- **Detection-Augmented VLM Extraction Pipeline (Pass v2 + Research)** — t03_pass_design_v2, t03_pass_design_v2_set_of_mark_hint, t03_pass_design_v2_ab_experiment, t03_research_beam_grounding_vs_gridmaster [INFERRED 0.80]

## Communities (45 total, 7 thin omitted)

### Community 0 - "T01 House 08-11 GPU-Rental Workflow"
Cohesion: 0.08
Nodes (38): House 08-09-10 Local GGUF Workflow (superseded), extract_houses_local.py (local llama-server 2-phase extraction), t03 Pass 2 pattern filter reuse (7 patterns), House 11 GPU-Rental bf16/PEFT Workflow, Fair-comparison scope cut (drop pages either variant failed), Grammar-constrained decoding vs wall-clock timeout lesson, Low element recall / VLM counting hallucination finding (house 11), run_house_batch_t01.py (bf16/PEFT batch extraction script) (+30 more)

### Community 1 - "T02 Dataset Provenance & Training Bugs"
Cohesion: 0.07
Nodes (33): A/B Test Design (single-variable control), Do NOT re-run build_dataset.js Rule, Grid-Master Multi-Image Examples, SHA-256 Byte-Identical Verification, t02 Dataset (byte-identical copy of t01), Bug 1: max_length Truncates Gridmaster Examples, Bug 2: Collator Silently Downscales to 512px, Bug 3: max_seq_length Default 2048 Cuts Image Tokens (+25 more)

### Community 2 - "T03 GT-vs-AI Overlay Renderer"
Cohesion: 0.13
Nodes (24): draw_element(), fail_note(), _fit_group(), Grid, grid_instances(), iter_elements(), _line_groups(), load_ai_pages() (+16 more)

### Community 3 - "T02 House09 Export & Inference Runs"
Cohesion: 0.12
Nodes (24): Qwen t02 House 09 Constistant Export Package, export_qwen_to_platform.py Converter, --fix-roof-pattern Label Correction, Element Recall / Span Calculation Gap (0/21 vs 18/104 GT), Inference Run: House01 p19 Beam Plan (INVALID), Inference Run: House03 p31 Beam Plan Floor1 (valid, sparse), Inference Run: House04 p33 Beam Plan Floor1 (valid, sparse), Inference Run: House08 p21 Grammar-Constrained (lm-format-enforcer, INVALID) (+16 more)

### Community 4 - "T02/T03 Batch Inference Runners"
Cohesion: 0.14
Nodes (18): Path, grammar_setup(), run_one(), apply_arm(), element_ids(), generate(), load_model(), main() (+10 more)

### Community 5 - "T01 Dataset Builder (build_dataset.js)"
Cohesion: 0.10
Nodes (18): CFG, clean(), DROP_KEYS, est(), examples, fs, HARD_LEAK_RE, houses (+10 more)

### Community 6 - "T02 Dataset Builder (build_dataset.js)"
Cohesion: 0.10
Nodes (18): CFG, clean(), DROP_KEYS, est(), examples, fs, HARD_LEAK_RE, houses (+10 more)

### Community 7 - "T03 Comparison PNG Report Builder"
Cohesion: 0.23
Nodes (18): bold(), build_html(), esc(), estimate_height(), fmt_pct(), main(), measure_height(), nlines() (+10 more)

### Community 8 - "T01 Batch House Extraction Runner"
Cohesion: 0.23
Nodes (13): discover_pages(), generate(), load_model(), log(), main(), variant='tuned' -> base+adapter (PEFT); variant='base' -> base เพียวๆ ไม่มี adap, xgrammar builtin JSON grammar — เหมือน t02's run_house_batch.py (rule_of_tune.md, StoppingCriteria แบบ duck-typed (import transformers.StoppingCriteria ตรงๆ ในฟัง (+5 more)

### Community 9 - "T03 Gridline/Plan Prompt Passes"
Cohesion: 0.17
Nodes (16): Old Pass 1 I/O Spec (15 patterns), Images Manifest (data_before_tune), gridline Pass (grid master extraction), Dummy Grid Naming Rule (beam-endpoint rule), Grid Master Concept (x_lines/y_lines/z_levels), plan Pass (footing/column/beam/slab), Anti-Repetition/Anti-Loop Instruction, Beam-Endpoint Rule (every endpoint must land on a named line) (+8 more)

### Community 10 - "T03 Dataset Builder (build_dataset_t03.py)"
Cohesion: 0.21
Nodes (12): filter_elements(), find_image(), gt_for_plan_subtask(), load_prompt_block(), main(), prompt_for(), คืน (block ที่เจาะช่อง {{GLOSSARY}} ไว้, ตัว glossary)      glossary ไทย→field, GT = wrapper + elements filtered to this subtask's types (views preserved). (+4 more)

### Community 11 - "T01 Single-House Local Extraction Script"
Cohesion: 0.35
Nodes (12): call_model(), classify_page(), extract_page(), image_data_uri(), load_classify(), log(), main(), patterns_from_existing_extract() (+4 more)

### Community 12 - "T01 Multi-House Local Extraction Script"
Cohesion: 0.36
Nodes (11): call_model(), classify_page(), discover_pages(), extract_page(), image_data_uri(), log(), main(), หมายเลขหน้าจริงจากชื่อไฟล์ png (กัน gap ในลำดับ ไม่เดาว่าต่อเนื่อง 1..N). (+3 more)

### Community 13 - "T03 Common Rules + Schedule Pass"
Cohesion: 0.20
Nodes (11): _common.md Shared Rule Block, element_id = Printed Mark Only Rule, element_type Closed Vocabulary, grid_ref Notation Rule, The Honesty Rules (never guess/never drop/never repeat), Output Shape Rule (elements[]/grid{}/categories[]), schedule Pass (member summary tables), One Row = One Member Rule (+3 more)

### Community 14 - "T03 Pass1 Page Organizer"
Cohesion: 0.27
Nodes (10): binarize(), cut_views(), find_dividers(), main(), ตัดหน้าเป็นรูปละ view ตามคำบอกตำแหน่งจาก pass 0     คืน (list ของ box (x0,y0,x1, อ่านรูปเป็นขาวดำ (255 = มีหมึก) — รองรับ path ภาษาไทยด้วย np.fromfile, ตัดแถบ title block ทางขวาออก (ชุดแบบราชการมีทุกแผ่น) — หาเส้นตั้งเข้มในโซนขวา, หาเส้นแบ่ง n_parts-1 เส้นในช่วง [lo, hi) ตามแกนที่ระบุ     axis 0 = แบ่งตามแนวน (+2 more)

### Community 15 - "T03 Notes Pass & Schema Drift"
Cohesion: 0.20
Nodes (11): notes Pass (project specifications), notes Container Key Drift (6 spellings, 55 files), sections[] + notes{} Two-Container Design, soil_boring_log Pass (borehole reports), Borehole Layer/SPT Field Design (draft), t03 README, Grid Master Schema Change (z_levels/dimension_chains/unassigned_dimensions), notes Pattern Missing Value-Field Definitions (§4a fix) (+3 more)

### Community 16 - "T03 Pass3/Pass4 Takeoff Prompts"
Cohesion: 0.22
Nodes (10): Pass 3 Takeoff Prompt (dimensions/rebar from confirmed elements), {{ELEMENT_ACCOUNT}} Placeholder, merge_no_delete() Code-Enforced Guard, Old Pass 3 Extract Prompt (unused patterns, pre-rename), pass4_unused Extract Prompt (11 unused subtasks), {{PATTERN}}/{{TARGET}}/{{NEEDS_GRID}} Placeholders, Pass Design v2 (2026-08-26 renumbering + hint pipeline), 3-Arm A/B Experiment (2 / 2.4a / 2.4b) (+2 more)

### Community 17 - "T02 House09 Overlay Renderer"
Cohesion: 0.28
Nodes (8): draw_element(), parse_zone(), Overlay house09 (บ้าน_เล็ก_1ชั้น_04) — GREEN = ground-truth elements, ORANGE =, E1' -> ('E','1'); None if ids unknown., F-E x 1'-2'' -> ((y0,y1),(x0,x1)) in metres; None if unparsable., Returns True if anything was drawn for element e., render_page(), split_point()

### Community 18 - "T03 Pass0 Classifier (current vs superseded)"
Cohesion: 0.22
Nodes (9): Old Pass 0 Prompt (page classify + wrapper), Two-Pass Design README (superseded), 2-Pass Extraction Design (2026-08-04), t03 Prompt Design PDF (2026-08-04), Pass 0 Classifier Prompt (current), 16-Pattern Taxonomy Classification, Roof Framing plan_beam vs roof_plan Trap, views[] Multi-View Page Inventory (+1 more)

### Community 19 - "T03 Dataset Pull & Verify Script"
Cohesion: 0.46
Nodes (7): local_sha(), main(), คืน {relative_path: size} ของไฟล์ทั้งหมดใต้ d (ว่าง = ไม่มีโฟลเดอร์นั้น), sha256 ของทุกไฟล์ใต้ d — ขนาดตรงกันยังพลาดได้ (ไฟล์เสียระหว่างโอนโดยขนาดเท่าเดิม, remote_listing(), remote_sha(), sh()

### Community 20 - "T03 Visual Token Capacity Measurement"
Cohesion: 0.43
Nodes (6): load(), measure(), จำนวน visual token ของภาพ 1 ใบ หลังโดน cap (Qwen ย่อภาพให้พอดี cap โดยรักษาสัดส่, คืน (รายตัวอย่าง, สถิติภาพ) — ทุกตัวเลขคำนวณจากไฟล์ภาพจริง ไม่ได้ประมาณ, report(), visual_tokens()

### Community 21 - "T03 Training Script (train_t03.py)"
Cohesion: 0.33
Nodes (4): load_split(), jsonl → PIL Image objects (Unsloth ต้องการ object ไม่ใช่ path)     คืน subtask_, xgrammar builtin JSON grammar — มะขามสั่ง 2026-08-24: หน้า beam plan ต้องแนบ xgr, setup_grammar()

### Community 22 - "T03 Dataset Sizing Analysis"
Cohesion: 0.33
Nodes (6): Dataset Sizing Analysis, material_list Over-Annotation Waste Finding, plan_column Data Scarcity Problem, Per-Subtask Example Count Table, material_list Pass (BOQ extraction), categories[].items[] Container

### Community 23 - "T03 ID Ceiling Measurement"
Cohesion: 0.50
Nodes (3): gt_of(), คืน {subtask: (total_ids, printed_ids, [ตัวอย่างที่คนตั้งเอง])}, scan()

### Community 26 - "T02 GPU Rental Onstart Script"
Cohesion: 0.50
Nodes (3): MODEL_SIZE, onstart.sh script, TORCH_CUDA_ARCH_LIST

### Community 27 - "T03 Beam Grounding Research"
Cohesion: 0.67
Nodes (4): Set-of-Mark Hint Design for Pass 2.4, Research: Beam Grounding vs Gridmaster, GroundCount: Detection-Augmented Counting for VLMs, Qwen3-VL Native 2D Grounding Capability

## Ambiguous Edges - Review These
- `t01 PROMPT_SHORT (inference instruction)` → `t01 Prompt Explained (PDF)`  [AMBIGUOUS]
  t01/t01_prompt_อธิบาย.pdf · relation: conceptually_related_to

## Knowledge Gaps
- **70 isolated node(s):** `fs`, `path`, `REPO_ROOT`, `CFG`, `DROP_KEYS` (+65 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `t01 PROMPT_SHORT (inference instruction)` and `t01 Prompt Explained (PDF)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `main()` connect `T03 GT-vs-AI Overlay Renderer` to `T02/T03 Batch Inference Runners`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `_selftest()` connect `T03 GT-vs-AI Overlay Renderer` to `T02/T03 Batch Inference Runners`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `find_image()` connect `T03 Dataset Builder (build_dataset_t03.py)` to `T02/T03 Batch Inference Runners`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `plan Pass (footing/column/beam/slab)` (e.g. with `Old Pass 1 I/O Spec (15 patterns)` and `Pass 0 Classifier Prompt (current)`) actually correct?**
  _`plan Pass (footing/column/beam/slab)` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fs`, `path`, `REPO_ROOT` to the rest of the system?**
  _70 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `T01 House 08-11 GPU-Rental Workflow` be split into smaller, more focused modules?**
  _Cohesion score 0.07539118065433854 - nodes in this community are weakly interconnected._