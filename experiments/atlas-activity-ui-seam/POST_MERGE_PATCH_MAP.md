# Post-merge patch map — execute only from accepted new main

This map is preparation only. Re-audit exact `main` after #354 merges before applying it. If R15 visual polish changes any path below, use the accepted merged code as authority and shrink/revise the patch accordingly.

## 1. `apps/learnit-next/src/core/session.js`

**OWNER:** Learning / activity semantics

**WHY:** Existing QCM/fill normalization and correctness authority already lives here.

**MINIMUM DELTA:**

- add one bounded constructed-answer normalizer;
- add one `activity.type === 'constructed'` evaluation branch;
- keep QCM/fill code and normalized shapes unchanged;
- binary correctness only;
- deterministic NFC/trim plus explicit bounded case/whitespace options.

**DO NOT ADD:** generic evaluator registry, plugin API, planner hooks, DOM, persistence migration.

**REGRESSION RISK:** accidental change to QCM/fill normalization/errors or progress-record shape.

**TEST ORACLE:** existing core/session tests + new constructed unit cases + explicit golden QCM/fill behavior assertions.

## 2. UI-owned Atlas activity interaction

**OWNER:** UX / interaction presentation

**WHY:** `integration/atlas/session.js` currently owns `renderActivity()` and `readResponse()`, including DOM selectors. That is the coupling to remove.

**MINIMUM DELTA:**

- move QCM/fill activity markup generation and raw-response collection out of integration;
- add constructed fields rendering/readout there;
- accept learner-safe activity presentation only;
- return raw response only;
- preserve existing learner copy, accessibility, focus, and response affordances unless UX explicitly changes them.

**FILE CHOICE AFTER MERGE:** first evaluate whether existing `apps/learnit-next/src/ui/atlas_session.js` can own this without mixing its Atlas core-commit validation responsibilities. If not, create exactly one small UI module (for example `apps/learnit-next/src/ui/atlas_activity.js`). Do not create both.

**REGRESSION RISK:** keyboard/focus behavior, required-answer error messaging, QCM/fill visual regressions, selector drift.

**TEST ORACLE:** Atlas experience/integration/browser tests plus direct qcm/fill/constructed UI response-shape tests.

## 3. `apps/learnit-next/src/integration/atlas/session.js`

**OWNER:** Session / Atlas orchestration

**WHY:** It currently mixes adapter, renderer, and DOM reader.

**MINIMUM DELTA:**

- replace local `renderActivity()` / `readResponse()` implementations with calls to the UI-owned seam;
- retain source-activity resolution, Atlas session lifecycle, scoring adapter, assistance, feedback transition orchestration, evidence projection and resume behavior;
- extend Atlas activity registry allowlist for constructed only after core + contract support exists;
- keep correctness delegated to Learn-it core.

**DO NOT ADD:** constructed answer-key logic, DOM parsing, planner changes.

**REGRESSION RISK:** Atlas session submission lifecycle, feedback transition, resume/focus, assistance accounting.

**TEST ORACLE:** existing Atlas integration/experience suites + assertions that integration no longer contains activity DOM response parsing.

## 4. `contracts/learnit-kit-v2.schema.json`

**OWNER:** Architecture / contract + Learning

**WHY:** Current course activities are `oneOf(qcm, fill)` and common activity type enum is qcm/fill only.

**MINIMUM DELTA:**

- add exactly one `constructed` activity definition;
- add `constructed` to activity union/type admission;
- fields must have stable IDs + learner labels;
- evaluator must be deterministic `exact-fields` with bounded accepted values and normalization flags;
- decide whether authored pre-response support belongs in common activity or constructed only, based on the smallest E1/E2 requirement;
- keep existing qcm/fill definitions byte-semantically unchanged where possible.

**REGRESSION RISK:** widening the public contract beyond the capability proved, digest identity changes, accidental backwards incompatibility.

**TEST ORACLE:** schema valid/invalid fixtures, old v2 fixtures unchanged, new constructed fixtures, digest regression evidence.

## 5. `authoring/v2/validate_kit.py`

**OWNER:** Authoring + Learning

**WHY:** Semantic validation/reporting currently has explicit qcm/fill branches and counters.

**MINIMUM DELTA:**

- validate constructed field-ID uniqueness, evaluator field coverage, accepted-values presence, and deterministic normalization flags;
- reject incomplete/mismatched evaluator mappings;
- preserve qcm/fill semantic checks;
- do not infer semantic equivalence.

**REGRESSION RISK:** accepting ambiguous/underspecified constructed activities or disturbing frozen authoring checks.

**TEST ORACLE:** negative malformed-constructed fixtures and all existing validator tests.

## 6. `authoring/v2/atlas/validate_atlas_content.py`

**OWNER:** Atlas authoring / Learning

**WHY:** `stimulus_payload()` currently has qcm/fill-only branches and includes answer-operation material for independence-claim stimulus identities.

**MINIMUM DELTA:**

- define constructed learner-visible stimulus identity separately from private evaluator identity;
- ensure independence claims compare learner-visible challenge material, not answer keys;
- keep the current Atlas per-objective sequence and two-validation policy unchanged;
- prohibit revealing authored support in independent validation if support is admitted by the contract.

**REGRESSION RISK:** changing existing QCM/fill stimulus digests or weakening validation-independence semantics.

**TEST ORACLE:** current representative Atlas kits must retain their existing digests/claims; add constructed-specific digest separation tests.

## 7. `apps/learnit-next/source_manifest.json`

**OWNER:** Integration / release provenance

**WHY:** A new runtime/UI source file, if one is actually needed, must be part of deterministic build provenance.

**MINIMUM DELTA:** only if one new UI module is created, add that exact source and fingerprint/provenance entry. If existing modules are sufficient, do not touch ordered source count for architectural neatness alone.

**REGRESSION RISK:** deterministic-build identity mismatch or missing browser source.

**TEST ORACLE:** exact-head deterministic build and source-manifest checks.

## 8. Product tests

Expected additions should be placed in the smallest existing suites rather than creating a parallel QA programme:

- core/session: constructed normalization/correctness + qcm/fill golden regression;
- Atlas integration: constructed raw-response round trip and no scoring secret in UI projection;
- Atlas experience/UX: required fields, keyboard/focus, feedback continuity;
- authoring/schema: valid/invalid constructed examples;
- Atlas content: challenge/stimulus digest independent from evaluator answer key.

## Explicit non-changes

The first production slice should not require changes to:

- Atlas planner duration/selection semantics;
- ObjectiveEvidence state machine;
- memory schedule;
- transfer semantics;
- execution-class vocabulary;
- IndexedDB schema/migration;
- Today/Library objective maps or `worked != state changed` behavior;
- QCM/fill scoring semantics or persisted shapes.

Any requirement to change one of those surfaces is a **HOLD** and triggers a new architecture review before product mutation.
