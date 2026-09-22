# Student V0.1 — G5 human findings R1 / corrective decomposition

Status: engineering findings and corrective architecture only.  
Formal G5 decision: NOT RECORDED.  
G5 remains: PENDING_HUMAN.

## Exact replay/candidate context

- G4 candidate RESULT_SHA: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`
- G4 evidence head / corrective base: `18b925436777943b19c4b031c24659ad60dee133`
- G5 replay-prep SHA: `a72897c209b8ea7bd8672cc8a95be939ecee6fb8`
- Phase-A replay bundle SHA-256: `fc06e745405cb1ba48674bcf93478e9ccbc44d766bee4bd4174a3aab3b00ce66`

## Human-observed defects

1. After import, the application can show a misleading “Aucun parcours Atlas installé” state while the imported rich V4 course is visible below.
2. During an active journey, verbose objective progress/recommendation content dominates the screen before the actual activity.
3. The earlier per-objective visual reservoir/bucket model is no longer the primary readable progress signal.
4. Lesson/flashcard controls expose confusing duplicated states/actions such as “Réponse affichée”, “Prêt à continuer” and another “Continuer”.
5. Learner-facing showcase copy leaks internal authoring/program language such as “de la source”, “Student V0.1 Showcase” and “kit canonique Atlas M1 0.3”.
6. Constructed free-text scoring is brittle for mathematically equivalent keyboard typography. The current global rule is intentionally bounded text matching, not mathematical equivalence.

## Audit result: three distinct problem classes

### A — App Experience

Owns the application shell and journey context:
- truthful post-import state;
- library/navigation hierarchy;
- global progress;
- objective progress;
- resume/recovery clarity.

This is not the same problem as the look & feel of an individual activity.

### B — Activity Experience

The frozen Student V0.1 architecture already defines a useful product boundary:

`ActivityPresentation -> presenter -> ActivityResponse`

The presenter owns interaction mechanics only. It does not own correctness, scoring, mastery or hidden solutions.

This boundary is strong enough to support a standalone **Activity Experience Lab** that can prototype richer interactions without rebuilding the full application or changing Learning semantics.

The lab should be a fail-fast development sub-product:
- input: learner-safe ActivityPresentation fixtures;
- output: exact ActivityResponse;
- no scoring secrets;
- no correctness evaluation;
- no session/progress state;
- no plugin runtime;
- multiple prototype variants;
- human selection before production integration.

### C — Pilot Activity Policy

The constructed family is supported by learnit.kit.v4, but the first limited Student V0.1 pilot does not need to exercise every supported family.

For the limited pilot profile:
- admit lesson, flashcard, matching, order, classify, qcm, fill;
- exclude constructed free text.

This avoids pretending that a bounded exact-text scorer solves mathematical semantic equivalence.

The existing showcase constructed practice at activity index 4 is not required to preserve the two course objectives because conjugate practice/transfer/validation remain covered by other activities. Removing its 3 minutes changes the course from 42 to 39 minutes, still within the intended 30–45 minute window.

## Architectural boundary preserved

This corrective decomposition does not change:
- learnit.kit.v4 schema or published meaning;
- ActivityPresentation shapes;
- ActivityResponse shapes;
- canonical-text-match-v1;
- runtime support for constructed outside the limited-pilot profile.

## Superseded preparation

Issue #429 / PR #430 / ATLAS-WP-046 were prepared but not executed.

They are superseded because their two-track split mixed activity experience with product repair and attempted to retain constructed in the pilot through authored answer variants.

The R1 plan uses three streams and a human prototype gate before activity UX is integrated.
