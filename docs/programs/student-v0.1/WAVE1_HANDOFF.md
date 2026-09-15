# Student V0.1 — Wave 1 Handoff

- Architecture work package: `ARC-WP-025`
- Owner issue: `#380`
- Architecture source baseline: `1e71271436fd4b7dd7d895cfec827833187630fe`
- Frozen contract candidate: `contracts/learnit-kit-v4.schema.json`
- Current state: **PRE-WAVE / HUMAN GATE REQUIRED**

## 1. Do not start yet

This handoff is preparatory. JOB 01–03 **must not start** from the architecture branch or from `1e71271436fd4b7dd7d895cfec827833187630fe` merely because these documents exist.

Wave 1 may start only after:

1. the ARC-WP-025 DRAFT PR passes the accountable human architecture gate;
2. the PR is merged through normal repository governance;
3. each worker re-reads `main` and records the same exact post-merge commit;
4. the v4 schema on that commit is frozen;
5. the coordinator rechecks open PRs/branches for path overlap.

The resolved common base must replace:

`RESOLVE_EXACT_MAIN_COMMIT_AFTER_ACCEPTED_ARC_WP_025_MERGE`

in execution evidence. Never guess or inherit it from conversation context.

## 2. Frozen cross-worker interface

All workers implement against the architecture file:

`docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`

and the exact frozen schema:

`contracts/learnit-kit-v4.schema.json`.

The shared semantic boundary is:

```text
canonical activity
-> Learning semantic authority
-> Session
-> learner-safe ActivityPresentation
-> UI
-> ActivityResponse
-> Learning evaluation/completion
```

### Frozen response shapes

| Type | ActivityResponse |
| --- | --- |
| lesson | `{completed:true}` |
| flashcard | `{revealed:true}` |
| qcm | `{choiceId}` |
| fill | slotId -> tokenId mapping |
| matching | `{matches:[{leftItemId,rightItemId}]}` |
| order | `{itemIds:[...]}` |
| classify | `{assignments:[{itemId,bucketId}]}` |
| constructed | `{text}` |

No worker may alter these shapes unilaterally.

### Frozen secret boundary

Never expose through ActivityPresentation:

- qcm `correctChoiceId`;
- fill `answers`;
- matching `matches`;
- order `correctOrder`;
- classify item `correctBucketId`;
- constructed `acceptedResponses`.

Lesson/flashcard have no scoring key. Their completion must not be converted to correctness.

## 3. JOB 01 — Learning/runtime semantics

### Responsibility

Implement canonical v4 admission and Learning/session semantics without owning UI mechanics.

### Writable paths

Exactly:

- `apps/learnit-next/src/integration/atlas/import_adapter.js`
- `apps/learnit-next/src/integration/atlas/session.js`
- `apps/learnit-next/src/core/student_activity_semantics.js` (new if needed)
- `apps/learnit-next/tests/student_v0_1_contract_semantics.py`
- `apps/learnit-next/tests/student_v0_1_learning_semantics.py`

No other path is writable without returning to the coordinator.

### Required behavior

- explicit v2/v3/v4 admission; unknown discriminator fails closed;
- no v2/v3 semantic rewrite;
- semantic cross-reference validation not expressible in JSON Schema:
  - matching bijection;
  - order complete permutation;
  - classify unique IDs, declared bucket references and complete single-label response;
  - media asset references;
  - SVG/raster fail-closed admission handoe1;
- qcm/fill existing behavior unchanged;
- constructed `canonical-text-match-v1` unchanged;
- lesson completion and flashcard reveal completion remain non-scored;
- project learner-safe presentations that strip all hidden solution fields;
- no raw DOM access.

### Must not touch

UI/render/style files, authoring/factory files, v4 schema, source manifest, build, workflow, governance.

## 4. JOB 02 — Activity presentation/UI

### Responsibility

Implement type-specific learner interaction using only frozen ActivityPresentation data and return frozen ActivityResponse shapes.

### Writable paths

Exactly:

- `apps/learnit-next/src/ui/render.js`
- `apps/learnit-next/src/ui/student_activity_presenters.js` (new if needed)
- `apps/learnit-next/src/styles.css`
- `apps/learnit-next/src/atlas.css`
- `apps/learnit-next/tests/student_v0_1_activity_ui.py`
- `apps/learnit-next/tests/student_v0_1_activity_accessibility.py`

No other path is writable without returning to the coordinator.

