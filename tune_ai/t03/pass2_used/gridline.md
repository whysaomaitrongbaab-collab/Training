# pass2_gridline.md — the grid master

**Input:** every image in `pass2/gridline/images/` at once (dedicated grid sheets when the house
has them, plus every view Pass 0 flagged `also_gridline: true` — plans, elevations, sections).
**Output:** one `grid{}` file for the building, per `primary_rawjson_schema.md` §4.

Runs **first** in Pass 2. Every plan subtask blocks on it: spans are computed from this file and
from nothing else.

Prepend `../_common.md`.

---

## PROMPT START

You are reading every sheet of one building that shows a column grid, a dimension chain, or a
level. Build the single grid master for that building.

Output **one JSON object and nothing else**.

```json
{
  "png": "00",
  "doc_page": null,
  "discipline": "structural",
  "sheet_code": null,
  "sheet_name": null,
  "pattern": "grid_master",
  "source_pages": ["image/<house>/<house>_หน้า15.png", "image/<house>/<house>_หน้า20.png"],
  "grid": {
    "x_lines": [
      { "id": "1", "pos_m": 0.0, "type": "named" },
      { "id": "2", "pos_m": 4.0, "type": "named" },
      { "id": "3", "pos_m": 7.0, "type": "named" },
      { "id": "3'", "pos_m": 7.6, "type": "dummy" }
    ],
    "y_lines": [
      { "id": "D", "pos_m": 0.0, "type": "named" },
      { "id": "C", "pos_m": 4.0, "type": "named" },
      { "id": "B", "pos_m": 6.0, "type": "named" },
      { "id": "A", "pos_m": 9.5, "type": "named" }
    ],
    "z_levels": [
      { "id": "ระดับอ้างอิง",    "level_m": 0.0,  "type": "datum", "source_image": "..." },
      { "id": "ระดับพื้นชั้น 1", "level_m": 0.6,  "type": "named", "source_image": "..." },
      { "id": "ระดับหลังคาน",   "level_m": 3.75, "type": "named", "source_image": "..." }
    ],
    "dimension_chains": [
      {
        "axis": "x",
        "source_image": "...",
        "segments": [
          { "from": "edge", "to": "1", "value_m": 1.30 },
          { "from": "1", "to": "2", "value_m": 4.00 },
          { "from": "2", "to": "3", "value_m": 3.00 },
          { "from": "3", "to": "edge", "value_m": 0.60 }
        ]
      },
      {
        "axis": "z",
        "source_image": "...",
        "segments": [
          { "from": "ระดับอ้างอิง", "to": "ระดับพื้นชั้น 1", "value_m": 0.60 },
          { "from": "ระดับพื้นชั้น 1", "to": "ระดับหลังคาน", "value_m": 3.15 },
          { "from": "ระดับอ้างอิง", "to": "ระดับหลังคาน", "value_m": 3.75 }
        ]
      }
    ],
    "unassigned_dimensions": [
      { "value_m": 0.10, "label": "บัวปูนปั้น กว้าง 0.10 ม", "source_image": "...", "note": null }
    ]
  },
  "confidence_score": 0.9,
  "confidence_flags": [],
  "warnings": []
}
```

`png` is `"00"` and `doc_page` is `null` — this file is synthesized, it has no printed page
(§2). Use `source_pages[]`, an array of every image you read, instead of `source_image`.

### The rule that governs this whole pass

**Sweep every page you were given. Record every printed dimension you find. Nothing gets dropped
for not fitting a category.** A sheet with numbers printed on it that contributes nothing to this
file has not been read.

### `x_lines` / `y_lines` — the plan axes (§4)

- `x_lines` = the horizontal axis, markers along the top edge (usually `1`, `2`, `3`…).
  `y_lines` = the vertical axis, markers along the side edge (usually `A`, `B`, `C`… — Thai
  `ก`/`ข`/`ค` stays Thai).
- `pos_m` is **always read off a printed dimension line. Never estimated, never scaled off the
  image.**
- **Origin `0.0` is the leftmost / topmost `type: "named"` line.** A dummy line never takes the
  origin; one that falls before it gets a **negative** `pos_m`.
