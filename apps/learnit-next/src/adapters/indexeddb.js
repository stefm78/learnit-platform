import {
  NEXT_INDEXED_DB_NAME,
  NEXT_INDEXED_DB_VERSION,
  NEXT_LOCAL_STORAGE_PREFIX,
  NEXT_STORES,
} from '../ports/storage.js';

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.addEventListener('success', () => resolve(request.result), { once: true });
    request.addEventListener('error', () => reject(request.error ?? new Error('IndexedDB request failed')), { once: true });
  });
}

function transactionDone(transaction) {
  return new Promise((resolve, reject) => {
    transaction.addEventListener('complete', () => resolve(), { once: true });
    transaction.addEventListener('abort', () => reject(transaction.error ?? new Error('IndexedDB transaction aborted')), { once: true });
    transaction.addEventListener('error', () => reject(transaction.error ?? new Error('IndexedDB transaction failed')), { once: true });
  });
}

function deleteDatabase(indexedDbApi, name) {
  return new Promise((resolve, reject) => {
    const request = indexedDbApi.deleteDatabase(name);
    request.addEventListener('success', () => resolve(), { once: true });
    request.addEventListener('error', () => reject(request.error ?? new Error('IndexedDB delete failed')), { once: true });
    request.addEventListener('blocked', () => reject(new Error('IndexedDB delete is blocked by another open page')), { once: true });
  });
}

function openDatabase(indexedDbApi) {
  return new Promise((resolve, reject) => {
    const request = indexedDbApi.open(NEXT_INDEXED_DB_NAME, NEXT_INDEXED_DB_VERSION);
    request.addEventListener('upgradeneeded', () => {
      const database = request.result;
      if (!database.objectStoreNames.contains('packages')) {
        database.createObjectStore('packages', { keyPath: 'packageInstallId' });
      }
      if (!database.objectStoreNames.contains('courses')) {
        const courses = database.createObjectStore('courses', { keyPath: 'courseInstallId' });
        courses.createIndex('packageInstallId', 'packageInstallId', { unique: false });
      }
      if (!database.objectStoreNames.contains('progress')) {
        const progress = database.createObjectStore('progress', {
          keyPath: ['courseInstallId', 'activityRevisionId'],
        });
        progress.createIndex('courseInstallId', 'courseInstallId', { unique: false });
      }
      if (!database.objectStoreNames.contains('meta')) {
        database.createObjectStore('meta', { keyPath: 'key' });
      }
    });
    request.addEventListener('success', () => {
      const database = request.result;
      database.addEventListener('versionchange', () => database.close());
      resolve(database);
    }, { once: true });
    request.addEventListener('error', () => reject(request.error ?? new Error('IndexedDB open failed')), { once: true });
    request.addEventListener('blocked', () => reject(new Error('IndexedDB open is blocked by another page')), { once: true });
  });
}

function addRevision(index, revisionId, digest) {
  const previous = index.get(revisionId);
  if (previous && previous !== digest) {
    throw new Error(`Stored revision ${revisionId} has conflicting digests`);
  }
  index.set(revisionId, digest);
}

