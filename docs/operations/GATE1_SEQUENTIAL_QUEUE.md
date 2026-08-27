# Gate 1 — sequential GitHub-authoritative queue

Authority: `OPS-WP-007` / issue `#160`.

Canonical design: `G1-DESIGN-V6 R5`, package SHA-256
`698c08c2df2dc5e8a36bde6277311dd1dc382fdb5856b96fe37703d1840891a5`.

Gate 1 sits above the already accepted Gate 0 Codespace evidence bridge. It
discovers origin-bound Gate 0 request comments, elects at most one admissible
job, records append-only session/job state on the authority issue, invokes
Gate 0 exactly once, rereads GitHub, and only then considers another job.

## Hard boundary

Gate 1 does **not** create/start/restart a Codespace. It has no arbitrary shell
interface, repository write-job API, branch/commit/push, workflow dispatch,
merge, release, promotion, automatic governor decision, Gate 2 fan-in or Gate 4
parallel execution. Gate 0 implementation files are not modified.

A human starts a fresh Codespace and publishes the immutable session grant.
The fixed command can then drain one or more sequential jobs.

## Human session grant

Publish exactly one immutable comment on authority issue #160 with marker
`AI_GATE1_SESSION_GRANT_V1`, a `payload_sha256:` line containing the SHA-256 of
the canonical JSON payload, and exactly one fenced JSON object containing:

```json
{"authority_issue":160,"codespace_name":"<exact CODESPACE_NAME>","created_at":"<UTC Z>","generation":1,"granted_by":"<GitHub login posting the comment>","repository":"stefm78/learnit-platform","session_id":"G1S-<stable-id>"}
```

The grant comment must remain unedited. The posting GitHub login must equal
`granted_by`, and the running `CODESPACE_NAME` must equal `codespace_name`.

## Fixed invocation

```bash
python tools/ai_jobs/run.py \
  --repository stefm78/learnit-platform \
  --authority-issue 160 \
  --request-issue <issue containing Gate 0 requests> \
  --session-id G1S-<stable-id> \
  --max-jobs 1
```

`--max-jobs` is a bounded convenience only. Every job causes a fresh
GitHub-authoritative reconstruction before another can be elected.

## Recovery rule

A request digest with durable `JOB_STARTED` is never automatically replayed.
Any crash or ambiguous failure after that record enters `RECOVERY_REQUIRED`.
Recovery must reconcile an already-published Gate 0 outcome or obtain the human
authority required by the canonical design. Silently running the same job again
is forbidden.

## QA expectations

Independent QA owns only `tests/ai_jobs/**` paths listed in
`work-packages/OPS-WP-007.json`. QA must not repair implementation files.
Every implementation correction requires a full independent QA rerun.

Gate 2, Gate 3 and Gate 4 remain HOLD.
