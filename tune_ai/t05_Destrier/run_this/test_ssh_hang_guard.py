#!/usr/bin/env python3
"""Self-check ของด่านกัน ssh ค้างเงียบ — รัน: python test_ssh_hang_guard.py

ผูกกับความพังที่เกิดขึ้นจริง 23 ก.ย. 2026 ระหว่างเตรียมพรีเซนต์:
ssh ที่สืบ stdin ของคอนโซลมาใช้ ค้างที่ `mkdir -p /workspace` **10 นาทีกว่า**
โดยหน้าจอนิ่งสนิทไม่มีข้อความอะไรเลย (capture_output กลืน stderr ไว้หมด)
คำสั่งเดียวกันเป๊ะรันมือผ่านใน 1 วินาที ต่างกันแค่ `< /dev/null`

สามข้อนี้จึงเป็นด่านกันถอยหลัง ไม่ใช่เทสต์ตามพิธี
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import presentation as P  # noqa: E402

ST = {"ssh_host": "example.invalid", "ssh_port": 1234}

# 1) sh() ต้องตัด stdin ทิ้งเสมอ — นี่คือต้นเหตุของการค้าง
calls = []
real_run = subprocess.run
subprocess.run = lambda cmd, **kw: (calls.append(kw), real_run([sys.executable, "-c", ""], **kw))[1]
try:
    P.sh(["ignored"])
    assert calls[-1].get("stdin") is subprocess.DEVNULL, \
        f"sh() ไม่ได้ปิด stdin — ssh จะกลับไปค้างเงียบอีก (ได้ {calls[-1].get('stdin')!r})"

    # 2) แต่ห้ามทับผู้เรียกที่ส่ง input= มาเอง ไม่งั้น subprocess โยน ValueError ทันที
    #    (cmd_down ส่ง input="y\n" ให้ vastai destroy — ถ้าพังคือคืนการ์ดไม่ได้)
    P.sh(["ignored"], input="y\n")
    assert "stdin" not in calls[-1], \
        "sh() ไปใส่ stdin ทับกรณีที่มี input= — vastai destroy จะพังด้วย ValueError"
    assert calls[-1].get("input") == "y\n"
finally:
    subprocess.run = real_run

# 3) ssh_base ต้องมี BatchMode + ConnectTimeout — ให้ auth ที่มีปัญหาล้มทันที
#    แทนที่จะขึ้น prompt ถามรหัสผ่านที่ไม่มีใครเห็นแล้วค้างยาว
base = P.ssh_base(ST)
for opt in ("BatchMode=yes", "ConnectTimeout=15", "StrictHostKeyChecking=accept-new"):
    assert opt in base, f"ssh_base ขาด {opt} — เปิดช่องให้ค้างเงียบอีกรอบ"

# 4) คำสั่งสั่งรันเซิร์ฟเวอร์ต้องใช้ setsid --fork ไม่ใช่ setsid เปล่า
#    `&` ท้ายคำสั่งทำให้ทั้งชุดอยู่ใน subshell ที่เป็นหัวหน้ากลุ่มโปรเซสอยู่แล้ว
#    setsid เปล่าจะ exec ทับตัวเองแทนที่จะ fork → subshell กลายเป็นเซิร์ฟเวอร์เสียเอง
#    แล้วกอด fd ของ ssh ไว้ = ssh ไม่มีวันจบ = start_tunnel() ไม่ได้รัน
#    วัดบนเครื่องจริง 23 ก.ย.: ไม่มี --fork ค้างเกิน 30 วิ · มี --fork จบใน 4 วิ
src = Path(__file__).resolve().parent.joinpath("presentation.py").read_text(encoding="utf-8")
assert "setsid --fork nohup" in src,     "คำสั่งสั่งรันเซิร์ฟเวอร์ขาด --fork — ssh จะค้างจนกว่าโมเดลจะตาย"
assert "setsid nohup" not in src.replace("setsid --fork nohup", ""),     "ยังมี setsid เปล่าหลงเหลืออยู่"

print("ok — ด่านกัน ssh ค้างเงียบครบทั้ง 4 ข้อ")
