import {
  atlasElement,
  getAtlasActionPresentation,
  normalizeAtlasSessionPlan,
} from './atlas_today.js';

const EVIDENCE_STATE_PRESENTATION = Object.freeze({
  'not-started': Object.freeze({
    label: 'À commencer',
    description: 'Aucune preuve observée pour cet objectif.',
  }),
  training: Object.freeze({
    label: 'En entraînement',
    description: 'Des tentatives d’entraînement sont enregistrées.',
  }),
  'review-needed': Object.freeze({
    label: 'Correction nécessaire',
    description: 'Une erreur observée demande une correction.',
  }),
  'ready-for-validation': Object.freeze({
    label: 'Prêt pour validation',
    description: 'Une validation distincte peut être proposée.',
  }),
  'validated-recently': Object.freeze({
    label: 'Validation récente',
    description: 'Une validation distincte a été réussie récemment.',
  }),
});

const RESULT_PRESENTATION = Object.freeze({
  'practice:correct': Object.freeze({
    label: 'Entraînement réussi',
    className: 'atlas-summary__result--practice-correct',
  }),
  'practice:incorrect': Object.freeze({
    label: 'Entraînement à reprendre',
    className: 'atlas-summary__result--practice-incorrect',
  }),
  'practice:corrected': Object.freeze({
    label: 'Correction terminée',
    className: 'atlas-summary__result--correction',
  }),
  'practice:interrupted': Object.freeze({
    label: 'Entraînement interrompu',
    className: 'atlas-summary__result--interrupted',
  }),
  'validation:correct': Object.freeze({
    label: 'Validation réussie',
    className: 'atlas-summary__result--validation-correct',
  }),
  'validation:incorrect': Object.freeze({
    label: 'Validation à reprendre',
    className: 'atlas-summary__result--validation-incorrect',
  }),
  'validation:interrupted': Object.freeze({
    label: 'Validation interrompue',
    className: 'atlas-summary__result--interrupted',
  }),
});

export const ATLAS_OBJECTIVE_STATES = Object.freeze(Object.keys(EVIDENCE_STATE_PRESENTATION));

function requireDocument(documentRef) {
  if (!documentRef || typeof documentRef.createElement !== 'function') {
    throw new TypeError('Un document DOM est requis pour générer le bilan Atlas.');
  }
  return documentRef;
}

function requiredText(value, fieldName) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new TypeError(`${fieldName} doit être une chaîne non vide.`);
  }
  return value.trim();
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

function optionalBoolean(value, fieldName) {
  if (value !== null && value !== undefined && typeof value !== 'boolean') {
    throw new TypeError(`${fieldName} doit être un booléen ou null.`);
  }
  return value ?? null;
}

function optionalTimestamp(value, fieldName) {
  if (value === null || value === undefined) return null;
  return requiredText(value, fieldName);
}

function labelFromMap(labelsById, identifier) {
  if (labelsById instanceof Map) return labelsById.get(identifier) ?? identifier;
  if (labelsById && typeof labelsById === 'object' && !Array.isArray(labelsById)) {
    return labelsById[identifier] ?? identifier;
  }
  return identifier;
}

function normalizeEvidence(evidence) {
  if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence)) {
    throw new TypeError('ObjectiveEvidence doit être un objet data.');
  }
  const state = requiredText(evidence.state, 'evidence.state');
  if (!Object.hasOwn(EVIDENCE_STATE_PRESENTATION, state)) {
    throw new RangeError(`État ObjectiveEvidence non pris en charge : ${state}`);
  }
  if (!Array.isArray(evidence.reasons)) throw new TypeError('evidence.reasons doit être un tableau.');
  return {
    objectiveId: requiredText(evidence.objectiveId, 'evidence.objectiveId'),
    projectionVersion: positiveInteger(evidence.projectionVersion, 'evidence.projectionVersion'),
    practiceAttempts: nonNegativeInteger(evidence.practiceAttempts, 'evidence.practiceAttempts'),
    latestPracticeCorrect: optionalBoolean(
      evidence.latestPracticeCorrect,
      'evidence.latestPracticeCorrect',
    ),
    needsReview: typeof evidence.needsReview === 'boolean'
      ? evidence.needsReview
      : (() => { throw new TypeError('evidence.needsReview doit être un booléen.'); })(),
    correctionsCompleted: nonNegativeInteger(
      evidence.correctionsCompleted,
      'evidence.correctionsCompleted',
    ),
    validationAttempts: nonNegativeInteger(
      evidence.validationAttempts,
      'evidence.validationAttempts',
    ),
    latestValidationCorrect: optionalBoolean(
      evidence.latestValidationCorrect,
      'evidence.latestValidationCorrect',
    ),
    lastEvidenceAt: optionalTimestamp(evidence.lastEvidenceAt, 'evidence.lastEvidenceAt'),
    state,
    reasons: evidence.reasons.map((value, index) => requiredText(value, `evidence.reasons[${index}]`)),
  };
}

