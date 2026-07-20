#!/usr/bin/env node
/**
 * build_dataset.js — ประกอบ fine-tuning dataset สำหรับ Qwen3-VL
 *   จาก  json_แก้ไขแล้ว/  (4 หลัง, 474 ไฟล์)  →  train.jsonl / val.jsonl
 *
 * รันจากโฟลเดอร์นี้:  node build_dataset.js
 *
 * ⚠️ rule_of_tune.md ข้อ 2 (ส่วนขยาย): ไฟล์นี้กำหนดว่าอะไรจะกลายเป็น "ตัวอย่าง training"
 *    ทุกการแก้ CFG ด้านล่าง = เปลี่ยนสิ่งที่โมเดลจะเรียน ต้องเตือน/ขออนุญาตก่อนเสมอ
 */
const fs = require('fs');
const path = require('path');

// ─────────────────────────────────────────────────────────────
// CONFIG — ปรับตรงนี้แล้วรันใหม่ ไม่ต้องแก้โค้ดข้างล่าง
// ─────────────────────────────────────────────────────────────
// source_image ในไฟล์ JSON เขียนเป็น path relative จาก root ของ repo Training
// (เช่น "image/<house>/<house>_หน้า19.png") ต้อง resolve เทียบ root ไม่ใช่ cwd
const REPO_ROOT = path.resolve(__dirname, '../../..');
const fromRoot = (p) => path.resolve(REPO_ROOT, p);

const CFG = {
  SRC_JSON: fromRoot('json_แก้ไขแล้ว'),
  OUT: __dirname,

  // หลังไหนเป็น val (แบ่งตาม "หลัง" ไม่ใช่สุ่มตามหน้า — กันข้อมูลรั่ว)
  VAL_HOUSES: ['04บ้าน_เล็ก_2ชั้น_02'],

  // 'short'       = instruction สั้น ให้ format ฝังในน้ำหนักโมเดล (แนะนำ / default)
  // 'full_schema' = ยัด primary_rawjson_schema.md ทั้งไฟล์เป็น system prompt (~6k tok/example)
  PROMPT_MODE: 'short',

  // ตัดข้อความที่เป็น "บันทึกการทำงาน" ออกจาก confidence_flags / warnings
  // (เช่น "ADDED_2026-07-20_by_user", "t3_reconfirmed_via...", "agent อ่านหน้า07 แล้ว...")
  // ถ้าไม่ตัด โมเดลจะเรียนแต่งวันที่/ชื่อคนมั่ว
  STRIP_WORKLOG: true,

  // ตัด specs{} ออกจาก target ของหน้า plan
  // ⚠️ สำคัญ: ทุก specs{} ในชุดนี้มี spec_source ชี้ไป "หน้าอื่น" (แผ่น section)
  //    เช่น หน้า33 beam plan ของบ้าน04 เอา specs มาจากหน้า37 — ขนาด/จำนวนเหล็กพวกนั้น
  //    ไม่ได้พิมพ์อยู่บนภาพหน้า plan เลย ถ้าเทรนให้ตอบ = สอนโมเดลมโนตัวเลขเหล็กโดยตรง
  //    ซึ่งตรงกับบทเรียนข้อ 2 ใน training-data/CLAUDE.md ที่ VLM พลาดบ่อยที่สุดอยู่แล้ว
  //    การ join spec เข้ากับ position เป็นงานของโค้ดปลายทาง (สเปค §7) ไม่ใช่ของโมเดล
  //    ตั้ง false ถ้ามะขามอยากให้โมเดลตอบ specs ด้วย (กระทบ 10 examples)
  DROP_CROSS_PAGE_SPECS: true,

  // คัดลอกรูปเข้า images/ ให้ self-contained (ปิดได้ถ้าจะ mount โฟลเดอร์ image/ ตรง ๆ)
  COPY_IMAGES: true,
};

