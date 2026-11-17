# t07 Palfrey - build report (build_t07.py)

Variant: siamplan EXCLUDED · 111 houses · 3417 unique rows (pass1 2751, pass0 400, pass2.4 266). Gate: all checks passed. Everything below is MEASURED by this run unless it says INFERRED.

## Houses

| tree | scope | source | houses |
|---|---|---|---|
| corrected | full | non-siamplan | 19 |
| corrected | pass2_only | non-siamplan | 21 |
| raw | full | non-siamplan | 5 |
| raw | pass2_only | non-siamplan | 66 |

Exclusions (folder level):

| reason | folders |
|---|---|
| --exclude-source siamplan (D2 variant) | 57 |
| no data JSON (D1) | 3 |
| not a house folder | 2 |
| same 133-page drawing set as corrected บ้าน_เล็ก_1ชั้น_13, extracted twice with conflicting labels (D1) | 1 |
| superseded | 40 |

Held out (never in any fold): 58บ้าน_เล็ก_1ชั้น_20 - t05 test house บ้านไทยพอเพียง3 (byte-identical PDF); never in any fold (D1)

## Rows per subtask and kind

| subtask | kind | rows | houses |
|---|---|---|---|
| gridline | pass1 | 689 | 99 |
| notes | pass1 | 246 | 98 |
| pass0 | pass0 | 400 | 24 |
| plan_beam | pass1 | 332 | 109 |
| plan_beam | pass2.4 | 112 | 39 |
| plan_footing | pass1 | 239 | 111 |
| plan_footing | pass2.4 | 86 | 35 |
| plan_slab | pass1 | 191 | 101 |
| plan_slab | pass2.4 | 68 | 38 |
| schedule | pass1 | 200 | 81 |
| section | pass1 | 854 | 109 |

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
| 0 | 21 | 682 | 2735 | 682 | 6.9-8.4 h |
| 1 | 25 | 685 | 2732 | 685 | 6.9-8.4 h |
| 2 | 20 | 684 | 2733 | 684 | 6.9-8.4 h |
| 3 | 22 | 684 | 2733 | 684 | 6.9-8.4 h |
| 4 | 23 | 682 | - | - | - |

Wall time = train rows x 8.05-10.13 s per row-epoch (t05 fold0/fold3 measured) x EPOCHS=1 + 45 min setup. INFERRED. Mean row length: t07 11,838 tokens vs t05 train_fold0 13,088, so per-row time may scale by about 0.90x (INFERRED).

Rows per subtask in each fold (= the val split for folds 0-3):

| subtask | fold0 | fold1 | fold2 | fold3 | fold4 |
|---|---|---|---|---|---|
| gridline | 153 | 148 | 135 | 156 | 97 |
| notes | 43 | 49 | 48 | 48 | 58 |
| pass0 | 80 | 66 | 109 | 57 | 88 |
| plan_beam | 85 | 85 | 79 | 89 | 106 |
| plan_footing | 58 | 58 | 61 | 61 | 87 |
| plan_slab | 55 | 56 | 41 | 50 | 57 |
| schedule | 43 | 40 | 43 | 40 | 34 |
| section | 165 | 183 | 168 | 183 | 155 |

Houses per fold:

