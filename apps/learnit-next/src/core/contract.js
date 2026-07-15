import { sha256Canonical } from './canonical_json.js';
import { UUID_V4_PATTERN, addUniqueId } from './identity.js';

export const CONTRACT_VERSION = 'learnit.kit.v2';
const DIGEST_PATTERN = /^sha256:[0-9a-f]{64}$/;
const LANGUAGE_PATTERN = /^[a-z]{2}(?:-[A-Z]{2})?$/;
const DIFFICULTIES = new Set(['easy', 'medium', 'advanced', 'expert']);
const LEARNING_PHASES = new Set([
  'activation',
  'comprehension',
  'application',
  'transfer',
  'consolidation',
  'diagnostic',
  'validation',
]);
const ASSESSMENT_ROLES = new Set(['practice', 'diagnostic', 'validation']);

const PACKAGE_KEYS = new Set([
  'contract',
  'packageLineageId',
  'packageRevisionId',
  'packageRevisionDigest',
  'title',
  'description',
  'versionLabel',
  'language',
  'courses',
]);
const COURSE_KEYS = new Set([
  'courseLineageId',
  'courseRevisionId',
  'courseRevisionDigest',
  'title',
  'subtitle',
  'estimatedMinutes',
  'objectives',
  'activities',
]);
const OBJECTIVE_KEYS = new Set(['objectiveId', 'label']);
const ACTIVITY_COMMON_KEYS = [
  'activityLineageId',
  'activityRevisionId',
  'activityRevisionDigest',
  'objectiveIds',
  'type',
  'prompt',
  'explanation',
  'difficulty',
  'learningPhase',
  'assessmentRole',
];
const QCM_KEYS = new Set([...ACTIVITY_COMMON_KEYS, 'choices', 'correctChoiceId']);
const FILL_KEYS = new Set([...ACTIVITY_COMMON_KEYS, 'segments', 'tokens', 'answers']);
const CHOICE_KEYS = new Set(['choiceId', 'label']);
const TOKEN_KEYS = new Set(['tokenId', 'label', 'maxUses']);
const ANSWER_KEYS = new Set(['slotId', 'tokenId']);

export class ContractValidationError extends Error {
  constructor(errors) {
    super(errors[0]?.message ?? 'Package validation failed');
    this.name = 'ContractValidationError';
    this.errors = errors;
  }
}

function issue(errors, code, path, message) {
  errors.push({ code, path, message });
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
}

function requireObject(value, path, errors) {
  if (!isPlainObject(value)) {
    issue(errors, 'type', path, 'Expected an object');
    return false;
  }
  return true;
}

function exactKeys(value, allowed, required, path, errors) {
  for (const key of required) {
    if (!Object.hasOwn(value, key)) issue(errors, 'required', `${path}.${key}`, 'Required property is missing');
  }
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) issue(errors, 'additional_property', `${path}.${key}`, 'Property is not allowed by learnit.kit.v2');
  }
}

function stringValue(value, path, errors, { min = 0, max, pattern, constant } = {}) {
  if (typeof value !== 'string') {
    issue(errors, 'type', path, 'Expected a string');
    return false;
  }
  if (value.length < min) issue(errors, 'min_length', path, `Expected at least ${min} character(s)`);
  if (max !== undefined && value.length > max) issue(errors, 'max_length', path, `Expected at most ${max} character(s)`);
  if (pattern && !pattern.test(value)) issue(errors, 'pattern', path, 'String does not match the required format');
  if (constant !== undefined && value !== constant) issue(errors, 'const', path, `Expected ${constant}`);
  return true;
}

function integerValue(value, path, errors, { min, max } = {}) {
  if (!Number.isInteger(value)) {
    issue(errors, 'type', path, 'Expected an integer');
    return false;
  }
  if (min !== undefined && value < min) issue(errors, 'minimum', path, `Expected a value of at least ${min}`);
  if (max !== undefined && value > max) issue(errors, 'maximum', path, `Expected a value of at most ${max}`);
  return true;
}

