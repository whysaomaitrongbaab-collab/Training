#!/usr/bin/env python3
"""
verify_hf_push.py — Day-of-Shame guard สำหรับรอบที่ใช้ push_to_hub:true (t05_Courser/t06_Voldemort)

ต่างจาก pull_and_verify_t03.py (scp adapter ลงเครื่องเรา แล้วเทียบ sha256 local-vs-remote)
รอบนี้ Trainer อัปตรงจากเครื่องเช่าขึ้น HF เอง (push_to_hub:true) — ไม่มีขั้น "pull ลงเครื่องเรา"
ให้เทียบ sha256 ได้ ความเสี่ยงเปลี่ยนเป็น "อัปเงียบๆ ล้มเหลวกลางทาง (เน็ตหลุด/token หมดอายุ)
แล้วสคริปต์เทรนจบแบบไม่ error" — ตัวนี้เช็คว่าไฟล์ขึ้น HF repo จริง ครบ ขนาดตรงกับของ local
ก่อนอนุญาต destroy instance

รัน (บนเครื่องเช่า หลังเทรนจบ ก่อน destroy):
    python3 verify_hf_push.py --repo dacarokann/Courser_a --local-dir outputs_t05_fold0
    python verify_hf_push.py --repo dacarokann/Palfrey_a --local-dir outputs_t07_fold0 --sha   # t07

--sha (2026-11-11, t07): ขนาดอย่างเดียวแยก checkpoint ไม่ออก (ทุก checkpoint ขนาด 3,781,033,488 B เท่ากัน) —
  เทียบ sha256 ของ LFS ของ adapter_model.safetensors ที่ราก repo (metadata ฟรี ไม่ต้องดาวน์โหลด, Lesson 23)
  กับ sha256 ของไฟล์ adapter สุดท้ายบนเครื่อง: --local-file ถ้าใส่ · ไม่งั้น <local-dir>/lora/ · ไม่งั้น <local-dir>/
  (ไม่เดาจาก checkpoint-*)

ต้องเห็น "✅ PASS" เท่านั้น — อะไรอื่นคือ FAIL ห้าม destroy
"""
import argparse
import hashlib
import sys
from pathlib import Path

from huggingface_hub import HfApi

REQUIRED_SUFFIXES = ("adapter_config.json", ".safetensors")
ADAPTER = "adapter_model.safetensors"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def check_sha(api, repo, local_dir, local_file):
    """คืน (ผ่าน?, ข้อความ) — sha256 ของ LFS บน HF ต้องเท่ากับไฟล์บนเครื่อง"""
    cands = [Path(local_file)] if local_file else [local_dir / "lora" / ADAPTER, local_dir / ADAPTER]
    local = next((p for p in cands if p.is_file()), None)
    if local is None:
        return False, f"ไม่พบ adapter สุดท้ายบนเครื่อง ({', '.join(map(str, cands))})"
    try:
        info = api.get_paths_info(repo, [ADAPTER], expand=True)
    except Exception as e:
        return False, f"เรียก paths-info ไม่ผ่าน: {e}"
    remote = info[0].lfs.sha256 if info and getattr(info[0], "lfs", None) else None
    if remote is None:
        return False, f"ราก repo ไม่มี {ADAPTER} แบบ LFS (ยังไม่ขึ้น หรือไม่ใช่ LFS)"
    mine = sha256_file(local)
    if mine != remote:
        return False, f"sha256 ไม่ตรง: เครื่อง {mine} ({local}) vs HF {remote} — บน HF ไม่ใช่ตัวนี้"
    return True, f"sha256 ตรง {mine} ({local})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="เช่น dacarokann/Courser_a")
    ap.add_argument("--local-dir", required=True, help="output_dir ที่ Trainer เซฟ adapter ไว้")
    ap.add_argument("--sha", action="store_true", help="เทียบ sha256 ของ LFS กับ adapter สุดท้ายบนเครื่องด้วย")
    ap.add_argument("--local-file", default=None, help="ไฟล์ adapter ที่จะเทียบ (ค่าเริ่ม <local-dir>/lora/)")
    args = ap.parse_args()

    local_dir = Path(args.local_dir)
    if not local_dir.is_dir():
        print(f"❌ FAIL — ไม่พบโฟลเดอร์ local {local_dir}")
        sys.exit(1)

    api = HfApi()
    try:
        remote_files = api.list_repo_files(args.repo)
    except Exception as e:
        print(f"❌ FAIL — เรียก HF API ไม่ผ่าน: {e}")
        sys.exit(1)

    if not any(f.endswith(".safetensors") for f in remote_files):
        print(f"❌ FAIL — repo {args.repo} ไม่มีไฟล์ .safetensors เลย (adapter ไม่ขึ้นจริง)")
        sys.exit(1)
    if "adapter_config.json" not in remote_files:
        print(f"❌ FAIL — repo {args.repo} ไม่มี adapter_config.json")
        sys.exit(1)

    # เทียบขนาดไฟล์ safetensors ที่ใหญ่สุดใน local กับตัวที่ตรงชื่อบน remote
    # (ไม่ใช้ sha256 — HF API ไม่คืน sha ตรงๆ ในหนึ่ง call ราคาถูก; ขนาดพอจับ "อัปครึ่งเดียวขาด")
    local_st = sorted(local_dir.rglob("*.safetensors"), key=lambda p: p.stat().st_size, reverse=True)
    if not local_st:
        print(f"❌ FAIL — local {local_dir} ไม่มี .safetensors เลย (เทรนไม่จบ หรือ path ผิด)")
        sys.exit(1)

    biggest_local = local_st[0]
    local_size = biggest_local.stat().st_size
    try:
        info = api.model_info(args.repo, files_metadata=True)
        remote_size = next(
            (f.size for f in info.siblings if f.rfilename == biggest_local.name), None
        )
    except Exception as e:
        print(f"❌ FAIL — ดึงขนาดไฟล์ remote ไม่ได้: {e}")
        sys.exit(1)

    if remote_size is None:
        print(f"❌ FAIL — remote ไม่มีไฟล์ชื่อ {biggest_local.name} (ชื่อไม่ตรง หรือยังไม่ขึ้น)")
        sys.exit(1)
    if remote_size != local_size:
        print(f"❌ FAIL — ขนาดไม่ตรง: local {local_size:,} bytes vs remote {remote_size:,} bytes "
              f"({biggest_local.name}) — อัปน่าจะขาดหาย")
        sys.exit(1)

    sha_note = ""
    if args.sha:
        ok, msg = check_sha(api, args.repo, local_dir, args.local_file)
        if not ok:
            print(f"❌ FAIL — {msg}")
            sys.exit(1)
        sha_note = f" · {msg}"

    print(f"✅ PASS — {args.repo}: {len(remote_files)} ไฟล์บน HF, "
          f"{biggest_local.name} ขนาดตรง ({local_size:,} bytes){sha_note} — destroy ได้")


if __name__ == "__main__":
    main()
