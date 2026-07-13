# Dependency and contract rules

## 1. Layer direction

```text
UI and delivery
      ↓
Application use cases
      ↓
Domain model and ports
      ↑
Infrastructure adapters
```

Allowed dependencies point inward toward stable domain concepts. Infrastructure implements ports defined by the consuming application or domain.

## 2. Prohibited dependencies

The following direct dependencies are prohibited:

- domain → DOM or UI framework;
- domain → localStorage, IndexedDB, file system, or HTTP client;
- UI → database or remote API;
- catalog → progress persistence;
- commerce → entitlement tables;
- authoring → player internals;
- one module → another module's private adapter or repository;
- client domain → cloud-vendor SDK;
- module A ↔ module B cycle.

## 3. Ports and adapters

A port expresses the minimum capability required by its consumer.

```typescript
interface ProgressRepository {
  append(events: ProgressEvent[]): Promise<void>;
  read(query: ProgressQuery): Promise<ProgressEvent[]>;
  projection(profileId: ProfileId, courseId: CourseId): Promise<ProgressProjection>;
}
```

Local memory, current legacy storage, IndexedDB, and a remote synchronization adapter may implement different ports, but the learning domain must not know which vendor or persistence mechanism is used.

Avoid generic abstractions such as `UniversalRepository<T>` unless repeated real use proves identical semantics. Different domains have different concurrency, lifecycle, and consistency rules.

## 4. Data ownership

A module owns:

- the meaning of its entities;
- the write rules;
- the canonical storage schema;
- migrations;
- domain events it emits;
- invariants and tests.

Another module may not bypass that owner. Shared database access does not create shared ownership.

## 5. Cross-module communication

Use one of four explicit patterns:

1. synchronous command to the owning module;
2. synchronous query through a stable reader interface;
3. immutable domain event;
4. generated read model with declared source and refresh rule.

Every asynchronous event requires:

- stable type name;
- schema version;
- unique event ID;
- producer ownership;
- delivery semantics;
- idempotent consumer behavior;
- retention decision;
- privacy classification.

## 6. Contract versioning

Published contract fields cannot be silently redefined.

Compatible changes generally include:

- adding an optional field with a safe default;
- adding a new event type;
- widening an enum only when consumers are designed for unknown values;
- adding a new API operation.

Potentially breaking changes include:

- making an optional field required;
- changing identifier meaning;
- changing units, time semantics, or interpretation;
- removing an enum value;
- changing error behavior;
- reusing an event type for a different fact.

Breaking changes require a new contract version and an explicit migration or compatibility window.

## 7. Canonical source

Each normative contract has one editable canonical file.

Examples:

```text
contracts/events/progress-event.schema.json
        ↓ referenced or generated into
OpenAPI, fixtures, documentation, validators
```

```text
work-packages/ARC-WP-000.json
        ↓ rendered into
GitHub issue, roadmap view, human summary
```

Do not maintain equivalent JSON, YAML, Markdown, and issue text manually.

## 8. Architecture tests

Once the standalone source is imported, CI should check at least:

- prohibited imports;
- cycles between declared modules;
- access to browser storage outside adapters;
- direct network calls outside gateways;
- contract-reference integrity;
- duplicate canonical identifiers in fixtures;
- work-package scope against changed files.

Until code exists in the repository, these remain planned checks rather than proven enforcement.

## 9. Atomic progress and outbox ownership

The local transaction that records a learning fact must not be split ambiguously between Progress and Sync.

Recommended ownership:

```text
Progress persistence transaction
├── immutable progress event
├── updated local projection
└── outbound sync intent linked to that event
```

The synchronization component reads outbound intents through a public interface and owns:

- batch construction;
- retry policy;
- remote cursors;
- receipts;
- transport errors;
- remote conflict metadata.

This keeps the user action atomic without granting Sync ownership of learning semantics.

## 10. Exceptions

Any exception must state:

- rule being broken;
- evidence that the normal rule is inadequate;
- bounded duration;
- affected modules;
- rollback or removal plan;
- tests preventing expansion of the exception.

Exceptions are ADRs, not comments hidden in implementation code.
