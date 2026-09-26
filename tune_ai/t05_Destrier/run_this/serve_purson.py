#!/usr/bin/env python3
"""serve_purson.py — เปิดโมเดล Purson เป็น HTTP endpoint แบบ OpenAI-compatible

⚠️ ทำไมไม่ใช้ vLLM (ตรวจจริง 2026-08-30 ก่อนเช่าการ์ด — กันเสียเงินฟรี):
adapter ของเรา (`Sicilian44/t03`) เก็บ LoRA ของ MoE expert เป็น
`...mlp.experts.lora_A.weight` shape **[4096, 2048]** = 256 experts × rank 16 แบนรวมกัน
ซึ่งเป็นรูปแบบของ Unsloth เอง **ไม่ตรงกับที่ vLLM รับทั้งสองแบบ**:
  - 3D fused ของ vLLM ต้องเป็น `experts.gate_up_proj.lora_A` / `experts.down_proj.lora_A`
  - 2D megatron ต้องเป็น `experts.0.gate_proj.lora_A` แยกรายตัว
ประกาศ `is_3d_lora_weight` ผิด vLLM **ไม่ error แต่ให้ผลขยะเงียบๆ** จึงเลี่ยงทั้งเส้นทาง
แล้วโหลดด้วย Unsloth ตรงๆ — โค้ดโหลด/generate ที่นี่ยกมาจาก `infer_house_t03.py`
ซึ่งรันจริงผ่านแล้ว 33 งานบนบ้าน 08 (เส้นทางที่พิสูจน์แล้ว ไม่ใช่เส้นทางที่หวังว่าจะได้)

รันบนเครื่องเช่า (presentation.py จัดการให้เอง):
    pip install unsloth xgrammar fastapi uvicorn pillow
    python serve_purson.py --adapter Sicilian44/t03 --port 8000
    python serve_purson.py --base                      # ไม่ใส่ adapter (เทียบ untuned)

worker.py คุยกับตัวนี้ด้วย /v1/chat/completions เหมือนคุยกับ vLLM ทุกประการ —
ถ้าวันหนึ่ง adapter ถูกแปลงเป็นรูปแบบที่ vLLM รับได้ ก็สลับกลับได้โดยไม่ต้องแก้ worker เลย
"""
import argparse
import base64
import gc
import io
import time

BASE_MODEL = "unsloth/Qwen3.6-35B-A3B"
# ต้องตรงกับตอนเทรนของ adapter ที่กำลังเสิร์ฟ — ไม่ตรงคือบั๊กคลาส t01/t04 (ภาพโดนย่อเงียบๆ)
# t03 = 7680 · destrier/Courser = 6912 (ลดหลัง OOM จริง 2026-08-31) → ส่งผ่าน --max-pixels
MAX_PIXELS = 7680 * 1024
MIN_PIXELS = 256 * 1024

# 2026-09-02: เจอสด — เพดานนี้เดิม 25 นาที ตรงกับ worker.py รุ่นเก่า แต่ worker.py ฝั่ง
# client ขยับเป็น 2700s (45 นาที) ไปแล้วเมื่อวาน โดยไม่ได้แก้ตัวนี้ที่เป็นเพดานจริงฝั่ง
# SERVER (ตัด generation กลางคันด้วย StoppingCriteria ไม่สนว่า JSON จะครบหรือไม่) — ผลคือ
# หน้าที่เนื้อหาเยอะ (ฐานราก/หมายเหตุ) โดนตัดที่ 1501s ซ้ำ 3 ครั้งในงานเดียว ทั้งที่ client
# รอได้ถึง 2700s แล้ว ต้องตั้งให้ต่ำกว่า client เสมอ (กันไม่ให้ client timeout ก่อน server
# ตอบ) แต่สูงพอให้หน้าที่เนื้อหาเยอะจริงๆ เขียน JSON ให้ครบวงเล็บ
PAGE_TIMEOUT_S = 40 * 60

_state = {}


def load(src, max_pixels=MAX_PIXELS):
    try:
        from unsloth import FastVisionModel as M
    except ImportError:
        from unsloth import FastModel as M
    model, tok = M.from_pretrained(src, load_in_4bit=False)
    ip = getattr(tok, "image_processor", None)
    if ip is not None:
        ip.size["longest_edge"] = max_pixels
        ip.size["shortest_edge"] = MIN_PIXELS
        print(f"image processor: max={ip.size['longest_edge']} px "
              f"(≈{ip.size['longest_edge'] // 1024} visual tokens/ภาพ)", flush=True)
    M.for_inference(model)
    return model, tok


