'use strict';

const REASON_LABELS = Object.freeze({
  NEW_OBJECTIVE: 'Nouvel objectif à découvrir.',
  PRACTICE_IN_PROGRESS: 'Entraînement en cours.',
  RECENT_ERROR: 'Une erreur récente doit être reprise.',
  REVIEW_REQUIRED: 'Une correction ciblée est recommandée.',
  CORRECTION_COMPLETED: 'La correction a été effectuée.',
  NO_INDEPENDENT_VALIDATION: 'Aucune validation indépendante admissible.',
  VALIDATION_AVAILABLE: 'Une validation autonome est disponible.',
  RECENTLY_VALIDATED: 'Une validation récente est enregistrée.',
  TRANSFER_AVAILABLE: 'Une reconfirmation récente ouvre un défi dans un autre contexte.',
  SESSION_TIME_LIMIT: 'Cette activité ne tient pas dans la durée choisie.'
});

const ACTION_CLASS = Object.freeze({
  'start-practice': 'practice',
  'continue-practice': 'practice',
  'correct-practice': 'correction',
  'attempt-validation': 'validation',
  'maintain-recent-validation': 'validation',
  'attempt-transfer': 'transfer'
});
const ACTION_LABELS = Object.freeze({
  'start-practice': 'Entraînement — je m’exerce',
  'continue-practice': 'Entraînement — je m’exerce',
  'correct-practice': 'Correction — je corrige une erreur',
  'attempt-validation': 'Validation — je vérifie sans aide',
  'maintain-recent-validation': 'Entretien — je garde un acquis récent actif',
  'attempt-transfer': 'Défi de transfert — j’applique dans un autre contexte'
});


const SHA = /^sha256:[0-9a-f]{64}$/;
const TS = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
const IDS = Object.freeze({
  plan: /^atlas-plan-sha256:[0-9a-f]{64}$/,
  session: /^atlas-session-sha256:[0-9a-f]{64}$/,
  event: /^atlas-event-sha256:[0-9a-f]{64}$/,
  execution: /^atlas-execution-sha256:[0-9a-f]{64}$/,
  assistance: /^atlas-assistance-sha256:[0-9a-f]{64}$/,
  claim: /^atlas-claim-sha256:[0-9a-f]{64}$/
});

const SHA256_K = Object.freeze([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]);

