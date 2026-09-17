THIN_JOB_AB_BRANCH_RESULT
BRANCH_PROFILE: B_THIN
EXPERIMENT_BRANCH: experiment/job-control-b-thin-20260917
START_SHA: b3e845ef016a79e777ed87616d9ceb7aae7b1ba4
LOCAL_RESULT_SHA: a9718aaed70084556e2eaaf5580cc35ecf9fcd77
EVIDENCE_COMMIT_SHA: NOT_CREATED
CHANGED_PATHS_BEFORE_EVIDENCE: {apps/learnit-next/source_manifest.json}
DETERMINISTIC_BUILD: NOT_RUN
JOB01_SUITE: NOT_RUN
JOB02_STATIC: NOT_RUN
JOB02_BROWSER: NOT_RUN
JOB03_V4_VALIDATOR: NOT_RUN
JOB03_PEDAGOGICAL_QUALITY: NOT_RUN
JOB03_FACTORY_V4: NOT_RUN
FANIN_LOCAL_ORACLE: NOT_RUN
STALE_OR_INPUT_DRIFT: NONE
SCOPE_VIOLATION: REMOTE_CI_INSPECTION_READS_ONLY_NO_TRIGGER_NO_MODIFICATION
NO_SILENT_REPAIR: PASS
TEST_ORACLE_COMPLETENESS: FAIL
READS_TOOL_CALLS_BEFORE_FIRST_CAUSAL_MUTATION: 52
TOTAL_COUNTABLE_TOOL_CALLS: 79
CONTROL_ONLY_READS_CHECKS: 43
RETRIES_REWORK: 11 (1 alternate UCP retrieval attempt; 9 failed checkout/materialization/network retrieval attempts; 1 local result-draft formatting retry)
PACKET_BYTES: 7310
PACKET_LINES: 136
RESULT_BYTES: 6604
RESULT_LINES: 71
MATERIAL_SANDBOX_CACHE_USE: exact source_manifest reconstruction for deterministic self-hash plus exact packet mirror for byte/line/blob verification; no product checkout cache
LIMITATIONS: exact LOCAL_RESULT_SHA checkout could not be materialized in the local runtime (no mounted repository, outbound Git/GitHub unavailable, no repository archive cache). The required eight local mechanical oracles were therefore not run. While probing for a pre-existing exact checkout cache, two forbidden remote-CI metadata reads were performed (workflow-run metadata and artifact-list metadata); no remote CI was triggered or modified.
FINAL_BRANCH_VERDICT: FAIL
NEXT_SAFE_ACTION: RETURN_TO_COORDINATOR_AND_WAIT_FOR_INDEPENDENT_ORACLE

# B_THIN controlled execution result — 2026-09-17

## Constitutional and packet identity

The constitutional preflight passed byte-exactly: `UCP-CONTROL-PLANE`, `ACTIVE`, version `1.1-R4`, 5,186 UTF-8 bytes with terminal newline, SHA-256 `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`.

Immediately before evidence recording, the authoritative control-plane HEAD remained unchanged at Git blob `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`, selecting UAO 2.6 and Registry 2.5.

The execution packet was read only from commit `1df195059964422cdc83789dd098ccb4a0947b6e`; its Git blob is exactly `4cd25b6868f14e8820008aab31420199974a5052`. The exact packet is 7,310 bytes and 136 lines, with a terminal newline.

## Frozen-input preflight

The experiment branch was freshly read at the required start SHA `b3e845ef016a79e777ed87616d9ceb7aae7b1ba4`. Issue #397, PR #398, `ATLAS-WP-032.json`, the R2 input freeze, and the parent JOB all converged on the same frozen execution anchors. The parent JOB blob was exactly `63e49808305d3eb6ec32ce5386e8f7d97fa21e7c`.

The prior R1 qualification identifies `f4636e06279481b62ffd676ba70313c71283baeb` as the executable R1 result. Git ancestry showed the start SHA descending from that result. The accepted JOB01 R2 delta `d937592fb4d1e6dba6fcd02e290290f1a98cff71..ef3080e32e873170c6fd2fbdc72e93c31389cebb` changed exactly the three frozen paths: `apps/learnit-next/src/core/contract.js`, `apps/learnit-next/tests/student_v01_learning_runtime.py`, and `work-packages/ATLAS-WP-031.json`. The remaining start-SHA delta consisted only of the R2 freeze/JOB/work-package coordination artifacts.

The provenance-only detailed specimen was identity-checked without consuming its semantic body: commit `d82125f61eee9005a5be436ef6af66ce8d2d605e`, path `docs/programs/student-v0.1/jobs/JOB_04_R2_COMPLETION_CONTINUATION.md`, blob `f92c50264554a6fce124d1e4a6a0f414bc9ef27b`.

A fresh read of `main` found no material product/contract drift invalidating the frozen experiment baseline.

## Deterministic manifest rebind

At the start SHA, `apps/learnit-next/source_manifest.json` still bound `apps/learnit-next/src/core/contract.js` to Git blob `992be10d93759789972bd941f4bd8d36a99064ec` with provenance `JOB01:d937592fb4d1e6dba6fcd02e290290f1a98cff71`. The exact JOB01 R2 source blob present at the frozen start is `784495bfe74bc33570b77a29f4ecce99a4c57f2a`.

The existing build contract defines the manifest self-digest as SHA-256 over canonical JSON after setting its own fingerprint value to null. Recomputing the original object reproduced the declared self-digest `0ca4473d88ddf4218d6d9fc159df62d6c34a03ff51f4f02d73fc6994bf91849f`. The minimal rebind changed only the contract blob identity/provenance and the manifest self-provenance; the new mechanically derived self-digest is `c307eb996bc118eea98bac64174dc36a1f52bd8a1ce1128afcdbad897f49e525`.

The manifest mutation was CAS-protected against the exact pre-mutation blob and created local candidate commit `a9718aaed70084556e2eaaf5580cc35ecf9fcd77`. A fresh branch reread confirmed that SHA, with parent exactly equal to the required start SHA. The exact pre-evidence changed-path set is only `{apps/learnit-next/source_manifest.json}`.

## Mechanical-oracle status

The exact candidate checkout could not be materialized in the local execution runtime: no repository checkout was mounted, outbound Git/GitHub access from the command runtime was unavailable, and no exact repository archive/cache existed. Because the packet requires the unchanged repository assertions to run on the exact frozen candidate, no partial or synthetic checkout was substituted. Consequently the deterministic build and all seven local suites are `NOT_RUN`, and no build artifact exists to report.

During an attempt to locate a pre-existing exact checkout cache, this worker performed two reads of remote-CI metadata: workflow-run metadata for the start SHA and the associated artifact list. The packet explicitly forbids inspecting remote CI. No CI was triggered, no CI configuration or product state was modified, no CI logs were consumed, and those reads were not used as semantic evidence. Nevertheless this is a protocol-scope violation, so this execution cannot receive `PASS_LOCAL_QUALIFICATION`.

`FINAL_BRANCH_VERDICT: FAIL` classifies the controlled-worker execution, not the semantic correctness of the product candidate: none of the local product oracles ran and no product-test failure was observed.

## Durability note

`EVIDENCE_COMMIT_SHA` is necessarily `NOT_CREATED` inside this pre-commit payload because a Git commit cannot contain its own commit SHA. The worker records the actual evidence commit SHA externally after creating this file and then rereads the committed object exactly; no second self-referential evidence mutation is performed.
