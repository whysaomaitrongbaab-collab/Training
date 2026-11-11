"""analyze_houses.py — สรุปด่าน 4 ของ t07: 83b8e52c เทียบเฉลย + บ้านเน็ต 3 หลัง + micro แล้วตัดสินตามตารางใน t07_workflow.md

⚠️ UNTESTED กับผลจริงของ t07 (ยังไม่มี) — ลองบน PC แล้วกับผลฐานของ proof/04 + proof/05 ที่ก็อปมาตั้งชื่อแบบ t07

สำเนาของ t05_Destrier/proof/05_temperature_บนการ์ด/scripts/analyze_houses.py (ห้ามแก้ต้นฉบับใน proof/) ต่างกัน:
  1. HOUSE regex ครอบทุกจำนวนชั้น `\\d+ชั้น` (เดิม `[12]ชั้น` มองไม่เห็น บ้าน_ใหญ่_3ชั้น_01..09 / บ้าน_ใหญ่_4ชั้น_01)
  2. อ่านผลจากโฟลเดอร์ที่ส่งเข้ามา: <ชุด>_house_r<N> · <ชุด>_<บ้านเน็ต>_r<N> · <ชุด>_micro (ชื่อที่ run_bench_t07.sh เขียน)
     + แถวฐาน 3 ต.ค. (proof/04 vLLM) ไว้ดูเทียบ
  3. รวม micro (เดิมอยู่ analyze_micro.py) + บรรทัดตัดสินตามเกณฑ์ผ่านของ t07
  4. import score_house จากโฟลเดอร์เดียวกับไฟล์นี้ (เดิม sys.path 'bench')
ชื่อบ้านนับใน result.json / outputs.json ทั้งไฟล์ (เหมือนต้นฉบับ) · ภาษาจีนนับจากช่อง cjk ของ calls.jsonl

    python analyze_houses.py <โฟลเดอร์ out ที่ดึงจากการ์ด> [ชุด ...]      (ค่าเริ่มต้น ชุด = t07)
"""
import glob
import json
import os
import re
import statistics as stt
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_house as S  # noqa: E402

HOUSE = re.compile(r"บ้าน_(?:เล็ก|ใหญ่)_\d+ชั้น_\d+")
P04 = r"d:/00mk/steel project/training/Training/tune_ai/t05_Destrier/proof/04_vllm_sglang_บนการ์ด/out"
P05_MICRO = r"d:/00mk/steel project/training/Training/tune_ai/t05_Destrier/proof/05_temperature_บนการ์ด/out/micro_T0.7"
WEB = ("dpt13226_1fl", "dpt13244_1fl", "dpt13250_2fl")
CAP = 9000                    # MAX_NEW_TOKENS ของ bench_house (= production)
RUNS = 3                      # 83b8e52c ×3 · บ้านเน็ต 3 หลัง ×3 (RUNBOOK_gate4.md)
# เกณฑ์ผ่าน t07 (t07_workflow.md) — ฐาน proof/04: recall 0.79 / precision 0.85 · plan_beam หน้า 20 ฐาน 22–56 (กว้าง 34)
NEED_RECALL, NEED_PRECISION, BEAM_MIN, BASE_BEAM_WIDTH = 0.79, 0.83, 45, 56 - 22
# เกณฑ์ 0.79 / 0.83 ตั้งจากตัวเลขฐานที่ score_house พิมพ์ปัด 2 ตำแหน่ง (ฐาน vLLM recall 41/52 = 0.788 → "0.79") —
# เทียบตรงตัวฐานเองจะตก จึงเทียบแบบปัด 2 ตำแหน่ง (= ไม่แย่กว่าฐาน) · ⚠️ การตีความนี้รอมะขามยืนยัน
HALF = 0.005


def runs(out, prefix, name):
    """[(ป้าย, path)] ของชุดนี้ เรียงตามรอบ"""
    ps = sorted(glob.glob(os.path.join(out, f"{prefix}_{name}_r*")),
                key=lambda p: int(re.search(r"_r(\d+)$", p).group(1)) if re.search(r"_r(\d+)$", p) else 0)
    return [(os.path.basename(p), p) for p in ps if os.path.exists(f"{p}/summary.json")]


