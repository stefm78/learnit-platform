# E1A — Knowledge Architecture Falsification — MI2 Nombres Complexes

## Executive summary

E1A compares a Direct AI Kit Factory route with a Source Map -> Knowledge -> Pedagogy route on the same MI2 source scope and learner brief, without changing `learnit.kit.v2` or the Player.

The deterministic comparison is closed: both frozen candidates pass the unchanged canonical validators and both are `EXCELLENT_BY_PROFILE` at M3.1. Exact source-bound Factory contexts now also exist for both routes.

The independent semantic phase changes the result materially: **both routes are semantic HOLD**. Route A under-covers general n-th-root construction and also omits Theorem 1.56. Route B does cover the general n-th-root formula, so the Knowledge route is semantically stronger on this witness, but Route B also omits Theorem 1.56 and therefore cannot obtain `PASS_AI_KIT_FACTORY_V1`.

The most important architecture finding is causal and localized: the Source Map correctly contained Theorem 1.56, but the Knowledge Bundle did not preserve it. E1A therefore exposes a real Source Map -> Knowledge coverage-loss failure.

## Frozen A/B evidence

- baseline `main`: `1e71271436fd4b7dd7d895cfec827833187630fe`;
- experiment branch pre-semantic-evidence HEAD: `ee5e5fc50579723bd8722162afebcc6d28ee8c1d`;
- draft qualification PR: `#377`, explicitly not for merge;
- Route A package digest: `sha256:0d03102d9bcb880f8114c1992ab512d2ecb28b6227d0a60867645013aaabfc83`;
- Route B package digest: `sha256:cb38f6773437f39b6b9287149d4e8da76af6938467fe5a60dc39a8f7a29dcaf7`;
- exact source PDF SHA-256: `a197b2a17743752a79ec77caa4543b791cfcf246a2e8a749ffcb2677c3b05c26`.

Canonical deterministic run `34768852674` / job `103754617726` produced `PASS_DETERMINISTIC_CANONICAL_QUALIFICATION`; both routes are canonically valid and `EXCELLENT_BY_PROFILE`.

## Exact Factory binding

Route A:

- kitSha256 `sha256:c3bc513fbb3b003edfcdd06fe82aea886934bf4be71b80fe90525176a6a38b88`;
- contextDigest `sha256:a6c99a600a0134dc6e4c658f864228ac344f78051ffa27e6121a59017192c390`.

Route B:

- kitSha256 `sha256:4ce65c0de6520aae74b29ba89da4e8ef00023fed0b499216b6c1c765791afaec`;
- contextDigest `sha256:8d19e9fb88f25037ef584c7257b16e9bbd7906142a9da3d403252d220d1951d5`.

Both bind the same exact source bytes and learner brief.

## Independent semantic qualification

### Route A — semantic HOLD, schema resubmission required

The independent reviewer reports three major semantic defects:

- the kit never requires determination of all n-th roots of a general nonzero complex number;
- Theorem 1.56, the zero-sum property of roots of unity, is omitted;
- the second-objective validation pair therefore under-tests the stated objective.

The review content is source-supported, but the response profile/field names do not match the exact Factory review schema. It is retained as audit evidence, not treated as canonical Factory input. A clean-context reviewer must re-emit the same independently reached review in the exact `learnit.atlas.semantic_review.v1` shape.

### Route B — canonical semantic HOLD

The Route B review is structurally and cryptographically bound to the exact Factory context. It reports:

- `objectiveCoverage = hold` because Theorem 1.56 is absent;
- one major finding for that omission;
- one minor ambiguity because the correct general n-th-root QCM label omits the explicit `k=0,...,n-1` range although its explanation restores it.

The semantic verdict is `HOLD_SEMANTIC_REVIEW_V1`. Therefore the unchanged Factory Gate cannot return `PASS_AI_KIT_FACTORY_V1`; its semantic branch resolves to `HOLD_FACTORY_SEMANTIC_REVIEW`.

## A/B semantic comparison

Route A and Route B are not semantically tied anymore.

Route A covers square roots, complex quadratics, roots of unity, root count, and geometry, but it does not make the learner determine general n-th roots.

Route B adds an explicit validation for the general n-th-root formula of a nonzero complex number. That is a material improvement aligned with the learner brief. The Knowledge route therefore shows a real scope/coverage benefit over Direct on this witness.

However, both routes omit Theorem 1.56. Route B's omission is particularly informative because the Source Map had already identified the theorem.

## Root cause in the Knowledge architecture

`source/source-map.json` lists under section 1.2.4:

- Theorem 1.53;
- Example 1.54;
- Remark 1.55;
- Theorem 1.56;
- Example 1.57.

It also records that PDF page 21 begins with Theorem 1.56 despite the running header changing to 1.3, so the source-boundary ambiguity was already understood correctly.

`knowledge/knowledge-bundle.json`, however, retains only target units for:

- complex square roots;
- complex quadratic equations;
- n-th roots;
- roots of unity;
- regular-polygon representation.

There is no retained knowledge property/claim for the zero-sum theorem. `pedagogy/scope-ab.json` then consumes that reduced target set. The omission therefore occurs specifically at Source Map -> Knowledge, and the learner kit faithfully inherits the loss.

This falsifies the assumption that a concept-only knowledge inventory is sufficient to preserve a bounded source scope. Some important source knowledge is proposition/property shaped rather than concept shaped.

## Complexity ledger

Route B still adds useful durable structure for source mapping, target-vs-prerequisite separation, typed dependency relations, reuse and impact analysis. It does not require a graph database, OCR platform, backend or learner-runtime AI.

The new evidence shows the missing minimal capability: **coverage preservation for in-scope source items**. The smallest credible repair is not a general knowledge-management system. It is an explicit coverage ledger or claim layer that requires every in-scope numbered source item to be one of:

- represented by a Knowledge unit/property/claim;
- explicitly excluded with a source-bound rationale.

Silent disappearance must be invalid.

## FINAL VERDICT

`HOLD_E1A_ARCHITECTURE_NEEDS_REWORK`

E1A does not justify E1B scale testing yet because neither frozen route obtains a genuine Factory PASS. Route B is semantically stronger than Route A, so the Knowledge architecture is not falsified outright; but its own intermediate representation silently drops a source theorem that the Source Map knew about.

The frozen A/B pair must remain unchanged as evidence. Any repair must be a fresh iteration with new candidate identities and a targeted Source Map -> Knowledge coverage-preservation mechanism.

## Mandatory question

> If Learn-it had to produce 20 kits from this course or a much longer course, would the added knowledge artifacts really reduce work, inconsistencies and evolution cost—or merely move complexity?

Current answer: **they can reduce work and inconsistencies, but only if the Knowledge layer is coverage-preserving. E1A shows both sides: Route B preserves general n-th-root scope better than Direct, yet it silently loses Theorem 1.56 between Source Map and Knowledge. Without an explicit coverage invariant, the architecture can move complexity and create a new omission surface. With a lightweight coverage ledger/claim layer, the reuse/provenance/impact benefits remain plausible enough to justify a targeted repair experiment before any scale test.**
