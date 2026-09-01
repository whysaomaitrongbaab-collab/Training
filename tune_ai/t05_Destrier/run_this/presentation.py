#!/usr/bin/env python3
"""presentation.py — เปิด/ปิดเครื่อง GPU เช่าเฉพาะวันพรีเซนต์ (web → PC นี้ → คอมเช่า)

    python presentation.py up            เช่าการ์ด + เปิดโมเดล + ต่อ tunnel + รอจนพร้อม
    python presentation.py status        เช็คสถานะเครื่อง/tunnel/เครดิต
    python presentation.py tunnel        ต่อ tunnel ใหม่ (เช่น PC รีสตาร์ท)
    python presentation.py smoke         ยิงทดสอบ 1 ครั้ง ต้องได้ JSON กลับ
    python presentation.py down          destroy เครื่องเช่า + ปิด tunnel (จบวัน)

หัวใจ: SSH tunnel (-L 8000) ทำให้ worker เห็น GPU ที่ http://localhost:8000 เสมอ —
IP เครื่องเช่าเปลี่ยนทุกรอบก็ไม่ต้องแก้ worker_config.json อีกเลย และไม่ต้องเปิดพอร์ต
สาธารณะบนเครื่องเช่า (แนวทางมาตรฐาน vast.ai — tunnel เท่านั้น ไม่ expose HTTP ตรง)

⏰ วันจริง: รัน `up` ล่วงหน้า ~1 ชม. ก่อนพรีเซนต์ (ลง deps + โหลดโมเดล ~70GB กินเวลา)
💰 destroy ≠ stop — stop ยังเสียค่า storage ต่อ · เครื่อง inference ไม่มีไฟล์ต้องกู้
   destroy ได้ทันทีไม่ต้องเช็ค Day-of-Shame (ไม่เหมือนเครื่องเทรน)

ต้องมีบนเครื่องนี้: vastai CLI (login แล้ว), ssh.exe — ทั้งคู่ทีมใช้ประจำอยู่แล้ว
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "presentation_state.json"
LOCAL_PORT = 8000

# preset ต่อโมเดล — เสิร์ฟด้วย serve_purson.py (Unsloth) ไม่ใช่ vLLM
# ⚠️ ตรวจแล้ว 2026-08-30: adapter t03 เก็บ MoE LoRA เป็น experts.lora_A [4096,2048]
#    (256 experts × rank 16 แบนรวม = รูปแบบของ Unsloth) ไม่ตรงกับที่ vLLM รับทั้ง 2 แบบ
#    → เส้นทาง vLLM ถูกตัดทิ้งทั้งเส้น ดูเหตุผลเต็มในหัวไฟล์ serve_purson.py
MODELS = {
    "t03": {
        "adapter": "Sicilian44/t03",
        # inet_down>500 ไม่ใช่ของฟุ่มเฟือย — เครื่อง inference อายุสั้น ต้องโหลดโมเดล ~70GB
        # ทุกครั้งที่เช่าใหม่ ค่าเน็ตช้าจึงกินเวลาที่เราจ่ายเป็นรายชั่วโมง: 343Mbps ≈ 27 นาที
        # vs 888Mbps ≈ 11 นาที → offer ที่ $0.935 เน็ตช้า แพงกว่า offer $1.095 เน็ตเร็วจริง
        "search": ("gpu_ram>=90 num_gpus=1 reliability>0.99 inet_down>500 "
                   "rentable=true verified=true"),
        "deps": "unsloth xgrammar fastapi uvicorn pillow",
    },
    "t04": {
        # InternVL3-78B เทรนด้วย LLaMA-Factory ไม่ใช่ Unsloth — serve_purson.py โหลดไม่ได้
        # ต้องเขียนตัวโหลดด้วย transformers+peft ก่อน (ยังไม่ทำ) ดู infer_house_t04.py
        "adapter": "Sicilian44/Purson-weights",
        "search": "gpu_ram>=78 num_gpus=2 reliability>0.99 rentable=true verified=true",
        "deps": "transformers peft bitsandbytes xgrammar fastapi uvicorn pillow",
        "unsupported": "serve_purson.py ยังโหลด InternVL3 (LLaMA-Factory) ไม่ได้ — "
                       "ต้อง port ตัวโหลดจาก infer_house_t04.py ก่อน",
    },
    "destrier": {
        # destrier (รอบ t05 "Courser") — Qwen3.6-35B-A3B + soup ของ 3 fold (r48/α96, rank-concat) 2026-08-31
        # base เดียวกับ t03 ต่างแค่ adapter — แต่ **สองค่านี้ต่างจาก t03 และพลาดไม่ได้**:
        # 1) peft>=0.20 บังคับ — 0.18.1 แยกตัวประกอบชั้น MoE คนละข้าง โหลดแล้วได้ขยะ *เงียบๆ*
        #    ไม่ error (บันทึกไว้ workmen's_diary 2026-08-31 + rule_of_tune บทที่ 18)
        # 2) max_pixels 6912*1024 ไม่ใช่ 7680 — ลดตอนเทรนจริงหลัง OOM, เสิร์ฟคนละค่ากับที่เทรน
        #    = บั๊กคลาสเดียวกับที่ฆ่า t01/t04 (ภาพโดนย่อ/ขยายผิดเงียบๆ)
        # ⚠️ คุณภาพผลลัพธ์ยังไม่ผ่านเกณฑ์ — pure-power test recall ต่ำ ดูไดอารี่วันเดียวกัน
        "adapter": "dacarokann/destrier",
        "search": ("gpu_ram>=90 num_gpus=1 reliability>0.99 inet_down>500 "
                   "rentable=true verified=true"),
        "deps": "unsloth xgrammar fastapi uvicorn pillow 'peft>=0.20'",
        "max_pixels": 6912 * 1024,
    },
}
IMAGE = "vastai/pytorch:cuda-12.8.1-auto"   # convention เดิมของทีม (t03/t04 ใช้ตัวนี้)
DISK_GB = 150


def sh(cmd, **kw):
    """cmd เป็น list = เรียกตรงไม่ผ่าน shell (ปลอดภัยกับอักขระพิเศษ), เป็น str = ผ่าน shell

    ⚠️ บทเรียน 2026-08-31: subprocess(shell=True) บน Windows ใช้ **cmd.exe** เสมอ
    ต่อให้เรานั่งพิมพ์อยู่ใน bash ก็ตาม — cmd.exe ไม่รู้จัก single quote และมองว่า `>` คือ
    redirect ไฟล์ ทำให้ `search offers 'gpu_ram>=90 ...'` กลายเป็นการเขียนไฟล์ชื่อ =90
    แล้ว stdout ว่างเปล่า (JSON parse พังแบบไม่มีเบาะแส) ทุกคำสั่งที่มี > หรือ quote
    ต้องส่งเป็น list เท่านั้น"""
    print(f"$ {cmd if isinstance(cmd, str) else ' '.join(map(str, cmd))}")
    return subprocess.run(cmd, shell=isinstance(cmd, str),
                          capture_output=True, text=True, **kw)


def vastai_json(args):
    r = sh(["vastai", *args, "--raw"])
    if r.returncode != 0:
        sys.exit(f"vastai พัง: {r.stderr.strip()}")
    return json.loads(r.stdout)


def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(st):
    STATE_FILE.write_text(json.dumps(st, indent=2))


# ⚠️ ค้นพบจริงบน instance 49282912 (2026-08-31) — 3 อย่างที่ image ของ vast.ai ไม่ได้ให้ฟรี:
# 1) /workspace **ไม่มี** มาแต่แรก → redirect `> /workspace/pip.log` ทำให้ onstart ล้มทั้งบรรทัด
#    แบบเงียบๆ (ไม่มีทั้ง log ให้ดูและไม่มี package ที่ลง)
# 2) torch อยู่ใน **/venv/main** ไม่ใช่ python3 ของระบบ — เรียก `python` เฉยๆ = ModuleNotFoundError
#    และ `python` (ไม่มีเลข 3) ไม่มีใน PATH ด้วยซ้ำ
# 3) การ์ด Blackwell ต้อง TORCH_CUDA_ARCH_LIST=12.0 ก่อนติดตั้งอะไรที่ compile CUDA kernel
#    (กติกาเดิมของทีม จาก onstart.sh ของ t02/t03)
VENV_PY = "/venv/main/bin/python"


def onstart_cmd(m):
    """onstart ทำแค่ลง dependency — ตัวเสิร์ฟ scp ขึ้นไปทีหลัง (ไฟล์เราเอง ไม่มีบน PyPI)"""
    return (f"mkdir -p /workspace && export TORCH_CUDA_ARCH_LIST=12.0 && "
            f"{VENV_PY} -m pip install -U {m['deps']} > /workspace/pip.log 2>&1")


def cmd_up(a):
    m = MODELS[a.model]
    if m.get("unsupported"):
        sys.exit(f"--model {a.model} ยังใช้ไม่ได้: {m['unsupported']}")
    st = load_state()
    if st.get("instance_id"):
        sys.exit(f"มี instance {st['instance_id']} ค้างอยู่ใน state — รัน status หรือ down ก่อน")

    offers = vastai_json(["search", "offers", m["search"], "-o", "dph_total"])
    if not offers:
        sys.exit("ไม่เจอ offer ที่เข้าเงื่อนไข")
    offer = offers[0]
    price = offer.get("dph_total", 0)
    print(f"\nเลือก offer {offer['id']}: {offer.get('gpu_name')} ×{offer.get('num_gpus')} "
          f"({offer.get('gpu_ram', 0) / 1024:.0f}GB) @ ${price:.3f}/ชม. "
          f"rel={offer.get('reliability2', offer.get('reliability', '?'))}")
    if price > a.max_price:
        sys.exit(f"แพงเกิน --max-price {a.max_price} — เพิ่ม limit เองถ้ายอมจ่าย")
    if not a.yes and input("เช่าเลยไหม? [y/N] ").strip().lower() != "y":
        sys.exit("ยกเลิก")

    r = sh(["vastai", "create", "instance", str(offer["id"]), "--image", IMAGE,
            "--disk", str(DISK_GB), "--ssh", "--onstart-cmd", onstart_cmd(m), "--raw"])
    if r.returncode != 0:
        sys.exit(f"เช่าไม่สำเร็จ: {r.stderr.strip()}\n{r.stdout.strip()}")
    new_id = json.loads(r.stdout).get("new_contract")
    print(f"เช่าแล้ว instance {new_id} — รอเครื่องขึ้น...")
    save_state({"instance_id": new_id, "model": a.model, "price_per_hr": price})

    host, port = wait_running(new_id)
    st = load_state()
    st.update({"ssh_host": host, "ssh_port": port})
    save_state(st)
    upload_and_start_server(st, m)
    start_tunnel(st)
    wait_healthy()
    print("\n✅ พร้อมแล้ว — เปิดอีก terminal แล้วรัน: python worker.py"
          "\n   (จบวันอย่าลืม: python presentation.py down — ไม่งั้นเผาเงินทั้งคืน)")


def wait_running(iid, timeout_s=15 * 60):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        for ins in vastai_json(["show", "instances"]):
            if ins.get("id") == iid and ins.get("actual_status") == "running":
                host, port = ins.get("ssh_host"), ins.get("ssh_port")
                print(f"เครื่องขึ้นแล้ว: ssh -p {port} root@{host}")
                return host, port
        time.sleep(20)
        print(f"  ...รอเครื่องขึ้น ({int(time.time() - t0)}s)")
    sys.exit("เครื่องไม่ขึ้นใน 15 นาที — เช็ค vastai show instances เอง "
             "(host มีอาการ = destroy แล้วเช่าใหม่ อย่าฝืนรอ — บทเรียน fold3)")


def ssh_base(st):
    return ["-p", str(st["ssh_port"]), f"root@{st['ssh_host']}",
            "-o", "StrictHostKeyChecking=accept-new"]


def upload_and_start_server(st, m):
    """ส่ง serve_purson.py ขึ้นเครื่องเช่าแล้วสั่งรันใน background

    รอ pip ให้จบก่อน (onstart ยังวิ่งอยู่ตอนเครื่องเพิ่งขึ้น) — ไม่งั้น import unsloth พัง
    ทันทีแล้วเราจะไปรอ health check ที่ไม่มีวันเขียว"""
    # onstart อาจยังไม่ทัน mkdir (หรือล้มไปแล้ว) — สร้างเองก่อนเสมอ ไม่งั้น scp ตาย
    sh(["ssh", *ssh_base(st), "mkdir -p /workspace"])
    src = HERE / "serve_purson.py"
    r = sh(["scp", "-P", str(st["ssh_port"]), "-o", "StrictHostKeyChecking=accept-new",
            str(src), f'root@{st["ssh_host"]}:/workspace/serve_purson.py'])
    if r.returncode != 0:
        sys.exit(f"scp ไม่สำเร็จ: {r.stderr.strip()}")

    adapter = m["adapter"]
    px = f" --max-pixels {m['max_pixels']}" if m.get("max_pixels") else ""
    remote = (f"cd /workspace && "
              # '[p]ip install' ไม่ใช่ลูกเล่นสวยงาม — มันจำเป็น: bash ตัวนี้มีสตริง
              # "pip install" อยู่ใน command line ของตัวเอง `pgrep -f 'pip install'`
              # จึงเจอตัวเองทุกรอบ แล้ววนรอชั่วนิรันดร์ เซิร์ฟเวอร์ไม่มีวันเริ่ม
              # (เจอจริง 31 ส.ค. เครื่อง 49411642 — pip เสร็จตั้งแต่นาทีที่ 3 แต่ตัวรอ
              #  ยังวนอยู่ 17 นาทีจนต้องเข้าไป kill เอง) · วงเล็บทำให้ pattern ที่
              # pgrep ใช้ ไม่ตรงกับสตริงที่ปรากฏใน command line ของ bash ตัวนี้
              f"while pgrep -f '[p]ip install' > /dev/null; do sleep 10; done && "
              f"nohup {VENV_PY} serve_purson.py --adapter {adapter} --port {LOCAL_PORT}{px} "
              f"> /workspace/purson.log 2>&1 &")
    r = sh(["ssh", *ssh_base(st), remote])
    if r.returncode != 0:
        sys.exit(f"สั่งรันเซิร์ฟเวอร์ไม่สำเร็จ: {r.stderr.strip()}")
    print(f"ส่ง serve_purson.py ขึ้นแล้ว + สั่งรัน (adapter {adapter})")


def start_tunnel(st):
    # -N ไม่เปิด shell, ทิ้ง process ค้างไว้เป็นตัว tunnel · ปิดใน down
    # ServerAliveCountMax=6 → ยอมให้เงียบได้ 30s × 6 = 3 นาที ก่อนตัดสินว่าตาย
    # (ค่า default = 3 ครั้ง = 1.5 นาที · เน็ตบ้านกระตุกทีนึงเกินนั้นได้ง่าย ๆ)
    # ExitOnForwardFailure=yes → ถ้าจอง port ไม่ได้ให้ตายดัง ๆ ตอนนี้เลย ดีกว่าค้างเป็น
    # tunnel ที่ไม่ได้ forward อะไรจริงแล้ว worker มาเจอ connection refused ทีหลัง
    cmd = ["ssh", "-N", "-L", f"{LOCAL_PORT}:localhost:{LOCAL_PORT}",
           *ssh_base(st), "-o", "ServerAliveInterval=30",
           "-o", "ServerAliveCountMax=6", "-o", "ExitOnForwardFailure=yes"]
    print(f"$ {' '.join(cmd)}  (background)")
    p = subprocess.Popen(cmd)
    st["tunnel_pid"] = p.pid
    save_state(st)
    time.sleep(3)
    if p.poll() is not None:
        sys.exit("tunnel ตายทันที — เช็ค ssh key/host แล้วรัน: python presentation.py tunnel")
    print(f"tunnel ต่อแล้ว (pid {p.pid}) → http://localhost:{LOCAL_PORT}")


def healthy():
    try:
        with urllib.request.urlopen(f"http://localhost:{LOCAL_PORT}/v1/models", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def wait_healthy(timeout_s=60 * 60):
    print("รอ vLLM พร้อม (ติดตั้ง + โหลดโมเดล ~70GB — ปกติ 15-45 นาที)...")
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if healthy():
            print(f"✅ vLLM ตอบแล้ว ({int((time.time() - t0) / 60)} นาที)")
            return
        time.sleep(30)
        print(f"  ...ยังไม่พร้อม ({int((time.time() - t0) / 60)} นาที) "
              f"— ดู log: ssh เข้าไปแล้ว tail -f /workspace/purson.log")
    sys.exit("เกิน 1 ชม. ยังไม่พร้อม — ssh เข้าไปดู /workspace/purson.log")


def cmd_status(_a):
    st = load_state()
    if not st.get("instance_id"):
        print("ไม่มี instance ใน state (ยังไม่ up หรือ down ไปแล้ว)")
    else:
        ins = [i for i in vastai_json(["show", "instances"]) if i.get("id") == st["instance_id"]]
        print(f"instance {st['instance_id']}: "
              f"{ins[0].get('actual_status') if ins else 'ไม่พบ (โดน destroy แล้ว?)'} "
              f"@ ${st.get('price_per_hr', '?')}/ชม. (model {st.get('model')})")
        print(f"tunnel/vLLM: {'✅ ตอบปกติ' if healthy() else '❌ ไม่ตอบ — ลอง: python presentation.py tunnel'}")
    user = vastai_json(["show", "user"])
    print(f"เครดิตคงเหลือ: ${user.get('credit', '?')}")


def cmd_tunnel(_a):
    st = load_state()
    if not st.get("ssh_host"):
        sys.exit("ไม่มีข้อมูลเครื่องใน state — รัน up ก่อน")
    start_tunnel(st)
    wait_healthy(timeout_s=120)


def cmd_smoke(_a):
    body = json.dumps({
        "model": "purson",
        "messages": [{"role": "user",
                      "content": 'ตอบเป็น JSON object เดียว: {"ok": true}'}],
        "max_tokens": 50, "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        f"http://localhost:{LOCAL_PORT}/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    text = out["choices"][0]["message"]["content"]
    json.loads(text)  # ต้อง parse ได้ ไม่งั้น throw
    print(f"✅ smoke ผ่าน — โมเดลตอบ JSON ถูกต้อง: {text[:200]}")
    print("   (นี่เช็คแค่ 'เครื่องติด' — ก่อนเชื่อผลจริง ยิงหน้าแบบที่รู้คำตอบ 1 หน้า"
          " เทียบด้วยตาเสมอ โดยเฉพาะหลังเปลี่ยน is_3d_lora_weight/adapter)")


def cmd_down(_a):
    st = load_state()
    if st.get("tunnel_pid"):
        sh(["taskkill", "/PID", str(st["tunnel_pid"]), "/F", "/T"]
           if sys.platform == "win32" else ["kill", str(st["tunnel_pid"])])
    if st.get("instance_id"):
        r = sh(["vastai", "destroy", "instance", str(st["instance_id"])], input="y\n")
        print(r.stdout.strip() or r.stderr.strip())
        left = vastai_json(["show", "instances"])
        print(f"instance คงเหลือในบัญชี: {len(left)} "
              f"{'✅ คืนครบ' if not left else '⚠️ ยังมีเครื่องอื่นเปิดอยู่ — เช็คว่าตั้งใจไหม'}")
    STATE_FILE.unlink(missing_ok=True)
    print("จบวัน — ไม่เผาเงินต่อแล้ว")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("up")
    up.add_argument("--model", choices=list(MODELS), default="t03",
                    help="t03 = Qwen3.6-35B t03 adapter (พิสูจน์แล้วบนการ์ด 96GB) · "
                         "t04 = InternVL3-78B (2 การ์ด, ยังไม่เคย serve) · "
                         "destrier = Qwen3.6-35B soup adapter รอบ t05 (ใหม่สุด แก้ค่า decode แล้ว 31 ส.ค.)")
    up.add_argument("--max-price", type=float, default=1.5, help="เพดาน $/ชม.")
    up.add_argument("--yes", action="store_true", help="ไม่ต้องถามยืนยันก่อนเช่า")
    for name in ("status", "tunnel", "smoke", "down"):
        sub.add_parser(name)
    a = ap.parse_args()
    {"up": cmd_up, "status": cmd_status, "tunnel": cmd_tunnel,
     "smoke": cmd_smoke, "down": cmd_down}[a.cmd](a)


if __name__ == "__main__":
    main()
