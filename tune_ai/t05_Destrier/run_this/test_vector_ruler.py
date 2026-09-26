#!/usr/bin/env python3
"""Tests for vector_ruler.py — run: python test_vector_ruler.py   (stdlib only, no network, no GPU)

พิมพ์ PASS/FAIL รายข้อ (ล้มข้อเดียวไม่บังข้ออื่น) · exit 1 ถ้ามีข้อไหนล้ม

แหล่งข้อมูล:
  - test_fixtures/vectors/*.json — หน้าจริงจาก 5 บ้าน (pdf.js 3.11.174 @2.5 และ PyMuPDF reference @200/72)
    กรองให้เล็ก + grid master จาก GT ที่คนแก้แล้ว + ผลที่คาด (สร้างโดย vr_build/make_fixtures.py ของงานวิจัย)
  - เคสสังเคราะห์ในไฟล์นี้ (รู้ scale/ทิศจริงแน่นอน)
"""
import copy
import json
import math
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vector_ruler as vr  # noqa: E402

FIX = HERE / "test_fixtures" / "vectors"
S200 = 200 / 72                      # training/production PNG render scale (px per pt)
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def G(xs, ys):
    return {"x_lines": [{"id": str(i + 1), "type": "named", "pos_m": p} for i, p in enumerate(xs)],
            "y_lines": [{"id": "ABCDEFGH"[i], "type": "named", "pos_m": p} for i, p in enumerate(ys)]}


def synth(xs, ys, R=100, k=1.0, rs=S200, origin=(300.0, 250.0), pieces=40, extra_v=(), extra_h=()):
    """sidecar v1 ที่มีเส้นกริดเส้นประที่ pos_m ที่ให้ (y ลงล่าง) · extra_* = [(pos_m, pieces, span_frac)]"""
    s = vr.PT_PER_M_FULL / R * k * rs
    q = 10
    X = [origin[0] + s * m for m in xs]
    Y = [origin[1] + s * m for m in ys]
    x0, x1, y0, y1 = min(X) - 1.5 * s, max(X) + 1.5 * s, min(Y) - 1.5 * s, max(Y) + 1.5 * s
    V = [[round(x * q), round(y0 * q), round(y1 * q), pieces, -1] for x in X]
    H = [[round(y * q), round(x0 * q), round(x1 * q), pieces, -1] for y in Y]
    for m, n, f in extra_v:
        x = origin[0] + s * m
        V.append([round(x * q), round(y0 * q), round((y0 + f * (y1 - y0)) * q), n, -1])
    for m, n, f in extra_h:
        y = origin[1] + s * m
        H.append([round(y * q), round(x0 * q), round((x0 + f * (x1 - x0)) * q), n, -1])
    w, h = int(x1 + 400), int(y1 + 400)
    return {"frame": {"units_per_px": q, "png_w": w, "png_h": h, "render_scale": rs, "rotate": 0,
                      "viewport_transform": [rs, 0, 0, -rs, 0, h]},
            "layers": [], "hlines": H, "vlines": V, "segs": [], "circles": [], "text": [],
            "stats": {"painted_paths": 100, "prim_segs": 5000, "image_area_frac": 0}}, s


def one_view(rep):
    assert rep["ok"], rep
    assert len(rep["views"]) == 1, rep["views"]
    return rep["views"][0]


XS, YS = [0.0, 4.0, 7.0], [0.0, 3.0, 8.0, 11.5]     # ระยะไม่สมมาตรทั้งสองแกน


