export function createLibraryService(storage) {
  async function listCourses() {
    const courses = await storage.listCourses();
    return courses.map(record => ({
      courseInstallId: record.courseInstallId,
      packageInstallId: record.packageInstallId,
      courseLineageId: record.courseLineageId,
      courseRevisionId: record.courseRevisionId,
      title: record.displayLabel ?? record.title,
      canonicalTitle: record.title,
      subtitle: record.subtitle,
      estimatedMinutes: record.estimatedMinutes,
      activityCount: record.activityCount,
    }));
  }

  return Object.freeze({
    listCourses,

    async searchCourses(query) {
      const normalized = String(query ?? '').trim().toLocaleLowerCase('fr');
      const courses = await listCourses();
      if (!normalized) return courses;
      return courses.filter(course => (
        [course.title, course.canonicalTitle, course.subtitle]
          .filter(Boolean)
          .join(' ')
          .toLocaleLowerCase('fr')
          .includes(normalized)
      ));
    },

    async getCourse(courseInstallId) {
      return storage.getCourse(courseInstallId);
    },

    async setDisplayLabel(courseInstallId, label) {
      const normalized = String(label ?? '').trim();
      const codePointLength = Array.from(normalized).length;
      if (!normalized || codePointLength > 180) {
        throw new TypeError('Display label must contain between 1 and 180 characters');
      }
      await storage.setCourseDisplayLabel(courseInstallId, normalized);
      return normalized;
    },
  });
}
