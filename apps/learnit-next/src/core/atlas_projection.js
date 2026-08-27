'use strict';

const E = require('./atlas_events.js');

function key(reference) {
  return E.canonicalJson(reference);
}

function empty(reference) {
  return {
    evidenceVersion: 'atlas.objective-evidence.v1',
    objectiveRef: reference,
    practiceAttempts: 0,
    correctionsCompleted: 0,
    validationAttempts: 0,
    latestPracticeCorrect: null,
    latestValidationCorrect: null,
    lastValidationAt: null,
    lastEvidenceAt: null,
    state: 'not-started',
  };
}

function projectObjectiveEvidence(learningEvents, scoredExecutions, isValidationAdmissible) {
  if (!Array.isArray(learningEvents) || !Array.isArray(scoredExecutions)
      || typeof isValidationAdmissible !== 'function') E.fail('INVALID_PROJECTION_INPUT');
  const executions = new Map();
  for (const execution of scoredExecutions) {
    E.validateScoredExecution(execution);
    if (executions.has(execution.executionId)) E.fail('DUPLICATE_EXECUTION_ID');
    executions.set(execution.executionId, execution);
  }
  const result = new Map();
  const latestIncorrect = new Map();
  const corrected = new Set();
  const pedagogical = learningEvents
    .filter((event) => event.kind === 'activity-attempt' || event.kind === 'activity-corrected')
    .map(E.validatePedagogicalEvent)
    .sort((left, right) => left.occurredAt.localeCompare(right.occurredAt) || left.eventId.localeCompare(right.eventId));

  for (const event of pedagogical) {
    const objectiveKey = key(event.objectiveRef);
    const row = result.get(objectiveKey) || empty(event.objectiveRef);
    const execution = executions.get(event.executionId);
    if (!execution) E.fail('MISSING_EXECUTION');
    if (key(execution.objectiveRef) !== objectiveKey) E.fail('EVENT_EXECUTION_OBJECTIVE_MISMATCH');
    row.lastEvidenceAt = !row.lastEvidenceAt || event.occurredAt > row.lastEvidenceAt ? event.occurredAt : row.lastEvidenceAt;
    if (event.kind === 'activity-corrected') {
      if (execution.executionClass !== 'correction') E.fail('EVENT_EXECUTION_CLASS_MISMATCH');
      row.correctionsCompleted += 1;
      corrected.add(event.correctsEventId);
    } else if (execution.executionClass === 'practice') {
      row.practiceAttempts += 1;
      row.latestPracticeCorrect = execution.outcome === 'correct';
      if (execution.outcome === 'incorrect') {
        latestIncorrect.set(objectiveKey, event.eventId);
      } else if (row.state === 'review-needed' && row.latestValidationCorrect === false) {
        /*
         * A failed independent validation/reconfirmation means the objective
         * must be reviewed, not permanently trapped in review-needed. A later
         * successful practice is fresh evidence that permits a new validation
         * attempt. The previous validation timestamp/history is preserved; the
         * next successful attempt-validation starts a new memory cycle.
         */
        row.state = 'ready-for-validation';
      }
    } else if (execution.executionClass === 'validation') {
      row.validationAttempts += 1;
      row.latestValidationCorrect = execution.outcome === 'correct';
      const credit = execution.outcome === 'correct'
        && execution.assistance === 'none'
        && isValidationAdmissible(execution, event) === true;
      if (credit) {
        row.lastValidationAt = execution.scoredAt;
        row.state = 'validated-recently';
      } else if (execution.outcome === 'incorrect') {
        row.state = 'review-needed';
      }
    } else {
      E.fail('EVENT_EXECUTION_CLASS_MISMATCH');
    }
    result.set(objectiveKey, row);
  }

  for (const [objectiveKey, row] of result) {
    const unresolved = latestIncorrect.get(objectiveKey) && !corrected.has(latestIncorrect.get(objectiveKey));
    if (unresolved) row.state = 'review-needed';
    else if (row.state === 'not-started') {
      if (row.latestPracticeCorrect === true && row.practiceAttempts > 0) row.state = 'ready-for-validation';
      else if (row.practiceAttempts || row.correctionsCompleted) row.state = 'training';
    }
    E.deepFreeze(row);
  }
  return [...result.values()].sort((left, right) => key(left.objectiveRef).localeCompare(key(right.objectiveRef)));
}

module.exports = Object.freeze({ projectObjectiveEvidence });
