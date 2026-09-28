import { assertLearningProjectionPort } from '../ports/learning_projection.js';

export function createLearningLoopProjectionAdapter(storage, progressService) {
  return assertLearningProjectionPort(Object.freeze({
    async projectCourse(courseInstallId) {
      const courseRecord = await storage.getCourse(courseInstallId);
      if (!courseRecord) throw new Error(`Unknown courseInstallId ${courseInstallId}`);

      const records = await progressService.getProgress(courseInstallId);
      const base = progressService.summarize(courseRecord.course, records);
      const projection = {
        progress: {
          completed: base.completed,
          total: base.total,
          isComplete: base.isComplete,
          needsReview: false,
          objectives: [],
          recommendation: null,
        },
        objectives: structuredClone(courseRecord.course.objectives ?? []),
      };

      if (!progressService.learningLoopV2Enabled) return Object.freeze(projection);

      const learning = await progressService.getCourseProgress(
        courseInstallId,
        courseRecord.course,
      );
      return Object.freeze({
        objectives: structuredClone(courseRecord.course.objectives ?? []),
        progress: Object.freeze({
          completed: base.completed,
          total: base.total,
          isComplete: base.isComplete,
          needsReview: learning.needsReview,
          objectives: structuredClone(learning.objectives ?? []),
          recommendation: structuredClone(learning.recommendation ?? null),
        }),
      });
    },
  }));
}
