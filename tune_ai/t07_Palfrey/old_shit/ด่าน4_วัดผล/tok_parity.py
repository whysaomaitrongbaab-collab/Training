#!/usr/bin/env python3
"""tok_parity.py — Lesson 20: tokenizer ของโมเดล merged ต้องตัดคำไทยได้ id เท่ากับ tokenizer.json ของ base ทุกตัว

⚠️ UNTESTED บนการ์ด (ร่าง 11 พ.ย. 69) — ลองบน PC แล้ว (transformers 5.15.1): ผ่านกับ destrier_fixed และ **จับได้**
   เมื่อโหลดผ่าน class Qwen2Tokenizer (Thai 14 → 18 token) = บั๊กคลาสเดียวกับ destrier-merged 8 พ.ย.

    # รอบ 1 ใน /venv/main (transformers 5.5.0 = ชุดเดียวกับตอนเทรน) — เขียน id อ้างอิงไว้
    python tok_parity.py --base <base snapshot> --merged <merged> --ids-out /workspace/ft/logs/thai_ids.json
    # รอบ 2 ใน /workspace/venv_vllm (transformers 5.18.0 = ตัวที่เสิร์ฟจริง) — เทียบกับรอบ 1
    python tok_parity.py --base <base snapshot> --merged <merged> --ids-ref /workspace/ft/logs/thai_ids.json

ความจริงที่ใช้เทียบ = tokenizers อ่าน tokenizer.json ของ base ตรงๆ (ตอนเทรน tokenizer.json ที่เซฟออกมามี
pre_tokenizer เหมือน base ทุกตัว ต่างแค่ padding/truncation) · ไม่ผ่าน (exit 1) เมื่อ:
  1. tokenizers อ่าน tokenizer.json ของ merged ได้ id ไม่เท่า base
  2. transformers.AutoTokenizer โหลด merged (ทางที่ vLLM ใช้) ได้ id ไม่เท่า base — ข้อนี้จับ class ที่สร้าง
     pre_tokenizer ใหม่เองโดยไม่สนไฟล์ (เช่น Qwen2Tokenizer ใน transformers รุ่นใหม่ ตัดสระ/วรรณยุกต์ไทยผิด)
  3. --ids-ref: id ไม่เท่ากับไฟล์อ้างอิงจากรอบ 1
รายงานอย่างเดียว: sha256 ทั้งคู่ · คีย์บนสุดของ tokenizer.json ที่ต่างกัน · tokenizer_class — การตัดสินเรื่อง sha อยู่ใน
vllm_build_t07.sh (ต้องเท่ากับ sha ของ base ใน proof/06)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

TEXTS = [
    "แปลนฐานรากและเสาตอม่อ ชั้นที่ ๑",
    "คานคอดิน ค1 ขนาด 0.20x0.40 ม. เหล็กเสริม 4-DB16 ปลอก RB9 @0.15 ม.",
    "เสาเข็มเจาะ เส้นผ่าศูนย์กลาง ๓๕ ซม. ลึก ๒๑ เมตร รับน้ำหนักปลอดภัย ๓๐ ตัน/ต้น",
    "หมายเหตุ: คอนกรีตกำลังอัดประลัยไม่น้อยกว่า 240 กก./ตร.ซม. (ทรงกระบอก) ระยะหุ้ม ๒.๕ ซม.",
    '{"sheet_name": "แปลนคาน ชั้นสอง", "warnings": ["ภาพเบลอ อ่านไม่ชัด"]}',
    "อ่านแบบนี้ตอบเป็น JSON",
    'Plan view, beam B1 200x400 DB16 @0.15 m {"x_lines": []}',
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tok_class(d):
    f = Path(d) / "tokenizer_config.json"
    return json.loads(f.read_text(encoding="utf-8")).get("tokenizer_class") if f.exists() else "<ไม่มีไฟล์>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="โฟลเดอร์ base (HF snapshot ที่มี tokenizer.json)")
    ap.add_argument("--merged", required=True)
    ap.add_argument("--ids-out", help="เขียน id อ้างอิง (base อ่านตรง) ลงไฟล์ — รันใน /venv/main")
    ap.add_argument("--ids-ref", help="เทียบกับไฟล์จาก --ids-out — รันใน venv ของ vLLM")
    a = ap.parse_args()
    tb, tm = Path(a.base) / "tokenizer.json", Path(a.merged) / "tokenizer.json"
    print(f"sha256 tokenizer.json · base {sha(tb)} · merged {sha(tm)}")
    jb, jm = (json.loads(p.read_text(encoding="utf-8")) for p in (tb, tm))
    print(f"คีย์บนสุดที่ต่างกัน: {sorted(k for k in set(jb) | set(jm) if jb.get(k) != jm.get(k)) or 'ไม่มี'}")
    print(f"tokenizer_class (รายงานอย่างเดียว) · base {tok_class(a.base)} · merged {tok_class(a.merged)}")

    from tokenizers import Tokenizer
    rb, rm = Tokenizer.from_file(str(tb)), Tokenizer.from_file(str(tm))
    ref = {s: rb.encode(s, add_special_tokens=False).ids for s in TEXTS}
    got = {"tokenizers(merged)": {s: rm.encode(s, add_special_tokens=False).ids for s in TEXTS}}
    bad = []
    try:
        from transformers import AutoTokenizer
        at = AutoTokenizer.from_pretrained(a.merged)
        print(f"AutoTokenizer(merged) = {type(at).__name__}")
        got["AutoTokenizer(merged)"] = {s: at.encode(s, add_special_tokens=False) for s in TEXTS}
    except Exception as e:      # โหลดไม่ได้ = ตรวจทางที่ตัวเสิร์ฟใช้ไม่ได้ = ไม่ผ่าน ไม่ใช่ข้าม
        bad.append(f"AutoTokenizer โหลด merged ไม่ได้ ({type(e).__name__}: {e})")
    if a.ids_ref:
        old = json.loads(Path(a.ids_ref).read_text(encoding="utf-8"))
        got["tokenizers(base) ในชุดนี้ vs --ids-ref"] = ref
        ref = {s: old[s] for s in TEXTS}
    for name, ids in got.items():
        for s in TEXTS:
            if ids[s] != ref[s]:
                bad.append(f"{name}: {s[:20]}…")
                print(f"   ⛔ {name} ต่าง ({len(ref[s])} → {len(ids[s])} token): {s}")
    if a.ids_out:
        Path(a.ids_out).write_text(json.dumps(ref, ensure_ascii=False), encoding="utf-8")
        print(f"เขียน id อ้างอิง → {a.ids_out}")
    print(f"ข้อความทดสอบ {len(TEXTS)} ข้อ (ไทย {len(TEXTS) - 1} · อังกฤษ/JSON 1) · เทียบ {', '.join(got)}")
    if bad:
        print("⛔ tokenizer ไม่เหมือน base:", "; ".join(bad))
        return 1
    print("✅ tokenizer ตัดคำเหมือน base ทุก id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
