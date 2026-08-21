# pass2_schedule.md — summary tables

**Input:** one schedule-sheet image (a table where **one row = one member**).
**Output:** one `pattern: "schedule"` file.

`schedule` and `section` are **equally valid spec sources** (§7) — the fields are the same, only
the presentation differs (a table instead of a drawn cut). Everything in `pass2_section.md` about
rebar objects, the column single-`count` rule, and steel members applies here unchanged.

Prepend `../_common.md`.

---

## PROMPT START

You are reading a schedule table from a construction drawing. Each row describes one member.
Extract every row.

Output **one JSON object and nothing else**.

```json
{
  "png": "22",
  "doc_page": 22,
  "discipline": "structural",
  "sheet_code": "S-05",
  "sheet_name": "ตารางเสาและฐานราก",
  "pattern": "schedule",
  "source_image": "image/<house>/<house>_หน้า22.png",
  "columns": ["มาร์ค", "ขนาด", "เหล็กยืน", "เหล็กปลอก"],
  "elements": [ ... ],
  "confidence_score": 0.92,
  "confidence_flags": [],
  "warnings": []
}
```

`columns[]` holds the table's own header strings, verbatim and in printed order. It is a list of
plain strings — a table header, not drawing content — so it stays outside `elements[]` (§0.1).

Each row becomes one `elements[]` entry, in the same field shape a section uses:

```json
{
  "element_id": "C1",
  "element_type": "column",
  "width_mm": 200,
  "height_mm": 200,
  "main_bar": { "count": 4, "dia_mm": 12, "type": "DB" },
  "stirrup": { "dia_mm": 6, "type": "RB", "spacing_mm": 200 },
  "size_printed_as": "0.20x0.20 ม.",
  "main_bar_printed_as": "4-DB12",
  "confidence_score": 0.9,
  "confidence_flags": []
}
```

### The rules that repeat from the section prompt

- **A column uses a single `main_bar.count`, never `top`/`bottom`** — writing `top: 4, bottom: 4`
  doubles the real count to 8. Applies to columns, pedestals, short columns and fence columns.
- **A beam always splits `top`/`bottom`**, even when equal.
- `Ø` → `type: "RB"`. `stirrup` is the only name. `spacing_mm` is an integer.
- Sizes are integer millimetres; positions stay in metres. Keep the printed text in
  `*_printed_as`.
- A steel member uses `steel_section` and has no rebar fields (§6a).

### This is a table — read it as a table

- **Do not carry a value down from the row above.** A blank cell means blank: write `null`. Thai
  schedules commonly leave a cell empty where the value repeats, but they also leave it empty where
  the value genuinely does not apply, and you cannot tell which from the image alone. `null` plus
  a `warnings[]` note is correct; a filled-in guess is not.
- **Read every row, including the last.** A partially-read table is worse than a missing one,
  because it looks complete.
- **A cell you cannot read is `null` with a `confidence_flags` entry naming it** — never a
  plausible-looking number.
- If a row's mark is unreadable but the row is clearly there, keep the row with a descriptive
  `element_id` and flag it. Do not drop it.

### `schedule` vs `bbs_schedule` (§0.9, §1 #14)

If a row describes a **member** (`C1`: 200×200, 4-DB12) this is `schedule`.
If a row describes a single **cut bar** (`C1`/`T1`: Ø12, shape 00, 4.5 m, ×2) this is
`bbs_schedule` and belongs to a different subtask — say so in `warnings[]` rather than forcing the
rows into this shape.

### Rules

- `element_id` exactly as printed (§0.3).
- Two different members never share an `element_id` (§0.3). A schedule listing the same mark twice
  with different values is a real signal — keep both and flag it, do not silently pick one.
- No positions or instance counts here; those come from the plan sheets (§7).

## PROMPT END
