# /AUDIT /SOLVE /BUILD — G3
## Student V0.1 — Wave 2 review and Fan-in B input freeze

Repository: `stefm78/learnit-platform`  
Authority issue: `#419`  
Program issue: `#380`  
Wave 2 control issue: `#403`  
Work package: `ATLAS-WP-041`

Branch:

`student-v01/g3-wave2-review`

Exact anchors:

- `G3_BASE = 7c13d67a76705b4452304c0f6a882504bc7701a7`
- `REPAIRED_PRODUCT_SHA = bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- `JOB05_R1_RESULT_SHA = 1c92cad7ea576a613b6f198768bbebd114a06082`
- `JOB05_R1_EVIDENCE_HEAD = 9dbd5c97603be864a57cc0f7f46047ee41772b34`
- `JOB06_RESULT_SHA = 8e0e3c43968cf0cf442e0e47b73bc38fc19ae565`
- `JOB06_EVIDENCE_HEAD = 28d6e2968fcbe79d7225b2c29efda22317af09c8`
- `JOB07_R2_RESULT_SHA = 5e492fddc4d5cf00c71bdb770eb1aeac11a63803`
- `JOB07_R2_EVIDENCE_HEAD = a2695560810b9a1bf3761d065326ff7df09c2252`

JOB06 Factory target:

- `contextDigest = sha256:c9c90b779ea0c40ef0013bae3f78c3852de48cff36b4927f38ef9e22e21a9730`
- `kitSha256 = sha256:694f6713c2399e680f4748b925c9b293a9c9236cf25c593ce2f900ba5cec918b`
- `briefSha256 = sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`
- `sourceSetDigest = sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`
- exact source blob: `7f83784e8719917496a694b2ad170d724190fd04`
- source ID: `nombres-complexes-atlas-v2`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge or cherry-pick anything.

---

## 0. Role

You are the independent G3 Control Room reviewer.

G3 is a **review gate**, not an integration job.

Your mission is to decide whether the accepted Wave 2 outputs are ready to enter JOB08 Fan-in B, while closing the one intentionally deferred JOB06 semantic-review gate.

You may create only review/freeze evidence allowed by `ATLAS-WP-041`.

You may not modify or repair product, QA, showcase, packaging, authoring, schema, workflow or governance implementation.

A PASS from G3 authorizes only preparation of JOB08.

---

## 1. Fresh authority rebind

Before any mutation:

1. fresh-read active Human Control Plane HEAD;
2. bind exact UCP/UAO/governance authority;
3. fresh-read repository `main`;
4. read:
   - `docs/programs/student-v0.1/PROGRAM_CHARTER.md`
   - `docs/programs/student-v0.1/COORDINATION.yaml`
   - `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`
   - `docs/architecture/clean-generation/MULTI_AI_EXECUTION_V1.md`
   - issue #403
   - issue #419
   - `work-packages/ATLAS-WP-041.json`
5. fresh-read PR #411, #413, #408 and #418;
6. verify all are still DRAFT/unmerged;
7. verify their exact result/evidence SHAs match the anchors above;
8. verify this G3 branch descends exactly from `G3_BASE`.

If any accepted input head or authority binding drifted, stop:

`HOLD_STUDENT_V01_G3_EVIDENCE_DRIFT`

Do not silently select a newer sibling head.

---

## 2. Independence firewall for JOB06 semantic review

This section is mandatory and must happen **before** reading JOB06 author-side conclusions.

During the semantic-review phase you may receive only:

- exact source bytes;
- exact learner brief;
- exact candidate kit;
- exact Factory context;
- public repository review/factory authorities.

Read:

- `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md`
- `authoring/factory/README.md`
- `authoring/factory/factory_gate.py`
- canonical V4 schema/validator public authorities as needed.

### Forbidden before semantic review is frozen

Do **not** read:

- `showcase/student-v0.1/nombres-complexes/AUTHOR_AUDIT.md`
- `showcase/student-v0.1/nombres-complexes/PEDAGOGICAL_QUALITY_REPORT.json`
- `showcase/student-v0.1/nombres-complexes/PROVENANCE_MAP.json`
- `showcase/student-v0.1/nombres-complexes/SOURCE_BASIS.md`
- `qualification/STUDENT_V01_JOB06_SHOWCASE_RESULT.md`
- author scratchpad/chat/context
- any prior semantic-review conclusion for this candidate.

If you already consumed any forbidden author context in the new session, set independence truthfully and return semantic HOLD/G3 HOLD. Do not fabricate independence.

---

## 3. Materialize exact JOB06 reviewer inputs

Without committing them on the G3 branch, materialize into a temporary directory from exact Git objects:

### Source

From exact Wave 2 source authority:

`281dc7470d51682c5e6d79d3fff54c46cfbced3b:authoring/v2/atlas/nombres_complexes_atlas.json`

Require Git blob:

`7f83784e8719917496a694b2ad170d724190fd04`

and recompute source SHA256:

`sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`

### Candidate, brief and context

Materialize from exact `JOB06_RESULT_SHA`:

- `showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json`
- `showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json`
- `showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT.json`

Recompute exact bytes/hashes and require them to bind the frozen Factory target.

If any byte/hash differs, stop G3 with evidence drift.

---

## 4. Independent adversarial semantic review

Act as the independent reviewer defined by:

`authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md`

Review all six required dimensions:

1. `sourceFidelity`
2. `answerCorrectness`
3. `ambiguity`
4. `objectiveCoverage`
5. `validationTransfer`
6. `learnerFit`

### Required depth

Do not merely sample activities.

For the exact final JOB06 candidate:

- independently inspect every activity;
- independently recalculate every scored answer/correct mapping/order/matching/constructed accepted answer;
- check every important explanation and learner-visible claim against the source;
- inspect validation and transfer independence;
- challenge ambiguity and distractor equivalence;
- challenge the 42-minute learner fit against the learner brief.

For evidence-required dimensions, derive source evidence directly from the exact source JSON and cite:

- `sourceId = nombres-complexes-atlas-v2`
- exact JSON locator;
- concise basis.

Do not use JOB06's provenance map as your source evidence.

### Output

Create exactly:

`qualification/STUDENT_V01_G3_JOB06_SEMANTIC_REVIEW.json`

It must match:

`learnit.atlas.semantic_review.v1`

and bind target exactly to the four frozen hashes.

Independence must state truthfully:

```json
{
  "authorScratchpadSeen": false,
  "authorActiveContextReused": false
}
```

Only use:

`PASS_SEMANTIC_REVIEW_V1`

if every required dimension passes and no blocking/major finding exists.

Otherwise use semantic HOLD.

### Freeze the independent review before widening context

Commit the semantic-review JSON **alone** before reading the previously forbidden JOB06 author-side audit/provenance/quality/qualification files.

Record that commit as:

`SEMANTIC_REVIEW_SHA`

After this commit, do not change the review JSON. Any later discovered semantic defect invalidates G3 rather than silently editing the review.

If semantic review HOLDs, G3 may stop after recording the minimum durable HOLD evidence. Do not repair JOB06.

---

## 5. Deterministic Factory gate

After the semantic review is durably frozen, run the deterministic Factory gate using exact materialized inputs:

```bash
python -B authoring/factory/factory_gate.py gate \
  --kit <exact-job06-candidate> \
  --brief <exact-job06-brief> \
  --review qualification/STUDENT_V01_G3_JOB06_SEMANTIC_REVIEW.json \
  --source nombres-complexes-atlas-v2=<exact-source> \
  --json
