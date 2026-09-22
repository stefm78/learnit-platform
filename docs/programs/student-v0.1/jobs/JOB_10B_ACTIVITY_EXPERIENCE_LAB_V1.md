# /AUDIT /SOLVE /BUILD — JOB 10B
## Student V0.1 — Activity Experience Lab V1

Repository: `stefm78/learnit-platform`  
Issue: `#434`  
Coordinator: `#431 / ATLAS-WP-050`  
Work package: `ATLAS-WP-052`

Branch:

`student-v01/g5-r1-activity-experience-lab`

Exact common base:

`18b925436777943b19c4b031c24659ad60dee133`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge or cherry-pick anything.

## Mission

Build a standalone fail-fast Activity Experience Lab around the frozen Student V0.1 boundary:

```text
ActivityPresentation
        ↓
prototype interaction
        ↓
ActivityResponse
```

The Lab is not production Learn-it.

It must let a human judge activity interaction quality in minutes, before any selected prototype is integrated into production.

## Frozen contract authority

Fresh-read and verify exact blobs:

- `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
  - blob `cf15b12e0d008484b8341a8a059fe0d91955f8b0`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
  - blob `c900d96c3845276e23b77a43c970c7c3834655a5`
- production `activity_projection.js`
  - blob `607ecea8af6dc468ded05dbcc924693f90d576ff`
- production `activity_presenters.js`
  - read-only blob `fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

Frozen response grammars:

- lesson -> `{acknowledged:true}`
- flashcard -> `{revealed:true}`
- qcm -> `{choiceId}`
- fill -> canonical slot mapping
- matching -> `{associations:[{leftItemId,rightItemId}]}`
- order -> `{orderedItemIds:[...]}`
- classify -> `{assignments:[{itemId,bucketId}]}`

Constructed is not part of this first-pilot Lab.

If contract authority drifts, stop:
`HOLD_STUDENT_V01_ACTIVITY_LAB_AUTHORITY_DRIFT`.

## Absolute boundary

The Lab may:
- render;
- animate;
- manage local interaction state;
- emit ActivityResponse;
- expose the emitted response in a reviewer/developer inspector.

The Lab may not:
- know correct answers;
- evaluate correctness;
- know mastery;
- know session/course progress;
- persist learner progress;
- import product session/evaluator code;
- use a plugin registry, dynamic loader, event bus or evaluator framework.

Production `apps/learnit-next/src/**` is read-only.

## Lab location

Create the isolated sub-product under:

`labs/student-v0.1/activity-experience/**`

Create architecture note:

`docs/architecture/student-v0.1/ACTIVITY_EXPERIENCE_LAB_V1.md`

Keep it deterministic, static/local and network-free.

## Learner-safe fixtures

Create ActivityPresentation-only fixtures for:

- lesson
- flashcard
- matching
- order
- classify
- qcm
- fill

Fixtures must match frozen shapes.

Fail closed if any fixture contains hidden scoring authority, including:
- `correctChoiceId`
- fill answer keys
- `acceptedResponses`
- authored `matches`
- `correctOrder`
- authored classify solution assignments.

Use neutral synthetic content where necessary. The Lab evaluates interaction design, not mathematical content correctness.

## Required prototypes

### Lesson
At least one simplified candidate:
- clean reading hierarchy;
- exactly one Continue;
- emits `{acknowledged:true}`.

### Flashcard
At least two meaningfully different candidates.

Every candidate must:
- show front first;
- require explicit reveal;
- show back/explanation only after reveal;
- expose exactly one continuation after reveal;
- emit `{revealed:true}`;
- never use control-state clutter such as `Réponse affichée` or `Prêt à continuer`.

One variant may use a richer flip/card transition if:
- reduced-motion works;
- semantics remain explicit;
- animation is not required for comprehension.

### Matching
At least two candidates:
1. click/select association;
2. richer spatial or drag-enhanced association.

Both must:
- support full keyboard operation;
- work on touch;
- emit exact associations;
- not reveal correctness.

### Order
At least two candidates:
1. explicit move-up/down controls;
2. richer drag/reorder enhancement.

Both emit exact `orderedItemIds`.

### Classify
At least two candidates:
1. select item then choose bucket;
2. richer spatial/drag-to-bucket enhancement.

Both emit exact assignments.

### QCM and fill
Provide polished baseline renderings.

Do not invent a new response grammar.

## Prototype IDs

Assign stable deterministic variant IDs, for example:

- `lesson-a`
- `flashcard-a`, `flashcard-b`
- `matching-a`, `matching-b`
- `order-a`, `order-b`
- `classify-a`, `classify-b`
- `qcm-a`
- `fill-a`

Use IDs consistently in the UI, test evidence and human form.

## Response inspector

Provide a clearly separated reviewer/developer panel showing the exact emitted ActivityResponse.

It must:
- never display correctness;
- never display hidden source answers;
- make response-shape comparison easy.

The learner prototype itself must remain understandable even if the inspector is visually ignored.

