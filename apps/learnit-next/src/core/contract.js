import { normalizeConstructedText, V4_ACTIVITY_TYPES } from './activity_semantics.js';

export const CONTRACT_VERSION = 'learnit.kit.v2';
export const SUPPORTED_CONTRACT_VERSIONS = Object.freeze([
  'learnit.kit.v2', 'learnit.kit.v3', 'learnit.kit.v4',
]);

const CONTRACTS = new Set(SUPPORTED_CONTRACT_VERSIONS);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const DIGEST = /^sha256:[0-9a-f]{64}$/;
const CLAIM_ID = /^atlas-claim-sha256:[0-9a-f]{64}$/;
const LANGUAGE = /^[a-z]{2}(?:-[A-Z]{2})?$/;
const DIFFICULTY = new Set(['easy', 'medium', 'advanced', 'expert']);
const PHASE = new Set(['activation', 'comprehension', 'application', 'transfer', 'consolidation', 'diagnostic', 'validation']);
const ROLE = new Set(['practice', 'diagnostic', 'validation']);
const BASIS = new Set(['new-instance', 'new-context', 'alternate-representation']);
const MEDIA_FORMAT = new Set(['svg', 'png', 'jpeg', 'webp']);
const MEDIA_ROLE = new Set(['concept_visual', 'question_stimulus', 'worked_example', 'misconception_fix', 'diagram_to_interpret', 'memory_anchor']);
const MEDIA_PLACEMENT = new Set(['prompt', 'content', 'feedback']);
const MEDIA_DISPLAY = new Set(['contained', 'full_width']);
const V2_TYPES = new Set(['qcm', 'fill']);
const V3_TYPES = new Set(['qcm', 'fill', 'constructed']);
const V4_TYPES = new Set(V4_ACTIVITY_TYPES);
const EVALUATED_TYPES = new Set(['qcm', 'fill', 'constructed', 'matching', 'order', 'classify']);

export class ContractValidationError extends Error {
  constructor(errors) {
    super(errors[0]?.message ?? 'Package validation failed');
    this.name = 'ContractValidationError';
    this.errors = errors;
  }
}

function issue(errors, code, path, message) { errors.push({ code, path, message }); }
function plain(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function object(value, path, errors) {
  if (!plain(value)) { issue(errors, 'type', path, 'Expected an object'); return false; }
  return true;
}
function string(value, path, errors, { min = 0, max, pattern, constant } = {}) {
  if (typeof value !== 'string') { issue(errors, 'type', path, 'Expected a string'); return false; }
  const size = Array.from(value).length;
  if (size < min) issue(errors, 'min_length', path, `Expected at least ${min} character(s)`);
  if (max !== undefined && size > max) issue(errors, 'max_length', path, `Expected at most ${max} character(s)`);
  if (pattern && !pattern.test(value)) issue(errors, 'pattern', path, 'String does not match the required format');
  if (constant !== undefined && value !== constant) issue(errors, 'const', path, `Expected ${constant}`);
  return true;
}
function integer(value, path, errors, min, max) {
  if (!Number.isInteger(value)) { issue(errors, 'type', path, 'Expected an integer'); return false; }
  if (min !== undefined && value < min) issue(errors, 'minimum', path, `Expected at least ${min}`);
  if (max !== undefined && value > max) issue(errors, 'maximum', path, `Expected at most ${max}`);
  return true;
}
function array(value, path, errors, min, max) {
  if (!Array.isArray(value)) { issue(errors, 'type', path, 'Expected an array'); return false; }
  if (min !== undefined && value.length < min) issue(errors, 'min_items', path, `Expected at least ${min} item(s)`);
  if (max !== undefined && value.length > max) issue(errors, 'max_items', path, `Expected at most ${max} item(s)`);
  return true;
}
function exactKeys(value, allowed, required, path, errors) {
  for (const key of required) if (!Object.hasOwn(value, key)) issue(errors, 'required', `${path}.${key}`, 'Required property is missing');
  for (const key of Object.keys(value)) if (!allowed.has(key)) issue(errors, 'additional_property', `${path}.${key}`, 'Property is not allowed');
}
function uniqueStrings(values, path, errors, code = 'unique_items') {
  const seen = new Set();
  values.forEach((value, index) => {
    if (seen.has(value)) issue(errors, code, `${path}[${index}]`, 'Value is duplicated');
    seen.add(value);
  });
}
function uuid(value, path, errors) { return string(value, path, errors, { pattern: UUID }); }
function digest(value, path, errors) { return string(value, path, errors, { pattern: DIGEST }); }
function enumValue(value, allowed, path, errors) {
  if (typeof value !== 'string' || !allowed.has(value)) issue(errors, 'enum', path, `Expected one of: ${[...allowed].join(', ')}`);
}

function compareCodePoints(left, right) {
  const a = Array.from(left, character => character.codePointAt(0));
  const b = Array.from(right, character => character.codePointAt(0));
  const length = Math.min(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    if (a[index] !== b[index]) return a[index] - b[index];
  }
  return a.length - b.length;
}

function canonicalize(value, root, omitRootKey) {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value.normalize('NFC'));
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (!Number.isInteger(value) || !Number.isFinite(value)) throw new TypeError('Only finite integers are supported in canonical JSON');
    return Object.is(value, -0) ? '0' : String(value);
  }
  if (Array.isArray(value)) return `[${value.map(entry => canonicalize(entry, false, omitRootKey)).join(',')}]`;
  if (plain(value)) {
    const normalized = new Map();
    for (const originalKey of Object.keys(value)) {
      if (root && originalKey === omitRootKey) continue;
      const key = originalKey.normalize('NFC');
      if (normalized.has(key)) throw new TypeError('Object keys collide after NFC normalization');
      normalized.set(key, originalKey);
    }
    const keys = [...normalized.keys()].sort(compareCodePoints);
    return `{${keys.map(key => `${JSON.stringify(key)}:${canonicalize(value[normalized.get(key)], false, omitRootKey)}`).join(',')}}`;
  }
  throw new TypeError('Unsupported JSON value');
}

