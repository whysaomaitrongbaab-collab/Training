#!/usr/bin/env python3
"""
tools/pass1_toc.py — Pass 1 ส่วนเสริม: หน้าสารบัญ -> รายการแผ่น (SHEET LIST) -> เทียบกับประเภทหน้าที่ t07 pass0 อ่านได้
(สั่งโดยมะขาม 21 พ.ย. 2569: OCR ดึงหน้าสารบัญเป็นข้อความ ส่งให้ t07 จำแนกว่าหน้าไหนควรเป็นประเภทอะไร ระบบ fail-safe;
 ถ้าสารบัญกับ t07 ไม่ตรงกัน = เตือน + เอาผลทั้งสองมา union)

สถานะจริง (บอกตรงๆ): ไฟล์นี้เป็น "ตรรกะที่ไม่ขึ้นกับ t07 และไม่ขึ้นกับ OCR" เท่านั้น — t07 ยังไม่ได้เทรน และ worker ยังไม่ส่งหาง SHEET LIST
(tune_ai/t07_Palfrey/old_shit/เอกสาร/SHEET_LIST_format.md) จึงยังไม่มีผลอ่านจริงของ t07 ให้เทียบ; ที่ทดสอบได้คือตรรกะด้วยค่าที่แต่งขึ้น
ยังไม่ได้ต่อ: หาหน้าสารบัญ + OCR + แยกแถวจากข้อความ OCR (ส่วนนี้ต้องทดสอบกับหน้าจริง) · ไม่ได้แตะ pass1_sheet_classify.py

สิ่งที่ทำ:
  1. sheet_list_tail(entries) = หางข้อความที่ t07 ถูกสอน (ไบต์ต่อไบต์ตามฟอร์แมต: คีย์ title แล้ว sheet_range เท่านั้น, json.dumps ค่าเริ่มต้น,
     ensure_ascii=False, ไม่มีรายการ = ไม่มีหาง) — ต่างจากนี้ = train/serve mismatch
  2. expand_range("S-01 ถึง S-08") -> รหัสแผ่นทั้งช่วง; entry_types(title, range) -> ชุด subtask ที่สารบัญบอก (ตาราง "คำไทย -> subtask"
     ย่อจาก pass0/prompt.md ของ t07; ชื่อโหลดไม่ออกแต่รู้ระบบจากรหัส/ชื่อระบบ = ชุด subtask ทั้งระบบ (หยาบ))
  3. toc_types_by_page(entries, page_codes) = ผูกรายการสารบัญกับหน้า PDF ผ่านรหัสแผ่น (หน้า -> ชุด subtask) · หลายรายการใช้รหัสเดียวกัน = เอารายการที่เจาะจงสุด
  4. reconcile(toc, t07) ต่อหน้า:
       ทั้งคู่มี + มีตัวร่วม  -> agree: types = ตัวร่วม (สารบัญหยาบไม่ทำให้ผลบานเป็นทั้งระบบ)
       ทั้งคู่มี + ไม่มีตัวร่วม -> mismatch: types = UNION ของทั้งสอง + warning
       t07 ไม่มี (ล้ม/ยังไม่รัน)  -> toc_only: ใช้สารบัญ + warning t07_unavailable      (fail-safe)
       สารบัญไม่มีแถวของหน้า    -> t07_only: ใช้ t07 (ไม่ใช่ความผิด สารบัญบางเล่มไม่ครบ) + note toc_has_no_row
       ไม่มีทั้งสอง             -> none: ผู้เรียกต้องใช้ทางเดิม (เช่นรหัสแผ่น) ห้ามเดาประเภท

    python tools/pass1_toc.py --demo     # self-check ตรรกะ (ไม่ต้องมีไฟล์จริง)
"""
import json
import re
import sys

SHEET_MARK = "\n\nSHEET LIST (from this drawing set's index page)\n"     # ต้องตรงกับ SHEET_MARK ใน t07 sanitize_labels.py

