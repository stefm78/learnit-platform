# ARC-WP-024 — Constructed-response contract evolution

## Decision

Do **not** mutate `learnit.kit.v2` in place.

Introduce an explicit opt-in successor discriminator:

```text
learnit.kit.v3
```

`learnit.kit.v3` keeps the current v2 foundation semantics for `qcm` and `fill` and adds exactly one new activity family:

```text
constructed
```

This work package defines only the contract authority. It does not implement learner runtime, importer, authoring, planner, evidence, memory or storage changes.

## Why a new contract discriminator is required

ARC-WP-022 froze the v2 contract before parallel implementation and states that it may change only through a new architecture work package. More importantly, adding a new activity family while keeping the discriminator `learnit.kit.v2` would make the meaning of an already-published contract depend on reader age: an older v2 reader would reject a newly-valid v2 payload.

That ambiguity is unnecessary. Existing v2 kits already have durable value and must remain exactly what they are.

Therefore:

- existing `learnit.kit.v2` packages stay v2;
- the v2 schema stays byte-unchanged;
- new content that needs `constructed` uses `learnit.kit.v3`;
- future product work may support v2 and v3 side by side;
- no automatic migration or payload rewriting is required.

## First bounded constructed activity

The first v3 constructed family is intentionally narrow.

Canonical authored shape:

```json
{
  "type": "constructed",
  "prompt": "Expliquez le raisonnement.",
  "acceptedResponses": [
    "Réponse de référence A",
    "Variante de référence B"
  ]
}
```

The object also carries the same common lineage, revision, objective, explanation, difficulty, phase and assessment-role fields as qcm/fill.

No rubric object, evaluator plug-in, AI model, scoring callback or remote authority is part of the contract.

## Learner response

The learner response shape is exactly:

```json
{
  "text": "réponse saisie par l'apprenant"
}
```

A response that becomes empty after canonical normalization is invalid.

The first runtime slice should cap learner input at 4,000 characters. The contract limits each authored accepted response to the same bound.

## Deterministic evaluation semantics

The first and only authorized scoring rule is:

```text
canonical-text-match-v1
```

For learner text and every authored accepted response:

1. normalize Unicode to NFC;
2. trim leading/trailing whitespace;
3. collapse each run of Unicode whitespace to one ASCII space;
4. compare the resulting strings case-sensitively and otherwise exactly.

The answer is correct when the normalized learner text equals any normalized authored accepted response.

This is deliberately conservative. It proves the complete product seam without pretending that long-form reasoning can already be assessed semantically.

## Ownership boundary

The promoted ATLAS-WP-025 seam remains authoritative:

```text
Learning semantics
      |
      v
Session orchestration
      |
      v
learner-safe ActivityPresentation
      |
      v
UI interaction
      |
      v
ActivityResponse
      |
      v
Learning Evaluation
```

For `constructed`, the UI may receive only:

```json
{
  "type": "constructed",
  "prompt": "..."
}
```

The UI must **not** receive:

- `acceptedResponses`;
- scoring-rule identifiers if they expose hidden semantics;
- evaluator functions;
- reference answers;
- rubric criteria;
- future model prompts or scoring secrets.

The UI returns only `{text}`.

## Why not mutate v2

Rejected because:

- ARC-WP-022 froze v2;
- old v2 readers would reject constructed payloads while the discriminator still claimed v2;
- existing validators, Studio and Factory deliberately treat v2 as qcm/fill-only;
- silent semantic expansion makes compatibility harder to reason about than an explicit successor.

## Why not build a generic Activity Runtime

The current evidence supports one additional learner interaction, not a framework.

ATLAS-WP-026 should therefore extend the existing seams directly. No registry, event bus, generic evaluator protocol, plug-in loader or persistent execution schema is justified yet.

If a second genuinely different constructed-evaluation mode later appears, that future evidence can justify another contract decision.

## Why not use AI scoring now

The first slice must remain deterministic, local and testable.

Remote or model-based scoring would immediately introduce questions of model identity, nondeterminism, privacy, availability, cost, prompt authority, auditability and false-positive/false-negative behavior. None of those are required to prove that the product architecture can safely carry a free-text response.

AI or rubric evaluation is therefore a later pedagogical decision, not part of the first transport/runtime slice.

## Compatibility model

### Existing v2 content

Unchanged and still canonical under `contracts/learnit-kit-v2.schema.json`.

### New v3 content

Uses `contract: "learnit.kit.v3"` and validates against `contracts/learnit-kit-v3.schema.json`.

### Future importer requirement

ATLAS-WP-026 may add explicit dual-contract admission:

```text
learnit.kit.v2 -> existing qcm/fill behavior
learnit.kit.v3 -> same qcm/fill behavior + constructed
other contract -> fail closed
```

No conversion is needed at import time.

## ATLAS-WP-026 boundary

Once ARC-WP-024 is accepted, the next product slice should be bounded to one real end-to-end constructed activity and must prove:

- v2 import and qcm/fill behavior are unchanged;
- v3 import is explicit and fail-closed;
- `constructed` renders as a learner text area;
- blank text is rejected before scoring;
- normalized `{text}` reaches Learning evaluation;
- `acceptedResponses` never cross the learner-safe UI boundary;
- deterministic canonical-text matching produces the expected boolean outcome;
- progress/evidence consume the same boolean result without a new persistence schema;
- existing Atlas learner journeys remain green;
- one real kit fixture can exercise `kit -> import -> plan -> presentation -> response -> evaluation -> feedback`.

## Non-decision

This work package does **not** decide how Learn-it should ultimately evaluate essays, proofs, explanations or open-ended reasoning. It only establishes the smallest safe canonical lane in which those future experiments can happen without leaking scoring authority into the UI or redefining v2 retroactively.
