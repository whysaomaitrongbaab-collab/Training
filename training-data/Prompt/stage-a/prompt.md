---
stage: A
model: qwen-vl-plus
temperature: 0.1
max_tokens: 1500
response_format: json_object
input: batch of 10-12 page images (one PDF segment)
output: classification JSON — script reads sheet_type and routes to Stage B itself
---

> ⚠️ อ่าน [../../rule_of_tune.md](../../rule_of_tune.md) ก่อนเริ่มงานทุกครั้ง — ไม่มีข้อยกเว้น

# Stage A — Page Classifier

## หลักการทำงานจริง

```
qwen-processor.js (script)
  │
  ├── loop batch (10–12 รูป)
  │     └── callQwen({ model: 'qwen-vl-plus', prompt: CLASSIFY_PROMPT, images: batch })
  │              ↓
  │         JSON: [{page_number, sheet_type, confidence, key_identifiers}]
  │
  └── script อ่าน sheet_type แล้วตัดสินใจเอง:
        floor_plan / section_detail / schedule_table → Stage B1 (qwen-vl-max)
        general_notes                                → Stage B2 (qwen-vl-plus)
        table_of_contents / architectural / unknown → skip (ไม่ยิง API ต่อ)
```

**Qwen เห็นแค่ classify request ทีละ batch — ไม่รู้ว่ามี Stage B อยู่**
Routing ทำโดย script ด้วย if/else ธรรมดา ไม่ใช่ AI

---

## System Prompt

```
You are classifying pages of a Thai reinforced-concrete (RC) structural drawing set.
Identify each page by its visual layout only.
Do NOT read dimension numbers or small text — layout recognition is sufficient.

CRITICAL: base your answer ONLY on what is actually visible. Do NOT assume a page is
structural just because it has dimension lines, hatching, or section tags — architectural
detail sheets (stairs, tiling, finishes) have those too. You must cite the concrete visual
evidence that justifies your choice, and lower confidence when that evidence is weak or absent.
Never describe evidence you do not actually see (e.g. do not claim "rebar dots" unless dots
are clearly inside a cross-section).
```

---

## User Prompt Template

> `{{page_start}}` และ `{{total_in_batch}}` ถูก inject โดย script ก่อนส่ง API

```
This batch contains {{total_in_batch}} page images.
Pages are numbered starting from {{page_start}}.
First image in this request = page {{page_start}}, second = page {{page_start + 1}}, and so on.

REQUIREMENT: You MUST return exactly {{total_in_batch}} entries in the "pages" array.
If a page is unreadable or unclear, return sheet_type: "unknown", confidence: 0.0 — do NOT skip it.

━━━ CATEGORIES ━━━

"table_of_contents"
  Visual: table/grid listing sheet numbers and titles, no engineering drawings
  Text:   "รายการแบบ", "สารบัญ", "Drawing List"

"general_notes"
  Visual: paragraphs or numbered text lists, no drawing geometry
  Text:   "หมายเหตุทั่วไป", "GENERAL NOTES", "ข้อกำหนด", fc'=…ksc, วสท.

"schedule_table"
  Visual: tabular grid — element IDs (C1/B1/ค1) in left column, rebar specs in right columns;
          may contain small cross-section sketches inside cells
  Text:   "ตารางเสา", "ตารางคาน", "COLUMN SCHEDULE", "BEAM SCHEDULE"

"floor_plan"
  Visual: bird's-eye building layout, labels scattered across page, structural grid lines visible
  Text:   element labels ค□ B□ พ□ S□; grid axes ก/ข/ค or A/B/C + 1/2/3;
          "ผังโครงสร้าง", "FRAMING PLAN", "FOUNDATION PLAN"

"section_detail"
  Visual: cross-section shapes with VISIBLE REINFORCEMENT — rebar dots inside the section,
          OR explicit rebar callouts (DB□/RB□/@□). This is the DECIDING evidence.
  Text:   DB□, RB□, @□, fc'…ksc, SD40/SR24, "ตัด A-A", "SECTION", "DETAIL"
  ⚠️ Dimension lines + hatching + a section tag ALONE do NOT make it section_detail.
     If you see a cross-section/detail but NO rebar and NO DB/RB callouts → it is
     "architectural" (finish/stair/tile detail), NOT structural.

"architectural"
  Visual: room labels, door arcs, window symbols, furniture, MEP pipe/wire symbols,
          OR finish/stair/tile detail sections that show NO reinforcement
  Text:   "ห้อง", "ประตู", "หน้าต่าง", "บันได", "ผิวปูกระเบื้อง", room area in ตร.ม.,
          sheet codes starting AR□ / A-□

"unknown"
  When: blank, unreadable, or confidence < 0.60 on any category

━━━ RULES FOR AMBIGUOUS PAGES ━━━

- Page has BOTH floor plan AND schedule table → pick whichever covers more than 60% of the area
- Schedule table with embedded cross-sections → "schedule_table"
- Reinforcement details (rebar visible) without a schedule grid → "section_detail"
- Detail/section WITHOUT any rebar or DB/RB callout → "architectural" (do not default to section_detail)
- confidence < 0.60 → always return "unknown", do not guess

━━━ CONFIDENCE DISCIPLINE (กัน over-confidence) ━━━
- Reserve confidence ≥ 0.90 for pages where the deciding evidence is unmistakable.
- If the page is a detail/section and you are inferring "structural" WITHOUT seeing rebar or
  DB/RB text, cap confidence at 0.55 and lean "architectural" or "unknown".
- confidence must reflect how strongly evidence_seen supports sheet_type — not a default 0.95.

━━━ OUTPUT FORMAT ━━━

Return ONLY valid JSON. No explanation, no text outside the JSON block.
Total entries in "pages" array MUST equal {{total_in_batch}}.

{
  "pages": [
    {
      "page_number": {{page_start}},
      "sheet_type": "floor_plan",
      "confidence": 0.88,
      "rebar_evidence": false,
      "evidence_seen": "grid lines A-1 to C-3, element labels ค1 ค2 ค3 scattered; no rebar dots",
      "key_identifiers": "structural framing plan layout"
    },
    {
      "page_number": {{page_start + 1}},
      "sheet_type": "section_detail",
      "confidence": 0.92,
      "rebar_evidence": true,
      "evidence_seen": "cross-section rectangles with rebar dots inside + 'DB16@150' callout text",
      "key_identifiers": "beam section detail"
    }
  ],
  "summary": {
    "table_of_contents": [],
    "general_notes": [],
    "schedule_table": [],
    "floor_plan": [{{page_start}}],
    "section_detail": [{{page_start + 1}}],
    "architectural": [],
    "unknown": []
  }
}
```

