#!/usr/bin/env python3
"""
run_house_batch_t01.py — รัน t01 (Sicilian44/qwen36-thai-rc, LoRA บน unsloth/Qwen3.6-35B-A3B)
บน GPU เช่า ผ่าน transformers/PEFT (ไม่ใช่ GGUF — ตัดสินใจ 2026-08-24: รอบนี้เช่า GPU ใช้ตัว
not-gguf แทน local llama-server GGUF Q4_K_M ที่ทำไปก่อนหน้า เพื่อเลี่ยง quantization loss)

โหลด base+adapter ด้วยพารามิเตอร์ตรงกับตอนเทรน/eval จริง (MAX_PIXELS/MIN_PIXELS,
enable_thinking=False, max_new_tokens=3000, do_sample=False — คัดลอกมาจาก
eval_fields.py/train_qwen36.py ตรงๆ ห้ามเปลี่ยน ไม่งั้นผลไม่ตรงกับตัวเลขที่วัดไว้แล้ว
(JSON valid 90%, element recall 28.2%)). ไม่ใส่ repetition_penalty/no_repeat_ngram_size หรือ
grammar-constrained decoding แบบ t02 — สองอย่างนั้นเป็นของที่ t02 เพิ่มหลังเจอบั๊ก looping ของ
ตัวมันเอง ไม่เคยพิสูจน์กับโมเดล/ชุดข้อมูลของ t01 เลย

Two phase (สคริปต์เดียว, --phase เลือก):
  classify — จัดหมวด pattern ทุกหน้า (ใช้ variant tuned เสมอ ไม่ต้องรันซ้ำ 2 รอบเพราะการจัด
             หมวดหน้าไม่ขึ้นกับว่าโมเดลไหนจะมาอ่านต่อ) → เซฟ _classify.json ต่อบ้าน
  extract  — extract เต็มเฉพาะหน้าที่ pattern อยู่ใน KEEP_PATTERNS (t03 Pass 2) --variant
             เลือก tuned (adapter) หรือ base (Qwen3.6-35B-A3B เพียวๆ ไม่มี adapter)

resume-safe ทั้งสอง phase — ข้ามไฟล์ผลลัพธ์ที่มีอยู่แล้ว รันซ้ำได้ไม่เสียเงินที่ทำไปแล้ว
(บทเรียนจาก DAY OF SHAME)

    # classify ก่อนเสมอ (ใช้ร่วมกันทั้ง 2 variant ไม่ต้องรันซ้ำ)
    python3 run_house_batch_t01.py --phase classify --images-root /workspace/tune/image \
        --out-root /workspace/tune/ผล --houses 11 --limit 5   # ทดสอบสั้นก่อนเสมอ

    python3 run_house_batch_t01.py --phase classify --images-root /workspace/tune/image \
        --out-root /workspace/tune/ผล --houses 11

    python3 run_house_batch_t01.py --phase extract --variant tuned \
        --images-root /workspace/tune/image --out-root /workspace/tune/ผล --houses 11
    python3 run_house_batch_t01.py --phase extract --variant base \
        --images-root /workspace/tune/image --out-root /workspace/tune/ผล --houses 11

# scope 2026-08-24: บ้าน 11 (บ้าน_เล็ก_1ชั้น_06, 137 หน้า) เดียว — เปลี่ยนจาก 08/09/10 เดิม
# (มะขามสั่ง) HOUSES ยังเก็บ 08/09/10 ไว้เผื่อใช้ทีหลัง ไม่ได้ลบทิ้ง
"""
import argparse
import gc
import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).parent

HOUSES = {
    "08": "บ้าน_เล็ก_1ชั้น_03",
    "09": "บ้าน_เล็ก_1ชั้น_04",
    "10": "บ้าน_เล็ก_1ชั้น_05",
    "11": "บ้าน_เล็ก_1ชั้น_06",
}

