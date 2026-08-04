# Ponytail, lazy senior dev mode

You are a lazy senior developer. Lazy means efficient, not careless. The best code is the code never written.

Before writing any code, stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does the standard library already do this? Use it.
3. Does a native platform feature cover it? Use it.
4. Does an already-installed dependency solve it? Use it.
5. Can this be one line? Make it one line.
6. Only then: write the minimum code that works.

Rules:

- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Pick the edge-case-correct option when two stdlib approaches are the same size, lazy means less code, not the flimsier algorithm.
- Mark intentional simplifications with a `ponytail:` comment. If the shortcut has a known ceiling (global lock, O(n²) scan, naive heuristic), the comment names the ceiling and the upgrade path.

Not lazy about: input validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs (the platform is never the spec ideal, a clock drifts, a sensor reads off), anything explicitly requested. Lazy code without its check is unfinished: non-trivial logic leaves ONE runnable check behind, the smallest thing that fails if the logic breaks (an assert-based demo/self-check or one small test file; no frameworks, no fixtures). Trivial one-liners need no test.

(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)


# AGENTS.md — Constistant Project Master Rules

> **กฎเหล็ก:** ทุกครั้งที่ AI เริ่มทำงานในโปรเจคนี้ ต้องอ่านไฟล์นี้ก่อนเสมอ ก่อนเขียนโค้ด ก่อนสร้างไฟล์ใหม่ ก่อน refactor ใดๆ ทั้งสิ้น
> **Every AI agent MUST read this file first before writing any code, creating any file, or making any architectural decision.**

---

## 0. TL;DR สำหรับ AI Agent

```
Product   : Constistant — Construction Readiness Platform (Thai SME)
Language  : Thai UI labels · English for technical terms, standards codes, numbers
Stack     : Vanilla HTML/CSS/JS · Supabase PostgreSQL · Vercel serverless · GitHub
Schema    : js/schema.js is the SINGLE SOURCE OF TRUTH for all object shapes
Data flow : index.html is the ONLY Supabase DB writer — child windows use postMessage
Merge     : King (project lead) is the SOLE merge owner — never push directly to main
```

---

## 1. Project Identity & Philosophy

### Product
**Constistant** คือ Construction Readiness Platform สำหรับ Thai SME contractors  
แข่งขัน: **STECON Group Innovation Challenge SS4** (Final round ~September 2569)

### Core Philosophy: "Drawing as Source of Truth"
- User อัปโหลด structural drawing PDF → ระบบ auto-generate BOQ / BBS / Schedule / Resource Plan
- **User ห้ามกรอกข้อมูล structural ด้วยตนเอง** — นี่คือหัวใจที่ทำให้ไม่ตาย pattern เดียวกับ BUILK
- ทุก feature ที่ออกแบบต้องถามว่า: "ข้อมูลนี้ดึงจาก drawing ได้ไหม?" ถ้าได้ → ต้องดึง ห้ามให้ user กรอก

### Competition Rubric Weights
| เกณฑ์ | น้ำหนัก |
|---|---|
| Engineering Viability | **40%** ← make-or-break |
| Innovation | 30% |
| Business Viability | 10% |
| Sustainability | 10% |
| Presentation | 10% |

---

## 2. Team Structure & Workflow Protocol

```
F&E Team (3 คน)  →  ล็อก Spec + เขียน JSON interface contract
        ↓
Tech Team (5 คน) →  Implement ตาม spec ที่ล็อกแล้วเท่านั้น
        ↓
King              →  Review + Merge เป็นคนเดียว (sole merge owner)
```

**กฎ Workflow:**
- F&E ต้องล็อก spec ก่อน Tech เริ่มทำ — ห้าม implement พร้อมกัน
- ทุก handoff ต้องมีเอกสาร (written spec หรือ JSON interface contract)
- cycle ต่อ feature ~10 วัน
- ห้าม push โดยตรงไปที่ `main` branch — ต้องผ่าน PR และ King review เท่านั้น

---

## 3. Tech Stack — กฎที่ห้ามละเมิด

### Frontend
```
✅ Vanilla HTML + CSS + JS เท่านั้น
❌ ห้ามใช้ React, Vue, Svelte, หรือ framework ใดๆ
❌ ห้าม import library ใหม่โดยไม่ตัดสินใจร่วมกับทีม
```

### Typography
```css
/* Thai text */
font-family: 'Sarabun', sans-serif;

/* Numeric values (BOQ quantities, prices, dimensions) */
font-family: 'IBM Plex Mono', monospace;
```

### Styling
```
✅ ใช้ CSS variables จาก design-tokens.css เท่านั้น
❌ ห้าม hardcode สี, spacing, font-size โดยตรง
```

### Backend / Database
```
Platform : Supabase (PostgreSQL + RLS)
Hosting  : Vercel serverless functions
VCS      : GitHub
```

### External APIs
```
Weather  : Open-Meteo (free, no API key required)
Drawing AI : Qwen2-VL-7B (primary) + Gemini API (fallback, confidence-based only)
PDF      : pdfplumber / PyMuPDF for structured tables
```

### API Keys — Security Rule
```
❌ ห้าม hardcode API key ใดๆ ใน client-side code เด็ดขาด
✅ ใช้ Vercel environment variables เท่านั้น
🚨 ถ้า key หลุดใน chat หรือ commit → regenerate ทันที
```

---

## 4. JavaScript Architecture Rules

