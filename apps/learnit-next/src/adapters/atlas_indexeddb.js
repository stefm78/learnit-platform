'use strict';

const DATABASE = 'learnit_atlas_m1_v2';
const VERSION = 1;
const STORE_KEY_PATHS = Object.freeze({
  learningEvents: 'eventId',
  scoredExecutions: 'executionId',
  resumeStates: 'sessionRef.sessionId',
  atlasMeta: 'key',
});
const STORES = Object.freeze(Object.keys(STORE_KEY_PATHS));

function indexedDbError(code, detail = '') {
  const error = new Error(detail ? `${code}: ${detail}` : code);
  error.code = code;
  return error;
}

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || indexedDbError('INDEXEDDB_REQUEST_FAILED'));
  });
}

function transactionResult(transaction) {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve(true);
    transaction.onabort = () => reject(transaction.error || indexedDbError('INDEXEDDB_TRANSACTION_ABORTED'));
    transaction.onerror = () => reject(transaction.error || indexedDbError('INDEXEDDB_TRANSACTION_FAILED'));
  });
}

function openAtlasIndexedDb(indexedDBImpl = globalThis.indexedDB) {
  if (!indexedDBImpl) return Promise.reject(indexedDbError('INDEXEDDB_UNAVAILABLE'));
  return new Promise((resolve, reject) => {
    const request = indexedDBImpl.open(DATABASE, VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      for (const store of STORES) {
        if (!database.objectStoreNames.contains(store)) {
          database.createObjectStore(store, { keyPath: STORE_KEY_PATHS[store] });
        }
      }
    };
    request.onerror = () => reject(request.error || indexedDbError('INDEXEDDB_OPEN_FAILED'));
    request.onsuccess = () => resolve(request.result);
  });
}

function metadataRow(atlasMeta) {
  return { key: 'state', value: structuredClone(atlasMeta) };
}

async function readAtlasState(database) {
  const transaction = database.transaction(STORES, 'readonly');
  const done = transactionResult(transaction);
  const eventRequest = transaction.objectStore('learningEvents').getAll();
  const executionRequest = transaction.objectStore('scoredExecutions').getAll();
  const resumeRequest = transaction.objectStore('resumeStates').getAll();
  const metadataRequest = transaction.objectStore('atlasMeta').get('state');
  const [learningEvents, scoredExecutions, resumeStates, metadata] = await Promise.all([
    requestResult(eventRequest),
    requestResult(executionRequest),
    requestResult(resumeRequest),
    requestResult(metadataRequest),
  ]);
  await done;
  return {
    learningEvents: structuredClone(learningEvents || []),
    scoredExecutions: structuredClone(scoredExecutions || []),
    resumeStates: structuredClone(resumeStates || []),
    atlasMeta: metadata && metadata.value
      ? structuredClone(metadata.value)
      : { startOrdinal: 0, startRequests: {}, sessions: {}, assistanceUses: {} },
  };
}

function queueStateReplacement(transaction, state, abortAfterStore = null) {
  const values = {
    learningEvents: state.learningEvents,
    scoredExecutions: state.scoredExecutions,
    resumeStates: state.resumeStates,
    atlasMeta: [metadataRow(state.atlasMeta)],
  };
  for (const storeName of STORES) {
    const store = transaction.objectStore(storeName);
    store.clear();
    for (const value of values[storeName]) store.put(structuredClone(value));
    if (abortAfterStore === storeName) {
      transaction.abort();
      return;
    }
  }
}

async function replaceAtlasState(database, state, options = {}) {
  if (!state || !Array.isArray(state.learningEvents) || !Array.isArray(state.scoredExecutions)
      || !Array.isArray(state.resumeStates) || !state.atlasMeta) throw indexedDbError('INVALID_ATLAS_STATE_WRITE');
  const transaction = database.transaction(STORES, 'readwrite');
  const done = transactionResult(transaction);
  queueStateReplacement(transaction, state, options.abortAfterStore || null);
  await done;
  return true;
}

