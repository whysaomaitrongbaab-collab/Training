#!/usr/bin/env python3
"""Purson pipeline worker — claims jobs from Supabase, runs the multi-pass drawing
extraction against a Purson GPU endpoint, writes raw-JSON results back.

    Web (Constistant) --> Supabase (purson_jobs + storage) --> THIS WORKER --> GPU endpoint
                                                                (vLLM, OpenAI-compatible)

Runs identically on Makham's PC (mode B — GPU is a rented vast.ai box, IP changes
per rental, edit config only here) or on a rented server next to the model
(mode A — PURSON_GPU_URL=http://localhost:8000). See README.md.

Pipeline per house_extract job (pass numbering = tune_ai/t04_Purson/pass_io_table.csv):
  pass0   classify every page          -> AI call per page
  pass1   organize/slice views         -> local CPU subprocess (tune_ai/t03/pass1_organize/
                                          organize.py) — crops multi-view pages so token density
                                          matches training; falls back to full page on any failure
  pass1.5 CV template-match + hint      -> local CPU subprocess (tools/cv_scan.py --manifest);
                                          hint text appended to plan_footing/plan_beam/plan_slab
                                          prompts (arm 2.4a per pass2.4_hint/prompt.md — first
                                          live run of this arm, 2026-09-01, previously untested)
  pass2   extract per page x subtask   -> AI call each; gridline first, its grid.x_lines/
                                         y_lines then embedded into every plan_* prompt
                                         exactly as build_dataset_t03.py did at train time
  pass2.5 CV self-harvest sidecar       -> local CPU subprocess (tools/cv_scan.py --pass25);
                                          จุดที่คลังกลาง template ข้ามซีรีส์จับไม่ติด
  pass3   วัดระยะจริงจากพิกเซล            -> pass3_measure.py (pure, stdlib): หมุด = element ที่มี
                                          ทั้ง grid_ref (โมเดลอ่านได้) และพิกัด CV → fit px ต่อเมตร
                                          → เติม cv_measure (ตำแหน่งเมตร) ทุก element, snap grid
                                          ref ให้ตัวที่โมเดลไม่ได้ตอบ, รายงานจุดที่ CV เห็นแต่โมเดล
                                          ไม่พูดถึง · ต้องรันหลัง pass2.5 เพราะกินจุด self-harvest
  result: raw-JSON file set, same shape qt_importRawExtractionFiles() already accepts,
          บวก sidecar (cv15_*/cv25_*/pass3_measure.json) ที่ฝั่งเว็บกรองออกจากหน้าติ๊กเลือก
          แล้วสรุปเป็นบรรทัดเดียวแทน (drawing-purson.js: isSidecar/renderPass3Summary)

pass1/1.5/2.5 run on THIS machine's CPU (opencv+numpy, not GPU) — never touches the rented
GPU box. Any failure in that chain (organize.py exits non-zero, cv_scan.py times out, a crop
doesn't match 1:1 to a task) silently falls back to sending the full downloaded page with no
hint, exactly like before this was wired in — "ไม่เดา" applies to the fallback too, never to
whether pass2 still runs.

Prompt assembly replicates build_dataset_t03.py byte-for-byte (COMMON block from
_common.md minus glossary + pass2/<subtask>/prompt_<subtask>.md PROMPT block +
optional GRID MASTER tail) — the model must see prompts identical to training.

Deps: pip install requests    (nothing else)
Config: env vars or worker_config.json next to this file (env wins).
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pass3_measure import measure_page, merge_into_pass2  # noqa: E402  (pure, stdlib)


def load_config():
    cfg = {}
    f = HERE / "worker_config.json"
    if f.exists():
        cfg = json.loads(f.read_text(encoding="utf-8"))
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "PURSON_GPU_URL", "PURSON_GPU_KEY",
              "PURSON_MODEL", "PURSON_PROMPTS_DIR"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "PURSON_GPU_URL",
                           "PURSON_PROMPTS_DIR") if not cfg.get(k)]
    if missing:
        sys.exit(f"config ขาด: {', '.join(missing)} (ตั้ง env หรือใส่ใน worker_config.json)")
    cfg.setdefault("PURSON_MODEL", "purson")
    cfg.setdefault("POLL_INTERVAL_S", 3)
    cfg.setdefault("PAGE_TIMEOUT_S", 25 * 60)   # กติกาเดิมของ t03: เกิน 25 นาที/หน้า ตัดจบ
    cfg.setdefault("MAX_NEW_TOKENS", 6000)
    cfg.setdefault("STALE_PROCESSING_MIN", 45)
    return cfg


CFG = load_config()
PROMPTS_DIR = Path(CFG["PURSON_PROMPTS_DIR"])  # points at tune_ai/t04_Purson
REST = f"{CFG['SUPABASE_URL']}/rest/v1"
STORAGE = f"{CFG['SUPABASE_URL']}/storage/v1"
SB_HEADERS = {
    "apikey": CFG["SUPABASE_SERVICE_KEY"],
    "Authorization": f"Bearer {CFG['SUPABASE_SERVICE_KEY']}",
    "Content-Type": "application/json",
}

# 7 subtask ที่โมเดล **ถูกเทรนมาจริง** — ตรงกับ PROMPTS ใน build_dataset_t03.py เป๊ะ
#
# ⚠️ ต้องเป็น allowlist ห้ามเป็น blocklist (แก้ 2026-08-31 หลังอ่าน t04 pass_io_table_detailed.csv):
# โฟลเดอร์ pass2/ มี prompt ของ subtask ที่ **มี 0 ตัวอย่างตอนเทรน** ปนอยู่ด้วย —
#   plan_column      "ตัน" ไม่มีบ้านไหนมีแผ่นเดี่ยว (เสาอยู่บนแผ่นฐานราก/คานแทน)
#   material_list    prompt มี แต่ build_dataset ไม่โหลดเข้าชุดเทรน
#   soil_boring_log  ไม่มีไฟล์ GT เลยสักหลัง
# subtask_prompt() โหลดไฟล์พวกนี้ได้ตามปกติ ถ้าใช้ blocklist แล้วลืมใส่ = worker ยิง prompt
# ที่โมเดลไม่เคยเห็น แล้วได้ขยะกลับมาโดยไม่มีอะไรเตือน · allowlist ทำให้ "ลืม" แล้วปลอดภัย
TRAINED_SUBTASKS = ("gridline", "plan_footing", "plan_beam", "plan_slab",
                    "section", "schedule", "notes")

# ชื่อไทยไว้โชว์ในหน้าเว็บระหว่างทำงาน — ไม่ใช้ตัดสินใจอะไร แค่ให้ผู้ใช้อ่านออก
SUBTASK_TH = {
    "gridline": "ผังกริด", "plan_footing": "แปลนฐานราก", "plan_beam": "แปลนคาน",
    "plan_slab": "แปลนพื้น", "section": "รูปตัด/แบบขยาย", "schedule": "ตารางเหล็ก",
    "notes": "หมายเหตุ/รายการประกอบแบบ",
}

# 3 subtask ที่ organize.py/cv_scan.py จับ **และ** โมเดลถูกเทรนมาจริง (plan_column ตัดออก —
# cv_scan.py's PLAN_SUBTASKS มี 4 ตัว แต่ plan_column ไม่มีตัวอย่างตอนเทรนเลย ไม่มีวันเป็น task)
PLAN_SUBTASKS = ("plan_footing", "plan_beam", "plan_slab")

# subtask → ชื่อ pattern ที่ raw-extraction-adapter.js รู้จัก (PATTERN_ALIASES ในไฟล์นั้น)
#
# ⚠️ ไฟล์ผลลัพธ์ **ต้องมีฟิลด์ pattern เสมอ** ไม่งั้น adapter อ่านไม่ออกแล้วทิ้งเงียบ ๆ
# เจอจริงจากการจำลองบ้านครอบครัวไทยเป็นสุข2 (2026-09-01): grid_master.json ที่ worker เขียน
# มีแค่ {grid, warnings} ไม่มี pattern → adapter หากริดไม่เจอ → คานทุกตัวได้
# span_source 'unresolved' → **ไม่มีปริมาณคานใน BOQ ทั้งหลัง** โดยไม่มี error สักตัว
# (ไฟล์ GT ของทีมเทรนมี pattern: "grid_master" อยู่แล้ว ฝั่ง worker ต่างหากที่ลืมใส่)
# ประทับจากฝั่งเราเอง ไม่พึ่งว่าโมเดลจะตอบ pattern มาให้ — เรารู้อยู่แล้วว่าสั่งงานอะไรไป
SUBTASK_PATTERN = {
    "gridline": "grid_master", "plan_footing": "footing_plan", "plan_beam": "beam_plan",
    "plan_slab": "etc_plan", "section": "section", "schedule": "schedule", "notes": "notes",
}

# pass1/1.5/2.5 อยู่ที่ Training repo คนละที่กับ t04_Purson (PROMPTS_DIR):
#   PROMPTS_DIR = Training/tune_ai/t04_Purson
ORGANIZE_PY = PROMPTS_DIR.parent / "t03" / "pass1_organize" / "organize.py"
CV_SCAN_PY = PROMPTS_DIR.parent.parent / "tools" / "cv_scan.py"


# ── prompt assembly (ต้องตรงกับ build_dataset_t03.py เป๊ะ — โมเดลเทรนด้วย prompt ชุดนี้) ──
def load_common_block():
    txt = (PROMPTS_DIR / "_common.md").read_text(encoding="utf-8")
    m = re.search(r"## BLOCK START\n(.*?)\n## BLOCK END", txt, re.DOTALL)
    body = m.group(1).strip() if m else txt.strip()
    g = re.search(r"<!-- GLOSSARY START -->\n(.*?)\n<!-- GLOSSARY END -->\n", body, re.DOTALL)
    return body.replace(g.group(0), "").strip() if g else body


def load_prompt_file(path):
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)(?:\n## PROMPT END|\Z)", txt, re.DOTALL)
    return m.group(1).strip() if m else txt.strip()


COMMON = load_common_block()
PASS0_PROMPT = load_prompt_file(PROMPTS_DIR / "pass0" / "prompt.md")


def subtask_prompt(subtask):
    """คืน prompt เต็มของ subtask หรือ None ถ้าไม่มีไฟล์ prompt (= ยังไม่รองรับ)
    data-driven: เพิ่มโฟลเดอร์ prompt ใหม่ใน pass2/ แล้ว worker รองรับเองทันที"""
    f = PROMPTS_DIR / "pass2" / subtask / f"prompt_{subtask}.md"
    if not f.exists():
        return None
    return COMMON + "\n\n" + load_prompt_file(f)


# ── JSON cleanup — port ตรงจาก infer_house_t03.py strip_fence() (defense in depth) ──
def strip_fence(text):
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    t = m.group(1).strip() if m else t
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    t = re.sub(r"(\d)\.(?=[,}\]\s])", r"\1.0", t)  # บั๊กจริงบ้าน 08: "0." ไม่ใช่ JSON number
    return t


# ── element sanitize — ดักค่าขยะที่ผ่าน JSON parse ได้แต่เนื้อหาเพี้ยน (บ้านไทยพอเพียง3
# op04 2026-08-31: ตัวเลขติดลบ height_mm/spacing_mm, คีย์เพี้ยน "height_mm:-500,": ":null,")
# กรองที่ระดับ element เท่านั้น — ไม่ซ่อม ไม่เดา แค่ทิ้งของเสียก่อนถึงมือผู้ใช้ ————————
# ⚠️ ต้องเป็น allowlist ของ "ขนาด" เท่านั้น ห้ามเหมาทุกคีย์ที่ลงท้าย _mm/_m/_cm
# (แก้ 2026-09-01) ของเดิมเหมาหมด → คานคอดินที่พิมพ์ "GB1(-0.50)" มี level_m: -0.5 ซึ่ง
# **ถูกต้องตามสเปก** (ระดับใต้ datum ติดลบได้ · pos_m ก่อน origin ก็ติดลบได้) โดนตัดทิ้ง
# ทั้ง element เงียบๆ แล้วโทษโมเดลผิดใน warning · พบจริงใน GT: 07บ้าน_ใหญ่_2ชั้น_01
# หน้า35 footing_plan ทิ้ง GB1/GB1/GB1X 3 ตัวจาก 11 · precast level_step_mm: -100 อีก 4 ตัว
# ขนาดหน้าตัดต่างหากที่ติดลบไม่ได้จริง — จำกัดเงื่อนไขไว้แค่นั้น
_NEG_DIM_KEYS = re.compile(r"(width|height|thickness|depth|dia|spacing|length|cover)_(mm|m|cm)$")
_GARBAGE_KEY = re.compile(r"[:,]")  # คีย์จริงไม่มี : หรือ , ปน — ถ้ามีคือ generation หลุด


def _element_is_garbage(el):
    if not isinstance(el, dict):
        return True
    for k, v in el.items():
        if _GARBAGE_KEY.search(k):
            return True
        if _NEG_DIM_KEYS.search(k) and isinstance(v, (int, float)) and v < 0:
            return True
        if isinstance(v, dict) and _element_is_garbage(v):  # ตรวจ nested เช่น stirrup/main_bar
            return True
    return False


def sanitize_elements(doc):
    """ทิ้ง element ที่เป็นขยะ (ดู _element_is_garbage) คืน doc เดิมถ้าไม่มี elements[]
    บันทึกจำนวนที่ทิ้งใน doc['warnings'] เสมอเมื่อทิ้งจริง — ไม่เงียบ"""
    els = doc.get("elements")
    if not isinstance(els, list):
        return doc
    kept = [e for e in els if not _element_is_garbage(e)]
    dropped = len(els) - len(kept)
    if dropped:
        doc["elements"] = kept
        doc.setdefault("warnings", []).append(
            f"sanitize_elements: ทิ้ง {dropped}/{len(els)} element (ตัวเลขติดลบ/คีย์เพี้ยน — "
            f"generation หลุดกลางคัน) ไม่เดาค่าแทน")
    return doc


# ── ทนเน็ตสะดุด ───────────────────────────────────────────────────────────────
# งานจริงยาว 75-80 นาที และคุย Supabase ~40 ครั้งระหว่างทาง (set_progress ทุกหน้า)
# ถ้าเน็ตกระตุก 1 ครั้งแล้วทิ้งงานทั้งใบ = จ่ายค่า GPU ไปเปล่า ๆ 40 นาที
NET_TRIES = 5
NET_BACKOFF_S = (5, 15, 30, 60, 60)


def _retry(fn, what, tries=NET_TRIES):
    """ยิงซ้ำแบบถอยหลังเมื่อเน็ตสะดุด — ใช้กับ call ที่ยิงซ้ำแล้วผลเหมือนเดิม (GET/PATCH) เท่านั้น"""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            if i == tries - 1:
                break
            wait = NET_BACKOFF_S[min(i, len(NET_BACKOFF_S) - 1)]
            print(f"  ⚠️ {what} ไม่สำเร็จ ({type(e).__name__}) — รอ {wait}s ลองใหม่ "
                  f"({i + 1}/{tries})", flush=True)
            time.sleep(wait)
    raise last


# ── Supabase helpers ──────────────────────────────────────────────────────────
def claim_next_job():
    r = requests.get(
        f"{REST}/purson_jobs",
        headers=SB_HEADERS,
        params={"status": "eq.pending", "order": "created_at.asc", "limit": 1,
                "select": "id,job_type,payload,attempts"},
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    job = rows[0]
    # conditional update = atomic claim: แถวหลุดมือ (worker อื่นคว้าไปก่อน) ได้ 0 rows กลับ
    r = requests.patch(
        f"{REST}/purson_jobs",
        headers={**SB_HEADERS, "Prefer": "return=representation"},
        params={"id": f"eq.{job['id']}", "status": "eq.pending"},
        json={"status": "processing", "claimed_at": now_iso(),
              "attempts": job["attempts"] + 1},
        timeout=30,
    )
    r.raise_for_status()
    return job if r.json() else None


# เวลาที่งานปัจจุบันเริ่ม — set_progress ใช้คำนวณ elapsed_s ให้ UI ทำ ETA ต่อได้
# (module-level เพราะ worker ทำทีละงานอยู่แล้ว — claim_next_job คว้าทีละใบ)
JOB_T0 = None


def update_job(job_id, patch):
    def once():
        r = requests.patch(f"{REST}/purson_jobs", headers=SB_HEADERS,
                           params={"id": f"eq.{job_id}"}, json=patch, timeout=60)
        r.raise_for_status()
    _retry(once, f"เขียนสถานะงาน {job_id}")


def set_progress(job_id, step, done, total, note="", **extra):
    """เขียน progress jsonb ทับทั้งก้อนทุกครั้ง (ไม่ merge)

    4 คีย์แรกเป็นสัญญาเดิมที่ UI รุ่นก่อนอ่าน — ห้ามเปลี่ยนชื่อ/ความหมาย
    `extra` คือคีย์เสริมที่ UI ใหม่ใช้ทำ ETA/นับผลลัพธ์ ถ้าฝั่ง UI ไม่รู้จักก็แค่ไม่ใช้
    (worker กับหน้าเว็บอัปคนละรอบได้ — เลยต้อง degrade ได้ทั้งสองทาง)"""
    p = {"step": step, "done": done, "total": total, "note": note}
    p.update({k: v for k, v in extra.items() if v is not None})
    if JOB_T0 is not None:
        p["elapsed_s"] = round(time.time() - JOB_T0, 1)
    update_job(job_id, {"progress": p})
    print(f"  [{step}] {done}/{total} {note}", flush=True)


def requeue_stale():
    cutoff = time.time() - CFG["STALE_PROCESSING_MIN"] * 60
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(cutoff))
    r = requests.patch(
        f"{REST}/purson_jobs",
        headers={**SB_HEADERS, "Prefer": "return=representation"},
        # ⚠️ ต้องดู updated_at ไม่ใช่ claimed_at (แก้ 2026-09-01)
        # claimed_at เขียนครั้งเดียวตอนคว้างาน ไม่เคยต่ออายุ — งานจริงยาว 75-80 นาที
        # (38 หน้า × 32 วิ + gridline + pass2) แต่ STALE_PROCESSING_MIN = 45 แปลว่า
        # **งานจริงทุกใบเข้าเงื่อนไข stale** ระหว่างที่ยังทำอยู่ ถ้ามี worker ตัวที่ 2 เปิดขึ้นมา
        # (กด GO.bat ซ้ำ / เปิดหน้าต่างใหม่เพราะคิดว่าค้าง) มันจะดีดงานที่กำลังวิ่งกลับเป็น
        # pending แล้วคว้าไปทำซ้ำ = จ่ายค่า GPU สองเท่า + ผลเขียนทับกันตอนจบ
        # updated_at ถูก trigger purson_jobs_touch_updated_at อัปเดตทุกครั้งที่ set_progress
        # เขียน progress ลงไป → งานที่ยังรายงานความคืบหน้าอยู่จะไม่มีวันถูกมองว่าตาย
        params={"status": "eq.processing", "updated_at": f"lt.{iso}"},
        json={"status": "pending"},
        timeout=30,
    )
    r.raise_for_status()
    n = len(r.json())
    if n:
        print(f"requeue งานค้าง processing เกิน {CFG['STALE_PROCESSING_MIN']} นาที: {n} งาน")


def download_image(path):
    def once():
        r = requests.get(f"{STORAGE}/object/{requests.utils.quote('purson-jobs/' + path)}",
                         headers=SB_HEADERS, timeout=120)
        r.raise_for_status()
        return r.content
    return _retry(once, f"โหลดภาพ {path}")


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── GPU call ──────────────────────────────────────────────────────────────────
def call_purson(image_bytes_list, prompt):
    """ยิง OpenAI-compatible chat completion 1 ครั้ง คืน (parsed_json|None, raw_text)
    ภาพมาก่อน ข้อความปิดท้าย — ลำดับเดียวกับตอนเทรน · JSON grammar เปิดเสมอ (กติกา 2026-08-29)"""
    content = []
    for b in image_bytes_list:
        b64 = base64.b64encode(b).decode("ascii")
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}})
    content.append({"type": "text", "text": prompt})
    headers = {"Content-Type": "application/json"}
    if CFG.get("PURSON_GPU_KEY"):
        headers["Authorization"] = f"Bearer {CFG['PURSON_GPU_KEY']}"

    def once():
        r = requests.post(
            f"{CFG['PURSON_GPU_URL']}/v1/chat/completions",
            headers=headers,
            json={
                "model": CFG["PURSON_MODEL"],
                "messages": [{"role": "user", "content": content}],
                "max_tokens": CFG["MAX_NEW_TOKENS"],
                # ⚠️ ห้ามเป็น greedy (temperature 0) — วัดจริงแล้วโมเดลหลุดพ่นภาษาจีน
                # 18 นาทีเต็ม token, recall 0% · ค่านี้คือค่าที่ Qwen แนะนำและวัดผ่านจริง
                # serve_purson.py บังคับค่านี้ฝั่ง server อยู่แล้ว แต่ส่งให้ตรงกันไว้ด้วย
                # เผื่อวันหนึ่งสลับไปใช้ vLLM ซึ่ง**เชื่อค่าที่ client ส่งมา**
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "repetition_penalty": 1.15,   # ค่าเดียวกับ infer_house_t03.py
                "response_format": {"type": "json_object"},
            },
            timeout=CFG["PAGE_TIMEOUT_S"],
        )
        r.raise_for_status()
        return r
    try:
        r = once()
    except requests.exceptions.ReadTimeout:
        # อ่านไม่ทันเวลา = โมเดลยังคิดอยู่จริง ๆ ยิงซ้ำมีแต่ทำให้ GPU หนักกว่าเดิม
        raise
    except Exception:
        # ต่อไม่ติด/5xx = tunnel สะดุดหรือ server เพิ่งรีสตาร์ท — รอแล้วยิงใหม่ได้
        r = _retry(once, "ยิงโมเดล")
    raw = r.json()["choices"][0]["message"]["content"] or ""
    try:
        return json.loads(strip_fence(raw)), raw
    except Exception:
        return None, raw


def call_purson_safe(image_bytes_list, prompt):
    """เหมือน call_purson แต่ไม่โยน exception ออกไปทำลายทั้งงาน — คืน (None, เหตุผล) แทน

    เจอจริง 1 ก.ย.: บ้าน 18 หน้า pass0 ครบ + pass2 เสร็จไปแล้ว 2 งาน แล้วหน้าฐานรากหน้าเดียว
    ตอบเกิน 25 นาที (ReadTimeout) → **งานทั้งใบพัง** หายทั้ง 18+2 งานที่ทำไปแล้วทิ้งเปล่าๆ ทั้งที่
    มันคือแค่ "หน้านี้อ่านไม่ทัน" ไม่ใช่ทั้งบ้านอ่านไม่ได้ — มะขามสั่งให้ข้ามหน้าที่พังแล้วทำหน้า
    อื่นต่อแทน เหมือนที่ pass1/1.5 (local CPU) ทำอยู่แล้ว: ล้มได้ทีละจุด ไม่ล้มยกบ้าน"""
    try:
        return call_purson(image_bytes_list, prompt)
    except Exception as e:
        return None, f"ยิงโมเดลไม่สำเร็จ ({type(e).__name__}: {e})"


# ── pass1/1.5/2.5 (local CPU, no GPU/network) ──────────────────────────────────
def run_pass1_organize(house, classified, images):
    """pass1: ตัด view + จัด folder ผ่าน organize.py จริง (subprocess, ห้ามเขียนใหม่)
    คืน workroot (Path) ถ้าสำเร็จ, None ถ้าอะไรก็ตามพัง — ผู้เรียกต้อง fallback เป็นเต็มหน้า"""
    if not ORGANIZE_PY.exists():
        return None
    tmp = Path(tempfile.mkdtemp(prefix="purson_p1_"))
    img_dir = tmp / "image"
    img_dir.mkdir(parents=True)
    pages = []
    for doc in classified:
        page = doc["_page"]
        fname = f"page_{page}.png"
        (img_dir / fname).write_bytes(images[page])
        pages.append({"png": str(page), "image": fname,
                     "sheet_code": doc.get("sheet_code"), "sheet_name": doc.get("sheet_name"),
                     "building": doc.get("building") or "main", "views": doc.get("views") or []})
    pass0_path = tmp / "pass0_for_organize.json"
    pass0_path.write_text(json.dumps({"house": house, "pages": pages}, ensure_ascii=False),
                          encoding="utf-8")
    out_dir = tmp / "work"
    r = subprocess.run(
        [sys.executable, str(ORGANIZE_PY), "--pass0", str(pass0_path),
         "--images-root", str(img_dir), "--out", str(out_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if r.returncode != 0:
        return None
    workroot = out_dir / house
    return workroot if workroot.is_dir() else None


def run_cv_scan(workroot, pass25=False):
    """pass1.5 (pass25=False) หรือ pass2.5 (pass25=True) — subprocess cv_scan.py --manifest
    คืน True/False สำเร็จ; ไม่ throw — ผู้เรียกอ่านผลจากไฟล์เอง ไม่มีไฟล์ = ไม่มี hint แค่นั้น"""
    if not CV_SCAN_PY.exists():
        return False
    args = [sys.executable, str(CV_SCAN_PY), "--manifest", str(workroot)]
    if pass25:
        args.append("--pass25")
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    return r.returncode == 0


# subtask → คลาสที่ cv_scan.py ต้องเจออย่างน้อย 1 ตัวถึงจะเชื่อครอปนี้ (plan_slab
# ไม่มีเทมเพลตแยกใน cv_scan — ไม่เช็ค ปล่อยผ่านเสมอ)
CROP_TRUST_CLASSES = {"plan_footing": ("footing", "column"), "plan_beam": ("beam",)}


def _was_actually_cropped(workroot, sub, page):
    manifest_path = workroot / "pass2" / sub / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    matches = [e for e in manifest.get("sources", []) if e.get("png") == str(page)]
    return len(matches) == 1 and bool(matches[0].get("cropped"))


def crop_for_task(workroot, sub, page):
    """หา crop + hint ของ (page, sub) นี้จาก manifest ที่ organize.py เขียนไว้
    คืน (crop_bytes หรือ None, hint_text หรือ None) — None ทั้งคู่ = ให้ผู้เรียก fallback เต็มหน้า
    (0 หรือ >1 crop ตรงกับหน้านี้ = ไม่ชัดเจน ไม่เดา ส่งเต็มหน้าแทน)

    เจอจริง 1 ก.ย.: pass0 ตอบ top/bottom ของหน้าที่มี 2 view สลับกัน (บ้านครอบครัวไทย
    เป็นสุข๒ หน้า 12 — สั่ง top=plan_footing ทั้งที่ top จริงคือแปลนโครงหลังคา ฐานรากอยู่
    bottom) organize.py ก็ครอปตามที่สั่งอย่างซื่อสัตย์ ได้ครอปที่ **ไม่มีฐานรากอยู่เลย
    สักตัว** ส่งให้โมเดลอ่านเป็น plan_footing → โมเดลงมหาของที่ไม่มีจนตอบช้าผิดปกติ (ค้าง
    จนครบเพดานเวลา) จุดตรวจนี้ใช้ pass1.5 (CV) เป็นตัวเช็คสุขภาพครอปก่อนส่ง — ถ้า CV
    (ซึ่งเทมเพลตตรงไปตรงมา ไม่มีทางหลอน) หา element ของ subtask นี้ในครอปไม่เจอเลยสักตัว
    แปลว่าครอปน่าจะผิดโซน ไม่เชื่อมัน fallback เต็มหน้าให้โมเดลหาเองแทนดีกว่าส่งครอปที่ผิดแน่ๆ"""
    img_path = _crop_image_path(workroot, sub, page)
    if img_path is None:
        return None, None
    # เช็คสุขภาพเฉพาะกรณีตัดจริง (cropped:true) — หน้าที่มี view เดียวส่งเต็มหน้าตรงๆ
    # (cropped:false) ไม่มี "โซนผิด" ให้พลาด, CV หา 0 ตัวได้เพราะแบบจริงไม่มีสัญลักษณ์
    # แบบที่เทมเพลตรู้จัก ไม่ใช่สัญญาณว่าตัดผิดโซน — ไม่ควร fallback ทิ้งของจริงไป
    classes = CROP_TRUST_CLASSES.get(sub)
    if classes and _was_actually_cropped(workroot, sub, page):
        cv_path = img_path.parent.parent / "cv" / f"{img_path.stem}_cv.json"
        if cv_path.exists():
            try:
                counts = (json.loads(cv_path.read_text(encoding="utf-8")).get("counts") or {})
            except Exception:
                counts = None
            if counts is not None and sum(counts.get(c, 0) for c in classes) == 0:
                return None, None
    crop_bytes = img_path.read_bytes()
    hint_path = img_path.parent.parent / "cv" / f"{img_path.stem}_hint.txt"
    hint = hint_path.read_text(encoding="utf-8") if hint_path.exists() else None
    return crop_bytes, hint


def _crop_image_path(workroot, sub, page):
    """ตัวหา path ของ crop เดียวใช้ร่วมกันระหว่าง crop_for_task และ cv_mark_lookup —
    logic เดียวกัน (0/>1 match = ไม่ชัดเจน คืน None) กันสองที่ตัดสินคนละแบบแล้ว hint กับ
    cv.json อ้างคนละภาพกัน"""
    manifest_path = workroot / "pass2" / sub / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    matches = [e for e in manifest.get("sources", []) if e.get("png") == str(page)]
    if len(matches) != 1:
        return None
    img_path = workroot / "pass2" / sub / matches[0]["image"]
    return img_path if img_path.exists() else None


def cv_mark_lookup(workroot, sub, page):
    """คืน {n: element} ของ crop นี้จาก pass1.5's _cv.json (n = เลข #n ที่ hint บอกโมเดล
    เอาไว้ตอบกลับผ่าน cv_mark) — None ถ้าไม่มี (ไม่ใช่ error แค่ไม่มี hint ให้จับคู่)"""
    img_path = _crop_image_path(workroot, sub, page)
    if img_path is None:
        return None
    cv_path = img_path.parent.parent / "cv" / f"{img_path.stem}_cv.json"
    if not cv_path.exists():
        return None
    try:
        scan = json.loads(cv_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return {el["n"]: el for el in scan.get("elements", [])}


def cv_scan_for_task(workroot, sub, page):
    """ผล CV ของ crop นี้รวมสองรอบ: elements (#n จาก pass1.5) + self_harvest_points (pass2.5)
    คืน dict เดียวให้ pass3 กิน · None ถ้าไม่มีไฟล์ (pass3 ก็ยังวัด element ปกติได้ แค่ไม่มี
    จุด CV-only มารายงาน)"""
    img_path = _crop_image_path(workroot, sub, page)
    if img_path is None:
        return None
    cv_dir = img_path.parent.parent / "cv"
    out = {}
    for fname, key in ((f"{img_path.stem}_cv.json", "elements"),
                       (f"{img_path.stem}_cv25.json", "self_harvest_points")):
        f = cv_dir / fname
        if not f.exists():
            continue
        try:
            out[key] = json.loads(f.read_text(encoding="utf-8")).get(key) or []
        except Exception:
            pass
    return out or None


def merge_cv_marks(doc, workroot, sub, page):
    """ปิดวง cv_mark: element ที่โมเดล pass2 ตอบพร้อม cv_mark → เติม cv_position (พิกัด
    pixel จริงจากบัญชี #n ของ pass1.5) เข้าไป — จับคู่โดยตรงด้วยเลข #n ไม่ใช่ปัญหา spatial
    matching แบบตอนสร้างชุดเทรน (นั่นคือจับคู่ GT กับ CV ที่ไม่มีเลขร่วมกัน อันนี้ทั้งสอง
    ฝั่งอ้างเลข #n เดียวกันอยู่แล้วจาก hint — เทียบตรงๆ พอ) cv_mark ที่ไม่มีเลขนี้จริง
    (โมเดลหลอน) ติดธงใน warnings[] ไม่ทิ้งเงียบ ไม่ทำให้ pass2 ล้ม"""
    els = doc.get("elements")
    if not isinstance(els, list):
        return doc
    marks = cv_mark_lookup(workroot, sub, page)
    if marks is None:
        return doc
    stray = []
    for el in els:
        n = el.get("cv_mark")
        if n is None:
            continue
        m = marks.get(n)
        if m is None:
            stray.append(n)
            continue
        el["cv_position"] = {"cx": m["cx"], "cy": m["cy"], "w": m["w"], "h": m["h"],
                             "class": m["class"]}
    if stray:
        doc.setdefault("warnings", []).append(
            f"cv_mark ที่ไม่มีจริงในบัญชี pass1.5: {stray} — โมเดลอาจหลอนเลข ไม่ผูกพิกัดให้")
    return doc


def collect_pass15_files(workroot):
    """pass1.5 base scan (#n + พิกัด pixel ต่อ element) — เก็บเข้า files[] เหมือนกัน
    เพราะ cv_mark ที่โมเดล pass2 ตอบกลับมาอ้างเลข #n พวกนี้ แต่ยังไม่มีโค้ดจับคู่กลับ
    (เป็นหน้าที่ pass3 ที่ยังไม่มีตัวรัน) — ไม่เก็บไว้ = เลข #n ที่โมเดลตอบไม่มีอะไรอ้างอิงได้เลย
    คืน (files_list, n_elements_total)"""
    out, n_total = [], 0
    for sub in PLAN_SUBTASKS:
        cv_dir = workroot / "pass2" / sub / "cv"
        if not cv_dir.is_dir():
            continue
        for f in sorted(cv_dir.glob("*_cv.json")):
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            n_total += len(doc.get("elements") or [])
            out.append({"name": f"cv15_{sub}_{f.stem}.json", "json": doc})
    return out, n_total


def collect_pass25_files(workroot):
    """pass2.5 self-harvest sidecar — เก็บเข้า files[] ไว้ใช้ตอน pass3 (ยังไม่มีตัวรวมผล
    วันนี้จึงยังไม่ถูกใช้จริง แค่ไม่ทิ้งของที่คำนวณไปแล้ว) คืน (files_list, n_added_total)"""
    out, added_total = [], 0
    for sub in PLAN_SUBTASKS:
        cv_dir = workroot / "pass2" / sub / "cv"
        if not cv_dir.is_dir():
            continue
        for f in sorted(cv_dir.glob("*_cv25.json")):
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            added_total += doc.get("self_harvest_added", 0)
            out.append({"name": f"cv25_{sub}_{f.stem}.json", "json": doc})
    return out, added_total


# ── pipeline ──────────────────────────────────────────────────────────────────
def run_house_extract(job):
    global JOB_T0
    JOB_T0 = time.time()
    job_id = job["id"]
    pages = job["payload"]["pages"]
    warnings, files, timings = [], [], {}
    meta = {"phase": 1, "phase_total": 3, "pages": len(pages)}

    # ดาวน์โหลดภาพทุกหน้า
    set_progress(job_id, "download", 0, len(pages), **meta)
    images = {}  # page number -> bytes
    for i, p in enumerate(pages, 1):
        images[p["page"]] = download_image(p["path"])
        set_progress(job_id, "download", i, len(pages), **meta)

    # pass0 — จำแนกทีละหน้า
    t0 = time.time()
    meta["phase"] = 2
    classified = []
    for i, p in enumerate(pages, 1):
        doc, raw = call_purson_safe([images[p["page"]]], PASS0_PROMPT)
        if doc is None:
            warnings.append(f"pass0 หน้า {p['page']}: {raw or 'JSON เสีย'} — ข้ามหน้านี้")
        else:
            doc["_page"] = p["page"]
            classified.append(doc)
        set_progress(job_id, "pass0", i, len(pages),
                     note=f"หน้า {p['page']}", warnings=len(warnings), **meta)
    timings["pass0_s"] = round(time.time() - t0, 1)
    files.append({"name": "pass0.json", "json": {"pages": classified}})

    # pass1 + pass1.5 — local CPU, ล้มได้โดยไม่ล้มทั้งงาน (fallback = เต็มหน้า ไม่มี hint)
    workroot = None
    try:
        workroot = run_pass1_organize(job_id, classified, images)
        if workroot:
            if run_cv_scan(workroot, pass25=False):
                # เก็บบัญชี #n+พิกัดไว้ — โมเดล pass2 ตอบ cv_mark อ้างเลขพวกนี้ ไม่เก็บ
                # ไว้ = เลขที่โมเดลตอบไม่มีอะไรให้จับคู่กลับเลย (ยังไม่มีตัวจับคู่จริง = pass3)
                cv15_files, n_cv15 = collect_pass15_files(workroot)
                files.extend(cv15_files)
                if cv15_files:
                    warnings.append(
                        f"pass1.5: CV เห็น {n_cv15} จุด ({len(cv15_files)} ไฟล์) — "
                        f"เก็บไว้ให้ pass3 จับคู่กับ cv_mark ที่โมเดลตอบ (ยังไม่มีตัวจับคู่จริง)")
            else:
                warnings.append("pass1.5 (cv_scan.py) ล้ม — plan_* ไม่มี CV hint แนบ")
        else:
            warnings.append("pass1 (organize.py) ล้ม — ส่งเต็มหน้าทุกงานเหมือนเดิม")
    except Exception as e:
        warnings.append(f"pass1/1.5 ล้ม ({type(e).__name__}: {e}) — ส่งเต็มหน้าแทน")
        workroot = None

    # วางแผนงาน pass2: (page, subtask) ไม่ซ้ำ + หน้าที่ติดธง gridline
    grid_pages, tasks = [], []
    for doc in classified:
        page = doc["_page"]
        subs_here = set()
        for v in doc.get("views") or []:
            sub = v.get("subtask")
            if v.get("also_gridline") and page not in grid_pages:
                grid_pages.append(page)
            if not sub or sub in subs_here:
                continue
            subs_here.add(sub)
            if sub not in TRAINED_SUBTASKS:
                # เงียบสำหรับหน้ารองที่รู้อยู่แล้วว่าไม่เอา (pass4 ยกเลิก) · เตือนสำหรับ
                # ตัวที่มี prompt อยู่จริงแต่ไม่ได้เทรน เพราะนั่นคือกับดักที่คนอ่านโค้ดจะพลาด
                if subtask_prompt(sub) is not None:
                    warnings.append(
                        f"หน้า {page}: subtask '{sub}' มี prompt แต่โมเดลไม่ได้เทรนมา — ข้าม")
                continue
            tasks.append((page, sub))

    # pass2 ลำดับ: gridline ก่อน (ผลเป็น GRID MASTER ให้ plan_* ทุกตัว)
    t0 = time.time()
    meta["phase"] = 3
    meta["tasks"] = len(tasks)
    gm_text = None
    grid_master = None   # dict จริง (ไม่ใช่ข้อความ) — pass3 ใช้เป็นไม้บรรทัดวัดเมตร
    # นับ gridline เป็นงานที่ 1 ถ้ามีจริง — เดิม total บวก 1 แต่ตัวนับวิ่งแค่ 1..len(tasks)
    # ทำให้แถบไม่มีวันถึง 100% เมื่อมีหน้ากริด (ไม่เคยเห็นเพราะงานทดสอบไม่มีหน้ากริด)
    grid_step = 1 if grid_pages else 0
    pass2_total = len(tasks) + grid_step
    if grid_pages:
        gp = grid_pages[:4]  # เพดานเดียวกับตอนเทรน
        prompt = subtask_prompt("gridline")
        if prompt:
            set_progress(job_id, "pass2", 0, pass2_total, "อ่านผังกริด (ใช้อ้างอิงทุกหน้า)",
                         warnings=len(warnings), **meta)
            doc, raw = call_purson_safe([images[p] for p in gp], prompt)
            if doc is None:
                warnings.append(f"gridline: {raw or 'JSON เสีย'} — plan_* จะไม่มี GRID MASTER แนบ")
                files.append({"name": "grid_master.raw.txt", "json": {"raw_text": raw}})
            else:
                doc.setdefault("pattern", SUBTASK_PATTERN["gridline"])
                files.append({"name": "grid_master.json", "json": doc})
                grid = doc.get("grid")
                if isinstance(grid, dict):
                    grid_master = grid
                    slim = {"grid": {k: grid.get(k) for k in ("x_lines", "y_lines") if k in grid}}
                    gm_text = ("\n\nGRID MASTER (resolved axes for this building)\n"
                               + json.dumps(slim, ensure_ascii=False))
    else:
        warnings.append("pass0 ไม่พบหน้าไหนติดธง gridline — plan_* ไม่มี GRID MASTER แนบ")

    # pass2 ราย (page, subtask)
    n_elements = 0
    plan_docs = []   # [(sub, page, doc)] — pass3 กลับมาเติมผลวัดทีหลัง (dict ตัวเดียวกับใน
                     # files[] เพราะเป็น reference — แก้ตรงนี้ = ผลที่ส่งกลับเว็บเปลี่ยนด้วย)
    for i, (page, sub) in enumerate(tasks, 1):
        prompt = subtask_prompt(sub)
        if sub.startswith("plan_") and gm_text:
            prompt += gm_text
        img_bytes = images[page]
        if workroot and sub in PLAN_SUBTASKS:
            crop_bytes, hint = crop_for_task(workroot, sub, page)
            if crop_bytes:
                img_bytes = crop_bytes
            if hint:
                prompt += "\n\n" + hint
        doc, raw = call_purson_safe([img_bytes], prompt)
        name = f"page_{page:02d}_{sub}"
        if doc is None:
            warnings.append(f"{name}: {raw or 'JSON เสีย'} — ข้ามหน้านี้ ไปหน้าถัดไปต่อ ไม่เดาค่า")
            files.append({"name": f"{name}.raw.txt", "json": {"raw_text": raw}})
        else:
            doc = sanitize_elements(doc)
            doc.setdefault("pattern", SUBTASK_PATTERN.get(sub, sub))
            if workroot and sub in PLAN_SUBTASKS:
                doc = merge_cv_marks(doc, workroot, sub, page)
                plan_docs.append((sub, page, doc))
            els = doc.get("elements")
            n_elements += len(els) if isinstance(els, list) else 0
            files.append({"name": f"{name}.json", "json": doc})
        set_progress(job_id, "pass2", i + grid_step, pass2_total,
                     note=f"หน้า {page} · {SUBTASK_TH.get(sub, sub)}",
                     elements=n_elements, warnings=len(warnings), **meta)
    timings["pass2_s"] = round(time.time() - t0, 1)

    # pass2.5 — self-harvest sidecar, local CPU (จุดที่คลังกลางจับข้ามซีรีส์ไม่ติด)
    if workroot:
        try:
            if run_cv_scan(workroot, pass25=True):
                cv25_files, added = collect_pass25_files(workroot)
                files.extend(cv25_files)
                if cv25_files:
                    warnings.append(
                        f"pass2.5: self-harvest {len(cv25_files)} ไฟล์ (+{added} จุด)")
        except Exception as e:
            warnings.append(f"pass2.5 ล้ม ({type(e).__name__}: {e}) — ข้าม ไม่กระทบผลหลัก")

    # pass3 — วัดระยะจริง: หมุด (grid_ref ที่โมเดลอ่านได้ + พิกัด CV) → px ต่อเมตร →
    # เติมตำแหน่งเมตรให้ทุก element, snap grid ref ให้ตัวที่โมเดลไม่ได้ตอบ, และรายงาน
    # จุดที่ CV เห็นแต่โมเดลไม่พูดถึง · ต้องรันหลัง pass2.5 เพราะกินจุด self-harvest ด้วย
    if workroot and plan_docs:
        t3 = time.time()
        if not isinstance(grid_master, dict):
            warnings.append("pass3 ข้าม: ไม่มี grid master (ไม่มีหน้ากริด หรือ gridline JSON เสีย)")
        else:
            reports, ok_pages = {}, 0
            fill_totals = {"grid_refs": 0, "span": 0, "elements": 0}
            set_progress(job_id, "pass3", 0, len(plan_docs), "วัดระยะเทียบผังกริด",
                         elements=n_elements, warnings=len(warnings), **meta)
            for sub, page, doc in plan_docs:
                try:
                    rep = measure_page(doc, grid_master, cv_scan_for_task(workroot, sub, page))
                except Exception as e:
                    warnings.append(f"pass3 หน้า {page} ({sub}) ล้ม ({type(e).__name__}: {e})")
                    continue
                # เติมของที่ขาดกลับเข้า doc ของ pass2 — กฎมะขาม: เติมได้ ห้ามเอาออก
                # (doc เป็น reference ตัวเดียวกับใน files[] ผลที่ส่งกลับเว็บจึงได้ของเติมด้วย)
                filled = merge_into_pass2(doc, rep, grid_master, sub)
                rep["filled"] = filled
                for k in ("grid_refs", "span", "elements"):
                    fill_totals[k] += filled[k]
                reports[f"page_{page:02d}_{sub}"] = rep
                ok_pages += 1 if rep.get("ok") else 0
                set_progress(job_id, "pass3", len(reports), len(plan_docs),
                             note=f"หน้า {page} · {SUBTASK_TH.get(sub, sub)}",
                             elements=n_elements, warnings=len(warnings), **meta)
            files.append({"name": "pass3_measure.json",
                          "json": {"pages": reports, "grid_master_used": True}})
            n_cv_only = sum(len(r.get("cv_only") or []) for r in reports.values())
            n_off = sum(len(r.get("grid_check") or []) for r in reports.values())
            warnings.append(
                f"pass3: วัดได้ {ok_pages}/{len(plan_docs)} หน้า · เติม grid_ref "
                f"{fill_totals['grid_refs']} · เติมความยาวคาน {fill_totals['span']} · "
                f"เพิ่ม element จาก CV {fill_totals['elements']} · ref ตำแหน่งไม่ตรง {n_off} ตัว "
                f"(จุดที่ CV เห็นทั้งหมด {n_cv_only})")
        timings["pass3_s"] = round(time.time() - t3, 1)

    return {"files": files, "warnings": warnings, "timings": timings}


def run_single_call(job):
    p = job["payload"]
    imgs = [download_image(path) for path in p.get("image_paths", [])]
    prompt = p.get("prompt")
    if not prompt and p.get("subtask"):
        prompt = subtask_prompt(p["subtask"])
    if not prompt:
        raise ValueError("single_call ต้องมี prompt หรือ subtask ที่รู้จัก")
    doc, raw = call_purson(imgs, prompt)
    return {"json": doc, "raw_text": None if doc is not None else raw, "valid": doc is not None}


def main():
    print(f"purson worker เริ่ม — GPU: {CFG['PURSON_GPU_URL']} · model: {CFG['PURSON_MODEL']}"
          f" · prompts: {PROMPTS_DIR}")
    assert subtask_prompt("plan_beam"), "โหลด prompt plan_beam ไม่ได้ — เช็ค PURSON_PROMPTS_DIR"
    requeue_stale()
    while True:
        try:
            job = claim_next_job()
        except Exception as e:
            print(f"⚠️ ต่อ Supabase ไม่ได้: {e} — รอแล้วลองใหม่")
            time.sleep(15)
            continue
        if not job:
            time.sleep(CFG["POLL_INTERVAL_S"])
            continue
        print(f"งาน {job['id']} ({job['job_type']}) เริ่ม {now_iso()}")
        try:
            result = (run_house_extract if job["job_type"] == "house_extract"
                      else run_single_call)(job)
        except Exception as e:
            traceback.print_exc()
            # เขียนสถานะ "ล้มเหลว" เป็น network call เหมือนกัน — ถ้าเน็ตคือสาเหตุที่งานพัง
            # call นี้ก็พังตามไปด้วย ถ้าไม่กันไว้ exception จะทะลุออกนอก while แล้ว
            # **worker ทั้งตัวตาย** ปล่อยงานค้าง processing โดยไม่มีใครทำต่อ
            try:
                update_job(job["id"], {"status": "failed",
                                       "error_message": f"{type(e).__name__}: {e}"})
                print(f"งาน {job['id']} ล้มเหลว: {e}")
            except Exception as e2:
                print(f"งาน {job['id']} ล้มเหลว ({e}) และรายงานกลับไม่ได้ ({e2}) — "
                      f"ปล่อยค้าง processing ให้ requeue_stale เก็บไปทำใหม่", flush=True)
            continue
        # แยกออกมานอก try เดิม: ถ้าเขียน "done" ไม่สำเร็จ ห้ามตกไปทาง except แล้ว
        # ประทับว่า failed ทั้งที่ผลออกมาครบแล้ว (ทิ้งงาน 40 นาทีทิ้งเปล่า)
        try:
            update_job(job["id"], {"status": "done", "result": result})
            print(f"งาน {job['id']} เสร็จ")
        except Exception as e:
            print(f"⚠️ งาน {job['id']} ทำเสร็จแล้วแต่เขียนผลกลับไม่ได้: {e}\n"
                  f"   งานจะค้างสถานะ processing → requeue_stale จะเก็บไปทำใหม่รอบหน้า",
                  flush=True)


if __name__ == "__main__":
    main()
