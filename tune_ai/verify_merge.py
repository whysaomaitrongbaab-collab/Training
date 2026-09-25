#!/usr/bin/env python3
"""verify_merge.py — ด่านตรวจว่า merge_lora_to_base.py ทำงานถูกจริง ไม่ใช่แค่ "รันจบไม่ error"

กฎของทีมเอง (MISTAKES.md 2026-07-29): "a merge/convert step that raises no error has NOT
proven it worked" — บั๊ก merge ของ MoE ไม่มีวัน error มันแค่ให้น้ำหนักที่ผิดเงียบๆ
ไฟล์นี้คือด่านที่จับมันได้ เรียงจากถูกที่สุด (ฟรี ไม่ใช้ GPU) ไปแพงที่สุด

┌─ A: ชั้น experts เปลี่ยนจริงไหม ────────── ฟรี · จับเคส "merge ไม่ติดเลย"
├─ B: ΔW ที่ใส่เข้าไปตรงกับ packing แบบไหน ── ฟรี · จับเคส "merge ติดแต่ layout ผิด" ← ตัวชี้ขาด
└─ C: ผลลัพธ์เหมือน production path ไหม ──── ใช้ GPU · ตัวยืนยันสุดท้ายที่โกหกไม่ได้

รัน:
    # A+B พร้อมกัน (ฟรี รันบนโน้ตบุ๊กได้ ใช้ RAM ~6GB)
    python verify_merge.py --check-ab --base <hf-cache-ของ-base> --merged ./destrier_merged \\
        --adapter <โฟลเดอร์-adapter>

    # C — 3 process แยกกัน (โมเดลใหญ่เกินโหลดพร้อมกัน) แล้วค่อยเทียบ
    python verify_merge.py --fingerprint adapter --adapter <dir> --out ref.pt
    python verify_merge.py --fingerprint merged  --merged ./destrier_merged --out mrg.pt
    python verify_merge.py --fingerprint base    --base-repo unsloth/Qwen3.6-35B-A3B --out base.pt
    python verify_merge.py --compare ref.pt mrg.pt base.pt
"""
import argparse
import glob
import json
import os
import sys

NUM_EXPERTS = 256
MAX_PIXELS = 6912 * 1024
MIN_PIXELS = 256 * 1024


# ── โหลดเทนเซอร์ทีละตัวจาก repo ที่แตกเป็นหลาย shard (mmap ไม่กิน RAM ทั้งก้อน) ──
def weight_map(d):
    idx = glob.glob(os.path.join(d, "*.safetensors.index.json"))
    if idx:
        return json.load(open(idx[0], encoding="utf-8"))["weight_map"]
    files = glob.glob(os.path.join(d, "*.safetensors"))
    if not files:
        sys.exit(f"⛔ ไม่เจอไฟล์ safetensors ใน {d}")
    from safetensors import safe_open
    m = {}
    for f in files:
        with safe_open(f, framework="pt") as h:
            for k in h.keys():
                m[k] = os.path.basename(f)
    return m


def get_tensor(d, wm, name):
    from safetensors import safe_open
    with safe_open(os.path.join(d, wm[name]), framework="pt") as f:
        return f.get_tensor(name)


# ── A: ชั้น experts เปลี่ยนจริงไหม ───────────────────────────────────────────
def check_a(base_dir, merged_dir):
    """merge ที่ "ไม่ติด" จะทำให้เทนเซอร์ของชั้น experts เหมือน base ทุกบิต
    นี่คือเคส "ได้โมเดลเท่ากับไม่เคย fine-tune" ที่ฆ่า t01 มาแล้ว"""
    import torch
    wm_m, wm_b = weight_map(merged_dir), weight_map(base_dir)
    shared = [n for n in wm_m if n in wm_b]
    if not shared:
        sys.exit("⛔ ชื่อเทนเซอร์ของ base กับ merged ไม่ตรงกันเลยสักตัว — ชี้ path ผิด?")
    stat = {"exp_same": 0, "exp_diff": 0, "oth_same": 0, "oth_diff": 0}
    print(f"A: เทียบ {len(shared)} เทนเซอร์ (ใช้เวลาสักครู่ อ่านทีละตัว)…", flush=True)
    for i, n in enumerate(shared, 1):
        same = torch.equal(get_tensor(base_dir, wm_b, n), get_tensor(merged_dir, wm_m, n))
        k = ("exp_" if "experts" in n else "oth_") + ("same" if same else "diff")
        stat[k] += 1
        if i % 200 == 0:
            print(f"   {i}/{len(shared)}", flush=True)
    print(f"\nA: experts  เปลี่ยน {stat['exp_diff']} · เหมือนเดิม {stat['exp_same']}")
    print(f"   อื่นๆ     เปลี่ยน {stat['oth_diff']} · เหมือนเดิม {stat['oth_same']}")
    if stat["exp_diff"] == 0:
        print("⛔ A ไม่ผ่าน: ชั้น MoE ไม่ถูก merge เลยสักตัว = โมเดลนี้เท่ากับ base ที่ไม่เคยเทรน")
        return False
    if stat["exp_same"]:
        print(f"⚠️  มี expert {stat['exp_same']} ตัวที่ไม่เปลี่ยน — merge ติดไม่ครบ ตรวจก่อนใช้")
    print("✅ A ผ่าน: ชั้น MoE ถูกแตะจริง")
    return True


