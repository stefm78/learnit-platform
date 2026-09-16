# E1A — Canonical A/B completion prompt

## Mission
Close the only material proof gap left by E1A without redesigning Learn-it: execute a fair, falsifiable A/B comparison between the current Direct AI Kit Factory route and the experimental Source Map → Knowledge → Pedagogy route for the exact same MI2 Nombres Complexes scope.

## Immutable baseline
- Repository: `stefm78/learnit-platform`.
- Work only on `experiment/e1a-knowledge-architecture-mi2-complexes` or a descendant experimental branch.
- Do not modify `learnit.kit.v2`, Player, learner state, canonical validators, Factory Gate, or production publication state.
- Source PDF remains semantic authority. Its measured SHA-256 is `a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`.
- Exact teaching scope: sections `1.2.3.2` and `1.2.4`; section `1.1` may be consulted only as prerequisite context; exercises may be used only when they test the target concepts.
- Use one frozen learner brief for both routes.

## Route A — Direct
Author a fresh canonical `learnit.kit.v2` candidate from only the authoritative PDF plus the frozen learner brief. Do not consult the experimental Source Map, Knowledge Bundle, relations, pedagogy blueprints, or Route B candidate while authoring Route A.

## Route B — Knowledge-assisted
In a clean authoring context, author a fresh canonical `learnit.kit.v2` candidate from the frozen Source Map, Knowledge Bundle, typed relations, and the same learner brief. The PDF remains available as semantic authority for verification and ambiguity resolution. Do not consult Route A candidate while authoring Route B.

## Fairness controls
- Same audience, goal, language, time budget and teaching scope.
- Same canonical contract and quality thresholds.
- Fresh identities for each candidate.
- No copying candidate content between routes.
- Do not optimize one route after seeing the other route's score.
- Record route inputs and any unavailable isolation primitive explicitly.

## Deterministic qualification
For each candidate, using the repository authorities unchanged:
1. derive Atlas claims and revision digests;
2. run `authoring/v2/validate_kit.py`;
3. run Atlas canonical validation on the arbitrary candidate;
4. run `authoring/v2/atlas/pedagogical_quality.py --json`;
5. require at least `STRONG`; prefer `EXCELLENT_BY_PROFILE`;
6. generate exact Factory context bound to source + brief + kit.

Do not describe a locally reimplemented check as a canonical validator execution.

## Independent semantic review
For each route, create a clean reviewer context that has not seen the author scratchpad or active author context. Review the exact source/brief/kit/factory-context tuple using `SKILL_ATLAS_KIT_REVIEW_V1.md`. Evidence must cover source fidelity, answer correctness, ambiguity, objective coverage, validation/transfer and learner fit. Then run the unchanged Factory Gate. If independent context isolation is unavailable, stop that qualification step and record `INDEPENDENT_REVIEW_UNAVAILABLE`; never self-certify.

## Comparison
Compare A and B on: canonical validity; M3.1 band; Factory decision; source fidelity findings; out-of-scope teaching leakage; prerequisite handling; objective coverage; semantic ambiguity; reusable concept/provenance identities; change-impact traceability; number of experimental artifacts required; authoring/reconstruction effort observable in the run; and any complexity introduced only by Route B.

Treat final-kit similarity as a valid result. Knowledge Architecture does not win merely because it creates more metadata.

## Falsification rule
Return `PASS_E1A_READY_FOR_E1B_SCALE_TEST` only if both routes receive genuine `PASS_AI_KIT_FACTORY_V1`, Route B is non-degraded pedagogically/semantically, and Route B demonstrates at least one material advantage in scope control, provenance/reuse or impact traceability that is not merely shifted complexity. Preserve Direct AI Kit Factory as an explicit fast path for one-off work.

Return `HOLD_E1A_ARCHITECTURE_NEEDS_REWORK` if evidence is incomplete or mixed but a bounded repair remains plausible. Return `FAIL_E1A_KNOWLEDGE_ARCHITECTURE_NOT_JUSTIFIED` if Route B degrades results or its benefits do not justify its complexity.

## Execution discipline
Research actual repository state first. Audit every PASS claim adversarially. Correct the plan until it is falsifiable and proportionate, then build only the smallest missing artifacts. Re-run current-state/CAS checks before repository mutation. Never weaken an authority to obtain PASS.

## Required outputs
Persist the frozen learner brief, Route A and Route B candidates, exact deterministic qualification outputs, independent reviews/Factory outputs when available, one A/B comparison report, and an updated `E1A_REPORT.md` with a single final verdict and the evidence that supports it.
