# /AUDIT /SOLVE /BUILD — JOB 04 R2 COMPLETION CONTINUATION
## Student V0.1 — finish the already-started Wave 1 FAN-IN A R2 without restarting role work

TYPE: `BOUNDED_EXECUTION_PACKET`  
AUTHORITY: `NONE`  
DEPLOYABLE: `NO`  
PARENT_AUTHORITY_ISSUE: `#397`  
PARENT_WORK_PACKAGE: `ATLAS-WP-032`  
PARENT_PR: `#398`  
PARENT_JOB: `docs/programs/student-v0.1/jobs/JOB_04_R2_WAVE1_FANIN_A.md`  
PARENT_JOB_GIT_BLOB: `63e49808305d3eb6ec32ce5386e8f7d97fa21e7c`  
TARGET_EXECUTION_BRANCH: `student-v01/fanin-a-r2`  
EXPECTED_TARGET_HEAD_AT_PACKET_CREATION: `b3e845ef016a79e777ed87616d9ceb7aae7b1ba4`

This packet is a continuation aid only. It does not replace issue #397, ATLAS-WP-032, the parent JOB, repository architecture, or Human Control Plane authority.

---

## 0. Independence boundary

You are a fresh controlled continuation worker.

Do **not** use prior-chat summaries, remembered conclusions, hidden reasoning, or this packet's diagnostic notes as proof.

Reconstruct every material claim from current durable source-native evidence.

Do not restart JOB01, JOB02 or JOB03 merely because this is a fresh session. Preserve already-proven and already-applied work when its exact durable identity revalidates.

Do not execute product mutations on the packet branch. This packet is a locator and execution protocol. Product/integration continuation targets only `student-v01/fanin-a-r2` after exact CAS/revalidation.

---

## 1. Mission

Resume JOB 04 R2 from its exact durable partial state and determine whether it can be completed safely.

The parent JOB has already progressed through application of the exact JOB01 R2 delta. The remaining work must be handled in three bounded checkpoints:

A. deterministic integration rebind + build;
B. full local qualification without semantic repair;
C. exact-head CI/governance closure + final qualification evidence.

Do not collapse these checkpoints into one opaque operation.

At the end of each checkpoint, either:

- continue because the checkpoint has a durable, exact PASS;
- or stop with a precise HOLD/FAIL and `NEXT_SAFE_ACTION`.

Do not continue through an unexplained failure.

---

## 2. Frozen anchors to re-prove

Reconstruct the active Human Control Plane first, then re-read repository state.

Re-prove all of the following before mutation:

- `FANIN_A_BASE = 21d25c36aec6c04fdfe8126c95e71cbf80771a1b`
- `R2_START_CANDIDATE = f4636e06279481b62ffd676ba70313c71283baeb`
- `WAVE1_COMMON_BASE = 27846dff52fde9b83434bca29bd8732ea42834bf`
- `JOB01_PREDECESSOR = d937592fb4d1e6dba6fcd02e290290f1a98cff71`
- `JOB01_R2 = ef3080e32e873170c6fd2fbdc72e93c31389cebb`
- `JOB02 = 6c91346d07c934cfb2917799084647b13e4fb931`
- `JOB03 = a90ba85857dded331e5e3952c2f181cbe2e6d689`
- target branch `student-v01/fanin-a-r2`
- target branch head at packet creation `b3e845ef016a79e777ed87616d9ceb7aae7b1ba4`
- PR #398 is the R2 integration PR
- PR #396 remains at exact JOB01 R2 head and unmerged unless durable authority explicitly says otherwise.

Read at minimum:

- issue #397;
- parent issue #391;
- prior R1 issue #394;
- JOB01 R2 issue #395;
- PRs #393, #396 and #398;
- `work-packages/ATLAS-WP-032.json`;
- `docs/programs/student-v0.1/FANIN_A_R2_INPUT_FREEZE.md`;
- parent JOB exact bytes;
- prior R1 qualification `qualification/STUDENT_V01_FANIN_A_RESULT.md` from `student-v01/fanin-a`.

