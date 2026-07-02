# 🚀 Quick Start — 5 Minutes to First Annotation

> ⚠️ อ่าน [rule_of_tune.md](rule_of_tune.md) ก่อนเริ่มงานทุกครั้ง — ไม่มีข้อยกเว้น

## Step 0: Prerequisites
```bash
# Install Python dependencies (one time)
pip install pdfplumber pdf2image

# Install Poppler (one time)
# Windows (Chocolatey): choco install poppler
# macOS: brew install poppler
# Linux: sudo apt-get install poppler-utils
```

## Step 1: Get PDFs Ready
Your friend uploads PDF files here:
```
training-data/raw/
├── 1floor-project-001.pdf
├── 1floor-project-002.pdf
└── 2floor-project-001.pdf
```

## Step 2: Rasterize (1 minute)
Open PowerShell in `training-data/` folder:
```powershell
python pdf-processor.py
```

**Output:**
```
📄 Processing: 1floor-project-001.pdf
   Content type: scanned
   Pages: 4
   🖼️  Rasterizing to images...
   ✅ Processing complete. ID: abc12345
   📁 Output: processing/abc12345/
```

Check progress:
```powershell
python pdf-processor.py list
```

## Step 3: Call Qwen (2 minutes)
In same PowerShell:
```powershell
node qwen-processor.js
```

**Output:**
```
🔄 Processing with Qwen: abc12345
   📸 Loaded 4 images
   📤 Payload ready (2100 KB)
   🧠 Calling Qwen...
   💾 Qwen output saved: qwen-output/abc12345-qwen.json
```

Check specific record:
```powershell
node qwen-processor.js abc12345
```

## Step 4: Review & Annotate (2 minutes)
Start local server:
```powershell
# Python built-in server
python -m http.server 8000

# OR VS Code Live Server
# Right-click review.html → "Open with Live Server"
```

**Then open:** `http://localhost:8000/review.html`

**In browser:**
1. Select record from dropdown
2. Review PDF page on left → Qwen extraction JSON on right
3. Correct any errors in JSON
4. Click "💾 Save Annotation"
5. Move downloaded JSON to `annotated/` folder

## Full Example

```powershell
# Terminal 1: Process PDFs
cd C:\Users\taddy\OneDrive\work\Stecon\constistant\Constistant\training-data
python pdf-processor.py
node qwen-processor.js

# Terminal 2: Start web server
cd C:\Users\taddy\OneDrive\work\Stecon\constistant\Constistant\training-data
python -m http.server 8000
```

Then open: `http://localhost:8000/review.html`

## Check Your Work

```powershell
# See all files
dir
dir raw/              # Uploaded PDFs
dir processing/       # Rasterized images + metadata
dir qwen-output/      # Qwen extractions
dir annotated/        # Your corrections

# Check manifest
cat manifest.json
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: pdfplumber` | `pip install pdfplumber pdf2image` |
| `No such file or directory: poppler` | Install Poppler (see Prerequisites) |
| `Cannot find module 'fs'` | Make sure Node.js is installed: `node --version` |
| Images not loading in review.html | Make sure server is running on `http://localhost:8000/` |
| Qwen API error | Check Supabase secrets or set `QWEN_API_KEY` env var |

## Next: Batch Processing

Once pipeline works, process multiple PDFs:

```powershell
# 1. Friend uploads 10 PDFs to raw/
# 2. Run batch
python pdf-processor.py
node qwen-processor.js

# 3. Review all in browser (takes ~30 min for 10)
python -m http.server 8000
# Open review.html, cycle through each record
```

## Tips for High-Quality Annotations

✅ **Do:**
- Review all pages (use Next/Previous buttons)
- Correct element IDs (C1, B1, S1 format)
- Verify dimensions match drawing
- Note confidence levels
- Add review notes about corrections

❌ **Don't:**
- Rush through (accuracy matters for fine-tuning)
- Skip unclear elements (mark as low confidence)
- Trust Qwen 100% (it can misread grid refs, spacing)

## File Organization

```
training-data/
├── raw/                    ← Friend uploads here
│   └── *.pdf               (PDFs you process)
│
├── processing/             ← Auto-generated
│   └── abc12345/           (One folder per PDF)
│       ├── metadata.json   (PDF analysis)
│       ├── page_001.png    (Rasterized images)
│       └── ...
│
├── qwen-output/            ← Auto-generated
│   └── abc12345-qwen.json  (Raw Qwen extraction)
│
├── annotated/              ← YOU add reviewed files here
│   └── abc12345-annotated.json (Your corrected version)
│
└── review.html             (Open this in browser)
```

## Success Checklist

- [ ] Downloaded and installed pdfplumber + Poppler
- [ ] Friend uploaded at least 1 PDF to raw/
- [ ] Ran `python pdf-processor.py` successfully
- [ ] Ran `node qwen-processor.js` successfully
- [ ] Opened `http://localhost:8000/review.html` in browser
- [ ] Reviewed 1 PDF and saved annotation
- [ ] Moved annotated JSON to `annotated/` folder

**Done! 🎉** You now have your first training dataset entry.

---

**Next:** Repeat with more PDFs, then use annotated JSONs to fine-tune Qwen model.

Questions? See README.md or project CLAUDE.md (AI Vision section).
