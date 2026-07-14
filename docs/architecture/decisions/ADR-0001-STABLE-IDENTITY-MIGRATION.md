# ADR-0001 — Stable canonical identity and reversible migration

- Status: **Accepted with conditions**
- Work package: `ARC-WP-020`
- Decision date: 2026-07-15
- Reviewed baseline: `e9d3f1f36d34170111b6b583bc7d9219e68e03ab`
- Product baseline preserved: **RC718**, RC719 `PASS_WITH_RESERVATIONS`
- Implementation status: **not authorized**

## 1. Decision

Learn-it will separate three identity layers that are currently partially conflated:

1. **Canonical lineage identity** — globally stable identifiers for published semantic entities and their immutable revisions.
2. **Local installation identity** — opaque identifiers for one installed plan or course instance on one local library, including explicit duplicates or forks.
3. **Legacy compatibility keys** — current fields and map keys such as `packageId`, `localCourseId`, course-scoped activity `id`, normalized objective text and `contentVersion`.

The layers must coexist during a compatibility window. Existing fields retain their current meaning and are not silently reinterpreted as canonical identifiers.

The canonical scheme is named `learnit-identity-v1`.

## 2. Why this decision is required

The current standalone Player is behaviorally stable but its identifiers were designed for a local application, not for durable cross-version lineage or future synchronization.

Current source evidence shows that:

- imported course state is keyed by a stable local `localCourseId`, but the initial value is resolved from a title-derived slug and collision suffixes;
- the collection model falls back to a title-derived course ID;
- the import pipeline accepts a source `packageId`, but the installed collection receives a new local `plan-<digest>` value stored as `importPackageId`;
- activity `id` is course-scoped and directly keys session queues, answers, progress and bilan review lists;
- objective evidence is grouped by normalized objective text rather than an explicit objective identity;
- chapter IDs may be generated from position;
- `contentVersion` is recorded in progress and sessions but is not a globally enforced immutable revision identity;
- asset IDs are local references inside content payloads;
- legacy payloads can omit package identity and receive time- or import-derived fallback values.

Those mechanisms are valid compatibility keys for RC718. They are not sufficient evidence that two entities imported on different devices are globally identical, nor that historical learner evidence remains applicable after a semantic content change.

The exact source inventory is recorded in `docs/evidence/architecture/stable-identity/current-identity-inventory.json`.

## 3. Identity taxonomy

### 3.1 Canonical lineage identifiers

Canonical IDs are opaque, immutable, never reused and independent of labels, ordering, file names and local collision handling.

The target textual forms use a type prefix followed by an RFC 9562 UUIDv7 value:

| Entity | Prefix | Meaning |
|---|---:|---|
| Package lineage | `pkg_` | One logical authored package across versions |
| Package version | `pkv_` | One immutable published package payload |
| Course lineage | `crs_` | One logical course across revisions |
| Course revision | `crv_` | One immutable learner-relevant course revision |
| Objective lineage | `obj_` | One pedagogical objective across label edits |
| Activity lineage | `act_` | One logical activity across compatible revisions |
| Activity revision | `arv_` | One immutable learner-relevant activity revision |
| Asset lineage | `ast_` | One referenced media asset lineage |

UUID timestamp bits are an allocation convenience only. They are not event time, publication time or ordering authority.

### 3.2 Local installation identifiers

Local IDs are opaque and never presented as global lineage:

| Entity | Prefix | Meaning |
|---|---:|---|
| Imported plan installation | `col_` | One local collection/plan instance |
| Course installation | `cin_` | One local installed course instance and learner-state namespace |
| Migration transaction | `mig_` | One idempotent local migration attempt |

Two installations may reference the same canonical course lineage while retaining separate progress namespaces. An explicit duplicate/fork therefore creates another `courseInstallId`; it does not invent another canonical `courseId`.

Account, learner profile, organization, device, entitlement and event identities are outside this decision and remain held.

### 3.3 Legacy compatibility keys

The following current values remain compatibility keys until an explicit cutover gate:

- root `packageId` in `learnit.import.v1.1`;
- generated installed `importPackageId` such as `plan-<digest>`;
- `localCourseId`;
- fallback title slug returned by current course ID helpers;
- activity `id`;
- asset `id` and media `assetId`;
- objective label and its normalized key;
- generated `chapter-<n>` IDs;
- `contentVersion`;
- patch `courseId` and activity operation `id`.

A compatibility key may be mapped to canonical identity. It is not itself promoted to canonical identity merely because it is currently stable on one device.

## 4. Contract evolution

### 4.1 No silent reinterpretation

`learnit.import.v1.1` keeps its existing semantics. The current `packageId`, course title, activity `id`, objective strings, asset `id` and `contentVersion` fields are not redefined.

