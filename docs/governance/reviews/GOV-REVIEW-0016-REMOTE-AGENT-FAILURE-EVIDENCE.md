# GOV-REVIEW-0016 — Remote Agent failure evidence

## Decision

**GO_WITH_CONDITIONS** for `GOV-WP-016`.

## Evidence

- The fresh ARC-WP-014 run passed its envelope, patch application and repository-governance steps but failed the fixed `player-full` profile without producing a tested-result envelope.
- The current workflow uploads `.agent-runtime/tests.json` and Player reports only after a successful validation profile; the upload step is skipped when testing fails.
- Disposable diagnostics established partial facts—24 browser suites passed separately and the source-tree guard passed 11/11—but could not replace one complete exact-result run.
- The absence of durable failure evidence caused repeated diagnostic branches and increased repository noise without advancing the gate.

## Linus challenge

A quality gate that says only “failed” while discarding its own structured failure record is not a strong gate. It converts deterministic engineering into blind binary search. The correction must improve observability, not relax validation.

## Authorized correction

A separate pull request may add one failure-only artifact upload to `.github/workflows/remote-agent-worktree.yml`:

- condition: an earlier step has failed;
- paths restricted to `.agent-runtime/**` and `apps/player/reports/**`;
- artifact name clearly distinct from `remote-agent-result-*`;
- `if-no-files-found: warn`;
- short retention;
- no permission change and no modification of the successful result path.

## Conditions

1. No existing step may be removed, bypassed or marked `continue-on-error`.
2. No repository source, tool, governance state, architecture or product file may change in the implementation PR.
3. A disposable deliberately failing Remote Agent run must prove that the artifact is produced and contains the failed command evidence.
4. The artifact must be inspected for secrets and must not be treated as a tested result.
5. After acceptance, ARC-WP-014 must be recreated from the then-current exact `main`; no old first-seam branch may be reused.

## Current gates

- Stage B / ARC-WP-010: accepted.
- Stage C: **HOLD**, authorized but not complete.
- Stage D: blocked.

## Rollback

Revert the workflow-only correction. Product source and learner data are unaffected.
