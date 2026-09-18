# /AUDIT /SOLVE /BUILD — Student V0.1 served-session V4 integration rework

Repository: `stefm78/learnit-platform`  
Authority issue: `#410`  
Wave 2 control freeze: `#403`  
Work package: `ATLAS-WP-037`

Branch: `student-v01/served-v4-integration`

Exact anchors:

- `REPAIR_BASE = 281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- `QUALIFIED_PRODUCT_BASE = 8fa25844cf9ddf7c2429f730d818b3518c46de04`
- R3 evidence authority: issue #401 / PR #402
- JOB05 HOLD evidence: issue #404 / PR #407
- JOB07 HOLD evidence: issue #406 / PR #409
- frozen JOB06 showcase result: `8e0e3c43968cf0cf442e0e47b73bc38fc19ae565`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Role and stop rule

You are the explicit cross-role **served-session integration repair** worker.

You are authorized to repair only the bounded composition between:

- the already-qualified core session semantics;
- the already-qualified learner-safe ActivityPresentation projection;
- the already-qualified generic activity presenters;
- the actual served classic learner path;
- the Atlas compatibility selector.

You are **not** authorized to redesign any of those authorities.

If the repair requires changing the V4 schema, architecture freeze, core evaluation semantics, generic projection semantics, generic presenters, Atlas session engine, authoring, showcase content, persistence schema or another Wave 2 branch, stop and return HOLD. Do not widen scope.

---

## 1. Fresh authority rebind

Before any mutation:

1. fresh-read the active Human Control Plane HEAD;
2. bind exact UCP/UAO/governance authority;
3. fresh-read repository `main`;
4. verify this branch descends from exact `REPAIR_BASE`;
5. read issues #410, #403, #401, #404 and #406;
6. read PR #402 plus:
   - `qualification/STUDENT_V01_FANIN_A_R3_RESULT.md`;
   - `qualification/STUDENT_V01_JOB05_QA_RESULT.md` from PR #407 branch;
   - `qualification/STUDENT_V01_JOB07_PILOT_RESULT.md` from PR #409 branch;
7. read `work-packages/ATLAS-WP-037.json`;
8. verify JOB06 remains independent/frozen; do not consume its files.

Read the frozen authorities from `REPAIR_BASE`:

- `contracts/learnit-kit-v4.schema.json`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
- `apps/learnit-next/src/core/session.js`
- `apps/learnit-next/src/core/activity_semantics.js`
- `apps/learnit-next/src/integration/atlas/activity_projection.js`
- `apps/learnit-next/src/ui/activity_presenters.js`
- `apps/learnit-next/src/ui/media.js`
- `apps/learnit-next/src/main.js`
- `apps/learnit-next/src/ui/render.js`
- `apps/learnit-next/src/integration/atlas/surface.js`
- `apps/learnit-next/src/integration/atlas/session.js`
- `apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`

No product mutation before the blocker and design are re-derived.

---

## 2. Reproduce the exact product contradiction

Independently prove from the frozen source, not merely from JOB05/JOB07 prose:

### A. Qualified rich seams exist

Prove:

- `projectActivityPresentation()` supports:
  `qcm`, `fill`, `constructed`, `lesson`, `flashcard`, `matching`, `order`, `classify`;
- `renderActivityPresentation()` and `readActivityResponse()` support the same eight families;
- core `evaluateActivityResponse()` / `createSessionService()` already own scored versus non-scored semantics.

### B. Real served route is incomplete

Prove:

- classic `renderSessionSnapshot()` currently chooses qcm or fill rendering rather than the generic presenter seam;
- Atlas `compatibleAtlasCourse()` currently requires `assessmentRole` on every activity;
- conforming V4 lesson/flashcard do not carry `assessmentRole`;
- Atlas session implementation is explicitly qcm/fill-only;
- therefore a valid rich V4 course is not executable end-to-end through the current served learner path.

### C. Existing frozen rich fixture

Verify:

`apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`

contains all eight families and local media and remains valid against current runtime/contract expectations.

If this diagnosis is false, stop:

`HOLD_STUDENT_V01_SERVED_V4_DIAGNOSIS_DRIFT`

with exact observed evidence.

---

## 3. /solve — choose the minimum coherent integration

Before coding, write the chosen integration design into your eventual qualification evidence.

### Preferred minimal architecture

Unless repository evidence disproves it, use this composition:

```text
canonical activity with hidden scoring authority
        │
        ▼
