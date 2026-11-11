#!/usr/bin/env python3
"""ล้างชุดเทรน t07 ก่อนเทรน — ตัดของที่ "อ่านจากแบบไม่ได้" ออกจากคำตอบที่สอน (assistant) และจากส่วนที่ต่อท้าย prompt (user)

ทำไมต้องมี (สิ่งที่ต้องแก้ ข้อ 68, ทดสอบ 3 ต.ค. 69 proof/04): คำตอบที่สอน Destrier มี path ไฟล์ที่มีชื่อบ้านเทรน
(source_image / source_pages / grid_source …) + ประวัติการแก้ข้อมูล (วันที่, "by_user", บันทึกสคริปต์ relabel)
โมเดลจำไปพ่นกับบ้านที่ไม่เคยเห็น — gridline วนนับหน้าของบ้านเทรนจนชนเพดาน 9,000 token
ไม่แตะไฟล์ GT ใน json_แก้ไขแล้ว (กฎข้อ 1) — ล้างที่ jsonl ที่ตัวสร้างชุดเทรนผลิตออกมาเท่านั้น

    python sanitize_labels.py <in.jsonl> [<in2.jsonl> ...] --out <โฟลเดอร์>   # เขียนไฟล์ชื่อเดิมลงโฟลเดอร์ใหม่
    python sanitize_labels.py <in.jsonl> ... --stats                          # นับอย่างเดียว ไม่เขียน
    python sanitize_labels.py --selftest
    exit code 1 = ด่านไม่ผ่าน (หลังล้างยังเหลือของต้องห้ามในข้อความ user/assistant หรือคำตอบไม่ใช่ JSON) — ห้ามเทรน

กติกา (รอบ t07, 11 พ.ย. 69 ตาม D5 — ปรับได้ แต่ต้องรันเทียบก่อน/หลังทุกครั้ง):
  1. คีย์ใน DROP_KEYS / ขึ้นต้น dummy_grid_rule_check / ชื่อคีย์ที่มีวันที่ ISO หรือคำต้องห้าม → ตัดทั้งคีย์ ทุกระดับความลึก
  2. ข้อความที่มีชื่อบ้านเทรน (ทุกจำนวนชั้น + house #N / houses 08-11 / บ้าน 157) หรือประวัติการแก้ (HISTORY_MARKERS):
     อยู่ใน list → ตัดทีละรายการ · เป็นค่าใน dict → ตัดคีย์นั้น — ทุกระดับความลึก ไม่ใช่แค่ warnings/confidence_flags
  3. elements[] ไม่ถูกตัดทิ้งเป็นตัว — ตัดได้แค่คีย์ข้างใน (assert นับทั้ง elements ชั้นบนและ views[].elements)
  4. ฝั่ง user: prompt ที่มาจากไฟล์ prompt ห้ามแตะ (worker ส่งไฟล์ตรงๆ — แก้ตรงนี้ = เทรนกับใช้จริงไม่ตรงกัน)
     ล้างเฉพาะท้าย GRID MASTER (แก้เป็น JSON ด้วยกติกาเดียวกับข้อ 1-2 · ท้ายที่สะอาดอยู่แล้วคงไว้ทุกไบต์)
     และ CV hint/ส่วนต่อท้ายอื่น (ลบเฉพาะคำต้องห้าม) — ของต้องห้ามที่อยู่ใน prompt เองจะถูกด่านนับ แล้วต้องไปแก้ที่ไฟล์ prompt
  5. (11 พ.ย. บ่าย) z_levels แบบสั้น {id, level_m, type} ใน grid ของ gridline และ "SHEET LIST" ท้าย prompt pass0 คือ
     เนื้อหาจากแบบ — sanitize_row ไม่แตะทั้งคู่ (ตัวสร้างชุดเป็นคนตัดทั้งท้ายทิ้งถ้าเจอคำต้องห้าม) · ด่านยังนับของต้องห้าม
     ในนั้น (SHEET LIST นับเป็น user_extra) และ schema_info เช็คคีย์ข้างในตาม allowlist ชื่อมีจุดใน KEYS.json
  ไม่ทำที่นี่ (เป็นงานตัวสร้างชุด build_t07): allowlist คีย์ชั้นบนต่อ subtask · แปลง pattern ของแถว plan_* ·
  ตัด specs / views แบบ list ของข้อความบนแถว plan — ด่านแค่รายงานเป็นข้อมูลประกอบ (schema_info) ไม่ตัดเอง
"""
import argparse
import functools
import json
import re
import sys
from collections import Counter
from pathlib import Path