// field ที่โมเดล "ดูจากภาพแล้วรู้ไม่ได้" — ต้องตัดทิ้ง ไม่งั้นสอนให้มโน
const DROP_KEYS = new Set([
  // path / ความสัมพันธ์ระหว่างไฟล์ — โมเดลเห็นแค่ภาพ ไม่มีทางรู้
  'source_image', 'source_pages', 'sibling_files', 'grid_source',
  'schema_generation', 'schema_note', 'split_note',
  'last_updated_from_page', 'last_updated_date',
  'corresponding_sheet_in_other_variant',
  // free text ที่เป็น "บันทึกการรีวิว" ไม่ใช่ข้อมูลจากแบบ
  // (ข้อมูลจริงอยู่ใน field ที่มีโครงสร้างข้าง ๆ อยู่แล้ว — ปล่อยไว้โมเดลจะเรียนแต่งเรื่อง)
  'warnings', 'note', 'source', 'meaning', 'building_footprint_note',
  // inventory ของ view ที่ไฟล์ต้นทางบางตัวถืออยู่ (อ้างชื่อไฟล์พี่น้อง) —
  // ซ้ำซ้อนกับ views[] ที่สคริปต์นี้ประกอบเอง และทำให้ path หลุด
  'views',
]);
const DROP_KEY_RE = /_note$/;                       // min_lot_width_note, level_note, ...
const FLAG_KEY_RE = /(^|_)(confidence_)?flags$/;    // confidence_flags, spec_confidence_flags

// wrapper fields ที่เป็นของ "หน้า" ไม่ใช่ของ "view" → ยกขึ้นระดับบน
const PAGE_LEVEL = ['png', 'doc_page', 'discipline', 'sheet_code', 'sheet_name',
  'drawing_no', 'sheet_no', 'sheet_total', 'scale'];

const PROMPT_SHORT = [
  'You are reading one page of a Thai reinforced-concrete (RC) construction drawing set.',
  'Extract everything on the page into JSON following the primary_rawjson_schema.',
  '',
  'Rules:',
  '- Inventory EVERY view/box on the page first, then emit one entry per view in "views".',
  '  A page with a single view still uses "views" with one entry. Never drop a view.',
  '- Each view carries its own "pattern", one of: plan, section, schedule, notes, index,',
  '  material_list, site_plan, side_profile, gridline, title, symbol, roof_plan, misc, unknown.',
  '- Beams: one atomic entry per grid-to-grid segment. main_bar always splits top/bottom',
  '  (and middle when a distinct mid-depth row exists). A circle symbol (Ø) always means RB.',
  '- grid_ref reads row-letter first then column ("A-1"); point elements use a grid_refs array.',
  '- Use null for anything you cannot read clearly. Do not guess.',
  '',
  'Reply with JSON only. No markdown fence, no commentary.',
].join('\n');

// ─────────────────────────────────────────────────────────────
// ข้อความที่เป็นบันทึกกระบวนการรีวิว ไม่ใช่สิ่งที่อ่านได้จากภาพ
const WORKLOG_RE = [
  /20\d\d-\d\d-\d\d/, /\bt[1-4]\b/i,
  /(claude|agent|makham|มะขาม|by[_ ]user|per[_ ]user|reviewer|session|independent read)/i,
  /(RETRACT|SUPERSED|CARRIED[_ ]FORWARD|reconfirm|re-?added|reassess|CASCADE|PENDING)/i,
  /(CORRECTED|CONFIRMED|ADDED|DOWNGRADED|UPGRADED)[_ ]/i,
];
const isWorkLog = (s) => WORKLOG_RE.some((re) => re.test(String(s)));

// ผิดแน่ ๆ ไม่ใช่การตีความ — ใช้เป็นตัวตรวจรั่วท้าย build
// (แยกจาก WORKLOG_RE ที่กว้างกว่า และใช้กรองเฉพาะ flag array ซึ่งเป็น token สั้น ๆ
//  ถ้าเอา WORKLOG_RE มาจับ free text จะโดนคำอังกฤษปกติอย่าง "not independently confirmed")
const HARD_LEAK_RE = [
  /20\d\d-\d\d-\d\d/,
  /\.json\b|\.png\b|mk_test\/|raw_json_|json_แก้ไขแล้ว|image\//,
  /\b(by_user|per_user|claude|makham|มะขาม)\b/i,
];
const isHardLeak = (s) => HARD_LEAK_RE.some((re) => re.test(String(s)));

