# Learn-it clean-generation roadmap

## Governing rule

RC718 remains the frozen legacy standalone product. The successor is a distinct generation, not an in-place migration.

The roadmap is evidence-gated. Repository state, accepted ADRs and work packages override this document if they differ.

> **Current status (post-Atlas M3.4):** Learning Loop V2, Atlas M1, Atlas M2 memory/reconfirmation, Atlas M2.2 transfer/clarity, M3.0 Authoring Foundation, M3.1 Pedagogical Quality, M3.2 AI Kit Factory, M3.3 Portable Review Handoff and M3.4 Qualified Release Set are promoted. M3.2.5 Factory Reliability remains qualified on a real eight-domain benchmark. The learner runtime remains the exact M2.2 artifact; the separate authoring/factory/release-set capabilities remain outside learner runtime. Human sequence-level graphical review debt is tracked as #272. The C1–C7 sequence below remains historical planning evidence; the active roadmap is the evidence-gated sequence immediately below.

## Active post-M3.4 roadmap — STOP_AND_OBSERVE

### P0 — canonical state alignment

Canonical state alignment is completed through GOV-WP-036: machine-readable governor state, architecture status, project README and roadmap record the promoted M3.4 facts and the post-M3.4 STOP_AND_OBSERVE decision without changing product code.

### M3.0 — Authoring Foundation — **PROMOTED**

The accepted vertical slice is implemented, independently tested, human-reviewed and promoted:

```text
existing canonical kit
→ visual edit
→ live validation
→ preview
→ canonical deterministic export
→ re-import without semantic drift
```

The authoring application remains separate from the learner runtime and reuses the canonical kit contract and Python validation authorities. Its GitHub Pages browser packaging executes the same Python authorities in-browser.

### M3.1 — Pedagogical Quality — **PROMOTED**

A deterministic, read-only pedagogical-quality engine is promoted and available through CLI, CI and the Authoring Studio.

The AI-authoring loop is now:

```text
source material
→ constrained AI authoring skill
→ candidate learnit.kit.v2
→ canonical validation
→ pedagogical-quality report
→ AI/human correction
→ rerun
```

Quality bands are non-numeric and do not claim learning effectiveness. The human gate accepted this AI-authoring orientation.

Human sequence-level review remains weaker than desired because the Studio shows activities and diagnostics too locally. A future graphical overview of objective → practice → correction → validation 1 → validation 2 → transfer is tracked as non-blocking debt #272.

### M3.2 — AI Kit Factory — **PROMOTED**

The owner explicitly rejected a generic Source-to-Draft pipeline as unnecessary complexity for this milestone.

Accepted flow:

```text
source files + learner brief
→ AI author
→ learnit.kit.v2 candidate
→ canonical validators
→ M3.1 pedagogical-quality gate
→ author repair loop
→ independent AI semantic/source review
→ deterministic factory PASS/HOLD
```

The factory does not add a document-ingestion subsystem, intermediate draft contract, OCR layer, model-provider API, backend or learner-runtime AI.

Structural factory eligibility requires M3.1 `STRONG` or `EXCELLENT_BY_PROFILE`. Semantic release additionally requires a separate reviewer context bound to exact source/brief/kit hashes. The deterministic gate validates this evidence contract but does not claim semantic truth by itself.

Implementation is promoted under `ATLAS-WP-014`. The factory remains provider-agnostic and outside the learner runtime.

### M3.2.5 — Factory Reliability — **PROMOTED / QUALIFIED**

The additive reliability layer is promoted under `ATLAS-WP-015`. Real-source qualification covers all eight required domains with distinct source content and self-verifying FactoryRuns.

Final qualification evidence: 8 runs, 6 PASS, 2 justified semantic HOLD, 0 human escalations, all domains covered, `PASS_FACTORY_BENCHMARK_V1`. Source/candidate/review payloads are retained as evidence artifacts rather than a repository corpus.

### M3.3 — Portable Review Handoff — **PROMOTED**

The historical "optional LLM assistance" concept was challenged and redefined. M3.3 now productizes the provider-neutral transport/re-entry boundary around the existing independent semantic reviewer:

```text
candidate + learner brief + admitted exact sources
→ deterministic one-case review ZIP
→ separate reviewer context
→ learnit.atlas.semantic_review.v1
→ fail-closed review re-entry
→ self-verifying FactoryRun PASS/HOLD
```

Promotion evidence: frozen product HEAD `d4fe01f94ce38b2cd4d884930555f2bce971f561`, contradictory QA PASS, fresh separate-context real PASS/HOLD qualification, promotion merge `c102ca81f3b144bea1140860ef633a0d01987d59`.

No provider API, learner-runtime AI, source-ingestion/OCR layer, automatic semantic repair or automatic publication was added.

### M3.4 — Qualified Release Set — **PROMOTED**

The historical "Scale and publishing" candidate was challenged and narrowed before implementation. M3.4 does **not** publish remotely. It provides a bounded deterministic release-set layer:

```text
self-verifying PASS FactoryRuns + exact canonical kits
→ exact byte binding
→ canonical identity/digest validation
→ cross-kit collision checks
→ deterministic release-set manifest
→ deterministic portable ZIP
→ offline fail-closed verification
```

Promotion evidence:
- frozen product HEAD `870d69800dcb07fcfff9f1d232dd143c8eaa6486`;
- fresh contradictory QA R2 HEAD `9c0e20ef176ee03532543d009f22979c95d0d748`;
- QA verdict `PASS_QA_WP_024_R2_EXACT_HEAD_CONTRADICTORY_QA`;
- promotion merge `b8337c785cbec995de5891080776c4c44dd99179`;
- dedicated M3.4 post-merge CI PASS;
- central post-merge routing gap closed separately by CI-WP-013 at `f4bbc91c5d480e2996faa8a592c3c18fd83d8906`.

Scale-100 and Scale-500 remain engineering-only evidence and do not claim semantic qualification of synthetic fixtures. M3.4 adds no remote publisher, signing/authentication, asset/media contract, backend, provider dependency or learner-runtime behavior.

### Post-M3.4 — **STOP_AND_OBSERVE**

Independent architecture and product/learning reviews converged: do not open a new product milestone now.

The operating loop is:

```text
use promoted M3.0-M3.4 capabilities
→ observe real operator / distribution / learner friction
→ decide from evidence
```

The current stack should be exercised on a small number of real end-to-end cases. Measure only the evidence needed to identify the next bottleneck: operator active time/manual transfers/errors/recovery effort; Qualified Release Set PASS → learner-start steps/time; learner start/completion/transfer/reconfirmation friction; and the effort required for a responsible human to explain the pedagogical sequence.

Reopen rules:
- distribution friction dominates → consider minimal append-only distribution;
- human review/context friction dominates → consider read-only #272 pedagogical overview;
- operator orchestration toil/errors dominate → consider minimal local stateless artifact-driven automation;
- a different learner problem dominates → define a gate around that actual learner problem;
- no dominant bottleneck → continue STOP_AND_OBSERVE.

No remote publishing, registry, signing, asset subsystem, provider orchestration, #272 implementation, learner-runtime change, Gate3, Gate4 or M4+ capability is authorized by this decision.

### M4+ — platform evolution

Identity/synchronization, teacher/cohort and network/catalog capabilities remain future gates, not implied commitments.

### Separate tooling candidate

Controlled-time navigator tooling remains separate dev/QA capability and does not alter the normal learner artifact or authorize later product gates.

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

The following remain separate future decisions, not assumed roadmap commitments. Accepted M3.2 design does not authorize any of them:

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
