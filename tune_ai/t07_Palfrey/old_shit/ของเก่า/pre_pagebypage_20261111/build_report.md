# t07 Palfrey - build report (build_t07.py)

Variant: default (siamplan included, D2) · 168 houses · 3573 unique rows (pass1 2907, pass0 400, pass2.4 266). Gate: all checks passed. Everything below is MEASURED by this run unless it says INFERRED.

## Houses

| tree | scope | source | houses |
|---|---|---|---|
| corrected | full | non-siamplan | 19 |
| corrected | pass2_only | non-siamplan | 21 |
| raw | full | non-siamplan | 5 |
| raw | pass2_only | non-siamplan | 66 |
| raw | pass2_only | siamplan | 57 |

Exclusions (folder level):

| reason | folders |
|---|---|
| no data JSON (D1) | 3 |
| not a house folder | 2 |
| same 133-page drawing set as corrected บ้าน_เล็ก_1ชั้น_13, extracted twice with conflicting labels (D1) | 1 |
| superseded | 40 |

Held out (never in any fold): 58บ้าน_เล็ก_1ชั้น_20 - t05 test house บ้านไทยพอเพียง3 (byte-identical PDF); never in any fold (D1)

## Rows per subtask and kind

| subtask | kind | rows | houses |
|---|---|---|---|
| gridline | pass1 | 171 | 168 |
| notes | pass1 | 293 | 145 |
| pass0 | pass0 | 400 | 24 |
| plan_beam | pass1 | 494 | 166 |
| plan_beam | pass2.4 | 112 | 39 |
| plan_footing | pass1 | 380 | 168 |
| plan_footing | pass2.4 | 86 | 35 |
| plan_slab | pass1 | 262 | 158 |
| plan_slab | pass2.4 | 68 | 38 |
| schedule | pass1 | 255 | 128 |
| section | pass1 | 1052 | 166 |

pass0: 824 hazard-guarded rows from full-coverage houses, capped to 400 (water-filling, classes at or under the quota kept whole):

| view class | available | kept |
|---|---|---|
| index | 23 | 23 |
| material_list | 58 | 36 |
| material_list+material_list | 89 | 37 |
| misc | 39 | 36 |
| notes | 75 | 37 |
| plan_beam | 46 | 36 |
| plan_beam+plan_column | 1 | 1 |
| plan_beam+plan_slab | 1 | 1 |
| plan_footing | 22 | 22 |
| roof_plan | 20 | 20 |
| schedule | 54 | 36 |
| section | 269 | 37 |
| side_profile | 86 | 37 |
| site_plan | 23 | 23 |
| symbol | 4 | 4 |
| title | 14 | 14 |

## Folds (5 group-folds, folds 0-3 trained; fold 4 houses are in every train split)

| fold | houses | rows in fold | train rows | val rows | est. wall time (INFERRED) |
|---|---|---|---|---|---|
| 0 | 30 | 713 | 2860 | 713 | 7.1-8.8 h |
| 1 | 30 | 716 | 2857 | 716 | 7.1-8.8 h |
| 2 | 40 | 716 | 2857 | 716 | 7.1-8.8 h |
| 3 | 31 | 713 | 2860 | 713 | 7.1-8.8 h |
| 4 | 37 | 715 | - | - | - |

Wall time = train rows x 8.05-10.13 s per row-epoch (t05 fold0/fold3 measured) x EPOCHS=1 + 45 min setup. INFERRED. Mean row length: t07 13,043 tokens vs t05 train_fold0 13,088, so per-row time may scale by about 1.00x (INFERRED).

Rows per subtask in each fold (= the val split for folds 0-3):

| subtask | fold0 | fold1 | fold2 | fold3 | fold4 |
|---|---|---|---|---|---|
| gridline | 30 | 31 | 40 | 32 | 38 |
| notes | 67 | 52 | 52 | 58 | 64 |
| pass0 | 84 | 130 | 62 | 60 | 64 |
| plan_beam | 110 | 122 | 131 | 118 | 125 |
| plan_footing | 79 | 98 | 84 | 95 | 110 |
| plan_slab | 61 | 56 | 75 | 64 | 74 |
| schedule | 56 | 43 | 50 | 58 | 48 |
| section | 226 | 184 | 222 | 228 | 192 |

Houses per fold:

