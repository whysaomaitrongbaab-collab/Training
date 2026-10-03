"""เช่าการ์ดสำหรับทดสอบทางเร็ว (merge + vLLM + SGLang) — ใช้ฟังก์ชันของ presentation.py ตัวจริง
ต่างจาก `presentation.py up` แค่: ดิสก์ 400 GB (merge ต้อง ≥250) · ไม่เปิดตัวเสิร์ฟให้ · ตั้งคืนอัตโนมัติบนการ์ด
state เขียนลง presentation_state.json ตัวเดียวกัน → `python presentation.py down/status/autodown` ใช้กับการ์ดนี้ได้"""
import json
import sys
import time

sys.path.insert(0, r"d:/00mk/steel project/งานสมบูรณ์/Constistant/server/purson-worker")
import presentation as P  # noqa: E402

DISK = 400
MAX_PRICE = 1.45
AUTODOWN_H = float(sys.argv[1]) if len(sys.argv) > 1 else 7.0

st = P.load_state()
if st.get("instance_id"):
    sys.exit(f"มี instance {st['instance_id']} ค้างใน state อยู่แล้ว — down ก่อน")
m = P.MODELS["destrier"]          # deps ชุด production (unsloth/peft>=0.20) ลง /venv/main ตอน onstart
q = m["search"] + f" disk_space>={DISK}"
offers = P.drop_blacklisted(P.vastai_json(["search", "offers", q, "-o", "dph_total"]))
tried = 0
while offers and tried < 4:
    o = offers.pop(0)
    if o["dph_total"] > MAX_PRICE:
        sys.exit(f"ถูกสุดตอนนี้ ${o['dph_total']:.3f}/ชม. เกินเพดาน ${MAX_PRICE}")
    print(f"offer {o['id']} machine {o['machine_id']} {o['gpu_name']} ${o['dph_total']:.3f}/ชม. "
          f"{o.get('geolocation')} down {o.get('inet_down', 0):.0f} Mbps", flush=True)
    r = P.sh(["vastai", "create", "instance", str(o["id"]), "--image", P.IMAGE, "--disk", str(DISK),
              "--ssh", "--direct", "--label", "purson-fastpath-test",
              "--onstart-cmd", P.onstart_cmd(m), "--raw"])
    if r.returncode != 0:
        sys.exit(f"เช่าไม่สำเร็จ: {r.stderr.strip()} {r.stdout.strip()}")
    res = json.loads(r.stdout)
    iid = res.get("new_contract")
    if res.get("success") is False and iid:
        print("  ไม่ว่างจริง — คืนทันที", flush=True)
        P.sh(["vastai", "destroy", "instance", str(iid)], input="y\n")
        continue
    tried += 1
    P.save_state({"instance_id": iid, "model": "destrier-fastpath-test", "price_per_hr": o["dph_total"],
                  "machine_id": o.get("machine_id"), "gpu_name": o.get("gpu_name", "")})
    print(f"เช่าแล้ว instance {iid} — รอเครื่องขึ้น", flush=True)
    try:
        host, port = P.wait_running(iid)
    except P.BadMachine as e:
        P.blacklist_add(o.get("machine_id"), str(e), o.get("gpu_name", ""))
        P.scrap_instance(iid)
        continue
    st = P.load_state()
    st.update({"ssh_host": host, "ssh_port": port})
    P.save_state(st)
    P.arm_autodown(st, AUTODOWN_H)
    print(f"READY {iid} ssh -p {port} root@{host}")
    sys.exit(0)
sys.exit("ไม่ได้เครื่อง")
