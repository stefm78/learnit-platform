# /AUDIT /SOLVE /BUILD — JOB 01
## Student V0.1 — Learning/runtime semantics

You are an independent Wave 1 implementation worker.

Do not use another Wave 1 branch as evidence or implementation input. Do not inspect JOB 02 or JOB 03 branches. You share only the frozen main authorities named below.

Repository: `stefm78/learnit-platform`
Authority issue: `#383`
Work package: `ATLAS-WP-027`
Pre-created branch: `student-v01/wave1-learning-runtime`

## 0. Reconstruct exact authority

Before editing:

1. fresh-read current control-plane/kernel authority required by the installed bootstrap;
2. fresh-read repository `main`;
3. verify `main` contains merged `ARC-WP-025`, `learnit.kit.v4`, the Wave 1 launch package and `WAVE1_INTERFACE_FREEZE.md`;
4. verify your branch started from the exact same Wave 1 launch base and contains no product change from another role;
5. bind that exact commit into `ATLAS-WP-027.baseline.requiredCommonWave1Base`.

Read as normative:
- `contracts/learnit-kit-v2.schema.json`
- `contracts/learnit-kit-v3.schema.json`
- `contracts/learnit-kit-v4.schema.json`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `docs/programs/student-v0.1/PROGRAM_CHARTER.md`
- `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
- `docs/programs/student-v0.1/WAVE1_HANDOFF.md`
- `work-packages/ATLAS-WP-027.json`

PR #376 may be inspected only as historical/reference evidence for the bounded constructed-response seam. Do not merge or cherry-pick it. Reimplement only what v4/current authority justifies.

## 1. Mission

Implement the Learning/runtime side of v4 while preserving v2/v3 exactly.

You own:
- explicit contract admission;
- normalization/evaluation or non-evaluated completion semantics;
- active-session advancement;
- learner-safe ActivityPresentation projection;
- progress/evidence behavior;
- runtime/import adversarial tests.

You do **not** own UI markup, CSS, raw DOM interaction, authoring, Factory, workflows or source-manifest fan-in.

## 2. Contract admission

Runtime/import must be explicit and fail closed:

```text
learnit.kit.v2 -> existing qcm/fill
learnit.kit.v3 -> existing qcm/fill + constructed
learnit.kit.v4 -> qcm/fill/constructed + lesson/flashcard/matching/order/classify + bounded media
other          -> reject
```

No automatic migration or rewrite. Existing v2 bytes and behavior remain valid.

## 3. Semantics

### qcm / fill
No semantic change.

### constructed
Preserve v3 first-slice semantics:
- response `{text}`;
- NFC + trim + collapse Unicode whitespace;
- otherwise exact case-sensitive comparison against hidden `acceptedResponses`;
- blank-after-normalization fails closed.

### matching
Validate a complete one-to-one response. Correct iff the normalized association set equals the hidden authored `matches` set exactly. Reject unknown IDs, duplicates, omissions and extra associations.

### order
Correct iff the submitted complete `orderedItemIds` sequence contains every authored item exactly once and equals hidden `correctOrder`. Reject duplicate/unknown/missing IDs.

### classify
Student V0.1 is single-label only. Correct iff every item occurs exactly once and the complete item→bucket mapping equals hidden `assignments`. Reject unknown item/bucket IDs, duplicates, omissions and multiple classifications.

### lesson
Response shape `{acknowledged:true}`. It advances the active session only. It has no correctness outcome and must not generate success/failure, validation, mastery, transfer or spaced-review evidence.

### flashcard
Response shape `{revealed:true}`. Same non-scored semantics as lesson. Reveal/completion must not become assessment evidence.

Prefer existing active-session persistence. Do not introduce a new persistent learner schema solely to count exposure. If the current architecture cannot safely advance/resume non-scored units without a persistence contract change, stop with `ARCHITECTURE_REOPEN_REQUIRED` instead of inventing one.

## 4. Learner-safe projection

Implement exactly the frozen shapes in `WAVE1_INTERFACE_FREEZE.md`.

No scoring secret may cross the boundary:
- qcm: no `correctChoiceId`;
- fill: no `answers`;
- constructed: no `acceptedResponses`;
- matching: no `matches`;
- order: no `correctOrder`;
- classify: no `assignments`.

For matching, if authored left/right positional order exactly exposes all correct pairs, deterministically rotate learner-safe `rightItems` before presentation. Do not use a kit-authored seed or nondeterministic network/service dependency.

Resolve embedded media references into the learner-safe media shape. Runtime/import must reject malformed references and unsafe active SVG content fail-closed; UI will independently sanitize again in JOB 02.

## 5. Progress/evidence protection

Challenge the existing progress/evidence code, do not assume it can accept non-scored interactions safely.

Prove:
- lesson/flashcard can be traversed and resumed;
- they never increment success/failure counters;
- they never satisfy validation readiness;
- they never become transfer or review evidence;
- scored activities still produce exactly the expected existing evidence semantics.

Do not change recommendation/memory/transfer modules unless strictly required and explicitly authorized by the work package. If required outside the declared scope, return HOLD rather than widening scope.

## 6. Write boundary

Change only paths authorized by `ATLAS-WP-027.json`.

In particular do not edit:
- `contracts/**`;
- `apps/learnit-next/src/ui/**`;
- CSS;
- `authoring/**`;
- `.github/**`;
- `apps/learnit-next/source_manifest.json`.

JOB 04 owns integration-only files.

## 7. Qualification

Create deterministic tests covering at minimum:
- v2 qcm/fill regression;
- v3 constructed behavior;
- v4 explicit admission;
- unknown contract/type rejection;
- matching positive + duplicate/unknown/omission attacks;
- order positive + duplicate/unknown/omission attacks;
- classify positive + duplicate/unknown/multiple-bucket/omission attacks;
- lesson/flashcard non-scored session advancement;
- no mastery/validation/review contamination from lesson/flashcard;
- exact learner-safe projection secret stripping for every scored type;
- matching positional-solution de-alignment;
- invalid/unsafe media rejection.

Run the relevant existing Learn-it Next unit/integration suites that your changes can affect. Do not repair unrelated failures outside scope.

## 8. PR / handoff

Use the pre-created branch and its existing draft PR if present. Do not merge.

At completion freeze exact result head and report changed paths, tests, limitations and rollback. Separate claims from evidence.

Return exactly one verdict:

`PASS_STUDENT_V01_JOB01_LEARNING_RUNTIME_READY_FOR_FANIN_A`

`HOLD_STUDENT_V01_JOB01_LEARNING_RUNTIME_NEEDS_REWORK`

`FAIL_STUDENT_V01_JOB01_RUNTIME_SEMANTICS_UNSAFE`

Final block:

```text
STUDENT_V01_JOB01_RESULT
BASE_SHA: <exact common Wave1 base>
RESULT_SHA: <exact head>
ISSUE: 383
PR: <number>
CONTRACT_ADMISSION: <PASS|FAIL>
V2_REGRESSION: <PASS|FAIL>
V3_CONSTRUCTED: <PASS|FAIL>
V4_EVALUATED_TYPES: <PASS|FAIL>
NON_SCORED_LESSON_FLASHCARD: <PASS|FAIL>
SECRET_BOUNDARY: <PASS|FAIL>
MEDIA_ADMISSION: <PASS|FAIL>
SCOPE: <PASS|FAIL>
FINAL_VERDICT: <exact token>
```
