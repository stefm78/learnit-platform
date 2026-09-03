import {
  findResumableAtlasSession,
  runAtlasSession,
} from './session.js';

const DURATIONS = Object.freeze([5, 15, 30]);

function node(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === 'className') element.className = value;
    else if (name === 'text') element.textContent = String(value);
    else if (name === 'disabled') element.disabled = Boolean(value);
    else element.setAttribute(name, String(value));
  }
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child == null) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}

function compatibleAtlasCourse(context) {
  const course = context?.course;
  return Boolean(
    course
    && Array.isArray(course.objectives)
    && course.objectives.length > 0
    && Array.isArray(course.activities)
    && course.activities.length > 0
    && course.activities.every(activity => (
      Array.isArray(activity.objectiveIds)
      && activity.objectiveIds.length === 1
      && typeof activity.learningPhase === 'string'
      && typeof activity.assessmentRole === 'string'
      && Number.isInteger(activity.estimatedMinutes)
      && activity.estimatedMinutes >= 1
      && activity.estimatedMinutes <= 30
    ))
  );
}

function learnerObjectiveLabels(context) {
  return Object.freeze(Object.fromEntries(
    (context.course.objectives || [])
      .filter(objective => (
        typeof objective.objectiveId === 'string'
        && typeof objective.label === 'string'
        && objective.label.trim()
      ))
      .map(objective => [
        objective.objectiveId,
        objective.label.trim(),
      ]),
  ));
}