# ── B: ΔW ที่ใส่เข้าไปจริง ตรงกับการแกะแบบไหน ──────────────────────────────
def check_b(base_dir, merged_dir, adapter_dir, n_experts_probe):
    """ตัวชี้ขาด — แกะ lora_A/lora_B ทั้ง 4 แบบ (grouped/rank × A/B) แล้วดูว่าแบบไหน
    สร้าง ΔW ได้ตรงกับที่ merge ใส่เข้าไปจริง

    ถ้าไม่มีแบบไหนตรงเลย = ปัญหาไม่ได้อยู่ที่ขั้น merge แต่อยู่ที่ขั้นรวม 4 fold
    (การ cat แกน rank แบบตรงๆ ถูกสำหรับชั้น dense แต่ผิดสำหรับชั้น expert)"""
    import torch
    from safetensors import safe_open
    wm_m, wm_b = weight_map(merged_dir), weight_map(base_dir)
    cand_names = [n for n in wm_m if n.endswith("mlp.experts.gate_up_proj") and n in wm_b]
    if not cand_names:
        print("⚠️  B ข้าม: ไม่เจอเทนเซอร์ mlp.experts.gate_up_proj (ชื่อชั้นเปลี่ยน?)")
        return True
    name = sorted(cand_names)[len(cand_names) // 2]        # เอาชั้นกลางๆ ไม่ใช่ชั้นแรก/สุดท้าย
    print(f"\nB: ตรวจ packing ด้วย {name.split('language_model.')[-1]} "
          f"(ทดสอบ {n_experts_probe} expert แรก เพื่อประหยัด RAM)")

    dW_full = (get_tensor(merged_dir, wm_m, name).float()
               - get_tensor(base_dir, wm_b, name).float())      # [E, in, out]
    E = dW_full.shape[0]
    p = min(n_experts_probe, E)

    af = glob.glob(os.path.join(adapter_dir, "*.safetensors"))
    if not af:
        sys.exit(f"⛔ ไม่เจอ adapter safetensors ใน {adapter_dir}")
    cfg = json.load(open(os.path.join(adapter_dir, "adapter_config.json"), encoding="utf-8"))

    # ⚠️ จับคู่ด้วย **รูปร่าง** ไม่ใช่ชื่อ — ชื่อคีย์ที่ PEFT เซฟไม่ได้ใช้ชื่อ target_parameters
    #    ตรวจของจริงแล้ว (2026-09-20): gate_up_proj ถูกเซฟเป็น `...experts.base_layer.lora_A`
    #    ส่วน down_proj เป็น `...experts.lora_A` — grep หา "gate_up_proj" ในคีย์ adapter ไม่มีวันเจอ
    #    รูปร่างไม่โกหก: A ต้องเป็น [E*r, in] และ B ต้องเป็น [out, E*r] ของเทนเซอร์ปลายทางตัวนั้น
    layer = next((s for s in name.split(".") if s.isdigit()), None)
    in_dim, out_dim = dW_full.shape[1], dW_full.shape[2]
    with safe_open(af[0], framework="pt") as f:
        cand = [k for k in f.keys()
                if k.endswith("lora_A.weight") and "experts" in k
                and (layer is None or f".layers.{layer}." in k)]
        ka = kb = None
        for k in cand:
            kb_try = k[: -len("lora_A.weight")] + "lora_B.weight"
            if kb_try not in f.keys():
                continue
            sa, sb = f.get_slice(k).get_shape(), f.get_slice(kb_try).get_shape()
            if len(sa) == 2 and len(sb) == 2 and sa[1] == in_dim and sb[0] == out_dim \
                    and sa[0] == sb[1]:
                ka, kb = k, kb_try
                break
        if ka is None:
            print(f"⚠️  B ข้าม: หาคู่ lora_A/B ที่รูปร่างเข้ากับ [{in_dim}→{out_dim}] ไม่เจอ")
            print(f"    (ผู้สมัครในชั้นนี้: {[k.split('language_model.')[-1] for k in cand]})")
            return True
        print(f"   จับคู่กับ {ka.split('language_model.')[-1]} (ด้วยรูปร่าง ไม่ใช่ชื่อ)")
        A = f.get_tensor(ka).float()          # [E*r, in]
        B = f.get_tensor(kb).float()          # [out, E*r]
    r = A.shape[0] // E
    scale = cfg.get("lora_alpha", r) / r
    print(f"   r จากไฟล์ = {r} · alpha = {cfg.get('lora_alpha')} · scaling = {scale:.4f}")

    def unpack_a(mode):                       # → [E, r, in]
        return A.view(E, r, -1) if mode == "grp" else A.view(r, E, -1).permute(1, 0, 2)

    def unpack_b(mode):                       # → [E, r, out]
        return (B.view(-1, E, r).permute(1, 2, 0) if mode == "grp"
                else B.view(-1, r, E).permute(2, 1, 0))

    dW = dW_full[:p]
    ref = dW.norm()
    results = []
    for ma in ("grp", "rank"):
        for mb in ("grp", "rank"):
            try:
                a = unpack_a(ma)[:p].transpose(1, 2).contiguous()     # [p, in, r]
                b = unpack_b(mb)[:p].contiguous()                     # [p, r, out]
                cand = scale * torch.bmm(a, b)
                err = ((dW - cand).norm() / ref).item() if ref > 0 else float("inf")
            except Exception as e:
                err = float("inf")
                print(f"   A={ma:4s} B={mb:4s}  แกะไม่ได้ ({type(e).__name__})")
                continue
            results.append((err, f"A={ma} B={mb}"))
            print(f"   A={ma:4s} B={mb:4s}  ความคลาดเคลื่อน {err:.4f}")
    if not results:
        print("⛔ B ไม่ผ่าน: แกะไม่ได้เลยสักแบบ")
        return False
    best_err, best = min(results)
    print(f"   → ตรงที่สุด: {best} ({best_err:.4f})")
    if best_err > 0.05:
        print("⛔ B ไม่ผ่าน: ไม่มี packing แบบไหนตรงเลย")
        print("   แปลว่าปัญหาไม่ได้อยู่ที่ขั้น merge แต่อยู่ที่ขั้น **รวม 4 fold**")
        print("   (การต่อแกน rank ด้วย cat ตรงๆ ถูกสำหรับชั้น dense แต่ผิดสำหรับชั้น expert)")
        print("   → กลับไปดู soup_safetensors.py ก่อน อย่าไปแก้ที่ merge")
        return False
    print(f"✅ B ผ่าน: merge ใส่ ΔW ตามการแกะแบบ {best} จริง")
    return True


# ── C: ผลลัพธ์เหมือน production path ไหม ────────────────────────────────────
def fixed_input(processor):
    """input ตายตัว ไม่สุ่ม — ต้องได้ชุดเดิมเป๊ะทุก process ไม่งั้นเทียบไม่ได้"""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (768, 576), "white")
    d = ImageDraw.Draw(img)
    for k in range(7):
        d.rectangle([20 + k * 34, 20 + k * 24, 340 + k * 28, 240 + k * 34],
                    outline="black", width=2)
        d.text((44 + k * 22, 260 + k * 12), f"B{k + 1} 200x400 DB16", fill="black")
    ip = getattr(processor, "image_processor", None)
    if ip is not None:
        ip.size["longest_edge"] = MAX_PIXELS
        ip.size["shortest_edge"] = MIN_PIXELS
    text = processor.apply_chat_template(
        [{"role": "user", "content": [{"type": "image", "image": img},
                                      {"type": "text", "text": "อ่านแบบนี้ตอบเป็น JSON"}]}],
        add_generation_prompt=True, enable_thinking=False)
    return processor([img], text, add_special_tokens=False, return_tensors="pt")


