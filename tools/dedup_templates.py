#!/usr/bin/env python3
"""dedup_templates.py — ไอคอนที่หน้าตาเหมือนกันในกอง candidate/คลัง เก็บตัวแทนตัวเดียว

มะขามสั่ง 2026-08-28: "เอารูปที่เพิ่มขึ้นมาเทียบกับตัวที่อยู่ในประเภทเดียวกัน (เสา1 vs เสา2)
คะแนนเหมือน >0.8 เก็บอันเดียว ทำจำนวน n+(n-1)+..." — คือเทียบ**ทุกคู่จริง** (n(n-1)/2 คู่)
ไม่ใช่แค่เทียบกับตัวข้างเคียง เพื่อลดจำนวนที่ต้องเอาตาคน/Claude มาดู (harvest_templates.py
--review ยังทำมอนทาจให้ดูอยู่ แต่ทำ**หลัง**สคริปต์นี้ตัดตัวซ้ำออกแล้ว จะเหลือน้อยลงมาก)

หลักการเทียบ: resize สองรูปให้ขนาดเท่ากัน (64x64, INTER_AREA) แล้ว normalized
cross-correlation ทั้งภาพ — ตัวเดียวกับที่ pattern_recognition.py ใช้จับตำแหน่งบนหน้าใหญ่
(cv2.matchTemplate TM_CCOEFF_NORMED) ต่างกันแค่ที่นี่เทียบ "สองรูปนี้เหมือนกันแค่ไหน"
ไม่ใช่ "รูปนี้อยู่ตรงไหนในหน้าใหญ่"

จัดกลุ่มแบบ greedy เทียบกับ "ตัวแทน" ที่เก็บไว้แล้วเท่านั้น **ไม่ transitive** — ตั้งใจ
(ลองแบบ union-find ก่อนแล้วพบจริง 2026-08-28: ไฟล์ A~B ที่ 1.000 และ B~C ที่ 0.80 ทำให้ A
ถูกจัดกลุ่มกับ C ทั้งที่ A~C จริงแค่ 0.737 — เจอ 2 crop ตัวหนังสือคนละคำที่ไม่เกี่ยวกันเลย
ถูกจับซ้ำผ่าน "สะพาน" ตัวที่สาม) ทุกไฟล์ที่ถูก drop ต้องเทียบตรงกับตัวแทนที่เก็บไว้ ≥thresh
จริง คะแนนที่รายงานจึงเป็นคะแนนคู่จริงเสมอ ไม่มีการอนุมานผ่านไฟล์อื่น

ไม่ลบไฟล์เด็ดขาด — ค่าเริ่มต้นเป็น dry-run รายงานอย่างเดียว, --apply ค่อยย้ายตัวซ้ำไป
retired_dupes/ ข้างๆ (ย้อนได้เสมอ)

**โหมด --bank มีด่านที่สอง อัตโนมัติ (บทเรียนจริง 2026-08-28):** NCC ที่ใช้คัดกลุ่ม เป็นการ
เทียบตำแหน่งเดียวบนภาพย่อ 64x64 — ไม่ใช่ตัวชี้วัดเดียวกับที่ระบบใช้จริง (sliding-window
หลาย scale บนหน้าเต็ม) เจอจริง: footing คู่หนึ่งเหมือนกัน 0.80-1.00 ตาม NCC แต่ตัดออกจริง
ทำ 3 บ้านหลุดจาก ✅ — ตอนนี้ --bank --apply จะวัด coverage จริงก่อน/หลังทุกครั้ง (เรียก
house_pages()/match_bank ทางเดียวกับ harvest_templates.py) บ้านไหนหลุดจาก ✅ = ยกเลิกทั้ง
kind นั้น คืนไฟล์กลับที่เดิมเอง ไม่ต้องเชื่อ NCC เปล่าๆ (ตัวอย่าง: เสาผ่านฉลุย 7→3 coverage
เท่าเดิม, ฐานรากไม่ผ่านที่ 0.8 ต้องขยับ --thresh หรือคัดมือ) โหมด --staging ไม่มีด่านนี้
เพราะยังไม่ถูก promote เข้าคลัง ไม่กระทบของจริง

ใช้:
    python tools/dedup_templates.py --staging                    # ทุก kind ในกอง staging (dry-run)
    python tools/dedup_templates.py --staging --kind column       # เฉพาะเสา
    python tools/dedup_templates.py --staging --apply             # ย้ายตัวซ้ำจริง
    python tools/dedup_templates.py --bank --kind column          # เช็คคลังจริงที่ promote แล้ว
    python tools/dedup_templates.py --staging --thresh 0.85
"""
import argparse
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from pattern_recognition import imread_thai  # noqa: E402

STAGING = HERE / "templates" / "staging"
BANK = HERE / "templates"
KINDS = ("footing", "column")