- fold0: บ้าน_เล็ก_1ชั้น_15, บ้าน_เล็ก_1ชั้น_18, บ้าน_เล็ก_1ชั้น_29, บ้าน_เล็ก_1ชั้น_42, บ้าน_เล็ก_1ชั้น_48, บ้าน_เล็ก_1ชั้น_51, บ้าน_เล็ก_1ชั้น_52, บ้าน_เล็ก_1ชั้น_58, บ้าน_เล็ก_1ชั้น_66, บ้าน_เล็ก_1ชั้น_69, บ้าน_เล็ก_2ชั้น_01, บ้าน_เล็ก_2ชั้น_02, บ้าน_เล็ก_2ชั้น_04, บ้าน_เล็ก_2ชั้น_28, บ้าน_เล็ก_2ชั้น_40, บ้าน_เล็ก_2ชั้น_43, บ้าน_ใหญ่_1ชั้น_07, บ้าน_ใหญ่_1ชั้น_13, บ้าน_ใหญ่_1ชั้น_14, บ้าน_ใหญ่_1ชั้น_15, บ้าน_ใหญ่_1ชั้น_17, บ้าน_ใหญ่_1ชั้น_18, บ้าน_ใหญ่_2ชั้น_05, บ้าน_ใหญ่_2ชั้น_07, บ้าน_ใหญ่_2ชั้น_16, บ้าน_ใหญ่_2ชั้น_20, บ้าน_ใหญ่_2ชั้น_25, บ้าน_ใหญ่_2ชั้น_27, บ้าน_ใหญ่_3ชั้น_01, บ้าน_ใหญ่_3ชั้น_07
- fold1: บ้าน_เล็ก_1ชั้น_03, บ้าน_เล็ก_1ชั้น_04, บ้าน_เล็ก_1ชั้น_05, บ้าน_เล็ก_1ชั้น_06, บ้าน_เล็ก_1ชั้น_07, บ้าน_เล็ก_1ชั้น_26, บ้าน_เล็ก_1ชั้น_35, บ้าน_เล็ก_1ชั้น_39, บ้าน_เล็ก_1ชั้น_43, บ้าน_เล็ก_1ชั้น_44, บ้าน_เล็ก_1ชั้น_53, บ้าน_เล็ก_1ชั้น_54, บ้าน_เล็ก_1ชั้น_63, บ้าน_เล็ก_1ชั้น_68, บ้าน_เล็ก_1ชั้น_71, บ้าน_เล็ก_2ชั้น_12, บ้าน_เล็ก_2ชั้น_13, บ้าน_เล็ก_2ชั้น_15, บ้าน_เล็ก_2ชั้น_20, บ้าน_เล็ก_2ชั้น_21, บ้าน_เล็ก_2ชั้น_30, บ้าน_เล็ก_2ชั้น_31, บ้าน_เล็ก_2ชั้น_44, บ้าน_ใหญ่_1ชั้น_01, บ้าน_ใหญ่_1ชั้น_02, บ้าน_ใหญ่_1ชั้น_06, บ้าน_ใหญ่_2ชั้น_03, บ้าน_ใหญ่_2ชั้น_19, บ้าน_ใหญ่_2ชั้น_24, บ้าน_ใหญ่_3ชั้น_08
- fold2: บ้าน_เล็ก_1ชั้น_01, บ้าน_เล็ก_1ชั้น_09, บ้าน_เล็ก_1ชั้น_16, บ้าน_เล็ก_1ชั้น_17, บ้าน_เล็ก_1ชั้น_21, บ้าน_เล็ก_1ชั้น_22, บ้าน_เล็ก_1ชั้น_25, บ้าน_เล็ก_1ชั้น_27, บ้าน_เล็ก_1ชั้น_36, บ้าน_เล็ก_1ชั้น_46, บ้าน_เล็ก_1ชั้น_55, บ้าน_เล็ก_1ชั้น_56, บ้าน_เล็ก_1ชั้น_57, บ้าน_เล็ก_1ชั้น_60, บ้าน_เล็ก_1ชั้น_61, บ้าน_เล็ก_1ชั้น_70, บ้าน_เล็ก_1ชั้น_73, บ้าน_เล็ก_2ชั้น_11, บ้าน_เล็ก_2ชั้น_16, บ้าน_เล็ก_2ชั้น_17, บ้าน_เล็ก_2ชั้น_22, บ้าน_เล็ก_2ชั้น_24, บ้าน_เล็ก_2ชั้น_25, บ้าน_เล็ก_2ชั้น_26, บ้าน_เล็ก_2ชั้น_27, บ้าน_เล็ก_2ชั้น_32, บ้าน_เล็ก_2ชั้น_33, บ้าน_เล็ก_2ชั้น_36, บ้าน_ใหญ่_1ชั้น_08, บ้าน_ใหญ่_1ชั้น_09, บ้าน_ใหญ่_1ชั้น_16, บ้าน_ใหญ่_2ชั้น_01, บ้าน_ใหญ่_2ชั้น_04, บ้าน_ใหญ่_2ชั้น_06, บ้าน_ใหญ่_2ชั้น_08, บ้าน_ใหญ่_2ชั้น_13, บ้าน_ใหญ่_2ชั้น_15, บ้าน_ใหญ่_2ชั้น_18, บ้าน_ใหญ่_3ชั้น_04, บ้าน_ใหญ่_4ชั้น_01
- fold3: บ้าน_เล็ก_1ชั้น_02, บ้าน_เล็ก_1ชั้น_10, บ้าน_เล็ก_1ชั้น_13, บ้าน_เล็ก_1ชั้น_19, บ้าน_เล็ก_1ชั้น_24, บ้าน_เล็ก_1ชั้น_34, บ้าน_เล็ก_1ชั้น_37, บ้าน_เล็ก_1ชั้น_40, บ้าน_เล็ก_1ชั้น_41, บ้าน_เล็ก_1ชั้น_49, บ้าน_เล็ก_1ชั้น_59, บ้าน_เล็ก_1ชั้น_62, บ้าน_เล็ก_1ชั้น_65, บ้าน_เล็ก_2ชั้น_03, บ้าน_เล็ก_2ชั้น_05, บ้าน_เล็ก_2ชั้น_06, บ้าน_เล็ก_2ชั้น_07, บ้าน_เล็ก_2ชั้น_14, บ้าน_เล็ก_2ชั้น_18, บ้าน_เล็ก_2ชั้น_23, บ้าน_เล็ก_2ชั้น_29, บ้าน_เล็ก_2ชั้น_34, บ้าน_เล็ก_2ชั้น_37, บ้าน_เล็ก_2ชั้น_39, บ้าน_ใหญ่_1ชั้น_10, บ้าน_ใหญ่_1ชั้น_11, บ้าน_ใหญ่_1ชั้น_19, บ้าน_ใหญ่_2ชั้น_09, บ้าน_ใหญ่_2ชั้น_11, บ้าน_ใหญ่_2ชั้น_21, บ้าน_ใหญ่_3ชั้น_09
- fold4: บ้าน_เล็ก_1ชั้น_08, บ้าน_เล็ก_1ชั้น_11, บ้าน_เล็ก_1ชั้น_12, บ้าน_เล็ก_1ชั้น_23, บ้าน_เล็ก_1ชั้น_28, บ้าน_เล็ก_1ชั้น_30, บ้าน_เล็ก_1ชั้น_31, บ้าน_เล็ก_1ชั้น_32, บ้าน_เล็ก_1ชั้น_33, บ้าน_เล็ก_1ชั้น_38, บ้าน_เล็ก_1ชั้น_45, บ้าน_เล็ก_1ชั้น_47, บ้าน_เล็ก_1ชั้น_50, บ้าน_เล็ก_1ชั้น_64, บ้าน_เล็ก_1ชั้น_67, บ้าน_เล็ก_2ชั้น_08, บ้าน_เล็ก_2ชั้น_09, บ้าน_เล็ก_2ชั้น_10, บ้าน_เล็ก_2ชั้น_19, บ้าน_เล็ก_2ชั้น_35, บ้าน_เล็ก_2ชั้น_38, บ้าน_เล็ก_2ชั้น_41, บ้าน_เล็ก_2ชั้น_42, บ้าน_ใหญ่_1ชั้น_03, บ้าน_ใหญ่_1ชั้น_04, บ้าน_ใหญ่_1ชั้น_05, บ้าน_ใหญ่_1ชั้น_12, บ้าน_ใหญ่_2ชั้น_02, บ้าน_ใหญ่_2ชั้น_10, บ้าน_ใหญ่_2ชั้น_12, บ้าน_ใหญ่_2ชั้น_17, บ้าน_ใหญ่_2ชั้น_22, บ้าน_ใหญ่_2ชั้น_23, บ้าน_ใหญ่_2ชั้น_26, บ้าน_ใหญ่_3ชั้น_03, บ้าน_ใหญ่_3ชั้น_05, บ้าน_ใหญ่_3ชั้น_06