# ── สังเคราะห์ ─────────────────────────────────────────────────────────────────────────
@test
def clean_grid_gives_exact_scale_and_transform():
    sc, s = synth(XS, YS, extra_v=[(4.1, 20, 1.0), (5.5, 1, 1.0)])   # ขอบคานเส้นประ ±0.1 + ผนังเส้นทึบ
    v = one_view(vr.measure_page_vectors(sc, G(XS, YS)))
    assert v["scale_R"] == 100.0 and v["scale_nominal_R"] == 100 and v["orientation"] == "normal", v
    assert abs(v["px_per_m"] / s - 1) < 1e-4, (v["px_per_m"], s)
    t = v["transform"]
    assert abs(t["ax"] - s) < 0.01 and abs(t["ay"] - s) < 0.01 and abs(t["bx"] - 300) < 0.2 and abs(t["by"] - 250) < 0.2, t
    assert v["lines_x"] == ["1", "2", "3"] and v["lines_y"] == ["A", "B", "C", "D"], v
    assert v["unmatched_x"] == 1 and v["residual_max_m"] < 0.01, v   # เงาขอบคานนับว่าไม่ตรง แต่ไม่ทำให้ปฏิเสธ


@test
def a3_set_printed_on_a4_snaps_to_141():
    sc, s = synth(XS, YS, R=100, k=1 / math.sqrt(2))
    v = one_view(vr.measure_page_vectors(sc, G(XS, YS)))
    assert v["scale_R"] == 141.4 and v["scale_nominal_R"] == 100, v


@test
def non_standard_scale_is_refused():
    sc, _ = synth(XS, YS, R=117)          # ไม่ใช่ 1:R มาตรฐาน (และไม่ใช่ R·√2) = จับคู่ผิดหรือภาพถูกย่อ/ขยาย
    rep = vr.measure_page_vectors(sc, G(XS, YS))
    assert not rep["ok"] and rep["reason_code"] == "off_standard_scale", rep


@test
def web_render_scale_2_5_frame_handled():
    sc, s = synth(XS, YS, rs=2.5)
    v = one_view(vr.measure_page_vectors(sc, G(XS, YS)))
    assert v["scale_R"] == 100.0 and abs(v["pt_per_m"] - vr.PT_PER_M_FULL / 100) < 0.01, v


@test
def doubled_x_master_flags_x_ratio_2_not_y():
    xs = [0.0, 3.0, 6.0, 10.0]
    sc, _ = synth(xs, YS)
    rep = vr.measure_page_vectors(sc, G([2 * m for m in xs], YS))     # 83b8e52c: อ่าน 3.00+3.00 เป็น 0/6/12
    assert not rep["ok"] and rep["reason_code"] == "scale_suspect", rep
    sus = [i for i in rep["issues"] if i["code"] == "scale_suspect"]
    assert len(sus) == 1 and sus[0]["axis"] == "x" and sus[0]["ratio"] == 2.0, sus
    assert "ครึ่งหนึ่ง" in sus[0]["detail_th"] and "2.00" in sus[0]["detail_th"], sus[0]["detail_th"]
    assert not any(i.get("axis") == "y" for i in rep["issues"]), rep["issues"]


@test
def doubled_y_master_flags_y():
    ys = [0.0, 3.0, 5.0, 9.0]
    sc, _ = synth(XS, ys)
    rep = vr.measure_page_vectors(sc, G(XS, [2 * m for m in ys]))
    sus = [i for i in rep["issues"] if i["code"] == "scale_suspect"]
    assert len(sus) == 1 and sus[0]["axis"] == "y" and sus[0]["ratio"] == 2.0, rep


@test
def halved_axis_at_1to100_is_flagged_without_naming_an_axis():
    # x ครึ่งหนึ่งที่ 1:100 ≡ y สองเท่าที่ 1:50 ทางเรขาคณิต และ 1:50 ก็เป็นมาตราส่วนแปลนที่พบจริง → ไม่ชี้แกน
    xs = [0.0, 3.0, 6.0, 10.0]
    sc, _ = synth(xs, YS)
    rep = vr.measure_page_vectors(sc, G([m / 2 for m in xs], YS))
    sus = [i for i in rep["issues"] if i["code"] == "scale_suspect"]
    assert len(sus) == 1 and sus[0]["axis"] is None and sus[0]["ratio"] == 2.0, sus
    assert {(c["axis"], c["ratio"]) for c in sus[0]["candidates"]} == {("x", 0.5), ("y", 2.0)}, sus[0]["candidates"]


