// เทียบ GT vs คำตอบโมเดล ทีละงาน หาสาเหตุ recall 0%
import fs from 'fs';
import path from 'path';

const VAL = 'D:/00mk/steel project/training/Training/tune_ai/t04_Purson/data_before_tune/val_fold0_sample.jsonl';
const RES = 'D:/00mk/steel project/training/Training/tune_ai/t04_Purson/eval_results/fold0';

const gtById = new Map();
for (const line of fs.readFileSync(VAL, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const r = JSON.parse(line);
  const c = r.messages[r.messages.length - 1].content;
  const txt = typeof c === 'string' ? c : c.map(p => p.text || '').join('');
  gtById.set(r.id, { gt: JSON.parse(txt), subtask: r.subtask });
}

const only = process.argv[2]; // filter by subtask

for (const [id, { gt, subtask }] of gtById) {
  if (only && subtask !== only) continue;
  const fname = id.replace(/::/g, '__') + '.txt';
  const fp = path.join(RES, fname);
  if (!fs.existsSync(fp)) { console.log(`[MISSING FILE] ${id}`); continue; }
  let pred;
  try { pred = JSON.parse(fs.readFileSync(fp, 'utf8')); }
  catch { console.log(`[JSON เสีย] ${id}`); continue; }

  const gtIds = (gt.elements || []).map(e => e.element_id);
  const prIds = (pred.elements || []).map(e => e.element_id);
  const gtTypes = [...new Set((gt.elements || []).map(e => e.element_type))];
  const prTypes = [...new Set((pred.elements || []).map(e => e.element_type))];
  const hit = gtIds.filter(x => prIds.includes(x));

  console.log(`\n=== ${subtask} | ${id.split('::')[1]}`);
  console.log(`  pattern  GT=${gt.pattern}  PRED=${pred.pattern}`);
  console.log(`  types    GT=[${gtTypes}]  PRED=[${prTypes}]`);
  console.log(`  GT  ids  (${gtIds.length}) ${JSON.stringify(gtIds.slice(0, 12))}`);
  console.log(`  PRED ids (${prIds.length}) ${JSON.stringify(prIds.slice(0, 12))}`);
  console.log(`  ตรงกัน   ${hit.length} -> ${JSON.stringify(hit)}`);
}
