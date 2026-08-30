# Learn-it clean-generation roadmap

## Governing rule

RC718 remains the frozen legacy standalone product. The successor is a distinct generation, not an in-place migration.

The roadmap is evidence-gated. Repository state, accepted ADRs and work packages override this document if they differ.

> **Current status (post-Atlas M2.2):** Learning Loop V2, Atlas M1, Atlas M2 memory/reconfirmation and Atlas M2.2 transfer + bounded learner-facing clarity are promoted. The exact M2.2 artifact is published through GitHub Pages. The C1–C7 sequence below is retained as historical planning evidence; the active roadmap is the evidence-gated sequence immediately below.

## Active post-M2.2 roadmap

### P0 — canonical state alignment

Align the machine-readable governor state, architecture status, project README and roadmap with the promoted M2.2 facts and the currently enforced main-protection ruleset.

Exit gate: canonical repository sources no longer contradict the promoted M2.2 evidence or branch-protection reality.

### M3.0 — Authoring Foundation

Selected next **design-only** increment under issue #223.

Target vertical slice:

```text
existing canonical kit
→ visual edit
→ live validation
→ preview
→ canonical deterministic export
→ re-import without semantic drift
```

Architecture boundary:

- authoring is a separate local/static application from the learner runtime;
- existing canonical kit contracts and validators are reused where possible;
- no new activity type, contract revision, backend, account, sync or runtime AI is implied;
- document ingestion and LLM-assisted authoring belong to later M3 increments, not M3.0;
- implementation is forbidden until the design freezes exact paths, ownership, QA and rollback.

### M3.1 — Pedagogical diagnostics

After M3.0 is proven, add author-facing diagnostics for objective coverage, activity roles, durations, validation/transfer completeness and actionable errors.

### M3.2 — Source to draft

Later bounded ingestion of PDF/text/Markdown into a traceable author draft. Source provenance is mandatory and no imported suggestion is published automatically.

### M3.3 — Assisted authoring

Optional LLM assistance outside the learner runtime. Suggestions must be reviewed and converted into canonical static content before distribution.

### M3.4 — Scale and publishing

Batch validation, asset handling, collision diagnostics, rollback and 100/500-kit scale evidence before any broader publishing model.

### M4+ — platform evolution

Identity/synchronization, teacher/cohort and network/catalog capabilities remain future gates, not implied commitments.

### Separate tooling candidate

A controlled-time navigator is justified by M2.2 human-test cost and may be authorized as a small dev/QA-only work package. It must not alter the normal learner artifact or block M3.0 design.

## Completed foundation

### L0 — frozen legacy product

- RC718 source and promoted artifact are identified exactly.
- RC719 is `PASS_WITH_RESERVATIONS`.
- Permanent Player CI, repository governance and PR-scope controls exist.
- The first reversible storage seam and controlled Stage D operating model are accepted.

### D0 — strategic direction

- `learnit-identity-v1` taxonomy is accepted.
- `ARC-WP-021` selected trajectory C.
- RC718 compatibility resolver, overlay, dual-read and learner-state migration are cancelled.

## Historical gate

### C1 — clean-generation foundation design (`ARC-WP-022`)

Freeze before implementation:

- new major kit contract;
- canonical package, course, objective, activity, revision and asset identity rules;
- canonical digest and collision rules;
- isolated localStorage and IndexedDB namespaces;
- empty initial-state and legacy-package rejection behavior;
- minimum vertical product slice;
- exact file tree, ownership and source budget;
- golden-kit regeneration plan;
- tests, release provenance and human gate;
- disjoint multi-AI scopes and integration order.

Exit gate: the foundation can be implemented without two agents editing the same file or inventing missing contract semantics.

## Historical first implementation cycle

After C1 is accepted, four AI streams may run in parallel from the same exact baseline.

### C2A — contract and fixtures

Owner scope:

- successor JSON Schema and canonicalization rules;
- valid and invalid fixtures;
- deterministic contract validator;
- contract documentation.

