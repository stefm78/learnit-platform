# Architecture status

## Repository authority

Current architecture authority is distributed deliberately:

1. `governance/governor-state.json` defines the active phase, held work, risks and next gate.
2. Accepted ADRs define cross-cutting decisions.
3. Accepted work packages define exact scope and evidence.
4. `docs/handover/STAGE_D_RESTART_CHECKPOINT.md` is the concise restart point.
5. Source, tests, build evidence and promoted artifact hashes describe implemented reality.

No historical roadmap or architecture reference overrides these sources.

## Current product boundary

- **RC718** is the frozen promoted legacy standalone Player under `apps/player/`.
- **RC719** is the human promotion gate with `PASS_WITH_RESERVATIONS`.
- `ARC-WP-021` selected a **clean-break successor generation**.
- The successor does not automatically read or migrate RC718 content or learner data.
- New-generation implementation remains blocked until `ARC-WP-022` is accepted.

## Current decisions

- Local-first remains the product foundation.
- The successor starts with a new major kit contract and isolated browser storage.
- `learnit-identity-v1` remains the accepted identity taxonomy.
- Canonical identity is native to the successor and never derived from editable titles, slugs, order or filenames.
- RC718 compatibility resolver, identity overlay, dual-read and learner-state migration are not planned.
- AI implementation uses exact baselines, disjoint write ownership, contradictory QA and controlled integration.
- Tested artifact must equal distributed artifact.
- Backend, accounts, synchronization, remote catalog, commerce, tenancy and marketplace remain held.

## Accepted architecture decisions

- [`ADR-0001 — Stable identity taxonomy and migration design`](decisions/ADR-0001-STABLE-IDENTITY-MIGRATION.md): identity taxonomy retained; continuity sequence superseded by ADR-0002.
- [`ADR-0002 — Clean-break generation`](decisions/ADR-0002-CLEAN-BREAK-GENERATION.md): current successor strategy.

## Historical reference v1

Documents under `reference-v1/` are preserved challenged target material created before Player import and before the clean-break decision. They remain useful for long-term constraints such as modular-monolith preference, provenance and bounded multi-AI development.

They are **not canonical for current phase, current baseline, next gate or migration sequence**. Begin with [`reference-v1/00_START_HERE.md`](reference-v1/00_START_HERE.md), which records this historical boundary.

## Current reading order

1. `../governance/governor-state.json`
2. `../handover/STAGE_D_RESTART_CHECKPOINT.md`
3. `decisions/ADR-0002-CLEAN-BREAK-GENERATION.md`
4. `../../work-packages/ARC-WP-021.json`
5. `../../GOVERNANCE.md`
6. `../roadmap/STANDALONE_TO_PLATFORM.md`
7. historical `reference-v1/` only when deeper background is needed

## Next gate

`ARC-WP-022` must design and authorize the minimum viable clean-generation foundation. It must freeze the new contract and shared boundaries before any parallel implementation starts.
