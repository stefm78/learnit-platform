import { CONTRACT_VERSION } from './core/contract.js';
import { installAtlasRuntime } from './integration/atlas/bootstrap.js';
import { attachAtlasPreviewSurface } from './integration/atlas/surface.js';
import { createAtlasCompatibleImportService } from './integration/atlas/import_adapter.js';
import { createImportService } from './core/import.js';
import { createLibraryService } from './core/library.js';
import {
  createLearningLoopV2DomainAdapters,
  createProgressService,
} from './core/progress.js';
import { createSessionService } from './core/session.js';
import * as objectiveProgressDomain from './core/objective_progress.js';
import * as learningRecommendationDomain from './core/learning_recommendation.js';
import { createIndexedDbStorage } from './adapters/indexeddb.js';
import { assertStoragePort } from './ports/storage.js';
import * as objectiveUiModule from './ui/objective_progress.js';
import { renderApp } from './ui/render.js';

export const LEARNING_LOOP_V2_COMPOSITION = Object.freeze({
  registry: '__LEARNIT_NEXT_WAVE_A__',
  modules: Object.freeze({
    objectiveProgress: './core/objective_progress.js',
    learningRecommendation: './core/learning_recommendation.js',
    objectiveUi: './ui/objective_progress.js',
  }),
  requiredExports: Object.freeze({
    objectiveProgress: Object.freeze(['reduceObjectiveEvents', 'normalizeObjectiveProgress']),
    learningRecommendation: Object.freeze(['recommendNextObjective']),
    objectiveUi: Object.freeze(['renderObjectiveProgressPanel']),
  }),
});

const RECOMMENDATION_PRESENTATION = Object.freeze({
  correct: Object.freeze({
    title: 'Révision nécessaire',
    description: 'Reprenez une activité incorrecte avant de poursuivre vers la validation.',
  }),
  validate: Object.freeze({
    title: 'Validation disponible',
    description: 'L’entraînement est à jour. Une activité distincte peut maintenant valider cet objectif.',
  }),
  'continue-training': Object.freeze({
    title: 'Poursuivre l’entraînement',
    description: 'Continuez les activités d’entraînement associées à cet objectif.',
  }),
  'start-training': Object.freeze({
    title: 'Commencer l’entraînement',
    description: 'Commencez par une activité d’entraînement associée à cet objectif.',
  }),
  'revisit-later': Object.freeze({
    title: 'Revenir plus tard',
    description: 'La validation est récente et devra être revue ultérieurement.',
  }),
});

function presentRecommendation(recommendation) {
  if (recommendation == null) return null;
  if (typeof recommendation !== 'object' || Array.isArray(recommendation)) {
    throw new TypeError('Learning Loop V2 recommendation must be a data object or null');
  }
  const presentation = RECOMMENDATION_PRESENTATION[recommendation.action];
  if (!presentation) {
    throw new TypeError(`Unsupported Learning Loop V2 recommendation action: ${String(recommendation.action)}`);
  }
  return {
    ...presentation,
    actionKey: recommendation.action,
    objectiveId: recommendation.objectiveId,
    status: recommendation.status,
  };
}

function createObjectiveUiAdapter(moduleValue) {
  if (typeof moduleValue?.renderObjectiveProgressPanel !== 'function') {
    throw new TypeError('Learning Loop V2 objectiveUi.renderObjectiveProgressPanel() is required');
  }
  return Object.freeze({
    renderObjectiveProgress(input = {}) {
      const labelsById = Object.fromEntries(
        (input.courseObjectives ?? []).map((objective) => [
          objective.objectiveId,
          objective.label ?? objective.objectiveId,
        ]),
      );
      return moduleValue.renderObjectiveProgressPanel(
        {
          objectives: input.objectiveProgress ?? [],
          recommendation: presentRecommendation(input.recommendation ?? null),
        },
        {
          documentRef: input.document ?? globalThis.document,
          labelsById,
          idPrefix: `learning-loop-${input.context ?? 'surface'}`,
        },
      );
    },
  });
}

const domainIntegrations = createLearningLoopV2DomainAdapters(
  objectiveProgressDomain,
  learningRecommendationDomain,
);
const defaultIntegrations = Object.freeze({
  ...domainIntegrations,
  objectiveUi: createObjectiveUiAdapter(objectiveUiModule),
});

const atlasRuntime = installAtlasRuntime();

function resolveIntegrations(value = defaultIntegrations) {
  if (value == null) return Object.freeze({});
  if (typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Learning Loop V2 integrations must be an object');
  }
  return Object.freeze({
    objectiveProgress: value.objectiveProgress ?? null,
    learningRecommendation: value.learningRecommendation ?? null,
    objectiveUi: value.objectiveUi ?? null,
  });
}

