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

import notify
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "presentation_state.json"
BLACKLIST_FILE = HERE / "blacklist.json"
LOCAL_PORT = 8000
MAX_RENT_TRIES = 3          # ลองกี่เครื่องก่อนยอมแพ้แล้วให้คนมาดู
SLOW_MINUTES_MAX = 60       # โหลดโมเดลนานกว่านี้ = ทิ้งเครื่องนี้ (เครื่องดีใช้ 20-30 นาที)

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
# HF_HUB_DISABLE_XET=1 — Xet คือโปรโตคอลโหลดตัวใหม่ของ HuggingFace ที่เปิดเป็นค่า
# เริ่มต้น **และมันพังจริงกลางวันพรีเซนต์ 23 ก.ย. 69**: โหลดไป 9.1 GB จาก 72 GB แล้วโยน
#   RuntimeError: File reconstruction error: Internal Writer Error:
#                Background writer channel closed
# ตัวเสิร์ฟตายทั้ง process แล้วหน้าจอฝั่งเราก็ยังขึ้น "รอโมเดลพร้อม" ต่อไปเงียบๆ
# เสียไป ~20 นาทีกับการรอสิ่งที่ไม่มีวันมา
# ปิดแล้วถอยไปใช้ HTTP ธรรมดา ซึ่ง net_check วัดได้ 390 MB/s บนเครื่องที่ดี = เร็วพอ
# และเราโหลดโมเดลใหม่ทุกครั้งที่เช่า ไม่มีของเก่าให้ Xet dedup อยู่แล้ว = แทบไม่เสียอะไร
SERVE_ENV = ("UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert HF_HUB_DISABLE_XET=1")

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


class BadMachine(Exception):
    """เครื่องเช่าเครื่องนี้ใช้ไม่ได้จริง — ไม่ใช่ความผิดของสคริปต์เรา

    ต่างจาก sys.exit ตรงที่ **กู้ได้**: cmd_up จับแล้วคืนเครื่องทิ้ง + ขึ้นบัญชีดำ +
    เช่าเครื่องถัดไปให้อัตโนมัติ แทนที่จะโยนงานกลับให้คนนั่งเลือกเครื่องใหม่เอง
    (23 ก.ย. 2026 เจอเครื่องเสีย 4 เครื่องติดกัน เสียเวลาไปชั่วโมงกว่า เพราะทุกครั้ง
    ต้องเริ่มเมนูใหม่เองและมีสิทธิ์สุ่มได้เครื่องเดิมซ้ำ)"""


def load_blacklist():
    try:
        return json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}      # ไฟล์หาย/พัง = ถือว่ายังไม่เคยแบนใคร ไม่ใช่เหตุให้หยุดทำงาน


