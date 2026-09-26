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
  pass3   วัดระยะจริงจากพิกเซล            -> pass3_measure.py (pure, stdlib): หมุด = grid_ref ที่
                                          โมเดลอ่านได้ + พิกัด CV → fit px ต่อเมตร (ลอง 4 ทิศแกน
                                          กำกวม = ปฏิเสธ) · **รายงานอย่างเดียว** (ตัดสิน 2026-09-26):
                                          ไม่แก้ doc ของ pass2 เลย ผลอยู่ใน pass3_measure.json v2 +
                                          grid_master.json "validation" + warnings ระดับงาน
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
import struct
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pass3_measure import (cv_class_fits, grid_validation, marks_look_enumerated,  # noqa: E402
                           measure_page, pass3_file, summary_warnings)  # (pure, stdlib)
from vector_ruler import measure_page_vectors, merge_validation  # noqa: E402  (pure, stdlib)
from vector_ruler import summary_line as vector_summary_line     # noqa: E402
import notify  # noqa: E402  (เสียงบอกเหตุ — ไม่มี dependency ภายนอก)


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
                # "result" ต้องดึงมาด้วย — checkpoint รอบก่อน (ถ้ามี) อยู่ในนี้ ใช้ resume
                # ต่อแทนเริ่มจาก 0 (ดู run_house_extract's resume block)
                "select": "id,job_type,payload,attempts,result"},
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


def save_checkpoint(job_id, files, warnings, timings):
    """เขียน `result` ทับทั้งก้อนระหว่างงานยังไม่จบ (status ยังเป็น processing เหมือนเดิม) —
    2026-09-02 มะขามสั่ง: เก็บผลทุก pass ไว้ระหว่างทาง ไม่ใช่รอจบงานทั้งใบค่อยเขียนทีเดียว
    เหตุผล 2 ข้อ: (1) เข้าไปดูความคืบหน้าจริงได้ก่อนงานจบ ไม่ใช่แค่ progress bar (2) ถ้างานตาย
    กลางทาง (crash/timeout/ปิดเครื่อง) — requeue_stale() ดีดกลับเป็น pending แล้ว worker ตัวไหน
    ก็ตามที่คว้าไปทำต่อจะเห็น result เดิมนี้ผ่าน claim_next_job() แล้ว resume ต่อได้ (ดู resume
    block ต้น run_house_extract) ไม่ต้องเริ่ม pass0 ใหม่ทั้งหมด — ล้มได้ทีละจุดเหมือน pass1.5/2.5
    เขียนบ่อยแค่ไหนไม่ใช่ปัญหา (jsonb ก้อนเดียว ไม่มี history ให้บวมเหมือน progress ที่มี trigger
    touch updated_at ตัวเดียวกัน) — ยอมเขียนถี่กว่าจำเป็นดีกว่าเขียนน้อยไปแล้วข้อมูลหาย
    (update_job เองมี _retry อยู่แล้ว ไม่ต้องห่อซ้ำ)"""
    update_job(job_id, {"result": {"files": files, "warnings": warnings, "timings": timings}})


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


