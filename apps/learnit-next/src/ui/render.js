function node(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === 'className') element.className = value;
    else if (name === 'text') element.textContent = value;
    else if (name === 'disabled') element.disabled = Boolean(value);
    else if (name === 'checked') element.checked = Boolean(value);
    else if (name === 'value') element.value = value;
    else if (name.startsWith('on') && typeof value === 'function') element.addEventListener(name.slice(2).toLowerCase(), value);
    else if (value !== undefined && value !== null) element.setAttribute(name, String(value));
  }
  const normalized = Array.isArray(children) ? children : [children];
  for (const child of normalized) {
    if (child === null || child === undefined) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}

function errorMessages(error) {
  const summary = error?.message ?? 'Une erreur inattendue est survenue.';
  if (error?.code === 'ERR_LEGACY') return [summary];
  if (Array.isArray(error?.errors) && error.errors.length) {
    return [summary, ...error.errors.map((entry) => `${entry.path}: ${entry.message}`)];
  }
  return [summary];
}

function renderNotice(messages, type = 'error') {
  const items = messages.map((message) => node('li', { text: message }));
  return node('div', {
    className: `notice notice-${type}`,
    role: type === 'error' ? 'alert' : 'status',
    'aria-live': 'polite',
    'aria-atomic': 'true',
  }, [node('ul', {}, items)]);
}

function renderProgress(progress) {
  return node('div', { className: 'progress-summary' }, [
    node('progress', {
      max: progress.total,
      value: progress.completed,
      'aria-label': `${progress.completed} activités terminées sur ${progress.total}`,
    }),
    node('span', { text: `${progress.completed}/${progress.total} activités` }),
  ]);
}

function assertObjectiveUi(objectiveUi) {
  if (objectiveUi == null) return null;
  if (typeof objectiveUi.renderObjectiveProgress !== 'function') {
    throw new TypeError('Learning Loop V2 objectiveUi.renderObjectiveProgress() is required');
  }
  return objectiveUi;
}

function renderObjectiveSurface(objectiveUi, model) {
  if (!objectiveUi || !Array.isArray(model.progress?.objectives)) return null;
  const rendered = objectiveUi.renderObjectiveProgress({
    document,
    context: model.context,
    courseObjectives: structuredClone(model.courseObjectives ?? []),
    objectiveProgress: structuredClone(model.progress.objectives),
    recommendation: structuredClone(model.progress.recommendation ?? null),
    activity: model.activity ? structuredClone(model.activity) : null,
  });
  if (rendered == null) return null;
  if (rendered instanceof Node) return rendered;
  if (Array.isArray(rendered) && rendered.every((item) => item instanceof Node)) {
    return node('div', { 'data-learning-loop-v2-ui': model.context }, rendered);
  }
  throw new TypeError('renderObjectiveProgress() must return a Node, an array of Nodes, or null');
}

function renderLibraryObjectiveDetails(objectiveSurface) {
  if (!objectiveSurface) return null;
  return node('details', { 'data-library-objective-details': 'true' }, [
    node('summary', { text: 'Voir la progression détaillée' }),
    objectiveSurface,
  ]);
}

function renderQcmForm(activity, submit) {
  const fieldset = node('fieldset', { className: 'answer-fieldset' });
  fieldset.append(node('legend', { text: 'Choisissez une réponse' }));
  for (const choice of activity.choices) {
    const inputId = `choice-${choice.choiceId}`;
    const input = node('input', {
      id: inputId,
      type: 'radio',
      name: 'qcm-choice',
      value: choice.choiceId,
      required: 'required',
    });
    fieldset.append(node('label', { className: 'choice-row', for: inputId }, [input, node('span', { text: choice.label })]));
  }

  const form = node('form', { className: 'activity-form' }, [fieldset, node('button', { type: 'submit', className: 'primary', text: 'Valider' })]);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const selected = new FormData(form).get('qcm-choice');
    if (selected) submit({ choiceId: selected });
  });
  return form;
}

