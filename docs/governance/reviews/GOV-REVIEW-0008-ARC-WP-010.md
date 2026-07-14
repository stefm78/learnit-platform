# GOV-REVIEW-0008 — ARC-WP-010 first storage seam design

## Decision

**GO_WITH_CONDITIONS**

The proposed Stage B design is accepted as the only permitted design for the first reversible seam. This review does not authorize player implementation by itself.

## Exact reviewed identity

- Design base: `2c7cf873a0bf1fd65f7337cff430df7604fd67f3`
- Promoted RC718 source: `decd9b77bc77a6de9dc28497d0f3affeb972e964`
- Promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`
- Canonical design: `docs/architecture/seams/ARC-WP-010_LOCAL_STORAGE_PORT.md`

## Evidence reviewed

### Current implementation

- Runtime part `00_runtime_boot_and_content_library.js` declares every current synchronous storage key and owns the inline `storage` adapter that directly probes `window.localStorage`, provides the memory fallback, tracks telemetry and supports one-shot test faults.
- Runtime part `05_durable_library_store.js` separately owns direct IndexedDB access for the durable library snapshot.
- `10_content_store_and_state.js` consumes the synchronous adapter for journal, imported content, import transactions, content patches, active course, learner state, recovery and durable snapshot payloads.
- Performance instrumentation and the runtime test API consume the adapter rather than browser storage primitives directly.
- The source manifest currently orders runtime parts `00`, `05`, `10`, permitting a mechanically inserted `04` owner without changing caller order or lexical visibility.

### Proposed boundary

The design extracts only the existing `const storage` block from runtime part `00` into new runtime part `04_local_storage_port.js`. It preserves:

- the lexical object name;
- all six operations and their current failure behavior;
- every key and serialized payload;
- localStorage and memory-fallback selection;
- IndexedDB ownership in runtime part `05`;
- all existing callers;
- bundle order and synchronous semantics.

This is a source-ownership seam, not a migration.

## Adversarial findings

1. A broader “persistence repository” abstraction would touch `ContentStore`, `AppState`, durable hydration and import rollback simultaneously. It is rejected as too broad for the first seam.
2. Moving IndexedDB behind the same port would combine synchronous and asynchronous semantics and alter the blast radius. It is rejected.
3. Renaming keys or introducing typed payload wrappers would make rollback data-sensitive. It is rejected.
4. Leaving the adapter in runtime part `00` while adding a facade would create two owners. It is rejected.
5. Allowing the developer to edit the focused QA test would violate independent certification. The write scopes are therefore disjoint.

## Required Stage C conditions

Before implementation begins:

1. create a separate canonical Stage C work package from the exact post-merge `main` commit;
2. freeze the developer and QA paths exactly as specified by the design;
3. use the Remote Agent Worktree for the implementation branch;
4. run the full Player test profile and permanent Player CI on the exact result commit;
5. obtain adversarial QA review without QA editing implementation files;
6. obtain integrator review of diff, provenance, contract and rollback;
7. record a separate governor decision on the merged evidence.

Any scope expansion is a HOLD and requires a new design decision.

## Still held

- player-wide refactoring;
- key or data-shape changes;
- localStorage-to-IndexedDB migration;
- identity migration;
- backend, account, synchronization, remote catalog, commerce, institution and marketplace work;
- Stage D multi-agent implementation pilot.

## Governor conclusion

Stage B becomes accepted after the exact design pull request passes repository governance and PR-scope checks and is merged. The next gate is the separate Stage C implementation work package. Stage D remains **HOLD**.
