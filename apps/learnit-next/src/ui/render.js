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
  if (Array.isArray(error?.errors) && error.errors.length) {
    return error.errors.map((entry) => `${entry.path}: ${entry.message}`);
  }
  return [error?.message ?? 'Une erreur inattendue est survenue.'];
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

export function renderApp(root, runtime) {
  let notice = null;
  let busy = false;

  const header = node('header', { className: 'app-header' }, [
    node('div', {}, [
      node('p', { className: 'eyebrow', text: 'Nouvelle génération isolée' }),
      node('h1', { text: 'Learn-it Next' }),
    ]),
    node('p', { className: 'contract-badge', text: runtime.contractVersion }),
  ]);
  const main = node('main', { className: 'app-main' });
  const liveRegion = node('div', {
    className: 'sr-only',
    role: 'status',
    'aria-live': 'polite',
    'aria-atomic': 'true',
  });
  root.replaceChildren(header, main, liveRegion);

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

  async function renderLibrary({ focus = true, announcement = null } = {}) {
    const courses = await runtime.listCourses();
    const libraryTitle = node('h2', { id: 'library-title', tabindex: '-1', text: 'Vos cours' });
    const section = node('section', { 'aria-labelledby': 'library-title' });
    section.append(node('div', { className: 'section-heading' }, [
      node('div', {}, [node('p', { className: 'eyebrow', text: 'Bibliothèque locale' }), libraryTitle]),
      node('button', {
        type: 'button',
        className: 'danger-quiet',
        text: 'Réinitialiser Learn-it Next',
        onclick: () => {
          if (globalThis.confirm('Supprimer uniquement les données de Learn-it Next ?')) {
            run(() => runtime.resetNextData(), () => {
              const message = 'Les données de Learn-it Next ont été supprimées.';
              notice = renderNotice([message], 'success');
              return renderLibrary({ announcement: message });
            });
          }
        },
      }),
    ]));

    const importForm = node('form', { className: 'import-panel' });
    const fileInput = node('input', { id: 'kit-file', type: 'file', accept: '.json,application/json', required: 'required' });
    importForm.append(
      node('div', {}, [
        node('label', { for: 'kit-file', className: 'field-label', text: 'Importer un kit learnit.kit.v2' }),
        node('p', { className: 'help', text: 'Les packages legacy ou invalides sont rejetés avant toute écriture d’import.' }),
      ]),
      fileInput,
      node('button', { type: 'submit', className: 'primary', text: 'Importer' }),
    );
    importForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const file = fileInput.files?.[0];
      if (!file) return;
      run(async () => runtime.importPackage(await file.text()), async (result) => {
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
        const courseAction = course.progress.isComplete
          ? node('p', { className: 'course-complete', text: 'Cours terminé' })
          : node('button', {
            type: 'button',
            className: 'primary',
            text: course.progress.completed === 0 ? 'Commencer' : 'Reprendre',
            onclick: () => run(() => runtime.startCourse(course.courseInstallId), renderSessionSnapshot),
          });
        list.append(node('article', { className: 'course-card' }, [
          node('div', {}, [
            node('h3', { text: course.title }),
            course.subtitle ? node('p', { text: course.subtitle }) : null,
            node('p', { className: 'course-meta', text: `${course.estimatedMinutes} min · ${course.activityCount} activités` }),
          ]),
          renderProgress(course.progress),
          courseAction,
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
      const message = 'Cours terminé. La progression a été enregistrée.';
      notice = renderNotice([message], 'success');
      return renderLibrary({ announcement: message });
    }
    const activity = session.currentActivity;
    const activityTitle = node('h2', { id: 'activity-title', tabindex: '-1', text: activity.prompt });
    const section = node('section', { 'aria-labelledby': 'activity-title', className: 'session-panel' }, [
      node('button', { type: 'button', className: 'back-link', text: '← Bibliothèque', onclick: () => renderLibrary() }),
      node('p', { className: 'eyebrow', text: session.title }),
      activityTitle,
      renderProgress(session.progress),
      activity.type === 'qcm'
        ? renderQcmForm(activity, (answer) => submitAnswer(activity.activityRevisionId, answer))
        : renderFillForm(activity, (answer) => submitAnswer(activity.activityRevisionId, answer)),
    ]);
    shell(section, { focusTarget: focus ? activityTitle : null });
  }

  function renderFeedback(result) {
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
    const section = node('section', { 'aria-labelledby': 'feedback-title', className: 'feedback-panel' }, [
      outcome,
      node('h2', { id: 'feedback-title', text: 'Explication' }),
      node('p', { text: result.explanation }),
      renderProgress(result.progress),
      node('button', {
        type: 'button',
        className: 'primary',
        text: complete ? 'Retour à la bibliothèque' : 'Activité suivante',
        onclick: complete ? () => renderLibrary() : () => run(() => runtime.getSession(), renderSessionSnapshot),
      }),
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
