# Student V0.1 — Wave 1 Interface Freeze

Status: **EXECUTION AUTHORITY AFTER ARC-WP-025 G0 ACCEPTANCE**

Common base before this launch package: `0d1e400d95a371898e79335501d5f989677bdb0e`.

This file freezes only the interfaces that must be shared by the three Wave 1 workers. It does not implement product code.

## 1. Canonical contract authority

All Wave 1 roles read, but never modify:

- `contracts/learnit-kit-v4.schema.json`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `docs/programs/student-v0.1/PROGRAM_CHARTER.md`

Published meanings remain explicit:

- v2 = qcm/fill;
- v3 = qcm/fill/constructed;
- v4 = qcm/fill/constructed + lesson/flashcard/matching/order/classify + bounded media.

No automatic migration or rewrite is authorized.

## 2. Learner-safe ActivityPresentation shapes

The projection owned by Learning/session must remove all scoring secrets before data reaches UI.

Common optional field on every presentation: `media[]`, already resolved to learner-visible embedded assets.

### qcm

```json
{"type":"qcm","prompt":"...","choices":[{"choiceId":"...","label":"..."}],"media":[]}
```

Forbidden: `correctChoiceId`.

### fill

```json
{"type":"fill","prompt":"...","tokens":[{"tokenId":"...","label":"..."}],"segments":[{"text":"..."},{"slotId":"..."}],"media":[]}
```

Forbidden: authored `answers`.

### constructed

```json
{"type":"constructed","prompt":"...","media":[]}
```

Forbidden: `acceptedResponses`, scoring rule internals or reference answers.

### lesson

```json
{"type":"lesson","title":"...","body":"...","keyPoints":["..."],"contextNote":"...","media":[]}
```

`contextNote` and `keyPoints` may be absent. Lesson is non-scored.

### flashcard

```json
{"type":"flashcard","front":"...","back":"...","explanation":"...","media":[]}
```

`back`/`explanation` are learner-visible reveal content, not scoring secrets. Flashcard is non-scored and the presenter hides the back until reveal.

### matching

```json
{"type":"matching","prompt":"...","leftItems":[{"itemId":"...","label":"..."}],"rightItems":[{"itemId":"...","label":"..."}],"media":[]}
```

Forbidden: `matches`.

Learning projection must ensure that if the authored left/right positional order exactly exposes the solution, the learner-safe right-item order is deterministically rotated before presentation. The UI must render the two sides as independent pools, never as pre-paired rows.

### order

```json
{"type":"order","prompt":"...","items":[{"itemId":"...","label":"..."}],"media":[]}
```

Forbidden: `correctOrder`.

The canonical kit `items[]` order is the initial learner-visible order. Authoring validation must reject an `items[]` ID sequence identical to `correctOrder` so the solution is not revealed by construction.

### classify

```json
{"type":"classify","prompt":"...","buckets":[{"bucketId":"...","label":"..."}],"items":[{"itemId":"...","label":"..."}],"media":[]}
```

Forbidden: authored `assignments`.

Student V0.1 is single-label classification only: exactly one expected bucket per item.

## 3. ActivityResponse shapes

UI returns data only; it never evaluates correctness.

```text
qcm        -> {choiceId}
fill       -> existing canonical slot mapping
constructed-> {text}
lesson     -> {acknowledged:true}
flashcard  -> {revealed:true}
matching   -> {associations:[{leftItemId,rightItemId}]}
order      -> {orderedItemIds:[...]}
classify   -> {assignments:[{itemId,bucketId}]}
```

## 4. Evaluation / completion semantics

- qcm/fill preserve current behavior.
- constructed preserves v3 `canonical-text-match-v1` semantics.
- matching is correct only when the submitted complete one-to-one association set equals the authored hidden match set.
- order is correct only when the submitted complete ID sequence equals `correctOrder`.
- classify is correct only when every item is assigned exactly once and the complete item→bucket mapping equals the authored hidden assignment set.
- lesson and flashcard have **no correctness result**. Their response advances the active session only. They must not create success/failure, validation, mastery, transfer or spaced-review evidence.

Prefer existing session-state persistence for lesson/flashcard completion. Do not introduce a new learner persistence schema solely to count exposure.

## 5. Media projection

Initial v4 media is embedded/local only. Learner-safe resolved media shape:

```json
{
  "assetId":"...",
  "format":"svg|png|jpeg|webp",
  "alt":"...",
  "caption":"...",
  "pedagogicalRole":"...",
  "data":"...",
  "placement":"prompt|content|feedback",
  "display":"contained|full_width",
  "zoomable":false
}
```

Optional fields may be absent. No remote URL exists in the first slice.

Runtime/import and authoring validators must fail closed on unsafe SVG. UI rendering must also sanitize/fail closed defensively. No script, `foreignObject`, iframe, event attribute, external href, external `url()`, or active content is allowed.

## 6. Parallel ownership

JOB 01 owns Learning/runtime semantics and learner-safe projection.

JOB 02 owns UI rendering, interaction mechanics and response extraction from the frozen presentation shapes above.

JOB 03 owns authoring validation, Factory/quality and generation guidance against the frozen canonical v4 schema.

No role may change this file or `learnit-kit-v4.schema.json`. Any interface defect is returned to the Control Room as `ARCHITECTURE_REOPEN_REQUIRED`.

Integration-only files such as `apps/learnit-next/source_manifest.json` and central workflows remain JOB 04 ownership.