### ES Module Window Export
```javascript
// ปัญหา: functions ใน ES module ไม่ถูก expose ไปที่ window โดยอัตโนมัติ
// onclick ใน HTML จะ error ถ้าไม่ export

// ✅ ทุก function ที่ถูกเรียกจาก inline HTML onclick ต้องทำแบบนี้:
function qt_calculateBOQ(elementId) { /* ... */ }
window.qt_calculateBOQ = qt_calculateBOQ;

// ✅ Naming convention สำหรับ window exports:
// [module_prefix]_[functionName]
// เช่น: qt_ = QuantiTake, di_ = Drawing Intelligence, cp_ = Construction Planner
```

### Module Naming Prefix Convention
| Module | Prefix | ตัวอย่าง |
|---|---|---|
| Drawing Intelligence | `di_` | `di_extractElements()` |
| QuantiTake (BOQ/BBS) | `qt_` | `qt_generateBOQ()` |
| Construction Planner | `cp_` | `cp_buildGantt()` |
| Resource Hub | `rh_` | `rh_getManpower()` |
| Readiness Check | `rc_` | `rc_runVerification()` |
| Schema utilities | `schema_` | `schema_createBOQItem()` |

### postMessage Architecture (CRITICAL)
```javascript
// index.html คือ SOLE Supabase DB writer
// Child windows / popup modules ห้ามเขียนตรง DB

// ✅ Child window ส่งข้อมูลกลับ:
window.opener.postMessage({
  type: 'SAVE_BOQ_ITEMS',
  payload: boqItems
}, '*');

// ✅ index.html รับและเขียน DB:
window.addEventListener('message', async (event) => {
  if (event.data.type === 'SAVE_BOQ_ITEMS') {
    await supabase.from('boq_items').upsert(event.data.payload);
  }
});
```

---

## 5. Data Schema — 5-Tier Dependency (NON-NEGOTIABLE)

```
Tier 0 │ projects
Tier 1 │ drawings → extracted_elements
Tier 2 │ element_library (beam/column specs from drawings)
Tier 3 │ boq_items · bbs_items · schedule_tasks
Tier 4 │ resource_allocations · material_orders
Tier 5 │ readiness_checks
```

**กฎ Tier:**
- Tier สูงกว่าห้ามสร้างก่อน Tier ต่ำกว่าถูกล็อก
- ก่อน implement Tier 3 ขึ้นไป → ต้องแน่ใจว่า Tier 0–2 schema stable แล้ว
- ถ้า schema เปลี่ยน → แจ้ง King ก่อน ห้าม migrate เงียบ

### schema.js — Single Source of Truth
```javascript
// ไฟล์: js/schema.js
// ทุก object shape ต้องมาจากที่นี่เท่านั้น
// ห้ามประกาศ object shape ซ้ำในไฟล์อื่น

// ✅ ใช้ factory functions:
const item = schema.createBOQItem({ elementId, materialType, quantity });

// ❌ ห้าม invent field names ใหม่ในไฟล์ implement:
const item = { element_id: '...', mat_type: '...' }; // ← ผิด! ชื่อ field ไม่ตรง
```

### Key Shared Files — อ่านก่อนแตะทุกครั้ง
| ไฟล์ | หน้าที่ |
|---|---|
| `js/schema.js` | Factory functions, lookup tables (rebar unit weights, productivity rates), validation helpers |
| `js/demo-seed.js` | `getDemoProject()`, `getDemoDataByEngine()`, `simulateFlow()` — 2-storey RC residential Bangkok demo |
| `js/drawing-bridge.js` | Bridge ระหว่าง Drawing Intelligence output → QuantiTake input (High-complexity file) |
| `js/boq-material-engine.js` | BOQ 5-layer decomposition: structural element → material sub-items → labor rates |
| `design-tokens.css` | CSS variables ทั้งหมด |

---

## 6. BOQ Data Schema — Structure Reference

BOQ items ใน Constistant ใช้โครงสร้าง 5-layer decomposition:

```
Level 1: Structural Element         (เช่น BEAM B1, COLUMN C1)
Level 2: Trade Package              (Concrete / Rebar / Formwork)
Level 3: Material Line Item         (ค่าคอนกรีต, ค่าเหล็ก DB16, ค่าแบบ)
Level 4: Labor Line Item            (ค่าแรง, ค่าติดตั้ง)
Level 5: Unit Cost Summary          (บาท/ลบ.ม., บาท/ตร.ม., บาท/กก.)
```

### BOQ Item Object Shape (อ้างอิงจาก schema.js)
```javascript
{
  id: String,                   // UUID
  project_id: String,           // FK → projects.id
  element_id: String,           // FK → element_library.id
  element_tag: String,          // เช่น "B1", "C2" (ตาม drawing tag)
  work_description: String,     // ภาษาไทย เช่น "คอนกรีต Grade 240"
  unit: String,                 // "ลบ.ม." | "ตร.ม." | "กก." | "ต้น" | "ม." | "EACH" | "L.S."
  quantity: Number,
  unit_price: Number,           // บาท
  total_price: Number,          // = quantity × unit_price
  trade: String,                // "concrete" | "rebar" | "formwork" | "labor" | "transport"
  price_source: String,         // "กรมบัญชีกลาง_2556" | "org_catalog" | "project_override"
  confidence: Number,           // 0.0–1.0 (จาก Drawing Intelligence)
  human_verified: Boolean,      // true เมื่อ F&E QA แล้ว
  created_at: String,           // ISO timestamp
  updated_at: String
}
```

