# Learn-it Next runtime foundation

This directory contains the bounded `DEV-WP-031` browser runtime for the frozen `learnit.kit.v2` contract. It implements only the first vertical slice:

```text
empty library
→ strict v2 import
→ library projection
→ one course session
→ QCM and fill
→ progress persistence
→ refresh recovery
```

It is a clean generation. It does not interpret or migrate legacy packages or learner data.

## Architecture

- `src/core/` contains canonical JSON, identity, contract, import, library, session and progress rules.
- `src/ports/storage.js` defines the storage boundary and the only successor namespaces.
- `src/adapters/indexeddb.js` implements atomic IndexedDB imports and progress persistence.
- `src/ui/render.js` renders authored content with DOM text nodes and accessible native controls.
- `src/main.js` composes the adapter and domain services and exposes the bounded diagnostic API.

Domain modules receive a storage port; they do not import the IndexedDB adapter. The UI receives the composed runtime; it does not read or write storage directly.

## Storage ownership

- localStorage prefix: `learnit.next.v1.`
- IndexedDB database: `learnit_next_v1`
- stores: `packages`, `courses`, `progress`, `meta`

Reset deletes only this database and localStorage keys owned by the prefix above.

## Contract behavior

The runtime validates the complete bounded schema shape without external dependencies, then applies semantic checks and inside-out canonical SHA-256 verification. Import is fail-closed: parsing, contract discrimination, structural validation, semantic validation and digest verification complete before an installation plan is committed in one IndexedDB transaction.

QCM correctness compares `choiceId`. Fill correctness compares explicit `slotId` to `tokenId` assignments and rejects usage beyond each token's `maxUses`.

## Running the unbuilt template

Serve the repository root with any static HTTP server and open:

```text
/apps/learnit-next/index.template.html
```

Opening the template directly from `file://` is not supported because browser module loading requires an HTTP origin. Build, manifest, CI, fixtures and browser tests are owned by later or independent work packages and are intentionally absent here.

## Diagnostic surface

The visible interface and `window.__LEARNIT_NEXT_TEST__` call the same runtime services. The frozen diagnostic methods are:

- `contractVersion`
- `validatePackage(payload)`
- `previewImport(payload)`
- `importPackage(payload)`
- `listCourses()`
- `startCourse(courseInstallId)`
- `answer(activityRevisionId, answer)`
- `getProgress(courseInstallId)`
- `resetNextData()`
- `storageReport()`

This role output is not self-certified. Contract fixtures, browser behavior, storage isolation and cross-language digest agreement require independent QA and integration review.
