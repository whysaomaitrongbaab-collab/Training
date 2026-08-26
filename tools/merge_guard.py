#!/usr/bin/env python3
"""merge_guard.py — ด่านโค้ดของ pass 3 (ถอดระยะ): บังคับกฎ "ห้ามลบ element ที่ pass 2.5 เจอ"

pass_design_v2.md เฟส E ข้อ 13: กฎนี้ต้องบังคับด้วยโค้ด ไม่ใช่ prompt — โมเดลเชื่อไม่ได้
ในเรื่องนี้ (มันลบเงียบๆ ได้เสมอ) โค้ดตรวจได้เพราะ element ของ CV มีเลขกำกับ #n และ
prompt 2.4/3 สั่งให้โมเดลใส่ "cv_mark": n ทุกตัวที่จับคู่กรอบได้

กติกา:
  - เลข n ไหนใน CV ที่ไม่มีโมเดลตัวไหน claim → ใส่กลับเป็น stub: element_type จาก class,
    ฟิลด์ตัวเลข null ทั้งหมด, ธง dropped_by_pass3 — คนมาดูทีหลังว่าโมเดลข้ามเพราะอะไร
  - โมเดลเพิ่ม element ที่ CV ไม่เห็นได้เสมอ (ไม่มี cv_mark = ผ่านเฉยๆ)
  - สอง element claim เลขเดียวกัน → เก็บทั้งคู่ + warning (อย่าเลือกแทนคน)
  - cv_mark ที่ไม่มีจริงในบัญชี CV → warning (โมเดลแต่งเลข)

ใช้:  from merge_guard import merge_no_delete
      merged, warnings = merge_no_delete(scan["elements"], model_answer["elements"])
self-check:  python tools/merge_guard.py
"""

CLASS_TO_TYPE = {"footing": "footing", "column": "column", "beam_h": "beam", "beam_v": "beam"}


def cv_stub(cv_el):
    """สร้าง element ตัวแทนของกรอบ CV ที่โมเดลทำหาย — ทุกอย่างที่ CV ไม่รู้จริงเป็น null"""
    return {
        "element_id": "cv#%d" % cv_el["n"],
        "element_type": CLASS_TO_TYPE.get(cv_el["class"], "symbol"),
        "cv_mark": cv_el["n"],
        "confidence_score": None,
        "confidence_flags": ["dropped_by_pass3", "from_cv_only"],
        "grid_refs": None,
    }


def merge_no_delete(cv_elements, model_elements):
    """(บัญชี CV จาก pass 2.5, elements ที่โมเดลตอบใน pass 3) → (merged, warnings)

    merged = ของโมเดลทุกตัว (ห้ามแก้) + stub ของกรอบ CV ที่ไม่มีใคร claim
    ห้ามลบของโมเดลเช่นกัน — ด่านนี้เพิ่มได้อย่างเดียว ทั้งสองทิศ"""
    warnings = []
    valid_n = {e["n"] for e in cv_elements}
    claimed = {}
    for el in model_elements:
        m = el.get("cv_mark")
        if m is None:
            continue
        if m not in valid_n:
            warnings.append("โมเดลอ้าง cv_mark %r ที่ไม่มีในบัญชี CV — เลขแต่งเอง?" % (m,))
            continue
        if m in claimed:
            warnings.append("cv_mark %d ถูก claim ซ้ำโดย %r และ %r — เก็บทั้งคู่ ให้คนตัดสิน"
                            % (m, claimed[m], el.get("element_id")))
        else:
            claimed[m] = el.get("element_id")

    merged = list(model_elements)
    for cv_el in cv_elements:
        if cv_el["n"] not in claimed:
            merged.append(cv_stub(cv_el))
            warnings.append("กรอบ #%d (%s) โมเดลไม่ตอบ — ใส่ stub กลับ (dropped_by_pass3)"
                            % (cv_el["n"], cv_el["class"]))
    return merged, warnings


def _selfcheck():
    cv = [{"n": 1, "class": "column", "cx": 10, "cy": 10, "w": 40, "h": 40},
          {"n": 2, "class": "footing", "cx": 10, "cy": 90, "w": 60, "h": 60},
          {"n": 3, "class": "beam_h", "cx": 200, "cy": 50, "w": 300, "h": 20}]

    # โมเดล claim #1, ข้าม #2/#3, เพิ่มของตัวเอง 1 ตัว
    model = [{"element_id": "C1", "element_type": "column", "cv_mark": 1},
             {"element_id": "B9", "element_type": "beam"}]
    merged, warns = merge_no_delete(cv, model)
    ids = [e["element_id"] for e in merged]
    assert ids[:2] == ["C1", "B9"], "ของโมเดลต้องอยู่ครบ ลำดับเดิม"
    assert "cv#2" in ids and "cv#3" in ids, "กรอบที่หายต้องกลับมาเป็น stub"
    stubs = [e for e in merged if "dropped_by_pass3" in e.get("confidence_flags", [])]
    assert len(stubs) == 2 and all(e["confidence_score"] is None for e in stubs)
    assert stubs[1]["element_type"] == "beam", "beam_h ต้อง map เป็น beam"
    assert len(warns) == 2

    # claim ครบ → ไม่มี stub ไม่มี warning
    model_full = [{"element_id": "C1", "cv_mark": 1}, {"element_id": "F1", "cv_mark": 2},
                  {"element_id": "B1", "cv_mark": 3}]
    merged, warns = merge_no_delete(cv, model_full)
    assert len(merged) == 3 and not warns

    # เลขแต่งเอง + claim ซ้ำ → warning ทั้งคู่ ไม่มีอะไรถูกลบ
    model_bad = [{"element_id": "X", "cv_mark": 99}, {"element_id": "A", "cv_mark": 1},
                 {"element_id": "B", "cv_mark": 1}]
    merged, warns = merge_no_delete(cv, model_bad)
    assert len(merged) == 3 + 2  # ของโมเดล 3 + stub #2,#3
    assert any("แต่งเอง" in w for w in warns) and any("ซ้ำ" in w for w in warns)

    # โมเดลตอบว่างทั้งหมด → CV กลับมาครบทุกตัว
    merged, warns = merge_no_delete(cv, [])
    assert len(merged) == 3 and all("dropped_by_pass3" in e["confidence_flags"] for e in merged)
    print("OK — merge_guard self-check ผ่านทุกข้อ")


if __name__ == "__main__":
    _selfcheck()