## Accessibility and interaction quality

For every candidate:
- keyboard path;
- visible focus;
- no keyboard trap;
- semantic labels;
- touch-safe controls;
- responsive layout;
- no horizontal overflow at about 390px;
- reduced-motion support where animated;
- screen-reader smoke.

Drag-enhanced variants require non-drag fallback.

## Automated Lab tests

Require deterministic tests for:
- fixture schema/secret scan;
- exact response shapes;
- response emitted only after valid interaction state;
- flashcard reveal before continue;
- matching/order/classify keyboard operations;
- mobile layout;
- reduced motion;
- no external network;
- deterministic static build/archive;
- production source unchanged.

## Human fail-fast review bundle

Produce a deterministic downloadable ZIP outside Git with:
- Lab static artifact;
- local README/start instructions;
- exact bundle identity file;
- variant manifest;
- human review form.

For each family/variant, the human review should answer:

1. **30 seconds:** sans explication, comprends-tu quoi faire ?
2. **2 minutes:** l’interaction est-elle agréable et faible friction ?
3. **≤10 minutes:** clavier/mobile/accessibilité restent-ils cohérents ?

Human selection form:

```text
ACTIVITY_LAB_HUMAN_SELECTION
LAB_REVIEW_BUNDLE_SHA256: <exact hash>
REVIEW_COMPLETED: YES
LESSON_VARIANT: <variant-id>|REJECT_ALL
FLASHCARD_VARIANT: <variant-id>|REJECT_ALL
MATCHING_VARIANT: <variant-id>|REJECT_ALL
ORDER_VARIANT: <variant-id>|REJECT_ALL
CLASSIFY_VARIANT: <variant-id>|REJECT_ALL
QCM_BASELINE: ACCEPT|REJECT
FILL_BASELINE: ACCEPT|REJECT
NOTES: NONE|<text>
FINAL_DECISION: ACCEPT_SELECTION|HOLD
```

Do not infer selection from casual comments.

## Phase A result

Freeze the tested Lab as:

`LAB_RESULT_SHA`

Then add only:
`qualification/STUDENT_V01_ACTIVITY_LAB_V1_RESULT.md`

as evidence if needed, while preserving a clear result/evidence split.

Return exactly:

```text
STUDENT_V01_ACTIVITY_LAB_PHASE_A
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
LAB_RESULT_SHA: <sha>
LAB_EVIDENCE_HEAD: <sha>
ISSUE: 434
PR: <pr>
LAB_REVIEW_BUNDLE_SHA256: <sha>
LAB_REVIEW_BUNDLE_BYTES: <int>
LAB_CONTRACT_BOUNDARY: PASS|FAIL
LAB_SECRET_BOUNDARY: PASS|FAIL
LAB_RESPONSE_SHAPES: PASS|FAIL
LAB_VARIANT_COVERAGE: PASS|FAIL
LAB_BROWSER_ACCESSIBILITY: PASS|FAIL
LAB_NETWORK_FREE: PASS|FAIL
PRODUCTION_SOURCE_UNCHANGED: PASS|FAIL
REPOSITORY_GOVERNANCE: PASS|FAIL
SCOPE: PASS|FAIL
HUMAN_PROTOTYPE_DECISION: REQUIRED
FINAL_VERDICT: READY_STUDENT_V01_ACTIVITY_LAB_FOR_HUMAN_PROTOTYPE_REVIEW|HOLD_STUDENT_V01_ACTIVITY_LAB_NEEDS_REWORK|FAIL_STUDENT_V01_ACTIVITY_LAB_SCOPE_VIOLATION
```

Also provide the downloadable Lab review bundle.

Then stop.

## Phase B

Resume only after the exact human selection block with matching bundle hash.

If valid:
- create only `qualification/STUDENT_V01_ACTIVITY_LAB_SELECTION.md`;
- record selected/rejected variant IDs;
- preserve human notes;
- commit selection alone as `LAB_SELECTION_SHA`;
- do not change Lab implementation;
- do not change production presenters.

Return:

```text
STUDENT_V01_ACTIVITY_LAB_SELECTION_RESULT
LAB_RESULT_SHA: <sha>
LAB_REVIEW_BUNDLE_SHA256: <sha>
LAB_SELECTION_SHA: <sha>
LESSON_VARIANT: <id>
FLASHCARD_VARIANT: <id>
MATCHING_VARIANT: <id>
ORDER_VARIANT: <id>
CLASSIFY_VARIANT: <id>
QCM_BASELINE: ACCEPT
FILL_BASELINE: ACCEPT
PRODUCTION_IMPLEMENTATION: DEFERRED_TO_ATLAS_WP_054
FINAL_VERDICT: PASS_STUDENT_V01_ACTIVITY_LAB_SELECTION_FROZEN|HOLD_STUDENT_V01_ACTIVITY_LAB_SELECTION
```

A PASS authorizes only later ATLAS-WP-054 implementation/integration.
