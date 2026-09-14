# E1A A/B semantic qualification audit — 2026-09-14

## Result

`HOLD_E1A_ARCHITECTURE_NEEDS_REWORK`

The exact source bytes and Factory contexts are now available. Two independent reviewer responses were received. Route B is structurally consumable by the canonical semantic-review contract and reports `HOLD_SEMANTIC_REVIEW_V1`. Route A also reports semantic HOLD, but its JSON shape/profile are non-conformant and therefore cannot be consumed by `factory_gate.py` without a clean-context reviewer resubmission.

## Route A

Substantive reviewer findings are supported by the source and candidate:

1. no activity requires actual determination of all n-th roots of a general nonzero complex number;
2. Theorem 1.56 (sum of roots of unity equals zero for n>=2) is absent;
3. the second-objective validation pair therefore under-tests the declared objective.

The response is not canonical Factory evidence because its profile/field names do not match `learnit.atlas.semantic_review.v1`. Factory decision: `NOT_RUN_REVIEW_INPUT_NONCONFORMANT`.

## Route B

The review target binds exactly to the Route B Factory context. Structure and binding pass the canonical review-shape checks. Semantic reasons are:

- `DIMENSION_HOLD:objectiveCoverage`
- `MAJOR_FINDING:F-001`

Therefore, given the already-proved `EXCELLENT_BY_PROFILE` deterministic quality result, the unchanged Factory Gate logic necessarily resolves the semantic layer to `HOLD_FACTORY_SEMANTIC_REVIEW`; no Factory PASS can be claimed.

Route B additionally has one minor ambiguity: the correct general n-th-root choice omits the explicit `k=0,...,n-1` range in the choice label, although the explanation restores it.

## Source-grounded root cause

The PDF and `source-map.json` both contain Theorem 1.56. `source-map.json` explicitly lists `Théorème 1.56` and `Exemple 1.57` under section 1.2.4 and records the page-21 running-header ambiguity.

The information is then lost in `knowledge/knowledge-bundle.json`: target concepts cover complex square roots, complex quadratic equations, n-th roots, roots of unity and polygon representation, but no target concept/property represents the zero-sum theorem. `pedagogy/scope-ab.json` inherits only those target knowledge IDs. This establishes a concrete Source Map -> Knowledge coverage-loss failure in Route B.

Route B nevertheless preserves more of the requested semantic scope than Route A: it includes a validation for the general n-th-root formula of a nonzero `z0`, while Route A only validates roots of unity and cardinality for roots of `i`.

## Experimental interpretation

The Knowledge route is not semantically worse in this witness; it is materially better on general n-th roots. But it is not sufficient: a source item explicitly present in the Source Map was dropped by the Knowledge representation and consequently absent from the learner kit. This is exactly the kind of loss a Knowledge Architecture should prevent.

The architecture therefore cannot advance to E1B yet. The frozen candidates must remain unchanged. A repair iteration, if authorized next, should operate on the Source Map -> Knowledge coverage-preservation rule and produce fresh candidate identities rather than mutating the frozen E1A A/B evidence.