### Target-branch CAS rule

Before the first mutation, require:

`CURRENT_TARGET_HEAD == b3e845ef016a79e777ed87616d9ceb7aae7b1ba4`

If the target branch has moved, do not overwrite or silently rebase it.

Classify the movement. If it is not provably the exact continuation already authorized by this packet, stop:

`HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_TARGET_MOVED`

and return the observed head and changed paths.

### Current-main drift rule

Fresh-read `main`.

If `main` moved beyond `FANIN_A_BASE`, classify the drift exactly as the parent JOB requires. Coordination-only drift does not rewrite the frozen candidate. Product/contract drift that invalidates the frozen architecture returns HOLD for Control Room review.

---

## 3. Re-prove the already-completed portion

Do not reapply JOB01 R2.

Prove that current target head `b3e845ef...` descends from exact `R2_START_CANDIDATE` and that the already-applied role delta is exactly the accepted JOB01 R2 delta.

Required proofs:

1. `R2_START_CANDIDATE` is the exact executable candidate named by the R1 qualification.
2. `merge-base(JOB01_PREDECESSOR, JOB01_R2) == JOB01_PREDECESSOR`.
3. `JOB01_PREDECESSOR..JOB01_R2` changes exactly:
   - `apps/learnit-next/src/core/contract.js`
   - `apps/learnit-next/tests/student_v01_learning_runtime.py`
   - `work-packages/ATLAS-WP-031.json`
4. Relative to `R2_START_CANDIDATE`, current target head contains only:
   - the exact JOB01 R2 delta;
   - R2 authority/freeze/JOB packet preparation artifacts already authorized by ATLAS-WP-032;
   - no JOB02/JOB03 semantic mutation;
   - no unexplained product mutation.

If any proof fails, stop before modification with:

`HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_INPUT_DRIFT`

Return:

`CHECK | EXPECTED | OBSERVED | PATH/COMMIT`

---

## 4. Diagnostic hypotheses — verify, do not trust

The packet was prepared after an external audit observed two likely unfinished integration details at exact head `b3e845ef...`.

These are hypotheses to re-prove, not authority:

### H1 — deterministic source manifest is stale

Observed at packet preparation:

- current `apps/learnit-next/src/core/contract.js` Git blob: `784495bfe74bc33570b77a29f4ecce99a4c57f2a`;
- `apps/learnit-next/source_manifest.json` still declared predecessor blob `992be10d93759789972bd941f4bd8d36a99064ec` for that path;
- manifest provenance still named `JOB01:d937592f...`.

Freshly verify the exact current bytes and identities.

### H2 — exact R2 integration CI is not yet proven

Observed at packet preparation:

- only Repository governance had a recorded successful PR-triggered run on current R2 head;
- PR #398 is stacked with base `student-v01/fanin-a`;
- current workflow pull-request filter and route topology did not obviously provide an exact R2 integration run.

Freshly inspect current workflow topology, prior R1 CI evidence, any temporary control branch/PR topology, and all current run evidence before deciding how to route R2.

Do not modify CI merely because H2 was written here.

---

# CHECKPOINT A — deterministic integration rebind + build

## A1. Allowed mutation surface

Before local qualification, the only product/integration mutation allowed in Checkpoint A is:

- `apps/learnit-next/source_manifest.json`

No role implementation file may change.

No workflow change belongs to Checkpoint A.

## A2. Rebind deterministically

Rebind only manifest entries whose exact source bytes changed because of the already-applied JOB01 R2 delta and which are actually declared by the manifest.

Expected likely case: `apps/learnit-next/src/core/contract.js` plus the manifest's canonical self fingerprint and build artifact metadata as required by the existing deterministic build contract.

Do not assume that expectation is complete: derive the exact required rebind mechanically from the current manifest and source identities.

Preserve all unrelated manifest entries byte-for-byte/semantically unchanged where the canonical serialization permits.