```

Store the exact raw JSON output as:

`qualification/STUDENT_V01_G3_JOB06_FACTORY_RESULT.json`

Require deterministic Factory PASS.

If semantic PASS exists but Factory rejects binding/canonical/quality/semantic state, return:

`HOLD_STUDENT_V01_G3_FACTORY_GATE`

Do not weaken or repair anything.

---

## 6. Only now open the full JOB06 author-side evidence

After `SEMANTIC_REVIEW_SHA` exists, you may read:

- JOB06 qualification result;
- AUTHOR_AUDIT;
- PEDAGOGICAL_QUALITY_REPORT;
- PROVENANCE_MAP;
- SOURCE_BASIS;
- V4_VALIDATION_REPORT;
- FACTORY_REVIEW_REQUEST.

Use them only to cross-check prior author claims against your already-frozen independent review.

Rerun on exact candidate bytes:

- canonical V4 validation;
- pedagogical quality.

Require no contradiction with the accepted JOB06 claims.

Do not modify JOB06 content.

---

## 7. Audit accepted result/evidence separation

Independently verify for each accepted output:

### Served-V4 repair

- executable `bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- evidence head `7c13d67a76705b4452304c0f6a882504bc7701a7`
- evidence-only delta changes only its qualification evidence.

### JOB05 R1