GROUPED = "grouped_by_expert"


def adapter_b_layout(src):
    """layout ของ lora_B ที่ adapter นี้ต้องการ — คีย์ lora_B_layout ใน adapter_config
    ไม่มีคีย์ = เทรนด้วย Unsloth ก่อน 18 ก.ย. 2026 = grouped_by_expert · อ่านไม่ได้ = None"""
    import json
    import os
    try:
        if os.path.isdir(src):
            p = os.path.join(src, "adapter_config.json")
        else:
            from huggingface_hub import hf_hub_download
            p = hf_hub_download(src, "adapter_config.json")
        return json.load(open(p, encoding="utf-8")).get("lora_B_layout") or GROUPED
    except Exception:
        return None


def has_layout_key(src):
    """adapter ประกาศ lora_B_layout เองไหม (ตัวที่ซ่อม/soup รุ่นใหม่ประกาศ · destrier e229403 ไม่ประกาศ)"""
    import json
    import os
    try:
        if os.path.isdir(src):
            p = os.path.join(src, "adapter_config.json")
        else:
            from huggingface_hub import hf_hub_download
            p = hf_hub_download(src, "adapter_config.json")
        return "lora_B_layout" in json.load(open(p, encoding="utf-8"))
    except Exception:
        return False


def print_versions():
    """เวอร์ชันที่ใช้เสิร์ฟจริง — เดิมไม่มีบันทึกเลย ย้อนดูไม่ได้ว่ารอบไหนใช้ Unsloth รุ่นไหน
    (สำคัญ: วิธีอ่าน LoRA ของ expert เปลี่ยนตามรุ่น unsloth_zoo)"""
    import os
    from importlib import metadata
    vs = []
    for pkg in ("unsloth", "unsloth_zoo", "peft", "transformers", "torch"):
        try:
            vs.append(f"{pkg} {metadata.version(pkg)}")
        except Exception:
            vs.append(f"{pkg} ?")
    print("เวอร์ชัน: " + " · ".join(vs), flush=True)
    print(f"UNSLOTH_MOE_LORA_B_LAYOUT={os.environ.get('UNSLOTH_MOE_LORA_B_LAYOUT', '<ไม่ได้ตั้ง>')}",
          flush=True)


