import crypto from 'node:crypto';

function canonical(value) {
  if (value === null || typeof value === 'boolean' || Number.isInteger(value)) return value;
  if (typeof value === 'string') return value.normalize('NFC');
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key.normalize('NFC'), canonical(value[key])]));
  }
  throw new Error('NON_CANONICAL_VALUE');
}

export function digest(domain, value) {
  const data = `${domain}\0${JSON.stringify(canonical(value))}`;
  return `sha256:${crypto.createHash('sha256').update(data, 'utf8').digest('hex')}`;
}

export function normalizeText(value, rules = {}) {
  if (typeof value !== 'string') throw new Error('TEXT_RESPONSE_REQUIRED');
  let out = value.normalize('NFC');
  if (rules.trim !== false) out = out.trim();
  if (rules.collapseWhitespace === true) out = out.replace(/\s+/gu, ' ');
  if (rules.case === 'lower') out = out.toLocaleLowerCase(rules.locale ?? 'und');
  return out;
}

function assertActivity(activity) {
  if (!activity || typeof activity !== 'object') throw new Error('ACTIVITY_REQUIRED');
  if (!activity.id || !activity.objectiveId || !activity.stimulus?.prompt) throw new Error('ACTIVITY_IDENTITY_REQUIRED');
  if (!Array.isArray(activity.response?.fields) || activity.response.fields.length === 0) throw new Error('FIELDS_RESPONSE_REQUIRED');
  if (activity.evaluator?.kind !== 'exact-fields') throw new Error('EXACT_FIELDS_EVALUATOR_REQUIRED');
  const ids = activity.response.fields.map((field) => field.id);
  if (new Set(ids).size !== ids.length) throw new Error('DUPLICATE_FIELD_ID');
  for (const id of ids) {
    const rule = activity.evaluator.fields?.[id];
    if (!rule || !Array.isArray(rule.acceptedValues) || rule.acceptedValues.length === 0) throw new Error(`EVALUATOR_RULE_REQUIRED:${id}`);
  }
  return activity;
}

export function visibleStimulus(activity) {
  assertActivity(activity);
  return {
    support: activity.support ?? null,
    prompt: activity.stimulus.prompt,
    fields: activity.response.fields.map(({ id, label }) => ({ id, label })),
  };
}

export function responseSpec(activity) {
  assertActivity(activity);
  return {
    kind: 'fields',
    fields: activity.response.fields.map(({ id, label }) => ({ id, label })),
  };
}

export function evaluatorSpec(activity) {
  assertActivity(activity);
  return {
    kind: activity.evaluator.kind,
    fields: activity.evaluator.fields,
  };
}

export function evaluate(activity, rawResponse) {
  assertActivity(activity);
  if (!rawResponse || typeof rawResponse !== 'object' || Array.isArray(rawResponse)) throw new Error('FIELDS_RESPONSE_OBJECT_REQUIRED');
  const expectedIds = activity.response.fields.map((field) => field.id);
  if (Object.keys(rawResponse).length !== expectedIds.length || expectedIds.some((id) => !(id in rawResponse))) {
    throw new Error('FIELDS_RESPONSE_INCOMPLETE');
  }
  const normalized = {};
  const fieldResults = {};
  for (const id of expectedIds) {
    const rule = activity.evaluator.fields[id];
    const value = normalizeText(rawResponse[id], rule.normalize ?? {});
    normalized[id] = value;
    const accepted = rule.acceptedValues.map((candidate) => normalizeText(candidate, rule.normalize ?? {}));
    fieldResults[id] = accepted.includes(value);
  }
  return {
    normalized,
    fieldResults,
    correct: Object.values(fieldResults).every(Boolean),
  };
}

export function scoredExecutionLike(activity, rawResponse, { assistance = 'none' } = {}) {
  const result = evaluate(activity, rawResponse);
  if (!['none', 'used'].includes(assistance)) throw new Error('INVALID_ASSISTANCE');
  return {
    activityId: activity.id,
    objectiveId: activity.objectiveId,
    responseDigest: digest('learnit.experiment.e1e2/response', result.normalized),
    scoringRuleId: 'experiment.exact-fields.v1',
    scoringRuleDigest: digest('learnit.experiment.e1e2/evaluator', evaluatorSpec(activity)),
    outcome: result.correct ? 'correct' : 'incorrect',
    assistance,
    evidenceEligibleForIndependentValidation: activity.assessmentRole === 'validation' && assistance === 'none' && activity.support == null,
  };
}

