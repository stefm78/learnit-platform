# Student V0.1 — V5 Runtime / Atlas Projection R1 Qualification Result

## Binding

- Work package: `ATLAS-WP-057`
- Issue: #444
- Draft PR: #445
- Branch: `student-v01/r2-v5-runtime-atlas-projection-r1`
- Human R2 decision: issue #431 comment `5817817692` — `GO_PRE_PILOT_V5`
- Qualified Handoff-2 parent: `student-v01/r2-v5-authoring-factory-r1@dc855d1c527bcc27a8fca262dd2ad814aed96cb0`
- Handoff-2 RESULT_SHA: `a3e14ddfc631da7c8fe089f0fc45ea5e19661dec`
- Functional RESULT_SHA: `f1254562247a2ee54d5a5329b953fafc22eb8fd3`
- Merge-base with Handoff 2: exact parent head
- Candidate behind parent: 0

## Frozen authority identities

Qualified V5 remains byte-identical:
- `contracts/learnit-kit-v5.schema.json`: `15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7`
- `authoring/v5/validate_kit.py`: `0b93925eb22058878f13bc86554126846d2923d1`
- `authoring/v5/tests/test_validate_v5.py`: `61cc3f77e5efb89d350fb4569808f58fd3ecd912`

Frozen V4 remains byte-identical:
- `contracts/learnit-kit-v4.schema.json`: `e141bd5fafa75dda88a49e8a2094e4589bb4306e`
- `authoring/v4/validate_kit.py`: `4ef561dfc1137aa436b4d8c8820db421ab6e1861`
- `authoring/v4/tests/test_validate_v4.py`: `85debca78c3ec342d9e4e7ed63a033fd0968e72e`

Frozen evaluation / Atlas persistence / selected presenter surfaces remain byte-identical:
- `apps/learnit-next/src/core/activity_semantics.js`: `07c4595332419da1da0473a9715f09894620f6bd`
- `apps/learnit-next/src/adapters/atlas_indexeddb.js`: `c8b6f27326ba6aa4b7caf16ab6ef178f0812312f`
- `apps/learnit-next/src/ports/atlas_storage.js`: `8def176ac7b96748a2384af97f23183016a4a4be`
- `apps/learnit-next/src/ui/atlas_session.js`: `712c378a8e7675b6656c84efb6ba23a866fc5292`
- `apps/learnit-next/src/ui/activity_presenters.js`: `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`
- `apps/learnit-next/src/ui/media.js`: `1c84d5da04025cf372e3496fb7d25c088d1a0650`

## Exact functional candidate blobs

- `apps/learnit-next/src/core/contract.js`: `176a523e81006e9dcb574b2154f564403f64cd3f`
- `apps/learnit-next/src/core/import.js`: `3891c7d464003200d4cee6ce350b400359a1a20b`
- `apps/learnit-next/src/integration/atlas/activity_projection.js`: `06025e76b6b60d1dc3bee3af43e661689da99d08`
- `apps/learnit-next/src/integration/atlas/session.js`: `21a0fe27acbdde4698d0651e72ffa3da644b44ce`
- `apps/learnit-next/src/main.js`: `ac68280407fd356bfe6dc8b86af83d742ce55352`
- `apps/learnit-next/source_manifest.json`: `17b56aa94638ba700344571460241b36575d6c80`
- `apps/learnit-next/tests/v5_runtime_atlas_projection_r1.py`: `dd06bb12038e19bbe4293ebff6622e4dbca0be54`
- `docs/architecture/student-v0.1/LEARNIT_KIT_V5_RUNTIME_ATLAS_PROJECTION.md`: `666e5ddf5ea77e4d4f84c210ff898f4f2d5c5ff0`
- `work-packages/ATLAS-WP-057.json`: `c3c41050004551e4cffa3a76a9acf0302a52ab9c`

## Causal qualification

A transient CI carrier was used only to execute the exact candidate in GitHub Actions and was removed before RESULT_SHA. The carrier head and RESULT_SHA have identical Handoff-3 product/test/source-manifest blobs; their only tree difference is removal of `.github/workflows/atlas-wp057-transient-qualification.yml`.

