#!/usr/bin/env python3
"""vector_ruler.py — ไม้บรรทัดจาก "เส้นกริดเวกเตอร์" ของ PDF (ไม่ใช้ CV ไม่ใช้หมุดจากโมเดล) · pure stdlib

    เว็บ (pdf.js) สกัด vector sidecar รายหน้า → worker โหลดคู่กับ PNG (กรอบพิกัด = พิกเซลของ PNG)
    เส้นกริดใน PDF ที่ export จาก CAD = เส้นประยาว (dash-dot ถูกระเบิดเป็นท่อนๆ 10-70 ท่อน) ตัดกันเป็นตาราง
    grid master (pass2 gridline) ให้ pos_m ของทุกเส้น
    ───────────────────────────────────────────────────────────────────────────
    ไฟล์นี้: ตำแหน่งเส้นกริดที่วาดจริง ↔ pos_m ของ grid master → px ต่อเมตร (scale เดียวทั้งสองแกน)
             + ด่าน: มาตราส่วนมาตรฐาน · อธิบายเส้นได้ครบ · สลับแกนต้องแย่กว่า
             + ตรวจ grid master: ทิศ origin (origin_not_top_left) · แกนที่ระยะผิดเป็นเท่า (scale_suspect)

วัดแล้ว (vr_build/eval_all.py บน 98 หน้า vector ของชุด GT + 3 bundle จาก pdf.js — ดูตัวเลขใน
integration.md): ไม่พึ่งหมุดจากโมเดลเลย จึงวัดหน้าคานล้วนได้ ต่างจาก pass3_measure.py ที่ 0/9 หน้า production

กติกาที่วัดมาแล้ว ห้ามเชื่อโน้ตมาตราส่วนที่พิมพ์ในแบบ: บ้าน 01 พิมพ์ 1:100 แต่ PDF เป็น 1:141.4 (ชุด A3
พิมพ์ลง A4) → snap กับ {2834.6457/R × 1, × 1/√2} เท่านั้น · และ snap จับ grid master ที่แกนหนึ่งยาวเป็น
2 เท่าไม่ได้ (1:100 หาร 2 = 1:200 ก็มาตรฐาน) → ต้องมีด่าน "ครบ" รายแกน

รายงานอย่างเดียว: ไม่แก้ grid master / doc ของ pass2 / สิ่งที่ส่งให้โมเดล — ผลอยู่ใน report ที่คืน

self-check: python test_vector_ruler.py
"""
import bisect
import json
import math

VERSION = 1

