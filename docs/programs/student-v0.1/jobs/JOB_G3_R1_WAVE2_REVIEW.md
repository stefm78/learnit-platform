# /AUDIT /SOLVE /BUILD — G3 R1
## Student V0.1 — independent Wave 2 review after repaired JOB06

Repository: `stefm78/learnit-platform`  
Authority issue: `#423`  
Program issue: `#380`  
Wave 2 control issue: `#403`  
Work package: `ATLAS-WP-043`

Branch:

`student-v01/g3-wave2-review-r1`

Exact anchors:

- `G3_R1_BASE = 7c13d67a76705b4452304c0f6a882504bc7701a7`
- `REPAIRED_PRODUCT_SHA = bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- `JOB05_R1_RESULT_SHA = 1c92cad7ea576a613b6f198768bbebd114a06082`
- `JOB05_R1_EVIDENCE_HEAD = 9dbd5c97603be864a57cc0f7f46047ee41772b34`
- `JOB06_R1_RESULT_SHA = 80ec72fef535e78013a9f0fb10bedb57f05bc761`
- `JOB06_R1_EVIDENCE_HEAD = d40a27ffadf99e2c0d47981cca47082be0003cfb`
- `JOB07_R2_RESULT_SHA = 5e492fddc4d5cf00c71bdb770eb1aeac11a63803`
- `JOB07_R2_EVIDENCE_HEAD = a2695560810b9a1bf3761d065326ff7df09c2252`

Exact repaired JOB06 review target:

- kit path: `showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json`
- kit Git blob: `03ed1d5819911c23734980f89716f4ca18a6bca4`
- kit SHA-256: `sha256:da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`
- Factory context path: `showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT.json`
- Factory context Git blob: `ea5ce453421bfe25db8e1a16597953cad77ac2db`
- context digest: `sha256:eab953d540af138f1da0b030d9cee97fdeab4060b76bfc832ab018f7abd89123`
- learner brief SHA-256: `sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`
- source-set digest: `sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`
- source commit: `281dc7470d51682c5e6d79d3fff54c46cfbced3b`
- source path: `authoring/v2/atlas/nombres_complexes_atlas.json`
- source Git blob: `7f83784e8719917496a694b2ad170d724190fd04`
- source SHA-256: `sha256:3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`

Apply strictly:

`/refresh -> /audit -> /solve -> /build -> /audit`

Do not merge or cherry-pick anything.

---

## 0. Role

You are the new independent G3 reviewer.

This is a **full clean-context review of the repaired exact JOB06 candidate**, followed—only on semantic PASS—by the remaining G3 Factory, compatibility and Fan-in B input-freeze work.

You are not a repair worker.

You must not modify product, QA, showcase, pilot, authoring, schema, workflow or governance implementation.

A G3 R1 PASS authorizes only preparation of JOB08.

---

## 1. Pre-review authority refresh

Before mutation:

1. fresh-read the active Human Control Plane HEAD;
2. bind exact UCP/UAO/governance authority;
3. fresh-read repository `main`;
4. read only:
   - issue #423;
   - `work-packages/ATLAS-WP-043.json`;
   - `docs/programs/student-v0.1/PROGRAM_CHARTER.md`;
   - `docs/architecture/student-v0.1/STUDENT_V0_1_ACTIVITY_RICHNESS_ARCHITECTURE.md`;
   - `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md`;
   - `authoring/factory/README.md`;
   - `authoring/factory/factory_gate.py`;
   - canonical V4 schema/validator public authorities as needed.
5. verify this branch descends exactly from `G3_R1_BASE`.

Do **not** read issue #421, issue #419, PR #422/420 body text, historical G3 review files, repaired JOB06 qualification, or author-side JOB06 evidence before the semantic-review freeze.

You may fetch exact Git objects by immutable SHA without reading their branch/PR narrative.

If you already consumed forbidden author/historical context in this new session before the review was frozen, stop:

`HOLD_STUDENT_V01_G3_R1_INDEPENDENCE_BREACH`

Do not pretend a clean review.

---

## 2. Independence firewall

Until the new semantic-review JSON is committed, your semantic context may contain only:

- exact source bytes;
- exact learner brief;
- exact repaired candidate;
- exact repaired Factory context;
- public reviewer/factory/schema authorities.

Forbidden before review freeze:

- historical G3 semantic review/evidence;
- original/repaired JOB06 qualification results;
- `AUTHOR_AUDIT.md`;
- `PROVENANCE_MAP.json`;
- `SOURCE_BASIS.md`;
- `PEDAGOGICAL_QUALITY_REPORT.json`;
- `V4_VALIDATION_REPORT.json`;
- `FACTORY_REVIEW_REQUEST.md`;
- author scratchpad;
- JOB06/JOB06-R1 active author conversation/context;
- any prior semantic conclusion for either old or repaired candidate.

The repaired candidate must be reviewed from the supplied source itself, not from author-side provenance.

---

## 3. Materialize exact clean-review inputs

Use immutable Git SHAs only.

### Source

Materialize:

`281dc7470d51682c5e6d79d3fff54c46cfbced3b:authoring/v2/atlas/nombres_complexes_atlas.json`

Require:

- Git blob `7f83784e8719917496a694b2ad170d724190fd04`;
- raw SHA-256 `3f5d465d22a0e197f0d9fd6a7f219931d3533138dc6fe5cba7838a5a9d05034d`.

### Repaired candidate, learner brief and Factory context

Materialize only these files from exact `JOB06_R1_RESULT_SHA`:

- `showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json`
- `showcase/student-v0.1/nombres-complexes/LEARNER_BRIEF.json`
- `showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT.json`

Require:

- candidate Git blob `03ed1d5819911c23734980f89716f4ca18a6bca4`;
- candidate raw SHA-256 `da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`;
- Factory-context Git blob `ea5ce453421bfe25db8e1a16597953cad77ac2db`;
- context digest `eab953d540af138f1da0b030d9cee97fdeab4060b76bfc832ab018f7abd89123`;
- brief SHA-256 `fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a`;
- source-set digest `ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83`.

If any exact identity differs, stop:

`HOLD_STUDENT_V01_G3_R1_EVIDENCE_DRIFT`

---

## 4. Full independent semantic review

Apply `authoring/skills/SKILL_ATLAS_KIT_REVIEW_V1.md` exactly.

Review all six dimensions from scratch:

1. `sourceFidelity`
2. `answerCorrectness`
3. `ambiguity`
4. `objectiveCoverage`
5. `validationTransfer`
6. `learnerFit`

This is **not** a delta review.

Independently inspect all eleven activities.

Independently recalculate every evaluated answer/mapping/order/constructed accepted response.

Challenge:

- factual/source support;
- answer correctness;
- distractor equivalence;
- wording ambiguity;
- objective coverage within the 42-minute brief;
- practice/validation/transfer independence across the entire sequence;
- learner fit.

For required evidence dimensions, derive evidence directly from the exact source JSON using:

- `sourceId = nombres-complexes-atlas-v2`;
- exact JSON locator;
- concise basis.

Do not use author-side provenance.

### Review output

Create exactly:

`qualification/STUDENT_V01_G3_R1_JOB06_SEMANTIC_REVIEW.json`

It must match `learnit.atlas.semantic_review.v1`.

Bind `target` exactly to the repaired four-hash Factory context.

Independence must be truthful:

```json
{
  "authorScratchpadSeen": false,
  "authorActiveContextReused": false
}
```

Use `PASS_SEMANTIC_REVIEW_V1` only if every dimension passes and no blocking/major finding exists.

Otherwise semantic HOLD.

### Freeze before widening context

Commit this semantic-review JSON **alone**.

Record that commit as:

`SEMANTIC_REVIEW_SHA`

After this commit, never edit the semantic-review JSON.

If semantic review HOLDs, create minimum durable G3 R1 HOLD evidence and stop. Do not open author-side/historical evidence to search for a justification or repair.

---

## 5. Deterministic Factory gate — only after semantic PASS

Run:

```bash
python -B authoring/factory/factory_gate.py gate \
  --kit <exact-repaired-job06-kit> \
  --brief <exact-repaired-job06-brief> \
  --review qualification/STUDENT_V01_G3_R1_JOB06_SEMANTIC_REVIEW.json \
  --source nombres-complexes-atlas-v2=<exact-source> \
  --json