Groups with more than one house (union-find over D8 evidence):

| fold | members | evidence |
|---|---|---|
| 2 | บ้าน_เล็ก_1ชั้น_01 บ้าน_เล็ก_1ชั้น_25 | _scope R72~01 |
| 1 | บ้าน_เล็ก_1ชั้น_03 บ้าน_เล็ก_1ชั้น_04 | C08 C09 |
| 4 | บ้าน_เล็ก_1ชั้น_08 บ้าน_เล็ก_2ชั้น_08 บ้าน_เล็ก_2ชั้น_09 บ้าน_เล็ก_2ชั้น_10 | บ้านสำเร็จรูป C19 C23 C28 C29 |
| 4 | บ้าน_เล็ก_1ชั้น_11 บ้าน_เล็ก_1ชั้น_12 บ้าน_เล็ก_1ชั้น_23 | _scope R69~11; ห่วงใยไทยประชาสุขใจ C18 C24 R69 |
| 2 | บ้าน_เล็ก_1ชั้น_16 บ้าน_เล็ก_1ชั้น_17 บ้าน_เล็ก_1ชั้น_21 บ้าน_เล็ก_1ชั้น_22 บ้าน_เล็ก_2ชั้น_24 บ้าน_เล็ก_2ชั้น_25 บ้าน_เล็ก_2ชั้น_26 บ้าน_เล็ก_2ชั้น_27 | _scope R52~R51; _scope R63~R62; ไทยพอเพียง C39 C40 R59-R64 |
| 4 | บ้าน_เล็ก_1ชั้น_31 บ้าน_เล็ก_1ชั้น_32 บ้าน_เล็ก_1ชั้น_33 | _scope R92~R90 R91 |
| 0 | บ้าน_เล็ก_2ชั้น_02 บ้าน_เล็ก_2ชั้น_04 บ้าน_เล็ก_2ชั้น_28 | C04 C17 R73; _scope R73~02 |
| 3 | บ้าน_เล็ก_2ชั้น_03 บ้าน_เล็ก_2ชั้น_05 บ้าน_เล็ก_2ชั้น_29 | C05 C26 R76; _scope R76~03 |
| 0 | บ้าน_ใหญ่_1ชั้น_07 บ้าน_ใหญ่_1ชั้น_17 | _scope OBEC R161~R123 (weaker: same family) |
| 2 | บ้าน_ใหญ่_1ชั้น_09 บ้าน_ใหญ่_1ชั้น_16 | _scope OBEC R159~R125 (weaker: same family) |
| 3 | บ้าน_ใหญ่_1ชั้น_11 บ้าน_ใหญ่_2ชั้น_21 | _scope OBEC R163~R128 (weaker: same family) |
| 4 | บ้าน_ใหญ่_2ชั้น_10 บ้าน_ใหญ่_2ชั้น_12 | R66 R68; _scope R68~R66 |
| 2 | บ้าน_ใหญ่_2ชั้น_13 บ้าน_ใหญ่_3ชั้น_04 บ้าน_ใหญ่_4ชั้น_01 | _scope R74 R75~R71 |

