# ARC-WP-010 — First reversible storage seam design

## Decision status

**Accepted design, implementation still blocked behind the separate Stage C work package and governor gate.**

This document defines one deliberately small seam. It does not authorize a storage migration, a data-model change, an identifier change, a UI change or a platform feature.

**Evidence-gate amendment:** ARC-WP-012 adds one QA-owned path, `apps/player/dev/checks_registry.json`, solely to register `tests/contract_storage_boundary.py` in the existing mandatory full Player CI list. It does not broaden developer scope or product behavior.

## Exact design baseline

- Repository: `stefm78/learnit-platform`
- Base commit: `2c7cf873a0bf1fd65f7337cff430df7604fd67f3`
- Promoted product source: `decd9b77bc77a6de9dc28497d0f3affeb972e964`
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`
- Product baseline: RC718, promoted after RC719 `PASS_WITH_RESERVATIONS`

## Current storage cartography

### Browser persistence primitives

| Current owner | Primitive | Responsibility | Stage C treatment |
|---|---|---|---|
| `apps/player/src/scripts/core/runtime_parts/00_runtime_boot_and_content_library.js` | `window.localStorage` | Synchronous `storage` adapter, memory fallback, telemetry and one-shot synthetic fault injection | Move the adapter block byte-for-byte into the new narrow owner; no semantic change |
| `apps/player/src/scripts/core/runtime_parts/05_durable_library_store.js` | `indexedDB` | Durable library snapshot database, store and record; asynchronous read/write/clear/report | Frozen and explicitly outside the first seam |

No other player runtime source is allowed to call `window.localStorage` or `indexedDB` directly after Stage C.

### Existing synchronous adapter contract

The current lexical object is named `storage` and exposes:

- `getItem(key) -> string`: returns the stored string; returns `""` when absent, when the browser backend is unavailable, or when a backend read fails;
- `setItem(key, value)`: coerces key and value to strings; writes to `localStorage` or the in-memory fallback; propagates write errors;
- `removeItem(key)`: removes from the selected backend and propagates removal errors;
- `dump()`: returns all in-memory values or all browser keys prefixed `learnit_`;
- `report()`: returns the existing schema, mode, counters and last failure;
- `injectFaultOnce(spec)`: preserves the current one-shot test fault behavior.

The adapter currently probes `window.localStorage` once during initialization. When the probe fails it uses the existing process-memory fallback. These semantics are frozen.

### Current keys and formats

The following key strings are frozen for the first seam:

| Constant | Stored key | Current payload |
|---|---|---|
| `STORAGE_KEY` | `learnit_clean_state_v2` | JSON learner/application state, schema version 4 |
| `JOURNAL_KEY` | `learnit_clean_journal_v2` | JSON UX journal array |
| `PATCH_KEY` | `learnit_content_patches_v2` | JSON content-patch history |
| `ACTIVE_COURSE_KEY` | `learnit_active_course_v1` | active local course identifier string |
| `FIELD_EVIDENCE_KEY` | `learnit_field_evidence_v1` | field-evidence payload string/JSON |
| `IMPORTED_COURSES_KEY` | `learnit_imported_courses_v1` | JSON imported-course array |
| `IMPORT_HISTORY_KEY` | `learnit_import_history_v1` | JSON bounded import history |
| `IMPORT_LAST_APPLIED_KEY` | `learnit_import_last_applied_v1` | JSON last-applied import report |
| `IMPORT_TRANSACTION_KEY` | `learnit_import_transaction_v1` | JSON prepared import transaction and rollback snapshot |
| `RECOVERY_REPORT_KEY` | `learnit_recovery_report_v1` | JSON state recovery report |
| `RESILIENCE_META_KEY` | `learnit_resilience_meta_v1` | resilience metadata |
| `LIBRARY_REVISION_KEY` | `learnit_library_revision_v1` | numeric revision serialized as string |
| `LIBRARY_PERSISTENCE_META_KEY` | `learnit_library_persistence_meta_v1` | JSON durable-library metadata |

The durable snapshot database remains:

- database: `learnit_durable_library_v1`;
- object store: `snapshots`;
- record id: `library`;
- record shape: unchanged current snapshot containing imported courses, history, active course, learner-state payload, content-patch payload, field-evidence payload, revision and digest.

### Current callers through the adapter

| File | Access category |
|---|---|
| `10_content_store_and_state.js` | journal load/save, active course, imported courses, import history/report/transaction, content patches, learner state, recovery report, durable snapshot composition and restoration |
| `72_performance_scalability_runtime.js` | read-only storage size instrumentation through the adapter |
| `73_runtime_test_api.js` | test-only dump, report, read, write, remove and fault injection through the adapter |
| `70_automation_and_boot.js` | no primitive access; uses `ContentStore`/`AppState` public behavior |
| `60_app_runtime_and_test_api.js` | no primitive access; composes `ContentStore`/`AppState` and durable hydration |

## Accepted seam

### New owner

Create:

`apps/player/src/scripts/core/runtime_parts/04_local_storage_port.js`

It becomes the sole owner of the existing synchronous `storage` adapter and the sole runtime source allowed to reference `window.localStorage`.

### Mechanical implementation

1. Remove only the current `const storage = (() => { ... })();` block from `00_runtime_boot_and_content_library.js`.
2. Add the same block, without behavioral edits, to `04_local_storage_port.js`.
3. Insert the new path in `source_manifest.json` immediately after `00_runtime_boot_and_content_library.js` and before `05_durable_library_store.js`.
4. Update `apps/player/docs/OWNER_MAP.json` so:
   - `00_runtime_boot_and_content_library.js` owns boot, built-in content and storage key declarations;
   - `04_local_storage_port.js` owns the synchronous local storage port, memory fallback, telemetry and fault injection;
   - `05_durable_library_store.js` remains the IndexedDB durable snapshot owner.
5. Add the focused `apps/player/tests/contract_storage_boundary.py` contract test, owned by adversarial QA.
6. Add only `tests/contract_storage_boundary.py` to the existing `mandatory` list in `apps/player/dev/checks_registry.json`; do not alter any existing entry, policy, runner or browser list.
7. Rebuild using the existing deterministic build; allow generated manifest fingerprints to change only as a consequence of the moved source boundary.

The runtime bundle remains one ordered lexical closure. The name `storage`, its API, all callers and all key constants remain unchanged. No dependency injection framework or new abstraction hierarchy is introduced.

## Machine-checkable Stage C scopes

### Developer scope

Allowed implementation paths only:

- `apps/player/src/scripts/core/runtime_parts/00_runtime_boot_and_content_library.js`
- `apps/player/src/scripts/core/runtime_parts/04_local_storage_port.js`
- `apps/player/source_manifest.json`
- `apps/player/docs/OWNER_MAP.json`

Forbidden to the developer:

- all tests and the check registry;
- contracts and authoring assets;
- workflows, governance, architecture and work packages;
- every other runtime source;
- generated `dist`, reports and release directories.

### Adversarial QA scope

Allowed QA paths only:

- `apps/player/tests/contract_storage_boundary.py`
- `apps/player/dev/checks_registry.json`, limited to one added mandatory entry for that focused test

QA must not edit implementation files. Existing tests may be executed but not altered. The registry schema, RC, policy, build command, reports, existing mandatory checks and browser checks are frozen.

### Integrator scope

Read-only on implementation and tests. Its durable output is limited to a later integration/evidence record under `docs/evidence/architecture/first-storage-seam/**`; it must verify diff, contract, provenance, rollback and exact test identities.

### Governor scope

Governance/work-package/review files only. The governor must not repair implementation or tests while certifying them.

## Equivalence test profile

### Static boundary assertions

The new QA test must prove:

1. `window.localStorage` occurs in player runtime only in `04_local_storage_port.js`;
2. `indexedDB` remains owned only by `05_durable_library_store.js`;
3. the complete frozen key set and exact string values are unchanged;
4. `00_runtime_boot_and_content_library.js` no longer defines `const storage`;
5. `04_local_storage_port.js` defines exactly one `const storage` with all six frozen operations;
6. the source manifest orders `00`, `04`, `05`, `10` consecutively;
7. the owner map names the three owners consistently;
8. no new storage technology, backend, HTTP API or migration marker appears;
9. the focused test is registered exactly once as an additional mandatory check while the rest of the registry remains unchanged.

### Existing behavioral protection

The exact seam commit must pass:

- permanent `Player CI / gate`;
- `Remote agent worktree / tested result`;
- full player test profile, including the newly registered focused contract;
- existing library persistence and naming contract test;
- existing browser library persistence and naming test;
- import transaction rollback and storage fault tests already included in the full profile;
- deterministic build and manifest validation.

### Black-box equivalence scenarios

The integrator must confirm the existing suites cover and still pass:

- empty storage boot;
- pre-existing learner state load and save;
- imported library close/reopen persistence;
- active course persistence;
- imported course and collection rename persistence;
- localStorage unavailable with memory fallback;
- write failure propagation and rollback;
- IndexedDB durable hydration and snapshot restoration;
- import transaction interruption recovery;
- storage telemetry and test fault injection.

## Explicit non-goals and forbidden expansion

The first seam must not:

- migrate localStorage to IndexedDB;
- merge the local and durable stores;
- rename a key, database, store or record;
- change any JSON shape, revision rule or identifier;
- add asynchronous semantics to the synchronous port;
- add accounts, backend, synchronization, remote catalog or cloud APIs;
- change UI, copy, navigation, activities, import behavior or learner recommendations;
- move callers behind new repositories or domain services;
- refactor the large `ContentStore` or `AppState` classes;
- alter RC719 reservations or implement inferred product corrections.

Any such need stops the work and requires a new work-package decision.

## Rollback

Rollback is a single revert of the Stage C seam pull request. The revert restores the adapter block to `00_runtime_boot_and_content_library.js`, removes `04_local_storage_port.js`, restores manifest/owner-map fingerprints, removes the focused test and removes its single mandatory registry entry. No user-data migration, key rewrite or remote-system compensation is required.

## Stage B governor decision

The design is **GO_WITH_CONDITIONS**:

- Stage B is accepted only when repository governance and PR-scope checks pass on the exact design head and this design is merged;
- Stage C may then be prepared from the resulting exact `main` commit;
- implementation may use only the accepted mechanical extraction and scopes above;
- Stage D remains blocked until the seam implementation, full Player CI, adversarial QA, integrator review, rollback proof and a separate governor acceptance are merged.
