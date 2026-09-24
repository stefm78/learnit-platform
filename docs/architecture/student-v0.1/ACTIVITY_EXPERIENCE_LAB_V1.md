# Activity Experience Lab V1 — V6 Destination Feedback / No Layout Shift

Status: Phase-A prototype laboratory; human physical-device decision still required.

## Boundary

The Lab consumes learner-safe `ActivityPresentation` fixtures and emits only the frozen Student V0.1 `ActivityResponse` grammar. Production `apps/learnit-next/src/**` remains read-only. The Lab contains no answer keys, correctness evaluation, score, mastery, progress/session authority, persistence, external network dependency, plugin registry, dynamic loader or production import.

## V6 interaction invariant

Across Matching B, Order B, Classify B and Fill B:

1. selecting an object changes only visual state;
2. selection reveals all and only valid tap/click destinations;
3. revealing destinations does not alter layout geometry;
4. activating a destination performs the mutation and clears destination feedback;
5. dragging to the same destination is a direct shortcut to the same mutation;
6. keyboard focus remains visually and semantically independent.

Shared visual states are `normal`, `selected`, `eligible-destination`, `active-destination` and `dragging`.

## Candidate behavior

- `flashcard-b`: question, answer and explanation share one left/start reading axis; card remains reversible.
- `matching-b`: selected source card highlights valid description cards; empty source side has one dashed target only; filled source side is replaced by the moved card; pair row has no outer frame.
- `order-b`: selection creates an absolute overlay of insertion targets without changing list height or any row rectangle. Each target has a large invisible hit region and a thin visible line. Drag remains strict-Y with fixed-X ghost and independent placeholder/reflow.
- `classify-b`: selected card reveals valid bucket-title destinations (and source return when applicable); selection alone never moves a card.
- `fill-b`: selected token reveals valid empty slots (and bank return when applicable); filled slots are shell-free and non-destination by tap; drag replacement remains explicit.
- `qcm-a`: radio/text alignment and long-label wrapping remain robust.

## Randomization

QCM choices, Matching source/targets, Order initial items, Classify source cards and Fill tokens shuffle once per attempt. Category order and sentence-slot order remain stable. Test-seed support exists only for deterministic audit and is not persisted authority.

## Verification

`test_lab.py` checks static boundary invariants, Pointer Events, absence of HTML5 drag/network/persistence, required shared state markers and absolute Order overlay machinery.

`browser_smoke.py` runs a 390x844 touch audit proving:

- exact response grammars;
- deterministic per-attempt randomization;
- zero selection-induced geometry movement for Matching/Order/Classify/Fill;
- eligible-destination feedback and cleanup;
- Matching and Classify drag active-destination feedback;
- Order zero-reflow overlay selection, non-drag insertion and strict-Y causal drag;
- Fill direct empty-slot placement, bank return and explicit drag replacement;
- long-label layout, reduced motion, no external requests and no browser errors.

`production_audit.py` is intentionally adversarial and checks numeric row rectangles/list height, overlay out-of-flow structure, bounded target overlap with adjacent cards, destination validity, selection-vs-destination distinction, mutation safety, framing convergence, common look-and-feel and accessibility DOM sanity.

The V6 visual audit caught one bounded production defect during construction: the rendered page still carried stale V5 title/eyebrow metadata. This was corrected to V6 and the complete static, browser, production and visual audits were rerun successfully.

Two audit assertions were also corrected because they incorrectly treated transient CSS transition/focus behavior as product defects; those audit fixes did not relax the functional invariants.

Physical Android review remains the final Phase-A gate.
