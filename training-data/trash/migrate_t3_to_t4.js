/**
 * One-off migration: mk_test/t3/ -> mk_test/t4/, applying the 3 rules added
 * 2026-07-08 in `20260708draft of prime rawjson.md` without re-reading any images
 * (token-saving pass — pure data transform of already-extracted t3 content):
 *
 *   1. Add `source_image` (wrapper-level) to every file, derived from house+png.
 *   2. Reclassify pattern for the small number of files that fit one of the 3
 *      new pattern types (title/symbol/roof_plan) better than their t3 pattern.
 *   3. Grid master (หน้า00) gets `source_pages` instead of a single source_image,
 *      and is checked (not rewritten — already compliant) against the new
 *      dummy-grid prime-ordering rule.
 *
 * Run once: node migrate_t3_to_t4.js
 */
const fs = require('fs');
const path = require('path');

const SRC_DIR = path.join(__dirname, 'mk_test', 't3');
const DST_DIR = path.join(__dirname, 'mk_test', 't4');
if (!fs.existsSync(DST_DIR)) fs.mkdirSync(DST_DIR, { recursive: true });

// Pattern reclassifications decided by inspecting t3 content (see workmen's_diary
// entry for this migration for the reasoning behind each).
const PATTERN_OVERRIDES = {
  'บ้าน_เล็ก_1ชั้น_01_หน้า01.json': {
    to: 'title',
    reason: 'sheet_name "ปกแบบ" (front cover) -- was "unknown" in t3 before pattern "title" existed',
  },
  'บ้าน_เล็ก_1ชั้น_01_หน้า61.json': {
    to: 'title',
    reason: 'back-cover catalog/promotional page for the whole house-design series -- JUDGMENT CALL: "title" pattern was only defined as "หน้าปก" (front cover) without a front/back distinction; classifying this back-cover page as "title" too since it is cover-type front-matter with zero takeoff content, not because it is definitely correct -- flag for human confirmation',
  },
  'บ้าน_เล็ก_1ชั้น_01_หน้า03_symbol_legend.json': { to: 'symbol', reason: 'symbol/legend table -- was "unknown" in t3' },
  'บ้าน_เล็ก_1ชั้น_01_หน้า26_symbol_legend.json': { to: 'symbol', reason: 'symbol/legend table -- was "notes" in t3' },
  'บ้าน_เล็ก_1ชั้น_01_หน้า33_symbol_legend.json': { to: 'symbol', reason: 'symbol/legend table -- was "notes" in t3' },
  'บ้าน_เล็ก_1ชั้น_01_หน้า20_view2_roof_frame_plan.json': { to: 'roof_plan', reason: 'roof framing plan (purlin/rafter) -- was generic "plan" in t3, now has its own pattern' },
};

const GRID_MASTER_FILE = 'บ้าน_เล็ก_1ชั้น_01_หน้า00_gridline.json';
const files = fs.readdirSync(SRC_DIR).filter((f) => f.endsWith('.json'));

let migrated = 0;
const patternChanges = [];

for (const file of files) {
  if (file === GRID_MASTER_FILE) continue; // handled separately below

  const data = JSON.parse(fs.readFileSync(path.join(SRC_DIR, file), 'utf-8'));

  const house = data.house || 'บ้าน_เล็ก_1ชั้น_01';
  const pngNum = String(data.png).padStart(2, '0');
  data.source_image = `image/${house}/${house}_หน้า${pngNum}.png`;

  const override = PATTERN_OVERRIDES[file];
  if (override) {
    data['_pattern_reclassified_2026-07-08'] = { from: data.pattern, to: override.to, reason: override.reason };
    data.pattern = override.to;
    patternChanges.push(`${file}: ${data['_pattern_reclassified_2026-07-08'].from} -> ${override.to}`);
  }

  fs.writeFileSync(path.join(DST_DIR, file), JSON.stringify(data, null, 2), 'utf-8');
  migrated++;
}

// Grid master: source_pages (list) instead of a single source_image, since it's
// synthesized from evidence across multiple pages, not read from one image.
const gridData = JSON.parse(fs.readFileSync(path.join(SRC_DIR, GRID_MASTER_FILE), 'utf-8'));
const houseName = 'บ้าน_เล็ก_1ชั้น_01';
gridData.source_pages = [
  `image/${houseName}/${houseName}_หน้า06.png`, // A-04 floor plan -- dummy grid 1'/3'/A'/A'' evidence
  `image/${houseName}/${houseName}_หน้า19.png`, // S-02 -- named grid + dummy grid 1'/3'/A' re-confirmed on this sheet itself
  `image/${houseName}/${houseName}_หน้า20.png`, // S-03 -- named grid re-confirmed (tie-beam + roof frame views)
];
gridData['_migration_note_2026-07-08'] =
  'Checked against the new dummy-grid prime-ordering rule (20260708draft section 3.1.1/3.1.2): ' +
  "existing entries already comply -- x_lines 1'/3' are in separate gaps (no reordering needed), " +
  "y_lines A'(11.0)/A''(12.5) are in the same gap and already ordered top-to-bottom by increasing " +
  "distance from grid A, matching the rule. No dummy grid found before the origin (0,0), so the " +
  'negative-pos_m rule (3.1.2) was not triggered -- nothing to change, verified only.';
fs.writeFileSync(path.join(DST_DIR, GRID_MASTER_FILE), JSON.stringify(gridData, null, 2), 'utf-8');
migrated++;

console.log(`Migrated ${migrated} files (incl. grid master) to mk_test/t4/`);
console.log(`Pattern reclassifications (${patternChanges.length}):`);
patternChanges.forEach((c) => console.log('  ' + c));
