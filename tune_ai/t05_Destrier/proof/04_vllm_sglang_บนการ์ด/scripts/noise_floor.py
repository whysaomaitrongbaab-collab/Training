"""ค่าคลาดพื้นฐานของด่าน C: base เปล่าผ่าน Unsloth vs ผ่าน transformers (ไม่มี LoRA ทั้งคู่)
ถ้าตัวนี้เองก็ต่ำกว่า 0.999 = เกณฑ์ C เข้มเกินสิ่งที่สองเส้นทางนี้ทำได้ ไม่ใช่ merge ผิด"""
import os
os.environ.setdefault("UNSLOTH_MOE_LORA_B_LAYOUT", "grouped_by_expert")
import sys
sys.path.insert(0, "/workspace/ft/tune")
import torch
from unsloth import FastVisionModel
import verify_merge as V
src = open("/workspace/ft/base_path").read().strip()
m, p = FastVisionModel.from_pretrained(model_name=src, load_in_4bit=False, dtype=torch.bfloat16)
FastVisionModel.for_inference(m)
inp = {k: (v.to(m.device) if hasattr(v, "to") else v) for k, v in V.fixed_input(p).items()}
with torch.no_grad():
    lg = m(**inp).logits[0, -1].float().cpu()
torch.save(lg, "/workspace/ft/base_unsloth.pt")
F = torch.nn.functional
b = torch.load("/workspace/ft/base.pt").float()
r = torch.load("/workspace/ft/ref.pt").float()
g = torch.load("/workspace/ft/mrg.pt").float()
print(f"ค่าคลาดพื้นฐาน base: Unsloth vs transformers cosine {F.cosine_similarity(lg, b, dim=0).item():.6f}"
      f" · top1 ตรง {int(lg.argmax()) == int(b.argmax())} · ต่างสุด {(lg - b).abs().max().item():.4f}")
print(f"merged(tf) vs adapter(Unsloth) cosine {F.cosine_similarity(g, r, dim=0).item():.6f}")
print(f"adapter(Unsloth) vs base(Unsloth)  cosine {F.cosine_similarity(r, lg, dim=0).item():.6f}  ← LoRA ขยับไปเท่าไหร่ในเส้นทางเดียวกัน")
print(f"merged(tf) vs base(tf)             cosine {F.cosine_similarity(g, b, dim=0).item():.6f}")
