#!/usr/bin/env python3
"""go.py — เมนูเดียวจบสำหรับวันพรีเซนต์ ไม่ต้องจำคำสั่ง ไม่ต้องพิมพ์ path

    ดับเบิลคลิก GO.bat   (หรือ python go.py)

ทำไมมีไฟล์นี้: คู่มือเดิมให้พิมพ์คำสั่งเอง แล้วเจอปัญหาจริง 2 รอบ —
คัดลอกจาก PDF ทำให้สระไทยเพี้ยน `cd` ไม่เจอโฟลเดอร์, และคัดลอกคำอธิบายท้ายบรรทัด
ติดมาด้วยจน argparse ตาย · เมนูตัวเลขไม่มีทางพิมพ์ผิดได้เลย

หน้าแรกโชว์แค่ 4 ข้อที่ใช้จริง — เครื่องมือซ่อมยุบไว้ข้อ 9 เพราะจะแตะก็ต่อเมื่อมีอะไรพัง
เห็น 8 ทางเลือกพร้อมกันตอนกำลังจะขึ้นเวทีมันหนักเกินจำเป็น
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
STATE = HERE / "presentation_state.json"


def run(args, capture=False):
    """เรียก presentation.py — cwd ล็อกที่โฟลเดอร์นี้เสมอ ไม่ว่าจะถูกเรียกจากไหน"""
    cmd = [PY, str(HERE / "presentation.py"), *args]
    if capture:
        return subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    return subprocess.run(cmd, cwd=HERE)


def current_instance():
    """id ของการ์ดที่เปิดอยู่ **จริง** (None ถ้าไม่มี)

    เช็คกับ vast.ai เสมอ ไม่เชื่อไฟล์ state อย่างเดียว — เจอจริง 31 ส.ค.: คืนการ์ดไป
    แล้วแต่ state ยังค้าง id เก่า พอกดเปิดใหม่ระบบเลยหลงคิดว่ามีของค้างและพยายาม
    คืนซ้ำ · ถ้าไม่ตรงกันให้ลบ state ทิ้ง เพราะความจริงอยู่ที่ vast.ai ไม่ใช่ไฟล์เรา"""
    if not STATE.exists():
        return None
    try:
        iid = json.loads(STATE.read_text(encoding="utf-8")).get("instance_id")
    except Exception:
        return None
    if not iid:
        return None
    r = subprocess.run(["vastai", "show", "instances", "--raw"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return iid          # ถามไม่ได้ (เน็ตล่ม?) — เชื่อ state ไว้ก่อน ปลอดภัยกว่า
    try:
        alive = {i.get("id") for i in json.loads(r.stdout or "[]")}
    except Exception:
        return iid
    if iid in alive:
        return iid
    print(f"  (ล้าง state เก่า — instance {iid} ถูกคืนไปแล้ว ไม่มีอยู่จริง)")
    STATE.unlink(missing_ok=True)
    return None


# เมนูเลือกรุ่น — ลำดับในนี้คือลำดับที่โชว์ ตัวแรกคือค่าเริ่มต้น (Enter เฉยๆ)
# ⚠️ ทุกตัวต้องมีอยู่จริงใน presentation.py MODELS — มี assert กันตกหล่นท้ายไฟล์
MODEL_MENU = [
    ("destrier", "รุ่นที่ใช้อยู่จริงตอนนี้ — ช้า (~4-5 นาที/หน้า) แต่พิสูจน์แล้วว่าผลถูก"),
    ("destrier-sglang", "เร็วกว่ามาก ⚠️ ต้อง merge โมเดลก่อน (ดู README) ยังไม่เคยรันจริง"),
    ("destrier-vllm", "เร็วกว่ามาก ⚠️ เงื่อนไขเดียวกับข้างบน"),
    ("t03", "รุ่นเก่า เก็บไว้เทียบ"),
]


def pick_model():
    """เลือกรุ่นโมเดล — ตัวแรกในเมนูเป็นค่าเริ่มต้น

    เคยพลาดจริง 31 ส.ค.: เมนูเรียก `up` เฉยๆ แล้วได้ค่า default ของ presentation.py
    ซึ่งคือ t03 (รุ่นเก่า) โดยไม่มีใครรู้จนเห็นชื่อ adapter ในคำสั่ง ssh
    ตอนนี้จึงส่ง --model ทุกครั้ง ไม่พึ่ง default ของอีกไฟล์"""
    print("\n  เลือกรุ่นโมเดล")
    for i, (name, note) in enumerate(MODEL_MENU, 1):
        star = "  (ค่าเริ่มต้น)" if i == 1 else ""
        print(f"    {i}  {name:17s} {note}{star}")
    print()
    c = input(f"  เลือก [1]: ").strip()
    if c.isdigit() and 1 <= int(c) <= len(MODEL_MENU):
        return MODEL_MENU[int(c) - 1][0]
    return MODEL_MENU[0][0]


# ข้อความชุดเดียวใช้ทั้งทางเช่าเองและทางอัตโนมัติ — เคยเป็นสองก๊อปปี้ที่เหมือนกันคำต่อคำ
# ถ้าแก้ที่เดียวลืมอีกที่ จะเพี้ยนแบบไม่มีใครเห็น · ต่างกันแค่บรรทัดบอกว่าตัวรับงานอยู่ที่ไหน
READY_TAIL = """   • เปิดเว็บ → Drawing Intelligence → อัปโหลด PDF → กดปุ่ม "ถอดแบบด้วย Destrier"
   • กดทีละงาน รอให้เสร็จก่อนกดใหม่เสมอ

   จบงานแล้วกลับมาที่เมนูนี้ เลือกข้อ 4 เพื่อคืนการ์ด (สำคัญมาก ไม่งั้นเงินเดิน)
