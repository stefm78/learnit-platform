# Atlas M3.2 AI Kit Factory

The AI Kit Factory is a **manufacturing contract**, not a model runtime.

A capable AI reads supplied learning sources directly. Learn-it code gates the resulting kit.

```text
source files + learner brief
→ author AI
→ learnit.kit.v2
→ canonical validation
→ M3.1 pedagogical quality
→ independent semantic reviewer
→ deterministic factory gate
→ PASS_AI_KIT_FACTORY_V1 or HOLD
```

M3.2 deliberately does **not** add PDF extraction, OCR, a Source-to-Draft schema, model-provider integration, a backend, Studio upload UI, or learner-runtime AI.

## Files

- `factory_gate.py` — deterministic context and final gate;
- `../skills/SKILL_ATLAS_KIT_AUTHORING_V2.md` — author role;
- `../skills/SKILL_ATLAS_KIT_REVIEW_V1.md` — independent adversarial reviewer role.

Existing canonical authorities remain upstream:

- `contracts/learnit-kit-v2.schema.json`
- `authoring/v2/validate_kit.py`
- `authoring/v2/atlas/validate_atlas_content.py`
- `authoring/v2/atlas/pedagogical_quality.py`

## Learner brief

Example:

```json
{
  "schema": "learnit.atlas.learner_brief.v1",
  "audience": "2e année école d'ingénieur",
  "goal": "Comprendre et savoir utiliser les notions du document",
  "language": "fr",
  "timeBudgetMinutes": 45
}
```

Required fields are `schema`, `audience`, `goal`, `language` and a positive integer `timeBudgetMinutes`.

This brief is authoring context only. It is not added to `learnit.kit.v2`.

## Bind exact inputs

The reviewer must review the **exact** source/brief/kit combination.

Generate the context:

```bash
python -B authoring/factory/factory_gate.py context \
  --kit candidate.json \
  --brief learner-brief.json \
  --source cours=./cours.pdf \
  --source notes=./notes.md \
  > factory-context.json
```

The context contains only source IDs, byte lengths and hashes. Host file paths are not emitted.

Changing one source byte, the learner brief, or the kit changes the context digest and makes a previous semantic review stale.

## Semantic review

The reviewer returns exactly:

`learnit.atlas.semantic_review.v1`

Required dimensions:

- `sourceFidelity`
- `answerCorrectness`
- `ambiguity`
- `objectiveCoverage`
- `validationTransfer`
- `learnerFit`

Each dimension has:

```json
{
  "status": "pass",
  "summary": "What was checked and why the result is acceptable.",
  "evidence": [
    {
      "sourceId": "cours",
      "locator": "p. 12",
      "basis": "The source states the relation used by this activity."
    }
  ]
}
```

Evidence is mandatory for source fidelity, answer correctness, objective coverage and validation/transfer.

Review top-level example:

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
  "dimensions": {
    "sourceFidelity": {"status": "pass", "summary": "...", "evidence": []},
    "answerCorrectness": {"status": "pass", "summary": "...", "evidence": []},
    "ambiguity": {"status": "pass", "summary": "...", "evidence": []},
    "objectiveCoverage": {"status": "pass", "summary": "...", "evidence": []},
    "validationTransfer": {"status": "pass", "summary": "...", "evidence": []},
    "learnerFit": {"status": "pass", "summary": "...", "evidence": []}
  },
  "findings": [],
  "limitations": [],
  "verdict": "PASS_SEMANTIC_REVIEW_V1"
}
```

The abbreviated example above omits the mandatory evidence content in the four evidence-required dimensions; real reports must include it.

Finding severities are `blocking`, `major`, `minor` and `advice`.

A factory PASS permits only minor/advice findings.

## Run the final gate

```bash
python -B authoring/factory/factory_gate.py gate \
  --kit candidate.json \
  --brief learner-brief.json \
  --review semantic-review.json \
  --source cours=./cours.pdf \
  --source notes=./notes.md \
  --json
