import { CONTRACT_VERSION } from '__LEARNIT_MODULE_URL_0005__';
import { installAtlasRuntime } from '__LEARNIT_MODULE_URL_0006__';
import { attachAtlasPreviewSurface } from '__LEARNIT_MODULE_URL_0007__';
import { createAtlasCompatibleImportService } from '__LEARNIT_MODULE_URL_0008__';
import { createImportService } from '__LEARNIT_MODULE_URL_0009__';
import { createLibraryService } from '__LEARNIT_MODULE_URL_0010__';
import {
  createLearningLoopV2DomainAdapters,
  createProgressService,
} from '__LEARNIT_MODULE_URL_0011__';
import { createSessionService } from '__LEARNIT_MODULE_URL_0012__';
import * as objectiveProgressDomain from '__LEARNIT_MODULE_URL_0013__';
import * as learningRecommendationDomain from '__LEARNIT_MODULE_URL_0014__';
import { createIndexedDbStorage } from '__LEARNIT_MODULE_URL_0015__';
import { assertStoragePort } from '__LEARNIT_MODULE_URL_0016__';
import * as objectiveUiModule from '__LEARNIT_MODULE_URL_0017__';
import { renderApp } from '__LEARNIT_MODULE_URL_0018__';

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

function atlasR13StatesFromProgress(progress, objectives) {
  const reservoirs = [...progress.querySelectorAll('[data-atlas-r13-objective]')];
  if (reservoirs.length === objectives.length && reservoirs.length > 0) {
    const byId = new Map(reservoirs.map(item => [
      item.getAttribute('data-atlas-r13-objective'),
      item,
    ]));
    return objectives.map(objective => ({
      objectiveId: objective.objectiveId,
      label: objective.label,
      state: byId.get(objective.objectiveId)?.getAttribute('data-atlas-r13-state') ?? 'not-started',
    }));
  }

  const segments = [...progress.querySelectorAll('.course-objective-segment')];
  if (segments.length !== objectives.length || !segments.length) return [];
  return objectives.map((objective, index) => ({
    objectiveId: objective.objectiveId,
    label: objective.label,
    state: atlasR13StateFromSegment(segments[index]),
  }));
}

