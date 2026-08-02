/**
 * Upload rasterized house images to Supabase Storage and generate a
 * Label Studio task file using public URLs (instead of local-files serving),
 * so remote teammates can annotate without needing the images on their machine.
 *
 * Requires:
 *   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY env vars
 *   npm install (in training-data/) to pull @supabase/supabase-js
 *
 * Usage:
 *   node upload-to-supabase-storage.js               # all houses
 *   node upload-to-supabase-storage.js <house-name>  # single house
 */

const fs = require('fs');
const path = require('path');
const { createClient } = require('@supabase/supabase-js');

const TRAINING_DATA_DIR = __dirname;
const IMAGE_DIR = path.join(TRAINING_DATA_DIR, 'raw', 'image');
const QWEN_OUTPUT_DIR = path.join(TRAINING_DATA_DIR, 'qwen-output');
const OUTPUT_FILE = path.join(TRAINING_DATA_DIR, 'label-studio-tasks-remote.json');
const BUCKET = 'training-drawings';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error('❌ Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars first.');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

function naturalPageSort(a, b) {
  const numOf = (name) => parseInt((name.match(/(\d+)(?=\.\w+$)/) || [0, 0])[1], 10);
  return numOf(a) - numOf(b);
}

async function uploadHouse(houseName) {
  const houseDir = path.join(IMAGE_DIR, houseName);
  const pages = fs
    .readdirSync(houseDir)
    .filter((f) => /\.(png|jpg|jpeg)$/i.test(f))
    .sort(naturalPageSort);

  if (pages.length === 0) {
    console.warn(`⚠️  No page images for ${houseName}`);
    return null;
  }

  const images = [];
  for (const page of pages) {
    const localPath = path.join(houseDir, page);
    const remotePath = `${houseName}/${page}`;
    const fileBuffer = fs.readFileSync(localPath);

    const { error } = await supabase.storage
      .from(BUCKET)
      .upload(remotePath, fileBuffer, { contentType: 'image/png', upsert: true });

    if (error) {
      console.error(`❌ Upload failed ${remotePath}: ${error.message}`);
      continue;
    }

    const { data } = supabase.storage.from(BUCKET).getPublicUrl(remotePath);
    images.push(data.publicUrl);
    process.stdout.write('.');
  }
  console.log(` ✅ ${houseName} (${images.length} pages)`);

  const task = { data: { record_id: houseName, images } };

  const qwenFile = path.join(QWEN_OUTPUT_DIR, `${houseName}-qwen.json`);
  if (fs.existsSync(qwenFile)) {
    task.predictions = [
      {
        model_version: 'qwen-vl-max-v1',
        result: [
          {
            from_name: 'corrected_json',
            to_name: 'page',
            type: 'textarea',
            value: { text: [fs.readFileSync(qwenFile, 'utf-8')] },
          },
        ],
      },
    ];
  }

  return task;
}

async function main() {
  const target = process.argv[2];
  const houses = target
    ? [target]
    : fs.readdirSync(IMAGE_DIR).filter((f) => fs.statSync(path.join(IMAGE_DIR, f)).isDirectory());

  const tasks = [];
  for (const house of houses) {
    const task = await uploadHouse(house);
    if (task) tasks.push(task);
  }

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(tasks, null, 2), 'utf-8');
  console.log(`\n✅ Wrote ${tasks.length} task(s) → ${OUTPUT_FILE}`);
  console.log('   Import this file in the shared Label Studio project.');
}

main();
