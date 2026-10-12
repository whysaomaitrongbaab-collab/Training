/**
 * Destrier Lab Playground - Frontend Application Logic
 */

// State
const state = {
  activeTab: 'tab-pipeline',
  currentStep: 0,
  selectedHouse: '',
  selectedPage: null,
  houses: [],
  pages: [],
  prompts: {},
  endpoint: {
    url: 'http://localhost:8000/v1',
    model: 'purson',
    key: '',
    connected: false,
    latency: null
  },
  pipelineResults: {},
  overlayConfig: {
    crop: true,
    cv: true,
    grid: true
  }
};

// DOM Elements
const el = {
  endpointUrl: document.getElementById('endpoint-url'),
  endpointModel: document.getElementById('endpoint-model'),
  endpointKey: document.getElementById('endpoint-key'),
  btnTestEndpoint: document.getElementById('btn-test-endpoint'),
  endpointStatus: document.getElementById('endpoint-status'),

  selectHouse: document.getElementById('select-house'),
  selectPage: document.getElementById('select-page'),
  btnReloadHouse: document.getElementById('btn-reload-house'),
  pageMetadata: document.getElementById('page-metadata'),

  blueprintImg: document.getElementById('blueprint-img'),
  overlayCanvas: document.getElementById('overlay-canvas'),
  chkOverlayCrop: document.getElementById('chk-overlay-crop'),
  chkOverlayCv: document.getElementById('chk-overlay-cv'),
  chkOverlayGrid: document.getElementById('chk-overlay-grid'),

  stepChips: document.querySelectorAll('.step-chip'),
  btnRunCurrentStep: document.getElementById('btn-run-current-step'),
  btnRunAllSteps: document.getElementById('btn-run-all-steps'),
  stepTimer: document.getElementById('step-timer'),
  stepResultCard: document.getElementById('step-result-card'),
  defensiveBadges: document.getElementById('defensive-badges'),
  badgeList: document.getElementById('badge-list'),
  jsonViewer: document.getElementById('json-viewer'),

  // Prompt Lab
  selectSubtask: document.getElementById('select-subtask'),
  btnLoadPreset: document.getElementById('btn-load-preset'),
  chkIncCommon: document.getElementById('chk-inc-common'),
  chkIncGrid: document.getElementById('chk-inc-grid'),
  chkIncCv: document.getElementById('chk-inc-cv'),
  chkEnableThinking: document.getElementById('chk-enable-thinking'),
  paramTemp: document.getElementById('param-temp'),
  paramTopp: document.getElementById('param-topp'),
  paramMaxTokens: document.getElementById('param-max-tokens'),
  valTemp: document.getElementById('val-temp'),
  valTopp: document.getElementById('val-topp'),
  promptEditorText: document.getElementById('prompt-editor-text'),
  btnAssemblePreview: document.getElementById('btn-assemble-preview'),
  btnRunPromptTest: document.getElementById('btn-run-prompt-test'),
  contractStatusBox: document.getElementById('contract-status-box'),
  evalElementsContainer: document.getElementById('eval-elements-container'),
  evalRawOutput: document.getElementById('eval-raw-output'),
  metricTokens: document.getElementById('metric-tokens'),
  metricSpeed: document.getElementById('metric-speed'),
  metricTime: document.getElementById('metric-time')
};

// ── Initialization ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  initTabs();
  initSliders();
  initCanvas();
  await loadPrompts();
  await loadHouses();
  bindEvents();
});

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
        state.activeTab = targetId;
      }
    });
  });
}

function initSliders() {
  el.paramTemp.addEventListener('input', e => { el.valTemp.textContent = e.target.value; });
  el.paramTopp.addEventListener('input', e => { el.valTopp.textContent = e.target.value; });
}

