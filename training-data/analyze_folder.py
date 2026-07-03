#!/usr/bin/env python3
"""
analyze_folder.py — 2-layer drawing analysis pipeline (Stage A classify → route → Stage B extract)

Flow (ตามที่ทีมออกแบบไว้):
  Layer 1 (text):   pdfplumber/PyMuPDF ดึง text layer ของหน้านั้นจาก PDF ต้นฉบับ
                    - มี text  → ใช้เป็น "grounding" ให้ Qwen (prompt variant B) — เชื่อ text เรื่องตัวอักษร
                    - ไม่มี text → prompt variant A (pure vision)
  Layer 2 (vision): Stage A classify (qwen-vl-plus) → route ด้วย sheet-code / sheet_type
                    → Stage B extract เฉพาะทางต่อ sheet_type (qwen-vl-max / qwen-vl-plus)

Output: qwen-output/<house>/<ชื่อเดียวกับรูป>.json  (1:1 กับไฟล์รูป)

Prompt เนื้อหาเต็มอยู่ใน Prompt/stage-a|b1|b2/prompt.md — ไฟล์นี้คือ executable source of truth
Usage:
  python analyze_folder.py <imageFolder> --page 13        # หน้าเดียว (ทดสอบ)
  python analyze_folder.py <imageFolder>                  # ทั้งโฟลเดอร์
"""
import os, sys, re, json, time, base64, pathlib, argparse, urllib.request, urllib.error
from log_utils import log_action

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

BASE = pathlib.Path(__file__).resolve().parent

