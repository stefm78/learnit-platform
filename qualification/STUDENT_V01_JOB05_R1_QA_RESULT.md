# Student V0.1 — JOB05 R1 Contradictory QA Result

**Status:** PASS  
**Verdict:** `PASS_STUDENT_V01_JOB05_R1_READY_FOR_JOB07_R1`  
**Authority:** issue #412 / ATLAS-WP-038  
**Qualification PR:** #413 (DRAFT, unmerged)  
**Qualified RESULT_SHA:** `1c92cad7ea576a613b6f198768bbebd114a06082`

## 1. Frozen authority and ancestry

The R1 qualification was executed from the approved repair/freeze chain:

- `JOB05_R1_BASE = 7c13d67a76705b4452304c0f6a882504bc7701a7`
- `REPAIRED_PRODUCT_SHA = bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- `PRE_REPAIR_JOB05_RESULT = 3ef8895fcf4df0ded936daf4c939e2c60200232c`
- frozen QA fixture Git blob: `c190fc4f04a7cee5731627e4f6276ee08e39d746`

At RESULT_SHA, the exact R1 base is an ancestor and the repaired product SHA is an ancestor. The R1 delta contains only the approved job/work-package/fixture, the two JOB05 R1 QA harnesses, and the minimal exact-head workflow route. No product source, source manifest, build script, product tests, contracts, architecture, authoring, showcase, pilot, or governance file changed after the repaired product anchor.

## 2. Independent oracle strategy

The repair author's earlier JOB05 verdict was not reused as the R1 oracle. R1 uses the pre-repair frozen V4 fixture and two new contradictory harnesses:

- `qa/student-v0.1/job05_r1_contradictory_qa.py`
- `qa/student-v0.1/browser_job05_r1_contradictory_qa.py`

The static harness verifies frozen-fixture identity, runs the canonical V4 validator, builds the artifact twice, challenges the former classic/Atlas routing blocker, and executes digest-attributable malicious-media negatives.

The browser harness drives the repaired product through the actual learner controls for the full frozen family sequence:

`lesson -> flashcard -> matching -> order -> classify -> qcm -> fill -> constructed`

It separately exercises an intentional incorrect matching answer, reload/resume at multiple semantic points, completion/reopen behavior, runtime/DOM secret-boundary scans, local media, active/remote hostile media, desktop/mobile viewport behavior, keyboard/focus smoke checks, persistence/isolation, and the Atlas qcm/fill gate.

## 3. Frozen fixture and canonical authoring validation

PASS:

- exact Git blob = `c190fc4f04a7cee5731627e4f6276ee08e39d746`
- canonical `authoring/v4/validate_kit.py --format=json` returns PASS
- family order is exactly the frozen eight-family sequence
- lesson and flashcard remain non-scored authoring units
- no R1-owned substitute fixture was used

CI marker:

- `JOB05_R1_FROZEN_FIXTURE_IDENTITY=PASS`
- `JOB05_R1_CANONICAL_V4_FIXTURE=PASS`

## 4. Old blocker closure

PASS. The prior blocker is closed on the repaired product:

- learner current/next activity envelopes are projected to `{activityRevisionId, presentation}`
- the classic served session renders through the generic activity presenter path rather than qcm/fill-only rendering
- the generic presenter supports all eight frozen activity families
- the Atlas compatibility gate remains explicitly bounded to qcm/fill activity types
- the frozen rich V4 course is not intercepted by Atlas
- an existing qcm/fill Atlas fixture is still accepted and rendered by Atlas

CI markers:

- `JOB05_R1_OLD_BLOCKER_STATIC_CLOSED=PASS`
- `JOB05_R1_ATLAS_GATE=PASS`

## 5. Real served V4 journey

PASS on real Chromium with actual visible learner controls.

For every family the QA:

- confirms the expected rendered family
- scans the projected runtime object for scoring-secret keys
- scans the rendered learner DOM for the same secret keys
- operates the visible family-specific controls
- submits through the served submit control
- inspects scored/non-scored feedback and persisted progress
- advances or reloads using the product's real continuation/resume behavior

All eight families complete in order and the final course state is complete. Returning to the library and reopening/reloading preserves completion coherently.

CI markers:

- `JOB05_R1_REAL_SERVED_V4_JOURNEY=PASS`
- `JOB05_R1_ALL_FAMILIES_REAL_PATH=PASS`
- `JOB05_R1_COMPLETION=PASS`

## 6. Incorrect-answer challenge

PASS on a disposable clean state.

The harness intentionally submits a wrong matching association through the real UI. It requires:

- scored feedback
- incorrect learner feedback
- persisted progress record with `correct=false`
- the activity to enter the review queue

The state is discarded after the negative run and is not reused for the clean success run.

CI marker:

- `JOB05_R1_WRONG_ANSWER_SEMANTICS=PASS`

## 7. Reload / resume / persistence

PASS.

The clean journey reloads at three distinct incomplete states:

1. immediately after a completed non-scored lesson
2. immediately after a completed scored matching activity
3. immediately after a completed scored qcm activity

Each reload resumes on the correct next family with the same learner-safe projection. After final completion, a library return plus page reload preserves the completed state.

Isolation challenges also pass:

- two independently identified packages/courses with the same human-readable labels remain distinct installations
- reload preserves both installations
- clean reset removes Learn-it data
- unrelated local state sentinel remains untouched by Learn-it reset/journey operations

CI markers:

- `JOB05_R1_RELOAD_RESUME=PASS`
- `JOB05_R1_PERSISTENCE_ISOLATION=PASS`

## 8. Scored vs non-scored semantics

PASS.

Lesson and flashcard:

- complete through the real served controls
- persist `scored=false`
- do not carry a correctness field
- never show correct/incorrect learner feedback

Matching, order, classify, qcm, fill, and constructed remain scored.

CI marker:

- `JOB05_R1_NON_SCORED_LESSON_FLASHCARD=PASS`

## 9. Scoring-secret boundary

PASS.

The R1 browser oracle recursively scans every current learner activity projection and requires its top-level envelope to contain only:

- `activityRevisionId`
- `presentation`

It rejects any runtime or rendered-DOM occurrence of:

- `correctChoiceId`
- `answers`
- `acceptedResponses`
- `matches`
- `correctOrder`
- `assignments`

This scan is repeated across the complete eight-family path, including after reload/resume points.

CI marker:

- `JOB05_R1_SECRET_BOUNDARY=PASS`

## 10. Media safety

PASS.

Positive case:

- frozen inline SVG media renders on the real learner page
- alternative text is present
- the rendered source is local/data-backed
- no unexpected external request is observed

Negative cases are generated in temporary QA data only. For both an active SVG payload and an external/remote-reference SVG payload:

- the package revision identity is changed
- the package digest is reset and recomputed using the canonical authoring digest implementation
- the canonical authoring validator rejects the payload for media safety
- the rejection is not a stale/digest mismatch
- the runtime validator rejects it with `unsafe_svg`
- runtime import fails closed
- no course/learner activity is admitted
- no external network request is emitted

CI markers:

- `JOB05_R1_MEDIA_AUTHORING_FAIL_CLOSED=PASS`
- `JOB05_R1_MEDIA_SAFE_LOCAL=PASS`
- `JOB05_R1_MEDIA_RUNTIME_FAIL_CLOSED=PASS`

## 11. Desktop, mobile, keyboard/focus smoke

PASS.

The full learner journey runs independently at:

- desktop viewport: 1365×768
- mobile viewport: 390×844 with touch enabled

For every activity family, the relevant visible interactive controls are required to be keyboard-focusable and to expose a meaningful visible/accessible name. Matching, order, and classify expose non-drag-only button/select controls. Feedback transfers focus to a status target. No horizontal overflow is accepted.

CI markers:

- `JOB05_R1_DESKTOP=PASS`
- `JOB05_R1_MOBILE=PASS`
- `JOB05_R1_ACCESSIBILITY_SMOKE=PASS`

## 12. Deterministic build identity

PASS.

Two canonical builds executed inside the independent R1 harness are byte-identical and match the repaired product artifact exactly. The workflow performs a final canonical rebuild and checks the same identity again.

- bytes: `478657`
- SHA-256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

CI markers:

- `JOB05_R1_BUILD_IDENTITY_EXACT_REPAIR=PASS`
- `STUDENT_V01_JOB05_R1_ARTIFACT_BYTES=478657`
- `STUDENT_V01_JOB05_R1_ARTIFACT_SHA256=85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