# ── เกณฑ์ (ตัวเลขเดียว เปลี่ยนที่นี่ที่เดียว · ที่มาของแต่ละค่าอยู่ใน vr_build/ ของงานวิจัย) ─────────
MIN_PIECES = 10          # ลายเส้นประ: run ของเส้น named ≥10 ท่อน 440/487 (vr_build/explore1.py) · ผนัง/ขอบ 1-3 ท่อน
MIN_SPAN_FRAC = 0.05     # ยาวอย่างน้อย 5% ของด้านยาวหน้ากระดาษ (ตัดเส้นประสั้นๆ ของ hatch/สัญลักษณ์)
COVER_MIN = 0.6          # เส้นกริดต้องพาดผ่านเส้นแกนตั้งฉากในตารางเดียวกันอย่างน้อยเท่านี้ (สัดส่วน)
MERGE_PX = 1.0           # สองท่อนที่ตำแหน่งตั้งฉากห่างกัน ≤ นี้ = เส้นเดียวกัน (เส้นที่ถูกวงกลม/ตัวหนังสือตัด)
CROSS_TOL_PT = 5.0       # เส้นตั้ง/นอน "ตัดกัน" ถ้าปลายเลยกันไม่เกินนี้ (pt บนกระดาษ)
TOL_M = 0.05             # เส้นที่วาด ต้องตกห่างเส้นใน grid master ไม่เกิน 5 ซม. (GT ปัด pos_m 0.05)
SNAP_TOL = 0.01          # px/m ต้องห่างมาตราส่วนมาตรฐานไม่เกิน 1%
MIN_LINES = 5            # เส้นที่อธิบายได้รวมสองแกนขั้นต่ำ (2+2 ยังบังเอิญได้)
# ด่าน "ครบ" รายแกน (สองทาง — ที่มาของตัวเลขใน integration.md):
#   (ก) เส้น named ทุกเส้นใน grid master ต้องมีเส้นที่วาดรองรับ (k = 0) — master ที่ยาว/สั้นเป็นเท่าจะมีเส้นตกนอกแบบ
#       หรือตกช่องว่างเสมอ จึงผ่านไม่ได้ทั้งที่ snap มาตรฐานผ่าน (1:100 ÷ 2 = 1:200)
#   (ข) เส้นประที่วาด "ในช่วงกริด" ที่อธิบายไม่ได้ ≤ MAX_INSIDE_UNEXPLAINED ต่อแกน (0 ถ้า master แกนนั้นมี 2 เส้น)
#       อธิบายได้ = ตรงเส้น named/dummy หรือเป็นเงาห่างเส้นที่จับคู่ได้ ≤ SHADOW_M (ขอบคานเส้นประ ±0.1 ม.) ·
#       เส้นนอกช่วงกริดที่สั้นกว่าทุกเส้นที่จับคู่ได้ (กรอบเขตที่ดินเส้นประ ~3 ม. นอกกริด เจอใน template เดียวกัน
#       หลายหลัง) ไม่นับ แต่รายงานเป็น unmatched
#   วัด 5 แบบบน 98 หน้า GT (integration.md): (ก)+(ข)k=1 ผ่าน 68 หน้า ยอมรับ master ที่เพี้ยนผิด 0 ครั้ง ·
#   (ก)+(ข)k=0 60 หน้า 0 ครั้ง · ครบฝั่งเส้นที่วาดอย่างเดียว k=1 (ข้อเสนอเดิม) 35 หน้า แต่ยอมรับ master ยาว 2 เท่า
#   21 ครั้ง · ไม่มีด่านเลย 86 หน้า ยอมรับผิด 88 ครั้ง
SHADOW_M = 0.4
MAX_INSIDE_UNEXPLAINED = 1
PT_PER_M_RANGE = (5.0, 150.0)   # 1:19 .. 1:567 — นอกช่วงนี้ไม่ใช่แปลนอาคาร
STD_R = (20, 25, 30, 40, 50, 60, 75, 80, 100, 125, 150, 200, 250, 300, 400, 500)
PT_PER_M_FULL = 2834.6457       # 1:1 → pt ต่อเมตร (72 / 0.0254)
STD_PT_PER_M = sorted((PT_PER_M_FULL / r * k, r) for r in STD_R for k in (1.0, 1 / math.sqrt(2)))
# ตัวคูณที่ลองกับแกนที่ "ไม่ครบ": 2 / ½ = อ่านโซ่มิติซ้ำ/อ่านครึ่ง (เจอจริง 83b8e52c: อ่าน 3.00+3.00 เป็น
# 0/6/12) · 3/2 / 2/3 = อัตราส่วนเต็มเล็กถัดไป (ไม่เคยเจอจริง ใส่ตามข้อกำหนด) · วัดแล้ว (vr_build/factor_study.py):
# บน grid master สะอาด 105 ตาราง ไม่มี scale_suspect ปลอมเลยทั้งชุดนี้และชุดที่เติม 3, ⅓ — ไม่ใส่ 3, ⅓ เพราะยังไม่มี
# ความผิดแบบนั้นให้เห็น และ master จริงจากโมเดลรกกว่า GT (ตัวคูณยิ่งมาก ยิ่งมีโอกาสครบโดยบังเอิญ)
FACTORS = (2.0, 0.5, 1.5, 2.0 / 3.0)
# มาตราส่วน (ตามชื่อ ไม่นับการย่อ A3→A4) ของแปลนที่ผ่านด่านในชุด GT: 1:100 54 ตาราง · 1:50 13 · 1:75 5 — ใช้ตัดสิน
# ชื่อแกนของ scale_suspect เท่านั้น (ดู _suspects) ไม่ใช้ตัดสินว่าจะยอมรับ scale ไหน
COMMON_PLAN_R = (50, 75, 100)
# เพดานเวลา: สมมติฐานโต ~n² ต่อแกน · แปลนจริงในชุด GT มีเส้นผู้สมัครต่อแกนสูงสุด 31 (หลังคามีแป) · หน้าที่ไม่ใช่แปลน
# ใน bundle pdf.js 290 หน้า สูงสุด 48 เส้น = 469 ms (vr_build/worstcase.py) → เกิน 60 = ไม่ใช่ผังกริดบ้าน ไม่วัด
MAX_LINES_PER_AXIS = 60
_LOG_BIN = 0.005         # ถังของ log(px/m) ตอนรวมสมมติฐานสองแกน (0.5%)
_TOP_K = 6               # จำนวนถัง scale ที่ fit ละเอียด

REASON_TH = {
    "malformed_sidecar": "vector sidecar ของหน้านี้รูปแบบเสีย — ข้าม ไม่วัด",
    "no_grid_master": "grid master มีเส้นที่รู้ pos_m ไม่ถึงแกนละ 2 เส้น — ไม่มีไม้บรรทัด",
    "no_vector_grid": "ไม่พบตารางเส้นกริดเวกเตอร์ในหน้านี้ (หน้าเป็นภาพสแกน หรือเส้นกริดไม่ใช่เส้นประ) — ไม่วัด",
    "no_fit": "เส้นกริดที่วาดจับคู่กับ grid master ไม่ได้เลย",
    "too_many_lines": f"ตารางนี้มีเส้นประยาวเกิน {MAX_LINES_PER_AXIS} เส้นต่อแกน — ไม่ใช่ผังกริด ไม่วัด",
    "too_few_lines": f"เส้นกริดที่อธิบายได้น้อยเกินไป (ต้อง ≥{MIN_LINES} เส้นรวม และแกนละ ≥2) — ไม่ใช้ผล",
    "off_standard_scale": "มาตราส่วนที่ได้ไม่ใช่มาตราส่วนมาตรฐาน (ห่างเกิน 1%) — น่าจะจับคู่ผิด ไม่ใช้ผล",
    "incomplete": "เส้นกริดที่วาดกับ grid master ไม่ครบกัน (เส้นใน master ไม่มีในแบบ หรือมีเส้นกริดในแบบที่ master "
                  "ไม่มี) — ไม่ใช้ผล",
    "transpose_ambiguous": "สลับแกน x/y แล้วอธิบายเส้นได้เท่ากันหรือดีกว่า — ไม่รู้ว่าแกนไหนเป็นแกนไหน ไม่ใช้ผล",
    "scale_ambiguous": "ทิศแกนต่างกันให้มาตราส่วนต่างกัน — ไม่ใช้ผล",
    "scale_suspect": "grid master น่าจะอ่านระยะผิดเป็นเท่า (ดู issues) — ไม่ใช้ผลวัดของตารางนี้",
}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


class _Bad(Exception):
    pass


