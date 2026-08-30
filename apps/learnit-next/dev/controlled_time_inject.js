/* LEARNIT_CONTROLLED_TIME_INJECT_V1 */
const __learnitControlledTimeApi = await (async () => {
  'use strict';

  const VERSION = 'learnit.atlas.controlled-time.v1';
  const STATE_SCHEMA = 'learnit.atlas.controlled-time.state.v1';
  const STATE_KEY = 'learnit.dev.controlled-time.navigator.v1.state';
  const PENDING_KEY = 'learnit.dev.controlled-time.navigator.v1.pending';
  const NORMAL_LOCAL_PREFIX = 'learnit.next.v1.';
  const DEV_LOCAL_PREFIX = 'learnit.dev.controlled-time.next.v1.';
  const DATABASE_MAP = Object.freeze({
    learnit_next_v1: 'learnit_dev_controlled_time_next_v1',
    learnit_atlas_m1_v2: 'learnit_dev_controlled_time_atlas_m1_v2',
  });
  const REVERSE_DATABASE_MAP = Object.freeze(Object.fromEntries(
    Object.entries(DATABASE_MAP).map(([normal, isolated]) => [isolated, normal]),
  ));
  const QUICK_DAYS = Object.freeze([0, 1, 3, 7, 21]);
  const DAY_MS = 86_400_000;
  const ISO_RX = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
  const NativeDate = globalThis.Date;
  const nativeIndexedDb = globalThis.indexedDB;
  const nativeLocalStorage = globalThis.localStorage;

  if (!nativeIndexedDb || !nativeLocalStorage) {
    throw new Error('CONTROLLED_TIME_BROWSER_STORAGE_REQUIRED');
  }

  function canonicalIso(value) {
    if (typeof value !== 'string' || !ISO_RX.test(value)) {
      throw new Error('CONTROLLED_TIME_NON_CANONICAL_TIMESTAMP');
    }
    const milliseconds = NativeDate.parse(value);
    if (!Number.isFinite(milliseconds) || new NativeDate(milliseconds).toISOString() !== value) {
      throw new Error('CONTROLLED_TIME_NON_CANONICAL_TIMESTAMP');
    }
    return value;
  }

  function stateValue(originIso, nowIso) {
    return Object.freeze({
      schema: STATE_SCHEMA,
      mode: 'controlled',
      originIso: canonicalIso(originIso),
      nowIso: canonicalIso(nowIso),
    });
  }

  function parseStored(key) {
    const raw = nativeLocalStorage.getItem(key);
    if (raw == null) return null;
    let value;
    try {
      value = JSON.parse(raw);
    } catch {
      throw new Error(`CONTROLLED_TIME_INVALID_STORED_JSON: ${key}`);
    }
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      throw new Error(`CONTROLLED_TIME_INVALID_STORED_VALUE: ${key}`);
    }
    return value;
  }

  function readState() {
    const value = parseStored(STATE_KEY);
    if (value == null) return Object.freeze({mode: 'system'});
    if (value.schema !== STATE_SCHEMA || value.mode !== 'controlled') {
      throw new Error('CONTROLLED_TIME_INVALID_STATE');
    }
    return stateValue(value.originIso, value.nowIso);
  }

  function writeState(value) {
    nativeLocalStorage.setItem(STATE_KEY, JSON.stringify(value));
  }

  function devLocalKeys() {
    const keys = [];
    for (let index = 0; index < nativeLocalStorage.length; index += 1) {
      const key = nativeLocalStorage.key(index);
      if (key && key.startsWith(DEV_LOCAL_PREFIX)) keys.push(key);
    }
    return keys.sort();
  }

  function clearDevLocalStorage() {
    for (const key of devLocalKeys()) nativeLocalStorage.removeItem(key);
  }

  function deleteDatabase(name) {
    return new Promise((resolve, reject) => {
      const request = nativeIndexedDb.deleteDatabase(name);
      request.addEventListener('success', () => resolve(true), {once: true});
      request.addEventListener('error', () => reject(
        request.error || new Error(`CONTROLLED_TIME_DATABASE_DELETE_FAILED: ${name}`),
      ), {once: true});
      request.addEventListener('blocked', () => reject(
        new Error(`CONTROLLED_TIME_DATABASE_DELETE_BLOCKED: ${name}`),
      ), {once: true});
    });
  }

  async function clearDevDatabases() {
    for (const name of Object.values(DATABASE_MAP)) await deleteDatabase(name);
  }

  async function applyPendingReset() {
    const pending = parseStored(PENDING_KEY);
    if (pending == null) return;
    if (pending.schema !== STATE_SCHEMA || !['system', 'controlled'].includes(pending.mode)) {
      throw new Error('CONTROLLED_TIME_INVALID_PENDING_RESET');
    }
    await clearDevDatabases();
    clearDevLocalStorage();
    nativeLocalStorage.removeItem(STATE_KEY);
    if (pending.mode === 'controlled') {
      writeState(stateValue(pending.originIso, pending.nowIso));
    }
    nativeLocalStorage.removeItem(PENDING_KEY);
  }

  await applyPendingReset();
  let currentState = readState();

  function patchDate() {
    const controlledMilliseconds = currentState.mode === 'controlled'
      ? NativeDate.parse(currentState.nowIso)
      : null;

    function CandidateDate(...args) {
      if (!new.target) {
        return new NativeDate(controlledMilliseconds ?? NativeDate.now()).toString();
      }
      const actualArgs = args.length ? args : [controlledMilliseconds ?? NativeDate.now()];
      return Reflect.construct(NativeDate, actualArgs, NativeDate);
    }

    Object.setPrototypeOf(CandidateDate, NativeDate);
    CandidateDate.prototype = NativeDate.prototype;
    Object.defineProperties(CandidateDate, {
      now: {value: () => controlledMilliseconds ?? NativeDate.now()},
      parse: {value: NativeDate.parse.bind(NativeDate)},
      UTC: {value: NativeDate.UTC.bind(NativeDate)},
    });
    Object.defineProperty(globalThis, 'Date', {
      configurable: false,
      enumerable: false,
      writable: false,
      value: CandidateDate,
    });
  }

  function mapDatabaseName(value) {
    const name = String(value);
    const mapped = DATABASE_MAP[name];
    if (!mapped) throw new Error(`CONTROLLED_TIME_DATABASE_FORBIDDEN: ${name}`);
    return mapped;
  }

  function patchIndexedDb() {
    const facade = new Proxy(nativeIndexedDb, {
      get(target, property) {
        if (property === 'open') {
          return (name, version) => (
            version === undefined
              ? target.open(mapDatabaseName(name))
              : target.open(mapDatabaseName(name), version)
          );
        }
        if (property === 'deleteDatabase') {
          return name => target.deleteDatabase(mapDatabaseName(name));
        }
        if (property === 'databases' && typeof target.databases === 'function') {
          return async () => (await target.databases())
            .filter(record => Object.hasOwn(REVERSE_DATABASE_MAP, record.name))
            .map(record => ({...record, name: REVERSE_DATABASE_MAP[record.name]}));
        }
        const value = Reflect.get(target, property, target);
        return typeof value === 'function' ? value.bind(target) : value;
      },
    });
    Object.defineProperty(globalThis, 'indexedDB', {
      configurable: false,
      enumerable: true,
      writable: false,
      value: facade,
    });
  }

  function normalKey(value) {
    const key = String(value);
    if (!key.startsWith(NORMAL_LOCAL_PREFIX)) {
      throw new Error(`CONTROLLED_TIME_LOCAL_STORAGE_KEY_FORBIDDEN: ${key}`);
    }
    return DEV_LOCAL_PREFIX + key.slice(NORMAL_LOCAL_PREFIX.length);
  }

  function virtualLocalKeys() {
    return devLocalKeys().map(key => NORMAL_LOCAL_PREFIX + key.slice(DEV_LOCAL_PREFIX.length));
  }

  function patchLocalStorage() {
    const facade = new Proxy(nativeLocalStorage, {
      get(target, property) {
        if (property === 'length') return virtualLocalKeys().length;
        if (property === 'key') return index => virtualLocalKeys()[Number(index)] ?? null;
        if (property === 'getItem') return key => target.getItem(normalKey(key));
        if (property === 'setItem') return (key, value) => target.setItem(normalKey(key), String(value));
        if (property === 'removeItem') return key => target.removeItem(normalKey(key));
        if (property === 'clear') return () => clearDevLocalStorage();
        const value = Reflect.get(target, property, target);
        return typeof value === 'function' ? value.bind(target) : value;
      },
      set() {
        throw new Error('CONTROLLED_TIME_LOCAL_STORAGE_PROPERTY_WRITE_FORBIDDEN');
      },
    });
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: false,
      enumerable: true,
      writable: false,
      value: facade,
    });
  }

  patchDate();
  patchIndexedDb();
  patchLocalStorage();

  const atlasClock = Object.freeze({
    now() {
      return currentState.mode === 'controlled'
        ? currentState.nowIso
        : new NativeDate().toISOString();
    },
  });
  Object.defineProperty(globalThis, '__LEARNIT_ATLAS_CLOCK__', {
    configurable: false,
    enumerable: false,
    writable: false,
    value: atlasClock,
  });

  function pendingReset(value) {
    nativeLocalStorage.setItem(PENDING_KEY, JSON.stringify(value));
    globalThis.location.reload();
  }

  function activate(value, clearFirst = false) {
    const next = stateValue(value.originIso, value.nowIso);
    if (clearFirst || (
      currentState.mode === 'controlled'
      && NativeDate.parse(next.nowIso) < NativeDate.parse(currentState.nowIso)
    )) {
      pendingReset(next);
      return;
    }
    writeState(next);
    globalThis.location.reload();
  }

  function systemReset() {
    pendingReset({schema: STATE_SCHEMA, mode: 'system'});
  }

  function renderNavigator() {
    const style = document.createElement('style');
    style.id = 'learnit-controlled-time-style';
    style.textContent = `
      :root { --learnit-controlled-time-offset: 0px; }
      body.learnit-controlled-time-active { padding-top: var(--learnit-controlled-time-offset) !important; }
      #learnit-controlled-time-panel {
        position: fixed; inset: 0 0 auto 0; z-index: 2147483647;
        box-sizing: border-box; display: grid; gap: .45rem;
        padding: .55rem .8rem; color: #fff; background: #5b1122;
        border-bottom: 3px solid #ffcf33; font: 600 14px/1.25 system-ui, sans-serif;
        box-shadow: 0 3px 12px rgba(0,0,0,.35);
      }
      #learnit-controlled-time-panel[data-mode="system"] { background: #26364a; }
      #learnit-controlled-time-panel .ct-row { display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; }
      #learnit-controlled-time-panel .ct-title { font-weight: 850; letter-spacing: .025em; }
      #learnit-controlled-time-panel button, #learnit-controlled-time-panel input {
        min-height: 2rem; box-sizing: border-box; border: 1px solid #fff; border-radius: .35rem;
        font: inherit;
      }
      #learnit-controlled-time-panel button { padding: .25rem .6rem; color: #172233; background: #fff; cursor: pointer; }
      #learnit-controlled-time-panel button:focus-visible, #learnit-controlled-time-panel input:focus-visible {
        outline: 3px solid #ffcf33; outline-offset: 2px;
      }
      #learnit-controlled-time-panel input { width: 17rem; max-width: 100%; padding: .25rem .45rem; color: #172233; background: #fff; }
      #learnit-controlled-time-panel [role="status"] { min-height: 1.25em; color: #ffefad; }
      @media (max-width: 620px) {
        #learnit-controlled-time-panel { font-size: 12px; }
        #learnit-controlled-time-panel input { width: min(100%, 17rem); }
      }
    `;
    document.head.append(style);

    const panel = document.createElement('section');
    panel.id = 'learnit-controlled-time-panel';
    panel.dataset.mode = currentState.mode;
    panel.setAttribute('aria-label', 'Navigateur temporel Atlas de test');

    const headline = document.createElement('div');
    headline.className = 'ct-row';
    const title = document.createElement('strong');
    title.className = 'ct-title';
    title.textContent = currentState.mode === 'controlled'
      ? 'TEMPS SIMULÉ — DONNÉES DE TEST'
      : 'NAVIGATEUR QA — TEMPS SYSTÈME — STOCKAGE DE TEST ISOLÉ';
    const clock = document.createElement('span');
    clock.dataset.controlledTimeNow = 'true';
    clock.textContent = currentState.mode === 'controlled'
      ? currentState.nowIso
      : new NativeDate().toISOString();
    headline.append(title, clock);

    const controls = document.createElement('div');
    controls.className = 'ct-row';
    for (const days of QUICK_DAYS) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.controlledTimeDays = String(days);
      button.textContent = days === 0 ? 'J0' : `+${days}j`;
      button.addEventListener('click', () => {
        const originIso = currentState.mode === 'controlled'
          ? currentState.originIso
          : new NativeDate().toISOString();
        const nowIso = new NativeDate(NativeDate.parse(originIso) + days * DAY_MS).toISOString();
        activate({originIso, nowIso});
      });
      controls.append(button);
    }

    const inputLabel = document.createElement('label');
    inputLabel.textContent = 'ISO exact : ';
    const input = document.createElement('input');
    input.dataset.controlledTimeIso = 'true';
    input.inputMode = 'text';
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.placeholder = '2026-08-01T10:00:00.000Z';
    input.value = currentState.mode === 'controlled' ? currentState.nowIso : '';
    inputLabel.append(input);
    controls.append(inputLabel);

    const setButton = document.createElement('button');
    setButton.type = 'button';
    setButton.dataset.controlledTimeSet = 'true';
    setButton.textContent = 'Définir J0';
    controls.append(setButton);

    const systemButton = document.createElement('button');
    systemButton.type = 'button';
    systemButton.dataset.controlledTimeSystem = 'true';
    systemButton.textContent = 'Retour au temps système';
    systemButton.addEventListener('click', systemReset);
    controls.append(systemButton);

    const status = document.createElement('span');
    status.dataset.controlledTimeStatus = 'true';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    setButton.addEventListener('click', () => {
      try {
        const exact = canonicalIso(input.value.trim());
        input.removeAttribute('aria-invalid');
        status.textContent = 'Nouveau scénario en cours de chargement…';
        activate({originIso: exact, nowIso: exact}, true);
      } catch {
        input.setAttribute('aria-invalid', 'true');
        status.textContent = 'Format requis : AAAA-MM-JJThh:mm:ss.sssZ.';
        input.focus();
      }
    });

    panel.append(headline, controls, status);
    document.body.prepend(panel);
    document.body.classList.add('learnit-controlled-time-active');
    document.title = `${currentState.mode === 'controlled' ? '[TEMPS SIMULÉ] ' : '[QA TEMPS] '}${document.title}`;

    const updateOffset = () => {
      document.documentElement.style.setProperty(
        '--learnit-controlled-time-offset',
        `${Math.ceil(panel.getBoundingClientRect().height)}px`,
      );
    };
    updateOffset();
    globalThis.addEventListener('resize', updateOffset);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNavigator, {once: true});
  } else {
    renderNavigator();
  }

  const api = Object.freeze({
    version: VERSION,
    mode: currentState.mode,
    nowIso: currentState.mode === 'controlled' ? currentState.nowIso : null,
    originIso: currentState.mode === 'controlled' ? currentState.originIso : null,
    quickDays: QUICK_DAYS,
    storage: Object.freeze({
      indexedDbNames: Object.freeze(Object.values(DATABASE_MAP)),
      localStoragePrefix: DEV_LOCAL_PREFIX,
    }),
    clock: atlasClock,
    resetToSystemTime: systemReset,
  });
  Object.defineProperty(globalThis, '__LEARNIT_CONTROLLED_TIME__', {
    configurable: false,
    enumerable: false,
    writable: false,
    value: api,
  });
  return api;
})();
