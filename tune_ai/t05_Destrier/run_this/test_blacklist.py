# -*- coding: utf-8 -*-
"""ตรวจบัญชีดำเครื่องเช่า — รัน: python test_blacklist.py

ทำไมต้องมี: 23 ก.ย. 2026 เช่าเครื่องเจ๊งติดกัน 4 เครื่อง (ต่อ ssh ไม่ติด / เน็ต 6 MB/s)
เสียเวลาไปชั่วโมงกว่า เพราะทุกครั้งที่ล้ม สคริปต์แค่ sys.exit แล้วโยนงานกลับให้คนกดเมนูใหม่
และไม่มีใครจำว่าเครื่องไหนเคยเจ๊ง จึงสุ่มได้เครื่องเดิมซ้ำได้เรื่อยๆ

ชุดนี้ตรึงสองอย่างที่พังเงียบได้ง่าย:
  · ตรรกะการกรอง/จำ (ทดสอบจริง เรียกฟังก์ชันตรงๆ)
  · โครงสร้าง cmd_up ที่ต้องจับ BadMachine แล้วคืนเครื่อง+แบน+ไปเครื่องถัดไป
    (ถ้าใครลบ try/except ทิ้ง เทสต์ยูนิตธรรมดาจะไม่รู้เลย เพราะ path นั้นต้องมีการ์ดจริงถึงจะวิ่ง)
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import presentation as P  # noqa: E402

FAILED = []


def check(label, cond):
    if cond:
        print(f"  OK  {label}")
    else:
        print(f"  ❌  {label}")
        FAILED.append(label)


def with_temp_blacklist(fn):
    """กัน test เขียนทับ blacklist.json ตัวจริงของมะขาม"""
    real = P.BLACKLIST_FILE
    with tempfile.TemporaryDirectory() as d:
        P.BLACKLIST_FILE = Path(d) / "blacklist.json"
        try:
            fn()
        finally:
            P.BLACKLIST_FILE = real


def test_store():
    check("ไฟล์ยังไม่มี = ยังไม่เคยแบนใคร (ไม่ใช่ error)", P.load_blacklist() == {})

    P.blacklist_add(149000, "ต่อ ssh ไม่ติด", "RTX PRO 6000 S")
    bl = P.load_blacklist()
    check("จำได้ว่าแบนเครื่องไหน", "149000" in bl)
    check("จำเหตุผลไว้ด้วย", bl["149000"]["reason"] == "ต่อ ssh ไม่ติด")
    check("จำชื่อการ์ดไว้ด้วย", bl["149000"]["gpu"] == "RTX PRO 6000 S")
    check("มีวันเวลากำกับ", len(bl["149000"].get("at", "")) >= 10)

    # ไม่รู้ machine_id = ข้ามไปเงียบๆ ห้ามพัง (เกิดได้เมื่อ vastai ตอบไม่ครบ)
    P.blacklist_add(None, "อะไรสักอย่าง")
    check("ไม่รู้ machine_id ก็ไม่พัง และไม่เขียนขยะลงไฟล์", len(P.load_blacklist()) == 1)

    P.BLACKLIST_FILE.write_text("{ พัง ไม่ใช่ json", encoding="utf-8")
    check("ไฟล์พัง = ถือว่าไม่เคยแบนใคร ไม่ใช่เหตุให้หยุดทำงาน", P.load_blacklist() == {})


def test_filter():
    P.blacklist_add(149000, "เน็ตช้า")
    offers = [
        {"id": 1, "machine_id": 149000},      # int — ต้องโดนกรอง
        {"id": 2, "machine_id": "149000"},    # str — ต้องโดนกรองเหมือนกัน
        {"id": 3, "machine_id": 777},
        {"id": 4},                            # ไม่มี machine_id เลย — ปล่อยผ่าน ไม่เดา
    ]
    kept = [o["id"] for o in P.drop_blacklisted(offers)]
    check("กรองเครื่องที่แบนไว้ออก ไม่ว่า machine_id จะเป็น int หรือ str", kept == [3, 4])

    P.BLACKLIST_FILE.unlink()
    check("ไม่มีบัญชีดำ = คืน offer เดิมครบ", len(P.drop_blacklisted(offers)) == 4)


def test_ssh_endpoint_sentinel():
    """vast.ai ใช้เลขพอร์ตที่เป็นไปไม่ได้แทนรหัส "ยังไม่มีพอร์ตตรง" — เจอมาแล้ว 2 แบบ:
    65535 (ไม่เปิดพอร์ตตรงเลย) กับ -1 (เครื่องยังบูตไม่เสร็จ — เจอสด 23 ก.ย. 69 ตอน
    เครื่องอายุ 1 นาที) ถ้าไม่กรองออก จะเสียเวลา timeout ทุกรอบและบังหน้าว่าเครื่องเงียบ
    ทั้งที่ควรไปลองพร็อกซีเลย"""
    for bad_port in (65535, -1, 0):
        tried = []
        real_alive = P.ssh_alive
        P.ssh_alive = lambda h, p: (tried.append((h, p)), False)[1]
        try:
            P.pick_ssh_endpoint({"public_ipaddr": "1.2.3.4", "direct_port_start": bad_port,
                                 "ssh_host": "ssh2.vast.ai", "ssh_port": 32696})
        finally:
            P.ssh_alive = real_alive
        check(f"ไม่ลองทางตรงเมื่อ direct_port_start = {bad_port}",
              ("1.2.3.4", bad_port) not in tried)
        check(f"ยังลองพร็อกซีตามปกติ (port={bad_port})", ("ssh2.vast.ai", 32696) in tried)

    tried = []
    P.ssh_alive = lambda h, p: (tried.append((h, p)), False)[1]
    try:
        P.pick_ssh_endpoint({"public_ipaddr": "1.2.3.4", "direct_port_start": 22000,
                             "ssh_host": "ssh2.vast.ai", "ssh_port": 32696})
    finally:
        P.ssh_alive = real_alive
    check("พอร์ตตรงที่ใช้ได้จริงยังลองตามปกติ", ("1.2.3.4", 22000) in tried)


def test_cmd_up_structure():
    """source guard — path นี้ต้องมีการ์ดจริงถึงจะวิ่ง เทสต์ยูนิตจึงแตะไม่ถึง
    ตรวจว่าโครงยังอยู่ครบแทน (แบบเดียวกับ test_ssh_hang_guard.py)"""
    src = (HERE / "presentation.py").read_text(encoding="utf-8")
    up = src[src.index("def cmd_up(a):"):src.index("def cmd_attach(a):")]
    check("cmd_up กรองเครื่องที่แบนไว้ก่อนเลือก", "drop_blacklisted(" in up)
    check("cmd_up จับ BadMachine (ไม่ตายกลางทาง)", "except BadMachine" in up)
    check("cmd_up จำเครื่องที่เจ๊ง", "blacklist_add(" in up)
    check("cmd_up คืนเครื่องที่เจ๊งทิ้ง ไม่ปล่อยเผาเงิน", "scrap_instance(" in up)
    check("cmd_up ไปลองเครื่องถัดไปต่อ", "continue" in up)
    check("cmd_up จำ machine_id ลง state (ไว้ใช้ตอน down --bad)", '"machine_id"' in up)

    # ทางที่ล้มแล้วต้องกู้ได้ ห้ามกลับไปเป็น sys.exit อีก
    for fn_name, needle in (("wait_running", "เครื่องไม่ขึ้นใน 15 นาที"),
                            ("net_check", "ช้าผิดปกติ")):
        check(f"{fn_name} โยน BadMachine ไม่ใช่ sys.exit",
              needle not in src or "raise BadMachine" in src)


def test_dead_server_detection():
    """23 ก.ย. 69: ตัวโหลดของ HuggingFace (Xet) พังที่ 9.1/72 GB ตัวเสิร์ฟตายทั้ง process
    แต่หน้าจอยังขึ้น "ยังไม่พร้อม" ต่อไปอีก 20 นาทีเหมือนปกติทุกประการ — กับดักคลาสเดียวกับ
    ssh ค้างเงียบ: รอสิ่งที่ไม่มีวันมา โดยไม่มีอะไรบอก"""
    import re
    pres = (HERE / "presentation.py").read_text(encoding="utf-8")
    serve = (HERE / "serve_purson.py").read_text(encoding="utf-8")

    check("ปิด Xet ตอนโหลดโมเดล (ตัวที่พังจริง)", "HF_HUB_DISABLE_XET=1" in pres)
    check("ยังคง MoE layout เดิมไว้ (ไม่งั้นผลเป็นขยะเงียบๆ)",
          "UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert" in pres)

    wh = pres[pres.index("def wait_healthy("):pres.index("def cmd_status(")]
    check("รอโมเดลแล้วเช็คด้วยว่าตัวเสิร์ฟยังอยู่", "server_alive(st)" in wh)
    check("ตัวเสิร์ฟตาย = โยน BadMachine (กู้ได้ ไม่ใช่ตายทั้งโปรแกรม)",
          "raise BadMachine" in wh)

    sa = pres[pres.index("def server_alive("):pres.index("def wait_healthy(")]
    check("ssh ตอบช้าไม่นับว่าตัวเสิร์ฟตาย (ห้ามตัดสินผิดทาง)",
          "TimeoutExpired" in sa and "return True" in sa)
    check("pgrep ต้องไม่เจอตัวเอง (ใช้ [s]erve_purson)", "[s]erve_purson" in sa)

    # ทุกจุดที่เรียก wait_healthy ต้องมีคนรับ BadMachine ไม่งั้นโผล่เป็น traceback ใส่หน้า
    calls = list(re.finditer(r"^( *)wait_healthy" + chr(92) + "(", pres, re.M))
    check(f"เรียก wait_healthy {len(calls)} จุด และทุกจุดอยู่ใน try",
          len(calls) >= 3 and all(len(m.group(1)) >= 8 for m in calls))

    check("โหลดโมเดลล้ม = ลองใหม่ ไม่ใช่ตายทันที",
          "for attempt in range(1, 4)" in serve and "model, tok = load(" in serve)

    scrap = pres[pres.index("def scrap_instance("):pres.index("def cmd_up(")]
    check("คืนเครื่องแล้วต้องฆ่า tunnel ด้วย (ไม่งั้นจองพอร์ต 8000 ค้าง)",
          "tunnel_pid" in scrap)


def test_jupyter_mode_guard():
    """เครื่องที่เช่าเองจากเว็บแล้วเลือกโหมด Jupyter จะไม่มี sshd เลย — ต่อไม่ได้ทั้งทางตรง
    และพร็อกซี และแก้ทีหลังไม่ได้ (vastai attach ssh ตอบ error) ต้องบอกทันทีตั้งแต่วินาทีแรก
    ไม่ใช่ปล่อยให้รอ 15 นาทีแล้วค่อยบอกว่าเครื่องเสีย (เจอจริง 23 ก.ย. 69 instance 52242218)

    ห้ามขึ้นบัญชีดำเด็ดขาด — เครื่องไม่ได้เสีย การ์ดดีปกติ เช่าใหม่แบบเลือกโหมด SSH ก็ใช้ได้เลย
    ถ้าแบนไป เท่ากับตัดเครื่องดีทิ้งเพราะความผิดของคนกดเช่า"""
    real_json = P.vastai_json
    P.vastai_json = lambda args: [{"id": 1, "image_runtype": "ssh_proxy"},
                                  {"id": 2, "image_runtype": "ssh_direc"},
                                  {"id": 3, "image_runtype": "jupyter"},
                                  {"id": 4, "image_runtype": "jupyter_proxy"}]
    try:
        ok = []
        for iid in (1, 2):
            try:
                P.check_ssh_mode(iid)
                ok.append(True)
            except SystemExit:
                ok.append(False)
        check("โหมด ssh ทุกแบบต้องผ่าน (ssh_proxy · ssh_direc)", all(ok))

        blocked = []
        for iid in (3, 4):
            try:
                P.check_ssh_mode(iid)
                blocked.append(False)
            except SystemExit:
                blocked.append(True)
        check("โหมด jupyter ต้องหยุดทันที ไม่ปล่อยให้รอ 15 นาที", all(blocked))

        try:
            P.check_ssh_mode(999)
            found = False
        except SystemExit:
            found = True
        check("ไม่เจอ instance id ต้องบอกตรงๆ ไม่ใช่เดินต่อ", found)
    finally:
        P.vastai_json = real_json

    src = (HERE / "presentation.py").read_text(encoding="utf-8")
    guard = src[src.index("def check_ssh_mode("):src.index("def cmd_attach(")]
    check("ห้ามแบนเครื่อง เพราะเครื่องไม่ได้เสีย (คนกดเช่าผิดโหมด)",
          "blacklist_add" not in guard and "BadMachine" not in guard)
    check("cmd_attach เรียกด่านนี้ก่อนรอเครื่อง",
          src.index("check_ssh_mode(a.instance_id)") < src.index("wait_running(a.instance_id)"))


def main():
    print("ตรวจบัญชีดำเครื่องเช่า")
    for fn in (test_store, test_filter):
        with_temp_blacklist(fn)
    test_ssh_endpoint_sentinel()
    test_cmd_up_structure()
    test_dead_server_detection()
    test_jupyter_mode_guard()
    if FAILED:
        sys.exit(f"\n❌ ไม่ผ่าน {len(FAILED)} ข้อ: {', '.join(FAILED)}")
    print("\nok — บัญชีดำทำงานครบ (จำได้ · กรองได้ · ไฟล์พังไม่ล้ม · cmd_up กู้ตัวเองได้)")


if __name__ == "__main__":
    main()
