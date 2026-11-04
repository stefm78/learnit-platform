/**
 * Local-only candidate — V6 Parcours assistance contract.
 * Not wired to the learner until the governing domain, durable IndexedDB CAS
 * adapter and browser integration have independently passed qualification.
 * This module NEVER consumes V5 assistance events and NEVER persists hint text.
 */
const SCHEMA = 'learnit.v6.assistance-journal.v1';
const CONTRACT = 'learnit.kit.v6';
const SHA = /^sha256:[0-9a-f]{64}$/;
const IDENT = /^[A-Za-z0-9_-]{8,120}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export class V6AssistanceError extends Error {
  constructor(code) { super(code); this.name = 'V6AssistanceError'; this.code = code; }
}
function guard(condition, code) { if (!condition) throw new V6AssistanceError(code); }
function exactKeys(value, names) {
  return value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).length === names.length && names.every(k => Object.hasOwn(value, k));
}
function freezeReceipt(e) { return Object.freeze({ requestId:e.requestId, rank:e.rank, acknowledged:e.event === 'ACKNOWLEDGED' }); }
function validateContext(ctx) {
  guard(ctx?.contract === CONTRACT, 'V6_CONTRACT_REQUIRED');
  guard(Array.isArray(ctx.hints) && ctx.hints.length <= 3 && ctx.hints.every(x =>
    typeof x === 'string' && x.trim().length > 0 && x.length <= 2000
  ), 'V6_HINTS_INVALID');
  guard(typeof ctx.sessionId === 'string' && IDENT.test(ctx.sessionId), 'SESSION_ID_INVALID');
  guard(typeof ctx.activityId === 'string' && IDENT.test(ctx.activityId), 'ACTIVITY_ID_INVALID');
  guard(typeof ctx.packageRevisionDigest === 'string' && SHA.test(ctx.packageRevisionDigest), 'PACKAGE_DIGEST_INVALID');
  guard(typeof ctx.activityRevisionDigest === 'string' && SHA.test(ctx.activityRevisionDigest), 'ACTIVITY_DIGEST_INVALID');
  const key = `${SCHEMA}:${ctx.sessionId}:${ctx.activityId}`;
  return { key, bindingPrefix:`${ctx.packageRevisionDigest}:${ctx.activityRevisionDigest}` };
}
function parse(snapshot, binding, maximum) {
  guard(snapshot && Number.isSafeInteger(snapshot.version) && snapshot.version >= 0, 'PORT_SNAPSHOT_INVALID');
  const state = snapshot.state;
  if (state == null) {
    guard(snapshot.version === 0, 'JOURNAL_MISSING_AFTER_COMMIT');
    return { events: [], visible: 0, pending: null };
  }
  guard(exactKeys(state, ['schema', 'binding', 'events']) && state.schema === SCHEMA, 'JOURNAL_SCHEMA_INVALID');
  guard(state.binding === binding, 'SOURCE_BINDING_CHANGED');
  guard(Array.isArray(state.events) && state.events.length <= 6, 'JOURNAL_EVENTS_INVALID');
  const requests = new Map(); let visible = 0; let pending = null;
  for (const e of state.events) {
    guard(exactKeys(e, ['event', 'requestId', 'rank']) && UUID.test(e.requestId) &&
      Number.isInteger(e.rank) && e.rank >= 0 && e.rank < maximum, 'JOURNAL_EVENT_INVALID');
    if (e.event === 'AUTHORIZED') {
      guard(!pending && e.rank === visible && !requests.has(e.requestId), 'JOURNAL_EVENT_ORDER_INVALID');
      requests.set(e.requestId, { ...e }); pending = e;
    } else if (e.event === 'ACKNOWLEDGED') {
      guard(pending && pending.requestId === e.requestId && pending.rank === e.rank,
        'JOURNAL_ACK_ORDER_INVALID');
      requests.set(e.requestId, { ...e }); pending = null; visible += 1;
    } else throw new V6AssistanceError('JOURNAL_EVENT_TYPE_INVALID');
  }
  return { events: state.events, visible, pending, requests };
}
function validatedRequestId(requestId) {
  guard(typeof requestId === 'string' && UUID.test(requestId), 'REQUEST_ID_INVALID');
}
/**
 * @param {Object} port
 *   read(key) -> {version, state|null}; compareAndSwap(key, expectedVersion, state)
 *   -> true only after durable atomic commit, false on real contention.
 * @param {Object} opts authorize(context) -> explicitly true, otherwise deny.
 */