```

Store the exact raw JSON output as:

`qualification/STUDENT_V01_G3_R1_JOB06_FACTORY_RESULT.json`

Require deterministic Factory PASS.

If Factory rejects canonical, quality, binding or semantic state, stop:

`HOLD_STUDENT_V01_G3_R1_FACTORY_GATE`

Do not repair anything.

---

## 6. Only now open author-side and historical evidence

Only after `SEMANTIC_REVIEW_SHA` exists and semantic verdict is PASS, you may read:

- repaired JOB06 issue #421 / PR #422;
- repaired JOB06 qualification;
- repaired JOB06 AUTHOR_AUDIT;
- PROVENANCE_MAP;
- SOURCE_BASIS;
- PEDAGOGICAL_QUALITY_REPORT;
- V4_VALIDATION_REPORT;
- FACTORY_REVIEW_REQUEST;
- historical G3 issue #419 / PR #420;
- historical G3 semantic review/evidence;
- original JOB06 qualification.

Use them only to cross-check against your already-frozen independent review.

Rerun on exact repaired candidate:

- canonical V4 validation;
- pedagogical quality.

Require no contradiction with the new semantic/Factory PASS.

---

## 7. Revalidate accepted input durability

Fresh-read and verify live exact state of:

### Served-V4 repair

- executable `bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- evidence `7c13d67a76705b4452304c0f6a882504bc7701a7`