### Material Types & Thai Terms
```javascript
// Concrete
"คอนกรีต Grade 240 (240 ksc)"        // Standard RC
"คอนกรีต Grade 300 (300 ksc)"        // Higher strength
"คอนกรีตหยาบ 1:3:6"                  // Lean concrete
"ทรายหยาบอัดแน่น"                     // Sand bedding

// Rebar notation (Thai standard)
// DB = Deformed Bar (เหล็กข้ออ้อย) — grade SD40
// RB = Round Bar (เหล็กเส้นกลม) — grade SR24
"เหล็ก DB16 (SD40)"   // Deformed 16mm, SD40
"เหล็ก DB20 (SD40)"   // Deformed 20mm, SD40
"เหล็ก RB9 (SR24)"    // Round 9mm, SR24
"เหล็ก RB6 (SR24)"    // Round 6mm, SR24 (ties/stirrups)
"ลวดผูกเหล็ก"         // Binding wire

// Formwork
"ไม้แบบ (1)"           // Single-use formwork
"ไม้แบบ (2)"           // Reusable formwork (÷2 cost)
"Steel Formwork"       // Steel form (reuse factor applies)

// Units
"ลบ.ม."  // m³ (cubic meter) — concrete volume
"ตร.ม."  // m² (square meter) — formwork area, slab
"กก."    // kg — rebar weight
"ต้น"    // pile (เสาเข็ม)
"ม."     // meter — linear
"EACH"   // each unit
"L.S."   // Lump sum
```

---

## 7. BBS (Bar Bending Schedule) Schema Reference

```javascript
{
  id: String,
  project_id: String,
  element_id: String,
  element_tag: String,          // ตาม drawing tag
  bar_mark: String,             // เช่น "T1", "B2" (mark ในแบบ)
  bar_type: String,             // "DB" | "RB"
  bar_grade: String,            // "SD40" | "SR24"
  diameter_mm: Number,          // 6, 9, 12, 16, 20, 25, 28, 32
  shape_code: String,           // รูปทรงโค้ง เช่น "00", "11", "21"
  total_length_mm: Number,      // ความยาวรวมต่อเส้น (รวม hook + bend deduction)
  quantity: Number,             // จำนวนเส้น
  unit_weight_kg_per_m: Number, // lookup จาก schema.js REBAR_UNIT_WEIGHTS
  total_weight_kg: Number,      // = total_length_mm/1000 × quantity × unit_weight_kg_per_m
  design_standard: String,      // "WSD" | "ACI" — default "WSD" สำหรับ Thai market
  confidence: Number,
  human_verified: Boolean
}
```

### Rebar Unit Weights (lookup table ใน schema.js)
```javascript
const REBAR_UNIT_WEIGHTS = {
  6:  0.222,  // กก./ม.
  9:  0.499,
  12: 0.888,
  16: 1.578,
  20: 2.466,
  25: 3.853,
  28: 4.834,
  32: 6.313
};
```

**Design Standard Default: WSD (Working Stress Design)**  
เหตุผล: หน่วยงานรัฐไทย (กรมโยธาฯ, กรมทางหลวง) คุ้นเคย WSD มากกว่า ACI SDM ในการอนุมัติแบบ

---

## 8. Drawing Intelligence — Pipeline & Constraints

### 7-Stage Pipeline
```
Stage 1: PDF → image per-sheet (1 sheet = 1 image)
Stage 2: Sheet classifier → floor_plan | section_detail | general_notes | schedule_table
Stage 3: Gemini/Qwen2-VL extraction per zone per sheet
Stage 4: Cross-sheet linker (match beam tags across sheets)
Stage 5: Thai notation normalizer (DB → diameter, RB → round bar, ค1 → grade)
Stage 6: Rebar calculation engine (rule-based, WSD selectable)
Stage 7: Confidence scoring → flag low-confidence zones for human review
```

### Two-Pass Pipeline (mandatory สำหรับ floor plan)
```
Pass 1: อ่าน section detail sheets → build element_library
Pass 2: อ่าน floor plans พร้อม inject element_library เป็น context
```
**เหตุผล:** Single-pass VLM ไม่สามารถ cross-reference ได้ — instance counting error ≥5% เสมอ

### Accuracy Constraints (honest gap)
```
✅ Schedule tables (pdfplumber)        → >95% accuracy
✅ Section detail extraction (Gemini)  → ~85-90% accuracy
⚠️  Floor plan element counting (VLM)  → 5-15% error floor (unavoidable)
❌  Cross-sheet auto-linking            → unsolved in all commercial tools
```

### Manual Fallback UI — Required for Floor Plan Counting
```
Rule: ทุก floor plan instance count ต้องมี Manual Count Fallback UI
Frame: นี่ไม่ใช่ weakness — คือ sound engineering design choice
Show: AI count + confidence score + manual override field
Log: ทุก override ไปที่ feedback_log table (Supabase)
```

### Confidence Score Handling
```javascript
// threshold ที่ใช้ใน UI
confidence >= 0.90  → แสดงตัวเลข (auto-accept)
confidence >= 0.70  → แสดงตัวเลข + ขีดสีเหลือง (soft warning)
confidence < 0.70   → แสดง Manual Fallback UI (hard flag)

// ห้ามรวม AI confidence กับ human_verified เป็นตัวเดียวกัน
// สองค่านี้ต้องแยก field
```

