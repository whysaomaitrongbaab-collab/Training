/**
 * js/drawing/drawing-purson.js — ปุ่ม "ถอดแบบด้วย Destrier" ใน Drawing Intelligence
 * (ชื่อโมเดล/โมดูลภายในยังเป็น purson ทุกที่ — Destrier คือชื่อที่โชว์ผู้ใช้เท่านั้น)
 *
 * เส้นทาง: render ทุกหน้า PDF เป็น PNG → ส่งงานเข้าคิว Supabase (pursonVision.js) →
 * worker บน PC/เครื่องเช่ารัน pass0+pass2 → ได้ raw-JSON กลับ → เข้า "หน้าติ๊กเลือก"
 * เดียวกับปุ่มนำเข้าไฟล์มือทุกประการ (qt_showRawPreviewFromTexts) — คนตรวจก่อนบันทึกเสมอ
 *
 * ปุ่มนี้ใช้ได้ต่อเมื่อ worker กำลังรันอยู่ — ถ้าไม่มี worker งานจะค้าง pending จน
 * timeout ข้อความบอกผู้ใช้ตรงๆ ไม่เดา
 */
import { purson_submitHouseExtract, purson_waitForJob } from '../ai/pursonVision.js';
import { qt_showRawPreviewFromTexts, escapeHtml } from './raw-extraction-import.js';
import { getCurrentProjectId } from '../shared/project-store.js';

// โมเดลเทรนที่ความละเอียดเต็ม (~2339×1654) — scale 2.5 ให้ภาพใกล้เคียง อย่าลดต่ำกว่านี้
// (บทเรียน t01: ภาพโดนย่อเงียบๆ = ผลพังทั้งรอบโดยไม่มี error)
const RENDER_SCALE = 2.5;

async function renderPagesToPngBlobs(file) {
  if (typeof pdfjsLib === 'undefined') throw new Error('pdfjsLib not loaded');
  const toBlob = (canvas) => new Promise((res, rej) =>
    canvas.toBlob(b => (b ? res(b) : rej(new Error('toBlob failed'))), 'image/png'));

  if (file.type !== 'application/pdf') {
    return [{ page: 1, blob: file }];
  }
  const ab = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: ab }).promise;
  const pages = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const vp = page.getViewport({ scale: RENDER_SCALE });
    const canvas = document.createElement('canvas');
    canvas.width = vp.width;
    canvas.height = vp.height;
    await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp }).promise;
    pages.push({ page: i, blob: await toBlob(canvas) });
  }
  return pages;
}

function setStatus(html) {
  const box = document.getElementById('raw-import-result');
  if (box) box.innerHTML = html;
}

// ลำดับขั้นของงานถอดแบบทั้งเส้น — 3 ขั้นแรกฝั่งเบราว์เซอร์, 3 ขั้นหลังตรงกับ
// step ที่ worker.py เขียนลง progress ({step: 'download'|'pass0'|'pass2'})
const PURSON_STEPS = [
  ['prep', 'แปลงหน้าแบบเป็นรูป'],
  ['upload', 'อัปโหลดเข้าคิว'],
  ['wait', 'รอ worker รับงาน'],
  ['download', 'worker ดาวน์โหลดรูป'],
  ['pass0', 'จำแนกว่าแต่ละหน้าคือแบบอะไร'],
  ['pass2', 'อ่านเนื้อหาทีละหน้า'],
  ['pass3', 'วัดระยะเทียบผังกริด'],
];

// วินาทีต่อหน่วยงาน วัดจริงบนการ์ดเช่า RTX PRO 6000 (op04 + e2e 2026-08-31 —
// ดู destrier_test_house/results/*/timings.json) · ใช้ประมาณเวลาที่เหลือเท่านั้น
// เครื่องอื่น/โมเดลอื่นตัวเลขจะเลื่อนตามกัน ตัวเลขนี้จึงเป็น "ประมาณ" เสมอ
const SEC = { download: 2, pass0: 32, gridline: 250, pass2: 167 };

