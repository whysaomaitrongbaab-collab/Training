#!/usr/bin/env python3
"""
pure_power_read.py — destrier อ่านบ้านไทยพอเพียง3 "ด้วยกำลังเพียวๆ" (มะขามสั่ง 2026-08-31)

ต่างจาก smoke_destrier.py (ทดสอบบน val ที่ทั้ง subtask ถูกต้องและมี grid master ฝังในพรอมต์แล้ว):
บ้านนี้คือ **ตัวเทียบข้ามรอบตัวจริงของ Courser** (t05_workflow.md §🎯) — ยืนยันไม่อยู่ใน 40
หลังคลัง ไม่มี pass0/grid master ทำไว้เลย มะขามสั่งให้ทดสอบ "เพียวๆ" คือ ไม่เดินสายพาน
(pass0→gridline→plan→schedule ทีละขั้น) แต่ป้อนพรอมต์ตัวเดียว = แกนกลางของ schema (ที่เหมือน
กันทุก subtask ใน t05) + ปล่อยให้โมเดลตัดสินเองว่าหน้านั้นเป็น pattern อะไร (grid/plan/section/
notes/schedule) — วัดว่าโมเดลอ่านและจัดหมวดเองได้แค่ไหนโดยไม่มีคนบอกล่วงหน้า

เลือกหน้าแบบกระจายทั่วเล่ม (ไม่ใช่ทั้ง 65 หน้า — ช้าเกินไปด้วย torch fallback บนเครื่องนี้ วัด
จาก smoke ~20 นาที/หน้า) ให้เห็นภาพรวมว่ามันอ่านออกจริงไหม ก่อนตัดสินใจเดินสายพานเต็ม

รัน: /workspace/infer_env/bin/python pure_power_read.py
"""
import glob
import json
import os
import re
import sys

import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

BASE = "unsloth/Qwen3.6-35B-A3B"
ADAPTER = "dacarokann/destrier"
HOUSE_DIR = "/workspace/Training/tune_ai/t04_Purson/test_house_new/image_บ้านไทยพอเพียง3"
MAX_PIXELS = 6912 * 1024
MAX_NEW = 4096
# กระจายทั่วเล่ม 65 หน้า — คาดว่า front matter/site plan (ต้น) มักมีกริด, กลางเล่มมัก
# เป็นแปลนโครงสร้าง/schedule, ท้ายเล่มมักเป็น detail/หมายเหตุ
PAGES = [3, 10, 19, 28, 36, 46, 55, 62]

PROMPT_CORE = """You are extracting structured data from a Thai reinforced-concrete construction drawing
Output one JSON object and nothing else - no prose before or after, no markdown fence


Output shape

Put drawing content in `elements[]` Two exceptions only (§0.1)
- a grid file uses `grid{ ... }`
- a bill of quantities uses `categories[].items[]`
A notes/specification sheet uses `sections[]` (verbatim transcript) + optional `notes{}`
(parsed spec values) instead of `elements[]`

Never name an array after the kind of element it holds `beams[]`, `columns[]`, `slabs[]`,
`footing_types[]`, `structural_elements[]` are forbidden - the kind belongs in `element_type`

Every file carries these wrapper fields (§2)

```
png, doc_page, discipline, sheet_code, sheet_name, pattern,
source_image, confidence_score, confidence_flags, warnings
```

`discipline` is one of these values (§2) `structural` · `architectural` · `sanitary` ·
`electrical` · `mechanical` · `boq` · `material_list` · `general` · `front_matter` ·
`regulatory` · `misc`
Write `architectural`, never `architecture`

`pattern` - decide it yourself from what the sheet actually draws (no subtask was told to
you for this page): `grid_master` · `footing_plan` · `beam_plan` · `roof_frame_plan` ·
`etc_plan` (column/slab plans) · `section` · `schedule` · `notes` · `boq` · `other`

Every element carries four fields (§0.2)

```json
{ "element_id": "...", "element_type": "...", "confidence_score": 0.9, "confidence_flags": [] }
```

`confidence_score` is `null` when the sheet gave you nothing to judge by
Never invent a number to fill it - an honest `null` beats a made-up score

`element_id` is the mark printed on the drawing, nothing else (§0.3)

- Exactly as printed `"B1"`, `"F1.30x1.30"`, `"C1A"`
- No position suffix (position lives in `grid_refs`), no level suffix (use `level`), no
  section suffix (use `section_ref`)
- Unmarked thing → a descriptive id (`"ceiling_fan_นอน1"`) Never leave it absent
- Two different members must never share an `element_id` on one sheet

`element_type` - reuse, do not invent (§0.4)

`beam` · `column` · `footing` · `pile` · `pile_cap` · `pedestal` · `slab` · `tie_beam` ·
`rafter` · `stair` · `room` · `room_cut` · `door` · `window` · `wall` · `dimension` ·
`dimension_chain` · `dimension_note` · `level` · `datum` · `note` · `symbol` ·
`symbol_legend_entry` · `sheet_index_entry` · `detail_view` · `section_view` · `plan_view` ·
`precast_plank_detail` · `sanitary_fixture` · `vent_pipe` · `fitting` · `accessory` ·
`furniture` · `gate_component` · `railing_component` · `electrical_outlet` ·
`ceiling_downlight_point` · `ceiling_fan` · `design_criterion` · `steel_member` ·
`connection_detail` · `installation_detail`

Only invent a value when none of these fits, and say so in `warnings[]` when you do

Numbers (§0.5)

- Member size → `width_mm`, `height_mm`, `thickness_mm`, `depth_mm` as integer millimetres
- Never a packed string `"0.20x0.40"` → `width_mm: 200, height_mm: 400`
- Positions stay in metres as numbers `level_m`, `span_length_m`, `pos_m`
- Multi-span member → `spans_m[]` `span_length_m` is always a single number
- Printed `4+4` → `count` = the sum, printed text in `count_printed_as`
- Printed `16+12` → `dia_mm` = first, `mixed_dia_mm` = the list, text in `dia_mm_printed_as`

Rebar is always an object, never a string (§0.6)

This is wrong - do not write `"main_bar": "2-Ø16มม. top"` or `"stirrup": "Ø6มม.@0.20ม."`
- `stirrup` is the only name - `tie`, `tie_bar`, `stirrup_or_tie` are forbidden spellings
- Spacing is `spacing_mm`, an integer · `Ø` → `type: "RB"`
- `main_bar` / `stirrup` / `rebar` / `steel_section` are single objects, never arrays

Keep the drawing's own words (§0.7) — whenever you convert something printed, keep the
original verbatim in a sibling `*_printed_as` field Thai stays Thai Never translate a label

`grid_ref` notation - one way only (§0.8)
- a point → `"C1"`, `"ค1"`, `"E'1"` — never `"C-1"` or `"1-C"`
- a range on one axis → `"D-C"` or `"1-2"` · a 2-axis area, vertical axis first → `"D-C x 1-2"`
- approximate → `"~A1"`, never "near grid A1" · `grid`/`dummy` never appear inside the value

The honesty rules - these outrank being complete

1) Never guess a measurement not printed on THIS sheet - no grid master was supplied for
   this house, so leave any un-printed span/position `null` with a reason in `warnings[]`
   rather than estimating it (the scaled-from-grid procedure needs a grid master you were not
   given here - do not attempt it)
2) Never drop something you could not read - give it an entry with unreadable fields `null`
   plus a `confidence_flags` note
3) Never repeat an entry to fill space - a short honest answer beats a long repetitive one
4) `warnings[]` is where you talk to the human

No subtask was chosen for you and no grid master was supplied. Read whatever sheet this
actually is, decide `pattern` yourself, and extract everything visible per the rules above.

Output one JSON object and nothing else."""