- fold0: บ้าน_เล็ก_1ชั้น_09, บ้าน_เล็ก_1ชั้น_57, บ้าน_เล็ก_1ชั้น_73, บ้าน_เล็ก_2ชั้น_01, บ้าน_เล็ก_2ชั้น_02, บ้าน_เล็ก_2ชั้น_04, บ้าน_เล็ก_2ชั้น_06, บ้าน_เล็ก_2ชั้น_19, บ้าน_เล็ก_2ชั้น_28, บ้าน_ใหญ่_1ชั้น_04, บ้าน_ใหญ่_1ชั้น_08, บ้าน_ใหญ่_1ชั้น_09, บ้าน_ใหญ่_1ชั้น_14, บ้าน_ใหญ่_1ชั้น_16, บ้าน_ใหญ่_1ชั้น_19, บ้าน_ใหญ่_2ชั้น_13, บ้าน_ใหญ่_2ชั้น_16, บ้าน_ใหญ่_2ชั้น_20, บ้าน_ใหญ่_3ชั้น_04, บ้าน_ใหญ่_3ชั้น_06, บ้าน_ใหญ่_4ชั้น_01
- fold1: บ้าน_เล็ก_1ชั้น_02, บ้าน_เล็ก_1ชั้น_05, บ้าน_เล็ก_1ชั้น_10, บ้าน_เล็ก_1ชั้น_15, บ้าน_เล็ก_1ชั้น_16, บ้าน_เล็ก_1ชั้น_17, บ้าน_เล็ก_1ชั้น_18, บ้าน_เล็ก_1ชั้น_21, บ้าน_เล็ก_1ชั้น_22, บ้าน_เล็ก_2ชั้น_15, บ้าน_เล็ก_2ชั้น_16, บ้าน_เล็ก_2ชั้น_20, บ้าน_เล็ก_2ชั้น_24, บ้าน_เล็ก_2ชั้น_25, บ้าน_เล็ก_2ชั้น_26, บ้าน_เล็ก_2ชั้น_27, บ้าน_เล็ก_2ชั้น_32, บ้าน_ใหญ่_1ชั้น_05, บ้าน_ใหญ่_2ชั้น_04, บ้าน_ใหญ่_2ชั้น_05, บ้าน_ใหญ่_2ชั้น_22, บ้าน_ใหญ่_2ชั้น_23, บ้าน_ใหญ่_2ชั้น_24, บ้าน_ใหญ่_3ชั้น_07, บ้าน_ใหญ่_3ชั้น_09
- fold2: บ้าน_เล็ก_1ชั้น_01, บ้าน_เล็ก_1ชั้น_03, บ้าน_เล็ก_1ชั้น_04, บ้าน_เล็ก_1ชั้น_24, บ้าน_เล็ก_1ชั้น_25, บ้าน_เล็ก_1ชั้น_59, บ้าน_เล็ก_2ชั้น_07, บ้าน_เล็ก_2ชั้น_11, บ้าน_เล็ก_2ชั้น_18, บ้าน_เล็ก_2ชั้น_22, บ้าน_ใหญ่_1ชั้น_02, บ้าน_ใหญ่_1ชั้น_03, บ้าน_ใหญ่_1ชั้น_10, บ้าน_ใหญ่_2ชั้น_03, บ้าน_ใหญ่_2ชั้น_07, บ้าน_ใหญ่_2ชั้น_15, บ้าน_ใหญ่_2ชั้น_19, บ้าน_ใหญ่_2ชั้น_26, บ้าน_ใหญ่_3ชั้น_05, บ้าน_ใหญ่_3ชั้น_08
- fold3: บ้าน_เล็ก_1ชั้น_58, บ้าน_เล็ก_2ชั้น_03, บ้าน_เล็ก_2ชั้น_05, บ้าน_เล็ก_2ชั้น_14, บ้าน_เล็ก_2ชั้น_17, บ้าน_เล็ก_2ชั้น_29, บ้าน_เล็ก_2ชั้น_30, บ้าน_เล็ก_2ชั้น_31, บ้าน_ใหญ่_1ชั้น_07, บ้าน_ใหญ่_1ชั้น_12, บ้าน_ใหญ่_1ชั้น_13, บ้าน_ใหญ่_1ชั้น_17, บ้าน_ใหญ่_2ชั้น_01, บ้าน_ใหญ่_2ชั้น_06, บ้าน_ใหญ่_2ชั้น_08, บ้าน_ใหญ่_2ชั้น_10, บ้าน_ใหญ่_2ชั้น_11, บ้าน_ใหญ่_2ชั้น_12, บ้าน_ใหญ่_2ชั้น_18, บ้าน_ใหญ่_2ชั้น_25, บ้าน_ใหญ่_2ชั้น_27, บ้าน_ใหญ่_3ชั้น_03
- fold4: บ้าน_เล็ก_1ชั้น_06, บ้าน_เล็ก_1ชั้น_07, บ้าน_เล็ก_1ชั้น_08, บ้าน_เล็ก_1ชั้น_11, บ้าน_เล็ก_1ชั้น_12, บ้าน_เล็ก_1ชั้น_13, บ้าน_เล็ก_1ชั้น_19, บ้าน_เล็ก_1ชั้น_23, บ้าน_เล็ก_2ชั้น_08, บ้าน_เล็ก_2ชั้น_09, บ้าน_เล็ก_2ชั้น_10, บ้าน_เล็ก_2ชั้น_12, บ้าน_เล็ก_2ชั้น_13, บ้าน_เล็ก_2ชั้น_21, บ้าน_เล็ก_2ชั้น_23, บ้าน_ใหญ่_1ชั้น_01, บ้าน_ใหญ่_1ชั้น_11, บ้าน_ใหญ่_1ชั้น_15, บ้าน_ใหญ่_1ชั้น_18, บ้าน_ใหญ่_2ชั้น_02, บ้าน_ใหญ่_2ชั้น_09, บ้าน_ใหญ่_2ชั้น_21, บ้าน_ใหญ่_3ชั้น_01