The first compatible contract extension must be additive, provisionally `learnit.import.v1.2`, and must use explicit identity envelopes.

### 4.2 Proposed additive envelope

A canonical package version declares:

```json
{
  "identity": {
    "scheme": "learnit-identity-v1",
    "packageId": "pkg_<uuidv7>",
    "packageVersionId": "pkv_<uuidv7>",
    "canonicalDigest": "sha256:<hex>"
  }
}
```

Each course declares:

```json
{
  "identity": {
    "courseId": "crs_<uuidv7>",
    "courseRevisionId": "crv_<uuidv7>"
  }
}
```

The compatibility form retains the current string objective list and adds an explicit catalog:

```json
{
  "objectiveCatalog": [
    {"objectiveId": "obj_<uuidv7>", "label": "..."}
  ]
}
```

Each activity retains its current course-scoped `id` during the compatibility window and adds:

```json
{
  "identity": {
    "activityId": "act_<uuidv7>",
    "activityRevisionId": "arv_<uuidv7>"
  },
  "objectiveIds": ["obj_<uuidv7>"]
}
```

Each asset retains its current local `id` and adds an `identity.assetId`.

The exact JSON Schema is not created by this design package. It requires a separate contract work package and compatibility tests.

### 4.3 All-or-none canonical declaration

For one published package version, canonical identity is either:

- absent, making the package explicitly **legacy-only**; or
- complete and internally consistent for the package version, every course, every referenced objective, every activity and every asset.

Partial canonical identity is rejected. The runtime must not guess missing canonical IDs from titles, order, file names, content hashes or legacy IDs.

## 5. Revision rules

### 5.1 Stable lineage versus immutable revision

A stable lineage ID answers “which logical entity?”. A revision ID answers “which immutable learner-relevant form?”.

- Label or metadata changes that do not alter learner interpretation may keep the lineage ID and, only under an explicit compatibility rule, the revision ID.
- Any change to question meaning, expected answer, assessment role, learning phase, objective linkage, scoring interpretation or remediation semantics creates a new activity revision.
- A course revision changes when its objective structure, required activity set, sequencing semantics or learner-state interpretation changes.
- A package version is immutable and binds all included revisions and assets.

### 5.2 Digest binding

Every package version and revision that can affect learner evidence is bound to a canonicalized payload digest.

The digest is evidence of immutable bytes or canonical data, not the primary ID.

The following is a hard failure:

- same `packageVersionId`, `courseRevisionId` or `activityRevisionId`;
- different canonical digest.

This is treated as collision, corruption or unauthorized mutation, never as an update.

## 6. Collision and import behavior

| Situation | Required behavior |
|---|---|
| Same canonical package version and same digest | Idempotent no-op or verified reinstall |
| Same package lineage, new package version | Version/update candidate; never silent replacement |
| Same course lineage, compatible new revision | Preserve historical facts; project them only under an explicit compatibility decision |
| Same course lineage, incompatible revision | Retain history but do not count it automatically as current mastery |
| Same immutable revision ID, different digest | Reject |
| Different canonical IDs, identical labels | Coexist |
| Same canonical course imported twice explicitly | Create separate `courseInstallId` namespaces |
| Legacy-only content with identical label or digest | Do not infer global identity |
| Canonical package mixed with incomplete canonical children | Reject |
| Source package ID collides only with local installed plan key | Keep concepts separate; do not overwrite either identity |

The current rename/replace/skip/reject collision policy remains a legacy compatibility behavior until a later import-contract implementation gate specifies its canonical mapping.

## 7. Learner evidence ownership

### 7.1 Target key

Future learner evidence is associated with:

```text
courseInstallId
  + canonical courseId/courseRevisionId
  + canonical activityId/activityRevisionId
  + algorithm or projection version
```

The local installation ID preserves separate local journeys. Canonical IDs permit lineage analysis without merging installations implicitly.

### 7.2 Historical applicability

Historical attempts are never deleted because a revision changes.

They are classified as:

- **current-compatible** — eligible for the current projection under an explicit compatibility rule;
- **historical-only** — visible in history but excluded from current mastery;
- **ambiguous** — quarantined from mastery projection until resolved.

A label match, normalized objective text or activity position is insufficient to establish compatibility.

### 7.3 Current maps requiring migration

A later transactional migration must account for at least:

- `activeCourseId`;
- `sessionByCourseId`;
- `lastBilanByCourseId`;
- `activityProgressByCourseId`;
- `retentionByCourseId`;
- active `session.queue` and `session.answers`;
- `lastBilan.review`;
- import history and last-applied import reports;
- durable library snapshot copies of learner state;
- field evidence and content patch references where they contain course or activity keys.

