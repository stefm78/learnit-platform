export function summarizeProgress(course, records) {
  const byActivity = new Map(records.map((record) => [record.activityRevisionId, record]));
  const completed = course.activities.filter((activity) => byActivity.get(activity.activityRevisionId)?.completed).length;
  return {
    courseInstallId: records[0]?.courseInstallId ?? null,
    completed,
    total: course.activities.length,
    isComplete: completed === course.activities.length,
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

export function createProgressService(storage) {
  return {
    async getProgress(courseInstallId) {
      return storage.listProgress(courseInstallId);
    },

    async recordAttempt(input) {
      const previous = await storage.getProgress(input.courseInstallId, input.activity.activityRevisionId);
      const record = buildProgressRecord({ ...input, previous });
      await storage.putProgress(record);
      return record;
    },

    summarize: summarizeProgress,
  };
}
