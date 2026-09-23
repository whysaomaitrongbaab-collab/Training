# -*- coding: utf-8 -*-
"""ตรวจเสียงบอกเหตุ — รัน: python test_notify.py  (เงียบ ไม่มีเสียงออกระหว่างตรวจ)

สองอย่างที่พังเงียบได้:
  · notify ทำให้งานหลักล้ม — ของแถวนี้เป็นของแถม ห้ามมีวันฆ่างานถอดแบบ 40 นาทีทิ้ง
  · มีคนลบบรรทัดเรียกออกตอนแก้อย่างอื่น แล้วไม่มีใครรู้จนกว่าจะยืนรอหน้าจอเปล่าๆ อีกรอบ
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

os.environ["PURSON_QUIET"] = "1"          # ห้ามส่งเสียงจริงตอนรันชุดตรวจ
import notify  # noqa: E402

FAILED = []


def check(label, cond):
    print(f"  {'OK ' if cond else '❌ '} {label}")
    if not cond:
        FAILED.append(label)


def test_never_raises():
    check("PURSON_QUIET=1 แล้วเงียบจริง (ไม่เรียก winsound)",
          all(fn() is None for fn in (notify.ready, notify.done, notify.fail)))

    # จำลองเครื่องที่ winsound พัง (ไม่ใช่ Windows / ไม่มีลำโพง / RuntimeError)
    os.environ.pop("PURSON_QUIET")
    real = sys.modules.get("winsound")
    sys.modules["winsound"] = None        # import winsound จะได้ None → โยน TypeError
    try:
        for name, fn in (("ready", notify.ready), ("done", notify.done), ("fail", notify.fail)):
            try:
                fn()
                ok = True
            except Exception as e:
                ok = False
                print(f"      ({name} โยน {type(e).__name__}: {e})")
            check(f"{name}() ไม่โยน exception แม้ winsound พัง", ok)
    finally:
        if real is not None:
            sys.modules["winsound"] = real
        else:
            sys.modules.pop("winsound", None)
        os.environ["PURSON_QUIET"] = "1"


def test_wired():
    """source guard — เรียกจริงต้องมีการ์ด/งานจริงถึงจะวิ่ง เทสต์ยูนิตแตะไม่ถึง"""
    pres = (HERE / "presentation.py").read_text(encoding="utf-8")
    work = (HERE / "worker.py").read_text(encoding="utf-8")

    ready_fn = pres[pres.index("def print_ready():"):pres.index("def ssh_alive(")]
    check("READY มีเสียง (จังหวะที่รอนานสุด 20-45 นาที)", "notify.ready()" in ready_fn)

    up = pres[pres.index("def cmd_up(a):"):pres.index("def cmd_attach(a):")]
    check("เช่าไม่รอดครบทุกเครื่อง = มีเสียงเรียกคนมาดู", "notify.fail()" in up)

    check("งานถอดแบบเสร็จ = มีเสียง", "notify.done()" in work)
    check("งานถอดแบบล้ม = มีเสียง (คนละเสียงกับเสร็จ)", "notify.fail()" in work)
    check("worker import notify จริง", "import notify" in work)


def main():
    print("ตรวจเสียงบอกเหตุ")
    test_never_raises()
    test_wired()
    if FAILED:
        sys.exit(f"\n❌ ไม่ผ่าน {len(FAILED)} ข้อ: {', '.join(FAILED)}")
    print("\nok — เสียงครบทุกจังหวะ และพังยังไงก็ไม่ลากงานหลักลงไปด้วย")


if __name__ == "__main__":
    main()
