# pass2_soil_boring_log.md — soil investigation / borehole log

**Input:** one borehole-log image (รายงานเจาะสำรวจดิน).
**Output:** one `pattern: "soil_boring_log"` file.

Marked *(draft)* in `primary_rawjson_schema.md` §1 #15 — the field set has not been verified
against a real extraction yet. Everything below the wrapper level is the spec's stated shape, not
a proven one; expect to revise after the first real sheet.

This sits in Pass 2 rather than Pass 3 because Constistant consumes it — through a different door
than the raw-JSON import (Site Investigate → Foundation Design's bearing-capacity calculation).

Prepend `../_common.md`.

---

## PROMPT START

You are reading a soil investigation report — a borehole log. This is not a drawing of the
building: it has no grid references, no element marks, and no rebar.

Output **one JSON object and nothing else**.

```json
{
  "png": "03",
  "doc_page": 3,
  "discipline": "general",
  "sheet_code": null,
  "sheet_name": "รายงานผลการเจาะสำรวจดิน",
  "pattern": "soil_boring_log",
  "source_image": "image/<house>/<house>_หน้า03.png",
  "borehole_id": "BH-1",
  "groundwater_level_m": 1.8,
  "elements": [
    {
      "element_id": "layer_1",
      "element_type": "soil_layer",
      "depth_from_m": 0.0,
      "depth_to_m": 3.0,
      "soil_description": "ดินถมปนทราย",
      "uscs": "SM",
      "spt_n": 8,
      "unit_weight_kn_m3": 17.6,
      "depth_printed_as": "0.00 - 3.00",
      "confidence_score": 0.9,
      "confidence_flags": []
    }
  ],
  "confidence_score": 0.88,
  "confidence_flags": [],
  "warnings": []
}
```

`borehole_id` and `groundwater_level_m` sit at the **wrapper level** — they describe the hole, not
a layer. Each stratum is one `elements[]` entry with `element_type: "soil_layer"` (§0.1: the
container is `elements[]` like everything else).

### Layers

- `element_id` — the printed layer label if there is one, otherwise `layer_1`, `layer_2`… in
  printed order, top of hole first (§0.2 allows a descriptive id; never leave it absent).
- Depths are in **metres** as numbers (`depth_from_m`, `depth_to_m`) — a depth is a position, not
  a member size, so metres is correct here (§0.5). Keep the printed range in
  `depth_printed_as`.
- `soil_description` is the printed Thai description, verbatim.
- `uscs` is the printed classification symbol (`SM`, `CH`, `CL`…) when the log prints one.
- Unit weight is `unit_weight_kn_m3` as a number. **Thai logs commonly print γt in t/m³** — if the
  sheet prints `1.80 ต/ม³`, convert (×9.81) and keep `1.80 ต/ม³` in `unit_weight_printed_as`.
  Never record a t/m³ figure in a `_kn_m3` field.

### SPT N-values

- A plain number → `spt_n` as a number.
- **`R`, `Refusal`, or `>100`** means the sampler could not advance — record `spt_n: 100`,
  add `confidence_flags: ["spt_refusal"]`, and keep the printed text in `spt_n_printed_as`.
  Do not write `null`: refusal is a real, meaningful reading (very dense/hard stratum), and a
  `null` reads downstream as "not tested".
- A blow-count triple (`5-8-11`) → `spt_n` = the **sum of the last two** (the standard N value),
  full text in `spt_n_printed_as`.

### Groundwater

`groundwater_level_m` is the depth below ground surface, positive downward, as printed.
**If the log does not report a groundwater level, write `null` and say so in `warnings[]`.**
Do not substitute a regional estimate — a consumer that wants an estimate has its own source for
one, and a guessed value here is indistinguishable from a measured one.

### Rules

- Lab results (Atterberg limits, unconfined compression, specific gravity) go on the layer they
  belong to, using the printed field name in a `*_printed_as` sibling when you are unsure of the
  canonical key — and say in `warnings[]` that you introduced a key, so the next house reuses it
  instead of inventing a third spelling (§0.4's rule, applied to fields).
- Read every stratum including the last, and including a thin one.
- No grid references anywhere in this file.

## PROMPT END
