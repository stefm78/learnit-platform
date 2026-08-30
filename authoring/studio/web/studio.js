'use strict';

const STORAGE_KEY = 'learnit.authoring.m3.v1';
const state = { draft: null, validation: null, courseIndex: 0, objectiveIndex: 0, activityIndex: 0 };

const $ = selector => document.querySelector(selector);
const workspace = $('#workspace');
const emptyState = $('#empty-state');
const courseSelect = $('#course-select');
const objectiveSelect = $('#objective-select');
const activitySelect = $('#activity-select');
const diagnostics = $('#diagnostic-list');
const validationBadge = $('#validation-badge');
const exportButton = $('#export');
const discardButton = $('#discard');
const previewContent = $('#preview-content');
const qualityList = $('#quality-list');
const qualityBadge = $('#quality-badge');
const qualitySummary = $('#quality-summary');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
}

async function requestJson(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) {
    const diagnostic = data.diagnostic || {cause: `HTTP ${response.status}`};
    throw new Error(`${diagnostic.path || '$'} — ${diagnostic.cause || diagnostic.code || 'Erreur'}`);
  }
  return data;
}

function persist() {
  if (state.draft) localStorage.setItem(STORAGE_KEY, JSON.stringify(state.draft));
}

function resetSelection() {
  state.courseIndex = 0;
  state.objectiveIndex = 0;
  state.activityIndex = 0;
}

function selectedCourse() { return state.draft.package.courses[state.courseIndex]; }
function selectedObjective() { return selectedCourse().objectives[state.objectiveIndex]; }
function selectedActivity() { return selectedCourse().activities[state.activityIndex]; }

function option(label, value, selected) {
  return `<option value="${escapeHtml(value)}"${selected ? ' selected' : ''}>${escapeHtml(label)}</option>`;
}

function syncSelectors() {
  const courses = state.draft.package.courses;
  if (state.courseIndex >= courses.length) state.courseIndex = 0;
  courseSelect.innerHTML = courses.map((course, index) => option(course.title, index, index === state.courseIndex)).join('');
  const course = selectedCourse();
  if (state.objectiveIndex >= course.objectives.length) state.objectiveIndex = 0;
  objectiveSelect.innerHTML = course.objectives.map((objective, index) => option(objective.label, index, index === state.objectiveIndex)).join('');
  const objective = selectedObjective();
  const linked = course.activities.map((activity, index) => ({activity, index})).filter(row => row.activity.objectiveIds.includes(objective.objectiveId));
  if (!linked.some(row => row.index === state.activityIndex)) state.activityIndex = linked[0]?.index ?? 0;
  activitySelect.innerHTML = linked.map(row => option(`${row.index + 1}. ${row.activity.prompt}`, row.index, row.index === state.activityIndex)).join('');
}

function field(label, path, value, kind = 'text', wide = false, choices = null) {
  const cls = wide ? 'field wide' : 'field';
  const encodedPath = escapeHtml(JSON.stringify(path));
  if (choices) {
    return `<label class="${cls}"><span>${escapeHtml(label)}</span><select data-edit='${encodedPath}'>${choices.map(choice => option(choice.label, choice.value, choice.value === value)).join('')}</select></label>`;
  }
  if (kind === 'textarea') {
    return `<label class="${cls}"><span>${escapeHtml(label)}</span><textarea data-edit='${encodedPath}'>${escapeHtml(value)}</textarea></label>`;
  }
  const inputType = kind === 'number' ? 'number' : 'text';
  return `<label class="${cls}"><span>${escapeHtml(label)}</span><input type="${inputType}" data-value-type="${kind}" data-edit='${encodedPath}' value="${escapeHtml(value)}"></label>`;
}

