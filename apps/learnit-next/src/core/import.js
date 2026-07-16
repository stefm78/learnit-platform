import { assertValidPackage, validatePackageObject, CONTRACT_VERSION } from './contract.js';
import { createInstallationId } from './identity.js';

const UNSUPPORTED_CONTRACT_MESSAGE = 'Format non pris en charge : ce fichier n’est pas un kit learnit.kit.v2. Les formats legacy ne sont ni importés ni migrés.';
const INVALID_PACKAGE_MESSAGE = 'Le kit learnit.kit.v2 est invalide et n’a pas été importé.';

class DomainImportError extends Error {
  constructor(name, code, message, { cause, errors = [] } = {}) {
    super(message, { cause });
    this.name = name;
    this.code = code;
    this.errors = errors;
  }
}

export class ContractError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) {
    super('ContractError', 'ERR_CONTRACT', message, options);
  }
}

export class SchemaValidationError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) {
    super('SchemaValidationError', 'ERR_SCHEMA', message, options);
  }
}

export class DigestMismatchError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) {
    super('DigestMismatchError', 'ERR_DIGEST', message, options);
  }
}

export class RevisionConflictError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) {
    super('RevisionConflictError', 'ERR_REVISION_CONFLICT', message, options);
  }
}

export class LegacyContractError extends DomainImportError {
  constructor(message = UNSUPPORTED_CONTRACT_MESSAGE, options) {
    super('LegacyContractError', 'ERR_LEGACY', message, options);
  }
}

export class ImportRejectedError extends DomainImportError {
  constructor(message, options) {
    super('ImportRejectedError', 'ERR_IMPORT_REJECTED', message, options);
  }
}

const SCHEMA_ERROR_CODES = new Set([
  'type',
  'required',
  'additional_property',
  'min_length',
  'max_length',
  'pattern',
  'const',
  'minimum',
  'maximum',
  'min_items',
  'max_items',
  'unique_items',
  'one_of',
  'enum',
  'activity_type',
]);

function domainValidationError(error) {
  if (error instanceof DomainImportError) return error;
  const errors = Array.isArray(error?.errors) ? error.errors : [];
  const codes = new Set(errors.map((entry) => entry.code));
  const options = { cause: error, errors };
  if (codes.has('digest_mismatch')) return new DigestMismatchError(INVALID_PACKAGE_MESSAGE, options);
  if (codes.has('revision_digest_conflict') || codes.has('existing_revision_digest_conflict')) {
    return new RevisionConflictError(INVALID_PACKAGE_MESSAGE, options);
  }
  if ([...codes].some((code) => SCHEMA_ERROR_CODES.has(code))) {
    return new SchemaValidationError(INVALID_PACKAGE_MESSAGE, options);
  }
  return new ContractError(INVALID_PACKAGE_MESSAGE, options);
}

export function parsePackagePayload(payload) {
  if (typeof payload === 'string') {
    try {
      return JSON.parse(payload);
    } catch (error) {
      throw new ImportRejectedError('The selected file is not valid JSON', { cause: error });
    }
  }
  if (payload && typeof payload === 'object') {
    try {
      return structuredClone(payload);
    } catch (error) {
      throw new ImportRejectedError('The selected package cannot be cloned as JSON data', { cause: error });
    }
  }
  throw new ImportRejectedError('A JSON string or object is required');
}

export function assertSupportedContract(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload) || payload.contract !== CONTRACT_VERSION) {
    throw new LegacyContractError();
  }
  return payload;
}

function validationResultFromError(error) {
  return {
    ok: false,
    contractVersion: CONTRACT_VERSION,
    errors: [{
      code: error.code ?? 'ERR_IMPORT_REJECTED',
      path: error.code === 'ERR_LEGACY' ? '$.contract' : '$',
      message: error.message,
    }],
  };
}

async function assertInstallablePackage(parsed, storage) {
  try {
    await assertValidPackage(parsed);
  } catch (error) {
    throw domainValidationError(error);
  }
  const existingRevisionDigests = await storage.getRevisionDigestIndex();
  try {
    await assertValidPackage(parsed, { existingRevisionDigests });
  } catch (error) {
    throw domainValidationError(error);
  }
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
        assertSupportedContract(parsed);
      } catch (error) {
        return validationResultFromError(error);
      }
      const localValidation = await validatePackageObject(parsed);
      if (!localValidation.ok) return localValidation;
      const existingRevisionDigests = await storage.getRevisionDigestIndex();
      return validatePackageObject(parsed, { existingRevisionDigests });
    },

    async previewImport(payload) {
      const parsed = parsePackagePayload(payload);
      assertSupportedContract(parsed);
      await assertInstallablePackage(parsed, storage);
      return makeSummary(parsed);
    },

    async importPackage(payload) {
      const parsed = parsePackagePayload(payload);
      assertSupportedContract(parsed);
      await assertInstallablePackage(parsed, storage);

      const plan = buildInstallationPlan(parsed);
      await storage.commitImport(plan);

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
