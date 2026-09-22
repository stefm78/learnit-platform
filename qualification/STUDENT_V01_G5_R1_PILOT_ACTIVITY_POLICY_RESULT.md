# Student V0.1 — G5 R1 Pilot Activity Policy qualification

## Exact candidate

- Common base: `18b925436777943b19c4b031c24659ad60dee133`
- G4 candidate: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`
- Policy result SHA: `9e3685b9b811abbd5c0ceeeb70e346ee3fa4d530`
- Issue: #435
- Authoring PR: #438 — DRAFT, open, unmerged at evidence preflight.
- CI-only carrier: #439 — closed unmerged after exact-head evidence collection.
- Active HCP HEAD blob at evidence preflight: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- UCP: `UCP-CONTROL-PLANE 1.1-R4 ACTIVE`, SHA-256 `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`.

## Author-side qualification

- `PILOT_PROFILE: PASS`
- `CONSTRUCTED_EXCLUDED_FROM_PILOT: PASS`
- `V4_CONTRACT_UNCHANGED: PASS`
- `SHOWCASE_ACTIVITY_COUNT: 10`
- `SHOWCASE_DURATION_MINUTES: 39`
- `OBJECTIVES_UNCHANGED: PASS`
- `OBJECTIVE_COVERAGE: PASS`
- `REMAINING_ORDER_UNCHANGED: PASS`
- `INTERNAL_JARGON_REMOVED: PASS`
- `NO_ACCEPTED_RESPONSES_WORKAROUND: PASS`
- `SOURCE_UNCHANGED: PASS`
- `REVISION_DIGEST_HYGIENE: PASS`
- `V4_CANONICAL: PASS`
- `PEDAGOGICAL_QUALITY: PASS`
- `SOURCE_TRACEABILITY: PASS`
- `SCOPE: PASS`

Exact source remains:
- commit `281dc7470d51682c5e6d79d3fff54c46cfbced3b`;
- blob `7f83784e8719917496a694b2ad170d724190fd04`;
- 12384 bytes;
- SHA-256 `3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`.

Exact repaired Factory target:
- kit SHA-256 `sha256:10a9a9e86a9c26dc6d45e278122307ca522d057712ffc157d39ebbb93b6172b0`;
- brief SHA-256 `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`;
- source-set digest `sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`;
- Factory context digest `sha256:741e84b5c266a0888fe02b408a27e72e45f11c95afb5b5d1fd70915101eb5d13`.

## Exact-head CI evidence

Learn-it Next CI run `35788467803`, job `106950945025`, completed SUCCESS on `9e3685b9b811abbd5c0ceeeb70e346ee3fa4d530`.

The exact JOB10C route emitted:
- `STUDENT_V01_JOB10C_POLICY_CONTENT=PASS`
- `STUDENT_V01_JOB10C_V4_CANONICAL=PASS`
- `STUDENT_V01_JOB10C_PEDAGOGICAL_QUALITY=PASS:EXCELLENT_BY_PROFILE`
- `STUDENT_V01_JOB10C_FACTORY_CONTEXT=PASS`
- `STUDENT_V01_JOB10C_EXACT_ROUTE=PASS`
- `STUDENT_V01_JOB10C_TARGET=9e3685b9b811abbd5c0ceeeb70e346ee3fa4d530`

Repository governance run `35788467929` completed SUCCESS on the same result SHA:
- job `106950946039` — `validate-repository`: SUCCESS;
- job `106950994571` — `Repository governance`: SUCCESS.

The temporary carrier also triggered legacy workflows whose branch routers do not admit JOB10C. Their failures occurred before content qualification and are not reused as JOB10C evidence. The dedicated JOB10C route is the bounded exact-head verifier authorized by ATLAS-WP-053 and it checks the exact common-base scope directly.

## Semantic-review firewall

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_CORRECTIVE_REVIEW`

No historical semantic review is reused for the changed learner bytes. No independent semantic PASS is authored here.

## Result

`INTEGRATION_CI: PASS`  
`REPOSITORY_GOVERNANCE: PASS`  
`FINAL_VERDICT: PASS_STUDENT_V01_G5_R1_PILOT_POLICY_READY_FOR_INDEPENDENT_REVIEW`

This PASS authorizes only the later independent corrective semantic review/integration gate. It authorizes no merge, no G4 R1/G5 replay, and no student session.

This file is the sole evidence payload added after the frozen `POLICY_RESULT_SHA`. The Git commit containing this file is the `POLICY_EVIDENCE_HEAD`.
