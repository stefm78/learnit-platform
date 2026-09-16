# E1A Route A — semantic-review schema correction request

Your semantic conclusions are not being challenged or repaired. Re-emit the review you independently produced, preserving its findings, severities, evidence and verdict, but conforming exactly to `SKILL_ATLAS_KIT_REVIEW_V1.md` and `learnit.atlas.semantic_review.v1`.

Required corrections only:

- `profile` must be `atlas.semantic-review.v1`.
- Every dimension must have exactly `status`, `summary`, `evidence`; rename the current `notes` field to `summary` without changing its meaning.
- Every evidence item must have exactly `sourceId`, `locator`, `basis`; rename the current `support` field to `basis` without changing its meaning.
- Every finding must have exactly `id`, `severity`, `dimension`, `path`, `problem`, `impact`, `fix`, `evidence`; map `findingId→id`, `kitPath→path`, `fixDirection→fix`, `sourceEvidence→evidence` without changing substance.
- Preserve the exact target digests and `independence=false/false` only if they remain truthful for your clean reviewer context.
- Preserve `HOLD_SEMANTIC_REVIEW_V1` unless your independent semantic judgment itself changes for a source-supported reason.

Return only the corrected JSON object. Do not inspect Route B and do not receive author scratchpad or active author context.
