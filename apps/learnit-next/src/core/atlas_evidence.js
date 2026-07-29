export const ATLAS_EVIDENCE_PROJECTION_VERSION = 1;

export const ATLAS_OBJECTIVE_EVIDENCE_STATES = Object.freeze([
  'not-started',
  'training',
  'review-needed',
  'ready-for-validation',
  'validated-recently',
]);

const STATE_SET = new Set(ATLAS_OBJECTIVE_EVIDENCE_STATES);
const CONTRACT_FIELDS = Object.freeze([
  'objectiveId',
  'projectionVersion',
  'practiceAttempts',
  'latestPracticeCorrect',
  'needsReview',
  'correctionsCompleted',
  'validationAttempts',
  'latestValidationCorrect',
  'lastEvidenceAt',
  'state',
  'reasons',
]);
const CONTRACT_FIELD_SET = new Set(CONTRACT_FIELDS);
const ISO_INSTANT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;

export class AtlasEvidenceError extends TypeError {
  constructor(message, code = 'INVALID_OBJECTIVE_EVIDENCE') {
    super(message);
    this.name = 'AtlasEvidenceError';
    this.code = code;
  }
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function compareText(left, right) {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function normalizeIdentifier(value, label = 'objectiveId') {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new AtlasEvidenceError(`${label} must be a non-empty string`, 'INVALID_OBJECTIVE_ID');
  }
  return value.trim();
}

function normalizeCount(value, label) {
  if (!Number.isInteger(value) || value < 0) {
    throw new AtlasEvidenceError(`${label} must be a non-negative integer`);
  }
  return value;
}

function normalizeLatest(value, attempts, label) {
  if (attempts === 0) {
    if (value !== null) {
      throw new AtlasEvidenceError(`${label} must be null when its attempt count is zero`);
    }
    return null;
  }
  if (typeof value !== 'boolean') {
    throw new AtlasEvidenceError(`${label} must be boolean after an attempt`);
  }
  return value;
}

function normalizeTimestamp(value) {
  if (value === null) return null;
  if (typeof value !== 'string' || !ISO_INSTANT.test(value)) {
    throw new AtlasEvidenceError('lastEvidenceAt must be null or a canonical UTC timestamp');
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString() !== value) {
    throw new AtlasEvidenceError('lastEvidenceAt must be a valid canonical UTC timestamp');
  }
  return value;
}

function normalizeReasons(value) {
  if (!Array.isArray(value)) {
    throw new AtlasEvidenceError('reasons must be an array');
  }
  const normalized = value.map((reason, index) => {
    if (typeof reason !== 'string' || reason.trim() === '') {
      throw new AtlasEvidenceError(`reasons[${index}] must be a non-empty string`);
    }
    return reason.trim();
  });
  if (new Set(normalized).size !== normalized.length) {
    throw new AtlasEvidenceError('reasons must not contain duplicates');
  }
  return [...normalized].sort((left, right) => compareText(left, right));
}

function assertContractShape(input) {
  const unknown = Object.keys(input).filter((key) => !CONTRACT_FIELD_SET.has(key));
  if (unknown.length > 0) {
    throw new AtlasEvidenceError(`objective evidence contains unknown fields: ${unknown.join(', ')}`);
  }
  const missing = CONTRACT_FIELDS.filter((key) => !Object.hasOwn(input, key));
  if (missing.length > 0) {
    throw new AtlasEvidenceError(`objective evidence is missing: ${missing.join(', ')}`);
  }
}

function assertStateInvariants(evidence) {
  const {
    practiceAttempts,
    latestPracticeCorrect,
    needsReview,
    correctionsCompleted,
    validationAttempts,
    latestValidationCorrect,
    lastEvidenceAt,
    state,
    reasons,
  } = evidence;

  if (correctionsCompleted > practiceAttempts) {
    throw new AtlasEvidenceError('correctionsCompleted cannot exceed practiceAttempts');
  }

  if (state === 'not-started') {
    const containsEvidence = practiceAttempts !== 0
      || validationAttempts !== 0
      || correctionsCompleted !== 0
      || latestPracticeCorrect !== null
      || latestValidationCorrect !== null
      || needsReview
      || lastEvidenceAt !== null
      || reasons.length !== 0;
    if (containsEvidence) {
      throw new AtlasEvidenceError('not-started evidence must be empty');
    }
    return;
  }

  if (lastEvidenceAt === null) {
    throw new AtlasEvidenceError(`${state} evidence requires lastEvidenceAt`);
  }

  if (state === 'review-needed') {
    if (!needsReview) {
      throw new AtlasEvidenceError('review-needed state requires needsReview=true');
    }
    if (latestPracticeCorrect !== false && latestValidationCorrect !== false) {
      throw new AtlasEvidenceError('review-needed state requires a latest incorrect attempt');
    }
  } else if (needsReview) {
    throw new AtlasEvidenceError('needsReview=true requires review-needed state');
  }

  if (state === 'ready-for-validation') {
    if (practiceAttempts === 0 || latestPracticeCorrect !== true) {
      throw new AtlasEvidenceError('ready-for-validation requires a correct practice attempt');
    }
    if (latestValidationCorrect === true) {
      throw new AtlasEvidenceError('ready-for-validation cannot already contain a successful validation');
    }
  }

  if (state === 'validated-recently') {
    if (validationAttempts === 0 || latestValidationCorrect !== true) {
      throw new AtlasEvidenceError('validated-recently requires a successful validation attempt');
    }
  }
}

export function createEmptyObjectiveEvidence(objectiveId) {
  return {
    objectiveId: normalizeIdentifier(objectiveId),
    projectionVersion: ATLAS_EVIDENCE_PROJECTION_VERSION,
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

export function normalizeObjectiveEvidence(input) {
  if (!isRecord(input)) {
    throw new AtlasEvidenceError('objective evidence must be an object');
  }
  assertContractShape(input);
  if (input.projectionVersion !== ATLAS_EVIDENCE_PROJECTION_VERSION) {
    throw new AtlasEvidenceError(
      `unsupported projectionVersion: ${String(input.projectionVersion)}`,
      'UNSUPPORTED_PROJECTION_VERSION',
    );
  }

  const practiceAttempts = normalizeCount(input.practiceAttempts, 'practiceAttempts');
  const validationAttempts = normalizeCount(input.validationAttempts, 'validationAttempts');
  const evidence = {
    objectiveId: normalizeIdentifier(input.objectiveId),
    projectionVersion: ATLAS_EVIDENCE_PROJECTION_VERSION,
    practiceAttempts,
    latestPracticeCorrect: normalizeLatest(
      input.latestPracticeCorrect,
      practiceAttempts,
      'latestPracticeCorrect',
    ),
    needsReview: input.needsReview,
    correctionsCompleted: normalizeCount(input.correctionsCompleted, 'correctionsCompleted'),
    validationAttempts,
    latestValidationCorrect: normalizeLatest(
      input.latestValidationCorrect,
      validationAttempts,
      'latestValidationCorrect',
    ),
    lastEvidenceAt: normalizeTimestamp(input.lastEvidenceAt),
    state: input.state,
    reasons: normalizeReasons(input.reasons),
  };

  if (typeof evidence.needsReview !== 'boolean') {
    throw new AtlasEvidenceError('needsReview must be boolean');
  }
  if (!STATE_SET.has(evidence.state)) {
    throw new AtlasEvidenceError(`unsupported evidence state: ${String(evidence.state)}`);
  }
  assertStateInvariants(evidence);
  return evidence;
}

export function interpretObjectiveEvidence(input) {
  const evidence = normalizeObjectiveEvidence(input);
  const hasSuccessfulIndependentValidation = evidence.validationAttempts > 0
    && evidence.latestValidationCorrect === true;
  return {
    evidence,
    hasPracticeEvidence: evidence.practiceAttempts > 0,
    hasSuccessfulIndependentValidation,
    missingIndependentValidation: !hasSuccessfulIndependentValidation,
    latestAttemptIncorrect: evidence.state === 'review-needed',
    correctionCompleted: evidence.correctionsCompleted > 0,
    validationAvailable: evidence.state === 'ready-for-validation',
    recentlyValidated: evidence.state === 'validated-recently'
      && hasSuccessfulIndependentValidation,
  };
}

export function normalizeObjectiveEvidenceSet(objectiveIds, records = []) {
  if (!Array.isArray(objectiveIds)) {
    throw new AtlasEvidenceError('objectiveIds must be an array', 'INVALID_OBJECTIVE_LIST');
  }
  if (!Array.isArray(records)) {
    throw new AtlasEvidenceError('evidence records must be an array', 'INVALID_EVIDENCE_LIST');
  }

  const normalizedIds = objectiveIds.map((value, index) => normalizeIdentifier(
    value,
    `objectiveIds[${index}]`,
  ));
  if (new Set(normalizedIds).size !== normalizedIds.length) {
    throw new AtlasEvidenceError('objectiveIds must not contain duplicates', 'DUPLICATE_OBJECTIVE_ID');
  }

  const allowed = new Set(normalizedIds);
  const byObjective = new Map();
  for (const record of records) {
    const normalized = normalizeObjectiveEvidence(record);
    if (!allowed.has(normalized.objectiveId)) {
      throw new AtlasEvidenceError(
        `evidence references unknown objectiveId: ${normalized.objectiveId}`,
        'UNKNOWN_OBJECTIVE_ID',
      );
    }
    if (byObjective.has(normalized.objectiveId)) {
      throw new AtlasEvidenceError(
        `duplicate evidence for objectiveId: ${normalized.objectiveId}`,
        'DUPLICATE_OBJECTIVE_EVIDENCE',
      );
    }
    byObjective.set(normalized.objectiveId, normalized);
  }

  return normalizedIds
    .map((objectiveId) => byObjective.get(objectiveId) ?? createEmptyObjectiveEvidence(objectiveId))
    .sort((left, right) => compareText(left.objectiveId, right.objectiveId));
}
