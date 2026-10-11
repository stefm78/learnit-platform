export class ActivityResponseValidationError extends Error {
  constructor(message, code = 'invalid_answer') {
    super(message);
    this.name = 'ActivityResponseValidationError';
    this.code = code;
  }
}

export const SCORED_ACTIVITY_TYPES = Object.freeze([
  'qcm', 'fill', 'constructed', 'matching', 'order', 'classify', 'productive',
]);
export const NON_SCORED_ACTIVITY_TYPES = Object.freeze(['lesson', 'flashcard']);
export const V4_ACTIVITY_TYPES = Object.freeze([
  ...SCORED_ACTIVITY_TYPES.filter(type => type !== 'productive'),
  ...NON_SCORED_ACTIVITY_TYPES,
]);

const SCORED = new Set(SCORED_ACTIVITY_TYPES);
const NON_SCORED = new Set(NON_SCORED_ACTIVITY_TYPES);

export function isScoredActivity(activityOrType) {
  const type = typeof activityOrType === 'string' ? activityOrType : activityOrType?.type;
  return SCORED.has(type);
}

export function isNonScoredActivity(activityOrType) {
  const type = typeof activityOrType === 'string' ? activityOrType : activityOrType?.type;
  return NON_SCORED.has(type);
}

export function normalizeConstructedText(value) {
  if (typeof value !== 'string') {
    throw new ActivityResponseValidationError('A constructed response must provide string text', 'invalid_text');
  }
  return value.normalize('NFC').trim().replace(/\s+/gu, ' ');
}

function normalizeQcm(activity, response) {
  const choiceId = typeof response === 'string' ? response : response?.choiceId;
  if (typeof choiceId !== 'string') {
    throw new ActivityResponseValidationError('A QCM response must provide a choiceId');
  }
  if (!activity.choices?.some(choice => choice.choiceId === choiceId)) {
    throw new ActivityResponseValidationError(`Unknown choiceId ${String(choiceId)}`, 'unknown_choice');
  }
  return Object.freeze({ choiceId });
}

function normalizeFill(activity, response) {
  const entries = Array.isArray(response)
    ? response.map(value => [value?.slotId, value?.tokenId])
    : Object.entries(response ?? {});
  const assignments = new Map();
  for (const [slotId, tokenId] of entries) {
    if (typeof slotId !== 'string' || typeof tokenId !== 'string') {
      throw new ActivityResponseValidationError('Each fill assignment must contain string slotId and tokenId values');
    }
    if (assignments.has(slotId)) {
      throw new ActivityResponseValidationError(`slotId ${slotId} is assigned more than once`, 'duplicate_slot_assignment');
    }
    assignments.set(slotId, tokenId);
  }
  const slotIds = (activity.segments ?? [])
    .filter(segment => Object.hasOwn(segment, 'slotId'))
    .map(segment => segment.slotId);
  const slotSet = new Set(slotIds);
  const tokenById = new Map((activity.tokens ?? []).map(token => [token.tokenId, token]));
  if (assignments.size !== slotIds.length || slotIds.some(slotId => !assignments.has(slotId))) {
    throw new ActivityResponseValidationError('Every declared fill slot must have exactly one token', 'incomplete_fill');
  }
  const usage = new Map();
  for (const [slotId, tokenId] of assignments) {
    if (!slotSet.has(slotId)) {
      throw new ActivityResponseValidationError(`Unknown slotId ${slotId}`, 'unknown_slot');
    }
    const token = tokenById.get(tokenId);
    if (!token) throw new ActivityResponseValidationError(`Unknown tokenId ${tokenId}`, 'unknown_token');
    const count = (usage.get(tokenId) ?? 0) + 1;
    if (count > token.maxUses) {
      throw new ActivityResponseValidationError(`tokenId ${tokenId} exceeds maxUses ${token.maxUses}`, 'max_uses');
    }
    usage.set(tokenId, count);
  }
  return Object.freeze(Object.fromEntries(slotIds.map(slotId => [slotId, assignments.get(slotId)])));
}