function fail(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function esc(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function assertClosed(value, required, optional = [], code = 'INVALID_OBJECT') {
  if (!isObject(value)) fail(code);
  const allowed = new Set([...required, ...optional]);
  for (const key of Object.keys(value)) if (!allowed.has(key)) fail('UNKNOWN_FIELD');
  for (const key of required) if (!(key in value)) fail('MISSING_FIELD');
  return value;
}

function nonEmpty(value, code) {
  if (typeof value !== 'string' || value.length === 0) fail(code);
  return value;
}

function compareCodePoints(left, right) {
  const a = Array.from(left);
  const b = Array.from(right);
  for (let index = 0; index < Math.min(a.length, b.length); index += 1) {
    const difference = a[index].codePointAt(0) - b[index].codePointAt(0);
    if (difference) return difference;
  }
  return a.length - b.length;
}

function canonicalJson(value, stack = new WeakSet()) {
  if (value === undefined || typeof value === 'function' || typeof value === 'symbol' || typeof value === 'bigint') fail('NON_CANONICAL_VALUE');
  if (value === null) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'string') return JSON.stringify(value.normalize('NFC'));
  if (typeof value === 'number') {
    if (!Number.isInteger(value) || !Number.isFinite(value) || Object.is(value, -0)) fail('NON_CANONICAL_NUMBER');
    return String(value);
  }
  if (!value || typeof value !== 'object') fail('NON_CANONICAL_VALUE');
  if (stack.has(value)) fail('CANONICAL_CYCLE');
  stack.add(value);
  let result;
  if (Array.isArray(value)) {
    result = `[${value.map(item => canonicalJson(item, stack)).join(',')}]`;
  } else {
    const normalized = new Map();
    for (const originalKey of Object.keys(value)) {
      const key = originalKey.normalize('NFC');
      if (normalized.has(key)) fail('CANONICAL_KEY_COLLISION');
      if (value[originalKey] === undefined) fail('NON_CANONICAL_VALUE');
      normalized.set(key, value[originalKey]);
    }
    const keys = [...normalized.keys()].sort(compareCodePoints);
    result = `{${keys.map(key => `${JSON.stringify(key)}:${canonicalJson(normalized.get(key), stack)}`).join(',')}}`;
  }
  stack.delete(value);
  return result;
}

function rotateRight(value, amount) {
  return (value >>> amount) | (value << (32 - amount));
}

function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const bitLength = bytes.length * 8;
  const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64;
  const padded = new Uint8Array(paddedLength);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000), false);
  view.setUint32(paddedLength - 4, bitLength >>> 0, false);

  const hash = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
  ]);
  const words = new Uint32Array(64);

  for (let offset = 0; offset < paddedLength; offset += 64) {
    for (let index = 0; index < 16; index += 1) words[index] = view.getUint32(offset + index * 4, false);
    for (let index = 16; index < 64; index += 1) {
      const s0 = rotateRight(words[index - 15], 7) ^ rotateRight(words[index - 15], 18) ^ (words[index - 15] >>> 3);
      const s1 = rotateRight(words[index - 2], 17) ^ rotateRight(words[index - 2], 19) ^ (words[index - 2] >>> 10);
      words[index] = (words[index - 16] + s0 + words[index - 7] + s1) >>> 0;
    }

    let [a, b, c, d, e, f, g, h] = hash;
    for (let index = 0; index < 64; index += 1) {
      const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
      const choice = (e & f) ^ (~e & g);
      const temp1 = (h + sum1 + choice + SHA256_K[index] + words[index]) >>> 0;
      const sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
      const majority = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (sum0 + majority) >>> 0;
      h = g; g = f; f = e; e = (d + temp1) >>> 0;
      d = c; c = b; b = a; a = (temp1 + temp2) >>> 0;
    }
    hash[0] = (hash[0] + a) >>> 0;
    hash[1] = (hash[1] + b) >>> 0;
    hash[2] = (hash[2] + c) >>> 0;
    hash[3] = (hash[3] + d) >>> 0;
    hash[4] = (hash[4] + e) >>> 0;
    hash[5] = (hash[5] + f) >>> 0;
    hash[6] = (hash[6] + g) >>> 0;
    hash[7] = (hash[7] + h) >>> 0;
  }
  return [...hash].map(word => word.toString(16).padStart(8, '0')).join('');
}

function hashHex(domain, value) {
  return sha256Hex(`${domain}\0${canonicalJson(value)}`);
}

function typedHash(prefix, domain, value) {
  return `${prefix}${hashHex(domain, value)}`;
}

function without(value, field) {
  const result = {};
  for (const [key, item] of Object.entries(value)) if (key !== field) result[key] = item;
  return result;
}

function assertCanonicalTimestamp(value, code = 'INVALID_TIMESTAMP') {
  if (typeof value !== 'string' || !TS.test(value) || Number.isNaN(Date.parse(value)) || new Date(Date.parse(value)).toISOString() !== value) fail(code);
  return value;
}

function assertCourseRef(ref) {
  assertClosed(ref, ['packageLineageId', 'courseLineageId'], [], 'INVALID_COURSE_REF');
  nonEmpty(ref.packageLineageId, 'INVALID_COURSE_REF');
  nonEmpty(ref.courseLineageId, 'INVALID_COURSE_REF');
  return ref;
}

function assertContentRevisionRef(ref) {
  assertClosed(ref, ['packageLineageId', 'packageRevisionId', 'packageDigest'], [], 'INVALID_CONTENT_REVISION_REF');
  nonEmpty(ref.packageLineageId, 'INVALID_CONTENT_REVISION_REF');
  nonEmpty(ref.packageRevisionId, 'INVALID_CONTENT_REVISION_REF');
  if (!SHA.test(ref.packageDigest)) fail('INVALID_CONTENT_REVISION_REF');
  return ref;
}

function assertObjectiveRef(ref) {
  assertClosed(ref, ['courseRef', 'objectiveId'], [], 'INVALID_OBJECTIVE_REF');
  assertCourseRef(ref.courseRef);
  nonEmpty(ref.objectiveId, 'INVALID_OBJECTIVE_REF');
  return ref;
}

function assertActivityRef(ref) {
  assertClosed(ref, ['courseRef', 'activityLineageId'], [], 'INVALID_ACTIVITY_REF');
  assertCourseRef(ref.courseRef);
  nonEmpty(ref.activityLineageId, 'INVALID_ACTIVITY_REF');
  return ref;
}