core session / Learning authority
        │
        │ raw source remains inside trusted runtime
        ▼
createLearnitRuntime served boundary
        │
        ├─ activityRevisionId / safe routing metadata
        └─ learner-safe ActivityPresentation
                    │
                    ▼
             render.js
                    │
          renderActivityPresentation()
                    │
             learner response
                    │
           readActivityResponse()
                    │
                    ▼
          runtime.answer(id,response)
                    │
                    ▼
      core evaluation/completion authority
```

Important:

- do **not** move correctness into UI;
- do **not** make UI derive ActivityPresentation from raw canonical activity;
- do **not** expose hidden solutions in the served runtime result;
- a small session envelope may carry non-secret identifiers/objective metadata required by the UI, but ActivityPresentation shapes themselves remain frozen;
- package assets already stored on the course record may be used by the trusted runtime projection.

### Atlas rule

Atlas Today may remain intentionally bounded to the semantics it actually supports.

If you choose the preferred path:

- make Atlas compatibility explicit about supported activity families rather than accidentally depending on the absence/presence of fields;
- do not let Atlas intercept a course containing unsupported rich families;
- preserve existing Atlas qcm/fill behavior;
- the classic served path must then fully handle the rich course.

Do **not** disable Atlas globally.

Do **not** modify `apps/learnit-next/src/integration/atlas/session.js`.

If a coherent solution cannot be implemented inside the authorized paths without changing that file or another forbidden authority, stop:

`HOLD_STUDENT_V01_SERVED_V4_ARCHITECTURE_REOPEN_REQUIRED`

---

## 4. Allowed product mutation

Only these product files are writable:

- `apps/learnit-next/src/main.js`
- `apps/learnit-next/src/ui/render.js`
- `apps/learnit-next/src/integration/atlas/surface.js`

The existing generic projection/presenter/media modules are **read-only** and must be reused.

### Runtime served boundary

The served runtime methods used by UI must no longer deliver authored solution authority as the activity to render.

At minimum handle safely:

- start course;
- resume active course;
- get active session where used by UI;
- answer result / next activity.

For each current/next activity, expose:

- the activity revision identifier needed for submission;
- only non-secret routing/objective metadata genuinely needed by UI;
- learner-safe ActivityPresentation produced by the frozen generic projection using the correct package assets.

Explicitly forbid in the UI-bound payload:

- `correctChoiceId`;
- fill authored `answers`;
- constructed `acceptedResponses`;
- matching `matches`;
- `correctOrder`;
- classify authored `assignments`.

### Served rendering

Replace qcm-vs-fill-only dispatch for the Student V0.1 served path with the generic presentation seam.

The UI must:

1. render the supplied ActivityPresentation with `renderActivityPresentation()`;
2. obtain learner response with `readActivityResponse()`;
3. submit only the resulting ActivityResponse and activityRevisionId to runtime;
4. render scored feedback only when the result is scored;
5. render a neutral completion/continue outcome for lesson/flashcard;
6. preserve existing progress/objective surfaces, focus handling, announcements and review behavior where compatible.

Do not implement a second evaluator in UI.

Do not add per-family correctness logic to `render.js`.

---

## 5. Tests — real served path is the authority

Add only:

- `apps/learnit-next/tests/student_v01_served_v4_integration.py`
- `apps/learnit-next/tests/browser_student_v01_served_v4_integration.py`

Do not weaken or rewrite prior Student V0.1 tests.

### A. Static/runtime integration test

Prove:

- served runtime current/next envelope is learner-safe;
- all forbidden scoring-secret keys are absent recursively from the UI-bound activity payload;
- all eight response shapes round-trip to core session semantics;
- lesson/flashcard return `scored:false` and no `correct`;
- evaluated families remain scored;
- package media reaches ActivityPresentation through the trusted projection;
- Atlas compatibility explicitly rejects unsupported rich courses while continuing to accept the supported qcm/fill Atlas route.

### B. Real browser test

Build and serve the actual Learn-it Next HTML.

Use the existing frozen fixture:

`apps/learnit-next/tests/fixtures/student_v01_v4_runtime.json`

Start from clean storage and use actual learner controls:

1. open real application;
2. open library if necessary;
3. choose/import the fixture using the actual file input;
4. start the course using the real course action;
5. interact with every family through visible controls;
6. submit/continue through the actual served UI;
7. verify lesson/flashcard never show correct/incorrect feedback;
8. verify scored families do show scored outcome;
9. reload mid-course;
10. verify resume lands on the correct incomplete activity;
11. continue through all eight families;
12. verify course completion/progress;
13. verify no scoring secrets appear in rendered DOM/attributes/serialized learner presentation;
14. verify local media renders without external network access.

Use canonical answer data only inside the test driver, out-of-band. Never inject hidden solutions into learner DOM.

Run the critical journey at:

- desktop around 1365×768;
- mobile around 390×844.

If the served browser path exposes a new defect in a forbidden authority, stop with owner classification instead of repairing it.

---

## 6. Regression matrix

Run unchanged prior suites including at minimum:

- `python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v`
- `python -B apps/learnit-next/tests/student_v01_activity_presentation.py`
- `python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py`
- `python -B apps/learnit-next/tests/student_v01_fanin_a.py`
- V2/V3 regressions used by R3;
- relevant Atlas session/surface tests for qcm/fill behavior.

Run the new static and browser tests.

No prior green behavior may be waived because the rich path works.

---

## 7. Source manifest and deterministic build

Any changed declared build source must be rebound in:

`apps/learnit-next/source_manifest.json`

Do not alter the manifest before the product source set is final.

Recompute:

- changed source Git blob fingerprints;
- canonical manifest self SHA256;
- exact manifest Git blob.

Then run the canonical build twice from the exact same executable candidate.

Require identical:

- output path;
- bytes;
- SHA256.

Do not accept locally reconstructed source bytes that differ from authoritative Git blobs.

---

## 8. Exact CI route

Minimum workflow routing only is authorized in:

`.github/workflows/learnit-next-ci.yml`

Route:

`student-v01/served-v4-integration`

through a narrowly bounded exact-head profile.

Require:

- PR event only;
- exact repair base ancestry;
- remote branch head = tested target;
- full new served-V4 static/browser tests;
- unchanged prior Student V0.1 regression suites;
- deterministic build;
- repository governance.

Do not generalize the workflow into a new framework.

If stacked PR topology prevents exact CI, a temporary DRAFT carrier to `main` may be used only for CI transport and must be closed without merge after evidence is recorded.

---

## 9. Scope audit

Before final qualification, compare exact `REPAIR_BASE..RESULT_SHA`.

Allowed final changed paths are only:

- `work-packages/ATLAS-WP-037.json`
- `docs/programs/student-v0.1/jobs/JOB_04_R4_SERVED_V4_INTEGRATION.md`
- `apps/learnit-next/src/main.js`
- `apps/learnit-next/src/ui/render.js`
- `apps/learnit-next/src/integration/atlas/surface.js`
- `apps/learnit-next/tests/student_v01_served_v4_integration.py`
- `apps/learnit-next/tests/browser_student_v01_served_v4_integration.py`
- `apps/learnit-next/source_manifest.json`
- `.github/workflows/learnit-next-ci.yml`
- later evidence-only `qualification/STUDENT_V01_SERVED_V4_INTEGRATION_RESULT.md`

Any other changed path is a scope failure.

---

## 10. Executable candidate versus evidence head

Separate:

- `RESULT_SHA`: exact executable candidate on which all functional/build/CI PASS claims were obtained;
- `EVIDENCE_HEAD`: later commit containing only qualification evidence.

Create:

`qualification/STUDENT_V01_SERVED_V4_INTEGRATION_RESULT.md`

Record:

- fresh HCP binding;
- exact repair base and qualified product base;
- reproduced blocker;
- chosen integration design and rejected alternatives;
- exact product diff;
- safe served-session envelope;
- Atlas compatibility decision;
- all commands/results;
- desktop/mobile evidence;
- reload/resume/completion evidence;
- secret-boundary evidence;
- manifest fingerprints/self-hash;
- two artifact hashes/byte counts;
- workflow run IDs;
- changed-path scope;
- rollback and reservations.

---

## 11. PASS gate

PASS requires all of the following on exact `RESULT_SHA`:

- diagnosis reproduced;
- product change restricted to authorized integration paths;
- UI-bound activity payload learner-safe;
- all eight families through the **real served** journey;
- qcm/fill/constructed/matching/order/classify scored correctly;
- lesson/flashcard non-scored completion only;
- generic presenters reused unchanged;
- safe media works;
- malicious/remote media remains fail-closed through unchanged authority;
- reload/resume works;
- completion works;
- desktop PASS;
- mobile PASS;
- existing Atlas qcm/fill route PASS;
- V2/V3 regressions PASS;
- unchanged R3/Wave1 suites PASS;
- deterministic double build PASS;
- source-manifest PASS;
- Repository governance PASS;
- PR scope PASS;
- exact integration CI PASS;
- scope PASS.

PASS does **not** authorize Wave 2 G3, JOB08, main merge or real students.

It authorizes only Control Room preparation of:

- JOB05 R1 contradictory QA against this exact repaired product;
- JOB07 R1 pilot packaging against this exact repaired product.

JOB06 remains frozen and is not rerun.

---

## 12. Final result block

Return exactly:

```text
STUDENT_V01_SERVED_V4_INTEGRATION_RESULT
REPAIR_BASE: 281dc7470d51682c5e6d79d3fff54c46cfbced3b
PREVIOUS_QUALIFIED_PRODUCT: 8fa25844cf9ddf7c2429f730d818b3518c46de04
RESULT_SHA: <exact executable candidate sha>
EVIDENCE_HEAD: <final evidence head sha>
ISSUE: 410
PR: <pr number>
DIAGNOSIS: PASS|FAIL
INTEGRATION_DESIGN: CLASSIC_CORE_SESSION_PLUS_GENERIC_PRESENTERS|OTHER_JUSTIFIED|UNRESOLVED
LEARNER_SAFE_RUNTIME_BOUNDARY: PASS|FAIL
ALL_EIGHT_REAL_SERVED: PASS|FAIL
SCORED_FAMILIES: PASS|FAIL
NON_SCORED_LESSON_FLASHCARD: PASS|FAIL
SECRET_BOUNDARY: PASS|FAIL
MEDIA: PASS|FAIL
ATLAS_QCM_FILL_REGRESSION: PASS|FAIL
RELOAD_RESUME: PASS|FAIL
COMPLETION: PASS|FAIL
DESKTOP: PASS|FAIL
MOBILE: PASS|FAIL
V2_REGRESSION: PASS|FAIL
V3_REGRESSION: PASS|FAIL
R3_REGRESSION: PASS|FAIL
SOURCE_MANIFEST: PASS|FAIL
DETERMINISTIC_BUILD: PASS|FAIL
REPOSITORY_GOVERNANCE: PASS|FAIL
PR_SCOPE: PASS|FAIL
INTEGRATION_CI: PASS|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed verdicts:

- `PASS_STUDENT_V01_SERVED_V4_READY_FOR_JOB05_R1_JOB07_R1`
- `HOLD_STUDENT_V01_SERVED_V4_DIAGNOSIS_DRIFT`
- `HOLD_STUDENT_V01_SERVED_V4_GENERIC_SEAM_DEFECT`
- `HOLD_STUDENT_V01_SERVED_V4_ARCHITECTURE_REOPEN_REQUIRED`
- `HOLD_STUDENT_V01_SERVED_V4_NEEDS_REWORK`
- `FAIL_STUDENT_V01_SERVED_V4_SCOPE_VIOLATION`
