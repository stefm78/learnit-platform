import {
  createObjectiveProgress,
  normalizeObjectiveProgress,
  ObjectiveProgressError,
} from './objective_progress.js';

export const LEARNING_RECOMMENDATION_ACTIONS = Object.freeze([
  'correct',
  'validate',
  'continue-training',
  'start-training',
  'revisit-later',
]);

const RECOMMENDATION_BY_STATUS = Object.freeze({
  'review-needed': Object.freeze({ priority: 0, action: 'correct', reason: 'needs-review' }),
  'ready-for-validation': Object.freeze({ priority: 1, action: 'validate', reason: 'ready-for-validation' }),
  training: Object.freeze({ priority: 2, action: 'continue-training', reason: 'training-in-progress' }),
  'not-started': Object.freeze({ priority: 3, action: 'start-training', reason: 'not-started' }),
  'validated-recently': Object.freeze({
    priority: 4,
    action: 'revisit-later',
    reason: 'validated-recently-not-durable',
  }),
});

function normalizeObjectiveIds(objectiveIds) {
  if (!Array.isArray(objectiveIds)) {
    throw new ObjectiveProgressError('objectiveIds must be an array', 'INVALID_OBJECTIVE_LIST');
  }
  const seen = new Set();
  return objectiveIds.map((value) => {
    const normalized = createObjectiveProgress(value).objectiveId;
    if (seen.has(normalized)) {
      throw new ObjectiveProgressError(
        `duplicate objectiveId: ${normalized}`,
        'DUPLICATE_OBJECTIVE_ID',
      );
    }
    seen.add(normalized);
    return normalized;
  });
}

function indexProgress(objectiveIds, progressRecords) {
  if (!Array.isArray(progressRecords)) {
    throw new ObjectiveProgressError('progressRecords must be an array', 'INVALID_PROGRESS_LIST');
  }
  const allowed = new Set(objectiveIds);
  const byObjective = new Map();
  for (const input of progressRecords) {
    const progress = normalizeObjectiveProgress(input);
    if (!allowed.has(progress.objectiveId)) {
      throw new ObjectiveProgressError(
        `progress references unknown objectiveId: ${progress.objectiveId}`,
        'UNKNOWN_OBJECTIVE_ID',
      );
    }
    if (byObjective.has(progress.objectiveId)) {
      throw new ObjectiveProgressError(
        `duplicate progress for objectiveId: ${progress.objectiveId}`,
        'DUPLICATE_OBJECTIVE_PROGRESS',
      );
    }
    byObjective.set(progress.objectiveId, progress);
  }
  return byObjective;
}

export function rankLearningRecommendations(objectiveIds, progressRecords = []) {
  const orderedIds = normalizeObjectiveIds(objectiveIds);
  const byObjective = indexProgress(orderedIds, progressRecords);
  return orderedIds
    .map((objectiveId, authorIndex) => {
      const progress = byObjective.get(objectiveId) ?? createObjectiveProgress(objectiveId);
      const recommendation = RECOMMENDATION_BY_STATUS[progress.status];
      return {
        objectiveId,
        status: progress.status,
        needsReview: progress.needsReview,
        action: recommendation.action,
        reason: recommendation.reason,
        priority: recommendation.priority,
        authorIndex,
      };
    })
    .sort((left, right) => left.priority - right.priority || left.authorIndex - right.authorIndex)
    .map(({ priority, authorIndex, ...recommendation }) => recommendation);
}

export function recommendNextObjective(objectiveIds, progressRecords = []) {
  return rankLearningRecommendations(objectiveIds, progressRecords)[0] ?? null;
}
