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
    """65535 คือรหัส 'ไม่มีพอร์ตตรง' — ถ้าไม่กรองออก จะเสียเวลา timeout ทุกรอบ
    และหน้าจอจะบอกว่า 'ทางตรงยังไม่ตอบ' ซ้ำๆ จนคนเข้าใจผิดว่าเครื่องกำลังจะขึ้น"""
    tried = []
    real_alive = P.ssh_alive
    P.ssh_alive = lambda h, p: (tried.append((h, p)), False)[1]
    try:
        P.pick_ssh_endpoint({"public_ipaddr": "1.2.3.4", "direct_port_start": 65535,
                             "ssh_host": "ssh2.vast.ai", "ssh_port": 32696})
    finally:
        P.ssh_alive = real_alive
    check("ไม่ลองทางตรงเมื่อ direct_port_start = 65535", ("1.2.3.4", 65535) not in tried)
    check("ยังลองพร็อกซีตามปกติ", ("ssh2.vast.ai", 32696) in tried)


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


def main():
    print("ตรวจบัญชีดำเครื่องเช่า")
    for fn in (test_store, test_filter):
        with_temp_blacklist(fn)
    test_ssh_endpoint_sentinel()
    test_cmd_up_structure()
    if FAILED:
        sys.exit(f"\n❌ ไม่ผ่าน {len(FAILED)} ข้อ: {', '.join(FAILED)}")
    print("\nok — บัญชีดำทำงานครบ (จำได้ · กรองได้ · ไฟล์พังไม่ล้ม · cmd_up กู้ตัวเองได้)")


if __name__ == "__main__":
    main()