# ── load .env.local (no dotenv dependency) ──────────────────────────
def load_env():
    env = {}
    for line in (BASE / '.env.local').read_text(encoding='utf-8').splitlines():
        m = re.match(r'^([A-Z_]+)=(.*)$', line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env

ENV = load_env()
HOST = ENV['QWEN_API_HOST'].rstrip('/')
KEY = ENV['QWEN_API_KEY']

MODEL_CLASSIFY = 'qwen-vl-plus'         # Stage A
MODEL_EXTRACT_STRUCT = 'qwen-vl-max'    # Stage B1 (section/schedule/floor_plan)
MODEL_EXTRACT_NOTES = 'qwen-vl-plus'    # Stage B2 (general_notes)

RATE_LIMIT_DELAY = 0.5  # วินาที คั่นระหว่าง call กัน 429

# ── sheet-code map (extensible — ต่อยอด dataset ได้โดยไม่แตะโค้ด) ────
SHEET_CODE_MAP = {
    'AR': 'architectural', 'A-': 'architectural', 'สถ': 'architectural',
    'S-': 'structural', 'ST-': 'structural', 'โครงสร้าง': 'structural',
    'SN': 'sanitary', 'EE': 'electrical', 'M-': 'mechanical',
}
STRUCT_TYPES = {'section_detail', 'schedule_table', 'floor_plan'}
NOTES_TYPES = {'general_notes'}

# ════════════════════════════════════════════════════════════════════
# PROMPTS  (mirror ของ Prompt/stage-*/prompt.md)
# ════════════════════════════════════════════════════════════════════
STAGE_A_SYSTEM = (
    "You are classifying pages of a Thai reinforced-concrete (RC) structural drawing set. "
    "Identify each page by its visual layout only. "
    "CRITICAL: base your answer ONLY on what is actually visible. Do NOT assume a page is "
    "structural just because it has dimension lines, hatching, or section tags — architectural "
    "detail sheets (stairs, tiling, finishes) have those too. Cite the concrete evidence and "
    "lower confidence when it is weak. Never describe evidence you do not see (do not claim "
    "'rebar dots' unless dots are clearly inside a cross-section)."
)

STAGE_A_USER = """Classify THIS single page into exactly one category:
- "table_of_contents": table listing sheet numbers/titles (รายการแบบ, สารบัญ)
- "general_notes": paragraphs/numbered text, no drawing geometry (หมายเหตุ, ข้อกำหนด, GENERAL NOTES)
- "schedule_table": tabular grid of element IDs (C1/B1/ค1) with rebar specs (ตารางเสา/ตารางคาน)
- "floor_plan": bird's-eye layout with structural grid + scattered element labels (ผังโครงสร้าง, FRAMING/FOUNDATION PLAN)
- "section_detail": cross-section shapes with VISIBLE REINFORCEMENT — rebar dots inside the
    section OR explicit DB#/RB#/@# callouts. This is the deciding evidence.
    WARNING: dimension lines + hatching + a section tag ALONE do NOT qualify. A detail/section
    with NO rebar and NO DB/RB callout = "architectural" (finish/stair/tile), NOT section_detail.
- "architectural": rooms/doors/windows/furniture/MEP, OR finish/stair/tile detail with NO rebar
    (บันได, ผิวปูกระเบื้อง, AR/A- sheet codes)
- "unknown": blank/unreadable or confidence < 0.60

CONFIDENCE DISCIPLINE: reserve >=0.90 for unmistakable evidence. If calling a detail/section
"structural" WITHOUT seeing rebar or DB/RB text, cap confidence at 0.55 and lean architectural.

Return ONLY valid JSON:
{"sheet_type":"...","confidence":0.0,"rebar_evidence":false,"sheet_code":"code from title block if legible else null","evidence_seen":"what you actually see (mention if rebar/DB/RB present or absent)","key_identifiers":"short summary"}"""

def grounding_block(text):
    """prompt variant B — แนบ text layer ที่ดึงมาแล้วเป็น ground truth"""
    return (
        "\n\n=== TEXT ที่ดึงจาก PDF text layer ของหน้านี้แล้ว (ถือเป็นความจริง) ===\n"
        f"{text[:4000]}\n"
        "กติกา: ค่าที่เป็นตัวอักษร/ตัวเลข (sheet code, element ID, เกรด, spacing) → เชื่อ TEXT ข้างบน "
        "ห้ามอ่านใหม่จากภาพและห้ามขัดแย้ง. ใช้ภาพเฉพาะ geometry/ตำแหน่ง/การนับที่ text ให้ไม่ได้.\n"
    )

# ── Stage B prompts (เนื้อหาเต็มใน Prompt/stage-b1|b2/prompt.md) ──────
THAI_NOTATION = """THAI RC NOTATION: "2DB16"=2 deformed bars 16mm (main_bar_count=2,dia=16,type=DB);
"RB6"=round bar 6mm (stirrup, type=RB); "ค1"=beam ,"ต1/C1"=column ,"พ1"=slab ,"F1/ฐ1"=footing;
"@0.10"/"@10cm"=spacing 100mm; fc' in ksc; grades SR24/SD30/SD40. Lengths: section=mm, span=m."""

CONFIDENCE_POLICY = """CONFIDENCE: every numeric/enum field pairs with confidence_score 0-1.
Not legible/absent -> value=null, confidence_score=0, add a tag to confidence_flags.
NEVER invent numbers. null+flag beats a guess. Output ONLY valid JSON, no markdown fences."""

def stage_b1_user(sheet_type):
    common = f"{THAI_NOTATION}\n{CONFIDENCE_POLICY}\n"
    if sheet_type == 'floor_plan':
        return common + """TASK: STRUCTURAL FLOOR/FRAMING PLAN. Do: (1) read floor_level, (2) read floor_area_sqm if shown,
(3) for each DISTINCT element mark COUNT instances, list grid_refs, read span_length_m for beams if dimensioned.
COUNTING: count only marks you can read; "ค1" and "ค1'" differ; dense/overlapping -> best count BUT add
"count_uncertain" and lower confidence. DO NOT read rebar/dimension specs here.
Return ONLY JSON:
{"sheet_type":"floor_plan","floor_level":"F1","floor_area_sqm":null,"grid_labels":[],
"elements":[{"element_id":"ค1","element_type":"beam","count":6,"grid_refs":["A-1/A-2"],
"span_length_m":3.0,"confidence_score":0.7,"confidence_flags":["count_uncertain"]}],"warnings":[]}"""
    if sheet_type == 'schedule_table':
        return common + """TASK: SCHEDULE TABLE (ตารางเสา/คาน). Read ROW BY ROW; one JSON object per row (per element mark).
Empty/illegible cell -> null + flag, do NOT copy from row above.
Return ONLY JSON:
{"sheet_type":"schedule_table","table_kind":"column_schedule","elements":[{"element_id":"ต1",
"element_type":"column","floor_applicable":"all","width_mm":200,"height_mm":200,"main_bar_count":4,
"main_bar_dia_mm":16,"main_bar_type":"DB","stirrup_dia_mm":6,"stirrup_type":"RB","stirrup_spacing_mm":200,
"stirrup_spacing_dense_mm":null,"stirrup_dense_zone_mm":null,"concrete_grade":"fc240","steel_grade":"SD40",
"confidence_score":0.88,"confidence_flags":[]}],"warnings":[]}"""
    # section_detail (default)
    return common + """TASK: SECTION/DETAIL sheet. For EVERY element cross-section read dimensions + reinforcement.
Return ONLY JSON:
{"sheet_type":"section_detail","elements":[{"element_id":"ค1","element_type":"beam","width_mm":200,
"height_mm":400,"main_bar_count":4,"main_bar_dia_mm":16,"main_bar_type":"DB","main_bar_top":"2DB16",
"main_bar_bottom":"2DB16","stirrup_dia_mm":6,"stirrup_type":"RB","stirrup_spacing_mm":150,
"stirrup_spacing_dense_mm":100,"stirrup_dense_zone_mm":1000,"concrete_grade":"fc240","steel_grade":"SD40",
"confidence_score":0.9,"confidence_flags":[]}],"warnings":[]}"""

STAGE_B2_USER = """You are reading the GENERAL NOTES / ข้อกำหนดทั่วไป page of a Thai RC drawing set.
Extract project-wide material specs + code standards. Read literally; value not on page -> null.
Notation: fc' in ksc; SR24/SD30/SD40; ระยะหุ้ม=cover; ระยะทาบ/Ld=lap; วสท./มอก./TIS=codes.
raw_notes: keep AT MOST 8 short structural items — do NOT transcribe the whole page.
Return ONLY JSON:
{"sheet_type":"general_notes","concrete_strength":{"default_ksc":240,"column_ksc":null,"beam_ksc":null,
"slab_ksc":null,"foundation_ksc":null,"confidence_score":0.9,"confidence_flags":[]},
"steel_grade":{"main_bar":"SD40","stirrup":"SR24","confidence_score":0.9,"confidence_flags":[]},
"concrete_cover_mm":{"beam":25,"column":25,"slab":20,"foundation":75,"confidence_score":0.8,"confidence_flags":[]},
"lap_length_rule":"40D","soil_bearing":{"value":null,"unit":null,"confidence_score":0,"confidence_flags":["not_on_page"]},
"design_codes":[],"raw_notes":[],"warnings":[]}"""

# ════════════════════════════════════════════════════════════════════
# API
# ════════════════════════════════════════════════════════════════════
def call_qwen(model, system, user_text, image_b64, max_tokens):
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ]},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }).encode('utf-8')
    req = urllib.request.Request(HOST + '/chat/completions', data=payload,
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': 'Bearer ' + KEY})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    content = data['choices'][0]['message']['content']
    usage = data.get('usage', {})
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"_parse_error": True, "raw": content}
    return parsed, usage