function renderEditor() {
  const pkg = state.draft.package;
  const course = selectedCourse();
  const objective = selectedObjective();
  const activity = selectedActivity();
  $('#package-fields').innerHTML = [
    field('Titre', ['title'], pkg.title, 'text', true),
    field('Description', ['description'], pkg.description, 'textarea', true),
    field('Version', ['versionLabel'], pkg.versionLabel),
    field('Langue', ['language'], pkg.language),
  ].join('');
  $('#course-fields').innerHTML = [
    field('Titre', ['courses', state.courseIndex, 'title'], course.title, 'text', true),
    field('Sous-titre', ['courses', state.courseIndex, 'subtitle'], course.subtitle, 'text', true),
    field('Durée estimée (min)', ['courses', state.courseIndex, 'estimatedMinutes'], course.estimatedMinutes, 'number'),
  ].join('');
  $('#objective-fields').innerHTML = field('Libellé', ['courses', state.courseIndex, 'objectives', state.objectiveIndex, 'label'], objective.label, 'text', true);

  const phases = ['activation','comprehension','application','consolidation','validation','transfer','diagnostic'].map(value => ({value,label:value}));
  const roles = ['practice','diagnostic','validation'].map(value => ({value,label:value}));
  const difficulties = ['easy','medium','advanced','expert'].map(value => ({value,label:value}));
  $('#activity-fields').innerHTML = [
    field('Question / consigne', ['courses', state.courseIndex, 'activities', state.activityIndex, 'prompt'], activity.prompt, 'textarea', true),
    field('Explication', ['courses', state.courseIndex, 'activities', state.activityIndex, 'explanation'], activity.explanation, 'textarea', true),
    field('Difficulté', ['courses', state.courseIndex, 'activities', state.activityIndex, 'difficulty'], activity.difficulty, 'text', false, difficulties),
    field('Phase', ['courses', state.courseIndex, 'activities', state.activityIndex, 'learningPhase'], activity.learningPhase, 'text', false, phases),
    field('Rôle d’évaluation', ['courses', state.courseIndex, 'activities', state.activityIndex, 'assessmentRole'], activity.assessmentRole, 'text', false, roles),
    field('Durée (min)', ['courses', state.courseIndex, 'activities', state.activityIndex, 'estimatedMinutes'], activity.estimatedMinutes, 'number'),
  ].join('');

  const typeFields = $('#type-fields');
  if (activity.type === 'qcm') {
    const choiceRows = activity.choices.map((choice, index) => field(
      `Choix ${index + 1}`,
      ['courses', state.courseIndex, 'activities', state.activityIndex, 'choices', index, 'label'],
      choice.label,
      'text', true,
    )).join('');
    const correct = field(
      'Bonne réponse',
      ['courses', state.courseIndex, 'activities', state.activityIndex, 'correctChoiceId'],
      activity.correctChoiceId,
      'text', true,
      activity.choices.map(choice => ({value: choice.choiceId, label: choice.label})),
    );
    typeFields.innerHTML = `<div class="type-block"><h3>QCM</h3><div class="repeated">${choiceRows}${correct}</div></div>`;
  } else if (activity.type === 'fill') {
    const textSegments = activity.segments.map((segment, index) => 'text' in segment ? field(
      `Texte ${index + 1}`,
      ['courses', state.courseIndex, 'activities', state.activityIndex, 'segments', index, 'text'],
      segment.text, 'text', true,
    ) : `<div class="field wide"><span>Emplacement ${index + 1}</span><input value="Emplacement gelé (${escapeHtml(segment.slotId)})" disabled></div>`).join('');
    const tokenRows = activity.tokens.map((token, index) => `<div class="row">${field(
      `Jeton ${index + 1}`,
      ['courses', state.courseIndex, 'activities', state.activityIndex, 'tokens', index, 'label'], token.label,
    )}${field(
      'Usages max', ['courses', state.courseIndex, 'activities', state.activityIndex, 'tokens', index, 'maxUses'], token.maxUses, 'number'
    )}</div>`).join('');
    const answers = activity.answers.map((answer, index) => field(
      `Réponse emplacement ${index + 1}`,
      ['courses', state.courseIndex, 'activities', state.activityIndex, 'answers', index, 'tokenId'],
      answer.tokenId, 'text', true,
      activity.tokens.map(token => ({value: token.tokenId,label: token.label})),
    )).join('');
    typeFields.innerHTML = `<div class="type-block"><h3>Texte à compléter</h3><div class="repeated">${textSegments}<h4>Jetons</h4>${tokenRows}<h4>Réponses</h4>${answers}</div></div>`;
  } else {
    typeFields.innerHTML = `<div class="diagnostic-item"><strong>Type non pris en charge</strong><code>${escapeHtml(activity.type)}</code></div>`;
  }

  document.querySelectorAll('[data-edit]').forEach(control => control.addEventListener('change', onEdit));
  $('#dirty-badge').textContent = state.draft.dirty ? 'Brouillon modifié' : 'Source inchangée';
  $('#dirty-badge').className = state.draft.dirty ? 'badge bad' : 'badge';
}

