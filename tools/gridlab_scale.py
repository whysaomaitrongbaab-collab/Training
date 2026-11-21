#!/usr/bin/env python3
"""
tools/gridlab_scale.py — grid lab ส่วน 3 ขั้น "ตั้งสเกลต่อหน้า" (แผนผัง King ประชุม 19 พ.ย. 2569) แล้วได้ pos_m ของทุกเส้น
= grid master ที่อ่านจากแบบเองล้วน (ไม่ใช้โมเดล) ต่อจาก gridlab_probe.detect()

    python tools/gridlab_scale.py <บ้าน> <หน้า>          # สเกลต่อแปลน + pos_m ของเส้น
    python tools/gridlab_scale.py --eval                  # เทียบระยะระหว่างเส้นกับ pos_m ในเฉลย (ชุดหน้าเดียวกับ gridlab --eval)
    python tools/gridlab_scale.py --demo                  # self-check ของตรรกะเลือกสเกล (ไม่ต้องมีไฟล์จริง)

ทำไมใช้ตัวเลขบอกระยะ ไม่ใช้โน้ตมาตราส่วน: วัดแล้ว 2026-11-19 มาตราส่วนจริงใน PDF ต่างจากที่พิมพ์ (1ชั้น_27: 35.0 pt/m แต่ 1:75 ควรได้ 37.8)
ทำไม OCR: ตัวเลขบอกระยะไม่อยู่ในข้อความฝังเลยใน 5 หน้าที่ลอง (siamplan/ภาครัฐ — CAD วาดตัวเลขมิติเป็นเส้น)

ตรรกะ (ต่อแปลน ต่อแกน):
  1. แถบที่โซ่เส้นบอกระยะอยู่ = ระหว่างแถววงหัวกริดกับเส้นกริดแรกของอีกแกนในแปลนเดียวกัน (ธรรมเนียมแบบ) -> OCR
     แถบของเส้นนอน (ตัวเลขเขียนตั้ง) หมุนภาพทั้งสองทิศแล้วรวมผล
  2. ตัวเลข "d.dd" ที่ศูนย์กลางอยู่กลางระหว่างเส้นกริดคู่ใดๆ (i<j รวมตัวเลขรวมที่คร่อมหลายช่อง) -> สเกลผู้สมัคร (pt/m)
  3. สเกลที่มีคู่เส้นต่างกันยืนยันตรงกันมากสุด (±1.5%) ชนะ; ต้อง >= 2 คู่ หรือ 1 คู่ที่อีกแกนของแปลนเดียวกันยืนยัน
  4. แกนที่ไม่มีตัวเลขยืมสเกลจากอีกแกนของแปลนเดียวกัน (วัดแล้ว x/y ตรงกันภายใน 2% ใน 153/154 แปลน — gridlab --eval คืน 21 พ.ย.)
  5. pos_m = (pos - pos ของเส้นแรก) / สเกล ปัด 0.01 ม. (จุดเริ่ม 0 ที่เส้นซ้ายสุด/บนสุดของแปลน — ทิศของเฉลยแต่ละบ้านไม่เหมือนกัน)
ไม่มีตัวเลขที่ยืนยันได้ = ไม่ให้ pos_m (ไม่เดาจากโน้ตมาตราส่วน)

ผลวัด 2026-11-21 รอบสุดท้าย (--eval --dump: ชุดหน้าเดียวกับ gridlab_probe --eval = หน้าแปลน 2 หน้าแรกของบ้านที่มีเฉลย grid master;
รอบก่อนหน้าในวันเดียวกันได้ 156 แปลน/153/831 จาก 832 ช่อง ก่อนแก้ตัวหาเส้นรอบสุดท้าย — ใช้เลขรอบสุดท้ายข้างล่าง):
  - 155 แปลน: หาสเกลได้ 154 (99%) ทุกตัวมีตัวเลขยืนยันจากทั้งสองแกน; ไม่มีสเกล 1
  - ระยะระหว่างเส้นติดกัน (ชื่อตรงเฉลย) เทียบ |Δpos_m| ของเฉลย: 841/842 ช่อง คลาดไม่เกิน 2 ซม.
  - ช่องเดียวที่ไม่ตรง (2ชั้น_07 หน้า 5 ช่อง 2-3 ได้ 3.0 เฉลย 3.5) = แบบวาดวงหัวกริด 3 คลาดจากขีดบอกระยะ ~0.5 ม. เอง
    (ผังบริเวณ A-03) เส้นตามที่วาดถูก แต่ pos_m ที่ได้คือของเส้นที่วาด ไม่ใช่ของตัวเลขระยะ — ยังไม่มีธงจับกรณีนี้
  - ข้อจำกัด: ต้องมีตัวเลขระยะอยู่ระหว่างวงหัวกริดกับตัวอาคาร (ธรรมเนียมแบบที่เจอทั้งหมด); โซ่ระยะอีกฝั่งยังไม่ได้อ่าน;
    หน้าภาพสแกนไม่รองรับ (ตามขั้นต่ำ "เริ่มจากเวกเตอร์"); จุดเริ่ม 0 อยู่ที่เส้นแรกของแปลน ไม่ใช่ที่เส้นอ้างอิงของเฉลย
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
DIM_RE = re.compile(r"^\d{1,2}[.,]\d{2,3}$")
MID_TOL = 0.03          # ตัวเลขต้องอยู่ห่างจุดกึ่งกลางคู่เส้นไม่เกินสัดส่วนนี้ของช่อง (+2 pt): ตัวจริงคลาด < 1 pt แต่ตัวเลข
                        # ระยะย่อย (0.50 ไปขีดช่องเปิด) บังเอิญห่างกลางช่อง ~8.5 pt แล้วให้สเกลปลอม 210 pt/m (1ชั้น_27 หน้า 11)
AGREE = 0.015           # สเกลที่ต่างกันไม่เกิน 1.5% = ตัวเดียวกัน
SCALE_RANGE = (5.0, 150.0)   # pt/m ที่เป็นไปได้ของแปลน/แบบขยาย (~1:500 ถึง ~1:20); นอกช่วง = จับคู่ผิด
MAX_PX = 3300           # ด้านยาวภาพที่ส่ง OCR (paddle ล้มที่ ~4000)


def scale_candidates(positions, tokens, tag=None):
    """positions = ตำแหน่งเส้น (pt) เรียงแล้ว, tokens = [(value_m, along_pt)] -> [(scale, (tag, i, j))] (pure)"""
    out = []
    for v, c in tokens:
        if v <= 0:
            continue
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                a, b = positions[i], positions[j]
                s = (b - a) / v
                if abs(c - (a + b) / 2) <= MID_TOL * (b - a) + 2 and SCALE_RANGE[0] <= s <= SCALE_RANGE[1]:
                    out.append((s, (tag, i, j)))
    return out


def pick_scale(cands):
    """สเกลที่มีคู่เส้นต่างกันสนับสนุนมากสุด -> (scale, {คู่ที่สนับสนุน}) หรือ (None, set()) (pure)
    เสมอกัน: เลือกสเกลเล็กกว่า (ตัวเลขรวมที่ยาวกว่าให้สเกลเล็ก — ตัวเลขย่อยที่จับผิดคู่ให้สเกลใหญ่เกินจริง)"""
    best = (None, set())
    for s, _ in cands:
        keys = {k for t, k in cands if abs(t - s) <= AGREE * s}
        if len(keys) > len(best[1]) or (len(keys) == len(best[1]) and best[0] and s < best[0]):
            mates = [t for t, k in cands if abs(t - s) <= AGREE * s]
            best = (sum(mates) / len(mates), keys)
    return best


def _band_tokens(page, rect, vertical_text):
    """OCR แถบ (พิกัดที่ตามองเห็น) -> [(value_m, cx_pt, cy_pt)]; vertical_text: หมุนภาพทั้งสองทิศแล้วรวม"""
    import fitz
    import numpy as np
    import titleblock_extract as T
    rect = rect & page.rect
    if rect.is_empty or rect.width < 5 or rect.height < 5:
        return []
    dpi = int(min(300, MAX_PX * 72 / max(rect.width, rect.height)))
    pix = page.get_pixmap(dpi=dpi, clip=rect)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    img = np.ascontiguousarray(img[:, :, :3] if pix.n >= 3 else np.repeat(img, 3, axis=2))
    H = img.shape[0]
    W = img.shape[1]
    views = [(np.ascontiguousarray(np.rot90(img, k=-1)), "cw"), (np.ascontiguousarray(np.rot90(img, k=1)), "ccw")] \
        if vertical_text else [(img, "none")]
    out = []
    k = 72.0 / dpi
    for (im, how), r in zip(views, T._reader().predict([v for v, _ in views])):
        for txt, box in zip(r.get("rec_texts", []), r.get("rec_boxes", [])):
            toks = [t for t in re.split(r"\s+", txt.strip()) if t]
            x0, y0, x1, y1 = [float(b) for b in box]
            for n, t in enumerate(toks):     # ข้อความที่ติดกันหลายตัวเลข: แบ่งกล่องตามลำดับ
                if not DIM_RE.match(t):
                    continue
                u = x0 + (x1 - x0) * (n + 0.5) / len(toks)
                w = (y0 + y1) / 2
                if how == "none":
                    px, py = u, w
                elif how == "cw":            # B = rot90(A, -1): B[w, u] = A[H-1-u, w]
                    px, py = w, H - 1 - u
                else:                        # B = rot90(A, 1): B[w, u] = A[u, W-1-w]
                    px, py = W - 1 - w, u
                out.append((float(t.replace(",", ".")), rect.x0 + px * k, rect.y0 + py * k))
    return out


def plan_scales(page, lines, ocr=True):
    """lines = gridlab_probe.detect() -> {plan: dict(scale, source, support, per_axis)} และใส่ pos_m ลงในแต่ละเส้น"""
    import fitz
    plans = collections.defaultdict(lambda: {"v": [], "h": []})
    for ax in ("v", "h"):
        for ln in lines.get(ax, []):
            if ln.get("method") == "bubble" and ln.get("plan") is not None:
                plans[ln["plan"]][ax].append(ln)
    result = {}
    for pid, axes in plans.items():
        per, pool = {}, []
        for ax, other in (("v", "h"), ("h", "v")):
            ls = sorted(axes[ax], key=lambda l: l["pos"])
            if len(ls) < 2 or not ocr:
                continue
            pos = [l["pos"] for l in ls]
            bub = ls[0]["bubble"]
            d, s = bub[2], ls[0].get("dir", 1)
            b_along = bub[1] if ax == "v" else bub[0]
            ops = [l["pos"] for l in axes[other]]
            if ops:      # ขอบแถบ = เส้นแรกของอีกแกนฝั่งที่ก้านชี้ไป
                inner = min(ops) if s > 0 else max(ops)
            else:
                inner = b_along + s * 12 * d
            lo_al, hi_al = sorted((b_along + s * d / 2, inner))
            gap = min(b - a for a, b in zip(pos, pos[1:])) if len(pos) > 1 else 50
            a0, a1 = pos[0] - 0.6 * gap, pos[-1] + 0.6 * gap
            rect = fitz.Rect(a0, lo_al, a1, hi_al) if ax == "v" else fitz.Rect(lo_al, a0, hi_al, a1)
            toks = _band_tokens(page, rect, vertical_text=(ax == "h"))
            cands = scale_candidates(pos, [(v, x if ax == "v" else y) for v, x, y in toks], tag=ax)
            pool += cands
            sc, keys = pick_scale(cands)
            per[ax] = dict(scale=round(sc, 3) if sc else None, support=len(keys), tokens=len(toks))
        # แปลนเดียวมีสเกลเดียว: เลือกจากคู่ยืนยันของทั้งสองแกนรวมกัน (ไม่ให้แกนใดแกนหนึ่งชนะเพราะตัวเลขย่อยมาก)
        scale, keys = pick_scale(pool)
        nv, nh = sum(k[0] == "v" for k in keys), sum(k[0] == "h" for k in keys)
        if scale and nv and nh:
            source = "dims_both_axes"
        elif scale and max(nv, nh) >= 2:
            source = "dims_v_only" if nv else "dims_h_only"
        else:
            scale, source = None, None    # คู่เดียวที่ไม่มีอีกแกนยืนยัน = ยังไม่เชื่อ
        result[pid] = dict(scale=round(scale, 3) if scale else None, source=source, support=dict(v=nv, h=nh), per_axis=per)
        for ax in ("v", "h"):
            ls = sorted(axes[ax], key=lambda l: l["pos"])
            own = per.get(ax, {})
            # แกนที่มีตัวเลขยืนยันเอง >= 2 คู่และไม่ต่างจากสเกลรวม ใช้สเกลของแกนนั้น (สองแกนต่างกันได้ ~0.1% —
            # สเกลเฉลี่ยทำให้ 10.50 ม. กลายเป็น 10.49 บน 1ชั้น_29 หน้า 10)
            s_ax = own["scale"] if scale and own.get("scale") and own.get("support", 0) >= 2 \
                and abs(own["scale"] - scale) <= AGREE * scale else scale
            for ln in ls:
                ln["pos_m"] = round((ln["pos"] - ls[0]["pos"]) / s_ax, 2) if s_ax else None
    return result


# ---------- เทียบเฉลย ----------

def gt_pos(house):
    import gridlab_probe as G
    for base in ("json_แก้ไขแล้ว", "rawjson_ยังไม่ได้แก้ไขโดนคน"):
        for d in (G.ROOT / base).glob(f"*{house}"):
            for f in d.glob("*gridline*.json"):
                g = json.loads(f.read_text(encoding="utf-8")).get("grid", {})
                return ({str(l["id"]): l.get("pos_m") for l in g.get("x_lines", []) if l.get("type") != "dummy"},
                        {str(l["id"]): l.get("pos_m") for l in g.get("y_lines", []) if l.get("type") != "dummy"})
    return None


def evaluate(dump_path=None):
    """ชุดหน้าเดียวกับ gridlab_probe --eval: ทุกช่องระหว่างเส้นติดกัน (ชื่อตรงเฉลย) เทียบ |Δpos_m| ของเฉลย"""
    import fitz
    import gridlab_probe as G
    st, bad, recs = collections.Counter(), [], []
    for h in sorted(x.name for x in (G.ROOT / "image").iterdir() if x.is_dir()):
        ids, gp, pp = G.gt_ids(h), gt_pos(h), G.plan_pages(h)[:2]
        if not ids or not gp or not pp:
            continue
        doc = fitz.open(G.pdf_of(h))
        if not any(len(p.get_text("words")) > 8 for p in list(doc)[:12]):
            continue
        for pn in pp:
            if pn > len(doc):
                continue
            page = doc[pn - 1]
            lines = G.detect(page)
            res = plan_scales(page, lines)
            recs.append(dict(house=h, page=pn, plans={str(k): {kk: vv for kk, vv in v.items() if kk != "per_axis"} | {
                "per_axis": v["per_axis"]} for k, v in res.items()}))
            for pid, r in res.items():
                st["plans"] += 1
                st["scale_" + (r["source"] or "none")] += 1
                for ax, gmap in (("v", gp[0]), ("h", gp[1])):
                    ls = sorted([l for l in lines[ax] if l.get("plan") == pid and l["label"] in gmap
                                 and isinstance(gmap[l["label"]], (int, float))], key=lambda l: l["pos"])
                    for a, b in zip(ls, ls[1:]):
                        if a.get("pos_m") is None:
                            st["gap_no_scale"] += 1
                            continue
                        want = abs(gmap[b["label"]] - gmap[a["label"]])
                        got = round(b["pos_m"] - a["pos_m"], 2)
                        st["gap_checked"] += 1
                        if abs(got - want) <= 0.02:
                            st["gap_ok_2cm"] += 1
                        else:
                            st["gap_off"] += 1
                            bad.append((h, pn, pid, ax, f"{a['label']}-{b['label']}", got, want, r["scale"], r["source"]))
    print(dict(st))
    for b in bad[:40]:
        print("  ", *b)
    if dump_path:
        Path(dump_path).write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")


def demo():
    pos = [100.0, 205.0, 310.0, 415.0]                     # ช่องละ 105 pt = 3.00 ม. ที่ 35 pt/m
    toks = [(3.0, 152.5), (3.0, 257.5), (3.0, 362.5),     # ตัวเลขช่องย่อย
            (9.0, 257.5),                                  # ตัวเลขรวม 1->4 กึ่งกลางเดียวกับช่อง 2->3 (ต้องไม่ทำให้สเกลเพี้ยน)
            (1.5, 126.0)]                                  # ระยะย่อยไปขีดที่ไม่ใช่กริด: ไม่อยู่กลางคู่ไหน
    s, keys = pick_scale(scale_candidates(pos, toks))
    assert abs(s - 35.0) < 1e-6 and len(keys) == 4, (s, keys)    # 3 ช่อง + ตัวรวม 1->4
    assert pick_scale([]) == (None, set())
    assert pick_scale(scale_candidates([0.0, 100.0], [(2.0, 50.0)]))[0] == 50.0
    # ตัวเลขระยะย่อยที่บังเอิญอยู่ใกล้กลางช่อง (ห่าง 8.5 pt) ต้องไม่ถูกจับคู่ (1ชั้น_27 หน้า 11 เคยได้ 210 pt/m)
    assert scale_candidates([300.8, 406.1], [(0.5, 362.0)]) == []
    # สเกลนอกช่วงที่เป็นไปได้ถูกทิ้ง แม้ตัวเลขอยู่กลางช่องพอดี
    assert scale_candidates([0.0, 105.0], [(0.5, 52.5)]) == []
    print("OK — self-check ผ่าน (เลือกสเกลจากตัวเลขบอกระยะ — ไม่ได้ OCR จริง ใช้ --eval)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("house", nargs="?")
    ap.add_argument("page", nargs="?", type=int)
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--dump")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if a.eval:
        return evaluate(a.dump)
    if not (a.house and a.page):
        ap.print_help()
        return
    import fitz
    import gridlab_probe as G
    page = fitz.open(G.pdf_of(a.house))[a.page - 1]
    lines = G.detect(page)
    res = plan_scales(page, lines)
    for pid, r in sorted(res.items()):
        print(f"แปลน {pid}: สเกล {r['scale']} pt/m ({r['source']}) ต่อแกน {r['per_axis']}")
        for ax in ("v", "h"):
            print("  ", ax, [(ln["label"], ln.get("pos_m")) for ln in sorted(lines[ax], key=lambda l: l["pos"]) if ln.get("plan") == pid])


if __name__ == "__main__":
    main()
