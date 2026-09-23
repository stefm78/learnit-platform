# Activity Experience Lab V1

Status: Phase-A prototype laboratory — V2 touch repair.

## Boundary

The Lab consumes learner-safe `ActivityPresentation` fixtures and emits only the frozen `ActivityResponse` grammar. It contains no answer keys, correctness evaluator, scoring, mastery/progress/session authority, persistence, plugin registry, dynamic loader, event bus or production imports.

Production `apps/learnit-next/src/**` remains read-only. The implementation lives entirely under `labs/student-v0.1/activity-experience/**`.

## Variant design

Stable IDs remain: `lesson-a`, `flashcard-a`, `flashcard-b`, `matching-a`, `matching-b`, `order-a`, `order-b`, `classify-a`, `classify-b`, `qcm-a`, `fill-a`.

A and B variants are intentionally discriminating rather than cosmetic:
- flashcard A = direct reveal; B = explicit two-sided card;
- matching A = select left then right; B = spatial cards dropped onto large targets;
- order A = explicit up/down controls; B = direct tactile reorder with a visible handle;
- classify A = per-item category menus; B = cards moved into large category zones.

B drag mechanics use Pointer Events (`pointerdown` / `pointermove` / `pointerup`) so the same causal interaction works with mouse, pen and touch. HTML5 `draggable` is not used. Drag is progressive enhancement: matching/classify retain select-then-target fallback and order retains arrow controls. Motion is optional and disabled under reduced-motion preferences.

## Verification

`test_lab.py` checks learner-safe fixtures, family/variant coverage, no HTML5 drag usage, Pointer Event implementation, network-free/static behavior and mobile/reduced-motion affordances.

`browser_smoke.py` executes every variant at 390px and adds causal touch-drag probes for matching B, order B and classify B using browser touch input. It also verifies that A/B DOM interaction structures are materially different, exact response shapes remain frozen, keyboard fallbacks work, reduced-motion works and no external request occurs.

## Human gate

Phase A stops after a deterministic external review package is produced. No variant is selected or integrated into production until an explicit human selection block with the exact current bundle SHA-256 is returned.
