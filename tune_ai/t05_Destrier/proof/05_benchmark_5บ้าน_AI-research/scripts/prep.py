import fitz, json, sys, time
from pathlib import Path
T = Path(r"D:\00mk\steel project\training\Training\image")
OUT = Path(r"D:\Temp\claude\3049db1b73f5b7d5\c641593e-2919-41af-bebc-66157c3c1ea4\scratchpad\bench5")
HOUSES = {"TEST-01": "บ้าน_เล็ก_1ชั้น_03", "TEST-02": "บ้าน_เล็ก_1ชั้น_06", "TEST-03": "บ้าน_เล็ก_2ชั้น_01",
          "TEST-04": "บ้าน_เล็ก_2ชั้น_06", "TEST-05": "บ้าน_ใหญ่_1ชั้น_02"}
for tid, name in HOUSES.items():
    pdf = T / name / f"{name}.pdf"
    d = OUT / tid / "img"; d.mkdir(parents=True, exist_ok=True)
    t0 = time.time(); doc = fitz.open(pdf); pages = []
    for i, pg in enumerate(doc, 1):
        fn = d / f"page_{i:02d}.png"
        if not fn.exists(): pg.get_pixmap(dpi=200).save(fn)
        pages.append({"page": i, "path": f"bench/{tid}/page_{i:02d}.png"})
    (OUT / tid / "job.json").write_text(json.dumps({"payload": {"pages": pages}}, ensure_ascii=False), encoding="utf-8")
    print(tid, name, len(pages), "หน้า", round(time.time() - t0, 1), "วิ", flush=True)