BASE_MODEL = "unsloth/Qwen3.6-35B-A3B"
ADAPTER_REPO = "Sicilian44/qwen36-thai-rc"
ADAPTER_SUBFOLDER = "lora-adapter"
# ต้องตรงกับตอนเทรน (train_qwen36.py) เป๊ะ — ดู eval_fields.py comment เดียวกัน
MAX_PIXELS = 5120 * 1024
MIN_PIXELS = 256 * 1024

# t03 Pass 2 (tune_ai/t03/pass_design.csv, README.md) — 7 pattern ที่ Constistant อ่านจริง
# material_list ตัดออกจาก default ตาม op04/dataset_sizing.md (2026-08-21): 37% ของงาน annotate
# ทั้งหมดแต่ให้ elements=0 เสมอ (เป็นตาราง BOQ ไม่ใช่ตำแหน่งโครงสร้าง) — ยังอยู่ใน pass_design.csv
# ว่าเป็น Pass2 แต่ไม่คุ้มเวลา extract วันนี้
KEEP_PATTERNS = {"gridline", "plan", "section", "schedule", "notes", "soil_boring_log"}

# บ้าน 11 มีของจริงจาก json_แก้ไขแล้ว/11บ้าน_เล็ก_1ชั้น_06/ (86 ไฟล์ ครอบหน้า 00-66 เท่านั้น —
# หน้า 67-137 ไม่เคยถูกแตะเลยทั้งใน raw และ json_แก้ไขแล้ว ไม่มีข้อมูล pattern) ใช้คัด PAGE_FILTER
# ตรงจากของจริงแทนการ classify ด้วยโมเดล (ประหยัดเวลา/เงินเช่าเต็มๆ) — ตรวจ pattern field จริง
# ทีละไฟล์แล้ว (ไม่ได้เดาจากชื่อไฟล์), แก้บั๊กที่ t03/README.md บันทึกไว้ 1 จุด: หน้า24
# "roof_frame_plan" ถูกแปะ pattern=roof_plan (ควรเป็น plan — โครงหลังคาเป็นโครงสร้างจริง) รวมไว้
# ในกลุ่ม plan ตามที่ควรจะเป็น ไม่ใช่ตามป้ายเดิมที่ผิด — หน้า00 (gridline) เป็นไฟล์สังเคราะห์
# (ไม่มีภาพจริง source_pages = หน้า20/21/22 ซึ่งอยู่ในกลุ่ม plan อยู่แล้ว) ไม่ต้องเพิ่มแยก
#
# 2026-08-24: มะขามสั่งตัด pattern=section ให้เหลือแค่ฐานราก+คาน/เสา (ตัดหน้า wc/grab_rail/
# ramp/roof_eave/slab/precast_plank/seismic/pipe_install ออก — ไม่ใช่หมวดที่สนใจรอบนี้)
# ตัดออก 12 หน้า: 12,13,14,15,16,17 (wc/grab_rail/ramp/roof_eave),
# 30,31 (slab/precast_plank), 32,33 (seismic), 39,40 (pipe_install)
# เหลือ section แค่: 25,26,27 (footing detail), 28,29 (beam detail)
#
# 2026-08-24 (2): มะขามสั่งตัดเพิ่ม — เอาแต่โครงสร้างล้วน (plan/section ของฐานราก-คาน-เสา)
# ตัดออกอีก 10 หน้า: 4,18,19,35,36,42 (notes/design_guidance — ไม่ใช่โครงสร้าง),
# 38,44 (wc_plan_isometric/lighting_outlet_plan — WC/ไฟฟ้า ไม่ใช่โครงสร้าง),
# 11,43 (door_window_schedule/panel_schedule — schedule ตาราง ไม่ใช่ plan/section)
# หน้า 4,6,11 เคย extract ไปแล้วตอน scope เก่า (ไฟล์ยังอยู่ใน tuned/ ไม่ได้ลบ) แต่หน้า 4,11
# ไม่นับเป็น scope อีกต่อไป — เหลือ 12 หน้า ล้วนเป็น plan/section ของฐานราก-คาน-เสา-โครงหลังคา
PAGE_FILTER = {
    "11": (
        [6, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 37]
    ),
}
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


