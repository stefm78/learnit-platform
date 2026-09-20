# Student V0.1 JOB06 R1 — Showcase semantic repair qualification

## Exact authority binding

- Repository: `stefm78/learnit-platform`
- Issue: #421
- Work package: `ATLAS-WP-042`
- DRAFT repair PR: #422
- JOB06 R1 base: `28d6e2968fcbe79d7225b2c29efda22317af09c8`
- Original JOB06 result: `8e0e3c43968cf0cf442e0e47b73bc38fc19ae565`
- Historical G3 semantic-review commit: `461b3a39440568d0f55c6a9b3d83f979e875bd78`
- Historical G3 evidence head: `38892dc2bb65afd3b3c74b06cb6ff56bad8a5627`
- Preparation head: `d72286e381d53d81fce8397f9c0f96606c6c08aa`
- Author-side repaired result: `80ec72fef535e78013a9f0fb10bedb57f05bc761`
- Constitutional UCP: `UCP-CONTROL-PLANE 1.1-R4 ACTIVE`, exact SHA-256 `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- Active control-plane HEAD Git blob remained `2a9014e2b2051b0ede746a9772cdbbe471f55e3a` through result mutation and evidence preflight.

## Accepted G3 findings and exact repair

### G3-SEM-001 — PASS repaired
Removed from earlier conjugate matching only:
- `356f1c65-15dd-4abe-b3b0-39ae1c899356` / `5 − 2i`
- `8e33618e-5f8f-409d-8e8a-435a7c39ef8b` / `5 + 2i`
- their matching solution entry.

The validation at activity 5 remains unchanged.

### G3-SEM-002 — PASS repaired
Removed from earlier module matching only:
- `839fe45f-b8c9-40a3-9dd1-4de798ecb08f` / `|−5 + 12i|`
- `b85b6ad3-6305-4518-a9cd-b987c2ce2751` / `13`
- their matching solution entry.

The validation at activity 9 remains unchanged.

Both matching activities retain two complete one-to-one pairs. No replacement mathematical example was invented.

## Revision identity and digest evidence

- Activity 2 revision: `4df86b61-81fa-489a-aed2-fb0abde50ded` -> `66c05bee-82c6-4192-8e0e-4ef4412f6095`
- Activity 2 digest: `sha256:64decd72d4a575bd08c9c26f00e180b1f3f72e15a4a4c29093d4ceb8a289dc55` -> `sha256:493ee2474d5776453814a9b23913a9edc2e65d4b1b64f9415230ae0aea23742e`
- Activity 8 revision: `11536112-05f1-4548-93b5-80f6d5b4db7a` -> `c08425be-c74a-4610-aef0-9d2bd0a721d9`
- Activity 8 digest: `sha256:4027721883d27c4987faace4c152cc499adf161dc26eb0408787038104a24ea9` -> `sha256:2658c1a66a451a74352a5c64710d6d0b016b42e95b308d83a9d235aaf66f0fe4`
- Course revision: `584b1cc7-2915-4ef0-b866-56fe3186fc78` -> `a0a34de6-e00a-41c5-97db-010c3fd333df`
- Course digest: `sha256:d09e729b12ca7cba0c08de38bcb928dc26da5ae3d0e155f573ee2555be3050c5` -> `sha256:c66a0871c8bc1d767507ed60f593e6b82810acc92b47c5b7aad66e99e8863418`
- Package revision: `77305022-2670-4983-9ec1-f59a76011c95` -> `14a8e677-ea6a-4705-a7b8-cffbbd5ed1f1`
- Package digest: `sha256:481e971dc71a1994219d50c6f5c1ef02ce646c42ae0a0086623796b36c376acb` -> `sha256:69027acc24444047d0be714eb417addace9d28a7b946e7533dfb7768c63a26ee`

All untouched activity revision identities/digests remain unchanged and validate.

## Deterministic author-side evidence

- G3-SEM-001 prior-answer exposure: removed.
- G3-SEM-002 prior-answer exposure: removed.
- Validation activities 5 and 9: unchanged.
- Matching minimums/one-to-one coverage: PASS, 2 left / 2 right / 2 matches for each repaired matching.
- Activity count: 11, unchanged.
- Activity type/order: unchanged.
- Objectives: unchanged.
- Declared course duration: 42 minutes, unchanged.
- Source bytes: unchanged at `sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`.
- Learner brief: unchanged at `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`.
- Canonical V4: PASS; zero errors/warnings; 55 canonical IDs; 12 objective references.
- Pedagogical quality: `EXCELLENT_BY_PROFILE`; zero blocking/warning/advice diagnostics.
- Validation contamination audit: PASS for both validations.
- Provenance: exact repaired matching refs only; no source traceability weakening.

## Fresh Factory target

- Repaired kit SHA-256: `sha256:da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`
- Brief SHA-256: `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`
- Source-set digest: `sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`
- Context digest: `sha256:eab953d540af138f1da0b030d9cee97fdeab4060b76bfc832ab018f7abd89123`

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_G3_R1`