Use exact source-native blob identities. Do not write guessed hashes.

## A3. Deterministic build oracle

Run the canonical build:

`python -B apps/learnit-next/build.py`

The build must pass without modifying semantic role code.

Record:

- exact candidate SHA used;
- exact manifest diff;
- artifact path;
- artifact byte count;
- artifact SHA-256.

Then rerun from the same exact source state as needed to prove deterministic output / no stale manifest residue.

If build failure requires changing a role-owned semantic file, stop:

`HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_ROLE_REWORK_REQUIRED`

Identify the owning role and failing invariant. Do not repair it.

If the manifest cannot be repaired without exceeding ATLAS-WP-032 scope, stop:

`HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_REBIND_SCOPE`

## A4. Freeze Checkpoint A

Commit only the authorized deterministic manifest rebind to `student-v01/fanin-a-r2`.

Freeze:

`R2_REBIND_SHA = <exact commit>`

Immediately re-read the branch and prove it equals the commit just written.

Do not proceed if CAS/re-read fails.

Checkpoint result:

- `CHECKPOINT_A: PASS`
- or an exact HOLD token above.

---

# CHECKPOINT B — full local qualification, zero semantic mutation

Checkpoint B is read/test-only.

No product, role, architecture, contract, UI, authoring or test semantic change is permitted.

Start only from exact `R2_REBIND_SHA` and revalidate it before running tests.

## B1. JOB01 R2 role suite

Run:

`python -B apps/learnit-next/tests/student_v01_learning_runtime.py -v`

Require the parent JOB invariants, including:

- standard inline SVG namespace PASS;
- malicious/external SVG fail-closed;
- representative JOB03 media PASS;
- v2 regression PASS;
- v3 constructed PASS;
- v4 evaluated/non-scored semantics PASS;
- secret boundary PASS.

## B2. JOB02 presentation suites

Run unchanged:

- `python -B apps/learnit-next/tests/student_v01_activity_presentation.py`
- `python -B apps/learnit-next/tests/browser_student_v01_activity_presentation.py`

Require all parent JOB presentation, media, accessibility and secret-boundary expectations.

## B3. JOB03 authoring suites

Run unchanged:

- `python -B authoring/v4/tests/test_validate_v4.py -v`
- `python -B authoring/v2/atlas/tests/test_pedagogical_quality.py -v`
- `python -B authoring/factory/tests/test_student_v01_v4.py -v`

## B4. Cross-role FAN-IN oracle

Run unchanged:

`python -B apps/learnit-next/tests/student_v01_fanin_a.py`

Require all admitted Student V0.1 activity types and the exact representative JOB03 inline SVG to cross authoring → runtime → learner-safe presentation.

## B5. Failure ownership rule

If any suite fails:

- do not patch the failing implementation;
- identify exact command, failing assertion, path and owning boundary;
- distinguish integration wiring defect from JOB01/JOB02/JOB03 semantic defect;
- stop with one of:

`HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_LOCAL_REWORK_REQUIRED`

or, if architecture/contracts must reopen:

`FAIL_STUDENT_V01_FANIN_A_R2_ARCHITECTURE_REOPEN_REQUIRED`

A local failure must not be hidden by proceeding to CI.

## B6. Checkpoint result

If every local oracle passes on exact `R2_REBIND_SHA`:

`CHECKPOINT_B: PASS`

Freeze the complete command/result matrix in the worker's durable evidence plan, but do not create the final qualification artifact yet because CI is still unproven.

---

# CHECKPOINT C — exact-head CI/governance closure + final evidence

Start only after A and B PASS.

## C1. Determine the smallest valid CI topology

Freshly inspect:

- `.github/workflows/learnit-next-ci.yml` on the exact candidate;
- PR #398 base/head;
- prior R1 exact CI run topology and workflow run IDs;
- any prior `student-v01/fanin-a-r1-control-temp` or equivalent control technique;
- currently available GitHub Actions capabilities.

