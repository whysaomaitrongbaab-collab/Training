#!/usr/bin/env python3
"""pull_and_verify_t03.py — ดึง LoRA adapter ลงเครื่องเรา แล้ว "พิสูจน์" ว่าครบจริงก่อน destroy

ทำไมต้องมีไฟล์นี้: 2026-07-21 (DAY OF SHAME) เสีย adapter 7.5GB + merged 66GB + GGUF 21GB
ถาวรเพราะ destroy ก่อนที่ไฟล์จะปลอดภัยจริง — "คิดว่าเซฟแล้ว" กับ "พิสูจน์แล้วว่าเซฟ" ไม่เหมือนกัน
สคริปต์นี้เทียบ **ชื่อไฟล์ + ขนาดไบต์ ทีละไฟล์ remote-vs-local** แล้วบอก PASS/FAIL ชัดๆ
ห้าม destroy จนกว่าจะเห็น ✅ PASS

    python3 pull_and_verify_t03.py                       # ดึง + ตรวจ
    python3 pull_and_verify_t03.py --verify-only         # ตรวจอย่างเดียว (ดึงมาแล้ว)
"""
import argparse
import subprocess
import sys
from pathlib import Path

SSH_PORT = "21382"
SSH_HOST = "root@76.100.228.184"
REMOTE_DIRS = ["/workspace/tune/outputs_t03/lora", "/workspace/tune/ผล_t03"]
LOCAL_ROOT = Path(__file__).resolve().parent.parent / "ผล_t03_run"   # tune_ai/t03/ผล_t03_run/


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def remote_listing(d):
    """คืน {relative_path: size} ของไฟล์ทั้งหมดใต้ d (ว่าง = ไม่มีโฟลเดอร์นั้น)"""
    r = sh(f'ssh -p {SSH_PORT} {SSH_HOST} "cd {d} 2>/dev/null && find . -type f -printf \'%s %p\\n\'"')
    out = {}
    for line in r.stdout.splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            out[parts[1].lstrip("./")] = int(parts[0])
    return out


def remote_sha(d):
    """sha256 ของทุกไฟล์ใต้ d — ขนาดตรงกันยังพลาดได้ (ไฟล์เสียระหว่างโอนโดยขนาดเท่าเดิม)
    ก่อน destroy ซึ่งลบต้นฉบับถาวร ต้องเทียบ checksum ไม่ใช่แค่ขนาด"""
    r = sh(f'ssh -p {SSH_PORT} {SSH_HOST} '
           f'"cd {d} 2>/dev/null && find . -type f -exec sha256sum {{}} +"')
    out = {}
    for line in r.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            out[parts[1].lstrip("./")] = parts[0]
    return out