## Length gate (t05 trainer preflight arithmetic)

Calibration: t05 train_fold0 longest row = 39,220 tokens, the logged preflight value. Limit 0.95 x 47,104 = 44,749. Longest t07 row 35,093 (25.5% below MAX_LENGTH), rows over the limit: 0.

| subtask | rows | max | p99 | median | mean |
|---|---|---|---|---|---|
| gridline | 171 | 34971 | 33777 | 32316 | 29001 |
| notes | 293 | 14621 | 12526 | 11335 | 11322 |
| pass0 | 400 | 9529 | 9485 | 8913 | 8801 |
| plan_beam | 606 | 35093 | 29068 | 14321 | 15156 |
| plan_footing | 466 | 16382 | 14510 | 12641 | 12714 |
| plan_slab | 330 | 19498 | 17100 | 12807 | 12995 |
| schedule | 255 | 15020 | 14058 | 11045 | 11025 |
| section | 1052 | 16937 | 15507 | 11768 | 11974 |

Top 10 rows:

| tokens | visual | subtask | id |
|---|---|---|---|
| 35093 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_25::บ้าน_ใหญ่_2ชั้น_25_หน้า29_view1_beam_plan::plan_beam |
| 34971 | 27648 | gridline | บ้าน_ใหญ่_2ชั้น_27::บ้าน_ใหญ่_2ชั้น_27_หน้า00_gridline::gridline |
| 34901 | 27648 | gridline | บ้าน_ใหญ่_3ชั้น_09::บ้าน_ใหญ่_3ชั้น_09_หน้า00_gridline::gridline |
| 33978 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_27::บ้าน_ใหญ่_2ชั้น_27_หน้า38_view1_beam_plan::plan_beam |
| 33777 | 27648 | gridline | บ้าน_เล็ก_2ชั้น_02::บ้าน_เล็ก_2ชั้น_02_หน้า00_gridline::gridline |
| 33493 | 27648 | gridline | บ้าน_เล็ก_2ชั้น_03::บ้าน_เล็ก_2ชั้น_03_หน้า00_gridline::gridline |
| 33486 | 27648 | gridline | บ้าน_ใหญ่_2ชั้น_26::บ้าน_ใหญ่_2ชั้น_26_หน้า00_gridline::gridline |
| 33296 | 27648 | gridline | บ้าน_ใหญ่_2ชั้น_21::บ้าน_ใหญ่_2ชั้น_21_หน้า00_gridline::gridline |
| 32929 | 27648 | gridline | บ้าน_เล็ก_2ชั้น_01::บ้าน_เล็ก_2ชั้น_01_หน้า00_gridline::gridline |
| 32927 | 27648 | gridline | บ้าน_ใหญ่_2ชั้น_23::บ้าน_ใหญ่_2ชั้น_23_หน้า00_gridline::gridline |