- The same line appearing on several sheets is **one entry**. If two sheets print different
  positions for the same line, keep the first, and put both values in `warnings[]`.

### Dummy grids (§4)

A structural line that is not on a printed main grid gets a prime appended to the main grid
**above it** (y-axis) or **to its left** (x-axis) — **direction, not nearest**. A line at 5.2
between `2`(5.0) and `3`(8.5) is `2'`, even though `2` is far closer.

Several dummies in one gap: scan left→right (x) or top→bottom (y); first is `A'`, next `A''`.

**How to find them — the beam-endpoint rule.** If a beam's start or end does not sit on any known
line, that point needs a dummy grid. A beam always lands on something; if there is nowhere to name
its landing point, the grid master is incomplete, not the beam. Read the new line's `pos_m` off
the printed dimension chain.

**But do not invent a dummy for a slab-only edge.** A dashed slab boundary, a roof overhang, or an
eave line with no beam label and no columns at its corners is not a structural line. The trigger
is a beam endpoint, nothing else.

### `z_levels[]` — the vertical axis

Levels are printed on elevations and sections and **nowhere else in the set**. If elevation
sheets were given to you, this array should not be empty.

- **`id` is the printed Thai label, verbatim.** `"ระดับหลังคาน"`, not `"roof beam level"`, not
  `"F1"`. A level printed with only a number and no label gets `id: null`.
- `type`: `datum` for the ±0.00 reference, `named` for a labelled level, `dummy` for a level the
  dimension chain implies but never labels.
- `level_m` is signed relative to the datum, as printed. `"±0.00"` → `0.0`, `"+3.75"` → `3.75`,
  a below-datum level → negative.
- One set of levels per building, merged across every sheet that prints them.

### `dimension_chains[]` — every printed dimension row

One entry per printed row of dimensions, per sheet. `axis` is `x`, `y`, or `z`.

- `from` / `to` name a grid `id` (or a `z_levels[]` `id` on the z axis) when that end sits on one,
  or the literal string `"edge"` when it is a building or slab edge with no grid line.
  **Never invent a grid id just to fill this in.**
- Record **every row printed, including the cumulative total row** — the `3.75` that equals
  `0.60 + 3.15`, the `7.00` that equals `4.00 + 3.00`. It is arithmetically redundant and that is
  the point: a mismatch between the detail row and the total row is a reading error caught for
  free.
- The same chain reprinted on three sheets gets three entries with three different
  `source_image` values. **Do not deduplicate across sheets.**

### `unassigned_dimensions[]` — the catch-all

Every printed number that did not land in a chain or a level goes here.

```json
{ "value_m": 0.10, "label": "บัวปูนปั้น กว้าง 0.10 ม", "source_image": "...", "note": null }
```

- `label` is the printed text verbatim, Thai stays Thai.
- `note` is optional and only for a real observation — leave it `null` rather than inventing an
  interpretation.
- **This array is what makes "nothing gets dropped" true.** A sheet with numbers on it and nothing
  here means you stopped reading, not that the sheet was clean.

### Recording genuine uncertainty (§4, optional — skip on a clean file)

- Per-line `confidence_score` / `confidence_flags` on one `x_lines[]` / `y_lines[]` entry, when
  one specific line is less certain than the rest. Better than dragging the whole file's score
  down.
- `dummy_grid_rule_check` (sibling of `grid`) — one short sentence per rule, when naming or
  prime-ordering or a negative `pos_m` took a judgment call.
- `non_grid_dimensions_do_not_confuse[]` (sibling of `grid`) — a dimension elsewhere in the set
  that coincidentally matches a grid value and could mislead a later reader.

Do not add these to a file that does not need them.

### Rules

- Every `pos_m` and every `level_m` traces to a printed number. If a line is clearly there but its
  position is printed nowhere, record the line with `pos_m: null` and explain in `warnings[]` —
  never scale it off the image.
- One grid master per building. If the sheets you were given cover more than one building, extract
  the main building only and name the others in `warnings[]`.

## PROMPT END
