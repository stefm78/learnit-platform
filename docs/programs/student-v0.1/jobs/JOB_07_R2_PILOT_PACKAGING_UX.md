# /AUDIT /SOLVE /BUILD — JOB 07 R2
## Student V0.1 — deterministic pilot packaging with canonical generated qualification kit

Repository: `stefm78/learnit-platform`  
Authority issue: `#417`  
Wave 2 control freeze: `#403`  
Served-V4 repair: `#410 / PR #411`  
Independent contradictory QA PASS: `#412 / PR #413`  
JOB07 R1 qualification-input HOLD: `#415 / PR #416`  
Work package: `ATLAS-WP-040`

Branch:

`student-v01/wave2-pilot-package-r2`

Exact anchors:

- `JOB07_R2_BASE = 7c13d67a76705b4452304c0f6a882504bc7701a7`
- `REPAIRED_PRODUCT_SHA = bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- `JOB05_R1_RESULT_SHA = 1c92cad7ea576a613b6f198768bbebd114a06082`
- `JOB05_R1_EVIDENCE_HEAD = 9dbd5c97603be864a57cc0f7f46047ee41772b34`
- `JOB07_R1_RESULT_SHA = 87a851051bdf80d6e9edb097130521a96df4038a`
- `JOB07_R1_EVIDENCE_HEAD = 704b4588547bc4ca8af6f85ecbf0004e34b8a03f`

Canonical qualification generator:

- path: `authoring/v4/tests/test_validate_v4.py`
- required Git blob: `85debca78c3ec342d9e4e7ed63a033fd0968e72e`
- function: `make_valid_v4()`

Rejected R1 qualification input:

- path: `apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`
- Git blob: `943944eaee6944529810acffc06e61affc71f909`
- status for R2: **read-only historical runtime fixture; do not use as canonical packaging qualification input**

Expected repaired application:

- bytes: `478657`
- SHA256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Role and purpose

You are the Student V0.1 pilot-packaging owner.

R1 stopped correctly because the Control Room had mandated the wrong qualification input: a runtime fixture that is structurally rich but intentionally does not satisfy current canonical V4 authoring admissibility.

That R1 HOLD is accepted.

R2 corrects **only the qualification-input authority**.

Your job is now to complete the original pilot-packaging mission around the exact repaired product.

You may build packaging code, learner-start material, a deterministic package builder, package tests, packaged-browser qualification and bounded CI routing.

You may not repair product code, authoring, validators, schema, runtime fixture, QA, or showcase content.

If a genuine product defect appears during packaged use, stop with a reproducible HOLD. Do not widen scope.

---

## 1. Fresh authority rebind

Before mutation:

1. fresh-read active Human Control Plane HEAD;
2. bind exact UCP/UAO/governance authority;
3. fresh-read repository `main`;
4. verify PR #411 is open/DRAFT/unmerged at exact evidence head `7c13d67a76705b4452304c0f6a882504bc7701a7`;
5. verify repaired executable product `bdb66bffefd6738e3cb4004d304159e9d3d048ce` remains the accepted product anchor;
6. verify JOB05 R1 durable PASS from #412 / PR #413 at exact result/evidence SHAs above;
7. read JOB07 R1 issue #415, PR #416 and `qualification/STUDENT_V01_JOB07_R1_PILOT_RESULT.md`;
8. read issue #417 and `work-packages/ATLAS-WP-040.json`;
9. verify this R2 branch descends exactly from `JOB07_R2_BASE`;
10. verify it does **not** inherit R1 implementation/workflow/evidence commits;
11. verify no JOB05 R1 QA files and no JOB06 showcase files are present in the R2 delta.

Read without editing:

- `authoring/v4/tests/test_validate_v4.py`
- `authoring/v4/validate_kit.py`
- `contracts/learnit-kit-v4.schema.json`
- `apps/learnit-next/build.py`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/index.template.html`
- `apps/learnit-next/src/main.js`
- `apps/learnit-next/src/ui/render.js`
- repaired served-V4 tests and relevant Student V0.1 regressions.

