#!/usr/bin/env python3
"""gate2_check.py — ตัวตรวจของ gate 2 (t07 Palfrey) · gate2_smoke.sh เรียกให้ทีละข้อ

  python gate2_check.py config <adapter_dir>        # r16 · α32 · lora_B_layout grouped_by_expert · มี training_env.txt
  python gate2_check.py longest [--data data]       # fold (0-3) ที่ train มีแถวยาวสุด — ประเมินแบบเดียวกับ SORT_LONGEST
  python gate2_check.py reload --adapter DIR --val data/val_fold0.jsonl [--row N] [--out DIR] [--results tsv]
      process ใหม่ + env grouped → โหลด adapter ผ่าน Unsloth (แบบ serve_purson.load) → เช็ค LoRA ของ expert
      (port จาก Constistant server/purson-worker/serve_purson.py check_expert_lora — ไม่ import Constistant)
      → อนุมาน 1 แถว val ด้วยข้อความในแถวเอง (= prompt จริงของ t07 ที่ build_t07 ใช้) → ต้อง parse เป็น JSON + ไม่มีชื่อบ้านเทรน
      ⚠️ เปิดโมเดลผ่าน Unsloth เพื่อตรวจอย่างเดียว (ไม่ใช่เสิร์ฟ) — บอกมะขามก่อนรัน (กฎ 7 พ.ย.)

ต่างจากตัวเสิร์ฟโดยตั้งใจ: serve_purson "ตรวจไม่ได้ = เตือนแล้วไปต่อ" (ไม่อยากปิดเครื่องดีวันสาธิต) แต่ด่านก่อนเช่า
4 การ์ดต้อง "ยืนยันได้เท่านั้นถึงผ่าน" — ทุกกรณีที่ยืนยันไม่ได้ = FAIL (หรือ UNVERIFIED สำหรับ PIN_SET=t05)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GROUPED = "grouped_by_expert"
MAX_PIXELS, MIN_PIXELS, MAX_LENGTH = 6912 * 1024, 256 * 1024, 47104      # = train_t07.py
EXPECT_EXPERT_WRAPPERS = 80                                             # 40 ชั้น × gate_up_proj/down_proj
HOUSE_RE = re.compile(r"บ้าน_(?:เล็ก|ใหญ่)_\d+ชั้น_\d+")                 # D5 — ทุกจำนวนชั้น
TRACES = {"ISO date": r"20\d\d-\d\d-\d\d", "op_fix": r"op_fix", "by_user": r"by_user",
          "CORRECTED_": r"CORRECTED_", "หน้าNN": r"_หน้า\d", ".png": r"\.png", "source_image": r"source_image"}
CJK_RE = re.compile(r"[一-鿿]")


def label_text(row):
    a = row["messages"][1]["content"]
    return "".join(x.get("text", "") for x in a) if isinstance(a, list) else a


def row_est(row, sizes):
    """vis + (ข้อความ prompt + label)/2.2 — สูตรเดียวกับ _len_est ใน train_t07.py (ขนาดรูปจาก header)"""
    vis, txt = 0, 0
    for c in row["messages"][0]["content"]:
        if c["type"] == "image":
            p = c["image"]
            if p not in sizes:
                from PIL import Image
                with Image.open(ROOT / p) as im:
                    sizes[p] = im.size
            w, h = sizes[p]
            vis += min(w * h, MAX_PIXELS) // 1024
        else:
            txt += len(c["text"])
    return vis + (txt + len(label_text(row))) / 2.2


def cmd_longest(a):
    best, sizes = (-1.0, None, None), {}
    for k in range(4):
        p = Path(a.data) / f"train_fold{k}.jsonl"
        if not p.is_file():
            raise SystemExit(f"⛔ ไม่มี {p}")
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    e = row_est(r, sizes)
                    if e > best[0]:
                        best = (e, k, r.get("id"))
    print(f"FOLD={best[1]} est={best[0]:.0f} id={best[2]}")
    return 0


def cmd_config(a):
    d = Path(a.adapter)
    cfg = json.loads((d / "adapter_config.json").read_text(encoding="utf-8"))
    envp = d / "training_env.txt"
    env = json.loads(envp.read_text(encoding="utf-8")) if envp.is_file() else {}
    pin = env.get("pin_set", "A")
    lay = cfg.get("lora_B_layout")
    nested = {p.get("lora_B_layout") for p in ((cfg.get("unsloth_fused_expert_lora") or {}).get("parameters")
                                                 or {}).values() if isinstance(p, dict) and p.get("lora_B_layout")}
    st = d / "adapter_model.safetensors"
    checks = [
        ("r == 16", cfg.get("r") == 16, cfg.get("r")),
        ("lora_alpha == 32", cfg.get("lora_alpha") == 32, cfg.get("lora_alpha")),
        ("lora_B_layout", lay == GROUPED or (pin == "t05" and lay is None), f"{lay!r} (PIN_SET {pin})"),
        ("nested layout ตรงกัน", not nested or nested == {GROUPED}, sorted(nested) or "-"),
        ("target_parameters (expert LoRA)", bool(cfg.get("target_parameters")), len(cfg.get("target_parameters") or [])),
        ("adapter_model.safetensors", st.is_file(), f"{st.stat().st_size:,} B" if st.is_file() else "ไม่มี"),
        ("training_env.txt", bool(env), f"pin {pin} · drift {len(env.get('pins_drift') or [])}" if env else "ไม่มี"),
    ]
    print(f"r={cfg.get('r')} alpha={cfg.get('lora_alpha')} lora_B_layout={lay} peft={cfg.get('peft_version')} pin={pin}")
    for name, ok, detail in checks:
        print(f"  {'✓' if ok else '⛔'} {name}: {detail}")
    return 0 if all(ok for _, ok, _ in checks) else 1


def print_versions():
    from importlib import metadata
    vs = []
    for pkg in ("unsloth", "unsloth_zoo", "peft", "transformers", "torch"):
        try:
            vs.append(f"{pkg} {metadata.version(pkg)}")
        except Exception:
            vs.append(f"{pkg} ?")
    print("เวอร์ชัน: " + " · ".join(vs), flush=True)
    print(f"UNSLOTH_MOE_LORA_B_LAYOUT={os.environ.get('UNSLOTH_MOE_LORA_B_LAYOUT', '<ไม่ได้ตั้ง>')}", flush=True)


def check_expert_lora(model, tok, adapter_dir, pin, expect=EXPECT_EXPERT_WRAPPERS):
    """LoRA ของ MoE expert ถูกอ่านแบบที่ adapter ประกาศจริงไหม — คืน (True/False/"UNVERIFIED", ข้อความ)
    ตรรกะเดียวกับ serve_purson.check_expert_lora (หลัง forward จริง 1 ครั้งถาม zoo ว่าใช้ทางของ Unsloth และอ่าน layout ไหน)
    แต่เข้มกว่า: จำนวนต้องครบ · ต้องมีคีย์ใน adapter_config · ตัวแปะต้องติด · ต้องวัดได้ครบทุกตัว"""
    import torch
    from peft.tuners.lora.layer import ParamWrapper
    wrappers = [(n, m) for n, m in model.named_modules()
                if isinstance(m, ParamWrapper) and int(getattr(m, "num_experts", 1) or 1) > 1]
    want = json.loads((Path(adapter_dir) / "adapter_config.json").read_text(encoding="utf-8")).get("lora_B_layout")
    env = os.environ.get("UNSLOTH_MOE_LORA_B_LAYOUT")
    print(f"LoRA ของ expert {len(wrappers)} ตัว · adapter ประกาศ {want} · env {env}", flush=True)
    if len(wrappers) != expect:
        return False, f"พบ LoRA ของ expert {len(wrappers)} ตัว (ต้อง {expect})"
    if env != GROUPED:
        return False, f"env UNSLOTH_MOE_LORA_B_LAYOUT={env!r} (ต้อง {GROUPED})"
    try:
        from unsloth_zoo.temporary_patches import moe_utils as mu
        layout_for = mu.moe_lora_b_layout_for_wrapper
        applies_stash = mu._wrapper_forward_applies_stash
    except Exception as e:
        if pin == "t05":
            return "UNVERIFIED", f"PIN_SET=t05: zoo ≤ 2026.9.5 ไม่มีฟังก์ชันตรวจ ({type(e).__name__}) — grouped ตายตัว ต้องตัดสินเอง"
        return False, f"unsloth_zoo ไม่มีฟังก์ชันตรวจ ({type(e).__name__}) — ยืนยันไม่ได้"
    if want != GROUPED:
        return False, f"adapter_config lora_B_layout={want!r} (ต้อง {GROUPED})"
    # วัดได้หลังมี forward จริงหนึ่งครั้ง — Unsloth ตัดสินตอนนั้นว่าจะใช้ทางของตัวเองหรือยกให้ PEFT
    warm = tok(None, "ok", add_special_tokens=False, return_tensors="pt").to("cuda")
    with torch.no_grad():
        model.generate(**warm, max_new_tokens=1, do_sample=False)
    # ตัวแปะไม่ติด = forward ของ PEFT = rank_major เสมอ (layout_for ตอบตาม env เมื่อยังไม่มีผลวัด) — ดู __code__
    code = getattr(getattr(ParamWrapper.forward, "__code__", None), "co_name", "")
    patched = code == "_patched_param_wrapper_forward" or any(applies_stash(w) is not None for _, w in wrappers)
    if not patched:
        return False, "ตัวแปะ MoE ของ Unsloth ไม่ติด — LoRA ของ expert วิ่งทาง PEFT (rank_major)"
    bad, unmeasured = [], []
    for name, w in wrappers:
        lay, st = layout_for(w), applies_stash(w)
        if lay != want:
            bad.append(f"{name.split('language_model.')[-1]}: อ่านแบบ {lay} · วัดได้={st}")
        elif st is None:
            unmeasured.append(name)
    if bad:
        return False, f"อ่านผิดแบบ {len(bad)}/{len(wrappers)} ตัว — ตัวอย่าง: {bad[0]}"
    if unmeasured:
        return False, f"Unsloth ยังไม่ได้วัด {len(unmeasured)}/{len(wrappers)} ตัว — ยืนยันไม่ได้"
    return True, f"✅ LoRA ของ expert ทั้ง {len(wrappers)} ตัว อ่านแบบ {want} ผ่านทางของ Unsloth"


def strip_fences(s):
    s = s.strip()
    m = re.match(r"^```[A-Za-z]*\s*\n(.*?)\n?```\s*$", s, re.S)
    return m.group(1).strip() if m else s


def pick_row(val_path, row_idx):
    with open(val_path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if row_idx is not None:
        return rows[row_idx], row_idx
    cands = [(len(label_text(r)), i) for i, r in enumerate(rows)
             if sum(c["type"] == "image" for c in r["messages"][0]["content"]) == 1 and len(label_text(r)) >= 300]
    if not cands:
        raise SystemExit("⛔ ไม่มีแถว val ภาพเดียวที่ label ≥ 300 ตัวอักษร — ใส่ --row เอง")
    _, i = min(cands)            # label สั้นสุด = อนุมานเร็วสุด (Unsloth MoE ช้ามาก) แต่ยังไม่ใช่คำตอบว่าง
    return rows[i], i


def cmd_reload(a):
    results = []

    def rec(step, status, detail):
        status = {True: "PASS", False: "FAIL"}.get(status, status)
        results.append((step, status, detail))
        print(f"{status:5} {step}: {detail}", flush=True)
        if a.results:
            with open(a.results, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"{step}\t{status}\t{detail}\n")

    # Lesson 11 — ห้ามโหลดโมเดลชุดที่สองบนการ์ดที่มีงานเทรนอยู่
    try:
        busy = subprocess.run(["pgrep", "-f", "[t]rain_t07"], capture_output=True).returncode == 0
    except FileNotFoundError:
        busy = False
        print("⚠️  ไม่มี pgrep — เช็คเองว่าไม่มี train_t07 รันอยู่ (nvidia-smi)", flush=True)
    if busy:
        rec("5a LoRA expert layout", False, "มี train_t07 รันอยู่ — ห้ามโหลดโมเดลที่สองบนการ์ดเดียวกัน (Lesson 11)")
        return 1
    os.environ.setdefault("UNSLOTH_MOE_LORA_B_LAYOUT", GROUPED)       # ต้องก่อน import unsloth
    envp = Path(a.adapter) / "training_env.txt"
    pin = json.loads(envp.read_text(encoding="utf-8")).get("pin_set", "A") if envp.is_file() else "A"
    from unsloth import FastVisionModel
    import torch
    from PIL import Image
    from transformers import StoppingCriteriaList

    model, tok = FastVisionModel.from_pretrained(a.adapter, load_in_4bit=False, max_seq_length=MAX_LENGTH)
    ip = tok.image_processor                     # ต้องเท่าตอนเทรน — ไม่ตรง = บั๊กคลาส t01/t04 (Lesson 15)
    ip.size["longest_edge"], ip.size["shortest_edge"] = MAX_PIXELS, MIN_PIXELS
    FastVisionModel.for_inference(model)
    print_versions()
    ok, msg = check_expert_lora(model, tok, a.adapter, pin)
    rec("5a LoRA expert layout", ok, msg)

    row, idx = pick_row(a.val, a.row)
    content = []
    for c in row["messages"][0]["content"]:
        if c["type"] == "image":
            with Image.open(ROOT / c["image"]) as im:
                content.append({"type": "image", "image": im.convert("RGB")})
        else:
            content.append({"type": "text", "text": c["text"]})
    msgs = [{"role": "user", "content": content}]
    # [t01] enable_thinking=False จำเป็น — ไม่งั้นเขียน CoT จนหมด budget ก่อนถึง JSON
    text = tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
    imgs = [c["image"] for c in content if c["type"] == "image"]
    inputs = tok(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
    lab = label_text(row)
    lab_tok = len(tok.tokenizer(lab, add_special_tokens=False)["input_ids"])
    max_new = min(8192, max(1024, int(lab_tok * 1.5) + 256))
    deadline = time.time() + a.minutes * 60

    class _Deadline:
        def __call__(self, input_ids, scores, **kw):
            return time.time() > deadline

    torch.manual_seed(3407)
    t0 = time.time()
    # sampling เดียวกับ production (worker T 0.7 · serve_purson top_p 0.8 top_k 20) — greedy ทำให้วนซ้ำ (Qwen ประกาศเอง)
    out = model.generate(**inputs, max_new_tokens=max_new, do_sample=True, temperature=0.7, top_p=0.8, top_k=20,
                         stopping_criteria=StoppingCriteriaList([_Deadline()]))
    gen = out[0][inputs["input_ids"].shape[1]:]
    pred = tok.decode(gen, skip_special_tokens=True)
    dt = time.time() - t0
    if a.out:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"val0_row{idx}_pred.txt").write_text(pred, encoding="utf-8")
        (Path(a.out) / f"val0_row{idx}_label.json").write_text(lab, encoding="utf-8")
    head = f"แถว {idx} ({row.get('subtask')}, label {lab_tok} token) · ได้ {gen.shape[0]} token ใน {dt:.0f}s"
    if gen.shape[0] >= max_new or time.time() > deadline:
        head += " · ⚠️ ชนเพดาน/หมดเวลา"
    try:
        parsed = json.loads(strip_fences(pred))
        rec("5b อนุมาน → JSON", isinstance(parsed, dict), f"{head} · คีย์ {sorted(parsed)[:8] if isinstance(parsed, dict) else type(parsed).__name__}")
    except Exception as e:
        rec("5b อนุมาน → JSON", False, f"{head} · parse ไม่ได้ ({e}) · ต้น: {pred[:120]!r}")
    houses = sorted(set(HOUSE_RE.findall(pred)))
    rec("5c ไม่มีชื่อบ้านเทรน", not houses, f"พบ {houses[:3]}" if houses else "0 ครั้ง (regex ทุกจำนวนชั้น)")
    traces = [f"{k} {n}" for k, n in ((k, len(re.findall(v, pred))) for k, v in TRACES.items()) if n]
    rec("5d ร่องรอยไฟล์เทรน/ภาษาจีน", "INFO", " · ".join([f"cjk {len(CJK_RE.findall(pred))}"] + traces))
    return 0 if all(s != "FAIL" for _, s, _ in results) else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("config")
    p.add_argument("adapter")
    p = sub.add_parser("longest")
    p.add_argument("--data", default=str(HERE / "data"))
    p = sub.add_parser("reload")
    p.add_argument("--adapter", required=True)
    p.add_argument("--val", required=True)
    p.add_argument("--row", type=int, default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--results", default=None, help="ต่อท้ายผลลง tsv ของ gate2_smoke.sh")
    p.add_argument("--minutes", type=float, default=20.0, help="เพดานเวลาอนุมาน")
    a = ap.parse_args(argv)
    return {"config": cmd_config, "longest": cmd_longest, "reload": cmd_reload}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
