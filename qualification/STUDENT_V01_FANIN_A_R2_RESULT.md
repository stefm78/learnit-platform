# Student V0.1 — FAN-IN A R2 Qualification Result

Status: **HOLD — INTEGRATION ORACLE REWORK REQUIRED**

Work package: `ATLAS-WP-032`  
Authority issue: #397  
Authoritative DRAFT PR: #398  
Integration branch: `student-v01/fanin-a-r2`

## 1. Fresh authority rebind

Immediately before this evidence-only mutation:

- Human Control Plane HEAD blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- UCP: `UCP-CONTROL-PLANE 1.1-R4`
- UCP SHA256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- UAO: `2.6`
- UAO SHA256: `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- GCP: `1.5`
- GCP SHA256: `d0a49d52d04ea158a6708f0f632bf426068f788a6f185ce5f4e24010c36061cd`
- Learn-it repository `main`: `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- PR #398 live executable head before this evidence-only commit: `7d261fd515b36f20865daea5a933c4ff3e7ffc16`
- PR #398 remains DRAFT and unmerged.

No authority drift invalidated the frozen R2 inputs.

## 2. Frozen inputs

- `FANIN_A_BASE = 21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- `R2_START_CANDIDATE = f4636e06279481b62ffd676ba70313c71283baeb`
- `WAVE1_COMMON_BASE = 27846dff52fde9b83434bca29bd8732ea42834bf`
- `JOB01_PREDECESSOR = d937592fb4d1e6dba6fcd02e290290f1a98cff71`
- `JOB01_R2 = ef3080e32e873170c6fd2fbdc72e93c31389cebb`
- `JOB02 = 6c91346d07c934cfb2917799084647b13e4fb931`
- `JOB03 = a90ba85857dded331e5e3952c2f181cbe2e6d689`

Fresh proof for PR #396:

- live head = exact `JOB01_R2`;
- PR remains open/unmerged;
- merge-base(`JOB01_PREDECESSOR`, `JOB01_R2`) = exact `JOB01_PREDECESSOR`;
- exact delta paths:
  - `apps/learnit-next/src/core/contract.js`
  - `apps/learnit-next/tests/student_v01_learning_runtime.py`
  - `work-packages/ATLAS-WP-031.json`

No JOB02/JOB03 role-owned file was modified by R2.

## 3. Byte-exact source reconstruction and manifest rebind

The previously blocked ordered source was recovered directly from authoritative Git object bytes rather than semantically reconstructed:

- path: `apps/learnit-next/src/integration/atlas/surface.js`
- exact Git blob: `ffa86b06d2efd62e9eddb734bcf83b59f76597b3`

The learner media module was also bound exactly:

- `apps/learnit-next/src/ui/media.js`
- exact Git blob: `1c84d5da04025cf372e3496fb7d25c088d1a0650`

R2 source-manifest rebind:

- `apps/learnit-next/src/core/contract.js` -> `784495bfe74bc33570b77a29f4ecce99a4c57f2a`
- provenance -> `JOB01:ef3080e32e873170c6fd2fbdc72e93c31389cebb`
- canonical manifest self SHA256 -> `c307eb996bc118eea98bac64174dc36a1f52bd8a1ce1128afcdbad897f49e525`
- exact manifest Git blob -> `37e4f9532d11798247f4a56ac8185a28c35ae5d5`
- manifest provenance -> `ATLAS-WP-032 JOB04 R2 deterministic integration rebind`

Manifest rebind commit:

- `1f98011a56dd143cf4f89fed243538355edaea75`

## 4. Minimum CI routing

The existing exact FAN-IN route covered only `student-v01/fanin-a`. R2 added only minimum integration-owned routing required to execute the exact new candidate:

- admit `student-v01/fanin-a-r2` to the existing `student-v01-fanin-a` routed profile;
- retain exact R1 behavior;
- bind R2 ancestry to `R2_START_CANDIDATE`;
- require remote branch head = exact target.

Final executable candidate before evidence-only mutation:

`RESULT_SHA = 7d261fd515b36f20865daea5a933c4ff3e7ffc16`

A temporary DRAFT PR #400 against `main` was used only as a GitHub Actions event carrier because PR #398 is stacked against `student-v01/fanin-a`. PR #400 is not integration authority and must not be merged.

Authoritative PR #398 changed paths at RESULT_SHA were exactly:

- `.github/workflows/learnit-next-ci.yml`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/src/core/contract.js`
- `apps/learnit-next/tests/student_v01_learning_runtime.py`
- `docs/programs/student-v0.1/FANIN_A_R2_INPUT_FREEZE.md`
- `docs/programs/student-v0.1/jobs/JOB_04_R2_WAVE1_FANIN_A.md`
- `work-packages/ATLAS-WP-031.json`
- `work-packages/ATLAS-WP-032.json`

This set is contained in `ATLAS-WP-032.scope.allowedPaths`.

## 5. Deterministic build

Exact candidate `7d261fd515b36f20865daea5a933c4ff3e7ffc16` was built independently in two exact-head CI runs:

- Learn-it Next CI run `35317110266` (#604)
- Learn-it Next CI run `35317121736` (#605)

Both produced exactly:

- path: `apps/learnit-next/dist/learnit-next.html`
- bytes: `474861`
- SHA256: `0b1e21038bc8f17521ecd604460781377a850b174907723a7d6af6174511310f`

Deterministic double-build: **PASS**.

## 6. Role and regression qualification

On the exact RESULT_SHA, both routed runs reached the same qualification state.

### JOB01 / runtime

`python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v`

Result:

- `STUDENT_V01_LEARNING_RUNTIME_PASS 92/92`
- standard SVG namespace admitted;
- malicious/external SVG remains fail-closed;
- v2 regression PASS;
- v3 constructed regression PASS;
- v4 evaluated/non-scored semantics PASS;
- secret boundary PASS.

### JOB02 / learner-safe presentation

`python -B apps/learnit-next/tests/student_v01_activity_presentation.py`

PASS markers:

- `STUDENT_V01_ACTIVITY_PRESENTATION_STATIC_PASS`
- `SECRET_BOUNDARY_STATIC_PASS`
- `MEDIA_FAIL_CLOSED_STATIC_PASS`
- `ACCESSIBLE_NON_DRAG_CONTROLS_STATIC_PASS`

`python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py`

PASS markers:

- `QCM_FILL_BROWSER_PASS`
- `LESSON_FLASHCARD_BROWSER_PASS`
- `MATCHING_ORDER_CLASSIFY_CONSTRUCTED_BROWSER_PASS`
- `MEDIA_SECRET_ACCESSIBILITY_BROWSER_PASS`
- `STUDENT_V01_ACTIVITY_PRESENTATION_BROWSER_PASS`

### JOB03 / v4 authoring, quality and Factory

`python -B authoring/v4/tests/test_validate_v4.py -v`

- 8/8 PASS.

`python -B authoring/v2/atlas/tests/test_pedagogical_quality.py -v`

- 6/6 PASS.

`python -B authoring/factory/tests/test_student_v01_v4.py -v`

- 3/3 PASS.

## 7. Cross-role E2E oracle — deterministic HOLD

The unchanged required oracle:

`python -B apps/learnit-next/tests/student_v01_fanin_a.py`

fails identically in both exact-head runs at line 124:

`assert [p["type"] for p in presentations] == list(FAMILIES)`

with `AssertionError`.

The failure is reproducible and occurs after all role suites above have passed.

### Root boundary identified

The unchanged oracle declares the expected family order as:

`qcm, fill, constructed, lesson, flashcard, matching, order, classify`

but its own authoritative representative input is produced by `make_valid_v4()`, whose activity list is:

`lesson, flashcard, matching, order, classify, qcm, fill, constructed`

`projectActivityPresentation()` projects each activity by type and preserves caller order; it does not impose or promise the oracle's alternate family ordering.

Therefore the current failure is an **integration-oracle ordering inconsistency**, not evidence of a JOB01/JOB02/JOB03 semantic repair requirement.

The prior R1 execution failed earlier at the SVG admission boundary, so this later latent oracle inconsistency had not yet become the stopping boundary.

## 8. No-silent-repair decision

`apps/learnit-next/tests/student_v01_fanin_a.py` is explicitly frozen/forbidden in `ATLAS-WP-032`.

R2 therefore does **not**:

- rewrite the oracle;
- reorder the canonical JOB03 representative package;
- change JOB01 projection semantics;
- change JOB02/JOB03 role code;
- reopen v4 schema or architecture.

A successor Control Room work package must decide the intended order invariant for the cross-role oracle and independently requalify it.

## 9. Governance and reservations

- Repository governance on exact candidate: **PASS**.
- Authoritative PR #398 static changed-path scope: **PASS**.
- Exact routed Learn-it Next integration CI: **FAIL**, solely because the required unchanged FAN-IN oracle fails at the ordering assertion described above.
- Full authoring-to-learner E2E proof: **FAIL / incomplete**, because the cross-role oracle stops before completing its UI/E2E continuation.
- No main merge, product promotion, Wave 2 launch or student use is authorized.
- Temporary CI carrier PR #400 must be closed without merge after this evidence is durably recorded.
- Rollback remains closure/deletion of R2 branch/PR; R1 candidate and frozen role heads remain recoverable.

## 10. Final result

```text
STUDENT_V01_JOB04_R2_FANIN_A_RESULT
FANIN_A_BASE: 21d25c36aec6c04fdfe8126c95e71cbf80771a1b
R2_START_CANDIDATE: f4636e06279481b62ffd676ba70313c71283baeb
WAVE1_COMMON_BASE: 27846dff52fde9b83434bca29bd8732ea42834bf
JOB01_PREDECESSOR_SHA: d937592fb4d1e6dba6fcd02e290290f1a98cff71
JOB01_R2_SHA: ef3080e32e873170c6fd2fbdc72e93c31389cebb
JOB02_SHA: 6c91346d07c934cfb2917799084647b13e4fb931
JOB03_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
RESULT_SHA: 7d261fd515b36f20865daea5a933c4ff3e7ffc16
ISSUE: 397
PR: 398
R2_START_IDENTITY: PASS
JOB01_R2_DELTA_IDENTITY: PASS
ROLE_TESTS: PASS
V2_REGRESSION: PASS
V3_REGRESSION: PASS
V4_END_TO_END: FAIL
NON_SCORED_LESSON_FLASHCARD: PASS
SECRET_BOUNDARY: PASS
STANDARD_SVG_NAMESPACE: PASS
MALICIOUS_SVG_FAIL_CLOSED: PASS
MEDIA: PASS
AUTHORING_TO_LEARNER: FAIL
REPOSITORY_GOVERNANCE: PASS
PR_SCOPE: PASS
INTEGRATION_CI: FAIL
SCOPE: PASS
FINAL_VERDICT: HOLD_STUDENT_V01_FANIN_A_R2_NEEDS_REWORK
```
