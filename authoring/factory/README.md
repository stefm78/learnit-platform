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
- distinct source-content digests for distinct benchmark cases, so one source cannot be relabelled into several domains;
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

## M3.3 portable review handoff

M3.3 does not add a model API. It turns the already-promoted author/reviewer boundary into one deterministic portable artifact.

Prepare one independent-review bundle:

```bash
python -B authoring/factory/handoff.py prepare-review \
  --kit candidate.json \
  --brief learner-brief.json \
  --source cours=./cours.pdf \
  --admission cours=./cours.source-admission.json \
  --out ATLAS_REVIEW_COURS_V1.zip
```

The `--admission` input accepts one of two explicit authorities:

- existing curated benchmark `PASS_SOURCE_ADMISSION_V1`, replayed against the frozen benchmark catalog and exact source bytes;
- `PASS_TRANSIENT_SOURCE_ADMISSION_V1` for a user-provided source used only for private personal learning, with transient-only retention and source redistribution prohibited.

The transient path is deliberately separate from the benchmark catalog. A transient PASS does **not** mean Learn-it verified copyright, ownership, licence or redistribution rights. It means the required user declaration and private/transient processing context are explicit and the exact caller-bound source bytes/version are hash-bound.

For end-to-end compatibility, transient `sourceId` is a deliberately narrower subset of the promoted M3.2/M3.3 source identity grammar: `[A-Za-z0-9][A-Za-z0-9._-]{0,159}`. The 160-character cap keeps the sourceId-derived temporary/archive filename components below the common 255-byte component limit. Identifiers outside that grammar (for example `user:private-course`) and overlong identifiers are rejected before admission so a transient PASS cannot later fail only at the M3.3 boundary.

Create a transient declaration:

```json
{
  "schema": "learnit.atlas.transient_source_declaration.v1",
  "profile": "atlas.user-provided-private-learning.v1",
  "declarationVersion": "learnit.private-source-user-declaration.v1",
  "sourceId": "cours",
  "version": "2026-09",
  "provenance": "user-provided",
  "processingContext": "private-personal-learning",
  "authorizationBasis": "user-declaration",
  "userDeclarationAccepted": true,
  "retention": "transient-only",
  "redistribution": "prohibited",
  "legalRightsVerified": false
}
```

Bind that declaration to the exact source bytes:

```bash
python -B authoring/factory/transient_source_admission.py admit \
  --declaration cours.transient-declaration.json \
  --file ./cours.pdf \
  > cours.source-admission.json
```

The source bytes may exist in the caller workspace, the temporary review ZIP and the reviewer workspace while processing is active. This authority introduces no persistent source catalog, repository corpus or durable source store. Durable factory evidence may retain only non-reconstructive source identity such as sourceId, version, byte count and SHA-256 plus the declaration/admission record.

A bundle contains one case only:

```text
review-handoff.json
REVIEW_REQUEST.md
SKILL_ATLAS_KIT_REVIEW_V1.md
candidate.json
learner-brief.json
factory-context.json
quality-report.json
source-catalog.json                 # present only when a benchmark SourceAdmission is used
source-admission/<source-id>.json    # benchmark or transient admission
sources/<source-id>.<deterministic-extension>
```

The ZIP is byte-deterministic for identical logical inputs and does not contain host paths, author scratchpad, chat logs or active author context.

The intended operator prompt can remain trivial:

```text
Review @ATLAS_REVIEW_COURS_V1.zip. Follow REVIEW_REQUEST.md.
```

Verify a received handoff before using it:

```bash
python -B authoring/factory/handoff.py verify-review \
  --handoff ATLAS_REVIEW_COURS_V1.zip
```

Consume an independent semantic review:

```bash
python -B authoring/factory/handoff.py consume-review \
  --handoff ATLAS_REVIEW_COURS_V1.zip \
  --review semantic-review.json \
  --run-out factory-run.json
```

Review re-entry fails closed on archive tampering, unsafe/duplicate/undeclared members, source/admission drift, stale target hashes, unknown evidence source IDs or reviewer independence declarations that are not `false/false`.

A valid semantic PASS produces a self-verifying PASS FactoryRun. A justified semantic HOLD produces a self-verifying HOLD FactoryRun. Minor-only findings preserve the already-authorized M3.2 PASS semantics.

The handoff layer does not repair kits, choose a model, publish content, change `learnit.kit.v2`, or run inside the learner.


## M3.4 qualified release sets

M3.4 is a local deterministic scale/release layer, not a remote publishing system.

Build one immutable qualified release set from already self-verifying PASS FactoryRuns and their exact canonical kits:

\`\`\`bash
python -B authoring/factory/release_set.py build \
  --entry ./runs/math.json=./kits/math.json \
  --entry ./runs/physics.json=./kits/physics.json \
  --out LEARNIT_RELEASE_SET.zip
\`\`\`

Verify the portable artifact offline:

\`\`\`bash
python -B authoring/factory/release_set.py verify \
  --release LEARNIT_RELEASE_SET.zip
\`\`\`

The release ZIP contains only:

\`\`\`text
release-set.json
kits/<package-lineage-id>/<package-revision-id>.json
factory-runs/<run-id-hex>.json
\`\`\`

Admission is fail-closed:

- every FactoryRun must self-verify and have a PASS factory decision;
- exact kit bytes must match the run's \`generatedKit.sha256\`;
- canonical Atlas identity/revision digests must validate;
- one package lineage may appear only once in a release set;
- a revision ID reused with a different digest across the set is rejected;
- archive traversal, duplicate/extra members and tampering are rejected.

Release identity and ZIP bytes are deterministic across input ordering and host-path relocation.

Rollback is intentionally simple: keep immutable release ZIPs and select a previously verified \`releaseSetId\`. M3.4 does not mutate a deployment pointer or publish remotely.

Scale-100/Scale-500 tests are engineering fixtures only. They prove deterministic release-set mechanics, not semantic qualification of 100/500 real kits.

Release-set verification proves deterministic internal integrity and exact binding to the supplied self-verifying FactoryRuns. Before release admission, M3.4 also fails closed if a self-verifying FactoryRun's embedded factory evidence contradicts an exact factory PASS: canonical evidence must be true, pedagogical quality must be STRONG/EXCELLENT_BY_PROFILE, semantic review must be PASS, and blocking/major semantic finding counts must be zero. Offline verification additionally requires `release-set.json` to be the exact canonical JSON byte representation, not merely a semantically equivalent JSON object.

The release ZIP is not cryptographically signed and does not authenticate a third-party publisher or origin. Any future origin-signing or remote-distribution trust model requires a separate gate.
