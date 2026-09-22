# Student V0.1 — Human replay findings 01

Status: engineering findings only.  
Formal G5 decision: NOT RECORDED.  
G5 remains: PENDING_HUMAN.

## Exact replay/candidate context

- G4 candidate RESULT_SHA: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`
- G4 evidence head: `18b925436777943b19c4b031c24659ad60dee133`
- G5 replay-prep SHA: `a72897c209b8ea7bd8672cc8a95be939ecee6fb8`
- Phase-A replay bundle SHA-256: `fc06e745405cb1ba48674bcf93478e9ccbc44d766bee4bd4174a3aab3b00ce66`
- Phase-A replay bundle bytes: `508231`

## Human-observed learner-facing problems

The human reviewer reported, during real use of the exact G5 replay:

1. Immediately after importing the course, the top surface says **“Aucun parcours Atlas installé”** while the course is visibly present in the library below.
2. During the learning journey, the large **“Progression par objectif”** and **“Prochaine action recommandée”** blocks appear before the actual learning content and visually dominate it.
3. The earlier visual progression model with per-objective filling reservoirs/buckets is no longer clearly available in the Student V0.1 journey. The reviewer wants a direct view of what is acquired/not acquired per objective.
4. Lesson/flashcard interaction is confusing because the UI exposes several competing states/actions such as **“Continuer”**, **“Prêt à continuer”**, **“Réponse affichée”**, then another **“Continuer”**.
5. Learner-facing copy says phrases such as **“de la source”** even though the learner has no concept of an authoring source. Internal labels such as **“Student V0.1 Showcase”** and **“kit canonique Atlas M1 0.3”** also leak into learner-facing package metadata/copy.
6. A learner free-text answer judged mathematically correct by the reviewer was marked incorrect. The exact showcase constructed activity accepts only one typography: `−1 + 4i`.

These observations are sufficient to authorize engineering correction work. They are not, by themselves, a completed canonical `G5_HUMAN_REVIEW` decision block.

## Code audit confirmation on exact G4 candidate

### Misleading Atlas empty state

`apps/learnit-next/src/integration/atlas/surface.js`
Git blob:
`aea13ae66fdeeddae6a32b46f8c53875f6a754ad`

The legacy Atlas surface accepts only qcm/fill activities with legacy Atlas metadata and renders **“Aucun parcours Atlas installé”** whenever no compatible legacy-planner course exists, even though the classic library can contain an imported rich V4 course.

### Progression before activity

`apps/learnit-next/src/ui/render.js`
Git blob:
`0fc4b5027c82d038f69d402f97f8d0e059c5401c`

`renderSessionSnapshot()` places the full objective-progress surface before `renderServedActivityForm()`.

### Existing reservoir/bucket visual model

`apps/learnit-next/src/main.js`
Git blob:
`828997da351fc63b72adacf61f330fe2fcdd8f31`

The code still contains `atlas-r13-reservoir` visual progress with states including not-started, training, review-needed, ready-for-validation and validated-recently. The legacy session-owned CSS also hides this old progress block during active session presentation.

The corrective product work should preserve the useful visual concept, not blindly reactivate the old planner.

### Duplicate lesson/flashcard state machine

`apps/learnit-next/src/ui/activity_presenters.js`
Git blob:
`fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

Lesson has a local Continue button that becomes **“Prêt à continuer”**.  
Flashcard has local **“Afficher la réponse”** and Continue, with states **“Réponse affichée”** and **“Prêt à continuer”**.

`apps/learnit-next/src/ui/render.js` also wraps lesson/flashcard in an outer form with another **“Continuer”** button.

### Constructed scoring semantics

`apps/learnit-next/src/core/activity_semantics.js`
Git blob:
`07c4595332419da1da0473a9715f09894620f6bd`

The global rule is intentionally bounded:
- Unicode NFC;
- trim;
- collapse whitespace;
- exact case-sensitive comparison against hidden acceptedResponses.

This corrective wave must not change that architecture.

### Showcase learner copy and answer set

`showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json`
Git blob:
`03ed1d5819911c23734980f89716f4ca18a6bca4`

Learner-facing/internal leakage includes:
- package title `Nombres complexes — Student V0.1 Showcase`;
- description mentioning `kit canonique Atlas M1 0.3`;
- flashcard explanation ending `de la source`;
- matching explanation ending `de la source`.

The single constructed activity:
- prompt: `Calculer le conjugué de −1 − 4i.`
- hidden acceptedResponses: only `−1 + 4i`.

## Engineering disposition

The next author wave must produce two independent repair candidates from the same G4 evidence base:

- PRODUCT UX R1;
- SHOWCASE CONTENT R2.

No sibling consumption, no fan-in, no G5 verdict, no student authorization.
