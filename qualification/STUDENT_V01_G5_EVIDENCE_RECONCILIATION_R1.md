# Student V0.1 — G5 Evidence Reconciliation R1

## Scope and authority

- JOB: `JOB_27_HR24_FORMAL_ACCEPTANCE_CLOSEOUT_G5_EVIDENCE_RECONCILIATION_R1`
- WORK_PACKAGE: `ATLAS-WP-069`
- EXECUTION_ISSUE: `#469`
- CANONICAL_G5_AUTHORITY: `#427`
- HISTORICAL_G5_WORK_PACKAGE: `ATLAS-WP-045`
- HISTORICAL_G5_PR: `#428`
- REVIEWED_PRODUCT_SHA: `8eceb94b8003adc539d34d2cfeeca62ff0c565a0`
- SOURCE_EVIDENCE_HEAD: `0a0251df5f085c203fd43456bad63af33bb1a9a7`
- JOB26_FORMAL_HUMAN_VALIDATION: `ACCEPTED`
- JOB26_HUMAN_GATE: `PASS`
- JOB26_FORMAL_VALIDATION_SHA: `eb46abc4910f70b68cb3c615c2522682bc7c9db1`
- REPLAY_TRANSPORT: `REUSE_JOB26_IMMUTABLE_HTTPS_REPLAY`
- REPLAY_URL: `https://stefm78.github.io/learnit-platform/human-replay/8eceb94b8003adc539d34d2cfeeca62ff0c565a0/`
- REPLAY_HTTPS_LIVE_SMOKE: `PASS`
- JOB26_BUILD_SHA256: `96531b5eba19056268b2c451a0518e36c129464085ba5fcc73a318e6569b7128`
- JOB26_BUILD_BYTES: `583482`
- V5_SHOWCASE_SHA256: `aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b`

The canonical Student V0.1 charter still requires `G5 human replay/student-readiness PASS` before the first 5–6 real student sessions. JOB27 does not redefine G5 and does not rewrite JOB09/WP045 history.

## Reconciliation rules applied

1. Human evidence is reused only when it is a real human observation on a materially relevant surface.
2. Machine assertions do not become human PASS, especially for keyboard-only, screen-reader, touch, journey-quality or pilot-confidence requirements.
3. Historical human evidence that predates a material change is not treated as current unless the affected dimension was explicitly revalidated afterward.
4. JOB26 formal acceptance is reused only for the bounded surfaces actually present in the JOB25/JOB26 replay checklists.
5. A bounded human smoke that covers only one sub-part of a broader G5 requirement is recorded as evidence, but does not satisfy the broader dimension by itself.

## Evidence lineage used

- `#427 / #428 / ATLAS-WP-045`: canonical G5 protocol and mandatory human-only dimensions.
- `#429`: initial real G5 replay human-observed defects on the earlier G4 candidate.
- `#431` comment `5816782770`: explicit human Activity Lab selection, selection SHA `577aa6cde9dfc58663a4935545e48bf8953c902b`.
- `#431` comment `5817817692`: human `GO_PRE_PILOT_V5`; explicitly not G5 final authorization.
- `#459`: later human replay verdict `HOLD_MAJOR_UX_FLOW`, followed by learner-journey corrective work.
- `#463`: later human-observed HR23 defects and bounded corrective authorization; exact corrected result remained pending human replay.
- `#465` comment `5876560493`: human `ACCEPTED_WITH_TWO_SECONDARY_CORRECTIONS`, all other HR24 replay points accepted/frozen, HR24-003 separate/read-only.
- JOB25 replay run `36450360911`: HR24 parent checklist on product `68a852f1...`; bounded navigation/import/rename/resume/non-regression checks.
- JOB26 replay run `36471437763`: exact final delta checklist on product `8eceb94b...`; search/menu plus bounded regression smoke.
- JOB26 formal acceptance recorded by JOB27 at commit `eb46abc4910f70b68cb3c615c2522682bc7c9db1`.
- Exact JOB26 machine qualification run `36471117708` and repository-governance run `36471117690` are reused only as machine evidence.

## Mandatory G5 matrix

