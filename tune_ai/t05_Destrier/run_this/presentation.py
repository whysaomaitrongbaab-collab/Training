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
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "presentation_state.json"
LOCAL_PORT = 8000

# preset ต่อโมเดล — เสิร์ฟด้วย serve_purson.py (Unsloth) ไม่ใช่ vLLM
# ⚠️ ตรวจแล้ว 2026-08-30: adapter t03 เก็บ MoE LoRA เป็น experts.lora_A [4096,2048]
#    (256 experts × rank 16 แบนรวม = รูปแบบของ Unsloth) ไม่ตรงกับที่ vLLM รับทั้ง 2 แบบ
#    → เส้นทาง vLLM ถูกตัดทิ้งทั้งเส้น ดูเหตุผลเต็มในหัวไฟล์ serve_purson.py
#
# 🔴 2026-09-20 — ระเบิดเวลาที่เพิ่งเจอ ต้องอ่านก่อนแก้อะไรแถวนี้:
#    unsloth-zoo PR #1269 + #1232 (merge 17 ก.ย. 2026) เปลี่ยนวิธีอ่าน lora_B ของ MoE expert
#    จาก "grouped_by_expert" (expert ช้าสุด) ไปเป็น "rank_major" (expert เร็วสุด ตาม PEFT)
#    adapter ของเราทั้ง t03 และ destrier อัปก่อนวันนั้น = **เป็น grouped_by_expert ทั้งคู่**
#    แต่ onstart_cmd ใช้ `pip install -U unsloth` (ไม่ pin เวอร์ชัน) → เครื่องที่เช่าหลัง 17 ก.ย.
#    จะได้ unsloth ตัวใหม่ที่อ่าน adapter เราผิดทันที **ไม่ error แต่ผลลัพธ์เป็นขยะเงียบๆ**
#    (expert ทุกตัวจับคู่กับ rank คอลัมน์ผิด) — คือบั๊กคลาสเดียวกับที่ฆ่า GGUF t01/t02 ตอน ก.ค.
#    กัน: ส่ง env UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert ตอนรันเซิร์ฟเวอร์เสมอ
#    (เวอร์ชันเก่าไม่รู้จักตัวแปรนี้ = เมินทิ้ง ไม่กระทบ · เวอร์ชันใหม่ = อ่านถูกต้อง) ปลอดภัยทั้งสองทาง
SERVE_ENV = "UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert"

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
    # ── เส้นทางเร็ว (2026-09-20) — ใช้ได้ต่อเมื่อ merge LoRA เข้า base แล้วเท่านั้น ──
    # ทำไมถึงเปิดทางนี้ได้แล้ว: เหตุผลที่เคยตัด vLLM ทิ้ง (adapter MoE shape ไม่ตรง) เป็นปัญหา
    # ของ **runtime LoRA loading** ล้วนๆ — พอ merge เข้า base แล้วไม่มี adapter ให้ parse ผิด
    # เช็คพอยต์กลายเป็น Qwen3.6-35B-A3B ธรรมดาที่ทั้ง vLLM/SGLang เสิร์ฟได้ native
    # ได้ fused MoE kernel + CUDA graph + prefix cache ซึ่งคือตัวที่ทำให้เร็วขึ้นจริง
    #
    # ⚠️ ห้ามใช้ก่อนที่ verify_merge.py จะผ่านครบทั้ง A/B/C — โมเดลที่ merge ผิดจะเงียบสนิท
    "destrier-vllm": {
        "model_repo": "dacarokann/destrier-merged",
        "search": ("gpu_ram>=90 num_gpus=1 reliability>0.99 inet_down>500 "
                   "rentable=true verified=true"),
        "deps": "vllm",
        "serve": "vllm",
        "max_pixels": 6912 * 1024,
    },
    "destrier-sglang": {
        # SGLang น่าจะเร็วกว่า vLLM สำหรับงานนี้โดยเฉพาะ: worker.py ยิงทีละหน้าโดยใช้ instruction
        # prompt ก้อนเดิม (~1,000 token) ซ้ำทุกหน้า → RadixAttention cache prefix ข้าม request ได้
        # = ลด latency ต่อคำขอเดี่ยวตรงๆ ไม่ใช่แค่ throughput รวม
        "model_repo": "dacarokann/destrier-merged",
        "search": ("gpu_ram>=90 num_gpus=1 reliability>0.99 inet_down>500 "
                   "rentable=true verified=true"),
        "deps": "sglang[all]",
        "serve": "sglang",
        "max_pixels": 6912 * 1024,
    },
}

