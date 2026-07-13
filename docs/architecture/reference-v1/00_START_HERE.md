# Learn-it Platform Architecture Reference v1 — Start here

Date: 2026-07-13  
Status: **challenged target reference — not a description of the current player**

## Purpose

This reference prepares the evolution of Learn-it from a standalone local player toward a platform that may later support:

- multiple users and learner profiles;
- offline-first operation;
- synchronization between devices;
- remote distribution of free or paid learning kits;
- institutional assignment and licensing;
- controlled author publishing;
- parallel engineering by independent AI agents.

It does not authorize immediate cloud implementation. It defines the boundaries, identities, contracts, invariants, evidence, and gates needed to add those capabilities without a repeated full rewrite.

## Interpretation

Always distinguish three things:

1. **Current implementation** — proven only by the selected source, reconstructed build, tests, and human evidence.
2. **Target constraint** — an architectural direction that future work must respect.
3. **Unproven claim** — a plausible statement without reconstructed evidence.

When current code and target architecture differ:

- do not pretend the target is already implemented;
- record the gap;
- create a bounded migration work package;
- preserve validated standalone behavior until the replacement gate passes.

## Current repository phase

The active standalone application is still being stabilized outside this repository. Therefore:

- no player source is present yet;
- no backend module is authorized;
- no synchronization or account work is authorized;
- `ARC-WP-000` remains blocked until a standalone candidate is promoted.

## Central architecture decision

```text
Stable standalone player
        ↓
Local player with explicit domain and repository seams
        ↓
Local event model and deterministic sync simulator
        ↓
Modular-monolith backend
        ↓
Selective service extraction only on demonstrated need
```

## Non-negotiable prohibitions at this stage

- no immediate microservices;
- no synchronization of opaque global snapshots;
- no canonical identifier derived from an editable title;
- no UI-to-storage or UI-to-HTTP direct coupling;
- no parallel AI development without exact baseline and bounded scopes;
- no open marketplace before free catalog, synchronization, entitlements, and first-party commerce are proven;
- no claim of release provenance unless reviewed source, tested artifact, and published artifact are cryptographically linked.

## Reading order

1. `01_ARCHITECTURE_CONSTITUTION.md`
2. `02_TARGET_SYSTEM_ARCHITECTURE.md`
3. `04_DEPENDENCY_AND_CONTRACT_RULES.md`
4. `09_QUALITY_RELEASE_AND_PROVENANCE.md`
5. `10_MULTI_AI_DEVELOPMENT_PROTOCOL.md`
6. `12_ROADMAP_AND_GATES.md`
7. `14_ASSUMPTIONS_CLAIMS_EVIDENCE.md`
8. `../../roadmap/STANDALONE_TO_PLATFORM.md`

## Normative terms

- **MUST** — non-negotiable constraint;
- **SHOULD** — expected rule; deviation requires a documented decision;
- **MAY** — permitted option;
- **HOLD** — intentionally deferred;
- **NO GO** — prohibited at the current maturity stage.

## First executable gate

`ARC-WP-000` imports one selected standalone candidate without refactoring and proves:

- exact source identity;
- clean reconstruction;
- automated and human test evidence;
- artifact identity;
- known limitations;
- rollback.

No architectural transformation begins before that gate is accepted.
