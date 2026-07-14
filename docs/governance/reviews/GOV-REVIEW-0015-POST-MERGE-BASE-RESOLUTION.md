# GOV-REVIEW-0015 — Post-merge execution-base resolution

## Decision

**GO_WITH_CONDITIONS**

The earlier rebind exposed a self-reference defect: a governance commit cannot contain its own future merge SHA, so a pre-merge SHA cannot honestly be declared as the post-merge executable base.

## Corrected rule

- `baseline.baseCommit` is the immutable reviewed baseline before this correction.
- After this pull request is merged, read the exact current `main` SHA.
- Immediately create the fresh agent branch from that SHA.
- Put the same SHA in `job.json.baseCommit`.
- Require the pull-request base SHA to equal it.
- If `main` moves before branch creation, discard the capture and repeat from the new current `main`; do not broaden scope or reuse a branch.

This rule is machine-enforced by Remote Agent base ancestry/equality and strict PR-scope validation, while avoiding an impossible self-hash requirement.

## Preserved boundaries

The storage seam, seven changed files, role separation, fingerprints, full test profile, product identity, rollback and separate governor acceptance are unchanged. Prior failed and diagnostic branches remain non-evidence.

Stage C remains incomplete. Stage D remains blocked.
