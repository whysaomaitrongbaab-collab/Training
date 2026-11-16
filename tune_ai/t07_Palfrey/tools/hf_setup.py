#!/usr/bin/env python3
"""hf_setup.py — เตรียม Hugging Face สำหรับ t07 (รันบน PC ด้วย token ของ PC — ตัวนี้ห้ามขึ้นการ์ด, Lesson 22)

  python hf_setup.py                    # ค่าเริ่ม = dry-run: พิมพ์ว่าจะทำอะไร (เรียก API แบบอ่านอย่างเดียว) ไม่สร้าง/ไม่อัป
  python hf_setup.py --apply            # (a) สร้าง repo private ที่ยังไม่มี (b) อัป bundle + sha ขึ้น dataset repo
                                        # (c) เทียบ sha256 ของ LFS บน HF กับไฟล์ในเครื่อง
  python hf_setup.py --apply --skip-upload    # (a) อย่างเดียว

repo (D11): dacarokann/Palfrey_{a,b,c,d} (fold) · dacarokann/palfrey (soup) · dacarokann/palfrey-merged · dataset
dacarokann/palfrey-data (bundle) — private ทั้งหมด · ⛔ ไม่แตะ Courser_* / destrier* เด็ดขาด
⚠️ พื้นที่ private ของบัญชีฟรีมีจำกัด (destrier-merged ใช้ไป 71.9 GB) — ดูหน้า storage ก่อน gate 3 · ลบ bundle หลังเทรนได้
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

MODEL_REPOS = [f"dacarokann/Palfrey_{c}" for c in "abcd"] + ["dacarokann/palfrey", "dacarokann/palfrey-merged"]
DATA_REPO = "dacarokann/palfrey-data"
DEFAULT_BUNDLE = Path(r"D:\00mk\steel project\training\t07_bundle")
BUNDLE_FILES = ["t07_bundle.tar", "t07_bundle.tar.sha256", "BUNDLE_MANIFEST.sha256"]
FORBIDDEN = re.compile(r"courser|destrier", re.I)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def remote_sha(api, repo, path, repo_type):
    """sha256 ของ LFS (metadata ฟรี ไม่ต้องดาวน์โหลด — Lesson 23) · None = ไม่มีไฟล์/ไม่ใช่ LFS"""
    try:
        info = api.get_paths_info(repo, [path], repo_type=repo_type, expand=True)
    except Exception:
        return None
    return info[0].lfs.sha256 if info and getattr(info[0], "lfs", None) else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="ทำจริง (ไม่ใส่ = dry-run)")
    ap.add_argument("--bundle-dir", default=str(DEFAULT_BUNDLE))
    ap.add_argument("--skip-upload", action="store_true")
    a = ap.parse_args(argv)
    for r in MODEL_REPOS + [DATA_REPO]:
        if FORBIDDEN.search(r):
            raise SystemExit(f"⛔ {r} — t07 ห้ามแตะ repo ของ t05")
    from huggingface_hub import HfApi, get_token
    if not get_token():
        print("⚠️  ไม่มี token บนเครื่องนี้ — บอกไม่ได้ว่า repo private มีอยู่ไหม (401 = 'บอกไม่ได้', Lesson 22)")
        if a.apply:
            return 2
    api = HfApi()
    tag = "" if a.apply else "[dry-run] "
    print(f"{tag}ผู้ใช้: {api.whoami().get('name') if get_token() else '?'}")

    # (a) repo
    for repo, rtype in [(r, "model") for r in MODEL_REPOS] + [(DATA_REPO, "dataset")]:
        try:
            info = api.repo_info(repo, repo_type=rtype)
            note = "private ✓" if info.private else "⚠️ PUBLIC — ตั้งเป็น private เองที่หน้า Settings ก่อนใช้"
            print(f"  มีแล้ว {rtype:<7} {repo}  {note}")
        except Exception as e:
            if "404" not in str(e) and "RepositoryNotFound" not in type(e).__name__:
                print(f"  ⚠️ เช็ค {repo} ไม่ได้ ({type(e).__name__}) — ไม่สร้างทับ")
                continue
            print(f"  {tag}สร้าง {rtype:<7} {repo}  private")
            if a.apply:
                api.create_repo(repo, repo_type=rtype, private=True, exist_ok=True)

    # (b) + (c) bundle
    if a.skip_upload:
        return 0
    bd = Path(a.bundle_dir)
    missing = [f for f in BUNDLE_FILES if not (bd / f).is_file()]
    if missing:
        print(f"  ยังไม่มี {missing} ใน {bd} — รัน make_bundle.py ก่อน")
        return 1 if a.apply else 0
    want = (bd / "t07_bundle.tar.sha256").read_text(encoding="utf-8").split()[0]
    local = sha256_file(bd / "t07_bundle.tar")
    if local != want:
        raise SystemExit(f"⛔ t07_bundle.tar ในเครื่อง ({local}) ≠ ไฟล์ sha ({want}) — สร้าง bundle ใหม่")
    size = (bd / "t07_bundle.tar").stat().st_size
    print(f"  bundle ในเครื่อง {size / 1e9:.2f} GB sha256 {local}")
    before = remote_sha(api, DATA_REPO, "t07_bundle.tar", "dataset")
    if before == local:
        print(f"  ✓ บน HF มีตัวเดียวกันอยู่แล้ว — ไม่อัปซ้ำ")
    else:
        print(f"  {tag}อัป {BUNDLE_FILES} → dataset {DATA_REPO} (บน HF ตอนนี้: {before or 'ไม่มี'})")
        if a.apply:
            for f in BUNDLE_FILES:
                api.upload_file(path_or_fileobj=str(bd / f), path_in_repo=f, repo_id=DATA_REPO,
                                repo_type="dataset", commit_message=f"t07 bundle {local[:12]}")
    if a.apply:
        after = remote_sha(api, DATA_REPO, "t07_bundle.tar", "dataset")
        if after != local:
            print(f"  ❌ FAIL — sha256 บน HF ({after}) ≠ ในเครื่อง ({local})")
            return 1
        print(f"  ✅ PASS — sha256 บน HF ตรงกับในเครื่อง {local}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