## What the build removed

Top-level keys dropped by the KEYS.json allowlist (label count):

| subtask.key | labels |
|---|---|
| section.png | 1052 |
| section.doc_page | 1052 |
| section.source_image | 1052 |
| section.view_title | 788 |
| section.grid_source | 617 |
| section.scale | 594 |
| plan_beam.png | 494 |
| plan_beam.doc_page | 494 |
| plan_beam.source_image | 494 |
| plan_beam.grid_source | 494 |
| plan_footing.png | 380 |
| plan_footing.doc_page | 380 |
| plan_footing.source_image | 380 |
| plan_footing.grid_source | 380 |
| section.views | 348 |
| plan_beam.scale | 347 |
| notes.png | 293 |
| notes.doc_page | 293 |
| notes.source_image | 293 |
| plan_footing.scale | 274 |
| plan_slab.png | 262 |
| plan_slab.doc_page | 262 |
| plan_slab.source_image | 262 |
| plan_slab.grid_source | 262 |
| schedule.png | 255 |
| schedule.doc_page | 255 |
| schedule.source_image | 255 |
| section.schema_generation | 240 |
| plan_beam.views | 220 |
| notes.view_title | 198 |
| schedule.view_title | 191 |
| plan_slab.scale | 177 |
| notes.views | 155 |
| plan_footing.views | 149 |
| schedule.scale | 130 |
| notes.scale | 118 |
| section.building | 114 |
| notes.elements | 106 |
| plan_slab.views | 105 |
| section.printed_page | 97 |

notes labels that carried a top-level `elements` list (not in the notes prompt, so dropped): 23 labels, 272 non-structural elements.

Nested D5 scrub (sanitize_labels.scrub): drop_item 2304, drop_key 360, drop_text 97

Nested key occurrences removed by the scrub (top 30, subtask.key):

| subtask.key | removed |
|---|---|
| section.spec_source | 145 |
| section.spec_confidence_score | 140 |
| section.note | 41 |
| plan_beam.note | 38 |
| plan_beam.spec_source | 26 |
| plan_beam.spec_confidence_score | 26 |
| plan_footing.spec_source | 9 |
| plan_footing.spec_confidence_score | 9 |
| plan_slab.note | 7 |
| plan_footing.note | 6 |
| schedule.spec_source | 3 |
| section.description | 2 |
| section.spec_confidence_flags | 2 |
| section.location | 1 |
| schedule.note | 1 |
| plan_footing.offset_note | 1 |

Label rows with a sanitize gate hit BEFORE the scrub (kind, marker):

