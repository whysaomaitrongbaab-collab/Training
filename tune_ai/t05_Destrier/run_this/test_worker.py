#!/usr/bin/env python3
"""Self-check for worker.py's pure logic — run: python test_worker.py
(อยู่นอก tests/ เพราะ npm test เป็น node runner; ตัวนี้รันมือ/CI python เท่านั้น)"""
import os
import sys
from pathlib import Path

# worker.py โหลด config ตอน import — ใส่ dummy ให้ผ่าน แล้วชี้ prompts ที่ Training repo จริง
os.environ.setdefault("SUPABASE_URL", "http://dummy")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "dummy")
os.environ.setdefault("PURSON_GPU_URL", "http://dummy")
DEFAULT_PROMPTS = r"d:\00mk\steel project\training\Training\tune_ai\t04_Purson"
os.environ.setdefault("PURSON_PROMPTS_DIR", DEFAULT_PROMPTS)

if not Path(os.environ["PURSON_PROMPTS_DIR"]).exists():
    print("SKIP: PURSON_PROMPTS_DIR ไม่มีบนเครื่องนี้ — ตั้ง env ชี้ t04_Purson แล้วรันใหม่")
    sys.exit(0)

import worker  # noqa: E402

# strip_fence — เคสจริงที่เคยเจอทั้งหมด
assert worker.strip_fence('```json\n{"a": 1}\n```') == '{"a": 1}'
assert worker.strip_fence('{"a": 1,}') == '{"a": 1}'                    # trailing comma
assert worker.strip_fence('{"c": 0., "d": [1.]}') == '{"c": 0.0, "d": [1.0]}'  # บ้าน08 notes bug
assert worker.strip_fence('{"v": "1.5 m."}') == '{"v": "1.5 m."}'       # จุดในสตริงห้ามแตะ...
# หมายเหตุ: regex เดิมของ infer_house_t03.py ไม่แยกสตริง — เคสเลขจบด้วยจุดก่อน space ในสตริง
# จะโดนเติม 0 เหมือนกัน ยอมรับเป็น known limitation เดียวกับต้นทาง (defense layer ไม่ใช่ parser)

# prompt assembly — COMMON ต้องไม่มี glossary marker เหลือ และ prompt ราย subtask ต้องโหลดได้
assert "GLOSSARY START" not in worker.COMMON
for sub in ("plan_beam", "plan_footing", "plan_slab", "section", "schedule", "notes", "gridline"):
    p = worker.subtask_prompt(sub)
    assert p and p.startswith(worker.COMMON[:40]), f"prompt {sub} ประกอบผิด"
assert worker.subtask_prompt("no_such_subtask") is None
assert len(worker.PASS0_PROMPT) > 200, "pass0 prompt สั้นผิดปกติ"

print("OK — strip_fence + prompt assembly ผ่านทุกข้อ")

# ── ตัวกรองขยะ: ต้องทิ้งของเสียจริง แต่ห้ามทิ้งค่าติดลบที่ถูกต้องตามสเปก (แก้ 2026-09-01) ──
# เคสจริงจาก GT: 07บ้าน_ใหญ่_2ชั้น_01 หน้า35 คานคอดิน "GB1(-0.50)" → level_m: -0.5
gb1 = {"element_id": "GB1", "element_type": "beam", "level_m": -0.5, "span_length_m": 4.0}
assert not worker._element_is_garbage(gb1), "คานคอดิน level_m ติดลบ = ถูกต้อง ห้ามทิ้ง"
assert not worker._element_is_garbage({"id": "S1", "level_step_mm": -100}), \
    "พื้นสำเร็จลดระดับ level_step_mm ติดลบ = ถูกต้อง ห้ามทิ้ง"
assert not worker._element_is_garbage({"id": "C1", "pos_m": -1.2}), \
    "pos_m ก่อน origin ติดลบได้ตามสเปก (IO_SPEC ข้อ grid) ห้ามทิ้ง"
# ของที่ต้องทิ้งจริงยังต้องทิ้งอยู่
assert worker._element_is_garbage({"id": "B2", "width_mm": -200}), "ขนาดหน้าตัดติดลบ = ขยะ"
assert worker._element_is_garbage({"id": "B2", "span_length_m": -4.0}), "ความยาวติดลบ = ขยะ"
assert worker._element_is_garbage({"id": "B3", 'x": 1, "y': 2}), "คีย์มี : หรือ , = generation หลุด"
assert worker._element_is_garbage({"id": "B4", "stirrup": {"dia_mm": -6}}), "nested ก็ต้องตรวจ"

