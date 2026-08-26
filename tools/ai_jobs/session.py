"""Gate 1 session state projection and fail-closed transitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import ContractError, LedgerRecord, SessionGrant
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
        if record.record_type == "JOB_STARTED":
            if not isinstance(digest, str):
                raise ContractError("JOB_STARTED lacks request_digest")
            if digest in started:
                raise ContractError("request digest was started more than once")
            started.add(digest)
            active_job = digest
        elif record.record_type == "JOB_TERMINAL":
            if not isinstance(digest, str) or digest not in started:
                raise ContractError("JOB_TERMINAL has no matching JOB_STARTED")
            terminal.add(digest)
            active_job = None

        state = destination

    return SessionProjection(
        state=state,
        last_record=chain[-1] if chain else None,
        started_request_digests=frozenset(started),
        terminal_request_digests=frozenset(terminal),
        active_job_digest=active_job,
    )
