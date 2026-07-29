# Architecture status

## Repository authority

Current architecture authority is distributed deliberately:

1. `governance/governor-state.json` defines the active phase, promoted baseline, authorized work, held work, risks and next gate.
2. Accepted ADRs define cross-cutting decisions.
3. Accepted work packages define exact scope, file ownership and evidence.
4. Source, tests, build evidence and promoted artifact hashes describe implemented reality.

No historical roadmap or handover overrides these sources.

## Current product boundary

- `apps/player/` remains the frozen RC718 legacy standalone generation.
- Learn-it Next is a clean-break successor.
- Learning Loop V2 was promoted on commit `06c06d5ea0cadcb3cb2084769ff5ada4d0fe0a35`.
- Its exact promoted HTML SHA-256 is `9780bf3763864fbd42804a7dee129ae16e999e7971c4fce9a0a6a240d52b20df`.
- Project Atlas M1 is authorized for bootstrap under issue `#130`.
- Backend, accounts, synchronization, remote catalog, commerce, tenancy and marketplace remain held.

## Current decisions

- Local-first remains the product foundation.
- No LLM, remote AI API or network dependency is allowed during learning.
- Atlas M1 uses an embedded deterministic, versioned and explainable adaptive engine.
- Learning facts are immutable events; visible states are recalculable projections.
- Practice, correction and validation remain distinct.
- Gamification rewards pedagogical evidence, not consumption.
- Parallel AI implementation uses four disjoint lanes, independent QA and non-repairing integration.
- Tested artifact must equal distributed artifact.

## Accepted architecture decisions

- [`ADR-0001 — Stable identity taxonomy and migration design`](decisions/ADR-0001-STABLE-IDENTITY-MIGRATION.md)
- [`ADR-0002 — Clean-break generation`](decisions/ADR-0002-CLEAN-BREAK-GENERATION.md)

## Proposed Atlas decision

- [`ADR-0003 — Atlas local adaptive runtime`](decisions/ADR-0003-ATLAS-LOCAL-ADAPTIVE-RUNTIME.md)

ADR-0003 becomes accepted when the Atlas bootstrap PR is merged by the accountable owner.

## Atlas reading order

1. `../../governance/governor-state.json`
2. `../atlas/README.md`
3. `../atlas/CONTRACTS.md`
4. `decisions/ADR-0003-ATLAS-LOCAL-ADAPTIVE-RUNTIME.md`
5. `../../work-packages/ATLAS-WP-001.json`
6. `../../GOVERNANCE.md`

Historical `reference-v1/` material remains non-canonical.

## Next gate

Merge the Atlas bootstrap PR without product runtime changes. Its merge commit becomes the exact common base for the four authorized M1 development lanes.