@test
def reversed_y_on_asymmetric_grid_is_flipped_y_with_issue():
    sc, s = synth(XS, YS)
    ys_rev = [max(YS) + min(YS) - m for m in YS]          # master นับจากล่างขึ้นบน
    v = one_view(rep := vr.measure_page_vectors(sc, G(XS, ys_rev)))
    assert v["orientation"] == "flipped_y" and v["orientation_x"] == "normal", v
    assert v["transform"]["ay"] < 0 < v["transform"]["ax"], v["transform"]
    py = v["transform"]["ay"] * 0.0 + v["transform"]["by"]           # เส้น A (pos 0) ต้องอยู่ล่างสุด
    assert abs(py - (250 + s * max(YS))) < 0.5, py
    iss = [(i["code"], i["axis"]) for i in rep["issues"]]
    assert iss == [("origin_not_top_left", "y")], iss


@test
def symmetric_spacing_reversed_is_ambiguous_without_position():
    ys = [0.0, 4.0, 8.0]
    sc, s = synth(XS, ys)
    rep = vr.measure_page_vectors(sc, G(XS, [8.0 - m for m in ys]))
    v = one_view(rep)
    assert v["orientation"] == "ambiguous" and v["ambiguous_axes"] == ["y"] and v["transform"] is None, v
    assert abs(v["px_per_m"] / s - 1) < 1e-4, v                    # scale ยังใช้ได้ ทิศไม่ขึ้นกับมัน
    assert not rep["issues"], rep["issues"]


@test
def transposed_square_grid_is_refused():
    g = [0.0, 3.0, 7.0]
    sc, _ = synth(g, g)
    rep = vr.measure_page_vectors(sc, G(g, g))
    assert not rep["ok"] and rep["reason_code"] == "transpose_ambiguous", rep


@test
def raster_page_is_no_vector_grid():
    sc, _ = synth(XS, YS, pieces=1)                                  # เส้นทึบ = ไม่ใช่ลายเส้นกริด
    assert vr.measure_page_vectors(sc, G(XS, YS))["reason_code"] == "no_vector_grid"
    empty = {"frame": sc["frame"], "hlines": [], "vlines": [], "stats": {"prim_segs": 4, "image_area_frac": 0.95}}
    rep = vr.measure_page_vectors(empty, G(XS, YS))
    assert not rep["ok"] and rep["reason_code"] == "no_vector_grid" and rep["reason"], rep


@test
def huge_dashed_lattice_is_bounded():
    xs = [i * 0.5 for i in range(80)]                                  # 80 เส้นประยาว = ไม่ใช่ผังกริดบ้าน
    sc, _ = synth(xs, YS)
    t = time.perf_counter()
    rep = vr.measure_page_vectors(sc, G(XS, YS))
    assert time.perf_counter() - t < 1.0 and rep["reason_code"] == "too_many_lines", rep["reason_code"]


@test
def malformed_inputs_never_raise():
    good, _ = synth(XS, YS)
    bad_pages = [None, [], "x", {}, {"frame": "x"}, {"frame": {"units_per_px": 0, "render_scale": 2, "png_w": 1, "png_h": 1}},
                 {"frame": dict(good["frame"], render_scale=float("nan"))}, dict(good, hlines="abc"),
                 dict(good, vlines=[["a", 1, 2, 3], [1, 2], None, [True, 1, 2, 30], [float("inf"), 0, 1, 40]])]
    for p in bad_pages:
        rep = vr.measure_page_vectors(p, G(XS, YS))
        assert rep["ok"] is False and rep["reason_code"] in vr.REASON_TH and rep["reason"], (p, rep)
    for g in [None, {}, {"x_lines": "abc"}, {"x_lines": [{"pos_m": True}, {"pos_m": "3"}, {"pos_m": float("nan")}],
                                               "y_lines": [1, None]}, G([0.0], YS)]:
        rep = vr.measure_page_vectors(good, g)
        assert rep["ok"] is False and rep["reason_code"] == "no_grid_master", (g, rep)
    weird = G(XS, YS)
    weird["x_lines"][0]["id"] = {"no": "hash"}
    assert vr.measure_page_vectors(good, weird)["ok"]