async function onEdit(event) {
  const control = event.currentTarget;
  const path = JSON.parse(control.dataset.edit);
  let value = control.value;
  if (control.dataset.valueType === 'number') value = Number.parseInt(value, 10);
  try {
    const data = await requestJson('/api/edit', {draft: state.draft, path, value});
    state.draft = data.draft;
    state.validation = data.validation;
    persist();
    renderAll(false);
  } catch (error) {
    showStandaloneError(error);
  }
}

function renderPedagogicalQuality(report) {
  qualityList.innerHTML = '';
  if (!report) {
    qualityBadge.textContent = 'À analyser';
    qualityBadge.className = 'badge';
    qualitySummary.textContent = 'Le diagnostic pédagogique est calculé après validation canonique.';
    return;
  }

  const labels = {
    BLOCKED: 'Bloqué',
    COMPLETE: 'Complet · à renforcer',
    STRONG: 'Solide',
    EXCELLENT_BY_PROFILE: 'Excellent selon le profil',
  };
  qualityBadge.textContent = labels[report.qualityBand] || report.qualityBand || 'Indisponible';
  qualityBadge.className = report.qualityBand === 'EXCELLENT_BY_PROFILE' || report.qualityBand === 'STRONG'
    ? 'badge ok'
    : (report.qualityBand === 'BLOCKED' ? 'badge bad' : 'badge');

  const counts = report.counts || {blocking: 0, warning: 0, advice: 0};
  qualitySummary.textContent = report.canonicalValid
    ? `${counts.warning} avertissement(s) · ${counts.advice} conseil(s) · profil ${report.profile || 'Atlas'}`
    : 'La qualité pédagogique ne peut pas être validée tant que le kit canonique est invalide.';

  if (!report.diagnostics?.length) {
    qualityList.innerHTML = '<p class="muted">Aucun avertissement ni conseil du profil pédagogique déterministe.</p>';
    return;
  }

  for (const item of report.diagnostics) {
    const node = document.createElement('div');
    const severityClass = item.severity === 'advice' ? ' advice' : (item.severity === 'warning' ? ' warning' : '');
    const severityLabel = item.severity === 'advice' ? 'Conseil' : (item.severity === 'warning' ? 'Avertissement' : 'Blocage');
    node.className = `diagnostic-item${severityClass}`;
    node.innerHTML = `<strong>${severityLabel} · ${escapeHtml(item.code)}</strong><code>${escapeHtml(item.path || '$')}</code><div>${escapeHtml(item.cause)}</div><div class="quality-detail"><b>Impact :</b> ${escapeHtml(item.impact || '')}</div><div class="quality-detail"><b>Correction :</b> ${escapeHtml(item.fix || '')}</div>`;
    qualityList.appendChild(node);
  }
}