function normalizeResult(result, expectedPosition, planItem) {
  if (!result || typeof result !== 'object' || Array.isArray(result)) {
    throw new TypeError(`results[${expectedPosition - 1}] doit être un objet data.`);
  }
  if (result.position !== expectedPosition) {
    throw new TypeError('Les résultats doivent suivre les positions du SessionPlan.');
  }
  const objectiveId = requiredText(result.objectiveId, `results[${expectedPosition - 1}].objectiveId`);
  const activityLineageId = requiredText(
    result.activityLineageId,
    `results[${expectedPosition - 1}].activityLineageId`,
  );
  if (objectiveId !== planItem.objectiveId || activityLineageId !== planItem.activityLineageId) {
    throw new TypeError('Un résultat doit référencer exactement l’étape correspondante du SessionPlan.');
  }
  const assessmentRole = requiredText(
    result.assessmentRole,
    `results[${expectedPosition - 1}].assessmentRole`,
  );
  if (!['practice', 'validation'].includes(assessmentRole)) {
    throw new RangeError('assessmentRole doit valoir practice ou validation.');
  }
  const outcome = requiredText(result.outcome, `results[${expectedPosition - 1}].outcome`);
  const key = `${assessmentRole}:${outcome}`;
  if (!Object.hasOwn(RESULT_PRESENTATION, key)) {
    throw new RangeError(`Résultat de séance non pris en charge : ${key}`);
  }
  if (outcome === 'corrected' && planItem.action !== 'correct-practice') {
    throw new TypeError('Une correction terminée doit correspondre à une étape correct-practice.');
  }
  if (assessmentRole === 'validation' && planItem.action !== 'attempt-validation') {
    throw new TypeError('Un résultat validation doit correspondre à une étape attempt-validation.');
  }
  if (assessmentRole === 'practice' && planItem.action === 'attempt-validation') {
    throw new TypeError('Une étape attempt-validation ne peut pas être présentée comme practice.');
  }
  return {
    position: expectedPosition,
    objectiveId,
    activityLineageId,
    assessmentRole,
    outcome,
  };
}

function renderEvidenceFacts(documentRef, evidence) {
  const lastPractice = evidence.practiceAttempts === 0 || evidence.latestPracticeCorrect === null
    ? 'Aucun résultat'
    : evidence.latestPracticeCorrect ? 'Correct' : 'À reprendre';
  const lastValidation = evidence.validationAttempts === 0 || evidence.latestValidationCorrect === null
    ? 'Aucun résultat'
    : evidence.latestValidationCorrect ? 'Réussie' : 'À reprendre';
  return atlasElement(documentRef, 'dl', { className: 'atlas-objective-map__facts' }, [
    atlasElement(documentRef, 'dt', { text: 'Entraînements' }),
    atlasElement(documentRef, 'dd', { text: String(evidence.practiceAttempts) }),
    atlasElement(documentRef, 'dt', { text: 'Dernier entraînement' }),
    atlasElement(documentRef, 'dd', { text: lastPractice }),
    atlasElement(documentRef, 'dt', { text: 'Corrections terminées' }),
    atlasElement(documentRef, 'dd', { text: String(evidence.correctionsCompleted) }),
    atlasElement(documentRef, 'dt', { text: 'Validations distinctes' }),
    atlasElement(documentRef, 'dd', { text: String(evidence.validationAttempts) }),
    atlasElement(documentRef, 'dt', { text: 'Dernière validation' }),
    atlasElement(documentRef, 'dd', { text: lastValidation }),
  ]);
}

