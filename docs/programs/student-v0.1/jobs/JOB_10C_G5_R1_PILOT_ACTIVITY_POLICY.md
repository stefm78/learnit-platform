# /AUDIT /SOLVE /BUILD — JOB 10C
## Student V0.1 — G5 R1 Limited Pilot Activity Policy and Showcase repair

Repository: `stefm78/learnit-platform`  
Issue: `#435`  
Coordinator: `#431 / ATLAS-WP-050`  
Work package: `ATLAS-WP-053`

Branch:

`student-v01/g5-r1-pilot-activity-policy`

Exact common base:

`18b925436777943b19c4b031c24659ad60dee133`

Exact G4 showcase blob:

`03ed1d5819911c23734980f89716f4ca18a6bca4`

Exact source authority:
- commit `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- path `authoring/v2/atlas/nombres_complexes_atlas.json`
- blob `7f83784e8719917496a694b2ad170d724190fd04`
- SHA-256 `3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge or cherry-pick anything.

## Mission

Define the first limited Student V0.1 pilot activity profile without changing `learnit.kit.v4`.

Admitted in the limited pilot:
- lesson
- flashcard
- matching
- order
- classify
- qcm
- fill

Excluded from the limited pilot:
- constructed

Constructed remains supported by v4 outside this limited pilot.

The current mathematics showcase must be repaired accordingly and learner-facing internal/provenance jargon must be removed.

## Fresh authority

Before mutation:
- fresh-read HCP;
- fresh-read main;
- verify issue #435 / ATLAS-WP-053;
- verify exact common-base ancestry;
- verify source blob/hash;
- verify showcase blob;
- verify no sibling result from Stream A or B has been consumed.

Authority drift =>:
`HOLD_STUDENT_V01_G5_R1_PILOT_POLICY_AUTHORITY_DRIFT`.

## Pilot-profile document

Create:

`docs/programs/student-v0.1/STUDENT_V0_1_LIMITED_PILOT_ACTIVITY_PROFILE.md`

It must say clearly:
- this is a pilot admission profile, not a schema change;
- `constructed` remains part of v4;
- the limited pilot excludes free-text constructed because exact text matching is not a general mathematical semantic-equivalence mechanism;
- admitted families are lesson, flashcard, matching, order, classify, qcm, fill.

Do not change contracts or runtime support.

## Showcase repair

Start from exact G4 showcase.

The current course has:
- 11 activities;
- 42 estimated minutes;
- constructed at index 4;
- constructed estimatedMinutes = 3;
- two objectives:
  - `Calculer et interpréter un conjugué`
  - `Calculer et interpréter un module`.

### Remove constructed
Remove only the constructed activity at current index 4.

Do not replace it merely to preserve activity count or duration.

Expected minimal result:
- 10 activities;
- 39 estimated minutes;
- same two objectives;
- same remaining activity order.

The conjugate objective remains covered by:
- lesson;
- flashcard;
- matching;
- transfer qcm;
- validation qcm.

Prove this explicitly.

### Remove learner-facing internal jargon

At minimum remove or replace learner-facing/internal-program wording:
- `Student V0.1 Showcase`
- `kit canonique Atlas M1 0.3`
- `de la source`
- equivalent provenance/program wording exposed to the learner.

Preferred learner package title:

`Nombres complexes — Conjugué et module`

Use direct learner language.

Do not invent new mathematical facts.

## Revision/digest hygiene

Because package/course content changes:
- preserve lineage IDs;
- rotate/recompute package revision identity/digest;
- rotate/recompute course revision identity/digest;
- rotate/recompute only changed remaining activities if learner-visible content changed;
- keep unchanged activity revision identities stable where canonical rules permit.

Use canonical repository digest tooling/logic only.

Do not hand-invent digests.

## Author-side evidence