def check_expert_lora(model, tok, src):
    """LoRA ของ MoE expert ถูกอ่านแบบที่ adapter ต้องการจริงไหม — คืนเหตุผลถ้า "ผิดแน่" ไม่งั้น None

    ทำไมต้องมี (พบ 2026-09-27, หลักฐานใน Training/tune_ai/t05_Destrier/proof/03_…):
    lora_B ของ expert อ่านได้สองแบบที่รูปร่างเท่ากันเป๊ะ อ่านผิดแบบ = expert ได้ชิ้นส่วนของ
    expert ตัวอื่น ตอบเป็น JSON สวยงามแต่เนื้อเพี้ยน ไม่มี error สักตัว · และต่อให้ตั้ง env
    UNSLOTH_MOE_LORA_B_LAYOUT ถูก ถ้าตัวแปะของ Unsloth ติดตั้งไม่สำเร็จ (มันกลืน error เงียบ)
    LoRA จะตกไปทางของ PEFT ซึ่งอ่านแบบ rank_major เสมอ — ต้องถาม Unsloth หลังรันจริงหนึ่งครั้ง

    ตรวจไม่ได้ (API เปลี่ยน/ไม่มี expert LoRA) = เตือนแล้วไปต่อ · ผิดแน่ = คืนเหตุผล
    ผู้เรียกไม่ปิดเซิร์ฟเวอร์ (presentation.py จะตีว่าเครื่องเสีย คืนการ์ดดีทิ้ง + ขึ้นบัญชีดำ)
    แต่ปฏิเสธทุกคำขอพร้อมเหตุผลนี้แทน — ไม่มีผลขยะหลุดไปถึงผู้ใช้"""
    import os
    import torch
    try:
        from peft.tuners.lora.layer import ParamWrapper
    except Exception as e:
        print(f"⚠️ ตรวจ LoRA ของ expert ไม่ได้ (import peft: {e}) — ไปต่อแบบไม่ยืนยัน", flush=True)
        return None
    wrappers = [(n, m) for n, m in model.named_modules()
                if isinstance(m, ParamWrapper) and int(getattr(m, "num_experts", 1) or 1) > 1]
    if not wrappers:
        print("ไม่มี LoRA ของ MoE expert (เสิร์ฟ base หรือ adapter ไม่แตะ expert) — ข้ามการตรวจ layout",
              flush=True)
        return None
    want = adapter_b_layout(src)
    env = os.environ.get("UNSLOTH_MOE_LORA_B_LAYOUT", "<ไม่ได้ตั้ง = rank_major>")
    print(f"LoRA ของ expert {len(wrappers)} ตัว · adapter ต้องการ {want or '?'} · env {env}", flush=True)
    try:
        from unsloth_zoo.temporary_patches import moe_utils as mu
        layout_for = mu.moe_lora_b_layout_for_wrapper
        applies_stash = mu._wrapper_forward_applies_stash
    except Exception as e:
        print(f"⚠️ unsloth_zoo รุ่นนี้ไม่มีฟังก์ชันที่ใช้ตรวจ ({type(e).__name__}) — ไปต่อแบบไม่ยืนยัน"
              f" · ก่อนเชื่อผล ยิงหน้าที่รู้คำตอบเทียบด้วยตาหนึ่งหน้า", flush=True)
        return None
    try:
        # วัดได้หลังมี forward จริงหนึ่งครั้ง — Unsloth ตัดสินว่าจะใช้ทางของตัวเองหรือยกให้ PEFT ตอนนั้น
        warm = tok(None, "ok", add_special_tokens=False, return_tensors="pt").to("cuda")
        with torch.no_grad():
            model.generate(**warm, max_new_tokens=1, do_sample=False)
        bad, unmeasured = [], 0
        for name, w in wrappers:
            lay, st = layout_for(w), applies_stash(w)
            if lay != want or st is False:
                bad.append(f"{name.split('language_model.')[-1]}: อ่านแบบ {lay} · ทาง Unsloth={st}")
            elif st is None:     # Unsloth ยังไม่ได้วัด ≠ ผิด — ปฏิเสธทุกคำขอเพราะเดา = พังวันสาธิต
                unmeasured += 1
    except Exception as e:
        print(f"⚠️ ตรวจ LoRA ของ expert ไม่สำเร็จ ({type(e).__name__}: {e}) — ไปต่อแบบไม่ยืนยัน",
              flush=True)
        return None
    if want is None:
        print("⚠️ อ่าน adapter_config ไม่ได้ — ไม่รู้ว่า adapter ต้องการแบบไหน ไปต่อแบบไม่ยืนยัน", flush=True)
        return None
    if bad:
        return (f"LoRA ของ MoE expert ถูกอ่านผิดแบบ ({len(bad)}/{len(wrappers)} ตัว) — ผลจะเพี้ยนเงียบๆ "
                f"จึงไม่ตอบ · adapter ต้องการ {want} · env={env} · ตัวอย่าง: {bad[0]} · "
                f"แก้: ตั้ง UNSLOTH_MOE_LORA_B_LAYOUT={want} ก่อนเปิด และเช็คว่า Unsloth แปะ MoE forward ได้")
    if unmeasured:
        print(f"⚠️ LoRA ของ expert อ่านแบบ {want} แต่ Unsloth ยังไม่ได้วัดว่าใช้ทางของตัวเอง "
              f"{unmeasured}/{len(wrappers)} ตัว — ไปต่อแบบไม่ยืนยัน · ยิงหน้าที่รู้คำตอบเทียบด้วยตาก่อนเชื่อผล",
              flush=True)
        return None
    print(f"✅ LoRA ของ expert ทั้ง {len(wrappers)} ตัว อ่านแบบ {want} ผ่านทางของ Unsloth", flush=True)
    return None


def build_grammar(model, tok):
    """xgrammar builtin JSON — คืน factory (LogitsProcessor มี state ต้องสร้างใหม่ทุกครั้ง)
    ใช้ไม่ได้ก็รันต่อแบบไม่ constrain ดีกว่าล้มทั้งเซิร์ฟเวอร์"""
    try:
        import xgrammar as xgr
        cfg = model.config
        vocab = getattr(cfg, "vocab_size", None) or cfg.text_config.vocab_size
        info = xgr.TokenizerInfo.from_huggingface(tok.tokenizer, vocab_size=vocab)
        compiled = xgr.GrammarCompiler(info).compile_builtin_json_grammar()
        print("grammar: xgrammar (builtin JSON) พร้อม", flush=True)
        return lambda: [xgr.contrib.hf.LogitsProcessor(compiled)]
    except Exception as e:
        print(f"⚠️ xgrammar ใช้ไม่ได้ ({e}) — จะตอบแบบไม่ constrain", flush=True)
        return None


