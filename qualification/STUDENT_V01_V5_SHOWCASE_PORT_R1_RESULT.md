# Student V0.1 — Exact 10C Showcase V5 Port R1 Qualification Result

## Binding

- Work package: `ATLAS-WP-059`
- Issue: #448
- Draft PR: #449
- Branch: `student-v01/r2-v5-showcase-port-r1`
- Human R2 decision: issue #431 comment `5817817692` — `GO_PRE_PILOT_V5`
- Qualified Handoff-4 parent: `student-v01/r2-v8-selected-presenters-r1@6480a21694006a78f4b75dbfea3d214277e776ba`
- Handoff-4 RESULT_SHA: `3e44a1d4d74456dc7d2d74b62b151c016cdd85df`
- Historical JOB10C oracle: PR #438 @ `982b86bf86e18b39926736f92a16be40ba47f60b`
- Historical JOB10C RESULT_SHA: `9e3685b9b811abbd5c0ceeeb70e346ee3fa4d530`
- Historical V4 kit blob: `7d90c619b05d4dbea1a1b5674be82cc0dcdcdeec`
- Functional RESULT_SHA: `1f67cae285f9afc0425734329608623894b88831`

## Exact V5 candidate

The exact repaired JOB10C Nombres complexes showcase is ported to explicit `learnit.kit.v5` with:
- 1 course;
- 10 activities;
- 39 minutes;
- exact activity family/order: lesson, flashcard, matching, qcm, qcm, flashcard, order, matching, qcm, qcm;
- same two objectives;
- same ten activity lineage IDs and order;
- same course lineage/revision/digest;
- same ten activity revision IDs/digests;
- same prompts, explanations, choices/items and canonical scoring content;
- `constructed`: absent;
- `acceptedResponses` workaround: absent.

Only the package contract discriminator and package revision identity/digest rotate for the V5 successor.

Exact candidate identities:
- V5 kit blob: `57374ba897600894ab124e8ac2d3ee3b6f5c4cc2`
- V5 kit SHA-256: `sha256:aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b`
- package revision ID: `9062f1a1-f01f-42c7-90fb-ed4bdeaeb579`
- package revision digest: `sha256:fe02377b3c8e4cad94ee25883e90c68fb8083c15e18938f495c115d6ed1514ad`

## V5 optional-extension decisions

The port uses no quota and no feature-demonstration filler.

For every one of the ten activities:
- `hints`: NONE;
- `media`: NONE;
- `references`: NONE;
- activity revision rotation due to the V5 port: NO.

This is an explicit per-activity author decision, not an omission. Existing teaching/reveal/feedback and the exact historical source basis are sufficient; decorative media, redundant hints and unnecessary external dependencies are not introduced.

Decision evidence:
- `V5_PORT_DECISIONS.json`: `37b1014b4e86bf606fdb5fa8ec35738364ffeeb1`

## Source and Factory pre-review binding

Learner brief and Role B source remain byte-identical:
- learner brief blob: `6c4fb770f12690a3cb338c82fc77bf9b323c3b06`
- brief SHA-256: `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`
- Role B source blob: `7f83784e8719917496a694b2ad170d724190fd04`
- Role B source bytes: `12384`
- Role B source SHA-256: `sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`
- sourceSetDigest: `sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`
- Factory contextDigest: `sha256:32fd5f9afcc0dd9466c50afb961614f442969d7681036e12a98b1ee59dece739`

Role A learner references:
- required URLs: NONE;
- admission records: NONE;
- empty-set admission: PASS.

Author-side evidence:
- canonical V5 validation: PASS;
- V5 authoring policy: PASS;
- hint count: 0;
- pedagogical quality: EXCELLENT_BY_PROFILE;
- Role B exact local-source governance: PASS;
- historical V4 semantic review reused: NO;
- final V5 Factory gate: PENDING independent V5 semantic review.