function updateTokenAvailability(selects, activity) {
  const useCount = new Map();
  for (const select of selects) {
    if (select.value) useCount.set(select.value, (useCount.get(select.value) ?? 0) + 1);
  }
  for (const select of selects) {
    for (const option of select.options) {
      if (!option.value) continue;
      const token = activity.tokens.find((entry) => entry.tokenId === option.value);
      const usedElsewhere = (useCount.get(option.value) ?? 0) - (select.value === option.value ? 1 : 0);
      option.disabled = usedElsewhere >= token.maxUses;
    }
  }
}

function renderFillForm(activity, submit) {
  const sentence = node('div', { className: 'fill-sentence' });
  const selects = [];
  let slotNumber = 0;

  for (const segment of activity.segments) {
    if (Object.hasOwn(segment, 'text')) {
      sentence.append(node('span', { text: segment.text }));
      continue;
    }
    slotNumber += 1;
    const label = node('label', { className: 'fill-slot' });
    label.append(node('span', { className: 'sr-only', text: `Emplacement ${slotNumber}` }));
    const select = node('select', {
      required: 'required',
      'data-slot-id': segment.slotId,
      'aria-label': `Emplacement ${slotNumber}`,
    });
    select.append(node('option', { value: '', text: 'Choisir…' }));
    for (const token of activity.tokens) {
      select.append(node('option', { value: token.tokenId, text: token.label }));
    }
    select.addEventListener('change', () => updateTokenAvailability(selects, activity));
    selects.push(select);
    label.append(select);
    sentence.append(label);
  }

  const form = node('form', { className: 'activity-form' }, [
    node('fieldset', { className: 'answer-fieldset' }, [node('legend', { text: 'Complétez la phrase' }), sentence]),
    node('button', { type: 'submit', className: 'primary', text: 'Valider' }),
  ]);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const answer = Object.fromEntries(selects.map((select) => [select.dataset.slotId, select.value]));
    submit(answer);
  });
  return form;
}

