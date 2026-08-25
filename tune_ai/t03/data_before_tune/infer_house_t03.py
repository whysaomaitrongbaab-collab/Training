#!/usr/bin/env python3
"""infer_house_t03.py — ให้โมเดล t03 ถอดแบบ "ทีละ subtask" แล้วเทียบกับ GT

ออกแบบให้ไม่ทำงานซ้ำกับ build_dataset_t03.py เลย: **อ่าน train.jsonl/val.jsonl ที่อัปโหลด
ไปแล้วเป็นตัวป้อน** — แต่ละแถวมี (ภาพ, prompt ของ subtask, GT) ครบอยู่แล้ว จึงไม่ต้องส่ง
โฟลเดอร์ json_แก้ไขแล้ว/ หรือ image/ ขึ้นเครื่องเช่าเพิ่มแม้แต่ไฟล์เดียว
โมเดลเห็นเฉพาะ messages[0] (ภาพ+prompt) — GT ใน messages[1] ใช้ตอนเทียบผลเท่านั้น

    python3 infer_house_t03.py --house 32 --adapter outputs_t03/lora
    python3 infer_house_t03.py --house 01 --adapter outputs_t03/lora   # บ้าน val (ไม่เคยเห็น)
    python3 infer_house_t03.py --house 32 --base                       # untuned เทียบ

📌 กติกาถาวรของ t03 (มะขามสั่ง 2026-08-24): **หน้า plan_beam แนบ xgrammar ทุกครั้ง**
   หน้าคลาสนี้คือตัววนซ้ำ/JSON ไม่ปิด (บ้าน08 หน้า20, บ้าน09 หน้า26 48→2 collapse)
   xgrammar พิสูจน์บน GPU แล้ว 96.8% vs 57.9% — rule_of_tune ข้อ 13
   `--grammar-all` บังคับใช้ทุก subtask, `--no-grammar` ปิดทั้งหมด (ไว้ทำ A/B)

⚠️ อ่านตัวเลขให้ถูก: บ้านที่อยู่ใน train (เช่น 32) โมเดลเคยเห็นตอนเทรนแล้ว ตัวเลขคือ
   "จำได้แค่ไหน" ไม่ใช่ "อ่านแบบเป็นแค่ไหน" — ต้องเทียบกับบ้าน val (01-05) ถึงจะรู้
   generalization จริง สคริปต์เตือนเองตอนรัน
"""
import argparse
import gc
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_MODEL = "unsloth/Qwen3.6-35B-A3B"
MAX_PIXELS = 5120 * 1024      # = ตอนเทรนเป๊ะ
MIN_PIXELS = 256 * 1024
PAGE_TIMEOUT_S = 25 * 60      # มะขามสั่ง 2026-08-24: เกิน 25 นาที/หน้า ตัดจบ


def strip_fence(text):
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    t = m.group(1).strip() if m else t
    t = re.sub(r",(\s*[}\]])", r"\1", t)   # กันเผื่อ path ที่ไม่มี grammar
    # 2026-08-25: บ้าน 08 task 2 (notes) พบจริง — โมเดลเขียน "0." (จุดทศนิยมไม่มีเลขตาม)
    # ซึ่งไม่ใช่ JSON เลขที่ถูกต้อง (ต้องมีเลขอย่างน้อย 1 ตัวหลังจุด) เติม 0 ปิดให้
    t = re.sub(r"(\d)\.(?=[,}\]\s])", r"\1.0", t)
    return t


def element_ids(doc):
    """ดึง element_id ทั้งหมด ไม่ว่าจะอยู่ใต้ elements[] หรือ views[].elements[]"""
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


class _TimeLimit:
    def __init__(self, deadline):
        self.deadline = deadline

    def __call__(self, input_ids, scores, **kwargs):
        return time.time() > self.deadline


def load_model(src):
    try:
        from unsloth import FastVisionModel as UnslothModel
    except ImportError:
        from unsloth import FastModel as UnslothModel
    model, tokenizer = UnslothModel.from_pretrained(src, load_in_4bit=False)
    ip = getattr(tokenizer, "image_processor", None)
    if ip is not None:                       # [t01] ip.size คือกลไกจริงบน transformers 5.x
        ip.size["longest_edge"] = MAX_PIXELS
        ip.size["shortest_edge"] = MIN_PIXELS
        print(f"image processor: max={ip.size['longest_edge']} px "
              f"(≈{ip.size['longest_edge'] // 1024} visual tokens/ภาพ)")
    UnslothModel.for_inference(model)
    return model, tokenizer


def setup_grammar(model, tokenizer):
    """คืน factory ของ logits_processor (ตัวใหม่ทุกครั้ง — LogitsProcessor เป็น stateful)
    None ถ้าใช้ไม่ได้ → รันต่อแบบไม่ constrain ดีกว่าพังทั้งสคริปต์"""
    try:
        import xgrammar as xgr
        cfg = model.config
        vocab = getattr(cfg, "vocab_size", None) or cfg.text_config.vocab_size
        tok_info = xgr.TokenizerInfo.from_huggingface(tokenizer.tokenizer, vocab_size=vocab)
        compiled = xgr.GrammarCompiler(tok_info).compile_builtin_json_grammar()
        print("grammar-constrained: xgrammar (builtin JSON)")
        return lambda: {"logits_processor": [xgr.contrib.hf.LogitsProcessor(compiled)]}
    except Exception as e:
        print(f"⚠️  xgrammar ใช้ไม่ได้ ({e}) — รันต่อแบบไม่ constrain")
        return None