No Player runtime or authoring implementation.

### C2B — storage-isolation test harness

Owner scope:

- negative fixtures preloading RC718 storage;
- tests proving successor boot, use and reset do not mutate RC718 bytes;
- successor namespace contract tests.

No product storage implementation and no contract edits.

### C2C — authoring and golden-kit preparation

Owner scope:

- authoring profile for the frozen successor contract;
- Nombres complexes golden kit;
- Signaux électriques golden kit;
- pedagogical and media validation reports.

No Player runtime edits and no contract changes after freeze.

### C2D — minimal successor shell

Owner scope:

- isolated successor application shell;
- strict contract-version rejection path;
- no RC718 runtime import;
- no learning-session implementation beyond the accepted shell boundary.

No shared contract or golden-kit edits.

### C2I — controlled integration

A separate integrator:

- verifies exact result commits from C2A–C2D;
- rejects overlapping files or contract drift;
- combines only green outputs;
- runs clean-room build, repository governance and provenance checks;
- does not repair failed agent work silently.

Exit gate: one deterministic shell imports and validates both golden kits while RC718 storage remains byte-for-byte unchanged.

## Historical minimal vertical product slice

### C3 — learn one activity end to end

Implement only:

```text
valid successor kit
→ import
→ minimal library
→ launch one activity
→ submit one answer
→ record progress
→ persist in successor namespace
→ close and reopen
```

Required activity family for the first slice is selected by `ARC-WP-022`; it should minimize UI mechanics while exercising content, scoring, progress and persistence.

Exit gate:

- canonical identities survive label edits;
- duplicate labels with distinct identities coexist;
- immutable revision ID/digest conflicts are rejected;
- refresh and browser restart preserve successor state;
- RC718 data is untouched;
- tested artifact equals proposed artifact.

## Historical capability recovery

### C4 — justified learning core

Add capabilities only when required by a current product decision:

- session navigation and resume;
- a small justified set of activity families;
- progress and basic bilan;
- accessibility and responsive behavior;
- import diagnostics and safe reset.

Do not copy RC718 modules solely because they exist.

### C5 — pedagogical completeness

Prove the intended learning loop:

- diagnostic or entry assessment where justified;
- discovery and guided practice;
- independent practice;
- feedback and remediation;
- review and retention rules;
- transfer exercises.

Exit gate: the two golden kits are pedagogically complete and pass human learning review.

## Historical later local capabilities

### C6 — structured transactional storage

Consider only after the minimal product is stable. Introduce structured storage with crash recovery and explicit schema evolution inside the successor namespace.

This is not an RC718 migration.

### C7 — local event and projection model

Introduce immutable learning events only when product use cases justify their cost. Prove deterministic projections and idempotence before any synchronization work.

## Held platform evolution

The following remain separate future decisions, not assumed roadmap commitments. M3.0 does not authorize any of them:

1. synchronization simulator;
2. accounts and learner profiles;
3. modular-monolith backend;
4. remote catalog;
5. institutions;
6. commerce and entitlements;
7. controlled publishing;
8. marketplace decision.

No later item starts because an earlier one is technically possible. Each requires demonstrated user value and an accepted gate.

## Multi-AI rule

Parallel AI work is allowed only when:

- all agents share one exact base commit;
- shared contracts are frozen;
- write scopes are disjoint and machine-checkable;
- each agent produces an exact tested result;
- contradictory QA is independent;
- integration is performed by a separate role;
- no agent merges directly to `main`;
- failed work is not repaired by expanding another agent's scope.

When these conditions are not met, work remains sequential.

## Release discipline

- A commit or pull request is not automatically a release candidate.
- Human candidates use a distinct successor release identity.
- RC718 remains separately retrievable.
- The new-generation rupture is communicated explicitly.
- Tag only artifacts submitted to a meaningful gate.
- Never distribute an artifact different from the artifact tested.
