#!/usr/bin/env python3
"""Self-check ของแผน A (worker.py รันบนการ์ดเช่า) — รัน: python test_worker_remote.py

ตรวจได้หมดโดยไม่ต้องเช่าการ์ด — ทุกข้อคือของที่ถ้าพลาด จะไปรู้ตัวบนการ์ดที่จ่ายเงินอยู่:

  1. ของที่ส่งขึ้นไปครบ: แตก bundle ลงโฟลเดอร์ชั่วคราวแล้ว **import worker.py จากในนั้นจริง**
     (worker โหลด prompt ตอน import + หา organize.py/cv_scan.py จาก path สัมพัทธ์ —
      ขาดไฟล์ไหน/วางผิดชั้นไหน พังตรงนี้ ไม่ใช่ไปพังกลางงานถอดแบบ)
  2. config ที่ส่งขึ้นไปชี้ GPU = localhost ของการ์ดเอง + prompt = path บนการ์ด
  3. pgrep ไม่เจอตัวเอง — กับดักเดียวกับ '[p]ip install' ที่วนรอ 17 นาทีเมื่อ 31 ส.ค.
  4. สั่งรันด้วย setsid --fork — กับดัก ssh ค้างจนโมเดลตาย 23 ก.ย.

⚠️ ไม่พิมพ์ค่าใน config ออกหน้าจอเด็ดขาด (มี Supabase service key) — เทียบแค่ชื่อคีย์
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import presentation as P  # noqa: E402

CFG_FILE = HERE / "worker_config.json"
if not CFG_FILE.exists():
    print("ข้าม — เครื่องนี้ไม่มี worker_config.json (ไฟล์มี secret ไม่ตามมากับ git)")
    sys.exit(0)
local_cfg = json.loads(CFG_FILE.read_text(encoding="utf-8"))

tmp = Path(tempfile.mkdtemp(prefix="wk_test_"))
try:
    tar_path = tmp / "wk.tar.gz"
    names = P.build_worker_bundle(tar_path, local_cfg)

    # ── 1. รายชื่อไฟล์ ────────────────────────────────────────────────────────
    with tarfile.open(tar_path) as t:
        members = {m.name: m for m in t.getmembers()}
        assert set(names) == set(members), "รายชื่อที่คืนมาไม่ตรงกับของที่อยู่ใน bundle จริง"
        for must in ("start_worker.sh", "worker/worker.py", "worker/pass3_measure.py",
                     "worker/vector_ruler.py", "worker/notify.py", "worker/worker_config.json",
                     "training/tune_ai/t04_Purson/_common.md",
                     "training/tune_ai/t04_Purson/pass0/prompt.md",
                     "training/tune_ai/t03/pass1_organize/organize.py",
                     "training/tools/cv_scan.py", "training/tools/pattern_recognition.py"):
            assert must in members, f"bundle ขาด {must}"
        assert any(n.startswith("training/tools/templates/tpl_") for n in members), \
            "bundle ไม่มีรูปแม่แบบ CV เลย — pass1.5 จะจับอะไรไม่ได้"
        assert not [n for n in members if "__pycache__" in n or ".bak" in n], \
            "bundle มีขยะ (__pycache__/.bak) ติดไปด้วย"
        size_mb = tar_path.stat().st_size / 1e6
        assert size_mb < 5, f"bundle ใหญ่ {size_mb:.1f} MB — ควรราว 1 MB (หยิบโฟลเดอร์ผิดมาหรือเปล่า)"

        # ── 2. config ─────────────────────────────────────────────────────────
        cfg_m = members["worker/worker_config.json"]
        assert cfg_m.mode & 0o077 == 0, "config บนการ์ดต้องอ่านได้เฉพาะเจ้าของ (มี service key)"
        rcfg = json.loads(t.extractfile(cfg_m).read().decode("utf-8"))
        assert rcfg["PURSON_GPU_URL"] == f"http://localhost:{P.LOCAL_PORT}", \
            "worker บนการ์ดต้องยิงตัวเสิร์ฟบนเครื่องเดียวกัน ไม่ใช่ URL ของคอมมะขาม"
        assert rcfg["PURSON_PROMPTS_DIR"] == P.REMOTE_PROMPTS, "prompt dir ต้องเป็น path บนการ์ด"
        assert set(rcfg) == set(local_cfg) | {"PURSON_GPU_URL", "PURSON_PROMPTS_DIR"}, \
            "คีย์ config หายระหว่างทาง (ค่าที่จูนไว้ เช่น PAGE_TIMEOUT_S ต้องตามไปด้วย)"
        t.extractall(tmp / "wk", filter="data")
    print(f"OK  bundle {len(names)} ไฟล์ {size_mb:.2f} MB · config ชี้ localhost + path บนการ์ด")

    # ── 1 (ต่อ). import worker จาก bundle จริง ────────────────────────────────
    wk = tmp / "wk"
    probe = (
        "import sys, worker as W\n"
        "assert W.ORGANIZE_PY.exists(), 'ไม่เจอ organize.py ตาม path ที่ worker คำนวณ'\n"
        "assert W.CV_SCAN_PY.exists(), 'ไม่เจอ cv_scan.py ตาม path ที่ worker คำนวณ'\n"
        "miss = [s for s in W.TRAINED_SUBTASKS if not W.subtask_prompt(s)]\n"
        "assert not miss, f'prompt ขาด: {miss}'\n"
        "sys.path.insert(0, str(W.CV_SCAN_PY.parent))\n"
        "import pattern_recognition as PR\n"
        "t = PR.load_templates()\n"
        "assert t['footing'] and t['column'], 'โหลดแม่แบบ CV ไม่ได้'\n"
        "print('probe-ok', len(W.TRAINED_SUBTASKS), len(t['footing']), len(t['column']))\n")
    env = {**os.environ,
           "PURSON_PROMPTS_DIR": str(wk / P.REMOTE_PROMPTS[len(P.REMOTE_WK) + 1:])}
    r = subprocess.run([sys.executable, "-c", probe], cwd=wk / "worker", env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120)
    assert r.returncode == 0 and "probe-ok" in r.stdout, \
        f"import worker จาก bundle ไม่ผ่าน:\n{r.stdout[-800:]}\n{r.stderr[-1500:]}"
    print(f"OK  import worker.py จาก bundle ได้จริง ({r.stdout.strip().splitlines()[-1]})")

    # ── 3. pgrep/pkill ต้องไม่เจอตัวเอง ───────────────────────────────────────
    pat = re.compile(P.WORKER_PATTERN)
    assert pat.search(f"{P.VENV_PY} -u worker.py"), "pattern ไม่เจอ worker ตัวจริง"
    for own in (P.worker_live_cmd(), P.worker_stop_cmd(), P.worker_deploy_cmd(),
                (wk / "start_worker.sh").read_text(encoding="utf-8").replace("\n", " ")):
        # บรรทัดคำสั่งของ bash ที่ ssh เปิดมามีข้อความนี้อยู่ ถ้า pattern จับได้ = เจอตัวเองตลอด
        # ยกเว้นเนื้อไฟล์ start_worker.sh — มันไม่อยู่บน command line (bash อ่านจากไฟล์)
        # แต่ถ้า pattern จับเนื้อไฟล์ได้ด้วย แปลว่าวันไหนเผลอส่งแบบ bash -c ก็จะพังทันที
        assert not pat.search(own), f"pattern เจอบรรทัดคำสั่งของตัวเอง: {own[:120]}"
    print("OK  pgrep/pkill ไม่เจอตัวเอง (ทั้งคำสั่งเช็ค/หยุด/สั่งเปิด และเนื้อสคริปต์)")

    # ── 4. สคริปต์เปิด worker ─────────────────────────────────────────────────
    script = (wk / "start_worker.sh").read_text(encoding="utf-8")
    assert "setsid --fork nohup" in script, "ขาด setsid --fork — ssh จะค้างจนกว่า worker จะตาย"
    assert f"PY={P.VENV_PY}" in script and "$W -u worker.py" in script, \
        "ต้องใช้ python ของ /venv/main แบบ -u (log ไม่ค้างบัฟเฟอร์)"
    assert f"PYTHONPATH={P.REMOTE_WDEPS}" in script, "dependency ของ worker ต้องแยกจาก /venv/main"
    assert "--target" in script, "ห้ามลง dependency ของ worker ทับ /venv/main ที่ตัวเสิร์ฟใช้อยู่"
    assert script.index("echo LIVE") < script.index("setsid"), "ต้องเช็คตัวเก่าก่อนเปิดตัวใหม่"
    bash = shutil.which("bash")
    if bash:
        r = subprocess.run([bash, "-n", str(wk / "start_worker.sh")], capture_output=True, text=True)
        assert r.returncode == 0, f"start_worker.sh syntax พัง: {r.stderr}"
        print("OK  start_worker.sh ผ่าน bash -n")
    print("OK  สคริปต์เปิด worker: setsid --fork · -u · deps แยก · เช็คซ้ำก่อนเปิด")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nok — แผน A ตรวจครบทุกข้อ (ยังไม่ได้ทดสอบบนการ์ดจริง)")