def load_model(variant):
    """variant='tuned' -> base+adapter (PEFT); variant='base' -> base เพียวๆ ไม่มี adapter."""
    try:
        from unsloth import FastVisionModel as UnslothModel
    except ImportError:
        from unsloth import FastModel as UnslothModel

    if variant == "tuned":
        adapter_path = ADAPTER_REPO
        if not os.path.isdir(ADAPTER_REPO):
            from huggingface_hub import snapshot_download
            local_dir = snapshot_download(repo_id=ADAPTER_REPO, allow_patterns=[f"{ADAPTER_SUBFOLDER}/*"])
            adapter_path = os.path.join(local_dir, ADAPTER_SUBFOLDER)
        src = adapter_path
    else:
        src = BASE_MODEL

    model, tokenizer = UnslothModel.from_pretrained(src, load_in_4bit=False)
    ip = getattr(tokenizer, "image_processor", None)
    if ip is not None:
        ip.size["longest_edge"] = MAX_PIXELS
        ip.size["shortest_edge"] = MIN_PIXELS
        print(f"image processor: max={ip.size['longest_edge']} px (≈{ip.size['longest_edge'] // 1024} visual tokens/ภาพ)")
    else:
        print("⚠️  tokenizer.image_processor ไม่มี — ความละเอียดภาพอาจไม่ถูกบังคับตามที่ตั้งใจ")
    UnslothModel.for_inference(model)
    return model, tokenizer


def setup_grammar(model, tokenizer):
    """xgrammar builtin JSON grammar — เหมือน t02's run_house_batch.py (rule_of_tune.md ข้อ 13,
    พิสูจน์แล้วบน GPU จริง 2026-08-22: 96.8% valid vs 57.9% ไม่มี grammar). ตัว tokenizer จริงต้อง
    แกะจาก processor wrapper (.tokenizer) ไม่ใช่ตัว tokenizer ที่ UnslothModel คืนมาตรงๆ
    คืน None ถ้าใช้ไม่ได้ (จะรันต่อแบบไม่ constrain แทนที่จะพังทั้งสคริปต์)"""
    try:
        import xgrammar as xgr
        cfg = model.config
        vocab = getattr(cfg, "vocab_size", None) or cfg.text_config.vocab_size
        tok_info = xgr.TokenizerInfo.from_huggingface(tokenizer.tokenizer, vocab_size=vocab)
        compiled = xgr.GrammarCompiler(tok_info).compile_builtin_json_grammar()
        print("grammar-constrained: xgrammar")
        return lambda: {"logits_processor": [xgr.contrib.hf.LogitsProcessor(compiled)]}
    except Exception as e:
        print(f"⚠️  xgrammar ใช้ไม่ได้ ({e}) — รันต่อแบบไม่ constrain")
        return None


def strip_fence(text):
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    t = m.group(1).strip() if m else t
    # ตัวกันเผื่อสำหรับ path ที่ไม่มี grammar (--no-grammar) — xgrammar เองพิสูจน์แล้วว่า
    # comma ท้ายเป็นไปไม่ได้ที่ระดับ grammar (rule_of_tune.md ข้อ 13) แต่ output ดิบไม่มี
    # grammar กำกับยังเสี่ยงมี trailing comma ได้ตามปกติของ LLM
    return re.sub(r",(\s*[}\]])", r"\1", t)


PAGE_TIMEOUT_S = 25 * 60  # มะขามสั่ง 2026-08-24: หน้าไหนเกิน 25 นาทีตัดจบเลย (หน้า25 ค้างจริง
# แม้มี grammar+repetition_penalty แล้ว — เพดาน max_new_tokens=9000 ไม่พอกันเวลา ถ้าเนื้อหา/
# วนซ้ำแบบ grammar-legal ยาวจริง) ใช้ StoppingCriteria เช็คเวลาแทน os-level kill เพื่อให้ยัง
# ได้ output บางส่วนกลับมา (มักจะ parse ไม่ผ่านเพราะตัดกลางคัน แต่ไม่เสีย process/ต้องโหลดโมเดลใหม่)


