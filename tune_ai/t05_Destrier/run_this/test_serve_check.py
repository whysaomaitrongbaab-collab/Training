#!/usr/bin/env python3
"""Self-check ของด่าน "LoRA ของ expert ถูกอ่านแบบที่ adapter ต้องการ" ใน serve_purson.py
รัน: python test_serve_check.py   (ไม่ต้องมี GPU/unsloth/peft — ใช้ของปลอมแทน)

ผูกกับความพังจริง 2026-09-27: dacarokann/destrier ตอบ JSON สวยงามมาตลอดทั้งที่ LoRA ของ expert
ปนผิด ไม่มี error สักตัว — ด่านนี้คือสิ่งเดียวที่ทำให้ "อ่านผิดแบบ" กลายเป็นเสียงดัง
ต้องแยกให้ออก 3 อย่าง: ถูกแน่ (ไปต่อ) · ผิดแน่ (ปฏิเสธทุกคำขอ) · ตรวจไม่ได้ (เตือนแล้วไปต่อ)
และห้ามปิดเซิร์ฟเวอร์ — presentation.py จะตีว่าเครื่องเสีย คืนการ์ดดีทิ้งแล้วขึ้นบัญชีดำ
"""
import json
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import serve_purson as S  # noqa: E402


def _patched_param_wrapper_forward(self, *a, **k):   # ชื่อเดียวกับตัวแปะของ unsloth_zoo
    pass


def _peft_forward(self, *a, **k):
    pass


class ParamWrapper:                      # ปลอมของ peft.tuners.lora.layer.ParamWrapper
    forward = _patched_param_wrapper_forward

    def __init__(self, num_experts, layout, stash):
        self.num_experts, self.layout, self.stash = num_experts, layout, stash


def install_fakes(zoo_ok=True):
    peft_layer = types.ModuleType("peft.tuners.lora.layer")
    peft_layer.ParamWrapper = ParamWrapper
    for name in ("peft", "peft.tuners", "peft.tuners.lora"):
        sys.modules[name] = types.ModuleType(name)
    sys.modules["peft.tuners.lora.layer"] = peft_layer
    for name in ("unsloth_zoo", "unsloth_zoo.temporary_patches"):
        sys.modules[name] = types.ModuleType(name)
    mu = types.ModuleType("unsloth_zoo.temporary_patches.moe_utils")
    if zoo_ok:
        # เหมือนของจริง (zoo 9.7 moe_utils.py:2270): วัดได้ False = ตกไปทาง PEFT = rank_major
        mu.moe_lora_b_layout_for_wrapper = lambda w: RM if w.stash is False else w.layout
        mu._wrapper_forward_applies_stash = lambda w: w.stash
    sys.modules["unsloth_zoo.temporary_patches.moe_utils"] = mu


class Model:
    def __init__(self, wrappers):
        self.wrappers, self.generated = wrappers, 0

    def named_modules(self):
        yield "base_model.model.model", object()
        for i, w in enumerate(self.wrappers):
            yield f"base_model.model.model.language_model.layers.{i}.mlp.experts", w

    def generate(self, **kw):
        self.generated += 1


class Batch(dict):
    def to(self, _dev):
        return self


def tok(images, text, **kw):
    return Batch(input_ids=[[1]])


