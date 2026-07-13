# Multi-AI development protocol

## 1. Objective

Allow several AI agents to contribute in parallel without creating incompatible abstractions, hidden scope expansion, duplicate utilities, or unreviewed cross-cutting changes.

Parallelism is authorized only after repository controls can enforce the mission boundaries.

## 2. Required roles

A workstream may use these independent roles:

- **architect** — defines boundaries, contracts, invariants, non-goals, and decision records;
- **implementer** — changes code within the approved scope;
- **adversarial QA** — creates independent tests and seeks counterexamples;
- **security reviewer** — reviews permissions, tenancy, secrets, data, and abuse cases;
- **learning reviewer** — reviews evidence semantics, mastery claims, and pedagogical effects;
- **product/UX reviewer** — reviews learner comprehension and interaction quality;
- **integrator** — owns convergence, conflict resolution, and the final pull request.

One agent may hold more than one low-risk role, but the implementer must not be the sole certifier of high-risk work.

## 3. Canonical mission contract

Every implementation mission must contain:

```text
workPackageId
baseCommit
branchName
allowedGlobs
forbiddenGlobs
contractSetHash
changeClass
riskClass
invariants
nonGoals
acceptanceTests
adversarialTests
expectedOutputs
requiredReviewers
rollback
maximumDiffSize or explicit size exception
```

A missing exact baseline blocks implementation.

## 4. Isolation

Each agent works in:

- an independent clone or Git worktree;
- an independent branch;
- a clean dependency environment;
- least-privilege credentials;
- no production secrets;
- no shared mutable working directory.

A branch belongs to one work package. Long-lived branches per agent are prohibited.

## 5. Scope enforcement

CI must compare the changed-file set between `baseCommit` and the proposed head against the work package.

The check fails when an agent changes:

- a file outside `allowedGlobs`;
- a file matching `forbiddenGlobs`;
- an undeclared contract;
- a migration owned by another active work package;
- release or security policy without the required reviewer;
- a lockfile without declaring the dependency change.

CODEOWNERS and review rules supplement this check; they do not replace it.

## 6. Contract freeze before parallel work

Parallel implementation is safe only when shared contracts are:

- identified;
- versioned;
- reviewed;
- accompanied by fixtures;
- frozen for the duration of the work packages.

When a contract must change:

1. stop dependent work;
2. amend the architecture decision or contract proposal;
3. rerun compatibility analysis;
4. rebase or regenerate affected work packages;
5. resume only after integration ownership is clear.

## 7. Conflict prevention

Two work packages must not concurrently own:

- the same migration;
- the same canonical schema;
- the same domain aggregate;
- the same release workflow;
- overlapping broad source paths;
- competing implementations of the same port.

Parallel work should prefer disjoint responsibilities such as:

```text
Agent A — canonical identifier value objects
Agent B — black-box migration tests
Agent C — repository scope validator
Agent D — independent threat review
```

## 8. Handover requirements

An agent handover must include:

- exact base and head commits;
- changed files;
- decisions made;
- assumptions;
- claims not proven;
- tests run and not run;
- generated evidence;
- known failures;
- rollback command or commit;
- follow-up work outside scope.

Do not hand over a large sandbox archive as the primary source of truth. The reviewed branch, work package, and evidence index are primary.

## 9. Integration protocol

The integrator:

1. verifies the base commit and scope;
2. checks that shared contracts did not drift;
3. reviews implementation and independent QA together;
4. runs repository, architecture, unit, integration, and relevant human gates;
5. reconstructs the proposed artifact from the reviewed source;
6. records any manual conflict resolution explicitly;
7. rejects silent repairs performed only in the integrator workspace;
8. opens or updates the pull request with complete evidence.

## 10. Risk classes

### Low

Documentation or isolated tests with no normative or release effect.

### Moderate

Bounded refactor, local adapter, or UI correction protected by regression tests.

### High

Contract, storage, migration, identifier, progress semantics, synchronization, or entitlement change.

### Critical

Identity, tenant isolation, payment, release provenance, destructive migration, privacy, or security-control change.

High and critical changes require independent adverse review and an explicitly named integrator.

## 11. Initial rollout

Do not begin with several concurrent feature agents.

The first pilot after the standalone baseline should use:

- one bounded implementation agent;
- one independent adversarial QA agent;
- one integrator;
- disjoint file ownership;
- a small reversible seam.

Scale parallelism only after the pilot completes without hidden scope expansion or manual repair.
