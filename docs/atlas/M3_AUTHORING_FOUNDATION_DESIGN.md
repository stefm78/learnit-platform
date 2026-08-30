# M3.0 Authoring Foundation — design freeze candidate

## 1. Mandate and boundary

M3.0 is the smallest useful authoring increment after the promoted M2.2 learner loop.

The only product outcome in scope is:

```text
existing canonical Atlas kit
→ visual edit
→ live authoritative validation
→ author preview
→ canonical deterministic export
→ re-import into Learn-it without semantic drift
```

M3.0 does **not** create a full curriculum studio. It does not add document ingestion, LLM assistance, new activity types, cloud publishing, accounts, synchronization, remote catalog, teacher/cohort features or any learner-runtime semantic.

The authoring tool is a separate local/offline application. It shares canonical contracts and validators with Learn-it, but it is not embedded in the learner artifact.

## 2. Existing canonical inputs

M3.0 treats these current repository assets as read-only upstream authority:

- `contracts/learnit-kit-v2.schema.json`;
- `authoring/v2/validate_kit.py`;
- `authoring/v2/atlas/validate_atlas_content.py`;
- `authoring/v2/atlas/nombres_complexes_atlas.json`;
- `authoring/v2/atlas/signaux_electriques_atlas.json`.

The current contract remains `learnit.kit.v2`.

Supported activity families remain exactly:

- `qcm`;
- `fill`.

The current Atlas editorial profile remains unchanged: each objective keeps its authored practice/correction/validation/maintenance/transfer structure and existing independence-claim semantics.

Any need to change the schema, Atlas editorial profile, activity families or learner runtime is a separate gate and stops M3.0.

## 3. Architecture decision

### 3.1 Separate local author application

Implementation target:

```text
authoring/studio/
├── README.md
├── core.py
├── server.py
├── web/
│   ├── index.html
│   ├── studio.css
│   └── studio.js
└── tests/
    └── test_m3_authoring_foundation.py
```

A local Python process serves the studio only on loopback and invokes the existing canonical validators in-process.

The browser UI never contacts the public network. The learner runtime is not loaded into or modified by the studio.

### 3.2 Local server contract

The implementation must:

- bind only to `127.0.0.1`;
- reject non-loopback Host values;
- expose no CORS permission;
- make no outbound HTTP request;
- contain no secret or account concept;
- hold no learner state;
- accept and return only authoring draft/diagnostic/export material.

The local server is authoring tooling, not a platform backend.

### 3.3 Draft persistence

Draft persistence is isolated from Learn-it learner storage.

Browser namespace:

`learnit.authoring.m3.v1`

M3.0 stores only the current author draft and import provenance needed for reload recovery. It must never read, migrate, clear or write Learn-it learner IndexedDB/localStorage namespaces.

A user can explicitly discard the author draft.

## 4. Editing scope

M3.0 edits an **existing valid Atlas kit**.

The visual editor may change:

- package title, description, version label and language;
- course title, subtitle and estimated minutes;
- objective labels;
- existing activity prompt, explanation, difficulty, learning phase, assessment role and estimated minutes;
- existing QCM choice labels and correct choice;
- existing fill text, token labels, max-use values and answer mapping.

M3.0 does **not** add, delete or reorder packages, courses, objectives, activities, choices, slots or tokens.

It does not manually expose canonical lineage IDs, revision IDs, digests or claim IDs as ordinary author-editable fields.

This restriction is deliberate: M3.0 proves a safe edit/export loop before structural authoring is opened.

## 5. Identity and revision rules

Imported lineage IDs remain stable.

For an imported entity:

- a pure presentation-only navigation action changes nothing;
- the first semantic edit to an activity allocates one new UUIDv4 `activityRevisionId` for that draft revision;
- the enclosing course gets one new UUIDv4 `courseRevisionId` for that draft revision;
- the package gets one new UUIDv4 `packageRevisionId` for that draft revision;
- further edits within the same unsaved draft reuse those newly allocated revision IDs;
- unaffected activity lineage/revision identities remain unchanged.

New revision IDs are allocated once and persisted in the draft before export, so repeated exports of the same unchanged draft are byte-identical.

M3.0 creates no new lineage object because structural creation is out of scope.

## 6. Canonical export pipeline

The Python authoring core is the only export authority.

For every export it must, in this order:

1. load the persisted draft and reject duplicate keys/non-UTF-8/non-canonical unsupported values;
2. preserve imported lineage IDs;
3. apply the draft revision IDs for changed activity/course/package objects;
4. recompute Atlas independence claims from the edited visible stimuli using the existing Atlas claim logic;
5. recompute activity revision digests, then course digest, then package digest;
6. run the frozen JSON Schema validation;
7. run the existing general v2 authoring validator;
8. run the existing Atlas editorial validator;
9. serialize one canonical UTF-8 JSON representation with NFC strings, sorted object keys, authored array order, no insignificant whitespace and no floating-point values;
10. return the exact bytes and SHA-256 to the browser for download.

Export is disabled on any blocking diagnostic.

### Determinism rule

A draft with unchanged stored revision IDs and unchanged logical content must export to exactly the same bytes and digest on repeated runs.

