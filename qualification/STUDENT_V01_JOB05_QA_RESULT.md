# Student V0.1 — JOB05 Contradictory QA Result

Status: **HOLD — PRODUCT GAP**

Work package: `ATLAS-WP-034`  
Authority issue: #404  
Authoritative DRAFT PR: #407  
QA branch: `student-v01/wave2-contradictory-qa`

## 1. Exact authority and frozen inputs

Immediately before the evidence mutation:

- Human Control Plane HEAD blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- UCP: `UCP-CONTROL-PLANE 1.1-R4`
- UCP SHA256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- UAO: `2.6`
- UAO SHA256: `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- Wave 2 common base: `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- Qualified product base: `8fa25844cf9ddf7c2429f730d818b3518c46de04`
- QA executable/result head before this evidence commit: `3ef8895fcf4df0ded936daf4c939e2c60200232c`
- PR #407 base: exact `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- PR #407 was open, DRAFT and unmerged.

The qualified product base differs from the Wave 2 common base only by the R3 qualification evidence commit. No Wave 2 sibling branch was consumed.

## 2. Independent QA fixture

JOB05 adds an independently authored canonical-shape fixture at:

`qa/student-v0.1/JOB05_CANONICAL_V4_FIXTURE.json`

It contains exactly one course and exactly these eight activity families, in authored order:

`lesson, flashcard, matching, order, classify, qcm, fill, constructed`

It also contains a local embedded SVG with a normal
`xmlns="http://www.w3.org/2000/svg"` declaration. The lesson and flashcard
omit `assessmentRole`, as required by the frozen V4 non-scored semantics.

The fixture package digest recorded by the exact canonical digest algorithm is:

`sha256:1fc35e1164248c3e872dc136d58ec27f0aa6f3ee8c034d55f522cd5cd4f5c7f6`

The frozen V4 schema was independently inspected against the fixture shape and confirms
that the package keys are admitted, all eight families are schema families, and
`lesson` / `flashcard` derive from the non-scored `unitCommon` shape rather
than the evaluated shape that requires `assessmentRole`.

Because no permitted execution vehicle was available to invoke the repository's exact
`authoring/v4/validate_kit.py` against this new QA file without changing forbidden
workflow/product paths, JOB05 does **not** convert these static checks into a canonical
validator PASS. The final matrix therefore marks `CANONICAL_V4_FIXTURE: FAIL`
fail-closed rather than asserting unexecuted evidence.

## 3. False-PASS challenge against R3

R3 correctly proved the isolated Student V0.1 seams, but JOB05 found that the real served
journey does not consume those seams for rich V4 activity execution.

The frozen candidate contains:

- `apps/learnit-next/src/integration/atlas/activity_projection.js`, which projects all eight families;
- `apps/learnit-next/src/ui/activity_presenters.js`, which renders and reads all eight families;
- `apps/learnit-next/src/ui/media.js`, which provides the fail-closed local media boundary.

However, the actual served session paths remain independently limited.

### Classic served session

`apps/learnit-next/src/ui/render.js` renders the current activity with only two branches:

- `qcm` -> `renderQcmForm(...)`
- every other activity type -> `renderFillForm(...)`

Therefore a conforming `lesson`, `flashcard`, `matching`, `order`,
`classify` or `constructed` activity is not routed to the qualified rich presenter.

For the JOB05 fixture, the first activity is `lesson`. The real classic start route
therefore reaches the fill renderer with a lesson-shaped object rather than
`renderActivityPresentation(lesson)`.

### Atlas served session

`apps/learnit-next/src/integration/atlas/session.js` has its own activity projector,
registry and markup/response path. They explicitly accept only `qcm` and `fill` and
raise `ATLAS_ACTIVITY_TYPE_UNSUPPORTED` for the other six families.

In addition, `apps/learnit-next/src/integration/atlas/surface.js` considers a course
Atlas-compatible only when **every** activity has a string `assessmentRole`.
The frozen V4 authority explicitly makes `lesson` and `flashcard` non-scored and
forbids `assessmentRole` on those families. A conforming all-eight course is therefore
excluded by the Atlas compatibility gate before the qualified rich presenter can rescue
the journey.

This is a causal served-product integration contradiction, not merely a missing QA
assertion.

## 4. Smallest durable reproduction

JOB05 adds:

`qa/student-v0.1/job05_contradictory_qa.py`

The repro is QA-only and is designed to:

1. run the frozen canonical V4 validator on the independent fixture;
2. build Learn-it Next twice and require the R3 artifact identity:
   - bytes `474861`
   - SHA256 `0b1e21038bc8f17521ecd604460781377a850b174907723a7d6af6174511310f`;
