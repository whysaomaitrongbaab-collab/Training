#!/usr/bin/env python3
"""gate_d_t07.py — ด่าน D ของ t07 Palfrey: ตัวเสิร์ฟ (vLLM) คำนวณได้เท่ากับไฟล์ merged ที่ผ่านด่าน C ไหม

⚠️ UNTESTED บนการ์ด (ร่าง 11 พ.ย. 69) — ที่ทดสอบแล้วมีแค่กติกาตัดสิน (--selftest ด้วยตัวเลขจริงจาก proof/04)

คำขอ = ของ tune_ai/verify_merge.py --probe-server ทุกอย่าง (ภาพ/ข้อความ import จากไฟล์นั้นเอง = input เดียวกับตอน
ทำ fingerprint merged) · ต่างกันแค่เกณฑ์ผ่าน ซึ่ง **ตัดสินแล้ว 11 พ.ย. 69**:
  ผ่าน ถ้า (ก) token อันดับ 1 ตรงกัน และ top-5 ซ้อนกัน >= 4/5                          ← เกณฑ์เดิมของ verify_merge.py
        หรือ (ข) อันดับ 1 สลับกันระหว่าง ``` กับ {" เท่านั้น และ top-5 ซ้อนกันครบ 5/5
             และ |Δlogprob| สูงสุดใน top-5 < 0.7
  นอกนั้นไม่ผ่าน
ที่มาของข้อ (ข): proof/04 และ proof/05 ตัวเสิร์ฟ vLLM สลับ ``` / {" ที่ Δ 0.678 ทั้งสองรอบ ทั้งที่ merged ผ่านด่าน C
และผลอ่านบ้านดี — เกณฑ์เดิมจึงทิ้งโมเดลที่ถูก · ใต้ JSON grammar ของ worker สองตัวนี้ไม่ต่างกัน

    python gate_d_t07.py --url http://localhost:8000 --ref /workspace/ft/mrg.pt \\
        --merged /workspace/palfrey_merged --tune /workspace/ft/tune
    python gate_d_t07.py --selftest
"""
import argparse
import sys

SWAP_PAIR = {"```", '{"'}
MAX_DELTA = 0.7
TOP = 10


def verdict(srv, want):
    """srv/want = [(token, logprob)] เรียงมากไปน้อย (ตัวเสิร์ฟ / อ้างอิง) → (ผ่าน, เหตุผล)
    นับแบบเดียวกับ verify_merge.probe_server: Δ คิดจาก token ใน top-5 ของอ้างอิงที่เจอใน top-10 ของตัวเสิร์ฟ"""
    srv, want = srv[:TOP], want[:TOP]
    top1 = bool(srv) and bool(want) and srv[0][0] == want[0][0]
    overlap5 = len({t for t, _ in srv[:5]} & {t for t, _ in want[:5]})
    common = dict(srv)
    diffs = [abs(common[t] - v) for t, v in want[:5] if t in common]
    d = max(diffs) if diffs else float("inf")
    if top1 and overlap5 >= 4:
        return True, f"ผ่านเกณฑ์ (ก): อันดับ 1 ตรง · top-5 {overlap5}/5 · Δ {d:.3f}"
    if (srv and want and not top1 and {srv[0][0], want[0][0]} == SWAP_PAIR
            and overlap5 == 5 and d < MAX_DELTA):
        return True, f"ผ่านเกณฑ์ (ข): อันดับ 1 สลับ ``` / {{\" · top-5 5/5 · Δ {d:.3f} < {MAX_DELTA}"
    return False, f"ไม่ผ่าน: อันดับ 1 ตรง {top1} · top-5 {overlap5}/5 · Δ {d:.3f}"


