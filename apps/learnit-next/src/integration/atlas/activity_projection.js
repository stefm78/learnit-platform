const V5_CONTRACT = 'learnit.kit.v5';
const V6_CONTRACT = 'learnit.kit.v6';

function freezeList(values) {
  return Object.freeze(values.map(value => Object.freeze(value)));
}

function resolveMedia(activity, assets = [], accept = () => true) {
  const assetById = new Map((assets ?? []).map(asset => [asset.assetId, asset]));
  return freezeList((activity.media ?? []).filter(accept).map(ref => {
    const asset = assetById.get(ref.assetId);
    if (!asset) throw new Error(`ACTIVITY_MEDIA_ASSET_NOT_FOUND:${ref.assetId}`);
    return {
      assetId: asset.assetId,
      format: asset.format,
      alt: asset.alt,
      ...(Object.hasOwn(asset, 'caption') ? { caption: asset.caption } : {}),
      pedagogicalRole: asset.pedagogicalRole,
      data: asset.data,
      ...(Object.hasOwn(ref, 'placement') ? { placement: ref.placement } : {}),
      ...(Object.hasOwn(ref, 'display') ? { display: ref.display } : {}),
      ...(Object.hasOwn(ref, 'zoomable') ? { zoomable: ref.zoomable } : {}),
    };
  }));
}

function matchingRightItems(activity) {
  const right = (activity.rightItems ?? []).map(item => ({ itemId: item.itemId, label: item.label }));
  if (right.length < 2) return right;
  const expected = new Map((activity.matches ?? []).map(match => [match.leftItemId, match.rightItemId]));
  const exposesSolution = (activity.leftItems ?? []).length === right.length
    && activity.leftItems.every((left, index) => expected.get(left.itemId) === right[index]?.itemId);
  if (!exposesSolution) return right;
  return [...right.slice(1), right[0]];
}

function projectReferences(references = []) {
  return freezeList(references.map(reference => ({
    url: reference.url,
    label: reference.label,
    hook: reference.hook,
  })));
}

export function projectFeedbackMedia(
  activity,
  { assets = [], contract = null, transitionAuthorized = false } = {},
) {
  if (contract !== V5_CONTRACT && contract !== V6_CONTRACT) return Object.freeze([]);
  if (transitionAuthorized !== true) {
    throw new Error('V5_FEEDBACK_MEDIA_TRANSITION_REQUIRED');
  }
  return resolveMedia(
    activity,
    assets,
    ref => ref.placement === 'feedback',
  );
}

function readableLabel(items, id, idKey = 'itemId') {
  const item = (items ?? []).find(candidate => candidate?.[idKey] === id);
  if (!item || typeof item.label !== 'string' || !item.label.trim()) {
    throw new Error(`POST_ANSWER_LABEL_NOT_FOUND:${String(id)}`);
  }
  return item.label;
}

function frozenLines(values) {
  return Object.freeze(values.map(value => String(value)));
}

export function projectPostAnswerFeedback(
  activity,
  normalizedAnswer,
  { contract = null, transitionAuthorized = false } = {},
) {
  if (contract !== V5_CONTRACT && contract !== V6_CONTRACT) return null;
  if (transitionAuthorized !== true) {
    throw new Error('V5_POST_ANSWER_TRANSITION_REQUIRED');
  }
  if (!activity || typeof activity !== 'object' || Array.isArray(activity)) {
    throw new TypeError('Activity source must be an object');
  }
  if (!normalizedAnswer || typeof normalizedAnswer !== 'object' || Array.isArray(normalizedAnswer)) {
    throw new TypeError('Normalized post-answer response is required');
  }

  let learnerAnswer;
  let expectedAnswer;
  let comparisonRows = null;

  switch (activity.type) {
    case 'qcm':
      learnerAnswer = frozenLines([
        readableLabel(activity.choices, normalizedAnswer.choiceId, 'choiceId'),
      ]);
      expectedAnswer = frozenLines([
        readableLabel(activity.choices, activity.correctChoiceId, 'choiceId'),
      ]);
      break;
    case 'fill': {
      const expected = new Map((activity.answers ?? []).map(entry => [entry.slotId, entry.tokenId]));
      const slotIds = (activity.segments ?? [])
        .filter(segment => Object.hasOwn(segment, 'slotId'))
        .map(segment => segment.slotId);
      learnerAnswer = frozenLines(slotIds.map((slotId, index) =>
        `Emplacement ${index + 1} : ${readableLabel(activity.tokens, normalizedAnswer[slotId], 'tokenId')}`));
      expectedAnswer = frozenLines(slotIds.map((slotId, index) =>
        `Emplacement ${index + 1} : ${readableLabel(activity.tokens, expected.get(slotId), 'tokenId')}`));
      break;
    }
    case 'constructed':
      learnerAnswer = frozenLines([normalizedAnswer.text]);
      expectedAnswer = frozenLines(activity.acceptedResponses ?? []);
      break;
    case 'matching': {
      const submitted = new Map((normalizedAnswer.associations ?? []).map(entry => [entry.leftItemId, entry.rightItemId]));
      const expected = new Map((activity.matches ?? []).map(entry => [entry.leftItemId, entry.rightItemId]));
      comparisonRows = freezeList((activity.leftItems ?? []).map(left => ({
        item: left.label,
        learner: readableLabel(activity.rightItems, submitted.get(left.itemId), 'itemId'),
        expected: readableLabel(activity.rightItems, expected.get(left.itemId), 'itemId'),
      })));
      learnerAnswer = frozenLines(comparisonRows.map(row => row.learner));
      expectedAnswer = frozenLines(comparisonRows.map(row => row.expected));
      break;
    }
    case 'order':
      learnerAnswer = frozenLines((normalizedAnswer.orderedItemIds ?? []).map((itemId, index) =>
        `${index + 1}. ${readableLabel(activity.items, itemId, 'itemId')}`));
      expectedAnswer = frozenLines((activity.correctOrder ?? []).map((itemId, index) =>
        `${index + 1}. ${readableLabel(activity.items, itemId, 'itemId')}`));
      break;
    case 'classify': {
      const submitted = new Map((normalizedAnswer.assignments ?? []).map(entry => [entry.itemId, entry.bucketId]));
      const expected = new Map((activity.assignments ?? []).map(entry => [entry.itemId, entry.bucketId]));
      comparisonRows = freezeList((activity.items ?? []).map(item => ({
        item: item.label,
        learner: readableLabel(activity.buckets, submitted.get(item.itemId), 'bucketId'),
        expected: readableLabel(activity.buckets, expected.get(item.itemId), 'bucketId'),
      })));
      learnerAnswer = frozenLines(comparisonRows.map(row => row.learner));
      expectedAnswer = frozenLines(comparisonRows.map(row => row.expected));
      break;
    }
    case 'lesson':
    case 'flashcard':
    case 'productive':
      return null;
    default:
      throw new Error(`ACTIVITY_TYPE_UNSUPPORTED:${String(activity.type)}`);
  }

  const promptText = activity.prompt ?? activity.title ?? activity.front ?? 'Activité';
  return Object.freeze({
    type: activity.type,
    prompt: String(promptText),
    learnerAnswer,
    expectedAnswer,
    ...(comparisonRows ? { comparisonRows } : {}),
  });
}

