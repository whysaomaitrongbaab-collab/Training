#!/usr/bin/env python3
"""Destrier Lab Playground - FastAPI Server.

Provides interactive REST endpoints for testing each pass of the drawing extraction pipeline:
- Endpoint health & model ping (vLLM / SGLang / DashScope)
- House & blueprint page browsing
- Prompt assembly & optimization lab
- Defensive JSON salvage & element sanitization
- Contract validation against finetune_output_contract
- Step-by-step pipeline execution
"""
import base64
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
PROMPTS_DIR = REPO_ROOT / "tune_ai" / "t05_Destrier" / "prompts"
if not PROMPTS_DIR.exists():
    PROMPTS_DIR = REPO_ROOT / "tune_ai" / "t04_Purson" / "prompts"
IMAGE_DIR = REPO_ROOT / "image"
STATIC_DIR = HERE / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Destrier Lab Playground",
    description="Interactive white-box testbed for blueprint extraction AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Defensive Parsing & JSON Salvage ─────────────────────────────────────────

def strip_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    t = m.group(1).strip() if m else t
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    t = re.sub(r"(\d)\.(?=[,}\]\s])", r"\1.0", t)
    return t


def salvage_truncated_json(text: str):
    """Recovers truncated JSON by cutting back to the last complete element in the array."""
    try:
        return json.loads(text), False
    except Exception:
        pass
    stack = []
    in_str = False
    esc = False
    cut = -1
    cut_stack = None

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
            if len(stack) >= 2 and stack[-1] == "[":
                cut, cut_stack = i, list(stack)

    if cut < 0 or not cut_stack:
        return None, False

    closing = "".join("}" if b == "{" else "]" for b in reversed(cut_stack))
    try:
        return json.loads(text[: cut + 1] + closing), True
    except Exception:
        return None, False


_NEG_DIM_KEYS = re.compile(r"(width|height|thickness|depth|dia|spacing|length|cover)_(mm|m|cm)$")
_GARBAGE_KEY = re.compile(r"[:,]")


def _element_is_garbage(el: Any) -> bool:
    if not isinstance(el, dict):
        return True
    for k, v in el.items():
        if _GARBAGE_KEY.search(str(k)):
            return True
        if _NEG_DIM_KEYS.search(str(k)) and isinstance(v, (int, float)) and v < 0:
            return True
        if isinstance(v, dict) and _element_is_garbage(v):
            return True
    return False


def sanitize_elements(doc: Dict[str, Any]) -> Dict[str, Any]:
    els = doc.get("elements")
    if not isinstance(els, list):
        return doc
    kept = [e for e in els if not _element_is_garbage(e)]
    dropped = len(els) - len(kept)
    if dropped:
        doc["elements"] = kept
        doc.setdefault("warnings", []).append(
            f"sanitize_elements: dropped {dropped}/{len(els)} garbage elements"
        )
    return doc


# ── Prompt Loading & Assembly ────────────────────────────────────────────────

def load_common_block() -> str:
    f = PROMPTS_DIR / "_common.md"
    if not f.exists():
        return ""
    txt = f.read_text(encoding="utf-8")
    m = re.search(r"## BLOCK START\n(.*?)\n## BLOCK END", txt, re.DOTALL)
    body = m.group(1).strip() if m else txt.strip()
    g = re.search(r"<!-- GLOSSARY START -->\n(.*?)\n<!-- GLOSSARY END -->\n", body, re.DOTALL)
    return body.replace(g.group(0), "").strip() if g else body