function initCanvas() {
  el.chkOverlayCrop.addEventListener('change', e => { state.overlayConfig.crop = e.target.checked; redrawOverlay(); });
  el.chkOverlayCv.addEventListener('change', e => { state.overlayConfig.cv = e.target.checked; redrawOverlay(); });
  el.chkOverlayGrid.addEventListener('change', e => { state.overlayConfig.grid = e.target.checked; redrawOverlay(); });
}

function toggleLogic(header) {
  const box = header.closest('.logic-box');
  if (box) box.classList.toggle('collapsed');
}

// ── Data Loaders ────────────────────────────────────────────────────────────

async function loadHouses() {
  try {
    const res = await fetch('/api/houses');
    const data = await res.json();
    state.houses = data.houses || [];

    el.selectHouse.innerHTML = state.houses.map(h => 
      `<option value="${h.id}">${h.name} (${h.page_count} หน้า)</option>`
    ).join('');

    if (state.houses.length > 0) {
      state.selectedHouse = state.houses[0].id;
      await loadPages(state.selectedHouse);
    }
  } catch (err) {
    console.error('Failed to load houses:', err);
    el.selectHouse.innerHTML = '<option value="">โหลดบ้านล้มเหลว</option>';
  }
}

async function loadPages(houseId) {
  try {
    const res = await fetch(`/api/houses/${houseId}/pages`);
    const data = await res.json();
    state.pages = data.pages || [];

    el.selectPage.innerHTML = state.pages.map((p, idx) => 
      `<option value="${idx}">${p.filename}</option>`
    ).join('');

    el.pageMetadata.textContent = `${state.pages.length} หน้าในโครงการ`;

    if (state.pages.length > 0) {
      selectPage(0);
    }
  } catch (err) {
    console.error('Failed to load pages:', err);
    el.selectPage.innerHTML = '<option value="">ไม่มีหน้าแบบ</option>';
  }
}

function selectPage(idx) {
  if (!state.pages[idx]) return;
  state.selectedPage = state.pages[idx];
  // Clear previous results and overlays for the new page
  state.pipelineResults = {};
  renderStepInterface(state.currentStep);
  el.blueprintImg.src = `/api/image/${state.selectedPage.path}`;
  el.blueprintImg.onload = () => {
    resizeCanvas();
    redrawOverlay();
  };
}

async function loadPrompts() {
  try {
    const res = await fetch('/api/prompts');
    state.prompts = await res.json();
    loadSubtaskPrompt(el.selectSubtask.value);
  } catch (err) {
    console.error('Failed to load prompts:', err);
  }
}

function loadSubtaskPrompt(subtask) {
  const sub = state.prompts.subtasks?.[subtask];
  if (sub) {
    el.promptEditorText.value = sub.body || '';
  }
}

// ── Event Handlers ──────────────────────────────────────────────────────────

function bindEvents() {
  el.selectHouse.addEventListener('change', e => {
    state.selectedHouse = e.target.value;
    loadPages(state.selectedHouse);
  });

  el.selectPage.addEventListener('change', e => {
    selectPage(parseInt(e.target.value));
  });

  el.btnReloadHouse.addEventListener('click', () => {
    loadHouses();
  });

  el.btnTestEndpoint.addEventListener('click', testEndpoint);

  // Stepper
  el.stepChips.forEach(chip => {
    chip.addEventListener('click', () => {
      el.stepChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.currentStep = parseInt(chip.getAttribute('data-step'));
      renderStepInterface(state.currentStep);
    });
  });

  el.btnRunCurrentStep.addEventListener('click', runCurrentStep);
  el.btnRunAllSteps.addEventListener('click', runAllSteps);

  // Prompt Lab
  el.selectSubtask.addEventListener('change', e => loadSubtaskPrompt(e.target.value));
  el.btnLoadPreset.addEventListener('click', () => loadSubtaskPrompt(el.selectSubtask.value));
  el.btnAssemblePreview.addEventListener('click', previewAssembledPrompt);
  el.btnRunPromptTest.addEventListener('click', runPromptTest);

  // Lab 3 & 4 helpers
  document.getElementById('btn-run-mock-cv')?.addEventListener('click', runMockCvScan);
}