- result `1c92cad7ea576a613b6f198768bbebd114a06082`
- evidence `9dbd5c97603be864a57cc0f7f46047ee41772b34`
- authoritative result diff from G3 base contains only accepted QA/workflow/prompt/WP paths.

### JOB06

- result `8e0e3c43968cf0cf442e0e47b73bc38fc19ae565`
- evidence `28d6e2968fcbe79d7225b2c29efda22317af09c8`
- qualified role payload is the exact `showcase/student-v0.1/nombres-complexes/**` content.

### JOB07 R2

- result `5e492fddc4d5cf00c71bdb770eb1aeac11a63803`
- evidence `a2695560810b9a1bf3761d065326ff7df09c2252`
- qualified role payload is exact `pilot/student-v0.1/**` code plus accepted integration-route evidence.

Any ambiguous result/evidence relation is G3 HOLD.

---

## 8. Cross-output compatibility proof — no commit of temporary integration

G3 must answer whether the exact accepted outputs can coherently enter one Fan-in B.

Use a temporary worktree/directory only.

Do not commit imported Wave 2 payload.

### 8.1 Exact showcase on repaired product

Start from exact repaired application bytes produced by G3 base.

Materialize exact JOB06 candidate from `JOB06_RESULT_SHA`.

Using real product controls, prove at minimum:

- canonical import succeeds;
- course starts;
- lesson/flashcard non-scored behavior is preserved;
- each activity family present in the showcase is reachable;
- scored activities evaluate coherently;
- reload/resume works during the showcase;
- full 42-minute logical journey can reach completion;
- learner-safe secret boundary remains intact.

Run browser proof at desktop and mobile if no earlier causal failure exists.

This is compatibility evidence only, not a human learner-readiness test.

### 8.2 Exact JOB07 R2 packaging implementation with exact JOB06 showcase

Materialize the exact accepted `pilot/student-v0.1/**` files from `JOB07_R2_RESULT_SHA` into a temporary workspace.

Do not modify them.

Use the exact generic JOB07 R2 package builder to package:

- repaired Learn-it app bytes;
- exact JOB06 showcase kit bytes.

Require:

- builder accepts the candidate canonically;
- manifest binds exact app and JOB06 kit bytes/hashes;
- two package builds are deterministic;
- extracted package integrity passes;
- documented start mode remains valid;
- real packaged browser smoke uses the exact JOB06 showcase, not the R2 generated qualification kit;
- desktop/mobile start and interaction pass;
- reload/resume and completion pass if the generic harness supports the exact showcase shape;
- no external network dependency appears.

If the generic R2 browser harness assumes all eight families and cannot directly run the six-family showcase, create only a **temporary G3 probe outside Git** using public product behavior. Do not alter R2 code just to obtain G3 PASS.

A failure of exact showcase + exact package implementation is a G3 compatibility HOLD.

---

## 9. Cross-output overlap matrix

Compute exact changed-path sets for JOB05 R1, JOB06 and JOB07 R2 from their authoritative bases/results.

