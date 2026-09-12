import crypto from 'node:crypto';

const SECRET_KEYS = new Set([
  'correctChoiceId',
  'answers',
  'acceptedValues',
  'answerKey',
  'evaluator',
  'scoringRule',
  'scoringRuleId',
  'scoringRuleDigest',
]);

function canonical(value) {
  if (value === null || typeof value === 'boolean' || Number.isInteger(value)) return value;
  if (typeof value === 'string') return value.normalize('NFC');
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key.normalize('NFC'), canonical(value[key])]),
    );
  }
  throw new Error('NON_CANONICAL_VALUE');
}

export function digest(domain, value) {
  const data = `${domain}\0${JSON.stringify(canonical(value))}`;
  return `sha256:${crypto.createHash('sha256').update(data, 'utf8').digest('hex')}`;
}

function activityId(activity) {
  return activity.activityRevisionId ?? activity.id;
}

function objectiveId(activity) {
  if (Array.isArray(activity.objectiveIds) && activity.objectiveIds.length === 1) return activity.objectiveIds[0];
  return activity.objectiveId;
}

function supportProjection(activity) {
  const support = activity.preResponseSupport ?? activity.support ?? null;
  if (support == null) return null;
  if (typeof support === 'string') return support;
  if (typeof support.content === 'string') return support.content;
  throw new Error('PRE_RESPONSE_SUPPORT_INVALID');
}

export function activityPresentation(activity) {
  const common = {
    activityId: activityId(activity),
    objectiveId: objectiveId(activity),
    prompt: activity.prompt ?? activity.stimulus?.prompt,
    preResponseSupport: supportProjection(activity),
  };
  if (!common.activityId || !common.objectiveId || !common.prompt) throw new Error('ACTIVITY_PRESENTATION_IDENTITY_REQUIRED');

  if (activity.type === 'qcm') {
    return {
      ...common,
      responseSpec: {
        kind: 'qcm',
        choices: activity.choices.map(({ choiceId, label }) => ({ choiceId, label })),
      },
    };
  }

  if (activity.type === 'fill') {
    return {
      ...common,
      responseSpec: {
        kind: 'fill',
        segments: activity.segments.map((segment) => (
          Object.hasOwn(segment, 'text') ? { text: segment.text } : { slotId: segment.slotId }
        )),
        tokens: activity.tokens.map(({ tokenId, label, maxUses }) => ({ tokenId, label, maxUses })),
      },
    };
  }

  if (activity.type === 'constructed') {
    if (!Array.isArray(activity.fields) || activity.fields.length === 0) throw new Error('CONSTRUCTED_FIELDS_REQUIRED');
    return {
      ...common,
      responseSpec: {
        kind: 'constructed',
        fields: activity.fields.map(({ fieldId, label }) => ({ fieldId, label })),
      },
    };
  }

  throw new Error(`UNSUPPORTED_ACTIVITY_TYPE:${activity.type}`);
}

export function assertLearnerSafe(value, path = '$') {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertLearnerSafe(item, `${path}[${index}]`));
    return true;
  }
  if (!value || typeof value !== 'object') return true;
  for (const [key, child] of Object.entries(value)) {
    if (SECRET_KEYS.has(key)) throw new Error(`LEARNER_SECRET_EXPOSED:${path}.${key}`);
    assertLearnerSafe(child, `${path}.${key}`);
  }
  return true;
}

export function activityResponse(presentation, value) {
  assertLearnerSafe(presentation);
  return Object.freeze({ activityId: presentation.activityId, value: structuredClone(value) });
}

function normalizeConstructedText(value, rule) {
  if (typeof value !== 'string') throw new Error('CONSTRUCTED_TEXT_REQUIRED');
  let normalized = value.normalize('NFC').trim();
  if (rule.collapseWhitespace === true) normalized = normalized.replace(/\s+/gu, ' ');
  if (rule.caseSensitive === false) normalized = normalized.toLowerCase();
  return normalized;
}

function constructedEvaluator(activity) {
  if (activity.evaluator?.kind !== 'exact-fields') throw new Error('EXACT_FIELDS_EVALUATOR_REQUIRED');
  if (!Array.isArray(activity.evaluator.fields)) throw new Error('EXACT_FIELDS_RULES_REQUIRED');
  return activity.evaluator;
}

