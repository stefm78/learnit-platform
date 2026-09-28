const STATUS_PRESENTATION = Object.freeze({
  'not-started': Object.freeze({
    label: 'À découvrir',
    description: 'Aucune activité enregistrée pour cet objectif.',
    className: 'objective-progress__item--not-started',
  }),
  training: Object.freeze({
    label: 'En apprentissage',
    description: 'Des activités d’entraînement ont été réalisées pour cet objectif.',
    className: 'objective-progress__item--training',
  }),
  'review-needed': Object.freeze({
    label: 'À renforcer',
    description: 'Une activité doit être reprise avant de poursuivre vers la validation.',
    className: 'objective-progress__item--review-needed',
  }),
  'ready-for-validation': Object.freeze({
    label: 'À confirmer',
    description: 'L’entraînement est à jour ; cet objectif doit encore être confirmé par une validation distincte.',
    className: 'objective-progress__item--ready-for-validation',
  }),
  'validated-recently': Object.freeze({
    label: 'Acquis récemment',
    description: 'Une activité de validation a été réussie récemment.',
    className: 'objective-progress__item--validated-recently',
  }),
});

export const OBJECTIVE_PROGRESS_STATUSES = Object.freeze(Object.keys(STATUS_PRESENTATION));

function requireDocument(documentRef) {
  if (!documentRef || typeof documentRef.createElement !== 'function') {
    throw new TypeError('Un document DOM est requis pour générer la présentation.');
  }
  return documentRef;
}

function nonNegativeInteger(value, fieldName) {
  if (!Number.isInteger(value) || value < 0) {
    throw new TypeError(`${fieldName} doit être un entier positif ou nul.`);
  }
  return value;
}

function optionalBoolean(value, fieldName) {
  if (value !== null && value !== undefined && typeof value !== 'boolean') {
    throw new TypeError(`${fieldName} doit être un booléen ou null.`);
  }
  return value ?? null;
}

function requiredText(value, fieldName) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new TypeError(`${fieldName} doit être une chaîne non vide.`);
  }
  return value.trim();
}

function optionalText(value, fieldName) {
  if (value === null || value === undefined) return null;
  return requiredText(value, fieldName);
}

function statusPresentation(status) {
  const presentation = STATUS_PRESENTATION[status];
  if (!presentation) throw new RangeError(`État de progression non pris en charge : ${String(status)}`);
  return presentation;
}

function headingTag(level) {
  if (!Number.isInteger(level) || level < 2 || level > 6) {
    throw new RangeError('Le niveau de titre doit être compris entre 2 et 6.');
  }
  return `h${level}`;
}

function safeFragment(value) {
  const fragment = String(value)
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase();
  return fragment || 'objectif';
}

function append(parent, ...children) {
  for (const child of children.flat()) {
    if (child !== null && child !== undefined) parent.appendChild(child);
  }
}

function element(documentRef, tag, attributes = {}, children = []) {
  const node = documentRef.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined) continue;
    if (name === 'className') node.className = value;
    else if (name === 'text') node.textContent = String(value);
    else node.setAttribute(name, String(value));
  }
  append(node, children);
  return node;
}

function resultLabel(attempts, result, positiveLabel) {
  if (attempts === 0 || result === null) return 'Aucun résultat';
  return result ? positiveLabel : 'À reprendre';
}

function definitionPair(documentRef, term, value) {
  return [
    element(documentRef, 'dt', { text: term }),
    element(documentRef, 'dd', { text: value }),
  ];
}

function normalizeObjective(objective) {
  if (!objective || typeof objective !== 'object' || Array.isArray(objective)) {
    throw new TypeError('La progression d’objectif doit être un objet data.');
  }
  const objectiveId = requiredText(objective.objectiveId, 'objectiveId');
  const trainingAttempts = nonNegativeInteger(objective.trainingAttempts, 'trainingAttempts');
  const validationAttempts = nonNegativeInteger(objective.validationAttempts, 'validationAttempts');
  const latestTrainingCorrect = optionalBoolean(objective.latestTrainingCorrect, 'latestTrainingCorrect');
  const latestValidationCorrect = optionalBoolean(objective.latestValidationCorrect, 'latestValidationCorrect');
  if (typeof objective.needsReview !== 'boolean') throw new TypeError('needsReview doit être un booléen.');
  statusPresentation(objective.status);
  return {
    objectiveId,
    trainingAttempts,
    latestTrainingCorrect,
    needsReview: objective.needsReview,
    validationAttempts,
    latestValidationCorrect,
    status: objective.status,
  };
}

