'use strict';

const V = require('./atlas_events.js');
const M = require('./atlas_memory.js');

const VERSION = 'atlas.transfer-evidence.v1';

function fail(code, detail = '') {
  const error = new Error(detail ? code + ': ' + detail : code);
  error.code = code;
  throw error;
}

function compareExecutions(left, right) {
  return left.scoredAt.localeCompare(right.scoredAt)
    || left.executionId.localeCompare(right.executionId);
}

function rowFor(objectiveRef) {
  return {
    transferEvidenceVersion: VERSION,
    objectiveRef,
    attempts: 0,
    independentSuccesses: 0,
    lastAttemptAt: null,
    lastIndependentSuccessAt: null,
  };
}

function projectTransferEvidence({ learningEvents, scoredExecutions, evidenceModule }) {
  if (!Array.isArray(learningEvents) || !Array.isArray(scoredExecutions)) {
    fail('INVALID_TRANSFER_EVIDENCE_INPUT');
  }
  if (!evidenceModule || typeof evidenceModule.canonicalRefKey !== 'function'
      || typeof evidenceModule.sameRef !== 'function') {
    fail('INVALID_TRANSFER_EVIDENCE_MODULE');
  }

  const attemptEvents = new Map();
  for (const event of learningEvents.filter(item => item && item.kind === 'activity-attempt')) {
    V.validatePedagogicalEvent(event);
    if (attemptEvents.has(event.executionId)) fail('DUPLICATE_TRANSFER_EVENT');
    attemptEvents.set(event.executionId, event);
  }

  const rows = new Map();
  const transferExecutions = scoredExecutions
    .filter(execution => execution && execution.action === 'attempt-transfer')
    .map(execution => V.validateScoredExecution(execution))
    .sort(compareExecutions);

  for (const execution of transferExecutions) {
    if (execution.executionClass !== 'transfer') fail('TRANSFER_CLASS_MISMATCH');
    const event = attemptEvents.get(execution.executionId);
    if (!event) fail('MISSING_TRANSFER_EVENT');
    if (!evidenceModule.sameRef(event.objectiveRef, execution.objectiveRef)) {
      fail('TRANSFER_EVENT_OBJECTIVE_MISMATCH');
    }
    const key = evidenceModule.canonicalRefKey(execution.objectiveRef);
    const row = rows.get(key) || rowFor(execution.objectiveRef);
    row.attempts += 1;
    row.lastAttemptAt = execution.scoredAt;
    if (execution.outcome === 'correct' && execution.assistance === 'none') {
      row.independentSuccesses += 1;
      row.lastIndependentSuccessAt = execution.scoredAt;
    }
    rows.set(key, row);
  }

  return Object.freeze(
    [...rows.values()]
      .sort((left, right) => (
        evidenceModule.canonicalRefKey(left.objectiveRef)
          .localeCompare(evidenceModule.canonicalRefKey(right.objectiveRef))
      ))
      .map(row => Object.freeze({...row})),
  );
}

function status({
  learningEvents,
  scoredExecutions,
  objectiveRef,
  admissibleExecutionIds,
  evidenceModule,
}) {
  if (!Array.isArray(scoredExecutions) || !(admissibleExecutionIds instanceof Set)) {
    fail('INVALID_TRANSFER_STATUS_INPUT');
  }
  if (!evidenceModule || typeof evidenceModule.sameRef !== 'function') {
    fail('INVALID_TRANSFER_EVIDENCE_MODULE');
  }

  const validationHistory = M.validationHistory({
    executions: scoredExecutions,
    objectiveRef,
    admissibleExecutionIds,
    evidenceModule,
  });
  const cycle = M.currentCycle(validationHistory);
  const evidence = projectTransferEvidence({
    learningEvents,
    scoredExecutions,
    evidenceModule,
  }).find(row => evidenceModule.sameRef(row.objectiveRef, objectiveRef))
    || Object.freeze(rowFor(objectiveRef));

  if (cycle.length < 2) {
    return Object.freeze({
      transferEvidence: evidence,
      reconfirmationCount: Math.max(0, cycle.length - 1),
      basisExecution: cycle.at(-1) || null,
      latestTransferAttempt: null,
      eligible: false,
    });
  }

  const initialValidation = cycle[0];
  const latestReconfirmation = cycle[cycle.length - 1];
  if (latestReconfirmation.action !== 'maintain-recent-validation') {
    fail('TRANSFER_RECONFIRMATION_BASIS_INVALID');
  }

  const transferAttempts = scoredExecutions
    .filter(execution => (
      execution
      && execution.action === 'attempt-transfer'
      && execution.executionClass === 'transfer'
      && evidenceModule.sameRef(execution.objectiveRef, objectiveRef)
      && compareExecutions(execution, initialValidation) >= 0
    ))
    .map(execution => V.validateScoredExecution(execution))
    .sort(compareExecutions);

  const latestTransferAttempt = transferAttempts.at(-1) || null;
  const eligible = latestTransferAttempt === null
    || compareExecutions(latestTransferAttempt, latestReconfirmation) < 0;

  return Object.freeze({
    transferEvidence: evidence,
    reconfirmationCount: cycle.length - 1,
    basisExecution: latestReconfirmation,
    latestTransferAttempt,
    eligible,
  });
}

module.exports = Object.freeze({
  VERSION,
  compareExecutions,
  projectTransferEvidence,
  status,
});
