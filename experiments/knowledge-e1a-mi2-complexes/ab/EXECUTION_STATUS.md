# E1A A/B execution status

## Frozen inputs

- Learner brief: `learner-brief.json`, 40 minutes, exact teaching scope 1.2.3.2 + 1.2.4.
- Route A candidate digest: `sha256:0d03102d9bcb880f8114c1992ab512d2ecb28b6227d0a60867645013aaabfc83`.
- Route B candidate digest: `sha256:cb38f6773437f39b6b9287149d4e8da76af6938467fe5a60dc39a8f7a29dcaf7`.
- Each candidate contains 2 objectives, 10 activities, exactly 40 authored minutes, and fresh identities.

## Author-side deterministic construction checks

The candidates were constructed using the current repository schema/Atlas algorithms as inspected from `main` at `1e71271436fd4b7dd7d895cfec827833187630fe`: five-class objective order, two independence claims per objective, Atlas stimulus/claim hashing, and canonical revision-digest algorithm. Local reconstruction checks pass for both candidates: activity order, claim binding, revision digests, duration equality, mixed QCM/fill validation representation, and transfer difficulty.

This is **not** recorded as execution of the repository canonical CLI. The current execution surface has GitHub repository access but no executable checkout/network path for running the repository Python authorities against the branch. Therefore canonical validator/M3.1/Factory claims remain unproven rather than inferred from the local equivalent checks.

## Semantic source audit

The authored content is bounded to the supplied PDF evidence for complex square roots, Proposition 1.52, Theorem 1.53, general n-th roots, Remark 1.55 and exercises 1.5/1.7/1.8. No claim of independent semantic review is made: the same top-level execution authored the candidates, so it cannot truthfully satisfy `authorScratchpadSeen=false` and `authorActiveContextReused=false` for a Factory semantic reviewer.

`INDEPENDENT_REVIEW_UNAVAILABLE`

## A/B observation so far

Both routes can express the same bounded learner objective without schema or Player changes. Route B has a concrete provenance/scope advantage outside the final kit because its source map and knowledge bundle distinguish target concepts from consultable prerequisites and expose typed dependencies for impact analysis. Route A remains materially simpler for a one-off kit. The final learner-kit payloads are similar in size and pedagogical structure; the Knowledge route does not earn a PASS merely by creating more artifacts.

## Audit verdict

`HOLD_E1A_ARCHITECTURE_NEEDS_REWORK`

The previous gap has been narrowed from “no A/B candidates” to two frozen candidate artifacts plus a frozen fair brief. Promotion to E1B is still forbidden until both exact candidates are run through the unchanged canonical validators/M3.1 and each exact source+brief+kit tuple receives a genuinely independent semantic review followed by the unchanged Factory Gate. A clean reviewer execution is a real causal requirement, not paperwork, and must not be self-certified.
