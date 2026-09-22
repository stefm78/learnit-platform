# Student V0.1 — Activity Experience Lab V1 — Phase A Result

Status: **READY FOR HUMAN PROTOTYPE REVIEW**

## Authority

- common base: `18b925436777943b19c4b031c24659ad60dee133`
- issue: `#434`
- draft PR: `#437`
- preparation head: `e6c8f9b06a21a1e0359ae0322b390ee66196b77a`
- canonical job blob: `9867580c41fa72eeb7cade20a20060906810ee4d`
- work-package blob: `a863c67a575cb84c80ec128f66fb81bd5c05064d`

Frozen contract blobs revalidated before build:

- `WAVE1_INTERFACE_FREEZE.md`: `cf15b12e0d008484b8341a8a059fe0d91955f8b0`
- `STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`: `c900d96c3845276e23b77a43c970c7c3834655a5`
- `activity_projection.js`: `607ecea8af6dc468ded05dbcc924693f90d576ff`
- `activity_presenters.js`: `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

## Frozen Lab result

`LAB_RESULT_SHA`: `f9a16fa8f9b66aa4fc08a663a78b8ed259c9d224`

The Lab is isolated under `labs/student-v0.1/activity-experience/**`, plus the allowed architecture note. It consumes learner-safe `ActivityPresentation` fixtures and emits only frozen `ActivityResponse` objects. No production presenter/source file was modified.

Stable variants:

- `lesson-a`
- `flashcard-a`, `flashcard-b`
- `matching-a`, `matching-b`
- `order-a`, `order-b`
- `classify-a`, `classify-b`
- `qcm-a`
- `fill-a`

## Automated evidence

- fixture secret scan: PASS
- exact ActivityResponse shapes: PASS
- invalid/incomplete interaction does not emit for matching/classify/qcm/fill: PASS
- flashcard reveal required before continuation: PASS
- matching/order/classify keyboard path: PASS
- drag-enhanced variants retain non-drag fallback: PASS
- 390px mobile overflow smoke: PASS
- visible focus / labelled control smoke: PASS
- reduced-motion smoke: PASS
- external request observation: PASS (none observed)
- static source network dependency scan: PASS
- production source blobs unchanged: PASS
- deterministic review archive: PASS (two independent byte-identical builds)
- Repository governance on LAB_RESULT_SHA: PASS, run `35788331699`

## Human review bundle

- filename: `STUDENT_V01_ACTIVITY_LAB_V1_HUMAN_REVIEW.zip`
- SHA-256: `2a1dd2044194a52f05e663775304ad7582e955d5a908c2f2c202945b994de700`
- bytes: `9093`

The bundle contains the static Lab artifact, local start instructions, exact payload identity manifest, stable variant manifest and human review form.

## Gate

`HUMAN_PROTOTYPE_DECISION: REQUIRED`

No human prototype selection is inferred. Phase B is not authorized until the exact completed human selection block is returned with the matching bundle SHA-256.
