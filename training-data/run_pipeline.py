#!/usr/bin/env python3
"""
run_pipeline.py — FULL flow ทั้งโฟลเดอร์ (Stage 0 → route ทุกหน้า → Stage B structural + BOQ)

Step ที่เกิดขึ้นจริง:
  Step 1  ensure document map (build_document_map.py) — สารบัญ → PDF page → discipline
  Step 2  ไล่ทุกหน้า → lookup map:
            structural → Stage B (unified): อ่าน title-block sheet_name → เลือก pattern
                         (plan/schedule/section/notes) + focus → extract  [qwen-vl-max]
            boq        → ตารางปริมาณงาน (หมุน 90° CCW ก่อนส่ง — ต้นฉบับเป็น portrait
                         ฝังในเล่ม landscape) [qwen-vl-max]
            อื่นๆ      → skip (log เหตุผล)  — ตาม scope: structural + boq
  Step 3  เซฟ JSON ต่อหน้า (ชื่อตรงรูป) + _run_summary.json

Usage:
  python run_pipeline.py raw/image/บ้าน_เล็ก_1ชั้น_01 --toc 02 --anchors 20,40
  python run_pipeline.py raw/image/บ้าน_เล็ก_1ชั้น_01 --only 20      # ทดสอบหน้าเดียว
"""
import os, re, sys, io, json, time, base64, pathlib, argparse, subprocess, urllib.request
from PIL import Image
from log_utils import log_action

BASE = pathlib.Path(__file__).resolve().parent
HERE = pathlib.Path(__file__).resolve().parent

def load_env():
    env = {}
    for line in (BASE / '.env.local').read_text(encoding='utf-8').splitlines():
        m = re.match(r'^([A-Z_]+)=(.*)$', line)
        if m: env[m.group(1)] = m.group(2).strip()
    return env
ENV = load_env(); HOST = ENV['QWEN_API_HOST'].rstrip('/'); KEY = ENV['QWEN_API_KEY']
MODEL_STRUCT = 'qwen-vl-max'
DELAY = 0.5

def call(model, system, user, b64, max_tokens, pixels=None):
    # pixels: (width, height) ของภาพที่ส่งจริง — ล็อก min/max_pixels ให้ API ไม่ย่อภาพต่ำกว่า
    # native resolution เอง (ค่า default ของ Qwen-VL อาจย่อภาพใหญ่ลงจนตัวเลข/ตัวอักษรเล็กอ่านไม่ออก
    # — ดูบทเรียน CLAUDE.md ข้อ 2 เรื่องอ่านขนาดเหล็กผิด)
    image_url = {"url": f"data:image/png;base64,{b64}"}
    if pixels:
        w, h = pixels
        image_url["min_pixels"] = w * h
        image_url["max_pixels"] = w * h
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": image_url},
            ]},
        ],
        "temperature": 0.1, "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }).encode('utf-8')
    req = urllib.request.Request(HOST + '/chat/completions', data=payload,
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + KEY})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    content = data['choices'][0]['message']['content']
    try:
        return json.loads(content), data.get('usage', {})
    except json.JSONDecodeError:
        return {"_parse_error": True, "raw": content}, data.get('usage', {})

def b64file(p):
    return base64.b64encode(p.read_bytes()).decode(), Image.open(p).size

def b64file_rotated(p, degrees=90):
    """หมุนภาพก่อนแปลง base64 — ใช้กับหน้า BOQ ที่ต้นฉบับ portrait ถูกฝังใน landscape"""
    im = Image.open(p).rotate(degrees, expand=True)
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode(), im.size

# ════════════════════════════════════════════════════════════════════
# Stage B — UNIFIED structural extractor (1 call/หน้า, self-routing 4 patterns)
# ════════════════════════════════════════════════════════════════════
STRUCT_SYSTEM = (
    "You are a licensed Thai structural engineer doing quantity takeoff from ONE structural "
    "(S-series) sheet of a Thai RC building. A sheet often contains MULTIPLE labeled views on the "
    "same page (e.g. two plans side by side, or one detail box per beam mark) — you must enumerate "
    "every one as a separate view, never merge them together. First read the title-block sheet name "
    "(ช่อง 'แสดงแบบ', bottom-right), then find every underlined/bold heading or caption on the sheet "
    "and extract each as its own view using the schema for that view's pattern. For 'plan' views, also "
    "read the printed grid dimension chain so beam spans can be computed later, not guessed. Read only "
    "what is visible; a null is better than a guess. Every numeric field carries confidence_score 0-1."
)

