const V5_CONTRACT = 'learnit.kit.v5';

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
  if (contract !== V5_CONTRACT) return Object.freeze([]);
  if (transitionAuthorized !== true) {
    throw new Error('V5_FEEDBACK_MEDIA_TRANSITION_REQUIRED');
  }
  return resolveMedia(
    activity,
    assets,
    ref => ref.placement === 'feedback',
  );
}

export function projectActivityPresentation(activity, { assets = [], contract = null } = {}) {
  if (!activity || typeof activity !== 'object' || Array.isArray(activity)) {
    throw new TypeError('Activity source must be an object');
  }
  const v5 = contract === V5_CONTRACT;
  const media = resolveMedia(
    activity,
    assets,
    ref => !v5 || ref.placement !== 'feedback',
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
  if (v5 && Array.isArray(activity.references) && activity.references.length) {
    presentation = {
      ...presentation,
      references: projectReferences(activity.references),
    };
  }
  return Object.freeze(presentation);
}
