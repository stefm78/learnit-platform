import { evaluateAnswer } from '../../core/session.js';

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

function renderActivity(activity, modules) {
  const esc = modules.today.esc;

  const prompt =
    `<p class="atlas-question"><strong>${
      esc(activity.prompt)
    }</strong></p>`;

  if (activity.type === 'qcm') {
    const choices = activity.choices
      .map(choice => {
        const id =
          `atlas-choice-${choice.choiceId}`;

        return (
          `<label class="choice-row" for="${esc(id)}">`
          + `<input id="${esc(id)}" `
          + 'type="radio" '
          + 'name="atlas-qcm-choice" '
          + `value="${esc(choice.choiceId)}" `
          + 'data-atlas-choice="true">'
          + `<span>${esc(choice.label)}</span>`
          + '</label>'
        );
      })
      .join('');

    return (
      prompt
      + '<fieldset class="answer-fieldset">'
      + '<legend>Choisissez une réponse</legend>'
      + choices
      + '</fieldset>'
    );
  }

  if (activity.type === 'fill') {
    const options = activity.tokens
      .map(token => (
        `<option value="${esc(token.tokenId)}">`
        + `${esc(token.label)}</option>`
      ))
      .join('');

    let slotNumber = 0;

    const sentence = activity.segments
      .map(segment => {
        if (Object.hasOwn(segment, 'text')) {
          return `<span>${esc(segment.text)}</span>`;
        }

        slotNumber += 1;

        return (
          '<label class="atlas-fill-slot">'
          + `<span class="visually-hidden">Réponse ${
            slotNumber
          }</span>`
          + `<select data-atlas-slot="${
            esc(segment.slotId)
          }">`
          + '<option value="">Choisir…</option>'
          + options
          + '</select>'
          + '</label>'
        );
      })
      .join('');

    return (
      prompt
      + '<fieldset class="answer-fieldset">'
      + '<legend>Complétez la phrase</legend>'
      + `<div class="fill-sentence">${sentence}</div>`
      + '</fieldset>'
    );
  }

  throw new Error(
    `ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${activity.type}`,
  );
}

function readResponse(container, activity) {
  if (activity.type === 'qcm') {
    const selected = container.querySelector(
      '[data-atlas-choice="true"]:checked',
    );

    if (!selected) {
      const error = new Error(
        'Choisissez une réponse avant de valider.',
      );

      error.code = 'ATLAS_ANSWER_REQUIRED';
      throw error;
    }

    return { choiceId: selected.value };
  }

  if (activity.type === 'fill') {
    const answer = {};

    const selects = [
      ...container.querySelectorAll(
        '[data-atlas-slot]',
      ),
    ];

    for (const select of selects) {
      if (!select.value) {
        const error = new Error(
          'Complétez toutes les réponses avant de valider.',
        );

        error.code = 'ATLAS_ANSWER_REQUIRED';
        throw error;
      }

      answer[
        select.getAttribute('data-atlas-slot')
      ] = select.value;
    }

    return answer;
  }

  throw new Error(
    `ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${activity.type}`,
  );
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

  const plannerActions =
    atlasCard?.querySelector(
      '[data-atlas-planner-actions="true"]',
    )
    ?? null;

  const plannerActionsDisplay =
    plannerActions?.style.display ?? '';

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

    if (classicMain) {
      classicMain.style.display = classicDisplay;

      if (!classicWasInert) {
        classicMain.removeAttribute('inert');
      }
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
          core.evidence().filter(
            item =>
              modules.today.sameCanonical(
                item.objectiveRef.courseRef,
                activePlan.payload.courseRef,
              ),
          );

        const wrapper = node('div');

        wrapper.innerHTML =
          modules.summary.renderSummary({
            evidence,
            completed: true,
          });

        if (previousFeedback) {
          const feedback = node('div');
          feedback.innerHTML =
            previousFeedback;

          wrapper.prepend(
            ...feedback.childNodes,
          );
        }

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

      const activity =
        sourceActivity(
          context,
          item.activityRef,
        );

      const wrapper = node('div');

      wrapper.innerHTML =
        modules.session.renderSession({
          plan: activePlan,
          resumeState: checkpoint,
          activityHtml:
            renderActivity(
              activity,
              modules,
            ),
          feedbackHtml: previousFeedback,
        });

      container.replaceChildren(wrapper);

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
       * EXPERIENCE normally provides the hint control.
       * INT normalizes it and creates it defensively if absent.
       */
      let help =
        wrapper.querySelector(
          '[data-atlas-help="hint"]',
        );

      if (!help) {
        help = node(
          'button',
          {
            type: 'button',
            className: 'secondary',
            text: 'Indice',
            'data-atlas-help': 'hint',
          },
        );
      }

      help.classList.add('secondary');

      help.setAttribute(
        'data-atlas-control',
        'hint',
      );

      submit.setAttribute(
        'data-atlas-control',
        'submit',
      );

      if (help.parentElement !== sessionActions) {
        sessionActions.insertBefore(
          help,
          submit,
        );
      }

      help.addEventListener(
        'click',
        async () => {
          help.disabled = true;

          try {
            await controller.requestHelp(
              'hint',
            );

            wrapper.querySelector(
              '[data-atlas-help-status]',
            )?.remove();

            const guidance =
              activity.type === 'qcm'
                ? 'Relisez la règle demandée puis éliminez les propositions incompatibles.'
                : 'Repérez la forme attendue dans la phrase avant de choisir chaque élément.';

            wrapper.querySelector(
              '.atlas-activity',
            )?.append(
              node(
                'p',
                {
                  className: 'help',
                  role: 'status',
                  'data-atlas-help-status':
                    'true',
                  text: guidance,
                },
              ),
            );
          } catch (error) {
            showError(
              container,
              error,
            );
          } finally {
            help.disabled = false;
          }
        },
      );

      submit.addEventListener(
        'click',
        async () => {
          submit.disabled = true;

          try {
            const rawResponse =
              readResponse(
                wrapper,
                activity,
              );

            const result =
              await controller.submit(
                rawResponse,
              );

            await renderCurrent(
              feedbackHtml(
                result,
                activity,
                modules,
              ),
            );
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

      assertAtlasControlVisible(
        help,
        'hint',
      );

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