function labelFromMap(labelsById, objectiveId) {
  if (labelsById instanceof Map) return labelsById.get(objectiveId) ?? objectiveId;
  if (labelsById && typeof labelsById === 'object') return labelsById[objectiveId] ?? objectiveId;
  return objectiveId;
}

export function getObjectiveStatusPresentation(status) {
  return statusPresentation(status);
}

export function renderObjectiveProgressItem(objective, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  const data = normalizeObjective(objective);
  const presentation = statusPresentation(data.status);
  const index = Number.isInteger(options.index) && options.index >= 0 ? options.index : 0;
  const idPrefix = safeFragment(options.idPrefix ?? 'learning-loop');
  const itemId = `${idPrefix}-objective-${safeFragment(data.objectiveId)}-${index}`;
  const titleId = `${itemId}-title`;
  const descriptionId = `${itemId}-description`;
  const label = requiredText(options.label ?? data.objectiveId, 'label');
  const title = element(documentRef, headingTag(options.headingLevel ?? 3), {
    id: titleId,
    className: 'objective-progress__title',
    text: label,
  });
  const status = element(documentRef, 'p', {
    className: 'objective-progress__status',
  }, [
    element(documentRef, 'span', { className: 'objective-progress__status-prefix', text: 'État : ' }),
    element(documentRef, 'strong', { text: presentation.label }),
  ]);
  const description = element(documentRef, 'p', {
    id: descriptionId,
    className: 'objective-progress__description',
    text: presentation.description,
  });
  const facts = element(documentRef, 'dl', { className: 'objective-progress__facts' }, [
    ...definitionPair(documentRef, 'Entraînements', String(data.trainingAttempts)),
    ...definitionPair(
      documentRef,
      'Dernier entraînement',
      resultLabel(data.trainingAttempts, data.latestTrainingCorrect, 'Correct'),
    ),
    ...definitionPair(documentRef, 'Révision à effectuer', data.needsReview ? 'Oui' : 'Non'),
    ...definitionPair(documentRef, 'Validations', String(data.validationAttempts)),
    ...definitionPair(
      documentRef,
      'Dernière validation',
      resultLabel(data.validationAttempts, data.latestValidationCorrect, 'Réussie'),
    ),
  ]);
  return element(documentRef, 'article', {
    id: itemId,
    className: `objective-progress__item ${presentation.className}`,
    'data-objective-id': data.objectiveId,
    'data-progress-status': data.status,
    'aria-labelledby': titleId,
    'aria-describedby': descriptionId,
  }, [title, status, description, facts]);
}

export function renderObjectiveProgressList(objectives, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  if (!Array.isArray(objectives)) throw new TypeError('objectives doit être un tableau.');
  const idPrefix = safeFragment(options.idPrefix ?? 'learning-loop');
  const titleId = `${idPrefix}-objectives-title`;
  const section = element(documentRef, 'section', {
    className: 'objective-progress',
    'aria-labelledby': titleId,
  });
  section.appendChild(element(documentRef, headingTag(options.headingLevel ?? 2), {
    id: titleId,
    className: 'objective-progress__heading',
    text: options.title ?? 'Progression par objectif',
  }));
  if (objectives.length === 0) {
    section.appendChild(element(documentRef, 'p', {
      className: 'objective-progress__empty',
      role: 'status',
      text: options.emptyMessage ?? 'Aucun objectif à afficher pour le moment.',
    }));
    return section;
  }
  const list = element(documentRef, 'ol', { className: 'objective-progress__list' });
  objectives.forEach((objective, index) => {
    const label = labelFromMap(options.labelsById, objective?.objectiveId);
    const item = element(documentRef, 'li', { className: 'objective-progress__list-item' }, [
      renderObjectiveProgressItem(objective, {
        documentRef,
        idPrefix,
        index,
        label,
        headingLevel: Math.min((options.headingLevel ?? 2) + 1, 6),
      }),
    ]);
    list.appendChild(item);
  });
  section.appendChild(list);
  return section;
}