export function projectActivityPresentation(activity, { assets = [], contract = null } = {}) {
  if (!activity || typeof activity !== 'object' || Array.isArray(activity)) {
    throw new TypeError('Activity source must be an object');
  }
  const v5 = contract === V5_CONTRACT;
  const v6 = contract === V6_CONTRACT;
  const rich = v5 || v6;
  const media = resolveMedia(
    activity,
    assets,
    ref => !rich || ref.placement !== 'feedback',
  );
  let presentation;
  switch (activity.type) {
    case 'qcm':
      presentation = {
        type: 'qcm',
        prompt: activity.prompt,
        choices: freezeList((activity.choices ?? []).map(choice => ({ choiceId: choice.choiceId, label: choice.label }))),
        media,
      };
      break;
    case 'fill':
      presentation = {
        type: 'fill',
        prompt: activity.prompt,
        tokens: freezeList((activity.tokens ?? []).map(token => ({ tokenId: token.tokenId, label: token.label }))),
        segments: freezeList((activity.segments ?? []).map(segment => (
          Object.hasOwn(segment, 'text') ? { text: segment.text } : { slotId: segment.slotId }
        ))),
        media,
      };
      break;
    case 'constructed':
      presentation = { type: 'constructed', prompt: activity.prompt, media };
      break;
    case 'productive':
      if (!v6) throw new Error('PRODUCTIVE_REQUIRES_V6');
      presentation = {
        type: 'productive',
        prompt: activity.prompt,
        parts: freezeList((activity.parts ?? []).map(part => ({
          partId: part.partId,
          label: part.label,
          responseKind: part.responseKind,
          ...(Object.hasOwn(part, 'unitPrompt') ? { unitPrompt: part.unitPrompt } : {}),
        }))),
        media,
      };
      break;
    case 'lesson':
      presentation = {
        type: 'lesson',
        title: activity.title,
        body: activity.body,
        ...(Object.hasOwn(activity, 'keyPoints') ? { keyPoints: Object.freeze([...activity.keyPoints]) } : {}),
        ...(Object.hasOwn(activity, 'contextNote') ? { contextNote: activity.contextNote } : {}),
        media,
      };
      break;
    case 'flashcard':
      presentation = {
        type: 'flashcard',
        front: activity.front,
        back: activity.back,
        explanation: activity.explanation,
        media,
      };
      break;
    case 'matching':
      presentation = {
        type: 'matching',
        prompt: activity.prompt,
        leftItems: freezeList((activity.leftItems ?? []).map(item => ({ itemId: item.itemId, label: item.label }))),
        rightItems: freezeList(matchingRightItems(activity)),
        media,
      };
      break;
    case 'order':
      presentation = {
        type: 'order',
        prompt: activity.prompt,
        items: freezeList((activity.items ?? []).map(item => ({ itemId: item.itemId, label: item.label }))),
        media,
      };
      break;
    case 'classify':
      presentation = {
        type: 'classify',
        prompt: activity.prompt,
        buckets: freezeList((activity.buckets ?? []).map(bucket => ({ bucketId: bucket.bucketId, label: bucket.label }))),
        items: freezeList((activity.items ?? []).map(item => ({ itemId: item.itemId, label: item.label }))),
        media,
      };
      break;
    default:
      throw new Error(`ACTIVITY_TYPE_UNSUPPORTED:${String(activity.type)}`);
  }
  if (rich && Array.isArray(activity.references) && activity.references.length) {
    presentation = {
      ...presentation,
      references: projectReferences(activity.references),
    };
  }
  return Object.freeze(presentation);
}