# context สูงสุดต่อ 1 คำขอ — คิดจากงานจริงที่หนักสุด (gridline มัด 4 ภาพ):
#   4 ภาพ × 6,912 visual token = 27,648 + instruction ~1,000 + GRID MASTER tail
#   + output สูงสุด 6,000 (MAX_NEW_TOKENS ของ worker) ≈ 36,000
# ตั้ง 40,960 เผื่อไว้ — **ห้ามลดเหลือ 32,768** งาน gridline จะโดนตัดกลางคัน
# (ถ้า OOM ตอนเปิดเซิร์ฟเวอร์ ให้ลด --gpu-memory-utilization/--mem-fraction-static ก่อน
#  อย่าลด context เพราะจะพังเฉพาะงานหนักซึ่งมองไม่เห็นตอน smoke test)
SERVE_CONTEXT_LEN = 40960
# worker ยิงทีละงานเสมอ (คู่มือห้ามกดซ้อน) — จองคิวเดียวให้ KV cache ไปอยู่กับ sequence ยาวๆ
SERVE_MAX_SEQS = 1
# ต้องตรงกับตอนเทรนเป๊ะ (train_t05_courser.py MIN_PIXELS) — ส่งคู่กับ longest_edge เสมอ
# transformers รุ่นใหม่โยน ValueError ถ้าส่ง size dict มาไม่ครบทั้งสองคีย์
MIN_PIXELS = 256 * 1024
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
    # ⚠️ บทเรียน 2026-09-23 (เจอสดตอนเตรียมพรีเซนต์ เครื่อง 52203739): ssh/scp ที่ **สืบ
    # stdin ของคอนโซลมาใช้** ค้างได้ไม่มีกำหนด และเพราะ capture_output กลืน stderr ไว้หมด
    # หน้าจอจะนิ่งสนิทไม่มีเบาะแสเลย — ค้างจริง 10+ นาทีที่ `mkdir -p /workspace` ทั้งที่
    # คำสั่งเดียวกันเป๊ะรันมือผ่านใน 1 วินาที ต่างกันแค่ `< /dev/null` · ตัด stdin ที่นี่
    # ที่เดียวครอบคลุมผู้เรียกทุกตัว (เป็นทางผ่านร่วมของ ssh/scp/vastai ทั้งหมด)
    # ผู้เรียกที่ต้องป้อน stdin จริง (destroy ที่ส่งตัวอักษร y) ส่ง input= มาเอง ห้ามไปทับ
    # ไม่งั้น subprocess โยน ValueError ทันที
    if "input" not in kw:
        kw.setdefault("stdin", subprocess.DEVNULL)
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
    check_model_available(a.model, m, assume_yes=a.yes)   # กันเช่าการ์ดแล้วค่อยพบว่าโมเดลไม่มี
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
    print("   เปิดอีก terminal แล้วรัน: python worker.py"
          "\n   (จบวันอย่าลืม: python presentation.py down — ไม่งั้นเผาเงินทั้งคืน)")


def cmd_attach(a):
    """ต่อกับเครื่องที่มะขามเช่าเองแล้วจากหน้าเว็บ vast.ai โดยตรง — ข้ามขั้นเลือก/เช่า
    offer อัตโนมัติของ `up` ทั้งหมด แค่รอให้เครื่องขึ้น running แล้วอัพโหลด+สั่งรัน
    +ต่อ tunnel เหมือนเดิม (ใช้ instance ID ที่เห็นในหน้าเว็บ vast.ai ของมะขาม)"""
    m = MODELS[a.model]
    if m.get("unsupported"):
        sys.exit(f"--model {a.model} ยังใช้ไม่ได้: {m['unsupported']}")
    check_model_available(a.model, m)      # กันเช่าการ์ดแล้วค่อยพบว่าโมเดลยังไม่มี
    st = load_state()
    if st.get("instance_id") and st["instance_id"] != a.instance_id:
        sys.exit(f"มี instance {st['instance_id']} ค้างอยู่ใน state — รัน down ก่อนถ้าจะสลับเครื่อง")

    print(f"ต่อกับ instance {a.instance_id} ที่มะขามเช่าไว้แล้ว — รอเครื่องขึ้น...")
    save_state({"instance_id": a.instance_id, "model": a.model, "price_per_hr": None})

    host, port = wait_running(a.instance_id)
    st = load_state()
    st.update({"ssh_host": host, "ssh_port": port})
    save_state(st)
    upload_and_start_server(st, m)
    start_tunnel(st)
    wait_healthy()
    print_ready()
    print("   เปิดอีก terminal แล้วรัน: python worker.py"
          "\n   (จบวันอย่าลืม: python presentation.py down — ไม่งั้นเผาเงินทั้งคืน)")


