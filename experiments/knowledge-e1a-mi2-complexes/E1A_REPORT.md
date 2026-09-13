# E1A — Knowledge Architecture Falsification — MI2 Nombres Complexes

## Executive summary

E1A tested Source Map → Knowledge → Pedagogy against the current Direct AI Kit Factory route without changing `learnit.kit.v2` or the Player.

Observed value: the separation helps **scope control, prerequisite declaration, reuse, and deterministic impact analysis**. It is not justified as a mandatory route. Section 1.2 can be teaching scope while 1.1 remains consultable prerequisite context and selected exercises from 1.4 remain assessment material.

The experiment falsifies “OKF everywhere”: a general knowledge-management layer is unnecessary. The useful core is smaller: stable source locators + compact concept bundle + typed Learn-it relations + pedagogical blueprints. OKF-like portability may be useful as interchange, not runtime dependency.

## Scenario results

- A Scope selector: PASS at model level.
- B Reuse: PASS at model level; module/argument/exponential form are shared dependencies.
- C Same knowledge/different pedagogy: PASS at model level; knowledge identities remain unchanged.
- D Figures/equations: PASS with locator caveat; PDF-page + numbered item locators suffice, extracted glyph offsets do not.
- E Exercises: PASS; exercises are practice/assessment evidence, not concepts.
- F Direct vs Knowledge A/B: **HOLD**; a fair pair of canonical `learnit.kit.v2` candidates has not yet passed the complete Factory qualification in this execution.
- G Existing kit: product witness only; visible current course focuses on conjugate/module and is not semantic authority for the bounded 1.2 target.
- H Impact: PASS at model level; fixture change to `roots-of-unity` marks only dependent blueprints `REVIEW_REQUIRED`.
- I Fast path: PASS; Direct AI Kit Factory remains preferred for small one-off non-reused scopes.

## Complexity ledger

Added only: source manifest/map, compact knowledge bundle, typed relation sidecar, scope manifests, pedagogical blueprints, impact manifest. Not added: backend, graph/vector DB, OCR, Player/schema/learner-state changes, generic ingestion platform.

This complexity is proportionate only when reuse, selective scope or change-impact analysis is needed. For a one-shot kit it is overhead.

## Uncovered risks

Not proven: 200–300 page scale; multiple authoritative sources; conflicting editions; scan/OCR-heavy input; multilingual scale; catalogue/search performance; operational cost of independent A/B author/reviewer contexts.

## Independent audit

False PASS found: canonical A/B qualification is incomplete, so E1A cannot PASS. False FAIL also rejected: scope separation, reuse and impact targeting show concrete value. PDF remains semantic authority. No scale claim is made. Fast-path negative result is retained.

## FINAL VERDICT

`HOLD_E1A_ARCHITECTURE_NEEDS_REWORK`

### Minimum rework

Do not redesign. Complete one narrow missing proof: generate two canonical kits for the same `1.2.3.2 + 1.2.4` learner brief; Route A gets PDF+brief; Route B gets Source Map+Knowledge Bundle+same brief with PDF still authoritative; run canonical validators, M3.1 quality, independent source-fidelity review and Factory gate on both; compare leakage, prerequisites, fidelity, quality, artifact count and reconstruction cost. PASS to E1B only if B is non-degraded and materially improves scope/provenance/reuse/impact while the fast path remains optional.

## Mandatory question

> If Learn-it had to produce 20 kits from this course or a much longer course, would the added knowledge artifacts really reduce work, inconsistencies and evolution cost—or merely move complexity?

Current answer: **probably reduce them when kits overlap or evolve independently, but this is not yet causally proven by the required canonical A/B run.** Reusable concept identities and explicit dependencies reduce repeated interpretation and enable impact targeting; the source map prevents chapter selection from becoming accidental full-course teaching. For isolated one-off kits they merely move complexity. E1A therefore stays HOLD until the narrow A/B proof is complete.
