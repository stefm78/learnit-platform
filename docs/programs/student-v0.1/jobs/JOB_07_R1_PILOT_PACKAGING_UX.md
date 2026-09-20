# /AUDIT /SOLVE /BUILD — JOB 07 R1
## Student V0.1 — deterministic pilot packaging after served-V4 repair

Repository: `stefm78/learnit-platform`  
Authority issue: `#415`  
Wave 2 control freeze: `#403`  
Served-V4 repair: `#410 / PR #411`  
Independent contradictory QA gate: `#412 / PR #413`  
Work package: `ATLAS-WP-039`

Branch:

`student-v01/wave2-pilot-package-r1`

Exact anchors:

- `JOB07_R1_BASE = 7c13d67a76705b4452304c0f6a882504bc7701a7`
- `REPAIRED_PRODUCT_SHA = bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- `JOB05_R1_RESULT_SHA = 1c92cad7ea576a613b6f198768bbebd114a06082`
- `JOB05_R1_EVIDENCE_HEAD = 9dbd5c97603be864a57cc0f7f46047ee41772b34`
- `PRE_REPAIR_JOB07_RESULT = 3f9798dd11edea4dcc95c959aacb0a6790d2bfc1`
- expected repaired application:
  - bytes: `478657`
  - SHA256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Qualification fixture:

`apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Role

You are the pilot-packaging owner.

The product is already repaired and has independently survived JOB05 R1 contradictory QA.

Your job is now to answer a different question:

> Can the exact repaired application and an arbitrary canonical V4 kit be handed to a controlled pilot learner in a deterministic, local/offline package with a clear start path, honest action count, reliable resume/completion, and no hidden product fork?

You own packaging, start instructions, package validation, browser packaging smoke and evidence only.

You do **not** own product repair.

If packaged use reveals a product defect, stop with a reproducible HOLD. Do not mutate product source.

---

## 1. Fresh authority rebind

Before any mutation:

1. fresh-read active Human Control Plane HEAD and bind exact UCP/UAO/governance authority;
2. fresh-read repository `main`;
3. verify PR #411 remains DRAFT/unmerged and still binds:
   - executable repaired product `bdb66bffefd6738e3cb4004d304159e9d3d048ce`;
   - evidence head `7c13d67a76705b4452304c0f6a882504bc7701a7`;
4. verify JOB05 R1 durable PASS from issue #412 / PR #413 and exact result/evidence SHAs above;
5. read initial JOB07 issue #406 / PR #409 and `qualification/STUDENT_V01_JOB07_PILOT_RESULT.md` as historical blocker evidence;
6. read issue #415 and `work-packages/ATLAS-WP-039.json`;
7. verify this branch descends exactly from `JOB07_R1_BASE`;
8. verify no JOB05 R1 QA files or JOB06 showcase files have been cherry-picked into this branch.

Read, without editing:

- `apps/learnit-next/build.py`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/index.template.html`
- `apps/learnit-next/src/main.js`
- `apps/learnit-next/src/ui/render.js`
- `contracts/learnit-kit-v4.schema.json`
- `authoring/v4/validate_kit.py`
- repaired served-V4 tests;
- qualification fixture named above.

Do not trust historical JOB07's blocker as still current. Re-prove the repaired start path before packaging.

---

## 2. Re-prove the prerequisite product state

Before implementing packaging:

### A. Exact app identity

Build Learn-it Next twice from this branch before adding any pilot implementation.

Because pilot files are not product build inputs, both builds must match the repaired artifact exactly:

```text
bytes   478657
sha256  85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e
```

If not, stop with:

`HOLD_STUDENT_V01_JOB07_R1_BUILD_DRIFT`

### B. Qualification fixture

Run the canonical V4 validator against:

`apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`

Require PASS.

Verify it exercises the rich family set and local media needed for pilot smoke.

### C. Old blocker closure

Using the actual repaired build, perform a short pre-packaging browser probe:

- import the qualification fixture using the real file input;
- start the course using the real learner action;
- prove the first rich family renders through the repaired served path;
- prove the course can advance at least beyond the old first-activity blocker.

If the old structural blocker still reproduces, stop:

`HOLD_STUDENT_V01_JOB07_R1_PRODUCT_BLOCKS_PILOT`

Do not build a wrapper around a broken product.

---

## 3. /solve — choose the smallest pilot contract

Before coding, write the chosen package contract into the eventual qualification evidence.

The package builder must be generic and accept two explicit inputs:

1. exact built Learn-it Next HTML;
2. one canonical `learnit.kit.v4` JSON file.

The preferred minimal package contents are conceptually:

```text
student-v01-pilot/
  START_HERE.html
  learnit-next.html
  course.learnit.json
  pilot_manifest.json
  [optional minimal facilitator/local-start helper only if proven necessary]
