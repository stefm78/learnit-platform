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
- M3.0 Authoring Foundation and its browser/Pages packaging are promoted as a separate local/static authoring application.
- M3.1 Pedagogical Quality Engine is promoted with frozen product HEAD `6fa1acc23999b5a0b9a0b7f375a12f19ecc4e4e2`, independent QA HEAD `6ff592af68e6cc95bd479911a09388293c5528f5`, promotion merge `be3d5b2635836e8ce0d9a6ecf42d573efc9ef749` and stable Pages publication merge `601cade1376e6f87e71351fe3f201833a9356697`.
- The promoted learner runtime remains the exact M2.2 artifact: `366412` bytes, SHA-256 `4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7`. M3 authoring does not redefine learner artifact identity.
- Human sequence-level graphical review debt for AI-authored kits is tracked as issue `#272` and remains deferred/non-blocking.
- M3.2 AI Kit Factory is promoted under `ATLAS-WP-014` / issue `#286`, preserving the accepted direct-source author AI → deterministic structural gates → independent semantic review → deterministic PASS/HOLD architecture.
- M3.2.5 Factory Reliability is promoted and real-source qualified under `ATLAS-WP-015` / issue `#297`: 8 distinct real FactoryRuns across all required domains, 6 PASS, 2 justified semantic HOLD, zero human escalations, final verdict `PASS_FACTORY_BENCHMARK_V1`.
- M3.3 Portable Review Handoff is promoted under `ATLAS-WP-019` / issue `#310`, frozen product HEAD `d4fe01f94ce38b2cd4d884930555f2bce971f561`, independent QA PASS and promotion merge `c102ca81f3b144bea1140860ef633a0d01987d59`.
- M3.4 Qualified Release Set is promoted under `ATLAS-WP-021` / issue `#322`, frozen product HEAD `870d69800dcb07fcfff9f1d232dd143c8eaa6486`, independent QA R2 HEAD `9c0e20ef176ee03532543d009f22979c95d0d748`, verdict `PASS_QA_WP_024_R2_EXACT_HEAD_CONTRADICTORY_QA` and promotion merge `b8337c785cbec995de5891080776c4c44dd99179`. The additive layer is local/offline, content-addressed and deterministic; it does not add remote publishing, signing, assets or learner-runtime behavior.
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
- M3.0/M3.1 authoring remains architecturally separate from the learner runtime: shared canonical contracts are allowed, authoring-only behavior is not embedded into the learner artifact.
- M3.1 has one deterministic Python pedagogical-quality authority shared by CLI, CI and Studio. Canonical schema/validators remain upstream; browser JavaScript renders the Python report and does not duplicate `PQ_*` rule semantics.
- AI self-iteration is an authoring/development workflow only: source material → constrained Atlas authoring skill → candidate kit → canonical validation → pedagogical-quality report → correction/rerun. No runtime LLM or authoring network dependency is introduced.
- M3.2 extends this with logical role separation: an author AI may create/repair; a separate reviewer context must challenge source fidelity, correctness, ambiguity, objective coverage, validation/transfer authenticity and learner-fit. Deterministic code validates the review contract and exact hash binding, not semantic truth itself.
- Source provenance for M3.2 remains factory evidence outside `learnit.kit.v2`; no source/draft schema is added to the learner contract.

## Accepted architecture decisions

- [`ADR-0001 — Stable identity taxonomy and migration design`](decisions/ADR-0001-STABLE-IDENTITY-MIGRATION.md)
- [`ADR-0002 — Clean-break generation`](decisions/ADR-0002-CLEAN-BREAK-GENERATION.md)
- [`ADR-0003 — Atlas local adaptive runtime`](decisions/ADR-0003-ATLAS-LOCAL-ADAPTIVE-RUNTIME.md)

## Atlas reading order

1. `../../governance/governor-state.json`;
2. `../../work-packages/ATLAS-WP-005.json`, `ATLAS-WP-006.json` and `ATLAS-WP-007.json` for the unchanged promoted M2.2 learner baseline;
3. `../../work-packages/ATLAS-WP-009.json`, `ATLAS-WP-010.json` and `ATLAS-WP-012.json` for promoted M3.0/M3.1 authoring;
4. `../atlas/M3_1_PEDAGOGICAL_QUALITY_ENGINE_DESIGN.md` and `../../authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V1.md`;
5. `../atlas/M3_2_AI_KIT_FACTORY_DESIGN.md`, `../../work-packages/ATLAS-WP-014.json` and `../../work-packages/ATLAS-WP-015.json`;
6. `../../authoring/factory/benchmark_contract.json` and `../../authoring/factory/reliability.py`;
7. `../atlas/M3_3_PORTABLE_REVIEW_HANDOFF_DESIGN.md`, `../../work-packages/ATLAS-WP-019.json` and `../../authoring/factory/handoff.py`;
8. `../atlas/M3_4_QUALIFIED_RELEASE_SET_DESIGN.md`, `../../work-packages/ATLAS-WP-021.json` and `../../authoring/factory/release_set.py`;
9. `../atlas/README.md`;
10. `../atlas/CONTRACTS.md`;
11. `decisions/ADR-0003-ATLAS-LOCAL-ADAPTIVE-RUNTIME.md`;
12. `../../GOVERNANCE.md`.

Historical `reference-v1/` material remains non-canonical.

## Active Atlas gate

Atlas M1, M2 and M2.2 learner milestones are promoted historical steps. The exact learner artifact remains unchanged at 366412 bytes / SHA-256 `4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7`.

M3.0 Authoring Foundation, M3.0 browser/Pages packaging and M3.1 Pedagogical Quality are promoted, independently tested and stably published under `/authoring/`.

M3.2 **AI Kit Factory** is promoted, M3.2.5 **Factory Reliability** is qualified, M3.3 **Portable Review Handoff** is promoted, and M3.4 **Qualified Release Set** is promoted. The architecture remains provider-neutral: source files + learner brief → author AI → canonical/M3.1 structural gates → independent semantic reviewer → deterministic FactoryRun PASS/HOLD → deterministic qualified release-set composition.

M3.4 binds exact canonical kit bytes to self-verifying PASS FactoryRuns, rechecks canonical identity/digest claims, rejects cross-kit collisions, emits one deterministic content-addressed release ZIP, and verifies that ZIP offline. The accepted product HEAD is `870d69800dcb07fcfff9f1d232dd143c8eaa6486`; fresh contradictory QA R2 passed on QA HEAD `9c0e20ef176ee03532543d009f22979c95d0d748`; promotion merge is `b8337c785cbec995de5891080776c4c44dd99179`. CI-WP-013 repaired only central post-merge routing at `f4bbc91c5d480e2996faa8a592c3c18fd83d8906`.

Human graphical/context review debt remains open as issue `#272`. No remote distribution backend, publisher authentication/signature, asset/media contract or learner-runtime capability is implied by M3.4.

The next product direction is **HOLD pending fresh accountable-owner arbitration**. At minimum that arbitration must compare controlled remote distribution/publishing, debt #272, further factory/operator automation, and stopping because the current local/static workflow is sufficient. Gate3, Gate4 and M4+ platform evolution remain separately held.
