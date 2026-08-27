# Graph Report - tools  (2026-08-27)

## Corpus Check
- Large corpus: 149 files · ~520,891 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 125 nodes · 226 edges · 11 communities
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.75)
- Token cost: 80,647 input · 0 output

## Community Hubs (Navigation)
- Harvest Report - Exact Match Houses
- Harvest Report - Staging Houses
- CV Scan Detection Pipeline
- Template Harvesting Workflow
- Pattern Recognition Core Matching
- Markdown-to-PDF Book Builder
- Pattern Recognition Visualization
- Merge Guard Safety Layer
- Format Validation Gate
- Qwen Export Converter
- Harvest Report - Match Config

## God Nodes (most connected - your core abstractions)
1. `Harvest Report` - 49 edges
2. `พอดี (Exact Match) - GT bank count matches template count` - 24 edges
3. `ขาด (Incomplete Template) - routed to staging 3 กลุ่ม` - 21 edges
4. `imread_thai()` - 9 edges
5. `analyze()` - 9 edges
6. `scan_image()` - 8 edges
7. `harvest()` - 8 edges
8. `load_templates()` - 8 edges
9. `imwrite_thai()` - 7 edges
10. `match_bank()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `self_harvest()` --calls--> `analyze()`  [EXTRACTED]
  cv_scan.py → pattern_recognition.py
- `scan_image()` --calls--> `analyze()`  [EXTRACTED]
  cv_scan.py → pattern_recognition.py
- `scan_image()` --calls--> `imread_thai()`  [EXTRACTED]
  cv_scan.py → pattern_recognition.py
- `write_outputs()` --calls--> `imwrite_thai()`  [EXTRACTED]
  cv_scan.py → pattern_recognition.py
- `demo()` --calls--> `load_templates()`  [EXTRACTED]
  cv_scan.py → pattern_recognition.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Houses Routed to 3-Group Staging** — harvest_report_incomplete_template_staging, harvest_report_house_04_small_2f_02, harvest_report_house_07_large_2f_01, harvest_report_house_10_small_1f_05, harvest_report_house_11_small_1f_06, harvest_report_house_12_large_2f_02, harvest_report_house_14_large_2f_04, harvest_report_house_16_small_1f_09, harvest_report_house_19_large_3f_03, harvest_report_house_21_small_1f_10, harvest_report_house_22_small_2f_04, harvest_report_house_23_small_1f_12, harvest_report_house_26_small_1f_07, harvest_report_house_27_large_1f_04, harvest_report_house_31_small_1f_11, harvest_report_house_32_small_1f_13, harvest_report_house_39_small_2f_15, harvest_report_house_45_large_1f_02, harvest_report_house_46_large_1f_03, harvest_report_house_47_large_2f_06 [EXTRACTED 1.00]
- **Excess False-Positive Match Houses** — harvest_report_excess_noise, harvest_report_house_08_small_1f_03, harvest_report_house_24_small_2f_08 [EXTRACTED 1.00]
- **GT Bank Matching Configuration** — harvest_report_bank_10_template, harvest_report_threshold_0_72, harvest_report_exact_match [EXTRACTED 1.00]

## Communities (11 total, 0 thin omitted)

### Community 0 - "Harvest Report - Exact Match Houses"
Cohesion: 0.16
Nodes (25): พอดี (Exact Match) - GT bank count matches template count, Harvest Report, 01บ้าน_เล็ก_1ชั้น_01, 02บ้าน_เล็ก_1ชั้น_02, 03บ้าน_เล็ก_2ชั้น_01, 05บ้าน_เล็ก_2ชั้น_03, 06บ้าน_ใหญ่_1ชั้น_01, 09บ้าน_เล็ก_1ชั้น_04 (+17 more)

### Community 1 - "Harvest Report - Staging Houses"
Cohesion: 0.10
Nodes (20): 04บ้าน_เล็ก_2ชั้น_02, 07บ้าน_ใหญ่_2ชั้น_01, 10บ้าน_เล็ก_1ชั้น_05, 11บ้าน_เล็ก_1ชั้น_06, 12บ้าน_ใหญ่_2ชั้น_02, 14บ้าน_ใหญ่_2ชั้น_04, 16บ้าน_เล็ก_1ชั้น_09, 19บ้าน_ใหญ่_3ชั้น_03 (+12 more)

### Community 2 - "CV Scan Detection Pipeline"
Cohesion: 0.18
Nodes (18): cv_hint_text(), demo(), draw_som_marks(), number_elements(), page_hint(), แปลง scan → บล็อกข้อความแปะท้าย prompt pass 2.4 (2.4a=ข้อความล้วน, 2.4b=คู่ภาพมา, เอา detection ของหน้านี้เอง (ทุกตัวที่ผ่านคลังกลาง) เป็น template กวาดซ้ำเข้ม 0., ลายนิ้วมือหยาบๆ จากจำนวนที่เจอ — ไว้เช็คขวางป้าย pass0 ไม่ใช่แทนที่มัน (+10 more)

### Community 3 - "Template Harvesting Workflow"
Cohesion: 0.26
Nodes (11): harvest(), house_pages(), image_of(), จัดอันดับ candidate ในกอง staging แล้วทำ montage ให้คนดูเรียงตามความน่าจะเป็นของ, {'06บ้าน_ใหญ่_1ชั้น_01': {'footing': ('หมายเลขหน้า', gt_count)}} จากชื่อ+เนื้อไฟ, หาไอคอนที่ซ้ำกันหลายจุดบนหน้า — สำหรับบ้านที่ bank ปัจจุบันจับไม่ได้     วิธี:, repeated_icon_candidates(), review() (+3 more)

### Community 4 - "Pattern Recognition Core Matching"
Cohesion: 0.24
Nodes (12): analyze(), beam_template(), match_bank(), match_beam_runs(), match_points(), _nms(), _nms_greedy(), match คานแล้วรวมจุดต่อเนื่องเป็นแถบยาว คืน [(x, y, w, h)] (+4 more)

### Community 5 - "Markdown-to-PDF Book Builder"
Cohesion: 0.52
Nodes (6): absolutize_images(), append_to_book(), find_browser(), md_to_pdf(), Path, แปลง src ของรูปที่เขียนเป็น path สัมพัทธ์ ให้เป็น file:// เต็ม      จำเป็นเพรา

### Community 6 - "Pattern Recognition Visualization"
Cohesion: 0.29
Nodes (7): demo(), draw_marks(), load_templates(), วาด overlay: ฐานราก=แดง เสา=เขียว คาน=น้ำเงินโปร่ง + ป้ายจำนวนมุมภาพ, template bank: tpl_footing*.png / tpl_column*.png ทุกไฟล์ใน tools/templates/, self-check กับบ้าน 17 — ฐานรากหน้า14 ต้องเจอครบ 14 (ground truth นับจากแบบจริง), run()

### Community 7 - "Merge Guard Safety Layer"
Cohesion: 0.47
Nodes (5): cv_stub(), merge_no_delete(), สร้าง element ตัวแทนของกรอบ CV ที่โมเดลทำหาย — ทุกอย่างที่ CV ไม่รู้จริงเป็น nul, (บัญชี CV จาก pass 2.5, elements ที่โมเดลตอบใน pass 3) → (merged, warnings), _selfcheck()

### Community 8 - "Format Validation Gate"
Cohesion: 0.70
Nodes (4): check_house(), load_grid(), main(), walk()

### Community 9 - "Qwen Export Converter"
Cohesion: 0.50
Nodes (4): convert(), floor_from(), Path, อ่านชั้นจากหัวแบบ — ไม่เจอคืน None (ห้ามเดาเป็น F1 ตามสเปก)

### Community 10 - "Harvest Report - Match Config"
Cohesion: 0.40
Nodes (5): Bank of 10 Templates, เกิน (ขยะ) - Excess False Positive matches, 08บ้าน_เล็ก_1ชั้น_03, 24บ้าน_เล็ก_2ชั้น_08, Match Threshold @0.72

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Harvest Report` connect `Harvest Report - Exact Match Houses` to `Harvest Report - Staging Houses`, `Harvest Report - Match Config`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `analyze()` connect `Pattern Recognition Core Matching` to `CV Scan Detection Pipeline`, `Pattern Recognition Visualization`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `imread_thai()` connect `Template Harvesting Workflow` to `CV Scan Detection Pipeline`, `Pattern Recognition Core Matching`, `Pattern Recognition Visualization`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `Harvest Report - Staging Houses` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._