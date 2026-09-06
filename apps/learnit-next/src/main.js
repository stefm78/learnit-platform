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

function atlasR8StateFromSegment(segment) {
  const prefix = 'course-objective-segment--';
  const token = [...segment.classList].find(value => value.startsWith(prefix));
  return token ? token.slice(prefix.length) : 'training';
}

function atlasR8GroupForState(state) {
  if (state === 'validated-recently') return 'acquired';
  if (state === 'ready-for-validation') return 'confirm';
  return 'work';
}

function atlasR8StateLabel(state) {
  switch (state) {
    case 'not-started': return 'À découvrir';
    case 'training': return 'En apprentissage';
    case 'review-needed': return 'À renforcer';
    case 'ready-for-validation': return 'À confirmer';
    case 'validated-recently': return 'Acquis récemment';
    default: return 'En apprentissage';
  }
}

function atlasR8WhyNow(state) {
  switch (state) {
    case 'review-needed': return 'Cet objectif mérite d’être renforcé avant d’aller plus loin.';
    case 'ready-for-validation': return 'Cet objectif est prêt à être confirmé sans aide.';
    case 'validated-recently': return 'Cet acquis peut maintenant être consolidé ou réutilisé.';
    case 'not-started': return 'Cet objectif reste à découvrir.';
    default: return 'Cet objectif est encore en apprentissage.';
  }
}

function atlasR8Node(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === 'className') element.className = value;
    else if (name === 'text') element.textContent = String(value);
    else element.setAttribute(name, String(value));
  }
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child == null) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}

async function enhanceAtlasR8LearningMap(root, runtime) {
  const today = root.querySelector('[data-atlas-int-content="true"]');
  if (!today) return;
  const cards = [...today.querySelectorAll('[data-atlas-course-install-id]')];

  for (const card of cards) {
    if (card.getAttribute('data-atlas-r8-enhanced') === 'true') continue;
    const courseInstallId = card.getAttribute('data-atlas-course-install-id');
    if (!courseInstallId) continue;

    let context;
    try {
      context = await runtime.getAtlasCourseContext(courseInstallId);
    } catch {
      continue;
    }

    const segments = [...card.querySelectorAll('.course-objective-segment')];
    if (segments.length !== context.course.objectives.length) continue;

    const objectiveStates = context.course.objectives.map((objective, index) => ({
      objectiveId: objective.objectiveId,
      label: objective.label,
      state: atlasR8StateFromSegment(segments[index]),
    }));
    const groups = {
      work: objectiveStates.filter(item => atlasR8GroupForState(item.state) === 'work'),
      confirm: objectiveStates.filter(item => atlasR8GroupForState(item.state) === 'confirm'),
      acquired: objectiveStates.filter(item => atlasR8GroupForState(item.state) === 'acquired'),
    };

    const progress = card.querySelector('.course-progress-compact');
    if (!progress) continue;
    const currentNext = progress.querySelector('.course-next-step')?.textContent?.trim() ?? '';
    const target = objectiveStates.find(item => currentNext.includes(item.label)) ?? objectiveStates[0] ?? null;
    const situation = `${groups.acquired.length} acquis · ${groups.confirm.length} à confirmer · ${groups.work.length} à travailler`;

    progress.replaceChildren(
      atlasR8Node('div', {className: 'course-progress-at-glance'}, [
        atlasR8Node('span', {className: 'course-progress-caption', text: 'Votre situation'}),
        atlasR8Node('strong', {className: 'course-progress-text', text: situation}),
      ]),
      currentNext ? atlasR8Node('strong', {className: 'course-next-step', text: currentNext}) : null,
      target ? atlasR8Node('span', {className: 'help', text: atlasR8WhyNow(target.state)}) : null,
    );
    progress.setAttribute('data-atlas-progress-situation', 'true');

    const map = atlasR8Node('div', {
      className: 'course-learning-map',
      'data-atlas-learning-map': 'true',
      'aria-label': 'Détail de votre progression par objectif',
    }, [
      atlasR8Node('p', {className: 'course-progress-caption', text: 'Voir le détail par objectif'}),
    ]);

    const groupSpecs = [
      ['work', 'À travailler'],
      ['confirm', 'À confirmer'],
      ['acquired', 'Acquis'],
    ];
    for (const [groupKey, groupLabel] of groupSpecs) {
      const objectives = groups[groupKey];
      if (!objectives.length) continue;
      const details = atlasR8Node('details', {
        className: `course-learning-group course-learning-group--${groupKey}`,
        'data-atlas-progress-group': groupKey,
      }, [
        atlasR8Node('summary', {
          text: `${groupLabel} — ${objectives.length}`,
          'aria-label': `${groupLabel}, ${objectives.length} objectif${objectives.length > 1 ? 's' : ''}`,
        }),
        atlasR8Node('ul', {
          className: 'course-objective-status-list',
          'aria-label': groupLabel,
        }, objectives.map(item => atlasR8Node('li', {
          className: `course-objective-status-item course-objective-status-item--${item.state}`,
          'data-atlas-objective-state': item.state,
        }, [
          atlasR8Node('span', {text: item.label}),
          atlasR8Node('strong', {text: atlasR8StateLabel(item.state)}),
        ]))),
      ]);
      map.append(details);
    }

    progress.after(map);
    card.setAttribute('data-atlas-r8-enhanced', 'true');
  }
}

function installAtlasR8LearningMap(root, runtime) {
  const today = root.querySelector('[data-atlas-int-content="true"]');
  if (!today) return;
  let queued = false;
  const enhance = () => {
    if (queued) return;
    queued = true;
    queueMicrotask(async () => {
      queued = false;
      await enhanceAtlasR8LearningMap(root, runtime);
    });
  };
  const observer = new MutationObserver(enhance);
  observer.observe(today, {childList: true, subtree: true});
  enhance();
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
  installAtlasR8LearningMap(root, runtime);

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

// ATLAS_R8_DERIVED_PROGRESS_GROUPING_WIRED
