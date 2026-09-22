# Activity Experience Lab V1

Status: Phase-A prototype laboratory only.

## Boundary

The Lab consumes learner-safe `ActivityPresentation` fixtures and emits only the frozen `ActivityResponse` grammar. It contains no answer keys, correctness evaluator, scoring, mastery/progress/session authority, persistence, plugin registry, dynamic loader, event bus or production imports.

Production `apps/learnit-next/src/**` remains read-only. The implementation lives entirely under `labs/student-v0.1/activity-experience/**`.

## Variants

Stable IDs: `lesson-a`, `flashcard-a`, `flashcard-b`, `matching-a`, `matching-b`, `order-a`, `order-b`, `classify-a`, `classify-b`, `qcm-a`, `fill-a`. Drag-enhanced variants retain button/select fallbacks. Motion is optional and disabled under reduced-motion preferences.

## Verification

`test_lab.py` checks learner-safe fixtures, family/variant coverage, network-free/static behavior and mobile/reduced-motion affordances. `browser_smoke.py` executes every variant in headless Chromium at 390px, exercises keyboard focus and response emission, checks reduced-motion and rejects external requests.

## Human gate

Phase A stops after a deterministic external review ZIP is produced. No variant is selected or integrated into production until an explicit human selection block with the exact bundle SHA-256 is returned.
