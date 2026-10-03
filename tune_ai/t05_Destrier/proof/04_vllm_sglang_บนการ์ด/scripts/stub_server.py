"""stub OpenAI server สำหรับซ้อม bench_house.py ในเครื่อง (ไม่มีโมเดลจริง)
ตอบด้วยผลของ production job 83b8e52c ตามหน้าที่ภาพตรงกัน (hash) — ครอป/หน้าที่ไม่รู้จักตอบ elements ว่าง"""
import base64, hashlib, json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"d:/00mk/steel project/งานสมบูรณ์/Constistant/server/purson-worker")
os.environ.update(SUPABASE_URL="http://offline.invalid", SUPABASE_SERVICE_KEY="x", PURSON_GPU_URL="x",
                  PURSON_PROMPTS_DIR=r"d:/00mk/steel project/training/Training/tune_ai/t04_Purson")
import worker as W  # noqa
job = json.load(open(f"{S}/job_83b8e52c.json", encoding="utf-8"))
files = {f["name"]: f["json"] for f in job["result"]["files"]}
pass0 = {d["_page"]: d for d in files["pass0.json"]["pages"]}
h2page = {}
for p in job["payload"]["pages"]:
    b = open(f"{S}/img83/{os.path.basename(p['path'])}", "rb").read()
    h2page[hashlib.sha256(b).hexdigest()] = p["page"]
subs = [s for s in W.TRAINED_SUBTASKS if W.subtask_prompt(s)]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send({"data": [{"id": "purson"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        content = body["messages"][-1]["content"]
        imgs = [base64.b64decode(c["image_url"]["url"].split(",", 1)[1]) for c in content if c["type"] == "image_url"]
        text = "".join(c["text"] for c in content if c["type"] == "text")
        if body.get("logprobs"):
            tl = [{"token": t, "logprob": lp} for t, lp in (("{", -0.1), ("```", -2.5), ("[", -4.0), (" {", -5.0), ("\n", -6.0))]
            return self._send({"choices": [{"message": {"content": "{"}, "logprobs": {"content": [{"token": "{", "logprob": -0.1, "top_logprobs": tl}]}}]})
        pages = [h2page.get(hashlib.sha256(b).hexdigest()) for b in imgs]
        if text == W.PASS0_PROMPT:
            doc = {k: v for k, v in pass0.get(pages[0], {"views": []}).items() if k != "_page"}
        elif text.startswith(W.subtask_prompt("gridline")):
            doc = files.get("grid_master.json", {})
        else:
            sub = next((s for s in subs if text.startswith(W.subtask_prompt(s))), None)
            doc = files.get(f"page_{pages[0]:02d}_{sub}.json") if pages[0] else None
            doc = doc or {"elements": [], "warnings": ["stub: ครอป/ไม่รู้จัก"]}
        time.sleep(0.05)
        txt = json.dumps(doc, ensure_ascii=False)
        self._send({"choices": [{"message": {"content": txt}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 7000 * len(imgs) + 900, "completion_tokens": max(1, len(txt) // 3)}})


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8099), H).serve_forever()