DROP_KEYS = {
    # ที่มา/ตำแหน่งไฟล์ — worker ประทับเอง โมเดลมองไม่เห็นในภาพ (D5)
    "png", "doc_page", "source_image", "source_pages", "grid_source",
    # บันทึกตรวจ/ประวัติการแก้ที่ prompt ไม่ได้ขอ (prompts-labels.md ข้อ 5)
    "schema_generation", "schema_note", "spec_source", "spec_confidence_score", "spec_confidence_flags",
    "sibling_files", "printed_page", "title_block", "drawing_no", "field_map", "grid_dims_note",
    "building_footprint_note", "non_grid_dimensions_do_not_confuse", "warnings_local", "table_kind",
    "last_updated_from_page", "last_updated_date",
    # อ้างไฟล์อื่นในชุดข้อมูล (มีตั้งแต่รอบ 3 ต.ค.)
    "same_as", "source_pages_used_for_this_manifest", "corresponding_sheet_in_other_variant",
}
DROP_KEY_PREFIXES = ("dummy_grid_rule_check",)
FORBIDDEN_KEYS = ("png", "doc_page", "source_image", "source_pages", "grid_source")  # ด่านนับเป็นคีย์ JSON ทั้งสองฝั่ง

# ชื่อโฟลเดอร์บ้านเทรน ทุกจำนวนชั้น (เดิม [12]ชั้น — บ้าน 3/4 ชั้น 10 หลังหลุด)
HOUSE_NAME = re.compile(r"บ้าน_(?:เล็ก|ใหญ่)_\d+ชั้น_\d+")
# อ้างบ้านเทรนด้วยเลข (วัดใน GT 11 พ.ย.: ไม่เจอที่เป็นเนื้อหาจากแบบเลย — เป็นบันทึกคนทำข้อมูลทั้งหมด)
HOUSE_REF = re.compile(
    r"(?i:(?<![A-Za-z])houses?\s*(?:#\s*\d*|[-_ ]?\d{1,3}(?!\d)))"          # house #3 · houses 08-11 · house-70
    r"|บ้าน\s*#\s*\d+"                                                        # บ้าน#3
    r"|(?:บรรทัดฐาน|แบบอย่าง|บทเรียน|precedent)\s*(?:ของ)?\s*บ้าน\s*\d{1,3}(?![\d.])"  # ตามบรรทัดฐานบ้าน 14
    r"|บ้าน\s?(?:0\d|\d{3})(?![\d.])(?!\s*(?:ตร|ต\.ร|ชั้น|หลัง))"            # บ้าน 07 · บ้าน 157 (ไม่ใช่ หน้าบ้าน 3 / 20.00 ม.)
    r"|บ้าน\s?\d{1,3}(?:[/-]\d{1,3})+(?![\d.])(?!\s*ชั้น)")                   # บ้าน 09/16 · บ้าน 01-13
HOUSE = re.compile(HOUSE_NAME.pattern + "|" + HOUSE_REF.pattern)   # ชื่อนี้ t07_workflow ใช้วัดผลอ่าน — อย่าเปลี่ยนชื่อ

# ประวัติการแก้/กระบวนการทำข้อมูล — ด่านนับแยกทีละตัว · ตัวตาม D5 ไม่พึ่ง \b (_ นับเป็นตัวอักษรของ \b เลยพลาด)
# ป้าย CAPS ตรงตัวพิมพ์: ตัวเล็กเป็นธงความซื่อตรงที่ดีได้ ('not_normalized_to_match', 'span_unresolved', 'merged_cell')
HISTORY_MARKERS = {
    "iso_date": r"(?<!\d)20\d\d-\d\d-\d\d(?!\d)",            # NORMALIZED_2026-08-02 · op_fix_2026-09-29_x
    "op_fix": r"(?i:op_?fix)",
    "by_user": r"(?i:by[_ ]user)",                            # ADDED 2026-07-13 BY USER
    "added_by": r"(?i:added[_ ]by)",
    "CORRECTED_": r"CORRECTED_",
    "ADDED_": r"ADDED_",
    "NORMALIZED": r"NORMALI[ZS]ED",
    "MERGED_": r"MERGED_",
    "CASCADE_": r"CASCADE_",
    "RETRACTED": r"RETRACTED",
    "RESOLVED_": r"RESOLVED_",
    "REASSESSED": r"REASSESSED",
    "batch_derived": r"(?i:batch[- _]derived)",
    "reviewer": r"(?i:reviewer)",
    "claude": r"(?i:claude)",                                 # claude_output_03 · by_Claude
    "rawjson_": r"(?i:rawjson_)",
    "json_fixed_path": r"json_แก้ไขแล้ว",
    "mk_test": r"(?i:mk_test)",
    "carry_forward": r"(?i:carr(?:y|ied)[- _]forward)",
    "relabel_note": r"(?i:pattern re-labelled|Nothing else in this file changed)",
    "schema_upgrade": r"§\d+-upgrade",
    "dataset_meta": r"(?i:in the dataset|previous house|this extraction session|FORMAT LOCK)|สิ่งที่ต้องแก้",
    # ตัวเพิ่มจากที่วัดใน GT 11 พ.ย. (prompt t07 ที่โมเดลเห็น เจอ 0 ทุกตัว — ด่านจึงไม่ล้มเพราะ prompt):
    "person": r"(?i:makham|มะขาม)",
    "user": r"(?i:\buser\b)",
    "op_round": r"\bop[1-5]\b",                               # op1 precedence rule / op1 direct read
    "t_round": r"(?<![A-Za-z0-9_])t[1-5](?![A-Za-z0-9_]|\.\d)",  # matches t3's table · ไม่ใช่ความหนา t3.2
    "file_ref": r"\.(?:json|png|md|py)\b",                    # sibling _view1_x.json · tools/gridfix.py
}
HISTORY = re.compile("|".join(f"(?:{p})" for p in HISTORY_MARKERS.values()))
BAD = re.compile(HOUSE.pattern + "|" + HISTORY.pattern)