function renderDiagnostics() {
  const result = state.validation;
  diagnostics.innerHTML = '';
  if (!result) {
    validationBadge.textContent = 'À vérifier';
    validationBadge.className = 'badge';
    exportButton.disabled = true;
    renderPedagogicalQuality(null);
    return;
  }
  if (result.diagnostics.length === 0) {
    diagnostics.innerHTML = '<p class="muted">Aucun diagnostic bloquant ni avertissement.</p>';
  } else {
    for (const item of result.diagnostics) {
      const node = document.createElement('div');
      node.className = `diagnostic-item${item.severity === 'warning' ? ' warning' : ''}`;
      node.innerHTML = `<strong>${item.severity === 'warning' ? 'Avertissement' : 'Erreur bloquante'} · ${escapeHtml(item.code)}</strong><code>${escapeHtml(item.path || '$')}</code><div>${escapeHtml(item.cause)}</div>`;
      diagnostics.appendChild(node);
    }
  }
  validationBadge.textContent = result.ok ? 'Canonique · export possible' : `${result.blockingCount} erreur(s) bloquante(s)`;
  validationBadge.className = result.ok ? 'badge ok' : 'badge bad';
  exportButton.disabled = !result.exportAvailable;
  $('#export-status').textContent = result.ok ? 'Le même validateur canonique sera rejoué au moment de l’export.' : 'Corrigez les erreurs bloquantes avant export.';
  renderPedagogicalQuality(result.pedagogicalQuality || null);
}
async function refreshPreview() {
  if (!state.draft) return;
  try {
    const data = await requestJson('/api/preview', {draft: state.draft, courseIndex: state.courseIndex, activityIndex: state.activityIndex});
    const p = data.preview;
    let body = `<article class="preview-card"><p class="meta-line">${escapeHtml(p.learningPhase)} · ${escapeHtml(p.assessmentRole)} · ${escapeHtml(p.estimatedMinutes)} min</p><h3>${escapeHtml(p.prompt)}</h3>`;
    if (p.type === 'qcm') {
      body += '<ul>' + p.choices.map(choice => `<li${choice.correct ? ' class="preview-answer"' : ''}>${escapeHtml(choice.label)}${choice.correct ? ' ✓' : ''}</li>`).join('') + '</ul>';
    } else if (p.type === 'fill') {
      body += '<p>' + p.segments.map(segment => 'text' in segment ? escapeHtml(segment.text) : `<strong>[ ${escapeHtml(segment.answer)} ]</strong>`).join('') + '</p>';
    }
    body += `<p>${escapeHtml(p.explanation)}</p><p class="meta-line">Objectif : ${escapeHtml(p.objectiveLabels.join(' · '))}</p></article>`;
    previewContent.innerHTML = body;
  } catch (error) {
    previewContent.innerHTML = `<div class="diagnostic-item">${escapeHtml(error.message)}</div>`;
  }
}

function renderAll(updatePreview = true) {
  if (!state.draft) {
    workspace.hidden = true;
    emptyState.hidden = false;
    discardButton.disabled = true;
    return;
  }
  workspace.hidden = false;
  emptyState.hidden = true;
  discardButton.disabled = false;
  syncSelectors();
  $('#source-name').textContent = state.draft.source.name;
  $('#source-sha').textContent = state.draft.source.sha256;
  renderEditor();
  renderDiagnostics();
  if (updatePreview) refreshPreview();
}

function showStandaloneError(error) {
  validationBadge.textContent = 'Erreur';
  validationBadge.className = 'badge bad';
  diagnostics.innerHTML = `<div class="diagnostic-item"><strong>Erreur</strong><div>${escapeHtml(error.message)}</div></div>`;
  exportButton.disabled = true;
  renderPedagogicalQuality(null);
}

$('#kit-file').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const response = await fetch('/api/import', {
      method: 'POST',
      headers: {'Content-Type': 'application/octet-stream', 'X-Learnit-Source-Name': file.name},
      body: await file.arrayBuffer(),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.diagnostic?.cause || `HTTP ${response.status}`);
    state.draft = data.draft;
    state.validation = data.validation;
    resetSelection();
    persist();
    renderAll();
  } catch (error) {
    showStandaloneError(error);
  } finally {
    event.target.value = '';
  }
});

