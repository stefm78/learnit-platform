import { validatePackageObject } from '../../core/contract.js';
import { buildInstallationPlan } from '../../core/import.js';
import { sha256Canonical } from '../../core/canonical_json.js';

const DIGEST = /^sha256:[0-9a-f]{64}$/;
const CLAIM_ID = /^atlas-claim-sha256:[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function parse(payload) {
  if (typeof payload === 'string') return JSON.parse(payload);
  return structuredClone(payload);
}

function isAtlasKit(payload) {
  return Array.isArray(payload?.courses) && payload.courses.some(course =>
    Object.hasOwn(course, 'atlasValidationIndependenceClaims')
    || course.activities?.some(activity =>
      Object.hasOwn(activity, 'estimatedMinutes')
    )
  );
}

function add(errors, code, path, message) {
  errors.push({ code, path, message });
}

function validateExtensions(payload, errors) {
  for (let ci = 0; ci < payload.courses.length; ci += 1) {
    const course = payload.courses[ci];
    const coursePath = `$.courses[${ci}]`;

    for (let ai = 0; ai < course.activities.length; ai += 1) {
      const activity = course.activities[ai];

      if (!Object.hasOwn(activity, 'estimatedMinutes')) continue;

      const path = `${coursePath}.activities[${ai}].estimatedMinutes`;
      const value = activity.estimatedMinutes;

      if (!Number.isInteger(value)) add(errors, 'type', path, 'Expected an integer');
      else if (value < 1) add(errors, 'minimum', path, 'Expected at least 1');
      else if (value > 30) add(errors, 'maximum', path, 'Expected at most 30');
    }

    const claims = course.atlasValidationIndependenceClaims;
    if (claims === undefined) continue;

    if (!Array.isArray(claims)) {
      add(errors, 'type', `${coursePath}.atlasValidationIndependenceClaims`, 'Expected an array');
      continue;
    }

    if (claims.length > 500) {
      add(errors, 'max_items', `${coursePath}.atlasValidationIndependenceClaims`, 'Expected at most 500 claims');
    }

    const objectiveIds = new Set(course.objectives.map(x => x.objectiveId));
    const activities = new Map(course.activities.map(x => [x.activityLineageId, x]));

    claims.forEach((claim, index) => {
      const path = `${coursePath}.atlasValidationIndependenceClaims[${index}]`;

      if (!claim || typeof claim !== 'object' || Array.isArray(claim)) {
        add(errors, 'type', path, 'Expected an object');
        return;
      }

      const required = [
        'claimVersion', 'claimId', 'objectiveId',
        'sourceActivityLineageId', 'targetActivityLineageId',
        'basisCode', 'sourceStimulusDigest', 'targetStimulusDigest',
      ];

      const allowed = new Set(required);

      for (const key of required) {
        if (!Object.hasOwn(claim, key)) {
          add(errors, 'required', `${path}.${key}`, 'Required property is missing');
        }
      }

      for (const key of Object.keys(claim)) {
        if (!allowed.has(key)) {
          add(errors, 'additional_property', `${path}.${key}`, 'Property is not allowed');
        }
      }

      if (claim.claimVersion !== 'atlas.independence.v1') {
        add(errors, 'const', `${path}.claimVersion`, 'Expected atlas.independence.v1');
      }

      if (!CLAIM_ID.test(claim.claimId ?? '')) {
        add(errors, 'pattern', `${path}.claimId`, 'Invalid Atlas claim ID');
      }

      if (!UUID.test(claim.objectiveId ?? '') || !objectiveIds.has(claim.objectiveId)) {
        add(errors, 'reference', `${path}.objectiveId`, 'Unknown objective');
      }

      const source = activities.get(claim.sourceActivityLineageId);
      const target = activities.get(claim.targetActivityLineageId);

      if (!source) add(errors, 'reference', `${path}.sourceActivityLineageId`, 'Unknown source activity');
      if (!target) add(errors, 'reference', `${path}.targetActivityLineageId`, 'Unknown target activity');

      if (
        source
        && target
        && claim.sourceActivityLineageId === claim.targetActivityLineageId
      ) {
        add(errors, 'relation', path, 'Validation activities must be distinct');
      }

      if (source && !source.objectiveIds.includes(claim.objectiveId)) {
        add(errors, 'relation', path, 'Source activity is not linked to the objective');
      }

      if (target && !target.objectiveIds.includes(claim.objectiveId)) {
        add(errors, 'relation', path, 'Target activity is not linked to the objective');
      }

      if (!['new-instance', 'new-context', 'alternate-representation'].includes(claim.basisCode)) {
        add(errors, 'enum', `${path}.basisCode`, 'Invalid independence basis');
      }

      if (!DIGEST.test(claim.sourceStimulusDigest ?? '')) {
        add(errors, 'pattern', `${path}.sourceStimulusDigest`, 'Invalid digest');
      }

      if (!DIGEST.test(claim.targetStimulusDigest ?? '')) {
        add(errors, 'pattern', `${path}.targetStimulusDigest`, 'Invalid digest');
      }
    });
  }
}

async function baseProjection(payload) {
  const projected = structuredClone(payload);

  for (const course of projected.courses) {
    delete course.atlasValidationIndependenceClaims;

    for (const activity of course.activities) {
      delete activity.estimatedMinutes;

      activity.activityRevisionDigest = await sha256Canonical(
        activity,
        { omitRootKey: 'activityRevisionDigest' },
      );
    }

    course.courseRevisionDigest = await sha256Canonical(
      course,
      { omitRootKey: 'courseRevisionDigest' },
    );
  }

  projected.packageRevisionDigest = await sha256Canonical(
    projected,
    { omitRootKey: 'packageRevisionDigest' },
  );

  return projected;
}

async function validateDigests(payload, errors) {
  for (let ci = 0; ci < payload.courses.length; ci += 1) {
    const course = payload.courses[ci];

    for (let ai = 0; ai < course.activities.length; ai += 1) {
      const activity = course.activities[ai];
      const calculated = await sha256Canonical(
        activity,
        { omitRootKey: 'activityRevisionDigest' },
      );

      if (calculated !== activity.activityRevisionDigest) {
        add(
          errors,
          'digest_mismatch',
          `$.courses[${ci}].activities[${ai}].activityRevisionDigest`,
          `Declared digest does not match ${calculated}`,
        );
      }
    }

    const courseDigest = await sha256Canonical(
      course,
      { omitRootKey: 'courseRevisionDigest' },
    );

    if (courseDigest !== course.courseRevisionDigest) {
      add(
        errors,
        'digest_mismatch',
        `$.courses[${ci}].courseRevisionDigest`,
        `Declared digest does not match ${courseDigest}`,
      );
    }
  }

  const packageDigest = await sha256Canonical(
    payload,
    { omitRootKey: 'packageRevisionDigest' },
  );

  if (packageDigest !== payload.packageRevisionDigest) {
    add(
      errors,
      'digest_mismatch',
      '$.packageRevisionDigest',
      `Declared digest does not match ${packageDigest}`,
    );
  }
}

async function validateAtlasPackage(payload, storage) {
  const errors = [];

  validateExtensions(payload, errors);

  const projected = await baseProjection(payload);
  const base = await validatePackageObject(projected);

  errors.push(...base.errors);

  await validateDigests(payload, errors);

  const existing = await storage.getRevisionDigestIndex();

  const revisions = [
    [payload.packageRevisionId, payload.packageRevisionDigest],
  ];

  for (const course of payload.courses) {
    revisions.push([course.courseRevisionId, course.courseRevisionDigest]);

    for (const activity of course.activities) {
      revisions.push([
        activity.activityRevisionId,
        activity.activityRevisionDigest,
      ]);
    }
  }

  for (const [revisionId, digest] of revisions) {
    const previous = existing.get(revisionId);

    if (previous && previous !== digest) {
      add(
        errors,
        'existing_revision_digest_conflict',
        '$',
        `Stored revision ${revisionId} has a conflicting digest`,
      );
    }
  }

  return {
    ok: errors.length === 0,
    contractVersion: 'learnit.kit.v2',
    errors,
  };
}

function fail(result) {
  const error = new Error(
    result.errors[0]?.message ?? 'Atlas kit validation failed',
  );

  error.code = result.errors.some(x => x.code === 'digest_mismatch')
    ? 'ERR_DIGEST'
    : 'ERR_SCHEMA';

  error.errors = result.errors;
  throw error;
}

function summary(payload) {
  return {
    contract: payload.contract,
    packageLineageId: payload.packageLineageId,
    packageRevisionId: payload.packageRevisionId,
    title: payload.title,
    versionLabel: payload.versionLabel,
    language: payload.language,
    courseCount: payload.courses.length,
    activityCount: payload.courses.reduce(
      (total, course) => total + course.activities.length,
      0,
    ),
  };
}

export function createAtlasCompatibleImportService(storage, base) {
  return Object.freeze({
    async validatePackage(payload) {
      let value;

      try {
        value = parse(payload);
      } catch {
        return base.validatePackage(payload);
      }

      if (!isAtlasKit(value)) return base.validatePackage(value);

      return validateAtlasPackage(value, storage);
    },

    async previewImport(payload) {
      const value = parse(payload);

      if (!isAtlasKit(value)) return base.previewImport(value);

      const result = await validateAtlasPackage(value, storage);
      if (!result.ok) fail(result);

      return summary(value);
    },

    async importPackage(payload) {
      const value = parse(payload);

      if (!isAtlasKit(value)) return base.importPackage(value);

      const result = await validateAtlasPackage(value, storage);
      if (!result.ok) fail(result);

      const plan = buildInstallationPlan(value);
      await storage.commitImport(plan);

      return {
        ...summary(value),
        packageInstallId: plan.package.packageInstallId,
        courses: plan.courses.map(course => ({
          courseInstallId: course.courseInstallId,
          courseLineageId: course.courseLineageId,
          courseRevisionId: course.courseRevisionId,
          displayLabel: course.displayLabel,
        })),
      };
    },
  });
}