@test
def inputs_are_not_mutated():
    sc, _ = synth(XS, YS)
    g = G(XS, YS)
    a, b = copy.deepcopy(sc), copy.deepcopy(g)
    vr.measure_page_vectors(sc, g)
    assert sc == a and g == b


@test
def dummy_lines_drawn_count_as_explained():
    g = G(XS, YS)
    g["x_lines"].append({"id": "1'", "type": "dummy", "pos_m": 1.5})
    sc, _ = synth(XS + [1.5], YS)
    one_view(vr.measure_page_vectors(sc, g))


@test
def two_line_axis_gets_no_tolerance():
    # x master 2 เส้น [0, 1.5] ตกเส้นประจริงที่ 0 และ 1.5 ได้พอดี แต่เส้นกริดจริงที่ 4.0 เหลือ → ต้องปฏิเสธ
    # (แกนที่ master ≥3 เส้นยอมเส้นเกินในช่วงกริดได้ 1 เส้น แกน 2 เส้นไม่ยอมเลย)
    sc, _ = synth([0.0, 1.5, 4.0], YS)
    rep = vr.measure_page_vectors(sc, G([0.0, 1.5], YS))
    assert not rep["ok"] and rep["reason_code"] == "incomplete", rep
    sc, _ = synth([0.0, 1.5, 4.0, 7.0], YS)
    one_view(vr.measure_page_vectors(sc, G([0.0, 4.0, 7.0], YS)))     # 3 เส้น: เส้นเกิน 1 เส้นยอมได้


@test
def grid_master_with_extra_undrawn_named_line_is_incomplete():
    sc, _ = synth(XS, YS)
    rep = vr.measure_page_vectors(sc, G(XS + [10.0], YS))
    assert not rep["ok"] and rep["reason_code"] == "incomplete", rep


# ── หน้าจริง ────────────────────────────────────────────────────────────────────────────
def _fixtures():
    return sorted(FIX.glob("*.json"))


def _summary(rep):
    return {"ok": rep["ok"], "reason_code": rep["reason_code"],
            "views": [{k: v[k] for k in ("view", "scale_R", "orientation", "orientation_x", "orientation_y",
                                         "lines_x", "lines_y", "px_per_m")} for v in rep["views"]],
            "issues": sorted([i["code"], i["axis"]] for i in rep["issues"])}


def _corrupt(g, kind):
    """kind 'x*2' = pos_m ทุกเส้นของ x_lines คูณ 2 (รูปแบบเดียวกับ expect_corrupted ใน fixture)"""
    axis, f = kind.split("*")
    g = copy.deepcopy(g)
    for ln in g[axis + "_lines"]:
        if isinstance(ln.get("pos_m"), (int, float)):
            ln["pos_m"] *= 1 / 3 if f == "0.3333" else float(f)
    return g


@test
def real_fixtures_match_expected():
    files = _fixtures()
    assert len(files) >= 5, files
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        t = time.perf_counter()
        got = _summary(vr.measure_page_vectors(d["sidecar"], d["grid_master"]))
        assert time.perf_counter() - t < 1.0, f.name
        exp = dict(d["expect"], issues=sorted(list(i) for i in d["expect"]["issues"]))
        assert got == exp, (f.name, got, exp)
        for kind, e in d["expect_corrupted"].items():
            got = _summary(vr.measure_page_vectors(d["sidecar"], _corrupt(d["grid_master"], kind)))
            assert got == dict(e, issues=sorted(list(i) for i in e["issues"])), (f.name, kind, got)


