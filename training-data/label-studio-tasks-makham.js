/**
 * Per-page Label Studio tasks for "Makham's Pattern" (Gen 3.1/3.2) extraction output.
 *
 * Unlike the old label-studio-tasks-perpage.js (which read raw/image/<house>/qwen-output/
 * and only handled the Gen 1 flat schema: plan[]/section[]/schedule[] + categories[].items[]),
 * this script reads training-data/mk_test/<subfolder>/*.json — the new Gen 3 fresh-extraction
 * output, one file per pattern/view (mixed-pattern pages already split at extraction time,
 * see "Makham's Pattern" doc, this folder: Makham's patter of rawjson20260705.md).
 *
 * Gen 3 has 9 pattern types (plan/section/schedule/notes/index/material_list/site_plan/
 * site_profile/gridline) plus a 10th ("unknown") added during real extraction for content
 * that fits none of the 9. This script buckets every file into one of 3 task groups by
 * shape (not by trusting the "pattern" field name alone, since different extraction agents
 * drifted slightly — e.g. page 29 in mk_test/t2 uses "elements" plural where the spec says
 * "element" singular. Detecting by actual array-key presence is more robust):
 *
 *   1. "elements"      — any file with an element/elements array (plan, section, schedule,
 *                        site_plan, site_profile, and anything else shaped that way)
 *   2. "material_list" — categories[].items[] (BOQ-style)
 *   3. "single"        — everything else: notes (single object), gridline (single object),
 *                        unknown (raw_text), index (sections[] — small enough to review as
 *                        one block rather than a full Repeater)
 *
 * Because element_type varies a lot within group 1 (footing has pile{}, precast_plank_detail
 * has dowel_bar{}/topping_mesh{}, beam/column have main_bar{}/stirrup{}, plan-pattern elements
 * have grid_ref/span_source instead) this script surfaces the common/high-risk fields as
 * editable boxes (matching the "AI often gets this wrong" philosophy of the original
 * label-studio-structural.xml) and dumps anything else into a read-only `other_fields_json`
 * string so nothing is silently dropped (rule_of_tune lesson #3 — never lose a field silently).
 *
 * Usage:
 *   node label-studio-tasks-makham.js <house> [subfolder]
 *   e.g. node label-studio-tasks-makham.js บ้าน_เล็ก_1ชั้น_01 t2
 * Output (written to training-data/ root):
 *   label-studio-tasks-makham-elements.json
 *   label-studio-tasks-makham-material_list.json
 *   label-studio-tasks-makham-single.json
 */

const fs = require('fs');
const path = require('path');

const GITHUB_OWNER = 'whysaomaitrongbaab-collab';
const GITHUB_REPO = 'Training';
const GITHUB_BRANCH = 'main';

function githubRawUrl(houseName, fileName) {
  const encodedHouse = encodeURIComponent(houseName);
  const encodedFile = encodeURIComponent(fileName);
  return `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_BRANCH}/image/${encodedHouse}/${encodedFile}`;
}

