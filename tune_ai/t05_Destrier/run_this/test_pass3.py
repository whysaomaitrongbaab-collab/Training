#!/usr/bin/env python3
"""Tests for pass3_measure.py — run: python test_pass3.py   (stdlib only, no network, no GPU)

ทุกเทสต์รันแยกกัน แล้วพิมพ์ PASS/FAIL รายข้อ (ล้มข้อเดียวไม่บังข้ออื่น) · exit 1 ถ้ามีข้อไหนล้ม

แหล่งข้อมูล:
  - ../../tests/fixtures/grid-ref-vectors.json — สัญญา grid ref ร่วมกับฝั่ง JS (ห้ามแก้ไฟล์นั้น)
  - test_fixtures/real_*.json — หน้า pass2 จริงจากงาน production (คัดมาเฉพาะ JSON ที่ต้องใช้)
  - เคสสังเคราะห์ในไฟล์นี้ (พอร์ตจาก repro_minimal.py ของทีมตรวจ แต่กลับ assert เป็นพฤติกรรมที่ต้องการ)
"""
import copy
import json
import math
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pass3_measure as p3  # noqa: E402

FIX = HERE / "test_fixtures"
# สัญญาอยู่ที่ repo (tests/fixtures) — โฟลเดอร์ worker ถูกก๊อปไปรันเดี่ยวๆ ได้ (Training run_this) จึงมีสำเนา
# ใน test_fixtures ด้วย · vectors_copy_in_sync ด้านล่างกันสองไฟล์แยกทางกัน
REPO_VECTORS = HERE.parents[1] / "tests" / "fixtures" / "grid-ref-vectors.json"
LOCAL_VECTORS = FIX / "grid-ref-vectors.json"
VECTORS = json.loads((REPO_VECTORS if REPO_VECTORS.exists() else LOCAL_VECTORS).read_text(encoding="utf-8"))


def real(name):
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def G(xs, ys):
    return {"x_lines": [{"id": i, "type": "named", "pos_m": p} for i, p in xs],
            "y_lines": [{"id": i, "type": "named", "pos_m": p} for i, p in ys]}


def nodes(grid):
    """ทุกจุดตัดของเส้น named: (ref ตัวอักษรนำ, mx, my) — ใช้กับกริดมาตรฐาน (เลข=x, อักษร=y)"""
    return [(ly["id"] + lx["id"], lx["pos_m"], ly["pos_m"])
            for ly in grid["y_lines"] for lx in grid["x_lines"]]


def cv_from(points, to_px, cls="footing"):
    """cv_scan-like numbering: rows top->bottom, left->right"""
    pts = sorted(((to_px(mx, my), ref) for ref, mx, my in points),
                 key=lambda t: (round(t[0][1]), t[0][0]))
    return [{"n": k, "class": cls, "cx": int(round(px)), "cy": int(round(py)), "w": 24, "h": 24}
            for k, ((px, py), _) in enumerate(pts, 1)]


def worst_error(rep, to_px, grid):
    """คลาดสูงสุด (เมตร) ของตัวแปลงที่ยอมรับ ณ ทุกจุดตัดกริด เทียบความจริงที่สร้างภาพไว้"""
    t = rep["transform"]
    out = 0.0
    for _, mx, my in nodes(grid):
        ex, ey = p3.pixel_to_metre(t, *to_px(mx, my))
        out = max(out, math.hypot(ex - mx, ey - my))
    return out


TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


# ── D2 grid-ref grammar: one shared contract with the JS adapter ─────────────────────
@test
def vectors_parse():
    bad = []
    for case in VECTORS["parse"]:
        got = p3.parse_grid_ref(case["ref"])
        if got != case["expect"]:
            bad.append((case["ref"], case["expect"], got))
    assert not bad, f"{len(bad)}/{len(VECTORS['parse'])} parse vectors ผิด: {bad}"


@test
def vectors_resolve():
    bad = []
    for case in VECTORS["resolve"]:
        got = p3.ref_to_metre(VECTORS["grids"][case["grid"]], case["ref"])
        got = list(got) if got is not None else None
        exp = case["expect"]
        if (got is None) != (exp is None) or (got and any(abs(a - b) > 1e-9 for a, b in zip(got, exp))):
            bad.append((case["grid"], case["ref"], exp, got))
    assert not bad, f"{len(bad)}/{len(VECTORS['resolve'])} resolve vectors ผิด: {bad}"


def _all_intersections(grid):
    for lx in grid.get("x_lines") or []:
        for ly in grid.get("y_lines") or []:
            if isinstance(lx.get("pos_m"), (int, float)) and isinstance(ly.get("pos_m"), (int, float)):
                yield lx, ly