STRUCTURAL = {"plan_footing", "plan_column", "plan_beam", "plan_slab", "section", "schedule", "bbs_schedule", "notes",
              "gridline", "soil_boring_log"}
ARCH = {"plan_architectural", "roof_plan", "site_plan", "side_profile", "notes"}
DISCIPLINE = {"structural": STRUCTURAL, "architecture": ARCH, "electrical": {"plan_electrical"}, "sanitary": {"plan_sanitary"}}
_PREFIX = (("SN", "sanitary"), ("SA", "sanitary"), ("ส", "structural"), ("S", "structural"), ("A", "architecture"), ("E", "electrical"),
           ("P", "sanitary"))

# ชื่อ (ไทย) -> subtask ย่อจากตาราง "Title-block wording to subtask" ใน pass0/prompt.md ของ t07 · (regex, ชุด subtask)
# ลำดับสำคัญ: เจาะจงก่อนหยาบ; ตัวที่ขึ้นกับระบบ (แปลนพื้น/ผังโครงสร้าง) แยกต่างหากด้านล่าง
_TITLE = [
    (r"สารบัญ", {"index"}),
    (r"ผังบริเวณ", {"site_plan"}),
    (r"ฐานราก|เสาเข็ม", {"plan_footing", "plan_column"}),
    (r"โครงหลังคา|โครงสร้างหลังคา", {"plan_beam"}),
    (r"สุขาภิบาล|ประปา|ท่อระบาย|ระบายน้ำ|บำบัด", {"plan_sanitary"}),
    (r"ไฟฟ้า|เต้ารับ|แผงเมน|แสงสว่าง", {"plan_electrical"}),
    (r"รูปด้าน", {"side_profile"}),
    (r"รูปตัด", {"section", "side_profile"}),
    (r"แบบขยาย|ห้องน้ำ|บันได|ประตู|หน้าต่าง|รั้ว|เชิงชาย|ราวกันตก", {"plan_architectural"}),
    (r"รายการประกอบแบบ|หมายเหตุ|ข้อกำหนด", {"notes"}),
    (r"รายการวัสดุ|ปริมาณ|ประมาณราคา|ปร\.?\s*4|BOQ", {"material_list"}),
    (r"ตารางเหล็ก|ตารางดัด|bbs", {"bbs_schedule"}),
    (r"ตารางคาน|ตารางเสา|ตารางพื้น|ตารางสรุป", {"schedule"}),
    (r"เจาะสำรวจ|สำรวจดิน|boring", {"soil_boring_log"}),
    (r"กริด|แนวเสา", {"gridline"}),
    (r"ปก|หน้าปก", {"title"}),
]
_DISC_WORD = [(r"โครงสร้าง|วิศวกรรม", "structural"), (r"สถาปัตย", "architecture"), (r"ไฟฟ้า", "electrical"), (r"สุขาภิบาล|ประปา", "sanitary")]
_CODE = re.compile(r"(?<![A-Za-zก-ฮ])([A-Za-zก-ฮ]{1,3})\s*[-–]?\s*(\d{1,3})(?!\d)")   # ขีดไม่บังคับ: titleblock_extract.norm_code คืน 'A01' ไม่มีขีด


def sheet_list_tail(entries):
    """entries = [{title, sheet_range?}] -> หางข้อความตามฟอร์แมต t07 (ไม่มี title = ตัดทิ้ง; ว่าง = '' ไม่ส่งหาง)"""
    ents = [{"title": e["title"], "sheet_range": e.get("sheet_range")} for e in entries if e.get("title")]
    return SHEET_MARK + json.dumps(ents, ensure_ascii=False) if ents else ""


def norm(code):
    m = _CODE.search(str(code or ""))
    return f"{m.group(1).upper()}-{int(m.group(2)):02d}" if m else None


