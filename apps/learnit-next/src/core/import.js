import { assertValidPackage, validatePackageObject, CONTRACT_VERSION } from './contract.js';
import { createInstallationId } from './identity.js';

export class ImportError extends Error {
  constructor(message, { code = 'import_failed', cause, errors = [] } = {}) {
    super(message, { cause });
    this.name = 'ImportError';
    this.code = code;
    this.errors = errors;
  }
}

export function parsePackagePayload(payload) {
  if (typeof payload === 'string') {
    try {
      return JSON.parse(payload);
    } catch (error) {
      throw new ImportError('The selected file is not valid JSON', { code: 'malformed_json', cause: error });
    }
  }
  if (payload && typeof payload === 'object') {
    return structuredClone(payload);
  }
  throw new ImportError('A JSON string or object is required', { code: 'invalid_input' });
}

function makeSummary(payload) {
  return {
    contract: payload.contract,
    packageLineageId: payload.packageLineageId,
    packageRevisionId: payload.packageRevisionId,
    title: payload.title,
    versionLabel: payload.versionLabel,
    language: payload.language,
    courseCount: payload.courses.length,
    activityCount: payload.courses.reduce((total, course) => total + course.activities.length, 0),
  };
}

export function collectRevisionDigests(payload) {
  const revisions = [{ revisionId: payload.packageRevisionId, digest: payload.packageRevisionDigest }];
  for (const course of payload.courses) {
    revisions.push({ revisionId: course.courseRevisionId, digest: course.courseRevisionDigest });
    for (const activity of course.activities) {
      revisions.push({ revisionId: activity.activityRevisionId, digest: activity.activityRevisionDigest });
    }
  }
  return revisions;
}

export function buildInstallationPlan(payload, now = new Date()) {
  const packageInstallId = createInstallationId();
  const installedAt = now.toISOString();
  const courses = payload.courses.map((course) => ({
    courseInstallId: createInstallationId(),
    packageInstallId,
    packageLineageId: payload.packageLineageId,
    packageRevisionId: payload.packageRevisionId,
    courseLineageId: course.courseLineageId,
    courseRevisionId: course.courseRevisionId,
    title: course.title,
    displayLabel: course.title,
    subtitle: course.subtitle ?? '',
    estimatedMinutes: course.estimatedMinutes,
    activityCount: course.activities.length,
    course: structuredClone(course),
    installedAt,
  }));

  return {
    package: {
      packageInstallId,
      packageLineageId: payload.packageLineageId,
      packageRevisionId: payload.packageRevisionId,
      packageRevisionDigest: payload.packageRevisionDigest,
      title: payload.title,
      displayLabel: payload.title,
      versionLabel: payload.versionLabel,
      language: payload.language,
      payload: structuredClone(payload),
      installedAt,
    },
    courses,
    revisions: collectRevisionDigests(payload),
    meta: [
      { key: 'schemaVersion', value: 1 },
      { key: 'lastImport', value: { packageInstallId, installedAt } },
    ],
  };
}

export function createImportService(storage) {
  return {
    async validatePackage(payload) {
      let parsed;
      try {
        parsed = parsePackagePayload(payload);
      } catch (error) {
        return {
          ok: false,
          contractVersion: CONTRACT_VERSION,
          errors: [{ code: error.code, path: '$', message: error.message }],
        };
      }
      const localValidation = await validatePackageObject(parsed);
      if (!localValidation.ok) return localValidation;
      const existingRevisionDigests = await storage.getRevisionDigestIndex();
      return validatePackageObject(parsed, { existingRevisionDigests });
    },

    async previewImport(payload) {
      const parsed = parsePackagePayload(payload);
      await assertValidPackage(parsed);
      const existingRevisionDigests = await storage.getRevisionDigestIndex();
      await assertValidPackage(parsed, { existingRevisionDigests });
      return makeSummary(parsed);
    },

    async importPackage(payload) {
      const parsed = parsePackagePayload(payload);
      try {
        await assertValidPackage(parsed);
        const existingRevisionDigests = await storage.getRevisionDigestIndex();
        await assertValidPackage(parsed, { existingRevisionDigests });
      } catch (error) {
        throw new ImportError('Package rejected before storage mutation', {
          code: parsed?.contract === CONTRACT_VERSION ? 'invalid_package' : 'unsupported_contract',
          cause: error,
          errors: error.errors ?? [],
        });
      }

      const plan = buildInstallationPlan(parsed);
      try {
        await storage.commitImport(plan);
      } catch (error) {
        throw new ImportError('The atomic import transaction was aborted', {
          code: 'storage_transaction_aborted',
          cause: error,
        });
      }

      return {
        ...makeSummary(parsed),
        packageInstallId: plan.package.packageInstallId,
        courses: plan.courses.map(({ courseInstallId, courseLineageId, courseRevisionId, displayLabel }) => ({
          courseInstallId,
          courseLineageId,
          courseRevisionId,
          displayLabel,
        })),
      };
    },
  };
}
