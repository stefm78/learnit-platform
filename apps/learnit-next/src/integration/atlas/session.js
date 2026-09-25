import { evaluateAnswer } from '../../core/session.js';
import {
  readAtlasActivityResponse,
  renderAtlasActivityMarkup,
} from '../../ui/render.js';
import { renderEmbeddedMediaSet } from '../../ui/media.js';
import {
  projectActivityPresentation,
  projectFeedbackMedia,
} from './activity_projection.js';

const V5_CONTRACT = 'learnit.kit.v5';
const V5_HINT_INFLIGHT = new Set();

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
    element.append(
      child instanceof Node
        ? child
        : document.createTextNode(String(child)),
    );
  }

  return element;
}

function courseRef(context) {
  return Object.freeze({
    packageLineageId: context.packageLineageId,
    courseLineageId: context.course.courseLineageId,
  });
}

function contentRevisionRef(context) {
  return Object.freeze({
    packageLineageId: context.packageLineageId,
    packageRevisionId: context.packageRevisionId,
    packageDigest: context.packageDigest,
  });
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

function sourceActivity(context, reference) {
  const activity = context.course.activities.find(
    item => (
      item.activityLineageId
      === reference.activityLineageId
    ),
  );

  if (!activity) {
    throw new Error(
      `ATLAS_ACTIVITY_NOT_FOUND: ${reference.activityLineageId}`,
    );
  }

  return activity;
}

export function projectAtlasActivityPresentation(
  activity,
  { assets = [], contract = null } = {},
) {
  if (contract === V5_CONTRACT) {
    return projectActivityPresentation(
      activity,
      { assets, contract },
    );
  }

  if (activity.type === 'qcm') {
    return Object.freeze({
      type: activity.type,
      prompt: activity.prompt,
      choices: Object.freeze(
        activity.choices.map(choice => Object.freeze({
          choiceId: choice.choiceId,
          label: choice.label,
        })),
      ),
    });
  }

  if (activity.type === 'fill') {
    return Object.freeze({
      type: activity.type,
      prompt: activity.prompt,
      tokens: Object.freeze(
        activity.tokens.map(token => Object.freeze({
          tokenId: token.tokenId,
          label: token.label,
        })),
      ),
      segments: Object.freeze(
        activity.segments.map(segment => (
          Object.hasOwn(segment, 'text')
            ? Object.freeze({ text: segment.text })
            : Object.freeze({ slotId: segment.slotId })
        )),
      ),
    });
  }

  throw new Error(
    `ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${activity.type}`,
  );
}

function scoringAnswer(activity) {
  if (activity.type === 'qcm') {
    return activity.correctChoiceId;
  }

  if (activity.type === 'fill') {
    return structuredClone(activity.answers);
  }

  throw new Error(
    `ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${activity.type}`,
  );
}

function createRegistry(context) {
  const activities = new Map(
    context.course.activities.map(activity => [
      activity.activityLineageId,
      activity,
    ]),
  );

  return Object.freeze({
    activity(reference) {
      const source = activities.get(
        reference?.activityLineageId,
      );

      if (!source) return null;

      if (!['qcm', 'fill'].includes(source.type)) {
        throw new Error(
          `ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${source.type}`,
        );
      }

      return Object.freeze({
        type: source.type,

        /*
         * Learn-it remains the answer-evaluation authority.
         * Atlas consumes only the resulting boolean outcome.
         */
        scoringRuleId:
          `learnit.kit.v2.${source.type}.v1`,

        answer: scoringAnswer(source),

        score(rawResponse) {
          return evaluateAnswer(
            source,
            rawResponse,
          ).correct;
        },
      });
    },

    /*
     * Pre-QA INT must never self-authorize
     * validation-independence claims.
     */
    validateClaim() {
      return false;
    },
  });
}

function feedbackHtml(result, activity, modules) {
  const correct =
    result.execution.outcome === 'correct';

  const esc = modules.today.esc;

  return (
    `<div class="notice ${
      correct
        ? 'notice-success'
        : 'notice-error'
    }" role="status">`
    + `<strong>${
      correct
        ? 'Bonne réponse.'
        : 'À reprendre.'
    }</strong>`
    + (
      activity.explanation
        ? `<p>${esc(activity.explanation)}</p>`
        : ''
    )
    + '</div>'
  );
}

function nextAtlasPaint() {
  return new Promise(resolve => {
    requestAnimationFrame(() => {
      requestAnimationFrame(resolve);
    });
  });
}

async function showFeedbackTransition(
  container,
  activityWrapper,
  sessionActions,
  feedbackMarkup,
  onContinue,
  nextLabel = 'Activité suivante',
  feedbackMedia = [],
) {
  /*
   * Keep activity N visible while its own feedback is read.
   * The scored response becomes read-only and activity N+1
   * is not rendered until the learner explicitly continues.
   */
  container.querySelector(
    '[data-atlas-session-error]',
  )?.remove();

  activityWrapper
    .querySelectorAll('input, select')
    .forEach(control => {
      control.disabled = true;
    });

  activityWrapper.querySelector(
    '[data-atlas-help-status]',
  )?.remove();

  sessionActions.remove();

  const transition = node(
    'div',
    {
      className: 'atlas-feedback-transition',
      'data-atlas-feedback-transition': 'true',
    },
  );

  const feedback = node('div');
  feedback.innerHTML = feedbackMarkup;
  transition.append(...feedback.childNodes);

  if (Array.isArray(feedbackMedia) && feedbackMedia.length) {
    const mediaRegion = node(
      'div',
      {
        className: 'activity-feedback-media',
        'data-activity-feedback-media': 'post-transition',
      },
    );
    mediaRegion.append(renderEmbeddedMediaSet(feedbackMedia));
    transition.append(mediaRegion);
  }

  const next = node(
    'button',
    {
      type: 'button',
      className: 'atlas-primary',
      text: nextLabel,
      'data-atlas-feedback-next': 'true',
    },
  );

  next.addEventListener(
    'click',
    async () => {
      next.disabled = true;

      try {
        await onContinue();
      } catch (error) {
        showError(container, error);
        next.disabled = false;
      }
    },
  );

  transition.append(
    node(
      'div',
      { className: 'atlas-actions' },
      [next],
    ),
  );

  activityWrapper.append(transition);

  await nextAtlasPaint();
  assertAtlasControlVisible(
    next,
    'feedback-next',
  );
  next.focus();
}

function assertAtlasControlVisible(control, name) {
  if (!(control instanceof HTMLElement)) {
    throw new Error(
      `ATLAS_SESSION_CONTROL_MISSING:${name}`,
    );
  }

  const style = getComputedStyle(control);
  const rect = control.getBoundingClientRect();

  if (
    style.display === 'none'
    || style.visibility === 'hidden'
    || Number(style.opacity) === 0
    || rect.width < 1
    || rect.height < 1
    || control.getClientRects().length === 0
  ) {
    throw new Error(
      `ATLAS_SESSION_CONTROL_NOT_VISIBLE:${name}`
      + `:display=${style.display}`
      + `:visibility=${style.visibility}`
      + `:opacity=${style.opacity}`
      + `:width=${rect.width}`
      + `:height=${rect.height}`,
    );
  }

  return control;
}

function showError(container, error) {
  container.querySelector(
    '[data-atlas-session-error]',
  )?.remove();

  const notice = node(
    'div',
    {
      className: 'notice notice-error',
      role: 'alert',
      'data-atlas-session-error': 'true',
    },
    [
      node('strong', {
        text:
          'La réponse n’a pas été enregistrée.',
      }),
      node('p', {
        text:
          error?.message
          ?? error?.code
          ?? String(error),
      }),
    ],
  );

  container.prepend(notice);
}

function resumeState(storage, sessionId) {
  return storage.snapshot().resumeStates.find(
    state => (
      state.sessionRef.sessionId === sessionId
    ),
  ) ?? null;
}

function lifecycleEvents(storage, sessionId) {
  return storage.snapshot().learningEvents
    .filter(event => (
      event.sessionRef?.sessionId === sessionId
      && [
        'session-interrupted',
        'session-resumed',
        'session-completed',
      ].includes(event.kind)
    ))
    .sort(
      (left, right) =>
        left.eventOrdinal - right.eventOrdinal,
    );
}

function eventForExecution(state, executionId) {
  return state.learningEvents.find(event => (
    event.kind === 'activity-attempt'
    && event.executionId === executionId
  )) ?? null;
}

function claimDetailsForExecution(
  state,
  execution,
  modules,
) {
  const session =
    state.atlasMeta.sessions[
      execution.sessionRef.sessionId
    ];

  const planItem =
    session?.plan?.payload?.items?.[
      execution.itemPosition
    ];

  if (
    !planItem
    || ![
      'attempt-validation',
      'maintain-recent-validation',
    ].includes(planItem.action)
  ) {
    return null;
  }

  const sourceEvent =
    state.learningEvents.find(
      event =>
        event.eventId
        === planItem.validationBasisEventId,
    );

  const sourceExecution =
    sourceEvent
      ? state.scoredExecutions.find(
        item =>
          item.executionId
          === sourceEvent.executionId,
      )
      : null;

  if (!sourceEvent || !sourceExecution) {
    return null;
  }

  const details = {
    objectiveRef: execution.objectiveRef,
    sourceActivityRef:
      sourceExecution.activityRef,
    targetActivityRef: execution.activityRef,
    sourceEvent,
    sourceExecution,
    targetExecution: execution,
    contentRevisionRef:
      execution.contentRevisionRef,
    independenceClaimId:
      planItem.independenceClaimId,
  };

  return modules.claimAuthority
    .validateRuntimeClaim(
      planItem,
      details,
    )
    ? Object.freeze({
      planItem,
      sourceEvent,
      sourceExecution,
    })
    : null;
}

function admissibleValidationIds(state, modules) {
  const result = new Set();

  for (const execution of state.scoredExecutions) {
    if (execution.executionClass !== 'validation') {
      continue;
    }

    if (
      claimDetailsForExecution(
        state,
        execution,
        modules,
      )
    ) {
      result.add(execution.executionId);
    }
  }

  return result;
}

function projectCourseEvidence(
  storage,
  expectedCourseRef,
  modules,
) {
  const state = storage.snapshot();
  const admissibleIds =
    admissibleValidationIds(state, modules);

  return modules.projection
    .projectObjectiveEvidence(
      state.learningEvents,
      state.scoredExecutions,
      execution =>
        admissibleIds.has(execution.executionId),
    )
    .filter(item =>
      modules.today.sameCanonical(
        item.objectiveRef.courseRef,
        expectedCourseRef,
      ));
}


export function reconstructAtlasHintPrefix(
  state,
  {
    sessionRef,
    itemPosition,
    contentRevisionRef: expectedContentRevisionRef,
    hints,
  },
  sameCanonical = (left, right) => (
    JSON.stringify(left) === JSON.stringify(right)
  ),
) {
  if (!state || !Array.isArray(state.resumeStates)) {
    throw new Error('ATLAS_V5_ASSISTANCE_STATE_UNAVAILABLE');
  }
  if (!Array.isArray(hints)) {
    throw new Error('ATLAS_V5_HINTS_UNAVAILABLE');
  }

  const checkpoint = state.resumeStates.find(candidate => (
    candidate.sessionRef?.sessionId === sessionRef?.sessionId
  ));

  if (
    !checkpoint
    || !sameCanonical(checkpoint.sessionRef, sessionRef)
    || !sameCanonical(
      checkpoint.contentRevisionRef,
      expectedContentRevisionRef,
    )
  ) {
    throw new Error('ATLAS_V5_CONTENT_REVISION_MISMATCH');
  }

  const itemState = checkpoint.itemStates?.find(candidate => (
    candidate.itemPosition === itemPosition
  ));

  if (!itemState || !Array.isArray(itemState.assistanceUseIds)) {
    throw new Error('ATLAS_V5_ASSISTANCE_RESUME_STATE_MISSING');
  }

  const assistanceUses = state.atlasMeta?.assistanceUses;
  if (!assistanceUses || typeof assistanceUses !== 'object') {
    throw new Error('ATLAS_V5_ASSISTANCE_HISTORY_MISSING');
  }

  const resumeIds = new Set(itemState.assistanceUseIds);
  const records = itemState.assistanceUseIds.map(identifier => {
    const record = assistanceUses[identifier];
    if (
      !record
      || record.assistanceUseId !== identifier
      || record.itemPosition !== itemPosition
      || !sameCanonical(record.sessionRef, sessionRef)
    ) {
      throw new Error('ATLAS_V5_ASSISTANCE_HISTORY_MISMATCH');
    }
    return record;
  });

  for (const [identifier, record] of Object.entries(assistanceUses)) {
    if (
      record?.itemPosition === itemPosition
      && sameCanonical(record.sessionRef, sessionRef)
      && !resumeIds.has(identifier)
    ) {
      throw new Error('ATLAS_V5_ASSISTANCE_HISTORY_MISMATCH');
    }
  }

  const hintRecords = records.filter(record => (
    record.assistanceKind === 'hint'
  ));

  if (hintRecords.length > hints.length) {
    throw new Error('ATLAS_V5_HINT_HISTORY_EXCEEDS_CONTENT');
  }

  return Object.freeze({
    count: hintRecords.length,
    revealed: Object.freeze(
      hints.slice(0, hintRecords.length),
    ),
    assistanceUseIds: Object.freeze(
      hintRecords.map(record => record.assistanceUseId),
    ),
  });
}

export async function requestNextAtlasV5Hint({
  readState,
  requestHelp,
  sessionRef,
  itemPosition,
  contentRevisionRef: expectedContentRevisionRef,
  hints,
  sameCanonical,
}) {
  if (
    typeof readState !== 'function'
    || typeof requestHelp !== 'function'
  ) {
    throw new TypeError('ATLAS_V5_HINT_PORT_REQUIRED');
  }

  const key = `${sessionRef?.sessionId ?? 'unknown'}:${itemPosition}`;
  if (V5_HINT_INFLIGHT.has(key)) {
    return Object.freeze({ status: 'in-flight' });
  }

  V5_HINT_INFLIGHT.add(key);
  try {
    const before = reconstructAtlasHintPrefix(
      readState(),
      {
        sessionRef,
        itemPosition,
        contentRevisionRef: expectedContentRevisionRef,
        hints,
      },
      sameCanonical,
    );

    if (before.count >= hints.length) {
      return Object.freeze({
        status: 'exhausted',
        prefix: before,
      });
    }

    const confirmation = await requestHelp('hint');
    if (
      confirmation?.committed !== true
      || confirmation.record?.assistanceKind !== 'hint'
      || typeof confirmation.record?.assistanceUseId !== 'string'
    ) {
      throw new Error('ATLAS_V5_HINT_PERSISTENCE_NOT_CONFIRMED');
    }

    const after = reconstructAtlasHintPrefix(
      readState(),
      {
        sessionRef,
        itemPosition,
        contentRevisionRef: expectedContentRevisionRef,
        hints,
      },
      sameCanonical,
    );

    if (
      after.count !== before.count + 1
      || !after.assistanceUseIds.includes(
        confirmation.record.assistanceUseId,
      )
    ) {
      throw new Error('ATLAS_V5_HINT_PERSISTENCE_NOT_CONFIRMED');
    }

    const index = after.count - 1;
    return Object.freeze({
      status: 'revealed',
      index,
      text: hints[index],
      prefix: after,
    });
  } finally {
    V5_HINT_INFLIGHT.delete(key);
  }
}

function assertV5PinnedContentRevision(
  context,
  activePlan,
  checkpoint,
  sameCanonical,
) {
  if (context.contract !== V5_CONTRACT) return;

  const expected = contentRevisionRef(context);
  if (
    !sameCanonical(
      activePlan?.payload?.contentRevisionRef,
      expected,
    )
    || !sameCanonical(
      checkpoint?.contentRevisionRef,
      expected,
    )
  ) {
    throw new Error('ATLAS_V5_CONTENT_REVISION_MISMATCH');
  }
}

function appendV5Hint(wrapper, text, index) {
  const rank = index + 1;
  const target =
    wrapper.querySelector('.activity-presentation')
    ?? wrapper.querySelector('.atlas-activity');
  if (!target) {
    throw new Error('ATLAS_V5_HINT_TARGET_MISSING');
  }
  let region = target.querySelector('[data-atlas-v8-hints]');
  if (!region) {
    region = node(
      'section',
      {
        className: 'activity-hints',
        'aria-label': 'Indices révélés',
        'data-atlas-v8-hints': 'committed-only',
      },
    );
    target.append(region);
  }
  if (region.querySelector(
    '[data-atlas-hint-rank="' + rank + '"]',
  )) {
    return;
  }
  region.append(
    node(
      'p',
      {
        className: 'help activity-hint',
        role: 'status',
        'data-atlas-help-status': 'true',
        'data-atlas-hint-rank': String(rank),
        text,
      },
    ),
  );
}

export async function findResumableAtlasSession(
  context,
  atlasRuntime,
) {
  const modules = atlasRuntime.modules;

  const storage =
    await modules.indexedDb
      .IndexedDbAtlasStorage.open();

  try {
    const state = storage.snapshot();

    const expectedCourseRef =
      courseRef(context);

    const expectedRevisionRef =
      contentRevisionRef(context);

    const completed = new Set(
      state.learningEvents
        .filter(
          event =>
            event.kind === 'session-completed',
        )
        .map(
          event =>
            event.sessionRef.sessionId,
        ),
    );

    const candidates = state.resumeStates
      .filter(checkpoint => {
        const sessionId =
          checkpoint.sessionRef.sessionId;

        const session =
          state.atlasMeta.sessions[sessionId];

        return Boolean(
          session
          && !completed.has(sessionId)
          && modules.today.sameCanonical(
            checkpoint.courseRef,
            expectedCourseRef,
          )
          && modules.today.sameCanonical(
            checkpoint.contentRevisionRef,
            expectedRevisionRef,
          )
        );
      });

    const checkpoint = candidates.at(-1);

    if (!checkpoint) return null;

    const session =
      state.atlasMeta.sessions[
        checkpoint.sessionRef.sessionId
      ];

    return Object.freeze({
      sessionRef:
        structuredClone(session.sessionRef),

      plan:
        structuredClone(session.plan),

      resumeState:
        structuredClone(checkpoint),
    });
  } finally {
    storage.close();
  }
}

export async function runAtlasSession({
  container,
  context,
  plan,
  atlasRuntime,
  existing = null,
  onReturn,
}) {
  const modules = atlasRuntime.modules;

  /*
   * While an Atlas session is active, Atlas owns the learner
   * interaction surface. The classic Learn-it session remains
   * intact but hidden.
   */
  const classicMain = document.querySelector(
    '[data-learnit-next-app] .app-main',
  );

  const classicDisplay =
    classicMain?.style.display ?? '';

  const classicWasInert =
    classicMain?.hasAttribute('inert') ?? false;

  const atlasCard =
    container.closest('.atlas-course-card');

  const atlasSurface =
    atlasCard?.closest('[data-atlas-int-surface]')
    ?? null;

  const surfaceHeading =
    atlasSurface?.querySelector('.section-heading')
    ?? null;

  const otherAtlasCards =
    atlasSurface
      ? [...atlasSurface.querySelectorAll('.atlas-course-card')]
        .filter(card => card !== atlasCard)
      : [];

  const courseTitle =
    atlasCard?.querySelector('h3')
    ?? null;

  const courseMeta =
    atlasCard?.querySelector('.course-meta')
    ?? null;

  const surfaceHeadingDisplay =
    surfaceHeading?.style.display ?? '';

  const courseTitleDisplay =
    courseTitle?.style.display ?? '';

  const courseMetaDisplay =
    courseMeta?.style.display ?? '';

  const otherAtlasCardDisplays =
    new Map(
      otherAtlasCards.map(card => [
        card,
        card.style.display,
      ]),
    );

  const plannerActions =
    atlasCard?.querySelector(
      '[data-atlas-planner-actions="true"]',
    )
    ?? null;

  const plannerActionsDisplay =
    plannerActions?.style.display ?? '';

  atlasCard?.setAttribute(
    'data-atlas-r13-session-owned',
    'true',
  );

  container.setAttribute(
    'data-atlas-session-active',
    'true',
  );

  if (classicMain) {
    /*
     * Do not rely on the HTML hidden attribute here:
     * Learn-it's author stylesheet declares
     * .app-main { display: grid }, which can win over
     * the browser's default [hidden] presentation rule.
     */
    classicMain.style.display = 'none';
    classicMain.setAttribute('inert', '');
  }

  if (surfaceHeading) {
    surfaceHeading.style.display = 'none';
  }

  if (courseTitle) {
    courseTitle.style.display = 'none';
  }

  if (courseMeta) {
    courseMeta.style.display = 'none';
  }

  for (const card of otherAtlasCards) {
    card.style.display = 'none';
  }

  if (plannerActions) {
    /*
     * A frozen Atlas plan owns the active session.
     * Duration controls must not offer replanning while it runs.
     */
    plannerActions.style.display = 'none';
  }

  function releaseAtlasSurface() {
    container.removeAttribute(
      'data-atlas-session-active',
    );

    atlasCard?.removeAttribute(
      'data-atlas-r13-session-owned',
    );

    if (classicMain) {
      classicMain.style.display = classicDisplay;

      if (!classicWasInert) {
        classicMain.removeAttribute('inert');
      }
    }

    if (surfaceHeading) {
      surfaceHeading.style.display =
        surfaceHeadingDisplay;
    }

    if (courseTitle) {
      courseTitle.style.display =
        courseTitleDisplay;
    }

    if (courseMeta) {
      courseMeta.style.display =
        courseMetaDisplay;
    }

    for (const [card, display] of otherAtlasCardDisplays) {
      card.style.display = display;
    }

    if (plannerActions) {
      plannerActions.style.display =
        plannerActionsDisplay;
    }
  }


  const storage =
    await modules.indexedDb
      .IndexedDbAtlasStorage.open();

  let storageClosed = false;

  function closeStorage() {
    if (storageClosed) return;
    storageClosed = true;
    storage.close();
  }

  const clock = Object.freeze({
    now() {
      return new Date().toISOString();
    },
  });

  const core =
    new modules.indexedDb.IndexedDbAtlasCoreService({
      storage,
      clock,
      registry: createRegistry(context),
    });

  const activePlan =
    existing?.plan ?? plan;

  let sessionRef;

  try {
    if (existing) {
      sessionRef = existing.sessionRef;

      const previous =
        lifecycleEvents(
          storage,
          sessionRef.sessionId,
        ).at(-1);

      if (
        previous?.kind
        === 'session-completed'
      ) {
        throw new Error(
          'ATLAS_SESSION_ALREADY_COMPLETED',
        );
      }

      if (
        previous?.kind
        === 'session-interrupted'
      ) {
        await core.lifecycle(
          sessionRef.sessionId,
          'session-resumed',
        );
      }
    } else {
      const request =
        await core.prepareStartRequest(
          activePlan.planDigest,
        );

      sessionRef =
        await core.startSession(
          request.startRequestId,
          activePlan,
        );
    }

    let checkpoint =
      resumeState(
        storage,
        sessionRef.sessionId,
      );

    if (!checkpoint) {
      throw new Error(
        'ATLAS_RESUME_STATE_NOT_FOUND',
      );
    }

    const controller =
      modules.session.createSessionController({
        core,
        plan: activePlan,

        focus(target) {
          requestAnimationFrame(() => {
            const element =
              document.getElementById(target);

            if (!element) return;

            if (!element.hasAttribute('tabindex')) {
              element.setAttribute(
                'tabindex',
                '-1',
              );
            }

            element.focus();
          });
        },
      });

    controller.start(
      sessionRef,
      checkpoint,
      activePlan,
    );

    async function renderCurrent(
      previousFeedback = '',
    ) {
      checkpoint =
        resumeState(
          storage,
          sessionRef.sessionId,
        );

      if (!checkpoint) {
        throw new Error(
          'ATLAS_RESUME_STATE_NOT_FOUND',
        );
      }

      if (
        checkpoint.nextItemPosition
        >= activePlan.payload.items.length
      ) {
        const last =
          lifecycleEvents(
            storage,
            sessionRef.sessionId,
          ).at(-1);

        if (
          last?.kind
          !== 'session-completed'
        ) {
          await core.lifecycle(
            sessionRef.sessionId,
            'session-completed',
          );
        }

        const evidence =
          projectCourseEvidence(
            storage,
            activePlan.payload.courseRef,
            modules,
          );

        const wrapper = node('div');

        wrapper.innerHTML =
          modules.summary.renderSummary({
            evidence,
            completed: true,
            objectiveLabels:
              learnerObjectiveLabels(context),
          });

        if (previousFeedback) {
          const feedback = node('div');
          feedback.innerHTML =
            previousFeedback;

          wrapper.prepend(
            ...feedback.childNodes,
          );
        }

        wrapper.prepend(
          node('p', {
            className: 'eyebrow',
            text: context.title,
          }),
        );

        const back = node(
          'button',
          {
            type: 'button',
            className: 'atlas-primary',
            text: 'Retour à Aujourd’hui',
          },
        );

        back.addEventListener(
          'click',
          async () => {
            closeStorage();
            releaseAtlasSurface();
            await onReturn?.();
          },
        );

        wrapper.append(
          node(
            'div',
            { className: 'atlas-actions' },
            [back],
          ),
        );

        container.replaceChildren(wrapper);
        closeStorage();

        return;
      }

      const item =
        activePlan.payload.items[
          checkpoint.nextItemPosition
        ];

      assertV5PinnedContentRevision(
        context,
        activePlan,
        checkpoint,
        modules.today.sameCanonical,
      );

      const activity =
        sourceActivity(
          context,
          item.activityRef,
        );

      const activityPresentation =
        projectAtlasActivityPresentation(
          activity,
          {
            assets: context.packageAssets ?? [],
            contract: context.contract ?? null,
          },
        );

      const wrapper = node('div');

      wrapper.innerHTML =
        modules.session.renderSession({
          plan: activePlan,
          resumeState: checkpoint,
          activityHtml:
            renderAtlasActivityMarkup(activityPresentation),
          feedbackHtml: previousFeedback,
        });

      const objectiveLabel =
        learnerObjectiveLabels(context)[
          item.objectiveRef.objectiveId
        ] ?? 'Objectif courant';

      const sessionHeader =
        wrapper.querySelector(
          '.atlas-session > header',
        );

      if (sessionHeader) {
        sessionHeader.replaceChildren(
          node('p', {
            className: 'eyebrow',
            text: context.title,
          }),
          node('p', {
            className: 'atlas-session-objective',
            text: `Objectif : ${objectiveLabel}`,
          }),
          node('h1', {
            id: 'atlas-session-title',
            text:
              `Étape ${item.position + 1} `
              + `sur ${activePlan.payload.items.length}`,
          }),
        );
      }

      container.replaceChildren(wrapper);

      let v5HintPrefix = null;
      const authoredV5Hints =
        context.contract === V5_CONTRACT
        && Array.isArray(activity.hints)
        && activity.hints.length > 0
          ? Object.freeze([...activity.hints])
          : null;

      if (authoredV5Hints) {
        v5HintPrefix = reconstructAtlasHintPrefix(
          storage.snapshot(),
          {
            sessionRef,
            itemPosition: item.position,
            contentRevisionRef:
              contentRevisionRef(context),
            hints: authoredV5Hints,
          },
          modules.today.sameCanonical,
        );

        v5HintPrefix.revealed.forEach(
          (text, index) => {
            appendV5Hint(wrapper, text, index);
          },
        );
      }

      const submit =
        wrapper.querySelector(
          '[data-atlas-submit]',
        );

      if (!submit) {
        throw new Error(
          'ATLAS_SUBMIT_CONTROL_MISSING',
        );
      }

      /*
       * Anchor the session actions on the known submit control,
       * never on the first generic .atlas-actions in the card.
       */
      let sessionActions =
        submit.closest('.atlas-actions');

      if (!sessionActions) {
        sessionActions = node(
          'div',
          {
            className:
              'atlas-actions atlas-runtime-session-actions',
            'data-atlas-session-actions':
              'true',
          },
        );

        submit.replaceWith(sessionActions);
        sessionActions.append(submit);
      } else {
        sessionActions.classList.add(
          'atlas-runtime-session-actions',
        );

        sessionActions.setAttribute(
          'data-atlas-session-actions',
          'true',
        );
      }

      /*
       * Handoff 3 is the sole V5 hint authority. Handoff 4 exposes a
       * control only when that qualified capability exists for this item.
       * The presenter never receives unrevealed hint text.
       */
      let help = null;

      submit.setAttribute(
        'data-atlas-control',
        'submit',
      );

      if (authoredV5Hints) {
        help =
          wrapper.querySelector(
            '[data-atlas-help="hint"]',
          )
          ?? node(
            'button',
            {
              type: 'button',
              className: 'secondary',
              text: 'Indice',
              'data-atlas-help': 'hint',
            },
          );

        help.classList.add('secondary');
        help.setAttribute(
          'data-atlas-control',
          'hint',
        );

        if (help.parentElement !== sessionActions) {
          sessionActions.insertBefore(
            help,
            submit,
          );
        }

        help.disabled =
          v5HintPrefix.count >= authoredV5Hints.length;

        help.addEventListener(
          'click',
          async () => {
            help.disabled = true;

            try {
              const result =
                await requestNextAtlasV5Hint({
                  readState: () => storage.snapshot(),
                  requestHelp: kind =>
                    controller.requestHelp(kind),
                  sessionRef,
                  itemPosition: item.position,
                  contentRevisionRef:
                    contentRevisionRef(context),
                  hints: authoredV5Hints,
                  sameCanonical:
                    modules.today.sameCanonical,
                });

              if (result.status === 'revealed') {
                appendV5Hint(
                  wrapper,
                  result.text,
                  result.index,
                );
              }

              const current =
                reconstructAtlasHintPrefix(
                  storage.snapshot(),
                  {
                    sessionRef,
                    itemPosition: item.position,
                    contentRevisionRef:
                      contentRevisionRef(context),
                    hints: authoredV5Hints,
                  },
                  modules.today.sameCanonical,
                );

              help.disabled =
                current.count >= authoredV5Hints.length;
            } catch (error) {
              showError(
                container,
                error,
              );
              help.disabled = false;
            }
          },
        );
      }

      submit.addEventListener(
        'click',
        async () => {
          submit.disabled = true;

          try {
            const rawResponse =
              readAtlasActivityResponse(wrapper, activityPresentation);

            const result =
              await controller.submit(
                rawResponse,
              );

            const outcomeFeedback =
              feedbackHtml(
                result,
                activity,
                modules,
              );

            const outcomeFeedbackMedia =
              context.contract === V5_CONTRACT
                ? projectFeedbackMedia(
                  activity,
                  {
                    assets: context.packageAssets ?? [],
                    contract: context.contract,
                    transitionAuthorized: true,
                  },
                )
                : Object.freeze([]);

            const nextCheckpoint =
              resumeState(
                storage,
                sessionRef.sessionId,
              );

            if (!nextCheckpoint) {
              throw new Error(
                'ATLAS_RESUME_STATE_NOT_FOUND',
              );
            }

            if (
              nextCheckpoint.nextItemPosition
              >= activePlan.payload.items.length
            ) {
              const lastLifecycle =
                lifecycleEvents(
                  storage,
                  sessionRef.sessionId,
                ).at(-1);

              if (
                lastLifecycle?.kind
                !== 'session-completed'
              ) {
                await core.lifecycle(
                  sessionRef.sessionId,
                  'session-completed',
                );
              }

              await showFeedbackTransition(
                container,
                wrapper,
                sessionActions,
                outcomeFeedback,
                async () => {
                  await renderCurrent();
                },
                'Voir le bilan',
                outcomeFeedbackMedia,
              );
            } else {
              await showFeedbackTransition(
                container,
                wrapper,
                sessionActions,
                outcomeFeedback,
                async () => {
                  await renderCurrent();
                },
                'Activité suivante',
                outcomeFeedbackMedia,
              );
            }
          } catch (error) {
            showError(
              container,
              error,
            );

            submit.disabled = false;
          }
        },
      );

      const pause = node(
        'button',
        {
          type: 'button',
          className: 'secondary',
          text:
            'Quitter et reprendre plus tard',
          'data-atlas-pause-session':
            'true',
          'data-atlas-control':
            'pause',
        },
      );

      pause.addEventListener(
        'click',
        async () => {
          pause.disabled = true;

          try {
            await core.lifecycle(
              sessionRef.sessionId,
              'session-interrupted',
            );

            closeStorage();
            releaseAtlasSurface();
            await onReturn?.();
          } catch (error) {
            showError(
              container,
              error,
            );

            pause.disabled = false;
          }
        },
      );

      sessionActions.append(pause);

      /*
       * Fail closed on the actual rendered layout.
       * Markup presence alone is not sufficient.
       */
      await nextAtlasPaint();

      if (help) {
        assertAtlasControlVisible(
          help,
          'hint',
        );
      }

      assertAtlasControlVisible(
        submit,
        'submit',
      );

      assertAtlasControlVisible(
        pause,
        'pause',
      );

    }

    await renderCurrent();
  } catch (error) {
    closeStorage();
    releaseAtlasSurface();
    throw error;
  }
}
