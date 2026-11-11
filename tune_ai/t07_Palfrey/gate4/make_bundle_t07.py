"""make_bundle_t07.py — รวมทุกอย่างที่ด่าน 4 ต้องใช้บนการ์ดเป็น ft_t07.tar (+ ft_t07.tar.sha256) · รันบน PC

⚠️ UNTESTED บนการ์ด (ร่าง 11 พ.ย. 69) — ลองบน PC แล้ว: รอบแรกด้วย T07_DIR ชี้ t04_Purson · 01:32 ด้วย prompt t07 ตัวจริง
   (123 ไฟล์ · 104.3 MB · แตกแล้ว MANIFEST ผ่าน · bench ซ้อมด้วย dryrun_bench_stub.py ผ่าน)

    python make_bundle_t07.py <โฟลเดอร์ออก>
บนการ์ด: cd /workspace && sha256sum -c ft_t07.tar.sha256 && tar -xf ft_t07.tar && sha256sum -c --quiet ft/MANIFEST.sha256

กติกา:
  · ไม่อ่าน/ไม่ใส่ worker_config.json หรือไฟล์ key ใดๆ — ตรวจชื่อไฟล์ + สแกนหา token ในทุกไฟล์ข้อความก่อนเขียน tar
  · .sh / .txt / .sha256 แปลง CRLF → LF (bash บนการ์ดพังเงียบด้วย \\r) · ไฟล์อื่นตามจริงทุกไบต์ (sha ตรงกับบน PC)
  · ตรวจก่อนห่อ: ภาพ 83b8e52c ตรง SHA256SUMS · PDF บ้านเน็ตตรง proof/04 · launch_vllm_*.txt ตรงกับที่
    presentation.launch_cmd สร้างตอนนี้ (flag ของ production เปลี่ยน = หยุด ไม่ส่งของเก่าขึ้นการ์ด)
  · ชุด worker (โค้ด + prompt + organize.py + cv_scan.py) มาจาก presentation.worker_bundle_sources ตัวจริง
    วาง prompt ไว้ระดับ tune_ai/<รอบ>/ ทั้ง t07_Palfrey (วัด t07) และ t04_Purson (วัด Destrier ซ้ำ ถ้าเลือก)
"""
import hashlib
import io
import os
import re
import sys
import tarfile
import time
from pathlib import Path

sys.dont_write_bytecode = True      # ห้ามเขียน __pycache__ ลง Constistant (อ่านอย่างเดียว)
TR = Path(r"D:\00mk\steel project\training\Training")
TUNE = TR / "tune_ai"
T07 = Path(os.environ.get("T07_DIR", TUNE / "t07_Palfrey"))      # override เฉพาะตอนลองบน PC
T04 = TUNE / "t04_Purson"
G = Path(__file__).resolve().parent
PW = Path(r"D:\00mk\steel project\งานสมบูรณ์\Constistant\server\purson-worker")
P04 = TUNE / "t05_Destrier" / "proof" / "04_vllm_sglang_บนการ์ด"
P06 = TUNE / "t05_Destrier" / "proof" / "06_merged_sha256_verified_2026-11-08.txt"
B83 = Path(r"D:\00mk\steel project\training\t07_bench\83b8e52c")
LF_EXT = (".sh", ".txt", ".sha256")
SECRET = re.compile(rb"hf_[A-Za-z0-9]{30,}|eyJhbGciOi|sk-[A-Za-z0-9]{20,}")
TEXT_EXT = (".py", ".sh", ".txt", ".md", ".json", ".sha256")