function clean(node) {
  if (Array.isArray(node)) return node.map(clean).filter((v) => v !== undefined);
  if (node && typeof node === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(node)) {
      if (DROP_KEYS.has(k) || DROP_KEY_RE.test(k)) continue;
      if (CFG.DROP_CROSS_PAGE_SPECS && k === 'specs') continue;
      if (CFG.STRIP_WORKLOG && FLAG_KEY_RE.test(k) && Array.isArray(v)) {
        out[k] = v.filter((x) => !isWorkLog(x));
        continue;
      }
      out[k] = clean(v);
    }
    return out;
  }
  // free text ที่อ้างชื่อไฟล์ข้ามหน้า ("... — see หน้า14_eave_r1.json") — ตัดเฉพาะส่วนอ้างไฟล์
  // ไม่ทิ้งทั้งประโยค เพราะเนื้อความที่เหลือเป็นสิ่งที่อ่านได้จากภาพจริง
  if (typeof node === 'string' && /\.json\b/.test(node))
    return node.replace(/[\s—–-]*\bsee\s+[^\s,;)]+\.json\b/gi, '')
      .replace(/\s*\(?\b[^\s,;()]+\.json\b\)?/g, '').replace(/\s{2,}/g, ' ').trim();
  return node;
}

const houses = fs.readdirSync(CFG.SRC_JSON)
  .filter((f) => fs.statSync(path.join(CFG.SRC_JSON, f)).isDirectory()).sort();

const examples = [];
const problems = [];

for (const house of houses) {
  const dir = path.join(CFG.SRC_JSON, house);
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.json')).sort();

  // group by source_image  (gridline หน้า00 ใช้ source_pages → special case ท้ายลูป)
  const byImage = new Map();
  const gridMasters = [];
  for (const f of files) {
    const j = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    if (!j.source_image) {
      if (Array.isArray(j.source_pages)) gridMasters.push({ f, j });
      else problems.push(`${house}/${f}: ไม่มีทั้ง source_image และ source_pages`);
      continue;
    }
    if (!byImage.has(j.source_image)) byImage.set(j.source_image, []);
    byImage.get(j.source_image).push({ f, j });
  }

  for (const [srcImage, group] of [...byImage.entries()].sort()) {
    // เรียง view ตามเลข _viewN แล้วตามชื่อไฟล์ ให้ผลรันซ้ำได้เหมือนเดิมทุกครั้ง
    group.sort((a, b) => {
      const n = (x) => { const m = x.f.match(/_view(\d+)/); return m ? +m[1] : 0; };
      return n(a) - n(b) || a.f.localeCompare(b.f);
    });

    // ยกขึ้นระดับหน้าเฉพาะ field ที่ทุก view เห็นตรงกัน — ที่ไม่ตรงปล่อยไว้ใน view
    // (เช่น sheet_code ของ BOQ 2 แผ่นใน PNG เดียว ต่างกันถูกแล้วตามสเปค §11)
    const shared = PAGE_LEVEL.filter((k) => {
      const vals = group.map(({ j }) => JSON.stringify(j[k]));
      return vals[0] !== undefined && vals.every((v) => v === vals[0]);
    });
    const page = {};
    for (const k of shared) page[k] = group[0].j[k];

    page.views = group.map(({ j }) => {
      const v = {};
      for (const [k, val] of Object.entries(j)) if (!shared.includes(k)) v[k] = val;
      return clean(v);
    });

    const rel = path.posix.join('images', path.basename(srcImage));
    examples.push({
      id: `${house}::${path.basename(srcImage, '.png')}`,
      house, split: CFG.VAL_HOUSES.includes(house) ? 'val' : 'train',
      images: [rel], srcAbs: [fromRoot(srcImage)],
      target: page,
    });
  }

  // ── special case: หน้า00 grid master (สังเคราะห์จากหลายหน้า → multi-image input)
  for (const { f, j } of gridMasters) {
    const srcs = j.source_pages;
    const missing = srcs.filter((s) => !fs.existsSync(fromRoot(s)));
    if (missing.length) { problems.push(`${house}/${f}: source_pages ชี้ไฟล์ไม่มีจริง ${missing.length} ไฟล์`); continue; }
    examples.push({
      id: `${house}::gridmaster`,
      house, split: CFG.VAL_HOUSES.includes(house) ? 'val' : 'train',
      images: srcs.map((s) => path.posix.join('images', path.basename(s))),
      srcAbs: srcs.map(fromRoot),
      gridMaster: true,
      target: clean(j),
    });
  }
}

// ─────────────────────────────────────────────────────────────
let instruction = PROMPT_SHORT;
if (CFG.PROMPT_MODE === 'full_schema') {
  const spec = fromRoot('raw_json_ตัวที่ใช้งานจริง/00file_for_making_rawjson_from_claude/primary_rawjson_schema.md');
  instruction = fs.readFileSync(spec, 'utf8') + '\n\n' + PROMPT_SHORT;
}
const GRID_SUFFIX = '\n\nThese images are every page of one house that shows grid lines. '
  + 'Build the single house-wide grid master: all named grids plus every dummy grid, '
  + 'each with an id and pos_m read from a printed dimension line.';