function arrayValue(value, path, errors, { min, max } = {}) {
  if (!Array.isArray(value)) {
    issue(errors, 'type', path, 'Expected an array');
    return false;
  }
  if (min !== undefined && value.length < min) issue(errors, 'min_items', path, `Expected at least ${min} item(s)`);
  if (max !== undefined && value.length > max) issue(errors, 'max_items', path, `Expected at most ${max} item(s)`);
  return true;
}

function uuidValue(value, path, errors) {
  return stringValue(value, path, errors, { pattern: UUID_V4_PATTERN });
}

function digestValue(value, path, errors) {
  return stringValue(value, path, errors, { pattern: DIGEST_PATTERN });
}

function enumValue(value, allowed, path, errors) {
  if (typeof value !== 'string' || !allowed.has(value)) {
    issue(errors, 'enum', path, `Expected one of: ${[...allowed].join(', ')}`);
    return false;
  }
  return true;
}

function validateObjectiveShape(objective, path, errors) {
  if (!requireObject(objective, path, errors)) return;
  exactKeys(objective, OBJECTIVE_KEYS, OBJECTIVE_KEYS, path, errors);
  uuidValue(objective.objectiveId, `${path}.objectiveId`, errors);
  stringValue(objective.label, `${path}.label`, errors, { min: 1, max: 180 });
}

function validateActivityCommonShape(activity, path, errors) {
  uuidValue(activity.activityLineageId, `${path}.activityLineageId`, errors);
  uuidValue(activity.activityRevisionId, `${path}.activityRevisionId`, errors);
  digestValue(activity.activityRevisionDigest, `${path}.activityRevisionDigest`, errors);
  if (arrayValue(activity.objectiveIds, `${path}.objectiveIds`, errors, { min: 1, max: 8 })) {
    const seen = new Set();
    activity.objectiveIds.forEach((id, index) => {
      uuidValue(id, `${path}.objectiveIds[${index}]`, errors);
      if (seen.has(id)) issue(errors, 'unique_items', `${path}.objectiveIds[${index}]`, 'Objective reference is duplicated');
      seen.add(id);
    });
  }
  stringValue(activity.prompt, `${path}.prompt`, errors, { min: 1, max: 1200 });
  stringValue(activity.explanation, `${path}.explanation`, errors, { min: 1, max: 2000 });
  enumValue(activity.difficulty, DIFFICULTIES, `${path}.difficulty`, errors);
  enumValue(activity.learningPhase, LEARNING_PHASES, `${path}.learningPhase`, errors);
  enumValue(activity.assessmentRole, ASSESSMENT_ROLES, `${path}.assessmentRole`, errors);
}

function validateQcmShape(activity, path, errors) {
  exactKeys(activity, QCM_KEYS, QCM_KEYS, path, errors);
  validateActivityCommonShape(activity, path, errors);
  stringValue(activity.type, `${path}.type`, errors, { constant: 'qcm' });
  if (arrayValue(activity.choices, `${path}.choices`, errors, { min: 2, max: 12 })) {
    activity.choices.forEach((choice, index) => {
      const choicePath = `${path}.choices[${index}]`;
      if (!requireObject(choice, choicePath, errors)) return;
      exactKeys(choice, CHOICE_KEYS, CHOICE_KEYS, choicePath, errors);
      uuidValue(choice.choiceId, `${choicePath}.choiceId`, errors);
      stringValue(choice.label, `${choicePath}.label`, errors, { min: 1, max: 500 });
    });
  }
  uuidValue(activity.correctChoiceId, `${path}.correctChoiceId`, errors);
}

