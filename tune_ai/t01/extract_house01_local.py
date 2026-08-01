#!/usr/bin/env python3
"""
เอา t01 (Qwen3.6-35B-A3B ทูนแล้ว, GGUF merge ในเครื่อง) มาถอดแบบบ้าน_เล็ก_1ชั้น_01
ผ่าน llama-server (โหลดโมเดลครั้งเดียว)

2 phase (เปลี่ยนตามคำสั่งมะขาม 2026-07-29 — extraction เต็มทุกหน้าช้าเกินไป ~18 นาที/หน้า):
  Phase A — classify: สแกนทุกหน้าด้วย prompt สั้น ถามแค่ pattern ของแต่ละ view บนหน้านั้น
            (เร็วกว่ามาก เพราะ output สั้น ไม่ต้องสกัดรายละเอียดเต็ม)
  Phase B — extract: รัน prompt เต็ม (PROMPT_SHORT) เฉพาะหน้าที่ classify แล้วมี pattern
            อยู่ใน KEEP_PATTERNS เท่านั้น หน้าอื่นข้าม

หมายเหตุ mapping: มะขามขอ "footing" มาด้วย แต่ schema ไม่มี pattern ชื่อนี้แยก — หน้า footing
plan/detail จะถูกจัดเป็น "plan" หรือ "section" อยู่แล้วตาม schema จริง ("grid master" = pattern
"gridline") ฉะนั้น KEEP_PATTERNS ครอบคลุม footing ผ่าน plan/section โดยอัตโนมัติ ไม่ต้องเพิ่มค่าเอง

รันต่อได้ (resumable) ทั้งสอง phase — ข้ามหน้าที่มีผลอยู่แล้ว (classify หรือ extract)
"""
import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
IMAGES_DIR = Path(r"D:\00mk\steel project\training\Training\image\บ้าน_เล็ก_1ชั้น_01")
OUT_DIR = ROOT / "ผล"
RAW_DIR = OUT_DIR / "_raw"
LOG_FILE = OUT_DIR / "extract_log.txt"
CLASSIFY_FILE = OUT_DIR / "_classify.json"

LLAMA_SERVER = r"D:\00mk\ai-models\qwen36-thai-rc\llama\llama-server.exe"
MODEL = r"D:\00mk\ai-models\qwen36-thai-rc\Qwen3.6-35B-A3B.Q4_K_M.gguf"
MMPROJ = r"D:\00mk\ai-models\qwen36-thai-rc\mmproj-F16.gguf"
HOST, PORT = "127.0.0.1", "8090"
BASE_URL = f"http://{HOST}:{PORT}"

PAGE_COUNT = 61
MAX_TOKENS_EXTRACT = 9000
MAX_TOKENS_CLASSIFY = 300
REQUEST_TIMEOUT_S = 3600  # worst case ~47min generation + prompt time, see extract_log history 2026-07-29
CLASSIFY_TIMEOUT_S = 600  # short output, dominated by prompt/image processing (~3-4min), generous margin
RETRIES_PER_PAGE = 2

KEEP_PATTERNS = {"plan", "section", "roof_plan", "side_profile", "gridline"}
ALL_PATTERNS = {
    "plan", "section", "schedule", "notes", "index", "material_list", "site_plan",
    "side_profile", "gridline", "title", "symbol", "roof_plan", "misc", "unknown",
}

CLASSIFY_PROMPT = (
    "You are looking at one page of a Thai reinforced-concrete construction drawing set.\n"
    "Identify every distinct view/box on this page. Reply with ONLY a JSON array of pattern\n"
    "strings, one entry per view (same order as they appear on the page), using exactly one\n"
    "of these values per entry: plan, section, schedule, notes, index, material_list,\n"
    "site_plan, side_profile, gridline, title, symbol, roof_plan, misc, unknown.\n"
    "Example: [\"plan\", \"schedule\"]\n"
    "No commentary, no markdown fence, JSON array only."
)

