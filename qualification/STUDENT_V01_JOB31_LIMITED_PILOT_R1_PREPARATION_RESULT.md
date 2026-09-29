# STUDENT V0.1 — JOB31 LIMITED PILOT R1 PREPARATION RESULT

JOB: `JOB_31_LIMITED_PILOT_5_6_STUDENTS_EXECUTION_R1`  
WORK_PACKAGE: `ATLAS-WP-073`  
ISSUE: #477  
PR: #478 — DRAFT / OPEN / UNMERGED

## Authority

- JOB30 evidence head: `af14bc0a9b1988b5d42b158ae4a6b3afa544221f`
- Reviewed frozen product SHA: `e04cf62963faae83e073cde9cffd9d33ae42dc9c`
- G5: `PASS / GO_LIMITED_PILOT`
- Authorized cohort: first cohort only, target 5–6, hard maximum 6
- HR24-003: `CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED`
- HR24-003 pilot acceptance: `ACCEPT`

## Exact frozen identities

- deterministic learner build: 583764 bytes
- deterministic learner build SHA-256: `7ee493b8855e4cda7703deccbf5c813391afaa5a9674d6760b75a277e0267553`
- exact V5 showcase SHA-256: `aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b`
- kit contract: `learnit.kit.v5`
- activity count: 10

## Phase A machine qualification

Source qualification head: `f2bf7a7df6ba3616606424d2bd5dc63f4029e260`

- JOB31 workflow run #16 / run id `36597977846`: SUCCESS
- duplicate push run #15 / run id `36597971972`: SUCCESS
- Repository governance run #1549 / run id `36597977722`: SUCCESS
- exact topology / mutation allowlist: PASS
- exact frozen learner rebuild twice: PASS
- exact V5 showcase validation: PASS
- learner/facilitator package determinism: PASS
- session/state/ledger adversarial rejection: PASS
- desktop first start: PASS
- mobile 390x844 first start: PASS
- recovery/reset: PASS
- no horizontal overflow: PASS
- no remote network: PASS
- learner secret projection boundary: PASS
- generated ZIPs not tracked: PASS
- repository governance: PASS

Machine smoke is explicitly **not** a real student session.

## Qualified package identities

### Learner package

- exact ZIP SHA-256: `b2d11f0a5e33a19de98744a06178cdccdf1aa5078f07c1352b38ca4fffcb62c8`
- GitHub Actions artifact id: `11046433814`
- artifact name: `student-v01-limited-pilot-r1-learner-f2bf7a7df6ba3616606424d2bd5dc63f4029e260`
- artifact-retention expiry recorded by GitHub: 2026-10-29

### Facilitator package

- exact ZIP SHA-256: `c2ba3f37558537ffb37ec958fcc97d52ff82038a33313bee00e6e9853c400e38`
- GitHub Actions artifact id: `11047230520`
- artifact name: `student-v01-limited-pilot-r1-facilitator-f2bf7a7df6ba3616606424d2bd5dc63f4029e260`
- artifact-retention expiry recorded by GitHub: 2026-10-29

The artifact-service archive digest is not substituted for the exact inner pilot ZIP SHA-256.

## Durable pilot state

After successful Phase A qualification:

- `PILOT_STATE = READY_NOT_STARTED`
- `COMPLETED_REAL_SESSIONS = 0`
- `HOLD_STATUS = NONE`
- learner package identity: frozen
- facilitator package identity: frozen
- cohort ledger: LP01..LP06 all `NOT_RUN`

No participant, consent document, raw notes, audio/video, photograph, device/account identifier, email, address, IP address, or other identifying material is persisted in Git.

## Decision

`PASS_JOB31_PHASE_A_PREPARATION_READY_NOT_STARTED`

This does **not** declare pilot success and does **not** claim that any real student has used the candidate.

NEXT_GATE: `REAL_STUDENT_SESSION_LP01_REQUIRED`

No product mutation, merge, promotion, second cohort, expansion beyond six, or HR24-003 technical resolution is authorized by this result.
