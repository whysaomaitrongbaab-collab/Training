# Pass 1.5 — ตา CV ตรวจของที่ตัดแล้ว

**ไม่ใช้ AI เลย — ไม่มี prompt** เจตนา: CV มั่วไม่เป็น ใช้เป็นคนตรวจ ไม่ใช่คนอ่านแทน

รันกับ crop ที่ pass 1 ตัดแล้ว เฉพาะ 4 subtask ผังโครงสร้าง (plan_footing/column/beam/slab)
เอา template จริงถูหาทั้งภาพ ได้ 3 อย่างต่อภาพ: บัญชี element เลขกำกับ `#n` คงที่, ภาพมาร์คเลข
(Set-of-Mark), บล็อกข้อความ hint — ของสองอย่างหลังไปใช้ต่อที่ [`pass2.4_hint/`](../pass2.4_hint/)

ของจริงอยู่ที่: [`tools/cv_scan.py`](../../../tools/cv_scan.py) (`--manifest <workroot>`)
เครื่องยนต์ template matching: [`tools/pattern_recognition.py`](../../../tools/pattern_recognition.py)
คลัง template: [`tools/templates/`](../../../tools/templates/)

    python tools/cv_scan.py --manifest <workroot>   # เดิน pass2/{4 ผัง}/images → เขียนลง cv/
