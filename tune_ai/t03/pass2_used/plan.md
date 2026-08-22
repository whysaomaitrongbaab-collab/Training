# pass2_plan.md — structural plans

One prompt, four subtasks. The runner substitutes `{{TARGET}}` and `{{ELEMENT_TYPES}}` per folder:

| subtask | `{{TARGET}}` | `{{ELEMENT_TYPES}}` |
|---|---|---|
| `plan_footing` | footings (ฐานราก) and the columns marked with them | `footing`, `pile`, `pile_cap`, `pedestal`, `column` |
| `plan_column` | columns (เสา) | `column`, `pedestal` |
| `plan_beam` | beams at every level — ground beams (คานคอดิน), floor beams, ring beams (คานอะเส), roof framing (โครงหลังคา) | `beam`, `tie_beam`, `rafter` |
| `plan_slab` | floor slabs and precast plank fields | `slab`, `precast_plank_detail` |

Deliberately **one file, not four near-identical copies** — four copies drift, and drift across
same-shaped files is the exact failure this whole spec exists to stop (`primary_rawjson_schema.md`
§0). Change the rules here once and all four subtasks change together.

Prepend `../_common.md`. Requires `_shared/gridmaster.json` — the manifest's `needs` gate blocks this
subtask until it exists.

---

## PROMPT START

You are reading a structural plan sheet. Extract **{{TARGET}}**.

You are also given the building's grid master. Use it — the spans you report come from it, not
from the image.

Output **one JSON object and nothing else**.

```json
{
  "png": "20",
  "doc_page": 20,
  "discipline": "structural",
  "sheet_code": "S-03",
  "sheet_name": "แปลนคาน, พื้นชั้นล่าง",
  "pattern": "plan",
  "source_image": "image/<house>/<house>_หน้า20.png",
  "floor_level": "F1",
  "building": "main",
  "grid_source": "<house>_หน้า00_gridline.json",
  "elements": [ ... ],
  "confidence_score": 0.86,
  "confidence_flags": [],
  "warnings": []
}
```

`pattern` is `"plan"` for all four subtasks — the subtask decides what you extract, not what the
file is called.

### `floor_level`

Read it from the sheet title (`แปลนคาน ชั้นล่าง` → `"F1"`, `ชั้นสอง` → `"F2"`, a roof framing
sheet → `"RF"`). If the title does not say, use `null` and note it in `warnings[]` — do not assume
`F1`.

### Line elements vs point elements (§4)

**A beam is a line.** It gets one entry **per span between two grid points** — one atomic segment,
never merged across a whole gridline:

```json
{
  "element_id": "B2",
  "element_type": "beam",
  "grid_ref_start": "D1",
  "grid_ref_end": "D2",
  "span_length_m": 4.0,
  "span_source": "grid_table",
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

**A footing or column is a point.** All positions of one mark merge into **one** entry with an
array of refs and a count:

```json
{
  "element_id": "F1",
  "element_type": "footing",
  "grid_refs": ["A1", "A2", "B1"],
  "count": 3,
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

`grid_refs` is an array of strings, never a comma-joined string. Each ref is a point with no dash
(`"C1"`, not `"C-1"`) — §0.8.

A slab marker with no resolvable position (a circled `SO`/`SI`/`ST` tag sitting inside a bay) is
`element_type: "slab"` with `grid_refs: []`, `confidence_flags: ["marker_only_not_a_line_element"]`,
and the bays it covers described in `description`.

### `span_length_m` comes from the grid, never from the image (§4)

Look up both endpoints in the grid master and subtract.

- Both endpoints known, same row or same column → `span_source: "grid_table"`.
- The distance is printed locally on this sheet and you used that → `span_source: "local_dimension"`.
- You could not resolve it → `span_length_m: null`, `span_source: "unresolved"`, and name the
  missing line in `warnings[]`.
- The element is a point, not a line → `span_source: "n/a"`.

**Never estimate a span by how long the line looks.** A wrong span silently becomes a wrong
concrete volume and a wrong steel weight downstream.

### Every beam endpoint must land on a named line — the beam-endpoint rule (§4)

Trace every beam segment on the sheet, including short stubs and the crowded ones in stair and
closet clusters. For each endpoint, find its line in the grid master.

If an endpoint sits on no known line, the grid master is missing a dummy grid. Record the beam
with `span_source: "unresolved"` and say exactly which point could not be named in `warnings[]`,
so the grid master can be fixed.

**Three things you must never do instead** — each one silently loses a real beam:

- ❌ Drop the beam because it "isn't on the grid"
- ❌ Write a prose description with no `grid_ref_start` / `grid_ref_end`
- ❌ Set `grid_ref_start` equal to `grid_ref_end` with a `null` span

A beam bearing on another beam rather than a column is normal — record it against the dummy grid
and add a flag like `"bears_on_beam:B4(start)"`.

### Read the sheet, do not pattern-fill it

Extract what is actually drawn. A plan has a specific, finite set of members in specific places —
it is never a grid with the same beam in every cell.

If you notice yourself emitting the same `element_id` repeatedly with only the grid reference
advancing (`1-2`, `2-3`, `3-4`, `4-5`…) in a way you are not reading off the drawing, **stop and
close the JSON immediately.** A short honest file that ends properly is correct and usable. A long
repetitive one that never closes is worthless — it cannot even be parsed, so every element in it,
including the real ones you read at the start, is lost.

Twenty-five accurate beams beat two hundred invented ones.

### Rules

- `element_id` exactly as printed. `B4X` is not `B4` — an X variant is a different mark (§0.3).
- Two different members never share an `element_id` on one sheet (§0.3).
- No rebar specs here. This sheet gives position and count; the section and schedule sheets give
  the spec, joined later by `element_id` (§7).
- Anything ambiguous, blurred, or judged goes in `warnings[]`.

## PROMPT END