function normalizeRecommendation(recommendation) {
  if (!recommendation || typeof recommendation !== 'object' || Array.isArray(recommendation)) {
    throw new TypeError('La recommandation doit être un objet data.');
  }
  const normalized = {
    title: requiredText(recommendation.title, 'recommendation.title'),
    description: requiredText(recommendation.description, 'recommendation.description'),
    actionLabel: optionalText(recommendation.actionLabel, 'recommendation.actionLabel'),
    actionKey: optionalText(recommendation.actionKey, 'recommendation.actionKey'),
    href: optionalText(recommendation.href, 'recommendation.href'),
    objectiveId: optionalText(recommendation.objectiveId, 'recommendation.objectiveId'),
    status: recommendation.status ?? null,
  };
  if (normalized.status !== null) statusPresentation(normalized.status);
  return normalized;
}

export function renderRecommendedAction(recommendation, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  const idPrefix = safeFragment(options.idPrefix ?? 'learning-loop');
  const titleId = `${idPrefix}-recommendation-title`;
  const section = element(documentRef, 'section', {
    className: 'objective-recommendation',
    'aria-labelledby': titleId,
  });
  section.appendChild(element(documentRef, headingTag(options.headingLevel ?? 2), {
    id: titleId,
    className: 'objective-recommendation__heading',
    text: options.title ?? 'Prochaine action recommandée',
  }));
  if (recommendation === null || recommendation === undefined) {
    section.appendChild(element(documentRef, 'p', {
      className: 'objective-recommendation__empty',
      role: 'status',
      text: options.emptyMessage ?? 'Aucune action recommandée pour le moment.',
    }));
    return section;
  }
  const data = normalizeRecommendation(recommendation);
  const content = element(documentRef, 'div', {
    className: 'objective-recommendation__content',
    'data-action-key': data.actionKey,
    'data-objective-id': data.objectiveId,
    'data-progress-status': data.status,
  });
  if (data.objectiveId) {
    const objectiveLabel = labelFromMap(options.labelsById, data.objectiveId);
    content.appendChild(element(documentRef, 'p', {
      className: 'objective-recommendation__context',
      text: `Objectif : ${objectiveLabel}`,
    }));
  }
  append(content,
    element(documentRef, headingTag(Math.min((options.headingLevel ?? 2) + 1, 6)), {
      className: 'objective-recommendation__title',
      text: data.title,
    }),
    element(documentRef, 'p', {
      className: 'objective-recommendation__description',
      text: data.description,
    }),
  );
  if (data.actionLabel && data.href) {
    content.appendChild(element(documentRef, 'a', {
      className: 'objective-recommendation__action primary',
      href: data.href,
      text: data.actionLabel,
    }));
  } else if (data.actionLabel && typeof options.onAction === 'function') {
    const button = element(documentRef, 'button', {
      className: 'objective-recommendation__action primary',
      type: 'button',
      text: data.actionLabel,
    });
    button.addEventListener('click', () => options.onAction(recommendation));
    content.appendChild(button);
  } else if (data.actionLabel) {
    content.appendChild(element(documentRef, 'p', {
      className: 'objective-recommendation__action-label',
      text: data.actionLabel,
    }));
  }
  section.appendChild(content);
  return section;
}

const R15_VISUAL_LEVEL = Object.freeze({
  'not-started': '0%',
  training: '48%',
  'review-needed': '46%',
  'ready-for-validation': '82%',
  'validated-recently': '100%',
});
const R15_STATE_MARK = Object.freeze({
  'not-started': null,
  training: null,
  'review-needed': '↺',
  'ready-for-validation': '◇',
  'validated-recently': '✓',
});

