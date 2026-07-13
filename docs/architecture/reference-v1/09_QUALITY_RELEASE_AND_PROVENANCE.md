# Quality, release, and provenance

## 1. Evidence model

Every material assertion must be classified as one of:

- **evidence** — reproduced, observed, or independently verified;
- **claim** — stated by a document, tool, or author but not independently reproduced;
- **assumption** — accepted temporarily for planning;
- **absence of evidence** — no reliable basis to conclude.

A passing test proves only the exercised behavior, artifact, environment, and data set.

## 2. Release identity chain

A release candidate must record:

```text
source commit
+ dependency lock identity
+ contract identity
+ migration identity
+ build command and environment
+ test suite identity
+ built artifact hash
+ package manifest hash
+ published artifact hash
```

The required invariant is:

```text
reviewed source
   produces
built artifact
   equals
artifact under test
   equals
artifact published
```

A package process must fail if the source changes after build or if the candidate artifact differs from the tested artifact.

## 3. Manifest requirements

A release manifest must verify:

- every declared file exists;
- every declared file hash matches;
- no undeclared extra file exists;
- canonical paths are normalized;
- duplicate paths are rejected;
- the manifest root is externally anchored by a signed commit, attestation, or equivalent trusted provenance mechanism.

A hash file stored beside an archive detects accidental corruption but is not, by itself, proof against coordinated replacement of both files.

## 4. Build requirements

A promoted standalone or platform candidate must be built:

- from a clean checkout;
- using declared tool versions;
- with locked dependencies where dependencies exist;
- without untracked source inputs;
- with deterministic or explained output differences;
- before tests and packaging;
- without subsequent source mutation.

## 5. Test layers

### Static and contract checks

- syntax and schema validation;
- contract compatibility;
- module-boundary checks;
- work-package scope checks;
- secret and forbidden-file checks;
- dependency and license checks when dependencies exist.

### Unit tests

- pure domain rules;
- identifiers and versioning;
- projections;
- migration decisions;
- entitlement behavior;
- idempotence.

### Integration tests

- persistence transactions;
- import/export;
- build and package chain;
- API and database boundaries;
- storage and media behavior.

### Browser and device tests

- navigation and scroll;
- all activity types;
- responsive rendering;
- keyboard and touch alternatives;
- persistence across restart;
- offline behavior;
- representative target devices.

### Adversarial tests

- duplicate delivery;
- out-of-order events;
- false clocks;
- interrupted import or migration;
- stale client;
- tenant-crossing attempts;
- webhook replay;
- undeclared package file;
- source mutation after build;
- backup restoration.

## 6. Human gates

Automation does not replace human review for:

- perceived scroll and gesture quality;
- information density and comprehensibility;
- accessibility with real interaction;
- pedagogical interpretation;
- confidence and trust signals;
- ambiguous recovery or conflict states.

A candidate can be automation-ready while still remaining unpromoted.

## 7. RC, tag, and release discipline

- A commit is a technical change.
- A tag marks a candidate submitted to a meaningful gate.
- A GitHub Release is reserved for a human-test candidate, promoted baseline, handover, or distributed version.
- Hundreds of internal micro-changes should not become hundreds of heavyweight releases.

## 8. Baseline gate

The first repository application baseline requires:

- exact source import without refactor;
- successful clean rebuild;
- comparison with the promoted local artifact;
- complete required test run;
- human validation record;
- known-issues register;
- source and artifact hashes;
- rollback path.

Only after that gate may a refactoring claim behavioral equivalence to an accepted baseline.