```

Exit classes:

- `0` — `PASS_AI_KIT_FACTORY_V1`
- `2` — canonical invalid
- `3` — M3.1 structural quality below STRONG
- `4` — malformed/unreadable factory input
- `5` — stale/mismatched review binding
- `6` — semantic review HOLD

Factory structural PASS requires M3.1 `STRONG` or `EXCELLENT_BY_PROFILE`.

`COMPLETE` is a HOLD because it still contains one or more deterministic warnings.

`STRONG` may pass with advisory diagnostics: a source must never be distorted merely to eliminate an advisory.

## Independence boundary

The semantic reviewer must not receive:

- the author AI's hidden reasoning;
- the author's active conversation/context.

A different model is useful but not required in v1. A clean reviewer context is required.

The deterministic code can verify the review declaration and its exact file binding. It cannot prove that the reviewer told the truth about semantic content or context isolation.

## Meaning of PASS

`PASS_AI_KIT_FACTORY_V1` means:

- canonical kit authorities pass;
- M3.1 structural quality is STRONG or EXCELLENT;
- the exact source/brief/kit combination has an independently declared semantic review;
- every required semantic dimension passes;
- no blocking/major semantic finding remains.

It does **not** prove learner mastery, retention, certification or educational effectiveness.

## Iteration

If the gate returns HOLD:

1. author AI repairs only source-supported issues;
2. canonical identities/digests are regenerated as required;
3. deterministic gates are rerun;
4. because the kit changed, the previous semantic review is stale;
5. a new independent reviewer context reviews the new exact kit;
6. repeat until PASS or an unresolved source limitation is reported.

The factory never edits the kit automatically and never weakens a validator to obtain PASS.

## M3.2.5 reliability layer

M3.2.5 composes around the promoted M3.2 gate. It does not replace or weaken `factory_gate.py`.

A source used in a reliability run has a logical identity:

```text
resourceId + version + sha256
```

The physical path is only a local resolver input and is never emitted in a `FactoryRun` or evidence bundle. Moving the same bytes to another storage location therefore does not change the emitted run, while changing the logical resource version does change the M3.2.5 run identity.

Create a deterministic run:

```bash
python -B authoring/factory/reliability.py run \
  --kit candidate.json \
  --brief learner-brief.json \
  --review semantic-review.json \
  --resource cours@2026-01=./cours.pdf \
  > factory-run.json
```

Verify a stored run without the original host paths:

```bash
python -B authoring/factory/reliability.py verify-run \
  --run factory-run.json
```

A `FactoryRun` is a path-free manifest binding:

```text
resources
+ learner brief
+ generated kit
+ deterministic validators
+ semantic review
+ M3.2 factory evidence
+ final PASS/HOLD decision
→ self-verifying evidence bundle
→ deterministic runId
```

The run manifest does not store source documents, generated-kit libraries or large media payloads. Those may live outside Git; their logical identity remains stable through `resourceId + version + sha256`.

### Benchmark gate

The executable benchmark policy is `benchmark_contract.json`. The v1 contract requires:

- mathematics;
- physics;
- computer science;
- history;
- law;
- medicine;
- literature;
- management;
- at least eight distinct FactoryRuns;
- at least two PASS runs;
- at least two justified HOLD runs;
- human escalation on no more than 25% of runs.

A corpus that only produces PASS is therefore not considered a reliability proof.

Benchmark manifest:

```json
{
  "schema": "learnit.atlas.factory_benchmark_manifest.v1",
  "cases": [
    {
      "caseId": "math-001",
      "domain": "mathematics",
      "run": "/evidence/math-001.factory-run.json",
      "expectedDecision": "PASS",
      "humanEscalation": false
    }
  ]
}
```

The manifest path is operational input; emitted benchmark reports contain case IDs and run IDs, not host paths.

Run the benchmark:

```bash
python -B authoring/factory/reliability.py benchmark \
  --manifest benchmark-manifest.json
```

M3.2.5 does not authorize source ingestion, OCR, model-provider integration, automatic publishing, learner-runtime AI, M3.3, M3.4, Gate3 or Gate4.