function normalizeConstructed(response) {
  const text = normalizeConstructedText(response?.text);
  if (!text) {
    throw new ActivityResponseValidationError('Constructed response is blank after normalization', 'blank_text');
  }
  return Object.freeze({ text });
}

function normalizeMatching(activity, response) {
  if (!Array.isArray(response?.associations)) {
    throw new ActivityResponseValidationError('Matching response requires associations[]', 'invalid_matching');
  }
  const leftIds = (activity.leftItems ?? []).map(item => item.itemId);
  const rightIds = (activity.rightItems ?? []).map(item => item.itemId);
  const leftSet = new Set(leftIds);
  const rightSet = new Set(rightIds);
  if (response.associations.length !== leftIds.length || leftIds.length !== rightIds.length) {
    throw new ActivityResponseValidationError('Matching response must cover every authored item exactly once', 'incomplete_matching');
  }
  const leftSeen = new Set();
  const rightSeen = new Set();
  const mapping = new Map();
  for (const association of response.associations) {
    const leftItemId = association?.leftItemId;
    const rightItemId = association?.rightItemId;
    if (typeof leftItemId !== 'string' || typeof rightItemId !== 'string') {
      throw new ActivityResponseValidationError('Each matching association requires string IDs', 'invalid_matching');
    }
    if (!leftSet.has(leftItemId)) {
      throw new ActivityResponseValidationError(`Unknown leftItemId ${String(leftItemId)}`, 'unknown_matching_item');
    }
    if (!rightSet.has(rightItemId)) {
      throw new ActivityResponseValidationError(`Unknown rightItemId ${String(rightItemId)}`, 'unknown_matching_item');
    }
    if (leftSeen.has(leftItemId) || rightSeen.has(rightItemId)) {
      throw new ActivityResponseValidationError('Matching response contains a duplicate or multi-use association', 'duplicate_matching_item');
    }
    leftSeen.add(leftItemId);
    rightSeen.add(rightItemId);
    mapping.set(leftItemId, rightItemId);
  }
  if (leftSeen.size !== leftIds.length || rightSeen.size !== rightIds.length) {
    throw new ActivityResponseValidationError('Matching response omits authored items', 'incomplete_matching');
  }
  return Object.freeze({
    associations: Object.freeze(leftIds.map(leftItemId => Object.freeze({
      leftItemId,
      rightItemId: mapping.get(leftItemId),
    }))),
  });
}

function normalizeOrder(activity, response) {
  if (!Array.isArray(response?.orderedItemIds)) {
    throw new ActivityResponseValidationError('Order response requires orderedItemIds[]', 'invalid_order');
  }
  const authored = (activity.items ?? []).map(item => item.itemId);
  const authoredSet = new Set(authored);
  if (response.orderedItemIds.length !== authored.length) {
    throw new ActivityResponseValidationError('Order response must include every authored item', 'incomplete_order');
  }
  const seen = new Set();
  const orderedItemIds = response.orderedItemIds.map(itemId => {
    if (typeof itemId !== 'string' || !authoredSet.has(itemId)) {
      throw new ActivityResponseValidationError(`Unknown order itemId ${String(itemId)}`, 'unknown_order_item');
    }
    if (seen.has(itemId)) {
      throw new ActivityResponseValidationError(`Duplicate order itemId ${itemId}`, 'duplicate_order_item');
    }
    seen.add(itemId);
    return itemId;
  });
  if (seen.size !== authored.length) {
    throw new ActivityResponseValidationError('Order response omits authored items', 'incomplete_order');
  }
  return Object.freeze({ orderedItemIds: Object.freeze(orderedItemIds) });
}

