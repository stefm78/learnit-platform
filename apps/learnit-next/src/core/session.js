export class AnswerValidationError extends Error {
  constructor(message, code = 'invalid_answer') {
    super(message);
    this.name = 'AnswerValidationError';
    this.code = code;
  }
}

export const LEARNING_LOOP_V2_SESSION_META_KEY = 'learningLoopV2Session';

function normalizeQcmAnswer(activity, answer) {
  const choiceId = typeof answer === 'string' ? answer : answer?.choiceId;
  if (typeof choiceId !== 'string') {
    throw new AnswerValidationError('A QCM answer must provide a choiceId');
  }
  if (!activity.choices.some((choice) => choice.choiceId === choiceId)) {
    throw new AnswerValidationError('The selected choiceId is not declared by this activity', 'unknown_choice');
  }
  return { choiceId };
}

function normalizeFillAnswer(activity, answer) {
  const entries = Array.isArray(answer)
    ? answer.map((assignment) => [assignment?.slotId, assignment?.tokenId])
    : Object.entries(answer ?? {});
  const assignments = new Map();
  for (const [slotId, tokenId] of entries) {
    if (typeof slotId !== 'string' || typeof tokenId !== 'string') {
      throw new AnswerValidationError('Each fill assignment must contain string slotId and tokenId values');
    }
    if (assignments.has(slotId)) {
      throw new AnswerValidationError(`slotId ${slotId} is assigned more than once`, 'duplicate_slot_assignment');
    }
    assignments.set(slotId, tokenId);
  }

  const slotIds = activity.segments.filter((segment) => Object.hasOwn(segment, 'slotId')).map((segment) => segment.slotId);
  const tokenById = new Map(activity.tokens.map((token) => [token.tokenId, token]));
  if (assignments.size !== slotIds.length || slotIds.some((slotId) => !assignments.has(slotId))) {
    throw new AnswerValidationError('Every declared fill slot must have exactly one token', 'incomplete_fill');
  }

  const usage = new Map();
  for (const [slotId, tokenId] of assignments) {
    if (!slotIds.includes(slotId)) {
      throw new AnswerValidationError(`Unknown slotId ${slotId}`, 'unknown_slot');
    }
    const token = tokenById.get(tokenId);
    if (!token) throw new AnswerValidationError(`Unknown tokenId ${tokenId}`, 'unknown_token');
    const count = (usage.get(tokenId) ?? 0) + 1;
    if (count > token.maxUses) {
      throw new AnswerValidationError(`tokenId ${tokenId} exceeds maxUses ${token.maxUses}`, 'max_uses');
    }
    usage.set(tokenId, count);
  }

  return Object.fromEntries(slotIds.map((slotId) => [slotId, assignments.get(slotId)]));
}

function evaluateAnswer(activity, answer) {
  if (activity.type === 'qcm') {
    const normalized = normalizeQcmAnswer(activity, answer);
    return { normalized, correct: normalized.choiceId === activity.correctChoiceId };
  }
  if (activity.type === 'fill') {
    const normalized = normalizeFillAnswer(activity, answer);
    const expected = new Map(activity.answers.map((entry) => [entry.slotId, entry.tokenId]));
    const correct = Object.entries(normalized).every(([slotId, tokenId]) => expected.get(slotId) === tokenId);
    return { normalized, correct };
  }
  throw new AnswerValidationError(`Unsupported activity type ${activity.type}`, 'unsupported_activity');
}

function nextIncompleteIndex(course, records, preferredIndex = null) {
  const complete = new Set(records.filter((record) => record.completed).map((record) => record.activityRevisionId));
  if (
    Number.isInteger(preferredIndex)
    && preferredIndex >= 0
    && preferredIndex < course.activities.length
    && !complete.has(course.activities[preferredIndex].activityRevisionId)
  ) {
    return preferredIndex;
  }
  return course.activities.findIndex((activity) => !complete.has(activity.activityRevisionId));
}