---

## 2. /audit — prove the R1 HOLD classification before proceeding

Reproduce the R1 input contradiction without changing anything:

- verify the rejected runtime fixture blob is exactly `943944eaee6944529810acffc06e61affc71f909`;
- run canonical V4 validation against it;
- require the known lesson-body admissibility failure or an equivalently specific current failure;
- verify the repaired product's served-V4 regressions still pass independently.

Then verify the replacement qualification authority:

- `authoring/v4/tests/test_validate_v4.py` blob is exactly `85debca78c3ec342d9e4e7ed63a033fd0968e72e`;
- run the unchanged representative canonical V4 test that exercises `make_valid_v4()`;
- require PASS.

If either authority blob has drifted, stop:

`HOLD_STUDENT_V01_JOB07_R2_AUTHORITY_DRIFT`

Do not silently choose a substitute generator.

---

## 3. Materialize the canonical ephemeral qualification kit

The qualification kit is generated only for R2 qualification.

It is not committed as product content and is not the eventual pilot showcase.

Materialize it into a temporary/output directory by importing the exact bound:

`authoring.v4.tests.test_validate_v4.make_valid_v4`

Use the returned package object unchanged.

Serialize the generated package deterministically as UTF-8 JSON using exactly:

- `ensure_ascii=False`
- `sort_keys=True`
- `separators=(",", ":")`
- one final `\n`

Record:

- generator path;
- generator Git blob;
- generated JSON byte count;
- generated JSON SHA256;
- package revision digest;
- course revision digest;
- ordered activity family sequence;
- asset count/media-reference count.

Require the activity sequence to be:

`lesson, flashcard, matching, order, classify, qcm, fill, constructed`

Require at least one safe local SVG asset.

Then run the canonical command on the exact serialized file:

`python -B authoring/v4/validate_kit.py <generated-kit> --format=json`

Require PASS before any packaging implementation proceeds.

### Critical boundary

The package builder created later must **not** import `make_valid_v4()`.

The generator is qualification-input authority only.

The package builder must accept an arbitrary explicit canonical V4 JSON file.

---

## 4. Re-prove exact repaired application identity

Before packaging implementation, run the canonical Learn-it Next build twice.

Require both outputs to match each other and exactly:

```text
bytes   478657
sha256  85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e
```

If not:

`HOLD_STUDENT_V01_JOB07_R2_BUILD_DRIFT`

A pilot-only branch may not change product bytes.

---

## 5. Re-prove old blocker closure with the generated kit

Before writing the package builder, use the actual repaired build and the generated canonical kit.

Through the real browser/product controls:

1. import the generated kit;
2. start the course;
3. verify the first rich unit renders correctly;
4. advance far enough to prove the old qcm/fill-only served blocker is absent.

This is a short prerequisite probe, not the final packaged journey.

If the old blocker returns:

`HOLD_STUDENT_V01_JOB07_R2_PRODUCT_BLOCKS_PILOT`

Do not wrap a broken product.

---

## 6. /solve — choose the minimum pilot package contract

Write the chosen design into final qualification evidence before implementation.

The package builder must accept exactly two logical content inputs:

1. an explicit built Learn-it Next HTML file;
2. an explicit canonical V4 kit JSON file.

Preferred bounded archive:

```text
student-v01-pilot/
  START_HERE.html
  learnit-next.html
  course.learnit.json
  pilot_manifest.json
  [optional serve_local.py only if direct file mode is not viable]
```

The builder itself should be a small standard-library Python program under:

`pilot/student-v0.1/**`

Suggested interface:

```text
python -B pilot/student-v0.1/build_pilot_package.py \
  --app <learnit-next.html> \
  --kit <canonical-v4.json> \
  --output <pilot.zip>
```

The builder must validate the V4 kit before packaging, either by invoking the existing canonical validator as a subprocess or by calling its stable public validation entry point without modifying it.

