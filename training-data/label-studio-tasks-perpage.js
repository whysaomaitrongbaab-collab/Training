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

// Label Studio's "$items[{{idx}}].field" data binding only renders correctly for
// string values — numbers (count, span_length_m, confidence_score, etc.) came
// through as raw JS numbers before and rendered as blank boxes in the UI. Stringify
// everything so every field is guaranteed to display.
function str(v) {
  return v === null || v === undefined ? '' : String(v);
}

function flattenStructural(extraction) {
  const items = [];
  for (const source of ['plan', 'section', 'schedule']) {
    const arr = extraction[source];
    if (!Array.isArray(arr)) continue;
    for (const el of arr) {
      items.push({
        _source: source,
        element_id: str(el.element_id),
        element_type: str(el.element_type),
        count: str(el.count),
        grid_refs: Array.isArray(el.grid_refs) ? el.grid_refs.join(', ') : str(el.grid_refs),
        span_length_m: str(el.span_length_m),
        width_mm: str(el.width_mm),
        height_mm: str(el.height_mm),
        main_bar_count: str(el.main_bar_count),
        main_bar_dia_mm: str(el.main_bar_dia_mm),
        main_bar_type: str(el.main_bar_type),
        stirrup_dia_mm: str(el.stirrup_dia_mm),
        stirrup_type: str(el.stirrup_type),
        stirrup_spacing_mm: str(el.stirrup_spacing_mm),
        concrete_grade: str(el.concrete_grade),
        steel_grade: str(el.steel_grade),
        confidence_score: str(el.confidence_score),
        confidence_flags: Array.isArray(el.confidence_flags) ? el.confidence_flags.join(', ') : '',
        delete: false,
      });
    }
  }
  return items;
}

// NOTE: tried pre-checking element_type_{{idx}} Choices via Label Studio
// "predictions" — confirmed broken (2026-07-02). Label Studio validates a
// prediction's from_name against the literal control tag names in the labeling
// config; Repeater only expands {{idx}} into element_type_0, element_type_1, etc.
// client-side at render time, so the server rejects every prediction as
// "from_name not found in configuration". No known workaround for Choices+Repeater
// pre-selection — label-studio-structural.xml shows the AI's guess as a plain text
// hint next to the Choices instead (works, already verified in the live UI).

function flattenBoq(extraction) {
  const items = [];
  for (const cat of extraction.categories || []) {
    for (const it of cat.items || []) {
      items.push({
        category: str(cat.category),
        item_no: str(it.item_no),
        description: str(it.description),
        quantity: str(it.quantity),
        unit: str(it.unit),
        material_unit_price: str(it.material_unit_price),
        material_amount: str(it.material_amount),
        labor_unit_price: str(it.labor_unit_price),
        labor_amount: str(it.labor_amount),
        total_amount: str(it.total_amount),
        confidence_score: str(it.confidence_score),
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