function validateFillShape(activity, path, errors) {
  exactKeys(activity, FILL_KEYS, FILL_KEYS, path, errors);
  validateActivityCommonShape(activity, path, errors);
  stringValue(activity.type, `${path}.type`, errors, { constant: 'fill' });

  if (arrayValue(activity.segments, `${path}.segments`, errors, { min: 2, max: 60 })) {
    activity.segments.forEach((segment, index) => {
      const segmentPath = `${path}.segments[${index}]`;
      if (!requireObject(segment, segmentPath, errors)) return;
      const keys = Object.keys(segment);
      if (keys.length !== 1 || (keys[0] !== 'text' && keys[0] !== 'slotId')) {
        issue(errors, 'one_of', segmentPath, 'A fill segment must contain exactly one text or slotId property');
        return;
      }
      if (keys[0] === 'text') stringValue(segment.text, `${segmentPath}.text`, errors, { min: 1, max: 1000 });
      else uuidValue(segment.slotId, `${segmentPath}.slotId`, errors);
    });
  }

  if (arrayValue(activity.tokens, `${path}.tokens`, errors, { min: 1, max: 40 })) {
    activity.tokens.forEach((token, index) => {
      const tokenPath = `${path}.tokens[${index}]`;
      if (!requireObject(token, tokenPath, errors)) return;
      exactKeys(token, TOKEN_KEYS, TOKEN_KEYS, tokenPath, errors);
      uuidValue(token.tokenId, `${tokenPath}.tokenId`, errors);
      stringValue(token.label, `${tokenPath}.label`, errors, { min: 1, max: 300 });
      integerValue(token.maxUses, `${tokenPath}.maxUses`, errors, { min: 1, max: 20 });
    });
  }

  if (arrayValue(activity.answers, `${path}.answers`, errors, { min: 1, max: 30 })) {
    activity.answers.forEach((answer, index) => {
      const answerPath = `${path}.answers[${index}]`;
      if (!requireObject(answer, answerPath, errors)) return;
      exactKeys(answer, ANSWER_KEYS, ANSWER_KEYS, answerPath, errors);
      uuidValue(answer.slotId, `${answerPath}.slotId`, errors);
      uuidValue(answer.tokenId, `${answerPath}.tokenId`, errors);
    });
  }
}

function validateActivityShape(activity, path, errors) {
  if (!requireObject(activity, path, errors)) return;
  if (activity.type === 'qcm') validateQcmShape(activity, path, errors);
  else if (activity.type === 'fill') validateFillShape(activity, path, errors);
  else issue(errors, 'activity_type', `${path}.type`, 'Only qcm and fill activities are supported');
}

function validateCourseShape(course, path, errors) {
  if (!requireObject(course, path, errors)) return;
  const required = new Set([...COURSE_KEYS].filter((key) => key !== 'subtitle'));
  exactKeys(course, COURSE_KEYS, required, path, errors);
  uuidValue(course.courseLineageId, `${path}.courseLineageId`, errors);
  uuidValue(course.courseRevisionId, `${path}.courseRevisionId`, errors);
  digestValue(course.courseRevisionDigest, `${path}.courseRevisionDigest`, errors);
  stringValue(course.title, `${path}.title`, errors, { min: 1, max: 180 });
  if (Object.hasOwn(course, 'subtitle')) stringValue(course.subtitle, `${path}.subtitle`, errors, { max: 300 });
  integerValue(course.estimatedMinutes, `${path}.estimatedMinutes`, errors, { min: 1, max: 600 });
  if (arrayValue(course.objectives, `${path}.objectives`, errors, { min: 1, max: 30 })) {
    course.objectives.forEach((objective, index) => validateObjectiveShape(objective, `${path}.objectives[${index}]`, errors));
  }
  if (arrayValue(course.activities, `${path}.activities`, errors, { min: 1, max: 200 })) {
    course.activities.forEach((activity, index) => validateActivityShape(activity, `${path}.activities[${index}]`, errors));
  }
}

function validatePackageShape(payload, errors) {
  if (!requireObject(payload, '$', errors)) return;
  const required = new Set([...PACKAGE_KEYS].filter((key) => key !== 'description'));
  exactKeys(payload, PACKAGE_KEYS, required, '$', errors);
  stringValue(payload.contract, '$.contract', errors, { constant: CONTRACT_VERSION });
  uuidValue(payload.packageLineageId, '$.packageLineageId', errors);
  uuidValue(payload.packageRevisionId, '$.packageRevisionId', errors);
  digestValue(payload.packageRevisionDigest, '$.packageRevisionDigest', errors);
  stringValue(payload.title, '$.title', errors, { min: 1, max: 180 });
  if (Object.hasOwn(payload, 'description')) stringValue(payload.description, '$.description', errors, { max: 2000 });
  stringValue(payload.versionLabel, '$.versionLabel', errors, { min: 1, max: 80 });
  stringValue(payload.language, '$.language', errors, { pattern: LANGUAGE_PATTERN });
  if (arrayValue(payload.courses, '$.courses', errors, { min: 1, max: 20 })) {
    payload.courses.forEach((course, index) => validateCourseShape(course, `$.courses[${index}]`, errors));
  }
}