class _Deadline:
    def __init__(self, t):
        self.t = t

    def __call__(self, input_ids, scores, **kw):
        return time.time() > self.t


def generate(images, prompt, max_new_tokens, use_grammar):
    import torch
    from transformers import StoppingCriteriaList
    model, tok, grammar = _state["model"], _state["tok"], _state["grammar"]

    parts = [{"type": "image", "image": im} for im in images]
    parts.append({"type": "text", "text": prompt})
    # enable_thinking=False จำเป็น ไม่งั้นโมเดลเขียน CoT จนหมด budget ก่อนถึง JSON [t01]
    text = tok.apply_chat_template([{"role": "user", "content": parts}],
                                   add_generation_prompt=True, enable_thinking=False)
    # images=[] ทำให้ processor ของ vision model ทำ images[0] แล้ว IndexError —
    # ส่ง None แทนเมื่อไม่มีภาพ (เคสข้อความล้วน เช่น smoke test)
    inputs = tok(images or None, text, add_special_tokens=False,
                 return_tensors="pt").to("cuda")
    # 2026-08-31 op04: เลิก greedy + ถอด rep_penalty/no_repeat_ngram — Qwen ประกาศเองว่า
    # greedy ทำให้ endless repetition (เจอจริง: หลุดโซ่คำพ้อง→ภาษาจีน 18 นาทีเต็ม token)
    # และ rep_penalty พังเนื้อหาซ้ำโดยธรรมชาติ (grid refs/ตาราง) — ใช้ค่าแนะนำ non-thinking
    # ของ Qwen: temperature=0.7, top_p=0.8, top_k=20 (presence_penalty ไม่มีใน HF generate)
    kw = dict(max_new_tokens=max_new_tokens, do_sample=True,
              temperature=0.7, top_p=0.8, top_k=20,
              stopping_criteria=StoppingCriteriaList([_Deadline(time.time() + PAGE_TIMEOUT_S)]))
    if use_grammar and grammar is not None:
        kw["logits_processor"] = grammar()
    out = model.generate(**inputs, **kw)
    gen_len = out.shape[1] - inputs["input_ids"].shape[1]
    # ⚠️ ต้องรู้ให้ได้ว่า "จบเพราะโมเดลเขียนครบ" หรือ "จบเพราะเราตัดเอง" — สองอย่างนี้
    # ต่างกันคนละเรื่อง แต่เดิมตอบ finish_reason="stop" ตายตัวทั้งคู่ ฝั่ง worker จึงแยกไม่ออก
    # พอ JSON ขาดครึ่งเพราะโดนตัด มันก็แค่ทิ้งหน้านั้นเงียบๆ เหมือนหน้าที่โมเดลตอบมั่ว
    # (เจอจริง 23 ก.ย.: หน้า S-01 เขียน 15,910 ตัวอักษรใน 1,411 วินาที = ชนเพดาน 6000 token พอดี)
    truncated = gen_len >= max_new_tokens
    pred = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    del inputs, out
    gc.collect()
    torch.cuda.empty_cache()
    return pred, truncated