"""
READY = ("\n✅ พร้อมสาธิตแล้ว\n\n"
         "   • หน้าต่างใหม่ที่เพิ่งเปิด = ตัวรับงาน ห้ามปิดตลอดช่วงสาธิต\n" + READY_TAIL)
READY_REMOTE = ("\n✅ พร้อมสาธิตแล้ว — ตัวรับงานรันอยู่บนการ์ดเช่า (แผน A)\n\n"
                "   • ไม่มีหน้าต่างรับงานบนคอมนี้ เน็ตคอมหลุดหรือปิดเมนูนี้ งานที่รันอยู่ก็ไม่สะดุด\n"
                "   • ไม่มีเสียงตอนงานเสร็จ — ดูความคืบหน้าที่หน้าเว็บ หรือเมนู 9 → 8 ดู log\n"
                + READY_TAIL)


def start_worker():
    """หน้าต่างแยกที่ต้องเปิดค้างไว้ — ปิดเมื่อไหร่ เว็บกดปุ่มแล้วงานจะค้างในคิวทันที"""
    subprocess.Popen(["cmd", "/c", "start", "cmd", "/k",
                      f'cd /d "{HERE}" && "{PY}" worker.py'], shell=False)


def local_worker_running():
    """มีหน้าต่างรับงานบนคอมนี้เปิดค้างอยู่ไหม (เช่นลืมปิดจากรอบเช่าก่อน)

    ต้องรู้ก่อนเปิดตัวบนการ์ด เพราะตัวรับงานสองตัวจะคว้าคนละงานแล้วยิงโมเดลพร้อมกัน —
    ตัวเสิร์ฟ Unsloth รับทีละคำขอ ยิงซ้อนแล้วค้างมาแล้วเกิน 7 ชม. (MISTAKES.md บันทึกไว้)
    ถามไม่ได้ (ไม่มี PowerShell) = ถือว่าไม่มี ไม่ขวางการทำงาน"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" "
             "| ForEach-Object CommandLine"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except Exception:
        return False
    return any("worker.py" in line and "--release-stuck" not in line
               for line in (r.stdout or "").splitlines())


def start_worker_auto():
    """เปิดตัวรับงาน — แผน A ก่อน (รันบนการ์ดเช่า) ไม่สำเร็จค่อยถอยไปหน้าต่างบนคอมนี้แบบเดิม

    ถอยทุกครั้งต้องสั่งหยุดตัวบนการ์ดก่อน: ถ้ามันติดขึ้นมาจริงแต่รายงานพลาด (ssh หลุดตอนท้าย)
    จะกลายเป็นสองตัวยิงโมเดลพร้อมกัน — เหตุผลเดียวกับ local_worker_running()"""
    if local_worker_running():
        print("\n(มีหน้าต่างรับงานบนคอมนี้เปิดอยู่แล้ว — ใช้ตัวนั้นต่อ ไม่เปิดบนการ์ดซ้อน"
              "\n อยากย้ายไปรันบนการ์ด: ปิดหน้าต่างนั้นก่อน แล้วเมนู 9 → 3)")
        print(READY)
        return
    print("\n▶ เปิดตัวรับงานบนการ์ดเช่า (แผน A)...")
    if run(["worker-up"]).returncode == 0:
        print(READY_REMOTE)
        return
    print("\n⚠️ เปิดบนการ์ดไม่สำเร็จ — ถอยไปเปิดหน้าต่างรับงานบนคอมนี้แทน (แบบเดิม)")
    run(["worker-down"])
    start_worker()
    print(READY)


