import { assertObjectiveProgressStorage } from '../ports/storage.js';

export const LEARNING_LOOP_V2_STATUSES = Object.freeze([
  'not-started',
  'training',
  'review-needed',
  'ready-for-validation',
  'validated-recently',
]);

const STATUS_SET = new Set(LEARNING_LOOP_V2_STATUSES);
const OBJECTIVE_FIELDS = [
  'objectiveId',
  'trainingAttempts',
  'latestTrainingCorrect',
  'needsReview',
  'validationAttempts',
  'latestValidationCorrect',
  'status',
];

export function deriveReviewQueue(course, records) {
  const byActivity = new Map(records.map((record) => [record.activityRevisionId, record]));
  return course.activities.filter(
    (activity) => byActivity.get(activity.activityRevisionId)?.correct === false,
  );
}

export function summarizeProgress(course, records) {
  const byActivity = new Map(records.map((record) => [record.activityRevisionId, record]));
  const completed = course.activities.filter((activity) => byActivity.get(activity.activityRevisionId)?.completed).length;
  return {
    courseInstallId: records[0]?.courseInstallId ?? null,
    completed,
    total: course.activities.length,
    isComplete: completed === course.activities.length,
    needsReview: deriveReviewQueue(course, records).length,
    records: course.activities
      .map((activity) => byActivity.get(activity.activityRevisionId))
      .filter(Boolean),
  };
}

export function buildProgressRecord({ courseInstallId, activity, answer, correct, previous, now = new Date() }) {
  const normalizedAnswer = structuredClone(answer);
  const record = {
    courseInstallId,
    activityLineageId: activity.activityLineageId,
    activityRevisionId: activity.activityRevisionId,
    attempts: (previous?.attempts ?? 0) + 1,
    lastAnswer: normalizedAnswer,
    correct: Boolean(correct),
    completed: true,
    updatedAt: now.toISOString(),
  };
  if (activity.type === 'qcm') record.selectedChoiceId = normalizedAnswer.choiceId;
  if (activity.type === 'fill') record.answers = normalizedAnswer;
  return record;
}

function optionalBoolean(value, field, objectiveId) {
  if (value === null || typeof value === 'boolean') return value;
  throw new TypeError(`Objective ${objectiveId} has invalid ${field}`);
}

function nonNegativeInteger(value, field, objectiveId) {
  if (Number.isInteger(value) && value >= 0) return value;
  throw new TypeError(`Objective ${objectiveId} has invalid ${field}`);
}

function normalizeObjectiveProjection(courseInstallId, course, projected, existing, now) {
  if (!Array.isArray(projected)) {
    throw new TypeError('projectObjectiveProgress() must return an array');
  }
  const authored = Array.isArray(course.objectives) ? course.objectives : [];
  const authoredIds = authored.map((objective) => objective.objectiveId);
  if (projected.length !== authoredIds.length) {
    throw new TypeError('Objective projection must contain every authored objective exactly once');
  }

  const existingById = new Map(existing.map((record) => [record.objectiveId, record]));
  const projectedById = new Map();
  for (const state of projected) {
    const objectiveId = state?.objectiveId;
    if (typeof objectiveId !== 'string' || !authoredIds.includes(objectiveId) || projectedById.has(objectiveId)) {
      throw new TypeError('Objective projection contains an unknown or duplicate objectiveId');
    }
    const normalized = {
      objectiveId,
      trainingAttempts: nonNegativeInteger(state.trainingAttempts, 'trainingAttempts', objectiveId),
      latestTrainingCorrect: optionalBoolean(state.latestTrainingCorrect, 'latestTrainingCorrect', objectiveId),
      needsReview: typeof state.needsReview === 'boolean'
        ? state.needsReview
        : (() => { throw new TypeError(`Objective ${objectiveId} has invalid needsReview`); })(),
      validationAttempts: nonNegativeInteger(state.validationAttempts, 'validationAttempts', objectiveId),
      latestValidationCorrect: optionalBoolean(state.latestValidationCorrect, 'latestValidationCorrect', objectiveId),
      status: STATUS_SET.has(state.status)
        ? state.status
        : (() => { throw new TypeError(`Objective ${objectiveId} has invalid status`); })(),
    };
    projectedById.set(objectiveId, normalized);
  }

  return authoredIds.map((objectiveId) => {
    const normalized = projectedById.get(objectiveId);
    const previous = existingById.get(objectiveId);
    const unchanged = previous && OBJECTIVE_FIELDS.every((field) => previous[field] === normalized[field]);
    return {
      schemaVersion: 1,
      courseInstallId,
      ...normalized,
      updatedAt: unchanged && typeof previous.updatedAt === 'string' ? previous.updatedAt : now.toISOString(),
    };
  });
}

