# /AUDIT /SOLVE /BUILD — JOB 10
## Student V0.1 — G5 human-findings corrective author wave

Repository: `stefm78/learnit-platform`  
Coordinator issue: `#429`  
Parent program: `#380`  
G4 authority: `#425 / PR #426`  
G5 authority: `#427 / PR #428`  
Coordinator work package: `ATLAS-WP-046`

Coordinator branch:

`student-v01/g5-findings-corrective-wave`

Exact common base:

`18b925436777943b19c4b031c24659ad60dee133`

Exact G4 executable candidate:

`757ed15e840bfca603de0eac3bef1e9d5ff3483d`

G5 replay preparation:

`a72897c209b8ea7bd8672cc8a95be939ecee6fb8`

Canonical human findings:

`qualification/STUDENT_V01_G5_HUMAN_FINDINGS_01.md`

Reserved child work packages:

- `ATLAS-WP-047` — PRODUCT UX R1
- `ATLAS-WP-048` — SHOWCASE CONTENT R2

Reserved child branches:

- `student-v01/g5-finding-product-ux-r1`
- `student-v01/g5-finding-showcase-r2`

Next independent gate, not part of this job:

- `ATLAS-WP-049` — independent semantic review + corrective fan-in + G4 R1

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

Do not cherry-pick anything.

---

## 0. Mission

The G5 human replay has found learner-facing defects that automation did not detect.

This job is **author-side corrective work only**.

Produce **two independent repair candidates** from the exact same common base:

1. PRODUCT UX R1;
2. SHOWCASE CONTENT R2.

Do not fan them in.

Do not consume one sibling result while authoring the other.

Do not record a formal G5 GO/HOLD decision.

G5 remains formally:

`PENDING_HUMAN`

until a future exact replay and explicit human decision.

---

# PHASE 0 — AUTHORITY REBIND AND FAILURE REPRODUCTION

## 1. Fresh authority

Before any mutation:

1. fresh-read active Human Control Plane HEAD;
2. fresh-read repository `main`;
3. fresh-read:
   - issue #429;
   - `ATLAS-WP-046`;
   - `qualification/STUDENT_V01_G5_HUMAN_FINDINGS_01.md`;
   - issue #425 / PR #426;
   - `qualification/STUDENT_V01_JOB08_FANIN_B_RESULT.md`;
   - issue #427 / PR #428;
   - `qualification/STUDENT_V01_JOB09_G5_REPLAY_PACKET.json`.
4. verify:
   - G4 RESULT_SHA remains `757ed15e840bfca603de0eac3bef1e9d5ff3483d`;
   - G4 EVIDENCE_HEAD remains `18b925436777943b19c4b031c24659ad60dee133`;
   - G5 replay-prep remains `a72897c209b8ea7bd8672cc8a95be939ecee6fb8`;
   - PR #426 and #428 remain unmerged;
   - no final `STUDENT_V01_JOB09_G5_RESULT.md` has appeared;
   - no formal G5 human decision has superseded the corrective premise.

If authority drift invalidates the premise, stop:

`HOLD_STUDENT_V01_G5_CORRECTIVE_AUTHOR_WAVE_AUTHORITY_DRIFT`

---

## 2. Reproduce the six findings before repair

On the exact G4 candidate, independently confirm the code/data causes recorded in the findings report.

At minimum verify:

### F01 — misleading empty state

`apps/learnit-next/src/integration/atlas/surface.js`

Blob expected on G4:

`aea13ae66fdeeddae6a32b46f8c53875f6a754ad`

Verify the legacy surface can show:

`Aucun parcours Atlas installé`

while the classic library can contain the imported rich V4 course.

### F02 — activity obscured by progress detail

`apps/learnit-next/src/ui/render.js`

Blob expected:

`0fc4b5027c82d038f69d402f97f8d0e059c5401c`

Verify active-session DOM order places the large objective surface before the activity form.

### F03 — reservoir model no longer primary

`apps/learnit-next/src/main.js`

Blob expected:

`828997da351fc63b72adacf61f330fe2fcdd8f31`

Verify `atlas-r13-reservoir` still exists historically and the session-owned CSS hides the legacy progress block.

This is reference evidence only. Do not reactivate the old planner wholesale.

