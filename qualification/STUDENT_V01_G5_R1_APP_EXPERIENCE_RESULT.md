# Student V0.1 — G5 R1 App Experience qualification

Work package: `ATLAS-WP-051`  
Issue: #433  
Draft PR: #436  
Common base: `18b925436777943b19c4b031c24659ad60dee133`  
G4 candidate: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`  
RESULT_SHA: 1d32e819a4a71e08f23bd64e9b9cb9fa643feef6

## Authority and scope

- UCP 1.1-R4 was byte-verified against the installed constitutional SHA-256 before governed execution.
- The active control-plane selection remained unchanged through the final mutation preflight.
- PR #436 remained DRAFT, unmerged, and based exactly on the common base.
- RESULT ancestry merge-base is exactly the common base.
- RESULT changed paths are limited to ATLAS-WP-051-authorized job/WP/CI/test/product-shell paths.
- `apps/learnit-next/src/ui/activity_presenters.js` remains blob `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`.
- `apps/learnit-next/source_manifest.json` remains blob `a15325fb50d77dd770fd92c07271cf2461313aad`, exactly equal to the common base.
- No `apps/learnit-next/src/core/**`, `build.py`, `index.template.html`, contracts, authoring, showcase, pilot, QA, governance or tools payload was changed by RESULT.

## Baseline reproduction and repair

The deterministic static oracle reproduced both G4 defects on the exact common base:
- false learner-facing Atlas empty diagnosis after rich V4 import;
- verbose objective detail preceding the active activity.

At RESULT:
- rich V4 courses that are not planner-compatible remain presented by the canonical learner library rather than a false Atlas empty state;
- the current activity is before objective buckets and detailed progress in DOM order;
- every objective receives a compact reservoir/bucket plus learner-readable state text;
- detailed objective evidence is behind a closed-by-default `Voir ma progression` disclosure;
- the active activity is not visually competed with by `Prochaine action recommandée`;
- current progress state remains the source of bucket state; no second progress truth was introduced.

## Exact-head qualification

Learn-it Next CI:
- run: `35789310961`
- exact-head job: `106953711305`
- target: `1d32e819a4a71e08f23bd64e9b9cb9fa643feef6`
- conclusion: success

Repository governance:
- run: `35789310959`
- validate-repository job: `106953710810` — success
- aggregate Repository governance job: `106953752609` — success

Deterministic application build:
- bytes: `482573`
- SHA-256: `b13872b9bbdd03f897c671e2cdb8232fa49cbb8fcb918d9322a67aa59d078f9a`
- two independent builds were byte-identical.

Because ATLAS-WP-051 explicitly freezes `source_manifest.json`, exact-head CI generated a transient manifest preview only inside a detached temporary worktree to validate the changed source fingerprints. The branch manifest itself remained byte-identical to the common base. The generated HTML was then used for the unchanged runtime/browser regressions.

## Qualification results

- FALSE_EMPTY_STATE: PASS
- ACTIVITY_PRIMARY: PASS
- COMPACT_OBJECTIVE_BUCKETS: PASS
- PROGRESSIVE_DISCLOSURE: PASS
- RESUME_RECOVERY: PASS
- ACTIVITY_PRESENTERS_UNCHANGED: PASS
- CORE_SEMANTICS_UNCHANGED: PASS
- PRODUCT_REGRESSIONS: PASS
- INTEGRATION_CI: PASS
- REPOSITORY_GOVERNANCE: PASS
- SCOPE: PASS

Browser evidence includes desktop `1365x768`, mobile `390x844`, keyboard disclosure, all rich activity families, real served V4 journey, reload/resume, completion, accessibility smoke and secret-boundary checks.

## Boundary

This PASS authorizes only later corrective integration under ATLAS-WP-054. It does not authorize merge, G4 R1, replacement G5 replay, release or student sessions.

FINAL_VERDICT: PASS_STUDENT_V01_G5_R1_APP_EXPERIENCE_READY_FOR_INTEGRATION
