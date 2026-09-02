# M3.3 — Portable Review Handoff / Factory Operator Orchestration

## Status

Design authority: `ATLAS-WP-018` / issue #308.

Entry baseline: main `0957a38dd51cee0c94e2e99a43521caba83f4aca`.

M3.2 AI Kit Factory is promoted. M3.2.5 Factory Reliability is promoted and qualified on a real eight-domain benchmark with `PASS_FACTORY_BENCHMARK_V1`.

This design does **not** authorize implementation.

## Why M3.3 is redefined

The historical M3.3 description — “optional LLM assistance” — is now redundant. M3.2/M3.2.5 already provide the substantive AI-authoring loop:

```text
source files + learner brief
→ author AI
→ canonical kit
→ canonical/M3.1 gates
→ author repair
→ independent semantic reviewer
→ deterministic PASS/HOLD
→ self-verifying FactoryRun
```

The real qualification exposed a different operational gap: moving a candidate from an author context to a truly independent reviewer context still requires ad hoc packaging and careful manual reconstruction.

M3.3 is therefore redefined as a **provider-neutral portable handoff layer** around the promoted factory.

It productizes transport and re-entry. It does not add new semantic truth, a model runtime or a publishing system.

## Operator contract

The target operator experience is:

```text
candidate + learner brief + admitted exact source bytes
→ PREPARE REVIEW BUNDLE
→ one portable .zip
→ independent reviewer context
→ "Review @bundle. Follow REVIEW_REQUEST.md."
→ semantic_review.json
→ CONSUME REVIEW
→ verified FactoryRun PASS/HOLD
```

For a HOLD:

```text
verified semantic review
→ unchanged findings
→ author repair context
→ new candidate/revisions/digests
→ fresh review bundle
```

A repaired candidate always requires a fresh independent review. No stale review is rebound.

## Design principles

1. **No new semantic authority.** Existing canonical validators, M3.1 quality, M3.2 review contract/factory gate and M3.2.5 reliability layer remain authoritative.
2. **No provider integration.** No OpenAI/Anthropic/local-model API, key, SDK or chat runtime.
3. **No learner-runtime change.**
4. **No repository corpus.** Review bundles are transient/exported artifacts, not committed source or generated-kit libraries.
5. **No author-context leakage.** The handoff is built from an explicit allowlist. Author scratchpad, hidden reasoning, chat logs and active author context are never inputs.
6. **Exact bytes, exact binding.** The reviewer sees the exact admitted source bytes whose hashes bind the FactoryContext.
7. **One case per bundle.** Parallelism is achieved by creating multiple independent bundles, not by multiplexing unrelated cases into one reviewer context.
8. **Filename is not identity.** `ATLAS_REVIEW_<LABEL>_<REVISION>.zip` is an operator convention only; cryptographic identity comes from canonical manifest content.
9. **Fail closed.** Any missing admission, stale target, wrong source ID, malformed review, independence violation or digest mismatch rejects re-entry.
10. **Static output only.** A PASS yields a canonical static kit plus evidence; it does not publish automatically.

## Review-handoff manifest

Introduce an external evidence schema:

`learnit.atlas.review_handoff.v1`

Profile:

`atlas.review-handoff.v1`

The manifest is evidence outside `learnit.kit.v2`.

Required logical content:

```json
{
  "schema": "learnit.atlas.review_handoff.v1",
  "profile": "atlas.review-handoff.v1",
  "factoryMain": "<40-char promoted/selected factory commit>",
  "target": {
    "contextDigest": "sha256:...",
    "kitSha256": "sha256:...",
    "sourceSetDigest": "sha256:...",
    "briefSha256": "sha256:..."
  },
  "reviewEvidenceSourceIds": ["..."],
  "independence": {
    "reviewerContextMustBeSeparate": true,
    "authorScratchpadSeenMustBe": false,
    "authorActiveContextReusedMustBe": false
  },
  "artifacts": [
    {
      "role": "candidate|learner-brief|factory-context|quality-report|source-admission|source|reviewer-skill|review-request",
      "path": "<bundle-relative path>",
      "bytes": 0,
      "sha256": "sha256:..."
    }
  ],
  "bundleDigest": "sha256:..."
}
```

Rules:

- exact fields are frozen by implementation;
- `artifacts` is sorted canonically by `path`;
- paths are POSIX-style bundle-relative paths, never host paths;
- duplicate paths are rejected;
- source IDs are unique and must match the source IDs in the embedded FactoryContext;
- `target` is copied exactly from the embedded FactoryContext;
- `bundleDigest` covers the manifest core and every declared artifact identity;
- the manifest does not contain a physical source path, user account identifier, provider identifier or conversation identifier.

## Bundle contents

A single review ZIP contains exactly the evidence needed by the independent reviewer and no author-private context.

Required files:

```text
review-handoff.json
REVIEW_REQUEST.md
SKILL_ATLAS_KIT_REVIEW_V1.md
candidate.json
learner-brief.json
factory-context.json
quality-report.json
source-admission/<source-id>.json
sources/<stable bundle filename>
```

The implementation may use subdirectories, but their exact names must be frozen by the implementation contract and covered by tests.

### Reviewer skill

`SKILL_ATLAS_KIT_REVIEW_V1.md` must be the exact repository reviewer skill blob selected by the implementation baseline. The handoff manifest binds its SHA-256.

The bundle generator must not silently summarize or rewrite the skill.

### REVIEW_REQUEST.md

The request is intentionally short and deterministic. Its semantics are:

```text
Review only the candidate in this bundle as an independent Atlas semantic reviewer.
Follow SKILL_ATLAS_KIT_REVIEW_V1.md and review-handoff.json.
Use only the supplied candidate, brief, exact sources, quality report and factory context.
Do not repair or modify anything.
Bind target exactly to the supplied factory context.
Return only learnit.atlas.semantic_review.v1 JSON.
```

The exact emitted template is frozen and regression-tested.

The operator may then use a provider-specific surface with a trivial prompt such as:

```text
Review @ATLAS_REVIEW_<LABEL>_<REVISION>.zip. Follow REVIEW_REQUEST.md.
```

That prompt is not part of the factory identity.

## Source-admission boundary

The handoff layer does not fetch or normalize sources.

For each packaged source:

- exact source bytes must already exist locally;
- the current SourceAdmission authority must accept those exact bytes/resource conditions;
- the admission evidence must be packaged and hash-bound;
- a pre-admission HOLD prevents bundle creation;
- the tool must not downgrade permission, provenance, version or content-integrity requirements.

Packaging source bytes into a user-controlled transient bundle is not authorization to commit or republish those bytes elsewhere.

## Deterministic ZIP

The portable artifact must be byte-reproducible for identical logical inputs.

Implementation must freeze:

- lexicographic member order;
- UTF-8 names;
- fixed ZIP timestamp;
- fixed permission bits;
- no archive comment;
- no host-path metadata;
- fixed compression method/level, or stored entries if cross-version reproducibility cannot otherwise be proved.

Two builds from identical inputs must have identical ZIP SHA-256.

Relocating the input files on disk must not change the manifest or ZIP.

## Prepare-review command

Implementation target:

```text
python -B authoring/factory/handoff.py prepare-review ...
```

The command must:

1. read candidate, learner brief and exact source/resource arguments;
2. verify current SourceAdmission evidence for every packaged source;
3. invoke/reuse existing canonical, M3.1 and FactoryContext authorities rather than duplicating them;
4. require canonical-valid input and an M3.1 factory-eligible quality band;
5. build the exact FactoryContext;
6. bind allowed reviewer evidence source IDs;
7. package the exact reviewer skill and deterministic request;
8. emit one deterministic ZIP;
9. emit a concise JSON result containing bundle identity and target;
10. never modify the kit, brief or source files.

It performs no network call.

## Consume-review command

Implementation target:

```text
python -B authoring/factory/handoff.py consume-review --handoff <zip> --review <semantic_review.json> ...
```

The command must:

1. verify ZIP structure and every artifact digest before trusting content;
2. reject unsafe/archive-traversal paths and undeclared extra members;
3. validate the embedded handoff manifest;
4. validate `learnit.atlas.semantic_review.v1` with the existing M3.2 review authority;
5. require exact four-hash target binding;
6. require `authorScratchpadSeen=false` and `authorActiveContextReused=false`;
7. require evidence source IDs to be among `reviewEvidenceSourceIds`;
8. preserve PASS-with-minor behavior already authorized by the M3.2 factory contract;
9. invoke the existing FactoryRun builder on the exact embedded candidate/brief/source bytes;
10. emit a self-verifying FactoryRun for both PASS and justified HOLD decisions.

The handoff layer does not re-review semantics and cannot turn a HOLD into PASS.

