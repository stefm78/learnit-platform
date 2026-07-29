const REASON_PRESENTATION = Object.freeze({
  NEW_OBJECTIVE: Object.freeze({
    label: 'Nouvel objectif',
    explanation: 'Aucune preuve n’est encore enregistrée pour cet objectif.',
  }),
  PRACTICE_IN_PROGRESS: Object.freeze({
    label: 'Entraînement commencé',
    explanation: 'Un entraînement est en cours et peut être poursuivi.',
  }),
  RECENT_ERROR: Object.freeze({
    label: 'Erreur récente',
    explanation: 'Une tentative récente demande une reprise ciblée.',
  }),
  REVIEW_REQUIRED: Object.freeze({
    label: 'Correction nécessaire',
    explanation: 'Une correction doit être terminée avant de poursuivre.',
  }),
  CORRECTION_COMPLETED: Object.freeze({
    label: 'Correction terminée',
    explanation: 'L’erreur a été corrigée sans compter comme une validation.',
  }),
  NO_INDEPENDENT_VALIDATION: Object.freeze({
    label: 'Validation distincte absente',
    explanation: 'Aucune validation indépendante réussie n’est encore disponible.',
  }),
  VALIDATION_AVAILABLE: Object.freeze({
    label: 'Validation disponible',
    explanation: 'Les conditions locales sont réunies pour proposer une validation distincte.',
  }),
  RECENTLY_VALIDATED: Object.freeze({
    label: 'Validation récente',
    explanation: 'Une validation récente peut être entretenue sans conclusion au-delà des preuves observées.',
  }),
  SESSION_TIME_LIMIT: Object.freeze({
    label: 'Temps disponible',
    explanation: 'La durée choisie limite les actions proposées dans cette séance.',
  }),
});

const ACTION_PRESENTATION = Object.freeze({
  'start-practice': Object.freeze({
    label: 'Commencer l’entraînement',
    phase: 'practice',
  }),
  'continue-practice': Object.freeze({
    label: 'Continuer l’entraînement',
    phase: 'practice',
  }),
  'correct-practice': Object.freeze({
    label: 'Corriger une erreur',
    phase: 'correction',
  }),
  'attempt-validation': Object.freeze({
    label: 'Faire une validation distincte',
    phase: 'validation',
  }),
  'maintain-recent-validation': Object.freeze({
    label: 'Entretenir une validation récente',
    phase: 'maintenance',
  }),
});

export const ATLAS_DURATION_OPTIONS = Object.freeze([5, 15, 30]);
export const ATLAS_REASON_CODES = Object.freeze(Object.keys(REASON_PRESENTATION));
export const ATLAS_RECOMMENDATION_ACTIONS = Object.freeze(Object.keys(ACTION_PRESENTATION));

function requireDocument(documentRef) {
  if (!documentRef || typeof documentRef.createElement !== 'function') {
    throw new TypeError('Un document DOM est requis pour générer la présentation Atlas.');
  }
  return documentRef;
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

function nonNegativeInteger(value, fieldName) {
  if (!Number.isInteger(value) || value < 0) {
    throw new TypeError(`${fieldName} doit être un entier positif ou nul.`);
  }
  return value;
}

function positiveInteger(value, fieldName) {
  if (!Number.isInteger(value) || value <= 0) {
    throw new TypeError(`${fieldName} doit être un entier strictement positif.`);
  }
  return value;
}

function append(parent, ...children) {
  for (const child of children.flat()) {
    if (child !== null && child !== undefined) parent.appendChild(child);
  }
}

export function atlasElement(documentRef, tag, attributes = {}, children = []) {
  const node = documentRef.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined) continue;
    if (name === 'className') node.className = String(value);
    else if (name === 'text') node.textContent = String(value);
    else if (name === 'disabled') node.disabled = Boolean(value);
    else node.setAttribute(name, String(value));
  }
  append(node, children);
  return node;
}

function safeFragment(value) {
  const fragment = String(value)
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase();
  return fragment || 'atlas';
}

function labelFromMap(labelsById, identifier) {
  if (labelsById instanceof Map) return labelsById.get(identifier) ?? identifier;
  if (labelsById && typeof labelsById === 'object' && !Array.isArray(labelsById)) {
    return labelsById[identifier] ?? identifier;
  }
  return identifier;
}

