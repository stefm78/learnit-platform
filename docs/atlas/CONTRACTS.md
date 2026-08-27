# Atlas M1 shared contracts

```text
contractVersion: 0.3
repository: stefm78/learnit-platform
authorityIssue: 130
workPackage: ATLAS-WP-001
arbitrationId: ATLAS-M1-ARB-001
normativeRegister: ATLAS_M1_ARBITRATION_FROZEN_V1
freezeDigestInputSha256: sha256:fb1ecc98ffa18947104d9596a5eabcbda9fc41c8796e636c2bc8e3a4a541cd75
exactContractBase: 58e39e8917006058fdf177a5daa37535f5e2c78d
```

Version 0.3 is the minimal frozen amendment required before corrective heads. It introduces no backend, network, runtime LLM, randomness, new action, new reason code, correction role, or claimed transfer. All Atlas objects are closed and fail before effects on unknown fields, missing fields, wrong types, unknown enums, unqualified references, identity conflicts, or noncanonical time.

## References and content

```text
CourseRef(packageLineageId, courseLineageId)
ContentRevisionRef(packageLineageId, packageRevisionId, packageDigest)
ObjectiveRef(courseRef, objectiveId)
ActivityRef(courseRef, activityLineageId)
ObjectiveActivityLink(objectiveRef, activityRef, authorIndex >= 0)
```

`ActivityRef` never contains `objectiveId`. `authorIndex` is zero-based within the subsequence of `course.activities` linked to one objective; it is neither identity nor adaptive policy.

```text
ActiveContentRegistry {
  registryVersion: "atlas.content-registry.v1",
  contentRevisionRef, courseRef,
  objectiveByRef, activityByRef,
  objectiveActivityLinks[],
  validationClaims[],
  acceptedValidationClaimSet
}

ValidationIndependenceClaim {
  claimVersion: "atlas.independence.v1",
  claimId, objectiveRef, sourceActivityRef, targetActivityRef,
  basisCode, sourceStimulusDigest, targetStimulusDigest
}

AcceptedValidationClaimSet {
  schemaVersion: "atlas.accepted-validation-claims.v1",
  contentRevisionRef, oracleVersion, artifactDigest,
  acceptedClaimIds: sortedUnique
}
```

CONTENT publishes course-level relational claims; QA alone publishes the accepted set. A claim is valid only when source and target differ, digests differ, both link to the same objective/course/revision, the closed basis is used, the claim ID recalculates, and the exact accepted set matches revision, oracle, and executed artifact. A comment or review status is not an accepted set.

`atlas.stimulus.v1` contains activity type, pre-response prompt, answer operation or blank structure, and visible choices/tokens needed to answer. Strings are NFC, trimmed, and whitespace-collapsed. Choice/token multisets are sorted unless order is itself cognitive. Titles, feedback, explanations, remediation, decorative media, style, random display order, and technical IDs are excluded. A changed digest is necessary but not sufficient; QA rejects cosmetic variants, same operations, same values, and same distractors.

## Activity classification and time

| learningPhase | assessmentRole | executionClass | M1 use |
|---|---|---|---|
| activation/comprehension/application | practice | practice | practice actions |
| consolidation | practice | correction | `correct-practice` only |
| validation | validation | validation | validation actions |
| transfer | practice | transfer | classified, never planned |
| diagnostic | diagnostic | diagnostic | outside M1 planner |

Every other pair is rejected. Correction is never inferred from title, position, UUID order, DOM, generic metadata, or action alone.

`activityCommon.estimatedMinutes` is an author-supplied integer `1..30`. It stays optional for historical non-Atlas kits but is mandatory at the Atlas gate.

## Closed enums

