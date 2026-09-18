# /AUDIT /SOLVE /BUILD — JOB 04 R3
## Student V0.1 — cross-role FAN-IN oracle alignment and exact requalification

You are a fresh controlled integration worker. Do not trust prior-chat conclusions as authority. Reconstruct state from Git.

Repository: `stefm78/learnit-platform`

Authority issue: `#401`  
Parent program: `#380`  
Parent FAN-IN: `#391`  
R2 authority: `#397`  
R2 authoritative PR: `#398`  
Work package: `ATLAS-WP-033`

Integration branch: `student-v01/fanin-a-r3-oracle`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

---

## 0. Constitutional and repository rebind

Before any mutation:

1. fresh-read the active Human Control Plane HEAD and bind exact UCP/UAO/governance authority;
2. fresh-read repository `main`;
3. read issues #401, #397, #391 and #380;
4. read PR #398 and `qualification/STUDENT_V01_FANIN_A_R2_RESULT.md`;
5. read `work-packages/ATLAS-WP-033.json`;
6. read:
   - `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`;
   - `contracts/learnit-kit-v4.schema.json`;
   - `authoring/v4/tests/test_validate_v4.py`;
   - `apps/learnit-next/src/integration/atlas/activity_projection.js`;
   - `apps/learnit-next/tests/student_v01_fanin_a.py`;
7. verify the live branch/PR state before writing.

Bind these frozen anchors exactly:

- `R3_BASE = 249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`
- `R2_EXECUTABLE_RESULT = 7d261fd515b36f20865daea5a933c4ff3e7ffc16`
- `FANIN_A_BASE = 21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- `WAVE1_COMMON_BASE = 27846dff52fde9b83434bca29bd8732ea42834bf`
- `JOB01_R2 = ef3080e32e873170c6fd2fbdc72e93c31389cebb`
- `JOB02 = 6c91346d07c934cfb2917799084647b13e4fb931`
- `JOB03 = a90ba85857dded331e5e3952c2f181cbe2e6d689`

The R3 branch was created from exact `R3_BASE`. Preparation commits may add only `ATLAS-WP-033` and this prompt before execution.

If the live R2 authority moved after R3 branch creation, classify the movement. Evidence-only drift does not silently rewrite R3. Product/contract drift that invalidates the frozen candidate returns HOLD for Control Room review.

---

## 1. Re-prove the R2 stopping boundary

Do not accept the Control Room diagnosis without reproducing it.

From exact repository files, prove all of the following:

1. the R2 qualification records the unchanged cross-role oracle failure at:
   `assert [p["type"] for p in presentations] == list(FAMILIES)`;
2. `student_v01_fanin_a.py` defines its expected family order as:
   `qcm, fill, constructed, lesson, flashcard, matching, order, classify`;
3. the authoritative representative package returned by `make_valid_v4()` orders activities as:
   `lesson, flashcard, matching, order, classify, qcm, fill, constructed`;
4. `projectActivityPresentation(activity, ...)` is a per-activity projection and does not define or perform family sorting;
5. the R2 exact-head CI reached this assertion only after JOB01/JOB02/JOB03 role suites had passed.

If any statement above is false, stop with:

`HOLD_STUDENT_V01_FANIN_A_R3_DIAGNOSIS_DRIFT`

and return exact observed evidence.

---

## 2. Decide the ordering invariant before editing

This is the key reasoning gate.

Search current architecture, contract, authoring, runtime and integration authority for a normative rule requiring a canonical cross-family sort of Student V0.1 activities.

Distinguish carefully between:

- an authored activity sequence;
- a test fixture's incidental construction order;
- the expected set of admitted activity families;
- a normative canonical family ordering.

### Decision rule

If an authoritative contract or architecture rule requires a canonical family order, do **not** edit the oracle. Return:

`HOLD_STUDENT_V01_FANIN_A_R3_ORDER_SEMANTICS_AMBIGUOUS`

with the exact source and the conflict that must be resolved by Control Room.

If no authoritative canonical family sort exists, adopt this bounded integration-oracle invariant:

1. the representative package must contain exactly one instance of every expected Student V0.1 family;
2. no expected family may be missing or duplicated;
3. the projection layer must preserve the activity order supplied by the canonical package;
4. the oracle must not require an unrelated hard-coded family ordering.

This is an oracle correction only. It is **not** authorization to redefine product sequencing semantics.

Record the decision and evidence before mutation.

---

## 3. Minimum oracle correction

Only if section 2 resolves to the bounded invariant above, modify:

`apps/learnit-next/tests/student_v01_fanin_a.py`

The correction must be minimal.

A preferred equivalent formulation is:

- derive `source_types` from `kit["courses"][0]["activities"]`;
- prove its length equals the expected family count;
- prove the expected family list itself has no duplicates;
- prove `source_types` has no duplicates;
- prove `set(source_types) == set(EXPECTED_FAMILIES)` or an equivalent exact-coverage assertion;
- prove `[p["type"] for p in presentations] == source_types`.

The exact spelling may differ, but all two dimensions must remain explicit:

**coverage** and **source-order preservation**.

Forbidden shortcuts:

- deleting the ordering assertion;
- sorting both lists and comparing only sorted values;
- changing `make_valid_v4()` activity order;
- changing `projectActivityPresentation()`;
- changing any product implementation;
- weakening secret/media/non-scored assertions already present later in the oracle.

Do not modify `apps/learnit-next/source_manifest.json`: this integration test is not a declared deterministic build source.

---

## 4. Scope proof before qualification

Before running the full suite, compare exact `R3_BASE..HEAD`.

Product/runtime/authoring/UI files must be unchanged from R3_BASE.

The only permitted eventual changed paths are:

- `work-packages/ATLAS-WP-033.json`;
- `docs/programs/student-v0.1/jobs/JOB_04_R3_FANIN_ORACLE_ALIGNMENT.md`;
- `apps/learnit-next/tests/student_v01_fanin_a.py`;
- `.github/workflows/learnit-next-ci.yml` only for minimum exact R3 routing;
- `qualification/STUDENT_V01_FANIN_A_R3_RESULT.md` after qualification.

Any other path returns:

`FAIL_STUDENT_V01_FANIN_A_R3_SCOPE_VIOLATION`

---

## 5. Local/full qualification — no shortened path

After the oracle correction, rerun the whole integration qualification. Do not stop after the formerly failing assertion.

### 5.1 Deterministic build twice

Run the canonical Learn-it Next build twice from the same exact candidate head.

Require identical:

- artifact path;
- byte count;
- SHA256.

Any difference is FAIL.

### 5.2 JOB01 R2

Run:

`python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v`

Require all prior runtime invariants, including:

- v2 regression;
- v3 constructed regression;
- v4 evaluated/non-scored semantics;
- standard SVG namespace admission;
- malicious/external SVG fail-closed;
- secret boundary.

### 5.3 JOB02

Run unchanged:

- `python -B apps/learnit-next/tests/student_v01_activity_presentation.py`
- `python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py`

Require PASS for qcm/fill, lesson/flashcard, matching/order/classify/constructed, media, accessibility and presentation secret boundary.

### 5.4 JOB03

Run unchanged:

- `python -B authoring/v4/tests/test_validate_v4.py -v`
- `python -B authoring/v2/atlas/tests/test_pedagogical_quality.py -v`
- `python -B authoring/factory/tests/test_student_v01_v4.py -v`

### 5.5 Cross-role E2E

Run corrected:

`python -B apps/learnit-next/tests/student_v01_fanin_a.py`

Require completion of the entire script, not merely passage of the corrected ordering assertion.

The completed oracle must prove, as already encoded by the test:

- JOB03 representative v4 authoring package;
- JOB01 runtime admission/projection/evaluation;
- JOB02 learner-safe browser rendering/response grammar;
- all eight Student V0.1 families;
- bounded media;
- learner-secret exclusion;
- lesson/flashcard non-scored behavior;
- authoring-to-learner flow.

If a new downstream failure appears, do not repair it in this job. Classify the owning boundary and stop with:

`HOLD_STUDENT_V01_FANIN_A_R3_NEW_E2E_DEFECT`

---

## 6. Exact CI routing

The R3 candidate must receive exact-head CI, not only local PASS.

Use only the minimum route necessary.

Preferred topology:

- authoritative R3 DRAFT PR is stacked on `student-v01/fanin-a-r2`;
- route `student-v01/fanin-a-r3-oracle` through the existing bounded `student-v01-fanin-a` profile;
- exact R3 ancestry is bound to `R3_BASE`;
- remote branch HEAD must equal the CI target;
- existing R1/R2 route behavior must remain unchanged.

If GitHub's PR event topology does not execute the stacked PR route, a temporary DRAFT PR from the exact same R3 branch to `main` may be used **only as a CI carrier**. It must:

- be explicitly labeled in its body as non-authoritative transport;
- never be merged;
- use the exact same branch HEAD as the authoritative R3 PR;
- be closed after durable CI evidence is recorded.

Do not classify an unrouted or missing CI run as PASS.

---

## 7. Exact final candidate and evidence-only mutation

Separate:

- `RESULT_SHA`: the exact executable/testable R3 candidate before qualification-only evidence mutation;
- `EVIDENCE_HEAD`: later commit(s) containing only qualification evidence.

All functional PASS claims must bind to `RESULT_SHA`, not to a later evidence commit.

Create:

`qualification/STUDENT_V01_FANIN_A_R3_RESULT.md`

Record at minimum:

- fresh HCP binding;
- current `main`;
- `R3_BASE`;
- R2 executable/evidence anchors;
- frozen JOB01/JOB02/JOB03 SHAs;
- diagnosis proof;
- ordering-invariant decision and source evidence;
- exact oracle diff;
- exact changed paths;
- two deterministic build hashes and byte counts;
- all role/E2E commands and results;
- workflow run IDs;
- Repository governance result;
- PR scope result;
- exact CI result;
- temporary carrier identity/closure if one was required;
- rollback/reservations.

---

## 8. PASS gate

PASS requires **all** of the following on the exact RESULT_SHA:

- R3 base identity PASS;
- R2 stopping-boundary diagnosis PASS;
- ordering invariant resolved without architecture reopen;
- oracle coverage invariant PASS;
- oracle source-order-preservation invariant PASS;
- deterministic double build PASS;
- JOB01 R2 PASS;
- JOB02 PASS;
- JOB03 PASS;
- v2 regression PASS;
- v3 regression PASS;
- v4 full E2E PASS;
- non-scored lesson/flashcard PASS;
- secret boundary PASS;
- standard SVG namespace PASS;
- malicious SVG fail-closed PASS;
- media PASS;
- authoring-to-learner PASS;
- Repository governance PASS;
- PR scope PASS;
- exact integration CI PASS;
- scope PASS.

PASS authorizes **Control Room preparation of Wave 2 only**.

It does not authorize:

- merge to `main`;
- product promotion;
- student use;
- automatic launch of JOB05/JOB06/JOB07.

---

## 9. Final result block

Return exactly:

```text
STUDENT_V01_JOB04_R3_FANIN_A_RESULT
R3_BASE: 249ea00b287fb98fb9ad02b8ffeff2fe2eeec670
R2_EXECUTABLE_RESULT: 7d261fd515b36f20865daea5a933c4ff3e7ffc16
JOB01_R2_SHA: ef3080e32e873170c6fd2fbdc72e93c31389cebb
JOB02_SHA: 6c91346d07c934cfb2917799084647b13e4fb931
JOB03_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
RESULT_SHA: <exact executable candidate sha>
EVIDENCE_HEAD: <final evidence head sha>
ISSUE: 401
PR: <authoritative R3 PR number>
R2_DIAGNOSIS: PASS|FAIL
ORDERING_INVARIANT: SOURCE_ORDER_PLUS_EXACT_COVERAGE|CANONICAL_SORT_FOUND|UNRESOLVED
ORACLE_COVERAGE: PASS|FAIL
ORACLE_SOURCE_ORDER: PASS|FAIL
DETERMINISTIC_BUILD: PASS|FAIL
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

Allowed final verdicts:

- `PASS_STUDENT_V01_FANIN_A_R3_READY_FOR_WAVE2`
- `HOLD_STUDENT_V01_FANIN_A_R3_DIAGNOSIS_DRIFT`
- `HOLD_STUDENT_V01_FANIN_A_R3_ORDER_SEMANTICS_AMBIGUOUS`
- `HOLD_STUDENT_V01_FANIN_A_R3_NEW_E2E_DEFECT`
- `HOLD_STUDENT_V01_FANIN_A_R3_NEEDS_REWORK`
- `FAIL_STUDENT_V01_FANIN_A_R3_SCOPE_VIOLATION`
- `FAIL_STUDENT_V01_FANIN_A_R3_ARCHITECTURE_REOPEN_REQUIRED`
