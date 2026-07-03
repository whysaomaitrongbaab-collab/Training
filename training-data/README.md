# Structural Plan Training Data Pipeline

> ⚠️ อ่าน [rule_of_tune.md](rule_of_tune.md) ก่อนเริ่มงานทุกครั้ง — ไม่มีข้อยกเว้น

Workspace for building fine-tuning datasets for Qwen vision model. Process: **PDF Upload → PDF Analysis → Rasterization → Qwen Extraction → Human Review & Annotation → Dataset Ready**

## Folder Structure

```
training-data/
├── raw/                      # 📥 Friend uploads PDF files here
├── processing/               # 🔄 Intermediate: analyzed PDFs + rasterized images
├── qwen-output/              # 🧠 Qwen's JSON extractions (raw)
├── annotated/                # ✅ Human-reviewed & corrected JSON datasets
├── manifest.json             # 📋 Central tracking of all records
├── pdf-processor.py          # 🐍 Step 1: PDF analysis + rasterization
├── qwen-processor.js         # 🤖 Step 2: Call Qwen API
├── review.html               # 👁️ Step 3: Review UI (open in browser)
└── README.md                 # This file
```

## Workflow

### Step 1: Upload PDF Files
Your friend uploads construction plan PDFs to:
```
training-data/raw/
```

File naming convention (optional but recommended):
```
1floor-project-001.pdf
2floor-project-002.pdf
```

### Step 2: Analyze & Rasterize PDFs
Run the Python script to:
1. Detect if PDF has text/vectors or is scanned
2. Rasterize to PNG images (Qwen works with images)
3. Save processing metadata

```bash
cd training-data
python pdf-processor.py
```

**Output:** Creates a subfolder in `processing/` for each PDF:
```
processing/
├── abc12345/
│   ├── metadata.json          # Content analysis + processing info
│   ├── page_001.png           # Rasterized images
│   ├── page_002.png
│   └── ...
```

**Check status:**
```bash
python pdf-processor.py list
```

### Step 3: Call Qwen Vision
Run the Node.js script to send images to Qwen:

```bash
cd training-data
node qwen-processor.js
```

**Output:** Creates Qwen extractions in `qwen-output/`:
```
qwen-output/
├── abc12345-qwen.json        # Raw Qwen extraction (structural elements)
├── def67890-qwen.json
└── ...
```

**Check specific record:**
```bash
node qwen-processor.js abc12345
```

**Check pending records:**
```bash
node qwen-processor.js list
```

### Step 4: Review & Annotate
Open the review UI in a web browser:

```bash
# Start a local server (Python):
cd training-data
python -m http.server 8000

# Or use Live Server (VS Code)
```

Then open: `http://localhost:8000/review.html`

**In the UI:**
1. Select a record from the dropdown
2. View the PDF page on the left → Qwen extraction JSON on the right
3. Correct any errors in the JSON (element IDs, dimensions, rebar specs, etc.)
4. Add review notes (confidence, issues found, corrections made)
5. Click "💾 Save Annotation" to download the corrected JSON
6. Move the file to `annotated/` folder

**Output:** Annotated JSON files in `annotated/`:
```
annotated/
├── abc12345-annotated.json
├── def67890-annotated.json
└── ...
```

### Step 5: Track Progress
The pipeline maintains `manifest.json` which tracks:
- Total PDFs uploaded
- PDFs analyzed
- Qwen extractions complete
- Annotated datasets ready

```bash
cat manifest.json
```

## JSON Structure Reference

### Qwen Output Format
Qwen returns structural elements in this format:

```json
{
  "elements": [
    {
      "id": "C1",
      "type": "column",
      "location": "A-1",
      "dimensions": {
        "width_mm": 400,
        "depth_mm": 400,
        "height_mm": 3500
      },
      "concrete_grade_ksc": 240,
      "rebar_main": {
        "grade": "SD30",
        "diameter_mm": 16,
        "quantity": 4
      },
      "rebar_stirrups": {
        "diameter_mm": 6,
        "spacing_mm": 200
      },
      "notes": "",
      "confidence": 0.95
    }
  ],
  "page_summary": "Ground floor plan with column/beam layout",
  "notes": "Clear structural drawing, all dimensions visible"
}
```

### Annotated Dataset Format
After human review, save in this format:

```json
{
  "record_id": "abc12345",
  "source_file": "1floor-project-001.pdf",
  "annotation_date": "2026-06-27T12:30:00Z",
  "qwen_extraction": { /* corrected Qwen output */ },
  "review_notes": "Corrected C2 stirrup spacing from 250 to 200mm. All other values verified.",
  "status": "annotated"
}
```

## Setup Instructions

### Prerequisites

1. **Python 3.7+**
   - Install PDFPlumber: `pip install pdfplumber pdf2image`
   - Install Poppler (required for pdf2image): 
     - Windows: `pip install python-pptx` or use Chocolatey `choco install poppler`
     - macOS: `brew install poppler`
     - Linux: `sudo apt-get install poppler-utils`

2. **Node.js 14+**
   - Already have this if running Constistant

3. **Qwen API Integration** (in qwen-processor.js)
   - Currently a placeholder. To use real Qwen:
   - Option A: Call via existing Supabase Edge Function (`supabase.functions.invoke('qwen-vision', ...)`)
   - Option B: Call via existing Vercel fallback (`js/ai/qwenVision.js`)
   - Update the `callQwenAPI()` function in `qwen-processor.js`

### Quick Start

```bash
# 1. Upload PDFs
# → Your friend puts PDFs in training-data/raw/

# 2. Process PDFs
cd training-data
python pdf-processor.py

# 3. Call Qwen
node qwen-processor.js

# 4. Review in browser
python -m http.server 8000
# → Open http://localhost:8000/review.html

# 5. Save annotations
# → Download JSON from review.html → move to annotated/
```

## Tips

- **PDF Quality:** Clear structural drawings (text labels, dimension lines) work best
- **Multi-page PDFs:** Each page is analyzed separately → review all pages
- **Rebar Details:** Qwen works best when dimensions and rebar schedules are visible in the same drawing
- **Confidence:** Lower confidence (< 0.85) = review carefully and correct manually
- **Spacing Ambiguity:** When stirrup/mesh spacing is shown as tick marks (not labels), Qwen may miscount
- **Grid References:** Always check that grid references (A-1, B-C/2-3, etc.) are correctly read

## Troubleshooting

### PDFPlumber/pdf2image errors
```bash
# Re-install dependencies
pip install --upgrade pdfplumber pdf2image
```

### Poppler not found
```bash
# Windows with Chocolatey
choco install poppler

# macOS
brew install poppler

# Linux
sudo apt-get install poppler-utils
```

### Qwen API errors
- Check that `QWEN_API_KEY` and `QWEN_API_HOST` are set in Supabase secrets
- Check image sizes (max ~5MB/image, 20MB total payload)
- Review rate limiting (max 10 requests/min via legacy Vercel endpoint)

### JSON parse errors in review.html
- Ensure Qwen response is valid JSON (not HTML error)
- Check browser console for error details

## Next Steps (Fine-tuning)

Once you have 20-50 annotated datasets:
1. Export all `annotated/*.json` files
2. Create a fine-tuning dataset format (Qwen/OpenAI spec)
3. Upload to Qwen fine-tuning portal
4. Run fine-tuning job
5. Test with new model version
6. Iterate

## Contact

Questions? Check:
- Qwen docs: https://dashscope.aliyun.com/
- Supabase Edge Functions: https://supabase.com/docs/guides/functions
- Project CLAUDE.md: See AI Vision section