function normalizeClassify(activity, response) {
  if (!Array.isArray(response?.assignments)) {
    throw new ActivityResponseValidationError('Classify response requires assignments[]', 'invalid_classification');
  }
  const itemIds = (activity.items ?? []).map(item => item.itemId);
  const itemSet = new Set(itemIds);
  const bucketSet = new Set((activity.buckets ?? []).map(bucket => bucket.bucketId));
  if (response.assignments.length !== itemIds.length) {
    throw new ActivityResponseValidationError('Classification must assign every authored item exactly once', 'incomplete_classification');
  }
  const mapping = new Map();
  for (const assignment of response.assignments) {
    const itemId = assignment?.itemId;
    const bucketId = assignment?.bucketId;
    if (typeof itemId !== 'string' || typeof bucketId !== 'string') {
      throw new ActivityResponseValidationError('Each classification assignment requires string IDs', 'invalid_classification');
    }
    if (!itemSet.has(itemId)) {
      throw new ActivityResponseValidationError(`Unknown classify itemId ${String(itemId)}`, 'unknown_classification_item');
    }
    if (!bucketSet.has(bucketId)) {
      throw new ActivityResponseValidationError(`Unknown bucketId ${String(bucketId)}`, 'unknown_classification_bucket');
    }
    if (mapping.has(itemId)) {
      throw new ActivityResponseValidationError(`Item ${itemId} is classified more than once`, 'multiple_classification');
    }
    mapping.set(itemId, bucketId);
  }
  if (mapping.size !== itemIds.length) {
    throw new ActivityResponseValidationError('Classification omits authored items', 'incomplete_classification');
  }
  return Object.freeze({
    assignments: Object.freeze(itemIds.map(itemId => Object.freeze({ itemId, bucketId: mapping.get(itemId) }))),
  });
}

function normalizeLesson(response) {
  if (response?.acknowledged !== true || Object.keys(response ?? {}).length !== 1) {
    throw new ActivityResponseValidationError('Lesson completion requires {acknowledged:true}', 'invalid_completion');
  }
  return Object.freeze({ acknowledged: true });
}

function normalizeFlashcard(response) {
  if (response?.revealed !== true || Object.keys(response ?? {}).length !== 1) {
    throw new ActivityResponseValidationError('Flashcard completion requires {revealed:true}', 'invalid_completion');
  }
  return Object.freeze({ revealed: true });
}

function normalizeProductiveText(value) {
  if (typeof value !== 'string') {
    throw new ActivityResponseValidationError('Productive text responses must be strings', 'invalid_productive_value');
  }
  return value.normalize('NFC').trim().replace(/\s+/gu, ' ');
}

function normalizeExpression(value) {
  return normalizeProductiveText(value).replace(/\s+/gu, '').toLowerCase();
}

function normalizeUnit(value) {
  if (value == null || value === '') return null;
  if (typeof value !== 'string') {
    throw new ActivityResponseValidationError('Productive units must be strings', 'invalid_productive_unit');
  }
  return value.normalize('NFC').trim().replace(/\s+/gu, ' ').toLowerCase();
}

function rationalNumber(value, label) {
  const numerator = value?.numerator;
  const denominator = value?.denominator;
  if (!Number.isInteger(numerator) || !Number.isInteger(denominator) || denominator <= 0) {
    throw new ActivityResponseValidationError(`Invalid ${label} rational evaluator`, 'invalid_productive_evaluator');
  }
  return numerator / denominator;
}

