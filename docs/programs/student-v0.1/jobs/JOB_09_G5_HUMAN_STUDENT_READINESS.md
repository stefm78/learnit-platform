# /AUDIT /SOLVE /BUILD — JOB 09 / G5
## Student V0.1 — human replay and student-readiness gate

Repository: `stefm78/learnit-platform`  
Authority issue: `#427`  
Program issue: `#380`  
G4 authority: `#425 / PR #426`  
Work package: `ATLAS-WP-045`

Branch:

`student-v01/g5-human-readiness`

Exact anchors:

- `JOB09_BASE = 18b925436777943b19c4b031c24659ad60dee133`
- `G4_CANDIDATE_SHA = 757ed15e840bfca603de0eac3bef1e9d5ff3483d`
- `G4_EVIDENCE_HEAD = 18b925436777943b19c4b031c24659ad60dee133`
- repaired app bytes: `478657`
- repaired app SHA-256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`
- repaired showcase SHA-256: `da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`
- exact learner package bytes: `496658`
- exact learner package SHA-256: `a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10`
- accepted package start mode: `DIRECT_FILE`

Apply:

`/refresh -> /audit -> /solve -> /build -> /audit`

This job has a mandatory **human stop**.  
Do not merge anything.

---

## 0. Role and gate semantics

You are the G5 gate facilitator and evidence recorder.

You are **not** the human reviewer.

The program charter requires:

`G5 human replay/student-readiness PASS`

before the first 5–6 real student sessions.

Automation already established G4. G5 exists specifically for qualities that machine tests do not replace:

- perceived interaction and gesture quality;
- information density and comprehensibility;
- accessibility with real interaction;
- pedagogical interpretation;
- confidence and trust;
- ambiguous recovery/conflict states.

Therefore this job has two phases:

### Phase A — machine preparation

Revalidate the exact G4 candidate, build an immutable human-replay bundle, persist its protocol/identity evidence, and stop at:

`HUMAN_DECISION_REQUIRED`

### Phase B — human gate

Resume only after a real human has used the exact bundle and explicitly returns a decision.

The model must never synthesize, infer, approximate, or self-award human PASS.

---

# PHASE A — MACHINE PREPARATION

## 1. Fresh authority rebind

Before mutation:

1. fresh-read active Human Control Plane HEAD;
2. bind exact UCP/UAO/governance authority;
3. fresh-read repository `main`;
4. fresh-read issue #427 and `ATLAS-WP-045`;
5. fresh-read G4 issue #425 / PR #426;
6. verify PR #426 remains DRAFT/unmerged with:
   - exact functional candidate `757ed15e840bfca603de0eac3bef1e9d5ff3483d`;
   - exact evidence head `18b925436777943b19c4b031c24659ad60dee133`;
7. verify this JOB09 branch descends exactly from `JOB09_BASE`;
8. revalidate the JOB08 qualification and exact-head CI identities.

If any G4 authority moved incompatibly, stop:

`HOLD_STUDENT_V01_JOB09_G4_DRIFT`

Do not silently select a newer candidate.

---

## 2. Candidate immutability

JOB09 is review-only.

No mutation is allowed under:

- `.github/**`
- `apps/**`
- `authoring/**`
- `contracts/**`
- `showcase/**`
- `pilot/**`
- `qa/**`
- `governance/**`
- `tools/**`

The learner candidate under review remains exactly:

`G4_CANDIDATE_SHA = 757ed15e840bfca603de0eac3bef1e9d5ff3483d`

JOB09 does not create a new product candidate.

---

## 3. Rebuild the exact replay inputs

From the exact G4 candidate:

1. build Learn-it Next twice;
2. require both builds byte-identical;
3. require exact app identity:

```text
bytes   478657
sha256  85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e
```

Verify the exact repaired showcase:

`sha256:da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`

Use the exact integrated JOB07 R2 builder unchanged to produce the learner package twice.

Require:

```text
bytes   496658
sha256  a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10
```

Inspect and require:

- exact app/kit manifest binding;
- deterministic archive metadata;
- exact extracted app/kit bytes;
- local-only START_HERE;
- no remote dependency;
- accepted `DIRECT_FILE` contract.

If any identity differs, stop:

`HOLD_STUDENT_V01_JOB09_REPLAY_IDENTITY_DRIFT`

---

## 4. Build a transient human-replay bundle

Create one downloadable outer ZIP outside Git.

Suggested structure:

```text
student-v01-g5-human-replay/
  README_FIRST.md
  identity.json
  learner/
    student-v01-pilot.zip
  reviewer-only/
    HUMAN_REPLAY_PROTOCOL.md
    ANSWER_GUIDE.md
    invalid-not-v4.json
    G5_DECISION_FORM.md
    verify_replay.py
```

### Learner package

`learner/student-v01-pilot.zip` must be the exact 496658-byte package above.

Do not modify or repack its contents.

### identity.json

Bind at minimum:

- schema `learnit.student-v0.1.g5-human-replay.v1`;
- G4 candidate SHA;
- G4 evidence head;
- app bytes/SHA-256;
- repaired showcase SHA-256;
- nested learner-package bytes/SHA-256;
- `humanGateRequired: true`;
- `g5Pass: false`;
- `authorizedStudentSessions: 0`;
- protocol version.

Do not put an outer-bundle self-hash inside the outer bundle itself.

### reviewer-only answer guide

Generate deterministically from the exact repaired showcase.

It exists only to let the reviewer finish the controlled replay after the cold-start portion.

It must remain outside the nested learner package.

### invalid-not-v4.json

Create a tiny deterministic invalid/non-V4 JSON file solely for the human recovery test.

It is reviewer tooling, not candidate content.

### verify_replay.py

Provide a standard-library-only verifier that checks the nested learner package against the exact expected bytes/SHA-256 and checks identity.json.

### Outer bundle

Produce the outer ZIP deterministically.

Record:

- byte count;
- SHA-256;
- entry list/order;
- per-entry SHA-256.

The outer bundle is a reviewer transport wrapper, not the learner candidate.

---

## 5. Durable Phase-A replay packet

Create:

`qualification/STUDENT_V01_JOB09_G5_PROTOCOL.md`

and:

`qualification/STUDENT_V01_JOB09_G5_REPLAY_PACKET.json`

The replay packet must bind:

- G4 candidate/evidence SHAs;
- exact app/showcase/nested-package identities;
- exact outer replay-bundle bytes/SHA-256;
- protocol version;
- replay entry hashes;
- mandatory human dimensions;
- explicit statement `humanDecision = PENDING`;
- explicit statement `g5 = PENDING_HUMAN`;
- authorization `studentSessions = 0`.

Commit these two files together after the WP/prompt preparation.

Record that commit as:

`REPLAY_PREP_SHA`

Repository governance and exact JOB09 scope must PASS.

---

## 6. Human replay protocol

The human protocol must be concise enough to execute, but must cover every required human-only dimension.

### Stage 0 — identity

The human reviewer must:

1. download the exact outer replay bundle;
2. run or otherwise verify its SHA-256 against the replay packet;
3. extract it;
4. run `reviewer-only/verify_replay.py` or independently verify the nested package SHA;
5. confirm the nested package is exactly:

`a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10`

No human verdict from an identity-mismatched bundle is valid.

### Stage 1 — cold start, no answer guide

The reviewer must **not open `ANSWER_GUIDE.md` yet**.

Using only the nested learner package and its own START_HERE:

1. extract the learner package;
2. start from START_HERE;
3. reach the app;
4. import the packaged course;
5. start the course;
6. complete at least:
   - lesson;
   - flashcard;
   - first scored interaction.

Record human judgments on:

- cold-start comprehensibility;
- information density;
- confidence about what to do next;
- visual/interaction quality;
- whether scoring/non-scoring behavior feels understandable.

If the reviewer accidentally opens the answer guide before completing Stage 1, restart Stage 1 from clean state before claiming cold-start PASS.

### Stage 2 — full learner journey

Now the reviewer may open the reviewer-only answer guide.

Complete the full 11-activity course / intended 30–45 minute journey.

During the run:

- intentionally answer one scored practice activity incorrectly;
- judge whether feedback is understandable, trustworthy and useful;
- later complete it correctly;
- reload/reopen after non-scored progress;
- reload/reopen after scored progress;
- resume;
- reach full completion;
- reopen and confirm completion state is understandable.

Judge:

- pedagogical flow;
- progression/coherence;
- feedback/scoring trust;
- fatigue/information density;
- confidence that a learner understands current state and next action.

### Stage 3 — recovery

Human-test:

1. cancel the file chooser and retry;
2. select `reviewer-only/invalid-not-v4.json`;
3. recover and import the exact real course again;
4. return to library and continue;
5. perform the documented local reset/re-import path.

Judge whether errors and recovery are comprehensible and confidence-preserving.

### Stage 4 — real accessibility interaction

A G5 PASS requires real human accessibility interaction, not DOM assertions alone.

On desktop:

- use keyboard-only navigation through start/import and at least one scored activity;
- judge focus visibility, focus order, control naming and absence of keyboard traps.

With one real screen reader:

- NVDA, VoiceOver, or TalkBack;
- inspect at minimum:
  - start/import;
  - one activity;
  - feedback/result state;
  - completion state.

Record whether the experience is understandable enough for this limited pilot.

### Stage 5 — mobile touch

On a real touch/mobile environment, preferably around the already-qualified 390px width:

- open/use the exact candidate/package;
- exercise start/import, one non-scored activity, one scored interaction, feedback and resume;
- judge touch target quality, scrolling, gesture friction, text density and horizontal overflow.

Browser/device details may be recorded briefly but do not collect unnecessary personal information.

---

## 7. Mandatory human dimensions

The human must explicitly mark each:

- `COLD_START_COMPREHENSION: PASS|HOLD`
- `INFORMATION_DENSITY: PASS|HOLD`
- `PEDAGOGICAL_FLOW: PASS|HOLD`
- `INTERACTION_GESTURE_QUALITY: PASS|HOLD`
- `KEYBOARD_ACCESSIBILITY: PASS|HOLD`
- `SCREEN_READER_ACCESSIBILITY: PASS|HOLD`
- `FEEDBACK_SCORING_TRUST: PASS|HOLD`
- `RECOVERY_RESUME_CLARITY: PASS|HOLD`
- `MOBILE_TOUCH_USABILITY: PASS|HOLD`
- `FULL_30_45_MIN_JOURNEY: PASS|HOLD`
- `OVERALL_LIMITED_PILOT_CONFIDENCE: PASS|HOLD`

Findings use:

- `BLOCKER`
- `MAJOR`
- `MINOR`

G5 GO requires:

- every mandatory dimension PASS;
- no unresolved BLOCKER;
- no unresolved MAJOR;
- any MINOR explicitly accepted by the human as non-blocking for only the first 5–6 student sessions, with any necessary pilot guardrail.

---

## 8. Mandatory Phase-A stop

After producing the bundle and durable replay packet, stop.

Do **not** fill the human decision form.

Do **not** commit a human decision.

Do **not** claim G5 PASS.

Return exactly this Phase-A block:

```text
STUDENT_V01_JOB09_G5_PHASE_A
JOB09_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
REPLAY_PREP_SHA: <commit>
ISSUE: 427
PR: <job09 pr>
APP_IDENTITY: PASS
SHOWCASE_IDENTITY: PASS
LEARNER_PACKAGE_IDENTITY: PASS
REPLAY_BUNDLE_SHA256: <sha256>
REPLAY_BUNDLE_BYTES: <integer>
REPLAY_PROTOCOL: PASS
REPOSITORY_GOVERNANCE: PASS|FAIL
SCOPE: PASS|FAIL
HUMAN_DECISION: REQUIRED
G5: PENDING_HUMAN
FINAL_VERDICT: READY_STUDENT_V01_JOB09_G5_FOR_HUMAN_REPLAY
```

Also provide the downloadable replay-bundle link.

Then wait for the human.

---

# PHASE B — HUMAN DECISION

## 9. Accept only an explicit human form

Resume Phase B only after the human submits a completed block based on the exact replay bundle.

Required form:

```text
G5_HUMAN_REVIEW
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
REPLAY_BUNDLE_SHA256: <exact Phase-A hash>
HUMAN_REPLAY_COMPLETED: YES
COLD_START_COMPREHENSION: PASS|HOLD
INFORMATION_DENSITY: PASS|HOLD
PEDAGOGICAL_FLOW: PASS|HOLD
INTERACTION_GESTURE_QUALITY: PASS|HOLD
KEYBOARD_ACCESSIBILITY: PASS|HOLD
SCREEN_READER_ACCESSIBILITY: PASS|HOLD
FEEDBACK_SCORING_TRUST: PASS|HOLD
RECOVERY_RESUME_CLARITY: PASS|HOLD
MOBILE_TOUCH_USABILITY: PASS|HOLD
FULL_30_45_MIN_JOURNEY: PASS|HOLD
OVERALL_LIMITED_PILOT_CONFIDENCE: PASS|HOLD
BLOCKER_FINDINGS: NONE|<text>
MAJOR_FINDINGS: NONE|<text>
MINOR_FINDINGS: NONE|<text>
PILOT_GUARDRAILS: NONE|<text>
FINAL_DECISION: GO_LIMITED_PILOT|HOLD
```

Do not convert casual approval into this decision.

Do not infer missing PASS fields.

If incomplete or hash-mismatched, return `HUMAN_DECISION_INVALID` without Git mutation and ask for the corrected block.

---

## 10. Decision validity

### GO_LIMITED_PILOT is valid only if

- candidate SHA exact;
- replay-bundle SHA exact;
- `HUMAN_REPLAY_COMPLETED: YES`;
- every mandatory human dimension = PASS;
- BLOCKER_FINDINGS = NONE;
- MAJOR_FINDINGS = NONE;
- MINOR findings, if any, have explicit non-blocking acceptance/guardrails;
- final decision explicitly says `GO_LIMITED_PILOT`.

### HOLD

A human may choose HOLD for any reason.

Do not overrule it with automation.

If the human reports a blocker/major or any mandatory HOLD, final G5 is HOLD.

JOB09 does not repair the issue.

---

## 11. Durable human decision

After a valid explicit human form, create exactly:

`qualification/STUDENT_V01_JOB09_G5_HUMAN_DECISION.md`

Record:

- candidate SHA;
- replay prep SHA;
- replay-bundle SHA/bytes;
- nested learner-package SHA/bytes;
- the human-provided dimension statuses;
- findings and guardrails;
- final human decision;
- explicit authorization boundary.

Do not invent observations not supplied by the human.

Commit this file alone.

Record:

`HUMAN_DECISION_SHA`

Then create final evidence:

`qualification/STUDENT_V01_JOB09_G5_RESULT.md`

as a later evidence-only commit.

Record final:

`EVIDENCE_HEAD`

---

## 12. Final authorization boundary

If valid GO:

G5 PASS authorizes only:

- first limited cohort of **5–6 real student sessions**;
- exact G4 candidate/package identity only;
- use of human-recorded pilot guardrails.

It does **not** authorize:

- main merge;
- broad rollout;
- release promotion;
- production readiness;
- silent repair after feedback.

If HOLD:

- student sessions remain blocked;
- classify findings for Control Room;
- do not repair from JOB09.

---

## 13. Final result block

After Phase B, return exactly:

```text
STUDENT_V01_JOB09_G5_RESULT
JOB09_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
G4_EVIDENCE_HEAD: 18b925436777943b19c4b031c24659ad60dee133
REPLAY_PREP_SHA: <phase-a durable replay-prep commit>
REPLAY_BUNDLE_SHA256: <exact human-reviewed outer bundle>
LEARNER_PACKAGE_SHA256: a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10
HUMAN_DECISION_SHA: <dedicated human-decision commit>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 427
PR: <authoritative job09 pr>
COLD_START_COMPREHENSION: PASS|HOLD
INFORMATION_DENSITY: PASS|HOLD
PEDAGOGICAL_FLOW: PASS|HOLD
INTERACTION_GESTURE_QUALITY: PASS|HOLD
KEYBOARD_ACCESSIBILITY: PASS|HOLD
SCREEN_READER_ACCESSIBILITY: PASS|HOLD
FEEDBACK_SCORING_TRUST: PASS|HOLD
RECOVERY_RESUME_CLARITY: PASS|HOLD
MOBILE_TOUCH_USABILITY: PASS|HOLD
FULL_30_45_MIN_JOURNEY: PASS|HOLD
OVERALL_LIMITED_PILOT_CONFIDENCE: PASS|HOLD
BLOCKER_FINDINGS: NONE|PRESENT
MAJOR_FINDINGS: NONE|PRESENT
MINOR_FINDINGS: NONE|PRESENT
PILOT_GUARDRAILS: NONE|PRESENT
HUMAN_DECISION: GO_LIMITED_PILOT|HOLD
REPOSITORY_GOVERNANCE: PASS|FAIL
SCOPE: PASS|FAIL
AUTHORIZED_STUDENT_SESSIONS: 5-6|0
G5: PASS|HOLD|FAIL
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_JOB09_G5_READY_FOR_LIMITED_5_6_STUDENT_PILOT`
- `HOLD_STUDENT_V01_JOB09_G5_HUMAN_READINESS`
- `HOLD_STUDENT_V01_JOB09_G4_DRIFT`
- `HOLD_STUDENT_V01_JOB09_REPLAY_IDENTITY_DRIFT`
- `FAIL_STUDENT_V01_JOB09_SCOPE_VIOLATION`

The model may return the PASS token only after a valid explicit human `GO_LIMITED_PILOT`.