function atlasR13JsonAttribute(element, name, fallback) {
  const raw = element?.getAttribute(name);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function renderAtlasR13Progress(progress, objectiveStates, target, sessionProjection = null) {
  const allAcquired = objectiveStates.length > 0
    && objectiveStates.every(item => item.state === 'validated-recently');
  const worked = new Set(sessionProjection?.workedObjectiveIds ?? []);
  const changed = new Set(sessionProjection?.changedObjectiveIds ?? []);
  const beforeStates = sessionProjection?.beforeStates ?? {};

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
    if (!sessionProjection || !worked.has(item.objectiveId)) {
      detailLabel.textContent = item.label;
      return;
    }
    const before = beforeStates[item.objectiveId] ?? item.state;
    detailLabel.textContent = changed.has(item.objectiveId)
      ? `${item.label} · Cette séance : ${atlasR13StateLabel(before)} → ${atlasR13StateLabel(item.state)}`
      : `${item.label} · Travaillé pendant cette séance, état inchangé`;
  };

  objectiveStates.forEach((item) => {
    const isPriority = !sessionProjection && target?.objectiveId === item.objectiveId;
    const wasWorked = worked.has(item.objectiveId);
    const didChange = changed.has(item.objectiveId);
    const reservoir = atlasR13Node('button', {
      type: 'button',
      className: `atlas-r13-reservoir atlas-r13-reservoir--${item.state}`,
      'data-atlas-r13-objective': item.objectiveId,
      'data-atlas-r13-state': item.state,
      'data-atlas-r13-priority': String(isPriority),
      'data-atlas-r13-session-worked': String(wasWorked),
      'data-atlas-r13-session-changed': String(didChange),
      'aria-label': `${item.label}. ${atlasR13StateLabel(item.state)}${isPriority ? '. Priorité Learn-it' : ''}${wasWorked ? '. Travaillé pendant cette séance' : ''}${didChange ? '. État modifié pendant cette séance' : ''}`,
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

  let context;
  if (sessionProjection) {
    const workedCount = worked.size;
    const changedCount = changed.size;
    context = atlasR13Node('div', {
      className: 'atlas-r13-context atlas-r13-session-context',
      'data-atlas-r13-context': 'true',
    }, [
      atlasR13Node('span', {className: 'atlas-r13-context-kicker', text: 'Cette séance'}),
      atlasR13Node('strong', {
        className: 'atlas-r13-context-state',
        text: `${workedCount} objectif${workedCount > 1 ? 's' : ''} travaillé${workedCount > 1 ? 's' : ''}`,
      }),
      atlasR13Node('span', {
        className: 'atlas-r13-context-target',
        text: changedCount
          ? `${changedCount} changement${changedCount > 1 ? 's' : ''} d’état visible${changedCount > 1 ? 's' : ''}`
          : 'État global inchangé',
      }),
    ]);
  } else {
    context = atlasR13Node('div', {
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
  }

  progress.replaceChildren(
    atlasR13Node('div', {
      className: 'atlas-r13-progress',
      'data-atlas-r13-progress': 'true',
      'data-atlas-r13-summary-progress': String(Boolean(sessionProjection)),
    }, [group, context, detail]),
  );
  if (target) progress.setAttribute('data-atlas-r13-target-objective', target.objectiveId);
  else progress.removeAttribute('data-atlas-r13-target-objective');
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
    if (!progress) continue;
    const enhanced = progress.getAttribute('data-atlas-r13-enhanced') === 'true';
    const plannedObjectiveId = card.getAttribute('data-atlas-planned-first-objective');
    if (enhanced && !plannedObjectiveId) continue;
    if (
      enhanced
      && progress.getAttribute('data-atlas-r13-target-objective') === plannedObjectiveId
    ) continue;

    let context;
    try {
      context = await runtime.getAtlasCourseContext(courseInstallId);
    } catch {
      continue;
    }

    const objectiveStates = atlasR13StatesFromProgress(progress, context.course.objectives);
    if (objectiveStates.length !== context.course.objectives.length || !objectiveStates.length) continue;

    const currentNext = progress.querySelector('.course-next-step')?.textContent?.trim() ?? '';
    const target = objectiveStates.find(item => item.objectiveId === plannedObjectiveId)
      ?? atlasR13PriorityTarget(currentNext, objectiveStates);

    renderAtlasR13Progress(progress, objectiveStates, target);
    progress.setAttribute('data-atlas-r13-enhanced', 'true');
    card.querySelector('.course-learning-map')?.remove();
  }
}

function atlasR13SummaryState(card) {
  const status = card.querySelector('.atlas-objective-status');
  if (!status) return null;
  const prefix = 'atlas-objective-status--';
  const token = [...status.classList].find(value => value.startsWith(prefix));
  return token ? token.slice(prefix.length) : null;
}

async function enhanceAtlasR13SessionSummaries(root, runtime) {
  const summaries = [
    ...root.querySelectorAll('.atlas-summary-overview:not([data-atlas-r13-summary-enhanced="true"])'),
  ];
  for (const summary of summaries) {
    const courseCard = summary.closest('[data-atlas-course-install-id]');
    const courseInstallId = courseCard?.getAttribute('data-atlas-course-install-id');
    if (!courseCard || !courseInstallId) continue;

    let context;
    try {
      context = await runtime.getAtlasCourseContext(courseInstallId);
    } catch {
      continue;
    }

    const beforeStates = atlasR13JsonAttribute(
      courseCard,
      'data-atlas-session-before-states',
      {},
    );
    const workedObjectiveIds = atlasR13JsonAttribute(
      courseCard,
      'data-atlas-session-objectives',
      [],
    );
    const observedByLabel = new Map();
    const summaryRoot = summary.closest('.atlas-summary');
    for (const objectiveCard of summaryRoot?.querySelectorAll('.atlas-objective-card') ?? []) {
      const label = objectiveCard.querySelector('.atlas-objective-name')?.textContent?.trim();
      const state = atlasR13SummaryState(objectiveCard);
      if (label && state) observedByLabel.set(label, state);
    }

    const objectiveStates = context.course.objectives.map(objective => ({
      objectiveId: objective.objectiveId,
      label: objective.label,
      state: observedByLabel.get(objective.label)
        ?? beforeStates[objective.objectiveId]
        ?? 'not-started',
    }));
    const changedObjectiveIds = objectiveStates
      .filter(item => (
        workedObjectiveIds.includes(item.objectiveId)
        && (beforeStates[item.objectiveId] ?? 'not-started') !== item.state
      ))
      .map(item => item.objectiveId);

    renderAtlasR13Progress(summary, objectiveStates, null, {
      workedObjectiveIds,
      changedObjectiveIds,
      beforeStates,
    });
    summary.setAttribute('data-atlas-r13-summary-enhanced', 'true');
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
    button.atlas-r13-reservoir{position:relative;flex:0 0 1.35rem;width:1.35rem;height:4.6rem;border:2px solid #68778d;border-radius:.45rem;background:#f7f9fc;overflow:hidden;padding:0;min-width:1.35rem}
    button.atlas-r13-reservoir:focus-visible{outline:3px solid #233f64;outline-offset:3px}
    .atlas-r13-reservoir[data-atlas-r13-priority="true"]{outline:2px solid #233f64;outline-offset:2px}
    button.atlas-r13-reservoir--not-started{border-color:#52647c;background:#fff}
    .atlas-r13-fill{position:absolute;left:0;right:0;bottom:0;height:var(--atlas-r13-level);background:#738bac}
    .atlas-r13-reservoir--not-started .atlas-r13-fill{background:#dfe3e8}
    .atlas-r13-reservoir--ready-for-validation .atlas-r13-fill{background:#7775a2}
    .atlas-r13-reservoir--review-needed .atlas-r13-fill{background:repeating-linear-gradient(135deg,#b48a46 0 5px,#ead8b8 5px 10px)}
    .atlas-r13-reservoir--validated-recently .atlas-r13-fill{background:#648a69}
    .atlas-r13-reservoir[data-atlas-r13-session-worked="true"]{box-shadow:0 0 0 2px #9bacc4}
    .atlas-r13-reservoir[data-atlas-r13-session-changed="true"]{outline:3px solid #3156d3;outline-offset:2px;box-shadow:none}
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
    .atlas-course-card[data-atlas-r13-session-owned="true"] .atlas-summary-overview .atlas-r13-progress{display:grid!important}
    @media(max-width:640px){
      .atlas-r13-group{padding:.58rem}
      button.atlas-r13-reservoir{flex-basis:1.2rem;width:1.2rem;min-width:1.2rem;height:4.1rem}
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
      await enhanceAtlasR13SessionSummaries(root, runtime);
    });
  };

  const observer = new MutationObserver(reconcile);
  observer.observe(root, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['data-atlas-planned-first-objective'],
  });
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

// ATLAS_R14_SESSION_BOUND_OBJECTIVE_MAP
