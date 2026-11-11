"""dryrun_bench_stub.py — ซ้อม bench ของด่าน 4 ฟรีบน PC ด้วย bundle ที่แตกแล้ว (โครงเดียวกับการ์ด) ไม่มี GPU ไม่มีเน็ต

⚠️ วัดแค่ "ท่อ" ไม่ได้วัดคุณภาพ: โมเดลปลอม (stub) ตอบ JSON แบบ t07 (ไม่มี png / doc_page / source_*) ตามชนิด prompt
แล้วรัน bench_house.py ตัวจริง (house + micro) จาก ft/wk/worker แบบเดียวกับ run_bench_t07.sh (PURSON_CV_MERGE=0)
จับได้: worker.py ที่ import ไม่ผ่าน / ต้องใช้ Supabase / prompt t07 ที่ worker โหลดไม่ได้ / GRID MASTER ที่ต่อท้ายไม่ตรงสูตร D4
ผลวัด 11 พ.ย. 69: house + micro exit 0 · คำขอ pass0 31 · gridline 1 · plan_footing 3 · plan_beam 3 · section 3 · ~3.5 นาที

    python -B dryrun_bench_stub.py <ft ที่แตกจาก ft_t07.tar> <โฟลเดอร์ออก>
    แล้ว: python -B analyze_houses.py <โฟลเดอร์ออก>/out t07     (ตัวเลขต่ำ = ปกติ โมเดลปลอม)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FT, OUT = (Path(a) for a in sys.argv[1:3])
PR = FT / "wk" / "training" / "tune_ai" / "t07_Palfrey"
IMG = FT / "bench" / "img83"


def common():          # same regexes as worker.load_common_block / load_prompt_file
    txt = (PR / "_common.md").read_text(encoding="utf-8")
    m = re.search(r"## BLOCK START\n(.*?)\n## BLOCK END", txt, re.DOTALL)
    body = m.group(1).strip() if m else txt.strip()
    g = re.search(r"<!-- GLOSSARY START -->\n(.*?)\n<!-- GLOSSARY END -->\n", body, re.DOTALL)
    return body.replace(g.group(0), "").strip() if g else body


def prompt_file(p):
    txt = p.read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)(?:\n## PROMPT END|\Z)", txt, re.DOTALL)
    return m.group(1).strip() if m else txt.strip()


PASS0 = prompt_file(PR / "pass0" / "prompt.md")
SUBS = {f.parent.name: common() + "\n\n" + prompt_file(f) for f in sorted((PR / "pass2").glob("*/prompt_*.md"))}
H2PAGE = {hashlib.sha256(p.read_bytes()).hexdigest(): int(p.stem.split("_")[1]) for p in IMG.glob("page_*.png")}
X = [{"id": "1", "pos_m": 0.0, "type": "main"}, {"id": "2", "pos_m": 4.0, "type": "main"}]
Y = [{"id": "A", "pos_m": 0.0, "type": "main"}, {"id": "B", "pos_m": 3.5, "type": "main"}]
SHEET = {"discipline": "structural", "sheet_code": "S-0X", "sheet_name": "stub"}
PLAN = {**SHEET, "floor_level": "F1", "building": "main", "view_title": "stub", "confidence_score": 0.8,
        "confidence_flags": [], "warnings": []}
ANSWER = {
    "gridline": {"pattern": "grid_master", "grid": {"x_lines": X, "y_lines": Y},
                 "confidence_score": 0.9, "confidence_flags": [], "warnings": []},
    "plan_beam": {**PLAN, "pattern": "beam_plan", "elements": [{"mark": "B1"}, {"mark": "B2"}, {"mark": "ZZ9"}]},
    "plan_footing": {**PLAN, "pattern": "footing_plan", "elements": [{"mark": "F1"}, {"mark": "F2"}]},
    "section": {**SHEET, "pattern": "section", "elements": [{"mark": "B1"}], "confidence_score": 0.8,
                "confidence_flags": [], "warnings": []},
}
VIEWS = {19: [{"subtask": "plan_footing", "where": "full", "also_gridline": True}],
         20: [{"subtask": "plan_beam", "where": "full", "also_gridline": True}],
         22: [{"subtask": "section", "where": "full"}]}
LOG = []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self.send({"data": [{"id": "purson"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        parts = body["messages"][0]["content"]
        text = next(p["text"] for p in parts if p["type"] == "text")
        imgs = [p["image_url"]["url"].split(",", 1)[1] for p in parts if p["type"] == "image_url"]
        import base64
        pages = [H2PAGE.get(hashlib.sha256(base64.b64decode(b)).hexdigest()) for b in imgs]
        if text == PASS0:
            kind = "pass0"
            doc = {**SHEET, "building": "main", "views": VIEWS.get(pages[0], []), "confidence_score": 0.9,
                   "warnings": []}
        else:
            kind = next((s for s, p in SUBS.items() if text.startswith(p)), "other")
            doc = ANSWER.get(kind, {"elements": [], "warnings": []})
        tail = text[len(SUBS[kind]):] if kind in SUBS else ""
        LOG.append({"kind": kind, "pages": pages, "n_images": len(imgs), "tail": tail,
                    "response_format": body.get("response_format"), "temperature": body.get("temperature")})
        raw = json.dumps(doc, ensure_ascii=False)
        self.send({"choices": [{"message": {"content": raw}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": len(text) // 3, "completion_tokens": len(raw) // 3}})


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}"
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "PURSON_QUIET": "1",
       "PURSON_CV_MERGE": "0", "TMP": str(OUT / "tmp"), "TEMP": str(OUT / "tmp")}
(OUT / "tmp").mkdir(parents=True, exist_ok=True)
base = [sys.executable, "-B", "bench_house.py"]
common_args = ["--job", str(FT / "bench" / "job_83b8e52c.json"), "--images", str(IMG), "--out", str(OUT / "out"),
               "--prompts", str(PR), "--gpu-url", url]
runs = [("t07_house_r1", ["house"]),
        ("t07_micro", ["micro", "--pages", "1,19", "--tasks", "22:section,20:plan_beam,19:plan_footing",
                       "--repeat", "2"])]
for label, mode in runs:
    r = subprocess.run(base + mode + common_args + ["--label", label], cwd=FT / "wk" / "worker", env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    (OUT / f"{label}.log").write_text(r.stdout + "\n--- stderr\n" + r.stderr, encoding="utf-8")
    print(f"{label}: exit {r.returncode} · log {OUT / (label + '.log')}")
srv.shutdown()

kinds = {}
for e in LOG:
    kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
print("stub requests by kind:", kinds)
gm = [e["tail"] for e in LOG if e["kind"].startswith("plan_") and "GRID MASTER" in e["tail"]]
want = "\n\nGRID MASTER (resolved axes for this building)\n" + json.dumps({"grid": {"x_lines": X, "y_lines": Y}},
                                                                         ensure_ascii=False)
print("plan_* requests with GRID MASTER tail:", len(gm), "| tail starts byte-identical to D4 builder:",
      all(t.startswith(want) for t in gm) if gm else None)
print("response_format / temperature seen:", {json.dumps(e["response_format"]) for e in LOG}, {e["temperature"] for e in LOG})
(OUT / "stub_log.json").write_text(json.dumps(LOG, ensure_ascii=False, indent=1), encoding="utf-8")
