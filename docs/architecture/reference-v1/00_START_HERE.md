# Learn-it Platform Architecture Reference v1 — Start here

Date: 2026-07-13  
Status: **historical challenged target reference — not canonical current status**

## Current authority warning

This reference was written before the standalone Player was imported, before RC718 promotion and before the clean-break decision.

Statements in the reference that say no Player source exists, `ARC-WP-000` is blocked, or an in-place migration sequence is current are historical context only.

For current state, read:

1. `../../../governance/governor-state.json`;
2. `../../handover/STAGE_D_RESTART_CHECKPOINT.md`;
3. `../decisions/ADR-0002-CLEAN-BREAK-GENERATION.md`;
4. `../../../work-packages/ARC-WP-021.json`.

Current facts include:

- RC718 is the frozen promoted legacy standalone generation;
- trajectory C is accepted;
- no RC718 compatibility or learner-state migration is planned;
- the successor begins with a new major contract and isolated storage;
- `ARC-WP-022` is the next mandatory gate;
- backend and other platform domains remain held.

## Purpose retained

This reference still provides useful long-term constraints for a platform that may later support:

- multiple users and learner profiles;
- offline-first operation;
- synchronization between devices;
- remote distribution of learning kits;
- institutional assignment and licensing;
- controlled author publishing;
- parallel engineering by independent AI agents.

It does not authorize immediate cloud implementation.

## Interpretation

Always distinguish:

1. **Implemented reality** — proven by exact source, tests, build, artifact and human evidence.
2. **Accepted current decision** — proven by governor state, ADR and accepted work package.
3. **Historical target constraint** — useful background that may have been superseded in sequence or scope.
4. **Unproven claim** — a plausible statement without reconstructed evidence.

When historical reference and current repository state differ, current repository state wins.

## Still-useful central direction

```text
Local-first learner product
        ↓
Explicit contracts and ownership boundaries
        ↓
Deterministic local behavior and provenance
        ↓
Optional modular-monolith platform only after separate gates
        ↓
Selective service extraction only on demonstrated need
```

The clean-break decision changes the migration path, not these quality principles.

## Non-negotiable prohibitions retained

- no immediate microservices;
- no synchronization of opaque global snapshots;
- no canonical identifier derived from an editable title;
- no UI-to-storage or UI-to-HTTP direct coupling;
- no parallel AI development without exact baseline and bounded scopes;
- no open marketplace before simpler product and operational gates are proven;
- no provenance claim unless reviewed source, tested artifact and distributed artifact are linked.

## Historical reading order

1. `01_ARCHITECTURE_CONSTITUTION.md`
2. `02_TARGET_SYSTEM_ARCHITECTURE.md`
3. `04_DEPENDENCY_AND_CONTRACT_RULES.md`
4. `09_QUALITY_RELEASE_AND_PROVENANCE.md`
5. `10_MULTI_AI_DEVELOPMENT_PROTOCOL.md`
6. `12_ROADMAP_AND_GATES.md`
7. `14_ASSUMPTIONS_CLAIMS_EVIDENCE.md`

The phase names and migration sequence inside these documents are not current unless reaffirmed by a later accepted decision.

## Normative terms

- **MUST** — non-negotiable constraint;
- **SHOULD** — expected rule; deviation requires a documented decision;
- **MAY** — permitted option;
- **HOLD** — intentionally deferred;
- **NO GO** — prohibited at the current maturity stage.
