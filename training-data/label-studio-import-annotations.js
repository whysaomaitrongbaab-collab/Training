/**
 * Convert a Label Studio JSON export back into annotated/<record>-annotated.json
 * (matches the format in annotated/SAMPLE-annotated.json) and updates manifest.json.
 *
 * Usage:
 *   node label-studio-import-annotations.js <path-to-label-studio-export.json>
 */

const fs = require('fs');
const path = require('path');

const TRAINING_DATA_DIR = __dirname;
const ANNOTATED_DIR = path.join(TRAINING_DATA_DIR, 'annotated');
const MANIFEST_FILE = path.join(TRAINING_DATA_DIR, 'manifest.json');

function extractCorrectedJson(task) {
  const annotation = task.annotations && task.annotations[0];
  if (!annotation) return null;

  const result = annotation.result.find((r) => r.from_name === 'corrected_json');
  if (!result) return null;

  const text = result.value.text[0];
  try {
    return JSON.parse(text);
  } catch (e) {
    console.warn(`⚠️  ${task.data.record_id}: corrected_json is not valid JSON (${e.message})`);
    return null;
  }
}

function main() {
  const exportFile = process.argv[2];
  if (!exportFile) {
    console.error('Usage: node label-studio-import-annotations.js <export.json>');
    process.exit(1);
  }

  const tasks = JSON.parse(fs.readFileSync(exportFile, 'utf-8'));
  if (!fs.existsSync(ANNOTATED_DIR)) fs.mkdirSync(ANNOTATED_DIR, { recursive: true });

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8'));
  let written = 0;

  for (const task of tasks) {
    const recordId = task.data.record_id;
    const qwenExtraction = extractCorrectedJson(task);
    if (!qwenExtraction) continue;

    const annotated = {
      record_id: recordId,
      source_file: `${recordId}.pdf`,
      annotation_date: new Date().toISOString(),
      review_status: 'approved',
      qwen_extraction: qwenExtraction,
      review_notes: {},
      metadata: {
        extraction_method: 'qwen-vl-max',
        dataset_version: 'v1',
      },
    };

    const outFile = path.join(ANNOTATED_DIR, `${recordId}-annotated.json`);
    fs.writeFileSync(outFile, JSON.stringify(annotated, null, 2), 'utf-8');
    console.log(`💾 ${outFile}`);
    written += 1;

    let entry = manifest.datasets.find((d) => d.id === recordId);
    if (!entry) {
      entry = { id: recordId };
      manifest.datasets.push(entry);
    }
    entry.annotated_output = outFile;
    entry.annotation_date = annotated.annotation_date;
    entry.status = 'annotated';
  }

  manifest.stats.annotated_datasets = manifest.datasets.filter((d) => d.status === 'annotated').length;
  fs.writeFileSync(MANIFEST_FILE, JSON.stringify(manifest, null, 2), 'utf-8');

  console.log(`✅ Wrote ${written} annotated file(s), manifest updated`);
}

main();
