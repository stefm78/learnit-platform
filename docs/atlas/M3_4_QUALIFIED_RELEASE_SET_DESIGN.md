# M3.4 — Qualified Release Set / Scale Pack Design

## Status

Design authority: `ATLAS-WP-020` / issue #320.

Entry baseline: main `3b02ef988e978fb47eafc20241387a3ce59e8596`.

Upstream promoted capabilities:

- M3.2 AI Kit Factory;
- M3.2.5 Factory Reliability;
- M3.3 Portable Review Handoff, promotion merge `c102ca81f3b144bea1140860ef633a0d01987d59`.

This design does **not** authorize implementation.

## Arbitration result

Historical M3.4 combined six ideas:

1. batch validation;
2. asset handling;
3. collision diagnostics;
4. rollback;
5. 100/500-kit scale evidence;
6. publishing.

The challenge rejects that bundle as too broad.

### Accepted now

- **batch release qualification** of already independently qualified kits;
- **release-level collision diagnostics**;
- **deterministic immutable release sets**;
- **rollback by selecting a prior immutable release set**;
- **100/500-kit engineering scale evidence**.

### Deferred/rejected now

- **asset/media handling** — `learnit.kit.v2` has no current asset model; adding one would be a contract/product expansion unrelated to the immediate operator pain;
- **remote publishing** — no GitHub Release write, catalog, object store, backend or repository-write effect is required to solve the current problem;
- **source/review repackaging** — M3.2.5 FactoryRun already binds the evidence chain; M3.4 must not become another evidence corpus;
- **semantic batch review** — M3.4 consumes self-verifying FactoryRuns and does not replace independent semantic review.

## Why this is now useful

M3.3 solved one candidate → one independent reviewer handoff.

At scale, the remaining operator problem is different:

> Given many independently reviewed candidate outputs, which exact qualified kit revisions belong to the next distributable set, and can that set be proven deterministic, collision-free and reversible before any remote publication exists?

The current system can answer whether one FactoryRun is valid. It cannot yet produce one deterministic release-level identity over many PASS kits or reject cross-kit identity conflicts before distribution.

M3.4 is therefore redefined as **Qualified Release Set / Scale Pack**, not a publishing platform.

## Target operator flow

```text
many exact kit.json files
+ corresponding self-verifying FactoryRun.json files
→ BUILD QUALIFIED RELEASE SET
→ verify every FactoryRun
→ require PASS
→ bind each FactoryRun to exact kit bytes
→ canonical kit validation for identity/digest trust
→ cross-kit collision analysis
→ deterministic release-set manifest
→ deterministic portable release ZIP

release ZIP
→ VERIFY RELEASE SET
→ exact releaseSetId + entries + diagnostics
```

No network call is required.

## New evidence schema

External evidence schema:

`learnit.atlas.qualified_release_set.v1`

Profile:

`atlas.qualified-release-set.v1`

The release-set manifest is outside `learnit.kit.v2`.

Target shape:

```json
{
  "schema": "learnit.atlas.qualified_release_set.v1",
  "profile": "atlas.qualified-release-set.v1",
  "factoryAuthority": "<exact promoted factory/reliability implementation identity>",
  "entries": [
    {
      "packageLineageId": "<uuid>",
      "packageRevisionId": "<uuid>",
      "packageRevisionDigest": "sha256:...",
      "title": "...",
      "versionLabel": "...",
      "language": "fr",
      "kit": {
        "bytes": 0,
        "sha256": "sha256:..."
      },
      "factoryRun": {
        "runId": "sha256:...",
        "bytes": 0,
        "sha256": "sha256:...",
        "factoryContextDigest": "sha256:..."
      }
    }
  ],
  "metrics": {
    "packages": 0,
    "courses": 0,
    "activities": 0
  },
  "releaseSetId": "sha256:..."
}
```

Exact implementation fields may be tightened but not expanded semantically without returning to the authority issue.

