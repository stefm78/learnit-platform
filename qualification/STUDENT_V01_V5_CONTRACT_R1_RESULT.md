# Student V0.1 — V5 Contract R1 Qualification Result

## Binding

- Work package: `ATLAS-WP-055`
- Issue: #440
- Draft PR: #441
- Branch: `student-v01/r2-v5-contract-r1`
- Human R2 decision: issue #431 comment `5817817692` — `GO_PRE_PILOT_V5`
- Common base: `18b925436777943b19c4b031c24659ad60dee133`
- Candidate RESULT_SHA: `199fc3b9f7e5a51e5d8772fa9664480f6f7e963e`
- Candidate merge-base with common base: exact common base
- Candidate ahead/behind: 7 / 0

## Exact blobs

V5 candidate:
- `contracts/learnit-kit-v5.schema.json`: `15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7`
- `authoring/v5/validate_kit.py`: `0b93925eb22058878f13bc86554126846d2923d1`
- `authoring/v5/tests/test_validate_v5.py`: `61cc3f77e5efb89d350fb4569808f58fd3ecd912`

Frozen V4 on the exact candidate head:
- `contracts/learnit-kit-v4.schema.json`: `e141bd5fafa75dda88a49e8a2094e4589bb4306e` — unchanged PASS
- `authoring/v4/validate_kit.py`: `4ef561dfc1137aa436b4d8c8820db421ab6e1861` — unchanged PASS
- `authoring/v4/tests/test_validate_v4.py`: `85debca78c3ec342d9e4e7ed63a033fd0968e72e` — unchanged PASS

## Exact candidate changed paths

Compared with `18b925436777943b19c4b031c24659ad60dee133`, RESULT_SHA changes only:

1. `authoring/v5/tests/test_validate_v5.py`
2. `authoring/v5/validate_kit.py`
3. `contracts/learnit-kit-v5.schema.json`
4. `docs/architecture/student-v0.1/LEARNIT_KIT_V5_CONTRACT_DELTA.md`
5. `work-packages/ATLAS-WP-055.json`

Scope: PASS.

## Narrow deterministic execution

The sandbox has no outbound Git network access, so the test harness was materialized only from exact GitHub-authority file content already retrieved through the GitHub connector. Before execution, `git hash-object` was used to bind each critical local file to its GitHub blob:

- v2 validator: `f14fd2435706000800d92d4a139448e7d8b28ce1`
- V4 schema: `e141bd5fafa75dda88a49e8a2094e4589bb4306e`
- V4 validator: `4ef561dfc1137aa436b4d8c8820db421ab6e1861`
- V4 tests: `85debca78c3ec342d9e4e7ed63a033fd0968e72e`
- V5 schema: `15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7`
- V5 validator: `0b93925eb22058878f13bc86554126846d2923d1`
- V5 tests: `61cc3f77e5efb89d350fb4569808f58fd3ecd912`

Commands:
- `PYTHONPATH=. python -B authoring/v4/tests/test_validate_v4.py`
- `PYTHONPATH=. python -B authoring/v5/tests/test_validate_v5.py`

Results:
- V4 canonical regression: 8/8 PASS.
- V5 contract qualification: 11/11 PASS.

## Required qualification matrix

- V4 schema byte identity: PASS.
- V4 validator byte identity: PASS.
- V4 validator-test byte identity: PASS.
- Existing V4 canonical regression: PASS.
- V4 payload with `hints` or `references`: rejected PASS.
- V5 canonical package without hints/references: PASS.
- All eight activity families admit V5 hints: PASS.
- All eight activity families admit V5 references: PASS.
- Hints cardinality 0..3 accepted / 4 rejected: PASS.
- Empty and whitespace-only hints rejected: PASS.
- Closed V5 activity schema rejects unknown fields: PASS.
- Valid HTTPS `{url,label,hook}` reference accepted: PASS.
- Reference object is closed; missing label/hook and extra provenance fields rejected: PASS.
- Media-shaped reference rejected: PASS.
- `http:`, `javascript:`, `file:`, `blob:`, protocol-relative, malformed, credential-bearing and backslash URLs rejected: PASS.
- Reference validation performs no link fetching; a socket connection attempt is patched to fail during the positive URL test and no attempt occurs: PASS.
- V4 embedded-media semantics reused: PASS.
- Remote media URL rejected: PASS.
- Unsafe SVG regression rejected: PASS.
- Changing a hint changes activity/course/package digest chain: PASS.
- Changing reference URL, label or hook changes digest chain: PASS.
- Reordering hints changes canonical identity: PASS.
- Unchanged V5 revalidation is deterministic: PASS.
- V4 digest behavior remains unchanged: PASS.
- V5 validator rejects `learnit.kit.v4`: PASS.
- V4 validator rejects `learnit.kit.v5`: PASS.
- No implicit conversion path introduced: PASS.

## Repository governance

Initial exact-head run `36027970032` on earlier candidate `98f94ba3e05bd18316c994072bbd17e82a1cebde` failed because the newly created work-package file did not yet conform to the repository's canonical work-package schema. No contract/schema/validator failure was reported.

The work-package file alone was repaired within the authorized mutation surface.

Final candidate exact-head run:
- Workflow: `Repository governance`
- Run: `36028338399`
- Head: `199fc3b9f7e5a51e5d8772fa9664480f6f7e963e`
- Conclusion: SUCCESS

Repository governance: PASS.

## Final independent audit

1. Any V4 byte or meaning changed? **No** — PASS.
2. Can V4 silently carry V5 hints/references? **No** — V4 family closure rejects them — PASS.
3. Can a V5 reference become remote media? **No** — reference shape is distinct and V4 media semantics are reused — PASS.
4. Did Handoff 1 implement Factory/runtime/UI/showcase behavior? **No** — changed-path audit PASS.
5. Are hints/references digest-bearing canonical content? **Yes** — mutation and ordering tests PASS.
6. Does URL validation require network access? **No** — static parsing only; no socket call occurs — PASS.
7. Is the candidate based on the exact authorized common base? **Yes** — merge-base exact, behind 0 — PASS.
8. Is PR #441 DRAFT / OPEN / UNMERGED? **Yes** at RESULT_SHA audit — PASS.
9. Is `ATLAS-WP-054` still blocked? **Yes**. R2 requires Handoff 2, runtime/Atlas projection, V8, exact 10C port/requalification, fresh semantic review, fan-in regression and human replay before WP-054 can proceed.
10. Is the next safe action Handoff 2 rather than fan-in? **Yes** — PASS.

## Verdict

`PASS_READY_FOR_R2_HANDOFF_2`

This result does not merge, promote, execute Handoff 2, prepare `ATLAS-WP-054`, or start a student session.