Regenerate/rebind as needed:
- `AUTHOR_AUDIT.md`
- `PROVENANCE_MAP.json`
- `SOURCE_BASIS.md`
- `V4_VALIDATION_REPORT.json`
- `PEDAGOGICAL_QUALITY_REPORT.json`
- `FACTORY_CONTEXT.json`
- `FACTORY_REVIEW_REQUEST.md`

Do not change source bytes.

## Mandatory checks

Require:
- activity count 10;
- estimatedMinutes 39;
- no activity type `constructed`;
- every remaining family belongs to admitted pilot profile;
- both objective IDs and labels unchanged;
- remaining activity order preserved;
- validation independence preserved;
- source fidelity preserved;
- internal-jargon scan PASS;
- no `acceptedResponses` workaround added;
- V4 canonical PASS;
- pedagogical quality accepted high band;
- revision/digest hygiene PASS;
- provenance/source traceability PASS;
- source blob/hash unchanged;
- secret boundary PASS.

## Semantic-review firewall

This is an authoring session.

Do not claim independent semantic PASS.

Historical G3 semantic review cannot be reused as proof for changed learner bytes.

The final author-side qualification must state exactly:

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_CORRECTIVE_REVIEW`

A later independent gate owns semantic review and fan-in.

## CI

Add only a minimum bounded branch route if required.

Require:
- exact base ancestry;
- source identity;
- scope;
- canonical validation;
- jargon scan;
- pilot profile check;
- duration/activity-count check;
- objective coverage check;
- revision/digest hygiene;
- quality;
- governance.

Same-head DRAFT carrier to main may be used only as CI transport and must be closed unmerged.

## Result/evidence split

Freeze repaired author candidate as:

`POLICY_RESULT_SHA`

Then add only:

`qualification/STUDENT_V01_G5_R1_PILOT_ACTIVITY_POLICY_RESULT.md`

and record:

`POLICY_EVIDENCE_HEAD`.

Return exactly:

```text
STUDENT_V01_G5_R1_PILOT_ACTIVITY_POLICY_RESULT
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
RESULT_SHA: <sha>
EVIDENCE_HEAD: <sha>
ISSUE: 435
PR: <pr>
PILOT_PROFILE: PASS|FAIL
CONSTRUCTED_EXCLUDED_FROM_PILOT: PASS|FAIL
V4_CONTRACT_UNCHANGED: PASS|FAIL
SHOWCASE_ACTIVITY_COUNT: 10|OTHER
SHOWCASE_DURATION_MINUTES: 39|OTHER
OBJECTIVES_UNCHANGED: PASS|FAIL
OBJECTIVE_COVERAGE: PASS|FAIL
REMAINING_ORDER_UNCHANGED: PASS|FAIL
INTERNAL_JARGON_REMOVED: PASS|FAIL
NO_ACCEPTED_RESPONSES_WORKAROUND: PASS|FAIL
SOURCE_UNCHANGED: PASS|FAIL
REVISION_DIGEST_HYGIENE: PASS|FAIL
V4_CANONICAL: PASS|FAIL
PEDAGOGICAL_QUALITY: PASS|FAIL
SOURCE_TRACEABILITY: PASS|FAIL
SEMANTIC_REVIEW: PENDING_INDEPENDENT_CORRECTIVE_REVIEW
INTEGRATION_CI: PASS|FAIL
REPOSITORY_GOVERNANCE: PASS|FAIL
SCOPE: PASS|FAIL
FINAL_VERDICT: <token>
```

Allowed verdicts:
- `PASS_STUDENT_V01_G5_R1_PILOT_POLICY_READY_FOR_INDEPENDENT_REVIEW`
- `HOLD_STUDENT_V01_G5_R1_PILOT_POLICY_AUTHORITY_DRIFT`
- `HOLD_STUDENT_V01_G5_R1_PILOT_POLICY_NEEDS_REWORK`
- `FAIL_STUDENT_V01_G5_R1_PILOT_POLICY_SCOPE_VIOLATION`

PASS authorizes only later independent semantic review/integration.
