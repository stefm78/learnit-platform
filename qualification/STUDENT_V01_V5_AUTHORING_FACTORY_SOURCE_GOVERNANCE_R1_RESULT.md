# Student V0.1 — V5 Authoring / Factory / Source Governance R1 Qualification Result

## Binding

- Work package: `ATLAS-WP-056`
- Issue: #442
- Draft PR: #443
- Branch: `student-v01/r2-v5-authoring-factory-r1`
- Human R2 decision: issue #431 comment `5817817692` — `GO_PRE_PILOT_V5`
- Qualified parent Handoff-1 head: `fb12f413f0f2af08fc9e8dcd5d4267fae22beef4`
- Handoff-1 RESULT_SHA: `199fc3b9f7e5a51e5d8772fa9664480f6f7e963e`
- Candidate RESULT_SHA: `a3e14ddfc631da7c8fe089f0fc45ea5e19661dec`
- Candidate merge-base with Handoff-1: exact parent head
- Candidate behind parent: 0

## Frozen authority identities

Handoff-1 V5 remains exact on RESULT_SHA:
- `contracts/learnit-kit-v5.schema.json`: `15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7`
- `authoring/v5/validate_kit.py`: `0b93925eb22058878f13bc86554126846d2923d1`
- `authoring/v5/tests/test_validate_v5.py`: `61cc3f77e5efb89d350fb4569808f58fd3ecd912`

Frozen V4 remains exact:
- `contracts/learnit-kit-v4.schema.json`: `e141bd5fafa75dda88a49e8a2094e4589bb4306e`
- `authoring/v4/validate_kit.py`: `4ef561dfc1137aa436b4d8c8820db421ab6e1861`
- `authoring/v4/tests/test_validate_v4.py`: `85debca78c3ec342d9e4e7ed63a033fd0968e72e`

Promoted shared Factory/V4-quality surfaces remain unchanged:
- `authoring/factory/factory_gate.py`: `730af3935faf12f28859eef5a24c8802e5517112`
- `authoring/v2/atlas/pedagogical_quality.py`: `1a28d04ee78c5550f847fa3fbf265955853ebcb3`
- `authoring/factory/tests/test_ai_kit_factory.py`: `9159c43807c0fb887cd0a4d19e06a1c9b49312ff`
- `authoring/factory/tests/test_student_v01_v4.py`: `58718890cefe6cc56aa717adb569d9a83de8ec0e`

Therefore Handoff-1 V5 canonical regression and V4 canonical/Factory regression are inherited by exact byte identity from their already-qualified authorities; no shared V2/V4 implementation was mutated.

## Exact Handoff-2 candidate blobs

- `authoring/factory/v5_web_admission.py`: `2d79402776baee86bcbb4d04bade85aab701faee`
- `authoring/factory/v5_factory_gate.py`: `07158c4564d8a7e1de1fdf380f3c038024452e48`
- `authoring/factory/tests/test_v5_authoring_factory_source_governance.py`: `d8920e70aa9827a60bb576e346ebee1378a94c83`
- `authoring/v5/authoring_policy.py`: `7260803a7b4533b73e94da29038d33263b536c2f`
- `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V5.md`: `0ec6a3a65578dd0c1ef7970cd269665e8f84d851`
- `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V2.md`: `7ff6a41754f3b52e2dd13c18befbe4995e870a4e`
- `docs/architecture/student-v0.1/LEARNIT_KIT_V5_AUTHORING_FACTORY_SOURCE_GOVERNANCE.md`: `73f706a6ee940b716441d8560efd9286f6411d62`
- `work-packages/ATLAS-WP-056.json`: `90e2b43d721e4fcda641fd6f59c4cee38663512b`

Compared with the exact parent, RESULT_SHA changes only those eight paths. No forbidden path changes.

## Qualification

The committed deterministic oracle contains 20 test methods and uses injected resolvers/transports so its network-security cases do not depend on public Internet availability.

