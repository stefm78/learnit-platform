import { createSystemAtlasClock } from '../core/atlas_clock.js';
import {
  canonicalAtlasJson,
  cloneFrozenAtlasValue,
  mergeLearningEventJournals,
  normalizeLearningEvent,
} from '../core/atlas_events.js';
import {
  ATLAS_ACTIVE_SESSION_META_KEY,
  ATLAS_EVENT_STORE,
  ATLAS_INDEXED_DB_NAME,
  ATLAS_INDEXED_DB_VERSION,
  ATLAS_META_STORE,
  ATLAS_RESUME_STORE,
  ATLAS_STORAGE_NAMESPACE,
  ATLAS_STORES,
  AtlasStorageError,
  createAtlasExportEnvelope,
  mergeAtlasResumeStateSets,
  normalizeAtlasExportEnvelope,
  normalizeAtlasResumeState,
  selectAtlasActiveSessionId,
} from '../ports/atlas_storage.js';

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.addEventListener('success', () => resolve(request.result), { once: true });
    request.addEventListener(
      'error',
      () => reject(request.error ?? new Error('Atlas IndexedDB request failed')),
      { once: true },
    );
  });
}

function transactionDone(transaction) {
  return new Promise((resolve, reject) => {
    transaction.addEventListener('complete', () => resolve(), { once: true });
    transaction.addEventListener(
      'abort',
      () => reject(transaction.error ?? new Error('Atlas IndexedDB transaction aborted')),
      { once: true },
    );
    transaction.addEventListener(
      'error',
      () => reject(transaction.error ?? new Error('Atlas IndexedDB transaction failed')),
      { once: true },
    );
  });
}

function openDatabase(indexedDbApi) {
  return new Promise((resolve, reject) => {
    const request = indexedDbApi.open(ATLAS_INDEXED_DB_NAME, ATLAS_INDEXED_DB_VERSION);
    request.addEventListener('upgradeneeded', () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(ATLAS_EVENT_STORE)) {
        database.createObjectStore(ATLAS_EVENT_STORE, { keyPath: 'eventId' });
      }
      if (!database.objectStoreNames.contains(ATLAS_RESUME_STORE)) {
        database.createObjectStore(ATLAS_RESUME_STORE, { keyPath: 'sessionId' });
      }
      if (!database.objectStoreNames.contains(ATLAS_META_STORE)) {
        database.createObjectStore(ATLAS_META_STORE, { keyPath: 'key' });
      }
    });
    request.addEventListener('success', () => {
      const database = request.result;
      database.addEventListener('versionchange', () => database.close());
      resolve(database);
    }, { once: true });
    request.addEventListener(
      'error',
      () => reject(request.error ?? new Error('Atlas IndexedDB open failed')),
      { once: true },
    );
    request.addEventListener(
      'blocked',
      () => reject(new Error('Atlas IndexedDB open is blocked by another page')),
      { once: true },
    );
  });
}

function abortAndRethrow(transaction, completion, error) {
  try {
    transaction.abort();
  } catch {
    // IndexedDB may already have aborted the transaction after a request failure.
  }
  return completion.catch(() => undefined).then(() => { throw error; });
}

function sortResumeStates(states) {
  return states.sort((left, right) => (
    left.savedAt.localeCompare(right.savedAt) || left.sessionId.localeCompare(right.sessionId)
  ));
}

