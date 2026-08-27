# Learn-it

Public engineering repository for the controlled evolution of Learn-it.

## Current status

Learn-it now has two explicitly separated generations:

1. **RC718 legacy standalone** — frozen, promoted and retained for historical access.
2. **Learn-it Next** — clean-generation successor implemented and promoted through Learning Loop V2, then extended by Project Atlas.

Current Atlas facts:

- Atlas M1 is promoted: product merge `354a2cf27954de13435a08a2a4ec014b9e8a2e89`;
- accepted M1 INT: `e2c10c8eb5a3e1c4dff5e45b210f327942bafce8`;
- accepted M1 QA: `67d70e7307402242dbc1939d6cabfd87af617d74`;
- promoted M1 artifact: `334194` bytes, SHA-256 `6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f`;
- Atlas M2 is promoted: product merge `dd0c191179f968d35742cb58f7d6bb9ccb53a852`, accepted QA head `4b0d80dd3b576a2300a4d1516481769b198d9637`, canonical artifact `352237` bytes / SHA-256 `7c242614c394ca1a0eb739c0f02c672c6afe280a128056a8f75b96266727a091`; the human promotion gate passed and GitHub Pages publishes that exact artifact at https://stefm78.github.io/learnit-platform/.

The legacy baseline is:

- source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`;
- promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`;
- human gate: **RC719 — PASS_WITH_RESERVATIONS**;
- source: [`apps/player/`](apps/player/).

`ARC-WP-021` selected trajectory **C — clean break**. The new generation does not automatically read or migrate RC718 libraries, progress, sessions, bilans, retention or packages. RC718 remains independently usable and must not be mutated by new-generation work.

## Canonical current state

For current product work, read these sources in this order:

1. [`governance/governor-state.json`](governance/governor-state.json) for the repository's machine-readable current state;
2. [`ATLAS-WP-003`](work-packages/ATLAS-WP-003.json) and [`ATLAS-WP-004`](work-packages/ATLAS-WP-004.json) for the completed M2 product and Pages promotion evidence;
3. [Atlas M2 authority #157](https://github.com/stefm78/learnit-platform/issues/157) for the completed M2 decision history;
4. accepted architecture decisions under [`docs/architecture/decisions/`](docs/architecture/decisions/);
5. [`GOVERNANCE.md`](GOVERNANCE.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).

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

Atlas M2 is promoted and published. There is currently **no active product increment**.

The next product increment must begin with a new explicit authority issue/work package and bounded scope; completed M2 authority #157 does not implicitly authorize additional product changes.
