import {
  assertValidPackage,
  validatePackageObject,
  SUPPORTED_CONTRACT_VERSIONS,
} from './contract.js';

const SUPPORTED = new Set(SUPPORTED_CONTRACT_VERSIONS);
const INVALID_PACKAGE_MESSAGE = 'Le kit Learn-it est invalide et n’a pas été importé.';
const UNSUPPORTED_CONTRACT_MESSAGE = 'Format non pris en charge : seuls learnit.kit.v2, learnit.kit.v3, learnit.kit.v4 et learnit.kit.v5 sont admis explicitement.';

class DomainImportError extends Error {
  constructor(name, code, message, { cause, errors = [] } = {}) {
    super(message, { cause });
    this.name = name;
    this.code = code;
    this.errors = errors;
  }
}

export class ContractError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) { super('ContractError', 'ERR_CONTRACT', message, options); }
}
export class SchemaValidationError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) { super('SchemaValidationError', 'ERR_SCHEMA', message, options); }
}
export class DigestMismatchError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) { super('DigestMismatchError', 'ERR_DIGEST', message, options); }
}
export class RevisionConflictError extends DomainImportError {
  constructor(message = INVALID_PACKAGE_MESSAGE, options) { super('RevisionConflictError', 'ERR_REVISION_CONFLICT', message, options); }
}
export class LegacyContractError extends DomainImportError {
  constructor(message = UNSUPPORTED_CONTRACT_MESSAGE, options) { super('LegacyContractError', 'ERR_LEGACY', message, options); }
}
export class ImportRejectedError extends DomainImportError {
  constructor(message, options) { super('ImportRejectedError', 'ERR_IMPORT_REJECTED', message, options); }
}

function domainValidationError(error) {
  if (error instanceof DomainImportError) return error;
  const errors = Array.isArray(error?.errors) ? error.errors : [];
  const codes = new Set(errors.map(entry => entry.code));
  const options = { cause: error, errors };
  if (codes.has('digest_mismatch')) return new DigestMismatchError(INVALID_PACKAGE_MESSAGE, options);
  if (codes.has('existing_revision_digest_conflict') || codes.has('revision_digest_conflict')) return new RevisionConflictError(INVALID_PACKAGE_MESSAGE, options);
  if (codes.has('unsupported_contract')) return new LegacyContractError(UNSUPPORTED_CONTRACT_MESSAGE, options);
  return new SchemaValidationError(INVALID_PACKAGE_MESSAGE, options);
}

export function parsePackagePayload(payload) {
  if (typeof payload === 'string') {
    try { return JSON.parse(payload); }
    catch (error) { throw new ImportRejectedError('The selected file is not valid JSON', { cause: error }); }
  }
  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    try { return structuredClone(payload); }
    catch (error) { throw new ImportRejectedError('The selected package cannot be cloned as JSON data', { cause: error }); }
  }
  throw new ImportRejectedError('A JSON string or object is required');
}

export function assertSupportedContract(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload) || !SUPPORTED.has(payload.contract)) {
    throw new LegacyContractError();
  }
  return payload;
}

async function assertInstallablePackage(parsed, storage) {
  try { await assertValidPackage(parsed); }
  catch (error) { throw domainValidationError(error); }
  const existingRevisionDigests = await storage.getRevisionDigestIndex();
  try { await assertValidPackage(parsed, { existingRevisionDigests }); }
  catch (error) { throw domainValidationError(error); }
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
    for (const activity of course.activities) revisions.push({ revisionId: activity.activityRevisionId, digest: activity.activityRevisionDigest });
  }
  return revisions;
}

function installationId() {
  if (typeof globalThis.crypto?.randomUUID !== 'function') {
    throw new Error('Secure UUID generation is unavailable');
  }
  return globalThis.crypto.randomUUID();
}

export function buildInstallationPlan(payload, now = new Date()) {
  const packageInstallId = installationId();
  const installedAt = now.toISOString();
  const packageAssets = ['learnit.kit.v4', 'learnit.kit.v5'].includes(payload.contract)
    ? structuredClone(payload.assets ?? [])
    : null;
  const courses = payload.courses.map(course => ({
    courseInstallId: installationId(),
    packageInstallId,
    contract: payload.contract,
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
    ...(packageAssets ? { packageAssets: structuredClone(packageAssets) } : {}),
    installedAt,
  }));
  return {
    package: {
      packageInstallId,
      contract: payload.contract,
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

function validationResultFromError(error, contractVersion = null) {
  return {
    ok: false,
    contractVersion,
    errors: [{
      code: error.code ?? 'ERR_IMPORT_REJECTED',
      path: error.code === 'ERR_LEGACY' ? '$.contract' : '$',
      message: error.message,
    }],
  };
}

export function createImportService(storage) {
  return Object.freeze({
    async validatePackage(payload) {
      let parsed;
      try {
        parsed = parsePackagePayload(payload);
        assertSupportedContract(parsed);
      } catch (error) {
        return validationResultFromError(error, parsed?.contract ?? null);
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
          courseInstallId, courseLineageId, courseRevisionId, displayLabel,
        })),
      };
    },
  });
}
