# Rollback proof — Stage D role-scope pilot

## Trigger

Rollback is required if the role-scope report is shown to misclassify repository paths, create unsafe implicit writes or interfere with the existing Player validation chain.

## Operation

Revert merge commit `ae6b82d90b72f0287462c7d34708d0330d5ce35b` through a reviewed pull request.

The revert must:

1. remove `apps/player/dev/role_scope_report.py`;
2. remove `apps/player/tests/contract_role_scope.py`;
3. restore `apps/player/dev/checks_registry.json`;
4. restore `apps/player/dev/evidence_coverage.json`.

## Data and product impact

None.

- No Player runtime source changed.
- No generated or promoted product artifact changed.
- No storage key, payload, database or learner state changed.
- No identifier, remote API or platform service changed.
- No migration, backfill or external compensation is required.

## Verification after rollback

- run Remote Agent `player-fast` or the currently authorized replacement profile;
- require permanent Player CI, PR scope and repository governance;
- verify the mandatory registry and evidence map return to their prior exact state;
- verify the Player working-file count returns from 150 to 148;
- verify the RC718 artifact identity remains unchanged.

## Recovery objective

The complete pilot can be removed by one revert without changing product behavior or learner data.