def classify_kind(name):
    """เดา kind จากชื่อไฟล์ — คำเดียวพอ ไม่สนคำนำหน้า (repo นี้มีอย่างน้อย 2 รูปแบบชื่อ
    ปนกันในกอง staging: cand_footing__* จากรอบเก่า vs cand_fromFootingPage__* จากตัวปัจจุบัน)"""
    low = name.lower()
    if "footing" in low:
        return "footing"
    if "column" in low:
        return "column"
    return None


def natural_key(p):
    """เรียงบ้าน 2 มาก่อนบ้าน 10 (ไม่ใช่ string sort ที่ให้ '10' มาก่อน '2')"""
    nums = [int(x) for x in re.findall(r"\d+", p.name)]
    return (nums, p.name)


def similarity(a, b, size=64):
    """normalized cross-correlation ของสองภาพ resize เท่ากัน — 1.0 = เหมือนเป๊ะ"""
    A = cv2.resize(a, (size, size), interpolation=cv2.INTER_AREA)
    B = cv2.resize(b, (size, size), interpolation=cv2.INTER_AREA)
    return float(cv2.matchTemplate(A, B, cv2.TM_CCOEFF_NORMED)[0, 0])


def dedup_group(paths, thresh):
    """greedy: เรียงลำดับคงที่ (natural_key) แล้วไล่ทีละไฟล์ — เทียบกับ "ตัวแทน" ที่เก็บไว้
    แล้วทุกตัว (ไม่ใช่ไฟล์ที่ถูก drop ไปแล้ว — กัน chain drift ตามคอมเมนต์หัวไฟล์) เจอตัวแทน
    ที่คะแนน ≥thresh ตัวแรก → drop เข้ากลุ่มนั้นทันที ไม่ตรงใครเลย → ตัวเองกลายเป็นตัวแทนใหม่

    ตัวแทนที่เหลือทั้งหมดจึงรับประกันว่าเทียบกันเองจริงแล้วทุกคู่และ <thresh (ตอนไฟล์ที่มาทีหลัง
    กลายเป็นตัวแทน มันเพิ่งเทียบกับตัวแทนเก่าทุกตัวไม่ผ่านมาหมาดๆ) — คือ n(n-1)/2 คู่จริงถ้านับ
    เฉพาะคู่ (ตัวแทน, ผู้สมัคร) ทุกคู่ที่เคยเกิดขึ้นจริง ไม่ใช่คู่ที่ถูก short-circuit ข้ามไปเพราะ
    เจอคำตอบก่อนแล้ว → คืน (representative -> [ตัวซ้ำที่ถูกดรอป], n_pairs_checked, n_dup_pairs)"""
    ordered = sorted(paths, key=natural_key)
    imgs = {p: imread_thai(p) for p in ordered}
    reps = []
    result = {}
    n_pairs = n_dup = 0
    for p in ordered:
        hit = None
        for rep in reps:
            n_pairs += 1
            if similarity(imgs[rep], imgs[p]) >= thresh:
                n_dup += 1
                hit = rep
                break
        if hit:
            result[hit].append(p)
        else:
            reps.append(p)
            result[p] = []
    return result, n_pairs, n_dup


def bank_ok_houses(kind):
    """เรียก house_pages()+match_bank ทางเดียวกับ harvest_templates.py เป๊ะ — เช็คว่าคลัง
    (ตามสภาพบนดิสก์ ณ ตอนเรียก) ยังจับแต่ละบ้านได้ ≥70% ของ GT ไหม คืน set ชื่อบ้านที่ผ่าน

    ทำไมต้องมีฟังก์ชันนี้ (บทเรียนจริง 2026-08-28): NCC ที่ dedup_group() ใช้เทียบเป็นคู่ๆ
    แบบ single-position บนภาพ 64x64 ไม่ใช่ตัวชี้วัดเดียวกับที่ระบบใช้จริง (sliding-window
    หลาย scale บนหน้าเต็ม) — เจอจริง: tpl_footing13/15/17 เหมือน tpl_footing7/6/16 ที่
    0.80-1.00 ตาม NCC แต่ตัดออกจริงทำให้ 3 บ้าน (04/05/17) หลุดจาก ✅ (16/16→11/16 เป็นต้น)
    ฟังก์ชันนี้จึงเป็นด่านที่สอง ยึดของจริงเป็นหลัก ไม่ใช่เชื่อ NCC เฉยๆ"""
    import harvest_templates as ht
    from pattern_recognition import load_templates, match_bank, FOOTING_THRESH, COLUMN_THRESH
    tpls = load_templates()[kind]
    thresh = FOOTING_THRESH if kind == "footing" else COLUMN_THRESH
    kwargs = {} if kind == "footing" else {"scales": (1.0,)}
    ok = set()
    for house, kinds in ht.house_pages().items():
        if kind not in kinds:
            continue
        page, gt = kinds[kind]
        img = ht.image_of(house, page)
        if img is None or gt <= 0:
            continue
        n = len(match_bank(imread_thai(img), tpls, thresh, **kwargs))
        if n >= gt * 0.7:
            ok.add(house)
    return ok


