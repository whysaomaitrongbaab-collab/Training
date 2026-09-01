/**
 * js/ai/pursonVision.js
 *
 * Client-side entry to Purson — our own fine-tuned drawing-extraction model.
 * Two paths, chosen automatically:
 *  - Queue (mode B / default): upload page images to the 'purson-jobs' storage
 *    bucket, insert a purson_jobs row (RLS-owned), poll until the worker
 *    (server/purson-worker/worker.py) finishes. Result = raw-JSON file set in
 *    the same shape qt_importRawExtractionFiles() accepts.
 *  - Direct (mode A): purson_analyzeSingle() invokes the 'purson-vision' Edge
 *    Function, which forwards ONE call to a stable GPU endpoint when the
 *    PURSON_ENDPOINT_URL secret is configured (503 otherwise).
 */

const BUCKET = 'purson-jobs';
const POLL_MS = 5000;
// 180 × 5 วิ = ทนเน็ตหลุดได้ ~15 นาทีก่อนจะยอมแพ้ (เพดานจริงยังคุมด้วย timeoutMs 4 ชม.)
const MAX_POLL_FAILS = 180;

/**
 * Submit a full-house extraction job.
 * @param {object} opts
 * @param {string} opts.projectId
 * @param {string} [opts.drawingUploadId]
 * @param {Array<{page: number, blob: Blob}>} opts.pages - rendered page images (PNG)
 * @returns {Promise<string>} job id
 */
export async function purson_submitHouseExtract({ projectId, drawingUploadId, pages }) {
  const supabase = await getSupabaseClient();
  if (!supabase) throw new Error('Supabase client not initialized');
  const { data: { user } = {} } = await supabase.auth.getUser();
  if (!user) throw new Error('ต้องเข้าสู่ระบบก่อนใช้ Purson');

  const jobId = crypto.randomUUID();
  const uploaded = [];
  for (const p of pages) {
    const path = `${user.id}/${jobId}/page_${String(p.page).padStart(2, '0')}.png`;
    const { error } = await supabase.storage.from(BUCKET)
      .upload(path, p.blob, { contentType: 'image/png' });
    if (error) throw new Error(`อัปโหลดหน้า ${p.page} ไม่สำเร็จ: ${error.message}`);
    uploaded.push({ page: p.page, path });
  }

  const { error } = await supabase.from('purson_jobs').insert({
    id: jobId,
    project_id: projectId ?? null,
    drawing_upload_id: drawingUploadId ?? null,
    job_type: 'house_extract',
    payload: { pages: uploaded },
  });
  if (error) throw new Error(`สร้างงานไม่สำเร็จ: ${error.message}`);
  return jobId;
}

/** Read one job row (status/progress/result). */
export async function purson_getJob(jobId) {
  const supabase = await getSupabaseClient();
  const { data, error } = await supabase.from('purson_jobs')
    .select('id,status,progress,result,error_message,updated_at')
    .eq('id', jobId).single();
  if (error) throw new Error(error.message);
  return data;
}

/**
 * Poll until the job finishes. onProgress receives the progress jsonb each tick.
 * @returns {Promise<object>} result jsonb ({files, warnings, timings})
 */
export async function purson_waitForJob(jobId, { onProgress, timeoutMs = 4 * 3600 * 1000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let netFails = 0;
  for (;;) {
    let job;
    try {
      job = await purson_getJob(jobId);
      netFails = 0;
    } catch (e) {
      // เน็ตสะดุด ≠ งานพัง — worker ยังทำงานต่ออยู่ฝั่งโน้น ถ้าโยน error ทันที
      // ผู้ใช้จะเห็น "ล้มเหลว" ทั้งที่อีกฝั่งกำลังวิ่งอยู่ และไม่มีทางกลับเข้าไปดูได้อีก
      // ไม่เรียก onProgress ตอนพลาด — ให้ UI ค้างค่าล่าสุดไว้ ดีกว่าไปกวน ETA ให้เพี้ยน
      if (++netFails > MAX_POLL_FAILS) {
        throw new Error(`ติดต่อ Supabase ไม่ได้ ${netFails} ครั้งติดกัน: ${e.message}`);
      }
      await new Promise((r) => setTimeout(r, POLL_MS));
      continue;
    }
    if (onProgress && job.progress) onProgress(job.progress);
    if (job.status === 'done') return job.result;
    if (job.status === 'failed') throw new Error(job.error_message || 'งาน Purson ล้มเหลว');
    if (Date.now() > deadline) throw new Error('รอผล Purson นานเกินกำหนด');
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}

/**
 * One direct model call via the Edge Function (mode A only; 503 = no endpoint,
 * caller should use the queue instead).
 * @param {Array<{data: string, mime_type?: string}>} images - base64, no data: prefix
 */
export async function purson_analyzeSingle(images, promptText) {
  const supabase = await getSupabaseClient();
  const { data, error } = await supabase.functions.invoke('purson-vision', {
    body: { action: 'single', images, prompt: promptText },
  });
  if (error) throw new Error(error.message || 'Purson request failed');
  return data;
}

async function getSupabaseClient() {
  if (globalThis.supabase) return globalThis.supabase;
  try {
    const mod = await import('../../supabase.js');
    globalThis.supabase = mod.supabase || null;
    return globalThis.supabase;
  } catch {
    return null;
  }
}

// guard ตาม convention ของ repo (bbs-index.js:1495 ฯลฯ) — ไม่ guard แล้วไฟล์เทสที่
// import ต่อกันมาถึงตัวนี้จะตายด้วย "window is not defined" ใน node
if (typeof window !== 'undefined') {
  window.purson_submitHouseExtract = purson_submitHouseExtract;
  window.purson_waitForJob = purson_waitForJob;
}