Groups with more than one house (union-find over D8 evidence):

| fold | members | evidence |
|---|---|---|
| 2 | บ้าน_เล็ก_1ชั้น_01 บ้าน_เล็ก_1ชั้น_25 | _scope R72~01 |
| 2 | บ้าน_เล็ก_1ชั้น_03 บ้าน_เล็ก_1ชั้น_04 | C08 C09 |
| 4 | บ้าน_เล็ก_1ชั้น_08 บ้าน_เล็ก_2ชั้น_08 บ้าน_เล็ก_2ชั้น_09 บ้าน_เล็ก_2ชั้น_10 | บ้านสำเร็จรูป C19 C23 C28 C29 |
| 4 | บ้าน_เล็ก_1ชั้น_11 บ้าน_เล็ก_1ชั้น_12 บ้าน_เล็ก_1ชั้น_23 | _scope R69~11; ห่วงใยไทยประชาสุขใจ C18 C24 R69 |
| 1 | บ้าน_เล็ก_1ชั้น_16 บ้าน_เล็ก_1ชั้น_17 บ้าน_เล็ก_1ชั้น_21 บ้าน_เล็ก_1ชั้น_22 บ้าน_เล็ก_2ชั้น_24 บ้าน_เล็ก_2ชั้น_25 บ้าน_เล็ก_2ชั้น_26 บ้าน_เล็ก_2ชั้น_27 | _scope R52~R51; _scope R63~R62; ไทยพอเพียง C39 C40 R59-R64 |
| 0 | บ้าน_เล็ก_2ชั้น_02 บ้าน_เล็ก_2ชั้น_04 บ้าน_เล็ก_2ชั้น_28 | C04 C17 R73; _scope R73~02 |
| 3 | บ้าน_เล็ก_2ชั้น_03 บ้าน_เล็ก_2ชั้น_05 บ้าน_เล็ก_2ชั้น_29 | C05 C26 R76; _scope R76~03 |
| 3 | บ้าน_ใหญ่_1ชั้น_07 บ้าน_ใหญ่_1ชั้น_17 | _scope OBEC R161~R123 (weaker: same family) |
| 0 | บ้าน_ใหญ่_1ชั้น_09 บ้าน_ใหญ่_1ชั้น_16 | _scope OBEC R159~R125 (weaker: same family) |
| 4 | บ้าน_ใหญ่_1ชั้น_11 บ้าน_ใหญ่_2ชั้น_21 | _scope OBEC R163~R128 (weaker: same family) |
| 3 | บ้าน_ใหญ่_2ชั้น_10 บ้าน_ใหญ่_2ชั้น_12 | R66 R68; _scope R68~R66 |
| 0 | บ้าน_ใหญ่_2ชั้น_13 บ้าน_ใหญ่_3ชั้น_04 บ้าน_ใหญ่_4ชั้น_01 | _scope R74 R75~R71 |