sys.path.insert(0, str(PW))
import presentation as P  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check_list(listing, root):
    """บรรทัด '<sha>  <path>' (หรือ '*path') ทุกบรรทัดต้องตรงกับไฟล์จริงใต้ root"""
    bad = []
    for line in listing.decode("utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            h, name = line.split(None, 1)
            if sha((root / name.lstrip("*")).read_bytes()) != h:
                bad.append(name)
    return bad


def git(repo, *args):
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", timeout=60)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def bundle_info():
    """commit + ไฟล์ที่ยังไม่ commit ของทั้งสอง repo ตอนห่อ (Lesson 18d: จดรุ่นไว้ข้างผลวัด) — git อ่านอย่างเดียว"""
    pw_repo = PW.parent.parent
    return (f"ห่อเมื่อ {time.strftime('%Y-%m-%d %H:%M:%S')} · prompt t07 จาก {T07}\n"
            f"Constistant HEAD {git(pw_repo, 'rev-parse', 'HEAD')}\n"
            f"Constistant ยังไม่ commit (server/purson-worker):\n{git(pw_repo, 'status', '--short', '--', 'server/purson-worker') or '-'}\n"
            f"Training HEAD {git(TR, 'rev-parse', 'HEAD')}\n"
            f"Training ยังไม่ commit (tune_ai):\n{git(TR, 'status', '--short', '--', 'tune_ai') or '-'}\n")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    members = {}                                   # arc → bytes

    def add(src, arc):
        data = Path(src).read_bytes()
        members[arc] = data.replace(b"\r\n", b"\n") if arc.endswith(LF_EXT) else data

    for n in ("soup_safetensors.py", "merge_lora_to_base.py", "verify_merge.py",
              "test_soup_layout.py", "fix_destrier_layout.py"):      # fix_ ใช้แค่ให้ test_soup_layout import ได้
        add(TUNE / n, f"ft/tune/{n}")
    for n in ("vllm_build_t07.sh", "run_bench_t07.sh", "stop_server.sh", "dl_destrier_merged.sh",
              "gate_d_t07.py", "tok_parity.py", "launch_vllm_palfrey.txt", "launch_vllm_destrier.txt"):
        add(G / n, f"ft/gate4/{n}")
    add(PW / "vllm_engines.sh", "ft/vllm_engines.sh")
    add(PW / "bench_house.py", "ft/wk/worker/bench_house.py")
    add(P04 / "scripts" / "render_jobs.py", "ft/render_jobs.py")
    add(P04 / "fingerprint" / "mrg.pt", "ft/gate4/destrier_mrg.pt")      # ref ของด่าน D ตอนวัด Destrier ซ้ำ
    for p in sorted((P04 / "webpdf").glob("*.pdf")):
        add(p, f"ft/webpdf/{p.name}")
    add(P04 / "webpdf_sha256.txt", "ft/webpdf/webpdf.sha256")
    lines = [ln for ln in P06.read_bytes().replace(b"\r\n", b"\n").split(b"\n") if ln.strip() and not ln.startswith(b"#")]
    members["ft/gate4/destrier_merged.sha256"] = b"\n".join(lines) + b"\n"
    add(B83 / "job_83b8e52c.json", "ft/bench/job_83b8e52c.json")
    add(B83 / "SHA256SUMS", "ft/bench/SHA256SUMS")
    for p in sorted((B83 / "img83").glob("*.png")):
        add(p, f"ft/bench/img83/{p.name}")
    for prompts in (T07, T04):
        for src, arc in P.worker_bundle_sources({"PURSON_PROMPTS_DIR": str(prompts)}):   # หายไฟล์ = sys.exit ดังๆ
            add(src, f"ft/wk/{arc}")

    # ── ตรวจก่อนห่อ ──
    problems = []
    if len(lines) != 27:
        problems.append(f"destrier_merged.sha256 มี {len(lines)} บรรทัด (proof/06 ต้องมี 26 shard + tokenizer.json)")
    problems += [f"83b8e52c ไม่ตรง SHA256SUMS: {x}" for x in check_list(members["ft/bench/SHA256SUMS"], B83)]
    problems += [f"PDF บ้านเน็ตไม่ตรง proof/04: {x}" for x in check_list(members["ft/webpdf/webpdf.sha256"], P04 / "webpdf")]
    if len([a for a in members if a.startswith("ft/bench/img83/")]) != 29:
        problems.append("ภาพ 83b8e52c ไม่ครบ 29 หน้า")
    old = P.VENV_PY
    P.VENV_PY = "/workspace/venv_vllm/bin/python"
    try:
        for name in ("palfrey", "destrier"):
            m = f"/workspace/{name}_merged"
            want = P.launch_cmd(dict(P.MODELS["destrier-vllm"], model_repo=m), m, "") + "\n"
            if members[f"ft/gate4/launch_vllm_{name}.txt"].decode("utf-8") != want:
                problems.append(f"launch_vllm_{name}.txt ไม่ตรงกับ presentation.launch_cmd ตอนนี้ — สร้างใหม่ก่อน")
    finally:
        P.VENV_PY = old
    for arc, data in members.items():
        low = arc.lower()
        if any(k in low for k in ("worker_config", "gemini", ".env", "token")) and not low.endswith("tok_parity.py"):
            problems.append(f"ชื่อไฟล์น่าสงสัย (key?): {arc}")
        if arc.endswith(TEXT_EXT) and SECRET.search(data):
            problems.append(f"เจอรูปแบบ token/key ใน {arc}")
        if arc.endswith(LF_EXT) and b"\r" in data:
            problems.append(f"ยังมี CR ใน {arc}")
    if problems:
        sys.exit("⛔ ไม่ห่อ:\n   " + "\n   ".join(problems))

    members["ft/BUNDLE_INFO.txt"] = bundle_info().encode("utf-8")
    manifest = "".join(f"{sha(members[a])}  {a}\n" for a in sorted(members)).encode("utf-8")
    members["ft/MANIFEST.sha256"] = manifest
    tar_path = out / "ft_t07.tar"
    now = int(time.time())
    with tarfile.open(tar_path, "w") as t:
        for arc in sorted(members):
            ti = tarfile.TarInfo(arc)
            ti.size, ti.mtime = len(members[arc]), now
            ti.mode = 0o755 if arc.endswith(".sh") else 0o644
            t.addfile(ti, io.BytesIO(members[arc]))
    tsha = sha(tar_path.read_bytes())
    with open(out / "ft_t07.tar.sha256", "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{tsha}  ft_t07.tar\n")
    n_prompt = sum(1 for a in members if "/tune_ai/" in a and a.endswith(".md"))
    print(f"✅ {len(members)} ไฟล์ ({n_prompt} prompt) · {tar_path.stat().st_size / 1e6:.1f} MB → {tar_path}")
    print(f"   sha256 {tsha}")
    print(f"   prompt t07 จาก {T07}" + ("   ⚠️ T07_DIR ถูก override (ลองบน PC เท่านั้น ห้ามใช้ขึ้นการ์ดจริง)"
                                     if "T07_DIR" in os.environ else ""))


if __name__ == "__main__":
    main()