function learnerDateTime(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function emptyEvidence(objectiveRef) {
  return Object.freeze({
    evidenceVersion: 'atlas.objective-evidence.v1',
    objectiveRef,
    practiceAttempts: 0,
    correctionsCompleted: 0,
    validationAttempts: 0,
    latestPracticeCorrect: null,
    latestValidationCorrect: null,
    lastValidationAt: null,
    lastEvidenceAt: null,
    state: 'not-started',
  });
}

function buildContentIndex(context, modules) {
  const E = modules.evidence;
  const course = context.course;
  const courseRef = Object.freeze({
    packageLineageId: context.packageLineageId,
    courseLineageId: course.courseLineageId,
  });
  const contentRevisionRef = Object.freeze({
    packageLineageId: context.packageLineageId,
    packageRevisionId: context.packageRevisionId,
    packageDigest: context.packageDigest,
  });
  const authorIndexes = new Map();
  const activities = [];
  const links = [];

  for (const source of course.activities) {
    if (source.objectiveIds.length !== 1) {
      throw new Error('ATLAS_INT_REQUIRES_SINGLE_OBJECTIVE_ACTIVITY');
    }
    const objectiveRef = Object.freeze({courseRef, objectiveId: source.objectiveIds[0]});
    const activityRef = Object.freeze({courseRef, activityLineageId: source.activityLineageId});
    activities.push(Object.freeze({
      activityRef,
      objectiveRef,
      learningPhase: source.learningPhase,
      assessmentRole: source.assessmentRole,
      estimatedMinutes: source.estimatedMinutes,
    }));
    const objectiveKey = E.canonicalRefKey(objectiveRef);
    const authorIndex = authorIndexes.get(objectiveKey) ?? 0;
    authorIndexes.set(objectiveKey, authorIndex + 1);
    links.push(Object.freeze({objectiveRef, activityRef, authorIndex}));
  }

  return Object.freeze({
    courseRef,
    contentRevisionRef,
    objectiveRefs: course.objectives.map(objective => Object.freeze({
      courseRef,
      objectiveId: objective.objectiveId,
    })),
    index: E.indexActivities(activities, links),
  });
}

async function atlasState(modules) {
  const storage = await modules.indexedDb.IndexedDbAtlasStorage.open();
  try {
    return storage.snapshot();
  } finally {
    storage.close();
  }
}

function eventForExecution(state, executionId) {
  return state.learningEvents.find(event => (
    event.kind === 'activity-attempt'
    && event.executionId === executionId
  )) ?? null;
}

function claimDetailsForExecution(state, execution, modules) {
  const session = state.atlasMeta.sessions[execution.sessionRef.sessionId];
  const planItem = session?.plan?.payload?.items?.[execution.itemPosition];
  if (!planItem || !['attempt-validation', 'maintain-recent-validation'].includes(planItem.action)) {
    return null;
  }
  const sourceEvent = state.learningEvents.find(event => event.eventId === planItem.validationBasisEventId);
  const sourceExecution = sourceEvent
    ? state.scoredExecutions.find(item => item.executionId === sourceEvent.executionId)
    : null;
  if (!sourceEvent || !sourceExecution) return null;
  const details = {
    objectiveRef: execution.objectiveRef,
    sourceActivityRef: sourceExecution.activityRef,
    targetActivityRef: execution.activityRef,
    sourceEvent,
    sourceExecution,
    targetExecution: execution,
    contentRevisionRef: execution.contentRevisionRef,
    independenceClaimId: planItem.independenceClaimId,
  };
  return modules.claimAuthority.validateRuntimeClaim(planItem, details)
    ? Object.freeze({planItem, sourceEvent, sourceExecution})
    : null;
}

function admissibleValidationIds(state, modules) {
  const result = new Set();
  for (const execution of state.scoredExecutions) {
    if (execution.executionClass !== 'validation') continue;
    if (claimDetailsForExecution(state, execution, modules)) result.add(execution.executionId);
  }
  return result;
}

function correctionTarget(state, objectiveRef, modules) {
  const E = modules.evidence;
  const executions = new Map(state.scoredExecutions.map(record => [record.executionId, record]));
  const corrected = new Set(
    state.learningEvents
      .filter(event => event.kind === 'activity-corrected')
      .map(event => event.correctsEventId),
  );
  const candidates = state.learningEvents
    .filter(event => event.kind === 'activity-attempt')
    .filter(event => E.sameRef(event.objectiveRef, objectiveRef))
    .filter(event => {
      const execution = executions.get(event.executionId);
      return execution
        && execution.executionClass === 'practice'
        && execution.outcome === 'incorrect'
        && !corrected.has(event.eventId);
    })
    .sort((left, right) => left.occurredAt.localeCompare(right.occurredAt) || left.eventId.localeCompare(right.eventId));
  return candidates.at(-1) ?? null;
}

function correctionProvenance(state, objectiveRef, modules) {
  const target = correctionTarget(state, objectiveRef, modules);
  if (!target) throw new Error('ATLAS_CORRECTION_TARGET_NOT_FOUND');
  return Object.freeze({correctsEventId: target.eventId});
}

function acceptedBasisCandidates(state, objectiveRef, modules, executionClass) {
  const E = modules.evidence;
  return state.scoredExecutions
    .filter(execution => (
      execution.executionClass === executionClass
      && execution.outcome === 'correct'
      && E.sameRef(execution.objectiveRef, objectiveRef)
    ))
    .filter(execution => executionClass !== 'validation' || execution.assistance === 'none')
    .slice()
    .sort((left, right) => (
      right.scoredAt.localeCompare(left.scoredAt)
      || right.executionId.localeCompare(left.executionId)
    ));
}

function acceptedTargets(context, objectiveRef, basisExecution, modules) {
  const targets = modules.claimAuthority.targetsForBasis({
    context,
    objectiveRef,
    sourceActivityRef: basisExecution.activityRef,
  });
  return targets.filter(target => {
    const activity = context.course.activities.find(item => (
      item.activityLineageId === target.targetActivityRef.activityLineageId
    ));
    return activity?.learningPhase === 'validation'
      && activity?.assessmentRole === 'validation';
  });
}

function firstValidationOpportunity(context, state, objectiveRef, modules) {
  for (const basisExecution of acceptedBasisCandidates(state, objectiveRef, modules, 'practice')) {
    const sourceEvent = eventForExecution(state, basisExecution.executionId);
    if (!sourceEvent) continue;
    const targets = acceptedTargets(context, objectiveRef, basisExecution, modules);
    if (targets.length) return Object.freeze({basisExecution, sourceEvent, targets});
  }
  return null;
}

function maintenanceOpportunity(context, state, objectiveRef, admissibleIds, now, modules) {
  const memory = modules.memory.status({
    now,
    executions: state.scoredExecutions,
    objectiveRef,
    admissibleExecutionIds: admissibleIds,
    evidenceModule: modules.evidence,
  });
  if (!memory.hasIndependentValidation || !memory.due || !memory.basisExecution) {
    return Object.freeze({memory, opportunity: null});
  }
  const sourceEvent = eventForExecution(state, memory.basisExecution.executionId);
  if (!sourceEvent) return Object.freeze({memory, opportunity: null});
  const targets = acceptedTargets(context, objectiveRef, memory.basisExecution, modules);
  if (!targets.length) return Object.freeze({memory, opportunity: null});
  return Object.freeze({
    memory,
    opportunity: Object.freeze({
      basisExecution: memory.basisExecution,
      sourceEvent,
      targets,
    }),
  });
}

function hasTransferActivity(context, objectiveRef) {
  return context.course.activities.some(activity => (
    Array.isArray(activity.objectiveIds)
    && activity.objectiveIds.length === 1
    && activity.objectiveIds[0] === objectiveRef.objectiveId
    && activity.learningPhase === 'transfer'
    && activity.assessmentRole === 'practice'
  ));
}

function recommendationContext(context, state, row, admissibleIds, now, modules) {
  if (row.evidence.state === 'review-needed') {
    return Object.freeze({
      hasAcceptedValidation: false,
      maintenanceEligible: false,
      hasCorrectablePracticeError: Boolean(correctionTarget(state, row.objectiveRef, modules)),
    });
  }
  if (row.evidence.state === 'ready-for-validation') {
    const opportunity = firstValidationOpportunity(context, state, row.objectiveRef, modules);
    if (!opportunity) return Object.freeze({hasAcceptedValidation: false, maintenanceEligible: false});
    return Object.freeze({
      hasAcceptedValidation: true,
      maintenanceEligible: false,
      acceptedTargetActivityRefs: Object.freeze(opportunity.targets.map(target => target.targetActivityRef)),
      opportunity,
    });
  }
  if (row.evidence.state === 'validated-recently') {
    const maintenance = maintenanceOpportunity(context, state, row.objectiveRef, admissibleIds, now, modules);
    if (maintenance.opportunity) {
      return Object.freeze({
        hasAcceptedValidation: true,
        maintenanceEligible: true,
        transferEligible: false,
        acceptedTargetActivityRefs: Object.freeze(
          maintenance.opportunity.targets.map(target => target.targetActivityRef),
        ),
        opportunity: maintenance.opportunity,
        memory: maintenance.memory,
      });
    }
    const transfer = modules.transfer.status({
      learningEvents: state.learningEvents,
      scoredExecutions: state.scoredExecutions,
      objectiveRef: row.objectiveRef,
      admissibleExecutionIds: admissibleIds,
      evidenceModule: modules.evidence,
    });
    return Object.freeze({
      hasAcceptedValidation: true,
      maintenanceEligible: false,
      transferEligible: transfer.eligible && hasTransferActivity(context, row.objectiveRef),
      memory: maintenance.memory,
      transfer,
    });
  }
  return Object.freeze({hasAcceptedValidation: false, maintenanceEligible: false});
}

function validationProvenance(recommendation, context, modules) {
  const opportunity = context.opportunity;
  if (!opportunity) throw new Error('ATLAS_VALIDATION_OPPORTUNITY_MISSING');
  const accepted = opportunity.targets.find(target => (
    modules.evidence.sameRef(target.targetActivityRef, recommendation.preferredActivityRef)
  ));
  if (!accepted) throw new Error('ATLAS_VALIDATION_TARGET_NOT_ACCEPTED');
  return Object.freeze({
    validationBasisEventId: opportunity.sourceEvent.eventId,
    independenceClaimId: accepted.claimId,
  });
}

async function buildPreview(context, durationMinutes, atlasRuntime) {
  const modules = atlasRuntime.modules;
  const E = modules.evidence;
  const content = buildContentIndex(context, modules);
  const state = await atlasState(modules);
  const admissibleIds = admissibleValidationIds(state, modules);

  const projected = modules.projection.projectObjectiveEvidence(
    state.learningEvents,
    state.scoredExecutions,
    execution => admissibleIds.has(execution.executionId),
  );
  const evidenceByObjective = new Map(
    projected.map(evidence => [E.canonicalRefKey(evidence.objectiveRef), evidence]),
  );
  const rows = content.objectiveRefs.map(objectiveRef => ({
    objectiveRef,
    evidence: evidenceByObjective.get(E.canonicalRefKey(objectiveRef)) ?? emptyEvidence(objectiveRef),
  }));
  const ranked = modules.recommendation.rankRecommendations(rows, state.learningEvents);
  const now = new Date().toISOString();
  const contexts = new Map();

  const recommendations = ranked.map(row => {
    const detail = recommendationContext(context, state, row, admissibleIds, now, modules);
    contexts.set(E.canonicalRefKey(row.objectiveRef), detail);
    return modules.recommendation.buildRecommendation({
      objectiveRef: row.objectiveRef,
      evidence: row.evidence,
      index: content.index,
      context: detail,
    });
  });

  const itemProvenance = recommendations.map(recommendation => {
    if (recommendation.action === 'correct-practice') {
      return correctionProvenance(state, recommendation.objectiveRef, modules);
    }
    if (['attempt-validation', 'maintain-recent-validation'].includes(recommendation.action)) {
      return validationProvenance(
        recommendation,
        contexts.get(E.canonicalRefKey(recommendation.objectiveRef)),
        modules,
      );
    }
    return {};
  });

  const plan = modules.planner.buildPlan({
    engineVersion: 'atlas.m2.transfer.v1',
    courseRef: content.courseRef,
    contentRevisionRef: content.contentRevisionRef,
    durationMinutes,
    recommendations,
    itemProvenance,
  });

  return Object.freeze({
    recommendation: recommendations[0],
    plan,
    memory: contexts.get(E.canonicalRefKey(recommendations[0].objectiveRef))?.memory ?? null,
  });
}

function renderError(container, error) {
  container.replaceChildren(
    node('div', {className: 'notice notice-error', role: 'alert'}, [
      node('strong', {text: 'Atlas ne peut pas construire cette séance.'}),
      node('p', {text: error?.code ?? error?.message ?? String(error)}),
    ]),
  );
}

export async function attachAtlasPreviewSurface({root, runtime, atlasRuntime}) {
  if (!root || !runtime || !atlasRuntime?.ready) throw new Error('ATLAS_SURFACE_DEPENDENCY_MISSING');
  const previous = root.querySelector('[data-atlas-int-surface]');
  if (previous) previous.remove();

  const content = node('div', {'data-atlas-int-content': 'true'});
  const surface = node('section', {
    className: 'atlas-m1 atlas-int-surface',
    'aria-labelledby': 'atlas-int-title',
    'data-atlas-int-surface': 'ready',
  }, [
    node('div', {className: 'section-heading'}, [
      node('div', {}, [
        node('h2', {id: 'atlas-int-title', text: 'Aujourd’hui'}),
        node('p', {text: 'Choisissez votre cours et le temps disponible.'}),
      ]),
      node('button', {
        type: 'button',
        className: 'secondary',
        text: 'Afficher la bibliothèque',
        'data-atlas-library-toggle': 'true',
      }),
    ]),
    content,
  ]);
  const header = root.querySelector('.app-header') ?? root.firstElementChild;
  if (header?.parentNode === root) header.after(surface);
  else root.prepend(surface);

  const appMain = root.querySelector('.app-main');
  const classicDisplay = appMain?.style.display ?? '';
  const classicWasInert = appMain?.hasAttribute('inert') ?? false;
  const libraryToggle = surface.querySelector('[data-atlas-library-toggle="true"]');
  let libraryVisible = false;
  let atlasContextsByInstallId = new Map();

  function setClassicVisible(visible) {
    libraryVisible = Boolean(visible);
    if (!appMain || !libraryToggle) return;

    if (libraryVisible) {
      appMain.style.display = classicDisplay;
      if (!classicWasInert) appMain.removeAttribute('inert');
      libraryToggle.textContent = 'Masquer la bibliothèque';
      libraryToggle.setAttribute('aria-expanded', 'true');
      return;
    }

    appMain.style.display = 'none';
    appMain.setAttribute('inert', '');
    libraryToggle.textContent = 'Afficher la bibliothèque';
    libraryToggle.setAttribute('aria-expanded', 'false');
  }

  libraryToggle?.addEventListener('click', () => {
    const nextVisible = !libraryVisible;
    if (nextVisible) {
      root.dispatchEvent(new CustomEvent('learnit:show-library'));
    }
    setClassicVisible(nextVisible);
  });

  function atlasCardFor(courseInstallId) {
    return [...content.querySelectorAll('[data-atlas-course-install-id]')]
      .find(card => (
        card.getAttribute('data-atlas-course-install-id') === courseInstallId
      )) ?? null;
  }

  async function openAtlasCourse(courseInstallId) {
    setClassicVisible(false);
    let card = atlasCardFor(courseInstallId);
    if (!card) {
      await refresh();
      card = atlasCardFor(courseInstallId);
    }
    if (!card) return;

    const resumeButton = card.querySelector('[data-atlas-resume-session="true"]');
    if (resumeButton) {
      resumeButton.click();
      return;
    }

    const durationButton = (
      card.querySelector('[data-atlas-duration="15"]')
      ?? card.querySelector('[data-atlas-duration]')
    );
    card.scrollIntoView?.({block: 'start'});
    durationButton?.focus();
  }

  root.addEventListener('click', event => {
    const action = event.target instanceof Element
      ? event.target.closest('[data-course-learning-action][data-course-install-id]')
      : null;
    const courseInstallId = action?.getAttribute('data-course-install-id');
    if (!courseInstallId || !atlasContextsByInstallId.has(courseInstallId)) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    void openAtlasCourse(courseInstallId);
  }, true);

  async function refresh() {
    const courses = await runtime.listCourses();
    const atlasCourses = [];
    for (const course of courses) {
      try {
        const context = await runtime.getAtlasCourseContext(course.courseInstallId);
        if (compatibleAtlasCourse(context)) atlasCourses.push(context);
      } catch {
        // Non-Atlas or incomplete local course remains handled by the classic UI.
      }
    }

    atlasContextsByInstallId = new Map(
      atlasCourses.map(context => [context.courseInstallId, context]),
    );

    if (!atlasCourses.length) {
      if (appMain) {
        appMain.style.display = classicDisplay;
        if (!classicWasInert) appMain.removeAttribute('inert');
      }
      if (libraryToggle) libraryToggle.style.display = 'none';
      content.replaceChildren(node('div', {className: 'empty-state'}, [
        node('h3', {text: 'Aucun parcours Atlas installé'}),
        node('p', {text: 'Importez un kit Atlas dans la bibliothèque Learn-it pour préparer une séance de 5, 15 ou 30 minutes.'}),
      ]));
      return;
    }

    if (libraryToggle) libraryToggle.style.display = '';
    setClassicVisible(libraryVisible);

    const cards = [];
    for (const context of atlasCourses) {
      const preview = node('div', {className: 'atlas-int-preview', 'aria-live': 'polite'});
      const actions = node('div', {
        className: 'atlas-actions',
        role: 'group',
        'aria-label': `Durée pour ${context.title}`,
        'data-atlas-planner-actions': 'true',
      });
      const resumable = await findResumableAtlasSession(context, atlasRuntime);
      if (resumable) {
        const resumeButton = node('button', {
          type: 'button',
          className: 'atlas-primary',
          text: 'Reprendre la séance',
          'data-atlas-resume-session': 'true',
        });
        resumeButton.addEventListener('click', async () => {
          resumeButton.disabled = true;
          preview.replaceChildren(node('p', {role: 'status', text: 'Reprise de la séance…'}));
          try {
            await runAtlasSession({container: preview, context, plan: resumable.plan, existing: resumable, atlasRuntime, onReturn: refresh});
          } catch (error) {
            renderError(preview, error);
            resumeButton.disabled = false;
          }
        });
        actions.append(resumeButton);
      }

      for (const duration of DURATIONS) {
        const button = node('button', {
          type: 'button',
          className: 'atlas-primary',
          text: `${duration} min`,
          'data-atlas-duration': duration,
        });
        button.addEventListener('click', async () => {
          actions.querySelectorAll('button').forEach(item => { item.disabled = true; });
          preview.replaceChildren(node('p', {role: 'status', text: `Préparation de la séance de ${duration} minutes…`}));
          try {
            const result = await buildPreview(context, duration, atlasRuntime);
            const wrapper = node('div');
            wrapper.innerHTML = atlasRuntime.modules.today.renderToday({
              recommendation: result.recommendation,
              plan: result.plan,
              objectiveLabels: learnerObjectiveLabels(context),
            });
            if (result.memory?.dueAt) {
              const readableDueAt = learnerDateTime(result.memory.dueAt);
              wrapper.append(node('p', {
                className: 'help',
                'data-atlas-memory-due': result.memory.dueAt,
                text: result.memory.due
                  ? 'Une reconfirmation est disponible.'
                  : readableDueAt
                    ? `Prochaine reconfirmation à partir du ${readableDueAt}.`
                    : 'Une prochaine reconfirmation sera proposée au bon moment.',
              }));
            }
            const start = wrapper.querySelector('[data-atlas-action="start"]');
            if (!start) throw new Error('ATLAS_START_CONTROL_MISSING');
            start.addEventListener('click', async () => {
              start.disabled = true;
              start.textContent = 'Démarrage…';
              try {
                await runAtlasSession({container: preview, context, plan: result.plan, atlasRuntime, onReturn: refresh});
              } catch (error) {
                renderError(preview, error);
                start.disabled = false;
              }
            });
            preview.replaceChildren(wrapper);
          } catch (error) {
            renderError(preview, error);
          } finally {
            actions.querySelectorAll('button').forEach(item => { item.disabled = false; });
          }
        });
        actions.append(button);
      }

      cards.push(node('article', {
        className: 'course-card atlas-course-card',
        'data-atlas-course-install-id': context.courseInstallId,
      }, [
        node('h3', {text: context.title}),
        node('p', {className: 'course-meta', text: `${context.course.objectives.length} objectif(s) · ${context.course.activities.length} activité(s)`}),
        actions,
        preview,
      ]));
    }
    content.replaceChildren(node('div', {className: 'course-grid'}, cards));
  }

  let refreshQueued = false;
  function queueRefresh() {
    if (root.querySelector('[data-atlas-session-active="true"]') || refreshQueued) return;
    refreshQueued = true;
    queueMicrotask(async () => {
      refreshQueued = false;
      try {
        await refresh();
      } catch (error) {
        renderError(content, error);
      }
    });
  }

  await refresh();
  if (appMain) {
    const observer = new MutationObserver(queueRefresh);
    observer.observe(appMain, {childList: true, subtree: true});
  }
  return Object.freeze({ready: true, durations: DURATIONS, memoryPolicy: 'atlas.memory-policy.v1'});
}

// ATLAS_SESSION_START_WIRED
// ATLAS_M2_MEMORY_PROOF_LOOP_WIRED
