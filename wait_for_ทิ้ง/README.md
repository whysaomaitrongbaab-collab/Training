# wait_for_ทิ้ง — staging for deletion

Everything in here was moved out of `training-data/` on **2026-08-02** when Makham cancelled the
Label Studio workflow ("ยกเลิก label studio ไม่ต้องเก็บข้อมูลแล้ว"). Nothing here is referenced by
any live workflow anymore — `op1`/`op2` no longer generate Label Studio task files.

| item | was | why here |
|---|---|---|
| `label_studio_stuff/` | task generator + import scripts + project XMLs + all generated task JSONs (10 houses) | the entire Label Studio toolchain |
| `label-studio-mindmap-บ้าน_เล็ก_1ชั้น_01.pdf` | review-flow mindmap | LS documentation |
| `label-studio-config.xml` | Prompt/stage-a LS labeling config | LS config |
| `manifest.json` | LS review-pipeline manifest (stats all zero) | LS pipeline state |
| `review.html` | pre-LS local review UI | superseded review tooling |
| `annotated/` | LS review output (only SAMPLE-annotated.json — no real data) | LS output slot |
| `upload-to-supabase-storage.js` | generated LS task file with public URLs | LS-only script |

Delete the whole folder whenever Makham confirms — everything is recoverable from git history
(moved in the same commit that created this README).

Ground truth now lives solely in `raw_json_ตัวที่ใช้งานจริง/0N<house>/`, gated by `tools/check_format.py`.
