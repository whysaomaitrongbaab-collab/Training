#!/usr/bin/env python3
"""gate2_hf_write.py — ทดสอบว่า HF_TOKEN (อ่านจาก env เท่านั้น) เขียน repo ที่ระบุได้จริง: อัปไฟล์ probe → อ่านกลับ → ลบ

  python gate2_hf_write.py --repo dacarokann/Palfrey_a [--repo-type model]
  python gate2_hf_write.py --selftest          # ตรวจตัวแยก token กว้าง/แคบ แบบไม่ใช้เน็ต

ใช้ใน gate 2 (ข้อ 6) และใน run_fold.sh ก่อนเทรน 10+ ชม. (กันคลาส Day of Shame: เทรนจบแล้วค่อยรู้ว่า push ไม่ได้)
⛔ ปฏิเสธ token ที่เขียนได้ทุก repo ของ user/org (Lesson 22: ห้าม token กว้างบนการ์ดเช่า) — ใส่ --allow-broad ถ้าตั้งใจจริง
ไม่พิมพ์/ไม่เขียน token เด็ดขาด · ไม่อ่าน token ที่เก็บไว้ในเครื่อง (~/.cache/huggingface/token) — env เท่านั้น
"""
import argparse
import hashlib
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path


def token_is_broad(who):
    """True = token เขียนได้ทุก repo ของ user/org · None = อ่านโครงสร้างไม่ออก (บอกแล้วไปต่อ ไม่เดา)"""
    acc = (who.get("auth") or {}).get("accessToken") or {}
    role = acc.get("role")
    if role == "write":
        return True
    if role == "read":
        return False
    if role != "fineGrained":
        return None
    for s in (acc.get("fineGrained") or {}).get("scoped") or []:
        if (s.get("entity") or {}).get("type") in ("user", "org") and "repo.write" in (s.get("permissions") or []):
            return True
    return False


def _selftest():
    tok = lambda role, scoped=(): {"auth": {"accessToken": {"role": role, "fineGrained": {"scoped": list(scoped)}}}}  # noqa: E731
    user_w = {"entity": {"type": "user", "name": "dacarokann"}, "permissions": ["repo.content.read", "repo.write"]}
    repo_w = {"entity": {"type": "model", "name": "dacarokann/Palfrey_a"}, "permissions": ["repo.write"]}
    assert token_is_broad(tok("write")) is True
    assert token_is_broad(tok("read")) is False
    assert token_is_broad(tok("fineGrained", [user_w])) is True        # = token t44 ของ PC (วัด whoami 11 พ.ย.)
    assert token_is_broad(tok("fineGrained", [repo_w])) is False       # token ที่ควรใช้บนการ์ด
    assert token_is_broad(tok("fineGrained", [repo_w, user_w])) is True
    assert token_is_broad({}) is None
    print("selftest ok")


