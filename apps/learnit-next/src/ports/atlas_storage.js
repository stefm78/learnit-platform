import { assertAtlasClock, createSystemAtlasClock, normalizeAtlasTimestamp } from '../core/atlas_clock.js';
import {
  canonicalAtlasJson,
  cloneFrozenAtlasValue,
  mergeLearningEventJournals,
  normalizeLearningEvent,
} from '../core/atlas_events.js';

export const ATLAS_STORAGE_NAMESPACE = 'learnit.atlas.m1.v1';
export const ATLAS_INDEXED_DB_NAME = 'learnit_atlas_m1_v1';
export const ATLAS_INDEXED_DB_VERSION = 1;
export const ATLAS_EVENT_STORE = 'learningEvents';
export const ATLAS_RESUME_STORE = 'resumeStates';
export const ATLAS_META_STORE = 'atlasMeta';
export const ATLAS_STORES = Object.freeze([
  ATLAS_EVENT_STORE,
  ATLAS_RESUME_STORE,
  ATLAS_META_STORE,
]);
export const ATLAS_ACTIVE_SESSION_META_KEY = 'activeSessionId';
export const ATLAS_RESUME_VERSION = 1;
export const ATLAS_EXPORT_KIND = 'learnit-atlas-local-export';
export const ATLAS_EXPORT_VERSION = 1;

const REQUIRED_METHODS = Object.freeze([
  'appendEvents',
  'listEvents',
  'getEvent',
  'saveResumeState',
  'listResumeStates',
  'getResumeState',
  'loadActiveResumeState',
  'clearResumeState',
  'exportAtlasData',
  'importAtlasData',
  'storageReport',
  'close',
]);

export class AtlasStorageError extends TypeError {
  constructor(message, code = 'INVALID_ATLAS_STORAGE') {
    super(message);
    this.name = 'AtlasStorageError';
    this.code = code;
  }
}

function isPlainRecord(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function nonEmptyString(value, label) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new AtlasStorageError(`${label} must be a non-empty string`);
  }
  return value.trim();
}

function assertExactFields(input, expected, label) {
  const expectedSet = new Set(expected);
  const missing = expected.filter((key) => !Object.hasOwn(input, key));
  const unknown = Object.keys(input).filter((key) => !expectedSet.has(key));
  if (missing.length > 0) {
    throw new AtlasStorageError(`${label} is missing: ${missing.join(', ')}`);
  }
  if (unknown.length > 0) {
    throw new AtlasStorageError(`${label} contains unknown fields: ${unknown.sort().join(', ')}`);
  }
}

export function assertAtlasStoragePort(storage) {
  for (const method of REQUIRED_METHODS) {
    if (typeof storage?.[method] !== 'function') {
      throw new AtlasStorageError(`Atlas storage adapter is missing ${method}()`);
    }
  }
  return storage;
}

export function normalizeAtlasResumeState(input) {
  if (!isPlainRecord(input)) {
    throw new AtlasStorageError('Atlas resume state must be a plain object', 'INVALID_RESUME_STATE');
  }
  assertExactFields(
    input,
    ['resumeVersion', 'sessionId', 'savedAt', 'payload'],
    'Atlas resume state',
  );
  if (input.resumeVersion !== ATLAS_RESUME_VERSION) {
    throw new AtlasStorageError(
      `resumeVersion must be ${ATLAS_RESUME_VERSION}`,
      'UNSUPPORTED_RESUME_VERSION',
    );
  }
  if (!isPlainRecord(input.payload)) {
    throw new AtlasStorageError('resume payload must be a plain object', 'INVALID_RESUME_STATE');
  }
  return cloneFrozenAtlasValue({
    resumeVersion: ATLAS_RESUME_VERSION,
    sessionId: nonEmptyString(input.sessionId, 'resume sessionId'),
    savedAt: normalizeAtlasTimestamp(input.savedAt, 'resume savedAt'),
    payload: input.payload,
  }, 'Atlas resume state');
}