The package contract is packaging metadata only. Do not introduce a new Learn-it product contract.

---

## 7. Deterministic manifest

Create deterministic `pilot_manifest.json`.

Minimum fields:

- `schema`: a bounded packaging identifier such as `student.v0.1.pilot-package.v1`;
- app filename;
- app bytes;
- app SHA256;
- kit filename;
- kit bytes;
- kit SHA256;
- kit contract identifier;
- start filename;
- package-builder version;
- explicit local/offline declaration.

Forbidden deterministic-output fields:

- wall-clock timestamps;
- random IDs;
- absolute paths;
- machine/user names;
- environment-specific temporary paths.

Serialize manifest deterministically.

---

## 8. Deterministic archive

The same app+kit inputs must produce byte-identical package output.

Requirements:

- stable sorted entry order;
- fixed ZIP timestamp;
- fixed Unix permissions/external attributes;
- fixed compression policy;
- no host-dependent comments/extra metadata;
- deterministic generated text bytes.

For this small pilot package, `ZIP_STORED` is acceptable and preferred if it makes byte identity easier to prove.

Build the package twice in independent temporary directories.

Require exact same:

- byte count;
- SHA256;
- entry names;
- entry order;
- per-entry bytes;
- per-entry ZIP metadata.

Do not commit generated ZIP binaries.

---

## 9. Package integrity

Extract a generated package into a clean temporary directory.

Verify:

- packaged app bytes exactly equal repaired app input;
- packaged kit bytes exactly equal generated canonical kit input;
- manifest app/kit byte counts and SHA256 match the extracted files;
- `START_HERE.html` references local resources only;
- no unexpected file exists;
- no debug dump/answer-key file is added;
- no path traversal/archive escape is possible.

Changing the kit filename is allowed only if the bytes remain identical and manifest binding is exact.

---

## 10. Learner START_HERE

Create deterministic learner-facing instructions.

Clearly separate:

### Learner

Actions the learner performs from START_HERE until the course is started.

### Facilitator/setup

Actions required before handing control to the learner.

### Recovery

How to recover from:

- wrong/invalid JSON selection;
- canceled chooser;
- return to library;
- local reset/re-import.

Do not claim:

- account recovery;
- cloud sync;
- cross-device resume.

### Honest learner action count

Measure the actual action count from opening `START_HERE.html` through the product's successful course start.

Count mandatory browser interactions honestly, including chooser/selection/import actions.

Do not reduce the metric with product modification or auto-import.

Record exact action names and total.

---

## 11. Direct-file versus loopback mode

The package must state the start mode it actually supports.

Test direct local-file usage first.

### DIRECT_FILE

If the documented learner path works from extracted local files with the required browser persistence/import behavior, qualify it.

### LOOPBACK_LOCAL

If browser origin/storage restrictions make direct-file use unreliable, you may package a minimal standard-library-only local server helper.

If used:

- bind only `127.0.0.1`;
- serve only the extracted package directory;
- no remote request or package download;
- make start/stop explicit;
- classify launching the helper as facilitator/setup work;
- do not hide setup complexity in learner action count.

### BOTH

Use only if both modes are actually executed and pass.

Never document direct-file while qualifying only loopback.

Record exactly:

`START_MODE = DIRECT_FILE | LOOPBACK_LOCAL | BOTH`

If neither works without product modification:

`HOLD_STUDENT_V01_JOB07_R2_PACKAGING_NEEDS_REWORK`

---

## 12. Real packaged learner journey

This is the primary PASS authority.

Use an **extracted generated package**, not the source-tree app.

Use the documented start mode.

From clean browser storage:

1. open START_HERE;
2. follow its learner instructions;
3. open packaged Learn-it;
4. use the real file chooser;
5. select packaged `course.learnit.json`;
6. import;
7. start the course;
8. traverse all eight activity families through visible controls;
9. use QA-driver answer authority out-of-band only;
10. reload after at least one non-scored unit;
11. resume and verify correct next incomplete unit;
12. reload after at least one scored unit;
13. resume again;
14. continue to full completion;
15. return to library/progress;
16. reload/reopen and verify coherent completion state.