@test
def real_two_plans_on_one_sheet_a3_on_a4():
    d = json.loads((FIX / "house01_p19_pdfjs_2views.json").read_text(encoding="utf-8"))
    rep = vr.measure_page_vectors(d["sidecar"], d["grid_master"])
    assert rep["ok"] and len(rep["views"]) == 2, rep
    assert all(v["scale_R"] == 141.4 and v["scale_nominal_R"] == 100 for v in rep["views"])  # พิมพ์ 1:100 แต่ PDF 1:141.4
    assert rep["views"][0]["bbox_px"][2] < rep["views"][1]["bbox_px"][0]      # สองแปลนวางข้างกัน ไม่ปนกัน


@test
def real_bottom_up_gt_master_is_reported_not_hidden():
    # GT ของบ้านนี้นับ y จากล่าง (แถว E วาดอยู่บนสุด) — ต้องรายงาน ไม่ใช่วางตำแหน่งกลับหัวเงียบๆ
    d = json.loads((FIX / "large1f02_p28_beam_flipped_y.json").read_text(encoding="utf-8"))
    rep = vr.measure_page_vectors(d["sidecar"], d["grid_master"])
    v = one_view(rep)
    assert v["orientation"] == "flipped_y" and v["transform"]["ay"] < 0, v
    assert [(i["code"], i["axis"], i["source"]) for i in rep["issues"]] == [("origin_not_top_left", "y", "vector_grid")]


@test
def real_1to50_doubled_axis_is_not_blamed_on_one_axis():
    d = json.loads((FIX / "small1f08_p21_beam_1to50.json").read_text(encoding="utf-8"))
    for kind in ("x*2", "y*2"):
        rep = vr.measure_page_vectors(d["sidecar"], _corrupt(d["grid_master"], kind))
        sus = [i for i in rep["issues"] if i["code"] == "scale_suspect"]
        assert sus and all(i["axis"] is None for i in sus), (kind, sus)


@test
def real_two_line_axis_wrong_master_is_never_accepted():
    # master x มี 2 เส้น: คูณ ⅓ แล้วสองเส้นยังตกเส้นประที่ห่างพอดีได้ — ต้องไม่ยอมรับ (เคยยอมรับก่อนมีกฎ 2 เส้น)
    d = json.loads((FIX / "small2f08_p21_beam_2line_x.json").read_text(encoding="utf-8"))
    assert vr.measure_page_vectors(d["sidecar"], d["grid_master"])["ok"]
    for kind in ("x*2", "y*2", "x*0.3333"):
        rep = vr.measure_page_vectors(d["sidecar"], _corrupt(d["grid_master"], kind))
        assert not rep["ok"], (kind, rep["views"])


def _vreps():
    """{page_NN: report} จริง: หน้า 27/28 ของบ้านที่ GT นับ y จากล่าง + หน้าคานที่ master x ยาวไป 2 เท่า"""
    a = json.loads((FIX / "large1f02_p28_beam_flipped_y.json").read_text(encoding="utf-8"))
    b = json.loads((FIX / "small2f01_p31_beam.json").read_text(encoding="utf-8"))
    ra = vr.measure_page_vectors(a["sidecar"], a["grid_master"])
    rb = vr.measure_page_vectors(b["sidecar"], _corrupt(b["grid_master"], "x*2"))
    return {"page_27": ra, "page_28": copy.deepcopy(ra), "page_31": rb}