export function mergeAtlasResumeStateSets(existingStates, incomingStates) {
  if (!Array.isArray(existingStates) || !Array.isArray(incomingStates)) {
    throw new AtlasStorageError('resume state sets must be arrays', 'INVALID_RESUME_STATE_SET');
  }
  const bySession = new Map();
  const acceptedIncoming = [];
  const retainedExisting = [];

  for (const raw of existingStates) {
    const state = normalizeAtlasResumeState(raw);
    if (bySession.has(state.sessionId)) {
      throw new AtlasStorageError(
        `duplicate existing resume state for ${state.sessionId}`,
        'RESUME_STATE_CONFLICT',
      );
    }
    bySession.set(state.sessionId, state);
  }

  for (const raw of incomingStates) {
    const incoming = normalizeAtlasResumeState(raw);
    const existing = bySession.get(incoming.sessionId);
    if (!existing) {
      bySession.set(incoming.sessionId, incoming);
      acceptedIncoming.push(incoming.sessionId);
      continue;
    }
    const existingCanonical = canonicalAtlasJson(existing, 'existing resume state');
    const incomingCanonical = canonicalAtlasJson(incoming, 'incoming resume state');
    if (existingCanonical === incomingCanonical) {
      retainedExisting.push(incoming.sessionId);
      continue;
    }
    const order = incoming.savedAt.localeCompare(existing.savedAt);
    if (order > 0) {
      bySession.set(incoming.sessionId, incoming);
      acceptedIncoming.push(incoming.sessionId);
    } else if (order < 0) {
      retainedExisting.push(incoming.sessionId);
    } else {
      throw new AtlasStorageError(
        `resume state ${incoming.sessionId} conflicts at identical savedAt`,
        'RESUME_STATE_CONFLICT',
      );
    }
  }

  const states = [...bySession.values()].sort((left, right) => (
    left.savedAt.localeCompare(right.savedAt) || left.sessionId.localeCompare(right.sessionId)
  ));
  return cloneFrozenAtlasValue({ states, acceptedIncoming, retainedExisting });
}

export function selectAtlasActiveSessionId(localSessionId, importedSessionId, resumeStates) {
  const states = new Map(resumeStates.map((raw) => {
    const state = normalizeAtlasResumeState(raw);
    return [state.sessionId, state];
  }));
  const normalizeOptional = (value, label) => {
    if (value === null) return null;
    const id = nonEmptyString(value, label);
    if (!states.has(id)) {
      throw new AtlasStorageError(`${label} does not reference a resume state`, 'INVALID_ACTIVE_SESSION');
    }
    return id;
  };
  const local = normalizeOptional(localSessionId, 'local activeSessionId');
  const imported = normalizeOptional(importedSessionId, 'imported activeSessionId');
  if (local === null) return imported;
  if (imported === null) return local;
  const localState = states.get(local);
  const importedState = states.get(imported);
  const order = importedState.savedAt.localeCompare(localState.savedAt);
  if (order > 0) return imported;
  if (order < 0) return local;
  return [local, imported].sort()[0];
}

export function normalizeAtlasExportEnvelope(input) {
  if (!isPlainRecord(input)) {
    throw new AtlasStorageError('Atlas export must be a plain object', 'INVALID_ATLAS_EXPORT');
  }
  assertExactFields(
    input,
    ['kind', 'exportVersion', 'exportedAt', 'events', 'resumeStates', 'activeSessionId'],
    'Atlas export',
  );
  if (input.kind !== ATLAS_EXPORT_KIND) {
    throw new AtlasStorageError(`Atlas export kind must be ${ATLAS_EXPORT_KIND}`, 'INVALID_ATLAS_EXPORT');
  }
  if (input.exportVersion !== ATLAS_EXPORT_VERSION) {
    throw new AtlasStorageError(
      `exportVersion must be ${ATLAS_EXPORT_VERSION}`,
      'UNSUPPORTED_ATLAS_EXPORT_VERSION',
    );
  }
  if (!Array.isArray(input.events) || !Array.isArray(input.resumeStates)) {
    throw new AtlasStorageError('Atlas export events and resumeStates must be arrays', 'INVALID_ATLAS_EXPORT');
  }
  const events = mergeLearningEventJournals([], input.events);
  const resumeMerge = mergeAtlasResumeStateSets([], input.resumeStates);
  const activeSessionId = selectAtlasActiveSessionId(
    null,
    input.activeSessionId,
    resumeMerge.states,
  );
  return cloneFrozenAtlasValue({
    kind: ATLAS_EXPORT_KIND,
    exportVersion: ATLAS_EXPORT_VERSION,
    exportedAt: normalizeAtlasTimestamp(input.exportedAt, 'exportedAt'),
    events,
    resumeStates: resumeMerge.states,
    activeSessionId,
  }, 'Atlas export');
}

export function createAtlasExportEnvelope(
  { events, resumeStates, activeSessionId = null },
  { clock = createSystemAtlasClock() } = {},
) {
  assertAtlasClock(clock);
  return normalizeAtlasExportEnvelope({
    kind: ATLAS_EXPORT_KIND,
    exportVersion: ATLAS_EXPORT_VERSION,
    exportedAt: clock.now(),
    events: events.map((event) => normalizeLearningEvent(event)),
    resumeStates: resumeStates.map((state) => normalizeAtlasResumeState(state)),
    activeSessionId,
  });
}
