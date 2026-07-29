import {
  cloneFrozenAtlasValue,
  mergeLearningEventJournals,
  normalizeLearningEvent,
} from './atlas_events.js';

export const OBJECTIVE_EVIDENCE_PROJECTION_VERSION = 1;
export const OBJECTIVE_EVIDENCE_STATES = Object.freeze([
  'not-started',
  'training',
  'review-needed',
  'ready-for-validation',
  'validated-recently',
]);

export class ObjectiveEvidenceError extends TypeError {
  constructor(message, code = 'INVALID_OBJECTIVE_EVIDENCE') {
    super(message);
    this.name = 'ObjectiveEvidenceError';
    this.code = code;
  }
}

function normalizeObjectiveId(value, label = 'objectiveId') {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new ObjectiveEvidenceError(`${label} must be a non-empty string`, 'INVALID_OBJECTIVE_ID');
  }
  return value.trim();
}

function emptyEvidence(objectiveId) {
  return {
    objectiveId,
    projectionVersion: OBJECTIVE_EVIDENCE_PROJECTION_VERSION,
    practiceAttempts: 0,
    latestPracticeCorrect: null,
    needsReview: false,
    correctionsCompleted: 0,
    validationAttempts: 0,
    latestValidationCorrect: null,
    lastEvidenceAt: null,
    state: 'not-started',
    reasons: [],
  };
}

function isLater(left, right) {
  if (left === null) return false;
  if (right === null) return true;
  return left > right;
}

export function projectObjectiveEvidence(objectiveId, events) {
  const normalizedObjectiveId = normalizeObjectiveId(objectiveId);
  if (!Array.isArray(events)) {
    throw new ObjectiveEvidenceError('events must be an array', 'INVALID_EVENT_JOURNAL');
  }
  const journal = mergeLearningEventJournals([], events);
  const objectiveEvents = journal.filter((event) => event.objectiveId === normalizedObjectiveId);
  if (objectiveEvents.length === 0) return cloneFrozenAtlasValue(emptyEvidence(normalizedObjectiveId));

  const evidence = emptyEvidence(normalizedObjectiveId);
  let latestEvent = null;
  let latestFailureKey = null;
  let latestValidationSuccessKey = null;

  for (const rawEvent of objectiveEvents) {
    const event = normalizeLearningEvent(rawEvent);
    const orderKey = `${event.occurredAt}\u0000${event.eventId}`;
    latestEvent = event;
    evidence.lastEvidenceAt = event.occurredAt;

    if (event.kind === 'activity-attempt' && event.assessmentRole === 'practice') {
      evidence.practiceAttempts += 1;
      evidence.latestPracticeCorrect = event.outcome === 'correct';
      evidence.needsReview = event.outcome === 'incorrect';
      if (evidence.needsReview) latestFailureKey = orderKey;
    } else if (event.kind === 'activity-corrected') {
      evidence.correctionsCompleted += 1;
      evidence.needsReview = false;
    } else if (event.kind === 'activity-attempt' && event.assessmentRole === 'validation') {
      evidence.validationAttempts += 1;
      evidence.latestValidationCorrect = event.outcome === 'correct';
      evidence.needsReview = event.outcome === 'incorrect';
      if (evidence.needsReview) latestFailureKey = orderKey;
      if (event.outcome === 'correct') latestValidationSuccessKey = orderKey;
    }
  }

  if (evidence.needsReview) {
    evidence.state = 'review-needed';
  } else if (
    latestValidationSuccessKey !== null
    && !isLater(latestFailureKey, latestValidationSuccessKey)
  ) {
    evidence.state = 'validated-recently';
  } else if (latestEvent.kind === 'activity-corrected') {
    evidence.state = 'training';
  } else if (
    latestEvent.kind === 'activity-attempt'
    && latestEvent.assessmentRole === 'practice'
    && latestEvent.outcome === 'correct'
  ) {
    evidence.state = 'ready-for-validation';
  } else {
    evidence.state = 'training';
  }
  evidence.reasons = [];
  return cloneFrozenAtlasValue(evidence);
}

export function projectAllObjectiveEvidence(events, objectiveIds = []) {
  if (!Array.isArray(events)) {
    throw new ObjectiveEvidenceError('events must be an array', 'INVALID_EVENT_JOURNAL');
  }
  if (!Array.isArray(objectiveIds)) {
    throw new ObjectiveEvidenceError('objectiveIds must be an array', 'INVALID_OBJECTIVE_IDS');
  }
  const journal = mergeLearningEventJournals([], events);
  const ids = new Set(objectiveIds.map((value, index) => normalizeObjectiveId(value, `objectiveIds[${index}]`)));
  for (const event of journal) {
    if (Object.hasOwn(event, 'objectiveId')) ids.add(event.objectiveId);
  }
  const projections = [...ids]
    .sort((left, right) => left.localeCompare(right))
    .map((id) => projectObjectiveEvidence(id, journal));
  return cloneFrozenAtlasValue(projections);
}