def expand_range(rng):
    """'S-01 ถึง S-08' -> [S-01..S-08] · 'A-04' -> [A-04] · None/ไม่มีรหัส -> [] · รหัสสองตัวคนละชุดอักษร = ลิสต์รหัสที่เจอ (ไม่ถมช่วง)"""
    found = _CODE.findall(str(rng or ""))
    if len(found) == 2 and found[0][0].upper() == found[1][0].upper() and int(found[0][1]) <= int(found[1][1]):
        a, b = int(found[0][1]), int(found[1][1])
        return [f"{found[0][0].upper()}-{n:02d}" for n in range(a, min(b, a + 199) + 1)]
    return [f"{p.upper()}-{int(n):02d}" for p, n in found]


def discipline_of(code):
    code = str(code or "").upper()
    for pre, d in _PREFIX:
        if code.startswith(pre):
            return d
    return None


def entry_types(title, code=None):
    """รายการสารบัญหนึ่งแถว (+รหัสแผ่นของหน้านั้น) -> ชุด subtask ที่สารบัญบอก (ว่าง = สารบัญบอกไม่ได้)
    ชื่อทั่วไปที่ขึ้นกับระบบ: 'แปลนพื้นชั้น N / ผังโครงสร้าง' = โครงสร้าง -> plan_beam/plan_slab · สถาปัตย์ -> plan_architectural(+roof_plan ถ้ามีหลังคา)"""
    t = str(title or "")
    disc = discipline_of(code)
    if re.search(r"แปลนพื้น|ผังโครงสร้าง|ผังพื้น|แปลนชั้น", t):
        if disc == "structural" or re.search(r"โครงสร้าง", t):
            return {"plan_beam", "plan_slab"}
        if disc == "architecture":
            return {"plan_architectural", "roof_plan"} if "หลังคา" in t else {"plan_architectural"}
        return {"plan_beam", "plan_slab", "plan_architectural"}          # ไม่รู้ระบบ: ทุกทางที่เป็นไปได้ (กว้าง = ไม่เตือนพร่ำเพรื่อ)
    if re.fullmatch(r"\s*แปลนหลังคา\s*", t):
        return {"roof_plan"}
    if "รูปตัด" in t and disc in ("architecture", "structural"):          # t07: รูปตัดมีเหล็ก = section · ไม่มีเหล็ก = side_profile
        return {"side_profile"} if disc == "architecture" else {"section"}
    out = set()
    for rx, types in _TITLE:
        if re.search(rx, t, re.I):
            out |= types
    if out:
        return out
    for rx, d in _DISC_WORD:                                              # ชื่อหยาบ: 'แบบวิศวกรรมโครงสร้าง S-01 ถึง S-14'
        if re.search(rx, t):
            return set(DISCIPLINE[d])
    return set(DISCIPLINE.get(disc, ()))


def toc_types_by_page(entries, page_codes):
    """entries = [{title, sheet_range}] · page_codes = {pdf_page: sheet_code} -> {pdf_page: set(subtask)} ของหน้าที่สารบัญมีแถวให้
    หลายแถวใช้รหัสเดียวกัน (สารบัญรวม + สารบัญย่อย) เอาแถวที่ได้ชุดเล็กที่สุด (เจาะจงสุด) ถ้าเท่ากันรวมกัน"""
    by_code = {}
    for e in entries:
        for c in expand_range(e.get("sheet_range")):
            ts = entry_types(e.get("title"), c)
            if ts:
                by_code.setdefault(c, []).append(ts)
    out = {}
    for page, code in page_codes.items():
        cands = by_code.get(norm(code))
        if cands:
            small = min(len(x) for x in cands)
            out[page] = set().union(*(x for x in cands if len(x) == small))
    return out


def reconcile(toc, t07):
    """toc / t07 = ชุด subtask หรือ None -> dict(status, types[], warning|note) — กติกาอยู่ที่ docstring ด้านบน"""
    toc, t07 = set(toc or ()), set(t07 or ())
    if toc and t07:
        common = toc & t07
        if common:
            return dict(status="agree", types=sorted(common))
        return dict(status="mismatch", types=sorted(toc | t07), warning="toc_vs_t07_mismatch")
    if toc:
        return dict(status="toc_only", types=sorted(toc), warning="t07_unavailable")
    if t07:
        return dict(status="t07_only", types=sorted(t07), note="toc_has_no_row")
    return dict(status="none", types=[], warning="no_source")


