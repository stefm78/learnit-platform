# M3.2 AI Kit Factory — design freeze candidate

## 1. Product decision

M3.2 is **AI Kit Factory**, not Source to Draft.

The prior idea of building a generic PDF/text/Markdown ingestion pipeline, intermediate draft model and provenance-heavy transformation chain is rejected for this milestone as unnecessary complexity.

A capable AI should read supplied source material directly. Learn-it code should constrain, measure and gate the output rather than reproduce document understanding in deterministic software.

The target manufacturing loop is:

```text
source files + learner brief
        ↓
AI AUTHOR
        ↓
candidate learnit.kit.v2
        ↓
canonical validators
        ↓
M3.1 Pedagogical Quality Engine
        ↓
author repairs
        ↓
AI REVIEWER — independent context
        ↓
semantic/source-fidelity review
        ↓
deterministic factory gate
        ↓
PASS_AI_KIT_FACTORY_V1 or HOLD
```

The learner sees only the resulting canonical kit.

## 2. Design principles

### 2.1 Code what AI must not negotiate

Deterministic code owns:

- canonical `learnit.kit.v2` validity;
- Atlas canonical editorial validity;
- M3.1 structural pedagogical quality;
- source/brief/kit hash binding;
- semantic-review report shape;
- independence declarations;
- final factory PASS/HOLD logic;
- immutable machine-readable evidence.

AI owns:

- understanding source documents;
- selecting learning objectives;
- writing questions, explanations and distractors;
- pedagogical reformulation;
- repairing diagnostics;
- semantic/source-fidelity criticism.

### 2.2 No model integration in M3.2

M3.2 does not embed or call a model vendor.

There is:

- no API key;
- no remote AI endpoint;
- no backend;
- no runtime LLM;
- no model-specific prompt API;
- no network requirement in the factory gate.

An AI may operate in ChatGPT, Codex, another sandbox, a local model or future orchestration. The repository defines the manufacturing contract, not the model provider.

### 2.3 Author and reviewer are logically independent

The author and semantic reviewer are separate roles.

The reviewer:

- receives source files, learner brief, candidate kit and factory context;
- does **not** receive the author's hidden reasoning or scratchpad;
- is instructed to falsify the kit rather than improve it;
- must issue a structured review report.

Using a different model is desirable but not required in v1. Reusing the same model in a clean independent context is allowed. Reusing the author's active conversation/context is not.

## 3. Factory inputs

A factory run has three semantic inputs.

### 3.1 Source set

One or more source files.

The factory does not parse them. It binds them by:

- explicit source ID chosen by the operator/AI;
- byte length;
- SHA-256.

Example CLI notation:

```text
--source cours=./cours.pdf
--source notes=./notes.md
```

Source IDs must be unique and match `[A-Za-z0-9._-]+`.

Host absolute paths are not included in evidence.

### 3.2 Learner brief

A small JSON object outside the canonical kit:

```json
{
  "schema": "learnit.atlas.learner_brief.v1",
  "audience": "2e année école d'ingénieur",
  "goal": "Comprendre et savoir utiliser les notions du document",
  "language": "fr",
  "timeBudgetMinutes": 45
}
```

Required fields:

- exact schema string;
- non-empty `audience`;
- non-empty `goal`;
- non-empty `language`;
- integer `timeBudgetMinutes > 0`.

Additional fields are allowed because the brief is operator context, not a learner-runtime contract.

The factory hashes the canonical JSON bytes of the brief.

### 3.3 Candidate kit

Exactly one `learnit.kit.v2` candidate.

The factory does not extend the kit schema with source or reviewer metadata.

## 4. Factory context contract

The deterministic gate can emit a context document before semantic review:

`learnit.atlas.ai_kit_factory_context.v1`

Minimum shape:

```json
{
  "schema": "learnit.atlas.ai_kit_factory_context.v1",
  "profile": "atlas.ai-kit-factory.v1",
  "kitSha256": "sha256:...",
  "briefSha256": "sha256:...",
  "sources": [
    {
      "sourceId": "cours",
      "bytes": 12345,
      "sha256": "sha256:..."
    }
  ],
  "sourceSetDigest": "sha256:...",
  "contextDigest": "sha256:..."
}
```

Deterministic rules:

- sources sorted by `sourceId`;
- SHA-256 strings always prefixed `sha256:`;
- `sourceSetDigest` is SHA-256 of canonical JSON for the sorted source inventory;
- `contextDigest` is SHA-256 of canonical JSON containing profile, kit hash, brief hash and source-set digest;
- identical inputs produce byte-identical context output.

The semantic reviewer must bind its report to this context digest.

## 5. Structural factory gate

The deterministic gate reruns existing authorities. It does not trust a previously saved M3.1 report.

### 5.1 Canonical requirement

Required:

- general v2 validator PASS;
- Atlas canonical validator PASS.