@test
def nearest_grid_ref_never_emits_ambiguous_id():
    grids = dict(VECTORS["grids"])
    grids["dup"] = G([("1", 0), ("2", 3.2)], [("จ", 0.0), ("จ", 4.0), ("ง", 6.0)])   # cbb90abe-style
    for gname, grid in grids.items():
        for lx, ly in _all_intersections(grid):
            ref, _ = p3.nearest_grid_ref(grid, lx["pos_m"], ly["pos_m"])
            if ref is None:
                continue
            back = p3.ref_to_metre(grid, ref)
            assert back is not None and abs(back[0] - lx["pos_m"]) < 1e-9 and \
                abs(back[1] - ly["pos_m"]) < 1e-9, \
                f"{gname}: snap ({lx['pos_m']},{ly['pos_m']}) -> {ref!r} -> {back} (ต้องกลับมาจุดเดิม)"
    # จุดบนเส้นที่ชื่อซ้ำ / id ที่อยู่ทั้งสองแกน ต้องไม่ได้ ref เลย
    assert p3.nearest_grid_ref(grids["dup"], 3.2, 4.0)[0] is None, "เส้น จ ซ้ำสองเส้น ห้าม snap เป็น จ2"
    assert p3.nearest_grid_ref(grids["mixed"], 0.0, 0.0)[0] is None, "'1' อยู่ทั้งสองแกน ห้าม emit"
    assert p3.nearest_grid_ref(grids["swapped"], 5.0, 3.5)[0] == "B2"
    assert p3.nearest_grid_ref(grids["thai"], 12.0, 1.5)[0] == "ข3"


# ── D3 report-only: pass3 never touches the pass2 doc ────────────────────────────────
# ระยะกริดไม่สมมาตรพอที่ทิศกลับด้านทั้ง 3 แบบคลาด > 1 ม. (หาด้วย fix_worker/find_test_grid.py) —
# ผังสมมาตร/ระยะเท่า ทิศแกนกำกวมจริง (D4 ต้องปฏิเสธ) จึงใช้เป็นหน้าที่ "ต้องวัดได้" ไม่ได้
STD = G([("1", 0.0), ("2", 4.5), ("3", 9.0), ("4", 10.5)], [("A", 0.0), ("B", 5.0), ("C", 8.5), ("D", 11.5)])
TO_PX = lambda mx, my: (140 + 60 * mx, 90 + 60 * my)     # origin top-left (as the prompt requires)


def _std_page(extra_cv=()):
    pts = nodes(STD)
    doc = {"pattern": "footing_plan", "warnings": ["model warning"], "elements": [
        {"element_id": "F1", "element_type": "footing", "count": len(pts),
         "grid_refs": [r for r, _, _ in pts], "span_length_m": None, "confidence_flags": []},
        {"element_id": "F9", "element_type": "footing", "count": 1, "grid_refs": [],
         "span_length_m": None}]}
    return doc, {"elements": cv_from(pts, TO_PX) + list(extra_cv), "self_harvest_points": []}


@test
def measure_page_is_report_only():
    doc, cv = _std_page(extra_cv=[{"n": 99, "class": "footing", "cx": 140 + 60 * 5, "cy": 90 + 60 * 3,
                                   "w": 24, "h": 24}])
    cases = [(doc, STD, cv)]
    for name in ("real_267d1989_p08", "real_cbb90abe_p01", "real_83b8e52c_p19", "real_83b8e52c_p23"):
        fx = real(name)
        cases.append((fx["doc"], fx["grid"], fx["cv_scan"]))
    for d, g, c in cases:
        before = copy.deepcopy((d, g, c))
        p3.measure_page(d, g, c, "plan_footing")
        assert (d, g, c) == before, "measure_page แก้ doc/grid/cv_scan ที่รับมา (D3: ต้องรายงานอย่างเดียว)"
    rep = p3.measure_page(doc, STD, cv, "plan_footing")
    assert rep["ok"], rep["reason"]
    assert "cv_measure" not in json.dumps(doc), "ห้ามเขียน cv_measure ลง element"


@test
def merge_into_pass2_is_gone():
    assert not hasattr(p3, "merge_into_pass2"), "D3: ตัวเติมผลกลับเข้า pass2 ต้องถูกถอดออก"
    src = (HERE / "worker.py").read_text(encoding="utf-8")
    assert "merge_into_pass2" not in src, "worker.py ยังเรียก merge_into_pass2"


@test
def cv_only_points_reported_not_added():
    far = {"n": 99, "class": "footing", "cx": 140 + 60 * 5, "cy": 90 + 60 * 3, "w": 24, "h": 24}
    doc, cv = _std_page(extra_cv=[far])
    n_before = len(doc["elements"])
    rep = p3.measure_page(doc, STD, cv, "plan_footing")
    assert rep["ok"], rep["reason"]
    assert len(doc["elements"]) == n_before
    assert rep["cv_only_count"] == len(rep["cv_only"]) >= 1, rep
    assert any(abs(c["pos_m"][0] - 5) < 0.05 and abs(c["pos_m"][1] - 3) < 0.05 for c in rep["cv_only"])


