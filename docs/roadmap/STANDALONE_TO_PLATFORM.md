# Standalone-to-platform roadmap

## Governing rule

Do not transform the active player while the standalone product is still being stabilized. Prepare the future platform around it, then migrate through small seams after a promoted standalone baseline exists.

## Track A — standalone stabilization

Allowed before the platform baseline:

- functional and UX corrections;
- accessibility;
- scroll, navigation, drag-and-drop, and responsive behavior;
- local persistence and import/export robustness;
- kit compatibility;
- performance;
- regression tests;
- reproducible release and provenance.

Held until baseline promotion:

- backend;
- accounts and profiles;
- cloud synchronization;
- commerce and marketplace;
- global identifier rewrite;
- transversal storage migration;
- large-scale player reorganization.

## Track B — platform readiness

Safe parallel work before baseline promotion:

- repository governance and CI;
- exact architecture claims and open decisions;
- read-only code cartography when source is available;
- black-box behavioral tests;
- migration scenarios;
- canonical work-package format;
- release and evidence controls.

## Gates

### R0 — repository foundation

- private repository initialized;
- pull-request contract present;
- governance validator executable;
- architecture reference clearly marked as target, not current implementation;
- canonical `ARC-WP-000` present.

### R1 — standalone candidate selected

- human promotion gate passed;
- candidate source identified exactly;
- source and artifact hashes captured;
- known-issues register frozen.

### R2 — forensic baseline imported

- source imported without refactor;
- clean checkout rebuild succeeds;
- rebuilt artifact is compared with the promoted candidate;
- automated and human evidence is attached;
- source-to-build-to-test-to-package provenance is demonstrated.

### R3 — black-box protection

- representative kits and user journeys are captured as regression fixtures;
- persistence, import/export, recovery, and activity behavior are reproducible;
- performance baselines exist on target devices.

### R4 — first architectural seam

Encapsulate one legacy storage boundary behind a narrow interface without changing storage technology, data shape, UI, or behavior.

### R5 — controlled AI parallelism pilot

Run one implementation agent, one independent adversarial QA agent, and one integrator on disjoint scopes. No broad multi-feature parallel development yet.

### R6 — canonical identities and local event model

Introduce stable content and learner identifiers, immutable learning events, derived projections, and explicit migration rules.

### R7 — IndexedDB and local outbox

Migrate behind existing interfaces with crash recovery, rollback, and data-equivalence proof.

### R8 — synchronization simulator

Prove idempotence, deduplication, reordering, clock skew, partitions, and deterministic convergence with two simulated devices.

### R9 — modular backend alpha

Add identity, profiles, progress synchronization, and a free catalog in one modular monolith with tenant-isolation tests and operational evidence.

### R10 — distribution, commerce, institutions

Proceed in this order only after prior gates pass:

1. free remote catalog;
2. first-party purchases and entitlements;
3. simple institutional licensing;
4. invited publishers;
5. open marketplace only on demonstrated demand and operational maturity.

## Release discipline

- A commit or pull request is not automatically a release candidate.
- Tag only artifacts submitted to a meaningful test gate.
- Create a GitHub Release for human candidates, promoted baselines, handovers, or distributed versions.
- Never publish an artifact different from the artifact tested.
