#!/usr/bin/env python3
"""
soup_safetensors.py — รวม LoRA adapter หลาย fold เป็น "destrier" ด้วยเลขล้วน ๆ

ทำไมไม่ใช้ PEFT add_weighted_adapter (merge_adapters_soup.py):
  Qwen3.6-MoE ต้องใช้ LoRA แบบ target_parameters (mlp.experts.*) ซึ่ง PEFT อนุญาต
  ให้มี adapter แบบนั้นได้ **ตัวเดียวต่อโมเดล** → โหลด fold ที่ 2 ปุ๊บ ValueError ทันที
  (เจอจริง 2026-08-31 ตอนรัน merge k=3) ⇒ ต้องบวกเทนเซอร์เองโดยไม่ต้องมีโมเดล

สมการที่ใช้ — ต่อแกน rank ให้ได้ ΔW = (1/k)·Σ ΔW_i **เป๊ะ ไม่มีพจน์ไขว้**:
  A_รวม = [A_1; A_2; …]  (ต่อแกน r)   B_รวม = (1/k)·[B_1 | B_2 | …]
  ⇒ B_รวม·A_รวม = (1/k)·Σ B_i A_i     r: 16 → k·16   alpha: ×k (ให้ scaling คงเดิม)
  ชั้น MoE เก็บเป็น (E·r) จึงต้อง reshape เป็น (E, r, ·) ก่อนต่อ แล้ว flatten กลับ

ทำไมไม่เฉลี่ยน้ำหนัก A/B ตรง ๆ (A=(1/√k)ΣA_i, B=(1/√k)ΣB_i — เวอร์ชันแรกของไฟล์นี้):
  ได้ ΔW = (1/k)Σ_ij B_i A_j คือมีพจน์ไขว้ B_i·A_j (i≠j) ปนมา ซึ่งจะหักล้างกันเอง
  ก็ต่อเมื่อ adapter แต่ละ fold เกือบตั้งฉากกัน — **วัดจริงแล้วไม่ใช่**: fold ทั้งสาม
  ชี้ทางเดียวกันเกือบสนิท (มาจาก base+seed เดียวกัน) พจน์ไขว้เลยบวกทบ
  วัดได้ ‖ΔW‖ เกินจริง 3.0 เท่าที่ชั้น attn และ 16.3 เท่าที่ชั้น MoE

ข้อแลกของวิธี exact: ไฟล์ใหญ่ขึ้น k เท่า และตอน serve ต้องตั้ง max_lora_rank ≥ k·16

รัน:
    python soup_safetensors.py --folds 0 2 3            # เซฟลงเครื่อง ./destrier_local
    python soup_safetensors.py --folds 0 2 3 --push     # อัปขึ้น dacarokann/destrier
"""
import argparse
import json
import os
import shutil
import sys

import torch
from huggingface_hub import HfApi, snapshot_download
from safetensors.torch import load_file, save_file

FOLD_REPO = "dacarokann/Courser_{}"
LETTERS = "abcd"
OUT_REPO = "dacarokann/destrier"
OUT_DIR = "./destrier_local"
# ไฟล์ประกอบที่ต้องติดไปด้วย ไม่งั้นโหลด processor ไม่ได้
SIDECAR = ["adapter_config.json", "chat_template.jinja", "tokenizer.json",
           "tokenizer_config.json", "special_tokens_map.json", "preprocessor_config.json",
           "added_tokens.json", "vocab.json", "merges.txt"]


def expert_delta_e0(A, B, r):
    """ΔW ของ expert ตัวแรก ตาม peft ParamWrapper.get_delta_weight
       A (E·r, X) → (E, r, X) ; B (Y, E·r) → (Y, r, E) ; einsum('o r e, e r i -> e i o')"""
    E = A.shape[0] // r
    a0 = A.float().reshape(E, r, A.shape[-1])[0]          # (r, X)
    b0 = B.float().reshape(B.shape[0], r, E)[..., 0]      # (Y, r)
    return a0.T @ b0.T                                     # (X, Y)


def convert_expert_pair(A, B, r):
    """สลับข้างการแยกตัวประกอบของชั้น MoE ให้ตรงอีก convention หนึ่งของ peft — **ไม่เสียข้อมูล**
       ต้องการ new[e,p,q] == old[e,p,q] จาก einsum เดิม ⇒ A' = permute(B), B' = permute(A)
         A'[e,r,q] := B[q,r,e]   และ   B'[p,r,e] := A[e,r,p]
       (พิสูจน์จาก source peft 0.18.1 layer.py get_delta_weight — ไม่ใช่การเดารูปร่าง)"""
    E = A.shape[0] // r
    X, Y = A.shape[-1], B.shape[0]
    A2 = B.reshape(Y, r, E).permute(2, 1, 0).reshape(E * r, Y).contiguous()
    B2 = A.reshape(E, r, X).permute(2, 1, 0).reshape(X, E * r).contiguous()
    return A2, B2


