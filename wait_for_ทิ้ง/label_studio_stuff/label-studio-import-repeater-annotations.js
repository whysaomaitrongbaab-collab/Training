/**
 * Convert a Label Studio export for the Repeater-based "Structural Review" /
 * "BOQ Review" projects back into annotated/<record_id>-<type>-annotated.json,
 * in the SAME shape/types as the original AI extraction schema — this is what
 * makes the output usable as fine-tuning ground truth later (docs/FINETUNING_FLOW.md
 * step 5, main Constistant repo), not just a review record.
 *
 * label-studio-tasks-perpage.js flattened the original nested schema into a UI-
 * friendly shape (numbers -> strings so Label Studio would render them, arrays ->
 * comma-joined strings, plan+section+schedule merged into one items[] list). This
 * script reverses all three so the output matches what the model should actually
 * learn to produce:
 *   - numeric fields  -> Number (or null if blank/unparseable)
 *   - grid_refs / confidence_flags -> array (split on comma)
 *   - structural items -> regrouped back into plan[] / section[] / schedule[] by _source
 *   - boq items        -> regrouped back into categories[].items[] by category
 *
 * CONFIDENCE WARNING: I could not verify Label Studio's exact export JSON shape
 * for Repeater results against live docs (fetch attempts failed while building
 * this). The field-name convention assumed below (`<field>_<idx>` as `from_name`,
 * `value.text[0]` for TextArea, `value.choices` for Choices) matches the
 * `{{idx}}`-suffixed names used in label-studio-structural.xml / label-studio-boq.xml.
 *
 * BEFORE trusting this at scale: export just 1-2 completed tasks from Label Studio,
 * run this script on that small file, and manually check the output JSON matches
 * what the reviewer actually typed (types included — count should be a number, not
 * "9" in quotes).
 *
 * Usage:
 *   node label-studio-import-repeater-annotations.js structural <export.json>
 *   node label-studio-import-repeater-annotations.js boq <export.json>
 */

const fs = require('fs');
const path = require('path');

const ANNOTATED_DIR = path.join(__dirname, 'annotated');
const MANIFEST_FILE = path.join(__dirname, 'manifest.json');

// Only fields with an actual edit box in label-studio-structural.xml / label-studio-boq.xml
// (v3 — cut down to the fields the AI actually gets wrong often, see CLAUDE.md).
// Everything else is NOT editable in the UI and is always carried over from the
// original AI value below (see the "carry over non-editable fields" block).
const EDITABLE_FIELD_NAMES = {
  structural: ['element_id', 'element_type', 'count', 'grid_refs', 'span_length_m',
    'main_bar_dia_mm', 'stirrup_dia_mm', 'stirrup_spacing_mm'],
  boq: ['item_no', 'description', 'quantity', 'unit'],
};

const READONLY_FIELD_NAMES = {
  structural: ['width_mm', 'height_mm', 'main_bar_count', 'main_bar_type', 'stirrup_type',
    'concrete_grade', 'steel_grade'],
  boq: ['material_unit_price', 'material_amount', 'labor_unit_price', 'labor_amount', 'total_amount'],
};

// Fields that must come back out as JS numbers (they were stringified only so
// Label Studio's "$items[{{idx}}].field" binding would render them — see
// label-studio-tasks-perpage.js's str() helper).
const NUMERIC_FIELDS = {
  structural: ['count', 'span_length_m', 'width_mm', 'height_mm', 'main_bar_count',
    'main_bar_dia_mm', 'stirrup_dia_mm', 'stirrup_spacing_mm', 'confidence_score'],
  boq: ['quantity', 'material_unit_price', 'material_amount', 'labor_unit_price',
    'labor_amount', 'total_amount', 'confidence_score'],
};

// Fields that were arrays originally, joined with ", " for display — split back.
const ARRAY_FIELDS = ['grid_refs', 'confidence_flags'];

function resultMap(annotation) {
  // from_name -> result entry, for quick lookup
  const map = {};
  for (const r of annotation.result || []) {
    map[r.from_name] = r;
  }
  return map;
}

function textValue(entry) {
  if (!entry) return undefined;
  if (entry.value?.text?.length) return entry.value.text[0];
  return undefined;
}

// element_type_{{idx}} is a Choices field (label-studio-structural.xml), not a
// TextArea like the other fields — reads value.choices instead of value.text.
function choiceValue(entry) {
  if (!entry) return undefined;
  if (entry.value?.choices?.length) return entry.value.choices[0];
  return undefined;
}

function isDeleted(entry) {
  if (!entry) return false;
  return Array.isArray(entry.value?.choices) && entry.value.choices.includes('delete');
}

function toNumberOrNull(value, fieldName, recordId) {
  if (value === '' || value === null || value === undefined) return null;
  const n = Number(value);
  if (Number.isNaN(n)) {
    console.warn(`⚠️  ${recordId}: field "${fieldName}" = "${value}" is not a valid number — set to null, fix by hand`);
    return null;
  }
  return n;
}