function normalizeRecommendation(value) {
  if (value == null) return null;
  if (typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('recommendLearningAction() must return a data object or null');
  }
  return structuredClone(value);
}

function sameObjectiveRecords(left, right) {
  if (left.length !== right.length) return false;
  const byId = new Map(left.map((record) => [record.objectiveId, record]));
  return right.every((record) => {
    const previous = byId.get(record.objectiveId);
    return previous && OBJECTIVE_FIELDS.every((field) => previous[field] === record[field]);
  });
}

export function assertLearningLoopV2Integrations(integrations = {}) {
  const objectiveProgress = integrations?.objectiveProgress ?? null;
  const learningRecommendation = integrations?.learningRecommendation ?? null;
  if (objectiveProgress == null && learningRecommendation == null) {
    return Object.freeze({ objectiveProgress: null, learningRecommendation: null });
  }
  if (typeof objectiveProgress?.projectObjectiveProgress !== 'function') {
    throw new TypeError('Learning Loop V2 objectiveProgress.projectObjectiveProgress() is required');
  }
  if (learningRecommendation != null && typeof learningRecommendation.recommendLearningAction !== 'function') {
    throw new TypeError('Learning Loop V2 learningRecommendation.recommendLearningAction() is required');
  }
  return Object.freeze({ objectiveProgress, learningRecommendation });
}

export function createProgressService(storage, integrations = {}) {
  const resolved = assertLearningLoopV2Integrations(integrations);
  const learningLoopV2Enabled = Boolean(resolved.objectiveProgress);
  if (learningLoopV2Enabled) assertObjectiveProgressStorage(storage);

  async function projectCourseProgress(courseInstallId, course, records = null) {
    const activityProgress = records ?? await storage.listProgress(courseInstallId);
    const legacy = summarizeProgress(course, activityProgress);
    if (!learningLoopV2Enabled) return legacy;

    const existing = await storage.listObjectiveProgress(courseInstallId);
    const projected = await resolved.objectiveProgress.projectObjectiveProgress({
      course: structuredClone(course),
      activityProgress: structuredClone(activityProgress),
    });
    const objectiveRecords = normalizeObjectiveProjection(
      courseInstallId,
      course,
      projected,
      existing,
      new Date(),
    );
    if (!sameObjectiveRecords(existing, objectiveRecords)) {
      await storage.putObjectiveProgressRecords(objectiveRecords);
    }

    const objectiveProgress = objectiveRecords.map((record) => {
      const { schemaVersion, courseInstallId: storedCourseInstallId, updatedAt, ...state } = record;
      void schemaVersion;
      void storedCourseInstallId;
      void updatedAt;
      return state;
    });
    const reviewActivityRevisionIds = deriveReviewQueue(course, activityProgress)
      .map((activity) => activity.activityRevisionId);
    const recommendation = resolved.learningRecommendation
      ? normalizeRecommendation(await resolved.learningRecommendation.recommendLearningAction({
        course: structuredClone(course),
        objectiveProgress: structuredClone(objectiveProgress),
        activityProgress: structuredClone(activityProgress),
        reviewActivityRevisionIds,
      }))
      : null;

    return {
      ...legacy,
      objectives: objectiveProgress,
      recommendation,
    };
  }

  return {
    learningLoopV2Enabled,

    async getProgress(courseInstallId) {
      return storage.listProgress(courseInstallId);
    },

    async getCourseProgress(courseInstallId, course, records = null) {
      return projectCourseProgress(courseInstallId, course, records);
    },

    async getObjectiveProgress(courseInstallId, course) {
      const projection = await projectCourseProgress(courseInstallId, course);
      return {
        courseInstallId,
        objectives: projection.objectives ?? [],
        recommendation: projection.recommendation ?? null,
      };
    },

    async recordAttempt(input) {
      const previous = await storage.getProgress(input.courseInstallId, input.activity.activityRevisionId);
      const record = buildProgressRecord({ ...input, previous });
      await storage.putProgress(record);
      if (learningLoopV2Enabled) {
        if (!input.course) throw new TypeError('Learning Loop V2 recordAttempt() requires the authored course');
        const records = await storage.listProgress(input.courseInstallId);
        const projection = await projectCourseProgress(input.courseInstallId, input.course, records);
        return {
          ...record,
          objectiveProgress: projection.objectives,
          recommendation: projection.recommendation,
        };
      }
      return record;
    },

    summarize: summarizeProgress,
    reviewQueue: deriveReviewQueue,
  };
}
