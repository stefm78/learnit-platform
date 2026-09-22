# Student V0.1 JOB10C — Author-side Pilot Activity Policy R1 audit

## Authority and baseline

- Constitutional authority: `UCP-CONTROL-PLANE 1.1-R4 ACTIVE`, exact SHA-256 `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`.
- Active control-plane HEAD Git blob at mutation preflight: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`.
- Authority issue: #435; work package: `ATLAS-WP-053`; DRAFT PR: #438.
- Exact common base: `18b925436777943b19c4b031c24659ad60dee133`.
- Preparation head: `b83bdd260ce7c30279eb40ee9172e2476906321a`.
- Exact G4 candidate: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`.
- Exact G4 showcase blob: `03ed1d5819911c23734980f89716f4ca18a6bca4`.
- Source blob/hash remain `7f83784e8719917496a694b2ad170d724190fd04` / `sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`.

## Pilot policy

The first limited Student V0.1 pilot admits `lesson`, `flashcard`, `matching`, `order`, `classify`, `qcm`, and `fill`. It excludes `constructed` from pilot admission only. `constructed` remains supported by `learnit.kit.v4`, and `canonical-text-match-v1` is unchanged.

## Showcase repair

- Removed only the previous activity at index 4, lineage `ff4305ec-22c6-4880-bf7f-1f8177ea4705`, type `constructed`, 3 minutes.
- Activity count: 11 → 10.
- Course duration: 42 → 39 minutes.
- Both objective IDs and labels are byte-identical to the G4 showcase.
- All remaining activity lineage IDs preserve their previous order.
- No replacement activity was invented.
- No `acceptedResponses` field remains in the repaired showcase.

Conjugate coverage remains: lesson, flashcard, matching practice, transfer QCM, validation QCM. Module coverage remains: flashcard, order/matching/transfer practice, validation QCM.

Learner-facing cleanup:
- package title → `Nombres complexes — Conjugué et module`;
- package description/version label no longer expose Student V0.1/Showcase/Atlas provenance wording;
- flashcard and module-matching explanations no longer expose “de la source”;
- conjugate validation prompt is direct and no longer depends on a removed preceding example.

## Revision and digest hygiene

Package revision: `14a8e677-ea6a-4705-a7b8-cffbbd5ed1f1` → `7f40d370-1015-41fc-899f-b1600c5e0dbe`
Package digest: `sha256:69027acc24444047d0be714eb417addace9d28a7b946e7533dfb7768c63a26ee` → `sha256:fd447bdcee498bab50c67601c8d4dee863508d7a23410432e5ff75c0924ef323`

Course revision: `a0a34de6-e00a-41c5-97db-010c3fd333df` → `640ea095-d3f6-4fb7-92a9-b33e20302940`
Course digest: `sha256:c66a0871c8bc1d767507ed60f593e6b82810acc92b47c5b7aad66e99e8863418` → `sha256:0b7975a766e4dbaec9d9286bb54792ca73a6e4374e34f58c16d3593075c2bc07`

Changed remaining activities:
- flashcard lineage `28ef0c23-a968-4f37-bb56-8d4b0635e01c`: revision `7a918ca6-f2de-46fe-974d-64ef35b0c072` → `be024979-1d66-4ef7-ad51-9ed541d57d0b`, digest `sha256:0f72b187442b0da307f616d3f41ff80e7c6e8e0aa1e4731763a58bd4c2046b92` → `sha256:97a3b2c0b75bb2c171d3192803b0af05c6f8d2a40ee2836e0050029aad1725d8`;
- validation-QCM lineage `7672a1b7-9328-4b31-be08-1a56bbd2e57f`: revision `1bd5164b-8905-4742-8ba1-7f37bff6337c` → `66b080a6-8479-4c93-8010-273b07872bef`, digest `sha256:86f3d199b53e14b26d0943c7aa4534dab21848e4347d44294cef90b6e3f2f04c` → `sha256:3c60016fcd69c44db6ed1a6edd588b7f7a3f94ce1ba080eb75f8895e9050ee53`;
- module-matching lineage `e7279474-373a-4823-9281-59952f2e91f9`: revision `c08425be-c74a-4610-aef0-9d2bd0a721d9` → `79b0d82c-9c30-48c1-994c-622d5203a5ca`, digest `sha256:2658c1a66a451a74352a5c64710d6d0b016b42e95b308d83a9d235aaf66f0fe4` → `sha256:18e7a3922de1fe87a72ad767d44d93109f616e4e1d25eb67c77b07fd6ca4d6ec`.

All seven unchanged remaining activities retain their prior revision IDs and digests. Digests use the repository canonical NFC + sorted-key JSON + SHA-256 algorithm.

## Canonical, quality, provenance and boundary checks

- `V4_CANONICAL: PASS`; 10 activities; no `constructed`; all revision digests self-consistent.
- `PEDAGOGICAL_QUALITY: EXCELLENT_BY_PROFILE`; zero blocking/warning/advice diagnostics under the deterministic V4 profile.
- `OBJECTIVES_UNCHANGED: PASS`.
- `OBJECTIVE_COVERAGE: PASS`.
- `REMAINING_ORDER_UNCHANGED: PASS`.
- `INTERNAL_JARGON_REMOVED: PASS`.
- `NO_ACCEPTED_RESPONSES_WORKAROUND: PASS`.
- `SOURCE_UNCHANGED: PASS`.
- `SOURCE_TRACEABILITY: PASS`.
- Secret boundary: PASS; the only constructed `acceptedResponses` payload is removed with its excluded activity and no workaround is added.

## Fresh Factory target

- Repaired kit SHA-256: `sha256:10a9a9e86a9c26dc6d45e278122307ca522d057712ffc157d39ebbb93b6172b0`
- Brief SHA-256: `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`
- Source-set digest: `sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`
- Factory context digest: `sha256:741e84b5c266a0888fe02b408a27e72e45f11c95afb5b5d1fd70915101eb5d13`

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_CORRECTIVE_REVIEW`

No independent semantic-review PASS is claimed by this authoring execution. Historical semantic review is not reused as proof for these changed learner bytes. A later independent corrective review owns that gate.

## Scope and rollback

No source, learner brief, app/runtime, contract, authoring implementation, QA, pilot runtime, governance or scoring rule is changed. The only CI mutation is the bounded JOB10C route in `.github/workflows/learnit-next-ci.yml`, authorized by `ATLAS-WP-053`; it changes no product/runtime semantics. Rollback is the preparation HEAD `b83bdd260ce7c30279eb40ee9172e2476906321a`; no merge or cherry-pick is part of this execution.