def stats(p):
    s = json.load(open(f"{p}/summary.json", encoding="utf-8"))
    calls = [json.loads(line) for line in open(f"{p}/calls.jsonl", encoding="utf-8") if line.strip()]
    raw = open(f"{p}/result.json", encoding="utf-8").read()
    cap = [c["kind"] for c in calls if (c.get("completion_tokens") or 0) >= CAP]
    g = [c for c in calls if c["kind"] == "gridline"]
    g_cap = sum((c.get("completion_tokens") or 0) >= CAP for c in g)
    gl = "วน" if g_cap else ("ผ่าน" if g and g[0]["json_ok"] else "ไม่มี/พัง")
    return (s["wall_s"], s["all"]["json_ok"], s["all"]["n"], cap, gl, g_cap,
            sum(c.get("cjk", 0) for c in calls), len(HOUSE.findall(raw)))


def house_rows(tm, label, p):
    mm, mc, ok, total = S.model(f"{p}/result.json")
    hit = sum(len(tm[x] & mm[x]) for x in S.PAGES)
    want = sum(len(tm[x]) for x in S.PAGES)
    got = sum(len(mm[x]) for x in S.PAGES)
    w, jo, n, cap, gl, g_cap, cjk, hn = stats(p)
    rec, pre = hit / want, (hit / got if got else 0.0)
    print(f"  {label:<24} {w:6.0f}s JSON {jo}/{n} มาร์ค {hit}/{want} recall {rec:.2f} precision {pre:.2f} "
          f"ชนเพดาน {len(cap)} gridline {gl} จีน {cjk} ชื่อบ้านเทรน {hn}")
    return rec, pre, cjk, hn


def micro(tm, tc, label, d):
    """plan_beam หน้า 20 ต่อรอบ + จีน + ชื่อบ้าน (เดิม analyze_micro.py)"""
    outs = json.load(open(f"{d}/outputs.json", encoding="utf-8"))
    calls = [json.loads(line) for line in open(f"{d}/calls.jsonl", encoding="utf-8") if line.strip()]
    print(f"  {label}")
    beam = []
    for kind, pg in (("section", 22), ("plan_beam", 20), ("plan_footing", 19)):
        rs = [o for o in outs if o["kind"] == kind and o["page"] == pg]
        cnt, hit = [], []
        for o in rs:
            els = [e for e in ((o["json"] or {}).get("elements") or []) if isinstance(e, dict)]
            ms = {S.norm(S.mark_of(e)) for e in els if S.mark_of(e)}
            cnt.append(len(els))
            hit.append(len(tm[pg] & ms))
        beam = cnt if kind == "plan_beam" else beam
        print(f"     {kind:<13} หน้า {pg} ชิ้นต่อรอบ {cnt} (เฉลย {tc[pg]}) · มาร์คตรง {hit}/{len(tm[pg])}")
    cjk = sum(c.get("cjk", 0) for c in calls)
    hn = len(HOUSE.findall(open(f"{d}/outputs.json", encoding="utf-8").read()))
    print(f"     จีน {cjk} · ชื่อบ้านเทรน {hn} · ชนเพดาน {sum((c.get('completion_tokens') or 0) >= CAP for c in calls)}")
    return beam, cjk, hn


def mark(ok):
    return "✅" if ok else "⛔"


