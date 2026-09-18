# Student V0.1 — JOB07 Pilot Packaging / Learner-start UX Result

Status: **HOLD — PRODUCT BLOCKS PILOT**

Work package: `ATLAS-WP-036`  
Authority issue: #406  
Wave 2 control issue: #403  
Authoritative DRAFT PR: #409  
Branch: `student-v01/wave2-pilot-package`

## 1. Fresh authority rebind

Immediately before the blocker probe and evidence mutation:

- Human Control Plane HEAD blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- UCP: `UCP-CONTROL-PLANE 1.1-R4`
- UCP SHA256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- UAO: `2.6`
- UAO SHA256: `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- Wave 2 common base: `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- Qualified product base: `8fa25844cf9ddf7c2429f730d818b3518c46de04`
- JOB07 preparation head: `48d7e25aa77d72733244704eda4ecbb6387ac4c9`
- PR #402: open, DRAFT, unmerged, head `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- PR #409 before JOB07 mutation: open, DRAFT, unmerged, base `281dc7470d51682c5e6d79d3fff54c46cfbced3b`

No authority drift invalidated the JOB07 execution.

## 2. Exact product identity used for the blocker audit

The following blobs are byte-identical between
`QUALIFIED_PRODUCT_BASE=8fa25844cf9ddf7c2429f730d818b3518c46de04`
and the JOB07 branch before mutation:

- `contracts/learnit-kit-v4.schema.json`: `e141bd5fafa75dda88a49e8a2094e4589bb4306e`
- `apps/learnit-next/src/integration/atlas/surface.js`: `ffa86b06d2efd62e9eddb734bcf83b59f76597b3`
- `apps/learnit-next/src/ui/render.js`: `1309573b6cb34d20eb1771467792838987d1642a`
- `apps/learnit-next/src/core/session.js`: `dbf816ea82af7758436fdc7716e969b39a194798`
- `authoring/v4/tests/test_validate_v4.py`: `85debca78c3ec342d9e4e7ed63a033fd0968e72e`

The blocker therefore belongs to the exact qualified product candidate, not to
JOB07 packaging work.

## 3. Independent rich V4 fixture

The canonical v4 authoring fixture in
`authoring/v4/tests/test_validate_v4.py::make_valid_v4()` is independent of
JOB06 and contains exactly:

`lesson, flashcard, matching, order, classify, qcm, fill, constructed`

plus safe embedded SVG media.

The exact qualified R3 evidence records:

- canonical v4 validator: 8/8 PASS;
- all eight family seams exercised;
- media and learner-secret boundaries PASS.

JOB07 therefore accepts this fixture as the independent valid rich V4 input.
It does not consume the JOB06 showcase kit.

## 4. Product blocker — causal proof

### 4.1 V4 contract

`lesson` and `flashcard` derive from `unitCommon`.

`unitCommon` has no `assessmentRole` property, and the two family definitions
use `unevaluatedProperties: false`. A contract-valid lesson/flashcard therefore
does not carry `assessmentRole`.

The canonical rich fixture follows this exact contract and omits
`assessmentRole` from lesson and flashcard.

### 4.2 Atlas served-session admission

`apps/learnit-next/src/integration/atlas/surface.js::compatibleAtlasCourse()`
requires every activity to satisfy:

`typeof activity.assessmentRole === 'string'`

Because every valid rich V4 course in scope contains lesson and flashcard, the
canonical rich course cannot enter the Atlas served-session path.

This is a structural contradiction between the V4 non-scored families and the
current Atlas session-compatibility predicate.

### 4.3 Classic fallback cannot carry the rich journey

When Atlas does not claim the course, the classic library action remains the
fallback.

The classic session starts at authored index 0 and selects the first incomplete
activity. The independent rich fixture starts with `lesson`.

`apps/learnit-next/src/ui/render.js::renderSessionSnapshot()` routes:

- `qcm` -> `renderQcmForm()`;
- every non-QCM activity -> `renderFillForm()`.

`renderFillForm()` immediately iterates `activity.segments`, which a valid
lesson does not have.

Therefore the current real served path cannot successfully render the first
activity of the canonical rich V4 journey. It cannot reach completion, reload
resume, or recovery for that journey.

## 5. Why the R3 PASS does not contradict this HOLD

R3 proves the activity projection/presenter/evaluator seams and deterministic
product build. Its cross-role browser coverage renders each projected
ActivityPresentation directly.

JOB07 asks the stronger question: can an imported rich V4 course traverse the
actual served learner path from library/import through the real Atlas/classic
session integration, reload/resume, and completion?

The incompatibility above sits precisely at that later served-session boundary.
The R3 seam PASS remains valid.

## 6. Fail-closed build decision

JOB07 explicitly forbids repairing runtime, session integration, presentation UI,
schema, source manifest, or workflow from packaging scope.

Once the product blocker was proven, JOB07 stopped at the product boundary.