def adapter_dir(layout_key=None):
    d = tempfile.mkdtemp(prefix="adapter_")
    cfg = {"r": 48}
    if layout_key:
        cfg["lora_B_layout"] = layout_key
    Path(d, "adapter_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return d


G, RM = "grouped_by_expert", "rank_major"
install_fakes()

# 1. ถูกแน่: ทุก wrapper อ่าน grouped ผ่านทาง Unsloth + adapter ไม่มีคีย์ (= legacy grouped)
m = Model([ParamWrapper(256, G, True), ParamWrapper(256, G, True)])
assert S.check_expert_lora(m, tok, adapter_dir()) is None
assert m.generated == 1, "ต้องยิง forward จริงหนึ่งครั้งก่อนถาม — ไม่งั้น Unsloth ยังไม่ได้วัดทางที่ใช้จริง"
print("OK  1. อ่านถูกแบบ + ผ่านทาง Unsloth -> ไปต่อ (และยิง warmup ก่อนถามเสมอ)")

# 2. ผิดแน่: env ไม่ได้ตั้ง Unsloth เลยอ่าน rank_major กับ adapter ที่ต้องการ grouped
m = Model([ParamWrapper(256, RM, True), ParamWrapper(256, RM, True)])
why = S.check_expert_lora(m, tok, adapter_dir())
assert why and "2/2" in why and "grouped_by_expert" in why, why
print("OK  2. อ่านผิดแบบ -> คืนเหตุผล (บอกจำนวนตัวที่ผิด + วิธีแก้)")

# 3. ผิดแน่แบบเงียบที่สุด: layout ถูกแต่ตัวแปะของ Unsloth ไม่ทำงาน ตกไปทาง PEFT
m = Model([ParamWrapper(256, G, True), ParamWrapper(256, G, False)])
why = S.check_expert_lora(m, tok, adapter_dir())
assert why and "1/2" in why, why
print("OK  3. ตัวแปะ Unsloth ไม่ทำงาน (ตกไปทาง PEFT) -> จับได้แม้ env ถูก")

# 3b. layout ถูกแต่ Unsloth ยังไม่ได้วัด (None) -> ไม่ใช่หลักฐานว่าผิด ห้ามปฏิเสธทุกคำขอ
m = Model([ParamWrapper(256, G, True), ParamWrapper(256, G, None)])
assert S.check_expert_lora(m, tok, adapter_dir()) is None
print("OK  3b. Unsloth ยังไม่ได้วัด -> เตือนแล้วไปต่อ (ไม่ปฏิเสธเพราะเดา)")

# 3c. ตัวแปะของ Unsloth ไม่ได้ติดตั้งเลย (forward ยังเป็นของ PEFT) -> PEFT อ่าน rank_major เสมอ
#     ทั้งที่ layout_for ตอบตาม env ว่า grouped และวัดได้ None — ต้องปฏิเสธ (รีวิว 27 ก.ย.)
ParamWrapper.forward = _peft_forward
m = Model([ParamWrapper(256, G, None), ParamWrapper(256, G, None)])
why = S.check_expert_lora(m, tok, adapter_dir())
assert why and "2/2" in why and "ไม่ติด" in why, why
#     กลับกัน: adapter เป็น rank_major + ไม่มีตัวแปะ = PEFT อ่านถูก -> ไปต่อ
assert S.check_expert_lora(m, tok, adapter_dir(RM)) is None
ParamWrapper.forward = _patched_param_wrapper_forward
print("OK  3c. ตัวแปะ Unsloth ไม่ติดตั้ง -> ปฏิเสธ adapter grouped · ปล่อย adapter rank_major")

# 3d. ติดตัวแปะแต่ experts forward ส่งกลับให้ PEFT (วัดได้ False) + adapter rank_major = ถูก ห้ามปฏิเสธ
m = Model([ParamWrapper(256, RM, False)])
assert S.check_expert_lora(m, tok, adapter_dir(RM)) is None
print("OK  3d. วัดได้ False กับ adapter rank_major -> ไปต่อ (ไม่ปฏิเสธของที่ถูก)")

# 3e. zoo รุ่นหน้าห่อตัวแปะด้วย functools.wraps (ชื่อกลายเป็นของ PEFT) -> ยังต้องรู้ว่าติด ไม่ปฏิเสธเครื่องดี
import functools  # noqa: E402
_wrapped = types.FunctionType(_patched_param_wrapper_forward.__code__, {})
ParamWrapper.forward = functools.wraps(_peft_forward)(_wrapped)
assert ParamWrapper.forward.__name__ == "_peft_forward"
m = Model([ParamWrapper(256, G, None), ParamWrapper(256, G, None)])   # ยังไม่มีผลวัดเลย ดูจาก code อย่างเดียว
assert S.check_expert_lora(m, tok, adapter_dir()) is None
ParamWrapper.forward = _peft_forward
m = Model([ParamWrapper(256, G, True), ParamWrapper(256, G, True)])   # code ไม่ตรง แต่มีผลวัด = ตัวแปะรันแล้ว
assert S.check_expert_lora(m, tok, adapter_dir()) is None
ParamWrapper.forward = _patched_param_wrapper_forward
print("OK  3e. ตัวแปะโดน wraps เปลี่ยนชื่อ / ชื่อไม่ตรงแต่มีผลวัด -> รู้ว่าติด ไม่ปฏิเสธเครื่องดี")

# 4. adapter ประกาศ rank_major เอง (soup/เทรนรุ่นใหม่) + ตัวเสิร์ฟอ่าน rank_major -> ถูก
m = Model([ParamWrapper(256, RM, True)])
assert S.check_expert_lora(m, tok, adapter_dir(RM)) is None
print("OK  4. adapter ประกาศ layout เอง -> ยึดตาม adapter ไม่ยึด env")

# 5. ไม่มี LoRA ของ expert (เสิร์ฟ base / num_experts=1) -> ข้าม ไม่ยิง warmup
m = Model([ParamWrapper(1, RM, None)])
assert S.check_expert_lora(m, tok, adapter_dir()) is None and m.generated == 0
print("OK  5. ไม่มี LoRA ของ expert -> ข้ามการตรวจ")

# 6. ตรวจไม่ได้ (unsloth_zoo รุ่นที่ไม่มีฟังก์ชันนี้) -> เตือนแล้วไปต่อ ไม่ปฏิเสธ
install_fakes(zoo_ok=False)
m = Model([ParamWrapper(256, RM, True)])
assert S.check_expert_lora(m, tok, adapter_dir()) is None
install_fakes()
print("OK  6. ตรวจไม่ได้ -> ไปต่อแบบไม่ยืนยัน (ไม่เดาว่าผิด)")

# 7. warmup พัง (เช่น processor เปลี่ยน signature) -> ห้ามทำเซิร์ฟเวอร์ล้ม
m = Model([ParamWrapper(256, G, True)])
m.generate = lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))
assert S.check_expert_lora(m, tok, adapter_dir()) is None
print("OK  7. ด่านพังเอง -> ไปต่อ ไม่ลากเซิร์ฟเวอร์ลงไปด้วย")