# ── 1. sidecar → เส้นผู้สมัคร (พิกเซลของ PNG) ────────────────────────────────────────────
def _decode(page):
    if not isinstance(page, dict) or not isinstance(page.get("frame"), dict):
        raise _Bad("ไม่มี frame")
    fr = page["frame"]
    q, rs, w, h = (fr.get(k) for k in ("units_per_px", "render_scale", "png_w", "png_h"))
    if not all(_num(v) and v > 0 for v in (q, rs, w, h)):
        raise _Bad("frame ขาด units_per_px/render_scale/png_w/png_h")
    out = {}
    for key in ("vlines", "hlines"):
        rows = page.get(key)
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise _Bad(f"{key} ไม่ใช่ list")
        good = []
        for r in rows:
            if isinstance(r, (list, tuple)) and len(r) >= 4 and all(_num(v) for v in r[:4]):
                a0, a1 = sorted((r[1] / q, r[2] / q))
                good.append((r[0] / q, a0, a1, r[3]))
        out[key] = good
    return rs, max(w, h), out["vlines"], out["hlines"]


def _collapse(rows):
    """ท่อนที่ตำแหน่งตั้งฉากเดียวกัน (≤ MERGE_PX) รวมเป็นเส้นเดียว → [(pos, a0, a1)]"""
    out = []
    for perp, a0, a1, _ in sorted(rows):
        if out and perp - out[-1][0] <= MERGE_PX:
            p, b0, b1 = out[-1]
            out[-1] = (p, min(a0, b0), max(a1, b1))
        else:
            out.append((perp, a0, a1))
    return out


def _cover(line, others, tol):
    return sum(1 for o in others if line[1] - tol <= o[0] <= line[2] + tol) / len(others)