function normalizeReasonCodes(reasonCodes, fieldName = 'reasonCodes') {
  if (!Array.isArray(reasonCodes) || reasonCodes.length === 0) {
    throw new TypeError(`${fieldName} doit être un tableau non vide.`);
  }
  const normalized = reasonCodes.map((code, index) => requiredText(code, `${fieldName}[${index}]`));
  if (new Set(normalized).size !== normalized.length) {
    throw new TypeError(`${fieldName} ne doit pas contenir de doublon.`);
  }
  for (const code of normalized) {
    if (!Object.hasOwn(REASON_PRESENTATION, code)) {
      throw new RangeError(`reasonCode Atlas M1 non pris en charge : ${code}`);
    }
  }
  return normalized;
}

function normalizeAction(action, fieldName = 'action') {
  const normalized = requiredText(action, fieldName);
  if (!Object.hasOwn(ACTION_PRESENTATION, normalized)) {
    throw new RangeError(`Action Atlas M1 non prise en charge : ${normalized}`);
  }
  return normalized;
}

function normalizeRecommendation(recommendation) {
  if (!recommendation || typeof recommendation !== 'object' || Array.isArray(recommendation)) {
    throw new TypeError('La recommandation Atlas doit être un objet data.');
  }
  const priority = Number(recommendation.priority);
  if (!Number.isFinite(priority)) throw new TypeError('recommendation.priority doit être un nombre fini.');
  if (!Array.isArray(recommendation.eligibleActivityIds)) {
    throw new TypeError('recommendation.eligibleActivityIds doit être un tableau.');
  }
  const eligibleActivityIds = recommendation.eligibleActivityIds.map((value, index) => (
    requiredText(value, `recommendation.eligibleActivityIds[${index}]`)
  ));
  if (new Set(eligibleActivityIds).size !== eligibleActivityIds.length) {
    throw new TypeError('recommendation.eligibleActivityIds ne doit pas contenir de doublon.');
  }
  return {
    recommendationVersion: positiveInteger(
      recommendation.recommendationVersion,
      'recommendation.recommendationVersion',
    ),
    objectiveId: requiredText(recommendation.objectiveId, 'recommendation.objectiveId'),
    action: normalizeAction(recommendation.action, 'recommendation.action'),
    priority,
    reasonCodes: normalizeReasonCodes(recommendation.reasonCodes, 'recommendation.reasonCodes'),
    estimatedMinutes: positiveInteger(
      recommendation.estimatedMinutes,
      'recommendation.estimatedMinutes',
    ),
    eligibleActivityIds,
  };
}

function normalizePlanItem(item, expectedPosition) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    throw new TypeError(`plan.items[${expectedPosition - 1}] doit être un objet data.`);
  }
  const position = positiveInteger(item.position, `plan.items[${expectedPosition - 1}].position`);
  if (position !== expectedPosition) {
    throw new TypeError('Les positions du plan doivent être continues et commencer à 1.');
  }
  return {
    position,
    objectiveId: requiredText(item.objectiveId, `plan.items[${expectedPosition - 1}].objectiveId`),
    activityLineageId: requiredText(
      item.activityLineageId,
      `plan.items[${expectedPosition - 1}].activityLineageId`,
    ),
    action: normalizeAction(item.action, `plan.items[${expectedPosition - 1}].action`),
    estimatedMinutes: positiveInteger(
      item.estimatedMinutes,
      `plan.items[${expectedPosition - 1}].estimatedMinutes`,
    ),
    reasonCodes: normalizeReasonCodes(
      item.reasonCodes,
      `plan.items[${expectedPosition - 1}].reasonCodes`,
    ),
  };
}

