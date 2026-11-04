#!/usr/bin/env python3
"""ให้คะแนน Destrier (vLLM) บนบ้านทดสอบ 5 หลังของ AI-research ด้วยเกณฑ์เดียวกับ King (src/evaluation/metrics.py ตัวจริง)
เฉลย = ชิ้น element_type=='beam' ทุกหน้าใน json_แก้ไขแล้ว (นับได้ 50/46/86/86/61 เทียบของ King 50/46/87/86/61)"""
import glob, importlib.util, json, os, re, sys
from collections import Counter
B = r"D:\Temp\claude\3049db1b73f5b7d5\c641593e-2919-41af-bebc-66157c3c1ea4\scratchpad\bench5"
GT = r"D:\00mk\steel project\training\Training\json_แก้ไขแล้ว"
spec = importlib.util.spec_from_file_location("metrics", r"D:\00mk\steel project\AI-research\src\evaluation\metrics.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
HOUSES = {"TEST-01": ("08บ้าน_เล็ก_1ชั้น_03", 50), "TEST-02": ("11บ้าน_เล็ก_1ชั้น_06", 46), "TEST-03": ("03บ้าน_เล็ก_2ชั้น_01", 87),
          "TEST-04": ("27บ้าน_เล็ก_2ชั้น_06", 86), "TEST-05": ("34บ้าน_ใหญ่_1ชั้น_02", 61)}
KING = {"v0.2 Hybrid-Vector-VLM-Engine": (7.5, 2.18, 3.38)}
TYPES = ("beam",)

def gt_elements(folder, types=TYPES):
    out = []
    for f in sorted(glob.glob(os.path.join(GT, folder, "*.json"))):
        try: d = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        if isinstance(d, dict):
            out += [e for e in d.get("elements") or [] if isinstance(e, dict) and e.get("element_id") and e.get("element_type") in types]
    return out

def pred_elements(res, types=TYPES):
    out = []
    for f in res["files"]:
        if not re.match(r"page_\d+_", f["name"]) or f["name"].endswith((".raw.json", ".txt")) or not isinstance(f.get("json"), dict): continue
        out += [e for e in f["json"].get("elements") or [] if isinstance(e, dict) and e.get("element_id") and e.get("element_type") in types]
    return out

def main():
    rows, T = [], dict(tp=0, fp=0, fn=0)
    for tid, (folder, king_n) in HOUSES.items():
        rp = os.path.join(B, "out", tid, "vllm", "result.json"); sp = os.path.join(B, "out", tid, "vllm", "summary.json")
        if not os.path.exists(rp): print(tid, folder, "— ยังไม่มีผล"); continue
        res = json.load(open(rp, encoding="utf-8")); summ = json.load(open(sp, encoding="utf-8"))
        g, p = gt_elements(folder), pred_elements(res)
        m = M.compute_element_metrics(g, p)
        T["tp"] += m["true_positives"]; T["fp"] += m["false_positives"]; T["fn"] += m["false_negatives"]
        pages = len(json.load(open(os.path.join(B, tid, "job.json")))["payload"]["pages"])
        bk = summ["by_kind"]
        rows.append((tid, folder, pages, summ["wall_s"], len(g), king_n, len(p), m, summ["all"]["n"], summ["all"]["json_ok"], summ["timings"]))
    print(f"{'บ้าน':<8}{'หน้า':>5}{'เวลา(วิ)':>10}{'เวลา(นาที)':>11}{'เฉลย':>6}{'(King)':>7}{'ทาย':>5}{'TP':>4}{'FP':>5}{'FN':>5}{'P%':>7}{'R%':>7}{'F1%':>7}{'คำขอ':>6}{'JSONผ่าน':>9}")
    for tid, folder, pages, wall, ng, kn, npred, m, ncalls, nok, tm in rows:
        print(f"{tid:<8}{pages:>5}{wall:>10.0f}{wall/60:>11.1f}{ng:>6}{kn:>7}{npred:>5}{m['true_positives']:>4}{m['false_positives']:>5}{m['false_negatives']:>5}{m['precision']:>7}{m['recall']:>7}{m['f1']:>7}{ncalls:>6}{nok:>9}")
    tp, fp, fn = T["tp"], T["fp"], T["fn"]
    # ภาพรวมเสริม: (ก) คานแบบดูแค่มาร์ค (ไม่ดูปลายช่วง) (ข) ทุกชนิดโครงสร้างแบบเข้มเหมือน King
    STRUCT = ("beam", "girder", "column", "footing", "slab")
    print()
    print("มุมมองเสริม (ผ่อนเกณฑ์/ขยายชนิด เพื่อดูว่าพลาดตรงไหน — ไม่ใช่เกณฑ์ของ King)")
    print(f"{'บ้าน':<8}{'คานมาร์คตรง R%':>16}{'P%':>8}{'  โครงสร้างทุกชนิดเข้ม R%':>26}{'P%':>8}")
    ta = [0, 0, 0]; tb = [0, 0, 0]
    for tid, (folder, _) in HOUSES.items():
        rp = os.path.join(B, "out", tid, "vllm", "result.json")
        if not os.path.exists(rp): continue
        res = json.load(open(rp, encoding="utf-8"))
        g, p = gt_elements(folder), pred_elements(res)
        gi = {((e.get("element_id") or "").strip().upper()) for e in g}; pi = {((e.get("element_id") or "").strip().upper()) for e in p}
        a_tp, a_fp, a_fn = len(gi & pi), len(pi - gi), len(gi - pi)
        g2, p2 = gt_elements(folder, STRUCT), pred_elements(res, STRUCT)
        m2 = M.compute_element_metrics(g2, p2)
        for t, v in ((ta, (a_tp, a_fp, a_fn)), (tb, (m2["true_positives"], m2["false_positives"], m2["false_negatives"]))):
            for i in range(3): t[i] += v[i]
        print(f"{tid:<8}{a_tp/(a_tp+a_fn)*100 if a_tp+a_fn else 0:>16.1f}{a_tp/(a_tp+a_fp)*100 if a_tp+a_fp else 0:>8.1f}{m2['recall']:>26.2f}{m2['precision']:>8.2f}")
    def pr(t): return (t[0]/(t[0]+t[2])*100 if t[0]+t[2] else 0, t[0]/(t[0]+t[1])*100 if t[0]+t[1] else 0)
    print(f"{'รวม':<8}{pr(ta)[0]:>16.1f}{pr(ta)[1]:>8.1f}{pr(tb)[0]:>26.2f}{pr(tb)[1]:>8.2f}")
    if rows:
        P = tp / (tp + fp) * 100 if tp + fp else 0; R = tp / (tp + fn) * 100 if tp + fn else 0; F = 2 * P * R / (P + R) if P + R else 0
        print(f"รวม (micro เหมือน King): P={P:.2f}% R={R:.2f}% F1={F:.2f}%  | เวลารวม {sum(r[3] for r in rows)/60:.1f} นาที · {sum(r[2] for r in rows)} หน้า")
        for k, (p_, r_, f_) in KING.items(): print(f"ของ King {k}: P={p_}% R={r_}% F1={f_}%")

if __name__ == "__main__": main()