function semanticValidation(payload, errors) {
  const registry = new Map();
  const revisionRegistry = new Map();

  const registerRevision = (revisionId, digest, path) => {
    addUniqueId(registry, 'revisionId', revisionId, path, errors);
    const previous = revisionRegistry.get(revisionId);
    if (previous && previous.digest !== digest) {
      issue(errors, 'revision_digest_conflict', path, `Revision ID conflicts with ${previous.path}`);
    } else if (!previous) {
      revisionRegistry.set(revisionId, { digest, path });
    }
  };

  addUniqueId(registry, 'packageLineageId', payload.packageLineageId, '$.packageLineageId', errors);
  registerRevision(payload.packageRevisionId, payload.packageRevisionDigest, '$.packageRevisionId');

  payload.courses.forEach((course, courseIndex) => {
    const coursePath = `$.courses[${courseIndex}]`;
    addUniqueId(registry, 'courseLineageId', course.courseLineageId, `${coursePath}.courseLineageId`, errors);
    registerRevision(course.courseRevisionId, course.courseRevisionDigest, `${coursePath}.courseRevisionId`);

    const objectiveIds = new Set();
    course.objectives.forEach((objective, objectiveIndex) => {
      const objectivePath = `${coursePath}.objectives[${objectiveIndex}].objectiveId`;
      addUniqueId(registry, 'objectiveId', objective.objectiveId, objectivePath, errors);
      objectiveIds.add(objective.objectiveId);
    });

    course.activities.forEach((activity, activityIndex) => {
      const activityPath = `${coursePath}.activities[${activityIndex}]`;
      addUniqueId(registry, 'activityLineageId', activity.activityLineageId, `${activityPath}.activityLineageId`, errors);
      registerRevision(activity.activityRevisionId, activity.activityRevisionDigest, `${activityPath}.activityRevisionId`);

      for (const objectiveId of activity.objectiveIds) {
        if (!objectiveIds.has(objectiveId)) {
          issue(errors, 'missing_objective_reference', `${activityPath}.objectiveIds`, `Unknown objectiveId ${objectiveId}`);
        }
      }

      if (activity.type === 'qcm') {
        const choiceIds = new Set();
        activity.choices.forEach((choice, choiceIndex) => {
          const choicePath = `${activityPath}.choices[${choiceIndex}].choiceId`;
          addUniqueId(registry, 'choiceId', choice.choiceId, choicePath, errors);
          choiceIds.add(choice.choiceId);
        });
        if (!choiceIds.has(activity.correctChoiceId)) {
          issue(errors, 'missing_choice_reference', `${activityPath}.correctChoiceId`, 'correctChoiceId is not declared in choices');
        }
      }

      if (activity.type === 'fill') {
        const slotIds = new Set();
        activity.segments.forEach((segment, segmentIndex) => {
          if (!Object.hasOwn(segment, 'slotId')) return;
          const slotPath = `${activityPath}.segments[${segmentIndex}].slotId`;
          addUniqueId(registry, 'slotId', segment.slotId, slotPath, errors);
          slotIds.add(segment.slotId);
        });

        const tokens = new Map();
        activity.tokens.forEach((token, tokenIndex) => {
          const tokenPath = `${activityPath}.tokens[${tokenIndex}].tokenId`;
          addUniqueId(registry, 'tokenId', token.tokenId, tokenPath, errors);
          tokens.set(token.tokenId, token);
        });

        const answeredSlots = new Set();
        const usage = new Map();
        activity.answers.forEach((answer, answerIndex) => {
          const answerPath = `${activityPath}.answers[${answerIndex}]`;
          if (!slotIds.has(answer.slotId)) {
            issue(errors, 'missing_slot_reference', `${answerPath}.slotId`, `Unknown slotId ${answer.slotId}`);
          }
          if (answeredSlots.has(answer.slotId)) {
            issue(errors, 'duplicate_slot_answer', `${answerPath}.slotId`, `slotId ${answer.slotId} has more than one answer`);
          }
          answeredSlots.add(answer.slotId);
          if (!tokens.has(answer.tokenId)) {
            issue(errors, 'missing_token_reference', `${answerPath}.tokenId`, `Unknown tokenId ${answer.tokenId}`);
          }
          usage.set(answer.tokenId, (usage.get(answer.tokenId) ?? 0) + 1);
        });

        for (const slotId of slotIds) {
          if (!answeredSlots.has(slotId)) {
            issue(errors, 'missing_slot_answer', `${activityPath}.answers`, `slotId ${slotId} has no declared answer`);
          }
        }
        for (const [tokenId, count] of usage) {
          const token = tokens.get(tokenId);
          if (token && count > token.maxUses) {
            issue(errors, 'max_uses', `${activityPath}.answers`, `tokenId ${tokenId} is used ${count} times but maxUses is ${token.maxUses}`);
          }
        }
      }
    });
  });

  return revisionRegistry;
}