export function canonicalJson(value, { omitRootKey } = {}) {
  return canonicalize(value, true, omitRootKey);
}

export async function sha256Canonical(value, options = {}) {
  if (!globalThis.crypto?.subtle) throw new Error('Web Crypto SHA-256 is unavailable in this environment');
  const bytes = new TextEncoder().encode(canonicalJson(value, options));
  const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return `sha256:${[...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, '0')).join('')}`;
}

function typeSet(contract) {
  if (contract === 'learnit.kit.v2') return V2_TYPES;
  if (contract === 'learnit.kit.v3') return V3_TYPES;
  if (contract === 'learnit.kit.v4') return V4_TYPES;
  return new Set();
}

const PACKAGE_BASE = ['contract', 'packageLineageId', 'packageRevisionId', 'packageRevisionDigest', 'title', 'description', 'versionLabel', 'language', 'courses'];
const COURSE_KEYS = new Set(['courseLineageId', 'courseRevisionId', 'courseRevisionDigest', 'title', 'subtitle', 'estimatedMinutes', 'objectives', 'activities', 'atlasValidationIndependenceClaims']);
const OBJECTIVE_KEYS = new Set(['objectiveId', 'label']);
const EVAL_COMMON = ['activityLineageId', 'activityRevisionId', 'activityRevisionDigest', 'objectiveIds', 'type', 'prompt', 'explanation', 'difficulty', 'learningPhase', 'assessmentRole', 'estimatedMinutes'];
const UNIT_COMMON = ['activityLineageId', 'activityRevisionId', 'activityRevisionDigest', 'objectiveIds', 'type', 'learningPhase', 'estimatedMinutes'];

function validateObjective(value, path, errors) {
  if (!object(value, path, errors)) return;
  exactKeys(value, OBJECTIVE_KEYS, OBJECTIVE_KEYS, path, errors);
  uuid(value.objectiveId, `${path}.objectiveId`, errors);
  string(value.label, `${path}.label`, errors, { min: 1, max: 180 });
}

function validateMediaRef(value, path, errors) {
  if (!object(value, path, errors)) return;
  const allowed = new Set(['assetId', 'placement', 'display', 'zoomable']);
  exactKeys(value, allowed, new Set(['assetId']), path, errors);
  uuid(value.assetId, `${path}.assetId`, errors);
  if (Object.hasOwn(value, 'placement')) enumValue(value.placement, MEDIA_PLACEMENT, `${path}.placement`, errors);
  if (Object.hasOwn(value, 'display')) enumValue(value.display, MEDIA_DISPLAY, `${path}.display`, errors);
  if (Object.hasOwn(value, 'zoomable') && typeof value.zoomable !== 'boolean') issue(errors, 'type', `${path}.zoomable`, 'Expected a boolean');
}