function renderR15ObjectiveProgress(data, options) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  const context = data.context ?? 'library';
  const labelsById = options.labelsById;
  const idPrefix = safeFragment(options.idPrefix ?? 'learning-loop');
  const delta = data.sessionDelta?.available === true ? data.sessionDelta : null;
  if (context === 'terminal-summary' && !delta) return null;
  const before = delta?.beforeObjectiveStates ?? {};
  const after = delta?.afterObjectiveStates ?? {};
  const worked = new Set(delta?.workedObjectiveIds ?? []);
  const changed = new Set(delta?.changedObjectiveIds ?? []);
  if (delta) {
    if (!delta.beforeObjectiveStates || !delta.afterObjectiveStates
      || !Array.isArray(delta.workedObjectiveIds) || !Array.isArray(delta.changedObjectiveIds)) {
      throw new TypeError('sessionDelta disponible mais incomplet.');
    }
    for (const state of [...Object.values(before), ...Object.values(after)]) statusPresentation(state);
  }
  const objectives = (data.objectives ?? []).map((raw) => {
    const objective = normalizeObjective(raw);
    const status = context === 'terminal-summary' && Object.hasOwn(after, objective.objectiveId)
      ? after[objective.objectiveId] : objective.status;
    statusPresentation(status);
    return {...objective, status, label: requiredText(labelFromMap(labelsById, objective.objectiveId), 'label')};
  });
  const requestedPriority = context === 'library'
    ? optionalText(data.recommendation?.objectiveId, 'recommendation.objectiveId') : null;
  const priority = requestedPriority && objectives.some(item => item.objectiveId === requestedPriority)
    ? requestedPriority : null;
  const allAcquired = objectives.length > 0 && objectives.every(item => item.status === 'validated-recently');

  const detailId = `${idPrefix}-r15-selected-objective-detail`;
  const detailState = element(documentRef, 'strong', {className: 'objective-progress-r15__detail-state'});
  const detailLabel = element(documentRef, 'span', {className: 'objective-progress-r15__detail-label'});
  const detail = element(documentRef, 'div', {
    id: detailId,
    className: 'objective-progress-r15__detail',
    'data-objective-progress-r15-detail': 'true',
    'aria-live': 'polite',
    hidden: true,
  }, [detailState, detailLabel]);
  let selectedReservoir = null;
  const renderDetail = (item) => {
    detail.hidden = false;
    detailState.textContent = statusPresentation(item.status).label;
    if (context !== 'terminal-summary' || !worked.has(item.objectiveId)) {
      detailLabel.textContent = item.label;
    } else if (changed.has(item.objectiveId)) {
      const oldState = before[item.objectiveId];
      const newState = after[item.objectiveId];
      if (!oldState || !newState) throw new TypeError('sessionDelta changed incomplet.');
      detailLabel.textContent = `${item.label} · Cette séance : ${statusPresentation(oldState).label} → ${statusPresentation(newState).label}`;
    } else {
      detailLabel.textContent = `${item.label} · Travaillé pendant cette séance, état inchangé`;
    }
  };
  const clearDetail = () => {
    selectedReservoir = null;
    detail.hidden = true;
    for (const reservoir of reservoirs.querySelectorAll('[data-objective-progress-r15-objective]')) {
      reservoir.setAttribute('aria-pressed', 'false');
      reservoir.setAttribute('aria-expanded', 'false');
      reservoir.setAttribute('data-objective-progress-r15-selected', 'false');
    }
  };
  const selectDetail = (item, reservoirToSelect) => {
    selectedReservoir = reservoirToSelect;
    for (const reservoir of reservoirs.querySelectorAll('[data-objective-progress-r15-objective]')) {
      const selected = reservoir === reservoirToSelect;
      reservoir.setAttribute('aria-pressed', String(selected));
      reservoir.setAttribute('aria-expanded', String(selected));
      reservoir.setAttribute('data-objective-progress-r15-selected', String(selected));
    }
    renderDetail(item);
  };

  const reservoirs = element(documentRef, 'div', {
    className: 'objective-progress-r15__reservoirs',
    role: 'group',
    'aria-label': `${objectives.length} objectifs du cours`,
  });
  objectives.forEach((item, index) => {
    const presentation = statusPresentation(item.status);
    const isPriority = priority === item.objectiveId;
    const wasWorked = context === 'terminal-summary' && worked.has(item.objectiveId);
    const didChange = context === 'terminal-summary' && changed.has(item.objectiveId);
    const aria = [
      `${item.label}. ${presentation.label}.`,
      isPriority ? 'Objectif proposé en priorité' : null,
      wasWorked ? 'Travaillé pendant cette séance' : null,
      didChange ? 'État modifié pendant cette séance' : null,
    ].filter(Boolean).join('. ');
    const reservoir = element(documentRef, 'button', {
      id: `${idPrefix}-r15-${safeFragment(item.objectiveId)}-${index}`,
      type: 'button',
      className: `objective-progress-r15__reservoir objective-progress-r15__reservoir--${item.status}`,
      'data-objective-progress-r15-objective': item.objectiveId,
      'data-objective-progress-r15-state': item.status,
      'data-objective-progress-r15-priority': String(isPriority),
      'data-objective-progress-r15-session-worked': String(wasWorked),
      'data-objective-progress-r15-session-changed': String(didChange),
      'data-objective-progress-r15-selected': 'false',
      'aria-label': aria,
      'aria-pressed': 'false',
      'aria-expanded': 'false',
      'aria-controls': detailId,
      title: `${item.label} — ${presentation.label}`,
    }, [
      element(documentRef, 'span', {
        className: 'objective-progress-r15__fill',
        'aria-hidden': 'true',
        style: `--objective-progress-r15-level:${R15_VISUAL_LEVEL[item.status]}`,
      }),
      R15_STATE_MARK[item.status] ? element(documentRef, 'span', {
        className: 'objective-progress-r15__state-mark',
        'aria-hidden': 'true',
        text: R15_STATE_MARK[item.status],
      }) : null,
    ]);
    reservoir.addEventListener('click', () => {
      if (selectedReservoir === reservoir) clearDetail();
      else selectDetail(item, reservoir);
    });
    reservoir.addEventListener('focus', () => {
      if (selectedReservoir === null) renderDetail(item);
    });
    reservoirs.appendChild(reservoir);
  });
  const group = element(documentRef, 'div', {
    className: `objective-progress-r15__group${allAcquired ? ' objective-progress-r15__group--consolidated' : ''}`,
    'data-objective-progress-r15-group': 'objectifs-du-cours',
    'data-objective-progress-r15-consolidated': String(allAcquired),
  }, [
    element(documentRef, 'span', {className: 'objective-progress-r15__group-label', text: 'Objectifs du cours'}),
    reservoirs,
    detail,
  ]);
  const children = [group];
  if (context === 'terminal-summary') {
    const workedCount = delta.workedObjectiveIds.length;
    const changedCount = delta.changedObjectiveIds.length;
    children.push(element(documentRef, 'div', {
      className: 'objective-progress-r15__context objective-progress-r15__session-context',
      'data-objective-progress-r15-session-context': 'true',
    }, [
      element(documentRef, 'span', {className: 'objective-progress-r15__context-kicker', text: 'Cette séance'}),
      element(documentRef, 'strong', {
        className: 'objective-progress-r15__context-state',
        text: `${workedCount} objectif${workedCount > 1 ? 's' : ''} travaillé${workedCount > 1 ? 's' : ''}`,
      }),
      element(documentRef, 'span', {
        className: 'objective-progress-r15__context-target',
        text: changedCount
          ? `${changedCount} changement${changedCount > 1 ? 's' : ''} d’état visible${changedCount > 1 ? 's' : ''}`
          : 'État global inchangé',
      }),
    ]));
  } else if (priority) {
    const target = objectives.find(item => item.objectiveId === priority);
    children.push(element(documentRef, 'div', {
      className: 'objective-progress-r15__context objective-progress-r15__priority-context',
      'data-objective-progress-r15-priority-context': 'true',
    }, [
      element(documentRef, 'strong', {className: 'objective-progress-r15__context-state', text: statusPresentation(target.status).label}),
      element(documentRef, 'span', {className: 'objective-progress-r15__context-target', text: target.label}),
    ]));
  }
  return element(documentRef, 'section', {
    className: `objective-progress-r15 objective-progress-r15--${context}`,
    'data-objective-progress-r15': 'true',
    'data-objective-progress-r15-context': context,
    'aria-label': context === 'terminal-summary' ? 'Bilan de progression de cette séance' : 'Progression détaillée par objectif',
  }, children);
}

export function renderObjectiveProgressPanel(data, options = {}) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new TypeError('Le panneau de progression doit recevoir un objet data.');
  }
  return renderR15ObjectiveProgress(data, options);
}
