# Architecture status

## Repository authority

Architecture authority is distributed deliberately:

1. active authority issues and accepted work packages define the currently authorized product scope;
2. accepted ADRs define cross-cutting decisions;
3. source, tests, build evidence and promoted artifact hashes describe implemented reality;
4. `governance/governor-state.json` remains the machine-readable governance record, but historical phase text is not rewritten by repository-hygiene work.

No historical roadmap or handover overrides later accepted and promoted repository facts.

## Current product boundary

- `apps/player/` remains the frozen RC718 legacy standalone generation.
- Learn-it Next is the implemented clean-break successor.
- Learning Loop V2 was promoted on commit `06c06d5ea0cadcb3cb2084769ff5ada4d0fe0a35`.
- Its exact promoted HTML SHA-256 is `9780bf3763864fbd42804a7dee129ae16e999e7971c4fce9a0a6a240d52b20df`.
- Project Atlas M1 is promoted on product merge `354a2cf27954de13435a08a2a4ec014b9e8a2e89`, with accepted INT `e2c10c8eb5a3e1c4dff5e45b210f327942bafce8` and accepted QA `67d70e7307402242dbc1939d6cabfd87af617d74`.
- The promoted M1 artifact is `334194` bytes with SHA-256 `6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f`.
- Atlas M2 memory/reconfirmation is promoted on product merge `dd0c191179f968d35742cb58f7d6bb9ccb53a852`.
- Atlas M2.2 transfer plus learner-facing clarity is promoted with accepted product HEAD `abaa0af0dcbd5338be2221587c1e871c4f939c52` and accepted QA HEAD `0e529f8b4f684a7c9aa900742efe94b2a012abc0`; its exact canonical artifact is `366412` bytes with SHA-256 `4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7` and is published through GitHub Pages.
- M3.0 Authoring Foundation design is accepted under completed issue `#223`; it freezes a separate local/offline authoring application, canonical validator reuse, deterministic export/re-import evidence and exact future implementation/QA paths. Product implementation is not yet authorized.
- Backend, accounts, synchronization, remote catalog, commerce, tenancy and marketplace remain held.

## Current decisions

- Local-first remains the product foundation.
- No LLM, remote AI API or network dependency is allowed during learning.
- Atlas uses an embedded deterministic, versioned and explainable adaptive engine.
- Learning facts are immutable events; visible states are recalculable projections.
- Practice, correction and validation remain distinct.
- Gamification rewards pedagogical evidence, not consumption.
- Controlled parallel AI implementation uses bounded ownership, independent QA and non-repairing integration.
- Tested artifact must equal distributed artifact.
- Atlas M2 adds no database, store or migration; it derives reconfirmation state from immutable M1 evidence under the bounded policy authorized by issue `#157`.
- Atlas M2.2 adds deterministic transfer evidence without changing the memory schedule, then applies only bounded learner-facing clarity corrections; it introduces no backend, storage migration or runtime network dependency.
- M3.0 Authoring Foundation must be architecturally separate from the learner runtime: shared canonical contracts are allowed, shared authoring/runtime behavior is not.

## Accepted architecture decisions

- [`ADR-0001 — Stable identity taxonomy and migration design`](decisions/ADR-0001-STABLE-IDENTITY-MIGRATION.md)
- [`ADR-0002 — Clean-break generation`](decisions/ADR-0002-CLEAN-BREAK-GENERATION.md)
- [`ADR-0003 — Atlas local adaptive runtime`](decisions/ADR-0003-ATLAS-LOCAL-ADAPTIVE-RUNTIME.md)

## Atlas reading order

1. `../../governance/governor-state.json`;
2. `../../work-packages/ATLAS-WP-005.json`, `ATLAS-WP-006.json` and `ATLAS-WP-007.json` for completed M2.2 product and publication evidence;
3. M3.0 design authority issue `#223`;
4. `../atlas/README.md`;
5. `../atlas/CONTRACTS.md`;
6. `decisions/ADR-0003-ATLAS-LOCAL-ADAPTIVE-RUNTIME.md`;
7. `../../GOVERNANCE.md`.

Historical `reference-v1/` material remains non-canonical.

## Active Atlas gate

Atlas M1 bootstrap, lane execution, integration, independent QA, human validation, promotion and post-merge verification are historical completed steps.

Atlas M2 product implementation, M2.2 transfer and clarity correction, independent QA, accountable-human validation, promotion and exact-artifact Pages publication are completed historical steps.

M3.0 Authoring Foundation design is accepted. The next mandatory gate is a fresh bounded implementation package that conforms exactly to `../atlas/M3_AUTHORING_FOUNDATION_DESIGN.md`.

Product implementation remains HOLD until that separate authority is explicitly opened. Gate3, Gate4 and M4+ platform evolution remain separately held.