def make_app():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from PIL import Image
    app = FastAPI()

    @app.get("/v1/models")
    def models():
        return {"object": "list",
                "data": [{"id": _state["name"], "object": "model", "owned_by": "purson"}]}

    @app.post("/v1/chat/completions")
    async def chat(req: Request):
        body = await req.json()
        content = body["messages"][-1]["content"]
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        images, texts = [], []
        for c in content:
            if c.get("type") == "image_url":
                url = c["image_url"]["url"]
                raw = base64.b64decode(url.split(",", 1)[1] if url.startswith("data:") else url)
                images.append(Image.open(io.BytesIO(raw)).convert("RGB"))
            elif c.get("type") == "text":
                texts.append(c["text"])

        if _state.get("refuse"):
            # ตั้งตอนเปิดเครื่องเมื่อ LoRA ของ expert ถูกอ่านผิดแบบ — ตอบ error ดีกว่าตอบขยะเนียนๆ
            return JSONResponse(status_code=500, content={"error": {"message": _state["refuse"]}})
        want_json = (body.get("response_format") or {}).get("type") == "json_object"
        t0 = time.time()
        try:
            text, truncated = generate(images, "\n".join(texts),
                                       body.get("max_tokens", 6000), want_json)
            err = None
        except Exception as e:      # OOM ฯลฯ — ตอบ error ให้ worker บันทึก อย่าล้มเซิร์ฟเวอร์
            text, truncated, err = "", False, f"{type(e).__name__}: {e}"
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] {len(images)} ภาพ · "
              f"{'grammar' if want_json else 'ไม่ constrain'} · {dt:.0f}s"
              + (f" · ERROR {err}" if err else f" · {len(text)} ตัวอักษร"
                 + (" · ⚠️ โดนตัดเพราะชนเพดาน token" if truncated else "")), flush=True)
        if err:
            # ต้องใช้ JSONResponse — `return dict, 500` FastAPI ตีเป็น list ธรรมดา
            # ทำให้ฝั่ง client เห็น [body, 500] แทน HTTP 500 (เจอจริง 2026-08-31)
            return JSONResponse(status_code=500, content={"error": {"message": err}})
        return {
            "id": f"purson-{int(t0)}", "object": "chat.completion",
            "model": _state["name"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "length" if truncated else "stop"}],
        }

    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="Sicilian44/t03",
                    help="repo/โฟลเดอร์ของ adapter (ค่าเริ่มต้น = t03 บน HF)")
    ap.add_argument("--base", action="store_true", help="ไม่ใส่ adapter (เทียบ untuned)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--name", default="purson", help="ชื่อโมเดลที่ตอบใน /v1/models")
    ap.add_argument("--max-pixels", type=int, default=MAX_PIXELS,
                    help="ต้องตรงกับตอนเทรนของ adapter นั้น (t03 7864320 · destrier 7077888)")
    a = ap.parse_args()

    src = BASE_MODEL if a.base else a.adapter
    print(f"โหลดโมเดล: {src} (ครั้งแรกต้องดาวน์โหลด ~70GB ใช้เวลา 15-45 นาที)", flush=True)
    # เน็ตสะดุดทีเดียวตอนโหลด 72 GB ไม่ควรฆ่าการเช่าเครื่องทั้งรอบ — HuggingFace แคชไฟล์ที่
    # โหลดจบแล้วไว้ ลองใหม่จึงเริ่มต่อจากของเดิม ไม่ได้เริ่มศูนย์
    # (23 ก.ย. 69: Xet พังที่ 9.1/72 GB แล้ว process ตายทันที เสียเวลาไป ~20 นาที)
    for attempt in range(1, 4):
        try:
            model, tok = load(src, a.max_pixels)
            break
        except Exception as e:
            if attempt == 3:
                print(f"❌ โหลดโมเดลไม่สำเร็จครบ 3 ครั้ง — ยอมแพ้: {type(e).__name__}: {e}",
                      flush=True)
                raise
            print(f"⚠️ โหลดโมเดลล้มครั้งที่ {attempt}/3 ({type(e).__name__}: {e})"
                  f" — รอ 20 วิแล้วลองต่อจากไฟล์ที่โหลดไว้แล้ว", flush=True)
            time.sleep(20)
    print_versions()
    refuse = None if a.base else check_expert_lora(model, tok, src)
    if refuse:
        print("\n" + "!" * 72 + f"\n⛔ {refuse}\n   เซิร์ฟเวอร์เปิดไว้ แต่ทุกคำขอจะได้ error นี้แทนคำตอบ\n"
              + "!" * 72 + "\n", flush=True)
    if (not a.base and src.rstrip("/") == "dacarokann/destrier"
            and adapter_b_layout(src) == GROUPED and not has_layout_key(src)):
        print("⚠️ dacarokann/destrier ตัวนี้ (rev e229403) คือตัวที่ LoRA ของ expert ปนผิด (ยืนยัน 27 ก.ย.)"
              " — ใช้เพื่อเทียบเท่านั้น ตัวที่ซ่อมแล้วสร้างด้วย Training/tune_ai/fix_destrier_layout.py",
              flush=True)
    _state.update(model=model, tok=tok, grammar=build_grammar(model, tok), refuse=refuse,
                  name=a.name if not a.base else f"{a.name}-base")
    print(f"✅ พร้อมรับงานที่ port {a.port} — worker ยิงมาที่ /v1/chat/completions ได้เลย",
          flush=True)

    import uvicorn
    uvicorn.run(make_app(), host="0.0.0.0", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
