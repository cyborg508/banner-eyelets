'use strict';

// ── Geometry port (from banner_eyelets/geometry.py) ────────────────────────
function evenlySpaced(length, margin, targetSpacing) {
  const inner = length - 2 * margin;
  if (inner < 0) return [];
  if (Math.abs(inner) < 1e-9) return [margin];
  const segs = Math.max(1, Math.round(inner / targetSpacing));
  const step = inner / segs;
  return Array.from({ length: segs + 1 }, (_, i) => margin + i * step);
}

function buildEyeletPoints(outW, outH, margin, spacing) {
  const xs = evenlySpaced(outW, margin, spacing);
  const ys = evenlySpaced(outH, margin, spacing);
  const pts = [];
  for (const x of xs) { pts.push([x, margin]); pts.push([x, outH - margin]); }
  for (let i = 1; i < ys.length - 1; i++) {
    pts.push([margin, ys[i]]); pts.push([outW - margin, ys[i]]);
  }
  const seen = new Set();
  return pts.filter(([x, y]) => {
    const k = `${x.toFixed(6)},${y.toFixed(6)}`;
    if (seen.has(k)) return false;
    seen.add(k); return true;
  });
}

// ── State ───────────────────────────────────────────────────────────────────
let uploadedFileName = '';
let debounceTimer = null;

// ── DOM refs ────────────────────────────────────────────────────────────────
const dropZone       = document.getElementById('drop-zone');
const dropText       = document.getElementById('drop-text');
const fileInput      = document.getElementById('file-input');
const openBtn        = document.getElementById('open-btn');
const infoCard       = document.getElementById('info-card');
const dimsCard       = document.getElementById('dims-card');
const eyeletsCard    = document.getElementById('eyelets-card');
const optsCard       = document.getElementById('opts-card');
const actionsDiv     = document.getElementById('actions');
const pointsCard     = document.getElementById('points-card');
const previewImg     = document.getElementById('preview-img');
const previewPH      = document.getElementById('preview-placeholder');
const wrapCheck      = document.getElementById('wrap');
const borderCheck    = document.getElementById('border');
const wrapExtraRow   = document.getElementById('wrap-extra-row');
const pointsToggle   = document.getElementById('points-toggle');
const pointsList     = document.getElementById('points-list');
const pointsCount    = document.getElementById('points-count');
const pointsArrow    = document.getElementById('points-arrow');
const generateBtn    = document.getElementById('generate-btn');

// ── Params helper ───────────────────────────────────────────────────────────
function getParams() {
  return {
    out_w:      parseFloat(document.getElementById('out-w').value)    || 100,
    out_h:      parseFloat(document.getElementById('out-h').value)    || 100,
    margin:     parseFloat(document.getElementById('margin').value)   || 1.5,
    spacing:    parseFloat(document.getElementById('spacing').value)  || 50,
    marker:     parseFloat(document.getElementById('marker').value)   || 1,
    border:     borderCheck.checked,
    wrap:       wrapCheck.checked,
    half:       document.getElementById('half').checked,
    wrap_extra: parseFloat(document.getElementById('wrap-extra').value) || 3,
    frame_line_mm: parseFloat(document.getElementById('frame-line-mm').value) || 1,
    frame_halo_mm: parseFloat(document.getElementById('frame-halo-mm').value) || 0,
    frame_color:   document.getElementById('frame-color').value || 'gray',
    cross_mm:      parseFloat(document.getElementById('cross-mm').value) || 1.2,
  };
}

function toQuery(p) {
  return Object.entries(p)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');
}

