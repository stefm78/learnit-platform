# /AUDIT /SOLVE /BUILD — JOB 08
## Student V0.1 — Fan-in B final integrator and G4 exact-candidate qualification

Repository: `stefm78/learnit-platform`  
Authority issue: `#425`  
Program issue: `#380`  
Wave 2 control issue: `#403`  
G3 R1 authority: `#423 / PR #424`  
Work package: `ATLAS-WP-044`

Branch:

`student-v01/fanin-b`

Exact anchors:

- `JOB08_BASE = d5050bace4c7dcbb63dcfe44a64ef344434e9bc2`
- `G3_R1_RESULT_SHA = f0b8af8adeab132bec0ebe9410951e6add294c5b`
- `REPAIRED_PRODUCT_SHA = bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- `JOB05_R1_RESULT_SHA = 1c92cad7ea576a613b6f198768bbebd114a06082`
- `JOB06_R1_RESULT_SHA = 80ec72fef535e78013a9f0fb10bedb57f05bc761`
- `JOB07_R2_RESULT_SHA = 5e492fddc4d5cf00c71bdb770eb1aeac11a63803`

Frozen Fan-in B manifest:

`qualification/STUDENT_V01_G3_R1_FANIN_B_INPUT_MANIFEST.json`

Required manifest Git blob:

`d76d624b6e76655b60b1a43b1dafbce22d3eb087`

Expected repaired app:

```text
bytes   478657
sha256  85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e
```

Expected exact repaired-showcase package:

```text
bytes   496658
sha256  a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10
```

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge anything.

Do not cherry-pick sibling commits.

---

## 0. Role

You are the final Student V0.1 Fan-in B integrator.

G3 R1 already froze the exact role payloads and proved they are mutually compatible.

Your job is to materialize those exact payload bytes onto the exact G3 R1 evidence base, recompose the central CI route, and independently qualify one exact integrated automated candidate.

You have **integration authority only**.

You do not have authority to repair:
- product source;
- JOB05 QA;
- JOB06 showcase content;
- JOB07 pilot packaging;
- V4 schema/authoring policy.

If an accepted role payload fails after exact integration, classify and HOLD. Return the defect to the owning role.

A PASS from this job is G4 exact-candidate qualification. It authorizes only preparation of JOB09 / G5 human student-readiness.

---

## 1. Fresh authority rebind

Before mutation:

1. fresh-read active Human Control Plane HEAD;
2. bind exact UCP/UAO/governance authority;
3. fresh-read repository `main`;
4. read:
   - issue #425;
   - `work-packages/ATLAS-WP-044.json`;
   - issue #423 / PR #424;
   - `qualification/STUDENT_V01_G3_R1_WAVE2_REVIEW.md`;
   - `qualification/STUDENT_V01_G3_R1_FANIN_B_INPUT_MANIFEST.json`;
   - `docs/programs/student-v0.1/PROGRAM_CHARTER.md`;
   - `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`.
5. verify PR #424 is still DRAFT/unmerged at exact evidence head `JOB08_BASE`;
6. verify this branch descends exactly from `JOB08_BASE`;
7. fresh-read accepted role PRs and exact result/evidence:
   - JOB05 R1 #413;
   - JOB06 R1 #422;
   - JOB07 R2 #418.
8. verify no accepted role result/evidence SHA has drifted.

If any binding differs, stop:

`HOLD_STUDENT_V01_JOB08_INPUT_DRIFT`

---

## 2. Frozen payload authority

The only role-payload authority is the exact G3 R1 manifest.

Do not infer payload from branch diffs or copy whole branches.

Materialize files individually from immutable result SHAs.

### JOB05 R1 — exact QA payload

From:

`1c92cad7ea576a613b6f198768bbebd114a06082`

materialize exactly:

- `qa/student-v0.1/JOB05_CANONICAL_V4_FIXTURE.json`
  - Git blob `c190fc4f04a7cee5731627e4f6276ee08e39d746`
- `qa/student-v0.1/browser_job05_r1_contradictory_qa.py`
  - Git blob `9c33a185a957b3b3513822a4cc3f72294a867fae`
- `qa/student-v0.1/job05_r1_contradictory_qa.py`
  - Git blob `a7a1ac5baa93df355cc687d4635ff5f9837e30d9`

### JOB06 R1 — exact repaired showcase payload

From:

`80ec72fef535e78013a9f0fb10bedb57f05bc761`

materialize exactly:

- `showcase/student-v0.1/nombres-complexes/AUTHOR_AUDIT.md`
  - `dcbd252559292c9a9b1949b3cf85007cc60949e0`
- `FACTORY_CONTEXT.json`
  - `ea5ce453421bfe25db8e1a16597953cad77ac2db`
- `FACTORY_REVIEW_REQUEST.md`
  - `4e6903e9854c357a6d99178d0b8b4ba2614a5c67`
- `LEARNER_BRIEF.json`
  - `6c4fb770f12690a3cb338c82fc77bf9b323c3b06`
- `PEDAGOGICAL_QUALITY_REPORT.json`
  - `747daee9ad0ff3dc8c4c6b7c2edd621bbc26e963`
- `PROVENANCE_MAP.json`
  - `7fb0a7153a22c8e2b9bb6b899b152867e89f0cfc`
- `SOURCE_BASIS.md`
  - `f10e8f0f78512f4b3c95befb28e9fe565e8c99c9`
- `V4_VALIDATION_REPORT.json`
  - `711ebee54d9007364ffadfa964e907b09bdc550d`
- `nombres_complexes_student_v01_v4.json`
  - Git blob `03ed1d5819911c23734980f89716f4ca18a6bca4`
  - SHA-256 `da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`

### JOB07 R2 — exact pilot payload

From:

`5e492fddc4d5cf00c71bdb770eb1aeac11a63803`

materialize exactly:

- `pilot/student-v0.1/browser_generated_v4_probe.py`
  - `b5a4ecbf5879effb698929e17fb5c263ba8400c7`
- `browser_pilot_package.py`
  - `ae86fb159e322b24c1ce37ca662d4d5674422b43`
- `build_pilot_package.py`
  - `47ccfd8a7f6df23bc2c77b057f54f4502cff09a0`
- `ci_job07_r2.py`
  - `8c27a4dbdb9e2b16051da6d77b1a6a243705b555`
- `materialize_qualification_kit.py`
  - `2c805242f23825bca87fdacc46bdb0c241bb5b39`
- `test_pilot_package.py`
  - `6726504f8ca6540cb21a4372c5035a29cd848443`

For every file:

1. fetch exact bytes from the exact result commit;
2. materialize them into the JOB08 branch;
3. verify `git hash-object <path>` equals the frozen blob;
4. do not edit the file afterward.

Do not import sibling:
- work packages;
- job prompts;
- qualification files;
- workflow variants.

---

## 3. Product immutability

Before and after payload materialization, bind exact product/build inputs.

The following must remain byte-identical to `JOB08_BASE`:

- `apps/learnit-next/src/**`
- `apps/learnit-next/build.py`
- `apps/learnit-next/index.template.html`
- `apps/learnit-next/source_manifest.json`
- `contracts/**`
- `authoring/**`

Do not add the new Fan-in B integration oracle to `source_manifest.json`.

The QA/showcase/pilot payload is not a deterministic Learn-it build source.

Any product/build-input mutation is a scope failure.

---

## 4. /solve — minimum Fan-in B integration design

Use the frozen G3 plan unless exact evidence requires a smaller safe variant.

The intended candidate is:

```text
JOB08_BASE
+ exact JOB05 R1 qa/student-v0.1/** payload
+ exact JOB06 R1 showcase/student-v0.1/nombres-complexes/** payload
+ exact JOB07 R2 pilot/student-v0.1/** payload
+ one integrator-owned Fan-in B oracle
+ minimum recomposed Learn-it Next CI route
```

No product source change.

No source-manifest change.

No role-payload edit.

Create one integrator-owned oracle:

`apps/learnit-next/tests/student_v01_fanin_b.py`

It must independently enforce the combined-candidate invariants and fail closed.

---

## 5. Fan-in B integrator oracle

The new oracle must at minimum:

1. load the frozen G3 R1 Fan-in B manifest;
2. verify its schema and exact G3/base/result anchors;
3. verify every imported JOB05/JOB06/JOB07 payload path exists;
4. verify every imported file Git blob exactly matches the frozen manifest;
5. verify there are no unexpected files inside the three candidate-payload families relative to the frozen payload list, except the existing directory structure itself;
6. verify repaired showcase kit SHA-256 is exact;
7. verify repaired Factory context exact target;
8. verify product/build/source-manifest/index-template files are unchanged from JOB08_BASE;
9. run or orchestrate the canonical integrated checks below;
10. emit a concise machine-readable PASS/HOLD summary when useful.

The oracle is integration evidence only.

It must not become a second product implementation.

---

## 6. Canonical repaired showcase gates

On the exact imported repaired showcase:

### Canonical V4

Require canonical validation PASS.

### Pedagogical quality

Require the exact accepted profile remains:

`EXCELLENT_BY_PROFILE`

with no mutation.

### Factory

Use the already-independent exact G3 R1 semantic review on the unchanged exact kit:

`qualification/STUDENT_V01_G3_R1_JOB06_SEMANTIC_REVIEW.json`

Run deterministic Factory gate against:
- exact integrated repaired showcase;
- exact unchanged learner brief;
- exact source;
- exact G3 R1 semantic review.

Require:

`PASS_AI_KIT_FACTORY_V1`

The semantic review remains valid only because the showcase bytes are required to be exact.

If kit bytes differ, stop before Factory.

---

## 7. Deterministic Learn-it app identity

Build Learn-it Next twice from the exact integrated candidate.

Require both builds are byte-identical and exactly:

```text
bytes   478657
sha256  85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e
```

If not:

`HOLD_STUDENT_V01_JOB08_BUILD_DRIFT`

No product repair is authorized.

---

## 8. Full contradictory QA

Execute the imported JOB05 R1 QA payload unchanged.

At minimum run:

- `qa/student-v0.1/job05_r1_contradictory_qa.py`
- `qa/student-v0.1/browser_job05_r1_contradictory_qa.py`

Preserve the frozen QA fixture blob exactly.

Require the same categories that previously passed:
- served rich journey;
- all activity families in its QA fixture;
- wrong-answer scored semantics;
- non-scored lesson/flashcard;
- recursive learner-secret exclusion;
- safe/fail-closed media behavior;
- reload/resume;
- completion;
- desktop/mobile;
- accessibility smoke;
- persistence isolation.

Do not weaken or patch QA.

---

## 9. Product/runtime regression matrix

Run unchanged, at minimum:

- `apps/learnit-next/tests/student_v01_served_v4_integration.py`
- `apps/learnit-next/tests/browser_student_v01_served_v4_integration.py`
- `apps/learnit-next/tests/student_v01_learning_runtime.py -v`
- `apps/learnit-next/tests/student_v01_activity_presentation.py`
- `apps/learnit-next/tests/browser_student_v01_activity_presentation.py`
- `apps/learnit-next/tests/student_v01_fanin_a.py`
- `apps/learnit-next/tests/student_v01_fanin_b.py`
- relevant Atlas qcm/fill regressions used by served-V4 qualification;
- canonical V4 validator tests;
- relevant Factory tests needed to prove the exact repaired showcase binding.

A new regression defect returns HOLD with an owner.

---

## 10. Exact repaired showcase real journey

Use the exact integrated repaired showcase.

Through real visible learner controls prove:

- import;
- start;
- all families present in the showcase;
- lesson/flashcard non-scored;
- evaluated activities scored correctly;
- learner presentation/DOM excludes hidden scoring authority;
- reload/resume after non-scored progress;
- reload/resume after scored progress;
- full 11/11 completion;
- completion persistence after fresh reopen.

Run independently at:

- desktop about `1365x768`;
- mobile about `390x844`.

Require no unexpected external HTTP(S) request.

This is automated G4 compatibility evidence, not G5 human readiness.

---

## 11. Exact integrated package

Use the imported JOB07 R2 builder unchanged:

`pilot/student-v0.1/build_pilot_package.py`

Build a package twice from:

- exact 478657-byte repaired app;
- exact repaired showcase kit.

Require both package builds are byte-identical and exactly:

```text
bytes   496658
sha256  a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10
```

Require:

- manifest binding PASS;
- extracted app identity PASS;
- extracted kit identity PASS;
- deterministic entry order/metadata PASS;
- local-only START_HERE PASS;
- no remote dependency.

Run the learner/browser smoke from an **extracted package**.

### Start-mode evidence

Preferred: execute accepted `DIRECT_FILE` start mode directly.

If the runner has an administrator navigation policy that blocks all `file://` or loopback navigation, you may use the same bounded G3-style temporary browser harness only if:

1. exact extracted app/kit bytes are used;
2. START_HERE relative-link/local-only contract is independently inspected;
3. accepted JOB07 R2 direct-file evidence remains durably bound to the exact unchanged builder/app contract;
4. the limitation is recorded explicitly.

Do not silently claim a direct-file execution that was not run.

---

## 12. Central workflow recomposition

Only this central path may be functionally recomposed:

`.github/workflows/learnit-next-ci.yml`

Start from the exact JOB08_BASE version.

Do **not** whole-file copy the JOB05 or JOB07 workflow variants.

Add the minimum bounded JOB08 route.

### Required route behavior

The authoritative stacked PR should target the exact G3 R1 branch/base.

The workflow must:

- route head branch `student-v01/fanin-b` to a dedicated bounded Student V0.1 Fan-in B profile;
- bind exact base ancestry to `JOB08_BASE`;
- require remote branch HEAD equals the target under test;
- fail if the G3 manifest blob is not exact;
- fail if imported payload blobs differ;
- prove product/build-input immutability;
- run exact repaired app build identity;
- run Fan-in B oracle;
- run contradictory QA;
- run repaired showcase canonical/Factory gates;
- run repaired showcase browser journey;
- run exact showcase package determinism/integrity/browser smoke;
- run required regressions.

Preserve unrelated CI routes semantically unchanged.

If stacked PR topology prevents automatic execution, a temporary DRAFT carrier from the **exact same RESULT_SHA** to `main` may be used only as CI transport.

Carrier rules:
- non-authoritative;
- never merged;
- no carrier-specific mutation;
- close after evidence is durable.

Local-only qualification cannot satisfy `INTEGRATION_CI: PASS`.

---

## 13. Exact scope before qualification

Compare:

`JOB08_BASE..RESULT_SHA`

Allowed paths are only:

- `work-packages/ATLAS-WP-044.json`
- `docs/programs/student-v0.1/jobs/JOB_08_FANIN_B.md`
- exact frozen JOB05 payload files;
- exact frozen JOB06 payload files;
- exact frozen JOB07 payload files;
- `apps/learnit-next/tests/student_v01_fanin_b.py`
- `.github/workflows/learnit-next-ci.yml`

Then evidence-only may add:

- `qualification/STUDENT_V01_JOB08_FANIN_B_RESULT.md`

No other path may change.

---

## 14. Defect ownership and stop rules

Use these owner classes:

- `NONE`
- `PRODUCT_SERVED_RUNTIME`
- `JOB05_QA`
- `JOB06_SHOWCASE`
- `JOB07_PACKAGING`
- `JOB08_INTEGRATOR_ORACLE`
- `JOB08_CI_RECOMPOSITION`
- `BUILD_IDENTITY`
- `UNKNOWN_NEEDS_CONTROL_ROOM`

### Role-owned defect

If exact accepted JOB05/JOB06/JOB07 payload fails for a role-owned reason:

`HOLD_STUDENT_V01_JOB08_ROLE_DEFECT`

Do not repair it.

### Integration-only defect

If payloads are correct but the new oracle/CI recomposition needs correction within allowed JOB08 integrator paths, repair only those integrator-owned paths, rerun the full qualification, and continue.

Do not change role payload to make the integration oracle green.

---

## 15. RESULT_SHA and EVIDENCE_HEAD

Separate:

- `RESULT_SHA`: exact integrated executable/tested candidate;
- `EVIDENCE_HEAD`: later commit adding only `qualification/STUDENT_V01_JOB08_FANIN_B_RESULT.md`.

Every functional PASS and workflow run must bind to `RESULT_SHA`.

The qualification file records:

- HCP/main binding;
- exact G3 R1/Fan-in manifest binding;
- all imported source commit/path/blob identities;
- proof no imported payload was edited;
- exact changed paths;
- product/build-input immutability;
- app build bytes/hash;
- canonical/quality/Factory results;
- QA/regression commands/results;
- showcase desktop/mobile journey;
- package bytes/hash/determinism/integrity;
- browser start-mode evidence and limitations;
- external network observation;
- exact CI workflow/run/job IDs;
- Repository governance run;
- PR scope;
- defect owner;
- rollback.

---

## 16. G4 PASS gate

G4 PASS requires all on the exact RESULT_SHA:

- HCP/input binding PASS;
- frozen Fan-in B manifest identity PASS;
- all role payload materialization identities PASS;
- no extra role payload PASS;
- product/build/source-manifest immutability PASS;
- Fan-in B integrator oracle PASS;
- V4 canonical PASS;
- pedagogical quality PASS;
- deterministic Factory PASS;
- repaired app exact identity PASS;
- contradictory QA PASS;
- product/runtime regressions PASS;
- repaired showcase real journey PASS;
- desktop/mobile PASS;
- reload/resume/completion PASS;
- secret boundary PASS;
- offline/no-remote PASS;
- exact package identity/determinism/integrity PASS;
- package browser smoke PASS;
- central workflow recomposition PASS;
- exact-head CI PASS;
- Repository governance PASS;
- PR scope PASS;
- exact scope PASS;
- defect owner `NONE`.

A PASS constitutes:

`G4 Fan-in B exact candidate qualified`

and authorizes only preparation of JOB09 / G5.

---

## 17. Final result block

Return exactly:

```text
STUDENT_V01_JOB08_RESULT
JOB08_BASE: d5050bace4c7dcbb63dcfe44a64ef344434e9bc2
G3_R1_RESULT_SHA: f0b8af8adeab132bec0ebe9410951e6add294c5b
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
JOB05_R1_RESULT_SHA: 1c92cad7ea576a613b6f198768bbebd114a06082
JOB06_R1_RESULT_SHA: 80ec72fef535e78013a9f0fb10bedb57f05bc761
JOB07_R2_RESULT_SHA: 5e492fddc4d5cf00c71bdb770eb1aeac11a63803
RESULT_SHA: <exact integrated tested candidate>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 425
PR: <authoritative job08 pr>
FANIN_MANIFEST_IDENTITY: PASS|FAIL
ROLE_PAYLOAD_IDENTITY: PASS|FAIL
PRODUCT_IMMUTABILITY: PASS|FAIL
FANIN_B_ORACLE: PASS|FAIL|BLOCKED
V4_CANONICAL: PASS|FAIL|BLOCKED
PEDAGOGICAL_QUALITY: PASS|FAIL|BLOCKED
FACTORY_GATE: PASS|FAIL|BLOCKED
APP_BUILD_IDENTITY: PASS|FAIL|BLOCKED
CONTRADICTORY_QA: PASS|FAIL|BLOCKED
PRODUCT_REGRESSIONS: PASS|FAIL|BLOCKED
SHOWCASE_REAL_JOURNEY: PASS|FAIL|BLOCKED
DESKTOP_MOBILE: PASS|FAIL|BLOCKED
RELOAD_RESUME_COMPLETION: PASS|FAIL|BLOCKED
SECRET_BOUNDARY: PASS|FAIL|BLOCKED
OFFLINE_NO_REMOTE: PASS|FAIL|BLOCKED
PACKAGE_IDENTITY: PASS|FAIL|BLOCKED
PACKAGE_BROWSER_SMOKE: PASS|FAIL|BLOCKED
CI_RECOMPOSITION: PASS|FAIL|BLOCKED
INTEGRATION_CI: PASS|FAIL|BLOCKED
REPOSITORY_GOVERNANCE: PASS|FAIL|BLOCKED
PR_SCOPE: PASS|FAIL|BLOCKED
DEFECT_OWNER: NONE|PRODUCT_SERVED_RUNTIME|JOB05_QA|JOB06_SHOWCASE|JOB07_PACKAGING|JOB08_INTEGRATOR_ORACLE|JOB08_CI_RECOMPOSITION|BUILD_IDENTITY|UNKNOWN_NEEDS_CONTROL_ROOM
SCOPE: PASS|FAIL
G4: PASS|HOLD|FAIL
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_JOB08_FANIN_B_G4_QUALIFIED_FOR_G5`
- `HOLD_STUDENT_V01_JOB08_INPUT_DRIFT`
- `HOLD_STUDENT_V01_JOB08_PAYLOAD_IDENTITY`
- `HOLD_STUDENT_V01_JOB08_BUILD_DRIFT`
- `HOLD_STUDENT_V01_JOB08_ROLE_DEFECT`
- `HOLD_STUDENT_V01_JOB08_INTEGRATION_NEEDS_REWORK`
- `FAIL_STUDENT_V01_JOB08_SCOPE_VIOLATION`