async function digestValidation(payload, errors) {
  for (let courseIndex = 0; courseIndex < payload.courses.length; courseIndex += 1) {
    const course = payload.courses[courseIndex];
    for (let activityIndex = 0; activityIndex < course.activities.length; activityIndex += 1) {
      const activity = course.activities[activityIndex];
      const calculated = await sha256Canonical(activity, { omitRootKey: 'activityRevisionDigest' });
      if (calculated !== activity.activityRevisionDigest) {
        issue(errors, 'digest_mismatch', `$.courses[${courseIndex}].activities[${activityIndex}].activityRevisionDigest`, `Declared digest does not match ${calculated}`);
      }
    }
    const calculated = await sha256Canonical(course, { omitRootKey: 'courseRevisionDigest' });
    if (calculated !== course.courseRevisionDigest) {
      issue(errors, 'digest_mismatch', `$.courses[${courseIndex}].courseRevisionDigest`, `Declared digest does not match ${calculated}`);
    }
  }
  const calculated = await sha256Canonical(payload, { omitRootKey: 'packageRevisionDigest' });
  if (calculated !== payload.packageRevisionDigest) {
    issue(errors, 'digest_mismatch', '$.packageRevisionDigest', `Declared digest does not match ${calculated}`);
  }
}

function existingDigestValidation(revisions, existingRevisionDigests, errors) {
  if (!existingRevisionDigests) return;
  const get = existingRevisionDigests instanceof Map
    ? (key) => existingRevisionDigests.get(key)
    : (key) => existingRevisionDigests[key];
  for (const [revisionId, entry] of revisions) {
    const existing = get(revisionId);
    if (existing && existing !== entry.digest) {
      issue(errors, 'existing_revision_digest_conflict', entry.path, `Stored revision ${revisionId} has digest ${existing}`);
    }
  }
}

export async function validatePackageObject(payload, { existingRevisionDigests } = {}) {
  const errors = [];
  validatePackageShape(payload, errors);
  if (errors.length > 0) return { ok: false, contractVersion: CONTRACT_VERSION, errors };

  const revisions = semanticValidation(payload, errors);
  if (errors.length === 0) await digestValidation(payload, errors);
  existingDigestValidation(revisions, existingRevisionDigests, errors);

  return {
    ok: errors.length === 0,
    contractVersion: CONTRACT_VERSION,
    errors,
    revisionDigests: new Map([...revisions].map(([id, entry]) => [id, entry.digest])),
  };
}

export async function assertValidPackage(payload, options) {
  const result = await validatePackageObject(payload, options);
  if (!result.ok) throw new ContractValidationError(result.errors);
  return result;
}