def load_prompt_file(path: Path) -> str:
    if not path.exists():
        return ""
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)(?:\n## PROMPT END|\Z)", txt, re.DOTALL)
    return m.group(1).strip() if m else txt.strip()


def get_subtask_prompt(subtask: str) -> Optional[str]:
    if subtask == "pass0":
        p = PROMPTS_DIR / "pass0" / "prompt.md"
        return load_prompt_file(p) if p.exists() else None
    p = PROMPTS_DIR / "pass2" / subtask / f"prompt_{subtask}.md"
    if not p.exists():
        return None
    return load_prompt_file(p)


TRAINED_SUBTASKS = [
    "gridline", "plan_footing", "plan_beam", "plan_slab",
    "section", "schedule", "notes"
]


# ── API Models ───────────────────────────────────────────────────────────────

class PromptAssembleRequest(BaseModel):
    subtask: str
    custom_body: Optional[str] = None
    include_common: bool = True
    grid_master_text: Optional[str] = None
    cv_hint_text: Optional[str] = None


class SalvageRequest(BaseModel):
    raw_text: str


class ContractValidateRequest(BaseModel):
    doc: Dict[str, Any]


class EndpointTestRequest(BaseModel):
    url: str
    api_key: Optional[str] = None
    model: Optional[str] = None


class AICallRequest(BaseModel):
    endpoint_url: str
    api_key: Optional[str] = None
    model: str = "purson"
    prompt: str
    image_paths: List[str]
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    repetition_penalty: float = 1.15
    max_tokens: int = 6000
    enable_thinking: bool = False


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "prompts_dir": str(PROMPTS_DIR),
        "image_dir": str(IMAGE_DIR),
        "prompts_loaded": PROMPTS_DIR.exists(),
    }


@app.get("/api/houses")
def list_houses():
    houses = []
    if IMAGE_DIR.exists():
        for d in sorted(IMAGE_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                png_count = len(list(d.glob("*.png")))
                houses.append({
                    "id": d.name,
                    "name": d.name,
                    "page_count": png_count
                })
    return {"houses": houses}


@app.get("/api/houses/{house_id}/pages")
def list_house_pages(house_id: str):
    hdir = IMAGE_DIR / house_id
    if not hdir.exists() or not hdir.is_dir():
        raise HTTPException(status_code=404, detail="House not found")
    pages = []
    for f in sorted(hdir.glob("*.png")):
        pages.append({
            "filename": f.name,
            "path": f"image/{house_id}/{f.name}",
            "size_bytes": f.stat().st_size
        })
    return {"house": house_id, "pages": pages}


@app.get("/api/image/{subpath:path}")
def get_image(subpath: str):
    f = REPO_ROOT / subpath
    if not f.exists() or not f.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(f))


@app.get("/api/prompts")
def list_prompts():
    subtasks = {}
    common = load_common_block()
    pass0 = get_subtask_prompt("pass0")
    if pass0:
        subtasks["pass0"] = {"name": "Pass 0 (Page Classifier)", "body": pass0}

    for sub in TRAINED_SUBTASKS:
        body = get_subtask_prompt(sub)
        if body:
            subtasks[sub] = {"name": sub, "body": body}

    return {
        "common_block": common,
        "subtasks": subtasks,
        "trained_subtasks": TRAINED_SUBTASKS,
    }


@app.post("/api/prompt/assemble")
def assemble_prompt(req: PromptAssembleRequest):
    parts = []
    if req.include_common and req.subtask != "pass0":
        c = load_common_block()
        if c:
            parts.append(c)

    body = req.custom_body
    if not body:
        body = get_subtask_prompt(req.subtask) or ""
    if body:
        parts.append(body)

    if req.grid_master_text:
        parts.append(req.grid_master_text)

    if req.cv_hint_text:
        parts.append(req.cv_hint_text)

    return {"prompt": "\n\n".join(parts)}


@app.post("/api/defensive/salvage")
def test_salvage(req: SalvageRequest):
    stripped = strip_fence(req.raw_text)
    salvaged, was_repaired = salvage_truncated_json(stripped)
    if salvaged is not None:
        sanitized = sanitize_elements(salvaged)
        return {
            "salvaged": True,
            "was_repaired": was_repaired,
            "parsed": sanitized,
            "warnings": sanitized.get("warnings", []),
        }
    return {
        "salvaged": False,
        "was_repaired": False,
        "parsed": None,
        "error": "Failed to parse or salvage JSON"
    }


