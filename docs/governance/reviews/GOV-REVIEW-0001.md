# GOV-REVIEW-0001 — Standing governor bootstrap

## Review identity

- Date: 2026-07-13
- Repository: `stefm78/learnit-platform`
- Base commit: `4b993be6d00b5e4a2e9461e270ae5ef3fa40b97c`
- Work package: `GOV-WP-001`
- Operational governor: Architecture & Repository Governor bootstrap
- Accountable owner: `stefm78`

## Scope reconstructed

The repository already contained the architecture foundation, work-package contract, governance validator, and the blocked standalone baseline gate. It did not contain a permanent authority, a canonical current-state record, decision rights, or a mandatory governor checkpoint.

## Evidence

- private repository foundation exists on `main`;
- governance CI exists and previously passed;
- `ARC-WP-000` is present and intentionally blocked;
- architecture target and current implementation are explicitly separated.

## Claims and missing proof

- branch protection and mandatory code-owner review are not yet independently evidenced;
- active standalone source remains outside the repository;
- changed-file scope enforcement is specified but not implemented;
- no platform implementation is yet available for architecture-boundary testing;
- no independent reviewer identity exists yet beyond the single accountable repository owner.

## Counterexamples considered

- an AI agent starts backend work because the target architecture mentions a backend;
- a contract change is merged without updating the current phase or risk register;
- the same agent implements and self-certifies a high-risk migration;
- a temporary exception becomes permanent because it lacks an owner or removal gate;
- a future chat treats old architecture prose as proof of current implementation.

## Decision

**GO WITH CONDITIONS**

Create a permanent Architecture & Repository Governor with:

- repository owner as accountable authority;
- AI or human operational governor per review;
- canonical `governance/governor-state.json`;
- explicit decision rights;
- mandatory triggers for high-risk, cross-cutting, security, data, contract, and release changes;
- independent review for high and critical work;
- event-driven review cadence;
- explicit exception policy.

## Bootstrap exception

`EXC-GOV-BOOTSTRAP-001` permits the initial governor charter and validation tooling to be merged without a second reviewer identity because:

- the repository currently has one accountable owner;
- the change contains no application or learner data code;
- it is fully reversible;
- the exception must be removed before the first high or critical application, migration, identity, synchronization, security, entitlement, or release-provenance change.

## Conditions

1. Governor state must be validated by CI.
2. The governor must not become the sole certifier of work it authored after the bootstrap exception expires.
3. `ARC-WP-000` remains the next mandatory application gate.
4. Backend, sync, commerce, and marketplace work remain held.
5. Branch protection and scope-check enforcement remain open governance risks until proven.
6. The bootstrap exception remains visible until an independent reviewer mechanism exists.

## Next gate

Merge `GOV-WP-001`, then keep the governor active on every architecture-sensitive pull request and every release-candidate promotion.
