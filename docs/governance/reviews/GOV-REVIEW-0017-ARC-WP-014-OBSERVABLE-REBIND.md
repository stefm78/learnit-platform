# GOV-REVIEW-0017 — Observable ARC-WP-014 rebind

## Decision

**GO_WITH_CONDITIONS** for `ARC-WP-017`.

## Why a new execution is required

The previous ARC-WP-014 branch was correctly closed without merge. It failed `player-full`, produced no tested result, and was based on a `main` that has since changed through the accepted GOV-WP-016 Remote Agent observability repair. Reusing that branch would violate the exact-base invariant established by ARC-WP-016.

## Facts retained from disposable diagnostics

- The original focused contract contained a false positive: semantic mentions of IndexedDB were treated as direct API ownership. The corrected contract checks direct `indexedDB.open(...)` ownership.
- All 24 registered browser scripts passed when executed independently on the seam.
- The source-tree guard passed 11/11 on the seam.
- These are partial diagnostic facts only; none replaces a complete `player-full` result bound to one exact commit.

## Authorized execution

After this review is merged:

1. capture the resulting exact SHA of `main`;
2. create `agent/arc-wp-014-observable-first-storage-seam-result` directly from that SHA;
3. apply only the accepted ARC-WP-014 seven-file patch;
4. run `player-full` through Remote Agent Worktree;
5. inspect a GOV-WP-016 failure artifact if the run fails;
6. accept nothing unless the exact result commit passes Remote Agent attestation, permanent Player CI, PR scope and repository governance;
7. obtain separate contradictory QA, integrator and governor decisions.

## Linus challenge

No more blind diagnostics and no branch recycling. One exact base, one bounded patch, one complete result, one decision. If it fails, the structured failure artifact must identify the command and evidence. If it passes, the result must remain byte- and provenance-bound through merge.

## Gates

- ARC-WP-010 / Stage B: accepted.
- Stage C: authorized, **not accepted**.
- Stage D: blocked.

## Rollback

Close the fresh implementation PR without merge. No data migration or product rollback is required.