| kind | marker | rows |
|---|---|---|
| pass1 | ADDED_ | 15 |
| pass1 | CASCADE_ | 5 |
| pass1 | CORRECTED_ | 38 |
| pass1 | MERGED_ | 4 |
| pass1 | NORMALIZED | 194 |
| pass1 | RESOLVED_ | 3 |
| pass1 | RETRACTED | 3 |
| pass1 | added_by | 10 |
| pass1 | by_user | 33 |
| pass1 | carry_forward | 6 |
| pass1 | claude | 2 |
| pass1 | dataset_meta | 60 |
| pass1 | file_ref | 285 |
| pass1 | house_name | 26 |
| pass1 | house_ref | 562 |
| pass1 | iso_date | 500 |
| pass1 | mk_test | 1 |
| pass1 | op_fix | 2 |
| pass1 | op_round | 124 |
| pass1 | person | 38 |
| pass1 | rawjson_ | 21 |
| pass1 | relabel_note | 296 |
| pass1 | reviewer | 5 |
| pass1 | t_round | 20 |
| pass1 | user | 18 |

Routing / skip counters:

| counter | n |
|---|---|
| grid_line_pos_m_not_number | 2 |
| gridline_images_1 | 12 |
| gridline_images_2 | 14 |
| gridline_images_3 | 12 |
| gridline_images_4 | 133 |
| not_pass1_material_list | 544 |
| not_pass1_pattern:etc_plan | 242 |
| not_pass1_pattern:index | 66 |
| not_pass1_pattern:misc | 39 |
| not_pass1_pattern:roof_plan | 27 |
| not_pass1_pattern:side_profile | 159 |
| not_pass1_pattern:site_plan | 23 |
| not_pass1_pattern:symbol | 50 |
| not_pass1_pattern:title | 14 |
| not_pass1_pattern:unknown | 1 |
| pass0_candidate_rows_sheet_list_no | 278 |
| pass0_candidate_rows_sheet_list_yes | 235 |
| pass0_material_list_2sheet | 89 |
| pass0_sheet_list_house_without_usable_index | 10 |
| pass0_skip_multi_file_page | 365 |
| pass0_skip_only_viewN_fragment | 2 |
| pass0_skip_page_00 | 25 |
| pass0_skip_pattern_underivable | 135 |
| plan_files_string_views (t04 views bug) | 313 |
| skip_pass24_old_format_hint | 18 |
| skip_plan_no_matching_elements | 1 |
| z_entry_level_not_number | 87 |
| z_entry_source_page_not_in_images | 485 |
| z_id_number_only_to_null | 125 |
| z_id_slug_to_null | 10 |
| z_type_mapped:beam_top | 25 |
| z_type_mapped:floor | 6 |
| z_type_mapped:landing | 3 |
| z_type_named_without_id_to_dummy | 80 |

GRID MASTER selection for plan rows: by_building_field 28, default_main_master 6, only_master 1102

## 2026-11-11 afternoon: gridline z_levels (slim) + pass0 SHEET LIST

Before this change (first build, 2026-11-11 01:46; its data is kept in `data_20261111_0146/` and `data_raw_20261111_0146/`, its report in `build_report_20261111_0146.md`): gridline rows with z 0, pass0 rows with the sheet list 0, longest gridline row 34,503 tokens, longest pass0 row 8,961, 3,573 rows, same houses, same folds (row counts per house do not change, so the fold assignment does not).

gridline rows 171: **124 carry `z_levels`**, 47 do not. GT z entries on those rows' masters: 1208, kept in labels: 636 (an entry stays only if its own source page is among the row's images, level_m is a number, id passes the leak gate).

Rows by z outcome:

| outcome | gridline rows |
|---|---|
| no_z_gt_has_no_z_levels | 5 |
| no_z_gt_z_levels_empty | 4 |
| no_z_levels_page_not_among_row_images | 36 |
| no_z_no_numeric_level_m | 2 |
| with_z_all_entries | 29 |
| with_z_partial | 95 |

Entries dropped (entry level, before the row decision):

| reason | entries |
|---|---|
| z_entry_level_not_number | 87 |
| z_entry_source_page_not_in_images | 485 |