### Required behavior

- a closed internal typed presenter dispatch is allowed;
- no dynamic registry/plugin loading;
- lesson: readable structured content and explicit continue;
- flashcard: front first, explicit reveal, then continue;
- matching: accessible one-to-one association interaction;
- order: accessible reordering interaction;
- classify: accessible single-bucket assignment interaction;
- constructed: bounded text input;
- qcm/fill remain behaviorally equivalent;
- no correctness logic and no scoring-secret field assumption;
- raw DOM reading remains UI-owned.

### Must not touch

Session/evaluation/import code, authoring/factory, v4 schema, source manifest, build, workflow, governance.

## 5. JOB 03 — Authoring/Factory/quality

### Responsibility

Add a v4 authoring/validation path and update deterministic Factory/quality admission without changing learner runtime.

### Writable paths

Exactly:

- `authoring/v4/**`
- `authoring/factory/factory_gate.py`
- `authoring/factory/README.md`
- `authoring/skills/SKILL_ATLAS_KIT_AUTHORING_V3.md`
- `authoring/tests/student_v0_1_authoring.py`
- `authoring/tests/student_v0_1_quality.py`

No other path is writable without returning to the coordinator.

### Required behavior

- author v4 directly; never rewrite v2/v3 payloads in place;
- generate only the frozen eight activity families;
- select families because they serve a cognitive role, not a quota;
- distinguish non-scored lesson/flashcard from assessment evidence;
- validate matching/order/classify hidden solution completeness;
- validate embedded local media and pedagogical metadata;
- reject remote media dependencies;
- keep Knowledge-assisted authoring outside the execution path;
- Factory remains deterministic/provider-neutral at its gate; no runtime model/provider dependency.

### Must not touch

Learn-it Next app/runtime/UI, v4 schema, build/source manifest/workflow, governance.

## 6. Pairwise-disjointness proof

JOB 01 prefixes/files:
- `apps/learnit-next/src/integration/atlas/*` limited to two exact files;
- `apps/learnit-next/src/core/student_activity_semantics.js`;
- two dedicated test filenames.

JOB 02 prefixes/files:
- `apps/learnit-next/src/ui/*` limited to two exact files;
- two exact style files;
- two different dedicated test filenames.

JOB 03:
- `authoring/**` bounded to listed paths only.

The writable sets have no identical path. Shared integration surfaces are not writable by more than one worker.

The following are intentionally owned by **JOB 04 only**:

- `apps/learnit-next/source_manifest.json`;
- `apps/learnit-next/build.py`;
- `apps/learnit-next/dev/run_checks.py`;
- `.github/workflows/learnit-next-ci.yml`.

This is the minimum concurrency seam. No pre-Wave product refactor is required; if a worker discovers that the frozen interface cannot be implemented without another worker's file, that worker stops and reports the conflict instead of editing across scope.

## 7. Evidence package required from each worker

Each JOB 01–03 handoff must contain:

- exact common base commit;
- exact result commit;
- `git diff --name-only <base>..<result>`;
- confirmation all changed paths are within its exact writable set;
- commands/tests and raw pass/fail summary;
- negative/adversarial cases exercised;
- known limitations;
- rollback (drop/revert the exact worker commit set);
- explicit statement that the v4 schema was not edited;
- explicit statement that build/source-manifest/workflow files were not edited.

## 8. Fan-in A contract — JOB 04

JOB 04 starts only after all accepted worker result commits are frozen.

It must:

1. verify each result is based on the exact common base;
2. verify changed paths are disjoint;
3. integrate exact reviewed results;
4. wire only integrator-owned shared files;
5. run deterministic clean build and repository governance;
6. run v2/v3 regression plus v4 boundary tests;
7. return any worker-owned defect to its owner rather than silently repair it;
8. publish one exact Fan-in A head for Wave 2.

A merge conflict in a worker-owned file is evidence that the parallelism contract failed. JOB 04 must not improvise a resolution.

## 9. Stop conditions

Stop Wave 1 immediately on:

- different base SHA between workers;
- v4 schema drift;
- worker path overlap;
- need to change a frozen response/presentation semantic;
- solution secret entering UI;
- lesson/flashcard treated as scored evidence;
- remote media requirement;
- backend/account/provider/runtime-AI dependency;
- generic plug-in/evaluator/event-bus abstraction;
- ambiguous durable effect or stale base before mutation.

Human authority may narrow or revoke the program at any point.
