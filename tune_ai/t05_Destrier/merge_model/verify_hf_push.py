#!/usr/bin/env python3
"""
verify_hf_push.py — Day-of-Shame guard สำหรับรอบที่ใช้ push_to_hub:true (t05_Courser/t44_Voldemort)

ต่างจาก pull_and_verify_t03.py (scp adapter ลงเครื่องเรา แล้วเทียบ sha256 local-vs-remote)
รอบนี้ Trainer อัปตรงจากเครื่องเช่าขึ้น HF เอง (push_to_hub:true) — ไม่มีขั้น "pull ลงเครื่องเรา"
ให้เทียบ sha256 ได้ ความเสี่ยงเปลี่ยนเป็น "อัปเงียบๆ ล้มเหลวกลางทาง (เน็ตหลุด/token หมดอายุ)
แล้วสคริปต์เทรนจบแบบไม่ error" — ตัวนี้เช็คว่าไฟล์ขึ้น HF repo จริง ครบ ขนาดตรงกับของ local
ก่อนอนุญาต destroy instance

รัน (บนเครื่องเช่า หลังเทรนจบ ก่อน destroy):
    python3 verify_hf_push.py --repo dacarokann/Courser_a --local-dir outputs_t05_fold0

ต้องเห็น "✅ PASS" เท่านั้น — อะไรอื่นคือ FAIL ห้าม destroy
"""
import argparse
import sys
from pathlib import Path

from huggingface_hub import HfApi

REQUIRED_SUFFIXES = ("adapter_config.json", ".safetensors")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="เช่น dacarokann/Courser_a")
    ap.add_argument("--local-dir", required=True, help="output_dir ที่ Trainer เซฟ adapter ไว้")
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

    print(f"✅ PASS — {args.repo}: {len(remote_files)} ไฟล์บน HF, "
          f"{biggest_local.name} ขนาดตรง ({local_size:,} bytes) — destroy ได้")


if __name__ == "__main__":
    main()