class _TimeLimit:
    """StoppingCriteria แบบ duck-typed (import transformers.StoppingCriteria ตรงๆ ในฟังก์ชันที่ใช้
    เพื่อไม่ต้อง import หนักที่หัวไฟล์ตอน --phase อื่นไม่ได้ใช้)"""
    def __init__(self, deadline):
        self.deadline = deadline

    def __call__(self, input_ids, scores, **kwargs):
        return time.time() > self.deadline


def generate(model, tokenizer, prompt_text, img_path, max_new_tokens, grammar_setup=None):
    from PIL import Image
    import torch
    from transformers import StoppingCriteriaList
    img = Image.open(img_path).convert("RGB")
    msgs = [{"role": "user", "content": [
        {"type": "image", "image": img}, {"type": "text", "text": prompt_text}]}]
    # enable_thinking=False required — ดู eval_fields.py comment เดียวกัน (bug พบ 2026-07-24)
    text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer([img], text, add_special_tokens=False, return_tensors="pt").to("cuda")
    gen_kwargs = dict(max_new_tokens=max_new_tokens, do_sample=False,
                       repetition_penalty=1.15, no_repeat_ngram_size=8,
                       stopping_criteria=StoppingCriteriaList([_TimeLimit(time.time() + PAGE_TIMEOUT_S)]))
    if grammar_setup is not None:
        gen_kwargs.update(grammar_setup())  # ตัวใหม่ต่อครั้ง — LogitsProcessor เป็น stateful
    out = model.generate(**inputs, **gen_kwargs)
    pred_txt = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    del inputs, out
    gc.collect()
    torch.cuda.empty_cache()
    return pred_txt


def discover_pages(images_root, house_name):
    images_dir = images_root / house_name
    pat = re.compile(rf"^{re.escape(house_name)}_หน้า(\d+)\.png$")
    pages = []
    for p in images_dir.glob(f"{house_name}_หน้า*.png"):
        m = pat.match(p.name)
        if m:
            pages.append(int(m.group(1)))
    return images_dir, sorted(pages)


def run_classify(model, tokenizer, args, grammar_setup=None):
    out_root = Path(args.out_root) / "_classify"
    for hnum in args.houses:
        house_name = HOUSES[hnum]
        out_dir = out_root / f"{hnum}{house_name}"
        out_dir.mkdir(parents=True, exist_ok=True)
        log_file = out_dir / "classify_log.txt"
        classify_file = out_dir / "_classify.json"
        classify_map = json.loads(classify_file.read_text(encoding="utf-8")) if classify_file.exists() else {}

        images_dir, pages = discover_pages(Path(args.images_root), house_name)
        if args.limit:
            pages = pages[: args.limit]
        log(log_file, f"=== classify บ้าน {hnum}{house_name}: {len(pages)} หน้า ===")

        for page_num in pages:
            page_str = f"{page_num:02d}"
            if page_str in classify_map:
                continue
            img_path = images_dir / f"{house_name}_หน้า{page_str}.png"
            if not img_path.exists():
                log(log_file, f"[classify] หน้า{page_str}: image missing, skip")
                continue
            t0 = time.time()
            content = generate(model, tokenizer, CLASSIFY_PROMPT, img_path, 300, grammar_setup)
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

        keep = [p for p in pages if set(classify_map.get(f"{p:02d}", [])) & KEEP_PATTERNS]
        log(log_file, f"=== จบ classify บ้าน {hnum}{house_name}: keep {len(keep)}/{len(pages)} หน้า {keep} ===")


