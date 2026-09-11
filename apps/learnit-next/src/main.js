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

function resolveBuildIdentity(locationRef = globalThis.location, explicitValue = globalThis.__LEARNIT_BUILD_ID__) {
  const explicit = typeof explicitValue === 'string' ? explicitValue.trim() : '';
  if (/^[0-9a-f]{40}$/i.test(explicit)) return explicit.toLowerCase();

  const pathname = String(locationRef?.pathname ?? '');
  const replayMatch = pathname.match(/\/human-replay\/([0-9a-f]{40})(?:\/|$)/i);
  return replayMatch ? replayMatch[1].toLowerCase() : null;
}

function installBuildIdentityBadge(documentRef = globalThis.document) {
  if (!documentRef?.body) return null;
  const existing = documentRef.querySelector('[data-learnit-build-identity]');
  if (existing) return existing;

  const identity = resolveBuildIdentity();
  if (!identity) return null;
  const badge = documentRef.createElement('div');
  badge.className = 'learnit-build-identity';
  badge.setAttribute('data-learnit-build-identity', identity);
  badge.setAttribute('aria-label', `Build Learn-it ${identity}`);
  badge.title = `Build exact : ${identity}`;
  badge.textContent = `build ${identity.slice(0, 8)}`;
  documentRef.body.append(badge);
  return badge;
}

function atlasR13StateFromSegment(segment) {
  const prefix = 'course-objective-segment--';
  const token = [...segment.classList].find(value => value.startsWith(prefix));
  return token ? token.slice(prefix.length) : 'training';
}

function atlasR13StateLabel(state) {
  switch (state) {
    case 'not-started': return 'À découvrir';
    case 'training': return 'En apprentissage';
    case 'review-needed': return 'À renforcer';
    case 'ready-for-validation': return 'À confirmer';
    case 'validated-recently': return 'Acquis récemment';
    default: return 'En apprentissage';
  }
}

function atlasR13VisualLevel(state) {
  switch (state) {
    case 'not-started': return '0%';
    case 'training': return '48%';
    case 'review-needed': return '46%';
    case 'ready-for-validation': return '82%';
    case 'validated-recently': return '100%';
    default: return '48%';
  }
}

function atlasR13Node(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === 'className') element.className = value;
    else if (name === 'text') element.textContent = String(value);
    else if (name === 'hidden') element.hidden = Boolean(value);
    else element.setAttribute(name, String(value));
  }
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child == null) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}

function atlasR13PriorityTarget(currentNext, objectiveStates) {
  const text = String(currentNext || '');
  return objectiveStates.find(item => text.includes(item.label))
    ?? objectiveStates.find(item => item.state === 'review-needed')
    ?? objectiveStates.find(item => item.state === 'ready-for-validation')
    ?? objectiveStates.find(item => item.state !== 'validated-recently')
    ?? objectiveStates[0]
    ?? null;
}

function renderAtlasR13Progress(progress, objectiveStates, target) {
  const allAcquired = objectiveStates.length > 0
    && objectiveStates.every(item => item.state === 'validated-recently');

  const groupLabel = atlasR13Node('span', {
    className: 'atlas-r13-group-label',
    text: 'Objectifs du cours',
  });

  const reservoirs = atlasR13Node('div', {
    className: 'atlas-r13-reservoirs',
    role: 'group',
    'aria-label': `${objectiveStates.length} objectifs du cours`,
  });

  const detailState = atlasR13Node('strong', {className: 'atlas-r13-detail-state'});
  const detailLabel = atlasR13Node('span', {className: 'atlas-r13-detail-label'});
  const detail = atlasR13Node('div', {
    className: 'atlas-r13-detail',
    'data-atlas-r13-detail': 'true',
    'aria-live': 'polite',
    hidden: true,
  }, [detailState, detailLabel]);

  const showDetail = (item) => {
    detail.hidden = false;
    detailState.textContent = atlasR13StateLabel(item.state);
    detailLabel.textContent = item.label;
  };

  objectiveStates.forEach((item) => {
    const isPriority = target?.objectiveId === item.objectiveId;
    const reservoir = atlasR13Node('button', {
      type: 'button',
      className: `atlas-r13-reservoir atlas-r13-reservoir--${item.state}`,
      'data-atlas-r13-objective': item.objectiveId,
      'data-atlas-r13-state': item.state,
      'data-atlas-r13-priority': String(isPriority),
      'aria-label': `${item.label}. ${atlasR13StateLabel(item.state)}${isPriority ? '. Priorité Learn-it' : ''}`,
      title: `${item.label} — ${atlasR13StateLabel(item.state)}`,
    }, [
      atlasR13Node('span', {
        className: 'atlas-r13-fill',
        'aria-hidden': 'true',
        style: `--atlas-r13-level:${atlasR13VisualLevel(item.state)}`,
      }),
      item.state === 'review-needed'
        ? atlasR13Node('span', {className: 'atlas-r13-state-mark', 'aria-hidden': 'true', text: '↺'})
        : item.state === 'ready-for-validation'
          ? atlasR13Node('span', {className: 'atlas-r13-state-mark', 'aria-hidden': 'true', text: '◇'})
          : item.state === 'validated-recently'
            ? atlasR13Node('span', {className: 'atlas-r13-state-mark', 'aria-hidden': 'true', text: '✓'})
            : null,
    ]);
    reservoir.addEventListener('click', () => showDetail(item));
    reservoir.addEventListener('focus', () => showDetail(item));
    reservoirs.append(reservoir);
  });

  const group = atlasR13Node('div', {
    className: `atlas-r13-group${allAcquired ? ' atlas-r13-group--consolidated' : ''}`,
    'data-atlas-r13-group': 'objectifs-du-cours',
    'data-atlas-r13-consolidated': String(allAcquired),
  }, [groupLabel, reservoirs]);

  const context = atlasR13Node('div', {
    className: 'atlas-r13-context',
    'data-atlas-r13-context': 'true',
  }, [
    atlasR13Node('span', {className: 'atlas-r13-context-kicker', text: 'Priorité Learn-it'}),
    atlasR13Node('strong', {
      className: 'atlas-r13-context-state',
      text: target ? atlasR13StateLabel(target.state) : 'À jour',
    }),
    atlasR13Node('span', {
      className: 'atlas-r13-context-target',
      text: target?.label ?? 'Aucun objectif prioritaire',
    }),
  ]);

  progress.replaceChildren(
    atlasR13Node('div', {
      className: 'atlas-r13-progress',
      'data-atlas-r13-progress': 'true',
    }, [group, context, detail]),
  );
}