def clear_stuck_card(keep=None):
    """ถ้ามีการ์ดค้างอยู่ ถามว่าจะคืนก่อนไหม — คืน True เมื่อพร้อมไปต่อ

    keep = instance id ที่กำลังจะต่อด้วย · ถ้าตรงกับตัวที่ค้างอยู่ แปลว่ากำลังต่อกลับเข้า
    **การ์ดตัวเดิมของตัวเอง** ไม่ใช่การเปลี่ยนเครื่อง — ข้ามไปเลย ไม่ต้องถาม
    เจอจริง 23 ก.ย.: ต่อรอบแรกล้มเพราะ ssh ไปทางพร็อกซีที่เครื่อง Jupyter ไม่รองรับ
    พอกดข้อ 1 ซ้ำด้วย id เดิม มันดันเสนอให้คืนการ์ดตัวเองทิ้ง = จ่ายค่าเช่าใหม่ฟรีๆ"""
    iid = current_instance()
    if not iid:
        return True
    if keep and str(keep) == str(iid):
        print(f"\n(ต่อกลับเข้าการ์ดเดิม instance {iid} ที่เปิดอยู่แล้ว — ไม่ต้องคืน)")
        return True
    print(f"\n⚠️  มีการ์ดค้างอยู่ (instance {iid}) — ถ้าไม่คืนก่อน ระบบจะเปิดใหม่ไม่ได้")
    if input("   คืนการ์ดเดิมแล้วเริ่มใหม่เลยไหม? [y/N] ").strip().lower() != "y":
        print("   ยกเลิก — ถ้าการ์ดเดิมยังใช้ได้อยู่ ไปข้อ 9 → เปิดตัวรับงาน ได้เลย")
        return False
    run(["down"])
    return True


def bring_up(instance_id=None):
    """เปิดให้พร้อมสาธิต — ใช้ร่วมกันทั้งสองทาง ต่างกันแค่คำสั่งที่ยิงไปบรรทัดเดียว

    instance_id = None   → ให้สคริปต์หาเครื่องถูกสุดแล้วเช่าให้เอง (ข้อ 3)
    instance_id = "1234" → ต่อกับเครื่องที่ไปเช่าเองจากหน้าเว็บ vast.ai (ข้อ 1)

    ที่เหลือ (เลือกรุ่น → ทดสอบ → เปิดตัวรับงาน) เหมือนกันทุกขั้น"""
    if not clear_stuck_card(keep=instance_id):
        return

    model = pick_model()
    if instance_id:
        print(f"\n▶ กำลังต่อกับ instance {instance_id} [{model}] — ใช้เวลา 20-45 นาที "
              f"(ส่วนใหญ่รอโหลดโมเดล 70GB)")
        cmd = ["attach", instance_id, "--model", model]
    else:
        print(f"\n▶ กำลังเช่าการ์ด + เปิดโมเดล [{model}] — ใช้เวลา 20-45 นาที "
              f"(ส่วนใหญ่รอโหลดโมเดล 70GB)")
        # เพดาน $2/ชม. (มะขามเคาะ 23 ก.ย.) — 1.5 ต่ำเกินจริง วันที่การ์ดขาดตลาด
        # RTX PRO 6000 ถูกสุดยังอยู่ที่ $1.57 แล้วสคริปต์ปฏิเสธทิ้งทั้งที่ยอมจ่ายไหว
        cmd = ["up", "--model", model, "--yes", "--max-price", "2.0"]
    print("  อย่าปิดหน้าต่างนี้ระหว่างรอ\n")

    if run(cmd).returncode != 0:
        print("\n❌ ไม่สำเร็จ — ดูข้อความข้างบน")
        print("   เลือกข้อ 2 ดูก่อนว่าการ์ดขึ้นมาหรือยัง")
        print("   ถ้าการ์ด**ขึ้นแล้ว** ไม่ต้องเช่าใหม่ — ไปข้อ 9 ทำต่อจากตรงนั้นได้เลย")
        return

    # smoke แค่ยิงคุยกับโมเดลอีกรอบเพื่อความมั่นใจ — **ไม่ใช่** ด่านตัดสินว่าเปิด worker ได้
    # ไหม เพราะ `run(cmd)` ที่ผ่านมาแล้วข้างบนหมายความว่า wait_healthy() ข้างใน
    # presentation.py ยืนยันแล้วว่าโมเดลตอบจริง (เช็คที่แน่นอนกว่า) — เดิมโค้ดผูกสองเรื่องนี้
    # ไว้ด้วยกัน พอ smoke สะดุดแค่ครั้งเดียว (เน็ตกระตุก/โมเดลตอบช้ารอบแรกหลังโหลดเสร็จ)
    # ก็ `return` ข้าม start_worker() ไปเลย ทั้งที่โมเดลพร้อมจริง — เจอสด 23 ก.ย. 69:
    # การ์ดพร้อมสมบูรณ์แต่ worker.py ไม่เคยถูกเปิด งานที่ผู้ใช้ยิงจากเว็บค้างเงียบในคิว
    print("\n▶ ทดสอบว่าโมเดลตอบจริง...")
    smoke_ok = run(["smoke"]).returncode == 0
    if not smoke_ok:
        print("\n⚠️ smoke ทดสอบไม่ผ่าน — แต่การ์ด+โมเดลผ่านการเช็คหลักมาแล้ว "
              "เปิด worker ให้ต่อไปตามปกติ")
        print("   ก่อนสาธิตสด ลองยิงงานจริงจากเว็บ 1 รอบเทียบดูก่อนเชื่อเต็มที่")

    start_worker_auto()