export const MATH_E1 = Object.freeze({
  practice: {
    id: 'e1-math-practice',
    objectiveId: 'choose-and-compute-complex-square-roots',
    assessmentRole: 'practice',
    support: {
      kind: 'authored-baseline',
      content: 'Si un argument de z₀ est fourni, la forme exponentielle donne directement les deux demi-arguments. Sans argument connu, écrire z=a+ib et utiliser a²-b²=a₀, 2ab=b₀ et a²+b²=|z₀|.'
    },
    stimulus: {
      prompt: 'On donne z₀ = 4e^{iπ/3}. Choisis la méthode et donne les deux racines. Convention : root1 est la racine dont l’argument est π/6 ; root2 = -root1.'
    },
    response: {
      fields: [
        { id: 'method', label: 'Méthode' },
        { id: 'root1', label: 'Racine 1' },
        { id: 'root2', label: 'Racine 2' }
      ]
    },
    evaluator: {
      kind: 'exact-fields',
      fields: {
        method: { acceptedValues: ['exponentielle'], normalize: { trim: true, case: 'lower', locale: 'fr' } },
        root1: { acceptedValues: ['2e^{iπ/6}'], normalize: { trim: true, collapseWhitespace: true } },
        root2: { acceptedValues: ['-2e^{iπ/6}'], normalize: { trim: true, collapseWhitespace: true } }
      }
    }
  },
  validation: {
    id: 'e1-math-validation',
    objectiveId: 'choose-and-compute-complex-square-roots',
    assessmentRole: 'validation',
    support: null,
    stimulus: {
      prompt: 'On donne z₀ = 5 + 12i, sans argument fourni. Choisis la méthode et donne les deux racines. Convention : root1 a une partie réelle positive ; root2 = -root1.'
    },
    response: {
      fields: [
        { id: 'method', label: 'Méthode' },
        { id: 'root1', label: 'Racine 1' },
        { id: 'root2', label: 'Racine 2' }
      ]
    },
    evaluator: {
      kind: 'exact-fields',
      fields: {
        method: { acceptedValues: ['algébrique', 'algebrique'], normalize: { trim: true, case: 'lower', locale: 'fr' } },
        root1: { acceptedValues: ['3+2i', '3 + 2i'], normalize: { trim: true, collapseWhitespace: true } },
        root2: { acceptedValues: ['-3-2i', '-3 - 2i'], normalize: { trim: true, collapseWhitespace: true } }
      }
    }
  }
});

const VOCAB = [
  ['maison', 'casa'], ['fenêtre', 'ventana'], ['porte', 'puerta'], ['table', 'mesa'], ['chaise', 'silla'],
  ['livre', 'libro'], ['école', 'escuela'], ['eau', 'agua'], ['pain', 'pan'], ['soleil', 'sol'],
  ['arbre', 'árbol'], ['nuit', 'noche'], ['main', 'mano'], ['ami', 'amigo'], ['famille', 'familia'],
  ['ville', 'ciudad'], ['chien', 'perro'], ['chat', 'gato'], ['chaussure', 'zapato'], ['plage', 'playa']
];

function vocabularyActivity(groupIndex, assessmentRole) {
  const slice = VOCAB.slice(groupIndex * 5, groupIndex * 5 + 5);
  const fields = slice.map(([fr], index) => ({ id: `word${index + 1}`, label: fr }));
  const evaluatorFields = Object.fromEntries(slice.map(([, es], index) => [
    `word${index + 1}`,
    { acceptedValues: [es], normalize: { trim: true, case: 'lower', locale: 'es' } }
  ]));
  return {
    id: `e2-vocab-g${groupIndex + 1}-${assessmentRole}`,
    objectiveId: `produce-vocab-group-${groupIndex + 1}`,
    assessmentRole,
    support: assessmentRole === 'practice' ? {
      kind: 'authored-baseline',
      content: slice.map(([fr, es]) => `${fr} → ${es}`).join(' ; ')
    } : null,
    stimulus: {
      prompt: `Produis en espagnol les cinq mots français suivants : ${slice.map(([fr]) => fr).join(', ')}.`
    },
    response: { fields },
    evaluator: { kind: 'exact-fields', fields: evaluatorFields }
  };
}

export const VOCAB_E2 = Object.freeze(Array.from({ length: 4 }, (_, groupIndex) => Object.freeze({
  practice: vocabularyActivity(groupIndex, 'practice'),
  validation: vocabularyActivity(groupIndex, 'validation')
})));