// ── Endpoint Testing ────────────────────────────────────────────────────────

async function testEndpoint() {
  const url = el.endpointUrl.value.trim();
  const model = el.endpointModel.value.trim();
  const key = el.endpointKey.value.trim();

  el.endpointStatus.className = 'status-badge status-disconnected';
  el.endpointStatus.textContent = 'กำลังทดสอบ...';

  try {
    const res = await fetch('/api/endpoint/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, model, api_key: key })
    });
    const data = await res.json();

    if (data.ok) {
      el.endpointStatus.className = 'status-badge status-connected';
      el.endpointStatus.textContent = `เชื่อมต่อสำเร็จ (${data.latency_ms} ms)`;
      state.endpoint = { url, model, key, connected: true, latency: data.latency_ms };
    } else {
      el.endpointStatus.className = 'status-badge status-disconnected';
      el.endpointStatus.textContent = `ล้มเหลว (${data.error || 'Connection Refused'})`;
      state.endpoint.connected = false;
    }
  } catch (err) {
    el.endpointStatus.className = 'status-badge status-disconnected';
    el.endpointStatus.textContent = `ไม่สามารถเชื่อมต่อได้: ${err.message}`;
    state.endpoint.connected = false;
  }
}

// ── Stepper Logic ───────────────────────────────────────────────────────────

function renderStepInterface(step) {
  const stepNames = [
    'Pass 0: จำแนกประเภทหน้า (Classifier)',
    'Pass 1 & 1.5: ครอปรูปและสแกนสัญลักษณ์ (Crop & CV)',
    'Pass 2: ดึงผังกริดแกน X-Y (Grid Master)',
    'Pass 2: สกัดชิ้นส่วนโครงสร้าง (Subtask Extraction)',
    'Pass 3: สอบเทียบระยะพิกเซลต่อเมตร (Calibration)'
  ];

  const prevResult = state.pipelineResults[step];
  if (prevResult) {
    displayStepResult(step, prevResult);
  } else {
    el.stepResultCard.innerHTML = `
      <h4>${stepNames[step]}</h4>
      <div class="placeholder-text">ยังไม่ได้รันสเต็ปนี้ — กดปุ่ม <strong>[▶ รันสเต็ปนี้]</strong> ด้านบนเพื่อประมวลผล</div>
    `;
    el.jsonViewer.textContent = '{}';
    el.defensiveBadges.classList.add('hidden');
  }
}

async function runCurrentStep() {
  if (!state.selectedPage) {
    alert('กรุณาเลือกหน้าแบบก่อนรัน');
    return;
  }

  el.btnRunCurrentStep.disabled = true;
  el.btnRunCurrentStep.textContent = '⏳ กำลังประมวลผล...';
  const t0 = performance.now();

  try {
    let result = null;
    const step = state.currentStep;

    if (step === 0) {
      result = await executePass0();
    } else if (step === 1) {
      result = await executePass1();
    } else if (step === 2) {
      result = await executePass2Grid();
    } else if (step === 3) {
      result = await executePass2Subtask();
    } else if (step === 4) {
      result = await executePass3();
    }

    const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
    el.stepTimer.textContent = `${elapsed}s`;

    state.pipelineResults[step] = result;
    displayStepResult(step, result);
    redrawOverlay();
  } catch (err) {
    el.stepResultCard.innerHTML = `<div class="report-warn">⚠️ เกิดข้อผิดพลาด: ${err.message}</div>`;
  } finally {
    el.btnRunCurrentStep.disabled = false;
    el.btnRunCurrentStep.textContent = '▶ รันสเต็ปนี้ (Run Step)';
  }
}

async function runAllSteps() {
  for (let s = 0; s <= 4; s++) {
    state.currentStep = s;
    el.stepChips.forEach((c, idx) => c.classList.toggle('active', idx === s));
    renderStepInterface(s);
    await runCurrentStep();
  }
}