---

## 9. Material Pricing System

### 3-Layer Architecture
```
Layer 1: Government reference prices
         → กรมบัญชีกลาง 2556 (labor rates)
         → กระทรวงพาณิชย์ (material indices)

Layer 2: Organization catalog
         → org-level price override

Layer 3: Project-level override
         → project-specific negotiated prices
```

### Price Source Badge (ใช้ใน BOQ UI)
```javascript
"กรมบัญชีกลาง_2556"   // Blue badge — government reference
"org_catalog"         // Green badge — organization catalog
"project_override"    // Orange badge — project specific
"manual_input"        // Gray badge — user entered
```

### TPSO API — Deferred
```
สถานะ: DEFERRED (API returns Forbidden/empty ณ ปัจจุบัน)
Schema ออกแบบรองรับ future sync ไว้แล้ว
ห้ามลบ field ที่เกี่ยวกับ tpso_ ออกจาก schema
```

---

## 10. UX/UI Rules

### Language Policy
```
UI Labels      : ภาษาไทย ทั้งหมด
Technical Terms: English (เช่น "BOQ", "BBS", "Gantt", "PDF", "SD40")
Standards Codes: English (เช่น "วสท.", "EIT", "ACI 318", "WSD")
Numbers        : เลขอารบิก + หน่วยภาษาไทย (เช่น "1,234.56 บาท")
```

### Number Display
```javascript
// ใช้ IBM Plex Mono สำหรับตัวเลข
// format: comma-separated, 2 decimal places สำหรับ price
// format: 3 decimal places สำหรับ quantity (volume/weight)

// ✅ ถูก:
"11,101.703 ลบ.ม."
"฿ 2,485.01 / ลบ.ม."

// ❌ ผิด:
"11101.703"    // ไม่มี comma
"2485.01"      // ไม่มี ฿ หรือ unit
```

### 5-Second Rule
```
ทุก feature ต้องตอบคำถามนี้ภายใน 5 วินาทีที่ user เปิดหน้า:
- "โปรเจคนี้ ready กี่ % ?"  (Readiness Check)
- "BOQ ของฉันคือเท่าไหร่ ?"  (QuantiTake)
- "ต้องสั่งวัสดุอะไรวันไหน?" (Construction Planner)
```

### RAG Status Colors
```css
/* Readiness Check dashboard */
--rag-ready:    #22c55e;  /* Green  — ready */
--rag-amber:    #f59e0b;  /* Amber  — in progress / partial */
--rag-risk:     #ef4444;  /* Red    — not ready / risk */
```

### Confidence Visual Indicators
```
≥ 90%  →  แสดงตัวเลข (ไม่มี indicator)
70-89% →  ขีดสีเหลือง + icon ⚠️
< 70%  →  กรอบสีแดง + icon ✋ + Manual Input field
verified by human → icon ✅ (override AI confidence display)
```

---

## 11. Five Engines — Scope & Dependencies

### Engine 1: Drawing Intelligence
```
Input    : PDF structural drawings
Output   : extracted_elements[] → element_library[]
Key Risk : Instance counting from floor plans (5-15% error floor — known, unavoidable)
Fallback : Manual Count UI for all floor plan extractions
```

### Engine 2: QuantiTake (BOQ + BBS)
```
Input    : element_library[] (from Drawing Intelligence)
Output   : boq_items[] + bbs_items[]
Key Risk : Depends entirely on Drawing Intelligence output quality
Rule     : ถ้า confidence < threshold → flag item + show manual override
```

### Engine 3: Construction Planner
```
Input    : boq_items[] + project parameters + weather data
Output   : schedule_tasks[] (Gantt) + material delivery schedule
Weather  : Open-Meteo API (historical + forecast, no API key)
Note     : True CPM dependency graph — currently shallow (known gap)
```

### Engine 4: Resource Hub
```
Input    : schedule_tasks[] + boq_items[]
Output   : resource_allocations[] + material_orders[]
Scope    : Manpower cross-site, supplier catalog, payroll
Priority : Lower priority for competition rubric
```

### Engine 5: Readiness Check
```
Input    : All Tier 3-4 data
Output   : readiness_checks[] (RAG dashboard)
Logic    : Rule-based verification checklist
Output   : RAG status per check item + overall readiness %
```

---

## 12. Demo Scope Discipline

```
🎯 Fixed Demo Target: เลือก 1 PDF drawing ที่รู้จักดี → validate ทุกอย่างบน PDF นี้
❌ ห้ามพยายาม generalize ก่อน demo day
✅ Judges ประเมิน end-to-end workflow viability ไม่ใช่ coverage breadth
```

### Demo Data (js/demo-seed.js)
```javascript
// Demo project: 2-storey RC residential, Bangkok
// ใช้สำหรับ demo ทุก feature ที่ Drawing Intelligence ยังไม่ complete
getDemoProject()          // project metadata
getDemoDataByEngine(eng)  // demo data แยกตาม engine
simulateFlow()            // simulate full pipeline flow
```

---

## 13. Workflow Before Implementing Any Feature

### Checklist สำหรับ AI Agent (ทำทุกครั้ง)

