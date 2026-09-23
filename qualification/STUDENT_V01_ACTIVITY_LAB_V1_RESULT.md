# Student V0.1 — Activity Experience Lab V3 — Human Feedback Rework — Phase A Result

Status: **READY FOR HUMAN PROTOTYPE REVIEW**

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

## Refined execution prompt

The human mobile review feedback was converted into a bounded V3 execution prompt before implementation.

- external prompt filename: `ACTIVITY_LAB_V3_EXECUTION_PROMPT.md`
- SHA-256: `8c91b6138da269b2a4c769c9d3e064dfedbe0c4db54d0c1b0bcc399038bd2ceb`
- bytes: `6136`

The prompt preserves the frozen ActivityPresentation → ActivityResponse boundary, keeps production read-only, requires Pointer Events rather than HTML5 drag-and-drop, adds causal mobile-touch tests and long-label stress, and explicitly forbids inferring a Phase-B human selection.

## Superseded result

The V2 result `bba621e92dc7c7ad7ffe6674a4be27c89f525b38` and its review bundle are superseded for the next human review. No formal human selection was recorded for V2.

## Frozen V3 result

`LAB_RESULT_SHA`: `02b14abac3a5682fb5319711e5448f740b22f775`

V3 keeps the same authority boundary and modifies only the isolated Lab, its allowed architecture note, and deterministic tests.

### Implemented human feedback

- Lesson A retained as the simple accepted baseline.
- Flashcard B repeats the original question on the revealed side and remains reversible.
- Matching B uses persistent paired rows: the moved source card is physically placed opposite its target and the source pool shrinks.
- Order B removes visible ordinals and visible up/down arrows; the entire card is the pointer-drag surface, the grip is only a subtle affordance, and surrounding cards reflow during pointer movement before drop. Keyboard lift/move/drop remains available.
- Classify B moves the actual cards out of “À classer” and into the target buckets; cards can move between buckets or return to source; long labels wrap; mobile buckets stack below the source.
- QCM A keeps its simple baseline but aligns text directly after the radio control and wraps long labels robustly.
- Fill A remains available.
- Fill B adds draggable token chips into sentence slots while emitting the exact same canonical slot mapping grammar as Fill A; reassignment returns displaced tokens to the bank.

Stable variant count: **12**.

## Automated audit

Static audit:

- fixture schema / scoring-secret scan: PASS
- required variant set including `fill-b`: PASS
- Pointer Events implementation: PASS
- HTML5 drag-and-drop dependency: ABSENT
- external network / persistence / evaluator authority: ABSENT
- required V3 visual structures: PASS

Mobile Chromium audit at 390×844:

- A/B structural differentiation: PASS
- exact frozen response grammars: PASS
- Flashcard B question repeated on verso: PASS
- Matching B causal touch drag: PASS
- Matching B source pool shrinks and paired rows persist: PASS
- Matching B reassignment + keyboard fallback: PASS
- Order B whole-card causal touch drag: PASS
- Order B DOM reflow occurs during pointer movement before pointer-up: PASS
- Order B keyboard lift/move/drop fallback: PASS
- Classify B causal source→bucket movement: PASS
- Classify B inter-bucket movement and return-to-source: PASS
- Classify B keyboard/tap fallback: PASS
- Fill B causal token→slot movement: PASS
- Fill B token reassignment and fallback: PASS
- 390px horizontal overflow: NONE
- long-label stress for QCM / Classify / Matching: PASS
- reduced-motion Flashcard B: PASS
- external requests: NONE
- browser errors: NONE

The same static and browser audit scripts were re-run successfully from the extracted review bundle.

## Repository audit

- exact common-base merge base: PASS
- production `activity_projection.js` unchanged: PASS
- production `activity_presenters.js` unchanged: PASS
- frozen interface and richness architecture blobs unchanged: PASS
- V3 implementation files uploaded byte-exact by Git blob identity: PASS
- obsolete monolithic `lab.js` and V2 overlay `lab_v2_touch.js` removed from the V3 result tree: PASS
- changed-path scope: PASS
- PR remains DRAFT / OPEN / UNMERGED: PASS
- Repository governance on LAB_RESULT_SHA: PASS, run `35846902289`

## Human review package

Current deterministic review archive:

- filename: `STUDENT_V01_ACTIVITY_LAB_V3_HUMAN_REVIEW.zip`
- SHA-256: `abb55ecfda1e97cae5f722681b9bac07b6dcb4c147dc24f85bdff99bdf2a7b2c`
- bytes: `34471`
- deterministic rebuild: PASS (three byte-identical archive builds)

Portable Android entry:

- filename: `ACTIVITY_LAB_V3_HUMAN_FEEDBACK_ANDROID.html`
- archive entry: `00_OPEN_ME_ACTIVITY_LAB_V3.html`
- SHA-256: `999eeac9221dec8408a3a997fea1211a293f7b1756c26d6e9df9ad8b95ca0896`
- bytes: `37370`
- external stylesheet/script references: NONE
- standalone full mobile/touch audit: PASS

An external human-selection form is also generated with the exact current ZIP hash. It is a template only; it does not encode or infer a human decision.

## Gate

`HUMAN_PROTOTYPE_DECISION: REQUIRED`

The user's qualitative comments that motivated V3 are implementation feedback, not a formal Phase-B selection. Phase B remains blocked until an explicit completed selection block using the exact current bundle SHA-256 is returned.
