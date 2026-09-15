# JOB 01 R1 — Publish durable Learning/runtime result

## Role
You are the corrective worker for Student V0.1 JOB 01 only.

This is **not** a new architecture exercise and **not** FAN-IN A. Your first responsibility is to turn the previously narrated JOB 01 result into exact durable Git evidence on the already-authorized role branch.

## Fixed authority

- Repository: `stefm78/learnit-platform`
- Parent program issue: `#380`
- Role issue: `#383`
- Work package: `ATLAS-WP-027`
- Role PR: **`#387`**
- Role branch: `student-v01/wave1-learning-runtime`
- Common Wave 1 base: `27846dff52fde9b83434bca29bd8732ea42834bf`
- Frozen interface: `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
- Original role prompt: `docs/programs/student-v0.1/jobs/JOB_01_LEARNING_RUNTIME.md`

Do not inspect or modify JOB 02 or JOB 03 branches.

## Observed corrective trigger

The prior result reported:

- `RESULT_SHA: NOT_PUBLISHED`
- `PR: 385`
- semantic checks reported PASS
- final verdict HOLD.

Current durable Git evidence shows PR `#387` is the actual JOB 01 role PR and its visible delta from the common base contains only `work-packages/ATLAS-WP-027.json`. Therefore the earlier semantic PASS claims are not yet admissible for FAN-IN A.

## Mission

1. Bind the exact common base and current role branch.
2. Recover any already-completed local JOB 01 implementation if it still exists. Do **not** rewrite working code merely to create a different result.
3. If the implementation was never durably published, publish the minimum correct JOB 01 implementation to `student-v01/wave1-learning-runtime` under the exact `ATLAS-WP-027` write scope.
4. If local work is unavailable, reconstruct JOB 01 from the original role prompt and frozen interface, still within the exact role scope.
5. Run the exact role qualification again on the **published head**.
6. Verify the published head is the head of PR `#387` and is a full lowercase SHA-40.
7. Do not merge the PR.

## Scope invariants

All original `ATLAS-WP-027` invariants remain binding. In particular:

- no UI/CSS ownership;
- no authoring/Factory ownership;
- no contract schema mutation;
- no `.github/**`, source-manifest or central workflow edits;
- lesson/flashcard remain non-scored;
- scoring/correctness secrets must not cross learner-safe presentation;
- v2 and v3 behavior must remain regression-safe;
- v4 matching/order/classify evaluation remains fail-closed.

A publication problem is not permission to broaden scope.

## Required evidence

The final published head must prove:

- exact base ancestry from `27846dff52fde9b83434bca29bd8732ea42834bf`;
- PR `#387` head equals `RESULT_SHA`;
- changed paths are a subset of `ATLAS-WP-027.scope.allowedPaths`;
- `CONTRACT_ADMISSION = PASS`;
- `V2_REGRESSION = PASS`;
- `V3_CONSTRUCTED = PASS`;
- `V4_EVALUATED_TYPES = PASS`;
- `NON_SCORED_LESSON_FLASHCARD = PASS`;
- `SECRET_BOUNDARY = PASS`;
- `MEDIA_ADMISSION = PASS`;
- `SCOPE = PASS`.

If any semantic test fails after publication, repair only within JOB 01 scope and rerun. Do not report PASS from an unpublished worktree.

## Adversarial checks

Qualification must fail if any of the following is true:

- `RESULT_SHA` is absent, synthetic, local-only or not the PR `#387` head;
- the result names PR `#385` or any PR other than `#387`;
- only the work-package metadata is published while implementation remains local;
- any forbidden path changes;
- lesson/flashcard emit correctness/mastery/validation evidence;
- any scoring secret appears in learner-safe projection;
- v2 or v3 regression is not exact PASS.

## Final output

Return exactly one result block in this shape:

```text
STUDENT_V01_JOB01_R1_RESULT
BASE_SHA: 27846dff52fde9b83434bca29bd8732ea42834bf
RESULT_SHA: <exact published PR-387 head SHA40>
ISSUE: 383
PR: 387
CONTRACT_ADMISSION: PASS|FAIL
V2_REGRESSION: PASS|FAIL
V3_CONSTRUCTED: PASS|FAIL
V4_EVALUATED_TYPES: PASS|FAIL
NON_SCORED_LESSON_FLASHCARD: PASS|FAIL
SECRET_BOUNDARY: PASS|FAIL
MEDIA_ADMISSION: PASS|FAIL
SCOPE: PASS|FAIL
DURABILITY: PASS|FAIL
FINAL_VERDICT: PASS_STUDENT_V01_JOB01_R1_READY_FOR_FANIN_A|HOLD_STUDENT_V01_JOB01_R1_NEEDS_REWORK
```

Use PASS only when the exact published Git head supports the claim.
