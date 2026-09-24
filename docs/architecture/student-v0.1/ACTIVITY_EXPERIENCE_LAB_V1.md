# Activity Experience Lab V1 — V5 Interaction Convergence

Status: Phase-A prototype laboratory; human physical-device decision still required.

## Boundary

The Lab consumes learner-safe `ActivityPresentation` fixtures and emits only the frozen Student V0.1 `ActivityResponse` grammar. Production `apps/learnit-next/src/**` remains read-only. The Lab contains no answer keys, correctness evaluation, score, mastery, progress/session authority, persistence, external network dependency, plugin registry, dynamic loader or production import.

## V5 interaction grammar

Manipulable candidates share a common visual/state model:

- `normal`: one neutral border and common radius;
- `selected`: subtle tint + accent border + small elevation;
- `focus`: independent keyboard-focus ring;
- `dragging`: elevated floating representation;
- `empty target`: one dashed affordance;
- `filled target`: moved card/token replaces the empty-target affordance, without a redundant shell.

Drag uses Pointer Events. Tap/click selection never mutates position by itself. Mutation requires an explicit destination or an actual drag/drop.

## Candidate behavior

- `flashcard-b`: repeated question, answer and explanation share the same left/start reading axis; card remains reversible.
- `matching-b`: source card and target become a persistent two-card pair; no outer pair frame and no filled-slot frame; source/target orders randomize independently once per attempt.
- `order-b`: vertical-only ghost; independent insertion placeholder moves while the source card remains structurally stable during pointer movement; tap selection reveals large-hit-area visual intercalaires for non-drag placement.
- `classify-b`: no movement panel; persistent bucket-title destinations implement select-card -> tap-bucket; drag supports source↔bucket and bucket↔bucket.
- `fill-b`: no movement panel; select-token -> tap-empty-slot; filled slots remove their shell and nested destination semantics; drag replacement returns displaced token to the bank; bank title is the explicit non-drag return destination.
- `qcm-a`: radio and label remain naturally aligned with robust wrapping.

## Randomization

QCM choices, Matching source/targets, Order initial items, Classify source cards and Fill token/options shuffle once per attempt. Category order and sentence-slot order remain stable. Test-seed support exists only for deterministic audit and is not persisted authority.

## Verification

`test_lab.py` checks static boundary invariants, required Pointer Event machinery, absence of HTML5 drag/network/persistence, and V5 structural markers.

`browser_smoke.py` runs a 390x844 mobile/touch causal audit covering exact response grammars, deterministic randomization, Matching visual replacement and selection, Order vertical ghost/placeholder/intercalaires, Classify tap destinations, Fill tap-empty-slot/drag-replacement, long-label layout, reduced motion and network/browser cleanliness.

`production_audit.py` independently challenges the authored test assumptions (selection, nested framing, direct destinations, non-drag reorder, common radii and stale movement UI). `visual_audit.py` captures Matching B, Order B, Classify B and Fill B final states for visual inspection.

The V5 adversarial audit found one bounded regression during construction: pointer handlers could suppress the subsequent tap-selection path. The implementation was repaired so a normal tap survives Pointer Event setup while post-drag synthetic clicks remain suppressed; the full static, mobile-touch and production audits then passed from clean state.

Physical Android review remains the final Phase-A gate.