No replacement `learnit.atlas.semantic_review.v1` artifact was created, no semantic-review PASS is claimed, and no final Factory semantic gate was fabricated. The repaired candidate requires a later clean-context independent G3 R1 review.

## Repository governance and scope

Repository governance on exact `RESULT_SHA=80ec72fef535e78013a9f0fb10bedb57f05bc761`:
- run: `35539089171`
- workflow: `Repository governance`
- conclusion: `success`
- validate-repository job: PASS
- mirrored repository-governance job: PASS

Exact `JOB06_R1_BASE..RESULT_SHA` changed paths:
1. `docs/programs/student-v0.1/jobs/JOB_06_R1_SHOWCASE_SEMANTIC_REPAIR.md`
2. `work-packages/ATLAS-WP-042.json`
3. `showcase/student-v0.1/nombres-complexes/AUTHOR_AUDIT.md`
4. `showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT.json`
5. `showcase/student-v0.1/nombres-complexes/FACTORY_REVIEW_REQUEST.md`
6. `showcase/student-v0.1/nombres-complexes/PROVENANCE_MAP.json`
7. `showcase/student-v0.1/nombres-complexes/V4_VALIDATION_REPORT.json`
8. `showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json`

No product, source, learner brief, schema, authoring implementation, QA, pilot, workflow or governance mutation occurred. No merge or cherry-pick occurred.

Evidence-only follow-up is limited to this qualification file.

## Rollback

Close PR #422 and delete `student-v01/wave2-showcase-kit-r1`. Original JOB06 PR #408 and the historical G3 HOLD evidence remain intact.

## Result

```text
STUDENT_V01_JOB06_R1_RESULT
JOB06_R1_BASE: 28d6e2968fcbe79d7225b2c29efda22317af09c8
JOB06_ORIGINAL_RESULT: 8e0e3c43968cf0cf442e0e47b73bc38fc19ae565
G3_SEMANTIC_REVIEW_SHA: 461b3a39440568d0f55c6a9b3d83f979e875bd78
RESULT_SHA: 80ec72fef535e78013a9f0fb10bedb57f05bc761
EVIDENCE_HEAD: <evidence-only commit containing this file>
ISSUE: 421
PR: 422
G3_SEM_001_REMOVED: PASS
G3_SEM_002_REMOVED: PASS
VALIDATION_ACTIVITIES_UNCHANGED: PASS
MATCHING_MINIMUMS: PASS
NO_NEW_SOURCE_CONTENT: PASS
SOURCE_UNCHANGED: PASS
LEARNER_BRIEF_UNCHANGED: PASS
JOURNEY_STRUCTURE_UNCHANGED: PASS
REVISION_DIGEST_HYGIENE: PASS
SOURCE_TRACEABILITY: PASS
V4_CANONICAL: PASS
PEDAGOGICAL_QUALITY: EXCELLENT_BY_PROFILE
VALIDATION_CONTAMINATION_AUDIT: PASS
REPAIRED_KIT_SHA256: sha256:da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff
FACTORY_CONTEXT_DIGEST: sha256:eab953d540af138f1da0b030d9cee97fdeab4060b76bfc832ab018f7abd89123
FACTORY_CONTEXT_REBOUND: PASS
SEMANTIC_REVIEW: PENDING_INDEPENDENT_G3_R1
REPOSITORY_GOVERNANCE: PASS
SCOPE: PASS
FINAL_VERDICT: PASS_STUDENT_V01_JOB06_R1_SHOWCASE_REPAIRED_FOR_G3_R1
```