# ── D4 orientation hypotheses ────────────────────────────────────────────────────────
@test
def symmetric_grid_flipped_y_is_refused_ambiguous():
    # repro_minimal case 1: A (pos 0) printed at the BOTTOM of a symmetric grid — old code accepted
    # the mirror image with residual 0 and wrote C1 for a true A1
    grid = G([("1", 0), ("2", 4), ("3", 8)], [("A", 0), ("B", 4), ("C", 8)])
    to_px = lambda mx, my: (100 + 50 * mx, 900 - 50 * my)
    doc = {"elements": [{"element_id": "F1", "element_type": "footing", "count": 9,
                         "grid_refs": [r for r, _, _ in nodes(grid)]}]}
    rep = p3.measure_page(doc, grid, {"elements": cv_from(nodes(grid), to_px)}, "plan_footing")
    assert not rep["ok"], f"ผังสมมาตรที่กลับด้าน ต้องไม่ถูกยอมรับ (ได้ {rep['transform']})"
    assert rep["reason_code"] == "orientation_ambiguous", rep
    assert "ทิศแกนกำกวม" in rep["reason"], rep["reason"]


ASYM = G([("1", 0.0), ("2", 4.5), ("3", 9.0), ("4", 10.5)], [("ก", 0.0), ("ข", 5.0), ("ค", 8.5), ("ง", 11.5)])


@test
def asymmetric_bottom_origin_is_accepted_flipped_with_issue():
    to_px = lambda mx, my: (150 + 80 * mx, 1400 - 80 * my)          # ก (pos 0) at the bottom
    doc = {"elements": [{"element_id": "F1", "element_type": "footing", "count": 16,
                         "grid_refs": [r for r, _, _ in nodes(ASYM)]}]}
    rep = p3.measure_page(doc, ASYM, {"elements": cv_from(nodes(ASYM), to_px)}, "plan_footing")
    assert rep["ok"], rep["reason"]
    assert rep["orientation"] == "flipped_y", rep["orientation"]
    assert rep["transform"]["ay"] < 0 < rep["transform"]["ax"]
    assert worst_error(rep, to_px, ASYM) < 0.05
    v = p3.grid_validation(ASYM, {"page_19_plan_footing": rep})
    iss = [i for i in v["issues"] if i["code"] == "origin_not_top_left"]
    assert iss and iss[0]["axis"] == "y", v


@test
def asymmetric_mirror_survivor_is_never_a_wrong_accept():
    # repro_minimal case 2: old code accepted a mirrored fit (worst error > 10 m) via survivor bias
    grid = G([("1", 0), ("2", 4.15), ("3", 10.7), ("4", 16.75), ("5", 23.55), ("6", 27.0)],
             [("F", 0), ("E", 6.4), ("D", 9.1), ("C", 11.35), ("B", 13.6), ("A", 15.6)])
    to_px = lambda mx, my: (200 + 60 * mx, 1200 - 60 * my)
    doc = {"elements": [{"element_id": "F1", "element_type": "footing", "count": 36,
                         "grid_refs": [r for r, _, _ in nodes(grid)]}]}
    rep = p3.measure_page(doc, grid, {"elements": cv_from(nodes(grid), to_px)}, "plan_footing")
    if rep["ok"]:
        assert worst_error(rep, to_px, grid) < 0.1, "ยอมรับแต่ผิด = ห้ามเด็ดขาด"


@test
def unflipped_asymmetric_page_still_accepted_identity():
    doc = {"elements": [{"element_id": "F1", "element_type": "footing", "count": 16,
                         "grid_refs": [r for r, _, _ in nodes(ASYM)]}]}
    to_px = lambda mx, my: (150 + 80 * mx, 90 + 80 * my)
    rep = p3.measure_page(doc, ASYM, {"elements": cv_from(nodes(ASYM), to_px)}, "plan_footing")
    assert rep["ok"] and rep["orientation"] == "identity", rep
    assert abs(rep["transform"]["px_per_m_x"] - 80) < 0.5 and abs(rep["transform"]["px_per_m_y"] - 80) < 0.5
    assert worst_error(rep, to_px, ASYM) < 0.05
    assert not [i for i in p3.grid_validation(ASYM, {"p": rep})["issues"]
                if i["code"] == "origin_not_top_left"]