function assertSessionRef(ref) {
  assertClosed(ref, ['sessionId', 'planId'], [], 'INVALID_SESSION_REF');
  if (!IDS.session.test(ref.sessionId) || !IDS.plan.test(ref.planId)) fail('INVALID_SESSION_REF');
  return ref;
}

function courseKey(ref) {
  assertCourseRef(ref);
  return `${ref.packageLineageId}\0${ref.courseLineageId}`;
}

function objectiveKey(ref) {
  assertObjectiveRef(ref);
  return `${courseKey(ref.courseRef)}\0${ref.objectiveId}`;
}

function activityKey(ref) {
  assertActivityRef(ref);
  return `${courseKey(ref.courseRef)}\0${ref.activityLineageId}`;
}

function sameCanonical(left, right) {
  return canonicalJson(left) === canonicalJson(right);
}

function validateRecommendation(recommendation) {
  assertClosed(recommendation, [
    'recommendationVersion', 'objectiveRef', 'action', 'eligibleActivityRefs',
    'preferredActivityRef', 'estimatedMinutes', 'reasonCodes'
  ], [], 'INVALID_RECOMMENDATION');
  if (recommendation.recommendationVersion !== 'atlas.recommendation.v1' || !ACTION_CLASS[recommendation.action]) fail('INVALID_RECOMMENDATION');
  assertObjectiveRef(recommendation.objectiveRef);
  assertActivityRef(recommendation.preferredActivityRef);
  if (!sameCanonical(recommendation.objectiveRef.courseRef, recommendation.preferredActivityRef.courseRef)) fail('INVALID_RECOMMENDATION');
  if (!Array.isArray(recommendation.eligibleActivityRefs) || recommendation.eligibleActivityRefs.length === 0) fail('INVALID_RECOMMENDATION');
  const eligibleKeys = recommendation.eligibleActivityRefs.map(ref => {
    assertActivityRef(ref);
    if (!sameCanonical(ref.courseRef, recommendation.objectiveRef.courseRef)) fail('INVALID_RECOMMENDATION');
    return activityKey(ref);
  });
  if (new Set(eligibleKeys).size !== eligibleKeys.length || !eligibleKeys.includes(activityKey(recommendation.preferredActivityRef))) fail('INVALID_RECOMMENDATION');
  if (!Number.isInteger(recommendation.estimatedMinutes) || recommendation.estimatedMinutes < 1 || recommendation.estimatedMinutes > 30) fail('INVALID_RECOMMENDATION');
  if (!Array.isArray(recommendation.reasonCodes) || recommendation.reasonCodes.length === 0 || new Set(recommendation.reasonCodes).size !== recommendation.reasonCodes.length || recommendation.reasonCodes.some(code => !REASON_LABELS[code])) fail('INVALID_RECOMMENDATION');
  return recommendation;
}

function validatePlanItem(item, index) {
  if (!isObject(item)) fail('INVALID_SESSION_PLAN');
  const validationAction = ['attempt-validation', 'maintain-recent-validation'].includes(item.action);
  const optional = item.action === 'correct-practice' ? ['correctsEventId'] : validationAction ? ['validationBasisEventId', 'independenceClaimId'] : [];
  assertClosed(item, ['position', 'objectiveRef', 'activityRef', 'action', 'executionClass', 'estimatedMinutes'], optional, 'INVALID_SESSION_PLAN');
  if (item.position !== index || ACTION_CLASS[item.action] !== item.executionClass) fail('INVALID_SESSION_PLAN');
  if (!Number.isInteger(item.estimatedMinutes) || item.estimatedMinutes < 1 || item.estimatedMinutes > 30) fail('INVALID_SESSION_PLAN');
  assertObjectiveRef(item.objectiveRef);
  assertActivityRef(item.activityRef);
  if (!sameCanonical(item.objectiveRef.courseRef, item.activityRef.courseRef)) fail('INVALID_SESSION_PLAN');
  if (item.action === 'correct-practice' && !IDS.event.test(item.correctsEventId || '')) fail('INVALID_SESSION_PLAN');
  if (validationAction && (!IDS.event.test(item.validationBasisEventId || '') || !IDS.claim.test(item.independenceClaimId || ''))) fail('INVALID_SESSION_PLAN');
  return item;
}

