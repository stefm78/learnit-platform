# Assumptions, claims, evidence, and missing proof

## Classification rules

### Evidence

A statement is evidence only when the relevant source, artifact, environment, and procedure are identified and the result has been observed or independently reproduced.

### Claim

A statement is a claim when a document, developer, test report, or tool asserts it but the repository cannot independently reconstruct the proof.

### Assumption

An assumption is a temporary planning premise. It must have an owner, consequence, and validation plan.

### Absence of evidence

Absence of evidence means the project must not conclude either success or failure. It is a gap to close, not permission to assume the preferred outcome.

## Current state register

| Statement | Classification | Current interpretation |
|---|---|---|
| A standalone Learn-it player exists and is actively being stabilized | Claim supported by project handovers | The source is not yet imported into this repository, so this repository cannot reconstruct it yet |
| The current player is ready for platform refactoring | Absence of evidence | Blocked until standalone promotion and `ARC-WP-000` |
| Local-first is the correct platform foundation | Architectural judgment | Strongly retained, but its future implementation still requires migration proof |
| The current storage and identifiers support multi-device synchronization | Unproven and likely false | Must be mapped against real source before design work begins |
| A modular monolith is sufficient for the first backend | Planning assumption with strong engineering rationale | Revisit only when deployment, scaling, security, or ownership evidence contradicts it |
| Several AI agents can safely implement features in parallel | Conditional claim | Not accepted until exact scopes, contract freeze, independent worktrees, CI scope checks, and an integration pilot exist |
| A remote paid kit library will create sustainable demand | Business hypothesis | Requires catalog and purchase experiments; do not treat marketplace as inevitable |
| Learning analytics can prove mastery | False as stated | The platform may store observations and interpretations, not cognitive certainty |
| Repository governance is fully enforced | False currently | Initial validator and CI exist on the bootstrap branch, but source, architecture tests, scope diff checks, and branch protections are not yet proven |

## Evidence obligations by domain

### Standalone player

Required:

- selected source commit;
- clean build;
- artifact hash;
- automated suites;
- target-device human tests;
- known-defect register;
- recovery and import/export tests.

### Architecture modularity

Required:

- real dependency graph;
- direct storage and network access inventory;
- cycle detection;
- executable boundary tests;
- small seam migration with behavior equivalence.

### Synchronization

Required:

- immutable event identity;
- deduplication;
- reordering tests;
- retry after ambiguous response;
- partition and reconnection;
- clock-skew handling;
- deterministic convergence;
- stale-client compatibility.

### Security and multi-tenancy

Required:

- threat model;
- authorization matrix;
- negative tenant-isolation tests;
- privileged-function review;
- audit records;
- backup restoration;
- export and deletion exercises.

### Learning quality

Required:

- versioned raw facts;
- explicit interpretation algorithm;
- evidence-compatibility rules across content revisions;
- human comprehension tests;
- retention and transfer studies before strong mastery claims.

### Commerce

Required:

- merchant and tax responsibility decision;
- idempotent order and webhook processing;
- refund and dispute behavior;
- entitlement recovery;
- offline revocation policy;
- support and unit-economics evidence.

## Review discipline

Every audit and pull request should answer:

1. What was directly observed?
2. What was only asserted?
3. What counterexample was attempted?
4. What environment and data were used?
5. What remains untested?
6. What decision would change if the missing proof contradicted the assumption?

Do not replace these questions with a confidence score alone.
