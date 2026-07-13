# Contributing to Learn-it Platform

## Repository phase

The repository is currently preparing the transition from a standalone application to a scalable platform. Until the standalone baseline is formally selected and imported, changes must be limited to repository governance, architecture evidence, contracts, validation tooling, and migration preparation.

The current project frame is defined by `governance/governor-state.json`. Contributors and AI agents must read it before proposing work.

## Mandatory workflow

1. Start from the current `main` commit.
2. Read `GOVERNANCE.md` and `governance/governor-state.json`.
3. Use one short-lived branch per bounded change.
4. Link the change to one canonical work package.
5. Declare the exact baseline commit and the permitted file scope.
6. Add or update independent tests before requesting review.
7. Open a pull request; do not commit directly to `main`.
8. Obtain Architecture & Repository Governor review when the change is high-risk, critical, cross-cutting, data-bearing, security-sensitive, or release-critical.
9. Merge only after required checks and reviews pass.
10. Prefer squash merge for bounded work packages.

## Change classes

Every pull request must identify one principal class:

- functional fix;
- UX or accessibility change;
- refactoring without behavior change;
- data migration;
- contract change;
- test or evidence improvement;
- repository governance or documentation.

Do not combine a functional correction, a storage migration, a contract change, and a transversal refactor in the same pull request.

## Governor review triggers

Governor review is mandatory when a change touches any of the following:

- architecture constitution or target architecture;
- canonical identifiers or contract semantics;
- persistence, migration, progress, synchronization, or entitlements;
- identity, tenancy, privacy, security, or destructive operations;
- release workflows, manifests, provenance, or build chain;
- shared code used by several modules;
- a phase transition or roadmap gate;
- a new exception or an extension of an existing exception;
- work currently listed as held or prohibited in the governor state.

The governor may require a review for other changes when scope, evidence, or regression risk is unclear.

## AI-agent requirements

An AI work package must state:

- `baseCommit`;
- `workPackageId`;
- allowed and forbidden paths;
- contracts that may change;
- invariants and acceptance tests;
- expected outputs;
- risk class;
- independent reviewer;
- rollback strategy.

An implementing agent must not certify its own work. Agents must use independent clones or worktrees and must not share an uncontrolled working directory.

## Architecture rules

- Domain code must not depend on UI, browser storage, HTTP, or vendor SDKs.
- UI code must not access persistence or remote APIs directly.
- A datum has one owning module.
- A normative artifact has one editable source of truth; derived Markdown, indexes, or issues must be generated.
- Titles and labels are never canonical identifiers.
- Published contracts are versioned and are not silently reinterpreted.
- Backend modules begin as a modular monolith; microservices require a demonstrated operational need.

## Security and data

Never commit:

- credentials or tokens;
- real learner data;
- private exports;
- production databases;
- unreviewed third-party content;
- generated release archives.

Use synthetic fixtures for tests.

## Definition of done

A change is not done until:

- its scope matches the work package;
- automated checks pass;
- the built artifact is produced from the reviewed source;
- regression risks and known limitations are documented;
- rollback is possible;
- architecture, QA, learning, security, governor, or human review gates required by its risk class are satisfied;
- `governance/governor-state.json` is updated when the effective project frame, risks, exceptions, or next gate changes.