### JOB05 R1

- result `1c92cad7ea576a613b6f198768bbebd114a06082`
- evidence `9dbd5c97603be864a57cc0f7f46047ee41772b34`
- authoritative QA CI still durably PASS.

### repaired JOB06 R1

- result `80ec72fef535e78013a9f0fb10bedb57f05bc761`
- evidence `d40a27ffadf99e2c0d47981cca47082be0003cfb`
- result→evidence delta only its qualification file.

### JOB07 R2

- result `5e492fddc4d5cf00c71bdb770eb1aeac11a63803`
- evidence `a2695560810b9a1bf3761d065326ff7df09c2252`
- exact-head packaging CI still durably PASS.

Any accepted input drift returns:

`HOLD_STUDENT_V01_G3_R1_EVIDENCE_DRIFT`

---

## 8. Exact repaired showcase on repaired product

Use temporary workspace only.

Do not commit Wave 2 payload.

Build the repaired application from `G3_R1_BASE`.

Require the accepted repaired app identity remains:

- bytes `478657`
- SHA-256 `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

Materialize the exact repaired JOB06 showcase candidate from `JOB06_R1_RESULT_SHA`.

Through real visible learner controls prove:

1. import succeeds;
2. course starts;
3. all activity families actually present in the repaired showcase are reachable;
4. lesson/flashcard remain non-scored;
5. evaluated activities score coherently;
6. hidden scoring authority stays outside learner presentation/DOM;
7. reload/resume works after non-scored and scored progress;
8. full journey reaches completion;
9. completion remains coherent after reopen.

Run browser proof at:

- desktop about `1365x768`;
- mobile about `390x844`.

This is automated compatibility evidence, not human readiness.

---

## 9. Package exact repaired showcase with exact JOB07 R2 implementation

Materialize into a temporary workspace, without editing, the exact accepted JOB07 R2 payload from `JOB07_R2_RESULT_SHA`:

- `pilot/student-v0.1/browser_generated_v4_probe.py`
- `pilot/student-v0.1/browser_pilot_package.py`
- `pilot/student-v0.1/build_pilot_package.py`
- `pilot/student-v0.1/ci_job07_r2.py`
- `pilot/student-v0.1/materialize_qualification_kit.py`
- `pilot/student-v0.1/test_pilot_package.py`

Use the generic package builder to package:

- exact repaired app HTML;
- exact repaired JOB06 showcase kit.

Do **not** substitute the generated JOB07 qualification kit.

Require:

- package builder accepts the repaired showcase canonically;
- manifest binds exact app/showcase bytes and hashes;
- two identical builds are byte-identical;
- extracted app/kit bytes match inputs exactly;
- accepted `DIRECT_FILE` start mode remains viable for this exact showcase;
- no external network dependency appears.

Perform a real browser smoke from the **extracted package**.

If the existing R2 browser harness assumes a different fixture shape, create only a temporary G3 probe outside Git using public product behavior. Do not modify JOB07 R2 code.

Require desktop/mobile import/start/interact/reload/resume/completion compatibility.

A package or product incompatibility returns:

`HOLD_STUDENT_V01_G3_R1_WAVE2_INCOMPATIBLE`

---

## 10. Cross-output overlap matrix

Compute exact accepted changed paths.

Classify each into:

- `candidate_payload`
- `evidence_or_control_only`
- `integrator_owned_recompose`
- `forbidden_or_unresolved`

Freeze these expected payload families if exact evidence supports them.

### JOB05 R1 payload

From `JOB05_R1_RESULT_SHA`:

- `qa/student-v0.1/JOB05_CANONICAL_V4_FIXTURE.json`
- `qa/student-v0.1/browser_job05_r1_contradictory_qa.py`
- `qa/student-v0.1/job05_r1_contradictory_qa.py`

Its central workflow delta is `integrator_owned_recompose`.

### repaired JOB06 R1 payload

From `JOB06_R1_RESULT_SHA`, complete directory:

`showcase/student-v0.1/nombres-complexes/**`

including exact repaired kit and its bound author-side evidence.

JOB06 prompt/WP/qualification are control/evidence only.

### JOB07 R2 payload

From `JOB07_R2_RESULT_SHA`:

`pilot/student-v0.1/**`

Its central workflow delta is `integrator_owned_recompose`.

### Central integration ownership

`.github/workflows/learnit-next-ci.yml`

must be recomposed by JOB08 from the G3 base and required integrated checks.

Do not blindly cherry-pick sibling workflow variants.

No accepted role output should require product-source or source-manifest repair.

Any unresolved same-payload-path conflict blocks G3 R1.

---

## 11. /solve — freeze minimum JOB08 composition

If all prior gates pass, independently choose the minimum non-repairing Fan-in B plan.

Expected composition to challenge:

```text
G3 R1 evidence head
→ import exact JOB05 R1 qa/student-v0.1/** payload
→ import exact repaired JOB06 showcase/student-v0.1/nombres-complexes/** payload
→ import exact JOB07 R2 pilot/student-v0.1/** payload
→ JOB08 integrator recomposes .github/workflows/learnit-next-ci.yml
→ no product source change
→ no source_manifest change unless a declared build source truly requires it
→ verify repaired app build identity remains exact
→ rerun canonical + Factory binding on repaired showcase
→ real repaired showcase journey
→ exact showcase packaged by integrated pilot builder
→ contradictory QA
→ desktop/mobile/reload/resume/completion
→ deterministic app/package
→ exact-head CI
→ Repository governance
→ G4 exact candidate qualification
```

If the evidence indicates a smaller safe plan, use it.

Do not add repair authority to JOB08.

Any role-owned defect must return to its role.

---

## 12. Fan-in B input manifest

Create:

`qualification/STUDENT_V01_G3_R1_FANIN_B_INPUT_MANIFEST.json`

Schema:

`learnit.student-v0.1.g3-r1-fanin-b-inputs.v1`

Include:

- G3 R1 base;
- repaired product result/evidence;
- JOB05 R1 result/evidence;
- repaired JOB06 R1 result/evidence;
- JOB07 R2 result/evidence;
- new semantic-review SHA;
- deterministic Factory verdict/target;
- exact payload paths grouped by source result SHA;
- Git blob SHA per payload file where practical;
- evidence/control paths excluded from payload;
- central paths assigned to JOB08 recomposition;
- exact integration order;
- exact required JOB08 tests;
- exact app/package identity expectations;
- no-silent-repair stop rule;
- rollback anchors.

This manifest freezes inputs only.

It does not integrate them.

---

## 13. Repository governance and scope

No workflow modification is authorized in G3 R1.

Repository governance must PASS on the G3 R1 branch.

Exact `G3_R1_BASE..RESULT_SHA` may change only:

- `work-packages/ATLAS-WP-043.json`
- `docs/programs/student-v0.1/jobs/JOB_G3_R1_WAVE2_REVIEW.md`
- `qualification/STUDENT_V01_G3_R1_JOB06_SEMANTIC_REVIEW.json`
- `qualification/STUDENT_V01_G3_R1_JOB06_FACTORY_RESULT.json`
- `qualification/STUDENT_V01_G3_R1_FANIN_B_INPUT_MANIFEST.json`

Then evidence-only may add only:

- `qualification/STUDENT_V01_G3_R1_WAVE2_REVIEW.md`

Any implementation-path mutation is scope FAIL.

---

## 14. Result/evidence semantics

Use:

- `SEMANTIC_REVIEW_SHA`: commit adding only the new semantic-review JSON;
- `RESULT_SHA`: exact G3 R1 frozen result containing semantic review + Factory result + Fan-in B manifest, before narrative evidence;
- `EVIDENCE_HEAD`: later commit adding only `qualification/STUDENT_V01_G3_R1_WAVE2_REVIEW.md`.

The narrative evidence records:

- fresh HCP/main binding;
- clean-review firewall compliance;
- exact input hashes;
- semantic-review verdict;
- Factory raw result identity;
- post-freeze canonical/quality cross-check;
- accepted input durability;
- repaired showcase on repaired product;
- exact showcase through exact JOB07 R2 package implementation;
- desktop/mobile/offline/secret-boundary results;
- overlap matrix;
- selected JOB08 composition;
- Repository governance run;
- exact scope;
- rollback.

---

## 15. PASS gate

PASS requires:

- HCP binding PASS;
- independence firewall PASS;
- exact repaired review-input identity PASS;
- new JOB06 semantic review PASS;
- deterministic JOB06 Factory gate PASS;
- canonical/quality cross-check PASS;
- JOB05 R1 accepted evidence intact;
- repaired JOB06 R1 accepted evidence intact;
- JOB07 R2 accepted evidence intact;
- repaired showcase on repaired product PASS;
- repaired showcase packaged by exact JOB07 R2 implementation PASS;
- desktop/mobile compatibility PASS;
- reload/resume/completion PASS;
- offline/no-remote PASS;
- learner secret boundary PASS;
- cross-output overlap PASS;
- Fan-in B input manifest PASS;
- Repository governance PASS;
- scope PASS.

PASS authorizes only Control Room preparation of JOB08 from final `EVIDENCE_HEAD`.

It does not authorize JOB08 execution automatically, G4, JOB09, main merge, release or real students.

---

## 16. Final result block

Return exactly:

```text
STUDENT_V01_G3_R1_RESULT
G3_R1_BASE: 7c13d67a76705b4452304c0f6a882504bc7701a7
REPAIRED_PRODUCT_SHA: bdb66bffefd6738e3cb4004d304159e9d3d048ce
JOB05_R1_RESULT_SHA: 1c92cad7ea576a613b6f198768bbebd114a06082
JOB06_R1_RESULT_SHA: 80ec72fef535e78013a9f0fb10bedb57f05bc761
JOB07_R2_RESULT_SHA: 5e492fddc4d5cf00c71bdb770eb1aeac11a63803
SEMANTIC_REVIEW_SHA: <commit adding only new semantic review json>
RESULT_SHA: <exact g3 r1 frozen-result sha>
EVIDENCE_HEAD: <final evidence-only head>
ISSUE: 423
PR: <authoritative g3 r1 pr>
HCP_BINDING: PASS|FAIL
INDEPENDENCE_FIREWALL: PASS|FAIL
INPUT_IDENTITY: PASS|FAIL
JOB06_R1_SEMANTIC_REVIEW: PASS|HOLD|FAIL
JOB06_R1_FACTORY_GATE: PASS|HOLD|FAIL|BLOCKED
JOB06_R1_CANONICAL_QUALITY: PASS|FAIL|BLOCKED
JOB05_R1_ACCEPTED: PASS|FAIL|BLOCKED
JOB06_R1_ACCEPTED: PASS|FAIL|BLOCKED
JOB07_R2_ACCEPTED: PASS|FAIL|BLOCKED
SHOWCASE_ON_REPAIRED_PRODUCT: PASS|FAIL|BLOCKED
SHOWCASE_PACKAGED_WITH_JOB07_R2: PASS|FAIL|BLOCKED
DESKTOP_MOBILE: PASS|FAIL|BLOCKED
RELOAD_RESUME_COMPLETION: PASS|FAIL|BLOCKED
OFFLINE_NO_REMOTE: PASS|FAIL|BLOCKED
SECRET_BOUNDARY: PASS|FAIL|BLOCKED
CROSS_OUTPUT_OVERLAP: PASS|FAIL|BLOCKED
FANIN_B_INPUT_MANIFEST: PASS|FAIL|BLOCKED
REPOSITORY_GOVERNANCE: PASS|FAIL|BLOCKED
SCOPE: PASS|FAIL
JOB08_BASE: <EVIDENCE_HEAD if PASS, else BLOCKED>
FINAL_VERDICT: <token>
```

Allowed final verdicts:

- `PASS_STUDENT_V01_G3_R1_READY_FOR_JOB08`
- `HOLD_STUDENT_V01_G3_R1_INDEPENDENCE_BREACH`
- `HOLD_STUDENT_V01_G3_R1_EVIDENCE_DRIFT`
- `HOLD_STUDENT_V01_G3_R1_JOB06_SEMANTIC_REVIEW`
- `HOLD_STUDENT_V01_G3_R1_FACTORY_GATE`
- `HOLD_STUDENT_V01_G3_R1_WAVE2_INCOMPATIBLE`
- `FAIL_STUDENT_V01_G3_R1_SCOPE_VIOLATION`
