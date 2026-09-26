# Student V0.1 — V8 Selected Presenters R1 Qualification Result

## Binding

- Work package: `ATLAS-WP-058`
- Issue: #446
- Draft PR: #447
- Branch: `student-v01/r2-v8-selected-presenters-r1`
- Human R2 decision: issue #431 comment `5817817692` — `GO_PRE_PILOT_V5`
- Qualified Handoff-3 parent: `student-v01/r2-v5-runtime-atlas-projection-r1@1bd57ee49f39ebc993af6198d24ebd54cd0ddbab`
- Handoff-3 RESULT_SHA: `f1254562247a2ee54d5a5329b953fafc22eb8fd3`
- V7 selection authority: PR #437 / `577aa6cde9dfc58663a4935545e48bf8953c902b`
- V7 selection blob: `947d0b20fbae356c47acd560fab584f9d4aa5199`
- V7 LAB_RESULT_SHA: `13d44db96e3d526ddb7e3ae90bde488fd16af9a3`
- Functional RESULT_SHA: `3e44a1d4d74456dc7d2d74b62b151c016cdd85df`

## Selected production baseline

The exact human-selected variants remain frozen and are materially implemented:
- Flashcard B — PASS
- Matching B — PASS
- Order B — PASS
- Classify B — PASS
- QCM A — PASS
- Fill B — PASS
- Lesson A — PASS

No A/B choice was reopened. PR #437 was used only as the exact behavior/geometry oracle and was neither merged nor cherry-picked.

## V7 mechanics and response boundary

- frozen ActivityResponse grammar — PASS
- common selection / explicit-destination / no-selection-reflow invariant — PASS
- click/tap/keyboard and Pointer Events convergence — PASS
- Order B exact placeholder dimensions within 1 CSS px — PASS
- Order B stable list height / fixed-X ghost / strict-Y drag — PASS
- pointer-cancel exact restoration and no residual inline drag styles — PASS
- QCM long-label radio/text alignment — PASS
- Flashcard B reversible common reading axis — PASS
- Lesson A simple reading/acknowledgement — PASS
- per-attempt presentation-only randomization — PASS
- no persisted random authority — PASS

Exact selected V7 Lab reproduction on `577aa6cde9dfc58663a4935545e48bf8953c902b`:
- `STATIC_LAB_V7_TESTS: PASS`
- `STATIC_LAB_V7_GEOMETRY_INVARIANTS: PASS`
- `BROWSER_LAB_V7_DESTINATION_FEEDBACK_AUDIT: PASS`
- `PRODUCTION_AUDIT_V7: PASS`
- `ADVERSARIAL_PRODUCTION_GEOMETRY_AUDIT_V7: PASS`

## V5 presentation capabilities

### Hints
- initial learner projection remains free of unrevealed hint text — PASS
- fake generic hint guidance removed — PASS
- hint control exists only for qualified authored V5 hint capability — PASS
- Handoff-3 `requestNextAtlasV5Hint` / `reconstructAtlasHintPrefix` remain the sole persistence/reconstruction authority — PASS
- presenter creates no assistance ledger — PASS
- committed/resumed hint display remains outside geometry-critical boards — PASS

### Media
- prompt/content media render only from initial learner-safe presentation — PASS
- feedback media remains excluded from initial presentation — PASS
- feedback media projection requires `transitionAuthorized: true` and renders only in the post-answer transition — PASS
- existing defensive embedded-media validation remains unchanged — PASS
- media failure is accessible and non-scoring — PASS
- remote media fallback — NONE

### References
- disclosure closed by default and secondary to the activity — PASS
- learner labels `Pour aller plus loin` / `Références` — PASS
- render/open disclosure runtime fetch — NONE
- external-link visual indicator — PASS
- accessible new-tab announcement — PASS
- `target="_blank"` with `rel="noopener noreferrer"` — PASS

## Causal qualification

Transient qualification carrier:
- carrier head: `401d7bcd235c941728f821c56e3f4398e5cb5c1c`
- workflow run: `36108728377`
- job: `107987103667`
- conclusion: **SUCCESS**

Carrier-to-RESULT tree delta is exactly removal of:
`.github/workflows/atlas-wp-058-v8-selected-presenters.yml`

Therefore the qualified product/test/source-manifest tree is byte-identical between carrier and RESULT_SHA.

Carrier evidence:
- `V8_SELECTED_PRESENTERS_BROWSER: PASS`
- `V8_VIEWPORTS_DESKTOP_390_320: PASS`
- `V8_KEYBOARD_POINTER_TOUCH: PASS`
- `V8_ORDER_NUMERIC_GEOMETRY: PASS`
- `V8_REDUCED_MOTION_OVERFLOW: PASS`
- `REFERENCES_RUNTIME_FETCH: NONE`
- V7 exact Lab reproduction — PASS
- Handoff-3 causal regression with intentional presenter supersession sentinel — PASS
- frozen V5/V4/Factory regressions — PASS
- historical Student V0.1 runtime and Atlas regressions — PASS
- deterministic build — PASS
- detached Stream 10A compatibility probe — PASS

