# /AUDIT /SOLVE /BUILD — JOB 04
## Learn-it Student V0.1 — Controlled Wave 1 FAN-IN A

Repository: `stefm78/learnit-platform`

Authority issue: `#391`

Work package: `ATLAS-WP-030`

This is an integration job, not a new implementation stream.

## 0. GOVERNANCE / FRESH REBIND

Before any mutation:

1. Re-read the active Human Control Plane authority.
2. Re-read current `main`.
3. Re-read:
   - `GOVERNANCE.md`
   - `governance/governor-state.json`
   - `work-packages/ATLAS-WP-030.json`
   - `docs/programs/student-v0.1/FANIN_A_INPUT_FREEZE.md`
   - `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
   - `contracts/learnit-kit-v2.schema.json`
   - `contracts/learnit-kit-v3.schema.json`
   - `contracts/learnit-kit-v4.schema.json`
4. Bind the exact current `main` as `FANIN_A_BASE`.
5. Do not assume any SHA from chat state except the frozen child-head SHAs below.

Fail closed on authority drift or if the launch package containing this prompt is not on current `main`.

## 1. FROZEN INPUTS

Shared Wave 1 base:

`27846dff52fde9b83434bca29bd8732ea42834bf`

Accepted role inputs:

- JOB 01 / PR #387: `d937592fb4d1e6dba6fcd02e290290f1a98cff71`
- JOB 02 / PR #388: `6c91346d07c934cfb2917799084647b13e4fb931`
- JOB 03 / PR #389: `a90ba85857dded331e5e3952c2f181cbe2e6d689`

For each PR, re-read the live PR and prove:
- it still targets `main`;
- it is still unmerged;
- its live head equals the frozen SHA exactly;
- its merge-base with the shared Wave 1 base is the expected base;
- its changed-path set exactly matches `FANIN_A_INPUT_FREEZE.md`.

If any check fails, stop with:

`HOLD_STUDENT_V01_FANIN_A_INPUT_DRIFT`

Do not substitute a newer branch head.

## 2. PATH-INDEPENDENCE PROOF

Compute the three changed-path sets from the shared Wave 1 base to the three exact frozen heads.

Required:
- JOB01 ∩ JOB02 = empty
- JOB01 ∩ JOB03 = empty
- JOB02 ∩ JOB03 = empty

If any intersection exists, stop with:

`HOLD_STUDENT_V01_FANIN_A_PATH_CONFLICT`

Do not auto-resolve it.

## 3. CREATE THE INTEGRATION BRANCH

Create:

`student-v01/fanin-a`

from exact `FANIN_A_BASE`.

Open one DRAFT PR to `main` governed by `ATLAS-WP-030`.

Do not merge PR #387, #388 or #389 directly to main.

## 4. COMBINATION RULE

Combine only the reviewed deltas from the three frozen role heads.

The integration branch must contain the exact semantic child changes relative to the common Wave 1 base while preserving all current-main coordination/governance changes made after that base.

Preferred order for deterministic provenance:
1. JOB 01 exact delta
2. JOB 02 exact delta
3. JOB 03 exact delta

Because the child path sets are frozen as disjoint, any semantic conflict indicates unexpected drift or hidden coupling and must HOLD.

No-silent-repair rule:
- do not improve role code;
- do not refactor for taste;
- do not redesign interfaces;
- do not change v4 contract;
- do not edit `WAVE1_INTERFACE_FREEZE.md`;
- do not fix a child defect inside JOB 04.

If a child defect is exposed, identify its owning role and return:

`HOLD_STUDENT_V01_FANIN_A_CONFLICT_REQUIRES_ROLE_REWORK`

## 5. INTEGRATION-OWNED WIRING

After the three exact deltas are combined, add only the minimum wiring required to make the combined candidate buildable and exactly testable.

Authorized integration-owned paths only:
- `.github/workflows/learnit-next-ci.yml`
- `apps/learnit-next/build.py`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/tests/student_v01_fanin_a.py`
- `qualification/STUDENT_V01_FANIN_A_RESULT.md`

Use these only when necessary.

The generic role-branch CI failures observed during Wave 1 were router/infrastructure reservations. JOB 04 may add the smallest explicit route needed for `student-v01/fanin-a` / its exact integration candidate. Do not generalize this into a new CI framework.

## 6. REQUIRED INTEGRATION QUALIFICATION

Run all unchanged role-specific tests that qualified JOB 01, JOB 02 and JOB 03 on the combined head.

Then add/run an end-to-end FAN-IN A qualification that covers at minimum:

### Contract admission
- v2 still admits only its existing semantics;
- v3 constructed still behaves exactly as frozen;
- v4 is explicit and fail-closed;
- unknown contract/activity types reject.

### Activity pipeline
For every Student V0.1 family:
- qcm
- fill
- constructed
- lesson
- flashcard
- matching
- order
- classify

prove the path:

`canonical kit -> runtime admission -> learner-safe ActivityPresentation -> UI response shape -> Learning evaluation/completion`

### Non-scored semantics
For lesson and flashcard prove:
- session can advance;
- no correctness PASS/FAIL is created;
- no validation evidence;
- no mastery evidence;
- no transfer evidence;
- no spaced-review evidence.

### Secret boundary
Prove learner-safe presentation never exposes:
- `correctChoiceId`
- fill authored `answers`
- constructed `acceptedResponses`
- matching `matches`
- order `correctOrder`
- classify authored `assignments`

### Matching/order/classify
Prove malformed, duplicate, omitted, extra and unknown IDs fail closed.

### Media
Prove:
- embedded/local only;
- allowed formats only;
- alt text preserved;
- unsafe SVG fails closed at validation/import and defensive UI boundary;
- no remote URL dependency.

### Authoring -> learner path
Create at least one deterministic v4 fixture that is accepted by the v4 authoring validator/quality layer and then successfully enters learner runtime/presentation without contract mutation.

### Regression
Run the relevant v2 and v3 regression suites and record exact commands/results.

## 7. CI / SCOPE / EXACT-HEAD EVIDENCE

Before final verdict prove on the exact final PR head:
- Repository governance = PASS;
- PR scope = PASS;
- exact integration CI route = PASS;
- no forbidden paths changed;
- no child PR was merged to main;
- the three child PR heads still equal the frozen SHAs;
- current main has not moved incompatibly since `FANIN_A_BASE` was bound.

If `main` moves during execution, re-evaluate merge-base/CAS safety. Do not silently rebase the candidate and claim the old evidence still applies.

## 8. RESULT ARTIFACT

Create:

`qualification/STUDENT_V01_FANIN_A_RESULT.md`

It must bind:
- `FANIN_A_BASE`
- shared Wave 1 base
- three accepted child PR numbers and exact SHAs
- integration branch
- final `RESULT_SHA`
- exact changed-path list
- exact integration-only paths
- test commands and results
- v2 regression
- v3 regression
- all v4 family checks
- non-scored lesson/flashcard evidence
- secret-boundary evidence
- media evidence
- CI/governance/scope evidence
- reservations
- rollback
- final verdict.

## 9. OUTPUT BLOCK

Return exactly this block, populated with real values:

```text
STUDENT_V01_JOB04_FANIN_A_RESULT
FANIN_A_BASE: <sha>
WAVE1_COMMON_BASE: 27846dff52fde9b83434bca29bd8732ea42834bf
JOB01_SHA: d937592fb4d1e6dba6fcd02e290290f1a98cff71
JOB02_SHA: 6c91346d07c934cfb2917799084647b13e4fb931
JOB03_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
RESULT_SHA: <sha>
ISSUE: 391
PR: <number>
PATH_INDEPENDENCE: PASS|FAIL
CHILD_DELTA_IDENTITY: PASS|FAIL
ROLE_TESTS: PASS|FAIL
V2_REGRESSION: PASS|FAIL
V3_REGRESSION: PASS|FAIL
V4_END_TO_END: PASS|FAIL
NON_SCORED_LESSON_FLASHCARD: PASS|FAIL
SECRET_BOUNDARY: PASS|FAIL
MEDIA: PASS|FAIL
AUTHORING_TO_LEARNER: PASS|FAIL
REPOSITORY_GOVERNANCE: PASS|FAIL
PR_SCOPE: PASS|FAIL
INTEGRATION_CI: PASS|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

## 10. FINAL VERDICT

Return exactly one:

`PASS_STUDENT_V01_FANIN_A_READY_FOR_WAVE2`

`HOLD_STUDENT_V01_FANIN_A_CONFLICT_REQUIRES_ROLE_REWORK`

`HOLD_STUDENT_V01_FANIN_A_INPUT_DRIFT`

`HOLD_STUDENT_V01_FANIN_A_NEEDS_REWORK`

`FAIL_STUDENT_V01_FANIN_A_ARCHITECTURE_REOPEN_REQUIRED`

PASS means the exact integrated Wave 1 candidate is ready for Control Room review and Wave 2 launch preparation only.

PASS does not authorize merge to main, Wave 2 execution, product promotion or student use.
