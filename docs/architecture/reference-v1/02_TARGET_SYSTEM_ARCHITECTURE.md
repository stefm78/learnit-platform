# Target system architecture

## 1. Evolution topology

Learn-it evolves in three controlled stages.

### Stage A — standalone local player

```text
Browser or packaged web runtime
└── Learn-it player
    ├── learning runtime
    ├── local content
    ├── local progress
    ├── local sessions
    └── import/export
```

The current development stream remains in this stage until the standalone promotion gate passes.

### Stage B — local-first client and modular-monolith backend

```text
┌────────────────────────────────────┐
│ Learn-it client                    │
│                                    │
│ App shell                          │
│ Learning and content domains       │
│ Progress and session domains       │
│ Local repositories                 │
│ Event outbox and sync client       │
│ Identity/catalog/entitlement ports │
└─────────────────┬──────────────────┘
                  │ HTTPS
┌─────────────────▼──────────────────┐
│ Learn-it modular backend           │
│                                    │
│ Identity and learner profiles      │
│ Catalog and kit versions           │
│ Progress synchronization           │
│ Entitlements                       │
│ Organizations                      │
│ Governance                         │
│ Commerce when authorized           │
└─────────────┬───────────────┬──────┘
              │               │
         PostgreSQL      Object storage/CDN
```

The backend is one deployable system with explicit internal module boundaries. Modules do not share ownership merely because they share a database server.

### Stage C — selective extraction

A module may become a separate service only after evidence demonstrates at least one strong reason:

- independent scaling characteristics;
- independent release cadence;
- distinct security boundary;
- separate operational ownership;
- external reuse through a stable contract;
- measurable repository or deployment bottleneck.

## 2. Client structure

The target client contains these responsibilities, introduced only when real code requires them:

- `app-shell` — composition, navigation, lifecycle;
- `learning-runtime` — activity and learning-session execution;
- `content-domain` — packages, courses, objectives, activities, versions;
- `progress-domain` — attempts, evidence, interpretations, revision state;
- `session-domain` — active series, resume, exit, local continuity;
- `local-storage` — transactions and local schema migrations;
- `sync-client` — push/pull, retry, receipts, cursors, conflict presentation;
- `identity-client` — account and learner-profile interactions;
- `catalog-client` — remote discovery and installation;
- `entitlement-client` — access decisions and offline grace state;
- `media-runtime` — media validation, cache, quotas, zoom and rendering;
- `ui-components` — presentation without business persistence rules;
- `observability` — technical diagnostics with privacy limits.

These names are bounded responsibilities, not permission to create empty directories before extraction work begins.

## 3. Server modules and data ownership

| Module | Owns |
|---|---|
| Identity | accounts, credentials, authentication sessions |
| Learner Profiles | learner identities and profile preferences |
| Catalog | product metadata and discoverability |
| Content Publication | submissions, validation, review, publication state |
| Kit Distribution | immutable package versions, hashes, download metadata |
| Progress Sync | immutable learning events, projections, sync receipts |
| Entitlements | access rights, validity, grants, revocations |
| Commerce | orders, payment references, refunds, invoices |
| Organizations | organizations, cohorts, seats, assignments |
| Governance | consent, exports, deletion requests, audit records |

A module may read another module only through an approved query or replicated read model. It may not update another owner's tables.

## 4. Storage model

### Relational database

Suitable for:

- identity and profile metadata;
- catalog metadata;
- content lineage;
- orders and entitlements;
- organizations and assignments;
- event indexes, receipts, and projections;
- governance records.

### Object storage

Suitable for:

- published kit archives;
- images, audio, video, and other large media;
- generated release evidence that must be retained;
- immutable content objects addressed by hash.

### Client storage

The eventual client storage model should use structured, transactional storage for:

- installed package manifests and content;
- progress events;
- progress projections;
- active sessions;
- synchronization outbox and receipts;
- cached catalog metadata and media indexes.

The migration technology is intentionally held until the standalone baseline is protected by tests.

## 5. Learning event flow

```text
User action
   ↓
Application use case validates intent
   ↓
Progress domain creates immutable event
   ↓
Single local transaction writes:
- event
- derived projection update
- outbound sync intent
   ↓
UI reads local projection immediately
   ↓
Sync client later transmits idempotent batches
```

The progress domain owns the atomic creation of the event and its outbound intent. The synchronization module owns remote cursors, retries, batch state, and server receipts.

## 6. Commerce isolation

Commerce does not directly rewrite learner progress or package installations.

```text
Order paid
   ↓
Commerce records transaction
   ↓
Entitlements grants access
   ↓
Client receives entitlement state
   ↓
Catalog/distribution permits installation
```

Refund, expiry, or revocation rules must preserve learner-data export and define explicit offline behavior.

## 7. Operational architecture

The first production platform should prefer:

- one regional modular backend deployment;
- one relational primary with tested backup and restoration;
- object storage and CDN for packages and media;
- stateless API instances when horizontal scaling becomes necessary;
- structured logs, metrics, traces, and audit events;
- asynchronous jobs only for work that does not require immediate transactional completion.

Redis, message brokers, multi-region active-active, and service meshes remain optional future tools, not baseline requirements.