## Length gate (t05 trainer preflight arithmetic)

Calibration: t05 train_fold0 longest row = 39,220 tokens, the logged preflight value. Limit 0.95 x 47,104 = 44,749. Longest t07 row 35,093 (25.5% below MAX_LENGTH), rows over the limit: 0.

| subtask | rows | max | p99 | median | mean |
|---|---|---|---|---|---|
| gridline | 689 | 13783 | 12922 | 10827 | 10856 |
| notes | 246 | 14621 | 12474 | 11238 | 11111 |
| pass0 | 400 | 9529 | 9485 | 8913 | 8801 |
| plan_beam | 444 | 35093 | 30138 | 14396 | 15342 |
| plan_footing | 325 | 16382 | 14525 | 12740 | 12799 |
| plan_slab | 259 | 19498 | 17608 | 12889 | 13093 |
| schedule | 200 | 15020 | 14186 | 10999 | 10964 |
| section | 854 | 16937 | 15560 | 11716 | 11898 |

Top 10 rows:

| tokens | visual | subtask | id |
|---|---|---|---|
| 35093 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_25::บ้าน_ใหญ่_2ชั้น_25_หน้า29_view1_beam_plan::plan_beam |
| 33978 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_27::บ้าน_ใหญ่_2ชั้น_27_หน้า38_view1_beam_plan::plan_beam |
| 31832 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_27::บ้าน_ใหญ่_2ชั้น_27_หน้า39_view1_beam_plan::plan_beam |
| 30724 | 6912 | plan_beam | บ้าน_ใหญ่_1ชั้น_11::บ้าน_ใหญ่_1ชั้น_11_หน้า05_view1_roof_frame_plan::plan_beam |
| 30194 | 6912 | plan_beam | บ้าน_ใหญ่_3ชั้น_09::บ้าน_ใหญ่_3ชั้น_09_หน้า38_view1_beam_plan::plan_beam |
| 30138 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_21::บ้าน_ใหญ่_2ชั้น_21_หน้า10_view3_beam_plan_2nd_floor::plan_beam |
| 29358 | 6912 | plan_beam | บ้าน_ใหญ่_1ชั้น_11::บ้าน_ใหญ่_1ชั้น_11_หน้า04_view1_beam_plan::plan_beam |
| 29068 | 6912 | plan_beam | บ้าน_ใหญ่_3ชั้น_09::บ้าน_ใหญ่_3ชั้น_09_หน้า39_view1_beam_plan::plan_beam |
| 28248 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_26::บ้าน_ใหญ่_2ชั้น_26_หน้า38_view1_beam_plan::plan_beam |
| 28088 | 6912 | plan_beam | บ้าน_ใหญ่_2ชั้น_27::บ้าน_ใหญ่_2ชั้น_27_หน้า40_view2_beam_plan_roof::plan_beam |

## What the build removed

Top-level keys dropped by the KEYS.json allowlist (label count):