Classify every changed path into exactly one of:

- `candidate_payload`
- `evidence_or_control_only`
- `integrator_owned_recompose`
- `forbidden_or_unresolved`

Expected hypothesis to challenge:

### JOB05 R1 candidate payload

QA harness/fixture paths under:

`qa/student-v0.1/**`

### JOB06 candidate payload

`showcase/student-v0.1/nombres-complexes/**`

### JOB07 R2 candidate payload

`pilot/student-v0.1/**`

### Integrator-owned recompose

Central workflow modifications:

`.github/workflows/learnit-next-ci.yml`

Do not blindly cherry-pick sibling workflow versions into JOB08.

Prompt/WP/qualification files are provenance/control evidence, not learner candidate payload.

If any same candidate-payload path has conflicting accepted bytes across siblings, G3 HOLDs.

---

## 10. /solve — freeze the minimum JOB08 integration plan

If all review and compatibility checks pass, independently choose the minimum Fan-in B composition.

Do not simply say "merge all PASS branches".

Freeze:

1. exact future JOB08 base: final G3 evidence head;
2. accepted executable product already present in that base;
3. exact payload source SHA for JOB05 R1 QA files;
4. exact payload source SHA for JOB06 showcase files;
5. exact payload source SHA for JOB07 R2 pilot files;
6. exact per-path import policy;
7. central files that JOB08 owns and must recompose;
8. required integration order;
9. tests that must run on the exact combined candidate;
10. stop/rollback rules.

Preferred integration order to challenge:

```text
G3 evidence head
→ import exact JOB05 R1 QA payload
→ import exact JOB06 showcase payload
→ import exact JOB07 R2 pilot payload
→ integrator recomposes central workflow only
→ canonical/source-manifest/build identity audit
→ real showcase through repaired served product
→ package exact showcase with integrated pilot builder
→ full contradictory QA
→ deterministic build/package
→ exact-head CI
→ G4 candidate qualification
```

Note: source manifest is changed only if the accepted candidate payload introduces declared build sources requiring it. Do not change it merely because QA/showcase/pilot files were added.

No role-owned product/content/package repair is allowed in JOB08.

---

## 11. Fan-in B input manifest

Create:

`qualification/STUDENT_V01_G3_FANIN_B_INPUT_MANIFEST.json`

Use a small explicit schema, e.g.:

`learnit.student-v0.1.g3-fanin-b-inputs.v1`

It must include:

- G3 base;
- repaired product SHA;
- accepted result/evidence SHAs;
- semantic-review commit SHA;
- Factory verdict;
- exact candidate-payload path lists grouped by source result SHA;
- path Git blob SHA if practical;
- evidence/control-only paths excluded from payload;
- integrator-owned central paths;
- exact integration order;
- required G4/JOB08 tests;
- explicit forbidden silent-repair rule;
- rollback anchors.

Do not put branch-tip aliases where an exact SHA is available.

The manifest freezes inputs. It does not integrate them.

---

## 12. Repository governance and G3 scope

No central CI workflow modification is authorized in G3.

Repository governance on the G3 review branch must PASS.

Exact `G3_BASE..RESULT_SHA` may change only:

- `work-packages/ATLAS-WP-041.json`
- `docs/programs/student-v0.1/jobs/JOB_G3_WAVE2_REVIEW.md`
- `qualification/STUDENT_V01_G3_JOB06_SEMANTIC_REVIEW.json`
- `qualification/STUDENT_V01_G3_JOB06_FACTORY_RESULT.json`
- `qualification/STUDENT_V01_G3_FANIN_B_INPUT_MANIFEST.json`

Then an evidence-only commit may add only:

- `qualification/STUDENT_V01_G3_WAVE2_REVIEW.md`

Any implementation-path mutation is a scope failure.

---

## 13. RESULT_SHA and EVIDENCE_HEAD

Use:

- `SEMANTIC_REVIEW_SHA` = commit adding only the frozen semantic-review JSON;
- `RESULT_SHA` = exact G3 reviewed/frozen state containing semantic review + Factory result + Fan-in B input manifest, before final narrative evidence;
- `EVIDENCE_HEAD` = later commit adding only `qualification/STUDENT_V01_G3_WAVE2_REVIEW.md`.

The narrative evidence must record:

- fresh HCP binding;
- input SHA verification;
- semantic-review process and verdict;
- Factory raw result identity;
- canonical/quality reruns;
- exact compatibility commands/results;
- showcase-on-repaired-product proof;
- showcase-through-R2-package proof;
- path overlap matrix;
- selected JOB08 composition;
- Repository governance run;
- exact scope;
- rollback.

Do not edit the semantic-review JSON after `SEMANTIC_REVIEW_SHA`.

---

## 14. G3 PASS gate

G3 PASS requires:

- HCP/input identities PASS;
- JOB05 R1 accepted evidence intact;
- JOB06 independent semantic review PASS;
- JOB06 deterministic Factory gate PASS;
- JOB06 canonical/quality reruns PASS;
- JOB07 R2 accepted evidence intact;
- exact JOB06 showcase works on repaired served product;
- exact JOB07 R2 builder packages exact JOB06 showcase coherently;
- cross-output payload paths have no unresolved conflicts;
- central workflow overlap is explicitly assigned to JOB08 integrator ownership;
- Fan-in B input manifest complete and exact;
- Repository governance PASS;
- G3 scope PASS.

G3 PASS authorizes only preparation of JOB08 Fan-in B from final `EVIDENCE_HEAD`.

It does not authorize JOB08 execution automatically, G4 PASS, JOB09, main merge, release or real students.

---

## 15. Final result block

Return exactly:

```text
STUDENT_V01_G3_RESULT
G3_BASE: 7c13d67a76705b4452304c0f6a882504bc7701a7
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
JOB05_R1_RESULT_SHA: 1c92cad7ea576a613b6f198768bbebd114a06082
JOB06_RESULT_SHA: 8e0e3c43968cf0cf442e0e47b73bc38fc19ae565
JOB07_R2_RESULT_SHA: 5e492fddc4d5cf00c71bdb770eb1aeac11a63803
SEMANTIC_REVIEW_SHA: <commit adding only semantic review json>
RESULT_SHA: <exact g3 frozen-result sha>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 419
PR: <authoritative g3 pr>
HCP_BINDING: PASS|FAIL
INPUT_IDENTITY: PASS|FAIL
JOB05_R1_ACCEPTED: PASS|FAIL
JOB06_SEMANTIC_REVIEW: PASS|HOLD|FAIL
JOB06_FACTORY_GATE: PASS|HOLD|FAIL|BLOCKED
JOB06_CANONICAL_QUALITY: PASS|FAIL|BLOCKED
JOB07_R2_ACCEPTED: PASS|FAIL
SHOWCASE_ON_REPAIRED_PRODUCT: PASS|FAIL|BLOCKED
SHOWCASE_PACKAGED_WITH_JOB07_R2: PASS|FAIL|BLOCKED
CROSS_OUTPUT_OVERLAP: PASS|FAIL|BLOCKED
FANIN_B_INPUT_MANIFEST: PASS|FAIL|BLOCKED
REPOSITORY_GOVERNANCE: PASS|FAIL|BLOCKED
SCOPE: PASS|FAIL
JOB08_BASE: <EVIDENCE_HEAD if PASS, else BLOCKED>
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_G3_READY_FOR_JOB08`
- `HOLD_STUDENT_V01_G3_EVIDENCE_DRIFT`
- `HOLD_STUDENT_V01_G3_JOB06_SEMANTIC_REVIEW`
- `HOLD_STUDENT_V01_G3_FACTORY_GATE`
- `HOLD_STUDENT_V01_G3_WAVE2_INCOMPATIBLE`
- `FAIL_STUDENT_V01_G3_SCOPE_VIOLATION`
