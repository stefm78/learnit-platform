# /AUDIT /SOLVE /BUILD — JOB 04 R2
## Student V0.1 — Wave 1 FAN-IN A convergence after JOB01 media-policy rework

You are a fresh controlled integrator. Do not use prior-chat conclusions as authority.

Repository: `stefm78/learnit-platform`

Authority issue: `#397`
Parent FAN-IN issue: `#391`
Prior R1 issue: `#394`
JOB01 R2 issue: `#395`

Integration branch: `student-v01/fanin-a-r2`
Work package: `ATLAS-WP-032`

## 0. Constitutional / repository rebind

Before mutation:

1. reconstruct the active Human Control Plane from its authoritative HEAD;
2. fresh-read repository `main`;
3. read #397, #391, #394, #395;
4. read `work-packages/ATLAS-WP-032.json`;
5. read `docs/programs/student-v0.1/FANIN_A_R2_INPUT_FREEZE.md`;
6. read prior qualification `qualification/STUDENT_V01_FANIN_A_RESULT.md` from PR #393 / branch `student-v01/fanin-a`;
7. re-read PRs #387, #388, #389, #396 and their exact heads.

Do not replace frozen SHAs with moving branch names.

## 1. Exact frozen inputs

Bind exactly:

- `FANIN_A_BASE = 21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- `R2_START_CANDIDATE = f4636e06279481b62ffd676ba70313c71283baeb`
- `WAVE1_COMMON_BASE = 27846dff52fde9b83434bca29bd8732ea42834bf`
- `JOB01_PREDECESSOR = d937592fb4d1e6dba6fcd02e290290f1a98cff71`
- `JOB01_R2 = ef3080e32e873170c6fd2fbdc72e93c31389cebb`
- `JOB02 = 6c91346d07c934cfb2917799084647b13e4fb931`
- `JOB03 = a90ba85857dded331e5e3952c2f181cbe2e6d689`

The branch was prepared from exact `R2_START_CANDIDATE` and then received only execution-authority artifacts. Prove that no product delta occurred before your execution.

If current `main` has moved beyond `FANIN_A_BASE`, classify the drift. Coordination-only movement does not rewrite this candidate baseline. Product/contract drift that invalidates the frozen architecture requires HOLD and Control Room review.

## 2. Re-prove prior candidate identity

Prove that `R2_START_CANDIDATE` is the exact executable result qualified by JOB04 R1 before the qualification-only evidence commit.

Required checks:

- prior qualification names `f4636e06279481b62ffd676ba70313c71283baeb` as `RESULT_SHA`;
- `f4636e...` contains the accepted JOB01 predecessor, JOB02 and JOB03 role deltas and prior integration wiring;
- branch-preparation commits after `f4636e...` change only `ATLAS-WP-032`, the R2 freeze, and this prompt before execution.

If false, fail closed.

## 3. Re-prove JOB01 R2 delta identity

Use exact commits, not PR prose.

Required:

- PR #396 head = `ef3080e32e873170c6fd2fbdc72e93c31389cebb`;
- PR #396 remains unmerged;
- merge-base(`JOB01_PREDECESSOR`, `JOB01_R2`) = `JOB01_PREDECESSOR`;
- exact changed-path set is:
  - `apps/learnit-next/src/core/contract.js`
  - `apps/learnit-next/tests/student_v01_learning_runtime.py`
  - `work-packages/ATLAS-WP-031.json`

If any mismatch exists, return a table:

`CHECK | EXPECTED | OBSERVED | PATH/COMMIT`

and stop with `HOLD_STUDENT_V01_FANIN_A_R2_INPUT_DRIFT`.

## 4. Apply only the exact JOB01 R2 delta

Apply the exact file delta `JOB01_PREDECESSOR..JOB01_R2` onto the R2 branch.

Do not re-author the fix from the issue description.

JOB02 and JOB03 role-owned files are immutable in this job.

Any unexpected conflict means stop with:
`HOLD_STUDENT_V01_FANIN_A_R2_CONFLICT_REQUIRES_ROLE_REWORK`.

## 5. Minimum integration rebinding

After applying the exact role delta, update only what is strictly necessary to make the new exact candidate deterministic and routable:

- `apps/learnit-next/source_manifest.json` if source hashes/declared files require rebind;
- `.github/workflows/learnit-next-ci.yml` only to route this exact R2 branch/candidate if the existing route does not cover it;
- `qualification/STUDENT_V01_FANIN_A_R2_RESULT.md` after real qualification.

Do not change semantic role code beyond the exact JOB01 R2 delta.

Do not edit `apps/learnit-next/tests/student_v01_fanin_a.py`; rerun it unchanged as an integration oracle.

## 6. Full qualification — no shortened path

Rerun the full FAN-IN oracle, not only the repaired media case.

### 6.1 Deterministic build

Run the canonical Learn-it Next deterministic build and record artifact hash.

### 6.2 JOB01 R2 role suite

Run the unchanged/updated JOB01 R2 role qualification and prove:

- standard inline SVG namespace PASS;
- malicious/external SVG remains fail-closed;
- JOB03 representative media PASS;
- v2 regression PASS;
- v3 constructed PASS;
- v4 evaluated/non-scored semantics PASS;
- secret boundary PASS.

### 6.3 JOB02 role suite

Run the frozen JOB02 static/browser presentation suites unchanged.

Require PASS for:

- qcm/fill regression;
- lesson/flashcard;
- matching;
- order;
- classify;
- constructed;
- media;
- accessibility smoke;
- presentation secret boundary.

### 6.4 JOB03 role suite

Run frozen JOB03 tests unchanged:

- v4 validator;
- pedagogical quality;
- Factory v4.

### 6.5 Cross-role E2E

Run unchanged:

`python -B apps/learnit-next/tests/student_v01_fanin_a.py`

Require the exact JOB03 representative v4 package, including its standard inline SVG namespace, to flow through runtime admission and learner-safe presentation.

Require PASS for all admitted types:

- qcm
- fill
- constructed
- lesson
- flashcard
- matching
- order
- classify
- bounded media

### 6.6 Core invariants

Explicitly prove:

- lesson/flashcard produce no correctness, validation, mastery, transfer or spaced-review evidence;
- no `correctChoiceId`, fill answers, `acceptedResponses`, matching solution, correct order or classify assignments cross learner-safe presentation;
- standard SVG namespace metadata is admitted;
- malicious/external SVG remains rejected;
- v2 and v3 regressions remain green;
- authoring-to-learner boundary is green.

## 7. Governance / CI

On the exact final candidate head require:

- Repository governance PASS;
- PR scope PASS;
- exact routed Learn-it Next integration CI PASS.

Do not classify missing/unrouted CI as product PASS. Add only the minimum R2 branch route if necessary and rerun on the new exact head.

## 8. Scope and no-silent-repair rules

Allowed role mutation is only the exact JOB01 R2 delta.

Any new semantic failure owned by JOB01/JOB02/JOB03 must return HOLD and identify the owner. The integrator must not repair it.

Any need to change `contracts/**`, architecture authority or frozen JOB02/JOB03 semantics returns:
`FAIL_STUDENT_V01_FANIN_A_R2_ARCHITECTURE_REOPEN_REQUIRED`.

Wave 2 remains blocked until PASS.

## 9. Qualification artifact

Create:

`qualification/STUDENT_V01_FANIN_A_R2_RESULT.md`

Bind:

- active authority rebind;
- current main observed;
- all frozen input SHAs;
- exact JOB01 R2 delta proof;
- exact result SHA before evidence-only mutation if applicable;
- exact changed paths;
- all test commands/results;
- build artifact hash;
- workflow run IDs;
- reservations/rollback.

## 10. Final result

Return exactly:

```text
STUDENT_V01_JOB04_R2_FANIN_A_RESULT
FANIN_A_BASE: 21d25c36aec6c04fdfe8126c95e71cbf80771a1b
R2_START_CANDIDATE: f4636e06279481b62ffd676ba70313c71283baeb
WAVE1_COMMON_BASE: 27846dff52fde9b83434bca29bd8732ea42834bf
JOB01_PREDECESSOR_SHA: d937592fb4d1e6dba6fcd02e290290f1a98cff71
JOB01_R2_SHA: ef3080e32e873170c6fd2fbdc72e93c31389cebb
JOB02_SHA: 6c91346d07c934cfb2917799084647b13e4fb931
JOB03_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
RESULT_SHA: <sha>
ISSUE: 397
PR: <number>
R2_START_IDENTITY: PASS|FAIL
JOB01_R2_DELTA_IDENTITY: PASS|FAIL
ROLE_TESTS: PASS|FAIL
V2_REGRESSION: PASS|FAIL
V3_REGRESSION: PASS|FAIL
V4_END_TO_END: PASS|FAIL
NON_SCORED_LESSON_FLASHCARD: PASS|FAIL
SECRET_BOUNDARY: PASS|FAIL
STANDARD_SVG_NAMESPACE: PASS|FAIL
MALICIOUS_SVG_FAIL_CLOSED: PASS|FAIL
MEDIA: PASS|FAIL
AUTHORING_TO_LEARNER: PASS|FAIL
REPOSITORY_GOVERNANCE: PASS|FAIL
PR_SCOPE: PASS|FAIL
INTEGRATION_CI: PASS|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed verdicts:

- `PASS_STUDENT_V01_FANIN_A_R2_READY_FOR_WAVE2`
- `HOLD_STUDENT_V01_FANIN_A_R2_INPUT_DRIFT`
- `HOLD_STUDENT_V01_FANIN_A_R2_CONFLICT_REQUIRES_ROLE_REWORK`
- `HOLD_STUDENT_V01_FANIN_A_R2_NEEDS_REWORK`
- `FAIL_STUDENT_V01_FANIN_A_R2_ARCHITECTURE_REOPEN_REQUIRED`

PASS authorizes Control Room preparation of Wave 2 only. It does not authorize merge to main, product promotion or real student use.
