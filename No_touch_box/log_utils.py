"""
Activity log อัตโนมัติสำหรับทุกครั้งที่ script เขียนไฟล์ JSON ผลลัพธ์ลง raw/image/
บันทึกลงไฟล์เดียว pipeline_activity_log.json (ใหม่สุดอยู่บนสุด — เรียงจาก newest → oldest)

ใช้: from log_utils import log_action
     log_action(file=out_path, ai_model=MODEL_STRUCT, action='extract', house=house)

Username: ตั้งค่า env var TRAINING_USER เพื่อ override ชื่อที่บันทึก (ไม่งั้นใช้ OS login name)
"""
import json, os, getpass, datetime, pathlib

LOG_PATH = pathlib.Path(__file__).resolve().parent / 'pipeline_activity_log.json'


def _current_username():
    return os.environ.get('TRAINING_USER') or getpass.getuser()


def log_action(file, ai_model, action, house=None, **extra):
    entry = {
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        "username": _current_username(),
        "ai_model": ai_model,
        "action": action,
        "file": str(file),
    }
    if house:
        entry["house"] = house
    entry.update(extra)

    logs = []
    if LOG_PATH.exists():
        try:
            logs = json.loads(LOG_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            logs = []
    logs.insert(0, entry)
    LOG_PATH.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding='utf-8')
    return entry