@test
def noisy_pages_never_accept_a_mirror_or_wrong_scale():
    # หน้า fuzz ที่มี noise จริงจัง (CV พลาด/FP นอกผัง/ref ผิด/โมเดลตอบไม่ครบ): "ทิศเดียวที่ผ่านด่าน"
    # เคยเป็นกระจก (ผิด 3.9–24.5 ม.) หรือ px/m ผิด 2.8 เท่า — ต้องปฏิเสธ หรือถ้ายอมรับต้องถูก
    cases = json.loads((FIX / "fuzz_mirror_noise.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 5
    for c in cases:
        rep = p3.measure_page(c["doc"], c["grid"], c["cv_scan"], "plan_footing")
        if not rep["ok"]:
            assert rep["reason_code"] in ("orientation_ambiguous", "weak_support", "residual",
                                          "too_few_anchors", "anisotropy"), rep["reason_code"]
            continue
        tp = c["truth_px"]
        to_px = lambda mx, my: (tp["bx"] + tp["ax"] * mx, tp["by"] + tp["ay"] * my)
        named = G([(l["id"], l["pos_m"]) for l in c["grid"]["x_lines"] if l["type"] == "named"],
                  [(l["id"], l["pos_m"]) for l in c["grid"]["y_lines"] if l["type"] == "named"])
        assert worst_error(rep, to_px, named) < 0.5, f"seed {c['seed']}: ยอมรับแต่ผิด ({rep['orientation']})"


# ── per-class aspect gate: one degenerate CV class must not poison the fit ─────────────
@test
def degenerate_class_is_skipped_not_pooled():
    # repro_minimal case 9 on an asymmetric grid (so orientation is unique): 12 columns found,
    # footings found only on one row (y-spread 2 px) -> old code pooled them -> residual reject
    grid = ASYM
    to_px = lambda mx, my: (2145 + 103 * mx, 624 + 102 * my)
    pts = nodes(grid)
    cols = cv_from(pts, to_px, "column")
    foot = [{"n": 90, "class": "footing", "cx": int(to_px(0, 5.0)[0]), "cy": int(to_px(0, 5.0)[1]) + 1,
             "w": 48, "h": 48},
            {"n": 91, "class": "footing", "cx": int(to_px(4.5, 5.0)[0]), "cy": int(to_px(4.5, 5.0)[1]) - 1,
             "w": 48, "h": 48}]
    doc = {"elements": [
        {"element_id": "F1", "element_type": "footing", "count": 16, "grid_refs": [r for r, _, _ in pts]},
        {"element_id": "C1", "element_type": "column", "count": 16, "grid_refs": [r for r, _, _ in pts]}]}
    rep = p3.measure_page(doc, grid, {"elements": cols + foot}, "plan_footing")
    assert rep["ok"], rep["reason"]
    assert [c["class"] for c in rep["classes_skipped"]] == ["footing"], rep["classes_skipped"]
    assert worst_error(rep, to_px, grid) < 0.05


@test
def real_267d1989_p08():
    fx = real("real_267d1989_p08")
    rep = p3.measure_page(fx["doc"], fx["grid"], fx["cv_scan"], "plan_footing")
    # cv_mark 1..7 = ลำดับรายการ (ไม่ได้ชี้กล่อง CV จริง) -> ต้องไม่ถูกใช้เป็นหมุด
    assert rep["anchor_source"] == "shape_match", rep["anchor_source"]
    # คลาส footing (CV เจอ 2 ตัวบนแถวเดียว สูงต่างกัน 2 px) ต้องถูกข้าม ไม่ถูกยืดเป็น [0,1]
    assert [c["class"] for c in rep["classes_skipped"]] == ["footing"], rep["classes_skipped"]
    ident = next(c for c in rep["candidates"] if c["orientation"] == "identity")
    assert ident["ok"], ident
    assert abs(ident["px_per_m_x"] - 103.6) < 0.3 and abs(ident["px_per_m_y"] - 102.3) < 0.3, ident
    assert ident["residual_max_m"] < 0.04 and ident["n_anchors"] == 5, ident
    # ผังนี้มี x 2 เส้น และ y ระยะเท่ากัน (3.925/3.925) -> ทั้ง 4 ทิศ fit ได้ดีเท่ากัน ตัดสินทิศไม่ได้
    # จากตำแหน่งอย่างเดียว -> D4: ต้องปฏิเสธ ไม่เดาทิศ (ยอมเสียหน้านี้ ดีกว่ายอมรับผิด)
    assert not rep["ok"] and rep["reason_code"] == "orientation_ambiguous", rep


# ── M3 cv_mark = record order -> distrusted ──────────────────────────────────────────
@test
def enumerated_cv_marks_are_detected():
    for name in ("real_267d1989_p08", "real_cbb90abe_p01", "real_83b8e52c_p19", "real_83b8e52c_p23"):
        assert p3.marks_look_enumerated(real(name)["doc"]["elements"]), f"{name}: เลข 1..N ตามลำดับ"
    ok_marks = [{"cv_mark": 4}, {"cv_mark": 1}, {"cv_mark": 7}]
    assert not p3.marks_look_enumerated(ok_marks)
    assert not p3.marks_look_enumerated([{"cv_mark": 1}]), "mark เดียวบอกไม่ได้"
    # เลขนับเฉพาะรายการที่มี mark (มีรายการไม่ติด mark แทรก) ก็ยังเป็นการนับลำดับ
    assert p3.marks_look_enumerated([{"cv_mark": 1}, {"id": "x"}, {"cv_mark": 2}, {"cv_mark": 3}])


@test
def enumerated_marks_never_become_anchors():
    # repro_minimal case 8 pattern (83b8e52c p19): 3 single-ref records echo cv_mark = record index,
    # the boxes are unrelated -> old code: collinear anchors, page dead, shape path never tried
    grid = ASYM
    to_px = lambda mx, my: (150 + 80 * mx, 90 + 80 * my)
    pts = nodes(grid)
    els = cv_from(pts, to_px)
    doc = {"elements": [{"element_id": "F1", "element_type": "footing", "count": 9,
                         "grid_refs": [r for r, _, _ in pts if r not in ("ง1", "ง2", "ง3")]}]}
    for i, r in enumerate(("ง1", "ง2", "ง3"), 2):
        box = next(e for e in els if e["n"] == i)            # mark = record index (wrong box)
        doc["elements"].append({"element_id": f"F{i}", "element_type": "footing", "grid_refs": [r],
                                "cv_mark": i, "cv_position": {k: box[k] for k in ("cx", "cy", "w", "h", "class")}})
    doc["elements"][0]["cv_mark"] = 1
    b1 = next(e for e in els if e["n"] == 1)
    doc["elements"][0]["cv_position"] = {k: b1[k] for k in ("cx", "cy", "w", "h", "class")}
    rep = p3.measure_page(doc, grid, {"elements": els}, "plan_footing")
    assert rep["anchor_source"] == "shape_match", rep
    assert rep["ok"] and worst_error(rep, to_px, grid) < 0.05, rep["reason"]


@test
def cv_class_must_fit_element_type():
    assert p3.cv_class_fits("footing", "footing") and p3.cv_class_fits("footing", "column")
    assert p3.cv_class_fits("column", "footing") and p3.cv_class_fits("beam", "beam_h")
    assert not p3.cv_class_fits("footing", "beam_h"), "83b8e52c p23: F6 ผูกกับกล่องคาน"
    assert not p3.cv_class_fits("detail_view", "beam_v")
    assert not p3.cv_class_fits("beam", "footing")
    assert not p3.cv_class_fits(None, "footing")


@test
def real_83b8e52c_p19():
    fx = real("real_83b8e52c_p19")
    rep = p3.measure_page(fx["doc"], fx["grid"], fx["cv_scan"], "plan_footing")
    assert rep["anchor_source"] != "cv_mark", "cv_mark 1..5 ต้องไม่ถูกเชื่อ"
    assert not rep["ok"], "grid master แกน x อ่านผิด 2 เท่า + ก อยู่ล่าง + CV เห็น 5/14 -> ต้องปฏิเสธ"
    assert rep["reason_code"], rep


@test
def real_cbb90abe_p01():
    fx = real("real_cbb90abe_p01")
    assert p3.parse_grid_ref("1-จ") == {"row": "จ", "col": "1"}, "รูปเลขนำ+ขีด ต้องอ่านอักษรเป็นแถว"
    assert p3.ref_to_metre(fx["grid"], "1-ก") == (0.0, 14.55)
    assert p3.ref_to_metre(fx["grid"], "1-จ") is None, "จ มีสองเส้น (0.0 และ 4.0) ห้ามเดาเส้นแรก"
    rep = p3.measure_page(fx["doc"], fx["grid"], fx["cv_scan"], "plan_footing")
    assert not rep["ok"] and rep["reason_code"], rep
    iss = p3.validate_grid(fx["grid"])
    assert any(i["code"] == "duplicate_id" and i["axis"] == "y" and i["id"] == "จ" for i in iss), iss


@test
def real_83b8e52c_p23():
    fx = real("real_83b8e52c_p23")
    rep = p3.measure_page(fx["doc"], fx["grid"], fx["cv_scan"], "plan_footing")
    assert not rep["ok"] and rep["anchor_source"] != "cv_mark", rep


# ── C2 grid-master validation ────────────────────────────────────────────────────────
@test
def validate_grid_issues():
    assert p3.validate_grid(STD) == [], p3.validate_grid(STD)
    g43 = G([("1", 0), ("2", 3.2), ("3", 6.4), ("4", 9.6), ("ก", 11.4), ("ข", 13.2)],
            [("1", 0), ("2", 3.2), ("3", 6.4), ("4", 9.6)])            # production 43323920 shape
    codes = {(i["code"], i["axis"]) for i in p3.validate_grid(g43)}
    assert ("mixed_axis", "x") in codes and ("id_on_both_axes", None) in codes, codes
    for i in p3.validate_grid(g43):
        assert isinstance(i["detail_th"], str) and i["detail_th"], i


@test
def doubled_axis_reports_grid_scale_suspect():
    # 83b8e52c: grid master x = 0/6/12 where the sheet prints 3.00+3.00 -> px/m x is half of y.
    # Trusted identity anchors (real cv_mark echo, not enumeration) must yield 'grid_scale_suspect'.
    true_x = [("1", 0.0), ("2", 3.0), ("3", 6.0)]
    ys = [("ก", 0.0), ("ข", 1.5), ("ค", 5.5), ("ง", 7.7)]
    grid = G([(i, 2 * p) for i, p in true_x], ys)                    # x read 2x too large
    to_px = lambda mx, my: (900 + 104 * mx, 1000 + 104 * my)         # truth uses the real metres
    marks = [5, 2, 7, 3, 9, 4]
    refs = ["ก1", "ก3", "ข2", "ค1", "ง3", "ง2"]
    doc, cv = {"elements": []}, {"elements": []}
    for k, (n, ref) in enumerate(zip(marks, refs)):
        col = int(ref[1:]) - 1
        mx, my = true_x[col][1], dict(ys)[ref[0]]
        px, py = to_px(mx, my)
        cv["elements"].append({"n": n, "class": "footing", "cx": px, "cy": py, "w": 40, "h": 40})
        doc["elements"].append({"element_id": f"F{k}", "element_type": "footing", "grid_refs": [ref],
                                "cv_mark": n, "cv_position": {"cx": px, "cy": py, "w": 40, "h": 40,
                                                              "class": "footing"}})
    rep = p3.measure_page(doc, grid, cv, "plan_footing")
    assert not rep["ok"] and rep["reason_code"] == "grid_scale_suspect", rep
    assert "grid master แกน x น่าจะผิด (อัตราส่วน 2.00)" in rep["reason"], rep["reason"]
    sc = p3.grid_validation(grid, {"page_19_plan_footing": rep})["scale_check"]
    assert sc["status"] == "suspect" and sc["suspect_axis"] == "x" and abs(sc["ratio"] - 2.0) < 0.05, sc
    assert "page_19_plan_footing" in sc["source"], sc
    assert any(i["code"] == "scale_suspect" and i["axis"] == "x"
               for i in p3.grid_validation(grid, {"page_19_plan_footing": rep})["issues"])


@test
def scale_check_ok_and_unknown():
    doc, cv = _std_page()
    rep = p3.measure_page(doc, STD, cv, "plan_footing")
    assert p3.grid_validation(STD, {"p": rep})["scale_check"]["status"] == "ok"
    assert p3.grid_validation(STD, {})["scale_check"]["status"] == "unknown"


# ── C1 pass3_measure.json v2 ─────────────────────────────────────────────────────────
PAGE_KEYS = {"ok": bool, "reason": (str, type(None)), "reason_code": (str, type(None)),
             "orientation": (str, type(None)), "anchor_source": (str, type(None)),
             "transform": (dict, type(None)), "measured": int, "cv_only_count": int,
             "grid_check": list}


@test
def pass3_file_v2_schema():
    doc, cv = _std_page()
    reports = {"page_01_plan_footing": p3.measure_page(doc, STD, cv, "plan_footing"),
               "page_02_plan_beam": p3.measure_page({"elements": []}, STD, None, "plan_beam")}
    v = p3.grid_validation(STD, reports)
    f = p3.pass3_file(reports, v)
    assert f["version"] == 2 and f["mode"] == "report_only" and f["grid_master_used"] is True, f
    assert f["grid_validation"] == v and set(v) >= {"issues", "scale_check"}
    assert set(v["scale_check"]) >= {"status", "suspect_axis", "ratio", "source"}
    for key, page in f["pages"].items():
        for k, typ in PAGE_KEYS.items():
            assert k in page and isinstance(page[k], typ), (key, k, page.get(k))
    json.dumps(f, ensure_ascii=False)   # ต้อง serialize ได้ (ไม่มี tuple/set ค้าง)
    ok = f["pages"]["page_01_plan_footing"]
    assert ok["ok"] and ok["orientation"] == "identity" and ok["measured"] > 0


@test
def summary_warnings_are_system_messages():
    doc, cv = _std_page()
    reports = {"page_01_plan_footing": p3.measure_page(doc, STD, cv, "plan_footing"),
               "page_02_plan_beam": p3.measure_page({"elements": []}, STD, None, "plan_beam")}
    lines = p3.summary_warnings(reports, p3.grid_validation(STD, reports))
    assert lines and all(isinstance(s, str) for s in lines)
    txt = " ".join(lines)
    assert "วัดได้ 1/2 หน้า" in txt and "รายงานอย่างเดียว" in txt, txt
    for bad in ("เติม", "เพิ่ม element", "โมเดล"):
        assert bad not in txt, f"ข้อความ pass3 ต้องไม่อ้างว่าเติม/เพิ่ม และไม่พูดแทนโมเดล: {txt}"


@test
def demo_selfcheck():
    p3.demo()


# ── fix-up 2026-09-26 (worker review) ────────────────────────────────────────────────
@test
def vectors_copy_in_sync():
    assert LOCAL_VECTORS.exists(), "ต้องมีสำเนา vectors ใน test_fixtures (โฟลเดอร์ worker รันเดี่ยวได้)"
    if REPO_VECTORS.exists():
        assert json.loads(LOCAL_VECTORS.read_text(encoding="utf-8")) == \
            json.loads(REPO_VECTORS.read_text(encoding="utf-8")), \
            "สำเนา grid-ref-vectors.json ใน test_fixtures ไม่ตรงกับของ repo — ก๊อปใหม่จาก tests/fixtures"


@test
def junk_grid_shapes_never_raise():
    # gridline ตอบ {"x_lines": 3} แล้วงานทั้งบ้านตายที่ขั้น C2 (หลังใช้ GPU หมดแล้ว) — ทุกฟังก์ชันต้องทนได้
    doc, cv = _std_page()
    for g in ({"x_lines": 3, "y_lines": True}, {"x_lines": True}, {"x_lines": "abc", "y_lines": 5.0},
              {"x_lines": None, "y_lines": None}, [], None, 7,
              {"x_lines": [1, None, "x", {"id": None}, {"id": True, "pos_m": 1}], "y_lines": [{"id": "A"}]}):
        v = p3.grid_validation(g, {"p": {"ok": False, "reason_code": "residual"}})
        p3.summary_warnings({}, v)
        json.dumps(p3.pass3_file({}, v), ensure_ascii=False)
        assert not p3.measure_page(doc, g, cv, "plan_footing")["ok"]
        p3.nearest_grid_ref(g, 1.0, 2.0)
        assert p3.ref_to_metre(g, "A1") is None


@test
def unhashable_element_type_never_raises():
    assert p3.cv_class_fits(["footing"], "footing") is False
    assert p3.cv_class_fits({"t": "footing"}, "footing") is False
    assert p3.cv_class_fits("footing", ["footing"]) is False
    box = {"cx": 140, "cy": 90, "w": 20, "h": 20, "class": "footing"}
    els = [{"element_id": "F1", "element_type": ["footing"], "grid_refs": ["A1"], "cv_mark": 5, "cv_position": box},
           {"element_id": "F2", "element_type": {"t": 1}, "grid_refs": ["B1"], "cv_mark": 2, "cv_position": box}]
    assert p3.collect_anchors(els) == []
    assert not p3.measure_page({"elements": els}, STD, {"elements": [box]}, "plan_footing")["ok"]


@test
def stale_cv_position_without_mark_is_not_trusted():
    # doc จาก pass3 รุ่นเก่า: cv_position ที่ได้จากการจับคู่รูปทรง (อาจเป็นกระจก) / element ที่มันเพิ่มจาก CV
    # ไม่ได้มาจาก cv_mark — resume แล้วห้ามกลายเป็นหมุด
    pts = nodes(STD)[:6]
    els = []
    for i, (r, mx, my) in enumerate(pts):
        px, py = TO_PX(mx, my)
        el = {"element_id": f"F{i}", "element_type": "footing", "grid_refs": [r],
              "cv_position": {"cx": px, "cy": py, "w": 20, "h": 20, "class": "footing"}}
        if i % 2:
            el["confidence_flags"] = ["cv_matched_by_shape"]
        els.append(el)
    assert p3._trusted_cv_positions(els) == [] and p3.collect_anchors(els) == []
    # cv_mark จริง (ไม่ใช่เลขลำดับ) แต่ติดธงว่าจับคู่ด้วยรูปทรงโดย pass3 เก่า = ไม่เชื่อเช่นกัน
    els[1]["cv_mark"] = 9
    assert p3._trusted_cv_positions(els) == []


def _affine_worst(rep, case):
    a, b = case["truth_affine"]["a"], case["truth_affine"]["b"]
    t, out = rep["transform"], 0.0
    for lx in case["grid"]["x_lines"]:
        for ly in case["grid"]["y_lines"]:
            if lx["type"] == ly["type"] == "named":
                mx, my = lx["pos_m"], ly["pos_m"]
                px, py = a[0][0] * mx + a[0][1] * my + b[0], a[1][0] * mx + a[1][1] * my + b[1]
                ex, ey = p3.pixel_to_metre(t, px, py)
                out = max(out, math.hypot(ex - mx, ey - my))
    return out


@test
def reviewer_wrong_accepts_are_refused_or_right():
    # 16 หน้า fuzz ที่รอบตรวจเจอว่ายอมรับตัวแปลงผิด: กระจกรอดด่าน (ผิด 3–29 ม.), หมุด cv_mark 3–4 ตัว
    # extrapolate ผิด 0.6–2 ม., หน้าหมุน 90° (ผิด 19 ม.), หน้ายืด — ต้องปฏิเสธ หรือถ้ายอมรับต้องถูกทั้งผัง
    cases = json.loads((FIX / "fuzz_wrong_accept_v2.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 16
    bad = []
    for c in cases:
        snap = copy.deepcopy((c["doc"], c["grid"], c["cv_scan"]))
        rep = p3.measure_page(c["doc"], c["grid"], c["cv_scan"], "plan_footing")
        assert (c["doc"], c["grid"], c["cv_scan"]) == snap
        if rep["ok"] and _affine_worst(rep, c) >= 0.5:
            bad.append((c["exp"], c["seed"], rep["anchor_source"], rep["orientation"], round(_affine_worst(rep, c), 2)))
    assert not bad, f"ยอมรับแต่ผิด: {bad}"


@test
def cv_mark_fit_from_clustered_anchors_is_refused():
    # หมุด cv_mark 4 ตัวกองอยู่มุมเดียว (ช่อง 1.5 ม.) บนผังยาว 30 ม. — residual ตรงหมุดเล็ก แต่ px/m ที่ได้จาก
    # ฐาน 1.5 ม. คลาด 3 px ก็ทำให้ขอบผังเพี้ยนเกินเมตร → ต้องปฏิเสธ ไม่ใช่ยอมรับเพราะ residual ผ่าน
    grid = G([("1", 0.0), ("2", 1.5), ("3", 9.0), ("4", 30.0)], [("A", 0.0), ("B", 1.5), ("C", 12.0), ("D", 20.0)])
    to_px = lambda mx, my: (200 + 60 * mx, 150 + 60 * my)
    jit = {"A1": (3, -2), "A2": (-3, 2), "B1": (-2, 3), "B2": (3, -3)}
    doc, cv = {"elements": []}, {"elements": []}
    for mark, ref in zip((7, 3, 9, 5), ("A1", "A2", "B1", "B2")):
        mx, my = p3.ref_to_metre(grid, ref)
        px, py = to_px(mx, my)
        px, py = px + jit[ref][0], py + jit[ref][1]
        box = {"n": mark, "cx": px, "cy": py, "w": 30, "h": 30, "class": "footing"}
        cv["elements"].append(box)
        doc["elements"].append({"element_id": f"F{mark}", "element_type": "footing", "grid_refs": [ref],
                                "cv_mark": mark, "cv_position": {k: box[k] for k in ("cx", "cy", "w", "h", "class")}})
    rep = p3.measure_page(doc, grid, cv, "plan_footing")
    assert rep["anchor_source"] == "cv_mark", rep
    assert not rep["ok"] and rep["reason_code"] == "underdetermined", rep


def _doubled(grid, axis, k=2):
    g = copy.deepcopy(grid)
    for ln in g[f"{axis}_lines"]:
        ln["pos_m"] *= k
    return g


@test
def doubled_axis_detected_on_shape_path():
    # production: cv_mark เป็นเลขลำดับเสมอ (ไม่เชื่อ) → เหลือแต่ทางรูปทรง · เดิมด่านสัดส่วนต่อคลาสตัดคลาสทิ้งก่อน
    # fit ทุกครั้งที่แกนยาวผิดสเกล (สัดส่วนต่างเกือบ k เท่า) → scale_check ไม่มีวันขึ้น 'suspect' (83b8e52c จริง)
    to_px = lambda mx, my: (150 + 80 * mx, 90 + 80 * my)            # ภาพจริงใช้เมตรจริง
    doc = {"elements": [{"element_id": "F1", "element_type": "footing", "count": 16,
                         "grid_refs": [r for r, _, _ in nodes(ASYM)]}]}
    cv = {"elements": cv_from(nodes(ASYM), to_px)}
    for axis in ("x", "y"):
        grid = _doubled(ASYM, axis)                                 # grid master อ่านแกนนี้ยาวไป 2 เท่า
        rep = p3.measure_page(doc, grid, cv, "plan_footing")
        assert not rep["ok"] and rep["reason_code"] == "grid_scale_suspect", (axis, rep["reason_code"], rep["reason"])
        assert rep["scale"]["suspect_axis"] == axis and rep["scale"]["k"] == 2, rep["scale"]
        sc = p3.grid_validation(grid, {"page_19_plan_footing": rep})["scale_check"]
        assert sc["status"] == "suspect" and sc["suspect_axis"] == axis, sc
    # ผังที่ถูกอยู่แล้ว ต้องไม่ถูกหาว่าผิดสเกล
    assert p3.measure_page(doc, ASYM, cv, "plan_footing")["ok"]


@test
def no_false_scale_suspect_on_noisy_pages():
    # สเกลผิดต้องมาจากหลักฐานที่ผ่านทุกด่าน ไม่ใช่ fit ที่จับคู่มั่วแล้วบังเอิญได้อัตราส่วนใกล้ 2
    # (เดิม: 25/40000 หน้า fuzz ที่ grid ถูกทุกแผ่น ถูกรายงาน grid_scale_suspect)
    cases = json.loads((FIX / "fuzz_wrong_accept_v2.json").read_text(encoding="utf-8"))["cases"]
    cases += json.loads((FIX / "fuzz_mirror_noise.json").read_text(encoding="utf-8"))["cases"]
    got = [c["seed"] for c in cases
           if p3.measure_page(c["doc"], c["grid"], c["cv_scan"], "plan_footing")["reason_code"] == "grid_scale_suspect"]
    assert not got, got


if __name__ == "__main__":
    failed = []
    for fn in TESTS:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:  # noqa: BLE001 — report every test, never stop at the first
            failed.append(fn.__name__)
            msg = f"{type(e).__name__}: {e}"
            print(f"FAIL  {fn.__name__} — {msg[:400]}")
            if "-v" in sys.argv:
                traceback.print_exc()
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} ผ่าน")
    sys.exit(1 if failed else 0)