TAIL_MARK = "\n\nGRID MASTER (resolved axes for this building)\n"   # worker.py ~L1038/L1060 ตัวต่อตัว
SHEET_MARK = "\n\nSHEET LIST (from this drawing set's index page)\n"       # ท้าย prompt pass0 (SHEET_LIST_format.md)
GRID_SO_FAR_MARK = "\n\nGRID SO FAR (lines read from earlier pages of this building)\n"   # ท้าย prompt gridline (grid_incremental.MARK)
HINT_START = re.compile(r"\n\n(?:### )?สิ่งที่เครื่องตรวจภาพ \(CV\) เห็นบนแผ่นนี้")   # cv_scan.cv_hint_text (+รูปแบบเก่า)
_DEC = json.JSONDecoder()

GATE = {"house_name": HOUSE_NAME, "house_ref": HOUSE_REF,
        **{k: re.compile(v) for k, v in HISTORY_MARKERS.items()},
        **{f'key "{k}"': re.compile(r'"%s"\s*:' % k) for k in FORBIDDEN_KEYS}}

# allowlist คีย์ชั้นบน — ตัวสร้างชุดเป็นคนบังคับ ไฟล์นี้แค่รายงาน · ใช้ pass2/KEYS.json (คีย์ใน JSON ตัวอย่างของ prompt t07)
# ถ้าไม่มีไฟล์นั้น ใช้รายการตาม D5 ข้างล่าง
_PLAN = {"discipline", "sheet_code", "sheet_name", "pattern", "floor_level", "building", "view_title", "elements",
         "confidence_score", "confidence_flags", "warnings"}
ALLOW = {
    "gridline": {"pattern", "grid", "confidence_score", "confidence_flags", "warnings"},
    # ชื่อมีจุด = allowlist ของ dict ข้างใน (path ใต้ label) — 11 พ.ย. เพิ่ม z_levels แบบสั้น {id, level_m, type}
    "gridline.grid": {"x_lines", "y_lines", "z_levels"},
    "gridline.grid.x_lines": {"id", "pos_m", "type"}, "gridline.grid.y_lines": {"id", "pos_m", "type"},
    "gridline.grid.z_levels": {"id", "level_m", "type"},
    "plan_footing": _PLAN, "plan_beam": _PLAN, "plan_slab": _PLAN,
    "section": {"discipline", "sheet_code", "sheet_name", "pattern", "elements", "confidence_score", "confidence_flags",
                "warnings"},
    "schedule": {"discipline", "sheet_code", "sheet_name", "pattern", "columns", "elements", "confidence_score",
                 "confidence_flags", "warnings"},
    "notes": {"discipline", "sheet_code", "sheet_name", "pattern", "sections", "confidence_score", "confidence_flags",
              "warnings"},
    "pass0": {"sheet_code", "sheet_name", "discipline", "building", "views", "confidence_score", "warnings"},
}
ALLOW_SOURCE = "D5"
try:
    _k = json.loads((Path(__file__).resolve().parent / "pass2" / "KEYS.json").read_text(encoding="utf-8"))
    if isinstance(_k, dict) and all(isinstance(v, list) and all(isinstance(x, str) for x in v) for v in _k.values()):
        ALLOW, ALLOW_SOURCE = {s: set(v) for s, v in _k.items()}, "pass2/KEYS.json"
except (OSError, ValueError):
    pass
SUBTASK_PATTERN = {"gridline": "grid_master", "plan_footing": "footing_plan", "plan_beam": "beam_plan",
                   "plan_slab": "etc_plan"}   # = worker.py SUBTASK_PATTERN


def _bad(s):
    return BAD.search(s) is not None


