// tools/adapt_check.mjs — เอาโฟลเดอร์บ้านหนึ่งหลังเข้า adapter ตัวจริงของ Constistant (ไม่แตะอะไร อ่านอย่างเดียว)
// แล้วสรุป: จำนวนชิ้นต่อ ชั้น|ชนิด|ที่มาของความยาว, ช่วงที่หาตำแหน่งไม่ได้ (unresolved), สเปกที่ join ได้, คำเตือนของ adapter
//
//   node tools/adapt_check.mjs "rawjson_ยังไม่ได้แก้ไขโดนคน/165บ้าน_ใหญ่_2ชั้น_23"
//
// หา Constistant จาก env CONSTISTANT_DIR ไม่งั้นใช้ path ข้างล่าง (repo พี่น้องของ Training บนเครื่องนี้)
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const CONSTISTANT = process.env.CONSTISTANT_DIR || 'D:/00mk/steel project/งานสมบูรณ์/Constistant';
const dir = process.argv[2];
if (!dir || !fs.existsSync(dir)) { console.error('usage: node tools/adapt_check.mjs <house folder>'); process.exit(2); }

const { adaptRawExtraction } = await import(pathToFileURL(path.join(CONSTISTANT, 'js/drawing/raw-extraction-adapter.js')).href);
const names = fs.readdirSync(dir).filter(f => f.endsWith('.json') && !f.startsWith('_')).sort();
if (!names.length) { console.error('no data json in ' + dir); process.exit(1); }
const files = names.map(f => JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')));
const r = adaptRawExtraction(files);

const counts = {};
const unresolved = [];
for (const e of r.elements) {
  const k = `${e.floor_level ?? '?'}|${e.element_type ?? '?'}|${e.span_source ?? 'n/a'}`;
  counts[k] = (counts[k] || 0) + 1;
  if (e.span_source === 'unresolved' && e.element_type !== 'footing' && e.element_type !== 'column') unresolved.push(`${e.element_id ?? e.mark ?? '?'} ${e.grid_refs ?? ''}`);
}
console.log(`files read: ${names.length}  elements: ${r.elements.length}`);
console.log('┌────────────────────┬────────┐');
for (const k of Object.keys(counts).sort()) console.log(`│ ${k.padEnd(18)} │ ${String(counts[k]).padEnd(6)} │`);
console.log('└────────────────────┴────────┘');
console.log('unresolved spans:', JSON.stringify(unresolved.slice(0, 20)) + (unresolved.length > 20 ? ` ... +${unresolved.length - 20}` : ''));
const specKeys = Array.isArray(r.specs) ? r.specs.map(s => s.element_id ?? s.mark ?? s.id) : Object.keys(r.specs || {});
console.log('specs joined:', specKeys.filter(Boolean).sort().join(' '));
const own = r.warnings.filter(w => !w.startsWith('[โมเดล]'));
console.log(`warnings (${r.warnings.length}, ${own.length} from the adapter itself):`);
for (const w of own.slice(0, 25)) console.log(' - ' + w);
if (own.length > 25) console.log(` ... and ${own.length - 25} more`);
