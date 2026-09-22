# /AUDIT /SOLVE /BUILD — JOB 10 R1
## Student V0.1 — G5 corrective wave R1: App Experience + Activity Experience Lab + Pilot Activity Policy

Repository: `stefm78/learnit-platform`  
Coordinator issue: `#431`  
Parent program: `#380`  
G4 authority: `#425 / PR #426`  
G5 authority: `#427 / PR #428`  
Coordinator work package: `ATLAS-WP-050`

Coordinator branch:

`student-v01/g5-findings-corrective-wave-r1`

Exact common base:

`18b925436777943b19c4b031c24659ad60dee133`

Exact G4 candidate:

`757ed15e840bfca603de0eac3bef1e9d5ff3483d`

G5 replay preparation:

`a72897c209b8ea7bd8672cc8a95be939ecee6fb8`

Canonical engineering findings:

`qualification/STUDENT_V01_G5_HUMAN_FINDINGS_R1.md`

Reserved child work packages:

- `ATLAS-WP-051` — APP EXPERIENCE R1
- `ATLAS-WP-052` — ACTIVITY EXPERIENCE LAB V1
- `ATLAS-WP-053` — PILOT ACTIVITY POLICY R1

Reserved later gate:

- `ATLAS-WP-054` — independent review + selected activity implementation + corrective fan-in + G4 R1

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge or cherry-pick anything.

---

## 0. Core decision

