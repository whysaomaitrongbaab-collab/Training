#!/usr/bin/env python3
"""go.py — เมนูเดียวจบสำหรับวันพรีเซนต์ ไม่ต้องจำคำสั่ง ไม่ต้องพิมพ์ path

    ดับเบิลคลิก GO.bat   (หรือ python go.py)

ทำไมมีไฟล์นี้: คู่มือเดิมให้พิมพ์คำสั่งเอง แล้วเจอปัญหาจริง 2 รอบ —
คัดลอกจาก PDF ทำให้สระไทยเพี้ยน `cd` ไม่เจอโฟลเดอร์, และคัดลอกคำอธิบายท้ายบรรทัด
ติดมาด้วยจน argparse ตาย · เมนูตัวเลขไม่มีทางพิมพ์ผิดได้เลย
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


def pick_model():
    """เลือกรุ่นโมเดล — destrier เป็นค่าเริ่มต้น (รุ่นที่ทีมใช้อยู่จริงตอนนี้)

    เคยพลาดจริง 31 ส.ค.: เมนูเรียก `up` เฉยๆ แล้วได้ค่า default ของ presentation.py
    ซึ่งคือ t03 (รุ่นเก่า) โดยไม่มีใครรู้จนเห็นชื่อ adapter ในคำสั่ง ssh
    ตอนนี้จึงส่ง --model ทุกครั้ง ไม่พึ่ง default ของอีกไฟล์"""
    print("""
  เลือกรุ่นโมเดล
    1  destrier  (ค่าเริ่มต้น — รุ่นที่เราใช้อยู่ตอนนี้)
    2  t03       (รุ่นเก่า เก็บไว้เทียบ)
""")
    return "t03" if input("  เลือก [1]: ").strip() == "2" else "destrier"


def do_start():
    iid = current_instance()
    if iid:
        print(f"\n⚠️  มีการ์ดค้างอยู่ (instance {iid}) — ถ้าไม่คืนก่อน ระบบจะเปิดใหม่ไม่ได้")
        if input("   คืนการ์ดเดิมแล้วเริ่มใหม่เลยไหม? [y/N] ").strip().lower() != "y":
            print("   ยกเลิก — ถ้าการ์ดเดิมยังใช้ได้อยู่ ให้ข้ามไปข้อ 4 (เปิดตัวรับงาน) ได้เลย")
            return
        run(["down"])

    model = pick_model()
    print(f"\n▶ กำลังเช่าการ์ด + เปิดโมเดล [{model}] — ใช้เวลา 20-45 นาที (ส่วนใหญ่รอโหลดโมเดล 70GB)")
    print("  อย่าปิดหน้าต่างนี้ระหว่างรอ\n")
    if run(["up", "--model", model, "--yes", "--max-price", "1.5"]).returncode != 0:
        print("\n❌ เปิดไม่สำเร็จ — ดูข้อความข้างบน · เลือกข้อ 2 เช็คสถานะได้")
        return

    print("\n▶ ทดสอบว่าโมเดลตอบจริง...")
    if run(["smoke"]).returncode != 0:
        print("\n⚠️ ทดสอบไม่ผ่าน — ยังไม่ควรไปสาธิตสด (เลือกข้อ 2 ดูสถานะ)")
        return

    print("\n▶ เปิดหน้าต่างรับงาน (worker) ให้อัตโนมัติ...")
    # หน้าต่างแยกที่ต้องเปิดค้างไว้ — ปิดเมื่อไหร่ เว็บกดปุ่มแล้วงานจะค้างในคิวทันที
    subprocess.Popen(["cmd", "/c", "start", "cmd", "/k",
                      f'cd /d "{HERE}" && "{PY}" worker.py'], shell=False)
    print("""
✅ พร้อมสาธิตแล้ว

   • หน้าต่างใหม่ที่เพิ่งเปิด = ตัวรับงาน ห้ามปิดตลอดช่วงสาธิต
   • เปิดเว็บ → Drawing Intelligence → อัปโหลด PDF → กดปุ่ม "ถอดแบบด้วย Purson"
   • กดทีละงาน รอให้เสร็จก่อนกดใหม่เสมอ

   จบงานแล้วกลับมาที่เมนูนี้ เลือกข้อ 3 เพื่อคืนการ์ด (สำคัญมาก ไม่งั้นเงินเดิน)
""")


def do_stop():
    if not current_instance():
        print("\n(ไม่มีการ์ดค้างใน state — เช็คซ้ำให้อีกที)")
    run(["down"])
    print("\n✅ ถ้าเห็นว่าเหลือ 0 instance = คืนเรียบร้อย ปิดหน้าต่างรับงานได้เลย")


MENU = """
╔══════════════════════════════════════════════╗
║        Purson — เมนูวันพรีเซนต์               ║
╚══════════════════════════════════════════════╝

  1  เปิดใช้งาน   (เช่าการ์ด + เปิดโมเดล + เปิดตัวรับงาน)
  2  เช็คสถานะ    (การ์ดยังเปิดอยู่ไหม โมเดลตอบไหม)
  3  คืนการ์ด     (จบงานแล้วต้องกดทุกครั้ง)
  4  ทดสอบโมเดล   (ยิง 1 ครั้ง ดูว่าตอบจริง)
  5  ต่อ tunnel ใหม่ (ถ้าหลุด)
  0  ออก
"""


def main():
    actions = {
        "1": do_start,
        "2": lambda: run(["status"]),
        "3": do_stop,
        "4": lambda: run(["smoke"]),
        "5": lambda: run(["tunnel"]),
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
        else:
            print("  สถานะล่าสุด: ยังไม่ได้เปิดการ์ด")
        choice = input("\nเลือกข้อ (พิมพ์เลขแล้ว Enter): ").strip()
        if choice == "0":
            if current_instance():
                print("\n⚠️  การ์ดยังเปิดอยู่ — เงินเดินต่อไปเรื่อยๆ นะ (เลือกข้อ 3 ถ้าจะคืน)")
            print("จบการทำงาน")
            return
        act = actions.get(choice)
        if not act:
            print("\n❌ ไม่มีข้อนี้ พิมพ์เลข 0-5 เท่านั้น")
            continue
        try:
            act()
        except KeyboardInterrupt:
            print("\n(ยกเลิกคำสั่งนี้ — กลับสู่เมนู)")
        input("\nกด Enter เพื่อกลับไปเมนู...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nจบการทำงาน")
