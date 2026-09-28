import { renderActivityPresentation, readActivityResponse } from './activity_presenters.js';
import { renderEmbeddedMediaSet } from './media.js';
import { createNavigationDrawer } from './navigation.js';
import { matchesLibrarySearch } from '../core/library.js';

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
    sessionDelta: model.sessionDelta ? structuredClone(model.sessionDelta) : null,
  });
  if (rendered == null) return null;
  if (rendered instanceof Node) return rendered;
  if (Array.isArray(rendered) && rendered.every((item) => item instanceof Node)) {
    return node('div', { 'data-learning-loop-v2-ui': model.context }, rendered);
  }
  throw new TypeError('renderObjectiveProgress() must return a Node, an array of Nodes, or null');
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

function activityPresentationHeading(presentation) {
  return presentation.prompt
    ?? presentation.title
    ?? presentation.front
    ?? 'Activité';
}

function renderServedActivityForm(activity, submit) {
  const presentation = activity?.presentation;
  if (!presentation || typeof presentation !== 'object') {
    throw new TypeError('Learner-safe ActivityPresentation is required');
  }
  const responseStatus = node('p', {
    className: 'help',
    role: 'status',
    'aria-live': 'polite',
    'data-served-activity-response-status': 'true',
  });
  const submitLabel = ['lesson', 'flashcard'].includes(presentation.type)
    ? 'Continuer'
    : 'Valider';
  const submitButton = node('button', {
    type: 'submit',
    className: 'primary',
    text: submitLabel,
    'data-served-activity-submit': 'true',
    disabled: presentation.type === 'flashcard',
  });
  const form = node('form', {
    className: 'activity-form served-activity-form',
    'data-served-activity-type': presentation.type,
  }, [
    renderActivityPresentation(presentation),
    responseStatus,
    submitButton,
  ]);
  form.addEventListener('learnit:activity-ready', () => {
    submitButton.disabled = false;
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    responseStatus.textContent = '';
    try {
      submit(readActivityResponse(form, presentation));
    } catch (error) {
      if (error?.code !== 'ACTIVITY_RESPONSE_REQUIRED') throw error;
      responseStatus.textContent = error.message;
    }
  });
  return form;
}

function escapeAtlasActivityHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character]);
}