```text
LearningAction =
  start-practice | continue-practice | correct-practice |
  attempt-validation | maintain-recent-validation | attempt-transfer

ExecutionClass = practice | correction | validation | transfer | diagnostic
Outcome = correct | incorrect
ObjectiveEvidenceState =
  not-started | training | review-needed |
  ready-for-validation | validated-recently
AssistanceState = none | used | unknown
AssistanceKind =
  hint | guided-step | revealing-feedback | solution | previous-answer
IndependenceBasisCode =
  new-instance | new-context | alternate-representation
RewardKind =
  correction-completed | independent-success | validation-completed |
  validation-reconfirmed | resumed-after-interruption
RewardLabelCode =
  reward.correction_completed | reward.independent_success |
  reward.validation_completed | reward.validation_reconfirmed |
  reward.resumed_after_interruption
SessionLifecycleKind =
  session-started | session-interrupted | session-resumed | session-completed
PedagogicalEventKind = activity-attempt | activity-corrected
ReasonCode =
  NEW_OBJECTIVE | PRACTICE_IN_PROGRESS | RECENT_ERROR |
  REVIEW_REQUIRED | CORRECTION_COMPLETED |
  NO_INDEPENDENT_VALIDATION | VALIDATION_AVAILABLE |
  RECENTLY_VALIDATED | TRANSFER_AVAILABLE | SESSION_TIME_LIMIT
```

`transfer-completed` and all free-form alternatives are forbidden.

### M2.2 transfer evidence

Transfer remains a distinct observed evidence category, not a mastery state.

```text
TransferEvidence {
  transferEvidenceVersion: "atlas.transfer-evidence.v1",
  objectiveRef,
  attempts >= 0,
  independentSuccesses >= 0,
  lastAttemptAt: canonicalTimestamp|null,
  lastIndependentSuccessAt: canonicalTimestamp|null
}
```

`attempt-transfer` maps only to existing `ExecutionClass=transfer` and only authored
`learningPhase=transfer / assessmentRole=practice` activities are eligible.

Transfer is planifiable only after at least one successful admissible
`maintain-recent-validation` in the current validation cycle. Each successful
maintenance reconfirmation unlocks at most one later transfer attempt. A later
successful maintenance reconfirmation may unlock one new attempt.

Priority is fail-closed and deterministic: unresolved review/correction first,
then due maintenance, then an unlocked transfer challenge. Transfer never resets
or extends the 1/3/7/21 memory schedule. Correct + unassisted transfer increments
independent transfer success; incorrect or assisted transfer remains observed
without independent success and without erasing prior validation.

`ObjectiveEvidence v1` remains unchanged. Transfer evidence is a pure projection
from accepted activity-attempt events plus scored executions.

## Recommendation, plans, maintenance, fairness

```text
LearningRecommendation {
  recommendationVersion: "atlas.recommendation.v1",
  objectiveRef, action,
  eligibleActivityRefs: unique,
  preferredActivityRef,
  estimatedMinutes: 1..30,
  reasonCodes: unique
}
```

LEARNING publishes one preferred activity before duration. Recommendation and plan use that exact activity without substitution.

```text
action -> class
start-practice -> practice
continue-practice -> practice
correct-practice -> correction
attempt-validation -> validation
maintain-recent-validation -> validation in maintenance mode
```

```text
SessionPlanItem {
  position, objectiveRef, activityRef, action, executionClass,
  estimatedMinutes,
  correctsEventId?, validationBasisEventId?, independenceClaimId?
}
SessionPlanCanonicalPayload {
  schemaVersion: "atlas.session-plan.v1",
  engineVersion, courseRef, contentRevisionRef,
  durationMinutes: 5|15|30, items[],
  totalEstimatedMinutes, unusedMinutes
}
SessionPlan { planId, planDigest, payload }
```

Positions are contiguous from zero. `totalEstimatedMinutes + unusedMinutes = durationMinutes`. An activity that does not fit yields `SESSION_TIME_LIMIT`; no cost invention, truncation, course-duration division, or shorter substitute is allowed. Correction requires `correctsEventId`; validation/maintenance require basis event and claim.

Maintenance requires an admissible prior correct validation, at least 24 hours between canonical timestamps, distinct target and stimulus digest, exact accepted relational claim, scored submission, and assistance `none`. Success reconfirms; failure yields `review-needed` without deleting history.

At equal pedagogical priority, fairness sorts by unresolved error first, oldest or absent `lastSelectedAt`, lowest count in the last ten accepted `session-started` events, then canonical objective reference. An objective counts once per session; interrupted sessions count after durable start. Randomness, hidden cursors, ambient time, timezones, and UUID lexical policy are forbidden.

## Canonical JSON and identities

