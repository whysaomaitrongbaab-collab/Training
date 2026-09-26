#!/usr/bin/env python3
"""
soup_safetensors.py — รวม LoRA adapter หลาย fold เป็น "destrier" ด้วยเลขล้วน ๆ

🔴 แก้ 2026-09-27: รุ่นก่อนหน้า (ที่สร้าง dacarokann/destrier rev e229403 เมื่อ 31 ส.ค.) ต่อ lora_B
ของ MoE expert ผิด — อ่านเป็น rank_major (แบบ PEFT) ทั้งที่ fold เทรนด้วย Unsloth ที่เก็บเป็น
grouped_by_expert และ convert_expert_pair ก็อ่านผิดแบบเดียวกัน ⇒ ตอนเสิร์ฟ expert แต่ละตัวได้ชิ้นส่วน
ถูกคู่แค่ 17/12288 · ด่านตรวจเดิมอ่านด้วยแบบผิดเดียวกันจึงผ่านทุกครั้ง (หลักฐาน + วิธีซ่อมตัวเดิม:
t05_Destrier/proof/03_destrier_expert_LoRA_ปนผิด.md และ fix_destrier_layout.py)

ทำไมไม่ใช้ PEFT add_weighted_adapter (merge_adapters_soup.py):
  Qwen3.6-MoE ต้องใช้ LoRA แบบ target_parameters (mlp.experts.*) ซึ่ง PEFT อนุญาต
  ให้มี adapter แบบนั้นได้ **ตัวเดียวต่อโมเดล** → โหลด fold ที่ 2 ปุ๊บ ValueError ทันที
  (เจอจริง 2026-08-31 ตอนรัน merge k=3) ⇒ ต้องบวกเทนเซอร์เองโดยไม่ต้องมีโมเดล

สมการที่ใช้ — ต่อแกน rank ให้ได้ ΔW = (1/k)·Σ ΔW_i **เป๊ะ ไม่มีพจน์ไขว้**:
  A_รวม = [A_1; A_2; …]  (ต่อแกน r)   B_รวม = (1/k)·[B_1 | B_2 | …]
  ⇒ B_รวม·A_รวม = (1/k)·Σ B_i A_i     r: 16 → k·16   alpha: ×k (ให้ scaling คงเดิม)
  ชั้น MoE ต้องต่อแกน r **ภายใน expert เดียวกัน** — layout ของเมทริกซ์แบนสำคัญที่สุด:
    lora_A (E·r, in)  expert-major เสมอ:     แถว e·r + q        = expert e rank q
    lora_B (out, E·r) grouped_by_expert:     คอลัมน์ e·r + q    = expert e rank q   ← Unsloth ≤ zoo 2026.9.5
                      rank_major:            คอลัมน์ q·E + e    = expert e rank q   ← PEFT / zoo ≥ 2026.9.6 default
  รูปร่างเท่ากันเป๊ะทั้งสองแบบ → อ่านผิดแบบไม่มี error มีแต่ผลเพี้ยนเงียบๆ
  layout ของ fold: **วัดจากตัวเลขเอง** (detect_layout) แล้วเทียบกับคีย์ lora_B_layout ใน adapter_config
  ถ้ามี — ไม่มีคีย์ไม่ใช่หลักฐานว่าเป็น grouped (PEFT load→save ทิ้งคีย์ที่ไม่รู้จัก, zoo กลืน error ตอนเขียน)
  วัดไม่ชัด / ขัดกับคีย์ = หยุด ไม่เดา
  ด้านการแยกตัวประกอบ (rule_of_tune บทที่ 18): ตัดสินจากรูปร่างเทนเซอร์เทียบขนาดของ base (fold_orientation)
  peft_version ใช้ตรวจทาน (≤ 0.18 สลับ · ≥ 0.19.1 ปกติ) — ผลลัพธ์เป็นด้านปกติเสมอ (ตัวเสิร์ฟบังคับ peft ≥ 0.20)
  สคริปต์นี้แปลงทุก fold เป็น grouped_by_expert ด้านปกติก่อนต่อ แล้วประกาศ lora_B_layout ในผลลัพธ์
  ⇒ เสิร์ฟด้วย UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert (SERVE_ENV ใน presentation.py)

ด่านตรวจ (check_soup) เทียบกับค่าอ้างอิงที่คำนวณจากเทนเซอร์ **ดิบ** ของทุก fold ก่อนโค้ดรวมแตะอะไร ด้วยตัวอ่าน
ที่เขียนแยกจากโค้ดแปลง (served_probe ตามวิธีที่ Unsloth คูณจริงของแต่ละด้าน/layout) — รุ่นแรกของวันที่ 27
เทียบกับ fold ที่โค้ดรวมแปลงไปแล้ว จึงจับบั๊กในขั้นแปลงไม่ได้ (รีวิวอิสระ 27 ก.ย.)

ทำไมไม่เฉลี่ยน้ำหนัก A/B ตรง ๆ (A=(1/√k)ΣA_i, B=(1/√k)ΣB_i — เวอร์ชันแรกของไฟล์นี้):
  ได้ ΔW = (1/k)Σ_ij B_i A_j คือมีพจน์ไขว้ B_i·A_j (i≠j) ปนมา ซึ่งจะหักล้างกันเอง
  ก็ต่อเมื่อ adapter แต่ละ fold เกือบตั้งฉากกัน — **วัดจริงแล้วไม่ใช่**: fold ทั้งสาม
  ชี้ทางเดียวกันเกือบสนิท (มาจาก base+seed เดียวกัน) พจน์ไขว้เลยบวกทบ

ข้อแลกของวิธี exact: ไฟล์ใหญ่ขึ้น k เท่า และตอน serve ต้องตั้ง max_lora_rank ≥ k·16

รัน:
    python soup_safetensors.py --folds 0 2 3            # เซฟลงเครื่อง ./destrier_local
    python soup_safetensors.py --folds 0 2 3 --push     # อัปขึ้น repo (ดู --out) — อย่าทับ destrier เดิม
    python test_soup_layout.py                          # ตรวจสูตรด้วยตัวเลขสังเคราะห์ (ไม่ใช้เน็ต)
"""
import argparse
import json
import os
import shutil
import sys