def print_ready():
    """บรรทัด READY เด่นๆ แยกจากข้อความอื่น — ให้มะขามเหลือบตาดู terminal แล้วรู้ทันที
    ไม่ต้องอ่านข้อความไทยทั้งหมด (เจอจริง: ข้อความยาวรวมกับ log อื่นแล้วมองไม่ทัน)"""
    print("\n" + "=" * 40 + "\nREADY\n" + "=" * 40)


def ssh_alive(host, port, timeout=12):
    """ปลายทางนี้ตอบ SSH จริงไหม — ไม่ใช่แค่ TCP ติด

    vast.ai ให้สองทางเข้าเครื่อง: พร็อกซี (ssh_host/ssh_port เช่น ssh6.vast.ai:13738)
    กับทางตรง (public_ipaddr/direct_port_start) — **ไม่ใช่ทุกเครื่องที่ใช้พร็อกซีได้**

    เจอจริง 23 ก.ย. instance 52203739 (เปิดด้วยโหมด Jupyter): ต่อพร็อกซีแล้ว TCP ติด
    แต่ถูกปิดทันทีตอน handshake — `kex_exchange_identification: Connection closed by
    remote host` เพราะข้างในไม่มี sshd หลังพร็อกซี · ทางตรงใช้ได้ปกติ และ `vastai ssh-url`
    เองก็คืนทางตรงมาให้ · เดิมโค้ดหยิบแต่ ssh_host/ssh_port จึงล้มทั้งที่เครื่องดีอยู่
    แล้วขึ้นข้อความชวนให้ destroy เครื่องทิ้งฟรีๆ

    BatchMode=yes กันไม่ให้มันค้างถามรหัสผ่านเวลาคีย์ใช้ไม่ได้"""
    try:
        r = subprocess.run(
            ["ssh", "-p", str(port), f"root@{host}",
             "-o", "StrictHostKeyChecking=accept-new",
             "-o", f"ConnectTimeout={timeout}", "-o", "BatchMode=yes", "true"],
            capture_output=True, text=True, timeout=timeout + 10)
        return r.returncode == 0
    except Exception:
        return False


def pick_ssh_endpoint(ins):
    """เลือกทางที่ตอบจริง — ลองทางตรงก่อนเพราะใช้ได้กว้างกว่า แล้วค่อยถอยไปพร็อกซี
    คืน (host, port) หรือ None ถ้ายังไม่มีทางไหนตอบ (เครื่องอาจยังบูต sshd ไม่เสร็จ)"""
    cands = []
    if ins.get("public_ipaddr") and ins.get("direct_port_start"):
        cands.append(("ทางตรง", ins["public_ipaddr"], int(ins["direct_port_start"])))
    if ins.get("ssh_host") and ins.get("ssh_port"):
        cands.append(("พร็อกซี", ins["ssh_host"], int(ins["ssh_port"])))
    for label, host, port in cands:
        if ssh_alive(host, port):
            print(f"เครื่องขึ้นแล้ว ({label}): ssh -p {port} root@{host}")
            return host, port
        print(f"  ...{label} ยังไม่ตอบ (ssh -p {port} root@{host})")
    return None


def wait_running(iid, timeout_s=15 * 60):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        for ins in vastai_json(["show", "instances"]):
            if ins.get("id") == iid and ins.get("actual_status") == "running":
                picked = pick_ssh_endpoint(ins)
                if picked:
                    return picked
                # เครื่อง running แล้วแต่ sshd ยังไม่ขึ้น — วนรออีกรอบ ไม่ตายทันที
                break
        time.sleep(20)
        print(f"  ...รอเครื่องขึ้น ({int(time.time() - t0)}s)")
    sys.exit("เครื่องไม่ขึ้นใน 15 นาที — เช็ค vastai show instances เอง "
             "(host มีอาการ = destroy แล้วเช่าใหม่ อย่าฝืนรอ — บทเรียน fold3)")