function svgSecurityReason(data) {
  const raw = String(data ?? '').trim();
  if (!/^<svg(?:\s|>)/i.test(raw) || !/(?:<\/svg\s*>|<svg\b[^>]*\/\s*>)\s*$/i.test(raw)) return 'SVG must be an inline <svg> document';
  if (/<\s*(?:script|foreignObject|iframe|object|embed|link|meta|style|animate|animateMotion|animateTransform|set)\b/i.test(raw)) return 'SVG contains active or forbidden elements';
  if (/\son[a-z0-9:_-]+\s*=/i.test(raw)) return 'SVG event attributes are forbidden';
  if (/\s(?:href|xlink:href|src)\s*=\s*["'](?!\s*#)[^"']+["']/i.test(raw)) return 'SVG external references are forbidden';
  if (/(?:javascript|vbscript|data|https?|file|blob)\s*:/i.test(raw)) return 'SVG active/external URI is forbidden';
  for (const match of raw.matchAll(/url\s*\(([^)]*)\)/gi)) {
    const value = match[1].trim().replace(/^['"]|['"]$/g, '');
    if (!/^#[A-Za-z_][\w:.-]*$/.test(value)) return 'SVG external url() is forbidden';
  }
  return null;
}

function rasterSecurityReason(format, data) {
  const raw = String(data ?? '').trim();
  const mime = format === 'jpeg' ? 'jpeg' : format;
  const pattern = new RegExp(`^data:image/${mime};base64,[A-Za-z0-9+/=\\s]+$`, 'i');
  if (!pattern.test(raw)) return `${format} data must be an embedded base64 data:image/${mime} payload`;
  return null;
}

function validateAsset(value, path, errors) {
  if (!object(value, path, errors)) return;
  const allowed = new Set(['assetId', 'type', 'format', 'alt', 'caption', 'pedagogicalRole', 'data']);
  const required = new Set(['assetId', 'type', 'format', 'alt', 'pedagogicalRole', 'data']);
  exactKeys(value, allowed, required, path, errors);
  uuid(value.assetId, `${path}.assetId`, errors);
  string(value.type, `${path}.type`, errors, { constant: 'image' });
  enumValue(value.format, MEDIA_FORMAT, `${path}.format`, errors);
  string(value.alt, `${path}.alt`, errors, { min: 1, max: 500 });
  if (Object.hasOwn(value, 'caption')) string(value.caption, `${path}.caption`, errors, { max: 800 });
  enumValue(value.pedagogicalRole, MEDIA_ROLE, `${path}.pedagogicalRole`, errors);
  if (string(value.data, `${path}.data`, errors, { min: 1, max: 5000000 })) {
    if (value.format === 'svg') {
      const reason = svgSecurityReason(value.data);
      if (reason) issue(errors, 'unsafe_svg', `${path}.data`, reason);
    } else if (MEDIA_FORMAT.has(value.format)) {
      const reason = rasterSecurityReason(value.format, value.data);
      if (reason) issue(errors, 'unsafe_media', `${path}.data`, reason);
    }
  }
}

function validateCommon(activity, path, errors, v4, evaluated = true) {
  uuid(activity.activityLineageId, `${path}.activityLineageId`, errors);
  uuid(activity.activityRevisionId, `${path}.activityRevisionId`, errors);
  digest(activity.activityRevisionDigest, `${path}.activityRevisionDigest`, errors);
  if (array(activity.objectiveIds, `${path}.objectiveIds`, errors, 1, 8)) {
    activity.objectiveIds.forEach((id, index) => uuid(id, `${path}.objectiveIds[${index}]`, errors));
    uniqueStrings(activity.objectiveIds, `${path}.objectiveIds`, errors);
  }
  enumValue(activity.learningPhase, PHASE, `${path}.learningPhase`, errors);
  if (Object.hasOwn(activity, 'estimatedMinutes')) integer(activity.estimatedMinutes, `${path}.estimatedMinutes`, errors, 1, 30);
  if (evaluated) {
    string(activity.prompt, `${path}.prompt`, errors, { min: 1, max: 1200 });
    string(activity.explanation, `${path}.explanation`, errors, { min: 1, max: 2000 });
    enumValue(activity.difficulty, DIFFICULTY, `${path}.difficulty`, errors);
    enumValue(activity.assessmentRole, ROLE, `${path}.assessmentRole`, errors);
  }
  if (v4 && Object.hasOwn(activity, 'media')) {
    if (array(activity.media, `${path}.media`, errors, 0, 2)) activity.media.forEach((ref, index) => validateMediaRef(ref, `${path}.media[${index}]`, errors));
  }
}

function validateItems(values, path, errors, idKey, labelMax, maxItems) {
  if (!array(values, path, errors, 2, maxItems)) return;
  values.forEach((value, index) => {
    const p = `${path}[${index}]`;
    if (!object(value, p, errors)) return;
    const allowed = new Set([idKey, 'label']);
    exactKeys(value, allowed, allowed, p, errors);
    uuid(value[idKey], `${p}.${idKey}`, errors);
    string(value.label, `${p}.label`, errors, { min: 1, max: labelMax });
  });
  uniqueStrings(values.map(value => value?.[idKey]), path, errors);
}

function validateActivity(activity, path, errors, contract) {
  if (!object(activity, path, errors)) return;
  const supported = typeSet(contract);
  if (!supported.has(activity.type)) {
    issue(errors, 'activity_type', `${path}.type`, `Activity type ${String(activity.type)} is not admitted by ${contract}`);
    return;
  }
  const v4 = contract === 'learnit.kit.v4';
  const mediaKey = v4 ? ['media'] : [];
  if (EVALUATED_TYPES.has(activity.type)) validateCommon(activity, path, errors, v4, true);
  else validateCommon(activity, path, errors, v4, false);

  if (activity.type === 'qcm') {
    const allowed = new Set([...EVAL_COMMON, ...mediaKey, 'choices', 'correctChoiceId']);
    exactKeys(activity, allowed, new Set([...EVAL_COMMON.filter(k => k !== 'estimatedMinutes'), 'choices', 'correctChoiceId']), path, errors);
    if (array(activity.choices, `${path}.choices`, errors, 2, 12)) {
      activity.choices.forEach((choice, index) => {
        const p = `${path}.choices[${index}]`;
        if (!object(choice, p, errors)) return;
        exactKeys(choice, new Set(['choiceId', 'label']), new Set(['choiceId', 'label']), p, errors);
        uuid(choice.choiceId, `${p}.choiceId`, errors);
        string(choice.label, `${p}.label`, errors, { min: 1, max: 500 });
      });
      uniqueStrings(activity.choices.map(choice => choice?.choiceId), `${path}.choices`, errors);
    }
    uuid(activity.correctChoiceId, `${path}.correctChoiceId`, errors);
    return;
  }
  if (activity.type === 'fill') {
    const allowed = new Set([...EVAL_COMMON, ...mediaKey, 'segments', 'tokens', 'answers']);
    exactKeys(activity, allowed, new Set([...EVAL_COMMON.filter(k => k !== 'estimatedMinutes'), 'segments', 'tokens', 'answers']), path, errors);
    if (array(activity.segments, `${path}.segments`, errors, 2, 60)) activity.segments.forEach((segment, index) => {
      const p = `${path}.segments[${index}]`;
      if (!object(segment, p, errors)) return;
      const keys = Object.keys(segment);
      if (keys.length !== 1 || !['text', 'slotId'].includes(keys[0])) { issue(errors, 'one_of', p, 'Fill segment must contain exactly one text or slotId'); return; }
      if (keys[0] === 'text') string(segment.text, `${p}.text`, errors, { min: 1, max: 1000 }); else uuid(segment.slotId, `${p}.slotId`, errors);
    });
    if (array(activity.tokens, `${path}.tokens`, errors, 1, 40)) activity.tokens.forEach((token, index) => {
      const p = `${path}.tokens[${index}]`;
      if (!object(token, p, errors)) return;
      exactKeys(token, new Set(['tokenId', 'label', 'maxUses']), new Set(['tokenId', 'label', 'maxUses']), p, errors);
      uuid(token.tokenId, `${p}.tokenId`, errors); string(token.label, `${p}.label`, errors, { min: 1, max: 300 }); integer(token.maxUses, `${p}.maxUses`, errors, 1, 20);
    });
    if (array(activity.answers, `${path}.answers`, errors, 1, 30)) activity.answers.forEach((answer, index) => {
      const p = `${path}.answers[${index}]`;
      if (!object(answer, p, errors)) return;
      exactKeys(answer, new Set(['slotId', 'tokenId']), new Set(['slotId', 'tokenId']), p, errors);
      uuid(answer.slotId, `${p}.slotId`, errors); uuid(answer.tokenId, `${p}.tokenId`, errors);
    });
    return;
  }
  if (activity.type === 'constructed') {
    const allowed = new Set([...EVAL_COMMON, ...mediaKey, 'acceptedResponses']);
    exactKeys(activity, allowed, new Set([...EVAL_COMMON.filter(k => k !== 'estimatedMinutes'), 'acceptedResponses']), path, errors);
    if (array(activity.acceptedResponses, `${path}.acceptedResponses`, errors, 1, 20)) activity.acceptedResponses.forEach((value, index) => string(value, `${path}.acceptedResponses[${index}]`, errors, { min: 1, max: 4000 }));
    return;
  }
  if (activity.type === 'lesson') {
    const allowed = new Set([...UNIT_COMMON, ...mediaKey, 'title', 'body', 'keyPoints', 'contextNote']);
    exactKeys(activity, allowed, new Set([...UNIT_COMMON.filter(k => k !== 'estimatedMinutes'), 'title', 'body']), path, errors);
    string(activity.title, `${path}.title`, errors, { min: 1, max: 180 });
    string(activity.body, `${path}.body`, errors, { min: 1, max: 6000 });
    if (Object.hasOwn(activity, 'keyPoints') && array(activity.keyPoints, `${path}.keyPoints`, errors, 0, 8)) {
      activity.keyPoints.forEach((value, index) => string(value, `${path}.keyPoints[${index}]`, errors, { min: 1, max: 800 })); uniqueStrings(activity.keyPoints, `${path}.keyPoints`, errors);
    }
    if (Object.hasOwn(activity, 'contextNote')) string(activity.contextNote, `${path}.contextNote`, errors, { max: 1600 });
    return;
  }
  if (activity.type === 'flashcard') {
    const allowed = new Set([...UNIT_COMMON, ...mediaKey, 'front', 'back', 'explanation']);
    exactKeys(activity, allowed, new Set([...UNIT_COMMON.filter(k => k !== 'estimatedMinutes'), 'front', 'back', 'explanation']), path, errors);
    string(activity.front, `${path}.front`, errors, { min: 1, max: 1200 });
    string(activity.back, `${path}.back`, errors, { min: 1, max: 2000 });
    string(activity.explanation, `${path}.explanation`, errors, { min: 1, max: 2000 });
    return;
  }
  if (activity.type === 'matching') {
    const allowed = new Set([...EVAL_COMMON, ...mediaKey, 'leftItems', 'rightItems', 'matches']);
    exactKeys(activity, allowed, new Set([...EVAL_COMMON.filter(k => k !== 'estimatedMinutes'), 'leftItems', 'rightItems', 'matches']), path, errors);
    validateItems(activity.leftItems, `${path}.leftItems`, errors, 'itemId', 600, 12);
    validateItems(activity.rightItems, `${path}.rightItems`, errors, 'itemId', 600, 12);
    if (array(activity.matches, `${path}.matches`, errors, 2, 12)) activity.matches.forEach((match, index) => {
      const p = `${path}.matches[${index}]`; if (!object(match, p, errors)) return;
      exactKeys(match, new Set(['leftItemId', 'rightItemId']), new Set(['leftItemId', 'rightItemId']), p, errors);
      uuid(match.leftItemId, `${p}.leftItemId`, errors); uuid(match.rightItemId, `${p}.rightItemId`, errors);
    });
    return;
  }
  if (activity.type === 'order') {
    const allowed = new Set([...EVAL_COMMON, ...mediaKey, 'items', 'correctOrder']);
    exactKeys(activity, allowed, new Set([...EVAL_COMMON.filter(k => k !== 'estimatedMinutes'), 'items', 'correctOrder']), path, errors);
    validateItems(activity.items, `${path}.items`, errors, 'itemId', 800, 15);
    if (array(activity.correctOrder, `${path}.correctOrder`, errors, 2, 15)) { activity.correctOrder.forEach((id, index) => uuid(id, `${path}.correctOrder[${index}]`, errors)); uniqueStrings(activity.correctOrder, `${path}.correctOrder`, errors); }
    return;
  }
  if (activity.type === 'classify') {
    const allowed = new Set([...EVAL_COMMON, ...mediaKey, 'buckets', 'items', 'assignments']);
    exactKeys(activity, allowed, new Set([...EVAL_COMMON.filter(k => k !== 'estimatedMinutes'), 'buckets', 'items', 'assignments']), path, errors);
    validateItems(activity.buckets, `${path}.buckets`, errors, 'bucketId', 300, 8);
    validateItems(activity.items, `${path}.items`, errors, 'itemId', 600, 30);
    if (array(activity.assignments, `${path}.assignments`, errors, 2, 30)) activity.assignments.forEach((assignment, index) => {
      const p = `${path}.assignments[${index}]`; if (!object(assignment, p, errors)) return;
      exactKeys(assignment, new Set(['itemId', 'bucketId']), new Set(['itemId', 'bucketId']), p, errors);
      uuid(assignment.itemId, `${p}.itemId`, errors); uuid(assignment.bucketId, `${p}.bucketId`, errors);
    });
  }
}

function validateClaim(claim, path, errors) {
  if (!object(claim, path, errors)) return;
  const keys = new Set(['claimVersion', 'claimId', 'objectiveId', 'sourceActivityLineageId', 'targetActivityLineageId', 'basisCode', 'sourceStimulusDigest', 'targetStimulusDigest']);
  exactKeys(claim, keys, keys, path, errors);
  string(claim.claimVersion, `${path}.claimVersion`, errors, { constant: 'atlas.independence.v1' });
  string(claim.claimId, `${path}.claimId`, errors, { pattern: CLAIM_ID });
  uuid(claim.objectiveId, `${path}.objectiveId`, errors); uuid(claim.sourceActivityLineageId, `${path}.sourceActivityLineageId`, errors); uuid(claim.targetActivityLineageId, `${path}.targetActivityLineageId`, errors);
  enumValue(claim.basisCode, BASIS, `${path}.basisCode`, errors); digest(claim.sourceStimulusDigest, `${path}.sourceStimulusDigest`, errors); digest(claim.targetStimulusDigest, `${path}.targetStimulusDigest`, errors);
}

function validateCourse(course, path, errors, contract) {
  if (!object(course, path, errors)) return;
  const required = new Set(['courseLineageId', 'courseRevisionId', 'courseRevisionDigest', 'title', 'estimatedMinutes', 'objectives', 'activities']);
  exactKeys(course, COURSE_KEYS, required, path, errors);
  uuid(course.courseLineageId, `${path}.courseLineageId`, errors); uuid(course.courseRevisionId, `${path}.courseRevisionId`, errors); digest(course.courseRevisionDigest, `${path}.courseRevisionDigest`, errors);
  string(course.title, `${path}.title`, errors, { min: 1, max: 180 }); if (Object.hasOwn(course, 'subtitle')) string(course.subtitle, `${path}.subtitle`, errors, { max: 300 }); integer(course.estimatedMinutes, `${path}.estimatedMinutes`, errors, 1, 600);
  if (array(course.objectives, `${path}.objectives`, errors, 1, 30)) course.objectives.forEach((value, index) => validateObjective(value, `${path}.objectives[${index}]`, errors));
  if (array(course.activities, `${path}.activities`, errors, 1, 200)) course.activities.forEach((value, index) => validateActivity(value, `${path}.activities[${index}]`, errors, contract));
  if (Object.hasOwn(course, 'atlasValidationIndependenceClaims') && array(course.atlasValidationIndependenceClaims, `${path}.atlasValidationIndependenceClaims`, errors, 0, 500)) course.atlasValidationIndependenceClaims.forEach((value, index) => validateClaim(value, `${path}.atlasValidationIndependenceClaims[${index}]`, errors));
}

function validateShape(payload, errors) {
  if (!object(payload, '$', errors)) return;
  const contract = payload.contract;
  if (typeof contract !== 'string' || !CONTRACTS.has(contract)) {
    issue(errors, 'unsupported_contract', '$.contract', `Unsupported contract ${String(contract)}`);
    return;
  }
  const allowed = new Set([...PACKAGE_BASE, ...(contract === 'learnit.kit.v4' ? ['assets'] : [])]);
  const required = new Set(PACKAGE_BASE.filter(k => k !== 'description'));
  exactKeys(payload, allowed, required, '$', errors);
  uuid(payload.packageLineageId, '$.packageLineageId', errors); uuid(payload.packageRevisionId, '$.packageRevisionId', errors); digest(payload.packageRevisionDigest, '$.packageRevisionDigest', errors);
  string(payload.title, '$.title', errors, { min: 1, max: 180 }); if (Object.hasOwn(payload, 'description')) string(payload.description, '$.description', errors, { max: 2000 }); string(payload.versionLabel, '$.versionLabel', errors, { min: 1, max: 80 }); string(payload.language, '$.language', errors, { pattern: LANGUAGE });
  if (contract === 'learnit.kit.v4' && Object.hasOwn(payload, 'assets') && array(payload.assets, '$.assets', errors, 0, 100)) payload.assets.forEach((asset, index) => validateAsset(asset, `$.assets[${index}]`, errors));
  if (array(payload.courses, '$.courses', errors, 1, 20)) payload.courses.forEach((course, index) => validateCourse(course, `$.courses[${index}]`, errors, contract));
}

function semanticValidation(payload, errors) {
  const assetById = new Map((payload.assets ?? []).map(asset => [asset.assetId, asset]));
  if ((payload.assets ?? []).length !== assetById.size) issue(errors, 'unique_items', '$.assets', 'assetId values must be unique');
  const registry = new Map();
  const globalRevision = new Map();
  const registerId = (category, id, path) => {
    const categoryRegistry = registry.get(category) ?? new Map();
    registry.set(category, categoryRegistry);
    const previousPath = categoryRegistry.get(id);
    if (previousPath) issue(errors, 'duplicate_id', path, `${category} duplicates ${previousPath}`);
    else categoryRegistry.set(id, path);
  };
  const registerRevision = (id, declared, path) => {
    registerId('revisionId', id, path);
    const previous = globalRevision.get(id);
    if (previous && previous.digest !== declared) issue(errors, 'revision_digest_conflict', path, `Revision ID conflicts with ${previous.path}`);
    else if (!previous) globalRevision.set(id, { digest: declared, path });
  };
  registerId('packageLineageId', payload.packageLineageId, '$.packageLineageId');
  registerRevision(payload.packageRevisionId, payload.packageRevisionDigest, '$.packageRevisionId');
  for (let ai = 0; ai < (payload.assets ?? []).length; ai += 1) registerId('assetId', payload.assets[ai].assetId, `$.assets[${ai}].assetId`);

  payload.courses.forEach((course, ci) => {
    const cp = `$.courses[${ci}]`;
    registerId('courseLineageId', course.courseLineageId, `${cp}.courseLineageId`); registerRevision(course.courseRevisionId, course.courseRevisionDigest, `${cp}.courseRevisionId`);
    const objectiveIds = new Set();
    course.objectives.forEach((objective, oi) => { registerId('objectiveId', objective.objectiveId, `${cp}.objectives[${oi}].objectiveId`); objectiveIds.add(objective.objectiveId); });
    const activityByLineage = new Map();
    course.activities.forEach((activity, ai) => {
      const ap = `${cp}.activities[${ai}]`;
      registerId('activityLineageId', activity.activityLineageId, `${ap}.activityLineageId`); registerRevision(activity.activityRevisionId, activity.activityRevisionDigest, `${ap}.activityRevisionId`); activityByLineage.set(activity.activityLineageId, activity);
      activity.objectiveIds.forEach(id => { if (!objectiveIds.has(id)) issue(errors, 'missing_objective_reference', `${ap}.objectiveIds`, `Unknown objectiveId ${id}`); });
      if (payload.contract === 'learnit.kit.v4') (activity.media ?? []).forEach((ref, mi) => { if (!assetById.has(ref.assetId)) issue(errors, 'missing_asset_reference', `${ap}.media[${mi}].assetId`, `Unknown assetId ${ref.assetId}`); });
      if (activity.type === 'qcm') {
        activity.choices.forEach((choice, index) => registerId('choiceId', choice.choiceId, `${ap}.choices[${index}].choiceId`)); const ids = new Set(activity.choices.map(choice => choice.choiceId)); if (!ids.has(activity.correctChoiceId)) issue(errors, 'missing_choice_reference', `${ap}.correctChoiceId`, 'correctChoiceId is not declared in choices');
      } else if (activity.type === 'fill') {
        const slots = activity.segments.filter(segment => Object.hasOwn(segment, 'slotId')).map(segment => segment.slotId); activity.segments.forEach((segment, index) => { if (Object.hasOwn(segment, 'slotId')) registerId('slotId', segment.slotId, `${ap}.segments[${index}].slotId`); });
        const tokens = activity.tokens.map(token => token.tokenId); activity.tokens.forEach((token, index) => registerId('tokenId', token.tokenId, `${ap}.tokens[${index}].tokenId`)); const slotSet = new Set(slots); const tokenSet = new Set(tokens); const answerSlots = new Set(); const usage = new Map();
        activity.answers.forEach((answer, index) => { if (!slotSet.has(answer.slotId)) issue(errors, 'missing_slot_reference', `${ap}.answers[${index}].slotId`, 'Unknown slotId'); if (!tokenSet.has(answer.tokenId)) issue(errors, 'missing_token_reference', `${ap}.answers[${index}].tokenId`, 'Unknown tokenId'); if (answerSlots.has(answer.slotId)) issue(errors, 'duplicate_slot_answer', `${ap}.answers[${index}].slotId`, 'Each slot must have one answer'); answerSlots.add(answer.slotId); usage.set(answer.tokenId, (usage.get(answer.tokenId) ?? 0) + 1); });
        if (answerSlots.size !== slotSet.size || slots.some(id => !answerSlots.has(id))) issue(errors, 'incomplete_fill_answers', `${ap}.answers`, 'Every fill slot must have exactly one authored answer');
        activity.tokens.forEach(token => { if ((usage.get(token.tokenId) ?? 0) > token.maxUses) issue(errors, 'max_uses', `${ap}.answers`, `Authored token ${token.tokenId} exceeds maxUses`); });
      } else if (activity.type === 'constructed') {
        const normalized = activity.acceptedResponses.map(value => normalizeConstructedText(value));
        normalized.forEach((value, index) => { if (!value) issue(errors, 'blank_accepted_response', `${ap}.acceptedResponses[${index}]`, 'Accepted response is blank after normalization'); });
        if (new Set(normalized).size !== normalized.length) issue(errors, 'ambiguous_accepted_responses', `${ap}.acceptedResponses`, 'Accepted responses collapse to duplicates after canonical text normalization');
      } else if (activity.type === 'matching') {
        activity.leftItems.forEach((item, index) => registerId('matchingLeftItemId', item.itemId, `${ap}.leftItems[${index}].itemId`)); activity.rightItems.forEach((item, index) => registerId('matchingRightItemId', item.itemId, `${ap}.rightItems[${index}].itemId`)); const left = activity.leftItems.map(item => item.itemId); const right = activity.rightItems.map(item => item.itemId); const leftSet = new Set(left); const rightSet = new Set(right);
        if (leftSet.size !== left.length || rightSet.size !== right.length) issue(errors, 'unique_items', ap, 'Matching item IDs must be unique');
        if ([...leftSet].some(id => rightSet.has(id))) issue(errors, 'ambiguous_matching_ids', ap, 'Left and right matching IDs must be disjoint');
        if (left.length !== right.length || activity.matches.length !== left.length) issue(errors, 'incomplete_matching_definition', `${ap}.matches`, 'Matching must define a complete one-to-one relation');
        const seenLeft = new Set(); const seenRight = new Set();
        activity.matches.forEach((match, index) => { if (!leftSet.has(match.leftItemId)) issue(errors, 'missing_matching_reference', `${ap}.matches[${index}].leftItemId`, 'Unknown leftItemId'); if (!rightSet.has(match.rightItemId)) issue(errors, 'missing_matching_reference', `${ap}.matches[${index}].rightItemId`, 'Unknown rightItemId'); if (seenLeft.has(match.leftItemId) || seenRight.has(match.rightItemId)) issue(errors, 'ambiguous_matching_definition', `${ap}.matches[${index}]`, 'Matching must be one-to-one'); seenLeft.add(match.leftItemId); seenRight.add(match.rightItemId); });
      } else if (activity.type === 'order') {
        activity.items.forEach((item, index) => registerId('orderItemId', item.itemId, `${ap}.items[${index}].itemId`)); const ids = activity.items.map(item => item.itemId); const itemSet = new Set(ids); if (itemSet.size !== ids.length) issue(errors, 'unique_items', `${ap}.items`, 'Order item IDs must be unique'); if (activity.correctOrder.length !== ids.length || activity.correctOrder.some(id => !itemSet.has(id))) issue(errors, 'incomplete_order_definition', `${ap}.correctOrder`, 'correctOrder must contain every authored item exactly once');
      } else if (activity.type === 'classify') {
        activity.items.forEach((item, index) => registerId('classifyItemId', item.itemId, `${ap}.items[${index}].itemId`)); activity.buckets.forEach((bucket, index) => registerId('bucketId', bucket.bucketId, `${ap}.buckets[${index}].bucketId`)); const items = activity.items.map(item => item.itemId); const buckets = activity.buckets.map(bucket => bucket.bucketId); const itemSet = new Set(items); const bucketSet = new Set(buckets); if (itemSet.size !== items.length || bucketSet.size !== buckets.length) issue(errors, 'unique_items', ap, 'Classify IDs must be unique'); if (activity.assignments.length !== items.length) issue(errors, 'incomplete_classification_definition', `${ap}.assignments`, 'Every item must have exactly one authored bucket'); const seen = new Set(); activity.assignments.forEach((assignment, index) => { if (!itemSet.has(assignment.itemId)) issue(errors, 'missing_classification_reference', `${ap}.assignments[${index}].itemId`, 'Unknown itemId'); if (!bucketSet.has(assignment.bucketId)) issue(errors, 'missing_classification_reference', `${ap}.assignments[${index}].bucketId`, 'Unknown bucketId'); if (seen.has(assignment.itemId)) issue(errors, 'multiple_classification', `${ap}.assignments[${index}].itemId`, 'Item has multiple authored buckets'); seen.add(assignment.itemId); });
      }
    });
    (course.atlasValidationIndependenceClaims ?? []).forEach((claim, index) => {
      const p = `${cp}.atlasValidationIndependenceClaims[${index}]`; const source = activityByLineage.get(claim.sourceActivityLineageId); const target = activityByLineage.get(claim.targetActivityLineageId);
      if (!objectiveIds.has(claim.objectiveId)) issue(errors, 'reference', `${p}.objectiveId`, 'Unknown objective'); if (!source) issue(errors, 'reference', `${p}.sourceActivityLineageId`, 'Unknown source activity'); if (!target) issue(errors, 'reference', `${p}.targetActivityLineageId`, 'Unknown target activity'); if (claim.sourceActivityLineageId === claim.targetActivityLineageId) issue(errors, 'relation', p, 'Validation activities must be distinct'); if (source && !source.objectiveIds.includes(claim.objectiveId)) issue(errors, 'relation', p, 'Source activity is not linked to objective'); if (target && !target.objectiveIds.includes(claim.objectiveId)) issue(errors, 'relation', p, 'Target activity is not linked to objective');
    });
  });
  return globalRevision;
}

async function validateDigests(payload, revisions, errors) {
  for (let ci = 0; ci < payload.courses.length; ci += 1) {
    const course = payload.courses[ci];
    for (let ai = 0; ai < course.activities.length; ai += 1) {
      const activity = course.activities[ai]; const calculated = await sha256Canonical(activity, { omitRootKey: 'activityRevisionDigest' }); if (calculated !== activity.activityRevisionDigest) issue(errors, 'digest_mismatch', `$.courses[${ci}].activities[${ai}].activityRevisionDigest`, `Declared digest does not match ${calculated}`);
    }
    const courseDigest = await sha256Canonical(course, { omitRootKey: 'courseRevisionDigest' }); if (courseDigest !== course.courseRevisionDigest) issue(errors, 'digest_mismatch', `$.courses[${ci}].courseRevisionDigest`, `Declared digest does not match ${courseDigest}`);
  }
  const packageDigest = await sha256Canonical(payload, { omitRootKey: 'packageRevisionDigest' }); if (packageDigest !== payload.packageRevisionDigest) issue(errors, 'digest_mismatch', '$.packageRevisionDigest', `Declared digest does not match ${packageDigest}`);
  return revisions;
}

export async function validatePackageObject(payload, { existingRevisionDigests } = {}) {
  const errors = [];
  validateShape(payload, errors);
  if (errors.length) return { ok: false, contractVersion: typeof payload?.contract === 'string' ? payload.contract : null, errors };
  const revisions = semanticValidation(payload, errors);
  await validateDigests(payload, revisions, errors);
  if (existingRevisionDigests) for (const [revisionId, entry] of revisions) {
    const existing = existingRevisionDigests.get(revisionId); if (existing && existing !== entry.digest) issue(errors, 'existing_revision_digest_conflict', entry.path, `Stored revision ${revisionId} has digest ${existing}`);
  }
  return { ok: errors.length === 0, contractVersion: payload.contract, errors, revisionDigests: new Map([...revisions].map(([id, entry]) => [id, entry.digest])) };
}

export async function assertValidPackage(payload, options) {
  const result = await validatePackageObject(payload, options);
  if (!result.ok) throw new ContractValidationError(result.errors);
  return result;
}
