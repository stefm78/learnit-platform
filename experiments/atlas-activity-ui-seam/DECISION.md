# Decision — smallest post-merge Activity Runtime ↔ UI seam

## Baseline observations

R14 `core/session.js` already owns deterministic QCM/fill normalization and correctness through `evaluateAnswer()`.

R14 `integration/atlas/session.js` still combines three concerns:

1. Atlas scoring adapter / registry construction;
2. activity HTML generation (`renderActivity()`);
3. DOM response collection (`readResponse()`).

It therefore contains QCM/fill type branches on both semantic and interaction sides. Adding `constructed` directly there would create a third duplicated case and deepen the coupling.

The product schema and authoring validators currently admit only QCM/fill. Atlas editorial stimulus hashing also contains QCM/fill-specific stimulus/answer-operation branches. Those are legitimate future contract surfaces, but none must change in this experiment.

## Options challenged

### A — Keep core/session.js as learning authority; extract only activity render/read to UI

Decision: **SELECTED as the default post-merge direction.**

Why:

- reuses the existing normalization/correctness authority;
- creates one narrow technical seam at the actual coupling point;
- allows QCM/fill to keep native response shapes;
- gives `constructed` one new semantic branch and one new UI rendering branch, instead of duplicating it across scoring/render/read inside integration;
- requires no generic runtime or registry.

Residual question after merge: whether the UI functions belong in an existing UI module or one small new UI module. File naming is deliberately not frozen by this experiment.

### B — Add explicit ActivityPresentation / ActivityResponse objects

Decision: **ACCEPTED AS TRANSIENT INTERNAL VOCABULARY, NOT AS A NEW PERSISTED CONTRACT.**

The experiment shows a learner-safe presentation projection and raw response envelope are useful for enforcing ownership. They need not become separately versioned schemas, persisted records, or public APIs.

If direct function arguments achieve the same separation after merge, do not create extra DTO modules merely to preserve these names.

### C — Create activity_runtime.js / generic registry / capability or plugin framework

Decision: **REJECTED.**

No evidence requires it. The bounded capability gain is one deterministic learner-produced response family. A framework would add indirection, migration cost, and duplicate authority before a second genuinely different runtime need exists.

### D — Add constructed branches directly to integration/atlas/session.js

Decision: **REJECTED.**

This preserves the current architectural defect and increases the number of semantic + UI branches living together. The arrival of `constructed` should be used to remove the coupling, not deepen it.

## Falsification results

The executable prototype demonstrates all of the following without planner/evidence/storage/runtime changes:

- QCM presentation excludes `correctChoiceId`;
- fill presentation excludes `answers`;
- constructed presentation excludes evaluator and `acceptedValues`;
- QCM/fill responses still use the real product `evaluateAnswer()` authority;
- existing QCM unknown-choice and fill-incomplete errors remain observable;
- E1 exact-fields correct, incorrect, and incomplete cases are deterministic;
- E2 case/NFC normalization works while accent distinctions remain significant;
- authored practice support remains distinct from `assistance=used`;
- revealing support can be prohibited for constructed validation fixtures;
- result material can expose response/scoring digests + binary outcome + assistance without a new ObjectiveEvidence state or execution class;
- QCM/fill remain their native compact grammars;
- the experimental seam itself has no DOM/querySelector or generic capability registry.

## Decision

`PREINTEGRATION_PASS`

The smallest expected production architecture is:

```text
core/session.js
  existing qcm/fill authority
  + bounded constructed normalization/evaluation

UI-owned activity interaction
  render/read qcm/fill/constructed

integration/atlas/session.js
  orchestration + Atlas adapter
  no direct DOM response parsing
  no activity HTML construction
```

This is a hypothesis for the post-merge patch, not authorization to mutate product files now.

## What this does not prove

- the exact final schema shape for `constructed`;
- the exact filename of the future UI seam;
- that every future free-response domain can use exact-fields;
- semantic-equivalence scoring for mathematics or prose;
- media, speech, code, simulation, branching, ordering, matching, or external human evaluation;
- that the R14 branch itself may be promoted before the separate visual-polish gate closes.