def load():
    print(f"โหลด base {BASE} …", flush=True)
    model = AutoModelForImageTextToText.from_pretrained(BASE, dtype="auto", device_map="auto")
    processor = AutoProcessor.from_pretrained(BASE)
    ip = getattr(processor, "image_processor", None)
    if ip is not None and hasattr(ip, "max_pixels"):
        ip.max_pixels = MAX_PIXELS
    print(f"โหลด adapter {ADAPTER} จาก HF …", flush=True)
    model = PeftModel.from_pretrained(model, ADAPTER)
    model.eval()
    return model, processor


def page_path(n):
    hits = glob.glob(os.path.join(HOUSE_DIR, f"*_หน้า{n:02d}.png"))
    return hits[0] if hits else None


def main():
    model, processor = load()
    outs = []
    for n in PAGES:
        p = page_path(n)
        if p is None:
            print(f"⚠️  ไม่พบหน้า {n:02d} — ข้าม")
            continue
        user = [{"role": "user", "content": [
            {"type": "image", "image": p},
            {"type": "text", "text": PROMPT_CORE},
        ]}]
        kw = dict(add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
        try:
            inputs = processor.apply_chat_template(user, enable_thinking=False, **kw)
        except TypeError:
            inputs = processor.apply_chat_template(user, **kw)
        inputs = inputs.to(model.device)
        n_in = inputs["input_ids"].shape[-1]
        print(f"\n=== หน้า {n:02d} ({os.path.basename(p)}) — input {n_in} tokens ===", flush=True)
        with torch.no_grad():
            g = model.generate(**inputs, max_new_tokens=MAX_NEW, do_sample=False)
        txt = processor.decode(g[0][n_in:], skip_special_tokens=True)
        txt = re.sub(r"^```(?:json)?|```$", "", txt.strip()).strip()
        outs.append((n, txt))

        cleaned = re.sub(r",(\s*[}\]])", r"\1", txt)
        try:
            obj = json.loads(cleaned)
            jok = "valid"
            pattern = obj.get("pattern")
            n_el = len(obj.get("elements", [])) if isinstance(obj.get("elements"), list) else (
                "n/a" if "sections" in obj else 0)
        except Exception as e:
            jok = f"เสีย ({e})"
            pattern, n_el = "?", "?"
        print(f"   ยาว {len(txt)} ตัวอักษร · JSON {jok} · pattern={pattern} · elements={n_el}")
        print(f"   ตัวอย่างคำตอบ 400 ตัวแรก:\n{txt[:400]}")

        out_path = os.path.join(os.path.dirname(HOUSE_DIR), f"pure_power_out_page{n:02d}.json")
        open(out_path, "w", encoding="utf-8").write(txt)

    texts = [t for _, t in outs]
    if len(texts) >= 2 and len(set(texts)) == 1:
        print("\n⛔ ทุกหน้าตอบเหมือนกันเป๊ะ — ไม่ได้อ่านภาพจริง")
        return 1
    print(f"\n✅ {len(texts)} หน้าตอบต่างกันจริง — ไฟล์ผลลัพธ์แต่ละหน้าอยู่ที่ test_house_new/pure_power_out_page*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
