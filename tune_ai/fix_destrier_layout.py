#!/usr/bin/env python3
"""fix_destrier_layout.py — ซ่อม dacarokann/destrier (rev e229403) ที่ LoRA ของ MoE expert ปนผิด

พบ 2026-09-27 (หลักฐานเต็ม: t05_Destrier/proof/03_destrier_expert_LoRA_ปนผิด.md)
══════════════════════════════════════════════════════════════════════════════════════
fold ทั้งสาม (Courser_a/c/d) เทรนด้วย Unsloth 2026.8.22 (unsloth_zoo 2026.8.16-2026.9.5) ซึ่ง
forward อ่าน lora_B ของ expert แบบ grouped_by_expert (คอลัมน์ e*r+q = expert e rank q) และ
lora_A แบบ expert-major (แถว e*r+q) — แต่ soup_safetensors.py อ่าน lora_B แบบ rank_major
(ของ PEFT) ทั้งตอนต่อ fold และตอนแปลงด้าน Courser_a (convert_expert_pair) ผลคือ:
  · lora_B ของ destrier = [B_a | B_c | B_d]/3 ต่อกันเป็นก้อน ไม่ได้แทรกราย expert
  · ช่องของ Courser_a ทั้งฝั่ง A และ B ย้ายไปอยู่ expert ผิดตัว
  → ตอนเสิร์ฟ (บังคับ grouped_by_expert) มีคู่ A↔B ที่ถูกต้องแค่ 17 จาก 12288 ต่อเทนเซอร์
  ด่านตรวจเดิม (diagnose / ตรวจการแปลง) อ่านด้วยแบบผิดเดียวกัน จึงขึ้นผ่านทุกครั้ง

ซ่อมได้โดยไม่ต้องใช้ fold และไม่เสียข้อมูล: ทุกชิ้นส่วนยังอยู่ในไฟล์ครบ แค่อยู่ผิดตำแหน่ง
  E=256 · r=16 ต่อ fold · k=3 · R=48 · ลำดับ fold ในไฟล์ = Courser_a, Courser_c, Courser_d
  ช่อง Courser_a    s = e*R + q          A_fix[s] = D_A[((e*r+q) % E)*R + (e*r+q)//E]
                                         B_fix[:, s] = D_B[:, q*E + e]
  ช่อง Courser_c/d  s = e*R + kk*r + q   A_fix[s] = D_A[s]
                                         B_fix[:, s] = D_B[:, kk*E*r + e*r + q]
  (1/3 อยู่ใน D_B แล้ว · r=48 / lora_alpha=96 ไม่ต้องแก้ · เทนเซอร์ที่ไม่ใช่ expert ไม่แตะ)
ผลลัพธ์ = adapter แบบ grouped_by_expert r=48 ที่ถูกต้อง → ต้องเสิร์ฟด้วย
UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert (SERVE_ENV ใน presentation.py ตั้งให้อยู่แล้ว)
และตัวเสิร์ฟต้องผ่าน Unsloth separated MoE forward จริง (serve_purson.py ตรวจตอนเปิดเครื่อง)

⛔ สูตรผูกกับไฟล์นี้ไฟล์เดียว (ลำดับ fold + fold ไหนผ่าน convert) — มีด่านลายนิ้วมือกันใช้ผิดไฟล์
   soup รอบหน้าให้ใช้ soup_safetensors.py ตัวที่แก้แล้ว ไม่ต้องใช้สคริปต์นี้

วิธีเขียน: คัดลอกไฟล์เดิมทั้งก้อน แล้วเขียนทับเฉพาะ 160 เทนเซอร์ของ expert ณ byte เดิม
(รูปร่าง/ชนิด/ลำดับเท่าเดิม → header เดิมทุก byte) ใช้ RAM ไม่เกินราว 2 เทนเซอร์ต่อครั้ง

รัน:
  python fix_destrier_layout.py --src <โฟลเดอร์ snapshot ของ destrier> --out ./destrier_fixed
  python fix_destrier_layout.py --src dacarokann/destrier --out ./destrier_fixed   # โหลด 11 GB ก่อน
  python fix_destrier_layout.py --check-folds ./destrier_fixed     # เทียบ fold จริงบน HF (~2 MB)
  python fix_destrier_layout.py --selftest                         # จำลองสายเทรน→soup→ซ่อม ไม่ใช้เน็ต
"""
import argparse
import hashlib
import json
import os
import shutil
import ssl
import struct
import sys
import time
import urllib.request

