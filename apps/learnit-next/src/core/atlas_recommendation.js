import {
  AtlasEvidenceError,
  interpretObjectiveEvidence,
  normalizeObjectiveEvidenceSet,
} from './atlas_evidence.js';

export const ATLAS_RECOMMENDATION_VERSION = 1;
export const ATLAS_ESTIMATED_ACTION_MINUTES = 5;

export const ATLAS_RECOMMENDATION_ACTIONS = Object.freeze([
  'start-practice',
  'continue-practice',
  'correct-practice',
  'attempt-validation',
  'maintain-recent-validation',
]);

export const ATLAS_CANONICAL_REASON_CODES = Object.freeze([
  'NEW_OBJECTIVE',
  'PRACTICE_IN_PROGRESS',
  'RECENT_ERROR',
  'REVIEW_REQUIRED',
  'CORRECTION_COMPLETED',
  'NO_INDEPENDENT_VALIDATION',
  'VALIDATION_AVAILABLE',
  'RECENTLY_VALIDATED',
  'SESSION_TIME_LIMIT',
]);

const REASON_CODE_SET = new Set(ATLAS_CANONICAL_REASON_CODES);
const REASON_CODE_POSITION = new Map(
  ATLAS_CANONICAL_REASON_CODES.map((code, index) => [code, index]),
);
const PRACTICE_ACTIONS = new Set([
  'start-practice',
  'continue-practice',
  'correct-practice',
]);
const VALIDATION_ACTIONS = new Set([
  'attempt-validation',
  'maintain-recent-validation',
]);
const ASSESSMENT_ROLES = new Set(['practice', 'diagnostic', 'validation']);

const RULES_BY_STATE = Object.freeze({
  'review-needed': Object.freeze({ action: 'correct-practice', priority: 100 }),
  'ready-for-validation': Object.freeze({ action: 'attempt-validation', priority: 80 }),
  training: Object.freeze({ action: 'continue-practice', priority: 60 }),
  'not-started': Object.freeze({ action: 'start-practice', priority: 40 }),
  'validated-recently': Object.freeze({ action: 'maintain-recent-validation', priority: 20 }),
});

export class AtlasRecommendationError extends TypeError {
  constructor(message, code = 'INVALID_ATLAS_RECOMMENDATION_INPUT') {
    super(message);
    this.name = 'AtlasRecommendationError';
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

function normalizeIdentifier(value, label) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new AtlasRecommendationError(`${label} must be a non-empty string`);
  }
  return value.trim();
}

function normalizeObjective(objective, index) {
  if (!isRecord(objective)) {
    throw new AtlasRecommendationError(`objectives[${index}] must be an object`);
  }
  return {
    objectiveId: normalizeIdentifier(objective.objectiveId, `objectives[${index}].objectiveId`),
  };
}

function normalizeActivity(activity, index, knownObjectiveIds) {
  if (!isRecord(activity)) {
    throw new AtlasRecommendationError(`activities[${index}] must be an object`);
  }
  const activityLineageId = normalizeIdentifier(
    activity.activityLineageId,
    `activities[${index}].activityLineageId`,
  );
  if (!Array.isArray(activity.objectiveIds) || activity.objectiveIds.length === 0) {
    throw new AtlasRecommendationError(`activities[${index}].objectiveIds must be a non-empty array`);
  }
  const objectiveIds = activity.objectiveIds.map((objectiveId, objectiveIndex) => normalizeIdentifier(
    objectiveId,
    `activities[${index}].objectiveIds[${objectiveIndex}]`,
  ));
  if (new Set(objectiveIds).size !== objectiveIds.length) {
    throw new AtlasRecommendationError(
      `activity ${activityLineageId} contains duplicate objectiveIds`,
      'DUPLICATE_ACTIVITY_OBJECTIVE_ID',
    );
  }
  for (const objectiveId of objectiveIds) {
    if (!knownObjectiveIds.has(objectiveId)) {
      throw new AtlasRecommendationError(
        `activity ${activityLineageId} references unknown objectiveId: ${objectiveId}`,
        'UNKNOWN_ACTIVITY_OBJECTIVE_ID',
      );
    }
  }
  if (!ASSESSMENT_ROLES.has(activity.assessmentRole)) {
    throw new AtlasRecommendationError(
      `activity ${activityLineageId} has unsupported assessmentRole: ${String(activity.assessmentRole)}`,
      'UNSUPPORTED_ASSESSMENT_ROLE',
    );
  }
  return {
    activityLineageId,
    objectiveIds: [...objectiveIds].sort((left, right) => compareText(left, right)),
    assessmentRole: activity.assessmentRole,
  };
}

export function normalizeAtlasLearningContent(content) {
  if (!isRecord(content)) {
    throw new AtlasRecommendationError('content must be an object');
  }
  if (!Array.isArray(content.objectives) || content.objectives.length === 0) {
    throw new AtlasRecommendationError('content.objectives must be a non-empty array');
  }
  if (!Array.isArray(content.activities) || content.activities.length === 0) {
    throw new AtlasRecommendationError('content.activities must be a non-empty array');
  }

  const objectives = content.objectives.map(normalizeObjective);
  const objectiveIds = objectives.map(({ objectiveId }) => objectiveId);
  if (new Set(objectiveIds).size !== objectiveIds.length) {
    throw new AtlasRecommendationError('content objectives must not contain duplicate objectiveId values');
  }
  const knownObjectiveIds = new Set(objectiveIds);
  const activities = content.activities.map((activity, index) => normalizeActivity(
    activity,
    index,
    knownObjectiveIds,
  ));
  const activityIds = activities.map(({ activityLineageId }) => activityLineageId);
  if (new Set(activityIds).size !== activityIds.length) {
    throw new AtlasRecommendationError(
      'content activities must not contain duplicate activityLineageId values',
      'DUPLICATE_ACTIVITY_ID',
    );
  }

  return {
    objectives: [...objectives].sort((left, right) => compareText(left.objectiveId, right.objectiveId)),
    activities: [...activities].sort((left, right) => (
      compareText(left.activityLineageId, right.activityLineageId)
    )),
  };
}