| Dimension | Requirement | Strongest evidence pointer | Candidate/version observed | Human or machine | Survived later changes? | Disposition |
|---|---|---|---|---|---|---|
| `COLD_START_COMPREHENSION` | A human can start from a clean state without answer-guide priming and understand how to enter learning. | Historical JOB09 protocol + real G5 replay findings recorded in `#429`. | Historical G4 candidate `757ed15e...`; not exact JOB26. | Human historical | **No.** App shell, import/library, activity UX, V5/V8 and later HR waves materially changed the start experience. | `SUPERSEDED_BY_LATER_CHANGE` |
| `INFORMATION_DENSITY` | Human judgment that density/hierarchy is understandable across the current learner path. | `#429` human finding on dominating progress/recommendation UI; later `#459` `HOLD_MAJOR_UX_FLOW`; JOB25/26 bounded acceptance does not ask for end-to-end density judgment. | Earlier G4/R15/JOB21-era surfaces. | Human historical + machine current | **No.** Multiple later layout/library/feedback/summary changes are material. | `SUPERSEDED_BY_LATER_CHANGE` |
| `NAVIGATION_SEARCH_CLARITY` | Current Library search/navigation is understandable and usable on the exact candidate. | JOB25/JOB26 replay checklists; `#465` human acceptance provenance; JOB27 formal acceptance commit `eb46abc...`. | Exact JOB26 product `8eceb94b...`. | Human | **Yes.** This is the final changed surface and was the explicit subject of the final correction/replay. | `SATISFIED_BY_JOB26_FORMAL_VALIDATION` |
| `PEDAGOGICAL_FLOW` | Human judges the current learning sequence, next-action hierarchy and transitions coherent. | Initial G5 human findings `#429`; later human `HOLD_MAJOR_UX_FLOW` in `#459`; machine learner-journey/HR22/HR23 qualifications after repairs. | Human evidence predates final corrective chain. | Human historical + machine current | **No.** Learner-flow, feedback and terminal states changed materially afterward. | `SUPERSEDED_BY_LATER_CHANGE` |
| `OBJECTIVE_PROGRESS_CLARITY` | Human understands current per-objective progress/reservoir state and direct objective interaction. | Human-validated R15 reference carried by JOB21; human findings in `#429`; later HR22/HR23 changed selected/toggle behavior. Current machine evidence passes R15 regressions. | R15 reference and intermediate candidates, not exact final interaction. | Human historical + machine current | **No.** HR22/HR23 made material interaction/selected-state changes not followed by a specific final human objective-progress validation. | `SUPERSEDED_BY_LATER_CHANGE` |
| `INTERACTION_GESTURE_QUALITY` | Real human finds representative current activity interactions/gestures immediately understandable and usable. | `#431` human Activity Lab selection SHA `577aa6c...`; later V8 port; `#463` human finding required a new matching tap-destination affordance. | Selected V7 baseline, then materially extended/changed later. | Human historical + machine current | **No.** Matching/touch interaction changed after the frozen human selection. | `SUPERSEDED_BY_LATER_CHANGE` |
| `KEYBOARD_ACCESSIBILITY` | Real keyboard-only navigation through start/import and at least one scored activity, with focus/order/naming/trap judgment. | R15/HR22/HR23/HR24 automated browser/ARIA/focus evidence; JOB25/JOB26 bounded Enter/Escape/focus operations. | Exact current code has machine regression evidence; bounded human replay did not perform the canonical keyboard-only G5 path. | Machine plus bounded human control use | **Not sufficient.** | `MACHINE_ONLY_NOT_SUFFICIENT` |
| `SCREEN_READER_ACCESSIBILITY` | One real human screen-reader smoke (NVDA, VoiceOver or TalkBack) over start/import, activity, feedback and completion. | Current automated accessibility/ARIA regressions only; no durable real-human screen-reader result for the exact JOB26 candidate was found. | Exact current candidate machine evidence only. | Machine | **Not sufficient.** | `MACHINE_ONLY_NOT_SUFFICIENT` |
| `FEEDBACK_SCORING_TRUST` | Human intentionally experiences wrong/correct scored feedback and judges it understandable/trustworthy. | Initial G5 replay produced human scoring/interaction concerns in `#429`; HR22/HR23 later changed feedback presentation and session-end separation; machine regressions pass. | Earlier human candidate; later corrected candidates machine-qualified. | Human historical + machine current | **No.** Feedback presentation materially changed afterward and was not revalidated as a human trust judgment on exact JOB26. | `SUPERSEDED_BY_LATER_CHANGE` |
| `RECOVERY_RESUME_CLARITY` | Human understands cancel/invalid-import/reset recovery and resume after persisted progress. | JOB25 step 14 + JOB26 step 16 provide exact-current human reload/resume smoke; HR23 materially changed reset lifecycle; broader JOB09 recovery protocol was not rerun on final candidate. | Exact JOB26 for resume subset; HR23/current for recovery machine evidence. | Human subset + machine remainder | **Only resume subset.** Recovery side remains insufficiently human-validated after the reset change. | `MACHINE_ONLY_NOT_SUFFICIENT` |
| `MOBILE_TOUCH_USABILITY` | Real touch use over start/import, non-scored + scored interaction, feedback and resume; judge targets/scroll/gesture friction/density/overflow. | JOB25/JOB26 replay used mobile/touch 390×844 for drawer/search/rename/overflow; current full activity-touch path remains primarily machine-qualified. | Exact JOB26 for bounded shell subset. | Human subset + machine remainder | **Only bounded shell subset.** | `MACHINE_ONLY_NOT_SUFFICIENT` |
| `FULL_LEARNER_JOURNEY` | Human completes the current exact intended 30–45 minute learner journey. | Historical JOB09 real replay on earlier candidate; later `#459` human hold; current exact showcase is 10 activities / 39 minutes and machine-qualified. | Historical earlier candidate vs exact current V5/V8 candidate. | Human historical + machine current | **No.** Multiple material product/content/runtime/UI changes occurred after the historical full replay. | `SUPERSEDED_BY_LATER_CHANGE` |
| `OVERALL_LIMITED_PILOT_CONFIDENCE` | Explicit human confidence/decision on handing the exact current candidate to the first 5–6 student sessions. | Canonical JOB09 decision form requirement; all later records explicitly keep `GO_LIMITED_PILOT: NOT_DECLARED`; JOB26 formal acceptance explicitly does not grant it. | Exact current candidate has no such final human decision. | Human decision required | N/A | `NO_HUMAN_EVIDENCE` |
| `KNOWN_HR24_003_LIMITATION` | Preserve the known separate engine gap and obtain explicit human acceptance if proceeding to pilot with it. | JOB25/JOB26 replay checklists and results; formal JOB26 validation preserves it unresolved. | Exact JOB26. | Human aware + machine identity | **Yes as a known limitation, not as non-blocking acceptance.** | `KNOWN_LIMITATION_REQUIRES_EXPLICIT_PILOT_ACCEPTANCE` |

