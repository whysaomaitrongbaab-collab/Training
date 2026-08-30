#!/usr/bin/env python3
"""
merge_adapters_soup.py — รวม adapter fold0+fold1 เป็นก้อนเดียวด้วย PEFT model soup
(มะขามสั่ง 2026-08-31: เช่า 4 การ์ดพร้อมกัน fold0+fold1 × Courser+Voldemort คู่ขนาน
แทนรันทีละ fold แล้ว "ต่อยอด" — วิธีนี้คือรวมสองอาดาปเตอร์ที่เทรนจบแล้วให้เป็นตัวเดียว)

ใช้หลังทั้ง fold0/fold1 ของแขนเดียวกันเทรนจบและ push ขึ้น HF แล้วเท่านั้น
(dacarokann/Courser_a + dacarokann/Courser_b, หรือ dacarokann/Voldemort_a + _b)

รัน:
    python3 merge_adapters_soup.py --arm courser
    python3 merge_adapters_soup.py --arm voldemort

⚠️ ยังไม่เคยรันจริง — ต้องรอทั้ง fold0/fold1 ของแขนนั้นเทรนจบก่อน (rule_of_tune ข้อ 4:
dry-run ทาง PEFT เล็กๆ ก่อนถ้าเป็นไปได้ ก่อนเชื่อผล soup เต็ม)
"""
import argparse

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ARMS = {
    "courser": {
        "base": "Qwen/Qwen3.6-35B-A3B",  # ต้องตรงกับ base ที่ train_t05_courser.py ใช้จริง
        "adapters": ["dacarokann/Courser_a", "dacarokann/Courser_b"],
        "out": "dacarokann/Courser_soup",
    },
    "voldemort": {
        "base": "OpenGVLab/InternVL3-78B-hf",
        "adapters": ["dacarokann/Voldemort_a", "dacarokann/Voldemort_b"],
        "out": "dacarokann/Voldemort_soup",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=ARMS.keys())
    ap.add_argument("--combination-type", default="linear",
                     choices=["linear", "ties", "dare_ties", "svd", "cat"])
    ap.add_argument("--push", action="store_true", help="push souped adapter ขึ้น HF (ต้อง export HF_TOKEN)")
    args = ap.parse_args()

    cfg = ARMS[args.arm]
    fold0_id, fold1_id = cfg["adapters"]

    base = AutoModelForCausalLM.from_pretrained(cfg["base"], device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(cfg["base"])

    model = PeftModel.from_pretrained(base, fold0_id, adapter_name="fold0")
    model.load_adapter(fold1_id, adapter_name="fold1")

    model.add_weighted_adapter(
        adapters=["fold0", "fold1"],
        weights=[0.5, 0.5],
        combination_type=args.combination_type,
        adapter_name=f"{args.arm}_soup",
    )
    model.set_adapter(f"{args.arm}_soup")

    if args.push:
        model.push_to_hub(cfg["out"])
        tokenizer.push_to_hub(cfg["out"])
        print(f"pushed → {cfg['out']}")
    else:
        model.save_pretrained(f"./{args.arm}_soup_local")
        print(f"saved locally → ./{args.arm}_soup_local (ใส่ --push เพื่อขึ้น HF)")


if __name__ == "__main__":
    main()
