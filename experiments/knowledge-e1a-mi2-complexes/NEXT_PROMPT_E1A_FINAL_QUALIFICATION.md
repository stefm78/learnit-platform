# E1A — Final qualification execution prompt

## Mission
Close the remaining E1A proof gap without redesigning either candidate. Qualify the two already-authored A/B kits with the unchanged canonical Learn-it authorities, produce reproducible evidence, and stop exactly at any boundary that cannot honestly be crossed in the current execution environment.

## Frozen experiment identity
Repository: `stefm78/learnit-platform`
Branch: `experiment/e1a-knowledge-architecture-mi2-complexes`
Baseline main commit: `1e71271436fd4b7dd7d895cfec827833187630fe`

Frozen inputs:
- Route A: `experiments/knowledge-e1a-mi2-complexes/ab/candidate-route-a.json`
  - Git blob SHA-1: `7a6a7299d2a77cde3956d2576e5de868a36da984`
  - packageRevisionDigest: `sha256:0d03102d9bcb880f8114c1992ab512d2ecb28b6227d0a60867645013aaabfc83`
- Route B: `experiments/knowledge-e1a-mi2-complexes/ab/candidate-route-b.json`
  - Git blob SHA-1: `ead95f56d5fb37bfbe73edbe370426d03418b458`
  - packageRevisionDigest: `sha256:cb38f6773437f39b6b9287149d4e8da76af6938467fe5a60dc39a8f7a29dcaf7`
- Learner brief: `experiments/knowledge-e1a-mi2-complexes/ab/learner-brief.json`
  - Git blob SHA-1: `f8affc7dcac77430e8f0794a63aa276d8ed408dc`
- Semantic source PDF SHA-256: `a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`

Any drift in A, B or learner brief invalidates this qualification. Do not repair or tune a candidate during this run.

## Immutable authorities
Do not modify or replace:
- `contracts/learnit-kit-v2.schema.json`
- `authoring/v2/validate_kit.py`
- `authoring/v2/atlas/validate_atlas_content.py`
- `authoring/v2/atlas/pedagogical_quality.py`
- `authoring/factory/factory_gate.py`
- `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V2.md`
- `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md`

A local reimplementation, copied algorithm, hand-computed score or inferred result is not canonical execution evidence.

## Phase 1 — Canonical deterministic qualification
Create only the minimum experimental CI harness needed to run the repository authorities unchanged against the exact frozen candidates.

For the exact A/B files:
1. verify the frozen Git blob identities before validation;
2. run `authoring/v2/validate_kit.py` on A and B together so cross-file identity checks also execute;
3. invoke the canonical `validate_packages()` function from `authoring/v2/atlas/validate_atlas_content.py` on A and B without modifying that module;
4. run `authoring/v2/atlas/pedagogical_quality.py --json` separately on A and B;
5. require `canonicalValid=true` and quality band in `STRONG | EXCELLENT_BY_PROFILE` for both;
6. bind evidence to exact HEAD, baseline, frozen input blobs, package revision digests, and SHA-256 of the canonical authority files used;
7. upload the exact evidence as a GitHub Actions artifact.

The harness must be read-only with respect to product/runtime state and must not change production publication state.

## Phase 2 — Factory-context boundary
The Factory Gate context must be generated from the exact source PDF bytes + frozen learner brief + exact candidate. The source PDF is intentionally not retained in Git.

If the exact PDF bytes are not available inside the canonical execution environment, record `FACTORY_CONTEXT_SOURCE_BYTES_UNAVAILABLE_IN_CI`. Do not substitute a manifest, extracted text, source hash string, reconstructed PDF or repository kit for the PDF bytes.

## Phase 3 — Independent semantic review boundary
A reviewer may receive only source PDF, learner brief, exact candidate, exact Factory context and canonical public authorities. The reviewer must not receive the author scratchpad or active author context.

The current author context is not eligible to self-certify either candidate. If no clean reviewer execution is available, record `INDEPENDENT_REVIEW_UNAVAILABLE`. Never fabricate `PASS_SEMANTIC_REVIEW_V1`.

## Phase 4 — Factory Gate
Run `factory_gate.py gate` only after an exact Factory context and a genuinely independent semantic review exist for that route. A genuine `PASS_AI_KIT_FACTORY_V1` is required for each route before E1A can PASS.

## Decision rule
Return `PASS_E1A_READY_FOR_E1B_SCALE_TEST` only if:
- both frozen candidates pass canonical deterministic qualification;
- both receive genuine independent `PASS_SEMANTIC_REVIEW_V1` bound to their exact Factory contexts;
- both receive genuine `PASS_AI_KIT_FACTORY_V1`;
- Route B is non-degraded versus Route A;
- Route B demonstrates at least one material reusable advantage in scope control, provenance/reuse or change-impact traceability that is not merely shifted complexity.

Return `HOLD_E1A_ARCHITECTURE_NEEDS_REWORK` when deterministic proof advances but one of the exact source/reviewer/Factory boundaries remains unavailable.

Return `FAIL_E1A_KNOWLEDGE_ARCHITECTURE_NOT_JUSTIFIED` only from completed comparative evidence showing degradation or unjustified complexity, not from missing infrastructure.

## Execution discipline
- Reconstruct current repository state before acting.
- Revalidate current state/CAS immediately before each mutation.
- Keep `main` untouched; a draft PR is permitted solely to trigger experimental read-only CI and must not be merged.
- Prefer an experimental workflow over modifying canonical validators.
- Do not commit the source PDF.
- Do not redesign A or B.
- Do not weaken any gate to obtain PASS.
- Distinguish canonical execution from model inference in every report.

## Required outputs
Persist or retain pointers to:
- this frozen prompt;
- the minimal experimental CI workflow;
- CI run identity and exact commit HEAD;
- deterministic validation JSON;
- Atlas validation result;
- M3.1 reports for A and B;
- deterministic qualification manifest;
- exact blockers for Factory context / independent review if still present;
- updated E1A execution status and report with exactly one current verdict.