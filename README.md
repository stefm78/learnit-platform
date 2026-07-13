# Learn-it Platform

Private engineering repository for the controlled evolution of Learn-it from a stable standalone application toward a scalable, multi-user, local-first learning platform.

## Current status

The **repository foundation is installed**. The project remains in bootstrap mode for the application baseline.

- The active standalone application is still being stabilized outside this repository.
- No player source has been imported yet.
- No backend, account, synchronization, commerce, or marketplace implementation is authorized yet.
- The first engineering gate is [`ARC-WP-000`](work-packages/ARC-WP-000.json): establish an exact, reproducible baseline of the standalone version selected for import.

## Two-track strategy

1. **Standalone stabilization** — continue functional, UX, accessibility, persistence, performance, test, and release hardening without a transversal architectural rewrite.
2. **Platform readiness** — prepare executable architecture rules, contracts, repository governance, provenance, and migration seams without changing the player behavior.

See [`docs/roadmap/STANDALONE_TO_PLATFORM.md`](docs/roadmap/STANDALONE_TO_PLATFORM.md).

## Non-negotiable principles

- local-first player;
- modular monolith before microservices;
- stable canonical identifiers before synchronization;
- one owner per datum and one editable source of truth per normative artifact;
- short-lived branches and pull requests;
- AI work packages with exact baseline, bounded scope, independent QA, and controlled integration;
- tested artifact equals published artifact;
- no direct cloud coupling from UI or domain logic.

## Repository entry points

- [Architecture status and authority](docs/architecture/README.md)
- [Architecture reference — start here](docs/architecture/reference-v1/00_START_HERE.md)
- [Architecture constitution](docs/architecture/reference-v1/01_ARCHITECTURE_CONSTITUTION.md)
- [Contribution protocol](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Canonical baseline work package](work-packages/ARC-WP-000.json)

## Immediate next step

Keep `ARC-WP-000` blocked until the standalone development stream promotes a candidate. Then populate its exact source commit, artifact hash, evidence, and known-issues register before importing any player code.
