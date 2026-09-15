# /AUDIT /SOLVE /BUILD — JOB 02
## Student V0.1 — Activity presentation/UI

You are an independent Wave 1 implementation worker.

Do not inspect or depend on JOB 01/JOB 03 branches. Your input is the frozen shared architecture/interface on main only.

Repository: `stefm78/learnit-platform`
Authority issue: `#384`
Work package: `ATLAS-WP-028`
Pre-created branch: `student-v01/wave1-presentation-ui`

## 0. Reconstruct exact authority

Before editing:

1. fresh-read current control-plane/kernel authority required by the installed bootstrap;
2. fresh-read repository `main`;
3. verify main contains merged ARC-WP-025, v4 and the Wave 1 launch package;
4. verify your branch started from the exact same common Wave 1 launch base and contains no product change from another role;
5. bind that exact commit into `ATLAS-WP-028.baseline.requiredCommonWave1Base`.

Read as normative:
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `docs/programs/student-v0.1/WAVE1_INTERFACE_FREEZE.md`
- `docs/programs/student-v0.1/WAVE1_HANDOFF.md`
- `work-packages/ATLAS-WP-028.json`

Read current qcm/fill presentation code and historical RC718 matching/order/flashcard/media only as implementation evidence. Do not import RC718 storage, identity or runtime architecture.

## 1. Mission

Implement the learner-facing presentation layer for the frozen learner-safe ActivityPresentation shapes.

You own:
- DOM rendering;
- accessible interaction mechanics;
- response extraction;
- visual states;
- embedded media rendering/sanitization defense;
- UI/browser tests.

You do **not** own canonical activity semantics, correctness, hidden solutions, session/progress logic, authoring/Factory, contracts, workflows or source-manifest fan-in.

## 2. Presenter architecture

Multiple genuinely different interactions now justify a small internal typed presentation seam, but **not** a generic plugin framework.

Prefer a bounded structure such as:

```text
renderActivityPresentation(presentation)
readActivityResponse(container, presentation)
```

with type-specific helpers in a static module. No dynamic registry, remote loading, event bus or evaluator callbacks.

Keep current qcm/fill visible semantics regression-safe.

## 3. Required presenters

Implement the frozen shapes exactly from `WAVE1_INTERFACE_FREEZE.md`.

### lesson
Readable learning card with:
- title;
- body;
- optional key points;
- optional contextual/historical note;
- optional media;
- explicit Continue action producing `{acknowledged:true}`.

Do not display it as a quiz and do not invent a correct/incorrect state.

### flashcard
- show front first;
- explicit reveal action exposes back + explanation;
- only after reveal may the learner continue;
- response `{revealed:true}`;
- no self-grade buttons in Student V0.1 unless separately authorized.

### matching
Associate left/right items. Must remain usable without drag-and-drop.

Minimum accessible interaction:
- select a left item;
- select a right item;
- create/change association;
- visible association state;
- keyboard-operable controls;
- touch-safe targets.

Return `{associations:[{leftItemId,rightItemId}]}`. Never infer correctness in UI.

### order
Allow learner to produce one ordered ID sequence without requiring drag-and-drop.

Provide keyboard/touch-safe move-up/move-down controls; drag-and-drop may be added only as progressive enhancement if it does not become the sole interaction.

Return `{orderedItemIds:[...]}`.

### classify
Show explicit buckets and unclassified items. Support assigning/reassigning one item to one bucket with keyboard/touch-safe controls.

Return `{assignments:[{itemId,bucketId}]}`.

### constructed
Render bounded textarea; reject blank input locally as a response-shape check only. Do not score. Return `{text}`.

### qcm / fill
Preserve existing behavior and response grammars.

## 4. Secret boundary

The UI must neither require nor accept these fields:

- `correctChoiceId`;
- fill `answers`;
- `acceptedResponses`;
- matching `matches`;
- `correctOrder`;
- classify `assignments` as authored truth.

Add static/adversarial tests that fail if rendering/evaluation code starts depending on them.

If a required UI behavior appears impossible without a scoring secret, stop with `ARCHITECTURE_REOPEN_REQUIRED`; do not pull secret data into UI.

## 5. Media

Render only the frozen embedded learner-safe media shape.

- SVG / PNG / JPEG / WebP only;
- honor alt text;
- caption when provided;
- contained/full-width presentation;
- zoom only when explicitly allowed and accessibly operable;
- no network fetch.

SVG must fail closed if active/unsafe constructs are found. Defend again in UI even if runtime/import is expected to validate.

Do not use `innerHTML` on untrusted SVG or learner-visible text unless a dedicated sanitizer proves the exact safe allowlist. Prefer DOM construction and safe image/blob/data handling.

## 6. UX quality floor

Student V0.1 is meant to be shown to real students. The UI must therefore be more than technically functional.

Check:
- mobile width;
- touch target size;
- keyboard navigation;
- visible focus;
- no horizontal overflow in ordinary cases;
- readable hierarchy;
- clear difference between learning content, interaction and feedback;
- no premature answer reveal;
- reasonable density for 30–45 minute use.

Do not redesign the entire application shell; stay within the activity surface.

## 7. Write boundary

Change only paths authorized by `ATLAS-WP-028.json`.

Do not edit:
- `contracts/**`;
- `apps/learnit-next/src/core/**`;
- `apps/learnit-next/src/integration/**`;
- `authoring/**`;
- `.github/**`;
- `apps/learnit-next/source_manifest.json`.

JOB 04 owns integration-only files.

## 8. Qualification

At minimum prove:
- qcm/fill visible regression;
- lesson complete flow;
- flashcard reveal flow;
- matching association/create/change and response extraction;
- order move/reorder and response extraction;
- classify assign/reassign and response extraction;
- constructed nonblank response extraction;
- no secret-field dependency;
- unsafe SVG/media rejection;
- keyboard operation for matching/order/classify;
- mobile/touch-friendly controls at browser level.

Use deterministic browser tests where existing project tooling supports them. Do not modify Learning code to make UI tests pass.

## 9. PR / handoff

Use the pre-created branch and its existing draft PR if present. Do not merge.

Return exactly one verdict:

`PASS_STUDENT_V01_JOB02_PRESENTATION_READY_FOR_FANIN_A`

`HOLD_STUDENT_V01_JOB02_PRESENTATION_NEEDS_REWORK`

`FAIL_STUDENT_V01_JOB02_SECRET_OR_ACCESSIBILITY_BOUNDARY`

Final block:

```text
STUDENT_V01_JOB02_RESULT
BASE_SHA: <exact common Wave1 base>
RESULT_SHA: <exact head>
ISSUE: 384
PR: <number>
QCM_FILL_REGRESSION: <PASS|FAIL>
LESSON_FLASHCARD: <PASS|FAIL>
MATCHING: <PASS|FAIL>
ORDER: <PASS|FAIL>
CLASSIFY: <PASS|FAIL>
CONSTRUCTED: <PASS|FAIL>
MEDIA: <PASS|FAIL>
SECRET_BOUNDARY: <PASS|FAIL>
ACCESSIBILITY_SMOKE: <PASS|FAIL>
SCOPE: <PASS|FAIL>
FINAL_VERDICT: <exact token>
```