def do_attach():
    """ข้อ 1 — ไปเลือก+เช่าเครื่องเองจากหน้าเว็บ แล้วเอา instance ID มาต่อที่นี่"""
    print("\n  หา instance ID ได้จากหน้าเว็บ vast.ai → Instances → คอลัมน์ ID")
    raw = input("  พิมพ์ instance ID แล้ว Enter: ").strip()
    if not raw.isdigit():
        print("\n❌ ต้องเป็นตัวเลขเท่านั้น")
        return
    bring_up(raw)


def do_stop():
    """คืนการ์ด + เก็บคำตัดสินของมะขามว่าเครื่องนี้ใช้ได้หรือไม่

    ถามตรงนี้เพราะเป็นนาทีเดียวที่เขายังจำได้ว่าเครื่องนี้เป็นยังไง — ถ้าไม่ถามตอนนี้
    ความรู้นั้นหายไปพร้อมหน้าต่าง แล้วรอบหน้าก็มีสิทธิ์สุ่มได้เครื่องเดิมอีก"""
    args = ["down"]
    if not current_instance():
        print("\n(ไม่มีการ์ดค้างใน state — เช็คซ้ำให้อีกที)")
    else:
        ans = input("\n  เครื่องนี้มีปัญหาไหม (เน็ตช้า/ต่อไม่ติด/โมเดลไม่ขึ้น)? [y/N] ")
        if ans.strip().lower() == "y":
            why = input("  สั้นๆ ว่าเป็นอะไร: ").strip() or "มีปัญหา (ไม่ได้ระบุ)"
            args += ["--bad", why]
            print("  จะจำไว้ ไม่เช่าเครื่องนี้ซ้ำอีก")
    run(args)
    print("\n✅ ถ้าเห็นว่าเหลือ 0 instance = คืนเรียบร้อย ปิดหน้าต่างรับงานได้เลย")


def do_worker():
    """เปิดตัวรับงานใหม่ — ครึ่งหลังของข้อ 1/3 สำหรับกรณีการ์ด+โมเดลพร้อมอยู่แล้ว
    (เช่นเปิดค้างไว้สะดุดกลางทางแต่การ์ดรอด, ตัวรับงานดับ, หรือเผลอปิดหน้าต่างไป)
    กดซ้ำได้ปลอดภัย — ทั้งบนการ์ดและบนคอมมีตัวเช็คไม่ให้เปิดซ้อน"""
    if not current_instance():
        print("\n❌ ยังไม่มีการ์ดเปิดอยู่ — เลือกข้อ 1 หรือ 3 ก่อน")
        return
    start_worker_auto()