// Label Studio's "$items[{{idx}}].field" binding only renders reliably for strings —
// numbers/booleans/arrays/objects came through blank before. Stringify everything.
function str(v) {
  if (v === null || v === undefined) return '';
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

function getArrayField(obj, keys) {
  for (const k of keys) {
    if (Array.isArray(obj[k])) return { key: k, arr: obj[k] };
  }
  return null;
}

// Turn a Makham's Pattern grid_ref like "{D1D2,4}" into "D1 → D2 (4 ม.)" so reviewers
// don't have to mentally parse the compact `{head+tail,span}` notation. Grid tokens are
// [ROW-LETTER][primes?][COL-NUMBER][primes?] (e.g. "D1", "C1'", "A''2") concatenated with
// no separator per spec — split by matching two such tokens (or "?" for unresolved).
const GRID_TOKEN = "[A-Za-z]'*\\d+'*";
const BEAM_GRID_RE = new RegExp(`^\\{(${GRID_TOKEN}|\\?)(${GRID_TOKEN}|\\?),([^}]*)\\}$`);

function formatGridRefDisplay(raw) {
  if (!raw) return '(ไม่มี — เช่น element ที่เป็น slab marker ไม่ใช่เส้น)';
  const m = String(raw).match(BEAM_GRID_RE);
  if (m) {
    const [, head, tail, span] = m;
    const spanTrim = span.trim();
    const spanText = spanTrim === '' || spanTrim === 'null' ? 'ระยะไม่ทราบ' : `ยาว ${spanTrim} ม.`;
    return `${head} → ${tail} (${spanText})`;
  }
  if (String(raw).includes(',')) {
    return `ตำแหน่ง: ${raw}`;
  }
  return String(raw);
}

// Gen 4 (2026-07-08 schema) atomic beam segments use separate grid_ref_start/
// grid_ref_end/span_length_m fields instead of Makham's original packed
// "{head+tail,span}" string. This was NOT handled by the original flattenElementItem
// below -- grid_ref_start/end silently fell into other_fields_json (read-only) and
// grid_ref/grid_ref_display came out blank for every beam. Fixed 2026-07-08.
function formatGridStartEndDisplay(start, end, span) {
  if (!start && !end) return '(ไม่มี — เช่น element ที่เป็น slab marker ไม่ใช่เส้น)';
  const spanText = span === null || span === undefined || span === '' ? 'ระยะไม่ทราบ' : `ยาว ${span} ม.`;
  return `${start || '?'} → ${end || '?'} (${spanText})`;
}

const ELEMENT_CORE_FIELDS = [
  'element_id', 'element_type', 'count', 'grid_ref', 'grid_refs', 'span_source',
  'grid_ref_start', 'grid_ref_end', 'span_length_m',
  'width_mm', 'height_mm', 'level', 'view_title',
];

function flattenElementItem(el) {
  const mainBar = el.main_bar || {};
  // Gen 4 mandates main_bar.top/main_bar.bottom (nested) instead of Makham's
  // original flat main_bar.count/dia_mm/type. Same bug as grid_ref above: the old
  // flat lookup (mainBar.count) silently returned undefined for every beam/column
  // once the schema switched to nested top/bottom. Fixed 2026-07-08 -- now surfaces
  // both, falling back to the flat legacy shape only if top/bottom aren't present.
  const hasTopBottom = mainBar.top || mainBar.bottom;
  const mainBarTop = hasTopBottom ? (mainBar.top || {}) : mainBar;
  const mainBarBottom = hasTopBottom ? (mainBar.bottom || {}) : mainBar;
  const stirrup = el.stirrup || {};
  const rest = {};
  for (const [k, v] of Object.entries(el)) {
    if (
      ELEMENT_CORE_FIELDS.includes(k) ||
      k === 'main_bar' || k === 'stirrup' ||
      k === 'confidence_score' || k === 'confidence_flags'
    ) {
      continue;
    }
    rest[k] = v;
  }

  const hasStartEnd = el.grid_ref_start !== undefined || el.grid_ref_end !== undefined;
  const gridRefRaw = str(el.grid_ref ?? el.grid_refs);
  const gridRefStart = str(el.grid_ref_start);
  const gridRefEnd = str(el.grid_ref_end);
  const spanLengthM = str(el.span_length_m);
  const gridRefDisplay = hasStartEnd
    ? formatGridStartEndDisplay(gridRefStart, gridRefEnd, spanLengthM)
    : formatGridRefDisplay(gridRefRaw);

  return {
    element_id: str(el.element_id),
    element_type: str(el.element_type),
    count: str(el.count),
    grid_ref: hasStartEnd ? '' : gridRefRaw,
    grid_ref_start: gridRefStart,
    grid_ref_end: gridRefEnd,
    span_length_m: spanLengthM,
    grid_ref_display: gridRefDisplay,
    span_source: str(el.span_source),
    width_mm: str(el.width_mm),
    height_mm: str(el.height_mm),
    main_bar_top_count: str(mainBarTop.count),
    main_bar_top_dia_mm: str(mainBarTop.dia_mm),
    main_bar_top_type: str(mainBarTop.type),
    main_bar_bottom_count: str(mainBarBottom.count),
    main_bar_bottom_dia_mm: str(mainBarBottom.dia_mm),
    main_bar_bottom_type: str(mainBarBottom.type),
    stirrup_dia_mm: str(stirrup.dia_mm),
    stirrup_type: str(stirrup.type),
    stirrup_spacing_mm: str(stirrup.spacing_mm),
    confidence_score: str(el.confidence_score),
    confidence_flags: str(el.confidence_flags),
    other_fields_json: Object.keys(rest).length ? JSON.stringify(rest) : '',
    delete: false,
  };
}

function flattenMaterialList(fileData) {
  const items = [];
  for (const cat of fileData.categories || []) {
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
        confidence_flags: str(it.confidence_flags),
        delete: false,
      });
    }
  }
  return items;
}

