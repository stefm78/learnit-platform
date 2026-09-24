# Activity Experience Lab V4 — Interaction Stabilization

Status: Phase-A isolated prototype candidate; human review required.

## Boundary

The Lab consumes learner-safe `ActivityPresentation` fixtures and emits only the frozen Student V0.1 `ActivityResponse` grammar. Production presenter/projection files remain read-only. The Lab contains no answer key, correctness evaluator, scoring, mastery, progress, session authority, persistence or external network dependency.

## V4 interaction invariants

- `CLICK_CARD != MOVE_CARD`
- `CLICK_TOKEN != MOVE_TOKEN`
- `BUBBLING_CANNOT_CAUSE_MUTATION`
- `DRAG_OR_EXPLICIT_FALLBACK_REQUIRED_FOR_MOVE`
- `ONE_ATTEMPT_ONE_STABLE_RANDOM_ORDER`
- `NEW_ATTEMPT_MAY_HAVE_NEW_RANDOM_ORDER`
- `POINTER_DRAG_IS_NOT_HTML5_DRAG_DROP`
- `ACTIVITY_RESPONSE_GRAMMAR_UNCHANGED`

## Randomization

Each render starts one in-memory attempt seed. QCM choices, matching source/targets, order items, classify source cards and fill tokens/options are shuffled once from that seed. Category order and sentence slot order remain stable. No interaction re-shuffles an active attempt. A deterministic test seed hook exists only for audit/replay and has no authority or persistence semantics.

## Order B

Order B was rebuilt after physical Android review refuted the previous simulated PASS. Pointer-down creates a floating visual ghost while the original card becomes a low-opacity insertion gap. During pointer movement the original card is reinserted in DOM order as the pointer crosses sibling centers, so surrounding cards reflow before pointer-up. Drop removes the ghost and exposes the current gap as the committed item. Keyboard lift/move/drop remains available without visible arrow controls.

## Classify B and Fill B

Card/token click handlers only select and stop propagation. Buckets and slots are not implicit mutation controls. A dedicated movement panel provides the non-drag fallback. Drag remains the primary tactile path.

Classify cards physically move among source and bucket containers; multiple cards can coexist in a bucket.

Fill slots show a dashed affordance only while empty. Once occupied, the slot shell loses its border/background and the token itself becomes the visible inline answer. Explicit drag or explicit movement controls may replace a filled slot, returning the displaced token to the bank.

## Verification

Static tests prohibit HTML5 drag-and-drop, persistence/network APIs and hidden scoring authority.

Mobile Chromium tests at 390x844 challenge:
- verso text alignment;
- deterministic/random seed behavior;
- Order B ghost-follow + pre-drop DOM reflow;
- negative repeated-click sequences for Classify B and Fill B;
- explicit drag/fallback movement;
- occupied-slot visual simplification;
- frozen response grammar;
- long-label overflow;
- reduced motion;
- external request/browser error absence.

Physical Android review remains the final Phase-A human gate.