| subtask.key | labels |
|---|---|
| section.png | 854 |
| section.doc_page | 854 |
| section.source_image | 854 |
| section.view_title | 590 |
| section.grid_source | 419 |
| section.scale | 396 |
| plan_beam.png | 332 |
| plan_beam.doc_page | 332 |
| plan_beam.source_image | 332 |
| plan_beam.grid_source | 332 |
| section.views | 291 |
| notes.png | 246 |
| notes.doc_page | 246 |
| notes.source_image | 246 |
| section.schema_generation | 240 |
| plan_footing.png | 239 |
| plan_footing.doc_page | 239 |
| plan_footing.source_image | 239 |
| plan_footing.grid_source | 239 |
| schedule.png | 200 |
| schedule.doc_page | 200 |
| schedule.source_image | 200 |
| plan_slab.png | 191 |
| plan_slab.doc_page | 191 |
| plan_slab.source_image | 191 |
| plan_slab.grid_source | 191 |
| plan_beam.scale | 185 |
| notes.view_title | 151 |
| schedule.view_title | 136 |
| plan_footing.scale | 133 |
| plan_beam.views | 128 |
| section.building | 114 |
| notes.views | 108 |
| notes.elements | 106 |
| plan_slab.scale | 106 |
| section.printed_page | 97 |
| plan_footing.views | 85 |
| schedule.scale | 76 |
| notes.scale | 72 |
| plan_slab.views | 65 |

notes labels that carried a top-level `elements` list (not in the notes prompt, so dropped): 23 labels, 272 non-structural elements.

Nested D5 scrub (sanitize_labels.scrub): drop_item 2230, drop_key 360, drop_text 97

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
| pass1 | house_ref | 489 |
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
| plan_files_string_views (t04 views bug) | 202 |
| skip_pass24_old_format_hint | 18 |
| skip_plan_no_matching_elements | 1 |
| z_entry_duplicate | 4 |
| z_entry_level_not_number | 11 |
| z_id_number_only_to_null | 204 |
| z_id_slug_to_null | 25 |
| z_type_mapped:beam_top | 2 |
| z_type_mapped:floor | 6 |
| z_type_mapped:landing | 3 |
| z_type_named_without_id_to_dummy | 86 |

GRID MASTER selection for plan rows: by_building_field 28, default_main_master 6, only_master 728

## 2026-11-11 evening: gridline is page-by-page (grid_incremental.py)

One page image + the GRID SO FAR tail per row; the label is only what THIS page adds. Order: beam plan, footing plan, roof frame, other plans, then sections/elevations. The old rows (up to 4 images, whole master in one answer) are gone from the data; the old build is kept in `ของเก่า/data_20261111_0146/` / `ของเก่า/build_report_20261111_0146.md`.

| measured | value |
|---|---|
| masters seen | 114 |
| masters cut into page rows | 101 |
| skipped: no dimension_chains in the master (no per-page evidence) | 7 |
| skipped: ids / origin do not follow the spec's mechanical rule | 6 |
| skipped: a line without a named/dummy type | 0 |
| skipped: no page with an image | 0 |
| skipped: replay mismatch (must be 0) | 0 |
| pages (steps) over all used masters | 1034 |
| steps that add something | 556 |
| rows written: adding rows / empty rows kept (max 2 per master) | 556 / 133 |
| empty steps not written | 345 |
| ground-truth x/y lines in those masters | 2671 |
| of those, no page connects them to the known grid (not in any label) | 183 |
| times the CODE renumbered a line the model had already given (origin shift or primes) | 731 |
| named lines given with a negative pos_m (revealed left of the origin) | 7 |
| chain rows ignored (page has no usable image / axis) | 429 |

Replay (verify): 689 rows of 101 masters re-merged in step order with `merge_delta`; every row's GRID SO FAR tail equals the state the earlier rows build - bad: 0.

gridline rows now 689 (old build: 171), tokens per row: max 13,783 · p99 12,922 · median 10,827 · mean 10,856 (old build max 34,503).

Masters with the most rows: บ้าน_เล็ก_2ชั้น_03 บ้าน_เล็ก_2ชั้น_03_หน้า00_gridline (26 rows / 41 pages); บ้าน_เล็ก_2ชั้น_02 บ้าน_เล็ก_2ชั้น_02_หน้า00_gridline (25 rows / 40 pages); บ้าน_ใหญ่_2ชั้น_01 บ้าน_ใหญ่_2ชั้น_01_หน้า00_gridline (25 rows / 28 pages); บ้าน_เล็ก_2ชั้น_01 บ้าน_เล็ก_2ชั้น_01_หน้า00_gridline (17 rows / 35 pages); บ้าน_ใหญ่_2ชั้น_23 บ้าน_ใหญ่_2ชั้น_23_หน้า00_gridline (16 rows / 23 pages)