function toArray(value) {
  if (value === '' || value === null || value === undefined) return [];
  return String(value).split(',').map((s) => s.trim()).filter(Boolean);
}

function groupStructural(items) {
  const grouped = { plan: [], section: [], schedule: [] };
  for (const item of items) {
    const { _source, ...rest } = item;
    (grouped[_source] || grouped.plan).push(rest);
  }
  return grouped;
}

function groupBoq(items) {
  const byCategory = new Map();
  for (const item of items) {
    const { category, ...rest } = item;
    if (!byCategory.has(category)) byCategory.set(category, []);
    byCategory.get(category).push(rest);
  }
  return [...byCategory.entries()].map(([category, catItems]) => ({ category, items: catItems }));
}

function convertTask(task, type) {
  const annotation = task.annotations?.[0];
  if (!annotation) return null;

  const recordId = task.data.record_id;
  const map = resultMap(annotation);
  const originalItems = task.data.items || [];
  const editableFields = EDITABLE_FIELD_NAMES[type];
  const readonlyFields = READONLY_FIELD_NAMES[type];
  const numericFields = new Set(NUMERIC_FIELDS[type]);

  const items = [];
  originalItems.forEach((original, idx) => {
    if (isDeleted(map[`delete_${idx}`])) return; // reviewer marked as AI hallucination

    const corrected = {};
    for (const field of editableFields) {
      const entry = map[`${field}_${idx}`];
      // element_type is a Choices field in the structural config; every other
      // editable field is a TextArea.
      const edited = field === 'element_type' ? choiceValue(entry) : textValue(entry);
      // Fall back to the original AI value if the reviewer didn't touch this field
      corrected[field] = edited !== undefined && edited !== '' ? edited : original[field];
    }
    // Non-editable fields (no edit box in the UI) — always carry over from source as-is
    for (const field of readonlyFields) {
      corrected[field] = original[field];
    }
    corrected.confidence_score = original.confidence_score;
    corrected.confidence_flags = original.confidence_flags;
    if (type === 'structural') corrected._source = original._source;
    if (type === 'boq') corrected.category = original.category;

    // Reverse the stringify-for-display transforms from label-studio-tasks-perpage.js
    for (const field of Object.keys(corrected)) {
      if (numericFields.has(field)) {
        corrected[field] = toNumberOrNull(corrected[field], field, recordId);
      } else if (ARRAY_FIELDS.includes(field)) {
        corrected[field] = toArray(corrected[field]);
      }
    }

    items.push(corrected);
  });

  const reviewerNote = textValue(map['reviewer_note']) || '';
  const base = {
    record_id: recordId,
    house: task.data.house,
    page: task.data.page,
    review_status: 'approved',
    reviewer_note: reviewerNote,
    annotation_date: new Date().toISOString(),
  };

  if (type === 'structural') {
    const grouped = groupStructural(items);
    return {
      ...base,
      sheet_code: task.data.sheet_code,
      sheet_name: task.data.sheet_name,
      plan: grouped.plan,
      section: grouped.section,
      schedule: grouped.schedule,
    };
  }

  return {
    ...base,
    sheet_no: task.data.sheet_no,
    categories: groupBoq(items),
  };
}

function main() {
  const type = process.argv[2];
  const exportFile = process.argv[3];

  if (!['structural', 'boq'].includes(type) || !exportFile) {
    console.error('Usage: node label-studio-import-repeater-annotations.js <structural|boq> <export.json>');
    process.exit(1);
  }

  const tasks = JSON.parse(fs.readFileSync(exportFile, 'utf-8'));
  if (!fs.existsSync(ANNOTATED_DIR)) fs.mkdirSync(ANNOTATED_DIR, { recursive: true });

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8'));
  let written = 0;

  for (const task of tasks) {
    const converted = convertTask(task, type);
    if (!converted) continue;

    const outFile = path.join(ANNOTATED_DIR, `${converted.record_id}-${type}-annotated.json`);
    fs.writeFileSync(outFile, JSON.stringify(converted, null, 2), 'utf-8');
    console.log(`💾 ${outFile}`);
    written += 1;

    let entry = manifest.datasets.find((d) => d.id === converted.record_id);
    if (!entry) {
      entry = { id: converted.record_id };
      manifest.datasets.push(entry);
    }
    entry.annotated_output = outFile;
    entry.annotation_date = converted.annotation_date;
    entry.status = 'annotated';
    entry.type = type;
  }

  manifest.stats.annotated_datasets = manifest.datasets.filter((d) => d.status === 'annotated').length;
  fs.writeFileSync(MANIFEST_FILE, JSON.stringify(manifest, null, 2), 'utf-8');

  console.log(`✅ Wrote ${written} annotated file(s), manifest updated`);
  console.log('⚠️  First run: spot-check the output against what you actually typed in Label Studio (including types — count should be a number, not "9" in quotes).');
}

main();