import torch

FOLD_REPO = "dacarokann/Courser_{}"
LETTERS = "abcd"
OUT_REPO = "dacarokann/destrier-v2"     # ห้ามทับ dacarokann/destrier เดิม — เก็บไว้ย้อนดูได้
OUT_DIR = "./destrier_local"
# ไฟล์ประกอบที่ต้องติดไปด้วย ไม่งั้นโหลด processor ไม่ได้
SIDECAR = ["adapter_config.json", "chat_template.jinja", "tokenizer.json",
           "tokenizer_config.json", "special_tokens_map.json", "preprocessor_config.json",
           "added_tokens.json", "vocab.json", "merges.txt"]
GROUPED, RANK_MAJOR = "grouped_by_expert", "rank_major"
CANON, REVERSED = "canonical", "reversed"
# ต้องเท่ากันทุก fold — ไม่งั้น scaling ของแต่ละ fold ต่างกันแล้วถูกกลบด้วย alpha ของ fold อ้างอิงตัวเดียว
SAME_CFG = ("r", "lora_alpha", "use_rslora", "rank_pattern", "alpha_pattern",
            "target_parameters", "target_modules", "base_model_name_or_path")
# วัดบน Courser_a..d จริง 27 ก.ย. (ชั้น 0/20/39 × 2 คีย์ = 24 เทนเซอร์): แบบที่ถูก 0.44-0.96 · แบบที่ผิด 0.04-0.09
# (chance ≈ (E-1)/(E·r-1) = 0.062) · ต่ำสุด 0.44 คือชั้น 0 ของ fold ด้านสลับ — ตัดสินด้วย median ทุกคีย์ ไม่ใช่รายคีย์
ETA_HI, ETA_LO = 0.4, 0.2