@test
def merge_validation_groups_pages_and_sets_scale_check():
    base = {"issues": [{"code": "duplicate_id", "axis": "x", "detail_th": "dup"}],
            "scale_check": {"status": "unknown", "suspect_axis": None, "ratio": None, "source": "pass3 ไม่ได้รัน"}}
    frozen = copy.deepcopy(base)
    out = vr.merge_validation(base, _vreps())
    assert base == frozen                                             # ไม่แก้ของเดิม
    ori = [i for i in out["issues"] if i["code"] == "origin_not_top_left"]
    assert len(ori) == 1 and ori[0]["pages"] == ["page_27", "page_28"] and ori[0]["axis"] == "y", ori
    assert ori[0]["source"] == "vector_grid" and "page_27, page_28" in ori[0]["detail_th"] and "view" not in ori[0]
    sus = [i for i in out["issues"] if i["code"] == "scale_suspect"]
    assert len(sus) == 1 and sus[0]["axis"] == "x" and sus[0]["ratio"] == 2.0 and sus[0]["pages"] == ["page_31"], sus
    assert out["scale_check"] == {"status": "suspect", "suspect_axis": "x", "ratio": 2.0, "source": "vector_grid page_31"}
    assert out["issues"][0]["code"] == "duplicate_id"
    json.dumps(out, ensure_ascii=False)


@test
def merge_validation_cv_and_vector_disagree_on_axis_flags_both():
    cv = {"issues": [{"code": "scale_suspect", "axis": "y", "ratio": 2.0, "detail_th": "cv"}],
          "scale_check": {"status": "suspect", "suspect_axis": "y", "ratio": 2.0, "source": "pass3 page_31_plan_beam"}}
    out = vr.merge_validation(cv, _vreps())
    assert out["scale_check"]["status"] == "suspect" and out["scale_check"]["suspect_axis"] is None, out["scale_check"]
    assert "pass3 page_31_plan_beam" in out["scale_check"]["source"]


@test
def merge_validation_confirms_existing_issue_instead_of_repeating():
    cv = {"issues": [{"code": "origin_not_top_left", "axis": "y", "pages": ["page_28_plan_beam"], "detail_th": "cv"}],
          "scale_check": {"status": "ok", "suspect_axis": None, "ratio": 1.01, "source": "pass3 page_28_plan_beam"}}
    reps = _vreps()
    reps.pop("page_31")
    out = vr.merge_validation(cv, reps)
    ori = [i for i in out["issues"] if i["code"] == "origin_not_top_left"]
    assert len(ori) == 1 and ori[0]["vector_pages"] == ["page_27", "page_28"] and "เวกเตอร์ยืนยัน" in ori[0]["detail_th"]
    assert out["scale_check"]["source"] == "pass3 page_28_plan_beam"          # ok เดิมคงไว้


@test
def merge_validation_unknown_becomes_ok_when_vectors_measured():
    reps = _vreps()
    reps.pop("page_31")
    out = vr.merge_validation(None, reps)
    assert out["scale_check"] == {"status": "ok", "suspect_axis": None, "ratio": 1.0,
                                  "source": "vector_grid page_27, page_28"}, out["scale_check"]
    assert vr.merge_validation({"issues": "junk", "scale_check": 5}, {"page_01": None})["issues"] == []


@test
def summary_line_counts_pages():
    s = vr.summary_line(_vreps())
    assert s.startswith("ไม้บรรทัดเส้นกริดเวกเตอร์") and "วัดได้ 2/3 หน้า" in s and "1:100" in s and "scale_suspect 1" in s, s
    assert vr.summary_line({}) is None


@test
def report_shape_contract():
    d = json.loads((FIX / "small2f01_p31_beam.json").read_text(encoding="utf-8"))
    rep = vr.measure_page_vectors(d["sidecar"], d["grid_master"])
    assert rep["source"] == "vector_grid" and rep["version"] == 1 and rep["reason_code"] is None
    v = rep["views"][0]
    for k in ("px_per_m", "pt_per_m", "scale_R", "snap_err", "orientation", "lines_x", "lines_y", "unmatched_x",
              "unmatched_y", "residual_max_m", "transform", "bbox_px"):
        assert k in v, k
    assert set(v["transform"]) == {"ax", "bx", "ay", "by"}
    json.dumps(rep, ensure_ascii=False)       # ต้อง serialize ได้ (ลง pass3_measure.json)


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
