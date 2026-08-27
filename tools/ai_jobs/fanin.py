"""Deterministic Gate 2 bounded read-only fan-in overlay.

This module is credential-free. It consumes normalized stable GitHub snapshots and
an authenticated publisher login supplied by the existing Gate 1 coordinator.
It never invokes Gate 0, creates requests, or exposes a generic effect channel.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping

from tools.codespace_evidence.request import EvidenceRequest, RequestError, parse_request_envelope
from tools.codespace_evidence.run import _discover_candidates

from . import (
    GATE0_OPERATIONS,
    GATE2_GRAPH_MARKER,
    GATE2_GRAPH_SCHEMA_VERSION,
    GATE2_RECEIPT_MARKER,
    GATE2_RECEIPT_SCHEMA_VERSION,
)
from .contracts import (
    ContractError,
    JOB_ID_RE,
    LedgerRecord,
    QueueJob,
    SessionGrant,
    SHA256_RE,
    SHA_RE,
    canonical_json_bytes,
    exact_fields,
    exact_int,
    loads_closed_json,
)
from .ledger import validate_chain
from .parser import queue_job_from_comment
from .session import project
from .snapshot import StableSnapshot

MAX_GATE2_PAYLOAD_BYTES = 65_536
MAX_GATE2_NODES = 32
MAX_GATE2_EDGES = 64
MAX_GATE2_FAN_IN = 8
MAX_GATE2_FAN_OUT = 16
MAX_GATE2_DEPTH = 8

_GRAPH_ID_RE = re.compile(r"^G2D-[A-Z0-9][A-Z0-9._-]{2,63}$", re.ASCII)
_ENVELOPE_RE_TEMPLATE = (
    r"\A{marker}\npayload_sha256: ([0-9a-f]{{64}})\n"
    r"```json\n([^\n]+)\n```\Z"
)

_GRAPH_FIELDS = frozenset({
    "schema_version", "repository", "authority_issue", "request_issue",
    "session_id", "generation", "session_grant_comment_id",
    "session_grant_digest", "graph_id", "nodes",
})
_REF_FIELDS = frozenset({
    "job_id", "request_comment_id", "request_sha256", "target_sha",
})
_NODE_FIELDS = frozenset(set(_REF_FIELDS) | {"depends_on"})
_RECEIPT_FIELDS = frozenset({
    "schema_version", "repository", "authority_issue", "request_issue",
    "session_id", "generation", "graph_comment_id", "graph_payload_sha256",
    "predecessor", "gate1_terminal_record_sha256", "gate1_terminal_sequence",
    "gate0_authoritative_comment_id", "gate0_outcome_body_sha256",
})


class Gate2Error(ContractError):
    """Closed Gate 2 contract or live-authority failure."""

    def __init__(self, code: str, detail: str, *, graph_state: str = "GLOBAL_HOLD") -> None:
        self.code = code
        self.detail = detail
        self.graph_state = graph_state
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, order=True)
class Gate2Ref:
    request_comment_id: int
    job_id: str
    request_sha256: str
    target_sha: str

    @property
    def order_key(self) -> tuple[int, str]:
        return self.request_comment_id, self.job_id

    @classmethod
    def from_value(cls, value: Mapping[str, Any], label: str) -> "Gate2Ref":
        exact_fields(value, _REF_FIELDS, label)
        job_id = value.get("job_id")
        if not isinstance(job_id, str) or JOB_ID_RE.fullmatch(job_id) is None:
            raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", f"{label}.job_id is invalid")
        comment_id = exact_int(value.get("request_comment_id"), f"{label}.request_comment_id", minimum=1)
        request_sha = value.get("request_sha256")
        target_sha = value.get("target_sha")
        if not isinstance(request_sha, str) or SHA256_RE.fullmatch(request_sha) is None:
            raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", f"{label}.request_sha256 is invalid")
        if not isinstance(target_sha, str) or SHA_RE.fullmatch(target_sha) is None:
            raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", f"{label}.target_sha is invalid")
        return cls(comment_id, job_id, request_sha, target_sha)

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "request_comment_id": self.request_comment_id,
            "request_sha256": self.request_sha256,
            "target_sha": self.target_sha,
        }


@dataclass(frozen=True)
class Gate2Node:
    ref: Gate2Ref
    depends_on: tuple[Gate2Ref, ...]


@dataclass(frozen=True)
class Gate2Graph:
    repository: str
    authority_issue: int
    request_issue: int
    session_id: str
    generation: int
    session_grant_comment_id: int
    session_grant_digest: str
    graph_id: str
    nodes: tuple[Gate2Node, ...]
    comment_id: int
    payload_sha256: str
    author: str

    @property
    def by_ref(self) -> dict[Gate2Ref, Gate2Node]:
        return {node.ref: node for node in self.nodes}


@dataclass(frozen=True)
class Gate2Receipt:
    comment_id: int
    payload_sha256: str
    predecessor: Gate2Ref
    terminal_record_sha256: str
    terminal_sequence: int
    outcome_comment_id: int
    outcome_body_sha256: str


@dataclass(frozen=True)
class ReceiptPlan:
    predecessor: Gate2Ref
    payload: dict[str, Any]


@dataclass(frozen=True)
class Gate2Projection:
    graph: Gate2Graph
    graph_state: str
    node_states: tuple[tuple[Gate2Ref, str], ...]
    dependency_truth: tuple[tuple[Gate2Ref, str], ...]
    runnable: tuple[Gate2Ref, ...]
    receipt_plans: tuple[ReceiptPlan, ...]

    def node_state(self, ref: Gate2Ref) -> str:
        for item, state in self.node_states:
            if item == ref:
                return state
        raise Gate2Error("G2_INTERNAL_PROJECTION_INCONSISTENT", "node absent from projection")

    def truth(self, ref: Gate2Ref) -> str:
        for item, state in self.dependency_truth:
            if item == ref:
                return state
        raise Gate2Error("G2_INTERNAL_PROJECTION_INCONSISTENT", "dependency truth absent")

    def ref_for_job(self, job: QueueJob) -> Gate2Ref:
        ref = Gate2Ref(job.request_comment_id, job.job_id, job.request_digest, job.target_sha)
        if ref not in self.graph.by_ref:
            raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", "selected Gate 1 job is not one exact Gate 2 node")
        return ref


def _comment_for_parser(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "node_id": raw.get("node_id"),
        "body": raw.get("body"),
        "user": {
            "login": raw.get("author"),
            "id": raw.get("author_id"),
            "node_id": raw.get("author_node_id"),
        },
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "html_url": raw.get("html_url"),
        "issue_url": raw.get("issue_url"),
    }


def jobs_from_snapshot(snapshot: StableSnapshot, *, repository: str, request_issue: int) -> tuple[QueueJob, ...]:
    if not isinstance(repository, str) or not repository:
        raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", "repository is invalid")
    exact_int(request_issue, "request_issue", minimum=1)
    result: list[QueueJob] = []
    for raw in snapshot.comments:
        job = queue_job_from_comment(
            _comment_for_parser(raw), repository=repository,
            origin_type="issue", origin_number=request_issue,
        )
        if job is not None:
            if job.operation not in GATE0_OPERATIONS:
                raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", "Gate 2 node operation is outside Gate 0")
            result.append(job)
    return tuple(result)


def _parse_envelope(body: Any, marker: str, label: str) -> tuple[dict[str, Any], str, bytes]:
    code = "G2_RECEIPT_INVALID" if label == "receipt" else "G2_GRAPH_SCHEMA_INVALID"
    if not isinstance(body, str):
        raise Gate2Error(code, f"{label} body unavailable")
    pattern = re.compile(_ENVELOPE_RE_TEMPLATE.format(marker=re.escape(marker)), re.ASCII)
    match = pattern.fullmatch(body)
    if match is None:
        raise Gate2Error(code, f"{label} envelope is not exact")
    claimed, json_text = match.groups()
    try:
        value = loads_closed_json(json_text)
        if not isinstance(value, Mapping):
            raise Gate2Error(code, f"{label} payload must be an object")
        canonical = canonical_json_bytes(value)
    except Gate2Error:
        raise
    except ContractError as exc:
        raise Gate2Error(code, f"{label} JSON is outside the closed canonical domain") from exc
    if canonical.decode("utf-8") != json_text:
        raise Gate2Error(code, f"{label} JSON is not canonical")
    actual = hashlib.sha256(canonical).hexdigest()
    if actual != claimed:
        raise Gate2Error(code, f"{label} payload digest mismatch")
    return dict(value), actual, canonical


def _immutable_author(raw: Mapping[str, Any], *, label: str, edited_code: str) -> tuple[int, str]:
    comment_id = exact_int(raw.get("id"), f"{label}.id", minimum=1)
    if raw.get("created_at") != raw.get("updated_at"):
        raise Gate2Error(edited_code, f"{label} comment {comment_id} was edited")
    author = raw.get("author")
    if not isinstance(author, str) or not author:
        raise Gate2Error("G2_GRAPH_AUTHORITY_MISMATCH", f"{label} author unavailable")
    return comment_id, author


def _parse_node(value: Mapping[str, Any], index: int) -> Gate2Node:
    exact_fields(value, _NODE_FIELDS, f"nodes[{index}]")
    ref = Gate2Ref.from_value({key: value[key] for key in _REF_FIELDS}, f"nodes[{index}]")
    deps_value = value.get("depends_on")
    if not isinstance(deps_value, (tuple, list)):
        raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", f"nodes[{index}].depends_on must be an array")
    deps = tuple(Gate2Ref.from_value(dep, f"nodes[{index}].depends_on[{j}]") for j, dep in enumerate(deps_value))
    return Gate2Node(ref, deps)


def _bind_graph_jobs(nodes: tuple[Gate2Node, ...], jobs: Iterable[QueueJob]) -> None:
    items = tuple(jobs)
    for node in nodes:
        matches = [
            job for job in items
            if job.job_id == node.ref.job_id
            and job.request_comment_id == node.ref.request_comment_id
            and job.request_digest == node.ref.request_sha256
            and job.target_sha == node.ref.target_sha
        ]
        if len(matches) != 1:
            raise Gate2Error(
                "G2_REQUEST_BINDING_MISMATCH",
                f"node {node.ref.job_id} does not reproduce exactly one current immutable Gate 1 request",
            )


def _validate_graph_structure(nodes: tuple[Gate2Node, ...], payload_size: int, jobs: Iterable[QueueJob]) -> None:
    # Normative order: bounds, order+request reproduction, duplicates, edges,
    # missing/cross-boundary refs, direct cycle, indirect cycle, depth.
    if payload_size > MAX_GATE2_PAYLOAD_BYTES or not 1 <= len(nodes) <= MAX_GATE2_NODES:
        raise Gate2Error("G2_GRAPH_BOUND_EXCEEDED", "graph payload/node bound exceeded")
    edge_count = sum(len(node.depends_on) for node in nodes)
    if edge_count > MAX_GATE2_EDGES or any(len(node.depends_on) > MAX_GATE2_FAN_IN for node in nodes):
        raise Gate2Error("G2_GRAPH_BOUND_EXCEEDED", "edge/fan-in bound exceeded")
    fan_out: dict[Gate2Ref, int] = {}
    for node in nodes:
        for dep in node.depends_on:
            fan_out[dep] = fan_out.get(dep, 0) + 1
    if any(count > MAX_GATE2_FAN_OUT for count in fan_out.values()):
        raise Gate2Error("G2_GRAPH_BOUND_EXCEEDED", "fan-out bound exceeded")

    node_order = tuple(node.ref.order_key for node in nodes)
    if node_order != tuple(sorted(node_order)):
        raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", "graph nodes are not canonically ordered")
    for node in nodes:
        dep_order = tuple(dep.order_key for dep in node.depends_on)
        if dep_order != tuple(sorted(dep_order)):
            raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", f"depends_on for {node.ref.job_id} is not canonically ordered")
    _bind_graph_jobs(nodes, jobs)

    for attr in ("job_id", "request_comment_id", "request_sha256"):
        values = [getattr(node.ref, attr) for node in nodes]
        if len(values) != len(set(values)):
            raise Gate2Error("G2_DUPLICATE_NODE_IDENTITY", f"duplicate graph node {attr}")

    refs = {node.ref for node in nodes}
    for node in nodes:
        if len(node.depends_on) != len(set(node.depends_on)):
            raise Gate2Error("G2_DUPLICATE_DEPENDENCY", f"duplicate dependency for {node.ref.job_id}")
    for node in nodes:
        for dep in node.depends_on:
            if dep not in refs:
                aliases = [
                    candidate for candidate in refs
                    if candidate.job_id == dep.job_id
                    or candidate.request_comment_id == dep.request_comment_id
                    or candidate.request_sha256 == dep.request_sha256
                ]
                code = "G2_CROSS_BOUNDARY_REFERENCE" if aliases else "G2_MISSING_DEPENDENCY"
                raise Gate2Error(code, f"dependency for {node.ref.job_id} does not resolve exactly inside graph")
    for node in nodes:
        if node.ref in node.depends_on:
            raise Gate2Error("G2_CYCLE_DIRECT", f"direct self-cycle at {node.ref.job_id}")

    indegree = {node.ref: len(node.depends_on) for node in nodes}
    followers: dict[Gate2Ref, list[Gate2Ref]] = {node.ref: [] for node in nodes}
    by_ref = {node.ref: node for node in nodes}
    for node in nodes:
        for dep in node.depends_on:
            followers[dep].append(node.ref)
    ready = sorted((ref for ref, degree in indegree.items() if degree == 0), key=lambda ref: ref.order_key)
    emitted: list[Gate2Ref] = []
    while ready:
        current = ready.pop(0)
        emitted.append(current)
        for child in sorted(followers[current], key=lambda ref: ref.order_key):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort(key=lambda ref: ref.order_key)
    if len(emitted) != len(nodes):
        raise Gate2Error("G2_CYCLE_INDIRECT", "graph contains an indirect cycle")

    depth: dict[Gate2Ref, int] = {}
    for ref in emitted:
        deps = by_ref[ref].depends_on
        depth[ref] = 0 if not deps else 1 + max(depth[dep] for dep in deps)
        if depth[ref] > MAX_GATE2_DEPTH:
            raise Gate2Error("G2_DEPTH_BOUND_EXCEEDED", f"graph depth exceeds 8 at {ref.job_id}")


def parse_graph(
    snapshot: StableSnapshot, *, repository: str, authority_issue: int,
    request_issue: int, grant: SessionGrant, jobs: Iterable[QueueJob],
) -> Gate2Graph:
    candidates: list[tuple[Mapping[str, Any], dict[str, Any], str, bytes]] = []
    for raw in snapshot.comments:
        body = raw.get("body")
        if not isinstance(body, str) or GATE2_GRAPH_MARKER not in body:
            continue
        payload, digest, canonical = _parse_envelope(body, GATE2_GRAPH_MARKER, "graph")
        exact_fields(payload, _GRAPH_FIELDS, "Gate 2 graph")
        if payload.get("schema_version") != GATE2_GRAPH_SCHEMA_VERSION:
            raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", "unsupported Gate 2 graph schema")
        session_id = payload.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", "graph.session_id is invalid")
        generation = exact_int(payload.get("generation"), "graph.generation", minimum=1)
        exact_int(payload.get("authority_issue"), "graph.authority_issue", minimum=1)
        exact_int(payload.get("request_issue"), "graph.request_issue", minimum=1)
        exact_int(
            payload.get("session_grant_comment_id"),
            "graph.session_grant_comment_id",
            minimum=1,
        )
        graph_repository = payload.get("repository")
        if not isinstance(graph_repository, str) or not graph_repository:
            raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", "graph.repository is invalid")
        grant_digest = payload.get("session_grant_digest")
        if not isinstance(grant_digest, str) or SHA256_RE.fullmatch(grant_digest) is None:
            raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", "graph.session_grant_digest is invalid")
        if session_id != grant.session_id or generation != grant.generation:
            continue
        candidates.append((raw, payload, digest, canonical))

    if len(candidates) != 1:
        raise Gate2Error("G2_GRAPH_SESSION_MISMATCH", "exactly one immutable graph is required for selected session/generation")
    raw, payload, digest, canonical = candidates[0]
    comment_id, author = _immutable_author(raw, label="graph", edited_code="G2_GRAPH_COMMENT_EDITED")

    if payload.get("repository") != repository or payload.get("authority_issue") != authority_issue:
        raise Gate2Error("G2_GRAPH_AUTHORITY_MISMATCH", "graph repository/authority issue mismatch")
    if payload.get("request_issue") != request_issue:
        raise Gate2Error("G2_CROSS_BOUNDARY_REFERENCE", "graph request issue mismatch")
    if author != grant.granted_by:
        raise Gate2Error("G2_GRAPH_AUTHORITY_MISMATCH", "graph author differs from selected grantor")
    if payload.get("session_grant_comment_id") != grant.grant_comment_id or payload.get("session_grant_digest") != grant.grant_digest:
        raise Gate2Error("G2_GRAPH_SESSION_MISMATCH", "graph does not bind exact selected session grant")
    graph_id = payload.get("graph_id")
    if not isinstance(graph_id, str) or _GRAPH_ID_RE.fullmatch(graph_id) is None:
        raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", "graph_id is invalid")
    nodes_value = payload.get("nodes")
    if not isinstance(nodes_value, (tuple, list)):
        raise Gate2Error("G2_GRAPH_SCHEMA_INVALID", "nodes must be an array")
    nodes = tuple(_parse_node(node, index) for index, node in enumerate(nodes_value))
    _validate_graph_structure(nodes, len(canonical), jobs)
    return Gate2Graph(
        repository=repository, authority_issue=authority_issue, request_issue=request_issue,
        session_id=grant.session_id, generation=grant.generation,
        session_grant_comment_id=grant.grant_comment_id,
        session_grant_digest=grant.grant_digest, graph_id=graph_id, nodes=nodes,
        comment_id=comment_id, payload_sha256=digest, author=author,
    )


def _request_for_node(snapshot: StableSnapshot, graph: Gate2Graph, node: Gate2Node) -> EvidenceRequest:
    matches = [raw for raw in snapshot.comments if raw.get("id") == node.ref.request_comment_id]
    if len(matches) != 1:
        raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", f"source request {node.ref.request_comment_id} missing/non-unique")
    raw = matches[0]
    job = queue_job_from_comment(
        _comment_for_parser(raw), repository=graph.repository,
        origin_type="issue", origin_number=graph.request_issue,
    )
    if job is None:
        raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", f"source request {node.ref.request_comment_id} is no longer a Gate 0 request")
    if (
        job.job_id != node.ref.job_id
        or job.request_comment_id != node.ref.request_comment_id
        or job.request_digest != node.ref.request_sha256
        or job.target_sha != node.ref.target_sha
        or job.operation not in GATE0_OPERATIONS
    ):
        raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", f"source request for {node.ref.job_id} changed identity")
    body = raw.get("body")
    if not isinstance(body, str):
        raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", "source request body unavailable")
    try:
        value, digest = parse_request_envelope(body)
        request = EvidenceRequest.from_value(value, digest)
    except (RequestError, ValueError) as exc:
        raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", "source request no longer validates") from exc
    return request


def _terminal_for_node(records: tuple[LedgerRecord, ...], node: Gate2Node) -> LedgerRecord | None:
    matches = [
        record for record in records
        if record.record_type == "JOB_TERMINAL"
        and record.payload.get("job_id") == node.ref.job_id
        and record.payload.get("request_digest") == node.ref.request_sha256
    ]
    if len(matches) > 1:
        raise Gate2Error("G2_TERMINAL_AMBIGUOUS", f"terminal truth for {node.ref.job_id} is non-unique")
    return matches[0] if matches else None


@dataclass(frozen=True)
class _OutcomeReadback:
    authenticated_login: str
    repository: str
    comments_value: tuple[dict[str, Any], ...]

    def list_origin_comments(self, repository: str, origin_number: int) -> list[dict[str, Any]]:
        if repository != self.repository:
            raise Gate2Error("G2_CROSS_BOUNDARY_REFERENCE", "Gate 0 validation requested another repository")
        exact_int(origin_number, "origin_number", minimum=1)
        return list(self.comments_value)


def _validated_outcome(
    *, request_snapshot: StableSnapshot, graph: Gate2Graph, node: Gate2Node,
    terminal: LedgerRecord, authenticated_login: str,
) -> tuple[int, str]:
    request = _request_for_node(request_snapshot, graph, node)
    comments = tuple(_comment_for_parser(raw) for raw in request_snapshot.comments)
    readback = _OutcomeReadback(authenticated_login, graph.repository, comments)
    try:
        election = _discover_candidates(readback, request)
    except Exception as exc:
        raise Gate2Error("G2_OUTCOME_INVALIDATED", f"existing Gate 0 validation failed for {node.ref.job_id}: {type(exc).__name__}") from exc
    incumbent = election.incumbent
    expected_id = terminal.payload.get("gate0_authoritative_comment_id")
    if incumbent is None or incumbent.comment_id != expected_id:
        raise Gate2Error("G2_OUTCOME_INVALIDATED", f"authoritative Gate 0 outcome for {node.ref.job_id} is missing or changed")
    current = [raw for raw in request_snapshot.comments if raw.get("id") == expected_id]
    if len(current) != 1:
        raise Gate2Error("G2_OUTCOME_INVALIDATED", f"bound Gate 0 outcome for {node.ref.job_id} is missing/non-unique")
    raw = current[0]
    if raw.get("created_at") != raw.get("updated_at"):
        raise Gate2Error("G2_OUTCOME_INVALIDATED", f"bound Gate 0 outcome for {node.ref.job_id} was edited")
    if raw.get("author") != authenticated_login:
        raise Gate2Error("G2_OUTCOME_INVALIDATED", f"bound Gate 0 outcome for {node.ref.job_id} has untrusted publisher")
    body = raw.get("body")
    if not isinstance(body, str):
        raise Gate2Error("G2_OUTCOME_INVALIDATED", "bound Gate 0 outcome body unavailable")
    body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if incumbent.body_sha256 != body_sha:
        raise Gate2Error("G2_OUTCOME_INVALIDATED", "Gate 0 election digest differs from exact current body")
    return exact_int(expected_id, "gate0_authoritative_comment_id", minimum=1), body_sha


def _parse_receipt_payload(raw: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    payload, digest, _canonical = _parse_envelope(raw.get("body"), GATE2_RECEIPT_MARKER, "receipt")
    exact_fields(payload, _RECEIPT_FIELDS, "Gate 2 receipt")
    if payload.get("schema_version") != GATE2_RECEIPT_SCHEMA_VERSION:
        raise Gate2Error("G2_RECEIPT_INVALID", "unsupported Gate 2 receipt schema")
    for field in (
        "authority_issue", "request_issue", "generation", "graph_comment_id",
        "gate1_terminal_sequence", "gate0_authoritative_comment_id",
    ):
        exact_int(payload.get(field), f"receipt.{field}", minimum=1)
    for field in (
        "graph_payload_sha256", "gate1_terminal_record_sha256", "gate0_outcome_body_sha256",
    ):
        value = payload.get(field)
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            raise Gate2Error("G2_RECEIPT_INVALID", f"receipt.{field} is invalid")
    predecessor = payload.get("predecessor")
    if not isinstance(predecessor, Mapping):
        raise Gate2Error("G2_RECEIPT_INVALID", "receipt predecessor must be an object")
    Gate2Ref.from_value(predecessor, "receipt.predecessor")
    return payload, digest


def _receipt_for_completed(
    *, authority_snapshot: StableSnapshot, graph: Gate2Graph, grant: SessionGrant,
    node: Gate2Node, terminal: LedgerRecord, outcome_comment_id: int,
    outcome_body_sha256: str,
) -> Gate2Receipt | None:
    matching: list[Gate2Receipt] = []
    for raw in authority_snapshot.comments:
        body = raw.get("body")
        if not isinstance(body, str) or GATE2_RECEIPT_MARKER not in body:
            continue
        payload, digest = _parse_receipt_payload(raw)
        if payload.get("session_id") != graph.session_id or payload.get("generation") != graph.generation:
            continue
        if (
            payload.get("repository") != graph.repository
            or payload.get("authority_issue") != graph.authority_issue
            or payload.get("request_issue") != graph.request_issue
            or payload.get("graph_comment_id") != graph.comment_id
            or payload.get("graph_payload_sha256") != graph.payload_sha256
        ):
            raise Gate2Error("G2_RECEIPT_INVALID", "receipt scope/graph binding mismatch")
        comment_id, author = _immutable_author(raw, label="receipt", edited_code="G2_RECEIPT_INVALID")
        if author != grant.granted_by:
            raise Gate2Error("G2_RECEIPT_INVALID", "receipt author differs from selected pilot identity")
        predecessor = Gate2Ref.from_value(payload["predecessor"], "receipt.predecessor")
        if predecessor not in graph.by_ref:
            raise Gate2Error(
                "G2_RECEIPT_INVALID",
                "receipt predecessor does not resolve exactly inside the selected graph",
            )
        if predecessor != node.ref:
            continue
        if (
            payload.get("gate1_terminal_record_sha256") != terminal.record_sha256
            or payload.get("gate1_terminal_sequence") != terminal.sequence
            or payload.get("gate0_authoritative_comment_id") != outcome_comment_id
            or payload.get("gate0_outcome_body_sha256") != outcome_body_sha256
        ):
            raise Gate2Error("G2_RECEIPT_INVALID", f"receipt for {node.ref.job_id} no longer binds current terminal/outcome")
        matching.append(Gate2Receipt(
            comment_id=comment_id,
            payload_sha256=digest,
            predecessor=predecessor,
            terminal_record_sha256=terminal.record_sha256,
            terminal_sequence=terminal.sequence,
            outcome_comment_id=outcome_comment_id,
            outcome_body_sha256=outcome_body_sha256,
        ))
    if not matching:
        return None
    digests = {item.payload_sha256 for item in matching}
    if len(digests) != 1:
        raise Gate2Error("G2_RECEIPT_AMBIGUOUS", f"divergent valid receipts exist for {node.ref.job_id}")
    return min(matching, key=lambda item: item.comment_id)


def build_receipt_payload(
    *, graph: Gate2Graph, node: Gate2Node, terminal: LedgerRecord,
    outcome_comment_id: int, outcome_body_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": GATE2_RECEIPT_SCHEMA_VERSION,
        "repository": graph.repository,
        "authority_issue": graph.authority_issue,
        "request_issue": graph.request_issue,
        "session_id": graph.session_id,
        "generation": graph.generation,
        "graph_comment_id": graph.comment_id,
        "graph_payload_sha256": graph.payload_sha256,
        "predecessor": node.ref.as_dict(),
        "gate1_terminal_record_sha256": terminal.record_sha256,
        "gate1_terminal_sequence": terminal.sequence,
        "gate0_authoritative_comment_id": outcome_comment_id,
        "gate0_outcome_body_sha256": outcome_body_sha256,
    }


def render_dependency_receipt(payload: Mapping[str, Any]) -> str:
    exact_fields(payload, _RECEIPT_FIELDS, "Gate 2 receipt payload")
    canonical = canonical_json_bytes(payload)
    digest = hashlib.sha256(canonical).hexdigest()
    return (
        f"{GATE2_RECEIPT_MARKER}\n"
        f"payload_sha256: {digest}\n"
        "```json\n"
        f"{canonical.decode('utf-8')}\n"
        "```"
    )


def reconstruct_gate2(
    *, authority_snapshot: StableSnapshot, request_snapshot: StableSnapshot,
    repository: str, authority_issue: int, request_issue: int, grant: SessionGrant,
    gate1_records: Iterable[LedgerRecord], authenticated_login: str,
) -> Gate2Projection:
    if authenticated_login != grant.granted_by:
        raise Gate2Error("G2_GRAPH_AUTHORITY_MISMATCH", "authenticated pilot identity differs from selected grantor")
    jobs = jobs_from_snapshot(request_snapshot, repository=repository, request_issue=request_issue)
    graph = parse_graph(
        authority_snapshot, repository=repository, authority_issue=authority_issue,
        request_issue=request_issue, grant=grant, jobs=jobs,
    )
    records = validate_chain(tuple(gate1_records))
    session = project(records, grant)

    truth: dict[Gate2Ref, str] = {}
    terminals: dict[Gate2Ref, LedgerRecord | None] = {}
    plans: list[ReceiptPlan] = []
    for node in graph.nodes:
        # Full current source reconstruction is mandatory for every node.
        _request_for_node(request_snapshot, graph, node)
        terminal = _terminal_for_node(records, node)
        terminals[node.ref] = terminal
        if terminal is None:
            truth[node.ref] = "UNFINISHED"
            continue
        result = terminal.payload.get("result")
        if result == "FAILED":
            truth[node.ref] = "FAILED"
            continue
        if result in {"STALE_BEFORE_EXECUTION", "STALE_AFTER_EXECUTION"}:
            truth[node.ref] = "STALE"
            continue
        if result == "AMBIGUOUS_HOLD":
            truth[node.ref] = "AMBIGUOUS"
            continue
        if result != "COMPLETED":
            raise Gate2Error("G2_TERMINAL_AMBIGUOUS", f"unsupported terminal result for {node.ref.job_id}")
        outcome_id, outcome_sha = _validated_outcome(
            request_snapshot=request_snapshot, graph=graph, node=node,
            terminal=terminal, authenticated_login=authenticated_login,
        )
        receipt = _receipt_for_completed(
            authority_snapshot=authority_snapshot, graph=graph, grant=grant,
            node=node, terminal=terminal, outcome_comment_id=outcome_id,
            outcome_body_sha256=outcome_sha,
        )
        if receipt is None:
            truth[node.ref] = "BINDING_PENDING"
            plans.append(ReceiptPlan(
                predecessor=node.ref,
                payload=build_receipt_payload(
                    graph=graph, node=node, terminal=terminal,
                    outcome_comment_id=outcome_id, outcome_body_sha256=outcome_sha,
                ),
            ))
        else:
            truth[node.ref] = "SATISFIED"

    active_ref: Gate2Ref | None = None
    if session.state in {"JOB_SELECTED", "JOB_STARTED"} and session.last_record is not None:
        payload = session.last_record.payload
        matches = [
            node.ref for node in graph.nodes
            if node.ref.job_id == payload.get("job_id")
            and node.ref.request_sha256 == payload.get("request_digest")
            and node.ref.request_comment_id == payload.get("request_comment_id")
            and node.ref.target_sha == payload.get("target_sha")
        ]
        if len(matches) != 1:
            raise Gate2Error("G2_REQUEST_BINDING_MISMATCH", "active Gate 1 job is not exactly one graph node")
        active_ref = matches[0]

    node_states: dict[Gate2Ref, str] = {}
    runnable: list[Gate2Ref] = []
    for node in graph.nodes:
        terminal_truth = truth[node.ref]
        if terminal_truth == "SATISFIED":
            node_states[node.ref] = "SUCCEEDED"
            continue
        if terminal_truth == "BINDING_PENDING" and terminals[node.ref] is not None:
            node_states[node.ref] = "BINDING_PENDING"
            continue
        if terminal_truth in {"FAILED", "STALE", "AMBIGUOUS"}:
            node_states[node.ref] = terminal_truth
            continue
        if active_ref == node.ref:
            node_states[node.ref] = "SELECTED" if session.state == "JOB_SELECTED" else "STARTED"
            continue
        direct = tuple(truth[dep] for dep in node.depends_on)
        if any(item in {"FAILED", "STALE", "AMBIGUOUS"} for item in direct):
            node_states[node.ref] = "BLOCKED"
        elif any(item == "UNFINISHED" for item in direct):
            node_states[node.ref] = "WAITING"
        elif any(item == "BINDING_PENDING" for item in direct):
            node_states[node.ref] = "BINDING_PENDING"
        elif all(item == "SATISFIED" for item in direct):
            node_states[node.ref] = "RUNNABLE"
            runnable.append(node.ref)
        else:
            raise Gate2Error("G2_INTERNAL_PROJECTION_INCONSISTENT", f"cannot project node {node.ref.job_id}")

    if session.state == "GLOBAL_HOLD":
        graph_state = "GLOBAL_HOLD"
    elif session.state == "RECOVERY_REQUIRED":
        graph_state = "RECOVERY_REQUIRED"
    elif all(state == "SUCCEEDED" for state in node_states.values()):
        graph_state = "COMPLETE"
    elif any(state in {"RUNNABLE", "SELECTED", "STARTED"} for state in node_states.values()):
        graph_state = "ACTIVE"
    elif any(state == "BINDING_PENDING" for state in node_states.values()):
        graph_state = "RECONCILING"
    elif any(state in {"BLOCKED", "FAILED", "STALE", "AMBIGUOUS"} for state in node_states.values()):
        graph_state = "BLOCKED"
    else:
        raise Gate2Error("G2_INTERNAL_PROJECTION_INCONSISTENT", "graph is neither active, reconciling, blocked nor complete")

    return Gate2Projection(
        graph=graph,
        graph_state=graph_state,
        node_states=tuple((node.ref, node_states[node.ref]) for node in graph.nodes),
        dependency_truth=tuple((node.ref, truth[node.ref]) for node in graph.nodes),
        runnable=tuple(sorted(runnable, key=lambda ref: ref.order_key)),
        receipt_plans=tuple(sorted(plans, key=lambda plan: plan.predecessor.order_key)),
    )


def require_boundary_eligible(
    projection: Gate2Projection, *, job: QueueJob,
    expected_gate1_state: str, gate1_tail: LedgerRecord,
) -> None:
    """Require one fresh full reconstruction before a privileged Gate 1 boundary."""
    if expected_gate1_state not in {"JOB_SELECTED", "JOB_STARTED"}:
        raise Gate2Error("G2_INTERNAL_PROJECTION_INCONSISTENT", "invalid boundary state")
    if gate1_tail.record_type != expected_gate1_state:
        raise Gate2Error("G2_BOUNDARY_AUTHORITY_CHANGED", "Gate 1 tail type differs from boundary")
    payload = gate1_tail.payload
    if (
        payload.get("job_id") != job.job_id
        or payload.get("request_digest") != job.request_digest
        or payload.get("request_comment_id") != job.request_comment_id
        or payload.get("target_sha") != job.target_sha
    ):
        raise Gate2Error("G2_BOUNDARY_AUTHORITY_CHANGED", "Gate 1 tail no longer binds selected descendant")
    ref = projection.ref_for_job(job)
    node = projection.graph.by_ref[ref]
    direct = tuple(projection.truth(dep) for dep in node.depends_on)
    if any(item in {"FAILED", "STALE", "AMBIGUOUS"} for item in direct):
        raise Gate2Error("G2_BOUNDARY_BLOCKED", "direct predecessor is failed/stale/ambiguous", graph_state="BLOCKED")
    if any(item != "SATISFIED" for item in direct):
        raise Gate2Error("G2_BOUNDARY_INVALIDATED", "fresh dependency truth no longer proves every predecessor SATISFIED")
    expected_node_state = "SELECTED" if expected_gate1_state == "JOB_SELECTED" else "STARTED"
    if projection.node_state(ref) != expected_node_state:
        raise Gate2Error("G2_BOUNDARY_AUTHORITY_CHANGED", "fresh projection no longer proves selected descendant state")


def runnable_jobs(projection: Gate2Projection, jobs: Iterable[QueueJob]) -> tuple[QueueJob, ...]:
    allowed = set(projection.runnable)
    selected = [
        job for job in jobs
        if Gate2Ref(job.request_comment_id, job.job_id, job.request_digest, job.target_sha) in allowed
    ]
    return tuple(sorted(selected, key=lambda job: job.order_key))