function fmtDuration(s) {
  if (!Number.isFinite(s) || s < 0) return '';
  const m = Math.round(s / 60);
  if (m < 1) return `${Math.round(s)} วิ`;
  if (m < 60) return `${m} นาที`;
  return `${Math.floor(m / 60)} ชม. ${m % 60} นาที`;
}

/** ประมาณวินาทีที่เหลือจาก progress ปัจจุบัน — คืน null เมื่อยังเดาไม่ได้อย่างมีเหตุผล */
export function estimateRemainingSec(p = {}) {
  const pages = Number(p.pages) || 0;
  if (!pages) return null;
  const tasks = Number(p.tasks) || 0;
  const done = Number(p.done) || 0;
  const total = Number(p.total) || 0;
  // งานที่ยังไม่รู้จำนวนจริง (ก่อน pass0 จบ) เดาว่า 1 หน้า ≈ 1 งาน pass2
  const pass2Units = tasks || pages;
  // ขั้นที่ผ่านไปแล้วต้องเป็น 0 เสมอ — ตัดสินจากลำดับขั้น ไม่ใช่ if ทีละตัว (เดิมพอถึง
  // pass3 ตัว pass2 ตกไปเข้า else แล้วเด้งกลับเป็นเวลาเต็ม = ETA พุ่งตอนใกล้เสร็จ)
  const at = PURSON_STEPS.findIndex(([k]) => k === p.step);
  const stepIdx = (key) => PURSON_STEPS.findIndex(([k]) => k === key);
  const remain = (key, ifCurrent, ifFuture) =>
    at > stepIdx(key) ? 0 : at === stepIdx(key) ? ifCurrent : ifFuture;
  const left = {
    download: remain('download', Math.max(0, pages - done), pages),
    pass0: remain('pass0', Math.max(0, pages - done), pages),
    pass2: remain('pass2', Math.max(0, total - done), pass2Units),
  };
  return Math.round(left.download * SEC.download + left.pass0 * SEC.pass0
    + left.pass2 * SEC.pass2);
}

// CSS ฉีดครั้งเดียว — อยู่ในไฟล์นี้เพราะเป็นของกล่องนี้ล้วนๆ ไม่มีใครใช้ร่วม
// (ใช้ currentColor + rgba กลางๆ จะได้ไม่ต้องเดาชื่อ token ของธีมมืด/สว่าง)
const PROGRESS_CSS = `
.dz-card{border:1px solid rgba(128,140,150,.28);border-radius:12px;padding:14px 16px;
  background:rgba(128,140,150,.06)}
.dz-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:2px}
.dz-title{font-weight:700;font-size:14px;letter-spacing:.2px}
.dz-pct{font-size:22px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1}
.dz-now{font-size:12px;opacity:.75;margin-bottom:10px}
.dz-bar{height:8px;border-radius:99px;background:rgba(128,140,150,.22);overflow:hidden}
.dz-bar>span{display:block;height:100%;border-radius:99px;background:#2066DF;
  background-image:linear-gradient(90deg,#2066DF,#4d8dff,#2066DF);background-size:200% 100%;
  transition:width .45s cubic-bezier(.4,0,.2,1);animation:dz-flow 2.2s linear infinite}
@keyframes dz-flow{to{background-position:-200% 0}}
.dz-steps{margin:12px 0 0;padding:0;list-style:none;position:relative}
.dz-steps:before{content:"";position:absolute;left:6px;top:8px;bottom:8px;width:2px;
  background:rgba(128,140,150,.25)}
.dz-step{position:relative;padding:3px 0 3px 22px;font-size:12.5px;line-height:1.6;opacity:.45}
.dz-step:before{content:"";position:absolute;left:1px;top:9px;width:11px;height:11px;
  border-radius:50%;background:rgba(128,140,150,.35);box-shadow:0 0 0 3px rgba(0,0,0,0)}
.dz-step.is-done{opacity:.7}
.dz-step.is-done:before{background:#22a06b}
.dz-step.is-now{opacity:1;font-weight:600}
.dz-step.is-now:before{background:#2066DF;animation:dz-pulse 1.4s ease-out infinite}
@keyframes dz-pulse{0%{box-shadow:0 0 0 0 rgba(32,102,223,.5)}
  100%{box-shadow:0 0 0 7px rgba(32,102,223,0)}}
.dz-sub{font-size:11.5px;opacity:.7;font-weight:400}
.dz-facts{margin-top:10px;padding-top:9px;border-top:1px solid rgba(128,140,150,.2);
  font-size:11.5px;opacity:.8;display:flex;flex-wrap:wrap;gap:4px 12px}
.dz-p3{margin:8px 0 2px;padding:9px 11px;border-radius:9px;font-size:12px;
  border:1px solid rgba(34,160,107,.35);background:rgba(34,160,107,.08)}
.dz-p3 b{font-weight:700}
@media (prefers-reduced-motion:reduce){
  .dz-bar>span{animation:none;transition:none}.dz-step.is-now:before{animation:none}}
`;