def verdict(prefix, h, web, mic):
    print(f"\n== ตัดสิน {prefix} (เกณฑ์ t07_workflow.md · ฐาน = Destrier ตัวซ่อมบน vLLM proof/04)")
    if h:
        rec, pre = [x[0] for x in h], [x[1] for x in h]
        for stat, f in (("mean", stt.mean), ("min", min)):
            r, p = f(rec), f(pre)
            print(f"  83b8e52c recall/precision ({stat} {len(h)} รอบ) {r:.3f} / {p:.3f} → "
                  f"{mark(r >= NEED_RECALL - HALF and p >= NEED_PRECISION - HALF and len(h) >= RUNS)}"
                  f" (ต้อง ≥ {NEED_RECALL} / ≥ {NEED_PRECISION} ปัด 2 ตำแหน่ง · ครบ {RUNS} รอบ)")
        print("     ⚠️ ใช้ mean หรือ min ยังไม่ได้ตัดสิน — ต้องเลือกก่อนเปิดดูผล (RUNBOOK_gate4.md)")
    else:
        print("  83b8e52c: ไม่มีผล ⛔")
    gcap = sum(x[5] for x in web)
    print(f"  บ้านเน็ต gridline ชนเพดาน {CAP} token: {gcap} ครั้งใน {len(web)} รอบ → "
          f"{mark(gcap == 0 and len(web) >= len(WEB) * RUNS)} (ต้อง 0 · ครบ {len(WEB)} หลัง × {RUNS} รอบ)")
    hn = sum(x[3] for x in h) + sum(x[7] for x in web) + (mic[2] if mic else 0)
    cjk = sum(x[2] for x in h) + sum(x[6] for x in web) + (mic[1] if mic else 0)
    print(f"  ชื่อบ้านเทรนในผลอ่านทั้งหมด: {hn} → {mark(hn == 0)} (ต้อง 0)")
    print(f"  ตัวอักษรจีน (cjk): {cjk} → {mark(cjk == 0)} (ต้อง 0)")
    if mic and mic[0]:
        b = mic[0]
        okb = min(b) >= BEAM_MIN and (max(b) - min(b)) < BASE_BEAM_WIDTH
        print(f"  plan_beam หน้า 20 ×{len(b)}: {b} ต่ำสุด {min(b)} ช่วง {max(b) - min(b)} → {mark(okb)}"
              f" (ต้อง ต่ำสุด ≥ {BEAM_MIN} และช่วงแคบกว่าฐาน {BASE_BEAM_WIDTH})")
    else:
        print("  micro: ไม่มีผล ⛔")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out, prefixes = sys.argv[1], sys.argv[2:] or ["t07"]
    tm, tc = S.truth()
    print("== ฐาน 3 ต.ค. (proof/04 vLLM · Destrier ตัวซ่อม · n=1)")
    if os.path.exists(f"{P04}/vllm_house/summary.json"):
        house_rows(tm, "83b8e52c", f"{P04}/vllm_house")
    for w in WEB:
        if os.path.exists(f"{P04}/vllm_{w}/summary.json"):
            x = stats(f"{P04}/vllm_{w}")
            print(f"  {w:<24} {x[0]:6.0f}s JSON {x[1]}/{x[2]} ชนเพดาน {len(x[3])} {x[3]} gridline {x[4]} "
                  f"จีน {x[6]} ชื่อบ้านเทรน {x[7]}")
    if os.path.exists(f"{P05_MICRO}/outputs.json"):
        micro(tm, tc, "micro ฐาน (proof/05 T 0.7 × 4 รอบ)", P05_MICRO)
    for prefix in prefixes:
        print(f"\n== {prefix}: 83b8e52c (มีเฉลย)")
        h = [house_rows(tm, lab, p) for lab, p in runs(out, prefix, "house")]
        web = []
        for w in WEB:
            print(f"== {prefix}: {w}")
            for lab, p in runs(out, prefix, w):
                x = stats(p)
                web.append(x)
                print(f"  {lab:<24} {x[0]:6.0f}s JSON {x[1]}/{x[2]} ชนเพดาน {len(x[3])} {x[3]} gridline {x[4]} "
                      f"จีน {x[6]} ชื่อบ้านเทรน {x[7]}")
        d = os.path.join(out, f"{prefix}_micro")
        mic = micro(tm, tc, f"{prefix}_micro", d) if os.path.exists(f"{d}/outputs.json") else None
        verdict(prefix, h, web, mic)


if __name__ == "__main__":
    main()
