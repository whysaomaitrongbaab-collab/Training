#!/usr/bin/env python3
"""infer_house_t04.py — ให้ InternVL3-78B (QLoRA adapter t04) ถอดแบบ "ทีละ subtask" เทียบกับ GT

**สืบทอด logic วัดผลจาก `infer_house_t03.py` ตรงๆ** (score_ids/element_ids/strip_fence/apply_arm/
hide_grid_lines ไม่ผูก Unsloth เลย — ยกมาไม่ต้องเขียนใหม่) เปลี่ยนแค่ 2 จุด: (1) วิธีโหลดโมเดล
(transformers+bitsandbytes+peft แทน Unsloth) (2) วิธี generate (processor.apply_chat_template
แบบ HF-native แทน tokenizer.apply_chat_template ของ Unsloth)

**อ่าน train.jsonl/val.jsonl ตัวเดิม** (ไม่ใช่ train_lf.json/val_lf.json ที่แปลงไว้เทรน) —
ไฟล์ jsonl เดิมมี id/house/subtask ให้กรองด้วย `--house`/`--subtask` ส่วน `_lf.json` ถูกทำมา
สำหรับ LLaMA-Factory trainer เท่านั้น ไม่มี metadata พวกนี้แล้ว

    python3 infer_house_t04.py --house 01 --adapter outputs_t04/lora   # บ้าน val (ไม่เคยเห็น)
    python3 infer_house_t04.py --house 32 --base                       # untuned เทียบ
    python3 infer_house_t04.py --selftest                              # เช็ค logic ล้วน ไม่ต้องมี GPU/โมเดล

⚠️ **ยังไม่เคยรันจริงบน GPU สักครั้ง** (เขียน 2026-08-30 ตอนมะขามไม่อยู่ under att1235) —
ก่อนใช้จริงต้อง dry-run ยืนยัน 3 เรื่องตาม rule_of_tune ข้อ 13 (ห้าม assume จาก README):
  1. `processor.apply_chat_template(...)` คืนรูปที่ถูกต้องจริงสำหรับ InternVL3-78B-hf
     (เขียนตามรูปแบบมาตรฐานที่ HF ใช้กับ VLM ตระกูลนี้ทั้งหมด — Qwen2-VL/Qwen3-VL/Idefics3
     ใช้ pattern เดียวกัน แต่ InternVL3-hf ยังไม่เคยลองจริงในโปรเจกต์นี้)
  2. `processor.tokenizer` คือ tokenizer จริงสำหรับ xgrammar (บทเรียน t02: "tokenizer" ที่ได้
     จาก processor อาจเป็น wrapper ต้องขุดหา attribute จริง — ใส่ fallback ไว้แล้วแต่ยังไม่ทดสอบ)
  3. bitsandbytes 4-bit โหลด InternVL3-78B-hf ได้จริงไม่ error (dense model ควรได้ แต่ยังไม่วัด)
"""
import argparse
import gc
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_MODEL = "OpenGVLab/InternVL3-78B-hf"  # ⚠️ ต้องเป็นตัว -hf เท่านั้น (ดู train_t04_internvl3_qlora.yaml)
PAGE_TIMEOUT_S = 25 * 60      # เท่า t03 (มะขามสั่ง 2026-08-24: เกิน 25 นาที/หน้า ตัดจบ)


def strip_fence(text):
    """สืบมาจาก infer_house_t03.py ตรงๆ — ไม่ผูกโมเดล/framework ใดๆ"""
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    t = m.group(1).strip() if m else t
    t = re.sub(r",(\s*[}\]])", r"\1", t)   # กันเผื่อ path ที่ไม่มี grammar
    t = re.sub(r"(\d)\.(?=[,}\]\s])", r"\1.0", t)   # "0." → "0.0" (บั๊กที่เจอจริงในบ้าน 08 ยุค t03)
    return t


# ── id-recall scoring — สืบมาจาก infer_house_t03.py ทั้งหมด (มาตรฐาน KIE, ดูที่มาในไฟล์เดิม) ──
PRINTED_ID = re.compile(r"^[A-Za-zก-๙]{1,4}[0-9]{0,3}[A-Za-z']{0,3}$")


def norm_id(s):
    return re.sub(r"\s+", " ", s.strip()).casefold()


