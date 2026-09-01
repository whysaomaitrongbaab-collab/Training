#!/usr/bin/env python3
"""
merge_adapters_soup.py — รวม adapter ทุก fold เป็นตัวเดียว "destrier" ด้วย PEFT model soup

มะขามสั่ง 2026-08-31: "เทรนจบต้องบันทึกลง hugging face ทุกตัว แล้วเอามารวมกันตามสมการ
k fold และเก็บใน hugging face ตั้งชื่อว่า destrier"

สมการ k-fold soup: adapter รวม = Σ (1/k) × adapter_i   (ถ่วงน้ำหนักเท่ากันทุก fold)
  k=4 → weights = [0.25, 0.25, 0.25, 0.25]
เหตุผลที่เท่ากัน: ทุก fold เห็นข้อมูล 4/5 เท่ากัน แบ่งด้วย stratified split เดียวกัน
ไม่มี fold ไหน "ดีกว่า" โดยโครงสร้าง — ถ่วงน้ำหนักต่างกันต้องมีหลักฐานจาก eval ก่อน

ลำดับที่ต้องทำ (ห้ามข้าม ห้ามสลับ):
  1. ทุก fold เทรนจบ + push ขึ้น HF แล้ว (dacarokann/Courser_a .. _d)
  2. `verify_hf_push.py` ผ่าน ✅ ทุก fold  ← ไฟล์อยู่จริงบน HF ไม่ใช่แค่สคริปต์จบ
  3. รันไฟล์นี้ → dacarokann/destrier
  4. ตรวจ Day of Shame ตาม rule_of_tune (ดู README/ลำดับปิดงานใน t05_workflow.md)
  5. **ถึงจะ destroy การ์ดได้**

⚠️ แขน Voldemort (InternVL3-78B) ตายแล้ว 2026-08-31 — ตกประตู go/no-go เพราะ BNB 4-bit
ทำ InternViT ตาบอด (ดู rule_of_tune Lesson 16) จึงเหลือแขนเดียวคือ Courser 4 fold

รัน:
    python3 merge_adapters_soup.py                 # เซฟลงเครื่อง (ตรวจก่อน)
    python3 merge_adapters_soup.py --push          # อัปขึ้น dacarokann/destrier
    python3 merge_adapters_soup.py --folds 0 1     # รวมเฉพาะบาง fold (ถ้า fold อื่นพัง)
"""
import argparse
import os
import sys

from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

BASE = "unsloth/Qwen3.6-35B-A3B"      # ต้องตรงกับ MODEL ใน train_t05_courser.py
FOLD_REPO = "dacarokann/Courser_{}"   # fold0→a fold1→b fold2→c fold3→d
LETTERS = "abcd"
OUT_REPO = "dacarokann/destrier"      # ✅ ชื่อที่มะขามตั้ง 2026-08-31


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", nargs="+", type=int, default=[0, 1, 2, 3],
                    help="fold ที่จะรวม (default ทั้ง 4)")
    ap.add_argument("--combination-type", default="linear",
                    choices=["linear", "ties", "dare_ties", "svd", "cat"],
                    help="linear = ค่าเฉลี่ยตรง ๆ ตามสมการ k-fold (default)")
    ap.add_argument("--push", action="store_true",
                    help="อัปขึ้น HF (ต้อง export HF_TOKEN ก่อน)")
    ap.add_argument("--out", default=OUT_REPO)
    args = ap.parse_args()

    if args.push and not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")):
        raise SystemExit("⛔ --push ต้องมี HF_TOKEN — export HF_TOKEN=hf_xxxxx ก่อน")

    repos = [FOLD_REPO.format(LETTERS[k]) for k in args.folds]
    names = [f"fold{k}" for k in args.folds]
    w = 1.0 / len(repos)
    weights = [w] * len(repos)
    print(f"รวม {len(repos)} adapter ด้วยสมการ k-fold: นน. {w:.4f} เท่ากันทุกตัว")
    for n, r in zip(names, repos):
        print(f"   {n}: {r}")

    print(f"\nโหลด base {BASE} …", flush=True)
    base = AutoModelForImageTextToText.from_pretrained(BASE, dtype="auto", device_map="auto")
    processor = AutoProcessor.from_pretrained(BASE)

    model = PeftModel.from_pretrained(base, repos[0], adapter_name=names[0])
    for n, r in zip(names[1:], repos[1:]):
        print(f"โหลด adapter {n} …", flush=True)
        model.load_adapter(r, adapter_name=n)

    print("\nรวมเป็น destrier …", flush=True)
    # ชื่อ "default" ไม่ใช่ "destrier": PEFT เซฟ adapter ที่ไม่ชื่อ default ลงโฟลเดอร์ย่อย
    # ตามชื่อมัน → repo จะไม่มีไฟล์ที่ root และ from_pretrained("…/destrier") จะโหลดไม่เจอ
    model.add_weighted_adapter(adapters=names, weights=weights,
                               combination_type=args.combination_type,
                               adapter_name="default")
    model.set_adapter("default")
    for n in names:  # ไม่งั้น push_to_hub อัป adapter ทุก fold ตามไปด้วย (3.78GB ต่อตัว)
        model.delete_adapter(n)

    if args.push:
        model.push_to_hub(args.out)
        processor.push_to_hub(args.out)
        print(f"\n✅ อัปแล้ว → https://huggingface.co/{args.out}")
        print("   ต่อไป: ตรวจ Day of Shame ให้ครบ **ก่อน** destroy การ์ด (rule_of_tune)")
    else:
        model.save_pretrained("./destrier_local")
        print("\n✅ เซฟลงเครื่อง → ./destrier_local  (ใส่ --push เพื่ออัปขึ้น HF)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