STRUCT_USER = """THAI RC NOTATION: "2DB16"=2 deformed bars 16mm (count=2,dia=16,type=DB); "RB6"=round 6mm (stirrup,RB);
"ค1"=beam, "ต1/C1"=column, "พ1"=slab, "F1/ฐ1"=footing; "@0.10"=100mm; fc' in ksc; grades SR24/SD30/SD40.
Lengths: section/schedule=mm, span=m.

STEP 1 — read the title block (มุมขวาล่าง): sheet_code (e.g. S-03) and overall sheet_name (e.g. "ผังคานชั้น 1").
STEP 2 — INVENTORY FIRST: scan the WHOLE sheet and list every underlined/bold heading or caption you
  can see — each one becomes a "view". Do this before extracting any element detail. Do not skip a
  heading because it looks minor; sheets commonly have 2+ views side by side (e.g. "แปลนฐานราก" +
  "แปลนคาน" on the same page) or one detail box per element mark. Missing a whole view/element is worse
  than an imprecise number inside one — always err toward listing more views, not fewer.
STEP 3 — for EACH view in your inventory, decide its pattern from the heading text + what you see:
  "plan"     = ผัง*/แปลน* (ผังฐานราก/ผังเสา/ผังคาน/ผังพื้น) — bird's-eye layout with element marks + grid
  "schedule" = ตาราง* (ตารางเสา/คาน/ฐานราก) — a table of marks with spec columns
  "section"  = รายละเอียด*/รูปตัด — cross-sections with rebar (DB/RB dots + callouts)
  "notes"    = หมายเหตุ/ข้อกำหนดโครงสร้าง — text specs (fc', เกรดเหล็ก, ระยะหุ้ม)
STEP 4 — for each "plan" view ONLY: read the grid dimension chain (the row of numbers printed along the
  top/side of the plan giving the spacing between adjacent grid lines, e.g. "4.00 | 3.00 | 4.00"). Build
  a coordinate table by accumulating these spacings from one reference line (pos_m=0). The grid is
  normally shared by every plan view on the same sheet — read it once and reuse it.
STEP 5 — extract each view's elements with the matching block below. Fill focus by element type the view
  is about.

  For LINEAR elements (beam) in a "plan" view — READ THIS CAREFULLY, it is the #1 source of mistakes:
  A physical beam is always ONE STRAIGHT MEMBER running between exactly TWO ADJACENT supports. A
  "support" is any of the following — not just a column:
    - a grid intersection / a column
    - the point where this beam BEARS ON (frames into / rests on top of) ANOTHER BEAM instead of a
      column — very common for secondary beams; that other beam is still a real support even though it
      isn't a named grid point
    - a CHANGE OF DIRECTION — if the drawn line bends or turns a corner, that corner is a break point.
      A beam cannot be diagonal-then-straight or turn a corner and still be "one" member; the two straight
      runs on either side of the bend are two separate beams even if they share one mark/label.
  If a beam mark is drawn/labelled continuously across ANY of the above (an intermediate grid
  intersection/column, a point where it crosses/lands on another beam, or a corner), that is NOT one
  beam — it is two (or more) separate physical beams that happen to share a mark name. You MUST split it
  into separate segment entries at every such point. Never let one "grid_ref_start"/"grid_ref_end" pair
  skip over a support of any of these three kinds.
  When an end is NOT a grid intersection because it bears on another beam, still set it to "?" (grid
  can't resolve it), but add a confidence_flag like "bears_on_beam:B5" naming the beam it rests on — this
  preserves the structural fact even when the exact coordinate isn't computable from the grid table.
  Emit ONE array entry PER ATOMIC SEGMENT — do not group same-mark segments together yourself; grouping
  identical (mark, span) pairs into a count happens automatically afterward, so just list every physical
  segment you can see, one at a time, even if several end up with the same mark and the same length.
  Segment entry shape: {"element_id":"ค1","element_type":"beam","grid_ref_start":"A-1","grid_ref_end":"A-2",
  "span_length_m":4.0,"span_source":"grid_table","confidence_score":0.7,"confidence_flags":[]}
  Span length rules, in order of trust:
    (a) both grid_ref_start and grid_ref_end are grid intersections → leave span_length_m as your best
        estimate, it will be recomputed exactly from the grid table afterward — do not agonize over
        precision here, just get grid_ref_start/grid_ref_end right (this is the part that must not skip
        over a support).
    (b) one or BOTH ends are not grid intersections (cantilever, secondary beam framing between two other
        beams, ends mid-bay, etc.) but a dimension number is printed directly along/near that specific
        beam → set the unresolved side(s) to "?", read the printed number into span_length_m yourself, and
        set "span_source":"local_dimension" (this value will NOT be overwritten). This is the normal case
        for any beam whose span isn't a standard grid module — Thai drafting convention always prints an
        explicit dimension for it, so look for that number before giving up.
    (c) truly no dimension can be found anywhere near the beam (neither a grid endpoint nor a printed
        number) → set the unresolved side(s) to "?", span_length_m:null, "span_source":"unresolved" — do
        NOT invent an endpoint or a length.

  POINT-type elements (footing/column marks repeated across a plan) do not have a span and are NOT
  segments — keep the old shape: grid_refs is a list of every intersection where the mark occurs,
  span_length_m stays null, no grid_ref_start/grid_ref_end.

Return ONLY JSON — one entry in "views" per heading found in STEP 2, in the order they appear on the sheet:
{
 "sheet_code":"S-03","sheet_name":"...",
 "views": [
   {
     "view_title":"ผังคานชั้น 1","pattern":"plan",
     "grid": {"x_lines":[{"id":"A","pos_m":0.0},{"id":"B","pos_m":4.0},{"id":"C","pos_m":7.0}],
              "y_lines":[{"id":"1","pos_m":0.0},{"id":"2","pos_m":3.0},{"id":"3","pos_m":6.0}]},
     "elements": [
       {"element_id":"ค1","element_type":"beam","grid_ref_start":"A-1","grid_ref_end":"A-2",
        "span_length_m":3.0,"span_source":"grid_table","confidence_score":0.7,"confidence_flags":[]},
       {"element_id":"ค1","element_type":"beam","grid_ref_start":"B-1","grid_ref_end":"B-2",
        "span_length_m":3.0,"span_source":"grid_table","confidence_score":0.7,"confidence_flags":[]},
       {"element_id":"ค1","element_type":"beam","grid_ref_start":"A-2","grid_ref_end":"A-3",
        "span_length_m":4.0,"span_source":"grid_table","confidence_score":0.7,"confidence_flags":["count_uncertain"]},
       {"element_id":"ค9","element_type":"beam","grid_ref_start":"C-2","grid_ref_end":"?",
        "span_length_m":1.5,"span_source":"local_dimension","confidence_score":0.6,"confidence_flags":["cantilever"]},
       {"element_id":"F1","element_type":"footing","count":3,"grid_refs":["A-1","A-2","A-3"],
        "span_length_m":null,"confidence_score":0.85,"confidence_flags":[]}
     ]
   },
   {
     "view_title":"ตารางเสา","pattern":"schedule",
     "elements": [ {"element_id":"ต1","element_type":"column","width_mm":200,"height_mm":200,
               "main_bar_count":4,"main_bar_dia_mm":16,"main_bar_type":"DB","stirrup_dia_mm":6,
               "stirrup_type":"RB","stirrup_spacing_mm":200,"concrete_grade":"fc240","steel_grade":"SD40",
               "confidence_score":0.85,"confidence_flags":[]} ]
   },
   {
     "view_title":"รายละเอียดคาน ค1","pattern":"section",
     "elements": [ {"element_id":"ค1","element_type":"beam","width_mm":200,"height_mm":400,
               "main_bar_count":4,"main_bar_dia_mm":16,"main_bar_type":"DB","stirrup_dia_mm":6,
               "stirrup_type":"RB","stirrup_spacing_mm":150,"stirrup_spacing_dense_mm":100,
               "stirrup_dense_zone_mm":1000,"concrete_grade":"fc240","steel_grade":"SD40",
               "confidence_score":0.85,"confidence_flags":[]} ]
   },
   {
     "view_title":"หมายเหตุโครงสร้าง","pattern":"notes",
     "notes": {"concrete_strength_ksc":240,"steel_main":"SD40","steel_stirrup":"SR24",
               "cover_mm":{"beam":25,"column":25,"footing":75},"lap_rule":"40D","design_codes":[],
               "confidence_score":0.8,"confidence_flags":[]}
   }
 ],
 "warnings": []
}"""