async function enhanceAtlasR13VisualProgress(root, runtime) {
  const cards = [
    ...root.querySelectorAll(
      '[data-atlas-course-install-id], .course-card[data-course-install-id]',
    ),
  ];

  for (const card of cards) {
    const courseInstallId = card.getAttribute('data-atlas-course-install-id')
      ?? card.getAttribute('data-course-install-id');
    if (!courseInstallId) continue;

    const progress = card.querySelector('.course-progress-compact');
    if (!progress || progress.getAttribute('data-atlas-r13-enhanced') === 'true') continue;

    let context;
    try {
      context = await runtime.getAtlasCourseContext(courseInstallId);
    } catch {
      continue;
    }

    const segments = [...progress.querySelectorAll('.course-objective-segment')];
    if (segments.length !== context.course.objectives.length || !segments.length) continue;

    const objectiveStates = context.course.objectives.map((objective, index) => ({
      objectiveId: objective.objectiveId,
      label: objective.label,
      state: atlasR13StateFromSegment(segments[index]),
    }));
    const currentNext = progress.querySelector('.course-next-step')?.textContent?.trim() ?? '';
    const target = atlasR13PriorityTarget(currentNext, objectiveStates);

    renderAtlasR13Progress(progress, objectiveStates, target);
    progress.setAttribute('data-atlas-r13-enhanced', 'true');
    card.querySelector('.course-learning-map')?.remove();
  }
}

