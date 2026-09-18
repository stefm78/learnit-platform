# /AUDIT /SOLVE /BUILD — JOB 05
## Student V0.1 — independent contradictory QA

Repository: `stefm78/learnit-platform`  
Authority issue: `#404`  
Wave 2 control freeze: `#403`  
Work package: `ATLAS-WP-034`

Branch: `student-v01/wave2-contradictory-qa`

Exact anchors:

- `WAVE2_COMMON_BASE = 281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- `QUALIFIED_PRODUCT_BASE = 8fa25844cf9ddf7c2429f730d818b3518c46de04`
- FAN-IN A R3 authority: issue #401 / PR #402

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Role

You are independent contradictory QA.

Your job is not to re-demonstrate the known happy path. Your job is to find a false PASS before a real student does.

You own QA probes, fixtures and evidence only. You do **not** own product repair.

If you discover a defect in runtime, presentation, Atlas session integration, import, authoring, media handling or persistence, stop with a reproducible owner-classified HOLD. Do not expand scope to fix it.

---

## 1. Fresh authority and base reconstruction

Before mutation:

1. fresh-read the active Human Control Plane HEAD and bind exact UCP/UAO/governance rules;
2. fresh-read repository `main`;
3. read issues #403, #404 and #401;
4. read PR #402 and `qualification/STUDENT_V01_FANIN_A_R3_RESULT.md`;
5. read `work-packages/ATLAS-WP-034.json`;
6. verify this branch descends from exact `WAVE2_COMMON_BASE`;
7. verify no sibling Wave 2 branch has been consumed.

Read as QA authority, without editing:

- `contracts/learnit-kit-v4.schema.json`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `authoring/v4/validate_kit.py`
- `apps/learnit-next/build.py`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/src/main.js`
- `apps/learnit-next/src/core/contract.js`
- `apps/learnit-next/src/core/session.js`
- `apps/learnit-next/src/integration/atlas/session.js`
- `apps/learnit-next/src/integration/atlas/activity_projection.js`
- `apps/learnit-next/src/ui/activity_presenters.js`
- `apps/learnit-next/src/ui/media.js`
- existing Student V0.1 tests.

Do not infer real-app readiness from the R3 seam-level E2E result. Prove it.

---

## 2. Build one independent QA fixture

Create a fixed, canonical V4 QA fixture under `qa/student-v0.1/**`.

It must:

- be independently generated from current V4 authority, not copied from JOB06;
- contain exactly one course;
- contain all eight Student V0.1 families:
  `lesson`, `flashcard`, `matching`, `order`, `classify`, `qcm`, `fill`, `constructed`;
- include at least one safe embedded SVG asset with normal `xmlns="http://www.w3.org/2000/svg"`;
- keep lesson/flashcard non-scored;
- include correct hidden solutions only in the canonical kit;
- pass canonical V4 validation before browser use.

This fixture is QA data, not candidate learning content. Pedagogical excellence is not required, but schema/semantic correctness is.

Also create adversarial mutations in the QA harness rather than weakening the canonical fixture.

---

## 3. Contradictory attack matrix

### A. Exact deterministic artifact

From this QA-only branch, canonical product bytes should remain unchanged.

Run the Learn-it Next build at least twice.

Require both outputs to match each other and the qualified R3 artifact identity unless a justified non-product build input changed.

R3 artifact reference:

- bytes: `474861`
- SHA256: `0b1e21038bc8f17521ecd604460781377a850b174907723a7d6af6174511310f`

Any product artifact drift from a QA-only branch is a FAIL.

### B. Real served/browser V4 journey

This is the primary false-PASS challenge.

Serve/open the **actual built Learn-it Next application**, not a hand-built test DOM.

Through user-visible product controls:

1. start from empty local state;
2. import the canonical QA V4 file through the real import control;
3. verify the course appears;
4. start the real course/session path;
5. reach and interact with every activity family actually scheduled by the product;
6. for evaluated families, submit responses through visible controls;
7. for lesson/flashcard, complete/reveal without scoring;
8. observe feedback and continuation;
9. reload during an unfinished journey;
10. resume from product state;
11. continue to completion where the product model allows;
12. return to library/progress.

Use canonical answer data only in the test driver, out-of-band. Never inject answer keys into learner presentation or DOM.

A direct call sequence like:

`projectActivityPresentation -> renderActivityPresentation -> readActivityResponse`

is useful supporting evidence but is **not** sufficient for this section.