### F04 — duplicate lesson/flashcard controls

`apps/learnit-next/src/ui/activity_presenters.js`

Blob expected:

`fe38702b97f2f243101bfd0ae894b43aaeb2fbaf`

Verify:
- lesson local Continue -> `Prêt à continuer`;
- flashcard local reveal -> `Réponse affichée`;
- flashcard local Continue -> `Prêt à continuer`;
- outer served form adds another Continue.

### F05 — learner-facing provenance/program jargon

Exact repaired showcase blob expected:

`03ed1d5819911c23734980f89716f4ca18a6bca4`

Verify learner-facing/internal leakage includes:
- `Student V0.1 Showcase`;
- `kit canonique Atlas M1 0.3`;
- `de la source`.

### F06 — constructed-answer keyboard brittleness

`apps/learnit-next/src/core/activity_semantics.js`

Blob expected:

`07c4595332419da1da0473a9715f09894620f6bd`

Verify global `canonical-text-match-v1` is still exact after NFC/trim/whitespace collapse.

Verify the showcase constructed activity currently accepts only:

`−1 + 4i`

and ordinary keyboard-equivalent forms such as `-1 + 4i` do not match.

Do not change the global scoring rule in this wave.

---

# PHASE 1 — CREATE TWO INDEPENDENT AUTHOR TRACKS

## 3. Child authority

Create two child issues under coordinator #429.

### Track A issue

Title:

`Student V0.1 — G5 finding PRODUCT UX R1 repair`

Create branch exactly from common base:

`student-v01/g5-finding-product-ux-r1`

Create DRAFT PR against:

`student-v01/fanin-b`

whose exact base is:

`18b925436777943b19c4b031c24659ad60dee133`

Create:

`work-packages/ATLAS-WP-047.json`

and:

`docs/programs/student-v0.1/jobs/JOB_10A_G5_PRODUCT_UX_R1.md`

### Track B issue

Title:

`Student V0.1 — G5 finding SHOWCASE CONTENT R2 repair`

Create branch exactly from common base:

`student-v01/g5-finding-showcase-r2`

Create DRAFT PR against the same exact base branch.

Create:

`work-packages/ATLAS-WP-048.json`

and:

`docs/programs/student-v0.1/jobs/JOB_10B_G5_SHOWCASE_R2.md`

Both work packages must preserve the ATLAS-WP-046 invariants.

The branches may independently modify the central CI workflow for exact-head transport, but that workflow is not role payload and must not be copied between siblings.

---

# TRACK A — PRODUCT UX R1

## 4A. Exact scope

Allowed product payload paths:

- `apps/learnit-next/src/integration/atlas/surface.js`
- `apps/learnit-next/src/ui/render.js`
- `apps/learnit-next/src/ui/activity_presenters.js`
- `apps/learnit-next/src/ui/objective_progress.js`
- `apps/learnit-next/src/atlas.css`
- `apps/learnit-next/tests/student_v01_g5_findings_ux.py`
- `apps/learnit-next/tests/browser_student_v01_g5_findings_ux.py`

Allowed control/evidence paths:

- `work-packages/ATLAS-WP-047.json`
- `docs/programs/student-v0.1/jobs/JOB_10A_G5_PRODUCT_UX_R1.md`
- `.github/workflows/learnit-next-ci.yml`
- `qualification/STUDENT_V01_G5_PRODUCT_UX_R1_RESULT.md`

Forbidden:

- `apps/learnit-next/src/core/activity_semantics.js`
- `apps/learnit-next/source_manifest.json`
- `apps/learnit-next/build.py`
- `apps/learnit-next/index.template.html`
- `contracts/**`
- `authoring/**`
- `showcase/**`
- `pilot/**`
- `qa/**`
- `governance/**`

If a product repair seems to require forbidden paths, HOLD. Do not widen scope silently.

---

## 5A. Solve the UX defects minimally

### A1 — truthful top-level surface

Do not extend the legacy Atlas planner to all rich V4 families.

Instead ensure:

- if one or more installed rich V4 courses exist but none is eligible for the legacy Atlas planner, the UI must **not** display `Aucun parcours Atlas installé`;
- the actual library/course becomes the primary visible surface;
- there must be no simultaneous “no course/no Atlas path” claim contradicting a visible imported course;
- no internal “Atlas compatibility” concept is exposed to the learner.