function main() {
  const house = process.argv[2];
  const subfolder = process.argv[3] || 't2';
  const disciplineFilter = process.argv[4] || null; // e.g. "structural" — omit for all disciplines
  if (!house) {
    console.error('Usage: node label-studio-tasks-makham.js <house> [subfolder] [discipline]');
    process.exit(1);
  }

  const dir = path.join(__dirname, 'mk_test', subfolder);
  if (!fs.existsSync(dir)) {
    console.error(`❌ ${dir} not found`);
    process.exit(1);
  }

  const elementsTasks = [];
  const materialListTasks = [];
  const singleTasks = [];
  let skippedGridMaster = 0;

  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.json') && f.startsWith(house));

  for (const file of files) {
    let data;
    try {
      data = JSON.parse(fs.readFileSync(path.join(dir, file), 'utf-8'));
    } catch (e) {
      console.warn(`⚠️  ${file}: invalid JSON, skipped (${e.message})`);
      continue;
    }

    // The "หน้า00" grid master file is a synthesized cross-page reference, not a
    // real page — review it separately by eye, don't push it through the per-page flow.
    if (data.png === '00') {
      skippedGridMaster += 1;
      continue;
    }

    if (disciplineFilter && data.discipline !== disciplineFilter) continue;

    const recordId = file.replace(/\.json$/, '');
    const pngFile = `${house}_หน้า${data.png}.png`;
    const imageUrl = githubRawUrl(house, pngFile);

    const baseData = {
      record_id: recordId,
      house,
      png: str(data.png),
      doc_page: str(data.doc_page),
      discipline: str(data.discipline),
      sheet_code: str(data.sheet_code),
      sheet_name: str(data.sheet_name),
      pattern: str(data.pattern),
      view_title: str(data.view_title),
      image: imageUrl,
      file_confidence_score: str(data.confidence_score),
      file_confidence_flags: str(data.confidence_flags),
      file_warnings: str(data.warnings),
    };

    const elementArr = getArrayField(data, ['element', 'elements']);
    const catArr = Array.isArray(data.categories);
    const sectionsArr = Array.isArray(data.sections);

    if (elementArr) {
      // Group same-mark segments together (e.g. all B5 spans adjacent) instead of
      // scattering them in extraction order — much easier to review one beam at a time.
      // Array.sort is stable in modern JS engines, so segments keep their original
      // relative order within the same element_id.
      const items = elementArr.arr
        .map(flattenElementItem)
        .sort((a, b) => a.element_id.localeCompare(b.element_id, 'th'));
      if (items.length === 0) continue;
      elementsTasks.push({ data: { ...baseData, source_key: elementArr.key, items } });
    } else if (catArr) {
      const items = flattenMaterialList(data);
      if (items.length === 0) continue;
      materialListTasks.push({ data: { ...baseData, items } });
    } else {
      // notes (single object), gridline (single object), unknown (raw_text), index (sections[])
      // — all reviewed as one JSON block rather than a field-by-field Repeater.
      const reviewObject = { ...data };
      delete reviewObject.png;
      delete reviewObject.doc_page;
      delete reviewObject.discipline;
      delete reviewObject.sheet_code;
      delete reviewObject.sheet_name;
      delete reviewObject.pattern;
      singleTasks.push({
        data: {
          ...baseData,
          sections_count: sectionsArr ? String(data.sections.length) : '',
          review_json: JSON.stringify(reviewObject, null, 2),
        },
      });
    }
  }

  const suffix = disciplineFilter ? `-${disciplineFilter}` : '';
  const elementsFile = `label-studio-tasks-makham-elements${suffix}.json`;
  const materialListFile = `label-studio-tasks-makham-material_list${suffix}.json`;
  const singleFile = `label-studio-tasks-makham-single${suffix}.json`;
  const allFile = `label-studio-tasks-makham-all${suffix}.json`;

  fs.writeFileSync(path.join(__dirname, elementsFile), JSON.stringify(elementsTasks, null, 2), 'utf-8');
  fs.writeFileSync(path.join(__dirname, materialListFile), JSON.stringify(materialListTasks, null, 2), 'utf-8');
  fs.writeFileSync(path.join(__dirname, singleFile), JSON.stringify(singleTasks, null, 2), 'utf-8');

  // Reference/archive copy only — NOT for importing into Label Studio directly. Each
  // group still needs its own project + matching Labeling Interface config (elements/
  // material_list/single have different field shapes), so real imports use the 3 files
  // above. This one just groups them for browsing/backup in one place.
  const allTasks = {
    _readme: 'Reference/archive copy only — for actually importing into Label Studio Cloud, use the 3 separate files (elements/material_list/single) into their matching project. This file just groups all 3 together for browsing/backup.',
    elements: elementsTasks,
    material_list: materialListTasks,
    single: singleTasks,
  };
  fs.writeFileSync(path.join(__dirname, allFile), JSON.stringify(allTasks, null, 2), 'utf-8');

  console.log(`✅ Elements tasks (plan/section/schedule/site_plan/...): ${elementsTasks.length} → ${elementsFile}`);
  console.log(`✅ Material list tasks: ${materialListTasks.length} → ${materialListFile}`);
  console.log(`✅ Single-record tasks (notes/gridline/unknown/index): ${singleTasks.length} → ${singleFile}`);
  console.log(`✅ Combined reference copy (not for import): ${elementsTasks.length + materialListTasks.length + singleTasks.length} → ${allFile}`);
  console.log(`ℹ️  Skipped ${skippedGridMaster} grid-master file(s) (png:"00", reviewed separately)`);
  if (disciplineFilter) console.log(`ℹ️  Filtered to discipline="${disciplineFilter}" only`);
}

main();