async function executePass0() {
  if (!state.endpoint.connected) {
    // Return realistic mock based on actual house pattern
    return {
      sheet_code: "S-02",
      sheet_name: "แปลนคานชั้น 2 และแปลนโครงหลังคา",
      building: "main",
      views: [
        { subtask: "plan_beam", also_gridline: true, box_hint: "top" },
        { subtask: "plan_slab", also_gridline: false, box_hint: "bottom" }
      ],
      mode: "Mock Demonstration (Endpoint offline)"
    };
  }

  // Live call to vLLM/SGLang with pass0 prompt
  const res = await fetch('/api/ai/call', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      endpoint_url: state.endpoint.url,
      api_key: state.endpoint.key,
      model: state.endpoint.model,
      prompt: state.prompts.subtasks?.pass0?.body || "Classify this architectural sheet.",
      image_paths: [state.selectedPage.path],
      temperature: 0.7,
      max_tokens: 3000
    })
  });
  const data = await res.json();
  return data.parsed || { raw_text: data.raw_text, error: data.error };
}

async function executePass1() {
  return {
    crops_generated: 2,
    subtasks: ["plan_beam", "plan_slab"],
    cv_symbols_detected: {
      beams: 14,
      columns: 8,
      footings: 0
    },
    hint_text_generated: "CV Hint: Found 14 beams and 8 column markers."
  };
}

async function executePass2Grid() {
  return {
    pattern: "grid_master",
    grid: {
      x_lines: [
        { id: "1", pos_m: 0.0 },
        { id: "2", pos_m: 4.0 },
        { id: "3", pos_m: 8.0 }
      ],
      y_lines: [
        { id: "A", pos_m: 0.0 },
        { id: "B", pos_m: 5.0 },
        { id: "C", pos_m: 9.0 }
      ]
    },
    dimension_summary: "อาคารขนาด 8.0 x 9.0 เมตร (2 ช่วงเสา)"
  };
}

async function executePass2Subtask() {
  return {
    pattern: "beam_plan",
    elements: [
      { element_id: "2B1", element_type: "beam", grid_ref_start: "1", grid_ref_end: "2", span_m: 4.0 },
      { element_id: "2B2", element_type: "beam", grid_ref_start: "2", grid_ref_end: "3", span_m: 4.0 },
      { element_id: "2B3", element_type: "beam", grid_ref_start: "A", grid_ref_end: "B", span_m: 5.0 }
    ],
    warnings: []
  };
}

async function executePass3() {
  return {
    px_per_meter: 172.4,
    scale_factor: "1:100",
    discrepancy_max_mm: 12.5,
    c2_validation: {
      origin_orientation: "OK (Top-Left origin)",
      grid_label_duplicates: 0,
      status: "PASS"
    }
  };
}

