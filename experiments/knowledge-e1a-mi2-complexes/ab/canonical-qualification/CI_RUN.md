# E1A canonical A/B qualification — CI evidence

## Qualification identity

- Pull request: `#377` (`E1A: canonical A/B qualification only`), draft, do not merge.
- Workflow: `E1A Canonical A-B Qualification`.
- Workflow run: `34768852674`.
- Job: `103754617726` (`E1A frozen A-B canonical qualification`).
- Qualified head: `6f05ac1677b070c60488dc08616d855eddaf2996`.
- Frozen baseline: `1e71271436fd4b7dd7d895cfec827833187630fe`.
- Result: `PASS_DETERMINISTIC_CANONICAL_QUALIFICATION`.
- GitHub Actions artifact id: `10321675054`.
- Artifact name: `e1a-canonical-ab-6f05ac1677b070c60488dc08616d855eddaf2996`.
- Artifact digest: `sha256:10cd159b9e479ef116e4369638d9ecf7e6986fdd9f7056c7b4ddbbf3f761d45d`.

## Canonical results

- `authoring/v2/validate_kit.py`: PASS on the frozen A/B pair; `ok=true`; no cross-file errors.
- Route A generic validator: 0 errors, 0 warnings.
- Route B generic validator: 0 errors, 1 non-blocking warning: `$.courses[0].activities[5].explanation: explanation is unusually short; value="Pour n=3, U₃={e^{i2kπ/3}:k=0,1,2}."`.
- `authoring/v2/atlas/validate_atlas_content.py::validate_packages`: PASS on the frozen A/B pair.
- Route A M3.1: `canonicalValid=true`, `EXCELLENT_BY_PROFILE`, 0 blocking / 0 warning / 0 advice.
- Route B M3.1: `canonicalValid=true`, `EXCELLENT_BY_PROFILE`, 0 blocking / 0 warning / 0 advice.

The Route B generic warning is retained as evidence and is not repaired in this frozen run. It is not a canonical M3.1 degradation and did not block deterministic qualification.

## Frozen input binding

- Route A Git blob: `7a6a7299d2a77cde3956d2576e5de868a36da984`.
- Route B Git blob: `ead95f56d5fb37bfbe73edbe370426d03418b458`.
- Learner brief Git blob: `f8affc7dcac77430e8f0794a63aa276d8ed408dc`.
- Source PDF SHA-256: `a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`.

## Evidence retention

This directory persists the compact qualification manifest, both canonical M3.1 reports and the Atlas validation result. The complete `validate-kit.json` remains bound to workflow run `34768852674` in artifact `10321675054`; the artifact upload succeeded in the same job. The manifest records the exact authority hashes used.

## Remaining qualification boundaries

- `FACTORY_CONTEXT_SOURCE_BYTES_UNAVAILABLE_IN_CI`
- `INDEPENDENT_REVIEW_UNAVAILABLE`

No `PASS_SEMANTIC_REVIEW_V1` and no `PASS_AI_KIT_FACTORY_V1` are claimed by this run.