def score_ids(gt_ids, pred_ids):
    g_all = {norm_id(i) for i in gt_ids}
    p_all = {norm_id(i) for i in pred_ids}
    g_pr = {norm_id(i) for i in gt_ids if PRINTED_ID.match(i.strip())}
    hit_all = len(g_all & p_all)
    hit_pr = len(g_pr & p_all)
    return dict(
        gt_ids=len(g_all), hit_ids=hit_all,
        recall=hit_all / len(g_all) if g_all else None,
        gt_printed=len(g_pr), hit_printed=hit_pr,
        recall_printed=hit_pr / len(g_pr) if g_pr else None,
    )


def element_ids(doc):
    ids, n = [], 0
    if not isinstance(doc, dict):
        return ids, n
    buckets = []
    if isinstance(doc.get("elements"), list):
        buckets.append(doc["elements"])
    for v in doc.get("views") or []:
        if isinstance(v, dict) and isinstance(v.get("elements"), list):
            buckets.append(v["elements"])
    for b in buckets:
        for e in b:
            if isinstance(e, dict):
                n += 1
                eid = e.get("element_id")
                if isinstance(eid, str):
                    ids.append(eid)
    return ids, n


def apply_arm(content, arm, cv_dir):
    """แขนทดลอง pass 2 vs 2.4a — สืบมาจาก infer_house_t03.py ตรงๆ (hint เป็นข้อความล้วน
    ไม่ผูกโมเดล ใช้กับ InternVL3 ได้เหมือน Qwen ทุกประการ)"""
    if arm == "2" or not cv_dir:
        return content, False
    cv_dir = Path(cv_dir)
    hint = None
    for c in content:
        if c["type"] == "image" and hint is None:
            hp = cv_dir / (Path(c["image"]).stem + "_hint.txt")
            if hp.exists():
                hint = hp.read_text(encoding="utf-8").strip()
    if not hint:
        return content, False
    out = [dict(c) for c in content]
    out.append({"type": "text", "text": "\n\n" + hint})
    return out, True


GM_MARK = "GRID MASTER (resolved axes for this building)\n"


def hide_grid_lines(content, ids):
    """eval เท่านั้น — สืบมาจาก infer_house_t03.py ตรงๆ ห้ามใช้กับงานสกัดจริง"""
    if not ids:
        return content, 0
    hidden = 0
    out = []
    for c in content:
        if c.get("type") == "text" and GM_MARK in c.get("text", ""):
            head, gm = c["text"].split(GM_MARK, 1)
            try:
                doc = json.loads(gm)
                for axis in ("x_lines", "y_lines"):
                    for ln in (doc.get("grid") or {}).get(axis) or []:
                        if str(ln.get("id")) in ids and ln.get("pos_m") is not None:
                            ln["pos_m"] = None
                            hidden += 1
                c = {**c, "text": head + GM_MARK + json.dumps(doc, ensure_ascii=False)}
            except Exception:
                pass
        out.append(c)
    return out, hidden


class _TimeLimit:
    def __init__(self, deadline):
        self.deadline = deadline

    def __call__(self, input_ids, scores, **kwargs):
        return time.time() > self.deadline


# ── ส่วนใหม่ของ t04 — โหลดโมเดล/generate ผ่าน transformers+bitsandbytes+peft (ไม่ใช่ Unsloth) ──

def load_model(adapter_path, use_base):
    """โหลด InternVL3-78B-hf แบบ 4-bit (bitsandbytes) แล้วต่อ LoRA adapter (เว้นแต่ --base)
    ⚠️ ยังไม่เคยรันจริง — โครงตาม pattern มาตรฐานของ transformers AutoModelForImageTextToText
    (ยืนยันจาก HF docs 2026-08-30, ไม่ใช่ pattern เฉพาะของ Unsloth ที่ใช้กับ t01-t03)"""
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

    processor = AutoProcessor.from_pretrained(BASE_MODEL, trust_remote_code=True)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4",
    )
    model = AutoModelForImageTextToText.from_pretrained(
        BASE_MODEL, quantization_config=bnb_config, device_map="cuda",
        torch_dtype=torch.bfloat16, trust_remote_code=True,
    )
    if not use_base:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()

    # tokenizer จริงสำหรับ xgrammar — probe แทนสมมติ (บทเรียน t02 rule_of_tune ข้อ 13:
    # "tokenizer" จาก processor มักเป็น wrapper ไม่ใช่ตัวจริง)
    real_tok = getattr(processor, "tokenizer", None)
    if real_tok is None:
        raise RuntimeError("processor ไม่มี .tokenizer — ต้อง probe หา attribute จริงบนเครื่องเช่า"
                            " ก่อนไปต่อ (ดู docstring หัวไฟล์ข้อ 2)")
    return model, processor, real_tok