Exact evidence blobs:
- `V5_VALIDATION_REPORT.json`: `415b96e3602e1d42490c82f9ed53459de9fea994`
- `V5_AUTHORING_POLICY_REPORT.json`: `90a1d5c4f388e198bf4e8e98290cd5de55bf5acc`
- `V5_PEDAGOGICAL_QUALITY_REPORT.json`: `d2f774031da1b24d95b8b8d5e575c222d29b4249`
- `FACTORY_CONTEXT_V5.json`: `3f6a1cec5444121c8fe742d515b400780046557c`
- `V5_PRE_REVIEW_EVIDENCE.json`: `40765b9b4944e71cc8b72e2e53f9abb8e2cc528a`
- `PROVENANCE_MAP_V5.json`: `7a4b6802ff94aded62d44da47c9a2d4c319718e0`
- `ROLE_B_SOURCE_MANIFEST_V5.json`: `74e16e07e9e5978b7b5f3ce81befa4c0650bf925`
- author audit: `9c07b13ff2df63da9cc95e39b9c8923567fead08`
- independent-review request: `76f8c296be4937d71a39c56d2233b40cd729d2fc`

## Product / runtime qualification

No product/runtime/contract/authoring implementation source is changed by Handoff 5.

A prior diagnostic correctly observed that the legacy optional Atlas surface still has a qcm/fill-only compatibility gate. That observation does not block this exact no-hints Handoff-5 candidate: the qualified Learn-it product path is wired to the Handoff-4 V8 presenters.

Exact carrier:
- head: `9d3029a36475d77600d107469cfdad51ddf1364c`
- workflow run: `36137427599`
- job: `108078765157`
- conclusion: **SUCCESS**

Carrier evidence:
- `OVERALL PASS`
- `V5_IMPORT: PASS`
- `CORE_10_ACTIVITY_CORRECT_RESPONSE: PASS`
- `RELOAD_RESUME: PASS`
- `SCORING_AUTHORITY: PASS`
- `V8_EXACT_10_ACTIVITY_RENDER_RESPONSE: PASS`
- `ACTIVITY_RESPONSE_UNCHANGED: PASS`
- `UPSTREAM_PRODUCT_MUTATION: NONE`
- `CLASSIC_V8_PATH_REFUTES_ATLAS_SURFACE_ONLY_BLOCKER: PASS`
- V5 validator regressions: 11 tests — PASS
- V4 validator regressions: 8 tests — PASS
- V5 Factory/source-governance regressions: 20 tests — PASS
- `V8_SELECTED_PRESENTERS_BROWSER: PASS`
- `V8_VIEWPORTS_DESKTOP_390_320: PASS`
- `V8_KEYBOARD_POINTER_TOUCH: PASS`
- `V8_ORDER_NUMERIC_GEOMETRY: PASS`
- `V8_REDUCED_MOTION_OVERFLOW: PASS`
- `REFERENCES_RUNTIME_FETCH: NONE`
- repository validation in carrier: `REPOSITORY VALIDATION OK`

Product build remains byte-identical to qualified Handoff 4:
- bytes: `518513`
- SHA-256: `978caf5b1905a65d669bee5b369f228a5254b878e4a26e48d001441b648586f0`

## Causal freeze

Carrier-to-RESULT tree delta is exactly removal of:
- `.github/workflows/atlas-wp059-transient-blocker-qualification.yml`

No other file changes between carrier head `9d3029a36475d77600d107469cfdad51ddf1364c` and functional RESULT_SHA `1f67cae285f9afc0425734329608623894b88831`.

Repository governance on exact functional RESULT_SHA:
- run: `36137568357`
- conclusion: **SUCCESS**

## Functional RESULT scope

