# GOV-REVIEW-0023 — ARC-WP-021 clean-break generation decision

## Decision

**GO_WITH_CONDITIONS** for `ARC-WP-021` as an accountable product and architecture direction.

The decision is governance-only. New-generation implementation remains **HOLD** until the next bounded foundation work package is accepted.

## Reviewed baseline

- Repository: `stefm78/learnit-platform`
- Exact baseline: `0575385c5891e56506de6aaa0244297d766ea458`
- Legacy product: RC718
- Human gate: RC719 `PASS_WITH_RESERVATIONS`
- Existing identity design: `ADR-0001-STABLE-IDENTITY-MIGRATION.md`
- Player working-file count: 150

## Evidence

- RC718 is a promoted and reproducible standalone baseline.
- The current compatibility path would need to preserve and migrate library, session, progress, bilan, retention and durable snapshot structures keyed by legacy identifiers.
- No backend, account, synchronization, remote catalog, institutional or commerce deployment currently creates a continuity obligation.
- The Player is already at its working-file budget ceiling.
- The accountable owner explicitly selected trajectory C and stated that current value does not justify continuity cost.

## Claims accepted

- The clean-break path has lower implementation and long-term maintenance cost than resolver, overlay, dual-read and transactional migration.
- RC718 can remain the legacy access path without being mutated by the next generation.
- Canonical identity should be native to the new generation rather than overlaid on RC718 compatibility keys.
- Existing kits should be regenerated or deliberately converted offline, not supported through a permanent runtime compatibility layer.

## Assumptions

- RC718 local learner data has no contractual preservation requirement.
- Current users can accept a distinct new product generation with empty active state.
- Priority kits can be regenerated under a new contract.

These assumptions must be challenged before external distribution.

## Absence of evidence

There is no evidence of:

- a production user population requiring transparent upgrade;
- a contractual obligation to preserve learner histories;
- cross-device data requiring continuity;
- a business case that exceeds the cost and risk of migration.

## Adversarial review

The decision does not authorize careless deletion. It requires:

- immutable preservation of RC718 source, artifact and evidence;
- isolated new storage keys and database identity;
- no fallback reads from RC718 state;
- no automatic clearing of RC718 state;
- fail-closed rejection of legacy packages;
- an explicit release message describing the rupture;
- atomic contract, authoring, build, test and artifact provenance.

The following shortcuts are rejected:

- silently reusing RC718 storage keys for new semantics;
- treating legacy title slugs or activity IDs as canonical identity;
- adding a partial compatibility reader “temporarily” without its own accepted reversal of this decision;
- copying all RC718 implementation into the new generation without current justification;
- calling the new generation an RC718 upgrade.

## Conditions

1. RC718 remains immutable and retrievable.
2. This pull request changes no Player file, contract, data, build or artifact.
3. The clean-break decision retains the canonical identity taxonomy of ADR-0001 but supersedes its migration and compatibility sequence.
4. The next work package must define the minimum viable new contract, isolated storage namespace, regenerated golden kits, exact file plan and release gates.
5. No compatibility resolver, identity overlay, dual-key storage or learner-state migration may be introduced without a new accountable-owner decision.
6. The new generation must prove by negative test that it does not mutate RC718 browser storage.
7. Backend, accounts, synchronization, remote catalog, commerce, tenancy and marketplace remain held.

## Outcome

`ARC-WP-021` is accepted as the canonical trajectory decision.

The previous planned resolver gate is cancelled. The next mandatory gate is `ARC-WP-022`, a bounded design-and-authorization package for the minimum viable clean-generation foundation. No implementation is accepted by this review.
