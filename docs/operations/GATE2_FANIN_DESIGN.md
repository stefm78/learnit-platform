# Gate 2 — bounded read-only dependency fan-in design

Authority: \`OPS-WP-008\` / issue \`#181\`.

Preparation baseline: \`33d4ffc5f8aa5289008a72de301f937137f119e7\`.

Gate 1 ancestor: \`G1-DESIGN-V6 R5\`, validated implementation head
\`e85233cbd5bdc122ba17b053d05ecc55f842a4ea\`, merged through
\`002d5d10e53be2c3f57abdb71603ebb28b771621\`.

## 1. Status and authority boundary

This document is a design contract only.

- \`GATE2_PREPARATION_ONLY\`
- \`GATE2_NOT_ACTIVATED\`
- \`GATE3_HOLD\`
- \`GATE4_HOLD\`
- \`NO_RUNTIME_IMPLEMENTATION_AUTHORIZED\`

Issue #181 authorizes only this document and \`work-packages/OPS-WP-008.json\`.
It does not authorize a Gate 2 runtime, a new Gate 0 operation, a repository-write
job, parallel execution, an automatic Codespace lifecycle, or any modification
under \`tools/ai_jobs/**\` or \`tools/codespace_evidence/**\`.

Gate 2 is an eligibility overlay above the accepted Gate 1 sequential queue.
It does not redesign Gate 0 or Gate 1. A future implementation must reuse the
existing Gate 0 request bytes, Gate 1 session/generation identity, Gate 1 durable
\`JOB_STARTED\` recovery rule, and Gate 1 deterministic election.

## 2. Design objective

Gate 2 V1 allows a bounded set of already-existing read-only Gate 0 requests to
declare dependencies on other requests. A node becomes eligible only after every
declared predecessor has a durable, still-valid successful outcome binding.

The fan-in relation is control flow only. It is not dataflow: predecessor
stdout, artifacts, generated code, summaries, files, or outcome fields never
become parameters of a descendant request.

The V1 graph is fixed before the first node is executed. It is not a generic
workflow language.

## 3. Normative invariants

1. GitHub remains authoritative for the immutable graph declaration, Gate 0
   requests, Gate 1 grant/ledger, Gate 0 outcome comments, and Gate 2 outcome
   binding receipts.
2. A dependency is never identified by \`job_id\` alone.
3. Every graph node resolves to exactly one immutable Gate 0 request comment
   already admissible to Gate 1.
4. Every node and every edge is confined to one repository, one authority
   issue, one request issue, one session, and one generation.
5. Cross-repository, cross-authority, cross-session, and cross-generation
   dependencies are forbidden in V1.
6. The dependency rule is strict AND. OR, quorum, optional, conditional, and
   best-effort dependencies do not exist in V1.
7. A predecessor satisfies a dependency only when its Gate 1 terminal result is
   \`COMPLETED\` and a durable Gate 2 receipt binds the exact authoritative
   Gate 0 outcome comment body.
8. A GitHub comment ID alone is not a durable outcome binding because a comment
   body is mutable. The UTF-8 body SHA-256 is mandatory.
9. Failed, stale, ambiguous, missing, deleted, edited, or otherwise invalidated
   predecessors never satisfy descendants.
10. A queue containing unfinished nodes that are all blocked or waiting for
    outcome binding is not empty and must not be automatically closed.
11. Among simultaneously runnable nodes, Gate 1's existing order
    \`(request_comment_id, job_id)\` remains authoritative.
12. Exactly one non-terminal Gate 1 job may exist in the session. Gate 2 does
    not introduce runtime parallelism.
13. Descendant Gate 0 requests are closed, immutable, and pre-existing before
    graph admission. Gate 2 cannot synthesize or mutate a request.
14. A durable \`JOB_STARTED\` keeps the accepted Gate 1 semantics:
    crash/ambiguity means \`RECOVERY_REQUIRED\`, with zero automatic replay.
15. Gate 0 remains limited to the four accepted read-only operations:
    \`pr-snapshot\`, \`pr-governor-evidence\`,
    \`run-repository-validation\`, and \`run-test-profile\`.
16. Gate 3 repository writes remain HOLD.
17. Gate 4 parallel execution remains HOLD.
18. Any malformed, oversized, ambiguous, conflicting, or non-closed contract
    fails closed before a new Gate 0 invocation.

## 4. Identity model

### 4.1 Graph scope

One graph is bound to exactly:

- \`repository\`;
- \`authority_issue\`;
- \`request_issue\`;
- \`session_id\`;
- \`generation\`;
- the exact immutable Gate 1 session grant via
  \`session_grant_comment_id\` and \`session_grant_digest\`.

The selected Gate 1 grant must be the unique highest admissible generation
under the existing Gate 1 exclusivity rules. The graph declaration author must
equal that grant's \`granted_by\` identity and still have Gate 1 request
authority at graph admission.

The current Gate 1 implementation discovers requests from one issue and parses
them with \`origin_type="issue"\`. Gate 2 V1 therefore requires every graph node
to be an issue-origin request whose \`origin_number == request_issue\`.
A request may still target a commit or a pull request exactly as Gate 0 permits.

### 4.2 Minimum node/dependency binding

A logical \`job_id\` is not sufficient. The minimum V1 binding for a node or a
dependency reference is the following four-tuple:

    {
      "job_id": "<Gate 0 job id>",
      "request_comment_id": <positive GitHub issue-comment id>,
      "request_sha256": "<64 lowercase hex>",
      "target_sha": "<40 lowercase hex>"
    }

The graph scope supplies repository and request issue. At admission, this tuple
must reproduce exactly one current Gate 1 \`QueueJob\` from the immutable source
comment. The re-parsed request must also prove its existing Gate 0 operation,
origin, target type/number, parameters, timeout, author, and creation time.

Why all four members are required:

- \`job_id\` carries the human/logical name but is reusable only at the cost of
  a Gate 1 conflict;
- \`request_comment_id\` binds the GitHub source object;
- \`request_sha256\` binds the exact closed Gate 0 request bytes;
- \`target_sha\` makes the exact execution target explicit at the fan-in layer.

No weaker reference is admissible.

## 5. Canonical graph declaration

### 5.1 Envelope

The graph is one immutable comment on \`authority_issue\`. Its body has exactly
this shape and no additional non-empty text:

    AI_GATE2_FANIN_V1
    payload_sha256: <sha256(canonical JSON payload bytes)>
    \`\`\`json
    <one canonical JSON object>
    \`\`\`

Canonical JSON uses the existing Gate 1 rules: UTF-8, NFC strings, sorted object
keys, shortest separators, no duplicate keys, no floats, no NaN/Infinity.

The comment must remain unedited: GitHub \`created_at == updated_at\`.
Exactly one admissible graph declaration may exist for the selected
session/generation. Multiple declarations, even byte-identical ones, fail
closed; a graph is human authority, not a retryable runtime publication.

### 5.2 Payload schema

\`schema_version\` is exactly \`learnit.gate2.fanin.v1\`.

Exact top-level fields:

    {
      "schema_version": "learnit.gate2.fanin.v1",
      "repository": "owner/repo",
      "authority_issue": 123,
      "request_issue": 124,
      "session_id": "G1S-...",
      "generation": 1,
      "session_grant_comment_id": 100,
      "session_grant_digest": "<64 lowercase hex>",
      "graph_id": "G2D-...",
      "nodes": [...]
    }

\`graph_id\` must match
\`^G2D-[A-Z0-9][A-Z0-9._-]{2,63}$\`.

Exact node fields:

    {
      "job_id": "JOB-A",
      "request_comment_id": 1001,
      "request_sha256": "<64 lowercase hex>",
      "target_sha": "<40 lowercase hex>",
      "depends_on": [...]
    }

Each \`depends_on\` element uses exactly the four dependency-binding fields
defined in section 4.2.

Nodes in the canonical payload must be sorted by
\`(request_comment_id, job_id)\`. Each node's \`depends_on\` array must use the
same ordering. Unsorted arrays are rejected rather than silently normalized.

### 5.3 Closed quantitative bounds

Gate 2 V1 is intentionally small:

| Metric | V1 bound |
| --- | ---: |
| canonical graph payload | <= 65,536 UTF-8 bytes |
| nodes | 1..32 |
| directed dependency edges | <= 64 |
| fan-in (in-degree) per node | <= 8 |
| fan-out (out-degree) per node | <= 16 |
| DAG depth | <= 8 edges from a root |

A root has depth 0. A non-root has depth
\`1 + max(depth(predecessor))\`.

These Gate 2 bounds are additional to the existing Gate 1/GitHub snapshot and
record bounds. A future implementation must fail closed when either layer's
bound is exceeded.

## 6. DAG validation and deterministic rejection

The entire graph is validated before any Gate 2 node can be elected.

Validation order is normative so equivalent invalid inputs produce the same
primary rejection:

1. envelope and canonical JSON;
2. graph-scope/session-grant binding;
3. graph byte/node/edge/fan-in/fan-out bounds;
4. node ordering and exact node identity reproduction;
5. duplicate node identity;
6. duplicate dependency edge;
7. missing/internal dependency reference;
8. direct self-cycle;
9. indirect cycle;
10. depth bound.

Duplicate policy is stricter than Gate 1 queue observation: two graph nodes
may not share a \`job_id\`, \`request_comment_id\`, or \`request_sha256\`.
A duplicate edge is invalid even if its bytes are identical.

All dependency references must resolve inside the same graph. External
references are forbidden.

Indirect cycles are detected with Kahn topological elimination. Whenever more
than one zero-in-degree node is available, the elimination tie-break is
\`(request_comment_id, job_id)\`. If not all nodes are emitted, the graph is
rejected as an indirect cycle.

Canonical rejection codes:

- \`G2_GRAPH_SCHEMA_INVALID\`
- \`G2_GRAPH_COMMENT_EDITED\`
- \`G2_GRAPH_AUTHORITY_MISMATCH\`
- \`G2_GRAPH_SESSION_MISMATCH\`
- \`G2_GRAPH_BOUND_EXCEEDED\`
- \`G2_DUPLICATE_NODE_IDENTITY\`
- \`G2_DUPLICATE_DEPENDENCY\`
- \`G2_MISSING_DEPENDENCY\`
- \`G2_CROSS_BOUNDARY_REFERENCE\`
- \`G2_CYCLE_DIRECT\`
- \`G2_CYCLE_INDIRECT\`
- \`G2_DEPTH_BOUND_EXCEEDED\`
- \`G2_REQUEST_BINDING_MISMATCH\`

No partial graph survives rejection.

## 7. AND fan-in and dependency truth

For every edge \`P -> D\`, predecessor \`P\` projects to exactly one dependency
truth:

- \`UNFINISHED\`: P has no Gate 1 terminal record.
- \`BINDING_PENDING\`: P has a unique \`COMPLETED\` Gate 1 terminal but no
  durable valid Gate 2 outcome-binding receipt yet.
- \`SATISFIED\`: P has a unique \`COMPLETED\` terminal and a valid durable
  receipt whose bound outcome remains authoritative and unchanged.
- \`FAILED\`: Gate 1 terminal result is \`FAILED\`.
- \`STALE\`: Gate 1 terminal result is \`STALE_BEFORE_EXECUTION\` or
  \`STALE_AFTER_EXECUTION\`.
- \`AMBIGUOUS\`: Gate 1 terminal result is \`AMBIGUOUS_HOLD\`, or authoritative
  terminal/outcome election is non-unique.
- \`INVALIDATED\`: the source request, terminal record, receipt, or bound Gate 0
  outcome was deleted, edited, changed, or no longer verifies.

A root node has no dependency truth requirements.

A non-root descendant is \`RUNNABLE\` if and only if every direct predecessor
is \`SATISFIED\`. This is strict AND semantics. Any number smaller than the full
declared predecessor set is insufficient.

\`FAILED\`, \`STALE\`, \`AMBIGUOUS\`, and \`INVALIDATED\` never count as
success, even if some other predecessor succeeded.

## 8. Durable authoritative outcome binding

### 8.1 Decision

Binding only \`gate0_authoritative_comment_id\` is explicitly rejected.

GitHub comment ID identifies a container whose body can later be edited. Gate 0
already validates strong inner manifest/bundle digests, but Gate 2 must also
bind the exact durable comment body that justified dependency satisfaction.

The V1 authoritative predecessor binding therefore requires both:

- the exact authoritative Gate 0 outcome comment ID; and
- \`SHA-256(UTF8(exact current outcome comment body))\`.

The bound body must independently pass the existing Gate 0 cryptographically
complete outcome validation and match the full predecessor request identity.

### 8.2 Dependency-binding receipt

After a predecessor reaches a unique Gate 1 terminal result \`COMPLETED\`, a
future Gate 2 runtime may publish one deterministic receipt on the same
\`authority_issue\`:

    AI_GATE2_DEPENDENCY_BINDING_V1
    payload_sha256: <sha256(canonical JSON payload bytes)>
    \`\`\`json
    <one canonical JSON object>
    \`\`\`

The exact payload schema is
\`learnit.gate2.dependency-binding.v1\` and has exactly:

    {
      "schema_version": "learnit.gate2.dependency-binding.v1",
      "repository": "owner/repo",
      "authority_issue": 123,
      "request_issue": 124,
      "session_id": "G1S-...",
      "generation": 1,
      "graph_comment_id": 200,
      "graph_payload_sha256": "<64 lowercase hex>",
      "predecessor": {
        "job_id": "JOB-A",
        "request_comment_id": 1001,
        "request_sha256": "<64 lowercase hex>",
        "target_sha": "<40 lowercase hex>"
      },
      "gate1_terminal_record_sha256": "<64 lowercase hex>",
      "gate1_terminal_sequence": 5,
      "gate0_authoritative_comment_id": 3001,
      "gate0_outcome_body_sha256": "<64 lowercase hex>"
    }

There is deliberately no generated timestamp in this payload. The receipt
identity is a deterministic function of already durable facts, which permits
safe publication reconciliation after a crash without re-executing Gate 0.

A receipt is valid only if all of the following are true on fresh stable
GitHub read-back:

1. the receipt comment itself is unedited;
2. its author equals the selected Gate 1 grantor/authenticated pilot identity;
3. it binds the one accepted graph comment and graph payload digest;
4. its predecessor reference resolves exactly inside that graph;
5. the Gate 1 ledger record is the unique terminal record for that predecessor
   in the same repository/authority/session/generation;
6. that terminal result is exactly \`COMPLETED\`;
7. the terminal record's job/request identity and authoritative outcome comment
   ID equal the receipt;
8. the Gate 0 outcome comment still exists, is unedited, and is authored by the
   trusted Gate 0 publisher identity;
9. the exact body passes the existing Gate 0 complete cryptographic/schema
   validation for the predecessor;
10. the exact UTF-8 body SHA-256 equals
    \`gate0_outcome_body_sha256\`.

Retry/recovery publication may observe multiple byte-identical receipt payloads;
the smallest immutable comment ID is the deterministic incumbent. Two valid
receipts for the same predecessor with different payload digests are
\`G2_RECEIPT_AMBIGUOUS\` and fail closed.

## 9. Predecessor failure, stale, ambiguity, deletion, and edit semantics

- \`FAILED\`: descendants are permanently \`BLOCKED_FAILED\` in this graph.
- \`STALE_BEFORE_EXECUTION\` or \`STALE_AFTER_EXECUTION\`: descendants are
  permanently \`BLOCKED_STALE\`. A stale result can never satisfy fan-in.
- \`AMBIGUOUS_HOLD\` or non-unique durable evidence: descendants are
  \`BLOCKED_AMBIGUOUS\`; no automatic tie-breaking beyond the already-defined
  authoritative elections is allowed.
- Deleted/edited predecessor source request: the predecessor is
  \`INVALIDATED\`; the selected graph/session enters fail-closed global hold.
- Deleted/edited bound Gate 0 outcome, body-digest mismatch, or failed inner
  seal validation: the predecessor is \`INVALIDATED\`; the selected
  graph/session enters fail-closed global hold.
- Edited graph or receipt comment: the graph/session enters fail-closed global
  hold.
- A target SHA that moves before a descendant effect remains subject to the
  existing Gate 1 final effect guard and cannot execute.

If invalidation is discovered after any descendant already reached durable
\`JOB_STARTED\`, the existing \`RECOVERY_REQUIRED\`/no-replay boundary dominates
for that active job. If discovered after downstream terminal work exists, Gate 2
does not roll it back or replay it; the graph is held and requires human
disposition.

A new session/generation and a new graph are required to change dependencies or
retry a failed/stale branch. V1 never rewrites the old graph to manufacture
success.

## 10. State model

Gate 2 adds a derived projection; it does not replace Gate 1 states or ledger
semantics.

### 10.1 Node states

- \`WAITING\`: valid node, at least one predecessor is \`UNFINISHED\`.
- \`BINDING_PENDING\`: all execution predecessors are terminal-successful but
  at least one successful predecessor lacks a durable valid receipt.
- \`RUNNABLE\`: root, or every predecessor is \`SATISFIED\`, and the node has
  neither started nor terminated.
- \`SELECTED\`: Gate 1 durable \`JOB_SELECTED\` for this node.
- \`STARTED\`: Gate 1 durable \`JOB_STARTED\` for this node.
- \`SUCCEEDED\`: Gate 1 terminal \`COMPLETED\` plus valid Gate 2 receipt.
- \`FAILED\`: Gate 1 terminal \`FAILED\`.
- \`STALE\`: Gate 1 terminal stale result.
- \`AMBIGUOUS\`: Gate 1 terminal ambiguity or non-unique authority.
- \`BLOCKED\`: unfinished node with at least one failed/stale/ambiguous
  predecessor.
- \`INVALIDATED\`: a previously required authority/evidence object no longer
  validates.
- \`RECOVERY_REQUIRED\`: the existing Gate 1 projection is
  \`RECOVERY_REQUIRED\`.

The final sink node also needs a receipt before the entire graph is considered
complete. This keeps "all nodes complete" and "all dependency success proofs
durably bound" identical concepts.

### 10.2 Graph/queue states

- \`INVALID\`: graph contract rejection; zero Gate 0 execution.
- \`ACTIVE\`: at least one runnable/selected/started node exists.
- \`RECONCILING\`: no runnable node exists only because one or more successful
  predecessors are \`BINDING_PENDING\`; runtime may reconcile/publish receipts,
  but may not replay Gate 0.
- \`RECOVERY_REQUIRED\`: Gate 1 has a durable started job requiring recovery.
- \`BLOCKED\`: no runnable/active/reconcilable node exists and at least one
  unfinished node is blocked by failed/stale/ambiguous predecessor truth.
- \`GLOBAL_HOLD\`: source, graph, receipt, or bound outcome authority was
  invalidated or contradictory.
- \`COMPLETE\`: every graph node is \`SUCCEEDED\`.

## 11. BLOCKED is not EMPTY

This is a required Gate 2 change to future orchestration, not a change made by
this design PR.

Current Gate 1 closes when its ordinary election returns no selected job.
A future Gate 2 runtime must project the graph before taking that close path.

The only Gate 2 state equivalent to autonomous queue exhaustion is:

    QUEUE_EMPTY_COMPLETE := graph_state == COMPLETE

If \`graph_state\` is \`BLOCKED\`, \`RECONCILING\`,
\`RECOVERY_REQUIRED\`, or \`GLOBAL_HOLD\`, the runtime must not publish a
normal empty-queue close candidate.

A graph with only blocked descendants is therefore observably blocked, not
empty. Human disposition is required; this design does not invent an automatic
"ignore failed branch" rule.

Any state combination that is impossible for a valid DAG (for example no
runnable/started node, no binding pending work, no terminal blocker, and graph
not complete) is \`G2_INTERNAL_PROJECTION_INCONSISTENT\` and fails closed.

## 12. Sequential deterministic election

Gate 2 computes only the runnable subset. It then delegates election to the
existing Gate 1 deterministic queue rule.

For two or more runnable nodes, the winner remains the smallest:

    (request_comment_id, job_id)

Topological depth, graph array position, number of dependents, or completion
time do not alter this order.

After one node is selected, no second node may be selected until Gate 1 has
reconstructed a terminal/recovery state and Gate 2 has reconstructed all
required predecessor receipts. Gate 4 parallel execution remains absent.

## 13. No dataflow contract

A Gate 2 edge means only "eligible after durable predecessor success."

The following are forbidden:

- inserting predecessor stdout into descendant parameters;
- inserting artifacts, filenames, generated code, diffs, summaries, or
  outcome fields into descendant requests;
- templating a request from predecessor output;
- mutating \`job_id\`, operation, timeout, target, origin, test profile, or
  parameters after graph admission;
- creating a new Gate 0 request because a predecessor completed;
- treating the Gate 2 receipt body as application input.

Before graph admission, every node's exact Gate 0 request comment must already
exist and its \`request_sha256\` must already be final. During every readiness
projection, the current source comment must still reproduce that same digest.

## 14. Crash and recovery

The accepted Gate 1 crash boundary is preserved without exception.

### Crash before JOB_STARTED

Reconstruct from GitHub. A still-valid selected/runnable job may continue
according to existing Gate 1 rules.

### Crash after durable JOB_STARTED

The generation becomes \`RECOVERY_REQUIRED\`. The request digest is never
automatically replayed, even if no Gate 0 outcome can be found.

### Crash after JOB_TERMINAL COMPLETED but before Gate 2 receipt

This is not permission to rerun the predecessor. Reconstruct the unique Gate 1
terminal record, locate and fully validate the already-authoritative Gate 0
outcome, compute its exact body SHA-256, and publish/reconcile the deterministic
Gate 2 receipt. Only after that durable receipt exists may descendants become
runnable.

### Ambiguous receipt publication

Perform stable reread. If an identical valid receipt is found, elect the
smallest comment ID. If no unique payload truth can be established, enter
\`G2_RECEIPT_AMBIGUOUS\` / global hold. Never rerun Gate 0 to repair a receipt
ambiguity.

## 15. Security and trust profile

### 15.1 Controls compatible with the existing GATE1_PILOT_READ_ONLY mechanics

The following mechanisms do not by themselves add a new privileged effect:

- parse and validate a bounded immutable graph;
- read existing Gate 1/Gate 0 GitHub evidence;
- compute dependency truth and runnable subsets;
- hash and validate exact outcome comment bodies;
- publish same-authority control-plane dependency receipts;
- continue to invoke only the exact four accepted Gate 0 read-only operations;
- retain manual Codespace start/session grant;
- retain same-Codespace process fencing;
- retain post-\`JOB_STARTED\` authority rereads and zero automatic replay;
- retain exactly one non-terminal sequential job.

These mechanics can be implemented inside the same trust assumptions as the
current pilot, but this design does not authorize doing so.

### 15.2 Capabilities that require FULL_V6_SECURITY

\`FULL_V6_SECURITY\` is required before any of the following may be claimed or
enabled:

- repository-write jobs or any Gate 3 capability;
- branch/commit/push/workflow-dispatch/merge/release/promotion effects;
- compromised-broker resistance or a claim of separated cryptographic
  issuer/effect-domain isolation;
- automatic Codespace creation/start/restart;
- cross-session, cross-generation, or cross-authority delegation;
- dynamic creation/mutation of descendant requests from predecessor output;
- output dataflow across jobs;
- any future privileged effect outside the accepted Gate 0 read-only surface.

Gate 4 parallel execution is separately HOLD and is not authorized merely by
obtaining FULL_V6_SECURITY.

### 15.3 Owner decision deliberately left open

\`OWNER-G2-SEC-01 — Does dependency-triggered autonomous continuation constitute
"stronger autonomy" requiring FULL_V6_SECURITY before Gate 2 activation?\`

The design is intentionally neutral between two future owner choices:

A. Conservative activation: require \`FULL_V6_SECURITY\` before any Gate 2
   runtime is enabled.

B. Bounded pilot activation: explicitly authorize a distinct
   \`GATE2_PILOT_READ_ONLY\` profile with the same trust limitations as
   \`GATE1_PILOT_READ_ONLY\`, exact four Gate 0 operations, no repository write,
   no external issuer-isolation claim, and all V1 fan-in invariants above.

Issue #181 selects neither option. A new runtime implementation/activation
authority must record the owner decision explicitly.

## 16. Valid examples

### 16.1 Structurally valid graph

Assume the three referenced request comments already exist on issue 201, are
immutable, and their stated digests and target SHAs exactly match Gate 1
reconstruction. Then this graph is valid and C has AND fan-in on A and B:

    {
      "authority_issue":200,
      "generation":1,
      "graph_id":"G2D-DEMO-001",
      "nodes":[
        {
          "depends_on":[],
          "job_id":"JOB-A",
          "request_comment_id":1001,
          "request_sha256":"1111111111111111111111111111111111111111111111111111111111111111",
          "target_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        },
        {
          "depends_on":[],
          "job_id":"JOB-B",
          "request_comment_id":1002,
          "request_sha256":"2222222222222222222222222222222222222222222222222222222222222222",
          "target_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        },
        {
          "depends_on":[
            {
              "job_id":"JOB-A",
              "request_comment_id":1001,
              "request_sha256":"1111111111111111111111111111111111111111111111111111111111111111",
              "target_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            },
            {
              "job_id":"JOB-B",
              "request_comment_id":1002,
              "request_sha256":"2222222222222222222222222222222222222222222222222222222222222222",
              "target_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            }
          ],
          "job_id":"JOB-C",
          "request_comment_id":1003,
          "request_sha256":"3333333333333333333333333333333333333333333333333333333333333333",
          "target_sha":"cccccccccccccccccccccccccccccccccccccccc"
        }
      ],
      "repository":"stefm78/learnit-platform",
      "request_issue":201,
      "schema_version":"learnit.gate2.fanin.v1",
      "session_grant_comment_id":1500,
      "session_grant_digest":"4444444444444444444444444444444444444444444444444444444444444444",
      "session_id":"G1S-DEMO-001"
    }

A and B are roots. If both become \`SATISFIED\`, C becomes runnable. If only A
is satisfied, C remains waiting. If B fails, C is blocked.

### 16.2 Valid recovery without replay

A reaches durable Gate 1 \`JOB_TERMINAL(COMPLETED)\`, then the process crashes
before the Gate 2 receipt is published. On restart, A is
\`BINDING_PENDING\`. The runtime validates A's existing authoritative Gate 0
outcome and publishes the deterministic binding receipt. A becomes
\`SATISFIED\`; A is not executed again.

## 17. Invalid examples

- \`{"job_id":"JOB-A"}\` as a dependency: rejected because job ID alone is not
  identity.
- A node depending on itself: \`G2_CYCLE_DIRECT\`.
- A -> B -> C -> A: \`G2_CYCLE_INDIRECT\`.
- Two identical A -> C edges: \`G2_DUPLICATE_DEPENDENCY\`.
- C references D but D is absent from \`nodes\`: \`G2_MISSING_DEPENDENCY\`.
- Two nodes reuse one request digest or job ID:
  \`G2_DUPLICATE_NODE_IDENTITY\`.
- A dependency from another repository, authority issue, request issue,
  session, or generation: \`G2_CROSS_BOUNDARY_REFERENCE\`.
- A graph with 33 nodes, 65 edges, fan-in 9, fan-out 17, depth 9, or payload
  above 65,536 bytes: rejected by the corresponding bound.
- C has predecessors A and B, but only A is successful: C is not runnable.
- A has terminal \`FAILED\` and an apparently valid Gate 0 comment: the receipt
  is inadmissible because the Gate 1 terminal result is not \`COMPLETED\`.
- A's outcome comment keeps the same comment ID but its body is edited after a
  receipt: the body digest no longer matches; A is invalidated and the graph
  enters global hold.
- A's source request comment is deleted after success: A is invalidated; its
  descendants cannot continue.
- A graph contains only descendants blocked by a failed root: it is
  \`BLOCKED\`, not empty, and may not be automatically closed.
- A descendant request is rewritten using A's stdout: forbidden dataflow and
  request-binding failure.

## 18. Expected contradictory test oracle

A future implementation is not ready for owner activation unless independent QA
can prove at least all of the following on one exact head:

1. closed graph envelope/parser, duplicate-key rejection, canonical digest, and
   immutable graph comment checks;
2. exact session-grant/repository/authority/request-issue/session/generation
   binding;
3. rejection of job-id-only dependency identity;
4. exact request-comment/digest/target reproduction for every node;
5. deterministic rejection of duplicate nodes and duplicate edges;
6. deterministic rejection of missing references;
7. direct-cycle rejection;
8. indirect-cycle rejection independent of input array order;
9. payload/node/edge/fan-in/fan-out/depth bounds;
10. strict AND truth table for 0, 1, and 8 predecessors;
11. completed predecessor without receipt remains \`BINDING_PENDING\`;
12. \`FAILED\`, both stale outcomes, and \`AMBIGUOUS_HOLD\` never satisfy an
    edge;
13. same comment ID with edited outcome body fails the receipt body-digest
    binding;
14. deleted/edited predecessor request fails closed;
15. deleted/edited outcome or receipt fails closed;
16. divergent valid receipts for one predecessor produce ambiguity/hold;
17. identical retry receipts elect deterministically without replay;
18. blocked-only graph is never projected as empty/closable;
19. graph becomes complete only after every node has successful terminal plus
    durable valid receipt;
20. multiple runnable nodes preserve existing Gate 1
    \`(request_comment_id, job_id)\` order;
21. exactly one non-terminal job remains enforceable;
22. descendant request bytes/digest remain unchanged before and after every
    predecessor completion;
23. no predecessor stdout/artifact/body field is exposed as descendant input;
24. crash after \`JOB_STARTED\` still yields \`RECOVERY_REQUIRED\` and zero
    automatic replay;
25. crash after terminal-before-receipt reconciles the receipt without a Gate 0
    invocation;
26. source/outcome invalidation after downstream start cannot cause automatic
    replay or rollback;
27. current \`GATE1_PILOT_READ_ONLY\` versus \`FULL_V6_SECURITY\` claims are
    accurately separated;
28. no Gate 3 write surface exists;
29. no Gate 4 parallel runtime exists;
30. all existing Gate 1 tests remain green with zero skip/xfail camouflage;
31. all existing Gate 0 regression tests remain green and Gate 0 blobs remain
    byte-identical.

The independent oracle should include mutation cases that weaken AND to OR,
drop body SHA binding, treat BLOCKED as EMPTY, accept a missing reference,
ignore one cycle edge, allow cross-generation references, or sort runnable
nodes by graph position. Every such mutant must be killed.

## 19. Migration from Gate 1

There is no in-place migration of historical Gate 1 sessions.

A future Gate 2 activation must:

1. use a new explicit runtime implementation/activation authority;
2. use a fresh Gate 1 session/generation and immutable session grant;
3. keep the existing Gate 0 request grammar unchanged;
4. publish all request comments before graph admission;
5. publish exactly one immutable graph bound to the selected grant;
6. validate the full graph before the first Gate 0 execution;
7. use the existing Gate 1 ledger/election/recovery semantics for each node;
8. add only the Gate 2 eligibility/receipt overlay.

Closed or historical Gate 1 outcomes are not imported as predecessor success
into a new Gate 2 generation. Cross-generation reuse is forbidden in V1.

## 20. Rollback

### Design rollback

Because this work package is design-only, rollback is limited to closing the
draft PR without merge or reverting only:

- \`docs/operations/GATE2_FANIN_DESIGN.md\`
- \`work-packages/OPS-WP-008.json\`

No executable behavior changes.

### Recommended future runtime rollback

If a later, separately authorized Gate 2 runtime is ever enabled, rollback
should disable only the Gate 2 graph-admission/eligibility path and restore the
unchanged Gate 1 sequential behavior. Gate 0 and historical GitHub evidence
remain untouched. Durable graph/receipt comments are append-only evidence and
must not be deleted or rewritten.

## 21. Recommended future implementation allowlist — NOT AUTHORIZED

The smallest expected runtime surface is:

- new \`tools/ai_jobs/fanin.py\` — closed graph/receipt contracts, DAG
  validation, dependency projection, bounds;
- existing \`tools/ai_jobs/run.py\` — filter to runnable subset, receipt
  reconciliation, and BLOCKED-vs-EMPTY close guard;
- existing \`tools/ai_jobs/__init__.py\` only if central marker/bound constants
  are justified instead of keeping them private to \`fanin.py\`.

Recommended independent QA additions:

- \`tests/ai_jobs/test_fanin_contracts.py\`
- \`tests/ai_jobs/test_fanin_graph.py\`
- \`tests/ai_jobs/test_fanin_recovery.py\`
- \`tests/ai_jobs/test_fanin_security.py\`
- \`tests/ai_jobs/test_fanin_integration.py\`

A future implementation should not need to modify Gate 0,
\`tools/ai_jobs/queue.py\`, \`tools/ai_jobs/session.py\`,
\`tools/ai_jobs/github_transport.py\`, or \`tools/ai_jobs/gate0_adapter.py\`.
If evidence shows that any of those paths is necessary, the runtime work
package must justify that scope explicitly before modification.

This allowlist is a recommendation only. Issue #181 authorizes none of it.

## 22. Closed decisions and unresolved owner decision

Closed by this design:

- dependency identity is the exact four-field binding under one graph scope,
  never job ID alone;
- fan-in is strict AND;
- only \`COMPLETED\` plus a durable valid outcome-binding receipt satisfies a
  predecessor;
- comment ID alone is insufficient; exact outcome body SHA-256 is mandatory;
- failed/stale/ambiguous/edited/deleted predecessors do not satisfy;
- BLOCKED and RECONCILING are not EMPTY;
- V1 is a static bounded DAG with deterministic rejection;
- V1 is same repository, authority, request issue, session, and generation
  only;
- runnable election remains the existing Gate 1 total order;
- no dataflow exists;
- Gate 1 \`JOB_STARTED -> RECOVERY_REQUIRED\` and zero auto replay remain;
- Gate 3 remains HOLD;
- Gate 4 remains HOLD;
- graph bounds are 32 nodes / 64 edges / fan-in 8 / fan-out 16 / depth 8 /
  65,536-byte payload.

Still owner-open:

- \`OWNER-G2-SEC-01\`: whether Gate 2 read-only dependency-triggered
  continuation may be activated under an explicitly limited
  \`GATE2_PILOT_READ_ONLY\` trust profile, or whether the autonomy increase
  requires \`FULL_V6_SECURITY\` first.

Until that owner decision and a separate runtime authority exist, the only
correct operational state is \`GATE2_NOT_ACTIVATED\`.
