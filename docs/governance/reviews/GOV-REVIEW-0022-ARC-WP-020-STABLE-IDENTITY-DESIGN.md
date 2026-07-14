# GOV-REVIEW-0022 — ARC-WP-020 stable identity and migration design

## Decision

**GO_WITH_CONDITIONS** for `ARC-WP-020` as a design-only architecture gate.

Implementation, contract publication, identity-overlay writes and learner-state migration remain **HOLD**.

## Reviewed baseline

- Repository: `stefm78/learnit-platform`
- Exact baseline: `e9d3f1f36d34170111b6b583bc7d9219e68e03ab`
- Product baseline: RC718
- Human gate: RC719 `PASS_WITH_RESERVATIONS`
- Player working-file count: 150
- Pull-request scope is bound only to `ARC-WP-020`; later work-package references describe future gates and do not authorize concurrent implementation.

## Evidence reviewed

1. `apps/player/docs/ENGINEERING.md` records the current distinction between immutable local `localCourseId`, current technical `importPackageId` and editable `importCollectionTitle`.
2. `apps/player/src/learning/course_collection_model.js` contains a title-derived fallback course identifier and collection grouping by `importPackageId`.
3. `apps/player/src/scripts/core/runtime_parts/10_content_store_and_state.js` owns imported identity allocation and state maps keyed by current course and activity compatibility keys.
4. `apps/player/src/learning/mastery_evidence_model.js` groups objectives by normalized text and may generate positional chapter IDs.
5. `apps/player/contract/learnit-import.schema.json` defines current activity and asset references but no globally stable package-version, course, objective or activity-revision lineage.
6. `apps/player/data/golden-kits/golden_nombres_complexes.json` confirms representative use of human-authored package/content version strings, course-scoped activity IDs and package-local asset IDs.
7. `docs/evidence/architecture/stable-identity/current-identity-inventory.json` binds those observations to the exact baseline and separates claims, assumptions and absence of evidence.
8. `docs/architecture/decisions/ADR-0001-STABLE-IDENTITY-MIGRATION.md` defines the target identity layers, compatibility window, collision policy, evidence applicability and migration phases.

## Findings

### Evidence

- RC718 already preserves progress, bilan and resume state when imported course and plan labels are renamed.
- Current learner state is densely keyed by legacy course and activity identifiers.
- Current identifiers are sufficient for the accepted standalone product behavior.
- The repository contains no proof that current package, course, objective, activity or version keys are globally unique or immutable across devices and publishers.

### Claims accepted

- Canonical lineage identity must be separated from local installation identity and legacy compatibility keys.
- Canonical identifiers must be opaque, immutable and independent of editable labels and local collision handling.
- Legacy v1.1 fields must retain their current semantics.
- Canonical identity must be complete and digest-consistent for a published package version; partial identity must be rejected rather than inferred.
- Historical learner evidence must be retained across revisions, but current mastery applicability requires an explicit compatibility decision.
- Migration must be overlay-first, transactional, mixed-version tolerant and reversible.

### Assumptions retained

- Future authoring can allocate collision-resistant opaque IDs offline.
- A future additive contract can carry complete identity envelopes while current display labels remain editable.
- Authored or governed compatibility decisions can classify evidence across revisions.

These assumptions are not implementation evidence.

### Absence of evidence

- No executable resolver for `learnit-identity-v1` exists.
- No canonical identity envelope is implemented or published.
- No state overlay or transactional learner-state migration exists.
- No mixed legacy/canonical runtime fixture exists.
- No synchronization evidence exists.

The design does not convert these absences into implementation confidence.

## Architecture assessment

The three-layer model is accepted:

1. canonical lineage and immutable revision identity;
2. local plan/course installation identity;
3. existing legacy compatibility keys.

The design avoids the two highest-risk errors:

- deriving global identity from editable titles, slugs, positions or local collision suffixes;
- rewriting current state keys before a compatibility resolver and complete mapping are independently proven.

The proposed scheme names are accepted as design vocabulary, not as deployed contract:

- canonical: `pkg_`, `pkv_`, `crs_`, `crv_`, `obj_`, `act_`, `arv_`, `ast_`;
- local: `col_`, `cin_`, `mig_`.

UUIDv7 is accepted as an allocation mechanism. Its embedded timestamp is not accepted as semantic event or publication time.

## Adversarial review

The design explicitly rejects:

- canonical IDs derived from titles, filenames, ordering, normalized labels or collision suffixes;
- reuse of immutable revision IDs with different canonical digests;
- partial canonical identity envelopes;
- implicit merging of legacy imports by matching label or digest;
- implicit merging of separate local installations of the same canonical course;
- automatic application of historical evidence to incompatible activity revisions;
- coupling identity migration to IndexedDB migration, backend or synchronization;
- Player file growth beyond the current budget without an explicit budget action.

Rollback is credible because `ARC-WP-020` changes only design, evidence and governance records.

## Conditions

1. `learnit.import.v1.1` remains unchanged and its existing fields are not silently reinterpreted.
2. No canonical ID, overlay or migrated state may be written under this work package.
3. No Player source, test, contract, data, manifest, release or artifact file may change in this design pull request.
4. The first implementation gate must be `ARC-WP-021` and must be limited to an additive read-only resolver and shadow diagnostic.
5. `ARC-WP-021` must modify exact existing Player files or remove/consolidate one so the working-file count remains at or below 150.
6. The resolver must preserve all current import, rename, session, progress, bilan, retention, persistence, export and rollback behavior.
7. Contract publication, overlay writes and learner-state migration each require later separately accepted gates.
8. Backend, accounts, synchronization, remote catalog, commerce, tenancy and marketplace remain held.

## Outcome

`ARC-WP-020` is accepted as the canonical design and migration strategy.

The next mandatory gate is `ARC-WP-021`: authorization of one bounded additive read-only identity resolver and shadow diagnostic, with exact baseline, disjoint Stage D role scopes, permanent Player CI and separate governor acceptance.