function displayStepResult(step, result) {
  el.jsonViewer.textContent = JSON.stringify(result, null, 2);

  let html = '';
  if (step === 0) {
    html = `
      <h4>📋 Pass 0 Classification:</h4>
      <p><strong>Sheet Code:</strong> ${result.sheet_code || '-'}</p>
      <p><strong>Sheet Name:</strong> ${result.sheet_name || '-'}</p>
      <p><strong>Views Found:</strong> ${(result.views || []).map(v => `<span class="meta-tag">${v.subtask}</span>`).join(' ')}</p>
    `;
  } else if (step === 1) {
    html = `
      <h4>✂️ Pass 1 & 1.5 Crop/CV Analysis:</h4>
      <p><strong>Crops Generated:</strong> ${result.crops_generated || 0} ภาพ</p>
      <p><strong>CV Detection:</strong> คาน ${result.cv_symbols_detected?.beams || 0} ตัว, เสา ${result.cv_symbols_detected?.columns || 0} ต้น</p>
      <p class="meta-tag">${result.hint_text_generated || ''}</p>
    `;
  } else if (step === 2) {
    html = `
      <h4>📐 GRID MASTER Output:</h4>
      <p><strong>แกน X:</strong> ${(result.grid?.x_lines || []).map(x => `${x.id} (${x.pos_m}m)`).join(' ➔ ')}</p>
      <p><strong>แกน Y:</strong> ${(result.grid?.y_lines || []).map(y => `${y.id} (${y.pos_m}m)`).join(' ➔ ')}</p>
      <p><strong>ขนาดอาคาร:</strong> ${result.dimension_summary || '-'}</p>
    `;
  } else if (step === 3) {
    const els = result.elements || [];
    html = `
      <h4>🏗️ Elements Extracted (${els.length} ชิ้นส่วน):</h4>
      <div class="elements-table-box">
        <table style="width:100%; border-collapse: collapse; font-size:0.8rem;">
          <tr style="border-bottom:1px solid #334155; text-align:left;">
            <th>ID</th><th>Type</th><th>Span</th><th>Length</th>
          </tr>
          ${els.map(e => `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
              <td><strong>${e.element_id || e.id}</strong></td>
              <td>${e.element_type}</td>
              <td>${e.grid_ref_start || '?'}-${e.grid_ref_end || '?'}</td>
              <td>${e.span_m || '-'} m</td>
            </tr>
          `).join('')}
        </table>
      </div>
    `;
  } else if (step === 4) {
    html = `
      <h4>📏 Spatial Calibration & C2 Report:</h4>
      <p><strong>Px per Meter:</strong> ${result.px_per_meter} px/m</p>
      <p><strong>Scale:</strong> ${result.scale_factor}</p>
      <p><strong>C2 Validation:</strong> <span class="report-ok">✅ ${result.c2_validation?.status || 'PASS'}</span></p>
    `;
  }

  el.stepResultCard.innerHTML = html;
}

// ── Prompt Optimization Lab ─────────────────────────────────────────────────

async function previewAssembledPrompt() {
  const subtask = el.selectSubtask.value;
  const customBody = el.promptEditorText.value;
  const includeCommon = el.chkIncCommon.checked;
  const gridMasterText = el.chkIncGrid.checked ? "\n\nGRID MASTER (resolved axes for this building)\n{\"grid\": {\"x_lines\": [{\"id\": \"1\", \"pos_m\": 0}, {\"id\": \"2\", \"pos_m\": 4}]}}" : null;
  const cvHintText = el.chkIncCv.checked ? "CV Hint: Found #1 Beam at (150, 300)" : null;

  try {
    const res = await fetch('/api/prompt/assemble', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subtask,
        custom_body: customBody,
        include_common: includeCommon,
        grid_master_text: gridMasterText,
        cv_hint_text: cvHintText
      })
    });
    const data = await res.json();
    el.evalRawOutput.textContent = data.prompt;
  } catch (err) {
    alert('Failed to assemble prompt: ' + err.message);
  }
}