courseSelect.addEventListener('change', () => { state.courseIndex = Number(courseSelect.value); state.objectiveIndex = 0; state.activityIndex = 0; renderAll(); });
objectiveSelect.addEventListener('change', () => { state.objectiveIndex = Number(objectiveSelect.value); state.activityIndex = 0; renderAll(); });
activitySelect.addEventListener('change', () => { state.activityIndex = Number(activitySelect.value); renderAll(); });
$('#refresh-preview').addEventListener('click', refreshPreview);

discardButton.addEventListener('click', () => {
  if (!confirm('Abandonner uniquement le brouillon auteur local ?')) return;
  localStorage.removeItem(STORAGE_KEY);
  state.draft = null;
  state.validation = null;
  resetSelection();
  previewContent.innerHTML = '';
  renderAll();
});

exportButton.addEventListener('click', async () => {
  try {
    const response = await fetch('/api/export', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({draft: state.draft}),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.diagnostic?.cause || `HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const digest = response.headers.get('X-Learnit-Sha256') || '';
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = (state.draft.source.name || 'kit.json').replace(/\.json$/i, '') + '--atlas-m3.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    $('#export-status').textContent = `Export prêt · SHA-256 ${digest}`;
  } catch (error) {
    showStandaloneError(error);
  }
});

(async function restore() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) { renderAll(); return; }
  try {
    state.draft = JSON.parse(raw);
    const data = await requestJson('/api/validate', {draft: state.draft});
    state.validation = data.validation;
    renderAll();
  } catch (error) {
    localStorage.removeItem(STORAGE_KEY);
    state.draft = null;
    showStandaloneError(new Error(`Brouillon local rejeté puis supprimé : ${error.message}`));
    renderAll();
  }
})();
)}</code>
      <div>${escapeHtml(item.cause)}</div>
      <div class="quality-detail"><b>Impact :</b> ${escapeHtml(item.impact || '')}</div>
      <div class="quality-detail"><b>Correction :</b> ${escapeHtml(item.fix || '')}</div>`;
    qualityList.appendChild(node);
  }
}

function renderDiagnostics() {
  const result = state.validation;
  diagnostics.innerHTML = '';
  if (!result) {
    validationBadge.textContent = 'À vérifier';
    validationBadge.className = 'badge';
    exportButton.disabled = true;
    return;
  }
  if (result.diagnostics.length === 0) {
    diagnostics.innerHTML = '<p class="muted">Aucun diagnostic bloquant ni avertissement.</p>';
  } else {
    for (const item of result.diagnostics) {
      const node = document.createElement('div');
      node.className = `diagnostic-item${item.severity === 'warning' ? ' warning' : ''}`;
      node.innerHTML = `<strong>${item.severity === 'warning' ? 'Avertissement' : 'Erreur bloquante'} · ${escapeHtml(item.code)}</strong><code>${escapeHtml(item.path || '$')}</code><div>${escapeHtml(item.cause)}</div>`;
      diagnostics.appendChild(node);
    }
  }
  validationBadge.textContent = result.ok ? 'Canonique · export possible' : `${result.blockingCount} erreur(s) bloquante(s)`;
  validationBadge.className = result.ok ? 'badge ok' : 'badge bad';
  exportButton.disabled = !result.exportAvailable;
  $('#export-status').textContent = result.ok ? 'Le même validateur canonique sera rejoué au moment de l’export.' : 'Corrigez les erreurs bloquantes avant export.';
}

async function refreshPreview() {
  if (!state.draft) return;
  try {
    const data = await requestJson('/api/preview', {draft: state.draft, courseIndex: state.courseIndex, activityIndex: state.activityIndex});
    const p = data.preview;
    let body = `<article class="preview-card"><p class="meta-line">${escapeHtml(p.learningPhase)} · ${escapeHtml(p.assessmentRole)} · ${escapeHtml(p.estimatedMinutes)} min</p><h3>${escapeHtml(p.prompt)}</h3>`;
    if (p.type === 'qcm') {
      body += '<ul>' + p.choices.map(choice => `<li${choice.correct ? ' class="preview-answer"' : ''}>${escapeHtml(choice.label)}${choice.correct ? ' ✓' : ''}</li>`).join('') + '</ul>';
    } else if (p.type === 'fill') {
      body += '<p>' + p.segments.map(segment => 'text' in segment ? escapeHtml(segment.text) : `<strong>[ ${escapeHtml(segment.answer)} ]</strong>`).join('') + '</p>';
    }
    body += `<p>${escapeHtml(p.explanation)}</p><p class="meta-line">Objectif : ${escapeHtml(p.objectiveLabels.join(' · '))}</p></article>`;
    previewContent.innerHTML = body;
  } catch (error) {
    previewContent.innerHTML = `<div class="diagnostic-item">${escapeHtml(error.message)}</div>`;
  }
}

function renderAll(updatePreview = true) {
  if (!state.draft) {
    workspace.hidden = true;
    emptyState.hidden = false;
    discardButton.disabled = true;
    return;
  }
  workspace.hidden = false;
  emptyState.hidden = true;
  discardButton.disabled = false;
  syncSelectors();
  $('#source-name').textContent = state.draft.source.name;
  $('#source-sha').textContent = state.draft.source.sha256;
  renderEditor();
  renderDiagnostics();
  if (updatePreview) refreshPreview();
}

function showStandaloneError(error) {
  validationBadge.textContent = 'Erreur';
  validationBadge.className = 'badge bad';
  diagnostics.innerHTML = `<div class="diagnostic-item"><strong>Erreur</strong><div>${escapeHtml(error.message)}</div></div>`;
  exportButton.disabled = true;
}

$('#kit-file').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const response = await fetch('/api/import', {
      method: 'POST',
      headers: {'Content-Type': 'application/octet-stream', 'X-Learnit-Source-Name': file.name},
      body: await file.arrayBuffer(),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.diagnostic?.cause || `HTTP ${response.status}`);
    state.draft = data.draft;
    state.validation = data.validation;
    resetSelection();
    persist();
    renderAll();
  } catch (error) {
    showStandaloneError(error);
  } finally {
    event.target.value = '';
  }
});