def ssh_base(st):
    """ตัวเลือก ssh ร่วมของทุกคำสั่งที่ยิงเข้าเครื่องเช่า

    BatchMode=yes สำคัญกว่าที่คิด: ถ้า auth มีปัญหา ssh จะ **ล้มทันที** แทนที่จะขึ้น prompt
    ถามรหัสผ่านที่ไม่มีใครมองเห็น (stderr ถูก capture ไว้) แล้วค้างยาว — ssh_alive() ใช้
    ตัวเลือกนี้อยู่แล้วและต่อติดทุกครั้ง ส่วนทางนี้ที่ไม่มี ค้าง 10+ นาทีเมื่อ 2026-09-23"""
    return ["-p", str(st["ssh_port"]), f"root@{st['ssh_host']}",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]


def check_model_available(name, m, assume_yes=False):
    """เช็คว่าโมเดล/adapter ที่จะเสิร์ฟมีอยู่จริงบน HF **ก่อนเช่าการ์ด**

    ทำไมต้องมี: preset ตระกูล -vllm/-sglang ชี้ไปที่โมเดล merged ซึ่ง **ยังไม่มีจนกว่าจะรัน
    merge_lora_to_base.py** ถ้าไม่เช็คตรงนี้ จะรู้ตัวหลังเช่าการ์ด + ลง deps + รอโหลด
    = จ่ายค่าการ์ดฟรีๆ 20-45 นาทีเพื่อค้นพบว่าลืมทำขั้นก่อนหน้า

    ⚠️ ข้อจำกัดที่ต้องรู้ (เจอจริงตอนทดสอบ 2026-09-20): **HF ตอบ 401 ทั้งกรณี "เป็น repo
    ส่วนตัว" และกรณี "ไม่มี repo นี้"** โดยตั้งใจ (ไม่ยอมบอกว่ามีอยู่ไหมกับคนที่ไม่มีสิทธิ์)
    ถ้าไม่มี HF_TOKEN จึงแยกสองเคสนี้ไม่ได้เลย — ตอนนั้นให้ถามผู้ใช้ยืนยันแทนที่จะเดาเอง"""
    repo = m.get("model_repo") or m.get("adapter")
    if not repo or os.path.isdir(repo):        # path ในเครื่องเช่า — เช็คจากที่นี่ไม่ได้
        return
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    req = urllib.request.Request(f"https://huggingface.co/api/models/{repo}")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status == 200:
                print(f"✅ {repo} มีอยู่บน HF")
                return
    except urllib.error.HTTPError as e:
        if e.code == 404 or (e.code in (401, 403) and tok):
            # มี token แล้วยังเข้าไม่ได้ = ไม่มีจริง หรือไม่ใช่ repo ของเรา — ฟันธงได้
            hint = ("\n   preset นี้ต้องใช้โมเดลที่ merge แล้ว — รัน Training/tune_ai/"
                    "merge_lora_to_base.py\n   แล้วตรวจด้วย verify_merge.py ให้ผ่านก่อน "
                    "(ดู README) · ระหว่างนี้ใช้ --model destrier ไปก่อนได้"
                    if m.get("serve") else "")
            sys.exit(f"⛔ เข้าถึง '{repo}' บน HuggingFace ไม่ได้ (HTTP {e.code}, preset {name})"
                     f"{hint}")
        if e.code in (401, 403):
            # ไม่มี token → แยกไม่ออกว่า "ส่วนตัว" หรือ "ไม่มีอยู่" — ห้ามเดาว่ามี
            print(f"\n⚠️  เช็ค '{repo}' ไม่ได้ (HTTP {e.code} และเครื่องนี้ไม่มี HF_TOKEN)")
            print("   HF ตอบ 401 ทั้งกรณี repo ส่วนตัว และกรณีไม่มี repo นี้ — แยกไม่ออก")
            if m.get("serve"):
                print("   preset นี้ต้องใช้โมเดลที่ merge แล้ว ถ้ายังไม่ได้ merge จะไปพังบนเครื่องเช่า"
                      " (เสียเงินฟรี ~20-45 นาที)")
            if not assume_yes and input("   เช่าต่อเลยไหม? [y/N] ").strip().lower() != "y":
                sys.exit("ยกเลิก — ตั้ง HF_TOKEN แล้วลองใหม่จะเช็คได้แน่นอน")
            return
    except Exception as e:
        print(f"⚠️  เช็ค {repo} ไม่ได้ ({type(e).__name__}) — ไปต่อ แต่ถ้าพังทีหลังให้สงสัยตรงนี้")
        return