def reconcile_book(page_codes, toc_entries, t07_by_page):
    """ทั้งเล่ม: page_codes {page: code} · toc_entries [{title, sheet_range}] หรือ None (ไม่มีหน้าสารบัญ) · t07_by_page {page: [subtask..]|None}"""
    toc = toc_types_by_page(toc_entries, page_codes) if toc_entries else {}
    pages = sorted(set(page_codes) | set(t07_by_page or {}))
    rows, count = [], {}
    for p in pages:
        r = reconcile(toc.get(p), (t07_by_page or {}).get(p))
        if not toc_entries and r["status"] == "t07_only":
            r["note"] = "no_index_page"
        rows.append(dict(pdf_page=p, **r))
        count[r["status"]] = count.get(r["status"], 0) + 1
    return dict(pages=rows, summary=count, warnings=sum(1 for r in rows if r.get("warning")))


def demo():
    # หางตามฟอร์แมต t07 (ตัวอย่างจริงในเอกสาร SHEET_LIST_format.md)
    tail = sheet_list_tail([{"title": "แบบสถาปัตยกรรม", "sheet_range": "A-01 ถึง A-20"}, {"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-14"}])
    assert tail == ("\n\nSHEET LIST (from this drawing set's index page)\n"
                    '[{"title": "แบบสถาปัตยกรรม", "sheet_range": "A-01 ถึง A-20"}, {"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-14"}]'), tail
    assert sheet_list_tail([]) == "" and sheet_list_tail([{"title": "", "sheet_range": "A-01"}, {"title": None}]) == ""   # ไม่มีรายการ = ไม่มีหาง
    assert '"sheet_range": null' in sheet_list_tail([{"title": "รายการประกอบแบบ"}])                                   # ไม่มีช่วง = null ไม่ใช่เลขหน้า
    # ช่วงรหัส
    assert expand_range("S-01 ถึง S-04") == ["S-01", "S-02", "S-03", "S-04"] and expand_range("A-04") == ["A-04"]
    assert expand_range(None) == [] and expand_range("ไม่มีรหัส") == [] and expand_range("S-08 ถึง S-01") == ["S-08", "S-01"]
    assert expand_range("A-01 ถึง S-03") == ["A-01", "S-03"]                                                         # คนละชุดอักษร ไม่ถมช่วง
    # รหัสหน้าจริงจาก titleblock_extract.norm_code ไม่มีขีด ('A01') ต้องจับคู่กับสารบัญที่พิมพ์ 'A-01' ได้ (ข้อมูลจริง 1ชั้น_01 จับบั๊กนี้)
    assert norm("A01") == "A-01" and norm("A-1") == "A-01" and norm("a-04") == "A-04" and norm("S12") == "S-12" and norm("WC.1") is None
    assert expand_range("S01 ถึง S03") == ["S-01", "S-02", "S-03"]
    assert toc_types_by_page([{"title": "รูปด้าน 1", "sheet_range": "A-05"}], {7: "A05"}) == {7: {"side_profile"}}
    # ประเภทจากชื่อ (ตัวอย่างจริงของ 1ชั้น_01)
    assert entry_types("แปลนพื้นชั้น 1, แปลนหลังคา", "A-04") == {"plan_architectural", "roof_plan"}
    assert entry_types("แปลนพื้นชั้น 1", "S-05") == {"plan_beam", "plan_slab"}                                         # ชื่อเดียวกันคนละระบบ ต่างประเภท
    assert entry_types("รูปด้าน 1, รูปด้าน 2", "A-05") == {"side_profile"}
    assert entry_types("รูปตัด 1, รูปตัด 2", "A-07") == {"side_profile"} and entry_types("รูปตัด", "S-06") == {"section"}   # สถาปัตย์ไม่มีเหล็ก
    assert entry_types("รูปตัด", None) == {"section", "side_profile"}                                                  # ไม่รู้ระบบ: ทั้งสองทาง
    assert entry_types("แบบขยายห้องน้ำ WC.1", "A-10") == {"plan_architectural"}
    assert entry_types("แปลนหลังคา", "A-04") == {"roof_plan"} and entry_types("แปลนโครงหลังคา", "S-08") == {"plan_beam"}
    assert entry_types("รายการประกอบแบบ", "A-02") == {"notes"} and entry_types("ผังบริเวณ", "A-03") == {"site_plan"}
    assert entry_types("แบบวิศวกรรมโครงสร้าง", "S-01") == STRUCTURAL                                                   # หยาบ = ทั้งระบบ
    assert entry_types("อะไรสักอย่าง", None) == set() and entry_types("อะไรสักอย่าง", "S-09") == STRUCTURAL         # ชื่อไม่รู้จัก: ใช้ระบบจากรหัส; ไม่มีรหัสด้วย = บอกไม่ได้
    # จับคู่หน้า: หลายแถวรหัสเดียว -> เจาะจงสุด
    ents = [{"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-04"}, {"title": "แปลนฐานราก", "sheet_range": "S-02"}]
    m = toc_types_by_page(ents, {10: "S-02", 11: "S-03", 12: "A-01", 13: None})
    assert m[10] == {"plan_footing", "plan_column"} and m[11] == STRUCTURAL and 12 not in m and 13 not in m, m
    # reconcile: 5 สถานะ
    assert reconcile({"plan_beam", "plan_slab"}, {"plan_beam"}) == dict(status="agree", types=["plan_beam"])           # หยาบ+เจาะจง = เจาะจง (ไม่บาน)
    r = reconcile({"plan_footing"}, {"plan_beam"})
    assert r["status"] == "mismatch" and r["types"] == ["plan_beam", "plan_footing"] and r["warning"] == "toc_vs_t07_mismatch"   # UNION + เตือน
    assert reconcile({"notes"}, None) == dict(status="toc_only", types=["notes"], warning="t07_unavailable")           # fail-safe: t07 ล้ม
    assert reconcile(None, {"section"}) == dict(status="t07_only", types=["section"], note="toc_has_no_row")
    assert reconcile(None, None) == dict(status="none", types=[], warning="no_source") and reconcile(set(), []) ["status"] == "none"
    # ทั้งเล่ม: ไม่มีหน้าสารบัญเลย = ใช้ t07 อย่างเดียวพร้อมหมายเหตุ; t07 ล้มทั้งเล่ม = สารบัญอย่างเดียวพร้อมเตือนทุกหน้าที่มีแถว
    b = reconcile_book({3: "A-04", 4: "S-02"}, None, {3: ["plan_architectural"], 4: ["plan_footing"]})
    assert b["summary"] == {"t07_only": 2} and all(r["note"] == "no_index_page" for r in b["pages"]) and b["warnings"] == 0
    b = reconcile_book({3: "A-04", 4: "S-02"}, [{"title": "แปลนฐานราก", "sheet_range": "S-02"}], None)
    assert b["summary"] == {"none": 1, "toc_only": 1} and b["warnings"] == 2
    b = reconcile_book({3: "A-04", 4: "S-02"}, [{"title": "แปลนฐานราก", "sheet_range": "S-02"}], {3: ["plan_architectural"], 4: ["plan_beam"]})
    assert b["summary"] == {"t07_only": 1, "mismatch": 1} and b["warnings"] == 1 and [r for r in b["pages"] if r["pdf_page"] == 4][0]["types"] == ["plan_beam", "plan_column", "plan_footing"]
    print("OK — self-check ผ่าน (ตรรกะฟอร์แมตหาง/ช่วงรหัส/ประเภทจากชื่อ/จับคู่หน้า/5 สถานะ เท่านั้น ยังไม่ได้ทดสอบกับหน้าสารบัญจริงหรือผลของ t07 จริง)")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print(__doc__)