# sanitize_elements ต้องเก็บของดีไว้ครบ และบันทึกจำนวนที่ทิ้งเสมอ (ไม่เงียบ)
_doc = worker.sanitize_elements({"elements": [gb1, {"id": "X", "height_mm": -1}]})
assert len(_doc["elements"]) == 1 and _doc["elements"][0]["element_id"] == "GB1"
assert any("ทิ้ง 1/2" in w for w in _doc.get("warnings", [])), _doc.get("warnings")

# ── pass1/1.5/2.5 wiring (2026-09-01) — ต้องมีของจริง ไม่ mock organize.py/cv_scan.py ──
if not worker.ORGANIZE_PY.exists() or not worker.CV_SCAN_PY.exists():
    print("SKIP pass1 test: organize.py/cv_scan.py ไม่มีบนเครื่องนี้")
else:
    import io
    import tempfile
    from PIL import Image, ImageDraw

    def _tiny_png(w=400, h=300):
        img = Image.new("L", (w, h), 255)
        d = ImageDraw.Draw(img)
        d.rectangle([10, 10, w - 10, h - 10], outline=0, width=3)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    house = "test_house_pass1"
    images = {1: _tiny_png(), 2: _tiny_png(600, 300)}
    classified = [
        {"_page": 1, "sheet_code": "S-01", "sheet_name": "แปลนฐานราก", "building": "main",
         "views": [{"subtask": "plan_footing", "where": "full"}]},
        # หน้า 2 มี 2 view ชนิดเดียวกัน (footing ซ้าย/ขวา) — ไม่มีเส้นแบ่งจริงในภาพ →
        # organize.py ต้อง "ไม่เดา" คืน None ให้ crop_for_task fallback เต็มหน้า
        {"_page": 2, "sheet_code": "S-02", "sheet_name": "แปลนฐานราก 2", "building": "main",
         "views": [{"subtask": "plan_footing", "where": "left"},
                   {"subtask": "plan_footing", "where": "right"}]},
    ]

    workroot = worker.run_pass1_organize(house, classified, images)
    assert workroot is not None, "run_pass1_organize ควรสำเร็จกับ input ที่ถูกต้อง"
    assert (workroot / "pass2" / "plan_footing" / "manifest.json").exists()

    ok = worker.run_cv_scan(workroot, pass25=False)
    assert ok, "cv_scan.py --manifest ควรรันจบสำเร็จ (แม้ไม่เจอ element ก็ต้อง exit 0)"

    # หน้า 1: 1 view เดี่ยว → organize.py คัดลอกเต็มหน้าตรงๆ (ไม่ตัด — มีแค่ view เดียวอยู่แล้ว)
    # แต่ manifest/crop_for_task ต้องหาไฟล์เจอและคืน bytes จริง ไม่ fallback เป็น None
    crop1, hint1 = worker.crop_for_task(workroot, "plan_footing", 1)
    assert crop1 is not None, "หน้า 1 (1 view) ต้องหา crop เจอ ไม่ fallback"
    assert crop1 == images[1], "1 view ไม่มีอะไรให้ตัด — organize.py ต้องคัดลอกเต็มหน้าตรงๆ"

    # หน้า 2: ตัดไม่ได้ (ไม่มีเส้นแบ่งจริง) → organize.py ส่งเต็มหน้าให้ทุก view ของหน้านั้น
    # (คนละ entry ต่อ view ใน manifest แต่ทั้งคู่ png="2") → crop_for_task เจอ >1 entry → fallback
    crop2, hint2 = worker.crop_for_task(workroot, "plan_footing", 2)
    assert crop2 is None and hint2 is None, "หน้าที่ตัดไม่ชัดเจนต้อง fallback เป็น None ไม่ใช่เดา"

    # หน้าที่ไม่มีจริงเลย → fallback เช่นกัน ไม่ throw
    crop3, hint3 = worker.crop_for_task(workroot, "plan_footing", 999)
    assert crop3 is None and hint3 is None

    # pass1.5 base scan (#n+พิกัด) ต้องถูกเก็บเข้า files[] จริง ไม่ทิ้งไปเฉยๆ — ภาพ synthetic
    # นี้ไม่มี footing/column จริงจึงคาด elements=0 แต่ "ไฟล์ต้องถูกเขียน" คือสิ่งที่เทสนี้ยืนยัน
    cv15_files, n_cv15 = worker.collect_pass15_files(workroot)
    assert isinstance(cv15_files, list) and isinstance(n_cv15, int)
    assert all(f["name"].startswith("cv15_plan_footing_") for f in cv15_files)

    ok25 = worker.run_cv_scan(workroot, pass25=True)
    assert ok25, "cv_scan.py --manifest --pass25 ควรรันจบสำเร็จ"
    files25, added = worker.collect_pass25_files(workroot)
    assert isinstance(files25, list) and isinstance(added, int)

    # merge_cv_marks: หน้า 2 (fallback, ไม่มี crop ชัดเจน) → ไม่มี marks ให้จับคู่ ต้องคืน
    # doc เดิมเป๊ะ ไม่ throw ไม่แก้อะไร
    fake_doc = {"elements": [{"cv_mark": 1, "id": "F1"}]}
    unchanged = worker.merge_cv_marks(dict(fake_doc), workroot, "plan_footing", 2)
    assert unchanged == fake_doc, "ไม่มี crop ชัดเจน (fallback) ต้องไม่แก้ doc เลย"

    # หน้า 1: crop เจอ แต่ synthetic image ไม่มี footing/column จริง → marks={} (ไม่ใช่ None)
    # → cv_mark=1 ที่โมเดล "ตอบ" ไม่มีจริงในบัญชี → ต้องติดธง warnings ไม่ใช่ throw/เงียบ
    stray_doc = worker.merge_cv_marks(dict(fake_doc), workroot, "plan_footing", 1)
    assert "cv_position" not in stray_doc["elements"][0]
    assert any("หลอน" in w for w in stray_doc.get("warnings", [])), \
        "cv_mark ที่ไม่มีจริงในบัญชีต้องติดธงใน warnings ไม่ใช่เงียบ"

    # element ที่ไม่มี cv_mark เลย ต้องผ่านไปเฉยๆ ไม่ไปยุ่ง ไม่มี warning
    no_mark_doc = worker.merge_cv_marks({"elements": [{"id": "F2"}]}, workroot, "plan_footing", 1)
    assert "warnings" not in no_mark_doc or not no_mark_doc["warnings"]

    # cv_scan_for_task: หน้า 1 มี _cv.json จริง (เขียนเสมอแม้ 0 element) → ต้องได้ dict
    # ที่มีคีย์ elements · หน้า fallback (2) ไม่มี crop ชัดเจน → None
    scan1 = worker.cv_scan_for_task(workroot, "plan_footing", 1)
    assert isinstance(scan1, dict) and "elements" in scan1, scan1
    assert worker.cv_scan_for_task(workroot, "plan_footing", 2) is None

    # run_pass1_organize เองไม่กันพลาด (images ขาดหน้า = KeyError) — run_house_extract
    # เป็นคนห่อ try/except ให้ fallback เต็มหน้า ยืนยันสัญญานี้ตรงๆ กันมีคนลบ try/except ทิ้ง
    try:
        worker.run_pass1_organize(house, [{"_page": 1, "views": []}], {})
        raise AssertionError("run_pass1_organize ควร throw เมื่อ images ขาดหน้า ไม่ใช่กลืนเงียบ")
    except KeyError:
        pass

    print("OK — pass1/1.5/2.5 wiring (organize.py + cv_scan.py จริง) ผ่านทุกข้อ")