No ZIP, wrapper, helper server, copied application artifact, auto-import shim, or
product patch was created. This prevents a packaging layer from hiding the
product defect or claiming a false pilot PASS.

A read-only causal probe was added:

- `pilot/student-v0.1/job07_product_blocker_probe.py`
- executable result SHA: `3f9798dd11edea4dcc95c959aacb0a6790d2bfc1`
- probe blob: `61e6b9c7c3bee5245d6fa9cac7c801dc9efe0609`

The same assertions were independently executed against the exact
`QUALIFIED_PRODUCT_BASE` through the Git connector and returned:

- `JOB07_BLOCKER_PROBE=PASS`
- `RICH_V4_ATLAS_COMPATIBILITY=FAIL`
- `CLASSIC_FALLBACK_FIRST_ACTIVITY=lesson`
- `CLASSIC_FALLBACK_RENDERER=fill`
- `PRODUCT_BLOCKER=ATLAS_SESSION_INTEGRATION`

## 7. Packaging/browser fields under the fail-closed stop

The result schema has only PASS/FAIL for these fields and no NOT_RUN token.
Accordingly, controls that were intentionally not executed after the product
boundary stop are reported as FAIL, not as a fabricated PASS.

- package determinism: FAIL — no package was produced after the stop;
- app hash binding: FAIL — no package manifest was produced;
- kit hash binding: FAIL — no package manifest was produced;
- offline/no-remote package proof: FAIL — no package was produced;
- learner start instructions: FAIL — no package/start surface was produced;
- desktop/mobile full journey: FAIL — structurally blocked before a successful
  rich served session can start;
- reload/resume, completion, recovery: FAIL — unreachable after the deterministic
  first-activity blocker.

The intended learner-start path, had packaging proceeded, contains seven explicit
actions under the current product UX:

1. open `START_HERE.html`;
2. open Learn-it;
3. activate `Afficher la bibliothèque`;
4. activate the course file chooser;
5. select the canonical V4 JSON;
6. activate `Importer`;
7. activate `Commencer`.

The blocker occurs after action 7 when the rich course is handed to the served
session path. The action count is reported rather than hidden or optimized away.

## 8. Scope and governance

Exact preparation-head to executable-result delta:

- added `pilot/student-v0.1/job07_product_blocker_probe.py`

No product/runtime/authoring/schema/manifest/workflow/showcase/QA/governance file
changed.

Repository governance for executable result
`3f9798dd11edea4dcc95c959aacb0a6790d2bfc1`:

- run: `35357117273`
- `validate-repository`: success
- mirrored `Repository governance`: success

PR #409 remained open, DRAFT and unmerged.

Scope: **PASS**.

## 9. Rollback

Rollback is bounded and does not touch the qualified product:

- revert/delete the JOB07 blocker probe commit/result;
- revert/delete this qualification evidence;
- or close PR #409 and delete `student-v01/wave2-pilot-package`.

The Wave 2 common base, qualified product base, PR #402 and sibling Wave 2
branches remain untouched.

## 10. Audit verdict

False-PASS challenge:

- packaging success cannot compensate for a served product path that rejects the
  contract-valid non-scored families;
- direct presenter tests are not equivalent to import/start/resume/finish through
  the served application;
- no field lacking execution evidence is promoted to PASS.

False-FAIL challenge:

- the contradiction is anchored to exact product blobs;
- it applies to every valid rich V4 course containing lesson/flashcard under the
  frozen Student V0.1 grammar;
- the canonical independent fixture begins with lesson and therefore reaches the
  deterministic classic fallback failure immediately;
- no JOB07-owned packaging change can repair this without violating scope.

Final audit: **HOLD**.

```text
STUDENT_V01_JOB07_RESULT
WAVE2_COMMON_BASE: 281dc7470d51682c5e6d79d3fff54c46cfbced3b
QUALIFIED_PRODUCT_BASE: 8fa25844cf9ddf7c2429f730d818b3518c46de04
RESULT_SHA: 3f9798dd11edea4dcc95c959aacb0a6790d2bfc1
ISSUE: 406
PR: 409
PACKAGE_DETERMINISM: FAIL
APP_HASH_BINDING: FAIL
KIT_HASH_BINDING: FAIL
OFFLINE_NO_REMOTE: FAIL
LEARNER_START_INSTRUCTIONS: FAIL
LEARNER_START_ACTIONS: 7
RICH_V4_FIXTURE: PASS
REAL_SERVED_V4_JOURNEY: FAIL
DESKTOP: FAIL
MOBILE: FAIL
RELOAD_RESUME: FAIL
COMPLETION: FAIL
RECOVERY: FAIL
PRODUCT_BLOCKER: ATLAS_SESSION_INTEGRATION
SCOPE: PASS
FINAL_VERDICT: HOLD_STUDENT_V01_JOB07_PRODUCT_BLOCKS_PILOT
```