```

Names may differ slightly if justified, but the package must remain obvious and bounded.

### Package manifest minimum

Use a small explicit schema, for example `student.v0.1.pilot-package.v1`, containing at least:

- package schema/version;
- app filename;
- app byte count;
- app SHA256;
- kit filename;
- kit byte count;
- kit SHA256;
- kit contract identifier;
- deterministic package-builder version;
- start surface filename;
- explicit offline/no-remote declaration.

Do not put wall-clock timestamps, random IDs, absolute paths, machine names or environment-specific data into deterministic output.

The manifest is packaging metadata, not a new product contract.

---

## 4. Deterministic package builder

Implement under:

`pilot/student-v0.1/**`

Create a small deterministic builder, preferably:

`pilot/student-v0.1/build_pilot_package.py`

It must:

1. take explicit `--app`, `--kit`, `--output` inputs;
2. reject a kit that is not canonical valid V4;
3. bind exact app and kit bytes/SHA256;
4. generate deterministic `START_HERE.html`;
5. generate canonical deterministic manifest JSON;
6. write archive entries in a stable sorted order;
7. use fixed archive metadata/timestamps and fixed permissions;
8. avoid non-deterministic compressor metadata.

For a package this small, ZIP_STORED with fixed ZIP metadata is acceptable and preferred if it simplifies cross-run byte determinism.

Reject unsafe output paths/path traversal.

Do not commit generated ZIP binaries. Generate them in temporary/output directories during qualification.

---

## 5. START_HERE and learner instructions

The start surface must be understandable without repository knowledge.

It must clearly distinguish:

### Learner actions

Actual clicks/selections from opening `START_HERE.html` until the course is started.

### Facilitator/setup actions

For example:

- unpack archive;
- if absolutely necessary, start a local loopback-only static server.

### Recovery/reset actions

How to:

- return to library;
- reselect the bundled kit if needed;
- recover from an invalid file;
- reset local Learn-it data.

Do not claim account recovery, cloud sync or cross-device resume.

### Honest action count

Measure the actual learner action count.

Mandatory steps such as:

- opening Learn-it;
- showing library if required;
- opening the file chooser;
- selecting the bundled kit;
- importing;
- starting the course

must not be hidden from the count.

The initial JOB07 historical plan estimated seven learner actions. Treat that as a comparison point, not as authority. Report the real R1 count.

If packaging itself adds unnecessary learner friction beyond the current product path, improve the packaging within scope.

Do not change product code to optimize the metric.

---

## 6. Direct-file versus loopback start mode

The pilot package is local/offline, but browser origin behavior matters.

Test the start mode promised by the learner instructions.

### First preference

Try the unpacked package directly from local files:

`START_HERE.html -> learnit-next.html`

and determine whether the browser/product features required for import, IndexedDB persistence and resume work correctly.

### If direct file mode is not viable

You may add one minimal optional local helper under `pilot/student-v0.1/**` using standard-library-only code to serve the unpacked directory on `127.0.0.1`.

If used:

- it is facilitator/setup tooling, not product architecture;
- it must bind loopback only;
- it must make no remote network request;
- start/stop instructions must be explicit;
- learner action count starts from the learner-facing START_HERE surface after facilitator setup;
- the package must still work with no internet connection.

Do not silently qualify under loopback while instructing learners to use file://.

Record:

`START_MODE = DIRECT_FILE | LOOPBACK_LOCAL | BOTH`

If neither mode provides a coherent controlled-pilot start without product modification, return packaging HOLD.

---

## 7. Package integrity qualification

Build the pilot package twice from the exact same app/kit inputs.

Require exact equality:

- package bytes;
- package SHA256.

Extract both packages and compare:

- entry names;
- entry order;
- entry bytes;
- timestamps/metadata;
- permissions where relevant.

Then verify:

- app bytes inside package exactly equal the repaired app artifact;
- kit bytes inside package exactly equal the qualification fixture input;
- manifest hashes/byte counts exactly match extracted bytes;
- START_HERE references only packaged/local resources;
- no extra answer-key/debug file exists.

Any mismatch is a packaging FAIL.

---

## 8. Real packaged learner journey

This is the primary pilot readiness proof.

Do not test a source-tree app while claiming package PASS.

Use an **extracted package** and the exact documented start mode.

From clean browser state:

1. open `START_HERE`;
2. follow the written learner path exactly;
3. open Learn-it;
4. use the real file chooser;
5. select the packaged kit file;
6. import;
7. start the course;
8. interact with the real learner controls through the rich journey;
9. reload while incomplete;
10. resume;
11. continue to completion;
12. return to library/progress surface.

Automation may programmatically select a file for browser control, but the reported learner action count must count the corresponding manual chooser/selection actions.

Do not call internal runtime APIs to bypass the learner flow.

---

## 9. Desktop and mobile

Run the packaged critical journey independently at least at:

- desktop about `1365x768`;
- mobile about `390x844`.

Require:

- START_HERE readable/usable;
- import/start controls usable;
- rich activity controls usable;
- no horizontal layout break that prevents interaction;
- reload/resume works;
- completion is observable.

A desktop-only PASS is insufficient.

---

## 10. Offline/no-remote proof

Observe browser requests during:

- START_HERE;
- app open;
- import/start;
- media rendering;
- reload/resume;
- completion.

Allow only the chosen local origin plus data/blob URLs that are already legitimate product behavior.

No external HTTP(S) request is allowed.

Also inspect START_HERE/package files for remote scripts, fonts, stylesheets, images or URLs.

Do not require internet access for any pilot step.

---

## 11. Learner secret boundary in packaged use

The packaged canonical kit contains scoring authority by design.

Do not claim file-level secrecy.

During real learner interaction, independently scan the learner-bound runtime/presentation and rendered DOM for forbidden scoring authority:

- `correctChoiceId`
- authored fill `answers`
- `acceptedResponses`
- matching `matches`
- `correctOrder`
- classify authored `assignments`

Require absence during packaged use.

No extra debug/answer artifact may be added by packaging.

---

## 12. Reload/resume/completion and recovery

At minimum prove:

### Reload/resume

Reload once after a non-scored unit and once after a scored unit.

Require return to the correct next incomplete activity.

### Completion

Complete the full fixture and verify the product's completion/progress state after reload/reopen.

### Recovery

Challenge and document:

- selecting an invalid/non-V4 JSON file;
- canceling/retrying file selection;
- returning to library and continuing;
- local reset and clean re-import.

Packaging must not make recovery harder than the underlying product.

Do not claim cross-device/account recovery.

---

## 13. Regression protection

Run, unchanged, at minimum:

- canonical repaired application build;
- `apps/learnit-next/tests/student_v01_served_v4_integration.py`;
- `apps/learnit-next/tests/browser_student_v01_served_v4_integration.py`;
- relevant Student V0.1/FAN-IN regressions used by the repair;
- Atlas qcm/fill regressions used by the repair.

Also run your own pilot package unit/static tests and packaged browser test.

JOB05 R1 PASS is a prerequisite, not a substitute for this execution.

---

## 14. Exact-head CI

A final PASS requires exact-head CI.

The authoritative R1 PR is stacked on:

`student-v01/served-v4-integration`

Add only the minimum bounded route in:

`.github/workflows/learnit-next-ci.yml`

for:

`student-v01/wave2-pilot-package-r1`

The route must:

- be PR-only;
- bind exact ancestry to `JOB07_R1_BASE`;
- require remote branch HEAD = tested target;
- prove repaired app artifact identity;
- run package determinism/integrity tests;
- run packaged desktop/mobile browser smoke;
- run relevant repaired-product regressions;
- leave existing routes unchanged.

If stacked PR event topology prevents execution, a temporary DRAFT carrier from the exact same branch HEAD to `main` may be used only as CI transport.

It must be clearly marked non-authoritative, never merged, and closed after evidence is durable.

---

## 15. Scope audit

Before final qualification, compare exact `JOB07_R1_BASE..RESULT_SHA`.

Allowed paths are only:

- `work-packages/ATLAS-WP-039.json`
- `docs/programs/student-v0.1/jobs/JOB_07_R1_PILOT_PACKAGING_UX.md`
- `pilot/student-v0.1/**`
- `.github/workflows/learnit-next-ci.yml`
- later evidence-only `qualification/STUDENT_V01_JOB07_R1_PILOT_RESULT.md`

No product source, product tests, source manifest, contract, architecture, authoring, showcase, QA, governance or tool path may change.

---

## 16. Result/evidence separation

Separate:

- `RESULT_SHA`: exact implementation/tested packaging head before evidence-only commit;
- `EVIDENCE_HEAD`: later evidence-only qualification head.

Create:

`qualification/STUDENT_V01_JOB07_R1_PILOT_RESULT.md`

Record at minimum:

- fresh HCP binding;
- repaired product and JOB05 R1 prerequisite binding;
- chosen package contract/start mode;
- exact app/kit/package hashes and byte counts;
- package entry list and deterministic metadata rules;
- actual learner action count;
- direct-file versus loopback results;
- desktop/mobile packaged journey;
- reload/resume/completion/recovery;
- offline network observations;
- learner secret scan;
- all regression commands/results;
- workflow IDs;
- carrier identity/closure if used;
- exact changed paths and rollback.

---

## 17. PASS gate

PASS requires:

- repaired prerequisite identity PASS;
- qualification fixture canonical PASS;
- exact repaired app identity PASS;
- package manifest binding PASS;
- deterministic package PASS;
- extracted package integrity PASS;
- learner start instructions PASS;
- honest measured action count recorded;
- documented start mode works as instructed;
- offline/no-remote PASS;
- real packaged rich-V4 journey PASS;
- desktop PASS;
- mobile PASS;
- reload/resume PASS;
- completion PASS;
- recovery PASS;
- packaged learner secret boundary PASS;
- repaired-product regressions PASS;
- Repository governance PASS;
- authoritative PR scope PASS;
- exact integration CI PASS;
- scope PASS.

PASS authorizes only Control Room G3 review of:

- accepted JOB05 R1;
- frozen JOB06;
- JOB07 R1.

It does not authorize JOB08, merge to main, release promotion or real-student use.

---

## 18. Final result block

Return exactly:

```text
STUDENT_V01_JOB07_R1_RESULT
JOB07_R1_BASE: 7c13d67a76705b4452304c0f6a882504bc7701a7
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
JOB05_R1_RESULT_SHA: 1c92cad7ea576a613b6f198768bbebd114a06082
RESULT_SHA: <exact tested packaging head>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 415
PR: <authoritative pr number>
REPAIRED_APP_IDENTITY: PASS|FAIL|BLOCKED
RICH_V4_FIXTURE: PASS|FAIL|BLOCKED
PACKAGE_MANIFEST_BINDING: PASS|FAIL|BLOCKED
PACKAGE_DETERMINISM: PASS|FAIL|BLOCKED
PACKAGE_INTEGRITY: PASS|FAIL|BLOCKED
START_MODE: DIRECT_FILE|LOOPBACK_LOCAL|BOTH|UNRESOLVED
LEARNER_START_INSTRUCTIONS: PASS|FAIL|BLOCKED
LEARNER_START_ACTIONS: <integer>
OFFLINE_NO_REMOTE: PASS|FAIL|BLOCKED
REAL_PACKAGED_V4_JOURNEY: PASS|FAIL|BLOCKED
DESKTOP: PASS|FAIL|BLOCKED
MOBILE: PASS|FAIL|BLOCKED
RELOAD_RESUME: PASS|FAIL|BLOCKED
COMPLETION: PASS|FAIL|BLOCKED
RECOVERY: PASS|FAIL|BLOCKED
SECRET_BOUNDARY: PASS|FAIL|BLOCKED
REPAIRED_PRODUCT_REGRESSION: PASS|FAIL|BLOCKED
REPOSITORY_GOVERNANCE: PASS|FAIL|BLOCKED
PR_SCOPE: PASS|FAIL|BLOCKED
INTEGRATION_CI: PASS|FAIL|BLOCKED
PRODUCT_BLOCKER: NONE|CONTRACT_IMPORT|LEARNING_SEMANTICS|SERVED_RUNTIME_BOUNDARY|ATLAS_SESSION_INTEGRATION|PRESENTATION_UI|MEDIA|PERSISTENCE|ACCESSIBILITY|BUILD_INTEGRATION|UNKNOWN_NEEDS_CONTROL_ROOM
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_JOB07_R1_READY_FOR_G3`
- `HOLD_STUDENT_V01_JOB07_R1_BUILD_DRIFT`
- `HOLD_STUDENT_V01_JOB07_R1_PRODUCT_BLOCKS_PILOT`
- `HOLD_STUDENT_V01_JOB07_R1_PACKAGING_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB07_R1_SCOPE_VIOLATION`
