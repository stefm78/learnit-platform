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

function renderObjectiveCard(evidence) {
  validateEvidence(evidence);
  const label = evidenceLabel(evidence);
  const last = evidence.lastEvidenceAt ? `Dernière preuve : ${evidence.lastEvidenceAt}` : 'Aucune preuve enregistrée';
  return `<article class="atlas-objective-card"><h2>${T.esc(label)}</h2><p>${T.esc(last)}</p><dl><div><dt>Essais d’entraînement</dt><dd>${evidence.practiceAttempts}</dd></div><div><dt>Corrections</dt><dd>${evidence.correctionsCompleted}</dd></div><div><dt>Validations</dt><dd>${evidence.validationAttempts}</dd></div></dl></article>`;
}

function renderSummary({ evidence = [], completed = false }) {
  if (!Array.isArray(evidence) || typeof completed !== 'boolean') fail('INVALID_SUMMARY');
  const title = completed ? 'Séance terminée' : 'État de la séance';
  const cards = evidence.map(renderObjectiveCard).join('');
  return `<section class="atlas-m1 atlas-summary" aria-labelledby="atlas-summary-title"><h1 id="atlas-summary-title">${title}</h1><p>Ces éléments décrivent les preuves enregistrées. Ils ne constituent ni une certification ni une promesse de rétention durable.</p><div class="atlas-objective-grid">${cards}</div></section>`;
}

module.exports = Object.freeze({ evidenceLabel, validateEvidence, renderObjectiveCard, renderSummary });
