# Student V0.1 — G5 Delta Human Replay Protocol R1

## Identity binding

- CANONICAL_G5_AUTHORITY: `#427`
- WORK_PACKAGE: `ATLAS-WP-069`
- REVIEWED_PRODUCT_SHA: `8eceb94b8003adc539d34d2cfeeca62ff0c565a0`
- SOURCE_EVIDENCE_HEAD: `0a0251df5f085c203fd43456bad63af33bb1a9a7`
- JOB26_BUILD_SHA256: `96531b5eba19056268b2c451a0518e36c129464085ba5fcc73a318e6569b7128`
- JOB26_BUILD_BYTES: `583482`
- V5_SHOWCASE_SHA256: `aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b`
- REPLAY_TRANSPORT: `REUSE_JOB26_IMMUTABLE_HTTPS_REPLAY`
- REPLAY_URL: `https://stefm78.github.io/learnit-platform/human-replay/8eceb94b8003adc539d34d2cfeeca62ff0c565a0/`
- REPLAY_HTTPS_LIVE_SMOKE: `PASS`

Do not redeploy. Do not alter the candidate. Do not redo the already accepted JOB26 multi-term search/menu correction replay as a required gate.

## What is already closed

- `JOB26_FORMAL_HUMAN_VALIDATION: ACCEPTED`
- `JOB26_HUMAN_GATE: PASS`
- `NAVIGATION_SEARCH_CLARITY: SATISFIED_BY_JOB26_FORMAL_VALIDATION`
- HR24 search/menu/rename bounded replay points remain frozen.

## Delta-only execution

Use one integrated pass on the exact immutable JOB26 replay. The steps below intentionally combine dimensions instead of creating separate replays.

### 1. Clean cold start + first learning action

Start from a clean local state. Without opening the answer guide first, reach/import/open the exact V5 course and start learning. Do **not** spend time re-judging multi-term search or the hamburger correction.

Record:
- `COLD_START_COMPREHENSION: PASS|HOLD`
- `INFORMATION_DENSITY: PASS|HOLD`

### 2. Current objective progress + representative interactions

Inspect the current R15 objective reservoirs/selected-objective behavior in the actual learner flow. Use representative current interactions, including the matching tap-destination path that changed after the earlier Activity Lab selection.

Record:
- `OBJECTIVE_PROGRESS_CLARITY: PASS|HOLD`
- `INTERACTION_GESTURE_QUALITY: PASS|HOLD`

### 3. Full exact learner journey and feedback trust

Complete the exact current 10-activity / 39-minute journey. Intentionally make at least one scored answer incorrect, inspect the resulting feedback, then continue correctly. Observe activity-to-feedback-to-next-action flow and the final session recap as separate states.

Record:
- `PEDAGOGICAL_FLOW: PASS|HOLD`
- `FEEDBACK_SCORING_TRUST: PASS|HOLD`
- `FULL_LEARNER_JOURNEY: PASS|HOLD`

### 4. Recovery + resume delta

The one-step reload/resume smoke from JOB26 is already accepted; do not repeat it merely for ceremony. Exercise only the missing recovery cases on the exact current candidate: cancel an import/file selection and recover; try an invalid/non-course JSON if available without modifying the replay; use the current local reset/re-import path; after a persisted learning step, confirm that returning to the course remains understandable.

Record:
- `RECOVERY_RESUME_CLARITY: PASS|HOLD`

If an invalid test file is not available inside the immutable replay, the reviewer may use any tiny local invalid JSON solely as external reviewer input; it must not be committed or treated as candidate content.

### 5. Real keyboard-only accessibility

Using only the keyboard, traverse start/import and at least one current scored activity. Judge visible focus, order, control naming, operability and absence of traps. This is a real human interaction; automated browser evidence is not a substitute.

Record:
- `KEYBOARD_ACCESSIBILITY: PASS|HOLD`

### 6. Real screen-reader accessibility

With one real screen reader (NVDA, VoiceOver or TalkBack), inspect start/import, one current activity, its feedback/result state, and completion/summary state. Judge whether the experience is understandable enough for a bounded pilot.

Record:
- `SCREEN_READER_ACCESSIBILITY: PASS|HOLD`

### 7. Real mobile/touch delta

On a real touch/mobile environment, exercise at minimum one non-scored activity, one scored interaction, feedback and resume. Search/menu appearance itself is already accepted; focus this step on activity use, touch targets, scrolling, gesture friction, density and horizontal overflow through the learner path.

Record:
- `MOBILE_TOUCH_USABILITY: PASS|HOLD`

### 8. Final exact-candidate pilot confidence + HR24-003

After the above observations, explicitly consider the known unresolved limitation:

`HR24_003_ENGINE_GAP: CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED`

No scheduler/date/new validation CTA exists for that gap and JOB27 does not repair it.

Record:
- `HR24_003_PILOT_ACCEPTANCE: ACCEPT|HOLD`
- `OVERALL_LIMITED_PILOT_CONFIDENCE: PASS|HOLD`
- `BLOCKER_FINDINGS: NONE|<text>`
- `MAJOR_FINDINGS: NONE|<text>`
- `MINOR_FINDINGS: NONE|<text>`
- `PILOT_GUARDRAILS: NONE|<text>`
- `FINAL_DECISION: GO_LIMITED_PILOT|HOLD`

A future `GO_LIMITED_PILOT` is valid only if all twelve delta dimensions are PASS, no unresolved BLOCKER/MAJOR remains, any MINOR is explicitly accepted with guardrails as needed, HR24-003 is explicitly accepted for the bounded pilot, and the human explicitly chooses `GO_LIMITED_PILOT` for this exact product identity.

## Required response block

```text
G5_DELTA_HUMAN_REVIEW_R1
REVIEWED_PRODUCT_SHA: 8eceb94b8003adc539d34d2cfeeca62ff0c565a0
REPLAY_URL: https://stefm78.github.io/learnit-platform/human-replay/8eceb94b8003adc539d34d2cfeeca62ff0c565a0/
DELTA_REPLAY_COMPLETED: YES
COLD_START_COMPREHENSION: PASS|HOLD
INFORMATION_DENSITY: PASS|HOLD
PEDAGOGICAL_FLOW: PASS|HOLD
OBJECTIVE_PROGRESS_CLARITY: PASS|HOLD
INTERACTION_GESTURE_QUALITY: PASS|HOLD
KEYBOARD_ACCESSIBILITY: PASS|HOLD
SCREEN_READER_ACCESSIBILITY: PASS|HOLD
FEEDBACK_SCORING_TRUST: PASS|HOLD
RECOVERY_RESUME_CLARITY: PASS|HOLD
MOBILE_TOUCH_USABILITY: PASS|HOLD
FULL_LEARNER_JOURNEY: PASS|HOLD
HR24_003_PILOT_ACCEPTANCE: ACCEPT|HOLD
OVERALL_LIMITED_PILOT_CONFIDENCE: PASS|HOLD
BLOCKER_FINDINGS: NONE|<text>
MAJOR_FINDINGS: NONE|<text>
MINOR_FINDINGS: NONE|<text>
PILOT_GUARDRAILS: NONE|<text>
FINAL_DECISION: GO_LIMITED_PILOT|HOLD
```

This protocol does not itself authorize any student session. Until a valid final human decision is durably recorded, `AUTHORIZED_STUDENT_SESSIONS: 0`.
