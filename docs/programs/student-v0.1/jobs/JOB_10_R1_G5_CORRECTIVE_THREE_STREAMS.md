# /AUDIT /SOLVE /BUILD — JOB 10 R1 COORDINATION
## Student V0.1 — prepare three independent corrective jobs

Repository: `stefm78/learnit-platform`  
Coordinator issue: `#431`  
Coordinator work package: `ATLAS-WP-050`

Exact common base:

`18b925436777943b19c4b031c24659ad60dee133`

G4 candidate:

`757ed15e840bfca603de0eac3bef1e9d5ff3483d`

G5 replay prep:

`a72897c209b8ea7bd8672cc8a95be939ecee6fb8`

## Coordination decision

Do **not** execute the corrective streams in one conversation.

The correct topology is:

```text
COORDINATOR
   ├── separate session A → ATLAS-WP-051 / APP EXPERIENCE R1
   ├── separate session B → ATLAS-WP-052 / ACTIVITY EXPERIENCE LAB V1
   └── separate session C → ATLAS-WP-053 / PILOT ACTIVITY POLICY R1
```

All three child branches start from the same exact common base and must not consume one another.

The coordinator is control-only.

## Prepared child jobs

### A — App Experience R1
- issue: #433
- PR: #436
- branch: `student-v01/g5-r1-app-experience`
- work package: `ATLAS-WP-051`
- prompt: `docs/programs/student-v0.1/jobs/JOB_10A_G5_R1_APP_EXPERIENCE.md`

Owns:
- truthful post-import state;
- app/library/navigation hierarchy;
- compact per-objective progress buckets;
- progress disclosure;
- resume/recovery.

Does not own activity presenter interaction design.

### B — Activity Experience Lab V1
- issue: #434
- PR: #437
- branch: `student-v01/g5-r1-activity-experience-lab`
- work package: `ATLAS-WP-052`
- prompt: `docs/programs/student-v0.1/jobs/JOB_10B_ACTIVITY_EXPERIENCE_LAB_V1.md`

Owns:
- isolated fail-fast prototype lab;
- `ActivityPresentation -> prototype -> ActivityResponse`;
- multiple variants;
- keyboard/mobile/accessibility;
- human prototype selection.

Must stop before production presenter implementation.

### C — Limited Pilot Activity Policy R1
- issue: #435
- PR: #438
- branch: `student-v01/g5-r1-pilot-activity-policy`
- work package: `ATLAS-WP-053`
- prompt: `docs/programs/student-v0.1/jobs/JOB_10C_G5_R1_PILOT_ACTIVITY_POLICY.md`

Owns:
- limited-pilot family profile;
- constructed excluded from first pilot while remaining supported by v4;
- removal of current constructed showcase activity;
- 42 → 39 minute journey;
- learner-facing jargon cleanup;
- author-side evidence only;
- independent semantic review deferred.

## Prerequisites for later ATLAS-WP-054

Do not prepare or execute ATLAS-WP-054 until all are true:

1. Stream A returns accepted PASS.
2. Stream B Phase A returns a valid Lab bundle and the human freezes an explicit prototype selection.
3. Stream C returns author-side PASS.
4. Stream C receives a later independent semantic PASS on the changed exact learner content.
5. No cross-consumption/scope defect exists.

Then ATLAS-WP-054 may:
- implement only the human-selected Activity Lab variants in production;
- consume exact Stream A result;
- consume exact independently accepted Stream C result;
- fan-in;
- qualify a new G4 R1 candidate;
- prepare a replacement G5 replay only after G4 R1 PASS.

## G5 boundary

G5 remains:

`PENDING_HUMAN`

The engineering findings do not constitute a formal G5 GO/HOLD decision.

## Coordinator stop

Once the three child jobs are identity-bound, governance-clean, separately packaged and ready for separate conversations, the coordinator stops.

Return:

```text
STUDENT_V01_JOB10_R1_COORDINATION_RESULT
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
COORDINATOR_ISSUE: 431
COORDINATOR_PR: 432
APP_ISSUE: 433
APP_PR: 436
APP_WP: ATLAS-WP-051
APP_READY_FOR_SEPARATE_EXECUTION: PASS|FAIL
LAB_ISSUE: 434
LAB_PR: 437
LAB_WP: ATLAS-WP-052
LAB_READY_FOR_SEPARATE_EXECUTION: PASS|FAIL
POLICY_ISSUE: 435
POLICY_PR: 438
POLICY_WP: ATLAS-WP-053
POLICY_READY_FOR_SEPARATE_EXECUTION: PASS|FAIL
ALL_CHILDREN_SAME_BASE: PASS|FAIL
CHILD_PREP_GOVERNANCE: PASS|FAIL
OLD_PLAN_SUPERSEDED: PASS|FAIL
G5_FORMAL_STATUS: PENDING_HUMAN
NEXT_STEP: EXECUTE_THREE_CHILD_JOBS_IN_SEPARATE_SESSIONS
FINAL_VERDICT: PASS_STUDENT_V01_JOB10_R1_COORDINATION_COMPLETE|FAIL_STUDENT_V01_JOB10_R1_COORDINATION
```

This coordinator does not execute child implementation.