Decisions made here (att1235): the proportion-measuring step of the old prompt is dropped (a line that no printed dimension reaches is not added); confidence_flags on page rows are `[]` (the master's audit notes are not a property of one page); plan rows keep the full ground-truth master as their GRID MASTER tail; folds are recomputed from the new per-house row counts.

## 2026-11-11 afternoon: gridline z_levels (slim) + pass0 SHEET LIST

Before this change (first build, 2026-11-11 01:46; its data is kept in `ของเก่า/data_20261111_0146/` and `ของเก่า/data_raw_20261111_0146/`, its report in `ของเก่า/build_report_20261111_0146.md`): gridline rows with z 0, pass0 rows with the sheet list 0, longest gridline row 34,503 tokens, longest pass0 row 8,961, 3,573 rows, same houses, same folds (row counts per house do not change, so the fold assignment does not).

gridline rows 689: **260 carry `z_levels`**, 429 do not. GT z entries on those rows' masters: 714, kept in labels: 699 (an entry stays only if its own source page is among the row's images, level_m is a number, id passes the leak gate).

Rows by z outcome:

| outcome | gridline rows |
|---|---|
| no_z_gt_z_levels_empty | 4 |
| no_z_no_numeric_level_m | 2 |
| with_z_all_entries | 88 |
| with_z_partial | 7 |

Entries dropped (entry level, before the row decision):

| reason | entries |
|---|---|
| z_entry_duplicate | 4 |
| z_entry_level_not_number | 11 |

type mapped to the prompt's datum/named/dummy (old GT vocabulary): {'beam_top': 2, 'floor': 6, 'landing': 3} (named when the level has a printed id, dummy otherwise). id set to null because it was the bare number or a snake_case slug, not a printed label (the prompt says number-only -> null): {'number_only': 204, 'slug': 25}; `named` with no id (after that, or in GT) changed to `dummy`, because the prompt says named = a labelled level: 86. Exact duplicates dropped after that: 4.

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
- final verify on data/: 3417 unique rows, 6834 text parts, 1887 images opened (bad 0); regex hits 0; keys outside allowlist 0; plan pattern not normalized 0; gridline shape violations 0; plan tails equal to a FULL ground-truth master of the same house 1028 (plan rows of houses with no master at all: 0); gridline page-by-page replay: 689 rows of 101 masters, bad 0
- held-out page overlap (INFO, survey fingerprints): {"status": "from fp_pairs.json (survey, read-only)", "rows_with_near_dup_page": 80, "rows_with_identical_dhash_page": 7, "houses": ["บ้าน_เล็ก_1ชั้น_01", "บ้าน_เล็ก_1ชั้น_02", "บ้าน_เล็ก_1ชั้น_03", "บ้าน_เล็ก_1ชั้น_04", "บ้าน_เล็ก_1ชั้น_05", "บ้าน_เล็ก_1ชั้น_08", "บ้าน_เล็ก_1ชั้น_11", "บ้าน_เล็ก_1ชั้น_12", "บ้าน_เล็ก_1ชั้น_16", "บ้าน_เล็ก_1ชั้น_17", "บ้าน_เล็ก_1ชั้น_21", "บ้าน_เล็ก_1ชั้น_22", "บ้าน_เล็ก_1ชั้น_23", "บ้าน_เล็ก_1ชั้น_25", "บ้าน_เล็ก_2ชั้น_01", "บ้าน_เล็ก_2ชั้น_02", "บ้าน_เล็ก_2ชั้น_03", "บ้าน_เล็ก_2ชั้น_04", "บ้าน_เล็ก_2ชั้น_05", "บ้าน_เล็ก_2ชั้น_06", "บ้าน_เล็ก_2ชั้น_07", "บ้าน_เล็ก_2ชั้น_08", "บ้าน_เล็ก_2ชั้น_09", "บ้าน_เล็ก_2ชั้น_10", "บ้าน_เล็ก_2ชั้น_24", "บ้าน_เล็ก_2ชั้น_25", "บ้าน_เล็ก_2ชั้น_26", "บ้าน_เล็ก_2ชั้น_27", "บ้าน_เล็ก_2ชั้น_28", "บ้าน_เล็ก_2ชั้น_29", "บ้าน_ใหญ่_1ชั้น_02", "บ้าน_ใหญ่_1ชั้น_03", "บ้าน_ใหญ่_2ชั้น_01"]}
- bench design names in text (INFO): 0
- siamplan-excluded variant: {"note": "this build IS the excluded variant"}