def _views(vrows, hrows, tol):
    """ตาราง = กลุ่มเส้นตั้ง+นอนที่ตัดกันต่อเนื่อง (หนึ่งแผ่นมีได้หลายแปลน) → [(xs, ys, bbox)]"""
    nodes = [("v", r) for r in vrows] + [("h", r) for r in hrows]
    parent = list(range(len(nodes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    nv = len(vrows)
    for i, v in enumerate(vrows):
        for j, hh in enumerate(hrows):
            if hh[1] - tol <= v[0] <= hh[2] + tol and v[1] - tol <= hh[0] <= v[2] + tol:
                parent[find(i)] = find(nv + j)
    comps = {}
    for i, (ax, r) in enumerate(nodes):
        comps.setdefault(find(i), {"v": [], "h": []})[ax].append(r)
    out = []
    for c in comps.values():
        xs, ys = _collapse(c["v"]), _collapse(c["h"])
        for _ in range(3):   # เส้นกริดต้องพาดผ่านเส้นตั้งฉากส่วนใหญ่ของตาราง (เส้นประคาน/ช่วงสั้นไม่ผ่าน)
            if len(xs) < 2 or len(ys) < 2:
                break
            nx = [l for l in xs if _cover(l, ys, tol) >= COVER_MIN]
            ny = [l for l in ys if _cover(l, xs, tol) >= COVER_MIN]
            if (nx, ny) == (xs, ys):
                break
            xs, ys = nx, ny
        if len(xs) >= 2 and len(ys) >= 2:
            bbox = [min(l[0] for l in xs), min(l[0] for l in ys), max(l[0] for l in xs), max(l[0] for l in ys)]
            out.append(([l[0] for l in xs], [l[0] for l in ys], bbox,
                        [l[2] - l[1] for l in xs], [l[2] - l[1] for l in ys]))
    out.sort(key=lambda v: (v[2][0], v[2][1]))
    return out


# ── 2. grid master → เส้นอ้างอิง ────────────────────────────────────────────────────────
def _master(grid, axis):
    """([(pos_m, id)] เส้นที่ใช้ fit, [pos_m ของเส้นที่เหลือ]) · fit ด้วยเส้น named เมื่อมี ≥2 (dummy มักไม่ได้
    วาด แต่ถ้าวาดก็ถือว่าอธิบายได้) · ตำแหน่งใกล้กันกว่า 2×TOL รวมเป็นเส้นเดียว (จับคู่หนึ่งต่อหนึ่งต้องไม่กำกวม)"""
    lines = grid.get("x_lines" if axis == "x" else "y_lines") if isinstance(grid, dict) else None
    ok = [ln for ln in lines if isinstance(ln, dict) and _num(ln.get("pos_m"))] if isinstance(lines, list) else []
    named = [ln for ln in ok if ln.get("type") != "dummy"]
    use = named if len(named) >= 2 else ok
    fit = []
    for ln in sorted(use, key=lambda ln: ln["pos_m"]):
        lid = ln.get("id")
        lid = str(lid) if isinstance(lid, (str, int)) and not isinstance(lid, bool) else None
        if fit and ln["pos_m"] - fit[-1][0] <= 2 * TOL_M:
            continue
        fit.append((float(ln["pos_m"]), lid))
    rest = sorted(float(ln["pos_m"]) for ln in ok if ln not in use)
    return fit, rest


# ── 3. fit: px = s·u + b ต่อแกน โดย u = σ·pos_m (s ร่วมกันสองแกน, σ = ทิศ ±1) ────────────
def _match(P, U, s, b):
    """หนึ่งต่อหนึ่ง: {k ใน U: (i ใน P, คลาดเมตร)} — U เรียงน้อยไปมาก"""
    best = {}
    for i, p in enumerate(P):
        u = (p - b) / s
        k = bisect.bisect_left(U, u)
        for kk in (k - 1, k):
            if 0 <= kk < len(U):
                e = abs(U[kk] - u)
                if e <= TOL_M and (kk not in best or e < best[kk][1]):
                    best[kk] = (i, e)
    return best


def _explain(P, SP, U, D, s, b):
    """ครบแค่ไหน ที่ตัวแปลง (s, b): master_un = เส้น named ที่ไม่มีเส้นวาดรองรับ · inside = เส้นที่วาดในช่วงกริด
    ที่อธิบายไม่ได้ + เส้นนอกช่วงที่ยาวเท่าเส้นที่จับคู่ได้ (สมมติฐานผิดทิศชอบดันเส้นกริดจริงออกนอกช่วงแล้วใช้
    กรอบเส้นประแทน — บ้าน 01 หน้า 19) · outside = เส้นสั้นกว่าทุกเส้นที่จับคู่ได้ นอกช่วงกริด (รายงานอย่างเดียว)
    SP = ความยาวของแต่ละเส้นใน P · D = dummy (σ·pos เรียงแล้ว)"""
    mt = _match(P, U, s, b)
    got = sorted(P[i] for i, _ in mt.values())
    inside = outside = 0
    if got:
        used = {i for i, _ in mt.values()}
        shortest = min(SP[i] for i in used)
        for i, p in enumerate(P):
            if i in used:
                continue
            u = (p - b) / s
            k = bisect.bisect_left(D, u)
            if any(0 <= kk < len(D) and abs(D[kk] - u) <= TOL_M for kk in (k - 1, k)):
                continue
            j = bisect.bisect_left(got, p)
            if any(0 <= jj < len(got) and abs(got[jj] - p) <= SHADOW_M * s for jj in (j - 1, j)):
                continue
            if got[0] - TOL_M * s <= p <= got[-1] + TOL_M * s or SP[i] >= shortest:
                inside += 1
            else:
                outside += 1
    return {"mt": mt, "master_un": len(U) - len(mt), "inside": inside, "outside": outside,
            "unmatched": len(P) - len(mt), "n_master": len(U)}


def _complete(ex):
    # แกนที่ master มีแค่ 2 เส้น: "เส้น named ทุกเส้นมีในแบบ" แทบไม่พิสูจน์อะไร (สองเส้นตกเส้นประอะไรก็ได้ที่ห่างพอดี —
    # เจอจริง: master x ของ บ้าน_เล็ก_2ชั้น_08 คูณ ⅓ ยังผ่าน) → ไม่ยอมเส้นที่อธิบายไม่ได้เลย
    k = MAX_INSIDE_UNEXPLAINED if ex["n_master"] >= 3 else 0
    return ex["master_un"] == 0 and ex["inside"] <= k


def _axis_fit(P, U, s):
    """offset ที่จับคู่ได้มากสุดของแกนเดียวที่ scale คงที่ → (n, b)"""
    best, tried = (0, 0.0, 0.0, None), set()
    cell = s * TOL_M
    for p in P:
        for u in U:
            b = p - s * u
            key = round(b / cell)
            if key in tried:
                continue
            tried.add(key)
            mt = _match(P, U, s, b)
            sse = sum(e * e for _, e in mt.values())
            if (len(mt), -sse) > (best[0], -best[1]):
                best = (len(mt), sse, b, mt)
    n, _, b, mt = best
    if n:
        b = sum(P[i] - s * U[k] for k, (i, _) in mt.items()) / n
    return len(_match(P, U, s, b)), b


def _hyps(P, U, lo, hi):
    """สมมติฐานจากคู่เส้น (วาด) × คู่เส้น (master) → [(s, b, n)]"""
    out = []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            dp = P[j] - P[i]
            for a in range(len(U)):
                for c in range(a + 1, len(U)):
                    s = dp / (U[c] - U[a])
                    if lo <= s <= hi:
                        b = P[i] - s * U[a]
                        out.append((s, b, len(_match(P, U, s, b))))
    return out


def _lsq(pairs_by_axis):
    """least squares ร่วม: s เดียว offset แยกแกน · pairs_by_axis = [[(u, p)], ...] → (s, [b...]) หรือ None"""
    num = den = 0.0
    means = []
    for prs in pairs_by_axis:
        mu = sum(u for u, _ in prs) / len(prs)
        mp = sum(p for _, p in prs) / len(prs)
        num += sum((u - mu) * (p - mp) for u, p in prs)
        den += sum((u - mu) ** 2 for u, _ in prs)
        means.append((mu, mp))
    if den <= 0 or num <= 0:
        return None
    s = num / den
    return s, [mp - s * mu for mu, mp in means]


def _refine(P, Q, U, V, s, bx, by):
    for _ in range(2):
        mx, my = _match(P, U, s, bx), _match(Q, V, s, by)
        if len(mx) < 2 or len(my) < 2:
            break
        r = _lsq([[(U[k], P[i]) for k, (i, _) in mx.items()], [(V[k], Q[i]) for k, (i, _) in my.items()]])
        if r is None:
            break
        s, (bx, by) = r
    return s, bx, by


def _joint_fit(P, Q, SP, SQ, U, V, DU, DV, lo, hi):
    """scale เดียวที่จับคู่เส้นได้มากที่สุดรวมสองแกน → dict (s, bx, by, ex, ey, res) หรือ None"""
    if len(P) < 2 or len(Q) < 2 or len(U) < 2 or len(V) < 2:
        return None
    bins = [{}, {}]
    for side, (A, W) in enumerate(((P, U), (Q, V))):
        for s, b, n in _hyps(A, W, lo, hi):
            k = round(math.log(s) / _LOG_BIN)
            if n > bins[side].get(k, (0,))[0]:
                bins[side][k] = (n, s)

    def near(side, k):
        return max((bins[side][j] for j in (k - 1, k, k + 1) if j in bins[side]), default=(0, None))

    cand = []
    for k in set(bins[0]) | set(bins[1]):
        a, c = near(0, k), near(1, k)
        if a[0] >= 2 and c[0] >= 2:
            cand.append((a[0] + c[0], k, a[1], c[1]))
    cand.sort(reverse=True)
    best, seen = None, set()
    for _, _, s1, s2 in cand[:_TOP_K]:
        for s0 in (s1, s2):
            key0 = round(math.log(s0) / _LOG_BIN * 4)
            if key0 in seen:
                continue
            seen.add(key0)
            nx, bx = _axis_fit(P, U, s0)
            ny, by = _axis_fit(Q, V, s0)
            if nx < 2 or ny < 2:
                continue
            s, bx, by = _refine(P, Q, U, V, s0, bx, by)
            ex, ey = _explain(P, SP, U, DU, s, bx), _explain(Q, SQ, V, DV, s, by)
            errs = [e for _, e in ex["mt"].values()] + [e for _, e in ey["mt"].values()]
            key = (len(ex["mt"]) + len(ey["mt"]), -sum(e * e for e in errs))
            if best is None or key > best["key"]:
                best = {"key": key, "s": s, "bx": bx, "by": by, "ex": ex, "ey": ey,
                        "res": max(errs) if errs else 0.0}
    return best


def _snap(pt_per_m):
    v, r = min(STD_PT_PER_M, key=lambda t: abs(t[0] - pt_per_m) / t[0])
    return v, r, abs(v - pt_per_m) / v


def _gate(f, rs):
    if f is None:
        return "no_fit"
    nx, ny = len(f["ex"]["mt"]), len(f["ey"]["mt"])
    if nx < 2 or ny < 2 or nx + ny < MIN_LINES:
        return "too_few_lines"
    if _snap(f["s"] / rs)[2] > SNAP_TOL:
        return "off_standard_scale"
    if not (_complete(f["ex"]) and _complete(f["ey"])):
        return "incomplete"
    return None


SIGNS = ((1, 1), (-1, 1), (1, -1), (-1, -1))


def _signed(pos, sign):
    return sorted(sign * m for m in pos)


def _ids(M, sign, mt):
    """ดัชนีใน U (= σ·pos เรียง) → id ของเส้นใน master (เรียงตาม pos_m)"""
    order = sorted(range(len(M)), key=lambda i: sign * M[i][0])
    return [M[j][1] for j in sorted(order[k] for k in mt)]


# ── 4. ตรวจแกนที่ระยะผิดเป็นเท่า ─────────────────────────────────────────────────────────
def _complete_scales(P, SP, U, D, lo, hi):
    """scale ที่แกนเดียวนี้ครบ (named ทุกเส้นมีเส้นวาด + ไม่มีเส้นในช่วงที่อธิบายไม่ได้) หลัง least squares"""
    seen, out = set(), []
    for s, b, n in _hyps(P, U, lo, hi):
        k = round(math.log(s) / _LOG_BIN)
        if n < len(U) or k in seen:
            continue
        seen.add(k)
        mt = _match(P, U, s, b)
        r = _lsq([[(U[kk], P[i]) for kk, (i, _) in mt.items()]])
        if r and _complete(_explain(P, SP, U, D, r[0], r[1][0])):
            out.append(r[0])
    out.sort()
    ded = []
    for s in out:
        if not ded or s / ded[-1] - 1 > 2 * _LOG_BIN:
            ded.append(s)
    return ded


def _suspects(P, Q, SP, SQ, MX, MY, rs, lo, hi):
    """แกน A ครบที่ scale มาตรฐาน s · อีกแกน B ไม่ครบที่ s แต่ครบเมื่อคูณ pos_m ด้วย f ตัวเดียวพอดี
    → {"axis": B หรือ None, "ratio": 1/f (= master ใหญ่กว่าของจริงกี่เท่า), "px_per_m", "candidates"}
    ทั้งสองแกนต้องมีเส้น named ≥3 (2 เส้นเข้ากับ f ไหนก็ได้โดยบังเอิญ)

    ⚠️ เรขาคณิตอย่างเดียวแยก "x ยาวไป 2 เท่า ที่ 1:100" กับ "y สั้นไปครึ่งหนึ่ง ที่ 1:200" ไม่ออกเลย (ย่อ/ขยาย
    ทั้งแผ่นพร้อมกันได้ภาพเดียวกันเป๊ะ) → บอกชื่อแกนเฉพาะเมื่อคำตอบเดียวตกมาตราส่วนแปลนที่พบจริง
    (COMMON_PLAN_R) ไม่งั้น axis = None = เว็บติดธงช่วงคานทั้งสองแกน (ปลอดภัยกว่าชี้ผิดแกน ซึ่งติดธงแกนที่ถูก
    แล้วปล่อยแกนที่ผิด) · วัดแล้ว: prior "ใกล้ 1:100 ที่สุด" จะชี้ผิดแกน 13/67 ครั้ง ทุกครั้งเป็นแบบ 1:50 จริง"""
    got = []
    (UX, DX), (UY, DY) = MX, MY
    for ref, A, SA, UA, DA, B, SB, UB, DB in (("y", Q, SQ, UY, DY, P, SP, UX, DX), ("x", P, SP, UX, DX, Q, SQ, UY, DY)):
        pa, pb = [m for m, _ in UA], [m for m, _ in UB]
        if len(pa) < 3 or len(pb) < 3 or len(A) < 3 or len(B) < 3:
            continue
        for sa in (1, -1):   # ทิศแกนไม่ผูก: grid master ที่นับจากล่างขึ้นบนก็ยังตรวจได้ (บ้าน 1ชั้น_05)
            for s in _complete_scales(A, SA, _signed(pa, sa), _signed(DA, sa), lo, hi):
                _, r, err = _snap(s / rs)
                if err > SNAP_TOL:
                    continue

                def ok_b(f, sb):
                    Uf, Df = [u * f for u in _signed(pb, sb)], [d * f for d in _signed(DB, sb)]
                    return _complete(_explain(B, SB, Uf, Df, s, _axis_fit(B, Uf, s)[1]))

                if ok_b(1.0, 1) or ok_b(1.0, -1):
                    continue
                fs = [f for f in FACTORS if ok_b(f, 1) or ok_b(f, -1)]
                if len(fs) == 1:
                    g = {"axis": "x" if ref == "y" else "y", "ratio": round(1.0 / fs[0], 3),
                         "px_per_m": round(s, 4), "scale_nominal_R": r}
                    if not any(o["axis"] == g["axis"] and o["ratio"] == g["ratio"] for o in got):
                        got.append(g)
    if not got:
        return None
    common = [g for g in got if g["scale_nominal_R"] in COMMON_PLAN_R]
    axes = {g["axis"] for g in got}
    pick = got[0] if len(axes) == 1 else common[0] if len({g["axis"] for g in common}) == 1 else None
    if pick:
        return dict(pick, candidates=got)
    big = max(got, key=lambda g: max(g["ratio"], 1 / g["ratio"]))
    return {"axis": None, "ratio": round(max(big["ratio"], 1 / big["ratio"]), 3), "px_per_m": None,
            "candidates": got}


def _ratio_th(ratio):
    w = {2.0: "ครึ่งหนึ่ง", 0.5: "สองเท่า", 1.5: "2/3", 0.667: "1.5 เท่า"}.get(round(ratio, 3))
    return f"ระยะในแบบเป็น{w}ของที่อ่านได้" if w else f"ระยะในแบบเป็น {1 / ratio:.2f} เท่าของที่อ่านได้"


# ── 5. ตารางเดียว ─────────────────────────────────────────────────────────────────────────
def _fit_signed(xs, ys, sxs, sys_, MX, MY, sx, sy, lo, hi):
    (UX, DX), (UY, DY) = MX, MY
    return _joint_fit(xs, ys, sxs, sys_, _signed([m for m, _ in UX], sx), _signed([m for m, _ in UY], sy),
                      _signed(DX, sx), _signed(DY, sy), lo, hi)


def _view(xs, ys, bbox, spx, spy, MX, MY, rs, lo, hi, idx):
    if max(len(xs), len(ys)) > MAX_LINES_PER_AXIS:
        return None, {"bbox_px": [round(v, 1) for v in bbox], "n_drawn_x": len(xs), "n_drawn_y": len(ys),
                      "reason_code": "too_many_lines"}, []
    fits = {k: _fit_signed(xs, ys, spx, spy, MX, MY, k[0], k[1], lo, hi) for k in SIGNS}
    reasons = {k: _gate(f, rs) for k, f in fits.items()}
    passing = [k for k in SIGNS if reasons[k] is None]
    base = {"bbox_px": [round(v, 1) for v in bbox], "n_drawn_x": len(xs), "n_drawn_y": len(ys)}
    issues = []
    pin = fits[(1, 1)]

    if not passing:
        sus = _suspects(xs, ys, spx, spy, MX, MY, rs, lo, hi)
        if sus:
            ax, ratio = sus["axis"], sus["ratio"]
            if ax:
                detail = (f"grid master แกน {ax} น่าจะผิด — {_ratio_th(ratio)} (อัตราส่วน {ratio:.2f}) · เส้นกริด"
                          f"เวกเตอร์ตาราง {idx + 1} อธิบายได้ครบเมื่อปรับแกนนี้เท่านั้น ระยะที่คำนวณจากแกนนี้ควรตรวจก่อนใช้")
            else:
                alt = " หรือ ".join(f"แกน {c['axis']} {_ratio_th(c['ratio'])} ถ้าแบบเป็น 1:{c['scale_nominal_R']}"
                                    for c in sus["candidates"])
                detail = (f"grid master แกน x หรือ y น่าจะอ่านระยะผิดเป็นเท่า (สองแกนต่างกัน {ratio:.2f} เท่า) — {alt} · "
                          f"เส้นกริดเวกเตอร์ตาราง {idx + 1} แยกไม่ได้ว่าแกนไหน ระยะจากทั้งสองแกนควรตรวจก่อนใช้")
            issues.append({"code": "scale_suspect", "axis": ax, "ratio": ratio, "view": idx, "source": "vector_grid",
                           "candidates": sus["candidates"], "detail_th": detail})
            return None, dict(base, reason_code="scale_suspect", px_per_m=sus["px_per_m"]), issues
        rej = dict(base, reason_code=reasons[(1, 1)])
        if pin:
            rej.update(px_per_m=round(pin["s"], 4), lines_explained=len(pin["ex"]["mt"]) + len(pin["ey"]["mt"]),
                       master_unmatched=[pin["ex"]["master_un"], pin["ey"]["master_un"]],
                       inside_unexplained=[pin["ex"]["inside"], pin["ey"]["inside"]])
        return None, rej, issues

    # สลับแกน (master x บนเส้นนอน) ที่ผ่านด่านเดียวกันและอธิบายได้เท่ากัน = ไม่รู้ว่าแกนไหนเป็นแกนไหน
    n_best = max(len(fits[k]["ex"]["mt"]) + len(fits[k]["ey"]["mt"]) for k in passing)
    for sx, sy in SIGNS:
        t = _fit_signed(xs, ys, spx, spy, MY, MX, sx, sy, lo, hi)
        if _gate(t, rs) is None and len(t["ex"]["mt"]) + len(t["ey"]["mt"]) >= n_best:
            return None, dict(base, reason_code="transpose_ambiguous"), issues

    scales = [fits[k]["s"] for k in passing]
    if max(scales) / min(scales) - 1 > SNAP_TOL:
        return None, dict(base, reason_code="scale_ambiguous"), issues
    # ทิศรายแกน: ผ่านทิศเดียว = รู้ทิศ · ผ่านทั้งสองทิศ (ระยะสมมาตร) = กำกวม ไม่ให้ตำแหน่ง แต่ scale ยังใช้ได้
    per_axis = {}
    for a, i in (("x", 0), ("y", 1)):
        sg = {k[i] for k in passing}
        per_axis[a] = "ambiguous" if len(sg) > 1 else "normal" if sg == {1} else "flipped"
    amb = [a for a in ("x", "y") if per_axis[a] == "ambiguous"]
    chosen = max(passing, key=lambda k: k[0] + k[1])      # แกนที่กำกวมแสดงแบบทิศปกติ (id ไม่ใช้วางตำแหน่ง)
    f = fits[chosen]
    orient = "ambiguous" if amb else {(1, 1): "normal", (-1, 1): "flipped_x", (1, -1): "flipped_y",
                                      (-1, -1): "flipped_both"}[chosen]
    ptm = f["s"] / rs
    snapv, r, err = _snap(ptm)
    view = dict(base, px_per_m=round(f["s"], 4), pt_per_m=round(ptm, 4),
                scale_R=round(PT_PER_M_FULL / snapv, 1), scale_nominal_R=r, snap_err=round(err, 5),
                orientation=orient, orientation_x=per_axis["x"], orientation_y=per_axis["y"], ambiguous_axes=amb,
                lines_x=_ids(MX[0], chosen[0], f["ex"]["mt"]), lines_y=_ids(MY[0], chosen[1], f["ey"]["mt"]),
                unmatched_x=len(xs) - len(f["ex"]["mt"]), unmatched_y=len(ys) - len(f["ey"]["mt"]),
                residual_max_m=round(f["res"], 4),
                transform=None if amb else {"ax": round(chosen[0] * f["s"], 5), "bx": round(f["bx"], 3),
                                            "ay": round(chosen[1] * f["s"], 5), "by": round(f["by"], 3)})
    for axis in ("x", "y"):
        if per_axis[axis] == "flipped":
            way = "ขวาไปซ้าย" if axis == "x" else "ล่างขึ้นบน"
            issues.append({"code": "origin_not_top_left", "axis": axis, "view": idx, "source": "vector_grid",
                           "detail_th": f"grid master: pos_m แกน {axis} เริ่มนับจาก{way} (ไม่ใช่ซ้ายบนตามที่ prompt "
                                        f"gridline กำหนด) — เส้นกริดเวกเตอร์ตาราง {idx + 1} เข้ากับทิศนี้ทิศเดียว "
                                        f"ควรตรวจว่า grid master อ่านทิศถูก"})
    return view, None, issues


def measure_page_vectors(page_sidecar, grid_master):
    """ไม้บรรทัดของหน้านี้จาก vector sidecar (พิกัด PNG) + grid master · ไม่แก้อินพุต ไม่ raise

    คืน {"ok", "reason_code", "reason", "views": [ตารางที่ผ่าน], "rejected": [ตารางที่ไม่ผ่าน + เหตุผล],
         "issues": [{"code": "origin_not_top_left"|"scale_suspect", "axis", "detail_th", ...}],
         "source": "vector_grid", "version": 1}
    view: px_per_m, pt_per_m, scale_R (1:R ที่ PDF เป็นจริง), scale_nominal_R, snap_err, orientation
    (normal / flipped_x / flipped_y / flipped_both / ambiguous), lines_x/y (id ที่จับคู่ได้), unmatched_x/y
    (เส้นที่วาดแต่ไม่ตรงเส้น named — รวมเงา/dummy/นอกช่วงกริด), residual_max_m, transform {ax,bx,ay,by}
    (px = a·pos_m + b, a ติดลบ = แกนกลับด้าน) หรือ None เมื่อทิศกำกวม, bbox_px (กรอบเส้นกริดของตาราง)"""
    rep = {"ok": False, "reason_code": None, "reason": None, "views": [], "rejected": [], "issues": [],
           "source": "vector_grid", "version": VERSION}

    def fail(code, extra=""):
        rep.update(reason_code=code, reason=REASON_TH[code] + extra)
        return rep

    try:
        rs, long_px, vrows, hrows = _decode(page_sidecar)
    except _Bad as e:
        return fail("malformed_sidecar", f" ({e})")
    except Exception as e:  # noqa: BLE001 — อินพุตจากเครือข่าย ห้ามล้มงาน
        return fail("malformed_sidecar", f" ({type(e).__name__})")
    try:
        MX, MY = _master(grid_master, "x"), _master(grid_master, "y")
        if len(MX[0]) < 2 or len(MY[0]) < 2:
            return fail("no_grid_master")
        min_len = MIN_SPAN_FRAC * long_px
        V = [r for r in vrows if r[3] >= MIN_PIECES and r[2] - r[1] >= min_len]
        H = [r for r in hrows if r[3] >= MIN_PIECES and r[2] - r[1] >= min_len]
        views = _views(V, H, CROSS_TOL_PT * rs)
        if not views:
            return fail("no_vector_grid")
        lo, hi = PT_PER_M_RANGE[0] * rs, PT_PER_M_RANGE[1] * rs
        for i, (xs, ys, bbox, spx, spy) in enumerate(views):
            v, rej, iss = _view(xs, ys, bbox, spx, spy, MX, MY, rs, lo, hi, i)
            rep["issues"] += iss
            if v:
                rep["views"].append(dict(v, view=i))
            else:
                rep["rejected"].append(dict(rej, view=i))
        if rep["views"]:
            rep["ok"] = True
            return rep
        codes = [r["reason_code"] for r in rep["rejected"]]
        return fail("scale_suspect" if "scale_suspect" in codes else codes[0])
    except Exception as e:  # noqa: BLE001 — report-only: อะไรแปลกก็คืน ok False ไม่ล้ม worker
        return fail("malformed_sidecar", f" ({type(e).__name__}: {e})")


# ── 6. รวมเข้า grid_master.json "validation" (สัญญาเดิมของ pass3_measure.grid_validation) ─────────
def merge_validation(validation, vector_reports):
    """validation เดิม + {"page_NN": report ของ measure_page_vectors} → validation ใหม่ (ไม่แก้ของที่รับมา)

    issue เดียวกัน (code + axis + ratio) จากหลายหน้ารวมเป็นก้อนเดียวพร้อม pages · code+axis ที่ pass3 (CV) รายงาน
    อยู่แล้ว = ต่อท้ายว่าเวกเตอร์ยืนยัน (vector_pages) ไม่เตือนซ้ำ · scale_check: suspect ชนะเสมอ (เวกเตอร์หรือ CV
    ฝั่งไหนก็ได้ สองฝั่งชี้คนละแกน = suspect_axis None ให้เว็บติดธงทุกแกน) · unknown + เวกเตอร์วัดได้ = ok"""
    out = json.loads(json.dumps(validation)) if isinstance(validation, dict) else {}
    issues = out["issues"] = [i for i in out.get("issues") or [] if isinstance(i, dict)]
    sc = out.get("scale_check") if isinstance(out.get("scale_check"), dict) else {
        "status": "unknown", "suspect_axis": None, "ratio": None, "source": "pass3 ไม่ได้รัน"}
    groups = {}
    for key in sorted(vector_reports or {}):
        rep = vector_reports[key]
        for it in (rep.get("issues") or []) if isinstance(rep, dict) else []:
            g = groups.setdefault((it.get("code"), it.get("axis"), it.get("ratio")), {"first": it, "pages": []})
            if key not in g["pages"]:
                g["pages"].append(key)
    sus_pages, sus_axes = [], set()
    for (code, axis, ratio), g in groups.items():
        pages = ", ".join(g["pages"])
        if code == "scale_suspect":
            sus_pages += g["pages"]
            sus_axes.add(axis)
        same = next((i for i in issues if i.get("code") == code and i.get("axis") == axis
                     and i.get("source") != "vector_grid"), None)
        if same:
            same["vector_pages"] = g["pages"]
            same["detail_th"] = f"{same.get('detail_th') or code} · เส้นกริดเวกเตอร์ยืนยัน ({pages})"
            continue
        it = {k: v for k, v in g["first"].items() if k != "view"}
        it.update(pages=g["pages"], source="vector_grid", detail_th=f"{g['first'].get('detail_th') or code} ({pages})")
        issues.append(it)
    if sus_pages:
        axis = sus_axes.pop() if len(sus_axes) == 1 else None
        src = "vector_grid " + ", ".join(sorted(set(sus_pages)))
        if sc.get("status") == "suspect":
            axis = axis if sc.get("suspect_axis") == axis else None
            src = f"{sc.get('source')} + {src}"
        ratio = next(k[2] for k in groups if k[0] == "scale_suspect")
        sc = {"status": "suspect", "suspect_axis": axis, "ratio": ratio, "source": src}
    elif sc.get("status") == "unknown":
        ok = sorted(k for k, r in (vector_reports or {}).items() if isinstance(r, dict) and r.get("ok"))
        if ok:
            # สเกลเดียวสองแกนที่อธิบายเส้นครบทั้งสองแกน = สองแกนสอดคล้องกันพอดี (อัตราส่วน 1)
            sc = {"status": "ok", "suspect_axis": None, "ratio": 1.0, "source": "vector_grid " + ", ".join(ok)}
    out["scale_check"] = sc
    return out


def summary_line(vector_reports):
    """บรรทัดเดียวถึงคน (warnings ระดับงาน) — None ถ้าไม่มีหน้าที่ลองวัด"""
    reps = [r for r in (vector_reports or {}).values() if isinstance(r, dict)]
    if not reps:
        return None
    ok = [r for r in reps if r.get("ok")]
    scales = sorted({f"1:{v['scale_R']:g}" for r in ok for v in r.get("views") or []})
    why = {}
    for r in reps:
        if not r.get("ok"):
            why[r.get("reason_code")] = why.get(r.get("reason_code"), 0) + 1
    s = (f"ไม้บรรทัดเส้นกริดเวกเตอร์ (รายงานอย่างเดียว ไม่แก้ผลอ่านแบบ): วัดได้ {len(ok)}/{len(reps)} หน้า"
         + (f" มาตราส่วนใน PDF {', '.join(scales)}" if scales else ""))
    if why:
        s += " · วัดไม่ได้: " + ", ".join(f"{k} {n}" for k, n in sorted(why.items(), key=lambda t: -t[1]))
    return s
