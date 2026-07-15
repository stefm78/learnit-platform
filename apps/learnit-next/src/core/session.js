export class AnswerValidationError extends Error {
  constructor(message, code = 'invalid_answer') {
    super(message);
    this.name = 'AnswerValidationError';
    this.code = code;
  }
}

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

function nextIncompleteIndex(course, records) {
  const complete = new Set(records.filter((record) => record.completed).map((record) => record.activityRevisionId));
  return course.activities.findIndex((activity) => !complete.has(activity.activityRevisionId));
}

export function createSessionService(storage, progressService) {
  let active = null;

  async function snapshot() {
    if (!active) return null;
    const records = await progressService.getProgress(active.courseRecord.courseInstallId);
    const summary = progressService.summarize(active.courseRecord.course, records);
    const index = nextIncompleteIndex(active.courseRecord.course, records);
    active.currentIndex = index;
    return {
      courseInstallId: active.courseRecord.courseInstallId,
      title: active.courseRecord.displayLabel,
      canonicalTitle: active.courseRecord.title,
      currentIndex: index,
      currentActivity: index >= 0 ? structuredClone(active.courseRecord.course.activities[index]) : null,
      progress: { ...summary, courseInstallId: active.courseRecord.courseInstallId },
    };
  }

  return {
    async startCourse(courseInstallId) {
      const courseRecord = await storage.getCourse(courseInstallId);
      if (!courseRecord) throw new Error(`Unknown courseInstallId ${courseInstallId}`);
      active = { courseRecord, currentIndex: 0 };
      await storage.setMeta('activeCourse', { courseInstallId });
      return snapshot();
    },

    async resumeActiveCourse() {
      const meta = await storage.getMeta('activeCourse');
      if (!meta?.courseInstallId) return null;
      try {
        return await this.startCourse(meta.courseInstallId);
      } catch {
        await storage.deleteMeta('activeCourse');
        return null;
      }
    },

    async getSession() {
      return snapshot();
    },

    async answer(activityRevisionId, answer) {
      const current = await snapshot();
      if (!current?.currentActivity) throw new AnswerValidationError('No active incomplete activity', 'no_active_activity');
      if (current.currentActivity.activityRevisionId !== activityRevisionId) {
        throw new AnswerValidationError('Answers must follow the authored session queue', 'out_of_sequence');
      }

      const evaluation = evaluateAnswer(current.currentActivity, answer);
      await progressService.recordAttempt({
        courseInstallId: current.courseInstallId,
        activity: current.currentActivity,
        answer: evaluation.normalized,
        correct: evaluation.correct,
      });
      const after = await snapshot();
      if (after.progress.isComplete) await storage.deleteMeta('activeCourse');
      return {
        activityRevisionId,
        correct: evaluation.correct,
        answer: evaluation.normalized,
        explanation: current.currentActivity.explanation,
        progress: after.progress,
        nextActivity: after.currentActivity,
      };
    },

    clearActiveSession() {
      active = null;
    },
  };
}

export { evaluateAnswer };
