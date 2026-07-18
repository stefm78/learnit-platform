# Codespace Evidence Bridge — Gate 0

## Scope

`OPS-WP-003` implements a portable, read-only evidence bridge bound to the exact design baseline `c0658b71e2d3a91e85d6629547cb34188b12f632`.

The bridge executes exactly one verified request and exposes exactly four operations:

- `pr-snapshot`
- `pr-governor-evidence`
- `run-repository-validation`
- `run-test-profile`

It is not a queue, a generic command runner, a merge or release engine, or a governance decision-maker.

## Launch

The core runs outside Codespaces:

```bash
python tools/codespace_evidence/run.py \
  --request .codespace-evidence/request.json \
  --output-root .agent-result/codespace-evidence
```

The optional Codespace hook adds only `--stop-after-success`. When the launch descriptor is absent, the command exits successfully without doing work.

## Origin-bound request

The launch descriptor is a locator, not authority:

```json
{
  "repository": "stefm78/learnit-platform",
  "origin_type": "issue",
  "origin_number": 102,
  "request_comment_id": 5010000000
}
```

The exact issue or pull-request conversation comment must contain one envelope:

````text
AI_CODESPACE_REQUEST_V1
request_sha256: <lowercase sha256 of canonical request JSON>

```json
{
  "schema_version": "learnit.codespace-evidence.request.v1",
  "job_id": "CEB-20260718-0001",
  "operation": "pr-governor-evidence",
  "repository": "stefm78/learnit-platform",
  "target_type": "pull_request",
  "target_number": 99,
  "target_sha": "f3ed7d0c2943133c98a6daf35936a5b3122f1917",
  "origin": {
    "type": "issue",
    "number": 102,
    "request_comment_id": 5010000000
  },
  "created_at": "2026-07-18T12:00:00Z",
  "timeout_seconds": 1800,
  "parameters": {
    "test_profile": null,
    "required_checks": ["Repository governance", "PR scope / gate"],
    "include_logs": false,
    "include_artifacts": false
  },
  "allow_new_attempt": false
}
```
````

Before target resolution or local operation execution, the bridge fetches that exact GitHub comment and verifies its issue URL, comment ID, marker count, canonical JSON digest, repository, origin type and number, and request comment ID. Unknown or duplicate fields fail closed. Publication is derived only from the verified origin.

## Request constraints

- `target_sha` is a full 40-character lowercase hexadecimal SHA.
- PR operations require `target_type=pull_request` and `target_number`.
- Local operations require `target_type=commit` and no `target_number`.
- `run-test-profile` accepts only `repository`, `learnit-next-strict`, `player-fast`, or `player-full`.
- Requests cannot supply commands, argv, shell fragments, scripts, plugins, paths, or environment variables.

## Fixed execution mappings

```text
repository          -> python tools/validate_repository.py
learnit-next-strict -> python apps/learnit-next/dev/run_checks.py --strict
player-fast         -> make -C apps/player test-fast
player-full         -> make -C apps/player test
```

All processes use explicit argv and `shell=False`.

## SHA binding and isolation

The current target SHA is resolved before execution. A mismatch produces `STALE_TARGET` and no repository operation runs. Local operations run in a disposable private clone detached at the exact requested SHA. The PR/commit target is resolved again before publication; movement produces `STALE_AFTER_EXECUTION` and prevents an evidence-candidate classification.

The primary checkout is snapshotted before and after using:

- HEAD and branch;
- porcelain status digest;
- refs digest;
- index digest;
- remotes digest.

Any difference fails the read-only invariant.

## GitHub evidence

PR evidence collection retrieves current metadata, full paginated changed-file inventory, complete unified diff, paginated reviews with reviewed commit IDs, status contexts, check runs, workflow runs, workflow jobs and job steps. Optional log and artifact collection records available logs and artifact metadata and emits explicit `missing_proof` entries when evidence is unavailable or intentionally not downloaded across the security boundary.

`pr-governor-evidence` adds factual review-to-SHA correlation, requested-check inventory and changed-path categorization. It never emits an acceptance, merge authorization or `GOVERNANCE_DECISION` classification.

## Evidence bundle and durable publication

Each run creates a new immutable directory:

```text
.agent-result/codespace-evidence/<job-id>/attempt-001/
  bundle/
  publication/
  stop/
```

The sealed bundle contains facts, summary, command records, redacted stdout/stderr, allowlisted environment facts and operation artifacts. `manifest.sha256` is generated and verified before the bundle is made read-only. Publication and stop receipts are written outside the sealed bundle.

Exactly one same-origin issue-conversation comment is rendered in full before POST. Its UTF-8 size must not exceed 58,000 bytes. Required facts are never silently omitted. If the durable capsule cannot fit, the outcome is `INCONCLUSIVE` with `DURABLE_CAPSULE_OVERSIZE`, only a bounded diagnostic is posted, and self-stop is disabled by the non-success state.

Publication succeeds only after exact read-back by returned comment ID verifies the origin URL and byte-identical body, including marker, job ID, request digest, origin, target SHA, manifest digest and bundle digest. A restart detects a previously posted final marker and avoids duplicate final publication unless the verified request explicitly authorizes another immutable attempt.

## Redaction and permissions

Command argv, outputs, GitHub responses, local reports and durable evidence are redacted for tokens, secrets, passwords, cookies, credentials, private keys, authorization schemes and URL-embedded credentials. Environment capture is allowlist-based and never records token values or credential files.

The implementation exposes GitHub reads plus one same-origin issue-comment POST. It has no code path for branch, commit, push, merge, release, workflow dispatch/rerun, label, state, assignee, review or repository-content mutation.

## Stop policy

Self-stop is best effort and separate from evidence classification. It is attempted only after durable publication has been read back and verified. `CODESPACE_NAME` must be present, syntactically valid, and match exactly one Codespace for the exact repository returned by `gh codespace list`. Missing, ambiguous or wrong identity disables stop; stop failure changes only the stop receipt.

## Failure classes

Allowed classifications are:

- `DIAGNOSTIC`
- `TEST_RESULT`
- `EVIDENCE_CANDIDATE`
- `STALE_TARGET`
- `STALE_AFTER_EXECUTION`
- `FAIL_ENVIRONMENT`
- `FAIL_HARNESS`
- `FAIL_TOPOLOGY`
- `FAIL_PRODUCT`
- `INCONCLUSIVE`

Every outcome states: `Evidence only. This outcome is not a governor decision.`

## Rollback

Revert or close the draft PR, remove the minimal devcontainer hook and `tools/codespace_evidence/`, remove this document and the work-package record, and revert the single `.codespace-evidence/` ignore entry. No product state, learner data, release artifact, workflow or migration is involved.