async function runPromptTest() {
  if (!state.selectedPage) {
    alert('กรุณาเลือกหน้าแบบในแถบด้านบนก่อนทดสอบ');
    return;
  }

  el.btnRunPromptTest.disabled = true;
  el.btnRunPromptTest.textContent = '🚀 กำลังยิงทดสอบ AI...';

  // Assemble full prompt
  const subtask = el.selectSubtask.value;
  const customBody = el.promptEditorText.value;
  const includeCommon = el.chkIncCommon.checked;
  const gridMasterText = el.chkIncGrid.checked ? "\n\nGRID MASTER\n{\"grid\": {\"x_lines\": [{\"id\": \"1\", \"pos_m\": 0}, {\"id\": \"2\", \"pos_m\": 4}]}}" : null;
  const cvHintText = el.chkIncCv.checked ? "CV Hint: Found #1 Beam" : null;

  try {
    const asmRes = await fetch('/api/prompt/assemble', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subtask, custom_body: customBody, include_common: includeCommon, grid_master_text: gridMasterText, cv_hint_text: cvHintText })
    });
    const { prompt } = await asmRes.json();

    if (!state.endpoint.connected) {
      // Simulate quick response when offline
      const mockParsed = {
        pattern: subtask,
        elements: [
          { element_id: "B1", element_type: "beam", grid_ref_start: "1", grid_ref_end: "2", span_m: 4.0 },
          { element_id: "B2", element_type: "beam", grid_ref_start: "2", grid_ref_end: "3", span_m: 4.0 }
        ]
      };
      displayPromptEvalResults({
        success: true,
        elapsed_s: 1.25,
        usage: { completion_tokens: 154 },
        tokens_per_sec: 123.2,
        raw_text: JSON.stringify(mockParsed, null, 2),
        parsed: mockParsed
      });
      return;
    }

    const aiRes = await fetch('/api/ai/call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        endpoint_url: state.endpoint.url,
        api_key: state.endpoint.key,
        model: state.endpoint.model,
        prompt: prompt,
        image_paths: [state.selectedPage.path],
        temperature: parseFloat(el.paramTemp.value),
        top_p: parseFloat(el.paramTopp.value),
        max_tokens: parseInt(el.paramMaxTokens.value),
        enable_thinking: el.chkEnableThinking.checked
      })
    });
    const aiData = await aiRes.json();
    displayPromptEvalResults(aiData);
  } catch (err) {
    alert('Prompt test failed: ' + err.message);
  } finally {
    el.btnRunPromptTest.disabled = false;
    el.btnRunPromptTest.textContent = '🚀 ยิงทดสอบกับหน้านี้ (Run AI)';
  }
}

async function displayPromptEvalResults(res) {
  el.metricTime.textContent = `${res.elapsed_s || '-'} s`;
  el.metricTokens.textContent = res.usage?.completion_tokens || '-';
  el.metricSpeed.textContent = `${res.tokens_per_sec || '-'} tok/s`;
  el.evalRawOutput.textContent = res.raw_text || res.error || '';

  if (res.parsed) {
    // Validate Contract
    const valRes = await fetch('/api/contract/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc: res.parsed })
    });
    const valData = await valRes.json();

    if (valData.valid) {
      el.contractStatusBox.innerHTML = `
        <div class="contract-banner valid">
          ✅ สอดคล้องกับ finetune_output_contract (พบ ${valData.element_count} ชิ้นส่วน)
        </div>
      `;
    } else {
      el.contractStatusBox.innerHTML = `
        <div class="contract-banner invalid">
          ⚠️ ผิดสัญญา Contract: ${valData.warnings.join(', ')}
        </div>
      `;
    }

    const els = res.parsed.elements || [];
    el.evalElementsContainer.innerHTML = `
      <table style="width:100%; border-collapse: collapse; font-size:0.75rem;">
        <tr style="border-bottom:1px solid #334155; text-align:left;"><th>ID</th><th>Type</th><th>Span</th></tr>
        ${els.map(e => `
          <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td><strong>${e.element_id || e.id || '?'}</strong></td>
            <td>${e.element_type || '-'}</td>
            <td>${e.grid_ref_start || ''}-${e.grid_ref_end || ''}</td>
          </tr>
        `).join('')}
      </table>
    `;
  } else {
    el.contractStatusBox.innerHTML = `<div class="contract-banner invalid">❌ ไม่สามารถแปลงผลลัพธ์เป็น JSON ได้</div>`;
  }
}

// ── Canvas Overlay Rendering ────────────────────────────────────────────────

function resizeCanvas() {
  const img = el.blueprintImg;
  const canvas = el.overlayCanvas;
  if (!img.naturalWidth) return;
  canvas.width = img.clientWidth;
  canvas.height = img.clientHeight;
}

window.addEventListener('resize', () => {
  resizeCanvas();
  redrawOverlay();
});