export function normalizeAtlasSessionPlan(plan) {
  if (!plan || typeof plan !== 'object' || Array.isArray(plan)) {
    throw new TypeError('Le SessionPlan doit être un objet data.');
  }
  const durationMinutes = positiveInteger(plan.durationMinutes, 'plan.durationMinutes');
  if (!ATLAS_DURATION_OPTIONS.includes(durationMinutes)) {
    throw new RangeError('plan.durationMinutes doit valoir 5, 15 ou 30.');
  }
  if (!Array.isArray(plan.items)) throw new TypeError('plan.items doit être un tableau.');
  const items = plan.items.map((item, index) => normalizePlanItem(item, index + 1));
  const unusedMinutes = nonNegativeInteger(plan.unusedMinutes, 'plan.unusedMinutes');
  const usedMinutes = items.reduce((total, item) => total + item.estimatedMinutes, 0);
  if (usedMinutes > durationMinutes || usedMinutes + unusedMinutes > durationMinutes) {
    throw new TypeError('La durée estimée du plan dépasse la durée choisie.');
  }
  return {
    planVersion: positiveInteger(plan.planVersion, 'plan.planVersion'),
    planId: requiredText(plan.planId, 'plan.planId'),
    generatedAt: requiredText(plan.generatedAt, 'plan.generatedAt'),
    durationMinutes,
    items,
    unusedMinutes,
  };
}

function normalizeResume(resumableSession) {
  if (resumableSession === null || resumableSession === undefined) return null;
  if (typeof resumableSession !== 'object' || Array.isArray(resumableSession)) {
    throw new TypeError('resumableSession doit être un objet data ou null.');
  }
  const completedItems = nonNegativeInteger(resumableSession.completedItems, 'resumableSession.completedItems');
  const totalItems = positiveInteger(resumableSession.totalItems, 'resumableSession.totalItems');
  if (completedItems >= totalItems) {
    throw new TypeError('Une séance reprenable doit avoir au moins une étape restante.');
  }
  return {
    sessionId: requiredText(resumableSession.sessionId, 'resumableSession.sessionId'),
    planId: requiredText(resumableSession.planId, 'resumableSession.planId'),
    completedItems,
    totalItems,
    objectiveId: optionalText(resumableSession.objectiveId, 'resumableSession.objectiveId'),
  };
}

export function getAtlasReasonPresentation(reasonCode) {
  const code = requiredText(reasonCode, 'reasonCode');
  const presentation = REASON_PRESENTATION[code];
  if (!presentation) throw new RangeError(`reasonCode Atlas M1 non pris en charge : ${code}`);
  return presentation;
}

export function getAtlasActionPresentation(action) {
  return ACTION_PRESENTATION[normalizeAction(action)];
}

export function renderAtlasReasonList(reasonCodes, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  const normalized = normalizeReasonCodes(reasonCodes);
  const list = atlasElement(documentRef, 'ul', {
    className: options.className ?? 'atlas-reasons',
    'aria-label': options.ariaLabel ?? 'Pourquoi cette proposition',
  });
  for (const code of normalized) {
    const presentation = getAtlasReasonPresentation(code);
    list.appendChild(atlasElement(documentRef, 'li', {
      className: 'atlas-reasons__item',
      'data-reason-code': code,
    }, [
      atlasElement(documentRef, 'strong', {
        className: 'atlas-reasons__label',
        text: presentation.label,
      }),
      atlasElement(documentRef, 'span', {
        className: 'atlas-reasons__explanation',
        text: presentation.explanation,
      }),
    ]));
  }
  return list;
}

function renderDurationChooser(documentRef, selectedDuration, onDurationChange) {
  const fieldset = atlasElement(documentRef, 'fieldset', {
    className: 'atlas-today__duration',
  }, [
    atlasElement(documentRef, 'legend', { text: 'Combien de temps avez-vous ?' }),
  ]);
  const controls = atlasElement(documentRef, 'div', {
    className: 'atlas-duration-options',
    role: 'group',
    'aria-label': 'Durée de la séance',
  });
  for (const duration of ATLAS_DURATION_OPTIONS) {
    const selected = duration === selectedDuration;
    const button = atlasElement(documentRef, 'button', {
      className: `atlas-duration-options__button${selected ? ' is-selected' : ''}`,
      type: 'button',
      'aria-pressed': selected ? 'true' : 'false',
      'data-duration-minutes': duration,
      text: `${duration} min`,
    });
    if (typeof onDurationChange === 'function') {
      button.addEventListener('click', () => onDurationChange(duration));
    }
    controls.appendChild(button);
  }
  fieldset.appendChild(controls);
  return fieldset;
}