def probe(url, ref_p, tok_dir, tune_dir):
    import base64
    import io
    import requests
    import torch
    from transformers import AutoTokenizer
    sys.path.insert(0, tune_dir)
    import verify_merge as V    # fixed_image / FIXED_TEXT ชุดเดียวกับ fingerprint
    buf = io.BytesIO()
    V.fixed_image().save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    body = {"model": "purson", "max_tokens": 1, "temperature": 0.0,
            "logprobs": True, "top_logprobs": 20,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": V.FIXED_TEXT}]}]}
    r = requests.post(f"{url.rstrip('/')}/v1/chat/completions", json=body, timeout=300)
    r.raise_for_status()
    got = r.json()["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
    srv = [(g["token"], float(g["logprob"])) for g in got][:TOP]
    tok = AutoTokenizer.from_pretrained(tok_dir)
    ref = torch.log_softmax(torch.load(ref_p).float(), dim=0)
    vals, ids = ref.topk(TOP)
    want = [(tok.decode([int(i)]), float(v)) for v, i in zip(vals, ids)]
    print(f"\nD: {url} เทียบ merged ({tok_dir})")
    print(f"   {'อันดับ':6} {'ตัวเสิร์ฟ':>24} {'อ้างอิง':>24}")
    for k in range(TOP):
        s = srv[k] if k < len(srv) else ("-", float("nan"))
        print(f"   {k + 1:<6} {repr(s[0]):>16} {s[1]:7.3f} {repr(want[k][0]):>16} {want[k][1]:7.3f}")
    return srv, want


# ตัวเลขจริงจาก proof/04 logs/probeD_vllm.log (สลับอันดับ 1) และ probeD_prodvllm.log (อันดับ 1 ตรง)
REF04 = [("```", -1.285), ('{"', -1.973), ("ดู", -2.723), ("คุณ", -2.910), ("{", -3.098),
         ("ฉัน", -3.848), ("อธิบาย", -4.223), ("นี่", -4.348), ("ต้อง", -4.348), ("เนื่องจาก", -4.473)]
VLLM04 = [('{"', -1.295), ("```", -1.607), ("คุณ", -2.545), ("ดู", -2.857), ("{", -2.982),
          ("ฉัน", -4.107), ("อธิบาย", -4.295), ("นี่", -4.482), ("เนื่องจาก", -4.732), ("ต้อง", -4.795)]
PROD04 = [("```", -1.406), ('{"', -1.843), ("คุณ", -2.718), ("ดู", -2.718), ("{", -3.156),
          ("ฉัน", -3.843), ("อธิบาย", -4.031), ("เนื่องจาก", -4.156), ("ต้อง", -4.468), ("ตอบ", -4.468)]


def selftest():
    def ok(srv, want=REF04):
        return verdict(srv, want)[0]
    assert ok(VLLM04), "proof/04 vLLM (สลับ ``` / {\" Δ 0.678 · 5/5) ต้องผ่านเกณฑ์ (ข)"
    assert "Δ 0.678" in verdict(VLLM04, REF04)[1], "Δ ต้องคิดแบบเดียวกับ verify_merge (log proof/04 = 0.678)"
    assert ok(PROD04), "proof/04 prodvllm (อันดับ 1 ตรง Δ 0.192) ต้องผ่านเกณฑ์ (ก)"
    four = VLLM04[:4] + [("ไม่มี", -2.99)] + VLLM04[5:]
    assert not ok(four), "สลับแต่ top-5 ซ้อนแค่ 4/5 → ไม่ผ่าน"
    far = [('{"', -1.223)] + VLLM04[1:]          # |-1.223 - -1.973| = 0.750
    assert not ok(far), "สลับแต่ Δ 0.75 → ไม่ผ่าน"
    edge_ref = [REF04[0], ('{"', -1.5)] + REF04[2:]
    edge = [('{"', -0.8)] + VLLM04[1:]           # |-0.8 - -1.5| == 0.7 (double เดียวกับ 0.7) → ต้องน้อยกว่า
    assert not ok(edge, edge_ref), "Δ = 0.7 พอดี → ไม่ผ่าน"
    other = [("{", -1.30), ("```", -1.60), ("คุณ", -2.55), ("ดู", -2.86), ('{"', -2.98)] + VLLM04[5:]
    assert not ok(other), "อันดับ 1 ต่างแต่ไม่ใช่คู่ ``` / {\" → ไม่ผ่าน"
    three = PROD04[:3] + [("ก", -2.7), ("ข", -3.1)] + PROD04[5:]
    assert not ok(three), "อันดับ 1 ตรงแต่ top-5 ซ้อน 3/5 → ไม่ผ่าน"
    assert not ok([], REF04) and not ok(VLLM04, []), "ว่าง → ไม่ผ่าน"
    print("selftest ผ่าน 9 ข้อ — กติกาด่าน D ของ t07 ตรงตามที่ตัดสินไว้")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--ref", help="mrg.pt (verify_merge.py --fingerprint merged ของการ์ดนี้)")
    ap.add_argument("--merged", help="โฟลเดอร์ merged (เอา tokenizer)")
    ap.add_argument("--tune", default="/workspace/ft/tune", help="โฟลเดอร์ที่มี verify_merge.py")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if not (a.ref and a.merged):
        sys.exit("⛔ ต้องใส่ --ref mrg.pt และ --merged <โฟลเดอร์ merged>")
    srv, want = probe(a.url, a.ref, a.merged, a.tune)
    passed, why = verdict(srv, want)
    print(f"   {why}")
    print("✅ D ผ่าน" if passed else "⛔ D ไม่ผ่าน — engine นี้คำนวณไม่เท่ากับไฟล์ merged อย่าใช้ผลวัดจากมัน")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
