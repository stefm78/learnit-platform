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

    const objectiveRef = Object.freeze({
      courseRef,
      objectiveId: source.objectiveIds[0],
    });

    const activityRef = Object.freeze({
      courseRef,
      activityLineageId: source.activityLineageId,
    });

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

    links.push(Object.freeze({
      objectiveRef,
      activityRef,
      authorIndex,
    }));
  }

  const objectiveRefs = course.objectives.map(objective => Object.freeze({
    courseRef,
    objectiveId: objective.objectiveId,
  }));

  return Object.freeze({
    courseRef,
    contentRevisionRef,
    objectiveRefs,
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

function correctionProvenance(state, objectiveRef, modules) {
  const E = modules.evidence;
  const executions = new Map(
    state.scoredExecutions.map(record => [record.executionId, record]),
  );

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
    .sort((left, right) => (
      left.occurredAt.localeCompare(right.occurredAt)
      || left.eventId.localeCompare(right.eventId)
    ));

  const target = candidates.at(-1);

  if (!target) throw new Error('ATLAS_CORRECTION_TARGET_NOT_FOUND');

  return Object.freeze({
    correctsEventId: target.eventId,
  });
}

async function buildPreview(context, durationMinutes, atlasRuntime) {
  const modules = atlasRuntime.modules;
  const E = modules.evidence;

  const content = buildContentIndex(context, modules);
  const state = await atlasState(modules);

  /*
   * Pre-QA candidate rule:
   * validation claims are NOT declared accepted by INT.
   * Existing practice/correction evidence remains observable.
   */
  const projected = modules.projection.projectObjectiveEvidence(
    state.learningEvents,
    state.scoredExecutions,
    () => false,
  );

  const evidenceByObjective = new Map(
    projected.map(evidence => [
      E.canonicalRefKey(evidence.objectiveRef),
      evidence,
    ]),
  );

  const recommendationRows = content.objectiveRefs.map(objectiveRef => ({
    objectiveRef,
    evidence:
      evidenceByObjective.get(E.canonicalRefKey(objectiveRef))
      ?? emptyEvidence(objectiveRef),
  }));

  const ranked = modules.recommendation.rankRecommendations(
    recommendationRows,
    state.learningEvents,
  );

  const recommendations = ranked.map(row =>
    modules.recommendation.buildRecommendation({
      objectiveRef: row.objectiveRef,
      evidence: row.evidence,
      index: content.index,
      context: {
        hasAcceptedValidation: false,
        maintenanceEligible: false,
      },
    }),
  );

  const itemProvenance = recommendations.map(recommendation => {
    if (recommendation.action === 'correct-practice') {
      return correctionProvenance(
        state,
        recommendation.objectiveRef,
        modules,
      );
    }

    return {};
  });

  const plan = modules.planner.buildPlan({
    engineVersion: 'atlas.m1.v0.3',
    courseRef: content.courseRef,
    contentRevisionRef: content.contentRevisionRef,
    durationMinutes,
    recommendations,
    itemProvenance,
  });

  return Object.freeze({
    recommendation: recommendations[0],
    plan,
  });
}

function renderError(container, error) {
  container.replaceChildren(
    node('div', { className: 'notice notice-error', role: 'alert' }, [
      node('strong', { text: 'Atlas ne peut pas construire cette séance.' }),
      node('p', { text: error?.code ?? error?.message ?? String(error) }),
    ]),
  );
}

export async function attachAtlasPreviewSurface({
  root,
  runtime,
  atlasRuntime,
}) {
  if (!root || !runtime || !atlasRuntime?.ready) {
    throw new Error('ATLAS_SURFACE_DEPENDENCY_MISSING');
  }

  const previous = root.querySelector('[data-atlas-int-surface]');
  if (previous) previous.remove();

  const title = node('h2', {
    id: 'atlas-int-title',
    text: 'Aujourd’hui',
  });

  const content = node('div', {
    'data-atlas-int-content': 'true',
  });

  const surface = node('section', {
    className: 'atlas-m1 atlas-int-surface',
    'aria-labelledby': 'atlas-int-title',
    'data-atlas-int-surface': 'ready',
  }, [
    node('div', { className: 'section-heading' }, [
      node('div', {}, [
        node('p', { className: 'eyebrow', text: 'Atlas M1' }),
        title,
        node('p', {
          text: 'Choisissez le temps dont vous disposez. Atlas prépare la séance utile maintenant.',
        }),
      ]),
    ]),
    content,
  ]);

  const header = root.querySelector('.app-header') ?? root.firstElementChild;

  if (header?.parentNode === root) header.after(surface);
  else root.prepend(surface);

  async function refresh() {
    const courses = await runtime.listCourses();
    const atlasCourses = [];

    for (const course of courses) {
      try {
        const context = await runtime.getAtlasCourseContext(
          course.courseInstallId,
        );

        if (compatibleAtlasCourse(context)) {
          atlasCourses.push(context);
        }
      } catch {
        // Non-Atlas or incomplete local course: leave it to the classic UI.
      }
    }

    if (atlasCourses.length === 0) {
      content.replaceChildren(
        node('div', { className: 'empty-state' }, [
          node('h3', { text: 'Aucun parcours Atlas installé' }),
          node('p', {
            text: 'Importez un kit Atlas M1 dans la bibliothèque Learn-it pour préparer une séance de 5, 15 ou 30 minutes.',
          }),
        ]),
      );
      return;
    }

    const cards = [];

    for (const context of atlasCourses) {
      const preview = node('div', {
        className: 'atlas-int-preview',
        'aria-live': 'polite',
      });

      const actions = node('div', {
        className: 'atlas-actions',
        role: 'group',
        'aria-label': `Durée pour ${context.title}`,
        'data-atlas-planner-actions': 'true',
      });

      const resumable =
        await findResumableAtlasSession(
          context,
          atlasRuntime,
        );

      if (resumable) {
        const resumeButton = node(
          'button',
          {
            type: 'button',
            className: 'atlas-primary',
            text: 'Reprendre la séance',
            'data-atlas-resume-session': 'true',
          },
        );

        resumeButton.addEventListener(
          'click',
          async () => {
            resumeButton.disabled = true;

            preview.replaceChildren(
              node('p', {
                role: 'status',
                text: 'Reprise de la séance…',
              }),
            );

            try {
              await runAtlasSession({
                container: preview,
                context,
                plan: resumable.plan,
                existing: resumable,
                atlasRuntime,
                onReturn: refresh,
              });
            } catch (error) {
              renderError(
                preview,
                error,
              );

              resumeButton.disabled =
                false;
            }
          },
        );

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
          actions.querySelectorAll('button').forEach(item => {
            item.disabled = true;
          });

          preview.replaceChildren(
            node('p', {
              role: 'status',
              text: `Préparation de la séance de ${duration} minutes…`,
            }),
          );

          try {
            const result = await buildPreview(
              context,
              duration,
              atlasRuntime,
            );

            const wrapper = node('div');
            wrapper.innerHTML = atlasRuntime.modules.today.renderToday({
              recommendation: result.recommendation,
              plan: result.plan,
            });

            const start = wrapper.querySelector(
              '[data-atlas-action="start"]',
            );

            if (!start) {
              throw new Error(
                'ATLAS_START_CONTROL_MISSING',
              );
            }

            start.addEventListener(
              'click',
              async () => {
                start.disabled = true;
                start.textContent = 'Démarrage…';

                try {
                  await runAtlasSession({
                    container: preview,
                    context,
                    plan: result.plan,
                    atlasRuntime,
                    onReturn: refresh,
                  });
                } catch (error) {
                  renderError(
                    preview,
                    error,
                  );

                  start.disabled = false;
                }
              },
            );

            wrapper.append(
              node('p', {
                className: 'help',
                text: 'Plan Atlas calculé localement. Commencez lorsque vous êtes prêt.',
              }),
            );

            preview.replaceChildren(wrapper);
          } catch (error) {
            renderError(preview, error);
          } finally {
            actions.querySelectorAll('button').forEach(item => {
              item.disabled = false;
            });
          }
        });

        actions.append(button);
      }

      cards.push(
        node('article', { className: 'course-card atlas-course-card' }, [
          node('h3', { text: context.title }),
          node('p', {
            className: 'course-meta',
            text: `${context.course.objectives.length} objectif(s) · ${context.course.activities.length} activité(s)`,
          }),
          actions,
          preview,
        ]),
      );
    }

    content.replaceChildren(
      node('div', { className: 'course-grid' }, cards),
    );
  }

  let refreshQueued = false;

  function queueRefresh() {
    if (
      root.querySelector(
        '[data-atlas-session-active="true"]',
      )
    ) {
      return;
    }

    if (refreshQueued) return;
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

  const appMain = root.querySelector('.app-main');

  if (appMain) {
    const observer = new MutationObserver(queueRefresh);
    observer.observe(appMain, {
      childList: true,
      subtree: true,
    });
  }

  return Object.freeze({
    ready: true,
    durations: DURATIONS,
  });
}

// ATLAS_SESSION_START_WIRED