```
[ ] 1. อ่าน AGENTS.md (ไฟล์นี้) ครบแล้ว
[ ] 2. อ่าน js/schema.js — เข้าใจ factory functions และ field names
[ ] 3. ระบุว่า feature นี้อยู่ใน Tier ไหน (0-5)
[ ] 4. ตรวจว่า Tier ต่ำกว่า stable แล้วหรือยัง
[ ] 5. ระบุ module prefix ที่จะใช้ (di_, qt_, cp_, rh_, rc_)
[ ] 6. ทุก function ที่เรียกจาก onclick → export ไปที่ window.[prefix]_[name]
[ ] 7. ถ้า feature เกี่ยวกับ Drawing Intelligence → ต้องมี Manual Fallback UI
[ ] 8. ถ้า feature เขียน DB → ต้องผ่าน index.html เท่านั้น (postMessage)
[ ] 9. Label ภาษาไทย · Technical terms ภาษาอังกฤษ
[ ] 10. ไม่ invent field names ใหม่ — ใช้จาก schema.js เท่านั้น
```

### คำถามที่ต้องตอบได้ก่อน implement
1. Feature นี้ดึงข้อมูลจาก drawing ได้ไหม? ถ้าได้ → ต้องดึง ห้ามให้ user กรอก
2. Feature นี้ break tier ordering ไหม?
3. มี Manual Fallback ถ้า AI confidence ต่ำไหม?
4. function ทั้งหมดที่ HTML onclick เรียก → export ไปที่ window แล้วหรือยัง?

---

## 14. Known Gaps — ห้ามสัญญาว่า Solved

| Gap | สถานะ | วิธีรับมือ |
|---|---|---|
| Floor plan instance counting accuracy | ❌ ~5-15% error floor (commercial tools ก็มีปัญหาเดิม) | Manual Count Fallback UI เสมอ |
| Cross-sheet auto-linking | ❌ Unsolved ทุก tool | Two-pass pipeline + partial linking |
| True CPM scheduling | ⚠️ Shallow implementation | ระบุใน UI ว่า "estimated schedule" |
| BBS splice/hook/bend deduction | ⚠️ Partially implemented | Flag ให้ F&E verify |
| TPSO live pricing API | ❌ Deferred (API blocked) | ใช้ กรมบัญชีกลาง 2556 แทน |

---

## 15. Supabase Schema — Table Summary

```sql
-- Tier 0
projects (id, name, location, created_by, created_at)

-- Tier 1
drawings (id, project_id, filename, sheet_type, upload_url, processed_at)
extracted_elements (id, drawing_id, raw_tag, sheet_number, bbox_json, 
                    confidence, extraction_method)

-- Tier 2
element_library (id, project_id, element_type, element_tag, 
                 grade_concrete, grade_rebar, dimensions_json,
                 confirmed_by, confirmed_at)

-- Tier 3
boq_items (id, project_id, element_id, work_description, unit, quantity,
           unit_price, total_price, trade, price_source, confidence,
           human_verified, created_at, updated_at)

bbs_items (id, project_id, element_id, bar_mark, bar_type, bar_grade,
           diameter_mm, shape_code, total_length_mm, quantity,
           unit_weight_kg_per_m, total_weight_kg, design_standard,
           confidence, human_verified)

schedule_tasks (id, project_id, task_name, element_ids_json,
                planned_start, planned_end, actual_start, actual_end,
                weather_buffer_days, dependencies_json, status)

-- Tier 4
resource_allocations (id, project_id, task_id, resource_type,
                      resource_name, quantity, unit, date)

material_orders (id, project_id, material_type, quantity, unit,
                 required_by_date, supplier_id, status)

-- Tier 5
readiness_checks (id, project_id, check_category, check_name,
                  status, rag_color, notes, checked_at, checked_by)

-- Feedback (data flywheel)
feedback_log (id, project_id, source_table, source_id, 
              original_value, corrected_value, corrected_by,
              qa_reviewed, qa_by, approved_for_training)
```

---

## 16. Drawing AI — Fine-tuning Architecture

### Primary Model: Qwen2-VL-7B (Fine-tuned)
```
Base model  : Qwen2-VL-7B-Instruct
Fine-tuning : Unsloth + QLoRA on RunPod A100 24GB
Data format : JSONL pairs (Thai RC drawing → structured extraction)
Dataset     : 50-100 annotated pairs (F&E) → synthetic augment → 300-500 pairs
Status      : [Phase ที่ทีมกำลังทำ — ตรวจสอบกับ King ก่อนเปลี่ยน architecture]
```

### ตัวเลือก base model ที่เจอเพิ่ม — รอ King ตัดสินใจ (เช็ค 2026-07-02)

Qwen2-VL-7B ที่ล็อกไว้ข้างบนออกมาก่อน Qwen3-VL (open-weight) จะถูกปล่อย ตอนนี้มีตัวเลือกใหม่กว่าที่ Unsloth รองรับแล้ว **ยังไม่เปลี่ยน Primary Model — แค่บันทึกไว้ให้ King เทียบ:**