function normalizeProductive(activity, response) {
  const parts = activity.parts ?? [];
  const incoming = response?.parts;
  if (!incoming || typeof incoming !== 'object' || Array.isArray(incoming)) {
    throw new ActivityResponseValidationError('Productive response requires parts keyed by partId', 'invalid_productive_response');
  }
  const partIds = parts.map(part => part.partId);
  const supplied = Object.keys(incoming);
  if (supplied.length !== partIds.length || supplied.some(id => !partIds.includes(id))) {
    throw new ActivityResponseValidationError('Productive response must cover every authored part exactly once', 'incomplete_productive_response');
  }
  const normalized = {};
  for (const part of parts) {
    const raw = incoming[part.partId];
    if (part.responseKind === 'number') {
      const value = typeof raw === 'number' ? raw : raw?.value;
      const unit = typeof raw === 'number' ? null : normalizeUnit(raw?.unit);
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new ActivityResponseValidationError(`Productive number part ${part.partId} requires a finite number`, 'invalid_productive_number');
      }
      normalized[part.partId] = Object.freeze({ value, unit });
    } else if (part.responseKind === 'expression') {
      const value = typeof raw === 'string' ? raw : raw?.value;
      const normalizedValue = normalizeExpression(value);
      if (!normalizedValue) throw new ActivityResponseValidationError(`Productive expression part ${part.partId} is blank`, 'blank_productive_expression');
      normalized[part.partId] = Object.freeze({ value: normalizedValue });
    } else if (part.responseKind === 'text') {
      const value = typeof raw === 'string' ? raw : raw?.value;
      const normalizedValue = normalizeProductiveText(value);
      if (!normalizedValue) throw new ActivityResponseValidationError(`Productive text part ${part.partId} is blank`, 'blank_productive_text');
      normalized[part.partId] = Object.freeze({ value: normalizedValue });
    } else {
      throw new ActivityResponseValidationError(`Unsupported productive responseKind ${String(part.responseKind)}`, 'invalid_productive_evaluator');
    }
  }
  return Object.freeze({ parts: Object.freeze(normalized) });
}

function evaluateProductive(activity, response) {
  if (activity?.scoring?.aggregation !== 'all' || !Array.isArray(activity.scoring?.evaluators)) {
    throw new ActivityResponseValidationError('Productive scoring must use aggregation=all and evaluators[]', 'invalid_productive_evaluator');
  }
  const parts = activity.parts ?? [];
  const partById = new Map(parts.map(part => [part.partId, part]));
  const evaluators = activity.scoring.evaluators;
  if (partById.size !== parts.length || evaluators.length !== parts.length) {
    throw new ActivityResponseValidationError('Every productive part requires exactly one evaluator', 'invalid_productive_evaluator');
  }
  const evaluatorById = new Map();
  for (const evaluator of evaluators) {
    if (!evaluator || typeof evaluator !== 'object' || evaluatorById.has(evaluator.partId) || !partById.has(evaluator.partId)) {
      throw new ActivityResponseValidationError('Productive evaluator part bindings are invalid', 'invalid_productive_evaluator');
    }
    const part = partById.get(evaluator.partId);
    const expectedKind = {
      number: 'numeric-tolerance',
      expression: 'canonical-expression-set',
      text: 'required-concepts',
    }[part.responseKind];
    if (evaluator.kind !== expectedKind) {
      throw new ActivityResponseValidationError(`Productive evaluator kind does not match ${part.responseKind}`, 'invalid_productive_evaluator');
    }
    evaluatorById.set(evaluator.partId, evaluator);
  }
  const normalized = normalizeProductive(activity, response);
  const partResults = {};
  let correct = true;
  for (const part of parts) {
    const answer = normalized.parts[part.partId];
    const evaluator = evaluatorById.get(part.partId);
    let partCorrect = false;
    if (evaluator.kind === 'numeric-tolerance') {
      const expected = rationalNumber(evaluator.expected, 'expected');
      const tolerance = rationalNumber(evaluator.absoluteTolerance, 'absoluteTolerance');
      if (tolerance < 0) throw new ActivityResponseValidationError('Numeric tolerance must be non-negative', 'invalid_productive_evaluator');
      const acceptedUnits = evaluator.acceptedUnits ?? [];
      if (!Array.isArray(acceptedUnits)) throw new ActivityResponseValidationError('acceptedUnits must be an array', 'invalid_productive_evaluator');
      const units = new Set(acceptedUnits.map(unit => normalizeUnit(unit)));
      const unitOk = acceptedUnits.length === 0 ? answer.unit == null : answer.unit != null && units.has(answer.unit);
      partCorrect = unitOk && Math.abs(answer.value - expected) <= tolerance;
    } else if (evaluator.kind === 'canonical-expression-set') {
      if (!Array.isArray(evaluator.acceptedExpressions) || evaluator.acceptedExpressions.length === 0) {
        throw new ActivityResponseValidationError('canonical-expression-set requires acceptedExpressions', 'invalid_productive_evaluator');
      }
      const accepted = new Set(evaluator.acceptedExpressions.map(normalizeExpression));
      partCorrect = accepted.has(answer.value);
    } else if (evaluator.kind === 'required-concepts') {
      if (!Array.isArray(evaluator.requiredConceptGroups) || evaluator.requiredConceptGroups.length === 0) {
        throw new ActivityResponseValidationError('required-concepts requires concept groups', 'invalid_productive_evaluator');
      }
      const haystack = answer.value.toLocaleLowerCase();
      partCorrect = evaluator.requiredConceptGroups.every(group => (
        Array.isArray(group) && group.length > 0 && group.some(concept => {
          const needle = normalizeProductiveText(concept).toLocaleLowerCase();
          return needle.length > 0 && haystack.includes(needle);
        })
      ));
    }
    partResults[part.partId] = partCorrect;
    if (!partCorrect) correct = false;
  }
  return Object.freeze({
    scored: true,
    normalized,
    correct,
    partResults: Object.freeze(partResults),
  });
}