No map is rewritten under `ARC-WP-020`.

## 8. Legacy migration strategy

### Phase 0 — accepted design

This ADR and exact source inventory are accepted. No runtime or data change occurs.

### Phase 1 — read-only identity resolver

A separately authorized bounded seam may:

- parse a complete canonical identity envelope when present;
- classify content as canonical, legacy-only or invalid-partial;
- expose a shadow diagnostic;
- return current legacy keys for all existing behavior.

It must not write identity overlays, rewrite learner state, change import decisions or alter UI behavior.

### Phase 2 — additive local identity overlay

A later gate may create a separately versioned local overlay that maps:

```text
legacy collection key -> collectionInstallId
legacy localCourseId -> courseInstallId -> canonical lineage when supplied
legacy activity id -> canonical activity lineage/revision when supplied
legacy objective key -> canonical objective when supplied
```

For legacy-only content, generated IDs are explicitly local/provisional. They are not exportable as publisher canonical identity.

### Phase 3 — transactional learner-state migration

A later migration must:

1. create an immutable pre-migration snapshot and digest;
2. write a migration journal with `migrationId`, source schema and target schema;
3. build and validate the complete mapping before changing active state;
4. write the new projection atomically with the identity overlay;
5. verify counts, references and digests;
6. switch read preference only after verification;
7. retain the legacy snapshot through the rollback window.

Interruption at any point must resolve to either the complete old state or complete new state, never a partial mix.

### Phase 4 — dual export and mixed-version operation

During the compatibility window:

- legacy-only imports remain accepted if current product policy still allows them;
- canonical packages carry explicit identity envelopes;
- exports contain canonical identity when known and preserve required legacy keys;
- old readers ignore additive identity fields safely;
- new readers never treat absence of canonical identity as corruption;
- synchronization remains prohibited until its own gate.

### Phase 5 — contract v2 cutover

Only after migration evidence, real mixed-version fixtures, rollback tests and human release gates may a v2 contract make canonical identity primary or remove legacy fields.

## 9. Rollback

The migration architecture is overlay-first.

Before destructive cleanup, rollback consists of:

- disabling preference for the identity overlay;
- reading the preserved legacy keys and state maps;
- retaining canonical diagnostics as non-authoritative evidence;
- removing or ignoring the overlay after verification.

Rollback must not require localStorage-to-IndexedDB migration, backend compensation or remote reconciliation.

Legacy key deletion is a final, separately authorized step after the compatibility window, not part of the initial migration.

## 10. Adversarial requirements

Future implementation and migration tests must include:

1. title rename without identity change;
2. two different canonical courses with the same title;
3. one canonical course installed twice with isolated progress;
4. legacy packages with identical content imported independently;
5. same revision ID with different digest;
6. partial canonical envelope;
7. missing objective reference;
8. activity lineage preserved with compatible revision;
9. activity lineage preserved with incompatible revision;
10. activity ID reused for a different semantic entity;
11. reorder of activities and chapters;
12. changed objective label with stable objective identity;
13. interrupted overlay write;
14. interrupted learner-state rewrite;
15. rollback after verification but before read-preference switch;
16. mixed legacy-only and dual-identity library;
17. import/export round trip without identity loss;
18. no new Player file beyond the budget of 150;
19. no change to the accepted storage seam;
20. no entry into backend, synchronization or other held domains.

## 11. First authorized follow-up gate

The next gate is `ARC-WP-021`.

It may authorize only an additive **read-only identity resolver and shadow diagnostic** on exact current `main`.

It must define:

- exact existing Player files to modify;
- how the 150-file budget remains satisfied;
- canonical/legacy/partial classification behavior;
- deterministic validation and diagnostic output;
- black-box proof that every current course, import, rename, progress, bilan, retention and export behavior remains unchanged;
- disjoint developer, contradictory-QA, integrator and governor scopes;
- one-revert rollback.

`ARC-WP-021` must not authorize state writes, schema migration, contract v2, IndexedDB migration, backend or synchronization.

## 12. Consequences

### Positive

- Editable labels remain safely decoupled from identity.
- Future lineage, revision compatibility and synchronization can be reasoned about explicitly.
- Duplicate installations can remain separate without inventing false global entities.
- Legacy content remains usable during a measured compatibility window.
- Migration can proceed through small reversible seams.

### Costs and risks

- The model introduces more explicit identifiers and mapping evidence.
- Legacy-only packages cannot be globally deduplicated automatically without unsafe inference.
- Revision compatibility requires authored or governed decisions.
- The current Player file-budget ceiling constrains implementation structure.
- Until implementation and migration gates pass, this remains an accepted design rather than current behavior.