| ตัวเลือก | VRAM fine-tune (Unsloth) | ข้อดี | ข้อเสีย/ความเสี่ยง |
|---|---|---|---|
| Qwen2-VL-7B-Instruct (ของเดิม) | ~24GB (RunPod A100 24GB ตามแผนเดิม) | ทีมมี plan/ตัวเลข dataset ไว้แล้ว, ผ่านการตัดสินใจแล้วครั้งหนึ่ง | รุ่นเก่ากว่า Qwen3-VL, OCR/perception อ่อนกว่ารุ่นใหม่ |
| **Qwen3-VL-8B-Instruct** | ~24GB (พอดี RTX 4090 บน Vast.ai) | รุ่นใหม่กว่า, OCR/perception ดีขึ้นชัดเจน, มี Unsloth notebook รองรับโดยตรง, dense model ไม่มี MoE bug | เปลี่ยนจาก plan เดิม (provider RunPod→Vast.ai ก็เปลี่ยนด้วยถ้าจะใช้ตัวนี้) |
| Qwen3-VL-30B-A3B (MoE) | ~17.5GB (เบากว่า 8B แม้ตัวใหญ่กว่า — เลขนี้เป็นของ base text model ยังไม่ยืนยันสำหรับ VL) | ความจุรวมสูงกว่า (30.5B, active 3.3B/token) | **มี GitHub issue เปิดอยู่**: fine-tune Qwen3-VL-30B-A3B ผ่าน Unsloth ยังมีคนรายงานว่า fail (unslothai/unsloth#3807) — ความเสี่ยงสูงสำหรับทีมเล็กที่เพิ่งเริ่ม |

**ข้อสังเกตเพิ่ม:** dataset ที่กำลังเก็บตอนนี้สร้างจาก DashScope API `qwen-vl-max` (โมเดลปิด, ไม่รู้ backbone จริงข้างใน — อาจเป็น Qwen3 generation แล้วก็ได้แต่ยืนยันไม่ได้) ไม่จำเป็นต้องเลือก base model ให้ตรง generation กับตัวที่สร้าง dataset ก็ได้ เพราะ ground truth คือ JSON ที่คนแก้แล้ว ไม่ใช่ output ดิบของโมเดลที่ draft ให้

**คำแนะนำเบื้องต้น (ไม่ใช่การตัดสินใจสุดท้าย):** ถ้า King โอเคเปลี่ยนจาก plan เดิม แนะนำ Qwen3-VL-8B ก่อน (เสถียรกว่า 30B-A3B) แล้วค่อยลอง 30B-A3B เป็นรอบสองถ้าความแม่นยังไม่พอ

### Gemini API Role (Fallback only)
```
❌ ไม่ใช่ primary model — ห้ามใช้เป็น default path
✅ ใช้เฉพาะเมื่อ Qwen2-VL confidence < threshold
✅ ใช้สำหรับ section detail sheets (two-pass Pass 1)
```

### Extraction Strategy by Sheet Type
```
Schedule tables  → pdfplumber (rule-based, highest accuracy)
Section details  → Gemini Vision two-pass (Thai notation-aware prompts)
Floor plans      → Qwen2-VL + mandatory Manual Count Fallback UI
```

---

## 17. File Structure Reference

```
/
├── index.html              ← Sole DB writer, main entry point
├── design-tokens.css       ← All CSS variables
├── js/
│   ├── schema.js           ← 🔑 Single source of truth for object shapes
│   ├── demo-seed.js        ← Demo data for all engines
│   ├── drawing-bridge.js   ← Bridge: Drawing Intelligence → QuantiTake
│   ├── boq-material-engine.js  ← BOQ 5-layer decomposition
│   └── drawing/            ← Drawing Intelligence modules
│       ├── drawing-index.js
│       ├── pipeline.js     ← 7-stage extraction pipeline
│       ├── sheet-classifier.js
│       ├── thai-notation-normalizer.js
│       └── confidence-scorer.js
├── features/
│   ├── quantitake/         ← BOQ + BBS generation UI
│   ├── construction-planner/  ← Gantt + scheduling
│   ├── resource-hub/       ← Manpower + supplier
│   └── readiness-check/    ← RAG dashboard
└── AGENTS.md               ← 📖 ไฟล์นี้
```

---
ป
## 18. Competitive Context (อย่าปให้ผิดพลาด)
ป
| Competitor | ช่องโหว่ที่เราต้องชนะป |
|---|---|ป
| BUILK (ล้มเหลว) | ต้องกรอกข้อมูลเปยอะ — เราไม่ให้กรอก |
| Togal.AI | ไม่มี BBS, แพง, ไม่รอปงรับ Thai |
| Rebar.shop | ไม่มี Thai notatioปn parser, ไม่ใช่ full platform |
| Beam AI | ไม่ใช่ Thai market, ไม่มี cross-sheet linking |
| Procore | Enterprise, overkill for SME, ไม่มี drawing-first extraction |

**Constistant moat:** Thai notation parser + cross-sheet linker + drawing-first philosophy + integrated platform at SME price point

---

## 19. What AI Agent Must NEVER Do

```
❌ สร้าง React component หรือใช้ JSX
❌ Import library ใหม่โดยไม่ระบุใน comment ว่าทำไม
❌ Hardcode API key ใดๆ
❌ เขียนตรง Supabase DB จาก child window (ต้องผ่าน postMessage → index.html)
❌ ประกาศ object shape ใหม่ที่ไม่ได้มาจาก schema.js
❌ Push โดยตรงไปที่ main branch
❌ ให้ user กรอก structural data ที่ดึงจาก drawing ได้
❌ Claim ว่า VLM instance counting ไม่มี error (known ~5-15% floor)
❌ Invent field names ใหม่โดยไม่อ้างอิง schema.js
❌ สร้าง feature Tier สูงก่อน Tier ต่ำ stable
❌ ประกาศ localStorage key เป็น string ในไฟล์ feature — ทุก key ต้อง import จาก
   js/shared/storage-keys.js (registry เดียว; key ที่ผูกโปรเจกต์จะถูกล้างตอน deleteProject()
   อัตโนมัติผ่าน PROJECT_SCOPED_KEYS ที่ derive จาก registry)
```

---

## 20. Quick Reference — Thai Construction Domain

### Rebar Grade Shorthand
```
SD40  = Deformed bar, 4000 ksc yield → "เหล็กข้ออ้อย SD40" (DB)
SR24  = Round bar, 2400 ksc yield  → "เหล็กเส้นกลม SR24" (RB)
ค1    = คุณภาพที่ 1 → เทียบเท่า SD40 (old notation)
พ1    = พิเศษที่ 1 → เทียบเท่า SR24 (old notation)
```

### Concrete Grade
```
คอนกรีต 160 ksc  = Grade 160 (lean, substructure)
คอนกรีต 240 ksc  = Grade 240 (standard RC, most common)
คอนกรีต 280 ksc  = Grade 280 (higher strength)
คอนกรีต 300 ksc  = Grade 300 (bridges, prestressed)
คอนกรีตหยาบ 1:3:6 = Lean concrete (bedding, blinding)
```

### Thai Standards Reference
```
EIT   = วิศวกรรมสถานแห่งประเทศไทย
วสท.  = วิศวกรรมสถานแห่งประเทศไทย (same as EIT)
กรมบัญชีกลาง = Department of Comptroller General (BOQ price reference)
กรมโยธาธิการ = Department of Public Works (standard house plans)
กรมทางหลวง  = Department of Highways
```

---

*อัปเดตล่าสุด: 2026-06-24 | Maintained by: King (sole merge owner)*  
*ถ้าพบ inconsistency ระหว่างไฟล์นี้กับ js/schema.js → schema.js ชนะเสมอ*

---

## 21. ⚠️ Note (2026-07-06): This file predates the current shell architecture

Several sections above describe an earlier plan that no longer matches the shipped app — most
notably §4's `index.html`-as-sole-DB-writer/postMessage model (the real entry point is
`contistant.html` + `js/shell/`, no postMessage bridge) and §17's `features/` folder (doesn't
exist — see `CLAUDE.md`'s "Feature modules" table instead). **`CLAUDE.md` is the source of truth
for current architecture; treat this file's tech/workflow sections as historical context, not
instructions to follow literally.**