type mapped to the prompt's datum/named/dummy (old GT vocabulary): {'beam_top': 25, 'floor': 6, 'landing': 3} (named when the level has a printed id, dummy otherwise). id set to null because it was the bare number or a snake_case slug, not a printed label (the prompt says number-only -> null): {'number_only': 125, 'slug': 10}; `named` with no id (after that, or in GT) changed to `dummy`, because the prompt says named = a labelled level: 80. Exact duplicates dropped after that: 0.

pass0: 400 rows (cap 400 unchanged), **123 carry the SHEET LIST tail**; 14 houses have a usable index page, 250 of the kept rows belong to them (about half get the tail: even parity of sha256(row id)). Before the cap: {'with_list': 235, 'without_list': 278}. Full-coverage houses without a usable index page: 10; houses whose list was dropped by the leak gate: 0.

Index page used per house (lowest-numbered index file whose sections carry `sheet_range`):

| house | index file | entries |
|---|---|---|
| บ้าน_เล็ก_1ชั้น_01 | บ้าน_เล็ก_1ชั้น_01_หน้า02.json | 8 |
| บ้าน_เล็ก_1ชั้น_02 | บ้าน_เล็ก_1ชั้น_02_หน้า03_index.json | 19 |
| บ้าน_เล็ก_1ชั้น_03 | บ้าน_เล็ก_1ชั้น_03_หน้า02.json | 8 |
| บ้าน_เล็ก_1ชั้น_04 | บ้าน_เล็ก_1ชั้น_04_หน้า02.json | 8 |
| บ้าน_เล็ก_1ชั้น_10 | บ้าน_เล็ก_1ชั้น_10_หน้า02_view1_index.json | 2 |
| บ้าน_เล็ก_1ชั้น_12 | บ้าน_เล็ก_1ชั้น_12_หน้า02_index.json | 7 |
| บ้าน_เล็ก_2ชั้น_01 | บ้าน_เล็ก_2ชั้น_01_หน้า03_index.json | 25 |
| บ้าน_เล็ก_2ชั้น_02 | บ้าน_เล็ก_2ชั้น_02_หน้า03_index.json | 27 |
| บ้าน_เล็ก_2ชั้น_03 | บ้าน_เล็ก_2ชั้น_03_หน้า03_index.json | 26 |
| บ้าน_เล็ก_2ชั้น_04 | บ้าน_เล็ก_2ชั้น_04_หน้า02_index.json | 8 |
| บ้าน_เล็ก_2ชั้น_07 | บ้าน_เล็ก_2ชั้น_07_หน้า02.json | 8 |
| บ้าน_เล็ก_2ชั้น_11 | บ้าน_เล็ก_2ชั้น_11_หน้า02_view1_index.json | 2 |
| บ้าน_ใหญ่_2ชั้น_02 | บ้าน_ใหญ่_2ชั้น_02_หน้า02_view1_index.json | 4 |
| บ้าน_ใหญ่_3ชั้น_03 | บ้าน_ใหญ่_3ชั้น_03_หน้า02_view1_index.json | 2 |

## Gates

