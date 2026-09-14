# B_E1A vs B_R1

## Coverage
Frozen B preserves the general n-th-root formula but loses Theorem 1.56 between Source Map and Knowledge. The pre-repair coverage comparison reports exactly one `MISSING_SILENTLY` witness: `theorem-1.56`.

B_R1 adds `roots-of-unity#zero-sum-property`, maps Theorem 1.56 to it, and makes Example 1.57 an explicit bounded exclusion. `coverage_check` passes after repair.

## Quality
Canonical `learnit.kit.v2`, Atlas and M3.1 results are intentionally left to the exact repository authorities in CI. No validator is modified.

## Scope
Same learner goal and same sections 1.2.3.2 + 1.2.4. No section 1.3 teaching content is added. The running-header ambiguity on PDF page 21 is resolved by the frozen Source Map item identity.

## Budget
10 activities × 4 minutes = 40 minutes. One redundant U4-count correction activity is replaced by a Theorem 1.56 zero-sum correction activity. The general n-th-root validation and Remark 1.55 geometry transfer remain present.

## Complexity / value
The mechanism is a JSON ledger plus a small deterministic checker and tests. It does not add runtime state, a database, a graph, generic ingestion, or mandatory Direct-path work.