export function normalizeAtlasReasonCodes(reasonCodes) {
  if (!Array.isArray(reasonCodes) || reasonCodes.length === 0) {
    throw new AtlasRecommendationError('reasonCodes must be a non-empty array', 'INVALID_REASON_CODES');
  }
  const normalized = reasonCodes.map((code, index) => {
    if (typeof code !== 'string' || !REASON_CODE_SET.has(code)) {
      throw new AtlasRecommendationError(
        `reasonCodes[${index}] is not in the canonical M1 registry: ${String(code)}`,
        'NON_CANONICAL_REASON_CODE',
      );
    }
    return code;
  });
  if (new Set(normalized).size !== normalized.length) {
    throw new AtlasRecommendationError('reasonCodes must not contain duplicates', 'INVALID_REASON_CODES');
  }
  return [...normalized].sort((left, right) => (
    REASON_CODE_POSITION.get(left) - REASON_CODE_POSITION.get(right)
  ));
}

function reasonCodesFor(interpretation) {
  const { evidence } = interpretation;
  const reasonCodes = [];
  if (evidence.state === 'not-started') {
    reasonCodes.push('NEW_OBJECTIVE');
  }
  if (evidence.state === 'training') {
    reasonCodes.push('PRACTICE_IN_PROGRESS');
  }
  if (interpretation.latestAttemptIncorrect) {
    reasonCodes.push('RECENT_ERROR', 'REVIEW_REQUIRED');
  }
  if (interpretation.correctionCompleted) {
    reasonCodes.push('CORRECTION_COMPLETED');
  }
  if (interpretation.missingIndependentValidation) {
    reasonCodes.push('NO_INDEPENDENT_VALIDATION');
  }
  if (interpretation.validationAvailable) {
    reasonCodes.push('VALIDATION_AVAILABLE');
  }
  if (interpretation.recentlyValidated) {
    reasonCodes.push('RECENTLY_VALIDATED');
  }
  return normalizeAtlasReasonCodes(reasonCodes);
}

function eligibleRoleForAction(action) {
  if (PRACTICE_ACTIONS.has(action)) return 'practice';
  if (VALIDATION_ACTIONS.has(action)) return 'validation';
  throw new AtlasRecommendationError(`unsupported action: ${action}`, 'UNSUPPORTED_RECOMMENDATION_ACTION');
}

function buildRecommendation(objectiveId, activities, evidence) {
  const interpretation = interpretObjectiveEvidence(evidence);
  const rule = RULES_BY_STATE[interpretation.evidence.state];
  if (!rule) {
    throw new AtlasRecommendationError(
      `no recommendation rule for state: ${interpretation.evidence.state}`,
      'UNSUPPORTED_EVIDENCE_STATE',
    );
  }
  const eligibleRole = eligibleRoleForAction(rule.action);
  const eligibleActivityIds = activities
    .filter((activity) => (
      activity.assessmentRole === eligibleRole
      && activity.objectiveIds.includes(objectiveId)
    ))
    .map(({ activityLineageId }) => activityLineageId)
    .sort((left, right) => compareText(left, right));

  if (eligibleActivityIds.length === 0) {
    throw new AtlasRecommendationError(
      `objective ${objectiveId} has no ${eligibleRole} activity for ${rule.action}`,
      'NO_ELIGIBLE_ACTIVITY',
    );
  }

  return {
    recommendationVersion: ATLAS_RECOMMENDATION_VERSION,
    objectiveId,
    action: rule.action,
    priority: rule.priority,
    reasonCodes: reasonCodesFor(interpretation),
    estimatedMinutes: ATLAS_ESTIMATED_ACTION_MINUTES,
    eligibleActivityIds,
  };
}

export function rankAtlasLearningRecommendations(content, evidenceRecords = []) {
  const normalizedContent = normalizeAtlasLearningContent(content);
  const objectiveIds = normalizedContent.objectives.map(({ objectiveId }) => objectiveId);
  let evidence;
  try {
    evidence = normalizeObjectiveEvidenceSet(objectiveIds, evidenceRecords);
  } catch (error) {
    if (error instanceof AtlasEvidenceError) throw error;
    throw new AtlasRecommendationError(String(error));
  }
  const byObjective = new Map(evidence.map((record) => [record.objectiveId, record]));

  return normalizedContent.objectives
    .map(({ objectiveId }) => buildRecommendation(
      objectiveId,
      normalizedContent.activities,
      byObjective.get(objectiveId),
    ))
    .sort((left, right) => (
      right.priority - left.priority
      || compareText(left.objectiveId, right.objectiveId)
    ));
}

export function recommendNextAtlasLearningAction(content, evidenceRecords = []) {
  return rankAtlasLearningRecommendations(content, evidenceRecords)[0] ?? null;
}
