# 📥 Raw PDF Upload Folder

Your friend uploads construction plan PDFs here for processing.

## How to use

1. Place PDF files in this folder
2. Run: `python ../pdf-processor.py`
3. Pipeline will analyze and rasterize them

## File naming (recommended)

```
1floor-project-001.pdf
1floor-project-002.pdf
2floor-project-001.pdf
```

## Note

PDF files are ignored by Git (large files). Only the `.gitkeep` file is tracked to ensure this folder appears on GitHub.

When you commit, only the `.gitkeep` needs to be in git. Your friend can upload PDFs directly or via GitHub Issues/Pull Request descriptions.
