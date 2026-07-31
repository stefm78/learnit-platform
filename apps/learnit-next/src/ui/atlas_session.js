'use strict';

const T = require('./atlas_today.js');

function fail(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function clone(value) {
  return typeof structuredClone === 'function' ? structuredClone(value) : JSON.parse(JSON.stringify(value));
}

function validateScoredExecution(record, plan, sessionRef, itemPosition) {
  T.assertClosed(record, [
    'executionVersion', 'executionId', 'sessionRef', 'courseRef', 'contentRevisionRef',
    'planDigest', 'itemPosition', 'submissionOrdinal', 'objectiveRef', 'activityRef',
    'action', 'executionClass', 'responseDigest', 'scoringRuleId', 'scoringRuleDigest',
    'outcome', 'assistance', 'assistanceUseIds', 'submittedAt', 'scoredAt'
  ], [], 'INVALID_CORE_COMMIT');
  if (record.executionVersion !== 'atlas.scored-execution.v1' || !T.IDS.execution.test(record.executionId) || !T.SHA.test(record.planDigest) || !T.SHA.test(record.responseDigest) || !T.SHA.test(record.scoringRuleDigest)) fail('INVALID_CORE_COMMIT');
  T.assertSessionRef(record.sessionRef);
  T.assertCourseRef(record.courseRef);
  T.assertContentRevisionRef(record.contentRevisionRef);
  T.assertObjectiveRef(record.objectiveRef);
  T.assertActivityRef(record.activityRef);
  T.nonEmpty(record.scoringRuleId, 'INVALID_CORE_COMMIT');
  if (!Number.isInteger(record.itemPosition) || record.itemPosition !== itemPosition || !Number.isInteger(record.submissionOrdinal) || record.submissionOrdinal < 1) fail('INVALID_CORE_COMMIT');
  if (T.ACTION_CLASS[record.action] !== record.executionClass || !['correct', 'incorrect'].includes(record.outcome) || !['none', 'used', 'unknown'].includes(record.assistance)) fail('INVALID_CORE_COMMIT');
  if (!Array.isArray(record.assistanceUseIds) || new Set(record.assistanceUseIds).size !== record.assistanceUseIds.length || record.assistanceUseIds.some(id => !T.IDS.assistance.test(id))) fail('INVALID_CORE_COMMIT');
  if (record.assistance === 'used' && record.assistanceUseIds.length === 0) fail('INVALID_CORE_COMMIT');
  if (record.assistance !== 'used' && record.assistanceUseIds.length !== 0) fail('INVALID_CORE_COMMIT');
  T.assertCanonicalTimestamp(record.submittedAt, 'INVALID_CORE_COMMIT');
  T.assertCanonicalTimestamp(record.scoredAt, 'INVALID_CORE_COMMIT');
  if (record.submittedAt > record.scoredAt) fail('INVALID_CORE_COMMIT');

  const item = plan.payload.items[itemPosition];
  if (!T.sameCanonical(record.sessionRef, sessionRef) || !T.sameCanonical(record.courseRef, plan.payload.courseRef) || !T.sameCanonical(record.contentRevisionRef, plan.payload.contentRevisionRef) || record.planDigest !== plan.planDigest) fail('CORE_COMMIT_SCOPE_MISMATCH');
  if (!T.sameCanonical(record.objectiveRef, item.objectiveRef) || !T.sameCanonical(record.activityRef, item.activityRef) || record.action !== item.action || record.executionClass !== item.executionClass) fail('CORE_COMMIT_ITEM_MISMATCH');
  const expectedId = T.typedHash('atlas-execution-sha256:', 'learnit.atlas.m1.v0.3/execution-id', T.without(record, 'executionId'));
  if (record.executionId !== expectedId) fail('CORE_COMMIT_IDENTITY_MISMATCH');
  return record;
}

function pedagogicalEventIdentity(event) {
  const identity = {
    eventVersion: event.eventVersion,
    kind: event.kind,
    executionId: event.executionId
  };
  if (event.kind === 'activity-corrected') identity.correctsEventId = event.correctsEventId;
  return identity;
}

function validatePedagogicalEvent(event, execution, planItem) {
  const expectedKind = planItem.executionClass === 'correction' ? 'activity-corrected' : 'activity-attempt';
  const optional = expectedKind === 'activity-corrected' ? ['correctsEventId'] : [];
  T.assertClosed(event, ['eventVersion', 'eventId', 'kind', 'objectiveRef', 'executionId', 'occurredAt'], optional, 'INVALID_CORE_COMMIT');
  if (event.eventVersion !== 'atlas.learning-event.v1' || !T.IDS.event.test(event.eventId) || event.kind !== expectedKind || !T.IDS.execution.test(event.executionId)) fail('INVALID_CORE_COMMIT');
  T.assertObjectiveRef(event.objectiveRef);
  T.assertCanonicalTimestamp(event.occurredAt, 'INVALID_CORE_COMMIT');
  if (!T.sameCanonical(event.objectiveRef, planItem.objectiveRef) || event.executionId !== execution.executionId) fail('CORE_COMMIT_EVENT_MISMATCH');
  if (expectedKind === 'activity-corrected' && (event.correctsEventId !== planItem.correctsEventId || !T.IDS.event.test(event.correctsEventId))) fail('CORE_COMMIT_EVENT_MISMATCH');
  const expectedId = T.typedHash('atlas-event-sha256:', 'learnit.atlas.m1.v0.3/event-id', pedagogicalEventIdentity(event));
  if (event.eventId !== expectedId) fail('CORE_COMMIT_IDENTITY_MISMATCH');
  return event;
}

function validateCommitResult(result, plan, sessionRef, committedPosition) {
  T.assertClosed(result, ['execution', 'event', 'resumeState'], [], 'INVALID_CORE_COMMIT');
  T.validatePlan(plan);
  T.assertSessionRef(sessionRef);
  if (!Number.isInteger(committedPosition) || committedPosition < 0 || committedPosition >= plan.payload.items.length) fail('INVALID_CORE_COMMIT');
  const execution = validateScoredExecution(result.execution, plan, sessionRef, committedPosition);
  const event = validatePedagogicalEvent(result.event, execution, plan.payload.items[committedPosition]);
  T.validateResumeState(result.resumeState, plan.payload.items.length, { plan, sessionRef });
  const expectedNext = Math.min(committedPosition + 1, plan.payload.items.length);
  const expectedFocus = expectedNext < plan.payload.items.length ? `atlas-session-item-${expectedNext}` : 'atlas-session-summary';
  if (result.resumeState.nextItemPosition !== expectedNext || result.resumeState.lastCommittedEventId !== event.eventId || result.resumeState.focusTarget !== expectedFocus) fail('CORE_COMMIT_RESUME_MISMATCH');
  const itemState = result.resumeState.itemStates[committedPosition];
  if (itemState.submissionOrdinal !== execution.submissionOrdinal || itemState.assistance !== execution.assistance || !T.sameCanonical(itemState.assistanceUseIds, execution.assistanceUseIds)) fail('CORE_COMMIT_RESUME_MISMATCH');
  return result;
}

function validateAssistanceConfirmation(confirmation, sessionRef, itemPosition, assistanceKind) {
  T.assertClosed(confirmation, ['committed', 'record'], [], 'INVALID_ASSISTANCE_CONFIRMATION');
  if (confirmation.committed !== true) fail('ASSISTANCE_NOT_PERSISTED');
  const record = confirmation.record;
  T.assertClosed(record, ['assistanceVersion', 'assistanceUseId', 'sessionRef', 'itemPosition', 'assistanceKind', 'recordedAt'], [], 'INVALID_ASSISTANCE_CONFIRMATION');
  if (record.assistanceVersion !== 'atlas.assistance-use.v1' || !T.IDS.assistance.test(record.assistanceUseId) || record.itemPosition !== itemPosition || record.assistanceKind !== assistanceKind || !['hint', 'guided-step', 'revealing-feedback', 'solution', 'previous-answer'].includes(record.assistanceKind)) fail('INVALID_ASSISTANCE_CONFIRMATION');
  T.assertSessionRef(record.sessionRef);
  T.assertCanonicalTimestamp(record.recordedAt, 'INVALID_ASSISTANCE_CONFIRMATION');
  if (!T.sameCanonical(record.sessionRef, sessionRef)) fail('INVALID_ASSISTANCE_CONFIRMATION');
  const expectedId = T.typedHash('atlas-assistance-sha256:', 'learnit.atlas.m1.v0.3/assistance-use-id', T.without(record, 'assistanceUseId'));
  if (record.assistanceUseId !== expectedId) fail('INVALID_ASSISTANCE_CONFIRMATION');
  return confirmation;
}

function createSessionController({ core, focus, plan: configuredPlan }) {
  if (!core || typeof core.commitActivitySubmission !== 'function' || typeof core.requestAssistance !== 'function') fail('CORE_PORT_REQUIRED');
  if (configuredPlan !== undefined) T.validatePlan(configuredPlan);
  let activePlan = configuredPlan || null;
  let activeSessionRef = null;
  let state = { sessionId: null, planId: null, planDigest: null, itemPosition: 0, committed: null, help: null };

  return Object.freeze({
    start(sessionRef, resumeState, plan) {
      activePlan = plan || activePlan;
      if (!activePlan) fail('SESSION_PLAN_REQUIRED');
      T.validatePlan(activePlan);
      T.assertSessionRef(sessionRef);
      T.validateResumeState(resumeState, activePlan.payload.items.length, { plan: activePlan, sessionRef });
      activeSessionRef = clone(sessionRef);
      state = {
        sessionId: sessionRef.sessionId,
        planId: sessionRef.planId,
        planDigest: activePlan.planDigest,
        itemPosition: resumeState.nextItemPosition,
        committed: null,
        help: null
      };
      focus?.(resumeState.focusTarget);
      return clone(state);
    },

    async submit(rawResponse) {
      if (!activePlan || !activeSessionRef || state.itemPosition >= activePlan.payload.items.length) fail('SESSION_NOT_ACTIVE');
      const committedPosition = state.itemPosition;
      const result = await core.commitActivitySubmission(state.sessionId, committedPosition, rawResponse);
      validateCommitResult(result, activePlan, activeSessionRef, committedPosition);
      state.committed = clone(result);
      state.itemPosition = result.resumeState.nextItemPosition;
      focus?.(result.resumeState.focusTarget);
      return result;
    },

    async requestHelp(kind) {
      if (!activePlan || !activeSessionRef || state.itemPosition >= activePlan.payload.items.length) fail('SESSION_NOT_ACTIVE');
      if (!['hint', 'guided-step', 'revealing-feedback', 'solution', 'previous-answer'].includes(kind)) fail('UNKNOWN_ASSISTANCE_KIND');
      const confirmation = await core.requestAssistance(state.sessionId, state.itemPosition, kind);
      validateAssistanceConfirmation(confirmation, activeSessionRef, state.itemPosition, kind);
      state.help = clone(confirmation.record);
      return confirmation;
    },

    snapshot() {
      return clone(state);
    }
  });
}

function renderSession({ plan, resumeState, activityHtml = '', feedbackHtml = '' }) {
  T.validatePlan(plan);
  T.validateResumeState(resumeState, plan.payload.items.length, { plan });
  const position = resumeState.nextItemPosition;
  if (plan.payload.items.length === 0) return '<section class="atlas-m1"><h1>Aucune séance en cours</h1></section>';
  if (position === plan.payload.items.length) return '<section class="atlas-m1 atlas-session atlas-session-complete" aria-labelledby="atlas-session-title"><h1 id="atlas-session-title" tabindex="-1">Séance terminée</h1><p>Les réponses ont été enregistrées. Consultez le bilan des preuves.</p><div class="atlas-actions"><button class="atlas-primary" type="button" data-atlas-summary>Voir le bilan</button></div></section>';
  const item = plan.payload.items[position];
  const labels = {
    practice: 'Entraînement',
    correction: 'Correction',
    validation: item.action === 'maintain-recent-validation' ? 'Reconfirmation' : 'Validation'
  };
  return `<section class="atlas-m1 atlas-session" aria-labelledby="atlas-session-title"><header><p>${T.esc(labels[item.executionClass] || 'Activité')}</p><h1 id="atlas-session-title">Étape ${item.position + 1} sur ${plan.payload.items.length}</h1></header><div class="atlas-activity" id="atlas-session-item-${item.position}">${activityHtml}</div>${feedbackHtml}<div class="atlas-actions"><button type="button" data-atlas-help="hint">Indice</button><button class="atlas-primary" type="button" data-atlas-submit>Valider la réponse</button></div></section>`;
}

module.exports = Object.freeze({
  validateResumeState: T.validateResumeState,
  validateScoredExecution,
  pedagogicalEventIdentity,
  validatePedagogicalEvent,
  validateCommitResult,
  validateAssistanceConfirmation,
  createSessionController,
  renderSession
});
