export const NEXT_LOCAL_STORAGE_PREFIX = 'learnit.next.v1.';
export const NEXT_UI_STORAGE_KEY = `${NEXT_LOCAL_STORAGE_PREFIX}ui`;
export const NEXT_INDEXED_DB_NAME = 'learnit_next_v1';
export const NEXT_INDEXED_DB_VERSION = 2;
export const NEXT_OBJECTIVE_PROGRESS_STORE = 'objectiveProgress';
export const NEXT_STORES = Object.freeze([
  'packages',
  'courses',
  'progress',
  'meta',
  NEXT_OBJECTIVE_PROGRESS_STORE,
]);

const REQUIRED_METHODS = [
  'commitImport',
  'getRevisionDigestIndex',
  'listCourses',
  'getCourse',
  'setCourseDisplayLabel',
  'listProgress',
  'getProgress',
  'putProgress',
  'getMeta',
  'setMeta',
  'deleteMeta',
  'resetNextData',
  'storageReport',
];

const OBJECTIVE_PROGRESS_METHODS = [
  'listObjectiveProgress',
  'putObjectiveProgressRecords',
];

export function assertStoragePort(storage) {
  for (const method of REQUIRED_METHODS) {
    if (typeof storage?.[method] !== 'function') {
      throw new TypeError(`Storage adapter is missing ${method}()`);
    }
  }
  return storage;
}

export function assertObjectiveProgressStorage(storage) {
  for (const method of OBJECTIVE_PROGRESS_METHODS) {
    if (typeof storage?.[method] !== 'function') {
      throw new TypeError(`Learning Loop V2 storage adapter is missing ${method}()`);
    }
  }
  return storage;
}