export function createIndexedDbAtlasStorage({
  indexedDbApi = globalThis.indexedDB,
  clock = createSystemAtlasClock(),
} = {}) {
  if (!indexedDbApi) throw new AtlasStorageError('IndexedDB is unavailable', 'ATLAS_INDEXEDDB_UNAVAILABLE');
  let databasePromise = null;

  const database = async () => {
    if (!databasePromise) databasePromise = openDatabase(indexedDbApi);
    return databasePromise;
  };

  return Object.freeze({
    async appendEvents(events) {
      if (!Array.isArray(events)) {
        throw new AtlasStorageError('appendEvents expects an array', 'INVALID_EVENT_JOURNAL');
      }
      const incoming = mergeLearningEventJournals([], events);
      const db = await database();
      const transaction = db.transaction(ATLAS_EVENT_STORE, 'readwrite');
      const completion = transactionDone(transaction);
      const store = transaction.objectStore(ATLAS_EVENT_STORE);
      try {
        const existing = await requestResult(store.getAll());
        const merged = mergeLearningEventJournals(existing, incoming);
        const existingIds = new Set(existing.map((event) => event.eventId));
        const additions = incoming.filter((event) => !existingIds.has(event.eventId));
        await Promise.all(additions.map((event) => requestResult(store.add(event))));
        await completion;
        return cloneFrozenAtlasValue({
          added: additions.length,
          existing: incoming.length - additions.length,
          total: merged.length,
        });
      } catch (error) {
        return abortAndRethrow(transaction, completion, error);
      }
    },

    async listEvents() {
      const db = await database();
      const transaction = db.transaction(ATLAS_EVENT_STORE, 'readonly');
      const completion = transactionDone(transaction);
      const events = await requestResult(transaction.objectStore(ATLAS_EVENT_STORE).getAll());
      await completion;
      return mergeLearningEventJournals([], events);
    },

    async getEvent(eventId) {
      if (typeof eventId !== 'string' || eventId.trim() === '') {
        throw new AtlasStorageError('eventId must be a non-empty string');
      }
      const db = await database();
      const transaction = db.transaction(ATLAS_EVENT_STORE, 'readonly');
      const completion = transactionDone(transaction);
      const event = await requestResult(transaction.objectStore(ATLAS_EVENT_STORE).get(eventId.trim()));
      await completion;
      return event === undefined ? null : normalizeLearningEvent(event);
    },

    async saveResumeState(resumeState) {
      const normalized = normalizeAtlasResumeState(resumeState);
      const db = await database();
      const transaction = db.transaction([ATLAS_RESUME_STORE, ATLAS_META_STORE], 'readwrite');
      const completion = transactionDone(transaction);
      try {
        await Promise.all([
          requestResult(transaction.objectStore(ATLAS_RESUME_STORE).put(normalized)),
          requestResult(transaction.objectStore(ATLAS_META_STORE).put({
            key: ATLAS_ACTIVE_SESSION_META_KEY,
            value: normalized.sessionId,
          })),
        ]);
        await completion;
        return normalized;
      } catch (error) {
        return abortAndRethrow(transaction, completion, error);
      }
    },

    async listResumeStates() {
      const db = await database();
      const transaction = db.transaction(ATLAS_RESUME_STORE, 'readonly');
      const completion = transactionDone(transaction);
      const states = await requestResult(transaction.objectStore(ATLAS_RESUME_STORE).getAll());
      await completion;
      return cloneFrozenAtlasValue(sortResumeStates(states.map(normalizeAtlasResumeState)));
    },

    async getResumeState(sessionId) {
      if (typeof sessionId !== 'string' || sessionId.trim() === '') {
        throw new AtlasStorageError('sessionId must be a non-empty string');
      }
      const db = await database();
      const transaction = db.transaction(ATLAS_RESUME_STORE, 'readonly');
      const completion = transactionDone(transaction);
      const state = await requestResult(transaction.objectStore(ATLAS_RESUME_STORE).get(sessionId.trim()));
      await completion;
      return state === undefined ? null : normalizeAtlasResumeState(state);
    },

    async loadActiveResumeState() {
      const db = await database();
      const transaction = db.transaction([ATLAS_RESUME_STORE, ATLAS_META_STORE], 'readonly');
      const completion = transactionDone(transaction);
      const meta = await requestResult(
        transaction.objectStore(ATLAS_META_STORE).get(ATLAS_ACTIVE_SESSION_META_KEY),
      );
      if (meta === undefined) {
        await completion;
        return null;
      }
      const state = await requestResult(transaction.objectStore(ATLAS_RESUME_STORE).get(meta.value));
      await completion;
      if (state === undefined) {
        throw new AtlasStorageError(
          `active session ${String(meta.value)} has no resume state`,
          'BROKEN_ACTIVE_RESUME_REFERENCE',
        );
      }
      return normalizeAtlasResumeState(state);
    },

    async clearResumeState(sessionId) {
      if (typeof sessionId !== 'string' || sessionId.trim() === '') {
        throw new AtlasStorageError('sessionId must be a non-empty string');
      }
      const normalizedSessionId = sessionId.trim();
      const db = await database();
      const transaction = db.transaction([ATLAS_RESUME_STORE, ATLAS_META_STORE], 'readwrite');
      const completion = transactionDone(transaction);
      try {
        const metaStore = transaction.objectStore(ATLAS_META_STORE);
        const active = await requestResult(metaStore.get(ATLAS_ACTIVE_SESSION_META_KEY));
        const requests = [
          requestResult(transaction.objectStore(ATLAS_RESUME_STORE).delete(normalizedSessionId)),
        ];
        if (active?.value === normalizedSessionId) {
          requests.push(requestResult(metaStore.delete(ATLAS_ACTIVE_SESSION_META_KEY)));
        }
        await Promise.all(requests);
        await completion;
      } catch (error) {
        return abortAndRethrow(transaction, completion, error);
      }
    },

    async exportAtlasData() {
      const db = await database();
      const transaction = db.transaction(ATLAS_STORES, 'readonly');
      const completion = transactionDone(transaction);
      const [events, resumeStates, active] = await Promise.all([
        requestResult(transaction.objectStore(ATLAS_EVENT_STORE).getAll()),
        requestResult(transaction.objectStore(ATLAS_RESUME_STORE).getAll()),
        requestResult(transaction.objectStore(ATLAS_META_STORE).get(ATLAS_ACTIVE_SESSION_META_KEY)),
      ]);
      await completion;
      return createAtlasExportEnvelope({
        events,
        resumeStates,
        activeSessionId: active?.value ?? null,
      }, { clock });
    },

    async importAtlasData(rawExport) {
      const imported = normalizeAtlasExportEnvelope(rawExport);
      const db = await database();
      const transaction = db.transaction(ATLAS_STORES, 'readwrite');
      const completion = transactionDone(transaction);
      const eventStore = transaction.objectStore(ATLAS_EVENT_STORE);
      const resumeStore = transaction.objectStore(ATLAS_RESUME_STORE);
      const metaStore = transaction.objectStore(ATLAS_META_STORE);
      try {
        const [existingEvents, existingResumeStates, active] = await Promise.all([
          requestResult(eventStore.getAll()),
          requestResult(resumeStore.getAll()),
          requestResult(metaStore.get(ATLAS_ACTIVE_SESSION_META_KEY)),
        ]);
        const mergedEvents = mergeLearningEventJournals(existingEvents, imported.events);
        const mergedResumes = mergeAtlasResumeStateSets(existingResumeStates, imported.resumeStates);
        const activeSessionId = selectAtlasActiveSessionId(
          active?.value ?? null,
          imported.activeSessionId,
          mergedResumes.states,
        );

        const existingEventIds = new Set(existingEvents.map((event) => event.eventId));
        const addedEvents = imported.events.filter((event) => !existingEventIds.has(event.eventId));
        const existingResumeBySession = new Map(
          existingResumeStates.map((state) => [state.sessionId, canonicalAtlasJson(state)]),
        );
        const resumeWrites = mergedResumes.states.filter((state) => (
          existingResumeBySession.get(state.sessionId) !== canonicalAtlasJson(state)
        ));
        const writes = [
          ...addedEvents.map((event) => requestResult(eventStore.add(event))),
          ...resumeWrites.map((state) => requestResult(resumeStore.put(state))),
        ];
        if (activeSessionId === null) {
          writes.push(requestResult(metaStore.delete(ATLAS_ACTIVE_SESSION_META_KEY)));
        } else {
          writes.push(requestResult(metaStore.put({
            key: ATLAS_ACTIVE_SESSION_META_KEY,
            value: activeSessionId,
          })));
        }
        await Promise.all(writes);
        await completion;
        return cloneFrozenAtlasValue({
          addedEvents: addedEvents.length,
          existingEvents: imported.events.length - addedEvents.length,
          totalEvents: mergedEvents.length,
          writtenResumeStates: resumeWrites.length,
          totalResumeStates: mergedResumes.states.length,
          activeSessionId,
        });
      } catch (error) {
        return abortAndRethrow(transaction, completion, error);
      }
    },

    async storageReport() {
      const db = await database();
      const transaction = db.transaction(ATLAS_STORES, 'readonly');
      const completion = transactionDone(transaction);
      const counts = {};
      await Promise.all(ATLAS_STORES.map(async (storeName) => {
        counts[storeName] = await requestResult(transaction.objectStore(storeName).count());
      }));
      await completion;
      return cloneFrozenAtlasValue({
        namespace: ATLAS_STORAGE_NAMESPACE,
        indexedDbName: ATLAS_INDEXED_DB_NAME,
        indexedDbVersion: ATLAS_INDEXED_DB_VERSION,
        stores: [...ATLAS_STORES],
        counts,
      });
    },

    async close() {
      if (!databasePromise) return;
      const db = await databasePromise;
      db.close();
      databasePromise = null;
    },
  });
}
