# Contributing to Learn-it

## Repository phase

The repository contains:

- the frozen RC718 legacy standalone Player;
- accepted architecture, governance, test and release evidence;
- the clean-break decision for a distinct successor generation.

RC718 is not an in-place migration base. New-generation implementation remains blocked until `ARC-WP-022` defines and authorizes the minimum foundation. The current project frame is always defined by `governance/governor-state.json`.

## Mandatory workflow

1. Start from the exact current `main` commit.
2. Read `GOVERNANCE.md`, `governance/governor-state.json` and the restart checkpoint.
3. Use one short-lived branch per bounded change.
4. Link the change to one canonical work package.
5. Declare the exact baseline commit and permitted file scope.
6. Declare contracts, data ownership, invariants, non-goals and rollback.
7. Add independent tests or evidence before requesting review.
8. Open a pull request; do not commit directly to `main`.
9. Obtain Architecture & Repository Governor review for cross-cutting, data-bearing, security-sensitive, release-critical or held work.
10. Merge only after required checks and reviews pass.
11. Delete the short-lived branch after merge.

## Change classes

Every pull request identifies one principal class:

- functional fix;
- UX or accessibility change;
- refactoring without behavior change;
- data or storage change;
- contract change;
- test or evidence improvement;
- repository governance or documentation.

Do not combine a functional correction, storage redesign, contract change and transversal refactor in one pull request.

## Current product boundaries

### RC718 legacy maintenance

A bounded maintenance package may change RC718 only when explicitly authorized. It must preserve its source-to-artifact provenance and must not be presented as successor-generation work.

### Clean-generation successor

Until `ARC-WP-022` is accepted, allowed work is limited to design, evidence, contract preparation, test planning, repository cleanliness and work-package preparation.

The successor must not:

- read, rewrite, clear or migrate RC718 browser storage;
- accept an RC718 package through a hidden compatibility path;
- derive canonical identity from titles, slugs, ordering, filenames or collision suffixes;
- copy all RC718 implementation without current product justification;
- enter backend, accounts, synchronization, catalog, commerce, tenancy or marketplace domains.

## Governor review triggers

Governor review is mandatory when a change touches:

- architecture decisions or phase gates;
- canonical identifiers or contract semantics;
- persistence, progress, migration, synchronization or destructive operations;
- privacy, security, tenancy, identity or authorization;
- release workflows, manifests, provenance or build chain;
- shared code used by several modules;
- source-file budget or repository ownership boundaries;
- active risks, exceptions, held or prohibited work.

## AI-agent requirements

An AI work package must state:

- exact `baseCommit` and `workPackageId`;
- allowed and forbidden paths;
- owned contracts and data;
- invariants and acceptance tests;
- expected outputs and evidence;
- risk class;
- independent contradictory reviewer;
- integration order and rollback strategy.

An implementing agent must not certify its own work. Parallel agents must have disjoint write scopes and independent clones or worktrees. Shared contracts are frozen before implementation starts.

## Architecture rules

- Domain code does not depend on UI, browser storage, HTTP or vendor SDKs.
- UI code does not access persistence or remote APIs directly.
- A datum has one owning module.
- A normative artifact has one editable source of truth.
- Titles and labels are never canonical identifiers.
- Published contracts are versioned and are not silently reinterpreted.
- Compatibility code requires an explicit accountable-owner decision.
- Backend modules, when eventually authorized, begin as a modular monolith.

## Security and repository hygiene

Never commit:

- credentials or tokens;
- real learner data or private exports;
- production databases;
- unreviewed third-party content;
- generated build or release archives;
- local agent output, caches or dependency trees.

Use synthetic fixtures and repository-approved evidence paths.

## Definition of done

A change is not done until:

- its exact files match its work package;
- automated checks pass;
- independent review is recorded;
- regression risks and limitations are explicit;
- rollback is possible;
- source, tests, build and artifact identities agree when a product artifact is involved;
- governor state is updated when the effective frame, risks, exceptions or next gate changes.
