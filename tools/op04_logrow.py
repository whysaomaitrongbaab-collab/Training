#!/usr/bin/env python3
"""tools/op04_logrow.py — ใส่แถว op04 ใหม่ลง No_touch_box/docs/raw_json_data_log.md (แถวใหม่อยู่บนสุด)

    python tools/op04_logrow.py <โฟลเดอร์บ้าน> <จำนวนไฟล์ข้อมูล> "<หมายเหตุ>" [--date 2026-10-22] [--orderer "..."] [--ai "..."]

เหตุผล: สคริปต์เดิมอยู่ใน scratchpad ของ session แล้วหายตอน session ถัดไป · ไม่ยิงเน็ต ไม่แตะไฟล์อื่น
ปฏิเสธถ้าโฟลเดอร์นี้มีแถวอยู่แล้ว (ใช้ Python แก้แถวเดิมแทน) เพราะ "แถวซ้ำ" ทำให้ขนาดชุดข้อมูลดูใหญ่เกินจริง
"""
import argparse
import sys
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / 'No_touch_box' / 'docs' / 'raw_json_data_log.md'
HEADER_SEP = '|---|---|---|---|---|\n'

ap = argparse.ArgumentParser()
ap.add_argument('folder')
ap.add_argument('nfiles')
ap.add_argument('note')
ap.add_argument('--date', default='2026-10-22')
ap.add_argument('--ai', default='Claude (Opus 5.5, Claude Code) — subagent สกัดจากภาพจริงทุกหน้าโครงสร้างเอง ซูมครอปจากภาพต้นฉบับ')
ap.add_argument('--orderer', default='มะขาม (สั่ง `ลงมือซะ` + `หาไปเรื่อย ๆ จน session หมดเลยนะ att1235`)')
a = ap.parse_args()

row = (f"| {a.date} | `rawjson_ยังไม่ได้แก้ไขโดนคน/{a.folder}/*.json` (ใหม่ทั้งหมด — **{a.nfiles} ไฟล์ + `_scope.json`, `op04 / pass2-only`**) "
       f"| {a.ai} | {a.orderer} | {a.note} |\n")
t = LOG.read_text(encoding='utf-8')
if a.folder in t:
    sys.exit(f'refused: {a.folder} already has a row in the log — edit that row instead')
i = t.index(HEADER_SEP) + len(HEADER_SEP)
LOG.write_text(t[:i] + row + t[i:], encoding='utf-8')
print('logged', a.folder)