## 13. Regression matrix

All required routed regressions passed on RESULT_SHA.

Observed proof includes:

- repaired served-V4 static suite: PASS
- repaired served-V4 real-browser suite: PASS
- Student V0.1 learning runtime, including frozen V2 acceptance and V3 constructed semantics: `STUDENT_V01_LEARNING_RUNTIME_PASS 92/92`
- Student V0.1 activity-presentation static suite: PASS
- Student V0.1 activity-presentation browser suite: PASS
- canonical V4 validator tests: 8/8 PASS
- Atlas pedagogical-quality tests: 6/6 PASS
- Student V0.1 V4 factory tests: 3/3 PASS
- FAN-IN A authoring-to-learner/all-family/secret/media/non-scored regressions: PASS
- Atlas M1 integration: 15/15 PASS
- Atlas M2 UX clarity: 17/17 PASS

No regression failure was accepted or waived.

## 14. Exact-head CI and governance evidence

Qualified exact-head workflow:

- workflow: **Learn-it Next CI**
- run number: **623**
- run id: `35469818920`
- exact-head routed job id: `105968617243`
- target: `1c92cad7ea576a613b6f198768bbebd114a06082`
- conclusion: **success**
- marker: `STUDENT_V01_JOB05_R1_EXACT_ROUTE=PASS`

