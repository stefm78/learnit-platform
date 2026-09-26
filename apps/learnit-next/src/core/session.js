import {
  ActivityResponseValidationError,
  evaluateActivityResponse,
} from './activity_semantics.js';
import { LEARNING_LOOP_V2_STATUSES } from './progress.js';

export class AnswerValidationError extends Error {
  constructor(message, code = 'invalid_answer') {
    super(message);
    this.name = 'AnswerValidationError';
    this.code = code;
  }
}

export const LEARNING_LOOP_V2_SESSION_META_KEY = 'learningLoopV2Session';

function evaluation(activity, answer) {
  try {
    return evaluateActivityResponse(activity, answer);
  } catch (error) {
    if (error instanceof ActivityResponseValidationError) {
      throw new AnswerValidationError(error.message, error.code);
    }
    throw error;
  }
}

export function evaluateAnswer(activity, answer) {
  const result = evaluation(activity, answer);
  return result.scored
    ? { normalized: result.normalized, correct: result.correct, scored: true }
    : { normalized: result.normalized, correct: null, scored: false, completed: true };
}

function nextIncompleteIndex(course, records, preferredIndex = null) {
  const complete = new Set(records.filter(record => record.completed).map(record => record.activityRevisionId));
  if (
    Number.isInteger(preferredIndex)
    && preferredIndex >= 0
    && preferredIndex < course.activities.length
    && !complete.has(course.activities[preferredIndex].activityRevisionId)
  ) return preferredIndex;
  return course.activities.findIndex(activity => !complete.has(activity.activityRevisionId));
}

const LEGACY_SESSION_PROVENANCE_UNAVAILABLE = 'LEGACY_SESSION_PROVENANCE_UNAVAILABLE';
const SESSION_PROVENANCE_UNAVAILABLE = 'SESSION_PROVENANCE_UNAVAILABLE';
const INVALID_SESSION_PROVENANCE = 'INVALID_SESSION_PROVENANCE';
const SESSION_PROVENANCE_ATTEMPTS_REGRESSED = 'SESSION_PROVENANCE_ATTEMPTS_REGRESSED';
const QUALIFIED_OBJECTIVE_STATES = new Set(LEARNING_LOOP_V2_STATUSES);

function validLearningLoopNavigationMeta(meta, activeCourseMeta) {
  return meta
    && (meta.schemaVersion === 1 || meta.schemaVersion === 2)
    && meta.courseInstallId === activeCourseMeta.courseInstallId
    && meta.mode === (activeCourseMeta.mode ?? 'learn');
}

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function exactRecordKeys(record, expectedKeys) {
  if (!isRecord(record)) return false;
  const actual = Object.keys(record).sort();
  const expected = [...expectedKeys].sort();
  return actual.length === expected.length
    && actual.every((key, index) => key === expected[index]);
}

function freezeRecord(record) {
  return Object.freeze({ ...record });
}

function unavailableSessionDelta(reason) {
  return Object.freeze({ available: false, reason });
}

function objectiveStateMap(course, summary) {
  if (!Array.isArray(summary?.objectives)) {
    throw new TypeError('Learning Loop V2 session provenance requires objective progress');
  }
  const authoredIds = (course.objectives ?? []).map(objective => objective.objectiveId);
  const byId = new Map();
  for (const state of summary.objectives) {
    if (
      !state
      || typeof state.objectiveId !== 'string'
      || !authoredIds.includes(state.objectiveId)
      || byId.has(state.objectiveId)
      || !QUALIFIED_OBJECTIVE_STATES.has(state.status)
    ) {
      throw new TypeError('Learning Loop V2 session provenance contains invalid objective state');
    }
    byId.set(state.objectiveId, state.status);
  }
  if (byId.size !== authoredIds.length) {
    throw new TypeError('Learning Loop V2 session provenance requires every authored objective');
  }
  return freezeRecord(Object.fromEntries(
    authoredIds.map(objectiveId => [objectiveId, byId.get(objectiveId)]),
  ));
}

function currentAttemptMap(course, records) {
  const byId = new Map(records.map(record => [record.activityRevisionId, record]));
  const attempts = {};
  for (const activity of course.activities ?? []) {
    const count = byId.get(activity.activityRevisionId)?.attempts ?? 0;
    if (!Number.isInteger(count) || count < 0) {
      throw new TypeError(
        `Learning Loop V2 session provenance has invalid attempts for ${activity.activityRevisionId}`,
      );
    }
    attempts[activity.activityRevisionId] = count;
  }
  return freezeRecord(attempts);
}

function captureSessionProvenance(course, records, summary) {
  return Object.freeze({
    available: true,
    beforeObjectiveStates: objectiveStateMap(course, summary),
    baselineActivityAttempts: currentAttemptMap(course, records),
  });
}