def collect(root, kind_filter):
    """เก็บไฟล์ candidate ทั้งหมด แยกตาม kind — ข้าม rejected_* (คนตัดสินไปแล้วรอบก่อน)
    และ retired_dupes/ ของตัวเอง (กันดรอปซ้ำถ้ารันสองรอบ)"""
    by_kind = defaultdict(list)
    for p in sorted(root.glob("*.png")):
        if p.name.startswith("rejected_") or "retired_dupes" in str(p):
            continue
        k = classify_kind(p.name)
        if k is None or (kind_filter and k != kind_filter):
            continue
        by_kind[k].append(p)
    return by_kind


def run(root, kind_filter, thresh, apply_, label, bank_mode):
    by_kind = collect(root, kind_filter)
    if not by_kind:
        print(f"[{label}] ไม่มีไฟล์ที่จัด kind ได้ (เช็ค --kind หรือ path)")
        return
    total_before = total_after = 0
    for kind in KINDS:
        paths = by_kind.get(kind)
        if not paths:
            continue
        result, n_pairs, n_dup = dedup_group(paths, thresh)
        kept = len(result)
        dropped_n = sum(len(v) for v in result.values())
        total_before += len(paths)
        total_after += kept
        print(f"\n[{label}/{kind}] {len(paths)} ไฟล์ → เทียบ {n_pairs} คู่ (ทุกไฟล์ vs "
              f"ตัวแทนที่เก็บไว้แล้ว ไม่เทียบผ่านไฟล์อื่น) → {n_dup} คู่คะแนน ≥{thresh} → "
              f"เหลือตัวแทน {kept} (ตัดซ้ำออก {dropped_n})")
        for rep, dropped in sorted(result.items(), key=lambda kv: -len(kv[1])):
            if not dropped:
                continue
            print(f"  เก็บ {rep.name}")
            for d in dropped:
                s = similarity(imread_thai(rep), imread_thai(d))
                print(f"    ซ้ำ {d.name}  (score {s:.3f})")
        if not (apply_ and dropped_n):
            continue
        dropped_paths = [d for group in result.values() for d in group]
        retired = root / "retired_dupes"
        retired.mkdir(exist_ok=True)
        if bank_mode:
            # ด่านที่สอง: ย้ายจริง วัด coverage จริงก่อน/หลัง (ดู bank_ok_houses ว่าทำไม
            # เชื่อ NCC อย่างเดียวไม่พอ) — บ้านไหนหลุดจาก ✅ ถือว่าไม่ปลอดภัย ย้ายกลับหมดทั้ง kind
            ok_before = bank_ok_houses(kind)
            for d in dropped_paths:
                shutil.move(str(d), str(retired / d.name))
            ok_after = bank_ok_houses(kind)
            regressed = ok_before - ok_after
            if regressed:
                for d in dropped_paths:
                    shutil.move(str(retired / d.name), str(d))
                print(f"  ⚠️ ยกเลิก — coverage จริงหลุดที่ {sorted(regressed)} "
                      f"(NCC ว่าเหมือนแต่ระบบจริงจับต่างกัน) คืนไฟล์ทั้ง {dropped_n} กลับที่เดิมแล้ว "
                      f"ลอง --thresh สูงขึ้นถ้าอยากให้กลุ่มนี้ผ่าน")
                total_after += dropped_n  # คืนของแล้ว นับกลับเข้า "หลัง"
            else:
                print(f"  ✅ ย้าย {dropped_n} ไฟล์ไป {retired} — เช็ค coverage จริงแล้ว "
                      f"ไม่มีบ้านไหนหลุดจาก ✅ ({len(ok_before)} บ้านผ่านเท่าเดิม)")
        else:
            for d in dropped_paths:
                shutil.move(str(d), str(retired / d.name))
            print(f"  → ย้าย {dropped_n} ไฟล์ไป {retired}")
    if total_before:
        print(f"\n[{label}] รวม {total_before} → {total_after} "
              f"({'ย้ายจริงแล้ว' if apply_ else 'DRY-RUN — ใส่ --apply เพื่อย้ายจริง'})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--staging", action="store_true", help="เช็คกอง candidate ใน templates/staging/")
    ap.add_argument("--bank", action="store_true", help="เช็คคลังจริงที่ promote แล้ว (tpl_*.png)")
    ap.add_argument("--kind", choices=KINDS, help="เฉพาะ kind เดียว (ไม่ระบุ = ทั้งสอง)")
    ap.add_argument("--thresh", type=float, default=0.8, help="คะแนนเหมือน ≥ นี้ = ซ้ำ (default 0.8)")
    ap.add_argument("--apply", action="store_true", help="ย้ายตัวซ้ำไป retired_dupes/ จริง (ไม่ลบ)")
    a = ap.parse_args()
    if not a.staging and not a.bank:
        ap.print_help()
        sys.exit(1)
    if a.staging:
        run(STAGING, a.kind, a.thresh, a.apply, "staging", bank_mode=False)
    if a.bank:
        run(BANK, a.kind, a.thresh, a.apply, "bank", bank_mode=True)
