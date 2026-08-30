#!/usr/bin/env python3
"""measure_capacity.py — วัดว่า MAX_PIXELS / MAX_LENGTH ปัจจุบัน "คับ" จริงแค่ไหน

มะขามสั่ง 2026-08-25 (ข้อ 3 จากประชุมอาจารย์): "อยากเพิ่ม max token"
ก่อนเพิ่มต้องรู้ก่อนว่า (ก) ตอนนี้ถูกย่อไปเท่าไหร่ (ข) เพิ่มแล้ว seq ยาวเท่าไหร่
เพราะรอบ t03 เพิ่มค่าแล้ว OOM จริง เสียเวลา 40 นาที (ดู train_t03.py บรรทัด optim/eval)

**อ่านอย่างเดียว ไม่แก้อะไรทั้งสิ้น** — ไม่โหลดโมเดล ไม่ใช้ GPU รันบนโน้ตบุ๊กได้

    python measure_capacity.py                 # วัด train.jsonl
    python measure_capacity.py --split val
    python measure_capacity.py --pixels 5120 7680 10240   # เทียบหลายค่า

เลขที่ใช้คำนวณ (จาก processor_config.json ของ t03 — ไม่ได้เดา):
    patch_size=16, merge_size=2  →  1 visual token = 16*2 x 16*2 = 1024 พิกเซล
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
MEDIA_ROOT = HERE
PX_PER_TOKEN = 32 * 32          # patch_size 16 x merge_size 2 กำลังสอง
CHARS_PER_TOKEN = 2.2           # ประมาณการข้อความไทย+JSON (ค่าเดียวกับ _est() ใน train_t03.py)
CURRENT_MAX_PIXELS_TOKENS = 5120
CURRENT_MAX_LENGTH = 32768


def visual_tokens(w, h, cap_tokens):
    """จำนวน visual token ของภาพ 1 ใบ หลังโดน cap (Qwen ย่อภาพให้พอดี cap โดยรักษาสัดส่วน)"""
    raw = (w * h) / PX_PER_TOKEN
    return min(raw, cap_tokens), raw


def load(split):
    rows = []
    with open(HERE / f"{split}.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def measure(rows, cap_tokens):
    """คืน (รายตัวอย่าง, สถิติภาพ) — ทุกตัวเลขคำนวณจากไฟล์ภาพจริง ไม่ได้ประมาณ"""
    per_example, shrunk, tokens_lost = [], 0, 0.0
    n_images = 0
    for r in rows:
        vis = 0.0
        for c in r["messages"][0]["content"]:
            if c["type"] != "image":
                continue
            n_images += 1
            w, h = Image.open(MEDIA_ROOT / c["image"]).size
            capped, raw = visual_tokens(w, h, cap_tokens)
            vis += capped
            if raw > cap_tokens:
                shrunk += 1
                tokens_lost += raw - cap_tokens
        txt = sum(len(c["text"]) for c in r["messages"][0]["content"] if c["type"] == "text")
        a = r["messages"][1]["content"]
        gt = "".join(x.get("text", "") for x in a) if isinstance(a, list) else a
        seq = vis + (txt + len(gt)) / CHARS_PER_TOKEN
        per_example.append((seq, r.get("subtask", "?"), vis))
    return per_example, n_images, shrunk, tokens_lost


def report(split, caps):
    rows = load(split)
    print(f"\n{'='*74}\nชุด {split}: {len(rows)} ตัวอย่าง\n{'='*74}")

    for cap in caps:
        per_ex, n_img, shrunk, lost = measure(rows, cap)
        seqs = sorted((s for s, _, _ in per_ex), reverse=True)
        over = [s for s in seqs if s >= CURRENT_MAX_LENGTH]
        tag = " ← ค่าปัจจุบัน" if cap == CURRENT_MAX_PIXELS_TOKENS else ""
        print(f"\n--- MAX_PIXELS = {cap:,} visual token/ภาพ{tag} ---")
        print(f"  ภาพที่โดนย่อ         : {shrunk:,}/{n_img:,} ใบ ({shrunk/n_img*100:.1f}%)"
              f"  — เสียรายละเอียดรวม {lost:,.0f} token")
        print(f"  seq ยาวสุด           : {seqs[0]:,.0f} token")
        print(f"  seq อันดับ 2-3        : {seqs[1]:,.0f} / {seqs[2]:,.0f}")
        print(f"  ตัวอย่างที่ทะลุ {CURRENT_MAX_LENGTH:,} : {len(over)} ตัว"
              + ("  ⚠️ label จะโดนตัดกลาง JSON" if over else "  ✅ ไม่มี"))
        need = int(seqs[0] * 1.05 / 1024 + 1) * 1024      # เผื่อ 5% แล้วปัดขึ้นหลักพัน
        print(f"  → MAX_LENGTH ที่ต้องใช้: {need:,}")

    # ภาพใหญ่สุดในชุด — ตัวที่กำหนดเพดานบน
    biggest = Counter()
    for r in rows:
        for c in r["messages"][0]["content"]:
            if c["type"] == "image":
                w, h = Image.open(MEDIA_ROOT / c["image"]).size
                biggest[(w, h)] += 1
    print("\n  ขนาดภาพในชุดนี้ (5 อันดับ):")
    for (w, h), n in biggest.most_common(5):
        raw = (w * h) / PX_PER_TOKEN
        mark = "  ← โดนย่อที่ค่าปัจจุบัน" if raw > CURRENT_MAX_PIXELS_TOKENS else ""
        print(f"    {w}x{h}  = {raw:>7,.0f} token เต็ม  ({n} ใบ){mark}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="train")  # เช่น train / val / train_fold0 / val_fold1
    ap.add_argument("--pixels", type=int, nargs="+",
                    default=[5120, 7680, 10240, 16384],
                    help="ค่า MAX_PIXELS (หน่วย visual token/ภาพ) ที่อยากเทียบ")
    # t05 เก็บ jsonl คนละที่กับรูป (path ในไฟล์เทียบรากรีโป) — เดิมสคริปต์นี้สมมติว่าอยู่ที่เดียวกัน
    ap.add_argument("--data-dir", default=None, help="โฟลเดอร์ที่มี <split>.jsonl (default: ข้างสคริปต์)")
    ap.add_argument("--media-root", default=None, help="รากที่ path รูปในไฟล์อ้างถึง (default: --data-dir)")
    a = ap.parse_args()
    if a.data_dir:
        HERE = Path(a.data_dir).resolve()
    MEDIA_ROOT = Path(a.media_root).resolve() if a.media_root else HERE
    report(a.split, a.pixels)
    print("\nหมายเหตุ: ตัวเลข seq เป็นการประมาณ (ข้อความหาร 2.2) — ตัวจริงต้องวัดด้วย")
    print("collator บน GPU แต่ส่วน visual token คำนวณตรงจากขนาดไฟล์ภาพ = แม่นยำ")
