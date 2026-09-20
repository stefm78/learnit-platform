# Student V0.1 — JOB07 R2 Pilot Packaging / Learner-start UX Result

**Status:** PASS  
**Verdict:** `PASS_STUDENT_V01_JOB07_R2_READY_FOR_G3`  
**Authority:** issue #417 / ATLAS-WP-040  
**Authoritative PR:** #418 (DRAFT, unmerged)  
**RESULT_SHA:** `5e492fddc4d5cf00c71bdb770eb1aeac11a63803`

## 1. Authority and exact baseline binding

Execution followed the mandated `/refresh -> /audit -> /solve -> /build -> /audit` sequence.

- UCP: `UCP-CONTROL-PLANE 1.1-R4`
- bootstrap-bound UCP SHA-256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- active UAO: `2.6`, SHA-256 `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- JOB07_R2_BASE: `7c13d67a76705b4452304c0f6a882504bc7701a7`
- REPAIRED_PRODUCT_SHA: `bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- JOB05_R1_RESULT_SHA: `1c92cad7ea576a613b6f198768bbebd114a06082`
- JOB07_R1_RESULT_SHA: `87a851051bdf80d6e9edb097130521a96df4038a`
- canonical generator blob: `85debca78c3ec342d9e4e7ed63a033fd0968e72e`
- rejected historical R1 fixture blob: `943944eaee6944529810acffc06e61affc71f909`

PR #418 remained open, DRAFT and unmerged. Its exact base remained `7c13d67a76705b4452304c0f6a882504bc7701a7`.

## 2. Initial audit — R1 contradiction and replacement authority

The historical R1 input contradiction reproduced exactly. The frozen runtime fixture remained at blob `943944eaee6944529810acffc06e61affc71f909`, and canonical V4 validation failed specifically on the undersized lesson body:

`lesson body is too small to be substantive learner-facing exposition`

This is the same contradiction that caused JOB07 R1 to HOLD; it is not a product regression.

The R2 replacement authority also remained exact. `authoring/v4/tests/test_validate_v4.py` matched blob `85debca78c3ec342d9e4e7ed63a033fd0968e72e`, and the unchanged canonical V4 validator suite passed.

Markers:

- `STUDENT_V01_JOB07_R2_R1_INPUT_CONTRADICTION=PASS`
- `STUDENT_V01_JOB07_R2_CANONICAL_GENERATOR=PASS`
- `STUDENT_V01_JOB07_R2_GENERATED_KIT_CANONICAL=PASS`

## 3. Ephemeral canonical qualification kit

The qualification kit was generated ephemerally from the exact canonical generator and serialized deterministically as required.

- bytes: `8381`
- SHA-256: `6ea51f25f15d17a8ce27667fa99c74d2f02f307e82333f6b503fba96dd5549c3`
- packageRevisionDigest: `sha256:2c14395fa5571bc525ad2b1f0b41ab9b8a16e923c903f9345b0caf996387c099`
- courseRevisionDigest: `sha256:2a586816d8ddb7042cb60e9fcd0cac8f3ff12312135560317d453b6751b94b9e`
- activity order: `lesson, flashcard, matching, order, classify, qcm, fill, constructed`
- assets: `1`
- media references: `1`
- media profile: inline/local SVG, canonical-safe

The generated kit is qualification input only. The generic package builder does not import or call `make_valid_v4()`.

## 4. Repaired application identity and old blocker

The repaired application was built twice on the exact R2 head.