If the real application rejects or cannot navigate a V4 family while isolated seams pass, return HOLD and identify the owning boundary exactly.

### C. Desktop and mobile

Repeat the critical import/start/interact/resume path in at least:

- desktop viewport around 1365×768;
- mobile viewport around 390×844.

Do not accept a desktop-only PASS.

### D. Secret boundary

Challenge DOM, attributes, serialized learner-safe presentations and visible text for leakage of:

- `correctChoiceId`
- fill answers
- `acceptedResponses`
- matching solution
- `correctOrder`
- classify assignments

Do not claim that the canonical local JSON file itself is secret. The authority is the learner-safe presentation boundary.

### E. Non-scored contamination

Prove lesson and flashcard completion/reveal:

- does not become correct/incorrect;
- does not count as validation/mastery evidence;
- does not silently create scored execution semantics.

### F. Media fail-closed

Positive:

- standard safe inline SVG namespace renders locally.

Negative mutations must be rejected or not rendered:

- `<script>`
- event handlers such as `onclick`
- `foreignObject`
- iframe/object/embed
- external `href` / `xlink:href`
- `javascript:`
- `data:`, `file:`, `blob:`
- unsafe/external `url(...)`
- http/https remote resources

Observe browser requests. Unexpected network access is a FAIL.

### G. Persistence and isolation

Challenge:

- reload during active journey;
- browser restart/reopen when practical;
- local reset;
- no mutation of legacy/RC718 namespaces;
- no cross-course identity collision from duplicate labels.

### H. Regression

Run existing v2/v3 Student/runtime regressions and relevant stable Learn-it Next tests. Do not modify them.

### I. Accessibility smoke

At minimum:

- keyboard-reachable controls;
- visible/logical focus progression;
- labels/names on inputs and buttons;
- no drag-only interaction for matching/order/classify;
- feedback/status semantics remain perceivable.

---

## 4. Output discipline

All new QA files live under:

`qa/student-v0.1/**`

plus your own work package/prompt/result evidence.

Do not edit product files to make QA pass.

If a product defect appears, add the smallest deterministic repro under QA scope and classify it as one of:

- CONTRACT/IMPORT
- LEARNING_SEMANTICS
- ATLAS_SESSION_INTEGRATION
- PRESENTATION_UI
- MEDIA
- PERSISTENCE
- ACCESSIBILITY
- BUILD/INTEGRATION
- UNKNOWN_NEEDS_CONTROL_ROOM

Do not assign blame by guess; cite the failing boundary.

---

## 5. Qualification result

Create:

`qualification/STUDENT_V01_JOB05_QA_RESULT.md`

Separate the exact tested product base from your QA branch evidence.

Return exactly:

```text
STUDENT_V01_JOB05_RESULT
WAVE2_COMMON_BASE: 281dc7470d51682c5e6d79d3fff54c46cfbced3b
QUALIFIED_PRODUCT_BASE: 8fa25844cf9ddf7c2429f730d818b3518c46de04
RESULT_SHA: <exact QA result sha>
ISSUE: 404
PR: <pr number>
BUILD_IDENTITY: PASS|FAIL
CANONICAL_V4_FIXTURE: PASS|FAIL
REAL_SERVED_V4_JOURNEY: PASS|FAIL
ALL_FAMILIES_REAL_PATH: PASS|FAIL
RELOAD_RESUME: PASS|FAIL
COMPLETION: PASS|FAIL
NON_SCORED_LESSON_FLASHCARD: PASS|FAIL
SECRET_BOUNDARY: PASS|FAIL
MEDIA_FAIL_CLOSED: PASS|FAIL
DESKTOP: PASS|FAIL
MOBILE: PASS|FAIL
ACCESSIBILITY_SMOKE: PASS|FAIL
PERSISTENCE_ISOLATION: PASS|FAIL
V2_V3_REGRESSION: PASS|FAIL
DEFECT_OWNER: NONE|CONTRACT_IMPORT|LEARNING_SEMANTICS|ATLAS_SESSION_INTEGRATION|PRESENTATION_UI|MEDIA|PERSISTENCE|ACCESSIBILITY|BUILD_INTEGRATION|UNKNOWN_NEEDS_CONTROL_ROOM
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_JOB05_CONTRADICTORY_QA_READY_FOR_FANIN_B`
- `HOLD_STUDENT_V01_JOB05_PRODUCT_GAP`
- `HOLD_STUDENT_V01_JOB05_QA_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB05_SCOPE_VIOLATION`

A PASS requires the real served rich-V4 path, not only lower-level seams.