If there are genuinely no installed courses, an empty-state may remain, but its wording must be learner-oriented rather than an internal planner diagnosis.

### A2 — activity is primary

During an active Student V0.1 session:

- the activity heading and activity controls must be the primary content;
- the large full `Progression par objectif` panel must not sit between the activity heading and the activity itself;
- `Prochaine action recommandée` must not be rendered as a competing pre-activity instruction while an activity is already active;
- detailed objective facts may be available through explicit progressive disclosure such as `Voir ma progression`, collapsed by default.

The simple overall `3/11 activités` progress may remain.

### A3 — compact per-objective reservoirs/buckets

Restore the **useful visual concept**, not the old planner implementation.

Add a compact per-objective progress presentation using the current objective-progress data.

For every course objective show:

- one small reservoir/bucket visual whose fill/state changes with objective status;
- objective label;
- a learner label for the state.

Use the current canonical states:

- `not-started` -> `À découvrir` or equivalent learner wording;
- `training` -> `En apprentissage`;
- `review-needed` -> `À renforcer`;
- `ready-for-validation` -> `À confirmer`;
- `validated-recently` -> `Acquis récemment`.

Requirements:
- compact enough not to push the activity below the fold on normal desktop;
- state must not rely on color alone;
- accessible text must expose objective + state;
- keyboard users must not encounter meaningless decorative controls;
- if interactive detail is provided, it must have correct button/disclosure semantics.

Do not use the historic R13 planner as a new source of truth. Reuse only the visual idea/state vocabulary when safe.

### A4 — one lesson interaction path

A lesson must expose one clear learner action:

`Continuer`

There must not be a local Continue that changes to `Prêt à continuer` plus another outer Continue.

Preferred behavior:

- lesson content;
- one outer Continue;
- submit directly returns `{acknowledged:true}`.

Non-scored semantics remain unchanged.

### A5 — one flashcard interaction path

Flashcard flow must be exactly:

1. `Afficher la réponse`;
2. answer/explanation appears;
3. one `Continuer` becomes available;
4. learner continues.

No learner-visible:
- `Réponse affichée`;
- `Prêt à continuer`;
- duplicate Continue controls.

The reveal remains mandatory before completion.

Non-scored semantics remain unchanged.

### A6 — do not “fix” constructed scoring in product

`canonical-text-match-v1` and `activity_semantics.js` remain byte-identical.

Track B owns the showcase-specific accepted variants.

---

## 6A. Product-specific regression tests

Create deterministic tests that fail on the G4 baseline and pass only after repair.

At minimum prove:

1. rich V4 installed + zero legacy-planner-compatible courses -> no misleading `Aucun parcours Atlas installé`;
2. active session DOM order makes the activity form primary and does not inject the full objective recommendation panel before it;
3. compact progress exposes every objective and one canonical state each;
4. compact state has non-color accessible text;
5. full detail is collapsed/progressive disclosure when present;
6. lesson has exactly one visible continuation control;
7. flashcard before reveal has exactly one reveal control and no usable continuation;
8. after reveal there is exactly one visible continuation and no `Réponse affichée`/`Prêt à continuer` control copy;
9. flashcard cannot complete before reveal;
10. lesson/flashcard remain non-scored;
11. qcm/fill/constructed/matching/order/classify presentation remains unchanged functionally;
12. secret boundary remains intact;
13. reload/resume/completion remains intact;
14. desktop and mobile browser smoke PASS;
15. keyboard navigation PASS.

Run existing relevant suites unchanged, including at minimum:

- `student_v01_activity_presentation.py`
- `browser_student_v01_activity_presentation.py`
- `student_v01_served_v4_integration.py`
- `browser_student_v01_served_v4_integration.py`
- `student_v01_learning_runtime.py -v`
- `student_v01_fanin_a.py`
- `student_v01_fanin_b.py`
- `atlas_m2_ux_clarity.py -v`
- canonical build/regression checks used by G4.

Build twice and record new deterministic app bytes/SHA-256.

Do not expect the old 478657-byte hash after product code changes.

---

## 7A. Product exact-head CI

Recompose only the minimum bounded route in:

`.github/workflows/learnit-next-ci.yml`

for branch:

`student-v01/g5-finding-product-ux-r1`

Require:

- exact common-base ancestry;
- remote HEAD binding;
- product scope;
- new G5 UX regression tests;
- relevant existing Student V0.1 regressions;
- deterministic double build;
- Repository governance.

Temporary same-head DRAFT carrier to main is allowed only if technically required for CI routing.

Never merge the carrier.

The authoritative repair PR remains the stacked child PR.

---

## 8A. Product result/evidence split

Freeze an executable product result:

`PRODUCT_RESULT_SHA`

Then add only:

`qualification/STUDENT_V01_G5_PRODUCT_UX_R1_RESULT.md`

as evidence.

Record:

`PRODUCT_EVIDENCE_HEAD`

Allowed product verdicts:

- `PASS_STUDENT_V01_G5_PRODUCT_UX_R1_READY_FOR_CORRECTIVE_REVIEW`
- `HOLD_STUDENT_V01_G5_PRODUCT_UX_R1_NEEDS_REWORK`
- `FAIL_STUDENT_V01_G5_PRODUCT_UX_R1_SCOPE_VIOLATION`

Do not consume this result in Track B.

---

# TRACK B — SHOWCASE CONTENT R2

## 4B. Independence reset

Before Track B authoring:

- return to the exact common base;
- fresh-read source authority and common-base showcase;
- do not read PRODUCT_RESULT_SHA implementation/diff/qualification;
- do not copy any product branch file.

This is authoring separation, not independent semantic review.

---

## 5B. Exact scope

Allowed showcase payload:

`showcase/student-v0.1/nombres-complexes/**`

Allowed control/evidence:

- `work-packages/ATLAS-WP-048.json`
- `docs/programs/student-v0.1/jobs/JOB_10B_G5_SHOWCASE_R2.md`
- `.github/workflows/learnit-next-ci.yml`
- `qualification/STUDENT_V01_G5_SHOWCASE_R2_RESULT.md`

Forbidden:

- `apps/**`
- `contracts/**`
- `authoring/**`
- `pilot/**`
- `qa/**`
- `governance/**`

The source authority remains exactly:

`authoring/v2/atlas/nombres_complexes_atlas.json`

at blob:

`7f83784e8719917496a694b2ad170d724190fd04`

SHA-256:

`3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`

Do not mutate source.

---

## 6B. Learner-copy repair

Remove internal authoring/program vocabulary from learner-visible content.

At minimum repair:

### Package title

Replace internal:

`Nombres complexes — Student V0.1 Showcase`

with a learner-facing title such as:

`Nombres complexes — Conjugué et module`

### Package description

Remove:

`kit canonique Atlas M1 0.3`

Keep only learner-relevant subject/duration framing supported by source.

### Flashcard explanation

Replace the phrase ending:

`de la source`

with direct learner language, for example:

`Cette règle s’applique par exemple à 2 + 3i, −1 − 4i et 5 − 2i.`

Do not imply an external source the learner cannot see.

### Matching explanation

Replace:

`... de la source`

with learner-facing course wording, e.g. the examples worked in this course.

### Version/program labels

If `versionLabel` or any other learner-reachable metadata contains internal `Student V0.1`, `Showcase`, `Atlas M1`, or `canonique` jargon, replace it with neutral learner-facing wording.

Run a deterministic scan over all learner-visible fields.

Forbidden learner-visible internal phrases include at minimum:

- `de la source`
- `la source`
- `kit canonique`
- `Atlas M1`
- `Student V0.1 Showcase`

Do not ban legitimate mathematical use of ordinary words when context differs; make the scanner path-aware.

---

## 7B. Constructed accepted-response repair

Do **not** alter global scoring semantics.

For the exact constructed prompt:

`Calculer le conjugué de −1 − 4i.`

preserve the mathematically correct target:

`−1 + 4i`

Add a bounded finite authored set of ordinary keyboard-equivalent forms.

At minimum include and prove correct:

- `−1 + 4i`
- `-1 + 4i`
- `−1+4i`
- `-1+4i`
- `−1 + 4 i`
- `-1 + 4 i`
- `−1+4 i`
- `-1+4 i`

Do not add algebraically different expressions.

