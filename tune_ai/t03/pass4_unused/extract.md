# pass4 extract.md — the patterns nothing reads yet (เดิมเรียก pass 3 — renumbered 2026-08-26, ดู pass_design_v2.md)

One prompt for all eight Pass 4 subtasks. The runner substitutes `{{PATTERN}}`, `{{TARGET}}` and
`{{NEEDS_GRID}}`.

| subtask | `{{PATTERN}}` | `{{TARGET}}` | grid? |
|---|---|---|---|
| `plan_architectural` | `plan` | rooms, doors, windows, walls, fixtures, furniture | yes |
| `plan_electrical` | `plan` | lighting points, outlets, fans, air-conditioning | yes |
| `plan_sanitary` | `plan` | pipes, fittings, fixtures, septic tanks, grease traps, manholes | yes |
| `roof_plan` | `roof_plan` | ridge and hip lines, eave overhangs, slope arrows, roofing material | yes |
| `site_plan` | `site_plan` | boundaries, setbacks, building footprint, roads, levels | yes |
| `side_profile` | `side_profile` | elevation or building section — levels, openings, materials | yes |
| `index` | `index` | the drawing-set table of contents | no |
| `title` | `title` | cover-page information | no |
| `symbol` | `symbol` | the symbol / legend table | no |
| `misc` | `misc` | series price table, catalogue, promotional content | no |
| `bbs_schedule` | `bbs_schedule` | bar-bending schedule — one row per **cut bar** | no |

Nothing in Constistant reads any of these today. They are extracted so the archive is complete
and so a future consumer does not have to re-read the drawings — **which is exactly why the
honesty rules matter more here, not less: nobody downstream will notice an invented value.**

One prompt rather than eleven near-identical files, for the same reason `pass2_plan.md` is one
file: eleven copies drift.

Prepend `../_common.md`.

---

## PROMPT START

You are reading a **{{PATTERN}}** sheet from a Thai construction drawing set. Extract
**{{TARGET}}**.

Output **one JSON object and nothing else**.

```json
{
  "png": "37",
  "doc_page": 37,
  "discipline": "electrical",
  "sheet_code": "E-02",
  "sheet_name": "แปลนไฟฟ้าแสงสว่าง",
  "pattern": "{{PATTERN}}",
  "source_image": "image/<house>/<house>_หน้า37.png",
  "floor_level": "F1",
  "building": "main",
  "elements": [ ... ],
  "confidence_score": 0.9,
  "confidence_flags": [],
  "warnings": []
}
```

`pattern` is the value from the table above — not the subtask name. Three of the plan subtasks all
write `pattern: "plan"`.

Include `grid_source` and resolve `grid_ref` values against the grid master **only when
`{{NEEDS_GRID}}` is yes and the sheet actually prints grid markers**. A sheet with no grid markers
gets no `grid_ref` fields — do not manufacture positions for it.

### Elements

Every entry carries the four required fields (§0.2) and uses an established `element_type` from
the list in the common block (§0.4). Reach for `room`, `door`, `window`, `wall`,
`sanitary_fixture`, `vent_pipe`, `fitting`, `accessory`, `furniture`, `electrical_outlet`,
`ceiling_downlight_point`, `ceiling_fan`, `symbol_legend_entry`, `sheet_index_entry`, `level`,
`note` before inventing anything. If you must invent one, say so in `warnings[]`.

Nothing on these sheets carries a printed mark most of the time. An unmarked element takes a
descriptive `element_id` built from its type plus the room or a running number —
`"ceiling_fan_นอน1"`, `"vent_pipe_2"` — never an absent id, and never something dressed up to
look like a real drawing mark (§0.3).

### `bbs_schedule` specifically

One row = **one cut bar**, not one member. `bar_mark`, `shape_code`, the bend dimensions
`len_A_mm` / `len_B_mm` / `len_C_mm`, `qty`, `grade`. If you find yourself writing a row that
describes a member (`C1`: 200×200, 4-DB12) this is a `schedule` sheet, not a `bbs_schedule` one —
say so in `warnings[]` (§0.9).

### `site_plan` specifically

`element_type` on site plans has **never been standardised** — the existing houses used ten
different strings for overlapping ideas (`boundary_line` / `lot_boundary`,
`building_footprint` / `building_outline`, …). Pick the closest established value, and record what
you chose and why in `warnings[]` so the eventual canonical list is built from evidence rather
than another round of invention.

### `side_profile` specifically

An elevation is not decoration. It carries the **level band** (`+3.75 ระดับหลังคาน`,
`±0.00 ระดับอ้างอิง`) that appears nowhere else in the set, and it usually reprints the column
grid with a full dimension chain. Record every level you can see as `element_type: "level"` with
`level_m` and the printed Thai label kept verbatim — the grid master pass reads the same sheet for
the same values, and the two must agree.

### The rules that matter most here

- **A dimension that is not printed is `null`.** These sheets are the easiest place to estimate
  from the image and the least likely place anyone will catch it.
- **Something you can see but cannot resolve still gets an entry**, with the unreadable fields
  `null` and a flag naming what was unreadable. Never drop it.
- **Transcribe Thai verbatim.** Room names, material notes, legend text — never translated, never
  paraphrased.
- **Never repeat an entry to fill space.** Close the JSON instead. A short file that parses is
  worth more than a long one that does not.

## PROMPT END