Do not use internal runtime methods to bypass the learner flow.

---

## 13. Desktop and mobile

Run the complete packaged journey independently at:

- desktop: about `1365x768`;
- mobile: about `390x844`.

Require:

- START_HERE usable;
- import/start controls usable;
- all rich controls usable;
- no blocking horizontal overflow;
- reload/resume works;
- completion visible.

Desktop-only cannot PASS.

---

## 14. Offline/no-remote proof

Observe browser requests through:

- START_HERE;
- app open;
- import;
- start;
- media;
- activity interaction;
- reload/resume;
- completion.

Allow only:

- documented local file/loopback origin;
- legitimate local `data:` / `blob:` use.

No external HTTP(S) request is allowed.

Statically inspect packaged files for remote scripts, styles, fonts, images or URLs.

The package must work without internet access.

---

## 15. Learner secret boundary

The canonical JSON file contains scoring authority by design.

Do not claim file-level secrecy.

During packaged learner interaction, recursively scan learner-bound presentation/runtime objects and rendered DOM/attributes for:

- `correctChoiceId`
- authored fill `answers`
- `acceptedResponses`
- matching `matches`
- `correctOrder`
- classify authored `assignments`

Require absence.

Packaging may not add answer-key/debug files.

---

## 16. Recovery

Execute, not just document:

- invalid/non-V4 JSON selection and fail-closed recovery;
- canceled/aborted chooser then retry;
- return to library then continue;
- local reset followed by clean re-import/start.

Record observed behavior.

Packaging must not make recovery harder than the underlying product.

---

## 17. Regression matrix

Run unchanged, at minimum:

- canonical app build;
- `apps/learnit-next/tests/student_v01_served_v4_integration.py`;
- `apps/learnit-next/tests/browser_student_v01_served_v4_integration.py`;
- `apps/learnit-next/tests/student_v01_learning_runtime.py -v`;
- `apps/learnit-next/tests/student_v01_activity_presentation.py`;
- `apps/learnit-next/tests/browser_student_v01_activity_presentation.py`;
- `apps/learnit-next/tests/student_v01_fanin_a.py`;
- canonical V4 validator tests;
- relevant Atlas qcm/fill regressions used by the repair.

Also run new R2 package unit/static/browser tests.

JOB05 R1 PASS is prerequisite evidence only; it does not replace R2 execution.

---

## 18. Exact-head CI

Final PASS requires exact-head CI.

Authoritative R2 PR is stacked on:

`student-v01/served-v4-integration`

Add only the minimum route in:

`.github/workflows/learnit-next-ci.yml`

for:

`student-v01/wave2-pilot-package-r2`

The route must:

- be PR-only;
- bind exact ancestry to `JOB07_R2_BASE`;
- require remote branch HEAD = tested target;
- verify canonical generator blob;
- generate+validate the ephemeral qualification kit;
- prove repaired app identity;
- prove package determinism/integrity;
- execute packaged desktop/mobile browser qualification;
- execute repaired-product regressions;
- preserve existing routes unchanged.

If stacked topology does not trigger, a temporary DRAFT carrier from the exact same R2 branch HEAD to `main` may be used only for CI transport.

Carrier rules:

- non-authoritative;
- never merged;
- close after durable evidence;
- carrier-specific PR-scope failure must not be presented as authoritative R2 scope.

Do not claim `INTEGRATION_CI: PASS` from local-only evidence.

---

## 19. Scope audit

Exact `JOB07_R2_BASE..RESULT_SHA` may change only:

- `work-packages/ATLAS-WP-040.json`
- `docs/programs/student-v0.1/jobs/JOB_07_R2_PILOT_PACKAGING_UX.md`
- `pilot/student-v0.1/**`
- `.github/workflows/learnit-next-ci.yml`

Then evidence-only:

