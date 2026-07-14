# GOV-REVIEW-0018 — First-seam evidence-map scope

## Decision

**GO_WITH_CONDITIONS** for `ARC-WP-018`.

## Evidence

The exact observable execution based on `9f2a30f26d6a3e02f7d60d0f12dcc98ed26d5a8b` passed:

- Remote Agent envelope validation;
- patch application;
- repository governance;
- the Player build;
- all 24 registered browser suites;
- 58 of 58 evidence bindings.

The aggregate reported 34 of 35 mandatory checks. The only failed command was `tests/contract_evidence_coverage.py`. Its report identified one and only one unmapped active test: `tests/contract_storage_boundary.py`.

The failure was retained in `remote-agent-failure-29353545001`, digest `sha256:8bc7f8c7efca7917fe7ddb635d1de3110d2bab45a285fa48117b0e0e510d873`. This validates the GOV-WP-016 observability repair and removes ambiguity about the remaining gate.

## Assessment

This is not a Player defect, storage-seam defect or test failure. The focused contract was added to the mandatory registry but the canonical evidence coverage map was omitted from the authorized QA write scope. The repository-wide gate correctly rejected that omission.

The omission must not be repaired opportunistically on a failed implementation branch. The canonical work package must first assign ownership of the exact metadata file.

## Authorized amendment

Contradictory QA receives one additional exact write path:

`apps/player/dev/evidence_coverage.json`

The only authorized change in that file is to add:

`tests/contract_storage_boundary.py`

a single time to the existing `storage-resilience` surface. No existing mapping, surface, policy, schema or human-only statement may change.

## Conditions

1. The next implementation branch is recreated from exact current `main` immediately after this authorization is merged.
2. The accepted seven-file seam bytes remain unchanged; only the exact evidence-map addition is appended.
3. Developer, QA, integrator and governor scopes remain disjoint.
4. The complete `player-full` profile, permanent Player CI, PR scope and repository governance must pass on one exact result commit.
5. Stage C remains unaccepted until a separate governor decision is merged.
6. Stage D remains blocked.

## Linus challenge

A mandatory test that is absent from the evidence map is not fully integrated. The correct repair is one explicit owner, one exact metadata line, one fresh complete run—not another exception and not a weakened gate.

## Rollback

Close the fresh implementation pull request without merge, or revert its merge. No learner-data migration or remote compensation is required.
