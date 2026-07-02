/**
 * Per-page Label Studio tasks for the "Structural Review" / "BOQ Review" projects
 * (King's plan: field-level Repeater editing instead of whole-JSON textarea).
 *
 * Reads real extraction JSON from raw/image/<house>/qwen-output/<house>_หน้าNN.json,
 * flattens plan+section+schedule (structural) or categories[].items[] (boq) into a
 * single `items` array per page, and points the image at raw.githubusercontent.com
 * (same public-repo approach as label-studio-tasks-github.js — no Supabase Storage,
 * per the "database ต้องเป็น GitHub repo Training เท่านั้น" requirement).
 *
 * "notes"-pattern structural pages are skipped: extraction.notes is a single object
 * (project-wide specs like concrete_strength_ksc), not a list — it doesn't fit the
 * Repeater review UI. Handle those separately later if needed.
 *
 * Usage:
 *   node label-studio-tasks-perpage.js
 * Output:
 *   label-studio-tasks-structural.json
 *   label-studio-tasks-boq.json
 */

const fs = require('fs');
const path = require('path');

const QWEN_OUTPUT_BASE = path.join(__dirname, 'raw', 'image');

const GITHUB_OWNER = 'whysaomaitrongbaab-collab';
const GITHUB_REPO = 'Training';
const GITHUB_BRANCH = 'main';

function githubRawUrl(houseName, fileName) {
  const encodedHouse = encodeURIComponent(houseName);
  const encodedFile = encodeURIComponent(fileName);
  return `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_BRANCH}/image/${encodedHouse}/${encodedFile}`;
}

function flattenStructural(extraction) {
  const items = [];
  for (const source of ['plan', 'section', 'schedule']) {
    const arr = extraction[source];
    if (!Array.isArray(arr)) continue;
    for (const el of arr) {
      items.push({
        _source: source,
        element_id: el.element_id ?? '',
        element_type: el.element_type ?? '',
        count: el.count ?? '',
        grid_refs: Array.isArray(el.grid_refs) ? el.grid_refs.join(', ') : (el.grid_refs ?? ''),
        span_length_m: el.span_length_m ?? '',
        width_mm: el.width_mm ?? '',
        height_mm: el.height_mm ?? '',
        main_bar_count: el.main_bar_count ?? '',
        main_bar_dia_mm: el.main_bar_dia_mm ?? '',
        main_bar_type: el.main_bar_type ?? '',
        stirrup_dia_mm: el.stirrup_dia_mm ?? '',
        stirrup_type: el.stirrup_type ?? '',
        stirrup_spacing_mm: el.stirrup_spacing_mm ?? '',
        concrete_grade: el.concrete_grade ?? '',
        steel_grade: el.steel_grade ?? '',
        confidence_score: el.confidence_score ?? '',
        confidence_flags: Array.isArray(el.confidence_flags) ? el.confidence_flags.join(', ') : '',
        delete: false,
      });
    }
  }
  return items;
}

function flattenBoq(extraction) {
  const items = [];
  for (const cat of extraction.categories || []) {
    for (const it of cat.items || []) {
      items.push({
        category: cat.category ?? '',
        item_no: it.item_no ?? '',
        description: it.description ?? '',
        quantity: it.quantity ?? '',
        unit: it.unit ?? '',
        material_unit_price: it.material_unit_price ?? '',
        material_amount: it.material_amount ?? '',
        labor_unit_price: it.labor_unit_price ?? '',
        labor_amount: it.labor_amount ?? '',
        total_amount: it.total_amount ?? '',
        confidence_score: it.confidence_score ?? '',
        confidence_flags: Array.isArray(it.confidence_flags) ? it.confidence_flags.join(', ') : '',
        delete: false,
      });
    }
  }
  return items;
}

function main() {
  if (!fs.existsSync(QWEN_OUTPUT_BASE)) {
    console.error(`❌ ${QWEN_OUTPUT_BASE} not found`);
    process.exit(1);
  }

  const houses = fs
    .readdirSync(QWEN_OUTPUT_BASE)
    .filter((f) => fs.statSync(path.join(QWEN_OUTPUT_BASE, f)).isDirectory());

  const structuralTasks = [];
  const boqTasks = [];
  let skippedNotes = 0;

  for (const house of houses) {
    const qwenDir = path.join(QWEN_OUTPUT_BASE, house, 'qwen-output');
    if (!fs.existsSync(qwenDir)) continue;

    const pageFiles = fs.readdirSync(qwenDir).filter((f) => /_หน้า\d+\.json$/.test(f));
    for (const pageFile of pageFiles) {
      let data;
      try {
        data = JSON.parse(fs.readFileSync(path.join(qwenDir, pageFile), 'utf-8'));
      } catch (e) {
        console.warn(`⚠️  ${house}/${pageFile}: invalid JSON, skipped (${e.message})`);
        continue;
      }

      const pngFile = pageFile.replace(/\.json$/, '.png');
      const imageUrl = githubRawUrl(house, pngFile);
      const pageMatch = pageFile.match(/_หน้า(\d+)\.json$/);
      const pageLabel = pageMatch ? pageMatch[1] : '?';

      if (data.discipline === 'structural' && data.extraction) {
        if (data.extraction.pattern === 'notes') {
          skippedNotes += 1;
          continue;
        }
        const items = flattenStructural(data.extraction);
        if (items.length === 0) continue;
        structuralTasks.push({
          data: {
            record_id: `${house}_page${pageLabel}`,
            house,
            page: pageLabel,
            sheet_code: data.extraction.sheet_code ?? '',
            sheet_name: data.extraction.sheet_name ?? '',
            image: imageUrl,
            items,
          },
        });
      } else if (data.discipline === 'boq' && data.extraction) {
        const items = flattenBoq(data.extraction);
        if (items.length === 0) continue;
        boqTasks.push({
          data: {
            record_id: `${house}_page${pageLabel}`,
            house,
            page: pageLabel,
            sheet_no: data.extraction.sheet_no ?? '',
            image: imageUrl,
            items,
          },
        });
      }
    }
  }

  fs.writeFileSync(
    path.join(__dirname, 'label-studio-tasks-structural.json'),
    JSON.stringify(structuralTasks, null, 2),
    'utf-8'
  );
  fs.writeFileSync(
    path.join(__dirname, 'label-studio-tasks-boq.json'),
    JSON.stringify(boqTasks, null, 2),
    'utf-8'
  );

  console.log(`✅ Structural tasks: ${structuralTasks.length} pages → label-studio-tasks-structural.json`);
  console.log(`✅ BOQ tasks: ${boqTasks.length} pages → label-studio-tasks-boq.json`);
  console.log(`ℹ️  Skipped ${skippedNotes} "notes"-pattern page(s) (single-object shape, not a list)`);
}

main();