function ensureProgressCss() {
  if (typeof document === 'undefined' || document.getElementById('dz-progress-css')) return;
  const s = document.createElement('style');
  s.id = 'dz-progress-css';
  s.textContent = PROGRESS_CSS;
  document.head.appendChild(s);
}

/** สรุปผล pass3 ให้คนอ่านรู้เรื่อง — ตัวเลขจริงจาก pass3_measure.json ไม่ตีความเกิน */
export function pass3Stats(report = {}) {
  const pages = Object.values(report.pages || {});
  const ok = pages.filter(r => r && r.ok);
  const scales = ok.map(r => r.transform?.px_per_m_x).filter(Number.isFinite);
  return {
    pagesOk: ok.length,
    pagesTotal: pages.length,
    cvOnly: pages.reduce((n, r) => n + (r.cv_only?.length || 0), 0),
    offGrid: pages.reduce((n, r) => n + (r.grid_check?.length || 0), 0),
    pxPerM: scales.length ? Math.round(scales.reduce((a, b) => a + b, 0) / scales.length) : null,
    // ความคลาดสูงสุดของการ fit ทั้งชุด = ตัวบอกว่าเชื่อระยะที่วัดได้แค่ไหน
    worstResidualM: ok.length
      ? Math.max(...ok.map(r => r.transform?.residual_max_m ?? 0)) : null,
  };
}

function renderPass3Summary(report) {
  const s = pass3Stats(report);
  if (!s.pagesTotal) return '';
  if (!s.pagesOk) {
    return '<div class="dz-p3" style="border-color:rgba(200,140,40,.4);'
      + 'background:rgba(200,140,40,.08)">📐 <b>วัดระยะไม่ได้</b> — หมุดไม่พอ หรือ grid_ref '
      + 'ไม่ตรงกับตำแหน่งจริง (เหตุผลรายหน้าอยู่ใน console: pass3 measure)</div>';
  }
  const bits = [
    `วัดได้ ${s.pagesOk}/${s.pagesTotal} หน้า`,
    s.pxPerM ? `มาตราส่วน ~${s.pxPerM} px ต่อเมตร` : '',
    s.worstResidualM !== null ? `คลาดสูงสุด ${s.worstResidualM.toFixed(2)} ม.` : '',
    s.cvOnly ? `⚠️ CV เห็นอีก ${s.cvOnly} จุดที่ AI ไม่ได้ตอบ` : '',
    s.offGrid ? `⚠️ ตำแหน่งไม่ตรงกริด ${s.offGrid} ตัว` : '',
  ].filter(Boolean);
  return `<div class="dz-p3">📐 <b>pass3 วัดระยะจากผังกริด</b> — ${escapeHtml(bits.join(' · '))}</div>`;
}

/**
 * กล่องสถานะระหว่างถอดแบบ — การ์ด + ไทม์ไลน์ขั้นตอน + แถบ % เคลื่อนไหว
 * ทุกค่าที่มาจาก worker ผ่าน escapeHtml ก่อนเสมอ
 */