def local_sha(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--fast", action="store_true",
                    help="ข้าม sha256 เทียบแค่ขนาด — ใช้เช็คระหว่างทางเท่านั้น ห้ามใช้ก่อน destroy")
    a = ap.parse_args()
    LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

    all_ok = True
    verified_dirs = 0        # กัน "PASS เพราะไม่มีอะไรให้ตรวจ" — ดูท้ายไฟล์
    adapter_ok = False
    for rd in REMOTE_DIRS:
        name = Path(rd).name
        local = LOCAL_ROOT / name
        remote = remote_listing(rd)
        if not remote:
            print(f"⏭  {rd} — ไม่มีบนเครื่องเช่า (ข้าม)")
            continue
        print(f"\n=== {rd} → {local}")
        print(f"    remote: {len(remote)} ไฟล์ รวม {sum(remote.values()) / 1024**3:.2f} GB")
        if not a.verify_only:
            local.mkdir(parents=True, exist_ok=True)
            r = sh(f'scp -P {SSH_PORT} -r "{SSH_HOST}:{rd}/." "{local}/"')
            if r.returncode != 0:
                print(f"    ❌ scp ล้มเหลว: {r.stderr.strip()[:200]}")
                all_ok = False
                continue

        missing, mismatch = [], []
        rsha = {} if a.fast else remote_sha(rd)
        if rsha:
            print(f"    เทียบ sha256 ทีละไฟล์ ({len(rsha)} ไฟล์)…")
        for rel, size in sorted(remote.items()):
            f = local / rel
            if not f.exists():
                missing.append(rel)
            elif f.stat().st_size != size:
                mismatch.append(f"{rel} (ขนาด remote {size} vs local {f.stat().st_size})")
            elif rel in rsha and local_sha(f) != rsha[rel]:
                mismatch.append(f"{rel} (sha256 ไม่ตรง — ไฟล์เสียระหว่างโอน)")
            elif rsha and rel not in rsha:
                mismatch.append(f"{rel} (ไม่มี sha256 ฝั่ง remote — ตรวจไม่ได้)")
        if missing or mismatch:
            all_ok = False
            for m in missing[:10]:
                print(f"    ❌ ขาด: {m}")
            for m in mismatch[:10]:
                print(f"    ❌ ขนาดไม่ตรง: {m}")
            if len(missing) > 10 or len(mismatch) > 10:
                print(f"    … ขาด {len(missing)} / ไม่ตรง {len(mismatch)} รายการ")
        else:
            print(f"    ✅ ครบทุกไฟล์ ขนาดตรงทุกไฟล์ ({len(remote)} ไฟล์)")
            verified_dirs += 1
            if name == "lora":
                # adapter ต้องมีทั้งน้ำหนักและ config ถึงจะโหลดกลับมาใช้ได้จริง
                need_w = any(k.endswith((".safetensors", ".bin")) for k in remote)
                need_c = any("adapter_config.json" in k for k in remote)
                adapter_ok = need_w and need_c
                if not adapter_ok:
                    all_ok = False
                    print(f"    ❌ lora/ ไม่มี{'น้ำหนัก (.safetensors/.bin)' if not need_w else ''}"
                          f"{' และ ' if not need_w and not need_c else ''}"
                          f"{'adapter_config.json' if not need_c else ''} — โหลดกลับมาใช้ไม่ได้")

    # ⛔ ด่านสำคัญที่สุด: "ไม่มีอะไรให้ตรวจ" ต้องไม่ใช่ PASS
    # (บั๊กที่เจอในสคริปต์ตัวเองตอน dry-run 2026-08-24 — ก่อนเทรนเสร็จมันขึ้น PASS
    #  ทั้งที่ยังไม่มีไฟล์อะไรเลย = ไฟเขียวที่ไม่ได้ยืนยันอะไร คือรูปแบบเดียวกับ DAY OF SHAME)
    if verified_dirs == 0:
        all_ok = False
        print("\n❌ ไม่พบไฟล์ผลลัพธ์ใดๆ บนเครื่องเช่า — ยังไม่มีอะไรให้ verify")
    elif not adapter_ok:
        all_ok = False
        print("\n❌ ไม่ได้ verify LoRA adapter (outputs_t03/lora) — ไฟล์ที่สำคัญที่สุดยังไม่ปลอดภัย")

    print("\n" + ("=" * 60))
    if all_ok and a.fast:
        all_ok = False
        print("❌ รันด้วย --fast (ไม่ได้เทียบ sha256) — ไม่นับเป็นไฟเขียวสำหรับ destroy")
        print("   รันใหม่โดยไม่ใส่ --fast ก่อนเสมอ")

    if all_ok:
        print("✅ PASS — ไฟล์อยู่บนเครื่องเราครบ ขนาดตรง และ sha256 ตรงทุกไฟล์ → destroy ได้")
        print(f"   ที่: {LOCAL_ROOT}")
        print("   ขั้นถัดไปก่อน destroy: อัปขึ้น HuggingFace จากเครื่องนี้ (token ไม่ต้องไปอยู่บนเครื่องเช่า)")
    else:
        print("❌ FAIL — ⛔ ห้าม destroy instance เด็ดขาด ไฟล์ยังไม่ปลอดภัย")
        print("   (destroy บน Vast.ai = ลบถาวรทันที กู้ไม่ได้ — DAY OF SHAME 2026-07-21)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