def release_stuck():
    """ปลดงานถอดแบบที่ค้างให้ทำต่อได้ทันที — ดูคำอธิบายเต็มใน worker.py release_stuck_jobs()
    ย่อ: worker ปิดกลางทาง → งานค้างสถานะ processing → worker ตัวใหม่คว้าไม่ได้เพราะมันหาแต่
    งาน pending → ต้องรอ 45 นาทีให้ requeue_stale ปลดเอง · ปุ่มนี้ข้ามการรอนั้น
    ผลที่ทำไปแล้วไม่หาย มี checkpoint ครบ แค่ไปบอกให้มีคนหยิบมาทำต่อ"""
    subprocess.run([PY, str(HERE / "worker.py"), "--release-stuck"], cwd=HERE)


def test_sound():
    """ให้ฟังทั้งสามเสียงก่อนใช้จริง — จะได้รู้ว่าลำโพงเปิดอยู่และแยกเสียงออกจากกันได้
    (ถ้าไม่ได้ยิน แล้วเดินออกจากจอไป ก็เท่ากับไม่มีฟีเจอร์นี้)"""
    subprocess.run([PY, str(HERE / "notify.py")], cwd=HERE)
    print("\n   ไม่อยากให้มีเสียง (เช่นตอนขึ้นเวที): พิมพ์  set PURSON_QUIET=1  ก่อนเปิดเมนู")


def clear_blacklist():
    """ล้างรายชื่อเครื่องที่เคยเจ๊ง — ถามก่อนเพราะมันคือความรู้ที่สะสมมาจากการเสียเวลาจริง
    ลบแล้วรอบหน้ามีสิทธิ์วนกลับไปเจอเครื่องเดิมใหม่ทั้งหมด"""
    run(["blacklist"])
    if input("\n  ล้างทั้งหมดจริงไหม? [y/N] ").strip().lower() != "y":
        print("  (ไม่ล้าง)")
        return
    run(["blacklist", "clear"])


REPAIR_MENU = """
  ── เครื่องมือซ่อม ──────────────────────────
  1  ทดสอบโมเดล        (ยิง 1 ครั้ง ดูว่าตอบจริง)
  2  ต่อ tunnel ใหม่    (ใช้เมื่อเชื่อมต่อหลุดกลางทาง)
  3  เปิดตัวรับงาน      (การ์ดเปิดอยู่แล้วแต่ตัวรับงานดับ/หน้าต่างรับงานปิดไป)
  4  ปลดงานถอดแบบที่ค้าง (ตัวรับงานดับตอนกำลังถอดแบบ แล้วงานค้างไม่มีใครทำต่อ)
  5  ดูเครื่องที่ใช้ไม่ได้   (บัญชีดำ — สคริปต์จะไม่เช่าเครื่องพวกนี้ซ้ำ)
  6  ล้างบัญชีดำ            (เผื่อโฮสต์ซ่อมแล้ว อยากให้กลับมาเลือกได้อีก)
  7  ทดสอบเสียง            (ฟังว่าเสียงแจ้งเตือนดังจริงไหม ก่อนเดินไปทำอย่างอื่น)
  8  ดู log ตัวรับงานบนการ์ด (แผน A — ไม่มีหน้าต่างให้ดู เลยดูตรงนี้แทน)
  0  กลับเมนูหลัก
"""


def repair_tools():
    """ของที่จะแตะก็ต่อเมื่อมีอะไรพัง — แยกออกจากหน้าแรกเพื่อไม่ให้รก
    ไม่ได้ลบทิ้ง เพราะถ้า tunnel หลุดกลางสาธิตแล้วไม่มีปุ่มนี้ ต้องไปพิมพ์คำสั่งเอง
    ซึ่งคือปัญหาเดิมที่ go.py เกิดมาเพื่อแก้"""
    tools = {"1": lambda: run(["smoke"]), "2": lambda: run(["tunnel"]), "3": do_worker,
             "4": release_stuck, "5": lambda: run(["blacklist"]), "6": clear_blacklist,
             "7": test_sound, "8": lambda: run(["worker-log"])}
    while True:
        print(REPAIR_MENU)
        c = input("  เลือกข้อ: ").strip()
        if c == "0":
            return
        act = tools.get(c)
        if not act:
            print("\n❌ ไม่มีข้อนี้ พิมพ์เลข 0-8 เท่านั้น")
            continue
        try:
            act()
        except KeyboardInterrupt:
            print("\n(ยกเลิกคำสั่งนี้)")
        input("\nกด Enter เพื่อกลับไปเมนูซ่อม...")