function renderResumeCard(documentRef, resume, options) {
  if (!resume) return null;
  const titleId = `${safeFragment(options.idPrefix)}-resume-title`;
  const objectiveLabel = resume.objectiveId
    ? labelFromMap(options.objectiveLabelsById, resume.objectiveId)
    : null;
  const card = atlasElement(documentRef, 'article', {
    className: 'atlas-resume-card',
    'aria-labelledby': titleId,
    'data-session-id': resume.sessionId,
  }, [
    atlasElement(documentRef, 'p', { className: 'atlas-kicker', text: 'Séance interrompue' }),
    atlasElement(documentRef, 'h3', { id: titleId, text: 'Reprendre là où vous vous êtes arrêté' }),
    atlasElement(documentRef, 'p', {
      text: `${resume.completedItems} étape${resume.completedItems > 1 ? 's' : ''} sur ${resume.totalItems} terminée${resume.completedItems > 1 ? 's' : ''}.`,
    }),
  ]);
  if (objectiveLabel) {
    card.appendChild(atlasElement(documentRef, 'p', {
      className: 'atlas-resume-card__objective',
      text: `Prochain objectif : ${objectiveLabel}`,
    }));
  }
  const button = atlasElement(documentRef, 'button', {
    className: 'atlas-button atlas-button--primary',
    type: 'button',
    text: 'Reprendre la séance',
  });
  if (typeof options.onResume === 'function') {
    button.addEventListener('click', () => options.onResume({ ...resume }));
  }
  card.appendChild(button);
  return card;
}

function renderRecommendationCard(documentRef, recommendation, options) {
  const titleId = `${safeFragment(options.idPrefix)}-recommendation-title`;
  if (!recommendation) {
    return atlasElement(documentRef, 'section', {
      className: 'atlas-recommendation atlas-recommendation--empty',
      'aria-labelledby': titleId,
    }, [
      atlasElement(documentRef, 'h3', { id: titleId, text: 'Prochaine action' }),
      atlasElement(documentRef, 'p', {
        role: 'status',
        text: 'Aucune recommandation n’est disponible pour le moment.',
      }),
    ]);
  }
  const action = getAtlasActionPresentation(recommendation.action);
  const objectiveLabel = labelFromMap(options.objectiveLabelsById, recommendation.objectiveId);
  return atlasElement(documentRef, 'section', {
    className: `atlas-recommendation atlas-recommendation--${action.phase}`,
    'aria-labelledby': titleId,
    'data-action': recommendation.action,
    'data-objective-id': recommendation.objectiveId,
  }, [
    atlasElement(documentRef, 'p', { className: 'atlas-kicker', text: 'Prochaine action' }),
    atlasElement(documentRef, 'h3', { id: titleId, text: action.label }),
    atlasElement(documentRef, 'p', {
      className: 'atlas-recommendation__objective',
      text: `Objectif : ${objectiveLabel}`,
    }),
    atlasElement(documentRef, 'p', {
      className: 'atlas-recommendation__time',
      text: `Environ ${recommendation.estimatedMinutes} min`,
    }),
    renderAtlasReasonList(recommendation.reasonCodes, {
      documentRef,
      ariaLabel: 'Raisons de la recommandation',
    }),
  ]);
}