- `qualification/STUDENT_V01_JOB07_R2_PILOT_RESULT.md`

Forbidden includes all product source/tests/build/manifest, authoring, contract, architecture, QA, showcase, governance and earlier WP files.

Any forbidden-path mutation is scope FAIL.

---

## 20. RESULT_SHA versus EVIDENCE_HEAD

Separate:

- `RESULT_SHA`: exact tested executable packaging/QA/CI head;
- `EVIDENCE_HEAD`: later commit(s) changing only qualification evidence.

Create:

`qualification/STUDENT_V01_JOB07_R2_PILOT_RESULT.md`

Record:

- fresh HCP binding;
- exact ancestry and prerequisite anchors;
- R1 failure reproduction/classification;
- canonical generator blob;
- generated kit bytes/SHA256 and canonical validation;
- repaired app bytes/SHA256;
- package design/start mode;
- manifest;
- package bytes/SHA256 from two builds;
- archive metadata proof;
- extracted integrity;
- learner action sequence/count;
- packaged desktop/mobile journey;
- reload/resume/completion;
- offline network observations;
- secret-boundary scan;
- recovery results;
- regression commands/results;
- CI run/job IDs;
- carrier identity/closure if any;
- exact changed paths;
- rollback.

---

## 21. PASS gate

PASS requires all independently executed:

- R1 input contradiction correctly reproduced/classified;
- canonical generator identity PASS;
- generated qualification kit canonical PASS;
- all-eight-family + safe media input PASS;
- repaired app identity PASS;
- old blocker closed on generated kit;
- package manifest binding PASS;
- package determinism PASS;
- package integrity PASS;
- documented start mode PASS;
- learner instructions PASS;
- learner action count recorded honestly;
- offline/no-remote PASS;
- real extracted-package rich-V4 journey PASS;
- desktop PASS;
- mobile PASS;
- reload/resume PASS;
- completion PASS;
- recovery PASS;
- learner secret boundary PASS;
- repaired-product regressions PASS;
- Repository governance PASS;
- authoritative PR scope PASS;
- exact integration CI PASS;
- scope PASS.

PASS authorizes only Control Room G3 review of:

- accepted JOB05 R1;
- frozen JOB06;
- JOB07 R2.

It does not authorize JOB08, main merge, release promotion or real students.

---

## 22. Final result block

Return exactly:

```text
STUDENT_V01_JOB07_R2_RESULT
JOB07_R2_BASE: 7c13d67a76705b4452304c0f6a882504bc7701a7
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
JOB05_R1_RESULT_SHA: 1c92cad7ea576a613b6f198768bbebd114a06082
JOB07_R1_RESULT_SHA: 87a851051bdf80d6e9edb097130521a96df4038a
CANONICAL_GENERATOR_BLOB: 85debca78c3ec342d9e4e7ed63a033fd0968e72e
GENERATED_KIT_SHA256: <sha256>
GENERATED_KIT_BYTES: <integer>
RESULT_SHA: <exact tested packaging head>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 417
PR: <authoritative pr number>
R1_INPUT_CONTRADICTION: PASS|FAIL|BLOCKED
CANONICAL_GENERATOR_IDENTITY: PASS|FAIL|BLOCKED
GENERATED_KIT_CANONICAL: PASS|FAIL|BLOCKED
REPAIRED_APP_IDENTITY: PASS|FAIL|BLOCKED
OLD_BLOCKER_CLOSED: PASS|FAIL|BLOCKED
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

Allowed verdicts:

- `PASS_STUDENT_V01_JOB07_R2_READY_FOR_G3`
- `HOLD_STUDENT_V01_JOB07_R2_AUTHORITY_DRIFT`
- `HOLD_STUDENT_V01_JOB07_R2_BUILD_DRIFT`
- `HOLD_STUDENT_V01_JOB07_R2_PRODUCT_BLOCKS_PILOT`
- `HOLD_STUDENT_V01_JOB07_R2_PACKAGING_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB07_R2_SCOPE_VIOLATION`
