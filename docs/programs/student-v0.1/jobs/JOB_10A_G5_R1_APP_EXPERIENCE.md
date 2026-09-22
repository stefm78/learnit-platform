# /AUDIT /SOLVE /BUILD — JOB 10A
## Student V0.1 — G5 R1 App Experience repair

Repository: `stefm78/learnit-platform`  
Issue: `#433`  
Coordinator: `#431 / ATLAS-WP-050`  
Work package: `ATLAS-WP-051`

Branch:

`student-v01/g5-r1-app-experience`

Exact common base:

`18b925436777943b19c4b031c24659ad60dee133`

Exact G4 candidate:

`757ed15e840bfca603de0eac3bef1e9d5ff3483d`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge or cherry-pick anything.

## Mission

Repair only the application-level learner experience surrounding the activity surface.

Owned defects:
1. misleading `Aucun parcours Atlas installé` after rich V4 import;
2. verbose objective progress/recommendation content dominates the active activity;
3. compact per-objective acquired/not-acquired progress is no longer immediately readable;
4. resume/recovery/navigation hierarchy must remain clear.

Not owned here:
- lesson/flashcard/matching/order/classify interaction design;
- activity response semantics;
- scoring;
- showcase content;
- pilot family admission policy.

## Fresh authority

Before mutation:
- fresh-read HCP;
- fresh-read main;
- verify issue #433 / ATLAS-WP-051;
- verify branch ancestry exactly from common base;
- verify G4/G5 Phase-A anchors remain unchanged;
- verify `apps/learnit-next/src/ui/activity_presenters.js` blob remains `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`.

If authority drifts, stop with:
`HOLD_STUDENT_V01_G5_R1_APP_EXPERIENCE_AUTHORITY_DRIFT`.

## Baseline reproduction

Reproduce the exact G4 problems before editing:
- rich V4 course installed while legacy Atlas shell says no Atlas course;
- active session inserts full objective progress/recommendation before the current activity.

Record deterministic repro evidence in tests.

## Required repair

### Truthful installed-course state
Do not widen the legacy planner.

If a rich V4 course is installed but not planner-compatible:
- do not show a learner-facing false empty diagnosis;
- prioritize actual installed course/library state;
- do not expose internal planner compatibility jargon.

A true empty state is allowed only when no learner course is installed.

### Activity-first hierarchy
During an active journey:
- current activity heading + activity must be primary;
- compact overall progress may remain;
- full objective detail must not precede the activity;
- detailed objective evidence belongs behind a collapsed `Voir ma progression` disclosure;
- `Prochaine action recommandée` must not compete with an already-active activity.

### Compact objective buckets
Use current objective-progress state only.

Show every objective with:
- compact visual bucket/reservoir;
- objective label;
- accessible textual state.

Map current canonical states to learner language:
- `not-started` -> `À découvrir`
- `training` -> `En apprentissage`
- `review-needed` -> `À renforcer`
- `ready-for-validation` -> `À confirmer`
- `validated-recently` -> `Acquis récemment`

Do not rely on color alone.

### Resume/recovery
Preserve:
- current course;
- current activity;
- resume;
- completion persistence;
- recovery behavior.

## Strict boundaries

Allowed product payload paths are exactly those in ATLAS-WP-051.

Forbidden:
- activity presenter modifications;
- core activity/scoring semantics;
- contracts;
- showcase;
- authoring;
- pilot/QA payload;
- build.py/index.template/source_manifest changes unless the WP explicitly permits them (it does not).

## Tests

Add deterministic static/browser tests that fail on the G4 baseline and pass only after repair.

Require:
- no false Atlas empty state with installed rich V4;
- activity precedes verbose progress detail;
- compact bucket per objective;
- accessible state text;
- detail collapsed by default;
- desktop/mobile layout;
- keyboard disclosure;
- persistence/reload/resume/completion;
- all rich activity families remain functional;
- secret boundary unchanged.

Run existing relevant Student V0.1 suites unchanged.

Build twice and record the new exact app bytes/SHA-256.

## CI

Recompose the minimum bounded Learn-it Next CI route for this branch only if needed.

Require:
- exact base ancestry;
- remote head binding;
- scope checks;
- new tests;
- relevant regressions;
- deterministic double build;
- Repository governance.

A same-head temporary DRAFT carrier to main is allowed only as CI transport and must be closed unmerged.

## Result/evidence split

Freeze executable/tested repair as:

`APP_RESULT_SHA`

Then add only:

`qualification/STUDENT_V01_G5_R1_APP_EXPERIENCE_RESULT.md`

as evidence and record:

`APP_EVIDENCE_HEAD`.

Return exactly:

```text
STUDENT_V01_G5_R1_APP_EXPERIENCE_RESULT
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
RESULT_SHA: <sha>
EVIDENCE_HEAD: <sha>
ISSUE: 433
PR: <pr>
FALSE_EMPTY_STATE: PASS|FAIL
ACTIVITY_PRIMARY: PASS|FAIL
COMPACT_OBJECTIVE_BUCKETS: PASS|FAIL
PROGRESSIVE_DISCLOSURE: PASS|FAIL
RESUME_RECOVERY: PASS|FAIL
ACTIVITY_PRESENTERS_UNCHANGED: PASS|FAIL
CORE_SEMANTICS_UNCHANGED: PASS|FAIL
PRODUCT_REGRESSIONS: PASS|FAIL
APP_BUILD_SHA256: <sha>
APP_BUILD_BYTES: <int>
INTEGRATION_CI: PASS|FAIL
REPOSITORY_GOVERNANCE: PASS|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed verdicts:
- `PASS_STUDENT_V01_G5_R1_APP_EXPERIENCE_READY_FOR_INTEGRATION`
- `HOLD_STUDENT_V01_G5_R1_APP_EXPERIENCE_AUTHORITY_DRIFT`
- `HOLD_STUDENT_V01_G5_R1_APP_EXPERIENCE_NEEDS_REWORK`
- `FAIL_STUDENT_V01_G5_R1_APP_EXPERIENCE_SCOPE_VIOLATION`

PASS authorizes only later ATLAS-WP-054 integration.
