export class ActivityResponseValidationError extends Error {
  constructor(message, code = 'invalid_answer') {
    super(message);
    this.name = 'ActivityResponseValidationError';
    this.code = code;
  }
}

export const SCORED_ACTIVITY_TYPES = Object.freeze([
  'qcm', 'fill', 'constructed', 'matching', 'order', 'classify',
]);
export const NON_SCORED_ACTIVITY_TYPES = Object.freeze(['lesson', 'flashcard']);
export const V4_ACTIVITY_TYPES = Object.freeze([
  ...SCORED_ACTIVITY_TYPES,
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
    case 'lesson':
      return Object.freeze({ scored: false, normalized: normalizeLesson(response), completed: true });
    case 'flashcard':
      return Object.freeze({ scored: false, normalized: normalizeFlashcard(response), completed: true });
    default:
      throw new ActivityResponseValidationError(`Unsupported activity type ${String(activity?.type)}`, 'unsupported_activity');
  }
}
