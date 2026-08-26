"""Closed, deterministic and credential-free Gate 1 data contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping

from . import (
    GATE0_OPERATIONS,
    GLOBAL_BOUND_LIMITS,
    MAX_GENERATION,
    MAX_RECORDS_PER_GENERATION,
    SCHEMA_VERSION,
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
SESSION_ID_RE = re.compile(r"^G1S-[A-Z0-9][A-Z0-9._-]{2,63}$", re.ASCII)
CODESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{1,79}$", re.ASCII)
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", re.ASCII)
JOB_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,79}$", re.ASCII)
UTC_SECONDS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", re.ASCII)
TIME_MIN = datetime(2000, 1, 1, tzinfo=timezone.utc)
TIME_MAX = datetime(2100, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

STATES = frozenset({
    "CLOSED", "GRANT_PENDING", "ACTIVE_IDLE", "JOB_SELECTED", "JOB_STARTED",
    "JOB_TERMINAL", "CLOSING", "RECOVERY_REQUIRED", "GLOBAL_HOLD",
})
TERMINAL_JOB_RESULTS = frozenset({
    "COMPLETED", "FAILED", "STALE_BEFORE_EXECUTION", "STALE_AFTER_EXECUTION",
    "AMBIGUOUS_HOLD",
})
RECORD_TYPES = frozenset({
    "SESSION_GRANT", "SESSION_ACTIVE", "JOB_SELECTED", "JOB_STARTED",
    "JOB_TERMINAL", "SESSION_CLOSE_CANDIDATE", "SESSION_CLOSE_ABORTED",
    "SESSION_CLOSED", "SESSION_RECOVERY_REQUIRED", "GLOBAL_HOLD",
    "STOP_ATTEMPTED",
})


class ContractError(RuntimeError):
    """Closed-contract validation failure."""


class FrozenDict(dict):
    """JSON-compatible mapping that rejects mutation."""

    @staticmethod
    def _blocked(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("Gate 1 canonical objects are immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _blocked


def _nfc(value: str, label: str = "string") -> str:
    if not isinstance(value, str):
        raise ContractError(f"{label} must be text")
    return unicodedata.normalize("NFC", value)


def freeze_json(value: Any) -> Any:
    """Normalize and recursively freeze the exact JSON value domain."""
    if value is None or type(value) is bool or type(value) is int:
        return value
    if type(value) is float:
        raise ContractError("floating point numbers are forbidden")
    if isinstance(value, str):
        return _nfc(value)
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item) for item in value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("object keys must be strings")
            key = _nfc(key, "object key")
            if key in result:
                raise ContractError(f"object contains colliding NFC keys: {key}")
            result[key] = freeze_json(item)
        return FrozenDict(result)
    raise ContractError(f"unsupported canonical value type: {type(value).__name__}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = item
    return result


def loads_closed_json(text: str) -> Any:
    if not isinstance(text, str):
        raise ContractError("JSON input must be text")
    try:
        value = json.loads(
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
    return freeze_json(value)


def canonical_json_bytes(value: Any) -> bytes:
    normalized = freeze_json(value)
    return json.dumps(
        normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def exact_fields(value: Mapping[str, Any], required: set[str] | frozenset[str], label: str) -> None:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label} must be an object")
    actual, expected = set(value), set(required)
    if actual != expected:
        raise ContractError(
            f"{label} field mismatch; missing={sorted(expected-actual)}; "
            f"unknown={sorted(actual-expected)}"
        )


def exact_int(value: Any, label: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    # R5: JSON booleans and int subclasses are not exact integers.
    if type(value) is not int:
        raise ContractError(f"{label} must be an exact integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ContractError(f"{label} is outside the closed range")
    return value


def validate_global_bounds(**values: Any) -> FrozenDict:
    """Validate exactly the seven normative R5 capacity metrics."""
    exact_fields(values, set(GLOBAL_BOUND_LIMITS), "global bounds")
    return FrozenDict({
        name: exact_int(values[name], name, minimum=0, maximum=limit)
        for name, limit in GLOBAL_BOUND_LIMITS.items()
    })


def iso_utc(value: Any, label: str) -> str:
    if not isinstance(value, str) or UTC_SECONDS_RE.fullmatch(value) is None:
        raise ContractError(f"{label} must use exact YYYY-MM-DDTHH:MM:SSZ UTC-seconds syntax")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContractError(f"{label} is not a real calendar timestamp") from exc
    if not TIME_MIN <= parsed <= TIME_MAX:
        raise ContractError(f"{label} is outside the canonical 2000-2100 time domain")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be non-empty text")
    if _nfc(value, label) != value:
        raise ContractError(f"{label} must already be NFC-normalized")
    return value


def _match(value: Any, regex: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or regex.fullmatch(value) is None:
        raise ContractError(f"invalid {label}")
    return value


def _payload_fields(payload: Mapping[str, Any], variants: tuple[frozenset[str], ...], label: str) -> None:
    if frozenset(payload) not in variants:
        raise ContractError(f"{label} payload field mismatch")


_PAYLOAD_KEYS: dict[str, tuple[frozenset[str], ...]] = {
    "SESSION_GRANT": (frozenset({"grant_comment_id", "grant_digest", "request_issue"}),),
    "SESSION_ACTIVE": (frozenset({"codespace_name", "request_issue"}),),
    "JOB_SELECTED": (frozenset({
        "job_id", "request_digest", "request_comment_id", "target_type",
        "target_number", "target_sha",
    }),),
    "JOB_STARTED": (frozenset({"job_id", "request_digest", "request_comment_id", "target_sha"}),),
    "JOB_TERMINAL": (frozenset({
        "job_id", "request_digest", "result", "gate0_return_code",
        "gate0_timed_out", "gate0_authoritative_comment_id",
    }),),
    "SESSION_CLOSE_CANDIDATE": (frozenset({"request_snapshot_sha256", "cutoff_comment_id"}),),
    "SESSION_CLOSE_ABORTED": (frozenset({"reason"}),),
    "SESSION_CLOSED": (frozenset({"final_request_snapshot_sha256"}),),
    "SESSION_RECOVERY_REQUIRED": (frozenset({"request_digest", "reason"}),),
    "GLOBAL_HOLD": (frozenset({"reason"}), frozenset({"reason", "request_digest"})),
    "STOP_ATTEMPTED": (frozenset({"result"}), frozenset({"result", "reason"})),
}


def _validate_record_payload(record_type: str, payload: Mapping[str, Any]) -> None:
    variants = _PAYLOAD_KEYS.get(record_type)
    if variants is None:
        raise ContractError(f"unknown record_type: {record_type}")
    _payload_fields(payload, variants, record_type)

    if record_type == "SESSION_GRANT":
        exact_int(payload["grant_comment_id"], "grant_comment_id", minimum=1)
        _match(payload["grant_digest"], SHA256_RE, "grant_digest")
        exact_int(payload["request_issue"], "request_issue", minimum=1)
    elif record_type == "SESSION_ACTIVE":
        _match(payload["codespace_name"], CODESPACE_RE, "SESSION_ACTIVE codespace_name")
        exact_int(payload["request_issue"], "request_issue", minimum=1)
    elif record_type in {"JOB_SELECTED", "JOB_STARTED"}:
        _match(payload["job_id"], JOB_ID_RE, f"{record_type} job_id")
        _match(payload["request_digest"], SHA256_RE, "request_digest")
        exact_int(payload["request_comment_id"], "request_comment_id", minimum=1)
        _match(payload["target_sha"], SHA_RE, "target_sha")
        if record_type == "JOB_SELECTED":
            if payload["target_type"] not in {"commit", "pull_request"}:
                raise ContractError("invalid JOB_SELECTED target_type")
            if payload["target_type"] == "commit":
                if payload["target_number"] is not None:
                    raise ContractError("commit target must not have target_number")
            else:
                exact_int(payload["target_number"], "target_number", minimum=1)
    elif record_type == "JOB_TERMINAL":
        _match(payload["job_id"], JOB_ID_RE, "JOB_TERMINAL job_id")
        _match(payload["request_digest"], SHA256_RE, "request_digest")
        if payload["result"] not in TERMINAL_JOB_RESULTS:
            raise ContractError("invalid JOB_TERMINAL result")
        exact_int(payload["gate0_return_code"], "gate0_return_code", minimum=0, maximum=255)
        if type(payload["gate0_timed_out"]) is not bool:
            raise ContractError("gate0_timed_out must be a boolean")
        exact_int(payload["gate0_authoritative_comment_id"], "gate0_authoritative_comment_id", minimum=1)
    elif record_type == "SESSION_CLOSE_CANDIDATE":
        _match(payload["request_snapshot_sha256"], SHA256_RE, "request_snapshot_sha256")
        exact_int(payload["cutoff_comment_id"], "cutoff_comment_id", minimum=0)
    elif record_type == "SESSION_CLOSED":
        _match(payload["final_request_snapshot_sha256"], SHA256_RE, "final_request_snapshot_sha256")
    elif record_type == "SESSION_RECOVERY_REQUIRED":
        _match(payload["request_digest"], SHA256_RE, "request_digest")
        _text(payload["reason"], "SESSION_RECOVERY_REQUIRED reason")
    elif record_type == "GLOBAL_HOLD":
        _text(payload["reason"], "GLOBAL_HOLD reason")
        if "request_digest" in payload:
            _match(payload["request_digest"], SHA256_RE, "request_digest")
    elif record_type == "SESSION_CLOSE_ABORTED":
        _text(payload["reason"], "SESSION_CLOSE_ABORTED reason")
    elif record_type == "STOP_ATTEMPTED":
        _text(payload["result"], "STOP_ATTEMPTED result")
        if "reason" in payload:
            _text(payload["reason"], "STOP_ATTEMPTED reason")


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

    def __post_init__(self) -> None:
        _match(self.repository, REPOSITORY_RE, "repository")
        if self.origin_type not in {"issue", "pull_request"}:
            raise ContractError("invalid origin_type")
        exact_int(self.origin_number, "origin_number", minimum=1)
        exact_int(self.request_comment_id, "request_comment_id", minimum=1)
        _text(self.request_author, "request_author")
        iso_utc(self.created_at, "created_at")
        _match(self.job_id, JOB_ID_RE, "job_id")
        validate_gate0_operation(self.operation)
        if self.target_type not in {"commit", "pull_request"}:
            raise ContractError("invalid target_type")
        if self.target_type == "commit":
            if self.target_number is not None:
                raise ContractError("commit target must not have target_number")
        else:
            exact_int(self.target_number, "target_number", minimum=1)
        _match(self.target_sha, SHA_RE, "target_sha")
        _match(self.request_digest, SHA256_RE, "request_digest")

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
        _match(self.repository, REPOSITORY_RE, "repository")
        exact_int(self.authority_issue, "authority_issue", minimum=1)
        _match(self.session_id, SESSION_ID_RE, "session_id")
        _match(self.codespace_name, CODESPACE_RE, "codespace_name")
        exact_int(self.generation, "generation", minimum=1, maximum=MAX_GENERATION)
        _text(self.granted_by, "granted_by")
        iso_utc(self.created_at, "created_at")
        exact_int(self.grant_comment_id, "grant_comment_id", minimum=1)
        _match(self.grant_digest, SHA256_RE, "grant_digest")


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
        if self.schema_version != SCHEMA_VERSION or self.record_type not in RECORD_TYPES:
            raise ContractError("unsupported ledger schema_version or record_type")
        _match(self.repository, REPOSITORY_RE, "repository")
        exact_int(self.authority_issue, "authority_issue", minimum=1)
        _match(self.session_id, SESSION_ID_RE, "session_id")
        exact_int(self.generation, "generation", minimum=1, maximum=MAX_GENERATION)
        exact_int(self.sequence, "sequence", minimum=1, maximum=MAX_RECORDS_PER_GENERATION)
        if self.previous_record_sha256 is not None:
            _match(self.previous_record_sha256, SHA256_RE, "previous_record_sha256")
        iso_utc(self.created_at, "created_at")
        frozen = freeze_json(self.payload)
        if not isinstance(frozen, FrozenDict):
            raise ContractError("ledger payload must be an object")
        object.__setattr__(self, "payload", frozen)
        _validate_record_payload(self.record_type, frozen)
        _match(self.record_sha256, SHA256_RE, "record_sha256")
        material = self.as_dict()
        claimed = material.pop("record_sha256")
        if claimed != sha256_canonical(material):
            raise ContractError("ledger record digest is invalid")

    @classmethod
    def build(cls, *, record_type: str, repository: str, authority_issue: int,
              session_id: str, generation: int, sequence: int,
              previous_record_sha256: str | None, created_at: str,
              payload: dict[str, Any]) -> "LedgerRecord":
        frozen = freeze_json(payload)
        if not isinstance(frozen, FrozenDict):
            raise ContractError("ledger payload must be an object")
        material = {
            "schema_version": SCHEMA_VERSION, "record_type": record_type,
            "repository": repository, "authority_issue": authority_issue,
            "session_id": session_id, "generation": generation, "sequence": sequence,
            "previous_record_sha256": previous_record_sha256,
            "created_at": created_at, "payload": frozen,
        }
        return cls(**material, record_sha256=sha256_canonical(material))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "record_type": self.record_type,
            "repository": self.repository, "authority_issue": self.authority_issue,
            "session_id": self.session_id, "generation": self.generation,
            "sequence": self.sequence,
            "previous_record_sha256": self.previous_record_sha256,
            "created_at": self.created_at, "payload": self.payload,
            "record_sha256": self.record_sha256,
        }


def validate_gate0_operation(operation: str) -> str:
    if operation not in GATE0_OPERATIONS:
        raise ContractError(f"operation is outside the Gate 0 allowlist: {operation}")
    return operation