@app.post("/api/contract/validate")
def validate_contract(req: ContractValidateRequest):
    doc = req.doc
    warnings = []
    missing_fields = []

    pattern = doc.get("pattern")
    elements = doc.get("elements")

    if not isinstance(elements, list):
        return {
            "valid": False,
            "warnings": ["doc missing 'elements' list"],
            "missing_fields": ["elements"],
            "element_count": 0
        }

    for idx, el in enumerate(elements):
        if not isinstance(el, dict):
            warnings.append(f"Element [{idx}] is not an object")
            continue
        el_id = el.get("element_id") or el.get("id")
        el_type = el.get("element_type")
        if not el_id:
            missing_fields.append(f"elements[{idx}].element_id")
            warnings.append(f"Element [{idx}] missing element_id")
        if not el_type and pattern not in ("notes", "grid_master"):
            missing_fields.append(f"elements[{idx}].element_type")
            warnings.append(f"Element [{idx}] missing element_type")

        if pattern == "beam_plan" or (el_type == "beam" and "grid_ref_start" in el):
            if "grid_ref_start" not in el or "grid_ref_end" not in el:
                warnings.append(f"Beam {el_id or idx} missing grid_ref_start or grid_ref_end")

    is_valid = len(missing_fields) == 0 and len(warnings) == 0
    return {
        "valid": is_valid,
        "warnings": warnings,
        "missing_fields": missing_fields,
        "element_count": len(elements)
    }


@app.post("/api/endpoint/test")
def test_endpoint(req: EndpointTestRequest):
    t0 = time.time()
    url = req.url.rstrip("/")
    if not url.endswith("/v1"):
        url_models = f"{url}/v1/models"
    else:
        url_models = f"{url}/models"

    headers = {"Content-Type": "application/json"}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"

    try:
        r = requests.get(url_models, headers=headers, timeout=10)
        latency_ms = round((time.time() - t0) * 1000, 1)
        if r.status_code == 200:
            models_data = r.json()
            model_list = [m.get("id") for m in models_data.get("data", [])]
            return {
                "ok": True,
                "latency_ms": latency_ms,
                "models": model_list,
                "selected_model": req.model or (model_list[0] if model_list else "unknown")
            }
        return {
            "ok": False,
            "status_code": r.status_code,
            "latency_ms": latency_ms,
            "error": r.text
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "latency_ms": round((time.time() - t0) * 1000, 1)
        }


@app.post("/api/ai/call")
def run_ai_call(req: AICallRequest):
    t0 = time.time()
    content = []

    for p in req.image_paths:
        fpath = REPO_ROOT / p
        if not fpath.exists():
            raise HTTPException(status_code=404, detail=f"Image not found: {p}")
        b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })

    content.append({"type": "text", "text": req.prompt})

    url = req.endpoint_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        if url.endswith("/v1"):
            url = f"{url}/chat/completions"
        else:
            url = f"{url}/v1/chat/completions"

    headers = {"Content-Type": "application/json"}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"

    payload = {
        "model": req.model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "top_k": req.top_k,
        "repetition_penalty": req.repetition_penalty,
        "response_format": {"type": "json_object"},
        "chat_template_kwargs": {"enable_thinking": req.enable_thinking},
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=600)
        elapsed_s = round(time.time() - t0, 2)
        r.raise_for_status()
        res = r.json()
        choice = (res.get("choices") or [{}])[0]
        raw_text = (choice.get("message") or {}).get("content") or ""
        finish_reason = choice.get("finish_reason")
        usage = res.get("usage") or {}

        # Salvage and parse
        stripped = strip_fence(raw_text)
        salvaged, was_repaired = salvage_truncated_json(stripped)
        parsed_doc = None
        if salvaged is not None:
            parsed_doc = sanitize_elements(salvaged)

        return {
            "success": True,
            "elapsed_s": elapsed_s,
            "finish_reason": finish_reason,
            "usage": usage,
            "raw_text": raw_text,
            "parsed": parsed_doc,
            "was_repaired": was_repaired,
            "tokens_per_sec": round(usage.get("completion_tokens", 0) / max(0.1, elapsed_s), 1)
        }
    except Exception as e:
        return {
            "success": False,
            "elapsed_s": round(time.time() - t0, 2),
            "error": str(e)
        }


# Mount static web assets
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8888"))
    print(f"Starting Destrier Lab Playground on http://localhost:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