Rules:

- entries are sorted canonically by `packageLineageId`;
- one `packageLineageId` appears at most once in one release set;
- `releaseSetId` is the SHA-256 of the canonical manifest core excluding itself;
- titles/version labels are display metadata copied from the exact kit, never identity authorities;
- physical input paths never enter the emitted manifest;
- no source PDF, learner brief, semantic review file, admission record, chat context or provider identity enters the release ZIP.

## Input boundary

The implementation may accept repeated CLI bindings or a local build-request JSON containing physical run/kit paths.

Any build-request path file is operator-local input only:

- it is not emitted;
- it is not part of release identity;
- relocating identical input bytes must not change the release output;
- duplicate logical entries fail closed.

## Per-entry acceptance

For each proposed release entry:

1. read the exact FactoryRun;
2. verify it using the promoted M3.2.5 `verify_run` authority;
3. require decision class `PASS`;
4. read exact kit bytes;
5. require kit SHA-256 to equal `evidenceBundle.artifacts.generatedKit.sha256`;
6. parse and run existing canonical kit/Atlas validators sufficiently to trust declared revision IDs and digests;
7. require package lineage/revision/digest copied into the release manifest to equal the exact kit;
8. emit no semantic reinterpretation.

A HOLD FactoryRun can be retained as factory evidence elsewhere but cannot enter a qualified release set.

## Cross-kit collision contract

M3.4 adds release-level diagnostics without changing canonical identity semantics.

### Hard HOLD

- duplicate release entry;
- same `packageLineageId` with more than one package revision in the same release set;
- same `packageRevisionId` with different digest or exact kit SHA;
- any package/course/activity **revision ID** reused with a different revision digest anywhere in the release set;
- same output archive member path claimed by different logical entries;
- malformed or unverifiable FactoryRun;
- kit/run hash mismatch;
- canonical kit validation failure.

### Allowed

- homonymous titles with distinct canonical identities;
- different package lineages with similar or identical display labels;
- same revision ID + same digest encountered through internally repeated references only where canonical kit semantics already allow it.

M3.4 must not invent title-based, filename-based or path-based identity.

## Portable release ZIP

One deterministic archive contains exactly:

```text
release-set.json
kits/<package-lineage-id>/<package-revision-id>.json
factory-runs/<run-id-hex>.json
```

Rules follow M3.3 deterministic archive discipline:

- lexicographic member order;
- UTF-8 names;
- fixed timestamp;
- fixed permission bits;
- no archive comment;
- no host metadata;
- fixed compression behavior;
- unsafe, duplicate or undeclared members rejected.

Two builds from identical logical bytes must have identical ZIP SHA-256.

Input order and host relocation must not change bytes.

## Rollback semantics

M3.4 does **not** implement mutable deployment rollback.

Every release set is immutable and content-addressed.

Rollback means:

```text
current releaseSetId B
→ operator selects previously verified releaseSetId A
→ distribute/use A again
```

No kit is rewritten, no release history is mutated and no learner state is migrated.

A future remote distribution layer may maintain an active pointer, but that is outside M3.4.

## Scale evidence

M3.4 implementation must exercise two explicit engineering scale profiles:

### Scale-100

- 100 distinct package entries;
- deterministic build twice;
- order permutation;
- host-path relocation;
- verify resulting ZIP;
- inject at least one collision/HOLD negative case.

### Scale-500

- 500 distinct package entries;
- deterministic build twice;
- order permutation;
- verify resulting ZIP;
- demonstrate no recursion/exponential work or per-entry subprocess fan-out;
- CI job completes within its bounded timeout.

The fixtures may be synthetic deterministic engineering fixtures.

The evidence MUST state:

> Scale fixtures prove release-set engineering behavior only. They do not represent 100/500 independently semantically qualified real kits and do not extend M3.2.5 pedagogical claims.

Wall-clock measurements may be recorded, but no narrow machine-dependent latency SLO is introduced in this milestone.