if (CFG.COPY_IMAGES) {
  fs.mkdirSync(path.join(CFG.OUT, 'images'), { recursive: true });
  const done = new Set();
  for (const ex of examples)
    ex.srcAbs.forEach((src, i) => {
      const dst = path.join(CFG.OUT, ex.images[i]);
      if (done.has(dst)) return; done.add(dst);
      if (!fs.existsSync(dst)) fs.copyFileSync(src, dst);
    });
  console.log(`คัดลอกรูป: ${done.size} ไฟล์`);
}

const toLine = (ex) => JSON.stringify({
  id: ex.id, house: ex.house,
  messages: [
    {
      role: 'user',
      content: [
        ...ex.images.map((im) => ({ type: 'image', image: im })),
        { type: 'text', text: instruction + (ex.gridMaster ? GRID_SUFFIX : '') },
      ],
    },
    { role: 'assistant', content: [{ type: 'text', text: JSON.stringify(ex.target) }] },
  ],
});

for (const split of ['train', 'val']) {
  const rows = examples.filter((e) => e.split === split);
  fs.writeFileSync(path.join(CFG.OUT, `${split}.jsonl`), rows.map(toLine).join('\n') + '\n', 'utf8');
}

// ── ตรวจรั่ว: ห้ามมีบันทึกการทำงาน/path หลุดเข้า target ที่โมเดลจะเรียน ──
const leaks = [];
for (const ex of examples) {
  const walk = (o, p) => {
    if (Array.isArray(o)) return o.forEach((v) => walk(v, p + '[]'));
    if (o && typeof o === 'object') return Object.entries(o).forEach(([k, v]) => walk(v, p ? p + '.' + k : k));
    if (typeof o === 'string' && isHardLeak(o))
      leaks.push({ id: ex.id, path: p, sample: o.slice(0, 90) });
  };
  walk(ex.target, '');
}
if (leaks.length) {
  const byPath = {};
  leaks.forEach((l) => (byPath[l.path] = (byPath[l.path] || 0) + 1));
  console.log(`\n❌ พบข้อความบันทึกการทำงานหลุดเข้า target ${leaks.length} จุด — แก้ DROP_KEYS/WORKLOG_RE แล้ว build ใหม่:`);
  Object.entries(byPath).sort((a, b) => b[1] - a[1]).slice(0, 15)
    .forEach(([p, n]) => console.log(`   ${String(n).padStart(3)} × ${p}`));
  console.log('   ตัวอย่าง:', leaks[0].sample);
} else {
  console.log('\n✓ ตรวจรั่วผ่าน — ไม่มีวันที่/ชื่อคน/path หลุดเข้า target');
}

// ─────────────────────────────────────────────────────────────
const est = (s) => Math.round(s.length / 3.2);
const stat = (rows) => {
  const out = rows.map((e) => est(JSON.stringify(e.target)));
  out.sort((a, b) => a - b);
  return {
    examples: rows.length,
    images: rows.reduce((a, e) => a + e.images.length, 0),
    output_tok_median: out[Math.floor(out.length / 2)] || 0,
    output_tok_p95: out[Math.floor(out.length * 0.95)] || 0,
    output_tok_max: out[out.length - 1] || 0,
  };
};
const stats = {
  built_at: new Date().toISOString(),
  config: CFG,
  instruction_tok_est: est(instruction),
  train: stat(examples.filter((e) => e.split === 'train')),
  val: stat(examples.filter((e) => e.split === 'val')),
  by_house: Object.fromEntries(houses.map((h) => [h, examples.filter((e) => e.house === h).length])),
  problems,
};
fs.writeFileSync(path.join(CFG.OUT, 'stats.json'), JSON.stringify(stats, null, 2), 'utf8');

console.log(`\ninstruction ≈ ${stats.instruction_tok_est} tok (mode=${CFG.PROMPT_MODE})`);
console.log('train:', JSON.stringify(stats.train));
console.log('val  :', JSON.stringify(stats.val));
if (problems.length) { console.log(`\n⚠️ ปัญหา ${problems.length} จุด:`); problems.slice(0, 20).forEach((p) => console.log('   ', p)); }
else console.log('\n✓ ไม่พบปัญหา');