def png_size(png_bytes):
    """(w, h) จาก IHDR — signature 8 ไบต์ แล้ว len+type แล้ว w,h big-endian"""
    if not isinstance(png_bytes, (bytes, bytearray)) or png_bytes[:8] != b"\x89PNG\r\n\x1a\n" \
            or png_bytes[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", png_bytes[16:24])


def load_vectors(payload, images, warnings):
    """vector sidecar v1 ที่เว็บอัปคู่กับ PNG (js/drawing/pdf-vector-sidecar.js) → {page: page_sidecar}
    ใช้เฉพาะหน้าที่กรอบพิกัดตรงกับ PNG ที่โหลดมาจริง (ขนาดไม่ตรง = คนละเฟรม ห้ามใช้)
    ไม่มี/โหลดไม่ได้/เวอร์ชันแปลก = {} + คำเตือน งานเดินต่อเหมือนเดิมทุกอย่าง (ไม่เดา ไม่ล้มงาน)"""
    path = (payload or {}).get("vectors")
    if not path:
        return {}                                          # เว็บรุ่นเก่า / PDF ภาพสแกน
    def once():
        r = requests.get(f"{STORAGE}/object/{requests.utils.quote('purson-jobs/' + path)}",
                         headers=SB_HEADERS, timeout=60)
        r.raise_for_status()
        return r.content
    try:
        doc = json.loads(_retry(once, f"โหลด vector sidecar {path}", tries=2))
    except Exception as e:                                 # 404/เน็ต/JSON เสีย — ห้ามล้มงาน
        warnings.append(f"vector sidecar โหลดไม่ได้ ({type(e).__name__}) — ข้าม ใช้ภาพอย่างเดียว")
        return {}
    if not isinstance(doc, dict) or doc.get("schema") != "constistant.vector_sidecar" or doc.get("v") != 1:
        warnings.append("vector sidecar เวอร์ชันไม่รู้จัก — ข้าม")
        return {}
    out = {}
    for key, pg in (doc.get("pages") or {}).items():
        try:
            page, fr = int(key), pg["frame"]
            want = (int(fr["png_w"]), int(fr["png_h"]))
        except Exception:
            warnings.append(f"vector sidecar หน้า {key}: frame เสีย — ข้ามหน้านี้")
            continue
        got = png_size(images.get(page, b""))
        if got != want:
            warnings.append(f"vector sidecar หน้า {page}: ขนาดภาพ {got} ≠ {want} — กรอบพิกัดไม่ตรง ไม่ใช้")
            continue
        out[page] = pg
    return out


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def release_stuck_jobs():
    """ปลดงานที่ค้าง processing ให้ทำต่อได้ทันที ไม่ต้องรอครบ STALE_PROCESSING_MIN (45 นาที)

    ทำไมต้องมี: requeue_stale() ถูกเรียก**ครั้งเดียวตอนเปิด worker** (ไม่ได้อยู่ในลูป) และปลด
    เฉพาะงานที่เงียบเกิน 45 นาที — ถ้าหน้าต่าง worker ถูกปิดตอนงานเดินไป 10 นาทีแล้วเปิดใหม่
    ทันที งานนั้นจะไม่ถูกปลด (เพิ่งเงียบ 10 นาที) และ worker ตัวใหม่ก็หาไม่เจอเพราะมันคว้าแต่
    งาน pending → งานค้างเฉยๆ ทั้งที่ checkpoint ครบ ไม่มีผลอะไรหายเลย แค่ไม่มีใครหยิบไปทำต่อ

    ⚠️ ห้ามใช้ถ้า worker ตัวเดิมยังวิ่งอยู่จริง — งานจะถูกคว้าซ้ำ = จ่ายค่า GPU สองเท่า
    และผลเขียนทับกันตอนจบ (เหตุผลเดียวกับที่ requeue_stale ดู updated_at ไม่ใช่ claimed_at)
    จึงโชว์เวลาที่รายงานความคืบหน้าล่าสุดแล้วบังคับให้ยืนยันด้วยมือ ไม่ทำอัตโนมัติ"""
    r = requests.get(f"{REST}/purson_jobs", headers=SB_HEADERS,
                     params={"status": "eq.processing",
                             "select": "id,updated_at,progress", "order": "updated_at.desc"},
                     timeout=30)
    r.raise_for_status()
    jobs = r.json()
    if not jobs:
        print("ไม่มีงานค้างสถานะ processing — ไม่มีอะไรต้องปลด")
        return

    print(f"\nเจองานค้าง {len(jobs)} งาน:\n")
    now = time.time()
    for j in jobs:
        try:
            last = time.mktime(time.strptime(j["updated_at"][:19], "%Y-%m-%dT%H:%M:%S"))
            quiet = f"{int((now - last - time.timezone) / 60)} นาทีที่แล้ว"
        except Exception:
            quiet = j.get("updated_at", "?")
        p = j.get("progress") or {}
        print(f"  งาน {j['id']}")
        print(f"    รายงานความคืบหน้าล่าสุด: {quiet}")
        print(f"    ทำถึง: {p.get('step', '?')} {p.get('done', '?')}/{p.get('total', '?')}\n")

    print("⚠️  ถ้าเวลาข้างบนเพิ่งผ่านไปไม่กี่นาที แปลว่า worker ตัวเดิม**น่าจะยังวิ่งอยู่**")
    print("    ปลดตอนนี้จะกลายเป็นทำซ้ำสองตัว เสียค่า GPU สองเท่า — ปลดเมื่อแน่ใจว่าตัวเดิมตายแล้วเท่านั้น")
    if input("\nปลดทั้งหมดให้ทำต่อเลยไหม? [y/N] ").strip().lower() != "y":
        print("ยกเลิก — ไม่ได้แตะอะไร")
        return

    for j in jobs:
        update_job(j["id"], {"status": "pending"})
        print(f"✅ ปลดงาน {j['id']} แล้ว")
    print("\nเปิดหน้าต่างรับงานไว้ เดี๋ยวมันจะคว้าไปทำต่อจาก checkpoint เดิมเอง ไม่เริ่ม pass0 ใหม่")


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
                # ⚠️ จำเป็นเมื่อสลับไป vLLM/SGLang (2026-09-20): Qwen3.6 เป็น thinking-by-default
                # และตัว **เซิร์ฟเวอร์** เป็นคนประกอบ chat template ไม่ใช่เรา — ถ้าไม่ปิด โมเดลจะ
                # เขียน <think> ยาวจนหมด token ก่อนถึง JSON (บั๊กคลาส t01 ที่ serve_purson.py
                # กันไว้ด้วย enable_thinking=False ฝั่งตัวเองอยู่แล้ว แต่ engine อื่นไม่รู้)
                # serve_purson.py เมินคีย์ที่ไม่รู้จัก ส่งไปด้วยจึงปลอดภัยทั้งสามเส้นทาง
                "chat_template_kwargs": {"enable_thinking": False},
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
    body = r.json()
    choice = (body.get("choices") or [{}])[0]
    raw = (choice.get("message") or {}).get("content") or ""
    try:
        return json.loads(strip_fence(raw)), raw
    except Exception:
        # ⚠️ แยกให้ออกระหว่าง "โมเดลตอบมั่ว" กับ "เราตัดมันเองเพราะชนเพดาน token"
        # เดิมสองเคสนี้คืนค่าเหมือนกันเป๊ะ หน้าที่คำตอบยาวเกินจึงหายไปทั้งหน้าแบบเงียบสนิท
        # ไม่มีข้อความบอกสักคำว่าทำไม (เจอจริง 23 ก.ย. หน้า S-01 เขียน 15,910 ตัวอักษร
        # = ชนเพดาน 6000 token พอดี แล้ว JSON ขาดครึ่ง)
        # หมายเหตุ: เซิร์ฟเวอร์รุ่นเก่ายังตอบ "stop" ตายตัว เช็คความยาวเสริมไว้ด้วย
        # ลองกู้ก่อนยอมแพ้ — คำตอบที่โดนตัดมักสมบูรณ์เกือบทั้งก้อน เสียแค่ชิ้นสุดท้าย
        salvaged, was_repaired = salvage_truncated_json(strip_fence(raw))
        if salvaged is not None and was_repaired:
            n = len((salvaged or {}).get("elements") or [])
            print(f"   ⚕️ กู้ JSON ที่โดนตัดสำเร็จ — ได้ชิ้นส่วนคืน {n} ตัว "
                  f"(ชิ้นสุดท้ายที่เขียนไม่จบถูกตัดทิ้ง)", flush=True)
            if isinstance(salvaged, dict):
                salvaged.setdefault("warnings", []).append(
                    "คำตอบโดนตัดเพราะชนเพดาน token — กู้กลับมาได้ แต่ชิ้นส่วนท้ายสุด "
                    "อาจขาดไปบางตัว ควรตรวจก่อนใช้จริง")
            return salvaged, raw
        if choice.get("finish_reason") == "length":
            return None, ("คำตอบโดนตัดกลางคันเพราะชนเพดาน token — หน้านี้มีของเยอะเกินกว่าที่ "
                          f"MAX_NEW_TOKENS={CFG['MAX_NEW_TOKENS']} จะเขียนครบ "
                          "(แก้ได้สองทาง: ขยายเพดานแล้วยอมให้ช้าลง หรือแยกผังในหน้านี้ออกเป็นคนละภาพ) "
                          f"· ที่เขียนมาได้ {len(raw)} ตัวอักษร · ท้ายสุด: ...{raw[-160:]}")
        return None, raw


def salvage_truncated_json(text):
    """กู้ JSON ที่ถูกตัดกลางคัน — ถอยไปถึงชิ้นที่สมบูรณ์ตัวสุดท้าย แล้วปิดวงเล็บที่ค้างอยู่

    ทำไมต้องมี (วัดจริง 23 ก.ย. 2026): หน้า S-01 ของบ้านครอบครัวไทยเป็นสุข2 ตอบยาว
    15,910 ตัวอักษรจนชนเพดาน token แล้ว JSON ขาดกลางประโยค ระบบเดิมโยนทิ้งทั้งไฟล์
    เหลือชิ้นส่วนเข้าโปรเจกต์แค่ 5 ตัว — **กู้แล้วได้คืน 49 ตัว** (ฐานราก 5 + คานคอดิน 44
    ซึ่ง 44 ตัวมีความยาวช่วงจริงจากตารางกริดครบ) คือของที่ทิ้งไปคือเนื้อหลักทั้งก้อน

    วิธี: เดินอ่านทีละตัวอักษรโดยรู้ว่าตอนนี้อยู่ในสตริงหรือไม่ (ห้ามนับวงเล็บที่อยู่ในสตริง)
    จำตำแหน่งที่ "ปิดชิ้นส่วนพอดี" ไว้ แล้วตัดตรงนั้น ปิดวงเล็บที่ยังค้างย้อนกลับตามลำดับ
    กติกา "ไม่เดา" ยังอยู่: ถ้าปิดแล้วยังแปลงไม่ผ่าน คืน None ไม่ยัดข้อมูลมั่ว
    """
    try:
        return json.loads(text), False
    except Exception:
        pass
    stack, in_str, esc, cut, cut_stack = [], False, False, -1, None
    for i, c in enumerate(text):
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in "{[":
            stack.append(c)
        elif c in "}]":
            if stack:
                stack.pop()
            # ปิดชิ้นส่วนที่อยู่ในอาร์เรย์พอดี = จุดตัดที่ปลอดภัย
            if len(stack) >= 2 and stack[-1] == "[":
                cut, cut_stack = i, list(stack)
    if cut < 0 or not cut_stack:
        return None, False
    closing = "".join("}" if b == "{" else "]" for b in reversed(cut_stack))
    try:
        return json.loads(text[:cut + 1] + closing), True
    except Exception:
        return None, False


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


# เพดานเวลา cv_scan ต่อรอบ — โตตามจำนวนภาพ (เดิม 300 วิคงที่ทั้งงาน: 83b8e52c มี 10 ครอป ใช้จริง
# 430-590 วิ ชนเพดานทั้ง pass1.5 และ 2.5) · วัดจริง ~29-43 วิ/ครอป (เครื่องว่าง/มีโหลด) → เผื่อ 90 วิ
# · พื้น 300 = ค่าเดิม (งานเล็กไม่เปลี่ยน) · เพดาน 30 นาทีกันค้างไม่รู้จบ (GPU เช่ารออยู่ระหว่าง pass1.5)
CV_SCAN_MIN_S, CV_SCAN_PER_IMAGE_S, CV_SCAN_MAX_S = 300, 90, 1800
CV_SCAN_SUBTASKS = ("plan_footing", "plan_column", "plan_beam", "plan_slab")   # = cv_scan.py PLAN_SUBTASKS


def cv_scan_timeout_s(workroot):
    """เพดานเวลาของ cv_scan --manifest = จำนวนภาพที่มันจะสแกน × ต่อภาพ (มีพื้น/เพดาน)"""
    n = sum(1 for sub in CV_SCAN_SUBTASKS
            for p in (Path(workroot) / "pass2" / sub / "images").glob("*.png") if "_marked" not in p.stem)
    return max(CV_SCAN_MIN_S, min(CV_SCAN_MAX_S, n * CV_SCAN_PER_IMAGE_S))


def run_cv_scan(workroot, pass25=False, notes=None):
    """pass1.5 (pass25=False) หรือ pass2.5 (pass25=True) — subprocess cv_scan.py --manifest
    คืน True/False สำเร็จ; ไม่ throw (รวมถึงตอนเกินเวลา — เดิม TimeoutExpired หลุดออกไปทำให้ผู้เรียก
    ทิ้งครอปของ pass1 ทั้งงาน) · notes (list) รับเหตุผลภาษาไทยเมื่อไม่สำเร็จ
    ผู้เรียกอ่านผลจากไฟล์เอง ไม่มีไฟล์ = ไม่มี hint แค่นั้น (ภาพที่สแกนเสร็จก่อนหมดเวลายังมีไฟล์ครบ)"""
    if not CV_SCAN_PY.exists():
        if notes is not None:
            notes.append("ไม่พบ cv_scan.py")
        return False
    args = [sys.executable, str(CV_SCAN_PY), "--manifest", str(workroot)]
    if pass25:
        args.append("--pass25")
    timeout = cv_scan_timeout_s(workroot)
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        if notes is not None:
            notes.append(f"เกินเวลา {timeout} วินาที")
        return False
    if r.returncode != 0 and notes is not None:
        notes.append(f"ล้ม (exit {r.returncode})")
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


def merge_cv_marks(doc, workroot, sub, page, notes=None):
    """ปิดวง cv_mark: element ที่โมเดล pass2 ตอบพร้อม cv_mark → เติม cv_position (พิกัด
    pixel จริงจากบัญชี #n ของ pass1.5) เข้าไป — จับคู่โดยตรงด้วยเลข #n

    ⚠️ cv_mark คือ "คำอ้าง" ของโมเดล ไม่ใช่ความจริง (ตรวจ 2026-09-26): ภาพที่ส่งไปไม่มีเลขกำกับ
    โมเดลจึงตอบ 1..N ตามลำดับรายการ (เจอ 5/5 หน้าจริง) → ถ้าทั้งหน้าดูเป็นเลขลำดับ ไม่ผูกเลยสักตัว
    และ mark ที่ชี้กล่อง CV คนละชนิดกับ element (ฐานราก→กล่องคาน, detail_view→อะไรก็ตาม) ไม่ผูก
    cv_mark ที่ไม่มีเลขนี้จริง (โมเดลหลอน) ติดธงไม่ทิ้งเงียบ ไม่ทำให้ pass2 ล้ม

    ข้อความไปที่ notes (list) ถ้าส่งมา — worker ส่ง warnings ระดับงาน เพราะ doc.warnings ฝั่งเว็บ
    แสดงเป็น "[โมเดล] …" (นี่คือระบบพูด ไม่ใช่โมเดล) · ไม่ส่ง = เขียนลง doc.warnings แบบเดิม"""
    els = doc.get("elements")
    if not isinstance(els, list):
        return doc
    marks = cv_mark_lookup(workroot, sub, page)
    if marks is None:
        return doc
    msgs = []
    if marks_look_enumerated(els):
        k = sum(1 for el in els if isinstance(el, dict) and el.get("cv_mark") is not None)
        msgs.append(f"ไม่ใช้ cv_mark ของหน้านี้ ({k} ตัว): เลขเรียงตามลำดับรายการที่ตอบ ไม่ได้ชี้กล่อง "
                    f"CV จริง — ไม่ผูกพิกัดให้")
    else:
        stray, wrong = [], []
        for el in els:
            if not isinstance(el, dict):
                continue
            n = el.get("cv_mark")
            if n is None:
                continue
            m = marks.get(n)
            if m is None:
                stray.append(n)
                continue
            if not cv_class_fits(el.get("element_type"), m.get("class")):
                wrong.append(f"{el.get('element_id') or el.get('id') or '?'} "
                             f"({el.get('element_type')}) → #{n} {m.get('class')}")
                continue
            el["cv_position"] = {"cx": m["cx"], "cy": m["cy"], "w": m["w"], "h": m["h"],
                                 "class": m["class"]}
        if stray:
            msgs.append(f"cv_mark ที่ไม่มีจริงในบัญชี pass1.5: {stray} — โมเดลอาจหลอนเลข ไม่ผูกพิกัดให้")
        if wrong:
            msgs.append(f"cv_mark ชี้กล่อง CV คนละชนิดกับ element: {', '.join(wrong)} — ไม่ผูกพิกัดให้")
    if msgs:
        (notes if notes is not None else doc.setdefault("warnings", [])).extend(msgs)
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

    # resume — checkpoint รอบก่อน (ถ้ามี งานนี้เคยตายกลางทางแล้วถูก requeue_stale() ดีดกลับมา
    # pending) เก็บ files/warnings/timings ที่ทำสำเร็จไปแล้วไว้ก่อน แต่ละ pass ด้านล่างเช็คเอง
    # ว่ามีของเดิมให้ใช้ต่อไหม ก่อนจะยิงโมเดลซ้ำ — ล้มได้ทีละจุด ไม่เริ่มใหม่ทั้งบ้าน
    prev = job.get("result") or {}
    prev_by_name = {f["name"]: f for f in (prev.get("files") or [])}
    if prev_by_name:
        warnings.extend(prev.get("warnings") or [])
        timings.update(prev.get("timings") or {})

    # ดาวน์โหลดภาพทุกหน้า (เร็ว ไม่คุ้มเก็บ checkpoint แยก — โหลดใหม่ทุกรอบเรียบง่ายกว่า)
    set_progress(job_id, "download", 0, len(pages), **meta)
    images = {}  # page number -> bytes
    for i, p in enumerate(pages, 1):
        images[p["page"]] = download_image(p["path"])
        set_progress(job_id, "download", i, len(pages), **meta)
    vectors = {}   # โหลดใหม่ทุกรอบเหมือนภาพ (เล็ก + ไม้บรรทัดเป็น pure ใช้ไม่กี่ ms ไม่ต้อง checkpoint)
    try:
        vectors = load_vectors(job["payload"], images, warnings)
    except Exception as e:   # loader ห่อเองแล้ว — กันเผื่อ ห้ามล้มงานเพราะ sidecar
        warnings.append(f"vector sidecar ล้ม ({type(e).__name__}) — ข้าม")

    # pass0 — จำแนกทีละหน้า (resume: ถ้า checkpoint มี pass0.json ครบทุกหน้าแล้ว ใช้ของเดิม
    # ไม่ยิงซ้ำ — เดิมเช็คแค่ "มีไฟล์ pass0.json ไหม" ไม่ได้เช็คว่าครบทุกหน้าไหม พอหน้าไหน
    # ยิงพลาด (tunnel หลุด/ConnectionError) โค้ดเดิมจะ "ข้ามหน้านี้" แล้วไม่มีวันจำแนกซ้ำอีก
    # เพราะรอบต่อไปเจอว่ามี pass0.json อยู่แล้วก็เชื่อว่าสมบูรณ์ทันที — เจอจริง 23-24 ก.ย. 69:
    # tunnel หลุดตอน pass0 ทำให้ 21 จาก 29 หน้าโดนข้าม แล้วล็อกอยู่ในนั้นถาวร ทั้งบ้านเหลือ
    # ข้อมูลจริงแค่ ~8 หน้า โดยไม่มีอะไรบอกจนกว่าจะไปนับเองตอนงานจบ**
    t0 = time.time()
    meta["phase"] = 2
    prev_pass0 = prev_by_name.get("pass0.json")
    classified = list(prev_pass0["json"]["pages"]) if prev_pass0 else []
    done_pages = {c["_page"] for c in classified if "_page" in c}
    missing = [p for p in pages if p["page"] not in done_pages]

    if not missing:
        files.append(prev_pass0 or {"name": "pass0.json", "json": {"pages": classified}})
        set_progress(job_id, "pass0", len(pages), len(pages),
                     note="resume จาก checkpoint เดิม (ครบทุกหน้าแล้ว)",
                     warnings=len(warnings), **meta)
    else:
        if prev_pass0:
            print(f"   ↻ pass0 checkpoint เดิมมีแค่ {len(done_pages)}/{len(pages)} หน้า "
                  f"— จำแนกซ้ำเฉพาะ {len(missing)} หน้าที่ขาด: "
                  f"{[p['page'] for p in missing]}", flush=True)
        for i, p in enumerate(missing, 1):
            doc, raw = call_purson_safe([images[p["page"]]], PASS0_PROMPT)
            if doc is None:
                warnings.append(f"pass0 หน้า {p['page']}: {raw or 'JSON เสีย'} — ข้ามหน้านี้")
            else:
                doc["_page"] = p["page"]
                classified.append(doc)
            set_progress(job_id, "pass0", i, len(missing),
                         note=f"หน้า {p['page']}"
                              + (f" (เติมหน้าที่ขาด {i}/{len(missing)})" if prev_pass0 else ""),
                         warnings=len(warnings), **meta)
        files.append({"name": "pass0.json", "json": {"pages": classified}})
    timings["pass0_s"] = round(time.time() - t0, 1)
    save_checkpoint(job_id, files, warnings, timings)

    # pass1 + pass1.5 — local CPU, ล้มได้โดยไม่ล้มทั้งงาน
    # pass1 ล้ม = ไม่มีครอป → เต็มหน้า · pass1.5 ล้ม/เกินเวลา = **ยังใช้ครอปของ pass1 ต่อ** แค่ไม่มี hint
    # (เดิม try เดียวครอบทั้งคู่ TimeoutExpired ของ cv_scan เลยทำ workroot=None ทิ้งครอปที่ตัดสำเร็จ
    # ไปทั้งงาน ทุกหน้าเลยส่งเต็มหน้า — เจอจริง 83b8e52c 10 ครอป cv_scan ใช้ ~570 วิ เกินเพดาน 300)
    workroot = None
    try:
        workroot = run_pass1_organize(job_id, classified, images)
        if not workroot:
            warnings.append("pass1 (organize.py) ล้ม — ส่งเต็มหน้าทุกงานเหมือนเดิม")
    except Exception as e:
        warnings.append(f"pass1 ล้ม ({type(e).__name__}: {e}) — ส่งเต็มหน้าแทน")
        workroot = None
    if workroot:
        try:
            why = []
            if run_cv_scan(workroot, pass25=False, notes=why):
                # เก็บบัญชี #n+พิกัดไว้ — โมเดล pass2 ตอบ cv_mark อ้างเลขพวกนี้ ไม่เก็บ
                # ไว้ = เลขที่โมเดลตอบไม่มีอะไรให้จับคู่กลับเลย
                cv15_files, n_cv15 = collect_pass15_files(workroot)
                files.extend(cv15_files)
                if cv15_files:
                    warnings.append(
                        f"pass1.5: CV เห็น {n_cv15} จุด ({len(cv15_files)} ไฟล์) — "
                        f"เก็บไว้ให้ pass3 ใช้วัดระยะ")
            else:
                warnings.append(f"pass1.5 (cv_scan.py) {'/'.join(why) or 'ล้ม'} — ใช้ครอปจาก pass1 "
                                f"ต่อตามปกติ ครอปที่ CV ยังสแกนไม่ถึงจะไม่มี CV hint แนบ")
        except Exception as e:
            warnings.append(f"pass1.5 ล้ม ({type(e).__name__}: {e}) — ใช้ครอปจาก pass1 ต่อ ไม่มี CV hint")
    save_checkpoint(job_id, files, warnings, timings)

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
    grid_doc = None      # ตัวไฟล์ grid_master.json (ใน files[]) — ท้ายงานเขียน "validation" ลงไป
    # นับ gridline เป็นงานที่ 1 ถ้ามีจริง — เดิม total บวก 1 แต่ตัวนับวิ่งแค่ 1..len(tasks)
    # ทำให้แถบไม่มีวันถึง 100% เมื่อมีหน้ากริด (ไม่เคยเห็นเพราะงานทดสอบไม่มีหน้ากริด)
    grid_step = 1 if grid_pages else 0
    pass2_total = len(tasks) + grid_step
    if "grid_master.json" in prev_by_name:
        # resume — gridline ตอบสำเร็จไปแล้วรอบก่อน ไม่ยิงซ้ำ
        doc = grid_doc = prev_by_name["grid_master.json"]["json"]
        files.append(prev_by_name["grid_master.json"])
        grid = doc.get("grid")
        if isinstance(grid, dict):
            grid_master = grid
            slim = {"grid": {k: grid.get(k) for k in ("x_lines", "y_lines") if k in grid}}
            gm_text = ("\n\nGRID MASTER (resolved axes for this building)\n"
                       + json.dumps(slim, ensure_ascii=False))
        set_progress(job_id, "pass2", 0, pass2_total, "อ่านผังกริด (resume จาก checkpoint เดิม)",
                     warnings=len(warnings), **meta)
    elif grid_pages:
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
                grid_doc = doc
                grid = doc.get("grid")
                if isinstance(grid, dict):
                    grid_master = grid
                    slim = {"grid": {k: grid.get(k) for k in ("x_lines", "y_lines") if k in grid}}
                    gm_text = ("\n\nGRID MASTER (resolved axes for this building)\n"
                               + json.dumps(slim, ensure_ascii=False))
            save_checkpoint(job_id, files, warnings, timings)
    else:
        warnings.append("pass0 ไม่พบหน้าไหนติดธง gridline — plan_* ไม่มี GRID MASTER แนบ")

    # pass2 ราย (page, subtask)
    n_elements = 0
    plan_docs = []   # [(sub, page, doc)] — pass3 อ่านไปวัด (อ่านอย่างเดียว ห้ามแก้: dict ตัวเดียวกับ
                     # ใน files[] แก้ตรงนี้ = ผลที่ส่งกลับเว็บเปลี่ยนด้วย — D3 ห้าม pass3 แตะ)
    for i, (page, sub) in enumerate(tasks, 1):
        name = f"page_{page:02d}_{sub}"
        if f"{name}.json" in prev_by_name:
            # resume — หน้านี้ตอบสำเร็จไปแล้วรอบก่อน ไม่ยิงซ้ำ (เดาไม่ได้ว่ารอบใหม่จะตอบ
            # เหมือนเดิม ของเดิมที่สำเร็จแล้วดีกว่า)
            doc = prev_by_name[f"{name}.json"]["json"]
            files.append(prev_by_name[f"{name}.json"])
            if workroot and sub in PLAN_SUBTASKS:
                plan_docs.append((sub, page, doc))
            els = doc.get("elements")
            n_elements += len(els) if isinstance(els, list) else 0
            set_progress(job_id, "pass2", i + grid_step, pass2_total,
                         note=f"หน้า {page} · {SUBTASK_TH.get(sub, sub)} (resume)",
                         elements=n_elements, warnings=len(warnings), **meta)
            continue
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
        if doc is None:
            warnings.append(f"{name}: {raw or 'JSON เสีย'} — ข้ามหน้านี้ ไปหน้าถัดไปต่อ ไม่เดาค่า")
            files.append({"name": f"{name}.raw.txt", "json": {"raw_text": raw}})
        else:
            doc = sanitize_elements(doc)
            doc.setdefault("pattern", SUBTASK_PATTERN.get(sub, sub))
            if workroot and sub in PLAN_SUBTASKS:
                cvm_notes = []
                try:
                    doc = merge_cv_marks(doc, workroot, sub, page, notes=cvm_notes)
                except Exception as e:
                    # merge_cv_marks เป็นแค่การ "ผูกพิกัด CV" เพิ่ม (D3-adjacent) — แถวที่โมเดล
                    # ตอบมาแล้วต้องรอดแม้ผูกไม่สำเร็จ ไม่งั้นข้อมูลรูปที่แบบพัง (เจอจริง: element_type
                    # เป็น list/dict) จะฆ่าทั้ง run_house_extract กลางคัน แทนที่จะข้ามแค่การผูก cv_mark
                    warnings.append(f"{name}: merge_cv_marks ล้ม ({type(e).__name__}: {e}) — "
                                     f"ไม่ผูกพิกัด CV ให้หน้านี้ (ผลอ่านแบบยังใช้ได้)")
                warnings.extend(f"{name}: {m}" for m in cvm_notes)
                plan_docs.append((sub, page, doc))
            els = doc.get("elements")
            n_elements += len(els) if isinstance(els, list) else 0
            files.append({"name": f"{name}.json", "json": doc})
        set_progress(job_id, "pass2", i + grid_step, pass2_total,
                     note=f"หน้า {page} · {SUBTASK_TH.get(sub, sub)}",
                     elements=n_elements, warnings=len(warnings), **meta)
        # checkpoint ทุกหน้า — จุดนี้แหละที่ช้าที่สุด/พังบ่อยที่สุด อยากได้ resume ตรงนี้มากสุด
        timings["pass2_s"] = round(time.time() - t0, 1)
        save_checkpoint(job_id, files, warnings, timings)
    timings["pass2_s"] = round(time.time() - t0, 1)

    # pass2.5 — self-harvest sidecar, local CPU (จุดที่คลังกลางจับข้ามซีรีส์ไม่ติด)
    if workroot:
        try:
            why = []
            if run_cv_scan(workroot, pass25=True, notes=why):
                cv25_files, added = collect_pass25_files(workroot)
                files.extend(cv25_files)
                if cv25_files:
                    warnings.append(
                        f"pass2.5: self-harvest {len(cv25_files)} ไฟล์ (+{added} จุด)")
            else:
                warnings.append(f"pass2.5 (cv_scan.py) {'/'.join(why) or 'ล้ม'} — ข้าม ไม่กระทบผลหลัก")
        except Exception as e:
            warnings.append(f"pass2.5 ล้ม ({type(e).__name__}: {e}) — ข้าม ไม่กระทบผลหลัก")
    save_checkpoint(job_id, files, warnings, timings)

    # pass3 — วัดระยะจริง: หมุด (grid_ref ที่โมเดลอ่านได้ + พิกัด CV) → px ต่อเมตร · ต้องรันหลัง
    # pass2.5 เพราะกินจุด self-harvest ด้วย · **รายงานอย่างเดียว** (D3, 2026-09-26): ไม่แก้ doc ของ
    # pass2 เลย ผลอยู่ใน pass3_measure.json v2 + grid_master.json "validation" + warnings ระดับงาน
    reports = {}
    if workroot and plan_docs:
        t3 = time.time()
        if not isinstance(grid_master, dict):
            warnings.append("pass3 ข้าม: ไม่มี grid master (ไม่มีหน้ากริด หรือ gridline JSON เสีย)")
        else:
            set_progress(job_id, "pass3", 0, len(plan_docs), "วัดระยะเทียบผังกริด",
                         elements=n_elements, warnings=len(warnings), **meta)
            for sub, page, doc in plan_docs:
                try:
                    rep = measure_page(doc, grid_master, cv_scan_for_task(workroot, sub, page), sub)
                except Exception as e:
                    warnings.append(f"pass3 หน้า {page} ({sub}) ล้ม ({type(e).__name__}: {e})")
                    continue
                reports[f"page_{page:02d}_{sub}"] = rep
                set_progress(job_id, "pass3", len(reports), len(plan_docs),
                             note=f"หน้า {page} · {SUBTASK_TH.get(sub, sub)}",
                             elements=n_elements, warnings=len(warnings), **meta)
        timings["pass3_s"] = round(time.time() - t3, 1)
    elif not workroot and any(sub in PLAN_SUBTASKS for _, sub in tasks):
        warnings.append("pass3 ข้าม: pass1 (organize.py) ไม่สำเร็จ — ไม่มีครอป/ผล CV ให้วัด")

    # pass3 (เวกเตอร์) — ไม้บรรทัดจากเส้นกริดใน PDF · ไม่ต้องมีครอป/CV/หมุดจากโมเดล จึงรันได้แม้
    # pass1/1.5 ล้ม และได้หน้าแปลนคานด้วย (pass3 แบบหมุดทำไม่ได้โดยโครงสร้าง) · **รายงานอย่างเดียว**:
    # ไม่แก้ doc ของ pass2 ไม่แนบอะไรเข้า prompt
    vector_reports = {}
    if vectors and isinstance(grid_master, dict):
        t3v = time.time()
        plan_pages = sorted({doc["_page"] for doc in classified
                             if any(isinstance(v, dict) and str(v.get("subtask") or "").startswith("plan_")
                                    for v in doc.get("views") or [])})
        for page in plan_pages:
            if page in vectors:
                try:
                    vector_reports[f"page_{page:02d}"] = measure_page_vectors(vectors[page], grid_master)
                except Exception as e:   # โมดูลไม่ raise เอง (fuzz 3000 รอบ) — กันเผื่อ
                    warnings.append(f"ไม้บรรทัดเวกเตอร์ หน้า {page} ล้ม ({type(e).__name__}) — ข้าม")
        timings["pass3_vector_s"] = round(time.time() - t3v, 1)
    elif vectors:
        warnings.append("ไม้บรรทัดเวกเตอร์ข้าม: ไม่มี grid master")

    # C2: ตรวจ grid master (ชื่อเส้นซ้ำ/ปนแกน/อยู่สองแกน + ทิศ origin + scale ที่ pass3 เห็น) — เขียน
    # "validation" ลง grid_master.json ให้เว็บเตือนข้างผังกริด · เขียนทุกครั้งที่มี grid master แม้ pass3
    # ไม่ได้รัน (ปัญหาจากตัวไฟล์เองยังเห็นได้) · คำนวณใหม่ทุกรอบ (resume ทับของเก่าได้ไม่เสียอะไร)
    # rev_worker major: ขั้นนี้เป็น report-only ทั้งก้อน (ไม่แก้ elements/pass2) แต่ไม่มี try เลย —
    # อินพุตแปลกที่ยังหลุดผ่านด่าน isinstance ของ pass3_measure.py เอง (เช่น grid_master พังรูปที่
    # ยังไม่เคยเจอ) จะทำให้งานที่ยิงโมเดลครบทุกหน้าแล้วล่มตรงนี้ **หลังใช้ GPU ไปหมดแล้ว** —
    # ห่อทั้งก้อนไว้ ให้อย่างแย่ที่สุดคือไม่มี validation/pass3_measure.json แต่ผลอ่านแบบยังคืนได้
    if isinstance(grid_master, dict):
        try:
            validation = grid_validation(grid_master, reports)
            if vector_reports:
                validation = merge_validation(validation, vector_reports)
            if isinstance(grid_doc, dict):
                grid_doc["validation"] = validation
            if reports or vector_reports:
                p3 = pass3_file(reports, validation)
                if vector_reports:
                    # key แยกระดับบน ไม่ใส่ใน "pages" — เว็บ (pass3Stats) ถือทุกตัวใน pages เป็นรายงาน CV
                    p3["vector_pages"] = vector_reports
                files.append({"name": "pass3_measure.json", "json": p3})
            line = vector_summary_line(vector_reports)
            if line:
                warnings.append(line)
            warnings.extend(summary_warnings(reports, validation))
        except Exception as e:
            warnings.append(f"C2 (ตรวจ grid master) ล้ม ({type(e).__name__}: {e}) — ข้าม ไม่กระทบผลอ่านแบบ")

    # งานที่ยิงโมเดลไม่สำเร็จ "ทุกหน้า" ยังคืน files=[pass0.json] ออกไปตามปกติ แล้วผู้เรียก
    # ประทับ status=done ทับ — หน้าเว็บจึงขึ้น "งานถอดแบบล่าสุดเสร็จแล้ว" พร้อมปุ่มดึงผล
    # ที่ไม่มีอะไรให้ดึง (เจอจริง 23 ก.ย. 69 job c2f4f69a: การ์ดหลุดกลางทาง 3/3 หน้าล้ม
    # ConnectionError ทุกหน้า แต่สถานะเป็น done) — แย่กว่าขึ้น failed ตรงๆ เพราะคนเชื่อว่าได้ผลแล้ว
    #
    # ดักเฉพาะ "ไม่ได้อะไรกลับมาเลย" — ผลบางส่วน (บางหน้าล้ม บางหน้าผ่าน) ยังถือว่าใช้ได้
    # ตามเดิม เพราะสเปกจากหน้าที่ผ่านก็มีค่าในตัวมันเอง
    #
    # โยน exception ได้โดยไม่เสีย diagnostic เพราะ save_checkpoint() เขียน result ลง DB
    # ไประหว่างทางแล้ว — ทาง except ของผู้เรียกเขียนแค่ status/error_message ไม่ทับ result
    SIDECAR_PREFIXES = ("cv15_", "cv25_")
    usable = [f for f in files
              if f["name"].endswith(".json")
              and f["name"] not in ("pass0.json", "pass3_measure.json")
              and not f["name"].startswith(SIDECAR_PREFIXES)]
    if not usable:
        raise RuntimeError(
            "ยิงโมเดลไม่สำเร็จสักหน้าเดียว — ไม่ได้ผลอ่านแบบกลับมาเลย "
            f"(มีคำเตือน {len(warnings)} รายการบันทึกไว้แล้ว) "
            "มักเกิดจากการ์ดหลุดหรือโมเดลยังไม่พร้อม — เช็คด้วยเมนูข้อ 2 แล้วสั่งถอดแบบใหม่")

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
                notify.fail()
            except Exception as e2:
                print(f"งาน {job['id']} ล้มเหลว ({e}) และรายงานกลับไม่ได้ ({e2}) — "
                      f"ปล่อยค้าง processing ให้ requeue_stale เก็บไปทำใหม่", flush=True)
            continue
        # แยกออกมานอก try เดิม: ถ้าเขียน "done" ไม่สำเร็จ ห้ามตกไปทาง except แล้ว
        # ประทับว่า failed ทั้งที่ผลออกมาครบแล้ว (ทิ้งงาน 40 นาทีทิ้งเปล่า)
        try:
            update_job(job["id"], {"status": "done", "result": result})
            print(f"งาน {job['id']} เสร็จ")
            notify.done()
        except Exception as e:
            print(f"⚠️ งาน {job['id']} ทำเสร็จแล้วแต่เขียนผลกลับไม่ได้: {e}\n"
                  f"   งานจะค้างสถานะ processing → requeue_stale จะเก็บไปทำใหม่รอบหน้า",
                  flush=True)


if __name__ == "__main__":
    # ไม่ใช้ argparse — มีโหมดเดียวจริงๆ และเคยเจอปัญหาคัดลอกคำสั่งมาแล้ว argparse ตาย
    if "--release-stuck" in sys.argv:
        release_stuck_jobs()
    else:
        main()