## Asset decision

Asset/media handling is **deferred**.

Reason:

- current `learnit.kit.v2` contains no canonical asset contract;
- adding assets would require rights, digest, packaging and learner-runtime decisions;
- release-set composition provides current value without those changes.

If assets become a product requirement, they require a separate contract/design gate.

## Publishing decision

Remote publishing is **deferred**.

M3.4 creates a portable verified release artifact. It does not:

- create a GitHub Release;
- push to a branch;
- upload to object storage;
- mutate GitHub Pages;
- create a catalog;
- activate Gate 3 repository-write capability.

This keeps "tested artifact = distributed candidate artifact" possible without prematurely choosing a distribution backend.

## Security/privacy

The release builder/verifier must reject:

- ZIP traversal/backslash/duplicate-member ambiguity;
- undeclared archive members;
- symlinks or non-regular members where applicable;
- tampered manifest, kit or FactoryRun;
- absolute/host path leakage;
- HOLD FactoryRun injection;
- FactoryRun decision tampering;
- kit hash mismatch;
- identity/digest collisions.

No credentials or source documents are packaged.

## Implementation boundary if accepted

Expected implementation authority: `ATLAS-WP-021`.

Writable product paths should be limited to:

- `work-packages/ATLAS-WP-021.json`
- `authoring/factory/release_set.py`
- `authoring/factory/README.md`
- `authoring/factory/tests/test_release_set.py`
- `.github/workflows/atlas-m3-4-release-set-ci.yml`

Read-only upstream authorities:

- `authoring/factory/factory_gate.py`;
- `authoring/factory/reliability.py`;
- `authoring/factory/handoff.py`;
- `authoring/v2/validate_kit.py`;
- `authoring/v2/atlas/validate_atlas_content.py`;
- `contracts/learnit-kit-v2.schema.json`;
- learner runtime;
- Authoring Studio.

Any shared CI-router change remains a separate bounded CI work package.

## Independent QA

Expected independent QA: `QA-WP-024`.

Disjoint QA paths:

- `work-packages/QA-WP-024.json`
- `authoring/factory/tests/qa_release_set.py`
- `.github/workflows/atlas-m3-4-release-set-qa.yml`

QA may attack product output but may not repair `release_set.py`.

## Implementation exit evidence

Before M3.4 promotion, prove:

- exact five-path product delta;
- upstream M3.2/M3.2.5/M3.3 regressions green;
- PASS-only release admission;
- exact kit ↔ FactoryRun binding;
- release-set canonical ordering and path independence;
- deterministic ZIP byte identity;
- hard revision collision rejection;
- duplicate package-lineage rejection;
- archive tamper/traversal/extra-member rejection;
- Scale-100 PASS;
- Scale-500 PASS;
- synthetic scale evidence labelled honestly;
- prior release ZIP remains independently verifiable after a newer release ZIP exists;
- no network/repository write;
- no source/review/private-context payload;
- no learner artifact change;
- independent contradictory QA bound to one frozen product head.

## Human gate

No human gate is required for the deterministic local release-set mechanism.

A human/product gate becomes mandatory before any increment introduces:

- automatic or remote publishing;
- a human-first catalog/distribution UX;
- a new asset/media contract;
- rights/licensing policy beyond existing source-admission evidence.

## Next gate

M3.4 does not pre-authorize a remote distribution milestone.

After M3.4 qualification, fresh arbitration must compare at least:

- controlled remote distribution/publishing;
- human pedagogical overview debt #272;
- further factory/operator automation;
- or stopping because the current local/static workflow is sufficient.

Gate 3, Gate 4 and M4+ remain HOLD.

## Design verdict

`PASS_M3_4_QUALIFIED_RELEASE_SET_DESIGN_TO_IMPLEMENTATION_GATE`

The historical M3.4 milestone is therefore **REDEFINED**, not kept intact.
