# Pass 3 — ถอดระยะ/เหล็ก จากบัญชี element ที่ยืนยันแล้ว

**สถานะ: โครง prompt — ยังไม่เคยรันจริงกับโมเดลแม้แต่ครั้งเดียว** (เขียน 2026-08-26 ตาม
pass_design_v2.md เฟส E — จะรันได้ต้องผ่านผลทดลองแขน 2 vs 2.4 ก่อน)

**Input:** รูป (มาร์คเลขจาก pass 2.5) + บัญชี element ฉบับสุดท้าย (CV ∪ โมเดล จาก pass 2.5)
+ grid master + prompt นี้ (prepend `../_common.md` — glossary ไทยติดมาด้วย)

**กฎเหล็กของ pass นี้ — บังคับด้วยโค้ด ไม่ใช่แค่ prompt:**
`tools/merge_guard.py::merge_no_delete()` รันหลังโมเดลตอบเสมอ — element ไหนในบัญชีที่
โมเดลไม่ตอบ จะถูกใส่กลับเป็น stub + ธง `dropped_by_pass3` ให้คนดู โมเดลจึง**ลบอะไรไม่ได้จริง**
ต่อให้ prompt ล้มเหลว

---

## PROMPT START

You are given (1) a Thai construction drawing with numbered boxes `#n` marking confirmed
elements, and (2) the confirmed element list below. Your job is to extract dimensions, spans and
rebar for **every** element in the list.

{{ELEMENT_ACCOUNT}}

Rules, in priority order:

1. **Never remove an element from the list.** Every listed element appears in your output with
   its `cv_mark`. If you cannot read anything about it, output it with all measurement fields
   `null` and a `confidence_flags` entry saying what was unreadable — that is a correct answer.
2. You **may add** elements the list missed. An added element has no `cv_mark`.
3. Spans come from the printed grid dimensions via the grid master — never from how long a line
   looks. A span you cannot resolve from printed numbers stays `null` with a warning.
4. All `_common.md` rules apply (element shape, units, rebar objects, honesty rules).

## PROMPT END