def scrub(obj, st):
    """คืนสำเนาที่ล้างแล้ว · st นับสิ่งที่ตัด (ไม่แก้ obj ของผู้เรียก)"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in DROP_KEYS or k.startswith(DROP_KEY_PREFIXES):
                st["drop_key"] += 1
                continue
            if _bad(k):                      # ชื่อคีย์เองมีวันที่/ชื่อบ้าน เช่น dummy_..._2026-07-08
                st["drop_key_name"] += 1
                continue
            if isinstance(v, str) and _bad(v):
                st["drop_text"] += 1
                continue
            out[k] = scrub(v, st)
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            if isinstance(v, str) and _bad(v):
                st["drop_item"] += 1
                continue
            out.append(scrub(v, st))
        return out
    return obj


def n_elements(doc):
    """นับ element ทั้ง elements[] ชั้นบน และ views[].elements (แถว plan บ้านที่เก็บแยกตามวิว)"""
    if not isinstance(doc, dict):
        return 0
    n = len(doc["elements"]) if isinstance(doc.get("elements"), list) else 0
    views = doc.get("views")
    for v in views if isinstance(views, list) else ():
        if isinstance(v, dict) and isinstance(v.get("elements"), list):
            n += len(v["elements"])
    return n


def _text_parts(content):
    """[(ตำแหน่งใน content หรือ None ถ้า content เป็น str, ข้อความ)]"""
    if isinstance(content, str):
        return [(None, content)]
    if not isinstance(content, list):
        return []
    return [(i, p["text"]) for i, p in enumerate(content)
            if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str)]


def _set_text(msg, idx, text):
    if idx is None:
        msg["content"] = text
    else:
        msg["content"][idx]["text"] = text


def split_prompt(text):
    """ข้อความ user ส่วนแรก → (prompt จากไฟล์, ท้าย GRID MASTER พร้อมหัว, ส่วนต่อท้ายที่เหลือ เช่น CV hint)"""
    i = text.find(TAIL_MARK)
    if i >= 0:
        j = i + len(TAIL_MARK)
        try:
            end = _DEC.raw_decode(text, j)[1]
        except ValueError:
            end = len(text)              # JSON เสีย → ถือว่าที่เหลือทั้งหมดเป็นท้าย ล้างแบบข้อความ
        return text[:i], text[i:end], text[end:]
    m = HINT_START.search(text)
    if m:
        return text[:m.start()], "", text[m.start():]
    return text, "", ""


def _scrub_plain(s, st):
    """ลบเฉพาะคำต้องห้ามในข้อความล้วน (CV hint / ส่วนต่อท้าย) — ไม่แตะส่วนอื่น"""
    new = HISTORY.sub("", HOUSE.sub("", s))
    if new != s:
        st["user_fixed"] += 1
    return new


def _scrub_tail(tail, st):
    raw = tail[len(TAIL_MARK):]
    try:
        doc = json.loads(raw)
    except ValueError:
        return TAIL_MARK + _scrub_plain(raw, st)
    local = new_stats()
    clean = scrub(doc, local)
    if not (local["drop_key"] or local["drop_key_name"] or local["drop_text"] or local["drop_item"]):
        return tail                      # สะอาดอยู่แล้ว → ไบต์เดิม (ตรงกับที่ worker ประกอบ)
    st["user_fixed"] += 1
    return TAIL_MARK + json.dumps(clean, ensure_ascii=False)


def _clean_user_text(text, st, first):
    if not first:                        # ส่วนข้อความที่ 2+ (hint แบบ t05) — ไม่มี prompt จากไฟล์ในนั้น
        return _scrub_plain(text, st)
    body, tail, rest = split_prompt(text)
    return body + (_scrub_tail(tail, st) if tail else "") + (_scrub_plain(rest, st) if rest else "")


def _clean_label(txt, st):
    try:
        doc = json.loads(txt)
    except ValueError:
        st["not_json"] += 1
        return txt
    n_el = n_elements(doc)
    clean = scrub(doc, st)
    assert n_elements(clean) == n_el, "ห้ามตัด element ทิ้งทั้งตัว"
    new = json.dumps(clean, ensure_ascii=False)
    st["chars_before"] += len(txt)
    st["chars_after"] += len(new)
    return new


def sanitize_row(row, st):
    row = json.loads(json.dumps(row, ensure_ascii=False))   # สำเนา — ไม่แก้ของผู้เรียก
    for msg in row.get("messages") or []:
        parts = _text_parts(msg.get("content"))
        if msg.get("role") == "assistant":
            for idx, txt in parts[:1]:
                _set_text(msg, idx, _clean_label(txt, st))
        elif msg.get("role") == "user":
            for n, (idx, txt) in enumerate(parts):
                _set_text(msg, idx, _clean_user_text(txt, st, first=n == 0))
    return row


def _hits(text):
    return [name for name, rx in GATE.items() if rx.search(text)]


_prompt_hits = functools.lru_cache(maxsize=256)(_hits)   # prompt จากไฟล์ซ้ำกันทุกแถวของ subtask เดียวกัน


def leak_counts(rows):
    """นับแถวที่ยังมีของต้องห้าม แยกช่อง: assistant · user_extra (ท้าย GRID MASTER/hint/ส่วนต่อท้าย) ·
    user_prompt (prompt จากไฟล์ — sanitize ไม่แตะ ถ้าไม่ใช่ 0 ต้องแก้ที่ไฟล์ prompt) → (จำนวนแถว, Counter[(ช่อง, รายการ)])"""
    c = Counter()
    n = 0
    for r in rows:
        n += 1
        seen = set()
        for msg in r.get("messages") or []:
            parts = _text_parts(msg.get("content"))
            if msg.get("role") == "assistant":
                for _, t in parts:
                    seen.update(("assistant", h) for h in _hits(t))
            elif msg.get("role") == "user":
                for k, (_, t) in enumerate(parts):
                    body, tail, rest = split_prompt(t) if k == 0 else ("", t, "")
                    for mark in (SHEET_MARK, GRID_SO_FAR_MARK):   # SHEET LIST / GRID SO FAR = เนื้อหาจากแบบ ไม่ใช่ไฟล์ prompt
                        i = body.find(mark)
                        if i >= 0:
                            body, tail = body[:i], body[i:] + tail
                    seen.update(("user_prompt", h) for h in _prompt_hits(body))
                    seen.update(("user_extra", h) for h in _hits(tail + rest))
        c.update(seen)
    return n, c


def gate_failures(after, st):
    """รายการที่ทำให้ด่านไม่ผ่าน — ว่าง = ผ่าน"""
    bad = [f"{ch}/{name} {v}" for (ch, name), v in sorted(after.items()) if v]
    if st["not_json"]:
        bad.append(f"assistant/not_json {st['not_json']}")
    return bad


def _nodes(doc, path):
    """dict ทุกตัวที่ path (เช่น ["grid", "z_levels"]) ชี้ถึงใต้ doc — list กางเป็นรายตัว"""
    cur = [doc]
    for k in path:
        nxt = []
        for c in cur:
            v = c.get(k) if isinstance(c, dict) else None
            nxt += v if isinstance(v, list) else [v]
        cur = nxt
    return [c for c in cur if isinstance(c, dict)]


def schema_info(rows):
    """ข้อมูลประกอบ ไม่นับเป็นด่าน: คีย์ชั้นบนนอก ALLOW ต่อ subtask (+ คีย์ข้างในตาม allowlist ชื่อมีจุด เช่น
    gridline.grid.z_levels) + pattern ที่ไม่ตรง SUBTASK_PATTERN"""
    off, pat = Counter(), Counter()
    for r in rows:
        sub = r.get("subtask")
        msgs = r.get("messages") or []
        parts = _text_parts(msgs[-1].get("content")) if msgs else []
        try:
            doc = json.loads(parts[0][1]) if parts else None
        except ValueError:
            continue
        if not isinstance(doc, dict):
            continue
        off.update(f"{sub}.{k}" for k in doc if sub in ALLOW and k not in ALLOW[sub])
        for name in ALLOW:
            head, _, tail = name.partition(".")
            if tail and head == sub:
                off.update(f"{name}.{k}" for node in _nodes(doc, tail.split(".")) for k in node if k not in ALLOW[name])
        if sub in SUBTASK_PATTERN and doc.get("pattern") != SUBTASK_PATTERN[sub]:
            pat[f"{sub}:{doc.get('pattern')}"] += 1
    return off, pat


def new_stats():
    return dict.fromkeys(("drop_key", "drop_key_name", "drop_text", "drop_item", "user_fixed", "not_json",
                          "chars_before", "chars_after"), 0)


def _fmt(c):
    by = {}
    for (ch, name), v in sorted(c.items()):
        if v:
            by.setdefault(ch, []).append(f"{name} {v}")
    return " | ".join(f"{ch}[{', '.join(v)}]" for ch, v in by.items()) or "0"


def selftest():
    def row(user_texts, label, subtask="plan_beam"):
        return {"id": "บ้าน_เล็ก_1ชั้น_02::x::" + subtask, "house": "บ้าน_เล็ก_1ชั้น_02", "subtask": subtask,
                "messages": [
                    {"role": "user", "content": [{"type": "image", "image": "image/บ้าน_เล็ก_1ชั้น_02/a.png"}]
                     + [{"type": "text", "text": t} for t in user_texts]},
                    {"role": "assistant", "content": [{"type": "text", "text": json.dumps(label, ensure_ascii=False)}]}]}

    def label_of(r):
        return json.loads(r["messages"][-1]["content"][0]["text"])

    def user_texts(r):
        return [t for _, t in _text_parts(r["messages"][0]["content"])]

    # 1) กติกาฝั่งคำตอบ (ของเดิม 3 ต.ค. + ทุกกติกาใหม่)
    lab = {
        "png": "20", "doc_page": 20, "discipline": "structural", "pattern": "beam_plan",
        "source_pages": ["image/บ้าน_เล็ก_1ชั้น_02/a.png"],
        "note": "unlike house #1 which had overhang", "last_updated_date": "2026-07-19",
        "dummy_grid_rule_check_2026-07-08": "ok", "note_2026-07-01": "x",            # ชื่อคีย์มีวันที่
        "grid": {"x_lines": [
            {"id": "1", "pos_m": 0, "type": "named", "source_image": "image/บ้าน_เล็ก_1ชั้น_02/b.png",
             "confidence_flags": ["added_2026-07-16_by_user_from_page12", "edge_read_twice",
                                  "split_out_2026-08-02 from the footing entries"],    # วันที่ติดขีดล่าง ไม่มีคำอื่นช่วย
             "note": "dimension tick, section 4 rule 4 (added by op_fix 2026-09-29)",   # ค่าใน dict มีประวัติ
             "source": "ADDED 2026-07-13 BY USER"},
            {"id": "2", "pos_m": 3.5, "type": "dummy", "source": "printed on S-02", "note": "ตามแบบอย่างบ้าน 157"}]},
        "views": ["แปลนคาน ชั้น 1", "รูปตัด A-A"],                  # list ข้อความบนแถว plan — งานตัวสร้างชุด ห้ามตัดที่นี่
        "elements": [
            {"element_id": "B1", "png": "x", "source_image": "p.png", "note": "เหมือน บ้าน_ใหญ่_3ชั้น_09 หน้า41",
             "confidence_flags": ["op_fix_2026-09-29_makham_ruling_6: was on x 3.30",
                                  "multi_line_spec_merged_into_one_row", "span_unresolved_no_grid",
                                  "not_normalized_to_match", "label_is_reviewer_key_not_printed_text"]},
            {"element_id": "B2", "note": "บันไดหน้าบ้าน 3 ลูกตั้ง สายเมนเข้าบ้าน 20.00 ม."}],
        "warnings": ["pattern re-labelled 'etc_plan' -> 'beam_plan'. Nothing else in this file changed.",
                     "NORMALIZED_2026-08-02: a packed size string was replaced",
                     "matching the id style houses 08-11 already use",
                     "Independent re-read (t4) matches t3's table verbatim",
                     "see sibling _หน้า07_floor_plan_upper.json",
                     "image/บ้าน_ใหญ่_4ชั้น_01/x.png",
                     "เหล็กรูปตัว C 100x50x20 t3.2 5.50 kg/m",
                     "ระยะ 3.20 บนแบบเบลอ อ่านจากผลรวม"],
    }
    r1 = row(["PROMPT"], lab)
    st = new_stats()
    out = sanitize_row(r1, st)
    d = label_of(out)
    for k in ("png", "doc_page", "source_pages", "note", "last_updated_date", "dummy_grid_rule_check_2026-07-08",
              "note_2026-07-01"):
        assert k not in d, k
    assert d["discipline"] == "structural" and d["pattern"] == "beam_plan"
    x0, x1 = d["grid"]["x_lines"]
    assert x0 == {"id": "1", "pos_m": 0, "type": "named", "confidence_flags": ["edge_read_twice"]}, x0
    assert x1 == {"id": "2", "pos_m": 3.5, "type": "dummy", "source": "printed on S-02"}, x1
    assert d["views"] == ["แปลนคาน ชั้น 1", "รูปตัด A-A"], d["views"]
    b1, b2 = d["elements"]
    assert b1 == {"element_id": "B1", "confidence_flags": ["multi_line_spec_merged_into_one_row",
                                                           "span_unresolved_no_grid", "not_normalized_to_match"]}, b1
    assert b2["note"] == "บันไดหน้าบ้าน 3 ลูกตั้ง สายเมนเข้าบ้าน 20.00 ม.", b2
    assert d["warnings"] == ["เหล็กรูปตัว C 100x50x20 t3.2 5.50 kg/m", "ระยะ 3.20 บนแบบเบลอ อ่านจากผลรวม"], d["warnings"]
    assert "บ้าน_เล็ก" in r1["messages"][-1]["content"][0]["text"], "ต้องไม่แก้ object ของผู้เรียก"
    assert st["drop_key_name"] == 1 and st["not_json"] == 0, st   # note_2026-07-01 (dummy_… ตัดด้วย prefix)
    n, after = leak_counts([out])
    assert n == 1 and not gate_failures(after, st), after
    n, before = leak_counts([r1])
    for name in ("house_name", "house_ref", "iso_date", "op_fix", "by_user", "added_by", "NORMALIZED", "relabel_note",
                 "person", "reviewer", "t_round", "file_ref", 'key "png"', 'key "doc_page"', 'key "source_pages"',
                 'key "source_image"'):
        assert before[("assistant", name)] == 1, name
    # element ใน views[].elements ก็ห้ามหาย
    lv = {"views": [{"view": "v1", "elements": [{"element_id": "F1", "note": "บ้าน_เล็ก_1ชั้น_02"}, {"element_id": "F2"}]}]}
    dv = label_of(sanitize_row(row(["PROMPT"], lv), new_stats()))
    assert n_elements(dv) == 2 and dv["views"][0]["elements"][0] == {"element_id": "F1"}, dv

    # 2) ฝั่ง user: prompt ห้ามแตะ · ท้าย GRID MASTER/hint ล้าง · ท้ายที่สะอาดคงไบต์เดิม
    prompt = "COMMON\n\nPROMPT: ตอบเป็น JSON"
    dirty = {"grid": {"x_lines": [{"id": "1", "pos_m": 0, "type": "named",
                                   "source_image": "image/บ้าน_เล็ก_1ชั้น_16/a.png",
                                   "confidence_flags": ["added_2026-07-19_by_user"]}],
                      "y_lines": [{"id": "A", "pos_m": 0.0, "type": "named"}]}}
    slim = {"grid": {"x_lines": [{"id": "1", "pos_m": 0, "type": "named", "confidence_flags": []}],
                     "y_lines": [{"id": "A", "pos_m": 0.0, "type": "named"}]}}
    tail_dirty = TAIL_MARK + json.dumps(dirty, ensure_ascii=False)
    tail_clean = TAIL_MARK + json.dumps(slim, ensure_ascii=False)
    hint = "\n\nสิ่งที่เครื่องตรวจภาพ (CV) เห็นบนแผ่นนี้ hint ไม่ใช่คำตอบ\n- คาน (beam) จำนวน 3 จุด"
    lab2 = {"pattern": "beam_plan", "elements": [{"element_id": "B1"}]}
    st = new_stats()
    a = sanitize_row(row([prompt + tail_dirty + hint + " (บ้าน_เล็ก_1ชั้น_16)"], lab2), st)       # แบบ t07: ส่วนเดียว
    assert user_texts(a) == [prompt + tail_clean + hint + " ()"], user_texts(a)
    b = sanitize_row(row([prompt + tail_dirty, hint + " op_fix 2026-09-29"], lab2), st)            # แบบ t05: hint แยกส่วน
    assert user_texts(b) == [prompt + tail_clean, hint + "  "], user_texts(b)
    keep = [prompt + tail_clean + hint]
    c = sanitize_row(row(keep, lab2), st)                                                         # สะอาดแล้ว → ไม่ขยับ
    assert user_texts(c) == keep
    assert st["user_fixed"] == 4, st
    n, after = leak_counts([a, b, c])
    assert not gate_failures(after, st), after
    n, before = leak_counts([row([prompt + tail_dirty + hint], lab2)])
    assert before[("user_extra", "house_name")] == 1 and before[("user_extra", 'key "source_image"')] == 1, before
    # ของต้องห้ามใน prompt เอง: ไม่แตะ แต่ด่านต้องเห็นและล้ม
    bad_prompt = 'COMMON\n\n```json\n{ "png": "20", "pattern": "beam_plan" }\n``` (schema §1, split 2026-08-28)'
    e = sanitize_row(row([bad_prompt + tail_clean], lab2), new_stats())
    assert user_texts(e) == [bad_prompt + tail_clean]
    n, after = leak_counts([e])
    fails = gate_failures(after, new_stats())
    assert fails == ['user_prompt/iso_date 1', 'user_prompt/key "png" 1'], fails

    # 3) pass0: ตัด png/doc_page + คำเตือนสคริปต์ batch-derived · views ที่เป็น dict คงไว้
    l0 = {"png": "20", "doc_page": 20, "sheet_code": "S-03", "sheet_name": "แปลนฐานราก", "discipline": "structural",
          "building": "main", "views": [{"subtask": "plan_footing", "where": "full", "also_gridline": True}],
          "confidence_score": 0.85, "warnings": ["batch-derived: ยืนยันด้วยตา 5 หน้า จาก 5 บ้าน", "หน้านี้มี 2 แผ่น"]}
    d0 = label_of(sanitize_row(row(["P0"], l0, "pass0"), new_stats()))
    assert d0 == {k: v for k, v in l0.items() if k not in ("png", "doc_page")} | {"warnings": ["หน้านี้มี 2 แผ่น"]}, d0

    # 4) คำตอบที่ไม่ใช่ JSON → ไม่แตะ แต่ด่านไม่ผ่าน
    nj = row(["P"], {})
    nj["messages"][-1]["content"][0]["text"] = "{not json"
    st = new_stats()
    sanitize_row(nj, st)
    assert gate_failures(Counter(), st) == ["assistant/not_json 1"], st

    # 5) schema_info เห็นคีย์นอก allowlist / pattern ที่ยังไม่แปลง (รายงานอย่างเดียว)
    off, pat = schema_info([out, row(["P"], {"pattern": "plan", "specs": {}, "elements": []}, "plan_slab")])
    assert off == Counter({"plan_beam.grid": 1, "plan_beam.views": 1, "plan_slab.specs": 1}), off
    assert pat == Counter({"plan_slab:plan": 1}), pat

    # 6) z_levels แบบสั้น (11 พ.ย.): รอด scrub ครบทั้ง 3 คีย์ · คีย์เกินใน entry ถูกรายงานโดย schema_info ตาม allowlist ชื่อมีจุด
    zg = {"pattern": "grid_master",
          "grid": {"x_lines": [{"id": "1", "pos_m": 0.0, "type": "named"}], "y_lines": [{"id": "A", "pos_m": 0.0, "type": "named"}],
                   "z_levels": [{"id": "ระดับอ้างอิง", "level_m": 0.0, "type": "datum"},
                                {"id": None, "level_m": -1.5, "type": "dummy"},
                                {"id": "ระดับหลังคาน", "level_m": 3.75, "type": "named"}]},
          "confidence_score": 0.9, "confidence_flags": [], "warnings": []}
    gr = row(["PROMPT"], zg, "gridline")
    gz = sanitize_row(gr, new_stats())
    assert label_of(gz) == zg and gz["messages"][-1] == gr["messages"][-1], label_of(gz)     # ไบต์เดิม ไม่ขยับ
    assert schema_info([gz]) == (Counter(), Counter()), schema_info([gz])
    n, after = leak_counts([gz])
    assert not gate_failures(after, new_stats()), after
    zbad = json.loads(json.dumps(zg))
    zbad["grid"]["z_levels"][0]["source_image"] = "image/บ้าน_เล็ก_1ชั้น_02/b.png"
    zbad["grid"]["y_lines"][0]["note"] = "x"
    off, _ = schema_info([row(["PROMPT"], zbad, "gridline")])
    assert off == Counter({"gridline.grid.z_levels.source_image": 1, "gridline.grid.y_lines.note": 1}), off
    zc = label_of(sanitize_row(row(["PROMPT"], zbad, "gridline"), new_stats()))
    assert "source_image" not in zc["grid"]["z_levels"][0], zc                    # source_image ถูกตัดโดย DROP_KEYS เหมือนเดิม

    # 7) SHEET LIST ท้าย pass0: sanitize_row ไม่แตะ · ด่านนับของต้องห้ามในนั้นเป็น user_extra (ไม่ใช่ user_prompt)
    sl_ok = SHEET_MARK + json.dumps([{"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-08"},
                                     {"title": "หลักเกณฑ์และข้อกำหนด", "sheet_range": None}], ensure_ascii=False)
    p0 = row(["PASS0 PROMPT" + sl_ok], {"sheet_code": None, "views": [], "warnings": []}, "pass0")
    p0c = sanitize_row(p0, new_stats())
    assert user_texts(p0c) == ["PASS0 PROMPT" + sl_ok], user_texts(p0c)
    n, after = leak_counts([p0c])
    assert not gate_failures(after, new_stats()), after
    sl_bad = SHEET_MARK + json.dumps([{"title": "แบบ บ้าน_เล็ก_1ชั้น_02 หน้า 3", "sheet_range": "A-01"}], ensure_ascii=False)
    p1 = sanitize_row(row(["PASS0 PROMPT" + sl_bad], {"views": []}, "pass0"), new_stats())
    assert user_texts(p1) == ["PASS0 PROMPT" + sl_bad], "sanitize ต้องไม่ตัด SHEET LIST เอง"
    n, after = leak_counts([p1])
    assert after[("user_extra", "house_name")] == 1 and after[("user_prompt", "house_name")] == 0, after
    assert gate_failures(after, new_stats()) == ["user_extra/house_name 1"], after
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if not a.inputs or not (a.out or a.stats):
        sys.exit("ต้องใส่ไฟล์ jsonl และ --out หรือ --stats")
    failed = []
    for f in a.inputs:
        rows = [json.loads(line) for line in open(f, encoding="utf-8") if line.strip()]
        st = new_stats()
        clean = [sanitize_row(r, st) for r in rows]
        n, before = leak_counts(rows)
        _, after = leak_counts(clean)
        shrink = 1 - st["chars_after"] / st["chars_before"] if st["chars_before"] else 0
        print(f"{Path(f).name}: แถว {n} · ตัดคีย์ {st['drop_key']} (ชื่อคีย์ติดธง {st['drop_key_name']}) · "
              f"ตัดค่าข้อความ {st['drop_text']} · ตัดรายการ {st['drop_item']} · แก้ข้อความฝั่ง user {st['user_fixed']} · "
              f"คำตอบสั้นลง {shrink:.1%} · ไม่ใช่ JSON {st['not_json']}")
        print(f"  ก่อนล้าง (แถวที่เจอ): {_fmt(before)}")
        print(f"  หลังล้าง (แถวที่เจอ): {_fmt(after)}")
        off, pat = schema_info(clean)
        if off or pat:
            print(f"  ข้อมูลประกอบ ไม่นับเป็นด่าน — คีย์ชั้นบนนอก allowlist ({ALLOW_SOURCE}): {dict(off.most_common())} · "
                  f"pattern ไม่ตรง worker: {dict(pat)}")
        fails = gate_failures(after, st)
        if fails:
            failed.append(Path(f).name)
            in_prompt = sum(v for (ch, _), v in after.items() if ch == "user_prompt")
            print(f"  ด่าน: ไม่ผ่าน — {', '.join(fails)}"
                  + (" (ส่วน user_prompt มาจากไฟล์ prompt — sanitize ไม่แตะ ต้องแก้ที่ไฟล์ prompt)" if in_prompt else ""))
        else:
            print("  ด่าน: ผ่าน")
        if a.out:
            Path(a.out).mkdir(parents=True, exist_ok=True)
            with open(Path(a.out) / Path(f).name, "w", encoding="utf-8") as w:
                for r in clean:
                    w.write(json.dumps(r, ensure_ascii=False) + "\n")
    if failed:
        print(f"ด่านไม่ผ่าน {len(failed)}/{len(a.inputs)} ไฟล์: {', '.join(failed)} — ห้ามเทรนด้วยชุดนี้")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
