'use strict';

const POLICY_VERSION = 'atlas.memory-policy.v1';
const DAY_MS = 24 * 60 * 60 * 1000;
const INTERVAL_DAYS = Object.freeze([1, 3, 7, 21]);

function fail(code, detail = '') {
  const error = new Error(detail ? `${code}: ${detail}` : code);
  error.code = code;
  throw error;
}

function assertTimestamp(value) {
  if (typeof value !== 'string') fail('INVALID_MEMORY_TIMESTAMP');
  const millis = Date.parse(value);
  if (!Number.isFinite(millis) || new Date(millis).toISOString() !== value) {
    fail('INVALID_MEMORY_TIMESTAMP');
  }
  return value;
}

function compareExecutions(left, right) {
  return left.scoredAt.localeCompare(right.scoredAt)
    || left.executionId.localeCompare(right.executionId);
}

function validationHistory({
  executions,
  objectiveRef,
  admissibleExecutionIds,
  evidenceModule,
}) {
  if (!Array.isArray(executions) || !(admissibleExecutionIds instanceof Set)) {
    fail('INVALID_MEMORY_HISTORY_INPUT');
  }
  if (!evidenceModule || typeof evidenceModule.sameRef !== 'function') {
    fail('INVALID_MEMORY_EVIDENCE_MODULE');
  }

  return executions
    .filter(execution => (
      execution
      && execution.executionClass === 'validation'
      && ['attempt-validation', 'maintain-recent-validation'].includes(execution.action)
      && evidenceModule.sameRef(execution.objectiveRef, objectiveRef)
      && admissibleExecutionIds.has(execution.executionId)
    ))
    .slice()
    .sort(compareExecutions);
}

function currentCycle(history) {
  let initialIndex = -1;
  for (let index = history.length - 1; index >= 0; index -= 1) {
    const execution = history[index];
    if (
      execution.action === 'attempt-validation'
      && execution.outcome === 'correct'
      && execution.assistance === 'none'
    ) {
      initialIndex = index;
      break;
    }
  }

  if (initialIndex < 0) return Object.freeze([]);

  const cycle = [history[initialIndex]];
  for (let index = initialIndex + 1; index < history.length; index += 1) {
    const execution = history[index];
    if (
      execution.action === 'maintain-recent-validation'
      && execution.outcome === 'correct'
      && execution.assistance === 'none'
    ) {
      cycle.push(execution);
    }
  }
  return Object.freeze(cycle);
}

function intervalDaysAfter(reconfirmationCount) {
  if (!Number.isInteger(reconfirmationCount) || reconfirmationCount < 0) {
    fail('INVALID_RECONFIRMATION_COUNT');
  }
  return INTERVAL_DAYS[Math.min(reconfirmationCount, INTERVAL_DAYS.length - 1)];
}

function status({
  now,
  executions,
  objectiveRef,
  admissibleExecutionIds,
  evidenceModule,
}) {
  assertTimestamp(now);
  const history = validationHistory({
    executions,
    objectiveRef,
    admissibleExecutionIds,
    evidenceModule,
  });
  const cycle = currentCycle(history);

  if (!cycle.length) {
    return Object.freeze({
      policyVersion: POLICY_VERSION,
      hasIndependentValidation: false,
      reconfirmationCount: 0,
      intervalDays: null,
      basisExecution: null,
      dueAt: null,
      due: false,
    });
  }

  const basisExecution = cycle[cycle.length - 1];
  const reconfirmationCount = cycle.length - 1;
  const intervalDays = intervalDaysAfter(reconfirmationCount);
  const dueAt = new Date(
    Date.parse(assertTimestamp(basisExecution.scoredAt))
      + intervalDays * DAY_MS,
  ).toISOString();

  return Object.freeze({
    policyVersion: POLICY_VERSION,
    hasIndependentValidation: true,
    reconfirmationCount,
    intervalDays,
    basisExecution,
    dueAt,
    due: Date.parse(now) >= Date.parse(dueAt),
  });
}

module.exports = Object.freeze({
  POLICY_VERSION,
  DAY_MS,
  INTERVAL_DAYS,
  validationHistory,
  currentCycle,
  intervalDaysAfter,
  status,
});
