# pass2_notes.md - project-level specifications

**Input:** one notes-sheet image (project-wide requirements and specifications).
**Output:** one `pattern: "notes"` file.

> **⚠️ Read this before using the prompt.** `notes` is the **worst-drifted pattern in the whole
> data set** - measured across the 11 houses on 2026-08-21: 55 notes files carry the same content
> under at least **six different container keys** (`notes` 22 files, `notes_sections` 9,
> `sections` 8, `spec_notes` 3, `notes_text` 1, `raw_text` 1) plus a long tail of one-off keys
> (`reference_standard`, `concrete_strength`, `precast_plank_spec`, `general_requirements`,
> `bangkok_additional_requirements`, `addendum`, …).
>
> The spec now names exactly two, and no others: **`sections[]`** (the verbatim transcript, §0.1)
> and **`notes{}`** (the parsed specification values, §4a - added 2026-08-21 on Makham's
> decision). Every other key is a defect. Existing files have not been migrated yet.

Prepend `../_common.md`.

---

## PROMPT START

You are reading a notes sheet - the project-wide requirements and specifications page

Output one JSON object and nothing else

```json
{
  "png": "29",
  "doc_page": 29,
  "discipline": "structural",
  "sheet_code": "S-11",
  "sheet_name": "หมายเหตุทั่วไป",
  "pattern": "notes",
  "source_image": "image/<house>/<house>_หน้า29.png",
  "sections": [
    {
      "heading": "1. ข้อกำหนดทั่วไป",
      "items": [
        "งานทั้งหมดให้เป็นไปตามมาตรฐาน ว.ส.ท.",
        "..."
      ]
    },
    {
      "heading": "2. คอนกรีต",
      "items": [
        "กำลังอัดประลัยของคอนกรีตทรงกระบอกที่ 28 วัน ไม่น้อยกว่า 210 กก./ตร.ซม.",
        "..."
      ]
    }
  ],
  "notes": {
    "reference_standard": "มยผ. 1101-52 ถึง 1106-52",
    "concrete": {
      "grade_label": "ค.3",
      "fc_ksc": 210,
      "curing_days": 28,
      "printed_as": "คอนกรีต ค.3 กำลังอัด 210 กก./ตร.ซม. ที่ 28 วัน"
    },
    "steel": {
      "round_bar":    { "notation": "RB", "grade": "SR-24", "fy_ksc": 2400, "applies_to_dia_mm": [6, 9] },
      "deformed_bar": { "notation": "DB", "grade": "SD-40", "fy_ksc": 4000, "applies_to_dia_mm": ">=12" }
    },
    "cover": {
      "default_mm": 25,
      "by_condition": [
        { "condition": "หล่อติดดิน", "cover_mm": 75 }
      ]
    },
    "fc_ksc": 210,
    "fy_main_ksc": 4000,
    "fy_stirrup_ksc": 2400,
    "cover_mm": 25
  },
  "confidence_score": 0.95,
  "confidence_flags": [],
  "warnings": []
}
```

Two containers, and only these two

`sections[]` is the verbatim transcript `notes{}` is the specification values parsed out
of it Never rename either, and never add a per-topic key of your own - a heading about concrete is
a `sections[]` entry whose `heading` says so, and its number goes in `notes.concrete` - it is not
a new top-level `concrete_strength` field

Forbidden container names, all seen in existing data `notes_sections`, `spec_notes`, `raw_text`,
`notes_text`, `reference_standard` (at top level), `concrete_strength`, `general_requirements`,
`precast_plank_spec`, `bangkok_additional_requirements`, `addendum`

`sections[]` - the transcript

Each entry is exactly

```json
{ "heading": "<the printed heading, verbatim>", "items": ["<one printed line, verbatim>", ...] }
```

It holds document structure, not drawing elements, so it correctly stays outside `elements[]`
(§0.1)

Transcribe, do not summarise or translate

- Every line is copied verbatim in Thai, exactly as printed Do not translate, do not
  paraphrase, do not shorten, do not merge two printed lines into one
- Keep the printed numbering inside `heading` (`"1. ข้อกำหนดทั่วไป"`, not `"ข้อกำหนดทั่วไป"`)
- A sub-numbered line (`1.1`, `ก)`) stays one `items[]` string with its own numbering intact
- A heading printed with no lines under it still gets an entry, with `items: []`
- A line you cannot read gets an `items[]` entry saying so plus a `warnings[]` note - never a
  reconstruction of what it probably said

`notes{}` - the parsed values (§4a)

Every value in `notes{}` must trace to a line you transcribed in `sections[]` If it is not in
the transcript, it does not go in the object Never carry a value in from another sheet, another
house, or a standard you happen to know

`steel` splits by bar notation, not by role Thai notes sheets specify steel as
RB = SR-24 = 2400 ksc and DB = SD-40 = 4000 ksc, by bar type They do not say main bars are X
and stirrups are Y Record what is printed `applies_to_dia_mm` takes an array of diameters or the
printed threshold string (`">=12"`), whichever the sheet gives

`cover` is in millimetres - it is a member dimension, so §0.5 applies A sheet printing
`0.075 ม.` becomes `cover_mm: 75` Never a `_m` field for cover `by_condition[]` is for the
several covers a sheet usually prints (cast against earth, exposed, interior), `default_mm` is the
unqualified one, and a sheet printing only one cover gets `default_mm` with an empty
`by_condition`

The four flat fields are one-way copies, not a second reading

- `fc_ksc` is a copy of `concrete.fc_ksc`
- `fy_main_ksc` is a copy of `steel.deformed_bar.fy_ksc`
- `fy_stirrup_ksc` is a copy of `steel.round_bar.fy_ksc`
- `cover_mm` is a copy of `cover.default_mm`

The main=deformed and stirrup=round pairings are the Thai convention, not a law If this
sheet states a different pairing, follow the sheet and say so in `warnings[]`

A flat field whose source is absent is `null` - never a convention-based default A missing
value means this house's notes sheet did not specify it, and that is real information

Omit `notes{}` entirely when the sheet is not a specification sheet - a purely procedural
notes page (site safety, submittal requirements) gets a `sections[]` transcript and no `notes{}`

Rules

- If the page holds more than notes (a notes column beside a drawing), this is a multi-view page -
  extract only the notes portion and say so in `warnings[]`
- A very long notes sheet is still transcribed in full If you run out of room, close the JSON
  properly and record in `warnings[]` exactly which heading you stopped at, so the rest can be
  read in a second pass A truncated file that does not parse loses everything, including the
  part you did read

## PROMPT END
