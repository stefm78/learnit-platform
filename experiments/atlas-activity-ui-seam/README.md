# Atlas Activity UI Seam — R14 pre-integration qualification

Status: isolated pre-integration experiment. **Not a product contract, not a runtime integration, not a promotion candidate.**

Baseline product HEAD: `8cd2c27edf68bae1bb1a1a634a431a2ecbfce4e9` (R14 candidate from PR #354).

Authority state at experiment start:

- `HUMAN_REPLAY_R14_FUNCTIONAL_PASS`;
- `VISUAL_POLISH_FINAL_CONFIRMATION_REQUIRED`;
- UX may polish #354;
- Learning must not mutate #354 product files;
- isolated `constructed` research/prototypes are allowed.

## Question

Can Learn-it add one bounded learner-produced response family without extending the current DOM/scoring coupling in `apps/learnit-next/src/integration/atlas/session.js`, while preserving current QCM/fill semantics and the Atlas evidence-facing result shape?

The experiment tests this conceptual boundary only:

```text
LEARNING
  source activity + private scoring material
        |
        | ActivityPresentation (learner-safe)
        v
ACTIVITY UI
  render + read interaction
        |
        | ActivityResponse
        v
LEARNING / EVALUATION
  normalization + correctness
        |
        | ActivityEvaluation
        v
ATLAS SESSION / EVIDENCE ADAPTER
```

`ActivityPresentation`, `ActivityResponse`, and `ActivityEvaluation` are vocabulary for ownership. They are not persistent schemas and do not authorize a new runtime, registry, plugin system, or generic activity framework.

## What is exercised

The tests load the repository's real `apps/learnit-next/src/core/session.js` source at runtime and import it as an ES module to use its exported `evaluateAnswer()` as the QCM/fill oracle. This avoids re-implementing those rules inside the experiment.

The experiment then adds only an isolated `constructed` + `exact-fields` evaluator sufficient for two prior falsification targets:

- E1: choose a method and produce both complex square roots;
- E2: productively recall twenty Spanish words, divided into four evidence-coherent objectives of five words.

## Learner-safe boundary

The presentation projection is intentionally incapable of carrying scoring secrets. Tests reject recursive exposure of keys such as:

- `correctChoiceId`;
- `answers`;
- `acceptedValues`;
- evaluator / scoring-rule internals.

QCM remains QCM-shaped; fill remains fill-shaped. Neither is forced into the constructed `fields` grammar.

## Support and assistance

Authored pre-response support is separate from learner-requested assistance. Practice support can be visible while `assistance` remains `none`. A constructed validation fixture with explicitly revealing authored support is rejected by the experiment.

This does not change Atlas assistance records or ObjectiveEvidence.

## Run

From repository root:

```bash
node --test experiments/atlas-activity-ui-seam/prototype.test.mjs
```

The test file reads the real R14 `core/session.js`; no network, persistence, clock, browser, planner, or Atlas evidence mutation is required.

## Falsification conditions

Treat the proposed seam as falsified or incomplete if production integration of the bounded E1/E2 capability requires any of the following:

- exposing answer keys or evaluator internals to the UI;
- putting DOM/querySelector dependencies in learning correctness logic;
- keeping QCM/fill rendering, DOM readout, and scoring branches together in the Atlas integration layer;
- changing QCM/fill normalized-answer semantics;
- a new planner rule, ObjectiveEvidence state, execution class, storage migration, or runtime;
- a generic capability/plugin framework merely to add this one response family;
- forcing QCM/fill into the constructed fields representation;
- probabilistic/LLM/fuzzy scoring for the bounded E1/E2 targets.

## Current conclusion

The prototype supports **PREINTEGRATION_PASS** for the architecture question, subject to one important limit: it does not prove the final product patch until #354 is accepted, merged, and the exact new `main` is re-audited. See `DECISION.md` and `POST_MERGE_PATCH_MAP.md`.