## Reconciliation outcome

- G5_EVIDENCE_COVERAGE: `PARTIAL`
- SATISFIED_DIMENSIONS: `NAVIGATION_SEARCH_CLARITY`
- KNOWN_LIMITATION: `KNOWN_HR24_003_LIMITATION`
- MATERIAL_BLOCKER: `NONE_ESTABLISHED_BY_CURRENT_EVIDENCE`
- JOB26_FULL_REPLAY_REQUIRED_AGAIN: `NO`
- PRODUCT_MUTATION_REQUIRED: `NO`
- WORKFLOW_MUTATION_REQUIRED: `NO`

### Missing / superseded human dimensions requiring only delta completion

1. `COLD_START_COMPREHENSION`
2. `INFORMATION_DENSITY`
3. `PEDAGOGICAL_FLOW`
4. `OBJECTIVE_PROGRESS_CLARITY`
5. `INTERACTION_GESTURE_QUALITY`
6. `KEYBOARD_ACCESSIBILITY`
7. `SCREEN_READER_ACCESSIBILITY`
8. `FEEDBACK_SCORING_TRUST`
9. `RECOVERY_RESUME_CLARITY`
10. `MOBILE_TOUCH_USABILITY`
11. `FULL_LEARNER_JOURNEY`
12. `OVERALL_LIMITED_PILOT_CONFIDENCE`

`NAVIGATION_SEARCH_CLARITY` must **not** be replayed as a required G5 delta dimension: it is satisfied by the exact JOB26 formal human validation. HR24-003 is not repaired; the eventual final pilot decision must explicitly accept or hold on that known limitation.

## Governed outcome

`G5_DELTA_HUMAN_REPLAY_REQUIRED`

The delta protocol is `qualification/STUDENT_V01_G5_DELTA_REPLAY_PROTOCOL_R1.md` and reuses the immutable JOB26 HTTPS replay. It is designed as one integrated replay pass so the twelve remaining human dimensions are observed without repeating JOB26 search/menu acceptance work.