def run_extract(model, tokenizer, args, grammar_setup=None):
    for hnum in args.houses:
        house_name = HOUSES[hnum]
        images_dir, all_pages = discover_pages(Path(args.images_root), house_name)

        if hnum in PAGE_FILTER:
            # ตัดจาก ground truth จริงแล้ว (ดูคอมเมนต์เหนือ PAGE_FILTER) — ไม่ต้อง classify
            keep_pages = [p for p in PAGE_FILTER[hnum] if p in all_pages]
        else:
            classify_file = Path(args.out_root) / "_classify" / f"{hnum}{house_name}" / "_classify.json"
            if not classify_file.exists():
                print(f"⚠️  ไม่มีผล classify ของบ้าน {hnum}{house_name} — รัน --phase classify ก่อน, ข้ามบ้านนี้")
                continue
            classify_map = json.loads(classify_file.read_text(encoding="utf-8"))
            keep_pages = [p for p in all_pages if set(classify_map.get(f"{p:02d}", [])) & KEEP_PATTERNS]

        out_dir = Path(args.out_root) / args.variant / f"{hnum}{house_name}"
        raw_dir = out_dir / "_raw"
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(exist_ok=True)
        log_file = out_dir / "extract_log.txt"

        if args.limit:
            keep_pages = keep_pages[: args.limit]
        log(log_file, f"=== extract บ้าน {hnum}{house_name} (variant={args.variant}): {len(keep_pages)} หน้า {keep_pages} ===")

        n_ok, t0 = 0, time.time()
        for page_num in keep_pages:
            page_str = f"{page_num:02d}"
            img_path = images_dir / f"{house_name}_หน้า{page_str}.png"
            out_json = out_dir / f"{house_name}_หน้า{page_str}_ai.json"
            raw_txt = raw_dir / f"{house_name}_หน้า{page_str}.txt"
            if out_json.exists():
                log(log_file, f"[extract] หน้า{page_str}: already done, skip")
                n_ok += 1
                continue
            if not img_path.exists():
                log(log_file, f"[extract] หน้า{page_str}: image missing, skip")
                continue
            t1 = time.time()
            content = generate(model, tokenizer, PROMPT_SHORT, img_path, 9000, grammar_setup)
            elapsed = time.time() - t1
            raw_txt.write_text(content, encoding="utf-8")
            try:
                parsed = json.loads(strip_fence(content))
                out_json.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
                log(log_file, f"[extract] หน้า{page_str}: OK ({elapsed:.0f}s)")
                n_ok += 1
            except json.JSONDecodeError as e:
                log(log_file, f"[extract] หน้า{page_str}: ⚠️ parse JSON ไม่ผ่าน ({e}) — raw ที่ {raw_txt.name}")

        elapsed_all = time.time() - t0
        summary = {"house": f"{hnum}{house_name}", "variant": args.variant,
                   "pages": len(keep_pages), "json_valid": n_ok, "elapsed_sec": round(elapsed_all, 1)}
        (out_dir / "_batch_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        log(log_file, f"=== จบบ้าน {hnum}{house_name}: {n_ok}/{len(keep_pages)} JSON valid, {elapsed_all/60:.1f} นาที ===")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["classify", "extract"], required=True)
    ap.add_argument("--variant", choices=["tuned", "base"], default="tuned",
                     help="เฉพาะ --phase extract (classify ใช้ tuned เสมอ)")
    ap.add_argument("--images-root", required=True)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--houses", nargs="+", default=list(HOUSES.keys()), choices=list(HOUSES.keys()))
    ap.add_argument("--limit", type=int, default=0, help="จำกัดจำนวนหน้า/บ้าน (0 = ทุกหน้าที่ผ่านกรอง)")
    ap.add_argument("--no-grammar", action="store_true",
                     help="ปิด xgrammar (ค่าเริ่มต้นเปิด — พิสูจน์แล้ว 96.8%% valid บน t02, rule_of_tune ข้อ 13)")
    args = ap.parse_args()

    variant = "tuned" if args.phase == "classify" else args.variant
    print(f"=== โหลดโมเดล (variant={variant}) ===")
    model, tokenizer = load_model(variant)

    grammar_setup = None if args.no_grammar else setup_grammar(model, tokenizer)

    if args.phase == "classify":
        run_classify(model, tokenizer, args, grammar_setup)
    else:
        run_extract(model, tokenizer, args, grammar_setup)


if __name__ == "__main__":
    main()
