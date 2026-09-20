# Student V0.1 — JOB07 R1 Pilot Packaging / Learner-start UX Result

**Status:** HOLD — QUALIFICATION FIXTURE INVALID BEFORE PACKAGING  
**Verdict:** `HOLD_STUDENT_V01_JOB07_R1_PACKAGING_NEEDS_REWORK`  
**Authority:** issue #415 / ATLAS-WP-039  
**Authoritative PR:** #416 (DRAFT, unmerged)  
**RESULT_SHA:** `87a851051bdf80d6e9edb097130521a96df4038a`

## 1. Fresh authority and exact baseline binding

The execution followed the mandated `/refresh -> /audit -> /solve -> /build -> /audit` sequence and revalidated authority before each governed write.

- UCP: `UCP-CONTROL-PLANE 1.1-R4`
- UCP SHA-256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- current Human Control Plane HEAD Git blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- active UAO: `2.6`, SHA-256 `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- JOB07_R1_BASE: `7c13d67a76705b4452304c0f6a882504bc7701a7`
- REPAIRED_PRODUCT_SHA: `bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- JOB05_R1_RESULT_SHA: `1c92cad7ea576a613b6f198768bbebd114a06082`
- JOB05_R1_EVIDENCE_HEAD: `9dbd5c97603be864a57cc0f7f46047ee41772b34`
- repository main observed before execution: `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`

PR #411 remained open/DRAFT/unmerged at exact head `7c13d67a76705b4452304c0f6a882504bc7701a7`.
PR #413 remained open/DRAFT/unmerged at exact evidence head `9dbd5c97603be864a57cc0f7f46047ee41772b34`.
PR #416 remained open/DRAFT/unmerged and based on exact `7c13d67a76705b4452304c0f6a882504bc7701a7`.

The initial JOB07 R1 branch delta contained only the prompt and ATLAS-WP-039. No JOB05 R1 QA file and no JOB06 showcase file was consumed.

## 2. /solve — selected package contract

Before packaging implementation, the selected minimal contract was:

- deterministic `ZIP_STORED` archive;
- fixed, sorted entries:
  - `START_HERE.html`
  - `learnit-next.html`
  - `course.learnit.json`
  - `pilot_manifest.json`
  - a standard-library-only loopback helper only if required by browser-origin behavior;
- canonical JSON manifest with exact app/kit byte counts and SHA-256;
- fixed ZIP timestamps and permissions;
- no random IDs, timestamps, machine paths, machine names or remote resources;
- explicit learner/setup/recovery instructions;
- direct-file mode to be tested first, with loopback-only `127.0.0.1` fallback.

This decision was not implemented because the mandatory qualification fixture failed the pre-packaging canonical-validation gate.

## 3. Exact repaired application identity — PASS

Exact-head CI built Learn-it Next twice before any `pilot/**` implementation existed.

Both artifacts were byte-identical and exactly matched the frozen repaired identity:

- bytes: `478657`
- SHA-256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Marker:

`STUDENT_V01_JOB07_R1_REPAIRED_APP_IDENTITY=PASS`

Therefore this execution is not a build-drift HOLD.

## 4. Mandatory qualification fixture — FAIL

The job mandates canonical V4 validation of:

`apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`

The exact fixture Git blob is:

`943944eaee6944529810acffc06e61affc71f909`

The exact canonical validator Git blob is:

`4ef561dfc1137aa436b4d8c8820db421ab6e1861`

Both blobs are unchanged between JOB07_R1_BASE and RESULT_SHA.

Canonical command:

`python -B authoring/v4/validate_kit.py apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json --format=json`

Observed result: exit 1 / FAIL.

Exact discriminating error:

`$.courses[0].activities[3].body: lesson body is too small to be substantive learner-facing exposition; value="Corps de leçon"`

The canonical validator requires a lesson body to contain at least 40 trimmed characters and at least 6 words. The frozen fixture does not satisfy that requirement.

The same validator output confirms that the fixture structurally contains all eight required families and one local SVG asset, and all declared revision digests match. The failure is specifically the canonical lesson-content admissibility rule.

Marker:

`STUDENT_V01_JOB07_R1_RICH_V4_FIXTURE=FAIL`

Because section 2.B of JOB07 R1 says **Require PASS** before packaging, substituting a different kit, modifying the fixture, weakening the validator, or proceeding with a wrapper would violate the job.

## 5. Old product blocker closure — PASS

A second exact-head diagnostic route deliberately preserved the canonical-fixture failure while continuing only read-only product probes, so the failure could be classified correctly.

On RESULT_SHA:

- repaired served-V4 static integration: PASS;
- repaired served-V4 real Chromium journey: PASS;
- `REAL_SERVED_V4_JOURNEY=PASS`;
- `COMPLETION=PASS`;
- `DESKTOP=PASS`;
- `MOBILE=PASS`;
- learner-secret boundary and local-media assertions inside the unchanged browser oracle passed;
- no external request accepted by that oracle;
- `STUDENT_V01_JOB07_R1_OLD_BLOCKER_CLOSED=PASS`.