A no-op import/export of either canonical Atlas proof kit must be byte-identical to its input.

## 7. Live validation

The UI may perform lightweight immediate field checks for responsiveness, but those checks are advisory only.

Authoritative live validation is the server result from the same canonical validator stack used at export.

The UI must show:

- blocking vs warning distinction;
- JSON/object location or author-facing field;
- cause;
- concerned value when useful;
- the fact that export is unavailable while blocking errors remain.

No green state may be shown if the canonical validator stack rejects the draft.

## 8. Preview

M3.0 provides an **author preview**, not a second learner runtime.

It renders only the supported existing QCM/fill content so the author can inspect:

- prompt;
- choices or fill structure;
- selected correct answer mapping;
- explanation;
- learning phase / assessment role;
- linked objective label.

Preview is explicitly non-authoritative for Atlas recommendation, memory, transfer eligibility or learner-state behavior.

The acceptance oracle for runtime compatibility is re-import of the exported kit into the real Learn-it Next product tests/browser flow.

## 9. Implementation package freeze

After this design is accepted, the proposed product implementation package is `ATLAS-WP-009`.

Exact product writable paths:

- `work-packages/ATLAS-WP-009.json`
- `authoring/studio/README.md`
- `authoring/studio/core.py`
- `authoring/studio/server.py`
- `authoring/studio/web/index.html`
- `authoring/studio/web/studio.css`
- `authoring/studio/web/studio.js`
- `authoring/studio/tests/test_m3_authoring_foundation.py`
- `.github/workflows/atlas-m3-authoring-foundation-ci.yml`

Everything else is read-only for product implementation, including:

- learner runtime;
- learner source manifest;
- kit schema;
- existing v2/Atlas validators;
- canonical proof kits;
- governance files.

This is intentionally one implementation lane. Splitting the small studio across multiple product lanes would increase interface cost without reducing risk.

## 10. Independent QA freeze

Independent QA is proposed as `QA-WP-018` on a separate head.

QA writable paths only:

- `work-packages/QA-WP-018.json`
- `authoring/studio/tests/qa_m3_authoring_foundation.py`
- `.github/workflows/atlas-m3-authoring-foundation-qa.yml`

QA never repairs product files.

QA must bind to one exact frozen implementation HEAD and exact authoring artifact/source package before a final PASS.

## 11. Required implementation evidence

Product CI must prove at minimum:

1. both canonical Atlas proof kits load successfully;
2. no-op export is byte-identical for both;
3. one representative QCM semantic edit preserves lineage IDs but rotates only required revision IDs and recomputes valid digests/claims;
4. one representative fill semantic edit does the same;
5. repeated export of an unchanged draft is byte-identical;
6. blocking schema/editorial defects disable export;
7. reload restores the author draft from only the authoring namespace;
8. discard clears only the authoring namespace;
9. no learner storage namespace is touched;
10. local server binds loopback only and makes no outbound network request;
11. exported edited kits pass both canonical validators;
12. exported edited kits are accepted by the existing Learn-it import/browser regression;
13. learner M1/M2/M2.2 regressions remain green without learner source changes.

## 12. Independent adversarial QA

The QA oracle must independently attack:

- stale revision IDs after semantic edits;
- lineage-ID mutation on ordinary edits;
- digest mismatch;
- stale Atlas claim IDs/stimulus digests;
- duplicate keys and malformed UTF-8;
- unsupported activity types;
- invalid phase/role combinations;
- QCM choice/correct-answer breakage;
- fill slot/token/answer breakage;
- export despite blocking diagnostics;
- non-deterministic repeated export;
- hidden writes to learner storage;
- non-loopback binding or attempted external network;
- preview being treated as learner-semantic authority;
- product/QA scope leakage.

Any such divergence yields HOLD.

## 13. Human gate

M3.0 requires one short desktop authoring human gate after exact-head independent QA.

Human flow:

1. open one canonical Atlas kit;
2. edit one visible activity field;
3. observe immediate diagnostic state;
4. preview the edited activity;
5. export;
6. re-open the exported kit and confirm the edit;
7. confirm the studio is understandable without editing JSON by hand.

Android authoring is not a M3.0 requirement. Exported learner-kit Android compatibility remains covered by learner regression evidence.

## 14. Deferred M3 increments

Explicitly not in M3.0:

- structural add/delete/reorder of objectives/activities;
- source-document import;
- PDF/Markdown ingestion;
- LLM-assisted authoring;
- asset/media authoring;
- batch authoring;
- remote publishing;
- accounts or collaboration;
- marketplace;
- teacher/cohort;
- learner-runtime changes.

These require later independent M3 gates.

## 15. Rollback

The entire M3.0 implementation is additive under `authoring/studio/**` plus its dedicated workflow/work-package metadata.

Rollback is deletion/revert of that isolated authoring surface. No learner storage migration, learner runtime change or canonical kit rewrite is involved.

## 16. Design verdict

If this document and its work package are accepted:

`PASS_M3_0_AUTHORING_FOUNDATION_DESIGN_TO_IMPLEMENTATION_GATE`

This authorizes a later explicit product implementation package only. It does not itself authorize implementation, promotion or publication.
