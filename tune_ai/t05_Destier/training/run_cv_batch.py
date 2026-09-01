#!/usr/bin/env python3
"""run_cv_batch.py — t05 Courser data-gap ②: รัน cv_scan --pass25 กับหน้าผังโครงสร้าง
ทั้ง 40 หลัง (CPU ล้วน บนเครื่องนี้) เพื่อผลิต _cv25.json/_marked25.png ให้ pass3 dataset

หน้าเป้าหมายดึงจาก train.jsonl+val.jsonl ของ t04 (subtask plan_footing/plan_beam/plan_slab)
— แม่นกว่ากวาดทุก .png ในคลัง (section/notes ไม่ต้องสแกน เปลือง+ได้ sidecar ขยะ)
sidecar เขียนข้างภาพต้นฉบับใน image/<บ้าน>/ ตาม convention ของ pass_io_table

    py run_cv_batch.py            # รันทั้งหมด (ข้ามไฟล์ที่มี _cv25.json แล้ว)
    py run_cv_batch.py --dry      # แค่ลิสต์ว่าจะทำกี่หน้า
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent.parent                      # Training repo root
DATA = TRAINING / "tune_ai" / "t04_Purson" / "data_before_tune"
IMG_ROOT = TRAINING / "image"
CV_SCAN = TRAINING / "tools" / "cv_scan.py"
PLAN_SUBTASKS = {"plan_footing", "plan_beam", "plan_slab"}

# หา house dir จากชื่อไฟล์ภาพ เช่น บ้าน_ใหญ่_1ชั้น_01_หน้า14.png → บ้าน_ใหญ่_1ชั้น_01
def house_of(img_name):
    stem = Path(img_name).stem
    return stem.split("_หน้า")[0]


def collect_targets():
    targets = {}
    for split in ("train.jsonl", "val.jsonl"):
        for line in (DATA / split).open(encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("subtask") not in PLAN_SUBTASKS:
                continue
            for c in r["messages"][0]["content"]:
                if c.get("type") == "image":
                    name = Path(c["image"]).name
                    p = IMG_ROOT / house_of(name) / name
                    if p.exists():
                        targets[str(p)] = r["subtask"]
                    else:
                        print(f"⚠️  ไม่พบภาพต้นฉบับ: {p}", flush=True)
    return targets


def main():
    dry = "--dry" in sys.argv
    targets = collect_targets()
    done = [p for p in targets if Path(p).with_name(Path(p).stem + "_cv25.json").exists()]
    todo = [p for p in targets if p not in set(done)]
    print(f"เป้าหมาย {len(targets)} หน้า | มี _cv25 แล้ว {len(done)} | ต้องรัน {len(todo)}", flush=True)
    if dry:
        return
    t0 = time.time()
    fail = []
    for i, p in enumerate(sorted(todo), 1):
        r = subprocess.run([sys.executable, str(CV_SCAN), p, "--pass25"],
                           capture_output=True, text=True, cwd=str(TRAINING))
        ok = Path(p).with_name(Path(p).stem + "_cv25.json").exists()
        status = "ok" if ok else "FAIL"
        if not ok:
            fail.append(p)
            tail = (r.stderr or r.stdout or "").strip().splitlines()
            status += " | " + (tail[-1][:120] if tail else "no output")
        print(f"[{i}/{len(todo)}] {Path(p).name} {status} ({time.time() - t0:.0f}s)", flush=True)
    print(f"เสร็จ: {len(todo) - len(fail)}/{len(todo)} ok, {len(fail)} fail ใน {(time.time() - t0) / 60:.1f} นาที", flush=True)
    if fail:
        print("รายการ fail (บ้านที่คลัง template จับไม่ติด = เพดานที่รู้อยู่แล้วของ pass2.5):", flush=True)
        for p in fail:
            print("  -", Path(p).name, flush=True)


if __name__ == "__main__":
    main()
