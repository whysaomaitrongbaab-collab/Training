#!/usr/bin/env python3
"""pass0_derive.py — t05 Courser data-gap ①: derive pass0 labels จาก GT rawjson ที่มีอยู่
(หน้าที่ derive อัตโนมัติไม่ได้ → เข้าคิว label มือของ Claude + มะขาม spot-check
 ตามที่มะขามเคาะ 2026-08-30)

กติกา derive (ตาม pass0/prompt.md — ไม่เดา ค่าที่ derive ไม่ได้ = เข้าคิว):
- pattern → subtask ตาม lookup ของ prompt; etc_plan/plan แตก view ตามชนิด element จริงใน GT
  (มี beam → plan_beam, มี slab → plan_slab, มี footing → plan_footing — prompt เองบอก
  "one view each if both are drawn")
- where: หน้าเดียว 1 ไฟล์ GT → "full" · หน้าที่มีหลายไฟล์/หลาย view → คิวมือ (ตำแหน่ง crop
  ไม่มีใน GT — เดาไม่ได้)
- also_gridline: true ถ้า element ใดในไฟล์มี grid_refs จริง หรือ pattern เป็น side_profile
  (กติกาใน prompt: elevation ต้อง flag เสมอ) · grid_master → view ตัวเองเป็น gridline
- sheet_code/sheet_name/discipline/doc_page/png: อ่านตรงจาก GT — null ก็ปล่อย null (ห้าม invent)
- building: "สุขา"/ชื่ออาคารรอง ถ้าชื่อไฟล์มี ไม่งั้น "main"

ผลลัพธ์: pass0_labels.jsonl (status: "auto") + pass0_manual_queue.jsonl (status: "manual",
เหตุผลกำกับ) + สถิติท้ายรัน
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent.parent
GT_ROOT = TRAINING / "json_แก้ไขแล้ว"
IMG_ROOT = TRAINING / "image"

# pattern → pass0 subtask ตรงตัว (จาก lookup ใน pass0/prompt.md)
DIRECT = {
    "grid_master": "gridline", "gridline": "gridline",
    "footing_plan": "plan_footing",
    "beam_plan": "plan_beam", "roof_frame_plan": "plan_beam",
    "section": "section", "schedule": "schedule", "notes": "notes",
    "material_list": "material_list",
    "title": "title", "index": "index", "symbol": "symbol", "misc": "misc",
    "site_plan": "site_plan", "side_profile": "side_profile", "roof_plan": "roof_plan",
}
# element_type → plan subtask (สำหรับแตก etc_plan/plan — ตรรกะเดียวกับ builder)
TYPE_TO_PLAN = {
    "beam": "plan_beam", "tie_beam": "plan_beam", "rafter": "plan_beam", "purlin": "plan_beam",
    "slab": "plan_slab", "precast_plank_detail": "plan_slab",
    "footing": "plan_footing", "pile_cap": "plan_footing", "pile": "plan_footing",
    "pedestal": "plan_footing", "column": "plan_column",
}


def elements_of(d):
    els = list(d.get("elements") or [])
    for v in d.get("views") or []:
        if isinstance(v, dict):
            els += list(v.get("elements") or [])
    return [e for e in els if isinstance(e, dict)]


def has_grid_refs(d):
    return any(e.get("grid_refs") or e.get("grid_ref_start") for e in elements_of(d))


def building_of(fname):
    for tag in ("สุขา", "ศาลา", "โรงจอด"):
        if tag in fname:
            return tag
    return "main"


def page_key(fname):
    m = re.search(r"หน้า(\d+[ab]?)", fname)
    return m.group(1) if m else None


def views_for(pat, d, fname):
    """คืน list ของ view dict หรือ None ถ้า derive ไม่ได้ (เข้าคิวมือ)"""
    gl = bool(has_grid_refs(d)) or pat == "side_profile"
    if pat in DIRECT:
        return [{"subtask": DIRECT[pat], "also_gridline": gl}]
    if pat in ("etc_plan", "plan"):
        subs = sorted({TYPE_TO_PLAN[e.get("element_type")] for e in elements_of(d)
                       if e.get("element_type") in TYPE_TO_PLAN})
        if subs:
            return [{"subtask": s, "also_gridline": gl} for s in subs]
        return None  # plan ที่ไม่มี element ชนิดที่รู้จัก — คิวมือ
    return None  # (none)/unknown — คิวมือ


def main():
    pages = defaultdict(list)   # (house, page) → [(fname, d)]
    broken = []
    houses = sorted(p.name for p in GT_ROOT.iterdir()
                    if p.is_dir() and re.match(r"^\d{2}บ้าน", p.name))
    for h in houses:
        for fp in sorted((GT_ROOT / h).glob("*.json")):
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                broken.append(f"{h}/{fp.name}: {e}")
                continue
            pk = page_key(fp.name)
            if pk is None:
                broken.append(f"{h}/{fp.name}: no หน้าNN in name")
                continue
            pages[(h, pk)].append((fp.name, d))

    auto, manual = [], []
    stats = Counter()
    for (h, pk), items in sorted(pages.items()):
        house_dir = re.sub(r"^\d{2}", "", h)
        img = IMG_ROOT / house_dir / f"{house_dir}_หน้า{pk}.png"
        base = {
            "house": h, "page": pk,
            "image": str(img.relative_to(TRAINING)) if img.exists() else None,
        }
        if not img.exists():
            manual.append({**base, "status": "manual", "reason": "image_missing"})
            stats["image_missing"] += 1
            continue
        if len(items) > 1:
            # หลายไฟล์ GT บนหน้าเดียว — where เดาไม่ได้ · เก็บ subtask ที่รู้ไว้ช่วยตอน label มือ
            known = []
            for fn, d in items:
                v = views_for(d.get("pattern"), d, fn)
                known += [x["subtask"] for x in (v or [])]
            manual.append({**base, "status": "manual", "reason": "multi_view_where_unknown",
                           "known_subtasks": sorted(set(known)), "n_views": len(items)})
            stats["manual_multiview"] += 1
            continue
        fn, d = items[0]
        vs = views_for(d.get("pattern"), d, fn)
        if vs is None:
            manual.append({**base, "status": "manual",
                           "reason": f"pattern_underivable:{d.get('pattern')}"})
            stats["manual_pattern"] += 1
            continue
        label = {
            "png": str(d.get("png") if d.get("png") is not None else pk),
            "doc_page": d.get("doc_page"),
            "sheet_code": d.get("sheet_code"),
            "sheet_name": d.get("sheet_name"),
            "discipline": d.get("discipline"),
            "building": building_of(fn),
            "views": [{"subtask": v["subtask"], "where": "full",
                       "also_gridline": v["also_gridline"]} for v in vs],
            "confidence_score": 1.0,   # derive จาก GT ตรง ๆ ไม่ใช่โมเดลทาย
            "warnings": [],
        }
        auto.append({**base, "status": "auto", "gt_file": fn, "label": label})
        stats["auto"] += 1
        stats[f"auto_sub:{vs[0]['subtask']}" if len(vs) == 1 else "auto_multi_subtask_1view"] += 1

    (HERE / "pass0_labels.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in auto), encoding="utf-8")
    (HERE / "pass0_manual_queue.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in manual), encoding="utf-8")

    print(f"บ้าน {len(houses)} | หน้า GT {len(pages)} | broken {len(broken)}")
    print(f"AUTO derive ได้: {stats['auto']} หน้า → pass0_labels.jsonl")
    print(f"คิว label มือ: {len(manual)} หน้า → pass0_manual_queue.jsonl "
          f"(multi-view {stats['manual_multiview']} / pattern derive ไม่ได้ {stats['manual_pattern']} "
          f"/ ภาพหาย {stats['image_missing']})")
    top = {k.replace('auto_sub:', ''): v for k, v in stats.items() if k.startswith('auto_sub:')}
    print("auto ราย subtask:", dict(sorted(top.items(), key=lambda x: -x[1])))
    if broken:
        print("broken files:")
        for b in broken[:10]:
            print("  -", b)


if __name__ == "__main__":
    main()