def launch_cmd(m, adapter, px):
    """คำสั่งเปิดเซิร์ฟเวอร์บนเครื่องเช่า — ต่างกันตาม m['serve'] แต่ **หน้าตา API ต้องเหมือนกันเป๊ะ**
    เพราะ worker.py ยิง /v1/chat/completions ด้วย body ชุดเดิมเสมอ (model/messages/max_tokens/
    temperature/top_p/top_k/repetition_penalty/response_format) — ตรวจแล้วว่าทั้ง vLLM และ
    SGLang รับครบทุกตัวเมื่อยิงแบบ raw HTTP (worker ใช้ requests ไม่ใช่ openai SDK จึงส่ง
    top-level ได้ตรงๆ ไม่ต้อง extra_body)"""
    kind = m.get("serve")
    if not kind:
        # เส้นทางเดิม: Unsloth + serve_purson.py (พิสูจน์มาแล้วว่าผลถูก แค่ช้า)
        # SERVE_ENV ต้องอยู่ "ก่อน" คำสั่ง python เสมอ — resolver ของ unsloth อ่าน env ใหม่ทุกครั้ง
        # ที่ forward ไม่ใช่อ่านครั้งเดียวตอน import ถ้าหลุดไปจะ fallback เป็น rank_major เงียบๆ
        return (f"env {SERVE_ENV} {VENV_PY} serve_purson.py "
                f"--adapter {adapter} --port {LOCAL_PORT}{px}")

    mp = m.get("max_pixels", 6912 * 1024)
    repo = m["model_repo"]
    # ⚠️ ความละเอียดภาพต้องส่งเป็น size dict ให้ครบ 2 คีย์ ห้ามส่ง max_pixels
    #    โมเดลนี้ใช้ Qwen3VLProcessor ซึ่ง **ไม่มีคีย์ max_pixels** — ส่งไปจะโดน HF warn แล้ว
    #    ทิ้งเงียบๆ ภาพก็จะถูกย่อตาม default ของ preprocessor_config = บั๊กคลาสที่ฆ่า t01/t04
    #    (merge_lora_to_base.py อบค่านี้ลง repo ให้แล้วชั้นหนึ่ง ตรงนี้คือชั้นที่สอง กันพลาด)
    if kind == "vllm":
        return (
            f"{VENV_PY} -m vllm.entrypoints.openai.api_server"
            f" --model {repo} --served-model-name purson"
            f" --host 0.0.0.0 --port {LOCAL_PORT} --trust-remote-code --dtype bfloat16"
            f" --max-model-len {SERVE_CONTEXT_LEN} --gpu-memory-utilization 0.92"
            f" --max-num-seqs {SERVE_MAX_SEQS}"
            f" --limit-mm-per-prompt '{{\"image\": 4, \"video\": 0}}'"
            f" --mm-processor-kwargs '{{\"size\": {{\"shortest_edge\": {MIN_PIXELS},"
            f" \"longest_edge\": {mp}}}}}'"
            f" --enable-prefix-caching")
    if kind == "sglang":
        # SGLANG_IMAGE_MAX_PIXELS: SGLang ย่อภาพของมันเองอีกชั้นหนึ่ง **นอก** HF processor
        # (default 12,845,056 px) ถ้าไม่ตั้งให้ตรงกัน สองชั้นจะตีกันแล้วผล ViT ต่างจากตอนเทรน
        # --mm-attention-backend: ไม่ระบุ ปล่อย auto — fa3 คอมไพล์มาสำหรับ Hopper ถ้าการ์ดเป็น
        # RTX PRO 6000 Blackwell (SM120) ให้ลอง sdpa ก่อนเมื่อเจอปัญหา
        return (
            f"env SGLANG_IMAGE_MAX_PIXELS={mp} {VENV_PY} -m sglang.launch_server"
            f" --model-path {repo} --served-model-name purson"
            f" --host 0.0.0.0 --port {LOCAL_PORT} --tp-size 1"
            f" --context-length {SERVE_CONTEXT_LEN} --mem-fraction-static 0.78"
            f" --mm-process-config '{{\"image\":{{\"size\":{{\"longest_edge\":{mp},"
            f"\"shortest_edge\":{MIN_PIXELS}}}}}}}'"
            f" --limit-mm-data-per-request '{{\"image\":4}}'"
            f" --grammar-backend xgrammar")
    sys.exit(f"⛔ ไม่รู้จัก serve='{kind}'")


