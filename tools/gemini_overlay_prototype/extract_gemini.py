"""Send one construction-drawing page image to Gemini and extract
footing/column elements using the same grid_ref schema already used for
Qwen fine-tuning in this repo. Writes output/<house>_หน้า<page>_gemini.json.
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

EXTRACTION_PROMPT = """You are reading one page of a Thai reinforced-concrete (RC) \
construction drawing set. This page shows a footing/column plan (แปลนฐานราก).

Find every footing (ฐานราก) and every column (เสา) mark on this page. Each mark has:
- element_id: the label printed in the drawing (e.g. "F1" for a footing type, "C1" for \
a column type). Footings and columns are often printed as a combined label at the same \
point (e.g. "F1,C1") — still record them as separate elements, one entry for the footing \
mark and one for the column mark, both pointing at that same grid position.
- element_type: exactly "footing" or "column".
- count: how many points on the page carry this exact mark.
- grid_refs: the list of grid positions where this mark appears, read from the grid \
lines printed on the page (row letter first, then column number — e.g. "C2", never "2C"). \
A grid line not on a named/printed grid still needs a name: append a prime to the \
nearest named grid ("1'", "A'"). Point-type elements (footing/column) always use a flat \
list of individual grid_ref strings, never a "start-end" range.

Return ONLY valid JSON, no explanation, in exactly this shape:

{"elements": [
  {"element_id": "F1", "element_type": "footing", "count": 11, "grid_refs": ["D1", "D2", ...]},
  {"element_id": "C1", "element_type": "column", "count": 12, "grid_refs": ["D1", "D2", ...]}
]}
"""

GENERATION_CONFIG = {
    "temperature": 1,
    "max_output_tokens": 65536,
    "top_p": 0.95,
    "thinking_level": "high",
    "response_format": {"type": "text", "mime_type": "application/json"},
}


def extract(image_path, model="models/gemini-3.1-pro-preview"):
    load_dotenv()  # repo root .env holds GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set (checked process env and .env). Get a key from "
            "https://aistudio.google.com/ and add it to the repo root .env file."
        )
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=model,
        input=[
            {"type": "text", "text": EXTRACTION_PROMPT},
            {"type": "image", "data": Path(image_path), "mime_type": "image/png"},
        ],
        generation_config=GENERATION_CONFIG,
    )

    text_output = ""
    for step in interaction.steps:
        if step.type == "model_output" and step.content:
            for part in step.content:
                if part.type == "text":
                    text_output += part.text

    if not text_output:
        raise RuntimeError("Gemini returned no text output — check interaction.steps for an error step.")
    return json.loads(text_output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--house", required=True, help='e.g. "บ้าน_เล็ก_1ชั้น_01"')
    parser.add_argument("--page", required=True, help='page number, e.g. "19"')
    args = parser.parse_args()

    page_padded = args.page.zfill(2)
    image_path = Path("image") / args.house / f"{args.house}_หน้า{page_padded}.png"
    if not image_path.exists():
        raise FileNotFoundError(f"Page image not found: {image_path}")

    result = extract(image_path)

    output_dir = Path("tools/gemini_overlay_prototype/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.house}_หน้า{page_padded}_gemini.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
