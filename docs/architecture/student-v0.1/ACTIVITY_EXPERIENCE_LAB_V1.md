# Activity Experience Lab V1 — V3 Human Feedback Rework

Status: Phase-A prototype laboratory, human decision still required.

## Frozen boundary

The Lab consumes learner-safe `ActivityPresentation` fixtures and emits only the frozen Student V0.1 `ActivityResponse` grammar. Production `apps/learnit-next/src/**` remains read-only. The Lab contains no answer keys, correctness evaluator, scoring, mastery, progress, session authority, persistence, plugin registry, dynamic loader or production imports.

## V3 interaction design

Stable baseline variants remain available. Candidate B variants are intentionally materially different rather than cosmetic:

- `flashcard-b`: two-sided card; revealed side repeats the original question above the answer.
- `matching-b`: source cards disappear from the source pool and snap into persistent paired rows directly opposite their target descriptions.
- `order-b`: no ordinal numbers and no visible move arrows; the whole row is the pointer drag surface, with a subtle grip affordance. Rows reflow immediately as the dragged row crosses insertion positions. Keyboard lift/move/drop semantics preserve accessibility.
- `classify-b`: source cards physically move from `À classer` into category buckets, which fill as classification progresses. Cards can move between buckets or back to source.
- `fill-b`: token chips physically move from a bank into visible sentence slots while emitting the same canonical slot mapping as `fill-a`.

QCM A is retained with corrected left alignment and robust text wrapping.

## Touch and accessibility

Drag candidates use Pointer Events (`pointerdown`, `pointermove`, `pointerup`, pointer capture), never HTML5 Drag and Drop. Cards are the full touch target; grips are visual affordances only. Tap/keyboard fallbacks are provided. Layout is audited at 390 px and long-label stress is part of the browser test. Reduced-motion behavior is retained.

## Verification

`test_lab.py` verifies variant coverage, secret-free fixtures, static/network-free constraints, Pointer Event usage and required V3 structures.

`browser_smoke.py` uses mobile Chromium touch input to prove causally that:

- Matching B moves cards into paired-row DOM slots and shrinks the source pool;
- Order B changes DOM order during pointer movement before pointer-up;
- Classify B moves cards into bucket DOM containers and between buckets;
- Fill B moves token chips into slots and emits canonical slot mapping;
- long labels remain contained without horizontal overflow at 390 px;
- keyboard/tap fallback and reduced-motion paths remain available.

Human physical-device review remains the final Phase-A gate.