`atlasCanonicalJsonV1` validates the closed type, uses UTF-8 without BOM, NFC strings, Unicode-code-point key order, no insignificant whitespace, semantic array order, sorted/deduplicated `sortedUnique` collections, base-10 integers, and removes the computed identity field. It rejects non-integers in identity payloads, `NaN`, infinities, `-0`, duplicate keys, undefined values, functions, cycles, and unauthorized nulls.

```text
atlasHashV1(domain, value) =
SHA-256(UTF8(domain) || 0x00 || UTF8(atlasCanonicalJsonV1(value)))
```

Domains:

```text
learnit.atlas.m1.v0.3/plan-digest
learnit.atlas.m1.v0.3/start-request-id
learnit.atlas.m1.v0.3/session-id
learnit.atlas.m1.v0.3/event-id
learnit.atlas.m1.v0.3/execution-id
learnit.atlas.m1.v0.3/assistance-use-id
learnit.atlas.m1.v0.3/validation-claim-id
learnit.atlas.m1.v0.3/reward-id
learnit.atlas.m1.v0.3/response-digest
learnit.atlas.m1.v0.3/scoring-rule-digest
learnit.atlas.m1.v0.3/stimulus-digest/atlas.stimulus.v1
```

`Sha256Digest` is `sha256:` plus 64 lower hex. Typed IDs use `atlas-plan-sha256:`, `atlas-start-sha256:`, `atlas-session-sha256:`, `atlas-event-sha256:`, `atlas-execution-sha256:`, `atlas-assistance-sha256:`, `atlas-reward-sha256:`, or `atlas-claim-sha256:`.

`planDigest` hashes the canonical payload and `planId` represents the same 32 bytes. Divergence fails.

```text
StartRequestRecord {
  schemaVersion: "atlas.start-request.v1",
  startRequestId, planDigest, startOrdinal >= 1, preparedAt
}
SessionRef { sessionId, planId }
```

CORE persists a strictly increasing start ordinal and request before session effects. `startRequestId` hashes `{planDigest,startOrdinal}`. `sessionId` hashes `{startRequestId,planDigest}`. Retrying the same pair returns the same session without duplicate start; a new deliberate start needs a new record. Same identity/same canonical payload is idempotent; same identity/different payload fails with `IDENTITY_PAYLOAD_CONFLICT`, `START_REQUEST_PLAN_CONFLICT`, or `SESSION_PLAN_CONFLICT`.

## Sessions, assistance, scoring, events

```text
SessionStartedEvent {
  eventVersion: "atlas.learning-event.v1", eventId, eventOrdinal: 0,
  kind: "session-started", sessionRef, courseRef, contentRevisionRef,
  planDigest, selectedItems[], occurredAt
}
SessionLifecycleEvent {
  eventVersion: "atlas.learning-event.v1", eventId, eventOrdinal >= 1,
  kind: session-interrupted|session-resumed|session-completed,
  sessionRef, occurredAt
}
ResumeItemState {
  itemPosition, submissionOrdinal, assistance, assistanceUseIds[]
}
ResumeState {
  resumeVersion: "atlas.resume-state.v1",
  sessionRef, courseRef, contentRevisionRef, planDigest,
  nextItemPosition, lastCommittedEventId?, responseDraft?,
  focusTarget, lifecycleOrdinal, itemStates[]
}
AssistanceUseRecord {
  assistanceVersion: "atlas.assistance-use.v1",
  assistanceUseId, sessionRef, itemPosition, assistanceKind, recordedAt
}
```

`session-started` is the sole durable selection fact. Lifecycle events never alter evidence.

Assistance protocol is EXPERIENCE request -> CORE validation/persistence -> CORE confirmation -> display. Failed persistence means no display. `used` is irreversible across navigation and resume. `none` exists only after explicit initialization; absent/corrupt/unproven state is `unknown`. Both `used` and `unknown` prohibit autonomous success, initial validation, and reconfirmation.

EXPERIENCE submits only `sessionId`, `itemPosition`, and `rawResponse`.