Relative to exact Handoff-4 parent, RESULT_SHA changes exactly:
- `apps/learnit-next/tests/v5_showcase_port_r1.py`
- `docs/programs/student-v0.1/STUDENT_V0_1_LIMITED_PILOT_ACTIVITY_PROFILE_V5.md`
- `showcase/student-v0.1/nombres-complexes/AUTHOR_AUDIT_V5.md`
- `showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT_V5.json`
- `showcase/student-v0.1/nombres-complexes/FACTORY_REVIEW_REQUEST_V5.md`
- `showcase/student-v0.1/nombres-complexes/PROVENANCE_MAP_V5.json`
- `showcase/student-v0.1/nombres-complexes/ROLE_B_SOURCE_MANIFEST_V5.json`
- `showcase/student-v0.1/nombres-complexes/V5_AUTHORING_POLICY_REPORT.json`
- `showcase/student-v0.1/nombres-complexes/V5_PEDAGOGICAL_QUALITY_REPORT.json`
- `showcase/student-v0.1/nombres-complexes/V5_PORT_DECISIONS.json`
- `showcase/student-v0.1/nombres-complexes/V5_PRE_REVIEW_EVIDENCE.json`
- `showcase/student-v0.1/nombres-complexes/V5_VALIDATION_REPORT.json`
- `showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v5.json`
- `work-packages/ATLAS-WP-059.json`

Forbidden implementation changes:
- `apps/learnit-next/src/**`: NONE
- `contracts/**`: NONE
- `authoring/**`: NONE
- `labs/**`: NONE
- `pilot/**`: NONE
- `qa/**`: NONE
- `governance/**`: NONE

PR #449 remains **DRAFT / OPEN / UNMERGED**.

## Semantic-review firewall

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_V5_REVIEW`

This Handoff-5 author session does not:
- reuse the historical V4 semantic-review PASS;
- produce `PASS_SEMANTIC_REVIEW_V5_R2`;
- produce `PASS_AI_KIT_FACTORY_V5_R2`;
- execute Handoff 6;
- execute fan-in;
- execute ATLAS-WP-054;
- merge or cherry-pick;
- promote;
- start a student session.

## Final adversarial audit

1. Exact Handoff-4 parent preserved? **PASS.**
2. Historical JOB10C exact 10 activities / 39 minutes preserved? **PASS.**
3. Activity lineage IDs and order preserved? **PASS.**
4. Course/activity revision IDs and digests gratuitously rotated? **NO — PASS.**
5. Constructed activity resurrected? **NO — PASS.**
6. `acceptedResponses` workaround introduced? **NO — PASS.**
7. Hints/media/references added merely to exercise V5? **NO — PASS.**
8. Learner brief changed? **NO — PASS.**
9. Role B source set expanded or changed? **NO — PASS.**
10. Role A external dependency introduced? **NO — PASS.**
11. Canonical V5 validator accepts persisted exact candidate? **YES — PASS.**
12. Authoring policy passes? **YES — PASS.**
13. Pedagogical quality remains EXCELLENT_BY_PROFILE? **YES — PASS.**
14. Role B exact source governance passes? **YES — PASS.**
15. Full ten-activity product path imports and scores correctly? **YES — PASS.**
16. Reload/resume survives mid-course? **YES — PASS.**
17. Exact ten activities render/respond through selected V8 presenters? **YES — PASS.**
18. Reference render/open causes runtime fetch? **NO — PASS.**
19. Product/runtime/contract/authoring implementation changed? **NO — PASS.**
20. Historical V4 semantic review reused? **NO — PASS.**
21. Final V5 Factory PASS manufactured in author session? **NO — PASS.**
22. ATLAS-WP-054 unblocked? **NO — PASS.**
23. PR remains DRAFT / OPEN / UNMERGED? **YES — PASS.**
24. Repository governance passes on exact functional RESULT_SHA? **YES — PASS.**

## Verdict

`PASS_READY_FOR_R2_HANDOFF_6`

Next:
`R2_HANDOFF_6_INDEPENDENT_V5_SEMANTIC_REVIEW`

This evidence records Handoff 5 only. Handoff 6 is not executed here.
