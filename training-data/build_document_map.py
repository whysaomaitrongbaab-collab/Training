#!/usr/bin/env python3
"""
build_document_map.py — Stage 0: อ่านสารบัญ → สร้าง document map ของทั้งโปรเจกต์

แนวคิด (ตามที่ทีมออกแบบ):
  1. อ่านหน้าสารบัญ (table of contents) → ได้ discipline + sheet-code range + doc page start
  2. หา offset ระหว่าง "เลขหน้าในสารบัญ (doc page)" กับ "ไฟล์ PNG จริง (PDF page)"
     โดยอ่าน sheet_code ของ anchor page ไม่กี่หน้า
  3. LOCK เป็น map: PDF page ทุกหน้า → discipline (ไม่ต้อง classify geometry รายหน้าอีก)

Output: qwen-output/<house>/_document_map.json
Usage: python build_document_map.py <imageFolder> [--toc 02] [--anchors 20,40]
"""
import os, re, sys, json, time, base64, pathlib, argparse, urllib.request

BASE = pathlib.Path(__file__).resolve().parent

def load_env():
    env = {}
    for line in (BASE / '.env.local').read_text(encoding='utf-8').splitlines():
        m = re.match(r'^([A-Z_]+)=(.*)$', line)
        if m: env[m.group(1)] = m.group(2).strip()
    return env
ENV = load_env(); HOST = ENV['QWEN_API_HOST'].rstrip('/'); KEY = ENV['QWEN_API_KEY']
MODEL = 'qwen-vl-plus'

# ── discipline canonical names (extensible) ─────────────────────────
DISCIPLINE_ALIASES = {
    'สถาปัตยกรรม': 'architectural', 'architectural': 'architectural',
    'โครงสร้าง': 'structural', 'structural': 'structural',
    'สุขาภิบาล': 'sanitary', 'sanitary': 'sanitary',
    'ไฟฟ้า': 'electrical', 'electrical': 'electrical',
    'เครื่องกล': 'mechanical', 'mechanical': 'mechanical',
    'boq': 'boq', 'ปริมาณ': 'boq',
    'หลักเกณฑ์': 'regulatory', 'ข้อกำหนด': 'regulatory', 'regulatory': 'regulatory',
}
# discipline ที่ต้องส่ง extractor; นอกนั้น skip
# ⚠️ ต้องตรงกับกิ่ง extract จริงใน run_pipeline.py — ตอนนี้ = structural (Stage B) + boq (ตารางปริมาณ)
# (ถ้าเพิ่ม architectural ในอนาคต ต้องเพิ่มกิ่ง extract ใน run_pipeline.py ด้วย ไม่งั้น flag extract จะโกหก)
EXTRACT_DISCIPLINES = {'structural', 'boq'}

def call(system, user, b64, max_tokens, pixels=None):
    # pixels: (width, height) จริงของภาพ — ล็อก min/max_pixels กัน API ย่อภาพต่ำกว่า native
    # จนตัวอักษรไทยเล็กในสารบัญ/sheet-code อ่านไม่ออก (ดู CLAUDE.md บทเรียนข้อ 2)
    image_url = {"url": f"data:image/png;base64,{b64}"}
    if pixels:
        w, h = pixels
        image_url["min_pixels"] = w * h
        image_url["max_pixels"] = w * h
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": image_url},
            ]},
        ],
        "temperature": 0.0, "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }).encode('utf-8')
    req = urllib.request.Request(HOST + '/chat/completions', data=payload,
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + KEY})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return json.loads(data['choices'][0]['message']['content'])

def b64file(p):
    from PIL import Image
    return base64.b64encode(p.read_bytes()).decode(), Image.open(p).size

