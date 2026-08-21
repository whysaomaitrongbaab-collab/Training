#!/usr/bin/env python3
"""
test_infer_schema.py — canary: lm-format-enforcer เปิดให้ใช้ schema แบบมี properties ได้หรือยัง

พบ 2026-08-21 (probe จริงบน 0.11.3): ทันทีที่ schema ประกาศ `properties` ตัว parser
จะ**ปิด key set** — key นอกรายการพิมพ์ไม่ได้เลย ไม่ว่าจะเขียน `additionalProperties`
เป็น true / {} / {"type":...} / unevaluatedProperties ก็ไม่เคารพทั้งนั้น
ผลคือ rawjson_infer_schema.json (บังคับ views[]/elements[] เป็น object, element ต้องมี
element_id/element_type) ใช้กับไลบรารีนี้ไม่ได้จริง เพราะ field ของ rawjson เปิดกว้าง
(printed_as siblings ฯลฯ ตาม primary_rawjson_schema.md) — enumerate หมดไม่ได้

infer_t02_grammar.py จึงใช้ {"type":"object"} + regex ลบ trailing comma ไปก่อน
schema ตัวเต็มถูกเก็บไว้รอไลบรารีที่รองรับ (outlines / xgrammar) หรือเวอร์ชันใหม่ที่แก้แล้ว

    python test_infer_schema.py
      exit 0 = ยังปิด key set อยู่ (สถานะเดิม ไม่ต้องทำอะไร)
      exit 1 = ไลบรารีรองรับแล้ว! → กลับไป wire rawjson_infer_schema.json เข้า
               infer_t02_grammar.py ได้ (ดูประวัติ git ของไฟล์นั้น มีโค้ดพร้อมอยู่)
"""
from lmformatenforcer import JsonSchemaParser

schema = {"type": "object", "required": ["a"],
          "properties": {"a": {"type": "string"}},
          "additionalProperties": True}
text = '{"a":"x","b":1}'          # "b" ไม่อยู่ใน properties — schema อนุญาต, parser ล่ะ?

p = JsonSchemaParser(schema)
for ch in text:
    if ch not in p.get_allowed_characters():
        print(f"ยังปิด key set อยู่ (reject ที่ {ch!r}) — สถานะเดิม, schema ตัวเต็มยังใช้ไม่ได้")
        raise SystemExit(0)
    p = p.add_character(ch)

print("ไลบรารีเคารพ additionalProperties แล้ว! → เอา rawjson_infer_schema.json กลับมา wire ได้")
raise SystemExit(1)