## Problems

none

## Output sha256

| file | sha256 |
|---|---|
| ข้อมูลเทรน/train_fold0.jsonl | 5e60239bba14365493430b58f84a0ae36b2b18d062c79ef50a658b1a173cfe81 |
| ข้อมูลเทรน/train_fold1.jsonl | c2e701d5f3f3cd68f9fc9f3c88e8333459b84dbb1363ad115b98bb789f37e76f |
| ข้อมูลเทรน/train_fold2.jsonl | db401292a8ff9efa29ad755bdbafe350e2f5e3bcf5ca0acceae59b1b28ac243e |
| ข้อมูลเทรน/train_fold3.jsonl | 94ce21551c7002637021576091770b248f4452b752fdc92d2c7b2cd8393284a7 |
| ข้อมูลเทรน/val_fold0.jsonl | b30eaa6395b45acd7ebabcaabfe2b6060a2573faecd7f25e9d2bbc10a9320d50 |
| ข้อมูลเทรน/val_fold1.jsonl | ac268d56baf4dff4bec2c8c39c6fa9ae41a7bca653e851b089cfd55612e3d73e |
| ข้อมูลเทรน/val_fold2.jsonl | 13be07968213f0aa6983d56ab7f7a7926449526d453b46a3e5d854fc7bffdb74 |
| ข้อมูลเทรน/val_fold3.jsonl | 36046cf79cfed2dac25b3964ffd000333783b359c7153872f9455b46f749709b |
| ข้อมูลก่อนล้าง/train_fold0.jsonl | f6053cc2262b637e2f55d1553a2ed2ccfe9db663ab98f6dbe3c3b41bdf0d0274 |
| ข้อมูลก่อนล้าง/train_fold1.jsonl | eaac5292c811bc4b32b9c6e21a9c53b68b05d550122bb7e39369683354861254 |
| ข้อมูลก่อนล้าง/train_fold2.jsonl | 6ad12282763ee275a9e35059aec52b4c8840c92fae66b26b0f0e18bff7e01806 |
| ข้อมูลก่อนล้าง/train_fold3.jsonl | a5e0699f560a51d7c3aca4a31eb423d9633ac329e24ecc6fe580c2d92020cf4b |
| ข้อมูลก่อนล้าง/val_fold0.jsonl | 59d517f639f34c59ca6881d6bebc521835a725dbcfc466b4df1d7b3a84fa61a2 |
| ข้อมูลก่อนล้าง/val_fold1.jsonl | 9d13b562024107e1d49a29cb998c63e7bef3ce146b3f8b890e85e9c6b56ccdc5 |
| ข้อมูลก่อนล้าง/val_fold2.jsonl | ac43f2f23c40dce09ad4c58897f0691d96dbd75e168e3cbb8ffc462299abbf22 |
| ข้อมูลก่อนล้าง/val_fold3.jsonl | 88c873a04a0b8c27d62ce9a8abe7c07153b3327a15ef657b07a56b0ee47168f4 |