export function renderApp(root, runtime, objectiveUiIntegration = null) {
  let notice = null;
  let busy = false;
  const objectiveUi = assertObjectiveUi(objectiveUiIntegration);

  const header = node('header', { className: 'app-header' }, [
    node('h1', { text: 'Learn-it' }),
  ]);
  const main = node('main', { className: 'app-main' });
  const liveRegion = node('div', {
    className: 'sr-only',
    role: 'status',
    'aria-live': 'polite',
    'aria-atomic': 'true',
  });
  root.replaceChildren(header, main, liveRegion);

  root.addEventListener('learnit:show-library', () => {
    main.replaceChildren(node('p', {
      role: 'status',
      text: 'Ouverture de la bibliothèque…',
    }));
    void renderLibrary();
  });

  function setBusy(value) {
    busy = value;
    root.setAttribute('aria-busy', String(value));
  }

  function announce(message) {
    if (!message) return;
    liveRegion.textContent = '';
    queueMicrotask(() => {
      if (liveRegion.isConnected) liveRegion.textContent = message;
    });
  }

  function focusAfterRender(element) {
    if (!element) return;
    if (!element.hasAttribute('tabindex')) element.setAttribute('tabindex', '-1');
    queueMicrotask(() => {
      if (!element.isConnected) return;
      try {
        element.focus({ preventScroll: false });
      } catch {
        element.focus();
      }
    });
  }

  function shell(content, { focusTarget = null, announcement = null } = {}) {
    main.replaceChildren(...[notice, content].filter(Boolean));
    announce(announcement);
    focusAfterRender(focusTarget);
  }

  async function run(action, onSuccess) {
    if (busy) return;
    setBusy(true);
    notice = null;
    try {
      const result = await action();
      if (onSuccess) await onSuccess(result);
    } catch (error) {
      const messages = errorMessages(error);
      notice = renderNotice(messages);
      await renderLibrary({ announcement: messages.join(' ') });
    } finally {
      setBusy(false);
    }
  }

  function renderCourseLabelForm(course) {
    const inputId = `course-display-label-${course.courseInstallId}`;
    const helpId = `${inputId}-help`;
    const input = node('input', {
      id: inputId,
      name: 'display-label',
      type: 'text',
      value: course.title,
      required: 'required',
      autocomplete: 'off',
      'aria-describedby': helpId,
    });
    const form = node('form', { className: 'course-label-form' }, [
      node('label', { className: 'field-label', for: inputId, text: 'Nom local du cours' }),
      node('div', { className: 'course-label-controls' }, [
        input,
        node('button', { type: 'submit', className: 'secondary', text: 'Enregistrer' }),
      ]),
      node('p', {
        id: helpId,
        className: 'help',
        text: 'Ce nom est utilisé uniquement sur cet appareil.',
      }),
    ]);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const requestedLabel = input.value;
      run(() => runtime.setCourseDisplayLabel(course.courseInstallId, requestedLabel), async () => {
        const normalizedLabel = requestedLabel.trim();
        const message = `Nom local enregistré : « ${normalizedLabel} ».`;
        notice = renderNotice([message], 'success');
        await renderLibrary({ announcement: message });
      });
    });
    return form;
  }

  function renderResetAction() {
    const container = node('div', { className: 'reset-confirmation' });
    const showInitial = () => {
      container.replaceChildren(node('button', {
        type: 'button',
        className: 'danger-quiet',
        text: 'Réinitialiser les données locales',
        onclick: () => {
          const confirmButton = node('button', {
            type: 'button',
            className: 'danger-quiet',
            text: 'Confirmer la réinitialisation',
            onclick: () => run(() => runtime.resetNextData(), () => {
              const message = 'Les données locales ont été supprimées.';
              notice = renderNotice([message], 'success');
              return renderLibrary({ announcement: message });
            }),
          });
          const cancelButton = node('button', {
            className: 'secondary',
            text: 'Annuler',
            onclick: () => {
              showInitial();
              announce('Réinitialisation annulée.');
            },
          });
          container.setAttribute('role', 'group');
          container.setAttribute('aria-label', 'Confirmer la réinitialisation');
          container.replaceChildren(confirmButton, cancelButton);
          announce('Confirmez la réinitialisation des données de Learn-it Next.');
          focusAfterRender(confirmButton);
        },
      }));
      container.removeAttribute('role');
      container.removeAttribute('aria-label');
    };
    showInitial();
    return container;
  }

  async function renderLibrary({ focus = true, announcement = null } = {}) {
    const courses = await runtime.listCourses();
    const libraryTitle = node('h2', { id: 'library-title', tabindex: '-1', text: 'Vos cours' });
    const section = node('section', { 'aria-labelledby': 'library-title' });
    section.append(node('div', { className: 'section-heading' }, [
      node('div', {}, [node('p', { className: 'eyebrow', text: 'Bibliothèque' }), libraryTitle]),
      renderResetAction(),
    ]));

    const importForm = node('form', { className: 'import-panel' });
    const fileInput = node('input', { id: 'kit-file', type: 'file', accept: '.json,application/json', required: 'required' });
    const importButton = node('button', { type: 'submit', className: 'primary', text: 'Importer', disabled: true });
    const fileStatus = node('p', {
      className: 'help',
      role: 'status',
      'aria-live': 'polite',
      'aria-atomic': 'true',
      text: 'Sélectionnez un fichier JSON à importer.',
    });
    let selectionVersion = 0;
    let selectedFileText = null;

    fileInput.addEventListener('change', async () => {
      const version = selectionVersion + 1;
      selectionVersion = version;
      selectedFileText = null;
      importButton.disabled = true;
      const file = fileInput.files?.[0];
      if (!file) {
        fileStatus.textContent = 'Sélectionnez un fichier JSON à importer.';
        return;
      }

      fileStatus.textContent = `Lecture de « ${file.name} »…`;
      try {
        const text = await file.text();
        if (version !== selectionVersion) return;
        selectedFileText = text;
        importButton.disabled = false;
        fileStatus.textContent = `« ${file.name} » est prêt à être importé.`;
      } catch (error) {
        if (version !== selectionVersion) return;
        const message = `Lecture du fichier impossible : ${error?.message ?? String(error)}`;
        fileStatus.textContent = message;
        announce(message);
      }
    });

    importForm.append(
      node('div', {}, [
        node('label', { for: 'kit-file', className: 'field-label', text: 'Importer un cours' }),
        node('p', { className: 'help', text: 'Le fichier est vérifié avant l’import.' }),
        fileStatus,
      ]),
      fileInput,
      importButton,
    );
    importForm.addEventListener('submit', (event) => {
      event.preventDefault();
      if (selectedFileText === null) return;
      const payload = selectedFileText;
      run(() => runtime.importPackage(payload), async (result) => {
        const message = `${result.courseCount} cours importé(s) depuis « ${result.title} ».`;
        notice = renderNotice([message], 'success');
        await renderLibrary({ announcement: message });
      });
    });
    section.append(importForm);

    if (courses.length === 0) {
      section.append(node('div', { className: 'empty-state' }, [
        node('h3', { text: 'Bibliothèque vide' }),
        node('p', { text: 'Importez un kit conforme pour commencer un cours.' }),
      ]));
    } else {
      const list = node('div', { className: 'course-grid' });
      for (const course of courses) {
        const reviewQueue = await runtime.getReviewQueue(course.courseInstallId);
        const courseAction = course.progress.isComplete
          ? node('p', { className: 'course-complete', text: 'Cours terminé' })
          : node('button', {
            type: 'button',
            className: 'primary',
            text: course.progress.completed === 0 ? 'Commencer' : 'Reprendre',
            'data-course-learning-action': 'learn',
            'data-course-install-id': course.courseInstallId,
            onclick: () => run(() => runtime.startCourse(course.courseInstallId), renderSessionSnapshot),
          });
        const reviewAction = reviewQueue.total === 0
          ? node('p', { className: 'help', text: 'À revoir : aucune activité.' })
          : node('div', {}, [
            node('p', { text: `À revoir : ${reviewQueue.total} activité${reviewQueue.total > 1 ? 's' : ''}.` }),
            node('button', {
              type: 'button',
              className: 'secondary',
              text: 'Ouvrir À revoir',
              'data-course-learning-action': 'review',
              'data-course-install-id': course.courseInstallId,
              onclick: () => run(() => runtime.startReviewQueue(course.courseInstallId), renderSessionSnapshot),
            }),
          ]);
        const objectiveSurface = renderObjectiveSurface(objectiveUi, {
          context: 'library',
          courseObjectives: course.objectives,
          progress: course.progress,
        });
        const objectiveDetails = renderLibraryObjectiveDetails(objectiveSurface);
        list.append(node('article', {
          className: 'course-card',
          'data-course-install-id': course.courseInstallId,
        }, [
          node('div', {}, [
            node('h3', { text: course.title }),
            course.subtitle ? node('p', { text: course.subtitle }) : null,
            node('p', { className: 'course-meta', text: `${course.estimatedMinutes} min · ${course.activityCount} activités` }),
          ]),
          renderCourseLabelForm(course),
          renderProgress(course.progress),
          objectiveDetails,
          courseAction,
          reviewAction,
        ]));
      }
      section.append(list);
    }
    shell(section, { focusTarget: focus ? libraryTitle : null, announcement });
  }

  async function submitAnswer(activityRevisionId, answer) {
    await run(() => runtime.answer(activityRevisionId, answer), renderFeedback);
  }

  function renderSessionSnapshot(session, { focus = true } = {}) {
    if (!session || !session.currentActivity) {
      const message = session?.mode === 'review'
        ? 'La file À revoir est vide. Vous pouvez reprendre le parcours normal.'
        : 'Cours terminé. La progression a été enregistrée.';
      notice = renderNotice([message], 'success');
      return renderLibrary({ announcement: message });
    }
    const activity = session.currentActivity;
    const reviewMode = session.mode === 'review';
    const activityTitle = node('h2', { id: 'activity-title', tabindex: '-1', text: activity.prompt });
    const objectiveSurface = renderObjectiveSurface(objectiveUi, {
      context: reviewMode ? 'review' : 'session',
      courseObjectives: session.courseObjectives,
      progress: session.progress,
      activity,
    });
    const section = node('section', { 'aria-labelledby': 'activity-title', className: 'session-panel' }, [
      node('button', { type: 'button', className: 'back-link', text: '← Bibliothèque', onclick: () => renderLibrary() }),
      node('p', { className: 'eyebrow', text: reviewMode ? `${session.title} · À revoir` : session.title }),
      activityTitle,
      renderProgress(session.progress),
      objectiveSurface,
      reviewMode ? node('p', { text: `${session.review.remaining} activité${session.review.remaining > 1 ? 's' : ''} dans la file À revoir.` }) : null,
      activity.type === 'qcm'
        ? renderQcmForm(activity, (answer) => submitAnswer(activity.activityRevisionId, answer))
        : renderFillForm(activity, (answer) => submitAnswer(activity.activityRevisionId, answer)),
      reviewMode ? node('button', {
        type: 'button',
        className: 'secondary',
        text: 'Revenir au parcours',
        onclick: () => run(() => runtime.startCourse(session.courseInstallId), renderSessionSnapshot),
      }) : null,
    ]);
    shell(section, { focusTarget: focus ? activityTitle : null });
  }

  function renderFeedback(result) {
    const reviewMode = result.mode === 'review';
    const reviewRemaining = result.review?.remaining ?? 0;
    const complete = result.progress.isComplete;
    const outcomeText = result.correct ? 'Réponse correcte' : 'Pas tout à fait';
    const outcome = node('p', {
      className: result.correct ? 'feedback-correct' : 'feedback-incorrect',
      role: 'status',
      'aria-live': 'polite',
      'aria-atomic': 'true',
      tabindex: '-1',
      text: outcomeText,
    });
    const primaryAction = reviewMode
      ? node('button', {
        type: 'button',
        className: 'primary',
        text: reviewRemaining === 0 ? 'Retour à la bibliothèque' : 'Activité suivante à revoir',
        onclick: reviewRemaining === 0 ? () => renderLibrary() : () => run(() => runtime.getSession(), renderSessionSnapshot),
      })
      : node('button', {
        type: 'button',
        className: 'primary',
        text: complete ? 'Retour à la bibliothèque' : 'Activité suivante',
        onclick: complete ? () => renderLibrary() : () => run(() => runtime.getSession(), renderSessionSnapshot),
      });
    const objectiveSurface = renderObjectiveSurface(objectiveUi, {
      context: 'feedback',
      courseObjectives: result.courseObjectives,
      progress: result.progress,
      activity: result.nextActivity,
    });
    const section = node('section', { 'aria-labelledby': 'feedback-title', className: 'feedback-panel' }, [
      outcome,
      node('h2', { id: 'feedback-title', text: 'Explication' }),
      node('p', { text: result.explanation }),
      renderProgress(result.progress),
      objectiveSurface,
      reviewMode ? node('p', {
        text: reviewRemaining === 0
          ? 'File À revoir vide. Cette réussite retire l’activité de la file.'
          : `${reviewRemaining} activité${reviewRemaining > 1 ? 's' : ''} reste${reviewRemaining > 1 ? 'nt' : ''} à revoir.`,
      }) : null,
      primaryAction,
      reviewMode ? node('button', {
        type: 'button',
        className: 'secondary',
        text: 'Revenir au parcours',
        onclick: () => run(() => runtime.startCourse(result.courseInstallId), renderSessionSnapshot),
      }) : null,
    ]);
    shell(section, { focusTarget: outcome, announcement: outcomeText });
  }

  async function initialize() {
    setBusy(true);
    try {
      const resumed = await runtime.resumeActiveCourse();
      if (resumed?.currentActivity) renderSessionSnapshot(resumed, { focus: false });
      else await renderLibrary({ focus: false });
    } catch (error) {
      const messages = errorMessages(error);
      notice = renderNotice(messages);
      await renderLibrary({ focus: false, announcement: messages.join(' ') });
    } finally {
      setBusy(false);
    }
  }

  initialize();
}