# 8. ห้ามปิดเซิร์ฟเวอร์เมื่อผิด — main() ต้องเก็บเหตุผลไว้ปฏิเสธคำขอ ไม่ใช่ sys.exit
src = Path(S.__file__).read_text(encoding="utf-8")
body = src[src.index("def check_expert_lora("):src.index("def build_grammar(")]
assert "sys.exit" not in body and "raise SystemExit" not in body, "ด่านนี้ห้ามปิดเซิร์ฟเวอร์"
chat = src[src.index("async def chat("):src.index("want_json =")]
assert '_state.get("refuse")' in chat, "chat ต้องเช็ค refuse ก่อนสร้างคำตอบ"
main = src[src.index("def main("):]
assert "refuse=refuse" in main and "check_expert_lora(model, tok, src)" in main
print("OK  8. อ่านผิด -> ปฏิเสธทุกคำขอพร้อมเหตุผล (ไม่ปิดเซิร์ฟเวอร์ ไม่ให้การ์ดดีโดนทิ้ง)")



# 9. presentation.py smoke: 500 ธรรมดารอบแรก -> รอบสองต้องส่ง payload เดิม (เคยโดนตัวแปร body ทับ) ·
#    500 ที่เป็นเหตุผลจากด่านนี้ -> หยุดทันทีพร้อมบอกว่าการ์ดไม่ได้เสีย
import io  # noqa: E402
import urllib.error  # noqa: E402
import presentation as P  # noqa: E402

sent = []


def fake_urlopen(responses):
    def _open(req, timeout=None):
        sent.append(req.data)
        code, text = responses.pop(0)
        if code != 200:
            raise urllib.error.HTTPError(req.full_url, code, "err", {}, io.BytesIO(text.encode("utf-8")))
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": text}}]}).encode())
    return _open


P.time.sleep = lambda s: None
P.urllib.request.urlopen = fake_urlopen([(500, "CUDA OOM"), (200, '{"ok": true}')])
P.cmd_smoke(None)
assert len(sent) == 2 and sent[0] == sent[1] and isinstance(sent[1], bytes), sent
sent.clear()
P.urllib.request.urlopen = fake_urlopen([(500, '{"error": {"message": "LoRA ของ MoE expert ถูกอ่านผิดแบบ (80/80 ตัว)"}}')])
try:
    P.cmd_smoke(None)
    raise AssertionError("ต้องหยุด")
except SystemExit as e:
    assert "ห้าม down --bad" in str(e) and len(sent) == 1, (e, sent)
print("OK  9. smoke: 500 ธรรมดาลองใหม่ด้วย payload เดิม · 500 จากด่าน LoRA หยุดทันที บอกว่าการ์ดไม่เสีย")


print("\nok — ด่านตรวจ LoRA ของ expert แยก ถูก/ผิด/ตรวจไม่ได้ ครบ")
