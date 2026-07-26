import { CONTRACT_VERSION } from './core/contract.js';
import { createImportService } from './core/import.js';
import { createLibraryService } from './core/library.js';
import { createProgressService } from './core/progress.js';
import { createSessionService } from './core/session.js';
import { createIndexedDbStorage } from './adapters/indexeddb.js';
import { assertStoragePort } from './ports/storage.js';
import { renderApp } from './ui/render.js';

export function createLearnitRuntime(storageAdapter = createIndexedDbStorage()) {
  const storage = assertStoragePort(storageAdapter);
  const progress = createProgressService(storage);
  const library = createLibraryService(storage, progress);
  const imports = createImportService(storage);
  const sessions = createSessionService(storage, progress);

  const runtime = {
    contractVersion: CONTRACT_VERSION,
    validatePackage: (payload) => imports.validatePackage(payload),
    previewImport: (payload) => imports.previewImport(payload),
    importPackage: (payload) => imports.importPackage(payload),
    listCourses: () => library.listCourses(),
    setCourseDisplayLabel: (courseInstallId, label) => library.setDisplayLabel(courseInstallId, label),
    startCourse: (courseInstallId) => sessions.startCourse(courseInstallId),
    startReviewQueue: (courseInstallId) => sessions.startReviewQueue(courseInstallId),
    answer: (activityRevisionId, answer) => sessions.answer(activityRevisionId, answer),
    async getProgress(courseInstallId) {
      const courseRecord = await library.getCourse(courseInstallId);
      if (!courseRecord) throw new Error(`Unknown courseInstallId ${courseInstallId}`);
      const records = await progress.getProgress(courseInstallId);
      return {
        ...progress.summarize(courseRecord.course, records),
        courseInstallId,
      };
    },
    async getReviewQueue(courseInstallId) {
      const courseRecord = await library.getCourse(courseInstallId);
      if (!courseRecord) throw new Error(`Unknown courseInstallId ${courseInstallId}`);
      const records = await progress.getProgress(courseInstallId);
      const activities = progress.reviewQueue(courseRecord.course, records);
      return {
        courseInstallId,
        total: activities.length,
        activityRevisionIds: activities.map((activity) => activity.activityRevisionId),
      };
    },
    async resetNextData() {
      sessions.clearActiveSession();
      await storage.resetNextData();
      return storage.storageReport();
    },
    storageReport: () => storage.storageReport(),

    // Visible UI helpers use the same domain services as the bounded diagnostic surface.
    resumeActiveCourse: () => sessions.resumeActiveCourse(),
    getSession: () => sessions.getSession(),
  };

  return Object.freeze(runtime);
}

function waitForInitialRender(root) {
  if (root.getAttribute('aria-busy') === 'false') return Promise.resolve();
  return new Promise((resolve) => {
    const observer = new MutationObserver(() => {
      if (root.getAttribute('aria-busy') !== 'false') return;
      observer.disconnect();
      resolve();
    });
    observer.observe(root, { attributes: true, attributeFilter: ['aria-busy'] });
  });
}

async function boot() {
  const root = document.getElementById('app');
  if (!root) throw new Error('Missing #app mount point');
  const runtime = createLearnitRuntime();
  renderApp(root, runtime);
  await waitForInitialRender(root);
  globalThis.__LEARNIT_NEXT_TEST__ = Object.freeze({
    contractVersion: runtime.contractVersion,
    validatePackage: runtime.validatePackage,
    previewImport: runtime.previewImport,
    importPackage: runtime.importPackage,
    listCourses: runtime.listCourses,
    setCourseDisplayLabel: runtime.setCourseDisplayLabel,
    startCourse: runtime.startCourse,
    startReviewQueue: runtime.startReviewQueue,
    answer: runtime.answer,
    getProgress: runtime.getProgress,
    getReviewQueue: runtime.getReviewQueue,
    resetNextData: runtime.resetNextData,
    storageReport: runtime.storageReport,
  });
}

if (typeof document !== 'undefined' && document.querySelector('[data-learnit-next-app]')) {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
}