# ── Stage 0: read table of contents ─────────────────────────────────
TOC_SYSTEM = "You read the สารบัญ (table of contents) page of a Thai construction drawing set. Extract it verbatim into JSON."
TOC_USER = """This is the master table of contents (สารบัญ). Each row lists a discipline/section,
its sheet-code range (e.g. 'แผ่นที่ A-01 ถึง A-15'), and the starting page number (เลขหน้า).

Extract EVERY row. For each:
- title: the Thai section title as written
- sheet_prefix: the letter code (A, S, SN, EE, M) or null if none (e.g. BOQ rows)
- sheet_from / sheet_to: integers from the range, or null
- doc_page_start: the page number printed on that row

Return ONLY JSON:
{"is_toc":true,"rows":[
  {"title":"แบบสถาปัตยกรรม","sheet_prefix":"A","sheet_from":1,"sheet_to":15,"doc_page_start":1},
  {"title":"แบบวิศวกรรมโครงสร้าง","sheet_prefix":"S","sheet_from":1,"sheet_to":8,"doc_page_start":16},
  {"title":"บัญชีปริมาณงาน (BOQ) ฐานรากแผ่","sheet_prefix":null,"sheet_from":null,"sheet_to":null,"doc_page_start":36}
]}"""

CODE_SYSTEM = "You read ONLY the sheet code from the title block (มุมขวาล่าง) of a Thai drawing. Nothing else."
CODE_USER = 'Return ONLY the sheet code in the bottom-right title block. JSON: {"sheet_code":"S-03"}'

# sheet-code prefix → discipline (อ่านแม่นกว่าข้อความไทยยาว → ใช้เป็นหลัก)
PREFIX_DISCIPLINE = {'A': 'architectural', 'S': 'structural', 'SN': 'sanitary',
                     'EE': 'electrical', 'M': 'mechanical'}

def canon_discipline(title, sheet_prefix=None):
    # 1) prefix ตัดสินก่อน (สั้น อ่านแม่นสุด) — แบบเขียนจริงมี prefix เสมอ (A/S/SN/EE/M)
    if sheet_prefix and sheet_prefix.upper() in PREFIX_DISCIPLINE:
        return PREFIX_DISCIPLINE[sheet_prefix.upper()]
    # 2) fallback ที่ title — เฉพาะ section ที่เป็นข้อความล้วนไม่มี prefix (boq/regulatory)
    t = (title or '').lower()
    for k, v in DISCIPLINE_ALIASES.items():
        if k.lower() in t:
            return v
    # 3) ไม่มี prefix + ไม่ match alias → ไม่ใช่แบบเขียน (แบบเขียนมี prefix เสมอ)
    #    section ท้ายเล่มพวกนี้แทบทั้งหมดคือ BOQ/ตารางปริมาณ → default 'boq' (skip)
    #    ⚠️ ห้าม default เป็น structural แม้ title มีคำว่า 'ฐานราก/คาน/เสา' — ตาราง BOQ
    #       ก็มีคำพวกนี้ (บทเรียนข้อ 4) title ของแถวไม่มี prefix เชื่อไม่ได้
    if not sheet_prefix:
        return 'boq'
    # 4) มี prefix แต่ไม่รู้จัก (แปลก) → unknown เพื่อให้ human ตรวจ (จะถูก flag เตือน ไม่ skip เงียบ)
    return 'unknown'