def lfs_probe(api, repo, repo_type, mb):
    """อัปไฟล์สุ่ม mb MB (ทาง LFS) → อ่าน sha256 ของ LFS กลับจาก get_paths_info (เหมือน train_t07.py/verify_hf_push.py --sha)
    → ต้องเท่ากับ sha256 ในเครื่อง → ลบ · ผ่านเมื่อตรงเท่านั้น (ไม่มี lfs/ไม่ตรง = FAIL ไม่เดา)"""
    path = f"_gate2_lfs_probe_{uuid.uuid4().hex[:8]}.bin"
    blob = os.urandom(mb * 1024 * 1024)
    want = hashlib.sha256(blob).hexdigest()
    uploaded, ok = False, False
    try:
        api.upload_file(path_or_fileobj=blob, path_in_repo=path, repo_id=repo, repo_type=repo_type,
                        commit_message="gate2 LFS probe")
        uploaded = True
        info = api.get_paths_info(repo, [path], repo_type=repo_type, expand=True)
        got = info[0].lfs.sha256 if info and getattr(info[0], "lfs", None) else None
        ok = got == want
        print(f"✓ LFS {mb} MB: sha256 บน HF ตรงกับในเครื่อง" if ok else
              f"⛔ LFS sha256 บน HF ({got}) ≠ ในเครื่อง ({want}) — ไฟล์นี้ไม่มี lfs metadata หรือไม่ใช่ตัวที่อัป")
    except Exception as e:
        print(f"❌ FAIL — ทดสอบอัปไฟล์ LFS ไม่ได้ ({type(e).__name__}: {str(e)[:200]})")
    finally:
        if uploaded:
            try:
                api.delete_file(path, repo_id=repo, repo_type=repo_type, commit_message="gate2 LFS probe cleanup")
                print("✓ ลบไฟล์ LFS probe แล้ว")
            except Exception as e:
                print(f"⚠️  ลบไฟล์ LFS probe ไม่ได้ ({type(e).__name__}) — ลบเองที่ {repo}/{path}")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--repo-type", default="model", choices=["model", "dataset"])
    ap.add_argument("--allow-broad", action="store_true")
    ap.add_argument("--lfs-mb", type=int, default=0,
                    help="[review 11 พ.ย.] >0 = อัปไฟล์สุ่มขนาดนี้ (ต้อง >10 MB ถึงไปทาง LFS) แล้วเช็ค lfs.sha256 จาก get_paths_info "
                         "= ทางเดียวกับที่ train_t07.py ใช้ยืนยัน adapter ท้ายรอบ — ไม่ให้เพิ่งรู้ว่าพังหลังเทรน 8 ชม. (gate2_smoke ใช้ 16)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return 0
    if not a.repo:
        ap.error("--repo จำเป็น")
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not tok:
        print("❌ FAIL — ไม่มี HF_TOKEN ใน env (บนการ์ด: read -rs HF_TOKEN && export HF_TOKEN)")
        return 2
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi(token=tok)
    try:
        who = api.whoami()
    except Exception as e:
        print(f"❌ FAIL — whoami ไม่ผ่าน ({type(e).__name__}) — token ผิด/หมดอายุ?")
        return 2
    acc = (who.get("auth") or {}).get("accessToken") or {}
    print(f"token: '{acc.get('displayName')}' role={acc.get('role')} user={who.get('name')}")
    broad = token_is_broad(who)
    if broad and not a.allow_broad:
        print("❌ FAIL — token นี้เขียนได้ทุก repo ของ user (เช่น destrier, destrier-merged) "
              "ห้ามใช้บนการ์ดเช่า (Lesson 22) — สร้าง fine-grained token ที่เขียนได้เฉพาะ repo ของ t07")
        return 3
    if broad is None:
        print("⚠️  อ่านขอบเขต token ไม่ออก (โครงสร้าง whoami เปลี่ยน?) — ทดสอบเขียนต่อ แต่ต้องเช็คเองว่าไม่ใช่ token กว้าง")
    path = f"_gate2_probe_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.txt"
    body = f"t07 gate2 write probe {time.strftime('%F %T')}\n"
    uploaded, ok = False, False
    try:
        api.upload_file(path_or_fileobj=body.encode("utf-8"), path_in_repo=path, repo_id=a.repo,
                        repo_type=a.repo_type, commit_message="gate2 write probe")
        uploaded = True
        with tempfile.TemporaryDirectory() as td:
            got = Path(hf_hub_download(a.repo, path, repo_type=a.repo_type, token=tok, local_dir=td)).read_text(
                encoding="utf-8")
        ok = got == body
        print("✓ อัป + อ่านกลับตรงกัน" if ok else "⛔ อ่านกลับไม่ตรง")
    except Exception as e:
        print(f"❌ FAIL — เขียน/อ่าน {a.repo} ไม่ได้ ({type(e).__name__}: {str(e)[:200]})")
    finally:
        if uploaded:
            try:
                api.delete_file(path, repo_id=a.repo, repo_type=a.repo_type, commit_message="gate2 write probe cleanup")
                print("✓ ลบไฟล์ probe แล้ว")
            except Exception as e:
                print(f"⚠️  ลบไฟล์ probe ไม่ได้ ({type(e).__name__}) — ลบเองที่ {a.repo}/{path}")
    if ok and a.lfs_mb:
        ok = lfs_probe(api, a.repo, a.repo_type, a.lfs_mb)
    print(f"✅ PASS — {a.repo} เขียนได้" if ok else f"❌ FAIL — {a.repo}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
