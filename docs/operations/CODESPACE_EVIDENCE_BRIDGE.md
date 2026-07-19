# Codespace Evidence Bridge — Gate 0

## Purpose

The Gate 0 bridge executes one bounded evidence request, binds it to an exact GitHub origin and target SHA, records evidence in an immutable attempt directory, seals the bundle, publishes only to the verified source issue or pull-request conversation, and optionally stops only the exact current Codespace.

It is an evidence transport. It does not make a governor decision.

## Supported operations

Only these operations exist:

- `pr-snapshot`
- `pr-governor-evidence`
- `run-repository-validation`
- `run-test-profile`

Requests cannot provide arbitrary commands, shell fragments, scripts, paths, plugins, environment overrides, branches, commits, pushes, merges, releases, or workflow mutations.

## Request binding

The local launch descriptor contains only repository, origin type, origin number, and request comment ID. Before the request comment is read, the requested repository must exactly equal the canonical `nameWithOwner` resolved from the current checkout. The referenced comment must contain one request marker, one lowercase SHA-256 digest, and one fenced JSON request. The digest is recalculated over canonical JSON. Repository, origin, source comment, operation, target and full target SHA must agree.

## GitHub-only architecture

OPS-WP-005 uses no AWS resource, external database, SaaS lock, cloud dependency, secret, second repository, branch, tag, claim ref, workflow, queue, lease, worker or scheduler.

Concurrent read-only executions are permitted. The bridge does not claim global at-most-once execution. The only global decision is the deterministic election of one final authoritative GitHub outcome after exhaustive reread.

The only remote mutation is creation of the final outcome comment in the exact verified source issue or pull-request conversation. Gate 0 collection and execution remain read-only.

## Filesystem and credential boundary

GitHub transport runs only through fixed `gh` command paths and may receive the authenticated GitHub environment required for read-only collection and the one same-origin comment publication.

Repository-controlled validators, tests, Python programs, Make processes, and descendants run with private state directories, no inherited GitHub token variables, disabled system/global Git configuration, private PID and mount namespaces on Linux, private `/proc`, and a fail-closed filesystem boundary. When Landlock is unavailable, the minimal namespace/chroot fallback remains fail closed.

Local validation and test operations execute only in a disposable clone detached at the requested SHA. The primary checkout is recorded before and after execution. Any difference downgrades the result and disables self-stop.

## Candidate discovery and cryptographic validation

Every arbitration pass exhausts all pages of comments from the exact origin. A comment is a valid candidate only when all of the following hold:

1. it has a unique exact outcome marker and closed header shape;
2. repository, origin, job ID and target SHA match the complete logical job identity;
3. its author is the authenticated publisher;
4. the JSON block parses without duplicate keys;
5. the request digest is a full lowercase SHA-256;
6. for a sealed outcome, the manifest is reconstructed, `manifest_sha256` and `bundle_sha256` are recomputed, and every embedded file is rehashed;
7. for an oversize diagnostic, the canonical diagnostic digest is recomputed;
8. operation, source request comment and target identity agree where represented explicitly;
9. no authority is inferred from marker text, header fragments, comment ordering or author alone.

Malformed, truncated, unknown-shape, edited or cryptographically inconsistent comments are not candidates.

## Deterministic election

For one complete logical job identity, all cryptographically valid candidates are sorted by numeric `comment_id`. The smallest valid `comment_id` is the incumbent after convergence.

- A same-digest request reuses the incumbent and performs no second authoritative POST.
- A different-digest request returns `CONFLICT_DIFFERENT_DIGEST`; it never displaces the incumbent.
- Every other valid same-job candidate is recorded locally as `DUPLICATE_FINAL_OUTCOME`.
- A previously recorded incumbent that is later missing, edited or no longer valid produces `REGISTRY_INTEGRITY_LOST`; the bridge does not silently re-elect.

The election is independent of client retrieval order. It is an outcome arbitration mechanism, not a pre-execution claim.

## Publication sequence

The exact sequence is:

1. verify and bind the source request;
2. preflight the canonical checkout and authenticated publisher;
3. exhaustively discover, validate and elect existing candidates;
4. reuse a same-digest incumbent or reject a different-digest conflict;
5. otherwise execute the fixed read-only operation;
6. seal and render the local evidence;
7. exhaustively reread before publication to detect a concurrent incumbent;
8. resolve the target SHA again immediately before POST;
9. POST the exact body only if the SHA still matches;
10. read back the returned comment exactly;
11. exhaustively reread the exact origin and recompute authority;
12. persist a receipt naming the incumbent, its body SHA-256, the posted comment, and duplicate IDs.

No unrelated GitHub request occurs between the final successful SHA resolution and POST.

## Crash and ambiguous response recovery

A crash before POST leaves no remote final outcome; a same-digest restart may execute again because local files are not treated as a global claim.

A crash after POST but before receipt persistence is recovered by exhaustive cryptographic reread. An ambiguous POST timeout is handled the same way: success is reported only when reread finds a valid same-digest incumbent. Otherwise the bridge fails closed.

Receipts are outside the sealed bundle. New receipts record `authoritative_comment_id` and `authoritative_body_sha256`, allowing later detection of deletion or editing.

## Limits and failure handling

The publication limit is 58,000 UTF-8 bytes. A required full capsule that exceeds the limit is represented only by a final diagnostic; partial evidence cannot appear final.

Incomplete pagination, transient read failure, stale target SHA, ambiguous publication without a valid reread, integrity loss, different-digest conflict, malformed candidates and unexpected identity drift all fail closed.

## Codespace stop

Self-stop is optional and enabled only for the elected authoritative, stop-eligible outcome after exact Codespace identity validation. A losing duplicate, recovery-only run, stale outcome, diagnostic or failed arbitration cannot stop the Codespace.

## Independent review boundary

Under OPS-WP-005, CI/Ops may modify only `outcome.py`, `github.py`, `run.py`, `request.py`, this document, and `work-packages/OPS-WP-003.json`. Independent QA owns only the four paths authorized in issue #105, including the optional new `test_outcome_arbitration.py`. Every corrected exact SHA requires a complete independent QA rerun before Linus or governor review.