Failure:

`HOLD_FACTORY_CANONICAL_INVALID`.

### 5.2 Pedagogical-quality requirement

The M3.1 engine is rerun on the exact kit.

Factory v1 accepts only:

- `STRONG`;
- `EXCELLENT_BY_PROFILE`.

Therefore:

- any M3.1 blocking diagnostic: canonical HOLD;
- any M3.1 warning / `COMPLETE`: `HOLD_FACTORY_PEDAGOGICAL_WARNING`;
- advice is allowed at `STRONG`, because source fidelity must not be distorted merely to eliminate an advisory;
- `EXCELLENT_BY_PROFILE` remains preferred.

There is deliberately no numeric threshold.

## 6. Semantic-review contract

The independent reviewer outputs:

`learnit.atlas.semantic_review.v1`

Required top-level shape:

```json
{
  "schema": "learnit.atlas.semantic_review.v1",
  "profile": "atlas.semantic-review.v1",
  "target": {
    "contextDigest": "sha256:...",
    "kitSha256": "sha256:...",
    "sourceSetDigest": "sha256:...",
    "briefSha256": "sha256:..."
  },
  "independence": {
    "authorScratchpadSeen": false,
    "authorActiveContextReused": false
  },
  "dimensions": {},
  "findings": [],
  "limitations": [],
  "verdict": "PASS_SEMANTIC_REVIEW_V1"
}
```

### 6.1 Mandatory dimensions

Exactly these six dimensions are required:

- `sourceFidelity`;
- `answerCorrectness`;
- `ambiguity`;
- `objectiveCoverage`;
- `validationTransfer`;
- `learnerFit`.

Each dimension contains:

```json
{
  "status": "pass",
  "summary": "non-empty reviewer statement",
  "evidence": [
    {
      "sourceId": "cours",
      "locator": "p. 12",
      "basis": "non-empty explanation of what was checked"
    }
  ]
}
```

Rules:

- `status` is `pass` or `hold`;
- `summary` is non-empty;
- `evidence` is non-empty for `sourceFidelity`, `answerCorrectness`, `objectiveCoverage` and `validationTransfer`;
- every evidence `sourceId` must exist in the bound source set;
- `locator` and `basis` are non-empty strings;
- `learnerFit` may use brief-based reasoning and therefore may have no source evidence.

The deterministic gate validates evidence references and shape. It does not claim the evidence text is semantically true.

### 6.2 Findings

Finding severities:

- `blocking`;
- `major`;
- `minor`;
- `advice`.

Every finding contains:

- stable reviewer-local `id`;
- `severity`;
- one mandatory review dimension;
- kit JSON `path` or `$`;
- non-empty `problem`;
- non-empty `impact`;
- non-empty `fix`;
- zero or more source evidence references.

Factory PASS permits only `minor` and `advice` findings.

Any `blocking` or `major` finding causes:

`HOLD_FACTORY_SEMANTIC_REVIEW`.

### 6.3 Semantic verdict

`PASS_SEMANTIC_REVIEW_V1` requires:

- all six dimensions `pass`;
- no blocking/major finding;
- reviewer independence booleans both `false`.

Otherwise the reviewer must use:

`HOLD_SEMANTIC_REVIEW_V1`.

The deterministic gate rejects inconsistent reports, for example a PASS verdict with a major finding.

## 7. Final factory verdict

The factory gate has these terminal outcomes:

- `HOLD_FACTORY_INPUT`;
- `HOLD_FACTORY_CANONICAL_INVALID`;
- `HOLD_FACTORY_PEDAGOGICAL_WARNING`;
- `HOLD_FACTORY_REVIEW_BINDING`;
- `HOLD_FACTORY_SEMANTIC_REVIEW`;
- `PASS_AI_KIT_FACTORY_V1`.

`PASS_AI_KIT_FACTORY_V1` requires simultaneously:

1. source set and learner brief are valid;
2. review target hashes exactly match current files;
3. canonical validators PASS;
4. M3.1 quality band is STRONG or EXCELLENT_BY_PROFILE;
5. all six semantic dimensions PASS;
6. no blocking or major semantic finding;
7. reviewer independence declarations are acceptable;
8. semantic reviewer verdict is PASS.

A PASS means:

> the candidate satisfies the deterministic Learn-it contract/profile and an independently declared semantic/source-fidelity review for the exact bound inputs.

It does **not** prove learner mastery, retention or teaching effectiveness.

## 8. Factory evidence

On every valid invocation the gate emits a deterministic JSON report:

`learnit.atlas.ai_kit_factory_evidence.v1`

It includes:

- factory profile/version;
- exact factory verdict;
- context digest;
- kit/source/brief hashes;
- canonical-valid boolean;
- exact M3.1 quality band/counts;
- semantic-review verdict/counts;
- semantic-review SHA-256;
- final blockers/reasons.

