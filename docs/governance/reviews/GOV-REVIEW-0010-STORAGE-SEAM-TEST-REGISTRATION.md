# GOV-REVIEW-0010 — Focused storage-seam test registration

## Decision

**GO_WITH_CONDITIONS**

The evidence plan is corrected before implementation. Adversarial QA may add the focused contract and one mandatory registry entry so the ordinary `player-full` path executes it. Developer scope is unchanged.

## Evidence

- `apps/player/dev/run_all_checks.py` loads the canonical checks registry and executes the listed mandatory and browser scripts; it does not auto-discover new test files.
- `apps/player/dev/checks_registry.json` does not yet list `tests/contract_storage_boundary.py`.
- Without registration, `player-full` could be green while the new boundary contract remained unexecuted.

## Accepted correction

QA receives exactly one additional write path: `apps/player/dev/checks_registry.json`. The only permitted registry diff is one new mandatory entry for `tests/contract_storage_boundary.py`.

The following remain frozen:

- developer implementation paths;
- test runner and registry schema;
- RC and release policy;
- build command and reports;
- every existing mandatory check and its order;
- every browser check and its order;
- all player behavior and storage semantics.

## Adversarial conditions

HOLD if the result removes, replaces or reorders an existing check; changes the runner or release configuration; grants the developer access to QA paths; or uses registry editing to suppress evidence.

## Conclusion

The correction closes an evidence gap rather than broadening the seam. Stage C remains authorized but incomplete. Stage D remains blocked.