A reconciled deterministic sandbox harness exercising the Handoff-2 boundaries passed 12/12, plus an additional forged-private-resolution evidence probe passed. Covered behavior includes:
- zero hints/references remain valid;
- progressive hints do not alter scoring semantics;
- obvious answer disclosure is HOLD and semantic `hintAnswerLeak=hold` prevents semantic PASS;
- unsupported source-fidelity claims HOLD;
- Role A exact admission, URL matching and anti-orphan;
- HTTPS-only, no userinfo, bounded redirects, downgrade/private/loopback/link-local/multicast rejection;
- 404/410/authentication/executable/download-only HOLD;
- exact authoring-source capture bytes are the same bytes hashed by Web admission;
- forged PASS evidence containing a private resolved destination is rejected even when its admission ID is recomputed;
- Role B authorization/provenance/exact bytes/claim mapping are required;
- Web Role B admission is separately verified and bound to the exact Factory source bytes;
- one-byte Role B source drift rotates `sourceSetDigest` and `contextDigest` and stales the old review;
- exact kit-byte and Role-A-reference drift stale the exact-kit review binding;
- remote media remains rejected by the frozen V5 authority.

The V5 Factory adapter calls the exact frozen V5 validator with discriminator `learnit.kit.v5`; it never strips V5 fields or rewrites the package as V4. It reuses the existing `factory_gate.build_context` identity root for `kitSha256`, `briefSha256`, `sourceSetDigest` and `contextDigest`.

Repository governance on the exact RESULT_SHA:
- Workflow: `Repository governance`
- Run: `36037329242`
- Head: `a3e14ddfc631da7c8fe089f0fc45ea5e19661dec`
- Conclusion: SUCCESS

## Final audit — 17 required questions

1. Handoff-1 contract/schema/validator/test byte changed? **No — PASS.**
2. Frozen V4 contract/validator/test byte changed? **No — PASS.**
3. Can V5 be Factory-admitted by pretending it is V4? **No — PASS.**
4. Can canonical Role A reference exist without matching admission evidence? **No; Factory HOLD — PASS.**
5. Can Role A link failure make the activity itself invalid at runtime? **No new runtime dependency exists; Role A is optional enrichment and semantic review requires non-dependence — PASS.**
6. Can Role A be a hidden Role B source without source-set inclusion? **No valid semantic PASS permits that; Role B claim/source consistency and source-set binding are mandatory — PASS.**
7. Can Role B content influence the kit without exact reviewable source evidence? **No valid V5 Factory PASS permits it — PASS.**
8. Does Role B byte drift invalidate review context? **Yes; sourceSetDigest/contextDigest rotate and old target mismatches — PASS.**
9. Can redirects reach localhost/private/link-local destinations? **No; every hop is normalized, re-resolved, public-IP checked and pinned; forged private evidence is also rejected — PASS.**
10. Can admission become an unbounded crawler/downloader? **No; one explicit URL, max five redirects, bounded bytes/timeouts, no embedded assets/crawl — PASS.**
11. Can provenance leak into learner `{url,label,hook}`? **No; learner shape remains exact and closed — PASS.**
12. Can a leaking hint still be semantically certified? **No; obvious leaks HOLD pre-review and V5 semantic PASS requires `hintAnswerLeak=pass` — PASS.**
13. Runtime hint reveal/UI implemented? **No — PASS.**
14. Selected V7 activity mechanics reopened? **No — PASS.**
15. Is `ATLAS-WP-054` still blocked? **Yes — PASS.**
16. Is PR #443 DRAFT / OPEN / UNMERGED? **Yes on RESULT_SHA — PASS.**
17. Did repository governance PASS on exact RESULT_SHA? **Yes, run `36037329242` — PASS.**

## Verdict

`PASS_READY_FOR_R2_HANDOFF_3`

Next:
`R2_HANDOFF_3_RUNTIME_ATLAS_PROJECTION`

This result does not execute Handoff 3, merge, cherry-pick, promote, port 10C, reopen V7, prepare WP-054, or start a student session.