export function assertValidationSupportPolicy(activity) {
  if (
    activity.type === 'constructed'
    && activity.assessmentRole === 'validation'
    && (activity.preResponseSupport ?? activity.support)?.revealing === true
  ) {
    throw new Error('VALIDATION_REVEALING_SUPPORT_FORBIDDEN');
  }
  return true;
}

export function evaluateConstructed(activity, rawValue) {
  assertValidationSupportPolicy(activity);
  const evaluator = constructedEvaluator(activity);
  if (!rawValue || typeof rawValue !== 'object' || Array.isArray(rawValue)) throw new Error('CONSTRUCTED_RESPONSE_REQUIRED');
  const fieldsValue = rawValue.fields;
  if (!fieldsValue || typeof fieldsValue !== 'object' || Array.isArray(fieldsValue)) throw new Error('CONSTRUCTED_FIELDS_RESPONSE_REQUIRED');

  const fieldIds = activity.fields.map((field) => field.fieldId);
  if (new Set(fieldIds).size !== fieldIds.length) throw new Error('CONSTRUCTED_DUPLICATE_FIELD_ID');
  if (Object.keys(fieldsValue).length !== fieldIds.length || fieldIds.some((fieldId) => !(fieldId in fieldsValue))) {
    throw new Error('CONSTRUCTED_RESPONSE_INCOMPLETE');
  }

  const rules = new Map(evaluator.fields.map((field) => [field.fieldId, field]));
  const normalized = {};
  const fieldResults = {};
  for (const fieldId of fieldIds) {
    const rule = rules.get(fieldId);
    if (!rule || !Array.isArray(rule.acceptedValues) || rule.acceptedValues.length === 0) {
      throw new Error(`CONSTRUCTED_EVALUATOR_RULE_REQUIRED:${fieldId}`);
    }
    const actual = normalizeConstructedText(fieldsValue[fieldId], rule);
    const accepted = rule.acceptedValues.map((candidate) => normalizeConstructedText(candidate, rule));
    normalized[fieldId] = actual;
    fieldResults[fieldId] = accepted.includes(actual);
  }

  return {
    normalized: { fields: normalized },
    fieldResults,
    correct: Object.values(fieldResults).every(Boolean),
  };
}

export function evaluateLearning(activity, response, productEvaluateAnswer) {
  if (response.activityId !== activityId(activity)) throw new Error('ACTIVITY_RESPONSE_ID_MISMATCH');
  if (activity.type === 'qcm' || activity.type === 'fill') {
    if (typeof productEvaluateAnswer !== 'function') throw new Error('PRODUCT_EVALUATOR_REQUIRED');
    return productEvaluateAnswer(activity, response.value);
  }
  if (activity.type === 'constructed') return evaluateConstructed(activity, response.value);
  throw new Error(`UNSUPPORTED_ACTIVITY_TYPE:${activity.type}`);
}

export function activityEvaluation(activity, response, productEvaluateAnswer, { assistance = 'none' } = {}) {
  if (!['none', 'used'].includes(assistance)) throw new Error('INVALID_ASSISTANCE');
  const result = evaluateLearning(activity, response, productEvaluateAnswer);
  const scoringRuleId = activity.type === 'constructed'
    ? 'learnit.kit.v2.constructed.exact-fields.v1'
    : `learnit.kit.v2.${activity.type}.v1`;
  const scoringMaterial = activity.type === 'constructed'
    ? constructedEvaluator(activity)
    : { type: activity.type, authority: 'apps/learnit-next/src/core/session.js' };
  return {
    activityId: activityId(activity),
    objectiveId: objectiveId(activity),
    normalizedResponse: result.normalized,
    responseDigest: digest('learnit.preintegration/response', result.normalized),
    scoringRuleId,
    scoringRuleDigest: digest('learnit.preintegration/scoring-rule', scoringMaterial),
    outcome: result.correct ? 'correct' : 'incorrect',
    assistance,
  };
}

export const QCM_FIXTURE = Object.freeze({
  activityRevisionId: 'qcm-r1',
  objectiveIds: ['qcm-objective'],
  type: 'qcm',
  prompt: '2 + 2 = ?',
  choices: [
    { choiceId: 'c1', label: '3' },
    { choiceId: 'c2', label: '4' },
  ],
  correctChoiceId: 'c2',
  explanation: 'Deux plus deux font quatre.',
});

