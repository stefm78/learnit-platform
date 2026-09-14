# E1A A/B execution status

## Frozen inputs

- Learner brief: `learner-brief.json`, 40 minutes, exact teaching scope 1.2.3.2 + 1.2.4.
- Route A candidate digest: `sha256:0d03102d9bcb880f8114c1992ab512d2ecb28b6227d0a60867645013aaabfc83`; Git blob `7a6a7299d2a77cde3956d2576e5de868a36da984`.
- Route B candidate digest: `sha256:cb38f6773437f39b6b9287149d4e8da76af6938467fe5a60dc39a8f7a29dcaf7`; Git blob `ead95f56d5fb37bfbe73edbe370426d03418b458`.
- Learner brief Git blob: `f8affc7dcac77430e8f0794a63aa276d8ed408dc`.
- Exact source PDF SHA-256: `a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`; repository retention remains forbidden.
- Each candidate contains 2 objectives, 10 activities, exactly 40 authored minutes, and fresh identities.

## Canonical deterministic qualification — PASS

Qualification was executed by the real repository authorities in GitHub Actions on draft PR `#377`.

- workflow: `E1A Canonical A-B Qualification`;
- run: `34768852674`;
- job: `103754617726`;
- exact qualified HEAD: `6f05ac1677b070c60488dc08616d855eddaf2996`;
- exact baseline: `1e71271436fd4b7dd7d895cfec827833187630fe`;
- uploaded artifact: `10321675054`;
- artifact digest: `sha256:10cd159b9e479ef116e4369638d9ecf7e6986fdd9f7056c7b4ddbbf3f761d45d`.

Results:

- canonical `authoring/v2/validate_kit.py`: PASS for A+B;
- canonical Atlas `validate_packages()`: PASS for A+B;
- Route A M3.1: `EXCELLENT_BY_PROFILE`, 0 blocking / 0 warning / 0 advice;
- Route B M3.1: `EXCELLENT_BY_PROFILE`, 0 blocking / 0 warning / 0 advice;
- Route B retains one generic-validator advisory warning on the short U3 explanation; the candidate was not repaired because the comparison is frozen.

Deterministic result remains:

`PASS_DETERMINISTIC_CANONICAL_QUALIFICATION`

## Exact Factory contexts — AVAILABLE

The exact PDF bytes were recovered and hash-verified. No source substitute was used.

Shared source:

- bytes: `210307`;
- SHA-256: `sha256:a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`;
- sourceSetDigest: `sha256:56518c66fab2fb2e7a8b60b675520265b935e9ed4d8db37f1b319d64dd9ec526`;
- briefSha256: `sha256:74e7b2b555f240f8f805c866c5d51bb7c22809caba809135afd46744b819292e`.

Route A Factory context:

- kitSha256: `sha256:c3bc513fbb3b003edfcdd06fe82aea886934bf4be71b80fe90525176a6a38b88`;
- contextDigest: `sha256:a6c99a600a0134dc6e4c658f864228ac344f78051ffa27e6121a59017192c390`.

Route B Factory context:

- kitSha256: `sha256:4ce65c0de6520aae74b29ba89da4e8ef00023fed0b499216b6c1c765791afaec`;
- contextDigest: `sha256:8d19e9fb88f25037ef584c7257b16e9bbd7906142a9da3d403252d220d1951d5`.

`FACTORY_CONTEXT_SOURCE_BYTES_UNAVAILABLE_IN_CI` is therefore closed for the interactive qualification path.

## Independent semantic reviews — RECEIVED, BOTH HOLD

### Route A

The independent reviewer reports `HOLD_SEMANTIC_REVIEW_V1` with three major findings:

1. no actual computation of the n distinct roots of a general nonzero complex number;
2. omission of Theorem 1.56 (sum of roots of unity is zero for n>=2);
3. the second-objective validation pair under-tests the declared n-th-root objective.

These substantive findings are supported by the source and the frozen Route A candidate.

However, the reviewer response is **not Factory-consumable as supplied**. It uses a non-canonical profile and non-canonical field names (`notes/support`, `findingId/kitPath/fixDirection/sourceEvidence`). Per `factory_gate.py`, it must not be author-normalized into canonical evidence.

Route A status:

`NOT_RUN_REVIEW_INPUT_NONCONFORMANT`

A clean-context reviewer resubmission using the exact `learnit.atlas.semantic_review.v1` shape is required for canonical gate evidence.

### Route B

The Route B reviewer response conforms to `learnit.atlas.semantic_review.v1` after transport unescaping only. Its target binding matches the exact Factory context and its independence declaration is `false/false`.

Semantic result:

`HOLD_SEMANTIC_REVIEW_V1`

Material findings:

- major `objectiveCoverage`: Theorem 1.56 is absent;
- minor `ambiguity`: the correct general n-th-root answer option omits the explicit `k=0,...,n-1` range, although the explanation restores it.

The canonical Factory Gate logic therefore cannot return PASS for Route B. With the already-proved M3.1 `EXCELLENT_BY_PROFILE` result, the semantic branch resolves to:

`HOLD_FACTORY_SEMANTIC_REVIEW`

No `PASS_AI_KIT_FACTORY_V1` is claimed.

## Root-cause audit — Source Map -> Knowledge coverage loss

The source PDF contains Theorem 1.56 and Example 1.57 at the end of the semantic 1.2.4 scope. `source/source-map.json` correctly lists both items under section 1.2.4 and explicitly records the page-21 running-header ambiguity.

The information is then lost before pedagogy:

- `knowledge/knowledge-bundle.json` includes `nth-roots`, `roots-of-unity`, and `regular-polygon-representation`, but no knowledge unit/property for the zero-sum theorem;
- `pedagogy/scope-ab.json` targets only the knowledge IDs exported by that bundle;
- the frozen Route B candidate consequently omits Theorem 1.56.

This is a concrete coverage-preservation failure in the Knowledge route, not a PDF extraction failure.

Route B still preserves more of the learner brief than Route A: it includes a validation for the general n-th-root formula of a nonzero complex number, whereas Route A validates only roots of unity and root count for `i`.

## Audit verdict

`HOLD_E1A_ARCHITECTURE_NEEDS_REWORK`

Both frozen routes remain semantic HOLD. Route B is materially stronger on general n-th roots but still loses a source item that the Source Map had correctly identified. Promotion to E1B remains forbidden.

The frozen candidates must not be repaired in place. The minimum next architecture experiment is a fresh repair iteration with new identities and an explicit Source Map -> Knowledge coverage-preservation invariant: every in-scope numbered source item must be represented in Knowledge or explicitly excluded with a reason. This should remain a lightweight ledger/claim mechanism, not a general-purpose knowledge platform.
