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
- Atlas M2 is active under issue [#157](https://github.com/stefm78/learnit-platform/issues/157); product PR [#158](https://github.com/stefm78/learnit-platform/pull/158) and independent QA PR [#159](https://github.com/stefm78/learnit-platform/pull/159) remain draft and unmerged.

The legacy baseline is:

- source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`;
- promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`;
- human gate: **RC719 — PASS_WITH_RESERVATIONS**;
- source: [`apps/player/`](apps/player/).

`ARC-WP-021` selected trajectory **C — clean break**. The new generation does not automatically read or migrate RC718 libraries, progress, sessions, bilans, retention or packages. RC718 remains independently usable and must not be mutated by new-generation work.

## Canonical current state

For current product work, read these sources in this order:

1. [Atlas M2 authority #157](https://github.com/stefm78/learnit-platform/issues/157) and its exact active PRs [#158](https://github.com/stefm78/learnit-platform/pull/158) / [#159](https://github.com/stefm78/learnit-platform/pull/159);
2. [`ATLAS-WP-001`](work-packages/ATLAS-WP-001.json) and [`ATLAS-WP-002`](work-packages/ATLAS-WP-002.json) for completed M1 and publication history;
3. [`governance/governor-state.json`](governance/governor-state.json) for the repository's machine-readable governance record;
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

Atlas M2 is the active product increment under issue #157. PR #158 has an exact product candidate and PR #159 carries independent contradictory QA, but both remain draft and unmerged.

No M2 promotion, merge to `main`, or GitHub Pages repin is authorized until the exact M2 artifact passes the accountable human gate and an explicit promotion decision is recorded.
