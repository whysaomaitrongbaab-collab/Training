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

print(f"\nOK — ตรวจ {len(P.MODELS)} preset ผ่านทุกข้อ")