def fingerprint(mode, args):
    """logits ของ token ถัดไป 1 ตัว — deterministic ล้วน ไม่ generate ไม่ sample"""
    import torch
    if mode == "adapter":
        from unsloth import FastVisionModel
        if not args.adapter:
            sys.exit("⛔ --fingerprint adapter ต้องใส่ --adapter")
        model, processor = FastVisionModel.from_pretrained(
            model_name=args.adapter, load_in_4bit=False, dtype=torch.bfloat16)
        FastVisionModel.for_inference(model)
    else:
        from transformers import AutoModelForImageTextToText, AutoProcessor
        src = args.merged if mode == "merged" else args.base_repo
        if not src:
            sys.exit(f"⛔ --fingerprint {mode} ต้องใส่ "
                     f"{'--merged' if mode == 'merged' else '--base-repo'}")
        model = AutoModelForImageTextToText.from_pretrained(
            src, dtype=torch.bfloat16, device_map="auto")
        processor = AutoProcessor.from_pretrained(src)
        model.eval()
    inputs = fixed_input(processor)
    inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) for k, v in inputs.items()}
    with torch.no_grad():
        logits = model(**inputs).logits[0, -1].float().cpu()
    torch.save(logits, args.out)
    print(f"✅ เซฟ logits ({mode}) → {args.out}  [{logits.shape[0]} ค่า]")


