'use strict';

const T = require('./atlas_today.js');

function fail(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function evidenceLabel(evidence) {
  switch (evidence.state) {
    case 'not-started': return 'Pas encore commencé';
    case 'training': return 'En entraînement';
    case 'review-needed': return 'À reprendre';
    case 'ready-for-validation': return 'Prêt pour une validation autonome';
    case 'validated-recently': return 'Validation autonome récente';
    default: fail('UNKNOWN_EVIDENCE_STATE');
  }
}

function validateEvidence(evidence) {
  T.assertClosed(evidence, [
    'evidenceVersion', 'objectiveRef', 'practiceAttempts', 'correctionsCompleted',
    'validationAttempts', 'latestPracticeCorrect', 'latestValidationCorrect',
    'lastValidationAt', 'lastEvidenceAt', 'state'
  ], [], 'INVALID_EVIDENCE');
  if (evidence.evidenceVersion !== 'atlas.objective-evidence.v1') fail('INVALID_EVIDENCE');
  T.assertObjectiveRef(evidence.objectiveRef);
  for (const key of ['practiceAttempts', 'correctionsCompleted', 'validationAttempts']) {
    if (!Number.isInteger(evidence[key]) || evidence[key] < 0) fail('INVALID_EVIDENCE');
  }
  for (const key of ['latestPracticeCorrect', 'latestValidationCorrect']) {
    if (evidence[key] !== null && typeof evidence[key] !== 'boolean') fail('INVALID_EVIDENCE');
  }
  for (const key of ['lastValidationAt', 'lastEvidenceAt']) {
    if (evidence[key] !== null) T.assertCanonicalTimestamp(evidence[key], 'INVALID_EVIDENCE');
  }
  if (!['not-started', 'training', 'review-needed', 'ready-for-validation', 'validated-recently'].includes(evidence.state)) fail('UNKNOWN_EVIDENCE_STATE');

  const hasEvidence = evidence.practiceAttempts + evidence.correctionsCompleted + evidence.validationAttempts > 0;
  if ((evidence.practiceAttempts === 0) !== (evidence.latestPracticeCorrect === null)) fail('EVIDENCE_STATE_CONTRADICTION');
  if ((evidence.validationAttempts === 0) !== (evidence.latestValidationCorrect === null)) fail('EVIDENCE_STATE_CONTRADICTION');
  if ((evidence.lastEvidenceAt === null) === hasEvidence) fail('EVIDENCE_STATE_CONTRADICTION');
  if (evidence.lastValidationAt !== null && evidence.validationAttempts === 0) fail('EVIDENCE_STATE_CONTRADICTION');
  if (evidence.lastValidationAt !== null && evidence.lastEvidenceAt !== null && evidence.lastValidationAt > evidence.lastEvidenceAt) fail('EVIDENCE_STATE_CONTRADICTION');

  if (evidence.state === 'not-started') {
    if (hasEvidence || evidence.lastValidationAt !== null || evidence.lastEvidenceAt !== null) fail('EVIDENCE_STATE_CONTRADICTION');
  }
  if (evidence.state !== 'not-started' && !hasEvidence) fail('EVIDENCE_STATE_CONTRADICTION');
  if (evidence.state === 'ready-for-validation' && evidence.latestPracticeCorrect !== true) fail('EVIDENCE_STATE_CONTRADICTION');
  if (evidence.state === 'validated-recently' && (evidence.validationAttempts < 1 || evidence.latestValidationCorrect !== true || evidence.lastValidationAt === null)) fail('EVIDENCE_STATE_CONTRADICTION');
  return evidence;
}

const MONTHS_FR = Object.freeze([
  'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
  'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
]);

function pad2(value) {
  return String(value).padStart(2, '0');
}

function formatLearnerTimestamp(value, now = new Date()) {
  T.assertCanonicalTimestamp(value, 'INVALID_EVIDENCE');
  const date = new Date(value);
  const reference = now instanceof Date ? now : new Date(now);
  if (Number.isNaN(reference.getTime())) fail('INVALID_EVIDENCE');
  const time = `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
  const sameDay = date.getFullYear() === reference.getFullYear()
    && date.getMonth() === reference.getMonth()
    && date.getDate() === reference.getDate();
  if (sameDay) return `Aujourd’hui à ${time}`;
  return `${date.getDate()} ${MONTHS_FR[date.getMonth()]} ${date.getFullYear()} à ${time}`;
}

function objectiveLabelFor(evidence, objectiveLabels) {
  if (!objectiveLabels || typeof objectiveLabels !== 'object' || Array.isArray(objectiveLabels)) return null;
  const value = objectiveLabels[evidence.objectiveRef.objectiveId];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function renderObjectiveCard(evidence, objectiveLabels = {}) {
  validateEvidence(evidence);
  const label = evidenceLabel(evidence);
  const objective = objectiveLabelFor(evidence, objectiveLabels);
  const objectiveHtml = objective
    ? `<p class="atlas-objective-name"><strong>Objectif : ${T.esc(objective)}</strong></p>`
    : '';
  const last = evidence.lastEvidenceAt
    ? `Dernière preuve : ${formatLearnerTimestamp(evidence.lastEvidenceAt)}`
    : 'Aucune preuve enregistrée';
  return `<article class="atlas-objective-card">${objectiveHtml}<h2>${T.esc(label)}</h2><p>${T.esc(last)}</p><dl><div><dt>Essais d’entraînement</dt><dd>${evidence.practiceAttempts}</dd></div><div><dt>Corrections</dt><dd>${evidence.correctionsCompleted}</dd></div><div><dt>Validations</dt><dd>${evidence.validationAttempts}</dd></div></dl></article>`;
}

function renderSummary({ evidence = [], completed = false, objectiveLabels = {} }) {
  if (!Array.isArray(evidence) || typeof completed !== 'boolean') fail('INVALID_SUMMARY');
  const title = completed ? 'Séance terminée' : 'État de la séance';
  const cards = evidence.map(item => renderObjectiveCard(item, objectiveLabels)).join('');
  return `<section class="atlas-m1 atlas-summary" aria-labelledby="atlas-summary-title"><h1 id="atlas-summary-title">${title}</h1><p>Voici votre bilan par objectif.</p><div class="atlas-objective-grid">${cards}</div></section>`;
}

module.exports = Object.freeze({
  evidenceLabel,
  validateEvidence,
  formatLearnerTimestamp,
  objectiveLabelFor,
  renderObjectiveCard,
  renderSummary
});
