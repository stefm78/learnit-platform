# GOV-REVIEW-0005 — Permanent quality gates

## Decision

```text
QA-WP-010  : GO
GOV-WP-010 : GO_WITH_CONDITIONS
```

## Reviewed implementation

- RC718 evidence repair: PR #28, merged as `3f1a67935ce782dcbf700e642f4ff8dfa41d3438`.
- PR scope gate: PR #30, merged as `26750bff307a6f756bd5b63d70da15b95397071e`.
- Permanent Player CI: PR #29, merged as `da74995f80b8eba6ef75ab5603fc101fcc9fde72`.

## QA-WP-010 evidence

The exact reviewed head was `cfc9e08e733d292820ca31b05dacfb7c6537b250`.

- Repository governance run `29322037469`: PASS.
- PR scope run `29322037571`: PASS.
- Player CI run `29322037422`: PASS.
- Clean build and mandatory contract/mutation checks: PASS.
- Browser registry: 24 declared and 24 discovered suites.
- Browser execution: 24 independent bounded jobs, all PASS, `fail-fast` disabled.
- Artifact size: 829,005 bytes.
- Artifact SHA-256: `e6ca9523bfd8fd59a5bf6abbfb1ee1c2f0de46c429c44749354c881eb31ff3eb`.
- Artifact identity: byte-identical to the RC718 downloadable candidate.
- Source manifest freshness: PASS.
- Build-before-test and artifact-before/after-suite identity: PASS.
- Adversarial CI-guard checks for omitted suites, artifact mutation, and source-after-build mutation: PASS.

The gate removes `RISK-QA-001`: the repository now runs a permanent complete browser matrix for player-sensitive pull requests.

## GOV-WP-010 evidence

- Positive implementation PR #30: `PR scope / gate` PASS, run `29321668977`.
- Negative PR #31: missing work package correctly rejected, run `29321879773`.
- Negative PR #32: path outside declared scope correctly rejected, run `29321914868`.
- Both negative PRs were closed without merge.

The source-level scope enforcement closes `RISK-GOV-003` for pull requests targeting `main`.

## Residual condition

`RISK-GOV-002` remains open. The repository contains and executes the required checks, but the current connector cannot configure or independently attest GitHub administrative rulesets. The following must still be applied and evidenced:

- pull request required for `main`;
- direct pushes forbidden;
- `Repository governance` required;
- `PR scope / gate` required;
- `Player CI / gate` required for player-sensitive changes;
- `Remote agent worktree / tested result` required for agent results;
- bypass restricted and auditable.

Until that evidence exists, the checks are technically operational but not proven unbypassable by repository policy.

## Product status

RC715 remains the promoted standalone baseline. RC718 remains the active development candidate. QA-WP-010 acceptance does not replace the required RC719 human close/reopen validation for plan naming and persistence.

## Next authorized step

A work package may now be prepared for the first reversible architecture seam: encapsulate one existing storage boundary behind a narrow interface without changing storage technology, data shape, UI, identifiers, or behavior.

Implementation of that seam remains subject to its own governor review and exact scope.
