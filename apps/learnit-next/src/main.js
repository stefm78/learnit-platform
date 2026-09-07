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

function atlasR9StateFromSegment(segment) {
  const prefix = 'course-objective-segment--';
  const token = [...segment.classList].find(value => value.startsWith(prefix));
  return token ? token.slice(prefix.length) : 'training';
}

function atlasR9GroupForState(state) {
  if (state === 'validated-recently') return 'acquired';
  if (state === 'ready-for-validation') return 'confirm';
  return 'work';
}

function atlasR9StateLabel(state) {
  switch (state) {
    case 'not-started': return 'À découvrir';
    case 'training': return 'En apprentissage';
    case 'review-needed': return 'À renforcer';
    case 'ready-for-validation': return 'À confirmer';
    case 'validated-recently': return 'Acquis récemment';
    default: return 'En apprentissage';
  }
}

function atlasR9SymbolForState(state) {
  if (state === 'validated-recently') return '✓';
  if (state === 'ready-for-validation') return '◇';
  return '!';
}

function atlasR9Node(tag, attributes = {}, children = []) {
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

function atlasR9InstallStyles() {
  if (document.getElementById('atlas-r9-visual-progress-style')) return;
  const style = document.createElement('style');
  style.id = 'atlas-r9-visual-progress-style';
  style.textContent = `
    .atlas-r9-progress{display:grid;gap:.65rem;margin:.55rem 0 .2rem}
    .atlas-r9-overview{display:flex;gap:.55rem;align-items:center;flex-wrap:wrap}
    .atlas-r9-stat{display:inline-flex;gap:.3rem;align-items:center;font-weight:800;font-size:.88rem;padding:.28rem .48rem;border:1px solid #8090a8;border-radius:999px;background:#fff}
    .atlas-r9-stat-symbol{display:inline-grid;place-items:center;width:1.15rem;height:1.15rem;font-weight:900}
    .atlas-r9-map{display:grid;grid-template-columns:repeat(auto-fit,minmax(2rem,1fr));gap:.38rem;max-width:42rem}
    .atlas-r9-objective{position:relative;min-width:2rem;height:2rem;border:2px solid #4f6078;border-radius:.45rem;background:#fff;color:#11213a;font-weight:900;cursor:pointer}
    .atlas-r9-objective[data-atlas-r9-group="confirm"]{border-style:double;border-width:3px}
    .atlas-r9-objective[data-atlas-r9-group="acquired"]{border-radius:999px}
    .atlas-r9-objective[data-atlas-r9-priority="true"]{outline:3px solid #111827;outline-offset:2px;transform:translateY(-1px)}
    .atlas-r9-priority-mark{position:absolute;right:-.3rem;top:-.65rem;font-size:.78rem;background:#fff;line-height:1}
    .atlas-r9-action{display:grid;grid-template-columns:auto 1fr;gap:.25rem .55rem;align-items:center;padding:.6rem .7rem;border-left:5px solid #162b4e;background:#f7f9fc;border-radius:.35rem}
    .atlas-r9-action-kicker{font-size:.72rem;letter-spacing:.07em;text-transform:uppercase;font-weight:900}
    .atlas-r9-action-verb{font-size:1rem;font-weight:900}
    .atlas-r9-action-target{grid-column:1/-1;font-size:.93rem;font-weight:700;line-height:1.25}
    .atlas-r9-inspector{min-height:2.5rem;padding:.45rem .6rem;border:1px solid #c7d0dc;border-radius:.4rem;background:#fff}
    .atlas-r9-inspector[hidden]{display:none}
    .atlas-r9-inspector-state{font-size:.8rem;font-weight:900;text-transform:uppercase;letter-spacing:.04em}
    .atlas-r9-inspector-label{margin:.15rem 0 0;font-weight:700}
    .atlas-r9-hint{font-size:.78rem;color:#4d5a6e;margin:0}
    @media (max-width:700px){.atlas-r9-map{grid-template-columns:repeat(10,minmax(1.85rem,1fr))}.atlas-r9-action{grid-template-columns:1fr}}
  `;
  document.head.append(style);
}

function atlasR9ParseAction(currentNext, target) {
  const cleaned = String(currentNext || '').replace(/^À faire maintenant\s*:\s*/i, '').trim();
  if (!cleaned) return { verb: 'Continuer', target: target?.label ?? '' };
  const separator = cleaned.indexOf(':');
  if (separator < 0) return { verb: cleaned, target: target?.label ?? '' };
  return {
    verb: cleaned.slice(0, separator).trim(),
    target: cleaned.slice(separator + 1).trim() || target?.label || '',
  };
}

async function enhanceAtlasR9VisualProgress(root, runtime) {
  const today = root.querySelector('[data-atlas-int-content="true"]');
  if (!today) return;
  const cards = [...today.querySelectorAll('[data-atlas-course-install-id]')];

  for (const card of cards) {
    if (card.getAttribute('data-atlas-r9-enhanced') === 'true') continue;
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
      state: atlasR9StateFromSegment(segments[index]),
    }));
    const groups = {
      work: objectiveStates.filter(item => atlasR9GroupForState(item.state) === 'work'),
      confirm: objectiveStates.filter(item => atlasR9GroupForState(item.state) === 'confirm'),
      acquired: objectiveStates.filter(item => atlasR9GroupForState(item.state) === 'acquired'),
    };

    const progress = card.querySelector('.course-progress-compact');
    if (!progress) continue;
    const currentNext = progress.querySelector('.course-next-step')?.textContent?.trim() ?? '';
    const target = objectiveStates.find(item => currentNext.includes(item.label)) ?? objectiveStates.find(item => item.state === 'review-needed') ?? objectiveStates.find(item => item.state === 'ready-for-validation') ?? objectiveStates[0] ?? null;
    const action = atlasR9ParseAction(currentNext, target);

    const overview = atlasR9Node('div', {className: 'atlas-r9-overview', 'aria-label': 'Vue rapide de votre progression'}, [
      atlasR9Node('span', {className: 'atlas-r9-stat', 'data-atlas-r9-stat': 'work'}, [
        atlasR9Node('span', {className: 'atlas-r9-stat-symbol', text: '!'}),
        `${groups.work.length} à travailler`,
      ]),
      atlasR9Node('span', {className: 'atlas-r9-stat', 'data-atlas-r9-stat': 'confirm'}, [
        atlasR9Node('span', {className: 'atlas-r9-stat-symbol', text: '◇'}),
        `${groups.confirm.length} à confirmer`,
      ]),
      atlasR9Node('span', {className: 'atlas-r9-stat', 'data-atlas-r9-stat': 'acquired'}, [
        atlasR9Node('span', {className: 'atlas-r9-stat-symbol', text: '✓'}),
        `${groups.acquired.length} acquis`,
      ]),
    ]);

    const inspectorState = atlasR9Node('div', {className: 'atlas-r9-inspector-state'});
    const inspectorLabel = atlasR9Node('p', {className: 'atlas-r9-inspector-label'});
    const inspector = atlasR9Node('div', {
      className: 'atlas-r9-inspector',
      'data-atlas-r9-inspector': 'true',
      'aria-live': 'polite',
      hidden: 'hidden',
    }, [inspectorState, inspectorLabel]);

    const showObjective = (item) => {
      inspector.hidden = false;
      inspector.removeAttribute('hidden');
      inspectorState.textContent = atlasR9StateLabel(item.state);
      inspectorLabel.textContent = item.label;
    };

    const map = atlasR9Node('div', {
      className: 'atlas-r9-map',
      'data-atlas-r9-visual-map': 'true',
      role: 'group',
      'aria-label': `${objectiveStates.length} objectifs. Point d’exclamation : à travailler. Losange : à confirmer. Coche : acquis. Étoile : priorité actuelle.`,
    });
    objectiveStates.forEach((item, index) => {
      const isPriority = target?.objectiveId === item.objectiveId;
      const button = atlasR9Node('button', {
        type: 'button',
        className: 'atlas-r9-objective',
        'data-atlas-r9-objective': item.objectiveId,
        'data-atlas-r9-group': atlasR9GroupForState(item.state),
        'data-atlas-r9-priority': String(isPriority),
        'aria-label': `${index + 1}. ${item.label}. ${atlasR9StateLabel(item.state)}${isPriority ? '. Priorité actuelle' : ''}`,
        title: `${item.label} — ${atlasR9StateLabel(item.state)}`,
      }, [atlasR9SymbolForState(item.state)]);
      if (isPriority) button.append(atlasR9Node('span', {className: 'atlas-r9-priority-mark', 'aria-hidden': 'true', text: '★'}));
      button.addEventListener('click', () => showObjective(item));
      button.addEventListener('focus', () => showObjective(item));
      button.addEventListener('mouseenter', () => showObjective(item));
      map.append(button);
    });

    const actionBox = atlasR9Node('div', {className: 'atlas-r9-action', 'data-atlas-r9-next-action': 'true'}, [
      atlasR9Node('span', {className: 'atlas-r9-action-kicker', text: 'Priorité ★'}),
      atlasR9Node('strong', {className: 'atlas-r9-action-verb', text: action.verb || 'Continuer'}),
      atlasR9Node('div', {className: 'atlas-r9-action-target', text: action.target || target?.label || ''}),
    ]);

    progress.replaceChildren(
      atlasR9Node('div', {className: 'atlas-r9-progress', 'data-atlas-r9-progress': 'true'}, [
        overview,
        map,
        actionBox,
        atlasR9Node('p', {className: 'atlas-r9-hint', text: 'Touchez, survolez ou parcourez les repères pour voir l’objectif.'}),
        inspector,
      ]),
    );
    card.querySelector('.course-learning-map')?.remove();
    card.setAttribute('data-atlas-r9-enhanced', 'true');
  }
}

function installAtlasR9VisualProgress(root, runtime) {
  atlasR9InstallStyles();
  const today = root.querySelector('[data-atlas-int-content="true"]');
  if (!today) return;
  let queued = false;
  const enhance = () => {
    if (queued) return;
    queued = true;
    queueMicrotask(async () => {
      queued = false;
      await enhanceAtlasR9VisualProgress(root, runtime);
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
  installAtlasR9VisualProgress(root, runtime);

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

// ATLAS_R9_VISUAL_PROGRESS_AT_A_GLANCE_WIRED
