"""Gate 1 session projection, fencing and fail-closed transitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import ContractError, LedgerRecord, SessionGrant, exact_int
from .ledger import validate_chain


@dataclass(frozen=True)
class SessionProjection:
    state: str
    last_record: LedgerRecord | None
    started_request_digests: frozenset[str]
    terminal_request_digests: frozenset[str]
    active_job_digest: str | None


_ALLOWED = {
    ("CLOSED", "SESSION_GRANT"): "GRANT_PENDING",
    ("GRANT_PENDING", "SESSION_ACTIVE"): "ACTIVE_IDLE",
    ("ACTIVE_IDLE", "JOB_SELECTED"): "JOB_SELECTED",
    ("JOB_TERMINAL", "JOB_SELECTED"): "JOB_SELECTED",
    ("JOB_SELECTED", "JOB_STARTED"): "JOB_STARTED",
    ("JOB_STARTED", "JOB_TERMINAL"): "JOB_TERMINAL",
    ("JOB_STARTED", "SESSION_RECOVERY_REQUIRED"): "RECOVERY_REQUIRED",
    ("RECOVERY_REQUIRED", "JOB_TERMINAL"): "JOB_TERMINAL",
    ("ACTIVE_IDLE", "SESSION_CLOSE_CANDIDATE"): "CLOSING",
    ("JOB_TERMINAL", "SESSION_CLOSE_CANDIDATE"): "CLOSING",
    ("CLOSING", "SESSION_CLOSE_ABORTED"): "ACTIVE_IDLE",
    ("CLOSING", "SESSION_CLOSED"): "CLOSED",
    ("CLOSED", "STOP_ATTEMPTED"): "CLOSED",
}


def project(
    records: Iterable[LedgerRecord],
    grant: SessionGrant,
) -> SessionProjection:
    chain = validate_chain(records)
    state = "CLOSED"
    started: set[str] = set()
    terminal: set[str] = set()
    seen_job_ids: dict[str, str] = {}
    selected_digest: str | None = None
    selected_job_id: str | None = None
    selected_comment_id: int | None = None
    selected_target_sha: str | None = None
    active_job: str | None = None
    active_job_id: str | None = None
    request_issue: int | None = None
    grant_seen = False
    durably_closed = False
    closing_snapshot_digest: str | None = None

    for record in chain:
        if record.repository != grant.repository:
            raise ContractError("ledger repository differs from grant")
        if record.authority_issue != grant.authority_issue:
            raise ContractError("ledger authority issue differs from grant")
        if (
            record.session_id != grant.session_id
            or record.generation != grant.generation
        ):
            raise ContractError("ledger session/generation differs from grant")

        if record.record_type == "SESSION_GRANT":
            if grant_seen:
                raise ContractError(
                    "generation contains more than one durable SESSION_GRANT"
                )
            payload = record.payload
            if (
                payload["grant_comment_id"] != grant.grant_comment_id
                or payload["grant_digest"] != grant.grant_digest
            ):
                raise ContractError(
                    "durable SESSION_GRANT does not bind the immutable grant"
                )
            request_issue = payload["request_issue"]
            grant_seen = True
            durably_closed = False
        elif not grant_seen:
            raise ContractError(
                "ledger generation must begin with its durable SESSION_GRANT"
            )

        if record.record_type == "GLOBAL_HOLD":
            if state == "GLOBAL_HOLD":
                raise ContractError("GLOBAL_HOLD may be recorded only once")
            state = "GLOBAL_HOLD"
            continue
        if state == "GLOBAL_HOLD":
            raise ContractError(
                "no record may advance a GLOBAL_HOLD generation"
            )

        destination = _ALLOWED.get((state, record.record_type))
        if destination is None:
            raise ContractError(
                f"forbidden Gate 1 transition: {state} + "
                f"{record.record_type}"
            )

        payload = record.payload
        if record.record_type == "SESSION_ACTIVE":
            if payload["codespace_name"] != grant.codespace_name:
                raise ContractError(
                    "SESSION_ACTIVE codespace differs from immutable grant"
                )
            if payload["request_issue"] != request_issue:
                raise ContractError(
                    "SESSION_ACTIVE changed the immutable request-issue binding"
                )

        elif record.record_type == "JOB_SELECTED":
            digest = payload["request_digest"]
            job_id = payload["job_id"]
            if digest in started or digest in terminal:
                raise ContractError(
                    "JOB_SELECTED attempts to reuse an already-started request digest"
                )
            prior_digest = seen_job_ids.get(job_id)
            if prior_digest is not None:
                raise ContractError(
                    "JOB_SELECTED attempts to reuse an existing job_id"
                )
            seen_job_ids[job_id] = digest
            selected_digest = digest
            selected_job_id = job_id
            selected_comment_id = payload["request_comment_id"]
            selected_target_sha = payload["target_sha"]

        elif record.record_type == "JOB_STARTED":
            digest = payload["request_digest"]
            if (
                digest != selected_digest
                or payload["job_id"] != selected_job_id
                or payload["request_comment_id"] != selected_comment_id
                or payload["target_sha"] != selected_target_sha
            ):
                raise ContractError(
                    "JOB_STARTED does not exactly match durable JOB_SELECTED"
                )
            if digest in started:
                raise ContractError(
                    "request digest was started more than once"
                )
            started.add(digest)
            active_job = digest
            active_job_id = selected_job_id

        elif record.record_type == "SESSION_RECOVERY_REQUIRED":
            if payload["request_digest"] != active_job:
                raise ContractError(
                    "SESSION_RECOVERY_REQUIRED does not bind the active job digest"
                )

        elif record.record_type == "JOB_TERMINAL":
            digest = payload["request_digest"]
            if digest != active_job or payload["job_id"] != active_job_id:
                raise ContractError(
                    "JOB_TERMINAL does not bind the active job identity"
                )
            if digest not in started or digest in terminal:
                raise ContractError(
                    "JOB_TERMINAL has no unique matching JOB_STARTED"
                )
            terminal.add(digest)
            active_job = None
            active_job_id = None
            selected_digest = None
            selected_job_id = None
            selected_comment_id = None
            selected_target_sha = None

        elif record.record_type == "SESSION_CLOSE_CANDIDATE":
            closing_snapshot_digest = payload["request_snapshot_sha256"]

        elif record.record_type == "SESSION_CLOSE_ABORTED":
            closing_snapshot_digest = None
            selected_digest = None
            selected_job_id = None
            selected_comment_id = None
            selected_target_sha = None

        elif record.record_type == "SESSION_CLOSED":
            if payload["final_request_snapshot_sha256"] != closing_snapshot_digest:
                raise ContractError(
                    "SESSION_CLOSED does not bind the durable close-candidate snapshot"
                )
            if active_job is not None or selected_digest is not None:
                raise ContractError(
                    "SESSION_CLOSED cannot hide a non-terminal execution"
                )
            durably_closed = True
            closing_snapshot_digest = None

        elif record.record_type == "STOP_ATTEMPTED":
            if not durably_closed:
                raise ContractError(
                    "STOP_ATTEMPTED requires prior durable SESSION_CLOSED"
                )

        state = destination

    if terminal - started:
        raise ContractError(
            "terminal request digests are not a subset of started digests"
        )
    if active_job is not None and active_job in terminal:
        raise ContractError(
            "active job digest is already terminal"
        )

    return SessionProjection(
        state=state,
        last_record=chain[-1] if chain else None,
        started_request_digests=frozenset(started),
        terminal_request_digests=frozenset(terminal),
        active_job_digest=active_job,
    )


def bound_request_issue(records: Iterable[LedgerRecord]) -> int | None:
    """Return the immutable request-issue binding for a generation."""
    chain = validate_chain(records)
    if not chain:
        return None

    grant_records = [
        record
        for record in chain
        if record.record_type == "SESSION_GRANT"
    ]
    if len(grant_records) != 1:
        raise ContractError(
            "generation must contain exactly one SESSION_GRANT record"
        )
    grant_payload = grant_records[0].payload
    request_issue = exact_int(
        grant_payload["request_issue"],
        "SESSION_GRANT.payload.request_issue",
        minimum=1,
    )

    active_records = [
        record
        for record in chain
        if record.record_type == "SESSION_ACTIVE"
    ]
    if len(active_records) > 1:
        raise ContractError(
            "generation must contain at most one SESSION_ACTIVE record"
        )
    if active_records:
        active_issue = exact_int(
            active_records[0].payload["request_issue"],
            "SESSION_ACTIVE.payload.request_issue",
            minimum=1,
        )
        if active_issue != request_issue:
            raise ContractError(
                "SESSION_ACTIVE changed the immutable request-issue binding"
            )
    return request_issue


def require_exclusive_session(
    grants: Iterable[SessionGrant],
    records: Iterable[LedgerRecord],
    selected: SessionGrant,
) -> None:
    """Require one unambiguous selected generation and all others durably closed."""
    grant_list = tuple(grants)
    record_list = tuple(records)
    if not grant_list:
        raise ContractError("authority snapshot contains no session grant")

    keys = [
        (grant.session_id, grant.generation)
        for grant in grant_list
    ]
    if len(keys) != len(set(keys)):
        raise ContractError(
            "duplicate session/generation grants are inadmissible"
        )

    session_ids = [grant.session_id for grant in grant_list]
    if len(session_ids) != len(set(session_ids)):
        raise ContractError(
            "session_id reuse across generations is inadmissible"
        )

    generations = [grant.generation for grant in grant_list]
    if len(generations) != len(set(generations)):
        raise ContractError(
            "multiple grants for the same generation are inadmissible"
        )

    grant_digests = [grant.grant_digest for grant in grant_list]
    if len(grant_digests) != len(set(grant_digests)):
        raise ContractError(
            "immutable grant identity was reused"
        )

    selected_key = (selected.session_id, selected.generation)
    if selected_key not in set(keys):
        raise ContractError(
            "selected session grant is absent from authority snapshot"
        )
    if selected.generation != max(generations):
        raise ContractError(
            "only the highest granted generation may be selected"
        )

    grant_keys = set(keys)
    for record in record_list:
        if (record.session_id, record.generation) not in grant_keys:
            raise ContractError(
                "ledger record exists without a matching immutable session grant"
            )

    for grant in grant_list:
        key = (grant.session_id, grant.generation)
        if key == selected_key:
            continue
        scoped = [
            record
            for record in record_list
            if record.session_id == grant.session_id
            and record.generation == grant.generation
        ]
        other = project(scoped, grant)
        if other.last_record is None or other.state != "CLOSED":
            raise ContractError(
                "another human-granted Gate 1 generation is not durably CLOSED"
            )