function installAtlasR13Styles(documentRef = globalThis.document) {
  if (!documentRef?.head || documentRef.querySelector('[data-atlas-r13-styles]')) return;
  const style = documentRef.createElement('style');
  style.setAttribute('data-atlas-r13-styles', 'true');
  style.textContent = `
    .atlas-r13-progress{display:grid;gap:.75rem}
    .atlas-r13-group{border:1px solid #d7dce5;border-radius:14px;padding:.65rem .75rem;background:#fbfcfd;min-width:0}
    .atlas-r13-group--consolidated{border-color:#8eae94;background:#eef7f0}
    .atlas-r13-group-label{display:block;font-size:.78rem;font-weight:700;color:#586276;margin-bottom:.55rem}
    .atlas-r13-reservoirs{display:flex;gap:.42rem;align-items:flex-end;overflow-x:auto;padding:.25rem .18rem .38rem;scrollbar-width:thin}
    .atlas-r13-reservoir{position:relative;flex:0 0 1.35rem;width:1.35rem;height:4.6rem;border:1.5px solid #99a3b1;border-radius:.45rem;background:#eef1f4;overflow:hidden;padding:0;min-width:1.35rem}
    .atlas-r13-reservoir:focus-visible{outline:3px solid #233f64;outline-offset:3px}
    .atlas-r13-reservoir[data-atlas-r13-priority="true"]{outline:2px solid #3a5378;outline-offset:2px}
    .atlas-r13-fill{position:absolute;left:0;right:0;bottom:0;height:var(--atlas-r13-level);background:#738bac}
    .atlas-r13-reservoir--not-started .atlas-r13-fill{background:#dfe3e8}
    .atlas-r13-reservoir--ready-for-validation .atlas-r13-fill{background:#7775a2}
    .atlas-r13-reservoir--review-needed .atlas-r13-fill{background:repeating-linear-gradient(135deg,#b48a46 0 5px,#ead8b8 5px 10px)}
    .atlas-r13-reservoir--validated-recently .atlas-r13-fill{background:#648a69}
    .atlas-r13-state-mark{position:absolute;inset:auto 0 .1rem;text-align:center;font-size:.7rem;font-weight:800;color:#172033;z-index:1}
    .atlas-r13-reservoir--validated-recently .atlas-r13-state-mark{color:#fff}
    .atlas-r13-context{display:grid;grid-template-columns:auto auto minmax(0,1fr);gap:.35rem .65rem;align-items:baseline;border-top:1px solid #e3e6eb;padding-top:.65rem}
    .atlas-r13-context-kicker{font-size:.74rem;color:#657083}
    .atlas-r13-context-state{font-size:.82rem}
    .atlas-r13-context-target{font-size:.88rem;min-width:0}
    .atlas-r13-detail{display:grid;gap:.15rem;border-radius:10px;background:#f5f7f9;padding:.55rem .65rem;font-size:.84rem}
    .atlas-r13-detail[hidden]{display:none}
    .atlas-library-rename{margin:0!important;padding:0!important;border:0!important;background:transparent!important}
    .atlas-library-rename>summary{display:inline-flex;cursor:pointer;font-size:.82rem;color:#44536a}
    .atlas-course-card[data-atlas-r13-session-owned="true"]>.course-row-main{display:none!important}
    .atlas-course-card[data-atlas-r13-session-owned="true"]>.atlas-course-actions{display:none!important}
    .atlas-course-card[data-atlas-r13-session-owned="true"] .atlas-r13-progress{display:none!important}
    @media(max-width:640px){
      .atlas-r13-group{padding:.58rem}
      .atlas-r13-reservoir{flex-basis:1.2rem;width:1.2rem;min-width:1.2rem;height:4.1rem}
      .atlas-r13-context{grid-template-columns:1fr;gap:.18rem}
    }
  `;
  documentRef.head.append(style);
}

function installAtlasR13RuntimeBehavior(root, runtime) {
  let queued = false;

  const reconcile = () => {
    if (queued) return;
    queued = true;
    queueMicrotask(async () => {
      queued = false;

      await enhanceAtlasR13VisualProgress(root, runtime);

      for (const card of root.querySelectorAll('.atlas-course-card')) {
        const active = Boolean(card.querySelector('[data-atlas-session-active="true"]'));
        const owned = card.getAttribute('data-atlas-r13-session-owned') === 'true';
        if (active && !owned) card.setAttribute('data-atlas-r13-session-owned', 'true');
        else if (!active && owned) card.removeAttribute('data-atlas-r13-session-owned');
      }

      for (const start of root.querySelectorAll(
        '.atlas-int-preview [data-atlas-action="start"]:not([data-atlas-r13-auto-started])',
      )) {
        if (start.closest('[data-atlas-session-active="true"]')) continue;
        start.setAttribute('data-atlas-r13-auto-started', 'true');
        start.click();
      }
    });
  };

  const observer = new MutationObserver(reconcile);
  observer.observe(root, {childList: true, subtree: true, attributes: true});
  reconcile();
}

function renderAtlasR13Fixture(container, states, priorityIndex = 0) {
  const objectiveStates = states.map((state, index) => ({
    objectiveId: `fixture-objective-${index + 1}`,
    label: `Objectif ${index + 1}`,
    state,
  }));
  const target = objectiveStates[priorityIndex] ?? objectiveStates[0] ?? null;
  renderAtlasR13Progress(container, objectiveStates, target);
  return container;
}

async function boot() {
  const root = document.getElementById('app');
  if (!root) throw new Error('Missing #app mount point');
  const integrations = resolveIntegrations(
    globalThis[LEARNING_LOOP_V2_COMPOSITION.registry] ?? defaultIntegrations,
  );
  const runtime = createLearnitRuntime(createIndexedDbStorage(), integrations);
  installAtlasR13Styles();
  renderApp(root, runtime, integrations.objectiveUi);
  installBuildIdentityBadge();
  await waitForInitialRender(root);

  await attachAtlasPreviewSurface({
    root,
    runtime,
    atlasRuntime,
  });
  installAtlasR13RuntimeBehavior(root, runtime);

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
    renderAtlasR13Fixture,
  });
}

if (typeof document !== 'undefined' && document.querySelector('[data-learnit-next-app]')) {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
}

// ATLAS_R13_COMPACT_BALANCED_VISUAL_CONTRACT