Goal: obtain the parent JOB's required Repository governance, PR scope and exact routed Learn-it Next integration CI on the exact R2 candidate semantics.

Preference order:

1. reuse an already-valid exact-head workflow dispatch/control topology without changing candidate semantics;
2. use a temporary source-native control branch/PR pointing to the exact candidate if this was already proven safe and it introduces no product delta;
3. only if necessary and sufficient, make the minimum authorized `.github/workflows/learnit-next-ci.yml` routing change allowed by ATLAS-WP-032.

Do not invent a new CI architecture.

Do not retarget/rebase the product candidate merely to manufacture green CI unless the parent authority explicitly supports that topology.

## C2. If workflow mutation is required

Only `.github/workflows/learnit-next-ci.yml` may change, and only the minimum routing required for exact R2 qualification.

Freeze the resulting candidate as:

`RESULT_SHA = <exact pre-evidence candidate SHA>`

Because the exact candidate SHA has changed, rerun the full Checkpoint B local oracle on `RESULT_SHA` even if the diff is workflow-only. This removes ambiguity about which exact head was qualified.

If no workflow mutation is required, then:

`RESULT_SHA = R2_REBIND_SHA`

## C3. Required remote evidence

On exact `RESULT_SHA` require:

- Repository governance PASS;
- PR scope PASS;
- exact routed Learn-it Next integration CI PASS.

Capture exact workflow run IDs, conclusions, commit SHA binding and relevant job/log evidence.

Missing, unrouted, stale-SHA, cancelled or unrelated CI is **not** PASS.

If exact CI cannot be triggered or observed with the available runtime/tool permissions, stop safely:

`HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_CI_UNAVAILABLE`

Return the smallest source-native action required to obtain the missing run. Do not fabricate completion.

If CI fails on a semantic role defect, apply the no-silent-repair rule and return the owning HOLD/FAIL.

## C4. Scope verification

On `RESULT_SHA`, prove:

- no unexpected JOB02/JOB03 role-file mutation;
- no `contracts/**` or architecture authority mutation;
- only exact JOB01 R2 role delta + authorized R2 preparation + deterministic manifest rebind + optional minimum CI routing are present beyond the R1 executable candidate;
- `apps/learnit-next/tests/student_v01_fanin_a.py` remains unchanged from the parent R1 integration oracle;
- no hidden repair entered through test weakening.

## C5. Final qualification artifact

Only after A/B/C all PASS, create:

`qualification/STUDENT_V01_FANIN_A_R2_RESULT.md`

This is evidence-only mutation after freezing `RESULT_SHA`.

Bind at minimum:

- active authority rebind;
- current main observed and drift classification;
- all frozen input SHAs;
- parent JOB blob identity;
- packet locator identity;
- initial continuation head `b3e845ef016a79e777ed87616d9ceb7aae7b1ba4`;
- exact JOB01 R2 delta proof;
- `R2_REBIND_SHA`;
- `RESULT_SHA` before evidence-only mutation;
- exact changed paths;
- manifest rebind proof;
- artifact hash/bytes;
- every local test command/result;
- remote workflow run IDs/results;
- scope proof;
- reservations and rollback;
- final verdict and `NEXT_SAFE_ACTION`.

Commit the qualification artifact to `student-v01/fanin-a-r2`, re-read it exactly, and record the evidence commit SHA separately from `RESULT_SHA`.

---

## 5. Stop rules / anti-loop rules

Do not retry the same failing operation repeatedly without a new observation.

For every failure:

1. capture exact observed failure;
2. classify whether it is source identity, manifest/build, local semantic oracle, CI topology/permissions, CI product failure, scope, or architecture;
3. return the smallest next safe action;
4. stop if the next action belongs to another role or requires new authority.

Do not create more child JOBs merely because the execution is long.

A further split is justified only if a remaining blocker is independently executable with its own frozen input and oracle. If so, recommend the child packet boundary explicitly but do not silently redefine parent authority.

