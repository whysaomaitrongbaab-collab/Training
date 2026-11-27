#!/usr/bin/env python3
"""pass_table_xlsx.py - เอกสาร/pass_ทำอะไร.csv -> เอกสาร/pass_ทำอะไร.xlsx (dark background, CSV cannot hold colours)

    python tools/pass_table_xlsx.py <baseline.csv>

Needs openpyxl (not in the global Python on purpose: use a venv). The CSV stays the source; rerun after every edit.
Yellow text = cells added or changed against <baseline.csv> (same pass numbering, compared by row label + column
header so inserted rows/columns do not shift the comparison). Gray text = reasons (row 'แก้อะไร / ทำไม' and the
'หมายเหตุ' column), per the sheet's own legend. A second sheet lists old -> new pass numbers (renumbered 2026-11-18).
"""
import csv
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

DOC = Path(__file__).resolve().parents[1] / "เอกสาร"
SRC = DOC / "pass_ทำอะไร.csv"
OUT = DOC / "pass_ทำอะไร.xlsx"
OLD_TO_NEW = [("1", "1"), ("2", "2"), ("3", "3"), ("3.5", "4"), ("4", "5"), ("4b", "6"), ("5", "7"), ("5.5", "8"),
              ("5.6", "9"), ("6", "10"), ("7", "11"), ("8", "12"), ("9", "13"), ("10", "14")]

BG, HEAD = PatternFill("solid", fgColor="1E1E1E"), PatternFill("solid", fgColor="2D2D30")
WHITE, YELLOW, GRAY = "E6E6E6", "FFD54F", "9E9E9E"
_S = Side(style="thin", color="3C3C3C")
BORDER = Border(left=_S, right=_S, top=_S, bottom=_S)


def read(p):
    return list(csv.reader(open(p, encoding="utf-8-sig", newline="")))


def header_of(h):
    return (h.replace("pass", "") if h.startswith("pass") else h) or "หมายเหตุ"


def keyed(table):
    out, hdr = {}, table[0]
    for r in table:
        if not r or not r[0]:
            continue
        if r[0] == "input of pattern":
            hdr = r
        for j, v in enumerate(r[1:], 1):
            out[(r[0], header_of(hdr[j] if j < len(hdr) else str(j)))] = v
    return out


def style(c, head, color):
    c.fill = HEAD if head else BG
    c.border = BORDER
    c.alignment = Alignment(wrap_text=True, vertical="top")
    c.font = Font(name="Leelawadee UI", size=10, bold=head, color=color)


def main(baseline):
    rows, old = read(SRC), keyed(read(baseline))
    old_labels = {k[0] for k in old}
    wb = Workbook()
    ws = wb.active
    ws.title = "pass"
    ws.sheet_view.showGridLines = False
    hdr = rows[0]
    for i, r in enumerate(rows, 1):
        if r and r[0] == "input of pattern":
            hdr = r
        head = i == 1 or bool(r and r[0] == "input of pattern")
        for j, v in enumerate(r, 1):
            c = ws.cell(row=i, column=j, value=v if v != "" else None)
            h = header_of(hdr[j - 1] if j - 1 < len(hdr) else str(j - 1))
            label = r[0] if r else ""
            changed = bool(label) and j > 1 and v != "" and old.get((label, h), "") != v
            new_row = bool(label) and label not in old_labels and v != ""
            reason = label == "แก้อะไร / ทำไม" or h == "หมายเหตุ"
            style(c, head or j == 1, YELLOW if (changed or new_row) else GRAY if reason else WHITE)
    for i in range(1, len(rows) + 15):                  # keep the margin around the table dark too
        for j in range(1, len(rows[0]) + 4):
            c = ws.cell(row=i, column=j)
            if c.value is None and c.fill.fgColor.rgb in (None, "00000000"):
                c.fill = BG
    ws.column_dimensions["A"].width = 18
    for j in range(2, len(rows[0]) + 1):
        ws.column_dimensions[ws.cell(row=1, column=j).column_letter].width = 30
    ws.column_dimensions[ws.cell(row=1, column=len(rows[0])).column_letter].width = 55
    ws.freeze_panes = "B2"

    m = wb.create_sheet("เลขเดิม→ใหม่")
    m.sheet_view.showGridLines = False
    m.append(["เลขใหม่ (18 พ.ย. 69)", "เลขเดิม", "งาน (จากแถว 'งาน')"])
    work = {header_of(h): rows[1][j] for j, h in enumerate(rows[0]) if j}
    for o, n in OLD_TO_NEW:
        m.append([n, o, work.get(n, "")[:120]])
    for i, r in enumerate(m.iter_rows(), 1):
        for c in r:
            style(c, i == 1, YELLOW if (i > 1 and c.column == 2 and c.value in ("3.5", "4b", "5.5", "5.6")) else WHITE)
    m.column_dimensions["A"].width, m.column_dimensions["B"].width, m.column_dimensions["C"].width = 20, 12, 110
    wb.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main(sys.argv[1])