def upload_and_start_server(st, m):
    """ส่ง serve_purson.py ขึ้นเครื่องเช่าแล้วสั่งรันใน background

    รอ pip ให้จบก่อน (onstart ยังวิ่งอยู่ตอนเครื่องเพิ่งขึ้น) — ไม่งั้น import unsloth พัง
    ทันทีแล้วเราจะไปรอ health check ที่ไม่มีวันเขียว"""
    # 2026-09-02 เจอสด (3 ใน 6 รอบเช่า): vast.ai รายงาน actual_status=running ก่อน
    # sshd ในคอนเทนเนอร์จะรับ key จริงเสร็จ — mkdir/scp แรกสุดชน "Permission denied
    # (publickey)" ทั้งที่ key ตรงกับที่ลงทะเบียนไว้ (ไม่ใช่ key ผิด, เป็นแค่ propagation
    # lag) ก่อนหน้านี้พอเจอแบบนี้ต้อง destroy เช่าใหม่ทั้งเครื่อง เสียเวลา+เงินฟรี —
    # ตอนนี้ลองใหม่สั้นๆ ก่อน ไม่ยอมแพ้ทันที
    ssh_ok = False
    for attempt in range(6):
        # timeout เป็นตาข่ายชั้นสอง: stdin=DEVNULL ใน sh() ปิดต้นเหตุการค้างไปแล้ว แต่ถ้า
        # ยังค้างด้วยเหตุอื่น ให้ **ดังขึ้นแล้วลองใหม่** ดีกว่าเงียบไปเรื่อยๆ กลางวันพรีเซนต์
        try:
            r = sh(["ssh", *ssh_base(st), "mkdir -p /workspace"], timeout=60)
        except subprocess.TimeoutExpired:
            print(f"  ...ssh ค้างเกิน 60 วิ ลองใหม่ {attempt + 1}/6")
            continue
        if r.returncode == 0:
            ssh_ok = True
            break
        print(f"  ...ssh ยังไม่พร้อม (key propagation lag) ลองใหม่ {attempt + 1}/6")
        time.sleep(10)
    if not ssh_ok:
        sys.exit("ssh เข้าเครื่องไม่ได้หลังลองซ้ำ 6 ครั้ง (60s) — เครื่องนี้อาจมีปัญหาจริง "
                  "destroy แล้วเช่าใหม่")
    if not m.get("serve"):          # เส้นทาง Unsloth — ต้องส่งตัวเสิร์ฟของเราขึ้นไปก่อน
        src = HERE / "serve_purson.py"
        try:
            r = sh(["scp", "-P", str(st["ssh_port"]),
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                    str(src), f'root@{st["ssh_host"]}:/workspace/serve_purson.py'],
                   timeout=5 * 60)
        except subprocess.TimeoutExpired:
            sys.exit("scp ค้างเกิน 5 นาที — ไฟล์แค่ ~12KB ไม่ควรนานขนาดนี้ "
                     "เครื่องนี้มีอาการ destroy แล้วเช่าใหม่")
        if r.returncode != 0:
            sys.exit(f"scp ไม่สำเร็จ: {r.stderr.strip()}")

    adapter = m.get("adapter", m.get("model_repo"))
    px = f" --max-pixels {m['max_pixels']}" if m.get("max_pixels") else ""
    remote = (f"cd /workspace && "
              # '[p]ip install' ไม่ใช่ลูกเล่นสวยงาม — มันจำเป็น: bash ตัวนี้มีสตริง
              # "pip install" อยู่ใน command line ของตัวเอง `pgrep -f 'pip install'`
              # จึงเจอตัวเองทุกรอบ แล้ววนรอชั่วนิรันดร์ เซิร์ฟเวอร์ไม่มีวันเริ่ม
              # (เจอจริง 31 ส.ค. เครื่อง 49411642 — pip เสร็จตั้งแต่นาทีที่ 3 แต่ตัวรอ
              #  ยังวนอยู่ 17 นาทีจนต้องเข้าไป kill เอง) · วงเล็บทำให้ pattern ที่
              # pgrep ใช้ ไม่ตรงกับสตริงที่ปรากฏใน command line ของ bash ตัวนี้
              f"while pgrep -f '[p]ip install' > /dev/null; do sleep 10; done && "
              # nohup + `< /dev/null` + `2>&1 >file` ปิด fd ครบ 3 ช่อง แต่**ไม่พอ** — ตัว
              # process ยังอยู่ session/process-group เดียวกับ shell ที่ ssh สั่งงาน พอ ssh
              # ปิด pty ของ session นั้น kernel ยังไม่ยอมปิด channel จนกว่าทุก process ใน
              # session จะตายหมด (ลองแล้ว 1 ก.ย. รอบแรก: ใส่ `< /dev/null` เฉยๆ ยังค้างซ้ำ
              # อีกรอบ) `setsid` ตัดตัวเองออกเป็น session ใหม่ทั้งหมด ไม่ผูกกับ pty ของ ssh
              # เลย — เป็นทางแก้มาตรฐานของปัญหา "ssh ค้างรอ background process" นี้
              f"setsid nohup {launch_cmd(m, adapter, px)} "
              f"> /workspace/purson.log 2>&1 < /dev/null &")
    # timeout กันไว้อีกชั้น เผื่อ setsid ไม่พอในบางภาพเครื่องเช่า — 60s พอเหลือสำหรับแค่
    # สั่งงาน (ตัว while pip-wait ทำงานฝั่ง remote shell ไปแล้วก่อนหน้านี้จะไม่ถูกนับ เพราะ
    # ssh คำสั่งนี้แยกจากคำสั่งเช็ค pgrep ด้านบน — ที่จริง while อยู่ในคำสั่งเดียวกัน ดังนั้น
    # ต้องให้เวลาพอสำหรับกรณี pip ยังไม่เสร็จตอนเรียกด้วย — ตั้งกว้างไว้ 20 นาที)
    try:
        r = sh(["ssh", *ssh_base(st), remote], timeout=20 * 60)
    except subprocess.TimeoutExpired:
        sys.exit("สั่งรันเซิร์ฟเวอร์ค้างเกิน 20 นาที (setsid ควรกันไม่ให้เกิดแล้ว — ถ้าเจออีก "
                 "แจ้งมะขาม) ลอง: python presentation.py tunnel (ถ้า server รันจริงอยู่แล้วจะต่อได้เลย)")
    if r.returncode != 0:
        sys.exit(f"สั่งรันเซิร์ฟเวอร์ไม่สำเร็จ: {r.stderr.strip()}")
    kind = m.get("serve") or "serve_purson.py (Unsloth)"
    print(f"สั่งรันเซิร์ฟเวอร์แล้ว — ตัวเสิร์ฟ: {kind} · โมเดล: {adapter}")


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
            print_ready()
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
        if healthy():
            print("tunnel/vLLM: ✅ ตอบปกติ")
            print_ready()
        else:
            print("tunnel/vLLM: ❌ ไม่ตอบ — ลอง: python presentation.py tunnel")
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
                    help="destrier = Unsloth+adapter (ช้าแต่พิสูจน์แล้ว — ใช้อันนี้ถ้ายังไม่ได้ merge) · "
                         "destrier-sglang / destrier-vllm = โมเดล merged แล้ว เร็วกว่ามาก "
                         "(ต้องรัน merge_lora_to_base.py + verify_merge.py ให้ผ่านก่อน) · "
                         "t03 = adapter รุ่นเก่า · t04 = InternVL3-78B (ยังใช้ไม่ได้)")
    up.add_argument("--max-price", type=float, default=1.5, help="เพดาน $/ชม.")
    up.add_argument("--yes", action="store_true", help="ไม่ต้องถามยืนยันก่อนเช่า")
    attach = sub.add_parser("attach", help="ต่อกับเครื่องที่เช่าเองจากหน้าเว็บ vast.ai แล้ว (ข้าม auto-select)")
    attach.add_argument("instance_id", type=int, help="instance ID จากหน้าเว็บ vast.ai (คอลัมน์ ID)")
    attach.add_argument("--model", choices=list(MODELS), default="destrier")
    for name in ("status", "tunnel", "smoke", "down"):
        sub.add_parser(name)
    a = ap.parse_args()
    {"up": cmd_up, "attach": cmd_attach, "status": cmd_status, "tunnel": cmd_tunnel,
     "smoke": cmd_smoke, "down": cmd_down}[a.cmd](a)


if __name__ == "__main__":
    main()