Do not add broad fuzzy matching.

Do not lowercase globally.

Do not parse mathematics in product code.

Prove at least one genuinely incorrect response remains incorrect, e.g.:

`1 + 4i`

and:

`−1 − 4i`

The acceptedResponses remain scoring secrets and must not cross learner-safe presentation.

---

## 8B. Source fidelity and revision hygiene

Preserve:

- 42-minute course duration;
- 11 activities;
- exact objective IDs and meanings;
- activity order;
- activity family;
- learningPhase;
- assessmentRole;
- factual mathematics;
- no new source facts;
- no media introduction.

Rotate revision IDs/digests only as required by changed learner payload.

Requirements:

- each changed activity gets correct new revision identity/digest;
- unchanged activities remain stable where contract permits;
- course revision identity/digest updates correctly;
- package revision identity/digest updates correctly;
- provenance map/source basis/author audit/validation/quality/factory-context artifacts are rebound to the repaired kit;
- source remains unchanged.

Run:

- V4 canonical validation;
- pedagogical quality;
- source traceability;
- revision-digest hygiene;
- secret-boundary checks;
- constructed-variant evaluator checks.

Require pedagogical quality at least:

`EXCELLENT_BY_PROFILE`

unless the authoritative quality tool produces a stronger/equivalent accepted label.

---

## 9B. Semantic-review boundary

This author session may not independently PASS semantic review of its own repaired showcase.

The final Track B evidence must say exactly:

`SEMANTIC_REVIEW: PENDING_INDEPENDENT_CORRECTIVE_REVIEW`

Do not reuse G3 R1 semantic PASS as proof for changed learner text.

Do not run a fake same-session “independent” review.

The later ATLAS-WP-049 job owns new semantic review.

---

## 10B. Showcase exact-head CI

Create the minimum bounded branch route in the child branch workflow.

Require:

- exact common-base ancestry;
- source blob/hash exact;
- changed-path scope;
- V4 canonical PASS;
- learner-copy internal-jargon scan PASS;
- constructed keyboard-variant positive and negative cases PASS;
- revision/digest hygiene PASS;
- pedagogical quality PASS;
- source traceability PASS;
- Repository governance PASS.

Factory context may be regenerated/rebound, but final Factory PASS that depends on a new independent semantic review is deferred to ATLAS-WP-049.

Temporary same-head DRAFT carrier is allowed only for CI transport, never merge.

---

## 11B. Showcase result/evidence split

Freeze:

`SHOWCASE_RESULT_SHA`

Then add only:

`qualification/STUDENT_V01_G5_SHOWCASE_R2_RESULT.md`

as evidence.

Record:

`SHOWCASE_EVIDENCE_HEAD`

Allowed verdicts:

- `PASS_STUDENT_V01_G5_SHOWCASE_R2_READY_FOR_CORRECTIVE_REVIEW`
- `HOLD_STUDENT_V01_G5_SHOWCASE_R2_NEEDS_REWORK`
- `FAIL_STUDENT_V01_G5_SHOWCASE_R2_SCOPE_VIOLATION`

---

# PHASE 3 — COORDINATOR AUDIT

## 12. Verify separation

After both child tracks stop:

1. verify both child branches started at exact common base;
2. verify both authoritative PRs are DRAFT/unmerged;
3. compare common base to each RESULT_SHA;
4. classify `.github/workflows/learnit-next-ci.yml` as control transport, not role payload;
5. require product payload and showcase payload path sets have empty intersection;
6. require product track did not modify showcase/authoring/contracts/core semantics;
7. require showcase track did not modify apps/contracts/authoring source;
8. require neither branch consumed the sibling RESULT/EVIDENCE;
9. require G5 final decision files remain absent;
10. require JOB09 Phase-A evidence remains untouched.

If either child is HOLD/FAIL, the wave is not ready for fan-in.

Do not repair one child from the coordinator.

---

## 13. Final result block

Return exactly:

