# Student V0.1 — JOB09 G5 Human Replay Protocol

Status: `HUMAN_DECISION_REQUIRED`  
Protocol version: `1.0`  
Authority issue: `#427`  
PR: `#428`

## Exact replay binding

- JOB09 base / G4 evidence head: `18b925436777943b19c4b031c24659ad60dee133`
- G4 candidate: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`
- app: `478657` bytes / SHA-256 `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`
- repaired showcase SHA-256: `da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`
- nested learner package: `496658` bytes / SHA-256 `a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10`
- outer replay bundle: `508231` bytes / SHA-256 `fc06e745405cb1ba48674bcf93478e9ccbc44d766bee4bd4174a3aab3b00ce66`
- accepted learner start mode: `DIRECT_FILE`

The outer ZIP is a reviewer transport wrapper only. The nested learner package is byte-exact and unchanged. No G5 PASS/HOLD has been recorded. Student sessions authorized at this point: `0`.

## Human execution

### Stage 0 — identity
Verify the outer ZIP against the replay packet, extract it, run `reviewer-only/verify_replay.py` (or independently verify the nested package), and confirm the nested package identity above. Any mismatch invalidates the review.

### Stage 1 — cold start, no answer guide
Do **not** open `reviewer-only/ANSWER_GUIDE.md`. From the nested package's own START_HERE, reach the app, import the packaged course, start it, and complete at least the lesson, flashcard and first scored interaction. Judge cold-start comprehension, information density, next-action confidence, interaction quality and scored/non-scored comprehensibility. Opening the answer guide early requires a clean restart of Stage 1.

### Stage 2 — full 11-activity journey
The answer guide may now be opened. Complete the full intended 30–45 minute journey. Intentionally answer one scored practice activity incorrectly, judge feedback trust/usefulness, later complete it correctly, reload/reopen after non-scored and scored progress, resume, complete all 11 activities, reopen, and inspect completion state. Judge pedagogical flow, coherence, fatigue/density, feedback/scoring trust and current/next-state confidence.

### Stage 3 — recovery
Cancel the file chooser and retry; select `reviewer-only/invalid-not-v4.json`; recover and import the real course; return to library and continue; perform the documented local reset/re-import path. Judge clarity and confidence preservation.

### Stage 4 — real accessibility
Use desktop keyboard-only navigation through start/import and at least one scored activity; judge focus visibility/order, naming and traps. With one real screen reader (NVDA, VoiceOver or TalkBack), inspect start/import, one activity, feedback/result and completion.

### Stage 5 — mobile touch
On a real touch/mobile environment, preferably around 390 px width, exercise start/import, one non-scored activity, one scored interaction, feedback and resume. Judge touch targets, scrolling, gesture friction, text density and horizontal overflow.

## Mandatory decision dimensions

Each must be explicitly `PASS` or `HOLD`:
- `COLD_START_COMPREHENSION`
- `INFORMATION_DENSITY`
- `PEDAGOGICAL_FLOW`
- `INTERACTION_GESTURE_QUALITY`
- `KEYBOARD_ACCESSIBILITY`
- `SCREEN_READER_ACCESSIBILITY`
- `FEEDBACK_SCORING_TRUST`
- `RECOVERY_RESUME_CLARITY`
- `MOBILE_TOUCH_USABILITY`
- `FULL_30_45_MIN_JOURNEY`
- `OVERALL_LIMITED_PILOT_CONFIDENCE`

Findings use `BLOCKER`, `MAJOR`, or `MINOR`. `GO_LIMITED_PILOT` is valid only if every mandatory dimension is PASS, no BLOCKER/MAJOR remains unresolved, and every MINOR is explicitly accepted as non-blocking with any required guardrail.

A valid GO authorizes only the first 5–6 real student sessions on this exact candidate/package. It does not authorize merge, release promotion, broader rollout, production readiness, or silent repair.

## Mandatory stop

Phase A stops here with `HUMAN_DECISION_REQUIRED`. The human decision form remains unfilled.
