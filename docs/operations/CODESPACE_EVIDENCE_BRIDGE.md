# Codespace Evidence Bridge — Gate 0

## Purpose

The Gate 0 bridge executes one bounded evidence request, binds it to an exact GitHub origin and target SHA, records evidence in an immutable attempt directory, seals the bundle, publishes one bounded same-origin outcome, verifies that exact publication, and optionally stops only the exact current Codespace.

It is an evidence transport. It does not make a governor decision.

## Supported operations

Only these operations exist:

- `pr-snapshot`
- `pr-governor-evidence`
- `run-repository-validation`
- `run-test-profile`

Requests cannot provide arbitrary commands, shell fragments, scripts, paths, plugins, environment overrides, branches, commits, pushes, merges, releases, or workflow mutations.

## Request binding

The local launch descriptor contains only:

- repository;
- origin type;
- origin number;
- request comment ID.

Before the request comment is read, the requested repository must exactly equal the canonical `nameWithOwner` resolved from the current checkout by `gh repo view`; a checkout/request repository mismatch fails closed. The referenced GitHub comment must contain exactly one `AI_CODESPACE_REQUEST_V1` marker, exactly one lowercase SHA-256 request digest, and exactly one fenced JSON request. The digest is recalculated over canonical JSON. Repository, origin object, comment ID, operation, and full lowercase 40-character target SHA must all agree.

## Filesystem and credential boundary

GitHub transport runs only through the fixed `gh` command paths and may receive the authenticated GitHub environment required for read-only collection and the one same-origin comment publication.

Repository-controlled validators, tests, Python programs, Make processes, and their descendants run with:

- a fresh private `HOME` and `USERPROFILE`;
- fresh XDG, `GH_CONFIG_DIR`, AppData and LocalAppData directories;
- a fresh private temp directory;
- no inherited GitHub token variables;
- system and global Git configuration disabled;
- a filesystem access boundary.

On Linux every confined profile first enters a private user, mount and PID namespace, becomes PID 1 there, and receives a newly mounted `/proc` that exposes only that namespace. Landlock is then applied inside that namespace. It permits only the system runtime required to execute tools, the fresh private state directories, and, when applicable, the disposable exact-SHA workspace. Absolute paths to the operator checkout, home directory, GitHub credential files, unrelated temporary files, host processes, and the host parent process remain inaccessible.

When Landlock is unavailable, the bridge remains inside the same private namespaces and fails closed through the minimal mount/chroot fallback. That fallback contains only the runtime, private state directories, private `/proc`, and optional disposable workspace. It does not fall back to unconstrained execution.

The exact-SHA clone/fetch/checkout infrastructure remains fixed and separately trusted. GitHub credentials are exposed only to the exact clone transport that requires them; subsequent fixed profile execution is confined.

## Disposable workspace

Local validation and test operations execute only in a new temporary clone detached at the requested full SHA. The bridge records the primary checkout before and after execution using HEAD, current branch, complete status, refs, index, and remotes digests. Any difference downgrades the result and disables self-stop.

## GitHub collection

The bridge exhausts paginated changed-file, review, status, check-run, workflow-run, job, and artifact-metadata endpoints. Requested logs are collected when available. Missing or deliberately excluded proof remains explicit.

Artifact metadata may be collected, but artifact content is not downloaded by Gate 0.

## Publication and replay

The local bundle is written once and sealed before publication. Its manifest contains the SHA-256 digest of every bundle file. `manifest_sha256` and `bundle_sha256` are derived from the reconstructed manifest. The target is resolved once more after rendering and immediately before the POST; any SHA movement records a local `STALE_AFTER_EXECUTION` publication failure and no comment is sent.

A final sealed publication includes the immutable identity fields, the sealed bundle digests, the embedded evidence payload, and a statement that the result is evidence only. Restart recovery:

1. identifies candidate comments by exact job, request, repository, origin, and target;
2. requires the candidate author to equal the authenticated GitHub publisher login;
3. reconstructs the manifest from the advertised file digests;
4. recalculates `manifest_sha256` and `bundle_sha256`;
5. recalculates every embedded file digest;
6. re-reads the exact comment ID;
7. verifies the origin, author, and body byte-for-byte.

A final oversize diagnostic uses `FINAL_DIAGNOSTIC_ONLY`. It includes the exact identity, origin, sealed bundle references, oversize reason, and a canonical `diagnostic_sha256`. Restart recovery recalculates that digest and performs the same exact author/origin/read-back checks, preventing duplicate publication after a POST-before-receipt crash.

A marker-shaped or internally self-consistent comment from another author is not a receipt. A `job_id` is atomically bound to one request digest. Replaying the same pair never allocates another attempt and never posts a duplicate; if the first claimed execution did not reach a verified final publication, a retry requires a new `job_id`. The request schema exposes no `allow_new_attempt` escape hatch.

## Limits and failure handling

The publication limit is 58,000 UTF-8 bytes. A required full capsule that exceeds the limit is represented only by a final diagnostic; partial evidence cannot appear final.

The first claim of a `job_id` and digest allocates one immutable attempt. Preflight and environment failures persist `FAIL_ENVIRONMENT` evidence in that attempt. The same `job_id` and digest cannot allocate a second attempt; a different digest cannot reuse the job ID. Publication and stop receipts remain outside the sealed bundle.

## Codespace stop

Self-stop is optional. It is enabled only after verified durable publication and only when:

- `CODESPACE_NAME` exactly identifies the current Codespace;
- the Codespace repository exactly matches the request repository;
- the final result is stop-eligible.

Missing, wrong, or ambiguous identity disables stop.

## Independent review boundary

CI/Ops owns only the implementation paths listed in `work-packages/OPS-WP-003.json`. Independent QA owns only the eight `tests/codespace_evidence/` files authorized by issue #102. Corrections do not alter QA-owned tests. Every corrected exact SHA requires a complete independent QA rerun before architecture or governor review.