export function createLearnitRuntime(
  storageAdapter = createIndexedDbStorage(),
  integrations = defaultIntegrations,
) {
  const storage = assertStoragePort(storageAdapter);
  const resolvedIntegrations = resolveIntegrations(integrations);
  const progress = createProgressService(storage, resolvedIntegrations);
  const library = createLibraryService(storage, progress);
  const imports = createAtlasCompatibleImportService(
    storage,
    createImportService(storage),
  );
  const sessions = createSessionService(storage, progress);

  const runtime = {
    contractVersion: CONTRACT_VERSION,
    validatePackage: (payload) => imports.validatePackage(payload),
    previewImport: (payload) => imports.previewImport(payload),
    importPackage: (payload) => imports.importPackage(payload),
    async listCourses() {
      const courses = await library.listCourses();
      if (!progress.learningLoopV2Enabled) return courses;
      const enriched = [];
      for (const course of courses) {
        const courseRecord = await library.getCourse(course.courseInstallId);
        if (!courseRecord) continue;
        const courseProgress = await progress.getCourseProgress(
          course.courseInstallId,
          courseRecord.course,
        );
        enriched.push({
          ...course,
          objectives: structuredClone(courseRecord.course.objectives ?? []),
          progress: {
            ...course.progress,
            needsReview: courseProgress.needsReview,
            objectives: courseProgress.objectives ?? [],
            recommendation: courseProgress.recommendation ?? null,
          },
        });
      }
      return enriched;
    },
    setCourseDisplayLabel: (courseInstallId, label) => library.setDisplayLabel(courseInstallId, label),
    startCourse: (courseInstallId) => sessions.startCourse(courseInstallId),
    startReviewQueue: (courseInstallId) => sessions.startReviewQueue(courseInstallId),
    answer: (activityRevisionId, answer) => sessions.answer(activityRevisionId, answer),
    async getProgress(courseInstallId) {
      const courseRecord = await library.getCourse(courseInstallId);
      if (!courseRecord) throw new Error(`Unknown courseInstallId ${courseInstallId}`);
      const summary = await progress.getCourseProgress(courseInstallId, courseRecord.course);
      return {
        ...summary,
        courseInstallId,
      };
    },
    async getObjectiveProgress(courseInstallId) {
      const courseRecord = await library.getCourse(courseInstallId);
      if (!courseRecord) throw new Error(`Unknown courseInstallId ${courseInstallId}`);
      return progress.getObjectiveProgress(courseInstallId, courseRecord.course);
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

    async getAtlasCourseContext(courseInstallId) {
      const courseRecord = await library.getCourse(courseInstallId);
      if (!courseRecord) {
        throw new Error(`Unknown courseInstallId ${courseInstallId}`);
      }

      const revisionDigests = await storage.getRevisionDigestIndex();
      const packageDigest = revisionDigests.get(
        courseRecord.packageRevisionId,
      );

      if (!packageDigest) {
        throw new Error('ATLAS_PACKAGE_DIGEST_NOT_FOUND');
      }

      return Object.freeze({
        courseInstallId,
        title: courseRecord.displayLabel,
        canonicalTitle: courseRecord.title,
        packageLineageId: courseRecord.packageLineageId,
        packageRevisionId: courseRecord.packageRevisionId,
        packageDigest,
        course: structuredClone(courseRecord.course),
      });
    },

    integrationStatus: () => ({
      learningLoopV2: progress.learningLoopV2Enabled,
      objectiveUi: typeof resolvedIntegrations.objectiveUi?.renderObjectiveProgress === 'function',
      atlasM1: atlasRuntime.status(),
    }),

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
  const integrations = resolveIntegrations(
    globalThis[LEARNING_LOOP_V2_COMPOSITION.registry] ?? defaultIntegrations,
  );
  const runtime = createLearnitRuntime(createIndexedDbStorage(), integrations);
  renderApp(root, runtime, integrations.objectiveUi);
  await waitForInitialRender(root);

  await attachAtlasPreviewSurface({
    root,
    runtime,
    atlasRuntime,
  });

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
    getObjectiveProgress: runtime.getObjectiveProgress,
    getReviewQueue: runtime.getReviewQueue,
    resetNextData: runtime.resetNextData,
    storageReport: runtime.storageReport,
    getAtlasCourseContext: runtime.getAtlasCourseContext,
    integrationStatus: runtime.integrationStatus,
    resumeActiveCourse: runtime.resumeActiveCourse,
    getSession: runtime.getSession,
  });
}

if (typeof document !== 'undefined' && document.querySelector('[data-learnit-next-app]')) {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
}