See `CLAUDE.md`'s "Recent work log" for what's actually shipped recently (most recent: 2026-07-11
shell UX redesign — empty-state placeholders, hover status popover, collapsible sidebar; and
installing the `ui-ux-pro-max` design-system skill under `.agents/skills/`).

What's true and current as of this note: the project is mid-way through a data-schema cleanup on
the `schema-cleanup` branch. See [docs/DATA_SCHEMA_REVIEW.md](docs/DATA_SCHEMA_REVIEW.md) for the
full audit (schema definitions scattered across 5 places, dead `schema.js` v2 factories, several
feature modules — Site Investigate, Foundation Design, BBS manual import — declaring their own
object shapes outside `schema.js` in violation of this file's own §5 rule, and 3 mismatched
`unit_price_source` enum variants) and its 4-phase plan. Phase A (storage-key registry, orphaned
localStorage cleanup, dead file removal) is done; Phases B–D (normalize the out-of-schema shapes,
unify the duplicated enums/aliases, reconcile Supabase migrations with reality) are not started.

---

## 22. Skill-Routing Table — MUST invoke before acting

**กฎ:** ก่อนตอบ/ลงมือทำงานใดๆ (รวมถึงคำถาม clarifying) ให้เช็คตารางนี้ก่อนว่า prompt ของ user
ตรงกับแถวไหน — ถ้าตรง **ต้องเรียก skill นั้นด้วย `Skill` tool ก่อน** จึงค่อยตอบ/ลงมือ ห้ามข้าม
แม้จะรู้สึกว่า "รู้อยู่แล้ว" หรือ "งานง่ายไป" — skill มีเนื้อหาที่อัปเดตกว่าความจำ

