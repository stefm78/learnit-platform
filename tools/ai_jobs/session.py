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


def project(records: Iterable[LedgerRecord], grant: SessionGrant) -> SessionProjection:
    chain = validate_chain(records)
    state = "CLOSED"
    started: set[str] = set()
    terminal: set[str] = set()
    selected_digest: str | None = None
    active_job: str | None = None

    allowed = {
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
    }

    for record in chain:
        if record.repository != grant.repository:
            raise ContractError("ledger repository differs from grant")
        if record.authority_issue != grant.authority_issue:
            raise ContractError("ledger authority issue differs from grant")
        if record.session_id != grant.session_id or record.generation != grant.generation:
            raise ContractError("ledger session/generation differs from grant")

        if record.record_type == "GLOBAL_HOLD":
            state = "GLOBAL_HOLD"
            selected_digest = None
            active_job = None
            continue
        if state == "GLOBAL_HOLD":
            raise ContractError("no record may advance a GLOBAL_HOLD generation")

        destination = allowed.get((state, record.record_type))
        if destination is None:
            raise ContractError(
                f"forbidden Gate 1 transition: {state} + {record.record_type}"
            )

        payload = record.payload
        digest = payload.get("request_digest") if isinstance(payload, dict) else None
        if record.record_type == "JOB_SELECTED":
            if not isinstance(digest, str) or not digest:
                raise ContractError("JOB_SELECTED lacks request_digest")
            if digest in started or digest in terminal:
                raise ContractError("JOB_SELECTED attempts to reuse an already-started request digest")
            selected_digest = digest
        elif record.record_type == "JOB_STARTED":
            if not isinstance(digest, str):
                raise ContractError("JOB_STARTED lacks request_digest")
            if digest != selected_digest:
                raise ContractError("JOB_STARTED does not match the durable JOB_SELECTED digest")
            if digest in started:
                raise ContractError("request digest was started more than once")
            started.add(digest)
            active_job = digest
        elif record.record_type == "SESSION_RECOVERY_REQUIRED":
            if not isinstance(digest, str) or digest != active_job:
                raise ContractError("SESSION_RECOVERY_REQUIRED does not bind the active job digest")
        elif record.record_type == "JOB_TERMINAL":
            if not isinstance(digest, str) or digest != active_job:
                raise ContractError("JOB_TERMINAL does not bind the active job digest")
            if digest not in started or digest in terminal:
                raise ContractError("JOB_TERMINAL has no unique matching JOB_STARTED")
            terminal.add(digest)
            active_job = None
            selected_digest = None
        elif record.record_type in {"SESSION_CLOSE_ABORTED", "SESSION_CLOSED"}:
            selected_digest = None
            active_job = None

        state = destination

    if terminal - started:
        raise ContractError("terminal request digests are not a subset of started digests")
    if active_job is not None and active_job in terminal:
        raise ContractError("active job digest is already terminal")

    return SessionProjection(
        state=state,
        last_record=chain[-1] if chain else None,
        started_request_digests=frozenset(started),
        terminal_request_digests=frozenset(terminal),
        active_job_digest=active_job,
    )


def bound_request_issue(records: Iterable[LedgerRecord]) -> int | None:
    """Return the immutable request-issue binding for an activated generation.

    A generation may not be restarted against another request issue to bypass
    the canonical global issue/comment bounds.
    """
    chain = validate_chain(records)
    if not chain:
        return None

    grant_records = [record for record in chain if record.record_type == "SESSION_GRANT"]
    if len(grant_records) != 1:
        raise ContractError("generation must contain exactly one SESSION_GRANT record")
    grant_payload = grant_records[0].payload
    request_issue = exact_int(
        grant_payload.get("request_issue") if isinstance(grant_payload, dict) else None,
        "SESSION_GRANT.payload.request_issue",
        minimum=1,
    )

    active_records = [record for record in chain if record.record_type == "SESSION_ACTIVE"]
    if active_records:
        if len(active_records) != 1:
            raise ContractError("generation must contain at most one SESSION_ACTIVE record")
        active_payload = active_records[0].payload
        active_issue = exact_int(
            active_payload.get("request_issue") if isinstance(active_payload, dict) else None,
            "SESSION_ACTIVE.payload.request_issue",
            minimum=1,
        )
        if active_issue != request_issue:
            raise ContractError("SESSION_ACTIVE changed the immutable request-issue binding")
    return request_issue


def require_exclusive_session(
    grants: Iterable[SessionGrant],
    records: Iterable[LedgerRecord],
    selected: SessionGrant,
) -> None:
    """Fail closed if another granted generation is not durably CLOSED.

    GitHub remains authoritative across host loss. A local process fence handles
    same-Codespace concurrency; this check prevents a second human-granted
    generation from becoming active while an earlier one is unresolved.
    """
    grant_list = tuple(grants)
    record_list = tuple(records)
    keys = [(grant.session_id, grant.generation) for grant in grant_list]
    if len(keys) != len(set(keys)):
        raise ContractError("duplicate session/generation grants are inadmissible")
    selected_key = (selected.session_id, selected.generation)
    if selected_key not in set(keys):
        raise ContractError("selected session grant is absent from authority snapshot")

    grant_keys = set(keys)
    for record in record_list:
        if (record.session_id, record.generation) not in grant_keys:
            raise ContractError("ledger record exists without a matching immutable session grant")

    for grant in grant_list:
        key = (grant.session_id, grant.generation)
        if key == selected_key:
            continue
        scoped = [
            record
            for record in record_list
            if record.session_id == grant.session_id and record.generation == grant.generation
        ]
        other = project(scoped, grant)
        if other.last_record is None or other.state != "CLOSED":
            raise ContractError(
                "another human-granted Gate 1 generation is not durably CLOSED"
            )