def is_expert(key):
    return ".experts." in key


def b_key(ka):
    return ka[: -len("lora_A.weight")] + "lora_B.weight"


def peft_orientation(cfg):
    """ด้านที่ peft_version บอก (ใช้แค่ตรวจทาน ตัวตัดสินจริงคือรูปร่าง ดู fold_orientation)
    ≤ 0.18 = สลับ · ≥ 0.19.1 = ปกติ (0.19.1 เปลี่ยนเงื่อนไขเป็น ndim==3 and not is_transposed เหมือน 0.20 —
    รีวิวรอบสอง 27 ก.ย. อ่านจาก wheel จริง) · 0.19.0 ขึ้นกับ is_transposed ของโมเดล = ไม่ชี้ขาด (None)"""
    v = str(cfg.get("peft_version") or "")
    try:
        parts = [int(x) for x in v.split(".")[:3] if x.isdigit()]
        ver = tuple(parts + [0] * (3 - len(parts)))[:3]
        if len(parts) < 2:
            return None
    except ValueError:
        return None
    if ver >= (0, 19, 1):
        return CANON
    return None if ver[:2] == (0, 19) else REVERSED


def valid_io(base_cfg):
    """(in, out) ที่เป็นไปได้ของชั้น MoE จาก config ของ base: gate_up hidden→2·moe_inter · down moe_inter→hidden"""
    t = base_cfg.get("text_config") or base_cfg
    h, i = t["hidden_size"], t["moe_intermediate_size"]
    return {(h, 2 * i), (i, h)}


def fold_orientation(cfg, sd, valid, name="fold"):
    """ด้านที่ fold เก็บ — ตัดสินจากรูปร่างเทนเซอร์เทียบกับขนาดจริงของ base (ข้อมูล ไม่ใช่ป้าย)
    แล้วต้องไม่ขัดกับ peft_version ในกรณีที่เลขรุ่นชี้ขาดได้ · กำกวม/ขัดกัน/ปนกันในไฟล์เดียว = หยุด"""
    got = set()
    for ka in (k for k in sd if is_expert(k) and k.endswith("lora_A.weight")):
        A, B = sd[ka], sd[b_key(ka)]
        canon, rev = (A.shape[1], B.shape[0]) in valid, (B.shape[0], A.shape[1]) in valid
        if canon == rev:
            raise SystemExit(f"⛔ {name}: {ka} รูปร่าง A{tuple(A.shape)} B{tuple(B.shape)} ตัดสินด้านไม่ได้"
                             f" (ขนาดที่ถูกต้อง {sorted(valid)}) — หยุด")
        got.add(CANON if canon else REVERSED)
    if len(got) > 1:
        raise SystemExit(f"⛔ {name}: บางคีย์ด้านปกติ บางคีย์ด้านสลับ — หยุด")
    o = got.pop() if got else CANON
    rule = peft_orientation(cfg)
    if rule and rule != o:
        raise SystemExit(f"⛔ {name}: รูปร่างบอก {o} แต่ peft_version={cfg.get('peft_version')} บอก {rule} — หยุด")
    return o


def eta2(x, groups, n_groups):
    """สัดส่วน variance ของ x ที่อธิบายได้ด้วยการจัดกลุ่ม (0 = ไม่เกี่ยว, 1 = กลุ่มอธิบายหมด)"""
    x = x.double()
    total = ((x - x.mean()) ** 2).sum()
    cnt = torch.bincount(groups, minlength=n_groups).double()
    means = torch.bincount(groups, weights=x, minlength=n_groups) / cnt.clamp_min(1)
    between = (cnt * (means - x.mean()) ** 2).sum()
    return (between / total.clamp_min(1e-30)).item()


