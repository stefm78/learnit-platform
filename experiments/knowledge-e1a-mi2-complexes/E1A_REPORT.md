# E1A — Knowledge Architecture Falsification — MI2 Nombres Complexes

## Executive summary

E1A tests Source Map → Knowledge → Pedagogy against the current Direct AI Kit Factory route without changing `learnit.kit.v2` or the Player.

Observed value remains concrete for **scope control, prerequisite declaration, reuse, provenance and deterministic impact analysis**. The experiment continues to falsify “OKF everywhere”: the useful core is smaller than a general knowledge-management platform, and Direct AI Kit Factory remains the preferred fast path for isolated one-off work.

The A/B authoring and deterministic qualification gaps are now closed. One frozen learner brief plus two fresh 40-minute `learnit.kit.v2` candidates target the exact same sections 1.2.3.2 + 1.2.4. Route A is direct-source authored; Route B is knowledge-assisted. On the unchanged canonical deterministic authorities both are valid and both achieve `EXCELLENT_BY_PROFILE`.

E1A is **not yet a PASS** because the experiment still lacks genuinely independent, exact-source-bound semantic reviews and therefore cannot honestly run the final Factory Gate for either route.

## Scenario results

- A Scope selector: PASS at model level.
- B Reuse: PASS at model level; module/argument/exponential form are shared dependencies.
- C Same knowledge/different pedagogy: PASS at model level; knowledge identities remain unchanged.
- D Figures/equations: PASS with locator caveat; PDF-page + numbered item locators suffice, extracted glyph offsets do not.
- E Exercises: PASS; exercises are practice/assessment evidence, not concepts.
- F Direct vs Knowledge A/B: **PARTIAL / HOLD, materially advanced**. The two exact frozen candidates were executed in GitHub Actions against the unchanged canonical `learnit.kit.v2` validator, Atlas `validate_packages()` authority and M3.1 pedagogical-quality engine. Both pass; both are `canonicalValid=true`; both are `EXCELLENT_BY_PROFILE`. Route A has zero generic-validator warnings. Route B has one non-blocking generic warning for an unusually short explanation, retained without repair. Independent semantic review and final Factory Gate remain unproven.
- G Existing kit: product witness only; it is not semantic authority for the bounded 1.2 target.
- H Impact: PASS at model level; fixture change to `roots-of-unity` marks only dependent blueprints `REVIEW_REQUIRED`.
- I Fast path: PASS; Direct AI Kit Factory remains preferred for small one-off non-reused scopes.

## A/B artifacts and canonical evidence

- Original A/B prompt: `NEXT_PROMPT_E1A_AB_CANONICAL.md`.
- Final qualification prompt: `NEXT_PROMPT_E1A_FINAL_QUALIFICATION.md`.
- Frozen brief: `ab/learner-brief.json`.
- Route A: `ab/candidate-route-a.json`, package digest `sha256:0d03102d9bcb880f8114c1992ab512d2ecb28b6227d0a60867645013aaabfc83`.
- Route B: `ab/candidate-route-b.json`, package digest `sha256:cb38f6773437f39b6b9287149d4e8da76af6938467fe5a60dc39a8f7a29dcaf7`.
- Read-only qualification workflow: `.github/workflows/e1a-canonical-ab-qualification.yml`.
- Draft qualification PR: `#377`, explicitly not for merge.
- Canonical run: `34768852674`, job `103754617726`, qualified HEAD `6f05ac1677b070c60488dc08616d855eddaf2996`.
- Actions artifact: `10321675054`, digest `sha256:10cd159b9e479ef116e4369638d9ecf7e6986fdd9f7056c7b4ddbbf3f761d45d`.
- Persisted compact evidence: `ab/canonical-qualification/`.
- Current exact blockers: `ab/EXECUTION_STATUS.md`.

## Deterministic qualification result

`PASS_DETERMINISTIC_CANONICAL_QUALIFICATION`

The canonical generic validator reports `ok=true` and no cross-file errors. Route A has zero errors/warnings. Route B has zero errors plus one non-blocking warning that its U₃ explanation is unusually short. The canonical Atlas arbitrary-package validator passes both candidates. M3.1 reports `EXCELLENT_BY_PROFILE` for both with 0 blocking / 0 warning / 0 advice.

This closes the earlier concern that author-side reconstructed checks might have diverged from the repository authorities. They did not materially diverge on validity or M3.1 outcome, although the real generic validator surfaced the retained Route B short-explanation warning that the earlier local summary did not expose.

## Complexity ledger

Route B adds source manifest/map, compact knowledge bundle, typed relation sidecar, scope manifests, pedagogical blueprints and impact manifest. It does not add backend, graph/vector DB, OCR, Player/schema/learner-state changes, generic ingestion platform or runtime dependency.

The final A/B kit structures are intentionally comparable. This is important: Knowledge Architecture does not win because it produces more metadata. Its value must appear in scope/provenance/reuse/change-management while final learner quality is non-degraded. The deterministic qualification now shows non-degradation at the canonical structural/M3.1 layer; semantic non-degradation remains to be independently established.

## Independent audit

The experiment no longer relies on local reconstructed validator claims: the frozen pair has now been run by the actual repository authorities in CI, bound to exact blobs and authority hashes.

A false PASS is still rejected. The source PDF bytes were not present in the CI environment, so an exact Factory context was not generated there. The active author execution has also seen the authoring context and both candidates, so it cannot truthfully act as an independent reviewer. Consequently neither `PASS_SEMANTIC_REVIEW_V1` nor `PASS_AI_KIT_FACTORY_V1` is claimed.

A false FAIL is likewise rejected. Both routes are canonically valid and M3.1-equivalent at `EXCELLENT_BY_PROFILE`, while Route B already demonstrates source-bound target/prerequisite separation and dependency-addressable impact analysis that Route A does not carry as durable authoring artifacts.

## FINAL VERDICT

`HOLD_E1A_ARCHITECTURE_NEEDS_REWORK`

### Minimum remaining proof

Do not redesign and do not rerun authoring. Present the exact source PDF bytes, frozen learner brief and exact Route A candidate to one clean semantic-review execution, then do the same independently for Route B. Generate the exact Factory contexts and run the unchanged Factory Gate only after each genuine independent review exists.

PASS to E1B only if both routes obtain genuine `PASS_AI_KIT_FACTORY_V1`, Route B remains semantically non-degraded, and its scope/provenance/reuse/impact advantage remains material after accounting for the extra artifacts.

## Mandatory question

> If Learn-it had to produce 20 kits from this course or a much longer course, would the added knowledge artifacts really reduce work, inconsistencies and evolution cost—or merely move complexity?

Current answer: **the architecture is increasingly plausible for overlapping/evolving kits, and deterministic learner-quality non-degradation is now proven at the canonical M3.1 layer. The remaining causal proof is semantic and independent, not structural.** For isolated kits the extra layer remains overhead; therefore the Direct route must stay available.