# ── ทนเน็ตสะดุด (เพิ่ม 2026-09-01) ────────────────────────────────────────────
# งานจริงยาว 75-80 นาที คุย Supabase ~40 ครั้ง — เน็ตกระตุกครั้งเดียวต้องไม่ทิ้งงานทั้งใบ
_slept = []
worker.time.sleep = lambda s: _slept.append(s)   # ไม่ต้องรอจริงตอนเทส

calls = []
assert worker._retry(lambda: (calls.append(1), "ok")[1], "ทดสอบ") == "ok"
assert len(calls) == 1 and not _slept, "สำเร็จรอบแรกต้องไม่ retry และไม่ sleep"

calls.clear(); _slept.clear()
def flaky():
    calls.append(1)
    if len(calls) < 3:
        raise ConnectionError("เน็ตหลุด")
    return "ok"
assert worker._retry(flaky, "ทดสอบ") == "ok"
assert len(calls) == 3, f"ต้องยิงซ้ำจนสำเร็จ (ได้ {len(calls)} ครั้ง)"
assert _slept == [5, 15], f"ต้องถอยหลังตาม NET_BACKOFF_S (ได้ {_slept})"

calls.clear(); _slept.clear()
def always_dead():
    calls.append(1)
    raise ConnectionError(f"ตายรอบที่ {len(calls)}")
try:
    worker._retry(always_dead, "ทดสอบ")
    raise AssertionError("พังครบทุกรอบต้อง raise ไม่ใช่คืน None เงียบๆ")
except ConnectionError as e:
    assert "ตายรอบที่ 5" in str(e), f"ต้องโยน exception ตัวล่าสุด (ได้ {e})"
assert len(calls) == worker.NET_TRIES, f"ต้องลอง {worker.NET_TRIES} ครั้ง (ได้ {len(calls)})"