export function getAtlasObjectiveStatePresentation(state) {
  const normalized = requiredText(state, 'state');
  const presentation = EVIDENCE_STATE_PRESENTATION[normalized];
  if (!presentation) throw new RangeError(`État ObjectiveEvidence non pris en charge : ${normalized}`);
  return presentation;
}

export function renderAtlasObjectiveMap(objectiveEvidence, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  if (!Array.isArray(objectiveEvidence)) throw new TypeError('objectiveEvidence doit être un tableau.');
  const normalized = objectiveEvidence.map(normalizeEvidence);
  const identifiers = normalized.map((item) => item.objectiveId);
  if (new Set(identifiers).size !== identifiers.length) {
    throw new TypeError('objectiveEvidence ne doit pas contenir deux fois le même objectif.');
  }
  const titleId = options.titleId ?? 'atlas-objective-map-title';
  const section = atlasElement(documentRef, 'section', {
    className: 'atlas-objective-map',
    'aria-labelledby': titleId,
  }, [
    atlasElement(documentRef, 'div', { className: 'atlas-section-heading' }, [
      atlasElement(documentRef, 'p', { className: 'atlas-kicker', text: 'Carte des objectifs' }),
      atlasElement(documentRef, 'h2', { id: titleId, text: options.title ?? 'Où en sont vos objectifs ?' }),
    ]),
    atlasElement(documentRef, 'p', {
      className: 'atlas-objective-map__boundary',
      text: 'Ces états décrivent uniquement les preuves observées dans Learn-it.',
    }),
  ]);
  if (normalized.length === 0) {
    section.appendChild(atlasElement(documentRef, 'p', {
      className: 'atlas-objective-map__empty',
      role: 'status',
      text: 'Aucun objectif à afficher pour le moment.',
    }));
    return section;
  }
  const list = atlasElement(documentRef, 'ol', { className: 'atlas-objective-map__list' });
  for (const evidence of normalized) {
    const presentation = getAtlasObjectiveStatePresentation(evidence.state);
    const objectiveLabel = labelFromMap(options.objectiveLabelsById, evidence.objectiveId);
    list.appendChild(atlasElement(documentRef, 'li', {
      className: `atlas-objective-map__item atlas-objective-map__item--${evidence.state}`,
      'data-objective-id': evidence.objectiveId,
      'data-evidence-state': evidence.state,
    }, [
      atlasElement(documentRef, 'article', {}, [
        atlasElement(documentRef, 'h3', { text: objectiveLabel }),
        atlasElement(documentRef, 'p', { className: 'atlas-objective-map__state' }, [
          atlasElement(documentRef, 'strong', { text: presentation.label }),
          atlasElement(documentRef, 'span', { text: presentation.description }),
        ]),
        renderEvidenceFacts(documentRef, evidence),
      ]),
    ]));
  }
  section.appendChild(list);
  return section;
}

function renderResultList(documentRef, plan, results, options) {
  const list = atlasElement(documentRef, 'ol', {
    className: 'atlas-summary__results',
    'aria-label': 'Résultats de la séance',
  });
  for (const result of results) {
    const planItem = plan.items[result.position - 1];
    const presentation = RESULT_PRESENTATION[`${result.assessmentRole}:${result.outcome}`];
    const action = getAtlasActionPresentation(planItem.action);
    const objectiveLabel = labelFromMap(options.objectiveLabelsById, result.objectiveId);
    const activityLabel = labelFromMap(options.activityLabelsById, result.activityLineageId);
    list.appendChild(atlasElement(documentRef, 'li', {
      className: `atlas-summary__result ${presentation.className}`,
      'data-assessment-role': result.assessmentRole,
      'data-outcome': result.outcome,
      'data-action': planItem.action,
    }, [
      atlasElement(documentRef, 'div', { className: 'atlas-summary__result-main' }, [
        atlasElement(documentRef, 'strong', { text: presentation.label }),
        atlasElement(documentRef, 'span', { text: objectiveLabel }),
        atlasElement(documentRef, 'span', {
          className: 'atlas-summary__activity',
          text: activityLabel,
        }),
      ]),
      atlasElement(documentRef, 'span', {
        className: 'atlas-summary__action',
        text: action.label,
      }),
    ]));
  }
  return list;
}