export function createV6AssistanceService(port, { authorize, maxRetries = 12 } = {}) {
  guard(port && typeof port.read === 'function' && typeof port.compareAndSwap === 'function',
    'DURABLE_CAS_PORT_REQUIRED');
  guard(typeof authorize === 'function', 'PARCOURS_AUTHORIZER_REQUIRED');
  guard(Number.isInteger(maxRetries) && maxRetries >= 1 && maxRetries <= 32, 'RETRIES_INVALID');
  async function access(ctx) {
    const scope = validateContext(ctx);
    guard(await authorize(ctx) === true, 'PARCOURS_AUTHORIZATION_DENIED');
    // Cryptographically bind the exact V6 hint strings to the revision source.
    // Changing a hint while keeping an old revision digest must fail closed.
    guard(globalThis.crypto?.subtle && typeof TextEncoder === 'function', 'SHA256_UNAVAILABLE');
    const data = new TextEncoder().encode(JSON.stringify(ctx.hints));
    const raw = new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', data));
    const hintSha = Array.from(raw, b => b.toString(16).padStart(2, '0')).join('');
    return { key:scope.key, binding:`${scope.bindingPrefix}:sha256:${hintSha}` };
  }
  async function requestNext(ctx, requestId) {
    validatedRequestId(requestId);
    const { key, binding } = await access(ctx);
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const snapshot = await port.read(key);
      const current = parse(snapshot, binding, ctx.hints.length);
      const old = current.requests?.get(requestId);
      if (old) return freezeReceipt(old); // duplicate never consumes another hint
      guard(!current.pending, 'HINT_PENDING_ACK');
      guard(current.visible < ctx.hints.length, 'HINTS_EXHAUSTED');
      const event = Object.freeze({ event:'AUTHORIZED', requestId, rank:current.visible });
      const state = { schema:SCHEMA, binding, events:[...current.events,event] };
      if (await port.compareAndSwap(key, snapshot.version, state) === true) return freezeReceipt(event);
    }
    throw new V6AssistanceError('CAS_CONFLICT_EXHAUSTED');
  }
  async function acknowledge(ctx, requestId) {
    validatedRequestId(requestId);
    const { key, binding } = await access(ctx);
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const snapshot = await port.read(key);
      const current = parse(snapshot, binding, ctx.hints.length);
      const existing = current.requests?.get(requestId);
      guard(existing, 'UNKNOWN_REQUEST_ID');
      if (existing.event === 'ACKNOWLEDGED') return freezeReceipt(existing);
      guard(current.pending?.requestId === requestId, 'OUT_OF_ORDER_ACK');
      const event = Object.freeze({ event:'ACKNOWLEDGED', requestId, rank:existing.rank });
      const state = { schema:SCHEMA, binding, events:[...current.events,event] };
      if (await port.compareAndSwap(key, snapshot.version, state) === true) return freezeReceipt(event);
    }
    throw new V6AssistanceError('CAS_CONFLICT_EXHAUSTED');
  }
  async function readAuthorizedView(ctx) {
    const { key, binding } = await access(ctx);
    const current = parse(await port.read(key), binding, ctx.hints.length);
    // The only API that returns actual hint values: AFTER durable acknowledgement.
    return Object.freeze({
      visibleCount:current.visible,
      hints:Object.freeze(ctx.hints.slice(0, current.visible)),
      hasPendingAuthorization:!!current.pending,
      pendingRequestId:current.pending?.requestId ?? null
    });
  }
  return Object.freeze({ requestNext, acknowledge, readAuthorizedView });
}
