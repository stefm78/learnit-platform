# GOV-REVIEW-0019 — Stage D controlled pilot authorization

## Decision

**GO_WITH_CONDITIONS** for `ARC-WP-019`.

## Why this pilot

Stage B and Stage C are accepted. The repository may now run the first controlled multi-agent implementation pilot, but not broad parallel development.

The selected task is deliberately operational rather than product-facing: add a deterministic report that verifies whether every changed path belongs to exactly one declared role scope. This directly tests the Stage D operating model before it is trusted for higher-risk architecture work.

## Linus challenge

Parallel agents are not useful merely because their prompts have different job titles. They are useful only when ownership is explicit, overlaps are rejected mechanically, failures are observable, and the exact tested result is preserved through integration.

The pilot therefore adds no framework, no general orchestration layer and no runtime abstraction. It adds one small tool, one adversarial contract and two exact integration registrations.

## Disjoint ownership

- Developer: `apps/player/dev/role_scope_report.py`.
- Contradictory QA: `apps/player/tests/contract_role_scope.py`.
- Integrator: `apps/player/dev/checks_registry.json`, `apps/player/dev/evidence_coverage.json`, and durable evidence after the tested result.
- Governor: work package, state and decisions only.

No role may edit another role's path.

## Required behavior

The report must:

- normalize repository-relative POSIX paths;
- reject absolute paths, empty paths and parent traversal;
- match exact paths and glob patterns deterministically;
- report unowned and multiply-owned changed paths;
- reject duplicate patterns and malformed required role scopes;
- sort all report structures canonically;
- exit non-zero for invalid ownership;
- avoid network, command execution and implicit repository writes.

## Gates

1. Governance-only authorization PR passes Repository governance and PR scope.
2. Fresh agent branch is created from exact post-merge `main`.
3. Remote Agent `player-fast` produces the exact result.
4. Permanent Player CI, PR scope and repository governance pass on that exact result.
5. Contradictory QA and integrator reviews are recorded independently.
6. A separate governor acceptance decides whether the pilot passed.

## Conditions

- The accepted first storage seam is immutable during the pilot.
- Exactly two Player files may be added; the working-file budget must remain at or below 150.
- No held platform domain is entered.
- No Stage D expansion follows automatically from implementation merge.

## Rollback

Remove the two pilot files and restore the two integration metadata files through one reviewed revert. Product behavior and learner data are unaffected.
