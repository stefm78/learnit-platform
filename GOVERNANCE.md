# Learn-it governance

## Standing authority

Learn-it uses a permanent **Architecture & Repository Governor** to preserve the project frame across releases, contributors, AI agents, and future platform stages.

The governor is a function, not a personality and not a temporary reviewer. Its mandate survives individual chats, agents, work packages, and release candidates.

## Accountable owner and operational governor

- **Accountable owner:** repository owner `@stefm78`.
- **Operational governor:** the AI or human explicitly executing the governor charter for a review.
- **Independent reviewers:** architecture, QA, security, learning, product/UX, or operations reviewers required by the risk class.

The operational governor may recommend, block, or escalate. Final business and product accountability remains with the accountable owner.

## Governor authority

The governor may:

- block a work package or pull request that violates the architecture constitution;
- require an ADR before a cross-cutting or irreversible decision;
- freeze a shared contract during parallel development;
- stop parallel AI work when baselines or scopes overlap;
- require additional adverse tests or human gates;
- declare architecture drift or repository-governance drift;
- move a capability to `HOLD` or `NO GO` until evidence exists;
- require rollback or removal of an expired exception;
- reject claims presented as evidence;
- require the current governance state to be updated before merge.

The governor may not:

- invent product priorities without owner approval;
- silently rewrite an approved work package;
- waive security, privacy, provenance, or human gates without a recorded decision;
- certify its own implementation as the only reviewer;
- treat target architecture as current implementation.

## Canonical governance state

The current frame is stored in:

`governance/governor-state.json`

It is the machine-readable source of truth for:

- current project phase;
- current promoted baseline;
- authorized work;
- held and prohibited work;
- active architecture risks;
- active exceptions;
- next mandatory gate;
- last governor review.

A pull request that changes the effective project frame must update this state or explicitly prove that no state change is required.

## Mandatory governor checkpoints

### Before a work package is approved

The governor verifies:

- exact base commit;
- bounded responsibility;
- allowed and forbidden paths;
- data and contract ownership;
- invariants and non-goals;
- independent QA;
- rollback;
- compatibility with active work packages;
- evidence required to close the package.

### Before a high-risk pull request is merged

The governor verifies:

- scope compliance;
- architecture dependency rules;
- contract and migration compatibility;
- source-of-truth discipline;
- adverse tests;
- provenance;
- required specialist reviews;
- absence of unrecorded exceptions.

### Before an RC is promoted

The governor verifies:

- exact source and artifact identities;
- tested artifact equals proposed artifact;
- automation and human gates;
- known issues and residual risks;
- rollback and recovery;
- roadmap and governance-state consistency.

### At each architecture phase transition

The governor verifies that the current phase exit gate is proven before authorizing the next phase.

## Decision classes

| Class | Example | Governor action |
|---|---|---|
| Local reversible | isolated test or bounded UI fix | verify scope and regression evidence |
| Cross-cutting | shared contract, identifier, repository abstraction | require architecture review and usually an ADR |
| Data-bearing | persistence, migration, progress, synchronization | require adverse QA, rollback, and compatibility proof |
| Security/privacy | identity, tenancy, permissions, export, deletion | require independent security review and negative tests |
| Release-critical | build, workflow, manifest, provenance | require independent QA and source-to-artifact proof |
| Strategic | backend topology, commerce, marketplace, institutions | require owner arbitration and evidence-gated roadmap decision |

## Exception policy

An exception must be explicit, bounded, owned, testable, and expiring. It must state:

- violated rule;
- reason normal architecture is insufficient;
- affected files and modules;
- risk;
- owner;
- expiry or removal gate;
- tests preventing expansion;
- rollback.

Permanent undocumented exceptions are prohibited.

## Cadence

The governor runs:

- on every high or critical-risk work package;
- on every contract, migration, architecture, security, or release change;
- on every release-candidate promotion;
- after any serious regression or provenance failure;
- at least once per meaningful development cycle to review drift, debt, and roadmap consistency.

The cadence is event-driven first. A periodic review may supplement it, but a calendar review never replaces merge and release gates.

## Governor output

Every governor review produces a concise decision record:

```text
Baseline reviewed
Scope reviewed
Evidence
Claims
Missing proof
Constitution violations
Exceptions
Required actions
Decision: GO / GO WITH CONDITIONS / HOLD / NO GO
Next gate
```

## Current rule

RC718 is the frozen promoted legacy standalone generation. It remains available for historical access and bounded maintenance, but it is not an in-place migration base for the successor.

`ARC-WP-021` selected trajectory **C — clean break**. The governor must therefore keep the following on hold unless a new accountable-owner decision explicitly reopens them:

- RC718 compatibility resolver or identity overlay;
- dual read or dual write between legacy and successor keys;
- automatic migration of RC718 libraries, custom labels or learner state;
- automatic interpretation of RC718 packages by the successor;
- new-generation Player implementation before `ARC-WP-022` is accepted;
- backend, accounts, cloud synchronization and remote catalog;
- commerce, institutions, tenancy and marketplace.

The next mandatory gate is `ARC-WP-022`: design and authorization of the minimum viable clean-generation foundation, including a new major contract, native canonical identity, isolated browser storage, regenerated golden kits, exact file ownership, contradictory QA and release provenance.

Repository state, accepted ADRs and exact work-package evidence override historical roadmaps or handovers when they conflict.