def detect_layout(B, r):
    """วัด layout ของ lora_B (?, E·r) จากตัวเลข: expert แต่ละตัวมีขนาดคอลัมน์ต่างกัน → จัดกลุ่มคอลัมน์ถูกแบบ
    แล้ว log(norm) ของคอลัมน์จะจับกลุ่มกันชัด · คืน (layout หรือ None ถ้ากำกวม, eta_grouped, eta_rank_major)"""
    n = B.shape[1]
    e_num = n // r
    lognorm = B.float().norm(dim=0).clamp_min(1e-30).log()
    j = torch.arange(n)
    eg, er = eta2(lognorm, j // r, e_num), eta2(lognorm, j % e_num, e_num)
    if eg >= ETA_HI and er <= ETA_LO:
        return GROUPED, eg, er
    if er >= ETA_HI and eg <= ETA_LO:
        return RANK_MAJOR, eg, er
    return None, eg, er


def fold_layout(cfg, sd, rank, name="fold", log=print):
    """layout ของ lora_B ใน fold นี้ — ตัดสินจากตัวเลข (median ของทุกคีย์ expert) + ต้องไม่ขัดกับคีย์ที่ประกาศ"""
    ekeys = [k for k in sd if is_expert(k) and k.endswith("lora_A.weight")]
    if not ekeys:
        return GROUPED              # ไม่มี expert LoRA = ไม่มีอะไรให้ layout ผิด
    votes = [detect_layout(sd[b_key(ka)], rank) for ka in ekeys]
    eg = sorted(v[1] for v in votes)[len(votes) // 2]
    er = sorted(v[2] for v in votes)[len(votes) // 2]
    data = GROUPED if (eg >= ETA_HI and er <= ETA_LO) else RANK_MAJOR if (er >= ETA_HI and eg <= ETA_LO) else None
    declared = cfg.get("lora_B_layout")
    if declared not in (None, GROUPED, RANK_MAJOR):
        raise SystemExit(f"⛔ {name}: lora_B_layout={declared!r} ไม่รู้จัก — หยุด ไม่เดา")
    nested = {p.get("lora_B_layout") for p in
              ((cfg.get("unsloth_fused_expert_lora") or {}).get("parameters") or {}).values()
              if isinstance(p, dict) and p.get("lora_B_layout")}
    log(f"   {name}: วัดได้ eta grouped={eg:.2f} rank_major={er:.2f} → {data or 'กำกวม'}"
        f" · ประกาศ {declared or '<ไม่มีคีย์>'}{' · nested ' + str(sorted(nested)) if nested else ''}")
    if data is None:
        raise SystemExit(f"⛔ {name}: วัด layout ของ lora_B จากตัวเลขไม่ชัด — ไม่รวม (ต้องมีคนดูก่อน)")
    if declared and declared != data:
        raise SystemExit(f"⛔ {name}: ประกาศ {declared} แต่ตัวเลขเป็น {data} — ไม่รวม")
    if nested and nested != {data}:
        raise SystemExit(f"⛔ {name}: nested layout {sorted(nested)} ขัดกับตัวเลข {data} — ไม่รวม")
    # median ตัดสินทั้งไฟล์ แต่คีย์ไหนวัดได้ชัดว่าตรงข้าม = fold ปนสองแบบ (zoo ≥ 9.6 รายงาน 'mixed' ได้) — หยุด
    opposite = [ka for ka, (lay, _, _) in zip(ekeys, votes) if lay not in (None, data)]
    if opposite:
        raise SystemExit(f"⛔ {name}: {len(opposite)} คีย์วัดได้ชัดว่าเป็นอีกแบบ (เช่น {opposite[0]}) — fold ปน layout ไม่รวม")
    return data


def b_to_grouped(B, r, layout):
    """lora_B (?, E·r) → grouped_by_expert (คอลัมน์ e·r+q)"""
    if layout == GROUPED:
        return B
    y, n = B.shape
    return B.reshape(y, r, n // r).permute(0, 2, 1).reshape(y, n).contiguous()


def b_from_grouped(B, r, layout):
    """grouped_by_expert → layout ที่ขอ (ใช้ตอนอ่านแบบอื่นเพื่อทดสอบ/แปลงออก)"""
    if layout == GROUPED:
        return B
    y, n = B.shape
    return B.reshape(y, n // r, r).permute(0, 2, 1).reshape(y, n).contiguous()


def swap_orientation(A, B):
    """สลับด้านการแยกตัวประกอบของชั้น MoE (peft 0.18.1 → ≥ 0.20) สำหรับ layout grouped_by_expert — ไม่เสียข้อมูล

    ด้านสลับ (peft 0.18.1): A0o (E·r, out) · B0o (in, E·r) — Unsloth คำนวณ x @ B0o_e @ A0o_e
    ด้านปกติ (peft ≥ 0.20): A (E·r, in) · B (out, E·r)    — Unsloth คำนวณ x @ A_eᵀ @ B_eᵀ
    ⇒ A = B0oᵀ และ B = A0oᵀ (แถว/คอลัมน์ e·r+q ยังเป็น expert e rank q ทั้งคู่)
    ⚠️ ต้องแปลง layout เป็น grouped **ก่อน** สลับ (lora_B ของ fold ด้านสลับคือ B0o)
    ⚠️ รุ่นก่อน 27 ก.ย. ทำด้วย reshape(Y, r, E) = อ่าน grouped เป็น rank_major → expert ปนกัน"""
    return B.T.contiguous(), A.T.contiguous()


def served_probe(A, B, r, layout, orient, u, v):
    """uᵀ·ΔW_e·v ของทุก expert ตามที่ตัวเสิร์ฟคูณจริง — **เขียนแยกจากโค้ดแปลง** (ไม่เรียก
    b_to_grouped/swap_orientation) · คืน (E, m, n) · u (out, m) · v (in, n)"""
    A, B = A.double(), B.double()
    e_num = A.shape[0] // r
    cols = (B.reshape(B.shape[0], e_num, r).permute(1, 0, 2) if layout == GROUPED     # (E, ?, r)
            else B.reshape(B.shape[0], r, e_num).permute(2, 0, 1))
    rows = A.reshape(e_num, r, A.shape[1])                                            # (E, r, ?)
    if orient == CANON:     # ΔW_e = cols_e @ rows_e  (out, in)
        return u.T @ (cols @ (rows @ v))
    # ด้านสลับ: x @ cols_e (in, r) @ rows_e (r, out) ⇒ ΔW_e = rows_eᵀ @ cols_eᵀ
    return u.T @ (rows.transpose(1, 2) @ (cols.transpose(1, 2) @ v))


def io_dims(A, B, orient):
    """(in, out) ของชั้น MoE ตามด้านที่ fold เก็บ — ด้านสลับ: A0o (E·r, out) · B0o (in, E·r)"""
    return (B.shape[0], A.shape[1]) if orient == REVERSED else (A.shape[1], B.shape[0])


def reference_probes(sds, layouts, orients, rank, m=4, n=4, seed=0):
    """ค่าอ้างอิง uᵀ(ΔW เฉลี่ยของทุก fold)v ต่อคีย์ — คำนวณจากเทนเซอร์ดิบ **ก่อน** merge_folds แตะ sds
    เก็บแค่ผล probe (E×m×n ต่อคีย์) ไม่เก็บสำเนาเทนเซอร์"""
    g = torch.Generator().manual_seed(seed)
    ref = {}
    for ka in sorted(sds[0]):
        if not ka.endswith("lora_A.weight"):
            continue
        kb = b_key(ka)
        dims = {io_dims(sd[ka], sd[kb], o) if is_expert(ka) else (sd[ka].shape[1], sd[kb].shape[0])
                for sd, o in zip(sds, orients)}
        if len(dims) != 1:
            raise SystemExit(f"⛔ {ka}: in/out ของแต่ละ fold ไม่ตรงกัน {sorted(dims)} — หยุด")
        d_in, d_out = dims.pop()
        u = torch.randn(d_out, m, generator=g, dtype=torch.float64)
        v = torch.randn(d_in, n, generator=g, dtype=torch.float64)
        if is_expert(ka):
            truth = sum(served_probe(sd[ka], sd[kb], rank, lay, o, u, v)
                        for sd, lay, o in zip(sds, layouts, orients)) / len(sds)
        else:
            truth = sum(u.T @ (sd[kb].double() @ (sd[ka].double() @ v)) for sd in sds) / len(sds)
        ref[ka] = (u, v, truth)
    return ref


def merge_folds(sds, layouts, orients, rank, log=print):
    """คืน dict ของ adapter ที่ต่อแกน rank แล้ว (grouped_by_expert ด้านปกติ) — แก้ sds ในที่"""
    k = len(sds)
    keys = sorted(sds[0])
    ekeys = [key for key in keys if is_expert(key) and key.endswith("lora_A.weight")]
    # 1) layout ก่อน (lora_B ตามที่เก็บ) แล้วค่อยสลับด้าน — กลับลำดับ = expert ปนกันสำหรับ fold ด้านสลับ+rank_major
    for i, (sd, lay, o) in enumerate(zip(sds, layouts, orients)):
        if lay != GROUPED:
            for ka in ekeys:
                sd[b_key(ka)] = b_to_grouped(sd[b_key(ka)], rank, lay)
            log(f"      fold {i}: แปลง lora_B {lay} → {GROUPED} ({len(ekeys)} เทนเซอร์)")
        # 2) ผลลัพธ์ด้านปกติเสมอ (ตัวเสิร์ฟบังคับ peft ≥ 0.20) — ไม่ใช้เสียงข้างมาก (เสมอกัน = ขึ้นกับลำดับ --folds)
        if o == REVERSED:
            for ka in ekeys:
                sd[ka], sd[b_key(ka)] = swap_orientation(sd[ka], sd[b_key(ka)])
            log(f"      fold {i}: ด้านสลับ → ด้านปกติ {len(ekeys)} คู่")
    for i, sd in enumerate(sds[1:], 1):
        for key in keys:
            if sd[key].shape != sds[0][key].shape:
                raise SystemExit(f"⛔ fold {i} รูปร่าง {key} ไม่ตรง (หลังแปลงแล้ว) — หยุด")
    # 3) ต่อแกน r
    merged = {}
    for key in keys:
        # คำนวณอย่างน้อย fp32 (bf16 → fp32) แต่ไม่ลดของที่ละเอียดกว่า (fp64 ในเทสคงเดิม)
        ts = [sd[key].to(torch.promote_types(sd[key].dtype, torch.float32)) for sd in sds]
        expert = is_expert(key)
        if key.endswith("lora_A.weight"):
            if expert:  # (E·r, X) → (E, r, X) ต่อแกน r ภายใน expert → (E·k·r, X)
                e_num, x = ts[0].shape[0] // rank, ts[0].shape[-1]
                m = torch.cat([t.reshape(e_num, rank, x) for t in ts], dim=1).reshape(e_num * rank * k, x)
            else:       # (r, in) → (k·r, in)
                m = torch.cat(ts, dim=0)
        elif key.endswith("lora_B.weight"):
            # 1/k อยู่ฝั่ง B ฝั่งเดียว → B_catA_cat = (1/k)Σ B_i A_i เป๊ะ
            if expert:  # grouped (Y, E·r) → (Y, E, r) ต่อแกน r ภายใน expert → (Y, E·k·r)
                y, e_num = ts[0].shape[0], ts[0].shape[-1] // rank
                m = torch.cat([t.reshape(y, e_num, rank) for t in ts], dim=2).reshape(y, e_num * rank * k) / k
            else:       # (out, r) → (out, k·r)
                m = torch.cat(ts, dim=1) / k
        else:
            raise SystemExit(f"⛔ คีย์ที่ไม่รู้จัก {key} — หยุด ไม่เดา")
        merged[key] = m     # อย่างน้อย fp32 — B/k ปัดใน bf16 คลาด ~2e-3 แล้วด่านปฏิเสธ soup ที่ถูก (รีวิวรอบสอง)
    return merged


def check_soup(ref, merged, rank_new, log=print):
    """soup อ่านแบบตัวเสิร์ฟ (grouped ด้านปกติ) ต้องเท่ากับค่าอ้างอิงจาก fold ดิบ **ทุก expert ทุกคีย์**
    + ตัวคุม: อ่าน soup แบบ rank_major ต้อง "ไม่ผ่าน" — ถ้าผ่านทั้งสองแบบ ด่านแยกไม่ออก ถือว่าไม่ผ่าน"""
    ok, worst, control = True, 0.0, float("inf")
    for ka, (u, v, truth) in ref.items():
        kb = b_key(ka)
        got = served_probe(merged[ka], merged[kb], rank_new, GROUPED, CANON, u, v) if is_expert(ka) \
            else u.T @ (merged[kb].double() @ (merged[ka].double() @ v))
        err = ((got - truth).norm() / truth.norm().clamp_min(1e-30)).item()
        worst = max(worst, err)
        if is_expert(ka):
            wrong = served_probe(merged[ka], merged[kb], rank_new, RANK_MAJOR, CANON, u, v)
            control = min(control, ((wrong - truth).norm() / truth.norm().clamp_min(1e-30)).item())
    log(f"\nตรวจ ΔW ทุกคีย์ ทุก expert เทียบค่าอ้างอิงจาก fold ดิบ (อ่านแบบตัวเสิร์ฟ grouped_by_expert):")
    log(f"   คลาดสูงสุด {worst:.2e}  ·  ตัวคุม (อ่านแบบ rank_major) คลาดต่ำสุด {control:.2f}")
    if worst > 1e-4:
        log("   ⛔ soup ไม่เท่ากับค่าเฉลี่ยของ fold — อย่าเชื่อ adapter นี้")
        ok = False
    if control < 0.5:
        log("   ⛔ ตัวคุมไม่ต่าง — ด่านนี้แยก layout ไม่ออก เชื่อผลไม่ได้")
        ok = False
    if ok:
        log("   ✅ ตรงกับค่าเฉลี่ยจริง และด่านแยก layout ออกจริง")
    return ok


def main(argv=None):
    from huggingface_hub import HfApi, snapshot_download
    from safetensors.torch import load_file, save_file

    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", nargs="+", type=int, required=True)
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--out", default=OUT_REPO)
    args = ap.parse_args(argv)

    if args.out.rstrip("/").endswith("dacarokann/destrier"):
        raise SystemExit("⛔ ห้ามทับ dacarokann/destrier เดิม (rev e229403 ตัวที่ปนผิด เก็บไว้ย้อนดู)")
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
    cfgs = [json.load(open(os.path.join(d, "adapter_config.json"), encoding="utf-8")) for d in dirs]
    for f in SAME_CFG:
        vals = [c.get(f) for c in cfgs]
        if any(v != vals[0] for v in vals):
            raise SystemExit(f"⛔ {f} ของแต่ละ fold ไม่เท่ากัน: {vals} — หยุด")
    if cfgs[0].get("use_rslora"):
        raise SystemExit("⛔ use_rslora=True — alpha×k จะไม่คง scaling (rsLoRA หาร √r) ยังไม่รองรับ")
    if cfgs[0].get("rank_pattern") or cfgs[0].get("alpha_pattern"):
        raise SystemExit("⛔ rank_pattern/alpha_pattern ไม่ว่าง — สคริปต์คูณ k ให้แค่ r/alpha หลัก ยังไม่รองรับ")
    rank = cfgs[0]["r"]
    base = cfgs[0]["base_model_name_or_path"]
    bdir = snapshot_download(base, allow_patterns=["config.json"])
    valid = valid_io(json.load(open(os.path.join(bdir, "config.json"), encoding="utf-8")))
    orients = [fold_orientation(c, sd, valid, name) for c, sd, name in zip(cfgs, sds, repos)]
    layouts = [fold_layout(c, sd, rank, name) for c, sd, name in zip(cfgs, sds, repos)]
    print(f"   ด้าน: {dict(zip(repos, orients))}")

    keys = set(sds[0])
    for i, sd in enumerate(sds[1:], 1):
        if set(sd) != keys:
            raise SystemExit(f"⛔ {repos[i]} คีย์ไม่ตรงกับ {repos[0]} — หยุด ไม่รวมมั่ว")

    ref = reference_probes(sds, layouts, orients, rank)       # ก่อน merge_folds แก้ sds ในที่
    merged = merge_folds(sds, layouts, orients, rank)
    for ka in (k_ for k_ in merged if is_expert(k_) and k_.endswith("lora_A.weight")):
        if (merged[ka].shape[1], merged[b_key(ka)].shape[0]) not in valid:
            raise SystemExit(f"⛔ ผลลัพธ์ {ka} ไม่ใช่ด้านปกติของ base {sorted(valid)} — ไม่เซฟ")
    rank_new = rank * k
    print(f"   ต่อแกน rank แบบ exact: r {rank} → {rank_new} ({len(keys)} เทนเซอร์)")

    ok = check_soup(ref, merged, rank_new)

    os.makedirs(OUT_DIR, exist_ok=True)
    save_file(merged, os.path.join(OUT_DIR, "adapter_model.safetensors"),
              metadata={"format": "pt"})
    # config/tokenizer จาก fold ด้านปกติ (ตรงกับของที่เซฟ) — ไม่มีเลยค่อยใช้ตัวแรก
    ref_dir = dirs[orients.index(CANON)] if CANON in orients else dirs[0]
    for f in SIDECAR:
        src = os.path.join(ref_dir, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT_DIR, f))
    cfg_path = os.path.join(OUT_DIR, "adapter_config.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    # alpha ต้องโตตาม r ไม่งั้น scaling = alpha/r เปลี่ยน → ΔW ผิดสเกลทั้งตัว
    cfg["lora_alpha"] = cfg["lora_alpha"] * k
    cfg["r"] = rank_new
    cfg["lora_B_layout"] = GROUPED
    # รายละเอียด nested ของ zoo ≥ 9.6 จาก fold rank_major จะขัดกับคีย์ข้างบน — ตัวแปลงที่เชื่อมันจะปน soup
    cfg.pop("unsloth_fused_expert_lora", None)
    if CANON not in orients:     # config มาจาก fold ด้านสลับ แต่เทนเซอร์ที่เซฟเป็นด้านปกติแล้ว
        cfg["peft_version"] = "0.20.0"
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), indent=2)
    print(f"   r={cfg['r']} alpha={cfg['lora_alpha']} (scaling {cfg['lora_alpha']/cfg['r']:.1f} เท่าเดิม)"
          f" · lora_B_layout={GROUPED}")
    open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8").write(
        f"""---
base_model: {cfg.get('base_model_name_or_path')}
library_name: peft
tags: [lora, model-soup, k-fold]
---

# {args.out.split('/')[-1]}

LoRA soup ของ {k} fold: {', '.join(repos)}

`ΔW = (1/{k})·Σ ΔW_i` **เป๊ะ** — ต่อแกน rank (r {rank} → {rank_new}, alpha โตตามให้ scaling คงเดิม)
lora_B ของ MoE expert เก็บแบบ **grouped_by_expert** ด้านปกติ (peft ≥ 0.20) — เสิร์ฟด้วย
`UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert` ผ่าน Unsloth separated MoE forward เท่านั้น
(PEFT/vLLM ล้วนอ่านแบบ rank_major → ต้องแปลง B ก่อน)

ใช้ PEFT `add_weighted_adapter` ไม่ได้: MoE `target_parameters` โหลดได้ตัวเดียวต่อโมเดล
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