- bytes: `478657`
- SHA-256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`
- both builds were byte-identical

The generated canonical V4 kit was then imported through real browser controls against the actual repaired build. The browser traversed lesson, flashcard and matching using visible learner controls, while recursively checking the learner-safe activity projection and rendered DOM for scoring-secret keys.

Markers:

- `STUDENT_V01_JOB07_R2_REPAIRED_APP_IDENTITY=PASS`
- `STUDENT_V01_JOB07_R2_OLD_BLOCKER_CLOSED=PASS`
- `STUDENT_V01_JOB07_R2_GENERATED_KIT_REAL_CONTROLS=PASS`

No product blocker remained.

## 5. Selected package contract

The implemented package is a deterministic ZIP with one bounded root directory:

`student-v01-pilot/`

Entries:

- `START_HERE.html`
- `course.learnit.json`
- `learnit-next.html`
- `pilot_manifest.json`

The builder accepts explicit `--app`, `--kit` and `--output` inputs, validates the supplied kit with the canonical V4 validator, and fails closed on invalid/non-canonical input.

The package manifest binds exact app and kit byte counts and SHA-256 values, declares `learnit.kit.v4`, identifies `START_HERE.html`, records builder version `1.0`, and declares local/offline operation. It contains no timestamp, random identifier, machine path or machine name.

## 6. Determinism and integrity

Two independent package builds from the same app and generated kit were byte-identical.

Qualified archive identity:

- bytes: `490056`
- SHA-256: `4d66b92bbc11f6db3321dd13875c15e04d214684eb39327db797f4b2f0763c17`

ZIP qualification also verified:

- entries sorted deterministically
- fixed ZIP timestamp
- fixed regular-file permissions
- `ZIP_STORED`
- empty per-entry and archive comments
- no absolute or parent-traversal paths
- extracted `learnit-next.html` byte-identical to the built app
- extracted `course.learnit.json` byte-identical to the generated canonical kit
- manifest hashes/byte counts exactly match extracted contents
- invalid V4 input is rejected fail-closed

Markers:

- `STUDENT_V01_JOB07_R2_PACKAGE_MANIFEST_BINDING=PASS`
- `STUDENT_V01_JOB07_R2_PACKAGE_DETERMINISM=PASS`
- `STUDENT_V01_JOB07_R2_PACKAGE_INTEGRITY=PASS`

## 7. Learner start UX

Direct-file mode was tested first and succeeded. No local HTTP helper was required or packaged.

`START_MODE=DIRECT_FILE`

The learner path from opening `START_HERE.html` to a started course contains six mandatory actions:

1. open `START_HERE.html`
2. open Learn-it
3. activate the file chooser
4. select `course.learnit.json`
5. import
6. start the course

`LEARNER_START_ACTIONS=6`

`START_HERE.html` separates learner instructions, facilitator/setup instructions and recovery. It makes no cloud, account or remote-recovery claim.

Marker:

- `STUDENT_V01_JOB07_R2_START_INSTRUCTIONS=PASS`

## 8. Extracted-package real browser qualification

The archive was extracted before browser qualification. The actual packaged `START_HERE.html`, `learnit-next.html` and `course.learnit.json` were used.

Full eight-family journeys passed independently at:

- desktop: `1365x768`
- mobile: `390x844`, touch enabled

The journey exercised only visible learner controls for import/start/answers/navigation. Internal runtime methods were used only for non-mutating QA inspection of learner-safe state/progress, not to advance the learner flow.

The browser qualification proved:

- all eight families complete in canonical order
- reload/resume after a non-scored lesson
- reload/resume after a scored QCM
- return to library and `Reprendre` during an incomplete course
- final completion and completion persistence after reload
- no external HTTP/HTTPS requests
- runtime and rendered-DOM scoring-secret boundary
- local packaged media rendering
- no horizontal overflow at qualified viewports

Markers:

- `STUDENT_V01_JOB07_R2_OFFLINE_NO_REMOTE=PASS`
- `STUDENT_V01_JOB07_R2_REAL_PACKAGED_V4_JOURNEY=PASS`
- `STUDENT_V01_JOB07_R2_DESKTOP=PASS`
- `STUDENT_V01_JOB07_R2_MOBILE=PASS`
- `STUDENT_V01_JOB07_R2_RELOAD_RESUME=PASS`
- `STUDENT_V01_JOB07_R2_COMPLETION=PASS`
- `STUDENT_V01_JOB07_R2_SECRET_BOUNDARY=PASS`

## 9. Recovery qualification

Recovery was exercised through the packaged direct-file route.

PASS cases:

- canceled chooser leaves the selection empty and allows retry
- invalid JSON is rejected and does not admit a course
- valid kit can be selected after the invalid attempt
- visible local reset plus explicit confirmation clears Learn-it local data
- clean re-import succeeds after reset
- learner can start again after re-import
- library return plus `Reprendre` preserves an incomplete course

Marker:

- `STUDENT_V01_JOB07_R2_RECOVERY=PASS`

## 10. Repaired-product regression matrix

The exact-head R2 route reran the required unchanged repaired-product regressions after package qualification, including:

- served-V4 static integration
- served-V4 real browser journey
- Student V0.1 learning runtime
- activity-presentation static/browser suites
- FAN-IN A regressions
- canonical V4 validator tests
- Atlas pedagogical-quality tests
- Student V0.1 V4 factory tests
- Atlas M1 integration
- Atlas M2 UX clarity

All passed.

Marker:

- `STUDENT_V01_JOB07_R2_REPAIRED_PRODUCT_REGRESSION=PASS`

## 11. Exact-head CI and governance

Qualified executable/tested head:

`RESULT_SHA = 5e492fddc4d5cf00c71bdb770eb1aeac11a63803`

Learn-it Next CI:

- run id: `35527862777`
- run number: `630`
- exact-head job id: `106123071520`
- conclusion: `success`
- target marker: `STUDENT_V01_JOB07_R2_TARGET=5e492fddc4d5cf00c71bdb770eb1aeac11a63803`
- exact-route marker: `STUDENT_V01_JOB07_R2_EXACT_ROUTE=PASS`

Repository governance:

- run id: `35527862893`
- run number: `1216`
- conclusion: `success`

An earlier R2 CI attempt (#629) failed before checkout because a newly introduced router line contained a literal escaped newline. That CI-only defect was corrected without product/package semantic change. It is retained as rework history and is not qualification evidence.

## 12. Exact scope audit

Exact `JOB07_R2_BASE..RESULT_SHA` is ahead-only from the required base with merge base exactly `7c13d67a76705b4452304c0f6a882504bc7701a7`.

Changed paths are limited to:

- `.github/workflows/learnit-next-ci.yml`
- `docs/programs/student-v0.1/jobs/JOB_07_R2_PILOT_PACKAGING_UX.md`
- `work-packages/ATLAS-WP-040.json`
- `pilot/student-v0.1/browser_generated_v4_probe.py`
- `pilot/student-v0.1/browser_pilot_package.py`
- `pilot/student-v0.1/build_pilot_package.py`
- `pilot/student-v0.1/ci_job07_r2.py`
- `pilot/student-v0.1/materialize_qualification_kit.py`
- `pilot/student-v0.1/test_pilot_package.py`

All are allowed by ATLAS-WP-040. No contract, architecture, authoring, showcase, QA, governance, tool, product source, source manifest, build script or product-test path changed.

`PR_SCOPE=PASS` and `SCOPE=PASS`.

## 13. False-PASS / false-FAIL challenge

False-PASS challenge:

- R1's rejected fixture was not modified or silently reused as canonical qualification input.
- The replacement generated kit is bound to the exact frozen generator blob and independently canonical-validated.
- The generic builder cannot import the generator.
- Package PASS fields are backed by extracted-package execution rather than source-only assertions.
- Direct-file mode was actually exercised; no untested loopback fallback is claimed.
- Product regressions reran on the same exact RESULT_SHA.
- PR #418 remains DRAFT/unmerged.

False-FAIL challenge:

- the historical R1 contradiction still reproduces exactly, proving the classification transition is due to the corrected R2 authority model rather than hidden validator weakening;
- repaired application identity remains exactly the frozen bytes/SHA;
- old product blocker remains closed using the generated canonical kit through real controls;
- exact-head CI and repository governance both pass.

## 14. Evidence separation and rollback

This qualification file is evidence-only and is written after the tested executable head. No executable, workflow, package, product, contract, authoring or governance semantics change after RESULT_SHA.

If this qualification is rejected or superseded:

1. close PR #418 without merge;
2. delete branch `student-v01/wave2-pilot-package-r2`;
3. retain PR #411, JOB05 R1 and JOB07 R1 evidence unchanged;
4. do not perform G3, JOB08, main merge, release or real-student actions from this result.

No merge was performed during JOB07 R2.

```text
STUDENT_V01_JOB07_R2_RESULT
JOB07_R2_BASE: 7c13d67a76705b4452304c0f6a882504bc7701a7
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
JOB05_R1_RESULT_SHA: 1c92cad7ea576a613b6f198768bbebd114a06082
JOB07_R1_RESULT_SHA: 87a851051bdf80d6e9edb097130521a96df4038a
CANONICAL_GENERATOR_BLOB: 85debca78c3ec342d9e4e7ed63a033fd0968e72e
GENERATED_KIT_SHA256: 6ea51f25f15d17a8ce27667fa99c74d2f02f307e82333f6b503fba96dd5549c3
GENERATED_KIT_BYTES: 8381
RESULT_SHA: 5e492fddc4d5cf00c71bdb770eb1aeac11a63803
EVIDENCE_HEAD: THIS_EVIDENCE_ONLY_COMMIT
ISSUE: 417
PR: 418
R1_INPUT_CONTRADICTION: PASS
CANONICAL_GENERATOR_IDENTITY: PASS
GENERATED_KIT_CANONICAL: PASS
REPAIRED_APP_IDENTITY: PASS
OLD_BLOCKER_CLOSED: PASS
PACKAGE_MANIFEST_BINDING: PASS
PACKAGE_DETERMINISM: PASS
PACKAGE_INTEGRITY: PASS
START_MODE: DIRECT_FILE
LEARNER_START_INSTRUCTIONS: PASS
LEARNER_START_ACTIONS: 6
OFFLINE_NO_REMOTE: PASS
REAL_PACKAGED_V4_JOURNEY: PASS
DESKTOP: PASS
MOBILE: PASS
RELOAD_RESUME: PASS
COMPLETION: PASS
RECOVERY: PASS
SECRET_BOUNDARY: PASS
REPAIRED_PRODUCT_REGRESSION: PASS
REPOSITORY_GOVERNANCE: PASS
PR_SCOPE: PASS
INTEGRATION_CI: PASS
PRODUCT_BLOCKER: NONE
SCOPE: PASS
FINAL_VERDICT: PASS_STUDENT_V01_JOB07_R2_READY_FOR_G3
```