def generate(model, tokenizer, content, max_new_tokens, grammar_setup):
    from PIL import Image
    import torch
    from transformers import StoppingCriteriaList
    imgs, parts = [], []
    for c in content:
        if c["type"] == "image":
            im = Image.open(HERE / c["image"]).convert("RGB")
            imgs.append(im)
            parts.append({"type": "image", "image": im})
        else:
            parts.append({"type": "text", "text": c["text"]})
    msgs = [{"role": "user", "content": parts}]
    # [t01] enable_thinking=False จำเป็น ไม่งั้นเขียน CoT จนหมด budget ก่อนถึง JSON
    text = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer(imgs, text, add_special_tokens=False, return_tensors="pt").to("cuda")
    kw = dict(max_new_tokens=max_new_tokens, do_sample=False,
              repetition_penalty=1.15, no_repeat_ngram_size=8,
              stopping_criteria=StoppingCriteriaList([_TimeLimit(time.time() + PAGE_TIMEOUT_S)]))
    if grammar_setup is not None:
        kw.update(grammar_setup())
    out = model.generate(**inputs, **kw)
    pred = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    del inputs, out
    gc.collect()
    torch.cuda.empty_cache()
    return pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--house", help="เลขนำหน้าโฟลเดอร์ เช่น 08 หรือ 01")
    ap.add_argument("--all-val", action="store_true",
                    help="ทุกบ้านใน val.jsonl (คู่กับ --subtask ใช้วัด subtask เดียวให้ n มากพอ)")
    ap.add_argument("--subtask", help="กรองเฉพาะ subtask นี้ เช่น plan_beam")
    ap.add_argument("--adapter", default="outputs_t03/lora")
    ap.add_argument("--base", action="store_true", help="ใช้ base ไม่มี adapter (เทียบ untuned)")
    ap.add_argument("--out-root", default="ผล_t03")
    ap.add_argument("--max-new-tokens", type=int, default=6000)
    ap.add_argument("--grammar-all", action="store_true")
    ap.add_argument("--no-grammar", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if not a.house and not a.all_val:
        raise SystemExit("ต้องระบุ --house หรือ --all-val อย่างน้อยหนึ่งอย่าง")
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
        print("    ไม่ใช่ความแม่นยำจริง ต้องดูเฉพาะบ้าน val ถึงจะรู้ generalization")

    tag = "base" if a.base else "tuned"
    out_dir = Path(a.out_root) / tag / (label.replace("::", "__") if a.all_val else houses[0])
    out_dir.mkdir(parents=True, exist_ok=True)

    model, tokenizer = load_model(BASE_MODEL if a.base else a.adapter)
    grammar = None if a.no_grammar else setup_grammar(model, tokenizer)

    results = []
    for i, r in enumerate(rows, 1):
        sub = r.get("subtask")
        # 📌 กติกาถาวร: plan_beam ต้องมี grammar เสมอ (subtask อื่นตาม flag)
        use_g = grammar if (grammar and (a.grammar_all or sub == "plan_beam")) else None
        t0 = time.time()
        try:
            pred = generate(model, tokenizer, r["messages"][0]["content"],
                            a.max_new_tokens, use_g)
            err = None
        except Exception as e:                       # OOM/อื่นๆ — บันทึกแล้วไปหน้าถัดไป
            pred, err = "", f"{type(e).__name__}: {e}"
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
        hit = len(set(gt_ids) & set(p_ids))
        rec = hit / len(set(gt_ids)) if gt_ids else None
        results.append(dict(id=r["id"], subtask=sub, valid=valid, error=err, sec=round(dt, 1),
                            gt_elements=gt_n, pred_elements=p_n,
                            gt_ids=len(set(gt_ids)), hit_ids=hit, recall=rec,
                            grammar=bool(use_g)))
        rl = "-" if rec is None else f"{rec:.0%}"
        print(f"[{i}/{len(rows)}] {sub:<13} {'JSON ok ' if valid else 'JSON เสีย'} "
              f"el {p_n:>3}/{gt_n:<3} id-recall {rl:>4} {dt:>6.0f}s"
              f"{' [xgrammar]' if use_g else ''}{' ' + err if err else ''}", flush=True)

    (out_dir / "_summary.json").write_text(
        json.dumps({"label": label, "houses": houses, "splits": splits_seen,
                    "variant": tag, "results": results},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for x in results if x["valid"])
    recs = [x["recall"] for x in results if x["recall"] is not None]
    line = (f"\nสรุป {label} ({tag}, split={','.join(splits_seen)}): "
            f"JSON valid {ok}/{len(results)} ({ok / len(results):.0%})")
    if recs:
        line += f" | id-recall เฉลี่ย {sum(recs) / len(recs):.1%} (จาก {len(recs)} งานที่ GT มี id)"
    print(line)
    per = {}
    for x in results:
        per.setdefault(x["subtask"], []).append(x)
    for s, xs in sorted(per.items()):
        rs = [x["recall"] for x in xs if x["recall"] is not None]
        v = sum(1 for x in xs if x["valid"])
        print(f"  {s:<13} valid {v}/{len(xs)}"
              + (f" | id-recall {sum(rs) / len(rs):.1%}" if rs else ""))
    print(f"\nไฟล์: {out_dir}")


if __name__ == "__main__":
    main()