Do not rerun already-PASS expensive work unless the exact candidate identity changed or evidence was lost.

Use the sandbox opportunistically for exact bytes/derived deterministic work when cheaper than reconstruction, but cache is never authority and cannot replace fresh source-native identity/CAS checks.

---

## 6. Mandatory reservations

Even a PASS from this continuation:

- does not merge PR #398;
- does not merge Wave 1 child PRs;
- does not merge to `main`;
- does not launch Wave 2 by itself;
- does not promote Student V0.1;
- does not authorize real student use.

It authorizes only the parent Control Room's next decision/action exactly as the original JOB defines.

---

## 7. Final output

Always return this summary, including on HOLD/FAIL:

```text
STUDENT_V01_JOB04_R2_COMPLETION_RESULT
PARENT_ISSUE: 397
PARENT_PR: 398
INITIAL_CONTINUATION_HEAD: b3e845ef016a79e777ed87616d9ceb7aae7b1ba4
FANIN_A_BASE: 21d25c36aec6c04fdfe8126c95e71cbf80771a1b
R2_START_CANDIDATE: f4636e06279481b62ffd676ba70313c71283baeb
JOB01_PREDECESSOR_SHA: d937592fb4d1e6dba6fcd02e290290f1a98cff71
JOB01_R2_SHA: ef3080e32e873170c6fd2fbdc72e93c31389cebb
JOB02_SHA: 6c91346d07c934cfb2917799084647b13e4fb931
JOB03_SHA: a90ba85857dded331e5e3952c2f181cbe2e6d689
R2_REBIND_SHA: <sha|NOT_REACHED>
RESULT_SHA: <sha|NOT_REACHED>
EVIDENCE_COMMIT_SHA: <sha|NOT_CREATED>
CHECKPOINT_A: PASS|HOLD|FAIL|NOT_REACHED
CHECKPOINT_B: PASS|HOLD|FAIL|NOT_REACHED
CHECKPOINT_C: PASS|HOLD|FAIL|NOT_REACHED
DETERMINISTIC_BUILD: PASS|FAIL|NOT_RUN
ROLE_TESTS: PASS|FAIL|NOT_RUN
V2_REGRESSION: PASS|FAIL|NOT_RUN
V3_REGRESSION: PASS|FAIL|NOT_RUN
V4_END_TO_END: PASS|FAIL|NOT_RUN
NON_SCORED_LESSON_FLASHCARD: PASS|FAIL|NOT_RUN
SECRET_BOUNDARY: PASS|FAIL|NOT_RUN
STANDARD_SVG_NAMESPACE: PASS|FAIL|NOT_RUN
MALICIOUS_SVG_FAIL_CLOSED: PASS|FAIL|NOT_RUN
MEDIA: PASS|FAIL|NOT_RUN
AUTHORING_TO_LEARNER: PASS|FAIL|NOT_RUN
REPOSITORY_GOVERNANCE: PASS|FAIL|NOT_RUN
PR_SCOPE: PASS|FAIL|NOT_RUN
INTEGRATION_CI: PASS|FAIL|UNAVAILABLE|NOT_RUN
SCOPE: PASS|FAIL|NOT_RUN
FINAL_VERDICT: <token>
NEXT_SAFE_ACTION: <one exact bounded action>
```

Allowed successful final verdict:

`PASS_STUDENT_V01_FANIN_A_R2_READY_FOR_WAVE2`

Relevant continuation HOLD tokens:

- `HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_TARGET_MOVED`
- `HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_INPUT_DRIFT`
- `HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_REBIND_SCOPE`
- `HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_ROLE_REWORK_REQUIRED`
- `HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_LOCAL_REWORK_REQUIRED`
- `HOLD_STUDENT_V01_FANIN_A_R2_COMPLETION_CI_UNAVAILABLE`
- parent JOB HOLD/FAIL tokens when their conditions apply.

The burden of proof for PASS remains on the integrator.