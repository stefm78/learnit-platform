# /AUDIT /SOLVE /BUILD — JOB 05 R1
## Student V0.1 — contradictory QA after served-V4 repair

Repository: `stefm78/learnit-platform`  
Authority issue: `#412`  
Wave 2 control freeze: `#403`  
Served-V4 repair authority: `#410 / PR #411`  
Work package: `ATLAS-WP-038`

Branch:

`student-v01/wave2-contradictory-qa-r1`

Exact anchors:

- `JOB05_R1_BASE = 7c13d67a76705b4452304c0f6a882504bc7701a7`
- `REPAIRED_PRODUCT_SHA = bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- `PRE_REPAIR_JOB05_RESULT = 3ef8895fcf4df0ded936daf4c939e2c60200232c`
- `FROZEN_QA_FIXTURE_BLOB = c190fc4f04a7cee5731627e4f6276ee08e39d746`
- expected repaired artifact:
  - bytes: `478657`
  - SHA256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Role

You are an independent contradictory QA worker.

Your task is **not** to confirm the served-V4 repair.

Your task is to falsify it if possible.

The product is read-only in this job. If you discover a defect, create the smallest deterministic QA repro and return HOLD with the failing ownership boundary. Do not repair product source.

A seam-level PASS, repair-worker test PASS, or static source inspection is never sufficient for this job's final PASS.

---

## 1. Fresh authority rebind

Before any mutation:

1. fresh-read the active Human Control Plane HEAD and bind exact UCP/UAO/governance authority;
2. fresh-read repository `main`;
3. read issues #412, #410, #404, #403 and #401;
4. read PR #411 and:
   - `qualification/STUDENT_V01_SERVED_V4_INTEGRATION_RESULT.md`;
5. read PR #407 and:
   - `qualification/STUDENT_V01_JOB05_QA_RESULT.md`;
   - historical `qa/student-v0.1/job05_contradictory_qa.py`;
6. read `work-packages/ATLAS-WP-038.json`;
7. verify this branch descends exactly from `JOB05_R1_BASE`;
8. verify the product source bytes inherited from `REPAIRED_PRODUCT_SHA` have not been changed on this QA branch.

The pre-repair QA harness is historical evidence only. It intentionally encodes the old expected failure and old artifact hash. Do not reuse its verdict logic as the R1 oracle.

---

## 2. Freeze the independent pre-repair fixture

The file already prepared on this branch:

`qa/student-v0.1/JOB05_CANONICAL_V4_FIXTURE.json`

must remain byte-for-byte identical to Git blob:

`c190fc4f04a7cee5731627e4f6276ee08e39d746`

Before writing any QA code:

- fetch/recompute its Git blob identity;
- fail closed if it differs;
- never edit it to accommodate the repaired implementation.

This fixture predates the repair and is the primary independent rich-V4 test input.

Run the canonical V4 validator against it.

Static inspection is not enough.

Require validator PASS before the fixture can be used as positive browser input.

---

## 3. /solve — derive independent post-repair oracles

Do not copy assertions blindly from the repair worker.

Derive QA oracles from the frozen contract/interface authorities:

- `contracts/learnit-kit-v4.schema.json`
- `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`

and from stable product semantics, not from implementation shape.

At minimum, independent QA must prove:

1. a valid rich V4 package imports through the actual served product;
2. the actual served learner path reaches every supported family;
3. UI-bound learner data excludes hidden scoring authority;
4. evaluated families are scored by Learning;
5. lesson/flashcard complete without correctness semantics;
6. reload/resume does not lose or skip the active journey;
7. completion is reachable;
8. local safe media works without external network access;
9. active/remote media remains fail-closed;
10. desktop and mobile both work;
11. prior v2/v3/R3/served-repair regressions remain green.

You may inspect repair implementation to form attack hypotheses, but implementation details are not the oracle.

---

## 4. QA files

Create only:

- `qa/student-v0.1/job05_r1_contradictory_qa.py`
- `qa/student-v0.1/browser_job05_r1_contradictory_qa.py`

plus later qualification evidence and the minimum exact-head workflow route allowed by WP-038.

Do not modify:

- the frozen fixture;
- any `apps/learnit-next/src/**`;
- any `apps/learnit-next/tests/**`;
- source manifest;
- contract;
- architecture;
- authoring;
- showcase;
- pilot.

---

## 5. Exact repaired artifact identity

Because this branch is QA-only, the canonical product build must remain byte-identical to the repaired candidate.

Run the canonical build twice.

Require both outputs to be identical to each other and exactly:

```text
bytes   478657
sha256  85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e
```

If build output differs, classify:

`BUILD_INTEGRATION`

and stop. A QA-only branch must not alter product bytes.

---

## 6. Prove the old blocker is actually closed

Write an independent supporting static/runtime check that demonstrates the old contradiction no longer applies.

At minimum challenge:

- classic served routing is no longer qcm-versus-fill-only for rich V4;
- a rich V4 course is not accidentally intercepted by the qcm/fill-only Atlas path;
- existing Atlas qcm/fill-compatible courses are still accepted by Atlas.

This section is supporting evidence only.

It does not substitute for the real browser journey.

If the old blocker still reproduces, return:

`HOLD_STUDENT_V01_JOB05_R1_PRODUCT_GAP`

without changing QA expectations or product code.

---

## 7. Independent runtime-boundary attack

Using the actual built application/runtime, independently inspect the learner-bound current/next activity envelopes.

Recursively assert absence of:

- `correctChoiceId`
- authored fill `answers`
- constructed `acceptedResponses`
- matching `matches`
- `correctOrder`
- classify authored `assignments`

Check both:

- JS/runtime learner-bound objects;
- serialized learner-safe payloads where observable;
- DOM text/attributes after rendering.

Do not claim that the local canonical kit JSON itself hides answers. That is not the security boundary.

### Wrong-answer challenge

On a disposable clean state, intentionally submit at least one valid but incorrect response for an evaluated family.

Require:

- `scored: true`
- `correct: false`

and no evaluation logic in UI.

Do not let this negative trial contaminate the later clean full-completion journey.

---

## 8. Real served/browser rich-V4 journey

This is the primary authority for PASS.

Build and serve the actual Learn-it Next artifact.

Using the frozen pre-repair QA fixture and actual product controls:

1. start from clean storage;
2. open the real application;
3. use the real file input;
4. import the frozen fixture;
5. verify the imported course is visible;
6. start using the real learner course action;
7. traverse every family through visible controls:
   - lesson
   - flashcard
   - matching
   - order
   - classify
   - qcm
   - fill
   - constructed
8. for evaluated units, submit QA-driver responses through visible controls;
9. for lesson/flashcard, use only their visible completion/reveal controls;
10. verify feedback semantics;
11. finish the course;
12. verify product completion/progress state.

The canonical answer data may be read by the QA driver out-of-band from the fixture. Never expose it to the learner DOM.

### Reload/resume challenge

Do not test only one reload point.

From clean runs, prove resume after at least:

- one completed non-scored unit;
- one completed scored unit;
- one reload while the journey remains incomplete.

After resume, prove the product returns to the expected next incomplete activity and does not duplicate/skip completion.

---

## 9. Media contradiction tests

### Positive

Require the fixture's safe local SVG to:

- survive import;
- render in the learner presentation where referenced;
- produce no unexpected HTTP(S) request.

### Negative

Create QA-owned temporary mutations in memory/temp files; do not edit the frozen fixture.

Challenge at least one active and one external/remote media case, such as:

- `<script>`
- event handler;
- external `href` / `xlink:href`;
- external `url(...)`;
- `javascript:`;
- http/https reference.

When a digest must change, use repository canonical digest logic so rejection is attributable to media policy, not merely stale digest metadata.

Require fail-closed rejection before learner rendering.

---

## 10. Desktop/mobile/accessibility

Run the full critical journey at minimum at:

- desktop: about `1365x768`;
- mobile: about `390x844`.

Accessibility smoke must independently check:

- keyboard-reachable learner controls;
- meaningful names/labels;
- no drag-only requirement for matching/order/classify;
- feedback/status perceivable;
- focus remains usable after reveal/submit/continue transitions.

Unexpected page errors or journey-related console errors are failures.

---

## 11. Persistence/isolation

Challenge at minimum:

- reload/resume;
- clean reset/restart path;
- no collision from repeated human-readable labels;
- no unexpected mutation of unrelated legacy state.

Do not claim cross-device sync or account recovery.

---

## 12. Regression matrix

Run unchanged prior suites, including at minimum:

- `python -B apps/learnit-next/tests/student_v01_served_v4_integration.py`
- `python -B apps/learnit-next/tests/browser_student_v01_served_v4_integration.py`
- `python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v`
- `python -B apps/learnit-next/tests/student_v01_activity_presentation.py`
- `python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py`
- `python -B apps/learnit-next/tests/student_v01_fanin_a.py`
- relevant V2/V3 regressions;
- Atlas qcm/fill regression suites used by the repair.

Your independent QA harness must run **in addition** to these suites.

Calling the repair worker's browser test is regression evidence, not contradictory QA evidence.

---

## 13. Exact-head CI

A final PASS requires exact-head CI.

The authoritative JOB05 R1 PR is stacked on the served-V4 repair branch.

Add only the minimum bounded route in:

`.github/workflows/learnit-next-ci.yml`

for:

`student-v01/wave2-contradictory-qa-r1`

The route must:

- be PR-only;
- bind exact ancestry to `JOB05_R1_BASE`;
- require remote branch HEAD = tested target;
- execute the independent R1 QA harnesses;
- execute repaired-product regression suites;
- verify exact artifact identity;
- preserve all existing routes unchanged.

If the stacked PR does not trigger because of GitHub event topology, a temporary DRAFT PR from the **same exact branch HEAD** to `main` may be used only as CI transport.

Such a carrier:

- is not authority;
- must be labeled CI-only;
- must never be merged;
- must be closed after durable evidence is recorded.

Do not report `INTEGRATION_CI: PASS` from a local-only run.

---

## 14. Stop discipline and result semantics

If a causal product defect is found, stop product qualification after capturing the smallest deterministic repro.

For result fields:

- `PASS` = independently executed and passed;
- `FAIL` = independently executed and failed;
- `BLOCKED` = not executed because an earlier causal product defect made it unreachable.

Never encode an unexecuted check as PASS.

Classify the smallest first failing owner as:

- `NONE`
- `CONTRACT_IMPORT`
- `LEARNING_SEMANTICS`
- `SERVED_RUNTIME_BOUNDARY`
- `ATLAS_SESSION_INTEGRATION`
- `PRESENTATION_UI`
- `MEDIA`
- `PERSISTENCE`
- `ACCESSIBILITY`
- `BUILD_INTEGRATION`
- `UNKNOWN_NEEDS_CONTROL_ROOM`

---

## 15. Qualification evidence

Create:

`qualification/STUDENT_V01_JOB05_R1_QA_RESULT.md`

Separate:

- `RESULT_SHA` = exact QA executable/tested head before evidence-only commit;
- `EVIDENCE_HEAD` = later evidence-only head.

Record at minimum:

- fresh HCP binding;
- exact base/product/frozen-fixture identities;
- canonical fixture validation;
- independent oracle design;
- exact QA changed paths;
- two build hashes/bytes;
- old-blocker closure proof;
- wrong-answer proof;
- runtime/DOM secret scans;
- desktop/mobile browser results;
- reload/resume positions;
- media positive/negative results;
- accessibility/persistence results;
- all regression commands/results;
- workflow run IDs;
- temporary carrier identity and closure if used;
- rollback.

---

## 16. PASS gate

PASS requires all of the following to be independently executed and PASS:

- frozen fixture identity;
- canonical V4 validation;
- exact repaired artifact identity;
- old blocker closed;
- real served all-eight-family journey;
- wrong-answer semantics;
- reload/resume;
- completion;
- lesson/flashcard non-scored boundary;
- secret boundary;
- positive local media;
- malicious/remote media fail-closed;
- desktop;
- mobile;
- accessibility smoke;
- persistence/isolation;
- V2/V3 regressions;
- R3/FAN-IN regression;
- served-V4 repair regressions;
- Repository governance;
- PR scope;
- exact integration CI;
- scope.

PASS authorizes only Control Room preparation/execution of JOB07 R1 against the same repaired product.

It does not authorize G3, JOB08, main merge or real students.

---

## 17. Final result block

Return exactly:

```text
STUDENT_V01_JOB05_R1_RESULT
JOB05_R1_BASE: 7c13d67a76705b4452304c0f6a882504bc7701a7
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
FROZEN_QA_FIXTURE_BLOB: c190fc4f04a7cee5731627e4f6276ee08e39d746
RESULT_SHA: <exact tested qa head>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 412
PR: <authoritative pr number>
FROZEN_FIXTURE_IDENTITY: PASS|FAIL|BLOCKED
CANONICAL_V4_FIXTURE: PASS|FAIL|BLOCKED
BUILD_IDENTITY_EXACT_REPAIR: PASS|FAIL|BLOCKED
OLD_BLOCKER_CLOSED: PASS|FAIL|BLOCKED
REAL_SERVED_V4_JOURNEY: PASS|FAIL|BLOCKED
ALL_FAMILIES_REAL_PATH: PASS|FAIL|BLOCKED
WRONG_ANSWER_SEMANTICS: PASS|FAIL|BLOCKED
RELOAD_RESUME: PASS|FAIL|BLOCKED
COMPLETION: PASS|FAIL|BLOCKED
NON_SCORED_LESSON_FLASHCARD: PASS|FAIL|BLOCKED
SECRET_BOUNDARY: PASS|FAIL|BLOCKED
MEDIA_SAFE_LOCAL: PASS|FAIL|BLOCKED
MEDIA_FAIL_CLOSED: PASS|FAIL|BLOCKED
DESKTOP: PASS|FAIL|BLOCKED
MOBILE: PASS|FAIL|BLOCKED
ACCESSIBILITY_SMOKE: PASS|FAIL|BLOCKED
PERSISTENCE_ISOLATION: PASS|FAIL|BLOCKED
V2_V3_REGRESSION: PASS|FAIL|BLOCKED
R3_REGRESSION: PASS|FAIL|BLOCKED
SERVED_REPAIR_REGRESSION: PASS|FAIL|BLOCKED
REPOSITORY_GOVERNANCE: PASS|FAIL|BLOCKED
PR_SCOPE: PASS|FAIL|BLOCKED
INTEGRATION_CI: PASS|FAIL|BLOCKED
DEFECT_OWNER: NONE|CONTRACT_IMPORT|LEARNING_SEMANTICS|SERVED_RUNTIME_BOUNDARY|ATLAS_SESSION_INTEGRATION|PRESENTATION_UI|MEDIA|PERSISTENCE|ACCESSIBILITY|BUILD_INTEGRATION|UNKNOWN_NEEDS_CONTROL_ROOM
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_JOB05_R1_READY_FOR_JOB07_R1`
- `HOLD_STUDENT_V01_JOB05_R1_PRODUCT_GAP`
- `HOLD_STUDENT_V01_JOB05_R1_QA_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB05_R1_SCOPE_VIOLATION`
