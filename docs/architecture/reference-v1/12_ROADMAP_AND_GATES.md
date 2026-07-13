# Architecture roadmap and gates

This roadmap is gated by evidence, not calendar dates. Later stages remain blocked until earlier gates pass.

## Phase 0 — standalone promotion

### Objective

Obtain a user-validated, reproducible standalone candidate.

### Required proof

- essential journeys pass;
- no blocking scroll, navigation, activity, persistence, or import defect;
- representative mobile and desktop human tests pass;
- build and package provenance are reconstructed;
- known limitations are explicit.

### Gate

A selected standalone candidate is named and frozen for `ARC-WP-000`.

## Phase 1 — repository baseline

### Objective

Import the exact standalone source and evidence without behavior change.

### Gate

A clean repository checkout reproduces the accepted artifact or explains every byte-level difference. The tested artifact equals the proposed release artifact.

## Phase 2 — behavioral protection

### Objective

Capture black-box tests for:

- library and course selection;
- session start, resume, exit, and completion;
- every activity family;
- progress and bilan;
- import/export and recovery;
- large kits and media;
- offline restart.

### Gate

A future refactor can be compared against stable observable behavior and data fixtures.

## Phase 3 — first seam

### Objective

Encapsulate one legacy persistence boundary behind a narrow port while retaining the current storage implementation.

### Gate

Behavior and stored data remain equivalent; rollback is a simple revert.

## Phase 4 — canonical identity foundation

### Objective

Introduce stable identifiers and content lineage for package, version, course, objective, activity, and revision.

### Gate

Renaming a title does not orphan progress. Homonymous kits do not collide. Compatibility decisions are explicit.

## Phase 5 — local event model

### Objective

Record immutable, idempotent learning events and derive projections.

### Gate

The same fact set deterministically reconstructs the same projection. Duplicate input does not duplicate learning evidence.

## Phase 6 — transactional local storage

### Objective

Move behind existing ports to structured transactional storage with migrations, crash recovery, and outbound intents.

### Gate

Fault injection at each write boundary produces no corrupt or partially committed learner state.

## Phase 7 — synchronization simulator

### Objective

Simulate two devices and a server protocol before deploying a real backend.

### Gate

No attempt is lost or counted twice under duplicate delivery, reordering, network partition, clock skew, stale clients, and replay.

## Phase 8 — security and tenancy foundation

### Objective

Define accounts, learner profiles, organizations, devices, authorization, retention, export, and deletion.

### Gate

Negative tests demonstrate that one principal cannot read, modify, or infer another tenant's protected data.

## Phase 9 — backend alpha

### Objective

Deploy a modular-monolith backend for identity, learner profiles, progress synchronization, and free catalog distribution.

### Gate

Backup restoration, observability, device recovery, tenant isolation, and end-to-end synchronization pass.

## Phase 10 — remote catalog

### Objective

Distribute signed or hashed immutable kit versions with atomic installation, update, rollback, and compatibility checks.

### Gate

Interrupted downloads and incompatible updates do not corrupt installed content or learner progress.

## Phase 11 — first-party commerce

### Objective

Add one-time purchases, grants, refunds, entitlement recovery, and explicit offline grace behavior.

### Gate

Webhook replay, retry, refund, and restoration tests do not create duplicate orders or inconsistent rights.

## Phase 12 — institutions

### Objective

Add organizations, cohorts, seats, assignments, and privacy-separated institutional evidence.

### Gate

A pilot demonstrates useful pedagogical action without exposing unrelated private learning behavior.

## Phase 13 — controlled publishing

### Objective

Invite selected publishers through schema, media, security, pedagogical, accessibility, rights, and human-review gates.

### Gate

Operational support, content quality, rights management, and demand justify expansion.

## Phase 14 — open marketplace decision

This is a decision gate, not an assumed destination.

Proceed only when:

- repeated purchase demand is demonstrated;
- catalog quality and support operations are stable;
- publisher demand exists;
- rights, removal, refund, tax, and payout responsibilities are operational;
- unit economics are positive;
- marketplace complexity does not degrade the learner product.
