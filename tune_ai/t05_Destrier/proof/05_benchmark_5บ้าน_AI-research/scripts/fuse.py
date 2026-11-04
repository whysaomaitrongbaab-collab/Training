#!/usr/bin/env python3
"""fuse.py — รวมผล CV (กล่องคานจาก pass1.5/2.5) + หัวกริด (วงกลม+OCR) + ป้ายคาน (OCR) + ผลโมเดล
เป็นช่วงคาน (รหัส, ปลายช่วงกริด) แบบเดียวกับที่เกณฑ์ของ King ต้องการ

กติกา: ใช้เฉพาะสิ่งที่ระบบหาเองได้ — ภาพหน้า, ครอป/ผล CV ใน workroot ของรอบวัด, ผลโมเดล (result.json)
ห้ามแตะเฉลยเด็ดขาด (เฉลยใช้แค่ตอนให้คะแนนใน score5.py)

    python fuse.py TEST-01 [TEST-02 ...]   → out/<TEST>/fused.json + fused_debug.json
"""
import glob, json, os, re, sys, time
from statistics import median
import cv2
import numpy as np

B = r"D:\Temp\claude\3049db1b73f5b7d5\c641593e-2919-41af-bebc-66157c3c1ea4\scratchpad\bench5"
TEMP = r"D:\Temp"
_OCR = None


def ocr():
    global _OCR
    if _OCR is None:
        from paddleocr import PaddleOCR
        _OCR = PaddleOCR(lang="th", enable_mkldnn=False, use_doc_orientation_classify=False,
                         use_doc_unwarping=False, use_textline_orientation=False,
                         text_det_limit_side_len=960, text_det_limit_type="max")
    return _OCR


def read(img):
    """OCR ภาพเล็ก → [(text, score, (cx, cy))] ในพิกัดของภาพนั้น"""
    if img is None or img.size == 0 or min(img.shape[:2]) < 8:
        return []
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    try:
        r = ocr().predict(img)[0]
    except Exception:
        return []
    out = []
    polys = r.get("rec_polys") if r.get("rec_polys") is not None else r.get("dt_polys")
    for t, s, p in zip(r["rec_texts"], r["rec_scores"], polys):
        p = np.asarray(p).reshape(-1, 2)
        out.append((str(t), float(s), (float(p[:, 0].mean()), float(p[:, 1].mean()))))
    return out


def norm(t):
    t = re.sub(r"[\s\.\-_·]", "", t.upper())
    return t.replace("Ｂ", "B")


# ── บ้าน → workroot / หน้าแปลนคาน / ผล CV ───────────────────────────────────────
def find_workroot(n_pages):
    cands = []
    for d in glob.glob(os.path.join(TEMP, "purson_p1_*")):
        wr = os.path.join(d, "work", "bench-vllm")
        if os.path.isdir(wr) and len(os.listdir(os.path.join(d, "image"))) == n_pages:
            cands.append((os.path.getmtime(d), wr))
    return max(cands)[1] if cands else None