- worker parity: OK (worker.py: 7 prompts + pass0 identical, SUBTASK_PATTERN equal, tail/hint code present)
- sanitize_labels.py (second net): selftest ok; 8/8 files ด่าน: ผ่าน, หลังล้าง 0; rows it changed: 0
- final verify on data/: 3573 unique rows, 7146 text parts, 2374 images opened (bad 0); regex hits 0; keys outside allowlist 0; plan pattern not normalized 0; gridline shape violations 0; plan tails equal to a gridline label of the same house 1402 (tails whose master has no gridline row: 0)
- held-out page overlap (INFO, survey fingerprints): {"status": "from fp_pairs.json (survey, read-only)", "rows_with_near_dup_page": 77, "rows_with_identical_dhash_page": 7, "houses": ["บ้าน_เล็ก_1ชั้น_01", "บ้าน_เล็ก_1ชั้น_02", "บ้าน_เล็ก_1ชั้น_03", "บ้าน_เล็ก_1ชั้น_04", "บ้าน_เล็ก_1ชั้น_05", "บ้าน_เล็ก_1ชั้น_08", "บ้าน_เล็ก_1ชั้น_11", "บ้าน_เล็ก_1ชั้น_12", "บ้าน_เล็ก_1ชั้น_16", "บ้าน_เล็ก_1ชั้น_17", "บ้าน_เล็ก_1ชั้น_21", "บ้าน_เล็ก_1ชั้น_22", "บ้าน_เล็ก_1ชั้น_23", "บ้าน_เล็ก_1ชั้น_25", "บ้าน_เล็ก_2ชั้น_01", "บ้าน_เล็ก_2ชั้น_02", "บ้าน_เล็ก_2ชั้น_03", "บ้าน_เล็ก_2ชั้น_04", "บ้าน_เล็ก_2ชั้น_05", "บ้าน_เล็ก_2ชั้น_06", "บ้าน_เล็ก_2ชั้น_07", "บ้าน_เล็ก_2ชั้น_08", "บ้าน_เล็ก_2ชั้น_09", "บ้าน_เล็ก_2ชั้น_10", "บ้าน_เล็ก_2ชั้น_24", "บ้าน_เล็ก_2ชั้น_25", "บ้าน_เล็ก_2ชั้น_26", "บ้าน_เล็ก_2ชั้น_27", "บ้าน_เล็ก_2ชั้น_28", "บ้าน_เล็ก_2ชั้น_29", "บ้าน_ใหญ่_1ชั้น_02", "บ้าน_ใหญ่_1ชั้น_03", "บ้าน_ใหญ่_2ชั้น_01"]}
- bench design names in text (INFO): 0
- siamplan-excluded variant: {"houses": 111, "corrected": 40, "raw_only": 71, "rows": 2842, "rows_per_kind": {"pass0": 400, "pass1": 2176, "pass2.4": 266}, "rows_per_subtask": {"gridline": 114, "notes": 246, "pass0": 400, "plan_beam": 444, "plan_footing": 325, "plan_slab": 259, "schedule": 200, "section": 854}, "fold_rows": [570, 570, 567, 569, 566], "groups": 87, "train_val_per_fold": {"0": [2272, 570], "1": [2272, 570], "2": [2275, 567], "3": [2273, 569]}}

## Problems

none

## Output sha256

| file | sha256 |
|---|---|
| data/train_fold0.jsonl | 3413ecd5cbe403b6e24673e84cc781b822ee23f1235c00417a0e271871f2ab72 |
| data/train_fold1.jsonl | 4ff1279f32b224f581ce9a9057a0b1683d893ecb87c331b57f258a52a676b0f6 |
| data/train_fold2.jsonl | 2dfd7ccb5c5ee10a867f9afaf0773d129d7a0d75aba9272e38b8ecfa474eaae6 |
| data/train_fold3.jsonl | a7117ef3ef654f556848785340412632e7f2ae187fa7d03cad6e5f55ff429bc0 |
| data/val_fold0.jsonl | 58ff4e13179dbb3d5074a630c85586630b3ac64b6cf9da654bb9b22af7b1108c |
| data/val_fold1.jsonl | 3814c6d8b6b989e8edcce1792e658c75a41ee72df3e35e16764789584b4415b8 |
| data/val_fold2.jsonl | 49812594d226220a78c79337f99b280482bd712bdba42aaf0dab9f6b4b80813d |
| data/val_fold3.jsonl | f4285e10a23b97a74a141b4062111af34284ef3231b0fe7c53e322f0fb8b7343 |
| data_raw/train_fold0.jsonl | 30b2f7d9af76ca5fad6cb53ea22954c9c2de72b3bf65a0519004ce642da596f8 |
| data_raw/train_fold1.jsonl | 179dcbd3d4743a35e5b0b1dba4f27607f4bad13c630d89c52bd1fb0e063ceb94 |
| data_raw/train_fold2.jsonl | 24a14c3b9070eb504329265937a113bf1e11c98b0484bbec95ef54cf35ca5176 |
| data_raw/train_fold3.jsonl | 0df18d73356884254606737127a5ee9d132c0d35f878e7c4e2c2553107e516c3 |
| data_raw/val_fold0.jsonl | b26fa8099b7db2e6000694e8562985f519ea75e0ba12bb6418b49ea7818ebe2f |
| data_raw/val_fold1.jsonl | 737674c0f78e158b07098796b9280898a343799620d07376da1e5bd6cf07d16d |
| data_raw/val_fold2.jsonl | 8e1e2c506a5c673f71d13fc68c6453407a03c6c4a647c9ca9a120a0a99e598e2 |
| data_raw/val_fold3.jsonl | 9619958465ca49b614ce0709cdce04f560c7a42bf38d2b4bbd7c374015f0b35a |