import numpy as np
import torch

E, R_FOLD, K = 256, 16, 3
R = R_FOLD * K
FOLD_REPOS = ("Courser_a", "Courser_c", "Courser_d")      # ลำดับเดียวกับ --folds 0 2 3 ของ soup
ST = "adapter_model.safetensors"

# ลายนิ้วมือของ dacarokann/destrier rev e229403b12f63794217290c199fc5a069aea5b78 (วัด 2026-09-27)
EXPECTED_HEADER_SHA256 = "b7a9e8937f1223c9876f29217063e366a2032834c9d267438016915777437240"
EXPECTED_L0_B_MIB_SHA256 = "3174130d83a3a51e16e70a9fb6a8a15c2b4affaefbc60691fd891ef2dc164a21"
L0_GATE_UP_B = "base_model.model.model.language_model.layers.0.mlp.experts.base_layer.lora_B.weight"


def build_perms(e_num=E, r=R_FOLD, k=K, converted_slot=0):
    """ดัชนีแบบ gather: A_fix = D_A[permA], B_fix = D_B[:, permB]

    converted_slot = ช่อง fold ที่ soup ส่งผ่าน convert_expert_pair (destrier: Courser_a = 0)"""
    big_r = r * k
    perm_a = np.empty(e_num * big_r, np.int64)
    perm_b = np.empty(e_num * big_r, np.int64)
    for e in range(e_num):
        for kk in range(k):
            for q in range(r):
                s = e * big_r + kk * r + q
                if kk == converted_slot:
                    # convert_expert_pair อ่าน grouped เป็น rank_major: คอลัมน์ c = e*r+q ของ B เดิม
                    # (expert e rank q) ไปอยู่แถว (c%E)*r + c//E ของ A ใหม่ แล้ว soup วางแถวนั้นที่
                    # (c%E)*R + kk*r + c//E · แถว e*r+q ของ A เดิม ไปอยู่คอลัมน์ q*E+e ของ B ใหม่
                    c = e * r + q
                    perm_a[s] = (c % e_num) * big_r + kk * r + c // e_num
                    perm_b[s] = kk * e_num * r + q * e_num + e
                else:
                    perm_a[s] = s
                    perm_b[s] = kk * e_num * r + e * r + q
    ident = np.arange(e_num * big_r)
    if not (np.array_equal(np.sort(perm_a), ident) and np.array_equal(np.sort(perm_b), ident)):
        raise SystemExit("⛔ permA/permB ไม่เป็น bijection — สูตรพัง หยุด")
    return torch.from_numpy(perm_a), torch.from_numpy(perm_b)