export function renderAtlasActivityMarkup(activity) {
  const esc = escapeAtlasActivityHtml;
  const prompt =
    `<p class="atlas-question"><strong>${esc(activity.prompt)}</strong></p>`;

  if (activity.type === 'qcm') {
    const choices = activity.choices
      .map((choice) => {
        const id = `atlas-choice-${choice.choiceId}`;
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
      .map((token) => (
        `<option value="${esc(token.tokenId)}">${esc(token.label)}</option>`
      ))
      .join('');

    let slotNumber = 0;
    const sentence = activity.segments
      .map((segment) => {
        if (Object.hasOwn(segment, 'text')) {
          return `<span>${esc(segment.text)}</span>`;
        }
        slotNumber += 1;
        return (
          '<label class="atlas-fill-slot">'
          + `<span class="visually-hidden">Réponse ${slotNumber}</span>`
          + `<select data-atlas-slot="${esc(segment.slotId)}">`
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

  throw new Error(`ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${activity.type}`);
}

export function readAtlasActivityResponse(container, activity) {
  if (activity.type === 'qcm') {
    const selected = container.querySelector(
      '[data-atlas-choice="true"]:checked',
    );
    if (!selected) {
      const error = new Error('Choisissez une réponse avant de valider.');
      error.code = 'ATLAS_ANSWER_REQUIRED';
      throw error;
    }
    return { choiceId: selected.value };
  }

  if (activity.type === 'fill') {
    const answer = {};
    const selects = [...container.querySelectorAll('[data-atlas-slot]')];
    for (const select of selects) {
      if (!select.value) {
        const error = new Error(
          'Complétez toutes les réponses avant de valider.',
        );
        error.code = 'ATLAS_ANSWER_REQUIRED';
        throw error;
      }
      answer[select.getAttribute('data-atlas-slot')] = select.value;
    }
    return answer;
  }

  throw new Error(`ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${activity.type}`);
}

export function renderApp(root, runtime, objectiveUiIntegration = null) {
  let notice = null;
  let busy = false;
  let currentView = 'library';
  let todayAvailable = false;
  let libraryImportActive = false;
  let libraryRenderEpoch = 0;
  const atlasLearningProjections = new Map();
  const objectiveUi = assertObjectiveUi(objectiveUiIntegration);

  const main = node('main', { className: 'app-main' });
  const liveRegion = node('div', {
    className: 'sr-only',
    role: 'status',
    'aria-live': 'polite',
    'aria-atomic': 'true',
  });

  let navigation = null;
  const headerTitle = node('h1', { text: 'Learn-it' });
  const header = node('header', { className: 'app-header app-shell-header' });
  navigation = createNavigationDrawer(root, (view) => {
    void navigate(view);
  });
  header.append(navigation.trigger, headerTitle);
  root.replaceChildren(header, navigation.backdrop, navigation.drawer, main, liveRegion);
  navigation.setActiveView('library');

  function setViewElementVisible(element, visible) {
    if (!element) return;
    element.hidden = !visible;
    if (visible) element.removeAttribute('inert');
    else element.setAttribute('inert', '');
  }

  async function navigate(view) {
    const requested = view === 'import' ? 'library' : view;
    const todaySurface = root.querySelector('[data-atlas-int-surface]');
    if (requested === 'today') {
      if (!todayAvailable || !todaySurface) {
        await navigate('library');
        return;
      }
      currentView = 'today';
      setViewElementVisible(main, false);
      setViewElementVisible(todaySurface, true);
      navigation.setActiveView('today');
      const title = todaySurface.querySelector('h2');
      focusAfterRender(title);
      return;
    }

    currentView = 'library';
    setViewElementVisible(todaySurface, false);
    setViewElementVisible(main, true);
    navigation.setActiveView('library');
    await renderLibrary({ focus: view !== 'import' });
    if (view === 'import') {
      const management = main.querySelector('.library-management');
      if (management) {
        management.open = true;
        focusAfterRender(management.querySelector('summary'));
      } else {
        focusAfterRender(main.querySelector('.library-file-picker'));
      }
    }
  }

  root.addEventListener('learnit:show-library', () => {
    void navigate('library');
  });
  root.addEventListener('learnit:navigate', event => {
    const view = event.detail?.view;
    if (['today', 'library', 'import'].includes(view)) void navigate(view);
  });
  root.addEventListener('learnit:view-availability', event => {
    if (event.detail?.view !== 'today') return;
    todayAvailable = Boolean(event.detail.available);
    navigation.setTodayAvailable(todayAvailable);
    if (!todayAvailable && currentView === 'today') void navigate('library');
  });
  root.addEventListener('learnit:learning-projection', event => {
    if (event.detail?.source !== 'atlas') return;
    const incoming = (event.detail.courses ?? [])
      .filter(projection => projection?.courseInstallId);
    const changed = incoming.length !== atlasLearningProjections.size
      || incoming.some(projection => (
        JSON.stringify(atlasLearningProjections.get(projection.courseInstallId) ?? null)
        !== JSON.stringify(projection)
      ));
    if (!changed) return;
    atlasLearningProjections.clear();
    for (const projection of incoming) {
      atlasLearningProjections.set(projection.courseInstallId, projection);
    }
    if (currentView === 'library' && !libraryImportActive) {
      void renderLibrary({ focus: false });
    }
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

  function dispatchCourseLearningAction(courseInstallId, durationMinutes, fallback) {
    const event = new CustomEvent('learnit:course-learning-action', {
      cancelable: true,
      detail: {
        courseInstallId,
        durationMinutes: Number.isInteger(durationMinutes) ? durationMinutes : null,
      },
    });
    const unhandled = root.dispatchEvent(event);
    if (unhandled && typeof fallback === 'function') fallback();
  }

  function renderExternalLearningProjection(projection) {
    if (!projection) return null;
    const states = Array.isArray(projection.objectiveStates) ? projection.objectiveStates : [];
    return node('div', {
      className: 'course-progress-compact library-learning-projection',
      'data-library-learning-projection': projection.source ?? 'learning',
    }, [
      node('div', { className: 'course-progress-at-glance' }, [
        node('span', { className: 'course-progress-caption', text: 'Progression' }),
        node('div', {
          className: 'course-objective-track',
          role: 'img',
          'aria-label': projection.overviewText ?? 'Progression du cours',
        }, states.map(item => node('span', {
          className: `course-objective-segment course-objective-segment--${item.state}`,
          title: `${item.label} — ${item.stateLabel}`,
          'aria-hidden': 'true',
        }))),
        node('span', { className: 'course-progress-text', text: projection.overviewText ?? '' }),
      ]),
      node('strong', {
        className: 'course-next-step',
        text: projection.sessionAvailableNow
          ? `À faire maintenant : ${projection.nextStep}`
          : projection.nextStep,
      }),
    ]);
  }

  function renderExternalObjectiveDetails(projection) {
    const states = Array.isArray(projection?.objectiveStates) ? projection.objectiveStates : [];
    if (!states.length) return null;
    return node('details', {
      className: 'course-objectives-details',
      'data-library-objective-details': 'true',
    }, [
      node('summary', { text: 'Voir les objectifs' }),
      node('ul', {
        className: 'course-objective-status-list',
        'aria-label': 'État des objectifs',
      }, states.map(item => node('li', {
        className: `course-objective-status-item course-objective-status-item--${item.state}`,
      }, [
        node('span', { className: 'course-objective-state-marker', 'aria-hidden': 'true' }),
        node('span', { text: item.label }),
        node('strong', { text: item.stateLabel }),
      ]))),
    ]);
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
            onclick: () => run(() => runtime.resetNextData(), async (report) => {
              const remaining = Object.values(report?.counts ?? {}).reduce(
                (total, value) => total + (Number.isInteger(value) ? value : 0),
                0,
              );
              if (remaining !== 0) throw new Error('La réinitialisation n’a pas vidé toutes les données locales.');
              const message = 'Les données locales ont été supprimées.';
              notice = renderNotice([message], 'success');
              root.dispatchEvent(new CustomEvent('learnit:library-changed', { detail: { reason: 'reset' } }));
              await renderLibrary({ announcement: message });
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
          announce('Confirmez la réinitialisation des données de Learn-it.');
          focusAfterRender(confirmButton);
        },
      }));
      container.removeAttribute('role');
      container.removeAttribute('aria-label');
    };
    showInitial();
    return container;
  }

  function objectiveStatusLabel(status) {
    return ({
      'not-started': 'À découvrir',
      training: 'En apprentissage',
      'review-needed': 'À renforcer',
      'ready-for-validation': 'À confirmer',
      'validated-recently': 'Acquis récemment',
    })[status] ?? 'Objectifs';
  }

  function courseObjectiveSummary(course) {
    const recommendation = course.progress?.recommendation ?? null;
    if (!recommendation?.objectiveId) return 'Voir les objectifs';
    const objective = (course.objectives ?? []).find(item => item.objectiveId === recommendation.objectiveId);
    if (!objective) return 'Voir les objectifs';
    return `${objectiveStatusLabel(recommendation.status)} — ${objective.label}`;
  }

  function renderCourseCompletionGuidance(course, reviewQueue) {
    if (!course.progress?.isComplete) return null;
    const recommendation = course.progress.recommendation ?? null;
    let detail = 'Toutes les activités prévues ont été réalisées.';
    if (recommendation?.action === 'correct' && reviewQueue.total > 0) {
      detail = 'Un objectif reste à renforcer. Reprenez une activité incorrecte pour continuer.';
    } else if (recommendation?.action === 'validate') {
      const acquired = (course.progress.objectives ?? []).filter(item => item.status === 'validated-recently').length;
      detail = acquired > 0
        ? 'Un objectif est acquis récemment et un autre reste à confirmer. Son entraînement est réussi, mais une validation distincte doit encore le confirmer. Toutes les activités disponibles ont été réalisées ; Learn-it n’a actuellement ni nouvelle activité de validation à proposer ni date de disponibilité.'
        : 'Un objectif reste à confirmer. Son entraînement est réussi, mais une validation distincte doit encore le confirmer. Toutes les activités disponibles ont été réalisées ; Learn-it n’a actuellement ni nouvelle activité de validation à proposer ni date de disponibilité.';
    } else if (recommendation?.action === 'revisit-later') {
      detail = 'Les acquis sont récents. Learn-it n’indique actuellement ni action supplémentaire ni date précise de consolidation.';
    } else if (recommendation?.action === 'continue-training' || recommendation?.action === 'start-training') {
      detail = 'Un objectif reste en apprentissage. Toutes les activités disponibles ont été réalisées ; aucune activité supplémentaire n’est proposée actuellement.';
    }
    return node('div', {
      className: 'course-path-status',
      'data-course-path-status': recommendation?.action ?? 'none',
    }, [
      node('strong', { text: 'Parcours d’activités terminé' }),
      node('span', { text: detail }),
    ]);
  }

  async function renderLibrary({ focus = true, announcement = null, focusCourseInstallId = null } = {}) {
    const renderEpoch = ++libraryRenderEpoch;
    const courses = await runtime.listCourses();
    if (renderEpoch !== libraryRenderEpoch) return;
    const libraryTitle = node('h2', { id: 'library-title', tabindex: '-1', text: 'Vos cours' });
    const section = node('section', { 'aria-labelledby': 'library-title' });
    let requestedCourseFocusTarget = null;
    section.append(node('div', { className: 'section-heading library-heading' }, [
      libraryTitle,
    ]));

    const importForm = node('form', { className: 'import-panel' });
    const fileInput = node('input', { id: 'kit-file', className: 'sr-only library-file-input', type: 'file', accept: '.json,application/json', required: 'required' });
    const importButton = node('button', { type: 'submit', className: 'primary', text: 'Ajouter à la bibliothèque', disabled: true });
    const fileStatus = node('p', {
      className: 'help',
      role: 'status',
      'aria-live': 'polite',
      'aria-atomic': 'true',
      text: '',
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
        libraryImportActive = false;
        fileStatus.textContent = '';
        return;
      }

      libraryImportActive = true;
      libraryRenderEpoch += 1;
      try {
        const text = await file.text();
        const preview = await runtime.previewImport(text);
        if (version !== selectionVersion) return;
        selectedFileText = text;
        importButton.disabled = false;
        fileStatus.textContent = preview.title;
      } catch (error) {
        if (version !== selectionVersion) return;
        libraryImportActive = false;
        const message = `Lecture du fichier impossible : ${error?.message ?? String(error)}`;
        fileStatus.textContent = message;
        announce(message);
      }
    });

    importForm.append(
      node('div', { className: 'library-import-controls' }, [
        node('label', { for: 'kit-file', className: 'secondary library-file-picker', text: 'Choisir un cours' }),
        fileInput,
        fileStatus,
      ]),
      importButton,
    );
    importForm.addEventListener('submit', (event) => {
      event.preventDefault();
      if (selectedFileText === null) return;
      const payload = selectedFileText;
      run(() => runtime.importPackage(payload), async (result) => {
        libraryImportActive = false;
        root.dispatchEvent(new CustomEvent('learnit:library-changed', { detail: { reason: 'import' } }));
        await renderLibrary({ announcement: `${result.title} ajouté à la bibliothèque.` });
      });
    });
    if (courses.length === 0) {
      section.append(node('div', { className: 'empty-state empty-library-import' }, [
        node('h3', { text: 'Importer votre premier cours' }),
        importForm,
      ]));
    } else {
      const list = node('div', { className: 'course-grid', 'data-library-course-list': 'true' });
      const courseEntries = [];
      const searchStatus = node('p', {
        className: 'sr-only',
        role: 'status',
        'aria-live': 'polite',
        text: '',
      });
      const searchInput = node('input', {
        type: 'search',
        className: 'library-search-input',
        placeholder: 'Rechercher un cours',
        'aria-label': 'Rechercher dans vos cours',
      });
      const filterCourses = () => {
        const query = searchInput.value;
        const hasQuery = query.trim().length > 0;
        let visible = 0;
        for (const entry of courseEntries) {
          const match = matchesLibrarySearch(query, entry.searchable);
          entry.article.hidden = !match;
          if (match) visible += 1;
        }
        searchStatus.textContent = hasQuery
          ? `${visible} cours trouvé${visible > 1 ? 's' : ''} sur ${courses.length}.`
          : '';
      };
      searchInput.addEventListener('input', filterCourses);
      if (courses.length >= 3) {
        section.append(node('div', { className: 'library-search' }, [searchInput, searchStatus]));
      }
      for (const course of courses) {
        const learningAvailable = Boolean(course.progress);
        const externalProjection = atlasLearningProjections.get(course.courseInstallId) ?? null;
        const reviewQueue = learningAvailable
          ? await runtime.getReviewQueue(course.courseInstallId)
          : { total: 0 };
        const correctivePriority =
          !externalProjection
          && course.progress?.recommendation?.action === 'correct'
          && reviewQueue.total > 0;

        let durationSelect = null;
        if (externalProjection?.sessionAvailableNow) {
          durationSelect = node('select', {
            className: 'library-duration-select',
            'aria-label': `Durée de la séance pour ${course.title}`,
          }, (externalProjection.durations ?? [5, 15, 30]).map(minutes => node('option', {
            value: String(minutes),
            text: `${minutes} min`,
          })));
          durationSelect.value = String((externalProjection.durations ?? [5, 15, 30]).includes(15) ? 15 : (externalProjection.durations ?? [5])[0]);
        }

        const courseAction = externalProjection
          ? externalProjection.sessionAvailableNow
            ? node('button', {
              type: 'button',
              className: 'primary',
              text: externalProjection.actionLabel ?? 'Continuer',
              'data-course-learning-action': 'learn',
              'data-course-install-id': course.courseInstallId,
              onclick: () => dispatchCourseLearningAction(
                course.courseInstallId,
                durationSelect ? Number(durationSelect.value) : null,
                () => run(() => runtime.startCourse(course.courseInstallId), renderSessionSnapshot),
              ),
            })
            : null
          : learningAvailable && !course.progress.isComplete
            ? node('button', {
              type: 'button',
              className: correctivePriority ? 'secondary' : 'primary',
              text: course.progress.completed === 0 ? 'Commencer' : 'Reprendre',
              'data-course-learning-action': 'learn',
              'data-course-install-id': course.courseInstallId,
              onclick: () => run(() => runtime.startCourse(course.courseInstallId), renderSessionSnapshot),
            })
            : null;

        const completionGuidance = renderCourseCompletionGuidance(course, reviewQueue);
        const reviewAction = correctivePriority
          ? node('button', {
            type: 'button',
            className: 'primary',
            text: 'Renforcer maintenant',
            'data-course-learning-action': 'review',
            'data-course-install-id': course.courseInstallId,
            onclick: () => run(() => runtime.startReviewQueue(course.courseInstallId), renderSessionSnapshot),
          })
          : null;

        const objectiveSurface = externalProjection
          ? null
          : renderObjectiveSurface(objectiveUi, {
            context: 'library',
            courseObjectives: course.objectives,
            progress: course.progress,
          });
        const objectiveDetails = externalProjection
          ? renderExternalObjectiveDetails(externalProjection)
          : objectiveSurface
            ? node('details', { className: 'course-objectives-details' }, [
              node('summary', { text: courseObjectiveSummary(course) }),
              objectiveSurface,
            ])
            : null;

        const titleHeading = node('h3', {
          className: 'course-title-heading',
          text: course.title,
        });
        const titleSlot = node('div', { className: 'course-title-slot' }, [titleHeading]);
        let settingsDetails = null;
        let settingsSummary = null;

        function beginRename() {
          const inputId = `course-display-label-${course.courseInstallId}`;
          const input = node('input', {
            id: inputId,
            name: 'display-label',
            type: 'text',
            value: course.title,
            required: 'required',
            maxlength: '180',
            autocomplete: 'off',
            'aria-label': `Nouveau nom local pour ${course.title}`,
          });
          const restoreTitle = ({ focusOptions = true } = {}) => {
            titleSlot.replaceChildren(titleHeading);
            if (focusOptions) queueMicrotask(() => settingsSummary?.focus());
          };
          const form = node('form', {
            className: 'course-inline-rename',
            'data-course-inline-rename': 'true',
          }, [
            input,
            node('div', { className: 'course-inline-rename-actions' }, [
              node('button', { type: 'submit', className: 'secondary', text: 'Enregistrer' }),
              node('button', {
                type: 'button',
                className: 'quiet',
                text: 'Annuler',
                onclick: () => {
                  restoreTitle();
                  announce('Renommage annulé.');
                },
              }),
            ]),
          ]);
          form.addEventListener('submit', event => {
            event.preventDefault();
            const requestedLabel = input.value;
            void run(
              () => runtime.setCourseDisplayLabel(course.courseInstallId, requestedLabel),
              async (normalizedResult) => {
                const normalizedLabel = typeof normalizedResult === 'string'
                  ? normalizedResult
                  : requestedLabel.trim();
                const message = `Nom local enregistré : « ${normalizedLabel} ».`;
                notice = renderNotice([message], 'success');
                root.dispatchEvent(new CustomEvent('learnit:library-changed', { detail: { reason: 'rename' } }));
                await renderLibrary({
                  focus: false,
                  announcement: message,
                  focusCourseInstallId: course.courseInstallId,
                });
              },
            );
          });
          input.addEventListener('keydown', event => {
            if (event.key !== 'Escape') return;
            event.preventDefault();
            restoreTitle();
            announce('Renommage annulé.');
          });
          settingsDetails.open = false;
          titleSlot.replaceChildren(form);
          queueMicrotask(() => {
            input.focus();
            input.select();
          });
        }

        settingsSummary = node('summary', { 'aria-label': `Options du cours ${course.title}` }, [
          node('span', { 'aria-hidden': 'true', text: '⋯' }),
          node('span', { className: 'sr-only', text: 'Options du cours' }),
        ]);
        settingsDetails = node('details', { className: 'course-settings-details' }, [
          settingsSummary,
          node('div', { className: 'course-settings-menu' }, [
            node('button', {
              type: 'button',
              className: 'quiet',
              text: 'Renommer',
              onclick: beginRename,
            }),
          ]),
        ]);

        const externalSummary = renderExternalLearningProjection(externalProjection);
        const learningUnavailable = !learningAvailable
          ? node('p', {
            className: 'course-learning-unavailable',
            role: 'status',
            text: 'Progression temporairement indisponible. La bibliothèque reste accessible.',
          })
          : null;
        const restStatus = externalProjection && !externalProjection.sessionAvailableNow
          ? node('p', {
            className: 'atlas-rest-status',
            role: 'status',
            'data-atlas-rest-status': 'true',
            text: 'À jour pour aujourd’hui',
          })
          : null;
        const durationControl = durationSelect
          ? node('label', { className: 'library-duration-control' }, [
            node('span', { className: 'sr-only', text: `Durée pour ${course.title}` }),
            durationSelect,
          ])
          : null;

        const article = node('article', {
          className: 'course-card course-list-row learner-course-card',
          'data-course-install-id': course.courseInstallId,
        }, [
          node('div', { className: 'course-row-main' }, [
            titleSlot,
            node('p', { className: 'course-meta', text: `${course.activityCount} activités · ${course.estimatedMinutes} min estimées au total` }),
            externalSummary,
            learningUnavailable,
          ]),
          objectiveDetails,
          completionGuidance,
          node('div', { className: 'course-row-actions learner-course-actions' }, [
            restStatus,
            reviewAction,
            durationControl,
            courseAction,
            settingsDetails,
          ]),
        ]);
        if (focusCourseInstallId === course.courseInstallId) requestedCourseFocusTarget = titleHeading;
        courseEntries.push({
          article,
          searchable: [
            course.title,
            course.canonicalTitle ?? '',
            course.subtitle ?? '',
            ...(externalProjection?.objectiveStates ?? course.objectives ?? []).map(item => item.label ?? ''),
          ],
        });
        list.append(article);
      }
      section.append(list);
      section.append(node('details', { className: 'library-management' }, [
        node('summary', { text: 'Gérer la bibliothèque' }),
        node('div', { className: 'library-management-body' }, [
          node('h3', { text: 'Ajouter un cours' }),
          importForm,
          node('div', { className: 'library-reset-zone' }, [
            node('h3', { text: 'Données locales' }),
            renderResetAction(),
          ]),
        ]),
      ]));
    }
    if (renderEpoch !== libraryRenderEpoch) return;
    shell(section, { focusTarget: requestedCourseFocusTarget ?? (focus ? libraryTitle : null), announcement });
  }
  async function submitAnswer(activityRevisionId, answer) {
    await run(() => runtime.answer(activityRevisionId, answer), async (result) => {
      if (result.scored !== true) {
        if (result.nextActivity) {
          const nextSession = await runtime.getSession();
          renderSessionSnapshot(nextSession, { focus: false });
          announce('Activité suivante.');
        } else {
          await renderLibrary({ focus: false, announcement: 'Parcours d’activités terminé. Consultez vos objectifs dans la bibliothèque.' });
        }
        return;
      }
      renderFeedback(result);
    });
  }

  function renderSessionSnapshot(session, { focus = true } = {}) {
    currentView = 'session';
    navigation.setActiveView('session');
    setViewElementVisible(root.querySelector('[data-atlas-int-surface]'), false);
    setViewElementVisible(main, true);
    if (!session || !session.currentActivity) {
      const message = session?.mode === 'review'
        ? 'La file À revoir est vide. Consultez vos objectifs dans la bibliothèque.'
        : 'Parcours d’activités terminé. Consultez vos objectifs dans la bibliothèque.';
      notice = renderNotice([message], 'success');
      return renderLibrary({ announcement: message });
    }
    const activity = session.currentActivity;
    const reviewMode = session.mode === 'review';
    const total = Number(session.progress?.total ?? 0);
    const completed = Number(session.progress?.completed ?? 0);
    const currentPosition = total > 0 ? Math.min(completed + 1, total) : 1;
    const activityTitle = node('h2', {
      id: 'activity-title',
      className: 'sr-only',
      text: reviewMode ? 'Activité à renforcer' : 'Activité en cours',
    });
    const section = node('section', { 'aria-labelledby': 'activity-title', className: 'session-panel learner-session-panel' }, [
      node('button', { type: 'button', className: 'back-link', text: '← Bibliothèque', onclick: () => renderLibrary() }),
      node('div', { className: 'activity-context-row' }, [
        node('p', { className: 'eyebrow', text: reviewMode ? `${session.title} · À revoir` : session.title }),
        node('p', { className: 'activity-position', text: `${currentPosition}/${total || 1} activités` }),
      ]),
      activityTitle,
      renderServedActivityForm(
        activity,
        (answer) => submitAnswer(activity.activityRevisionId, answer),
      ),
    ]);
    shell(section);
  }

  function renderFeedbackLines(title, lines, className) {
    if (!Array.isArray(lines) || lines.length === 0) return null;
    return node('section', { className }, [
      node('h3', { text: title }),
      node('div', { className: 'feedback-lines' },
        lines.map(line => node('p', { className: 'feedback-line', text: line }))),
    ]);
  }

  function renderFeedbackComparison(rows, includeExpected) {
    if (!Array.isArray(rows) || rows.length === 0) return null;
    const headers = [
      node('th', { scope: 'col', text: 'Élément' }),
      node('th', { scope: 'col', text: 'Votre réponse' }),
      includeExpected ? node('th', { scope: 'col', text: 'Attendu' }) : null,
    ];
    const bodyRows = rows.map(row => node('tr', {}, [
      node('th', { scope: 'row', text: row.item }),
      node('td', { text: row.learner }),
      includeExpected ? node('td', { text: row.expected }) : null,
    ]));
    return node('section', { className: 'feedback-comparison' }, [
      node('h3', { text: 'Correspondances' }),
      node('div', { className: 'feedback-comparison-scroll' }, [
        node('table', {}, [
          node('thead', {}, [node('tr', {}, headers)]),
          node('tbody', {}, bodyRows),
        ]),
      ]),
    ]);
  }

  function renderSessionSummary(result) {
    const title = node('h2', {
      id: 'session-summary-title',
      tabindex: '-1',
      text: 'Bilan de la séance',
    });
    const objectiveSurface = result.sessionDelta?.available === true
      ? renderObjectiveSurface(objectiveUi, {
        context: 'terminal-summary',
        courseObjectives: result.courseObjectives,
        progress: result.progress,
        sessionDelta: result.sessionDelta,
      })
      : null;
    const worked = result.sessionDelta?.available === true
      ? result.sessionDelta.workedObjectiveIds.length
      : 0;
    const changed = result.sessionDelta?.available === true
      ? result.sessionDelta.changedObjectiveIds.length
      : 0;
    const summary = result.sessionDelta?.available === true
      ? node('p', {
        className: 'session-summary-intro',
        text: `Cette séance a travaillé ${worked} objectif${worked > 1 ? 's' : ''} ; ${changed} changement${changed > 1 ? 's' : ''} d’état ${changed > 1 ? 'sont' : 'est'} enregistré${changed > 1 ? 's' : ''}.`,
      })
      : node('p', {
        className: 'session-summary-intro',
        text: 'Le détail avant/après de cette séance n’est pas disponible.',
      });
    const section = node('section', {
      'aria-labelledby': 'session-summary-title',
      className: 'session-summary-panel',
      'data-session-summary': 'true',
    }, [
      title,
      summary,
      objectiveSurface,
      node('button', {
        type: 'button',
        className: 'primary',
        text: 'Retour à la bibliothèque',
        onclick: () => renderLibrary(),
      }),
    ]);
    shell(section, { focusTarget: title, announcement: 'Bilan de la séance' });
  }

  function renderFeedback(result) {
    const reviewMode = result.mode === 'review';
    const reviewRemaining = result.review?.remaining ?? 0;
    const complete = result.progress.isComplete;
    const terminal = reviewMode ? reviewRemaining === 0 : complete === true;
    const outcomeText = result.correct ? 'Bonne réponse' : 'À corriger';
    const feedbackProjection = result.postAnswerFeedback ?? null;
    const feedbackTitle = node('h2', {
      id: 'feedback-title',
      className: result.correct ? 'feedback-correct' : 'feedback-incorrect',
      text: outcomeText,
    });
    const comparison = feedbackProjection?.comparisonRows
      ? renderFeedbackComparison(feedbackProjection.comparisonRows, !result.correct)
      : null;
    const learnerAnswer = feedbackProjection && !comparison
      ? renderFeedbackLines('Votre réponse', feedbackProjection.learnerAnswer, 'feedback-answer feedback-learner-answer')
      : null;
    const expectedAnswer = feedbackProjection && !comparison && !result.correct
      ? renderFeedbackLines('Réponse attendue', feedbackProjection.expectedAnswer, 'feedback-answer feedback-expected-answer')
      : null;
    const explanation = result.explanation
      ? node('section', { className: 'feedback-explanation' }, [
        node('h3', { text: 'Explication' }),
        node('p', { text: result.explanation }),
      ])
      : null;
    const feedbackMedia =
      Array.isArray(result.feedbackMedia)
      && result.feedbackMedia.length
        ? node(
          'div',
          {
            className: 'activity-feedback-media',
            'data-activity-feedback-media': 'post-transition',
          },
          [renderEmbeddedMediaSet(result.feedbackMedia)],
        )
        : null;
    const primaryAction = terminal
      ? node('button', {
        type: 'button',
        className: 'primary',
        'data-served-next-action': 'true',
        text: 'Voir le bilan de la séance',
        onclick: () => renderSessionSummary(result),
      })
      : reviewMode
        ? node('button', {
          type: 'button',
          className: 'primary',
          'data-served-next-action': 'true',
          text: 'Activité suivante à revoir',
          onclick: () => run(() => runtime.getSession(), renderSessionSnapshot),
        })
        : node('button', {
          type: 'button',
          className: 'primary',
          'data-served-next-action': 'true',
          text: 'Activité suivante',
          onclick: () => run(() => runtime.getSession(), renderSessionSnapshot),
        });
    const section = node('section', {
      'aria-labelledby': 'feedback-title',
      className: 'feedback-panel learner-feedback-panel',
      'data-served-feedback': 'scored',
    }, [
      feedbackTitle,
      comparison,
      learnerAnswer,
      expectedAnswer,
      explanation,
      ...(feedbackMedia ? [feedbackMedia] : []),
      primaryAction,
    ]);
    shell(section, { focusTarget: feedbackTitle, announcement: outcomeText });
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