## HOLD repair handoff

For a verified semantic HOLD, the operator needs author-facing findings but not another semantic engine.

The implementation may emit a small machine-readable repair descriptor containing only:

- original target;
- review SHA-256;
- verdict;
- findings copied without semantic alteration;
- limitations;
- allowed source IDs.

It must not invent repairs, rewrite findings, alter source claims or mutate the candidate.

After any candidate repair, the old review and old handoff are permanently stale for the new candidate.

## Parallelization

M3.3 explicitly supports safe parallel work by **separate bundles**.

Allowed:

```text
Math V2 bundle → reviewer context A
Physics V2 bundle → reviewer context B
Medicine V3 bundle → reviewer context C
```

Not allowed:

- one reviewer context receives author hidden reasoning;
- one review target is silently rebound to another candidate;
- one multi-case bundle is treated as evidence of reviewer-context independence between cases;
- a prior review is copied into a new bundle as authority.

## Human-review debt #272

M3.3 does not implement the sequence-level graphical human overview.

That debt remains useful if routine human pedagogical approval becomes a first-class workflow. The portable handoff layer is optimized for AI-independent-review orchestration and operator simplicity.

## Security and privacy

The implementation must test:

- ZIP-slip/path traversal rejection;
- symlink-like or duplicate-member ambiguity rejection where applicable;
- undeclared member rejection;
- source hash drift;
- manifest tampering;
- skill/request tampering;
- review target drift;
- review source-ID injection;
- author independence flags set true;
- host-path leakage;
- accidental inclusion of author scratchpad/chat/log/temp files.

No secrets or credentials are packaged.

## Exact implementation boundary

If this design is accepted, the next product implementation authority is `ATLAS-WP-019`.

Writable product paths should be limited to:

- `work-packages/ATLAS-WP-019.json`
- `authoring/factory/handoff.py`
- `authoring/factory/README.md`
- `authoring/factory/tests/test_review_handoff.py`
- `.github/workflows/atlas-m3-3-review-handoff-ci.yml`

Read-only upstream authorities include:

- `authoring/factory/factory_gate.py`
- `authoring/factory/reliability.py`
- `authoring/factory/source_admission.py`
- `authoring/v2/atlas/pedagogical_quality.py`
- `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md`
- `contracts/**`
- learner runtime
- Authoring Studio

If the legacy CI router needs a new delegated route, that must be handled by a separate bounded CI work package so the product implementation does not silently expand scope.

## Independent QA boundary

Use a disjoint QA authority, expected `QA-WP-023`, limited to QA-owned files such as:

- `work-packages/QA-WP-023.json`
- `authoring/factory/tests/qa_review_handoff.py`
- `.github/workflows/atlas-m3-3-review-handoff-qa.yml`

QA must not repair product files.

## Implementation exit evidence

Before M3.3 promotion, prove at minimum:

- exact implementation path scope;
- existing M3.2 and M3.2.5 regression suites remain green;
- deterministic ZIP byte identity across two builds;
- relocation of input files does not change bundle identity;
- source admission HOLD prevents packaging;
- source byte drift is detected;
- author scratchpad/context cannot enter through the declared interface;
- exact reviewer skill identity is packaged;
- stale/mismatched reviews fail closed;
- PASS review produces a self-verifying PASS FactoryRun;
- justified HOLD review produces a self-verifying HOLD FactoryRun;
- minor-only finding remains compatible with existing PASS semantics;
- duplicate/unsafe/undeclared ZIP members fail closed;
- no network access;
- no input mutation;
- no learner artifact change.

Qualification should exercise at least two real portable handoffs from separate reviewer contexts, including one PASS path and one HOLD path.

## Human gate

No human gate is required for implementation or independent QA of the deterministic handoff mechanism.

A human gate is required only if a later increment turns this into a human-first authoring/review UI or changes publication behavior.

## Non-goals

- model/provider integration;
- chat UI;
- model selection;
- source ingestion/OCR;
- automatic semantic repair;
- automatic publication;
- source/kit corpus in Git;
- canonical kit schema change;
- learner runtime change;
- human graphical sequence overview;
- M3.4 scale/publishing;
- Gate3/Gate4/M4+.

## Design verdict

`PASS_M3_3_PORTABLE_REVIEW_HANDOFF_DESIGN_TO_IMPLEMENTATION_GATE`

Subject to exact two-file design scope, Repository governance PASS and PR scope PASS.