courseSelect.addEventListener('change', () => { state.courseIndex = Number(courseSelect.value); state.objectiveIndex = 0; state.activityIndex = 0; renderAll(); });
objectiveSelect.addEventListener('change', () => { state.objectiveIndex = Number(objectiveSelect.value); state.activityIndex = 0; renderAll(); });
activitySelect.addEventListener('change', () => { state.activityIndex = Number(activitySelect.value); renderAll(); });
$('#refresh-preview').addEventListener('click', refreshPreview);

discardButton.addEventListener('click', () => {
  if (!confirm('Abandonner uniquement le brouillon auteur local ?')) return;
  localStorage.removeItem(STORAGE_KEY);
  state.draft = null;
  state.validation = null;
  resetSelection();
  previewContent.innerHTML = '';
  renderAll();
});

exportButton.addEventListener('click', async () => {
  try {
    const response = await fetch('/api/export', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({draft: state.draft}),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.diagnostic?.cause || `HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const digest = response.headers.get('X-Learnit-Sha256') || '';
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = (state.draft.source.name || 'kit.json').replace(/\.json$/i, '') + '--atlas-m3.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    $('#export-status').textContent = `Export prêt · SHA-256 ${digest}`;
  } catch (error) {
    showStandaloneError(error);
  }
});

(async function restore() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) { renderAll(); return; }
  try {
    state.draft = JSON.parse(raw);
    const data = await requestJson('/api/validate', {draft: state.draft});
    state.validation = data.validation;
    renderAll();
  } catch (error) {
    localStorage.removeItem(STORAGE_KEY);
    state.draft = null;
    showStandaloneError(new Error(`Brouillon local rejeté puis supprimé : ${error.message}`));
    renderAll();
  }
})();