function renderPlanPreview(documentRef, plan, options) {
  const titleId = `${safeFragment(options.idPrefix)}-plan-title`;
  const section = atlasElement(documentRef, 'section', {
    className: 'atlas-plan-preview',
    'aria-labelledby': titleId,
    'data-plan-id': plan.planId,
  }, [
    atlasElement(documentRef, 'div', { className: 'atlas-plan-preview__heading' }, [
      atlasElement(documentRef, 'div', {}, [
        atlasElement(documentRef, 'p', { className: 'atlas-kicker', text: 'Séance proposée' }),
        atlasElement(documentRef, 'h3', { id: titleId, text: `${plan.durationMinutes} minutes utiles` }),
      ]),
      atlasElement(documentRef, 'p', {
        className: 'atlas-plan-preview__count',
        text: `${plan.items.length} étape${plan.items.length > 1 ? 's' : ''}`,
      }),
    ]),
  ]);
  if (plan.items.length === 0) {
    section.appendChild(atlasElement(documentRef, 'p', {
      role: 'status',
      text: 'Aucune activité admissible ne tient dans la durée choisie.',
    }));
    return section;
  }
  const list = atlasElement(documentRef, 'ol', { className: 'atlas-plan-preview__list' });
  for (const item of plan.items) {
    const action = getAtlasActionPresentation(item.action);
    const objectiveLabel = labelFromMap(options.objectiveLabelsById, item.objectiveId);
    const activityLabel = labelFromMap(options.activityLabelsById, item.activityLineageId);
    list.appendChild(atlasElement(documentRef, 'li', {
      className: `atlas-plan-preview__item atlas-plan-preview__item--${action.phase}`,
      'data-action': item.action,
      'data-objective-id': item.objectiveId,
      'data-activity-lineage-id': item.activityLineageId,
    }, [
      atlasElement(documentRef, 'span', {
        className: 'atlas-plan-preview__position',
        text: String(item.position),
        'aria-hidden': 'true',
      }),
      atlasElement(documentRef, 'div', { className: 'atlas-plan-preview__content' }, [
        atlasElement(documentRef, 'strong', { text: action.label }),
        atlasElement(documentRef, 'span', { text: objectiveLabel }),
        atlasElement(documentRef, 'span', {
          className: 'atlas-plan-preview__activity',
          text: activityLabel,
        }),
      ]),
      atlasElement(documentRef, 'span', {
        className: 'atlas-plan-preview__minutes',
        text: `${item.estimatedMinutes} min`,
      }),
    ]));
  }
  section.appendChild(list);
  if (plan.unusedMinutes > 0) {
    section.appendChild(atlasElement(documentRef, 'p', {
      className: 'atlas-plan-preview__unused',
      text: `${plan.unusedMinutes} min restent disponibles : le plan ne force aucune activité supplémentaire.`,
    }));
  }
  const startButton = atlasElement(documentRef, 'button', {
    className: 'atlas-button atlas-button--primary atlas-plan-preview__start',
    type: 'button',
    text: `Démarrer la séance de ${plan.durationMinutes} min`,
  });
  if (typeof options.onStart === 'function') {
    startButton.addEventListener('click', () => options.onStart(plan));
  }
  section.appendChild(startButton);
  return section;
}

export function renderAtlasToday(data, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new TypeError('L’écran Aujourd’hui doit recevoir un objet data.');
  }
  const durationMinutes = positiveInteger(data.durationMinutes, 'durationMinutes');
  if (!ATLAS_DURATION_OPTIONS.includes(durationMinutes)) {
    throw new RangeError('durationMinutes doit valoir 5, 15 ou 30.');
  }
  const recommendation = data.recommendation === null || data.recommendation === undefined
    ? null
    : normalizeRecommendation(data.recommendation);
  const plan = data.plan === null || data.plan === undefined
    ? null
    : normalizeAtlasSessionPlan(data.plan);
  if (plan && plan.durationMinutes !== durationMinutes) {
    throw new TypeError('La durée du plan doit correspondre à la durée sélectionnée.');
  }
  const resume = normalizeResume(data.resumableSession);
  const idPrefix = safeFragment(options.idPrefix ?? 'atlas-today');
  const titleId = `${idPrefix}-title`;
  const section = atlasElement(documentRef, 'section', {
    className: 'atlas-today',
    'aria-labelledby': titleId,
  }, [
    atlasElement(documentRef, 'div', { className: 'atlas-today__intro' }, [
      atlasElement(documentRef, 'p', { className: 'atlas-kicker', text: 'Aujourd’hui' }),
      atlasElement(documentRef, 'h2', { id: titleId, text: 'Apprenez ce qui compte maintenant' }),
      atlasElement(documentRef, 'p', {
        className: 'atlas-today__lead',
        text: 'Choisissez votre temps. Learn-it présente une séance locale et explique chaque proposition.',
      }),
    ]),
    renderDurationChooser(documentRef, durationMinutes, options.onDurationChange),
  ]);
  append(section,
    renderResumeCard(documentRef, resume, {
      ...options,
      idPrefix,
    }),
    renderRecommendationCard(documentRef, recommendation, {
      ...options,
      idPrefix,
    }),
  );
  if (plan) {
    section.appendChild(renderPlanPreview(documentRef, plan, {
      ...options,
      idPrefix,
    }));
  } else {
    section.appendChild(atlasElement(documentRef, 'p', {
      className: 'atlas-plan-preview atlas-plan-preview--pending',
      role: 'status',
      text: 'Choisissez une durée pour préparer une séance locale.',
    }));
  }
  return section;
}