def compare(ref_p, mrg_p, base_p):
    """mrg ต้องเหมือน ref และต้องต่างจาก base ชัดเจน

    ข้อหลังคือกับดักที่ขาดไม่ได้ — ถ้า mrg เหมือน base มากกว่าเหมือน ref แปลว่า merge
    ไม่ติด ได้โมเดลที่ไม่เคย fine-tune (เคสที่ฆ่า t01 และมองไม่เห็นถ้าไม่เทียบ base)"""
    import torch
    ref, mrg = torch.load(ref_p).float(), torch.load(mrg_p).float()
    cos_rm = torch.nn.functional.cosine_similarity(ref, mrg, dim=0).item()
    top_same = int(ref.argmax()) == int(mrg.argmax())
    max_d = (ref - mrg).abs().max().item()
    print(f"\nC: merged เทียบ production path (base+adapter)")
    print(f"   cosine {cos_rm:.6f} · token อันดับ 1 ตรงกัน {top_same} · ต่างสุด {max_d:.4f}")
    ok = cos_rm >= 0.999 and top_same
    if base_p and os.path.exists(base_p):
        base = torch.load(base_p).float()
        cos_bm = torch.nn.functional.cosine_similarity(base, mrg, dim=0).item()
        print(f"   merged เทียบ base เปล่า: cosine {cos_bm:.6f}")
        if cos_bm >= cos_rm:
            print("⛔ merged เหมือน base มากกว่าเหมือน adapter = **merge ไม่ติด**")
            print("   (ได้โมเดลที่ไม่เคย fine-tune — เคสเดียวกับที่ฆ่า t01 เมื่อ ก.ค.)")
            ok = False
    else:
        print("   ⚠️  ไม่ได้เทียบกับ base เปล่า — ควรทำ ไม่งั้นมองไม่เห็นเคส 'merge ไม่ติด'")
    print("✅ C ผ่าน" if ok else "⛔ C ไม่ผ่าน — อย่า deploy")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-ab", action="store_true", help="ตรวจ A+B (ฟรี ไม่ใช้ GPU)")
    ap.add_argument("--base", help="โฟลเดอร์ base (HF cache snapshot) สำหรับ A/B")
    ap.add_argument("--merged", help="โฟลเดอร์โมเดลที่ merge แล้ว")
    ap.add_argument("--adapter", help="โฟลเดอร์ adapter")
    ap.add_argument("--experts", type=int, default=8, help="ทดสอบ B กี่ expert (ประหยัด RAM)")
    ap.add_argument("--fingerprint", choices=["adapter", "merged", "base"])
    ap.add_argument("--base-repo", help="repo/โฟลเดอร์ base สำหรับ --fingerprint base")
    ap.add_argument("--out", default="fp.pt")
    ap.add_argument("--compare", nargs="+", metavar=("REF MRG", "BASE"))
    a = ap.parse_args()

    if a.check_ab:
        for k in ("base", "merged", "adapter"):
            if not getattr(a, k):
                sys.exit(f"⛔ --check-ab ต้องใส่ --{k}")
        ok = check_a(a.base, a.merged)
        ok = check_b(a.base, a.merged, a.adapter, a.experts) and ok
        print("\n" + ("✅ A+B ผ่าน — ไปต่อข้อ C (เทียบพฤติกรรม) ได้" if ok
                      else "⛔ A+B ไม่ผ่าน — อย่าเสียเงินทำข้อ C แก้ตรงนี้ก่อน"))
        return 0 if ok else 1
    if a.fingerprint:
        fingerprint(a.fingerprint, a)
        return 0
    if a.compare:
        if len(a.compare) < 2:
            sys.exit("⛔ --compare ต้องมีอย่างน้อย ref.pt mrg.pt (ควรใส่ base.pt ด้วย)")
        return 0 if compare(a.compare[0], a.compare[1],
                            a.compare[2] if len(a.compare) > 2 else None) else 1
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