function renderPursonProgress(p = {}) {
  const { step, done = 0, total = 0, note = '' } = p;
  const idx = PURSON_STEPS.findIndex(([k]) => k === step);
  const currentLabel = idx >= 0 ? PURSON_STEPS[idx][1] : 'เริ่มงาน';
  const rows = PURSON_STEPS.map(([, label], i) => {
    const cls = i < idx ? 'is-done' : i === idx ? 'is-now' : '';
    const count = i === idx && total ? ` — ${escapeHtml(done)}/${escapeHtml(total)}` : '';
    const sub = i === idx && note ? `<div class="dz-sub">${escapeHtml(note)}</div>` : '';
    return `<li class="dz-step ${cls}">${label}${count}${sub}</li>`;
  }).join('');

  const eta = estimateRemainingSec(p);
  const elapsed = Number(p.elapsed_s) || 0;
  // % จาก done/total ของ pass ปัจจุบันถ้ามี (แม่นสุด) ไม่งั้นเดาจาก elapsed/(elapsed+eta)
  // (ใช้ตัวเลขเดียวกับที่ทำ ETA อยู่แล้ว ไม่คำนวณซ้ำสูตรใหม่) ไม่มีข้อมูลเลย (ยังไม่มี worker
  // รับงาน) แสดง 0% ตรงๆ — ไม่เดาว่าคืบหน้าไปแล้วทั้งที่ยังไม่มีใครทำอะไรจริง
  let pct = total ? Math.round((done / total) * 100) : null;
  if (pct === null) {
    pct = (elapsed && eta !== null && elapsed + eta > 0)
      ? Math.round((elapsed / (elapsed + eta)) * 100) : 0;
  }
  const facts = [
    elapsed ? `ผ่านไป ${fmtDuration(elapsed)}` : '',
    eta ? `เหลืออีกประมาณ ${fmtDuration(eta)}` : '',
    Number(p.elements) ? `อ่านได้แล้ว ${escapeHtml(p.elements)} ชิ้น` : '',
    Number(p.warnings) ? `⚠️ ${escapeHtml(p.warnings)} คำเตือน` : '',
  ].filter(Boolean).map(f => `<span>${f}</span>`).join('');

  ensureProgressCss();
  return `<div class="dz-card">
      <div class="dz-head">
        <span class="dz-title">🤖 Destrier กำลังถอดแบบ</span>
        <span class="dz-pct">${pct}%</span>
      </div>
      <div class="dz-now">ตอนนี้: ${escapeHtml(currentLabel)}</div>
      <div class="dz-bar"><span style="width:${pct}%"></span></div>
      <ul class="dz-steps">${rows}</ul>
      ${facts ? `<div class="dz-facts">${facts}</div>` : ''}
    </div>`;
}

/**
 * แจ้งเตือนตอนงานเสร็จ — งานนี้กิน 10-30 นาที ผู้ใช้สลับแท็บไปทำอย่างอื่นแน่นอน
 * ทั้งแอปยังไม่เคยมีการแจ้งข้ามแท็บเลย (สำรวจแล้ว 2026-08-31) นี่คือที่แรก
 * เงียบไว้ก่อนถ้าผู้ใช้ยังอยู่หน้านี้ — เด้ง title เฉพาะตอนแท็บถูกซ่อนจริง
 */
function notifyDone(text) {
  if (!document.hidden) return;
  const original = document.title;
  let on = true;
  const timer = setInterval(() => {
    document.title = (on = !on) ? original : `✅ ${text}`;
  }, 1200);
  const stop = () => {
    clearInterval(timer);
    document.title = original;
    document.removeEventListener('visibilitychange', stop);
  };
  document.addEventListener('visibilitychange', stop);
  setTimeout(stop, 120000);   // กันค้างถ้าไม่มีใครกลับมาดู
}

