# Student V0.1 — FAN-IN A R3 Qualification Result

Status: **PASS — READY FOR CONTROL ROOM WAVE 2 PREPARATION**

Work package: `ATLAS-WP-033`  
Authority issue: #401  
Authoritative DRAFT PR: #402  
Integration branch: `student-v01/fanin-a-r3-oracle`

## 1. Fresh authority rebind

Immediately before the evidence-only mutation:

- Human Control Plane HEAD blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- UCP: `UCP-CONTROL-PLANE 1.1-R4`
- UCP SHA256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- UAO: `2.6`
- UAO SHA256: `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- GCP: `1.5`
- GCP SHA256: `d0a49d52d04ea158a6708f0f632bf426068f788a6f185ce5f4e24010c36061cd`
- Learn-it repository `main`: `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- R2 authoritative PR #398 head: `249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`, open and unmerged.
- R3 authoritative PR #402 executable head: `8fa25844cf9ddf7c2429f730d818b3518c46de04`, DRAFT and unmerged.
- PR #402 base: `student-v01/fanin-a-r2` at exact `249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`.

No authority or product/contract drift invalidated the frozen R3 candidate.

## 2. Frozen anchors

- `R3_BASE = 249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`
- `R2_EXECUTABLE_RESULT = 7d261fd515b36f20865daea5a933c4ff3e7ffc16`
- `R2_EVIDENCE_HEAD = 249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`
- `FANIN_A_BASE = 21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- `WAVE1_COMMON_BASE = 27846dff52fde9b83434bca29bd8732ea42834bf`
- `JOB01_R2 = ef3080e32e873170c6fd2fbdc72e93c31389cebb`
- `JOB02 = 6c91346d07c934cfb2917799084647b13e4fb931`
- `JOB03 = a90ba85857dded331e5e3952c2f181cbe2e6d689`

The exact R2 executable-to-evidence delta contains only
`qualification/STUDENT_V01_FANIN_A_R2_RESULT.md`; therefore the movement to
`R3_BASE` is evidence-only and does not rewrite the frozen product candidate.

## 3. Reproduced R2 stopping boundary

The R2 diagnosis was independently reproduced from Git and exact-head CI:

1. R2 qualification records the failure at:
   `assert [p["type"] for p in presentations] == list(FAMILIES)`.
2. The unchanged oracle's expected tuple is:
   `qcm, fill, constructed, lesson, flashcard, matching, order, classify`.
3. `make_valid_v4()` constructs:
   `lesson, flashcard, matching, order, classify, qcm, fill, constructed`.
4. `projectActivityPresentation(activity, ...)` is a per-activity projection and contains no family sorting.
5. Exact-head R2 CI runs `35317110266` and `35317121736` both pass the JOB01/JOB02/JOB03 role suites before failing at that same ordering assertion.

R2 diagnosis: **PASS**.

## 4. Ordering invariant decision

Current architecture, v4 schema, authoring validator, runtime contract/import/session code,
and the integration projection were searched for a normative canonical cross-family sort.

No authoritative canonical family sort exists.

The bounded R3 invariant is therefore:

- exactly one source activity exists for every expected Student V0.1 family;
- the expected family set contains no duplicate;
- the source package contains no duplicate family;
- source family coverage equals the exact expected family set;
- presentation projection preserves the exact source activity order.

Decision: `SOURCE_ORDER_PLUS_EXACT_COVERAGE`.

This does not redefine learner sequencing semantics; it removes an unrelated hard-coded
ordering requirement from the integration oracle.

## 5. Exact oracle correction

Only the failing integration-oracle assertion was replaced with explicit coverage and
source-order checks:

```python
source_types = [a["type"] for a in kit["courses"][0]["activities"]]
assert len(FAMILIES) == len(set(FAMILIES)), "expected family list must not contain duplicates"
assert len(source_types) == len(FAMILIES), (source_types, FAMILIES)
assert len(source_types) == len(set(source_types)), f"duplicate source families: {source_types}"
assert set(source_types) == set(FAMILIES), (source_types, FAMILIES)
assert [p["type"] for p in presentations] == source_types
```

The later secret/media/non-scored/E2E assertions remain unchanged.

## 6. Exact executable candidate and scope

`RESULT_SHA = 8fa25844cf9ddf7c2429f730d818b3518c46de04`

Exact `R3_BASE..RESULT_SHA` changed paths:

- `.github/workflows/learnit-next-ci.yml`
- `apps/learnit-next/tests/student_v01_fanin_a.py`
- `docs/programs/student-v0.1/jobs/JOB_04_R3_FANIN_ORACLE_ALIGNMENT.md`
- `work-packages/ATLAS-WP-033.json`

No product/runtime/authoring/UI/schema/source-manifest file changed.

The workflow delta only:
- admits stacked PRs targeting `student-v01/fanin-a-r2`;
- routes `student-v01/fanin-a-r3-oracle` through the existing `student-v01-fanin-a` profile;
- requires exact R3 PR base `249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`;
- preserves exact remote-head and ancestry checks;
- leaves existing R1/R2 route behavior intact.

Scope: **PASS**.  
PR scope: **PASS**.

## 7. Deterministic double build

The exact candidate `8fa25844cf9ddf7c2429f730d818b3518c46de04` was qualified twice by the same exact-head routed job:

- Learn-it Next CI run `35347351175`, attempt 1, job `105606909903`;
- Learn-it Next CI run `35347351175`, attempt 2, job `105607600964`.

Both builds produced exactly:

- path: `apps/learnit-next/dist/learnit-next.html`
- bytes: `474861`
- SHA256: `0b1e21038bc8f17521ecd604460781377a850b174907723a7d6af6174511310f`

Deterministic double build: **PASS**.

## 8. Full role and regression qualification

Both exact-head attempts ran the complete required profile.

### JOB01 R2

`python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v`

- `STUDENT_V01_LEARNING_RUNTIME_PASS 92/92`
- v2 regression PASS;
- v3 constructed regression PASS;
- v4 evaluated and non-scored semantics PASS;
- standard SVG namespace admission PASS;
- malicious/external SVG fail-closed PASS;
- learner-secret projection boundary PASS.

### JOB02

`python -B apps/learnit-next/tests/student_v01_activity_presentation.py`

- `STUDENT_V01_ACTIVITY_PRESENTATION_STATIC_PASS`

`python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py`

- `QCM_FILL_BROWSER_PASS`
- `LESSON_FLASHCARD_BROWSER_PASS`
- `MATCHING_ORDER_CLASSIFY_CONSTRUCTED_BROWSER_PASS`
- `MEDIA_SECRET_ACCESSIBILITY_BROWSER_PASS`
- `STUDENT_V01_ACTIVITY_PRESENTATION_BROWSER_PASS`

### JOB03

`python -B authoring/v4/tests/test_validate_v4.py -v` -> **8/8 PASS**  
`python -B authoring/v2/atlas/tests/test_pedagogical_quality.py -v` -> **6/6 PASS**  
`python -B authoring/factory/tests/test_student_v01_v4.py -v` -> **3/3 PASS**

### Cross-role E2E

`python -B apps/learnit-next/tests/student_v01_fanin_a.py`

Both attempts complete the full script and emit:

- `STUDENT_V01_FANIN_A_AUTHORING_TO_LEARNER_PASS`
- `STUDENT_V01_FANIN_A_ALL_FAMILIES_END_TO_END_PASS`
- `STUDENT_V01_FANIN_A_SECRET_BOUNDARY_PASS`
- `STUDENT_V01_FANIN_A_MEDIA_PASS`
- `STUDENT_V01_FANIN_A_NON_SCORED_PASS`
- `STUDENT_V01_FANIN_A_EXACT_ROUTE=PASS`
- `STUDENT_V01_FANIN_A_TARGET=8fa25844cf9ddf7c2429f730d818b3518c46de04`

No downstream semantic defect emerged.

## 9. Repository governance and CI

Repository governance run `35347351077` completed successfully.

Direct validation evidence:

`REPOSITORY VALIDATION OK: 123 work package(s), governor state valid`

Learn-it Next exact integration CI:

- run `35347351175`
- run number `609`
- final attempt `2`
- PR `#402`
- exact head `8fa25844cf9ddf7c2429f730d818b3518c46de04`
- exact base `249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`
- final conclusion: **success**

