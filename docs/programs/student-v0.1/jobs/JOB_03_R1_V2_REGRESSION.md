# JOB 03 R1 — Requalify and repair V2 regression without widening scope

## Role
You are the corrective worker for Student V0.1 JOB 03 only.

This is a bounded rework of the existing authoring/Factory/quality branch. Do not redo the architecture and do not touch learner runtime/UI or central CI routing.

## Fixed authority

- Repository: `stefm78/learnit-platform`
- Parent program issue: `#380`
- Role issue: `#385`
- Work package: `ATLAS-WP-029`
- Role PR: `#389`
- Role branch: `student-v01/wave1-authoring-factory`
- Common Wave 1 base: `27846dff52fde9b83434bca29bd8732ea42834bf`
- Held head to start from: `a90ba85857dded331e5e3952c2f181cbe2e6d689`
- Frozen interface: `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
- Original role prompt: `docs/programs/student-v0.1/jobs/JOB_03_AUTHORING_FACTORY.md`

Do not inspect or modify JOB 01 or JOB 02 branches.

## Observed corrective trigger

The prior result reported:

- `V4_VALIDATOR: PASS`
- `NEW_ACTIVITY_SEMANTICS: PASS`
- `PEDAGOGICAL_QUALITY: PASS`
- `FACTORY: PASS`
- `V2_REGRESSION: FAIL`
- `MEDIA_VALIDATION: PASS`
- `SCOPE: PASS`
- final verdict HOLD.

The exact PR `#389` head is `a90ba85857dded331e5e3952c2f181cbe2e6d689`.

Repository CI also shows a separate generic `Learn-it Next CI` failure whose exact diagnostic is:

`Unknown branch reached Learn-it Next CI without a workflow audit change.`

That routing failure is **not itself proof of a V2 semantic regression** and `.github/**` is outside JOB 03 scope. Do not modify central workflows to silence it.

## Mission

1. Start from exact held head `a90ba85857dded331e5e3952c2f181cbe2e6d689` on PR `#389`.
2. Reproduce the prior `V2_REGRESSION: FAIL` with the exact repository-authoritative V2 authoring, pedagogical-quality and Factory regression commands. Record the exact failing command/test and failure text.
3. Distinguish two cases:
   - **REAL_V2_REGRESSION**: an existing V2 behavior/test actually fails because of JOB 03 changes. Repair it minimally within `ATLAS-WP-029.scope.allowedPaths`, then rerun all JOB 03 qualification.
   - **MISCLASSIFIED_INFRA_FAILURE**: all exact V2 regressions pass and the prior FAIL was only the generic unrecognized-branch CI router signal. In that case, do not change product code just to create a new SHA; retain the current exact head if appropriate and publish the corrected evidence classification.
4. Preserve all existing V4 PASS behavior while fixing/reclassifying V2 regression.
5. Do not edit `.github/**`, `apps/**`, `contracts/**`, `authoring/v2/validate_kit.py` or `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V2.md`.
6. Do not merge PR `#389`.

## Required regression proof

The R1 result must report separately:

- the exact V2 regression commands executed;
- `V2_REGRESSION = PASS|FAIL` based on those commands only;
- `GENERIC_LEARNIT_NEXT_CI = PASS|FAIL|OUT_OF_SCOPE_ROUTER_FAILURE`;
- whether the corrective classification was `REAL_V2_REGRESSION` or `MISCLASSIFIED_INFRA_FAILURE`;
- exact PR `#389` head after any repair;
- changed-path scope check against `ATLAS-WP-029`.

Do not collapse repository routing and semantic regression into one status.

## Preservation gates

After any repair, all of these must still pass:

- V4 canonical validator positive/adversarial fixtures;
- matching/order/classify semantic validation;
- lesson/flashcard remain non-scored learning exposure;
- pedagogical-quality rules do not count lesson/flashcard as validation evidence;
- Factory V4 support preserves source-fidelity/semantic review requirements;
- embedded media validation remains fail-closed;
- V2 authoring/quality/Factory regression is exact PASS;
- scope remains exact PASS.

## Adversarial checks

Qualification must fail if:

- `.github/**` is edited to make JOB 03 green;
- V2 semantics are weakened or bypassed instead of preserved;
- existing V2 authoring skill/validator authority is rewritten;
- a generic branch-router failure is reported as a V2 semantic failure without an actual failing V2 test;
- a real V2 failing test is dismissed as infrastructure noise;
- V4 PASS is lost while repairing V2;
- changed paths exceed `ATLAS-WP-029.scope.allowedPaths`.

## Final output

Return exactly one result block in this shape:

```text
STUDENT_V01_JOB03_R1_RESULT
BASE_SHA: 27846dff52fde9b83434bca29bd8732ea42834bf
START_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
RESULT_SHA: <exact PR-389 head SHA40>
ISSUE: 385
PR: 389
REGRESSION_CLASSIFICATION: REAL_V2_REGRESSION|MISCLASSIFIED_INFRA_FAILURE
V4_VALIDATOR: PASS|FAIL
NEW_ACTIVITY_SEMANTICS: PASS|FAIL
PEDAGOGICAL_QUALITY: PASS|FAIL
FACTORY: PASS|FAIL
V2_REGRESSION: PASS|FAIL
GENERIC_LEARNIT_NEXT_CI: PASS|FAIL|OUT_OF_SCOPE_ROUTER_FAILURE
MEDIA_VALIDATION: PASS|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: PASS_STUDENT_V01_JOB03_R1_READY_FOR_FANIN_A|HOLD_STUDENT_V01_JOB03_R1_NEEDS_REWORK
```

A PASS verdict requires an exact PR head, exact V2 regression PASS, preserved V4 PASS and scope PASS. The generic CI router may remain `OUT_OF_SCOPE_ROUTER_FAILURE` if its failure is solely the unrecognized-branch routing guard and no JOB 03-owned workflow edit is justified.