---

## Script: Build Payload (Node.js)

```js
/**
 * Stage A payload builder — injects page numbers before sending to Qwen
 * @param {Array} images      - [{base64, filename}] ordered by page number
 * @param {number} startPage  - 1-indexed page number of images[0]
 * @param {string} promptTemplate - raw prompt text with {{placeholders}}
 */
function buildStageAPayload(images, startPage, promptTemplate) {
  const total = images.length;

  const filledPrompt = promptTemplate
    .replaceAll('{{page_start}}', startPage)
    .replaceAll('{{total_in_batch}}', total)
    .replaceAll('{{page_start + 1}}', startPage + 1); // example — expand as needed

  const content = [{ type: 'text', text: filledPrompt }];

  images.forEach((img, i) => {
    // ฝัง label ก่อนแต่ละรูป — ช่วยให้ model ไม่ confuse page number
    content.push({ type: 'text', text: `[Page ${startPage + i}]` });
    content.push({ type: 'image_url', image_url: { url: `data:image/png;base64,${img.base64}` } });
  });

  return {
    model: 'qwen-vl-plus',
    messages: [{ role: 'user', content }],
    temperature: 0.1,
    max_tokens: 1500,
    response_format: { type: 'json_object' }
  };
}
```

---

## Script: Validate Output (Node.js)

```js
/**
 * ตรวจ Stage A output ก่อนส่ง Stage B หรือ import Label Studio
 * คืน { valid, errors, pages } — ถ้า valid === false ให้ log และ skip batch นั้น
 */
function validateStageAOutput(qwenOutput, expectedTotal, startPage) {
  const errors = [];
  const pages = qwenOutput.pages || [];

  // 1. ครบจำนวนไหม?
  if (pages.length !== expectedTotal) {
    errors.push(`Expected ${expectedTotal} pages, got ${pages.length}`);
  }

  // 2. page_number อยู่ในช่วงที่ถูกต้องไหม?
  const expectedNums = new Set(
    Array.from({ length: expectedTotal }, (_, i) => startPage + i)
  );
  pages.forEach(p => {
    if (!expectedNums.has(p.page_number)) {
      errors.push(`Unexpected page_number: ${p.page_number} (expected ${startPage}–${startPage + expectedTotal - 1})`);
    }
  });

  // 3. page_number ซ้ำไหม?
  const seen = new Set();
  pages.forEach(p => {
    if (seen.has(p.page_number)) errors.push(`Duplicate page_number: ${p.page_number}`);
    seen.add(p.page_number);
  });

  // 4. summary ตรงกับ pages[] ไหม?
  const fromPages = {};
  pages.forEach(p => {
    fromPages[p.sheet_type] = [...(fromPages[p.sheet_type] || []), p.page_number];
  });
  const summary = qwenOutput.summary || {};
  Object.entries(summary).forEach(([type, nums]) => {
    const diff = nums.filter(n => !(fromPages[type] || []).includes(n));
    if (diff.length) errors.push(`summary.${type} has [${diff}] not found in pages[]`);
  });

  // 5. sheet_type ถูก value ไหม?
  const VALID_TYPES = new Set([
    'table_of_contents','general_notes','schedule_table',
    'floor_plan','section_detail','architectural','unknown'
  ]);
  pages.forEach(p => {
    if (!VALID_TYPES.has(p.sheet_type)) {
      errors.push(`page ${p.page_number}: invalid sheet_type "${p.sheet_type}"`);
    }
  });

  return { valid: errors.length === 0, errors, pages };
}
```

