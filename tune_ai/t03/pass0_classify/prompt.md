# Pass 0 — page classification

**Input:** every page image of one house, one at a time.
**Output:** one JSON object per page, merged by the runner into the `pass0.json` that
`../pass1_organize/organize.py` consumes (shape: `output_example.json`, next to this file).

Does **not** use `../_common.md` — this pass classifies, it does not extract.

Two things make this the highest-stakes prompt in the pipeline:
1. Pass 1 routes purely on what this pass says. A page labelled wrong is extracted by the wrong
   subtask with the wrong prompt, or lands in Pass 3 and never reaches the BOQ at all.
2. It must emit the **destination subtask**, not one of the 19 `pattern` values in
   `primary_rawjson_schema.md` §1 — Pass 1 has to route a plan page to one of seven folders and
   `pattern: "beam_plan"` alone cannot tell it which (the plan family names the sheet, not the extraction).

---

## PROMPT START

You are looking at one page of a Thai construction drawing set. Classify it. Do not extract any
data from it.

Output **one JSON object and nothing else** — no prose, no markdown fence.

```json
{
  "png": "20",
  "doc_page": 20,
  "sheet_code": "S-03",
  "sheet_name": "แปลนคาน, พื้นชั้นล่าง",
  "discipline": "structural",
  "building": "main",
  "views": [
    { "subtask": "plan_beam", "where": "full", "also_gridline": true }
  ],
  "confidence_score": 0.9,
  "warnings": []
}
```

### Fields

- **`png`** — the page number as a string, from the image filename.
- **`doc_page`** — the page's position in the document, as a number.
- **`sheet_code`** / **`sheet_name`** — read them from the **title block** (the tall panel on the
  right edge). These are required and they matter beyond this pass: the title block is cropped
  away before the extraction passes see the page, so this is the **only** chance to capture them.
  If the title block is unreadable, use `null` and say so in `warnings[]` — never invent a code.
- **`discipline`** — one of: `structural` · `architectural` · `sanitary` · `electrical` ·
  `mechanical` · `boq` · `material_list` · `general` · `front_matter` · `regulatory` · `misc`.
  Write `architectural`, never `architecture`.
- **`building`** — `"main"`, or the Thai name of the outbuilding this sheet belongs to
  (e.g. `"สุขา"`). A house with a separate outbuilding has a separate grid for it, so getting
  this wrong means one building's grid gets used to measure another's beams.
- **`views[]`** — one entry per distinct drawing on the page. See below.
- **`warnings[]`** — anything unreadable, ambiguous, or that you had to judge.

### `views[]` — the unit of work is a view, not a page

A page can hold more than one drawing. Inventory **every** drawing on the page before writing
anything; a missed view is a silently lost sheet. Pages with three views exist.

Each view entry:

- **`subtask`** — the destination, from the list below. Not a `pattern` value.
- **`where`** — where the view sits on the page, so it can be cropped out:
  - `"full"` — the page holds one drawing
  - `"top"` / `"middle"` / `"bottom"` — the page is split into horizontal bands
  - `"left"` / `"center"` / `"right"` — the page is split into vertical columns
  - Use **one** vocabulary per page. Never mix rows and columns.
- **`also_gridline`** — `true` when this view prints column-grid markers (circled letters/numbers
  along its edges) **or** a level band (`+3.75 ระดับหลังคาน`, `±0.00 ระดับอ้างอิง`). Set it
  generously: a view that shows either of those is a real source for the grid master, and
  elevations and sections are the **only** place levels are printed at all.

### Choosing `subtask`

**Structural — these feed the quantity take-off:**

| The drawing shows | `subtask` |
|---|---|
| Footing layout, spread or pile (แปลนฐานราก) | `plan_footing` |
| Column layout | `plan_column` |
| Beams at any level: ground beams (คานคอดิน), floor beams, ring beams (คานอะเส), **and roof framing (แปลนโครงหลังคา)** | `plan_beam` |
| Floor slab / precast plank layout | `plan_slab` |
| A detail cut showing rebar and dimensions of a member | `section` |
| A table summarising members (one row = one member) | `schedule` |
| A bar-bending / cut-list table (one row = one **bar**) | `bbs_schedule` |
| Project-wide concrete/steel specifications | `notes` |
| A bill of quantities | `material_list` |
| A dedicated grid-reference sheet | `gridline` |
| A borehole log — SPT counts, strata, groundwater | `soil_boring_log` |

**Non-structural:**

