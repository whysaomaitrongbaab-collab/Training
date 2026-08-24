#!/usr/bin/env python3
"""
ถอดแบบบ้าน 08/09/10 (= บ้าน_เล็ก_1ชั้น_03/04/05, เลขบ้านตามธรรมเนียม json_แก้ไขแล้ว/ทดลองถอดแบบ_08_09_10_11)
ด้วยโมเดลบนเครื่องเอง (llama-server, ไม่เช่า GPU) — สอง variant เทียบกัน:

  --model tuned   t01: Qwen3.6-35B-A3B ทูนแล้ว (merge GGUF Q4_K_M, tune_ai/t01/t01_workflow.md)
  --model base    Qwen3.6-35B-A3B untuned เพียวๆ (IQ2_XXS — ไฟล์ quant เดียวที่มีอยู่บนเครื่อง
                   จาก Phase 0.3 ของ t01_workflow.md ต่างระดับ quant จาก tuned แต่เป็น base
                   จริงไม่ทูน; mmproj ใช้ไฟล์เดียวกันได้ทั้งสอง variant เพราะ vision encoder
                   ไม่ถูกแตะระหว่างทูน)

Logic 2-phase (classify ทุกหน้า -> extract เต็มเฉพาะหน้าที่ pattern อยู่ใน KEEP_PATTERNS) และ
prompt สองอัน byte-identical กับ extract_house01_local.py — generalize ให้วนหลายบ้าน/สลับโมเดล
ได้ ไม่แตะไฟล์เดิม (house01 มี state resumable อยู่แล้วที่ ผล/)

รันได้ variant เดียวต่อครั้ง (GPU ตัวเดียว รันสองโมเดลพร้อมกันไม่ได้) resumable ทุก phase/บ้าน
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
IMAGES_ROOT = Path(r"D:\00mk\steel project\training\Training\image")
OUT_ROOT = ROOT / "ผล_08_09_10"
LLAMA_SERVER = r"D:\00mk\ai-models\qwen36-thai-rc\llama\llama-server.exe"
HOST, PORT = "127.0.0.1", "8090"
BASE_URL = f"http://{HOST}:{PORT}"

HOUSES = {
    "08": "บ้าน_เล็ก_1ชั้น_03",
    "09": "บ้าน_เล็ก_1ชั้น_04",
    "10": "บ้าน_เล็ก_1ชั้น_05",
}

MODELS = {
    "tuned": dict(
        model=r"D:\00mk\ai-models\qwen36-thai-rc\Qwen3.6-35B-A3B.Q4_K_M.gguf",
        mmproj=r"D:\00mk\ai-models\qwen36-thai-rc\mmproj-F16.gguf",
    ),
    "base": dict(
        model=r"D:\00mk\ai-models\qwen36-base-test\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf",
        mmproj=r"D:\00mk\ai-models\qwen36-thai-rc\mmproj-F16.gguf",
    ),
}

MAX_TOKENS_EXTRACT = 9000
MAX_TOKENS_CLASSIFY = 300
REQUEST_TIMEOUT_S = 3600
CLASSIFY_TIMEOUT_S = 600
RETRIES_PER_PAGE = 2

# Pass 2 (t03/pass_design.csv, README.md "Pass 2 (used in Constistant)") — 7 pattern ที่
# Constistant อ่านจริง ต่างจาก KEEP_PATTERNS เดิมของ extract_house01_local.py (ซึ่งมี
# roof_plan/side_profile แทน schedule/notes/material_list/soil_boring_log — รอบนี้ยึด t03 แทน)
KEEP_PATTERNS = {"gridline", "plan", "section", "schedule", "notes", "material_list", "soil_boring_log"}
ALL_PATTERNS = {
    "plan", "section", "schedule", "notes", "index", "material_list", "site_plan",
    "side_profile", "gridline", "title", "symbol", "roof_plan", "misc", "unknown",
    "soil_boring_log", "bbs_schedule",
}

CLASSIFY_PROMPT = (
    "You are looking at one page of a Thai reinforced-concrete construction drawing set.\n"
    "Identify every distinct view/box on this page. Reply with ONLY a JSON array of pattern\n"
    "strings, one entry per view (same order as they appear on the page), using exactly one\n"
    "of these values per entry: plan, section, schedule, notes, index, material_list,\n"
    "site_plan, side_profile, gridline, title, symbol, roof_plan, misc, soil_boring_log,\n"
    "bbs_schedule, unknown.\n"
    "Example: [\"plan\", \"schedule\"]\n"
    "No commentary, no markdown fence, JSON array only."
)

# byte-identical to PROMPT_SHORT in extract_house01_local.py / build_dataset.js
PROMPT_SHORT = "\n".join([
    "You are reading one page of a Thai reinforced-concrete (RC) construction drawing set.",
    "Extract everything on the page into JSON following the primary_rawjson_schema.",
    "",
    "Inventory EVERY view/box on the page first, then emit one entry per view in \"views\"",
    "(a single-view page still uses a one-entry array — never drop a view). Each view",
    "carries its own \"pattern\": plan, section, schedule, notes, index, material_list,",
    "site_plan, side_profile, gridline, title, symbol, roof_plan, misc, or unknown.",
    "",
    "GRID AND DUMMY GRID — the single most error-prone part of this task, read carefully:",
    "- grid_ref reads row-letter first, then column (\"A-1\", not \"1-A\"). Point-type elements",
    "  (footing/column) use a grid_refs array instead of start/end.",
    "- A structural line not on a named/printed grid still needs a name: append a prime to",
    "  the nearest named grid (\"1'\", \"A'\"). If more than one dummy line falls in the same",
    "  gap, number them in reading order (left→right / top→bottom): 1st gets one prime,",
    "  2nd gets two.",
    "- THE KEY RULE: if a beam's start or end point does not sit on any grid line you can",
    "  see, that point still needs a grid line — it does NOT mean the beam should be",
    "  dropped. Trace every beam segment, including short stubs near stairs/closets. For",
    "  each endpoint: use the existing named/dummy grid if one is there; if not, read its",
    "  position off a printed dimension chain and record a new dummy grid, then reference",
    "  the beam against it. Never: (a) drop the beam because it \"isn't on the grid\",",
    "  (b) write a prose description instead of grid_ref_start/grid_ref_end, (c) set",
    "  start=end with a null span. Exception: a slab/eave edge with no beam label and no",
    "  corner columns is not structural and needs no dummy grid.",
    "- Span length comes from the grid table, not your own visual estimate.",
    "",
    "REBAR (main_bar):",
    "- Always split top/bottom, even when the counts are equal — never collapse into one.",
    "- If a section shows a clearly distinct row of bars at mid-depth (own leader line,",
    "  sitting between the top and bottom rows, usually a deep beam), record it as a third",
    "  face, main_bar.middle. Do not fold it into additional_bars, and do not invent one by",
    "  splitting a top/bottom cluster.",
    "- A circle symbol (Ø) always means round bar (RB); visible ribs mean deformed bar (DB)",
    "  — read the symbol, never infer type from diameter.",
    "- Columns use a single main_bar.count for the 4 corner bars — do not split top/bottom.",
    "- Before assigning an \"additional\" bar to top or bottom, check the leader line itself,",
    "  not just the label wording — the same-looking label has resolved to opposite sides",
    "  on different marks in this series.",
    "",
    "OUTPUT DISCIPLINE:",
    "- Same element_id appearing more than once on this page with non-overlapping",
    "  positions → merge into one entry (sum count, concatenate grid_refs). Exception: a",
    "  multi-level schedule keeps the same element_id per level as separate entries, using",
    "  a \"level\" field — never embed the level into element_id.",
    "- One atomic entry per grid-to-grid beam segment; do not pre-group same-mark spans.",
    "- Reading order: top-to-bottom by row, left-to-right by column, vertical before",
    "  horizontal at a shared start point.",
    "- Use null for anything unclear. Do not guess or invent a value.",
    "",
    "Reply with JSON only. No markdown fence, no commentary.",
])


def log(log_file, msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def start_server(model_cfg, server_log_path):
    server_log = open(server_log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            LLAMA_SERVER,
            "--model", model_cfg["model"],
            "--mmproj", model_cfg["mmproj"],
            "--n-gpu-layers", "999",
            "--ctx-size", "16384",
            "--parallel", "1",
            "--ubatch-size", "2048",
            "--chat-template-kwargs", '{"enable_thinking":false}',
            "--temp", "0",
            "--host", HOST,
            "--port", PORT,
        ],
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    print(f"llama-server started, pid={proc.pid}, waiting for /health ...", flush=True)
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                print("llama-server ready.", flush=True)
                return proc
        except requests.exceptions.RequestException:
            pass
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited early with code {proc.returncode} — check {server_log_path}")
        time.sleep(5)
    raise RuntimeError("llama-server did not become healthy within 600s")


def strip_fence(text):
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    return m.group(1).strip() if m else t


def image_data_uri(img_path):
    b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def call_model(prompt_text, img_path, max_tokens, timeout_s):
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": image_data_uri(img_path)}},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    finish_reason = data["choices"][0].get("finish_reason")
    return content, finish_reason


def discover_pages(house_name):
    """หมายเลขหน้าจริงจากชื่อไฟล์ png (กัน gap ในลำดับ ไม่เดาว่าต่อเนื่อง 1..N)."""
    images_dir = IMAGES_ROOT / house_name
    pat = re.compile(rf"^{re.escape(house_name)}_หน้า(\d+)\.png$")
    pages = []
    for p in images_dir.glob(f"{house_name}_หน้า*.png"):
        m = pat.match(p.name)
        if m:
            pages.append(int(m.group(1)))
    return images_dir, sorted(pages)


def classify_page(page_num, house_name, images_dir, out_dir, classify_map, classify_file, log_file):
    page_str = f"{page_num:02d}"
    if page_str in classify_map:
        return "skip"

    img_path = images_dir / f"{house_name}_หน้า{page_str}.png"
    if not img_path.exists():
        log(log_file, f"[classify] หน้า{page_str}: image missing, skip")
        return "missing_image"

    last_err = None
    for attempt in range(1, RETRIES_PER_PAGE + 2):
        t0 = time.time()
        try:
            content, _ = call_model(CLASSIFY_PROMPT, img_path, MAX_TOKENS_CLASSIFY, CLASSIFY_TIMEOUT_S)
            elapsed = time.time() - t0
            try:
                pats = json.loads(strip_fence(content))
                if not isinstance(pats, list):
                    raise ValueError("not a list")
                pats = [p if p in ALL_PATTERNS else "unknown" for p in pats] or ["unknown"]
            except Exception as e:
                log(log_file, f"[classify] หน้า{page_str}: parse ไม่ผ่าน ({e}), raw={content[:200]!r} -> unknown")
                pats = ["unknown"]
            classify_map[page_str] = pats
            classify_file.write_text(json.dumps(classify_map, ensure_ascii=False, indent=2), encoding="utf-8")
            log(log_file, f"[classify] หน้า{page_str}: OK ({elapsed:.0f}s) -> {pats}")
            return "ok"
        except requests.exceptions.RequestException as e:
            last_err = e
            log(log_file, f"[classify] หน้า{page_str}: request error attempt {attempt}/{RETRIES_PER_PAGE + 1}: {e}")
            time.sleep(10)
    log(log_file, f"[classify] หน้า{page_str}: ❌ ล้มเหลวทุก attempt ({last_err}) — เว้นไว้ (จะลองใหม่รอบหน้า)")
    return "failed"


def extract_page(page_num, house_name, images_dir, out_dir, raw_dir, log_file):
    page_str = f"{page_num:02d}"
    img_path = images_dir / f"{house_name}_หน้า{page_str}.png"
    out_json = out_dir / f"{house_name}_หน้า{page_str}_ai.json"
    raw_txt = raw_dir / f"{house_name}_หน้า{page_str}.txt"

    if out_json.exists():
        log(log_file, f"[extract] หน้า{page_str}: already done, skip")
        return "skip"
    if not img_path.exists():
        log(log_file, f"[extract] หน้า{page_str}: image missing, skip")
        return "missing_image"

    last_err = None
    for attempt in range(1, RETRIES_PER_PAGE + 2):
        t0 = time.time()
        try:
            content, finish_reason = call_model(PROMPT_SHORT, img_path, MAX_TOKENS_EXTRACT, REQUEST_TIMEOUT_S)
            elapsed = time.time() - t0

            raw_dir.mkdir(exist_ok=True)
            raw_txt.write_text(content, encoding="utf-8")

            try:
                parsed = json.loads(strip_fence(content))
                out_json.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
                log(log_file, f"[extract] หน้า{page_str}: OK ({elapsed:.0f}s, finish={finish_reason}, attempt {attempt})")
                if finish_reason == "length":
                    log(log_file, f"[extract] หน้า{page_str}: ⚠️ ตัดกลาง (finish_reason=length) — ควรตรวจซ้ำด้วยตา")
                return "ok"
            except json.JSONDecodeError as e:
                log(log_file, f"[extract] หน้า{page_str}: ⚠️ parse JSON ไม่ผ่าน ({e}) — เก็บ raw ไว้ที่ {raw_txt.name}")
                return "parse_failed"
        except requests.exceptions.RequestException as e:
            last_err = e
            log(log_file, f"[extract] หน้า{page_str}: request error attempt {attempt}/{RETRIES_PER_PAGE + 1}: {e}")
            time.sleep(10)
    log(log_file, f"[extract] หน้า{page_str}: ❌ ล้มเหลวทุก attempt ({last_err})")
    return "failed"


def run_house(hnum, house_name, variant, limit, t0_all):
    out_dir = OUT_ROOT / variant / f"{hnum}{house_name}"
    raw_dir = out_dir / "_raw"
    log_file = out_dir / "extract_log.txt"
    classify_file = out_dir / "_classify.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(exist_ok=True)

    images_dir, pages = discover_pages(house_name)
    if limit:
        pages = pages[:limit]
    log(log_file, f"=== บ้าน {hnum}{house_name}: {len(pages)} หน้า (variant={variant}) ===")

    classify_map = json.loads(classify_file.read_text(encoding="utf-8")) if classify_file.exists() else {}
    log(log_file, "--- Phase A: classify ---")
    for page in pages:
        classify_page(page, house_name, images_dir, out_dir, classify_map, classify_file, log_file)

    keep_pages = [p for p in pages if set(classify_map.get(f"{p:02d}", [])) & KEEP_PATTERNS]
    skip_pages = [p for p in pages if p not in keep_pages]
    log(log_file, f"--- Phase A จบ: keep {len(keep_pages)} หน้า {keep_pages}")
    log(log_file, f"--- ข้าม {len(skip_pages)} หน้า: {skip_pages}")

    log(log_file, "--- Phase B: extract เต็มเฉพาะหน้าที่ keep ---")
    results = {}
    for page in keep_pages:
        results[page] = extract_page(page, house_name, images_dir, out_dir, raw_dir, log_file)

    counts = {}
    for v in results.values():
        counts[v] = counts.get(v, 0) + 1
    elapsed_all = time.time() - t0_all
    log(log_file, f"=== จบบ้าน {hnum}{house_name}: {counts} (เวลาสะสมรวมทุกบ้านถึงตอนนี้ {elapsed_all/60:.1f} นาที) ===")
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=list(MODELS.keys()), required=True)
    parser.add_argument("--houses", nargs="+", default=list(HOUSES.keys()), choices=list(HOUSES.keys()))
    parser.add_argument("--limit", type=int, default=None, help="จำกัดจำนวนหน้าต่อบ้าน (สำหรับ smoke test จับเวลา)")
    args = parser.parse_args()

    OUT_ROOT.mkdir(exist_ok=True)
    server_log_path = OUT_ROOT / f"llama_server_{args.model}_stdout.log"
    t0_all = time.time()
    proc = start_server(MODELS[args.model], server_log_path)
    try:
        summary = {}
        for hnum in args.houses:
            summary[hnum] = run_house(hnum, HOUSES[hnum], args.model, args.limit, t0_all)
    finally:
        print("กำลังปิด llama-server ...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("ปิด llama-server แล้ว", flush=True)

    print(f"=== จบรันทั้งหมด (variant={args.model}): {summary} ===")


if __name__ == "__main__":
    sys.exit(main())
