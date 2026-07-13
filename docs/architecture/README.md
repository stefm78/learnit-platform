# Architecture status

## Repository authority

This directory contains the architectural preparation for Learn-it Platform. It does **not** claim that the current standalone application already implements the target architecture.

The active standalone source remains outside this repository until `ARC-WP-000` selects and imports an exact promoted candidate.

## Status of reference v1

The documents under `reference-v1/` are a **challenged architecture reference**. They provide direction, constraints, hypotheses, and migration gates. They are not yet fully normative because several package controls identified by forensic review still need to become executable repository checks.

Interpretation rules:

- current source and reconstructed evidence describe reality;
- architecture documents describe target constraints;
- a claim is not an implemented capability;
- an architecture rule becomes enforceable only when code, tests, or repository policy checks it;
- disagreements require an ADR or an explicit work package, not a silent exception.

## Current decisions

- Local-first remains the product foundation.
- The first backend topology will be a modular monolith, not microservices.
- The standalone version must stabilize before transversal player refactoring.
- Canonical identifiers, event semantics, and ownership boundaries must precede synchronization.
- Work performed by AI agents must be bounded by exact baseline, scope, tests, independent review, and controlled integration.
- Commerce and marketplace work remain on hold until synchronization and catalog distribution are proven.

## Reading order

1. `reference-v1/00_START_HERE.md`
2. `reference-v1/01_ARCHITECTURE_CONSTITUTION.md`
3. `reference-v1/02_TARGET_SYSTEM_ARCHITECTURE.md`
4. `reference-v1/04_DEPENDENCY_AND_CONTRACT_RULES.md`
5. `reference-v1/09_QUALITY_RELEASE_AND_PROVENANCE.md`
6. `reference-v1/10_MULTI_AI_DEVELOPMENT_PROTOCOL.md`
7. `reference-v1/12_ROADMAP_AND_GATES.md`
8. `../roadmap/STANDALONE_TO_PLATFORM.md`

## First gate

`ARC-WP-000` is blocked until the standalone development stream selects a candidate that is ready to become the reproducible repository baseline.
