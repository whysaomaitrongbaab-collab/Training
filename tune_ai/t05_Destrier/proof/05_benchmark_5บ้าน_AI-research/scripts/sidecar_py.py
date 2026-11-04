#!/usr/bin/env python3
"""vector sidecar ด้วย PyMuPDF — ทำซ้ำ js/drawing/pdf-vector-sidecar.js (vs_mergeRuns + frame) ให้ vector_ruler ใช้ได้
เฉพาะเส้นตรง (l/re/qu) · พิกัด px ของ PNG ที่เรนเดอร์ 200 dpi (S = 200/72)"""
import math
import fitz

Q = 10
MERGE_GAP_PT, MIN_SPAN_FRAC = 12, 0.02


def page_sidecar(pdf_path, page_no, dpi=200):
    doc = fitz.open(pdf_path); pg = doc[page_no - 1]
    S = dpi / 72.0
    W, H = pg.rect.width, pg.rect.height
    png_w, png_h = int(round(W * S)), int(round(H * S))
    layers, lidx, segs = [], {}, []
    for d in pg.get_drawings():
        name = d.get("layer")
        if name not in lidx: lidx[name] = len(layers); layers.append(name)
        L = lidx[name]
        for it in d.get("items", []):
            k = it[0]
            if k == "l":
                p, q = it[1], it[2]; segs.append((p.x * S, p.y * S, q.x * S, q.y * S, L))
            elif k == "re":
                r = it[1]; pts = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]
                for i in range(4):
                    a, b = pts[i], pts[(i + 1) % 4]; segs.append((a[0] * S, a[1] * S, b[0] * S, b[1] * S, L))
            elif k == "qu":
                qd = it[1]; pts = [qd.ul, qd.ur, qd.lr, qd.ll]
                for i in range(4):
                    a, b = pts[i], pts[(i + 1) % 4]; segs.append((a.x * S, a.y * S, b.x * S, b.y * S, L))
    AXIS_TOL, KEY, gap = 0.1 * S, 0.25 * S, MERGE_GAP_PT * S
    Hm, Vm = {}, {}
    for x0, y0, x1, y1, L in segs:
        if abs(y1 - y0) <= AXIS_TOL and abs(x1 - x0) > AXIS_TOL:
            Hm.setdefault((round((y0 + y1) / 2 / KEY), L), []).append((min(x0, x1), max(x0, x1)))
        elif abs(x1 - x0) <= AXIS_TOL and abs(y1 - y0) > AXIS_TOL:
            Vm.setdefault((round((x0 + x1) / 2 / KEY), L), []).append((min(y0, y1), max(y0, y1)))

    def runs(g):
        out = []
        for (kp, kl), iv in g.items():
            iv.sort(); a0, a1 = iv[0]; n = 1
            for s, e in iv[1:]:
                if s - a1 <= gap: a1 = max(a1, e); n += 1
                else: out.append((kp * KEY, a0, a1, n, kl)); a0, a1, n = s, e, 1
            out.append((kp * KEY, a0, a1, n, kl))
        return out
    thr = MIN_SPAN_FRAC * max(W, H) * S
    P = lambda x: round(x * Q)
    run = lambda r: [P(r[0]), P(r[1]), P(r[2]), r[3], r[4]]
    return {"frame": {"units_per_px": Q, "png_w": png_w, "png_h": png_h, "render_scale": S, "rotate": pg.rotation},
            "layers": layers,
            "hlines": [run(r) for r in runs(Hm) if r[2] - r[1] >= thr],
            "vlines": [run(r) for r in runs(Vm) if r[2] - r[1] >= thr]}


if __name__ == "__main__":
    import json, sys
    sys.path.insert(0, r"D:\00mk\steel project\งานสมบูรณ์\Constistant\server\purson-worker")
    import vector_ruler as VR
    pdf, pn, res = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    sc = page_sidecar(pdf, pn)
    R = json.load(open(res, encoding="utf-8"))
    gm = next(f["json"] for f in R["files"] if f["name"] == "grid_master.json")
    rep = VR.measure_page_vectors(sc, gm)
    print("hlines", len(sc["hlines"]), "vlines", len(sc["vlines"]), "ok", rep["ok"], rep.get("reason_code"), rep.get("reason"))
    for v in rep["views"]:
        print(" view", v["view"], "R", v.get("scale_R"), "orient", v.get("orientation"), "x", v.get("lines_x"), "y", v.get("lines_y"), "T", v.get("transform"), "bbox", v.get("bbox_px"))
    for r in rep["rejected"][:5]: print(" rej", r.get("reason_code"), str(r.get("reason"))[:150])