export const FILL_FIXTURE = Object.freeze({
  activityRevisionId: 'fill-r1',
  objectiveIds: ['fill-objective'],
  type: 'fill',
  prompt: 'Complète : le ciel est ___.',
  segments: [{ text: 'Le ciel est ' }, { slotId: 's1' }, { text: '.' }],
  tokens: [
    { tokenId: 't1', label: 'bleu', maxUses: 1 },
    { tokenId: 't2', label: 'vert', maxUses: 1 },
  ],
  answers: [{ slotId: 's1', tokenId: 't1' }],
  explanation: 'Le ciel paraît généralement bleu en journée.',
});

export const MATH_E1 = Object.freeze({
  practice: {
    id: 'e1-practice',
    objectiveId: 'complex-roots-method-and-result',
    type: 'constructed',
    assessmentRole: 'practice',
    prompt: 'Pour z₀ = 4e^{iπ/3}, choisis la méthode et donne les deux racines.',
    preResponseSupport: { revealing: false, content: 'Avec un argument connu, utilise la forme exponentielle et le demi-angle.' },
    fields: [
      { fieldId: 'method', label: 'Méthode' },
      { fieldId: 'root1', label: 'Racine 1' },
      { fieldId: 'root2', label: 'Racine 2' },
    ],
    evaluator: {
      kind: 'exact-fields',
      fields: [
        { fieldId: 'method', acceptedValues: ['exponentielle'], caseSensitive: false },
        { fieldId: 'root1', acceptedValues: ['2e^{iπ/6}'], caseSensitive: true, collapseWhitespace: true },
        { fieldId: 'root2', acceptedValues: ['-2e^{iπ/6}'], caseSensitive: true, collapseWhitespace: true },
      ],
    },
  },
  validation: {
    id: 'e1-validation',
    objectiveId: 'complex-roots-method-and-result',
    type: 'constructed',
    assessmentRole: 'validation',
    prompt: 'Pour z₀ = 5 + 12i, sans argument fourni, choisis la méthode et donne les deux racines.',
    fields: [
      { fieldId: 'method', label: 'Méthode' },
      { fieldId: 'root1', label: 'Racine 1' },
      { fieldId: 'root2', label: 'Racine 2' },
    ],
    evaluator: {
      kind: 'exact-fields',
      fields: [
        { fieldId: 'method', acceptedValues: ['algébrique', 'algebrique'], caseSensitive: false },
        { fieldId: 'root1', acceptedValues: ['3+2i', '3 + 2i'], caseSensitive: true, collapseWhitespace: true },
        { fieldId: 'root2', acceptedValues: ['-3-2i', '-3 - 2i'], caseSensitive: true, collapseWhitespace: true },
      ],
    },
  },
});

const VOCAB = [
  ['maison', 'casa'], ['fenêtre', 'ventana'], ['porte', 'puerta'], ['table', 'mesa'], ['chaise', 'silla'],
  ['livre', 'libro'], ['école', 'escuela'], ['eau', 'agua'], ['pain', 'pan'], ['soleil', 'sol'],
  ['arbre', 'árbol'], ['nuit', 'noche'], ['main', 'mano'], ['ami', 'amigo'], ['famille', 'familia'],
  ['ville', 'ciudad'], ['chien', 'perro'], ['chat', 'gato'], ['chaussure', 'zapato'], ['plage', 'playa'],
];

function vocabActivity(groupIndex, assessmentRole) {
  const slice = VOCAB.slice(groupIndex * 5, groupIndex * 5 + 5);
  return {
    id: `e2-g${groupIndex + 1}-${assessmentRole}`,
    objectiveId: `productive-vocab-group-${groupIndex + 1}`,
    type: 'constructed',
    assessmentRole,
    prompt: `Produis en espagnol : ${slice.map(([fr]) => fr).join(', ')}.`,
    ...(assessmentRole === 'practice' ? {
      preResponseSupport: {
        revealing: false,
        content: slice.map(([fr, es]) => `${fr} → ${es}`).join(' ; '),
      },
    } : {}),
    fields: slice.map(([fr], index) => ({ fieldId: `word${index + 1}`, label: fr })),
    evaluator: {
      kind: 'exact-fields',
      fields: slice.map(([, es], index) => ({
        fieldId: `word${index + 1}`,
        acceptedValues: [es],
        caseSensitive: false,
      })),
    },
  };
}

export const VOCAB_E2 = Object.freeze(Array.from({ length: 4 }, (_, index) => Object.freeze({
  practice: vocabActivity(index, 'practice'),
  validation: vocabActivity(index, 'validation'),
})));