The same log proves:

- repaired product anchor = `bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- fixture blob = `c190fc4f04a7cee5731627e4f6276ee08e39d746`
- exact artifact identity = `478657 / 85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Repository-governance runs for the same result head completed successfully (run numbers 1200 and 1201 in the two contemporaneous PR contexts).

A temporary DRAFT carrier PR #414 was opened when the stacked route initially exposed no run. It was never merged and was closed after the exact stacked #413 workflow evidence was captured. Its carrier-specific route/scope failures are not qualification evidence and did not modify product or authority state.

## 15. QA rework audit trail

Two pre-qualification QA harness defects were exposed by CI and corrected before RESULT_SHA:

1. an escaped newline in the newly added route caused a shell parse failure
2. the static harness omitted the repository root from Python import search path

Both failures were confined to R1 QA/workflow code. Neither was a product failure, neither caused product mutation, and neither was suppressed. RESULT_SHA is the first head after those QA defects were corrected that completed the entire exact-head contradictory QA matrix successfully.

## 16. Scope and stop-condition audit

PASS.

- product code remained read-only during JOB05 R1
- no source manifest/build/product-test/authoring/contract mutation occurred
- PR #413 remains DRAFT
- no merge to `main`
- no G3 action
- no JOB08 action
- no real-student pilot action
- carrier PR #414 closed unmerged

## Final qualification

No product blocker survived the independent R1 attacks, the original served-V4 blocker is closed, and the repaired artifact identity remains exact.

**VERDICT: `PASS_STUDENT_V01_JOB05_R1_READY_FOR_JOB07_R1`**

This verdict authorizes only the next step permitted by issue #412 / ATLAS-WP-038. It does not merge, promote, authorize G3/JOB08, or change any broader release gate.
