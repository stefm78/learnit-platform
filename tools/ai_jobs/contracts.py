"""Closed Gate 1 contracts and deterministic canonicalization."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from . import (
    GATE0_OPERATIONS,
    MAX_GENERATION,
    MAX_RECORDS_PER_GENERATION,
    SCHEMA_VERSION,
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SESSION_ID_RE = re.compile(r"^G1S-[A-Z0-9][A-Z0-9._-]{2,63}$")
CODESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{1,79}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

STATES = frozenset({
    "CLOSED",
    "CANDIDATING",
    "GRANT_PENDING",
    "ACTIVE_IDLE",
    "JOB_SELECTED",
    "JOB_STARTED",
    "OUTCOME_AVAILABLE",
    "JOB_TERMINAL",
    "CLOSING",
    "RECOVERY_REQUIRED",
    "GLOBAL_HOLD",
})

TERMINAL_JOB_RESULTS = frozenset({
    "COMPLETED",
    "FAILED",
    "STALE_BEFORE_EXECUTION",
    "STALE_AFTER_EXECUTION",
    "AMBIGUOUS_HOLD",
})

RECORD_TYPES = frozenset({
    "SESSION_GRANT",
    "SESSION_ACTIVE",
    "JOB_SELECTED",
    "JOB_STARTED",
    "JOB_TERMINAL",
    "SESSION_CLOSE_CANDIDATE",
    "SESSION_CLOSE_ABORTED",
    "SESSION_CLOSED",
    "SESSION_RECOVERY_REQUIRED",
    "GLOBAL_HOLD",
    "STOP_ATTEMPTED",
})


class ContractError(RuntimeError):
    """Closed-contract validation failure."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ContractError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def loads_closed_json(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda item: (_ for _ in ()).throw(
                ContractError(f"invalid JSON constant: {item}")
            ),
            parse_float=lambda item: (_ for _ in ()).throw(
                ContractError(f"floating point numbers are forbidden: {item}")
            ),
        )
    except ContractError:
        raise
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical bytes for Gate 1 digests.

    Gate 1 normative objects use only null, booleans, exact integers, strings,
    arrays and objects. Floats are rejected recursively.
    """
    def check(item: Any) -> None:
        if isinstance(item, float):
            raise ContractError("floating point numbers are forbidden")
        if isinstance(item, bool) or item is None or isinstance(item, (int, str)):
            return
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ContractError("object keys must be strings")
            for child in item.values():
                check(child)
            return
        raise ContractError(f"unsupported canonical value type: {type(item).__name__}")

    check(value)
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def exact_fields(value: dict[str, Any], required: set[str], label: str) -> None:
    actual = set(value)
    if actual != required:
        missing = sorted(required - actual)
        unknown = sorted(actual - required)
        raise ContractError(
            f"{label} field mismatch; missing={missing}; unknown={unknown}"
        )


def exact_int(value: Any, label: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label} must be an exact integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ContractError(f"{label} is outside the closed range")
    return value


def iso_utc(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError(f"{label} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{label} is not a real calendar timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ContractError(f"{label} must be UTC")
    return value


@dataclass(frozen=True)
class QueueJob:
    repository: str
    origin_type: str
    origin_number: int
    request_comment_id: int
    request_author: str
    created_at: str
    job_id: str
    operation: str
    target_type: str
    target_number: int | None
    target_sha: str
    request_digest: str

    @property
    def order_key(self) -> tuple[int, str]:
        return self.request_comment_id, self.job_id


@dataclass(frozen=True)
class SessionGrant:
    repository: str
    authority_issue: int
    session_id: str
    codespace_name: str
    generation: int
    granted_by: str
    created_at: str
    grant_comment_id: int
    grant_digest: str

    def __post_init__(self) -> None:
        if not REPOSITORY_RE.fullmatch(self.repository):
            raise ContractError("grant repository must use owner/name")
        exact_int(self.authority_issue, "authority_issue", minimum=1)
        if not SESSION_ID_RE.fullmatch(self.session_id):
            raise ContractError("invalid session_id")
        if not CODESPACE_RE.fullmatch(self.codespace_name):
            raise ContractError("invalid codespace_name")
        exact_int(self.generation, "generation", minimum=1, maximum=MAX_GENERATION)
        if not self.granted_by:
            raise ContractError("granted_by must be non-empty")
        iso_utc(self.created_at, "created_at")
        exact_int(self.grant_comment_id, "grant_comment_id", minimum=1)
        if not SHA256_RE.fullmatch(self.grant_digest):
            raise ContractError("invalid grant_digest")


@dataclass(frozen=True)
class LedgerRecord:
    schema_version: str
    record_type: str
    repository: str
    authority_issue: int
    session_id: str
    generation: int
    sequence: int
    previous_record_sha256: str | None
    created_at: str
    payload: dict[str, Any]
    record_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractError("unsupported ledger schema_version")
        if self.record_type not in RECORD_TYPES:
            raise ContractError(f"unknown record_type: {self.record_type}")
        if not REPOSITORY_RE.fullmatch(self.repository):
            raise ContractError("repository must use owner/name")
        exact_int(self.authority_issue, "authority_issue", minimum=1)
        if not SESSION_ID_RE.fullmatch(self.session_id):
            raise ContractError("invalid session_id")
        exact_int(self.generation, "generation", minimum=1, maximum=MAX_GENERATION)
        exact_int(self.sequence, "sequence", minimum=1, maximum=MAX_RECORDS_PER_GENERATION)
        if self.previous_record_sha256 is not None and not SHA256_RE.fullmatch(self.previous_record_sha256):
            raise ContractError("invalid previous_record_sha256")
        iso_utc(self.created_at, "created_at")
        if not isinstance(self.payload, dict):
            raise ContractError("ledger payload must be an object")
        if not SHA256_RE.fullmatch(self.record_sha256):
            raise ContractError("invalid record_sha256")

    @classmethod
    def build(
        cls,
        *,
        record_type: str,
        repository: str,
        authority_issue: int,
        session_id: str,
        generation: int,
        sequence: int,
        previous_record_sha256: str | None,
        created_at: str,
        payload: dict[str, Any],
    ) -> "LedgerRecord":
        if record_type not in RECORD_TYPES:
            raise ContractError(f"unknown record_type: {record_type}")
        if not REPOSITORY_RE.fullmatch(repository):
            raise ContractError("repository must use owner/name")
        exact_int(authority_issue, "authority_issue", minimum=1)
        if not SESSION_ID_RE.fullmatch(session_id):
            raise ContractError("invalid session_id")
        exact_int(generation, "generation", minimum=1, maximum=MAX_GENERATION)
        exact_int(sequence, "sequence", minimum=1, maximum=MAX_RECORDS_PER_GENERATION)
        if previous_record_sha256 is not None and not SHA256_RE.fullmatch(previous_record_sha256):
            raise ContractError("invalid previous_record_sha256")
        iso_utc(created_at, "created_at")
        material = {
            "schema_version": SCHEMA_VERSION,
            "record_type": record_type,
            "repository": repository,
            "authority_issue": authority_issue,
            "session_id": session_id,
            "generation": generation,
            "sequence": sequence,
            "previous_record_sha256": previous_record_sha256,
            "created_at": created_at,
            "payload": payload,
        }
        digest = sha256_canonical(material)
        return cls(**material, record_sha256=digest)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_type": self.record_type,
            "repository": self.repository,
            "authority_issue": self.authority_issue,
            "session_id": self.session_id,
            "generation": self.generation,
            "sequence": self.sequence,
            "previous_record_sha256": self.previous_record_sha256,
            "created_at": self.created_at,
            "payload": self.payload,
            "record_sha256": self.record_sha256,
        }


def validate_gate0_operation(operation: str) -> str:
    if operation not in GATE0_OPERATIONS:
        raise ContractError(f"operation is outside the Gate 0 allowlist: {operation}")
    return operation