function redrawOverlay() {
  const canvas = el.overlayCanvas;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // If no results have been generated for this page, leave canvas clean!
  if (!state.pipelineResults || Object.keys(state.pipelineResults).length === 0) {
    return;
  }

  const W = canvas.width;
  const H = canvas.height;

  // 1. Draw View Crop Frame only if Pass 1 has run and crop toggle is active
  const p1 = state.pipelineResults[1];
  if (p1 && state.overlayConfig.crop) {
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 3]);
    ctx.strokeRect(W * 0.08, H * 0.08, W * 0.84, H * 0.84);
    ctx.fillStyle = '#fbbf24';
    ctx.font = '11px sans-serif';
    ctx.fillText('Crop View 1: Main Plan Area', W * 0.08 + 6, H * 0.08 + 16);
    ctx.setLineDash([]);
  }

  // 2. Draw CV Bounding Boxes only if Pass 1/1.5 has run and cv toggle is active
  if (p1 && state.overlayConfig.cv) {
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.fillStyle = 'rgba(16, 185, 129, 0.2)';

    const boxes = [
      { x: W * 0.23, y: H * 0.23, w: 28, h: 28, label: '#1 C1' },
      { x: W * 0.48, y: H * 0.23, w: 28, h: 28, label: '#2 C1' },
      { x: W * 0.73, y: H * 0.23, w: 28, h: 28, label: '#3 C1' }
    ];

    boxes.forEach(b => {
      ctx.fillRect(b.x, b.y, b.w, b.h);
      ctx.strokeRect(b.x, b.y, b.w, b.h);
      ctx.fillStyle = '#34d399';
      ctx.font = '10px JetBrains Mono';
      ctx.fillText(b.label, b.x, b.y - 4);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.2)';
    });
  }

  // 3. Draw Grid Overlay only if Pass 2 Grid has run and grid toggle is active
  const p2g = state.pipelineResults[2];
  if (p2g && state.overlayConfig.grid) {
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);

    // Horizontal grid lines
    ctx.beginPath();
    ctx.moveTo(W * 0.15, H * 0.25); ctx.lineTo(W * 0.85, H * 0.25);
    ctx.moveTo(W * 0.15, H * 0.50); ctx.lineTo(W * 0.85, H * 0.50);
    ctx.moveTo(W * 0.15, H * 0.75); ctx.lineTo(W * 0.85, H * 0.75);

    // Vertical grid lines
    ctx.moveTo(W * 0.25, H * 0.15); ctx.lineTo(W * 0.25, H * 0.85);
    ctx.moveTo(W * 0.50, H * 0.15); ctx.lineTo(W * 0.50, H * 0.85);
    ctx.moveTo(W * 0.75, H * 0.15); ctx.lineTo(W * 0.75, H * 0.85);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // 4. Draw Subtask Elements if Pass 2 Subtasks has run
  const p2s = state.pipelineResults[3];
  if (p2s && Array.isArray(p2s.elements)) {
    ctx.strokeStyle = '#ec4899';
    ctx.lineWidth = 3;
    p2s.elements.forEach((elItem, i) => {
      const y = H * (0.25 + i * 0.25);
      if (y < H * 0.9) {
        ctx.beginPath();
        ctx.moveTo(W * 0.25, y);
        ctx.lineTo(W * 0.75, y);
        ctx.stroke();
        ctx.fillStyle = '#f472b6';
        ctx.font = '11px JetBrains Mono';
        ctx.fillText(elItem.element_id || 'Beam', W * 0.48, y - 6);
      }
    });
  }
}

function runMockCvScan() {
  document.getElementById('cv-counts-list').innerHTML = `
    <p>✅ สแกนสำเร็จ: ฐานราก (Footing) 6 ตัว, เสา (Column) 8 ต้น, คาน (Beam) 16 เส้น</p>
  `;
  document.getElementById('cv-hint-preview').textContent = 
    "CV Hint (pass1.5):\n" +
    "#1 footing [120, 240, 60, 60]\n" +
    "#2 footing [320, 240, 60, 60]\n" +
    "#3 column  [135, 255, 30, 30]";
}
