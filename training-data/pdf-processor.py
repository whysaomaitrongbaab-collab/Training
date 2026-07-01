#!/usr/bin/env python3
"""
PDF Processor for Training Data
1. Detects if PDF has text or vectors (using pdfplumber)
2. Rasterizes to images if needed (using pdf2image)
3. Outputs processing metadata + images for Qwen analysis
"""

import os
import sys
import json
import pdfplumber
from pdf2image import convert_from_path
from pathlib import Path
from datetime import datetime
import uuid

TRAINING_DATA_DIR = Path(__file__).parent
RAW_DIR = TRAINING_DATA_DIR / "raw"
PROCESSING_DIR = TRAINING_DATA_DIR / "processing"
MANIFEST_FILE = TRAINING_DATA_DIR / "manifest.json"


def analyze_pdf_content(pdf_path):
    """
    Use pdfplumber to analyze PDF:
    - Check if it has extractable text/vectors
    - Count pages
    - Detect content type
    """
    result = {
        "has_text": False,
        "has_vectors": False,
        "page_count": 0,
        "content_type": "unknown",  # "text", "scanned", "vector", "mixed"
        "text_sample": ""
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            result["page_count"] = len(pdf.pages)

            # Analyze first 3 pages
            text_chars = 0
            vector_objects = 0

            for i, page in enumerate(pdf.pages[:3]):
                # Check for extractable text
                text = page.extract_text()
                if text and len(text.strip()) > 20:
                    result["has_text"] = True
                    text_chars += len(text)
                    if i == 0:
                        result["text_sample"] = text[:200]

                # Check for vector objects (lines, rects, etc.)
                lines = page.lines + page.rects
                if len(lines) > 10:
                    result["has_vectors"] = True
                    vector_objects += len(lines)

            # Classify content type
            if result["has_text"] and result["has_vectors"]:
                result["content_type"] = "mixed"
            elif result["has_text"]:
                result["content_type"] = "text"
            elif result["has_vectors"]:
                result["content_type"] = "vector"
            else:
                result["content_type"] = "scanned"  # likely image-based

        return result
    except Exception as e:
        print(f"Error analyzing {pdf_path}: {e}")
        return {**result, "error": str(e)}


def rasterize_pdf(pdf_path, output_dir, dpi=300):
    """
    Convert PDF pages to PNG images (for scanned/image-based PDFs)
    Returns list of image paths
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        images = convert_from_path(pdf_path, dpi=dpi)

        image_paths = []
        for i, image in enumerate(images):
            image_path = output_dir / f"page_{i+1:03d}.png"
            image.save(str(image_path), "PNG")
            image_paths.append(str(image_path))

        return image_paths
    except Exception as e:
        print(f"Error rasterizing {pdf_path}: {e}")
        return []


def process_pdf(pdf_filename):
    """
    Main processing pipeline for a single PDF
    """
    pdf_path = RAW_DIR / pdf_filename

    if not pdf_path.exists():
        return {"error": f"File not found: {pdf_filename}"}

    print(f"\n📄 Processing: {pdf_filename}")

    # 1. Analyze content
    content_analysis = analyze_pdf_content(pdf_path)
    print(f"   Content type: {content_analysis['content_type']}")
    print(f"   Pages: {content_analysis['page_count']}")

    # 2. Create processing record
    record_id = str(uuid.uuid4())[:8]
    record = {
        "id": record_id,
        "source_file": pdf_filename,
        "analysis_date": datetime.now().isoformat(),
        "content_analysis": content_analysis,
        "processing_steps": []
    }

    # 3. Create output directory for this file
    file_processing_dir = PROCESSING_DIR / record_id
    file_processing_dir.mkdir(parents=True, exist_ok=True)

    # 4. If scanned/vector → rasterize; if text → keep as reference
    if content_analysis["content_type"] in ["scanned", "vector", "mixed"]:
        print(f"   🖼️  Rasterizing to images...")
        image_paths = rasterize_pdf(pdf_path, file_processing_dir)
        record["processing_steps"].append({
            "step": "rasterize",
            "status": "completed",
            "image_count": len(image_paths),
            "images": [str(p) for p in image_paths]
        })
        record["ready_for_qwen"] = True
        record["qwen_input_type"] = "images"
    else:
        record["ready_for_qwen"] = True
        record["qwen_input_type"] = "text_extract"

    # 5. Save processing metadata
    metadata_file = file_processing_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"   ✅ Processing complete. ID: {record_id}")
    print(f"   📁 Output: {file_processing_dir}")

    return record


def list_uploaded_pdfs():
    """List all PDFs in raw/ folder"""
    if not RAW_DIR.exists():
        print("❌ No raw/ folder found. Tell your friend to upload PDFs there.")
        return []

    pdfs = list(RAW_DIR.glob("*.pdf"))
    return [p.name for p in pdfs]


def process_batch():
    """Process all unprocessed PDFs in raw/ folder"""
    pdfs = list_uploaded_pdfs()

    if not pdfs:
        print("❌ No PDFs found in training-data/raw/")
        return

    print(f"Found {len(pdfs)} PDFs to process:")
    for pdf in pdfs:
        print(f"  - {pdf}")

    processed = []
    for pdf in pdfs:
        record = process_pdf(pdf)
        processed.append(record)

    # Update manifest
    with open(MANIFEST_FILE, "r") as f:
        manifest = json.load(f)

    manifest["datasets"].extend(processed)
    manifest["stats"]["total_pdfs_uploaded"] = len(pdfs)
    manifest["stats"]["pdfs_analyzed"] = len([r for r in processed if "error" not in r])

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Batch complete. Updated {MANIFEST_FILE}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        pdfs = list_uploaded_pdfs()
        if pdfs:
            print("📂 PDFs in raw/:")
            for pdf in pdfs:
                print(f"   {pdf}")
    else:
        process_batch()
