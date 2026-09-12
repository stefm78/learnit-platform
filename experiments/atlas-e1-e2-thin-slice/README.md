# Atlas E1/E2 learning-experience thin-slice experiment

Status: isolated architecture experiment. **Not a product contract, not a runtime integration, not a promotion candidate.**

Baseline: `learnit-platform` main `dbed49743ea84be87a7b55196b5b9800be65c8c5`.

## Question

Can two materially different learning targets use the same minimal executable grammar without changing the Atlas evidence kernel?

- E1: choose an appropriate method and compute both complex square roots.
- E2: productively recall 20 Spanish words, split into four evidence-coherent objectives of five words.

## Experimental grammar

```text
SCORED ACTIVITY
├─ support?        authored, pre-response, not on-demand assistance
├─ stimulus        learner-visible prompt
├─ response        fields[] of strings
├─ evaluator       exact-fields + explicit normalization
└─ feedback        intentionally outside this isolated evaluator prototype
        ↓
SCORING ADAPTER
        ↓
responseDigest + scoringRuleId + scoringRuleDigest + correct|incorrect + assistance
        ↓
EXISTING ATLAS EVIDENCE KERNEL (hypothesis)
```

The experiment intentionally does **not** introduce a non-scored learning-experience entity. Acquisition support is attached to a scored practice activity; revealing support is absent from validation.

## What the prototype proves if tests pass

1. E1 and E2 can share one response shape (`fields`) and one deterministic evaluator (`exact-fields`).
2. Productive vocabulary does not require a probabilistic or LLM scorer for a bounded lexical target.
3. A multi-component math target can be kept evidence-coherent by scoring method + both roots as one execution.
4. Twenty vocabulary items need not become one over-broad objective; the fixture uses four objectives of five terms.
5. Authored baseline support and on-demand assistance are distinct concepts.
6. A scoring adapter can emit the same evidence-facing primitives Atlas already consumes conceptually: response digest, scoring-rule identity/digest, binary outcome, and assistance state.
7. Learner-visible stimulus, response specification, and evaluator are separable identities; the evaluator answer key need not define learner-visible stimulus identity.

## What the prototype does not prove

- that `learnit.kit.v2` should now change;
- that the current Atlas five-class authoring profile should change;
- that free-form semantic answers can be scored deterministically;
- that images/audio/speech/code/external evaluation are solved;
- that retention or transfer is educationally improved;
- that this prototype architecture should be copied directly into production.

`EXPERIMENT_PASS != INTEGRATION_DESIGN_PASS`.

## E1 details

The practice fixture uses a provided argument and the exponential method. The independent-validation fixture uses `z₀ = 5 + 12i` without an argument and expects the algebraic method, with roots `3 + 2i` and `-3 - 2i` under an explicit ordering convention.

This is intentionally exact-text scoring. It does not claim mathematical-expression equivalence.

## E2 details

Twenty target pairs are divided into four objectives of five words. The evaluator applies NFC, trimming, and case normalization; accents remain significant. This tests productive recall rather than recognition from supplied choices.

## Run

```bash
node --test experiments/atlas-e1-e2-thin-slice/prototype.test.mjs
```

No external packages, network access, clock, randomness, persistence, or product runtime are required.

## Falsification conditions

Treat this architecture as falsified or incomplete if product integration later requires any of the following merely to support E1/E2:

- math-specific or language-specific branches in the Atlas evidence core;
- a new learner-state model;
- a new execution class;
- abandonment of `responseDigest` / scoring-rule identity / binary outcome;
- a probabilistic scorer for these bounded targets;
- treating authored acquisition support as if the learner requested assistance;
- representing QCM/fill unnaturally in the same grammar;
- an activity/evaluator contract whose complexity exceeds the capability gained.

## Next decision if this experiment passes

Return to `/solve` from the protected product baseline. Independently select the smallest integration design. Do not copy the prototype structure into `learnit.kit.v2` by default.
