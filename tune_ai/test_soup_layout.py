#!/usr/bin/env python3
"""เทส soup_safetensors.py (แก้ 2026-09-27 + รอบรีวิว) ด้วยตัวเลขสังเคราะห์ที่รู้คำตอบ — ไม่ใช้เน็ต ไม่ใช้ GPU

รัน: python test_soup_layout.py

ทุกข้อผูกกับความพังจริงของ dacarokann/destrier rev e229403 หรือ mutant ที่รีวิวอิสระ 27 ก.ย. เจอว่ารอดเทสรุ่นแรก
fold สร้างจากนิยามการคูณของ Unsloth ตรงๆ (ΔW_e = B_e·A_e / ด้านสลับ x@first_e@second_e) ไม่ใช่ transpose
— transpose คือสมมติฐานเดียวกับ swap_orientation ที่กำลังถูกทดสอบ
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_destrier_layout as FIX  # noqa: E402
import soup_safetensors as S  # noqa: E402

E, RF, K = 32, 16, 3
L = "base_model.model.model.language_model.layers.0."
KA = L + "mlp.experts.base_layer.lora_A.weight"     # gate_up (hidden 6 → 2·moe_inter 8)
KD = L + "mlp.experts.lora_A.weight"                # down ไม่มี base_layer (moe_inter 4 → hidden 6)
KQ = L + "self_attn.q_proj.lora_A.weight"
DIMS = {KA: (6, 8), KD: (4, 6), KQ: (6, 3)}
BASE_CFG = {"text_config": {"hidden_size": 6, "moe_intermediate_size": 4}}
VALID = S.valid_io(BASE_CFG)
quiet = lambda *a, **k: None  # noqa: E731
R = RF * K


def make_fold(g, orient=S.CANON, layout=S.GROUPED, declare=False, structured=True, sigma=1.0):
    """fold หนึ่งตัว → (sd, cfg, ΔW จริง {key: (E, out, in) หรือ (out, in)})"""
    sd, dw = {}, {}
    for ka in (KA, KD):
        d_in, d_out = DIMS[ka]
        sa = (sigma * torch.randn(E, generator=g)).exp() if structured else torch.ones(E)   # ขนาดต่อ expert ต่างกัน
        sb = (sigma * torch.randn(E, generator=g)).exp() if structured else torch.ones(E)   # เหมือนโมเดลที่เทรนจริง
        a = [torch.randn(RF, d_in, generator=g, dtype=torch.float64) * sa[e] for e in range(E)]
        b = [torch.randn(d_out, RF, generator=g, dtype=torch.float64) * sb[e] for e in range(E)]
        dw[ka] = torch.stack([b[e] @ a[e] for e in range(E)])
        if orient == S.CANON:        # A (E·r, in) · B (out, E·r)
            A = torch.stack(a).reshape(E * RF, d_in)
            cols = b
        else:                        # peft 0.18.1: x @ first_e (in, r) @ second_e (r, out) — first/second = A_eᵀ/B_eᵀ
            A = torch.stack([be.T for be in b]).reshape(E * RF, d_out)          # A0o (E·r, out) = second
            cols = [ae.T for ae in a]                                           # first_e (in, r)
        B = (torch.stack(cols, dim=1).reshape(cols[0].shape[0], E * RF) if layout == S.GROUPED
             else torch.stack(cols, dim=2).reshape(cols[0].shape[0], E * RF))   # คอลัมน์ q·E+e
        sd[ka], sd[S.b_key(ka)] = A, B
    d_in, d_out = DIMS[KQ]
    a2 = torch.randn(RF, d_in, generator=g, dtype=torch.float64)
    b2 = torch.randn(d_out, RF, generator=g, dtype=torch.float64)
    sd[KQ], sd[S.b_key(KQ)], dw[KQ] = a2, b2, b2 @ a2
    cfg = {"peft_version": "0.18.1" if orient == S.REVERSED else "0.20.0", "r": RF, "lora_alpha": 32,
           "use_rslora": False, "base_model_name_or_path": "unsloth/Qwen3.6-35B-A3B"}
    if declare:
        cfg["lora_B_layout"] = layout
    return sd, cfg, dw


def build(specs, seed=0):
    g = torch.Generator().manual_seed(seed)
    folds = [make_fold(g, *s) for s in specs]
    truth = {k: sum(f[2][k] for f in folds) / len(folds) for k in (KA, KD, KQ)}
    return [f[0] for f in folds], [f[1] for f in folds], truth


def served_dw(a, b, r):
    """ΔW ต่อ expert ตามที่ Unsloth grouped_by_expert อ่าน (ด้านปกติ)"""
    return torch.stack([b[:, e * r:(e + 1) * r] @ a[e * r:(e + 1) * r] for e in range(E)])


def soup(sds, cfgs):
    raw = [dict(sd) for sd in sds]
    lays = [S.fold_layout(c, sd, RF, log=quiet) for c, sd in zip(cfgs, raw)]
    ors = [S.fold_orientation(c, sd, VALID) for c, sd in zip(cfgs, raw)]
    ref = S.reference_probes(raw, lays, ors, RF)
    return S.merge_folds(raw, lays, ors, RF, log=quiet), ref


def rel(x, y):
    return ((x - y).norm() / y.norm()).item()


def assert_correct(merged, truth, what):
    for ka in (KA, KD):
        err = rel(served_dw(merged[ka], merged[S.b_key(ka)], R), truth[ka])
        assert err < 1e-12, f"{what}: {ka.split('.')[-3]} ΔW ไม่ตรงค่าเฉลี่ยจริง ({err})"
    err = rel(merged[S.b_key(KQ)] @ merged[KQ], truth[KQ])
    assert err < 1e-12, f"{what}: attn ไม่ตรง ({err})"


def refuses(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


DESTRIER = [(S.REVERSED,), (S.CANON,), (S.CANON,)]      # Courser_a (peft 0.18.1) + c + d

# 1 — ทุก expert ของทั้งสองคีย์ (มี/ไม่มี base_layer) ถูกต้องตามที่ตัวเสิร์ฟอ่าน
sds, cfgs, truth = build(DESTRIER)
merged, ref = soup(sds, cfgs)
assert_correct(merged, truth, "แบบ destrier")
assert S.check_soup(ref, merged, R, log=quiet), "check_soup ไม่ผ่านกับ soup ที่ถูกต้อง"
print("OK  1. แบบ destrier (fold ด้านสลับ + ปกติ 2): ΔW ทุก expert ทั้ง gate_up/down ตรง · ด่านผ่าน")


def old_soup(sds):
    """soup_safetensors.py รุ่นที่สร้าง destrier (ก่อน 27 ก.ย.) — บรรทัดเดิมคำต่อคำ ทุกคีย์ expert"""
    sds = [dict(sd) for sd in sds]
    out = {}
    for ka in (KA, KD):
        kb = S.b_key(ka)
        a0, b0 = sds[0][ka], sds[0][kb]
        y_, x_ = b0.shape[0], a0.shape[-1]
        sds[0][ka] = b0.reshape(y_, RF, E).permute(2, 1, 0).reshape(E * RF, y_).contiguous()
        sds[0][kb] = a0.reshape(E, RF, x_).permute(2, 1, 0).reshape(x_, E * RF).contiguous()
        X, Y = sds[1][ka].shape[1], sds[1][kb].shape[0]
        out[ka] = torch.cat([sd[ka].reshape(E, RF, X) for sd in sds], dim=1).reshape(E * RF * K, X)
        out[kb] = torch.cat([sd[kb].reshape(Y, RF, E) for sd in sds], dim=1).reshape(Y, E * RF * K) / K
    return out


# 2 — soup ใหม่ == soup เก่า + ซ่อมด้วย fix_destrier_layout (เป๊ะทุกค่า ทั้งสองคีย์)
old = old_soup(sds)
pa, pb = FIX.build_perms(E, RF, K, converted_slot=0)
for ka in (KA, KD):
    kb = S.b_key(ka)
    assert rel(served_dw(old[ka], old[kb], R), truth[ka]) > 0.5, "soup เก่าควรผิดชัดเจน"
    assert torch.equal(old[ka][pa], merged[ka]) and torch.equal(old[kb][:, pb], merged[kb]), \
        "soup ใหม่ ≠ soup เก่าที่ซ่อมแล้ว — สองทางนี้ต้องเป็นเรื่องเดียวกัน"
bad = dict(merged)
bad.update(old)
assert not S.check_soup(ref, bad, R, log=quiet), "check_soup ผ่านกับ soup เก่าที่ปนผิด"
print("OK  2. soup เก่า+ซ่อม == soup ใหม่ ทุกค่า (bit-exact) · ด่านไม่ผ่านกับ soup เก่า")

# 3 — fold ด้านสลับ + rank_major (layout ต้องแปลงก่อนสลับ) + ปกติ rank_major + ปกติ grouped
sds3, cfgs3, truth3 = build([(S.REVERSED, S.RANK_MAJOR), (S.CANON, S.RANK_MAJOR, True), (S.CANON,)], seed=1)
m3, ref3 = soup(sds3, cfgs3)
assert_correct(m3, truth3, "ผสม layout/ด้าน")
assert S.check_soup(ref3, m3, R, log=quiet)
print("OK  3. fold ด้านสลับ+rank_major / ปกติ+rank_major / ปกติ+grouped ต่อถูก")
sds3b, cfgs3b, truth3b = build([(S.REVERSED,), (S.REVERSED, S.RANK_MAJOR), (S.CANON,)], seed=2)
m3b, _ = soup(sds3b, cfgs3b)
assert_correct(m3b, truth3b, "ด้านสลับเป็นเสียงข้างมาก")
print("OK  3b. fold ด้านสลับเป็นเสียงข้างมาก (2/3) → ผลยังเป็นด้านปกติ ต่อถูก")

# 4 — ด่านตรวจต้องจับบั๊กใน **โค้ดแปลง** ได้ (ค่าอ้างอิงมาจาก fold ดิบ ไม่ใช่ของที่แปลงแล้ว)
real_swap, real_b2g = S.swap_orientation, S.b_to_grouped


def old_swap(A, B):   # convert_expert_pair ของรุ่นที่สร้าง destrier — อ่าน grouped เป็น rank_major
    y_, x_ = B.shape[0], A.shape[-1]
    return (B.reshape(y_, RF, E).permute(2, 1, 0).reshape(E * RF, y_).contiguous(),
            A.reshape(E, RF, x_).permute(2, 1, 0).reshape(x_, E * RF).contiguous())


def swap_then_normalize(sds_, lays, ors, r, log=print):   # ลำดับกลับ: สลับด้านก่อนแปลง layout
    for sd, lay, o in zip(sds_, lays, ors):
        for ka in (KA, KD):
            kb = S.b_key(ka)
            if o == S.REVERSED:
                sd[ka], sd[kb] = real_swap(sd[ka], sd[kb])
            sd[kb] = real_b2g(sd[kb], r, lay)
    return real_merge(sds_, [S.GROUPED] * len(sds_), [S.CANON] * len(sds_), r, log)


real_merge = S.merge_folds
for label, patch in (("convert_expert_pair เดิม", ("swap_orientation", old_swap)),
                     ("ไม่แปลง layout", ("b_to_grouped", lambda B, r, lay: B))):
    setattr(S, *patch)
    try:
        mm, rr = soup(sds3, cfgs3)
        assert not S.check_soup(rr, mm, R, log=quiet), f"ด่านผ่านทั้งที่โค้ดแปลงผิด ({label})"
    finally:
        S.swap_orientation, S.b_to_grouped = real_swap, real_b2g
raw = [dict(sd) for sd in sds3]
lays3 = [S.fold_layout(c, sd, RF, log=quiet) for c, sd in zip(cfgs3, raw)]
ors3 = [S.fold_orientation(c, sd, VALID) for c, sd in zip(cfgs3, raw)]
rr = S.reference_probes(raw, lays3, ors3, RF)
assert not S.check_soup(rr, swap_then_normalize(raw, lays3, ors3, RF, log=quiet), R, log=quiet), \
    "ด่านผ่านทั้งที่สลับด้านก่อนแปลง layout"
print("OK  4. ด่านจับได้: convert_expert_pair เดิม / ไม่แปลง layout / สลับด้านก่อนแปลง layout")

# 5 — layout วัดจากตัวเลข ไม่เชื่อว่า "ไม่มีคีย์ = grouped"
g = torch.Generator().manual_seed(5)
sd_g, cfg_g, _ = make_fold(g, S.CANON, S.GROUPED)
sd_r, cfg_r, _ = make_fold(g, S.CANON, S.RANK_MAJOR)
sd_rev, cfg_rev, _ = make_fold(g, S.REVERSED, S.RANK_MAJOR)
assert S.fold_layout(cfg_g, sd_g, RF, log=quiet) == S.GROUPED
assert S.fold_layout(cfg_r, sd_r, RF, log=quiet) == S.RANK_MAJOR, "ไม่มีคีย์แต่ตัวเลขเป็น rank_major ต้องได้ rank_major"
assert S.fold_layout(cfg_rev, sd_rev, RF, log=quiet) == S.RANK_MAJOR
assert refuses(lambda: S.fold_layout({**cfg_r, "lora_B_layout": S.GROUPED}, sd_r, RF, log=quiet)), \
    "ประกาศ grouped แต่ตัวเลขเป็น rank_major ต้องหยุด"
nested = {"unsloth_fused_expert_lora": {"parameters": {"gate_up_proj": {"lora_B_layout": S.RANK_MAJOR}}}}
assert refuses(lambda: S.fold_layout({**cfg_g, **nested}, sd_g, RF, log=quiet)), "nested ขัดกับตัวเลขต้องหยุด"
sd_flat, cfg_flat, _ = make_fold(g, S.CANON, S.GROUPED, structured=False)
assert refuses(lambda: S.fold_layout(cfg_flat, sd_flat, RF, log=quiet)), "ตัวเลขกำกวมต้องหยุด ไม่เดา"
sd_weak, cfg_weak, _ = make_fold(g, S.CANON, S.GROUPED, sigma=0.12)     # มีโครงแต่อ่อน (ต่ำกว่า fold จริงมาก)
eg_w = S.detect_layout(sd_weak[S.b_key(KA)], RF)[1]
assert 0.08 < eg_w < 0.35, f"ตัวอย่างอ่อนต้องอยู่ช่วงกำกวม ได้ {eg_w:.2f}"
assert refuses(lambda: S.fold_layout(cfg_weak, sd_weak, RF, log=quiet)), "โครงอ่อน (กำกวม) ต้องหยุด ไม่เดาว่า grouped"
# ชั้นแรกอ่อน/ไม่มีโครง แต่ชั้นอื่นชัด → ตัดสินจาก median ทั้งไฟล์ได้ grouped (fold จริง: ชั้น 0 ต่ำสุดคือ 0.44)
sd_l0, cfg_l0, _ = make_fold(g, S.CANON, S.GROUPED, structured=False)
sd_ok, _, _ = make_fold(g, S.CANON, S.GROUPED)
for i in (1, 2):
    Li = L.replace("layers.0.", f"layers.{i}.")
    for kk in (KA, KD):
        sd_l0[kk.replace(L, Li)], sd_l0[S.b_key(kk).replace(L, Li)] = sd_ok[kk], sd_ok[S.b_key(kk)]
assert S.fold_layout(cfg_l0, sd_l0, RF, log=quiet) == S.GROUPED, "ชั้นเดียวอ่อนต้องไม่ทำให้ทั้ง fold ถูกปฏิเสธ"
print("OK  5. layout จากตัวเลข: ไม่มีคีย์ไม่ถือเป็น grouped · ขัดกับคีย์/nested = หยุด · กำกวม/โครงอ่อน = หยุด · ชั้นเดียวอ่อนไม่ล้มทั้ง fold")

# 6 — ด้านตัดสินจากรูปร่างเทียบ base · peft_version ใช้ตรวจทาน (0.19.1 ปกติแล้ว · 0.19.0 ไม่ชี้ขาด)
assert S.peft_orientation({"peft_version": "0.18.1"}) == S.REVERSED
assert S.peft_orientation({"peft_version": "0.19.0"}) is None
assert S.peft_orientation({"peft_version": "0.19.1"}) == S.CANON
assert S.peft_orientation({"peft_version": "0.21.0.dev0"}) == S.CANON
assert S.peft_orientation({}) is None
g6 = torch.Generator().manual_seed(6)
sd_c, cfg_c, _ = make_fold(g6, S.CANON)
sd_v, cfg_v, _ = make_fold(g6, S.REVERSED)
for ver, sd_, want in (("0.19.1", sd_c, S.CANON), ("0.19.0", sd_c, S.CANON), ("0.19.0", sd_v, S.REVERSED), ("", sd_v, S.REVERSED)):
    assert S.fold_orientation({"peft_version": ver}, sd_, VALID) == want, (ver, want)
assert refuses(lambda: S.fold_orientation({"peft_version": "0.18.1"}, sd_c, VALID)), "รูปร่างปกติแต่รุ่นบอกสลับ ต้องหยุด"
assert refuses(lambda: S.fold_orientation({"peft_version": "0.20.0"}, sd_v, VALID)), "รูปร่างสลับแต่รุ่นบอกปกติ ต้องหยุด"
mixed_or = dict(sd_c)
mixed_or[KD], mixed_or[S.b_key(KD)] = sd_v[KD], sd_v[S.b_key(KD)]
assert refuses(lambda: S.fold_orientation({}, mixed_or, VALID)), "คีย์ปนด้านในไฟล์เดียวต้องหยุด"
print("OK  6. ด้านจากรูปร่าง (0.19.1 ปกติ · 0.19.0 ตามรูปร่าง) · ขัดกับ peft_version / ปนด้าน = หยุด")

# 7 — main() ทั้งเส้น (hub ปลอม): r, alpha×k, คีย์ layout, ตัด nested, config จาก fold ด้านปกติ, ลำดับ --folds
from safetensors.torch import load_file, save_file  # noqa: E402

work = Path(tempfile.mkdtemp(prefix="soup_main_"))
sds7, cfgs7, truth7 = build([(S.REVERSED,), (S.CANON, S.RANK_MAJOR, True), (S.CANON,)], seed=7)
cfgs7[1]["unsloth_fused_expert_lora"] = {"parameters": {"gate_up_proj": {"lora_B_layout": S.RANK_MAJOR}}}
repo_dir = {}
for letter, sd, cfg in zip("acd", sds7, cfgs7):
    d = work / f"Courser_{letter}"
    d.mkdir()
    save_file({k: v.contiguous() for k, v in sd.items()}, str(d / "adapter_model.safetensors"))
    (d / "adapter_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    repo_dir[f"dacarokann/Courser_{letter}"] = str(d)
bd = work / "base"
bd.mkdir()
(bd / "config.json").write_text(json.dumps(BASE_CFG), encoding="utf-8")
repo_dir["unsloth/Qwen3.6-35B-A3B"] = str(bd)
hub = types.ModuleType("huggingface_hub")
hub.snapshot_download = lambda repo, **kw: repo_dir[repo]
hub.HfApi = object
sys.modules["huggingface_hub"] = hub
cwd = os.getcwd()
_print = print
for order in (["0", "2", "3"], ["2", "0", "3"]):
    run = work / ("run_" + "".join(order))
    run.mkdir()
    os.chdir(run)
    try:
        import builtins
        builtins.print = quiet
        S.main(["--folds", *order])
    finally:
        builtins.print = _print
        os.chdir(cwd)
    out = run / "destrier_local"
    cfg = json.loads((out / "adapter_config.json").read_text(encoding="utf-8"))
    assert (cfg["r"], cfg["lora_alpha"], cfg["lora_B_layout"]) == (R, 32 * K, S.GROUPED), cfg
    assert "unsloth_fused_expert_lora" not in cfg, "nested จาก fold rank_major ต้องถูกตัด"
    assert cfg["peft_version"] == "0.20.0", "config ต้องมาจาก fold ด้านปกติ"
    assert_correct(load_file(str(out / "adapter_model.safetensors")), truth7, f"main() --folds {order}")
S.swap_orientation = old_swap          # main() ต้องไม่อัป/ต้องหยุดเมื่อโค้ดแปลงผิด (ด่านใช้ค่าอ้างอิงจาก fold ดิบ)
os.chdir(work)
try:
    assert refuses(lambda: S.main(["--folds", "0", "2", "3"])), "main() ผ่านทั้งที่โค้ดแปลงผิด"
finally:
    S.swap_orientation = real_swap
    os.chdir(cwd)
d_cfg = Path(repo_dir["dacarokann/Courser_d"]) / "adapter_config.json"
for field, val in (("r", 8), ("target_parameters", ["mlp.experts.gate_up_proj"]), ("use_rslora", True),
                   ("alpha_pattern", {"q_proj": 64})):
    d_cfg.write_text(json.dumps(dict(cfgs7[2], **{field: val})), encoding="utf-8")
    assert refuses(lambda: S.main(["--folds", "0", "2", "3"])), f"{field} ต่างกันต้องหยุด"
for field, val in (("use_rslora", True), ("alpha_pattern", {"q_proj": 64})):
    for letter, cfg in zip("acd", cfgs7):
        (Path(repo_dir[f"dacarokann/Courser_{letter}"]) / "adapter_config.json").write_text(
            json.dumps(dict(cfg, **{field: val})), encoding="utf-8")
    assert refuses(lambda: S.main(["--folds", "0", "2", "3"])), f"{field} (เท่ากันทุก fold) ต้องหยุด"
for letter, cfg in zip("acd", cfgs7):
    (Path(repo_dir[f"dacarokann/Courser_{letter}"]) / "adapter_config.json").write_text(json.dumps(cfg), encoding="utf-8")
bad_cfg = dict(cfgs7[2], lora_alpha=16)
(Path(repo_dir["dacarokann/Courser_d"]) / "adapter_config.json").write_text(json.dumps(bad_cfg), encoding="utf-8")
assert refuses(lambda: S.main(["--folds", "0", "2", "3"])), "alpha ไม่เท่ากันต้องหยุด"
assert refuses(lambda: S.main(["--folds", "0", "--out", "dacarokann/destrier"])), "ห้ามทับ destrier เดิม"
print("OK  7. main(): r=48 alpha=96 grouped · ตัด nested · config ด้านปกติ · ลำดับ --folds ไม่มีผล · "
      "alpha/r/target ต่าง, rslora, alpha_pattern = หยุด")

# 7b — ด่านต้อง "ไม่ผ่าน" เมื่อตัวคุมแยก layout ไม่ออก (E=1: grouped กับ rank_major อ่านเหมือนกัน)
g7 = torch.Generator().manual_seed(71)
A1, B1 = torch.randn(R, 6, generator=g7, dtype=torch.float64), torch.randn(8, R, generator=g7, dtype=torch.float64)
u1, v1 = torch.randn(8, 4, generator=g7, dtype=torch.float64), torch.randn(6, 4, generator=g7, dtype=torch.float64)
truth1 = S.served_probe(A1, B1, R, S.GROUPED, S.CANON, u1, v1)
assert not S.check_soup({KA: (u1, v1, truth1)}, {KA: A1, S.b_key(KA): B1}, R, log=quiet),     "ตัวคุมแยกไม่ออกแต่ด่านผ่าน"
print("OK  7b. ด่านไม่ผ่านเมื่อตัวคุมแยก layout ไม่ออก")

# 7c — fold ปน layout (บางคีย์ rank_major ไม่มีคีย์ประกาศ) · คีย์ประกาศ 'mixed' · คีย์แปลก — หยุดทั้งหมด
g8 = torch.Generator().manual_seed(8)
sd_mix, cfg_mix, _ = make_fold(g8, S.CANON, S.GROUPED)
sd_rm, _, _ = make_fold(g8, S.CANON, S.RANK_MAJOR)
L1 = L.replace("layers.0.", "layers.1.")
for kk in (KA, KD):
    sd_mix[kk.replace(L, L1)], sd_mix[S.b_key(kk).replace(L, L1)] = sd_mix[kk], sd_mix[S.b_key(kk)]
L2 = L.replace("layers.0.", "layers.2.")
sd_mix[KA.replace(L, L2)], sd_mix[S.b_key(KA).replace(L, L2)] = sd_rm[KA], sd_rm[S.b_key(KA)]
assert refuses(lambda: S.fold_layout(cfg_mix, sd_mix, RF, log=quiet)), "fold ปน layout (ส่วนน้อย) ต้องหยุด"
assert refuses(lambda: S.fold_layout({**cfg_g, "lora_B_layout": "mixed"}, sd_g, RF, log=quiet)), "ประกาศ mixed ต้องหยุด"
sds_x, cfgs_x, _ = build(DESTRIER, seed=9)
for sd in sds_x:
    sd[L + "mlp.modules_to_save.default.weight"] = torch.zeros(3, 3, dtype=torch.float64)
assert refuses(lambda: soup(sds_x, cfgs_x)), "คีย์ที่ไม่ใช่ lora_A/lora_B ต้องหยุด"
print("OK  7c. fold ปน layout / ประกาศ mixed / คีย์แปลก -> หยุด")

# 7d — fold bf16: ผลต้องเป็น fp32 และด่านผ่าน (ไม่ปฏิเสธ soup ที่ถูกเพราะปัดเศษ)
sds_h, cfgs_h, truth_h = build(DESTRIER, seed=10)
sds_h = [{k: v.to(torch.bfloat16) for k, v in sd.items()} for sd in sds_h]
m_h, ref_h = soup(sds_h, cfgs_h)
assert all(v.dtype == torch.float32 for v in m_h.values()), "ผลจาก fold bf16 ต้องเป็น fp32"
assert S.check_soup(ref_h, m_h, R, log=quiet), "fold bf16 ที่รวมถูกต้องโดนปฏิเสธ"
print("OK  7d. fold bf16 -> ผล fp32 · ด่านผ่าน")

# 8 — การแปลง layout ไป-กลับต้องได้ของเดิม
b = torch.randn(5, E * RF, dtype=torch.float64)
assert torch.equal(S.b_to_grouped(S.b_from_grouped(b, RF, S.RANK_MAJOR), RF, S.RANK_MAJOR), b)
assert torch.equal(S.b_to_grouped(b, RF, S.GROUPED), b)
print("OK  8. แปลง grouped ↔ rank_major ไป-กลับได้ของเดิม")

print("\nok — soup_safetensors.py ต่อ fold ถูกตามที่ตัวเสิร์ฟอ่าน และด่านตรวจจับบั๊กในโค้ดแปลงได้จริง")
