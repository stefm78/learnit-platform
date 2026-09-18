# /AUDIT /SOLVE /BUILD — JOB 07
## Student V0.1 — deterministic pilot packaging and learner-start UX

Repository: `stefm78/learnit-platform`  
Authority issue: `#406`  
Wave 2 control freeze: `#403`  
Work package: `ATLAS-WP-036`

Branch: `student-v01/wave2-pilot-package`

Exact anchors:

- `WAVE2_COMMON_BASE = 281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- `QUALIFIED_PRODUCT_BASE = 8fa25844cf9ddf7c2429f730d818b3518c46de04`

Apply:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Role

You own a **pilot wrapper**, not the learner product.

Your job is to make the exact qualified application and an arbitrary canonical V4 kit easy to hand to a controlled pilot learner/facilitator, with deterministic packaging and observable start friction.

You may not patch Learn-it Next source, schema, authoring, manifest or workflow behavior from this job.

If real application behavior blocks the pilot path, report HOLD and the exact product boundary.

---

## 1. Reconstruct authority

Before mutation:

1. fresh-read Human Control Plane HEAD;
2. fresh-read repository state, issues #403/#406/#401 and PR #402;
3. verify branch ancestry from exact `WAVE2_COMMON_BASE`;
4. read:
   - Student V0.1 program charter and architecture;
   - R3 qualification;
   - `apps/learnit-next/build.py`;
   - `apps/learnit-next/source_manifest.json`;
   - `apps/learnit-next/index.template.html`;
   - `apps/learnit-next/src/main.js`;
   - real import/session UI code;
   - V4 schema/validator.

Do not consume JOB06 output. This job must be generic.

---

## 2. Pilot-package contract

Create all implementation under:

`pilot/student-v0.1/**`

Design the smallest deterministic package builder that takes two explicit inputs:

1. exact built Learn-it Next HTML;
2. one canonical V4 kit JSON.

The package should contain a minimal, explicit set such as:

- exact learner app HTML;
- exact canonical course JSON;
- `START_HERE.html` or equivalent learner-facing launcher/instructions;
- machine-readable pilot manifest binding hashes;
- concise facilitator/readme instructions only if needed.

Do not embed a modified app.

Do not add a backend, installer, service worker dependency, catalog, remote script or remote font.

If a local helper server is useful for controlled testing, keep it optional pilot tooling and make clear that it is not learner-product architecture.

---

## 3. Determinism

The package builder must:

- canonicalize its manifest deterministically;
- sort package entries deterministically;
- use fixed metadata/timestamps for ZIP output if ZIP is used;
- bind SHA256 for the exact app and kit inputs;
- fail closed if either input changes without manifest regeneration;
- produce byte-identical package output on two runs with identical inputs.

Store source code/tests, not generated bulky binaries, unless repository conventions explicitly authorize the artifact.

---

## 4. Learner-start UX

The package must tell a first-time learner exactly what to do without undocumented developer knowledge.

Measure required learner actions from opening the package to starting the course.

Record each required action explicitly; do not manipulate the metric by excluding mandatory file-selection/import steps.

The instructions should distinguish:

- learner actions;
- facilitator/setup actions;
- optional recovery/reset actions.

Do not claim one-click import if browser security or product behavior requires a file chooser.

---

## 5. Independent rich-V4 pilot fixture

Do not use JOB06.

Generate a valid rich V4 temporary/test fixture from current V4 authority, ideally reusing the canonical test helper as code rather than copying sibling content.

The fixture must include:

- lesson;
- flashcard;
- matching;
- order;
- classify;
- qcm;
- fill;
- constructed;
- safe local media.

Validate it canonically before pilot smoke.

It is a packaging/UX probe, not learning content.

---

## 6. Real browser pilot smoke

Use the actual packaged/built application.

Test at least:

- desktop viewport around 1365×768;
- mobile viewport around 390×844.

From clean state:

1. open the learner start surface;
2. follow the documented start path;
3. import/select the rich V4 kit through actual product controls;
4. start the course/session;
5. interact with the real learner controls;
6. reload before completion;
7. resume;
8. continue and finish if the product supports the journey;
9. return to completion/progress surface.

The browser test may automate file selection, but the written action-count report must still count the manual learner action that automation represents.

Observe console/page errors and network requests.

No unexpected remote request is allowed.

### Critical rule

If the real served application cannot complete the representative rich V4 journey, do not patch product source.

Return:

`HOLD_STUDENT_V01_JOB07_PRODUCT_BLOCKS_PILOT`

with exact failing family/path/error and owner classification.

Packaging can be mechanically correct while pilot readiness is HOLD.

---

## 7. Resume and recovery

Challenge:

- page reload during active journey;
- reopen/resume;
- accidental return to library and continuation;
- invalid kit selection;
- local reset/recovery instructions.

Do not claim cross-device sync or account recovery.

---

## 8. Security/secret wording

The canonical local kit contains scoring authority by design.

Do not claim the distributed JSON file hides answers from a technically capable learner.

The required boundary is that the learner UI/presentation does not expose answer authority during normal interaction.

The package must not add additional answer-key files or debug dumps.

---

## 9. Final evidence

Create:

`qualification/STUDENT_V01_JOB07_PILOT_RESULT.md`

Record:

- exact input app identity;
- test fixture identity;
- package structure;
- package SHA256 and bytes for two builds;
- learner action count;
- desktop/mobile results;
- import/start result;
- reload/resume result;
- finish result;
- network observations;
- any product blocker and owner boundary;
- exact changed paths and rollback.

Return exactly:

```text
STUDENT_V01_JOB07_RESULT
WAVE2_COMMON_BASE: 281dc7470d51682c5e6d79d3fff54c46cfbced3b
QUALIFIED_PRODUCT_BASE: 8fa25844cf9ddf7c2429f730d818b3518c46de04
RESULT_SHA: <exact result sha>
ISSUE: 406
PR: <pr number>
PACKAGE_DETERMINISM: PASS|FAIL
APP_HASH_BINDING: PASS|FAIL
KIT_HASH_BINDING: PASS|FAIL
OFFLINE_NO_REMOTE: PASS|FAIL
LEARNER_START_INSTRUCTIONS: PASS|FAIL
LEARNER_START_ACTIONS: <integer>
RICH_V4_FIXTURE: PASS|FAIL
REAL_SERVED_V4_JOURNEY: PASS|FAIL
DESKTOP: PASS|FAIL
MOBILE: PASS|FAIL
RELOAD_RESUME: PASS|FAIL
COMPLETION: PASS|FAIL
RECOVERY: PASS|FAIL
PRODUCT_BLOCKER: NONE|CONTRACT_IMPORT|LEARNING_SEMANTICS|ATLAS_SESSION_INTEGRATION|PRESENTATION_UI|PERSISTENCE|UNKNOWN_NEEDS_CONTROL_ROOM
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed verdicts:

- `PASS_STUDENT_V01_JOB07_PILOT_PACKAGE_READY_FOR_FANIN_B`
- `HOLD_STUDENT_V01_JOB07_PRODUCT_BLOCKS_PILOT`
- `HOLD_STUDENT_V01_JOB07_PACKAGING_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB07_SCOPE_VIOLATION`

A mechanically deterministic ZIP is not sufficient for PASS if the real rich-V4 learner journey cannot run.