def crop_offset(page_img, crop_img):
    if crop_img.shape == page_img.shape:
        return 0, 0
    f = 0.25
    a = cv2.resize(page_img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    b = cv2.resize(crop_img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    r = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED); _, _, _, (x, y) = cv2.minMaxLoc(r)
    X, Y = int(x / f), int(y / f); best = (-2, X, Y)
    for dy in range(-6, 7, 2):           # refine ที่ความละเอียดจริง (ตัวอย่างกลางครอป)
        for dx in range(-6, 7, 2):
            x0, y0 = X + dx, Y + dy
            if x0 < 0 or y0 < 0: continue
            h, w = crop_img.shape
            ph, pw = min(h, 400), min(w, 400); cy0, cx0 = (h - ph) // 2, (w - pw) // 2
            pa = page_img[y0 + cy0:y0 + cy0 + ph, x0 + cx0:x0 + cx0 + pw]
            pb = crop_img[cy0:cy0 + ph, cx0:cx0 + pw]
            if pa.shape != pb.shape: continue
            s = -float(np.mean(np.abs(pa.astype(int) - pb.astype(int))))
            if s > best[0]: best = (s, x0, y0)
    return best[1], best[2]


def plan_pages(wr):
    man = json.load(open(os.path.join(wr, "pass2", "plan_beam", "manifest.json"), encoding="utf-8"))
    out = []
    for s in man.get("sources", []):
        stem = os.path.splitext(os.path.basename(s["image"]))[0]
        cvd = os.path.join(wr, "pass2", "plan_beam", "cv")
        f25, f15 = os.path.join(cvd, stem + "_cv25.json"), os.path.join(cvd, stem + "_cv.json")
        f = f25 if os.path.exists(f25) else f15
        els = json.load(open(f, encoding="utf-8")).get("elements", []) if os.path.exists(f) else []
        out.append({"page": int(s["png"]), "stem": stem, "crop": os.path.join(wr, "pass2", "plan_beam", s["image"]),
                    "cropped": bool(s.get("cropped")), "cv": els})
    return out


# ── หัวกริด: วงกลม + OCR ───────────────────────────────────────────────────────
def bubbles(gray, bbox, margin=650):
    x0, y0, x1, y1 = bbox
    X0, Y0 = max(0, int(x0 - margin)), max(0, int(y0 - margin))
    X1, Y1 = min(gray.shape[1], int(x1 + margin)), min(gray.shape[0], int(y1 + margin))
    sub = gray[Y0:Y1, X0:X1]
    f = 0.5; small = cv2.resize(sub, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    # สองรอบ: ภาพเดิม + ภาพที่ทำเส้นหนาขึ้น (แบบสแกนเส้นวงกลมขาดเป็นจุด) · รวมแล้วตัดวงซ้ำ
    found = []
    for img in (small, cv2.erode(small, np.ones((3, 3), np.uint8))):
        cs = cv2.HoughCircles(cv2.medianBlur(img, 3), cv2.HOUGH_GRADIENT, dp=1, minDist=18,
                              param1=120, param2=16, minRadius=10, maxRadius=17)
        for c in ([] if cs is None else cs[0]):
            if all((c[0] - d[0]) ** 2 + (c[1] - d[1]) ** 2 > 12 ** 2 for d in found):
                found.append(c)
    out = []
    for cx, cy, r in found:
        cx, cy, r = cx / f + X0, cy / f + Y0, r / f
        if x0 - 40 < cx < x1 + 40 and y0 - 40 < cy < y1 + 40:
            continue                              # วงในแปลน (ป้ายพื้น S0 ฯลฯ) ไม่ใช่หัวกริด
        k = int(r * 0.72)
        patch = gray[int(cy - k):int(cy + k), int(cx - k):int(cx + k)]
        if patch.size == 0: continue
        patch = cv2.copyMakeBorder(cv2.resize(patch, None, fx=2, fy=2), 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
        best = None
        for t, s, _ in read(patch):
            t = norm(t)
            if re.fullmatch(r"[A-Z]'{0,4}|\d{1,2}'{0,4}", t) and s > 0.5 and (best is None or s > best[1]):
                best = (t, s)
        if best:
            out.append({"id": best[0], "score": best[1], "x": cx, "y": cy, "r": r})
    return out


def grid_from_bubbles(bbs, bbox, master):
    """bubbles นอกกรอบบน/ล่าง → เส้นตั้ง (x) · ซ้าย/ขวา → เส้นนอน (y) · id ซ้ำ = ค่ากลาง
    + เส้น dummy จาก grid master ของโมเดล (ถ้ามี) ด้วย fit px = a·pos + b จากเส้น named ที่ตรงกัน"""
    x0, y0, x1, y1 = bbox
    X, Y = {}, {}
    for b in bbs:
        if (b["y"] < y0 or b["y"] > y1) and x0 - 80 <= b["x"] <= x1 + 80:
            X.setdefault(b["id"], []).append(b["x"])
        elif (b["x"] < x0 or b["x"] > x1) and y0 - 80 <= b["y"] <= y1 + 80:
            Y.setdefault(b["id"], []).append(b["y"])
    X = {k: median(v) for k, v in X.items()}; Y = {k: median(v) for k, v in Y.items()}
    src = {"x": "bubble", "y": "bubble"}
    g = (master or {}).get("grid") if isinstance(master, dict) else None
    for ax, D in (("x", X), ("y", Y)):
        if not g: continue
        # แกนของ master ที่ id ตรงกับ bubble มากกว่า (master ของโมเดลอาจสลับชื่อแกน)
        best = None
        for key in ("x_lines", "y_lines"):
            L = [l for l in g.get(key) or [] if isinstance(l, dict) and isinstance(l.get("pos_m"), (int, float))]
            m = [(l["pos_m"], D[str(l["id"])]) for l in L if str(l.get("id")) in D]
            if len(m) >= 2 and (best is None or len(m) > len(best[1])):
                best = (L, m)
        if not best: continue
        L, m = best
        idmap = {str(l["id"]): l["pos_m"] for l in L}
        while True:
            a, b = np.polyfit([p for p, _ in m], [q for _, q in m], 1)
            errs = [abs(a * p + b - q) for p, q in m]
            if max(errs) <= 25 or len(m) <= 2: break
            bad = errs.index(max(errs)); m.pop(bad)
        if max(errs) > 25 or abs(a) < 20: continue  # master กับหัวกริดไม่ลงกัน — ไม่เติม dummy
        good = {round(q, 1) for _, q in m}
        for k in [k for k in D if k in idmap and round(D[k], 1) not in good]:
            D[k] = a * idmap[k] + b                 # หัวกริดที่หลุดแนว → ใช้ตำแหน่งจาก fit แทน
        for l in L:
            lid = str(l["id"])
            if lid not in D: D[lid] = a * l["pos_m"] + b
        src[ax] = "bubble+master"
    return X, Y, src


# ── ช่วงคานจากกล่อง CV ─────────────────────────────────────────────────────────
NAMED = re.compile(r"^([A-Z]|\d{1,2})$")


def spans_from_cv(cv, off, X, Y, tol_axis=30, tol_end=70):
    xs = sorted(X.items(), key=lambda kv: kv[1]); ys = sorted(Y.items(), key=lambda kv: kv[1])
    out = []
    for e in cv:
        cls = e.get("class", "")
        if not cls.startswith("beam"): continue
        cx, cy, w, h = e["cx"] + off[0], e["cy"] + off[1], e["w"], e["h"]
        horiz = cls == "beam_h" or (cls == "beam" and w >= h)
        line_c, a0, a1, along, cross = (cy, cx - w / 2, cx + w / 2, xs, ys) if horiz else (cx, cy - h / 2, cy + h / 2, ys, xs)
        near = min(cross, key=lambda kv: abs(kv[1] - line_c), default=None)
        if not near or abs(near[1] - line_c) > tol_axis: continue
        inside = [kv for kv in along if a0 - tol_end <= kv[1] <= a1 + tol_end]
        if len(inside) < 2: continue
        cuts = [inside[0]] + [kv for kv in inside[1:-1] if NAMED.match(kv[0])] + [inside[-1]]
        for p, q in zip(cuts, cuts[1:]):
            out.append({"line": near[0], "horiz": horiz, "a": p[0], "b": q[0], "line_px": near[1],
                        "pa": p[1], "pb": q[1], "box": e.get("n")})
    # ช่วงเดียวกันจากกล่องซ้อนกัน → เหลืออันเดียว
    seen, uniq = set(), []
    for s in out:
        k = (s["line"], s["horiz"], frozenset((s["a"], s["b"])))
        if k not in seen: seen.add(k); uniq.append(s)
    return uniq


def label_span(gray, s, known):
    mid = (s["pa"] + s["pb"]) / 2; L = abs(s["pb"] - s["pa"]); half = max(90, min(260, L * 0.45))
    lc = s["line_px"]
    if s["horiz"]:
        y0, y1, x0, x1 = int(lc - 85), int(lc + 85), int(mid - half), int(mid + half)
        crops = [(gray[max(0, y0):y1, max(0, x0):x1], None)]
    else:
        y0, y1, x0, x1 = int(mid - half), int(mid + half), int(lc - 85), int(lc + 85)
        c = gray[max(0, y0):y1, max(0, x0):x1]
        crops = [(cv2.rotate(c, cv2.ROTATE_90_CLOCKWISE), "cw"), (cv2.rotate(c, cv2.ROTATE_90_COUNTERCLOCKWISE), "ccw")]
    best = None
    for scale in (1, 2):
        if best: break
        for img0, rot in crops:
            img = img0 if scale == 1 else cv2.resize(img0, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            best = _pick(img, known, best)
    return best


def _pick(img, known, best):
    H, W = img.shape[:2]
    if True:
        for t, sc, (tx, ty) in read(img):
            t = norm(t)
            ok = t in known if known else bool(re.fullmatch(r"B\d{1,2}[A-Z]?", t))
            if not ok or sc < 0.6: continue
            d = abs(tx - W / 2) / W                  # ใกล้กลางช่วงที่สุดชนะ (สัดส่วน — เทียบข้ามสเกลได้)
            if best is None or d < best[2]: best = (t, sc, d)
    return best


def run_house(tid):
    job = json.load(open(os.path.join(B, tid, "job.json"), encoding="utf-8"))
    n = len(job["payload"]["pages"])
    wr = find_workroot(n)
    R = json.load(open(os.path.join(B, "out", tid, "vllm", "result.json"), encoding="utf-8"))
    F = {f["name"]: f.get("json") for f in R["files"]}
    master = F.get("grid_master.json") if isinstance(F.get("grid_master.json"), dict) else None
    known = set()
    for name, j in F.items():
        if name.startswith("page_") and isinstance(j, dict):
            for e in j.get("elements") or []:
                if isinstance(e, dict) and e.get("element_type") == "beam" and e.get("element_id"):
                    known.add(norm(e["element_id"]))
    known = {k for k in known if re.fullmatch(r"[A-Z]{1,3}\d{0,2}[A-Z]?", k) and not k.startswith("S")}
    dbg = {"tid": tid, "workroot": wr, "known_ids": sorted(known), "master": bool(master), "pages": []}
    fused = []
    if not wr:
        dbg["error"] = "หา workroot ไม่เจอ"; return fused, dbg
    for pp in plan_pages(wr):
        t0 = time.time()
        page = cv2.imread(os.path.join(B, tid, "img", f"page_{pp['page']:02d}.png"), cv2.IMREAD_GRAYSCALE)
        crop = cv2.imdecode(np.fromfile(pp["crop"], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        off = crop_offset(page, crop) if pp["cropped"] else (0, 0)
        beams = [e for e in pp["cv"] if str(e.get("class", "")).startswith("beam")]
        info = {"page": pp["page"], "stem": pp["stem"], "offset": off, "cv_beams": sum(1 for e in pp["cv"] if str(e.get("class", "")).startswith("beam"))}
        if not beams:
            info["skip"] = "CV ไม่เห็นคาน"; dbg["pages"].append(info); continue
        xs = [e["cx"] + off[0] for e in beams]; ys = [e["cy"] + off[1] for e in beams]
        ws = [e["w"] / 2 for e in beams]; hs = [e["h"] / 2 for e in beams]
        bbox = (min(x - w for x, w in zip(xs, ws)), min(y - h for y, h in zip(ys, hs)),
                max(x + w for x, w in zip(xs, ws)), max(y + h for y, h in zip(ys, hs)))
        bbs = bubbles(page, bbox)
        X, Y, src = grid_from_bubbles(bbs, bbox, master)
        info.update(bubbles=[(b["id"], int(b["x"]), int(b["y"])) for b in bbs], X={k: int(v) for k, v in X.items()},
                    Y={k: int(v) for k, v in Y.items()}, grid_src=src)
        if len(X) < 2 or len(Y) < 2:
            info["skip"] = "หัวกริดไม่พอ"; dbg["pages"].append(info); continue
        letters_on_x = sum(1 for k in X if k[0].isalpha()) > sum(1 for k in X if k[0].isdigit())
        sp = spans_from_cv(pp["cv"], off, X, Y)
        lab = {}
        for s in sp:
            r = label_span(page, s, known)
            s["label"] = r[0] if r else None; s["label_src"] = "ocr" if r else None
        # ช่วงที่ OCR ไม่ได้ป้าย: ยืมชื่อจากคานที่โมเดลตอบในหน้านี้ ที่อยู่เส้นเดียวกันและทับช่วงกัน
        mb = []
        for name, j in F.items():
            if name.startswith(f"page_{pp['page']:02d}_plan_beam") and isinstance(j, dict):
                mb += [e for e in j.get("elements") or [] if isinstance(e, dict) and e.get("element_type") == "beam" and e.get("element_id")]
        order = lambda ids: {k: i for i, (k, _) in enumerate(sorted(ids.items(), key=lambda kv: kv[1]))}
        ox, oy = order(X), order(Y)
        def split_ref(r):
            m = re.fullmatch(r"([A-Z]'*)(\d+'*)", str(r or "").strip().upper())
            return (m.group(1), m.group(2)) if m else None
        for s in sp:
            if s["label"]: continue
            for e in mb:
                a, b = split_ref(e.get("grid_ref_start")), split_ref(e.get("grid_ref_end"))
                if not (a and b): continue
                L_ax, N_ax = (X, Y) if letters_on_x else (Y, X)       # แกนของตัวอักษร / ตัวเลข
                pa = {"x": a[0] if letters_on_x else a[1], "y": a[1] if letters_on_x else a[0]}
                pb = {"x": b[0] if letters_on_x else b[1], "y": b[1] if letters_on_x else b[0]}
                if s["horiz"] and pa["y"] == pb["y"] == s["line"] and pa["x"] in ox and pb["x"] in ox:
                    lo, hi = sorted((ox[pa["x"]], ox[pb["x"]])); sl, sh = sorted((ox.get(s["a"], -9), ox.get(s["b"], -9)))
                elif not s["horiz"] and pa["x"] == pb["x"] == s["line"] and pa["y"] in oy and pb["y"] in oy:
                    lo, hi = sorted((oy[pa["y"]], oy[pb["y"]])); sl, sh = sorted((oy.get(s["a"], -9), oy.get(s["b"], -9)))
                else:
                    continue
                if lo <= sl and sh <= hi and sl >= 0:
                    s["label"], s["label_src"] = norm(e["element_id"]), "model_same_line"; break
        # ช่วงที่ไม่มีป้าย: ยืมป้ายจากช่วงข้างเคียงในกล่อง CV เดียวกัน (คานต่อเนื่อง)
        for s in sp:
            if s["label"]: continue
            sib = [t for t in sp if t["box"] == s["box"] and t["label"] and t["line"] == s["line"]]
            if sib:
                s["label"] = min(sib, key=lambda t: abs((t["pa"] + t["pb"]) - (s["pa"] + s["pb"])))["label"]; s["label_src"] = "same_box"
        for s in sp:
            if not s["label"]: continue
            # ชื่อจุดกริด = ตัวอักษร + ตัวเลข (ธรรมเนียมเดียวกับผลโมเดล/เฉลย เช่น D1)
            def ref(xid, yid):
                return (xid + yid) if letters_on_x else (yid + xid)
            if s["horiz"]: a, b = ref(s["a"], s["line"]), ref(s["b"], s["line"])
            else: a, b = ref(s["line"], s["a"]), ref(s["line"], s["b"])
            fused.append({"element_id": s["label"], "element_type": "beam", "grid_ref_start": a, "grid_ref_end": b,
                          "source": "cv_fusion", "label_src": s["label_src"], "page": pp["page"]})
        info.update(spans=len(sp), labelled=sum(1 for s in sp if s["label"]), seconds=round(time.time() - t0, 1))
        dbg["pages"].append(info)
        print(f"  {tid} หน้า {pp['page']} ({pp['stem']}): CV คาน {info['cv_beams']} · หัวกริด x={list(X)} y={list(Y)} · ช่วง {len(sp)} · มีป้าย {info['labelled']} · {info['seconds']} วิ", flush=True)
    return fused, dbg


if __name__ == "__main__":
    for tid in sys.argv[1:]:
        t = time.time()
        fused, dbg = run_house(tid)
        o = os.path.join(B, "out", tid)
        json.dump(fused, open(os.path.join(o, "fused.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(dbg, open(os.path.join(o, "fused_debug.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print(f"{tid}: ช่วงคานจาก fusion {len(fused)} · {round(time.time() - t, 1)} วิ", flush=True)