function parseSessionProvenance(meta, course) {
  if (meta.schemaVersion === 1) {
    return Object.freeze({
      sessionMetaSchemaVersion: 1,
      sessionProvenance: null,
      sessionProvenanceReason: LEGACY_SESSION_PROVENANCE_UNAVAILABLE,
    });
  }
  const provenance = meta.sessionProvenance;
  const objectiveIds = (course.objectives ?? []).map(objective => objective.objectiveId);
  const activityIds = (course.activities ?? []).map(activity => activity.activityRevisionId);
  const valid = isRecord(provenance)
    && provenance.available === true
    && exactRecordKeys(provenance.beforeObjectiveStates, objectiveIds)
    && exactRecordKeys(provenance.baselineActivityAttempts, activityIds)
    && objectiveIds.every(objectiveId => (
      QUALIFIED_OBJECTIVE_STATES.has(provenance.beforeObjectiveStates[objectiveId])
    ))
    && activityIds.every(activityRevisionId => (
      Number.isInteger(provenance.baselineActivityAttempts[activityRevisionId])
      && provenance.baselineActivityAttempts[activityRevisionId] >= 0
    ));
  if (!valid) {
    return Object.freeze({
      sessionMetaSchemaVersion: 2,
      sessionProvenance: null,
      sessionProvenanceReason: INVALID_SESSION_PROVENANCE,
    });
  }
  return Object.freeze({
    sessionMetaSchemaVersion: 2,
    sessionProvenance: Object.freeze({
      available: true,
      beforeObjectiveStates: freezeRecord(provenance.beforeObjectiveStates),
      baselineActivityAttempts: freezeRecord(provenance.baselineActivityAttempts),
    }),
    sessionProvenanceReason: null,
  });
}

function deriveSessionDelta(active, course, records, summary) {
  if (active.sessionProvenanceReason) {
    return unavailableSessionDelta(active.sessionProvenanceReason);
  }
  if (active.sessionMetaSchemaVersion !== 2 || !active.sessionProvenance) {
    return unavailableSessionDelta(INVALID_SESSION_PROVENANCE);
  }
  const currentAttempts = currentAttemptMap(course, records);
  const baselineAttempts = active.sessionProvenance.baselineActivityAttempts;
  const workedActivityIds = new Set();
  for (const activity of course.activities ?? []) {
    const baseline = baselineAttempts[activity.activityRevisionId];
    const current = currentAttempts[activity.activityRevisionId];
    if (current < baseline) {
      return unavailableSessionDelta(SESSION_PROVENANCE_ATTEMPTS_REGRESSED);
    }
    if (current > baseline) workedActivityIds.add(activity.activityRevisionId);
  }
  const workedObjectiveSet = new Set();
  for (const activity of course.activities ?? []) {
    if (!workedActivityIds.has(activity.activityRevisionId)) continue;
    for (const objectiveId of activity.objectiveIds ?? []) workedObjectiveSet.add(objectiveId);
  }
  const afterObjectiveStates = objectiveStateMap(course, summary);
  const objectiveIds = (course.objectives ?? []).map(objective => objective.objectiveId);
  const workedObjectiveIds = objectiveIds.filter(objectiveId => workedObjectiveSet.has(objectiveId));
  const changedObjectiveIds = workedObjectiveIds.filter(objectiveId => (
    afterObjectiveStates[objectiveId]
    !== active.sessionProvenance.beforeObjectiveStates[objectiveId]
  ));
  return Object.freeze({
    available: true,
    beforeObjectiveStates: active.sessionProvenance.beforeObjectiveStates,
    afterObjectiveStates,
    workedObjectiveIds: Object.freeze(workedObjectiveIds),
    changedObjectiveIds: Object.freeze(changedObjectiveIds),
  });
}