# call_purson: ต่อไม่ติด = ยิงซ้ำได้ · แต่ ReadTimeout = โมเดลยังคิดอยู่ ห้ามยิงซ้ำ
# (ยิงซ้ำ = GPU ทำงานสองงานพร้อมกัน ช้าลงกว่าเดิม แล้วก็ timeout ซ้ำอยู่ดี)
posts = []
def post_readtimeout(*a, **k):
    posts.append(1)
    raise worker.requests.exceptions.ReadTimeout("อ่านไม่ทัน")
worker.requests.post = post_readtimeout
try:
    worker.call_purson([b"x"], "prompt")
    raise AssertionError("ReadTimeout ต้องทะลุออกมา ไม่ใช่ถูกกลืน")
except worker.requests.exceptions.ReadTimeout:
    pass
assert len(posts) == 1, f"ReadTimeout ห้ามยิงซ้ำ (ยิงไป {len(posts)} ครั้ง)"

posts.clear(); _slept.clear()
def post_connfail(*a, **k):
    posts.append(1)
    raise worker.requests.exceptions.ConnectionError("tunnel ตาย")
worker.requests.post = post_connfail
try:
    worker.call_purson([b"x"], "prompt")
except worker.requests.exceptions.ConnectionError:
    pass
assert len(posts) == 1 + worker.NET_TRIES, \
    f"ต่อไม่ติดต้องยิงซ้ำครบ (ยิงไป {len(posts)} ครั้ง)"

print("OK — retry/ทนเน็ตสะดุด ผ่านทุกข้อ")


# ── ครอปผิดโซนต้อง fallback เต็มหน้า ไม่ใช่ส่งครอปที่ CV ยืนยันแล้วว่าไม่มีของ (2026-09-01) ──
# เจอจริง: pass0 สลับ top/bottom ของหน้าที่มี 2 view → organize.py ครอปตามที่สั่งอย่าง
# ซื่อสัตย์ ได้ครอปที่ไม่มีฐานรากอยู่เลย ส่งให้โมเดลอ่านเป็น plan_footing จนตอบช้าผิดปกติ
import json as _json
import shutil as _shutil
import tempfile as _tempfile

_ct_root = Path(_tempfile.mkdtemp(prefix="purson_croptest_"))
try:
    _sub_dir = _ct_root / "pass2" / "plan_footing"
    (_sub_dir / "images").mkdir(parents=True)
    (_sub_dir / "cv").mkdir(parents=True)
    # crop_for_task แค่อ่าน bytes ดิบ ไม่ decode ภาพ — เนื้อหาไฟล์ไม่สำคัญสำหรับเทสนี้
    (_sub_dir / "images" / "page_1_view1.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (_sub_dir / "manifest.json").write_text(_json.dumps({
        "sources": [{"image": "images/page_1_view1.png", "png": "1", "cropped": True}]
    }), encoding="utf-8")

    # ครอปที่ตัดจริง (cropped:true) แต่ CV หาฐานราก/เสาไม่เจอเลย → สงสัยว่าผิดโซน → fallback
    (_sub_dir / "cv" / "page_1_view1_cv.json").write_text(
        _json.dumps({"counts": {"footing": 0, "column": 0, "beam": 0}}), encoding="utf-8")
    crop, hint = worker.crop_for_task(_ct_root, "plan_footing", 1)
    assert crop is None and hint is None, "ครอปที่ CV ยืนยันว่าไม่มีฐานราก/เสาเลยต้อง fallback"

    # เจอของจริงแม้แค่ตัวเดียว → เชื่อครอป ใช้ตามปกติ
    (_sub_dir / "cv" / "page_1_view1_cv.json").write_text(
        _json.dumps({"counts": {"footing": 1, "column": 0, "beam": 0}}), encoding="utf-8")
    crop, hint = worker.crop_for_task(_ct_root, "plan_footing", 1)
    assert crop is not None, "เจอฐานรากอย่างน้อย 1 ตัวในครอปแล้วต้องเชื่อครอป ไม่ fallback"

    # ไม่มี cv.json เลย (pass1.5 ล้ม/ข้าม) → เชื่อครอปไปก่อน (ไม่มีหลักฐานว่าผิดโซน)
    (_sub_dir / "cv" / "page_1_view1_cv.json").unlink()
    crop, hint = worker.crop_for_task(_ct_root, "plan_footing", 1)
    assert crop is not None, "ไม่มีผล CV ให้เช็ค ต้องเชื่อครอปไปก่อน ไม่ใช่ fallback เดา"
finally:
    _shutil.rmtree(_ct_root, ignore_errors=True)

print("OK — ครอปผิดโซน (CV ยืนยันว่าง) fallback เต็มหน้า ผ่านทุกข้อ")