def blacklist_add(machine_id, reason, gpu=""):
    """จำเป็น **machine_id** ไม่ใช่ instance_id — instance คือสัญญาเช่ารอบนั้น เกิดใหม่ทุกครั้ง
    ที่กดเช่า ส่วน machine_id คือเครื่องจริงของโฮสต์ ซึ่งเป็นตัวที่มีปัญหาและจะโผล่มาให้
    เลือกซ้ำเรื่อยๆ ถ้าไม่จำไว้"""
    if not machine_id:
        print(f"  (ไม่รู้ machine_id จึงจำไม่ได้ว่าเครื่องไหน — {reason})")
        return
    bl = load_blacklist()
    bl[str(machine_id)] = {"reason": reason, "gpu": gpu or "?",
                           "at": time.strftime("%Y-%m-%d %H:%M")}
    BLACKLIST_FILE.write_text(json.dumps(bl, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    print(f"  🚫 ขึ้นบัญชีดำแล้ว: เครื่อง {machine_id} ({gpu or '?'}) — {reason}")


def drop_blacklisted(offers):
    bl = load_blacklist()
    if not bl:
        return offers
    keep = [o for o in offers if str(o.get("machine_id")) not in bl]
    skipped = len(offers) - len(keep)
    if skipped:
        print(f"  (ข้าม {skipped} เครื่องที่เคยมีปัญหา — ดูรายชื่อ: "
              f"python presentation.py blacklist)")
    return keep


def instance_machine_id(iid):
    """คืน (machine_id, gpu_name) ของ instance ที่ยังมีชีวิตอยู่ — ต้องเรียก **ก่อน** destroy"""
    for ins in vastai_json(["show", "instances"]):
        if ins.get("id") == iid:
            return ins.get("machine_id"), ins.get("gpu_name", "")
    return None, ""


def scrap_instance(iid):
    """คืนเครื่องที่ใช้ไม่ได้ทิ้งทันที — ไม่ปล่อยให้ค่าเช่าเดินระหว่างไปลองเครื่องถัดไป

    ต้องฆ่า tunnel ก่อนด้วย: ถ้าล้มหลัง start_tunnel แล้ว จะมี ssh -N ค้างชี้ไปที่เครื่องที่
    กำลังจะหายไป มันจองพอร์ต 8000 ไว้ แล้วเครื่องถัดไปจะต่อ tunnel ไม่ได้
    (ExitOnForwardFailure=yes ทำให้ตายดังๆ ตรงนั้นแทนที่จะเงียบ แต่ก็คือล้มอยู่ดี)"""
    st = load_state()
    if st.get("tunnel_pid"):
        sh(["taskkill", "/PID", str(st["tunnel_pid"]), "/F", "/T"]
           if sys.platform == "win32" else ["kill", str(st["tunnel_pid"])])
    print(f"  คืนเครื่อง {iid} ทิ้ง (ไม่ปล่อยให้เงินเดิน)...")
    r = sh(["vastai", "destroy", "instance", str(iid)], input="y\n")
    if r.returncode != 0:
        print(f"  ⚠️ คืนไม่สำเร็จ: {(r.stderr or r.stdout).strip()}"
              f"\n     เช็คเองที่หน้าเว็บ vast.ai ด้วย อย่าปล่อยค้าง")
    STATE_FILE.unlink(missing_ok=True)


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

    offers = drop_blacklisted(
        vastai_json(["search", "offers", m["search"], "-o", "dph_total"]))
    if not offers:
        sys.exit("ไม่เจอ offer ที่เข้าเงื่อนไข\n"
                 "   (ถ้าแบนไว้เยอะ ลองล้างบัญชีดำ: python presentation.py blacklist clear)")

    # ลองทีละเครื่องจนกว่าจะได้เครื่องที่ใช้ได้จริง — เครื่องที่ล้มถูกคืน+จำไว้ทันที
    # ไม่ต้องมีคนมานั่งกดเมนูใหม่ทุกรอบ (บทเรียน 23 ก.ย.: เสีย 4 เครื่องติดกัน)
    for attempt in range(1, MAX_RENT_TRIES + 1):
        if not offers:
            sys.exit("offer หมดแล้ว — ลองใหม่ทีหลัง หรือผ่อนเงื่อนไขใน MODELS[...]['search']")
        offer = offers.pop(0)
        price = offer.get("dph_total", 0)
        print(f"\n[เครื่องที่ {attempt}/{MAX_RENT_TRIES}] offer {offer['id']} "
              f"(machine {offer.get('machine_id')}): {offer.get('gpu_name')} "
              f"×{offer.get('num_gpus')} ({offer.get('gpu_ram', 0) / 1024:.0f}GB) "
              f"@ ${price:.3f}/ชม. rel={offer.get('reliability2', offer.get('reliability', '?'))}")
        if price > a.max_price:
            # offer เรียงจากถูกไปแพง — ตัวนี้แพงเกินแล้ว ตัวถัดไปยิ่งแพง ไม่ต้องลองต่อ
            # บอกราคาที่ถูกสุดจริงไปด้วย ไม่งั้นต้องเดาว่าต้องเพิ่มเพดานเป็นเท่าไหร่
            sys.exit(
                f"การ์ดถูกสุดที่ว่างตอนนี้ ${price:.2f}/ชม. แต่เพดานตั้งไว้ ${a.max_price:.2f}/ชม."
                f"\n   ยอมจ่ายก็สั่งแบบนี้: python presentation.py up --model {a.model} "
                f"--yes --max-price {price + 0.2:.1f}"
                f"\n   อยากให้เมนูจำถาวร: แก้เลข --max-price ใน go.py")
        if not a.yes and input("เช่าเลยไหม? [y/N] ").strip().lower() != "y":
            sys.exit("ยกเลิก")

        r = sh(["vastai", "create", "instance", str(offer["id"]), "--image", IMAGE,
                "--disk", str(DISK_GB), "--ssh", "--onstart-cmd", onstart_cmd(m), "--raw"])
        if r.returncode != 0:
            sys.exit(f"เช่าไม่สำเร็จ: {r.stderr.strip()}\n{r.stdout.strip()}")
        new_id = json.loads(r.stdout).get("new_contract")
        print(f"เช่าแล้ว instance {new_id} — รอเครื่องขึ้น...")
        save_state({"instance_id": new_id, "model": a.model, "price_per_hr": price,
                    "machine_id": offer.get("machine_id"),
                    "gpu_name": offer.get("gpu_name", "")})

        try:
            host, port = wait_running(new_id)
            st = load_state()
            st.update({"ssh_host": host, "ssh_port": port})
            save_state(st)
            upload_and_start_server(st, m)
            start_tunnel(st)
            wait_healthy(st)
        except BadMachine as e:
            print(f"\n❌ เครื่องนี้ใช้ไม่ได้: {e}")
            blacklist_add(offer.get("machine_id"), str(e), offer.get("gpu_name", ""))
            scrap_instance(new_id)
            continue                     # ไปเครื่องถัดไปเลย ไม่ต้องรอใครสั่ง
        print("   เปิดอีก terminal แล้วรัน: python worker.py"
              "\n   (จบวันอย่าลืม: python presentation.py down — ไม่งั้นเผาเงินทั้งคืน)")
        return

    notify.fail()       # ต้องมีคนมาดูแล้ว ไม่ควรรู้ตัวตอนเดินกลับมาเจอจอค้าง
    sys.exit(f"ลองไปแล้ว {MAX_RENT_TRIES} เครื่อง ใช้ไม่ได้ทั้งหมด "
             "— ทุกเครื่องถูกคืนและขึ้นบัญชีดำแล้ว ไม่มีอะไรค้างเผาเงิน\n"
             "   สั่งเปิดการ์ดใหม่อีกรอบได้เลย มันจะข้ามเครื่องพวกนั้นให้เอง")


def check_ssh_mode(iid):
    """เครื่องที่เช่าเองจากเว็บ ถ้าเลือกโหมด Jupyter จะ **ไม่มี sshd อยู่ในนั้นเลย**

    vast.ai มีโหมดเปิดเครื่อง 3 แบบ — entrypoint / ssh / jupyter — และ "เปิด ssh" กับ
    "เปิด jupyter" เป็นสวิตช์คนละตัว ค่าเริ่มต้นปิดทั้งคู่ · เว็บของ vast.ai ค่าเริ่มต้น
    มักเป็น jupyter อย่างเดียว คนเช่าเองจึงได้เครื่องที่ ssh เข้าไม่ได้โดยไม่รู้ตัว
    (สคริปต์เราเองไม่เคยเจอ เพราะ `create instance` ของเราใส่ --ssh ไว้เสมอ)

    อาการตอนเจอ: ต่อพร็อกซีแล้ว TCP ติดแต่ถูกปิดทันทีตอน handshake
    "kex_exchange_identification: Connection closed by remote host" ส่วนทางตรงก็ timeout
    — หน้าตาเหมือนเครื่องเสีย ทั้งที่การ์ดดีทุกอย่าง แค่เช่ามาผิดโหมด

    แก้ทีหลังไม่ได้: `vastai attach ssh <id> <key>` ตอบกลับมาว่า
    "Error adding SSH key to instance: 'NoneType' object is not subscriptable"
    (ลองจริง 23 ก.ย. 69 กับ instance 52242218) — ต้องคืนแล้วเช่าใหม่โดยเลือกโหมด SSH

    เช็คจาก image_runtype ซึ่ง vast.ai บอกโหมดจริงมาตรงๆ (ssh / ssh_proxy / ssh_direc /
    jupyter / jupyter_proxy / ...) — ไม่ใช่การเดาจากชื่อ image"""
    ins = next((i for i in vastai_json(["show", "instances"]) if i.get("id") == iid), None)
    if ins is None:
        sys.exit(f"ไม่เจอ instance {iid} ในบัญชี — เช็คเลข ID ที่หน้าเว็บ vast.ai อีกที")
    runtype = (ins.get("image_runtype") or "")
    if "ssh" in runtype:
        return
    sys.exit(
        f"⛔ เครื่องนี้เช่ามาแบบ '{runtype or 'ไม่ระบุ'}' ไม่ได้เปิด SSH ไว้ — ต่อเข้าไม่ได้เลย"
        f"\n   (ไม่ใช่เครื่องเสีย การ์ดดีปกติ แค่ตอนกดเช่าบนเว็บเลือกโหมดผิด"
        f" และแก้ทีหลังไม่ได้)"
        f"\n   วิธีแก้: คืนเครื่องนี้ แล้วเช่าใหม่โดย **ติ๊ก SSH** ตอนเลือก template"
        f"\n   สังเกตง่ายๆ ที่การ์ดบนเว็บ: บรรทัด Status ต้องลงท้ายด้วย /ssh ไม่ใช่ /jupyter"
        f"\n   หรือใช้เมนูข้อ 3 ให้สคริปต์เช่าเอง — มันใส่ --ssh ให้เสมอ ไม่มีทางพลาดข้อนี้")


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

    check_ssh_mode(a.instance_id)          # กันเสีย 15 นาทีไปกับเครื่องที่ ssh เข้าไม่ได้ตั้งแต่เกิด
    print(f"ต่อกับ instance {a.instance_id} ที่มะขามเช่าไว้แล้ว — รอเครื่องขึ้น...")
    save_state({"instance_id": a.instance_id, "model": a.model, "price_per_hr": None})

    try:
        host, port = wait_running(a.instance_id)
        st = load_state()
        st.update({"ssh_host": host, "ssh_port": port})
        save_state(st)
        upload_and_start_server(st, m)
        start_tunnel(st)
        wait_healthy(st)
    except BadMachine as e:
        # เครื่องนี้มะขามเลือกเอง — จำไว้ว่าใช้ไม่ได้ แต่ไม่คืนให้เอง (สิทธิ์ตัดสินใจเป็นของเขา)
        mid, gpu = instance_machine_id(a.instance_id)
        blacklist_add(mid, str(e), gpu)
        sys.exit(f"⛔ เครื่องนี้ใช้ไม่ได้: {e}\n"
                 "   คืนเครื่อง (เมนูข้อ 4) แล้วใช้เมนูข้อ 3 ให้สคริปต์หาเครื่องใหม่ให้เอง\n"
                 "   — มันจะข้ามเครื่องนี้ให้อัตโนมัติแล้ว")
    print("   เปิดอีก terminal แล้วรัน: python worker.py"
          "\n   (จบวันอย่าลืม: python presentation.py down — ไม่งั้นเผาเงินทั้งคืน)")


def print_ready():
    """บรรทัด READY เด่นๆ แยกจากข้อความอื่น — ให้มะขามเหลือบตาดู terminal แล้วรู้ทันที
    ไม่ต้องอ่านข้อความไทยทั้งหมด (เจอจริง: ข้อความยาวรวมกับ log อื่นแล้วมองไม่ทัน)"""
    print("\n" + "=" * 40 + "\nREADY\n" + "=" * 40)
    notify.ready()      # จังหวะที่รอนานสุด — จะได้เดินไปทำอย่างอื่นระหว่างรอได้


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
    # vast.ai ใช้เลขพอร์ตที่เป็นไปไม่ได้แทนรหัส "ยังไม่มีพอร์ตตรง" — เจอมาแล้ว 2 แบบ:
    # 65535 = โฮสต์นี้ไม่เปิดพอร์ตตรงเลย, -1 = เครื่องยังบูตไม่เสร็จ พอร์ตยังไม่ถูกจอง
    # (เจอสด 23 ก.ย. 69 ตอนเครื่องอายุ 1 นาที) — เช็คว่า "เป็นพอร์ตที่ใช้ได้จริง" (1-65534)
    # แทนที่จะไล่จำทีละค่า กันเจอสันดานใหม่ของ vast.ai อีกในอนาคต
    dp = ins.get("direct_port_start")
    if ins.get("public_ipaddr") and isinstance(dp, (int, float)) and 0 < dp < 65535:
        cands.append(("ทางตรง", ins["public_ipaddr"], int(dp)))
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
    raise BadMachine("เครื่องไม่ขึ้น/ssh ไม่ตอบใน 15 นาที")


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


# ขนาดโมเดลฐานที่ต้องโหลดลงเครื่องเช่าทุกครั้ง (unsloth/Qwen3.6-35B-A3B = 71.9 GB
# วัดจาก HF API จริง 23 ก.ย. 2026) ใช้แค่ประมาณเวลา ไม่ได้ใช้ตัดสินใจอะไรเอง
MODEL_DOWNLOAD_GB = 72


def net_check(st, sample_mb=90, streams=6):
    """วัดความเร็วโหลดจริงของเครื่องเช่า **ก่อน** จะปล่อยให้โหลดโมเดล 72 GB

    ทำไมต้องมี (เจอจริง 23 ก.ย. 2026 เสียไปเกือบสองชั่วโมง):
    vast.ai โฆษณา inet_down ของแต่ละ offer และ `search` ก็กรอง inet_down>500 อยู่แล้ว
    **แต่ตัวเลขนั้นเชื่อไม่ได้** — instance 52207647 โฆษณา 996 Mbps (≈125 MB/s) แต่
    ดึงจริงได้ 6 MB/s ตายตัว ยิงขนาน 8 เส้นก็ยังได้ 6 MB/s เท่าเดิม (คือถูกจำกัดที่ต้นทาง
    ไม่ใช่ปัญหาต่อคอนเนกชัน) · ที่แย่กว่าคือมันเงียบ: หน้าจอขึ้น "รอ vLLM พร้อม" เหมือนปกติ
    ทุกประการ กว่าจะรู้ว่าเครื่องนี้ต้องใช้ 2 ชม. 45 นาทีแทน 25 นาที ก็จ่ายไปแล้วครึ่งทาง

    2026-09-23 เปลี่ยนจาก "เตือนแล้วให้คนตัดสิน" เป็น **โยน BadMachine ทิ้งเครื่องเลย**
    เพราะคำตอบมันมีอยู่คำตอบเดียวมาตลอด (เปลี่ยนเครื่องถูกกว่ารอเสมอ) การถามคนจึงเป็นแค่
    การบังคับให้มีคนนั่งเฝ้าจอ — ตอนนี้ cmd_up ไปเครื่องถัดไปให้เองโดยไม่ต้องมีใครกด
    """
    url = ("https://huggingface.co/unsloth/Qwen3.6-35B-A3B/resolve/main/"
           "model-00001-of-00026.safetensors")
    chunk = sample_mb * 1000 * 1000
    # ยิงขนานหลายเส้นแล้วบวกกัน เพราะนั่นคือสิ่งที่ตัวโหลดจริงของ huggingface ทำ
    # วัดเส้นเดียวจะได้ตัวเลขต่ำกว่าความจริงและตัดสินผิด
    remote = (f"for i in $(seq 0 {streams - 1}); do S=$((i*{chunk})); "
              f"curl -sL -o /dev/null -w '%{{speed_download}}\n' -m 20 "
              f"-r $S-$((S+{chunk - 1})) '{url}' & done > /tmp/netcheck.txt; wait; "
              "awk '{s+=$1} END {print s+0}' /tmp/netcheck.txt")
    print("เช็คความเร็วเน็ตของเครื่องเช่าก่อน (ไม่กี่วินาที)...")
    try:
        r = sh(["ssh", *ssh_base(st), remote], timeout=90)
        mbps = float(r.stdout.strip().splitlines()[-1]) / 1e6
    except Exception:
        print("  (วัดไม่สำเร็จ — ข้ามไป ไม่ใช่เรื่องคอขวด)")
        return None
    if mbps <= 0:
        print("  (วัดไม่ได้ — ข้ามไป)")
        return None
    mins = MODEL_DOWNLOAD_GB * 1000 / mbps / 60
    print(f"  เน็ตเครื่องนี้ {mbps:.1f} MB/s → โหลดโมเดล {MODEL_DOWNLOAD_GB} GB "
          f"ราว {mins:.0f} นาที")
    if mins > SLOW_MINUTES_MAX:
        print("  ⚠️  ช้าผิดปกติ — ปกติเครื่องที่ดีใช้ 20-30 นาที")
        raise BadMachine(f"เน็ตช้า {mbps:.1f} MB/s (โหลดโมเดลต้องใช้ ~{mins:.0f} นาที)")
    return mbps


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
        raise BadMachine("ssh เข้าไม่ได้หลังลองซ้ำ 6 ครั้ง")

    # กันเรียกฟังก์ชันนี้ซ้ำใส่เครื่องที่มีตัวเสิร์ฟรันอยู่แล้ว (เช่น เผลอกดข้อ 1 ซ้ำด้วย
    # instance เดิม — เคยเกิดจริง 2 ก.ย. ต้องเข้าไป kill PID ทับกันเอง) เดิม scp+รันใหม่ทับ
    # ไปเลยโดยไม่เช็คก่อน: process เก่ายัง live จองพอร์ต 8000 ไว้ ตัวใหม่ bind ไม่ติดแล้วตาย
    # เงียบ (ssh คำสั่งพื้นหลังคืน returncode 0 เสมอเพราะไม่รอ process ลูกจริง — ดูคอมเมนต์
    # `&` ด้านล่าง) แต่โค้ดเดิมพิมพ์ "สั่งรันเซิร์ฟเวอร์แล้ว" ราวกับสำเร็จทุกครั้ง — พังจริง
    # แต่จอบอกว่าโอเค อันตรายกว่าไม่เช็คเลย
    r = sh(["ssh", *ssh_base(st), "pgrep -f '[s]erve_purson.py' > /dev/null && echo LIVE"],
           timeout=20)
    if (r.stdout or "").strip() == "LIVE":
        print("  ⚠️ เครื่องนี้มีตัวเสิร์ฟรันอยู่แล้ว — ข้ามการอัปโหลด/รันซ้ำ "
              "(ไม่แตะของที่ทำงานอยู่ ป้องกันแย่งพอร์ต 8000 กัน)")
        print("     อยากรีสตาร์ทจริง ให้เข้าไป kill เองก่อน: ssh เข้าเครื่องแล้ว "
              "pkill -f serve_purson.py แล้วค่อยรันคำสั่งนี้ใหม่")
        return

    net_check(st)
    if not m.get("serve"):          # เส้นทาง Unsloth — ต้องส่งตัวเสิร์ฟของเราขึ้นไปก่อน
        src = HERE / "serve_purson.py"
        try:
            r = sh(["scp", "-P", str(st["ssh_port"]),
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                    str(src), f'root@{st["ssh_host"]}:/workspace/serve_purson.py'],
                   timeout=5 * 60)
        except subprocess.TimeoutExpired:
            raise BadMachine("ส่งไฟล์ขึ้นเครื่องค้างเกิน 5 นาที (ไฟล์แค่ ~12KB)")
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
              #
              # ⚠️ `--fork` ไม่ใช่ของประดับ — ขาดแล้วค้างจริง (เจอสด 23 ก.ย. instance
              # 52213153): `&` ท้ายคำสั่งทำให้ทั้งชุดไปอยู่ใน subshell เบื้องหลัง และ
              # subshell นั้น**เป็นหัวหน้ากลุ่มโปรเซสอยู่แล้ว** — `setsid` เจอเคสนี้จะ
              # **exec ทับตัวเองแทนที่จะ fork** subshell จึงกลายเป็นตัวเซิร์ฟเวอร์เสียเอง
              # แล้วกอด fd ของช่อง ssh ไว้จนกว่าโมเดลจะตาย = ssh ไม่มีวันจบ
              # ผลคือ upload_and_start_server() ค้าง → start_tunnel() ไม่ได้รัน →
              # เซิร์ฟเวอร์พร้อมอยู่บนเครื่องแต่ localhost:8000 ตายสนิท หาสาเหตุยากมาก
              # วัดบนเครื่องจริงแล้ว: ไม่มี --fork → ssh ค้างเกิน 30 วิ · มี --fork → จบใน 4 วิ
              f"setsid --fork nohup {launch_cmd(m, adapter, px)} "
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


def server_alive(st):
    """ตัวเสิร์ฟบนเครื่องเช่ายังมีชีวิตอยู่ไหม — คืน (alive, log ท้ายๆ ถ้าตาย)

    ssh ช้า/ตอบไม่ได้ชั่วคราว **ไม่ใช่** หลักฐานว่าตาย — เคสนั้นคืน True เสมอ
    ตัดสินว่าตายเฉพาะตอนที่เข้าไปดูได้จริงแล้วไม่เจอ process"""
    # [s]erve_purson — วงเล็บกัน pgrep เจอตัวเอง (กับดักเดียวกับ [p]ip install ด้านล่าง)
    try:
        r = sh(["ssh", *ssh_base(st),
                "pgrep -f '[s]erve_purson.py' > /dev/null && echo ALIVE || "
                "{ echo DEAD; tail -20 /workspace/purson.log 2>/dev/null; }"], timeout=60)
    except subprocess.TimeoutExpired:
        return True, ""
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out.startswith("DEAD"):
        return True, ""
    return False, out[len("DEAD"):].strip()


def wait_healthy(st=None, timeout_s=60 * 60):
    print("รอโมเดลพร้อม (ติดตั้ง + โหลดโมเดล ~70GB — ปกติ 15-45 นาที)...")
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if healthy():
            print(f"✅ โมเดลตอบแล้ว ({int((time.time() - t0) / 60)} นาที)")
            print_ready()
            return
        time.sleep(30)
        # เช็คว่ายังมีอะไรทำงานอยู่จริงไหม — 23 ก.ย. 69 ตัวเสิร์ฟตายตั้งแต่นาทีที่ 4
        # (Xet พังกลางโหลด) แต่หน้าจอยังขึ้น "ยังไม่พร้อม" ต่อไปอีก 20 นาทีเหมือนปกติ
        # ทุกประการ — รอสิ่งที่ไม่มีวันมา นี่คือกับดักคลาสเดียวกับ ssh ค้างเงียบ
        if st:
            alive, log_tail = server_alive(st)
            if not alive:
                print("\n--- ท้าย purson.log บนเครื่องเช่า ---\n" + (log_tail or "(ไม่มี log)"))
                raise BadMachine("ตัวเสิร์ฟบนเครื่องเช่าตายกลางทาง (ดู log ข้างบน)")
        print(f"  ...ยังไม่พร้อม ({int((time.time() - t0) / 60)} นาที) "
              f"— ดู log: ssh เข้าไปแล้ว tail -f /workspace/purson.log")
    raise BadMachine("เกิน 1 ชม. ยังไม่พร้อม")


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
    # ส่ง st เข้าไปด้วย เพื่อให้มันบอกได้ว่า "ตัวเสิร์ฟตายไปแล้ว" พร้อม log
    # แทนที่จะรอ 2 นาทีแล้วบอกแค่ว่าไม่ตอบ
    try:
        wait_healthy(st, timeout_s=120)
    except BadMachine as e:
        sys.exit(f"ต่อ tunnel ได้แล้วแต่โมเดลยังไม่ตอบ: {e}\n"
                 "   ถ้าตัวเสิร์ฟตาย (ดู log ข้างบน) = คืนเครื่องแล้วเช่าใหม่ "
                 "— เมนูข้อ 4 แล้วข้อ 3")


def cmd_smoke(_a):
    # เดิมยิงครั้งเดียวไม่มี try/except เลย — เน็ตกระตุกหรือโมเดลตอบช้าตอนคำขอแรกหลัง
    # โหลดเสร็จ (คำขอต่อ ๆ ไปเร็วกว่านี้เยอะ) พังทีเดียวจบ ทั้งที่โมเดลจริง ๆ ใช้ได้
    # เจอสด 23 ก.ย. 69: bring_up() ผูก start_worker() ไว้กับผลของฟังก์ชันนี้ พอสะดุด
    # ครั้งเดียว worker เลยไม่ถูกเปิดทั้งที่การ์ดพร้อมสมบูรณ์ — ตอนนี้ bring_up() เลิกผูก
    # สองเรื่องนี้แล้ว แต่ตัวนี้เองก็ควรทนได้บ้าง ไม่ใช่ล้มง่ายเกินความเป็นจริง
    body = json.dumps({
        "model": "purson",
        "messages": [{"role": "user",
                      "content": 'ตอบเป็น JSON object เดียว: {"ok": true}'}],
        "max_tokens": 50, "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode()
    last_err = None
    for attempt in range(1, 4):
        try:
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
            return
        except Exception as e:
            last_err = e
            if attempt < 3:
                print(f"  ...smoke ครั้งที่ {attempt}/3 ไม่ผ่าน ({type(e).__name__}) "
                      f"ลองใหม่ใน 10 วิ")
                time.sleep(10)
    sys.exit(f"smoke ล้มครบ 3 ครั้ง: {type(last_err).__name__}: {last_err}")


def cmd_down(_a):
    st = load_state()
    if st.get("tunnel_pid"):
        sh(["taskkill", "/PID", str(st["tunnel_pid"]), "/F", "/T"]
           if sys.platform == "win32" else ["kill", str(st["tunnel_pid"])])
    if getattr(_a, "bad", None) and st.get("instance_id"):
        # ต้องถาม machine_id **ก่อน** destroy — พอคืนไปแล้ว instance หายจากรายการทันที
        mid, gpu = st.get("machine_id"), st.get("gpu_name", "")
        if not mid:
            mid, gpu = instance_machine_id(st["instance_id"])
        blacklist_add(mid, _a.bad, gpu)
    if st.get("instance_id"):
        r = sh(["vastai", "destroy", "instance", str(st["instance_id"])], input="y\n")
        print(r.stdout.strip() or r.stderr.strip())
    STATE_FILE.unlink(missing_ok=True)
    # ต้องเช็คทุกครั้งไม่ว่า state จะมี instance_id ไหม — ถ้า state ว่างเพราะ destroy รอบก่อน
    # ล้มแล้วโค้ดยังลบ state ทิ้ง (scrap_instance ก็ทำแบบนี้) เครื่องอาจยังเดินอยู่จริง
    # ห้ามพูดว่า "ไม่เผาเงินต่อแล้ว" โดยไม่เคยถาม vast.ai ก่อน (เจอช่องโหว่นี้จากตรวจโค้ด 23 ก.ย.)
    left = vastai_json(["show", "instances"])
    if left:
        notify.fail()
        ids = ", ".join(str(i.get("id")) for i in left)
        print(f"⚠️ ยังมี {len(left)} เครื่องเปิดอยู่ในบัญชี: {ids}")
        print("   เงินยังเดินอยู่ — เข้าหน้าเว็บ vast.ai แล้วคืนเดี๋ยวนี้ อย่าปล่อยไว้ข้ามคืน")
    else:
        print("เหลือ 0 instance ในบัญชี — จบวัน ไม่เผาเงินต่อแล้ว")


def cmd_blacklist(a):
    bl = load_blacklist()
    if a.action == "clear":
        BLACKLIST_FILE.unlink(missing_ok=True)
        print(f"ล้างบัญชีดำแล้ว ({len(bl)} เครื่อง) — ครั้งหน้าจะกลับไปเลือกเครื่องพวกนี้ได้อีก")
        return
    if a.action == "add":
        if not a.machine_id:
            sys.exit("ต้องบอก machine_id ด้วย: python presentation.py blacklist add 149000 "
                     "--reason 'เน็ตช้า'\n"
                     "   (machine_id ดูได้จาก vastai show instances คอลัมน์ Machine)")
        blacklist_add(a.machine_id, a.reason or "สั่งแบนเอง")
        return
    if not bl:
        print("ยังไม่มีเครื่องไหนถูกแบน")
        return
    print(f"เครื่องที่ถูกแบนไว้ {len(bl)} เครื่อง (ไฟล์: {BLACKLIST_FILE.name})")
    for mid, info in sorted(bl.items(), key=lambda kv: kv[1].get("at", ""), reverse=True):
        print(f"  {mid:>9}  {info.get('gpu', '?'):<22} {info.get('at', '?')}  "
              f"{info.get('reason', '')}")
    print("\nล้างทั้งหมด: python presentation.py blacklist clear")


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
    up.add_argument("--max-price", type=float, default=2.0, help="เพดาน $/ชม.")
    up.add_argument("--yes", action="store_true", help="ไม่ต้องถามยืนยันก่อนเช่า")
    attach = sub.add_parser("attach", help="ต่อกับเครื่องที่เช่าเองจากหน้าเว็บ vast.ai แล้ว (ข้าม auto-select)")
    attach.add_argument("instance_id", type=int, help="instance ID จากหน้าเว็บ vast.ai (คอลัมน์ ID)")
    attach.add_argument("--model", choices=list(MODELS), default="destrier")
    for name in ("status", "tunnel", "smoke"):
        sub.add_parser(name)
    down = sub.add_parser("down")
    down.add_argument("--bad", metavar="เหตุผล",
                      help="คืนเพราะเครื่องมีปัญหา — ขึ้นบัญชีดำไม่ให้เช่าซ้ำ")
    bl = sub.add_parser("blacklist", help="ดู/ล้าง/เพิ่มรายชื่อเครื่องที่ใช้ไม่ได้")
    bl.add_argument("action", nargs="?", choices=["list", "clear", "add"], default="list")
    bl.add_argument("machine_id", nargs="?", help="ใช้กับ add เท่านั้น")
    bl.add_argument("--reason", default="")
    a = ap.parse_args()
    {"up": cmd_up, "attach": cmd_attach, "status": cmd_status, "tunnel": cmd_tunnel,
     "smoke": cmd_smoke, "down": cmd_down, "blacklist": cmd_blacklist}[a.cmd](a)


if __name__ == "__main__":
    main()