export function createSessionService(storage, progressService) {
  let active = null;
  const learningLoopV2Enabled = progressService.learningLoopV2Enabled === true;

  async function loadCourse(courseInstallId) {
    const courseRecord = await storage.getCourse(courseInstallId);
    if (!courseRecord) throw new Error(`Unknown courseInstallId ${courseInstallId}`);
    return courseRecord;
  }

  function legacyActiveMeta() {
    return {
      courseInstallId: active.courseRecord.courseInstallId,
      mode: active.mode,
      ...(active.mode === 'review' ? { reviewIndex: active.reviewIndex } : {}),
    };
  }

  function learningLoopMeta(current) {
    const navigation = {
      courseInstallId: active.courseRecord.courseInstallId,
      mode: active.mode,
      currentIndex: current?.currentIndex ?? active.currentIndex ?? -1,
      reviewIndex: active.mode === 'review' ? active.reviewIndex : 0,
      currentActivityRevisionId: current?.currentActivity?.activityRevisionId ?? null,
      reviewQueueActivityRevisionIds: current?.review?.activityRevisionIds ?? [],
    };
    if (active.sessionMetaSchemaVersion === 1) {
      return { schemaVersion: 1, ...navigation };
    }
    if (active.sessionMetaSchemaVersion === 2 && active.sessionProvenance) {
      return {
        schemaVersion: 2,
        ...navigation,
        sessionProvenance: structuredClone(active.sessionProvenance),
      };
    }
    return null;
  }

  async function persistActive(current = null) {
    if (!active) return;
    if (learningLoopV2Enabled) {
      const meta = learningLoopMeta(current);
      if (meta) await storage.setMeta(LEARNING_LOOP_V2_SESSION_META_KEY, meta);
    }
    await storage.setMeta('activeCourse', legacyActiveMeta());
  }

  async function clearPersistedActive() {
    if (learningLoopV2Enabled) await storage.deleteMeta(LEARNING_LOOP_V2_SESSION_META_KEY);
    await storage.deleteMeta('activeCourse');
  }

  async function snapshot() {
    if (!active) return null;
    const records = await progressService.getProgress(active.courseRecord.courseInstallId);
    const summary = await progressService.getCourseProgress(
      active.courseRecord.courseInstallId,
      active.courseRecord.course,
      records,
    );
    if (
      learningLoopV2Enabled
      && active.sessionMetaSchemaVersion === 2
      && active.sessionProvenance == null
      && active.sessionProvenanceReason == null
    ) {
      active.sessionProvenance = captureSessionProvenance(
        active.courseRecord.course,
        records,
        summary,
      );
    }
    const sessionDelta = learningLoopV2Enabled
      ? deriveSessionDelta(active, active.courseRecord.course, records, summary)
      : null;
    const common = {
      courseInstallId: active.courseRecord.courseInstallId,
      title: active.courseRecord.displayLabel,
      canonicalTitle: active.courseRecord.title,
      ...(learningLoopV2Enabled
        ? {
          courseObjectives: structuredClone(active.courseRecord.course.objectives ?? []),
          sessionDelta,
        }
        : {}),
      progress: { ...summary, courseInstallId: active.courseRecord.courseInstallId },
    };

    if (active.mode === 'review') {
      const queue = progressService.reviewQueue(active.courseRecord.course, records);
      if (queue.length === 0) {
        active.reviewIndex = 0;
        return {
          ...common,
          mode: 'review',
          currentIndex: -1,
          currentActivity: null,
          review: learningLoopV2Enabled ? { remaining: 0, activityRevisionIds: [] } : { remaining: 0 },
        };
      }
      const index = active.reviewIndex % queue.length;
      active.reviewIndex = index;
      return {
        ...common,
        mode: 'review',
        currentIndex: index,
        currentActivity: structuredClone(queue[index]),
        review: learningLoopV2Enabled
          ? { remaining: queue.length, activityRevisionIds: queue.map(activity => activity.activityRevisionId) }
          : { remaining: queue.length },
      };
    }

    const index = nextIncompleteIndex(active.courseRecord.course, records, active.currentIndex);
    active.currentIndex = index;
    return {
      ...common,
      mode: 'learn',
      currentIndex: index,
      currentActivity: index >= 0 ? structuredClone(active.courseRecord.course.activities[index]) : null,
    };
  }

  return Object.freeze({
    async startCourse(courseInstallId) {
      const courseRecord = await loadCourse(courseInstallId);
      active = {
        courseRecord,
        mode: 'learn',
        currentIndex: 0,
        sessionMetaSchemaVersion: 2,
        sessionProvenance: null,
        sessionProvenanceReason: null,
      };
      if (!learningLoopV2Enabled) {
        await persistActive();
        return snapshot();
      }
      const current = await snapshot();
      await persistActive(current);
      return current;
    },

    async startReviewQueue(courseInstallId) {
      const courseRecord = await loadCourse(courseInstallId);
      active = {
        courseRecord,
        mode: 'review',
        reviewIndex: 0,
        sessionMetaSchemaVersion: 2,
        sessionProvenance: null,
        sessionProvenanceReason: null,
      };
      const current = await snapshot();
      if (current.review.remaining > 0) await persistActive(current); else await clearPersistedActive();
      return current;
    },

    async resumeActiveCourse() {
      let meta;
      try { meta = await storage.getMeta('activeCourse'); }
      catch { active = null; return null; }
      if (meta == null) { active = null; return null; }
      const validCourseInstallId = typeof meta.courseInstallId === 'string' && meta.courseInstallId.length > 0;
      const validMode = meta.mode == null || meta.mode === 'learn' || meta.mode === 'review';
      if (!validCourseInstallId || !validMode) {
        active = null;
        await storage.deleteMeta('activeCourse');
        if (learningLoopV2Enabled) await storage.deleteMeta(LEARNING_LOOP_V2_SESSION_META_KEY);
        return null;
      }
      let courseRecord;
      try { courseRecord = await storage.getCourse(meta.courseInstallId); }
      catch { active = null; return null; }
      if (!courseRecord) {
        active = null;
        await storage.deleteMeta('activeCourse');
        if (learningLoopV2Enabled) await storage.deleteMeta(LEARNING_LOOP_V2_SESSION_META_KEY);
        return null;
      }
      let waveMeta = null;
      if (learningLoopV2Enabled) {
        try {
          const candidate = await storage.getMeta(LEARNING_LOOP_V2_SESSION_META_KEY);
          if (validLearningLoopNavigationMeta(candidate, meta)) waveMeta = candidate;
        } catch { active = null; return null; }
      }
      const provenanceState = waveMeta
        ? parseSessionProvenance(waveMeta, courseRecord.course)
        : Object.freeze({
          sessionMetaSchemaVersion: 1,
          sessionProvenance: null,
          sessionProvenanceReason: SESSION_PROVENANCE_UNAVAILABLE,
        });
      active = meta.mode === 'review'
        ? {
          courseRecord,
          mode: 'review',
          reviewIndex: Number.isInteger(meta.reviewIndex) && meta.reviewIndex >= 0
            ? meta.reviewIndex
            : (Number.isInteger(waveMeta?.reviewIndex) && waveMeta.reviewIndex >= 0 ? waveMeta.reviewIndex : 0),
          ...provenanceState,
        }
        : {
          courseRecord,
          mode: 'learn',
          currentIndex: Number.isInteger(waveMeta?.currentIndex) && waveMeta.currentIndex >= 0 ? waveMeta.currentIndex : 0,
          ...provenanceState,
        };
      let current;
      try { current = await snapshot(); }
      catch { active = null; return null; }
      if (current?.mode === 'review' && current.review.remaining === 0) await clearPersistedActive();
      else if (learningLoopV2Enabled) await persistActive(current);
      return current;
    },

    async getSession() { return snapshot(); },

    async answer(activityRevisionId, answer) {
      const current = await snapshot();
      if (!current?.currentActivity) throw new AnswerValidationError('No active activity', 'no_active_activity');
      if (current.currentActivity.activityRevisionId !== activityRevisionId) {
        throw new AnswerValidationError('Answers must follow the active session queue', 'out_of_sequence');
      }
      const result = evaluation(current.currentActivity, answer);
      const record = result.scored
        ? await progressService.recordAttempt({
          courseInstallId: current.courseInstallId,
          course: active.courseRecord.course,
          activity: current.currentActivity,
          answer: result.normalized,
          correct: result.correct,
        })
        : await progressService.recordCompletion({
          courseInstallId: current.courseInstallId,
          course: active.courseRecord.course,
          activity: current.currentActivity,
          answer: result.normalized,
        });

      const previousReviewIndex = current.mode === 'review' ? active.reviewIndex : null;
      const previousCurrentIndex = active.currentIndex;
      try {
        if (current.mode === 'review' && result.scored && !result.correct) active.reviewIndex += 1;
        const after = await snapshot();
        if (current.mode === 'review') {
          if (after.review.remaining === 0) await clearPersistedActive(); else await persistActive(after);
        } else if (after.progress.isComplete) await clearPersistedActive();
        else if (learningLoopV2Enabled) await persistActive(after);

        return {
          courseInstallId: current.courseInstallId,
          mode: current.mode,
          activityRevisionId,
          scored: result.scored,
          ...(result.scored ? { correct: result.correct } : {}),
          completed: record.completed,
          ...(record.selectedChoiceId ? { selectedChoiceId: record.selectedChoiceId } : {}),
          ...(record.answers ? { answers: structuredClone(record.answers) } : {}),
          answer: result.normalized,
          ...(Object.hasOwn(current.currentActivity, 'explanation') ? { explanation: current.currentActivity.explanation } : {}),
          ...(learningLoopV2Enabled
            ? {
              courseObjectives: current.courseObjectives,
              sessionDelta: after.sessionDelta,
            }
            : {}),
          progress: after.progress,
          ...(current.mode === 'review' ? { review: after.review } : {}),
          nextActivity: after.currentActivity,
        };
      } catch (error) {
        if (active) {
          if (current.mode === 'review') active.reviewIndex = previousReviewIndex;
          else active.currentIndex = previousCurrentIndex;
        }
        throw error;
      }
    },

    clearActiveSession() { active = null; },
  });
}