---

## Script: Route Pages After Validation (Node.js)

```js
// Script ตัดสินใจ routing เอง — ไม่ใช่ Qwen
const STAGE_B1_TYPES = new Set(['floor_plan', 'section_detail', 'schedule_table']);
const STAGE_B2_TYPES = new Set(['general_notes']);

function routePages(validatedPages) {
  const stageB1 = [];
  const stageB2 = [];
  const skip    = [];

  validatedPages.forEach(p => {
    if (STAGE_B1_TYPES.has(p.sheet_type))      stageB1.push(p);
    else if (STAGE_B2_TYPES.has(p.sheet_type)) stageB2.push(p);
    else                                        skip.push(p);
  });

  return { stageB1, stageB2, skip };
}
```

---

## Script: Convert to Label Studio Tasks (Node.js)

> ⚠️ **ชื่อไฟล์จริงในโปรเจกต์** = `<houseName>_หน้า<NN>.png` (NN = เลขหน้า pad 2 หลัก, prefix ภาษาไทย)
> เช่น `บ้าน_เล็ก_1ชั้น_01_หน้า15.png` — **ไม่ใช่** `page_015.png`
> ดังนั้นอย่า "สร้าง" ชื่อไฟล์เอง ให้ map จาก list ไฟล์จริงที่อ่านมาจากโฟลเดอร์แทน

```js
const path = require('path');

/**
 * แปลง Stage A output → Label Studio tasks
 * @param {Array}  pages       - [{page_number, sheet_type, confidence, key_identifiers}]
 * @param {Array}  imageFiles  - รายชื่อไฟล์รูปจริงในโฟลเดอร์ (absolute หรือ relative path)
 *                               ordered ตาม page_number เช่น
 *                               ['.../บ้าน_เล็ก_1ชั้น_01_หน้า01.png', '...หน้า02.png', ...]
 * @param {string} houseName   - ชื่อบ้าน/ชุดแบบ เช่น "บ้าน_เล็ก_1ชั้น_01"
 * @param {string} servePrefix - base URL/path ที่ Label Studio เข้าถึงรูปได้
 *                               (เช่น "/data/local-files/?d=บ้าน_เล็ก_1ชั้น_01")
 */
function toLabelStudioTasks(pages, imageFiles, houseName, servePrefix) {
  // index รูปจริงด้วยเลขหน้า: ดึง "หน้า15" → 15 จากชื่อไฟล์
  const byPage = new Map();
  for (const f of imageFiles) {
    const m = path.basename(f).match(/_หน้า(\d+)\.png$/i);
    if (m) byPage.set(parseInt(m[1], 10), path.basename(f));
  }

  return pages.map(page => {
    const filename = byPage.get(page.page_number);
    if (!filename) {
      console.warn(`⚠️  ไม่พบไฟล์รูปสำหรับหน้า ${page.page_number} ใน ${houseName}`);
    }
    return {
      data: {
        // ชี้ไปยังไฟล์จริง — ชื่อเดียวกับที่อยู่ในโฟลเดอร์เป๊ะ
        image: `${servePrefix}/${filename ?? `MISSING_หน้า${page.page_number}.png`}`,
        page_number: page.page_number,
        source_house: houseName,
        image_filename: filename ?? null,   // เก็บชื่อไฟล์ตรงไว้ debug/trace
        key_identifiers: page.key_identifiers
      },
      predictions: [{
        model_version: 'qwen-vl-plus-stage-a',
        score: page.confidence,
        result: [{
          id: `pred_p${page.page_number}`,
          type: 'choices',
          from_name: 'sheet_type',
          to_name: 'image',
          value: { choices: [page.sheet_type] }
        }]
      }]
    };
  });
}
```

## Script: Match Stage B output → filename (Node.js)

```js
/**
 * ตั้งชื่อไฟล์ JSON ของ Stage B ให้ตรงกับรูปที่อ่าน 1:1
 * รูป: บ้าน_เล็ก_1ชั้น_01_หน้า15.png  →  JSON: บ้าน_เล็ก_1ชั้น_01_หน้า15.json
 */
function outputJsonName(imagePath) {
  return path.basename(imagePath, path.extname(imagePath)) + '.json';
}
// qwen-output/<houseName>/<ชื่อเดียวกับรูป>.json
```

---

## Batch Size Guide

| จำนวนหน้า/PDF | แบ่ง batch |
|---|---|
| ≤ 12 หน้า | 1 batch เดียว |
| 13–24 หน้า | 2 batches (12 + remainder) |
| 25+ หน้า | batch ละ 10 หน้า |

อย่าเกิน 12 รูป/batch — Qwen context window มีจำกัด และ accuracy ลดหลังหน้าที่ 12+
