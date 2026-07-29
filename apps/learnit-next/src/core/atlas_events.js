import {
  assertAtlasClock,
  createSystemAtlasClock,
  normalizeAtlasTimestamp,
} from './atlas_clock.js';

export const LEARNING_EVENT_VERSION = 1;
export const LEARNING_EVENT_KINDS = Object.freeze([
  'activity-attempt',
  'activity-corrected',
  'session-started',
  'session-interrupted',
  'session-completed',
]);
export const LEARNING_ASSESSMENT_ROLES = Object.freeze(['practice', 'validation']);
export const LEARNING_EVENT_OUTCOMES = Object.freeze([
  'correct',
  'incorrect',
  'completed',
  'interrupted',
]);
export const LEARNING_EVENT_ASSISTANCE = Object.freeze(['none', 'hint', 'review']);

const KIND_SET = new Set(LEARNING_EVENT_KINDS);
const ASSESSMENT_ROLE_SET = new Set(LEARNING_ASSESSMENT_ROLES);
const ASSISTANCE_SET = new Set(LEARNING_EVENT_ASSISTANCE);
const COMMON_FIELDS = Object.freeze([
  'eventId',
  'eventVersion',
  'occurredAt',
  'kind',
  'sessionId',
  'metadata',
]);
const ACTIVITY_FIELDS = Object.freeze([
  'courseLineageId',
  'objectiveId',
  'activityLineageId',
  'assessmentRole',
  'outcome',
  'assistance',
]);
const INTERRUPTION_CONTEXT_FIELDS = Object.freeze([
  'courseLineageId',
  'objectiveId',
  'activityLineageId',
]);

export class LearningEventError extends TypeError {
  constructor(message, code = 'INVALID_LEARNING_EVENT') {
    super(message);
    this.name = 'LearningEventError';
    this.code = code;
  }
}

function isPlainRecord(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function normalizeSerializable(value, label, seen = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new LearningEventError(`${label} contains a non-finite number`, 'NON_SERIALIZABLE_VALUE');
    }
    return value;
  }
  if (typeof value !== 'object') {
    throw new LearningEventError(`${label} contains a non-serializable value`, 'NON_SERIALIZABLE_VALUE');
  }
  if (seen.has(value)) {
    throw new LearningEventError(`${label} contains a cycle`, 'NON_SERIALIZABLE_VALUE');
  }
  seen.add(value);
  try {
    if (Array.isArray(value)) {
      return value.map((item, index) => normalizeSerializable(item, `${label}[${index}]`, seen));
    }
    if (!isPlainRecord(value)) {
      throw new LearningEventError(`${label} must contain only plain objects`, 'NON_SERIALIZABLE_VALUE');
    }
    const normalized = {};
    for (const key of Object.keys(value).sort()) {
      if (typeof key !== 'string' || key === '') {
        throw new LearningEventError(`${label} contains an invalid key`, 'NON_SERIALIZABLE_VALUE');
      }
      normalized[key] = normalizeSerializable(value[key], `${label}.${key}`, seen);
    }
    return normalized;
  } finally {
    seen.delete(value);
  }
}

function deepFreeze(value) {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const child of Object.values(value)) deepFreeze(child);
  }
  return value;
}

export function cloneFrozenAtlasValue(value, label = 'value') {
  return deepFreeze(normalizeSerializable(value, label));
}

export function canonicalAtlasJson(value, label = 'value') {
  return JSON.stringify(normalizeSerializable(value, label));
}

function nonEmptyString(value, label) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new LearningEventError(`${label} must be a non-empty string`, 'INVALID_LEARNING_EVENT_ID');
  }
  return value.trim();
}

function assertOwn(input, field) {
  if (!Object.hasOwn(input, field)) {
    throw new LearningEventError(`LearningEvent is missing ${field}`, 'MISSING_LEARNING_EVENT_FIELD');
  }
}

function allowedFieldsForKind(kind) {
  if (kind === 'activity-attempt' || kind === 'activity-corrected') {
    return new Set([...COMMON_FIELDS, ...ACTIVITY_FIELDS]);
  }
  if (kind === 'session-interrupted') {
    return new Set([...COMMON_FIELDS, 'outcome', ...INTERRUPTION_CONTEXT_FIELDS]);
  }
  if (kind === 'session-completed') {
    return new Set([...COMMON_FIELDS, 'outcome']);
  }
  return new Set(COMMON_FIELDS);
}

function rejectUnknownOrNonApplicableFields(input, kind) {
  const allowed = allowedFieldsForKind(kind);
  const unknown = Object.keys(input).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new LearningEventError(
      `LearningEvent ${kind} contains non-applicable or unknown fields: ${unknown.sort().join(', ')}`,
      'NON_APPLICABLE_LEARNING_EVENT_FIELD',
    );
  }
}

