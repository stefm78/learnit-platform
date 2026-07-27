const STATUS_PRESENTATION = Object.freeze({
  'not-started': Object.freeze({
    label: 'À commencer',
    description: 'Aucune activité enregistrée pour cet objectif.',
    className: 'objective-progress__item--not-started',
  }),
  training: Object.freeze({
    label: 'En entraînement',
    description: 'Des activités d’entraînement ont été réalisées pour cet objectif.',
    className: 'objective-progress__item--training',
  }),
  'review-needed': Object.freeze({
    label: 'Révision nécessaire',
    description: 'Une activité doit être reprise avant de poursuivre vers la validation.',
    className: 'objective-progress__item--review-needed',
  }),
  'ready-for-validation': Object.freeze({
    label: 'Prêt pour validation',
    description: 'L’entraînement est à jour et une activité de validation peut être proposée.',
    className: 'objective-progress__item--ready-for-validation',
  }),
  'validated-recently': Object.freeze({
    label: 'Validation récente',
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

export function renderObjectiveProgressPanel(data, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new TypeError('Le panneau de progression doit recevoir un objet data.');
  }
  const panel = element(documentRef, 'div', { className: 'objective-progress-panel' });
  append(panel,
    renderObjectiveProgressList(data.objectives ?? [], {
      documentRef,
      idPrefix: options.idPrefix,
      labelsById: options.labelsById,
      title: options.objectivesTitle,
      emptyMessage: options.objectivesEmptyMessage,
      headingLevel: options.headingLevel ?? 2,
    }),
    renderRecommendedAction(data.recommendation ?? null, {
      documentRef,
      idPrefix: `${options.idPrefix ?? 'learning-loop'}-next`,
      labelsById: options.labelsById,
      title: options.recommendationTitle,
      emptyMessage: options.recommendationEmptyMessage,
      headingLevel: options.headingLevel ?? 2,
      onAction: options.onAction,
    }),
  );
  return panel;
}
