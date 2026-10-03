"""รวมทุกอย่างที่ต้องขึ้นการ์ดเป็น ft.tar (ไม่มี key/secret ใดๆ — worker_config.json ไม่ถูกใส่)"""
import json
import sys
import tarfile
from pathlib import Path

PW = Path(r"d:/00mk/steel project/งานสมบูรณ์/Constistant/server/purson-worker")
TUNE = Path(r"d:/00mk/steel project/training/Training/tune_ai")
SP = Path(__file__).resolve().parent.parent
CARD = SP / "card"
sys.path.insert(0, str(PW))
import presentation as P  # noqa: E402

cfg = {"PURSON_PROMPTS_DIR": json.load(open(PW / "worker_config.json", encoding="utf-8"))["PURSON_PROMPTS_DIR"]}
out = CARD / "ft.tar"
n = 0
with tarfile.open(out, "w") as t:
    for name in ("fix_destrier_layout.py", "merge_lora_to_base.py", "verify_merge.py"):
        t.add(TUNE / name, f"ft/tune/{name}"); n += 1
    for src, arc in P.worker_bundle_sources(cfg):
        t.add(src, f"ft/wk/{arc}"); n += 1
    for name in ("bench_house.py", "serve_purson.py"):
        t.add(PW / name, f"ft/wk/worker/{name}"); n += 1
    t.add(SP / "bench" / "job_83b8e52c.json", "ft/bench/job_83b8e52c.json"); n += 1
    for p in sorted((SP / "bench" / "img83").glob("*.png")):
        t.add(p, f"ft/bench/img83/{p.name}"); n += 1
    for name in ("phaseA.sh", "phaseB.sh", "install_engines.sh",
                 "launch_vllm.txt", "launch_sglang.txt", "launch_unsloth.txt"):
        t.add(CARD / name, f"ft/{name}"); n += 1
names = tarfile.open(out).getnames()
assert not any("worker_config" in x for x in names), "ห้ามมี config ที่มี key"
print(n, "ไฟล์", round(out.stat().st_size / 1e6, 1), "MB →", out)