# ── grid-based span resolution — คำนวณด้วยโค้ด ไม่ใช้ตัวเลขที่โมเดลกะเอง ──
# เหตุผล: sheet_code/ตัวเลขที่พิมพ์ไว้จริงบนแบบ โมเดลอ่านแม่นกว่าประเมินระยะจาก geometry มาก
# (ดู CLAUDE.md บทเรียนข้อ 1) เลยให้โมเดลแค่ "อ่าน" grid dimension chain ที่พิมพ์ไว้ แล้วคำนวณ span
# จริงด้วย Python แทนการให้โมเดลกะระยะเอง
#
# โมเดลต้องส่ง "atomic segment" มาทีละเส้น (คานหนึ่งตัว = อยู่ระหว่างเสา/จุดตัด grid 2 จุดติดกันเท่านั้น
# ถ้ามีเสาคั่นกลาง ต้องแยกเป็นคนละ segment) ห้ามให้โมเดลรวม/นับเองว่า mark เดียวกันมีกี่ตัว — โค้ดเป็น
# คนคำนวณระยะจริงต่อ segment แล้วค่อย "รวมนับ" segment ที่ (mark, ระยะ) ตรงกันทีหลัง (group_beam_segments)
# วิธีนี้แก้ปัญหาที่เจอจริง: mark เดียวกัน (เช่น B4) ยาวไม่เท่ากันหลายจุดในแบบเดียวกัน ถ้าปล่อยให้โมเดล
# รวมเองจะได้ span ผิดๆ (เฉลี่ย/สับสน) ต้องแยกก่อนคำนวณ แล้วค่อยรวมด้วยเกณฑ์ (mark, ระยะ) ไม่ใช่ (mark) เฉยๆ
_GRID_PT_RE = re.compile(r'^([A-Za-z]+)-(\d+)$')

