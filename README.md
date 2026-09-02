# Learn-it

Public engineering repository for the controlled evolution of Learn-it.

## Current status

Learn-it now has two explicitly separated generations:

1. **RC718 legacy standalone** — frozen, promoted and retained for historical access.
2. **Learn-it Next** — clean-generation successor implemented and promoted through Learning Loop V2, then extended by Project Atlas.

Current Atlas facts:

- Atlas M1 is promoted: product merge `354a2cf27954de13435a08a2a4ec014b9e8a2e89`;
- Atlas M2 memory/reconfirmation is promoted: product merge `dd0c191179f968d35742cb58f7d6bb9ccb53a852`;
- Atlas M2.2 transfer plus bounded learner-facing clarity is promoted and published;
- accepted final M2.2 product HEAD: `abaa0af0dcbd5338be2221587c1e871c4f939c52`;
- accepted final M2.2 QA HEAD: `0e529f8b4f684a7c9aa900742efe94b2a012abc0`;
- exact promoted M2.2 artifact: `366412` bytes, SHA-256 `4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7`;
- accountable-human gate: `PASS M2.2 — GO PROMOTION`;
- GitHub Pages publishes that exact artifact at https://stefm78.github.io/learnit-platform/.
- M3.0 Authoring Foundation and browser/Pages packaging are promoted as a separate authoring application;
- M3.1 Pedagogical Quality Engine is promoted with frozen product HEAD `6fa1acc23999b5a0b9a0b7f375a12f19ecc4e4e2`, independent QA HEAD `6ff592af68e6cc95bd479911a09388293c5528f5` and promotion merge `be3d5b2635836e8ce0d9a6ecf42d573efc9ef749`;
- M3.1 stable authoring is published at https://stefm78.github.io/learnit-platform/authoring/ through main `601cade1376e6f87e71351fe3f201833a9356697`;
- the M3.1 human gate accepted the AI-authoring orientation; sequence-level graphical human review remains deferred debt #272;
- M3.2 AI Kit Factory is promoted via merge `39775e83d029f780bf0fa21783ea597ab1abc6b5`;
- M3.2.5 Factory Reliability is promoted via merge `524cfc8b35654d7d54d3222a462fe582f4706a89` and qualified on a real eight-domain benchmark: 8 runs, 6 PASS, 2 justified HOLD, 0 human escalations, verdict `PASS_FACTORY_BENCHMARK_V1`;
- M3.3 Portable Review Handoff is promoted via merge `c102ca81f3b144bea1140860ef633a0d01987d59`, after independent QA PASS and fresh separate-reviewer PASS/HOLD qualification.

The legacy baseline is:

- source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`;
- promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`;
- human gate: **RC719 — PASS_WITH_RESERVATIONS**;
- source: [`apps/player/`](apps/player/).

`ARC-WP-021` selected trajectory **C — clean break**. The new generation does not automatically read or migrate RC718 libraries, progress, sessions, bilans, retention or packages. RC718 remains independently usable and must not be mutated by new-generation work.

## Canonical current state

For current product work, read these sources in this order:

1. [`governance/governor-state.json`](governance/governor-state.json) for the repository's machine-readable current state;
2. [`ATLAS-WP-005`](work-packages/ATLAS-WP-005.json), [`ATLAS-WP-006`](work-packages/ATLAS-WP-006.json) and [`ATLAS-WP-007`](work-packages/ATLAS-WP-007.json) for the unchanged promoted learner M2.2 baseline;
3. [`ATLAS-WP-009`](work-packages/ATLAS-WP-009.json), [`ATLAS-WP-010`](work-packages/ATLAS-WP-010.json) and [`ATLAS-WP-012`](work-packages/ATLAS-WP-012.json) for the promoted M3.0/M3.1 authoring product;
4. [`docs/atlas/M3_1_PEDAGOGICAL_QUALITY_ENGINE_DESIGN.md`](docs/atlas/M3_1_PEDAGOGICAL_QUALITY_ENGINE_DESIGN.md) for the promoted M3.1 quality architecture;
5. [`docs/atlas/M3_2_AI_KIT_FACTORY_DESIGN.md`](docs/atlas/M3_2_AI_KIT_FACTORY_DESIGN.md), [`ATLAS-WP-014`](work-packages/ATLAS-WP-014.json) and [`ATLAS-WP-015`](work-packages/ATLAS-WP-015.json) for the promoted and reliability-qualified M3.2 factory;
6. [`authoring/factory/benchmark_contract.json`](authoring/factory/benchmark_contract.json) and [`authoring/factory/reliability.py`](authoring/factory/reliability.py) for the deterministic M3.2.5 qualification authority;
7. [`docs/atlas/M3_3_PORTABLE_REVIEW_HANDOFF_DESIGN.md`](docs/atlas/M3_3_PORTABLE_REVIEW_HANDOFF_DESIGN.md), [`ATLAS-WP-019`](work-packages/ATLAS-WP-019.json) and [`authoring/factory/handoff.py`](authoring/factory/handoff.py) for promoted M3.3 portable independent-review transport/re-entry;
8. accepted architecture decisions under [`docs/architecture/decisions/`](docs/architecture/decisions/);
9. [`GOVERNANCE.md`](GOVERNANCE.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).

Historical work packages, reviews, handovers and roadmap stages remain evidence; they do not describe active work merely because they use terms such as “current” or “next gate”.

## Non-negotiable principles

- GitHub is the canonical editable source.
- RC718 source, artifact and browser data remain isolated and immutable from the successor.
- The new generation uses a new major content contract and isolated storage namespaces.
- Titles, slugs, order and filenames are never canonical identity.
- No compatibility resolver, dual-read layer or learner-state migration is introduced without a new accountable-owner decision.
- One datum and one normative artifact have one owner.
- AI work uses exact baselines, bounded paths, independent QA and controlled integration.
- Tested artifact equals distributed artifact.
- Backend, accounts, synchronization, remote catalog, commerce, tenancy and marketplace remain held.

## Engineering entry points

- [Frozen RC718 Player](apps/player/README.md)
- [Remote Agent Worktree contract](docs/governance/REMOTE_AGENT_WORKTREE.md)
- [Architecture status](docs/architecture/README.md)
- [Historical clean-generation roadmap](docs/roadmap/STANDALONE_TO_PLATFORM.md)
- [Governor decision rights](docs/governance/DECISION_RIGHTS.md)
- [Repository security policy](SECURITY.md)

## Active product gate

Atlas M2.2 remains the promoted learner runtime baseline. M3.0 Authoring Foundation and M3.1 Pedagogical Quality are promoted and stably published as the separate authoring surface.

M3.2 **AI Kit Factory** is promoted, M3.2.5 **Factory Reliability** is qualified, and M3.3 **Portable Review Handoff** is promoted. M3.3 turns the independent-review boundary into a deterministic one-case portable bundle and fail-closed review re-entry without adding a model provider, learner-runtime AI or automatic publishing.

Independent contradictory QA passed on frozen product HEAD `d4fe01f94ce38b2cd4d884930555f2bce971f561`. Fresh separate reviewer conversations then produced a real PASS path and a real justified HOLD path, both consumed into self-verifying FactoryRuns before promotion merge `c102ca81f3b144bea1140860ef633a0d01987d59`.

The factory still deliberately avoids a generic Source-to-Draft/document-ingestion subsystem, model-provider dependency, learner-runtime AI, backend and canonical-kit contract expansion. Real source/candidate/review corpora remain evidence artifacts rather than Git repository content.

Human graphical/context review debt is tracked in #272 and remains non-blocking until human supervision becomes a first-class authoring workflow.

M3.4 Scale and Publishing is the next possible product gate but remains HOLD pending fresh accountable-owner arbitration/design. Gate3, Gate4, M4+, backend, accounts, synchronization, remote catalog and runtime AI remain HOLD.