```text
ScoredExecutionRecord {
  executionVersion: "atlas.scored-execution.v1",
  executionId, sessionRef, courseRef, contentRevisionRef, planDigest,
  itemPosition, submissionOrdinal >= 1,
  objectiveRef, activityRef, action, executionClass,
  responseDigest, scoringRuleId, scoringRuleDigest,
  outcome, assistance, assistanceUseIds[],
  submittedAt, scoredAt
}
PedagogicalLearningEvent {
  eventVersion: "atlas.learning-event.v1",
  eventId, kind: activity-attempt|activity-corrected,
  objectiveRef, executionId, correctsEventId?, occurredAt
}
```

CORE resolves the exact started item and active revision, verifies the deterministic scorer, reads persisted assistance, scores, and atomically writes execution, event, and checkpoint. Caller-supplied outcome, identity, class, assistance, event kind, score, or accepted claim is rejected.

`activity-corrected` requires `correctsEventId` to an existing incorrect practice attempt of the same course/objective and frozen target. Multiple corrections may target one error and are all counted; correction never grants validation.

Pedagogical event identity hashes `{eventVersion,kind,executionId,correctsEventId?}`. Started-session identity hashes `{eventVersion,kind,sessionRef,planDigest,eventOrdinal:0}`. Lifecycle identity includes session, ordinal, and time.

## Evidence and rewards

```text
ObjectiveEvidence {
  evidenceVersion: "atlas.objective-evidence.v1",
  objectiveRef, practiceAttempts, correctionsCompleted,
  validationAttempts, latestPracticeCorrect, latestValidationCorrect,
  lastValidationAt, lastEvidenceAt, state
}
```

Evidence is recalculated only from accepted pedagogical events plus scored executions. Lifecycle changes nothing, including `lastEvidenceAt`. Correction increments only correction count. Multiple corrections may exceed practice attempts. Only admissible correct validation sets `validated-recently`; invalid/assisted/unknown validation is retained without credit. Incorrect validation or maintenance yields current `review-needed` while preserving history. Evidence is not certification, mastery percentage, or durable-retention proof.

```text
PedagogicalRewardSignal {
  ruleVersion, rewardId, kind, labelCode,
  objectiveRef|null, evidenceEventIds: sortedUnique, occurredAt
}
```

Rewards are a pure LEARNING projection over accepted CORE facts, never UI declarations or primary stored truth. Exclusive priority is reconfirmed validation, initial validation, correction, independent practice success, resumed-after-interruption. One event finances at most one reward. Missing, foreign, duplicated, reused, or inadmissible evidence fails. Reward time is the maximum evidence time.

## Time, storage, atomicity

Canonical timestamp regex is:

```text
^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$
```

Calendar validity and byte round-trip are required. Journal order is `occurredAt,eventId`; executions use `scoredAt,executionId`; fairness sessions use started time then event ID.

```text
atlasStateVersion: 0.3
namespace: learnit.atlas.m1.v2
database: learnit_atlas_m1_v2
stores: learningEvents, scoredExecutions, resumeStates, atlasMeta
```

The old `learnit.atlas.m1.v1` namespace is not read, migrated, modified, deleted, or cleared. Any state 0.2 import/checkpoint/resume is rejected before write with `UNSUPPORTED_ATLAS_STATE_VERSION`.

Submission atomically commits `scoredExecutions + learningEvents + resumeStates`. Fault injection may produce all three writes or zero, never partial state. Import validates all members and relations before one transaction.

## Schema compatibility, ownership, gates

The v2 schema adds only optional activity `estimatedMinutes: 1..30` and optional course-level closed `atlasValidationIndependenceClaims[]`. Old non-Atlas kits stay valid. Atlas gates require duration and applicable claims. No correction role or activity type is added.

CONTENT owns duration/order/candidate claims/digests. LEARNING owns recommendation/planning/fairness/maintenance eligibility/reward policy. CORE owns identities/scoring/assistance/events/evidence/storage. EXPERIENCE only presents confirmed facts. QA owns the independent oracle and accepted claim set. INT mechanically composes accepted heads and creates no semantics.

No INT is allowed before four new `ACCEPTED_HEAD` verdicts, written SHA freeze, accepted QA head, accepted contracts, and operational support. Product evidence must bind the exact artifact and clean checkout, block network, use real browsers at `1440x900` and `390x844`, and cover keyboard, focus, overflow, submission, interruption, close/reopen, resume, assistance, and IndexedDB fault injection. Human Windows and Android gates apply to that exact artifact.
