# SHEET LIST tail for pass0 (t07 Palfrey, decided 2026-11-11)

The 11-pass design sends the index page's sheet list to the model along with every page; the sheet
notes say the model must be trained on it before the worker sends it. t07 trains it. **The worker
does not send it yet.**

## The exact text

Appended to the pass0 user text, in the SAME text part as the prompt (no separate part), after
`PASS0_PROMPT` (the text `pass0/prompt.md` yields between `## PROMPT START` and `## PROMPT END`,
unchanged by this feature):

```python
SHEET_MARK = "\n\nSHEET LIST (from this drawing set's index page)\n"
text = PASS0_PROMPT + SHEET_MARK + json.dumps([{"title": t, "sheet_range": r}, ...], ensure_ascii=False)
```

- `json.dumps` defaults for separators (`", "` and `": "`), `ensure_ascii=False`, no trailing newline.
- Each entry has exactly two keys in this order, `title` then `sheet_range`.
- `title`: the entry's printed title, verbatim, never empty (entries without a title are dropped).
- `sheet_range`: the printed range string (e.g. `"S-01 ถึง S-08"`) or `null` when the index prints
  none (the BOQ and rules entries). Never `doc_page_start`, `doc_page_end`, `page`, `start_page` or
  any page number.
- Index order, as the GT lists them.
- Example (first two entries of a real list):
  `\n\nSHEET LIST (from this drawing set's index page)\n[{"title": "แบบสถาปัตยกรรม", "sheet_range": "A-01 ถึง A-20"}, {"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-14"}, ...]`
- The prompt text does not mention the list (same convention as the GRID MASTER tail on the plan
  prompts). Rows without a list are the prompt alone, which is what the worker sends today.

`sanitize_labels.py` has the same constant (`SHEET_MARK`) and `build_t07.py` asserts the two are
equal. Sanitize never edits the list; its leak gate counts forbidden text inside it (as
`user_extra`), and the builder drops the list of a house whose list matches the gate (house names,
file names, dates, edit-history words). 0 houses were dropped this way.

## Where the data comes from

The house's own GT index page: among the GT files with `pattern: "index"` whose `sections` is a
list in which some entry carries a `sheet_range` key, the one with the **lowest page number**.
Other index shapes in the GT (`sheet_no` / `sheet_code` / `items` / `heading` / `index_rows`) are not
used: only `title` and `sheet_range` exist in the format. A missing or blank `sheet_range` becomes
`null`.

14 of the 24 full-coverage houses have such a page (6 of them a coarse discipline list of 7-8
entries, 4 a detailed architectural list of 19-27 entries, the other 4 a list of 2-4 entries). Listed per house
in `build_report.md` and `manifest.json` (`change_2026_11_11_z_levels_and_sheet_list`).

## Which rows

Pass0 rows of those houses, about half, chosen by the parity of `sha256(row id)`: even gets the
list, odd does not (`int(sha256_hex, 16) % 2 == 0`). The rest of the pass0 rows (houses without a
usable index page) carry no list. The 400-row cap and its class balance are untouched: the list is
added after the row exists, the cap works on the view class of the label.

Final counts (MEASURED, after the cap): 400 pass0 rows; 250 belong to the 14 houses; **123 carry the
list**, 277 do not. The tail is 61-575 tokens (mean 297); the longest pass0 row grew from 8,961 to
9,529 tokens, far under MAX_LENGTH 47,104.

## What the worker must do later (not done)

`server/purson-worker/worker.py` pass0 currently calls
`_call_traced([images[p["page"]]], PASS0_PROMPT)` with no tail. A later change must send
`PASS0_PROMPT + SHEET_MARK + json.dumps(entries, ensure_ascii=False)` **byte-identical** to the
above (same mark, same dumps arguments, same two keys in the same order), the same list on every
page of the house, and only when it has a list; with no list it must keep sending the bare prompt.
Anything else is a train/serve mismatch (rule_of_tune Lesson 12).

Not decided here: where the worker gets the list. The index page is itself a page that pass0
classifies, so the worker needs either an index-first pass0 pass or a second pass0 round. Also
open: the model was trained on the list of the lowest-numbered index page; if the worker builds a
merged list across several index pages, its distribution differs from training.

## Not measured

Whether the model uses the list at all (no ablation was run), and whether the 123 rows are enough
to teach it. Treat the first Gate-2 pass0 output with and without a list as the measurement.
