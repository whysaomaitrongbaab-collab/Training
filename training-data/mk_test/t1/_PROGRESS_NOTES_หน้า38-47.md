# Progress notes — BOQ extraction, บ้าน_เล็ก_1ชั้น_01, หน้า 38-47 (แบบฐานรากแผ่)

Stopped mid-task per user request (2026-07-05). Resume here tomorrow.

## Key structural discovery (applies to all remaining pages)

Each source PNG (e.g. `..._หน้า40.png`) is a landscape scan containing **two separate BOQ sheets side by side**, each rotated 90°. To read them:

```python
from PIL import Image
im = Image.open(r"...หน้าNN.png")
w, h = im.size
left  = im.crop((0, 0, w//2, h)).rotate(90, expand=True)
right = im.crop((w//2, 0, w, h)).rotate(90, expand=True)
# upscale 2-2.2x with Image.LANCZOS, then crop to ~50% width (description+qty+unit
# columns together — do NOT split desc and qty/unit into separate crops, it breaks
# row alignment when descriptions wrap to 2 lines) and Read it.
```

- Physical **RIGHT** half of the image = the LOWER/earlier "แผ่นที่ N/19" sheet number.
- Physical **LEFT** half of the image = the HIGHER/later "แผ่นที่ N+1/19" sheet number.
- This held consistently for pages 38 (right=1/19, left=2/19) and 39 (right=3/19, left=4/19).
- Expected pattern going forward (NOT YET VERIFIED past page 39): page 40 right=5/19 left=6/19, page 41 right=7/19 left=8/19, page 42 right=9/19 left=10/19, page 43 right=11/19 left=12/19, page 44 right=13/19 left=14/19, page 45 right=15/19 left=16/19, page 46 right=17/19 left=18/19, page 47 right=19/19 left=? (only 19 sheets total in this BOQ book — left half of page 47 may be something else, e.g. start of the pile-foundation BOQ variant, or blank — CHECK, don't assume).
- Price/amount columns (ราคาวัสดุ, ค่าแรงงาน, รวม) are blank on every sheet seen so far — expected for this document.
- Some sheets are "index/summary" sheets (unit column literally prints the word "รวม" instead of a physical unit, no quantities) rather than itemized material lists — these still get `pattern: "material_list"` per the task spec, just with mostly-null quantity fields.
- Multi-line printed descriptions: when a BOQ row's Thai text wraps onto a second printed table row with NO item_no and NO quantity/unit of its own (e.g. a "โครงเคร่า..." framing-spec continuation line under a ceiling/roof material line), transcribe it as its **own separate item** with `item_no: null`, `quantity: null`, `unit: null` — do NOT merge it into the previous item's description. (Verified precisely via combined desc+qty+unit crop on page 40 left half — separate table rows really do get separate null-qty entries; only merge when it's visually one single printed line.)

## Files already written (DONE, do not redo)

- `บ้าน_เล็ก_1ชั้น_01_หน้า38_1.json` — sheet 1/19, "สรุปงาน" (cover/summary of the 5 top-level categories, all blank qty/price, unit literally "รวม" for items 1-4).
- `บ้าน_เล็ก_1ชั้น_01_หน้า38_2.json` — sheet 2/19, หมวดงานโครงสร้าง part 1 (ขุดดิน...เทคอนกรีตทับหน้า, 16 items, fully transcribed and cross-checked against a rotated/zoomed crop — high confidence, matches old OCR reference in numbers though several old descriptions were OCR-garbled and have now been corrected from a fresh read, e.g. "ทรายราดน้ำอัดแน่น" not "ทรายรากน้ำย้ายานุ", "เสาค้ำ" not "เสาคาน", "แบบหล่อคอนกรีต"/"ค่าแรงแบบหล่อคอนกรีต"/"ค้ำยันแบบหล่อคอนกรีต" not the garbled versions).
- `บ้าน_เล็ก_1ชั้น_01_หน้า39_1.json` — sheet 3/19, หมวดงานโครงสร้าง part 2 (งานเหล็กรูปพรรณ: 4 items - ⊏150x75x25x3.2mm 323kg, ⊏100x50x20x3.2mm 550kg, PL.หนา6mm 8kg, ทาสีกันสนิม 76ตร.ม.) + total row "รวมข้อ 1 หมวดงานโครงสร้าง".
- `บ้าน_เล็ก_1ชั้น_01_หน้า39_2.json` — sheet 4/19, หมวดงานสถาปัตยกรรม index (2.1-2.8 sub-category list, all unit="รวม", no quantities) + total row "รวมข้อ 2 หมวดงานสถาปัตยกรรม".

## In progress — NOT YET WRITTEN to JSON (data already transcribed below, just need to be turned into the two page-40 JSON files)

### page 40 RIGHT half → sheet 5/19 (expected) → continues หมวดงานสถาปัตยกรรม, subsection "2.1 งานหลังคา" (roof work)
Category: หมวดงานสถาปัตยกรรม
Items (all confirmed via zoomed crop, high confidence):
1. item_no "2.1" (header) description "2.1 งานหลังคา", quantity null, unit null
2. description "- หลังคาเหล็กรีดลอน หนา 0.4 มม. พร้อมติดตั้ง PE.FOAM หนารวม 6 มม.", quantity 115, unit "ตร.ม."
3. description "- ครอบหลังคา FLASHING", quantity 43, unit "เมตร"
4. description "- เชิงชายไฟเบอร์ซีเมนต์ ขนาด 8\" หนา 12 มม.", quantity 43, unit "เมตร"
5. total row description "รวมข้อ 2.1 งานหลังคา", quantity null, unit null, item_no null

(NOTE: only 3 material rows were visible in the crops read so far — double-check there isn't a 4th/5th row hidden between "เชิงชายไฟเบอร์ซีเมนต์..." and the total row; the right-half crops used (`p40_right_c1.png`, `p40_right_c2.png` in scratchpad `crops/`) should still be viewable to re-confirm, or re-crop from source fresh.)

### page 40 LEFT half → sheet 6/19 (expected) → หมวดงานสถาปัตยกรรม, subsection "2.2 งานฝ้าเพดาน" (ceiling work)
Category: หมวดงานสถาปัตยกรรม
Items (fully confirmed via combined desc+qty+unit crop `p40_left_desc_qty.png` — high confidence, exact row alignment verified):
1. item_no null, description "2.2 งานฝ้าเพดาน" (header), quantity null, unit null
2. item_no "ฝ1", description "- ฝ้าเพดานแผ่นยิบซั่ม หนา 9 มม. รอยต่อฉาบเรียบ", quantity 48, unit "ตร.ม."
3. item_no null, description "โครงเคร่าเหล็กชุบสังกะสี @ 0.60 x 1.00 ม.", quantity null, unit null
4. item_no "ฝ2", description "- ฝ้าเพดานแผ่นยิบซั่มชนิดทนชื้น หนา 9 มม.", quantity 5, unit "ตร.ม."
5. item_no null, description "โครงเคร่าอลูมิเนียมอบสี ที-บาร์ @ 0.60 x 1.20 ม.#", quantity null, unit null
6. item_no "ฝ3", description "- ฝ้าเพดานแผ่นไฟเบอร์ซีเมนต์ หนา 4 มม. ตีชนชิด", quantity 19, unit "ตร.ม."
7. item_no null, description "โครงเคร่าเหล็กชุบสังกะสี @ 0.60 x 1.20 ม.", quantity null, unit null
8. item_no "ฝ4", description "- ฝ้าเพดานแผ่นไฟเบอร์ซีเมนต์ หนา 4 มม. มีช่องระบายอากาศ ตีชนชิด", quantity 54, unit "ตร.ม."
9. item_no null, description "โครงเคร่าเหล็กชุบสังกะสี @ 0.60 x 1.20 ม.", quantity null, unit null
10. item_no "ฝ5", description "- ฝ้าเพดานผิวฉาบปูนเรียบ", quantity 6, unit "ตร.ม."
11. item_no null, description "- แผ่นฉนวนกันความร้อนหุ้มอลูมิเนียมฟอย์ลรอบด้าน หนา 6\"", quantity 132, unit "ตร.ม."
12. item_no null, description "- มอบฝ้าไฟเบอร์ซีเมนต์ หนา 8 มม. กว้าง 3\"", quantity 95, unit "เมตร"
13. total row description "รวมข้อ 2.2 งานฝ้าเพดาน", quantity null, unit null, item_no null

STILL TO DO before writing page 40 JSON files:
- Re-verify page 40 right-half sheet number and re-check for any 4th roof item (re-crop/re-read).
- Confirm doc_page (printed bottom page number) for page 40 — was not found for page 39 either (came up blank in corner crops); may need a different crop location, or may genuinely be absent/only present on some sheets. OK to leave null with a warning if not found.
- Write `บ้าน_เล็ก_1ชั้น_01_หน้า40_1.json` (sheet 5/19, roof) and `บ้าน_เล็ก_1ชั้น_01_หน้า40_2.json` (sheet 6/19, ceiling) using the schema shown in the already-completed files as a template.

## Not started at all

Pages 41, 42, 43, 44, 45, 46, 47 — no image reads done yet. Expect each to split into 2 files (sheet N/19 and N+1/19) following the same right=lower/left=higher convention, but VERIFY each page's footer "แผ่นที่ N/19" text rather than assuming — the content categories will likely continue หมวดงานสถาปัตยกรรม subsections (2.3 งานตกแต่งพื้น, 2.4 งานผนังและผิวผนัง, 2.5 งานประตู-หน้าต่าง, 2.6 งานเครื่องสุขภัณฑ์และอุปกรณ์, 2.7 งานตกแต่งบันได, 2.8 งานทาสี — per the index found on page 39 sheet 4/19), then presumably หมวดงานระบบสุขาภิบาล (item 3) and หมวดงานระบบไฟฟ้า (item 4) sections, ending around sheet 19/19. Page 47 (last page in this batch) should be inspected first to see where the ฐานรากแผ่ BOQ actually ends (sheet 19/19) and whether it spills onto extra content — do not assume it neatly ends there.

## Reusable crop recipe (for the remaining pages)

```python
from PIL import Image
im = Image.open(r"C:\00mk\steel project\training\Training\image\บ้าน_เล็ก_1ชั้น_01\บ้าน_เล็ก_1ชั้น_01_หน้าNN.png")
w, h = im.size
base = r"C:\Users\CHAICH~1\AppData\Local\Temp\claude\c--00mk-steel-project------------Constistant\457bfb67-ab95-492c-bfb8-e0fd8ad9949a\scratchpad\crops"
# NOTE: this scratchpad path is SESSION-SPECIFIC — in a new session, create a fresh
# scratchpad crops folder instead of reusing this exact path.
for side, box in [("left", (0,0,w//2,h)), ("right", (w//2,0,w,h))]:
    half = im.crop(box).rotate(90, expand=True)
    half = half.resize((int(half.width*2.2), int(half.height*2.2)), Image.LANCZOS)
    w2, h2 = half.size
    # combined description+qty+unit region (reliable row alignment):
    half.crop((0, 0, int(w2*0.5), h2)).save(f"{base}\\pNN_{side}_desc_qty.png")
    # footer/sheet-number region:
    half.crop((int(w2*0.7), 0, w2, h2)).save(f"{base}\\pNN_{side}_footer.png")
    # price columns region (expected blank, spot-check only):
    half.crop((int(w2*0.5), 0, int(w2*0.75), h2)).save(f"{base}\\pNN_{side}_price.png")
```
Then Read each `_desc_qty.png` and `_footer.png` (skip `_price.png` reading once a page or two confirm it's still all blank).

## Output convention recap
- One JSON per half-sheet: `บ้าน_เล็ก_1ชั้น_01_หน้าNN_1.json` (right half) and `..._หน้าNN_2.json` (left half).
- `png` field = "NN" (same for both halves of a page).
- `sheet_name` = full printed title + sub-heading + "(แผ่นที่ X/19)".
- `pattern` always "material_list".
- Honesty: null + warning for anything illegible; don't fabricate doc_page.
