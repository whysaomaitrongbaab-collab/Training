#!/usr/bin/env python3
"""op04_score.py — วัด recall ของ destrier เทียบเฉลยมือ (บ้านไทยพอเพียง3 หน้า 26/27)

3 ตัวเลข ตีความต่างกัน อย่าปนกัน:
1. strict (กติกา t01 eval_fields.py): จับคู่ tuple (element_id, grid_ref_start, grid_ref_end)
   str-equality เป๊ะ ไม่ normalize — เทียบกับ 28.2% ของ t01 ได้ตรงที่สุด (lower bound)
2. id_norm: จับคู่ element_id หลัง normalize (casefold, ตัดช่องว่าง) แบบ multiset
   (คานหลายท่อน id เดียวกัน นับ min(จำนวนท่อน gold, pred)) — วัดว่า "รู้จัก mark ครบไหม"
3. position (เฉพาะหน้าฐานราก): ขยายเป็นรายตำแหน่ง (id, grid_ref) แล้วจับคู่หลัง
   normalize grid ref ("1-A"/"A-1"/"A1" → เท่ากัน) — วัดว่า "วางตำแหน่งถูกไหม"

หน้า JSON เสีย: นับ gold เต็มใน denominator, found=0 (กติกา t01)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

OUT = Path(__file__).parent / "results" / "op04"


def norm_id(s):
    return re.sub(r"\s+", "", str(s)).casefold()


def mark_base(s):
    """"F4,C1" → "f4" — mark ในแบบพิมพ์ติดกันเป็นคู่ (ฐานราก,เสา) แต่ธรรมเนียม GT
    แยกเป็นคนละ element · ใช้วัดว่า "อ่านตัวฐานรากถูกไหม" แยกจากปัญหาธรรมเนียมบันทึก"""
    return norm_id(s).split(",")[0]


def norm_ref(s):
    """"1-A" / "A-1" / "A1" / "a 1" → ("A","1") — ตัวอักษรขึ้นก่อนเสมอ"""
    s = str(s).strip().replace(" ", "")
    letters = "".join(re.findall(r"[A-Za-zก-ฮ]+'*", s))
    digits = "".join(re.findall(r"\d+'*", s))
    return (letters.upper(), digits) if letters and digits else (s.upper(), "")


def elements_of(doc):
    els = list(doc.get("elements") or [])
    for v in doc.get("views") or []:
        els += v.get("elements") or []
    return [e for e in els if isinstance(e, dict)]


def strict_key(e):
    return (str(e.get("element_id")), str(e.get("grid_ref_start")), str(e.get("grid_ref_end")))


def score_page(gold_els, pred_doc, page_label):
    n_gold = len(gold_els)
    if pred_doc is None:
        return {"page": page_label, "json_ok": False, "strict": (0, n_gold),
                "id_norm": (0, n_gold), "mark_base": (0, n_gold),
                "missed_ids": sorted({str(e.get("element_id")) for e in gold_els}),
                "extra_ids": [], "pos": None, "pos_mb": None}
    pred_els = elements_of(pred_doc)

    # 1. strict (t01)
    pred_keys = {strict_key(e) for e in pred_els}
    strict_found = sum(1 for g in gold_els if strict_key(g) in pred_keys)

    # 2. id_norm multiset
    gold_ids = Counter(norm_id(e.get("element_id")) for e in gold_els)
    pred_ids = Counter(norm_id(e.get("element_id")) for e in pred_els)
    id_found = sum(min(c, pred_ids[i]) for i, c in gold_ids.items())
    missed = sorted(i for i, c in gold_ids.items() if pred_ids[i] < c)
    extra = sorted(i for i, c in pred_ids.items() if c > gold_ids.get(i, 0))

    # 3b. mark_base — ให้อภัยธรรมเนียม "F4,C1" vs "F4"+"C1" แยก element
    gold_mb = Counter(mark_base(e.get("element_id")) for e in gold_els)
    pred_mb = Counter(mark_base(e.get("element_id")) for e in pred_els)
    mb_found = sum(min(c, pred_mb[i]) for i, c in gold_mb.items())

    # 3. position-level (ใช้ grid_refs เมื่อสองฝั่งมี)
    def instances(els, keyfn=norm_id):
        out = Counter()
        for e in els:
            i = keyfn(e.get("element_id"))
            refs = e.get("grid_refs")
            if isinstance(refs, list) and refs:
                for r in refs:
                    out[(i, norm_ref(r))] += 1
            elif e.get("grid_ref_start") is not None:
                out[(i, norm_ref(e.get("grid_ref_start")), norm_ref(e.get("grid_ref_end")))] += 1
        return out
    gi, pi = instances(gold_els), instances(pred_els)
    pos = (sum(min(c, pi[k]) for k, c in gi.items()), sum(gi.values())) if gi else None
    gi2, pi2 = instances(gold_els, mark_base), instances(pred_els, mark_base)
    pos_mb = (sum(min(c, pi2[k]) for k, c in gi2.items()), sum(gi2.values())) if gi2 else None

    return {"page": page_label, "json_ok": True, "strict": (strict_found, n_gold),
            "id_norm": (id_found, n_gold), "mark_base": (mb_found, n_gold),
            "missed_ids": missed, "extra_ids": extra, "pos": pos, "pos_mb": pos_mb}


def main():
    pages = [("page_26_plan_footing", "gt_footing.json"),
             ("page_27_plan_beam", "gt_beam.json")]
    rows, agg = [], Counter()
    for pred_name, gt_name in pages:
        gold = json.loads((OUT / gt_name).read_text(encoding="utf-8"))
        gold_els = elements_of(gold)
        pf = OUT / f"{pred_name}.json"
        pred = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else None
        r = score_page(gold_els, pred, pred_name)
        rows.append(r)
        for k in ("strict", "id_norm", "mark_base"):
            agg[k + "_f"] += r[k][0]
            agg[k + "_n"] += r[k][1]
        if r["pos"]:
            agg["pos_f"] += r["pos"][0]
            agg["pos_n"] += r["pos"][1]
        if r["pos_mb"]:
            agg["posmb_f"] += r["pos_mb"][0]
            agg["posmb_n"] += r["pos_mb"][1]

    print("=" * 72)
    for r in rows:
        print(f"\n▶ {r['page']}  (JSON {'OK' if r['json_ok'] else 'เสีย — gold นับเต็ม found=0'})")
        sf, sn = r["strict"]
        inf, inn = r["id_norm"]
        print(f"  strict (กติกา t01)     : {sf}/{sn}  = {sf/sn*100:.1f}%")
        print(f"  id_norm (รู้จัก mark)  : {inf}/{inn} = {inf/inn*100:.1f}%")
        mf, mn = r["mark_base"]
        print(f"  mark_base (ให้อภัย F4,C1): {mf}/{mn} = {mf/mn*100:.1f}%")
        if r["pos"]:
            pf_, pn = r["pos"]
            print(f"  position (ตำแหน่งถูก) : {pf_}/{pn} = {pf_/pn*100:.1f}%")
        if r["pos_mb"]:
            pf2, pn2 = r["pos_mb"]
            print(f"  position+mark_base    : {pf2}/{pn2} = {pf2/pn2*100:.1f}%")
        if r["missed_ids"]:
            print(f"  หายไป: {', '.join(r['missed_ids'])}")
        if r["extra_ids"]:
            print(f"  เกินมา: {', '.join(r['extra_ids'])}")
    print("\n" + "=" * 72)
    print("รวมทั้งสองหน้า:")
    print(f"  strict recall  = {agg['strict_f']}/{agg['strict_n']} = {agg['strict_f']/agg['strict_n']*100:.1f}%   (t01 เทียบ: 28.2%)")
    print(f"  id_norm recall = {agg['id_norm_f']}/{agg['id_norm_n']} = {agg['id_norm_f']/agg['id_norm_n']*100:.1f}%")
    print(f"  mark_base recall= {agg['mark_base_f']}/{agg['mark_base_n']} = {agg['mark_base_f']/agg['mark_base_n']*100:.1f}%  ← ให้อภัยธรรมเนียมบันทึก")
    if agg["pos_n"]:
        print(f"  position recall= {agg['pos_f']}/{agg['pos_n']} = {agg['pos_f']/agg['pos_n']*100:.1f}%")
    if agg["posmb_n"]:
        print(f"  position+mark_base = {agg['posmb_f']}/{agg['posmb_n']} = {agg['posmb_f']/agg['posmb_n']*100:.1f}%  ← ตัวเลขที่สะท้อนการอ่านจริงที่สุด")


if __name__ == "__main__":
    main()


def _self_check():
    gold = [{"element_id": "F4", "element_type": "footing", "count": 2, "grid_refs": ["A1", "A2"]},
            {"element_id": "C1", "element_type": "column", "count": 2, "grid_refs": ["A1", "A2"]}]
    pred = {"elements": [{"element_id": "F4", "grid_refs": ["1-A"]},
                         {"element_id": "c 1", "grid_refs": ["A-1", "A-2"]}]}
    r = score_page(gold, pred, "t")
    # strict = ตรงเป๊ะแบบ t01: "F4" จับคู่ได้ แต่ "c 1" ≠ "C1" (ห้าม normalize) → 1/2
    assert r["strict"] == (1, 2), r["strict"]
    assert r["id_norm"] == (2, 2), r["id_norm"]      # "c 1" → c1
    assert r["pos"] == (3, 4), r["pos"]              # F4@A2 หาย
    r3 = score_page(gold, {"elements": [{"element_id": "F4,C1", "grid_refs": ["A1", "A2"]}]}, "t")
    assert r3["mark_base"] == (1, 2), r3["mark_base"]   # "F4,C1"→f4 ตรง 1 (C1 ยังไม่มี)
    assert r3["pos_mb"] == (2, 4), r3["pos_mb"]         # 2 ตำแหน่งของ f4 ตรง
    assert norm_ref("1-A") == norm_ref("A1") == ("A", "1")
    r2 = score_page(gold, None, "t")
    assert r2["strict"] == (0, 2) and not r2["json_ok"]


_self_check()