Deterministic build:
- bytes: `518513`
- SHA-256: `978caf5b1905a65d669bee5b369f228a5254b878e4a26e48d001441b648586f0`

Detached Stream 10A probe:
- exact accepted evidence head: `f26216cc28fee9a2f5a55b90e68959d53963663f`
- `FALSE_EMPTY_STATE_BROWSER=PASS`
- `ACTIVITY_PRIMARY_BROWSER=PASS`
- `PROGRESSIVE_DISCLOSURE_BROWSER=PASS`
- `DESKTOP_MOBILE_LAYOUT=PASS`
- `STREAM_10A_COMPATIBILITY_PROBE=PASS`
- durable fan-in created — NONE
- PR #436 cherry-pick/merge — NONE

## Frozen authority identities

Handoff-4 leaves these exact authorities unchanged:
- V5 schema: `15e708f9b57ea1b35ff50ad3b3854bd49d5cadc7`
- V5 validator: `0b93925eb22058878f13bc86554126846d2923d1`
- V5 validator tests: `61cc3f77e5efb89d350fb4569808f58fd3ecd912`
- V4 schema: `e141bd5fafa75dda88a49e8a2094e4589bb4306e`
- V4 validator: `4ef561dfc1137aa436b4d8c8820db421ab6e1861`
- V4 validator tests: `85debca78c3ec342d9e4e7ed63a033fd0968e72e`
- activity semantics/scoring authority: `07c4595332419da1da0473a9715f09894620f6bd`
- Atlas IndexedDB: `c8b6f27326ba6aa4b7caf16ab6ef178f0812312f`
- Atlas storage port: `8def176ac7b96748a2384af97f23183016a4a4be`
- Atlas UI session: `712c378a8e7675b6656c84efb6ba23a866fc5292`
- defensive media renderer: `1c84d5da04025cf372e3496fb7d25c088d1a0650`
- Handoff-3 activity projection: `06025e76b6b60d1dc3bee3af43e661689da99d08`

## Scope

Parent Handoff-3 to RESULT_SHA changes exactly:
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/src/integration/atlas/session.js`
- `apps/learnit-next/src/main.js`
- `apps/learnit-next/src/styles.css`
- `apps/learnit-next/src/ui/activity_presenters.js`
- `apps/learnit-next/src/ui/render.js`
- `apps/learnit-next/tests/v8_selected_presenters_harness.html`
- `apps/learnit-next/tests/v8_selected_presenters_r1.py`
- `docs/architecture/student-v0.1/LEARNIT_KIT_V8_SELECTED_PRESENTERS.md`
- `work-packages/ATLAS-WP-058.json`

No core, contract, authoring, Atlas-storage, Lab, showcase, pilot, QA or governance payload is changed by RESULT_SHA.

## Repository governance

Exact RESULT_SHA:
- run: `36109010441`
- conclusion: **SUCCESS**

PR #447 remains **DRAFT / OPEN / UNMERGED**.

## Final adversarial audit

1. Exact V7 human selection still authority? **YES — PASS.**
2. Any A/B choice reopened? **NO — PASS.**
3. Any Lab commit cherry-picked/merged? **NO — PASS.**
4. Any 10A commit cherry-picked/merged? **NO — PASS.**
5. All seven selected presenters materially implemented? **YES — PASS.**
6. Frozen response grammars unchanged? **YES — PASS.**
7. Selected V7 geometry invariants preserved? **YES — PASS.**
8. Every drag behavior backed by non-drag equivalent? **YES — PASS.**
9. Randomization presentation-only/non-authoritative? **YES — PASS.**
10. Initial V5 DOM/presentation contains unrevealed hint? **NO — PASS.**
11. Can V8 reveal a hint without Handoff-3 committed evidence? **NO — PASS.**
12. Can hint UI create a second assistance ledger? **NO — PASS.**
13. Prompt/content and feedback media lifecycle-separated? **YES — PASS.**
14. Can feedback media enter initial DOM? **NO — PASS.**
15. References collapsed/secondary? **YES — PASS.**
16. Rendering/opening references performs network fetch? **NO — PASS.**
17. External links accessibly indicated? **YES — PASS.**
18. Can references/media/hints alter ActivityResponse or scoring? **NO — PASS.**
19. Activity-first hierarchy compatible with accepted 10A? **YES — PASS.**
20. Handoff-3 runtime regressions PASS? **YES — PASS.**
21. V2/V3/V4 regressions PASS? **YES — PASS.**
22. ATLAS-WP-054 still blocked? **YES — PASS.**
23. PR DRAFT / OPEN / UNMERGED? **YES — PASS.**
24. Repository governance PASS on exact RESULT_SHA? **YES — PASS.**

## Verdict

`PASS_READY_FOR_R2_HANDOFF_5`

Next:
`R2_HANDOFF_5_EXACT_10C_SHOWCASE_V5_PORT_REQUALIFICATION`

This evidence records Handoff 4 only. Handoff 5 is not executed here.
