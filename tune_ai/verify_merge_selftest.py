#!/usr/bin/env python3
"""พิสูจน์ว่า "ด่านตรวจ" check_b แยก packing ถูก/ผิดได้จริง — บน adapter ตัวจริง ไม่ใช่ของปลอม

ทำไมต้องมีไฟล์นี้: check_b ตัวจริงต้องใช้โมเดล merged ซึ่งยังไม่มี (ต้องเช่าการ์ดจอก่อน)
แต่ถ้าตัวด่านเองแยกไม่ออก เราจะเอาไปตัดสินผล merge ที่จ่ายเงินไปแล้วไม่ได้
ไฟล์นี้จึงสังเคราะห์ ΔW จาก adapter จริงตาม layout ที่เชื่อว่าถูก แล้วดูว่าด่านชี้กลับมาถูกไหม

ข้อจำกัดที่ต้องรู้: นี่คือ self-consistency test — พิสูจน์ว่า "ด่านแยกออก"
ไม่ได้พิสูจน์ว่า "merge จะถูก" (พิสูจน์ไม่ได้จนกว่าจะมีโมเดล merged จริง)
"""
import glob, json, os, sys
import torch
from safetensors import safe_open

NUM_EXPERTS = 256
HUB = os.path.expanduser("~/.cache/huggingface/hub/models--dacarokann--destrier")

# รับ path ของ adapter จาก argv ได้ ไม่งั้นหาใน HF cache ของเครื่องนี้
if len(sys.argv) > 1:
    AD = sys.argv[1]
else:
    snaps = glob.glob(os.path.join(HUB, "snapshots", "*"))
    if not snaps:
        sys.exit(f"⛔ ไม่เจอ snapshot ใน {HUB} — ส่ง path ของ adapter มาเป็น argument แทนได้")
    AD = snaps[0]
print(f"adapter: {AD}\n")

cfg = json.load(open(os.path.join(AD, "adapter_config.json"), encoding="utf-8"))
alpha = cfg.get("lora_alpha")
print(f"adapter_config: r={cfg.get('r')} alpha={alpha} "
      f"lora_B_layout={cfg.get('lora_B_layout', '<ไม่มีคีย์นี้>')}")
if "lora_B_layout" not in cfg:
    print("  → ไม่มีคีย์ lora_B_layout = adapter รุ่นเก่า แปลว่า grouped_by_expert\n")

files = sorted(glob.glob(os.path.join(AD, "*.safetensors")))
if not files:
    sys.exit("⛔ ไม่เจอไฟล์ safetensors ของ adapter")

# หา lora_A/lora_B คู่แรกของชั้น experts ที่หารด้วย 256 ลงตัว
pair = None
for fp in files:
    with safe_open(fp, framework="pt") as f:
        for k in f.keys():
            if not (k.endswith("lora_A.weight") and "experts" in k):
                continue
            kb = k[: -len("lora_A.weight")] + "lora_B.weight"
            if kb not in f.keys():
                continue
            sa, sb = f.get_slice(k).get_shape(), f.get_slice(kb).get_shape()
            if len(sa) == 2 and len(sb) == 2 and sa[0] == sb[1] and sa[0] % NUM_EXPERTS == 0:
                pair = (fp, k, kb, sa, sb); break
    if pair: break

if not pair:
    sys.exit("⛔ หาคู่ lora_A/lora_B ของชั้น experts ไม่เจอ")

fp, ka, kb, sa, sb = pair
E, r = NUM_EXPERTS, sa[0] // NUM_EXPERTS
scale = (alpha / r) if alpha else 1.0
print(f"ใช้: {ka.split('language_model.')[-1]}")
print(f"  A {sa}  B {sb}  →  E={E} r={r} scale=alpha/r={scale:.4f}\n")

with safe_open(fp, framework="pt") as f:
    A = f.get_tensor(ka).float()
    B = f.get_tensor(kb).float()

def unpack_a(mode):   # → [E, r, in]   (คัดลอกจาก verify_merge.py ตรงๆ)
    return A.view(E, r, -1) if mode == "grp" else A.view(r, E, -1).permute(1, 0, 2)

def unpack_b(mode):   # → [E, r, out]
    return (B.view(-1, E, r).permute(1, 2, 0) if mode == "grp"
            else B.view(-1, r, E).permute(2, 1, 0))

P = 4   # ทดสอบ 4 expert แรกพอ ประหยัด RAM
TRUTH = ("grp", "grp")   # layout ที่เชื่อว่าถูก (adapter เก่า = grouped_by_expert)

a_t = unpack_a(TRUTH[0])[:P].transpose(1, 2).contiguous()
b_t = unpack_b(TRUTH[1])[:P].contiguous()
dW = scale * torch.bmm(a_t, b_t)
ref = dW.norm()
print(f"สังเคราะห์ ΔW จาก layout {TRUTH} · {P} expert · norm={ref:.2f}\n")
print("ด่านตรวจไล่ทั้ง 4 แบบ:")

results = []
for ma in ("grp", "rank"):
    for mb in ("grp", "rank"):
        try:
            a = unpack_a(ma)[:P].transpose(1, 2).contiguous()
            b = unpack_b(mb)[:P].contiguous()
            err = ((dW - scale * torch.bmm(a, b)).norm() / ref).item()
        except Exception as e:
            print(f"   A={ma:4s} B={mb:4s}  แกะไม่ได้ ({type(e).__name__})"); continue
        results.append((err, (ma, mb)))
        mark = "  ← ตัวที่ใช้สังเคราะห์" if (ma, mb) == TRUTH else ""
        print(f"   A={ma:4s} B={mb:4s}  ความคลาดเคลื่อน {err:.4f}{mark}")

best_err, best = min(results)
wrong = [e for e, m in results if m != TRUTH]
print(f"\n→ ด่านชี้ว่าตรงที่สุด: A={best[0]} B={best[1]} ({best_err:.4f})")

ok = True
if best != TRUTH:
    print("⛔ ไม่ผ่าน: ด่านชี้ผิดตัว — เอาไปตัดสินผล merge ไม่ได้"); ok = False
elif best_err > 0.05:
    print(f"⛔ ไม่ผ่าน: ตัวที่ถูกยังคลาดเคลื่อน {best_err:.4f} > เกณฑ์ 0.05"); ok = False
elif wrong and min(wrong) < 0.5:
    print(f"⛔ ไม่ผ่าน: ตัวผิดที่ใกล้สุดคลาดเคลื่อนแค่ {min(wrong):.4f} — แยกไม่ขาด"); ok = False
else:
    sep = min(wrong) / best_err if best_err > 0 else float("inf")
    print(f"✅ ผ่าน: ตัวถูก {best_err:.4f} · ตัวผิดใกล้สุด {min(wrong):.4f} · ห่างกัน {sep:.0f} เท่า")
    print("   ด่านนี้เชื่อถือได้ ใช้ตัดสินผล merge จริงได้")

print("\nหมายเหตุ: นี่พิสูจน์ว่า 'ด่านแยกออก' ไม่ได้พิสูจน์ว่า 'merge จะถูก'")
print("          อันหลังต้องมีโมเดล merged จริงเท่านั้น (= ต้องเช่าการ์ดจอ)")
sys.exit(0 if ok else 1)