def parse_code_num(code):
    """'S-03' -> ('S', 3) ; 'A-11' -> ('A', 11)"""
    m = re.match(r'([A-Za-z]+)[-\s]?0*(\d+)', code or '')
    return (m.group(1).upper(), int(m.group(2))) if m else (None, None)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--toc', default='02', help='PNG page number of the สารบัญ (default 02)')
    ap.add_argument('--anchors', default='', help='comma page numbers to detect offset, e.g. 20,40')
    args = ap.parse_args()

    folder = pathlib.Path(args.folder).resolve()
    house = folder.name
    imgs = {re.search(r'_หน้า(\d+)\.png$', p.name).group(1): p
            for p in folder.glob('*.png') if re.search(r'_หน้า(\d+)\.png$', p.name)}
    total_pages = len(imgs)
    print(f"🏠 {house} | {total_pages} pages")

    # ── Stage 0: read TOC ──
    toc_key = f"{int(args.toc):02d}"
    if toc_key not in imgs:
        sys.exit(f"❌ ไม่พบ PNG หน้าสารบัญ {toc_key} ใน {folder} "
                 f"(มีหน้า {min(imgs)}–{max(imgs)}) — ระบุ --toc ให้ถูก")
    print(f"📖 อ่านสารบัญจาก PNG หน้า {toc_key}…")
    toc_b64, toc_size = b64file(imgs[toc_key])
    toc = call(TOC_SYSTEM, TOC_USER, toc_b64, 1200, pixels=toc_size)
    rows = toc.get('rows', [])
    if not rows:
        sys.exit(f"❌ อ่านสารบัญไม่ได้ (0 rows) จากหน้า {toc_key} — "
                 f"เช็คว่าหน้านี้เป็นสารบัญจริงไหม หรือใช้ analyze_folder.py (per-page) แทน")
    for r in rows:
        r['discipline'] = canon_discipline(r.get('title', ''), r.get('sheet_prefix'))
    rows.sort(key=lambda r: r.get('doc_page_start') or 0)
    print(f"   พบ {len(rows)} sections:")
    for r in rows:
        rng = (f"{r['sheet_prefix']}-{r['sheet_from']:02d}..{r['sheet_to']:02d}"
               if r.get('sheet_prefix') and r.get('sheet_from') is not None and r.get('sheet_to') is not None
               else "—")
        print(f"     doc p.{r['doc_page_start']:>2} | {r['discipline']:<14} | {rng} | {r['title']}")

    # ── ตัดแถวที่ไม่มี doc_page_start (VLM อ่านตก) ออกก่อน — กัน crash ตอนเทียบ range ──
    warnings = []
    bad = [r for r in rows if r.get('doc_page_start') is None]
    for r in bad:
        warnings.append(f"row ไม่มี doc_page_start ถูกข้าม: {r.get('title')!r} (disc={r['discipline']})")
    rows = [r for r in rows if r.get('doc_page_start') is not None]

    # ── compute doc-page ranges per section (start .. next start-1) ──
    # แถวที่ start ซ้ำกัน (เช่น BOQ ซ้อนหัวข้อย่อย) จะได้ range ว่าง (end < start) → ตัดทิ้ง + เตือน
    for i, r in enumerate(rows):
        r['doc_page_end'] = (rows[i+1]['doc_page_start'] - 1) if i+1 < len(rows) else None
    kept = []
    for r in rows:
        end = r['doc_page_end']
        if end is not None and end < r['doc_page_start']:
            warnings.append(f"range ว่าง/ซ้อน ถูกข้าม: {r.get('title')!r} "
                            f"(doc p.{r['doc_page_start']}..{end}, disc={r['discipline']})")
            continue
        kept.append(r)
    rows = kept

    # ── detect offset: PDF(PNG) page = doc_page + offset ──
    # เช็ค anchor ทุกตัวที่ให้มา (อย่าเชื่อตัวแรกที่ parse ได้ทันที) — vl-plus อ่าน sheet-code
    # ในกรอบเล็กๆ ผิดได้ (เจอจริง: อ่าน "A-18" เป็น "S-03") ถ้าเชื่อ anchor เดียวจะได้ offset ผิด
    # แล้วทั้ง document map เลื่อนหน้าผิดหมดแบบเงียบๆ — ต้อง cross-check อย่างน้อย 2 anchor ให้ตรงกัน
    candidates = []  # (akey, code, offset)
    anchors = [a for a in args.anchors.split(',') if a.strip()]
    for a in anchors:
        akey = f"{int(a):02d}"
        if akey not in imgs: continue
        anchor_b64, anchor_size = b64file(imgs[akey])
        code = call(CODE_SYSTEM, CODE_USER, anchor_b64, 60, pixels=anchor_size).get('sheet_code')
        pref, num = parse_code_num(code)
        # หา section ที่ prefix ตรง แล้วคำนวณ doc page ของแผ่นนี้
        for r in rows:
            if r.get('sheet_prefix') == pref and r.get('sheet_from') is not None:
                doc_page = r['doc_page_start'] + (num - r['sheet_from'])
                off = int(a) - doc_page
                print(f"   ⚓ anchor PNG {akey}: code={code} → doc p.{doc_page} → offset={off:+d}")
                candidates.append((akey, code, off))
                break

    if len(candidates) >= 2 and len({c[2] for c in candidates}) > 1:
        detail = ', '.join(f"{k}={code}→{o:+d}" for k, code, o in candidates)
        sys.exit(f"❌ anchor ไม่ตรงกัน ({detail}) — น่าจะมี anchor ตัวใดตัวหนึ่งอ่าน sheet-code ผิด "
                 f"(vl-plus หลอนได้กับ title block เล็กๆ) ห้ามเดา offset เอง ให้ตรวจภาพจริงแล้วระบุ "
                 f"--anchors ใหม่ที่ทั้งคู่ตรงกัน")
    elif candidates:
        offset = candidates[0][2]
    else:
        offset = 2  # default: cover + toc
        warnings.append(f"ไม่มี anchor ตรงกับ sheet-code เลย ใช้ offset default {offset:+d} (ไม่ได้ตรวจ)")
        print(f"   ⚠️ ใช้ offset default {offset:+d} (ไม่ได้ตรวจ anchor)")

    # ── build per-PNG-page map ──
    page_map = {}
    for pnum in range(1, total_pages + 1):
        doc_page = pnum - offset
        disc = 'front_matter'  # ปก/สารบัญ (doc_page <= 0)
        for r in rows:
            end = r['doc_page_end'] if r['doc_page_end'] is not None else 9999
            if r['doc_page_start'] <= doc_page <= end:
                disc = r['discipline']; break
        page_map[f"{pnum:02d}"] = {"doc_page": doc_page, "discipline": disc,
                                    "extract": disc in EXTRACT_DISCIPLINES}

    # ── เตือนหน้า unknown ดังๆ (อย่าปล่อยให้ skip เงียบ = ความเสี่ยงข้อมูลหาย) ──
    unknown_pages = [k for k, v in page_map.items() if v['discipline'] == 'unknown']
    if unknown_pages:
        warnings.append(f"{len(unknown_pages)} หน้าเป็น discipline=unknown (prefix แปลก) "
                        f"ต้องให้คนตรวจว่าเป็น structural ที่พลาดไหม: {', '.join(unknown_pages)}")

    result = {"house": house, "toc_png_page": toc_key, "offset": offset,
              "sections": rows, "page_map": page_map,
              "extract_disciplines": sorted(EXTRACT_DISCIPLINES),
              "warnings": warnings}
    out = BASE / 'raw' / 'image' / house / 'qwen-output' / '_document_map.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    # summary
    from collections import Counter
    c = Counter(v['discipline'] for v in page_map.values())
    print(f"\n🗺️  Document map (offset {offset:+d}):")
    for disc, n in c.most_common():
        pages = [k for k, v in page_map.items() if v['discipline'] == disc]
        print(f"     {disc:<14} {n:>2} pages: {pages[0]}–{pages[-1]}  {'→ EXTRACT' if disc in EXTRACT_DISCIPLINES else '→ skip'}")
    if warnings:
        print("\n⚠️  WARNINGS (เก็บไว้ใน _document_map.json ด้วย):")
        for w in warnings:
            print(f"     • {w}")
    print(f"💾 {out.relative_to(BASE)}")

if __name__ == '__main__':
    main()
