# pass2_material_list.md - bill of quantities (BOQ)

**Input:** one BOQ-sheet image.
**Output:** one `pattern: "material_list"` file using `categories[].items[]` (§0.1, §11).

Prepend `../_common.md`.

---

## PROMPT START

You are reading a bill of quantities (BOQ / ใบประมาณราคา) from a construction drawing set

Output one JSON object and nothing else

```json
{
  "png": "38",
  "doc_page": 38,
  "discipline": "boq",
  "sheet_code": null,
  "sheet_name": "ประมาณราคาค่าก่อสร้าง",
  "pattern": "material_list",
  "source_image": "image/<house>/<house>_หน้า38.png",
  "sheet_no": "2/19",
  "columns": ["ลำดับที่", "รายการ", "จำนวน", "หน่วย"],
  "categories": [
    {
      "category": "หมวดงานโครงสร้าง",
      "items": [
        {
          "item_no": "1",
          "description": "- ขุดดิน",
          "quantity": 27,
          "unit": "ลบ.ม.",
          "material_unit_price": null,
          "material_amount": null,
          "labor_unit_price": null,
          "labor_amount": null,
          "total_amount": null,
          "confidence_score": 0.98,
          "confidence_flags": []
        }
      ]
    }
  ],
  "confidence_score": 0.95,
  "confidence_flags": [],
  "warnings": []
}
```

`categories[].items[]` is the container for this pattern - not `elements[]` (§0.1)
`columns[]` holds the table's own header strings verbatim, in printed order

Types - the thing most often got wrong

`quantity`, `material_unit_price`, `material_amount`, `labor_unit_price`, `labor_amount`,
`total_amount`, `confidence_score` are all numbers or `null` Never a string - `27`,
not `"27"` Never a formatted string - `1250.5`, not `"1,250.50"`

`item_no`, `description`, `unit`, `category` are strings, verbatim Thai

An empty price column is `null`, not `0` Zero is a real value meaning free, blank means not
priced on this sheet

Continuation rows are separate items (§11)

A row that continues the description of the row above, with no `item_no` and no quantity of its
own, is still its own `items[]` entry - never merged into the previous row's `description`
Write it with `item_no: null`, `quantity: null`, and its own text

Merging them silently changes what the BOQ says

Two sheets in one image (§11)

A single PNG sometimes holds two portrait pages laid out as one landscape image If you see
two complete tables side by side, each with its own header and its own `sheet_no`, that is two
sheets Extract the one you were asked for and say so in `warnings[]` - do not merge two sheets'
categories into one file

Rules

- Transcribe `description` verbatim, including the leading dash or bullet the sheet prints
  (`"- ขุดดิน"`) Do not clean it up
- `category` is the printed section heading (`"หมวดงานโครงสร้าง"`) Every item belongs to the
  category heading above it
- Read every row including the last Subtotal and grand-total rows are rows too - keep them with
  their printed text, and flag them in `confidence_flags` so a consumer does not double-count
- A cell you cannot read is `null` plus a flag naming it Never a plausible-looking number - a BOQ
  is the one sheet in the set where an invented figure looks exactly like a real one

## PROMPT END
