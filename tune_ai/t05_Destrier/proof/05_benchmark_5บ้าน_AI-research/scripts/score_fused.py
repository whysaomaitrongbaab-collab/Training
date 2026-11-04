#!/usr/bin/env python3
"""เทียบ 3 แบบด้วยเกณฑ์เข้มของ King (metrics.py ตัวจริง, เฉลย = คาน): โมเดลอย่างเดียว · โมเดล+CV (แทนที่) · โมเดล+CV (รวม)
แทนที่ = หน้าแปลนที่ fusion ได้ช่วงคาน ให้ใช้ช่วงจาก fusion แทนคานที่โมเดลตอบในหน้านั้น (ตัดสินกติกานี้ก่อนดูคะแนน)"""
import json, os, re
import score5 as S

def model_preds(res, drop_pages=()):
    out = []
    for f in res["files"]:
        m = re.match(r"page_(\d+)_", f["name"])
        if not m or f["name"].endswith((".raw.json", ".txt")) or not isinstance(f.get("json"), dict): continue
        plan = "_plan_beam" in f["name"]
        for e in f["json"].get("elements") or []:
            if isinstance(e, dict) and e.get("element_id") and e.get("element_type") == "beam":
                if plan and int(m.group(1)) in drop_pages: continue
                out.append(e)
    return out

def main():
    rows = []; T = {k: [0, 0, 0] for k in ("model", "replace", "union")}
    for tid, (folder, _) in S.HOUSES.items():
        rp = os.path.join(S.B, "out", tid, "vllm", "result.json"); fp = os.path.join(S.B, "out", tid, "fused.json")
        if not (os.path.exists(rp) and os.path.exists(fp)): continue
        res = json.load(open(rp, encoding="utf-8")); fused = json.load(open(fp, encoding="utf-8"))
        g = S.gt_elements(folder)
        pages = {f["page"] for f in fused}
        P = {"model": model_preds(res), "replace": model_preds(res, pages) + fused, "union": model_preds(res) + fused}
        r = {}
        for k, p in P.items():
            m = S.M.compute_element_metrics(g, p); r[k] = m
            T[k][0] += m["true_positives"]; T[k][1] += m["false_positives"]; T[k][2] += m["false_negatives"]
        rows.append((tid, len(fused), r))
    print(f"{'บ้าน':<8}{'ช่วงจากCV':>10} | {'โมเดลอย่างเดียว P/R/F1':>26} | {'โมเดล+CV แทนที่ P/R/F1':>26} | {'โมเดล+CV รวม P/R/F1':>24}")
    for tid, n, r in rows:
        f = lambda m: f"{m['precision']:6.1f}/{m['recall']:5.1f}/{m['f1']:5.1f}"
        print(f"{tid:<8}{n:>10} | {f(r['model']):>26} | {f(r['replace']):>26} | {f(r['union']):>24}")
    def tot(t):
        tp, fp, fn = t; P = tp / (tp + fp) * 100 if tp + fp else 0; R = tp / (tp + fn) * 100 if tp + fn else 0
        return P, R, (2 * P * R / (P + R) if P + R else 0), tp
    for k in T:
        P, R, F, tp = tot(T[k]); print(f"รวม {k:<8} P={P:.2f}% R={R:.2f}% F1={F:.2f}% (TP {tp})")
    print("King v0.2: P=7.5% R=2.18% F1=3.38%")

if __name__ == "__main__": main()