function validatePlan(plan) {
  assertClosed(plan, ['planId', 'planDigest', 'payload'], [], 'INVALID_SESSION_PLAN');
  assertClosed(plan.payload, [
    'schemaVersion', 'engineVersion', 'courseRef', 'contentRevisionRef',
    'durationMinutes', 'items', 'totalEstimatedMinutes', 'unusedMinutes'
  ], [], 'INVALID_SESSION_PLAN');
  if (plan.payload.schemaVersion !== 'atlas.session-plan.v1') fail('INVALID_SESSION_PLAN');
  nonEmpty(plan.payload.engineVersion, 'INVALID_SESSION_PLAN');
  assertCourseRef(plan.payload.courseRef);
  assertContentRevisionRef(plan.payload.contentRevisionRef);
  if (plan.payload.contentRevisionRef.packageLineageId !== plan.payload.courseRef.packageLineageId) fail('INVALID_SESSION_PLAN');
  if (![5, 15, 30].includes(plan.payload.durationMinutes) || !Array.isArray(plan.payload.items)) fail('INVALID_SESSION_PLAN');
  let total = 0;
  plan.payload.items.forEach((item, index) => {
    validatePlanItem(item, index);
    if (!sameCanonical(item.objectiveRef.courseRef, plan.payload.courseRef)) fail('INVALID_SESSION_PLAN');
    total += item.estimatedMinutes;
  });
  if (!Number.isInteger(plan.payload.totalEstimatedMinutes) || plan.payload.totalEstimatedMinutes < 0 || !Number.isInteger(plan.payload.unusedMinutes) || plan.payload.unusedMinutes < 0) fail('INVALID_SESSION_PLAN');
  if (total !== plan.payload.totalEstimatedMinutes || total + plan.payload.unusedMinutes !== plan.payload.durationMinutes) fail('INVALID_SESSION_PLAN');
  const hex = hashHex('learnit.atlas.m1.v0.3/plan-digest', plan.payload);
  if (plan.planDigest !== `sha256:${hex}` || plan.planId !== `atlas-plan-sha256:${hex}`) fail('PLAN_ID_DIGEST_MISMATCH');
  return plan;
}

function validateRecommendationPlan(recommendation, plan) {
  validateRecommendation(recommendation);
  validatePlan(plan);
  const item = plan.payload.items[0];
  if (!item || objectiveKey(item.objectiveRef) !== objectiveKey(recommendation.objectiveRef) || activityKey(item.activityRef) !== activityKey(recommendation.preferredActivityRef) || item.action !== recommendation.action || item.estimatedMinutes !== recommendation.estimatedMinutes) fail('RECOMMENDATION_PLAN_MISMATCH');
  return true;
}

function validateResumeItemState(item, expectedPosition) {
  assertClosed(item, ['itemPosition', 'submissionOrdinal', 'assistance', 'assistanceUseIds'], [], 'INVALID_RESUME_STATE');
  if (item.itemPosition !== expectedPosition || !Number.isInteger(item.submissionOrdinal) || item.submissionOrdinal < 0) fail('INVALID_RESUME_STATE');
  if (!['none', 'used', 'unknown'].includes(item.assistance) || !Array.isArray(item.assistanceUseIds) || new Set(item.assistanceUseIds).size !== item.assistanceUseIds.length || item.assistanceUseIds.some(id => !IDS.assistance.test(id))) fail('INVALID_RESUME_STATE');
  if (item.assistance === 'used' && item.assistanceUseIds.length === 0) fail('INVALID_RESUME_STATE');
  if (item.assistance !== 'used' && item.assistanceUseIds.length !== 0) fail('INVALID_RESUME_STATE');
  return item;
}

