#!/usr/bin/env python3
"""Self-check ของ preset เสิร์ฟทุกตัวใน presentation.py — รัน: python test_serve_presets.py

ทุก assert ในไฟล์นี้ผูกกับความพังที่ **เคยเกิดขึ้นจริง** ไม่ใช่ความพังที่จินตนาการเอา:

  · ความละเอียดภาพไม่ตรงกับตอนเทรน → บั๊กคลาสที่ฆ่า t01 และ t04 (ภาพโดนย่อเงียบๆ)
  · คีย์ max_pixels ที่โมเดลนี้ไม่รู้จัก → HF warn แล้วทิ้ง ภาพย่อตาม default เงียบๆ
  · lora_B layout ที่ unsloth เปลี่ยน 17 ก.ย. 2026 → expert จับคู่ rank ผิด ผลเป็นขยะเงียบๆ
  · ภาพต่อ request < 4 → งาน gridline (มัด 4 หน้า) โดนปฏิเสธ
  · context สั้นไป → งานหนักโดนตัดกลางคัน แต่ smoke test ผ่านฉลุย (มองไม่เห็น)

ทั้งหมดเป็นความพังแบบ "ไม่มี error ให้เห็น" ทั้งสิ้น — จึงต้องมีด่านที่ตรวจตอนยังไม่เสียเงิน
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import presentation as P  # noqa: E402

# ค่าที่เทรนมาจริง — ต้องตรงกับ train_t05_courser.py (MAX_PIXELS / MIN_PIXELS)
TRAIN_LONGEST = 6912 * 1024      # 7,077,888
TRAIN_SHORTEST = 256 * 1024      # 262,144
# worker.py ส่ง "model": CFG["PURSON_MODEL"] ซึ่ง default เป็น "purson"
WORKER_MODEL_NAME = "purson"
# งาน gridline มัดได้สูงสุด 4 ภาพ/คำขอ (worker.py: gp = grid_pages[:4])
MAX_IMAGES_PER_REQUEST = 4

served = [(k, m) for k, m in P.MODELS.items() if m.get("serve")]
assert served, "ไม่มี preset ที่ใช้ engine ภายนอกเลย — ตั้งใจหรือเปล่า?"

for name, m in served:
    cmd = P.launch_cmd(m, m.get("model_repo", ""), "")

    # 1. ความละเอียดต้องตรงกับตอนเทรน — ทั้งสองคีย์ ไม่ใช่แค่ค่าบน
    assert str(TRAIN_LONGEST) in cmd, f"{name}: ไม่มี longest_edge {TRAIN_LONGEST} ในคำสั่ง"
    assert str(TRAIN_SHORTEST) in cmd, f"{name}: ไม่มี shortest_edge {TRAIN_SHORTEST} ในคำสั่ง"

    # 2. ห้ามใช้คีย์ max_pixels — Qwen3VLProcessor ไม่รู้จัก จะโดนทิ้งเงียบๆ
    assert "max_pixels" not in cmd or "IMAGE_MAX_PIXELS" in cmd, (
        f"{name}: ใช้คีย์ max_pixels ซึ่ง processor ตัวนี้ไม่รู้จัก — ต้องใช้ size dict")

    # 3. ชื่อโมเดลต้องตรงกับที่ worker.py ส่งมา ไม่งั้น engine ตอบ 404 model not found
    assert WORKER_MODEL_NAME in cmd, f"{name}: ไม่ได้ตั้งชื่อโมเดลเป็น '{WORKER_MODEL_NAME}'"

    # 4. ต้องรับภาพได้อย่างน้อยเท่าที่ worker ส่งจริง
    assert f'"image": {MAX_IMAGES_PER_REQUEST}' in cmd or \
           f'"image":{MAX_IMAGES_PER_REQUEST}' in cmd, \
        f"{name}: ไม่ได้ตั้งเพดานภาพเป็น {MAX_IMAGES_PER_REQUEST} — งาน gridline จะโดนปฏิเสธ"

    # 5. context ต้องพอสำหรับงานหนักสุด (4 ภาพ + instruction + output)
    need = MAX_IMAGES_PER_REQUEST * (TRAIN_LONGEST // 1024) + 6000
    assert P.SERVE_CONTEXT_LEN >= need, (
        f"context {P.SERVE_CONTEXT_LEN} < ที่งาน gridline ต้องใช้จริง ~{need} "
        f"— งานหนักจะโดนตัดกลางคันโดย smoke test มองไม่เห็น")

    print(f"OK  {name}: ความละเอียด/ชื่อโมเดล/เพดานภาพ/context ครบ")

# 6. เส้นทาง Unsloth ต้องพก env กัน lora_B layout เสมอ (ระเบิดเวลา 17 ก.ย. 2026)
for name, m in P.MODELS.items():
    if m.get("serve") or m.get("unsupported"):
        continue
    cmd = P.launch_cmd(m, m.get("adapter", ""), "")
    assert "UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert" in cmd, (
        f"{name}: ขาด env กัน lora_B layout — เครื่องที่เช่าหลัง 17 ก.ย. 2026 จะอ่าน adapter "
        f"ผิดแบบเงียบๆ (pip install -U unsloth ได้ตัวใหม่ที่อ่าน rank_major)")
    assert "serve_purson.py" in cmd, f"{name}: เส้นทาง Unsloth ต้องเรียก serve_purson.py"
    print(f"OK  {name}: พก env กัน lora_B layout แล้ว")

# 7. preset ที่ใช้ engine ภายนอกต้องชี้ไปที่โมเดล merged ไม่ใช่ adapter
for name, m in served:
    assert m.get("model_repo") and not m.get("adapter"), (
        f"{name}: ต้องใช้ model_repo (โมเดล merged) — engine พวกนี้โหลด LoRA MoE ของเราไม่ได้")

# 8. เมนู GO.bat ต้องรู้จัก preset ครบ — ไม่งั้นเพิ่ม preset แล้วมะขามเลือกไม่ได้
#    (เกิดขึ้นจริงรอบนี้: เพิ่ม destrier-vllm/-sglang แล้วลืมแก้เมนู เลือกไม่ได้เลย)
import go  # noqa: E402

menu = {n for n, _ in go.MODEL_MENU}
unknown = menu - set(P.MODELS)
assert not unknown, f"เมนู GO.bat มีรุ่นที่ presentation.py ไม่รู้จัก: {unknown}"
missing = {k for k, m in P.MODELS.items() if not m.get("unsupported")} - menu
assert not missing, f"preset ที่ใช้ได้แต่เมนู GO.bat เลือกไม่ได้: {missing}"
assert go.MODEL_MENU[0][0] == "destrier", (
    "ตัวแรกในเมนู = ค่าเริ่มต้นเมื่อกด Enter — ต้องเป็นรุ่นที่พิสูจน์แล้วเสมอ "
    "ห้ามตั้งรุ่นที่ยังไม่เคยรันจริงเป็นค่าเริ่มต้น")
print(f"OK  เมนู GO.bat ตรงกับ preset ({len(menu)} รุ่น) · ค่าเริ่มต้น = {go.MODEL_MENU[0][0]}")

# 9. bring_up() ต้องเปิด worker ทันทีที่เช่าสำเร็จ — ไม่ผูกกับผลของ smoke test
#    เจอสด 23 ก.ย. 69: smoke สะดุดครั้งเดียว (เน็ตกระตุก/โมเดลตอบช้ารอบแรกหลังโหลดเสร็จ)
#    ทำให้ bring_up() เก่า `return` ก่อนถึง start_worker() ทั้งที่การ์ด+โมเดลพร้อมจริง
#    (ยืนยันจาก wait_healthy() ข้างใน presentation.py มาก่อนหน้านั้นแล้ว) —
#    ผู้ใช้ยิงงานจากเว็บแล้วค้างเงียบในคิวเพราะไม่มี worker.py รับ
import subprocess as _sp  # noqa: E402


def _run_bring_up(rent_ok, smoke_ok, remote_ok=True, local_running=False):
    """คืน (ลำดับคำสั่งที่ยิงไป presentation.py, จำนวนครั้งที่เปิดหน้าต่างรับงานบนคอม)"""
    calls, started = [], []
    saved = (go.run, go.clear_stuck_card, go.pick_model, go.start_worker,
             go.local_worker_running)

    def fake_run(cmd):
        calls.append(list(cmd))
        ok = {"up": rent_ok, "smoke": smoke_ok, "worker-up": remote_ok}.get(cmd[0], True)
        return _sp.CompletedProcess(cmd, 0 if ok else 1)

    go.run, go.clear_stuck_card, go.pick_model, go.start_worker, go.local_worker_running = (
        fake_run, (lambda keep=None: True), (lambda: "destrier"),
        (lambda: started.append(True)), (lambda: local_running))
    try:
        go.bring_up(None)
    finally:
        (go.run, go.clear_stuck_card, go.pick_model, go.start_worker,
         go.local_worker_running) = saved
    return [c[0] for c in calls], len(started)


_c, _n = _run_bring_up(rent_ok=True, smoke_ok=False)
assert _c == ["up", "smoke", "worker-up"] and _n == 0, (_c, _n)
print("OK  smoke ล้มไม่ปิดกั้นการเปิด worker (เช่าสำเร็จแล้ว = เปิดเสมอ — บั๊กที่แก้ 23 ก.ย.)")

_c, _n = _run_bring_up(rent_ok=False, smoke_ok=False)
assert _c == ["up"] and _n == 0, f"เช่าล้มต้องไม่ไปถึง smoke/ไม่เปิด worker เลย ได้ {_c} เปิด {_n}"
print("OK  เช่าไม่สำเร็จ -> ไม่เปิด worker และไม่ไปถึง smoke")

_c, _n = _run_bring_up(rent_ok=True, smoke_ok=True)
assert _c == ["up", "smoke", "worker-up"] and _n == 0, (_c, _n)
print("OK  ทางปกติ -> เปิดตัวรับงานบนการ์ด (แผน A) ไม่เปิดหน้าต่างบนคอมซ้อน")

# แผน A พัง -> ต้องสั่งหยุดตัวบนการ์ดก่อน แล้วค่อยถอยไปเปิดบนคอม (ห้ามมีสองตัวยิงโมเดลพร้อมกัน)
_c, _n = _run_bring_up(rent_ok=True, smoke_ok=True, remote_ok=False)
assert _c == ["up", "smoke", "worker-up", "worker-down"] and _n == 1, (_c, _n)
print("OK  เปิดบนการ์ดไม่สำเร็จ -> หยุดตัวบนการ์ดก่อน แล้วถอยไปหน้าต่างบนคอม 1 ตัว")

# มีหน้าต่างรับงานบนคอมค้างอยู่แล้ว (ลืมปิดจากรอบก่อน) -> ใช้ตัวนั้น ไม่เปิดบนการ์ดซ้อน
_c, _n = _run_bring_up(rent_ok=True, smoke_ok=True, local_running=True)
assert _c == ["up", "smoke"] and _n == 0, (_c, _n)
print("OK  มีตัวรับงานบนคอมอยู่แล้ว -> ไม่เปิดตัวที่สองซ้อน")

# 10. cmd_smoke ต้องทนสะดุดได้ 1-2 ครั้งก่อนยอมแพ้ (ไม่ใช่ throw รอบเดียวจบ)
_src = Path(__file__).with_name("presentation.py").read_text(encoding="utf-8")
_smoke_body = _src[_src.index("def cmd_smoke("):_src.index("def cmd_down(")]
assert "for attempt in range(1, 4)" in _smoke_body, (
    "cmd_smoke ต้อง retry ก่อนยอมแพ้ — ยิงครั้งเดียวแล้ว throw เจอเน็ตกระตุกทีเดียวก็ล้มฟรี")
print("OK  cmd_smoke ทนการสะดุดครั้งเดียวได้ (retry ก่อนยอมแพ้)")

print(f"\nOK — ตรวจ {len(P.MODELS)} preset ผ่านทุกข้อ")