The stacked PR route executed directly; no temporary main-target carrier PR was required.

Repository governance: **PASS**.  
Exact integration CI: **PASS**.

## 10. Final contradictory audit

False-PASS challenge:

- no canonical family sort is present in the current authority;
- coverage and order preservation are independently asserted;
- neither source package nor projection semantics were modified to fit the test;
- all frozen role/product files remain byte-identical to R3_BASE;
- full E2E proceeds beyond the formerly failing assertion;
- the exact candidate passes two identical deterministic builds;
- PR base/head, remote-head and exact ancestry are bound by CI;
- repository governance passes.

False-FAIL challenge:

- the retained `FAMILIES` tuple is used as an expected set/coverage authority, not as a canonical sequence;
- the package's authored order remains observable and is required to survive projection exactly.

Final audit: **PASS**.

## 11. Reservations and rollback

PASS authorizes **Control Room preparation of Wave 2 only**.

It does not authorize:

- merge to `main`;
- product promotion;
- real student use;
- automatic launch of JOB05/JOB06/JOB07.

Rollback: close PR #402 and delete `student-v01/fanin-a-r3-oracle`; PR #398, R2 executable
`7d261fd515b36f20865daea5a933c4ff3e7ffc16`, R2 evidence head `249ea00b287fb98fb9ad02b8ffeff2fe2eeec670`, and all frozen role heads remain recoverable.

## 12. Final result

```text
STUDENT_V01_JOB04_R3_FANIN_A_RESULT
R3_BASE: 249ea00b287fb98fb9ad02b8ffeff2fe2eeec670
R2_EXECUTABLE_RESULT: 7d261fd515b36f20865daea5a933c4ff3e7ffc16
JOB01_R2_SHA: ef3080e32e873170c6fd2fbdc72e93c31389cebb
JOB02_SHA: 6c91346d07c934cfb2917799084647b13e4fb931
JOB03_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
RESULT_SHA: 8fa25844cf9ddf7c2429f730d818b3518c46de04
EVIDENCE_HEAD: <this evidence commit>
ISSUE: 401
PR: 402
R2_DIAGNOSIS: PASS
ORDERING_INVARIANT: SOURCE_ORDER_PLUS_EXACT_COVERAGE
ORACLE_COVERAGE: PASS
ORACLE_SOURCE_ORDER: PASS
DETERMINISTIC_BUILD: PASS
ROLE_TESTS: PASS
V2_REGRESSION: PASS
V3_REGRESSION: PASS
V4_END_TO_END: PASS
NON_SCORED_LESSON_FLASHCARD: PASS
SECRET_BOUNDARY: PASS
STANDARD_SVG_NAMESPACE: PASS
MALICIOUS_SVG_FAIL_CLOSED: PASS
MEDIA: PASS
AUTHORING_TO_LEARNER: PASS
REPOSITORY_GOVERNANCE: PASS
PR_SCOPE: PASS
INTEGRATION_CI: PASS
SCOPE: PASS
FINAL_VERDICT: PASS_STUDENT_V01_FANIN_A_R3_READY_FOR_WAVE2
```