def read_header(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return 8 + n, json.loads(f.read(n))


def fingerprint(path):
    base, h = read_header(path)
    hs = hashlib.sha256(json.dumps(h, sort_keys=True).encode()).hexdigest()
    s = h[L0_GATE_UP_B]["data_offsets"][0]
    with open(path, "rb") as f:
        f.seek(base + s)
        bs = hashlib.sha256(f.read(1 << 20)).hexdigest()
    return hs, bs


def expert_pairs(h):
    """คู่ (lora_A, lora_B) ของ MoE expert ทุกคู่ — 40 ชั้น × {gate_up (base_layer), down}"""
    keys = [k for k in h if k != "__metadata__" and ".mlp.experts." in k]
    a_keys = sorted(k for k in keys if k.endswith("lora_A.weight"))
    pairs = [(ka, ka[: -len("lora_A.weight")] + "lora_B.weight") for ka in a_keys]
    if len(pairs) * 2 != len(keys) or any(kb not in h for _, kb in pairs):
        raise SystemExit("⛔ คีย์ expert ไม่ครบคู่ — ไม่ใช่ไฟล์ที่คาดไว้")
    return pairs


def resolve_src(src):
    if os.path.isdir(src):
        return src
    from huggingface_hub import snapshot_download
    print(f"ดาวน์โหลด {src} (≈11 GB) …", flush=True)
    return snapshot_download(src, revision="e229403b12f63794217290c199fc5a069aea5b78")


def fix(src, out):
    src = resolve_src(src)
    src_st, out_st = os.path.join(src, ST), os.path.join(out, ST)
    cfg = json.load(open(os.path.join(src, "adapter_config.json"), encoding="utf-8"))
    if cfg.get("lora_B_layout"):
        raise SystemExit(f"⛔ adapter ประกาศ lora_B_layout={cfg['lora_B_layout']} แล้ว — "
                         "ไม่ใช่ destrier ตัวที่ปนผิด (หรือซ่อมไปแล้ว) ไม่ทำซ้ำ")
    if cfg.get("r") != R or cfg.get("lora_alpha") != 96:
        raise SystemExit(f"⛔ r={cfg.get('r')} alpha={cfg.get('lora_alpha')} ไม่ใช่ 48/96 — ไฟล์ผิดตัว")
    hs, bs = fingerprint(src_st)
    if (hs, bs) != (EXPECTED_HEADER_SHA256, EXPECTED_L0_B_MIB_SHA256):
        raise SystemExit("⛔ ลายนิ้วมือไม่ตรงกับ destrier rev e229403 — สูตรนี้ใช้กับไฟล์อื่นไม่ได้")
    print("✅ ลายนิ้วมือตรงกับ destrier rev e229403")

    if os.path.abspath(src) == os.path.abspath(out):
        raise SystemExit("⛔ --out ต้องเป็นคนละโฟลเดอร์กับต้นฉบับ (เก็บตัวเดิมไว้ย้อนกลับ)")
    os.makedirs(out, exist_ok=True)
    # ป้าย "ซ่อมแล้ว" (lora_B_layout ใน config + README) ต้องอยู่คู่กับไฟล์ที่ตรวจผ่านเท่านั้น — รันซ้ำลงโฟลเดอร์เดิม
    # แล้วล้มกลางทาง (Ctrl+C/ดิสก์เต็ม) ป้ายเก่าจะค้างข้างไฟล์ที่สลับไปครึ่งเดียว (รีวิว 27 ก.ย.) · ลบก่อน เขียนท้ายสุด
    for stale in ("adapter_config.json", "README.md"):
        if os.path.exists(os.path.join(out, stale)):
            os.remove(os.path.join(out, stale))
    for name in os.listdir(src):
        p = os.path.join(src, name)
        if os.path.isfile(p) and name not in (ST, "adapter_config.json", "README.md"):
            shutil.copy(p, os.path.join(out, name))
    t0 = time.time()
    print(f"คัดลอก {ST} ทั้งก้อน (11 GB) …", flush=True)
    shutil.copyfile(src_st, out_st)
    print(f"   เสร็จใน {time.time() - t0:.0f} วิ")

    perm_a, perm_b = build_perms()
    base, h = read_header(src_st)
    pairs = expert_pairs(h)
    from safetensors import safe_open
    with safe_open(src_st, framework="pt") as f, open(out_st, "r+b") as g:
        for i, (ka, kb) in enumerate(pairs, 1):
            a, b = f.get_tensor(ka), f.get_tensor(kb)
            if a.shape[0] != E * R or b.shape[1] != E * R or a.dtype != torch.float32:
                raise SystemExit(f"⛔ รูปร่าง/ชนิด {ka} ไม่ตรงที่คาด: {tuple(a.shape)} {a.dtype}")
            for key, t in ((ka, a[perm_a].contiguous()), (kb, b[:, perm_b].contiguous())):
                s, e = h[key]["data_offsets"]
                data = t.numpy().tobytes()
                if len(data) != e - s:
                    raise SystemExit(f"⛔ ขนาด byte ของ {key} ไม่ตรง header — หยุด")
                g.seek(base + s)
                g.write(data)
            if i % 10 == 0 or i == len(pairs):
                print(f"   เขียนแล้ว {i}/{len(pairs)} คู่ ({time.time() - t0:.0f} วิ)", flush=True)

    verify_written(src_st, out_st, perm_a, perm_b)

    cfg["lora_B_layout"] = "grouped_by_expert"   # ประกาศไว้ในไฟล์ — Unsloth รุ่นที่อ่านคีย์นี้จะอ่านถูกเอง
    json.dump(cfg, open(os.path.join(out, "adapter_config.json"), "w", encoding="utf-8"), indent=2)
    open(os.path.join(out, "README.md"), "w", encoding="utf-8").write(README)
    print(f"\n✅ ซ่อมเสร็จ → {out}\n   ต่อไป: python {os.path.basename(__file__)} --check-folds {out}")


def verify_written(src_st, out_st, perm_a, perm_b):
    """อ่านไฟล์ที่เขียนจริงกลับมาเทียบทีละเทนเซอร์ — ไม่เชื่อว่าเขียนแล้วจะถูก"""
    from safetensors import safe_open
    base, h = read_header(out_st)
    if read_header(src_st)[1] != h:
        raise SystemExit("⛔ header ของไฟล์ใหม่ไม่เท่าของเดิม — หยุด")
    pairs = expert_pairs(h)
    expert_keys = {k for p in pairs for k in p}
    print("ตรวจไฟล์ที่เขียนแล้ว (อ่านกลับทุกเทนเซอร์) …", flush=True)
    with safe_open(src_st, framework="pt") as fs, safe_open(out_st, framework="pt") as fo:
        for ka, kb in pairs:
            if not torch.equal(fo.get_tensor(ka), fs.get_tensor(ka)[perm_a]):
                raise SystemExit(f"⛔ {ka} ที่เขียนไม่ตรงกับที่ควรเป็น")
            if not torch.equal(fo.get_tensor(kb), fs.get_tensor(kb)[:, perm_b]):
                raise SystemExit(f"⛔ {kb} ที่เขียนไม่ตรงกับที่ควรเป็น")
        for k in h:
            if k != "__metadata__" and k not in expert_keys:
                if not torch.equal(fo.get_tensor(k), fs.get_tensor(k)):
                    raise SystemExit(f"⛔ เทนเซอร์ที่ไม่ใช่ expert ถูกแตะ: {k}")
    print(f"   ✅ expert {len(pairs)} คู่ตรงตามสูตร · อีก {len(h) - 1 - len(expert_keys)} เทนเซอร์เหมือนเดิมทุกค่า")


# ── เทียบกับ fold จริงบน HuggingFace (อ่านทีละแถวผ่าน HTTP Range — ไม่โหลดไฟล์) ──────────────
# ใช้ urllib ไม่ใช้ requests: เครื่องนี้ requests (certifi) ไม่เชื่อใบรับรองของ CDN แต่ Windows
# certificate store เชื่อ — ssl.create_default_context() อ่าน store ของระบบ
_CTX = ssl.create_default_context()
_URL = "https://huggingface.co/dacarokann/{}/resolve/main/" + ST
_H = {}
_GOT = [0]


def _range(repo, a, b):
    req = urllib.request.Request(_URL.format(repo), headers={"Range": f"bytes={a}-{b}"})
    with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
        data = r.read()
    if len(data) != b - a + 1:
        raise SystemExit(f"⛔ อ่าน {repo} ได้ {len(data)} byte ไม่ครบช่วง — เซิร์ฟเวอร์ไม่รับ Range?")
    _GOT[0] += len(data)
    return data


def _remote_header(repo):
    if repo not in _H:
        n = struct.unpack("<Q", _range(repo, 0, 7))[0]
        _H[repo] = (8 + n, json.loads(_range(repo, 8, 8 + n - 1)))
    return _H[repo]


def _remote_row(repo, key, i):
    base, h = _remote_header(repo)
    m = h[key]
    if m["dtype"] != "F32":
        raise SystemExit(f"⛔ {repo} {key} เป็น {m['dtype']} ไม่ใช่ F32")
    cols = m["shape"][1]
    o = base + m["data_offsets"][0] + i * cols * 4
    return np.frombuffer(_range(repo, o, o + cols * 4 - 1), dtype=np.float32)


def check_folds(out, layers=(0, 20, 39), seed=7):
    """ชิ้นส่วนในไฟล์ที่ซ่อมแล้ว ต้องเท่ากับของ fold จริงทุกตัวที่สุ่มดู (อ่านจากไฟล์ที่เขียนจริง)

    Courser_c/d: A_fix[e*48+kk*16+q] == A_fold[e*16+q] (เป๊ะ) · 3*B_fix == B_fold (ปัด fp32 /3)
    Courser_a (ด้านสลับ peft 0.18.1): A_fix[e*48+q] == B_a[:, e*16+q] (เป๊ะ)
                                     3*B_fix[:, e*48+q] == A_a[e*16+q]
    ตัวคุมฝั่งกลับ: ไฟล์ต้นฉบับที่ตำแหน่งเดียวกันต้อง "ไม่" ตรง — พิสูจน์ว่าด่านนี้แยกออกจริง"""
    from safetensors import safe_open
    rs = np.random.default_rng(seed)
    out_st = os.path.join(out, ST) if os.path.isdir(out) else out
    worst = 0.0
    with safe_open(out_st, framework="pt") as f:
        keys = list(f.keys())
        for layer in layers:
            for part in ("base_layer.", ""):
                suf = f"layers.{layer}.mlp.experts.{part}lora_A.weight"
                ka = next(k for k in keys if k.endswith(suf))
                kb = ka.replace("lora_A", "lora_B")
                fa = next(k for k in _remote_header("Courser_a")[1] if k.endswith(suf))
                fb = fa.replace("lora_A", "lora_B")
                a_fix, b_fix = f.get_tensor(ka).numpy(), f.get_tensor(kb).numpy()
                picks = [(0, 0), (15, 15), (16, 0), (85, 3), (86, 9), (255, 15)] + \
                        [tuple(int(v) for v in x) for x in rs.integers([0, 0], [E, R_FOLD], (3, 2))]
                for kk, repo in ((1, "Courser_c"), (2, "Courser_d")):
                    for e, q in picks[:5]:
                        if not np.array_equal(_remote_row(repo, fa, e * 16 + q),
                                              a_fix[e * R + kk * R_FOLD + q]):
                            raise SystemExit(f"⛔ L{layer} {part or 'down'} {repo} A e={e} q={q} ไม่ตรง")
                    y = int(rs.integers(0, b_fix.shape[0]))
                    fold_row = _remote_row(repo, fb, y)
                    mine = b_fix[y].reshape(E, R)[:, kk * R_FOLD:(kk + 1) * R_FOLD].reshape(-1) * 3
                    worst = max(worst, float(np.abs(fold_row - mine).max() / np.abs(fold_row).max()))
                y = int(rs.integers(0, a_fix.shape[1]))
                b0 = _remote_row("Courser_a", fb, y)
                mine = a_fix[:, y].reshape(E, R)[:, :R_FOLD].reshape(-1)
                if not np.array_equal(b0, mine):
                    raise SystemExit(f"⛔ L{layer} {part or 'down'} Courser_a ด้าน A ไม่ตรง")
                for e, q in picks:
                    a0 = _remote_row("Courser_a", fa, e * 16 + q)
                    worst = max(worst, float(np.abs(a0 - 3 * b_fix[:, e * R + q]).max()
                                             / np.abs(a0).max()))
                print(f"   L{layer} {'gate_up' if part else 'down'}: ตรงกับ fold จริงทุกจุดที่สุ่ม")
    if worst > 1e-5:
        raise SystemExit(f"⛔ ฝั่ง B ต่างจาก fold จริง {worst:.1e} — เกินระดับปัดเศษ fp32")
    print(f"✅ ตรงกับ Courser_a/c/d จริง · ฝั่ง B ต่างสุด {worst:.1e} (ปัดเศษ /3) · "
          f"ดึงข้อมูล {_GOT[0] / 1024:.0f} KB")


# ── selftest: จำลองสายจริงทั้งเส้นด้วยตัวเลขเล็ก ไม่ใช้เน็ต ────────────────────────────────
def selftest(e_num=32, r=R_FOLD, x_dim=6, y_dim=5, seed=0, conv=0):
    """fold grouped (fold ช่อง conv เก็บด้านสลับแบบ peft 0.18.1 ที่เหลือด้านปกติ) →
    convert_expert_pair + soup ตามบรรทัดจริงใน soup_safetensors.py รุ่นที่สร้าง destrier →
    ซ่อมด้วย build_perms → อ่านแบบ grouped_by_expert ต้องได้ ΔW ทุก expert = ค่าเฉลี่ยจริงของ 3 fold"""
    g = torch.Generator().manual_seed(seed)
    k, big_r = K, r * K
    true_dw = torch.zeros(e_num, y_dim, x_dim, dtype=torch.float64)
    folds = []
    for kk in range(k):
        a = torch.randn(e_num * r, x_dim, generator=g, dtype=torch.float64)      # (E*r, in) expert-major
        b = torch.randn(y_dim, e_num * r, generator=g, dtype=torch.float64)      # (out, E*r) grouped
        for e in range(e_num):
            true_dw[e] += b[:, e * r:(e + 1) * r] @ a[e * r:(e + 1) * r] / k
        if kk == conv:  # Courser_a: peft 0.18.1 เก็บด้านสลับ — A0o=(E*r,out) B0o=(in,E*r)
            a, b = b.T.contiguous(), a.T.contiguous()
        folds.append((a, b))
    # soup_safetensors.py (rev ที่สร้าง destrier): convert_expert_pair กับ fold ด้านน้อย
    a0, b0 = folds[conv]
    y_, x_ = b0.shape[0], a0.shape[-1]
    a2 = b0.reshape(y_, r, e_num).permute(2, 1, 0).reshape(e_num * r, y_).contiguous()
    b2 = a0.reshape(e_num, r, x_).permute(2, 1, 0).reshape(x_, e_num * r).contiguous()
    folds[conv] = (a2, b2)
    d_a = torch.cat([t.reshape(e_num, r, x_dim) for t, _ in folds], dim=1).reshape(e_num * big_r, x_dim)
    d_b = torch.cat([t.reshape(y_dim, r, e_num) for _, t in folds], dim=1).reshape(y_dim, e_num * big_r) / k

    def served(a_, b_):     # grouped_by_expert r=48: expert e = แถว/คอลัมน์ e*R..e*R+R-1
        return torch.stack([b_[:, e * big_r:(e + 1) * big_r] @ a_[e * big_r:(e + 1) * big_r]
                            for e in range(e_num)])
    err_before = ((served(d_a, d_b) - true_dw).norm() / true_dw.norm()).item()
    perm_a, perm_b = build_perms(e_num, r, k, converted_slot=conv)
    err_after = ((served(d_a[perm_a], d_b[:, perm_b]) - true_dw).norm() / true_dw.norm()).item()
    print(f"selftest E={e_num} fold ที่แปลง={conv}: ก่อนซ่อมคลาด {err_before:.2f} · "
          f"หลังซ่อม {err_after:.1e}")
    if not (err_before > 0.5 and err_after < 1e-12):
        raise SystemExit("⛔ selftest ไม่ผ่าน")
    if e_num == E and r == 16 and conv == 0:
        # สูตรที่ทีมตรวจ 3 ตัวยืนยันกับ fold จริง (เขียนแบบตัวเลขตรงๆ) ต้องเท่ากับสูตรทั่วไปทุกช่อง
        verbatim = np.array([(16 * (e % 16) + q) * 48 + e // 16 for e in range(E) for q in range(16)])
        mine = perm_a.numpy().reshape(E, R)[:, :16].reshape(-1)
        if not np.array_equal(verbatim, mine):
            raise SystemExit("⛔ สูตรทั่วไปไม่ตรงกับสูตรที่ยืนยันกับ fold จริง")
    return err_before, err_after


README = """---
base_model: unsloth/Qwen3.6-35B-A3B
library_name: peft
tags: [lora, model-soup, k-fold]
---

# destrier-fixed

`dacarokann/destrier` rev e229403 ที่ซ่อม LoRA ของ MoE expert ให้อยู่ถูกตำแหน่งแล้ว (2026-09-27)
ด้วย `tune_ai/fix_destrier_layout.py` — สลับตำแหน่งอย่างเดียว ไม่เปลี่ยนค่าใดๆ

- layout: **grouped_by_expert** r=48 (Courser_a, Courser_c, Courser_d · ΔW = (1/3)·Σ ΔW_i)
- เสิร์ฟด้วย `UNSLOTH_MOE_LORA_B_LAYOUT=grouped_by_expert` ผ่าน Unsloth separated MoE forward เท่านั้น
  (PEFT/vLLM ล้วนอ่านแบบ rank_major → ต้องแปลง B ก่อน: B_rm[:, ρ*256+e] = B[:, e*48+ρ])
- ตัวเดิม (e229403) ปนผิด: ตอนเสิร์ฟมีคู่ A↔B ถูกแค่ 17/12288 ต่อเทนเซอร์ของ expert
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help="โฟลเดอร์ snapshot ของ destrier หรือ repo id บน HF")
    ap.add_argument("--out", help="โฟลเดอร์ปลายทาง (ต้องไม่ใช่ที่เดียวกับต้นฉบับ)")
    ap.add_argument("--check-folds", metavar="OUT", help="เทียบไฟล์ที่ซ่อมแล้วกับ fold จริงบน HF")
    ap.add_argument("--selftest", action="store_true", help="จำลองสายเทรน→soup→ซ่อม (ไม่ใช้เน็ต)")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        selftest(conv=1)
        selftest(e_num=E)
        return 0
    if a.check_folds:
        check_folds(a.check_folds)
        return 0
    if not (a.src and a.out):
        ap.error("ต้องใส่ --src และ --out (หรือ --selftest / --check-folds)")
    selftest()          # ด่านแรกเสมอ — สูตรพังต้องรู้ก่อนเขียน 11 GB
    fix(a.src, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
