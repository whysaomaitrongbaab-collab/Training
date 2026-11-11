#!/usr/bin/env python3
"""make_bundle.py — รวมทุกอย่างที่การ์ดเทรน t07 ต้องใช้เป็น tar เดียว (ไม่บีบอัด) + manifest + sha256 (รันบน PC)

  python make_bundle.py                                 # อ่าน t07_Palfrey/data/ → D:\\00mk\\steel project\\training\\t07_bundle\\
  python make_bundle.py --out <dir> [--tr <ราก Training>] [--data <โฟลเดอร์ jsonl>]

ในไฟล์ (path เทียบรากรีโป Training — แตกที่ /workspace/Training บนการ์ด):
  ทุกรูปที่ data/*.jsonl อ้างถึง (ต้องมีจริงทุกไฟล์ ไม่งั้นหยุด) · data/*.jsonl · manifest.json · prompt tree
  (_common.md, pass0/, pass2/) · train_t07.py onstart_t07.sh run_fold.sh gate2_* · tune_ai/verify_hf_push.py
  · freeze_train.txt ถ้ามี (pip freeze จากการ์ด gate 2 — การ์ด gate 3 ลงตามนี้, Lesson 18a)
  ไม่ใส่ data_raw/ (ก่อนล้าง) · ไม่ใส่ token/config ใดๆ (มีด่านสแกน) · .sh แปลง CRLF→LF ตอนใส่ tar (autocrlf=true)
ผลใน --out: t07_bundle.tar · t07_bundle.tar.sha256 (ใช้ sha256sum -c) · BUNDLE_MANIFEST.sha256 (ทุกไฟล์ LF —
  อยู่ใน tar ที่ tune_ai/t07_Palfrey/ ด้วย: หลังแตก `sha256sum -c --quiet tune_ai/t07_Palfrey/BUNDLE_MANIFEST.sha256`)
"""
import argparse
import hashlib
import io
import json
import re
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = Path(r"D:\00mk\steel project\training\t07_bundle")
REL_T07 = "tune_ai/t07_Palfrey"
SCRIPTS = ["train_t07.py", "onstart_t07.sh", "run_fold.sh", "gate2_smoke.sh", "gate2_check.py",
           "gate2_hf_write.py", "manifest.json"]
OPTIONAL = ["freeze_train.txt"]
SECRET_RE = re.compile(rb"hf_[A-Za-z0-9]{30,}|service_role|SUPABASE_KEY")
TEXT_EXT = {".py", ".sh", ".md", ".json", ".jsonl", ".txt"}