def setup_grammar(model, real_tok):
    """คืน factory ของ logits_processor — เหมือน infer_house_t03.py แต่ vocab_size ต้องอ่าน
    จาก model.config ของ InternVL3 (โครง config อาจต่างจาก Qwen — ยังไม่เคย probe จริง)"""
    try:
        import xgrammar as xgr
        cfg = model.config
        vocab = getattr(cfg, "vocab_size", None) or getattr(
            getattr(cfg, "text_config", None), "vocab_size", None)
        if vocab is None:
            raise AttributeError("หา vocab_size ไม่เจอทั้ง config และ config.text_config")
        tok_info = xgr.TokenizerInfo.from_huggingface(real_tok, vocab_size=vocab)
        compiled = xgr.GrammarCompiler(tok_info).compile_builtin_json_grammar()
        print("grammar-constrained: xgrammar (builtin JSON)")
        return lambda: {"logits_processor": [xgr.contrib.hf.LogitsProcessor(compiled)]}
    except Exception as e:
        print(f"⚠️  xgrammar ใช้ไม่ได้ ({e}) — รันต่อแบบไม่ constrain")
        return None


def generate(model, processor, content, max_new_tokens, grammar_setup):
    from PIL import Image
    import torch
    from transformers import StoppingCriteriaList

    parts = []
    for c in content:
        if c["type"] == "image":
            im = Image.open(HERE / c["image"]).convert("RGB")
            parts.append({"type": "image", "image": im})
        else:
            parts.append({"type": "text", "text": c["text"]})
    msgs = [{"role": "user", "content": parts}]
    inputs = processor.apply_chat_template(
        msgs, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt",
    ).to(model.device, torch.bfloat16)
    kw = dict(max_new_tokens=max_new_tokens, do_sample=False,
              repetition_penalty=1.15, no_repeat_ngram_size=8,
              stopping_criteria=StoppingCriteriaList([_TimeLimit(time.time() + PAGE_TIMEOUT_S)]))
    if grammar_setup is not None:
        kw.update(grammar_setup())
    out = model.generate(**inputs, **kw)
    pred = processor.batch_decode(
        out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
    del inputs, out
    gc.collect()
    torch.cuda.empty_cache()
    return pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--house", help="เลขนำหน้าโฟลเดอร์ เช่น 08 หรือ 01")
    ap.add_argument("--all-val", action="store_true")
    ap.add_argument("--subtask", help="กรองเฉพาะ subtask นี้ เช่น plan_beam")
    ap.add_argument("--adapter", default="outputs_t04/lora")
    ap.add_argument("--base", action="store_true", help="ใช้ base ไม่มี adapter (เทียบ untuned)")
    ap.add_argument("--out-root", default="ผล_t04")
    ap.add_argument("--max-new-tokens", type=int, default=6000)
    ap.add_argument("--no-grammar", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--arm", choices=("2", "2.4a"), default="2")
    ap.add_argument("--cv-dir", help="โฟลเดอร์ sidecar จาก tools/cv_scan.py")
    ap.add_argument("--hide-grid-lines")
    ap.add_argument("--selftest", action="store_true",
                     help="เช็ค logic ล้วน (score_ids/element_ids/strip_fence/apply_arm/"
                          "hide_grid_lines) ด้วยข้อมูลจำลอง — ไม่ต้องมี GPU/โมเดล")
    a = ap.parse_args()

    if a.selftest:
        run_selftest()
        return

    if not a.house and not a.all_val:
        raise SystemExit("ต้องระบุ --house หรือ --all-val อย่างน้อยหนึ่งอย่าง (หรือ --selftest)")
    splits = ("val",) if a.all_val else ("test", "val", "train")
    rows = []
    for split in splits:
        fp = HERE / f"{split}.jsonl"
        if not fp.exists():
            continue
        for line in fp.open(encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if a.house and not r["house"].startswith(a.house):
                continue
            if a.subtask and r.get("subtask") != a.subtask:
                continue
            r["_split"] = split
            rows.append(r)
    if not rows:
        raise SystemExit(f"ไม่พบแถวที่ตรงเงื่อนไข (house={a.house} subtask={a.subtask})")
    rows.sort(key=lambda r: r["id"])
    if a.limit:
        rows = rows[:a.limit]
    houses = sorted({r["house"] for r in rows})
    splits_seen = sorted({r["_split"] for r in rows})
    label = a.house or ("val-ทุกหลัง" if a.all_val else "?")
    if a.subtask:
        label += f"::{a.subtask}"
    print(f"{label} | {len(rows)} งาน | {len(houses)} หลัง | split = {','.join(splits_seen)}")
    if "train" in splits_seen:
        print("⚠️  มีบ้านที่อยู่ใน TRAIN — โมเดลเคยเห็นหน้าพวกนี้แล้ว ตัวเลขคือ 'จำได้แค่ไหน'")

    if a.arm != "2" and not a.cv_dir:
        raise SystemExit("--arm %s ต้องมี --cv-dir" % a.arm)

    tag = "base" if a.base else "tuned"
    out_dir = Path(a.out_root) / tag / (label.replace("::", "__") if a.all_val else houses[0])
    if a.arm != "2":
        out_dir = out_dir.with_name(out_dir.name + "__arm" + a.arm)
    hide_ids = {x.strip() for x in a.hide_grid_lines.split(",") if x.strip()} \
        if a.hide_grid_lines else set()
    if hide_ids:
        out_dir = out_dir.with_name(out_dir.name + "__hide" + "-".join(sorted(hide_ids)))
    out_dir.mkdir(parents=True, exist_ok=True)

    model, processor, real_tok = load_model(a.adapter, a.base)
    grammar = None if a.no_grammar else setup_grammar(model, real_tok)

    results = []
    for i, r in enumerate(rows, 1):
        sub = r.get("subtask")
        t0 = time.time()
        try:
            content, hint_used = apply_arm(r["messages"][0]["content"], a.arm, a.cv_dir)
            content, n_hidden = hide_grid_lines(content, hide_ids)
            pred = generate(model, processor, content, a.max_new_tokens, grammar)
            err = None
        except Exception as e:
            pred, err = "", f"{type(e).__name__}: {e}"
            hint_used, n_hidden = False, 0
        dt = time.time() - t0

        stem = r["id"].replace("::", "__").replace("/", "_")
        (out_dir / f"{stem}.txt").write_text(pred, encoding="utf-8")
        try:
            doc = json.loads(strip_fence(pred))
            valid = True
        except Exception:
            doc, valid = None, False
        gt_raw = r["messages"][1]["content"]
        gt_txt = "".join(x.get("text", "") for x in gt_raw) if isinstance(gt_raw, list) else gt_raw
        gt = json.loads(gt_txt)
        gt_ids, gt_n = element_ids(gt)
        p_ids, p_n = element_ids(doc) if valid else ([], 0)
        sc = score_ids(gt_ids, p_ids)
        results.append(dict(id=r["id"], subtask=sub, arm=a.arm, hint_used=hint_used,
                            hidden_grid_lines=n_hidden,
                            valid=valid, error=err, sec=round(dt, 1),
                            gt_elements=gt_n, pred_elements=p_n,
                            grammar=bool(grammar), **sc))
        rl = "-" if sc["recall"] is None else f"{sc['recall']:.0%}"
        rp = "-" if sc["recall_printed"] is None else f"{sc['recall_printed']:.0%}"
        print(f"[{i}/{len(rows)}] {sub:<13} {'JSON ok ' if valid else 'JSON เสีย'} "
              f"el {p_n:>3}/{gt_n:<3} recall {rl:>4} printed {rp:>4} {dt:>6.0f}s"
              f"{' [xgrammar]' if grammar else ''}{' ' + err if err else ''}", flush=True)

    (out_dir / "_summary.json").write_text(
        json.dumps({"label": label, "houses": houses, "splits": splits_seen,
                    "variant": tag, "model": BASE_MODEL, "results": results},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for x in results if x["valid"])
    recs = [x["recall"] for x in results if x["recall"] is not None]
    prs = [x["recall_printed"] for x in results if x.get("recall_printed") is not None]
    line = (f"\nสรุป {label} ({tag}, split={','.join(splits_seen)}): "
            f"JSON valid {ok}/{len(results)} ({ok / len(results):.0%})")
    if recs:
        line += f" | recall รวม {sum(recs) / len(recs):.1%} (จาก {len(recs)} งาน)"
    if prs:
        line += f" | recall เฉพาะชื่อบนแบบ {sum(prs) / len(prs):.1%} (จาก {len(prs)} งาน)"
    print(line)
    per = {}
    for x in results:
        per.setdefault(x["subtask"], []).append(x)
    for s, xs in sorted(per.items()):
        rs = [x["recall"] for x in xs if x["recall"] is not None]
        ps = [x["recall_printed"] for x in xs if x.get("recall_printed") is not None]
        v = sum(1 for x in xs if x["valid"])
        print(f"  {s:<13} valid {v}/{len(xs)}"
              + (f" | recall {sum(rs) / len(rs):.1%}" if rs else "")
              + (f" | printed {sum(ps) / len(ps):.1%} ({len(ps)} งาน)" if ps else " | printed - (GT ไม่มีชื่อบนแบบเลย)"))
    print(f"\nไฟล์: {out_dir}")


def run_selftest():
    """เช็ค logic ล้วนที่ port มาจาก infer_house_t03.py — ไม่ต้องมี GPU/โมเดล/เครือข่าย"""
    # strip_fence
    assert strip_fence('```json\n{"a": 1,}\n```') == '{"a": 1}'
    assert strip_fence('{"x": 0.,}') == '{"x": 0.0}'  # comma-strip รันก่อน decimal-fix
    # score_ids / norm_id / PRINTED_ID
    gt = ["B1", "gate_front", "F1A"]
    pred = ["b1 ", "F1A", "made_up"]
    sc = score_ids(gt, pred)
    assert sc["gt_ids"] == 3 and sc["hit_ids"] == 2, sc
    assert sc["gt_printed"] == 2, sc  # B1, F1A เป็นชื่อบนแบบ; gate_front ไม่ใช่
    assert sc["hit_printed"] == 2, sc
    # element_ids: ทั้ง elements[] และ views[].elements[]
    doc = {"elements": [{"element_id": "A1"}],
           "views": [{"elements": [{"element_id": "A2"}, {"no_id": True}]}]}
    ids, n = element_ids(doc)
    assert set(ids) == {"A1", "A2"} and n == 3, (ids, n)
    # apply_arm: arm "2" ไม่แตะอะไร, ไม่มี cv_dir ก็ไม่แตะ, sidecar หาไม่เจอ = hint_used False
    content = [{"type": "image", "image": "images/nope.png"}, {"type": "text", "text": "p"}]
    out, used = apply_arm(content, "2", "cv_val")
    assert out is content and used is False
    out, used = apply_arm(content, "2.4a", None)
    assert used is False
    out, used = apply_arm(content, "2.4a", "definitely_missing_dir_xyz")
    assert used is False and out == content
    # hide_grid_lines: ไม่มี id ให้ซ่อน = ไม่แตะ; มี GM block จริงต้อง mask pos_m
    gm_text = (GM_MARK + json.dumps(
        {"grid": {"x_lines": [{"id": "1", "pos_m": 0.0}, {"id": "3", "pos_m": 7.0}]}}))
    c2 = [{"type": "text", "text": "head\n\n" + gm_text}]
    out2, hidden = hide_grid_lines(c2, {"3"})
    assert hidden == 1, hidden
    doc2 = json.loads(out2[0]["text"].split(GM_MARK, 1)[1])
    assert doc2["grid"]["x_lines"][1]["pos_m"] is None
    assert doc2["grid"]["x_lines"][0]["pos_m"] == 0.0  # id "1" ไม่ถูกแตะ
    out3, hidden3 = hide_grid_lines(c2, set())
    assert hidden3 == 0
    print("OK — self-check ผ่านทุกข้อ (logic ล้วน, ไม่แตะ GPU/โมเดล)")


if __name__ == "__main__":
    main()