function normalizeActivityFields(input, kind) {
  for (const field of ACTIVITY_FIELDS) assertOwn(input, field);
  const assessmentRole = nonEmptyString(input.assessmentRole, 'assessmentRole');
  const outcome = nonEmptyString(input.outcome, 'outcome');
  const assistance = nonEmptyString(input.assistance, 'assistance');
  if (!ASSESSMENT_ROLE_SET.has(assessmentRole)) {
    throw new LearningEventError(`unsupported assessmentRole: ${assessmentRole}`);
  }
  if (!ASSISTANCE_SET.has(assistance)) {
    throw new LearningEventError(`unsupported assistance: ${assistance}`);
  }
  if (kind === 'activity-attempt' && !['correct', 'incorrect'].includes(outcome)) {
    throw new LearningEventError('activity-attempt outcome must be correct or incorrect');
  }
  if (kind === 'activity-corrected') {
    if (assessmentRole !== 'practice') {
      throw new LearningEventError('activity-corrected assessmentRole must be practice');
    }
    if (outcome !== 'completed') {
      throw new LearningEventError('activity-corrected outcome must be completed');
    }
    if (assistance !== 'review') {
      throw new LearningEventError('activity-corrected assistance must be review');
    }
  }
  return {
    courseLineageId: nonEmptyString(input.courseLineageId, 'courseLineageId'),
    objectiveId: nonEmptyString(input.objectiveId, 'objectiveId'),
    activityLineageId: nonEmptyString(input.activityLineageId, 'activityLineageId'),
    assessmentRole,
    outcome,
    assistance,
  };
}

export function normalizeLearningEvent(input) {
  if (!isPlainRecord(input)) {
    throw new LearningEventError('LearningEvent must be a plain object');
  }
  for (const field of COMMON_FIELDS) assertOwn(input, field);
  const kind = nonEmptyString(input.kind, 'kind');
  if (!KIND_SET.has(kind)) {
    throw new LearningEventError(`unsupported LearningEvent kind: ${kind}`);
  }
  rejectUnknownOrNonApplicableFields(input, kind);
  if (input.eventVersion !== LEARNING_EVENT_VERSION) {
    throw new LearningEventError(
      `eventVersion must be ${LEARNING_EVENT_VERSION}`,
      'UNSUPPORTED_LEARNING_EVENT_VERSION',
    );
  }
  if (!isPlainRecord(input.metadata)) {
    throw new LearningEventError('metadata must be a plain object');
  }
  const normalized = {
    eventId: nonEmptyString(input.eventId, 'eventId'),
    eventVersion: LEARNING_EVENT_VERSION,
    occurredAt: normalizeAtlasTimestamp(input.occurredAt, 'occurredAt'),
    kind,
    sessionId: nonEmptyString(input.sessionId, 'sessionId'),
  };

  if (kind === 'activity-attempt' || kind === 'activity-corrected') {
    Object.assign(normalized, normalizeActivityFields(input, kind));
  } else if (kind === 'session-interrupted') {
    assertOwn(input, 'outcome');
    if (input.outcome !== 'interrupted') {
      throw new LearningEventError('session-interrupted outcome must be interrupted');
    }
    normalized.outcome = 'interrupted';
    for (const field of INTERRUPTION_CONTEXT_FIELDS) {
      if (Object.hasOwn(input, field)) normalized[field] = nonEmptyString(input[field], field);
    }
  } else if (kind === 'session-completed') {
    assertOwn(input, 'outcome');
    if (input.outcome !== 'completed') {
      throw new LearningEventError('session-completed outcome must be completed');
    }
    normalized.outcome = 'completed';
  }

  normalized.metadata = normalizeSerializable(input.metadata, 'metadata');
  return deepFreeze(normalized);
}

export function createLearningEvent(
  fields,
  {
    clock = createSystemAtlasClock(),
    eventIdFactory = globalThis.crypto?.randomUUID?.bind(globalThis.crypto),
  } = {},
) {
  if (!isPlainRecord(fields)) {
    throw new LearningEventError('LearningEvent fields must be a plain object');
  }
  assertAtlasClock(clock);
  const eventId = Object.hasOwn(fields, 'eventId') ? fields.eventId : eventIdFactory?.();
  if (eventId === undefined) {
    throw new LearningEventError('eventId is required when no eventIdFactory is available');
  }
  return normalizeLearningEvent({
    ...fields,
    eventId,
    eventVersion: Object.hasOwn(fields, 'eventVersion')
      ? fields.eventVersion
      : LEARNING_EVENT_VERSION,
    occurredAt: Object.hasOwn(fields, 'occurredAt') ? fields.occurredAt : clock.now(),
    metadata: Object.hasOwn(fields, 'metadata') ? fields.metadata : {},
  });
}

export function compareLearningEvents(left, right) {
  const leftEvent = normalizeLearningEvent(left);
  const rightEvent = normalizeLearningEvent(right);
  return leftEvent.occurredAt.localeCompare(rightEvent.occurredAt)
    || leftEvent.eventId.localeCompare(rightEvent.eventId);
}

export function mergeLearningEventJournals(existingEvents, incomingEvents) {
  if (!Array.isArray(existingEvents) || !Array.isArray(incomingEvents)) {
    throw new LearningEventError('LearningEvent journals must be arrays', 'INVALID_EVENT_JOURNAL');
  }
  const byId = new Map();
  for (const [source, events] of [['existing', existingEvents], ['incoming', incomingEvents]]) {
    for (const event of events) {
      const normalized = normalizeLearningEvent(event);
      const canonical = canonicalAtlasJson(normalized, 'LearningEvent');
      const previous = byId.get(normalized.eventId);
      if (previous && previous.canonical !== canonical) {
        throw new LearningEventError(
          `eventId ${normalized.eventId} has conflicting immutable content in ${source} journal`,
          'LEARNING_EVENT_CONFLICT',
        );
      }
      if (!previous) byId.set(normalized.eventId, { event: normalized, canonical });
    }
  }
  const merged = [...byId.values()].map((entry) => entry.event);
  merged.sort((left, right) => left.occurredAt.localeCompare(right.occurredAt)
    || left.eventId.localeCompare(right.eventId));
  return deepFreeze(merged);
}
