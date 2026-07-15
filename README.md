# Learn-it

Private engineering repository for the controlled evolution of Learn-it.

## Current status

Learn-it now has two explicitly separated generations:

1. **RC718 legacy standalone** — frozen, promoted and retained for historical access.
2. **Clean-generation successor** — design authorized in principle through the clean-break decision, but implementation not yet authorized.

The legacy baseline is:

- source commit: `decd9b77bc77a6de9dc28497d0f3affeb972e964`;
- promoted artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`;
- human gate: **RC719 — PASS_WITH_RESERVATIONS**;
- source: [`apps/player/`](apps/player/).

`ARC-WP-021` selected trajectory **C — clean break**. The next generation will not automatically read or migrate RC718 libraries, progress, sessions, bilans, retention or packages. RC718 remains independently usable and must not be mutated by new-generation work.

## Canonical current state

Read these sources in this order:

1. [`governance/governor-state.json`](governance/governor-state.json) — machine-readable current authority;
2. [`docs/handover/STAGE_D_RESTART_CHECKPOINT.md`](docs/handover/STAGE_D_RESTART_CHECKPOINT.md) — concise restart point;
3. [`ADR-0002 — Clean-break generation`](docs/architecture/decisions/ADR-0002-CLEAN-BREAK-GENERATION.md);
4. [`ARC-WP-021`](work-packages/ARC-WP-021.json);
5. [`GOVERNANCE.md`](GOVERNANCE.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).

Historical work packages, reviews and architecture references remain evidence, but they do not override current governor state.

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
- [Current roadmap](docs/roadmap/STANDALONE_TO_PLATFORM.md)
- [Governor decision rights](docs/governance/DECISION_RIGHTS.md)
- [Repository security policy](SECURITY.md)

## Next mandatory gate

`ARC-WP-022` must design and authorize the minimum viable clean-generation foundation:

- new major kit contract;
- canonical identities from creation;
- isolated localStorage and IndexedDB namespaces;
- empty initial active state;
- explicit rejection of RC718 packages;
- regenerated Nombres complexes and Signaux électriques golden kits;
- exact source and file-budget plan;
- disjoint development, contradictory-QA, integration and governor scopes;
- deterministic build and source-to-artifact evidence.

No new-generation implementation begins before that gate is accepted.