def _grid_lookup(grid):
    lookup = {}
    if not isinstance(grid, dict):
        return lookup
    for axis in ('x_lines', 'y_lines'):
        for g in (grid.get(axis) or []):
            if isinstance(g, dict) and g.get('id') is not None and g.get('pos_m') is not None:
                lookup[str(g['id'])] = g['pos_m']
    return lookup

def _resolve_grid_point(lookup, label):
    m = _GRID_PT_RE.match((label or '').strip())
    if not m:
        return None
    x_label, y_label = m.groups()
    if x_label not in lookup or y_label not in lookup:
        return None
    return (lookup[x_label], lookup[y_label])

def apply_grid_spans(ext):
    """เติม/ยืนยัน span_length_m ของทุก beam segment (grid_ref_start/grid_ref_end) โดยคำนวณจาก
    view['grid'] จริง ทีละ segment — ข้าม element ที่ span_source='local_dimension' (โมเดลอ่านตัวเลข
    พิมพ์จริงมาแล้ว ไม่ทับ) และข้ามกรณี resolve ไม่ได้ (ปล่อยค่าเดิม/null ที่โมเดลให้มา ไม่เดา)"""
    if not isinstance(ext, dict):
        return ext
    for view in (ext.get('views') or []):
        if not isinstance(view, dict) or view.get('pattern') != 'plan':
            continue
        lookup = _grid_lookup(view.get('grid'))
        if not lookup:
            continue
        for el in (view.get('elements') or []):
            if not isinstance(el, dict) or 'grid_ref_start' not in el:
                continue  # ไม่ใช่ beam segment (เช่น footing/column แบบจุด) — ข้าม
            if el.get('span_source') == 'local_dimension':
                continue
            p1 = _resolve_grid_point(lookup, el.get('grid_ref_start'))
            p2 = _resolve_grid_point(lookup, el.get('grid_ref_end'))
            if p1 is None or p2 is None:
                continue  # resolve ไม่ได้ — ปล่อยค่าที่โมเดลให้มา (ควรเป็น null/unresolved ตาม prompt)
            el['span_length_m'] = round(((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5, 2)
            el['span_source'] = 'grid_table'
    return ext

def group_beam_segments(ext):
    """รวม beam segment ที่ element_id + span_length_m (หลังคำนวณจาก grid แล้ว) ตรงกันเป๊ะ เป็น 1
    รายการ (count + grid_refs list) — รวมด้วย (mark, ระยะ) เท่านั้น ไม่ใช่ (mark) เฉยๆ ตามหลักที่ว่า
    mark เดียวกันยาวไม่เท่ากันได้ ต้องนับแยกกันคนละความยาว ไม่เฉลี่ย ไม่ปนกัน"""
    if not isinstance(ext, dict):
        return ext
    for view in (ext.get('views') or []):
        if not isinstance(view, dict) or view.get('pattern') != 'plan':
            continue
        elements = view.get('elements') or []
        segments = [e for e in elements if isinstance(e, dict) and 'grid_ref_start' in e]
        others = [e for e in elements if not (isinstance(e, dict) and 'grid_ref_start' in e)]
        groups, order = {}, []
        for seg in segments:
            span = seg.get('span_length_m')
            key = (seg.get('element_id'), seg.get('element_type'),
                   None if span is None else round(span, 2), seg.get('span_source'))
            if key not in groups:
                groups[key] = {
                    "element_id": seg.get('element_id'), "element_type": seg.get('element_type'),
                    "count": 0, "grid_refs": [], "span_length_m": span,
                    "span_source": seg.get('span_source'),
                    "confidence_score": seg.get('confidence_score'), "confidence_flags": [],
                }
                order.append(key)
            g = groups[key]
            g["count"] += 1
            g["grid_refs"].append(f"{seg.get('grid_ref_start')}/{seg.get('grid_ref_end')}")
            sc = seg.get('confidence_score')
            if sc is not None:
                g["confidence_score"] = sc if g["confidence_score"] is None else min(g["confidence_score"], sc)
            for f in (seg.get('confidence_flags') or []):
                if f not in g["confidence_flags"]:
                    g["confidence_flags"].append(f)
        view['elements'] = others + [groups[k] for k in order]
    return ext

def extract_structural(img_path):
    b64, size = b64file(img_path)
    data, usage = call(MODEL_STRUCT, STRUCT_SYSTEM, STRUCT_USER, b64, 2048, pixels=size)
    data = apply_grid_spans(data)
    data = group_beam_segments(data)
    return data, usage

# ════════════════════════════════════════════════════════════════════
# BOQ extractor — ตารางปริมาณงาน (ปร.4/ปร.5) สำหรับประเมินราคา Constistant
# หน้า BOQ ในแบบไทยมักกรอก "ปริมาณ+หน่วย" มาแล้ว แต่ช่องราคาเว้นว่าง (template) →
# ของมีค่าคือ quantity takeoff; ราคาว่างให้คืน null (ห้ามเดา ตามบทเรียนข้อ 2/3)
# ════════════════════════════════════════════════════════════════════
MODEL_BOQ = 'qwen-vl-max'  # ตัวเลขในตารางหนาแน่น ต้องแม่น (เหมือน structural)
BOQ_SYSTEM = (
    "You are a Thai quantity surveyor (ผู้ประมาณราคา) reading ONE page of a Bill of Quantities "
    "(บัญชีปริมาณงาน / ปร.4 / ปร.5) from a Thai construction set. Transcribe the table EXACTLY as "
    "printed, row by row, across ALL work categories on the page. Read only what is visible; empty "
    "price cells are common (they are filled in later) — return null for any blank cell, NEVER guess "
    "a number. Every numeric field carries confidence_score 0-1."
)
BOQ_USER = """This is a Thai BOQ (บัญชีปริมาณงาน) page. Columns are usually:
ลำดับที่ | รายการ (description) | จำนวน (quantity) | หน่วย (unit) |
ราคาวัสดุ[ราคาต่อหน่วย, จำนวนเงิน] | ค่าแรงงาน[ราคาต่อหน่วย, จำนวนเงิน] | รวมค่าวัสดุและค่าแรงงาน (total)
Units seen: ลบ.ม. (m³), ตร.ม. (m²), กก. (kg), ต้น, ชุด, เมตร, ตร.ม.# (wire mesh). Keep the unit text verbatim.
Read the sheet number (แผ่นที่ x/y) if printed.

CRITICAL RULES:
1. TRANSCRIBE, do not paraphrase. Copy the รายการ text character-by-character exactly as printed.
   Never substitute a material/quantity term you "expect" to see instead of what's actually printed —
   if a character is genuinely illegible, keep your best-guess char but lower confidence_score and add
   a confidence_flag; do not silently swap in a different word.
2. A row with a bold/underlined category label and NO quantity/unit (e.g. "หมวดงานโครงสร้าง",
   "1. หมวดงานโครงสร้าง", "2.6 งานเครื่องสุขภัณฑ์และอุปกรณ์" when it's a section header, not a priced
   line) is a CATEGORY HEADER, not an item. Do NOT emit it as an item row — use it only to set the
   "category" field for the items printed below it, until the next header appears.
3. Categories run top-to-bottom in printed order and do NOT interleave — once you see a new category
   header, every following item belongs to THAT category until the next header. Do not reassign items
   to a category based on what the item sounds like; use strictly the header printed immediately above it.
4. Every priced row (has quantity+unit) becomes exactly one item, in printed order, under its category.

Return ONLY JSON. blank price cell → null (do NOT invent numbers):
{
 "sheet_no":"2/19",
 "categories":[
   {"category":"หมวดงานโครงสร้าง",
    "items":[
      {"item_no":"1","description":"คอนกรีตโครงสร้าง 1:2:4","quantity":29,"unit":"ลบ.ม.",
       "material_unit_price":null,"material_amount":null,
       "labor_unit_price":null,"labor_amount":null,"total_amount":null,
       "confidence_score":0.85,"confidence_flags":[]}
    ]}
 ],
 "warnings":[]
}"""

def extract_boq(img_path):
    # หมุน 90° CCW ก่อนส่ง — ต้นฉบับ BOQ เป็น portrait ฝังในเล่ม landscape (ยืนยันจากภาพจริงแล้ว)
    b64, size = b64file_rotated(img_path, 90)
    data, usage = call(MODEL_BOQ, BOQ_SYSTEM, BOQ_USER, b64, 4096, pixels=size)
    return data, usage

# ════════════════════════════════════════════════════════════════════
def ensure_document_map(folder, toc, anchors):
    house = folder.name
    mp = BASE / 'raw' / 'image' / house / 'qwen-output' / '_document_map.json'
    if not mp.exists():
        print("Step 1 · สร้าง document map (Stage 0)…")
        subprocess.run([sys.executable, str(HERE / 'build_document_map.py'), str(folder),
                        '--toc', toc, '--anchors', anchors], check=True)
    else:
        print(f"Step 1 · ใช้ document map เดิม: {mp.relative_to(BASE)}")
    return json.loads(mp.read_text(encoding='utf-8'))

def count_elements(ext):
    if not isinstance(ext, dict): return 0
    return sum(len(v.get('elements', []) or []) for v in (ext.get('views') or []) if isinstance(v, dict))

def count_boq_items(ext):
    if not isinstance(ext, dict): return 0
    return sum(len(c.get('items', []) or []) for c in (ext.get('categories') or []))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder'); ap.add_argument('--toc', default='02')
    ap.add_argument('--anchors', default='20,40'); ap.add_argument('--only', default=None)
    args = ap.parse_args()

    folder = pathlib.Path(args.folder).resolve()
    house = folder.name
    out_dir = BASE / 'raw' / 'image' / house / 'qwen-output'
    doc = ensure_document_map(folder, args.toc, args.anchors)
    page_map = doc['page_map']
    for w in doc.get('warnings', []):
        print(f"⚠️  {w}")
    print(f"\nStep 2 · ไล่ทุกหน้า ({len(page_map)}) — routing ตาม map (offset {doc['offset']:+d})\n")

    imgs = {re.search(r'_หน้า(\d+)\.png$', p.name).group(1): p
            for p in folder.glob('*.png') if re.search(r'_หน้า(\d+)\.png$', p.name)}

    summary, total_tokens = [], 0
    keys = sorted(page_map.keys())
    if args.only:
        # รับได้ทั้งหน้าเดียว "20" และหลายหน้า "49,50,57" (ใช้นำร่อง BOQ)
        keys = [f"{int(x):02d}" for x in str(args.only).split(',') if x.strip()]

    for k in keys:
        info = page_map[k]; disc = info['discipline']
        row = {"png": k, "doc_page": info['doc_page'], "discipline": disc}
        if disc == 'structural':
            print(f"  หน้า{k}  [{disc}] → Stage B (vl-max)…", end=' ')
            try:
                ext, usage = extract_structural(imgs[k])
                total_tokens += usage.get('total_tokens', 0)
                nm = ext.get('sheet_name'); ne = count_elements(ext)
                views = ext.get('views') or []
                pats = [v.get('pattern') for v in views if isinstance(v, dict)]
                (out_dir / (imgs[k].stem + '.json')).write_text(
                    json.dumps({"png": k, **info, "extraction": ext}, ensure_ascii=False, indent=2),
                    encoding='utf-8')
                row.update({"action": "extracted", "sheet_name": nm, "views": len(views),
                            "patterns": pats, "elements": ne, "needs_review": True})
                print(f"'{nm}' views={len(views)} {pats} → {ne} elements")
            except Exception as e:
                row.update({"action": "error", "error": str(e)[:120]})
                print(f"❌ {type(e).__name__}: {str(e)[:80]}")
            time.sleep(DELAY)
        elif disc == 'boq':
            print(f"  หน้า{k}  [{disc}] → BOQ (vl-max)…", end=' ')
            try:
                ext, usage = extract_boq(imgs[k])
                total_tokens += usage.get('total_tokens', 0)
                sn = ext.get('sheet_no'); ni = count_boq_items(ext)
                ncat = len(ext.get('categories') or [])
                out_path = out_dir / (imgs[k].stem + '.json')
                out_path.write_text(
                    json.dumps({"png": k, **info, "extraction": ext}, ensure_ascii=False, indent=2),
                    encoding='utf-8')
                log_action(file=out_path.relative_to(BASE), ai_model=MODEL_BOQ,
                           action='extract_boq', house=house)
                row.update({"action": "extracted", "sheet_no": sn, "categories": ncat,
                            "boq_items": ni, "needs_review": True})
                print(f"แผ่นที่ {sn} → {ncat} หมวด, {ni} รายการ")
            except Exception as e:
                row.update({"action": "error", "error": str(e)[:120]})
                print(f"❌ {type(e).__name__}: {str(e)[:80]}")
            time.sleep(DELAY)
        elif disc == 'unknown':
            # unknown = prefix แปลกที่ map ตัดสินไม่ได้ → skip แต่ flag ให้คนตรวจ (อย่าปล่อยเงียบ)
            row.update({"action": "skip", "needs_review": True})
            print(f"  หน้า{k}  [{disc}] → skip ⚠️ (unknown — ตรวจว่าเป็น structural ที่พลาดไหม)")
        else:
            row["action"] = "skip"
            print(f"  หน้า{k}  [{disc}] → skip")
        summary.append(row)

    summary_path = out_dir / '_run_summary.json'
    summary_path.write_text(
        json.dumps({"house": house, "offset": doc['offset'], "total_tokens": total_tokens,
                    "pages": summary}, ensure_ascii=False, indent=2), encoding='utf-8')
    extracted = [r for r in summary if r.get('action') == 'extracted']
    log_action(file=summary_path.relative_to(BASE), ai_model=f"{MODEL_STRUCT}/{MODEL_BOQ}",
               action='run_summary', house=house, pages_extracted=len(extracted))

    print(f"\nStep 3 · เสร็จ — extract {len(extracted)} หน้า, skip {len(summary)-len(extracted)} หน้า, "
          f"~{total_tokens} tokens")
    print(f"💾 {(out_dir/'_run_summary.json').relative_to(BASE)}")

if __name__ == '__main__':
    main()