function summaryMessage(results) {
  if (results.length === 0) return 'Aucune étape n’a été terminée dans cette séance.';
  const corrections = results.filter((item) => item.outcome === 'corrected').length;
  const validations = results.filter(
    (item) => item.assessmentRole === 'validation' && item.outcome === 'correct',
  ).length;
  const parts = [`${results.length} étape${results.length > 1 ? 's' : ''} renseignée${results.length > 1 ? 's' : ''}`];
  if (corrections > 0) parts.push(`${corrections} correction${corrections > 1 ? 's' : ''} terminée${corrections > 1 ? 's' : ''}`);
  if (validations > 0) parts.push(`${validations} validation${validations > 1 ? 's' : ''} réussie${validations > 1 ? 's' : ''}`);
  return `${parts.join(' · ')}.`;
}

export function renderAtlasSessionSummary(data, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new TypeError('Le bilan de séance doit recevoir un objet data.');
  }
  const sessionId = requiredText(data.sessionId, 'sessionId');
  const plan = normalizeAtlasSessionPlan(data.plan);
  if (!Array.isArray(data.results)) throw new TypeError('results doit être un tableau.');
  if (data.results.length > plan.items.length) {
    throw new TypeError('Le bilan contient plus de résultats que le SessionPlan.');
  }
  const results = data.results.map((result, index) => normalizeResult(result, index + 1, plan.items[index]));
  const objectiveEvidence = data.objectiveEvidence ?? [];
  if (!Array.isArray(objectiveEvidence)) throw new TypeError('objectiveEvidence doit être un tableau.');
  const titleId = 'atlas-summary-title';
  const section = atlasElement(documentRef, 'section', {
    className: 'atlas-summary',
    'aria-labelledby': titleId,
    'data-session-id': sessionId,
    'data-plan-id': plan.planId,
  }, [
    atlasElement(documentRef, 'header', { className: 'atlas-summary__header' }, [
      atlasElement(documentRef, 'p', { className: 'atlas-kicker', text: 'Bilan' }),
      atlasElement(documentRef, 'h2', { id: titleId, text: 'Ce que cette séance a produit' }),
      atlasElement(documentRef, 'p', {
        className: 'atlas-summary__lead',
        text: summaryMessage(results),
      }),
    ]),
    renderResultList(documentRef, plan, results, options),
  ]);
  if (typeof options.renderRewards === 'function') {
    const rewards = options.renderRewards(data.rewards ?? []);
    if (rewards !== null && rewards !== undefined) {
      if (typeof rewards !== 'object' || typeof rewards.setAttribute !== 'function') {
        throw new TypeError('renderRewards doit retourner un nœud DOM ou null.');
      }
      section.appendChild(rewards);
    }
  }
  section.appendChild(renderAtlasObjectiveMap(objectiveEvidence, {
    documentRef,
    objectiveLabelsById: options.objectiveLabelsById,
    title: 'Vos objectifs après cette séance',
    titleId: 'atlas-summary-objective-map-title',
  }));
  const actions = atlasElement(documentRef, 'div', {
    className: 'atlas-summary__controls',
    role: 'group',
    'aria-label': 'Actions après le bilan',
  });
  const todayButton = atlasElement(documentRef, 'button', {
    className: 'atlas-button atlas-button--primary',
    type: 'button',
    text: 'Revenir à Aujourd’hui',
  });
  if (typeof options.onReturnToday === 'function') {
    todayButton.addEventListener('click', () => options.onReturnToday({ sessionId, planId: plan.planId }));
  }
  actions.appendChild(todayButton);
  section.appendChild(actions);
  return section;
}