3. prove that the qualified eight-family seams are present while both served routes are
   still qcm/fill constrained;
4. serve the **actual built HTML**;
5. use the real file input / `Importer` / course `Commencer` controls;
6. run the same causal probe at desktop `1365x768` and mobile `390x844`;
7. fail closed on unexpected external browser network requests.

A successful execution of this harness means the expected JOB05 HOLD was reproduced; it
does not mean the product passed.

The connected GitHub environment exposed no permitted workflow-dispatch mutation for the
QA branch. The only automatic workflow on `3ef8895fcf4df0ded936daf4c939e2c60200232c`
was Repository governance run `35357209645`, which completed successfully but does not
execute the browser repro. JOB05 did not add or modify `.github/**`, product code, or
schema files merely to force the test to run.

Consequently, browser/build/canonical-validator rows that were not independently executed
are marked FAIL rather than being inherited from R3.

## 5. Defect ownership

Smallest failing served boundary: **PRESENTATION_UI**.

Reason:

- contract/import explicitly admit `learnit.kit.v4` and all eight families;
- the rich presentation/projection seams exist;
- the real classic learner session dispatches only qcm vs fill;
- the Atlas session path also remains two-family and rejects conforming non-scored
  lesson/flashcard compatibility.

The primary first failing boundary for the canonical JOB05 journey is the actual
presentation/session dispatch reached from the real learner start action.

No product repair was attempted under JOB05.

## 6. Scope audit

Exact `WAVE2_COMMON_BASE..RESULT_SHA` changed paths before this evidence commit:

- `docs/programs/student-v0.1/jobs/JOB_05_CONTRADICTORY_QA.md`
- `work-packages/ATLAS-WP-034.json`
- `qa/student-v0.1/JOB05_CANONICAL_V4_FIXTURE.json`
- `qa/student-v0.1/job05_contradictory_qa.py`

No product/runtime/schema/architecture/workflow path changed.

Repository governance run `35357209645` completed with conclusion `success`.

Scope: **PASS**.

## 7. Stop condition

The JOB05 stop condition is reached at the first causal product gap. Later attacks
(reload/resume, completion, end-state accessibility, persistence isolation and legacy
regression execution) are not promoted to PASS merely because lower-level R3 seams had
previously passed.

For the required binary result matrix, a FAIL after this stop condition means either
"causally blocked by the product gap" or "not independently executed by JOB05"; it must
not be read as a separate defect attribution for every row.

## 8. Final contradictory audit

False-PASS challenge: **FAIL for the product candidate**.

The previous seam-level browser tests instantiate the rich presenters directly. The
served product instead routes through classic/Atlas session code that remains constrained
to qcm/fill semantics. Therefore seam PASS is not equivalent to learner-journey PASS.

False-product-gap challenge: **rejected at source boundary**.

The contradiction is deterministic in the frozen candidate:

- conforming lesson/flashcard are non-scored;
- Atlas compatibility demands `assessmentRole` from every activity;
- Atlas execution supports only qcm/fill;
- classic served dispatch supports only qcm/fill;
- the eight-family presenter is not on the actual session dispatch path.

Final audit: **HOLD — PRODUCT GAP**.

No merge is authorized.

## 9. Final result

```text
STUDENT_V01_JOB05_RESULT
WAVE2_COMMON_BASE: 281dc7470d51682c5e6d79d3fff54c46cfbced3b
QUALIFIED_PRODUCT_BASE: 8fa25844cf9ddf7c2429f730d818b3518c46de04
RESULT_SHA: 3ef8895fcf4df0ded936daf4c939e2c60200232c
ISSUE: 404
PR: 407
BUILD_IDENTITY: FAIL
CANONICAL_V4_FIXTURE: FAIL
REAL_SERVED_V4_JOURNEY: FAIL
ALL_FAMILIES_REAL_PATH: FAIL
RELOAD_RESUME: FAIL
COMPLETION: FAIL
NON_SCORED_LESSON_FLASHCARD: FAIL
SECRET_BOUNDARY: FAIL
MEDIA_FAIL_CLOSED: FAIL
DESKTOP: FAIL
MOBILE: FAIL
ACCESSIBILITY_SMOKE: FAIL
PERSISTENCE_ISOLATION: FAIL
V2_V3_REGRESSION: FAIL
DEFECT_OWNER: PRESENTATION_UI
SCOPE: PASS
FINAL_VERDICT: HOLD_STUDENT_V01_JOB05_PRODUCT_GAP
```