MENU = """
╔══════════════════════════════════════════════╗
║        Purson — เมนูวันพรีเซนต์               ║
╚══════════════════════════════════════════════╝

  1  เชื่อมกับการ์ดที่เช่าเอง  (เลือก+เช่าเครื่องเองที่ vast.ai แล้วเอา instance ID มาใส่)
  2  เช็คสถานะ                (การ์ดยังเปิดอยู่ไหม โมเดลตอบไหม)
  3  เช่าอัตโนมัติทั้งหมด      (ให้สคริปต์หาเครื่องถูกสุด + เปิดโมเดล + เปิดตัวรับงาน ให้เอง)
  4  คืนการ์ด                  (จบงานแล้วต้องกดทุกครั้ง ไม่งั้นเงินเดิน)

  9  เครื่องมือซ่อม            (ทดสอบโมเดล / tunnel / เปิดตัวรับงาน / ปลดงานถอดแบบที่ค้าง)
  0  ออก
"""


def main():
    actions = {
        "1": do_attach,
        "2": lambda: run(["status"]),
        "3": bring_up,
        "4": do_stop,
        "9": repair_tools,
    }
    while True:
        print(MENU)
        iid = current_instance()
        if iid:
            model = "?"
            try:
                model = json.loads(STATE.read_text(encoding="utf-8")).get("model", "?")
            except Exception:
                pass
            print(f"  สถานะล่าสุด: การ์ดเปิดอยู่ · รุ่น {model} · instance {iid}")
            print("  → การ์ดเปิดอยู่แล้ว ถ้าเพิ่งพังกลางทาง ไม่ต้องเช่าใหม่ ไปข้อ 9 ทำต่อได้เลย")
        else:
            print("  สถานะล่าสุด: ยังไม่ได้เปิดการ์ด")
        choice = input("\nเลือกข้อ (พิมพ์เลขแล้ว Enter): ").strip()
        if choice == "0":
            if current_instance():
                print("\n⚠️  การ์ดยังเปิดอยู่ — เงินเดินต่อไปเรื่อยๆ นะ (เลือกข้อ 4 ถ้าจะคืน)")
            print("จบการทำงาน")
            return
        act = actions.get(choice)
        if not act:
            print("\n❌ ไม่มีข้อนี้ พิมพ์ 1-4, 9 หรือ 0 เท่านั้น")
            continue
        try:
            act()
        except KeyboardInterrupt:
            print("\n(ยกเลิกคำสั่งนี้ — กลับสู่เมนู)")
        input("\nกด Enter เพื่อกลับไปเมนู...")


def _check_model_menu():
    """กันชื่อรุ่นในเมนูหลุดจาก presentation.py — ถ้าตกหล่นจะรู้ตอนเปิดเมนู
    ไม่ใช่ตอนกดเปิดการ์ดไปแล้วครึ่งทาง (คอมเมนต์เหนือ MODEL_MENU สัญญาไว้ แต่เดิมไม่มีจริง)"""
    try:
        import presentation
    except Exception as e:
        print(f"⚠️  อ่าน presentation.py ไม่ได้ ({type(e).__name__}) — ข้ามการตรวจชื่อรุ่น")
        return
    missing = [n for n, _ in MODEL_MENU if n not in presentation.MODELS]
    if missing:
        print(f"⚠️  รุ่นในเมนูไม่มีอยู่จริงใน presentation.py: {', '.join(missing)}")
        print("   เลือกข้อนั้นแล้วจะพังกลางทาง — แก้ MODEL_MENU ใน go.py ก่อนใช้งาน\n")


if __name__ == "__main__":
    try:
        _check_model_menu()
        main()
    except (KeyboardInterrupt, EOFError):
        # EOFError = ถูกเรียกแบบไม่มีคนพิมพ์ (ท่อ/สคริปต์) — จบเงียบๆ ดีกว่าโยน traceback ใส่หน้า
        print("\nจบการทำงาน")
