# Student V0.1 — Activity Experience Lab V4 — Interaction Stabilization — Phase A Result

Status: **READY FOR PHYSICAL ANDROID HUMAN REVIEW**

## Authority

- common base: `18b925436777943b19c4b031c24659ad60dee133`
- issue: `#434`
- draft PR: `#437`
- branch: `student-v01/g5-r1-activity-experience-lab`
- canonical JOB 10B blob: `9867580c41fa72eeb7cade20a20060906810ee4d`
- work-package blob: `a863c67a575cb84c80ec128f66fb81bd5c05064d`

Frozen authority revalidated:

- `WAVE1_INTERFACE_FREEZE.md`: `cf15b12e0d008484b8341a8a059fe0d91955f8b0`
- `STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`: `c900d96c3845276e23b77a43c970c7c3834655a5`
- production `activity_projection.js`: `607ecea8af6dc468ded05dbcc924693f90d576ff`
- production `activity_presenters.js`: `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

## Refined V4 execution prompt

The latest physical-device review feedback was converted into a bounded V4 stabilization prompt before implementation.

- filename: `ACTIVITY_LAB_V4_INTERACTION_STABILIZATION_EXECUTION_PROMPT.md`
- SHA-256: `95ce56b185a175a490304dec2f879dd58c263d63a0c7013472f83911db78a923`
- bytes: `8536`

The prompt treats the previous physical Android Order-B failure as contradictory evidence, requires negative click oracles for Classify B and Fill B, requires occupied Fill-B slots to lose the redundant dashed shell, requires one stable randomized order per attempt, and preserves the frozen ActivityPresentation → ActivityResponse boundary.

## Superseded result

The V3 result `02b14abac3a5682fb5319711e5448f740b22f775` is superseded for the next human review.

The V3 automated Order-B PASS is explicitly not treated as physical-device proof because subsequent Android review refuted it.

## Frozen V4 result

`LAB_RESULT_SHA`: `91c217b4b9a1d5ba4b19c8e3b12e7da901ac6d25`

V4 remains isolated to the Lab, the allowed architecture note and deterministic tests. Production presentation/projection files were not changed.

### Implemented stabilization

- **Flashcard B**: the repeated question, answer and explanation use one left-aligned reading axis on the verso. The card remains reversible.
- **Matching B**: persistent visual pairs are retained; source and target choices are independently randomized once per attempt.
- **Order B**: rebuilt around a floating visual ghost plus a moving insertion gap. The whole card is the tactile surface. The original DOM row moves during pointer movement, before pointer-up, so surrounding cards reflow immediately. No visible ordinal numbers or move arrows are present. Keyboard lift/move/drop remains available.
- **Classify B**: clicking a card only selects it and stops propagation. Buckets are not implicit mutation controls. Movement happens only by pointer drag or a dedicated explicit movement panel. Multiple cards may coexist in a bucket and cards may move between source/buckets.
- **QCM A**: radio and text remain left aligned; long labels wrap safely.
- **Fill B**: clicking a token only selects it and stops propagation. Slots are not implicit mutation controls. Movement happens only by pointer drag or the explicit movement panel. Occupied slots remove their dashed border/background so the token itself becomes the inline answer. Tokens use the same squarer visual grammar as Classify cards.
- **Randomization**: QCM choices, Matching source/targets, Order initial items, Classify source cards and Fill tokens/options are shuffled once from an in-memory attempt seed. The order is stable during an attempt and may differ on the next attempt. Category order and sentence-slot order remain stable. No persisted state or authority is introduced.

## Automated audit

Static audit:

- fixture schema / scoring-secret scan: PASS
- 12 required variants: PASS
- Pointer Events implementation: PASS
- HTML5 drag-and-drop dependency: ABSENT
- persistence / external network / evaluator authority: ABSENT
- required V4 structural markers: PASS

Mobile Chromium audit at 390×844:

- Flashcard B verso text alignment: PASS
- same deterministic audit seed => same order: PASS
- different audit seed => different randomized order: PASS
- interaction during an attempt does not reshuffle: PASS
- Matching B causal touch drag and persistent pairs: PASS
- Order B floating ghost follows the touch point: PASS
- Order B DOM order changes during pointer movement before pointer-up: PASS
- Order B insertion-gap/sibling reflow: PASS
- Order B keyboard lift/move/drop fallback: PASS
- Classify B repeated source-card clicks produce zero movement: PASS
- Classify B clicks on already placed cards produce zero movement: PASS
- Classify B explicit fallback movement: PASS
- Classify B causal drag movement: PASS
- Fill B repeated token clicks produce zero movement: PASS
- Fill B clicks on already placed tokens produce zero movement: PASS
- Fill B occupied slot has no dashed border: PASS
- Fill B explicit fallback movement: PASS
- Fill B explicit drag replacement returns the displaced token to the bank: PASS
- frozen ActivityResponse grammars: PASS
- long-label overflow at 390px: PASS
- reduced-motion behavior: PASS
- external requests: NONE
- browser errors: NONE

Package verification:

- source static audit rerun from source tree: PASS
- source mobile browser audit rerun from source tree: PASS
- ZIP extracted source static audit: PASS
- ZIP extracted source mobile browser audit: PASS
- portable HTML bytes equal ZIP portable entry: PASS
- standalone portable Android audit: PASS

The automated browser audit is causal mobile/touch simulation. It does **not** substitute for the physical Android review that previously exposed a false-positive Order-B result.

## Repository audit

- exact common-base merge base: PASS
- V4 Git objects reread byte-exact by Git blob SHA: PASS
- obsolete split V3 candidate files removed from V4 result tree: PASS
- production `activity_projection.js` unchanged: PASS
- production `activity_presenters.js` unchanged: PASS
- frozen interface and richness architecture blobs unchanged: PASS
- changed-path scope: PASS
- PR remains DRAFT / OPEN / UNMERGED: PASS
- Repository governance on LAB_RESULT_SHA: PASS, run `35971965711`

## Human review package

Current deterministic review archive:

- filename: `STUDENT_V01_ACTIVITY_LAB_V4_HUMAN_REVIEW.zip`
- SHA-256: `54bb023430d333c298e422cf32d8f12dfe4251d18ee7b8a422b49d4b05cc0c6f`
- bytes: `37193`
- deterministic rebuild: PASS (three byte-identical archive builds)

Portable Android entry:

- filename: `ACTIVITY_LAB_V4_INTERACTION_STABILIZED_ANDROID.html`
- archive entry: `00_OPEN_ME_ACTIVITY_LAB_V4.html`
- SHA-256: `74b251bd072603025cf7af7ee5ee2a532faa68af14eed5dc0917559d85a542cd`
- bytes: `39833`
- self-contained CSS/data/JavaScript: PASS
- external stylesheet/script dependency: NONE
- standalone mobile interaction audit: PASS

A human-selection template was generated with the exact current ZIP SHA-256. It contains no inferred decision.

## Gate

`HUMAN_PROTOTYPE_DECISION: REQUIRED`

The user's comments are treated as repair requirements, not as a formal Phase-B selection. Phase B remains blocked until the exact V4 package is physically reviewed and an explicit completed human selection/authorization is returned.