def collect(tr, data):
    """{arc: source} + จำนวนรูป — หยุดทันทีถ้าขาดอะไร (ส่งของไม่ครบขึ้นการ์ด = จ่ายเงินแล้วเทรนไม่ได้)"""
    t07 = tr / REL_T07
    files, imgs = {}, set()
    jsonls = sorted(data.glob("*.jsonl"))
    if not jsonls:
        raise SystemExit(f"⛔ ไม่มี *.jsonl ใน {data}")
    for j in jsonls:
        files[f"{REL_T07}/data/{j.name}"] = j
        with open(j, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    for m in json.loads(line)["messages"]:
                        if isinstance(m["content"], list):
                            imgs.update(c["image"] for c in m["content"] if c.get("type") == "image")
    bad = [p for p in imgs if p.startswith(("/", "\\")) or ":" in p or ".." in Path(p).parts]
    if bad:
        raise SystemExit(f"⛔ path รูปต้องเทียบราก Training: {bad[:3]}")
    missing = sorted(p for p in imgs if not (tr / p).is_file())
    if missing:
        raise SystemExit(f"⛔ รูปหาย {len(missing)} ไฟล์ เช่น {missing[:5]}")
    files.update({p: tr / p for p in imgs})
    for s in SCRIPTS:
        if not (t07 / s).is_file():
            raise SystemExit(f"⛔ ไม่มี {t07 / s}")
        files[f"{REL_T07}/{s}"] = t07 / s
    prompts = [p for p in [t07 / "_common.md", *sorted((t07 / "pass0").rglob("*")), *sorted((t07 / "pass2").rglob("*"))]
               if p.is_file() and "__pycache__" not in p.parts]
    if not (t07 / "_common.md").is_file() or not any(p.name.startswith("prompt_") for p in prompts):
        raise SystemExit(f"⛔ prompt tree ไม่ครบใน {t07} (_common.md + pass0/ + pass2/<sub>/prompt_<sub>.md)")
    files.update({p.relative_to(tr).as_posix(): p for p in prompts})
    verify = tr / "tune_ai" / "verify_hf_push.py"
    if not verify.is_file():
        raise SystemExit(f"⛔ ไม่มี {verify}")
    files["tune_ai/verify_hf_push.py"] = verify
    files.update({f"{REL_T07}/{s}": t07 / s for s in OPTIONAL if (t07 / s).is_file()})
    return files, len(imgs)


def write_bundle(files, out):
    out.mkdir(parents=True, exist_ok=True)
    tar_p, part = out / "t07_bundle.tar", out / "t07_bundle.tar.part"
    for old in (tar_p, out / "t07_bundle.tar.sha256", out / "BUNDLE_MANIFEST.sha256"):
        old.unlink(missing_ok=True)       # ล้มกลางทาง = ไม่มี tar/sha ชุดเก่าค้างให้อัปผิดตัว (เหลือแค่ .part)
    lines, total, conv, now = [], 0, [], int(time.time())

    def add(t, arc, data, mode):
        ti = tarfile.TarInfo(arc)
        ti.size, ti.mode, ti.mtime = len(data), mode, now
        t.addfile(ti, io.BytesIO(data))

    with tarfile.open(part, "w", format=tarfile.PAX_FORMAT) as t:
        for arc in sorted(files):
            data = files[arc].read_bytes()
            if arc.endswith(".sh") and b"\r" in data:
                data = data.replace(b"\r\n", b"\n")
                conv.append(arc)
                if b"\r" in data:
                    raise SystemExit(f"⛔ {arc} มี CR ที่ไม่ใช่ CRLF — แก้ไฟล์ก่อน")
            if Path(arc).suffix in TEXT_EXT and SECRET_RE.search(data):
                raise SystemExit(f"⛔ {arc} มีข้อความหน้าตาเหมือน token/key — ไม่รวม bundle")
            add(t, arc, data, 0o755 if arc.endswith(".sh") else 0o644)
            lines.append(f"{hashlib.sha256(data).hexdigest()}  {arc}\n")
            total += len(data)
        man = "".join(lines).encode("utf-8")
        add(t, f"{REL_T07}/BUNDLE_MANIFEST.sha256", man, 0o644)
    part.replace(tar_p)
    (out / "BUNDLE_MANIFEST.sha256").write_bytes(man)
    h = hashlib.sha256()
    with open(tar_p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    (out / "t07_bundle.tar.sha256").write_bytes(f"{h.hexdigest()}  t07_bundle.tar\n".encode())
    with tarfile.open(tar_p) as t:
        n = len(t.getnames())
    if n != len(files) + 1:
        raise SystemExit(f"⛔ tar มี {n} ไฟล์ ไม่ใช่ {len(files) + 1}")
    return tar_p, h.hexdigest(), total, conv


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tr", default=str(HERE.parent.parent), help="รากรีโป Training")
    ap.add_argument("--data", default=None, help="ค่าเริ่ม <tr>/tune_ai/t07_Palfrey/data")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args(argv)
    tr = Path(a.tr).resolve()
    data = Path(a.data) if a.data else tr / REL_T07 / "data"
    out = Path(a.out).resolve()
    if out == tr or tr in out.parents:
        raise SystemExit(f"⛔ --out ต้องอยู่นอกรีโป ({out})")
    files, n_img = collect(tr, data)
    tar_p, sha, total, conv = write_bundle(files, out)
    print(f"✓ {tar_p}  {tar_p.stat().st_size / 1e9:.2f} GB · {len(files) + 1} ไฟล์ (รูป {n_img}) · "
          f"เนื้อไฟล์ {total / 1e9:.2f} GB")
    print(f"  sha256 {sha}" + (f" · แปลง CRLF→LF: {conv}" if conv else ""))
    print(f"  {'freeze_train.txt รวมแล้ว' if f'{REL_T07}/freeze_train.txt' in files else '⚠️ ไม่มี freeze_train.txt (gate 2 ยังไม่ได้ส่งกลับ — gate 3 จะลงตาม PIN_SET แทน)'}")
    print(f"  ต่อ: python {HERE / 'hf_setup.py'} (dry-run) → --apply อัปขึ้น dataset repo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
