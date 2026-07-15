# Clean-generation multi-AI execution v1

- Governing package: `ARC-WP-022`
- File plan: `FILE_PLAN_V1.json`
- Maximum parallel implementing agents: **3**
- Shared writable files: **none**
- Integrator: sequential, independent from implementers

## 1. When parallel work becomes safe

Parallel implementation may start only after:

1. `ARC-WP-022` is merged;
2. `contracts/learnit-kit-v2.schema.json` is frozen on `main`;
3. `ARC-WP-023` creates subordinate work packages using the exact same post-merge base commit;
4. each work package reproduces one role scope from `FILE_PLAN_V1.json` without adding paths;
5. each agent has an independent branch, clone or worktree;
6. the governor confirms that no open PR or branch already owns an overlapping path.

Until all six conditions hold, successor implementation remains on HOLD.

## 2. Parallel streams

### Stream A — runtime agent

Owns only the 14 runtime and UI files assigned by the file plan.

Responsibilities:

- canonical JSON and digest calculation in browser code;
- UUID and identity validation;
- contract and semantic validation interface;
- fail-closed import planning;
- library and course-install projections;
- session queue for QCM and fill;
- progress records;
- storage port and IndexedDB adapter;
- minimal accessible rendering.

The runtime agent must not create build, workflow, test, authoring, fixture or contract files.

### Stream B — authoring agent

Owns only the five authoring files assigned by the file plan.

Responsibilities:

- persistent UUID allocation tooling;
- semantic and digest validation in Python;
- representative Nombres complexes kit;
- representative Signaux électriques kit;
- author-facing rules for revision changes and digest regeneration.

The authoring agent must not alter the frozen schema or Player files.

### Stream C — contradictory QA and fixture agent

Owns only the three fixtures and four test files assigned by the file plan.

Responsibilities:

- schema-valid minimal fixture;
- legacy-package rejection fixture;
- revision-digest mismatch fixture;
- semantic contract attacks;
- RC718 storage immutability test;
- browser vertical-slice test;
- deterministic-build contract test.

The QA agent writes tests against the frozen contract and documented public behavior. It must not repair implementation code.

## 3. Independent role review

Each stream receives a review before integration:

- runtime output: architecture and browser-security review;
- authoring output: learning and contract-alignment review;
- QA output: adversarial sufficiency review by a reviewer who did not author runtime code.

A role output with unresolved critical or high findings does not enter integration.

## 4. Integrator scope

The integrator owns only:

- `apps/learnit-next/build.py`;
- `apps/learnit-next/source_manifest.json`;
- `apps/learnit-next/dev/run_checks.py`;
- `apps/learnit-next/dev/release.py`;
- `.github/workflows/learnit-next-ci.yml`.

The integrator may combine reviewed commits using explicit merge or cherry-pick provenance. It may not silently edit role-owned files. A defect in a role-owned file is returned to that role through a new reviewed commit.

## 5. Required merge order

The logical integration order is:

1. frozen contract from `ARC-WP-022`;
2. QA fixtures and test skeletons;
3. authoring tools and golden kits;
4. runtime implementation;
5. integrator build, manifest, checks and workflow;
6. full contradictory QA on the exact integrated result;
7. governor acceptance in a separate PR.

Streams 2, 3 and 4 may be developed concurrently, but their integration is controlled and ordered.

## 6. Public interfaces frozen for the streams

Runtime code exposes one browser test surface under `window.__LEARNIT_NEXT_TEST__` only in the built candidate. The bounded surface contains:

- `contractVersion`;
- `validatePackage(payload)`;
- `previewImport(payload)`;
- `importPackage(payload)`;
- `listCourses()`;
- `startCourse(courseInstallId)`;
- `answer(activityRevisionId, answer)`;
- `getProgress(courseInstallId)`;
- `resetNextData()`;
- `storageReport()`.

The test API is diagnostic and is not a second product implementation. It must use the same domain and storage paths as the visible UI.

## 7. Stop conditions

The governor stops all parallel work when:

- any two branches modify the same planned path;
- a branch changes the frozen schema;
- a branch introduces an unplanned successor file;
- a branch accesses an RC718 storage key or database;
- a branch adds compatibility or migration code;
- a branch enters a held platform domain;
- source, tests or artifact provenance becomes ambiguous;
- a high-severity contradictory-QA finding is unresolved;
- the exact common base is lost.

## 8. Evidence required from every agent

Every agent output includes:

- exact base commit;
- exact result commit;
- changed-path list;
- tests run and raw result summary;
- claims separated from evidence;
- known limitations;
- rollback instructions;
- confirmation that no generated output is committed;
- confirmation that no path outside the assigned scope changed.

## 9. Human intervention

No human test is required for individual parallel streams. Human testing begins only after the integrated candidate passes automated contract, storage-isolation, browser-flow, build-determinism and provenance gates.

The first human candidate is explicitly labeled as a new generation with empty active state, not as an RC718 upgrade.
