# E1A A/B execution status

## Frozen inputs

- Learner brief: `learner-brief.json`, 40 minutes, exact teaching scope 1.2.3.2 + 1.2.4.
- Route A candidate digest: `sha256:0d03102d9bcb880f8114c1992ab512d2ecb28b6227d0a60867645013aaabfc83`; Git blob `7a6a7299d2a77cde3956d2576e5de868a36da984`.
- Route B candidate digest: `sha256:cb38f6773437f39b6b9287149d4e8da76af6938467fe5a60dc39a8f7a29dcaf7`; Git blob `ead95f56d5fb37bfbe73edbe370426d03418b458`.
- Learner brief Git blob: `f8affc7dcac77430e8f0794a63aa276d8ed408dc`.
- Source PDF SHA-256: `a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`; repository retention remains forbidden.
- Each candidate contains 2 objectives, 10 activities, exactly 40 authored minutes, and fresh identities.

## Canonical deterministic qualification — PASS

The prior author-side reconstructed checks have now been replaced by real repository-authority execution for the deterministic layer.

Qualification was executed by GitHub Actions on draft PR `#377`:

- workflow: `E1A Canonical A-B Qualification`;
- run: `34768852674`;
- job: `103754617726`;
- exact qualified HEAD: `6f05ac1677b070c60488dc08616d855eddaf2996`;
- exact baseline: `1e71271436fd4b7dd7d895cfec827833187630fe`;
- uploaded artifact: `10321675054`;
- artifact digest: `sha256:10cd159b9e479ef116e4369638d9ecf7e6986fdd9f7056c7b4ddbbf3f761d45d`.

The workflow proved that the frozen A/B/brief blobs match their declared identities and that the canonical authorities are unchanged from the frozen baseline before executing them.

Results:

- canonical `authoring/v2/validate_kit.py` on A+B: PASS, `ok=true`, no cross-file errors;
- Route A generic validation: 0 errors, 0 warnings;
- Route B generic validation: 0 errors and one non-blocking short-explanation warning at `$.courses[0].activities[5].explanation`;
- canonical `authoring/v2/atlas/validate_atlas_content.py::validate_packages` on A+B: PASS;
- Route A canonical M3.1: `canonicalValid=true`, `EXCELLENT_BY_PROFILE`, 0 blocking / 0 warning / 0 advice;
- Route B canonical M3.1: `canonicalValid=true`, `EXCELLENT_BY_PROFILE`, 0 blocking / 0 warning / 0 advice.

Deterministic result: `PASS_DETERMINISTIC_CANONICAL_QUALIFICATION`.

The Route B generic warning is retained rather than repaired because the candidates are frozen for this comparison. It does not change the M3.1 quality band and is not hidden as part of the A/B evidence.

Persisted evidence lives under `ab/canonical-qualification/`; the full `validate-kit.json` is retained in the bound GitHub Actions artifact referenced by `ab/canonical-qualification/CI_RUN.md`.

## Factory-context boundary

The unchanged Factory context requires the exact source PDF bytes + frozen learner brief + exact candidate. The source PDF is intentionally absent from the repository and was not available inside the GitHub Actions runner.

`FACTORY_CONTEXT_SOURCE_BYTES_UNAVAILABLE_IN_CI`

No manifest, extracted text, hash string or reconstructed PDF was substituted for the source bytes. Therefore no Factory context and no Factory Gate PASS are claimed from this CI run.

## Independent semantic review boundary

The current author execution has seen the authoring scratchpad and both candidates. It is therefore ineligible to self-certify either route under `SKILL_ATLAS_KIT_REVIEW_V1.md`.

`INDEPENDENT_REVIEW_UNAVAILABLE`

No `PASS_SEMANTIC_REVIEW_V1` is claimed.

## A/B observation after canonical deterministic qualification

The learner-facing quality result is tied at the deterministic layer: both routes are canonically valid and both are `EXCELLENT_BY_PROFILE`. Route B therefore shows no M3.1 degradation. Route B still carries the durable source-map / target-vs-prerequisite / typed-dependency advantages outside the final kit, while Route A remains materially simpler for a one-off kit. The one generic warning on Route B is evidence against pretending the routes are byte-for-byte or diagnostic-for-diagnostic identical, but it is non-blocking and outside the M3.1 diagnostic result.

## Audit verdict

`HOLD_E1A_ARCHITECTURE_NEEDS_REWORK`

The deterministic proof gap is closed. Promotion to E1B remains forbidden until each exact source+brief+kit tuple receives a genuinely independent semantic review and then the unchanged Factory Gate returns genuine `PASS_AI_KIT_FACTORY_V1` for both routes. The next work is no longer kit construction or deterministic validation; it is exact source-bound independent qualification.