function validateResumeState(resumeState, itemCount, context = {}) {
  assertClosed(resumeState, [
    'resumeVersion', 'sessionRef', 'courseRef', 'contentRevisionRef', 'planDigest',
    'nextItemPosition', 'focusTarget', 'lifecycleOrdinal', 'itemStates'
  ], ['lastCommittedEventId', 'responseDraft'], 'INVALID_RESUME_STATE');
  if (resumeState.resumeVersion !== 'atlas.resume-state.v1' || !SHA.test(resumeState.planDigest)) fail('INVALID_RESUME_STATE');
  assertSessionRef(resumeState.sessionRef);
  assertCourseRef(resumeState.courseRef);
  assertContentRevisionRef(resumeState.contentRevisionRef);
  if (!Number.isInteger(itemCount) || itemCount < 0 || !Number.isInteger(resumeState.nextItemPosition) || resumeState.nextItemPosition < 0 || resumeState.nextItemPosition > itemCount) fail('INVALID_RESUME_STATE');
  nonEmpty(resumeState.focusTarget, 'INVALID_RESUME_STATE');
  if (!Number.isInteger(resumeState.lifecycleOrdinal) || resumeState.lifecycleOrdinal < 0) fail('INVALID_RESUME_STATE');
  if (!Array.isArray(resumeState.itemStates) || resumeState.itemStates.length !== itemCount) fail('INVALID_RESUME_STATE');
  resumeState.itemStates.forEach((item, index) => validateResumeItemState(item, index));
  if ('lastCommittedEventId' in resumeState && !IDS.event.test(resumeState.lastCommittedEventId)) fail('INVALID_RESUME_STATE');
  if ('responseDraft' in resumeState) canonicalJson(resumeState.responseDraft);

  if (context.plan) {
    validatePlan(context.plan);
    if (itemCount !== context.plan.payload.items.length || resumeState.sessionRef.planId !== context.plan.planId || resumeState.planDigest !== context.plan.planDigest || !sameCanonical(resumeState.courseRef, context.plan.payload.courseRef) || !sameCanonical(resumeState.contentRevisionRef, context.plan.payload.contentRevisionRef)) fail('RESUME_PLAN_MISMATCH');
  }
  if (context.sessionRef) {
    assertSessionRef(context.sessionRef);
    if (!sameCanonical(resumeState.sessionRef, context.sessionRef)) fail('RESUME_SESSION_MISMATCH');
  }
  return resumeState;
}

function learnerObjectiveLabel(objectiveLabels, objectiveRef) {
  if (!objectiveLabels || typeof objectiveLabels !== 'object' || Array.isArray(objectiveLabels)) return null;
  const value = objectiveLabels[objectiveRef.objectiveId];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function renderToday({ recommendation, plan, resumeState, objectiveLabels = {} }) {
  if (!recommendation || !plan) return '<section class="atlas-m1 atlas-today" aria-labelledby="atlas-today-title"><h1 id="atlas-today-title">Aujourd’hui</h1><p>Aucune séance admissible pour le moment.</p></section>';
  validateRecommendationPlan(recommendation, plan);
  let resume = '';
  if (resumeState !== undefined && resumeState !== null) {
    validateResumeState(resumeState, plan.payload.items.length, { plan });
    resume = '<button type="button" data-atlas-action="resume">Reprendre la séance</button>';
  }
  const reasons = recommendation.reasonCodes.map(code => `<li>${esc(REASON_LABELS[code])}</li>`).join('');
  const items = plan.payload.items.map(item => {
    const objectiveLabel = learnerObjectiveLabel(objectiveLabels, item.objectiveRef);
    const objective = objectiveLabel
      ? `<br><small class="atlas-plan-objective">Objectif : ${esc(objectiveLabel)}</small>`
      : '';
    return `<li><span><span>${esc(ACTION_LABELS[item.action])}</span>${objective}</span><strong>${item.estimatedMinutes} min</strong></li>`;
  }).join('');
  return `<section class="atlas-m1 atlas-today" aria-labelledby="atlas-today-title"><h1 id="atlas-today-title">Aujourd’hui</h1><p class="atlas-duration">${plan.payload.durationMinutes} minutes · ${plan.payload.totalEstimatedMinutes} prévues</p><ul class="atlas-reasons">${reasons}</ul><ol class="atlas-plan-preview">${items}</ol><div class="atlas-actions">${resume}<button class="atlas-primary" type="button" data-atlas-action="start">Commencer</button></div></section>`;
}

module.exports = Object.freeze({
  REASON_LABELS, ACTION_CLASS, ACTION_LABELS, SHA, TS, IDS,
  fail, esc, isObject, assertClosed, nonEmpty,
  canonicalJson, hashHex, typedHash, without, assertCanonicalTimestamp,
  assertCourseRef, assertContentRevisionRef, assertObjectiveRef, assertActivityRef, assertSessionRef,
  courseKey, objectiveKey, activityKey, sameCanonical,
  validateRecommendation, validatePlanItem, validatePlan, validateRecommendationPlan,
  validateResumeItemState, validateResumeState, learnerObjectiveLabel, renderToday
});
