#!/usr/bin/env python3
"""offers_t07.py — หา offer การ์ดเทรน t07 บน vast.ai (PC) · อ่านอย่างเดียว: ไม่เช่า ไม่คืน ไม่แตะ instance ใด

  python offers_t07.py                 # gate 2: ดู 6 ตัวถูกสุด
  python offers_t07.py --n 4           # gate 3: ต้องการ 4 ใบ

ตัวกรองชุดเดียวกับ Constistant build_vllm_card.py/presentation.py (ไม่ import — อ่านแค่ blacklist.json):
  gpu_ram>=90 num_gpus=1 reliability>0.99 inet_down>500 rentable=true verified=true direct_port_count>=1
  + ชื่อการ์ดมี "RTX PRO 6000" (ทั้งสูตรทดสอบบน sm120 เท่านั้น) + ตัดเครื่องในบัญชีดำ (machine_id)
  ประเทศ: กลุ่มภาษาอังกฤษก่อน (US,CA,GB,AU,NZ,IE — มะขามขอ 8 พ.ย.) ไม่พอ n ใบค่อยเติมจากทุกประเทศ (ติดป้าย any-geo)
  ราคาใส่ --storage ให้คิดดิสก์จริง (ราคาค่าเริ่มของ search คิดดิสก์ 5 GB) · RAM เครื่อง ≥ --min-ram GB
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE = ("gpu_ram>=90 num_gpus=1 reliability>0.99 inet_down>500 rentable=true verified=true "
        "direct_port_count>=1")
GEO = "US,CA,GB,AU,NZ,IE"
GPU_MATCH = "RTX PRO 6000"
BLACKLIST = Path(r"D:\00mk\steel project\งานสมบูรณ์\Constistant\server\purson-worker\blacklist.json")


def search(q, disk):
    r = subprocess.run(["vastai", "search", "offers", q, "-o", "dph_total", "--storage", str(disk), "--raw"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise SystemExit(f"⛔ vastai search ล้ม: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout or "[]")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--disk", type=int, default=200, help="GB — t07 เทรน: ฐาน 72 + bundle ~4 + checkpoint ~12")
    ap.add_argument("--min-ram", type=float, default=64, help="RAM เครื่อง (GB) ขั้นต่ำ")
    a = ap.parse_args(argv)
    try:
        bl = set(json.loads(BLACKLIST.read_text(encoding="utf-8")))
    except Exception:
        bl = set()
        print(f"(อ่านบัญชีดำไม่ได้/ไม่มี: {BLACKLIST} — ไม่ตัดเครื่องไหน)")
    q = f"{BASE} disk_space>={a.disk}"

    def keep(offers, tag):
        out = []
        for o in offers:
            if GPU_MATCH not in (o.get("gpu_name") or "") or str(o.get("machine_id")) in bl:
                continue
            if (o.get("cpu_ram") or 0) / 1024 < a.min_ram:        # raw = MB (วัด 11 พ.ย.: 184231 ≈ 180 GB)
                continue
            out.append(dict(o, _tag=tag))
        return out

    rows = keep(search(q + f" geolocation in [{GEO}]", a.disk), "EN")
    if len(rows) < a.n:
        seen = {o["id"] for o in rows}
        rows += [o for o in keep(search(q, a.disk), "any-geo") if o["id"] not in seen]
    print(f"q: {q}  + '{GPU_MATCH}' + ไม่อยู่ในบัญชีดำ ({len(bl)} เครื่อง) + RAM ≥ {a.min_ram:g} GB · ราคารวมดิสก์ {a.disk} GB")
    for o in rows[:max(a.n, 6)]:
        print(f"  offer {o['id']:>9}  machine {o.get('machine_id'):>7}  ${o.get('dph_total', 0):.3f}/ชม.  "
              f"{o.get('gpu_name'):<20} {o.get('geolocation') or '?':<24} {o['_tag']:<7} "
              f"net {o.get('inet_down', 0):.0f} Mbps  RAM {(o.get('cpu_ram') or 0) / 1024:.0f} GB  "
              f"disk {o.get('disk_space', 0):.0f} GB  cuda {o.get('cuda_max_good')}")
    if len(rows) < a.n:
        print(f"⚠️  ได้แค่ {len(rows)} ใบ ต้องการ {a.n}")
        return 1
    top = rows[:a.n]
    print(f"รวม {a.n} ใบถูกสุด: ${sum(o.get('dph_total', 0) for o in top):.2f}/ชม. "
          f"(ราคาขยับเร็ว — 11 พ.ย. 00:18→00:30 ถูกสุด $1.09→$1.61)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