export function createIndexedDbStorage({
  indexedDbApi = globalThis.indexedDB,
  localStorageApi = globalThis.localStorage,
} = {}) {
  if (!indexedDbApi) throw new Error('IndexedDB is unavailable');
  let databasePromise = null;

  const database = async () => {
    if (!databasePromise) databasePromise = openDatabase(indexedDbApi);
    return databasePromise;
  };

  return {
    async commitImport(plan) {
      const db = await database();
      const transaction = db.transaction(['packages', 'courses', 'meta'], 'readwrite');
      const requests = [requestResult(transaction.objectStore('packages').add(plan.package))];
      for (const course of plan.courses) {
        requests.push(requestResult(transaction.objectStore('courses').add(course)));
      }
      for (const meta of plan.meta) {
        requests.push(requestResult(transaction.objectStore('meta').put(meta)));
      }
      await Promise.all([...requests, transactionDone(transaction)]);
    },

    async getRevisionDigestIndex() {
      const db = await database();
      const transaction = db.transaction('packages', 'readonly');
      const packages = await requestResult(transaction.objectStore('packages').getAll());
      await transactionDone(transaction);
      const index = new Map();
      for (const record of packages) {
        const payload = record.payload;
        addRevision(index, payload.packageRevisionId, payload.packageRevisionDigest);
        for (const course of payload.courses) {
          addRevision(index, course.courseRevisionId, course.courseRevisionDigest);
          for (const activity of course.activities) {
            addRevision(index, activity.activityRevisionId, activity.activityRevisionDigest);
          }
        }
      }
      return index;
    },

    async listCourses() {
      const db = await database();
      const transaction = db.transaction('courses', 'readonly');
      const records = await requestResult(transaction.objectStore('courses').getAll());
      await transactionDone(transaction);
      return records.sort((left, right) => left.installedAt.localeCompare(right.installedAt) || left.courseInstallId.localeCompare(right.courseInstallId));
    },

    async getCourse(courseInstallId) {
      const db = await database();
      const transaction = db.transaction('courses', 'readonly');
      const record = await requestResult(transaction.objectStore('courses').get(courseInstallId));
      await transactionDone(transaction);
      return record ?? null;
    },

    async setCourseDisplayLabel(courseInstallId, displayLabel) {
      const db = await database();
      const transaction = db.transaction('courses', 'readwrite');
      const store = transaction.objectStore('courses');
      const record = await requestResult(store.get(courseInstallId));
      if (!record) {
        transaction.abort();
        throw new Error(`Unknown courseInstallId ${courseInstallId}`);
      }
      record.displayLabel = displayLabel;
      await Promise.all([requestResult(store.put(record)), transactionDone(transaction)]);
    },

    async listProgress(courseInstallId) {
      const db = await database();
      const transaction = db.transaction('progress', 'readonly');
      const records = await requestResult(transaction.objectStore('progress').index('courseInstallId').getAll(courseInstallId));
      await transactionDone(transaction);
      return records.sort((left, right) => left.updatedAt.localeCompare(right.updatedAt));
    },

    async getProgress(courseInstallId, activityRevisionId) {
      const db = await database();
      const transaction = db.transaction('progress', 'readonly');
      const record = await requestResult(transaction.objectStore('progress').get([courseInstallId, activityRevisionId]));
      await transactionDone(transaction);
      return record ?? null;
    },

    async putProgress(record) {
      const db = await database();
      const transaction = db.transaction('progress', 'readwrite');
      await Promise.all([requestResult(transaction.objectStore('progress').put(record)), transactionDone(transaction)]);
    },

    async getMeta(key) {
      const db = await database();
      const transaction = db.transaction('meta', 'readonly');
      const record = await requestResult(transaction.objectStore('meta').get(key));
      await transactionDone(transaction);
      return record?.value ?? null;
    },

    async setMeta(key, value) {
      const db = await database();
      const transaction = db.transaction('meta', 'readwrite');
      await Promise.all([requestResult(transaction.objectStore('meta').put({ key, value })), transactionDone(transaction)]);
    },

    async deleteMeta(key) {
      const db = await database();
      const transaction = db.transaction('meta', 'readwrite');
      await Promise.all([requestResult(transaction.objectStore('meta').delete(key)), transactionDone(transaction)]);
    },

    async resetNextData() {
      if (databasePromise) {
        const db = await databasePromise;
        db.close();
        databasePromise = null;
      }
      await deleteDatabase(indexedDbApi, NEXT_INDEXED_DB_NAME);
      if (localStorageApi) {
        const keys = [];
        for (let index = 0; index < localStorageApi.length; index += 1) {
          const key = localStorageApi.key(index);
          if (key?.startsWith(NEXT_LOCAL_STORAGE_PREFIX)) keys.push(key);
        }
        keys.forEach((key) => localStorageApi.removeItem(key));
      }
    },

    async storageReport() {
      const db = await database();
      const counts = {};
      const transaction = db.transaction(NEXT_STORES, 'readonly');
      const countRequests = NEXT_STORES.map(async (storeName) => {
        counts[storeName] = await requestResult(transaction.objectStore(storeName).count());
      });
      await Promise.all([...countRequests, transactionDone(transaction)]);
      const localStorageKeys = [];
      if (localStorageApi) {
        for (let index = 0; index < localStorageApi.length; index += 1) {
          const key = localStorageApi.key(index);
          if (key?.startsWith(NEXT_LOCAL_STORAGE_PREFIX)) localStorageKeys.push(key);
        }
      }
      return {
        localStoragePrefix: NEXT_LOCAL_STORAGE_PREFIX,
        localStorageKeys: localStorageKeys.sort(),
        indexedDbName: NEXT_INDEXED_DB_NAME,
        indexedDbVersion: NEXT_INDEXED_DB_VERSION,
        stores: [...NEXT_STORES],
        counts,
      };
    },
  };
}
