export const OBJECTIVE_STATUSES = Object.freeze([
  'not-started',
  'training',
  'review-needed',
  'ready-for-validation',
  'validated-recently',
]);

export const OBJECTIVE_EVENT_TYPES = Object.freeze([
  'training-started',
  'training-result',
  'validation-result',
]);

const STATUS_SET = new Set(OBJECTIVE_STATUSES);
const EVENT_TYPE_SET = new Set(OBJECTIVE_EVENT_TYPES);
const CONTRACT_KEYS = [
  'objectiveId',
  'trainingAttempts',
  'latestTrainingCorrect',
  'needsReview',
  'validationAttempts',
  'latestValidationCorrect',
  'status',
];

export class ObjectiveProgressError extends TypeError {
  constructor(message, code = 'INVALID_OBJECTIVE_PROGRESS') {
    super(message);
    this.name = 'ObjectiveProgressError';
    this.code = code;
  }
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function normalizeObjectiveId(value, label = 'objectiveId') {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new ObjectiveProgressError(`${label} must be a non-empty string`, 'INVALID_OBJECTIVE_ID');
  }
  return value.trim();
}

function normalizeAttempts(value, label) {
  if (!Number.isInteger(value) || value < 0) {
    throw new ObjectiveProgressError(`${label} must be a non-negative integer`);
  }
  return value;
}

function normalizeLatest(value, attempts, label) {
  if (attempts === 0) {
    if (value !== null) {
      throw new ObjectiveProgressError(`${label} must be null when its attempt count is zero`);
    }
    return null;
  }
  if (typeof value !== 'boolean') {
    throw new ObjectiveProgressError(`${label} must be boolean after an attempt`);
  }
  return value;
}

function assertStateInvariants(state) {
  if (state.status === 'not-started') {
    if (
      state.trainingAttempts !== 0
      || state.validationAttempts !== 0
      || state.latestTrainingCorrect !== null
      || state.latestValidationCorrect !== null
      || state.needsReview
    ) {
      throw new ObjectiveProgressError('not-started state cannot contain attempts or review state');
    }
  }
  if (state.status === 'review-needed' && !state.needsReview) {
    throw new ObjectiveProgressError('review-needed status requires needsReview=true');
  }
  if (state.status !== 'review-needed' && state.needsReview) {
    throw new ObjectiveProgressError('needsReview=true requires review-needed status');
  }
  if (state.status === 'ready-for-validation' && state.latestTrainingCorrect !== true) {
    throw new ObjectiveProgressError('ready-for-validation requires a latest correct training result');
  }
  if (state.status === 'validated-recently' && state.latestValidationCorrect !== true) {
    throw new ObjectiveProgressError('validated-recently requires a latest correct validation result');
  }
}

export function createObjectiveProgress(objectiveId) {
  return {
    objectiveId: normalizeObjectiveId(objectiveId),
    trainingAttempts: 0,
    latestTrainingCorrect: null,
    needsReview: false,
    validationAttempts: 0,
    latestValidationCorrect: null,
    status: 'not-started',
  };
}

export function normalizeObjectiveProgress(input) {
  if (!isRecord(input)) {
    throw new ObjectiveProgressError('objective progress must be an object');
  }
  const unknown = Object.keys(input).filter((key) => !CONTRACT_KEYS.includes(key));
  if (unknown.length > 0) {
    throw new ObjectiveProgressError(`objective progress contains unknown fields: ${unknown.join(', ')}`);
  }
  for (const key of CONTRACT_KEYS) {
    if (!Object.hasOwn(input, key)) {
      throw new ObjectiveProgressError(`objective progress is missing ${key}`);
    }
  }

  const trainingAttempts = normalizeAttempts(input.trainingAttempts, 'trainingAttempts');
  const validationAttempts = normalizeAttempts(input.validationAttempts, 'validationAttempts');
  const state = {
    objectiveId: normalizeObjectiveId(input.objectiveId),
    trainingAttempts,
    latestTrainingCorrect: normalizeLatest(
      input.latestTrainingCorrect,
      trainingAttempts,
      'latestTrainingCorrect',
    ),
    needsReview: input.needsReview,
    validationAttempts,
    latestValidationCorrect: normalizeLatest(
      input.latestValidationCorrect,
      validationAttempts,
      'latestValidationCorrect',
    ),
    status: input.status,
  };
  if (typeof state.needsReview !== 'boolean') {
    throw new ObjectiveProgressError('needsReview must be boolean');
  }
  if (!STATUS_SET.has(state.status)) {
    throw new ObjectiveProgressError(`unsupported objective status: ${String(state.status)}`);
  }
  assertStateInvariants(state);
  return state;
}

function normalizeObjectiveEvent(event) {
  if (!isRecord(event)) {
    throw new ObjectiveProgressError('objective event must be an object', 'INVALID_OBJECTIVE_EVENT');
  }
  const type = event.type;
  if (!EVENT_TYPE_SET.has(type)) {
    throw new ObjectiveProgressError(
      `unsupported objective event type: ${String(type)}`,
      'INVALID_OBJECTIVE_EVENT',
    );
  }
  const allowedFields = type === 'training-started'
    ? new Set(['type', 'objectiveId'])
    : new Set(['type', 'objectiveId', 'correct']);
  const unknown = Object.keys(event).filter((key) => !allowedFields.has(key));
  if (unknown.length > 0) {
    throw new ObjectiveProgressError(
      `objective event contains unknown fields: ${unknown.join(', ')}`,
      'INVALID_OBJECTIVE_EVENT',
    );
  }
  const normalized = {
    type,
    objectiveId: normalizeObjectiveId(event.objectiveId, 'event.objectiveId'),
  };
  if (type === 'training-started') {
    if (Object.hasOwn(event, 'correct')) {
      throw new ObjectiveProgressError(
        'training-started must not contain correct',
        'INVALID_OBJECTIVE_EVENT',
      );
    }
    return normalized;
  }
  if (typeof event.correct !== 'boolean') {
    throw new ObjectiveProgressError(
      `${type} requires a boolean correct field`,
      'INVALID_OBJECTIVE_EVENT',
    );
  }
  return { ...normalized, correct: event.correct };
}

export function applyObjectiveEvent(progress, event) {
  const current = normalizeObjectiveProgress(progress);
  const normalizedEvent = normalizeObjectiveEvent(event);
  if (normalizedEvent.objectiveId !== current.objectiveId) {
    throw new ObjectiveProgressError(
      `event objective ${normalizedEvent.objectiveId} does not match ${current.objectiveId}`,
      'OBJECTIVE_ID_MISMATCH',
    );
  }

  if (normalizedEvent.type === 'training-started') {
    if (current.needsReview) return current;
    return { ...current, status: 'training' };
  }

  if (normalizedEvent.type === 'training-result') {
    return {
      ...current,
      trainingAttempts: current.trainingAttempts + 1,
      latestTrainingCorrect: normalizedEvent.correct,
      needsReview: !normalizedEvent.correct,
      status: normalizedEvent.correct ? 'ready-for-validation' : 'review-needed',
    };
  }

  return {
    ...current,
    validationAttempts: current.validationAttempts + 1,
    latestValidationCorrect: normalizedEvent.correct,
    needsReview: !normalizedEvent.correct,
    status: normalizedEvent.correct ? 'validated-recently' : 'review-needed',
  };
}

export function reduceObjectiveEvents(objectiveId, events) {
  if (!Array.isArray(events)) {
    throw new ObjectiveProgressError('events must be an array', 'INVALID_OBJECTIVE_EVENT');
  }
  return events.reduce(applyObjectiveEvent, createObjectiveProgress(objectiveId));
}