export async function qt_runPurson() {
  const file = globalThis.qt_selectedFile;
  if (!file) { alert('เลือกไฟล์แบบก่อน'); return; }
  const btn = document.getElementById('purson-btn');
  const btnLabel = btn ? btn.textContent : '';
  if (btn) { btn.disabled = true; btn.textContent = '⏳ กำลังถอดแบบ...'; }

  const t0 = Date.now();
  try {
    setStatus(renderPursonProgress({ step: 'prep' }));
    const pages = await renderPagesToPngBlobs(file);

    setStatus(renderPursonProgress({ step: 'upload', total: pages.length, pages: pages.length }));
    const jobId = await purson_submitHouseExtract({
      projectId: getCurrentProjectId(),
      pages,
    });

    // ถ้าไม่มี worker รันอยู่ งานจะค้างที่ขั้นนี้จน timeout — บอกตรงๆ ไม่เดาแทนผู้ใช้
    setStatus(renderPursonProgress({ step: 'wait', pages: pages.length })
      + '<div style="color:var(--color-text-secondary,#5E696E);font-size:12px;margin-top:4px">'
      + 'ถ้าไม่มี worker รันอยู่ งานจะค้างจน timeout</div>');
    const result = await purson_waitForJob(jobId, {
      // worker รุ่นเก่าส่งแค่ {step,done,total,note} — คีย์เสริมที่ไม่มีจะเป็น undefined
      // แล้ว renderPursonProgress ข้ามเองทุกจุด (ETA/นับชิ้นหายไปเฉยๆ ไม่พัง)
      onProgress: (p) => setStatus(renderPursonProgress({ ...p, pages: p.pages ?? pages.length })),
    });

    // .json = ผลที่ parse ได้ → เข้าหน้าติ๊กเลือก · .raw.txt = JSON เสียจากโมเดล เก็บไว้ดูใน console
    // ไฟล์ CV (cv15_/cv25_/pass3_measure) ไม่ใช่ raw-extraction pattern — ส่งเข้า adapter
    // จะได้ warning "pattern ไม่รู้จัก" เปล่าๆ · แยกออกมาสรุปเป็นบรรทัดเดียวแทน
    const isSidecar = (n) => /^(cv15_|cv25_|pass3_measure\.json$)/.test(n);
    const fileTexts = (result.files || [])
      .filter(f => f.name.endsWith('.json') && !isSidecar(f.name))
      .map(f => ({ name: f.name, text: JSON.stringify(f.json) }));
    const broken = (result.files || []).filter(f => f.name.endsWith('.raw.txt'));
    const pass3 = (result.files || []).find(f => f.name === 'pass3_measure.json');
    if (broken.length) console.warn('[purson] งานที่ JSON เสีย:', broken);
    if (pass3) console.log('[purson] pass3 measure:', pass3.json);
    console.log('[purson] warnings:', result.warnings);

    if (!fileTexts.length) {
      setStatus('❌ Destrier ไม่ได้ผลลัพธ์ที่ใช้ได้เลยสักไฟล์ — ดู warnings ใน console');
      notifyDone('Destrier ไม่ได้ผลลัพธ์');
      return;
    }
    const took = fmtDuration((Date.now() - t0) / 1000);
    const noteHTML = `<div style="margin-bottom:6px;color:var(--color-text-secondary,#5E696E)">`
      + `✅ ถอดแบบเสร็จใน ${escapeHtml(took)} · ได้ ${escapeHtml(fileTexts.length)} ไฟล์`
      + ((result.warnings?.length || broken.length)
        ? ` · ⚠️ คำเตือน ${escapeHtml((result.warnings || []).length)} รายการ · JSON เสีย ${
            escapeHtml(broken.length)} งาน (ดูใน console)` : '')
      + `</div>${pass3 ? renderPass3Summary(pass3.json) : ''}`;
    qt_showRawPreviewFromTexts(fileTexts, noteHTML);
    notifyDone(`ถอดแบบเสร็จ ${fileTexts.length} ไฟล์`);
  } catch (err) {
    console.error('[purson] failed', err);
    setStatus(`❌ Destrier ไม่สำเร็จ: ${escapeHtml(err.message)}`);
    notifyDone('Destrier ไม่สำเร็จ');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = btnLabel; }
  }
}

// guard ตาม convention ของ repo (bbs-index.js:1495 ฯลฯ) — ให้ tests/ import ได้ใน node
if (typeof window !== 'undefined') window.qt_runPurson = qt_runPurson;