# byte-identical to PROMPT_SHORT in tune_ai/t01/data_before_tune/build_dataset.js
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


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def start_server():
    OUT_DIR.mkdir(exist_ok=True)
    server_log = open(OUT_DIR / "llama_server_stdout.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            LLAMA_SERVER,
            "--model", MODEL,
            "--mmproj", MMPROJ,
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
    log(f"llama-server started, pid={proc.pid}, waiting for /health ...")
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                log("llama-server ready.")
                return proc
        except requests.exceptions.RequestException:
            pass
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited early with code {proc.returncode} — check llama_server_stdout.log")
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


def load_classify():
    if CLASSIFY_FILE.exists():
        return json.loads(CLASSIFY_FILE.read_text(encoding="utf-8"))
    return {}


def save_classify(d):
    CLASSIFY_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def patterns_from_existing_extract(page_str):
    """หน้าที่มี _ai.json อยู่แล้ว (extract เต็มไปแล้วก่อนเปลี่ยนแผน) — อ่าน pattern จากในนั้นเลย ไม่ต้องเรียกโมเดลซ้ำ"""
    out_json = OUT_DIR / f"บ้าน_เล็ก_1ชั้น_01_หน้า{page_str}_ai.json"
    if not out_json.exists():
        return None
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
        views = data.get("views", [])
        pats = [v.get("pattern") for v in views if v.get("pattern")]
        return pats or ["unknown"]
    except Exception:
        return ["unknown"]


def classify_page(page_num, classify_map):
    page_str = f"{page_num:02d}"
    if page_str in classify_map:
        return "skip"

    existing = patterns_from_existing_extract(page_str)
    if existing is not None:
        classify_map[page_str] = existing
        save_classify(classify_map)
        log(f"[classify] หน้า{page_str}: ดึงจาก _ai.json เดิม -> {existing}")
        return "from_existing"

    img_path = IMAGES_DIR / f"บ้าน_เล็ก_1ชั้น_01_หน้า{page_str}.png"
    if not img_path.exists():
        log(f"[classify] หน้า{page_str}: image missing, skip")
        return "missing_image"

    last_err = None
    for attempt in range(1, RETRIES_PER_PAGE + 2):
        t0 = time.time()
        try:
            content, finish_reason = call_model(CLASSIFY_PROMPT, img_path, MAX_TOKENS_CLASSIFY, CLASSIFY_TIMEOUT_S)
            elapsed = time.time() - t0
            try:
                pats = json.loads(strip_fence(content))
                if not isinstance(pats, list):
                    raise ValueError("not a list")
                pats = [p if p in ALL_PATTERNS else "unknown" for p in pats] or ["unknown"]
            except Exception as e:
                log(f"[classify] หน้า{page_str}: parse ไม่ผ่าน ({e}), raw={content[:200]!r} -> ตั้งเป็น unknown ไว้ก่อน (จะไม่ถูก extract)")
                pats = ["unknown"]
            classify_map[page_str] = pats
            save_classify(classify_map)
            log(f"[classify] หน้า{page_str}: OK ({elapsed:.0f}s) -> {pats}")
            return "ok"
        except requests.exceptions.RequestException as e:
            last_err = e
            log(f"[classify] หน้า{page_str}: request error attempt {attempt}/{RETRIES_PER_PAGE + 1}: {e}")
            time.sleep(10)
    log(f"[classify] หน้า{page_str}: ❌ ล้มเหลวทุก attempt ({last_err}) — เว้นไว้ ไม่ classify (จะลองใหม่รอบหน้า)")
    return "failed"


def extract_page(page_num):
    page_str = f"{page_num:02d}"
    img_path = IMAGES_DIR / f"บ้าน_เล็ก_1ชั้น_01_หน้า{page_str}.png"
    out_json = OUT_DIR / f"บ้าน_เล็ก_1ชั้น_01_หน้า{page_str}_ai.json"
    raw_txt = RAW_DIR / f"บ้าน_เล็ก_1ชั้น_01_หน้า{page_str}.txt"

    if out_json.exists():
        log(f"[extract] หน้า{page_str}: already done, skip")
        return "skip"
    if not img_path.exists():
        log(f"[extract] หน้า{page_str}: image missing, skip")
        return "missing_image"

    last_err = None
    for attempt in range(1, RETRIES_PER_PAGE + 2):
        t0 = time.time()
        try:
            content, finish_reason = call_model(PROMPT_SHORT, img_path, MAX_TOKENS_EXTRACT, REQUEST_TIMEOUT_S)
            elapsed = time.time() - t0

            RAW_DIR.mkdir(exist_ok=True)
            raw_txt.write_text(content, encoding="utf-8")

            try:
                parsed = json.loads(strip_fence(content))
                out_json.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
                log(f"[extract] หน้า{page_str}: OK ({elapsed:.0f}s, finish={finish_reason}, attempt {attempt})")
                if finish_reason == "length":
                    log(f"[extract] หน้า{page_str}: ⚠️ ตัดกลาง (finish_reason=length) — ควรตรวจซ้ำด้วยตา")
                return "ok"
            except json.JSONDecodeError as e:
                log(f"[extract] หน้า{page_str}: ⚠️ parse JSON ไม่ผ่าน ({e}) — เก็บ raw ไว้ที่ {raw_txt.name}")
                return "parse_failed"
        except requests.exceptions.RequestException as e:
            last_err = e
            log(f"[extract] หน้า{page_str}: request error attempt {attempt}/{RETRIES_PER_PAGE + 1}: {e}")
            time.sleep(10)
    log(f"[extract] หน้า{page_str}: ❌ ล้มเหลวทุก attempt ({last_err})")
    return "failed"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    log("=== เริ่มรัน extract_house01_local.py (2-phase: classify -> extract เฉพาะ pattern ที่ต้องการ) ===")
    proc = start_server()
    try:
        log(f"--- Phase A: classify ทุกหน้า (เก็บที่ {CLASSIFY_FILE.name}) ---")
        classify_map = load_classify()
        for page in range(1, PAGE_COUNT + 1):
            classify_page(page, classify_map)

        keep_pages = [
            p for p in range(1, PAGE_COUNT + 1)
            if set(classify_map.get(f"{p:02d}", [])) & KEEP_PATTERNS
        ]
        skip_pages = [p for p in range(1, PAGE_COUNT + 1) if p not in keep_pages]
        log(f"--- Phase A จบ: keep {len(keep_pages)} หน้า {keep_pages}")
        log(f"--- ข้าม {len(skip_pages)} หน้า (ไม่ตรง pattern ที่ต้องการ): {skip_pages}")

        log(f"--- Phase B: extract เต็มเฉพาะหน้าที่ keep ---")
        results = {}
        for page in keep_pages:
            results[page] = extract_page(page)
    finally:
        log("กำลังปิด llama-server ...")
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        log("ปิด llama-server แล้ว")

    counts = {}
    for v in results.values():
        counts[v] = counts.get(v, 0) + 1
    log(f"=== จบรัน: {counts} ===")


if __name__ == "__main__":
    sys.exit(main())