function orderedPairsEqual(left, right, leftKey, rightKey) {
  if (left.length !== right.length) return false;
  const expected = new Map(right.map(item => [item[leftKey], item[rightKey]]));
  return left.every(item => expected.get(item[leftKey]) === item[rightKey]);
}

export function evaluateActivityResponse(activity, response) {
  switch (activity?.type) {
    case 'qcm': {
      const normalized = normalizeQcm(activity, response);
      return Object.freeze({ scored: true, normalized, correct: normalized.choiceId === activity.correctChoiceId });
    }
    case 'fill': {
      const normalized = normalizeFill(activity, response);
      const expected = new Map((activity.answers ?? []).map(entry => [entry.slotId, entry.tokenId]));
      const correct = Object.entries(normalized).every(([slotId, tokenId]) => expected.get(slotId) === tokenId);
      return Object.freeze({ scored: true, normalized, correct });
    }
    case 'constructed': {
      const normalized = normalizeConstructed(response);
      const accepted = (activity.acceptedResponses ?? []).map(normalizeConstructedText);
      return Object.freeze({ scored: true, normalized, correct: accepted.includes(normalized.text) });
    }
    case 'matching': {
      const normalized = normalizeMatching(activity, response);
      return Object.freeze({
        scored: true,
        normalized,
        correct: orderedPairsEqual(normalized.associations, activity.matches ?? [], 'leftItemId', 'rightItemId'),
      });
    }
    case 'order': {
      const normalized = normalizeOrder(activity, response);
      const correctOrder = activity.correctOrder ?? [];
      return Object.freeze({
        scored: true,
        normalized,
        correct: normalized.orderedItemIds.length === correctOrder.length
          && normalized.orderedItemIds.every((itemId, index) => itemId === correctOrder[index]),
      });
    }
    case 'classify': {
      const normalized = normalizeClassify(activity, response);
      return Object.freeze({
        scored: true,
        normalized,
        correct: orderedPairsEqual(normalized.assignments, activity.assignments ?? [], 'itemId', 'bucketId'),
      });
    }
    case 'productive':
      return evaluateProductive(activity, response);
    case 'lesson':
      return Object.freeze({ scored: false, normalized: normalizeLesson(response), completed: true });
    case 'flashcard':
      return Object.freeze({ scored: false, normalized: normalizeFlashcard(response), completed: true });
    default:
      throw new ActivityResponseValidationError(`Unsupported activity type ${String(activity?.type)}`, 'unsupported_activity');
  }
}
