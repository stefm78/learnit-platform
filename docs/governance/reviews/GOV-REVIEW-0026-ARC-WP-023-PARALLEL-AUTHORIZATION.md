# GOV-REVIEW-0026 — ARC-WP-023 parallel execution authorization

## Decision

**GO_WITH_CONDITIONS** for the exact subordinate work packages:

- `DEV-WP-031` — runtime and UI;
- `KIT-WP-001` — authoring and golden kits;
- `QA-WP-011` — contradictory fixtures and tests;
- `INT-WP-001` — later controlled integration.

The first three may start concurrently from the exact common base `d0186d7c0d65d44287c59534855ea90ffa3f8d06`. The integrator remains on HOLD until all three outputs have independent reviews.

## Evidence

- `ARC-WP-022` and the frozen `learnit.kit.v2` schema are merged at the common base.
- `FILE_PLAN_V1.json` defines 32 total working files: one frozen schema, 14 runtime files, five authoring files, seven QA/fixture files and five integration files.
- The four subordinate allowed-path lists reproduce the 31 unfrozen paths exactly.
- No allowed path appears in more than one subordinate package.
- Each implementation package blocks governance, architecture, work-package and RC718 Player paths.
- Runtime, authoring and QA packages share no writable integration surface.
- The integration package cannot modify role-owned runtime, authoring, fixture or test files.

## Claims accepted

- Three AI implementation agents can operate safely in parallel under the accepted Remote Agent Worktree transport because they share one immutable base and have disjoint write scopes.
- Contract freeze permits QA and authoring to work without waiting for runtime implementation details.
- Sequential integration is required because build order, source manifest, CI and release provenance are shared system concerns.
- Starting from the ARC-WP-022 merge commit is valid even though this later authorization record is merged to main, because the Remote Agent jobs can be authorized against an earlier immutable commit and carry no governance writes.

## Assumptions

- Remote Agent repository-profile execution is sufficient for role-local validation before integrated successor CI exists.
- All three branches can remain short-lived and be reviewed before integration.
- GitHub merge-base behavior will present only role-owned changes when branches created from the earlier exact base target a later `main`.

## Absence of evidence

There is not yet evidence that:

- any implementing agent has produced a result;
- the Python and JavaScript digest implementations agree;
- the two golden kits validate;
- the runtime can satisfy the QA tests;
- the 32-file budget is sufficient;
- an integrated deterministic artifact exists.

These are downstream execution and integration gates.

## Disjointness verdict

| Role | Paths | Parallel | Overlap |
|---|---:|---:|---:|
| DEV-WP-031 runtime | 14 | yes | 0 |
| KIT-WP-001 authoring | 5 | yes | 0 |
| QA-WP-011 QA/fixtures | 7 | yes | 0 |
| INT-WP-001 integration | 5 | no | 0 |

The union contains 31 paths. Adding the frozen schema produces the exact 32-file foundation plan.

## Conditions

1. Each implementing branch starts from `d0186d7c0d65d44287c59534855ea90ffa3f8d06`.
2. Each Remote Agent job declares only its work-package allowed paths and fixed budgets.
3. The frozen schema cannot be changed by an implementing branch.
4. No role may create a convenience file outside the plan.
5. An implementing role cannot certify its own output.
6. Critical or high review findings stop that role and block integration.
7. The integrator starts only after exact reviewed result commits exist for all three roles.
8. The integrator returns defects to the owning role rather than editing role-owned files.
9. No RC718 storage access, compatibility logic or held platform domain is permitted.
10. A separate governor acceptance is required before human testing.

## Operational note

The repository is now structurally ready for three parallel AI agents. This does not imply that the current chat connector can itself execute three autonomous agents. The approved branches and work packages can be consumed by the accepted Remote Agent workflow or another controlled independent-worktree mechanism.

## Next gate

`INT-WP-001` becomes the integration gate after independently reviewed results exist for the three parallel roles. Until then, the governor monitors overlap, contract mutation, unplanned files, failed validation and RC718 boundary violations.
