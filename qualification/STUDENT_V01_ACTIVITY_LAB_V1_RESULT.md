# Student V0.1 — Activity Experience Lab V2 Touch — Phase A Result

Status: **READY FOR HUMAN PROTOTYPE REVIEW**

## Authority

- common base: `18b925436777943b19c4b031c24659ad60dee133`
- issue: `#434`
- draft PR: `#437`
- branch: `student-v01/g5-r1-activity-experience-lab`
- canonical job blob: `9867580c41fa72eeb7cade20a20060906810ee4d`
- work-package blob: `a863c67a575cb84c80ec128f66fb81bd5c05064d`

Frozen contract authority revalidated:

- `WAVE1_INTERFACE_FREEZE.md`: `cf15b12e0d008484b8341a8a059fe0d91955f8b0`
- `STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`: `c900d96c3845276e23b77a43c970c7c3834655a5`
- production `activity_projection.js`: `607ecea8af6dc468ded05dbcc924693f90d576ff`
- production `activity_presenters.js`: `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

## Superseded result

The earlier Phase-A implementation `f9a16fa8f9b66aa4fc08a663a78b8ed259c9d224` and its review packages are superseded for human prototype selection because empirical mobile review showed insufficient A/B differentiation and non-functional HTML5 drag interaction on Android.

No human selection was recorded against the superseded package.

## Frozen V2 result

`LAB_RESULT_SHA`: `bba621e92dc7c7ad7ffe6674a4be27c89f525b38`

The V2 implementation preserves the frozen `ActivityPresentation -> ActivityResponse` boundary and changes only the isolated Lab and its tests/documentation.

### Discriminating B variants

- `flashcard-b`: explicit two-sided recto/verso card, distinct from direct reveal A.
- `matching-b`: physical cards moved into large spatial targets.
- `order-b`: tactile reorder list with explicit drag handle and insertion target.
- `classify-b`: physical cards moved into large category zones.

Matching/order/classify B use Pointer Events (`pointerdown`, `pointermove`, `pointerup`, pointer capture), not HTML5 drag-and-drop. Each drag-enhanced variant retains a tap/keyboard-safe fallback.

Frozen response grammars remain unchanged:

- lesson -> `{acknowledged:true}`
- flashcard -> `{revealed:true}`
- qcm -> `{choiceId}`
- fill -> canonical slot mapping
- matching -> `{associations:[{leftItemId,rightItemId}]}`
- order -> `{orderedItemIds:[...]}`
- classify -> `{assignments:[{itemId,bucketId}]}`

## Audit evidence

Static tests:

- fixture schema / scoring-secret scan: PASS
- 11 stable variants and required family coverage: PASS
- Pointer Event implementation present: PASS
- HTML5 drag-and-drop absent from V2 overlay: PASS
- no external network API / persistence / evaluator authority: PASS
- distinct B rendering paths and CSS structures: PASS

Browser/mobile touch audit at 390x844:

- A/B structural differentiation: PASS
- exact frozen response shapes: PASS
- Matching B causal touch drag for all cards: PASS
- Order B causal touch reorder changes list order: PASS
- Classify B causal touch drag for all cards: PASS
- matching/classify tap-keyboard fallback: PASS
- order keyboard fallback: PASS
- no horizontal overflow: PASS
- reduced-motion flashcard B: PASS
- browser errors: NONE
- external requests: NONE

The causal touch tests use Chromium mobile/touch emulation with browser touch input. Physical-device human review remains the required gate.

Production and authority audit:

- production `activity_projection.js` unchanged: PASS
- production `activity_presenters.js` unchanged: PASS
- frozen interface and architecture blobs unchanged: PASS
- changed-path scope relative to exact common base: PASS
- PR remains DRAFT / OPEN / UNMERGED: PASS
- Repository governance on LAB_RESULT_SHA: PASS, run `35838097402`

## Human review package

Current package:

- filename: `STUDENT_V01_ACTIVITY_LAB_V2_TOUCH_HUMAN_REVIEW.zip`
- SHA-256: `2a41db5d356288b0efb0421b3e0ae4e909111aa0213e759bf8f504c1ac96b1a5`
- bytes: `27566`
- deterministic rebuild: PASS (two independent byte-identical archives)

Portable Android entry:

- filename: `ACTIVITY_LAB_V2_TOUCH_ANDROID.html`
- package entry: `00_OPEN_ME_ACTIVITY_LAB_V2_TOUCH.html`
- SHA-256: `e8a4c4c03f4319a70b399a14223b2b6e56707228e6fe92a5c46c130423317c6b`
- bytes: `30871`
- self-contained CSS/data/JavaScript: PASS
- portable bootstrap: PASS
- portable 11/11 variants: PASS
- portable Matching B touch drag: PASS
- portable Order B touch reorder: PASS
- portable Classify B touch drag: PASS
- portable fallback paths: PASS
- portable external requests: NONE
- portable browser errors: NONE

## Gate

`HUMAN_PROTOTYPE_DECISION: REQUIRED`

No prototype selection is inferred. Phase B remains blocked until the exact completed human selection block is returned with the current ZIP SHA-256.