Qualification carrier:
- Head: `6f04da2f20471c0aa79eeec19b6aaddfc7d7b20e`
- Workflow: `ATLAS-WP-057 transient qualification carrier`
- Run: `36086994983`
- Job: `107920997062`
- Conclusion: **SUCCESS**

Evidence:
- Handoff-3 causal probe: **PASS**
- Runtime references fetch: **NONE**
- New Atlas persistence schema: **NONE**
- V5 qualified validator regression: **11/11 PASS**
- V4 canonical validator regression: **8/8 PASS**
- V5 Authoring / Factory / source-governance regression: **20/20 PASS**
- Historical Student V0.1 runtime semantics: **92/92 PASS**
  - the historical sentinel that treated `learnit.kit.v5` as an unknown contract was shifted transiently to `learnit.kit.v6` in the CI checkout only, because explicit V5 admission is the intended Handoff-3 change;
  - the repository test file itself was not modified.
- Atlas activity UI secret boundary: **PASS**
- Atlas core IndexedDB: **5/5 PASS**
- Atlas core semantics: **8/8 PASS**
- Atlas core V3 relational: **17/17 PASS**
- Atlas learning suite: **PASS**
- Atlas M1 integration suite: **15/15 PASS**
- Deterministic Learn-it Next build: **PASS**
  - bytes: `491322`
  - SHA-256: `60aaae4c27aeefe4fd93d9aff0624407258ef2abee085944c1ff51cb4f7017dd`

The first build attempt under a shallow checkout failed because the pre-existing source manifest references historical Git blobs unavailable to a shallow clone. The qualification carrier was changed to `fetch-depth: 0`; no product repair or historical-debt expansion was made.

Repository governance on exact RESULT_SHA:
- Run: `36087070642`
- Conclusion: **SUCCESS**

## Final adversarial audit

1. Exact Handoff-2 base proven and unchanged? **PASS.**
2. Qualified V5 schema changed? **No — PASS.**
3. Qualified V5 validator changed? **No — PASS.**
4. Qualified V5 validator tests changed? **No — PASS.**
5. Frozen V4 schema/validator/tests changed? **No — PASS.**
6. V5 admitted explicitly without V4 conversion? **PASS.**
7. V2/V3/V4 installation behavior preserved? **PASS; the V5 discriminator is persisted only for V5.**
8. V5 embedded assets preserved at import? **PASS.**
9. Initial V5 learner payload contains a `hints` key? **No — PASS.**
10. Initial V5 learner payload contains unrevealed hint text? **No — PASS.**
11. Prompt/content media remain available initially? **PASS.**
12. `placement=feedback` media appear initially? **No — PASS.**
13. Feedback media require the separate authorized post-transition seam? **PASS.**
14. Learner references expose anything beyond `{url,label,hook}`? **No — PASS.**
15. Display/answer/scoring requires a reference network fetch? **No — PASS.**
16. Hint reveal occurs before durable Atlas confirmation? **No — PASS.**
17. Canonical hint order is exactly 1 → 2 → 3? **PASS.**
18. A fourth hint request creates another Atlas assistance record? **No — PASS.**
19. Concurrent hint requests can consume two ranks? **No — PASS.**
20. Non-hint assistance advances hint rank? **No — PASS.**
21. Resume after committed hints reconstructs from durable AssistanceUseRecord + ResumeState evidence? **PASS.**
22. Commit-then-crash before rendering skips or loses a hint? **No — PASS.**
23. Pinned content revision mismatch falls back to another revision? **No; assistance fails closed — PASS.**
24. New Atlas counter/store/table/schema/sidecar or selected V7 presenter change introduced? **No — PASS.**

## Scope and verdict

The functional diff contains only the nine Handoff-3 paths authorized by ATLAS-WP-057. No V8, selected-presenter redesign, final “Pour aller plus loin” UI, 10C port, semantic fan-in, ATLAS-WP-054 work, merge, cherry-pick, promotion or student session was executed.

`PASS_READY_FOR_R2_HANDOFF_4`

Next:
`R2_HANDOFF_4_V8_SELECTED_PRESENTERS`

This result stops before Handoff 4.