The previous two-track corrective preparation (#429 / PR #430) is superseded and must not be executed.

The G5 findings are now split into three different concerns:

```text
STREAM A — APP EXPERIENCE
application shell / library / navigation / progress / resume

STREAM B — ACTIVITY EXPERIENCE LAB
ActivityPresentation -> sophisticated prototype -> ActivityResponse
fail-fast human selection before production implementation

STREAM C — PILOT ACTIVITY POLICY
which activity families are admitted in the first limited pilot
constructed is excluded from that pilot profile
```

All three streams start from the exact same common base and remain independent.

G5 stays formally:

`PENDING_HUMAN`

This job does not create a new G5 decision.

---

# PHASE 0 — AUTHORITY AND CONTRACT REBIND

## 1. Fresh authority

Before mutation:

1. fresh-read active Human Control Plane HEAD;
2. fresh-read repository `main`;
3. fresh-read:
   - issue #431;
   - `work-packages/ATLAS-WP-050.json`;
   - `qualification/STUDENT_V01_G5_HUMAN_FINDINGS_R1.md`;
   - issue #425 / PR #426 / JOB08 qualification;
   - issue #427 / PR #428 / G5 replay packet;
   - issue #429 / PR #430 only to verify it remains unexecuted/superseded.
4. verify:
   - G4 RESULT_SHA = `757ed15e840bfca603de0eac3bef1e9d5ff3483d`;
   - G4 EVIDENCE_HEAD = `18b925436777943b19c4b031c24659ad60dee133`;
   - G5 replay-prep = `a72897c209b8ea7bd8672cc8a95be939ecee6fb8`;
   - no final G5 human decision/result exists;
   - current coordinator branch descends exactly from the common base.

If authority invalidates the premise:

`HOLD_STUDENT_V01_JOB10_R1_AUTHORITY_DRIFT`

---

## 2. Rebind the ActivityPresentation boundary

Read as normative and do not modify:

- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`

Verify the frozen seam:

```text
projectActivityPresentation(sourceActivity)
renderActivityPresentation(presentation)
readActivityResponse(container, presentation)
```

and the frozen response grammars:

```text
lesson      -> {acknowledged:true}
flashcard   -> {revealed:true}
qcm         -> {choiceId}
fill        -> canonical slot mapping
matching    -> {associations:[{leftItemId,rightItemId}]}
order       -> {orderedItemIds:[...]}
classify    -> {assignments:[{itemId,bucketId}]}
constructed -> {text}
```

The Lab may prototype interaction mechanics, but it must never receive scoring secrets or evaluate correctness.

---

# PHASE 1 — CREATE THREE INDEPENDENT CHILD STREAMS

## 3. Child topology

Create three child issues and three child branches exactly from:

`18b925436777943b19c4b031c24659ad60dee133`

### Stream A

Branch:

`student-v01/g5-r1-app-experience`

Work package:

`ATLAS-WP-051`

Prompt:

`docs/programs/student-v0.1/jobs/JOB_10A_G5_R1_APP_EXPERIENCE.md`

DRAFT PR base:

`student-v01/fanin-b`

### Stream B

Branch:

`student-v01/g5-r1-activity-experience-lab`

Work package:

`ATLAS-WP-052`

Prompt:

`docs/programs/student-v0.1/jobs/JOB_10B_ACTIVITY_EXPERIENCE_LAB_V1.md`

DRAFT PR base:

`student-v01/fanin-b`

### Stream C

Branch:

`student-v01/g5-r1-pilot-activity-policy`

Work package:

`ATLAS-WP-053`

Prompt:

`docs/programs/student-v0.1/jobs/JOB_10C_G5_R1_PILOT_ACTIVITY_POLICY.md`

DRAFT PR base:

`student-v01/fanin-b`

Do not consume sibling results while authoring any stream.

---

# STREAM A — APP EXPERIENCE R1

## 4A. Ownership

Stream A owns only the **application-level experience around activities**.

It does not own the interaction design inside an activity.

Allowed payload paths:

- `apps/learnit-next/src/integration/atlas/surface.js`
- `apps/learnit-next/src/ui/render.js`
- `apps/learnit-next/src/ui/objective_progress.js`
- `apps/learnit-next/src/ui/objective_buckets.js` (new if useful)
- `apps/learnit-next/src/atlas.css`
- `apps/learnit-next/tests/student_v01_g5_r1_app_experience.py`
- `apps/learnit-next/tests/browser_student_v01_g5_r1_app_experience.py`

Allowed control/evidence:
- `ATLAS-WP-051`
- Stream A prompt
- bounded Learn-it Next CI route
- Stream A qualification

Forbidden:
- `apps/learnit-next/src/ui/activity_presenters.js`
- `apps/learnit-next/src/core/**`
- contracts
- showcase
- authoring
- pilot
- QA payload
- source manifest/build inputs.

---

## 5A. Required App Experience repair

### A1 — truthful post-import state

If an installed rich V4 course exists, do not display a contradictory:

`Aucun parcours Atlas installé`

because a legacy planner cannot consume that course.

Do not widen the legacy planner.

Make learner-visible state describe actual installed courses, not internal planner compatibility.

### A2 — activity-first hierarchy

During an active Student V0.1 journey:

- current activity must be visually primary;
- overall progress may remain compact;
- full objective detail must not precede and dominate the activity;
- “Prochaine action recommandée” must not compete with an activity already in progress.

### A3 — compact objective buckets

Provide compact per-objective visual state using current objective progress, with accessible text.

Use learner wording for canonical states:

- not-started -> `À découvrir`
- training -> `En apprentissage`
- review-needed -> `À renforcer`
- ready-for-validation -> `À confirmer`
- validated-recently -> `Acquis récemment`

Visual fill/state must not rely on color alone.

Detailed objective evidence may live behind:

`Voir ma progression`

collapsed by default.

### A4 — resume/recovery clarity

Preserve and clarify:
- current course;
- current activity;
- resume action;
- completion state;
- recovery path.

Do not redesign activity internals.

---

## 6A. Stream A qualification

Create tests that fail on G4 and pass after repair.

Require:
- rich V4 course + no legacy-planner course => no false empty state;
- activity appears before verbose progress detail;
- compact bucket exists for every objective;
- state text is accessible;
- details are progressive disclosure;
- desktop/mobile no overflow;
- keyboard access;
- existing persistence/reload/resume/completion;
- all existing activity families remain functional;
- secret boundary unchanged;
- deterministic double build;
- relevant G4 regressions PASS.

Freeze:
- `APP_RESULT_SHA`
- later evidence-only `APP_EVIDENCE_HEAD`

Allowed PASS:

`PASS_STUDENT_V01_G5_R1_APP_EXPERIENCE_READY_FOR_INTEGRATION`

---

# STREAM B — ACTIVITY EXPERIENCE LAB V1

## 4B. Purpose

This is a development sub-product, not production Learn-it.

Its purpose is to make activity UX cheap to prototype and cheap to reject.

It consumes:

`ActivityPresentation`

and emits:

`ActivityResponse`

Nothing else.

It must not:
- evaluate correctness;
- know hidden solutions;
- know course/session progress;
- persist learner state;
- mutate production presenters;
- load remote plugins;
- introduce a registry/event bus/evaluator framework.

---

## 5B. Lab scope

Create isolated lab under:

`labs/student-v0.1/activity-experience/**`

Also create:

`docs/architecture/student-v0.1/ACTIVITY_EXPERIENCE_LAB_V1.md`

Allowed Stream B control/evidence:
- `ATLAS-WP-052`
- Stream B prompt
- bounded CI route if needed
- `qualification/STUDENT_V01_ACTIVITY_LAB_V1_RESULT.md`
- `qualification/STUDENT_V01_ACTIVITY_LAB_SELECTION.md` only in Phase B after human input.

Forbidden:
- production `apps/learnit-next/src/**`;
- contracts;
- core/runtime;
- showcase;
- authoring;
- QA/pilot payload.

---

## 6B. Lab contract fixtures

Provide learner-safe fixtures only for the **limited-pilot families**:

- lesson
- flashcard
- matching
- order
- classify
- qcm
- fill

Fixtures must match the frozen ActivityPresentation shapes.

Explicitly scan and fail if any fixture contains:
- correctChoiceId
- fill answers
- acceptedResponses
- matches
- correctOrder
- authored classify assignments.

Constructed is intentionally not part of the limited-pilot Lab review.

---

## 7B. Prototype requirements

The Lab must be a standalone local static artifact, deterministic and network-free.

It must show:
- chosen fixture;
- prototype variant;
- rendered activity;
- interaction state;
- exact emitted ActivityResponse in a developer/reviewer inspector;
- no correctness result.

### Lesson

At least one simplified candidate:
- clear reading hierarchy;
- exactly one Continue action.

### Flashcard

At least **two meaningfully different candidates**.

Each must enforce:
- front first;
- explicit reveal;
- back/explanation after reveal;
- exactly one continuation after reveal;
- no “Réponse affichée” or “Prêt à continuer” control-state clutter.

One candidate may use a sophisticated visual flip/card transition if:
- reduced-motion is supported;
- keyboard and screen-reader semantics remain clear;
- animation is enhancement, not required for comprehension.

### Matching

At least **two meaningfully different candidates**:
- one click/select association model;
- one richer spatial/drag-enhanced model.

The richer model must retain complete keyboard/touch-safe fallback.

Both emit the same frozen associations response.

### Order

At least **two candidates**:
- explicit move-up/down model;
- richer drag/reorder enhancement.

Keyboard operation remains first-class.

Both emit the same orderedItemIds response.

### Classify

At least **two candidates**:
- select item -> choose bucket;
- richer spatial/drag-to-bucket enhancement.

Keyboard/touch-safe fallback mandatory.

Both emit the same assignments response.

### QCM / fill

Provide polished baseline reference renderings.

Do not invent a new response grammar.

---

## 8B. Fail-fast human micro-review

Build a downloadable deterministic Activity Lab review bundle.

It must allow a human to review variants without the full Learn-it application.

For each family/variant, ask only fast UX questions:

1. **30 seconds:** without explanation, is the required action obvious?
2. **2 minutes:** is the interaction pleasant and low-friction?
3. **10 minutes or less:** does keyboard/mobile/accessibility use remain coherent?

The review form must collect:
- family;
- variant ID;
- `ACCEPT|REJECT`;
- optional short note.

For families with multiple candidates, at most one variant may be selected for future production integration.

A human may reject all variants, which blocks that family pending a new prototype round.

---

## 9B. Stream B Phase-A stop

After:
- lab source committed;
- deterministic lab artifact PASS;
- browser/mobile/keyboard/accessibility tests PASS;
- review bundle generated and hash-bound;
- Repository governance PASS;

freeze:

`LAB_RESULT_SHA`

Return a downloadable bundle and:

```text
STUDENT_V01_ACTIVITY_LAB_PHASE_A
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
LAB_RESULT_SHA: <sha>
LAB_REVIEW_BUNDLE_SHA256: <sha>
LAB_REVIEW_BUNDLE_BYTES: <int>
LAB_CONTRACT_BOUNDARY: PASS
LAB_SECRET_BOUNDARY: PASS
LAB_RESPONSE_SHAPES: PASS
LAB_BROWSER_ACCESSIBILITY: PASS
HUMAN_PROTOTYPE_DECISION: REQUIRED
FINAL_VERDICT: READY_STUDENT_V01_ACTIVITY_LAB_FOR_HUMAN_PROTOTYPE_REVIEW
```

Then stop Stream B.

Do not implement selected prototypes in production.

---

# STREAM C — PILOT ACTIVITY POLICY R1

## 4C. Policy decision

Do not change learnit.kit.v4.

Create:

`docs/programs/student-v0.1/STUDENT_V0_1_LIMITED_PILOT_ACTIVITY_PROFILE.md`

The first limited pilot profile admits:

- lesson
- flashcard
- matching
- order
- classify
- qcm
- fill

It excludes:

- constructed

Reason:
constructed remains a valid bounded v4 family, but exact text matching is not a sufficient semantic-equivalence mechanism for the first real-student mathematics pilot.

This is a pilot admission decision, not a schema deletion.

---

## 5C. Showcase repair

From the exact G4 showcase:

- remove the single constructed activity at current index 4;
- do not replace it merely to preserve activity count;
- change course estimatedMinutes from 42 to 39;
- preserve both objectives;
- preserve remaining activity order;
- preserve validation independence;
- preserve source facts;
- remove learner-facing internal language:
  - `Student V0.1 Showcase`
  - `kit canonique Atlas M1 0.3`
  - `de la source`
  - other equivalent internal author/provenance wording.

Preferred learner title:

`Nombres complexes — Conjugué et module`

Do not invent new mathematics.

---

## 6C. Stream C scope

Allowed:
- `docs/programs/student-v0.1/STUDENT_V0_1_LIMITED_PILOT_ACTIVITY_PROFILE.md`
- `showcase/student-v0.1/nombres-complexes/**`
- `ATLAS-WP-053`
- Stream C prompt
- bounded CI route
- Stream C qualification.

Forbidden:
- apps;
- contracts;
- authoring source;
- runtime;
- pilot/QA payload;
- global scoring rules.

---

## 7C. Stream C qualification

Require:
- no constructed activity;
- activity count = 10;
- estimatedMinutes = 39;
- all activity types belong to admitted pilot profile;
- both objectives remain sufficiently covered;
- learner-visible internal jargon scan PASS;
- source blob/hash unchanged;
- canonical v4 validation PASS;
- pedagogical quality at least accepted high band;
- revision/digest hygiene PASS;
- source traceability PASS;
- validation independence preserved;
- no acceptedResponses workaround introduced;
- semantic review explicitly:
  `PENDING_INDEPENDENT_CORRECTIVE_REVIEW`.

Freeze:
- `POLICY_RESULT_SHA`
- later evidence-only `POLICY_EVIDENCE_HEAD`

Allowed PASS:

`PASS_STUDENT_V01_G5_R1_PILOT_POLICY_READY_FOR_INDEPENDENT_REVIEW`

---

# PHASE 2 — COORDINATOR PHASE-A AUDIT

## 10. Audit independence

Before asking for human prototype selection:

- Stream A and B and C all start from exact common base;
- no sibling result consumed;
- Stream A does not modify activity_presenters;
- Stream B does not modify production app source;
- Stream C does not modify app/runtime/contracts;
- Stream C does not claim semantic PASS;
- G5 final-decision files remain absent/unchanged;
- old PR #430 remains superseded and unused.

Stream A and C should be author-side PASS before human prototype review unless a causal defect blocks them.

---

## 11. Coordinator Phase-A return

Return:

```text
STUDENT_V01_JOB10_R1_PHASE_A
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
COORDINATOR_ISSUE: 431
COORDINATOR_PR: <pr>
APP_RESULT_SHA: <sha|BLOCKED>
APP_EVIDENCE_HEAD: <sha|BLOCKED>
APP_VERDICT: <token>
LAB_RESULT_SHA: <sha|BLOCKED>
LAB_REVIEW_BUNDLE_SHA256: <sha|BLOCKED>
LAB_REVIEW_BUNDLE_BYTES: <int|BLOCKED>
LAB_VERDICT: READY_STUDENT_V01_ACTIVITY_LAB_FOR_HUMAN_PROTOTYPE_REVIEW|BLOCKED
POLICY_RESULT_SHA: <sha|BLOCKED>
POLICY_EVIDENCE_HEAD: <sha|BLOCKED>
POLICY_VERDICT: <token>
STREAMS_COMMON_BASE: PASS|FAIL
CROSS_CONSUMPTION: NONE|PRESENT
G5_FORMAL_STATUS: PENDING_HUMAN
HUMAN_PROTOTYPE_DECISION: REQUIRED|BLOCKED
NEXT_STEP: HUMAN_ACTIVITY_PROTOTYPE_REVIEW|REPAIR_BLOCKED_STREAM
FINAL_VERDICT: READY_STUDENT_V01_JOB10_R1_FOR_ACTIVITY_PROTOTYPE_REVIEW|HOLD_STUDENT_V01_JOB10_R1_CHILD_NOT_READY|FAIL_STUDENT_V01_JOB10_R1_SCOPE_OR_INDEPENDENCE
```

Also provide the Activity Lab review bundle link.

If Phase A is ready, stop and wait for the human.

---

# PHASE B — HUMAN ACTIVITY PROTOTYPE SELECTION

## 12. Accept explicit human selection only

Resume only from an explicit block:

```text
ACTIVITY_LAB_HUMAN_SELECTION
LAB_REVIEW_BUNDLE_SHA256: <exact Phase-A hash>
REVIEW_COMPLETED: YES
LESSON_VARIANT: <variant-id>|REJECT_ALL
FLASHCARD_VARIANT: <variant-id>|REJECT_ALL
MATCHING_VARIANT: <variant-id>|REJECT_ALL
ORDER_VARIANT: <variant-id>|REJECT_ALL
CLASSIFY_VARIANT: <variant-id>|REJECT_ALL
QCM_BASELINE: ACCEPT|REJECT
FILL_BASELINE: ACCEPT|REJECT
NOTES: NONE|<text>
FINAL_DECISION: ACCEPT_SELECTION|HOLD
```

Do not infer missing selections.

Do not convert casual comments into selection.

Bundle hash mismatch => no Git mutation.

If any required family is REJECT_ALL or baseline rejected, final decision cannot be ACCEPT_SELECTION.

---

## 13. Freeze selection, do not implement it

On valid human selection:

create only:

`qualification/STUDENT_V01_ACTIVITY_LAB_SELECTION.md`

on Stream B branch.

Record:
- exact lab result SHA;
- exact bundle SHA;
- exact selected variant IDs;
- human notes verbatim enough to preserve intent;
- rejected variants;
- statement that selection is UX intent only and production implementation is deferred to ATLAS-WP-054.

Commit selection alone as:

`LAB_SELECTION_SHA`

Do not modify production presenters.

---

# PHASE 3 — FINAL COORDINATOR AUDIT

## 14. Final readiness for ATLAS-WP-054

Require:
- Stream A PASS;
- Stream B valid human selection frozen;
- Stream C author-side PASS with independent semantic review pending;
- common-base separation PASS;
- no cross-consumption;
- no production Activity Lab implementation;
- no formal G5 decision;
- Repository governance PASS on all branches.

Then return:

```text
STUDENT_V01_JOB10_R1_RESULT
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
COORDINATOR_ISSUE: 431
COORDINATOR_PR: <pr>
APP_WP: ATLAS-WP-051
APP_RESULT_SHA: <sha>
APP_EVIDENCE_HEAD: <sha>
APP_VERDICT: PASS_STUDENT_V01_G5_R1_APP_EXPERIENCE_READY_FOR_INTEGRATION
LAB_WP: ATLAS-WP-052
LAB_RESULT_SHA: <sha>
LAB_REVIEW_BUNDLE_SHA256: <sha>
LAB_SELECTION_SHA: <sha>
LAB_SELECTION: PASS
POLICY_WP: ATLAS-WP-053
POLICY_RESULT_SHA: <sha>
POLICY_EVIDENCE_HEAD: <sha>
POLICY_SEMANTIC_REVIEW: PENDING_INDEPENDENT_CORRECTIVE_REVIEW
POLICY_VERDICT: PASS_STUDENT_V01_G5_R1_PILOT_POLICY_READY_FOR_INDEPENDENT_REVIEW
STREAMS_COMMON_BASE: PASS
CROSS_CONSUMPTION: NONE
ACTIVITY_PRODUCTION_IMPLEMENTATION: DEFERRED_TO_ATLAS_WP_054
G5_FORMAL_STATUS: PENDING_HUMAN
NEXT_GATE: ATLAS-WP-054_INDEPENDENT_REVIEW_SELECTED_ACTIVITY_IMPLEMENTATION_FANIN_G4_R1
FINAL_VERDICT: PASS_STUDENT_V01_JOB10_R1_READY_FOR_ATLAS_WP_054
```

A PASS from JOB10 R1 does not authorize:
- production integration inside this job;
- G4 R1 PASS;
- replacement G5 replay;
- G5 GO;
- student sessions.
