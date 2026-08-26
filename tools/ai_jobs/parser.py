"""Parse Gate 0 request comments and Gate 1 authority comments fail-closed."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from tools.codespace_evidence.request import (
    EvidenceRequest,
    RequestError,
    parse_request_envelope,
)

from . import GRANT_MARKER, LEDGER_MARKER, SUSPEND_MARKER
from .contracts import (
    ContractError,
    LedgerRecord,
    QueueJob,
    SessionGrant,
    canonical_json_bytes,
    exact_fields,
    exact_int,
    iso_utc,
    loads_closed_json,
)

FENCED_JSON_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
DIGEST_LINE_RE = re.compile(r"(?m)^payload_sha256: ([0-9a-f]{64})$")


def _single_payload(body: str, marker: str) -> tuple[dict[str, Any], str]:
    if body.count(marker) != 1 or not body.startswith(marker + "\n"):
        raise ContractError(f"expected exactly one leading {marker}")
    fences = FENCED_JSON_RE.findall(body)
    digests = DIGEST_LINE_RE.findall(body)
    if len(fences) != 1 or len(digests) != 1:
        raise ContractError("authority comment must contain one JSON block and one digest")
    value = loads_closed_json(fences[0])
    if not isinstance(value, dict):
        raise ContractError("authority payload must be an object")
    digest = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
    if digest != digests[0]:
        raise ContractError("authority payload digest mismatch")
    return value, digest


def queue_job_from_comment(
    comment: dict[str, Any],
    *,
    repository: str,
    origin_type: str,
    origin_number: int,
) -> QueueJob | None:
    body = comment.get("body")
    if not isinstance(body, str) or "AI_CODESPACE_REQUEST_V1" not in body:
        return None
    comment_id = comment.get("id")
    user = comment.get("user")
    author = user.get("login") if isinstance(user, dict) else None
    created_at = comment.get("created_at")
    if not isinstance(comment_id, int) or comment_id < 1:
        raise ContractError("request comment has invalid id")
    if not isinstance(author, str) or not author:
        raise ContractError("request comment has no stable author")
    updated_at = comment.get("updated_at")
    if not isinstance(created_at, str) or not isinstance(updated_at, str):
        raise ContractError("request comment timestamps are unavailable")
    if created_at != updated_at:
        raise ContractError(f"edited request comment is inadmissible: {comment_id}")
    iso_utc(created_at, "request_comment.created_at")
    try:
        value, digest = parse_request_envelope(body)
        request = EvidenceRequest.from_value(value, digest)
    except RequestError as exc:
        raise ContractError(f"malformed Gate 0 request comment {comment_id}: {exc}") from exc
    if request.repository != repository:
        raise ContractError("request repository differs from queue repository")
    if request.origin.type != origin_type or request.origin.number != origin_number:
        raise ContractError("request origin differs from queue origin")
    if request.origin.request_comment_id != comment_id:
        raise ContractError("request is not bound to its own source comment")
    return QueueJob(
        repository=repository,
        origin_type=origin_type,
        origin_number=origin_number,
        request_comment_id=comment_id,
        request_author=author,
        created_at=created_at,
        job_id=request.job_id,
        operation=request.operation,
        target_type=request.target_type,
        target_number=request.target_number,
        target_sha=request.target_sha,
        request_digest=request.digest_sha256,
    )


def grant_from_comment(
    comment: dict[str, Any],
    *,
    repository: str,
    authority_issue: int,
) -> SessionGrant | None:
    body = comment.get("body")
    if not isinstance(body, str) or GRANT_MARKER not in body:
        return None
    if comment.get("created_at") != comment.get("updated_at"):
        raise ContractError("edited session grant is inadmissible")
    value, digest = _single_payload(body, GRANT_MARKER)
    required = {
        "repository", "authority_issue", "session_id", "codespace_name",
        "generation", "granted_by", "created_at",
    }
    exact_fields(value, required, "session grant")
    user = comment.get("user")
    author = user.get("login") if isinstance(user, dict) else None
    comment_id = comment.get("id")
    if not isinstance(author, str) or author != value["granted_by"]:
        raise ContractError("grant author does not match granted_by")
    if value["repository"] != repository or value["authority_issue"] != authority_issue:
        raise ContractError("grant authority binding mismatch")
    return SessionGrant(
        repository=value["repository"],
        authority_issue=exact_int(value["authority_issue"], "authority_issue", minimum=1),
        session_id=value["session_id"],
        codespace_name=value["codespace_name"],
        generation=exact_int(value["generation"], "generation", minimum=1),
        granted_by=value["granted_by"],
        created_at=value["created_at"],
        grant_comment_id=exact_int(comment_id, "grant_comment_id", minimum=1),
        grant_digest=digest,
    )


def ledger_from_comment(
    comment: dict[str, Any],
    *,
    repository: str,
    authority_issue: int,
) -> LedgerRecord | None:
    body = comment.get("body")
    if not isinstance(body, str) or LEDGER_MARKER not in body:
        return None
    if comment.get("created_at") != comment.get("updated_at"):
        raise ContractError("edited ledger record is inadmissible")
    value, digest = _single_payload(body, LEDGER_MARKER)
    required = {
        "schema_version", "record_type", "repository", "authority_issue",
        "session_id", "generation", "sequence", "previous_record_sha256",
        "created_at", "payload", "record_sha256",
    }
    exact_fields(value, required, "ledger record")
    if value["repository"] != repository or value["authority_issue"] != authority_issue:
        raise ContractError("ledger authority binding mismatch")
    claimed = value["record_sha256"]
    material = dict(value)
    material.pop("record_sha256")
    actual = hashlib.sha256(canonical_json_bytes(material)).hexdigest()
    if claimed != actual or digest != hashlib.sha256(canonical_json_bytes(value)).hexdigest():
        raise ContractError("ledger digest mismatch")
    return LedgerRecord(**value)


def is_suspend_comment(comment: dict[str, Any], *, repository: str, authority_issue: int) -> bool:
    body = comment.get("body")
    if not isinstance(body, str) or SUSPEND_MARKER not in body:
        return False
    if comment.get("created_at") != comment.get("updated_at"):
        raise ContractError("edited suspension record is inadmissible")
    value, _ = _single_payload(body, SUSPEND_MARKER)
    exact_fields(value, {"repository", "authority_issue", "created_at", "reason"}, "suspend")
    if value["repository"] != repository or value["authority_issue"] != authority_issue:
        raise ContractError("suspend authority binding mismatch")
    iso_utc(value["created_at"], "suspend.created_at")
    if not isinstance(value["reason"], str) or not value["reason"]:
        raise ContractError("suspend reason must be non-empty")
    return True