// ── Unlock UI after successful upload ───────────────────────────────────────
function unlockUI(fileName, pages, widthCm, heightCm) {
  uploadedFileName = fileName;
  document.getElementById('info-name').textContent  = fileName;
  document.getElementById('info-pages').textContent = pages;
  document.getElementById('info-size').textContent  = `${widthCm.toFixed(2)} × ${heightCm.toFixed(2)} cm`;
  document.getElementById('in-w').textContent = widthCm.toFixed(2);
  document.getElementById('in-h').textContent = heightCm.toFixed(2);
  document.getElementById('out-w').value = widthCm.toFixed(2);
  document.getElementById('out-h').value = heightCm.toFixed(2);
  dropText.textContent = `Załadowano: ${fileName}`;
  for (const el of [infoCard, dimsCard, eyeletsCard, optsCard, actionsDiv, pointsCard]) {
    el.removeAttribute('hidden');
  }
  schedulePreview();
  updatePointsList();
}

// ── Upload ───────────────────────────────────────────────────────────────────
async function handleFile(file) {
  if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
    alert('Wybierz plik PDF.'); return;
  }
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch('/api/upload', { method: 'POST', body: fd });
    if (!r.ok) { alert('Błąd uploadu: ' + await r.text()); return; }
    const d = await r.json();
    unlockUI(file.name, d.page_count, d.width_cm, d.height_cm);
  } catch (e) {
    alert('Błąd połączenia: ' + e);
  }
}

openBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => handleFile(fileInput.files[0]));
dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  handleFile(e.dataTransfer.files[0]);
});

// ── Preview (debounced) ──────────────────────────────────────────────────────
function schedulePreview() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(updatePreview, 400);
}

function updatePreview() {
  if (!uploadedFileName) return;
  const q = toQuery(getParams());
  previewImg.src = `/api/preview?${q}&_t=${Date.now()}`;
  previewImg.removeAttribute('hidden');
  previewPH.setAttribute('hidden', '');
}

previewImg.onerror = () => {
  previewImg.setAttribute('hidden', '');
  previewPH.removeAttribute('hidden');
  previewPH.textContent = 'Błąd podglądu';
};

// ── Wrap checkbox logic ──────────────────────────────────────────────────────
wrapCheck.addEventListener('change', () => {
  if (wrapCheck.checked) {
    wrapExtraRow.removeAttribute('hidden');
    borderCheck.checked = true;
  } else {
    wrapExtraRow.setAttribute('hidden', '');
  }
  schedulePreview(); updatePointsList();
});

// ── All numeric inputs + checkboxes → preview + points ──────────────────────
document.querySelectorAll('input[type=number], input[type=checkbox], select').forEach(el => {
  el.addEventListener('input',  () => { schedulePreview(); updatePointsList(); });
  el.addEventListener('change', () => { schedulePreview(); updatePointsList(); });
});

// ── Generate ─────────────────────────────────────────────────────────────────
generateBtn.addEventListener('click', () => {
  if (!uploadedFileName) return;
  window.location.href = `/api/generate?${toQuery(getParams())}`;
});

// ── Points list ──────────────────────────────────────────────────────────────
function updatePointsList() {
  if (!uploadedFileName) return;
  const p = getParams();
  const factor   = p.half ? 0.5 : 1.0;
  const margin   = p.margin  * factor;
  const spacing  = p.spacing * factor;
  const points   = buildEyeletPoints(p.out_w, p.out_h, margin, spacing);
  pointsCount.textContent = `Podgląd punktów (${points.length} oczek)`;
  if (!pointsList.hasAttribute('hidden')) {
    pointsList.innerHTML = '';
    points.forEach(([x, y], i) => {
      const d = document.createElement('div');
      d.className = 'point-item';
      d.textContent = `${i + 1}. x = ${x.toFixed(2)} cm, y = ${y.toFixed(2)} cm`;
      pointsList.appendChild(d);
    });
  }
}

function togglePoints() {
  const hidden = pointsList.hasAttribute('hidden');
  pointsToggle.setAttribute('aria-expanded', String(hidden));
  if (hidden) {
    pointsList.removeAttribute('hidden');
    pointsArrow.textContent = ' ▼';
    updatePointsList();
  } else {
    pointsList.setAttribute('hidden', '');
    pointsArrow.textContent = ' ▶';
  }
}
pointsToggle.addEventListener('click', togglePoints);
pointsToggle.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); togglePoints(); } });