```text
STUDENT_V01_G5_CORRECTIVE_AUTHOR_WAVE_RESULT
COMMON_BASE: 18b925436777943b19c4b031c24659ad60dee133
G4_CANDIDATE_SHA: 757ed15e840bfca603de0eac3bef1e9d5ff3483d
G5_REPLAY_PREP_SHA: a72897c209b8ea7bd8672cc8a95be939ecee6fb8
COORDINATOR_ISSUE: 429
COORDINATOR_PR: <coordinator prep PR>
PRODUCT_ISSUE: <child issue>
PRODUCT_PR: <child PR>
PRODUCT_WP: ATLAS-WP-047
PRODUCT_RESULT_SHA: <sha|BLOCKED>
PRODUCT_EVIDENCE_HEAD: <sha|BLOCKED>
PRODUCT_FALSE_EMPTY_STATE: PASS|FAIL|BLOCKED
PRODUCT_ACTIVITY_PRIMARY: PASS|FAIL|BLOCKED
PRODUCT_COMPACT_OBJECTIVE_BUCKETS: PASS|FAIL|BLOCKED
PRODUCT_LESSON_FLOW: PASS|FAIL|BLOCKED
PRODUCT_FLASHCARD_FLOW: PASS|FAIL|BLOCKED
PRODUCT_CORE_SCORING_UNCHANGED: PASS|FAIL|BLOCKED
PRODUCT_REGRESSIONS: PASS|FAIL|BLOCKED
PRODUCT_INTEGRATION_CI: PASS|FAIL|BLOCKED
PRODUCT_GOVERNANCE: PASS|FAIL|BLOCKED
PRODUCT_SCOPE: PASS|FAIL|BLOCKED
PRODUCT_VERDICT: <token>
SHOWCASE_ISSUE: <child issue>
SHOWCASE_PR: <child PR>
SHOWCASE_WP: ATLAS-WP-048
SHOWCASE_RESULT_SHA: <sha|BLOCKED>
SHOWCASE_EVIDENCE_HEAD: <sha|BLOCKED>
SHOWCASE_INTERNAL_JARGON_REMOVED: PASS|FAIL|BLOCKED
SHOWCASE_CONSTRUCTED_VARIANTS: PASS|FAIL|BLOCKED
SHOWCASE_SOURCE_UNCHANGED: PASS|FAIL|BLOCKED
SHOWCASE_STRUCTURE_UNCHANGED: PASS|FAIL|BLOCKED
SHOWCASE_REVISION_DIGEST_HYGIENE: PASS|FAIL|BLOCKED
SHOWCASE_V4_CANONICAL: PASS|FAIL|BLOCKED
SHOWCASE_PEDAGOGICAL_QUALITY: PASS|FAIL|BLOCKED
SHOWCASE_SOURCE_TRACEABILITY: PASS|FAIL|BLOCKED
SHOWCASE_SEMANTIC_REVIEW: PENDING_INDEPENDENT_CORRECTIVE_REVIEW|BLOCKED
SHOWCASE_INTEGRATION_CI: PASS|FAIL|BLOCKED
SHOWCASE_GOVERNANCE: PASS|FAIL|BLOCKED
SHOWCASE_SCOPE: PASS|FAIL|BLOCKED
SHOWCASE_VERDICT: <token>
PAYLOAD_SCOPE_DISJOINT: PASS|FAIL
CROSS_CONSUMPTION: NONE|PRESENT
JOB09_PHASE_A_UNCHANGED: PASS|FAIL
G5_FORMAL_STATUS: PENDING_HUMAN
NEXT_GATE: ATLAS-WP-049_INDEPENDENT_CORRECTIVE_REVIEW_AND_FANIN|BLOCKED
FINAL_VERDICT: <token>
```

Coordinator-level allowed verdicts:

- `PASS_STUDENT_V01_G5_CORRECTIVE_AUTHOR_WAVE_READY_FOR_INDEPENDENT_REVIEW`
- `HOLD_STUDENT_V01_G5_CORRECTIVE_AUTHOR_WAVE_CHILD_NOT_READY`
- `HOLD_STUDENT_V01_G5_CORRECTIVE_AUTHOR_WAVE_AUTHORITY_DRIFT`
- `FAIL_STUDENT_V01_G5_CORRECTIVE_AUTHOR_WAVE_INDEPENDENCE_OR_SCOPE`

A PASS from this job authorizes only preparation/execution of ATLAS-WP-049.

It does not authorize fan-in here, G4 R1 PASS, a new G5 replay, or student sessions.