# ════════════════════════════════════════════════════════════════════
# helpers
# ════════════════════════════════════════════════════════════════════
def extract_pdf_text(pdf_path, page_index):
    if not (fitz and pdf_path and pdf_path.exists()):
        return None
    try:
        doc = fitz.open(pdf_path)
        if page_index < 0 or page_index >= doc.page_count:
            return None
        t = doc[page_index].get_text().strip()
        return t if t else None
    except Exception as e:
        print(f"   [text] extract error: {e}")
        return None

def page_index_from_filename(name):
    m = re.search(r'_หน้า(\d+)\.png$', name, re.IGNORECASE)
    return int(m.group(1)) - 1 if m else None

def route_from_code(sheet_code):
    if not sheet_code:
        return None
    up = sheet_code.upper().replace(' ', '')
    for prefix, disc in SHEET_CODE_MAP.items():
        if up.startswith(prefix.upper()):
            return disc
    return None

# ════════════════════════════════════════════════════════════════════
# per-page pipeline
# ════════════════════════════════════════════════════════════════════
def process_page(image_path, pdf_path, out_dir):
    name = image_path.name
    pidx = page_index_from_filename(name)
    print(f"\n📄 {name}  (page_index={pidx})")

    # ── Layer 1: text ─────────────────────────────────────────
    text = extract_pdf_text(pdf_path, pidx) if pidx is not None else None
    has_text = bool(text)
    print(f"   Layer1 text: {'✅ ' + str(len(text)) + ' chars' if has_text else '❌ none → pure vision'}")

    b64 = base64.b64encode(image_path.read_bytes()).decode()

    # ── Stage A: classify ─────────────────────────────────────
    user_a = STAGE_A_USER + (grounding_block(text) if has_text else "")
    t0 = time.time()
    a, ua = call_qwen(MODEL_CLASSIFY, STAGE_A_SYSTEM, user_a, b64, 500)
    sheet_type = a.get('sheet_type', 'unknown')
    sheet_code = a.get('sheet_code')
    # sheet-code routing ทับ sheet_type ถ้ารหัสชัด (deterministic > vision guess)
    disc = route_from_code(sheet_code)
    print(f"   StageA: sheet_type={sheet_type} conf={a.get('confidence')} "
          f"rebar={a.get('rebar_evidence')} code={sheet_code} disc={disc}  ({time.time()-t0:.1f}s)")
    if disc == 'architectural' and sheet_type in STRUCT_TYPES:
        print(f"   ⚠️  sheet-code says architectural but VLM said {sheet_type} → trust code, mark for review")

    # ── Stage B: route + extract ──────────────────────────────
    extraction, stage_b_model = None, None
    if disc in (None, 'structural') and sheet_type in STRUCT_TYPES:
        stage_b_model = MODEL_EXTRACT_STRUCT
        user_b = stage_b1_user(sheet_type) + (grounding_block(text) if has_text else "")
        time.sleep(RATE_LIMIT_DELAY)
        extraction, ub = call_qwen(stage_b_model, "You are a licensed Thai structural engineer.",
                                   user_b, b64, 2048)
        n = len(extraction.get('elements', [])) if isinstance(extraction, dict) else 0
        print(f"   StageB1 ({stage_b_model}): extracted {n} elements")
    elif sheet_type in NOTES_TYPES and disc in (None, 'structural'):
        # เฉพาะ general_notes ของงานโครงสร้าง — SN/EE/architectural notes ไม่มี structural spec
        stage_b_model = MODEL_EXTRACT_NOTES
        user_b = STAGE_B2_USER + (grounding_block(text) if has_text else "")
        time.sleep(RATE_LIMIT_DELAY)
        extraction, ub = call_qwen(stage_b_model, "You are a Thai structural engineer.",
                                   user_b, b64, 1500)
        print(f"   StageB2 ({stage_b_model}): spec extracted")
    else:
        print(f"   StageB: skipped (sheet_type={sheet_type}, disc={disc})")

    # ── save ──────────────────────────────────────────────────
    result = {
        "image_filename": name,
        "page_index": pidx,
        "text_layer_available": has_text,
        "prompt_variant": "B_grounded" if has_text else "A_vision",
        "classification": a,
        "routed_discipline": disc,
        "extraction": extraction,
        "stage_b_model": stage_b_model,
        "needs_human_review": sheet_type == 'section_detail' or (disc == 'architectural' and sheet_type in STRUCT_TYPES),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (image_path.stem + '.json')
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"   💾 {out_path.relative_to(BASE)}")
    log_action(file=out_path.relative_to(BASE), ai_model=stage_b_model or MODEL_CLASSIFY,
               action='extract' if stage_b_model else 'classify_only', house=out_dir.parent.name)
    return result

# ════════════════════════════════════════════════════════════════════
def find_pdf(folder):
    pdfs = list(folder.glob('*.pdf'))
    return pdfs[0] if pdfs else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--page', type=int, help='เลขหน้า (เช่น 13) — ทดสอบหน้าเดียว')
    args = ap.parse_args()

    folder = pathlib.Path(args.folder).resolve()
    house = folder.name
    pdf_path = find_pdf(folder)
    out_dir = BASE / 'raw' / 'image' / house / 'qwen-output'
    print(f"🏠 {house}  | PDF: {pdf_path.name if pdf_path else 'none'}  | out: {out_dir.relative_to(BASE)}")

    images = sorted([p for p in folder.glob('*.png')])
    if args.page is not None:
        tag = f"_หน้า{args.page:02d}.png"
        images = [p for p in images if p.name.endswith(tag)]
        if not images:
            print(f"❌ ไม่พบหน้า {args.page}")
            sys.exit(1)

    for img in images:
        try:
            process_page(img, pdf_path, out_dir)
        except urllib.error.HTTPError as e:
            print(f"   ❌ HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            print(f"   ❌ {type(e).__name__}: {e}")
        time.sleep(RATE_LIMIT_DELAY)

if __name__ == '__main__':
    main()
