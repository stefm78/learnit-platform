E1B_FINAL_RESULT

SOURCE:
- SHA256: cc411ddb76a904a684a44ce85be15b67a9ef9f2bc75288697a4981a62a4b0c73
- BYTES: 3042017
- PAGES: 163
- TITLE: UXFGE2108 — Énergie et enjeux climatiques
- VERSION: 26 août 2026

BASELINE:
- MAIN_HEAD: 1e71271436fd4b7dd7d895cfec827833187630fe
- R1_EVIDENCE_HEAD: a760ce1f8bb1098f122a66beb73ce5d8c6e257b5
- E1B_HEAD: PENDING_REMOTE_COMMIT
- PR: PENDING_REMOTE_PR
- WORK_PACKAGE: EXP-WP-002

WORKLOADS:
- K1: PASS
- K2: PASS
- K3: PASS
- K4: PASS

A_B_QUALITY:
- DIRECT: 4/4 locally canonical/Atlas-equivalent PASS; expected M3.1 EXCELLENT_BY_PROFILE; exact repository authority recheck delegated to E1B CI.
- KNOWLEDGE: 4/4 same qualification state; all target coverage ledgers PASS with zero MISSING_SILENTLY.
- MATERIAL_QUALITY_REGRESSION: false

SCOPE:
- K4_NARROW_SCOPE: PASS
- SCOPE_LEAKAGE: 0

REUSE:
- TOTAL_KNOWLEDGE_REFS: 25
- UNIQUE_KNOWLEDGE_OBJECTS: 21
- REUSED_REFS: 4
- OBJECTS_REUSED_BY_2PLUS_KITS: 4
- HIGHEST_REUSE_COUNT: 2

SCALE:
- SEMANTIC_INTERPRETATION_PROXY_DIRECT: 47
- SEMANTIC_INTERPRETATION_PROXY_KNOWLEDGE: 65
- MARGINAL_COST_TREND: DECREASING for the observed K1→K2 reuse derivative; unrelated K3/K4 controls intentionally reset new-curation cost
- OBSERVED_BREAK_EVEN_N: NONE (within the four mixed workloads)
- PROJECTED_BREAK_EVEN_N: 13 (observed-medium K1/K2 reuse profile)
- BREAK_EVEN_BY_20: PASS

CHANGE_IMPACT:
- EXPECTED_IMPACT_SET: DELTA-CARNOT-REV=[K1,K2]; DELTA-K3-RTH=[K3]
- OBSERVED_IMPACT_SET: DELTA-CARNOT-REV=[K1,K2]; DELTA-K3-RTH=[K3]
- FALSE_POSITIVES: []
- FALSE_NEGATIVES: []
- RESULT: PASS

COMPLEXITY:
- ONE_TIME_OVERHEAD: one experiment verifier/workflow/work package; no product authority changes
- PER_SOURCE_OVERHEAD: exact source binding + lightweight document map + demand curation + locator audit
- PER_KIT_OVERHEAD: scope/coverage/blueprint evidence plus normal candidate activities; Direct does not require Knowledge artifacts
- BOUNDED: PASS

FAST_PATH:
- OPTIONAL_KNOWLEDGE_PATH: PASS

QUALIFIERS:
- SOURCE_PAGE_COUNT: 163
- 200_300_PAGE_SCALE_NOT_DIRECTLY_TESTED
- UPSTREAM_R1_RESERVATION: INDEPENDENCE_DEGRADED
- SEMANTIC_REVIEW_INDEPENDENCE: DEGRADED (`NON_INDEPENDENT_COMPARATIVE_REVIEW`)

FINAL_VERDICT:
PASS_E1B_LONG_SOURCE_SCALE_REUSE_READY_FOR_INTEGRATION_SOLVE

DECISION_BASIS:
- The full 163-page source was navigated with a lightweight structural map; only K1-K4 target/support regions were semantically curated.
- K4 remained a 5.3.4 learning scope with 5.3.2-5.3.3 only as support; no unrelated topic leaked into its frozen candidates.
- K1 and K2 reuse four concrete Knowledge objects grounded in p58-64, not generic placeholders.
- All B target obligations are represented; zero `MISSING_SILENTLY` states remain.
- A/B paired visible pedagogical content was controlled to avoid giving Knowledge an output-size/content advantage.
- The four mixed workloads do not amortize Knowledge yet: proxy 65 vs 47.
- Under the observed K1→K2 overlap profile (7/12 obligations reused), the transparent proxy projects break-even at N=13, within 20 derivatives.
- Low-reuse sensitivity does not break even by 20, so Knowledge must remain optional rather than universal.
- Change-impact traversal selects K1/K2 for the shared reversibility fixture and K3 only for the resistance-association fixture, with no false positives/negatives.
- The Direct fast path remains valid for a one-off Archimedes request; no Knowledge artifact is required.
- No runtime, canonical schema, validator, Factory Gate, or author/reviewer skill change was needed.
- Semantic comparison is deliberately labelled non-independent; this is a reservation, not hidden as a clean Factory pass.

ANSWER_THE_STRATEGIC_QUESTION:
> For 20 genuinely overlapping or evolving derivatives, the observed K1/K2 reuse profile indicates that persisted semantic curation and exact dependency traceability can amortize their overhead by roughly the 13th kit in the decision-count proxy, while reducing change-review fan-out. That conclusion does not generalize to low-reuse derivatives: when scopes are mostly unrelated, the Direct path remains cheaper and should be preferred.

NEXT_ACTION:
- if PASS: `REENTER_SOLVE_FROM_MAIN_FOR_MINIMUM_INTEGRATION`