Therefore the old Atlas/served-session product blocker does not reproduce. The current HOLD is not classified as a product defect.

## 6. Packaging stop condition

No `pilot/student-v0.1/**` implementation was created.

Consequently, none of the following is claimed as qualified:

- deterministic pilot ZIP;
- pilot manifest binding;
- extracted-package integrity;
- START_HERE learner journey;
- direct-file versus loopback package start mode;
- packaged desktop/mobile journey;
- packaged reload/resume/completion/recovery;
- packaged offline/no-remote proof;
- packaged learner-secret scan;
- full package regression matrix.

`LEARNER_START_ACTIONS=0` in the final machine block means **no learner-start action was executed because packaging was blocked before creation**. It is not an estimate of the future package UX.

## 7. CI and repository evidence

First preflight route:
- Learn-it Next CI run id: `35520788442`
- run number: `626`
- result: failure at the mandatory canonical fixture validation, after exact double-build PASS.

Final diagnostic RESULT_SHA route:
- Learn-it Next CI run id: `35520903483`
- run number: `627`
- exact routed job id: `106104698483`
- result: expected failure after collecting both:
  - canonical fixture FAIL;
  - repaired real served product journey PASS.

Repository governance on RESULT_SHA:
- run id: `35520903471`
- run number: `1206`
- `validate-repository`: success
- mirrored `Repository governance`: success

`INTEGRATION_CI=FAIL` is retained because the mandatory exact-head JOB07 R1 route cannot pass while its required fixture is canonically invalid.

## 8. Exact scope

Exact `JOB07_R1_BASE..RESULT_SHA` changed paths:

- `.github/workflows/learnit-next-ci.yml`
- `docs/programs/student-v0.1/jobs/JOB_07_R1_PILOT_PACKAGING_UX.md`
- `work-packages/ATLAS-WP-039.json`

All are allowed by ATLAS-WP-039. There is no product source, product test, source manifest, contract, architecture, authoring, showcase, QA, governance or tool mutation.

Scope: **PASS**.

## 9. False-PASS / false-FAIL challenge

False-PASS challenge:

- exact application identity and repaired runtime success cannot compensate for a mandatory qualification fixture that the canonical V4 validator rejects;
- JOB05 R1 PASS cannot substitute for the explicit JOB07 R1 fixture gate;
- changing or silently replacing the fixture would cross the frozen test-input boundary;
- no package field is promoted to PASS without an extracted-package execution.

False-FAIL challenge:

- the validator rule and the failing fixture are byte-identical to the authorized JOB07 R1 base;
- the failure reproduces in exact-head CI;
- revision digests and rich-family structure are otherwise intact;
- the repaired product itself passes the real served journey on the same RESULT_SHA;
- therefore the HOLD is narrowly attributable to the JOB07 R1 qualification-input contradiction, not to build drift or a product regression.

## 10. Rollback / safe resume

Rollback is bounded:

1. close PR #416 without merge and delete `student-v01/wave2-pilot-package-r1`; or
2. revert the two JOB07 R1 workflow-only diagnostic commits.

No product artifact, JOB05 R1 evidence, frozen JOB06 state, contract, authoring rule or main branch state was changed.

Safe resume requires an explicit Control Room correction that makes the JOB07 R1 qualification input and its mandated canonical validator mutually consistent. After that correction, restart from the exact pre-packaging prerequisite checks. Do not reuse this HOLD as a PASS.

```text
STUDENT_V01_JOB07_R1_RESULT
JOB07_R1_BASE: 7c13d67a76705b4452304c0f6a882504bc7701a7
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
JOB05_R1_RESULT_SHA: 1c92cad7ea576a613b6f198768bbebd114a06082
RESULT_SHA: 87a851051bdf80d6e9edb097130521a96df4038a
EVIDENCE_HEAD: THIS_EVIDENCE_ONLY_COMMIT
ISSUE: 415
PR: 416
REPAIRED_APP_IDENTITY: PASS
RICH_V4_FIXTURE: FAIL
PACKAGE_MANIFEST_BINDING: BLOCKED
PACKAGE_DETERMINISM: BLOCKED
PACKAGE_INTEGRITY: BLOCKED
START_MODE: UNRESOLVED
LEARNER_START_INSTRUCTIONS: BLOCKED
LEARNER_START_ACTIONS: 0
OFFLINE_NO_REMOTE: BLOCKED
REAL_PACKAGED_V4_JOURNEY: BLOCKED
DESKTOP: BLOCKED
MOBILE: BLOCKED
RELOAD_RESUME: BLOCKED
COMPLETION: BLOCKED
RECOVERY: BLOCKED
SECRET_BOUNDARY: BLOCKED
REPAIRED_PRODUCT_REGRESSION: BLOCKED
REPOSITORY_GOVERNANCE: PASS
PR_SCOPE: PASS
INTEGRATION_CI: FAIL
PRODUCT_BLOCKER: NONE
SCOPE: PASS
FINAL_VERDICT: HOLD_STUDENT_V01_JOB07_R1_PACKAGING_NEEDS_REWORK
```
