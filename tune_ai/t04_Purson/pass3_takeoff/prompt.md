# Pass 3 — ถอดระยะ/เหล็ก จากบัญชี element ที่ยืนยันแล้ว

**สถานะ: เขียนเต็มแล้ว ยังไม่เคยรันจริงกับโมเดล** (ย้ายมาจาก `tune_ai/t03/pass3_takeoff/`
2026-08-28 — ที่อยู่ถาวรคือที่นี่ ใน t04 ไม่ใช่ t03 อีกต่อไป จะรันได้ต้องผ่านผลทดลอง
แขน 2 vs 2.4 ก่อน ดู [`../pass2.4_hint/`](../pass2.4_hint/))

**Input:** รูปมาร์คเลข (จาก [pass 1.5](../pass1.5_cv/)) + บัญชี element ฉบับสุดท้าย
(CV ∪ โมเดล จาก [pass 2.5](../pass2.5_harvest/)) + grid master + prompt นี้
(prepend `../../t03/_common.md` — glossary ไทยติดมาด้วย)

**กฎเหล็กของ pass นี้ — บังคับด้วยโค้ด ไม่ใช่แค่ prompt:**
[`tools/merge_guard.py::merge_no_delete()`](../../../tools/merge_guard.py) รันหลังโมเดลตอบเสมอ —
element ไหนในบัญชีที่โมเดลไม่ตอบ (ไม่มี `cv_mark` ตรงกัน) จะถูกใส่กลับเป็น stub + ธง
`dropped_by_pass3` ให้คนดู โมเดลจึง**ลบอะไรไม่ได้จริง** ต่อให้ prompt ล้มเหลว

---

## `{{ELEMENT_ACCOUNT}}` — รูปแบบบัญชีที่ป้อนเข้า prompt

Runner ดึง `elements[]` จาก sidecar ของ pass 2.5 (`<stem>_cv25.json`) มาเรียงเป็นบรรทัดข้อความ
หนึ่งบรรทัดต่อหนึ่ง element ตามลำดับ `n` เดิม (ห้ามเรียงใหม่ — เลขต้องตรงกับที่มาร์คบนภาพเป๊ะ):

```
#1  column
#2  column
...
#15 footing
#16 footing
...
#29 beam_h
```

ชื่อ class (`column`/`footing`/`beam_h`/`beam_v`) เป็นแค่ป้ายบอกว่ากรอบนั้นเป็นไอคอนหน้าตาแบบไหน
**ไม่ใช่คำตอบสุดท้าย** — โมเดลยังต้องอ่านมาร์คจริงบนแบบ (เช่น F1 vs F2, C1 vs C1A) เอง ตาม
`_common.md` §0.4/§0.3

---

## PROMPT START

You are given (1) a Thai construction drawing image with numbered boxes `#n` marking elements a
computer-vision pass already found, and (2) the list below telling you what shape each numbered
box looks like (its coarse class, not its real mark).

{{ELEMENT_ACCOUNT}}

Your job: for **every** numbered box, find it on the image, read its real mark and dimensions, and
extract its full spec — size, span (for beams), and reinforcement.

Output **one JSON object and nothing else**:

```json
{
  "png": "14",
  "doc_page": 14,
  "discipline": "structural",
  "pattern": "section",
  "source_image": "image/<house>/<house>_หน้า14.png",
  "grid_source": "<house>_หน้า00_gridline.json",
  "elements": [ ... ],
  "confidence_score": 0.9,
  "confidence_flags": [],
  "warnings": []
}
```

### Every element you output carries `cv_mark` when it corresponds to a numbered box

```json
{
  "element_id": "F1",
  "element_type": "footing",
  "cv_mark": 15,
  "width_mm": 1000,
  "height_mm": 300,
  "grid_refs": ["A1"],
  "main_bar": { "count": 12, "dia_mm": 9, "type": "RB" },
  "stirrup": { "count": 1, "dia_mm": 9, "type": "RB" },
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

A fixed number of edge ties (e.g. `1-Ø9mm รัดรอบขอบฐานราก`) goes in `stirrup.count` with
`spacing_mm` **omitted** — never a top-level `stirrup_tie_count`, which schema §6b forbids
(Constistant reads `stirrup.count` only when `spacing_mm` is absent; a repeating stirrup keeps
`spacing_mm` as usual).

A beam uses `span_length_m`/`grid_ref_start`/`grid_ref_end` from the grid master exactly as in
`pass2_used/plan.md`. A footing/column uses `width_mm`/`height_mm`/`main_bar`/`stirrup` exactly as
in `pass2_used/section.md`. **This prompt does not redefine those field shapes — it only adds
`cv_mark` on top of them.**

### Rules, in priority order

1. **Never remove a numbered box from your output.** Every `#n` in the list above appears in your
   output with that `cv_mark`. If you cannot read anything about it (blurred, obstructed, or the
   box is a false positive with nothing there), output it anyway with all measurement fields
   `null` and a `confidence_flags` entry saying why — that is a correct answer, not a failure.
   [`merge_guard.py`](../../../tools/merge_guard.py) enforces this even if you get it wrong, but
   get it right anyway — a stub with no real data is worse than your own honest read.
2. **You may add elements the list missed** — a real member the CV pass did not detect. An added
   element has no `cv_mark`.
3. **Never invent a `cv_mark`.** Only use a number that appears in the list above. Guessing a
   number that isn't there is worse than leaving `cv_mark` off — `merge_guard.py` treats an unknown
   `cv_mark` as a warning-worthy anomaly, not a silent match.
4. **Two elements never claim the same `cv_mark`.** If two real members genuinely sit at one
   marked point (rare — a column-on-footing box drawn once for both), pick the element type the
   coarse class in the account most closely matches and note the other in `warnings[]`.
5. Spans come from the printed grid dimensions via the grid master — never from how long a line
   looks (`_common.md` honesty rule 1).
6. All `_common.md` rules apply unchanged (element shape, units, rebar-as-object, honesty rules,
   Thai glossary).

## PROMPT END
