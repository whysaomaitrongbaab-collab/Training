/**
 * Generate Label Studio import tasks using GitHub raw URLs for images
 * hosted in this repo's top-level image/<house>/ folders.
 *
 * No upload step needed — the Training repo is public, so
 * raw.githubusercontent.com serves the PNGs directly to Label Studio Cloud.
 *
 * Usage:
 *   node label-studio-tasks-github.js                 # all houses in image/
 *   node label-studio-tasks-github.js <house-name>    # single house
 */

const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..'); // training-data/ -> repo root
const IMAGE_DIR = path.join(REPO_ROOT, 'image');
const OUTPUT_FILE = path.join(__dirname, 'label-studio-tasks-github.json');

const GITHUB_OWNER = 'whysaomaitrongbaab-collab';
const GITHUB_REPO = 'Training';
const GITHUB_BRANCH = 'main';

function naturalPageSort(a, b) {
  const numOf = (name) => parseInt((name.match(/(\d+)(?=\.\w+$)/) || [0, 0])[1], 10);
  return numOf(a) - numOf(b);
}

function githubRawUrl(houseName, fileName) {
  // Encode each path segment separately (Thai + spaces) — do not encode the "/" separators.
  const encodedHouse = encodeURIComponent(houseName);
  const encodedFile = encodeURIComponent(fileName);
  return `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_BRANCH}/image/${encodedHouse}/${encodedFile}`;
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

  const images = pages.map((f) => githubRawUrl(houseName, f));
  const task = { data: { record_id: houseName, images } };

  // Attach a Qwen extraction as pre-annotation when one exists for this house.
  const qwenFile = path.join(__dirname, 'qwen-output', `${houseName}-qwen.json`);
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
  console.log(`   Import this file in Label Studio Cloud: Project → Import → Upload Files`);
}

main();