| The drawing shows | `subtask` |
|---|---|
| Room layout, bathroom plan, balcony, furniture | `plan_architectural` |
| Lighting, outlets, air-conditioning, fans | `plan_electrical` |
| Water supply, drainage, rainwater, septic | `plan_sanitary` |
| **Architectural** roof plan — ridge/hip lines, eave overhang, roofing material, no structural marks | `roof_plan` |
| Site layout, boundaries, setbacks | `site_plan` |
| Elevation (รูปด้าน) or building section — not top-down, no rebar | `side_profile` |
| Drawing-set table of contents | `index` |
| Cover page | `title` |
| Symbol / legend page | `symbol` |
| Series price table, catalogue, promotional page | `misc` |

### Title-block wording → `subtask` (glossary, not a rule)

The title block is Thai and every `subtask` above is English. These are the exact wordings that
appear in our own drawing sets, most frequent first. Read the title block first, then confirm
against what the drawing actually shows — the wording narrows the choice, the drawing decides it.

| printed in the title block | `subtask` |
|---|---|
| ผังบริเวณ | `site_plan` |
| แปลนฐานรากแผ่ · แปลนฐานรากเสาเข็ม · ผังโครงสร้างฐานราก | `plan_footing` (+ `plan_column` if column marks share the sheet) |
| ผังโครงสร้างชั้นล่าง · ผังโครงสร้างชั้นบน · แปลนพื้นชั้น N | `plan_beam` และ/หรือ `plan_slab` — one view each if both are drawn |
| แปลนโครงหลังคา · ผังโครงสร้างหลังคา | `plan_beam` (โครง = framing → structural) |
| แปลนหลังคา (ไม่มี mark/กริด) | `roof_plan` (architectural) |
| รูปด้าน 1-4 | `side_profile` + `also_gridline: true` |
| รูปตัด N | มีเหล็กเสริม → `section` · ไม่มี → `side_profile` |
| แบบขยาย… (บันได ST.n · ห้องน้ำ WC.n · ประตู-หน้าต่าง · รั้ว · ราวกันตก · เชิงชาย) | `plan_architectural` |
| แบบขยายระบบสุขาภิบาล… · ตารางระยะการแขวนท่อ | `plan_sanitary` |
| แปลนไฟฟ้าแสงสว่าง · แปลนเต้ารับไฟฟ้า · รายละเอียดแผงเมนสวิตช์ | `plan_electrical` |
| รายการประกอบแบบ | `notes` |
| รายการวัสดุ · รายการปริมาณวัสดุและแรงงาน | `material_list` |
| สารบัญ · สารบัญแบบ… | `index` |
| รายการสัญลักษณ์ประกอบแบบ · สัญลักษณ์… | `symbol` |
| คณะผู้จัดทำโครงการ… | `title` |
| หลักเกณฑ์และข้อกำหนด… | `misc` |

Words worth knowing on their own: `แปลน`/`ผัง` = plan (top-down) · `โครงสร้าง` = structural ·
`โครง` = framing · `แบบขยาย` = enlarged detail · `รูปด้าน` = elevation · `รูปตัด` = section ·
`ชั้นล่าง`/`ชั้นบน` = ground/upper floor · `รายการ` = schedule or list · `สารบัญ` = contents.

A wording not in this table is not permission to coin a subtask — fall back to the tables above.

### Two traps that have already cost real data

1. **Roof framing is `plan_beam`, not `roof_plan`.** A แปลนโครงหลังคา carrying beams or purlins
   with element marks and grid references is a structural beam plan. `roof_plan` is reserved for
   the architectural roof sheet — ridge and hip lines, eave overhangs, roofing material, no
   structural marks. In the existing data 8 of 11 houses got this wrong, and every roof beam in
   those houses was silently missing from the quantity take-off. If the sheet has marks and grid
   refs on it, it is `plan_beam`.

2. **An elevation is never "just a picture".** Elevations reprint the column-grid markers with a
   full dimension chain, and they carry the level band that appears nowhere else in the set. The
   view itself is `side_profile`, but it must be flagged `also_gridline: true`.

### Rules

- Classify only what you can see. If a page does not fit any subtask above, use `misc` and
  explain in `warnings[]` — never coin a new subtask name.
- If you cannot tell how many views a page has, say so in `warnings[]` and give your best single
  view rather than inventing a split. Pass 1 will send the whole page through and flag it.
- Never guess `sheet_code`. `null` plus a warning is correct; a plausible-looking invented code
  is not.

## PROMPT END
