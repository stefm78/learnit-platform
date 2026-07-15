export function createLibraryService(storage, progressService) {
  return {
    async listCourses() {
      const courses = await storage.listCourses();
      const projected = [];
      for (const record of courses) {
        const progressRecords = await progressService.getProgress(record.courseInstallId);
        const progress = progressService.summarize(record.course, progressRecords);
        projected.push({
          courseInstallId: record.courseInstallId,
          packageInstallId: record.packageInstallId,
          courseLineageId: record.courseLineageId,
          courseRevisionId: record.courseRevisionId,
          title: record.displayLabel,
          canonicalTitle: record.title,
          subtitle: record.subtitle,
          estimatedMinutes: record.estimatedMinutes,
          activityCount: record.activityCount,
          progress: {
            completed: progress.completed,
            total: progress.total,
            isComplete: progress.isComplete,
          },
        });
      }
      return projected;
    },

    async getCourse(courseInstallId) {
      return storage.getCourse(courseInstallId);
    },

    async setDisplayLabel(courseInstallId, label) {
      const normalized = String(label ?? '').trim();
      if (!normalized || normalized.length > 180) {
        throw new TypeError('Display label must contain between 1 and 180 characters');
      }
      await storage.setCourseDisplayLabel(courseInstallId, normalized);
      return this.listCourses();
    },
  };
}
