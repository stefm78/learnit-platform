# R1 semantic review status

Status: `PENDING_CLEAN_CONTEXT`

## Governance pre-clean-review closure

PR #378 requires exactly one canonical work package for its cumulative `base...head` diff. The governing package is `EXP-WP-001`, created specifically for the bounded E1A/E1A-R1 experimental qualification and its predeclared clean-review closure evidence. It does not authorize production promotion, merge, E1B, or product/runtime changes.

This Job A execution performs governance and mechanical qualification only. It does **not** perform the independent semantic review.

The learner candidate remains frozen at `experiments/knowledge-e1a-mi2-complexes/r1/candidate-b-r1.json` with `packageRevisionDigest` `sha256:47724cff565e776cb85dc7a83e957510e89826dd6011a2a1474898168beb8fb3`. The source identity remains `sha256:a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`.

This file is deliberately **not** a semantic review and is not Factory-consumable evidence. The active execution has authored/inspected the repair and has seen the desired R1 acceptance criteria; therefore it cannot satisfy the required independence boundary.

Clean reviewer input must contain only:
- exact PDF bytes, SHA-256 `a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`;
- frozen learner brief, blob `f8affc7dcac77430e8f0794a63aa276d8ed408dc`;
- `candidate-b-r1.json`;
- canonical review contract `learnit.atlas.semantic_review.v1`;
- Factory context `sha256:de3b5e76eeea53b553650c570a1f0482c362d63d0b4342bfc2f516012742c27f`.

The clean reviewer must not receive this experiment's desired verdict, author reasoning, prior semantic reviews, coverage-loss diagnosis, comparison conclusions, PR discussion, prior-chat summaries, or any file whose purpose is to explain the expected semantic result before freezing the review.