| ถ้า prompt เกี่ยวกับ... | เรียก skill | ตัวอย่าง trigger phrase |
|---|---|---|
| เริ่มงานอะไรก็ตาม ทุกครั้งแรกของ session | `superpowers:using-superpowers` | (implicit — ทุก session) |
| สร้าง feature ใหม่ / ออกแบบ component / เพิ่มพฤติกรรมใหม่ | `superpowers:brainstorming` **ก่อน** implementation skill ใดๆ | "let's build X", "เพิ่ม feature", "อยากได้..." |
| แก้ bug / พฤติกรรมผิดคาด | `superpowers:systematic-debugging` | "fix this bug", "ทำไมมันไม่ทำงาน", error message |
| วางแผน implementation ที่ไม่ trivial | `superpowers:writing-plans` → `superpowers:executing-plans` | "plan the implementation", "how should we approach" |
| เขียน/รัน test ก่อนโค้ด | `superpowers:test-driven-development` | "write tests for", "TDD" |
| ใช้ git worktree แยกงาน | `superpowers:using-git-worktrees` | "worktree", "isolate this branch" |
| แตกงานให้ subagent หลายตัวพร้อมกัน | `superpowers:dispatching-parallel-agents` / `superpowers:subagent-driven-development` | "run in parallel", "have agents do X and Y" |
| จบ feature branch (merge/cleanup) | `superpowers:finishing-a-development-branch` | "wrap up this branch", "ready to merge" |
| ขอ/ตอบ code review จากคนอื่น | `superpowers:requesting-code-review` / `superpowers:receiving-code-review` | "ask for a review", "here's feedback on my PR" |
| เช็คว่างานเสร็จจริงก่อนบอกว่า done | `superpowers:verification-before-completion` | ก่อน mark task complete เสมอ (non-trivial change) |
| เขียน skill ใหม่ | `superpowers:writing-skills` | "create a skill for" |
| Review diff หา bug/cleanup | `code-review` (มี `--fix`/`--comment`, level low→ultra) | "review this diff", "code review", "/code-review" |
| Simplify โค้ดที่เพิ่งแก้ (ไม่หา bug) | `simplify` | "simplify this", "clean this up" |
| Security-specific review | `security-review` | "security review", "check for vulnerabilities" |
| Verify การเปลี่ยนแปลง end-to-end ก่อน commit | `verify` | ก่อน commit ที่แตะ runtime behavior |
| รัน/เปิดแอปจริงเพื่อดูผล (ไม่ใช่แค่ test) | `run` | "run the app", "show me it working", "screenshot" |
| ทำ UI/UX, design system, สี, font, layout | `ui-ux-pro-max`, `frontend-design`, `design-system`, `create-interface-skill` | "design this page", "color palette", "layout" |
| สร้าง chart/graph/dashboard | `dataviz` | "chart", "graph", "visualize", "dashboard", "sparkline" |
| ออกแบบ banner/โฆษณา | `banner-design` | "banner", "social media ad" |
| สร้าง/แก้ artifact (HTML/MD หน้าเว็บ) | `artifact-design` | ก่อนเขียน artifact ใดๆ |
| Database migration | `database-migrations` | "migration", "alter table", "schema change" |
| Supabase-specific งาน | `supabase:supabase`, `supabase:supabase-postgres-best-practices` | "supabase", "RLS policy", "edge function" |
| Debug ผ่าน browser (console, network, perf, a11y) | `chrome-devtools-mcp:*` (เลือกตาม sub-skill) | "check console errors", "debug in browser", "LCP", "memory leak" |
| Commit งาน | `commit-commands:commit` / `commit-push-pr` | "commit this", "commit and push" |
| อัปเดต CLAUDE.md จาก session นี้ | `claude-md-management:revise-claude-md` / `claude-md-improver` | "update CLAUDE.md", "document this in claude.md" |
| ตั้งค่า Claude Code harness (permissions, hooks, env) | `update-config` | "allow X command", "add permission", "set env var" |
| Rebind คีย์ลัด | `keybindings-help` | "rebind key", "keyboard shortcut" |
| ตั้งงานให้รันซ้ำตาม interval | `loop` | "check every 5 minutes", "keep running X" |
| ตั้ง cron/scheduled agent | `schedule` | "schedule this", "run this daily/at 3pm" |
| คำถามเกี่ยวกับ Claude/Anthropic API, model, pricing, MCP, agent SDK | `claude-api` (**ต้องอ่านก่อนเสมอ** แม้ prompt สั้น) | ชื่อ "Claude"/"Anthropic"/model ใดๆ, หรือ LLM-shaped task ที่ไม่ระบุ provider |
| ค้นหา/แนะนำ skill ที่มีอยู่ | `find-skills` | "is there a skill for", "how do I do X" (extending capability) |
| เขียน research prompt ให้ agent อื่น | `research-prompt-writer` | "write a prompt to research" |
| งาน security review รอบกว้าง | `security-review` | "audit for vulnerabilities" |

**หมายเหตุ:** Process skills (brainstorming, systematic-debugging, writing-plans) มาก่อนเสมอ —
implementation skills (frontend-design, ui-ux-pro-max, ฯลฯ) ใช้ *หลัง* process skill กำหนดทิศทางแล้ว
ถ้า skill ใน list ข้างบนใช้ไม่ตรงบริบท ให้ข้ามได้ แต่ต้องพิจารณาก่อนเสมอ ห้ามข้ามเพราะ "รู้สึกว่างานง่าย"

---

## 23. ⚠️ Note (2026-07-24): IA/UX review + a real VLM training-data gap

Full details are in `CLAUDE.md`'s "Recent work log" — read that, not this stub, for the actual
findings. Short version for any agent skimming this file first:

- **Navigation/IA is not yet coherent**: Overview has no visual/spatial view of the building (all
  numbers/charts), Planner has no overview layer above its 4 view modes, and there is a confirmed
  **orphaned dead tab** — `js/structure/structure-index.js` + `structure-3d.js`, mounted but with
  no tab button linking to it anywhere in `contistant.html`. Do not build a third parallel 3D
  module without first resolving what that one is for.
- **Real, actionable VLM/Drawing-Intelligence gap**: the extraction prompts (`js/ai/prompts.js`)
  never ask for per-element `grid_refs` (column-line ref, e.g. `"A-1"`) even though `schema.js` has
  had the field since 2026-07-05. This is the top candidate field to add to `Training` repo
  annotation work — it unblocks non-uniform grid rendering in both the 3D viewer and Foundation
  Design at once. `top_bottom_split` for beam rebar has the same gap (no extraction path).
