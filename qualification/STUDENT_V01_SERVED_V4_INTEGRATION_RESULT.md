# Student V0.1 — Served V4 Integration Result

Status: PASS
Work package: `ATLAS-WP-037`
Authority issue: #410
Pull request: #411
RESULT_SHA: `bdb66bffefd6738e3cb4004d304159e9d3d048ce`
Evidence model: this file is added by an evidence-only commit after the executable RESULT_SHA. The exact EVIDENCE_HEAD is the commit that adds this file and is recorded in the final job result block.

## Governance binding

Fresh constitutional and operational binding was revalidated before the final mutations and again immediately before this evidence commit.

- UCP repository/object: `stefm78/human-control-plane@main:governance/UCP_ACTIVE.md`
- UCP SPEC_ID: `UCP-CONTROL-PLANE`
- UCP STATUS: `ACTIVE`
- UCP VERSION: `1.1-R4`
- UCP SHA256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- UCP git blob: `053440d84cd29a14e9c3112a18a72d7b391ce74b`
- CONTROL_PLANE_HEAD git blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- UAO: `UAO-KERNEL 2.6 ACTIVE`
- UAO SHA256: `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- UAO git blob: `5530dd710cb3615833d3529de7aab6f68aa067b0`
- Kernel registry: `2.5 ACTIVE`
- Kernel registry SHA256: `41abb5e2b36607bbdc246d64f32e03584689bd2efc599921ca7406c404f476d6`
- Kernel registry git blob: `f8ff46f3a57f31ec1ebc786d40b8b8cca2215d40`

## Exact bases

- REPAIR_BASE: `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- PREVIOUS_QUALIFIED_PRODUCT: `8fa25844cf9ddf7c2429f730d818b3518c46de04`
- PR base branch: `student-v01/fanin-a-r3-oracle`
- PR base SHA: `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- PR head branch: `student-v01/served-v4-integration`
- RESULT_SHA merge-base with REPAIR_BASE: exact REPAIR_BASE
- RESULT_SHA compare state: ahead only; behind by 0

## Reproduced blocker and diagnosis

The frozen V4 activity model already supported eight activity families through the core evaluator and generic ActivityPresentation projection/presenter seam. The served classic session path was still effectively qcm/fill-oriented, while Atlas compatibility was implicitly constrained by fields such as `assessmentRole` even though conforming lesson/flashcard activities do not carry that field and the Atlas session implementation is intentionally qcm/fill-only.

Diagnosis: the missing capability was a bounded served-session integration seam, not a V4 schema, core evaluation, generic presenter, persistence, authoring, or architecture defect.

## Integration design

Selected design: `CLASSIC_CORE_SESSION_PLUS_GENERIC_PRESENTERS`.

The core session remains the sole sequencing/evaluation/persistence authority. `main.js` projects canonical current/next activities at the learner boundary through the frozen `projectActivityPresentation()` function and emits only:

```text
{
  activityRevisionId,
  presentation
}
```

The classic UI reuses the frozen generic `renderActivityPresentation()` and `readActivityResponse()` seam. Lesson and flashcard receive neutral completion feedback when `scored !== true`. Atlas remains intentionally bounded to qcm/fill through an explicit supported-type gate, so rich V4 courses stay on the classic served path.

Rejected alternatives: changing the V4 schema, adding a second evaluator, changing generic projection semantics, changing generic presenters, widening the Atlas session engine, changing persistence, or disabling Atlas globally. None was required.

## Exact product diff

The bounded product repair changes only:

- `apps/learnit-next/src/main.js` — learner-safe current/next runtime projection.
- `apps/learnit-next/src/ui/render.js` — generic served renderer/response reader and neutral non-scored feedback.
- `apps/learnit-next/src/integration/atlas/surface.js` — explicit qcm/fill Atlas compatibility gate.

The V4 schema, `activity_semantics.js`, `activity_projection.js`, generic `activity_presenters.js`, `ui/media.js`, Atlas `session.js`, storage schema, authoring, and frozen showcase content were not changed by this repair.

## Learner-safe served boundary

The exact built runtime was exercised through `window.__LEARNIT_NEXT_TEST__` on the built Learn-it Next HTML.

PASS evidence:

- current activity envelope has exactly `activityRevisionId` and `presentation`;
- every returned `nextActivity` has the same safe envelope;
- forbidden scoring-secret keys are absent recursively: `correctChoiceId`, `answers`, `acceptedResponses`, `matches`, `correctOrder`, `assignments`;
- the serialized learner activity does not contain those field names;
- rendered activity DOM/attributes do not contain those field names;
- all eight response shapes round-trip through the real runtime;
- qcm/fill/constructed/matching/order/classify return `scored:true`;
- lesson/flashcard return `scored:false` and omit `correct`;
- constructed media reaches ActivityPresentation from the package asset through the trusted projection.

Observed markers:

```text
SERVED_RUNTIME_PROJECTION_BOUNDARY=PASS
CURRENT_NEXT_LEARNER_SAFE=PASS
FORBIDDEN_SECRET_KEYS_RECURSIVE=PASS
ALL_EIGHT_RESPONSE_SHAPES=PASS
SCORED_FAMILIES_RUNTIME=PASS
NON_SCORED_RESULT_SHAPE=PASS
TRUSTED_MEDIA_PROJECTION=PASS
```

## Atlas compatibility decision

The exact rich V4 fixture was imported into the built runtime and did not produce an Atlas course surface. The existing supported qcm/fill Atlas fixture `authoring/v2/atlas/nombres_complexes_atlas.json` was then imported into clean storage and did produce an Atlas course surface.

Observed markers:

```text
ATLAS_EXPLICIT_QCM_FILL_GATE=PASS
ATLAS_RICH_REJECTED=PASS
ATLAS_QCM_FILL_ACCEPTED=PASS
```

The existing `apps/learnit-next/tests/atlas_m1_int.py -v` and `apps/learnit-next/tests/atlas_m2_ux_clarity.py -v` suites also passed on RESULT_SHA.

## Real served browser journey

The browser qualification used the built `apps/learnit-next/dist/learnit-next.html`, the frozen `apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`, actual file input/import controls, actual course start control, and visible learner controls for all eight families.

Observed markers:

```text
STUDENT_V01_SERVED_V4_BROWSER_PASS
REAL_SERVED_V4_JOURNEY=PASS
ALL_FAMILIES_REAL_PATH=PASS
RELOAD_RESUME=PASS
COMPLETION=PASS
NON_SCORED_LESSON_FLASHCARD=PASS
SECRET_BOUNDARY=PASS
SERIALIZED_PRESENTATION_SECRET_BOUNDARY=PASS
DOM_SECRET_BOUNDARY=PASS
SAFE_MEDIA=PASS
DESKTOP=PASS
MOBILE=PASS
ACCESSIBILITY_SMOKE=PASS
```

The browser run also asserted zero external HTTP(S) requests for the local media journey and no page errors.

## Media authority

The repair does not modify `apps/learnit-next/src/ui/media.js` or generic projection semantics. The unchanged Student V0.1 activity-presentation regression statically proves data-only local media handling, finite SVG tag/attribute allowlists, no `innerHTML`, no `insertAdjacentHTML`, no `fetch(`, no `XMLHttpRequest`, and emits `MEDIA_FAIL_CLOSED_STATIC_PASS`. The new served-browser test additionally proves the frozen local SVG renders without external network access.

## Commands and regression results

All of the following ran on exact RESULT_SHA under the routed `student-v01-served-v4` CI profile and passed:

```text
python -B apps/learnit-next/build.py
python -B apps/learnit-next/tests/student_v01_served_v4_integration.py
python -B apps/learnit-next/tests/browser_student_v01_served_v4_integration.py
python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v
python -B apps/learnit-next/tests/student_v01_activity_presentation.py
python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py
python -B authoring/v4/tests/test_validate_v4.py -v
python -B authoring/v2/atlas/tests/test_pedagogical_quality.py -v
python -B authoring/factory/tests/test_student_v01_v4.py -v
python -B apps/learnit-next/tests/student_v01_fanin_a.py
python -B apps/learnit-next/tests/atlas_m1_int.py -v
python -B apps/learnit-next/tests/atlas_m2_ux_clarity.py -v
python -B apps/learnit-next/build.py
```

The routed job completed SUCCESS. Regression logs include multiple unittest `OK` results, `STUDENT_V01_FANIN_A_SECRET_BOUNDARY_PASS`, Atlas M1 integration PASS, Atlas M2 UX PASS, and the V4 authoring/factory suites PASS.

## Source manifest

`apps/learnit-next/source_manifest.json`:

- git blob: `a15325fb50d77dd770fd92c07271cf2461313aad`
- canonical self SHA256: `09750449aa48fb5e62ee5985d0d1b604f9752dcc9aab4b046dce7d534fdeee73`
- `src/main.js` fingerprint: `828997da351fc63b72adacf61f330fe2fcdd8f31`
- `src/ui/render.js` fingerprint: `0fc4b5027c82d038f69d402f97f8d0e059c5401c`
- `src/integration/atlas/surface.js` fingerprint: `aea13ae66fdeeddae6a32b46f8c53875f6a754ad`

The build accepted the manifest on both exact builds.

## Deterministic artifact

Build 1:

- bytes: `478657`
- SHA256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Build 2:

- bytes: `478657`
- SHA256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Observed marker: `STUDENT_V01_SERVED_V4_DETERMINISTIC_BUILD=PASS`.

## Workflow evidence

- Learn-it Next CI run: `35426446905` — SUCCESS
- Exact-head routed matrix job: `105853131991` — SUCCESS
- Repository governance run: `35426446912` — SUCCESS
- Exact route marker: `STUDENT_V01_SERVED_V4_EXACT_ROUTE=PASS`
- Exact target marker: `STUDENT_V01_SERVED_V4_TARGET=bdb66bffefd6738e3cb4004d304159e9d3d048ce`

## RESULT_SHA scope

The exact compare `281dc7470d51682c5e6d79d3fff54c46cfbced3b..bdb66bffefd6738e3cb4004d304159e9d3d048ce` is ahead only, behind by 0, with exact merge base `281dc7470d51682c5e6d79d3fff54c46cfbced3b`.

Changed paths on RESULT_SHA:

```text
.github/workflows/learnit-next-ci.yml
apps/learnit-next/source_manifest.json
apps/learnit-next/src/integration/atlas/surface.js
apps/learnit-next/src/main.js
apps/learnit-next/src/ui/render.js
apps/learnit-next/tests/browser_student_v01_served_v4_integration.py
apps/learnit-next/tests/student_v01_served_v4_integration.py
docs/programs/student-v0.1/jobs/JOB_04_R4_SERVED_V4_INTEGRATION.md
work-packages/ATLAS-WP-037.json
```

All are authorized JOB04 R4 paths. The evidence-only commit adds only `qualification/STUDENT_V01_SERVED_V4_INTEGRATION_RESULT.md`; final scope is re-audited after that commit.

## Rollback and reservations

Rollback target for this bounded repair is exact `REPAIR_BASE = 281dc7470d51682c5e6d79d3fff54c46cfbced3b` or equivalent clean reversion of the JOB04 R4 repair/evidence commits.

This PASS does not authorize Wave 2 G3, JOB08, a merge to main, or real-student use. PR #411 remains draft and unmerged. JOB06 remains frozen and is not rerun. The only downstream authorization produced by this result is Control Room preparation of JOB05 R1 contradictory QA and JOB07 R1 pilot packaging against exact RESULT_SHA.

## Verdict

`PASS_STUDENT_V01_SERVED_V4_READY_FOR_JOB05_R1_JOB07_R1`