The gate never modifies the kit, source files, brief or review.

The same exact inputs produce byte-identical factory evidence.

## 9. AI author skill V2

M3.2 versions a new skill rather than mutating the promoted V1 skill:

`authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V2.md`.

It keeps all V1 source-fidelity and Atlas rules, then adds the factory loop:

1. read source files and learner brief directly;
2. author one canonical candidate;
3. regenerate derived identities/digests with existing authorities;
4. run canonical validation;
5. run M3.1 quality;
6. iterate until at least STRONG, preferring EXCELLENT;
7. emit factory context;
8. hand source + brief + kit + context to an independent reviewer;
9. do not review the kit inside the active author context;
10. if semantic HOLD is returned, repair only source-supported findings and start a **new** independent review on the changed kit;
11. stop on PASS or unresolved source conflict.

The author never edits validators/gates to obtain PASS.

## 10. Independent reviewer skill

M3.2 adds:

`authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md`.

The reviewer is instructed to be adversarial, not helpful.

It must:

- ignore author intent and judge observable output;
- use source material as the semantic authority;
- recalculate/check answers rather than trust explanations;
- search for unsupported claims;
- search for ambiguity and answer leakage;
- challenge whether validations and transfer actually test the objective;
- check important source coverage;
- check learner brief fit;
- return only the structured semantic-review contract.

It must not repair the kit.

## 11. Minimal implementation

The implementation package after design acceptance is `ATLAS-WP-014`.

Exact product writable paths:

- `work-packages/ATLAS-WP-014.json`;
- `authoring/factory/factory_gate.py`;
- `authoring/factory/README.md`;
- `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V2.md`;
- `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md`;
- `authoring/factory/tests/test_ai_kit_factory.py`;
- `.github/workflows/atlas-m3-2-ai-kit-factory-ci.yml`.

Everything else is read-only, including:

- `contracts/**`;
- existing canonical validators;
- `authoring/v2/atlas/pedagogical_quality.py`;
- promoted authoring skill V1;
- Studio/Pages;
- learner runtime.

M3.2 intentionally has **no Studio file**.

## 12. Independent QA

Independent QA is `QA-WP-022`.

Exact QA writable paths:

- `work-packages/QA-WP-022.json`;
- `authoring/factory/tests/qa_ai_kit_factory.py`;
- `.github/workflows/atlas-m3-2-ai-kit-factory-qa.yml`.

QA is non-repairing and binds one exact frozen ATLAS-WP-014 HEAD.

Contradictory cases must include:

- stale review after one-byte kit change;
- stale review after one-byte source change;
- stale review after brief change;
- missing semantic dimension;
- unknown source evidence reference;
- reviewer independence violation;
- PASS review with major finding;
- all dimensions pass but M3.1 COMPLETE;
- M3.1 STRONG with advisory only;
- canonical-invalid otherwise positive review;
- deterministic evidence ordering/bytes;
- no writes/network;
- learner artifact unchanged.

## 13. Qualification run

Implementation + independent QA prove the machinery.

Before M3.2 promotion, perform at least two real-source qualification runs using supplied educational documents.

For each qualification:

- one clean author context;
- at least one clean independent reviewer context;
- exact source hashes;
- exact learner brief;
- final canonical kit;
- final factory evidence;
- semantic review bound to the exact final kit.

The qualification is not a deterministic CI model benchmark. It is evidence that a capable AI can use the protocol end to end.

A human gate is **not required** merely because the factory has no UI. Human intervention is required only if:

- semantic review finds unresolved source/domain uncertainty;
- the factory cannot reach PASS without distorting source content;
- a qualification reveals a product decision not frozen by this design.

## 14. Non-goals

M3.2 explicitly excludes:

- generic PDF/text/Markdown extraction pipeline;
- intermediate source-to-draft schema;
- OCR subsystem;
- embedded LLM/model API;
- model selection/routing;
- source provenance fields inside `learnit.kit.v2`;
- Studio document upload UI;
- human graphical overview debt #272;
- automatic publication;
- batch scale;
- marketplace/catalog;
- learner runtime changes;
- M3.3/M3.4;
- Gate3/Gate4/M4+.

## 15. Rollback

M3.2 is additive authoring tooling.

Rollback removes the factory gate, V2 author/reviewer skills, tests/workflow and work-package metadata.

No canonical kit, learner runtime, M3.1 engine, Studio, Pages surface or stored learner data is migrated.

## 16. Design verdict

If this design and ATLAS-WP-013 pass repository gates:

`PASS_M3_2_AI_KIT_FACTORY_DESIGN_TO_IMPLEMENTATION_GATE`

This authorizes only bounded ATLAS-WP-014 implementation and QA-WP-022 preparation.

It does not authorize M3.2 promotion, M3.3/M3.4, Gate3, Gate4 or M4+.
