/**
 * Generate Label Studio import tasks from rasterized house images.
 * Reads raw/image/<house>/*.png, attaches raw/image/<house>/qwen-output/<house>-qwen.json
 * as a pre-annotation (prediction) when it exists.
 *
 * Usage:
 *   node label-studio-tasks.js                 # all houses in raw/image/
 *   node label-studio-tasks.js <house-name>    # single house
 */

const fs = require('fs');
const path = require('path');

const TRAINING_DATA_DIR = __dirname;
const IMAGE_DIR = path.join(TRAINING_DATA_DIR, 'raw', 'image');
const OUTPUT_FILE = path.join(TRAINING_DATA_DIR, 'label-studio-tasks.json');
// Label Studio's list-type Image tag requires a fully-qualified URL (scheme + host),
// unlike a single $image binding where the browser resolves a relative path itself.
const LABEL_STUDIO_ORIGIN = process.env.LABEL_STUDIO_ORIGIN || 'http://localhost:8080';

function naturalPageSort(a, b) {
  const numOf = (name) => parseInt((name.match(/(\d+)(?=\.\w+$)/) || [0, 0])[1], 10);
  return numOf(a) - numOf(b);
}

function buildTaskForHouse(houseName) {
  const houseDir = path.join(IMAGE_DIR, houseName);
  const pages = fs
    .readdirSync(houseDir)
    .filter((f) => /\.(png|jpg|jpeg)$/i.test(f))
    .sort(naturalPageSort);

  if (pages.length === 0) {
    console.warn(`⚠️  No page images found for ${houseName}`);
    return null;
  }

  // Label Studio encodes this value itself when building the request — do not
  // pre-encode here, or the path gets double-encoded and fails to resolve.
  const images = pages.map(
    (f) => `${LABEL_STUDIO_ORIGIN}/data/local-files/?d=image/${houseName}/${f}`
  );

  const task = {
    data: { record_id: houseName, images },
  };

  const qwenFile = path.join(houseDir, 'qwen-output', `${houseName}-qwen.json`);
  if (fs.existsSync(qwenFile)) {
    const qwenJson = fs.readFileSync(qwenFile, 'utf-8');
    task.predictions = [
      {
        model_version: 'qwen-vl-max-v1',
        result: [
          {
            from_name: 'corrected_json',
            to_name: 'page',
            type: 'textarea',
            value: { text: [qwenJson] },
          },
        ],
      },
    ];
  }

  return task;
}

function main() {
  const target = process.argv[2];
  const houses = target
    ? [target]
    : fs.readdirSync(IMAGE_DIR).filter((f) => fs.statSync(path.join(IMAGE_DIR, f)).isDirectory());

  const tasks = houses.map(buildTaskForHouse).filter(Boolean);

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(tasks, null, 2), 'utf-8');
  console.log(`✅ Wrote ${tasks.length} task(s) → ${OUTPUT_FILE}`);
  console.log(`   Import this file in Label Studio: Project → Import → Upload Files`);
}

main();
