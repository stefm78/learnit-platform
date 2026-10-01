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
export const V6_ACTIVITY_TYPES = Object.freeze([
  ...V4_ACTIVITY_TYPES,
  'productive',
]);

const SCORED = new Set([...SCORED_ACTIVITY_TYPES, 'productive']);
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


function normalizeProductive(activity, response) {
  if (!Array.isArray(response?.parts)) throw new ActivityResponseValidationError('Productive response requires parts[]', 'invalid_productive_response');
  const authored = activity.parts ?? [];
  if (response.parts.length !== authored.length) throw new ActivityResponseValidationError('Productive response must contain every authored part exactly once', 'incomplete_productive_response');
  const authoredIds = new Set(authored.map(part => part.partId)), seen = new Set(), byId = new Map();
  for (const raw of response.parts) {
    const partId = raw?.partId;
    if (typeof partId !== 'string' || !authoredIds.has(partId) || seen.has(partId)) throw new ActivityResponseValidationError('Productive response contains an unknown or duplicate partId', 'invalid_productive_part');
    if (typeof raw.value !== 'string' || !raw.value.trim()) throw new ActivityResponseValidationError('Each productive response part requires non-blank string value', 'blank_productive_part');
    if (Object.hasOwn(raw, 'unit') && (typeof raw.unit !== 'string' || !raw.unit.trim())) throw new ActivityResponseValidationError('Productive response unit must be non-blank when supplied', 'invalid_productive_unit');
    seen.add(partId); byId.set(partId, Object.freeze({ partId, value: raw.value.normalize('NFC').trim(), ...(Object.hasOwn(raw,'unit') ? {unit:raw.unit.normalize('NFC').trim()} : {}) }));
  }
  return Object.freeze({parts:Object.freeze(authored.map(part=>byId.get(part.partId)))});
}
function expressionKey(value){return String(value??'').normalize('NFC').replace(/[−–—]/gu,'-').replace(/\s+/gu,'');}
function conceptKey(value){return String(value??'').normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim().replace(/\s+/gu,' ');}
function decimalRational(value){
  const raw=String(value??'').trim().replace(',','.'),m=/^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(raw);
  if(!m)throw new ActivityResponseValidationError('Numeric productive part must be a finite decimal number','invalid_productive_number');
  const sign=m[1]==='-'?-1n:1n,f=m[3]??'',exp=Number.parseInt(m[4]??'0',10);
  if(!Number.isInteger(exp)||Math.abs(exp)>18)throw new ActivityResponseValidationError('Numeric exponent is outside the bounded deterministic range','invalid_productive_number');
  let numerator=BigInt(m[2]+f)*sign,denominator=10n**BigInt(f.length);
  if(exp>=0)numerator*=10n**BigInt(exp);else denominator*=10n**BigInt(-exp);
  return {numerator,denominator};
}
function authoredRational(value,label){
  if(!value||!Number.isInteger(value.numerator)||!Number.isInteger(value.denominator)||value.denominator<=0)throw new ActivityResponseValidationError(`${label} must be an integer rational with positive denominator`,'invalid_productive_evaluator');
  return {numerator:BigInt(value.numerator),denominator:BigInt(value.denominator)};
}
function withinAbsoluteTolerance(actual,expected,tolerance){
  const diff=actual.numerator*expected.denominator-expected.numerator*actual.denominator,absDiff=diff<0n?-diff:diff;
  return absDiff*tolerance.denominator<=tolerance.numerator*actual.denominator*expected.denominator;
}
function evaluateProductivePart(part,evaluator){
  if(evaluator.kind==='numeric-tolerance'){
    const actual=decimalRational(part.value),expected=authoredRational(evaluator.expected,'expected'),tolerance=authoredRational(evaluator.absoluteTolerance,'absoluteTolerance');
    if(tolerance.numerator<0n)throw new ActivityResponseValidationError('absoluteTolerance cannot be negative','invalid_productive_evaluator');
    const unit=String(part.unit??'').normalize('NFC').trim().toLowerCase(),accepted=(evaluator.acceptedUnits??[]).map(v=>String(v).normalize('NFC').trim().toLowerCase());
    return (accepted.length===0?unit==='':accepted.includes(unit))&&withinAbsoluteTolerance(actual,expected,tolerance);
  }
  if(evaluator.kind==='canonical-expression-set'){const actual=expressionKey(part.value);return actual.length>0&&(evaluator.acceptedExpressions??[]).map(expressionKey).includes(actual);}
  if(evaluator.kind==='required-concepts'){
    const actual=` ${conceptKey(part.value)} `; if(!actual.trim())return false;
    return (evaluator.requiredConceptGroups??[]).every(group=>Array.isArray(group)&&group.some(alias=>{const key=conceptKey(alias);return key.length>0&&actual.includes(` ${key} `);}));
  }
  throw new ActivityResponseValidationError(`Unsupported productive evaluator ${String(evaluator.kind)}`,'unsupported_productive_evaluator');
}
function evaluateProductive(activity,response){
  const normalized=normalizeProductive(activity,response);
  if(activity.scoring?.aggregation!=='all'||!Array.isArray(activity.scoring?.evaluators))throw new ActivityResponseValidationError('Productive scoring requires bounded all-parts aggregation','invalid_productive_evaluator');
  const evaluators=new Map();
  for(const evaluator of activity.scoring.evaluators){if(!evaluator||typeof evaluator.partId!=='string'||evaluators.has(evaluator.partId))throw new ActivityResponseValidationError('Productive evaluator partId is invalid or duplicated','invalid_productive_evaluator');evaluators.set(evaluator.partId,evaluator);}
  const partResults=normalized.parts.map(part=>{const evaluator=evaluators.get(part.partId);if(!evaluator)throw new ActivityResponseValidationError('Productive part has no evaluator','invalid_productive_evaluator');return Object.freeze({partId:part.partId,correct:evaluateProductivePart(part,evaluator)});});
  if(partResults.length!==evaluators.size)throw new ActivityResponseValidationError('Productive evaluator set contains orphan entries','invalid_productive_evaluator');
  return Object.freeze({scored:true,normalized,partResults:Object.freeze(partResults),correct:partResults.every(result=>result.correct)});
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
    case 'productive':
      return evaluateProductive(activity, response);
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
