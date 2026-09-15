# Student V0.1 — Wave 1 Handoff

Status: **PREPARED / BLOCKED UNTIL G0 HUMAN ACCEPTANCE AND ARCHITECTURE MERGE**

Shared read-only authority:
- `contracts/learnit-kit-v4.schema.json`
- `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
- `docs/programs/student-v0.1/PROGRAM_CHARTER.md`

## JOB 01 — Learning/runtime

Own: explicit v2/v3/v4 admission, evaluation/non-evaluated completion semantics,
session orchestration, learner-safe projection, progress/evidence and own tests.

Must not edit UI rendering/styles, authoring/factory, v4 schema, build manifest or
central workflows.

## JOB 02 — Activity presentation/UI

Own: learner-safe rendering and response collection for all admitted types,
accessible interaction mechanics, embedded media rendering/sanitization boundary
and own tests.

Must not own correctness/scoring, Learning/session semantics, authoring/factory,
v4 schema, build manifest or workflows.

## JOB 03 — Authoring/Factory/quality

Own: v4 validator tooling, authoring skill, Factory support, pedagogical-quality
checks, authoring preview where justified and own tests.

Must not edit learner runtime/UI, v4 schema, build manifest or workflows.

## JOB 04 — fan-in A

Alone owns integration-only files: deterministic build routing, source-manifest
rebinding, central CI/workflow routing and integration provenance.

## Stop conditions

Return to architecture if a role requires changing v4, if two roles require the
same writable product path, if presentation needs scoring secrets, if media needs
network dependency, or if lesson/flashcard completion contaminates validation or
mastery evidence.
