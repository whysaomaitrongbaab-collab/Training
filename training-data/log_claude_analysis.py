#!/usr/bin/env python3
"""
Log when Claude manually analyzes a plan image/JSON

Usage:
  python log_claude_analysis.py raw/image/บ้าน_เล็ก/qwen-output/บ้าน_เล็ก_หน้า01.json --model claude-sonnet-5
  python log_claude_analysis.py raw/image/บ้าน_เล็ก_1ชั้น_01/qwen-output/บ้าน_เล็ก_1ชั้น_01_หน้า19.json --model claude-sonnet-5 --note "เฉพาะ element F1,C1"

After Claude analyzes something, run this to record it in pipeline_activity_log.json
"""
import sys, pathlib, argparse
from log_utils import log_action

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file', help='Path to JSON file analyzed (e.g. raw/image/.../qwen-output/...json)')
    ap.add_argument('--model', required=True, help='Claude model used (e.g. claude-sonnet-5)')
    ap.add_argument('--note', default='', help='Optional notes about what Claude did')
    args = ap.parse_args()

    file_path = pathlib.Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    # Extract house name from path (e.g. raw/image/บ้าน_เล็ก_1ชั้น_01/... → บ้าน_เล็ก_1ชั้น_01)
    try:
        house = file_path.parts[2] if len(file_path.parts) > 2 else None
    except:
        house = None

    entry = log_action(
        file=str(file_path),
        ai_model=args.model,
        action='claude_manual_analysis',
        house=house,
        note=args.note if args.note else None
    )

    print(f"✅ Logged to pipeline_activity_log.json")
    print(f"   File: {entry['file']}")
    print(f"   Model: {entry['ai_model']}")
    if entry.get('note'):
        print(f"   Note: {entry['note']}")

if __name__ == '__main__':
    main()