function validLearningLoopMeta(meta, activeCourseMeta) {
  return meta
    && meta.schemaVersion === 1
    && meta.courseInstallId === activeCourseMeta.courseInstallId
    && meta.mode === (activeCourseMeta.mode ?? 'learn');
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
    return {
      schemaVersion: 1,
      courseInstallId: active.courseRecord.courseInstallId,
      mode: active.mode,
      currentIndex: current?.currentIndex ?? active.currentIndex ?? -1,
      reviewIndex: active.mode === 'review' ? active.reviewIndex : 0,
      currentActivityRevisionId: current?.currentActivity?.activityRevisionId ?? null,
      reviewQueueActivityRevisionIds: current?.review?.activityRevisionIds ?? [],
    };
  }

  async function persistActive(current = null) {
    if (!active) return;
    if (learningLoopV2Enabled) {
      // Write the additive record first. The protected P1 record remains the resume authority.
      await storage.setMeta(LEARNING_LOOP_V2_SESSION_META_KEY, learningLoopMeta(current));
    }
    await storage.setMeta('activeCourse', legacyActiveMeta());
  }

  async function clearPersistedActive() {
    if (learningLoopV2Enabled) {
      // Preserve the protected P1 resume record if cleanup of the additive record fails.
      await storage.deleteMeta(LEARNING_LOOP_V2_SESSION_META_KEY);
    }
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
    const common = {
      courseInstallId: active.courseRecord.courseInstallId,
      title: active.courseRecord.displayLabel,
      canonicalTitle: active.courseRecord.title,
      ...(learningLoopV2Enabled ? { courseObjectives: structuredClone(active.courseRecord.course.objectives ?? []) } : {}),
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
          ? {
            remaining: queue.length,
            activityRevisionIds: queue.map((activity) => activity.activityRevisionId),
          }
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

  return {
    async startCourse(courseInstallId) {
      const courseRecord = await loadCourse(courseInstallId);
      active = { courseRecord, mode: 'learn', currentIndex: 0 };
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
      active = { courseRecord, mode: 'review', reviewIndex: 0 };
      const current = await snapshot();
      if (current.review.remaining > 0) await persistActive(current);
      else await clearPersistedActive();
      return current;
    },

    async resumeActiveCourse() {
      let meta;
      try {
        meta = await storage.getMeta('activeCourse');
      } catch {
        active = null;
        return null;
      }
      if (meta == null) {
        active = null;
        return null;
      }

      const validCourseInstallId = typeof meta.courseInstallId === 'string' && meta.courseInstallId.length > 0;
      const validMode = meta.mode == null || meta.mode === 'learn' || meta.mode === 'review';
      if (!validCourseInstallId || !validMode) {
        active = null;
        await storage.deleteMeta('activeCourse');
        if (learningLoopV2Enabled) await storage.deleteMeta(LEARNING_LOOP_V2_SESSION_META_KEY);
        return null;
      }

      let courseRecord;
      try {
        courseRecord = await storage.getCourse(meta.courseInstallId);
      } catch {
        active = null;
        return null;
      }
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
          if (validLearningLoopMeta(candidate, meta)) waveMeta = candidate;
        } catch {
          active = null;
          return null;
        }
      }

      active = meta.mode === 'review'
        ? {
          courseRecord,
          mode: 'review',
          reviewIndex: Number.isInteger(meta.reviewIndex) && meta.reviewIndex >= 0
            ? meta.reviewIndex
            : (Number.isInteger(waveMeta?.reviewIndex) && waveMeta.reviewIndex >= 0 ? waveMeta.reviewIndex : 0),
        }
        : {
          courseRecord,
          mode: 'learn',
          currentIndex: Number.isInteger(waveMeta?.currentIndex) && waveMeta.currentIndex >= 0
            ? waveMeta.currentIndex
            : 0,
        };

      let current;
      try {
        current = await snapshot();
      } catch {
        active = null;
        return null;
      }
      if (current?.mode === 'review' && current.review.remaining === 0) {
        await clearPersistedActive();
      } else if (learningLoopV2Enabled) {
        await persistActive(current);
      }
      return current;
    },

    async getSession() {
      return snapshot();
    },

    async answer(activityRevisionId, answer) {
      const current = await snapshot();
      if (!current?.currentActivity) throw new AnswerValidationError('No active activity', 'no_active_activity');
      if (current.currentActivity.activityRevisionId !== activityRevisionId) {
        throw new AnswerValidationError('Answers must follow the active session queue', 'out_of_sequence');
      }

      const evaluation = evaluateAnswer(current.currentActivity, answer);
      const record = await progressService.recordAttempt({
        courseInstallId: current.courseInstallId,
        course: active.courseRecord.course,
        activity: current.currentActivity,
        answer: evaluation.normalized,
        correct: evaluation.correct,
      });

      const previousReviewIndex = current.mode === 'review' ? active.reviewIndex : null;
      const previousCurrentIndex = active.currentIndex;
      try {
        if (current.mode === 'review' && !evaluation.correct) active.reviewIndex += 1;
        const after = await snapshot();
        if (current.mode === 'review') {
          if (after.review.remaining === 0) await clearPersistedActive();
          else await persistActive(after);
        } else if (after.progress.isComplete) {
          await clearPersistedActive();
        } else if (learningLoopV2Enabled) {
          await persistActive(after);
        }

        return {
          courseInstallId: current.courseInstallId,
          mode: current.mode,
          activityRevisionId,
          correct: evaluation.correct,
          completed: record.completed,
          ...(record.selectedChoiceId ? { selectedChoiceId: record.selectedChoiceId } : {}),
          ...(record.answers ? { answers: structuredClone(record.answers) } : {}),
          answer: evaluation.normalized,
          explanation: current.currentActivity.explanation,
          ...(learningLoopV2Enabled ? { courseObjectives: current.courseObjectives } : {}),
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

    clearActiveSession() {
      active = null;
    },
  };
}

export { evaluateAnswer };
