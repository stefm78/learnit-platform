# Student V0.1 JOB06 R1 — Author-side repair audit

## Authority and exact repair target

- Constitutional authority: `UCP-CONTROL-PLANE 1.1-R4 ACTIVE`, exact SHA-256 `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`.
- Active control-plane HEAD Git blob at preflight: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`; UAO 2.6 plus UAS 2.4, UAB 1.3, UAA 1.2 and compatibility contract 1.0 were exact-hash verified.
- Authority issue: #421; work package: `ATLAS-WP-042`; DRAFT repair PR: #422.
- JOB06 R1 base: `28d6e2968fcbe79d7225b2c29efda22317af09c8`.
- Preparation head: `d72286e381d53d81fce8397f9c0f96606c6c08aa`.
- Historical independent G3 semantic-review commit: `461b3a39440568d0f55c6a9b3d83f979e875bd78`; evidence head: `38892dc2bb65afd3b3c74b06cb6ff56bad8a5627`.
- Accepted findings: `G3-SEM-001` and `G3-SEM-002`. They are repair inputs, not a review of the repaired bytes.

## Minimal semantic repair

### G3-SEM-001
Removed only the earlier matching exposure:
- left `356f1c65-15dd-4abe-b3b0-39ae1c899356` — `5 − 2i`;
- right `8e33618e-5f8f-409d-8e8a-435a7c39ef8b` — `5 + 2i`;
- the corresponding matching solution entry.

The validation at `$.courses[0].activities[5]` is semantically unchanged, including revision `1bd5164b-8905-4742-8ba1-7f37bff6337c` and digest `sha256:86f3d199b53e14b26d0943c7aa4534dab21848e4347d44294cef90b6e3f2f04c`.

### G3-SEM-002
Removed only the earlier matching exposure:
- left `839fe45f-b8c9-40a3-9dd1-4de798ecb08f` — `|−5 + 12i|`;
- right `b85b6ad3-6305-4518-a9cd-b987c2ce2751` — `13`;
- the corresponding matching solution entry.

The validation at `$.courses[0].activities[9]` is semantically unchanged, including revision `9ba5d27c-2982-4b2c-b1de-574652d4043d` and digest `sha256:45075f52952487f27fad15219355ff28c670b2e21de3f7a05d242ab6e1ae3920`.

Each repaired matching retains two complete one-to-one pairs. No replacement mathematical instance was invented.

## Revision and digest hygiene

- Activity 2 revision: `4df86b61-81fa-489a-aed2-fb0abde50ded` -> `66c05bee-82c6-4192-8e0e-4ef4412f6095`
- Activity 2 digest: `sha256:64decd72d4a575bd08c9c26f00e180b1f3f72e15a4a4c29093d4ceb8a289dc55` -> `sha256:493ee2474d5776453814a9b23913a9edc2e65d4b1b64f9415230ae0aea23742e`
- Activity 8 revision: `11536112-05f1-4548-93b5-80f6d5b4db7a` -> `c08425be-c74a-4610-aef0-9d2bd0a721d9`
- Activity 8 digest: `sha256:4027721883d27c4987faace4c152cc499adf161dc26eb0408787038104a24ea9` -> `sha256:2658c1a66a451a74352a5c64710d6d0b016b42e95b308d83a9d235aaf66f0fe4`
- Course revision: `584b1cc7-2915-4ef0-b866-56fe3186fc78` -> `a0a34de6-e00a-41c5-97db-010c3fd333df`
- Course digest: `sha256:d09e729b12ca7cba0c08de38bcb928dc26da5ae3d0e155f573ee2555be3050c5` -> `sha256:c66a0871c8bc1d767507ed60f593e6b82810acc92b47c5b7aad66e99e8863418`
- Package revision: `77305022-2670-4983-9ec1-f59a76011c95` -> `14a8e677-ea6a-4705-a7b8-cffbbd5ed1f1`
- Package digest: `sha256:481e971dc71a1994219d50c6f5c1ef02ce646c42ae0a0086623796b36c376acb` -> `sha256:69027acc24444047d0be714eb417addace9d28a7b946e7533dfb7768c63a26ee`

All nine untouched activities retain their prior revision IDs and digests. All activity/course/package digests were recomputed with the frozen canonical NFC + sorted-key JSON + SHA-256 algorithm and rechecked.

## Canonical, quality, provenance and contamination checks

- `V4_CANONICAL: PASS`; zero errors/warnings, 55 canonical IDs, 12 objective references, 11 activities, no assets/media, matching coverage 2/2 on both repaired activities.
- Pedagogical quality: `EXCELLENT_BY_PROFILE`; zero blocking/warning/advice diagnostics under the frozen Student V0.1 V4 profile.
- Activity count, activity type/order, objectives and declared 42-minute duration are unchanged.
- Source bytes are unchanged: `sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`.
- Learner brief is unchanged: `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`.
- Provenance for activity 2 now retains only source activity refs 0 and 2; provenance for activity 8 retains only refs 5 and 8.
- Prior-to-validation contamination audit: PASS. Before activity 5, no learner-visible activity reveals the exact `5 − 2i -> 5 + 2i` mapping. Before activity 9, no learner-visible activity reveals the exact `|−5 + 12i| = 13` result.

## Fresh Factory target

- Repaired kit SHA-256: `sha256:da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`
- Brief SHA-256: `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`
- Source-set digest: `sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`
- Factory context digest: `sha256:eab953d540af138f1da0b030d9cee97fdeab4060b76bfc832ab018f7abd89123`

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_G3_R1`

No `learnit.atlas.semantic_review.v1` artifact is authored here, no semantic PASS is claimed, and the prior G3 review is not reused against changed kit bytes. A later clean-context G3 R1 reviewer owns independent semantic review and the final Factory gate.

## Scope and rollback

No source, learner brief, product/runtime/UI, schema, authoring implementation, QA, pilot, central workflow or governance file is changed by the repair. The result remains on `student-v01/wave2-showcase-kit-r1`; no merge or cherry-pick is part of this execution.

Rollback: close PR #422 and delete the repair branch; original JOB06 PR #408 and G3 HOLD evidence remain immutable historical evidence.
