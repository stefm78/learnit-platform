# Learn-it Platform

Private engineering repository for the controlled evolution of Learn-it from a stable standalone application toward a scalable, multi-user, local-first learning platform.

## Current status

RC715 is the **promoted standalone forensic baseline**.

- The complete player source is maintained under [`apps/player/`](apps/player/).
- GitHub is the canonical source for all subsequent standalone development.
- Promoted source commit: `6c826977e16985d50b45d1b5e53501b4d7b993a2`.
- Promoted artifact SHA-256: `6d4546efbf9a1216e18fa90ee260e7d79841171c48f533d6b107266e281aa7c0`.
- [`ARC-WP-000`](work-packages/ARC-WP-000.json) is accepted after reproducible reconstruction, automated checks, governor review, and accountable-owner human validation PASS.
- The validated [`Remote Agent Worktree`](docs/governance/REMOTE_AGENT_WORKTREE.md) is accepted for bounded multi-file development with exact baseline, machine-checkable scope, read-only test execution, explicit test profiles, and pull-request review.
- Backend, accounts, synchronization, remote catalog, commerce, institutions, and marketplace implementation remain on HOLD.
- The permanent Architecture & Repository Governor maintains the frame through [`GOVERNANCE.md`](GOVERNANCE.md) and the canonical [`governor-state.json`](governance/governor-state.json).

## Two-track strategy

1. **Standalone product line** — continue bounded functional, UX, accessibility, persistence, performance, test, and release improvements from the promoted baseline.
2. **Controlled platform evolution** — establish permanent behavioral protection, then introduce one reversible architecture seam at a time under explicit gates.

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

- [Player source and engineering instructions](apps/player/README.md)
- [Remote Agent Worktree operating contract](docs/governance/REMOTE_AGENT_WORKTREE.md)
- [Remote Agent Worktree accepted work package](work-packages/DEV-WP-030.json)
- [Standing architecture and repository governance](GOVERNANCE.md)
- [Canonical current governor state](governance/governor-state.json)
- [RC715 promotion review](docs/governance/reviews/GOV-REVIEW-0003-RC715-PROMOTION.md)
- [Remote Agent Worktree acceptance review](docs/governance/reviews/GOV-REVIEW-0004-REMOTE-AGENT-WORKTREE.md)
- [RC715 human validation attestation](docs/evidence/rc715/human-validation-attestation.json)
- [Permanent player CI and behavioral protection gate](work-packages/QA-WP-010.json)
- [Governor decision rights](docs/governance/DECISION_RIGHTS.md)
- [Governor review template](docs/governance/GOVERNOR_REVIEW_TEMPLATE.md)
- [Architecture status and authority](docs/architecture/README.md)
- [Architecture reference — start here](docs/architecture/reference-v1/00_START_HERE.md)
- [Architecture constitution](docs/architecture/reference-v1/01_ARCHITECTURE_CONSTITUTION.md)
- [Contribution protocol](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Promoted standalone baseline work package](work-packages/ARC-WP-000.json)
- [Standing governor work package](work-packages/GOV-WP-001.json)

## Immediate next step

Pass [`QA-WP-010`](work-packages/QA-WP-010.json): establish permanent player CI and representative black-box regression fixtures before implementing the first architectural seam.