async function atomicWrite(database, writes) {
  if (!Array.isArray(writes) || !writes.length) throw indexedDbError('EMPTY_ATLAS_WRITE');
  const names = [...new Set(writes.map((write) => write.store))];
  for (const name of names) if (!STORES.includes(name)) throw indexedDbError('UNKNOWN_ATLAS_STORE');
  const transaction = database.transaction(names, 'readwrite');
  const done = transactionResult(transaction);
  for (const write of writes) transaction.objectStore(write.store).put(structuredClone(write.value));
  await done;
  return true;
}

class IndexedDbAtlasStorage {
  constructor(database) {
    this.database = database;
    this.namespace = 'learnit.atlas.m1.v2';
    this.learningEvents = [];
    this.scoredExecutions = [];
    this.resumeStates = [];
    this.atlasMeta = { startOrdinal: 0, startRequests: {}, sessions: {}, assistanceUses: {} };
    this.abortAfterStore = null;
  }

  static async open(indexedDBImpl = globalThis.indexedDB) {
    const storage = new IndexedDbAtlasStorage(await openAtlasIndexedDb(indexedDBImpl));
    await storage.reload();
    return storage;
  }

  snapshot() {
    return structuredClone({
      learningEvents: this.learningEvents,
      scoredExecutions: this.scoredExecutions,
      resumeStates: this.resumeStates,
      atlasMeta: this.atlasMeta,
    });
  }

  async reload() {
    Object.assign(this, await readAtlasState(this.database));
    return this.snapshot();
  }

  injectAbortAfterStore(storeName) {
    if (!STORES.includes(storeName)) throw indexedDbError('UNKNOWN_ATLAS_STORE');
    this.abortAfterStore = storeName;
  }

  async commitState(state) {
    const abortAfterStore = this.abortAfterStore;
    this.abortAfterStore = null;
    await replaceAtlasState(this.database, state, { abortAfterStore });
    Object.assign(this, structuredClone(state));
    return true;
  }

  close() {
    if (this.database && typeof this.database.close === 'function') this.database.close();
  }
}

class IndexedDbAtlasCoreService {
  constructor({ storage, clock, registry }) {
    if (!(storage instanceof IndexedDbAtlasStorage)) throw indexedDbError('INVALID_INDEXEDDB_STORAGE');
    this.storage = storage;
    this.clock = clock;
    this.registry = registry;
  }

  createMemoryService() {
    const { InMemoryAtlasStorage, AtlasCoreService } = require('../ports/atlas_storage.js');
    const memoryStorage = new InMemoryAtlasStorage();
    Object.assign(memoryStorage, this.storage.snapshot());
    return { memoryStorage, service: new AtlasCoreService({ storage: memoryStorage, clock: this.clock, registry: this.registry }) };
  }

  async mutate(method, args) {
    const { memoryStorage, service } = this.createMemoryService();
    const result = service[method](...args);
    await this.storage.commitState(memoryStorage.snapshot());
    return result;
  }

  prepareStartRequest(planDigest) { return this.mutate('prepareStartRequest', [planDigest]); }
  startSession(startRequestId, plan) { return this.mutate('startSession', [startRequestId, plan]); }
  requestAssistance(sessionId, itemPosition, assistanceKind) {
    return this.mutate('requestAssistance', [sessionId, itemPosition, assistanceKind]);
  }
  commitActivitySubmission(sessionId, itemPosition, rawResponse) {
    return this.mutate('commitActivitySubmission', [sessionId, itemPosition, rawResponse]);
  }
  lifecycle(sessionId, kind) { return this.mutate('lifecycle', [sessionId, kind]); }
  importState(payload) { return this.mutate('importState', [payload]); }

  evidence() {
    return this.createMemoryService().service.evidence();
  }

  exportState() {
    return this.createMemoryService().service.exportState();
  }
}

module.exports = Object.freeze({
  DATABASE,
  VERSION,
  STORES,
  STORE_KEY_PATHS,
  openAtlasIndexedDb,
  atomicWrite,
  readAtlasState,
  replaceAtlasState,
  IndexedDbAtlasStorage,
  IndexedDbAtlasCoreService,
});