def diagnose(sds, merged, r, r_merged):
    """เช็คว่าพจน์ไขว้ไม่ได้กลบของจริง: ‖ΔW_รวม‖ ควรใกล้ ‖ค่าเฉลี่ย ΔW‖
       ตรวจทั้งชั้น attn ธรรมดา และชั้น MoE (ชั้นที่เพิ่งแปลง — ความเสี่ยงอยู่ตรงนี้)"""
    ok = True
    for label, want_expert in (("attn", False), ("MoE expert", True)):
        key_a = next((k for k in merged if k.endswith("lora_A.weight")
                      and ("experts" in k) == want_expert), None)
        if key_a is None:
            continue
        key_b = key_a[: -len("lora_A.weight")] + "lora_B.weight"
        if want_expert:
            f = lambda sd, rr: expert_delta_e0(sd[key_a], sd[key_b], rr)
        else:
            f = lambda sd, rr: sd[key_b].float() @ sd[key_a].float()
        true_avg = sum(f(sd, r) for sd in sds) / len(sds)
        got = f(merged, r_merged)
        ratio = (got.norm() / true_avg.norm()).item()
        print(f"\nตรวจ {label}: {key_a.split('language_model.')[-1]}")
        print(f"   ‖ΔW เฉลี่ยจริง‖ = {true_avg.norm():.4f}")
        print(f"   ‖ΔW ที่รวมได้‖ = {got.norm():.4f}   อัตราส่วน {ratio:.3f}")
        # ต่อแกน rank เป็นการรวมแบบ exact → ต้องได้ 1.000 ไม่ใช่ "พอรับได้"
        if abs(ratio - 1.0) > 0.02:
            print("   ⚠️  ไม่เท่ากับ 1.000 — การต่อแกนผิด อย่าเชื่อ adapter นี้")
            ok = False
        else:
            print("   ✅ ตรงกับค่าเฉลี่ยจริง")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", nargs="+", type=int, required=True)
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--out", default=OUT_REPO)
    args = ap.parse_args()

    if args.push and not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")):
        raise SystemExit("⛔ --push ต้องมี HF_TOKEN")

    repos = [FOLD_REPO.format(LETTERS[k]) for k in args.folds]
    k = len(repos)
    print(f"รวม {k} fold — ต่อแกน rank แบบ exact: ΔW = (1/{k})·Σ ΔW_i")

    # โหลดจาก HF ไม่ใช่จากดิสก์: ได้ตรวจไปในตัวว่าไฟล์บน HF ใช้งานได้จริง (Day of Shame)
    dirs = []
    for r in repos:
        print(f"   ดึง {r} …", flush=True)
        dirs.append(snapshot_download(r, allow_patterns=["*.json", "*.safetensors", "*.jinja",
                                                         "*.txt", "*.model"]))

    sds = [load_file(os.path.join(d, "adapter_model.safetensors")) for d in dirs]
    rank = json.load(open(os.path.join(dirs[0], "adapter_config.json")))["r"]

    keys = set(sds[0])
    for i, sd in enumerate(sds[1:], 1):
        if set(sd) != keys:
            raise SystemExit(f"⛔ {repos[i]} คีย์ไม่ตรงกับ {repos[0]} — หยุด ไม่รวมมั่ว")

    # peft สอง version แยกตัวประกอบชั้น MoE คนละข้าง (ดู rule_of_tune บทที่ 18)
    # เลือก convention ของกลุ่มที่มี fold มากที่สุด แล้วแปลงกลุ่มน้อยให้ตรง — แปลงแบบไม่เสียข้อมูล
    ekeys = sorted(k for k in keys if "experts" in k and k.endswith("lora_A.weight"))
    sig = [tuple(sd[ekeys[0]].shape) for sd in sds]
    ref = max(set(sig), key=sig.count)
    if len(set(sig)) > 1:
        print(f"   ⚠️  fold แยกตัวประกอบ MoE คนละข้าง: {dict(zip(repos, sig))}")
        print(f"   → ใช้ convention {ref} (กลุ่มมากสุด) แปลงที่เหลือให้ตรง")
    for i, sd in enumerate(sds):
        if sig[i] == ref:
            continue
        for j, ka in enumerate(ekeys):
            kb = ka[: -len("lora_A.weight")] + "lora_B.weight"
            before = expert_delta_e0(sd[ka], sd[kb], rank) if j == 0 else None
            sd[ka], sd[kb] = convert_expert_pair(sd[ka], sd[kb], rank)
            if j == 0:  # พิสูจน์ว่าแปลงแล้ว ΔW ตัวเดิมเป๊ะ ไม่ใช่แค่รูปร่างลงล็อก
                after = expert_delta_e0(sd[ka], sd[kb], rank)
                d = (before - after.T).abs().max().item()
                print(f"      ตรวจการแปลง: max|ΔW เดิม − ΔW ใหม่ᵀ| = {d:.2e}")
                if d > 1e-3:
                    raise SystemExit("⛔ การแปลงไม่รักษา ΔW — หยุด")
        print(f"      แปลง {repos[i]} แล้ว {len(ekeys)} คู่")

    for i, sd in enumerate(sds[1:], 1):
        for key in keys:
            if sd[key].shape != sds[0][key].shape:
                raise SystemExit(f"⛔ {repos[i]} รูปร่าง {key} ไม่ตรง (หลังแปลงแล้ว) — หยุด")
    print(f"   คีย์+รูปร่างตรงกันครบ {len(keys)} เทนเซอร์")

    merged = {}
    for key in keys:
        ts = [sd[key].float() for sd in sds]
        expert = "experts" in key
        if key.endswith("lora_A.weight"):
            if expert:  # (E·r, X) → (E, r, X) ต่อแกน r → (E, k·r, X)
                E, X = ts[0].shape[0] // rank, ts[0].shape[-1]
                m = torch.cat([t.reshape(E, rank, X) for t in ts], dim=1).reshape(E * rank * k, X)
            else:       # (r, in) → (k·r, in)
                m = torch.cat(ts, dim=0)
        elif key.endswith("lora_B.weight"):
            # 1/k อยู่ฝั่ง B ฝั่งเดียว → B_catA_cat = (1/k)Σ B_i A_i เป๊ะ
            if expert:  # (Y, E·r) → (Y, r, E) ต่อแกน r → (Y, k·r, E)
                Y, E = ts[0].shape[0], ts[0].shape[-1] // rank
                m = torch.cat([t.reshape(Y, rank, E) for t in ts], dim=1).reshape(Y, E * rank * k) / k
            else:       # (out, r) → (out, k·r)
                m = torch.cat(ts, dim=1) / k
        else:
            raise SystemExit(f"⛔ คีย์ที่ไม่รู้จัก {key} — หยุด ไม่เดา")
        merged[key] = m.to(sds[0][key].dtype)
    rank_new = rank * k
    print(f"   ต่อแกน rank แบบ exact: r {rank} → {rank_new} ({len(keys)} เทนเซอร์)")
    print(f"   ΔW = (1/{k})·Σ ΔW_i เป๊ะ ไม่มีพจน์ไขว้ (ต่างจากการเฉลี่ยน้ำหนัก A/B ตรง ๆ)")

    ok = diagnose(sds, merged, rank, rank_new)

    os.makedirs(OUT_DIR, exist_ok=True)
    save_file(merged, os.path.join(OUT_DIR, "adapter_model.safetensors"),
              metadata={"format": "pt"})
    # เอา config/tokenizer จาก fold ที่อยู่ใน convention อ้างอิง ไม่ใช่ dirs[0] เสมอไป
    ref_dir = dirs[sig.index(ref)]
    for f in SIDECAR:
        src = os.path.join(ref_dir, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT_DIR, f))
    cfg_path = os.path.join(OUT_DIR, "adapter_config.json")
    cfg = json.load(open(cfg_path))
    # alpha ต้องโตตาม r ไม่งั้น scaling = alpha/r เปลี่ยน → ΔW ผิดสเกลทั้งตัว
    cfg["lora_alpha"] = cfg["lora_alpha"] * k
    cfg["r"] = rank_new
    json.dump(cfg, open(cfg_path, "w"), indent=2)
    print(f"   r={cfg['r']} alpha={cfg['lora_alpha']} (scaling {cfg['lora_alpha']/cfg['r']:.1f} เท่าเดิม)")
    open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8").write(
        f"""---
base_model: {cfg.get('base_model_name_or_path')}
library_name: peft
tags: [lora, model-soup, k-fold]
---

# destrier

LoRA soup ของ {k} fold: {', '.join(repos)}

`ΔW = (1/{k})·Σ ΔW_i` **เป๊ะ** — ต่อแกน rank (r {rank} → {rank_new}, alpha โตตามให้ scaling คงเดิม)
ไม่ใช่การเฉลี่ยน้ำหนัก A/B ตรง ๆ ซึ่งจะมีพจน์ไขว้ `B_i·A_j` ปนมา (วัดได้จริงว่าทบเป็น {k}-16 เท่า)

ใช้ PEFT `add_weighted_adapter` ไม่ได้: MoE `target_parameters` โหลดได้ตัวเดียวต่อโมเดล
อนุมาน: ตอน serve ต้องตั้ง `max_lora_rank` ≥ {rank_new}
""")

    if not ok:
        raise SystemExit("⛔ ตรวจไม่ผ่าน — เซฟลงเครื่องไว้แล้วแต่ไม่อัป")

    if args.push:
        HfApi().upload_folder(folder_path=OUT_DIR, repo_id=args.out, repo_type="model")
        print(f"\n✅ อัปแล้ว → https://huggingface.co/{args.out}")
        print("   ต่อไป: ตรวจ Day of Shame ให้ครบ **ก่อน** destroy การ์ด")
    else:
        print(f"\n✅ เซฟ → {OUT_DIR} (ใส่ --push เพื่ออัป)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
